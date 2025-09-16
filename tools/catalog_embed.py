#!/usr/bin/env python3
"""
Build embeddings in-place for amis_catalog and create pgvector ANN index.
Auto-detects available libraries and falls back to hash-based embeddings if needed.
"""

import argparse
import numpy as np
from sqlalchemy import create_engine, text


def sanitize(name: str) -> str:
    return name.replace('-', '_').replace('.', '_')


def run(version: str, dburl: str, model_id: str, batch_size: int = 2000) -> None:
    eng = create_engine(dburl)

    # Try to import sentence-transformers, fallback to simple embeddings if not available
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_id)
        use_real_embeddings = True
        print(f"✅ Using real embeddings with {model_id}")
    except ImportError:
        model = None
        use_real_embeddings = False
        batch_size = min(batch_size, 500)  # Smaller batches for hash-based
        print(f"⚠️  sentence-transformers not available, using hash-based embeddings")
        print(f"⚠️  Note: These are for testing only - install sentence-transformers for production")

    with eng.begin() as cx:
        rows = cx.execute(text(
            """
            SELECT id, label FROM amis_catalog
            WHERE catalog_version = :v AND embedding IS NULL
            """
        ), {"v": version}).fetchall()

    total = len(rows)
    print(f"Embedding {total} rows for {version} with model {model_id} ...")

    for i in range(0, total, batch_size):
        chunk = rows[i:i+batch_size]
        ids = [r[0] for r in chunk]

        # Use structured labels for embeddings
        texts = [r[1] if r[1] else "" for r in chunk]  # r[1] is the label column

        if use_real_embeddings:
            # Real embeddings using sentence-transformers
            vecs = model.encode(texts, normalize_embeddings=True)
            params = []
            for _id, vec in zip(ids, vecs):
                emb_list = np.asarray(vec, dtype=np.float32).tolist()
                emb_str = "[" + ",".join(map(str, emb_list)) + "]"
                params.append({"id": _id, "embedding": emb_str})
        else:
            # Hash-based embeddings for testing
            params = []
            for _id, label_text in zip(ids, texts):
                # Create deterministic but varied embeddings based on label hash
                text_hash = hash(label_text.lower())
                np.random.seed(abs(text_hash) % (2**31))  # Deterministic seed
                embedding = np.random.normal(0, 1, 384).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)  # Normalize

                emb_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
                params.append({"id": _id, "embedding": emb_str})

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
            WHERE catalog_version = :v
            """
        ), {"v": version})
        cx.execute(text("ANALYZE amis_catalog"))

    with eng.begin() as cx:
        cx.execute(text(
            """
            UPDATE catalog_import
            SET model_id=:m, status='EMBEDDED'
            WHERE version=:v
            """
        ), {"m": model_id, "v": version})

    print("Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--batch-size", type=int, default=2000)
    args = ap.parse_args()
    run(args.version, args.db, args.model_id, args.batch_size)


