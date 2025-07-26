# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean Public Data API service that collects and serves K-Startup data from Korea's public data portal. The service is built with FastAPI, MongoDB, and Celery for asynchronous task processing.

**Core Architecture**: Domain-driven design with clear separation between domains (announcements, contents, statistics, businesses). Currently only the announcements domain is fully implemented.

## Development Commands

### Docker Environment (Recommended)
```bash
# Start all services
docker-compose up -d

# View real-time logs
docker-compose logs -f api

# Check service status
docker-compose ps

# Execute commands inside containers
docker-compose exec api bash
docker-compose exec mongodb mongosh korea_public_api -u api_user -p api_password
docker-compose exec redis redis-cli

# Stop services
docker-compose down
```

### Local Development
```bash
# Start dependencies only
docker-compose up -d mongodb redis

# Run FastAPI locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (separate terminal)
celery -A app.core.celery worker --loglevel=info

# Run Celery Beat scheduler (separate terminal)
celery -A app.core.celery beat --loglevel=info
```

### Testing
```bash
# Run tests in container
docker-compose exec api pytest

# Run tests with coverage
docker-compose exec api pytest --cov=app

# Local testing
pytest
pytest --cov=app --cov-report=html
```

### Data Management
```bash
# Initialize volumes (first time only)
./scripts/init-volumes.sh

# Backup data
./scripts/backup.sh

# Restore data
./scripts/restore.sh mongodb 20240301_143000
```

## Architecture Details

### Domain Structure
- **announcements/**: Fully implemented CRUD domain for business announcements
- **contents/**: Model only, service and router pending
- **statistics/**: Model only, service and router pending  
- **businesses/**: Model only, service and router pending

### Core Components
- **app/core/**: Configuration, database connection, Celery setup
- **app/shared/**: Common models, schemas, exceptions, API clients
- **app/scheduler/**: Celery tasks for data collection
- **volumes/**: Persistent data storage (excluded from git)

### Database Patterns
- Uses pymongo with MongoDB, **not** Motor (async driver)
- Document models use Pydantic with custom `id` field handling
- Repository pattern is not yet implemented - services directly use database collections
- ObjectId conversion handled in service layer: `doc["id"] = str(doc["_id"])`

### API Client Architecture
Currently uses a basic `PublicDataAPIClient` class, but the architecture is designed for expansion to support multiple public data sources.

### Dependency Injection
Simple factory functions in routers: `def get_announcement_service() -> AnnouncementService`
FastAPI `Depends()` is used but no formal DI container exists.

## Key Configuration

### Environment Variables
Required: `PUBLIC_DATA_API_KEY` from data.go.kr
Database: MongoDB connection via `MONGODB_URL` 
Cache: Redis via `REDIS_URL`
See README.md for complete list.

### API Endpoints
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
- **Main API**: `/api/v1/announcements/`

### External API Integration
Integrates with Korea's public data portal (data.go.kr) for K-Startup data:
- Base URL: `https://apis.data.go.kr/B552735/kisedKstartupService01`
- Currently supports announcement data collection via `/fetch` endpoints

## Current Implementation Status

**Completed**:
- Announcements domain (full CRUD + data fetching)
- Basic FastAPI setup with proper error handling
- MongoDB integration with document models
- Celery task queue setup
- Docker containerization
- Comprehensive Swagger documentation

**Pending Implementation**:
- Other domains (contents, statistics, businesses) - models exist but need services/routers
- Repository pattern implementation
- Proper dependency injection system  
- Abstract base classes for API clients
- Data source management system
- Unified response models across domains

## Important Technical Notes

1. **MongoDB ObjectId Handling**: Services manually convert `_id` to `id` string field for Pydantic models
2. **Error Handling**: Custom exception handlers in `shared/exceptions.py`
3. **API Client**: Single `PublicDataAPIClient` class handles all external API calls
4. **Data Transformation**: Service layer handles conversion from external API format to internal models
5. **Logging**: Structured logging throughout with appropriate log levels

## Next Development Priorities

Based on current codebase analysis, focus on:
1. Implementing abstract base classes for Repository and API Client patterns
2. Adding dependency injection container
3. Completing remaining domains (contents, statistics, businesses)
4. Adding data source configuration management
5. Implementing unified response models and error handling

## Development Patterns

- Services handle business logic and external API integration
- Routers are thin, focusing on request/response transformation
- Models use Pydantic for validation and serialization
- Database operations are synchronous using pymongo
- Celery tasks are defined separately from domain logic


# Korean Public Open API Platform - Product Requirements Document

- 아래는 현재 task-master 에서 프로젝트를 진행중인 내용 및 목표이다.

## Project Overview

### Purpose
현재 창업정보 API만 제공하는 시스템을 확장 가능한 공공데이터 API 플랫폼으로 개선하여, 다양한 정부 공공데이터를 유동적으로 통합하고 제공할 수 있는 시스템 구축

### Current State
- FastAPI + MongoDB + Celery + Redis 아키텍처
- 창업정보(K-Startup) API만 지원
- 기본적인 도메인 구조 존재 (announcements, businesses, contents, data_sources, statistics)
- API가 불완전한 상태로 안정성 문제

### Target Goals
1. 확장 가능한 멀티 공공데이터 API 플랫폼 구축
2. SOLID 원칙과 디자인 패턴을 적용한 아키텍처 개선
3. 가독성 좋은 패키지 구조 유지
4. 완전한 Swagger 문서화
5. 개발 과정에서의 지식 관리 체계

## Technical Requirements

### Architecture Principles
- **Single Responsibility**: 각 모듈은 단일 책임
- **Open/Closed**: 새로운 공공데이터 API 추가 시 기존 코드 변경 없이 확장 가능
- **Liskov Substitution**: 다양한 데이터 소스를 동일한 인터페이스로 처리
- **Interface Segregation**: 클라이언트별 필요한 인터페이스만 의존
- **Dependency Inversion**: 구체적 구현보다 추상화에 의존

### Design Patterns
- **Strategy Pattern**: 다양한 API 클라이언트 전략
- **Factory Pattern**: 데이터 소스별 서비스 생성
- **Repository Pattern**: 데이터 접근 계층 추상화
- **Observer Pattern**: 데이터 변경 알림
- **Template Method**: 공통 API 호출 흐름

### Core Components

#### 1. Data Source Management
- 동적 데이터 소스 등록/해제
- 데이터 소스별 설정 관리
- API 키 및 인증 정보 관리
- 데이터 수집 스케줄링

#### 2. API Client Framework
- 공통 API 클라이언트 인터페이스
- 다양한 공공데이터 API 통합 (K-Startup, 공공데이터포털 등)
- 에러 처리 및 재시도 로직
- 응답 데이터 표준화

#### 3. Data Processing Pipeline
- 수집된 데이터 정규화
- 데이터 품질 검증
- 중복 데이터 처리
- 데이터 변환 및 enrichment

#### 4. Service Layer
- 비즈니스 로직 캡슐화
- 도메인 서비스 (공고, 기업, 컨텐츠 등)
- 크로스 도메인 서비스
- 캐싱 전략

#### 5. API Layer
- RESTful API 제공
- GraphQL 지원 고려
- 완전한 OpenAPI(Swagger) 문서
- API 버저닝 전략

## Functional Requirements

### 1. Multi-Source Data Integration
- K-Startup API 완전 통합
- 새로운 공공데이터 API 추가 지원
- 데이터 소스별 독립적 처리
- 통합 검색 및 필터링

### 2. Data Management
- 실시간 데이터 수집
- 배치 데이터 처리
- 데이터 캐싱 및 동기화
- 데이터 아카이빙

### 3. API Features
- 통합공고 조회 (지원사업 구분코드 기반)
- 컨텐츠 분류 (컨텐츠 구분코드 기반)
- 기업정보 조회
- 통계 정보 제공
- 실시간 알림 기능

### 4. Administration
- 데이터 소스 관리 UI
- 시스템 모니터링
- API 사용량 추적
- 로그 관리

## Non-Functional Requirements

### 1. Performance
- 응답시간 < 200ms (캐시된 데이터)
- 응답시간 < 2초 (실시간 데이터)
- 동시 요청 1000+ 처리 가능
- 99.9% 가용성

### 2. Scalability
- 수평 확장 가능한 아키텍처
- 마이크로서비스 패턴 적용 가능
- 로드 밸런싱 지원
- 데이터베이스 샤딩 고려

### 3. Security
- API 키 인증
- Rate limiting
- 데이터 암호화
- 로그 보안

### 4. Maintainability
- 높은 테스트 커버리지 (>80%)
- 코드 품질 검증
- 자동화된 배포
- 완전한 문서화

## Implementation Plan

### Phase 1: Architecture Refactoring
1. 공통 인터페이스 및 추상화 계층 설계
2. 현재 K-Startup API 클라이언트 리팩토링
3. Repository 패턴 적용
4. 서비스 계층 개선
5. 의존성 주입 구조 구축

### Phase 2: Multi-Source Support
1. 데이터 소스 관리 시스템 구축
2. 새로운 API 클라이언트 프레임워크
3. 데이터 파이프라인 구현
4. 통합 검색 기능

### Phase 3: Enhanced Features
1. 고급 필터링 및 정렬
2. 실시간 알림 시스템
3. 통계 및 분석 기능
4. 관리자 대시보드

### Phase 4: Optimization & Monitoring
1. 성능 최적화
2. 모니터링 시스템 구축
3. 자동화된 테스트
4. 배포 파이프라인

## Documentation Requirements

### 1. Technical Documentation
- API 명세서 (OpenAPI/Swagger)
- 아키텍처 문서
- 데이터베이스 스키마
- 배포 가이드

### 2. Development Process
- Q_and_A.md: 개발 중 질문사항 기록
- CLAUDE.local.md: 학습 내용 및 중요 결정사항 기록
- 코드 리뷰 가이드라인
- 기여 가이드

### 3. Integration Guides
- 새로운 데이터 소스 통합 가이드
- API 클라이언트 개발 가이드
- 플러그인 개발 가이드

## Success Metrics

### Technical Metrics
- API 응답시간 개선 (목표: 50% 향상)
- 시스템 가용성 (목표: 99.9%)
- 코드 커버리지 (목표: >80%)
- 버그 감소율 (목표: 70% 감소)

### Business Metrics
- 지원 가능한 데이터 소스 수 (목표: 5개 이상)
- API 호출 성공률 (목표: >99%)
- 개발 생산성 향상
- 유지보수 비용 절감

## Risk Management

### Technical Risks
- 외부 API 의존성
- 데이터 일관성 문제
- 성능 병목점
- 보안 취약점

### Mitigation Strategies
- 포괄적인 에러 처리
- 데이터 검증 강화
- 성능 모니터링 및 알림
- 보안 감사 및 테스트

## Current Integration Requirements

### Immediate Implementation
- docs/통합코드_지원사업_구분_코드.md 기반 사업구분코드 적용
- docs/business_category_codes.md 기반 사업카테고리 구현
- docs/content-category-codes.md 기반 컨텐츠 분류 구현
- docs/kstartup-api-spec.md 기반 API 명세 완성

### Quality Assurance
- 모든 API 엔드포인트 Swagger 문서화
- 단위 테스트 및 통합 테스트 작성
- 코드 품질 검증 (linting, type hints)
- API 응답 검증 및 에러 처리