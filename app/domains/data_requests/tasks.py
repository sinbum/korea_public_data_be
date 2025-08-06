"""데이터 요청 관련 백그라운드 작업"""
from typing import List
import uuid
from datetime import datetime

from ...core.database import get_database
from .repository import CategoryRepository
from .models import CategoryDocument, Category


async def initialize_default_categories():
    """기본 카테고리 초기화"""
    db = get_database()
    category_repo = CategoryRepository(db)
    
    # 기본 카테고리 데이터
    default_categories = [
        {
            "name": "교통",
            "description": "대중교통, 도로, 주차장 등 교통 관련 데이터",
            "color": "#3B82F6"
        },
        {
            "name": "환경",
            "description": "대기질, 수질, 쓰레기 등 환경 관련 데이터",
            "color": "#10B981"
        },
        {
            "name": "보건의료",
            "description": "병원, 의료진, 건강 관련 데이터",
            "color": "#EF4444"
        },
        {
            "name": "교육",
            "description": "학교, 도서관, 교육과정 등 교육 관련 데이터",
            "color": "#8B5CF6"
        },
        {
            "name": "복지",
            "description": "사회복지, 복지시설 등 복지 관련 데이터",
            "color": "#F59E0B"
        },
        {
            "name": "문화관광",
            "description": "문화재, 관광지, 축제 등 문화관광 관련 데이터",
            "color": "#EC4899"
        },
        {
            "name": "경제산업",
            "description": "기업, 일자리, 산업 등 경제산업 관련 데이터",
            "color": "#06B6D4"
        },
        {
            "name": "안전",
            "description": "치안, 재해, 안전시설 등 안전 관련 데이터",
            "color": "#DC2626"
        },
        {
            "name": "기타",
            "description": "위 분류에 속하지 않는 기타 데이터",
            "color": "#6B7280"
        }
    ]
    
    created_count = 0
    
    for category_data in default_categories:
        # 중복 확인
        existing = await category_repo.find_by_name(category_data["name"])
        if not existing:
            # 새 카테고리 생성
            category = Category(
                id=str(uuid.uuid4()),
                name=category_data["name"],
                description=category_data["description"],
                color=category_data["color"],
                created_at=datetime.utcnow()
            )
            
            category_document = CategoryDocument(data=category)
            await category_repo.create(category_document)
            created_count += 1
    
    return {
        "created_count": created_count,
        "total_categories": len(default_categories)
    }


async def cleanup_expired_votes():
    """만료된 투표 정리 (필요시)"""
    # 현재는 투표에 만료 기능이 없지만, 향후 필요시 구현
    pass