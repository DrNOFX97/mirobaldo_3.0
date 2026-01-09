"""
ClassificationAgent - Agente especializado em classificações
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from agents.base_agent import BaseAgent


class ClassificationAgent(BaseAgent):
    """Agente especializado em responder queries sobre classificações"""

    def __init__(self, search_func, base_path: str):
        super().__init__(name="Classification Agent", agent_type="classification")
        self.search_func = search_func
        self.base_path = Path(base_path)

    def can_handle(self, parsed_query: Dict[str, Any]) -> bool:
        """
        Processa queries sobre classificações

        Args:
            parsed_query: Deve conter 'is_classification': True

        Returns:
            True se for query de classificação
        """
        return parsed_query.get('is_classification', False)

    def search(self, query: str, parsed_query: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Busca classificações EXCLUSIVAMENTE em dados/classificacoes/por_epoca/
        
        Estratégia:
        1. Se época identificada: Lê diretamente o ficheiro da época
        2. Se não: Busca vectorial filtrada estritamente por path
        
        Args:
            query: Query original
            parsed_query: Deve conter 'season' se detectado
            
        Returns:
            Lista de documentos ou None
        """
        results = []
        season = parsed_query.get('season', '')  # Ex: "1994-95"
        
        # Caminho base para classificações por época
        # self.base_path é .../dados, então adicionamos o resto
        classificacoes_path = self.base_path / 'classificacoes' / 'por_epoca'
        
        # ESTRATÉGIA 1: Leitura Direta (se temos época)
        if season:
            season_normalized = season.replace('/', '-')
            season_dir = classificacoes_path / season_normalized
            
            if season_dir.exists() and season_dir.is_dir():
                # Ler todos os md/txt desta pasta
                for file_path in season_dir.glob('*'):
                    if file_path.suffix in ['.md', '.txt']:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            results.append({
                                'content': content,
                                'score': 1.0,  # Score máximo pois é match exato de época
                                'metadata': {
                                    'file_path': str(file_path),
                                    'epoca': season,
                                    'tipo': 'classificacao_direta'
                                }
                            })
                        except Exception as e:
                            print(f"Erro ao ler classificacao: {e}")
                            
        # Se encontrou por leitura direta, retorna imediatamente
        if results:
            return results

        # ESTRATÉGIA 2: Busca Vectorial Filtrada (Fallback ou sem época)
        # Buscar mais documentos para compensar a filtragem agressiva
        raw_results = self.search_func(query, k=50)
        
        if not raw_results:
            return None
            
        for doc in raw_results:
            file_path = doc.get('metadata', {}).get('file_path', '').lower()
            
            # FILTRO EXCLUSIVO: Só aceita ficheiros da pasta por_epoca
            if '/classificacoes/por_epoca/' not in file_path:
                continue
                
            # Se passou no filtro, adiciona
            # Boosts adicionais
            score = doc.get('score', 0)
            content = doc.get('content', '').lower()
            
            # Boost se tiver "classificação" no nome do ficheiro
            if 'classificacao' in file_path or 'classificação' in file_path:
                score = min(score + 0.20, 1.0)
                
            # Boost se tiver época exata (se existir season na query)
            if season:
                season_normalized = season.replace('/', '-')
                if season_normalized in file_path:
                    score = min(score + 0.3, 1.0)
            
            doc['score'] = score
            results.append(doc)

        # Re-ordenar por score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results if results else None

    def filter(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> List[Dict]:
        """
        Filtra documentos irrelevantes para classificações

        Rejeita:
        - Biografias
        - Resultados de jogo individual sem classificação
        - Documentos com score < 0.3
        - Documentos sem tabela classificativa

        Args:
            docs: Documentos da busca
            parsed_query: Query parseada

        Returns:
            Documentos filtrados
        """
        filtered = []
        season = parsed_query.get('season', '')

        for doc in docs:
            content = doc.get('content', '').lower()
            file_path = doc.get('metadata', {}).get('file_path', '').lower()
            score = doc.get('score', 0)

            # Regra 1: Rejeitar scores baixos
            if score < 0.3:
                continue

            # Regra 2: DEVE ter tabela classificativa
            if not self._has_classification_table(content):
                continue

            # Regra 3: Rejeitar biografias
            if '/biografias/' in file_path:
                continue

            # Regra 4: Se especificou época, deve estar presente
            if season:
                season_patterns = [
                    season,
                    season.replace('/', '-'),
                    season.replace('-', '/'),
                    season.split('-')[0],  # Ano inicial
                ]
                if not any(sp in content for sp in season_patterns):
                    doc['score'] = doc['score'] * 0.5
                    if doc['score'] < 0.3:
                        continue

            # Regra 5: Boost se tiver "classificação final"
            if 'classificação final' in content:
                doc['score'] = min(doc['score'] + 0.15, 1.0)

            # Regra 6: Boost se tiver posição do Farense mencionada
            if self._mentions_farense_position(content):
                doc['score'] = min(doc['score'] + 0.1, 1.0)

            filtered.append(doc)

        # Re-ordenar e limitar
        filtered.sort(key=lambda x: x['score'], reverse=True)
        return filtered[:5]

    def format_response(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> str:
        """
        Formata resposta de classificação em HTML

        Formato:
        - Época (se identificada)
        - Tabela HTML estilizada com classificação
        - Contexto sobre posição do Farense
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
        max_chars = 5000

        # Header com época
        season = parsed_query.get('season', '')
        if season:
            response_parts.append(f'<h2 class="season-header">CLASSIFICAÇÃO - Época {season}</h2>')

        # Criar padrões de época para validação
        season_patterns = []
        if season:
            season_patterns = [
                season,
                season.replace('/', '-'),
                season.replace('-', '/'),
                season.split('-')[0],  # Ano inicial (ex: "1994")
            ]

        for doc in docs:
            content = doc.get('content', '')

            # Evitar duplicação
            content_hash = hash(content[:200])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # Limpar texto
            cleaned = self._clean_classification_text(content)

            # Extrair parágrafos de classificação
            paragraphs = self._extract_classification_paragraphs(cleaned, season=season)

            for para in paragraphs:
                if total_chars + len(para) > max_chars:
                    break

                # VALIDAÇÃO RIGOROSA: Se tiver época especificada, rejeitar parágrafos de outras épocas
                if season and season_patterns:
                    para_lower = para.lower()

                    # Procurar menções de época no parágrafo
                    import re
                    epoch_mentions = re.findall(r'(\d{4}[-/]\d{2})', para)

                    if epoch_mentions:
                        # Se menciona época diferente, rejeitar
                        valid_epoch = any(epoch.replace('/', '-') == season.replace('/', '-')
                                         for epoch in epoch_mentions)
                        if not valid_epoch:
                            continue  # Pular este parágrafo

                # Se for tabela, converter para HTML
                is_table = para.count('|') > 5
                if is_table:
                    para = self._markdown_table_to_html(para, 'classification-table')
                else:
                    para = f'<p class="info-text">{para}</p>'

                response_parts.append(para)
                total_chars += len(para)

            if total_chars >= max_chars:
                break

        if len(response_parts) <= 1:  # Só header ou vazio
            return '<p class="no-results">Desculpe, não encontrei a classificação para essa época.</p>'

        return '\n'.join(response_parts)

    # Métodos auxiliares privados

    def _markdown_table_to_html(self, markdown_table: str, table_class: str = '') -> str:
        """
        Converte tabela markdown para HTML estilizado

        Args:
            markdown_table: Tabela em formato markdown
            table_class: Classe CSS para a tabela

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

        # Header com título da competição
        html_parts.append('  <thead>')

        # Se o primeiro header tem o nome da competição (ex: "Campeonato Nacional...")
        # Mostrar numa linha especial como caption/título
        if len(headers) == 1 or (len(headers) > 1 and len(headers[0]) > 30):
            # Primeira linha é um título (competição)
            competition_title = headers[0]

            # Se for só "📅 Época: XXXX-XX", tornar mais descritivo
            import re
            epoch_match = re.search(r'📅 Época:\s*(\d{4}[-/]\d{2})', competition_title)
            if epoch_match:
                season = epoch_match.group(1).replace('-', '/')
                competition_title = f'Campeonato Nacional da I Divisão {season}'

            html_parts.append('    <tr>')
            html_parts.append(f'      <th class="competition-title" colspan="10">{competition_title}</th>')
            html_parts.append('    </tr>')

            # Se houver mais headers (colunas da tabela), adicionar
            if len(headers) > 1:
                html_parts.append('    <tr>')
                for header in headers[1:]:
                    html_parts.append(f'      <th>{header}</th>')
                html_parts.append('    </tr>')
        else:
            # Headers normais (colunas)
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
                # Verificar se é linha do Farense para destacar
                is_farense = any('farense' in cell.lower() for cell in cells)
                row_class = ' class="farense-row"' if is_farense else ''

                html_parts.append(f'    <tr{row_class}>')
                for i, cell in enumerate(cells):
                    # Adicionar classe pos-1, pos-2, pos-3 à primeira célula se for posição 1, 2 ou 3
                    cell_class = ''
                    if i == 0:  # Primeira célula (posição)
                        if cell.strip() == '1':
                            cell_class = ' class="pos-1"'
                        elif cell.strip() == '2':
                            cell_class = ' class="pos-2"'
                        elif cell.strip() == '3':
                            cell_class = ' class="pos-3"'

                    html_parts.append(f'      <td{cell_class}>{cell}</td>')
                html_parts.append('    </tr>')
        html_parts.append('  </tbody>')
        html_parts.append('</table>')

        return '\n'.join(html_parts)

    def _has_classification_table(self, content: str) -> bool:
        """Detecta se tem tabela classificativa"""
        indicators = [
            r'classificação',
            r'pts.*\|.*j.*\|.*v',  # Pontos | Jogos | Vitórias
            r'posição.*equipa',
            r'\d+º.*farense',
            r'farense.*\d+\s+pts',
        ]
        return any(re.search(ind, content, re.IGNORECASE) for ind in indicators)

    def _mentions_farense_position(self, content: str) -> bool:
        """Detecta se menciona posição do Farense"""
        patterns = [
            r'\d+º.*farense',
            r'farense.*\d+º',
            r'farense.*posição',
            r'classificou.*\d+',
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in patterns)

    def _clean_classification_text(self, text: str) -> str:
        """Limpa texto PRESERVANDO tabelas e fotos"""
        # Converter imagens
        text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'📷 Foto: \2', text)
        text = re.sub(r'<img\s+src="([^"]+)"[^>]*>', r'📷 Foto: \1', text)

        # Remover headers markdown (###, ##, #) - converter para texto normal
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Remover separadores markdown (---, ===) - mesmo que não estejam sozinhos na linha
        text = re.sub(r'\s*[-=]{3,}\s*', '\n', text)

        # Remover bold/italic mantendo conteúdo
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remover links mas manter texto
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Limpar linhas vazias excessivas
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _extract_classification_paragraphs(self, text: str, season: str = '') -> List[str]:
        """
        Extrai parágrafos com classificação

        Prioriza:
        - Tabelas classificativas (com |)
        - Parágrafos mencionando posição
        - Fotos de equipas

        Args:
            text: Texto a processar
            season: Época específica (opcional, para filtrar parágrafos de outras épocas)
        """
        paragraphs = text.split('\n\n')
        good_paras = []
        seen_normalized = set()

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            # Remover linhas de título no início e fim do parágrafo
            lines = p.split('\n')
            cleaned_lines = []

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # Rejeitar linha se for só um título de seção (sem dados)
                # Ex: "Época 1994/1995 - MELHOR CLASSIFICAÇÃO DE SEMPRE"
                # Ex: "Classificações Recentes"
                # Ex: "I Divisão (Primeira Liga)"
                if len(line) < 100 and ':' not in line and '|' not in line:
                    # Verificar se parece título (curto, sem dados concretos)
                    seems_title = any(pattern in line.lower() for pattern in [
                        'época 19', 'época 20',
                        'classificações recentes',
                        'i divisão', 'ii divisão', 'primeira liga', 'segunda liga',
                        'melhor classificação', 'melhor de sempre'
                    ])
                    if seems_title:
                        continue

                cleaned_lines.append(line)

            # Reconstruir parágrafo sem linhas de título
            p = '\n'.join(cleaned_lines).strip()

            if not p:
                continue

            # Rejeitar títulos vazios ou muito curtos (< 30 chars) sem dados concretos
            if len(p) < 30 and not '📷 Foto:' in p:
                continue

            # Rejeitar se for apenas um título de seção (sem detalhes)
            if len(p) < 80 and p.count('\n') == 0:
                # Verificar se é só um título sem dados
                has_data = any(keyword in p.lower() for keyword in [
                    'pontos:', 'vitórias:', 'empates:', 'derrotas:',
                    'golos marcados:', 'treinador:', 'pts |', '|'
                ])
                if not has_data and not '📷 Foto:' in p:
                    continue

            # Evitar duplicação
            p_normalized = p.lower().strip()
            if p_normalized in seen_normalized:
                continue
            seen_normalized.add(p_normalized)

            # SEMPRE incluir fotos
            if '📷 Foto:' in p:
                good_paras.append(p)
                continue

            # Incluir se tiver tabela (múltiplas linhas com |)
            if p.count('|') >= 3:
                good_paras.append(p)
                continue

            # Incluir se mencionar classificação COM dados concretos
            if 'classificação' in p.lower() and len(p) >= 80:
                good_paras.append(p)
                continue

            # Incluir se mencionar posição do Farense COM contexto
            if self._mentions_farense_position(p) and len(p) >= 50:
                good_paras.append(p)
                continue

            # Incluir se tiver pontos/jogos (linha de tabela ou stats)
            if re.search(r'\d+\s+pts|\d+\s+jogos|\d+\s+vitórias', p, re.IGNORECASE):
                good_paras.append(p)

        return good_paras
