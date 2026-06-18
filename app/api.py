"""FastAPI backend — wraps the GridLock ML pipeline as a REST API.

Serves the React SPA at / and the prediction + metrics endpoints at /api/*.
ML pipeline is loaded lazily so the health endpoint is always available even
if xgboost/sklearn fail to initialise in the container environment.
"""
from __future__ import annotations
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gridlock")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Lazy ML pipeline ──────────────────────────────────────────────────────────
_predict_fn = None
_startup_error: Optional[str] = None


def _load_ml() -> bool:
    """Import the ML pipeline once; cache success/failure. Returns True on success."""
    global _predict_fn, _startup_error
    if _predict_fn is not None:
        return True
    if _startup_error is not None:
        return False
    try:
        from src.predict import predict_all  # noqa: PLC0415 — intentional lazy import
        _predict_fn = predict_all
        logger.info("ML pipeline loaded OK")
        return True
    except Exception as exc:
        import traceback
        _startup_error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        logger.error("ML pipeline load FAILED:\n%s", _startup_error)
        return False


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info(
        "GridLock API starting | CWD=%s  ROOT=%s  PORT=%s",
        Path.cwd(), ROOT, os.environ.get("PORT", "not set"),
    )
    logger.info("Python %s", sys.version.split()[0])
    try:
        models_dir = ROOT / "models"
        if models_dir.exists():
            for p in sorted(models_dir.iterdir()):
                logger.info("  model: %s  (%d KB)", p.name, p.stat().st_size // 1024)
        else:
            logger.warning("models/ directory NOT found at %s", models_dir)
    except Exception as exc:
        logger.error("Error listing models dir: %s", exc)
    # ML is NOT loaded here — loading XGBoost/sklearn blocks the asyncio event loop
    # for several seconds, preventing uvicorn from responding to healthchecks.
    # _load_ml() is called lazily on the first /api/predict request instead.
    logger.info("GridLock API ready — ML will load on first prediction request")
    yield
    logger.info("GridLock API shutting down")


app = FastAPI(
    title="GridLock Congestion Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IncidentRequest(BaseModel):
    corridor: str = "Non-corridor"
    event_cause: str = "vehicle_breakdown"
    veh_type: Optional[str] = None
    zone: Optional[str] = None
    datetime_str: Optional[str] = None
    is_planned: bool = False
    description: Optional[str] = ""
    live_llm: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    police_station: Optional[str] = None


@app.get("/api/health")
async def health():
    return JSONResponse(content={
        "status": "ok",
        "version": "1.0.0",
        "ml_ready": _predict_fn is not None,
        "ml_error": _startup_error,
    })


@app.post("/api/predict")
async def predict_endpoint(req: IncidentRequest):
    if not _load_ml():
        raise HTTPException(
            status_code=503,
            detail=f"ML pipeline unavailable — check deploy logs. Error: {_startup_error}",
        )
    try:
        dt = datetime.now()
        if req.datetime_str:
            try:
                dt = datetime.fromisoformat(req.datetime_str)
            except Exception:
                pass

        record = {
            "corridor": req.corridor,
            "event_cause": req.event_cause,
            "veh_type": req.veh_type or None,
            "zone": req.zone or None,
            "datetime": dt,
            "is_planned": req.is_planned,
            "description": req.description or "",
            "latitude": req.latitude,
            "longitude": req.longitude,
            "police_station": req.police_station or None,
        }
        result = _predict_fn(record, live_llm=req.live_llm)
        result["closure_reasons"] = [
            {"feature": str(f), "contribution": round(float(c), 4)}
            for f, c in result.get("closure_reasons", [])
        ]
        return JSONResponse(content=result)
    except Exception as exc:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"{exc}\n{traceback.format_exc()}",
        )


@app.get("/api/metrics")
async def get_metrics():
    metrics_path = ROOT / "models" / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=503, detail="metrics.json not found")
    with open(metrics_path) as f:
        return json.load(f)


# ── Serve React static build ──────────────────────────────────────────────────
DIST = ROOT / "frontend" / "dist"

if DIST.exists():
    assets_dir = DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(str(DIST / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = DIST / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(DIST / "index.html"))
