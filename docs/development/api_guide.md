# 🌐 Korea Public Data API 가이드

> **현재 상태**: 백엔드 현재 구현 상태를 반영한 실제 사용 가능한 API 가이드

![API Status](https://img.shields.io/badge/API%20Status-Partially%20Implemented-yellow.svg)
![Version](https://img.shields.io/badge/Version-v1.0.0-blue.svg)
![Last Updated](https://img.shields.io/badge/Last%20Updated-2025--08--02-green.svg)

## 📋 목차
1. [시작하기](#시작하기)
2. [현재 구현 상태](#현재-구현-상태)
3. [인증](#인증)
4. [API 엔드포인트](#api-엔드포인트)
5. [응답 형식](#응답-형식)
6. [에러 처리](#에러-처리)
7. [예제 코드](#예제-코드)
8. [개발 로드맵](#개발-로드맵)
9. [자주 묻는 질문](#자주-묻는-질문)

## 🚀 시작하기

### Base URL
```
개발 환경: http://localhost:8000
프로덕션: TBD (개발 중)
```

### API 버전
- **현재 지원**: `v1` (부분 구현)
- **계획**: `v2`, `v3` (API 버저닝 시스템 준비됨)

모든 API 엔드포인트는 `/api/v1` 접두사를 사용합니다.

## 📊 현재 구현 상태

### 도메인별 완성도

| 도메인 | 완성도 | 상태 | 사용 가능 기능 |
|--------|--------|------|----------------|
| **🏢 Announcements** | **95%** | ✅ **프로덕션 준비** | 전체 CRUD, 데이터 수집, 검색 |
| **🎯 Businesses** | **60%** | 🔄 **API만 완성** | 기본 CRUD (비즈니스 로직 미흡) |
| **📚 Contents** | **60%** | 🔄 **API만 완성** | 기본 CRUD (분류 시스템 미흡) |
| **📊 Statistics** | **65%** | 🔄 **API만 완성** | 기본 CRUD (집계 로직 미흡) |

### ⚠️ 중요 알림
- **Announcements 도메인만 완전히 사용 가능**합니다
- 다른 도메인들은 기본 API는 있지만 비즈니스 로직이 부족합니다
- 인증 시스템이 아직 구현되지 않았습니다 (기본 API 키 인증만 존재)
- Repository 패턴이 적용되지 않아 서비스에서 직접 DB 접근합니다

## 🔐 인증

### 현재 상태: 기본 인증만 지원

현재 버전에서는 **매우 기본적인 인증**만 제공됩니다:
- 기본적인 API 키 검증만 존재
- 사용자 관리 시스템 없음
- 권한 기반 접근 제어 부재

### 개발 중인 인증 시스템 (예정)

#### Phase 1: JWT 기반 인증 (1-2주 내)
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### Phase 2: RBAC 시스템 (2-3주 내)
- 역할 기반 접근 제어
- 사용자/관리자/개발자 권한 분리
- API 엔드포인트별 권한 제어

### 현재 사용 방법
개발 단계에서는 인증 없이 API 사용 가능하지만, 프로덕션 배포 전 반드시 인증 시스템이 구현될 예정입니다.

## 🛠️ API 엔드포인트

### ✅ 완전 구현된 엔드포인트 (사용 권장)

### 1. 기본 정보

#### 서비스 상태 확인
```http
GET /health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-01T12:00:00Z",
  "database": "connected",
  "version": "1.0.0"
}
```

#### API 정보 조회
```http
GET /
```

### 2. 🏢 사업공고 (Announcements) - ✅ 완전 구현됨

> **상태**: 프로덕션 준비 완료 (95% 완성도)  
> **권장 사용**: 모든 기능 안정적으로 사용 가능

#### 2.1 공공데이터에서 사업공고 수집
```http
POST /api/v1/announcements/fetch
```

**Query Parameters:**
- `page_no` (int, optional): 페이지 번호 (기본값: 1)
- `num_of_rows` (int, optional): 한 페이지당 결과 수 (기본값: 10, 최대: 100)
- `business_name` (string, optional): 사업명 필터
- `business_type` (string, optional): 사업유형 필터

**요청 예시:**
```bash
curl -X POST "http://localhost:8000/api/v1/announcements/fetch?page_no=1&num_of_rows=10&business_name=창업도약"
```

**응답 예시:**
```json
{
  "success": true,
  "message": "공고 데이터 수집 완료",
  "data": [
    {
      "id": "65f1a2b3c4d5e6f7a8b9c0d1",
      "announcement_data": {
        "business_id": "KISED-2024-001",
        "business_name": "창업도약패키지",
        "business_type": "정부지원사업",
        "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
        "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
        "recruitment_period": "2024.03.15 ~ 2024.04.15",
        "application_method": "온라인 접수 (www.k-startup.go.kr)",
        "contact_info": "창업진흥원 창업성장실 02-123-4567",
        "announcement_date": "2024-03-01T09:00:00Z",
        "deadline": "2024-04-15T18:00:00Z",
        "status": "모집중"
      },
      "source_url": "https://www.data.go.kr/dataset/15121654",
      "is_active": true,
      "created_at": "2024-03-01T09:00:00Z",
      "updated_at": "2024-03-01T09:00:00Z"
    }
  ],
  "meta": {
    "total_fetched": 1,
    "new_items": 1,
    "updated_items": 0,
    "duplicates_skipped": 0
  }
}
```

#### 2.2 사업공고 목록 조회
```http
GET /api/v1/announcements/
```

**Query Parameters:**
- `skip` (int, optional): 건너뛸 데이터 수 (기본값: 0)
- `limit` (int, optional): 조회할 데이터 수 (기본값: 20, 최대: 100)
- `is_active` (bool, optional): 활성 상태 필터 (기본값: true)

**요청 예시:**
```bash
curl "http://localhost:8000/api/v1/announcements/?skip=0&limit=20&is_active=true"
```

#### 2.3 특정 사업공고 조회
```http
GET /api/v1/announcements/{announcement_id}
```

**Path Parameters:**
- `announcement_id` (string, required): 사업공고 고유 ID (MongoDB ObjectId)

**요청 예시:**
```bash
curl "http://localhost:8000/api/v1/announcements/65f1a2b3c4d5e6f7a8b9c0d1"
```

#### 2.4 사업공고 생성
```http
POST /api/v1/announcements/
```

**Request Body:**
```json
{
  "announcement_data": {
    "business_id": "KISED-2024-001",
    "business_name": "창업도약패키지",
    "business_type": "정부지원사업",
    "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
    "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
    "status": "모집중"
  },
  "source_url": "https://www.data.go.kr/dataset/15121654"
}
```

#### 2.5 사업공고 수정
```http
PUT /api/v1/announcements/{announcement_id}
```

**Request Body:**
```json
{
  "announcement_data": {
    "status": "마감"
  },
  "is_active": false
}
```

#### 2.6 사업공고 삭제 (비활성화)
```http
DELETE /api/v1/announcements/{announcement_id}
```

---

### 🔄 부분 구현된 엔드포인트 (개발 중)

> **주의**: 아래 API들은 기본 CRUD는 동작하지만 비즈니스 로직이 부족합니다.

### 3. 🎯 사업정보 (Businesses) - 🔄 60% 완성

**현재 상태**:
- ✅ 기본 CRUD API 완성
- ❌ 비즈니스 로직 미흡 (단순 CRUD만 가능)
- ❌ 관련 공고 매칭 로직 없음
- ❌ 성과 분석 기능 없음

#### 3.1 사업정보 목록 조회 (기본 기능만)
```http
GET /api/v1/businesses/
```

**Query Parameters**:
- `skip` (int, optional): 건너뛸 데이터 수
- `limit` (int, optional): 조회할 데이터 수

**⚠️ 제한사항**: 단순 목록 조회만 가능. 고급 필터링, 분석 데이터 없음

#### 3.2 사업정보 상세 조회
```http
GET /api/v1/businesses/{business_id}
```

**⚠️ 제한사항**: 관련 공고, 성과 데이터 등 부가 정보 제공 안됨

### 4. 📚 콘텐츠 정보 (Contents) - 🔄 60% 완성

**현재 상태**:
- ✅ 기본 CRUD API 완성
- ❌ 분류 시스템 미흡
- ❌ 자동 분류 기능 없음
- ❌ 검색 최적화 없음

#### 4.1 콘텐츠 목록 조회 (기본 기능만)
```http
GET /api/v1/contents/
```

**⚠️ 제한사항**: 기본 목록만. 카테고리별 분류, 태그 시스템 없음

### 5. 📊 통계 정보 (Statistics) - 🔄 65% 완성

**현재 상태**:
- ✅ 기본 CRUD API 완성
- ❌ 집계 로직 미흡
- ❌ 실시간 통계 계산 없음
- ❌ 대시보드용 데이터 가공 없음

#### 5.1 통계 정보 조회 (기본 기능만)
```http
GET /api/v1/statistics/
```

**⚠️ 제한사항**: 저장된 원시 데이터만 반환. 실시간 집계, 차트용 데이터 가공 없음

## 📊 응답 형식

### 표준 응답 구조

#### 성공 응답 (Announcements - 완전 구현)
```json
{
  "success": true,
  "message": "성공",
  "data": { /* 응답 데이터 */ },
  "timestamp": "2025-08-02T10:30:00Z"
}
```

#### 기본 응답 (다른 도메인 - 부분 구현)
```json
[
  { /* 데이터 객체들 */ }
]
```

**⚠️ 주의**: 
- **Announcements**: 표준화된 응답 구조 사용
- **다른 도메인들**: 아직 기본 배열/객체 응답만 제공
- 향후 모든 도메인을 표준 응답 구조로 통일 예정

### 페이지네이션 응답
목록 조회 시 페이지네이션 정보가 포함됩니다:

```json
{
  "success": true,
  "message": "성공",
  "data": [ /* 데이터 배열 */ ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

## ❌ 에러 처리

### 에러 응답 형식
```json
{
  "success": false,
  "message": "에러 메시지",
  "error_code": "ERROR_CODE",
  "details": { /* 상세 에러 정보 */ },
  "timestamp": "2024-03-01T12:00:00Z"
}
```

### 주요 에러 코드

| 코드 | HTTP 상태 | 설명 |
|------|-----------|------|
| `VALIDATION_ERROR` | 400 | 요청 데이터 검증 실패 |
| `DATA_NOT_FOUND` | 404 | 요청한 리소스를 찾을 수 없음 |
| `EXTERNAL_API_ERROR` | 502 | 외부 API 호출 실패 |
| `DATABASE_ERROR` | 500 | 데이터베이스 오류 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

### 에러 예시

#### 404 - 리소스를 찾을 수 없음
```json
{
  "success": false,
  "message": "해당 ID의 사업공고를 찾을 수 없습니다",
  "error_code": "DATA_NOT_FOUND",
  "timestamp": "2024-03-01T12:00:00Z"
}
```

#### 400 - 검증 오류
```json
{
  "success": false,
  "message": "요청 데이터 검증에 실패했습니다",
  "error_code": "VALIDATION_ERROR",
  "details": [
    {
      "field": "num_of_rows",
      "message": "값이 100보다 작거나 같아야 합니다",
      "type": "value_error"
    }
  ],
  "timestamp": "2024-03-01T12:00:00Z"
}
```

## 💻 예제 코드

### Python (requests)
```python
import requests

# 사업공고 목록 조회
response = requests.get(
    "http://localhost:8000/api/v1/announcements/",
    params={"limit": 10, "is_active": True}
)

if response.status_code == 200:
    announcements = response.json()
    print(f"총 {len(announcements)}개의 공고를 조회했습니다.")
else:
    error = response.json()
    print(f"에러: {error['message']}")

# 공공데이터 수집
fetch_response = requests.post(
    "http://localhost:8000/api/v1/announcements/fetch",
    params={"page_no": 1, "num_of_rows": 20}
)

if fetch_response.status_code == 200:
    new_announcements = fetch_response.json()
    print(f"{len(new_announcements)}개의 새로운 공고를 수집했습니다.")
```

### JavaScript (fetch)
```javascript
// 사업공고 목록 조회
async function getAnnouncements() {
  try {
    const response = await fetch(
      'http://localhost:8000/api/v1/announcements/?limit=10&is_active=true'
    );
    
    if (response.ok) {
      const announcements = await response.json();
      console.log(`총 ${announcements.length}개의 공고를 조회했습니다.`);
      return announcements;
    } else {
      const error = await response.json();
      console.error(`에러: ${error.message}`);
    }
  } catch (error) {
    console.error('네트워크 오류:', error);
  }
}

// 공공데이터 수집
async function fetchAnnouncements() {
  try {
    const response = await fetch(
      'http://localhost:8000/api/v1/announcements/fetch?page_no=1&num_of_rows=20',
      { method: 'POST' }
    );
    
    if (response.ok) {
      const newAnnouncements = await response.json();
      console.log(`${newAnnouncements.length}개의 새로운 공고를 수집했습니다.`);
      return newAnnouncements;
    }
  } catch (error) {
    console.error('데이터 수집 오류:', error);
  }
}
```

### curl
```bash
# 사업공고 목록 조회
curl -X GET "http://localhost:8000/api/v1/announcements/?limit=10&is_active=true" \
  -H "Content-Type: application/json"

# 공공데이터 수집
curl -X POST "http://localhost:8000/api/v1/announcements/fetch?page_no=1&num_of_rows=20" \
  -H "Content-Type: application/json"

# 새 사업공고 생성
curl -X POST "http://localhost:8000/api/v1/announcements/" \
  -H "Content-Type: application/json" \
  -d '{
    "announcement_data": {
      "business_name": "테스트 사업",
      "business_type": "정부지원사업",
      "status": "모집중"
    }
  }'
```

## 🛣️ 개발 로드맵

### Phase 1: 기반 인프라 강화 (2-3주)
- **인증 시스템 구축**: JWT + RBAC
- **Repository 패턴 적용**: 모든 도메인
- **응답 형식 표준화**: 통일된 API 응답 구조
- **에러 처리 개선**: 구조화된 에러 응답

### Phase 2: 도메인 로직 완성 (3-4주)
- **Businesses 도메인**: 분석 기능, 추천 시스템
- **Contents 도메인**: 자동 분류, 검색 최적화
- **Statistics 도메인**: 실시간 집계, 대시보드 데이터
- **도메인 간 연동**: 관련 데이터 매칭

### Phase 3: 고급 기능 (1-2개월)
- **GraphQL 지원**: REST와 함께 제공
- **실시간 알림**: WebSocket 기반
- **캐싱 전략**: Redis 다계층 캐싱
- **성능 최적화**: 쿼리 최적화, 인덱싱

## ❓ 자주 묻는 질문

### Q: 어떤 API를 사용해야 하나요?
**A: 현재는 Announcements API만 안정적입니다.** 다른 도메인은 기본 기능만 제공되므로 프로덕션 사용을 권장하지 않습니다.

### Q: 언제 모든 기능이 완성되나요?
**A: 3-4개월 내 엔터프라이즈급 시스템으로 완성 예정입니다.** 단계별 개발 로드맵을 참고하세요.

### Q: API 호출 횟수에 제한이 있나요?
**A: 현재는 제한 없음.** 프로덕션에서는 인증 기반 rate limiting 적용 예정.

### Q: 데이터는 얼마나 자주 업데이트되나요?
**A: Announcements만 자동 업데이트됩니다.** Celery 스케줄러로 매일 업데이트. 다른 도메인은 수동 업데이트만 가능.

### Q: 페이지네이션은 어떻게 사용하나요?
**A: 도메인별로 다릅니다:**
- **Announcements**: 표준 meta 정보 포함
- **다른 도메인**: 기본 `skip`/`limit`만 지원

### Q: 에러 처리는 어떻게 되나요?
**A: 현재 기본적인 에러 처리만 제공.** 구조화된 에러 응답은 인증 시스템과 함께 개선 예정.

### Q: 테스트 환경은 어떻게 사용하나요?
**A: Docker Compose로 로컬 개발 환경 구축 가능.** 자세한 내용은 README.md 참고.

## 📞 지원 및 문서

### 개발 도구
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 추가 문서
- **백엔드 현재 상태**: [be/docs/architecture/backend_current_state.md](../architecture/backend_current_state.md)
- **K-Startup API 명세**: [kstartup_api_spec.md](../integration/kstartup_api_spec.md)
- **개발 환경 설정**: [../../README.md](../../README.md)

### 지원
- **이슈 리포트**: GitHub Issues
- **개발팀 문의**: 프로젝트 담당자에게 문의

---

**⚠️ 중요 공지**: 이 문서는 실제 구현 상태를 반영합니다. 모든 기능이 완성되지 않았으므로 사용 전 구현 상태를 확인하세요.

**마지막 업데이트**: 2025-08-02  
**API 버전**: v1.0.0  
**문서 버전**: 2.0.0 (실제 구현 상태 반영)