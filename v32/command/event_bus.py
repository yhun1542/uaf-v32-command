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
