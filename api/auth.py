"""
Authentication middleware for Trail AI API.
"""

import os
import secrets
from typing import Optional
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Generate or load API key
API_KEY = os.getenv("TRAIL_AI_API_KEY", "trail-ai-secret-key-2024")

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify API key from Authorization header."""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return credentials.credentials

def get_current_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get and verify current API key."""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return credentials.credentials