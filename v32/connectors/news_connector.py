"""
UAF V32 News Connector
Integrates NewsAPI and GNews for real-time news monitoring
"""
import os
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

class NewsArticle(BaseModel):
    """뉴스 기사 모델"""
    source: str
    title: str
    description: Optional[str] = None
    url: str
    published_at: str
    author: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None

class NewsConnector:
    """통합 뉴스 커넥터 (NewsAPI + GNews)"""
    
    def __init__(self):
        self.newsapi_key = os.getenv("NEWS_API_KEY", "")
        self.newsapi_url = "https://newsapi.org/v2"
        self.gnews_url = "https://gnews.io/api/v4"
        
    async def fetch_newsapi(
        self, 
        query: str = "AI OR technology", 
        language: str = "en",
        page_size: int = 10,
        days_back: int = 7
    ) -> List[NewsArticle]:
        """NewsAPI에서 뉴스 가져오기"""
        if not self.newsapi_key:
            return []
            
        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            params = {
                "q": query,
                "language": language,
                "pageSize": page_size,
                "from": from_date,
                "sortBy": "publishedAt",
                "apiKey": self.newsapi_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.newsapi_url}/everything", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []
                        
                        for article in data.get("articles", []):
                            articles.append(NewsArticle(
                                source=article.get("source", {}).get("name", "Unknown"),
                                title=article.get("title", ""),
                                description=article.get("description"),
                                url=article.get("url", ""),
                                published_at=article.get("publishedAt", ""),
                                author=article.get("author"),
                                content=article.get("content"),
                                image_url=article.get("urlToImage")
                            ))
                        
                        return articles
                    else:
                        print(f"NewsAPI error: {response.status}")
                        return []
        except Exception as e:
            print(f"NewsAPI fetch error: {e}")
            return []
    
    async def fetch_gnews(
        self,
        query: str = "artificial intelligence",
        language: str = "en",
        max_results: int = 10
    ) -> List[NewsArticle]:
        """GNews에서 뉴스 가져오기 (API 키 불필요)"""
        try:
            # GNews는 무료 API이며 제한적이지만 API 키 없이 사용 가능
            # 실제 구현에서는 gnews.io API를 사용하거나 RSS 피드를 파싱
            # 여기서는 Google News RSS를 사용하는 방식으로 구현
            
            # Google News RSS URL
            rss_url = f"https://news.google.com/rss/search?q={query}&hl={language}&gl=US&ceid=US:{language}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url) as response:
                    if response.status == 200:
                        import xml.etree.ElementTree as ET
                        content = await response.text()
                        root = ET.fromstring(content)
                        
                        articles = []
                        for item in root.findall(".//item")[:max_results]:
                            title = item.find("title")
                            link = item.find("link")
                            pub_date = item.find("pubDate")
                            description = item.find("description")
                            
                            articles.append(NewsArticle(
                                source="Google News",
                                title=title.text if title is not None else "",
                                description=description.text if description is not None else None,
                                url=link.text if link is not None else "",
                                published_at=pub_date.text if pub_date is not None else "",
                                author=None,
                                content=None,
                                image_url=None
                            ))
                        
                        return articles
                    else:
                        print(f"GNews RSS error: {response.status}")
                        return []
        except Exception as e:
            print(f"GNews fetch error: {e}")
            return []
    
    async def search_news(
        self,
        query: str,
        sources: List[str] = ["newsapi", "gnews"],
        language: str = "en",
        max_results: int = 20
    ) -> Dict[str, List[NewsArticle]]:
        """통합 뉴스 검색"""
        results = {}
        
        if "newsapi" in sources:
            results["newsapi"] = await self.fetch_newsapi(
                query=query,
                language=language,
                page_size=max_results
            )
        
        if "gnews" in sources:
            results["gnews"] = await self.fetch_gnews(
                query=query,
                language=language,
                max_results=max_results
            )
        
        return results
    
    async def get_trending_topics(
        self,
        category: str = "technology",
        language: str = "en",
        max_results: int = 10
    ) -> List[NewsArticle]:
        """트렌딩 토픽 가져오기"""
        if not self.newsapi_key:
            # Fallback to Google News RSS
            return await self.fetch_gnews(
                query=category,
                language=language,
                max_results=max_results
            )
        
        try:
            params = {
                "category": category,
                "language": language,
                "pageSize": max_results,
                "apiKey": self.newsapi_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.newsapi_url}/top-headlines", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []
                        
                        for article in data.get("articles", []):
                            articles.append(NewsArticle(
                                source=article.get("source", {}).get("name", "Unknown"),
                                title=article.get("title", ""),
                                description=article.get("description"),
                                url=article.get("url", ""),
                                published_at=article.get("publishedAt", ""),
                                author=article.get("author"),
                                content=article.get("content"),
                                image_url=article.get("urlToImage")
                            ))
                        
                        return articles
                    else:
                        return []
        except Exception as e:
            print(f"Trending topics error: {e}")
            return []
