from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime, timezone

from auth import get_current_user
from models import get_progress, save_progress

router = APIRouter(prefix="/api", tags=["progress"])


class ProgressData(BaseModel):
    data: dict


@router.get("/progress")
def api_get_progress(request: Request):
    user = get_current_user(request)
    data = get_progress(user["user_id"])
    return {"ok": True, "data": data, "updated_at": data.get("_updated_at", "")}


@router.post("/progress")
def api_save_progress(request: Request, body: ProgressData):
    user = get_current_user(request)
    body.data["_updated_at"] = datetime.now(timezone.utc).isoformat()
    save_progress(user["user_id"], body.data)
    return {"ok": True}
