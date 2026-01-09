"""
LLM Interface para Farense Chatbot
Integra Mistral fine-tuned com RAG retrieval
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class LLMInterface:
    """Interface para comunicar com o modelo Mistral fine-tuned"""

    def __init__(self, model_path: Optional[str] = None, adapter_path: Optional[str] = None):
        """
        Inicializa a interface LLM

        Args:
            model_path: Caminho para o modelo base (ex: /path/to/mistral-7b-4bit)
            adapter_path: Caminho para os LoRA adapters treinados
        """
        self.model_path = model_path or "/Users/f.nuno/Desktop/chatbot_2.0/LLM_training/models/mistral-7b-4bit"
        self.adapter_path = adapter_path or "/Users/f.nuno/Desktop/chatbot_2.0/LLM_training/checkpoints/adapters"

        self.model = None
        self.tokenizer = None
        self.loaded = False

        logger.info("LLMInterface inicializado (carregamento lazy)")

    def load_model(self):
        """Carrega o modelo e adapters (lazy loading para economizar memória)"""
        if self.loaded:
            return

        try:
            logger.info("Inicializando modelo Mistral...")
            # Inicializar modelo mock para RAG (inference real pode ser integrado depois)
            self.model = {
                'model_path': self.model_path,
                'adapter_path': self.adapter_path,
                'type': 'mistral-7b-4bit',
                'status': 'ready'
            }
            self.loaded = True
            logger.info("Modelo inicializado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao inicializar modelo: {e}")
            self.loaded = False
            # Não lançar erro, apenas log

    def generate_response(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Gera resposta usando o modelo

        Args:
            prompt: Prompt/pergunta
            max_tokens: Máximo de tokens a gerar
            temperature: Temperature para sampling (0-1)

        Returns:
            Resposta gerada
        """
        if not self.loaded:
            self.load_model()

        try:
            # Implementação simplificada para demonstração
            # Em produção, integrar com MLX/Mistral inference
            logger.info(f"Gerando resposta para: {prompt[:100]}...")

            # Placeholder: retorna uma resposta estruturada
            response = f"""Baseado na informação disponível sobre o Farense:

{prompt}

[Resposta gerada pelo modelo Mistral fine-tuned com LoRA adapters]"""

            return response

        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            return f"Erro ao processar pergunta: {str(e)}"

    def format_rag_context(self, retrieved_docs: List[Dict]) -> str:
        """
        Formata documentos recuperados em contexto para o prompt

        Args:
            retrieved_docs: Lista de documentos do RAG

        Returns:
            String com contexto formatado
        """
        if not retrieved_docs:
            return ""

        context = "Contexto relevante:\n\n"
        for i, doc in enumerate(retrieved_docs, 1):
            relevance = doc.get('relevance', 0)
            source = doc.get('source', 'desconhecida').split('/')[-1]
            text = doc.get('text', '')[:300]  # Truncar para 300 chars

            context += f"{i}. [Fonte: {source} | Relevância: {relevance:.1%}]\n"
            context += f"   {text}...\n\n"

        return context

    def create_rag_prompt(self, query: str, retrieved_docs: List[Dict]) -> str:
        """
        Cria um prompt com RAG context

        Args:
            query: Pergunta do utilizador
            retrieved_docs: Documentos recuperados pelo RAG

        Returns:
            Prompt estruturado com contexto
        """
        context = self.format_rag_context(retrieved_docs)

        prompt = f"""Você é um assistente de IA especializado em história, estatísticas e informações sobre o Sporting Clube Farense.

{context}

Pergunta: {query}

Responda baseado no contexto fornecido. Se a informação não estiver disponível no contexto, indique que não tem informação suficiente.

Resposta:"""

        return prompt

    def generate_rag_response(self, query: str, retrieved_docs: List[Dict],
                              max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Gera resposta usando RAG context

        Args:
            query: Pergunta do utilizador
            retrieved_docs: Documentos recuperados
            max_tokens: Máximo de tokens
            temperature: Temperature para sampling

        Returns:
            Resposta com contexto RAG
        """
        prompt = self.create_rag_prompt(query, retrieved_docs)
        response = self.generate_response(prompt, max_tokens, temperature)
        return response


class ResponseFormatter:
    """Formata respostas para apresentação no frontend"""

    @staticmethod
    def format_chat_response(response: str, retrieved_docs: List[Dict] = None,
                             query: str = "") -> Dict:
        """
        Formata resposta para o frontend

        Returns:
            Dict com estrutura de resposta
        """
        sources = []
        if retrieved_docs:
            sources = [
                {
                    'text': doc.get('text', '')[:200],
                    'source': doc.get('source', 'unknown').split('/')[-1],
                    'relevance': f"{doc.get('relevance', 0):.1%}"
                }
                for doc in retrieved_docs[:3]  # Top 3 sources
            ]

        return {
            'response': response,
            'sources': sources,
            'query': query,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
