"""
FastAPI endpoints for Anthropic token-based authentication setup.
Provides UI endpoints for storing tokens from `claude setup-token`.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os
from pathlib import Path


router = APIRouter()

DEFAULT_AUTH_FILE = os.path.expanduser("~/.litellm/anthropic-tokens.json")


class SetupTokenRequest(BaseModel):
    token: str
    profile_id: Optional[str] = "anthropic:manual"
    expires_days: Optional[int] = None


class SetupTokenResponse(BaseModel):
    success: bool
    profile_id: str
    message: str


def validate_anthropic_setup_token(token: str) -> Optional[str]:
    """Validate token format. Returns error message if invalid."""
    token = token.strip()

    if not token:
        return "Token cannot be empty"

    if len(token) < 20:
        return "Token too short (minimum 20 characters)"

    if any(c.isspace() for c in token):
        return "Token contains invalid whitespace"

    return None


def load_token_storage(auth_file: str = DEFAULT_AUTH_FILE) -> dict:
    """Load stored tokens from file."""
    auth_path = Path(auth_file)

    if not auth_path.exists():
        return {"profiles": {}}

    try:
        with open(auth_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load auth file: {str(e)}"
        )


def save_token_storage(data: dict, auth_file: str = DEFAULT_AUTH_FILE):
    """Save tokens to file."""
    auth_path = Path(auth_file)
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(auth_path, 'w') as f:
            json.dump(data, f, indent=2)

        # Set file permissions to 600 (owner read/write only)
        auth_path.chmod(0o600)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save auth file: {str(e)}"
        )


@router.post("/anthropic/setup-token", response_model=SetupTokenResponse)
async def setup_anthropic_token(request: SetupTokenRequest):
    """
    Store an Anthropic setup-token from `claude setup-token`.

    This provides the same functionality as OpenClaw's token setup,
    allowing users to authenticate with tokens instead of API keys.
    """
    # Validate token
    validation_error = validate_anthropic_setup_token(request.token)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Load existing storage
    storage = load_token_storage()

    # Calculate expiration if specified
    expires_ms = None
    if request.expires_days is not None:
        import time
        expires_ms = int((time.time() + (request.expires_days * 86400)) * 1000)

    # Store token
    if "profiles" not in storage:
        storage["profiles"] = {}

    storage["profiles"][request.profile_id] = {
        "type": "token",
        "provider": "anthropic",
        "token": request.token.strip(),
        **({"expires": expires_ms} if expires_ms else {})
    }

    # Save to file
    save_token_storage(storage)

    return SetupTokenResponse(
        success=True,
        profile_id=request.profile_id,
        message=f"Token stored successfully: {request.profile_id}"
    )


@router.get("/anthropic/token-status")
async def get_token_status():
    """
    Check if an Anthropic token is configured.

    Returns:
        - has_token: Whether a valid token is stored
        - profile_id: The profile ID if token exists
        - expired: Whether the token is expired (if expiration is set)
    """
    try:
        storage = load_token_storage()
        profiles = storage.get("profiles", {})

        # Look for anthropic token profiles
        anthropic_profiles = {
            k: v for k, v in profiles.items()
            if v.get("provider") == "anthropic" and v.get("type") == "token"
        }

        if not anthropic_profiles:
            return {
                "has_token": False,
                "profile_id": None,
                "expired": None
            }

        # Return info about the first profile
        profile_id = list(anthropic_profiles.keys())[0]
        profile = anthropic_profiles[profile_id]

        # Check expiration
        expired = False
        if "expires" in profile:
            import time
            expired = time.time() * 1000 > profile["expires"]

        return {
            "has_token": True,
            "profile_id": profile_id,
            "expired": expired
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check token status: {str(e)}"
        )


@router.delete("/anthropic/setup-token/{profile_id}")
async def delete_anthropic_token(profile_id: str):
    """Remove a stored Anthropic token."""
    try:
        storage = load_token_storage()
        profiles = storage.get("profiles", {})

        if profile_id not in profiles:
            raise HTTPException(
                status_code=404,
                detail=f"Profile not found: {profile_id}"
            )

        # Remove profile
        del profiles[profile_id]
        save_token_storage(storage)

        return {
            "success": True,
            "message": f"Token removed: {profile_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete token: {str(e)}"
        )
