from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminBase(BaseModel):
    admin_name: str = Field(..., max_length=100)
    admin_email: EmailStr


class AdminCreate(AdminBase):
    password: str = Field(..., min_length=8)


class AdminLogin(BaseModel):
    admin_email: EmailStr
    password: str = Field(..., min_length=8)


class AdminResponse(AdminBase):
    admin_id: int
    password_initial_change: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminLoginResponse(AdminBase):
    admin_id: int
    access_token: str
    token_type: str = "bearer"
