"""
Authentication routes for OAuth and user management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse
from database import get_db
from models import Student
from schemas import StudentCreate, StudentResponse, AuthResponse
from auth import oauth, get_current_user, validate_vit_email
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
async def login(request: Request):
    """
    Initiate Google OAuth login flow
    
    Redirects to Google's OAuth consent screen
    """
    # Build redirect URI dynamically
    redirect_uri = str(request.url_for('auth_callback'))
    
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        access_type='offline',  # Request refresh token
        prompt='select_account'  # Force account selection
    )


@router.get("/callback", response_model=AuthResponse)
async def auth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback
    
    Returns:
        AuthResponse: Contains status and user info
    """
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from token
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google"
            )
        
        email = user_info.get('email')
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Validate VIT email
        is_valid, first_name, last_name = validate_vit_email(email)
        last_name = last_name[:-4]
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only VIT student emails (@vitstudent.ac.in) are allowed"
            )
        
        # Check if student already exists
        result = await db.execute(
            select(Student).where(Student.email == email)
        )
        student = result.scalar_one_or_none()
        
        if student:
            # Existing user - complete login
            request.session['user_email'] = email
            request.session['needs_registration'] = False
            
            return AuthResponse(
                status="success",
                message="Login successful",
                student=StudentResponse.model_validate(student)
            )
        else:
            # New user - needs registration
            request.session['user_email'] = email
            request.session['first_name'] = first_name
            request.session['last_name'] = last_name
            request.session['needs_registration'] = True
            
            return AuthResponse(
                status="registration_required",
                message="Please complete your registration",
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/register", response_model=StudentResponse)
async def register_student(
    student_data: StudentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete student registration after OAuth login
    
    Requires:
        - Active session with needs_registration=True
        - StudentCreate data (CGPA and batch)
    """
    # Validate session
    email = request.session.get('user_email')
    first_name = request.session.get('first_name')
    last_name = request.session.get('last_name')
    needs_registration = request.session.get('needs_registration')
    
    if not all([email, first_name, needs_registration]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration not initiated. Please login first."
        )
    
    # Check if already registered
    result = await db.execute(
        select(Student).where(Student.email == email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already registered"
        )
    
    # Create new student
    student = Student(
        email=email,
        first_name=first_name,
        last_name=last_name or "",
        cgpa=student_data.cgpa,
        current_batch=student_data.current_batch,
        original_batch=student_data.current_batch
    )
    
    db.add(student)
    await db.commit()
    await db.refresh(student)
    
    # Update session
    request.session['needs_registration'] = False
    
    return student


@router.get("/me", response_model=StudentResponse)
async def get_me(
    current_user: Student = Depends(get_current_user)
):
    """
    Get current authenticated user's profile
    
    Requires: Authentication
    """
    return current_user


@router.get("/check")
async def check_auth(request: Request):
    """
    Check authentication status without requiring login
    
    Returns session information
    """
    return {
        "authenticated": bool(request.session.get('user_email')),
        "needs_registration": request.session.get('needs_registration', False),
        "email": request.session.get('user_email')
    }


@router.post("/logout")
async def logout(request: Request):
    """
    Logout current user by clearing session
    """
    request.session.clear()
    
    return {
        "status": "success",
        "message": "Logged out successfully"
    }