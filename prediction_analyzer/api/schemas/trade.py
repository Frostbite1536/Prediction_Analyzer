# prediction_analyzer/api/schemas/trade.py
"""
Trade-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class TradeBase(BaseModel):
    """Base trade schema with common fields"""

    market: str = Field(..., min_length=1, max_length=500)
    market_slug: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime
    price: float = Field(0.0, ge=0.0, le=1_000_000.0)
    shares: float = Field(0.0, ge=0.0, le=1_000_000_000.0)
    cost: float = Field(0.0, ge=0.0, le=1_000_000_000.0)
    type: str = Field(..., min_length=1, max_length=50)  # Buy, Sell, etc.
    side: str = Field(..., min_length=1, max_length=10)  # YES or NO
    pnl: float = Field(0.0, ge=-1_000_000_000.0, le=1_000_000_000.0)
    tx_hash: Optional[str] = Field(None, max_length=100)
    source: str = Field(
        "limitless", max_length=50
    )  # "limitless", "polymarket", "kalshi", "manifold"
    currency: str = Field("USD", max_length=10)  # "USD", "USDC", "MANA"


class TradeCreate(TradeBase):
    """Schema for creating a trade manually"""

    pass


class TradeResponse(TradeBase):
    """Schema for trade response"""

    id: int
    user_id: int
    upload_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    """Schema for paginated trade list"""

    trades: List[TradeResponse]
    total: int
    limit: int
    offset: int


class TradeUploadResponse(BaseModel):
    """Response after uploading trades"""

    upload_id: int
    filename: str
    trade_count: int
    message: str


class MarketInfo(BaseModel):
    """Market information for listing"""

    slug: str
    title: str
    trade_count: int
    total_pnl: float
