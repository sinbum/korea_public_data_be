import os
from typing import Dict, List, Tuple, Any

import pytest
import httpx


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
OPENAPI_URL = f"{BASE_URL}/openapi.json"


def _fetch_openapi() -> Dict:
    with httpx.Client(timeout=10) as client:
        resp = client.get(OPENAPI_URL)
        resp.raise_for_status()
        return resp.json()


def _is_auth_path(path: str) -> bool:
    auth_keywords = [
        "/auth",
        "/login",
        "/logout",
        "/oauth",
        "/users",  # 사용자 관련은 인증이 필요한 경우가 많아 제외
        "/keys",   # 키 관리 관련은 인증/권한 필요 가능성 높음
    ]
    return any(k in path for k in auth_keywords)


def _skip_path(path: str) -> bool:
    skip_keywords = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/metrics",
        "/favicon.ico",
    ]
    return any(k == path or path.startswith(k) for k in skip_keywords)


def _has_path_params(path: str) -> bool:
    return "{" in path and "}" in path


def _collect_targets() -> List[Tuple[str, str]]:
    spec = _fetch_openapi()
    targets: List[Tuple[str, str]] = []
    for path, methods in spec.get("paths", {}).items():
        if _skip_path(path) or _is_auth_path(path):
            continue
        if _has_path_params(path):
            # 경로 파라미터 있는 엔드포인트는 안전한 샘플이 없어 일단 제외
            continue
        for method in methods.keys():
            m = method.lower()
            if m not in {"get", "post"}:  # 변경계열(put/patch/delete)은 기본 제외
                continue
            op: Dict = methods.get(method, {}) or {}
            # requestBody가 required면 제외 (샘플 없이 호출 불가)
            body = op.get("requestBody") or {}
            if body.get("required") is True:
                continue
            targets.append((m, path))
    # 중복 제거 및 정렬(경로 기준)
    return sorted(list(set(targets)), key=lambda x: (x[0], x[1]))


def _choose_sample_value(schema: Dict[str, Any]) -> Any:
    if not schema:
        return "test"
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]
    t = schema.get("type")
    if t == "integer":
        return max(1, int(schema.get("minimum", 1)))
    if t == "number":
        return float(schema.get("minimum", 1))
    if t == "boolean":
        return True
    if t == "array":
        item = _choose_sample_value(schema.get("items", {}))
        min_items = int(schema.get("minItems", 1) or 1)
        return [item] * min_items
    # default to string
    fmt = schema.get("format")
    if fmt == "date-time":
        return "2025-01-01T00:00:00Z"
    if fmt == "date":
        return "2025-01-01"
    return schema.get("default", "test")


def _build_query_params(spec: Dict, path: str, method: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    path_item: Dict = spec.get("paths", {}).get(path, {}) or {}
    parameters: List[Dict] = []
    parameters.extend(path_item.get("parameters", []) or [])
    op: Dict = path_item.get(method, {}) or {}
    parameters.extend(op.get("parameters", []) or [])
    for p in parameters:
        if p.get("in") != "query":
            continue
        required = p.get("required", False)
        name = p.get("name")
        schema = p.get("schema", {}) or {}
        # 일부 검색/검증 엔드포인트는 필수 파라미터가 아님에도 없으면 422가 날 수 있어 최소값 제공
        if required or name in {"q", "query", "code", "limit", "fields"}:
            params[name] = _choose_sample_value(schema)
            # 필드명에 따라 합리적 기본값 보정
            if name in {"q", "query"} and isinstance(params[name], str):
                params[name] = "test"
            if name == "limit" and isinstance(params[name], int):
                params[name] = max(1, min(params[name], 5))
    return params


@pytest.mark.e2e
def test_openapi_available():
    with httpx.Client(timeout=10) as client:
        resp = client.get(OPENAPI_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data and "paths" in data


@pytest.mark.e2e
@pytest.mark.parametrize("method,path", _collect_targets())
def test_public_endpoints_basic(method: str, path: str):
    url = f"{BASE_URL}{path}"
    spec = _fetch_openapi()
    qp = _build_query_params(spec, path, method)
    # 대부분의 공개 GET/POST는 바디 없이 동작해야 함 (query 파라미터는 기본값 사용)
    with httpx.Client(timeout=20) as client:
        if method == "get":
            resp = client.get(url, params=qp or None)
        elif method == "post":
            resp = client.post(url, params=qp or None)
        else:
            pytest.skip("method not targeted")

        # 허용 가능한 정상 범위: 2xx 또는 합리적 4xx (예: validation 400)
        assert (
            200 <= resp.status_code < 300
            or resp.status_code in {400, 404, 405, 422, 429}
        ), f"Unexpected status {resp.status_code} for {method.upper()} {path}: {resp.text[:200]}"


