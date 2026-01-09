import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from tabulate import tabulate

def extrair_titulo_subtitulo(url_competicao):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
    }
    response = requests.get(url_competicao, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        subtitle = soup.select_one("#zz-enthdr > div.zz-enthdr-top > div.zz-enthdr-data > div.text")
        title = soup.select_one("#zz-enthdr > div.zz-enthdr-top > div.zz-enthdr-data > h1 > span")
        return title.text.strip() if title else 'Título não encontrado', subtitle.text.strip() if subtitle else None
    return 'Erro ao carregar a página', None

def extrair_classificacao(url_competicao):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
    }
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(url_competicao, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table_element = soup.find('table', class_='zztable stats zz-datatable')
        if not table_element:
            return None
        rows = table_element.find_all('tr')
        data = []
        for row in rows[1:]:
            cols = row.find_all('td')
            row_data = [col.text.strip() for col in cols]
            data.append(row_data)
        headers = [th.text.strip() for th in rows[0].find_all('th')]
        df = pd.DataFrame(data, columns=headers)
        if len(df.columns) > 1:
            df = df.iloc[:, :-1]  # Remove a última coluna
        return df
    except Exception as e:
        print(f"Erro ao processar a classificação: {e}")
        return None

def get_classification_text(url_competicao="https://www.zerozero.pt/edicao/-/187713"):
    """
    Fetch and parse league classification table for Farense.
    
    Args:
        url_competicao (str): URL of the league/competition
    
    Returns:
        str: Formatted text of league classification
    """
    try:
        # Fetch classification data
        df = extrair_classificacao(url_competicao)
        
        if df is None:
            return "Sem informações de classificação. 🚫📊"
        
        # Fetch title and subtitle for context
        title, subtitle = extrair_titulo_subtitulo(url_competicao)
        
        # Create a formatted classification text
        classification_text = f"🏆 {title}\n"
        
        if subtitle:
            classification_text += f"{subtitle}\n\n"
        
        # Convert DataFrame to formatted text
        for index, row in df.iterrows():
            # Assuming the first column is position and third is team name
            position = row.iloc[0]
            team_name = row.iloc[2]
            points = row.iloc[3]
            
            classification_text += f"{position}º {team_name} - {points} pontos\n"
        
        return classification_text.strip()

    except Exception as e:
        print(f"Erro ao processar a classificação: {e}")
        return "Não foi possível recuperar a classificação. 🚫📊"

def tabela_classificativa(urls_competicoes=None):
    """
    Generate a sans-serif, monospaced classification table.
    
    Args:
        urls_competicoes (list, optional): List of competition URLs
    
    Returns:
        str: Formatted classification table
    """
    if urls_competicoes is None:
        urls_competicoes = ["https://www.zerozero.pt/competicao/liga-portuguesa"]
    
    try:
        # Fetch the first URL in the list
        url = urls_competicoes[0]
        
        # Fetch classification data
        df = extrair_classificacao(url)
        
        if df is None:
            return "Sem informações de classificação. 🚫📊"
        
        # Fetch title and subtitle for context
        title, subtitle = extrair_titulo_subtitulo(url)
        
        # Prepare the table
        table_text = f"🏆 `{title}`\n"
        if subtitle:
            table_text += f"`{subtitle}`\n\n"
        
        # Create a sans-serif, monospaced table
        table_text += "```\n"
        table_text += "POS EQUIPA            PTS   J  V  E  D  GM  GS  DG\n"
        table_text += "------------------------------------------------\n"
        
        for index, row in df.iterrows():
            # Extract relevant columns
            pos = row.iloc[0]
            team = row.iloc[2][:17]  # Truncate team name if too long
            pts = row.iloc[3]
            j = row.iloc[4]
            v = row.iloc[5]
            e = row.iloc[6]
            d = row.iloc[7]
            gm = row.iloc[8]
            gs = row.iloc[9]
            dg = row.iloc[10]
            
            # Highlight Farense row
            if 'Farense' in team:
                table_text += f"**{pos:>3}** **{team:<17}** **{pts:>3}** {j:>2} {v:>2} {e:>2} {d:>2} {gm:>3} {gs:>3} {dg:>3} 🔵⚪\n"
            else:
                table_text += f"{pos:>3} {team:<17} {pts:>3} {j:>2} {v:>2} {e:>2} {d:>2} {gm:>3} {gs:>3} {dg:>3}\n"
        
        table_text += "```"
        
        return table_text

    except Exception as e:
        print(f"Erro ao processar a classificação: {e}")
        return "Não foi possível recuperar a classificação. 🚫📊"

if __name__ == '__main__':
    urls_competicoes = ["https://www.zerozero.pt/edicao/-/187713"]
    print(tabela_classificativa(urls_competicoes))

