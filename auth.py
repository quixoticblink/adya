import os
import streamlit as st
import google_auth_oauthlib.flow
import requests
from typing import Optional, Dict, Any

# Constants
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

def get_google_auth_config() -> Dict[str, Any]:
    """Retrieves Google Auth config from Streamlit secrets."""
    try:
        return st.secrets["google_auth"]
    except KeyError:
        return {}

def login_button():
    """Does nothing, just a placeholder. The actual login is triggered by the URL."""
    # This function is kept for structural compatibility if needed, 
    # but the real work is done by generating the authorization URL.
    pass

def get_login_url() -> str:
    """Generates the Google OAuth login URL."""
    config = get_google_auth_config()
    client_config = {
        "web": {
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email", 
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_uri=config.get("redirect_uri", "http://localhost:8501")
    )
    
    authorization_url, _ = flow.authorization_url(prompt="consent")
    return authorization_url

def exchange_code_for_user(code: str) -> Optional[Dict[str, Any]]:
    """Exchanges an authorization code for user info."""
    config = get_google_auth_config()
    client_config = {
        "web": {
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            redirect_uri=config.get("redirect_uri", "http://localhost:8501")
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        response = requests.get(
            user_info_endpoint,
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
        return response.json()
        
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None
