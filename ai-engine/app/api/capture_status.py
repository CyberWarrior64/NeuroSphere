from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.demo_event_store import (
    capture_runner_status,
    heartbeat_capture_session,
    start_capture_session,
    stop_capture_session,
)

router = APIRouter(prefix="/api/v1/capture/runner", tags=["Capture Runner Status"])


class CaptureSessionUpdate(BaseModel):
    session_id: str
    action: Literal["start", "heartbeat", "stop"]
    capture_mode: Literal["live", "pcap"] | None = None


@router.get("/status")
def get_capture_runner_status():
    return capture_runner_status()


@router.post("/session")
def update_capture_session(payload: CaptureSessionUpdate):
    try:
        session_id = str(UUID(payload.session_id))
        if payload.action == "start":
            if payload.capture_mode is None:
                raise HTTPException(status_code=422, detail="capture_mode is required when starting a session")
            start_capture_session(session_id, payload.capture_mode)
        elif payload.action == "heartbeat":
            if not heartbeat_capture_session(session_id):
                raise HTTPException(status_code=404, detail="Capture session is not active")
        elif not stop_capture_session(session_id):
            raise HTTPException(status_code=404, detail="Capture session is not active")
    except ValueError as error:
        raise HTTPException(status_code=422, detail="session_id must be a UUID") from error
    return {"accepted": True, "action": payload.action}
