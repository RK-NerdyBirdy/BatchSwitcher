from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentBase(BaseModel):
    register_number: str = Field(..., max_length=20)
    student_name: str = Field(..., max_length=100)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=15)
    pfp_url: str | None = Field(default=None, max_length=512)


class StudentCreate(StudentBase):
    pass

class PhoneStatusResponse(BaseModel):
    has_phone_number: bool

class PhoneNumberUpdate(BaseModel):
    phone_number: str = Field(..., max_length=15)


    
class StudentResponse(StudentBase):
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentDirectoryResponse(BaseModel):
    register_number: str
    student_name: str
    pfp_url: str | None
    semester_name: str
    batch_name: str
    
    model_config = ConfigDict(from_attributes=True)