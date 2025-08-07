# CLAUDE.local.md - 학습 내용 및 중요 결정사항

이 문서는 Claude와의 협업 과정에서 학습한 내용과 중요한 아키텍처 결정사항을 기록합니다.

## 🏗️ 아키텍처 설계 결정사항

### 1. SOLID 원칙 적용
**결정**: 전체 아키텍처에 SOLID 원칙을 엄격히 적용
**이유**: 확장성과 유지보수성을 위해 필수
**구현**:
- **S**RP: 각 클래스는 단일 책임 (BaseAPIClient, BaseRepository, BaseService 분리)
- **O**CP: 새로운 API 소스 추가 시 기존 코드 수정 없이 확장 (Plugin System)
- **L**SP: 모든 구현체는 기본 인터페이스로 교체 가능
- **I**SP: 클라이언트별 필요한 인터페이스만 의존
- **D**IP: 구체적 구현보다 추상화에 의존 (Factory Pattern)

### 2. 디자인 패턴 조합
**선택한 패턴들과 이유**:

```
Strategy Pattern + Template Method Pattern
├── Strategy: 런타임 알고리즘 교체 (인증, 요청 처리)
└── Template: 공통 처리 흐름 표준화 (API 호출 파이프라인)

Factory Pattern + Abstract Factory Pattern  
├── Factory: 단일 객체 생성
└── Abstract Factory: 관련 객체군 생성 (완전한 서비스 스택)

Repository Pattern + Unit of Work Pattern
├── Repository: 데이터 접근 추상화
└── Unit of Work: 트랜잭션 관리 (향후 구현)

Plugin Pattern + Registry Pattern
├── Plugin: 동적 기능 확장
└── Registry: 플러그인 생명주기 관리
```

### 3. 제네릭 타입 시스템
**결정**: TypeVar와 Generic을 적극 활용
**장점**: 컴파일 타임 타입 안전성 + IDE 지원
**구현 예시**:
```python
T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)

class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    # 타입 안전한 CRUD 작업
```

## 🔧 기술적 학습 사항

### 1. MongoDB ObjectId 처리 패턴
**문제**: Pydantic과 MongoDB _id 필드 불일치
**해결책**: 서비스 계층에서 일관된 변환
```python
def _convert_objectid_to_string(self, doc: Dict[str, Any]) -> Dict[str, Any]:
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc
```

### 2. 비동기 vs 동기 전략
**현재 결정**: 혼합 사용
- **동기**: pymongo (데이터베이스), 단순 비즈니스 로직
- **비동기**: httpx (외부 API), I/O 집약적 작업
**향후**: 필요 시 Motor로 완전 비동기 전환

### 3. 에러 처리 계층화
```
Application Level (FastAPI)
├── HTTP 상태 코드 매핑
├── 사용자 친화적 메시지
└── 로깅 및 모니터링

Service Level
├── 비즈니스 로직 검증
├── 도메인 예외 처리  
└── 트랜잭션 롤백

Repository Level
├── 데이터 접근 오류
├── 제약 조건 위반
└── 연결 오류

External API Level
├── 네트워크 오류
├── 인증 실패
└── Rate Limiting
```

## 🎯 아키텍처 핵심 원칙

### 1. 확장성 우선 설계
- 새로운 공공데이터 API 추가가 주요 요구사항
- Plugin System으로 런타임 확장 지원
- Factory Pattern으로 객체 생성 추상화

### 2. 계층 분리 원칙
```
Presentation Layer (FastAPI Routers)
├── HTTP 요청/응답 처리
├── 입력 검증
└── 인증/인가

Business Layer (Services)  
├── 비즈니스 로직
├── 데이터 변환
└── 외부 API 통합

Data Access Layer (Repositories)
├── 데이터 저장/조회
├── 쿼리 최적화
└── 트랜잭션 관리

Infrastructure Layer (Clients, Config)
├── 외부 시스템 연동
├── 설정 관리
└── 유틸리티 기능
```

### 3. 의존성 역전 실현
- 인터페이스에 의존, 구현에 의존하지 않음
- 테스트 가능성 극대화
- 모듈 간 결합도 최소화

## 📚 구현한 핵심 컴포넌트

### 1. BaseAPIClient - Template Method Pattern
```python
def request() -> APIResponse[T]:
    # 1. 입력 검증
    # 2. 전처리 (Strategy 적용)
    # 3. 인증 (Strategy 적용)  
    # 4. HTTP 호출 (재시도 로직)
    # 5. 후처리 (Hook Method)
    # 6. 변환 (추상 메서드)
```

### 2. BaseRepository - Repository Pattern
```python
class BaseRepository(Generic[T, CreateT, UpdateT]):
    # CRUD 기본 작업
    # 쿼리 빌더 (QueryFilter, SortOption)
    # 페이지네이션 지원
    # 배치 작업 지원
```

### 3. BaseService - Service Layer Pattern
```python  
class BaseService(Generic[T, CreateT, UpdateT, ResponseT]):
    # 비즈니스 로직 캡슐화
    # 데이터 변환 (도메인 ↔ DTO)
    # 외부 API 통합
    # Hook 메서드 (before/after)
```

### 4. Plugin Registry - Plugin Pattern
```python
class PluginRegistry:
    # 동적 플러그인 등록/해제
    # 의존성 관리
    # 생명주기 관리
    # 네임스페이스 격리
```

## 🚀 다음 구현 우선순위

### 단기 (1-2주)
1. **K-Startup API 클라이언트 리팩토링**
   - BaseAPIClient 상속 구조로 변경
   - 비동기 HTTP 클라이언트 적용
   - 강화된 에러 처리 및 재시도

### 중기 (1개월)
2. **Repository 패턴 전면 적용**
   - 모든 도메인에 BaseRepository 적용
   - 쿼리 최적화 및 인덱스 설계
   - 트랜잭션 관리 구현

3. **나머지 도메인 완성**
   - contents, statistics, businesses 도메인
   - 도메인별 특화 로직 구현
   - 통합 테스트 작성

### 장기 (2-3개월)
4. **고급 기능 구현**
   - 통합 검색 (Elasticsearch 연동)
   - 실시간 알림 (WebSocket)
   - 성능 모니터링 (Prometheus + Grafana)

## 💡 핵심 학습 포인트

### 1. 추상화의 적절한 수준
- 너무 추상적: 복잡성 증가, 이해하기 어려움
- 너무 구체적: 확장성 저해, 중복 코드 발생
- **균형점**: 현재 요구사항 + 예상 가능한 확장 고려

### 2. 타입 시스템 활용
- Python의 타입 힌트를 적극 활용
- 제네릭으로 재사용성 극대화
- mypy 등 정적 분석 도구 활용 필수

### 3. 테스트 가능한 설계
- 의존성 주입으로 Mock 가능한 구조
- 단위 테스트와 통합 테스트 분리
- 테스트 더블(Mock, Stub, Fake) 적절히 활용

## 🔍 모니터링 및 메트릭

### 개발 진행 상황
- [x] Task 1: 공통 인터페이스 및 추상화 계층 설계 (완료)
- [ ] Task 2: K-Startup API 클라이언트 리팩토링 (다음)
- [ ] Task 3: Repository 패턴 적용
- [ ] Task 4: 의존성 주입 시스템 구축
- [ ] Task 5: 데이터 소스 관리 시스템

### 코드 품질 메트릭 (목표)
- 테스트 커버리지: >80%
- 타입 커버리지: >90%
- 복잡도: Cyclomatic complexity < 10
- 중복도: DRY 원칙 준수

## 🤖 작업 모니터링 가이드

### 작업 완료 후 확인 사항
- 작업이 끝나면, task-master 의 서브태스크와, 각 태스크를 확인한다.

---

*이 문서는 프로젝트 진행에 따라 지속적으로 업데이트됩니다.*
*새로운 아키텍처 결정이나 학습 사항이 있을 때마다 기록해주세요.*