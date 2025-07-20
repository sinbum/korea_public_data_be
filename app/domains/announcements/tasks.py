from celery import shared_task
from typing import Dict, Any
import logging
from .service import AnnouncementService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def fetch_announcements_task(self) -> Dict[str, Any]:
    """
    창업지원 사업공고 데이터를 주기적으로 수집하는 Celery 태스크
    
    Returns:
        Dict[str, Any]: 태스크 실행 결과
    """
    try:
        logger.info(f"사업공고 데이터 수집 태스크 시작 - Task ID: {self.request.id}")
        
        service = AnnouncementService()
        
        # 기본 파라미터로 데이터 수집
        params = {
            "page": 1,
            "limit": 100  # 한 번에 더 많은 데이터 수집
        }
        
        result = service.fetch_announcements(params)
        
        logger.info(f"사업공고 데이터 수집 완료 - 수집된 항목: {result.get('fetched_count', 0)}개")
        
        return {
            "task_id": self.request.id,
            "status": "success",
            "message": "사업공고 데이터 수집 완료",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"사업공고 데이터 수집 중 오류 발생: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True)
def cleanup_old_announcements_task(self, days: int = 30) -> Dict[str, Any]:
    """
    오래된 사업공고 데이터를 정리하는 Celery 태스크
    
    Args:
        days (int): 보관할 일수 (기본값: 30일)
        
    Returns:
        Dict[str, Any]: 태스크 실행 결과
    """
    try:
        logger.info(f"오래된 사업공고 데이터 정리 시작 - {days}일 이전 데이터 삭제")
        
        service = AnnouncementService()
        
        # TODO: 실제 삭제 로직 구현 (현재는 로그만)
        # deleted_count = service.cleanup_old_announcements(days)
        deleted_count = 0
        
        logger.info(f"오래된 사업공고 데이터 정리 완료 - 삭제된 항목: {deleted_count}개")
        
        return {
            "task_id": self.request.id,
            "status": "success",
            "message": "오래된 데이터 정리 완료",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"데이터 정리 중 오류 발생: {str(e)}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "message": f"데이터 정리 실패: {str(e)}"
        }


@shared_task(bind=True)
def sync_announcement_data_task(self, announcement_id: str) -> Dict[str, Any]:
    """
    특정 사업공고 데이터를 동기화하는 Celery 태스크
    
    Args:
        announcement_id (str): 동기화할 사업공고 ID
        
    Returns:
        Dict[str, Any]: 태스크 실행 결과
    """
    try:
        logger.info(f"사업공고 데이터 동기화 시작 - ID: {announcement_id}")
        
        service = AnnouncementService()
        
        # TODO: 특정 ID 동기화 로직 구현
        # result = service.sync_announcement(announcement_id)
        result = {"synced": True}
        
        logger.info(f"사업공고 데이터 동기화 완료 - ID: {announcement_id}")
        
        return {
            "task_id": self.request.id,
            "status": "success",
            "message": "사업공고 동기화 완료",
            "announcement_id": announcement_id,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"사업공고 동기화 중 오류 발생: {str(e)}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "message": f"동기화 실패: {str(e)}",
            "announcement_id": announcement_id
        }