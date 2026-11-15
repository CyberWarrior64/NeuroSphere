from fastapi import APIRouter, Query

from app.demo_event_store import recent_predictions

router = APIRouter(prefix="/api/v1/demo", tags=["Demo Event History"])


@router.get("/events")
def get_recent_demo_events(limit: int = Query(50, ge=1, le=250)):
    events = recent_predictions(limit)
    return {
        "events": events,
        "count": len(events),
        "simulated": False,
        "storage": "local metadata-only SQLite history; latest 1000 predictions",
    }
