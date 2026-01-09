"""
Base Agent - Classe base para todos os agentes especializados
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseAgent(ABC):
    """Classe base para agentes especializados"""

    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type

    @abstractmethod
    def can_handle(self, parsed_query: Dict[str, Any]) -> bool:
        """
        Determina se este agente pode processar a query

        Args:
            parsed_query: Query parseada com tipo, categoria, etc

        Returns:
            True se pode processar, False caso contrário
        """
        pass

    @abstractmethod
    def search(self, query: str, parsed_query: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Busca documentos relevantes para a query

        Args:
            query: Query original do utilizador
            parsed_query: Query parseada

        Returns:
            Lista de documentos ou None se não encontrar
        """
        pass

    @abstractmethod
    def filter(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> List[Dict]:
        """
        Filtra documentos baseado em regras específicas do agente

        Args:
            docs: Documentos retornados pela busca
            parsed_query: Query parseada

        Returns:
            Documentos filtrados
        """
        pass

    @abstractmethod
    def format_response(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> str:
        """
        Formata resposta de forma específica para este tipo de agente

        Args:
            docs: Documentos filtrados
            parsed_query: Query parseada

        Returns:
            Resposta formatada
        """
        pass

    def process(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pipeline completo de processamento

        Args:
            query: Query original
            parsed_query: Query parseada

        Returns:
            Resultado com resposta, fotos, metadata
        """
        # 1. Buscar documentos
        docs = self.search(query, parsed_query)

        # 2. Garantir que docs é lista válida
        if docs is None or not isinstance(docs, list):
            docs = []

        # 3. Filtrar documentos
        filtered_docs = self.filter(docs, parsed_query) if docs else []

        # 3. Formatar resposta (SEMPRE chamar, mesmo com lista vazia)
        # Isso permite que cada agente retorne mensagens personalizadas quando não há resultados
        response = self.format_response(filtered_docs, parsed_query)

        # 4. Extrair fotos do novo formato: "📷 FOTOGRAFIAS: 1. /path/to/photo.jpg"
        import re
        photos = []

        # Extrair fotos do novo formato numerado
        photo_matches = re.findall(r'^\s*\d+\.\s+([^\n]+)', response, re.MULTILINE)
        for match in photo_matches:
            # Verificar se é um caminho de foto (começa com / ou contém extensões de imagem)
            if match.startswith('/') or any(ext in match.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                photos.append(match.strip())

        # Também suportar o formato antigo para compatibilidade
        old_format_photos = re.findall(r'📷 Foto: ([^\n]+)', response)
        photos.extend(old_format_photos)

        # 5. Limpar resposta (remover seção de fotografias e linhas de foto antigas)
        # Remover seção "📷 FOTOGRAFIAS:" até a primeira linha vazia
        cleaned_response = re.sub(r'📷 FOTOGRAFIAS:.*?(?:\n\n|\Z)', '', response, flags=re.DOTALL).strip()
        # Remover formato antigo
        cleaned_response = re.sub(r'📷 Foto: [^\n]+\n*', '', cleaned_response).strip()

        return {
            'success': True,
            'response': cleaned_response,
            'photos': photos,
            'agent': self.agent_type,
            'metadata': {
                'docs_retrieved': len(docs) if docs else 0,
                'docs_after_filter': len(filtered_docs),
                'response_length': len(cleaned_response),
                'photos_count': len(photos)
            }
        }

    def get_info(self) -> Dict[str, str]:
        """Retorna informação sobre o agente"""
        return {
            'name': self.name,
            'type': self.agent_type,
            'description': self.__doc__ or 'No description'
        }
