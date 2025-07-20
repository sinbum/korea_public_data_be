from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DataSourceType(str, Enum):
    """데이터 소스 타입"""
    KISED_STARTUP = "kised_startup"  # 창업진흥원 K-Startup
    DATA_GO_KR = "data_go_kr"       # 공공데이터포털 일반
    CUSTOM_API = "custom_api"       # 사용자 정의 API


class ResponseFormat(str, Enum):
    """응답 데이터 형식"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"


class AuthType(str, Enum):
    """인증 방식"""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    NONE = "none"


class FieldMapping(BaseModel):
    """필드 매핑 설정"""
    source_field: str = Field(..., description="원본 API의 필드명")
    target_field: str = Field(..., description="내부 모델의 필드명")
    data_type: str = Field(default="string", description="데이터 타입 (string, int, datetime, etc.)")
    required: bool = Field(default=False, description="필수 필드 여부")
    default_value: Optional[Any] = Field(None, description="기본값")


class DataSourceConfig(BaseModel):
    """동적 데이터 소스 설정"""
    id: Optional[str] = Field(None, alias="_id", description="설정 고유 ID")
    name: str = Field(..., description="데이터 소스 이름")
    description: Optional[str] = Field(None, description="데이터 소스 설명")
    source_type: DataSourceType = Field(..., description="데이터 소스 타입")
    
    # API 설정
    base_url: str = Field(..., description="API 기본 URL")
    endpoint: str = Field(..., description="API 엔드포인트")
    method: str = Field(default="GET", description="HTTP 메소드")
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON, description="응답 형식")
    
    # 인증 설정
    auth_type: AuthType = Field(default=AuthType.API_KEY, description="인증 방식")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="인증 설정")
    
    # 요청 파라미터
    default_params: Dict[str, Any] = Field(default_factory=dict, description="기본 요청 파라미터")
    required_params: List[str] = Field(default_factory=list, description="필수 파라미터 목록")
    
    # 필드 매핑
    field_mappings: List[FieldMapping] = Field(default_factory=list, description="필드 매핑 설정")
    
    # 메타데이터
    is_active: bool = Field(default=True, description="활성 상태")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "창업진흥원 K-Startup 사업공고",
                "description": "창업진흥원에서 제공하는 사업공고 정보",
                "source_type": "kised_startup",
                "base_url": "https://apis.data.go.kr/B552735/kisedKstartupService01",
                "endpoint": "/getAnnouncementInformation01",
                "response_format": "xml",
                "auth_type": "api_key",
                "auth_config": {
                    "key_param": "serviceKey",
                    "key_value": "API_KEY"
                },
                "default_params": {
                    "page": 1,
                    "perPage": 10
                },
                "field_mappings": [
                    {
                        "source_field": "pbanc_sn",
                        "target_field": "business_id",
                        "data_type": "string",
                        "required": True
                    },
                    {
                        "source_field": "intg_pbanc_biz_nm",
                        "target_field": "business_name",
                        "data_type": "string",
                        "required": True
                    }
                ]
            }
        }
    }


class DataCollectionRequest(BaseModel):
    """데이터 수집 요청"""
    source_id: str = Field(..., description="데이터 소스 ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="추가 요청 파라미터")
    limit: Optional[int] = Field(default=10, description="수집할 데이터 수")
    save_to_db: bool = Field(default=True, description="데이터베이스 저장 여부")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_id": "kised_startup_announcements",
                "params": {
                    "business_type": "정부지원사업",
                    "page": 1
                },
                "limit": 20,
                "save_to_db": True
            }
        }
    }


class DataCollectionResponse(BaseModel):
    """데이터 수집 응답"""
    success: bool = Field(..., description="수집 성공 여부")
    message: str = Field(..., description="처리 메시지")
    source_name: str = Field(..., description="데이터 소스 이름")
    collected_count: int = Field(..., description="수집된 데이터 수")
    saved_count: int = Field(..., description="저장된 데이터 수")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="수집된 데이터")
    errors: List[str] = Field(default_factory=list, description="오류 목록")
    execution_time: Optional[float] = Field(None, description="실행 시간(초)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "데이터 수집이 완료되었습니다.",
                "source_name": "창업진흥원 K-Startup 사업공고",
                "collected_count": 15,
                "saved_count": 12,
                "data": [],
                "errors": ["중복 데이터 3건 스킵"],
                "execution_time": 2.5
            }
        }
    }