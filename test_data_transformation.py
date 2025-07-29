#!/usr/bin/env python3
"""
데이터 변환 로직만 테스트 (DB 연결 없이)
"""

import sys
import os
import json
from pprint import pprint

# 현재 프로젝트 경로 추가
sys.path.append('/app')

from app.domains.announcements.service import AnnouncementService
from app.shared.clients.kstartup_api_client import KStartupAPIClient

def main():
    print("🚀 데이터 변환 로직 테스트 시작")
    print("=" * 60)
    
    try:
        # API 클라이언트를 통해 데이터 가져오기
        client = KStartupAPIClient()
        
        print("📡 K-Startup API 호출 중...")
        
        with client as api_client:
            response = api_client.get_announcement_information(
                page_no=1,
                num_of_rows=2
            )
        
        if response.success and response.data and hasattr(response.data, 'data'):
            items = response.data.data
            print(f"✅ API 데이터 수집 완료: {len(items)}개 아이템")
            
            if items:
                # 서비스 객체 생성 (repository 없이)
                service = AnnouncementService(repository=None)
                
                print(f"\n🔄 첫 번째 아이템 변환 테스트:")
                first_item = items[0]
                
                # 변환 전 원본 데이터 확인
                print(f"\n📋 변환 전 원본 데이터 (주요 필드만):")
                print(f"  📌 announcement_id: {first_item.announcement_id}")
                print(f"  📌 title: {first_item.title}")
                print(f"  📌 organization: {first_item.organization}")
                print(f"  📌 contact_number: {first_item.contact_number}")
                print(f"  📌 detail_page_url: {first_item.detail_page_url}")
                print(f"  📌 support_region: {first_item.support_region}")
                print(f"  📌 business_category: {first_item.business_category}")
                
                # 데이터 변환 수행
                transformed_data = service._transform_announcementitem_to_data(first_item)
                
                print(f"\n✅ 변환 완료! 총 {len(transformed_data)}개 필드 생성")
                
                print(f"\n📊 변환된 데이터 분석:")
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
                    value = transformed_data.get(field_key)
                    if value:
                        print(f"  ✅ {field_name}: {value}")
                    else:
                        print(f"  ❌ {field_name}: None")
                
                print(f"\n📋 레거시 호환성 필드:")
                legacy_fields = [
                    ("business_id", transformed_data.get("business_id")),
                    ("business_name", transformed_data.get("business_name")),
                    ("business_type", transformed_data.get("business_type")),
                    ("recruitment_period", transformed_data.get("recruitment_period")),
                ]
                
                for field_name, value in legacy_fields:
                    print(f"  📌 {field_name}: {value}")
                
                # 전체 필드 수 비교
                print(f"\n📈 데이터 활용도 분석:")
                print(f"  🔹 변환된 총 필드 수: {len(transformed_data)}")
                populated_count = sum(1 for v in transformed_data.values() if v is not None and v != "")
                print(f"  🔹 실제 데이터가 있는 필드 수: {populated_count}")
                print(f"  🔹 데이터 활용률: {populated_count/len(transformed_data)*100:.1f}%")
                
                # 이전 방식과 비교 (가정: 9개 필드만 사용)
                print(f"  📊 이전 대비 개선:")
                print(f"    - 이전: 9개 필드 사용")
                print(f"    - 현재: {populated_count}개 필드 사용")
                print(f"    - 개선률: {(populated_count-9)/9*100:.1f}% 향상")
                
        else:
            print(f"❌ API 호출 실패: {response.error if hasattr(response, 'error') else 'Unknown error'}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()