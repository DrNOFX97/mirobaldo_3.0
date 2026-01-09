"""
FastAPI Backend com RAG Integration
Chatbot do Farense com retrieval augmented generation
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
from pathlib import Path
import json
import logging
from typing import List, Optional
import asyncio

# Import RAG e LLM
from .rag_system import RAGSystem, initialize_rag
from .llm_interface import LLMInterface, ResponseFormatter
from .models import TrainingConfig
from .services.system import get_hardware_info
from .services.validation import validate_dataset_file, clean_dataset_file
from .services.training import start_training_process, stop_training_process

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App setup
app = FastAPI(title="Farense Chatbot API", version="1.0.0")

# Global instances (lazy loading)
rag_system = None
llm_interface = None

class CleanRequest(BaseModel):
    filename: str

class ChatRequest(BaseModel):
    """Requisição de chat com RAG"""
    query: str
    retrieve_k: int = 5
    temperature: float = 0.7
    max_tokens: int = 500

class ChatResponse(BaseModel):
    """Resposta de chat estruturada"""
    response: str
    query: str
    sources: List[dict]
    timestamp: str

class RAGStatusResponse(BaseModel):
    """Status do sistema RAG"""
    rag_loaded: bool
    llm_loaded: bool
    total_documents: int
    last_error: Optional[str] = None

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Inicializa sistemas na startup"""
    global rag_system, llm_interface
    logger.info("Iniciando aplicação...")
    try:
        # Inicializar RAG (lazy loading, não bloqueia startup)
        logger.info("RAG será carregado na primeira requisição")
        # rag_system = initialize_rag()
    except Exception as e:
        logger.error(f"Erro na startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup na shutdown"""
    logger.info("Encerrando aplicação...")

async def get_rag_system() -> RAGSystem:
    """Helper para obter RAG system com lazy loading"""
    global rag_system
    if rag_system is None:
        logger.info("Carregando RAG system...")
        rag_system = initialize_rag()
    return rag_system

async def get_llm_interface() -> LLMInterface:
    """Helper para obter LLM interface"""
    global llm_interface
    if llm_interface is None:
        logger.info("Inicializando LLM interface...")
        llm_interface = LLMInterface()
    return llm_interface

# ==================== Endpoints RAG/Chat ====================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint principal do chatbot com RAG

    Args:
        request: ChatRequest com query

    Returns:
        ChatResponse com resposta, fontes e metadata
    """
    try:
        logger.info(f"Chat request: {request.query}")

        # Obter RAG system
        rag = await get_rag_system()

        # Retrieve documentos relevantes
        logger.info("Recuperando documentos relevantes...")
        retrieved_docs = rag.retrieve(request.query, k=request.retrieve_k)

        if not retrieved_docs:
            logger.warning("Nenhum documento relevante encontrado")
            return ChatResponse(
                response="Desculpe, não encontrei informação relevante para responder à sua pergunta.",
                query=request.query,
                sources=[],
                timestamp=__import__('datetime').datetime.now().isoformat()
            )

        # Obter LLM interface
        llm = await get_llm_interface()

        # Gerar resposta com RAG context
        logger.info("Gerando resposta com contexto RAG...")
        response = llm.generate_rag_response(
            query=request.query,
            retrieved_docs=retrieved_docs,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Formatar resposta
        formatted_response = ResponseFormatter.format_chat_response(
            response=response,
            retrieved_docs=retrieved_docs,
            query=request.query
        )

        return ChatResponse(
            response=formatted_response['response'],
            query=formatted_response['query'],
            sources=formatted_response['sources'],
            timestamp=formatted_response['timestamp']
        )

    except Exception as e:
        logger.error(f"Erro no chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/retrieve")
async def retrieve_documents(query: str, k: int = 5):
    """
    Endpoint apenas para retrieval (debug/testing)

    Args:
        query: Texto a buscar
        k: Número de documentos a retornar

    Returns:
        Lista de documentos recuperados
    """
    try:
        rag = await get_rag_system()
        docs = rag.retrieve(query, k=k)

        return {
            'query': query,
            'count': len(docs),
            'documents': [
                {
                    'text': doc['text'],
                    'source': doc['source'],
                    'relevance': doc['relevance']
                }
                for doc in docs
            ]
        }
    except Exception as e:
        logger.error(f"Erro no retrieve endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag-status", response_model=RAGStatusResponse)
async def rag_status() -> RAGStatusResponse:
    """Status do sistema RAG"""
    try:
        rag = await get_rag_system()
        llm = await get_llm_interface()

        return RAGStatusResponse(
            rag_loaded=rag.index is not None,
            llm_loaded=llm.loaded,
            total_documents=len(rag.documents) if rag.documents else 0
        )
    except Exception as e:
        logger.error(f"Erro ao obter RAG status: {e}")
        return RAGStatusResponse(
            rag_loaded=False,
            llm_loaded=False,
            total_documents=0,
            last_error=str(e)
        )

@app.post("/rag/rebuild")
async def rebuild_rag(background_tasks: BackgroundTasks):
    """
    Reconstrói o índice RAG (operação pesada em background)
    Útil para when novos documentos são adicionados
    """
    try:
        global rag_system
        logger.info("Iniciando reconstrução do RAG system...")

        def rebuild():
            global rag_system
            rag_system = initialize_rag(force_rebuild=True)
            logger.info("RAG system reconstruído com sucesso")

        background_tasks.add_task(rebuild)

        return {
            'status': 'rebuilding',
            'message': 'RAG system será reconstruído em background'
        }
    except Exception as e:
        logger.error(f"Erro ao disparar rebuild: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Endpoints Originais ====================

@app.get("/system-info")
async def get_system_info():
    """Informações do hardware"""
    return get_hardware_info()

@app.post("/start-training")
async def start_training(config: TrainingConfig):
    """Inicia treino de LLM"""
    thread = threading.Thread(target=start_training_process, args=(config,))
    thread.start()
    return {"status": "started", "config": config, "framework": config.framework}

@app.post("/validate-dataset")
async def validate_dataset(file: UploadFile = File(...)):
    """Valida arquivo de dataset"""
    return await validate_dataset_file(file)

@app.post("/clean-dataset")
async def clean_dataset(request: CleanRequest):
    """Limpa dataset"""
    return await clean_dataset_file(request.filename)

@app.get("/training-status")
async def get_training_status():
    """Status do treino"""
    metrics_path = Path(__file__).parent.parent / "LLM_training" / "checkpoints_qlora" / "training_metrics.json"
    if not metrics_path.exists():
        return {"status": "idle", "logs": [], "data": []}

    try:
        with open(metrics_path, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/stop-training")
async def stop_training():
    """Para o treino"""
    stop_training_process()
    return {"status": "stopped"}

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Farense Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /chat",
            "retrieve": "GET /chat/retrieve?query=...&k=5",
            "rag_status": "GET /rag-status",
            "system_info": "GET /system-info"
        }
    }
