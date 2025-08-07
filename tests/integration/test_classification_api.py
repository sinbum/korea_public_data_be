"""
Integration tests for /api/v1/classification REST APIs.

Covers health, business/content categories, validation, search, type-detect,
codes, recommendations, statistics, cache, and reference endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/v1/classification/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ["healthy", "unhealthy"]
    assert "timestamp" in body


def test_list_business_categories_default(client):
    r = client.get("/api/v1/classification/business-categories")
    assert r.status_code == 200
    items = r.json()
    # default active_only=True should still include all since all are active by default
    assert isinstance(items, list)
    assert len(items) == 9
    assert any(item["code"] == "cmrczn_tab1" for item in items)


def test_list_business_categories_minimal_fields(client):
    r = client.get(
        "/api/v1/classification/business-categories",
        params={"active_only": True, "include_details": False},
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 9
    # minimal fields still include code/name/description
    assert {"code", "name", "description"}.issubset(items[0].keys())


@pytest.mark.parametrize("code,expect_200", [("cmrczn_tab1", True), ("invalid_code", False)])
def test_get_business_category_by_code(client, code, expect_200):
    r = client.get(f"/api/v1/classification/business-categories/{code}")
    if expect_200:
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == code
    else:
        assert r.status_code == 404


def test_validate_business_category(client):
    ok = client.post("/api/v1/classification/business-categories/validate", params={"code": "cmrczn_tab1"})
    bad = client.post("/api/v1/classification/business-categories/validate", params={"code": "invalid_code"})
    assert ok.status_code == 200
    assert ok.json()["is_valid"] is True
    assert bad.status_code == 200
    assert bad.json()["is_valid"] is False


def test_search_business_categories(client):
    params = [("q", "교육"), ("fields", "name"), ("fields", "description"), ("limit", "5")]
    r = client.get("/api/v1/classification/business-categories/search", params=params)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) > 0


def test_list_content_categories_default(client):
    r = client.get("/api/v1/classification/content-categories")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) == 3
    assert any(item["code"] == "notice_matr" for item in items)


@pytest.mark.parametrize("code,expect_200", [("notice_matr", True), ("invalid_code", False)])
def test_get_content_category_by_code(client, code, expect_200):
    r = client.get(f"/api/v1/classification/content-categories/{code}")
    if expect_200:
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == code
    else:
        assert r.status_code == 404


def test_validate_content_category(client):
    ok = client.post("/api/v1/classification/content-categories/validate", params={"code": "notice_matr"})
    bad = client.post("/api/v1/classification/content-categories/validate", params={"code": "invalid_code"})
    assert ok.status_code == 200
    assert ok.json()["is_valid"] is True
    assert bad.status_code == 200
    assert bad.json()["is_valid"] is False


def test_search_content_categories(client):
    params = [("q", "정책"), ("fields", "name"), ("fields", "description"), ("limit", "5")]
    r = client.get("/api/v1/classification/content-categories/search", params=params)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) > 0


def test_validate_any_code(client):
    ok_biz = client.post("/api/v1/classification/validate", params={"code": "cmrczn_tab1"})
    ok_cts = client.post("/api/v1/classification/validate", params={"code": "notice_matr"})
    bad = client.post("/api/v1/classification/validate", params={"code": "invalid_code"})
    assert ok_biz.status_code == 200 and ok_biz.json()["is_valid"] is True
    assert ok_cts.status_code == 200 and ok_cts.json()["is_valid"] is True
    assert bad.status_code == 200 and bad.json()["is_valid"] is False


def test_validate_batch(client):
    r = client.post(
        "/api/v1/classification/validate-batch",
        json=["cmrczn_tab1", "notice_matr", "invalid_code"],
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"cmrczn_tab1", "notice_matr", "invalid_code"}
    assert data["cmrczn_tab1"]["is_valid"] is True
    assert data["notice_matr"]["is_valid"] is True
    assert data["invalid_code"]["is_valid"] is False


def test_validate_batch_overflow_returns_400(client):
    payload = ["x"] * 101
    r = client.post("/api/v1/classification/validate-batch", json=payload)
    assert r.status_code == 400


def test_detect_type(client):
    r = client.get("/api/v1/classification/detect-type/cmrczn_tab1")
    assert r.status_code == 200
    assert r.json()["detected_type"] == "business_category"


def test_unified_search(client):
    r = client.post(
        "/api/v1/classification/search",
        json={"query": "정책", "limit": 5},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "정책"
    assert isinstance(data["results"], list)
    assert data["total_count"] >= 0


def test_get_all_valid_codes(client):
    r = client.get("/api/v1/classification/codes")
    assert r.status_code == 200
    data = r.json()
    assert "business_category" in data and "content_category" in data
    assert len(data["business_category"]) == 9
    assert len(data["content_category"]) == 3


def test_recommendations_happy_path(client):
    r = client.get(
        "/api/v1/classification/recommendations",
        params={"context": "사업화 지원 프로그램", "limit": 3},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) <= 3


def test_recommendations_invalid_code_type_returns_400(client):
    r = client.get(
        "/api/v1/classification/recommendations",
        params={"context": "정책", "code_type": "wrong", "limit": 3},
    )
    assert r.status_code == 400


def test_recommendations_with_business_alias(client):
    r = client.get(
        "/api/v1/classification/recommendations",
        params={"context": "해외 진출 관련 지원", "code_type": "business", "limit": 5},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # expect only business_category results
    for item in items:
        assert item["type"] == "business_category"


def test_statistics(client):
    r = client.get("/api/v1/classification/statistics")
    assert r.status_code == 200
    data = r.json()
    assert data["total_business_categories"] == 9
    assert data["total_content_categories"] == 3


def test_cache_clear(client):
    r = client.post("/api/v1/classification/cache/clear")
    assert r.status_code == 200
    data = r.json()
    assert data.get("message") == "Cache cleared successfully"


def test_reference_business_categories(client):
    r = client.get("/api/v1/classification/reference/business-categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(item["code"] == "cmrczn_tab1" for item in data)


def test_reference_content_categories(client):
    r = client.get("/api/v1/classification/reference/content-categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(item["code"] == "notice_matr" for item in data)


def test_reference_types(client):
    r = client.get("/api/v1/classification/reference/types")
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"business_category", "content_category"}


