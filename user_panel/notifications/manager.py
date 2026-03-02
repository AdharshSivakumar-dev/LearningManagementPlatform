from typing import Dict, Set
from fastapi import WebSocket
import json
from user_panel.redis_client import get_redis


class NotificationManager:
    def __init__(self) -> None:
        # user_id -> set of websockets (user might be connected from multiple devices)
        self.active: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self.active.setdefault(user_id, set()).add(websocket)
        redis = await get_redis()
        if redis:
            # We might want to track online users for notifications too, but chat manager does that.
            pass

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self.active.get(user_id, set())
        if websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self.active[user_id]

    async def send_notification(self, user_id: int, message: dict) -> None:
        data = json.dumps(message)
        # local send
        conns = self.active.get(user_id, set())
        for ws in list(conns):
            await ws.send_text(data)
        
        # redis pub (for other instances)
        redis = await get_redis()
        if redis:
            await redis.publish(f"notifications:user:{user_id}", data)

manager = NotificationManager()
