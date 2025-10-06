"""
UAF V32 EDGAR Connector - Improved Version
Integrates SEC EDGAR API for financial filings monitoring
With proper rate limiting and error handling
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from collections import deque
import time
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class SECFiling(BaseModel):
    """SEC 파일링 모델"""
    company_name: str
    cik: str
    form_type: str
    filing_date: str
    accession_number: str
    file_url: str
    description: Optional[str] = None

class RateLimiter:
    """SEC EDGAR API 요청 제한 관리 (10 req/sec)"""
    
    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """요청 허가 대기"""
        async with self.lock:
            now = time.time()
            
            # 시간 윈도우 밖의 요청 제거
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # 제한 초과 시 대기
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            # 요청 기록
            self.requests.append(now)

class EDGARConnector:
    """SEC EDGAR API 커넥터 with Rate Limiting and Error Handling"""
    
    def __init__(self, user_email: str = "admin@example.com"):
        """
        초기화
        
        Args:
            user_email: SEC API 접근에 사용할 이메일 주소
                       실제 이메일로 변경 권장 (SEC Fair Access Policy)
        """
        self.base_url = "https://data.sec.gov"
        self.user_email = user_email
        self.headers = {
            "User-Agent": f"UAF-V32-Command-Hub {user_email}",
            "Accept-Encoding": "gzip, deflate"
        }
        self.rate_limiter = RateLimiter(max_requests=10, time_window=1.0)
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        
        # CIK 캐시 (메모리 캐싱)
        self.cik_cache = {}
    
    async def _get_session(self):
        """세션 생성 또는 반환"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )
        return self.session
    
    async def close(self):
        """세션 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(
        self, 
        url: str, 
        params: Optional[Dict] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Rate limiting과 retry logic이 적용된 HTTP 요청
        
        Args:
            url: 요청 URL
            params: URL 파라미터
            max_retries: 최대 재시도 횟수
            backoff_factor: 지수 백오프 계수
        """
        session = await self._get_session()
        
        for attempt in range(max_retries):
            try:
                # Rate limiting 적용
                await self.rate_limiter.acquire()
                
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 403:
                        logger.error(f"Access forbidden (403). Check User-Agent: {self.headers['User-Agent']}")
                        logger.info("Please use a valid email address in User-Agent header")
                        return None
                    elif response.status == 429:
                        # Too Many Requests - 지수 백오프
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Rate limit exceeded (429). Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Request failed with status {response.status}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                continue
            except Exception as e:
                logger.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                continue
        
        return None
    
    async def get_company_cik(self, ticker: str) -> Optional[str]:
        """
        티커 심볼로 CIK 번호 조회 (캐싱 포함)
        
        Args:
            ticker: 주식 티커 심볼 (예: 'AAPL')
        
        Returns:
            CIK 번호 (10자리 문자열) 또는 None
        """
        ticker_upper = ticker.upper()
        
        # 캐시 확인
        if ticker_upper in self.cik_cache:
            return self.cik_cache[ticker_upper]
        
        try:
            # company_tickers.json은 www.sec.gov에 있음
            url = "https://www.sec.gov/files/company_tickers.json"
            data = await self._make_request(url)
            
            if data:
                # 티커로 CIK 찾기
                for key, company in data.items():
                    if company.get("ticker", "").upper() == ticker_upper:
                        cik = str(company.get("cik_str", "")).zfill(10)
                        # 캐시에 저장
                        self.cik_cache[ticker_upper] = cik
                        logger.info(f"Found CIK {cik} for ticker {ticker_upper}")
                        return cik
                
                logger.warning(f"CIK not found for ticker: {ticker}")
                return None
            else:
                logger.error(f"Failed to fetch company tickers data")
                return None
                
        except Exception as e:
            logger.error(f"CIK lookup error: {e}")
            return None
    
    async def get_company_filings(
        self,
        cik: str,
        form_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[SECFiling]:
        """
        회사의 SEC 파일링 조회
        
        Args:
            cik: CIK 번호
            form_types: 필터링할 폼 타입 리스트 (예: ['10-K', '10-Q'])
            max_results: 최대 결과 수
        
        Returns:
            SECFiling 객체 리스트
        """
        try:
            # CIK를 10자리로 패딩
            cik_padded = cik.zfill(10)
            
            # SEC submissions API 사용
            url = f"{self.base_url}/submissions/CIK{cik_padded}.json"
            data = await self._make_request(url)
            
            if not data:
                logger.error(f"Failed to fetch filings for CIK: {cik}")
                return []
            
            filings = []
            recent_filings = data.get("filings", {}).get("recent", {})
            
            if not recent_filings:
                logger.warning(f"No recent filings found for CIK: {cik}")
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
            
            logger.info(f"Found {len(filings)} filings for {company_name}")
            return filings
            
        except Exception as e:
            logger.error(f"SEC filings fetch error: {e}")
            return []
    
    async def get_recent_filings(
        self,
        form_types: List[str] = ["10-K", "10-Q", "8-K"],
        max_results: int = 20
    ) -> List[SECFiling]:
        """
        최근 SEC 파일링 조회 (모든 회사)
        
        Args:
            form_types: 조회할 폼 타입 리스트
            max_results: 최대 결과 수
        
        Returns:
            SECFiling 객체 리스트
        """
        try:
            filings = []
            session = await self._get_session()
            
            for form_type in form_types:
                url = f"{self.base_url}/cgi-bin/browse-edgar"
                params = {
                    "action": "getcurrent",
                    "type": form_type,
                    "count": max_results // len(form_types),
                    "output": "atom"
                }
                
                # Rate limiting 적용
                await self.rate_limiter.acquire()
                
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
                    else:
                        logger.warning(f"Failed to fetch recent {form_type} filings: status {response.status}")
            
            return filings[:max_results]
            
        except Exception as e:
            logger.error(f"Recent filings error: {e}")
            return []
    
    async def search_filings(
        self,
        ticker: str,
        form_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[SECFiling]:
        """
        티커로 SEC 파일링 검색
        
        Args:
            ticker: 주식 티커 심볼
            form_types: 필터링할 폼 타입 리스트
            max_results: 최대 결과 수
        
        Returns:
            SECFiling 객체 리스트
        """
        # 먼저 CIK 조회
        cik = await self.get_company_cik(ticker)
        
        if not cik:
            logger.warning(f"Cannot search filings - CIK not found for ticker: {ticker}")
            return []
        
        # CIK로 파일링 조회
        return await self.get_company_filings(cik, form_types, max_results)
    
    async def get_filing_content(
        self, 
        filing_url: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        파일링 내용 다운로드
        
        Args:
            filing_url: 파일링 문서 URL
            max_retries: 최대 재시도 횟수
        
        Returns:
            파일링 내용 (HTML/텍스트) 또는 None
        """
        try:
            session = await self._get_session()
            
            for attempt in range(max_retries):
                try:
                    # Rate limiting 적용
                    await self.rate_limiter.acquire()
                    
                    async with session.get(filing_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            logger.info(f"Successfully downloaded filing content from {filing_url}")
                            return content
                        elif response.status == 403:
                            logger.error("Access forbidden (403). Check User-Agent configuration")
                            return None
                        elif response.status == 429:
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Failed to download filing: status {response.status}")
                            return None
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout downloading filing (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                    
        except Exception as e:
            logger.error(f"Filing content download error: {e}")
            return None
        
        return None

# 사용 예시 및 테스트 코드
async def test_edgar_connector():
    """EDGAR Connector 테스트 함수"""
    
    # 실제 사용 시 유효한 이메일로 변경 필요
    connector = EDGARConnector(user_email="your-email@example.com")
    
    try:
        # 1. CIK 조회 테스트
        print("Testing CIK lookup...")
        cik = await connector.get_company_cik("AAPL")
        if cik:
            print(f"✓ Apple CIK: {cik}")
        else:
            print("✗ Failed to get CIK for AAPL")
        
        # 2. 회사 파일링 조회 테스트
        if cik:
            print("\nTesting company filings...")
            filings = await connector.get_company_filings(
                cik=cik,
                form_types=["10-K", "10-Q"],
                max_results=5
            )
            print(f"✓ Found {len(filings)} filings")
            for filing in filings[:2]:  # 처음 2개만 출력
                print(f"  - {filing.form_type} on {filing.filing_date}")
        
        # 3. 최근 파일링 조회 테스트
        print("\nTesting recent filings...")
        recent = await connector.get_recent_filings(
            form_types=["8-K"],
            max_results=5
        )
        print(f"✓ Found {len(recent)} recent 8-K filings")
        
        # 4. Rate limiting 테스트 (빠른 연속 요청)
        print("\nTesting rate limiting with rapid requests...")
        tasks = []
        tickers = ["MSFT", "GOOGL", "AMZN", "META", "TSLA"]
        for ticker in tickers:
            tasks.append(connector.get_company_cik(ticker))
        
        results = await asyncio.gather(*tasks)
        successful = sum(1 for r in results if r is not None)
        print(f"✓ Successfully processed {successful}/{len(tickers)} tickers with rate limiting")
        
    finally:
        # 세션 정리
        await connector.close()
    
    print("\n✓ All tests completed!")

# 실행 시 테스트
if __name__ == "__main__":
    asyncio.run(test_edgar_connector())
# Global instance
edgar_connector = EDGARConnector(user_email="yhjun@seohancorp.com")
