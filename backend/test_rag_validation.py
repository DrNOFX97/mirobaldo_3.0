"""
Test script for RAG validation (Phase 2)
Validates chunking, retrieval, and reranking
"""

import logging
import json
from pathlib import Path
from hybrid_rag_system import HybridRAGSystem

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_chunking():
    """Test 1: Validate chunking"""
    print("\n" + "="*60)
    print("TEST 1: CHUNKING VALIDATION")
    print("="*60)

    rag = HybridRAGSystem()

    # Test chunking with sample text
    sample_text = """
    António Gago foi um jogador histórico do Farense.
    Nasceu em Faro em 1945. Jogou pelo Farense entre 1965 e 1975.
    Foi um dos melhores marcadores da história do clube.
    Marcou mais de 100 golos pela equipa principal.
    Depois de se reformar, tornou-se treinador.
    """ * 20  # Repetir para criar texto maior

    chunks = rag._chunk_text(sample_text, max_chunk_size=100, overlap=20)

    print(f"\n📊 Chunking Results:")
    print(f"   - Input text length: {len(sample_text.split())} words")
    print(f"   - Number of chunks: {len(chunks)}")
    print(f"   - Chunk sizes: {[len(c.split()) for c in chunks]}")

    print(f"\n📝 Sample chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n   Chunk {i+1} ({len(chunk.split())} words):")
        print(f"   {chunk[:150]}...")

    return len(chunks) > 0

def test_biography_loading():
    """Test 2: Load and chunk biographies"""
    print("\n" + "="*60)
    print("TEST 2: BIOGRAPHY LOADING & CHUNKING")
    print("="*60)

    # Check if biography directory exists
    bio_dir = Path("../data/chatbot_dados/biografias")

    if not bio_dir.exists():
        print(f"❌ Biography directory not found: {bio_dir}")
        return False

    print(f"✅ Biography directory found: {bio_dir}")

    # Count biography files
    bio_files = list(bio_dir.glob("*.txt")) + list(bio_dir.glob("*.md"))
    print(f"📚 Found {len(bio_files)} biography files")

    if len(bio_files) == 0:
        print("⚠️  No biography files found!")
        return False

    # Sample a few biographies
    print(f"\n📝 Sample biographies:")
    for bio_file in bio_files[:5]:
        size = bio_file.stat().st_size
        print(f"   - {bio_file.name} ({size} bytes)")

    # Load and chunk biographies
    rag = HybridRAGSystem()
    documents = rag.load_text_data(str(bio_dir))

    print(f"\n📊 Loading Results:")
    print(f"   - Total documents/chunks: {len(documents)}")

    if len(documents) > 0:
        print(f"\n📝 Sample document structure:")
        sample = documents[0]
        print(f"   - Text length: {len(sample['text'])} chars")
        print(f"   - Source: {sample.get('source', 'N/A')}")
        print(f"   - Chunk ID: {sample.get('chunk_id', 'N/A')}")
        print(f"   - Metadata: {sample.get('metadata', {})}")
        print(f"\n   Text preview:")
        print(f"   {sample['text'][:200]}...")

    return len(documents) > 0

def test_rag_retrieval():
    """Test 3: RAG retrieval"""
    print("\n" + "="*60)
    print("TEST 3: RAG RETRIEVAL")
    print("="*60)

    bio_dir = Path("../data/chatbot_dados/biografias")

    if not bio_dir.exists():
        print(f"❌ Biography directory not found")
        return False

    try:
        # Initialize RAG system
        print("🔧 Initializing RAG system...")
        rag = HybridRAGSystem()

        # Build index
        print("🏗️  Building index...")
        data_sources = [
            {
                'type': 'directory',
                'path': str(bio_dir)
            }
        ]
        rag.build_index(data_sources)

        # Test queries
        test_queries = [
            "Quem foi António Gago?",
            "Qual foi a carreira de António Gago?",
            "Jogadores históricos do Farense"
        ]

        print(f"\n🔍 Testing retrieval with {len(test_queries)} queries:")

        for i, query in enumerate(test_queries, 1):
            print(f"\n   Query {i}: '{query}'")
            results = rag.retrieve(query, k=3)

            print(f"   Retrieved {len(results)} documents:")
            for j, result in enumerate(results, 1):
                score = result.get('score', 0.0)
                preview = result['text'][:100].replace('\n', ' ')
                print(f"      {j}. Score: {score:.3f} | {preview}...")

        return True

    except Exception as e:
        logger.error(f"❌ RAG retrieval test failed: {e}", exc_info=True)
        return False

def main():
    """Run all RAG validation tests"""
    print("\n" + "="*60)
    print("RAG SYSTEM VALIDATION - PHASE 2")
    print("="*60)

    results = {
        'chunking': test_chunking(),
        'biography_loading': test_biography_loading(),
        'rag_retrieval': test_rag_retrieval()
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All RAG validation tests PASSED!")
        print("✅ Phase 2 complete - RAG system is working correctly")
    else:
        print("\n⚠️  Some tests FAILED - review results above")

    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
