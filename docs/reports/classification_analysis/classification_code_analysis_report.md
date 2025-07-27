# K-Startup API 분류 코드 실제 사용 현황 분석 리포트

분석 일시: 2025-07-27 07:30:30

## 📋 분석 개요

- 분석된 엔드포인트: 4개
- 분석 범위: 실제 API 응답 데이터의 분류 코드 vs 정의된 enum 클래스
- 목적: 분류 코드 정의와 실제 사용 현황 간의 차이점 및 개선 방안 도출

## 🔍 Announcements 엔드포인트 분석

### 📊 기본 정보

- 분석된 데이터 수: 3개
- 분류 필드: business_category, support_region, supervising_institution

### 🏷️ 실제 사용된 분류 코드

#### business_category
- `멘토링ㆍ컨설팅ㆍ교육` (1회 사용)
- `기술개발(R&amp;D)` (1회 사용)
- `창업교육` (1회 사용)

#### support_region
- `서울` (1회 사용)
- `전국` (1회 사용)
- `전북` (1회 사용)

#### supervising_institution
- `지자체` (1회 사용)
- `민간` (1회 사용)
- `공공기관` (1회 사용)

### 🔗 매핑 분석

#### business_category
- 매핑 상태: ❌ 미매핑
- 실제 사용 (한글): `멘토링ㆍ컨설팅ㆍ교육`, `기술개발(R&amp;D)`, `창업교육`
- 정의된 enum (영문): `cmrczn_tab1`, `cmrczn_tab2`, `cmrczn_tab3`, `cmrczn_tab4`, `cmrczn_tab5`, `cmrczn_tab6`, `cmrczn_tab7`, `cmrczn_tab8`, `cmrczn_tab9`
- 일치하는 설명: 창업교육
- 정의되지 않은 실제 카테고리: 멘토링ㆍ컨설팅ㆍ교육, 기술개발(R&amp;D)

#### 📝 매핑 추천

| 실제 사용 카테고리 | 추천 enum 코드 | enum 설명 | 신뢰도 |
|-------------------|---------------|-----------|---------|
| `멘토링ㆍ컨설팅ㆍ교육` | `cmrczn_tab4` | 멘토링,컨설팅 | 🟢 high |
| `기술개발(R&amp;D)` | `cmrczn_tab6` | 기술개발 R&D | 🟢 high |
| `창업교육` | `cmrczn_tab2` | 창업교육 | 🟢 high |

## 🔍 Business 엔드포인트 분석

### 📊 기본 정보

- 분석된 데이터 수: 3개
- 분류 필드: business_category

### 🏷️ 실제 사용된 분류 코드

#### business_category
- `cmrczn_Tab1` (3회 사용)

### 🔗 매핑 분석

#### business_category
- 매핑 상태: ❌ 미매핑
- 실제 사용 (한글): `cmrczn_Tab1`
- 정의된 enum (영문): `cmrczn_tab1`, `cmrczn_tab2`, `cmrczn_tab3`, `cmrczn_tab4`, `cmrczn_tab5`, `cmrczn_tab6`, `cmrczn_tab7`, `cmrczn_tab8`, `cmrczn_tab9`
- 정의되지 않은 실제 카테고리: cmrczn_Tab1

#### 📝 매핑 추천

| 실제 사용 카테고리 | 추천 enum 코드 | enum 설명 | 신뢰도 |
|-------------------|---------------|-----------|---------|
| `cmrczn_Tab1` | `미정의` | 매핑 불가 | 🔴 none |

## 🔍 Content 엔드포인트 분석

### 📊 기본 정보

- 분석된 데이터 수: 3개
- 분류 필드: content_type

### 🏷️ 실제 사용된 분류 코드

#### content_type
- `notice_matr` (1회 사용)
- `fnd_scs_case` (2회 사용)

### 🔗 매핑 분석

#### content_type
- 매핑 상태: ✅ 완전매핑
- 커버리지: 100.0%
- 매핑된 코드: notice_matr, fnd_scs_case
- 미사용 정의 코드: kstartup_isse_trd

## 🔍 Statistics 엔드포인트 분석

### 📊 기본 정보

- 분석된 데이터 수: 3개
- 분류 필드: 없음

### 🔗 매핑 분석

- 통계 정보 엔드포인트에는 분류 필드가 없습니다.
## 💡 종합 분석 결과

### ✅ 발견 사항

1. **콘텐츠 분류 코드**: ✅ 완전 매핑
   - API 응답과 enum 정의가 완전히 일치 (영문 코드 사용)
   - `fnd_scs_case`, `notice_matr` 코드가 실제로 사용됨

2. **사업 분류 코드**: ⚠️ 불일치 - 매핑 필요
   - API 응답: 한글 카테고리 사용 (`기술개발(R&D)`, `멘토링ㆍ컨설팅ㆍ교육` 등)
   - enum 정의: 영문 코드 사용 (`cmrczn_tab1` ~ `cmrczn_tab9`)
   - 의미적으로는 일치하지만 형태가 다름

### 🔧 권장 개선사항

#### 즉시 개선 필요
1. **사업 분류 코드 enum 수정**:
   - 현재: 영문 코드 정의 (`cmrczn_tab1` 등)
   - 변경: 실제 API 한글 응답 기반 enum 생성
   - 예시: `BusinessCategoryKorean` enum 클래스 추가

2. **역방향 매핑 함수 구현**:
   - 한글 카테고리 → 영문 코드 변환
   - 영문 코드 → 한글 설명 변환

#### 중장기 개선사항
1. **분류 코드 통합 관리**:
   - API 응답 형태와 내부 처리 형태 분리
   - 다국어 지원 고려한 분류 체계

2. **동적 분류 코드 감지**:
   - 신규 분류 코드 자동 감지
   - enum 정의와 실제 사용 차이 모니터링

## 📊 구체적 매핑 현황

### 사업 카테고리 매핑 테이블

| 실제 API 응답 (한글) | 현재 enum 코드 | 현재 enum 설명 | 상태 |
|---------------------|---------------|---------------|------|
| `기술개발(R&D)` | `cmrczn_tab6` | 기술개발 R&D | ✅ 매핑 가능 |
| `멘토링ㆍ컨설팅ㆍ교육` | `cmrczn_tab4` | 멘토링,컨설팅 | ⚠️ 부분 일치 |
| `창업교육` | `cmrczn_tab2` | 창업교육 | ✅ 완전 일치 |

### 콘텐츠 카테고리 매핑 테이블

| 실제 API 응답 | 현재 enum 코드 | 현재 enum 설명 | 상태 |
|--------------|---------------|---------------|------|
| `fnd_scs_case` | `fnd_scs_case` | 창업우수사례 | ✅ 완전 일치 |
| `notice_matr` | `notice_matr` | 정책 및 규제정보(공지사항) | ✅ 완전 일치 |

---

**결론**: 콘텐츠 분류는 완벽하게 정의되어 있으나, 사업 분류 코드는 API 응답 형태에 맞는 enum 재정의가 필요합니다.