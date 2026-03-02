from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, status, Query
from django.utils import timezone as djtz
from django.conf import settings
from pathlib import Path
import uuid
import os
from asgiref.sync import sync_to_async

from lms.models import ChatRoom, Message, FileAttachment, LMSUser, Notification
from .schemas import ChatRoomOut, CreateRoomRequest, MessageOut, UploadResponse
from user_panel.deps import get_current_user
from user_panel.auth import decode_token
from .manager import manager
from user_panel.notifications.manager import manager as notif_manager

router = APIRouter(prefix="/chat", tags=["chat"])

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", settings.BASE_DIR / "media"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/rooms/", response_model=List[ChatRoomOut])
def list_rooms(user=Depends(get_current_user)):
    user_id, _ = user
    rooms = ChatRoom.objects.filter(members__id=user_id).distinct()
    return [ChatRoomOut(id=r.id, name=r.name, room_type=r.room_type, member_count=r.members.count()) for r in rooms]


@router.post("/rooms/", response_model=ChatRoomOut)
def create_room(payload: CreateRoomRequest, user=Depends(get_current_user)):
    user_id, _ = user
    creator = LMSUser.objects.get(pk=user_id)
    # Ensure name is unique or handle it? The model doesn't enforce unique name, but let's just create.
    # Actually, for private rooms, maybe we should check if one exists with same members?
    # For now, let's just create.
    room = ChatRoom.objects.create(name=payload.name, room_type=payload.room_type, created_by=creator)
    room.members.add(creator)
    if payload.member_ids:
        for mid in payload.member_ids:
            try:
                room.members.add(LMSUser.objects.get(pk=mid))
            except LMSUser.DoesNotExist:
                continue
    # Refetch to ensure count is correct?
    return ChatRoomOut(id=room.id, name=room.name, room_type=room.room_type, member_count=room.members.count())


@router.get("/rooms/{room_id}/messages/", response_model=List[MessageOut])
def room_messages(room_id: int, limit: int = Query(50, le=200), user=Depends(get_current_user)):
    user_id, _ = user
    if not ChatRoom.objects.filter(pk=room_id, members__id=user_id).exists():
        raise HTTPException(status_code=403, detail="Not a room member")
    msgs = Message.objects.filter(room_id=room_id).order_by("-timestamp")[:limit][::-1]
    return [
        MessageOut(
            id=m.id, room_id=room_id, sender_id=m.sender_id, sender_username=m.sender_username,
            content=m.content, message_type=m.message_type, file_url=m.file_url or None,
            file_name=m.file_name or None, file_type=m.file_type or None, timestamp=m.timestamp.isoformat()
        ) for m in msgs
    ]


@router.post("/rooms/{room_id}/join/")
def join_room(room_id: int, user=Depends(get_current_user)):
    user_id, _ = user
    try:
        room = ChatRoom.objects.get(pk=room_id)
    except ChatRoom.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")
    room.members.add(user_id)
    return {"status": "ok"}


@router.post("/upload/", response_model=UploadResponse)
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = file.file.read()
    size = len(data)
    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    date_folder = djtz.now().date().isoformat()
    folder = MEDIA_ROOT / "chat_files" / date_folder
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}_{file.filename}"
    path = folder / name
    with open(path, "wb") as f:
        f.write(data)
    rel = str(path.relative_to(MEDIA_ROOT)).replace("\\", "/")
    url = f"/media/{rel}"
    return UploadResponse(file_url=url, file_name=file.filename, file_type=file.content_type, file_size=size)


@router.get("/rooms/{room_id}/")
def room_detail(room_id: int, user=Depends(get_current_user)):
    user_id, _ = user
    try:
        r = ChatRoom.objects.get(pk=room_id)
    except ChatRoom.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"id": r.id, "name": r.name, "room_type": r.room_type, "member_count": r.members.count()}


@router.websocket("/ws/chat/{room_id}")
async def chat_ws(websocket: WebSocket, room_id: int, token: str):
    # Support "Bearer <token>" format in query param if sent that way, though usually just token
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    user_id = int(payload["sub"])
    
    # Helper for async DB calls
    def get_sender():
        return LMSUser.objects.get(pk=user_id)
    
    def create_message(**kwargs):
        return Message.objects.create(**kwargs)
        
    def get_room_members_ids(rid):
        try:
            r = ChatRoom.objects.get(pk=rid)
            return list(r.members.values_list('id', flat=True)), r.name
        except ChatRoom.DoesNotExist:
            return [], "Unknown"

    def create_notification(**kwargs):
        return Notification.objects.create(**kwargs)

    try:
        await manager.connect(websocket, room_id, user_id)
        
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type in ("typing", "stop_typing"):
                await manager.broadcast(room_id, {"event": msg_type, "user_id": user_id})
                continue
            
            if msg_type == "text":
                content = data.get("content", "")
                sender = await sync_to_async(get_sender)()
                
                m = await sync_to_async(create_message)(
                    room_id=room_id, sender=sender, sender_username=sender.name,
                    content=content, message_type="text"
                )
                
                await manager.broadcast(room_id, {
                    "event": "message",
                    "id": m.id,
                    "room_id": room_id,
                    "sender_id": user_id,
                    "sender_username": sender.name,
                    "content": content,
                    "message_type": "text",
                    "timestamp": m.timestamp.isoformat(),
                })
                
                # Notifications
                member_ids, room_name = await sync_to_async(get_room_members_ids)(room_id)
                msg_preview = content[:30] + "..." if len(content) > 30 else content
                notif_msg = f"New message from {sender.name} in {room_name}: {msg_preview}"
                
                for mid in member_ids:
                    if mid != user_id and not manager.is_user_connected(room_id, mid):
                        n = await sync_to_async(create_notification)(user_id=mid, message=notif_msg)
                        await notif_manager.send_notification(mid, {
                            "id": n.id,
                            "message": n.message,
                            "is_read": n.is_read,
                            "created_at": n.created_at.isoformat()
                        })

            elif msg_type == "file":
                sender = await sync_to_async(get_sender)()
                m = await sync_to_async(create_message)(
                    room_id=room_id, sender=sender, sender_username=sender.name,
                    content="", message_type="file",
                    file_url=data.get("file_url",""), file_name=data.get("file_name",""),
                    file_type=data.get("file_type","")
                )
                
                await manager.broadcast(room_id, {
                    "event": "message",
                    "id": m.id,
                    "room_id": room_id,
                    "sender_id": user_id,
                    "sender_username": sender.name,
                    "content": "",
                    "message_type": "file",
                    "file_url": m.file_url,
                    "file_name": m.file_name,
                    "file_type": m.file_type,
                    "timestamp": m.timestamp.isoformat(),
                })
                
                # Notifications for file
                member_ids, room_name = await sync_to_async(get_room_members_ids)(room_id)
                notif_msg = f"New file from {sender.name} in {room_name}"
                
                for mid in member_ids:
                    if mid != user_id and not manager.is_user_connected(room_id, mid):
                        n = await sync_to_async(create_notification)(user_id=mid, message=notif_msg)
                        await notif_manager.send_notification(mid, {
                            "id": n.id,
                            "message": n.message,
                            "is_read": n.is_read,
                            "created_at": n.created_at.isoformat()
                        })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, room_id, user_id)
