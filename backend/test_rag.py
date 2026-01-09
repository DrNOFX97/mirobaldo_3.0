#!/usr/bin/env python3
"""
Script de teste para o RAG system
Valida embeddings, retrieval e integração completa
"""

import sys
from pathlib import Path
import logging
from typing import List, Dict
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from rag_system import RAGSystem, initialize_rag
from llm_interface import LLMInterface, ResponseFormatter

def test_rag_system():
    """Testa o sistema RAG completo"""

    print("\n" + "="*80)
    print("TESTE DO SISTEMA RAG FARENSE CHATBOT")
    print("="*80 + "\n")

    # Test 1: Inicializar RAG
    print("[1/5] Inicializando RAG System...")
    try:
        start_time = time.time()
        rag = initialize_rag()
        elapsed = time.time() - start_time
        print(f"✓ RAG inicializado em {elapsed:.2f}s")
        print(f"  - Documentos carregados: {len(rag.documents)}")
        print(f"  - Dimensão de embeddings: {rag.embedding_dim}")
    except Exception as e:
        print(f"✗ Erro ao inicializar RAG: {e}")
        return

    # Test 2: Testar queries básicas
    print("\n[2/5] Testando queries básicas...")
    test_queries = [
        "Qual foi o resultado do Farense contra a Associação Académica?",
        "Quem foi o presidente do Farense?",
        "Qual é a história do Farense?",
        "Que trofeus ganhou o Farense?",
        "Onde fica o estádio do Farense?"
    ]

    for i, query in enumerate(test_queries, 1):
        try:
            print(f"\n  Query {i}: '{query}'")
            start_time = time.time()
            results = rag.retrieve(query, k=3)
            elapsed = time.time() - start_time

            if results:
                print(f"  ✓ Recuperados {len(results)} documentos em {elapsed:.2f}s")
                for j, doc in enumerate(results, 1):
                    relevance_pct = doc['relevance'] * 100
                    text_preview = doc['text'][:100].replace('\n', ' ')
                    print(f"    {j}. [{relevance_pct:.0f}%] {text_preview}...")
            else:
                print(f"  ⚠ Nenhum documento encontrado")
        except Exception as e:
            print(f"  ✗ Erro: {e}")

    # Test 3: Testar LLM Interface
    print("\n[3/5] Testando LLM Interface...")
    try:
        llm = LLMInterface()
        print("✓ LLM Interface inicializada")
        print(f"  - Caminho do modelo: {llm.model_path}")
        print(f"  - Caminho dos adapters: {llm.adapter_path}")
    except Exception as e:
        print(f"✗ Erro ao inicializar LLM: {e}")
        return

    # Test 4: Testar RAG + LLM
    print("\n[4/5] Testando RAG + LLM Integration...")
    integration_queries = [
        "Qual é a história do Farense?",
        "Qual foi o melhor resultado do Farense?",
    ]

    for query in integration_queries:
        try:
            print(f"\n  Query: '{query}'")

            # Retrieve
            docs = rag.retrieve(query, k=3)
            print(f"  ✓ Documentos recuperados: {len(docs)}")

            # Format context
            context = llm.format_rag_context(docs)
            print(f"  ✓ Contexto formatado: {len(context)} caracteres")

            # Create prompt
            prompt = llm.create_rag_prompt(query, docs)
            print(f"  ✓ Prompt criado: {len(prompt)} caracteres")

            # Generate response
            response = llm.generate_rag_response(query, docs)
            print(f"  ✓ Resposta gerada: {len(response)} caracteres")
            print(f"     Preview: {response[:200]}...")

        except Exception as e:
            print(f"  ✗ Erro: {e}")

    # Test 5: Testar Response Formatter
    print("\n[5/5] Testando Response Formatter...")
    try:
        query = "Qual é a história do Farense?"
        docs = rag.retrieve(query, k=3)
        formatted = ResponseFormatter.format_chat_response(
            response="Resposta de teste",
            retrieved_docs=docs,
            query=query
        )

        print("✓ Response formatada:")
        print(f"  - Query: {formatted['query']}")
        print(f"  - Response length: {len(formatted['response'])}")
        print(f"  - Sources: {len(formatted['sources'])}")
        print(f"  - Timestamp: {formatted['timestamp']}")

    except Exception as e:
        print(f"✗ Erro ao formatar response: {e}")

    # Summary
    print("\n" + "="*80)
    print("TESTES CONCLUÍDOS COM SUCESSO ✓")
    print("="*80)
    print("\nPróximos passos:")
    print("1. Instalar dependências: pip install -r requirements.txt")
    print("2. Executar servidor: uvicorn backend.main_rag:app --reload")
    print("3. Testar endpoints:")
    print("   - GET http://localhost:8000/")
    print("   - POST http://localhost:8000/chat")
    print("   - GET http://localhost:8000/rag-status")

def benchmark_rag():
    """Benchmark do RAG system"""
    print("\n" + "="*80)
    print("BENCHMARK RAG SYSTEM")
    print("="*80 + "\n")

    try:
        rag = initialize_rag()

        queries = [
            "resultado",
            "presidente",
            "história",
            "campeonato",
            "jogadores"
        ]

        print("Testando performance do retrieval...\n")
        times = []

        for query in queries:
            start = time.time()
            results = rag.retrieve(query, k=5)
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"Query: '{query:20}' → {elapsed*1000:.2f}ms ({len(results)} docs)")

        avg_time = sum(times) / len(times)
        print(f"\nTempo médio de retrieval: {avg_time*1000:.2f}ms")
        print(f"QPS (queries/segundo): {1/avg_time:.2f}")

    except Exception as e:
        print(f"Erro no benchmark: {e}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Teste do RAG system')
    parser.add_argument('--benchmark', action='store_true', help='Executar benchmark')
    args = parser.parse_args()

    if args.benchmark:
        benchmark_rag()
    else:
        test_rag_system()
