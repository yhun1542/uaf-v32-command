import httpx
import asyncio
import zipfile
import io
from typing import List, Dict, Optional, Any, Tuple
from lxml import etree # 고성능 XML 파서
from datetime import datetime
from v32.config.settings import settings
from v32.data.schemas import DartCompany, DartFiling, DartFilingSearchInput, DartFinancialStatement, DartFinancialSearchInput, FSType

class DartAPIException(Exception):
    """Custom exception for DART API errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"DART API Error [{code}]: {message}")

class DartConnector:
    def __init__(self):
        self.api_key = settings.DART_API_KEY.get_secret_value() if settings.DART_API_KEY else None
        self.base_url = "https://opendart.fss.or.kr/api/"
        self.timeout = httpx.Timeout(30.0)
        self.headers = {"User-Agent": settings.USER_AGENT}
        # CORPCODE 맵 (인메모리 캐시)
        self._corp_map_by_code: Dict[str, DartCompany] = {}
        # 식별자 맵: {stock_code/corp_name: corp_code}
        self._identifier_map: Dict[str, str] = {}

    async def _request(self, endpoint: str, params: Dict[str, Any], return_type: str = 'json') -> Any:
        if not self.api_key:
            raise DartAPIException("000", "DART_API_KEY is not configured in .env.")
        
        params['crtfc_key'] = self.api_key
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                if return_type == 'binary':
                    return response.content
                
                # DART API는 성공 시에도 status 필드를 포함한 JSON을 반환합니다.
                data = response.json()
                status = data.get('status')
                message = data.get('message')

                # API 응답 상태 코드 검증
                if status != '000': # 000: 정상
                    # 013: 조회된 데이터 없음 (오류가 아님)
                    if status == '013': return None
                    raise DartAPIException(status, message)
                
                return data

            except httpx.HTTPStatusError as e:
                raise DartAPIException("HTTP", f"HTTP request failed: {e}")
            except Exception as e:
                if isinstance(e, DartAPIException): raise e
                raise DartAPIException("UNKNOWN", f"An unexpected error occurred: {e}")

    async def initialize_corp_codes(self):
        """Downloads and parses CORPCODE.xml from DART."""
        if self._corp_map_by_code: return

        print("Downloading DART CORPCODE.xml...")
        try:
            # 1. Download ZIP file (corpCode.xml 엔드포인트는 실제로는 ZIP을 반환)
            zip_data = await self._request("corpCode.xml", {}, return_type='binary')
            
            # 2. Extract XML from ZIP in memory & Parse (CPU-bound task)
            # ZIP 처리 및 XML 파싱은 CPU 바운드 작업이므로, 이벤트 루프를 블록하지 않도록 스레드 풀에서 실행합니다.
            def process_zip_and_parse():
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    xml_data = zf.read("CORPCODE.xml")
                
                # 3. Parse XML using lxml (Handles encoding robustly)
                tree = etree.fromstring(xml_data)
                
                temp_corp_map = {}
                temp_identifier_map = {}

                for element in tree.findall('list'):
                    corp_code = element.findtext('corp_code')
                    corp_name = element.findtext('corp_name')
                    stock_code = element.findtext('stock_code', '').strip()
                    modify_date_str = element.findtext('modify_date')

                    try:
                        modify_date = datetime.strptime(modify_date_str, '%Y%m%d').date() if modify_date_str else None
                        company = DartCompany(
                            corp_code=corp_code,
                            corp_name=corp_name,
                            stock_code=stock_code if stock_code else None,
                            modify_date=modify_date
                        )
                        temp_corp_map[corp_code] = company
                        
                        # 식별자 매핑 추가 (대소문자 구분 없이 처리)
                        temp_identifier_map[corp_name.upper()] = corp_code
                        if stock_code:
                            temp_identifier_map[stock_code] = corp_code

                    except Exception as e:
                        print(f"Warning: Failed to parse company {corp_name}: {e}")
                return temp_corp_map, temp_identifier_map

            # Run the blocking/CPU-bound task in a separate thread (Python 3.9+)
            self._corp_map_by_code, self._identifier_map = await asyncio.to_thread(process_zip_and_parse)
            print(f"DART CORPCODE Map loaded ({len(self._corp_map_by_code)} companies).")

        except Exception as e:
            print(f"FATAL: Failed to load DART CORPCODE Map: {e}")
            # CORPCODE 로드 실패는 치명적이므로 예외를 발생시킵니다.
            raise e

    async def get_corp_code(self, identifier: str) -> str:
        """Resolves a company name or stock code to a DART corp_code."""
        await self.initialize_corp_codes()
        
        # 1. 정확한 일치 (이름 또는 코드)
        corp_code = self._identifier_map.get(identifier.upper())
        if corp_code:
             return corp_code

        # 2. 부분 일치 검색 (최후의 수단, 정확성 문제 발생 가능성 경고)
        # DART는 정확한 이름을 요구하는 경우가 많아, 부분 일치는 신중해야 합니다.
        # for name, code in self._identifier_map.items():
        #     if identifier.upper() in name:
        #         print(f"DART: Resolved partial match '{identifier}' to '{name}'. Use exact name for accuracy.")
        #         return code
        
        raise ValueError(f"Company not found for identifier: {identifier}. (DART requires exact name or stock code)")

    async def search_filings(self, input: DartFilingSearchInput) -> List[DartFiling]:
        """Searches for filings based on company and date range."""
        corp_code = await self.get_corp_code(input.identifier)
        
        params = {
            'corp_code': corp_code,
            'bgn_de': input.start_date.strftime('%Y%m%d'),
            'end_de': input.end_date.strftime('%Y%m%d'),
            'pblntf_ty': input.pblntf_ty,
            'page_no': input.page_no,
            'page_count': input.page_count
        }
        
        data = await self._request("list.json", params)
        if not data or 'list' not in data: return []

        filings = []
        for item in data['list']:
            try:
                filings.append(DartFiling(
                    corp_code=item.get('corp_code'),
                    corp_name=item.get('corp_name'),
                    stock_code=item.get('stock_code').strip() if item.get('stock_code') else None,
                    corp_cls=item.get('corp_cls'),
                    report_nm=item.get('report_nm'),
                    rcept_no=item.get('rcept_no'),
                    flr_nm=item.get('flr_nm'),
                    rcept_dt=datetime.strptime(item.get('rcept_dt'), '%Y%m%d').date(),
                    rm=item.get('rm')
                ))
            except Exception as e:
                print(f"Warning: Failed to parse filing {item.get('rcept_no')}: {e}")
        
        # TODO: Handle pagination if total_page > page_no
        return filings

    async def get_financial_statements(self, input: DartFinancialSearchInput) -> List[DartFinancialStatement]:
        """Fetches standardized financial statements (단일회사 전체 재무제표). Auto-handles CFS/OFS fallback."""
        corp_code = await self.get_corp_code(input.identifier)

        params = {
            'corp_code': corp_code,
            'bsns_year': input.bsns_year,
            'reprt_code': input.reprt_code,
            'fs_div': input.fs_type.value
        }

        # API endpoint: fnlttSinglAcntAll.json (전체 재무제표)
        data = await self._request("fnlttSinglAcntAll.json", params)
        
        actual_fs_type = input.fs_type

        # 연결(CFS) 요청 시 데이터가 없고, 별도(OFS)가 있는지 자동 확인 (Fallback 메커니즘)
        if not data and input.fs_type == FSType.CFS:
            print(f"DART: No CFS data found for {input.identifier} ({input.bsns_year}). Attempting OFS fallback.")
            params['fs_div'] = FSType.OFS.value
            data = await self._request("fnlttSinglAcntAll.json", params)
            actual_fs_type = FSType.OFS

        if not data or 'list' not in data: return []

        statements = []
        # 금액 데이터는 문자열이며 콤마(,)가 포함될 수 있으므로 float로 변환하는 헬퍼 함수
        def parse_amount(amount_str: Optional[str]) -> Optional[float]:
            if amount_str is None or amount_str.strip() == '-': return None
            try:
                return float(amount_str.replace(',', ''))
            except ValueError:
                return None

        for item in data['list']:
            try:
                # API 응답의 fs_div 사용 (요청과 다를 수 있음)
                response_fs_div = item.get('fs_div')
                # 응답 값이 유효한 FSType인지 확인, 아니면 실제 사용된 타입(actual_fs_type) 사용
                try:
                    fs_div_enum = FSType(response_fs_div)
                except ValueError:
                    fs_div_enum = actual_fs_type

                statements.append(DartFinancialStatement(
                    rcept_no=item.get('rcept_no'),
                    bsns_year=item.get('bsns_year'),
                    corp_code=item.get('corp_code'),
                    stock_code=item.get('stock_code').strip() if item.get('stock_code') else None,
                    fs_div=fs_div_enum,
                    fs_nm=item.get('fs_nm'),
                    sj_div=item.get('sj_div'),
                    sj_nm=item.get('sj_nm'),
                    account_id=item.get('account_id'),
                    account_nm=item.get('account_nm'),
                    thstrm_nm=item.get('thstrm_nm'),
                    thstrm_amount=parse_amount(item.get('thstrm_amount')),
                    frmtrm_nm=item.get('frmtrm_nm'),
                    frmtrm_amount=parse_amount(item.get('frmtrm_amount')),
                    bfefrmtrm_nm=item.get('bfefrmtrm_nm'),
                    bfefrmtrm_amount=parse_amount(item.get('bfefrmtrm_amount'))
                ))
            except Exception as e:
                print(f"Warning: Failed to parse financial statement item for {corp_code} ({input.bsns_year}): {e}. Data: {item}")
        
        return statements

# Singleton instance
dart_connector = DartConnector()
