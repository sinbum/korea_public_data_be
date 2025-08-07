#!/usr/bin/env python3
"""
현재 KStartupAPIClient를 사용하여 실제 응답 데이터 분석
"""

import sys
import os
import json
from pprint import pprint

# 현재 프로젝트 경로 추가
sys.path.append('/app')

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.shared.models.kstartup import AnnouncementItem

def main():
    print("🚀 현재 KStartupAPIClient로 실제 데이터 분석 시작")
    print("=" * 60)
    
    try:
        # API 클라이언트 생성
        client = KStartupAPIClient()
        
        print("📡 K-Startup API 호출 중...")
        
        # 컨텍스트 매니저로 API 호출
        with client as api_client:
            response = api_client.get_announcement_information(
                page_no=1,
                num_of_rows=3
            )
        
        print(f"✅ API 호출 성공: {response.success}")
        print(f"📊 상태 코드: {response.status_code}")
        print(f"📈 총 개수: {response.total_count}")
        print(f"📋 현재 개수: {response.current_count}")
        
        if response.success and response.data:
            print(f"\n📦 응답 데이터 타입: {type(response.data)}")
            
            # 응답 데이터 구조 분석
            if hasattr(response.data, 'data'):
                items = response.data.data
                print(f"📝 데이터 아이템 수: {len(items)}")
                
                if items:
                    print(f"\n🔍 첫 번째 아이템 분석:")
                    first_item = items[0]
                    print(f"아이템 타입: {type(first_item)}")
                    
                    if isinstance(first_item, AnnouncementItem):
                        print("\n📋 AnnouncementItem 필드 분석:")
                        print("-" * 40)
                        
                        # 모든 필드 출력
                        for field_name in first_item.__fields__.keys():
                            value = getattr(first_item, field_name, None)
                            if value is not None:
                                print(f"✅ {field_name}: {value}")
                            else:
                                print(f"❌ {field_name}: None")
                        
                        print("\n📊 실제 데이터 딕셔너리:")
                        print("-" * 40)
                        item_dict = first_item.dict()
                        for key, value in item_dict.items():
                            if value is not None and value != "":
                                print(f"🔸 {key}: {value}")
                    
                    else:
                        print(f"원본 아이템 구조:")
                        pprint(first_item)
                        
            else:
                print(f"응답 데이터 전체 구조:")
                pprint(response.data)
        
        else:
            print(f"❌ API 호출 실패: {response.error}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()