"""
Concrete authentication and request strategies for different API types.

Implements Strategy pattern for flexible API integration.
"""

from typing import Dict, Any, Optional
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode

from ...core.interfaces.base_api_client import AuthenticationStrategy


class GovernmentAPIKeyStrategy(AuthenticationStrategy):
    """
    Korean Government Open Data Portal API key authentication.
    
    Handles the specific format used by data.go.kr APIs.
    """
    
    def __init__(self, api_key: str, encoding_key: Optional[str] = None):
        self.api_key = api_key
        self.encoding_key = encoding_key  # For encoded/decoded key handling
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply government API key authentication"""
        # Use decoded key if encoding key is provided
        auth_key = self.encoding_key or self.api_key
        
        # Add serviceKey to params dictionary, not directly to request_params
        if "params" not in request_params:
            request_params["params"] = {}
        request_params["params"]["serviceKey"] = auth_key
        return request_params


class OAuthBearerStrategy(AuthenticationStrategy):
    """OAuth Bearer token authentication strategy"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply OAuth bearer token authentication"""
        headers = request_params.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        request_params["headers"] = headers
        return request_params


class BasicAuthStrategy(AuthenticationStrategy):
    """Basic authentication strategy"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply basic authentication"""
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = request_params.get("headers", {})
        headers["Authorization"] = f"Basic {encoded_credentials}"
        request_params["headers"] = headers
        return request_params


class HMACSignatureStrategy(AuthenticationStrategy):
    """
    HMAC signature authentication strategy.
    
    Used for APIs requiring request signing.
    """
    
    def __init__(self, access_key: str, secret_key: str, signature_method: str = "HmacSHA256"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.signature_method = signature_method
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply HMAC signature authentication"""
        # Add timestamp
        timestamp = str(int(time.time() * 1000))
        
        # Build signature base string
        method = request_params.get("method", "GET")
        url = request_params.get("url", "")
        params = request_params.get("params", {})
        
        # Add auth parameters
        params.update({
            "AccessKey": self.access_key,
            "SignatureMethod": self.signature_method,
            "Timestamp": timestamp,
            "SignatureVersion": "2"
        })
        
        # Create signature
        signature = self._generate_signature(method, url, params)
        params["Signature"] = signature
        
        request_params["params"] = params
        return request_params
    
    def _generate_signature(self, method: str, url: str, params: Dict[str, Any]) -> str:
        """Generate HMAC signature"""
        # Sort parameters
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # Create string to sign
        string_to_sign = f"{method}\n{url}\n{query_string}"
        
        # Generate signature
        signature = hmac.new(
            self.secret_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()


class CustomHeaderStrategy(AuthenticationStrategy):
    """Custom header authentication strategy"""
    
    def __init__(self, headers: Dict[str, str]):
        self.custom_headers = headers
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom headers"""
        headers = request_params.get("headers", {})
        headers.update(self.custom_headers)
        request_params["headers"] = headers
        return request_params


class NoAuthStrategy(AuthenticationStrategy):
    """No authentication strategy for public APIs"""
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """No authentication needed"""
        return request_params


# Request processing strategies
class RequestStrategy:
    """Base class for request processing strategies"""
    
    def process_request(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request parameters"""
        return request_params


class JSONRequestStrategy(RequestStrategy):
    """JSON request processing strategy"""
    
    def process_request(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request for JSON APIs"""
        headers = request_params.get("headers", {})
        headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        request_params["headers"] = headers
        return request_params


class XMLRequestStrategy(RequestStrategy):
    """XML request processing strategy"""
    
    def process_request(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request for XML APIs"""
        headers = request_params.get("headers", {})
        headers.update({
            "Content-Type": "application/xml",
            "Accept": "application/xml"
        })
        request_params["headers"] = headers
        return request_params


class FormDataRequestStrategy(RequestStrategy):
    """Form data request processing strategy"""
    
    def process_request(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request for form data APIs"""
        headers = request_params.get("headers", {})
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        request_params["headers"] = headers
        return request_params


# Error handling strategies
class ErrorHandlingStrategy:
    """Base class for error handling strategies"""
    
    def should_retry(self, status_code: int, attempt: int, max_retries: int) -> bool:
        """Determine if request should be retried"""
        return False
    
    def get_retry_delay(self, attempt: int) -> float:
        """Get delay before retry"""
        return 1.0


class StandardErrorHandlingStrategy(ErrorHandlingStrategy):
    """Standard error handling with exponential backoff"""
    
    def should_retry(self, status_code: int, attempt: int, max_retries: int) -> bool:
        """Retry on 5xx errors and specific 4xx errors"""
        if attempt >= max_retries:
            return False
        
        # Retry on server errors
        if 500 <= status_code < 600:
            return True
        
        # Retry on specific client errors
        if status_code in [408, 429]:  # Timeout, Too Many Requests
            return True
        
        return False
    
    def get_retry_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter"""
        import random
        base_delay = 2 ** attempt
        jitter = random.uniform(0.1, 0.3)
        return base_delay + jitter


class AggressiveRetryStrategy(ErrorHandlingStrategy):
    """Aggressive retry strategy for unreliable APIs"""
    
    def should_retry(self, status_code: int, attempt: int, max_retries: int) -> bool:
        """Retry on most errors except auth failures"""
        if attempt >= max_retries:
            return False
        
        # Don't retry on auth errors
        if status_code in [401, 403]:
            return False
        
        # Retry on most other errors
        return status_code >= 400
    
    def get_retry_delay(self, attempt: int) -> float:
        """Linear backoff for faster retries"""
        return attempt * 0.5


class NoRetryStrategy(ErrorHandlingStrategy):
    """No retry strategy"""
    
    def should_retry(self, status_code: int, attempt: int, max_retries: int) -> bool:
        """Never retry"""
        return False