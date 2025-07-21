# 창업진흥원 K-Startup API 제공 명세서

**중요한 정보**
- 데이터 명 : 창업진흥원_K-Startup(사업소개,사업공고,콘텐츠 등)_조회서비스
- service-key : 프로젝트 최상단 .env 파일에 존재.
- 요청시 예제 : https://apis.data.go.kr/B552735/kisedKstartupService01/getStatisticalInformation01?serviceKey={PUBLIC_DATA_API_KEY or PUBLIC_DATA_API_KEY_DECODE}
- API 환경 또는 API 호출 조건에 따라 인증키가 적용되는 방식이 다를 수 있습니다. 포털에서 제공되는 Encoding/Decoding 된 인증키를 적용하면서 구동되는 키를 사용하시기 바랍니다. (로직에 PUBLIC_DATA_API_KEY 가 동작하지 않는 경우 PUBLIC_DATA_API_KEY_DECODE 로 조회 필요)
- 지원 포멧 : json, xml
## 1. API 서비스 개요

### 기본 정보
- **API 명 (영문)**: kisedKstartupService01
- **API 명 (국문)**: 창업진흥원_K-Startup(사업소개,사업공고, 콘텐츠 등)_조회서비스
- **서비스 설명**: 중소벤처기업부 및 창업진흥원이 운영하는 창업지원포털(K-Startup)의 사업공고, 사업정보, 콘텐츠정보 등을 활용할 수 있는 OPEN API 서비스
- **서비스 시작일**: 2023-12-15
- **데이터 갱신주기**: 일 1회
- **서비스 제공자**: 윤강준 / 디지털정보실 / 044-410-1658 / ykj8797@kised.or.kr

### 기술 사양
- **인증 방식**: ServiceKey (공공데이터포털에서 발급)
- **프로토콜**: REST (GET 방식만 지원)
- **응답 형식**: JSON (기본값), XML
- **메시지 교환유형**: Request-Response
- **최대 메시지 크기**: 4000 bytes
- **평균 응답 시간**: 500 ms
- **초당 최대 트랜잭션**: 30 tps

### API 엔드포인트
- **기본 URL**: https://apis.data.go.kr/B552735/kisedKstartupService01
- **WADL URL**: https://apis.data.go.kr/B552735/kisedKstartupService01?_wadl&type=xml

## 2. API 상세 기능 목록

### 2.1 통합공고 지원사업 정보 (getBusinessInformation)

#### 개요
- **기능**: 창업지원사업 예산, 규모, 수행기관, 사업절차, 문의처 등 사업 소개 정보 조회
- **엔드포인트**: /getBusinessInformation01
- **전체 URL**: https://apis.data.go.kr/B552735/kisedKstartupService01/getBusinessInformation01

#### 요청 파라미터
| 파라미터명 | 타입 | 필수여부 | 설명 | 예시 |
|-----------|------|----------|------|------|
| ServiceKey | String(100) | 필수 | 공공데이터포털 인증키 (URL Encode 필요) | - |
| page | Number(100) | 선택 | 페이지 번호 | 1 |
| perPage | Number(100) | 선택 | 한 페이지 결과 수 | 10 |
| returnType | String(50) | 선택 | 반환 타입 | json 또는 XML |
| biz_category_cd | String(50) | 선택 | 사업 구분 코드 | cmrczn_Tab3 |
| supt_biz_titl_nm | String(300) | 선택 | 사업명 | 1인 창조기업 활성화 지원사업 |
| biz_supt_trgt_info | String | 선택 | 지원 대상 | - |
| biz_supt_bdgt_info | String | 선택 | 지원예산 및 규모 | - |
| biz_supt_ctnt | String | 선택 | 지원 내용 | - |
| supt_biz_chrct | String | 선택 | 지원 특징 | - |
| supt_biz_intrd_info | String | 선택 | 사업 소개 정보 | - |
| biz_yr | String(4) | 선택 | 사업 연도 | 2023 |

#### 응답 데이터
| 필드명 | 타입 | 필수여부 | 설명 | 예시 |
|--------|------|----------|------|------|
| biz_category_cd | String(50) | 필수 | 사업 구분 코드 | cmrczn_Tab3 |
| supt_biz_titl_nm | String(300) | 필수 | 사업명 | 1인 창조기업 활성화 지원사업 |
| biz_supt_trgt_info | String | 필수 | 지원 대상 | 「1인 창조기업 육성에 관한 법률」제2조의 (예지) 1인 창조기업 |
| biz_supt_bdgt_info | String | 필수 | 지원예산 및 규모 | (예산현황) 51.1억원, (지원규모) (1인 창조기업 지원센터) 전국 총 47개, (사업화) 160개 내외 |
| biz_supt_ctnt | String | 필수 | 지원 내용 | (지원센터) 입주공간, 전문가 자문, 교육, 멘토링, 네트워킹 등, (사업화) 마케팅 판로·투자 지원 등 |
| supt_biz_chrct | String | 필수 | 지원 특징 | 창의성과 전문성을 갖춘 1인 창조기업의 창업과 성장기반을 조성 |
| supt_biz_intrd_info | String | 필수 | 사업 소개 정보 | 1인 창조기업 창업을 촉진하고 성장기반을 조성하기 위해 사업공간, 마케팅, 판로개척, 투자유치 등을 지원 |
| biz_yr | String(4) | 필수 | 사업 연도 | 2023 |
| Detl_pg_url | String(2000) | 필수 | 상세페이지 URL | https://www.k-startup.go.kr/web/contents/bizpbancdeadline.do?schM=view&pbancSn=166834 |

### 2.2 지원사업 공고 정보 (getAnnouncementInformation)

#### 개요
- **기능**: 창업지원사업 공고명, 공고기간, 지원대상, 지원내용, 지원방법 등 공고 정보 조회
- **엔드포인트**: /getAnnouncementInformation01
- **전체 URL**: https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01

#### 요청 파라미터
| 파라미터명 | 타입 | 필수여부 | 설명 | 예시 |
|-----------|------|----------|------|------|
| ServiceKey | String(100) | 필수 | 공공데이터포털 인증키 (URL Encode 필요) | - |
| page | Number(100) | 선택 | 페이지 번호 | 1 |
| perPage | Number(100) | 선택 | 한 페이지 결과 수 | 10 |
| returnType | String(50) | 선택 | 반환 타입 | json 또는 XML |
| intg_pbanc_yn | String(300) | 선택 | 통합 공고 여부 | N |
| intg_pbanc_biz_nm | String | 선택 | 통합 공고 사업명 | - |
| biz_pbanc_nm | String(50) | 선택 | 지원 사업 공고명 | 창업보육센터 입주기업 수출상담회 |
| supt_biz_clsfc | String | 선택 | 지원 분야 | 행사·네트워크 |
| aply_trgt_ctnt | String(200) | 선택 | 신청 대상 내용 | - |
| supt_regin | String | 선택 | 지역명 | 서울특별시 |
| pbanc_rcpt_bgng_dt | String | 선택 | 공고 접수 시작일시 | 20121129 |
| pbanc_rcpt_end_dt | String | 선택 | 공고 접수 종료일시 | 20121221 |
| aply_trgt | String(200) | 선택 | 신청 대상 | 청소년,대학생,일반인 |
| biz_enyy | String(200) | 선택 | 창업 기간 | 7년미만,5년미만,3년미만,2년미만,1년미만,예비창업자 |
| biz_trgt_age | String(200) | 선택 | 대상 연령 | 만 20세 미만, 만 20세 이상 ~ 만 39세 이하, 만 40세 이상 |
| prfn_matr | String(200) | 선택 | 우대 사항 | - |
| Rcrt_prgs_yn | String(1) | 선택 | 모집진행여부 | Y |

#### 응답 데이터 (주요 필드)
| 필드명 | 타입 | 필수여부 | 설명 | 예시 |
|--------|------|----------|------|------|
| intg_pbanc_yn | String(1) | 필수 | 통합 공고 여부 | N |
| intg_pbanc_biz_nm | String(300) | 필수 | 통합 공고 사업명 | - |
| biz_pbanc_nm | String(300) | 필수 | 지원 사업 공고명 | 창업보육센터 입주기업 수출상담회 |
| pbanc_ctnt | String | 필수 | 공고 내용 | - |
| supt_biz_clsfc | String(50) | 필수 | 지원 분야 | 행사·네트워크 |
| aply_trgt_ctnt | String | 필수 | 신청 대상 내용 | - |
| supt_regin | String(200) | 필수 | 지역명 | 서울특별시 |
| pbanc_rcpt_bgng_dt | String | 필수 | 공고 접수 시작일시 | 2012-11-29 00:00:00 |
| pbanc_rcpt_end_dt | String | 필수 | 공고 접수 종료일시 | 2012-12-01 00:00:00 |
| pbanc_ntrp_nm | String(300) | 필수 | 창업 지원 기관명 | - |
| sprv_inst | String(25) | 필수 | 주관 기관 | 공공기관 |
| biz_prch_dprt_nm | String(200) | 필수 | 사업 담당자 부서명 | - |
| biz_gdnc_url | String(2000) | 필수 | 사업 안내 URL | - |
| prch_cnpl_no | String(200) | 필수 | 담당자 연락처 | - |
| detl_pg_url | String(500) | 필수 | 상세페이지 URL | www.k-startup.go.kr/web/contents/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=14212 |
| aply_mthd_vst_rcpt_istc | String | 필수 | 신청 방법 방문 접수 설명 | - |
| aply_mthd_pssr_rcpt_istc | String | 필수 | 신청 방법 우편 접수 설명 | - |
| aply_mthd_fax_rcpt_istc | String | 필수 | 신청 방법 팩스 접수 설명 | - |
| aply_mthd_eml_rcpt_istc | String | 필수 | 신청 방법 이메일 접수 설명 | - |
| aply_mthd_onli_rcpt_istc | String | 필수 | 신청 방법 온라인 접수 설명 | - |
| aply_mthd_etc_istc | String | 필수 | 신청 방법 기타 설명 | - |
| aply_exclt_trgt_ctnt | String | 필수 | 신청제외대상내용 | - |
| aply_trgt | String(200) | 필수 | 신청 대상 | 청소년,대학생,일반인 |
| biz_enyy | String(200) | 필수 | 창업 기간 | 7년미만,5년미만,3년미만,2년미만,1년미만,예비창업자 |
| biz_trgt_age | String(200) | 필수 | 대상 연령 | 만 20세 미만, 만 20세 이상 ~ 만 39세 이하, 만 40세 이상 |
| prfn_matr | String(200) | 필수 | 우대 사항 | - |
| Rcrt_prgs_yn | String(1) | 필수 | 모집진행여부 | Y |
| pbanc_sn | String(32) | 필수 | 공고일련번호 | 1234 |

### 2.3 창업관련 콘텐츠 정보 (getContentInformation)

#### 개요
- **기능**: 정책·규제 정보, 생태계 이슈·동향, 창업우수사례 정보 등 콘텐츠 정보 조회
- **엔드포인트**: /getContentInformation01
- **전체 URL**: https://apis.data.go.kr/B552735/kisedKstartupService01/getContentInformation01

#### 요청 파라미터
| 파라미터명 | 타입 | 필수여부 | 설명 | 예시 |
|-----------|------|----------|------|------|
| ServiceKey | String(100) | 필수 | 공공데이터포털 인증키 (URL Encode 필요) | - |
| page | Number(100) | 선택 | 페이지 번호 | 1 |
| perPage | Number(100) | 선택 | 한 페이지 결과 수 | 10 |
| returnType | String(50) | 선택 | 반환 타입 | json 또는 XML |
| clss_cd | String(50) | 선택 | 콘텐츠 구분 코드 | notice_matr |
| titl_nm | String(300) | 선택 | 제목 | 2023년 창업에듀 영상 콘텐츠 공모전 선정결과 안내 |

#### 응답 데이터
| 필드명 | 타입 | 필수여부 | 설명 | 예시 |
|--------|------|----------|------|------|
| clss_cd | String(50) | 필수 | 콘텐츠 구분 코드 | notice_matr |
| titl_nm | String(300) | 필수 | 제목 | 2023년 창업에듀 영상 콘텐츠 공모전 선정결과 안내 |
| fstm_reg_dt | String | 필수 | 등록 일시 | 2023-10-31 17:45:34 |
| view_cnt | Number(7) | 필수 | 조회 수 | 38 |
| detl_pg_url | String(500) | 필수 | 상세페이지 URL | www.k-startup.go.kr/web/contents/webNotice_MATR.do?id=160721&schM=view |
| file_nm | String(300) | 필수 | 파일명 | 2023년 창업에듀 영상 콘텐츠 공모전 선정결과 안내.pdf |

### 2.4 창업관련 통계보고서 정보 (getStatisticalInformation)

#### 개요
- **기능**: 창업기업 업력, 형태, 분야, 해외진출 여부 등 통계보고서 정보 조회
- **엔드포인트**: /getStatisticalInformation01
- **전체 URL**: https://apis.data.go.kr/B552735/kisedKstartupService01/getStatisticalInformation01

#### 요청 파라미터
| 파라미터명 | 타입 | 필수여부 | 설명 | 예시 |
|-----------|------|----------|------|------|
| ServiceKey | String(100) | 필수 | 공공데이터포털 인증키 (URL Encode 필요) | - |
| page | Number(100) | 선택 | 페이지 번호 | 1 |
| perPage | Number(100) | 선택 | 한 페이지 결과 수 | 10 |
| returnType | String(50) | 선택 | 반환 타입 | json 또는 XML |
| titl_nm | String(300) | 선택 | 통계 자료명 | 중소기업청 창업진흥원 창업기업 실태조사 보고서(2013) |
| file_nm | String(1000) | 선택 | 통계 자료 내용 | - |

#### 응답 데이터
| 필드명 | 타입 | 필수여부 | 설명 | 예시 |
|--------|------|----------|------|------|
| titl_nm | String(300) | 필수 | 통계 자료명 | 중소기업청 창업진흥원 창업기업 실태조사 보고서(2013) |
| ctnt | String | 필수 | 통계 자료 내용 | 2023년 창업기업 실태조사... |
| fstm_reg_dt | String | 필수 | 등록 일시 | 2016-05-24 09:22:58 |
| last_mdfcn_dt | String | 필수 | 수정 일시 | 2022-04-04 14:18:41 |
| detl_pg_url | String(500) | 필수 | 상세페이지 URL | www.k-startup.go.kr/web/contents/webFND_STATS_RSCH_DATA.do?id=75403&schM=view |
| file_nm | String(1000) | 필수 | 다운로드 파일명 | 2013년 창업기업 실태조사.pdf |

## 3. 에러 코드 정의

| 에러코드 | 에러메시지 | 설명 |
|---------|-----------|------|
| 1 | APPLICATION_ERROR | 어플리케이션 에러 |
| 10 | INVALID_REQUEST_PARAMETER_ERROR | 잘못된 요청 파라미터 에러 |
| 12 | NO_OPENAPI_SERVICE_ERROR | 해당 오픈 API 서비스가 없거나 폐기됨 |
| 20 | SERVICE_ACCESS_DENIED_ERROR | 서비스 접근거부 |
| 22 | LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR | 서비스 요청제한횟수 초과에러 |
| 30 | SERVICE_KEY_IS_NOT_REGISTERED_ERROR | 등록되지 않은 서비스키 |
| 31 | DEADLINE_HAS_EXPIRED_ERROR | 기한만료된 서비스키 |
| 32 | UNREGISTERED_IP_ERROR | 등록되지 않은 IP |
| 99 | UNKNOWN_ERROR | 기타에러 |

## 4. API 호출 예시

### 4.1 통합공고 지원사업 정보 조회
```http
GET https://apis.data.go.kr/B552735/kisedKstartupService01/getBusinessInformation01?ServiceKey=인증키&page=1&perPage=10&returnType=json
```

### 4.2 지원사업 공고 정보 조회
```http
GET https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01?ServiceKey=인증키&intg_pbanc_yn=N&supt_biz_clsfc=행사·네트워크
```

### 4.3 창업관련 콘텐츠 정보 조회
```http
GET https://apis.data.go.kr/B552735/kisedKstartupService01/getContentInformation01?ServiceKey=인증키&clss_cd=notice_matr
```

### 4.4 창업관련 통계보고서 정보 조회
```http
GET https://apis.data.go.kr/B552735/kisedKstartupService01/getStatisticalInformation01?ServiceKey=인증키
```

## 5. 응답 형식 예시

### JSON 응답 (기본)
```json
{
  "items": {
    "item": [
      {
        "biz_category_cd": "cmrczn_Tab3",
        "supt_biz_titl_nm": "1인 창조기업 활성화 지원사업",
        "biz_supt_trgt_info": "「1인 창조기업 육성에 관한 법률」제2조의 (예지) 1인 창조기업",
        // ... 기타 필드
      }
    ]
  }
}
```

### XML 응답
```xml
<items>
  <item>
    <biz_category_cd>cmrczn_Tab3</biz_category_cd>
    <supt_biz_titl_nm>1인 창조기업 활성화 지원사업</supt_biz_titl_nm>
    <biz_supt_trgt_info>「1인 창조기업 육성에 관한 법률」제2조의 (예지) 1인 창조기업</biz_supt_trgt_info>
    <!-- 기타 필드 -->
  </item>
</items>
```

## 6. 주의사항 및 권장사항

### 6.1 인증키 관리
- ServiceKey는 공공데이터포털에서 발급받은 인증키를 사용
- URL 인코딩이 필요한 경우가 있으므로 주의
- 인증키 만료 시 에러코드 31 반환

### 6.2 요청 제한
- 초당 최대 30개의 트랜잭션 제한
- 제한 초과 시 에러코드 22 반환

### 6.3 파라미터 사용 팁
- 기본 응답 형식은 JSON이므로 returnType 생략 가능
- 페이징 처리 시 page와 perPage 파라미터 활용
- 검색 조건을 좁히려면 각 API별 선택 파라미터 활용

### 6.4 날짜 형식
- 요청 시: YYYYMMDD (예: 20121129)
- 응답 시: YYYY-MM-DD HH:MM:SS (예: 2012-11-29 00:00:00)

### 6.5 응답 데이터 처리
- 빈 값은 빈 문자열("")로 반환
- 리스트 형태의 데이터는 쉼표로 구분된 문자열로 반환
- HTML 태그가 포함된 콘텐츠가 있을 수 있음 (ctnt 필드 등)

## 7. 실제 활용 시나리오

### 7.1 특정 사업 구분의 지원사업 찾기
```http
GET .../getBusinessInformation01?ServiceKey=KEY&biz_category_cd=cmrczn_Tab3&biz_yr=2023
```

### 7.2 현재 모집 중인 공고 조회
```http
GET .../getAnnouncementInformation01?ServiceKey=KEY&Rcrt_prgs_yn=Y&page=1&perPage=20
```

### 7.3 최신 콘텐츠 조회
```http
GET .../getContentInformation01?ServiceKey=KEY&page=1&perPage=5&returnType=json
```

### 7.4 통계 보고서 검색
```http
GET .../getStatisticalInformation01?ServiceKey=KEY&titl_nm=창업기업
```