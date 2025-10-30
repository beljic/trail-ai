"""
FastAPI server for Trail AI.

Provides REST API endpoints for:
- Chat with AI assistant
- Race search and recommendations  
- Vector database management
- Health checks and statistics
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import AI modules
from ai.chat import get_chat_manager, ChatSession
from ai.rag import get_rag_client
from ai.embeddings import get_embeddings_client, sync_embeddings_from_postgres
from ai.llm import get_client as get_llm_client

# Create FastAPI app
app = FastAPI(
    title="Trail AI API",
    description="AI-powered trail running race discovery and recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response

class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Optional session ID")

class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    query_type: str
    context_races: int
    timestamp: str
    success: bool

class RaceQuery(BaseModel):
    """Race query model."""
    query: str = Field(..., description="Natural language query")
    n_results: int = Field(10, description="Number of results to return")
    task_type: str = Field("general", description="Query type: general, recommendation, analysis")

class RaceSearchCriteria(BaseModel):
    """Race search criteria model."""
    country: Optional[str] = None
    race_type: Optional[str] = None
    distance_min: Optional[float] = None
    distance_max: Optional[float] = None
    terrain: Optional[str] = None
    location: Optional[str] = None
    query: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    services: Dict[str, bool]
    database_stats: Dict[str, Any]

# Dependencies

def get_chat_manager_dep():
    """Dependency to get chat manager."""
    return get_chat_manager()

def get_rag_client_dep():
    """Dependency to get RAG client."""
    return get_rag_client()

def get_embeddings_client_dep():
    """Dependency to get embeddings client."""
    return get_embeddings_client()

# API Routes

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Trail AI API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Health check endpoint."""
    try:
        # Check services
        services = {}
        
        # Check Ollama
        llm_client = get_llm_client()
        services["ollama"] = llm_client.is_available()
        
        # Check ChromaDB
        try:
            stats = embeddings_client.get_stats()
            services["chromadb"] = True
        except Exception:
            services["chromadb"] = False
            stats = {}
        
        # Overall status
        all_healthy = all(services.values())
        status = "healthy" if all_healthy else "degraded"
        
        return HealthResponse(
            status=status,
            timestamp=datetime.now().isoformat(),
            services=services,
            database_stats=stats
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    chat_manager = Depends(get_chat_manager_dep)
):
    """Chat with AI assistant."""
    try:
        # Get or create session
        if message.session_id:
            session = chat_manager.get_session(message.session_id)
            if not session:
                session = chat_manager.create_session(message.session_id)
        else:
            session = chat_manager.create_session()
        
        # Process message
        result = session.process_message(message.message)
        
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            query_type=result.get("query_type", "unknown"),
            context_races=result.get("context_races", 0),
            timestamp=result["timestamp"],
            success=result["success"]
        )
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=Dict[str, Any])
async def query_races(
    query: RaceQuery,
    rag_client = Depends(get_rag_client_dep)
):
    """Query races using RAG."""
    try:
        result = rag_client.query(
            user_query=query.query,
            n_results=query.n_results,
            task_type=query.task_type
        )
        return result
        
    except Exception as e:
        logger.error(f"Race query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations", response_model=Dict[str, Any])
async def get_recommendations(
    preferences: str,
    n_results: int = 15,
    rag_client = Depends(get_rag_client_dep)
):
    """Get personalized race recommendations."""
    try:
        result = rag_client.get_recommendations(preferences, n_results)
        return result
        
    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=Dict[str, Any])
async def search_races(
    criteria: RaceSearchCriteria,
    rag_client = Depends(get_rag_client_dep)
):
    """Search races by criteria."""
    try:
        result = rag_client.search_races_by_criteria(
            criteria.dict(exclude_none=True),
            user_query=criteria.query
        )
        return result
        
    except Exception as e:
        logger.error(f"Race search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_races(
    analysis_query: str,
    n_results: int = 20,
    rag_client = Depends(get_rag_client_dep)
):
    """Analyze race data."""
    try:
        result = rag_client.analyze_races(analysis_query, n_results)
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session management endpoints

@app.get("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions(
    chat_manager = Depends(get_chat_manager_dep)
):
    """List all chat sessions."""
    return chat_manager.get_all_sessions()

@app.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    chat_manager = Depends(get_chat_manager_dep)
):
    """Get specific session details."""
    session = chat_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "stats": session.get_session_stats(),
        "history": session.get_conversation_history()
    }

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    chat_manager = Depends(get_chat_manager_dep)
):
    """Delete chat session."""
    success = chat_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": f"Session {session_id} deleted"}

# Database management endpoints

@app.get("/database/stats", response_model=Dict[str, Any])
async def get_database_stats(
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Get vector database statistics."""
    try:
        return embeddings_client.get_stats()
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/database/sync")
async def sync_database(
    background_tasks: BackgroundTasks,
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Sync embeddings from PostgreSQL database."""
    def sync_task():
        try:
            count = sync_embeddings_from_postgres()
            logger.info(f"Synced {count} races to vector database")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
    
    background_tasks.add_task(sync_task)
    return {"message": "Database sync started in background"}

@app.post("/database/reset")
async def reset_database(
    confirm: bool = False,
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Reset vector database (delete all data)."""
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to reset database"
        )
    
    try:
        success = embeddings_client.reset_database()
        if success:
            return {"message": "Database reset successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset database")
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search specific races

@app.get("/races/{race_id}", response_model=Dict[str, Any])
async def get_race(
    race_id: str,
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Get specific race by ID."""
    race = embeddings_client.get_race_by_id(race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    
    return race

@app.get("/races", response_model=List[Dict[str, Any]])
async def search_races_simple(
    q: str,
    limit: int = 10,
    embeddings_client = Depends(get_embeddings_client_dep)
):
    """Simple race search."""
    try:
        races = embeddings_client.search_races(query=q, n_results=limit)
        return races
    except Exception as e:
        logger.error(f"Simple search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# Startup/shutdown events

@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("Trail AI API starting up...")
    
    # Check if Ollama is available
    llm_client = get_llm_client()
    if llm_client.is_available():
        models = llm_client.list_models()
        logger.info(f"Ollama available with models: {models}")
    else:
        logger.warning("Ollama not available - AI features may not work")
    
    # Initialize embeddings client
    try:
        embeddings_client = get_embeddings_client()
        stats = embeddings_client.get_stats()
        logger.info(f"Vector database ready with {stats['total_races']} races")
    except Exception as e:
        logger.error(f"Failed to initialize vector database: {e}")
    
    logger.info("Trail AI API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("Trail AI API shutting down...")

if __name__ == "__main__":
    import uvicorn
    
    # Configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting Trail AI API on {host}:{port}")
    uvicorn.run("api.main:app", host=host, port=port, reload=reload)