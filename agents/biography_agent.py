"""
BiographyAgent - Agente especializado em biografias de jogadores
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from agents.base_agent import BaseAgent


class BiographyAgent(BaseAgent):
    """Agente especializado em responder queries sobre biografias de jogadores"""

    def __init__(self, search_func, base_path: str):
        super().__init__(name="Biography Agent", agent_type="biography")
        self.search_func = search_func  # smart_file_search
        self.base_path = Path(base_path)

    def can_handle(self, parsed_query: Dict[str, Any]) -> bool:
        """
        Processa queries de tipo biografia

        Args:
            parsed_query: Deve conter 'is_biography': True

        Returns:
            True se for query de biografia
        """
        return parsed_query.get('is_biography', False)

    def search(self, query: str, parsed_query: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Busca biografias EXCLUSIVAMENTE na pasta /dados/biografias/jogadores/

        REGRA RÍGIDA: Apenas documentos dessa pasta são considerados válidos.
        Qualquer outro documento é ignorado.

        Args:
            query: Query original
            parsed_query: Query parseada com 'player_name' se detectado

        Returns:
            Lista de documentos da pasta de biografias ou None
        """
        player_name = parsed_query.get('player_name', '').lower()

        # Buscar com RAG (k=50 para apanhar nomes comuns como "Almeida" que aparecem noutros docs)
        results = self.search_func(query, k=50)

        if not results:
            return None

        # FILTRO ABSOLUTO: Apenas documentos de /biografias/jogadores/
        biography_docs = []

        for doc in results:
            file_path = doc.get('metadata', {}).get('file_path', '').lower()

            # REJEITAR qualquer documento fora da pasta de biografias
            if '/biografias/jogadores/' not in file_path:
                continue

            # Boost se tiver nome do jogador no path
            if player_name and player_name in file_path:
                doc['score'] = min(doc['score'] + 0.2, 1.0)

            biography_docs.append(doc)

        # Se temos player_name mas nenhum dos docs tem o nome no path, tentar busca direta
        # (para nomes comuns como "Almeida" onde RAG retorna biografias de outros jogadores)
        if player_name:
            has_player_in_path = any(player_name in doc.get('metadata', {}).get('file_path', '').lower()
                                    for doc in biography_docs)

            if not has_player_in_path:
                filename_docs = self._search_by_filename(player_name)
                if filename_docs:
                    # SUBSTITUIR os docs do RAG pelos docs encontrados por filename (mais precisos)
                    biography_docs = filename_docs

        if not biography_docs:
            return None

        # Re-ordenar por score
        biography_docs.sort(key=lambda x: x['score'], reverse=True)

        return biography_docs

    def filter(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> List[Dict]:
        """
        Filtra documentos irrelevantes para biografias

        Rejeita:
        - Resultados de jogos (exceto se mencionam jogador)
        - Classificações
        - Documentos com score < 0.3
        - Documentos sem narrativa biográfica
        - IMPORTANTE: Se player_name detectado, DEVE aparecer no path ou content

        Args:
            docs: Documentos da busca
            parsed_query: Query parseada

        Returns:
            Documentos filtrados
        """
        filtered = []
        player_name = parsed_query.get('player_name', '').lower()

        for doc in docs:
            content = doc.get('content', '').lower()
            file_path = doc.get('metadata', {}).get('file_path', '').lower()
            score = doc.get('score', 0)

            # Regra PRINCIPAL: APENAS aceitar documentos da pasta de biografias
            if '/biografias/jogadores/' not in file_path:
                continue

            # Regra CRÍTICA: Se temos player_name na query, ele DEVE aparecer
            # no filename OU no content. Caso contrário, é biografia errada.
            if player_name:
                # Normalizar para comparação (remover espaços vs underscores)
                player_name_normalized = player_name.replace(" ", "_")
                file_path_normalized = file_path.replace(" ", "_")

                # Verificar se o nome do jogador aparece no path ou content
                player_name_in_path = (player_name in file_path or
                                      player_name_normalized in file_path_normalized)
                player_name_in_content = player_name in content

                # Se NÃO aparecer em nenhum dos dois, REJEITAR
                if not player_name_in_path and not player_name_in_content:
                    continue

                # Se aparecer, aceitar com score mais baixo
                min_score = 0.25
            else:
                # Se não temos player_name, exigir score MUITO alto (0.5)
                min_score = 0.5

            if score < min_score:
                continue

            # Regra 2: Boost se tiver indicadores biográficos
            if self._has_biography_indicators(content):
                doc['score'] = min(doc['score'] + 0.1, 1.0)

            # Regra 3: Boost FORTE se tiver nome do jogador
            if player_name and player_name in content:
                doc['score'] = min(doc['score'] + 0.25, 1.0)

            filtered.append(doc)

        # Re-ordenar e limitar a top 5
        filtered.sort(key=lambda x: x['score'], reverse=True)
        return filtered[:5]

    def format_response(self, docs: List[Dict], parsed_query: Dict[str, Any]) -> str:
        """
        Formata resposta biográfica COMPLETA

        IMPORTANTE: Retorna texto COMPLETO do ficheiro de biografia principal

        Args:
            docs: Documentos filtrados (APENAS de /biografias/jogadores/)
            parsed_query: Query parseada

        Returns:
            Biografia completa do jogador ou mensagem de que não existe
        """
        if not docs:
            player_name = parsed_query.get('player_name', '')
            if player_name:
                return f"Desculpe, não encontrei biografia de '{player_name}' na base de dados. Consulte LISTA_JOGADORES_BIOGRAFIAS.md para ver os 210 jogadores disponíveis."
            else:
                return "Desculpe, não encontrei informação biográfica para essa consulta. Consulte LISTA_JOGADORES_BIOGRAFIAS.md para ver os jogadores disponíveis."

        # Estratégia: ler ficheiro completo da biografia principal
        player_name = parsed_query.get('player_name', '').lower()

        # 1. Tentar encontrar ficheiro de biografia dedicado
        for doc in docs:
            file_path = doc.get('metadata', {}).get('file_path', '')

            # Se encontrou biografia em /biografias/jogadores/
            if '/biografias/jogadores/' in file_path and file_path.endswith('.md'):
                # Ler ficheiro COMPLETO
                try:
                    full_content = self._read_full_biography_file(file_path)
                    if full_content:
                        return full_content
                except Exception:
                    pass  # Continuar para fallback

        # 2. Fallback: usar chunks retornados pelo RAG (método antigo)
        # Agrupar chunks do mesmo ficheiro e ordenar por chunk_id
        file_chunks = {}

        for doc in docs:
            file_path = doc.get('metadata', {}).get('file_path', 'unknown')
            chunk_id = doc.get('metadata', {}).get('chunk_id', 0)
            content = doc.get('content', '')

            if file_path not in file_chunks:
                file_chunks[file_path] = []

            file_chunks[file_path].append({
                'chunk_id': chunk_id,
                'content': content,
                'score': doc.get('score', 0)
            })

        # Ordenar chunks de cada ficheiro por chunk_id
        for file_path in file_chunks:
            file_chunks[file_path].sort(key=lambda x: x['chunk_id'])

        # Escolher ficheiro com mais chunks e maior score total
        best_file = max(file_chunks.items(),
                       key=lambda x: (len(x[1]), sum(c['score'] for c in x[1])))

        # 1. Primeiro extrair TODAS as fotos de todos os chunks
        all_photos = []
        for chunk in best_file[1]:
            content = chunk['content']
            photos = self._extract_photos(content)
            all_photos.extend(photos)

        # Remover duplicados mantendo ordem
        seen_photos = set()
        unique_photos = []
        for photo in all_photos:
            if photo not in seen_photos:
                seen_photos.add(photo)
                unique_photos.append(photo)

        # 2. Agora concatenar texto dos chunks (SEM fotos)
        response_parts = []
        seen_content = set()

        for chunk in best_file[1]:
            content = chunk['content']
            content_hash = hash(content[:200])

            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            cleaned = self._clean_biography_text(content)
            response_parts.append(cleaned)

        if not response_parts:
            return "Desculpe, não encontrei informação biográfica suficiente."

        # 3. Unir texto
        full_text = '\n\n'.join(response_parts)

        # 4. Limitar a 8000 caracteres
        if len(full_text) > 8000:
            full_text = full_text[:8000] + '\n\n[Texto truncado para brevidade]'

        # 5. Montar resposta: FOTOS PRIMEIRO, depois texto
        final_parts = []

        if unique_photos:
            final_parts.append("📷 FOTOGRAFIAS:")
            for i, photo_url in enumerate(unique_photos, 1):
                final_parts.append(f"  {i}. {photo_url}")
            final_parts.append("")  # Linha vazia

        final_parts.append(full_text)

        return '\n'.join(final_parts)

    def _read_full_biography_file(self, file_path: str) -> Optional[str]:
        """
        Lê ficheiro completo de biografia e formata com FOTOS PRIMEIRO

        Args:
            file_path: Caminho do ficheiro

        Returns:
            Conteúdo completo com fotos no início + texto limpo ou None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. Extrair fotos PRIMEIRO
            photos = self._extract_photos(content)

            # 2. Limpar texto (REMOVE fotos)
            cleaned_text = self._clean_biography_text(content)

            # 3. Limitar texto a 8000 caracteres
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000] + '\n\n[Texto truncado para brevidade]'

            # 4. Montar resposta: FOTOS PRIMEIRO, depois texto
            parts = []

            # Adicionar fotos no início
            if photos:
                parts.append("📷 FOTOGRAFIAS:")
                for i, photo_url in enumerate(photos, 1):
                    parts.append(f"  {i}. {photo_url}")
                parts.append("")  # Linha vazia

            # Adicionar texto depois
            parts.append(cleaned_text)

            return '\n'.join(parts)

        except Exception:
            return None

    # Métodos auxiliares privados

    def _is_match_result(self, content: str) -> bool:
        """Detecta se é resultado de jogo"""
        patterns = [
            r'\d+\s*[-–]\s*\d+',  # Placar: 2-1, 3 - 0
            r'farense\s+\d+.*\d+',  # Farense 2 vs 1
            r'jornada\s+\d+',
            r'campeonato.*\d{4}[-/]\d{2,4}'
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in patterns)

    def _is_classification_table(self, content: str) -> bool:
        """Detecta se é tabela de classificação"""
        indicators = [
            'classificação',
            'pts | j | v | e | d',
            'posição | equipa',
            '1º.*2º.*3º'
        ]
        return any(ind in content.lower() for ind in indicators)

    def _has_biography_indicators(self, content: str) -> bool:
        """Detecta indicadores de conteúdo biográfico"""
        indicators = [
            'nascido em',
            'natural de',
            'carreira',
            'jogador',
            'internacional',
            'formação',
            'estreia',
            'transferência',
            'emprestado',
            'contratado'
        ]
        return sum(1 for ind in indicators if ind in content.lower()) >= 2

    def _extract_photos(self, text: str) -> List[str]:
        """
        Extrai URLs de fotos do texto (markdown e HTML)

        Returns:
            Lista de URLs de fotos encontradas
        """
        photos = []

        # Extrair imagens markdown: ![alt](url)
        markdown_images = re.findall(r'!\[([^\]]*)\]\(([^\)]+)\)', text)
        for alt, url in markdown_images:
            photos.append(url)

        # Extrair imagens HTML: <img src="url">
        html_images = re.findall(r'<img\s+src="([^"]+)"[^>]*>', text)
        photos.extend(html_images)

        return photos

    def _clean_biography_text(self, text: str) -> str:
        """Limpa texto REMOVENDO fotos (fotos serão apresentadas separadamente)"""
        # REMOVER imagens markdown completamente
        text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', '', text)
        # REMOVER imagens HTML completamente
        text = re.sub(r'<img\s+src="([^"]+)"[^>]*>', '', text)
        # Remover headers markdown
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remover bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        # Remover links mas manter texto
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Limpar linhas vazias múltiplas
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_biography_paragraphs(self, text: str) -> List[str]:
        """
        Extrai parágrafos relevantes de biografia

        Prioriza:
        - Parágrafos com fotos (SEMPRE incluir)
        - Parágrafos > 100 caracteres
        - Parágrafos com informação biográfica
        """
        paragraphs = text.split('\n\n')
        good_paras = []

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            # SEMPRE incluir se contém fotos
            if '📷 Foto:' in p:
                good_paras.append(p)
                continue

            # Incluir se for longo o suficiente
            if len(p) >= 100:
                good_paras.append(p)
                continue

            # Incluir se tiver indicadores biográficos (mesmo que curto)
            if self._has_biography_indicators(p):
                good_paras.append(p)

        return good_paras

    def _search_by_filename(self, player_name: str) -> List[Dict]:
        """
        Busca direta por nome de ficheiro na pasta de biografias.
        Usado como fallback quando o RAG não encontra.

        Estratégia de busca flexível:
        1. Match exato com underscores (ex: "antonio_gago.md")
        2. Match com qualquer componente do nome (ex: "gago" encontra "gago.md" ou "antonio_gago.md")
        3. Match parcial em qualquer ordem

        Args:
            player_name: Nome do jogador (ex: "almeida", "paco fortes", "antonio gago")

        Returns:
            Lista com documento encontrado ou lista vazia
        """
        bio_folder = self.base_path / "biografias" / "jogadores"

        if not bio_folder.exists():
            return []

        # Normalizar e dividir nome em componentes
        player_name_lower = player_name.lower().strip()
        name_components = player_name_lower.split()  # ["antonio", "gago"]
        search_name_underscore = player_name_lower.replace(" ", "_")  # "antonio_gago"

        # Procurar ficheiro com múltiplas estratégias
        candidates = []

        for bio_file in bio_folder.glob("*.md"):
            filename = bio_file.stem.lower()  # Nome sem extensão

            score = 0

            # Estratégia 1: Match exato com underscores (score: 1.0)
            if filename == search_name_underscore:
                score = 1.0

            # Estratégia 2: Match exato com espaços convertidos (score: 1.0)
            elif filename == player_name_lower.replace(" ", "_"):
                score = 1.0

            # Estratégia 3: Todos os componentes aparecem no filename (score: 0.9)
            elif all(comp in filename for comp in name_components):
                score = 0.9

            # Estratégia 4: Pelo menos um componente aparece (score baseado em quantos)
            elif any(comp in filename for comp in name_components):
                matching_components = sum(1 for comp in name_components if comp in filename)
                score = 0.7 * (matching_components / len(name_components))

            # Estratégia 5: Nome do jogador contido no filename (score: 0.8)
            elif player_name_lower.replace(" ", "") in filename.replace("_", ""):
                score = 0.8

            # Estratégia 6: Filename contido no nome do jogador (score: 0.6)
            elif filename in player_name_lower.replace(" ", "_"):
                score = 0.6

            if score > 0:
                candidates.append((bio_file, score))

        if not candidates:
            return []

        # Ordenar por score e pegar o melhor
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_file, best_score = candidates[0]

        try:
            content = best_file.read_text(encoding='utf-8')
            return [{
                'content': content,
                'score': 0.95,  # Score alto para priorizar no resto do sistema
                'metadata': {
                    'file_path': str(best_file),
                    'chunk_id': 0
                }
            }]
        except Exception:
            return []
