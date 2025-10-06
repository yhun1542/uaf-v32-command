"""
UAF V32 EDGAR Connector
Integrates SEC EDGAR API for financial filings monitoring
"""
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

class SECFiling(BaseModel):
    """SEC 파일링 모델"""
    company_name: str
    cik: str
    form_type: str
    filing_date: str
    accession_number: str
    file_url: str
    description: Optional[str] = None

class EDGARConnector:
    """SEC EDGAR API 커넥터"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            "User-Agent": "UAF V32 Command Hub contact@uaf.ai",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        }
    
    async def get_company_cik(self, ticker: str) -> Optional[str]:
        """티커 심볼로 CIK 번호 조회"""
        try:
            # SEC의 회사 티커 매핑 파일 사용
            url = f"{self.base_url}/files/company_tickers.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 티커로 CIK 찾기
                        for key, company in data.items():
                            if company.get("ticker", "").upper() == ticker.upper():
                                cik = str(company.get("cik_str", "")).zfill(10)
                                return cik
                        
                        return None
                    else:
                        print(f"CIK lookup error: {response.status}")
                        return None
        except Exception as e:
            print(f"CIK lookup error: {e}")
            return None
    
    async def get_company_filings(
        self,
        cik: str,
        form_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[SECFiling]:
        """회사의 SEC 파일링 조회"""
        try:
            # CIK를 10자리로 패딩
            cik_padded = cik.zfill(10)
            
            # SEC submissions API 사용
            url = f"{self.base_url}/submissions/CIK{cik_padded}.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        filings = []
                        
                        recent_filings = data.get("filings", {}).get("recent", {})
                        
                        if not recent_filings:
                            return []
                        
                        # 파일링 데이터 파싱
                        forms = recent_filings.get("form", [])
                        filing_dates = recent_filings.get("filingDate", [])
                        accession_numbers = recent_filings.get("accessionNumber", [])
                        primary_docs = recent_filings.get("primaryDocument", [])
                        
                        company_name = data.get("name", "Unknown")
                        
                        for i in range(min(len(forms), max_results * 3)):  # 여유있게 가져오기
                            form_type = forms[i]
                            
                            # 폼 타입 필터링
                            if form_types and form_type not in form_types:
                                continue
                            
                            if len(filings) >= max_results:
                                break
                            
                            accession = accession_numbers[i].replace("-", "")
                            file_url = f"{self.base_url}/Archives/edgar/data/{cik}/{accession}/{primary_docs[i]}"
                            
                            filings.append(SECFiling(
                                company_name=company_name,
                                cik=cik,
                                form_type=form_type,
                                filing_date=filing_dates[i],
                                accession_number=accession_numbers[i],
                                file_url=file_url,
                                description=f"{form_type} filing for {company_name}"
                            ))
                        
                        return filings
                    else:
                        print(f"SEC filings error: {response.status}")
                        return []
        except Exception as e:
            print(f"SEC filings fetch error: {e}")
            return []
    
    async def get_recent_filings(
        self,
        form_types: List[str] = ["10-K", "10-Q", "8-K"],
        max_results: int = 20
    ) -> List[SECFiling]:
        """최근 SEC 파일링 조회 (모든 회사)"""
        try:
            # RSS 피드를 사용하여 최근 파일링 가져오기
            filings = []
            
            for form_type in form_types:
                url = f"{self.base_url}/cgi-bin/browse-edgar"
                params = {
                    "action": "getcurrent",
                    "type": form_type,
                    "count": max_results // len(form_types),
                    "output": "atom"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, headers=self.headers) as response:
                        if response.status == 200:
                            import xml.etree.ElementTree as ET
                            content = await response.text()
                            root = ET.fromstring(content)
                            
                            # Atom 네임스페이스
                            ns = {"atom": "http://www.w3.org/2005/Atom"}
                            
                            for entry in root.findall("atom:entry", ns):
                                title = entry.find("atom:title", ns)
                                link = entry.find("atom:link", ns)
                                updated = entry.find("atom:updated", ns)
                                
                                if title is not None and link is not None:
                                    title_text = title.text or ""
                                    parts = title_text.split(" - ")
                                    
                                    company_name = parts[1] if len(parts) > 1 else "Unknown"
                                    
                                    filings.append(SECFiling(
                                        company_name=company_name,
                                        cik="",
                                        form_type=form_type,
                                        filing_date=updated.text[:10] if updated is not None else "",
                                        accession_number="",
                                        file_url=link.get("href", ""),
                                        description=title_text
                                    ))
            
            return filings[:max_results]
        except Exception as e:
            print(f"Recent filings error: {e}")
            return []
    
    async def search_filings(
        self,
        ticker: str,
        form_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[SECFiling]:
        """티커로 SEC 파일링 검색"""
        # 먼저 CIK 조회
        cik = await self.get_company_cik(ticker)
        
        if not cik:
            print(f"CIK not found for ticker: {ticker}")
            return []
        
        # CIK로 파일링 조회
        return await self.get_company_filings(cik, form_types, max_results)
    
    async def get_filing_content(self, filing_url: str) -> Optional[str]:
        """파일링 내용 다운로드"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(filing_url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        return None
        except Exception as e:
            print(f"Filing content download error: {e}")
            return None
