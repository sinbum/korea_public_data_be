"""
Pytest configuration and shared fixtures.

Provides common test setup, fixtures, and utilities.
"""

import os
import sys
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
import httpx
from datetime import datetime
from pathlib import Path

# Configure test environment before importing app modules
os.environ.setdefault('ENV_FILE', str(Path(__file__).parent / '.env.test'))
os.environ.setdefault('TESTING', '1')

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.shared.clients.strategies import GovernmentAPIKeyStrategy
from app.core.interfaces.retry_strategies import ExponentialBackoffStrategy
from app.shared.models.kstartup import (
    AnnouncementItem,
    BusinessItem,
    ContentItem,
    StatisticalItem
)
from app.core.container import get_container
from app.domains.users.service import UserService
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment configuration"""
    # Ensure test environment variables are set
    test_env = {
        'MONGODB_URL': 'mongodb://localhost:27017',
        'DATABASE_NAME': 'korea_public_api_test',
        'JWT_SECRET_KEY': 'test_jwt_secret_key_for_testing_minimum_32_chars_long_abcdef123456',
        'PUBLIC_DATA_API_KEY': 'test_api_key_minimum_32_characters_long',
        'REDIS_URL': 'redis://localhost:6379/1',
        'DEBUG': 'true',
        'TESTING': '1'
    }
    
    for key, value in test_env.items():
        os.environ.setdefault(key, value)
    
    # Initialize DI container with test services
    container = get_container()
    
    # Register test database
    mock_db = Mock()
    mock_db.__getitem__ = Mock(return_value=Mock())  # Mock collection access
    container.register_instance(AsyncIOMotorClient, Mock())
    
    # Register UserService
    mock_user_service = Mock(spec=UserService)
    mock_user_service.register_local_user = AsyncMock()
    mock_user_service.login_local_user = AsyncMock()
    mock_user_service.get_current_user = AsyncMock()
    mock_user_service.refresh_token = AsyncMock()
    mock_user_service.logout = AsyncMock()
    mock_user_service.google_oauth_login = AsyncMock()
    container.register_instance(UserService, mock_user_service)
    
    yield
    
    # Cleanup if needed
    # Clear singleton instances if any
    container._singletons.clear() if hasattr(container, '_singletons') else None


@pytest.fixture
def mock_api_key():
    """Mock API key for testing (meets minimum length requirements)"""
    return "test_api_key_minimum_32_characters_long"


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses"""
    def _create_response(
        status_code: int = 200,
        content: str = "",
        headers: Optional[Dict[str, str]] = None
    ):
        response = Mock(spec=httpx.Response)
        response.status_code = status_code
        response.text = content
        response.content = content.encode()
        response.headers = headers or {}
        return response
    
    return _create_response


@pytest.fixture
def sample_announcement_xml():
    """Sample XML response for announcement API"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<response>
    <currentCount>2</currentCount>
    <matchCount>2</matchCount>
    <page>1</page>
    <perPage>10</perPage>
    <totalCount>2</totalCount>
    <data>
        <item>
            <col name="pbanc_no">A2024001</col>
            <col name="pbanc_titl_nm">창업도약패키지 사업공고</col>
            <col name="pbanc_de">20240115</col>
            <col name="reqst_bgng_ymd">20240201</col>
            <col name="reqst_end_ymd">20240229</col>
            <col name="biz_category_cd">cmrczn_Tab3</col>
            <col name="supt_biz_titl_nm">창업도약패키지</col>
            <col name="excutr_instt_nm">창업진흥원</col>
            <col name="relm_url">http://www.k-startup.go.kr</col>
        </item>
        <item>
            <col name="pbanc_no">A2024002</col>
            <col name="pbanc_titl_nm">예비창업패키지 사업공고</col>
            <col name="pbanc_de">20240120</col>
            <col name="reqst_bgng_ymd">20240301</col>
            <col name="reqst_end_ymd">20240331</col>
            <col name="biz_category_cd">cmrczn_Tab2</col>
            <col name="supt_biz_titl_nm">예비창업패키지</col>
            <col name="excutr_instt_nm">창업진흥원</col>
            <col name="relm_url">http://www.k-startup.go.kr</col>
        </item>
    </data>
</response>"""


@pytest.fixture
def sample_announcement_json():
    """Sample JSON response for announcement API"""
    return {
        "response": {
            "body": {
                "currentCount": 2,
                "matchCount": 2,
                "pageNo": 1,
                "numOfRows": 10,
                "totalCount": 2,
                "items": [
                    {
                        "pbanc_no": "A2024001",
                        "pbanc_titl_nm": "창업도약패키지 사업공고",
                        "pbanc_de": "20240115",
                        "reqst_bgng_ymd": "20240201",
                        "reqst_end_ymd": "20240229",
                        "biz_category_cd": "cmrczn_Tab3",
                        "supt_biz_titl_nm": "창업도약패키지",
                        "excutr_instt_nm": "창업진흥원",
                        "relm_url": "k-startup.go.kr"
                    },
                    {
                        "pbanc_no": "A2024002", 
                        "pbanc_titl_nm": "예비창업패키지 사업공고",
                        "pbanc_de": "20240120",
                        "reqst_bgng_ymd": "20240301",
                        "reqst_end_ymd": "20240331",
                        "biz_category_cd": "cmrczn_Tab2",
                        "supt_biz_titl_nm": "예비창업패키지",
                        "excutr_instt_nm": "창업진흥원",
                        "relm_url": "k-startup.go.kr"
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_business_data():
    """Sample business information data"""
    return {
        "currentCount": 1,
        "matchCount": 1,
        "page": 1,
        "perPage": 10,
        "totalCount": 1,
        "data": [
            {
                "biz_no": "B2024001",
                "supt_biz_titl_nm": "창업도약패키지",
                "biz_cn": "성장단계 창업기업 지원사업",
                "biz_category_cd": "cmrczn_Tab3",
                "biz_field_nm": "창업사업화",
                "biz_supt_trgt_info": "창업 3-7년 기업",
                "supt_cn": "사업화 자금 지원",
                "supt_scl_info": "최대 2억원",
                "excutr_instt_nm": "창업진흥원",
                "excutr_instt_se_nm": "공공기관",
                "qustnr_info": "02-123-4567",
                "hmpg_url": "http://www.k-startup.go.kr",
                "relm_url": "http://www.k-startup.go.kr/business"
            }
        ]
    }


@pytest.fixture
def sample_content_data():
    """Sample content information data"""
    return {
        "currentCount": 1,
        "matchCount": 1,
        "page": 1,
        "perPage": 10,
        "totalCount": 1,
        "data": [
            {
                "cn_no": "C2024001",
                "cn_titl_nm": "2024년 창업 트렌드",
                "cn_cn": "올해 창업 트렌드 분석 내용",
                "cn_smry": "2024년 주요 창업 동향",
                "cn_se_cd": "content_Tab1",
                "ctgry_nm": "뉴스",
                "pblnt_de": "20240115",
                "updt_de": "20240116",
                "author_nm": "창업진흥원",
                "source_nm": "K-Startup",
                "relm_url": "http://www.k-startup.go.kr/news/123",
                "thmbnl_url": "http://www.k-startup.go.kr/images/thumb123.jpg"
            }
        ]
    }


@pytest.fixture
def sample_statistics_data():
    """Sample statistics information data"""
    return {
        "currentCount": 1,
        "matchCount": 1,
        "page": 1,
        "perPage": 10,
        "totalCount": 1,
        "data": [
            {
                "stats_no": "S2024001",
                "stats_titl_nm": "월별 창업기업 수",
                "stats_cn": "2024년 1월 창업기업 통계",
                "trgt_year": "2024",
                "trgt_month": "1",
                "stats_vl": "1250",
                "unt_nm": "개",
                "ctgry_nm": "창업통계",
                "subctgry_nm": "월별통계",
                "source_nm": "중소벤처기업부",
                "ref_de": "20240131"
            }
        ]
    }


@pytest.fixture
def mock_kstartup_client(mock_api_key):
    """Mock K-Startup API client with enhanced test setup"""
    with patch('app.core.config.settings.public_data_api_key', mock_api_key):
        client = KStartupAPIClient(api_key=mock_api_key)
        return client


@pytest.fixture
def mock_async_client():
    """Mock async httpx client"""
    mock_client = AsyncMock()
    mock_client.request = AsyncMock()
    return mock_client


@pytest.fixture
def error_response_scenarios():
    """Various error response scenarios for testing"""
    return {
        "timeout": httpx.TimeoutException("Request timed out"),
        "connection_error": httpx.ConnectError("Connection failed"),
        "http_400": (400, "Bad Request"),
        "http_401": (401, "Unauthorized"),
        "http_403": (403, "Forbidden"),
        "http_404": (404, "Not Found"),
        "http_429": (429, "Too Many Requests"),
        "http_500": (500, "Internal Server Error"),
        "http_502": (502, "Bad Gateway"),
        "http_503": (503, "Service Unavailable")
    }


@pytest.fixture
def performance_test_config():
    """Configuration for performance tests"""
    return {
        "concurrent_requests": 10,
        "total_requests": 100,
        "target_response_time_ms": 2000,
        "memory_threshold_mb": 100,
        "error_rate_threshold": 0.05  # 5% error rate threshold
    }


# Custom markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration  
pytest.mark.performance = pytest.mark.performance
pytest.mark.asyncio_test = pytest.mark.asyncio