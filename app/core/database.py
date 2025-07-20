import pymongo
from .config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    client: pymongo.MongoClient = None
    database = None


mongodb = MongoDB()


def connect_to_mongo():
    """MongoDB 연결 생성"""
    try:
        mongodb.client = pymongo.MongoClient(settings.mongodb_url)
        mongodb.database = mongodb.client[settings.database_name]
        
        # 연결 테스트
        mongodb.client.admin.command("ping")
        logger.info("MongoDB 연결 성공")
        
    except Exception as e:
        logger.error(f"MongoDB 연결 실패: {e}")
        raise


def close_mongo_connection():
    """MongoDB 연결 종료"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("MongoDB 연결 종료")


def get_database():
    """현재 데이터베이스 인스턴스 반환"""
    return mongodb.database