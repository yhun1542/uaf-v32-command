import httpx
from typing import Optional, Any
from v32.config.settings import settings

class UpstashRedisClient:
    def __init__(self):
        self.base_url = settings.KV_REST_API_URL
        self.token = settings.KV_REST_API_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.client = httpx.AsyncClient(headers=self.headers, timeout=10.0)
    
    async def get(self, key: str) -> Optional[str]:
        """GET key"""
        try:
            response = await self.client.get(f"{self.base_url}/get/{key}")
            if response.status_code == 200:
                data = response.json()
                return data.get("result")
            return None
        except Exception:
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """SET key value [EX seconds]"""
        try:
            url = f"{self.base_url}/set/{key}"
            if ex:
                url += f"?EX={ex}"
            response = await self.client.post(url, content=value)
            return response.status_code == 200
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """DEL key"""
        try:
            response = await self.client.get(f"{self.base_url}/del/{key}")
            return response.status_code == 200
        except Exception:
            return False
    
    async def lpush(self, key: str, *values: str) -> int:
        """LPUSH key value [value ...]"""
        try:
            # Upstash REST API: /lpush/{key}
            response = await self.client.post(
                f"{self.base_url}/lpush/{key}",
                json=list(values)
            )
            if response.status_code == 200:
                return response.json().get("result", 0)
            return 0
        except Exception:
            return 0
    
    async def lrange(self, key: str, start: int, stop: int) -> list:
        """LRANGE key start stop"""
        try:
            response = await self.client.get(f"{self.base_url}/lrange/{key}/{start}/{stop}")
            if response.status_code == 200:
                return response.json().get("result", [])
            return []
        except Exception:
            return []
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Global client instance
_redis_client: Optional[UpstashRedisClient] = None

async def get_redis_client() -> UpstashRedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = UpstashRedisClient()
    return _redis_client

async def close_redis_pool():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
