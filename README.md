# 한국 공공데이터 API 서비스

창업진흥원 K-Startup 데이터 수집 및 제공을 위한 FastAPI 백엔드 서비스

## 🚀 기능

- **사업공고 정보 수집 및 제공**
- **콘텐츠 정보 수집 및 제공** (구현 예정)
- **통계 정보 수집 및 제공** (구현 예정)
- **사업정보 수집 및 제공** (구현 예정)
- **자동 데이터 수집 스케줄러**
- **RESTful API 제공**

## 🛠️ 기술 스택

- **Backend**: FastAPI 0.104.1
- **Database**: MongoDB (Motor 3.3.2)
- **Task Queue**: Celery + Redis
- **HTTP Client**: httpx
- **Validation**: Pydantic 2.5.0
- **Container**: Docker & Docker Compose

## 📁 프로젝트 구조

```
korea_public_open_api/
├── app/                        # 애플리케이션 소스코드
│   ├── core/                   # 핵심 설정
│   │   ├── config.py          # 환경설정
│   │   └── database.py        # MongoDB 연결
│   ├── domains/               # 도메인별 분리
│   │   ├── announcements/     # 사업공고 (완성)
│   │   ├── contents/          # 콘텐츠 (모델만)
│   │   ├── statistics/        # 통계정보 (모델만)
│   │   └── businesses/        # 사업정보 (모델만)
│   ├── shared/                # 공통 기능
│   │   ├── models.py         # 공통 모델
│   │   ├── schemas.py        # API 스키마
│   │   ├── exceptions.py     # 예외 처리
│   │   └── clients/          # API 클라이언트
│   ├── scheduler/             # 데이터 수집 스케줄러
│   └── main.py               # FastAPI 엔트리포인트
├── volumes/                   # 로컬 볼륨 관리
│   ├── mongodb/              # MongoDB 데이터
│   ├── redis/                # Redis 데이터
│   ├── logs/                 # 애플리케이션 로그
│   ├── backups/              # 백업 파일
│   ├── uploads/              # 업로드 파일
│   └── tmp/                  # 임시 파일
├── scripts/                  # 관리 스크립트
│   ├── init-volumes.sh      # 볼륨 초기화
│   ├── backup.sh            # 데이터 백업
│   └── restore.sh           # 데이터 복원
├── docs/                     # 문서
│   └── API_GUIDE.md         # 상세 API 가이드
├── docker-compose.yml        # Docker 서비스 구성
├── Dockerfile               # 컨테이너 이미지 정의
├── requirements.txt         # Python 의존성
└── .env                     # 환경변수
```

## 🚀 빠른 시작

### 1. 프로젝트 설정

```bash
# 저장소 클론
git clone <repository-url>
cd korea_public_open_api

# 환경변수 파일 설정
cp .env.example .env
# .env 파일에서 PUBLIC_DATA_API_KEY를 실제 키로 변경

# 볼륨 초기화 (최초 1회만)
./scripts/init-volumes.sh
```

### 2. Docker로 실행 (권장)

```bash
# 전체 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 실시간 로그 확인
docker-compose logs -f api
```

### 3. 서비스 접속

서비스가 시작되면 다음 URL에서 접속할 수 있습니다:

- **🌐 API 서버**: http://localhost:8000
- **📖 API 문서 (Swagger)**: http://localhost:8000/docs
- **📚 API 문서 (ReDoc)**: http://localhost:8000/redoc
- **🌺 Celery 모니터링 (Flower)**: http://localhost:5555
- **🗄️ MongoDB**: localhost:27017 (admin/password123)
- **🔴 Redis**: localhost:6379

### 4. 로컬 개발 환경 (선택사항)

```bash
# Python 의존성 설치
pip install -r requirements.txt

# 데이터베이스만 Docker로 실행
docker-compose up -d mongodb redis

# FastAPI 서버 로컬 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Celery Worker (별도 터미널)
celery -A app.scheduler.celery_app worker --loglevel=info

# Celery Beat 스케줄러 (별도 터미널)
celery -A app.scheduler.celery_app beat --loglevel=info
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **🎨 Swagger UI**: http://localhost:8000/docs (대화형 API 테스트)
- **📖 ReDoc**: http://localhost:8000/redoc (읽기 전용 문서)
- **📋 상세 가이드**: [docs/API_GUIDE.md](./docs/API_GUIDE.md)

### 문서 특징
- ✅ **상세한 예제**: 모든 API에 실제 사용 가능한 예제 포함
- ✅ **에러 처리**: 모든 가능한 에러 시나리오 문서화
- ✅ **대화형 테스트**: Swagger UI에서 직접 API 테스트 가능
- ✅ **다국어 지원**: 한국어 설명 및 예제 제공

## 🔄 주요 API 엔드포인트

### 사업공고 (Announcements)

```bash
# 공공데이터에서 사업공고 수집
POST /api/v1/announcements/fetch

# 저장된 사업공고 목록 조회
GET /api/v1/announcements/

# 특정 사업공고 조회
GET /api/v1/announcements/{announcement_id}

# 새 사업공고 생성
POST /api/v1/announcements/

# 사업공고 수정
PUT /api/v1/announcements/{announcement_id}

# 사업공고 삭제
DELETE /api/v1/announcements/{announcement_id}
```

## 🔧 환경변수 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `MONGODB_URL` | MongoDB 연결 URL (인증 포함) | `mongodb://api_user:api_password@localhost:27017/korea_public_api` |
| `DATABASE_NAME` | 데이터베이스 이름 | `korea_public_api` |
| `MONGO_INITDB_ROOT_USERNAME` | MongoDB 관리자 사용자명 | `admin` |
| `MONGO_INITDB_ROOT_PASSWORD` | MongoDB 관리자 비밀번호 | `password123` |
| `PUBLIC_DATA_API_KEY` | 공공데이터포털 API 키 | **필수 설정** |
| `API_BASE_URL` | 공공데이터 API 기본 URL | `https://apis.data.go.kr/B552735/kisedKstartupService01` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `APP_HOST` | 서버 호스트 | `0.0.0.0` |
| `APP_PORT` | 서버 포트 | `8000` |
| `DEBUG` | 디버그 모드 | `True` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |

### 📝 환경변수 설정 방법

1. `.env.example`을 `.env`로 복사
2. 공공데이터포털에서 API 키 발급: [링크](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654)
3. `PUBLIC_DATA_API_KEY`에 발급받은 키 입력
4. 필요시 다른 설정값 수정

## 📊 데이터 수집 스케줄

- **사업공고**: 매일 자동 수집
- **콘텐츠**: 매일 자동 수집 (구현 예정)
- **통계정보**: 매주 자동 수집 (구현 예정)
- **사업정보**: 매주 자동 수집 (구현 예정)

## 🧪 테스트

```bash
# 테스트 실행
docker-compose exec api pytest

# 커버리지 포함 테스트
docker-compose exec api pytest --cov=app

# 로컬에서 테스트 (개발환경)
pytest
pytest --cov=app --cov-report=html

# API 엔드포인트 테스트
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8000/api/v1/announcements/"
```

## 🚀 서비스 구성

### 현재 구현된 서비스

- ✅ **FastAPI 웹 서버**: 메인 API 서버
- ✅ **MongoDB**: 데이터베이스 (자동 초기화)
- ✅ **Redis**: 캐시 및 Celery 브로커
- ✅ **Celery Worker**: 비동기 작업 처리
- ✅ **Celery Beat**: 스케줄 작업 관리
- ✅ **Celery Flower**: 작업 모니터링 UI
- ✅ **사업공고 도메인**: 완전한 CRUD API

### 📝 다음 구현 예정

1. **🏗️ 나머지 도메인 완성**
   - 콘텐츠 도메인 (Service, Router)
   - 통계정보 도메인 (Service, Router)  
   - 사업정보 도메인 (Service, Router)

2. **🔐 보안 및 인증**
   - JWT 토큰 기반 인증
   - API 키 관리
   - Rate Limiting

3. **⚡ 성능 최적화**
   - API 응답 캐싱 (Redis)
   - 데이터베이스 쿼리 최적화
   - 페이지네이션 개선

4. **🔍 고급 기능**
   - 전문 검색 엔진 (Elasticsearch)
   - 실시간 알림 (WebSocket)
   - 파일 업로드 처리

5. **📊 모니터링 및 로깅**
   - Prometheus + Grafana
   - 구조화된 로깅
   - 알림 시스템

6. **🧪 품질 보증**
   - 단위 테스트 확장
   - 통합 테스트 추가
   - CI/CD 파이프라인

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📁 볼륨 관리

### 볼륨 구조
```
volumes/
├── mongodb/           # MongoDB 데이터
│   ├── data/         # 데이터베이스 파일 (Git 제외)
│   ├── config/       # 설정 파일 (Git 제외)
│   └── init/         # 초기화 스크립트 (Git 포함)
│       └── init.js   # DB 및 컬렉션 초기화
├── redis/            # Redis 데이터
│   ├── data/         # Redis 데이터 파일 (Git 제외)
│   └── redis.conf    # Redis 설정 (Git 포함)
├── backups/          # 백업 파일 (Git 제외)
│   ├── mongodb/      # MongoDB 백업
│   └── redis/        # Redis 백업
├── logs/             # 애플리케이션 로그 (Git 제외)
├── uploads/          # 업로드된 파일 (Git 제외)
└── tmp/              # 임시 파일 (Git 제외)
```

### 🛠️ 볼륨 관리 명령어

#### 초기 설정
```bash
# 볼륨 초기화 (최초 1회)
./scripts/init-volumes.sh

# 권한 설정 (Linux/macOS)
sudo chown -R 999:999 volumes/mongodb/
sudo chown -R 999:1000 volumes/redis/
```

#### 백업 및 복원
```bash
# 전체 데이터 백업
./scripts/backup.sh

# 특정 데이터 복원
./scripts/restore.sh mongodb 20240301_143000
./scripts/restore.sh redis 20240301_143000

# 백업 파일 목록 확인
ls -la volumes/backups/
```

#### 상태 모니터링
```bash
# 서비스 상태 확인
docker-compose ps

# MongoDB 상태
docker-compose exec mongodb mongosh --eval "db.stats()"
docker-compose exec mongodb mongosh --eval "db.runCommand({connectionStatus: 1})"

# Redis 상태
docker-compose exec redis redis-cli info memory
docker-compose exec redis redis-cli info stats

# 디스크 사용량 확인
du -sh volumes/*

# 로그 확인
docker-compose logs -f api
tail -f volumes/logs/*.log
```

#### 개발 도구
```bash
# MongoDB 접속
docker-compose exec mongodb mongosh korea_public_api -u api_user -p api_password

# Redis 접속
docker-compose exec redis redis-cli

# 컨테이너 내부 접속
docker-compose exec api bash
```

### 🔧 볼륨 매핑

| 컨테이너 경로 | 로컬 경로 | 설명 | Git 포함 |
|---------------|-----------|------|----------|
| `/app/app` | `./app` | 소스코드 (실시간 반영) | ✅ |
| `/data/db` | `./volumes/mongodb/data` | MongoDB 데이터 | ❌ |
| `/data/configdb` | `./volumes/mongodb/config` | MongoDB 설정 | ❌ |
| `/docker-entrypoint-initdb.d` | `./volumes/mongodb/init` | 초기화 스크립트 | ✅ |
| `/data` | `./volumes/redis/data` | Redis 데이터 | ❌ |
| `/app/logs` | `./volumes/logs` | 애플리케이션 로그 | ❌ |
| `/app/uploads` | `./volumes/uploads` | 업로드 파일 | ❌ |
| `/app/tmp` | `./volumes/tmp` | 임시 파일 | ❌ |
| `/backups` | `./volumes/backups` | 백업 파일 | ❌ |

### ✨ 주요 특징

- 🏠 **로컬 볼륨 관리**: 모든 데이터가 `volumes/` 디렉토리에 저장
- 💾 **자동 백업/복원**: 스크립트를 통한 간편한 데이터 관리
- 🔄 **실시간 개발**: 소스코드 변경 시 자동 재로드
- 📦 **데이터 영속성**: 컨테이너 재시작 시에도 데이터 유지
- 🔒 **보안**: 비root 사용자로 컨테이너 실행
- 🏥 **헬스체크**: 모든 서비스의 상태 자동 모니터링
- 🌺 **작업 모니터링**: Celery Flower를 통한 비동기 작업 추적
- 🔗 **네트워크 격리**: 전용 Docker 네트워크로 서비스 격리

### ⚠️ 주의사항

1. **백업 필수**: 중요한 데이터는 정기적으로 백업하세요
2. **권한 관리**: Linux/macOS에서는 적절한 파일 권한 설정이 필요합니다
3. **디스크 공간**: 로그와 백업 파일이 계속 증가할 수 있습니다
4. **보안**: 프로덕션 환경에서는 기본 비밀번호를 변경하세요

## 📞 문의사항

프로젝트에 대한 질문이나 개선사항이 있으시면 이슈를 생성해 주세요.