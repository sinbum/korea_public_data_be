#!/usr/bin/env python3
"""
K-Startup API 응답 데이터 분석 스크립트

실제 API 응답 데이터를 분석하여 데이터 구조, 필드 매핑, 품질을 검증합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import defaultdict, Counter
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 결과 디렉토리 경로
RESULTS_DIR = Path("tests/live/results")
ANALYSIS_OUTPUT_DIR = Path("docs/reports/api_analysis")
ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class APIResponseAnalyzer:
    """API 응답 데이터 분석기"""
    
    def __init__(self):
        self.sample_files = {
            "announcements": "announcements_basic_sample.json",
            "business": "business_basic_sample.json", 
            "content": "content_basic_sample.json",
            "statistics": "statistics_basic_sample.json"
        }
        self.analysis_results = {}
        
    def analyze_all_endpoints(self):
        """모든 엔드포인트 분석"""
        logger.info("Starting comprehensive API response analysis...")
        
        for endpoint_name, sample_file in self.sample_files.items():
            sample_path = RESULTS_DIR / sample_file
            
            if sample_path.exists():
                logger.info(f"Analyzing {endpoint_name} endpoint data...")
                analysis = self.analyze_endpoint_data(endpoint_name, sample_path)
                self.analysis_results[endpoint_name] = analysis
            else:
                logger.warning(f"Sample file not found: {sample_path}")
        
        # 종합 분석 수행
        self.perform_cross_endpoint_analysis()
        
        # 분석 결과 저장
        self.save_analysis_results()
        
        logger.info("Analysis completed successfully")
    
    def analyze_endpoint_data(self, endpoint_name: str, sample_path: Path) -> Dict[str, Any]:
        """개별 엔드포인트 데이터 분석"""
        with open(sample_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = {
            "endpoint": endpoint_name,
            "metadata": self.analyze_metadata(data),
            "data_structure": self.analyze_data_structure(data),
            "field_analysis": self.analyze_fields(data.get("data", [])),
            "data_quality": self.analyze_data_quality(data.get("data", [])),
            "sample_count": len(data.get("data", []))
        }
        
        return analysis
    
    def analyze_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 분석"""
        metadata_fields = ["current_count", "match_count", "page", "per_page", "total_count"]
        metadata = {}
        
        for field in metadata_fields:
            if field in data:
                metadata[field] = {
                    "value": data[field],
                    "type": type(data[field]).__name__
                }
        
        return metadata
    
    def analyze_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 구조 분석"""
        structure = {
            "root_keys": list(data.keys()),
            "has_data_array": "data" in data and isinstance(data["data"], list),
            "data_array_length": len(data.get("data", [])),
            "pagination_present": any(key in data for key in ["page", "per_page", "total_count"])
        }
        
        if structure["has_data_array"] and data["data"]:
            first_item = data["data"][0]
            structure["item_fields"] = list(first_item.keys()) if isinstance(first_item, dict) else []
            structure["item_field_count"] = len(structure["item_fields"])
        
        return structure
    
    def analyze_fields(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """필드 분석"""
        if not data_items:
            return {"error": "No data items to analyze"}
        
        all_fields = set()
        field_types = defaultdict(Counter)
        field_presence = defaultdict(int)
        field_lengths = defaultdict(list)
        null_counts = defaultdict(int)
        
        for item in data_items:
            if not isinstance(item, dict):
                continue
                
            all_fields.update(item.keys())
            
            for field, value in item.items():
                field_presence[field] += 1
                
                if value is None or value == "":
                    null_counts[field] += 1
                else:
                    field_types[field][type(value).__name__] += 1
                    
                    if isinstance(value, str):
                        field_lengths[field].append(len(value))
        
        # 필드별 통계 계산
        field_stats = {}
        for field in all_fields:
            stats = {
                "presence_rate": field_presence[field] / len(data_items) * 100,
                "null_rate": null_counts[field] / len(data_items) * 100,
                "types": dict(field_types[field]),
                "most_common_type": field_types[field].most_common(1)[0][0] if field_types[field] else "null"
            }
            
            if field_lengths[field]:
                stats["string_length_stats"] = {
                    "min": min(field_lengths[field]),
                    "max": max(field_lengths[field]),
                    "avg": sum(field_lengths[field]) / len(field_lengths[field])
                }
            
            field_stats[field] = stats
        
        return {
            "total_unique_fields": len(all_fields),
            "field_statistics": field_stats,
            "all_fields": sorted(list(all_fields))
        }
    
    def analyze_data_quality(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터 품질 분석"""
        if not data_items:
            return {"error": "No data items to analyze"}
        
        quality_issues = []
        
        # 중복 검사 (ID 기준)
        ids = []
        for item in data_items:
            if isinstance(item, dict):
                item_id = item.get("announcement_id") or item.get("business_id") or item.get("id")
                if item_id:
                    ids.append(str(item_id))
        
        duplicate_ids = [item_id for item_id, count in Counter(ids).items() if count > 1]
        if duplicate_ids:
            quality_issues.append(f"Duplicate IDs found: {duplicate_ids}")
        
        # 필수 필드 검사
        required_fields_by_type = {
            "announcements": ["announcement_id", "title", "start_date", "end_date"],
            "business": ["business_id", "business_name"],
            "content": ["title"],
            "statistics": ["title"]
        }
        
        # 필드 완성도 검사
        field_completeness = {}
        for item in data_items:
            if isinstance(item, dict):
                for field, value in item.items():
                    if field not in field_completeness:
                        field_completeness[field] = {"filled": 0, "total": 0}
                    
                    field_completeness[field]["total"] += 1
                    if value is not None and value != "":
                        field_completeness[field]["filled"] += 1
        
        # 완성도 낮은 필드 식별
        low_completeness_fields = []
        for field, stats in field_completeness.items():
            completeness = stats["filled"] / stats["total"] * 100
            if completeness < 50:  # 50% 미만 완성도
                low_completeness_fields.append({
                    "field": field,
                    "completeness": completeness
                })
        
        return {
            "total_items_analyzed": len(data_items),
            "duplicate_ids": duplicate_ids,
            "quality_issues": quality_issues,
            "field_completeness": field_completeness,
            "low_completeness_fields": low_completeness_fields
        }
    
    def perform_cross_endpoint_analysis(self):
        """엔드포인트 간 교차 분석"""
        logger.info("Performing cross-endpoint analysis...")
        
        # 공통 필드 찾기
        all_endpoint_fields = {}
        for endpoint, analysis in self.analysis_results.items():
            if "field_analysis" in analysis:
                all_endpoint_fields[endpoint] = set(analysis["field_analysis"].get("all_fields", []))
        
        common_fields = set.intersection(*all_endpoint_fields.values()) if all_endpoint_fields else set()
        
        # 데이터 구조 일관성 검사
        structure_consistency = {}
        for endpoint, analysis in self.analysis_results.items():
            if "data_structure" in analysis:
                structure = analysis["data_structure"]
                structure_consistency[endpoint] = {
                    "has_pagination": structure.get("pagination_present", False),
                    "has_data_array": structure.get("has_data_array", False),
                    "field_count": structure.get("item_field_count", 0)
                }
        
        self.analysis_results["cross_endpoint_analysis"] = {
            "common_fields": sorted(list(common_fields)),
            "structure_consistency": structure_consistency,
            "total_endpoints_analyzed": len(self.analysis_results)
        }
    
    def save_analysis_results(self):
        """분석 결과 저장"""
        # JSON 형태로 상세 결과 저장
        results_file = ANALYSIS_OUTPUT_DIR / "api_response_analysis_detailed.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)
        
        # 마크다운 리포트 생성
        self.generate_markdown_report()
        
        logger.info(f"Analysis results saved to {ANALYSIS_OUTPUT_DIR}")
    
    def generate_markdown_report(self):
        """마크다운 형태의 분석 리포트 생성"""
        report_lines = [
            "# K-Startup API 응답 데이터 분석 리포트",
            "",
            f"분석 일시: {self._get_current_timestamp()}",
            "",
            "## 📊 개요",
            "",
            f"- 분석된 엔드포인트 수: {len([k for k in self.analysis_results.keys() if k != 'cross_endpoint_analysis'])}",
            f"- 총 샘플 데이터: {sum(analysis.get('sample_count', 0) for analysis in self.analysis_results.values() if isinstance(analysis.get('sample_count'), int))}개",
            ""
        ]
        
        # 엔드포인트별 분석 결과
        for endpoint, analysis in self.analysis_results.items():
            if endpoint == "cross_endpoint_analysis":
                continue
                
            report_lines.extend([
                f"## 🔍 {endpoint.title()} 엔드포인트 분석",
                "",
                "### 메타데이터",
                ""
            ])
            
            if "metadata" in analysis:
                for field, info in analysis["metadata"].items():
                    report_lines.append(f"- **{field}**: {info['value']} ({info['type']})")
                report_lines.append("")
            
            # 데이터 구조
            if "data_structure" in analysis:
                structure = analysis["data_structure"]
                report_lines.extend([
                    "### 데이터 구조",
                    "",
                    f"- 루트 키: {', '.join(structure.get('root_keys', []))}",
                    f"- 데이터 배열 존재: {'✅' if structure.get('has_data_array') else '❌'}",
                    f"- 페이지네이션 지원: {'✅' if structure.get('pagination_present') else '❌'}",
                    f"- 아이템당 필드 수: {structure.get('item_field_count', 0)}개",
                    ""
                ])
            
            # 필드 분석
            if "field_analysis" in analysis and "field_statistics" in analysis["field_analysis"]:
                report_lines.extend([
                    "### 주요 필드 분석",
                    "",
                    "| 필드명 | 완성도 | 주요 타입 | 비고 |",
                    "|--------|--------|----------|------|"
                ])
                
                field_stats = analysis["field_analysis"]["field_statistics"]
                for field, stats in sorted(field_stats.items())[:10]:  # 상위 10개 필드만 표시
                    presence_rate = f"{stats['presence_rate']:.1f}%"
                    main_type = stats['most_common_type']
                    
                    note = ""
                    if stats['null_rate'] > 50:
                        note = "⚠️ 높은 NULL 비율"
                    elif stats['null_rate'] == 0:
                        note = "✅ 완전"
                    
                    report_lines.append(f"| {field} | {presence_rate} | {main_type} | {note} |")
                
                report_lines.append("")
            
            # 데이터 품질
            if "data_quality" in analysis:
                quality = analysis["data_quality"]
                report_lines.extend([
                    "### 데이터 품질",
                    "",
                    f"- 분석된 아이템 수: {quality.get('total_items_analyzed', 0)}개",
                    f"- 중복 ID: {len(quality.get('duplicate_ids', []))}개",
                    f"- 품질 이슈: {len(quality.get('quality_issues', []))}개",
                    ""
                ])
                
                if quality.get('low_completeness_fields'):
                    report_lines.extend([
                        "#### 완성도 낮은 필드 (50% 미만)",
                        ""
                    ])
                    for field_info in quality['low_completeness_fields'][:5]:  # 상위 5개만
                        report_lines.append(f"- **{field_info['field']}**: {field_info['completeness']:.1f}%")
                    report_lines.append("")
        
        # 교차 분석 결과
        if "cross_endpoint_analysis" in self.analysis_results:
            cross_analysis = self.analysis_results["cross_endpoint_analysis"]
            report_lines.extend([
                "## 🔄 엔드포인트 간 교차 분석",
                "",
                f"### 공통 필드 ({len(cross_analysis.get('common_fields', []))}개)",
                ""
            ])
            
            if cross_analysis.get('common_fields'):
                for field in cross_analysis['common_fields']:
                    report_lines.append(f"- `{field}`")
                report_lines.append("")
            
            # 구조 일관성
            if cross_analysis.get('structure_consistency'):
                report_lines.extend([
                    "### 구조 일관성",
                    "",
                    "| 엔드포인트 | 페이지네이션 | 데이터 배열 | 필드 수 |",
                    "|------------|--------------|-------------|---------|"
                ])
                
                for endpoint, consistency in cross_analysis['structure_consistency'].items():
                    pagination = "✅" if consistency.get('has_pagination') else "❌"
                    data_array = "✅" if consistency.get('has_data_array') else "❌"
                    field_count = consistency.get('field_count', 0)
                    
                    report_lines.append(f"| {endpoint} | {pagination} | {data_array} | {field_count} |")
                
                report_lines.append("")
        
        # 권장사항
        report_lines.extend([
            "## 💡 권장사항",
            "",
            "### 데이터 품질 개선",
            "- NULL 값이 많은 필드에 대한 데이터 보완 검토",
            "- 중복 데이터 정리 프로세스 구축",
            "- 필수 필드 검증 로직 강화",
            "",
            "### API 일관성 향상", 
            "- 모든 엔드포인트에서 동일한 페이지네이션 구조 사용",
            "- 공통 메타데이터 필드 표준화",
            "- 응답 형식 통일화",
            "",
            "### 모니터링 및 검증",
            "- 정기적인 데이터 품질 검증",
            "- API 응답 구조 변경 감지 시스템",
            "- 실시간 데이터 완성도 모니터링"
        ])
        
        # 마크다운 파일 저장
        report_file = ANALYSIS_OUTPUT_DIR / "api_response_analysis_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
    
    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """메인 실행 함수"""
    print("🔍 K-Startup API 응답 데이터 분석 시작...")
    
    # 현재 디렉토리를 프로젝트 루트로 변경
    os.chdir(Path(__file__).parent.parent)
    
    analyzer = APIResponseAnalyzer()
    analyzer.analyze_all_endpoints()
    
    print("✅ 분석 완료!")
    print(f"📄 리포트 위치: {ANALYSIS_OUTPUT_DIR}")
    print(f"   - 상세 결과: api_response_analysis_detailed.json")
    print(f"   - 요약 리포트: api_response_analysis_report.md")


if __name__ == "__main__":
    main()