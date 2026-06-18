"""FastAPI backend — wraps the GridLock ML pipeline as a REST API.

Serves the React SPA at / and the prediction + metrics endpoints at /api/*.
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.predict import predict_all
from src import config as C

app = FastAPI(title="GridLock Congestion Intelligence API", version="1.0.0")

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


@app.post("/api/predict")
async def predict_endpoint(req: IncidentRequest):
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
        result = predict_all(record, live_llm=req.live_llm)
        # Convert closure_reasons tuples to JSON-serialisable dicts
        result["closure_reasons"] = [
            {"feature": str(f), "contribution": round(float(c), 4)}
            for f, c in result.get("closure_reasons", [])
        ]
        return JSONResponse(content=result)
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=500, detail=f"{exc}\n{traceback.format_exc()}")


@app.get("/api/metrics")
async def get_metrics():
    metrics_path = ROOT / "models" / "metrics.json"
    with open(metrics_path) as f:
        return json.load(f)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


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
