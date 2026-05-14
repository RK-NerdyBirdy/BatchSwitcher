from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.oauth import get_oauth
from app.core.security import verify_password, get_password_hash
from app.crud.admin import get_admin_by_email
from app.models.admin import Admin
from app.schemas.admin import AdminLogin, AdminResponse, AdminCreate, AdminLoginResponse
from app.services.auth_service import auth_service

router = APIRouter()


@router.get("/google/login")
async def google_login(request: Request):
    oauth = get_oauth()
    settings = get_settings()
    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    oauth = get_oauth()
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    if user is None:
        user = await oauth.google.parse_id_token(request, token)

    email = (user or {}).get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only permitted student accounts are allowed",
        )
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # --- ADD THIS DEBUG BLOCK ---
    try:
        auth_service.ensure_google_email_verified(user or {})
        print("✅ Email is verified by Google")
        
        auth_service.ensure_allowed_domain(email)
        print("✅ Domain is allowed")
        
        pfp_url = (user or {}).get("picture")
        await auth_service.update_student_pfp(db, email, pfp_url)
        print("✅ Student found in DB and PFP updated")
    except Exception as e:
        print(f"❌ CRASH HAPPENED HERE: {repr(e)}")
        raise e
    auth_service.ensure_google_email_verified(user or {})
    auth_service.ensure_allowed_domain(email)

    pfp_url = (user or {}).get("picture")
    await auth_service.update_student_pfp(db, email, pfp_url)

    # Generate JWT token for student
    student_name = (user or {}).get("name", email)
    jwt_token = auth_service.create_jwt_token(email, student_name, user_type="student", pfp_url=pfp_url)

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "email": email,
        "name": student_name,
        "pfp_url": pfp_url,
    }


@router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(
    payload: AdminLogin,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    admin = await get_admin_by_email(db, payload.admin_email)
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate JWT token for admin
    jwt_token = auth_service.create_jwt_token(
        email=admin.admin_email,
        name=admin.admin_name,
        user_type="admin",
        user_id=admin.admin_id,
    )
    
    return AdminLoginResponse(
        admin_name=admin.admin_name,
        admin_email=admin.admin_email,
        admin_id=admin.admin_id,
        access_token=jwt_token,
    )


@router.post("/admin/logout")
async def admin_logout() -> dict:
    """Logout endpoint (stateless JWT - just discard token on client side)."""
    return {"ok": True, "message": "Please discard the token on the client side"}

