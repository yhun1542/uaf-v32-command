"""
NASA Connector API Routes
"""
from fastapi import APIRouter, HTTPException
from v32.connectors.nasa_connector import nasa_connector
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.get("/nasa/collections")
async def search_nasa_collections(
    keyword: str,
    max_results: int = 20
):
    """
    Search NASA data collections by keyword.
    
    Example: /nasa/collections?keyword=MODIS&max_results=10
    """
    try:
        collections = await nasa_connector.search_collections(
            keyword=keyword,
            max_results=max_results
        )
        return {
            "status": "success",
            "keyword": keyword,
            "total_results": len(collections),
            "collections": collections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nasa/granules/{collection_id}")
async def search_nasa_granules(
    collection_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: int = 20
):
    """
    Search for data granules within a NASA collection.
    
    Example: /nasa/granules/C1234567890-LAADS?start_date=2024-01-01&max_results=5
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        granules = await nasa_connector.search_granules(
            collection_concept_id=collection_id,
            start_date=start_dt,
            end_date=end_dt,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "collection_id": collection_id,
            "total_results": len(granules),
            "granules": granules
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
