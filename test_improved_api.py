#!/usr/bin/env python3
"""
개선된 API 데이터 변환 테스트
"""

import sys
import os
import json
from pprint import pprint

# 현재 프로젝트 경로 추가
sys.path.append('/app')

from app.domains.announcements.service import AnnouncementService
from app.domains.announcements.repository import AnnouncementRepository
from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.core.database import mongodb, connect_to_mongo

def main():
    print("🚀 개선된 API 데이터 변환 테스트 시작")
    print("=" * 60)
    
    try:
        # MongoDB 연결 초기화
        print("📡 MongoDB 연결 초기화 중...")
        connect_to_mongo()
        print("✅ MongoDB 연결 초기화 완료")
        
        # 연결 확인
        if mongodb.database is None:
            raise Exception("MongoDB database 연결 실패")
        print(f"📊 데이터베이스: {mongodb.database.name}")
        
        # Repository와 Service 생성
        repository = AnnouncementRepository(mongodb.database)
        service = AnnouncementService(repository)
        
        print("📡 개선된 데이터 수집 테스트...")
        
        # 새로운 데이터 수집 (소량)
        announcements = service.fetch_and_save_announcements(
            page_no=1,
            num_of_rows=2
        )
        
        print(f"✅ 수집된 공고 수: {len(announcements)}")
        
        if announcements:
            print(f"\n🔍 첫 번째 공고 상세 분석:")
            first_announcement = announcements[0]
            
            print(f"📋 MongoDB 문서 ID: {first_announcement.id}")
            print(f"📋 활성 상태: {first_announcement.is_active}")
            print(f"📋 생성 시간: {first_announcement.created_at}")
            
            # announcement_data 상세 분석
            data = first_announcement.announcement_data
            print(f"\n📊 확장된 데이터 필드 분석:")
            print("-" * 50)
            
            # 새로 추가된 중요 필드들 확인
            important_fields = [
                ("공고번호", "announcement_id"),
                ("공고명", "title"),
                ("사업분류", "business_category"),
                ("신청대상", "application_target"),
                ("신청대상상세", "application_target_content"),
                ("사업참여년수", "business_entry"),
                ("지원지역", "support_region"),
                ("주관기관", "organization"),
                ("담당부서", "contact_department"),
                ("연락처", "contact_number"),
                ("상세페이지", "detail_page_url"),
                ("온라인접수", "online_reception"),
                ("이메일접수", "email_reception"),
                ("모집진행여부", "recruitment_progress"),
                ("시작일", "start_date"),
                ("종료일", "end_date")
            ]
            
            print("🆕 새로 추가된 중요 필드들:")
            for field_name, field_key in important_fields:
                value = getattr(data, field_key, None)
                if value:
                    print(f"  ✅ {field_name}: {value}")
                else:
                    print(f"  ❌ {field_name}: None")
            
            print(f"\n📋 레거시 호환성 필드:")
            legacy_fields = [
                ("business_id", data.business_id),
                ("business_name", data.business_name),
                ("business_type", data.business_type),
                ("recruitment_period", data.recruitment_period),
            ]
            
            for field_name, value in legacy_fields:
                print(f"  📌 {field_name}: {value}")
        
        print(f"\n🎯 API 호출로 조회 테스트...")
        
        # API 엔드포인트 테스트
        result = service.get_announcements(page=1, page_size=2)
        
        print(f"✅ 조회된 공고 수: {len(result.items)}")
        print(f"📊 전체 공고 수: {result.total_count}")
        
        if result.items:
            print(f"\n📝 조회된 첫 번째 공고 요약:")
            first = result.items[0]
            data = first.announcement_data
            
            print(f"  📌 제목: {data.title}")
            print(f"  📌 기관: {data.organization}")
            print(f"  📌 연락처: {data.contact_number}")
            print(f"  📌 지원지역: {data.support_region}")
            print(f"  📌 상세URL: {data.detail_page_url}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()