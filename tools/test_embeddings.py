#!/usr/bin/env python3
"""
Test script to verify embedding functionality works properly.
"""

import sys
import pathlib

# Add ML package to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "ml" / "src"))

def test_embedder():
    """Test the VehicleEmbedder class."""
    try:
        from app.ml.embed import VehicleEmbedder
        print("✅ Successfully imported VehicleEmbedder")
    except ImportError as e:
        print(f"❌ Failed to import VehicleEmbedder: {e}")
        return False

    try:
        # Test embedder initialization
        print("🔄 Initializing embedder with intfloat/multilingual-e5-large...")
        embedder = VehicleEmbedder(model_name="intfloat/multilingual-e5-large")
        print(f"✅ Embedder initialized with dimension: {embedder.dimension}")
    except Exception as e:
        print(f"❌ Failed to initialize embedder: {e}")
        return False

    try:
        # Test single vehicle embedding
        print("🔄 Testing single vehicle embedding...")
        embedding = embedder.embed_vehicle(
            brand="Toyota",
            model="Corolla",
            year=2020,
            description="sedan 4 puertas automatico"
        )
        print(f"✅ Single embedding shape: {embedding.shape}")
        print(f"✅ Embedding sample values: {embedding[:5]}")
    except Exception as e:
        print(f"❌ Failed single vehicle embedding: {e}")
        return False

    try:
        # Test batch embedding
        print("🔄 Testing batch embedding...")
        vehicles = [
            {"brand": "Toyota", "model": "Corolla", "year": 2020, "description": "sedan"},
            {"brand": "Honda", "model": "Civic", "year": 2019, "description": "hatchback"},
            {"brand": "Nissan", "model": "Sentra", "year": 2021, "description": "sedan"}
        ]

        embeddings = embedder.embed_batch(vehicles, batch_size=2)
        print(f"✅ Batch embeddings count: {len(embeddings)}")
        print(f"✅ First embedding shape: {embeddings[0].shape}")
    except Exception as e:
        print(f"❌ Failed batch embedding: {e}")
        return False

    try:
        # Test query embedding
        print("🔄 Testing query embedding...")
        query_embedding = embedder.embed_query("Toyota Corolla 2020 sedan")
        print(f"✅ Query embedding shape: {query_embedding.shape}")
    except Exception as e:
        print(f"❌ Failed query embedding: {e}")
        return False

    return True


def test_dependencies():
    """Test if required dependencies are available."""
    dependencies = {
        "sentence_transformers": "sentence-transformers",
        "torch": "PyTorch",
        "numpy": "NumPy"
    }

    print("🔄 Checking dependencies...")
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name} is available")
        except ImportError:
            print(f"❌ {name} is NOT available")
            return False

    return True


if __name__ == "__main__":
    print("🧪 Testing Embedding Functionality")
    print("=" * 50)

    # Test dependencies
    deps_ok = test_dependencies()
    print()

    if deps_ok:
        # Test embedder
        embedder_ok = test_embedder()
        print()

        if embedder_ok:
            print("🎉 All embedding tests passed!")
            print("✅ The embedding system is working properly.")
        else:
            print("❌ Embedding tests failed.")
            sys.exit(1)
    else:
        print("❌ Dependency tests failed.")
        print("💡 Try installing: pip install sentence-transformers torch")
        sys.exit(1)