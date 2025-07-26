"""
Classification code enumerations.

Defines enums for business categories and content categories based on K-Startup API specifications.
"""

from enum import Enum
from typing import Dict, List, Tuple


class BusinessCategory(Enum):
    """
    Business category codes for K-Startup support programs.
    
    Based on BIZ_CATEGORY_CD specification with 9 main categories.
    """
    
    # 사업화 - Commercialization
    COMMERCIALIZATION = "cmrczn_tab1"
    
    # 창업교육 - Startup Education
    STARTUP_EDUCATION = "cmrczn_tab2"
    
    # 시설,공간,보육 - Facilities, Space, Incubation
    FACILITIES_SPACE_INCUBATION = "cmrczn_tab3"
    
    # 멘토링,컨설팅 - Mentoring, Consulting
    MENTORING_CONSULTING = "cmrczn_tab4"
    
    # 행사,네트워크 - Events, Networking
    EVENTS_NETWORKING = "cmrczn_tab5"
    
    # 기술개발 R&D - Technology Development R&D
    TECHNOLOGY_RND = "cmrczn_tab6"
    
    # 융자 - Loan
    LOAN = "cmrczn_tab7"
    
    # 인력 - Human Resources
    HUMAN_RESOURCES = "cmrczn_tab8"
    
    # 글로벌 - Global
    GLOBAL = "cmrczn_tab9"
    
    @classmethod
    def get_description(cls, code: str) -> str:
        """Get Korean description for a business category code."""
        descriptions = {
            cls.COMMERCIALIZATION.value: "사업화",
            cls.STARTUP_EDUCATION.value: "창업교육",
            cls.FACILITIES_SPACE_INCUBATION.value: "시설,공간,보육",
            cls.MENTORING_CONSULTING.value: "멘토링,컨설팅",
            cls.EVENTS_NETWORKING.value: "행사,네트워크",
            cls.TECHNOLOGY_RND.value: "기술개발 R&D",
            cls.LOAN.value: "융자",
            cls.HUMAN_RESOURCES.value: "인력",
            cls.GLOBAL.value: "글로벌"
        }
        return descriptions.get(code, "알 수 없음")
    
    @classmethod
    def get_detailed_description(cls, code: str) -> str:
        """Get detailed Korean description for a business category code."""
        detailed_descriptions = {
            cls.COMMERCIALIZATION.value: "아이디어나 기술을 실제 사업으로 전환하는 과정을 지원하는 프로그램 (국내외 모두 포함)",
            cls.STARTUP_EDUCATION.value: "예비 창업자 및 초기 창업자를 위한 교육 프로그램",
            cls.FACILITIES_SPACE_INCUBATION.value: "창업 기업을 위한 물리적 공간 및 인큐베이팅 서비스 제공",
            cls.MENTORING_CONSULTING.value: "전문가의 경영 자문 및 멘토링 서비스 제공",
            cls.EVENTS_NETWORKING.value: "창업 생태계 활성화를 위한 네트워킹 및 행사 지원 (국내외 모두 포함)",
            cls.TECHNOLOGY_RND.value: "연구개발 활동을 위한 자금 및 인프라 지원",
            cls.LOAN.value: "창업 기업을 위한 정책 자금 대출 프로그램",
            cls.HUMAN_RESOURCES.value: "창업 기업의 인력 채용 및 양성 지원",
            cls.GLOBAL.value: "해외 진출 및 글로벌 비즈니스 전문 지원 (해외 특화)"
        }
        return detailed_descriptions.get(code, "상세 설명 없음")
    
    @classmethod
    def get_main_features(cls, code: str) -> List[str]:
        """Get main features for a business category code."""
        features = {
            cls.COMMERCIALIZATION.value: [
                "사업 모델 개발 지원",
                "제품/서비스 상용화 지원",
                "판로 개척 지원 (국내/해외)",
                "마케팅 전략 수립 지원"
            ],
            cls.STARTUP_EDUCATION.value: [
                "창업 기초 교육",
                "전문 분야별 심화 교육",
                "창업 실무 교육",
                "온라인/오프라인 교육 과정"
            ],
            cls.FACILITIES_SPACE_INCUBATION.value: [
                "사무 공간 제공",
                "제조/연구 시설 지원",
                "창업 보육 센터 입주",
                "공용 장비 및 시설 이용 지원"
            ],
            cls.MENTORING_CONSULTING.value: [
                "경영 전략 컨설팅",
                "기술 개발 자문",
                "1:1 전문가 멘토링",
                "분야별 전문 컨설팅"
            ],
            cls.EVENTS_NETWORKING.value: [
                "창업 경진대회 (국내/국제)",
                "네트워킹 행사",
                "투자 설명회(IR)",
                "전시회 및 박람회 참가 지원 (국내/해외)"
            ],
            cls.TECHNOLOGY_RND.value: [
                "R&D 자금 지원",
                "기술 개발 과제 지원",
                "연구 인프라 제공",
                "기술 이전 및 사업화 연계"
            ],
            cls.LOAN.value: [
                "저금리 정책 자금 대출",
                "운전 자금 지원",
                "시설 자금 지원",
                "특별 융자 프로그램"
            ],
            cls.HUMAN_RESOURCES.value: [
                "인건비 지원",
                "인력 매칭 서비스",
                "직무 교육 지원",
                "청년 인턴십 프로그램"
            ],
            cls.GLOBAL.value: [
                "해외 시장 진출 전문 지원",
                "글로벌 액셀러레이팅 프로그램",
                "해외 현지화 지원",
                "수출 전문 컨설팅 및 바이어 매칭"
            ]
        }
        return features.get(code, [])
    
    @classmethod
    def get_all_codes(cls) -> List[str]:
        """Get all business category codes."""
        return [category.value for category in cls]
    
    @classmethod
    def get_all_info(cls) -> List[Dict[str, any]]:
        """Get comprehensive information for all business categories."""
        return [
            {
                "code": category.value,
                "name": cls.get_description(category.value),
                "description": cls.get_detailed_description(category.value),
                "features": cls.get_main_features(category.value)
            }
            for category in cls
        ]
    
    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """Check if a code is a valid business category code."""
        return code in cls.get_all_codes()


class ContentCategory(Enum):
    """
    Content category codes for K-Startup content information.
    
    Based on CLSS_CD specification with 3 main categories.
    """
    
    # 정책 및 규제정보(공지사항) - Policy and Regulatory Information (Notices)
    POLICY_NOTICE = "notice_matr"
    
    # 창업우수사례 - Excellent Startup Cases
    SUCCESS_CASE = "fnd_scs_case"
    
    # 생태계 이슈, 동향 - Ecosystem Issues and Trends
    ECOSYSTEM_TRENDS = "kstartup_isse_trd"
    
    @classmethod
    def get_description(cls, code: str) -> str:
        """Get Korean description for a content category code."""
        descriptions = {
            cls.POLICY_NOTICE.value: "정책 및 규제정보(공지사항)",
            cls.SUCCESS_CASE.value: "창업우수사례",
            cls.ECOSYSTEM_TRENDS.value: "생태계 이슈, 동향"
        }
        return descriptions.get(code, "알 수 없음")
    
    @classmethod
    def get_detailed_description(cls, code: str) -> str:
        """Get detailed Korean description for a content category code."""
        detailed_descriptions = {
            cls.POLICY_NOTICE.value: "정부 정책, 규제 변경사항, 공식 공지사항 등 창업 관련 정책 정보",
            cls.SUCCESS_CASE.value: "성공적인 창업 기업의 사례 및 스토리, 벤치마킹 가능한 우수 사례",
            cls.ECOSYSTEM_TRENDS.value: "창업 생태계의 최신 이슈, 트렌드, 시장 동향 등 분석 정보"
        }
        return detailed_descriptions.get(code, "상세 설명 없음")
    
    @classmethod
    def get_content_types(cls, code: str) -> List[str]:
        """Get content types for a content category code."""
        content_types = {
            cls.POLICY_NOTICE.value: [
                "정부 창업 정책 발표",
                "규제 개선 및 변경 사항",
                "창업 지원 제도 안내",
                "공식 공지사항 및 알림",
                "법령 및 제도 변경 안내"
            ],
            cls.SUCCESS_CASE.value: [
                "창업 성공 스토리",
                "우수 창업 기업 인터뷰",
                "혁신 제품/서비스 사례",
                "투자 유치 성공 사례",
                "글로벌 진출 성공 사례",
                "업종별 성공 전략 분석"
            ],
            cls.ECOSYSTEM_TRENDS.value: [
                "창업 시장 동향 분석",
                "투자 시장 트렌드",
                "신기술 및 산업 동향",
                "창업 생태계 이슈",
                "글로벌 스타트업 트렌드",
                "산업별 시장 전망"
            ]
        }
        return content_types.get(code, [])
    
    @classmethod
    def get_all_codes(cls) -> List[str]:
        """Get all content category codes."""
        return [category.value for category in cls]
    
    @classmethod
    def get_all_info(cls) -> List[Dict[str, any]]:
        """Get comprehensive information for all content categories."""
        return [
            {
                "code": category.value,
                "name": cls.get_description(category.value),
                "description": cls.get_detailed_description(category.value),
                "content_types": cls.get_content_types(category.value)
            }
            for category in cls
        ]
    
    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """Check if a code is a valid content category code."""
        return code in cls.get_all_codes()


class ClassificationCodeType(Enum):
    """Types of classification codes."""
    
    BUSINESS_CATEGORY = "business_category"
    CONTENT_CATEGORY = "content_category"
    
    @classmethod
    def get_enum_class(cls, code_type: str):
        """Get the appropriate enum class for a code type."""
        mapping = {
            cls.BUSINESS_CATEGORY.value: BusinessCategory,
            cls.CONTENT_CATEGORY.value: ContentCategory
        }
        return mapping.get(code_type)
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all classification code types."""
        return [code_type.value for code_type in cls]