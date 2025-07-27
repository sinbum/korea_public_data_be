#!/usr/bin/env python3
"""
K-Startup API 필드 매핑 검증 스크립트

실제 API 응답과 현재 모델 정의 간의 필드 매핑을 검증합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import logging
from pydantic import BaseModel
import inspect

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리로 이동
sys_path = os.path.abspath('.')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

# 모델 임포트
try:
    from app.shared.models.kstartup import (
        AnnouncementItem,
        BusinessItem, 
        ContentItem,
        StatisticalItem
    )
    from app.domains.announcements.models import Announcement
    from app.domains.businesses.models import Business
    from app.domains.contents.models import Content
    from app.domains.statistics.models import Statistics
except ImportError as e:
    logger.error(f"Failed to import models: {e}")
    logger.info("Please run this script from the project root directory")
    exit(1)

# 결과 디렉토리 경로
RESULTS_DIR = Path("tests/live/results")
VALIDATION_OUTPUT_DIR = Path("docs/reports/field_mapping_validation")
VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class FieldMappingValidator:
    """필드 매핑 검증기"""
    
    def __init__(self):
        self.sample_files = {
            "announcements": {
                "file": "announcements_basic_sample.json",
                "api_model": AnnouncementItem,
                "domain_model": Announcement
            },
            "business": {
                "file": "business_basic_sample.json",
                "api_model": BusinessItem,
                "domain_model": Business
            },
            "content": {
                "file": "content_basic_sample.json",
                "api_model": ContentItem,
                "domain_model": Content
            },
            "statistics": {
                "file": "statistics_basic_sample.json",
                "api_model": StatisticalItem,
                "domain_model": Statistics
            }
        }
        self.validation_results = {}
    
    def validate_all_mappings(self):
        """모든 필드 매핑 검증"""
        logger.info("Starting field mapping validation...")
        
        for endpoint_name, config in self.sample_files.items():
            sample_path = RESULTS_DIR / config["file"]
            
            if sample_path.exists():
                logger.info(f"Validating {endpoint_name} field mappings...")
                validation = self.validate_endpoint_mapping(
                    endpoint_name, 
                    sample_path, 
                    config["api_model"],
                    config["domain_model"]
                )
                self.validation_results[endpoint_name] = validation
            else:
                logger.warning(f"Sample file not found: {sample_path}")
        
        # 검증 결과 저장
        self.save_validation_results()
        
        logger.info("Field mapping validation completed")
    
    def validate_endpoint_mapping(
        self, 
        endpoint_name: str, 
        sample_path: Path, 
        api_model: type, 
        domain_model: type
    ) -> Dict[str, Any]:
        """개별 엔드포인트 필드 매핑 검증"""
        
        # 실제 응답 데이터 로드
        with open(sample_path, 'r', encoding='utf-8') as f:
            response_data = json.load(f)
        
        actual_fields = set()
        if response_data.get("data") and len(response_data["data"]) > 0:
            first_item = response_data["data"][0]
            actual_fields = set(first_item.keys())
        
        # API 모델 필드 분석
        api_model_info = self.analyze_pydantic_model(api_model)
        
        # 도메인 모델 필드 분석
        domain_model_info = self.analyze_pydantic_model(domain_model)
        
        # 매핑 검증
        mapping_validation = self.validate_field_mapping(
            actual_fields,
            api_model_info,
            domain_model_info
        )
        
        # 실제 데이터로 모델 인스턴스 생성 테스트
        instantiation_test = self.test_model_instantiation(
            response_data.get("data", []),
            api_model,
            domain_model
        )
        
        return {
            "endpoint": endpoint_name,
            "actual_fields": sorted(list(actual_fields)),
            "api_model_info": api_model_info,
            "domain_model_info": domain_model_info,
            "mapping_validation": mapping_validation,
            "instantiation_test": instantiation_test
        }
    
    def analyze_pydantic_model(self, model_class: type) -> Dict[str, Any]:
        """Pydantic 모델 분석"""
        if not hasattr(model_class, '__fields__') and not hasattr(model_class, 'model_fields'):
            return {"error": "Not a valid Pydantic model"}
        
        # Pydantic V2 호환성
        if hasattr(model_class, 'model_fields'):
            fields = model_class.model_fields
        else:
            fields = model_class.__fields__
        
        field_info = {}
        aliases = {}
        
        for field_name, field_def in fields.items():
            # 필드 정보 추출
            info = {
                "type": str(field_def.annotation if hasattr(field_def, 'annotation') else field_def.type_),
                "required": True,  # 기본값
                "default": None
            }
            
            # Pydantic V2 방식
            if hasattr(field_def, 'alias'):
                alias = field_def.alias
                if alias:
                    aliases[field_name] = alias
                    info["alias"] = alias
            
            # Pydantic V1 방식 (fallback)
            elif hasattr(field_def, 'field_info') and hasattr(field_def.field_info, 'alias'):
                alias = field_def.field_info.alias
                if alias:
                    aliases[field_name] = alias
                    info["alias"] = alias
            
            field_info[field_name] = info
        
        return {
            "model_name": model_class.__name__,
            "total_fields": len(field_info),
            "fields": field_info,
            "aliases": aliases
        }
    
    def validate_field_mapping(
        self,
        actual_fields: Set[str],
        api_model_info: Dict[str, Any],
        domain_model_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """필드 매핑 검증"""
        
        # API 모델의 alias 매핑 확인
        api_aliases = api_model_info.get("aliases", {})
        api_field_names = set(api_model_info.get("fields", {}).keys())
        
        # 실제 필드와 API 모델 alias 비교
        missing_in_model = actual_fields - set(api_aliases.values()) - api_field_names
        missing_in_actual = set(api_aliases.values()) - actual_fields
        
        # 도메인 모델과 API 모델 필드 비교
        domain_field_names = set(domain_model_info.get("fields", {}).keys())
        api_to_domain_gaps = api_field_names - domain_field_names
        domain_to_api_gaps = domain_field_names - api_field_names
        
        return {
            "api_model_coverage": {
                "covered_fields": len(actual_fields) - len(missing_in_model),
                "total_actual_fields": len(actual_fields),
                "coverage_percentage": ((len(actual_fields) - len(missing_in_model)) / len(actual_fields) * 100) if actual_fields else 0
            },
            "missing_in_model": sorted(list(missing_in_model)),
            "missing_in_actual": sorted(list(missing_in_actual)),
            "api_to_domain_gaps": sorted(list(api_to_domain_gaps)),
            "domain_to_api_gaps": sorted(list(domain_to_api_gaps)),
            "alias_mappings": api_aliases
        }
    
    def test_model_instantiation(
        self,
        data_items: List[Dict[str, Any]],
        api_model: type,
        domain_model: type
    ) -> Dict[str, Any]:
        """모델 인스턴스 생성 테스트"""
        
        if not data_items:
            return {"error": "No data items to test"}
        
        test_results = {
            "api_model_test": {"success": 0, "failed": 0, "errors": []},
            "domain_model_test": {"success": 0, "failed": 0, "errors": []}
        }
        
        for i, item in enumerate(data_items[:3]):  # 처음 3개 아이템만 테스트
            # API 모델 테스트
            try:
                api_instance = api_model(**item)
                test_results["api_model_test"]["success"] += 1
            except Exception as e:
                test_results["api_model_test"]["failed"] += 1
                test_results["api_model_test"]["errors"].append({
                    "item_index": i,
                    "error": str(e)
                })
            
            # 도메인 모델 테스트 (API 모델 필드를 도메인 모델에 맞게 변환)
            try:
                # 간단한 필드 매핑 (실제 변환 로직은 서비스 계층에서 수행)
                domain_data = self.convert_api_to_domain_data(item, api_model, domain_model)
                domain_instance = domain_model(**domain_data)
                test_results["domain_model_test"]["success"] += 1
            except Exception as e:
                test_results["domain_model_test"]["failed"] += 1
                test_results["domain_model_test"]["errors"].append({
                    "item_index": i,
                    "error": str(e)
                })
        
        return test_results
    
    def convert_api_to_domain_data(
        self, 
        api_data: Dict[str, Any], 
        api_model: type, 
        domain_model: type
    ) -> Dict[str, Any]:
        """API 데이터를 도메인 모델 형태로 변환 (간단한 매핑)"""
        
        # 기본적인 필드 매핑
        domain_data = {}
        
        # 공통 필드들 매핑
        field_mappings = {
            "id": "id",
            "title": "title",
            "announcement_id": "id",
            "business_name": "title",
            "content": "content",
            "start_date": "created_at",
            "register_date": "created_at",
            "detail_page_url": "source_url"
        }
        
        for api_field, domain_field in field_mappings.items():
            if api_field in api_data and api_data[api_field] is not None:
                domain_data[domain_field] = api_data[api_field]
        
        # 필수 필드가 없는 경우 기본값 설정
        if "id" not in domain_data:
            domain_data["id"] = api_data.get("announcement_id", api_data.get("id", "test_id"))
        
        if "title" not in domain_data:
            domain_data["title"] = api_data.get("title", api_data.get("business_name", "Test Title"))
        
        if "created_at" not in domain_data:
            from datetime import datetime
            domain_data["created_at"] = datetime.now()
        
        return domain_data
    
    def save_validation_results(self):
        """검증 결과 저장"""
        
        # JSON 형태로 상세 결과 저장
        results_file = VALIDATION_OUTPUT_DIR / "field_mapping_validation_detailed.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, ensure_ascii=False, indent=2, default=str)
        
        # 마크다운 리포트 생성
        self.generate_validation_report()
        
        logger.info(f"Validation results saved to {VALIDATION_OUTPUT_DIR}")
    
    def generate_validation_report(self):
        """검증 리포트 생성"""
        
        report_lines = [
            "# K-Startup API 필드 매핑 검증 리포트",
            "",
            f"검증 일시: {self._get_current_timestamp()}",
            "",
            "## 📋 검증 개요",
            "",
            f"- 검증된 엔드포인트: {len(self.validation_results)}개",
            "- 검증 범위: API 응답 ↔ API 모델 ↔ 도메인 모델",
            "",
        ]
        
        # 전체 요약
        total_coverage = 0
        total_endpoints = 0
        
        for endpoint, validation in self.validation_results.items():
            if "mapping_validation" in validation:
                coverage = validation["mapping_validation"]["api_model_coverage"]["coverage_percentage"]
                total_coverage += coverage
                total_endpoints += 1
        
        avg_coverage = total_coverage / total_endpoints if total_endpoints > 0 else 0
        
        report_lines.extend([
            "### 📊 전체 통계",
            "",
            f"- 평균 필드 커버리지: {avg_coverage:.1f}%",
            f"- 검증 상태: {'✅ 양호' if avg_coverage >= 80 else '⚠️ 개선 필요' if avg_coverage >= 60 else '❌ 심각'}",
            ""
        ])
        
        # 엔드포인트별 상세 분석
        for endpoint, validation in self.validation_results.items():
            report_lines.extend([
                f"## 🔍 {endpoint.title()} 엔드포인트 검증",
                ""
            ])
            
            # 필드 커버리지
            if "mapping_validation" in validation:
                mapping = validation["mapping_validation"]
                coverage = mapping["api_model_coverage"]
                
                report_lines.extend([
                    "### 📈 필드 커버리지",
                    "",
                    f"- 전체 실제 필드: {coverage['total_actual_fields']}개",
                    f"- 모델에서 지원: {coverage['covered_fields']}개",
                    f"- 커버리지: {coverage['coverage_percentage']:.1f}%",
                    ""
                ])
                
                # 누락된 필드
                if mapping.get("missing_in_model"):
                    report_lines.extend([
                        "#### ❌ 모델에 누락된 필드",
                        ""
                    ])
                    for field in mapping["missing_in_model"]:
                        report_lines.append(f"- `{field}`")
                    report_lines.append("")
                
                # 실제 데이터에 없는 필드
                if mapping.get("missing_in_actual"):
                    report_lines.extend([
                        "#### ⚠️ 실제 데이터에 없는 필드",
                        ""
                    ])
                    for field in mapping["missing_in_actual"]:
                        report_lines.append(f"- `{field}`")
                    report_lines.append("")
            
            # 모델 인스턴스 생성 테스트
            if "instantiation_test" in validation:
                test_result = validation["instantiation_test"]
                
                if "error" not in test_result:
                    api_test = test_result["api_model_test"]
                    domain_test = test_result["domain_model_test"]
                    
                    report_lines.extend([
                        "### 🧪 모델 인스턴스 생성 테스트",
                        "",
                        f"#### API 모델 ({validation['api_model_info']['model_name']})",
                        f"- 성공: {api_test['success']}건",
                        f"- 실패: {api_test['failed']}건",
                    ])
                    
                    if api_test["errors"]:
                        report_lines.append("- 오류:")
                        for error in api_test["errors"]:
                            report_lines.append(f"  - Item {error['item_index']}: {error['error']}")
                    
                    report_lines.extend([
                        "",
                        f"#### 도메인 모델 ({validation['domain_model_info']['model_name']})",
                        f"- 성공: {domain_test['success']}건",
                        f"- 실패: {domain_test['failed']}건",
                    ])
                    
                    if domain_test["errors"]:
                        report_lines.append("- 오류:")
                        for error in domain_test["errors"]:
                            report_lines.append(f"  - Item {error['item_index']}: {error['error']}")
                    
                    report_lines.append("")
            
            # 별칭 매핑 정보
            if "mapping_validation" in validation and validation["mapping_validation"].get("alias_mappings"):
                aliases = validation["mapping_validation"]["alias_mappings"]
                report_lines.extend([
                    "### 🔗 필드 별칭 매핑",
                    "",
                    "| 모델 필드 | API 필드 (alias) |",
                    "|-----------|------------------|"
                ])
                
                for model_field, api_field in aliases.items():
                    report_lines.append(f"| {model_field} | {api_field} |")
                
                report_lines.append("")
        
        # 권장사항
        report_lines.extend([
            "## 💡 권장사항",
            "",
            "### 즉시 개선 필요",
        ])
        
        # 커버리지 낮은 엔드포인트 식별
        low_coverage_endpoints = []
        for endpoint, validation in self.validation_results.items():
            if "mapping_validation" in validation:
                coverage = validation["mapping_validation"]["api_model_coverage"]["coverage_percentage"]
                if coverage < 80:
                    low_coverage_endpoints.append((endpoint, coverage))
        
        if low_coverage_endpoints:
            for endpoint, coverage in low_coverage_endpoints:
                report_lines.append(f"- **{endpoint}**: 필드 커버리지 {coverage:.1f}% - 누락 필드 추가 필요")
        else:
            report_lines.append("- ✅ 모든 엔드포인트의 필드 커버리지가 양호합니다")
        
        report_lines.extend([
            "",
            "### 장기 개선사항",
            "- API 응답 구조 변경 감지 자동화",
            "- 필드 매핑 테스트 자동화",
            "- 도메인 모델과 API 모델 간 변환 로직 개선",
            "- 실시간 스키마 검증 시스템 구축"
        ])
        
        # 마크다운 파일 저장
        report_file = VALIDATION_OUTPUT_DIR / "field_mapping_validation_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
    
    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """메인 실행 함수"""
    print("🔍 K-Startup API 필드 매핑 검증 시작...")
    
    # 현재 디렉토리를 프로젝트 루트로 변경
    os.chdir(Path(__file__).parent.parent)
    
    validator = FieldMappingValidator()
    validator.validate_all_mappings()
    
    print("✅ 검증 완료!")
    print(f"📄 리포트 위치: {VALIDATION_OUTPUT_DIR}")
    print(f"   - 상세 결과: field_mapping_validation_detailed.json")
    print(f"   - 검증 리포트: field_mapping_validation_report.md")


if __name__ == "__main__":
    main()