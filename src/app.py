from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from v32.core.redis_client import close_redis_pool, get_redis_client
from v32.command.routes import router as command_router
from v32.command.state_manager import StateManager
import redis.asyncio as redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("UAF V32 Starting...")
    # Initialize state in Redis upon startup
    try:
        client: redis.Redis = await get_redis_client()
        await StateManager.get_state(client) # Ensures the state is initialized if empty
        print("Redis connection and initial state verified.")
    except Exception as e:
        print(f"FATAL: Failed to connect to Redis. Is it running? Error: {e}")
        exit(1) # Exit if Redis is unavailable
    yield
    await close_redis_pool()
    print("UAF V32 Stopped.")

app = FastAPI(title="UAF V32 Command Hub", version="32.0.1", lifespan=lifespan)

# CORS Configuration (필수)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # !! 경고: 운영 환경에서는 보안을 위해 특정 도메인으로 제한해야 합니다 !!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(command_router, prefix="/v32/command", tags=["Command Hub"])

# Connector Routes
from v32.connectors.routes import router as connector_router
app.include_router(connector_router, prefix="/v32/connectors", tags=["Data Connectors"])

# Serve the Aegis V4 Dashboard (Frontend)
try:
    # Mounts the static files at the root URL (http://localhost:8000)
    app.mount("/", StaticFiles(directory="src/static", html=True), name="aegis_v4")
except RuntimeError:
    print("Warning: src/static directory not found. Aegis V4 Dashboard will not be served.")

@app.get("/health")
def health(): 
    return {"status": "ok", "version": "32.0.1", "component": "UAF V32 Core"}
