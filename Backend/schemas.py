"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from models import BatchEnum, SwapRequestStatus


# Student Schemas
class StudentCreate(BaseModel):
    cgpa: float
    current_batch: BatchEnum
    
    @field_validator('cgpa')
    @classmethod
    def validate_cgpa(cls, v):
        if not 0.0 <= v <= 10.0:
            raise ValueError('CGPA must be between 0 and 10')
        return v


class StudentResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    cgpa: float
    current_batch: BatchEnum
    original_batch: BatchEnum
    created_at: datetime
    
    model_config = {"from_attributes": True}


class EligibleStudentResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    cgpa: float
    current_batch: BatchEnum
    cgpa_difference: float
    
    model_config = {"from_attributes": True}


class StudentUpdate(BaseModel):
    cgpa: Optional[float] = None
    
    @field_validator('cgpa')
    @classmethod
    def validate_cgpa(cls, v):
        if v is not None and not 0.0 <= v <= 10.0:
            raise ValueError('CGPA must be between 0 and 10')
        return v


# Swap Request Schemas
class SwapRequestCreate(BaseModel):
    target_id: int
    message: Optional[str] = None


class SwapRequestResponse(BaseModel):
    id: int
    requester: StudentResponse
    target: StudentResponse
    status: SwapRequestStatus
    message: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Chat Message Schemas
class ChatMessageCreate(BaseModel):
    receiver_id: int
    swap_request_id: int
    message: str


class ChatMessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    swap_request_id: int
    message: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Auth Schemas
class AuthResponse(BaseModel):
    status: str
    message: Optional[str] = None
    student: Optional[StudentResponse] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None