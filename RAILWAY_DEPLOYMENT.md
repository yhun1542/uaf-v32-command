# UAF V32 Command Hub - Railway Deployment Guide

## 🚀 Railway 배포 가이드

### 1. Railway 프로젝트 생성

1. [Railway](https://railway.app)에 로그인
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. `uaf-v32-command` 레포지토리 선택

### 2. Redis 추가

1. Railway 프로젝트 대시보드에서 "New" 클릭
2. "Database" → "Add Redis" 선택
3. Redis가 자동으로 프로비저닝됨

### 3. 환경 변수 설정

Railway 프로젝트 설정에서 다음 환경 변수를 추가:

```bash
# Redis (자동 생성됨)
REDIS_URL=${{Redis.REDIS_URL}}

# Command Hub Secret
COMMAND_HUB_SECRET=ac83802682295c9160964ad04b8472cd3528c6b82139ecfa6f76302c1fe33450

# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
XAI_API_KEY=your_xai_key
NEWS_API_KEY=your_news_api_key
```

### 4. 배포 설정

Railway는 자동으로 다음 파일들을 감지합니다:
- `requirements.txt`: Python 의존성
- `Procfile`: 시작 명령어
- `railway.json`: Railway 설정
- `runtime.txt`: Python 버전

### 5. 배포 실행

1. GitHub에 푸시하면 자동으로 배포됨
2. Railway 대시보드에서 배포 로그 확인
3. "Settings" → "Generate Domain"으로 공개 URL 생성

### 6. 헬스 체크

배포 후 다음 엔드포인트로 상태 확인:

```bash
curl https://your-app.railway.app/health
```

예상 응답:
```json
{
  "status": "ok",
  "version": "32.0.1",
  "component": "UAF V32 Core"
}
```

## 📡 API 엔드포인트

### Command Hub
- `GET /v32/command/stream` - SSE 스트림
- `GET /v32/command/state` - 현재 상태
- `POST /v32/command/task/{task_id}` - 작업 업데이트

### News Connector
- `GET /v32/connectors/news/search?query=AI` - 뉴스 검색
- `GET /v32/connectors/news/trending?category=technology` - 트렌딩 뉴스

### EDGAR Connector
- `GET /v32/connectors/edgar/company/AAPL` - 회사별 SEC 파일링
- `GET /v32/connectors/edgar/recent` - 최근 SEC 파일링

## 🔧 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# Redis 실행 (Docker)
docker run -d -p 6379:6379 redis:alpine

# 앱 실행
uvicorn src.app:app --reload --port 8000
```

## 📊 모니터링

Railway 대시보드에서 다음을 모니터링할 수 있습니다:
- CPU/메모리 사용량
- 배포 로그
- 애플리케이션 로그
- Redis 메트릭

## 🔐 보안

- 모든 API 키는 환경 변수로 관리
- CORS 설정은 프로덕션에서 특정 도메인으로 제한 권장
- Redis는 Railway 내부 네트워크로만 접근 가능

## 📝 주의사항

1. Railway 무료 티어는 월 $5 크레딧 제공
2. Redis는 별도 서비스로 실행되어 추가 비용 발생 가능
3. 슬립 모드 방지를 위해 헬스 체크 설정 권장

## 🆘 문제 해결

### Redis 연결 실패
```bash
# Railway 대시보드에서 Redis URL 확인
echo $REDIS_URL
```

### 배포 실패
1. Railway 로그 확인
2. `requirements.txt` 의존성 확인
3. Python 버전 호환성 확인 (`runtime.txt`)

### 포트 바인딩 오류
- Railway는 `$PORT` 환경 변수 사용
- `Procfile`에서 `--port $PORT` 필수

## 🔗 관련 링크

- [Railway 문서](https://docs.railway.app)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Redis 문서](https://redis.io/docs/)
