from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import hashlib
import secrets

from ...core.database import get_database


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: Optional[List[str]] = None


class ApiKeyItem(BaseModel):
    id: str
    name: str
    key_preview: str
    created_at: str
    last_used_at: Optional[str] = None
    status: str = "active"
    scopes: Optional[List[str]] = None


router = APIRouter(prefix="/keys", tags=["API 키"])


@router.get("/", summary="API 키 목록 조회")
def list_api_keys():
    db = get_database()
    items: List[ApiKeyItem] = []
    for doc in db["api_keys"].find({}).sort("created_at", -1):
        items.append(
            ApiKeyItem(
                id=str(doc.get("_id")),
                name=doc.get("name", ""),
                key_preview=doc.get("key_preview", "***"),
                created_at=doc.get("created_at", ""),
                last_used_at=doc.get("last_used_at"),
                status=doc.get("status", "active"),
                scopes=doc.get("scopes"),
            )
        )
    return {"success": True, "items": [item.dict() for item in items], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/", summary="API 키 생성")
def create_api_key(payload: CreateApiKeyRequest):
    db = get_database()

    raw_key = "sk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    key_preview = raw_key[:6] + "…" + raw_key[-4:]
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "name": payload.name,
        "key_hash": key_hash,
        "key_preview": key_preview,
        "created_at": now,
        "last_used_at": None,
        "status": "active",
        "scopes": payload.scopes or [],
    }

    result = db["api_keys"].insert_one(doc)
    return {"id": str(result.inserted_id), "key": raw_key, "key_preview": key_preview}


@router.post("/{key_id}/revoke", summary="API 키 폐기")
def revoke_api_key(key_id: str):
    db = get_database()
    updated = db["api_keys"].update_one({"_id": key_id}, {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}})
    if updated.matched_count == 0:
        # ObjectId와 문자열 혼용 방지: 문자열로 저장했을 수 있으므로 두 번째 시도 불필요 시 실패 처리
        raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다")
    return {"success": True}


