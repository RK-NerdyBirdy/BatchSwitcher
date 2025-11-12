"""
Authentication utilities and dependencies
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from config import settings
from database import get_db
from models import Student

# OAuth Setup
oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'  # Force account selection
    }
)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Student:
    """
    Dependency to get currently authenticated student from session
    
    Raises:
        HTTPException: If user is not authenticated or not found
    """
    user_email = request.session.get('user_email')
    
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login."
        )
    
    result = await db.execute(
        select(Student).where(Student.email == user_email)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        # Clear invalid session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found. Please complete registration."
        )
    
    return student


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Student | None:
    """
    Dependency to optionally get authenticated student
    Returns None if not authenticated
    """
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def validate_vit_email(email: str) -> tuple[bool, str, str]:
    """
    Validate VIT student email and extract name
    
    Returns:
        tuple: (is_valid, first_name, last_name)
    """
    if not email or not email.endswith('@vitstudent.ac.in'):
        return False, "", ""
    
    # Extract name from email (Firstname.Lastname@vitstudent.ac.in)
    try:
        name_part = email.split('@')[0]
        name_parts = name_part.split('.')
        
        first_name = name_parts[0].capitalize() if len(name_parts) > 0 else "Unknown"
        last_name = name_parts[1].capitalize() if len(name_parts) > 1 else ""
        
        return True, first_name, last_name
    except Exception:
        return False, "", ""