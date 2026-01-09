"""
Hybrid RAG System - BM25 + FAISS
Combina keyword search (BM25) com semantic search (FAISS)
Sem custos, funciona offline, muito melhor qualidade que FAISS puro
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
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# Suprimir warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*MessageFactory.*')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRAGSystem:
    """
    Sistema RAG Híbrido que combina:
    - BM25: Keyword search (procura por palavras exatas)
    - FAISS: Semantic search (procura por similaridade semântica)

    Score final = 0.4 * BM25_score + 0.6 * FAISS_score
    """

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 bm25_weight: float = 0.4, faiss_weight: float = 0.6):
        """
        Args:
            model_name: Modelo de embedding
            bm25_weight: Peso do BM25 (0.4 = 40%)
            faiss_weight: Peso do FAISS (0.6 = 60%)
        """
        logger.info(f"Carregando modelo de embedding: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Vector store
        self.index = None  # FAISS index
        self.documents = []  # Lista de documentos originais
        self.texts = []  # Textos processados (para retrieve)
        self.metadata = []  # Metadata associada

        # BM25
        self.bm25 = None  # BM25 instance
        self.texts_tokenized = []  # Textos tokenizados para BM25

        # Pesos
        self.bm25_weight = bm25_weight
        self.faiss_weight = faiss_weight

        logger.info(f"Dimensão de embedding: {self.embedding_dim}")
        logger.info(f"Pesos: BM25={bm25_weight}, FAISS={faiss_weight}")

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
                    chunks = self._chunk_text(content, max_chunk_size=500)
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            'text': chunk,
                            'source': str(file_path),
                            'chunk_id': i,
                            'metadata': {
                                'type': 'text_file',
                                'source_file': file_path.name,
                                'file_path': str(file_path)
                            }
                        })
                except Exception as e:
                    logger.warning(f"Erro ao ler {file_path}: {e}")

            for file_path in path.rglob('*.md'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    chunks = self._chunk_text(content, max_chunk_size=3000)
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            'text': chunk,
                            'source': str(file_path),
                            'chunk_id': i,
                            'metadata': {
                                'type': 'markdown_file',
                                'source_file': file_path.name,
                                'file_path': str(file_path)
                            }
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
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_size = len(sentence.split())

            if current_size + sentence_size > max_chunk_size and current_chunk:
                # Finalizar chunk atual
                chunk_text = '. '.join(current_chunk) + '.'
                chunks.append(chunk_text)

                # Overlap: manter últimas N palavras
                overlap_sentences = []
                overlap_words = 0
                for s in reversed(current_chunk):
                    s_words = len(s.split())
                    if overlap_words + s_words <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_words += s_words
                    else:
                        break

                current_chunk = overlap_sentences
                current_size = overlap_words

            current_chunk.append(sentence)
            current_size += sentence_size

        # Finalizar último chunk
        if current_chunk:
            chunk_text = '. '.join(current_chunk) + '.'
            chunks.append(chunk_text)

        return [c for c in chunks if len(c.strip()) > 10]

    def build_index(self, data_sources: List[Dict]) -> None:
        """Constrói índice FAISS + BM25"""
        logger.info("Construindo novo índice RAG híbrido...")

        # Carregar dados
        self.documents = []
        for source in data_sources:
            source_type = source['type']
            path = source['path']

            if source_type == 'jsonl':
                docs = self.load_jsonl_data(path)
            elif source_type == 'directory':
                docs = self.load_text_data(path)
            else:
                continue

            self.documents.extend(docs)

        if not self.documents:
            logger.error("Nenhum documento foi carregado!")
            return

        # Preparar textos - extrair text corretamente
        texts = []
        valid_documents = []

        for doc in self.documents:
            # Procurar chave 'text', 'passage', 'content', ou combinar campos
            if 'text' in doc:
                text = doc['text']
            elif 'passage' in doc:
                text = doc['passage']
            elif 'content' in doc:
                text = doc['content']
            elif 'response' in doc and 'question' in doc:
                # JSONL format: Q&A
                text = f"{doc['question']} {doc['response']}"
            else:
                # Tenta usar primeiro valor string significativo
                text = next((v for v in doc.values() if isinstance(v, str) and len(v) > 20), None)

            if text and len(text.strip()) > 10:
                texts.append(text)
                valid_documents.append(doc)

        self.documents = valid_documents
        self.texts = texts  # Guardar textos processados para retrieve
        logger.info(f"Total de documentos válidos: {len(texts)}")

        # BM25: Tokenizar e criar índice
        logger.info("Criando índice BM25...")
        self.texts_tokenized = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(self.texts_tokenized)
        logger.info("Índice BM25 criado ✓")

        # FAISS: Gerar embeddings e criar índice
        logger.info("Gerando embeddings para FAISS...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype(np.float32)

        logger.info("Criando índice FAISS...")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings)
        logger.info(f"Índice FAISS criado com {len(texts)} documentos ✓")

        # Metadata
        self.metadata = [doc.get('metadata', {}) for doc in self.documents]

    def retrieve(self, query: str, k: int = 5, bm25_k: int = 100) -> List[Dict]:
        """
        Retrieval híbrido: BM25 + FAISS

        Args:
            query: Query do utilizador
            k: Documentos a retornar
            bm25_k: Documentos intermediários do BM25

        Returns:
            Lista de documentos ordenados por score híbrido
        """
        if self.index is None:
            logger.error("Índice não foi construído!")
            return []

        results = {}

        # ===== BM25 SEARCH =====
        # Tokenizar query
        query_tokens = query.lower().split()

        # BM25 search (retorna top bm25_k)
        bm25_scores = self.bm25.get_scores(query_tokens)
        top_bm25_indices = np.argsort(-bm25_scores)[:bm25_k]

        # Normalizar scores BM25 para [0, 1]
        max_bm25_score = max(bm25_scores[top_bm25_indices]) if len(top_bm25_indices) > 0 else 1.0
        if max_bm25_score == 0:
            max_bm25_score = 1.0

        for idx in top_bm25_indices:
            bm25_normalized = float(bm25_scores[idx]) / max_bm25_score
            if bm25_normalized > 0:
                results[int(idx)] = {
                    'bm25_score': bm25_normalized,
                    'faiss_score': 0.0,
                    'hybrid_score': 0.0
                }

        # ===== FAISS SEARCH =====
        # Gerar embedding da query
        query_embedding = self.embedding_model.encode([query])[0].astype(np.float32)
        query_embedding = np.array([query_embedding])

        # FAISS search
        distances, indices = self.index.search(query_embedding, k=bm25_k)

        # Normalizar scores FAISS para [0, 1]
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                distance = float(distances[0][i])
                faiss_normalized = 1.0 / (1.0 + distance)

                idx = int(idx)
                if idx not in results:
                    results[idx] = {
                        'bm25_score': 0.0,
                        'faiss_score': 0.0,
                        'hybrid_score': 0.0
                    }
                results[idx]['faiss_score'] = faiss_normalized

        # ===== COMBINAR SCORES =====
        for idx in results:
            bm25_s = results[idx]['bm25_score']
            faiss_s = results[idx]['faiss_score']
            hybrid = self.bm25_weight * bm25_s + self.faiss_weight * faiss_s
            results[idx]['hybrid_score'] = hybrid

        # ===== ORDENAR E RETORNAR =====
        sorted_results = sorted(results.items(), key=lambda x: x[1]['hybrid_score'], reverse=True)

        final_results = []
        for idx, scores in sorted_results[:k]:
            doc = self.documents[idx]
            text = self.texts[idx] if idx < len(self.texts) else doc.get('text', '')
            final_results.append({
                'text': text,
                'source': doc.get('source', 'unknown'),
                'metadata': self.metadata[idx] if idx < len(self.metadata) else {},
                'bm25_score': scores['bm25_score'],
                'faiss_score': scores['faiss_score'],
                'relevance': scores['hybrid_score'],  # Score final
                'score': scores['hybrid_score']
            })

        return final_results

    def save(self, save_dir: str) -> None:
        """Salva os índices e metadata"""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        if self.index is not None:
            faiss.write_index(self.index, str(save_path / 'rag_index.faiss'))
            logger.info(f"Índice FAISS salvo ✓")

        with open(save_path / 'documents.pkl', 'wb') as f:
            pickle.dump(self.documents, f)

        with open(save_path / 'texts.pkl', 'wb') as f:
            pickle.dump(self.texts, f)

        with open(save_path / 'metadata.pkl', 'wb') as f:
            pickle.dump(self.metadata, f)

        with open(save_path / 'bm25.pkl', 'wb') as f:
            pickle.dump(self.bm25, f)

        with open(save_path / 'texts_tokenized.pkl', 'wb') as f:
            pickle.dump(self.texts_tokenized, f)

        logger.info(f"RAG system salvo em {save_path}")

    def load(self, save_dir: str) -> None:
        """Carrega os índices e metadata"""
        save_path = Path(save_dir)

        try:
            self.index = faiss.read_index(str(save_path / 'rag_index.faiss'))

            with open(save_path / 'documents.pkl', 'rb') as f:
                self.documents = pickle.load(f)

            with open(save_path / 'texts.pkl', 'rb') as f:
                self.texts = pickle.load(f)

            with open(save_path / 'metadata.pkl', 'rb') as f:
                self.metadata = pickle.load(f)

            with open(save_path / 'bm25.pkl', 'rb') as f:
                self.bm25 = pickle.load(f)

            with open(save_path / 'texts_tokenized.pkl', 'rb') as f:
                self.texts_tokenized = pickle.load(f)

            logger.info(f"RAG system carregado ✓")
        except Exception as e:
            logger.error(f"Erro ao carregar RAG system: {e}")


def initialize_hybrid_rag(data_dir: str = "/Users/f.nuno/Desktop/chatbot_2.0",
                         cache_dir: str = "/Users/f.nuno/Desktop/chatbot_2.0/backend/rag_cache_hybrid") -> HybridRAGSystem:
    """
    Função helper para inicializar o RAG híbrido
    Tenta carregar do cache, se não existir, constrói novo
    """
    rag = HybridRAGSystem()
    cache_path = Path(cache_dir)

    # Tentar carregar do cache
    if cache_path.exists() and (cache_path / 'rag_index.faiss').exists():
        logger.info("Carregando RAG hybrid do cache...")
        try:
            rag.load(cache_dir)
            return rag
        except Exception as e:
            logger.warning(f"Falha ao carregar cache: {e}. Construindo novo...")

    # Construir novo índice
    logger.info("Construindo novo índice RAG hybrid...")
    data_sources = [
        {'type': 'jsonl', 'path': f"{data_dir}/LLM_training/data/farense_dataset_v3_final_complete.jsonl"},
        {'type': 'jsonl', 'path': f"{data_dir}/LLM_training/data/biografias_qa.jsonl"},
        {'type': 'jsonl', 'path': f"{data_dir}/LLM_training/data/livros_qa_consolidated.jsonl"},
        {'type': 'jsonl', 'path': f"{data_dir}/LLM_training/data/installations_qa.jsonl"},
        {'type': 'directory', 'path': f"{data_dir}/dados"},
    ]

    rag.build_index(data_sources)
    rag.save(cache_dir)

    return rag
