# K-Startup API 필드 매핑 검증 리포트

검증 일시: 2025-07-27 07:23:43

## 📋 검증 개요

- 검증된 엔드포인트: 4개
- 검증 범위: API 응답 ↔ API 모델 ↔ 도메인 모델

### 📊 전체 통계

- 평균 필드 커버리지: 97.7%
- 검증 상태: ✅ 양호

## 🔍 Announcements 엔드포인트 검증

### 📈 필드 커버리지

- 전체 실제 필드: 30개
- 모델에서 지원: 30개
- 커버리지: 100.0%

#### ⚠️ 실제 데이터에 없는 필드

- `aply_excl_trgt_ctnt`
- `aply_mthd_eml_rcpt_istc`
- `aply_mthd_etc_istc`
- `aply_mthd_fax_rcpt_istc`
- `aply_mthd_onli_rcpt_istc`
- `aply_mthd_pssr_rcpt_istc`
- `aply_mthd_vst_rcpt_istc`
- `aply_trgt`
- `aply_trgt_ctnt`
- `biz_aply_url`
- `biz_enyy`
- `biz_gdnc_url`
- `biz_pbanc_nm`
- `biz_prch_dprt_nm`
- `biz_trgt_age`
- `detl_pg_url`
- `intg_pbanc_biz_nm`
- `intg_pbanc_yn`
- `pbanc_ctnt`
- `pbanc_ntrp_nm`
- `pbanc_rcpt_bgng_dt`
- `pbanc_rcpt_end_dt`
- `pbanc_sn`
- `prch_cnpl_no`
- `prfn_matr`
- `rcrt_prgs_yn`
- `sprv_inst`
- `supt_biz_clsfc`
- `supt_regin`

### 🧪 모델 인스턴스 생성 테스트

#### API 모델 (AnnouncementItem)
- 성공: 3건
- 실패: 0건

#### 도메인 모델 (Announcement)
- 성공: 0건
- 실패: 3건
- 오류:
  - Item 0: 2 validation errors for Announcement
announcement_data
  Field required [type=missing, input_value={'id': '174329', 'title':...hM=view&pbancSn=174329'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
created_at
  Input should be a valid datetime, invalid datetime separator, expected `T`, `t`, `_` or space [type=datetime_parsing, input_value='2025-07-14', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/datetime_parsing
  - Item 1: 2 validation errors for Announcement
announcement_data
  Field required [type=missing, input_value={'id': '174326', 'title':...hM=view&pbancSn=174326'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
created_at
  Input should be a valid datetime, invalid datetime separator, expected `T`, `t`, `_` or space [type=datetime_parsing, input_value='2025-07-23', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/datetime_parsing
  - Item 2: 2 validation errors for Announcement
announcement_data
  Field required [type=missing, input_value={'id': '174325', 'title':...hM=view&pbancSn=174325'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
created_at
  Input should be a valid datetime, invalid datetime separator, expected `T`, `t`, `_` or space [type=datetime_parsing, input_value='2025-07-23', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/datetime_parsing

### 🔗 필드 별칭 매핑

| 모델 필드 | API 필드 (alias) |
|-----------|------------------|
| announcement_id | pbanc_sn |
| title | biz_pbanc_nm |
| content | pbanc_ctnt |
| start_date | pbanc_rcpt_bgng_dt |
| end_date | pbanc_rcpt_end_dt |
| business_category | supt_biz_clsfc |
| integrated_business_name | intg_pbanc_biz_nm |
| application_target | aply_trgt |
| application_target_content | aply_trgt_ctnt |
| application_exclusion_content | aply_excl_trgt_ctnt |
| business_entry | biz_enyy |
| business_target_age | biz_trgt_age |
| support_region | supt_regin |
| organization | pbanc_ntrp_nm |
| supervising_institution | sprv_inst |
| contact_department | biz_prch_dprt_nm |
| contact_number | prch_cnpl_no |
| detail_page_url | detl_pg_url |
| business_guidance_url | biz_gdnc_url |
| business_application_url | biz_aply_url |
| online_reception | aply_mthd_onli_rcpt_istc |
| visit_reception | aply_mthd_vst_rcpt_istc |
| email_reception | aply_mthd_eml_rcpt_istc |
| fax_reception | aply_mthd_fax_rcpt_istc |
| postal_reception | aply_mthd_pssr_rcpt_istc |
| other_reception | aply_mthd_etc_istc |
| integrated_announcement | intg_pbanc_yn |
| recruitment_progress | rcrt_prgs_yn |
| performance_material | prfn_matr |
| id | id |

## 🔍 Business 엔드포인트 검증

### 📈 필드 커버리지

- 전체 실제 필드: 11개
- 모델에서 지원: 10개
- 커버리지: 90.9%

#### ❌ 모델에 누락된 필드

- `detl_pg_url`

#### ⚠️ 실제 데이터에 없는 필드

- `Detl_pg_url`
- `biz_category_cd`
- `biz_supt_bdgt_info`
- `biz_supt_ctnt`
- `biz_supt_trgt_info`
- `biz_yr`
- `supt_biz_chrct`
- `supt_biz_intrd_info`
- `supt_biz_titl_nm`

### 🧪 모델 인스턴스 생성 테스트

#### API 모델 (BusinessItem)
- 성공: 3건
- 실패: 0건

#### 도메인 모델 (Business)
- 성공: 0건
- 실패: 3건
- 오류:
  - Item 0: 2 validation errors for Business
id
  Value error, Invalid objectid [type=value_error, input_value='1', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
business_data
  Field required [type=missing, input_value={'id': '1', 'title': '바... 27, 7, 23, 43, 967726)}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 1: 2 validation errors for Business
id
  Value error, Invalid objectid [type=value_error, input_value='2', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
business_data
  Field required [type=missing, input_value={'id': '2', 'title': '글... 27, 7, 23, 43, 967849)}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 2: 2 validation errors for Business
id
  Value error, Invalid objectid [type=value_error, input_value='3', input_type=str]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
business_data
  Field required [type=missing, input_value={'id': '3', 'title': 'K-G... 27, 7, 23, 43, 967946)}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing

### 🔗 필드 별칭 매핑

| 모델 필드 | API 필드 (alias) |
|-----------|------------------|
| business_category | biz_category_cd |
| business_name | supt_biz_titl_nm |
| support_target | biz_supt_trgt_info |
| support_budget | biz_supt_bdgt_info |
| support_content | biz_supt_ctnt |
| business_feature | supt_biz_chrct |
| business_intro | supt_biz_intrd_info |
| business_year | biz_yr |
| detail_page_url | Detl_pg_url |
| id | id |

## 🔍 Content 엔드포인트 검증

### 📈 필드 커버리지

- 전체 실제 필드: 7개
- 모델에서 지원: 7개
- 커버리지: 100.0%

#### ⚠️ 실제 데이터에 없는 필드

- `clss_cd`
- `detl_pg_url`
- `file_nm`
- `fstm_reg_dt`
- `titl_nm`
- `view_cnt`

### 🧪 모델 인스턴스 생성 테스트

#### API 모델 (ContentItem)
- 성공: 3건
- 실패: 0건

#### 도메인 모델 (Content)
- 성공: 0건
- 실패: 3건
- 오류:
  - Item 0: 2 validation errors for Content
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
content_data
  Field required [type=missing, input_value={'title': '내 손안에 ...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 1: 2 validation errors for Content
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
content_data
  Field required [type=missing, input_value={'title': '청년,창업...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 2: 2 validation errors for Content
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
content_data
  Field required [type=missing, input_value={'title': '「BI 경쟁...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing

### 🔗 필드 별칭 매핑

| 모델 필드 | API 필드 (alias) |
|-----------|------------------|
| content_type | clss_cd |
| title | titl_nm |
| register_date | fstm_reg_dt |
| view_count | view_cnt |
| detail_page_url | detl_pg_url |
| file_name | file_nm |
| id | id |

## 🔍 Statistics 엔드포인트 검증

### 📈 필드 커버리지

- 전체 실제 필드: 7개
- 모델에서 지원: 7개
- 커버리지: 100.0%

#### ⚠️ 실제 데이터에 없는 필드

- `ctnt`
- `detl_pg_url`
- `file_nm`
- `fstm_reg_dt`
- `last_mdfcn_dt`
- `titl_nm`

### 🧪 모델 인스턴스 생성 테스트

#### API 모델 (StatisticalItem)
- 성공: 3건
- 실패: 0건

#### 도메인 모델 (Statistics)
- 성공: 0건
- 실패: 3건
- 오류:
  - Item 0: 2 validation errors for Statistics
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
statistical_data
  Field required [type=missing, input_value={'title': '중소기업...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 1: 2 validation errors for Statistics
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
statistical_data
  Field required [type=missing, input_value={'title': '중소기업...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing
  - Item 2: 2 validation errors for Statistics
id
  Value error, Invalid objectid [type=value_error, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/value_error
statistical_data
  Field required [type=missing, input_value={'title': '중소기업...&schM=view', 'id': None}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.5/v/missing

### 🔗 필드 별칭 매핑

| 모델 필드 | API 필드 (alias) |
|-----------|------------------|
| title | titl_nm |
| content | ctnt |
| register_date | fstm_reg_dt |
| modify_date | last_mdfcn_dt |
| detail_page_url | detl_pg_url |
| file_name | file_nm |
| id | id |

## 💡 권장사항

### 즉시 개선 필요
- ✅ 모든 엔드포인트의 필드 커버리지가 양호합니다

### 장기 개선사항
- API 응답 구조 변경 감지 자동화
- 필드 매핑 테스트 자동화
- 도메인 모델과 API 모델 간 변환 로직 개선
- 실시간 스키마 검증 시스템 구축