from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from v32.data.schemas import (
    StandardizedArticle, NewsFetchInput,
    EdgarFiling, CompanyFacts, EdgarSearchInput,
    DartFiling, DartFilingSearchInput, DartFinancialStatement, DartFinancialSearchInput
)
# Import connectors
from v32.connectors.news_connector import news_connector
from v32.connectors.edgar_connector import edgar_connector
from v32.connectors.dart_connector import dart_connector, DartAPIException

router = APIRouter()

# === Exception Handler Helper ===
def handle_data_exception(e: Exception):
    if isinstance(e, DartAPIException):
        # DART API 자체 오류 (예: 인증 실패, 파라미터 오류, 사용량 초과)
        status_code = status.HTTP_400_BAD_REQUEST
        if e.code in ["010", "011"]: status_code = status.HTTP_401_UNAUTHORIZED # 인증 오류
        if e.code == "020": status_code = status.HTTP_429_TOO_MANY_REQUESTS # 사용량 초과
        raise HTTPException(status_code=status_code, detail=str(e))
    elif isinstance(e, ValueError):
        # 기업 식별자 오류 (get_corp_code/get_cik 실패)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        # 기타 시스템 오류
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

# === News Routes (기존 유지) ===
@router.post("/news/search", response_model=List[StandardizedArticle])
async def search_news_route(payload: NewsFetchInput):
    try:
        results = await news_connector.search(
            query=payload.query,
            language=payload.language,
            max_results=payload.max_results
        )
        return results
    except Exception as e:
        handle_data_exception(e)

# === EDGAR Routes (기존 유지) ===
@router.post("/edgar/facts", response_model=CompanyFacts)
async def get_edgar_facts_route(payload: EdgarSearchInput):
    try:
        facts = await edgar_connector.get_company_facts(payload.ticker)
        if not facts:
            # 데이터는 있으나 파싱 실패 등 기타 이유로 None 반환 시
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facts not found or error occurred.")
        return facts
    except Exception as e:
        handle_data_exception(e)

@router.post("/edgar/filings", response_model=List[EdgarFiling])
async def get_edgar_filings_route(payload: EdgarSearchInput):
    try:
        filings = await edgar_connector.get_all_filings(payload.ticker)
        return filings
    except Exception as e:
        handle_data_exception(e)

# === DART Routes (신규 추가) ===

@router.post("/dart/filings", response_model=List[DartFiling])
async def search_dart_filings_route(payload: DartFilingSearchInput):
    """Search filings from KR DART system."""
    try:
        filings = await dart_connector.search_filings(payload)
        return filings
    except Exception as e:
        handle_data_exception(e)

@router.post("/dart/financials", response_model=List[DartFinancialStatement])
async def get_dart_financials_route(payload: DartFinancialSearchInput):
    """Fetch standardized financial statements (Full) from KR DART. Auto-handles CFS/OFS fallback."""
    try:
        statements = await dart_connector.get_financial_statements(payload)
        # 데이터가 없는 경우 (API 호출은 성공했으나 결과 없음, 예: 013 에러)는 빈 리스트 반환
        return statements
    except Exception as e:
        handle_data_exception(e)
