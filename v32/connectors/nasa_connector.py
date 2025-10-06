"""
NASA Earthdata Connector
Provides access to NASA's Common Metadata Repository (CMR) for Earth observation data.
"""
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from v32.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class NASAConnector:
    """
    NASA Earthdata API Connector
    Access NASA's vast collection of Earth observation data through CMR.
    """
    
    def __init__(self):
        self.cmr_base_url = "https://cmr.earthdata.nasa.gov/search"
        self.token = settings.NASA_EARTHDATA_TOKEN.get_secret_value() if settings.NASA_EARTHDATA_TOKEN else None
        
        if not self.token:
            logger.warning("NASA_EARTHDATA_TOKEN not configured. Some features may be limited.")
    
    async def search_collections(
        self,
        keyword: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search NASA data collections (datasets) by keyword.
        
        Args:
            keyword: Search term (e.g., "MODIS", "Temperature", "Aerosol")
            max_results: Maximum number of results to return
            
        Returns:
            List of collection metadata
        """
        url = f"{self.cmr_base_url}/collections.json"
        params = {
            "keyword": keyword,
            "page_size": min(max_results, 2000)
        }
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                entries = data.get("feed", {}).get("entry", [])
                
                collections = []
                for entry in entries[:max_results]:
                    collections.append({
                        "collection_id": entry.get("id"),
                        "title": entry.get("title"),
                        "summary": entry.get("summary"),
                        "data_center": entry.get("data_center"),
                        "time_start": entry.get("time_start"),
                        "time_end": entry.get("time_end")
                    })
                
                return collections
                
        except httpx.HTTPError as e:
            logger.error(f"NASA CMR API error: {e}")
            raise
    
    async def search_granules(
        self,
        collection_concept_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for data granules (individual files) within a collection.
        
        Args:
            collection_concept_id: NASA collection ID
            start_date: Start of temporal range
            end_date: End of temporal range
            max_results: Maximum number of granules to return
            
        Returns:
            List of granule metadata with download links
        """
        url = f"{self.cmr_base_url}/granules.json"
        params = {
            "collection_concept_id": collection_concept_id,
            "page_size": min(max_results, 2000)
        }
        
        if start_date:
            params["temporal"] = f"{start_date.isoformat()}Z,"
            if end_date:
                params["temporal"] += f"{end_date.isoformat()}Z"
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                entries = data.get("feed", {}).get("entry", [])
                
                granules = []
                for entry in entries[:max_results]:
                    # Extract download links
                    data_links = []
                    browse_links = []
                    
                    for link in entry.get("links", []):
                        href = link.get("href")
                        rel = link.get("rel")
                        
                        if rel == "http://esipfed.org/ns/fedsearch/1.1/data#":
                            data_links.append(href)
                        elif rel == "http://esipfed.org/ns/fedsearch/1.1/browse#":
                            browse_links.append(href)
                    
                    granules.append({
                        "granule_id": entry.get("id"),
                        "title": entry.get("title"),
                        "collection_concept_id": collection_concept_id,
                        "start_time": entry.get("time_start"),
                        "end_time": entry.get("time_end"),
                        "data_links": data_links,
                        "browse_links": browse_links
                    })
                
                return granules
                
        except httpx.HTTPError as e:
            logger.error(f"NASA CMR granule search error: {e}")
            raise
    
    async def close(self):
        """Cleanup resources"""
        pass

# Global instance
nasa_connector = NASAConnector()
