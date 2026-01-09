import requests
from bs4 import BeautifulSoup
import re
import logging
import traceback
import time
from datetime import datetime, timedelta
import locale

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def parse_date_time(date_time_str):
    """
    Parseia string de data e hora com múltiplos formatos.
    
    Args:
        date_time_str (str): String de data e hora
    
    Returns:
        tuple: (dia, mês, hora, minuto)
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
        
        # "dd/mm" sem hora (usa hora 00:00)
        r'(?P<dia>\d+)/(?P<mes>\d+)$',
        
        # "dd/mm HH:MM" sem ano (usa ano atual)
        r'(?P<dia>\d+)/(?P<mes>\d+)\s+(?P<hora>\d+):(?P<minuto>\d+)',
        
        # Formato com ano completo
        r'(?P<dia>\d+)/(?P<mes>\d+)/(?P<ano>\d{4})\s+(?P<hora>\d+):(?P<minuto>\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_time_str, re.IGNORECASE)
        if match:
            dia = int(match.group('dia'))
            
            # Converter mês (texto ou número)
            mes_str = match.group('mes').lower()
            mes = meses.get(mes_str, int(mes_str) if mes_str.isdigit() else None)
            
            # Usar ano atual se não especificado
            ano = int(match.group('ano')) if 'ano' in match.groupdict() else datetime.now().year
            
            # Usar hora 00:00 se não especificada
            hora = int(match.group('hora')) if 'hora' in match.groupdict() else 0
            minuto = int(match.group('minuto')) if 'minuto' in match.groupdict() else 0
            
            return dia, mes, hora, minuto
    
    raise ValueError(f"Não foi possível parsear a data: {date_time_str}")

def formatar_data_hora(date_time_str):
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
        dia, mes, hora, minuto = parse_date_time(date_time_str)
        
        # Criar objeto datetime
        data_hora = datetime(2025, mes, dia, hora, minuto)
        
        # Formatar data extenso
        data_formatada = data_hora.strftime("%A, %d de %B de %Y")
        
        # Adicionar hora se não for 00:00
        if hora != 0 or minuto != 0:
            data_formatada += f" às {hora:02d}:{minuto:02d}"
        
        # Capitalizar primeira letra
        return data_formatada.capitalize()
    
    except ValueError as e:
        # Tratamento de erro se conversão falhar
        print(f"Erro na conversão de data: {e}")
        return date_time_str
    finally:
        # Resetar locale para padrão
        locale.setlocale(locale.LC_TIME, '')

def fetch_last_matches(url='https://www.zerozero.pt/equipa/farense/10', max_retries=3):
    """
    Fetch and parse last matches for Farense with advanced parsing strategies.
    
    Args:
        url (str): URL to scrape matches from
        max_retries (int): Maximum number of retries for rate limiting
    
    Returns:
        str: Formatted text of previous matches
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'pt-PT,pt;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to fetch matches from URL: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Advanced selector strategies
            def find_results_table(soup):
                # Strategy 1: Look for specific class combinations
                results_selectors = [
                    lambda s: s.find('div', class_='results-table'),
                    lambda s: s.find('table', class_='matches-table'),
                    lambda s: s.select_one('div.team-results table'),
                    
                    # Strategy 2: Look for tables with match-like structure
                    lambda s: next((table for table in s.find_all('table') 
                                    if len(table.find_all('tr')) > 3 and 
                                    any(re.search(r'\d{2}/\d{2}', td.text) for td in table.find_all('td'))), None),
                    
                    # Strategy 3: Find tables with specific attributes
                    lambda s: s.find('table', attrs={'data-type': 'matches'}),
                    
                    # Strategy 4: Look in specific page sections
                    lambda s: s.find('div', id='matches-section').find('table') if s.find('div', id='matches-section') else None
                ]
                
                for selector in results_selectors:
                    result = selector(soup)
                    if result:
                        return result
                
                return None

            results_table = find_results_table(soup)
            
            if not results_table:
                logger.warning("No results table found using advanced strategies")
                
                # Debug: save full HTML for investigation
                with open('debug_zerozero_html.html', 'w', encoding='utf-8') as f:
                    f.write(str(soup))
                
                return "Sem informações de jogos anteriores. 🚫⚽"
            
            matches_text = "📋 Últimos resultados do SC Farense ⚫⚪:\n\n"
            processed_matches = 0
            
            # Flexible row parsing
            match_rows = results_table.find_all('tr')[1:] if len(results_table.find_all('tr')) > 1 else results_table.find_all('tr')
            
            for row in match_rows:
                cols = row.find_all('td')
                
                # Filter rows: only process rows with match results
                if not any(re.search(r'\d+-\d+', col.text.strip()) for col in cols):
                    continue
                
                try:
                    # Advanced column extraction
                    def extract_column(cols, validators):
                        for validator in validators:
                            for col in cols:
                                text = col.text.strip()
                                if validator(text):
                                    return text
                        return None
                    
                    # Date validation
                    date = extract_column(cols, [
                        lambda x: re.match(r'\d{2}/\d{2}', x),  # DD/MM format
                        lambda x: '/' in x  # Contains a slash
                    ])
                    
                    # Extração flexível de dados
                    def safe_extract(cols, index, default=''):
                        try:
                            return cols[index].text.strip()
                        except IndexError:
                            return default
                    
                    # Extração de competição da div com classe 'double'
                    competition_div = cols[3].find('div', class_='text')
                    competition_code = competition_div.text.strip() if competition_div else ''
                    
                    # Substituir código de competição
                    competition_info = {
                        "TP": {"name": "Taça de Portugal", "emoji": "🏆"},
                        "D1": {"name": "Primeira Liga", "emoji": "⚽"},
                        "h2h": {"name": "Amigável", "emoji": "🤝"},
                        "ECL": {"name": "Europa Conference League", "emoji": "🌍"},
                        "EL": {"name": "Europa League", "emoji": "🥅"}
                    }.get(competition_code, {
                        "name": competition_code, 
                        "emoji": "🥅"
                    })
                    
                    # Extração de times com links
                    home_team = cols[4].find('a').text.strip() if cols[4].find('a') else ''
                    away_team = cols[8].find('a').text.strip() if cols[8].find('a') else ''
                    
                    # Verificação de times
                    if not (home_team and away_team):
                        continue
                    
                    # Score validation
                    score_cols = [col for col in cols if re.search(r'\d+-\d+', col.text.strip())]
                    result = score_cols[0].text.strip() if score_cols else None
                    
                    # Skip if any critical information is missing
                    if not all([date, competition_code, home_team, away_team, result]):
                        continue
                    
                    # Skip future matches
                    if any(keyword in date.lower() for keyword in ['próximo', 'futuro']):
                        continue
                    
                    # Determine match details
                    home_score, away_score = map(int, result.split('-'))
                    
                    # Determinar local do jogo
                    if home_team == "Farense":
                        location_emoji = "🏡"
                        match_desc = f"**{home_team}** {result} {away_team}"
                        
                        if home_score > away_score:
                            outcome_emoji, outcome_text = "🏆", "Vitória"
                        elif home_score < away_score:
                            outcome_emoji, outcome_text = "😔", "Derrota"
                        else:
                            outcome_emoji, outcome_text = "🤝", "Empate"
                    else:
                        location_emoji = "✈️"
                        match_desc = f"{home_team} {result} **{away_team}**"
                        
                        if away_score > home_score:
                            outcome_emoji, outcome_text = "🏆", "Vitória"
                        elif away_score < home_score:
                            outcome_emoji, outcome_text = "😔", "Derrota"
                        else:
                            outcome_emoji, outcome_text = "🤝", "Empate"
                    
                    # Construir texto de detalhes do jogo
                    matches_text += f"{competition_info['emoji']} {competition_info['name']}\n"
                    matches_text += f"📅 {formatar_data_hora(date)}\n"
                    matches_text += f"{location_emoji} {match_desc}\n"
                    matches_text += f"{outcome_emoji} {outcome_text}\n"
                    matches_text += "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    
                    processed_matches += 1
                    
                    # Limit to 3 matches
                    if processed_matches >= 3:
                        break
                
                except Exception as row_error:
                    logger.warning(f"Error processing match row: {row_error}")
                    continue
            
            return matches_text.strip() if matches_text.strip() else "Sem informações de jogos anteriores. 🚫⚽"
        
        except requests.exceptions.RequestException as req_error:
            if response.status_code == 429:  # Too Many Requests
                wait_time = (attempt + 1) * 2  # Exponential backoff
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Network error: {req_error}")
                return f"Erro de rede ao buscar jogos: {req_error} 🚫⚽"
        
        except Exception as e:
            logger.error(f"Unexpected error fetching matches: {e}")
            logger.error(traceback.format_exc())
            return "Não foi possível recuperar os últimos jogos. 🚫⚽"
    
    return "Tentativas de busca de jogos esgotadas. 🚫⚽"

def get_last_matches_text():
    """
    Returns previous matches of Farense in text format.
    
    Returns:
        str: Formatted text of previous matches
    """
    return fetch_last_matches()

if __name__ == '__main__':
    print(get_last_matches_text())
