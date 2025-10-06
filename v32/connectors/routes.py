"""
UAF V32 Connector Routes
API endpoints for News and EDGAR connectors
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from .news_connector import NewsConnector, NewsArticle
from .edgar_connector import EDGARConnector, SECFiling
from .nasa_connector import nasa_connector

router = APIRouter()

# Initialize connectors
news_connector = NewsConnector()
edgar_connector = EDGARConnector(user_email="yhjun@seohancorp.com")

# ==================== News Connector Routes ====================

@router.get("/news/search", response_model=dict)
async def search_news(
    query: str = Query(..., description="Search query"),
    sources: str = Query("newsapi,gnews", description="Comma-separated sources"),
    language: str = Query("en", description="Language code"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results per source")
):
    """뉴스 검색 (NewsAPI + GNews)"""
    try:
        source_list = [s.strip() for s in sources.split(",")]
        results = await news_connector.search_news(
            query=query,
            sources=source_list,
            language=language,
            max_results=max_results
        )
        
        total_articles = sum(len(articles) for articles in results.values())
        
        return {
            "status": "success",
            "query": query,
            "sources": source_list,
            "total_articles": total_articles,
            "results": {
                source: [article.dict() for article in articles]
                for source, articles in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News search failed: {str(e)}")

@router.get("/news/trending", response_model=dict)
async def get_trending_news(
    category: str = Query("technology", description="News category"),
    language: str = Query("en", description="Language code"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """트렌딩 뉴스 가져오기"""
    try:
        articles = await news_connector.get_trending_topics(
            category=category,
            language=language,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "category": category,
            "total_articles": len(articles),
            "articles": [article.dict() for article in articles]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trending news failed: {str(e)}")

@router.get("/news/newsapi", response_model=dict)
async def fetch_newsapi(
    query: str = Query("AI OR technology", description="Search query"),
    language: str = Query("en", description="Language code"),
    page_size: int = Query(10, ge=1, le=100, description="Results per page"),
    days_back: int = Query(7, ge=1, le=30, description="Days to look back")
):
    """NewsAPI 전용 검색"""
    try:
        articles = await news_connector.fetch_newsapi(
            query=query,
            language=language,
            page_size=page_size,
            days_back=days_back
        )
        
        return {
            "status": "success",
            "source": "newsapi",
            "query": query,
            "total_articles": len(articles),
            "articles": [article.dict() for article in articles]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NewsAPI fetch failed: {str(e)}")

@router.get("/news/gnews", response_model=dict)
async def fetch_gnews(
    query: str = Query("artificial intelligence", description="Search query"),
    language: str = Query("en", description="Language code"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """GNews (Google News RSS) 전용 검색"""
    try:
        articles = await news_connector.fetch_gnews(
            query=query,
            language=language,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "source": "gnews",
            "query": query,
            "total_articles": len(articles),
            "articles": [article.dict() for article in articles]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GNews fetch failed: {str(e)}")

# ==================== EDGAR Connector Routes ====================

@router.get("/edgar/company/{ticker}", response_model=dict)
async def search_company_filings(
    ticker: str,
    form_types: Optional[str] = Query(None, description="Comma-separated form types (e.g., 10-K,10-Q)"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """티커로 회사 SEC 파일링 검색"""
    try:
        form_list = [f.strip() for f in form_types.split(",")] if form_types else None
        
        filings = await edgar_connector.search_filings(
            ticker=ticker,
            form_types=form_list,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "ticker": ticker,
            "form_types": form_list,
            "total_filings": len(filings),
            "filings": [filing.dict() for filing in filings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EDGAR search failed: {str(e)}")

@router.get("/edgar/recent", response_model=dict)
async def get_recent_filings(
    form_types: str = Query("10-K,10-Q,8-K", description="Comma-separated form types"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """최근 SEC 파일링 조회 (모든 회사)"""
    try:
        form_list = [f.strip() for f in form_types.split(",")]
        
        filings = await edgar_connector.get_recent_filings(
            form_types=form_list,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "form_types": form_list,
            "total_filings": len(filings),
            "filings": [filing.dict() for filing in filings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recent filings failed: {str(e)}")

@router.get("/edgar/cik/{ticker}", response_model=dict)
async def lookup_cik(ticker: str):
    """티커로 CIK 번호 조회"""
    try:
        cik = await edgar_connector.get_company_cik(ticker)
        
        if not cik:
            raise HTTPException(status_code=404, detail=f"CIK not found for ticker: {ticker}")
        
        return {
            "status": "success",
            "ticker": ticker,
            "cik": cik
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CIK lookup failed: {str(e)}")

@router.get("/edgar/filing/content", response_model=dict)
async def get_filing_content(
    url: str = Query(..., description="Filing URL")
):
    """SEC 파일링 내용 다운로드"""
    try:
        content = await edgar_connector.get_filing_content(url)
        
        if not content:
            raise HTTPException(status_code=404, detail="Filing content not found")
        
        return {
            "status": "success",
            "url": url,
            "content": content[:10000],  # 처음 10KB만 반환 (전체는 너무 클 수 있음)
            "content_length": len(content),
            "truncated": len(content) > 10000
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filing content fetch failed: {str(e)}")

# ==================== NASA Connector Routes ====================

@router.get("/nasa/collections")
async def search_nasa_collections(
    keyword: str = Query(..., description="Search keyword"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """NASA 데이터 컬렉션 검색"""
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
        raise HTTPException(status_code=500, detail=f"NASA collection search failed: {str(e)}")

@router.get("/nasa/granules/{collection_id}")
async def search_nasa_granules(
    collection_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """NASA 데이터 그래뉼 검색"""
    try:
        from datetime import datetime
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
        raise HTTPException(status_code=500, detail=f"NASA granule search failed: {str(e)}")

# ==================== Health Check ====================

@router.get("/health")
async def connectors_health():
    """커넥터 상태 확인"""
    return {
        "status": "ok",
        "connectors": {
            "news": {
                "newsapi": bool(news_connector.newsapi_key),
                "gnews": True
            },
            "edgar": True,
            "nasa": bool(nasa_connector.token)
        }
    }
