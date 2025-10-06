from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

# === News Schemas (기존 유지) ===
class NewsSource(BaseModel):
    id: Optional[str] = None
    name: str

class StandardizedArticle(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: HttpUrl
    image_url: Optional[HttpUrl] = None
    published_at: datetime
    source: NewsSource
    provider: str

class NewsFetchInput(BaseModel):
    query: str = Field(..., min_length=2)
    language: str = "en"
    max_results: int = Field(20, ge=1, le=100)

# === EDGAR Schemas (기존 유지) ===
class EdgarFiling(BaseModel):
    accession_number: str
    filing_date: date
    report_date: Optional[date] = None
    form: str
    primary_document: str
    primary_doc_description: Optional[str] = None

class CompanyFacts(BaseModel):
    cik: int
    entity_name: str
    facts: Dict[str, Any]

class EdgarSearchInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock Ticker (e.g., AAPL)")

# === DART Schemas (신규 추가) ===
class DartCompany(BaseModel):
    """DART 기업 정보 (CORPCODE.xml 기반)"""
    corp_code: str = Field(..., description="DART 고유번호 (8자리)")
    corp_name: str = Field(..., description="기업명")
    stock_code: Optional[str] = Field(None, description="주식 종목코드 (6자리)")
    modify_date: Optional[date] = Field(None, description="최종 수정일")

class DartFiling(BaseModel):
    """DART 공시 정보"""
    corp_code: str
    corp_name: str
    stock_code: Optional[str]
    corp_cls: str # 법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)
    report_nm: str # 보고서명
    rcept_no: str = Field(..., description="접수번호 (14자리, 공시 고유키)")
    flr_nm: str # 공시 제출인명
    rcept_dt: date # 공시 접수일자
    rm: Optional[str] = None # 비고

class DartFilingSearchInput(BaseModel):
    """DART 공시 검색 파라미터"""
    identifier: str = Field(..., description="기업명 또는 주식 종목코드")
    start_date: date = Field(..., description="검색 시작일 (YYYY-MM-DD)")
    end_date: date = Field(..., description="검색 종료일 (YYYY-MM-DD)")
    pblntf_ty: str = "A" # 공시유형 (A:전체)
    page_no: int = 1
    page_count: int = 100 # 최대 100

class FSType(str, Enum):
    CFS = "CFS" # 연결재무제표
    OFS = "OFS" # 별도(개별)재무제표

class DartFinancialStatement(BaseModel):
    """DART 표준화된 재무제표 항목 (전체 재무제표 API 기준: fnlttSinglAcntAll)"""
    rcept_no: str
    bsns_year: str # 사업연도
    corp_code: str
    stock_code: Optional[str]
    fs_div: FSType # CFS:연결, OFS:별도
    fs_nm: str # 연결/별도 명칭
    sj_div: str # 재무제표 구분 (BS, IS, CIS, CF)
    sj_nm: str # 재무제표명
    account_id: Optional[str] # 표준계정코드 (일부 항목은 없을 수 있음)
    account_nm: str # 계정명
    thstrm_nm: str # 당기명
    thstrm_amount: Optional[float] # 당기금액 (커넥터에서 변환)
    frmtrm_nm: Optional[str] = None # 전기명
    frmtrm_amount: Optional[float] = None # 전기금액
    bfefrmtrm_nm: Optional[str] = None # 전전기명
    bfefrmtrm_amount: Optional[float] = None # 전전기금액

class DartFinancialSearchInput(BaseModel):
    identifier: str = Field(..., description="기업명 또는 주식 종목코드")
    bsns_year: str = Field(..., description="사업연도 (YYYY)")
    reprt_code: str = "11011" # 보고서 코드 (11011: 사업보고서)
    fs_type: FSType = FSType.CFS # 기본값: 연결재무제표
