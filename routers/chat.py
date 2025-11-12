"""
Chat and messaging routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, async_session_maker
from models import Student, SwapRequest, ChatMessage
from schemas import ChatMessageResponse
from auth import get_current_user
from typing import List
import json

router = APIRouter(prefix="/chat", tags=["Chat"])


class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, student_id: int):
        await websocket.accept()
        self.active_connections[student_id] = websocket
    
    def disconnect(self, student_id: int):
        if student_id in self.active_connections:
            del self.active_connections[student_id]
    
    async def send_personal_message(self, message: dict, student_id: int):
        if student_id in self.active_connections:
            try:
                await self.active_connections[student_id].send_json(message)
            except Exception:
                # Connection broken, remove it
                self.disconnect(student_id)


manager = ConnectionManager()


@router.get("/messages/{swap_request_id}", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    swap_request_id: int,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all chat messages for a swap request
    
    Only accessible by requester or target of the swap
    """
    # Verify swap request exists and user is part of it
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == swap_request_id)
    )
    swap_request = result.scalar_one_or_none()
    
    if not swap_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap request not found"
        )
    
    if (swap_request.requester_id != current_user.id and 
        swap_request.target_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these messages"
        )
    
    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.swap_request_id == swap_request_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return messages


@router.websocket("/ws/{swap_request_id}")
async def websocket_chat(
    websocket: WebSocket,
    swap_request_id: int,
    token: str = Query(..., description="User email for authentication")
):
    """
    WebSocket endpoint for real-time chat
    
    Query params:
    - token: User's email address (for simple auth)
    
    Message format (JSON):
    {
        "message": "text content"
    }
    """
    async with async_session_maker() as db:
        try:
            # Authenticate user
            result = await db.execute(
                select(Student).where(Student.email == token)
            )
            student = result.scalar_one_or_none()
            
            if not student:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
            
            # Verify swap request exists and student is part of it
            result = await db.execute(
                select(SwapRequest).where(SwapRequest.id == swap_request_id)
            )
            swap_request = result.scalar_one_or_none()
            
            if not swap_request:
                await websocket.close(code=1008, reason="Swap request not found")
                return
            
            if (swap_request.requester_id != student.id and 
                swap_request.target_id != student.id):
                await websocket.close(code=1008, reason="Not authorized")
                return
            
            # Determine other party
            other_student_id = (
                swap_request.target_id 
                if swap_request.requester_id == student.id 
                else swap_request.requester_id
            )
            
            # Connect WebSocket
            await manager.connect(websocket, student.id)
            
            # Send connection confirmation
            await websocket.send_json({
                "type": "connected",
                "message": "Connected to chat"
            })
            
            # Listen for messages
            while True:
                # Receive message
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    message_text = message_data.get('message', '').strip()
                    
                    if not message_text:
                        continue
                    
                    # Save message to database
                    message = ChatMessage(
                        sender_id=student.id,
                        receiver_id=other_student_id,
                        swap_request_id=swap_request_id,
                        message=message_text
                    )
                    db.add(message)
                    await db.commit()
                    await db.refresh(message)
                    
                    # Prepare message payload
                    message_payload = {
                        "type": "message",
                        "id": message.id,
                        "sender_id": student.id,
                        "sender_name": f"{student.first_name} {student.last_name}",
                        "message": message_text,
                        "created_at": message.created_at.isoformat()
                    }
                    
                    # Send to sender (confirmation)
                    await websocket.send_json(message_payload)
                    
                    # Send to receiver if connected
                    await manager.send_personal_message(
                        message_payload,
                        other_student_id
                    )
                    
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid message format"
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error sending message: {str(e)}"
                    })
                    
        except WebSocketDisconnect:
            manager.disconnect(student.id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            try:
                await websocket.close(code=1011, reason=str(e))
            except:
                pass
            if student:
                manager.disconnect(student.id)