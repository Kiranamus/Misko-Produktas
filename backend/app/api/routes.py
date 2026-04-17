from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import (
    DEFAULT_COARSE_GRID_SIZE_M,
    DEFAULT_COARSE_TILE_SIZE_M,
    DEFAULT_DETAIL_GRID_SIZE_M,
    DEFAULT_DETAIL_TILE_SIZE_M,
    DEFAULT_SIMPLIFY_TOL_M,
    MAX_WORKERS,
)
from ..database import User, get_db
from ..schemas_auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from ..services.auth_service import (
    create_password_reset_token,
    get_current_user_from_token,
    login_user,
    register_user,
    reset_user_password,
)
from ..services.pipeline import (
    get_metadata as get_analysis_metadata,
    process_analysis,
    read_status,
)
from ..services.query_service import (
    get_counties,
    query_distribution,
    query_grid,
    query_stats,
)


router = APIRouter()
security = HTTPBearer()


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    return get_current_user_from_token(db, token.credentials)


@router.post("/register")
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, user_data)


@router.post("/login")
async def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    return login_user(db, user_data)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return create_password_reset_token(db, request)


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    return reset_user_password(db, request)


@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.full_name}, you are authenticated!"}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "database": "postgresql"}


@router.get("/status")
async def status(layer: str = Query(default="coarse", pattern="^(coarse|detail)$")):
    try:
        return read_status(layer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metadata")
async def metadata(layer: str = Query(default="coarse", pattern="^(coarse|detail)$")):
    try:
        return get_analysis_metadata(layer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze")
async def analyze(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    grid_size: Optional[int] = None,
    tile_size: Optional[int] = None,
    simplify_tol_m: float = DEFAULT_SIMPLIFY_TOL_M,
    max_workers: int = MAX_WORKERS,
    clear_cache: bool = True,
    bbox: Optional[str] = Query(default=None, description="EPSG:3346 bbox: minx,miny,maxx,maxy"),
):
    try:
        if grid_size is None:
            grid_size = (
                DEFAULT_DETAIL_GRID_SIZE_M if layer == "detail" else DEFAULT_COARSE_GRID_SIZE_M
            )

        if tile_size is None:
            tile_size = (
                DEFAULT_DETAIL_TILE_SIZE_M if layer == "detail" else DEFAULT_COARSE_TILE_SIZE_M
            )

        return process_analysis(
            layer_name=layer,
            grid_size=grid_size,
            tile_size=tile_size,
            simplify_tol_m=simplify_tol_m,
            max_workers=max_workers,
            clear_cache=clear_cache,
            bbox=bbox,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grid")
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


@router.get("/stats")
async def stats(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    bbox: Optional[str] = Query(default=None, description="EPSG:3346 bbox: minx,miny,maxx,maxy"),
    county: Optional[str] = None,
    classes: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    w_restr: float = 40,
    w_soil: float = 30,
    w_road: float = 30,
):
    try:
        parsed_classes = [c.strip().upper() for c in classes.split(",")] if classes else None
        return query_stats(
            layer_name=layer,
            bbox=bbox,
            county=county,
            classes=parsed_classes,
            min_score=min_score,
            max_score=max_score,
            w_restr=w_restr,
            w_soil=w_soil,
            w_road=w_road,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/distribution")
async def distribution(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
):
    try:
        return query_distribution(layer_name=layer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/counties")
async def counties():
    try:
        return {"items": get_counties()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
