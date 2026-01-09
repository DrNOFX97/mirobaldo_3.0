"""
AgentRouter - Router para despachar queries aos agentes especializados
"""

import re
from typing import Dict, List, Any, Optional
from agents.biography_agent import BiographyAgent
from agents.results_agent import ResultsAgent
from agents.classification_agent import ClassificationAgent


class AgentRouter:
    """
    Router que analisa queries e despacha para o agente apropriado
    """

    def __init__(self, search_func, base_path: str):
        """
        Inicializa router e todos os agentes

        Args:
            search_func: Função de busca (smart_file_search)
            base_path: Caminho base dos dados
        """
        self.search_func = search_func
        self.base_path = base_path

        # Inicializar agentes
        self.agents = [
            BiographyAgent(search_func, base_path),
            ResultsAgent(search_func, base_path),
            ClassificationAgent(search_func, base_path),
        ]

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Analisa query para determinar tipo e extrair entidades

        Args:
            query: Query original do utilizador

        Returns:
            Dict com:
                - is_biography: bool
                - is_result: bool
                - is_classification: bool
                - player_name: str (se detectado)
                - season: str (se detectado, ex: "1994-95")
                - competition: str (se detectado)
                - opponent: str (se detectado)
        """
        query_lower = query.lower()

        parsed = {
            'is_biography': False,
            'is_result': False,
            'is_classification': False,
            'player_name': None,
            'season': None,
            'competition': None,
            'opponent': None,
        }

        # Detectar tipo de query

        # 1. BIOGRAFIA
        biography_patterns = [
            r'quem (foi|é|era)',
            r'biografia',
            r'história de',
            r'carreira de',
            r'jogador',
        ]
        if any(re.search(p, query_lower) for p in biography_patterns):
            parsed['is_biography'] = True
            # Extrair nome do jogador
            parsed['player_name'] = self._extract_player_name(query)

        # 2. CLASSIFICAÇÃO
        classification_patterns = [
            r'classificação',
            r'tabela',
            r'que lugar',
            r'que posição',
            r'classificou',
        ]
        if any(re.search(p, query_lower) for p in classification_patterns):
            parsed['is_classification'] = True

        # Extrair entidades comuns ANTES de decidir o tipo
        # (adversário pode indicar que é query de resultados)

        # Época (ex: 1994-95, 1994/95, 94-95)
        parsed['season'] = self._extract_season(query)

        # Competição
        parsed['competition'] = self._extract_competition(query)

        # Adversário
        parsed['opponent'] = self._extract_opponent(query)

        # 3. RESULTADO (se não for biografia nem classificação)
        result_patterns = [
            r'resultados?',  # resultado ou resultados
            r'jogos?',       # jogo ou jogos
            r'taça',
            r'campeonato',
            r'farense.*\d+.*\d+',  # Farense 2-1
            r'\d+\s*[-–]\s*\d+',   # 2-1
            r'mostra.*com',        # mostra resultados com
            r'contra',             # contra o benfica
        ]
        if any(re.search(p, query_lower) for p in result_patterns):
            if not parsed['is_classification']:  # Classificação tem prioridade
                parsed['is_result'] = True

        # Se detectou adversário, provavelmente é query de resultados
        if parsed['opponent'] and not parsed['is_biography'] and not parsed['is_classification']:
            parsed['is_result'] = True

        # Se nenhum tipo detectado, assumir resultado (fallback)
        if not any([parsed['is_biography'], parsed['is_result'], parsed['is_classification']]):
            parsed['is_result'] = True

        return parsed

    def route(self, query: str) -> Dict[str, Any]:
        """
        Roteia query para o agente apropriado

        Args:
            query: Query original

        Returns:
            Resultado do processamento:
            {
                'success': bool,
                'response': str,
                'photos': list,
                'agent': str,
                'metadata': dict
            }
        """
        # 1. Parsear query
        parsed_query = self.parse_query(query)

        # 2. Encontrar agente que pode processar
        selected_agent = None
        for agent in self.agents:
            if agent.can_handle(parsed_query):
                selected_agent = agent
                break

        if not selected_agent:
            return {
                'success': False,
                'error': 'Nenhum agente disponível para processar esta query',
                'agent': 'none'
            }

        # 3. Processar com agente selecionado
        try:
            result = selected_agent.process(query, parsed_query)
            # Garantir que metadata existe
            if 'metadata' not in result:
                result['metadata'] = {}
            # Adicionar info da query parseada ao metadata
            result['metadata']['parsed_query'] = parsed_query
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao processar query: {str(e)}',
                'agent': selected_agent.agent_type
            }

    def get_available_agents(self) -> List[Dict[str, str]]:
        """Retorna lista de agentes disponíveis"""
        return [agent.get_info() for agent in self.agents]

    # Métodos auxiliares de extração de entidades

    def _extract_player_name(self, query: str) -> Optional[str]:
        """
        Extrai nome de jogador da query

        Exemplos:
        - "quem foi paco fortes" → "paco fortes"
        - "biografia de hassan nader" → "hassan nader"
        """
        patterns = [
            r'quem (?:foi|é|era) ([a-záàâãéèêíïóôõöúçñ ]+)',
            r'biografia de ([a-záàâãéèêíïóôõöúçñ ]+)',
            r'história de ([a-záàâãéèêíïóôõöúçñ ]+)',
            r'carreira de ([a-záàâãéèêíïóôõöúçñ ]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                name = match.group(1).strip()
                # Limpar palavras comuns no final
                name = re.sub(r'\s+(no farense|farense|jogador)$', '', name)
                return name

        return None

    def _extract_season(self, query: str) -> Optional[str]:
        """
        Extrai época da query

        Exemplos:
        - "época 1994-95" → "1994-95"
        - "em 94/95" → "1994-95"
        - "temporada 2023-24" → "2023-24"
        """
        # Padrão: 4 dígitos seguidos de - ou / e 2-4 dígitos
        match = re.search(r'(\d{4})[-/](\d{2,4})', query)
        if match:
            year1 = match.group(1)
            year2 = match.group(2)
            # Normalizar para formato YYYY-YY
            if len(year2) == 2:
                return f"{year1}-{year2}"
            elif len(year2) == 4:
                return f"{year1}-{year2[-2:]}"

        # Padrão: 2 dígitos seguidos de - ou / e 2 dígitos
        match = re.search(r'(\d{2})[-/](\d{2})', query)
        if match:
            year1 = match.group(1)
            year2 = match.group(2)
            # Assumir século 20 se >= 50, senão 21
            full_year1 = f"19{year1}" if int(year1) >= 50 else f"20{year1}"
            return f"{full_year1}-{year2}"

        return None

    def _extract_competition(self, query: str) -> Optional[str]:
        """
        Extrai competição da query

        Exemplos:
        - "taça de portugal" → "taça"
        - "campeonato nacional" → "campeonato"
        """
        query_lower = query.lower()

        competitions = {
            'taça': ['taça', 'cup'],
            'campeonato': ['campeonato', 'liga', 'championship'],
            'supertaça': ['supertaça', 'supercup'],
            'uefa': ['uefa', 'europeia'],
        }

        for comp_name, keywords in competitions.items():
            if any(kw in query_lower for kw in keywords):
                return comp_name

        return None

    def _extract_opponent(self, query: str) -> Optional[str]:
        """
        Extrai adversário da query

        Exemplos:
        - "farense benfica" → "benfica"
        - "jogo contra o porto" → "porto"
        """
        query_lower = query.lower()

        # Lista de equipas comuns
        teams = [
            'benfica', 'porto', 'sporting', 'braga', 'vitória', 'guimarães',
            'boavista', 'marítimo', 'belenenses', 'nacional', 'estoril',
            'paços de ferreira', 'paços', 'académica', 'coimbra',
        ]

        for team in teams:
            if team in query_lower:
                # Evitar match com "farense"
                if team != 'farense':
                    return team

        # Padrão: "contra (o|a) X"
        match = re.search(r'contra (?:o|a) ([a-záàâãéèêíïóôõöúçñ ]+)', query_lower)
        if match:
            opponent = match.group(1).strip()
            # Limpar palavras comuns
            opponent = re.sub(r'\s+(em|no|na)$', '', opponent)
            return opponent

        return None
