from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from motor.motor_asyncio import AsyncIOMotorDatabase

from .repository import AlertsRepository

logger = logging.getLogger(__name__)


class NotificationFrequencyManager:
    """알림 빈도 및 스케줄링 관리"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repository = AlertsRepository(db)
        
    async def should_send_notification(self, user_id: Any, notification_type: str, content_id: str) -> tuple[bool, str]:
        """
        사용자와 알림 유형에 따라 알림을 보낼지 결정
        
        Args:
            user_id: 사용자 ID
            notification_type: 알림 유형 (new_announcement, deadline_reminder, etc.)
            content_id: 콘텐츠 ID
            
        Returns:
            (should_send: bool, reason: str)
        """
        
        # 1. 사용자 알림 설정 확인
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            preferences = await self.repository.get_default_preferences()
            
        # 2. 해당 카테고리가 비활성화되어 있으면 차단
        if not preferences.get(notification_type, True):
            return False, f"Category {notification_type} disabled"
            
        # 3. 방해금지 시간 확인
        is_quiet, _ = await self.repository.check_quiet_hours(user_id)
        if is_quiet:
            return False, "Quiet hours active"
            
        # 4. 일일 한도 확인
        daily_allowed, current_count, max_daily = await self.repository.check_daily_limit(user_id)
        if not daily_allowed:
            return False, f"Daily limit reached ({current_count}/{max_daily})"
            
        # 5. 중복 알림 확인
        duplicate_count = await self._count_recent_notifications(user_id, notification_type, content_id)
        if duplicate_count > 0:
            return False, "Duplicate notification"
            
        # 6. 매칭 점수 확인 (최소 매칭 점수 이상인지)
        min_score = preferences.get("minimum_match_score", 0.5)
        # 이 로직은 호출하는 쪽에서 처리되지만, 여기서도 체크 가능
        
        return True, "Allowed"
    
    async def _count_recent_notifications(self, user_id: Any, notification_type: str, content_id: str, hours: int = 24) -> int:
        """최근 N시간 내 같은 콘텐츠에 대한 알림 수 확인"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        count = await self.db["notifications"].count_documents({
            "user_id": user_id,
            "content_id": content_id,
            "created_at": {"$gte": since}
        })
        
        return count
    
    async def get_digest_schedule(self, user_id: Any) -> Optional[Dict[str, Any]]:
        """사용자의 다이제스트 발송 일정 조회"""
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            preferences = await self.repository.get_default_preferences()
            
        digest_frequency = preferences.get("digest_frequency", "daily")
        
        if digest_frequency == "off":
            return None
            
        # 기본 발송 시간은 오전 9시
        base_schedule = {
            "hour": 9,
            "minute": 0,
            "timezone": preferences.get("quiet_hours_timezone", "Asia/Seoul")
        }
        
        if digest_frequency == "daily":
            return {**base_schedule, "frequency": "daily"}
        elif digest_frequency == "weekly":
            return {**base_schedule, "frequency": "weekly", "weekday": 0}  # Monday
        elif digest_frequency == "monthly":
            return {**base_schedule, "frequency": "monthly", "day": 1}  # 1st of month
            
        return None
    
    async def get_deadline_reminder_schedule(self, user_id: Any, deadline_date: datetime) -> List[datetime]:
        """마감 알림 발송 일정 계산"""
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            preferences = await self.repository.get_default_preferences()
            
        reminder_days = preferences.get("deadline_reminder_days", [7, 3, 1])
        
        schedule = []
        for days_before in reminder_days:
            reminder_date = deadline_date - timedelta(days=days_before)
            if reminder_date > datetime.utcnow():
                schedule.append(reminder_date)
                
        return sorted(schedule)
    
    async def calculate_notification_priority(self, user_id: Any, notification_data: Dict[str, Any]) -> int:
        """
        알림 우선순위 계산 (1-5, 5가 가장 높음)
        
        Args:
            user_id: 사용자 ID
            notification_data: 알림 데이터 (type, content, keywords 등)
            
        Returns:
            priority: 1-5 (5가 가장 높은 우선순위)
        """
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            preferences = await self.repository.get_default_preferences()
            
        priority = 3  # 기본 우선순위
        
        # 1. 알림 유형별 우선순위
        notification_type = notification_data.get("type", "new_announcement")
        if notification_type == "deadline_reminder":
            days_left = notification_data.get("days_left", 7)
            if days_left <= 1:
                priority = 5  # 긴급
            elif days_left <= 3:
                priority = 4  # 높음
            else:
                priority = 3  # 보통
        elif notification_type == "system_notification":
            priority = 4  # 시스템 알림은 높은 우선순위
        elif notification_type == "marketing_notification":
            priority = 2  # 마케팅은 낮은 우선순위
            
        # 2. 우선순위 키워드 매칭
        priority_keywords = preferences.get("priority_keywords", [])
        content_text = notification_data.get("content", {}).get("title", "") + " " + \
                      notification_data.get("content", {}).get("description", "")
        
        for keyword in priority_keywords:
            if keyword.lower() in content_text.lower():
                priority = min(5, priority + 1)  # 최대 5
                break
                
        # 3. 매칭 점수 기반 우선순위 조정
        match_score = notification_data.get("match_score", 0.5)
        if match_score >= 0.9:
            priority = min(5, priority + 1)
        elif match_score >= 0.7:
            priority = min(5, priority + 0.5)
            
        return int(priority)
    
    async def get_optimal_send_time(self, user_id: Any, base_time: Optional[datetime] = None) -> datetime:
        """사용자 설정에 기반한 최적 발송 시간 계산"""
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            preferences = await self.repository.get_default_preferences()
            
        if base_time is None:
            base_time = datetime.utcnow()
            
        # 방해금지 시간 확인
        quiet_enabled = preferences.get("quiet_hours_enabled", False)
        if not quiet_enabled:
            return base_time
            
        import pytz
        timezone_str = preferences.get("quiet_hours_timezone", "Asia/Seoul")
        try:
            timezone = pytz.timezone(timezone_str)
            local_time = base_time.replace(tzinfo=pytz.UTC).astimezone(timezone)
            
            quiet_start = preferences.get("quiet_hours_start", 22)
            quiet_end = preferences.get("quiet_hours_end", 7)
            
            current_hour = local_time.hour
            
            # 방해금지 시간 중인지 확인
            if quiet_start > quiet_end:
                # 다음날로 넘어가는 경우 (예: 22시-7시)
                is_quiet = current_hour >= quiet_start or current_hour < quiet_end
            else:
                # 같은 날 안에서 처리
                is_quiet = quiet_start <= current_hour < quiet_end
                
            if is_quiet:
                # 방해금지 종료 시간까지 연기
                if quiet_start > quiet_end and current_hour >= quiet_start:
                    # 다음날 종료시간으로
                    next_send = local_time.replace(hour=quiet_end, minute=0, second=0, microsecond=0) + timedelta(days=1)
                elif quiet_start > quiet_end and current_hour < quiet_end:
                    # 오늘 종료시간으로
                    next_send = local_time.replace(hour=quiet_end, minute=0, second=0, microsecond=0)
                else:
                    # 같은 날, 종료시간으로
                    next_send = local_time.replace(hour=quiet_end, minute=0, second=0, microsecond=0)
                    
                return next_send.astimezone(pytz.UTC).replace(tzinfo=None)
                
        except Exception as e:
            logger.warning(f"Error calculating optimal send time for user {user_id}: {e}")
            
        return base_time
    
    async def get_blocked_keywords(self, user_id: Any) -> Set[str]:
        """사용자의 차단 키워드 목록 조회"""
        preferences = await self.repository.get_user_preferences(user_id)
        if not preferences:
            return set()
            
        blocked_keywords = preferences.get("blocked_keywords", [])
        return set(keyword.lower().strip() for keyword in blocked_keywords if keyword.strip())
    
    async def is_content_blocked(self, user_id: Any, content_data: Dict[str, Any]) -> tuple[bool, str]:
        """콘텐츠가 사용자의 차단 키워드에 걸리는지 확인"""
        blocked_keywords = await self.get_blocked_keywords(user_id)
        
        if not blocked_keywords:
            return False, "No blocked keywords"
            
        # 콘텐츠 텍스트 추출
        content_text = (
            content_data.get("title", "") + " " +
            content_data.get("description", "") + " " +
            content_data.get("summary", "") + " " +
            " ".join(content_data.get("keywords", []))
        ).lower()
        
        # 차단 키워드 확인
        for blocked_keyword in blocked_keywords:
            if blocked_keyword in content_text:
                return True, f"Blocked by keyword: {blocked_keyword}"
                
        return False, "Content allowed"
    
    async def update_notification_stats(self, user_id: Any, notification_id: str, status: str) -> None:
        """알림 발송 통계 업데이트 (미래 기능을 위한 준비)"""
        # 통계 컬렉션에 기록 (현재는 스킵, 필요시 구현)
        pass
    
    async def get_user_engagement_score(self, user_id: Any) -> float:
        """
        사용자 참여도 점수 계산 (0.0-1.0)
        높을수록 알림에 더 적극적으로 반응하는 사용자
        """
        # 최근 30일간 통계 기반 계산
        since = datetime.utcnow() - timedelta(days=30)
        
        # 발송된 알림 수
        sent_count = await self.db["notifications"].count_documents({
            "user_id": user_id,
            "status": "sent",
            "sent_at": {"$gte": since}
        })
        
        if sent_count == 0:
            return 0.5  # 기본 점수
            
        # 클릭/조회 통계는 현재 없으므로 기본 계산
        # 실제 구현시에는 클릭률, 설정 변경 빈도 등을 고려
        
        # 알림 설정이 많이 활성화되어 있으면 높은 점수
        preferences = await self.repository.get_user_preferences(user_id)
        if preferences:
            active_channels = sum([
                preferences.get("email_enabled", True),
                preferences.get("web_enabled", True), 
                preferences.get("push_enabled", False),
                preferences.get("sms_enabled", False)
            ])
            
            active_categories = sum([
                preferences.get("new_announcements", True),
                preferences.get("deadline_reminders", True),
                preferences.get("digest_notifications", True),
                preferences.get("system_notifications", True)
            ])
            
            # 0.3 ~ 1.0 범위로 정규화
            engagement = 0.3 + (active_channels / 4 * 0.35) + (active_categories / 4 * 0.35)
            return min(1.0, engagement)
        
        return 0.5  # 기본 점수