"""
Data validation utilities for Korean Public API platform.

Provides comprehensive validation functions for various data types and formats.
"""

import re
from typing import Any, Optional, List, Dict, Union
from datetime import datetime
from pydantic import BaseModel, validator, field_validator, ValidationError

from .exceptions import DataValidationError


class ValidationUtils:
    """데이터 검증 유틸리티 클래스"""
    
    @staticmethod
    def validate_korean_business_number(business_number: str) -> bool:
        """
        한국 사업자등록번호 유효성 검증
        
        Args:
            business_number: 사업자등록번호 (10자리)
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        # 하이픈 제거
        number = re.sub(r'[-\s]', '', business_number)
        
        # 10자리 숫자인지 확인
        if not re.match(r'^\d{10}$', number):
            return False
            
        # 체크섬 검증
        check_id = [1, 3, 7, 1, 3, 7, 1, 3, 5]
        total = 0
        
        for i in range(9):
            total += int(number[i]) * check_id[i]
            
        total += (int(number[8]) * 5) // 10
        
        return (10 - (total % 10)) % 10 == int(number[9])
    
    @staticmethod
    def validate_date_format(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """
        날짜 형식 유효성 검증
        
        Args:
            date_str: 날짜 문자열
            format: 날짜 형식 (기본값: "%Y-%m-%d")
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        한국 전화번호 유효성 검증
        
        Args:
            phone: 전화번호
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        # 하이픈, 공백, 괄호 제거
        number = re.sub(r'[-\s\(\)]', '', phone)
        
        # 한국 전화번호 패턴
        patterns = [
            r'^02\d{7,8}$',  # 서울
            r'^0[3-9]\d{1,2}\d{3,4}\d{4}$',  # 지역번호
            r'^01[0-9]\d{7,8}$',  # 휴대폰
            r'^070\d{7,8}$',  # 인터넷 전화
            r'^1[3-9]\d{2,3}$'  # 특수번호
        ]
        
        return any(re.match(pattern, number) for pattern in patterns)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        이메일 주소 유효성 검증
        
        Args:
            email: 이메일 주소
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        URL 유효성 검증
        
        Args:
            url: URL 문자열
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        pattern = r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_korean_registration_number(reg_number: str) -> bool:
        """
        법인등록번호 유효성 검증
        
        Args:
            reg_number: 법인등록번호 (13자리)
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        # 하이픈 제거
        number = re.sub(r'[-\s]', '', reg_number)
        
        # 13자리 숫자인지 확인
        if not re.match(r'^\d{13}$', number):
            return False
            
        # 체크섬 검증
        check_sum = 0
        for i in range(12):
            check_sum += int(number[i]) * ((i % 2) + 1)
            
        check_digit = (10 - (check_sum % 10)) % 10
        
        return check_digit == int(number[12])
    
    @staticmethod
    def validate_korean_zip_code(zip_code: str) -> bool:
        """
        한국 우편번호 유효성 검증 (5자리)
        
        Args:
            zip_code: 우편번호
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        return bool(re.match(r'^\d{5}$', zip_code))
    
    @staticmethod
    def validate_amount(amount: Union[str, int, float], min_value: float = 0) -> bool:
        """
        금액 유효성 검증
        
        Args:
            amount: 금액
            min_value: 최소값 (기본값: 0)
            
        Returns:
            유효한 경우 True, 아니면 False
        """
        try:
            value = float(str(amount).replace(',', ''))
            return value >= min_value
        except ValueError:
            return False


class DataValidator:
    """도메인별 데이터 검증 클래스"""
    
    @staticmethod
    def validate_announcement_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        공고 데이터 검증
        
        Args:
            data: 공고 데이터 딕셔너리
            
        Returns:
            필드별 검증 오류 딕셔너리
        """
        errors = {}
        utils = ValidationUtils()
        
        # 필수 필드 검증
        required_fields = ['title', 'organization_name', 'start_date', 'end_date']
        for field in required_fields:
            if not data.get(field):
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"{field}는 필수 입력 항목입니다.")
        
        # 날짜 검증
        if data.get('start_date') and not utils.validate_date_format(data['start_date']):
            if 'start_date' not in errors:
                errors['start_date'] = []
            errors['start_date'].append("시작일 형식이 올바르지 않습니다. (YYYY-MM-DD)")
            
        if data.get('end_date') and not utils.validate_date_format(data['end_date']):
            if 'end_date' not in errors:
                errors['end_date'] = []
            errors['end_date'].append("종료일 형식이 올바르지 않습니다. (YYYY-MM-DD)")
        
        # 날짜 논리 검증
        if data.get('start_date') and data.get('end_date'):
            try:
                start = datetime.strptime(data['start_date'], "%Y-%m-%d")
                end = datetime.strptime(data['end_date'], "%Y-%m-%d")
                if start > end:
                    if 'date_range' not in errors:
                        errors['date_range'] = []
                    errors['date_range'].append("시작일이 종료일보다 늦을 수 없습니다.")
            except ValueError:
                pass
        
        # URL 검증
        if data.get('detail_url') and not utils.validate_url(data['detail_url']):
            if 'detail_url' not in errors:
                errors['detail_url'] = []
            errors['detail_url'].append("상세 URL 형식이 올바르지 않습니다.")
        
        # 전화번호 검증
        if data.get('contact_phone') and not utils.validate_phone_number(data['contact_phone']):
            if 'contact_phone' not in errors:
                errors['contact_phone'] = []
            errors['contact_phone'].append("전화번호 형식이 올바르지 않습니다.")
        
        # 이메일 검증
        if data.get('contact_email') and not utils.validate_email(data['contact_email']):
            if 'contact_email' not in errors:
                errors['contact_email'] = []
            errors['contact_email'].append("이메일 형식이 올바르지 않습니다.")
        
        # 금액 검증
        if data.get('total_amount'):
            if not utils.validate_amount(data['total_amount']):
                if 'total_amount' not in errors:
                    errors['total_amount'] = []
                errors['total_amount'].append("금액은 0 이상의 숫자여야 합니다.")
        
        return errors
    
    @staticmethod
    def validate_business_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        사업정보 데이터 검증
        
        Args:
            data: 사업정보 데이터 딕셔너리
            
        Returns:
            필드별 검증 오류 딕셔너리
        """
        errors = {}
        utils = ValidationUtils()
        
        # 필수 필드 검증
        required_fields = ['business_name', 'business_category']
        for field in required_fields:
            if not data.get(field):
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"{field}는 필수 입력 항목입니다.")
        
        # 사업자등록번호 검증
        if data.get('business_number'):
            if not utils.validate_korean_business_number(data['business_number']):
                if 'business_number' not in errors:
                    errors['business_number'] = []
                errors['business_number'].append("사업자등록번호 형식이 올바르지 않습니다.")
        
        # 법인등록번호 검증
        if data.get('corporation_number'):
            if not utils.validate_korean_registration_number(data['corporation_number']):
                if 'corporation_number' not in errors:
                    errors['corporation_number'] = []
                errors['corporation_number'].append("법인등록번호 형식이 올바르지 않습니다.")
        
        # 우편번호 검증
        if data.get('zip_code'):
            if not utils.validate_korean_zip_code(data['zip_code']):
                if 'zip_code' not in errors:
                    errors['zip_code'] = []
                errors['zip_code'].append("우편번호는 5자리 숫자여야 합니다.")
        
        # 홈페이지 URL 검증
        if data.get('homepage_url') and not utils.validate_url(data['homepage_url']):
            if 'homepage_url' not in errors:
                errors['homepage_url'] = []
            errors['homepage_url'].append("홈페이지 URL 형식이 올바르지 않습니다.")
        
        return errors
    
    @staticmethod
    def validate_content_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        콘텐츠 데이터 검증
        
        Args:
            data: 콘텐츠 데이터 딕셔너리
            
        Returns:
            필드별 검증 오류 딕셔너리
        """
        errors = {}
        
        # 필수 필드 검증
        required_fields = ['title', 'content_type', 'content_body']
        for field in required_fields:
            if not data.get(field):
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"{field}는 필수 입력 항목입니다.")
        
        # 콘텐츠 타입 검증
        valid_content_types = ['1', '2', '3', '4', '5', '6', '7', '8']
        if data.get('content_type') and data['content_type'] not in valid_content_types:
            if 'content_type' not in errors:
                errors['content_type'] = []
            errors['content_type'].append(f"콘텐츠 타입은 {', '.join(valid_content_types)} 중 하나여야 합니다.")
        
        # 콘텐츠 길이 검증
        if data.get('content_body'):
            if len(data['content_body']) < 10:
                if 'content_body' not in errors:
                    errors['content_body'] = []
                errors['content_body'].append("콘텐츠 내용은 최소 10자 이상이어야 합니다.")
            elif len(data['content_body']) > 10000:
                if 'content_body' not in errors:
                    errors['content_body'] = []
                errors['content_body'].append("콘텐츠 내용은 10,000자를 초과할 수 없습니다.")
        
        return errors


def validate_data(data: Dict[str, Any], data_type: str) -> None:
    """
    데이터 검증 헬퍼 함수
    
    Args:
        data: 검증할 데이터
        data_type: 데이터 타입 ('announcement', 'business', 'content')
        
    Raises:
        DataValidationError: 검증 실패 시
    """
    validator = DataValidator()
    
    if data_type == 'announcement':
        errors = validator.validate_announcement_data(data)
    elif data_type == 'business':
        errors = validator.validate_business_data(data)
    elif data_type == 'content':
        errors = validator.validate_content_data(data)
    else:
        raise ValueError(f"Unknown data type: {data_type}")
    
    if errors:
        error_messages = []
        for field, field_errors in errors.items():
            for error in field_errors:
                error_messages.append(f"{field}: {error}")
        
        raise DataValidationError(
            message="데이터 검증에 실패했습니다.",
            validation_errors=error_messages
        )