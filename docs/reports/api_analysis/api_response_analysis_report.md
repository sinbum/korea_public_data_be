# K-Startup API 응답 데이터 분석 리포트

분석 일시: 2025-07-27 07:21:29

## 📊 개요

- 분석된 엔드포인트 수: 4
- 총 샘플 데이터: 12개

## 🔍 Announcements 엔드포인트 분석

### 메타데이터

- **current_count**: 5 (int)
- **match_count**: 25664 (int)
- **page**: 1 (int)
- **per_page**: 5 (int)
- **total_count**: 25664 (int)

### 데이터 구조

- 루트 키: current_count, match_count, page, per_page, total_count, data
- 데이터 배열 존재: ✅
- 페이지네이션 지원: ✅
- 아이템당 필드 수: 30개

### 주요 필드 분석

| 필드명 | 완성도 | 주요 타입 | 비고 |
|--------|--------|----------|------|
| announcement_id | 100.0% | str | ✅ 완전 |
| application_exclusion_content | 100.0% | str |  |
| application_target | 100.0% | str | ✅ 완전 |
| application_target_content | 100.0% | str | ✅ 완전 |
| business_application_url | 100.0% | null | ⚠️ 높은 NULL 비율 |
| business_category | 100.0% | str | ✅ 완전 |
| business_entry | 100.0% | str | ✅ 완전 |
| business_guidance_url | 100.0% | str | ✅ 완전 |
| business_target_age | 100.0% | str | ✅ 완전 |
| contact_department | 100.0% | str | ✅ 완전 |

### 데이터 품질

- 분석된 아이템 수: 3개
- 중복 ID: 0개
- 품질 이슈: 0개

#### 완성도 낮은 필드 (50% 미만)

- **business_application_url**: 0.0%
- **online_reception**: 33.3%
- **visit_reception**: 0.0%
- **fax_reception**: 0.0%
- **postal_reception**: 0.0%

## 🔍 Business 엔드포인트 분석

### 메타데이터

- **current_count**: 5 (int)
- **match_count**: 1231 (int)
- **page**: 1 (int)
- **per_page**: 5 (int)
- **total_count**: 1231 (int)

### 데이터 구조

- 루트 키: current_count, match_count, page, per_page, total_count, data
- 데이터 배열 존재: ✅
- 페이지네이션 지원: ✅
- 아이템당 필드 수: 11개

### 주요 필드 분석

| 필드명 | 완성도 | 주요 타입 | 비고 |
|--------|--------|----------|------|
| business_category | 100.0% | str | ✅ 완전 |
| business_feature | 100.0% | str | ✅ 완전 |
| business_intro | 100.0% | str | ✅ 완전 |
| business_name | 100.0% | str | ✅ 완전 |
| business_year | 100.0% | str | ✅ 완전 |
| detail_page_url | 100.0% | null | ⚠️ 높은 NULL 비율 |
| detl_pg_url | 100.0% | str | ✅ 완전 |
| id | 100.0% | str | ✅ 완전 |
| support_budget | 100.0% | str | ✅ 완전 |
| support_content | 100.0% | str | ✅ 완전 |

### 데이터 품질

- 분석된 아이템 수: 3개
- 중복 ID: 0개
- 품질 이슈: 0개

#### 완성도 낮은 필드 (50% 미만)

- **detail_page_url**: 0.0%

## 🔍 Content 엔드포인트 분석

### 메타데이터

- **current_count**: 5 (int)
- **match_count**: 1083 (int)
- **page**: 1 (int)
- **per_page**: 5 (int)
- **total_count**: 1083 (int)

### 데이터 구조

- 루트 키: current_count, match_count, page, per_page, total_count, data
- 데이터 배열 존재: ✅
- 페이지네이션 지원: ✅
- 아이템당 필드 수: 7개

### 주요 필드 분석

| 필드명 | 완성도 | 주요 타입 | 비고 |
|--------|--------|----------|------|
| content_type | 100.0% | str | ✅ 완전 |
| detail_page_url | 100.0% | str | ✅ 완전 |
| file_name | 100.0% | str | ✅ 완전 |
| id | 100.0% | null | ⚠️ 높은 NULL 비율 |
| register_date | 100.0% | str | ✅ 완전 |
| title | 100.0% | str | ✅ 완전 |
| view_count | 100.0% | int | ✅ 완전 |

### 데이터 품질

- 분석된 아이템 수: 3개
- 중복 ID: 0개
- 품질 이슈: 0개

#### 완성도 낮은 필드 (50% 미만)

- **id**: 0.0%

## 🔍 Statistics 엔드포인트 분석

### 메타데이터

- **current_count**: 5 (int)
- **match_count**: 25 (int)
- **page**: 1 (int)
- **per_page**: 5 (int)
- **total_count**: 25 (int)

### 데이터 구조

- 루트 키: current_count, match_count, page, per_page, total_count, data
- 데이터 배열 존재: ✅
- 페이지네이션 지원: ✅
- 아이템당 필드 수: 7개

### 주요 필드 분석

| 필드명 | 완성도 | 주요 타입 | 비고 |
|--------|--------|----------|------|
| content | 100.0% | str | ✅ 완전 |
| detail_page_url | 100.0% | str | ✅ 완전 |
| file_name | 100.0% | str | ✅ 완전 |
| id | 100.0% | null | ⚠️ 높은 NULL 비율 |
| modify_date | 100.0% | str | ✅ 완전 |
| register_date | 100.0% | str | ✅ 완전 |
| title | 100.0% | str | ✅ 완전 |

### 데이터 품질

- 분석된 아이템 수: 3개
- 중복 ID: 0개
- 품질 이슈: 0개

#### 완성도 낮은 필드 (50% 미만)

- **id**: 0.0%

## 🔄 엔드포인트 간 교차 분석

### 공통 필드 (2개)

- `detail_page_url`
- `id`

### 구조 일관성

| 엔드포인트 | 페이지네이션 | 데이터 배열 | 필드 수 |
|------------|--------------|-------------|---------|
| announcements | ✅ | ✅ | 30 |
| business | ✅ | ✅ | 11 |
| content | ✅ | ✅ | 7 |
| statistics | ✅ | ✅ | 7 |

## 💡 권장사항

### 데이터 품질 개선
- NULL 값이 많은 필드에 대한 데이터 보완 검토
- 중복 데이터 정리 프로세스 구축
- 필수 필드 검증 로직 강화

### API 일관성 향상
- 모든 엔드포인트에서 동일한 페이지네이션 구조 사용
- 공통 메타데이터 필드 표준화
- 응답 형식 통일화

### 모니터링 및 검증
- 정기적인 데이터 품질 검증
- API 응답 구조 변경 감지 시스템
- 실시간 데이터 완성도 모니터링