from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from ...shared.models.base import BaseDocument


class AnnouncementData(BaseModel):
    """사업공고 개별 데이터 모델 - API 데이터를 완전히 반영"""
    
    # === 기본 공고 정보 ===
    announcement_id: Optional[str] = Field(
        None, 
        description="공고 번호",
        example="174380"
    )
    title: Optional[str] = Field(
        None, 
        description="사업공고명",
        example="2025년 RIST 첨단제조인큐베이팅센터 입주기업 모집 공고"
    )
    content: Optional[str] = Field(
        None, 
        description="공고 내용",
        example="신소재·바이오 등 첨단 제조 분야에서 독보적인 기술력과 성장 가능성을 갖춘 유망 스타트업을 발굴·지원..."
    )
    
    # === 일정 정보 ===
    start_date: Optional[str] = Field(
        None, 
        description="공고 접수 시작일",
        example="2025-07-28"
    )
    end_date: Optional[str] = Field(
        None, 
        description="공고 접수 종료일",
        example="2025-09-05"
    )
    announcement_date: Optional[datetime] = Field(
        None, 
        description="공고 발표일"
    )
    deadline: Optional[datetime] = Field(
        None, 
        description="신청 마감일"
    )
    
    # === 사업 정보 ===
    business_category: Optional[str] = Field(
        None, 
        description="지원사업구분",
        example="시설ㆍ공간ㆍ보육"
    )
    integrated_business_name: Optional[str] = Field(
        None, 
        description="통합공고사업명",
        example="2025년 RIST 첨단제조인큐베이팅센터 입주기업 모집 공고"
    )
    business_overview: Optional[str] = Field(
        None, 
        description="사업 개요 (content와 동일)",
        example="신소재·바이오 등 첨단 제조 분야에서 독보적인 기술력과 성장 가능성을 갖춘 유망 스타트업을 발굴·지원..."
    )
    
    # === 지원 대상 및 조건 ===
    application_target: Optional[str] = Field(
        None, 
        description="신청 대상",
        example="일반기업"
    )
    application_target_content: Optional[str] = Field(
        None, 
        description="신청 대상 상세 내용",
        example="모집공고일 기준 창업 7년 미만의 우수 기술을 보유한 기업"
    )
    application_exclusion_content: Optional[str] = Field(
        None, 
        description="신청 제외 대상 내용",
        example="부실기업, 휴업기업 등"
    )
    support_target: Optional[str] = Field(
        None, 
        description="지원 대상 (application_target과 유사)",
        example="일반기업"
    )
    business_entry: Optional[str] = Field(
        None, 
        description="사업 참여 년수",
        example="7년미만,10년미만"
    )
    business_target_age: Optional[str] = Field(
        None, 
        description="사업 대상 연령",
        example="만 20세 미만,만 20세 이상 ~ 만 39세 이하,만 40세 이상"
    )
    support_region: Optional[str] = Field(
        None, 
        description="지원 지역",
        example="전국"
    )
    
    # === 기관 정보 ===
    organization: Optional[str] = Field(
        None, 
        description="공고 기관명",
        example="(재)포항산업과학연구원장"
    )
    supervising_institution: Optional[str] = Field(
        None, 
        description="감독 기관",
        example="민간"
    )
    contact_department: Optional[str] = Field(
        None, 
        description="담당 부서명",
        example="기술사업화그룹"
    )
    contact_number: Optional[str] = Field(
        None, 
        description="연락처 번호",
        example="0542796567"
    )
    contact_info: Optional[str] = Field(
        None, 
        description="통합 문의처 정보",
        example="기술사업화그룹 (0542796567)"
    )
    
    # === URL 정보 ===
    detail_page_url: Optional[str] = Field(
        None, 
        description="상세 페이지 URL",
        example="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174380"
    )
    business_guidance_url: Optional[str] = Field(
        None, 
        description="사업 안내 URL",
        example="https://www.k-startup.go.kr/guide"
    )
    business_application_url: Optional[str] = Field(
        None, 
        description="사업 신청 URL",
        example="https://www.k-startup.go.kr/apply"
    )
    
    # === 신청 방법 정보 ===
    application_method: Optional[str] = Field(
        None, 
        description="신청 방법 및 절차",
        example="온라인 접수"
    )
    online_reception: Optional[str] = Field(
        None, 
        description="온라인 접수처",
        example="https://www.k-startup.go.kr"
    )
    visit_reception: Optional[str] = Field(
        None, 
        description="방문 접수처",
        example="서울시 강남구 테헤란로 123"
    )
    email_reception: Optional[str] = Field(
        None, 
        description="이메일 접수처",
        example="info@k-startup.go.kr"
    )
    fax_reception: Optional[str] = Field(
        None, 
        description="팩스 접수처",
        example="02-1234-5678"
    )
    postal_reception: Optional[str] = Field(
        None, 
        description="우편 접수처",
        example="서울시 강남구 우편접수처"
    )
    other_reception: Optional[str] = Field(
        None, 
        description="기타 접수처",
        example="기타 접수 방법"
    )
    
    # === 상태 정보 ===
    status: Optional[str] = Field(
        None, 
        description="공고 현재 상태",
        example="모집중"
    )
    integrated_announcement: Optional[str] = Field(
        None, 
        description="통합 공고 여부",
        example="N"
    )
    recruitment_progress: Optional[str] = Field(
        None, 
        description="모집 진행 여부",
        example="Y"
    )
    performance_material: Optional[str] = Field(
        None, 
        description="수행 자료",
        example="사업 수행 관련 자료"
    )
    
    # === 레거시 필드 (하위 호환성) ===
    business_id: Optional[str] = Field(
        None, 
        description="사업 고유 ID (announcement_id로 대체됨)",
        example="KISED-2024-001"
    )
    business_name: Optional[str] = Field(
        None, 
        description="사업명 (title로 대체됨)",
        example="창업도약패키지"
    )
    business_type: Optional[str] = Field(
        None, 
        description="사업 유형 분류 (business_category로 대체됨)",
        example="정부지원사업"
    )
    recruitment_period: Optional[str] = Field(
        None, 
        description="모집 기간 (start_date, end_date로 대체됨)",
        example="2024.03.15 ~ 2024.04.15"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        },
        json_schema_extra={
            "example": {
                "announcement_id": "174380",
                "title": "2025년 RIST 첨단제조인큐베이팅센터 입주기업 모집 공고",
                "content": "신소재·바이오 등 첨단 제조 분야에서 독보적인 기술력과 성장 가능성을 갖춘 유망 스타트업을 발굴·지원하고자...",
                "start_date": "2025-07-28",
                "end_date": "2025-09-05",
                "business_category": "시설ㆍ공간ㆍ보육",
                "application_target": "일반기업",
                "application_target_content": "모집공고일 기준 창업 7년 미만의 우수 기술을 보유한 기업",
                "business_entry": "7년미만,10년미만",
                "support_region": "전국",
                "organization": "(재)포항산업과학연구원장",
                "contact_department": "기술사업화그룹",
                "contact_number": "0542796567",
                "detail_page_url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174380",
                "status": "모집중",
                "recruitment_progress": "Y"
            }
        }
    )


class Announcement(BaseModel):
    """사업공고 MongoDB 문서 모델"""
    id: Optional[str] = Field(None, alias="_id", description="고유 식별자")
    announcement_data: AnnouncementData
    source_url: Optional[str] = Field(None, description="원본 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }
    )


class AnnouncementCreate(BaseModel):
    """사업공고 생성 요청 모델"""
    announcement_data: AnnouncementData = Field(
        description="생성할 사업공고 데이터"
    )
    source_url: Optional[str] = Field(
        None,
        description="데이터 출처 URL",
        example="https://www.data.go.kr/dataset/15121654"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "business_id": "KISED-2024-001",
                    "business_name": "창업도약패키지",
                    "business_type": "정부지원사업",
                    "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
                    "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
                    "status": "모집중"
                },
                "source_url": "https://www.data.go.kr/dataset/15121654"
            }
        }
    )


class AnnouncementUpdate(BaseModel):
    """사업공고 수정 요청 모델"""
    announcement_data: Optional[AnnouncementData] = Field(
        None,
        description="수정할 사업공고 데이터 (일부 필드만 업데이트 가능)"
    )
    source_url: Optional[str] = Field(
        None,
        description="수정할 출처 URL"
    )
    is_active: Optional[bool] = Field(
        None,
        description="활성 상태 변경 (True: 활성, False: 비활성)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "status": "마감"
                },
                "is_active": False
            }
        }
    )


class AnnouncementResponse(BaseModel):
    """사업공고 응답 모델"""
    id: str = Field(
        description="사업공고 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    )
    announcement_data: AnnouncementData = Field(
        description="사업공고 상세 데이터"
    )
    source_url: Optional[str] = Field(
        description="데이터 출처 URL",
        example="https://www.data.go.kr/dataset/15121654"
    )
    is_active: bool = Field(
        description="활성 상태",
        example=True
    )
    created_at: datetime = Field(
        description="생성 일시",
        example="2024-03-01T09:00:00Z"
    )
    updated_at: datetime = Field(
        description="최종 수정 일시",
        example="2024-03-01T09:00:00Z"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        },
        json_schema_extra={
            "example": {
                "id": "65f1a2b3c4d5e6f7a8b9c0d1",
                "announcement_data": {
                    "business_id": "KISED-2024-001",
                    "business_name": "창업도약패키지",
                    "business_type": "정부지원사업",
                    "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
                    "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
                    "recruitment_period": "2024.03.15 ~ 2024.04.15",
                    "application_method": "온라인 접수 (www.k-startup.go.kr)",
                    "contact_info": "창업진흥원 창업성장실 02-123-4567",
                    "announcement_date": "2024-03-01T09:00:00Z",
                    "deadline": "2024-04-15T18:00:00Z",
                    "status": "모집중"
                },
                "source_url": "https://www.data.go.kr/dataset/15121654",
                "is_active": True,
                "created_at": "2024-03-01T09:00:00Z",
                "updated_at": "2024-03-01T09:00:00Z"
            }
        }
    )