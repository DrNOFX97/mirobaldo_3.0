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

def find_biography_for_query(question: str, max_chars: int = 1500) -> str:
    """
    Search biography files for a player mentioned in the question.
    Returns the biography text if found, empty string otherwise.

    Strategy:
    1. Extract candidate name tokens from the query (nouns after "quem foi", "sobre", etc.)
    2. Scan biography filenames and first-line names for a match
    3. Return the best matching biography (truncated to max_chars)
    """
    from pathlib import Path

    bio_dir = Path(__file__).parent.parent / "data" / "chatbot_dados" / "biografias"
    if not bio_dir.exists():
        return ""

    # Normalise query
    norm_q = remove_accents(question.lower())

    # Extract candidate name: words after trigger phrases, or all words ≥ 3 chars
    trigger_patterns = [
        r'(?:quem foi|fala.me de|conta.me sobre|carreira de|o que fez|conquistas de|apresentar|historia de|sobre)\s+(.+)',
    ]
    candidate = ""
    for pat in trigger_patterns:
        m = re.search(pat, norm_q)
        if m:
            candidate = m.group(1).strip().rstrip('?.')
            break
    if not candidate:
        # Fallback: all words ≥ 3 chars
        candidate = norm_q

    candidate_words = [w for w in candidate.split() if len(w) >= 3]
    if not candidate_words:
        return ""

    # Score all biography files
    all_bio_files = list(bio_dir.rglob("*.txt")) + list(bio_dir.rglob("*.md"))
    best_score = 0
    best_text = ""

    placeholder_markers = ["nao disponiv", "informacoes: n/a", "sem informacao", "sem dados"]

    for bio_file in all_bio_files:
        # Score based on filename match
        fname_norm = remove_accents(bio_file.stem.lower().replace('_', ' ').replace('-', ' '))
        score = sum(1 for w in candidate_words if w in fname_norm)

        if score == 0:
            continue  # skip files with no name match

        # Read full content
        try:
            with open(bio_file, encoding='utf-8') as f:
                content = f.read()

            # Skip placeholder/stub files
            content_norm = remove_accents(content.lower())
            if any(p in content_norm for p in placeholder_markers):
                continue
            if len(content.strip()) < 80:
                continue

            first_line = remove_accents(content.split('\n')[0].lower())
            name_score = sum(1 for w in candidate_words if w in first_line)
            score += name_score

            if score > best_score:
                best_score = score
                best_text = content
        except Exception:
            continue

    if best_score == 0 or not best_text:
        return ""

    return best_text[:max_chars]


def format_biography_as_answer(bio_text: str, name: str) -> str:
    """
    Extract key facts from a biography file and return a clean prose answer.
    Works for both structured .md files (with metadata header) and prose .txt files.
    Returns empty string if insufficient data found.
    """
    import re as _re

    # ── Structured .md: has **DD/MM/YYYY, Place** | **Position** ──────────────
    meta = _re.search(
        r'\*{1,2}(\d{2}/\d{2}/\d{4}),\s*([^*|]+)\*{1,2}\s*\|\s*\*{1,2}([^*\n]+)\*{1,2}',
        bio_text
    )
    if meta:
        date, place, position = [x.strip() for x in meta.groups()]
        parts = [f"{name} nasceu a {date} em {place} e foi {position}."]

        # Career span
        career = _re.search(r'\*\*Carreira:\*\*\s*([^\n]+)', bio_text)
        if career:
            span = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', career.group(1)).strip(' .,')
            if span:
                parts.append(f"A sua carreira decorreu entre {span}.")

        # Clubs: lines with (YYYY-YYYY) or club section headers
        club_names = _re.findall(r'##\s+([^:()\n]+?)(?:\s*[:(]|\s*$)', bio_text, _re.MULTILINE)
        club_names = [c.strip() for c in club_names if len(c.strip()) > 2]
        if club_names:
            parts.append(f"Ao longo da sua carreira, representou: {', '.join(club_names[:5])}.")

        # Titles
        titles = _re.findall(r'🏆[^\n]+', bio_text)
        titles_clean = []
        seen = set()
        for t in titles:
            t = _re.sub(r'[🏆*]', '', t).strip(' -•')
            norm = _re.sub(r'\s+', '', t).upper()
            if t and norm not in seen:
                seen.add(norm)
                titles_clean.append(t)
        if titles_clean:
            parts.append(f"Conquistou: {'; '.join(titles_clean[:3])}.")

        return ' '.join(parts)

    # ── Prose .txt: return first 2 clean paragraphs ───────────────────────────
    clean = _re.sub(r'#{1,6}\s+', '', bio_text)
    clean = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', clean)
    clean = _re.sub(r'<[^>]+>', '', clean)
    clean = _re.sub(r'^[-*•]\s+', '', clean, flags=_re.MULTILINE)
    clean = _re.sub(r'\n{3,}', '\n\n', clean).strip()

    paragraphs = [
        p.strip() for p in clean.split('\n\n')
        if len(p.strip()) > 40 and len(p.strip().split()) >= 8 and any(c in p for c in '.!?;')
    ]

    if paragraphs:
        return '\n\n'.join(paragraphs[:2])

    return ""


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