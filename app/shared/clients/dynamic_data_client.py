import httpx
import xml.etree.ElementTree as ET
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from ..models.data_source import (
    DataSourceConfig, 
    ResponseFormat, 
    AuthType, 
    FieldMapping,
    DataCollectionResponse
)

logger = logging.getLogger(__name__)


class DynamicDataClient:
    """동적 공공데이터 수집 클라이언트"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.client = None
    
    def __enter__(self):
        self.client = httpx.Client(timeout=30.0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
    
    def collect_data(
        self, 
        params: Optional[Dict[str, Any]] = None, 
        limit: Optional[int] = None
    ) -> DataCollectionResponse:
        """데이터 수집 실행"""
        start_time = time.time()
        collected_data = []
        errors = []
        
        try:
            # 요청 파라미터 구성
            request_params = self._build_request_params(params, limit)
            
            # API 호출
            response_data = self._make_api_call(request_params)
            
            # 응답 데이터 파싱
            parsed_data = self._parse_response(response_data)
            
            # 필드 매핑 적용
            mapped_data = self._apply_field_mappings(parsed_data)
            
            collected_data = mapped_data
            
        except Exception as e:
            error_msg = f"데이터 수집 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        execution_time = time.time() - start_time
        
        return DataCollectionResponse(
            success=len(errors) == 0,
            message="데이터 수집 완료" if len(errors) == 0 else "데이터 수집 중 오류 발생",
            source_name=self.config.name,
            collected_count=len(collected_data),
            saved_count=0,  # 실제 저장은 서비스 레이어에서 처리
            data=collected_data,
            errors=errors,
            execution_time=execution_time
        )
    
    def _build_request_params(
        self, 
        params: Optional[Dict[str, Any]] = None, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """요청 파라미터 구성"""
        request_params = self.config.default_params.copy()
        
        # 사용자 제공 파라미터 병합
        if params:
            request_params.update(params)
        
        # 인증 정보 추가
        if self.config.auth_type == AuthType.API_KEY:
            auth_config = self.config.auth_config
            key_param = auth_config.get("key_param", "serviceKey")
            key_value = auth_config.get("key_value", "")
            request_params[key_param] = key_value
        
        # 제한 수 적용
        if limit:
            # 일반적인 페이징 파라미터명들 시도
            if "perPage" in request_params:
                request_params["perPage"] = limit
            elif "numOfRows" in request_params:
                request_params["numOfRows"] = limit
            elif "limit" in request_params:
                request_params["limit"] = limit
        
        return request_params
    
    def _make_api_call(self, params: Dict[str, Any]) -> str:
        """API 호출 실행"""
        url = f"{self.config.base_url}{self.config.endpoint}"
        
        # HTTP 헤더 설정
        headers = {"User-Agent": "Korea Public API Client/1.0"}
        
        # Bearer Token 인증
        if self.config.auth_type == AuthType.BEARER_TOKEN:
            token = self.config.auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        
        logger.info(f"API 요청: {url}")
        # 민감 값 마스킹(예: serviceKey, Authorization, token 등)
        try:
            def _mask(d: Dict[str, Any]) -> Dict[str, Any]:
                masked = {}
                for k, v in (d or {}).items():
                    if isinstance(v, str) and k.lower() in {"servicekey", "authorization", "access_token", "refresh_token", "token"}:
                        masked[k] = v[:4] + "***" if len(v) > 7 else "***"
                    else:
                        masked[k] = v
                return masked
            logger.debug(f"요청 파라미터: {_mask(params or {})}")
        except Exception:
            logger.debug("요청 파라미터 로깅 생략(마스킹 실패)")
        
        if self.config.method.upper() == "GET":
            response = self.client.get(url, params=params, headers=headers)
        elif self.config.method.upper() == "POST":
            response = self.client.post(url, json=params, headers=headers)
        else:
            raise ValueError(f"지원하지 않는 HTTP 메소드: {self.config.method}")
        
        response.raise_for_status()
        
        logger.info(f"API 요청 성공 (응답시간: {response.elapsed.total_seconds():.2f}s)")
        return response.text
    
    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """응답 데이터 파싱"""
        if self.config.response_format == ResponseFormat.JSON:
            return self._parse_json_response(response_text)
        elif self.config.response_format == ResponseFormat.XML:
            return self._parse_xml_response(response_text)
        else:
            raise ValueError(f"지원하지 않는 응답 형식: {self.config.response_format}")
    
    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """JSON 응답 파싱"""
        try:
            data = json.loads(response_text)
            
            # 다양한 JSON 구조 지원
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # 일반적인 응답 구조 패턴들
                if "data" in data:
                    if isinstance(data["data"], list):
                        return data["data"]
                    elif isinstance(data["data"], dict) and "data" in data["data"]:
                        return data["data"]["data"]
                elif "items" in data:
                    return data["items"]
                elif "results" in data:
                    return data["results"]
                else:
                    return [data]
            else:
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return []
    
    def _parse_xml_response(self, response_text: str) -> List[Dict[str, Any]]:
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(response_text)
            results = []
            
            # item 태그들을 찾아서 처리
            items = root.findall(".//item")
            if not items:
                # item이 없으면 data 하위 요소들 찾기
                items = root.findall(".//data/*")
            
            for item in items:
                item_dict = {}
                
                # col 태그가 있는 경우 (공공데이터포털 형식)
                cols = item.findall("col")
                if cols:
                    for col in cols:
                        name = col.get("name", "")
                        value = col.text or ""
                        if name:
                            item_dict[name] = value
                else:
                    # 일반적인 XML 요소 처리
                    for child in item:
                        tag = child.tag
                        text = child.text or ""
                        item_dict[tag] = text
                
                if item_dict:
                    results.append(item_dict)
            
            return results
            
        except ET.ParseError as e:
            logger.error(f"XML 파싱 실패: {e}")
            return []
    
    def _apply_field_mappings(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """필드 매핑 적용"""
        if not self.config.field_mappings:
            return data
        
        mapped_data = []
        
        for item in data:
            mapped_item = {}
            
            for mapping in self.config.field_mappings:
                source_value = item.get(mapping.source_field)
                
                # 기본값 처리
                if source_value is None and mapping.default_value is not None:
                    source_value = mapping.default_value
                
                # 데이터 타입 변환
                converted_value = self._convert_data_type(source_value, mapping.data_type)
                
                mapped_item[mapping.target_field] = converted_value
            
            # 매핑되지 않은 원본 필드도 포함 (선택적)
            for key, value in item.items():
                if key not in [m.source_field for m in self.config.field_mappings]:
                    mapped_item[f"_raw_{key}"] = value
            
            mapped_data.append(mapped_item)
        
        return mapped_data
    
    def _convert_data_type(self, value: Any, data_type: str) -> Any:
        """데이터 타입 변환"""
        if value is None:
            return None
        
        try:
            if data_type == "int":
                return int(value) if value else None
            elif data_type == "float":
                return float(value) if value else None
            elif data_type == "datetime":
                if isinstance(value, str) and value:
                    # 다양한 날짜 형식 지원
                    if len(value) == 8 and value.isdigit():  # YYYYMMDD
                        return datetime.strptime(value, "%Y%m%d")
                    elif "-" in value:  # YYYY-MM-DD
                        return datetime.strptime(value[:10], "%Y-%m-%d")
                return None
            elif data_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ("true", "y", "yes", "1")
                return bool(value)
            else:  # string (default)
                return str(value) if value is not None else None
                
        except (ValueError, TypeError):
            logger.warning(f"데이터 타입 변환 실패: {value} -> {data_type}")
            return value