# Standard library imports
import os
import sys
import json
import logging
import threading
import webbrowser
import socket
import traceback
import pandas as pd 
from flask import Response, stream_with_context
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mirobaldo_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Flask and other web-related imports
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Import utility functions and other dependencies
from utils import (
    remove_accents,
    find_relevant_context,
    read_historical_results_from_db,
    get_antonio_gago_biography
)
from chatbot import mirobaldo_chatbot

# Import Farense chatbot
try:
    from chatbot_farense_endpoint import farense_chatbot_query
    FARENSE_CHATBOT_AVAILABLE = True
    logger.info("✅ Farense Chatbot carregado com sucesso")
except Exception as e:
    FARENSE_CHATBOT_AVAILABLE = False
    logger.error(f"❌ Erro ao carregar Farense Chatbot: {e}")

# Get the absolute path of the project directory
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(PROJECT_DIR), 'frontend', 'mirobaldo_src')

# Create Flask app with correct template and static folders
app = Flask(__name__,
            template_folder=FRONTEND_DIR,
            static_folder=os.path.join(FRONTEND_DIR, 'static'),
            static_url_path='/static')
CORS(app)

# Verify template and static folder paths
print(f"Template Folder: {app.template_folder}")
print(f"Static Folder: {app.static_folder}")
print(f"Static URL Path: {app.static_url_path}")

# Load historical context
def load_historical_data():
    """
    Load historical data from JSON files.
    
    Returns:
        dict: Loaded historical data
    """
    try:
        with open('50_anos.json', 'r', encoding='utf-8') as f:
            historical_context = f.read()
        
        with open('dados_jogos.json', 'r', encoding='utf-8') as f:
            historical_results = json.load(f)
        
        return {
            'context': historical_context,
            'results': historical_results
        }
    except Exception as e:
        logging.error(f"Error loading historical data: {e}")
        return {'context': '', 'results': []}

# Global historical data
HISTORICAL_DATA = load_historical_data()

# Simplified route handlers
@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    """
    Main chatbot API endpoint with streaming support.
    
    Returns:
        Streaming JSON response with chatbot's answer or error details
    """
    try:
        # Validate request
        if not request.is_json:
            logger.warning("Received non-JSON request to chatbot endpoint")
            return jsonify({
                'error': 'Formato de requisição inválido',
                'details': 'Por favor, envie um JSON válido.'
            }), 400
        
        # Parse request data
        data = request.get_json()
        logger.debug(f"Received chatbot request data: {data}")
        
        # Extract question, supporting multiple keys
        question = (
            data.get('question') or 
            data.get('message') or 
            data.get('query') or 
            ''
        ).strip()
        
        # Validate question
        if not question:
            logger.warning("No question provided in chatbot request")
            return jsonify({
                'error': 'Nenhuma pergunta fornecida',
                'response': 'Por favor, faça uma pergunta sobre o Sporting Clube Farense.'
            }), 400
        
        # Validate historical data
        if not HISTORICAL_DATA or 'context' not in HISTORICAL_DATA:
            logger.error("Historical data context is missing or empty")
            return jsonify({
                'error': 'Dados históricos não carregados',
                'response': 'Erro interno: dados históricos não disponíveis.'
            }), 500
        
        # Detailed logging before processing
        logger.info(f"Processing chatbot query: {question}")
        logger.debug(f"Historical context length: {len(HISTORICAL_DATA['context'])} characters")
        
        def generate_response():
            try:
                # Process query using chatbot
                response = mirobaldo_chatbot(
                    question, 
                    HISTORICAL_DATA['context']
                )
                
                # Handle classification table specifically
                if isinstance(response, pd.DataFrame):
                    # Ensure DataFrame has expected columns
                    expected_columns = ['POS', 'EQUIPA', 'PTS', 'J', 'V', 'E', 'D', 'GM', 'GS', 'DG']
                    if not all(col in response.columns for col in expected_columns):
                        logger.error(f"Unexpected DataFrame columns: {list(response.columns)}")
                        yield json.dumps({'message': 'Erro na formatação da classificação.'}) + '\n'
                        return
                    
                    # Define column widths
                    widths = {
                        'POS': 3,     # Position
                        'EQUIPA': 15,  # Team name
                        'PTS': 4,     # Points
                        'J': 3,       # Games played
                        'V': 3,       # Wins
                        'E': 3,       # Draws
                        'D': 3,       # Losses
                        'GM': 4,      # Goals scored
                        'GS': 4,      # Goals conceded
                        'DG': 4       # Goal difference
                    }
                    
                    # Create header
                    header = ''.join(f'{col:{widths[col]}}' for col in widths.keys())
                    
                    # Create separator
                    separator = '-' * len(header)
                    
                    # Format rows
                    rows = []
                    for _, row in response.iterrows():
                        try:
                            # Prepare row data
                            row_data = {
                                'POS': row['POS'],
                                'EQUIPA': row['EQUIPA'],
                                'PTS': row['PTS'],
                                'J': row['J'],
                                'V': row['V'],
                                'E': row['E'],
                                'D': row['D'],
                                'GM': row['GM'],
                                'GS': row['GS'],
                                'DG': row['DG']
                            }
                            
                            # Format the row
                            formatted_row = ''.join(
                                f'{str(row_data[col]):{widths[col]}}' for col in widths.keys()
                            )
                            rows.append(formatted_row)
                        except Exception as e:
                            logger.error(f"Error formatting row: {e}")
                            logger.error(f"Row data: {row}")
                    
                    # Combine all parts
                    table_lines = [header, separator] + rows
                    formatted_table = '\n'.join(table_lines)
                    
                    # Yield the formatted table
                    yield json.dumps({'message': formatted_table}) + '\n'
                    return  # Stop processing after yielding the table
                elif isinstance(response, str):
                    # For string responses, stream in chunks
                    for i in range(0, len(response), 20):
                        chunk = response[i:i+20]
                        yield json.dumps({'message': chunk}) + '\n'
                else:
                    # For other types, convert to string and stream
                    response_str = str(response)
                    for i in range(0, len(response_str), 20):
                        chunk = response_str[i:i+20]
                        yield json.dumps({'message': chunk}) + '\n'
            
            except Exception as e:
                # Detailed logging for chatbot processing errors
                logger.error(f"Chatbot processing error: {e}", exc_info=True)
                yield json.dumps({
                    'error': 'Erro no processamento da pergunta',
                    'message': 'Desculpe, não foi possível processar sua pergunta no momento.'
                }) + '\n'
        
        # Return streaming response
        return Response(
            stream_with_context(generate_response()), 
            mimetype='text/event-stream'
        )
    
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.critical(f"Unexpected error in chatbot endpoint: {e}", exc_info=True)
        return jsonify({
            'error': 'Erro interno do servidor',
            'message': 'Ocorreu um erro inesperado. Por favor, tente novamente.'
        }), 500

@app.route('/api/biography/antonio_gago', methods=['GET'])
def api_antonio_gago_biography():
    """
    API endpoint for António Gago's biography.
    
    Returns:
        JSON response with biography details
    """
    biography = get_antonio_gago_biography()
    return jsonify(biography)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/last_matches', methods=['GET', 'POST'])
def api_last_matches():
    """
    API endpoint to retrieve last matches.
    
    Returns:
        JSON response with last matches
    """
    logger.info(f"Last matches route called. Method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request data: {request.get_data()}")
    
    try:
        from last_matches import get_last_matches_text
        last_matches = get_last_matches_text()
        return jsonify({"last_matches": last_matches})
    except Exception as e:
        logger.error(f"Error retrieving last matches: {e}", exc_info=True)
        return jsonify({"error": "Não foi possível recuperar os últimos resultados"}), 500

@app.route('/api/next_matches', methods=['GET', 'POST'])
def api_next_matches():
    """
    API endpoint to retrieve next matches.
    
    Returns:
        JSON response with next matches
    """
    logger.info(f"Next matches route called. Method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request data: {request.get_data()}")
    
    try:
        from next_matches import get_next_matches_text
        next_matches = get_next_matches_text()
        return jsonify({"next_matches": next_matches})
    except Exception as e:
        logger.error(f"Error retrieving next matches: {e}", exc_info=True)
        return jsonify({"error": "Não foi possível recuperar os próximos jogos"}), 500

@app.route('/api/classification', methods=['GET'])
def api_classification():
    """
    API endpoint to retrieve league classification.
    
    Returns:
        JSON response with classification
    """
    try:
        from classificação import tabela_classificativa
        classification = tabela_classificativa()
        return jsonify({"classification": classification})
    except Exception as e:
        logger.error(f"Error retrieving classification: {e}")
        return jsonify({"error": "Não foi possível recuperar a classificação"}), 500

@app.route('/api/next_away_game', methods=['GET'])
def api_next_away_game():
    """
    API endpoint to retrieve next away game.
    
    Returns:
        JSON response with next away game details
    """
    try:
        from next_away import main as get_next_away_game
        away_game = get_next_away_game()
        return jsonify({"away_game": away_game})
    except Exception as e:
        logger.error(f"Error retrieving next away game: {e}")
        return jsonify({"away_game": "Erro ao obter a próxima deslocação."}), 500

@app.route('/api/historical_results', methods=['POST', 'GET'])
def get_historical_results():
    print(" HISTORICAL RESULTS API CALLED")
    sys.stdout.flush()
    logger.critical(" HISTORICAL RESULTS API CALLED")

    try:
        # Get request data safely for both POST and GET
        if request.method == 'POST':
            data = request.get_json(force=True)
            query = data.get('query', '').strip()
        else:  # GET method
            query = request.args.get('query', '').strip()

        print(f" HISTORICAL RESULTS QUERY: {query}")
        sys.stdout.flush()
        logger.critical(f" HISTORICAL RESULTS QUERY: {query}")

        # Extract season dynamically from the query
        def extract_season(query):
            # More comprehensive season patterns
            season_patterns = [
                r'(\d{4}/\d{2})',     # 1989/90
                r'(\d{4}/\d{4})',     # 1989/1990
                r'(\d{4}-\d{2})',     # 1989-90
                r'(\d{4}-\d{4})',     # 1989-1990
            ]

            # Normalize the query
            query = query.lower().replace(' ', '')

            for pattern in season_patterns:
                match = re.search(pattern, query)
                if match:
                    season = match.group(1)

                    # Normalize season format
                    if '/' in season:
                        parts = season.split('/')
                        season = f"{parts[0]}-{parts[1]}"

                    print(f" SEASON EXTRACTED: {season}")
                    sys.stdout.flush()
                    logger.critical(f" SEASON EXTRACTED: {season}")
                    return season

            # If no explicit season found, try to infer from context or use current season
            current_year = datetime.now().year
            current_season = f"{current_year-1}-{str(current_year)[2:]}"

            print(f" NO SEASON FOUND, USING DEFAULT: {current_season}")
            sys.stdout.flush()
            logger.critical(f" NO SEASON FOUND, USING DEFAULT: {current_season}")

            return current_season

        # Identify specific competition types in the query
        def identify_competition_type(query):
            competition_keywords = {
                # League Competitions
                "campeonato": [
                    "campeonato", "liga", "primeira divisão", "segunda divisão", "terceira divisão", 
                    "I divisão", "II divisão", "III divisão", 
                    "campeonato do algarve", "campeonato de portugal", 
                    "liga nos", "liga portugal", "liga portugal betclic", 
                    "liga pro", "ledman ligapro", "segunda liga"
                ],
                "liga": [
                    "liga", "campeonato", "primeira divisão", "segunda divisão", "terceira divisão", 
                    "I divisão", "II divisão", "III divisão", 
                    "liga nos", "liga portugal", "liga portugal betclic", 
                    "liga pro", "ledman ligapro", "segunda liga", 
                    "liga 2 sabseg", "ii liga"
                ],
                
                # Cup Competitions
                "taça": [
                    "taça", "cup", "troféu", 
                    "taça de portugal", "taça da liga", "taça ctt", 
                    "allianz cup", "allianz"
                ],
                
                # Division-specific Competitions
                "divisão": [
                    # Specific Division Types
                    "II divisão", "III divisão", 
                    "divisão zona sul", "divisão zona d", "divisão zona c", 
                    "divisão algarve", "divisão série", 
                    
                    # Specific Historical Divisions
                    "II divisão grupo d", "II divisão grupo sul", 
                    "III divisão zona d", "III divisão zona sul",
                    
                    # Phase and Qualification Competitions
                    "liguilha", "fase final", "jogos de passagem", 
                    "fase de apuramento", "fase de subida", 
                    "II divisão fase final", "III divisão fase final"
                ],
                
                # Seasonal Identifiers
                "época": ["época", "temporada", "ano", "season"]
            }

            query_lower = query.lower()
            identified_types = []

            for comp_type, keywords in competition_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    identified_types.append(comp_type)

            return identified_types

        # Get the target season
        target_season = extract_season(query)

        # Identify competition types from the query
        competition_types = identify_competition_type(query)

        # Read historical results from JSON
        json_path = os.path.join(os.path.dirname(__file__), 'dados_jogos.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            historical_data = json.load(f)

        # Print available seasons for debugging
        available_seasons = list(historical_data.keys())
        print(f" AVAILABLE SEASONS: {available_seasons}")
        sys.stdout.flush()
        logger.critical(f" AVAILABLE SEASONS: {available_seasons}")

        # Collect all competitions for the target season
        all_competitions = []
        for competition_name, matches in historical_data.get(target_season, {}).items():
            # Translate competition name
            translated_comp = competition_name

            # Filter matches based on identified competition types
            if competition_types:
                if not any(comp_type in competition_name.lower() for comp_type in competition_types):
                    continue

            # Collect results for this competition
            competition_results = []
            for match in matches:
                # Determine home and away teams based on 'Local'
                if match.get('Local') == 'Casa':
                    home_team = '**SC Farense**'
                    away_team = match.get('Equipa', 'N/A')
                    result = match.get('Resultado', 'N/A')
                else:
                    home_team = match.get('Equipa', 'N/A')
                    away_team = '**SC Farense**'
                    result = match.get('Resultado', 'N/A')

                result_entry = {
                    'jornada': JORNADA_TRANSLATIONS.get(match.get('Jornada', ''), match.get('Jornada', '')),
                    'data': match.get('Data', 'N/A'),
                    'home_team': home_team,
                    'result': result,
                    'away_team': away_team,
                    'ved': VED_TRANSLATIONS.get(match.get('V-E-D', ''), match.get('V-E-D', ''))
                }
                competition_results.append(result_entry)

            # Sort results by date
            competition_results.sort(key=lambda x: x['data'])

            # Add to all competitions
            all_competitions.append({
                'name': translated_comp,
                'results': competition_results
            })

        # Prepare response text
        response_text = f" *Competições na Temporada {target_season}*:\n"

        if all_competitions:
            for comp_index, competition in enumerate(all_competitions, 1):
                response_text += f"\n**{comp_index}. {competition['name']}**:\n"

                if competition['results']:
                    for match_index, match in enumerate(competition['results'], 1):
                        # New formatting style
                        response_text += f"{match['jornada']} | {match['data']} |{match['home_team']} {match['result']} {match['away_team']}\n"
                else:
                    response_text += "      Sem resultados encontrados\n\n"
        else:
            response_text += "Nenhuma competição encontrada para esta temporada.\n"

        def generate():
            try:
                yield json.dumps({"message": response_text}) + "\n"

            except Exception as e:
                error_message = f"Erro ao processar resultados: {e}"
                print(f" ERROR IN HISTORICAL RESULTS: {e}")
                sys.stdout.flush()
                logger.critical(f" ERROR IN HISTORICAL RESULTS: {e}")

                yield json.dumps({"message": error_message}) + "\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f" INITIAL HISTORICAL RESULTS REQUEST ERROR: {e}")
        sys.stdout.flush()
        logger.critical(f" INITIAL HISTORICAL RESULTS REQUEST ERROR: {e}")

        return jsonify({"message": "Erro ao processar os resultados históricos."}), 500

def get_response_for_keyword(keyword):
    """
    Process and respond to user keywords with comprehensive error handling and logging.
    
    Args:
        keyword (str): The user's input keyword
    
    Returns:
        dict: A response dictionary with either the requested information or an error message
    """
    # Enhanced logging with structured information
    logger.info(f"Keyword Processing Started: Input = '{keyword}'")
    
    try:
        # Normalize the keyword
        normalized_keyword = keyword.lower().strip()
        logger.debug(f"Normalized Keyword: '{normalized_keyword}'")
        
        # Check for keyword match with enhanced matching
        matched_keyword = difflib.get_close_matches(
            normalized_keyword, 
            list(keywords.keys()), 
            n=1, 
            cutoff=0.6
        )
        
        if not matched_keyword:
            logger.warning(f"No keyword match found for: '{normalized_keyword}'")
            return {
                "message": f"Desculpe, não entendi '{keyword}'. Pode reformular sua pergunta? "
            }
        
        # Use the best match
        matched_keyword = matched_keyword[0]
        mapped_value = keywords[matched_keyword]
        
        logger.info(f"Keyword Match: '{matched_keyword}' -> '{mapped_value}'")
        
        # Centralized response handling
        response_handlers = {
            "resultados": get_last_matches_text,
            "próximos jogos": get_next_matches_text,
            "classificação": get_classification_text
        }
        
        # Handle standard keyword responses
        if mapped_value in response_handlers:
            try:
                result = response_handlers[mapped_value]()
                logger.debug(f"Response for {mapped_value}: {result[:100]}...")
                
                # Standardize response format
                return {
                    "matches" if mapped_value in ["resultados", "próximos jogos"] else 
                    "classification": result
                }
            except Exception as e:
                logger.error(f"Error processing {mapped_value}: {e}")
                return {
                    "message": f"Erro ao buscar {mapped_value}. Por favor, tente novamente. "
                }
        
        # Handle special messages
        if isinstance(mapped_value, str) and "Desculpe" in mapped_value:
            logger.info("Special message returned")
            return {"message": mapped_value}
        
        # Handle API routes
        if mapped_value.startswith("/api/"):
            logger.info(f"Processing API route: {mapped_value}")
            
            api_routes = {
                "/api/biography/antonio_gago": api_antonio_gago_biography
            }
            
            try:
                result = api_routes.get(mapped_value, lambda: {"error": "Rota não encontrada"})()
                logger.debug(f"API Response: {result}")
                return result
            except FileNotFoundError:
                logger.error("Biography file not found")
                return {"error": "Biografia não encontrada"}
            except Exception as e:
                logger.error(f"Unexpected error in API route: {e}")
                return {"error": "Erro inesperado ao processar solicitação"}
        
        # Fallback for unhandled cases
        logger.warning(f"Unhandled keyword mapping: {mapped_value}")
        return {
            "message": "Desculpe, não consegui processar sua solicitação. "
        }
    
    except Exception as e:
        # Comprehensive error logging
        logger.error(f"Unexpected error in keyword processing: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "message": "Ocorreu um erro inesperado. Por favor, tente novamente. "
        }
    finally:
        # Always log the end of processing
        logger.info("Keyword Processing Completed")

@app.route('/api/query', methods=['GET'])
def api_query():
    # EXTREME LOGGING FOR API QUERY
    print("="*100)
    print("EXTREME API QUERY LOGGING")
    print(f"Full Request Method: {request.method}")
    print(f"Full Request Headers: {dict(request.headers)}")
    print(f"Full Request Arguments: {dict(request.args)}")
    sys.stdout.flush()  # Force immediate output
    
    logger.critical("="*100)
    logger.critical("EXTREME API QUERY LOGGING")
    logger.critical(f"Full Request Method: {request.method}")
    logger.critical(f"Full Request Headers: {dict(request.headers)}")
    logger.critical(f"Full Request Arguments: {dict(request.args)}")
    
    # Extract query parameter with extreme verbosity
    keyword = request.args.get('q', '')
    print(f"EXTRACTED KEYWORD: '{keyword}'")
    sys.stdout.flush()
    logger.critical(f"EXTRACTED KEYWORD: '{keyword}'")
    
    try:
        # Process keyword with maximum logging
        print("INITIATING KEYWORD PROCESSING")
        sys.stdout.flush()
        logger.critical("INITIATING KEYWORD PROCESSING")
        
        response = get_response_for_keyword(keyword)
        
        print(f"RESPONSE GENERATED: {response}")
        sys.stdout.flush()
        logger.critical(f"RESPONSE GENERATED: {response}")
        
        return jsonify(response)
    
    except Exception as e:
        print("CATASTROPHIC API QUERY FAILURE")
        print(f"EXCEPTION: {e}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        sys.stdout.flush()
        
        logger.critical("CATASTROPHIC API QUERY FAILURE")
        logger.critical(f"EXCEPTION: {e}")
        logger.critical(f"TRACEBACK: {traceback.format_exc()}")
        
        return jsonify({"message": "Erro interno do servidor"}), 500

def read_historical_results_from_db(table_name):
    """
    Read historical results from a JSON file instead of SQLite database.
    
    Args:
        table_name (str): Ignored for JSON file, kept for compatibility
    
    Returns:
        list: A list of historical results dictionaries
    """
    try:
        # Path to the JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'dados_jogos.json')
        
        # Read the JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            historical_results = json.load(f)

        # Log the number of results loaded
        print(f" LOADED {len(historical_results)} HISTORICAL RESULTS FROM JSON")
        sys.stdout.flush()
        logger.critical(f" LOADED {len(historical_results)} HISTORICAL RESULTS FROM JSON")
        
        return historical_results
    
    except FileNotFoundError:
        print(f" ERROR: JSON file not found at {json_path}")
        sys.stdout.flush()
        logger.critical(f" ERROR: JSON file not found at {json_path}")
        return []
    
    except json.JSONDecodeError as e:
        print(f" ERROR: Invalid JSON format - {e}")
        sys.stdout.flush()
        logger.critical(f" ERROR: Invalid JSON format - {e}")
        return []
    
    except Exception as e:
        print(f" UNEXPECTED ERROR reading JSON: {e}")
        sys.stdout.flush()
        logger.critical(f" UNEXPECTED ERROR reading JSON: {e}")
        return []

def find_available_port(start_port=5000, max_attempts=10):
    """
    Find an available port starting from the given port.
    
    Args:
        start_port (int): Port to start searching from
        max_attempts (int): Maximum number of ports to try
    
    Returns:
        int: An available port number
    """
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def open_browser(port):
    """
    Open the default web browser to the application's URL.
    
    Args:
        port (int): Port number the server is running on
    """
    webbrowser.open(f'http://localhost:{port}')

def run_server(port=5000):
    """
    Run the Flask application and open browser.
    
    Args:
        port (int): Port number to run the server on
    """
    try:
        # Find an available port if the default is in use
        actual_port = find_available_port(port)
        
        # Open browser in a separate thread
        threading.Thread(target=open_browser, args=(actual_port,)).start()
        
        # Print the port being used
        print(f"Starting server on port {actual_port}")
        
        # Run the Flask app
        app.run(host='0.0.0.0', port=actual_port, debug=False)
    
    except Exception as e:
        print(f"Server startup failed: {e}")
        raise

def main():
    """
    Main entry point for the application.
    """
    try:
        app.config['DEBUG'] = False
        run_server()
    except Exception as e:
        print(f"Fatal error starting application: {e}")

def format_classification_table(df):
    """
    Format the league classification DataFrame with custom styling.
    
    Args:
        df (pd.DataFrame): Input DataFrame with league classification
    
    Returns:
        str: Formatted table string
    """
    # Rename columns to more readable Portuguese
    column_mapping = {
        'P': 'Pos', 
        'J': 'Jogos', 
        'V': 'Vitórias', 
        'E': 'Empates', 
        'D': 'Derrotas', 
        'GM': 'Golos Marcados', 
        'GS': 'Golos Sofridos', 
        'DG': 'Diferença Golos'
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Format the table with fancy styling
    return tabulate(
        df, 
        headers='keys', 
        tablefmt='pretty',  # More elegant table format
        numalign='right',   # Align numeric columns to the right
        stralign='left',    # Align string columns to the left
        showindex=False     # Hide index column
    )

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

# ============================================================================
# FARENSE CHATBOT ENDPOINT
# ============================================================================

@app.route('/api/farense-chat', methods=['POST'])
def farense_chat_api():
    """
    Endpoint do Chatbot Farense com fotos

    Request JSON:
    {
        "query": "quem foi paco fortes",
        "k": 15  // opcional
    }

    Response JSON:
    {
        "success": true,
        "response": "texto da resposta...",
        "photos": ["/static/fotografias/jogadores/paco_fortes.webp"],
        "metadata": {...}
    }
    """
    try:
        if not FARENSE_CHATBOT_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Chatbot Farense não disponível'
            }), 503

        data = request.get_json()
        query = data.get('query', '').strip()
        k = data.get('k', 15)

        if not query:
            return jsonify({
                'success': False,
                'error': 'Query vazia'
            }), 400

        # Processar query
        result = farense_chatbot_query(query, k=k)

        # Ajustar caminhos de fotos para static
        if result.get('success') and result.get('photos'):
            result['photos'] = [
                photo.replace('/fotografias/', '/static/fotografias/')
                for photo in result['photos']
            ]

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro no chatbot Farense: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    main()
