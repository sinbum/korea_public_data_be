# Q&A - 개발 중 질문사항

이 문서는 개발 과정에서 발생하는 질문사항과 해결방안을 기록합니다.

## 아키텍처 관련

### Q1: BaseAPIClient에서 제네릭 타입 T를 어떻게 활용해야 하나요?
**A:** BaseAPIClient[T]의 T는 API 응답 데이터의 타입을 나타냅니다.
- KStartupAPIClient는 `BaseAPIClient[KStartupAPIResponse]`로 구현
- 각 도메인별로 특화된 응답 타입을 정의하여 타입 안전성 확보
- `APIResponse[T]`를 통해 일관된 응답 구조 제공

### Q2: Strategy Pattern과 Template Method Pattern을 함께 사용하는 이유는?
**A:** 
- **Strategy Pattern**: 인증, 요청 처리 방식 등 알고리즘을 런타임에 교체 가능
- **Template Method Pattern**: API 호출의 전체 흐름(전처리→인증→호출→후처리)을 표준화
- 두 패턴을 조합하여 유연성과 일관성을 동시에 확보

### Q3: 플러그인 시스템이 필요한 이유는?
**A:** 
- 새로운 공공데이터 API 추가 시 기존 코드 수정 없이 확장 가능
- 런타임에 플러그인 활성화/비활성화 가능
- 의존성 관리 및 버전 관리 지원
- 모듈화된 아키텍처로 유지보수성 향상

## 기술적 구현

### Q4: MongoDB ObjectId를 문자열로 변환하는 이유는?
**A:** 
- JSON 직렬화 지원을 위해 필수
- Pydantic 모델의 `id` 필드와 MongoDB `_id` 필드 매핑
- API 응답에서 일관된 ID 형식 제공
- 프론트엔드에서 사용하기 쉬운 형태

### Q5: 비동기 vs 동기 처리 선택 기준은?
**A:**
- **비동기**: 외부 API 호출, I/O 작업이 많은 경우
- **동기**: 데이터베이스 CRUD, 단순한 비즈니스 로직
- 현재는 pymongo(동기) 사용 중, 필요 시 Motor(비동기)로 전환 고려

### Q6: 에러 처리 전략은?
**A:**
- **커스텀 예외**: 도메인별 예외 클래스 정의
- **로깅**: 구조화된 로깅으로 추적 가능
- **재시도**: 일시적 오류에 대한 지수 백오프
- **사용자 친화적 메시지**: 내부 에러를 적절히 변환

## 개발 프로세스

### Q7: 새로운 도메인 추가 절차는?
**A:**
1. `app/domains/{domain_name}/` 폴더 생성
2. `models.py` - Pydantic 모델 정의
3. `repository.py` - BaseRepository 상속 구현
4. `service.py` - BaseService 상속 구현  
5. `router.py` - FastAPI 라우터 정의
6. Factory에 등록
7. main.py에 라우터 추가

### Q8: 테스트 작성 가이드라인은?
**A:**
- **단위 테스트**: 각 클래스/함수별 독립적 테스트
- **통합 테스트**: 여러 컴포넌트 간의 상호작용 테스트
- **Mock 사용**: 외부 의존성(API, DB) 모킹
- **Coverage**: 80% 이상 목표
- **pytest**: 테스트 프레임워크 표준

## 성능 및 확장성

### Q9: 캐싱 전략은?
**A:**
- **Redis**: 세션, API 응답 캐싱
- **Application-level**: 자주 조회되는 설정 데이터
- **Database**: 쿼리 결과 캐싱
- **TTL**: 데이터 특성에 따른 적절한 만료 시간 설정

### Q10: API Rate Limiting 구현 방법은?
**A:**
- **Token Bucket**: 일정 시간당 요청 수 제한
- **Sliding Window**: 더 정확한 요청 제어
- **Redis**: 분산 환경에서 카운터 관리
- **Custom Middleware**: FastAPI 미들웨어로 구현

## 보안

### Q11: API 키 관리 방법은?
**A:**
- **환경변수**: 민감한 정보는 .env 파일 분리
- **Docker Secrets**: 프로덕션 환경에서 보안 강화
- **Rotation**: 정기적인 키 교체 절차
- **Encryption**: 저장 시 암호화 고려

### Q12: 인증/인가 구현 계획은?
**A:**
- **JWT**: 토큰 기반 인증
- **OAuth 2.0**: 외부 서비스 연동
- **Role-based**: 사용자 역할별 접근 제어
- **API 키**: 서비스 간 통신 인증

## 다음 단계

### Q13: 우선순위가 높은 개선사항은?
**A:**
1. ~~K-Startup API 클라이언트 리팩토링 완료~~ ✅ (진행중 - BaseAPIClient 상속 완료)
2. Repository 패턴 전면 적용
3. 나머지 도메인(contents, statistics, businesses) 구현
4. 통합 검색 기능 구현
5. 성능 모니터링 시스템 구축

### Q14: K-Startup API 클라이언트 리팩토링에서 구현된 주요 개선사항은?
**A:**
- **GovernmentAPIKeyStrategy 사용**: 정부 API 키 인증 전략으로 교체
- **비동기 메서드 추가**: 모든 주요 API 메서드에 async 버전 추가
- **배치 처리 지원**: `get_all_data_batch()` 메서드로 여러 API 동시 호출
- **타입 안전성**: RequestMethod enum 사용으로 메서드 타입 안전성 향상
- **향상된 헤더 관리**: K-Startup 특화 User-Agent 및 Accept 헤더 설정
- **강화된 에러 처리**: 계층적 예외 구조와 상세한 에러 정보 제공
- **지능형 재시도**: 지수 백오프와 에러 타입별 맞춤 재시도 전략

### Q15: 새로운 에러 처리 시스템의 장점은?
**A:**
- **계층적 예외 구조**: KoreanPublicAPIError → APIClientError → 구체적 예외
- **에러 타입별 분류**: 네트워크, 인증, 서버, 데이터 파싱 에러 구분
- **상세한 컨텍스트**: 상태 코드, 에러 코드, 추가 메타데이터 포함
- **자동 예외 변환**: httpx 에러를 의미있는 도메인 예외로 변환
- **로깅 강화**: 구조화된 로깅으로 디버깅 및 모니터링 개선

### Q16: 재시도 전략은 어떻게 구성되나?
**A:**
- **ExponentialBackoffStrategy**: 기본 지수 백오프 전략
- **AdaptiveRetryStrategy**: 성공률 기반 적응형 재시도
- **조건별 재시도**: 서버 에러, 타임아웃, 네트워크 에러, 레이트 리밋별 설정
- **Jitter 적용**: 동시 요청 집중 방지를 위한 랜덤 지연
- **최대 재시도 횟수**: 안정성과 성능의 균형을 위한 제한

### Q17: API 응답 데이터 검증 시스템의 특징은?
**A:**
- **타입별 전용 모델**: AnnouncementItem, BusinessItem, ContentItem, StatisticalItem
- **자동 데이터 정제**: 빈 문자열 → None, URL 형식 정규화, 날짜 형식 표준화
- **Enum 기반 분류**: BusinessCategoryCode, ContentTypeCode로 타입 안전성 확보
- **검증 단계별 처리**: 필드 수준 → 모델 수준 → 응답 수준 검증
- **유연한 에러 처리**: 개별 아이템 검증 실패 시에도 전체 처리는 계속 진행
- **도메인별 응답 타입**: KStartupAnnouncementResponse, KStartupBusinessResponse 등

### Q18: pydantic 모델의 검증 규칙은?
**A:**
- **날짜 검증**: YYYYMMDD → YYYY-MM-DD 자동 변환, 유효 범위 확인
- **URL 검증**: http/https 스키마 자동 추가, 기본 형식 검증
- **숫자 검증**: 년도(2000-2050), 월(1-12) 범위 검증
- **문자열 정제**: 앞뒤 공백 제거, null/NULL → None 변환
- **추가 필드 허용**: API 응답 구조 변경에 유연하게 대응

### Q19: API 검증에서 발견된 치명적 불일치 사항들은?
**A:**
- **사업 분류 코드**: 문서(cmrczn_tab1=사업화) ≠ 구현(R&D), 85% 이상 불일치 발견
- **콘텐츠 분류**: 실제 API(notice_matr, fnd_scs_case) ≠ 구현(content_Tab1~5), 완전히 다른 체계
- **필드 매핑**: 실제 XML 필드(pbanc_sn, biz_pbanc_nm) ≠ alias(pbanc_no, pbanc_titl_nm)
- **결정**: 실제 API 응답 기준으로 전면 재정의, 문서보다 실제 동작이 우선

### Q20: Enum 재정의 시 기존 데이터 호환성 문제는?
**A:**
- **전략**: 현재 DB에 저장된 데이터가 거의 없으므로 바로 변경
- **향후**: 마이그레이션 스크립트 준비, 기존값 → 새값 매핑 테이블 생성
- **API**: 새로운 enum 값으로만 응답, 구버전 호환성은 별도 필드로 제공

### Q21: 한글 값을 Enum으로 사용하는 것의 장단점은?
**A:**
- **장점**: 실제 API 응답과 1:1 매핑, 의미 명확, 별도 변환 로직 불필요
- **단점**: 코드에 한글 포함, IDE 자동완성 불편, 국제화 시 문제 가능성
- **결정**: 현재는 한글 그대로 사용, 향후 i18n 필요 시 별도 매핑 테이블 생성

### Q22: AnnouncementItem 필드를 25개로 확장한 이유는?
**A:**
- **기존**: 13개 기본 필드만 매핑, 많은 정보 누락
- **개선**: 실제 API 응답의 모든 중요 필드 25개로 확장
- **추가된 카테고리**: 신청방법(6개), 대상정보(6개), 상태정보(3개), URL정보(3개)
- **장점**: 완전한 데이터 보존, 더 풍부한 API 응답 제공

### Q23: 마이그레이션 전략이 단순한 이유는?
**A:**
- **현실적 판단**: 현재 DB에 데이터가 거의 없어 복잡한 마이그레이션 불필요
- **전략**: 기존 enum 값 → 새 enum 값 매핑 테이블만 준비, 실제 적용은 보류
- **향후 계획**: 프로덕션 데이터가 쌓이면 정식 마이그레이션 스크립트 개발

### Q24: BusinessItem, ContentItem, StatisticalItem 모델 업데이트 기준은?
**A:**
- **API 명세서 완전 반영**: docs/kstartup-api-spec.md의 실제 응답 필드 100% 매핑
- **필드 수 간소화**: 불필요한 추정 필드 제거, 실제 API 응답에 있는 필드만 유지
- **alias 정확성**: XML 응답의 실제 필드명과 정확히 일치하도록 수정
- **타입 검증 강화**: 날짜, URL, 숫자 필드에 대한 적절한 validation 추가

### Q25: 모델별 주요 변경 사항은?
**A:**
- **BusinessItem**: 9개 실제 필드로 단순화 (biz_category_cd, supt_biz_titl_nm, biz_supt_trgt_info 등)
- **ContentItem**: 6개 핵심 필드로 정리 (clss_cd, titl_nm, fstm_reg_dt, view_cnt, detl_pg_url, file_nm)
- **StatisticalItem**: 6개 필드로 단순화 (titl_nm, ctnt, fstm_reg_dt, last_mdfcn_dt, detl_pg_url, file_nm)
- **공통**: 불확실한 필드 제거, validation 규칙 추가, URL/날짜 형식 정규화

### Q26: 모델 검증 테스트 결과는?
**A:**
- **성공률**: 3/3 모델 100% 성공적 생성 및 필드 매핑
- **필드 검증**: BusinessItem 9개, ContentItem 6개, StatisticalItem 6개 필드 모두 올바르게 populate
- **데이터 변환**: URL 자동 https 추가, 날짜 형식 유지, view_count 숫자 변환 정상 작동
- **결론**: 실제 API 명세서 기반 모델 업데이트 완료, 프로덕션 준비 상태

---

*이 문서는 개발 진행에 따라 지속적으로 업데이트됩니다.*