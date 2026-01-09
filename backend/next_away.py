import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import locale
from datetime import datetime

# Implementação simples para evitar erro na referência a MatchParser
class MatchParser:
    @staticmethod
    def parse_datetime(date_str, time_str):
        """Tenta interpretar data e hora no formato 'dd/mm/yyyy' e 'HH:MM'"""
        if not date_str:
            return None
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
        except ValueError:
            return None

    @staticmethod
    def format_datetime(dt):
        """Formata o objeto datetime para string"""
        return dt.strftime("%d/%m/%Y %H:%M")

class FarenseScraper:
    """Scraper robusto para o SC Farense"""

    BASE_URL = 'https://www.zerozero.pt/equipa/farense/10'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    def __init__(self):
        self.session = requests.Session()
        self.soup = None
        self.matches = []

    def fetch_data(self):
        """Busca e processa dados principais"""
        try:
            response = self.session.get(self.BASE_URL, headers=self.HEADERS, timeout=15)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.content, 'html.parser')
            self._parse_main_table()
        except Exception as e:
            logging.error(f"Erro na obtenção de dados: {str(e)}")

    def _parse_main_table(self):
        """Processa a tabela principal de jogos"""
        table = self.soup.select_one('#page_main > div:nth-child(3)')
        if not table:
            return

        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 9:
                continue

            try:
                match_data = self._extract_match_data(cells)
                if match_data:
                    self.matches.append(match_data)
            except Exception as e:
                logging.error(f"Erro ao processar linha: {str(e)}")

    def _extract_match_data(self, cells):
        """Extrai dados de uma linha da tabela"""
        date_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ''
        time_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ''
        home_team = cells[4].get_text(strip=True) if len(cells) > 4 else ''
        away_team = cells[8].get_text(strip=True) if len(cells) > 8 else ''
        result = cells[6].get_text(strip=True) if len(cells) > 6 else ''

        dt = MatchParser.parse_datetime(date_cell, time_cell)
        formatted_date = MatchParser.format_datetime(dt) if dt else f"{date_cell} {time_cell}"

        return {
            'date': formatted_date,
            'home_team': home_team,
            'away_team': away_team,
            'result': result,
            'is_home': 'Farense' in home_team,
            'competition': self._get_competition(cells[3]),
            'link': self._get_match_link(cells[6])
        }

    def _get_competition(self, cell):
        """Identifica a competição com fallback seguro"""
        try:
            text = cell.find('div', class_='text').get_text(strip=True)
            return {
                'TP': 'Taça de Portugal 🏆',
                'D1': 'Primeira Liga ⚽',
                'h2h': 'Amistoso 🤝'
            }.get(text, 'Outra Competição 🥅')
        except AttributeError:
            return 'Competição desconhecida'

    def _get_match_link(self, cell):
        """Obtém link seguro para detalhes do jogo"""
        try:
            link_element = cell.find('a', href=True)
            if link_element:
                match_link = 'https://www.zerozero.pt' + link_element['href']
                logging.info(f"Match link extracted: {match_link}")
                return match_link
            else:
                logging.warning("Link element not found in cell.")
                return None
        except (TypeError, KeyError) as e:
            logging.error(f"Error extracting match link: {str(e)}")
            return None

    def get_detailed_matches(self):
        """Gera relatório detalhado com tratamento de erros"""
        report = []
        for idx, match in enumerate(self.matches, 1):
            try:
                report.append(self._format_match(match, idx))
                if match['link']:
                    report.append(self._get_additional_details(match['link']))
            except Exception as e:
                logging.error(f"Erro ao formatar jogo {idx}: {str(e)}")
        return '\n'.join(report) or "Nenhum jogo encontrado 🚫⚽"

    def _format_match(self, match, number):
        """Formata os dados básicos do jogo"""
        return (
            f"\n🔢 {number}ª Deslocação\n"
        )

    def _details_url(self, match):
        """Retorna a URL dos detalhes do jogo"""
        return f"{match['link']}"

    def _get_additional_details(self, url):
        """Busca detalhes adicionais com tratamento robusto"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            details = {
                'estádio': self._safe_extract(soup, '.stadium'),
                'cidade': self._safe_extract(soup, '.city'),
                'transmissão': self._safe_extract(soup, '.broadcast'),
                'árbitro': self._safe_extract(soup, '.referee .name')
            }

            return (
                "📌 Detalhes Adicionais:\n" +
                '\n'.join([f"• {k.capitalize()}: {v}" for k, v in details.items() if v]) +
                "\n➖➖➖➖➖➖➖➖➖➖➖➖➖"
            )
        except Exception as e:
            logging.warning(f"Erro nos detalhes de {url}: {str(e)}")
            return "ℹ️ Detalhes adicionais não disponíveis\n"

    def _safe_extract(self, soup, selector):
        """Método seguro para extração de elementos"""
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

def main():
    """Função principal com saída organizada"""
    scraper = FarenseScraper()
    scraper.fetch_data()

    # Filtra e inverte a ordem dos jogos
    away_matches = [m for m in reversed(scraper.matches) if not m['is_home'] and m['result'] == 'vs']

    if away_matches:
        output = "✈️ PRÓXIMOS JOGOS FORA DE CASA\n"

        for i, match in enumerate(away_matches, 1):
            # Adicionar número da deslocação
            output += f"🔢 {i}ª Deslocação\n"
            
            # Define a URL dos detalhes utilizando o método _details_url(match)
            url = scraper._details_url(match)
            if url:
                try:
                    relatorio = RelatorioJogo(url=url)
                    output += relatorio.gerar_relatorio() + "\n"
                except Exception as e:
                    output += f"Erro ao obter relatório: {e}\n"

        return output.strip()
    else:
        return "Nenhum jogo agendado encontrado 🚫⚽"

class RelatorioJogo:
    def __init__(self, url):
        self.url = url
        self.soup = self.obter_html()
        self.detalhes_jogo = self.extrair_detalhes_jogo() if self.soup else {}
        self.equipas = {}
        self.treinadores = {}

    def obter_html(self, max_tentativas=3):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'pt-PT,pt;q=0.9'
        }

        for tentativa in range(max_tentativas):
            try:
                resposta = requests.get(self.url, headers=headers)
                resposta.raise_for_status()
                return BeautifulSoup(resposta.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                if resposta.status_code == 429:
                    tempo_espera = (tentativa + 1) * 2
                    print(f"Limite de pedidos atingido. A aguardar {tempo_espera} segundos...")
                    time.sleep(tempo_espera)
                else:
                    print(f"Erro ao obter URL: {e}")
                    return None

        print("Número máximo de tentativas excedido")
        return None

    def analisar_data_hora(self, data_hora_str):
        """
        Analisa string de data e hora com múltiplos formatos.

        Args:
            data_hora_str (str): String de data e hora

        Returns:
            tuple: (dia_semana, dia, mês, ano, hora, minuto)
        """
        meses = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
            'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
            'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
        }

        dias_semana = {
            'segunda': 0, 'terça': 1, 'quarta': 2, 'quinta': 3, 
            'sexta': 4, 'sábado': 5, 'domingo': 6
        }

        padroes = [
            # Padrão: "Domingo  9 Março 2025 15h30"
            r'(Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)\s*(\d+)\s*([a-zA-Zçã]+)\s*(\d{4})\s*(\d+)h(\d+)',
            
            # Padrões anteriores mantidos
            r'(Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)?\s*(\d+)\s+([a-zA-Z]+)\s+(\d{4})\s+(\d+)h(\d+)',
            r'(Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)?\s*(\d+)/(\d+)/(\d{4})\s+(\d+):(\d+)'
        ]

        for padrao in padroes:
            match = re.search(padrao, data_hora_str, re.IGNORECASE)
            if match:
                # Determinar o dia da semana
                dia_semana_str = match.group(1).lower() if match.group(1) else None
                dia_semana_num = dias_semana.get(dia_semana_str, None)

                # Ajustar os índices de captura baseado na presença do dia da semana
                offset = 1 if dia_semana_str else 0
                
                dia = int(match.group(1 + offset))
                mes_str = match.group(2 + offset).lower()
                mes = meses.get(mes_str, None)
                
                if mes is None:
                    try:
                        # Tentar converter diretamente se for um número
                        mes = int(mes_str)
                    except ValueError:
                        continue
                
                ano = int(match.group(3 + offset))
                hora = int(match.group(4 + offset))
                minuto = int(match.group(5 + offset))

                return dia_semana_num, dia, mes, ano, hora, minuto

        raise ValueError(f"Não foi possível analisar a data: {data_hora_str}")

    def formatar_data_hora(self, data_hora_str):
        """
        Formata a data e hora de forma legível, mantendo o dia da semana.
        
        Args:
            data_hora_str (str): String de data e hora
        
        Returns:
            str: Data formatada de forma legível
        """
        try:
            locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Portuguese_Portugal.1252')
            except locale.Error:
                pass

        try:
            # Atualizar para lidar com o novo formato de retorno
            dia_semana_num, dia, mes, ano, hora, minuto = self.analisar_data_hora(data_hora_str)
            
            # Criar objeto datetime
            data_hora = datetime(ano, mes, dia, hora, minuto)
            
            # Mapear número do dia da semana para nome
            dias_semana = [
                'Segunda-feira', 'Terça-feira', 'Quarta-feira', 
                'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
            ]
            
            # Formatar data mantendo o dia da semana
            dia_semana_nome = dias_semana[dia_semana_num] if dia_semana_num is not None else ''
            data_formatada = f"{dia_semana_nome}, {dia} de {data_hora.strftime('%B')} de {ano} às {hora:02d}:{minuto:02d}"
            
            return data_formatada.capitalize()
        except ValueError as e:
            print(f"Erro na conversão de data: {e}")
            return data_hora_str
        finally:
            locale.setlocale(locale.LC_TIME, '')

    def extrair_detalhes_jogo(self):
        detalhes = {}
        try:
            dados_jogo = self.soup.find('div', id='match_data')

            if dados_jogo:
                # Extrair equipas
                equipa_casa = self.soup.find('div', class_='home').find('a')
                equipa_fora = self.soup.find('div', class_='away').find('a')
                detalhes['Equipa Casa'] = equipa_casa.get_text(strip=True) if equipa_casa else "Equipa não encontrada"
                detalhes['Equipa Fora'] = equipa_fora.get_text(strip=True) if equipa_fora else "Equipa não encontrada"

                # Extrair data e hora
                icone_data = dados_jogo.find('i', class_='fa-regular fa-calendar')
                icone_hora = dados_jogo.find('i', class_='fa-regular fa-clock')
                data = icone_data.next_sibling.strip() if icone_data else "Data não encontrada"
                hora = icone_hora.next_sibling.strip() if icone_hora else "Hora não encontrada"
                data_hora = f"{data} {hora}"
                detalhes['Data'] = self.formatar_data_hora(data_hora)

                # Extrair estádio
                icone_estadio = dados_jogo.find('i', class_='fa-solid fa-location-dot')
                link_estadio = icone_estadio.find_next('a') if icone_estadio else None
                if link_estadio:
                    nome_estadio = link_estadio.get_text(strip=True)
                    localizacao = link_estadio.find_next_sibling(string=True).strip('() ')
                    detalhes['Estádio'] = f"{nome_estadio} ({localizacao})"
                else:
                    detalhes['Estádio'] = "Estádio não encontrado"

                # Extrair espectadores e transmissão
                icone_espectadores = dados_jogo.find('i', class_='fa-solid fa-people-group')
                icone_tv = dados_jogo.find('i', class_='fa-solid fa-tv')
                detalhes['Espectadores'] = icone_espectadores.next_sibling.strip() if icone_espectadores else None
                detalhes['Transmissão TV'] = icone_tv.next_sibling.strip() if icone_tv else None

                # Extrair árbitro
                icone_arbitro = dados_jogo.find('i', class_='fa-regular fa-user')
                if icone_arbitro:
                    link_arbitro = icone_arbitro.find_next('a')
                    detalhes['Árbitro'] = link_arbitro.get_text(strip=True) if link_arbitro else None

                # Extrair competição
                elem_competicao = dados_jogo.find('a', href=lambda href: href and 'edicao' in href)
                detalhes['Competição'] = elem_competicao.get_text(strip=True) if elem_competicao else None

                # Extrair jornada ou fase
                texto_jornada = dados_jogo.get_text(strip=True)
                match_jornada = re.search(r'Jornada (\d+)', texto_jornada)
                if match_jornada:
                    detalhes['Jornada'] = f"Jornada {match_jornada.group(1)}"
                else:
                    # Extrair texto após o hífen
                    match_fase = re.search(r'-\s*(.+)', texto_jornada)
                    detalhes['Jornada'] = match_fase.group(1).strip() if match_fase else None

        except Exception as e:
            print(f"Erro ao extrair detalhes do jogo: {e}")

        return detalhes

    def gerar_relatorio(self):
        equipa_casa = self.detalhes_jogo.get('Equipa Casa', 'N/D')
        equipa_fora = self.detalhes_jogo.get('Equipa Fora', 'N/D')

        relatorio = f"""
=============================
{equipa_casa} - {equipa_fora}
=============================
{self.detalhes_jogo.get('Competição', '') if self.detalhes_jogo.get('Competição') else ''}
{self.detalhes_jogo.get('Jornada', '') if self.detalhes_jogo.get('Jornada') else ''}
{self.detalhes_jogo.get('Data', '') if self.detalhes_jogo.get('Data') else ''}
{self.detalhes_jogo.get('Estádio', '') if self.detalhes_jogo.get('Estádio') else ''}
{self.detalhes_jogo.get('Transmissão TV', '') if self.detalhes_jogo.get('Transmissão TV') else 'Sem transmissão'}
Árbitro: {self.detalhes_jogo.get('Árbitro', '') if self.detalhes_jogo.get('Árbitro') else ''}
------------------------------------
"""   
        return relatorio.strip()

if __name__ == "__main__":
    print(main())