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
