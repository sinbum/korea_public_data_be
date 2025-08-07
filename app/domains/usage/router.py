from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timezone
from collections import Counter, defaultdict

from ...core.database import get_database

router = APIRouter(prefix="/usage", tags=["API 사용량"])


@router.get("/summary", summary="기간 요약")
def get_summary(from_: str = Query(..., alias="from"), to: str = Query(...)):
    db = get_database()
    try:
        start = datetime.fromisoformat(from_.replace("Z", "+00:00"))
        end = datetime.fromisoformat(to.replace("Z", "+00:00"))
    except Exception:
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

    cur = db["api_usage"].find({
        "timestamp": {"$gte": start.isoformat(), "$lte": end.isoformat()}
    })

    total = 0
    by_endpoint = Counter()
    by_status = Counter()
    daily = defaultdict(int)

    for doc in cur:
        total += 1
        by_endpoint[doc.get("endpoint", "")] += 1
        by_status[doc.get("status", 0)] += 1
        day = (doc.get("timestamp", "") or "")[:10]
        if day:
            daily[day] += 1

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_requests": total,
        "by_endpoint": [{"endpoint": k, "count": v} for k, v in by_endpoint.most_common()],
        "by_status": [{"status": int(k), "count": v} for k, v in by_status.most_common()],
        "daily": [{"date": d, "count": c} for d, c in sorted(daily.items())]
    }


@router.get("/", summary="사용량 목록")
def list_usage(from_: str = Query(..., alias="from"), to: str = Query(...), page: int = 1, size: int = 100):
    db = get_database()
    try:
        start = datetime.fromisoformat(from_.replace("Z", "+00:00"))
        end = datetime.fromisoformat(to.replace("Z", "+00:00"))
    except Exception:
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

    skip = (page - 1) * size
    cur = db["api_usage"].find({
        "timestamp": {"$gte": start.isoformat(), "$lte": end.isoformat()}
    }).sort("timestamp", -1).skip(skip).limit(size)

    items = []
    for doc in cur:
        items.append({
            "timestamp": doc.get("timestamp"),
            "endpoint": doc.get("endpoint"),
            "method": doc.get("method", "GET"),
            "status": doc.get("status", 0),
            "latency_ms": doc.get("latency_ms", 0)
        })

    return {"success": True, "items": items}


