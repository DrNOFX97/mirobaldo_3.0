"""
RAG System for Farense Chatbot
Implementa vector store, embedding generation e retrieval logic
"""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Tuple
import pickle
import logging
import warnings
import os

# Suprimir warnings de protobuf (não críticos, apenas ruído)
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*MessageFactory.*')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # TensorFlow warnings

from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """Sistema RAG completo com FAISS vector store e Sentence Transformers embeddings"""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Inicializa o sistema RAG

        Args:
            model_name: Modelo de embedding (multilíngue, suporta português)
        """
        logger.info(f"Carregando modelo de embedding: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Vector store e metadata
        self.index = None  # FAISS index
        self.documents = []  # Lista de documentos
        self.metadata = []  # Metadata associada
        self.id_to_doc_idx = {}  # Mapping ID -> índice documento

        logger.info(f"Dimensão de embedding: {self.embedding_dim}")

    def load_jsonl_data(self, file_path: str) -> List[Dict]:
        """Carrega dados de arquivo JSONL"""
        documents = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        documents.append(json.loads(line))
            logger.info(f"Carregados {len(documents)} documentos de {file_path}")
        except Exception as e:
            logger.error(f"Erro ao carregar {file_path}: {e}")
        return documents

    def load_text_data(self, directory: str) -> List[Dict]:
        """Carrega dados de arquivos .txt e .md em um diretório"""
        documents = []
        try:
            path = Path(directory)
            for file_path in path.rglob('*.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Divide em chunks se muito grande
                    chunks = self._chunk_text(content, max_chunk_size=500)
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            'text': chunk,
                            'source': str(file_path),
                            'chunk_id': i,
                            'metadata': {'type': 'text_file', 'source_file': file_path.name}
                        })
                except Exception as e:
                    logger.warning(f"Erro ao ler {file_path}: {e}")

            for file_path in path.rglob('*.md'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    chunks = self._chunk_text(content, max_chunk_size=500)
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            'text': chunk,
                            'source': str(file_path),
                            'chunk_id': i,
                            'metadata': {'type': 'markdown_file', 'source_file': file_path.name}
                        })
                except Exception as e:
                    logger.warning(f"Erro ao ler {file_path}: {e}")

            logger.info(f"Carregados {len(documents)} documentos de {directory}")
        except Exception as e:
            logger.error(f"Erro ao carregar textos de {directory}: {e}")
        return documents

    def _chunk_text(self, text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Divide texto em chunks com sobreposição"""
        sentences = text.split('.')
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence = sentence.strip() + '.'
            if current_size + len(sentence) > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Sobreposição: manter últimas frases
                current_chunk = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk
                current_size = sum(len(s) for s in current_chunk)
            current_chunk.append(sentence)
            current_size += len(sentence)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return [c for c in chunks if c.strip()]

    def build_index(self, data_sources: List[Dict]) -> None:
        """
        Constrói o índice FAISS a partir de múltiplas fontes de dados

        Args:
            data_sources: Lista de dicts com 'type', 'path' e opcionalmente 'params'
                         Exemplo: {'type': 'jsonl', 'path': '/path/to/file.jsonl'}
                                  {'type': 'directory', 'path': '/path/to/dir'}
        """
        all_documents = []

        # Carregar dados de todas as fontes
        for source in data_sources:
            if source['type'] == 'jsonl':
                docs = self.load_jsonl_data(source['path'])
                # Converter para formato padronizado
                for doc in docs:
                    all_documents.append({
                        'text': doc.get('prompt', '') + ' ' + doc.get('completion', ''),
                        'source': source['path'],
                        'metadata': {
                            'type': 'qa_pair',
                            'prompt': doc.get('prompt', ''),
                            'completion': doc.get('completion', ''),
                            'original_metadata': doc.get('metadata', {})
                        }
                    })
            elif source['type'] == 'directory':
                docs = self.load_text_data(source['path'])
                all_documents.extend(docs)

        if not all_documents:
            logger.error("Nenhum documento carregado!")
            return

        logger.info(f"Total de documentos carregados: {len(all_documents)}")
        self.documents = all_documents

        # Gerar embeddings
        logger.info("Gerando embeddings...")
        texts = [doc['text'] for doc in self.documents]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype(np.float32)

        # Criar índice FAISS
        logger.info("Criando índice FAISS...")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings)

        # Guardar metadata
        self.metadata = [doc['metadata'] for doc in self.documents]

        logger.info(f"Índice construído com {self.index.ntotal} documentos")

    def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """
        Recupera os k documentos mais relevantes para uma query

        Args:
            query: Pergunta do utilizador
            k: Número de documentos a retornar

        Returns:
            Lista de documentos relevantes com scores
        """
        if self.index is None:
            logger.error("Índice não foi construído!")
            return []

        # Gerar embedding da query
        query_embedding = self.embedding_model.encode([query])[0].astype(np.float32)
        query_embedding = np.array([query_embedding])

        # Buscar documentos
        distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                doc = self.documents[idx]
                results.append({
                    'text': doc['text'],
                    'source': doc.get('source', 'unknown'),
                    'metadata': self.metadata[idx],
                    'score': float(distances[0][i]),  # L2 distance (menor é melhor)
                    'relevance': 1 / (1 + distances[0][i])  # Normalizar para [0,1]
                })

        return results

    def save(self, save_dir: str) -> None:
        """Salva o índice e metadata"""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        if self.index is not None:
            faiss.write_index(self.index, str(save_path / 'rag_index.faiss'))
            logger.info(f"Índice FAISS salvo em {save_path / 'rag_index.faiss'}")

        with open(save_path / 'documents.pkl', 'wb') as f:
            pickle.dump(self.documents, f)

        with open(save_path / 'metadata.pkl', 'wb') as f:
            pickle.dump(self.metadata, f)

        logger.info(f"RAG system salvo em {save_path}")

    def load(self, save_dir: str) -> None:
        """Carrega o índice e metadata"""
        save_path = Path(save_dir)

        try:
            self.index = faiss.read_index(str(save_path / 'rag_index.faiss'))

            with open(save_path / 'documents.pkl', 'rb') as f:
                self.documents = pickle.load(f)

            with open(save_path / 'metadata.pkl', 'rb') as f:
                self.metadata = pickle.load(f)

            logger.info(f"RAG system carregado de {save_path}")
        except Exception as e:
            logger.error(f"Erro ao carregar RAG system: {e}")


def initialize_rag(data_dir: str = "/Users/f.nuno/Desktop/chatbot_2.0",
                   cache_dir: str = "/Users/f.nuno/Desktop/chatbot_2.0/backend/rag_cache") -> RAGSystem:
    """
    Função helper para inicializar o RAG system
    Tenta carregar do cache, se não existir, constrói novo
    """
    rag = RAGSystem()
    cache_path = Path(cache_dir)

    # Tentar carregar do cache
    if cache_path.exists() and (cache_path / 'rag_index.faiss').exists():
        logger.info("Carregando RAG system do cache...")
        try:
            rag.load(cache_dir)
            return rag
        except Exception as e:
            logger.warning(f"Falha ao carregar cache: {e}. Construindo novo...")

    # Construir novo índice
    logger.info("Construindo novo índice RAG...")
    data_sources = [
        {'type': 'jsonl', 'path': f'{data_dir}/LLM_training/data/farense_dataset_v3_final_complete.jsonl'},
        {'type': 'jsonl', 'path': f'{data_dir}/LLM_training/data/biografias_qa.jsonl'},
        {'type': 'jsonl', 'path': f'{data_dir}/LLM_training/data/livros_qa_consolidated.jsonl'},
        {'type': 'jsonl', 'path': f'{data_dir}/LLM_training/data/installations_qa.jsonl'},
        {'type': 'directory', 'path': f'{data_dir}/dados/'},
    ]

    rag.build_index(data_sources)
    rag.save(cache_dir)

    return rag


if __name__ == '__main__':
    # Test
    rag = initialize_rag()

    # Exemplo de query
    query = "Qual foi o resultado do Farense contra a Associação Académica?"
    results = rag.retrieve(query, k=5)

    print(f"\nQuery: {query}")
    print(f"\nTop {len(results)} resultados:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. (Relevance: {result['relevance']:.2%})")
        print(f"   Texto: {result['text'][:200]}...")
        print(f"   Fonte: {result['source']}")
