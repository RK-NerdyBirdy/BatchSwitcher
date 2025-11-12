"""
Database models for the Batch Swap Platform
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class BatchEnum(str, enum.Enum):
    FORENOON = "Forenoon"
    EVENING_1 = "Evening 1"
    EVENING_2 = "Evening 2"


class SwapRequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)
    current_batch = Column(Enum(BatchEnum), nullable=False)
    original_batch = Column(Enum(BatchEnum), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sent_requests = relationship(
        "SwapRequest",
        foreign_keys="SwapRequest.requester_id",
        back_populates="requester",
        cascade="all, delete-orphan"
    )
    received_requests = relationship(
        "SwapRequest",
        foreign_keys="SwapRequest.target_id",
        back_populates="target",
        cascade="all, delete-orphan"
    )
    sent_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )


class SwapRequest(Base):
    __tablename__ = "swap_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(SwapRequestStatus), default=SwapRequestStatus.PENDING)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    requester = relationship("Student", foreign_keys=[requester_id], back_populates="sent_requests")
    target = relationship("Student", foreign_keys=[target_id], back_populates="received_requests")
    messages = relationship("ChatMessage", back_populates="swap_request", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    swap_request_id = Column(Integer, ForeignKey("swap_requests.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    sender = relationship("Student", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("Student", foreign_keys=[receiver_id], back_populates="received_messages")
    swap_request = relationship("SwapRequest", back_populates="messages")