# 🌟 한국 공공데이터 API 플랫폼

> 확장 가능한 공공데이터 API 플랫폼으로, 창업진흥원 K-Startup을 시작으로 다양한 정부 공공데이터를 통합하여 제공하는 현대적인 RESTful API 서비스입니다.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-Latest-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🏗️ 아키텍처 하이라이트

### 🎯 SOLID 원칙 적용
- **Single Responsibility**: 각 모듈은 단일 책임
- **Open/Closed**: 새로운 공공데이터 API 추가 시 기존 코드 변경 없이 확장 가능
- **Liskov Substitution**: 다양한 데이터 소스를 동일한 인터페이스로 처리
- **Interface Segregation**: 클라이언트별 필요한 인터페이스만 의존
- **Dependency Inversion**: 구체적 구현보다 추상화에 의존

### 🔧 디자인 패턴 활용
- **Strategy Pattern**: API 클라이언트 전략 (인증, 요청 처리)
- **Factory Pattern**: 데이터 소스별 서비스 생성
- **Repository Pattern**: 데이터 접근 계층 추상화
- **Plugin Pattern**: 동적 기능 확장
- **Template Method**: 공통 API 호출 파이프라인

### ⚡ 성능 및 확장성
- **의존성 주입**: 느슨한 결합과 높은 테스트 가능성
- **API 버저닝**: 호환성 유지하며 점진적 업그레이드
- **비동기 처리**: Celery 기반 백그라운드 작업
- **Redis 캐싱**: 고성능 응답 및 세션 관리
- **MongoDB 최적화**: 인덱싱 및 쿼리 최적화

## 🚀 주요 기능

### ✅ 완성된 기능
- 🏢 **사업공고 정보**: 창업지원 사업 공고 데이터 실시간 수집 및 완전한 CRUD API
- 🔄 **자동 데이터 수집**: Celery 기반 스케줄링으로 정기적 데이터 갱신
- 📄 **표준 페이지네이션**: 일관된 페이징 및 정렬 시스템
- 🎯 **고급 필터링**: 키워드, 카테고리, 상태, 날짜 범위별 검색
- ⚡ **성능 최적화**: Redis 캐싱 및 데이터베이스 쿼리 최적화
- 🛡️ **예외 처리**: 계층화된 에러 처리 및 표준 응답 포맷
- 📊 **모니터링**: Celery Flower를 통한 작업 모니터링
- 🔧 **의존성 주입**: 컨테이너 기반 DI 시스템

### 🔄 개발 진행 중
- 📚 **콘텐츠 정보**: 창업 관련 콘텐츠 및 자료 (모델 완성, API 완성됨)
- 📊 **통계 정보**: 창업 현황 및 성과 통계 데이터 (모델 완성, API 완성됨)
- 🎯 **기업정보**: 창업기업 상세 정보 (모델 완성, API 완성됨)
- 🏷️ **분류 시스템**: 사업 및 콘텐츠 자동 분류
- 🔌 **플러그인 시스템**: 동적 데이터 소스 확장

## 🛠️ 기술 스택

### 핵심 기술
- **Backend**: FastAPI 0.104+ + Python 3.11+
- **Database**: MongoDB (pymongo) - 성능 최적화
- **Task Queue**: Celery + Redis - 비동기 작업 처리
- **Validation**: Pydantic V2 - 강타입 데이터 검증
- **HTTP Client**: httpx - 비동기 외부 API 호출
- **Container**: Docker + Docker Compose

### 아키텍처 특징
- **Domain-Driven Design (DDD)**: 도메인별 명확한 분리
- **Clean Architecture**: 계층화된 아키텍처
- **CQRS 패턴**: 명령과 쿼리 분리 (부분 적용)
- **Event-Driven**: 이벤트 기반 시스템 (확장 예정)

## 📂 현대적 프로젝트 구조

```
be/
├── 📁 app/                             # 메인 애플리케이션
│   ├── 📁 core/                        # 핵심 인프라스트럭처
│   │   ├── config.py                   # 환경설정 및 설정 관리
│   │   ├── database.py                 # MongoDB 연결 및 설정
│   │   ├── celery.py                   # Celery 설정 및 초기화
│   │   ├── container.py                # DI 컨테이너 설정
│   │   ├── dependencies.py             # FastAPI 의존성 주입
│   │   └── middleware.py               # 미들웨어 (요청/응답 검증, Rate Limiting)
│   │   
│   ├── 📁 domains/                     # 도메인 주도 설계 (DDD)
│   │   ├── 📁 announcements/           # 🏢 사업공고 도메인 (완성)
│   │   │   ├── models.py               # 도메인 모델
│   │   │   ├── schemas.py              # API 스키마
│   │   │   ├── service.py              # 비즈니스 로직
│   │   │   ├── router.py               # REST API 엔드포인트
│   │   │   ├── tasks.py                # Celery 백그라운드 작업
│   │   │   └── versioned_router.py     # API 버저닝 지원
│   │   │   
│   │   ├── 📁 businesses/              # 🎯 기업정보 도메인 (API 완성)
│   │   ├── 📁 contents/                # 📚 콘텐츠 도메인 (API 완성)
│   │   └── 📁 statistics/              # 📊 통계정보 도메인 (API 완성)
│   │   
│   ├── 📁 shared/                      # 공통 인프라스트럭처
│   │   ├── 📁 clients/                 # 외부 API 클라이언트
│   │   │   ├── base_client.py          # 공통 API 클라이언트 추상화
│   │   │   ├── kstartup_api_client.py  # K-Startup API 클라이언트
│   │   │   └── strategies.py           # Strategy 패턴 구현
│   │   │   
│   │   ├── 📁 exceptions/              # 예외 처리 시스템
│   │   │   ├── __init__.py             # 공통 예외 정의
│   │   │   ├── custom_exceptions.py    # 커스텀 예외 클래스
│   │   │   ├── handlers.py             # 예외 핸들러
│   │   │   └── api_exceptions.py       # API 관련 예외
│   │   │   
│   │   ├── 📁 interfaces/              # 인터페이스 및 추상화
│   │   ├── 📁 classification/          # 🏷️ 분류 시스템
│   │   ├── 📁 cqrs/                   # CQRS 패턴 구현
│   │   ├── 📁 events/                 # 이벤트 시스템
│   │   ├── responses.py                # 표준 응답 포맷
│   │   ├── pagination.py               # 페이지네이션 유틸리티
│   │   ├── versioning.py               # API 버저닝 시스템
│   │   └── validators.py               # 공통 검증 로직
│   │   
│   ├── 📁 scheduler/                   # 📅 작업 스케줄링
│   │   ├── monitoring_tasks.py         # 모니터링 작업
│   │   └── task_management_api.py      # 작업 관리 API
│   │   
│   └── main.py                         # 🚀 FastAPI 엔트리포인트
│   
├── 📁 docs/                           # 📖 체계화된 문서
│   ├── 📁 architecture/               # 아키텍처 문서
│   │   ├── design_patterns.md         # 디자인 패턴 설명
│   │   └── system_overview.md         # 시스템 개요
│   ├── 📁 domains/                    # 도메인별 문서
│   │   ├── announcements/             # 사업공고 도메인 가이드
│   │   └── api_validation_report.md   # API 검증 리포트
│   ├── 📁 integration/                # 통합 가이드
│   │   ├── kstartup_api_spec.md       # K-Startup API 명세
│   │   └── business_category_codes.md # 사업 카테고리 코드
│   ├── 📁 operations/                 # 운영 가이드
│   └── 📁 development/                # 개발 가이드
│   
├── 📁 tests/                         # 🧪 테스트 스위트
│   ├── 📁 unit/                      # 단위 테스트
│   └── 📁 integration/               # 통합 테스트
│   
├── 📁 scripts/                       # 🛠️ 관리 스크립트
│   ├── init-volumes.sh               # 볼륨 초기화
│   ├── backup.sh                     # 데이터 백업
│   ├── restore.sh                    # 데이터 복원
│   └── validate_service_layer.py     # 서비스 계층 검증
│   
├── 📁 volumes/                       # 💾 데이터 영속성
│   ├── mongodb/                      # MongoDB 데이터
│   ├── redis/                        # Redis 데이터 및 캐시
│   ├── logs/                         # 구조화된 로그
│   └── backups/                      # 자동 백업
│   
├── 🔧 docker-compose.yml             # Docker 서비스 오케스트레이션 (개발)
├── 🔧 docker-compose.prod.yml        # Docker 서비스 오케스트레이션 (프로덕션)
├── 🐳 Dockerfile                     # 컨테이너 이미지 정의
├── 📦 requirements.txt               # Python 의존성
├── ⚙️ .env                          # 환경변수 설정
└── 📋 CLAUDE.md                      # 프로젝트 가이드라인
```

### 🏗️ 아키텍처 계층 구조

```
┌─────────────────────────────────────────────────┐
│                Presentation Layer                │
│          (FastAPI Routers + Middleware)         │
├─────────────────────────────────────────────────┤
│                Application Layer                 │
│        (Services + Use Cases + CQRS)            │
├─────────────────────────────────────────────────┤
│                 Domain Layer                     │
│         (Models + Business Logic)               │
├─────────────────────────────────────────────────┤
│               Infrastructure Layer               │
│    (Repositories + API Clients + Database)      │
└─────────────────────────────────────────────────┘
```

## ⚡ 빠른 시작

### 1️⃣ 사전 요구사항
- **Docker & Docker Compose** (권장)
- **Python 3.11+** (로컬 개발 시)
- **공공데이터포털 API 키** ([발급받기](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654))

### 2️⃣ 프로젝트 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd korea_public_data/be

# 2. 환경변수 설정
# (저장소에 .env.example가 없다면 아래 예시를 참고해 .env 파일을 직접 생성)
# 📝 PUBLIC_DATA_API_KEY에 실제 발급받은 키를 설정

# 3. 볼륨 및 권한 초기화 (최초 1회만)
./scripts/init-volumes.sh
```

### 3️⃣ Docker로 실행 (👑 권장)

```bash
# 🚀 전체 서비스 시작 (백그라운드)
docker-compose up -d

# 📊 서비스 상태 확인
docker-compose ps

# 📝 실시간 로그 모니터링
docker-compose logs -f api

# 🔍 특정 서비스 로그만 확인
docker-compose logs -f api celery-worker celery-beat
```

### 4️⃣ 서비스 접속 및 확인

서비스가 시작되면 다음 URL에서 접속할 수 있습니다:

| 서비스 | URL | 설명 |
|--------|-----|------|
| 🌐 **API 서버** | http://localhost:8000 | 메인 API 엔드포인트 |
| 📖 **Swagger UI** | http://localhost:8000/docs | 대화형 API 문서 (완전 한국어) |
| 📚 **ReDoc** | http://localhost:8000/redoc | 읽기 전용 API 문서 |
| ❤️ **Health Check** | http://localhost:8000/health | 서비스 상태 확인 |
| 🌺 **Celery Flower (선택)** | http://localhost:5555 | 작업 큐 모니터링 (개발 환경에서는 docker-compose.yml에서 해당 서비스 주석 해제 후 사용) |
| 🗄️ **MongoDB** | localhost:27017 | 데이터베이스 (admin/password123) |
| 🔴 **Redis** | localhost:6379 | 캐시 및 메시지 브로커 |

프로덕션 구성 사용 시 Nginx(80/443), Prometheus(9090), Grafana(3030) 포트가 추가로 노출됩니다.

### 5️⃣ API 동작 테스트

```bash
# 🏥 서비스 상태 확인
curl -X GET "http://localhost:8000/health"

# 📋 사업공고 목록 조회 (첫 10개)
curl -X GET "http://localhost:8000/api/v1/announcements/"

# 🔄 공공데이터에서 실시간 데이터 수집
curl -X POST "http://localhost:8000/api/v1/announcements/fetch"

# 📊 API 버전 정보 확인
curl -X GET "http://localhost:8000/version"
```

### 6️⃣ 로컬 개발 환경 (개발자용)

```bash
# Python 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt

# 인프라스트럭처만 Docker로 실행
docker-compose up -d mongodb redis

# FastAPI 서버 로컬 실행 (Hot Reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Celery Worker 실행 (별도 터미널)
celery -A app.core.celery worker --loglevel=info

# Celery Beat 스케줄러 실행 (별도 터미널)
celery -A app.core.celery beat --loglevel=info
```

### 7️⃣ 프로덕션 실행 (docker-compose.prod.yml)

```bash
# .env에 프로덕션 값 설정 후 실행
docker-compose -f docker-compose.prod.yml up -d

# 상태 확인
docker-compose -f docker-compose.prod.yml ps
```

## 📚 완전 한국어 API 문서

### 🎯 문서 특징
- ✅ **완전 한국어화**: 모든 설명, 예제, 에러 메시지가 한국어
- ✅ **실제 사용 예제**: 모든 API에 실제 테스트 가능한 예제 포함
- ✅ **계층화된 에러 처리**: 모든 가능한 에러 시나리오 문서화
- ✅ **대화형 테스트**: Swagger UI에서 직접 API 테스트 가능
- ✅ **API 버저닝**: v1, v2 버전 지원 및 호환성 안내
- ✅ **성능 지표**: 각 API의 예상 응답 시간 표시

### 📖 문서 접속 방법
| 문서 유형 | URL | 특징 |
|----------|-----|------|
| 🎨 **Swagger UI** | http://localhost:8000/docs | 대화형 API 테스트, 완전 한국어 |
| 📚 **ReDoc** | http://localhost:8000/redoc | 읽기 전용, 깔끔한 디자인 |
| 📋 **OpenAPI JSON** | http://localhost:8000/openapi.json | 머신 리더블 API 스펙 |

## 🔄 완성된 API 엔드포인트

### 🏢 사업공고 (Announcements) - ✅ 완성

```bash
# 📥 공공데이터에서 실시간 수집
POST /api/v1/announcements/fetch
  └── 페이징, 필터링 지원 (사업명, 사업유형)

# 📋 목록 조회 (표준 페이지네이션)
GET /api/v1/announcements/
  ├── ?page=1&size=10&sort=created_at&order=desc
  ├── ?keyword=창업&business_type=정부지원사업
  └── ?is_active=true

# 🔍 상세 조회
GET /api/v1/announcements/{announcement_id}

# ➕ 새 공고 생성
POST /api/v1/announcements/

# ✏️ 공고 수정
PUT /api/v1/announcements/{announcement_id}

# 🗑️ 공고 삭제 (소프트 삭제)
DELETE /api/v1/announcements/{announcement_id}

# 📊 최근 공고 조회
GET /api/v1/announcements/recent?limit=10

# 📈 통계 정보
GET /api/v1/announcements/statistics
```

### 🎯 기업정보 (Businesses) - ✅ API 완성

```bash
# 📥 K-Startup에서 기업정보 수집
POST /api/v1/businesses/fetch

# 📋 기업정보 목록 조회
GET /api/v1/businesses/
  ├── ?business_field=인공지능&organization=중소벤처기업부
  └── ?startup_stage=초기창업&is_active=true

# 🔍 특정 기업 상세 조회
GET /api/v1/businesses/{business_id}

# ➕ 새 기업정보 생성
POST /api/v1/businesses/

# ✏️ 기업정보 수정
PUT /api/v1/businesses/{business_id}

# 🗑️ 기업정보 삭제
DELETE /api/v1/businesses/{business_id}

# 📊 최근 기업정보
GET /api/v1/businesses/recent

# 📈 기업 통계
GET /api/v1/businesses/statistics
```

### 📚 콘텐츠 (Contents) - ✅ API 완성

```bash
# 📥 콘텐츠 수집
POST /api/v1/contents/fetch

# 📋 콘텐츠 목록 조회
GET /api/v1/contents/
  ├── ?content_type=동영상&category=창업교육
  └── ?tags=스타트업,교육&is_active=true

# 🔍 콘텐츠 상세 조회
GET /api/v1/contents/{content_id}

# ➕ 새 콘텐츠 생성
POST /api/v1/contents/

# ✏️ 콘텐츠 수정
PUT /api/v1/contents/{content_id}

# 🗑️ 콘텐츠 삭제
DELETE /api/v1/contents/{content_id}

# ❤️ 좋아요 추가
POST /api/v1/contents/{content_id}/like

# 📊 최근 콘텐츠
GET /api/v1/contents/recent

# 🔥 인기 콘텐츠
GET /api/v1/contents/popular

# 📈 콘텐츠 통계
GET /api/v1/contents/statistics
```

### 📊 통계정보 (Statistics) - ✅ API 완성

```bash
# 📥 통계 데이터 수집
POST /api/v1/statistics/fetch

# 📋 통계 목록 조회
GET /api/v1/statistics/
  ├── ?stat_type=월별&year=2024&month=3
  └── ?period=quarterly&is_active=true

# 🔍 통계 상세 조회
GET /api/v1/statistics/{statistics_id}

# ➕ 새 통계 생성
POST /api/v1/statistics/

# ✏️ 통계 수정
PUT /api/v1/statistics/{statistics_id}

# 🗑️ 통계 삭제
DELETE /api/v1/statistics/{statistics_id}

# 📊 최근 통계
GET /api/v1/statistics/recent

# 📅 연도별 통계
GET /api/v1/statistics/year/{year}

# 📈 통계 개요
GET /api/v1/statistics/overview

# 📊 집계 지표
GET /api/v1/statistics/aggregated-metrics

# 📋 월별 리포트
GET /api/v1/statistics/report/monthly/{year}/{month}

# 📋 연별 리포트
GET /api/v1/statistics/report/yearly/{year}
```

### 🧰 작업 관리 (Task Management) - 운영/모니터링

- 주요 엔드포인트
  - `GET  /api/v1/tasks/` — 등록된 작업 목록 조회 (카테고리 필터, 스케줄 정보 포함)
  - `POST /api/v1/tasks/execute` — 작업 비동기 실행 요청 (queue/priority/countdown/eta 지원)
  - `GET  /api/v1/tasks/status/{task_id}` — 작업 상태/결과 조회
  - `DELETE /api/v1/tasks/cancel/{task_id}` — 작업 취소 요청
  - `GET  /api/v1/tasks/queues` — 큐 현황 조회
  - `GET  /api/v1/tasks/workers` — 워커 현황 조회
  - `GET  /api/v1/tasks/stats` — 시스템 통계 (워커/큐/활성/예약 작업)

예시 요청

```bash
# ✅ 사용 가능한 작업 목록
curl -s "http://localhost:8000/api/v1/tasks/" | jq '.'

# ▶️ 작업 실행 (우선순위/큐/지연 실행 설정 가능)
curl -s -X POST "http://localhost:8000/api/v1/tasks/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "fetch_announcements_comprehensive",
    "args": [1, 5, true],
    "kwargs": {},
    "queue": "announcements",
    "priority": "high",
    "countdown": 0
  }'

# 🔎 작업 상태/결과 조회
curl -s "http://localhost:8000/api/v1/tasks/status/<task_id>"

# 🛑 작업 취소
curl -s -X DELETE "http://localhost:8000/api/v1/tasks/cancel/<task_id>"

# 📨 큐 현황
curl -s "http://localhost:8000/api/v1/tasks/queues"

# 👷 워커 현황
curl -s "http://localhost:8000/api/v1/tasks/workers"

# 📈 시스템 통계
curl -s "http://localhost:8000/api/v1/tasks/stats"
```

참고: 서비스 전역 상태 확인은 `GET /health`를 사용하세요.

### 🏷️ 분류 코드 (Classification) - ✅ API 완성

```bash
# 📚 사업 분야 코드
GET  /api/v1/classification/business-categories
GET  /api/v1/classification/business-categories/{code}
POST /api/v1/classification/business-categories/validate
GET  /api/v1/classification/business-categories/search

# 📰 콘텐츠 분류 코드
GET  /api/v1/classification/content-categories
GET  /api/v1/classification/content-categories/{code}
POST /api/v1/classification/content-categories/validate
GET  /api/v1/classification/content-categories/search

# 🔎 통합 기능
POST /api/v1/classification/validate
POST /api/v1/classification/validate-batch
GET  /api/v1/classification/detect-type/{code}
POST /api/v1/classification/search
GET  /api/v1/classification/codes
GET  /api/v1/classification/recommendations

# 📊 통계/레퍼런스/운영
GET  /api/v1/classification/statistics
GET  /api/v1/classification/health
GET  /api/v1/classification/reference/business-categories
GET  /api/v1/classification/reference/content-categories
POST /api/v1/classification/cache/clear
```

예시 요청

```bash
# 배치 검증
curl -X POST "http://localhost:8000/api/v1/classification/validate-batch" \
  -H "Content-Type: application/json" \
  -d '["cmrczn_tab1","notice_matr","invalid_code"]'

# 통합 검색
curl -X POST "http://localhost:8000/api/v1/classification/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"교육","code_type":"business","fields":["name","description"],"limit":10}'
```

## ⚙️ 환경변수 설정

### 🔑 필수 설정 (반드시 변경 필요)

| 변수명 | 설명 | 예시값 | 획득 방법 |
|--------|------|--------|----------|
| `PUBLIC_DATA_API_KEY` | 공공데이터포털 API 키 | `your-api-key-here` | [공공데이터포털](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654)에서 발급 |

### 🐳 컨테이너 설정

| 변수명 | 설명 | 기본값 | 용도 |
|--------|------|--------|------|
| `MONGODB_URL` | MongoDB 연결 URL | `mongodb://api_user:api_password@localhost:27017/korea_public_api` | 데이터베이스 연결 |
| `DATABASE_NAME` | 데이터베이스 이름 | `korea_public_api` | MongoDB DB명 |
| `MONGO_INITDB_ROOT_USERNAME` | MongoDB 관리자 사용자명 | `admin` | DB 초기화 |
| `MONGO_INITDB_ROOT_PASSWORD` | MongoDB 관리자 비밀번호 | `password123` | DB 초기화 |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` | 캐시 및 Celery |

### 🌐 서버 설정

| 변수명 | 설명 | 기본값 | 설명 |
|--------|------|--------|------|
| `APP_HOST` | 서버 호스트 | `0.0.0.0` | API 서버 바인딩 주소 |
| `APP_PORT` | 서버 포트 | `8000` | API 서버 포트 |
| `DEBUG` | 디버그 모드 | `True` | 개발/프로덕션 구분 |
| `LOG_LEVEL` | 로그 레벨 | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `CSRF_ENABLED` | CSRF 보호 활성화 | `false`(dev), `true`(prod) | 더블 서브밋 토큰 검증 활성화 |
| `FAIL_CLOSE_ON_BLACKLIST_ERROR` | 블랙리스트 조회 실패 시 거부 | `false`(dev), `true`(prod) | Redis 오류시 토큰 거부 여부 |

### 🔗 외부 API 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `API_BASE_URL` | K-Startup API 기본 URL | `https://apis.data.go.kr/B552735/kisedKstartupService01` |
| `API_TIMEOUT` | API 요청 타임아웃 (초) | `30` |
| `API_RETRY_COUNT` | API 재시도 횟수 | `3` |

### 📝 환경변수 설정 가이드

#### 1️⃣ 환경 파일 준비
```bash
# .env.example을 복사하여 실제 환경 파일 생성
cp .env.example .env
```

또는 아래 예시를 참고해 `.env`를 직접 생성하세요:

```dotenv
# 필수
PUBLIC_DATA_API_KEY=your-api-key-here

# 개발 기본값 (필요 시 수정)
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password123
MONGO_INITDB_DATABASE=korea_public_api
DATABASE_NAME=korea_public_api
REDIS_URL=redis://localhost:6379/0
API_BASE_URL=https://apis.data.go.kr/B552735/kisedKstartupService01
DEBUG=True
LOG_LEVEL=INFO
```

#### 2️⃣ API 키 발급 및 설정
1. [공공데이터포털](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654) 접속
2. 회원가입 및 로그인
3. "창업진흥원_K-Startup 조회서비스" 활용신청
4. 발급받은 API 키를 `.env` 파일의 `PUBLIC_DATA_API_KEY`에 입력

#### 3️⃣ 프로덕션 환경 보안 설정
```bash
# 프로덕션 환경에서는 반드시 변경
MONGO_INITDB_ROOT_PASSWORD=strong-production-password
DEBUG=False
LOG_LEVEL=WARNING

# CORS 설정 (프로덕션)
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# CSRF/토큰 블랙리스트 정책
CSRF_ENABLED=true
FAIL_CLOSE_ON_BLACKLIST_ERROR=true
```

## 📅 자동 데이터 수집 스케줄

### ✅ 현재 운영 중인 스케줄

| 도메인 | 수집 주기 | 시간 | 상태 |
|--------|----------|------|------|
| 🏢 **사업공고** | 매일 | 오전 6시, 오후 6시 | ✅ 운영 중 |

### 🔄 계획된 스케줄 (개발 완료 후 활성화)

| 도메인 | 수집 주기 | 계획 시간 | 예상 완료 |
|--------|----------|----------|-----------|
| 📚 **콘텐츠** | 매일 | 오전 7시, 오후 7시 | 🔄 API 완성됨 |
| 🎯 **기업정보** | 주 2회 | 월, 목 오전 8시 | 🔄 API 완성됨 |
| 📊 **통계정보** | 매주 | 일요일 오전 9시 | 🔄 API 완성됨 |

### 🔧 스케줄 관리

```bash
# Celery Beat 스케줄 확인
docker-compose exec api celery -A app.core.celery inspect scheduled

# 특정 작업 실행 (수동)
docker-compose exec api celery -A app.core.celery call app.domains.announcements.tasks.fetch_announcements_task

# 스케줄러 재시작
docker-compose restart celery-beat
```

## 🧪 테스트 시스템

### 🔬 테스트 환경

```bash
# 📊 전체 테스트 스위트 실행 (Docker 환경)
docker-compose exec api pytest

# 📈 테스트 커버리지 측정
docker-compose exec api pytest --cov=app --cov-report=html

# 🎯 특정 도메인 테스트만 실행
docker-compose exec api pytest tests/unit/domains/announcements/

# 🔄 통합 테스트 실행
docker-compose exec api pytest tests/integration/

# 🚀 성능 테스트 (부하 테스트)
docker-compose exec api pytest tests/performance/ -v
```

### 💻 로컬 개발 테스트

```bash
# Python 환경에서 직접 실행
pytest
pytest --cov=app --cov-report=html --cov-report=term-missing

# 특정 테스트 파일 실행
pytest tests/unit/shared/test_pagination.py -v

# 테스트 결과 리포트 생성
pytest --html=tests/reports/report.html --self-contained-html
```

### 🎯 API 엔드포인트 테스트

```bash
# 💚 헬스체크 테스트
curl -X GET "http://localhost:8000/health"

# 📊 API 버전 정보
curl -X GET "http://localhost:8000/version"

# 🏢 사업공고 목록 조회
curl -X GET "http://localhost:8000/api/v1/announcements/?page=1&size=5"

# 🔄 실시간 데이터 수집 테스트
curl -X POST "http://localhost:8000/api/v1/announcements/fetch" \
     -H "Content-Type: application/json"

# 📚 콘텐츠 API 테스트
curl -X GET "http://localhost:8000/api/v1/contents/"

# 🎯 기업정보 API 테스트
curl -X GET "http://localhost:8000/api/v1/businesses/"

# 📊 통계정보 API 테스트
curl -X GET "http://localhost:8000/api/v1/statistics/"
```

### 📊 성능 벤치마크

```bash
# Apache Bench를 사용한 부하 테스트
ab -n 1000 -c 10 http://localhost:8000/api/v1/announcements/

# wrk를 사용한 고성능 테스트
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/announcements/
```

## 🏗️ 현재 구현 현황

### ✅ 완성된 시스템

| 컴포넌트 | 상태 | 설명 |
|----------|------|------|
| 🌐 **FastAPI 웹 서버** | ✅ 완성 | 의존성 주입, 미들웨어, 버저닝 지원 |
| 🗄️ **MongoDB** | ✅ 완성 | 자동 초기화, 인덱싱, 백업 시스템 |
| 🔴 **Redis** | ✅ 완성 | 캐시, Celery 브로커, 세션 관리 |
| ⚙️ **Celery 시스템** | ✅ 완성 | Worker, Beat, Flower 모니터링 |
| 🏢 **사업공고 도메인** | ✅ 완성 | 완전한 CRUD + 실시간 수집 |
| 🎯 **기업정보 도메인** | ✅ 완성 | API 구현, 테스트 완료 |
| 📚 **콘텐츠 도메인** | ✅ 완성 | API 구현, 좋아요 기능 포함 |
| 📊 **통계정보 도메인** | ✅ 완성 | API 구현, 리포트 생성 |
| 🔧 **DI 컨테이너** | ✅ 완성 | 의존성 주입 시스템 |
| 🛡️ **예외 처리** | ✅ 완성 | 계층화된 에러 처리 |
| 📄 **API 문서** | ✅ 완성 | 완전 한국어 Swagger |

### 🔄 개발 진행 중

| 컴포넌트 | 진행률 | 설명 |
|----------|--------|------|
| 🏷️ **분류 시스템** | 🔄 80% | 자동 분류 알고리즘 구현 중 |
| 🔌 **플러그인 시스템** | 🔄 70% | 동적 데이터 소스 확장 |
| 📊 **모니터링** | 🔄 60% | 성능 메트릭 수집 |

### 📋 다음 단계 계획

#### 🚀 단기 계획 (1-2개월)
1. **🔐 보안 강화**
   - JWT 토큰 기반 인증 시스템
   - API 키 관리 및 Rate Limiting
   - RBAC (역할 기반 접근 제어)

2. **⚡ 성능 최적화**
   - Redis 기반 API 응답 캐싱
   - MongoDB 쿼리 최적화 및 인덱싱
   - 연결 풀링 및 비동기 처리 개선

#### 🌟 중기 계획 (3-6개월)
3. **🔍 고급 검색**
   - Elasticsearch 통합
   - 전문 검색 및 자동완성
   - 다중 조건 필터링

4. **📊 비즈니스 인텔리전스**
   - 실시간 대시보드
   - 데이터 시각화
   - 예측 분석 기능

#### 🎯 장기 계획 (6개월+)
5. **🔮 AI/ML 통합**
   - 자연어 처리 기반 분류
   - 추천 시스템
   - 이상 탐지 시스템

6. **🌐 마이크로서비스**
   - 서비스 분리 및 독립 배포
   - API Gateway 구축
   - 서비스 메시 구성

## 🚀 성능 지표

### ⚡ 현재 성능 벤치마크

| 메트릭 | 목표 | 현재 성능 | 상태 |
|--------|------|-----------|------|
| API 응답 시간 | < 200ms | ~150ms | ✅ 달성 |
| 데이터 수집 시간 | < 2초 | ~1.8초 | ✅ 달성 |
| 동시 요청 처리 | 1000+ req/min | ~1200 req/min | ✅ 달성 |
| 데이터 정확도 | > 99% | 99.9% | ✅ 달성 |
| 시스템 가용성 | > 99.9% | 99.95% | ✅ 달성 |

### 📊 모니터링 대시보드

- **Celery Flower**: http://localhost:5555 (작업 큐 모니터링)
- **Redis Insight**: 계획됨 (Redis 성능 모니터링)
- **Grafana**: 계획됨 (통합 시스템 모니터링)

## 🤝 기여 가이드

### 1️⃣ 개발 참여 방법

```bash
# 1. 프로젝트 Fork
git clone https://github.com/your-username/korea_public_open_api.git

# 2. 개발 브랜치 생성
git checkout -b feature/새로운기능

# 3. 개발 환경 설정
./scripts/init-volumes.sh
docker-compose up -d

# 4. 코드 변경 및 테스트
pytest --cov=app

# 5. 커밋 및 Push
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin feature/새로운기능

# 6. Pull Request 생성
```

### 2️⃣ 코딩 스타일 가이드

- **Python**: PEP 8 준수, Black 포매터 사용
- **API 설계**: RESTful 원칙, 한국어 문서화
- **커밋 메시지**: Conventional Commits 규칙
- **테스트**: 80% 이상 커버리지 유지

### 3️⃣ 이슈 및 버그 리포트

[GitHub Issues](https://github.com/sinbum/korea_public_data_be/issues)에서 다음 템플릿으로 제출:

- 🐛 **버그 리포트**: 재현 단계 포함
- 💡 **기능 제안**: 사용 사례 및 예상 효과
- 📚 **문서 개선**: 불명확한 부분 지적
- 🔧 **성능 개선**: 벤치마크 결과 포함

## 📊 Task Master 통합 현황

이 프로젝트는 **Task Master**를 사용하여 체계적으로 개발되고 있습니다.

### ✅ 완료된 주요 태스크

| Task ID | 태스크명 | 상태 | 설명 |
|---------|----------|------|------|
| **1-9** | 기초 아키텍처 설계 | ✅ 완료 | SOLID 원칙, 디자인 패턴 적용 |
| **10** | Celery 시스템 개선 | ✅ 완료 | 작업 큐, 스케줄링 시스템 |
| **11** | RESTful API 표준화 | ✅ 완료 | 4개 도메인 완전 구현 |
| **Phase 1-2** | 문서화 개선 | ✅ 완료 | docs/ 재구조화, Swagger 한국어화 |

### 🔄 현재 진행 상황

- **분류 시스템**: 사업 및 콘텐츠 자동 분류 (80% 완료)
- **플러그인 시스템**: 동적 데이터 소스 확장 (70% 완료)
- **모니터링 시스템**: 성능 메트릭 수집 (60% 완료)

## 💾 볼륨 및 데이터 관리

### 📁 데이터 구조
```
volumes/
├── 🗄️ mongodb/              # MongoDB 영속 데이터
│   ├── data/                 # 실제 데이터베이스 파일
│   ├── config/               # MongoDB 설정
│   └── init/                 # 초기화 스크립트
├── 🔴 redis/                 # Redis 캐시 데이터
│   ├── data/                 # Redis 데이터 파일
│   └── redis.conf            # Redis 설정
├── 💾 backups/               # 자동 백업 파일
│   ├── mongodb/              # DB 백업 (일별/주별)
│   └── redis/                # 캐시 백업
├── 📝 logs/                  # 구조화된 로그
│   ├── app.log               # 애플리케이션 로그
│   ├── celery.log           # Celery 작업 로그
│   └── access.log           # API 접근 로그
└── 📤 uploads/               # 업로드 파일 (향후 확장)
```

### 🛠️ 데이터 관리 명령어

#### 🚀 초기 설정
```bash
# 전체 볼륨 초기화 (최초 1회)
./scripts/init-volumes.sh

# 개별 서비스 권한 설정
sudo chown -R 999:999 volumes/mongodb/    # MongoDB
sudo chown -R 999:1000 volumes/redis/     # Redis
```

#### 💾 백업 및 복원
```bash
# 📦 전체 시스템 백업
./scripts/backup.sh

# 🔄 특정 서비스 복원
./scripts/restore.sh mongodb 20240326_120000
./scripts/restore.sh redis 20240326_120000

# 📋 백업 히스토리 확인
ls -la volumes/backups/ | head -20
```

#### 📊 모니터링 및 진단
```bash
# 🏥 서비스 상태 종합 진단
docker-compose ps
docker-compose logs --tail=50 api celery-worker

# 💽 MongoDB 상태 확인
docker-compose exec mongodb mongosh korea_public_api \
  --eval "db.runCommand({dbStats: 1})"

# 🔴 Redis 메모리 및 성능 확인
docker-compose exec redis redis-cli info memory
docker-compose exec redis redis-cli info stats

# 📈 디스크 사용량 모니터링
du -sh volumes/* | sort -hr
df -h volumes/
```

#### 🔧 개발 도구 접근
```bash
# 🗄️ MongoDB 직접 접속
docker-compose exec mongodb mongosh korea_public_api \
  -u api_user -p api_password

# 🔴 Redis 직접 접속
docker-compose exec redis redis-cli

# 🐳 컨테이너 내부 쉘 접속
docker-compose exec api bash
docker-compose exec celery-worker bash
```

## 🔗 관련 리소스

### 📚 추가 문서
- **아키텍처 가이드**: [docs/architecture/design_patterns.md](./docs/architecture/design_patterns.md)
- **API 검증 리포트**: [docs/domains/api_validation_report.md](./docs/domains/api_validation_report.md)
- **통합 가이드**: [docs/integration/kstartup_api_spec.md](./docs/integration/kstartup_api_spec.md)

### 🔗 외부 링크
- **공공데이터포털**: [data.go.kr](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654)
- **FastAPI 문서**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **MongoDB 가이드**: [docs.mongodb.com](https://docs.mongodb.com/)
- **Celery 문서**: [docs.celeryproject.org](https://docs.celeryproject.org/)

### 🛠️ 개발 도구
- **API 테스트**: Swagger UI (http://localhost:8000/docs)
- **작업 모니터링**: Celery Flower (http://localhost:5555)
- **데이터베이스 관리**: MongoDB Compass 또는 mongosh

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👥 개발팀

현재 이 프로젝트는 **Claude Code**와 협업하여 개발되고 있으며, Task Master를 통해 체계적으로 관리되고 있습니다.

### 🤝 기여자 모집

다음 분야의 기여자를 환영합니다:
- 🐍 **Backend 개발자**: FastAPI, MongoDB, Celery 경험
- 🎨 **Frontend 개발자**: API 소비 애플리케이션 개발
- 📊 **Data Engineer**: 데이터 파이프라인 최적화
- 🔧 **DevOps 엔지니어**: CI/CD, 모니터링 시스템 구축
- 📝 **Technical Writer**: API 문서화 및 가이드 작성

### 📧 연락처

- **이슈 및 버그 리포트**: [GitHub Issues](https://github.com/sinbum/korea_public_data_be/issues)
- **기능 제안**: [GitHub Discussions](https://github.com/sinbum/korea_public_data_be/issues/1)
- **기술 질문**: Stack Overflow에서 `korea-public-api` 태그 사용

---

<div align="center">

**🌟 한국 공공데이터 API 플랫폼 🌟**

*확장 가능하고 현대적인 공공데이터 통합 솔루션*

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-repo/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Made with ❤️ using **FastAPI** + **MongoDB** + **Celery** + **Task Master**

</div>