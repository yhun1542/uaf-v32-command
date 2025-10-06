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
