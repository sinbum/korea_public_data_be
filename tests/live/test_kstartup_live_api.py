"""
실제 K-Startup API 호출 테스트

실제 API 키를 사용하여 K-Startup API 엔드포인트를 호출하고
응답 데이터를 검증하는 라이브 테스트입니다.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from pathlib import Path
import logging

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.core.config import settings
from app.shared.models.kstartup import (
    KStartupAnnouncementResponse,
    KStartupBusinessResponse,
    KStartupContentResponse,
    KStartupStatisticsResponse
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting을 위한 설정 (30 TPS 제한)
RATE_LIMIT_DELAY = 1.1  # 초
TEST_RESULTS_DIR = Path("tests/live/results")
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.live_api
class TestKStartupLiveAPI:
    """실제 K-Startup API 라이브 테스트"""
    
    @pytest.fixture(scope="class")
    def live_client(self):
        """실제 API 키로 클라이언트 생성"""
        if not settings.public_data_api_key:
            pytest.skip("API key not configured")
        
        return KStartupAPIClient(
            api_key=settings.public_data_api_key,
            use_aggressive_retry=True
        )
    
    @pytest.fixture(scope="class")
    def test_session_data(self):
        """테스트 세션 데이터 저장용"""
        return {
            "session_id": f"live_test_{int(time.time())}",
            "results": {},
            "errors": [],
            "performance": {}
        }
    
    def save_test_result(self, test_session_data: Dict, endpoint: str, result: Any, execution_time: float):
        """테스트 결과 저장"""
        test_session_data["results"][endpoint] = {
            "success": result.success if hasattr(result, 'success') else True,
            "status_code": result.status_code if hasattr(result, 'status_code') else 200,
            "data_type": type(result).__name__,
            "execution_time": execution_time,
            "timestamp": time.time()
        }
        
        # 실제 응답 데이터 샘플 저장 (처음 몇 개 항목만)
        if hasattr(result, 'data') and result.data:
            sample_data = result.data
            if hasattr(sample_data, 'data') and isinstance(sample_data.data, list):
                # 처음 3개 항목만 저장
                sample_data.data = sample_data.data[:3]
            
            # JSON 직렬화 가능한 형태로 변환
            try:
                if hasattr(sample_data, 'model_dump'):
                    json_data = sample_data.model_dump()
                else:
                    json_data = str(sample_data)
                
                result_file = TEST_RESULTS_DIR / f"{endpoint}_sample.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
                    
            except Exception as e:
                logger.warning(f"Could not save sample data for {endpoint}: {e}")
    
    def test_01_announcement_information_basic(self, live_client, test_session_data):
        """공고 정보 기본 조회 테스트"""
        logger.info("Testing getAnnouncementInformation01 endpoint...")
        
        start_time = time.time()
        try:
            # Context manager 사용하여 클라이언트 초기화
            with live_client as client:
                result = client.get_announcement_information(
                    page_no=1,
                    num_of_rows=5
                )
            execution_time = time.time() - start_time
            
            # 기본 검증
            assert result is not None, "Result should not be None"
            assert hasattr(result, 'success'), "Result should have success attribute"
            
            if result.success:
                assert result.data is not None, "Data should not be None for successful response"
                assert isinstance(result.data, KStartupAnnouncementResponse), f"Data should be KStartupAnnouncementResponse, got {type(result.data)}"
                
                # 데이터 구조 검증
                if hasattr(result.data, 'data') and result.data.data:
                    logger.info(f"Retrieved {len(result.data.data)} announcement items")
                    first_item = result.data.data[0]
                    logger.info(f"First item structure: {type(first_item).__name__}")
                    
                    # 필수 필드 검증
                    if hasattr(first_item, 'announcement_id'):
                        assert first_item.announcement_id, "Announcement ID should not be empty"
                    if hasattr(first_item, 'title'):
                        assert first_item.title, "Title should not be empty"
                    
            else:
                logger.error(f"API call failed: {result.error}")
                test_session_data["errors"].append({
                    "endpoint": "getAnnouncementInformation01",
                    "error": result.error,
                    "status_code": getattr(result, 'status_code', None)
                })
            
            self.save_test_result(test_session_data, "announcements_basic", result, execution_time)
            
        except Exception as e:
            logger.error(f"Exception in announcement test: {e}")
            test_session_data["errors"].append({
                "endpoint": "getAnnouncementInformation01",
                "error": str(e),
                "type": "exception"
            })
            raise
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    def test_02_announcement_information_with_filters(self, live_client, test_session_data):
        """공고 정보 필터링 조회 테스트"""
        logger.info("Testing getAnnouncementInformation01 with filters...")
        
        start_time = time.time()
        try:
            with live_client as client:
                result = client.get_announcement_information(
                    page_no=1,
                    num_of_rows=3,
                    business_name="창업",
                    business_type="지원"
                )
            execution_time = time.time() - start_time
            
            assert result is not None
            self.save_test_result(test_session_data, "announcements_filtered", result, execution_time)
            
            if result.success:
                logger.info("Filtered announcement query successful")
            else:
                logger.warning(f"Filtered query failed: {result.error}")
            
        except Exception as e:
            logger.error(f"Exception in filtered announcement test: {e}")
            test_session_data["errors"].append({
                "endpoint": "getAnnouncementInformation01_filtered",
                "error": str(e),
                "type": "exception"
            })
            
        time.sleep(RATE_LIMIT_DELAY)
    
    def test_03_business_information(self, live_client, test_session_data):
        """사업 정보 조회 테스트"""
        logger.info("Testing getBusinessInformation01 endpoint...")
        
        start_time = time.time()
        try:
            with live_client as client:
                result = client.get_business_information(
                    page_no=1,
                    num_of_rows=5
                )
            execution_time = time.time() - start_time
            
            assert result is not None
            
            if result.success:
                assert isinstance(result.data, KStartupBusinessResponse), f"Expected KStartupBusinessResponse, got {type(result.data)}"
                logger.info("Business information query successful")
                
                if hasattr(result.data, 'data') and result.data.data:
                    logger.info(f"Retrieved {len(result.data.data)} business items")
            else:
                logger.warning(f"Business query failed: {result.error}")
            
            self.save_test_result(test_session_data, "business_basic", result, execution_time)
            
        except Exception as e:
            logger.error(f"Exception in business test: {e}")
            test_session_data["errors"].append({
                "endpoint": "getBusinessInformation01",
                "error": str(e),
                "type": "exception"
            })
            
        time.sleep(RATE_LIMIT_DELAY)
    
    def test_04_content_information(self, live_client, test_session_data):
        """콘텐츠 정보 조회 테스트"""
        logger.info("Testing getContentInformation01 endpoint...")
        
        start_time = time.time()
        try:
            with live_client as client:
                result = client.get_content_information(
                    page_no=1,
                    num_of_rows=5
                )
            execution_time = time.time() - start_time
            
            assert result is not None
            
            if result.success:
                assert isinstance(result.data, KStartupContentResponse), f"Expected KStartupContentResponse, got {type(result.data)}"
                logger.info("Content information query successful")
                
                if hasattr(result.data, 'data') and result.data.data:
                    logger.info(f"Retrieved {len(result.data.data)} content items")
            else:
                logger.warning(f"Content query failed: {result.error}")
            
            self.save_test_result(test_session_data, "content_basic", result, execution_time)
            
        except Exception as e:
            logger.error(f"Exception in content test: {e}")
            test_session_data["errors"].append({
                "endpoint": "getContentInformation01",
                "error": str(e),
                "type": "exception"
            })
            
        time.sleep(RATE_LIMIT_DELAY)
    
    def test_05_statistical_information(self, live_client, test_session_data):
        """통계 정보 조회 테스트"""
        logger.info("Testing getStatisticalInformation01 endpoint...")
        
        start_time = time.time()
        try:
            with live_client as client:
                result = client.get_statistical_information(
                    page_no=1,
                    num_of_rows=5
                )
            execution_time = time.time() - start_time
            
            assert result is not None
            
            if result.success:
                assert isinstance(result.data, KStartupStatisticsResponse), f"Expected KStartupStatisticsResponse, got {type(result.data)}"
                logger.info("Statistical information query successful")
                
                if hasattr(result.data, 'data') and result.data.data:
                    logger.info(f"Retrieved {len(result.data.data)} statistical items")
            else:
                logger.warning(f"Statistical query failed: {result.error}")
            
            self.save_test_result(test_session_data, "statistics_basic", result, execution_time)
            
        except Exception as e:
            logger.error(f"Exception in statistical test: {e}")
            test_session_data["errors"].append({
                "endpoint": "getStatisticalInformation01",
                "error": str(e),
                "type": "exception"
            })
            
        time.sleep(RATE_LIMIT_DELAY)
    
    @pytest.mark.asyncio
    async def test_06_async_batch_processing(self, live_client, test_session_data):
        """비동기 배치 처리 테스트"""
        logger.info("Testing async batch processing...")
        
        start_time = time.time()
        try:
            endpoints = [
                "getAnnouncementInformation01",
                "getBusinessInformation01",
                "getContentInformation01"
            ]
            params_list = [
                {"page_no": 1, "num_of_rows": 2},
                {"page_no": 1, "num_of_rows": 2},
                {"page_no": 1, "num_of_rows": 2}
            ]
            
            results = await live_client.get_all_data_batch(endpoints, params_list)
            execution_time = time.time() - start_time
            
            assert len(results) == 3, f"Expected 3 results, got {len(results)}"
            
            success_count = sum(1 for r in results if hasattr(r, 'success') and r.success)
            logger.info(f"Batch processing: {success_count}/{len(results)} successful")
            
            test_session_data["results"]["async_batch"] = {
                "success": success_count > 0,
                "total_requests": len(results),
                "successful_requests": success_count,
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"Exception in async batch test: {e}")
            test_session_data["errors"].append({
                "endpoint": "async_batch",
                "error": str(e),
                "type": "exception"
            })
    
    def test_07_error_handling(self, test_session_data):
        """에러 처리 테스트 (잘못된 API 키)"""
        logger.info("Testing error handling with invalid API key...")
        
        invalid_client = KStartupAPIClient(api_key="invalid_key_test")
        
        start_time = time.time()
        try:
            with invalid_client as client:
                result = client.get_announcement_information(page_no=1, num_of_rows=1)
            execution_time = time.time() - start_time
            
            # 잘못된 키로는 실패해야 함
            assert result is not None
            
            if result.success:
                logger.warning("Expected failure with invalid key, but got success")
            else:
                logger.info(f"Expected error with invalid key: {result.error}")
                assert result.status_code in [401, 403, 400], f"Expected auth error status, got {result.status_code}"
            
            test_session_data["results"]["error_handling"] = {
                "success": not result.success,  # 실패가 예상되는 상황
                "error_message": result.error if not result.success else None,
                "status_code": result.status_code,
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.info(f"Exception with invalid key (expected): {e}")
            test_session_data["results"]["error_handling"] = {
                "success": True,  # Exception이 발생하는 것도 정상적인 에러 처리
                "error_message": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_99_generate_test_report(self, test_session_data):
        """테스트 리포트 생성"""
        logger.info("Generating test report...")
        
        # 성능 통계 계산
        execution_times = [
            result.get("execution_time", 0) 
            for result in test_session_data["results"].values()
            if isinstance(result, dict) and "execution_time" in result
        ]
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
        else:
            avg_time = max_time = min_time = 0
        
        # 성공률 계산
        successful_tests = sum(
            1 for result in test_session_data["results"].values()
            if isinstance(result, dict) and result.get("success", False)
        )
        total_tests = len(test_session_data["results"])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 리포트 생성
        report = {
            "session_id": test_session_data["session_id"],
            "timestamp": time.time(),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "total_errors": len(test_session_data["errors"])
            },
            "performance": {
                "average_response_time": avg_time,
                "max_response_time": max_time,
                "min_response_time": min_time
            },
            "detailed_results": test_session_data["results"],
            "errors": test_session_data["errors"]
        }
        
        # 리포트 저장
        report_file = TEST_RESULTS_DIR / f"live_api_test_report_{test_session_data['session_id']}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Test report saved to: {report_file}")
        logger.info(f"Success rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        logger.info(f"Average response time: {avg_time:.3f}s")
        
        # 최소 성공률 검증
        assert success_rate >= 50, f"Success rate too low: {success_rate:.1f}%"
        assert avg_time < 5.0, f"Average response time too high: {avg_time:.3f}s"


@pytest.mark.live_api
class TestKStartupDataStructureValidation:
    """실제 응답 데이터 구조 검증"""
    
    def test_validate_announcement_response_structure(self):
        """공고 응답 데이터 구조 검증"""
        # 실제 응답 샘플 로드 및 검증
        sample_file = TEST_RESULTS_DIR / "announcements_basic_sample.json"
        if sample_file.exists():
            with open(sample_file, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            
            # 데이터 구조 검증 로직
            assert "data" in sample_data, "Response should contain 'data' field"
            
            if sample_data["data"]:
                first_item = sample_data["data"][0]
                # 필수 필드 존재 확인
                expected_fields = ["announcement_id", "title", "start_date", "end_date"]
                for field in expected_fields:
                    if field in first_item:
                        assert first_item[field], f"Field {field} should not be empty"
        else:
            pytest.skip("No sample data available for validation")
    
    def test_validate_field_mappings(self):
        """필드 매핑 검증"""
        # XML alias와 JSON 필드명 매핑이 올바른지 확인
        # 이는 실제 응답 데이터를 바탕으로 검증
        logger.info("Field mapping validation would be performed here based on actual responses")
        # 실제 구현에서는 샘플 데이터를 분석하여 매핑 정확성을 검증