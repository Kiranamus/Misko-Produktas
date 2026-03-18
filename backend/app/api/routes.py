from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.config import (
    DEFAULT_COARSE_GRID_SIZE_M,
    DEFAULT_COARSE_TILE_SIZE_M,
    DEFAULT_DETAIL_GRID_SIZE_M,
    DEFAULT_DETAIL_TILE_SIZE_M,
    DEFAULT_SIMPLIFY_TOL_M,
    MAX_WORKERS,
)
from app.services.pipeline import run_analysis, read_status
from app.services.query_service import get_metadata, query_grid, query_stats

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status")
def status(layer: str = "coarse"):
    return read_status(layer)


@router.get("/metadata")
def metadata(layer: str = "coarse"):
    return get_metadata(layer)


@router.post("/analyze")
def analyze(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    grid_size: Optional[int] = None,
    tile_size: Optional[int] = None,
    simplify_tol_m: float = DEFAULT_SIMPLIFY_TOL_M,
    max_workers: int = MAX_WORKERS,
    clear_cache: bool = True,
    bbox: Optional[str] = None,
):
    try:
        if grid_size is None:
            grid_size = DEFAULT_DETAIL_GRID_SIZE_M if layer == "detail" else DEFAULT_COARSE_GRID_SIZE_M

        if tile_size is None:
            tile_size = DEFAULT_DETAIL_TILE_SIZE_M if layer == "detail" else DEFAULT_COARSE_TILE_SIZE_M

        return run_analysis(
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
def grid(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    bbox: Optional[str] = Query(default=None, description="EPSG:3346 bbox: minx,miny,maxx,maxy"),
    classes: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
):
    try:
        parsed_classes = [c.strip().upper() for c in classes.split(",")] if classes else None
        return query_grid(
            layer_name=layer,
            bbox=bbox,
            classes=parsed_classes,
            min_score=min_score,
            max_score=max_score,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
def stats(
    layer: str = Query(default="coarse", pattern="^(coarse|detail)$"),
    bbox: Optional[str] = None,
    classes: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
):
    try:
        parsed_classes = [c.strip().upper() for c in classes.split(",")] if classes else None
        return query_stats(
            layer_name=layer,
            bbox=bbox,
            classes=parsed_classes,
            min_score=min_score,
            max_score=max_score,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))