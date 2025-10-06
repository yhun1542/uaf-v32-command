# UAF v32 Initialization Script [Comprehensive v32.0.1]
# 이 스크립트는 UAF v32 코어 시스템 전체를 처음부터 설정합니다.

echo "Operation Singularity: UAF V32 코어 시스템 배치를 시작합니다..."

# === 1. 환경 준비 및 보안 설정 ===
echo "1. 보안 설정 구성 중..."
if [ ! -f .env ]; then
    echo "새로운 COMMAND_HUB_SECRET 생성 중..."
    # Python 또는 openssl을 사용하여 안전한 난수 생성 (Fallback 포함)
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || openssl rand -hex 32)
    
    if [ -z "$SECRET_KEY" ]; then
        echo "ERROR: 보안 키 생성 실패. Python 3 또는 openssl이 필요합니다."
        exit 1
    fi

    echo "COMMAND_HUB_SECRET=${SECRET_KEY}" > .env
    echo "REDIS_URL=redis://localhost:6379/0" >> .env
    echo "" >> .env
    echo "# === API Keys (2단계에서 입력 필요) ===" >> .env
    echo "OPENAI_API_KEY=" >> .env
    echo "ANTHROPIC_API_KEY=" >> .env
    echo "GOOGLE_API_KEY=" >> .env
    echo "XAI_API_KEY=" >> .env
    echo "NEWS_API_KEY=" >> .env
    echo ".env 파일 생성 완료."
else
    echo ".env 파일이 이미 존재합니다. 기존 설정을 사용합니다."
fi

# === 2. 디렉토리 구조 생성 ===
echo "2. 디렉토리 구조 생성 중..."
mkdir -p v32/command v32/config v32/core src/static

# === 3. UAF v32 백엔드 코드 배치 (Context Bridge 4.1.1 기반 강화) ===
echo "3. 백엔드 모듈 배치 중..."

# --- v32/config/settings.py (API 키 환경변수 추가 및 필수 Import 포함) ---
cat > v32/config/settings.py << 'PY'
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import RedisDsn, SecretStr, field_validator
# 중요: Optional Import 추가됨
from typing import Dict, Optional

# !!! CONFIGURATION LOCK !!! (모델 고정 지침 준수)
UAF_IMMUTABLE_MODELS: Dict[str, Dict[str, str]] = {
    'gpt-4o-2024-08-06': {'provider': 'OpenAI'},
    'claude-sonnet-4-5-20250929': {'provider': 'Anthropic'},
    'gemini-2.5-pro': {'provider': 'Google'},
    'grok-4-0709': {'provider': 'xAI'},
}

class Settings(BaseSettings):
    # Core Infrastructure
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    COMMAND_HUB_SECRET: SecretStr
    KV_STORE_KEY: str = 'operation_singularity:v32:master_plan_state'
    PUBSUB_CHANNEL: str = 'operation_singularity:v32:events'

    # API Keys for Chimera Protocol (자율 개발 에이전트용)
    OPENAI_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    GOOGLE_API_KEY: Optional[SecretStr] = None
    XAI_API_KEY: Optional[SecretStr] = None

    # API Keys for Data Connectors (데이터 수집용)
    NEWS_API_KEY: Optional[SecretStr] = None
    # (필요시 추가 데이터 소스 키 정의)

    @field_validator('COMMAND_HUB_SECRET')
    def validate_secret(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError("COMMAND_HUB_SECRET must be at least 32 characters long.")
        return v
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()
PY

# --- v32/core/redis_client.py ---
cat > v32/core/redis_client.py << 'PY'
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from v32.config.settings import settings

pool = ConnectionPool.from_url(
    str(settings.REDIS_URL),
    decode_responses=True,
    max_connections=25
)

async def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=pool)

async def close_redis_pool():
    if pool:
        await pool.disconnect()
PY

# --- v32/command/schemas.py ---
cat > v32/command/schemas.py << 'PY'
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class Task(BaseModel):
    id: str
    name: str
    progress: int = Field(0, ge=0, le=100)
    status: TaskStatus = TaskStatus.PENDING

class Phase(BaseModel):
    name: str
    tasks: List[Task]

class Project(BaseModel):
    name: str
    accent: str
    phases: Dict[str, Phase]

MasterPlan = Dict[str, Project]

class UpdateTaskInput(BaseModel):
    task_id: str
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[TaskStatus] = None

    @model_validator(mode='before')
    @classmethod
    def check_update_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get('progress') is None and values.get('status') is None:
                raise ValueError("Either progress or status must be provided.")
        return values
PY

# --- v32/command/initial_state.py ---
cat > v32/command/initial_state.py << 'PY'
from v32.command.schemas import MasterPlan, TaskStatus

INITIAL_STATE: MasterPlan = {
    "P1_INSIGHT_ENGINE": {
        "name": "P1: The Insight Engine (예측 코어)", "accent": "p1", "phases": {
            "PHASE_1_1": {"name": "1.1 Data Fusion Pipeline", "tasks": [
                {"id": "T1_1_L1_EDGAR", "name": "L1: EDGAR Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L1_NEWS", "name": "L1: NewsAPI Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L1_NASA", "name": "L1: NASA Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L2_PLANET", "name": "L2: Planet Labs (Procurement)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_FUSION_ENGINE", "name": "OASIS-Lumio Fusion Engine", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_1_2": {"name": "1.2 Causal & Predictive Modeling", "tasks": [
                {"id": "T1_2_TCI", "name": "EmarkOS TCI Module", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_2_NDDE_PINN", "name": "NDDE/PINN Models", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_2_BACKTESTING", "name": "Backtesting Framework", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    },
    "P2_ALPHA_ONE": {
        "name": "P2: Alpha One (투자 집행 플랫폼)", "accent": "p2", "phases": {
            "PHASE_2_1": {"name": "2.1 C&C Dashboard", "tasks": [
                {"id": "T2_1_VISUALIZATION", "name": "LuminEX Real-time Visualization", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_1_TRADE_UI", "name": "Trade Proposal UI/UX", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_1_PNL_TRACKING", "name": "Real-time PnL Tracking", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_2_2": {"name": "2.2 Trade Execution Engine", "tasks": [
                {"id": "T2_2_BROKER_API", "name": "Global Broker API (IBKR)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_AUTO_AGENT", "name": "Chimera Z+ Trading Agent", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_CDT_VETO", "name": "Project Bank CDT (Veto)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_CCR_LOGGING", "name": "EmarkOS CCR (Logging)", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    },
    "P3_A2AAS": {
        "name": "P3: A²aaS (자율 개발 플랫폼)", "accent": "p3", "phases": {
            "PHASE_3_1": {"name": "3.1 Platform APIization", "tasks": [
                {"id": "T3_1_TDD_API", "name": "Chimera Z+ TDD Engine API", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_1_ORCHESTRATION_API", "name": "UAF v32 Orchestration API", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_3_2": {"name": "3.2 Project Genesis (No-Code)", "tasks": [
                {"id": "T3_2_BUILDER_UI", "name": "No-Code Builder UI/UX", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_2_BACKEND_INTEGRATION", "name": "Backend Integration", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_2_MARKETPLACE", "name": "AI Agent Marketplace", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    }
}
PY

# --- v32/command/state_manager.py (상태 관리 및 동시성 제어 강화) ---
cat > v32/command/state_manager.py << 'PY'
import json
from typing import Optional
import redis.asyncio as redis
from redis.exceptions import WatchError
from v32.config.settings import settings
from v32.command.schemas import MasterPlan, TaskStatus
from v32.command.initial_state import INITIAL_STATE

class StateManager:
    @staticmethod
    async def get_state(client: redis.Redis) -> MasterPlan:
        state_json = await client.get(settings.KV_STORE_KEY)
        if not state_json:
            # Initialize state if it doesn't exist
            await StateManager.reset_state(client)
            return INITIAL_STATE
        try:
            return json.loads(state_json)
        except json.JSONDecodeError:
            # Handle corrupted state
            await StateManager.reset_state(client)
            return INITIAL_STATE

    @staticmethod
    async def reset_state(client: redis.Redis):
        await client.set(settings.KV_STORE_KEY, json.dumps(INITIAL_STATE))

    @staticmethod
    async def update_task(client: redis.Redis, task_id: str, progress: Optional[int], status: Optional[TaskStatus]) -> dict:
        async with client.pipeline() as pipe:
            for attempt in range(5): # Optimistic locking with retries
                try:
                    await pipe.watch(settings.KV_STORE_KEY)
                    current_state_json = await pipe.get(settings.KV_STORE_KEY)
                    current_state = json.loads(current_state_json or json.dumps(INITIAL_STATE))
                    
                    updated_task = None
                    # Deep search for the task
                    for p_key, project in current_state.items():
                        for ph_key, phase in project['phases'].items():
                            for task in phase['tasks']:
                                if task['id'] == task_id:
                                    # Apply updates
                                    if progress is not None: task['progress'] = max(0, min(100, progress))
                                    if status is not None: task['status'] = status.value
                                    
                                    # Auto-adjust status based on progress, unless explicitly BLOCKED
                                    current_status = task['status']
                                    if current_status != TaskStatus.BLOCKED.value:
                                        if task['progress'] == 100:
                                            task['status'] = TaskStatus.COMPLETED.value
                                        elif task['progress'] > 0:
                                            task['status'] = TaskStatus.IN_PROGRESS.value
                                        # Keep PENDING if progress is 0 and status wasn't already IN_PROGRESS
                                        elif task['progress'] == 0 and current_status != TaskStatus.IN_PROGRESS.value:
                                             task['status'] = TaskStatus.PENDING.value

                                    updated_task = task
                                    break
                            if updated_task: break
                        if updated_task: break
                    
                    if not updated_task:
                        return {"success": False, "message": f"Task {task_id} not found."}
                    
                    # Execute transaction
                    pipe.multi()
                    pipe.set(settings.KV_STORE_KEY, json.dumps(current_state))
                    await pipe.execute()
                    return {"success": True, "updated_task": updated_task}
                
                except WatchError:
                    continue # State changed, retry
                except Exception as e:
                    return {"success": False, "message": f"An unexpected error occurred: {str(e)}"}
            
            return {"success": False, "message": "High contention: Failed to update task after multiple attempts."}
PY

# --- v32/command/event_bus.py (이벤트 버스 안정성 강화) ---
cat > v32/command/event_bus.py << 'PY'
import json
import asyncio
from typing import AsyncGenerator
from v32.config.settings import settings
from v32.core.redis_client import get_redis_client

class EventBus:
    @staticmethod
    async def publish_update(payload: dict):
        client = await get_redis_client()
        message = json.dumps({"type": "TASK_UPDATE", "payload": payload})
        try:
            await client.publish(settings.PUBSUB_CHANNEL, message)
        except Exception as e:
            print(f"Warning: Failed to publish update to Redis: {e}")

    @staticmethod
    async def subscribe_to_updates() -> AsyncGenerator[dict, None]:
        client = await get_redis_client()
        pubsub = client.pubsub()
        
        async def subscribe():
            try:
                await pubsub.subscribe(settings.PUBSUB_CHANNEL)
                return True
            except Exception:
                await asyncio.sleep(5)
                return False

        # Attempt connection twice
        if not await subscribe() and not await subscribe():
             raise ConnectionError("Cannot establish connection to Redis Pub/Sub.")

        try:
            while True:
                try:
                    # 15s timeout for heartbeat
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                    if message and message.get('type') == 'message':
                        data = json.loads(message['data'])
                        if data.get('type') == 'TASK_UPDATE':
                            yield data['payload']
                    else:
                        yield {"event": "HEARTBEAT"}
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Handle connection drop and attempt reconnection
                    print(f"Warning: Redis connection lost: {e}. Attempting to reconnect...")
                    if not await subscribe():
                        await asyncio.sleep(5)
                        if not await subscribe():
                             raise ConnectionError("Failed to reconnect to Redis Pub/Sub.")
        finally:
            try:
                await pubsub.unsubscribe(settings.PUBSUB_CHANNEL)
            except Exception:
                pass
PY

# --- v32/command/routes.py ---
cat > v32/command/routes.py << 'PY'
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis
from v32.core.redis_client import get_redis_client
from v32.config.settings import settings
from v32.command.state_manager import StateManager
from v32.command.event_bus import EventBus
from v32.command.schemas import UpdateTaskInput, MasterPlan

router = APIRouter()
security = HTTPBearer()

async def auth(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.scheme != "Bearer" or credentials.credentials != settings.COMMAND_HUB_SECRET.get_secret_value():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True

@router.post("/update-task", dependencies=[Depends(auth)], status_code=status.HTTP_200_OK)
async def update_task_route(payload: UpdateTaskInput, client: redis.Redis = Depends(get_redis_client)):
    result = await StateManager.update_task(client, payload.task_id, payload.progress, payload.status)
    
    if not result["success"]:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in result["message"] else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    await EventBus.publish_update(result["updated_task"])
    return {"message": "Update acknowledged and processed", "data": result["updated_task"]}

@router.get("/state", response_model=MasterPlan)
async def get_current_state_route(client: redis.Redis = Depends(get_redis_client)):
    return await StateManager.get_state(client)

@router.get("/stream")
async def stream_updates_route(request: Request, client: redis.Redis = Depends(get_redis_client)):
    async def event_generator():
        # Send initial state
        try:
            initial_state = await StateManager.get_state(client)
            yield {"event": "INITIAL_STATE", "data": json.dumps(initial_state)}
        except Exception as e:
            yield {"event": "ERROR", "data": json.dumps({"message": f"Failed to fetch initial state: {e}"})}
            return

        # Subscribe to updates
        try:
            async for payload in EventBus.subscribe_to_updates():
                if await request.is_disconnected():
                    break
                
                if payload.get("event") == "HEARTBEAT":
                    yield {"event": "HEARTBEAT", "data": "ping"}
                else:
                    yield {"event": "TASK_UPDATE", "data": json.dumps(payload)}
        except ConnectionError as e:
             yield {"event": "ERROR", "data": json.dumps({"message": str(e)})}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
PY

# --- src/app.py (Entry Point 및 프론트엔드 서버 통합) ---
cat > src/app.py << 'PY'
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

# Serve the Aegis V4 Dashboard (Frontend)
try:
    # Mounts the static files at the root URL (http://localhost:8000)
    app.mount("/", StaticFiles(directory="src/static", html=True), name="aegis_v4")
except RuntimeError:
    print("Warning: src/static directory not found. Aegis V4 Dashboard will not be served.")

@app.get("/health")
def health(): 
    return {"status": "ok", "version": "32.0.1", "component": "UAF V32 Core"}
PY

# === 4. Aegis V4 대시보드 배치 (Context Bridge 4.1.2 기반 UI/UX 강화) ===
echo "4. Aegis V4 대시보드 배치 중..."
cat > src/static/index.html << 'HTML'
<!DOCTYPE html><html lang="ko"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aegis V4 - UAF v32 Command Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root { --font-sans: 'Noto Sans KR', sans-serif; --bg-main: #0a0a0a; --bg-card: #141414; --border-color: #2a2a2a; --text-main: #f5f5f5; --text-muted: #a3a3a3; }
        body { font-family: var(--font-sans); background-color: var(--bg-main); color: var(--text-main); }
        .progress-bar>div { transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        .task-item { animation: fadeIn 0.3s ease-out; }
    </style></head><body class="p-4 sm:p-6 lg:p-8">
    <div class="max-w-7xl mx-auto">
        <header class="flex justify-between items-center mb-8 pb-4 border-b border-border-color">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-green-500">Operation Singularity</h1>
                <p class="text-base text-text-muted">UAF v32 통합 작전 현황 (Aegis V4)</p>
            </div>
            <div id="connection-status" class="flex items-center gap-3 px-4 py-2 rounded-lg bg-red-900/50 text-red-400 text-sm font-medium shadow-md border border-red-700">
                <i data-lucide="wifi-off" class="w-4 h-4"></i>
                <span>DISCONNECTED</span>
            </div>
        </header>
        <main id="dashboard-grid" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div id="loading-placeholder" class="col-span-1 lg:col-span-3 flex justify-center items-center h-64">
                <div class="text-center">
                    <i data-lucide="loader-2" class="w-12 h-12 animate-spin text-blue-500 mb-4 mx-auto"></i>
                    <p class="text-text-muted">지휘소 연결 대기 중...</p>
                </div>
            </div>
        </main>
    </div><script>
    let MASTER_PLAN = {};
    let retryInterval = 2000;

    const ICONS = {
        PENDING: 'clock', IN_PROGRESS: 'activity', COMPLETED: 'check-square', BLOCKED: 'alert-triangle'
    };
    const STATUS_COLORS = {
        PENDING: 'text-gray-500', IN_PROGRESS: 'text-blue-400', COMPLETED: 'text-green-400', BLOCKED: 'text-yellow-500'
    };
    const ACCENT_MAP = {
        p1: { base: 'blue', gradient: 'from-blue-500/20 to-blue-700/20' },
        p2: { base: 'green', gradient: 'from-green-500/20 to-green-700/20' },
        p3: { base: 'orange', gradient: 'from-orange-500/20 to-orange-700/20' }
    };

    function Task({ id, name, progress, status }, accent) {
        const colors = STATUS_COLORS[status];
        const icon = ICONS[status];
        const progressColor = `bg-${ACCENT_MAP[accent].base}-500`;

        return `
        <div id="${id}" class="task-item py-3 border-b border-gray-800 last:border-b-0">
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-3 text-sm font-medium">
                    <i data-lucide="${icon}" class="w-4 h-4 ${colors} ${status === 'IN_PROGRESS' ? 'animate-pulse' : ''}"></i>
                    <span class="text-text-main">${name}</span>
                </div>
                <span class="text-xs font-mono font-semibold ${colors}">${progress}%</span>
            </div>
            <div class="w-full bg-gray-800 rounded-full h-2 overflow-hidden progress-bar">
                <div class="${progressColor} h-2 rounded-full" style="width: ${progress}%"></div>
            </div>
        </div>`;
    }

    function Phase({ name, tasks }, accent) {
        return `<div class="mb-6">
            <h4 class="font-semibold text-text-muted text-sm uppercase tracking-wider mb-3">${name}</h4>
            <div>${tasks.map(t => Task(t, accent)).join('')}</div>
        </div>`;
    }
    
    function Project({ name, accent, phases }) {
        const { base, gradient } = ACCENT_MAP[accent];
        
        return `
        <div class="bg-bg-card border border-gray-800 rounded-xl shadow-xl overflow-hidden transition duration-300 hover:shadow-2xl hover:border-${base}-500">
            <div class="p-6 bg-gradient-to-b ${gradient} border-b border-gray-800">
                <h3 class="text-xl font-bold text-white">${name}</h3>
            </div>
            <div class="p-6">
                ${Object.values(phases).map(p => Phase(p, accent)).join('')}
            </div>
        </div>`;
    }

    function renderDashboard() {
        const grid = document.getElementById('dashboard-grid');
        if (Object.keys(MASTER_PLAN).length > 0) {
             document.getElementById('loading-placeholder')?.remove();
             grid.innerHTML = Object.values(MASTER_PLAN).map(Project).join('');
        }
        lucide.createIcons();
    }

    function updateLocalState(task) {
        for (const project of Object.values(MASTER_PLAN)) {
            for (const phase of Object.values(project.phases)) {
                const index = phase.tasks.findIndex(t => t.id === task.id);
                if (index !== -1) {
                    phase.tasks[index] = task;
                    return project.accent;
                }
            }
        }
        return null;
    }

    function handleTaskUpdate(task) {
        const accent = updateLocalState(task);
        if (!accent) return;

        const el = document.getElementById(task.id);
        if (!el) { renderDashboard(); return; }

        const newHTML = Task(task, accent);
        const template = document.createElement('template');
        template.innerHTML = newHTML.trim();
        const newNode = template.content.firstChild;

        el.replaceWith(newNode);
        // Re-initialize icon for the new node
        lucide.createIcons({ nodes: [newNode.querySelector('i')] });
    }

    function updateConnectionStatus(isConnected, error = null) {
        const statusEl = document.getElementById('connection-status');
        if (isConnected) {
            statusEl.className = 'flex items-center gap-3 px-4 py-2 rounded-lg bg-green-900/50 text-green-400 text-sm font-medium shadow-md border border-green-700';
            statusEl.innerHTML = `<i data-lucide="radio" class="w-4 h-4 animate-pulse"></i><span>LIVE</span>`;
            retryInterval = 2000; // Reset retry interval on success
        } else {
            statusEl.className = 'flex items-center gap-3 px-4 py-2 rounded-lg bg-red-900/50 text-red-400 text-sm font-medium shadow-md border border-red-700';
            statusEl.innerHTML = `<i data-lucide="wifi-off" class="w-4 h-4"></i><span>DISCONNECTED</span>`;
        }
        lucide.createIcons({ nodes: [statusEl.querySelector('i')] });
    }

    let eventSource = null;

    function connectToStream() {
        if (eventSource) { eventSource.close(); }
        
        console.log("Connecting to UAF v32 Command Stream...");
        // Stream URL is relative since backend serves the frontend
        eventSource = new EventSource('/v32/command/stream');

        eventSource.onopen = () => { updateConnectionStatus(true); };

        eventSource.onerror = (e) => {
            console.error("EventSource failed:", e);
            updateConnectionStatus(false);
            eventSource.close();
            
            // Exponential backoff reconnection
            retryInterval = Math.min(retryInterval * 1.5, 30000);
            setTimeout(connectToStream, retryInterval);
        };

        eventSource.addEventListener('INITIAL_STATE', e => {
            try {
                MASTER_PLAN = JSON.parse(e.data);
                renderDashboard();
            } catch (err) {
                console.error("Error parsing INITIAL_STATE:", err);
            }
        });

        eventSource.addEventListener('TASK_UPDATE', e => {
            try {
                handleTaskUpdate(JSON.parse(e.data));
            } catch (err) {
                console.error("Error parsing TASK_UPDATE:", err);
            }
        });

        eventSource.addEventListener('HEARTBEAT', () => {});

         eventSource.addEventListener('ERROR', e => {
            console.error("Server error:", JSON.parse(e.data));
            updateConnectionStatus(false, JSON.parse(e.data).message);
        });
    }
    
    document.addEventListener('DOMContentLoaded', () => {
        lucide.createIcons(); // Initialize icons (like the loading spinner)
        connectToStream();
    });</script></body></html>
HTML

# === 5. 종속성 설치 및 실행 안내 ===
echo "5. 필수 Python 패키지 설치 중..."
# 시스템 환경에 따라 pip 대신 pip3를 사용해야 할 수도 있습니다.
pip install fastapi uvicorn "redis[hiredis]" pydantic-settings sse-starlette python-dotenv "pydantic[email]"

echo ""
echo "UAF V32 코어 시스템 배치 완료."
echo "========================================================================"
echo " [중요] 서버 실행 전 필수 확인 사항:"
echo " 1. Redis 서버가 실행 중이어야 합니다 (기본값: localhost:6379)."
echo "    (실행 예시: docker run -d --name uaf-redis -p 6379:6379 redis)"
echo ""
echo " 2. .env 파일을 열어 2단계에서 요청할 API 키를 입력해야 합니다."
echo ""
echo " 3. UAF V32 서버 실행 명령어 (터미널에서 실행):"
echo "    uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo " 4. Aegis V4 대시보드 접속 주소 (웹 브라우저):"
echo "    http://localhost:8000 (또는 서버의 IP 주소)"
echo "========================================================================"