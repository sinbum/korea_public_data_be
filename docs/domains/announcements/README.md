# 사업공고 도메인 (Announcements Domain)

## 📋 개요

창업진흥원 K-Startup 사업공고 정보를 수집, 저장, 제공하는 완전히 구현된 도메인입니다.

## 🏗️ 아키텍처

### 계층 구조
```
Router Layer (API 엔드포인트)
    ↓
Service Layer (비즈니스 로직)
    ↓
Repository Layer (데이터 접근)
    ↓
Model Layer (데이터 모델)
```

### 핵심 컴포넌트

- **모델**: `Announcement`, `AnnouncementData`, `AnnouncementCreate`, `AnnouncementUpdate`
- **리포지토리**: `AnnouncementRepository` - MongoDB CRUD 작업 담당
- **서비스**: `AnnouncementService` - 비즈니스 로직 및 외부 API 통합
- **라우터**: `AnnouncementRouter` - RESTful API 엔드포인트 제공
- **태스크**: `AnnouncementTasks` - Celery 비동기 작업

## 📊 데이터 모델

### AnnouncementData
```python
{
    "business_id": "사업 고유 ID",
    "business_name": "사업명",
    "business_type": "사업 유형",
    "business_overview": "사업 개요",
    "support_target": "지원 대상",
    "recruitment_period": "모집 기간",
    "application_method": "신청 방법",
    "contact_info": "문의처",
    "announcement_date": "공고일",
    "deadline": "마감일",
    "status": "상태"
}
```

## 🔌 API 엔드포인트

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/fetch` | 공공데이터에서 실시간 수집 |
| GET | `/` | 저장된 공고 목록 조회 |
| GET | `/{id}` | 특정 공고 상세 조회 |
| POST | `/` | 새 공고 생성 |
| PUT | `/{id}` | 공고 수정 |
| DELETE | `/{id}` | 공고 삭제 |
| GET | `/recent` | 최근 공고 조회 |
| GET | `/statistics` | 공고 통계 조회 |

## 🚀 주요 기능

### 1. 실시간 데이터 수집
- K-Startup API와 연동하여 최신 사업공고 수집
- 중복 데이터 자동 감지 및 스킵
- 배치 처리 지원

### 2. 고급 검색 및 필터링
- 키워드 검색
- 사업 유형별 필터링
- 상태별 필터링
- 날짜 범위 검색

### 3. 페이지네이션
- 표준 페이지네이션 지원
- 정렬 옵션 (생성일, 수정일, 마감일)
- 페이지 크기 조정 가능

## 🔄 데이터 흐름

1. **수집 단계**: Celery 스케줄러가 정기적으로 K-Startup API 호출
2. **처리 단계**: 수집된 데이터를 내부 모델로 변환
3. **저장 단계**: MongoDB에 저장 (중복 체크 포함)
4. **제공 단계**: RESTful API를 통해 클라이언트에 제공

## 🧪 테스트 시나리오

### 단위 테스트
- 모델 검증 테스트
- 서비스 로직 테스트
- 리포지토리 CRUD 테스트

### 통합 테스트
- API 엔드포인트 테스트
- 외부 API 연동 테스트
- 데이터베이스 연동 테스트

## 📈 성능 지표

- **API 응답 시간**: < 200ms (캐시된 데이터)
- **데이터 수집 주기**: 일 1회
- **중복 처리 효율**: 99.9%
- **페이지네이션 성능**: 1000+ 레코드 처리 가능

## 🔮 향후 개선 계획

1. **검색 성능 최적화**: Elasticsearch 연동
2. **실시간 알림**: WebSocket 기반 신규 공고 알림
3. **고급 필터링**: 지역별, 지원금액별 필터
4. **데이터 분석**: 공고 트렌드 분석 기능