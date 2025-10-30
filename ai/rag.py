"""
RAG (Retrieval-Augmented Generation) system for Trail AI.

Combines semantic search with LLM generation to provide intelligent
answers about trail races based on the vector database.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date

from .embeddings import get_embeddings_client
from .llm import query_ollama, chat_with_ollama

logger = logging.getLogger(__name__)


class TrailRAG:
    """RAG system for trail running race queries."""
    
    def __init__(self):
        self.embeddings = get_embeddings_client()
    
    def _format_race_data(self, races: List[Dict[str, Any]], include_scores: bool = False) -> str:
        """
        Format race data for LLM context.
        
        Args:
            races: List of race data from search
            include_scores: Whether to include similarity scores
            
        Returns:
            Formatted text representation
        """
        if not races:
            return "No races found."
        
        formatted_races = []
        
        for i, race in enumerate(races, 1):
            metadata = race.get("metadata", {})
            
            # Build race info
            race_info = []
            
            # Basic info
            if metadata.get("name"):
                race_info.append(f"**{metadata['name']}**")
            
            if metadata.get("date"):
                race_info.append(f"Datum: {metadata['date']}")
            
            if metadata.get("location") and metadata.get("country"):
                race_info.append(f"Lokacija: {metadata['location']}, {metadata['country']}")
            elif metadata.get("location"):
                race_info.append(f"Lokacija: {metadata['location']}")
            elif metadata.get("country"):
                race_info.append(f"Zemlja: {metadata['country']}")
            
            # Race details
            details = []
            if metadata.get("distance_km"):
                details.append(f"{metadata['distance_km']} km")
            if metadata.get("elevation_m"):
                details.append(f"D+ {metadata['elevation_m']} m")
            if metadata.get("race_type"):
                details.append(f"Tip: {metadata['race_type']}")
            if metadata.get("terrain"):
                details.append(f"Teren: {metadata['terrain']}")
            
            if details:
                race_info.append(" | ".join(details))
            
            # Organization info
            if metadata.get("organizer"):
                race_info.append(f"Organizator: {metadata['organizer']}")
            
            # Fees
            if metadata.get("fee_eur"):
                race_info.append(f"Kotizacija: €{metadata['fee_eur']}")
            elif metadata.get("fee_rsd"):
                race_info.append(f"Kotizacija: {metadata['fee_rsd']} RSD")
            
            # Registration
            reg_info = []
            if metadata.get("registration_opens"):
                reg_info.append(f"Opens: {metadata['registration_opens']}")
            if metadata.get("registration_closes"):
                reg_info.append(f"Closes: {metadata['registration_closes']}")
            if metadata.get("registration_url"):
                reg_info.append(f"Register: {metadata['registration_url']}")
            
            if reg_info:
                race_info.append("Registration - " + " | ".join(reg_info))
            
            # Website
            if metadata.get("website"):
                race_info.append(f"Website: {metadata['website']}")
            
            # Score (if requested)
            if include_scores and race.get("similarity_score"):
                score = race["similarity_score"]
                race_info.append(f"(Relevance: {score:.2f})")
            
            formatted_races.append(f"{i}. " + "\n   ".join(race_info))
        
        return "\n\n".join(formatted_races)
    
    def _build_context_prompt(self, query: str, races: List[Dict[str, Any]], 
                            task_type: str = "general") -> str:
        """
        Build context prompt for LLM based on retrieved races.
        
        Args:
            query: User query
            races: Retrieved race data
            task_type: Type of task (general, recommendation, analysis)
            
        Returns:
            Context prompt for LLM
        """
        race_data = self._format_race_data(races)
        
        if task_type == "recommendation":
            return f"""You are a trail running expert helping a user find suitable races. Based on their query and the available race data, provide personalized recommendations.

User Query: "{query}"

Available Races:
{race_data}

Please provide specific race recommendations with clear reasoning. Consider factors like distance, location, terrain, dates, and the user's implied preferences. If no races match well, explain why and suggest alternatives."""

        elif task_type == "analysis":
            return f"""You are a trail running data analyst. Analyze the provided race data to answer the user's question with insights and patterns.

User Query: "{query}"

Race Data:
{race_data}

Provide a data-driven analysis addressing the user's question. Include specific examples from the data and identify relevant trends or patterns."""

        else:  # general
            return f"""Ti si stručnjak za trail trčanje u Srbiji. Odgovori UVEK na srpskom jeziku. Koristi pružene podatke o trkama da odgovoriš precizno i korisno na pitanje korisnika.

VAŽNO: 
- Odgovori SAMO na srpskom jeziku
- Budi kratak i precizan  
- Navedi konkretne detalje iz podataka
- Ako ne znaš tačan odgovor, reci to jasno

Pitanje korisnika: "{query}"

Relevantni podaci o trkama:
{race_data}

ODGOVORI SAMO NA SRPSKOM JEZIKU! Ne smeš koristiti engleski. Odgovori kratko i precizno."""
    
    def query(self, user_query: str, n_results: int = 10, 
             filters: Optional[Dict[str, Any]] = None,
             task_type: str = "general") -> Dict[str, Any]:
        """
        Process user query using RAG approach.
        
        Args:
            user_query: User's natural language query
            n_results: Number of races to retrieve for context
            filters: Optional metadata filters for search
            task_type: Type of task (general, recommendation, analysis)
            
        Returns:
            Dictionary with answer and metadata
        """
        try:
            # Step 1: Retrieve relevant races
            logger.info(f"Processing RAG query: '{user_query}'")
            retrieved_races = self.embeddings.search_races(
                query=user_query,
                n_results=n_results,
                where=filters
            )
            
            if not retrieved_races:
                return {
                    "answer": "Nisam našao trke koje odgovaraju vašem pitanju. Molim pokušajte da preformulišete pitanje ili proverite da li postoje trke u bazi podataka.",
                    "races_found": 0,
                    "query": user_query,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Step 2: Build context prompt
            context_prompt = self._build_context_prompt(user_query, retrieved_races, task_type)
            
            # Step 3: Generate answer using LLM
            logger.info(f"Generating answer using {len(retrieved_races)} retrieved races")
            logger.info(f"Context prompt: {context_prompt[:200]}...")  # Debug
            system_prompt = "JAKO VAŽNO: Odgovori SAMO na srpskom jeziku! Nikad ne koristiš engleski. Ti si srpski stručnjak za trail trčanje. Kratko i precizno odgovori."
            answer = query_ollama(context_prompt, system=system_prompt)
            
            return {
                "answer": answer,
                "races_found": len(retrieved_races),
                "retrieved_races": retrieved_races[:5],  # Include top 5 for reference
                "query": user_query,
                "task_type": task_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "error": str(e),
                "query": user_query,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_recommendations(self, user_preferences: str, n_results: int = 15) -> Dict[str, Any]:
        """
        Get personalized race recommendations.
        
        Args:
            user_preferences: Description of user preferences
            n_results: Number of races to consider
            
        Returns:
            Dictionary with recommendations
        """
        return self.query(
            user_query=user_preferences,
            n_results=n_results,
            task_type="recommendation"
        )
    
    def analyze_races(self, analysis_query: str, n_results: int = 20) -> Dict[str, Any]:
        """
        Analyze race data to answer analytical questions.
        
        Args:
            analysis_query: Analytical question
            n_results: Number of races to analyze
            
        Returns:
            Dictionary with analysis results
        """
        return self.query(
            user_query=analysis_query,
            n_results=n_results,
            task_type="analysis"
        )
    
    def search_races_by_criteria(self, criteria: Dict[str, Any], 
                                user_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Search races by specific criteria with optional natural language query.
        
        Args:
            criteria: Dictionary of search criteria
            user_query: Optional natural language description
            
        Returns:
            Dictionary with search results
        """
        # Build metadata filters from criteria
        filters = {}
        
        if criteria.get("country"):
            filters["country"] = criteria["country"]
        
        if criteria.get("race_type"):
            filters["race_type"] = criteria["race_type"]
        
        if criteria.get("source"):
            filters["source"] = criteria["source"]
        
        # Build search query
        if user_query:
            search_query = user_query
        else:
            # Build query from criteria
            query_parts = []
            if criteria.get("distance_min") or criteria.get("distance_max"):
                query_parts.append("distance")
            if criteria.get("terrain"):
                query_parts.append(criteria["terrain"])
            if criteria.get("location"):
                query_parts.append(criteria["location"])
            
            search_query = " ".join(query_parts) if query_parts else "trail race"
        
        return self.query(
            user_query=search_query,
            n_results=20,
            filters=filters if filters else None,
            task_type="general"
        )
    
    def chat_conversation(self, messages: List[Dict[str, str]], 
                         context_races: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Handle multi-turn conversation with race context.
        
        Args:
            messages: List of conversation messages
            context_races: Optional race context to maintain
            
        Returns:
            Assistant response
        """
        try:
            # If we have context races, add them to the system message
            if context_races:
                race_context = self._format_race_data(context_races)
                system_message = {
                    "role": "system",
                    "content": f"""You are a trail running expert assistant. You have access to the following race information to help answer questions:

{race_context}

Use this race data to provide helpful, accurate responses about trail running races. Be conversational and friendly while staying factual."""
                }
                
                # Insert system message at the beginning
                chat_messages = [system_message] + messages
            else:
                chat_messages = messages
            
            return chat_with_ollama(chat_messages)
            
        except Exception as e:
            logger.error(f"Chat conversation failed: {e}")
            return f"I encountered an error: {str(e)}"


# Global RAG instance
_rag_instance = None

def get_rag_client() -> TrailRAG:
    """Get or create global RAG client."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = TrailRAG()
    return _rag_instance


# Convenience functions

def ask_about_races(question: str, n_results: int = 10) -> str:
    """
    Simple function to ask questions about races.
    
    Args:
        question: Natural language question
        n_results: Number of races to consider
        
    Returns:
        Answer text
    """
    rag = get_rag_client()
    result = rag.query(question, n_results=n_results)
    return result.get("answer", "No answer available.")


def get_race_recommendations(preferences: str, n_results: int = 15) -> str:
    """
    Get race recommendations based on preferences.
    
    Args:
        preferences: User preferences description
        n_results: Number of races to consider
        
    Returns:
        Recommendations text
    """
    rag = get_rag_client()
    result = rag.get_recommendations(preferences, n_results=n_results)
    return result.get("answer", "No recommendations available.")


def analyze_race_data(analysis_question: str, n_results: int = 20) -> str:
    """
    Analyze race data to answer analytical questions.
    
    Args:
        analysis_question: Analytical question
        n_results: Number of races to analyze
        
    Returns:
        Analysis text
    """
    rag = get_rag_client()
    result = rag.analyze_races(analysis_question, n_results=n_results)
    return result.get("answer", "No analysis available.")