import requests
from bs4 import BeautifulSoup
import re
import logging
import locale
from datetime import datetime

def fetch_next_matches(url='https://www.zerozero.pt/equipa/farense/10', filter_away_games=False):
    """
    Fetch and parse upcoming matches for Farense.

    Args:
        url (str): URL to scrape matches from
        filter_away_games (bool): If True, return only away games

    Returns:
        str: HTML table of upcoming matches
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.content
        soup = BeautifulSoup(html_content, 'html.parser')

        element = soup.select_one('#page_main > div:nth-child(3)')
        if not element:
            logging.warning("Could not find matches element")
            return "No upcoming matches found."

        new_table = soup.new_tag('table')
        new_table['style'] = 'width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;'

        header_row = soup.new_tag('tr')
        headers_text = ['Date', 'Competition', 'Home Team', 'Away Team']
        for header in headers_text:
            header_cell = soup.new_tag('th')
            header_cell['style'] = 'border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;'
            header_cell.string = header
            header_row.append(header_cell)
        new_table.append(header_row)

        matches = []

        for row in element.find_all('tr'):
            if not any(re.search(r'^\d+-\d+$', cell.get_text(strip=True)) for cell in row.find_all('td')):
                new_row = soup.new_tag('tr')
                match_details = []
                for cell in row.find_all('td'):
                    new_cell = soup.new_tag('td')
                    new_cell['style'] = 'border: 1px solid #ddd; padding: 8px;'

                    img_tag = cell.find('img')
                    if img_tag and 'src' in img_tag.attrs:
                        img_url = img_tag['src']
                        if img_url.startswith('/'):
                            img_url = f'https://www.zerozero.pt{img_url}'
                        img_html = f'<img src="{img_url}" width="30" height="30" style="vertical-align: middle; margin-right: 10px;">'
                        new_cell.insert(0, BeautifulSoup(img_html, 'html.parser'))

                    text = cell.get_text(strip=True)
                    new_cell.append(text)
                    match_details.append(text)
                    new_row.append(new_cell)

                if len(match_details) > 1:
                    if not filter_away_games or (filter_away_games and match_details[4] != "Farense"):
                        matches.append(new_row)

        matches.reverse()
        for match in matches:
            new_table.append(match)

        return str(new_table)

    except requests.RequestException as e:
        logging.error(f"Error fetching matches: {e}")
        return "Unable to fetch matches. Please try again later."

def format_date_extended(date_str):
    """
    Convert date from DD/MM format to extended Portuguese format with year.

    Args:
        date_str (str): Date in DD/MM format

    Returns:
        str: Date in extended Portuguese format with year
    """
    months = {
        '01': 'janeiro', '02': 'fevereiro', '03': 'março',
        '04': 'abril', '05': 'maio', '06': 'junho',
        '07': 'julho', '08': 'agosto', '09': 'setembro',
        '10': 'outubro', '11': 'novembro', '12': 'dezembro'
    }

    weekdays = {
        '0': 'domingo', '1': 'segunda-feira', '2': 'terça-feira',
        '3': 'quarta-feira', '4': 'quinta-feira', '5': 'sexta-feira',
        '6': 'sábado'
    }

    try:
        current_year = datetime.now().year
        parsed_date = datetime.strptime(f"{date_str}/{current_year}", '%d/%m/%Y')
        weekday = weekdays[str(parsed_date.weekday())]
        day = parsed_date.day
        month = months[parsed_date.strftime('%m')]

        return f"{weekday.capitalize()}, {day} de {month} de {current_year}"

    except Exception as e:
        return date_str

def parse_date_time(date_time_str):
    """
    Parse date and time string with multiple formats.

    Args:
        date_time_str (str): Date and time string

    Returns:
        tuple: (day, month, hour, minute)
    """
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }

    patterns = [
        r'(?P<dia>\d+)\s+(?P<mes>[a-zA-Z]+)\s+(?P<ano>\d{4})\s+(?P<hora>\d+)h(?P<minuto>\d+)',
        r'(?P<dia>\d+)/(?P<mes>\d+)\s+(?P<hora>\d+):(?P<minuto>\d+)',
        r'(?P<dia>\d+)/(?P<mes>\d+)/(?P<ano>\d{4})\s+(?P<hora>\d+):(?P<minuto>\d+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, date_time_str, re.IGNORECASE)
        if match:
            dia = int(match.group('dia'))
            mes_str = match.group('mes').lower()
            mes = meses.get(mes_str, int(mes_str) if mes_str.isdigit() else None)
            ano = int(match.group('ano')) if 'ano' in match.groupdict() else datetime.now().year
            hora = int(match.group('hora'))
            minuto = int(match.group('minuto'))
            return dia, mes, hora, minuto

    raise ValueError(f"Não foi possível parsear a data: {date_time_str}")

def formatar_data_hora(date_time_str):
    """
    Format date and time in Portuguese with extended format.

    Args:
        date_time_str (str): Date and time string

    Returns:
        str: Formatted date in Portuguese
    """
    try:
        locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Portugal.1252')
        except locale.Error:
            pass

    try:
        dia, mes, hora, minuto = parse_date_time(date_time_str)
        data_hora = datetime(2025, mes, dia, hora, minuto)
        data_formatada = data_hora.strftime("%A, %d de %B de %Y às %H:%M")
        return data_formatada.capitalize()

    except ValueError as e:
        print(f"Erro na conversão de data: {e}")
        return date_time_str
    finally:
        locale.setlocale(locale.LC_TIME, '')

def normalize_stadium_name(venue_name, venue_location=''):
    """
    Normalize stadium name with specific rules.

    Args:
        venue_name (str): Original stadium name
        venue_location (str, optional): Stadium location

    Returns:
        str: Normalized stadium name
    """
    venue_name = re.sub(r'\s*\(POR\)', '', venue_name).strip()
    stadium_map = {
        "Estádio do Algarve": "Estádio Algarve"
    }
    return stadium_map.get(venue_name, venue_name)

def format_player_issues(team_issues):
    """
    Format injury and suspension information for display.

    Args:
        team_issues (dict): Dictionary with injury and suspension information

    Returns:
        str: Formatted text with player information
    """
    if not team_issues:
        return ""

    output = "-"*30+"\n🚨 Impedimentos de Jogadores:\n\n"

    for team, players in team_issues.items():
        output += f"🏆 {team}:\n"

        if not players:
            output += "   Todos os jogadores estão disponíveis.\n"

        for player in players:
            if 'Expulsão' in player['Tipo de Problema']:
                icon = '🟥'
            elif 'Lesão' in player['Tipo de Problema']:
                icon = '🩺'
            else:
                icon = '⚠️'

            output += (
                f"   👤 {player['Nome']} | {icon} {player['Tipo de Problema']}\n"
            )

        output += "\n"

    return output.strip()

def extract_player_issues(soup):
    """
    Extract injury and suspension information of players.

    Args:
        soup (BeautifulSoup): BeautifulSoup object of the page

    Returns:
        dict: Dictionary with injury and suspension information by team
    """
    team_issues = {}
    game_report_div = soup.find('div', id='game_report')

    if not game_report_div:
        return team_issues

    stats_tables = game_report_div.find_all('table', class_='zztable stats')

    for table in stats_tables:
        team_title = table.find_previous('div', class_='title')
        team_name = team_title.text.strip() if team_title else 'Time Desconhecido'
        team_issues[team_name] = []

        for row in table.find_all('tr'):
            player_div = row.find('div', class_='micrologo_and_text')
            if not player_div:
                continue

            player_link = player_div.find('a', href=re.compile(r'/jogador/'))
            player_name = player_link.text.strip() if player_link else 'Jogador Desconhecido'
            problem_cell = row.find_all('td')[-1]
            problem_text = problem_cell.text.strip() if problem_cell else 'Problema Desconhecido'
            problem_icon = row.find('img', style=re.compile(r'width:18px;'))
            problem_type = problem_icon.get('title', 'Problema Indeterminado') if problem_icon else 'Problema Indeterminado'

            team_issues[team_name].append({
                'Nome': player_name,
                'Tipo de Problema': problem_type,
                'Descrição': problem_text
            })
            
    return team_issues

def generate_match_link(date, home_team, away_team, match_id):
    """
    Generate the link for match details on Zerozero and extract additional information.

    Args:
        date (str): Match date in DD/MM format
        home_team (str): Home team name
        away_team (str): Away team name
        match_id (str): Match ID

    Returns:
        tuple: (match link, dictionary of additional details)
    """
    additional_details = {}

    try:
        day, month = map(int, date.split('/'))
        year = datetime.now().year
        formatted_date = f"{year}-{month:02d}-{day:02d}"
        home_team_url = home_team.lower().replace(' ', '-')
        away_team_url = away_team.lower().replace(' ', '-')
        match_link = f"https://www.zerozero.pt/jogo/{formatted_date}-{home_team_url}-{away_team_url}/{match_id}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        response = requests.get(match_link, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        player_issues = extract_player_issues(soup)
        if player_issues:
            additional_details['Problemas'] = format_player_issues(player_issues)

        match_data_div = soup.find('div', id='match_data')
        if match_data_div:
            venue_icon = match_data_div.find('i', class_='fa-solid fa-location-dot')
            if venue_icon:
                venue_link = venue_icon.find_next('a')
                if venue_link:
                    venue_name = venue_link.get_text(strip=True)
                    additional_details['Estádio'] = normalize_stadium_name(venue_name)

            broadcast_icon = match_data_div.find('i', class_='fa-solid fa-tv')
            if broadcast_icon:
                additional_details['Transmissão'] = broadcast_icon.next_sibling.strip()

            referee_icon = match_data_div.find('i', class_='fa-regular fa-user')
            if referee_icon:
                referee_link = referee_icon.find_next('a')
                if referee_link:
                    referee_name = referee_link.get_text(strip=True)
                    referee_name = re.sub(r'\s*\([A-Z]{3}\)', '', referee_name).strip()
                    additional_details['Arbitro'] = referee_name

            league_elem = match_data_div.find('a', href=lambda href: href and 'edicao' in href)
            if league_elem:
                additional_details['Liga'] = league_elem.get_text(strip=True)

        return match_link, additional_details

    except Exception as e:
        logging.error(f"Error generating match link: {e}")
        return None, additional_details

def extract_additional_match_details(row):
    """
    Extract additional details from a match row.

    Args:
        row (BeautifulSoup): Match row from HTML

    Returns:
        dict: Additional match details
    """
    additional_details = {}

    try:
        match_data_div = row.find('div', class_='match_data')
        if match_data_div:
            venue_icon = match_data_div.find('i', class_='fa-solid fa-location-dot')
            venue_link = venue_icon.find_next('a') if venue_icon else None
            if venue_link:
                venue_name = venue_link.get_text(strip=True)
                additional_details['Estádio'] = normalize_stadium_name(venue_name, '')

            broadcast_icon = match_data_div.find('i', class_='fa-solid fa-tv')
            if broadcast_icon:
                additional_details['Transmissão'] = broadcast_icon.next_sibling.strip()

            referee_icon = match_data_div.find('i', class_='fa-regular fa-user')
            referee_link = referee_icon.find_next('a') if referee_icon else None
            if referee_link:
                additional_details['Arbitro'] = referee_link.get_text(strip=True)

            league_elem = match_data_div.find('a', href=lambda href: href and 'edicao' in href)
            if league_elem:
                additional_details['Liga'] = league_elem.get_text(strip=True)

            if additional_details:
                logging.info("\n📋 Detalhes Adicionais do Jogo:")
                for key, value in additional_details.items():
                    logging.info(f"• {key}: {value}")

    except Exception as e:
        logging.error(f"Error extracting additional match details: {e}")

    return additional_details

def fetch_next_matches_text(soup):
    """
    Fetch and format the next match of Farense.

    Args:
        soup (BeautifulSoup): BeautifulSoup object of the page

    Returns:
        str: Formatted text with the next match
    """
    rows = list(soup.find_all('tr')[1:])
    rows.reverse()

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 9:
            continue

        if any(re.search(r'\d+-\d+', col.text.strip()) for col in cols):
            continue

        def safe_extract(cols, index, default=''):
            try:
                return cols[index].text.strip()
            except IndexError:
                return default

        competition_div = cols[3].find('div', class_='text')
        if not competition_div:
            continue

        competition_code = competition_div.text.strip()
        date = safe_extract(cols, 1)
        time = safe_extract(cols, 2)
        home_team_link = cols[4].find('a')
        away_team_link = cols[8].find('a')

        if not (home_team_link and away_team_link):
            continue

        home_team = home_team_link.text.strip()
        away_team = away_team_link.text.strip()

        if not (home_team and away_team):
            continue

        if not all([date, competition_code, home_team, away_team]):
            continue

        if home_team == "Farense":
            location_emoji = "🏡"
            match_desc = f"**{home_team}** vs {away_team}"
        else:
            location_emoji = "✈️"
            match_desc = f"{home_team} vs **{away_team}**"

        match_link, additional_details = generate_match_link(date, home_team, away_team, row.get('id'))

        matches_text = f"📋 Próximo jogo do SC Farense ⚫⚪:\n\n"
        matches_text += f"🏆 {additional_details.get('Liga', competition_code)}\n"
        matches_text += f"⚽  {match_desc}\n"

        try:
            full_date_time = f"{date} {time}"
            formatted_date = formatar_data_hora(full_date_time)
            matches_text += f"📅 {formatted_date}\n"
        except Exception:
            matches_text += f"📅 {date} | ⏰ {time}\n"

        matches_text += f"{location_emoji} {additional_details.get('Estádio', 'Não informado')}\n"

        if 'Transmissão' in additional_details:
            matches_text += f"📺 {additional_details['Transmissão']}\n"

        if 'Arbitro' in additional_details:
            matches_text += f"👨‍⚖️ {additional_details['Arbitro']}\n"

        if 'Problemas' in additional_details:
            matches_text += additional_details['Problemas'] + "\n"

        return matches_text.strip()

    return "Sem jogos próximos agendados. 🚫⚽"

def get_next_matches_html():
    """
    Return the HTML of the upcoming matches for Farense.

    Returns:
        str: Formatted HTML of upcoming matches
    """
    return fetch_next_matches()

def get_next_matches_text():
    """
    Generate a plain text description of upcoming matches in a vertical emoji table.

    Returns:
        str: Text description of upcoming matches
    """
    url = 'https://www.zerozero.pt/equipa/farense/10'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    return fetch_next_matches_text(soup)

if __name__ == '__main__':
    print(get_next_matches_text())
