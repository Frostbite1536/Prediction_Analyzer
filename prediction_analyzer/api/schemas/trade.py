# prediction_analyzer/api/schemas/trade.py
"""
Trade-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class TradeBase(BaseModel):
    """Base trade schema with common fields"""
    market: str
    market_slug: str
    timestamp: datetime
    price: float = 0.0
    shares: float = 0.0
    cost: float = 0.0
    type: str  # Buy, Sell, etc.
    side: str  # YES or NO
    pnl: float = 0.0
    tx_hash: Optional[str] = None


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
