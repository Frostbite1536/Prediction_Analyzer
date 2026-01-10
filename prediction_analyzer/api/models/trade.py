# prediction_analyzer/api/models/trade.py
"""
Trade and TradeUpload models for storing user trading data
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class TradeUpload(Base):
    """Metadata for trade file uploads"""
    __tablename__ = "trade_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # json, csv, xlsx
    trade_count = Column(Integer, default=0)
    file_hash = Column(String(64), nullable=True)  # SHA256 for dedup
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="uploads")
    trades = relationship("Trade", back_populates="upload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TradeUpload(id={self.id}, filename='{self.filename}')>"


class Trade(Base):
    """Individual trade record"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    upload_id = Column(Integer, ForeignKey("trade_uploads.id", ondelete="SET NULL"), nullable=True)

    # Trade data fields (matching the Trade dataclass)
    market = Column(String(500), nullable=False)
    market_slug = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float, default=0.0)
    shares = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    type = Column(String(50), nullable=False)  # Buy, Sell, Market Buy, Limit Sell, etc.
    side = Column(String(10), nullable=False)  # YES or NO
    pnl = Column(Float, default=0.0)
    tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="trades")
    upload = relationship("TradeUpload", back_populates="trades")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_trades_user_market", "user_id", "market_slug"),
        Index("ix_trades_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, market_slug='{self.market_slug}', type='{self.type}')>"
