import sqlite3
import logging
import json
import os
import re
import tiktoken
import openai
from dotenv import load_dotenv
from utils import (
    remove_accents, 
    find_relevant_context, 
    read_historical_results_from_db,
    get_antonio_gago_biography
)
from last_matches import get_last_matches_text
from next_matches import get_next_matches_text
from next_away import main as gerar_relatorio
from classificação import tabela_classificativa

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
DB_PATH = 'dados_jogos.db'
HISTORICAL_RESULTS_TABLE = 'historical_results'
HISTORICAL_50_YEARS_TABLE = 'historical_50_years'
BIOGRAPHIES_TABLE = 'biographies'

def get_response_from_agent(prompt, context, role, max_length=2048):
    """
    Generate AI response using OpenAI API.
    
    Args:
        prompt (str): User's query
        context (str): Relevant historical context
        role (str): System role description
        max_length (int): Maximum token length
    
    Returns:
        str: AI-generated response
    """
    # Load OpenAI API key from environment
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    try:
        # Prepare messages for OpenAI with valid roles
        messages = [
            {"role": "system", "content": role},
            {"role": "user", "content": f"Contexto histórico: {context}\n\nPergunta: {prompt}"}
        ]
        
        # Generate response using latest OpenAI library
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_length
        )
        
        # Extract content from the latest library response
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "Desculpe, não consegui processar sua pergunta no momento."

def generate_rich_response(biography, question):
    """
    Generate a comprehensive, narrative biographical text in European Portuguese.
    
    Args:
        biography (dict): Structured biography details
        question (str): User's original query
    
    Returns:
        str: Detailed, narrative biographical text in European Portuguese
    """
    # Log input details for debugging
    logger.info(f"Generating rich response for question: {question}")
    logger.debug(f"Biography input: {biography}")
    
    try:
        # Validate biography input
        if not isinstance(biography, dict):
            logger.warning("Invalid biography input: not a dictionary")
            return "Não foi possível recuperar informações detalhadas."
        
        # Extract key biography components
        nome = biography.get('nome_completo', 'Desconhecido')
        nascimento = biography.get('nascimento', 'Data não disponível')
        falecimento = biography.get('falecimento', 'Data não disponível')
        socio_numero = biography.get('socio_numero', 'Número não disponível')
        
        # Prepare narrative context
        context = {
            'fundacao': biography.get('percurso', {}).get('fundacao_e_primeiros_anos', {}),
            'jogador': biography.get('percurso', {}).get('contribuicoes_como_jogador', {}),
            'conquistas': biography.get('percurso', {}).get('conquistas', []),
            'contribuicoes': biography.get('contribuicoes', [])
        }
        
        # Construct detailed narrative in European Portuguese
        narrative = f"""António Guerreiro da Silva Gago: Uma Vida Dedicada ao Sporting Clube Farense

No dealbar do século XX, a 27 de Setembro de 1897, nascia em Faro um homem que se tornaria um pilar fundamental do desporto algarvio: António Guerreiro da Silva Gago. A sua história é mais do que uma simples biografia; é um testemunho da resiliência e paixão que moldaram o Sporting Clube Farense nos seus primeiros anos de existência.

Os anos iniciais do clube foram marcados por desafios significativos. A Primeira Grande Guerra e a devastadora Pneumónica criaram um contexto de profunda instabilidade. Era um período de crise financeira, escassez de atletas e dificuldades que teriam desanimado muitos. Porém, António Gago não se deixou abater. Foi um dos sócios fundadores, integrando um grupo de pouco mais de uma dúzia de jovens entusiastas que acreditavam no potencial do futebol como força unificadora.

Lado a lado com Francisco Tavares Bello, Gago desempenhou um papel crucial na consolidação do clube. A sua contribuição ultrapassava os limites do relvado: foi fundamental na aquisição de uma moradia na Rua Argel, que serviria para equipar os jogadores, simbolizando o compromisso com a infraestrutura e o futuro do Sporting Clube Farense.

Enquanto jogador, António Gago rapidamente se destacou. Extremo direito conhecido pela sua velocidade impressionante, tornou-se capitão da equipa em momentos fulcrais. A sua liderança era reconhecida não apenas pelas suas habilidades técnicas, mas pela capacidade de inspirar e unir os seus companheiros em momentos desafiantes.

O ponto alto da sua carreira chegou na época de 1922/23, quando liderou o clube à conquista do primeiro Campeonato do Algarve. A vitória por 3-2 contra o Sporting Clube Olhanense não foi apenas um triunfo desportivo, mas um marco histórico que estabeleceu o Farense como uma força a ter em conta no futebol regional.

Os seus momentos mais memoráveis incluem confrontos épicos com o Sporting Louletano, partidas contra a União Portimonense, e jogos históricos contra o Vitória de Setúbal e o Sporting Clube Olhanense. Cada encontro era mais do que uma competição; era uma afirmação da identidade e determinação do clube.

Contudo, a contribuição de António Gago transcendia os limites do relvado. Após pendurar as chuteiras, continuou a servir o clube que ajudou a fundar. Foi dirigente do Sporting Clube Farense, membro dos corpos sociais da Associação de Futebol do Algarve e integrou o Conselho Técnico do clube. A sua versatilidade estendia-se para além do futebol: praticante de atletismo e com envolvimento no pugilismo, Gago era um atleta completo.

Reconhecido como o Sócio n.º 1 do Sporting Clube Farense desde o início dos anos setenta, o seu legado é uma história de comprometimento, paixão e transformação. Não era apenas um jogador ou dirigente, mas um verdadeiro arquiteto dos sonhos de uma comunidade inteira.

António Guerreiro da Silva Gago faleceu em Lisboa a 11 de Dezembro de 1993, deixando um legado que ultrapassa gerações. A sua vida é um testemunho de como a dedicação, a visão e o amor por uma instituição podem moldar não apenas um clube, mas toda uma cultura desportiva.

Para o Sporting Clube Farense, António Gago não foi apenas um nome nos registos históricos. Foi a personificação da resiliência, da liderança e da paixão que definem o espírito do futebol algarvio."""
        
        # Log response details
        logger.debug(f"Generated narrative response (length: {len(narrative)} characters)")
        logger.debug(f"Response preview: {narrative[:200]}...")
        
        return narrative
    
    except Exception as e:
        logger.error(f"Error generating rich response: {e}", exc_info=True)
        return "Desculpe, não foi possível gerar uma resposta detalhada."

def mirobaldo_chatbot(question, historical_context):
    """
    Main chatbot function to process user queries with comprehensive logging.
    
    Args:
        question (str): User's query
        historical_context (str): Historical text context
    
    Returns:
        str: Chatbot response
    """
    # Validate inputs
    if not question:
        logger.warning("Empty question received")
        return "Por favor, faça uma pergunta sobre o Sporting Clube Farense."
    
    try:
        # Normalize question
        normalized_question = remove_accents(question.lower())
        logger.info(f"Processing query: '{question}'")
        logger.debug(f"Normalized query: '{normalized_question}'")
        
        # Retrieve relevant context
        context = find_relevant_context(question, historical_context)
        logger.debug(f"Retrieved context length: {len(context)} characters")
        
        # Special handling for specific queries
        if 'gago' in normalized_question:
            logger.info("Detected query about António Gago")
            biography = get_antonio_gago_biography()
            response = generate_rich_response(biography, question)
            logger.debug(f"António Gago biography response generated: {response[:100]}...")
            return response
        
        # Last Matches Keywords
        last_matches_keywords = [
            'últimos resultados', 'resultados recentes', 'jogos anteriores', 
            'resultados', 'últimos jogos', 'resultados passados', 
            'jogos já realizados', 'partidas anteriores'
        ]
        if any(keyword in normalized_question for keyword in last_matches_keywords):
            logger.info("Detected query about last matches")
            try:
                last_matches_text = get_last_matches_text()
                logger.debug(f"Last matches response: {last_matches_text[:100]}...")
                return last_matches_text
            except Exception as e:
                logger.error(f"Error fetching last matches: {e}")
                return "Não foi possível recuperar os últimos resultados. 🚫⚽"
        
        # Next Matches Keywords
        next_matches_keywords = [
            'próximos jogos', 'próximos resultados', 'jogos seguintes', 
            'próximas partidas', 'jogos futuros', 'próximos encontros', 
            'agenda de jogos', 'próximas competições',
            'proximos jogos', 'proximos resultados', 'jogos seguintes', 
            'proximas partidas', 'jogos futuros', 'proximos encontros', 
            'agenda de jogos', 'proximas competicoes'
        ]
        logger.info(f"Checking next matches keywords. Normalized query: {normalized_question}")
        logger.info(f"Keyword match: {any(keyword in normalized_question for keyword in next_matches_keywords)}")
        
        if any(keyword in normalized_question for keyword in next_matches_keywords):
            logger.info("FORCED: Detected query about next matches")
            try:
                next_matches_text = get_next_matches_text()
                logger.debug(f"FORCED: Next matches response: {next_matches_text[:100]}...")
                return next_matches_text
            except Exception as e:
                logger.error(f"FORCED: Error fetching next matches: {e}")
                return "Não foi possível recuperar os próximos jogos. 🚫⚽"
        
        # Next Away Keywords
        next_away_keywords = ['deslocacao', 'próximo jogo fora', 'próxima deslocação', 'próxima partida fora', 'próximo jogo visitante', 'próxima jornada fora']

        logger.info(f"Checking next away keywords. Normalized query: {normalized_question}")
        logger.info(f"Keyword match: {any(keyword in normalized_question for keyword in next_away_keywords)}")
        
        if any(keyword in normalized_question for keyword in next_away_keywords):
            logger.info("FORCED: Detected query about next away matches")
            try:
                next_away_text = gerar_relatorio()
                logger.debug(f"FORCED: Next away response: {next_away_text[:100]}...")
                return next_away_text
            except Exception as e:
                logger.error(f"FORCED: Error fetching next away matches: {e}")
                return "Não foi possível recuperar os próximos jogos de campo. 🚫⚽"
        
        # Classification Keywords
        classification_keywords = [
            'classificacao', 'tabela', 'posicao na liga', 
            'ranking', 'pontuacao', 'posicionamento', 
            'colocacao', 'situacao na competicao'
        ]
        logger.info(f"Checking classification keywords. Normalized query: {normalized_question}")
        logger.info(f"Keyword match: {any(keyword in normalized_question for keyword in classification_keywords)}")
        
        if any(keyword in normalized_question for keyword in classification_keywords):
            logger.info("FORCED: Detected query about league classification")
            try:
                # Fetch classification DataFrame
                classification_df = tabela_classificativa(url_competicao="https://www.zerozero.pt/competicao/liga-portuguesa")
                
                # Log DataFrame details
                logger.debug(f"FORCED: Classification DataFrame shape: {classification_df.shape}")
                
                return classification_df  # Return DataFrame directly
            
            except Exception as e:
                logger.error(f"FORCED: Error fetching classification: {e}")
        
        # Club History Keywords
        history_keywords = [
            'história do clube', 'historia do clube', 'origem do clube', 
            'fundação', 'fundacao', 'historia do farense', 'história do farense',
            'origem do farense', 'primórdios', 'primordios', 'historia do sporting clube farense',
            'história do sporting clube farense'
        ]
        logger.info(f"Checking club history keywords. Normalized query: {normalized_question}")
        logger.info(f"Keyword match: {any(keyword in normalized_question for keyword in history_keywords)}")
        
        if any(keyword in normalized_question for keyword in history_keywords):
            logger.info("FORCED: Detected query about club history")
            try:
                # Read history context from JSON file
                import json
                
                def load_history_context():
                    try:
                        with open('/Users/f.nuno/CascadeProjects/mirobaldo/50_anos.json', 'r', encoding='utf-8') as f:
                            history_data = json.load(f)
                        
                        # Combine all chapters into a single text
                        full_context = "\n\n".join([
                            str(chapter) for chapter in history_data.values()
                        ])
                        
                        return full_context
                    except Exception as e:
                        logger.error(f"Error loading history context: {e}")
                        return ""
                
                # Summarize and extract key historical context
                def extract_relevant_context(full_context, max_tokens=12000):
                    # Use tiktoken to accurately count tokens
                    import tiktoken
                    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-16k")
                    
                    # Log initial context details
                    initial_tokens = len(tokenizer.encode(full_context))
                    logger.info(f"Initial context size: {initial_tokens} tokens")
                    
                    # If context is already small, return as-is
                    if initial_tokens <= max_tokens:
                        logger.info("Context already within token limit")
                        return full_context
                    
                    # Focus on most critical keywords
                    critical_keywords = [
                        'sporting', 'farense', 'faro', 'futebol', 
                        'fundação', 'história', 'clube', 'raminhos bispo'
                    ]
                    
                    # Split context into potential chapters or sections
                    sections = full_context.split('\n\n')
                    
                    # Filter and prioritize sections
                    relevant_sections = [
                        section for section in sections 
                        if any(keyword.lower() in section.lower() for keyword in critical_keywords)
                    ]
                    
                    # Accumulate sections while staying under token limit
                    condensed_context = []
                    current_token_count = 0
                    
                    for section in relevant_sections:
                        section_tokens = len(tokenizer.encode(section))
                        
                        # If adding this section would exceed max tokens, break
                        if current_token_count + section_tokens > max_tokens:
                            logger.info(f"Reached token limit. Stopping at {current_token_count} tokens")
                            break
                        
                        condensed_context.append(section)
                        current_token_count += section_tokens
                    
                    # Convert to string and log final token count
                    final_context = '\n\n'.join(condensed_context)
                    final_tokens = len(tokenizer.encode(final_context))
                    logger.info(f"Final context size: {final_tokens} tokens")
                    
                    return final_context
                
                # Load and prepare history context
                history_context = load_history_context()
                if not history_context:
                    return "Não foi possível carregar o contexto histórico. 📚"
                
                # Extract relevant context
                condensed_context = extract_relevant_context(history_context)
                
                # Use a more concise prompt
                history_prompt = f"""
                Gere uma narrativa histórica sobre o Sporting Clube Farense com base no seguinte contexto:

                Contexto Histórico:
                {condensed_context}

                Directrizes:
                - Concentre-se na fundação e momentos cruciais do clube
                - Mantenha um tom narrativo cativante
                - Limite a resposta aos aspectos mais significativos
                - Priorize informações sobre a origem e desenvolvimento do clube
                """
                
                # Generate the history response with streaming
                stream_response = openai.chat.completions.create(
                    model="gpt-3.5-turbo-16k",
                    messages=[
                        {"role": "system", "content": "O senhor é um historiador especializado na história do Sporting Clube Farense."},
                        {"role": "user", "content": history_prompt}
                    ],
                    max_tokens=1024,  # Reduced token request
                    stream=True  # Enable streaming
                )
                
                # Collect streamed response
                history_response = ""
                for chunk in stream_response:
                    if chunk.choices[0].delta.content is not None:
                        history_response += chunk.choices[0].delta.content
                
                logger.debug(f"FORCED: Club history response generated (length: {len(history_response)} characters)")
                return history_response
            
            except Exception as e:
                # Log the full error details
                logger.error(f"FORCED: Error generating club history", exc_info=True)
                
                # If OpenAI API fails, provide a fallback response
                return (
                    "Peço desculpas, mas não foi possível gerar a história completa do clube neste momento. "
                    "O Sporting Clube Farense tem uma rica história no futebol algarvio, "
                    "fundado em Faro, com décadas de tradição e paixão pelo esporte. "
                    "Para informações mais detalhadas, recomendo consultar fontes históricas locais. 📚🏆"
                )
        
        # Fallback to AI-generated response
        system_role = (
            "Você é Mirobaldo, um assistente virtual especializado na história "
            "do Sporting Clube Farense. Responda de forma amigável e informativa "
            "com base no contexto histórico fornecido. Seja conciso e direto."
        )
        
        logger.info("Generating AI response for general query")
        ai_response = get_response_from_agent(
            prompt=question, 
            context=context, 
            role=system_role
        )
        
        # Log response details
        logger.debug(f"AI Response generated (length: {len(ai_response)} characters)")
        logger.debug(f"AI Response preview: {ai_response[:200]}...")
        
        return ai_response
    
    except Exception as e:
        logger.error(f"Error processing chatbot query: {e}", exc_info=True)
        return "Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente."

def initialize_database():
    """
    Inicializa o banco de dados SQLite com as tabelas necessárias e dados iniciais.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {HISTORICAL_RESULTS_TABLE} (
                data TEXT,
                hora TEXT,
                local TEXT,
                equipa TEXT,
                resultado TEXT,
                VED TEXT,
                jornada TEXT
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {HISTORICAL_50_YEARS_TABLE} (
                text TEXT
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {BIOGRAPHIES_TABLE} (
                nome TEXT PRIMARY KEY,
                biografia TEXT
            )
        ''')

        cursor.execute(f"SELECT COUNT(*) FROM {HISTORICAL_RESULTS_TABLE}")
        results_count = cursor.fetchone()[0]

        if results_count == 0:
            initial_results = load_initial_results()
            if initial_results:
                cursor.executemany(f'''
                    INSERT INTO {HISTORICAL_RESULTS_TABLE}
                    (data, hora, local, equipa, resultado, VED, jornada)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', initial_results)
                logger.info(f"Inicializados {len(initial_results)} resultados históricos de partidas")
            else:
                logger.info("Nenhum resultado inicial para carregar.")

        cursor.execute(f"SELECT COUNT(*) FROM {HISTORICAL_50_YEARS_TABLE}")
        anos_count = cursor.fetchone()[0]

        if anos_count == 0:
            try:
                with open('50_anos.txt', 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                initial_50_years = [(line.strip(),) for line in lines if line.strip()]
                cursor.executemany(f'''
                    INSERT INTO {HISTORICAL_50_YEARS_TABLE} (text) VALUES (?)
                ''', initial_50_years)
            except FileNotFoundError:
                initial_50_years = [
                    ("Fundação do SC Farense em 1910",),
                    ("Primeiro jogo oficial em 1920",),
                ]
                cursor.executemany(f'''
                    INSERT INTO {HISTORICAL_50_YEARS_TABLE} (text) VALUES (?)
                ''', initial_50_years)

        cursor.execute(f"SELECT COUNT(*) FROM {BIOGRAPHIES_TABLE} WHERE nome = 'António Gago'")
        gago_count = cursor.fetchone()[0]

        if gago_count == 0:
            antonio_gago_bio = get_antonio_gago_biography()
            cursor.execute(f'''
                INSERT INTO {BIOGRAPHIES_TABLE} (nome, biografia)
                VALUES (?, ?)
            ''', ('António Gago', antonio_gago_bio))

        conn.commit()
        logger.info("Banco de dados inicializado com sucesso")

    except sqlite3.Error as e:
        logger.error(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        conn.close()

def load_initial_results(file_path='dados_jogos.json'):
    """
    Carrega resultados históricos iniciais de um arquivo JSON.

    Args:
        file_path (str): Caminho para o arquivo JSON contendo resultados de partidas.

    Returns:
        list: Lista de tuplas contendo detalhes das partidas.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            match_data = json.load(f)

        initial_results = [
            (
                match.get('data', ''),
                match.get('hora', ''),
                match.get('local', ''),
                match.get('equipa', ''),
                match.get('resultado', ''),
                match.get('VED', ''),
                match.get('jornada', '')
            )
            for match in match_data.get('matches', [])
        ]

        return initial_results

    except FileNotFoundError:
        logger.error(f"Arquivo de dados de partidas não encontrado: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar JSON no arquivo {file_path}")
        return []

def main():
    """
    Main function to initialize database and start chatbot.
    """
    initialize_database()
    
    # Refresh historical results if needed
    global historical_results, historical_50_anos
    historical_results = read_historical_results_from_db(HISTORICAL_RESULTS_TABLE)
    historical_50_anos = read_historical_results_from_db(HISTORICAL_50_YEARS_TABLE)
    
    # Load historical context
    with open('50_anos.json', 'r', encoding='utf-8') as f:
        historical_context = f.read()
    
    # Example queries
    queries = [
        "Quem foi António Gago?",
        "Conte-me sobre a história do Farense",
        "Como surgiu o clube?"
    ]
    
    for query in queries:
        response = mirobaldo_chatbot(query, historical_context)
        print(f"Query: {query}\nResponse: {response}\n{'='*50}\n")

if __name__ == "__main__":
    main()