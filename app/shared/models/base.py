from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId


class APIResponse(BaseModel):
    """기본 API 응답 모델"""
    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="응답 메시지")
    error_code: Optional[str] = Field(None, description="오류 코드")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="응답 시간")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "요청이 성공적으로 처리되었습니다.",
                "error_code": None,
                "timestamp": "2024-03-15T10:30:00Z"
            }
        }
    }


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_before_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


class BaseDocument(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class PublicDataResponse(BaseModel):
    """공공데이터 API 응답 기본 구조"""
    current_count: int = Field(alias="currentCount")
    match_count: int = Field(alias="matchCount") 
    page: int
    per_page: int = Field(alias="perPage")
    total_count: int = Field(alias="totalCount")
    data: List[Any]

    model_config = {"populate_by_name": True}


class APIRequestLog(BaseDocument):
    """API 요청 로그"""
    endpoint: str
    params: dict
    response_status: int
    response_time: float
    error_message: Optional[str] = None