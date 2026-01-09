import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import locale
import re

class MatchReport:
    def __init__(self, url):
        self.url = url
        self.soup = self.fetch_html()
        self.match_details = self.extract_match_details() if self.soup else {}
        self.teams = {}
        self.coaches = {}
        
        # Buscar e parsear o HTML
        self._fetch_match_report()
    
    def fetch_html(self, max_retries=3):
        """
        Fetch HTML with retry mechanism for rate limiting
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.get(self.url, headers=headers)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                if response.status_code == 429:  # Too Many Requests
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Error fetching URL: {e}")
                    return None
        
        print("Max retries exceeded")
        return None

    def extract_match_details(self):
        """
        Extract comprehensive match details from the HTML
        
        Returns:
            dict: Match details
        """
        match_details = {}
        try:
            # Find match data container
            match_data_div = self.soup.find('div', id='match_data')
            
            if match_data_div:
                # Team names
                home_team_elem = self.soup.find('div', class_='home').find('a')
                away_team_elem = self.soup.find('div', class_='away').find('a')
                match_details['Visitado'] = home_team_elem.get_text(strip=True) if home_team_elem else "Home Team not found"
                match_details['Visitante'] = away_team_elem.get_text(strip=True) if away_team_elem else "Away Team not found"
                
                # Date and Time
                date_icon = match_data_div.find('i', class_='fa-regular fa-calendar')
                time_icon = match_data_div.find('i', class_='fa-regular fa-clock')
                match_details['Data'] = date_icon.next_sibling.strip() if date_icon else "Date not found"
                match_details['Hora'] = time_icon.next_sibling.strip() if time_icon else "Time not found"
                
                # Venue
                venue_icon = match_data_div.find('i', class_='fa-solid fa-location-dot')
                venue_link = venue_icon.find_next('a') if venue_icon else None
                if venue_link:
                    venue_name = venue_link.get_text(strip=True)
                    venue_location = venue_link.find_next_sibling(string=True).strip('() ')
                    match_details['Local'] = f"{venue_name} ({venue_location})"
                else:
                    match_details['Local'] = "Venue not found"
                
                # Attendance and Broadcast
                attendance_icon = match_data_div.find('i', class_='fa-solid fa-people-group')
                broadcast_icon = match_data_div.find('i', class_='fa-solid fa-tv')
                match_details['Assistência'] = attendance_icon.next_sibling.strip() if attendance_icon else "Attendance not found"
                match_details['Transmissão'] = broadcast_icon.next_sibling.strip() if broadcast_icon else "Broadcast not found"
                
                # Referee
                referee_icon = match_data_div.find('i', class_='fa-regular fa-user')
                referee_link = referee_icon.find_next('a') if referee_icon else None
                match_details['Arbitro'] = referee_link.get_text(strip=True) if referee_link else "Referee not found"
                
                # League
                league_elem = match_data_div.find('a', href=lambda href: href and 'edicao' in href)
                match_details['Liga'] = league_elem.get_text(strip=True) if league_elem else "League not found"
                
                # Score
                score_elem = self.soup.find('div', class_='score').find('a')
                match_details['Resultado'] = score_elem.get_text(strip=True) if score_elem else "Score not found"
                
                # Half-time score
                half_time_elem = self.soup.find('span', class_='partial')
                match_details['Ao intervalo'] = f"Intervalo: {half_time_elem.get_text(strip=True)}" if half_time_elem else "Intervalo: 0-0"
                
                # Scorers
                scorers_div = self.soup.find_all('div', class_='scorers')
                if len(scorers_div) > 1:
                    scorers = [scorer.get_text(strip=True) for scorer in scorers_div[1].find_all('a')]
                    scorer_times = [time.get_text(strip=True) for time in scorers_div[1].find_all('span', class_='time')]
                    
                    match_details['Marcadores'] = ': '.join([f"{scorer} {time}" 
                                                             for scorer, time in zip(scorers, scorer_times)])
                else:
                    match_details['Marcadores'] = ""
        
        except Exception as e:
            print(f"Error extracting match details: {e}")
        
        return match_details

    def parse_date_time(self, date_time_str):
        """
        Parseia string de data e hora com múltiplos formatos.
        
        Args:
            date_time_str (str): String de data e hora
        
        Returns:
            tuple: (dia, mês, hora)
        """
        # Mapeamento de meses
        meses = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 
            'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 
            'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
        }
        
        # Padrões de regex para diferentes formatos
        patterns = [
            # "Domingo  9 Fevereiro 2025 15h30"
            r'(?P<dia>\d+)\s+(?P<mes>[a-zA-Z]+)\s+(?P<ano>\d{4})\s+(?P<hora>\d+)h(?P<minuto>\d+)',
            
            # Outros formatos podem ser adicionados aqui
            r'(?P<dia>\d+)/(?P<mes>\d+)/(?P<ano>\d{4})\s+(?P<hora>\d+):(?P<minuto>\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_time_str, re.IGNORECASE)
            if match:
                dia = int(match.group('dia'))
                
                # Converter mês (texto ou número)
                mes_str = match.group('mes').lower()
                mes = meses.get(mes_str, int(mes_str) if mes_str.isdigit() else None)
                
                ano = int(match.group('ano'))
                hora = int(match.group('hora'))
                minuto = int(match.group('minuto'))
                
                return dia, mes, hora, minuto
        
        raise ValueError(f"Não foi possível parsear a data: {date_time_str}")

    def formatar_data_hora(self, date_time_str):
        """
        Formata data e hora em português com formato extenso.
        
        Args:
            date_time_str (str): String de data e hora
        
        Returns:
            str: Data formatada em português
        """
        try:
            # Configurar locale para português
            locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Portuguese_Portugal.1252')
            except locale.Error:
                # Fallback: usar locale padrão
                pass
        
        try:
            # Parsear data
            dia, mes, hora, minuto = self.parse_date_time(date_time_str)
            
            # Criar objeto datetime
            data_hora = datetime(2025, mes, dia, hora, minuto)
            
            # Formatar data extenso
            data_formatada = data_hora.strftime("%A, %d de %B de %Y às %H:%M")
            
            # Capitalizar primeira letra
            return data_formatada.capitalize()
        
        except ValueError as e:
            # Tratamento de erro se conversão falhar
            print(f"Erro na conversão de data: {e}")
            return date_time_str
        finally:
            # Resetar locale para padrão
            locale.setlocale(locale.LC_TIME, '')

    def _fetch_match_report(self):
        """
        Busca o HTML do relatório de jogo e parseia com BeautifulSoup.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            response = requests.get(self.url, headers=headers)
            response.raise_for_status()
            
            self.soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair relatório de jogo
            game_report_div = self.soup.find('div', id='game_report')
            if not game_report_div:
                print("Não foi possível encontrar o relatório de jogo.")
                return
            
            # Extrair informações das equipes
            self._extract_team_info(game_report_div)
            
            # Extrair informações dos treinadores
            self._extract_coaches_info(game_report_div)
        
        except Exception as e:
            print(f"Erro ao buscar relatório de jogo: {e}")
    
    def _extract_team_info(self, game_report_div):
        """
        Extrai informações dos jogadores de cada equipe.
        
        Args:
            game_report_div (BeautifulSoup): Div do relatório de jogo
        """
        team_columns = game_report_div.find_all('div', class_='column_300')
        
        # Variável para armazenar o nome da primeira equipe (equipa da casa)
        first_team = None
        
        for column in team_columns:
            subtitle = column.find('div', class_='subtitle')
            if not subtitle or not subtitle.text.strip():
                continue
            
            team_name = subtitle.text.strip()
            
            # Pular seções de treinadores
            if team_name == 'Treinadores':
                continue
            
            # Identificar a primeira equipe
            if first_team is None and team_name not in ['Suplentes', 'Treinadores']:
                first_team = team_name
            
            # Processar seção de suplentes da primeira equipe
            if team_name == 'Suplentes':
                if first_team not in self.teams:
                    self.teams[first_team] = {'titulares': [], 'suplentes': []}
                
                # Encontrar todos os jogadores na coluna de suplentes
                players = column.find_all('div', class_='player')
                
                for player_div in players:
                    # Extrair informações do jogador
                    player_info = self._parse_player_info(player_div)
                    if player_info:
                        self.teams[first_team]['suplentes'].append(player_info)
                
                continue
            
            # Processar titulares das equipes
            if team_name not in ['Suplentes', 'Treinadores']:
                if team_name not in self.teams:
                    self.teams[team_name] = {'titulares': [], 'suplentes': []}
                
                # Encontrar todos os jogadores na coluna
                players = column.find_all('div', class_='player')
                
                for player_div in players:
                    # Extrair informações do jogador
                    player_info = self._parse_player_info(player_div)
                    if player_info:
                        # Ignorar jogadores marcados como inativos (suplentes)
                        if 'inactive' not in player_div.get('class', []):
                            self.teams[team_name]['titulares'].append(player_info)

    def _parse_player_info(self, player_div):
        """
        Parseia as informações de um jogador.
        
        Args:
            player_div (BeautifulSoup): Div do jogador
        
        Returns:
            dict: Informações do jogador
        """
        try:
            # Número do jogador
            number_div = player_div.find('div', class_='number')
            number = number_div.text.strip() if number_div else 'N/A'
            
            # Nome do jogador
            name_div = player_div.find('div', class_='micrologo_and_text')
            if not name_div:
                return None
            
            # Nome e link do jogador
            player_link = name_div.find('a', href=re.compile(r'/jogador/'))
            player_name = player_link.text.strip() if player_link else 'Jogador Desconhecido'
            
            # Verificar se é capitão
            is_captain = '(C)' in player_name
            player_name = player_name.replace('(C)', '').strip()
            
            # Eventos do jogador
            events_div = player_div.find('div', class_='events')
            events = []
            
            if events_div:
                event_spans = events_div.find_all('span')
                event_times = events_div.find_all('div')
                
                for span, time in zip(event_spans, event_times):
                    # Prioriza título, depois classe
                    event_type = (
                        span.get('title') or  # Primeiro, tenta o título
                        ('Saiu' if 'grey' in span.get('class', []) else 
                         'Amarelos' if 'yellow' in span.get('class', []) else
                         'Vermelhos' if 'red' in span.get('class', []) else 
                         'Entrou' if 'Entrou' in span.get('title', '') else
                         'Evento')
                    )
                    event_time = time.text.strip()
                    
                    events.append({
                        'tipo': event_type,
                        'tempo': event_time
                    })
            
            return {
                'número': number,
                'nome': player_name,
                'capitão': is_captain,
                'eventos': events
            }
        
        except Exception as e:
            print(f"Erro ao parsear jogador: {e}")
            return None
    
    def _extract_coaches_info(self, game_report_div):
        """
        Extrai informações dos treinadores.
        
        Args:
            game_report_div (BeautifulSoup): Div do relatório de jogo
        """
        coaches_columns = game_report_div.find_all('div', class_='column_300')
        
        for column in coaches_columns:
            subtitle = column.find('div', class_='subtitle')
            if subtitle and subtitle.text.strip() == 'Treinadores':
                coaches = column.find_all('div', class_='player')
                
                for coach_div in coaches:
                    coach_name_div = coach_div.find('div', class_='micrologo_and_text')
                    if coach_name_div:
                        coach_link = coach_name_div.find('a')
                        if coach_link:
                            coach_name = coach_link.text.strip()
                            
                            self.coaches[coach_name] = {
                                'nome': coach_name
                            }
    
    def format_match_report(self):
        """
        Formata o relatório de jogo em texto.
        
        Returns:
            str: Relatório de jogo formatado
        """
        if not self.teams:
            return "Não foi possível gerar o relatório de jogo."
        
        report = "📋 Relatório de Jogo:\n\n"
        
        # Informações das equipes
        for team, team_data in self.teams.items():
            report += f"🏆 {team}:\n"
            
            # Jogadores titulares
            report += "   👥 Titulares:\n"
            for player in team_data['titulares']:
                # Preparar eventos do jogador
                player_events = []
                if player['eventos']:
                    for evento in player['eventos']:
                        # Mapear tipos de eventos para emojis
                        if 'Amarelos' in evento['tipo'] or 'yellow' in evento['tipo']:
                            emoji = '🟨'
                        elif 'Vermelhos' in evento['tipo'] or 'red' in evento['tipo']:
                            emoji = '🟥'
                        elif 'Golos' in evento['tipo'] or 'fut-11' in evento['tipo']:
                            emoji = '⚽'
                        elif 'Saiu' in evento['tipo']:
                            emoji = '⬅'
                        elif 'Assistência' in evento['tipo']:
                            emoji = '✅'
                        else:
                            emoji = '⚠️'
                        
                        player_events.append(f"{emoji} {evento['tempo']}")
            
                # Adicionar (C) para capitão
                player_name = f"{player['nome']} (C)" if player.get('capitão', False) else player['nome']
                
                # Adicionar nome e depois eventos
                if player_events:
                    report += f"      👤 {player_name} (#{player['número']}) {' '.join(player_events)}\n"
                else:
                    report += f"      👤 {player_name} (#{player['número']})\n"
        
            # Jogadores suplentes
            report += "   🔄 Suplentes:\n"
            for player in team_data['suplentes']:
                # Preparar eventos do jogador
                player_events = []
                if player['eventos']:
                    for evento in player['eventos']:
                        # Mapear tipos de eventos para emojis
                        if 'Entrou' in evento['tipo'] or 'Substituição de Entrada' in evento['tipo']:
                            emoji = '➡'
                        elif 'Amarelos' in evento['tipo'] or 'yellow' in evento['tipo']:
                            emoji = '🟨'
                        elif 'Vermelhos' in evento['tipo'] or 'red' in evento['tipo']:
                            emoji = '🟥'
                        else:
                            emoji = '⚠️'
                        
                        player_events.append(f"{emoji} {evento['tempo']}'")
            
                # Adicionar eventos depois do nome
                if player_events:
                    report += f"      👤 {player['nome']} (#{player['número']}) {' '.join(player_events)}\n"
                else:
                    report += f"      👤 {player['nome']} (#{player['número']})\n"
    
        return report
    
    def print_match_report(self):
        """
        Print comprehensive match report with emojis
        """
        # Define emoji mappings
        emojis = {
            'Visitado': '🏠',
            'Visitante': '✈️',
            'Data': '📅',
            'Hora': '⏰',
            'Local': '🏟️',
            'Assistência': '👥',
            'Transmissão': '📺',
            'Arbitro': '👨‍⚖️',
            'Liga': '🏆',
            'Resultado': '⚽',
            'Ao intervalo': '🕒',
            'Marcadores': '⚽'
        }
        
        # Print formatted match report
        print(" " * 40)
        print("⚽ Relatório do Jogo ⚽")
        print(" " * 40)
        
        # Special handling for match result line
        result_line = (
            f"{self.match_details.get('Visitado', 'N/A')} "
            f"{self.match_details.get('Resultado', '0-0')} "
            f"{self.match_details.get('Visitante', 'N/A')}"
        )
        print(result_line)
        print(" " * 40)
        
        # Print other details
        details_to_skip = ['Visitado', 'Visitante', 'Resultado', 'Hora']
        for key, value in self.match_details.items():
            if key not in details_to_skip:
                # Get emoji, default to 📌 if not found
                emoji = emojis.get(key, '📌')
                
                # Special formatting for specific keys
                if key == 'Marcadores' and not value:
                    value = "Sem marcadores"
                elif key == 'Data':
                    value = self.formatar_data_hora(value + ' ' + self.match_details['Hora'])
                
                # Print with emoji, remove key text
                print(f"{emoji} {value}")
        
        # Print formatted match report
        print("\n" + self.format_match_report())

# Example usage
if __name__ == "__main__":
    match_url = "https://www.zerozero.pt/jogo/2025-02-09-farense-nacional/10239995"
    report = MatchReport(match_url)
    report.print_match_report()