"""
Google OAuth 2.0 Client for handling Google authentication flow.

Implements authorization code flow, token exchange, and user profile retrieval.
"""

import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import secrets
from datetime import datetime, timedelta

from ...core.config import settings
from ...core.security import security


class GoogleOAuthClient:
    """Google OAuth 2.0 client for authentication"""
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.scope = settings.google_scope
        
        # Google OAuth 2.0 endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.tokeninfo_url = "https://oauth2.googleapis.com/tokeninfo"
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def get_authorization_url(self, state: Optional[str] = None, redirect_url: Optional[str] = None) -> Dict[str, str]:
        """
        Generate Google OAuth authorization URL with CSRF protection
        
        Args:
            state: Optional state parameter for additional CSRF protection
            redirect_url: Optional URL to redirect after authentication
            
        Returns:
            Dict containing authorization URL and state token
        """
        if not self.client_id:
            raise ValueError("Google Client ID not configured")
        
        # Generate secure state token
        if state is None:
            state = security.generate_state_token()
        
        # Store state data in Redis for verification
        state_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "redirect_url": redirect_url
        }
        security.store_oauth_state(state, state_data, expire_seconds=600)  # 10 minutes
        
        # Build authorization URL parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent"  # Force consent screen to get refresh token
        }
        
        authorization_url = f"{self.auth_url}?{urlencode(params)}"
        
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token and user info
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF verification
            
        Returns:
            Dict containing access token, refresh token, and user info
        """
        # Verify state parameter
        state_data = security.get_oauth_state(state)
        if not state_data:
            raise ValueError("Invalid or expired state parameter")
        
        # Exchange code for tokens
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        try:
            # Get access token
            async with self.http_client as client:
                token_response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                token_response.raise_for_status()
                tokens = token_response.json()
            
            # Get user info using access token
            user_info = await self._get_user_info(tokens["access_token"])
            if not user_info:
                return None
            
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in", 3600),
                "user_info": user_info,
                "state_data": state_data
            }
        
        except httpx.HTTPStatusError as e:
            print(f"HTTP error during token exchange: {e}")
            return None
        except Exception as e:
            print(f"Error during token exchange: {e}")
            return None
    
    async def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information from Google API
        
        Args:
            access_token: Google access token
            
        Returns:
            User profile information
        """
        try:
            async with self.http_client as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(self.userinfo_url, headers=headers)
                response.raise_for_status()
                user_info = response.json()
            
            # Validate required fields
            required_fields = ["id", "email", "name"]
            if not all(field in user_info for field in required_fields):
                print(f"Missing required fields in user info: {user_info}")
                return None
            
            return {
                "external_id": user_info["id"],
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False)
            }
        
        except httpx.HTTPStatusError as e:
            print(f"HTTP error getting user info: {e}")
            return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    async def verify_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google access token and get basic info
        
        Args:
            access_token: Google access token to verify
            
        Returns:
            Token info if valid, None if invalid
        """
        try:
            async with self.http_client as client:
                params = {"access_token": access_token}
                response = await client.get(self.tokeninfo_url, params=params)
                response.raise_for_status()
                token_info = response.json()
            
            # Verify token belongs to our app
            if token_info.get("aud") != self.client_id:
                print("Token does not belong to this application")
                return None
            
            # Check if token is expired
            expires_in = token_info.get("expires_in", 0)
            if expires_in <= 0:
                print("Token has expired")
                return None
            
            return token_info
        
        except httpx.HTTPStatusError as e:
            print(f"HTTP error verifying token: {e}")
            return None
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh Google access token using refresh token
        
        Args:
            refresh_token: Google refresh token
            
        Returns:
            New token information
        """
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            async with self.http_client as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                tokens = response.json()
            
            return {
                "access_token": tokens["access_token"],
                "expires_in": tokens.get("expires_in", 3600),
                "refresh_token": tokens.get("refresh_token", refresh_token)  # May be same or new
            }
        
        except httpx.HTTPStatusError as e:
            print(f"HTTP error refreshing token: {e}")
            return None
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke Google access or refresh token
        
        Args:
            token: Access or refresh token to revoke
            
        Returns:
            True if revocation successful
        """
        try:
            async with self.http_client as client:
                params = {"token": token}
                response = await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params=params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                # Google returns 200 for successful revocation
                return response.status_code == 200
        
        except Exception as e:
            print(f"Error revoking token: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Global Google OAuth client instance
google_oauth_client = GoogleOAuthClient()