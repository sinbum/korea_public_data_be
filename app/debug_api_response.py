#!/usr/bin/env python3
"""
K-Startup API 실제 응답 구조 확인 스크립트
공공데이터 API로부터 실제 raw 데이터를 가져와서 구조를 분석합니다.
"""

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import sys

# API 설정
BASE_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01"
API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")

def fetch_api_data(endpoint, params, format_type="json"):
    """K-Startup API에서 데이터 가져오기"""
    url = f"{BASE_URL}/{endpoint}"
    
    # 기본 파라미터 설정
    default_params = {
        "serviceKey": API_KEY,
        "type": format_type,
        "page": 1,
        "perPage": 5
    }
    default_params.update(params)
    
    print(f"🔗 요청 URL: {url}")
    print(f"📋 파라미터: {default_params}")
    print("=" * 50)
    
    try:
        response = requests.get(url, params=default_params, timeout=30)
        print(f"✅ 응답 상태: {response.status_code}")
        print(f"📦 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            return response.text, response.headers.get('Content-Type', '')
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답 내용: {response.text[:500]}...")
            return None, None
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")
        return None, None

def analyze_json_structure(data, name=""):
    """JSON 데이터 구조 분석"""
    print(f"\n📊 {name} JSON 구조 분석:")
    
    try:
        json_data = json.loads(data)
        
        def analyze_object(obj, prefix="", max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return
                
            if isinstance(obj, dict):
                for key, value in obj.items():
                    value_type = type(value).__name__
                    if isinstance(value, (dict, list)) and len(str(value)) > 100:
                        value_preview = f"{value_type} (length: {len(value) if isinstance(value, (list, dict)) else 'unknown'})"
                    else:
                        value_preview = str(value)[:100] + ("..." if len(str(value)) > 100 else "")
                    
                    print(f"  {prefix}{key}: {value_type} = {value_preview}")
                    
                    if isinstance(value, dict) and current_depth < max_depth - 1:
                        analyze_object(value, prefix + "  ", max_depth, current_depth + 1)
                    elif isinstance(value, list) and value and current_depth < max_depth - 1:
                        print(f"  {prefix}  [배열 첫 번째 항목 구조:]")
                        analyze_object(value[0], prefix + "    ", max_depth, current_depth + 1)
                        
            elif isinstance(obj, list) and obj:
                print(f"  {prefix}배열 길이: {len(obj)}")
                if obj:
                    print(f"  {prefix}[첫 번째 항목 구조:]")  
                    analyze_object(obj[0], prefix + "  ", max_depth, current_depth + 1)
        
        analyze_object(json_data)
        return json_data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return None

def analyze_xml_structure(data, name=""):
    """XML 데이터 구조 분석"""
    print(f"\n📊 {name} XML 구조 분석:")
    
    try:
        root = ET.fromstring(data)
        
        def analyze_element(element, prefix="", max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return
                
            tag = element.tag
            text = (element.text or "").strip()
            attrs = element.attrib
            
            if text and len(text) > 100:
                text = text[:100] + "..."
            
            attr_str = f" {attrs}" if attrs else ""
            text_str = f" = '{text}'" if text else ""
            
            print(f"  {prefix}<{tag}{attr_str}>{text_str}")
            
            if current_depth < max_depth - 1:
                for child in element:
                    analyze_element(child, prefix + "  ", max_depth, current_depth + 1)
        
        analyze_element(root)
        return root
        
    except ET.ParseError as e:
        print(f"❌ XML 파싱 오류: {e}")
        return None

def main():
    """메인 실행 함수"""
    print("🚀 K-Startup API 실제 응답 구조 확인 시작")
    print("=" * 60)
    
    if not API_KEY:
        print("❌ PUBLIC_DATA_API_KEY 환경변수가 설정되지 않았습니다!")
        print("사용법: PUBLIC_DATA_API_KEY=your_key python debug_api_response.py")
        return
    
    # 테스트할 엔드포인트들
    endpoints_to_test = [
        {
            "name": "사업공고 정보",
            "endpoint": "getAnnouncementInformation01", 
            "params": {}
        }
    ]
    
    results = {}
    
    for test_case in endpoints_to_test:
        print(f"\n🎯 {test_case['name']} 테스트")
        print("-" * 40)
        
        # JSON 형식으로 요청
        json_data, json_content_type = fetch_api_data(
            test_case["endpoint"], 
            test_case["params"], 
            "json"
        )
        
        if json_data:
            print(f"\n📄 JSON 응답 원본 (처음 1000자):")
            print(json_data[:1000] + ("..." if len(json_data) > 1000 else ""))
            
            json_parsed = analyze_json_structure(json_data, test_case['name'])
            results[f"{test_case['name']}_json"] = json_parsed
            
            # JSON 응답을 파일로 저장
            with open(f"api_response_{test_case['endpoint']}.json", "w", encoding="utf-8") as f:
                f.write(json_data)
            print(f"💾 JSON 응답 저장: api_response_{test_case['endpoint']}.json")
        
        print("\n" + "="*60)
    
    # 결과 요약
    print("\n📋 분석 요약:")
    print("-" * 30)
    for name, data in results.items():
        if data:
            print(f"✅ {name}: 성공")
        else:
            print(f"❌ {name}: 실패")
    
    print("\n🎉 분석 완료!")

if __name__ == "__main__":
    main()