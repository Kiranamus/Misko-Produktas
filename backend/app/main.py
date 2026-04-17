from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db, User, init_db
from .schemas_auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from .services.auth_service import (
    create_password_reset_token,
    get_current_user_from_token,
    login_user,
    register_user,
    reset_user_password,
)
from .services.query_service import get_counties, query_grid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

security = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    return get_current_user_from_token(db, token.credentials)

@app.post("/register")
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, user_data)

@app.post("/login")
async def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    return login_user(db, user_data)

@app.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return create_password_reset_token(db, request)

@app.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    return reset_user_password(db, request)

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.full_name}, you are authenticated!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "postgresql"}

@app.get("/grid")
async def grid(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    bbox: Optional[str] = Query(default=None, description="EPSG:3346 bbox: minx,miny,maxx,maxy"),
    county: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
    w_restr: float = 40,
    w_soil: float = 30,
    w_road: float = 30,
):
    try:
        return query_grid(
            layer_name=layer,
            bbox=bbox,
            county=county,
            min_score=min_score,
            max_score=max_score,
            limit=limit,
            w_restr=w_restr,
            w_soil=w_soil,
            w_road=w_road,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/counties")
async def counties():
    try:
        return {"items": get_counties()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
