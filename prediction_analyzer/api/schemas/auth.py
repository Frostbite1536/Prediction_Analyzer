# prediction_analyzer/api/schemas/auth.py
"""
Authentication-related Pydantic schemas
"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from JWT token"""
    user_id: Optional[int] = None
