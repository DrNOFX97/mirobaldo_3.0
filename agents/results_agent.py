"""
ResultsAgent - Agente especializado em resultados de jogos
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from agents.base_agent import BaseAgent


class ResultsAgent(BaseAgent):
    """Agente especializado em responder queries sobre resultados de jogos"""

    def __init__(self, search_func, base_path: str):
        super().__init__(name="Results Agent", agent_type="results")
        self.search_func = search_func
        self.base_path = Path(base_path)

    def can_handle(self, parsed_query: Dict[str, Any]) -> bool:
        """
        Processa queries sobre resultados de jogos

        Args:
            parsed_query: Deve conter 'is_result': True

        Returns:
            True se for query de resultado
        """
        return parsed_query.get('is_result', False)

    def search(self, query: str, parsed_query: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Busca resultados de jogos

        Prioriza:
        - Pasta /dados/resultados/
        - Documentos com época específica no path
        - Documentos com competição no path

        Args:
            query: Query original
            parsed_query: Deve conter 'season' e/ou 'competition' se detectados

        Returns:
            Lista de documentos ou None
        """
        opponent = parsed_query.get('opponent', '').lower()

        # SOLUÇÃO: Se query tem adversário específico, buscar MUITO MAIS documentos
        # para garantir que pegamos todas as épocas
        k_docs = 100 if opponent else 20

        results = self.search_func(query, k=k_docs)

        if not results:
            return None

        season = parsed_query.get('season') or ''  # Ex: "1989-90"
        competition = parsed_query.get('competition') or ''  # Ex: "taça", "campeonato"
        competition = competition.lower() if competition else ''
        opponent = parsed_query.get('opponent') or ''  # Ex: "benfica"
        opponent = opponent.lower() if opponent else ''

        # FILTRO AGRESSIVO: Se query é sobre adversário, REMOVER biografias e livros completamente
        if opponent:
            filtered_results = []
            for doc in results:
                if not isinstance(doc, dict):
                    continue
                metadata = doc.get('metadata', {})
                if not isinstance(metadata, dict):
                    doc['metadata'] = {}
                    metadata = {}
                file_path = metadata.get('file_path', '').lower()
                if '/biografias/' not in file_path and '/outros/' not in file_path:
                    filtered_results.append(doc)
            results = filtered_results

        for doc in results:
            # Garantir que doc tem estrutura correta
            if not isinstance(doc, dict):
                continue
            if 'metadata' not in doc:
                doc['metadata'] = {}

            file_path = doc.get('metadata', {}).get('file_path', '') or ''
            if not isinstance(file_path, str):
                file_path = ''
            file_path = file_path.lower()

            content = doc.get('content', '') or ''
            if not isinstance(content, str):
                content = str(content) if content else ''
            content = content.lower()

            # PENALIZAR FORTEMENTE ficheiros irrelevantes para resultados
            if '/biografias/' in file_path:
                doc['score'] = doc['score'] * 0.05  # Penalização 95%
            if '/historia/' in file_path or '/livros/' in file_path:
                doc['score'] = doc['score'] * 0.05  # Penalização 95%
            if '/outros/' in file_path:
                doc['score'] = doc['score'] * 0.01  # Penalização 99% para livros históricos

            # BOOST MASSIVO para /por_epoca/ (ficheiros de resultados organizados)
            if '/por_epoca/' in file_path:
                doc['score'] = min(doc['score'] * 10.0, 1.0)  # Multiplicar por 10!

            # Boost médio se estiver na pasta de resultados (ficheiros antigos)
            if '/resultados/' in file_path and '/por_epoca/' not in file_path:
                doc['score'] = min(doc['score'] + 0.30, 1.0)

            # Boost muito forte se tiver época exata no path ou conteúdo
            if season:
                season_normalized = season.replace('/', '-')
                if season_normalized in file_path:
                    doc['score'] = min(doc['score'] + 0.35, 1.0)
                elif season_normalized in content:
                    doc['score'] = min(doc['score'] + 0.15, 1.0)

            # Boost se tiver competição no path/conteúdo
            if competition and competition in (file_path + ' ' + content):
                doc['score'] = min(doc['score'] + 0.15, 1.0)

            # Boost FORTE se tiver adversário (query principal é sobre adversário)
            if opponent and opponent in content:
                doc['score'] = min(doc['score'] + 0.25, 1.0)  # Aumentado de 0.1 para 0.25

        # Re-ordenar por score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results

    def filter(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> List[Dict]:
        """
        Filtra documentos irrelevantes para resultados

        Rejeita:
        - Biografias longas sem resultados
        - Classificações finais
        - Documentos com score < 0.25
        - Documentos sem placares/resultados

        Args:
            docs: Documentos da busca
            parsed_query: Query parseada

        Returns:
            Documentos filtrados
        """
        filtered = []
        season = parsed_query.get('season') or ''
        competition = parsed_query.get('competition') or ''
        competition = competition.lower() if competition else ''
        opponent = parsed_query.get('opponent') or ''
        opponent = opponent.lower() if opponent else ''

        # REGRA ESPECIAL: Se tiver ficheiro em /por_epoca/ com época exata, usar SÓ esse
        if season:
            season_normalized = season.replace('/', '-')
            perfect_matches = [
                doc for doc in docs
                if '/resultados/por_epoca/' in doc.get('metadata', {}).get('file_path', '').lower()
                and season_normalized in doc.get('metadata', {}).get('file_path', '').lower()
            ]
            if perfect_matches:
                # Encontrou ficheiro perfeito em /resultados/por_epoca/YYYY-YY/
                # Usar SÓ esses, ignorar TODOS os outros (incluindo classificações)
                docs = perfect_matches

        for doc in docs:
            # Garantir estrutura correta do documento
            if not isinstance(doc, dict):
                continue
            if 'metadata' not in doc:
                doc['metadata'] = {}
            if 'score' not in doc:
                doc['score'] = 0.0

            content = doc.get('content', '') or ''
            if not isinstance(content, str):
                content = str(content) if content else ''
            content = content.lower()

            file_path = doc.get('metadata', {}).get('file_path', '') or ''
            if not isinstance(file_path, str):
                file_path = ''
            file_path = file_path.lower()

            score = doc.get('score', 0.0)
            if not isinstance(score, (int, float)):
                score = 0.0

            # Regra 1: Rejeitar scores muito baixos
            if score < 0.05:
                continue

            # Regra 2: Deve ter placar ou indicador de resultado
            if not self._has_match_result(content):
                continue

            # Regra 3: Rejeitar se for só tabela de classificação
            if self._is_only_classification(content):
                continue

            # Regra 4: Se tiver época, DEVE mencionar a época
            if season:
                season_patterns = [
                    season,
                    season.replace('/', '-'),
                    season.replace('-', '/'),
                    season.split('-')[0],  # Só o ano inicial
                ]
                if not any(sp in content for sp in season_patterns):
                    # Penalizar mas não rejeitar completamente
                    doc['score'] = doc['score'] * 0.6
                    if doc['score'] < 0.25:
                        continue

            # Regra 5: Boost se tiver competição mencionada
            if competition and competition in content:
                doc['score'] = min(doc['score'] + 0.1, 1.0)

            # Regra 6: Boost se tiver múltiplos resultados (pode ser calendário)
            match_count = len(re.findall(r'\d+\s*[-–]\s*\d+', content))
            if match_count >= 3:
                doc['score'] = min(doc['score'] + 0.05, 1.0)

            filtered.append(doc)

        # Re-ordenar e limitar
        filtered.sort(key=lambda x: x['score'], reverse=True)

        # SOLUÇÃO: Se query tem adversário, retornar MUITO MAIS documentos
        # para agregar todos os jogos históricos
        opponent = parsed_query.get('opponent', '')
        max_docs = 50 if opponent else 8

        return filtered[:max_docs]

    def format_response(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> str:
        """
        Formata resposta de resultados em HTML

        Formato:
        - Época e competição (se identificados)
        - Tabela HTML estilizada com resultados
        - Fotos (se disponíveis)

        Args:
            docs: Documentos filtrados
            parsed_query: Query parseada

        Returns:
            Resposta formatada em HTML
        """
        response_parts = []
        seen_content = set()
        total_chars = 0
        max_chars = 10000

        # Header com contexto
        season = parsed_query.get('season', '')
        competition = parsed_query.get('competition', '')
        opponent = parsed_query.get('opponent', '')

        # Preparar informação para o título da tabela
        # Passar época e competição separadamente para mostrá-las em linhas diferentes
        table_season = f"Época {season}" if season else None
        table_competition = competition.upper() if competition else None
        table_opponent = f"vs {opponent.title()}" if opponent else None

        # Track para evitar repetição de info
        seen_paragraphs = set()
        last_was_table = False

        for i, doc in enumerate(docs):
            content = doc.get('content', '')
            file_path = doc.get('metadata', {}).get('file_path', 'unknown')

            # Evitar duplicação
            content_hash = hash(content[:200])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # Limpar texto
            cleaned = self._clean_results_text(content)

            # Extrair parágrafos de resultados com seus subtítulos h3
            # Cada parágrafo/tabela pode ter seu próprio h3 antes dele
            paragraphs_with_titles = self._extract_paragraphs_with_titles(content)

            for para, h3_title in paragraphs_with_titles:
                # FILTRO LINHA A LINHA: Se adversário especificado, remover linhas irrelevantes
                if opponent:
                    para = self._filter_lines_by_opponent(para, opponent)
                    # Se parágrafo ficou vazio após filtragem, pular
                    if not para or len(para.strip()) < 20:
                        continue

                # Se for uma tabela de resultados (muitas linhas |), converter para HTML
                is_results_table = para.count('|') > 10

                # Parar se já ultrapassou limite (exceto se for tabela de resultados)
                if total_chars + len(para) > max_chars and not is_results_table:
                    break

                # Converter tabela markdown para HTML
                if is_results_table:
                    # Usar o subtítulo h3 específico desta tabela se existir, senão usar o parsed competition
                    comp_title = h3_title if h3_title else table_competition

                    para_html = self._markdown_table_to_html(
                        para,
                        'results-table',
                        season=table_season,
                        competition=comp_title,
                        opponent=table_opponent
                    )
                    last_was_table = True
                else:
                    # Remover títulos que já estão no header principal
                    if season and season in para and len(para) < 100:
                        # Provavelmente é título redundante como "Outros - Época 2024-25"
                        continue

                    # Evitar parágrafos duplicados
                    para_normalized = para.strip().lower()
                    if para_normalized in seen_paragraphs:
                        continue
                    seen_paragraphs.add(para_normalized)

                    # FILTRO LINHA A LINHA: Se adversário especificado, remover linhas irrelevantes
                    if opponent:
                        para = self._filter_lines_by_opponent(para, opponent)
                        # Se parágrafo ficou vazio após filtragem, pular
                        if not para or len(para.strip()) < 20:
                            continue

                    # Texto normal - converter para parágrafo HTML (geralmente resumo)
                    para_html = f'<p class="info-text">{para}</p>'

                    # Se é um resumo, adicionar separador DEPOIS dele
                    is_summary = '📊 Resumo:' in para or '**📊 Resumo:**' in para
                    if is_summary:
                        para_html += '<div class="section-divider"></div>'

                    last_was_table = False

                response_parts.append(para_html)
                total_chars += len(para_html)

                # Se for tabela de resultados, pode ultrapassar limite
                if is_results_table:
                    continue

            if total_chars >= max_chars:
                break

        if len(response_parts) <= 1:  # Só header ou vazio
            return '<p class="no-results">Desculpe, não encontrei resultados para essa época/competição.</p>'

        return '\n'.join(response_parts)

    # Métodos auxiliares privados

    def _markdown_table_to_html(self, markdown_table: str, table_class: str = '', season: str = None, competition: str = None, opponent: str = None) -> str:
        """
        Converte tabela markdown para HTML estilizado

        Args:
            markdown_table: Tabela em formato markdown
            table_class: Classe CSS para a tabela
            season: Época para mostrar no topo da tabela
            competition: Competição para mostrar abaixo da época
            opponent: Adversário (se aplicável)

        Returns:
            HTML da tabela
        """
        lines = [line.strip() for line in markdown_table.strip().split('\n') if line.strip()]

        if len(lines) < 2:
            return f'<p class="info-text">{markdown_table}</p>'

        # Primeira linha é o header
        header_line = lines[0]
        headers = [cell.strip() for cell in header_line.split('|') if cell.strip()]

        # Segunda linha é o separator (ignorar)
        # Linhas seguintes são dados
        data_lines = lines[2:] if len(lines) > 2 else []

        # Construir HTML
        html_parts = [f'<table class="{table_class}">']

        # Header
        html_parts.append('  <thead>')

        # Adicionar linhas de título (época, competição, adversário)
        # Cada uma em linha separada para melhor apresentação
        if season:
            html_parts.append('    <tr>')
            html_parts.append(f'      <th colspan="{len(headers)}" class="competition-title">{season}</th>')
            html_parts.append('    </tr>')

        if competition:
            html_parts.append('    <tr>')
            html_parts.append(f'      <th colspan="{len(headers)}" class="competition-title">{competition}</th>')
            html_parts.append('    </tr>')

        if opponent:
            html_parts.append('    <tr>')
            html_parts.append(f'      <th colspan="{len(headers)}" class="competition-title">{opponent}</th>')
            html_parts.append('    </tr>')

        html_parts.append('    <tr>')
        for header in headers:
            html_parts.append(f'      <th>{header}</th>')
        html_parts.append('    </tr>')
        html_parts.append('  </thead>')

        # Body
        html_parts.append('  <tbody>')
        for line in data_lines:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]

            # Ignorar linhas que são só separadores (-----, ===, etc)
            if cells and all(set(cell).issubset(set('-=:#')) for cell in cells):
                continue

            if cells:
                html_parts.append('    <tr>')
                for i, cell in enumerate(cells):
                    # Adicionar classes especiais para células com emojis de resultado
                    cell_class = ''
                    if '✅' in cell:
                        cell_class = ' class="win"'
                    elif '❌' in cell:
                        cell_class = ' class="loss"'
                    elif '➖' in cell:
                        cell_class = ' class="draw"'

                    html_parts.append(f'      <td{cell_class}>{cell}</td>')
                html_parts.append('    </tr>')
        html_parts.append('  </tbody>')
        html_parts.append('</table>')

        return '\n'.join(html_parts)

    def _has_match_result(self, content: str) -> bool:
        """Detecta se tem placar de jogo"""
        patterns = [
            r'\d+\s*[-–]\s*\d+',  # Placar: 2-1, 3 - 0
            r'farense\s+\d+.*\d+',
            r'vitória|empate|derrota',
            r'resultado.*:',
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in patterns)

    def _is_only_classification(self, content: str) -> bool:
        """Detecta se é apenas tabela de classificação sem resultados"""
        has_classification = any(ind in content.lower() for ind in [
            'classificação final',
            'pts | j | v | e | d',
            'posição | equipa'
        ])

        has_results = self._has_match_result(content)

        # É só classificação se tiver tabela mas não tiver resultados
        return has_classification and not has_results

    def _clean_results_text(self, text: str) -> str:
        """Limpa texto mantendo fotos"""
        # Converter imagens
        text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'📷 Foto: \2', text)
        text = re.sub(r'<img\s+src="([^"]+)"[^>]*>', r'📷 Foto: \1', text)
        # Remover headers markdown (###, ##, #) - QUALQUER posição, não só início de linha
        text = re.sub(r'#{1,6}\s+', '', text)
        # Remover separadores markdown
        text = re.sub(r'\s*[-=]{3,}\s*', '\n', text)
        # Remover bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        # Remover links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Limpar linhas vazias
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_result_paragraphs(self, text: str) -> List[str]:
        """
        Extrai parágrafos com resultados

        Prioriza:
        - Parágrafos com placares
        - Parágrafos com datas de jogos
        - Fotos de jogos
        """
        paragraphs = text.split('\n\n')
        good_paras = []

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            # SEMPRE incluir fotos
            if '📷 Foto:' in p:
                good_paras.append(p)
                continue

            # Incluir se tiver placar
            if re.search(r'\d+\s*[-–]\s*\d+', p):
                good_paras.append(p)
                continue

            # Incluir se tiver data de jogo
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', p):
                good_paras.append(p)
                continue

            # Incluir se tiver palavras-chave de resultado e for longo
            result_keywords = ['jornada', 'vitória', 'empate', 'derrota', 'golos']
            if any(kw in p.lower() for kw in result_keywords) and len(p) >= 80:
                good_paras.append(p)

        return good_paras

    def _extract_paragraphs_with_titles(self, text: str) -> List[tuple]:
        """
        Extrai parágrafos de resultados associados aos seus subtítulos h3

        Para competições com múltiplas fases, cada tabela tem seu próprio h3.
        Exemplo:
          ### II Divisão Fase Final 1939/1940
          (tabela 1)
          ### II Divisão Série Algarve 1939/1940
          (tabela 2)

        Returns:
            Lista de tuplas (parágrafo, h3_título)
        """
        # Dividir texto em blocos por h3
        # Estrutura: [h3_titulo, conteúdo_após_h3, h3_titulo, conteúdo_após_h3, ...]
        blocks = []
        current_h3 = None
        current_content = []

        for line in text.split('\n'):
            # Verificar se é um h3
            h3_match = re.match(r'###\s+(.+)', line)
            if h3_match:
                # Salvar bloco anterior se existir
                if current_content:
                    blocks.append((current_h3, '\n'.join(current_content)))
                # Iniciar novo bloco
                current_h3 = h3_match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        # Salvar último bloco
        if current_content:
            blocks.append((current_h3, '\n'.join(current_content)))

        # Agora extrair parágrafos de cada bloco
        result = []
        for h3_title, block_content in blocks:
            # Limpar e extrair parágrafos deste bloco
            cleaned = self._clean_results_text(block_content)
            paras = self._extract_result_paragraphs(cleaned)

            # Separar resumo (📊) das tabelas
            # Queremos: Tabela primeiro, depois resumo
            summary = None
            tables = []

            for para in paras:
                if '📊 Resumo:' in para or '**📊 Resumo:**' in para:
                    summary = para
                else:
                    tables.append(para)

            # Adicionar tabelas primeiro
            for table in tables:
                result.append((table, h3_title))

            # Depois adicionar resumo
            if summary:
                result.append((summary, h3_title))

        return result

    def _is_match_against_opponent(self, paragraph: str, opponent: str) -> bool:
        """
        Verifica se parágrafo é sobre um JOGO contra o adversário especificado

        Rejeita:
        - Biografias (menções a "carreira", "como jogador")
        - Menções a outros clubes (ex: "Sport Faro Benfica")
        - Parágrafos sem placares ou indicadores de jogo
        - Parágrafos muito longos (> 800 chars, provavelmente histórias)
        - Contexto irrelevante (ex: "melhor participação na Taça" quando a query é sobre adversário)

        Args:
            paragraph: Parágrafo a verificar
            opponent: Nome do adversário

        Returns:
            True se for sobre jogo contra o adversário
        """
        para_lower = paragraph.lower()
        opponent_lower = opponent.lower()

        # Verificar se menciona o adversário
        if opponent_lower not in para_lower:
            print(f"         ↳ Não menciona '{opponent}'")
            return False

        # REJEITAR se for biografia ou contexto irrelevante
        irrelevant_indicators = [
            'como jogador',
            'carreira',
            'sport faro benfica',  # Outro clube que contém "benfica"
            'passou pelo',
            'jogou no',
            'reservas do',
            'melhor participação',  # Contexto histórico genérico
            'contexto:',  # Parágrafos de contexto geral
            'tornou 1989/90',  # Menciona outra época
            'campeão da ii divisão',  # Contexto irrelevante
        ]
        if any(ind in para_lower for ind in irrelevant_indicators):
            print(f"         ↳ Rejeitado por indicador irrelevante")
            return False

        # REJEITAR se parágrafo for muito longo (provavelmente história/biografia)
        if len(paragraph) > 800:
            print(f"         ↳ Rejeitado por ser muito longo ({len(paragraph)} chars)")
            return False

        # REJEITAR se menciona adversário mas em lista genérica (sem contexto de jogo direto)
        # Ex: "SC Farense 1-0 FC Porto" numa lista onde Benfica não jogou
        lines = paragraph.split('\n')
        opponent_mentioned_in_match = False
        for line in lines:
            line_lower = line.lower()
            # Se linha menciona o adversário E tem placar, OK
            if opponent_lower in line_lower and re.search(r'\d+\s*[-–]\s*\d+', line):
                opponent_mentioned_in_match = True
                break
            # Se linha menciona o adversário em contexto de jogo (jornada, semifinal, etc)
            if opponent_lower in line_lower and any(kw in line_lower for kw in ['jornada', 'semifinal', 'final', 'quartos']):
                opponent_mentioned_in_match = True
                break

        # Se parágrafo menciona adversário mas não em nenhuma linha de jogo, rejeitar
        if not opponent_mentioned_in_match:
            print(f"         ↳ Rejeitado: '{opponent}' não mencionado em linha de jogo")
            return False

        # ACEITAR apenas se tiver indicadores de JOGO
        match_indicators = [
            re.search(r'\d+\s*[-–]\s*\d+', paragraph),  # Placar
            re.search(r'farense.*' + opponent_lower, para_lower),  # Farense vs opponent
            re.search(opponent_lower + r'.*farense', para_lower),  # opponent vs Farense
            'jornada' in para_lower,
            ' vs ' in para_lower or ' vs.' in para_lower,
            'semifinal' in para_lower or 'final' in para_lower or 'quartos' in para_lower,
        ]

        return any(match_indicators)

    def _filter_lines_by_opponent(self, paragraph: str, opponent: str) -> str:
        """
        Filtra linhas de um parágrafo, mantendo apenas as que mencionam o adversário

        Remove linhas de jogos contra outras equipas quando adversário especificado.

        Args:
            paragraph: Parágrafo completo
            opponent: Nome do adversário

        Returns:
            Parágrafo filtrado com apenas linhas relevantes
        """
        opponent_lower = opponent.lower()
        lines = paragraph.split('\n')
        filtered_lines = []

        for line in lines:
            line_lower = line.lower()

            # SEMPRE manter títulos/headers (curtos, sem placares)
            if len(line) < 80 and not re.search(r'\d+\s*[-–]\s*\d+', line):
                filtered_lines.append(line)
                continue

            # Se linha tem placar, só manter se menciona adversário
            if re.search(r'\d+\s*[-–]\s*\d+', line):
                if opponent_lower in line_lower:
                    filtered_lines.append(line)
                # Senão, pular linha (jogo contra outra equipa)
                continue

            # Linhas sem placar: manter se mencionam adversário OU são contexto geral
            if opponent_lower in line_lower or any(kw in line_lower for kw in ['classificação', 'qualificação', 'pontos']):
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)
