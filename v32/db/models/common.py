"""
Common Database Models
"""
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from v32.db.session import Base
import enum

class DataSource(enum.Enum):
    """Data source enumeration"""
    NEWS_API = "NEWS_API"
    GNEWS = "GNEWS"
    EDGAR = "EDGAR"
    DART = "DART"
    NASA = "NASA"
    PLANET = "PLANET"

class DataRecord(Base):
    """Generic data record for ETL pipeline"""
    __tablename__ = "data_records"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(SQLEnum(DataSource), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500))
    content = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AnalysisResult(Base):
    """Analysis results from TCI/NDDE modules"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # TCI, NDDE, etc.
    input_data_id = Column(Integer, index=True)
    result_data = Column(JSON)
    confidence_score = Column(Integer)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
