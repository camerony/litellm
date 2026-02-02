"""
Google Antigravity OAuth endpoints for Web UI integration.

Provides OAuth 2.0 PKCE flow for authenticating with Google to access
the Antigravity API (cloudcode-pa.googleapis.com).
"""

import os
import json
import time
import secrets
import hashlib
import base64
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx

from litellm._logging import verbose_proxy_logger

router = APIRouter()

# OAuth Configuration
DEFAULT_CLIENT_ID = os.getenv(
    "ANTIGRAVITY_CLIENT_ID",
    "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
)
DEFAULT_CLIENT_SECRET = os.getenv(
    "ANTIGRAVITY_CLIENT_SECRET",
    "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"
)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email https://www.googleapis.com/auth/cloud-platform"

# In-memory store for PKCE verifiers (use Redis in production)
_pkce_store: dict = {}


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
    return verifier, challenge


@router.get("/init")
async def oauth_init(request: Request):
    """
    Initialize OAuth flow. Redirects user to Google consent screen.
    
    Query params:
    - redirect_uri: Optional custom redirect URI (defaults to proxy callback)
    """
    # Determine callback URL
    # Use X-Forwarded headers if behind a proxy
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    callback_url = f"{scheme}://{host}/auth/google_antigravity/callback"
    
    # Generate PKCE
    verifier, challenge = _generate_pkce_pair()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(16)
    
    # Store verifier (keyed by state)
    _pkce_store[state] = {
        "verifier": verifier,
        "created_at": time.time(),
    }
    
    # Clean up old entries (older than 10 minutes)
    current_time = time.time()
    expired_states = [s for s, v in _pkce_store.items() if current_time - v["created_at"] > 600]
    for s in expired_states:
        del _pkce_store[s]
    
    # Build authorization URL
    params = {
        "client_id": DEFAULT_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",  # Force refresh token
        "state": state,
    }
    
    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    verbose_proxy_logger.info(f"[Antigravity OAuth] Redirecting to Google OAuth: state={state}")
    
    return RedirectResponse(url=auth_url)


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    OAuth callback. Exchanges code for tokens and stores credential.
    Returns HTML that posts result to parent window.
    """
    # Handle errors from Google
    if error:
        return _render_callback_html(success=False, error=error)
    
    if not code or not state:
        return _render_callback_html(success=False, error="Missing code or state parameter")
    
    # Retrieve PKCE verifier
    pkce_data = _pkce_store.pop(state, None)
    if not pkce_data:
        return _render_callback_html(success=False, error="Invalid or expired state")
    
    verifier = pkce_data["verifier"]
    
    # Determine callback URL (same as init)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    callback_url = f"{scheme}://{host}/auth/google_antigravity/callback"
    
    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "client_id": DEFAULT_CLIENT_ID,
                    "client_secret": DEFAULT_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_url,
                    "code_verifier": verifier,
                },
            )
            
            if response.status_code != 200:
                verbose_proxy_logger.error(f"[Antigravity OAuth] Token exchange failed: {response.text}")
                return _render_callback_html(success=False, error="Token exchange failed")
            
            tokens = response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3599)
            
            # Get user info
            userinfo_response = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            email = "unknown"
            if userinfo_response.status_code == 200:
                email = userinfo_response.json().get("email", "unknown")
            
            # Get Cloud Code Assist project ID
            project_id = None
            try:
                cca_response = await client.post(
                    "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={},
                )
                if cca_response.status_code == 200:
                    cca_data = cca_response.json()
                    # Handle both formats: string or object with id
                    project_data = cca_data.get("cloudaicompanionProject")
                    if isinstance(project_data, str):
                        project_id = project_data
                    elif isinstance(project_data, dict):
                        project_id = project_data.get("id")
                    verbose_proxy_logger.info(f"[Antigravity OAuth] Got projectId: {project_id}")
            except Exception as e:
                verbose_proxy_logger.warning(f"[Antigravity OAuth] Failed to get projectId: {e}")
    
    except Exception as e:
        verbose_proxy_logger.exception(f"[Antigravity OAuth] Error during token exchange: {e}")
        return _render_callback_html(success=False, error=str(e))
    
    # Store credential
    expires_at = int(time.time() * 1000) + (expires_in * 1000)
    credential_data = {
        "type": "oauth",
        "provider": "google_antigravity",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires_at,
        "email": email,
    }
    
    # Store in auth-profiles.json (can be extended to use database)
    auth_file = os.getenv("ANTIGRAVITY_AUTH_FILE", "auth-profiles.json")
    try:
        full_data = {"profiles": {}}
        if os.path.exists(auth_file):
            with open(auth_file, "r") as f:
                full_data = json.load(f)
        
        # Use 'access' and 'refresh' keys to match existing format
        full_data["profiles"][email] = {
            "type": "oauth",
            "provider": "google-antigravity",
            "access": access_token,
            "refresh": refresh_token,
            "expires": expires_at,
            "email": email,
            "projectId": project_id,  # From loadCodeAssist API
        }
        
        with open(auth_file, "w") as f:
            json.dump(full_data, f, indent=2)
        
        verbose_proxy_logger.info(f"[Antigravity OAuth] Stored credential for {email}")
    
    except Exception as e:
        verbose_proxy_logger.exception(f"[Antigravity OAuth] Error storing credential: {e}")
        return _render_callback_html(success=False, error=f"Failed to store credential: {e}")
    
    return _render_callback_html(success=True, email=email)


def _render_callback_html(success: bool, email: str = "", error: str = "") -> str:
    """Render HTML that posts result to parent window."""
    if success:
        message = json.dumps({"success": True, "email": email, "provider": "google_antigravity"})
    else:
        message = json.dumps({"success": False, "error": error})
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Authentication {'Complete' if success else 'Failed'}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .card {{
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }}
        h1 {{
            color: {'#10b981' if success else '#ef4444'};
            margin-bottom: 16px;
        }}
        p {{
            color: #6b7280;
            margin-bottom: 24px;
        }}
        .email {{
            font-weight: 600;
            color: #1f2937;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{'✓ Authentication Complete' if success else '✗ Authentication Failed'}</h1>
        <p>
            {'Authenticated as <span class="email">' + email + '</span>' if success else error}
        </p>
        <p>You can close this window.</p>
    </div>
    <script>
        if (window.opener) {{
            window.opener.postMessage({message}, '*');
        }}
        setTimeout(() => window.close(), 2000);
    </script>
</body>
</html>
"""
