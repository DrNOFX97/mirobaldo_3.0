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

def get_classification_text(url_competicao="https://www.zerozero.pt/competicao/liga-portuguesa"):
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

def tabela_classificativa(url_competicao=None):
    """
    Generate a league classification DataFrame.
    
    Args:
        url_competicao (str, optional): URL of the league/competition
    
    Returns:
        pd.DataFrame: Classification table
    """
    if url_competicao is None:
        url_competicao = "https://www.zerozero.pt/competicao/liga-portuguesa"
    
    try:
        # Fetch the first URL in the list
        url = url_competicao[0] if isinstance(url_competicao, list) else url_competicao
        
        # Fetch classification data
        df = extrair_classificacao(url)
        
        if df is None:
            return pd.DataFrame()  # Return empty DataFrame instead of string
        
        # Ensure DataFrame has expected columns
        if len(df.columns) < 11:
            return pd.DataFrame()
        
        # Select and rename columns for clarity
        classification_df = df.iloc[:, [0, 2, 3, 4, 5, 6, 7, 8, 9, 10]].copy()
        classification_df.columns = ['POS', 'EQUIPA', 'PTS', 'J', 'V', 'E', 'D', 'GM', 'GS', 'DG']
        
        return classification_df

    except Exception as e:
        print(f"Erro ao processar a classificação: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

if __name__ == '__main__':
    url_competicao = ["https://www.zerozero.pt/competicao/liga-portuguesa"]
    print(tabela_classificativa(url_competicao))
