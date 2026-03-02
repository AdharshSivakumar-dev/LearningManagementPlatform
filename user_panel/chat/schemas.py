from pydantic import BaseModel
from typing import List, Optional

class ChatRoomOut(BaseModel):
    id: int
    name: str
    room_type: str
    member_count: int

class CreateRoomRequest(BaseModel):
    name: str
    room_type: str = "group"
    member_ids: List[int] = []

class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    sender_username: str
    content: str
    message_type: str
    file_url: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    timestamp: str

class UploadResponse(BaseModel):
    file_url: str
    file_name: str
    file_type: str
    file_size: int

