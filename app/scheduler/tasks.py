from celery import Celery
from ..core.database import connect_to_mongo, close_mongo_connection
from ..domains.announcements.service import AnnouncementService
from ..shared.clients.public_data_client import PublicDataAPIClient
import logging
import asyncio
from .celery_app import celery_app

logger = logging.getLogger(__name__)


async def async_task_wrapper(async_func):
    """비동기 함수를 Celery 태스크에서 실행하기 위한 래퍼"""
    await connect_to_mongo()
    try:
        result = await async_func()
        return result
    finally:
        await close_mongo_connection()


@celery_app.task(bind=True, max_retries=3)
def fetch_all_announcements(self):
    """모든 사업공고 데이터 수집"""
    async def _fetch():
        logger.info("사업공고 데이터 수집 시작")
        service = AnnouncementService()
        
        total_fetched = 0
        page = 1
        
        while True:
            try:
                announcements = await service.fetch_and_save_announcements(
                    page_no=page,
                    num_of_rows=100  # 한 번에 많이 가져오기
                )
                
                if not announcements:
                    break
                    
                total_fetched += len(announcements)
                logger.info(f"페이지 {page}: {len(announcements)}개 수집, 총 {total_fetched}개")
                page += 1
                
                # 너무 많은 페이지를 가져오지 않도록 제한
                if page > 50:
                    break
                    
            except Exception as e:
                logger.error(f"페이지 {page} 수집 중 오류: {e}")
                self.retry(countdown=60, exc=e)
        
        logger.info(f"사업공고 데이터 수집 완료: 총 {total_fetched}개")
        return {"total_fetched": total_fetched}
    
    return asyncio.run(async_task_wrapper(_fetch))


@celery_app.task(bind=True, max_retries=3)
def fetch_all_contents(self):
    """모든 콘텐츠 데이터 수집"""
    async def _fetch():
        logger.info("콘텐츠 데이터 수집 시작")
        # TODO: ContentService 구현 후 활성화
        logger.info("콘텐츠 서비스 미구현 - 스킵")
        return {"total_fetched": 0}
    
    return asyncio.run(async_task_wrapper(_fetch))


@celery_app.task(bind=True, max_retries=3)
def fetch_all_statistics(self):
    """모든 통계 데이터 수집"""
    async def _fetch():
        logger.info("통계 데이터 수집 시작")
        # TODO: StatisticsService 구현 후 활성화
        logger.info("통계 서비스 미구현 - 스킵")
        return {"total_fetched": 0}
    
    return asyncio.run(async_task_wrapper(_fetch))


@celery_app.task(bind=True, max_retries=3)
def fetch_all_businesses(self):
    """모든 사업정보 데이터 수집"""
    async def _fetch():
        logger.info("사업정보 데이터 수집 시작")
        # TODO: BusinessService 구현 후 활성화
        logger.info("사업정보 서비스 미구현 - 스킵")
        return {"total_fetched": 0}
    
    return asyncio.run(async_task_wrapper(_fetch))


@celery_app.task
def test_task():
    """테스트용 태스크"""
    logger.info("테스트 태스크 실행")
    return "테스트 완료"