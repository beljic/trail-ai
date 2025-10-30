"""
Ollama LLM interface for Trail AI.

Provides functions to query local Ollama instance for various tasks:
- Chat completions
- Text generation
- Question answering
"""

import json
import os
import requests
from typing import Optional, Dict, Any, List, Generator
import logging

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class OllamaClient:
    """Client for interacting with local Ollama instance."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session = requests.Session()
        
    def _make_request(self, endpoint: str, data: Dict[Any, Any]) -> requests.Response:
        """Make HTTP request to Ollama API."""
        url = f"{self.base_url}/api/{endpoint}"
        try:
            # Use direct requests instead of session
            response = requests.post(url, json=data, timeout=60)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise
    
    def generate(self, prompt: str, model: Optional[str] = None, 
                system: Optional[str] = None, stream: bool = False,
                **kwargs) -> Dict[str, Any]:
        """
        Generate text completion from prompt.
        
        Args:
            prompt: Input prompt
            model: Model to use (defaults to instance model)
            system: System message for context
            stream: Whether to stream response
            **kwargs: Additional parameters (temperature, top_p, etc.)
            
        Returns:
            Dict with generated response
        """
        # Use chat format instead of generate
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        response = self._make_request("chat", data)
        
        if stream:
            # Handle streaming response
            result_lines = []
            for line in response.iter_lines():
                if line:
                    result_lines.append(json.loads(line))
            return {"responses": result_lines}
        else:
            # Parse chat response format
            result = response.json()
            # Convert chat response to generate format for compatibility
            if "message" in result and "content" in result["message"]:
                result["response"] = result["message"]["content"]
            return result
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
             stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Chat completion with conversation history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to instance model)
            stream: Whether to stream response
            **kwargs: Additional parameters
            
        Returns:
            Dict with chat response
        """
        data = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        response = self._make_request("chat", data)
        return response.json()
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """Get list of available models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []


# Global client instance
_client = None

def get_client() -> OllamaClient:
    """Get or create global Ollama client."""
    global _client
    # Always create fresh client to avoid caching issues
    _client = OllamaClient()
    return _client


def query_ollama(prompt: str, system: Optional[str] = None, 
                model: Optional[str] = None, **kwargs) -> str:
    """
    Simple text generation function.
    
    Args:
        prompt: Input prompt
        system: System message for context
        model: Model to use
        **kwargs: Additional parameters
        
    Returns:
        Generated text response
    """
    client = get_client()
    
    if not client.is_available():
        raise ConnectionError("Ollama service is not available. Make sure it's running on localhost:11434")
    
    try:
        response = client.generate(prompt, model=model, system=system, **kwargs)
        return response.get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama query failed: {e}")
        raise


def chat_with_ollama(messages: List[Dict[str, str]], model: Optional[str] = None,
                    **kwargs) -> str:
    """
    Chat with conversation history.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use
        **kwargs: Additional parameters
        
    Returns:
        Assistant response text
    """
    client = get_client()
    
    if not client.is_available():
        raise ConnectionError("Ollama service is not available")
    
    try:
        response = client.chat(messages, model=model, **kwargs)
        return response.get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Ollama chat failed: {e}")
        raise


# Specialized functions for Trail AI use cases

def summarize_races(race_data: str, question: str = None) -> str:
    """
    Summarize race information or answer questions about races.
    
    Args:
        race_data: Formatted race data as text
        question: Optional specific question to answer
        
    Returns:
        Summary or answer
    """
    system_prompt = """You are a trail running expert assistant. You help users understand and analyze trail running race data. 
    
Provide clear, concise, and helpful responses. When discussing races, include relevant details like:
- Race names, dates, locations
- Distances and elevation gains
- Registration information
- Organizer details

Be friendly and knowledgeable about trail running."""

    if question:
        prompt = f"""Based on this race data, please answer the following question:

Question: {question}

Race Data:
{race_data}

Please provide a helpful answer based on the available data."""
    else:
        prompt = f"""Please provide a summary of these trail races:

{race_data}

Focus on the most interesting and relevant information for trail runners."""

    return query_ollama(prompt, system=system_prompt)


def generate_race_recommendations(user_query: str, race_data: str) -> str:
    """
    Generate personalized race recommendations based on user preferences.
    
    Args:
        user_query: User's question or preferences
        race_data: Available race data
        
    Returns:
        Personalized recommendations
    """
    system_prompt = """You are a trail running coach and race expert. Help users find the perfect races based on their preferences, experience level, and goals.

Consider factors like:
- Distance preferences and experience level
- Location and travel preferences  
- Terrain types (trail, road, mixed)
- Race dates and timing
- Registration deadlines and fees
- Elevation and difficulty level

Provide specific recommendations with reasoning."""

    prompt = f"""A trail runner is asking: "{user_query}"

Based on this available race data, please provide personalized recommendations:

{race_data}

Give specific race suggestions with clear reasoning for each recommendation."""

    return query_ollama(prompt, system=system_prompt)


def extract_race_insights(race_data: str) -> str:
    """
    Extract insights and analysis from race data.
    
    Args:
        race_data: Race data to analyze
        
    Returns:
        Insights and analysis
    """
    system_prompt = """You are a data analyst specializing in trail running events. Analyze race data to identify patterns, trends, and interesting insights.

Look for patterns in:
- Popular race distances and formats
- Geographic distribution 
- Seasonal timing
- Price ranges and registration patterns
- Organizer trends
- Terrain and elevation patterns

Provide actionable insights for both runners and race organizers."""

    prompt = f"""Please analyze this trail race data and provide key insights and trends:

{race_data}

What interesting patterns, trends, or insights can you identify?"""

    return query_ollama(prompt, system=system_prompt)