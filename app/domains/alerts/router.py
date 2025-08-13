from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, List

from ...core.config import settings
from ...core.database import DatabaseManager
from .schemas import (
    SubscriptionCreateRequest, SubscriptionResponse, NotificationPreviewRequest,
    NotificationPreferenceUpdate, NotificationPreferenceResponse, NotificationPreferencePreview,
    NotificationHistoryQuery
)
from .models import AlertSubscription, NotificationPreference
from .service import AlertsService


router = APIRouter(prefix="/alerts", tags=["alerts"])


async def get_service() -> AlertsService:
    dbm = DatabaseManager()
    db = await dbm.get_async_database()
    service = AlertsService(db)
    await service.init()
    return service


@router.post("/subscriptions", response_model=dict)
async def create_subscription(payload: SubscriptionCreateRequest, svc: AlertsService = Depends(get_service)):
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")

    sub = AlertSubscription(
        user_id="me",  # TODO: replace with authenticated user id dependency
        keywords=payload.keywords,
        filters=payload.filters or {},
        channels=payload.channels or ["email"],
        frequency=payload.frequency or "realtime",
    )
    sub_id = await svc.create_subscription(sub)
    return {"id": sub_id}


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def list_subscriptions(svc: AlertsService = Depends(get_service)):
    if not settings.alerts_enabled:
        return []
    docs = await svc.list_subscriptions("me")  # TODO: replace with authenticated user id
    return docs


@router.post("/test", response_model=dict)
async def preview_matches(req: NotificationPreviewRequest):
    if not settings.alerts_enabled:
        return {"total": 0, "items": []}
    # Scaffold: return empty preview for now
    return {"total": 0, "items": []}


# Notification Preference Management Endpoints

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_user_preferences(svc: AlertsService = Depends(get_service)):
    """사용자 알림 설정 조회"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    user_id = "me"  # TODO: replace with authenticated user id
    preferences = await svc.repository.get_user_preferences(user_id)
    
    if not preferences:
        # 기본 설정으로 새로 생성
        default_prefs = await svc.repository.get_default_preferences()
        new_preference = NotificationPreference(user_id=user_id, **default_prefs)
        await svc.repository.create_user_preferences(new_preference)
        preferences = new_preference.model_dump(by_alias=True)
    
    return NotificationPreferenceResponse(**preferences)


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_user_preferences(
    updates: NotificationPreferenceUpdate,
    svc: AlertsService = Depends(get_service)
):
    """사용자 알림 설정 업데이트"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    user_id = "me"  # TODO: replace with authenticated user id
    
    # 업데이트할 데이터 준비 (None 값 제외)
    update_data = updates.model_dump(exclude_unset=True, exclude_none=True)
    
    if not update_data:
        # 변경사항이 없으면 현재 설정 반환
        preferences = await svc.repository.get_user_preferences(user_id)
        if not preferences:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User preferences not found")
        return NotificationPreferenceResponse(**preferences)
    
    # 설정 업데이트
    success = await svc.repository.update_user_preferences(user_id, update_data)
    if not success:
        # 설정이 존재하지 않으면 새로 생성
        default_prefs = await svc.repository.get_default_preferences()
        default_prefs.update(update_data)
        new_preference = NotificationPreference(user_id=user_id, **default_prefs)
        await svc.repository.create_user_preferences(new_preference)
    
    # 업데이트된 설정 반환
    preferences = await svc.repository.get_user_preferences(user_id)
    if not preferences:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update preferences")
    
    return NotificationPreferenceResponse(**preferences)


@router.post("/preferences/preview", response_model=NotificationPreferencePreview)
async def preview_notification_settings(
    preferences: NotificationPreferenceUpdate,
    svc: AlertsService = Depends(get_service)
):
    """알림 설정 변경 시 예상 결과 미리보기"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    user_id = "me"  # TODO: replace with authenticated user id
    
    # 현재 설정 가져오기
    current_prefs = await svc.repository.get_user_preferences(user_id)
    if not current_prefs:
        current_prefs = await svc.repository.get_default_preferences()
    
    # 미리보기용 설정 생성 (현재 설정 + 변경사항)
    preview_data = current_prefs.copy()
    update_data = preferences.model_dump(exclude_unset=True, exclude_none=True)
    preview_data.update(update_data)
    
    # 활성화된 채널 계산
    active_channels = []
    for channel in ["email", "web", "push", "sms"]:
        if preview_data.get(f"{channel}_enabled", False):
            active_channels.append(channel)
    
    # 활성화된 카테고리 계산
    active_categories = []
    for category in ["new_announcements", "deadline_reminders", "digest_notifications", "system_notifications"]:
        if preview_data.get(category, False):
            active_categories.append(category)
    
    # 방해금지 시간 요약
    if preview_data.get("quiet_hours_enabled", False):
        start = preview_data.get("quiet_hours_start", 22)
        end = preview_data.get("quiet_hours_end", 7)
        quiet_hours_summary = f"{start:02d}:00 - {end:02d}:00"
    else:
        quiet_hours_summary = "비활성화"
    
    # 다이제스트 일정 요약
    digest_freq = preview_data.get("digest_frequency", "daily")
    if digest_freq == "off":
        digest_schedule = "비활성화"
    elif digest_freq == "daily":
        digest_schedule = "매일 오전 9시"
    elif digest_freq == "weekly":
        digest_schedule = "매주 월요일 오전 9시"
    elif digest_freq == "monthly":
        digest_schedule = "매월 1일 오전 9시"
    else:
        digest_schedule = digest_freq
    
    # 예상 알림 수 계산 (단순화된 로직)
    base_daily = len(active_categories) * 2  # 카테고리당 평균 2개
    base_weekly = base_daily * 7
    
    # 채널 수에 따른 조정
    channel_multiplier = len(active_channels) * 0.3  # 채널이 많을수록 약간 증가
    
    estimated_daily = max(0, int(base_daily + channel_multiplier))
    estimated_weekly = max(0, int(base_weekly + channel_multiplier * 7))
    
    # 최대 일일 제한 적용
    max_daily = preview_data.get("max_daily_notifications", 10)
    estimated_daily = min(estimated_daily, max_daily)
    
    return NotificationPreferencePreview(
        estimated_daily_notifications=estimated_daily,
        estimated_weekly_notifications=estimated_weekly,
        active_channels=active_channels,
        active_categories=active_categories,
        quiet_hours_summary=quiet_hours_summary,
        digest_schedule=digest_schedule
    )


@router.delete("/preferences", response_model=dict)
async def delete_user_preferences(svc: AlertsService = Depends(get_service)):
    """사용자 알림 설정 삭제 (기본값으로 초기화)"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    user_id = "me"  # TODO: replace with authenticated user id
    success = await svc.repository.delete_user_preferences(user_id)
    
    return {"success": success, "message": "Notification preferences reset to default"}


@router.get("/preferences/default", response_model=dict)
async def get_default_preferences(svc: AlertsService = Depends(get_service)):
    """기본 알림 설정 조회"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    defaults = await svc.repository.get_default_preferences()
    return {"defaults": defaults}

