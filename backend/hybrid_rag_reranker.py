"""
Hybrid RAG System com Cross-Encoder Re-ranking
Otimizado para Apple M1 (MPS)

Pipeline:
1. BM25 + FAISS → top 20 candidatos (rápido, ~200ms)
2. Cross-Encoder → re-rank top 20 (preciso, ~100ms no M1)
3. Retornar top k finais (melhor qualidade)

Ganho esperado: +15-20% precisão
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
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch

# Suprimir warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*MessageFactory.*')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRAGReranker:
    """
    Sistema RAG Híbrido com Cross-Encoder Re-ranking

    Stage 1: BM25 + FAISS (0.4 + 0.6) → top 20 candidatos
    Stage 2: Cross-Encoder re-rank → top k finais

    Otimizado para Apple M1 com MPS
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",  # Leve para M1
        bm25_weight: float = 0.4,
        faiss_weight: float = 0.6,
        use_reranker: bool = True
    ):
        """
        Args:
            embedding_model: Modelo bi-encoder para retrieval
            reranker_model: Modelo cross-encoder para re-ranking
            bm25_weight: Peso BM25 no stage 1
            faiss_weight: Peso FAISS no stage 1
            use_reranker: Se True, usa cross-encoder (mais lento mas melhor)
        """
        # Detectar device (M1 usa MPS)
        if torch.backends.mps.is_available():
            self.device = "mps"
            logger.info("🚀 Usando Apple M1 GPU (MPS)")
        elif torch.cuda.is_available():
            self.device = "cuda"
            logger.info("🚀 Usando CUDA GPU")
        else:
            self.device = "cpu"
            logger.info("⚠️  Usando CPU (mais lento)")

        # Embedding model (bi-encoder)
        logger.info(f"Carregando bi-encoder: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_model.to(self.device)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Cross-encoder (re-ranker)
        self.use_reranker = use_reranker
        self.reranker = None

        if use_reranker:
            logger.info(f"Carregando cross-encoder: {reranker_model}")
            self.reranker = CrossEncoder(reranker_model, device=self.device)
            logger.info("✅ Cross-encoder carregado (re-ranking ativado)")
        else:
            logger.info("⚠️  Re-ranking desativado (apenas BM25 + FAISS)")

        # Vector store
        self.index = None  # FAISS index
        self.documents = []
        self.texts = []
        self.metadata = []

        # BM25
        self.bm25 = None
        self.texts_tokenized = []

        # Pesos stage 1
        self.bm25_weight = bm25_weight
        self.faiss_weight = faiss_weight

        logger.info(f"Dimensão embedding: {self.embedding_dim}")
        logger.info(f"Pesos Stage 1: BM25={bm25_weight}, FAISS={faiss_weight}")

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
        """Carrega dados de arquivos .txt e .md"""
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
                    logger.error(f"Erro ao ler {file_path}: {e}")

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
                            'metadata': {
                                'type': 'markdown_file',
                                'source_file': file_path.name,
                                'file_path': str(file_path)
                            }
                        })
                except Exception as e:
                    logger.error(f"Erro ao ler {file_path}: {e}")

            logger.info(f"Carregados {len(documents)} documentos de {directory}")
        except Exception as e:
            logger.error(f"Erro ao processar diretório {directory}: {e}")
        return documents

    def _chunk_text(self, text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Divide texto em chunks com overlap"""
        sentences = [s.strip() + '.' for s in text.split('.') if len(s.strip()) > 10]

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence.split())

            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunk_text = '. '.join(current_chunk) + '.'
                chunks.append(chunk_text)

                # Overlap
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

        if current_chunk:
            chunk_text = '. '.join(current_chunk) + '.'
            chunks.append(chunk_text)

        return [c for c in chunks if len(c.strip()) > 10]

    def build_index(self, data_sources: List[Dict]) -> None:
        """Constrói índice FAISS + BM25"""
        logger.info("Construindo índice RAG híbrido com re-ranking...")

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

        # Preparar textos
        texts = []
        valid_documents = []

        for doc in self.documents:
            text = doc.get('text') or doc.get('passage') or doc.get('content')
            if not text:
                question = doc.get('question', '')
                answer = doc.get('answer', '')
                if question and answer:
                    text = f"{question} {answer}"

            if text and len(text.strip()) > 10:
                texts.append(text)
                valid_documents.append(doc)

        self.documents = valid_documents
        self.texts = texts

        logger.info(f"Total de documentos válidos: {len(texts)}")

        # BM25
        logger.info("Criando índice BM25...")
        self.texts_tokenized = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(self.texts_tokenized)
        logger.info("✅ BM25 criado")

        # FAISS
        logger.info("Gerando embeddings (usando MPS)...")
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            device=self.device
        )
        embeddings = np.array(embeddings).astype(np.float32)

        logger.info("Criando índice FAISS...")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings)
        logger.info(f"✅ FAISS criado com {len(texts)} documentos")

        self.metadata = [doc.get('metadata', {}) for doc in self.documents]

    def retrieve(self, query: str, k: int = 5, stage1_k: int = 20) -> List[Dict]:
        """
        Retrieval híbrido com re-ranking

        Args:
            query: Query do utilizador
            k: Documentos finais a retornar
            stage1_k: Candidatos para stage 1 (BM25+FAISS)

        Returns:
            Lista de documentos re-ranked
        """
        if self.index is None:
            logger.error("Índice não construído!")
            return []

        # ===== STAGE 1: BM25 + FAISS =====
        results = {}

        # BM25 search
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)
        top_bm25_indices = np.argsort(-bm25_scores)[:stage1_k * 2]  # Buscar mais para diversidade

        max_bm25 = max(bm25_scores[top_bm25_indices]) if len(top_bm25_indices) > 0 else 1.0
        if max_bm25 == 0:
            max_bm25 = 1.0

        for idx in top_bm25_indices:
            bm25_norm = float(bm25_scores[idx]) / max_bm25
            if bm25_norm > 0:
                results[int(idx)] = {
                    'bm25_score': bm25_norm,
                    'faiss_score': 0.0,
                    'hybrid_score': 0.0
                }

        # FAISS search
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
        query_embedding = np.array([query_embedding])

        distances, indices = self.index.search(query_embedding, k=stage1_k * 2)

        for i, idx in enumerate(indices[0]):
            if idx != -1:
                distance = float(distances[0][i])
                faiss_norm = 1.0 / (1.0 + distance)

                idx = int(idx)
                if idx not in results:
                    results[idx] = {
                        'bm25_score': 0.0,
                        'faiss_score': 0.0,
                        'hybrid_score': 0.0
                    }
                results[idx]['faiss_score'] = faiss_norm

        # Calcular hybrid score
        for idx, scores in results.items():
            hybrid = (self.bm25_weight * scores['bm25_score'] +
                     self.faiss_weight * scores['faiss_score'])
            results[idx]['hybrid_score'] = hybrid

        # Top stage1_k candidatos
        sorted_results = sorted(results.items(), key=lambda x: x[1]['hybrid_score'], reverse=True)
        top_candidates = sorted_results[:stage1_k]

        # ===== STAGE 2: CROSS-ENCODER RE-RANKING =====
        if self.use_reranker and self.reranker and len(top_candidates) > 0:
            logger.debug(f"Re-ranking {len(top_candidates)} candidatos com cross-encoder...")

            # Preparar pares (query, documento)
            pairs = [(query, self.texts[idx]) for idx, _ in top_candidates]

            # Re-rank com cross-encoder (usa MPS automaticamente)
            rerank_scores = self.reranker.predict(pairs, show_progress_bar=False)

            # Combinar com resultados
            reranked = []
            for i, (idx, stage1_scores) in enumerate(top_candidates):
                reranked.append({
                    'idx': idx,
                    'rerank_score': float(rerank_scores[i]),
                    'stage1_score': stage1_scores['hybrid_score'],
                    'bm25_score': stage1_scores['bm25_score'],
                    'faiss_score': stage1_scores['faiss_score']
                })

            # Ordenar por rerank_score
            reranked.sort(key=lambda x: x['rerank_score'], reverse=True)
            final_results = reranked[:k]

        else:
            # Sem re-ranking, usar hybrid score
            final_results = [
                {
                    'idx': idx,
                    'rerank_score': scores['hybrid_score'],
                    'stage1_score': scores['hybrid_score'],
                    'bm25_score': scores['bm25_score'],
                    'faiss_score': scores['faiss_score']
                }
                for idx, scores in top_candidates[:k]
            ]

        # Formatar output
        output = []
        for result in final_results:
            idx = result['idx']
            output.append({
                'text': self.texts[idx],
                'score': result['rerank_score'],
                'metadata': self.metadata[idx],
                'source': self.documents[idx].get('source', 'unknown'),
                'scores_detail': {
                    'rerank': result['rerank_score'],
                    'stage1_hybrid': result['stage1_score'],
                    'bm25': result['bm25_score'],
                    'faiss': result['faiss_score']
                }
            })

        return output

    def save_index(self, cache_dir: str) -> None:
        """Salvar índice em disco"""
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Salvar FAISS
        faiss.write_index(self.index, str(cache_path / "faiss.index"))

        # Salvar outros componentes
        with open(cache_path / "rag_data.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'texts': self.texts,
                'metadata': self.metadata,
                'texts_tokenized': self.texts_tokenized,
            }, f)

        logger.info(f"✅ Índice salvo em {cache_dir}")

    def load_index(self, cache_dir: str) -> bool:
        """Carregar índice do disco"""
        cache_path = Path(cache_dir)

        if not (cache_path / "faiss.index").exists():
            return False

        try:
            # Carregar FAISS
            self.index = faiss.read_index(str(cache_path / "faiss.index"))

            # Carregar outros componentes
            with open(cache_path / "rag_data.pkl", 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.texts = data['texts']
                self.metadata = data['metadata']
                self.texts_tokenized = data['texts_tokenized']

            # Reconstruir BM25
            self.bm25 = BM25Okapi(self.texts_tokenized)

            logger.info(f"✅ Índice carregado de {cache_dir} ({len(self.texts)} docs)")
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar índice: {e}")
            return False


def initialize_hybrid_rag_reranker(force_rebuild: bool = False) -> HybridRAGReranker:
    """
    Inicializa RAG com re-ranking (singleton com cache)

    Args:
        force_rebuild: Se True, reconstrói índice mesmo se cache existir
    """
    cache_dir = "backend/rag_cache_reranker"

    # Criar instância
    rag = HybridRAGReranker(
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        bm25_weight=0.4,
        faiss_weight=0.6,
        use_reranker=True
    )

    # Tentar carregar cache
    if not force_rebuild and rag.load_index(cache_dir):
        logger.info("✅ RAG carregado do cache")
        return rag

    # Construir índice
    logger.info("Construindo novo índice...")
    data_sources = [
        {'type': 'jsonl', 'path': 'LLM_training/data/farense_dataset_v3.jsonl'},
        {'type': 'directory', 'path': 'dados/biografias'},
        {'type': 'directory', 'path': 'dados/outros'},
    ]

    rag.build_index(data_sources)
    rag.save_index(cache_dir)

    return rag
