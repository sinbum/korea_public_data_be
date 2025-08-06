#!/usr/bin/env python3
"""데이터 요청 관련 초기 데이터 설정 스크립트"""

import asyncio
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.domains.data_requests.tasks import initialize_default_categories


async def main():
    """메인 함수"""
    print("데이터 요청 관련 초기 데이터 설정을 시작합니다...")
    
    try:
        # 기본 카테고리 초기화
        result = await initialize_default_categories()
        print(f"카테고리 초기화 완료: {result['created_count']}/{result['total_categories']} 개 생성됨")
        
        print("초기 데이터 설정이 완료되었습니다!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())