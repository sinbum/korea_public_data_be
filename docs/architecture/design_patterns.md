# 🏗️ 디자인 패턴 및 아키텍처 설계

## 📋 개요

본 프로젝트는 SOLID 원칙을 기반으로 하여 확장 가능하고 유지보수하기 쉬운 아키텍처를 구축했습니다. 다양한 디자인 패턴을 적절히 조합하여 공공데이터 API 플랫폼의 복잡성을 관리하고 있습니다.

## 🎯 SOLID 원칙 적용

### 1. Single Responsibility Principle (SRP)
**각 클래스는 단일 책임만을 가집니다.**

```python
# 예시: 분리된 책임
class AnnouncementRepository:  # 데이터 접근만 담당
    def get_by_id(self, id: str) -> Announcement: ...

class AnnouncementService:     # 비즈니스 로직만 담당
    def process_announcement(self, data: dict) -> Announcement: ...

class AnnouncementRouter:      # HTTP 요청/응답만 담당
    def get_announcement(self, id: str) -> Response: ...
```

### 2. Open/Closed Principle (OCP)
**새로운 기능 추가 시 기존 코드 수정 없이 확장 가능합니다.**

```python
# 기존 코드 수정 없이 새로운 API 클라이언트 추가 가능
class BaseAPIClient(ABC):
    @abstractmethod
    def fetch_data(self) -> APIResponse: ...

class KStartupAPIClient(BaseAPIClient): ...     # 기존
class NewGovAPIClient(BaseAPIClient): ...       # 새로 추가
```

### 3. Liskov Substitution Principle (LSP)
**하위 클래스는 상위 클래스로 완전히 대체 가능합니다.**

```python
# 모든 Repository 구현체는 BaseRepository로 대체 가능
def process_data(repo: BaseRepository[T, CreateT, UpdateT]):
    # AnnouncementRepository, BusinessRepository 등 모두 사용 가능
    result = repo.get_all()
```

### 4. Interface Segregation Principle (ISP)
**클라이언트는 필요한 인터페이스만 의존합니다.**

```python
# 특정 기능만 필요한 클라이언트를 위한 작은 인터페이스
class Readable(Protocol):
    def read(self, id: str) -> T: ...

class Writable(Protocol):
    def create(self, data: CreateT) -> T: ...
```

### 5. Dependency Inversion Principle (DIP)
**구체적 구현보다 추상화에 의존합니다.**

```python
# 의존성 주입을 통한 느슨한 결합
class AnnouncementService:
    def __init__(self, 
                 repository: BaseRepository,    # 추상화에 의존
                 api_client: BaseAPIClient):    # 구체적 구현에 의존하지 않음
```

## 🎨 적용된 디자인 패턴

### 1. Strategy Pattern
**런타임에 알고리즘을 교체할 수 있습니다.**

```python
# 인증 전략
class AuthenticationStrategy(ABC):
    @abstractmethod
    def authenticate(self, request: Request) -> bool: ...

class APIKeyStrategy(AuthenticationStrategy): ...
class JWTStrategy(AuthenticationStrategy): ...
class OAuth2Strategy(AuthenticationStrategy): ...

# 요청 처리 전략
class RequestStrategy(ABC):
    @abstractmethod
    def process_request(self, params: dict) -> APIResponse: ...
```

**사용 예시:**
```python
# 설정에 따라 전략 선택
auth_strategy = get_auth_strategy(config.auth_type)
client = APIClient(auth_strategy=auth_strategy)
```

### 2. Template Method Pattern
**공통 처리 흐름을 표준화하면서 세부 구현은 하위 클래스에서 정의합니다.**

```python
class BaseAPIClient(ABC):
    def request(self, params: dict) -> APIResponse[T]:
        # 템플릿 메서드: 공통 흐름 정의
        self._validate_params(params)
        auth_header = self._authenticate()
        raw_response = self._make_request(params, auth_header)
        return self._transform_response(raw_response)
    
    @abstractmethod
    def _transform_response(self, raw: dict) -> APIResponse[T]:
        # 하위 클래스에서 구현
        pass
```

### 3. Factory Pattern
**객체 생성 로직을 캡슐화합니다.**

```python
class RepositoryFactory:
    @staticmethod
    def create_repository(domain: str) -> BaseRepository:
        factories = {
            "announcements": lambda: AnnouncementRepository(),
            "businesses": lambda: BusinessRepository(),
            "contents": lambda: ContentRepository(),
        }
        return factories[domain]()

# Abstract Factory Pattern
class ServiceFactory(ABC):
    @abstractmethod
    def create_repository(self) -> BaseRepository: ...
    @abstractmethod
    def create_api_client(self) -> BaseAPIClient: ...
    @abstractmethod
    def create_service(self) -> BaseService: ...
```

### 4. Repository Pattern
**데이터 접근 계층을 추상화합니다.**

```python
class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]: ...
    @abstractmethod
    def get_all(self, filters: QueryFilter = None) -> List[T]: ...
    @abstractmethod
    def create(self, data: CreateT) -> T: ...
    @abstractmethod
    def update_by_id(self, id: str, data: UpdateT) -> Optional[T]: ...
    @abstractmethod
    def delete_by_id(self, id: str) -> bool: ...
```

### 5. Plugin Pattern
**런타임에 기능을 확장할 수 있습니다.**

```python
class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
    
    def register(self, name: str, plugin: BasePlugin):
        self._plugins[name] = plugin
    
    def execute(self, name: str, *args, **kwargs):
        if name in self._plugins:
            return self._plugins[name].execute(*args, **kwargs)

# 플러그인 사용 예시
@plugin_registry.register("data_validator")
class DataValidationPlugin(BasePlugin):
    def execute(self, data: dict) -> ValidationResult: ...
```

### 6. Observer Pattern (Event-Driven)
**느슨하게 결합된 이벤트 시스템을 구축합니다.**

```python
class DomainEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent):
        for handler in self._handlers[event.event_type]:
            handler(event)
```

## 🏛️ 아키텍처 레이어

### 1. Presentation Layer (표현 계층)
```
FastAPI Routers
├── HTTP 요청/응답 처리
├── 입력 검증 (Pydantic)
├── 인증/인가
└── API 문서화 (OpenAPI)
```

### 2. Application Layer (응용 계층)
```
Services
├── 비즈니스 로직 조율
├── 트랜잭션 관리
├── 외부 API 통합
└── 이벤트 발행
```

### 3. Domain Layer (도메인 계층)
```
Domain Models & Business Rules
├── 핵심 비즈니스 로직
├── 도메인 이벤트
├── 값 객체 (Value Objects)
└── 도메인 서비스
```

### 4. Infrastructure Layer (인프라 계층)
```
Repositories & External Services
├── 데이터 접근 (MongoDB)
├── 외부 API 클라이언트
├── 메시징 (Celery/Redis)
└── 캐싱 (Redis)
```

## 🔧 의존성 주입 시스템

### Container 기반 DI
```python
class DIContainer:
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]):
        self._singletons[interface] = implementation
    
    def register_transient(self, interface: Type[T], implementation: Type[T]):
        self._services[interface] = implementation
    
    def resolve(self, interface: Type[T]) -> T:
        # 의존성 해결 로직
        ...
```

### FastAPI 통합
```python
def get_announcement_service() -> AnnouncementService:
    return container.resolve(AnnouncementService)

@router.get("/announcements/")
async def get_announcements(
    service: AnnouncementService = Depends(get_announcement_service)
):
    return await service.get_all()
```

## 📊 아키텍처 결정 기록 (ADR)

### ADR-001: Repository Pattern 도입
- **결정**: 모든 데이터 접근에 Repository Pattern 사용
- **이유**: 데이터 소스 변경 시 영향 최소화, 테스트 용이성
- **결과**: 코드 재사용성 증가, 유지보수성 향상

### ADR-002: Generic 타입 시스템 활용
- **결정**: TypeVar와 Generic을 적극 활용
- **이유**: 타입 안전성 확보, IDE 지원 향상
- **결과**: 런타임 오류 감소, 개발 생산성 향상

### ADR-003: Plugin 시스템 도입
- **결정**: 확장 가능한 Plugin 아키텍처 구축
- **이유**: 새로운 데이터 소스 추가 시 기존 코드 변경 최소화
- **결과**: 시스템 확장성 크게 향상

## 🎯 패턴 적용 효과

### 1. 확장성 (Scalability)
- 새로운 도메인 추가: 기존 코드 수정 없이 가능
- 새로운 데이터 소스 연동: Plugin으로 간단히 추가
- API 버전 관리: Strategy Pattern으로 호환성 유지

### 2. 유지보수성 (Maintainability)
- 단일 책임 원칙으로 코드 이해 용이
- 의존성 주입으로 테스트 작성 편리
- 계층 분리로 변경 영향 범위 제한

### 3. 테스트 가능성 (Testability)
- Mock 객체 활용 용이
- 단위 테스트와 통합 테스트 분리
- 의존성 격리로 독립적 테스트 가능

### 4. 성능 (Performance)
- Repository 패턴으로 쿼리 최적화
- Factory 패턴으로 객체 생성 최적화
- 캐싱 전략 적용 용이

## 🔍 코드 품질 메트릭

- **복잡도**: Cyclomatic complexity < 10
- **결합도**: 낮은 결합도 (Loose Coupling)
- **응집도**: 높은 응집도 (High Cohesion)
- **테스트 커버리지**: > 80%
- **타입 커버리지**: > 90%

이러한 아키텍처 설계를 통해 확장 가능하고 유지보수하기 쉬운 공공데이터 API 플랫폼을 구축했습니다.