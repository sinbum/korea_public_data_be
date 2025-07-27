"""
Data collection and processing related schemas.
"""

from pydantic import BaseModel, Field
from typing import List


class DataCollectionResult(BaseModel):
    """데이터 수집 결과 모델"""
    total_fetched: int = Field(description="수집된 총 데이터 수")
    new_items: int = Field(description="새로 추가된 데이터 수")
    updated_items: int = Field(description="업데이트된 데이터 수")
    skipped_items: int = Field(description="중복으로 스킵된 데이터 수")
    errors: List[str] = Field(default_factory=list, description="수집 중 발생한 오류 목록")
    collection_time: float = Field(description="수집 소요 시간(초)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_fetched": 15,
                "new_items": 10,
                "updated_items": 3,
                "skipped_items": 2,
                "errors": [],
                "collection_time": 2.45
            }
        }
    }