"""
Adaptive RAG System - Escolhe automaticamente entre re-ranking ou não
Otimizado para Apple M1

Decisão baseada no tipo de query:
- Biografias / Perguntas complexas → Com re-ranking (melhor qualidade)
- Resultados / Classificações → Sem re-ranking (mais rápido)
"""

import logging
import re
from typing import List, Dict, Optional
from hybrid_rag_system import HybridRAGSystem
from hybrid_rag_reranker import HybridRAGReranker

logger = logging.getLogger(__name__)


class AdaptiveRAGSystem:
    """
    Sistema RAG Adaptativo que escolhe automaticamente:
    - Re-ranking ON: queries complexas, biografias, semânticas
    - Re-ranking OFF: queries simples, keyword-based, estruturadas

    Otimizado para M1 com MPS
    """

    def __init__(self, force_mode: Optional[str] = None):
        """
        Args:
            force_mode: 'rerank', 'fast', ou None (auto)
        """
        self.force_mode = force_mode

        # Sistemas RAG
        self.rag_fast = None  # Sem re-ranking (39ms)
        self.rag_rerank = None  # Com re-ranking (488ms)

        # Padrões para detecção
        self._compile_patterns()

        logger.info(f"🤖 Adaptive RAG inicializado (modo: {force_mode or 'auto'})")

    def _compile_patterns(self):
        """Compila padrões regex para detecção de tipo de query"""

        # Queries que PRECISAM re-ranking (complexas, semânticas)
        self.rerank_patterns = [
            r'\bquem (foi|é|era)\b',  # "quem foi hassan", "quem é paco"
            r'\bcomo\b',  # "como jogava", "como foi"
            r'\bporque\b',  # "porque saiu"
            r'\bqualidades\b',
            r'\bestilo\b',
            r'\bcarreira\b',
            r'\bhistória\b',
            r'\bperfil\b',
            r'\bbiografia\b',
            r'\bconte[- ]me\b',
            r'\bexplica\b',
            r'\bdescreve\b',
            r'\bfale sobre\b',
            r'\bo que (aconteceu|passou)\b',
        ]

        # Queries que NÃO precisam re-ranking (estruturadas, keyword)
        self.fast_patterns = [
            r'\bresultado(s)?\s+(época|temporada|jogo)\b',  # "resultados época 2023"
            r'\bclassificação\b',  # "classificação 1ª liga"
            r'\bépoca\s+\d{4}',  # "época 2023/24"
            r'\bjogo\s+\d+',  # "jogo 15"
            r'\bjornada\s+\d+',  # "jornada 20"
            r'\b\d+-\d+\b',  # "3-1", "2023/24"
            r'\btabela\b',
            r'\bgolos\s+(marcados|sofridos)\b',
            r'\bvitórias\s+derrotas\b',
        ]

    def _should_use_reranking(self, query: str) -> bool:
        """
        Decide se deve usar re-ranking baseado na query

        Args:
            query: Query do utilizador

        Returns:
            True se deve usar re-ranking, False caso contrário
        """
        query_lower = query.lower()

        # Verificar padrões de re-ranking
        for pattern in self.rerank_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"✅ Re-ranking ON: padrão '{pattern}' encontrado")
                return True

        # Verificar padrões fast
        for pattern in self.fast_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"⚡ Re-ranking OFF: padrão '{pattern}' encontrado")
                return False

        # Default: se query tem >10 palavras ou ? → usar re-ranking
        word_count = len(query_lower.split())
        has_question = '?' in query

        if word_count > 10 or has_question:
            logger.info(f"✅ Re-ranking ON: query longa ({word_count} palavras) ou interrogação")
            return True

        # Default: fast (sem re-ranking)
        logger.info(f"⚡ Re-ranking OFF: query simples/curta")
        return False

    def _get_rag_fast(self) -> HybridRAGSystem:
        """Lazy load RAG sem re-ranking"""
        if self.rag_fast is None:
            logger.info("Carregando RAG rápido (sem re-ranking)...")

            from hybrid_rag_system import initialize_hybrid_rag
            self.rag_fast = initialize_hybrid_rag()

            logger.info("✅ RAG rápido carregado")

        return self.rag_fast

    def _get_rag_rerank(self) -> HybridRAGReranker:
        """Lazy load RAG com re-ranking"""
        if self.rag_rerank is None:
            logger.info("Carregando RAG com re-ranking...")

            from hybrid_rag_reranker import initialize_hybrid_rag_reranker
            self.rag_rerank = initialize_hybrid_rag_reranker()

            logger.info("✅ RAG re-ranking carregado")

        return self.rag_rerank

    def retrieve(self, query: str, k: int = 5, **kwargs) -> tuple[List[Dict], Dict]:
        """
        Retrieval adaptativo

        Args:
            query: Query do utilizador
            k: Número de documentos a retornar
            **kwargs: Argumentos extras (force_rerank, etc.)

        Returns:
            (documentos, metadata_decisao)
        """
        # Decisão: usar re-ranking ou não?
        if self.force_mode == 'rerank':
            use_rerank = True
            decision_reason = "Forçado: sempre re-ranking"
        elif self.force_mode == 'fast':
            use_rerank = False
            decision_reason = "Forçado: sempre rápido"
        elif kwargs.get('force_rerank') is not None:
            use_rerank = kwargs['force_rerank']
            decision_reason = f"Overridden por parâmetro: {use_rerank}"
        else:
            use_rerank = self._should_use_reranking(query)
            decision_reason = "Decisão automática baseada em padrões"

        # Executar retrieval
        import time
        start = time.time()

        if use_rerank:
            rag = self._get_rag_rerank()
            results = rag.retrieve(query, k=k, stage1_k=20)
            method = "rerank"
        else:
            rag = self._get_rag_fast()
            results = rag.retrieve(query, k=k)
            method = "fast"

        elapsed_ms = (time.time() - start) * 1000

        # Metadata da decisão
        metadata = {
            'method': method,
            'use_reranking': use_rerank,
            'decision_reason': decision_reason,
            'latency_ms': round(elapsed_ms, 1),
            'num_results': len(results)
        }

        logger.info(f"🎯 Retrieval: {method} | {elapsed_ms:.0f}ms | {len(results)} docs")

        return results, metadata


def initialize_adaptive_rag(force_mode: Optional[str] = None) -> AdaptiveRAGSystem:
    """
    Inicializa sistema RAG adaptativo

    Args:
        force_mode: 'rerank', 'fast', ou None (auto)

    Returns:
        AdaptiveRAGSystem instance
    """
    return AdaptiveRAGSystem(force_mode=force_mode)
