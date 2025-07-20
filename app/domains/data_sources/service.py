from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ...core.database import get_database
from ...shared.models.data_source import (
    DataSourceConfig, 
    DataCollectionRequest, 
    DataCollectionResponse,
    FieldMapping,
    DataSourceType,
    ResponseFormat,
    AuthType
)
from ...shared.clients.dynamic_data_client import DynamicDataClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class DataSourceService:
    """데이터 소스 관리 서비스"""
    
    def __init__(self, db=None):
        self.db = db or get_database()
        self.collection = self.db.data_sources
    
    def create_data_source(self, config: DataSourceConfig) -> DataSourceConfig:
        """새 데이터 소스 등록"""
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        
        result = self.collection.insert_one(config.dict(by_alias=True))
        config.id = str(result.inserted_id)
        
        logger.info(f"새 데이터 소스 등록: {config.name}")
        return config
    
    def get_data_sources(
        self, 
        skip: int = 0, 
        limit: int = 20,
        is_active: bool = True
    ) -> List[DataSourceConfig]:
        """데이터 소스 목록 조회"""
        cursor = self.collection.find({"is_active": is_active}).skip(skip).limit(limit)
        sources = []
        
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            sources.append(DataSourceConfig(**doc))
        
        return sources
    
    def get_data_source_by_id(self, source_id: str) -> Optional[DataSourceConfig]:
        """ID로 데이터 소스 조회"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(source_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return DataSourceConfig(**doc)
            return None
        except Exception:
            return None
    
    def update_data_source(
        self, 
        source_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[DataSourceConfig]:
        """데이터 소스 수정"""
        try:
            updates["updated_at"] = datetime.utcnow()
            
            self.collection.update_one(
                {"_id": ObjectId(source_id)},
                {"$set": updates}
            )
            
            return self.get_data_source_by_id(source_id)
        except Exception:
            return None
    
    def delete_data_source(self, source_id: str) -> bool:
        """데이터 소스 삭제 (비활성화)"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(source_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def collect_data_from_source(
        self, 
        request: DataCollectionRequest
    ) -> DataCollectionResponse:
        """지정된 데이터 소스에서 데이터 수집"""
        try:
            # 데이터 소스 설정 조회
            source_config = self.get_data_source_by_id(request.source_id)
            if not source_config:
                return DataCollectionResponse(
                    success=False,
                    message=f"데이터 소스를 찾을 수 없습니다: {request.source_id}",
                    source_name="Unknown",
                    collected_count=0,
                    saved_count=0,
                    errors=[f"데이터 소스 ID {request.source_id}가 존재하지 않습니다."]
                )
            
            # 동적 클라이언트로 데이터 수집
            with DynamicDataClient(source_config) as client:
                response = client.collect_data(
                    params=request.params,
                    limit=request.limit
                )
            
            # 데이터베이스 저장 (요청 시)
            saved_count = 0
            if request.save_to_db and response.success:
                saved_count = self._save_collected_data(
                    response.data, 
                    source_config
                )
            
            response.saved_count = saved_count
            return response
            
        except Exception as e:
            error_msg = f"데이터 수집 중 오류: {str(e)}"
            logger.error(error_msg)
            
            return DataCollectionResponse(
                success=False,
                message="데이터 수집 실패",
                source_name=source_config.name if 'source_config' in locals() else "Unknown",
                collected_count=0,
                saved_count=0,
                errors=[error_msg]
            )
    
    def _save_collected_data(
        self, 
        data: List[Dict[str, Any]], 
        source_config: DataSourceConfig
    ) -> int:
        """수집된 데이터를 데이터베이스에 저장"""
        saved_count = 0
        
        # 데이터 소스 타입에 따라 적절한 컬렉션에 저장
        if source_config.source_type == DataSourceType.KISED_STARTUP:
            saved_count = self._save_to_announcements(data)
        else:
            # 일반적인 동적 데이터 저장
            saved_count = self._save_to_dynamic_collection(data, source_config)
        
        return saved_count
    
    def _save_to_announcements(self, data: List[Dict[str, Any]]) -> int:
        """사업공고 컬렉션에 저장"""
        from ..announcements.service import AnnouncementService
        
        announcement_service = AnnouncementService(self.db)
        saved_count = 0
        
        for item in data:
            try:
                # 기존 사업공고 서비스의 변환 로직 사용
                announcement_data = {
                    "business_id": item.get("business_id"),
                    "business_name": item.get("business_name"),
                    "business_type": item.get("business_type"),
                    "business_overview": item.get("business_overview"),
                    "support_target": item.get("support_target"),
                    "recruitment_period": item.get("recruitment_period"),
                    "application_method": item.get("application_method"),
                    "contact_info": item.get("contact_info"),
                    "announcement_date": item.get("announcement_date"),
                    "deadline": item.get("deadline"),
                    "status": item.get("status")
                }
                
                # 중복 체크
                business_id = announcement_data.get("business_id")
                business_name = announcement_data.get("business_name")
                
                existing = None
                if business_id:
                    existing = announcement_service.collection.find_one({
                        "announcement_data.business_id": business_id
                    })
                elif business_name:
                    existing = announcement_service.collection.find_one({
                        "announcement_data.business_name": business_name
                    })
                
                if not existing:
                    from ..announcements.models import Announcement
                    announcement = Announcement(
                        announcement_data=announcement_data,
                        source_url=f"동적수집-{business_id or 'unknown'}"
                    )
                    
                    announcement_service.collection.insert_one(
                        announcement.dict(by_alias=True)
                    )
                    saved_count += 1
                    
            except Exception as e:
                logger.warning(f"사업공고 저장 실패: {e}")
                continue
        
        return saved_count
    
    def _save_to_dynamic_collection(
        self, 
        data: List[Dict[str, Any]], 
        source_config: DataSourceConfig
    ) -> int:
        """동적 데이터 컬렉션에 저장"""
        collection_name = f"dynamic_{source_config.source_type}_{source_config.id}"
        collection = self.db[collection_name]
        
        saved_count = 0
        for item in data:
            try:
                # 메타데이터 추가
                item["_source_config_id"] = source_config.id
                item["_collected_at"] = datetime.utcnow()
                
                collection.insert_one(item)
                saved_count += 1
                
            except Exception as e:
                logger.warning(f"동적 데이터 저장 실패: {e}")
                continue
        
        return saved_count
    
    def create_predefined_sources(self):
        """미리 정의된 데이터 소스들 생성"""
        # 창업진흥원 K-Startup 사업공고
        kised_config = DataSourceConfig(
            name="창업진흥원 K-Startup 사업공고",
            description="창업진흥원에서 제공하는 사업공고 정보",
            source_type=DataSourceType.KISED_STARTUP,
            base_url="https://apis.data.go.kr/B552735/kisedKstartupService01",
            endpoint="/getAnnouncementInformation01",
            response_format=ResponseFormat.XML,
            auth_type=AuthType.API_KEY,
            auth_config={
                "key_param": "serviceKey",
                "key_value": "dZPAMSikx/yXGzz01oPffs614BnJw5g1h8H7GGJ905JdAbCZsLsQaAfA8bMtLtsNrmYL1dNMvb+j1o4aoaNu1w=="
            },
            default_params={
                "page": 0,
                "perPage": 100
            },
            field_mappings=[
                FieldMapping(
                    source_field="pbanc_sn",
                    target_field="business_id",
                    data_type="string",
                    required=True
                ),
                FieldMapping(
                    source_field="intg_pbanc_biz_nm",
                    target_field="business_name",
                    data_type="string",
                    required=True
                ),
                FieldMapping(
                    source_field="supt_biz_clsfc",
                    target_field="business_type",
                    data_type="string"
                ),
                FieldMapping(
                    source_field="pbanc_ctnt",
                    target_field="business_overview",
                    data_type="string"
                ),
                FieldMapping(
                    source_field="aply_trgt",
                    target_field="support_target",
                    data_type="string"
                ),
                FieldMapping(
                    source_field="pbanc_rcpt_bgng_dt",
                    target_field="announcement_date",
                    data_type="datetime"
                ),
                FieldMapping(
                    source_field="pbanc_rcpt_end_dt",
                    target_field="deadline",
                    data_type="datetime"
                )
            ]
        )
        
        # 기존 설정이 없으면 생성
        existing = self.collection.find_one({"name": kised_config.name})
        if not existing:
            self.create_data_source(kised_config)
            logger.info("기본 데이터 소스 생성 완료")