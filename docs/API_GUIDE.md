# API 사용 가이드

## 📋 목차
1. [시작하기](#시작하기)
2. [인증](#인증)
3. [API 엔드포인트](#api-엔드포인트)
4. [응답 형식](#응답-형식)
5. [에러 처리](#에러-처리)
6. [예제 코드](#예제-코드)
7. [자주 묻는 질문](#자주-묻는-질문)

## 🚀 시작하기

### Base URL
```
개발 환경: http://localhost:8000
프로덕션: https://api.startup-data.kr
```

### API 버전
현재 지원되는 API 버전: `v1`

모든 API 엔드포인트는 `/api/v1` 접두사를 사용합니다.

## 🔐 인증

현재 버전에서는 별도의 인증이 필요하지 않습니다. (개발 단계)

향후 API 키 또는 JWT 토큰 기반 인증이 추가될 예정입니다.

## 🛠️ API 엔드포인트

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

### 2. 사업공고 (Announcements)

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
[
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
]
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

## 📊 응답 형식

### 성공 응답
모든 성공 응답은 다음 형식을 따릅니다:

```json
{
  "success": true,
  "message": "성공",
  "data": { /* 응답 데이터 */ }
}
```

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

## ❓ 자주 묻는 질문

### Q: API 호출 횟수에 제한이 있나요?
A: 현재 개발 단계에서는 별도의 rate limiting이 없습니다. 프로덕션 환경에서는 적절한 제한이 적용될 예정입니다.

### Q: 데이터는 얼마나 자주 업데이트되나요?
A: 자동 스케줄러를 통해 사업공고는 매일, 통계 데이터는 매주 업데이트됩니다. `/fetch` 엔드포인트를 통해 수동으로도 최신 데이터를 가져올 수 있습니다.

### Q: 페이지네이션은 어떻게 사용하나요?
A: `skip`과 `limit` 파라미터를 사용합니다. 예: 2페이지(페이지당 20개)를 조회하려면 `skip=20&limit=20`을 사용하세요.

### Q: 데이터 중복은 어떻게 처리되나요?
A: `/fetch` 엔드포인트는 `business_id`를 기준으로 중복을 자동 감지하여 새로운 데이터만 저장합니다.

### Q: 오래된 데이터는 어떻게 관리되나요?
A: 데이터는 삭제되지 않고 `is_active` 플래그를 통해 비활성화됩니다. 필요시 다시 활성화할 수 있습니다.

## 📞 지원

- **이슈 리포트**: GitHub Issues
- **이메일**: dev@example.com
- **문서**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

---

**업데이트**: 2024-03-01  
**버전**: 1.0.0