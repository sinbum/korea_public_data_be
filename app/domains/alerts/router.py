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


router = APIRouter(
    prefix="/alerts",
    tags=["알림 관리"],
    responses={
        503: {"description": "알림 기능이 비활성화됨"},
        500: {"description": "서버 내부 오류"},
        422: {"description": "요청 데이터 검증 실패"}
    }
)


async def get_service() -> AlertsService:
    dbm = DatabaseManager()
    db = await dbm.get_async_database()
    service = AlertsService(db)
    await service.init()
    return service


@router.post(
    "/subscriptions", 
    response_model=dict,
    summary="알림 구독 생성",
    description="""
    새로운 알림 구독을 생성합니다.
    
    **기능:**
    - 키워드 기반 알림 설정
    - 다중 채널 지원 (이메일, 웹, 푸시)
    - 실시간/일별/주별 빈도 설정
    - 카테고리 및 지역 필터링
    
    **사용 예시:**
    ```json
    {
        "keywords": ["AI", "스타트업", "핀테크"],
        "filters": {
            "domain": "announcements",
            "categories": ["기술창업"],
            "regions": ["서울", "경기"]
        },
        "channels": ["email", "web"],
        "frequency": "realtime"
    }
    ```
    """,
    responses={
        200: {"description": "구독 생성 성공", "content": {"application/json": {"example": {"id": "64f1a2b3c4d5e6f7g8h9i0j1"}}}},
        503: {"description": "알림 기능이 비활성화된 경우"},
        422: {"description": "입력 데이터 검증 실패"}
    }
)
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


@router.get(
    "/subscriptions", 
    response_model=List[SubscriptionResponse],
    summary="알림 구독 목록 조회",
    description="""
    현재 사용자의 모든 알림 구독을 조회합니다.
    
    **반환 정보:**
    - 구독 ID 및 생성일
    - 키워드 및 필터 설정
    - 알림 채널 및 빈도
    - 활성 상태 정보
    
    **참고:** 알림 기능이 비활성화된 경우 빈 배열을 반환합니다.
    """,
    responses={
        200: {"description": "구독 목록 조회 성공"},
        503: {"description": "알림 기능이 비활성화된 경우 빈 배열 반환"}
    }
)
async def list_subscriptions(svc: AlertsService = Depends(get_service)):
    if not settings.alerts_enabled:
        return []
    docs = await svc.list_subscriptions("me")  # TODO: replace with authenticated user id
    return docs


@router.post(
    "/test", 
    response_model=dict,
    summary="알림 매칭 미리보기",
    description="""
    설정한 키워드와 필터로 매칭되는 공고들을 미리 확인합니다.
    
    **기능:**
    - 키워드 매칭 결과 미리보기
    - 필터 조건별 결과 수 확인
    - 구독 생성 전 테스트용
    
    **요청 예시:**
    ```json
    {
        "keywords": ["AI", "스타트업"],
        "filters": {"domain": "announcements"},
        "limit": 5
    }
    ```
    
    **응답 예시:**
    ```json
    {
        "total": 3,
        "items": [{"title": "AI 스타트업 지원사업", "id": "123"}]
    }
    ```
    """,
    responses={
        200: {"description": "미리보기 성공", "content": {"application/json": {"example": {"total": 0, "items": []}}}},
        503: {"description": "알림 기능이 비활성화된 경우"}
    }
)
async def preview_matches(req: NotificationPreviewRequest):
    if not settings.alerts_enabled:
        return {"total": 0, "items": []}
    # Scaffold: return empty preview for now
    return {"total": 0, "items": []}


# Notification Preference Management Endpoints

@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="사용자 알림 설정 조회",
    description="""
    현재 사용자의 알림 설정을 조회합니다.
    
    **기능:**
    - 개인별 알림 채널 설정 확인
    - 방해금지 시간 설정 조회
    - 알림 카테고리별 활성화 상태
    - 일일/주간 알림 수 제한 설정
    
    **반환 정보:**
    ```json
    {
        "email_enabled": true,
        "web_enabled": true,
        "push_enabled": false,
        "quiet_hours_enabled": true,
        "quiet_hours_start": 22,
        "quiet_hours_end": 7,
        "max_daily_notifications": 10
    }
    ```
    
    **참고:** 설정이 존재하지 않으면 기본 설정으로 자동 생성됩니다.
    """,
    responses={
        200: {"description": "알림 설정 조회 성공"},
        503: {"description": "알림 기능이 비활성화된 경우"},
        404: {"description": "사용자 설정을 찾을 수 없음 (자동 생성됨)"}
    }
)
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


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="사용자 알림 설정 수정",
    description="""
    사용자의 알림 설정을 부분적으로 또는 전체적으로 수정합니다.
    
    **기능:**
    - 알림 채널별 활성화/비활성화
    - 방해금지 시간 설정 변경
    - 알림 카테고리별 세부 설정
    - 일일 최대 알림 수 제한 조정
    
    **요청 예시:**
    ```json
    {
        "email_enabled": false,
        "push_enabled": true,
        "quiet_hours_start": 23,
        "quiet_hours_end": 6,
        "max_daily_notifications": 15,
        "new_announcements": true,
        "deadline_reminders": false
    }
    ```
    
    **특징:**
    - 부분 업데이트 지원 (변경하고 싶은 필드만 전송)
    - 존재하지 않는 설정은 기본값으로 자동 생성
    - 실시간 설정 적용
    """,
    responses={
        200: {"description": "알림 설정 수정 성공"},
        503: {"description": "알림 기능이 비활성화된 경우"},
        422: {"description": "입력 데이터 검증 실패"},
        500: {"description": "설정 업데이트 실패"}
    }
)
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


@router.post(
    "/preferences/preview",
    response_model=NotificationPreferencePreview,
    summary="알림 설정 변경 미리보기",
    description="""
    알림 설정 변경 시 예상되는 결과를 미리 확인합니다.
    
    **기능:**
    - 일일/주간 예상 알림 수 계산
    - 활성화될 알림 채널 목록
    - 활성화될 알림 카테고리 목록
    - 방해금지 시간 적용 결과
    - 다이제스트 알림 스케줄
    
    **요청 예시:**
    ```json
    {
        "email_enabled": true,
        "push_enabled": true,
        "new_announcements": true,
        "deadline_reminders": true,
        "quiet_hours_enabled": true,
        "max_daily_notifications": 8
    }
    ```
    
    **응답 예시:**
    ```json
    {
        "estimated_daily_notifications": 5,
        "estimated_weekly_notifications": 35,
        "active_channels": ["email", "push"],
        "active_categories": ["new_announcements", "deadline_reminders"],
        "quiet_hours_summary": "22:00 - 07:00",
        "digest_schedule": "매일 오전 9시"
    }
    ```
    
    **참고:** 설정 저장 전 미리보기로 실제 변경되지 않습니다.
    """,
    responses={
        200: {"description": "미리보기 생성 성공", "content": {"application/json": {"example": {"estimated_daily_notifications": 5, "active_channels": ["email"]}}}},
        503: {"description": "알림 기능이 비활성화된 경우"}
    }
)
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


@router.delete(
    "/preferences",
    response_model=dict,
    summary="사용자 알림 설정 초기화",
    description="""
    사용자의 모든 알림 설정을 삭제하고 시스템 기본값으로 초기화합니다.
    
    **기능:**
    - 개인 설정 완전 삭제
    - 시스템 기본값으로 복원
    - 모든 채널 기본 상태로 리셋
    - 알림 히스토리는 유지
    
    **주의사항:**
    - 이 작업은 되돌릴 수 없습니다
    - 모든 개인 맞춤 설정이 사라집니다
    - 다음 로그인 시 기본 설정이 적용됩니다
    
    **응답 예시:**
    ```json
    {
        "success": true,
        "message": "Notification preferences reset to default"
    }
    ```
    """,
    responses={
        200: {"description": "설정 초기화 성공", "content": {"application/json": {"example": {"success": True, "message": "설정이 기본값으로 초기화되었습니다"}}}},
        503: {"description": "알림 기능이 비활성화된 경우"},
        500: {"description": "초기화 과정에서 오류 발생"}
    }
)
async def delete_user_preferences(svc: AlertsService = Depends(get_service)):
    """사용자 알림 설정 삭제 (기본값으로 초기화)"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    user_id = "me"  # TODO: replace with authenticated user id
    success = await svc.repository.delete_user_preferences(user_id)
    
    return {"success": success, "message": "Notification preferences reset to default"}


@router.get(
    "/preferences/default",
    response_model=dict,
    summary="시스템 기본 알림 설정 조회",
    description="""
    시스템에서 제공하는 기본 알림 설정값을 조회합니다.
    
    **기능:**
    - 신규 사용자 기본 설정 확인
    - 설정 초기화 시 적용될 값 미리보기
    - 시스템 권장 설정 참조
    
    **반환 정보:**
    - 기본 활성화 채널 목록
    - 권장 방해금지 시간
    - 기본 알림 카테고리 설정
    - 권장 일일 알림 수 제한
    
    **응답 예시:**
    ```json
    {
        "defaults": {
            "email_enabled": true,
            "web_enabled": true,
            "push_enabled": false,
            "sms_enabled": false,
            "quiet_hours_enabled": false,
            "quiet_hours_start": 22,
            "quiet_hours_end": 7,
            "max_daily_notifications": 10,
            "digest_frequency": "daily"
        }
    }
    ```
    
    **용도:** 설정 UI의 기본값 표시, 사용자 온보딩 참조
    """,
    responses={
        200: {"description": "기본 설정 조회 성공", "content": {"application/json": {"example": {"defaults": {"email_enabled": True, "max_daily_notifications": 10}}}}},
        503: {"description": "알림 기능이 비활성화된 경우"}
    }
)
async def get_default_preferences(svc: AlertsService = Depends(get_service)):
    """기본 알림 설정 조회"""
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")
    
    defaults = await svc.repository.get_default_preferences()
    return {"defaults": defaults}

