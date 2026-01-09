"""
Chatbot Farense Endpoint para mirobaldo.pt
Integra o sistema RAG do Farense no app Flask existente
"""

import sys
import warnings
import os
import io
import re
import contextlib

# Suprimir warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

@contextlib.contextmanager
def suppress_stderr():
    save_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = save_stderr

# Adicionar path para módulos do chatbot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chatbot_farense'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chatbot_farense', 'backend'))

import logging
logging.disable(logging.CRITICAL)

# Importar funções do chat
with suppress_stderr():
    from chat_simple import parse_query, smart_file_search, format_response, get_response, filter_results

def extract_photos_from_response(response_text):
    """Extrair fotos da resposta formatada"""
    photos = re.findall(r'📷 Foto: ([^\n]+)', response_text)
    return photos

def format_response_for_api(response_text):
    """Formatar resposta para API (remover linhas de foto para retornar em campo separado)"""
    cleaned = re.sub(r'📷 Foto: [^\n]+\n*', '', response_text)
    return cleaned.strip()

def farense_chatbot_query(query, k=15):
    """
    Processa query do chatbot Farense

    Args:
        query (str): Pergunta do utilizador
        k (int): Número de documentos a retornar (default: 15)

    Returns:
        dict: {
            'success': bool,
            'query': str,
            'response': str,
            'photos': list,
            'metadata': dict
        }
    """
    try:
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Query vazia'
            }

        # Parse query
        with suppress_stderr():
            parsed_query = parse_query(query)

            # Smart search ou RAG
            docs = smart_file_search(query, parsed_query)
            if not docs:
                docs = get_response(query, k=k)

            if not docs:
                return {
                    'success': False,
                    'error': 'Nenhum documento encontrado',
                    'query': query
                }

            # Filter
            if docs[0].get('score', 0) < 0.99:
                filtered_docs = filter_results(docs, parsed_query)
            else:
                filtered_docs = docs

            if not filtered_docs:
                return {
                    'success': False,
                    'error': 'Nenhum documento relevante após filtragem',
                    'query': query
                }

            # Format response
            response_text = format_response(query, filtered_docs)

        # Extract photos
        photos = extract_photos_from_response(response_text)

        # Clean response text (remover linhas de foto)
        cleaned_response = format_response_for_api(response_text)

        return {
            'success': True,
            'query': query,
            'response': cleaned_response,
            'photos': photos,
            'metadata': {
                'type': parsed_query.get('type', 'unknown'),
                'player_name': parsed_query.get('player_name'),
                'season': parsed_query.get('season'),
                'category': parsed_query.get('category'),
                'is_biography': parsed_query.get('is_biography', False),
                'is_result': parsed_query.get('is_result', False),
                'docs_retrieved': len(docs),
                'docs_after_filter': len(filtered_docs),
                'response_length': len(cleaned_response),
                'photos_count': len(photos)
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': query
        }
