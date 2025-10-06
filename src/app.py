from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from v32.core.redis_client import close_redis_pool, get_redis_client
from v32.command.routes import router as command_router
from v32.data.routes import router as data_router
from v32.command.state_manager import StateManager
import redis.asyncio as redis
import os
import asyncio

# 커넥터 Import
from v32.connectors.edgar_connector import edgar_connector
from v32.connectors.dart_connector import dart_connector

# 초기화 상태 추적
initialization_status = {
    "edgar": {"status": "not_started", "details": {}},
    "dart": {"status": "not_started", "details": {}}
}

async def initialize_dart_background():
    """DART CORPCODE를 백그라운드에서 초기화"""
    global initialization_status
    try:
        initialization_status["dart"]["status"] = "initializing"
        print("📋 DART initialization started in background...")
        await dart_connector.initialize_corp_codes()
        initialization_status["dart"]["status"] = "ready"
        initialization_status["dart"]["details"] = {
            "companies_loaded": len(dart_connector._corp_map_by_code)
        }
        print(f"✅ DART CORPCODE initialization complete! ({len(dart_connector._corp_map_by_code)} companies)")
    except Exception as e:
        initialization_status["dart"]["status"] = "failed"
        initialization_status["dart"]["details"] = {"error": str(e)}
        print(f"❌ DART initialization failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("🚀 UAF V32 Command Hub Starting...")
    print("=" * 50)
    
    # 1. Redis 연결 및 상태 확인 (필수)
    try:
        client: redis.Redis = await get_redis_client()
        await StateManager.get_state(client)
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ FATAL: Core infrastructure failure (Redis/Config). Error: {e}")
        exit(1)
        
    # 2. 데이터 커넥터 초기화
    print("📡 Initializing data connectors...")
    
    # EDGAR는 즉시 초기화 (빠름)
    try:
        initialization_status["edgar"]["status"] = "ready"
        initialization_status["edgar"]["details"] = {
            "rate_limiting": "enabled (10 req/sec)"
        }
        print("✅ EDGAR connector initialized")
    except Exception as e:
        initialization_status["edgar"]["status"] = "failed"
        print(f"⚠️  EDGAR initialization warning: {e}")
    
    # DART는 백그라운드에서 초기화 (느림 - 30-60초)
    asyncio.create_task(initialize_dart_background())
    
    print("💡 API is ready to use! DART features will be available soon...")
    print("=" * 50)
    print("✨ UAF V32 Command Hub is ready!")
    print(f"📍 Access the API at: http://0.0.0.0:8000")
    print(f"📚 Documentation: http://0.0.0.0:8000/docs")
    print("=" * 50)
    
    yield
    
    await close_redis_pool()
    print("🛑 UAF V32 Stopped.")

app = FastAPI(title="UAF V32 Command Hub", version="32.1.2", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(command_router, prefix="/v32/command", tags=["Command Hub"])
app.include_router(data_router, prefix="/v32/data", tags=["P1 Data Connectors"])

# 초기화 상태 확인 엔드포인트
@app.get("/v32/connectors/initialization-status")
def get_initialization_status():
    """데이터 커넥터 초기화 상태 확인"""
    return {"connectors": initialization_status}

# Health Check
@app.get("/health")
def health():
    return {"status": "ok", "version": "32.1.2", "component": "UAF V32 Core"}

# Serve the Aegis V4 Dashboard
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="aegis_v4")
else:
    print("⚠️  Warning: src/static directory not found.")
