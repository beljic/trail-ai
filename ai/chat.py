"""
Chat interface for Trail AI.

Provides conversational interface for querying trail race data
with context management and natural language understanding.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from .rag import get_rag_client
from .embeddings import get_embeddings_client

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the chat system can handle."""
    GENERAL_QUESTION = "general_question"
    RACE_SEARCH = "race_search"
    RECOMMENDATIONS = "recommendations"
    COMPARISON = "comparison"
    STATISTICS = "statistics"
    HELP = "help"
    GREETING = "greeting"


class ChatSession:
    """Manages a chat conversation session with context."""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.messages: List[Dict[str, Any]] = []
        self.context_races: List[Dict[str, Any]] = []
        self.rag_client = get_rag_client()
        self.embeddings_client = get_embeddings_client()
        
        logger.info(f"Created chat session: {self.session_id}")
    
    def _classify_query(self, user_input: str) -> QueryType:
        """
        Classify user input to determine query type.
        
        Args:
            user_input: User's message
            
        Returns:
            QueryType enum
        """
        user_lower = user_input.lower().strip()
        
        # Greetings - dodano srpsko
        if any(word in user_lower for word in ["hello", "hi", "hey", "greetings", "good morning", "good evening", "zdravo", "dobar dan", "dobro jutro", "dobro veče", "ćao", "cao"]):
            return QueryType.GREETING
        
        # Help requests
        if any(word in user_lower for word in ["help", "how to", "what can", "commands", "options"]):
            return QueryType.HELP
        
        # Recommendations
        if any(phrase in user_lower for phrase in [
            "recommend", "suggest", "best race", "good race", "should i run", 
            "looking for", "want to run", "find me", "which race"
        ]):
            return QueryType.RECOMMENDATIONS
        
        # Comparisons
        if any(word in user_lower for word in ["compare", "difference", "versus", "vs", "better"]):
            return QueryType.COMPARISON
        
        # Statistics/Analysis
        if any(phrase in user_lower for phrase in [
            "how many", "statistics", "stats", "analysis", "trends", 
            "average", "most popular", "distribution", "overview"
        ]):
            return QueryType.STATISTICS
        
        # Race search - dodano srpske ključne reči
        if any(phrase in user_lower for phrase in [
            "races in", "events in", "find races", "search", "when", "where", 
            "distance", "km", "marathon", "trail", "ultra",
            # Srpski
            "kad je", "kada je", "kad se", "kada se", "gde je", "gde se", 
            "povlen", "trka", "trčanje", "maraton", "polumaraton", "ultra",
            "datum", "lokacija", "mesto", "grad", "srbija", "serbia"
        ]):
            return QueryType.RACE_SEARCH
        
        return QueryType.GENERAL_QUESTION
    
    def _generate_greeting_response(self) -> str:
        """Generate friendly greeting response."""
        stats = self.embeddings_client.get_stats()
        
        return f"""Zdravo! 👋 Ja sam vaš Trail AI asistent, tu sam da vam pomognem da otkrijete i naučite o trail trčanju!

Imam pristup podacima o **{stats['total_races']} trka** iz {stats['countries']} zemalja. Evo kako mogu da vam pomognem:

🔍 **Pretraživanje trka**: "Nađi trail trke u Srbiji" ili "Pokaži mi trke od 10km"
🎯 **Preporuke**: "Želim izazovnu trail trku u oktobru"  
📊 **Analiza trka**: "Koje su najpopularnije distance trka?"
⚖️ **Poređenje trka**: "Poredi Povlen Trail sa drugim srpskim trkama"
❓ **Opšta pitanja**: "Šta treba da znam o ultra trail trčanju?"

Pitajte me bilo šta o trail trkama! Šta biste želeli da znate?"""
    
    def _generate_help_response(self) -> str:
        """Generate help response."""
        return """I can help you with trail running races in several ways:

**🔍 Search & Discovery**
- "Find races in [country/region]"
- "Show me races in [month/date]"
- "What races are happening this weekend?"

**🎯 Personalized Recommendations**  
- "I'm looking for a 25km trail race in Serbia"
- "Recommend races for a beginner trail runner"
- "Find me an ultra race with good elevation"

**📊 Analysis & Statistics**
- "What's the average distance of trail races?"
- "Show me race trends by country"
- "How many races are there in October?"

**⚖️ Comparisons**
- "Compare [Race A] vs [Race B]"
- "What's the difference between trail and ultra races?"

**💡 General Questions**
- "What should I bring to a trail race?"
- "How do I prepare for my first ultra?"

Just ask naturally - I understand conversational language! What would you like to explore?"""
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add message to conversation history.
        
        Args:
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
    
    def process_message(self, user_input: str) -> Dict[str, Any]:
        """
        Process user message and generate response.
        
        Args:
            user_input: User's message
            
        Returns:
            Response dictionary with message and metadata
        """
        try:
            # Add user message to history
            self.add_message("user", user_input)
            
            # Classify query type
            query_type = self._classify_query(user_input)
            logger.info(f"Classified query as: {query_type.value}")
            
            # Generate response based on query type
            if query_type == QueryType.GREETING:
                response = self._generate_greeting_response()
                
            elif query_type == QueryType.HELP:
                response = self._generate_help_response()
                
            elif query_type == QueryType.RECOMMENDATIONS:
                rag_result = self.rag_client.get_recommendations(user_input)
                response = rag_result["answer"]
                # Update context with relevant races
                if rag_result.get("retrieved_races"):
                    self.context_races = rag_result["retrieved_races"]
                
            elif query_type == QueryType.STATISTICS:
                rag_result = self.rag_client.analyze_races(user_input)
                response = rag_result["answer"]
                
            elif query_type == QueryType.RACE_SEARCH:
                rag_result = self.rag_client.query(user_input, task_type="general")
                response = rag_result["answer"]
                # Update context with found races
                if rag_result.get("retrieved_races"):
                    self.context_races = rag_result["retrieved_races"]
                
            else:  # GENERAL_QUESTION, COMPARISON
                rag_result = self.rag_client.query(user_input, task_type="general")
                response = rag_result["answer"]
            
            # Add assistant response to history
            self.add_message("assistant", response, {
                "query_type": query_type.value,
                "context_races_count": len(self.context_races)
            })
            
            return {
                "response": response,
                "query_type": query_type.value,
                "session_id": self.session_id,
                "context_races": len(self.context_races),
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = f"I encountered an error processing your message: {str(e)}. Please try rephrasing your question."
            
            self.add_message("assistant", error_response, {"error": str(e)})
            
            return {
                "response": error_response,
                "error": str(e),
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Returns:
            List of messages
        """
        return self.messages.copy()
    
    def clear_context(self):
        """Clear conversation context."""
        self.context_races = []
        logger.info(f"Cleared context for session {self.session_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Statistics dictionary
        """
        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in self.messages if msg["role"] == "assistant"]
        
        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "context_races": len(self.context_races),
            "created_at": self.messages[0]["timestamp"] if self.messages else None,
            "last_activity": self.messages[-1]["timestamp"] if self.messages else None
        }


class ChatManager:
    """Manages multiple chat sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        logger.info("ChatManager initialized")
    
    def create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """
        Create new chat session.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            ChatSession instance
        """
        session = ChatSession(session_id)
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get existing session.
        
        Args:
            session_id: Session ID
            
        Returns:
            ChatSession if exists, None otherwise
        """
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all sessions.
        
        Returns:
            List of session statistics
        """
        return [session.get_session_stats() for session in self.sessions.values()]


# Global chat manager
_chat_manager = None

def get_chat_manager() -> ChatManager:
    """Get or create global chat manager."""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ChatManager()
    return _chat_manager


# Convenience functions

def start_chat_session(session_id: Optional[str] = None) -> ChatSession:
    """
    Start new chat session.
    
    Args:
        session_id: Optional session ID
        
    Returns:
        ChatSession instance
    """
    manager = get_chat_manager()
    return manager.create_session(session_id)


def chat_with_ai(message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple chat function for single interactions.
    
    Args:
        message: User message
        session_id: Optional session ID (creates new if not provided)
        
    Returns:
        Response dictionary
    """
    manager = get_chat_manager()
    
    if session_id:
        session = manager.get_session(session_id)
        if not session:
            session = manager.create_session(session_id)
    else:
        session = manager.create_session()
    
    return session.process_message(message)


def quick_ask(question: str) -> str:
    """
    Quick question without session management.
    
    Args:
        question: User question
        
    Returns:
        Answer text
    """
    result = chat_with_ai(question)
    return result.get("response", "No response available.")