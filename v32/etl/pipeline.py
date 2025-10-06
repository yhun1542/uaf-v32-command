"""
ETL Pipeline Service
Extract, Transform, Load data from various connectors
"""
from typing import List, Dict, Any
from v32.db.session import SessionLocal
from v32.db.models.common import DataRecord, DataSource
from v32.connectors.news_connector import news_connector
from v32.connectors.edgar_connector import edgar_connector
from v32.connectors.dart_connector import dart_connector
from v32.connectors.nasa_connector import nasa_connector
import logging

logger = logging.getLogger(__name__)

class ETLPipeline:
    """
    Unified ETL Pipeline for all data sources
    """
    
    @staticmethod
    async def extract_news(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Extract news data"""
        try:
            results = await news_connector.search_news(
                query=query,
                sources=["gnews"],
                max_results=max_results
            )
            
            extracted = []
            for source, articles in results.items():
                for article in articles:
                    extracted.append({
                        "source": DataSource.GNEWS,
                        "external_id": article.url,
                        "title": article.title,
                        "content": article.description or "",
                        "metadata": {
                            "published_at": article.published_at.isoformat() if article.published_at else None,
                            "source_name": article.source.name
                        }
                    })
            
            return extracted
        except Exception as e:
            logger.error(f"News extraction failed: {e}")
            return []
    
    @staticmethod
    async def extract_edgar(ticker: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Extract EDGAR filings"""
        try:
            filings = await edgar_connector.search_filings(
                ticker=ticker,
                form_types=["10-K", "10-Q"],
                max_results=max_results
            )
            
            extracted = []
            for filing in filings:
                extracted.append({
                    "source": DataSource.EDGAR,
                    "external_id": filing.accession_number,
                    "title": f"{filing.company_name} - {filing.form_type}",
                    "content": filing.description or "",
                    "metadata": {
                        "filing_date": filing.filing_date.isoformat() if filing.filing_date else None,
                        "cik": filing.cik,
                        "file_url": filing.file_url
                    }
                })
            
            return extracted
        except Exception as e:
            logger.error(f"EDGAR extraction failed: {e}")
            return []
    
    @staticmethod
    async def load_to_database(records: List[Dict[str, Any]]) -> int:
        """Load extracted data to database"""
        db = SessionLocal()
        try:
            loaded_count = 0
            for record_data in records:
                # Check if record already exists
                existing = db.query(DataRecord).filter(
                    DataRecord.source == record_data["source"],
                    DataRecord.external_id == record_data["external_id"]
                ).first()
                
                if not existing:
                    record = DataRecord(**record_data)
                    db.add(record)
                    loaded_count += 1
            
            db.commit()
            return loaded_count
        except Exception as e:
            db.rollback()
            logger.error(f"Database load failed: {e}")
            return 0
        finally:
            db.close()
    
    @staticmethod
    async def run_pipeline(source: str, **kwargs) -> Dict[str, Any]:
        """
        Run full ETL pipeline for a data source
        
        Args:
            source: Data source name (news, edgar, dart, nasa)
            **kwargs: Source-specific parameters
            
        Returns:
            Pipeline execution summary
        """
        extracted = []
        
        if source == "news":
            extracted = await ETLPipeline.extract_news(
                query=kwargs.get("query", "AI"),
                max_results=kwargs.get("max_results", 20)
            )
        elif source == "edgar":
            extracted = await ETLPipeline.extract_edgar(
                ticker=kwargs.get("ticker", "AAPL"),
                max_results=kwargs.get("max_results", 10)
            )
        
        loaded_count = await ETLPipeline.load_to_database(extracted)
        
        return {
            "source": source,
            "extracted": len(extracted),
            "loaded": loaded_count,
            "status": "success" if loaded_count > 0 else "no_new_data"
        }

# Global instance
etl_pipeline = ETLPipeline()
