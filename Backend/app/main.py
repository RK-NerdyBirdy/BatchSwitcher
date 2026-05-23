from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware  

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Batch Switcher API",
    description="Batch switching platform with student-admin coordination",
    version="1.0.0",
    docs_url=None,    # Disables the /docs (Swagger UI)
    redoc_url=None,   # Disables the /redoc endpoint
    openapi_url=None, # Disables the /openapi.json endpoint
)

# ==========================================
# CORS MIDDLEWARE SETUP
# Must be added before the router!
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Allows your local frontend to connect
        "https://batchxchange.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# SessionMiddleware is required for OAuth state management (used internally by Authlib)
# Note: This is for OAuth flow only, not for admin API auth (which uses JWT)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="lax",
    https_only=True,
)
app.include_router(api_router, prefix="/api")

# Notice the .api_route here!
@app.api_route("/pinggg", methods=["GET", "HEAD"])
async def ping():
    return {"status": "awake"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Batch Switcher API",
        version="1.0.0",
        description="Batch switching platform with student-admin coordination",
        routes=app.routes,
    )

    # Add security scheme for JWT Bearer tokens
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token from OAuth (student) or admin login. Required for student and admin endpoints.",
        },
    }

    # Mark student and admin endpoints as requiring bearer auth
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            if "/student/" in path or "/admin/" in path:
                for operation in path_item.values():
                    if isinstance(operation, dict) and "security" in operation:
                        operation["security"] = [{"bearerAuth": []}]
                    elif isinstance(operation, dict) and "responses" in operation:
                        operation["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi