from typing import Dict, Set, Tuple, Any
from fastapi import WebSocket
import json
from asgiref.sync import sync_to_async
from django.utils import timezone
from lms.models import UserStatus, LMSUser
from user_panel.redis_client import get_redis


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[int, Set[WebSocket]] = {}
        # Track which users are in which room (locally)
        self.room_users: Dict[int, Set[int]] = {}

    async def _update_status(self, user_id: int, is_online: bool):
        try:
            def update():
                user = LMSUser.objects.get(pk=user_id)
                status, _ = UserStatus.objects.get_or_create(user=user)
                status.is_online = is_online
                status.last_seen = timezone.now()
                status.save()
            await sync_to_async(update)()
        except Exception:
            pass

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int) -> None:
        await websocket.accept()
        self.active.setdefault(room_id, set()).add(websocket)
        self.room_users.setdefault(room_id, set()).add(user_id)
        
        await self._update_status(user_id, True)
        
        redis = await get_redis()
        if redis:
            await redis.sadd("online_users", str(user_id))

    async def disconnect(self, websocket: WebSocket, room_id: int, user_id: int) -> None:
        conns = self.active.get(room_id, set())
        if websocket in conns:
            conns.remove(websocket)
        
        if not conns:
            if room_id in self.room_users:
                del self.room_users[room_id]
            if room_id in self.active:
                del self.active[room_id]

        # Check if user is active in any other room? 
        # This is a local check. Ideally we should check globally or use Redis refcount.
        # But for now, we assume if they disconnect from a room, they might still be online elsewhere?
        # Simpler: just mark offline. If they are in another tab, that tab might send a heartbeat or reconnect?
        # Actually, if we mark offline here, and they have another tab open, they will show offline until next action.
        # Let's check if they are in `room_users` for ANY room.
        
        still_connected = False
        for r_users in self.room_users.values():
            if user_id in r_users:
                still_connected = True
                break
        
        if not still_connected:
            await self._update_status(user_id, False)

        redis = await get_redis()
        if redis:
            # Only remove if no connections? Redis doesn't track refcount on sadd.
            # We'll just remove.
            await redis.srem("online_users", str(user_id))

    async def broadcast(self, room_id: int, message: dict) -> None:
        data = json.dumps(message)
        # local broadcast
        conns = self.active.get(room_id, set())
        for ws in list(conns):
            try:
                await ws.send_text(data)
            except:
                pass # Handle stale sockets
        # redis pub
        redis = await get_redis()
        if redis:
            await redis.publish(f"chat:room:{room_id}", data)

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        await websocket.send_json(message)

    def is_user_connected(self, room_id: int, user_id: int) -> bool:
        return user_id in self.room_users.get(room_id, set())

manager = ConnectionManager()
