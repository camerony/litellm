
import os
import sys
import json
import time
import hashlib
import base64
import secrets
import threading
import webbrowser
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import httpx

# Constants
DEFAULT_CLIENT_ID = os.getenv("ANTIGRAVITY_CLIENT_ID", "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com")
DEFAULT_CLIENT_SECRET = os.getenv("ANTIGRAVITY_CLIENT_SECRET", "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")
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "openid email https://www.googleapis.com/auth/cloud-platform"
REDIRECT_URI_TEMPLATE = "http://localhost:{port}"

logger = logging.getLogger(__name__)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress server logs

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        
        if "code" in query:
            self.server.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login Successful</h1><p>You can close this window and return to the terminal.</p><script>window.close()</script></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code found.")

def _generate_pkce_pair():
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
    return verifier, challenge

def login(client_id=DEFAULT_CLIENT_ID, client_secret=DEFAULT_CLIENT_SECRET, auth_file="auth-profiles.json"):
    """
    Initiates the OAuth2 PKCE flow for Google Antigravity.
    """
    print("Starting Google Antigravity Login...")
    
    # 1. Start Local Server
    server = HTTPServer(("localhost", 0), OAuthCallbackHandler)
    port = server.server_port
    redirect_uri = REDIRECT_URI_TEMPLATE.format(port=port)
    
    # 2. Generate PKCE
    verifier, challenge = _generate_pkce_pair()
    
    # 3. Construct URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent" # Force refresh token
    }
    url_params = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{AUTH_URL}?{url_params}"
    
    print(f"\nPlease visit the following URL to authorize:\n{auth_url}\n")
    
    # 4. Open Browser
    try:
        webbrowser.open(auth_url)
    except:
        pass

    # 5. Wait for callback
    print("Waiting for callback...", end="", flush=True)
    server.auth_code = None
    while server.auth_code is None:
        server.handle_request()
        print(".", end="", flush=True)
    print("\nCallback received!")
    server.server_close()
    
    # 6. Exchange Code
    print("Exchanging code for tokens...")
    response = httpx.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": server.auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": verifier
    })
    
    if response.status_code != 200:
        print(f"Error exchanging token: {response.text}")
        return
    
    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token") # Might be None if user re-auths without prompt=consent
    expires_in = tokens.get("expires_in", 3599)
    # Get email and project (minimal check)
    # We can get email from id_token if present, or userinfo endpoint
    
    email = "unknown"
    project_id = "unknown"
    
    # decode id_token roughly to get email
    id_token = tokens.get("id_token")
    if id_token:
        try:
            # Simple decode without strict verification just to get email for the profile key
            # (Security comes from the TLS channel and Google signature verification in real apps, 
            # here we just need the key name).
            parts = id_token.split(".")
            if len(parts) > 1:
                import json
                # Pad base64
                payload = parts[1]
                padded = payload + '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(padded)
                claims = json.loads(decoded)
                email = claims.get("email", email)
        except Exception as e:
            print(f"Warning: Could not decode id_token: {e}")

    # For Antigravity, projectId is often separate credential or default.
    # We'll default to placeholder or ask user?
    # OpenClaw stores projectId. We can try to query resource manager but that requires enabling API.
    # Let's prompt user for Project ID if we can't find it? 
    # Or just store "default" and let the user edit.
    
    # Try to fetch user info to confirm email/identity if id_token failed
    if email == "unknown":
         try:
             userinfo = httpx.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
             if userinfo.status_code == 200:
                 email = userinfo.json().get("email", email)
         except: pass

    # Fetch Cloud Code Assist project ID from Google
    print("Fetching Cloud Code Assist project ID...")
    project_id = None
    try:
        cca_response = httpx.post(
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
            print(f"Got project ID: {project_id}")
        else:
            print(f"Warning: Could not fetch project ID (status {cca_response.status_code})")
    except Exception as e:
        print(f"Warning: Could not fetch project ID: {e}")
    
    if not project_id:
        # Fallback to asking user
        user_project_id = input("Enter Google Cloud Project ID: ").strip()
        if user_project_id:
            project_id = user_project_id
        else:
            print("Warning: No project ID set. Requests may fail.")
            project_id = None
    
    # 7. Write to file
    expires_at = int(time.time() * 1000) + (expires_in * 1000)
    
    profile_data = {
        "type": "oauth",
        "provider": "google-antigravity",
        "access": access_token,
        "refresh": refresh_token,
        "expires": expires_at,
        "email": email,
        "projectId": project_id
    }
    
    full_data = {"profiles": {}}
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r") as f:
                full_data = json.load(f)
        except: pass
    
    full_data["profiles"][email] = profile_data
    
    with open(auth_file, "w") as f:
        json.dump(full_data, f, indent=2)
        
    print(f"Success! Credentials saved to {os.path.abspath(auth_file)}")
    print("You can now start litellm proxy.")

if __name__ == "__main__":
    login()
