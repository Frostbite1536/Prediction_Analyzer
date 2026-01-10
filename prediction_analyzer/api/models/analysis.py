# prediction_analyzer/api/models/analysis.py
"""
SavedAnalysis model for persisting user analysis results
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class SavedAnalysis(Base):
    """Saved analysis results"""
    __tablename__ = "saved_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Analysis parameters (stored as JSON string)
    filter_params = Column(Text, nullable=True)  # JSON: {start_date, end_date, types, etc.}
    market_slug = Column(String(255), nullable=True)  # For market-specific analyses

    # Analysis results (stored as JSON string)
    results = Column(Text, nullable=False)  # JSON: summary stats, market breakdown, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_analyses")

    def __repr__(self):
        return f"<SavedAnalysis(id={self.id}, name='{self.name}')>"
