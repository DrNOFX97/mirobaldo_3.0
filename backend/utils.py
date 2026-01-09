# Essential imports
import unicodedata
import logging
import json
import re
import os

logger = logging.getLogger(__name__)

def remove_accents(input_str):
    """
    Remove accents from a string.
    
    Args:
        input_str (str): Input string with potential accents
    
    Returns:
        str: String with accents removed
    """
    if not isinstance(input_str, str):
        return input_str
    
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

def find_relevant_context(question, historical_text, max_context_length=4000):
    """
    Find the most relevant context for a given question.
    
    Args:
        question (str): User's query
        historical_text (str): Full historical text
        max_context_length (int): Maximum length of context to return
    
    Returns:
        str: Most relevant context snippet
    """
    try:
        # Normalize question
        normalized_question = remove_accents(question.lower())
        
        # If no historical text is provided, return a default message
        if not historical_text or len(historical_text.strip()) < 10:
            return "Não encontrei informações relevantes para esta pergunta."
        
        # Split historical text into paragraphs
        paragraphs = historical_text.split('\n\n')
        
        # Find paragraphs that might be relevant
        keywords = [
            'sporting', 'farense', 'futebol', 'clube', 
            'história', 'jogo', 'resultado', 'gago', 'gralho'
        ]
        
        relevant_paragraphs = [
            p for p in paragraphs 
            if any(keyword in remove_accents(p.lower()) for keyword in keywords)
        ]
        
        # If no relevant paragraphs found, return a default message
        if not relevant_paragraphs:
            return "Não encontrei informações relevantes para esta pergunta."
        
        # Sort paragraphs by length to get most informative
        relevant_paragraphs.sort(key=len, reverse=True)
        
        # Take top 3 paragraphs and truncate to max length
        context = '\n\n'.join(relevant_paragraphs[:3])[:max_context_length]
        
        return context.strip() or "Não encontrei informações relevantes para esta pergunta."
    
    except Exception as e:
        logger.error(f"Error in find_relevant_context: {e}")
        return "Não encontrei informações relevantes para esta pergunta."

def read_historical_results_from_db(table_name):
    """
    Read historical results from a JSON file.
    
    Args:
        table_name (str): Name of the table/data source
    
    Returns:
        list: Historical results
    """
    try:
        # Map table names to files
        table_file_map = {
            'historical_results': '50_anos.json',
            'historical_50_years': 'dados_jogos.json'
        }
        
        file_path = table_file_map.get(table_name)
        if not file_path:
            logger.error(f"No file mapping for table: {table_name}")
            return []
        
        # Use absolute path to ensure file is found
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        
        with open(full_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    except Exception as e:
        logger.error(f"Error reading historical results for {table_name}: {e}")
        return []

def get_antonio_gago_biography():
    """
    Retrieve António Gago's biography with rich formatting.
    
    Returns:
        dict: Biography details or error information
    """
    try:
        # Use absolute path to ensure file is found
        biography_path = os.path.join(os.path.dirname(__file__), 'antonio_gago.json')
        
        # Log file path for debugging
        logger.debug(f"Attempting to read biography from: {biography_path}")
        
        # Verify file exists
        if not os.path.exists(biography_path):
            logger.error(f"Biography file not found: {biography_path}")
            return {
                'error': 'Arquivo de biografia não encontrado',
                'details': f'Caminho: {biography_path}'
            }
        
        # Read biography file
        with open(biography_path, 'r', encoding='utf-8') as file:
            biography_json = json.load(file)
        
        # Log raw JSON for debugging
        logger.debug(f"Raw biography JSON: {json.dumps(biography_json, indent=2)}")
        
        # Prepare structured biography
        biography = {
            'nome_completo': biography_json['dados_biograficos']['nome_completo'],
            'nascimento': biography_json['dados_biograficos']['nascimento'],
            'falecimento': biography_json['dados_biograficos']['falecimento'],
            'socio_numero': biography_json['dados_biograficos']['socio_numero'],
            'percurso': biography_json['percurso_no_sporting_clube_farense'],
            'contribuicoes': biography_json.get('contribuicoes_alem_do_futebol', [])
        }
        
        # Log structured biography
        logger.info(f"Successfully retrieved biography for {biography['nome_completo']}")
        logger.debug(f"Structured biography: {json.dumps(biography, indent=2)}")
        
        return biography
    
    except KeyError as ke:
        # Handle missing keys in JSON
        logger.error(f"Missing key in biography JSON: {ke}")
        return {
            'error': 'Formato de biografia inválido',
            'details': str(ke)
        }
    
    except Exception as e:
        # Catch-all for other errors
        logger.error(f"Error retrieving António Gago's biography: {e}", exc_info=True)
        return {
            'error': 'Biografia indisponível',
            'details': str(e)
        }

    # Add more extraction logic as needed

    biography = " ".join(bio_sections)
    return biography.strip() if biography else "Não encontrei informações detalhadas sobre João Gralho."