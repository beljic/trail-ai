"""
Lightweight AI system for Trail AI without heavy ML dependencies.

Uses TF-IDF and simple text matching instead of neural embeddings.
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import lightweight components
from .lightweight_embeddings import LightweightEmbeddings
from .llm import query_ollama, chat_with_ollama, get_client as get_llm_client

logger = logging.getLogger(__name__)


class LightweightRAG:
    """Lightweight RAG using TF-IDF instead of neural embeddings."""
    
    def __init__(self):
        self.embeddings = LightweightEmbeddings()
        
    def query(self, user_query: str, n_results: int = 10, task_type: str = "general") -> Dict[str, Any]:
        """Process query using lightweight approach."""
        try:
            # Search for relevant races
            races = self.embeddings.search_races(user_query, n_results)
            
            if not races:
                return {
                    "answer": "I couldn't find any races matching your query.",
                    "races_found": 0,
                    "query": user_query,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Format race data for LLM
            race_data = self._format_races(races)
            
            # Generate answer using Ollama
            try:
                prompt = self._build_prompt(user_query, race_data, task_type)
                answer = query_ollama(prompt)
            except Exception as e:
                logger.warning(f"Ollama not available, providing simple answer: {e}")
                answer = self._simple_answer(user_query, races)
            
            return {
                "answer": answer,
                "races_found": len(races),
                "retrieved_races": races[:5],
                "query": user_query,
                "task_type": task_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "error": str(e),
                "query": user_query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_races(self, races: List[Dict[str, Any]]) -> str:
        """Format races for display."""
        formatted = []
        for i, race in enumerate(races, 1):
            metadata = race.get("metadata", {})
            parts = [f"{i}. {metadata.get('name', 'Unknown race')}"]
            
            if metadata.get('date'):
                parts.append(f"Date: {metadata['date']}")
            if metadata.get('location'):
                parts.append(f"Location: {metadata['location']}")
            if metadata.get('distance_km'):
                parts.append(f"Distance: {metadata['distance_km']} km")
            if metadata.get('race_type'):
                parts.append(f"Type: {metadata['race_type']}")
                
            formatted.append(" | ".join(parts))
        
        return "\n".join(formatted)
    
    def _build_prompt(self, query: str, race_data: str, task_type: str) -> str:
        """Build prompt for LLM."""
        if task_type == "recommendation":
            return f"""You are a trail running expert. Based on this query and race data, provide personalized recommendations:

Query: "{query}"

Available races:
{race_data}

Provide specific recommendations with reasoning."""
        else:
            return f"""You are a trail running assistant. Answer this question using the race data:

Question: "{query}"

Race data:
{race_data}

Provide a helpful answer based on the available information."""
    
    def _simple_answer(self, query: str, races: List[Dict[str, Any]]) -> str:
        """Simple answer when Ollama is not available."""
        if not races:
            return "No races found matching your query."
        
        race_list = []
        for race in races[:3]:
            metadata = race.get("metadata", {})
            name = metadata.get("name", "Unknown")
            location = metadata.get("location", "Unknown location")
            race_list.append(f"• {name} in {location}")
        
        return f"Found {len(races)} races matching '{query}':\n\n" + "\n".join(race_list)
    
    def get_recommendations(self, preferences: str, n_results: int = 15) -> Dict[str, Any]:
        """Get recommendations."""
        return self.query(preferences, n_results, task_type="recommendation")
    
    def analyze_races(self, analysis_query: str, n_results: int = 20) -> Dict[str, Any]:
        """Analyze races."""
        return self.query(analysis_query, n_results, task_type="analysis")


class LightweightChatSession:
    """Lightweight chat session."""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.messages = []
        self.rag = LightweightRAG()
    
    def process_message(self, user_input: str) -> Dict[str, Any]:
        """Process user message."""
        try:
            self.messages.append({"role": "user", "content": user_input, "timestamp": datetime.now().isoformat()})
            
            # Simple query classification
            if any(word in user_input.lower() for word in ["hello", "hi", "hey"]):
                response = "Hello! I can help you find trail running races. What are you looking for?"
            elif any(word in user_input.lower() for word in ["recommend", "suggest", "find me"]):
                result = self.rag.get_recommendations(user_input)
                response = result["answer"]
            else:
                result = self.rag.query(user_input)
                response = result["answer"]
            
            self.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
            
            return {
                "response": response,
                "session_id": self.session_id,
                "query_type": "general",
                "context_races": 0,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            error_response = f"Error: {str(e)}"
            return {
                "response": error_response,
                "session_id": self.session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }


class LightweightChatManager:
    """Lightweight chat manager."""
    
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, session_id: Optional[str] = None) -> LightweightChatSession:
        """Create new session."""
        session = LightweightChatSession(session_id)
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[LightweightChatSession]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions."""
        return [{"session_id": sid, "message_count": len(session.messages)} 
                for sid, session in self.sessions.items()]


# Global instances
_rag_client = None
_chat_manager = None
_embeddings_client = None

def get_rag_client():
    """Get RAG client."""
    global _rag_client
    if _rag_client is None:
        _rag_client = LightweightRAG()
    return _rag_client

def get_chat_manager():
    """Get chat manager."""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = LightweightChatManager()
    return _chat_manager

def get_embeddings_client():
    """Get embeddings client."""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = LightweightEmbeddings()
    return _embeddings_client