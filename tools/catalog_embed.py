#!/usr/bin/env python3
"""
Build embeddings in-place for amis_catalog using intfloat/multilingual-e5-large.
Uses sentence-transformers for high-quality multilingual embeddings.
"""

import argparse
import numpy as np
from sqlalchemy import create_engine, text
import sys
import pathlib

# Add ML package to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "ml" / "src"))

try:
    from app.ml.embed import VehicleEmbedder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("❌ sentence-transformers not available, falling back to TF-IDF")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD


def sanitize(name: str) -> str:
    return name.replace('-', '_').replace('.', '_')


def run_with_sentence_transformers(version: str, dburl: str, model_id: str, batch_size: int = 100) -> None:
    """Generate embeddings using sentence-transformers with intfloat/multilingual-e5-large."""
    eng = create_engine(dburl)

    print(f"✅ Using sentence-transformers with {model_id}")

    # Initialize embedder
    embedder = VehicleEmbedder(model_name=model_id)

    # Get all texts for the version
    with eng.begin() as cx:
        rows = cx.execute(text(
            """
            SELECT id, descveh, marca, submarca, modelo, tipveh FROM amis_catalog
            WHERE catalog_version = :v AND embedding IS NULL
            """
        ), {"v": version}).fetchall()

    total = len(rows)
    print(f"Processing {total} rows for {version}...")

    if total == 0:
        print("No rows to embed.")
        return

    # Process in batches to avoid memory issues
    print("🔄 Generating embeddings with sentence-transformers...")
    for i in range(0, total, batch_size):
        chunk_rows = rows[i:i+batch_size]

        # Prepare vehicle data for embedding
        vehicles = []
        for row in chunk_rows:
            vehicle = {
                "brand": row[2] if row[2] else "",
                "model": row[3] if row[3] else "",
                "year": row[4] if row[4] else None,
                "description": row[1] if row[1] else "",
                "body": "",
                "use": ""
            }
            vehicles.append(vehicle)

        # Generate embeddings for this batch
        try:
            embeddings = embedder.embed_batch(vehicles, batch_size=min(32, len(vehicles)))

            # Prepare database parameters
            params = []
            for j, row in enumerate(chunk_rows):
                embedding = embeddings[j]
                emb_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
                params.append({"id": row[0], "embedding": emb_str})

            # Update database
            if params:
                with eng.begin() as cx:
                    cx.execute(text(
                        """
                        UPDATE amis_catalog
                        SET embedding = CAST(:embedding AS vector)
                        WHERE id = :id
                        """
                    ), params)

        except Exception as e:
            print(f"❌ Error processing batch {i}-{i+batch_size}: {e}")
            continue

        print(f"  -> {min(i+batch_size, total)}/{total}")

    # Create ANN index for this version
    index_name = f"amis_emb_hnsw_{sanitize(version)}"
    with eng.begin() as cx:
        cx.execute(text(
            f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON amis_catalog USING hnsw (embedding vector_cosine_ops)
            WHERE catalog_version = '{version}'
            """
        ))
        cx.execute(text("ANALYZE amis_catalog"))

    # Update catalog import status
    with eng.begin() as cx:
        cx.execute(text(
            """
            UPDATE catalog_import
            SET model_id=:m, status='EMBEDDED'
            WHERE version=:v
            """
        ), {"m": model_id, "v": version})

    print("✅ Done with sentence-transformers embeddings.")


def run_with_tfidf_fallback(version: str, dburl: str, model_id: str, batch_size: int = 2000) -> None:
    """Generate embeddings using TF-IDF + SVD as fallback."""
    eng = create_engine(dburl)

    print(f"✅ Using TF-IDF vectorization with {model_id} (fallback method)")
    print("📝 Note: Using TF-IDF + SVD as fallback since sentence-transformers requires PyTorch")

    # Get all texts for the version to fit the vectorizer
    with eng.begin() as cx:
        rows = cx.execute(text(
            """
            SELECT id, descveh FROM amis_catalog
            WHERE catalog_version = :v AND embedding IS NULL
            """
        ), {"v": version}).fetchall()

    total = len(rows)
    print(f"Processing {total} rows for {version}...")

    if total == 0:
        print("No rows to embed.")
        return

    # Extract texts
    texts = [r[1] if r[1] else "" for r in rows]
    ids = [r[0] for r in rows]

    # Create TF-IDF vectors
    print("🔄 Creating TF-IDF vectors...")
    vectorizer = TfidfVectorizer(
        max_features=10000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        print(f"✅ TF-IDF matrix shape: {tfidf_matrix.shape}")

        # Reduce dimensionality to 1024 using SVD (to match multilingual-e5-large)
        print("🔄 Reducing dimensionality with SVD...")
        svd = TruncatedSVD(n_components=1024, random_state=42)
        embeddings = svd.fit_transform(tfidf_matrix)

        # Normalize embeddings
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        print(f"✅ Final embeddings shape: {embeddings.shape}")

    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        return

    # Process in batches for database insertion
    print("🔄 Inserting embeddings into database...")
    for i in range(0, total, batch_size):
        chunk_embeddings = embeddings[i:i+batch_size]
        chunk_ids = ids[i:i+batch_size]

        params = []
        for j, _id in enumerate(chunk_ids):
            embedding = chunk_embeddings[j]
            emb_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
            params.append({"id": _id, "embedding": emb_str})

        # Update database
        if params:
            with eng.begin() as cx:
                cx.execute(text(
                    """
                    UPDATE amis_catalog
                    SET embedding = CAST(:embedding AS vector)
                    WHERE id = :id
                    """
                ), params)
            print(f"  -> {min(i+batch_size, total)}/{total}")

    # Create ANN index for this version
    index_name = f"amis_emb_hnsw_{sanitize(version)}"
    with eng.begin() as cx:
        cx.execute(text(
            f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON amis_catalog USING hnsw (embedding vector_cosine_ops)
            WHERE catalog_version = '{version}'
            """
        ))
        cx.execute(text("ANALYZE amis_catalog"))

    # Update catalog import status
    with eng.begin() as cx:
        cx.execute(text(
            """
            UPDATE catalog_import
            SET model_id=:m, status='EMBEDDED'
            WHERE version=:v
            """
        ), {"m": f"tfidf-svd-{model_id}", "v": version})

    print("✅ Done with TF-IDF fallback.")


def run(version: str, dburl: str, model_id: str, batch_size: int = 2000) -> None:
    """Generate embeddings using the best available method."""
    if SENTENCE_TRANSFORMERS_AVAILABLE and model_id.startswith("intfloat/"):
        # Use sentence-transformers for proper multilingual embeddings
        run_with_sentence_transformers(version, dburl, model_id, batch_size=100)
    else:
        # Fall back to TF-IDF + SVD
        run_with_tfidf_fallback(version, dburl, model_id, batch_size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="Catalog version to embed")
    ap.add_argument("--db", required=True, help="Database URL")
    ap.add_argument("--model-id", required=True, help="Model identifier (intfloat/multilingual-e5-large)")
    ap.add_argument("--batch-size", type=int, default=2000, help="Batch size for database insertion (default: 2000)")
    args = ap.parse_args()
    run(args.version, args.db, args.model_id, args.batch_size)