from fastapi import APIRouter

from app.api import admin, auth, student

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
