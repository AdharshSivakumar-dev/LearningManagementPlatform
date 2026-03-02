from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from asgiref.sync import sync_to_async
from lms.models import Notification, LMSUser
from user_panel.deps import get_current_user
from user_panel.auth import decode_token
from user_panel.schemas import NotificationOut
from .manager import manager

router = APIRouter(prefix="/notifications", tags=["notifications-extended"])


@router.get("/", response_model=List[NotificationOut])
def list_notifications(user=Depends(get_current_user)):
    user_id, _ = user
    qs = Notification.objects.filter(user_id=user_id).order_by("-created_at")
    return [NotificationOut(id=n.id, message=n.message, is_read=n.is_read, created_at=n.created_at.isoformat()) for n in qs]


@router.patch("/{notif_id}/read/")
def mark_read(notif_id: int, user=Depends(get_current_user)):
    user_id, _ = user
    try:
        n = Notification.objects.get(pk=notif_id, user_id=user_id)
    except Notification.DoesNotExist:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    n.save()
    return {"status": "ok"}


@router.patch("/read-all/")
def read_all(user=Depends(get_current_user)):
    user_id, _ = user
    Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
    return {"status": "ok"}


@router.get("/unread-count/")
def unread_count(user=Depends(get_current_user)):
    user_id, _ = user
    c = Notification.objects.filter(user_id=user_id, is_read=False).count()
    return {"count": c}


@router.websocket("/ws/notifications/{user_id}")
async def notifications_ws(websocket: WebSocket, user_id: int, token: str):
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    # Verify the user_id matches the token (security check)
    token_user_id = int(payload["sub"])
    if token_user_id != user_id:
        await websocket.close(code=4003) # Forbidden
        return

    try:
        await manager.connect(websocket, user_id)
        while True:
            # Keep connection alive, maybe receive client acks if needed
            # For now, we just listen but client doesn't send much
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
