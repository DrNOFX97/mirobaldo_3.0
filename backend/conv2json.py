import json
import logging
import re

# Configurar o logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_fields(line):
    # Definir padrões regex para cada campo
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    time_pattern = r'(\d{2}:\d{2})'
    local_pattern = r'(Casa|Fora)'
    equipa_pattern = r'([a-zA-Z\s]+)'  # Assume que a equipa é qualquer sequência de letras e espaços
    resultado_pattern = r'(\d+-\d+)'
    ved_pattern = r'(V|E|D)'
    jornada_pattern = r'(\d+[ªº]?\s*Jornada)'  # Assume que a jornada pode ter "ª" ou "º" e "Jornada"

    # Dicionário para armazenar os resultados
    record = {
        "data": None,
        "hora": None,
        "local": None,
        "equipa": None,
        "resultado": None,
        "VED": None,
        "jornada": None
    }

    # Procurar cada padrão na linha
    if match := re.search(date_pattern, line):
        record["data"] = match.group(1).strip()

    if match := re.search(time_pattern, line):
        record["hora"] = match.group(1).strip()

    if match := re.search(local_pattern, line):
        record["local"] = match.group(1).strip()

    if match := re.search(resultado_pattern, line):
        record["resultado"] = match.group(1).strip()

    if match := re.search(ved_pattern, line):
        record["VED"] = match.group(1).strip()

    if match := re.search(jornada_pattern, line):
        record["jornada"] = match.group(1).strip()

    # Extrair a equipa removendo os outros campos já identificados
    for key, value in record.items():
        if value and key != "equipa":
            line = line.replace(value, "")

    # Remover espaços extras e capturar a equipa
    line = re.sub(r'\s+', ' ', line).strip()
    record["equipa"] = line

    return record

def convert_txt_to_json(input_file, output_file):
    logging.info(f"Iniciando a conversão do arquivo {input_file} para JSON.")

    # Lista para armazenar os dicionários
    data = []

    try:
        # Ler o arquivo de texto
        with open(input_file, 'r') as file:
            logging.debug(f"Abrindo o arquivo {input_file} para leitura.")
            for line in file:
                line = line.strip()
                if not line:
                    logging.warning("Linha vazia encontrada, pulando.")
                    continue

                logging.debug(f"Processando a linha: {line}")

                # Extrair campos da linha
                record = extract_fields(line)

                # Adicionar o dicionário à lista
                data.append(record)
                logging.debug(f"Dicionário criado: {record}")

        # Escrever a lista de dicionários em um arquivo JSON
        with open(output_file, 'w') as json_file:
            logging.debug(f"Escrevendo dados em {output_file}")
            json.dump(data, json_file, indent=4)
            logging.info(f"Conversão concluída. Dados salvos em {output_file}")

    except Exception as e:
        logging.error(f"Ocorreu um erro: {e}")

# Usar a função para converter o arquivo
convert_txt_to_json('hist_result.txt', 'hist_result.json')
