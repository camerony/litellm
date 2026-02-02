
import json
import time
import os
import fcntl
import httpx
import uuid
import asyncio
from typing import Optional, Union, Callable, Any, List, Dict
from ...base import BaseLLM
from litellm import LlmProviders, verbose_logger
import litellm

class AntigravityError(Exception):
    def __init__(self, status_code, message, headers=None):
        self.status_code = status_code
        self.message = message
        self.headers = headers
        super().__init__(self.message)

class SimpleFileLock:
    """A simple file lock using fcntl (Linux/Unix only)."""
    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self.fp = None

    def __enter__(self):
        self.fp = open(self.lock_file, 'w+')
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, _type, value, traceback):
        if self.fp:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            self.fp.close()

class GoogleAntigravityChatCompletion(BaseLLM):
    def __init__(self) -> None:
        super().__init__()
        self.auth_file_path = os.getenv("ANTIGRAVITY_AUTH_FILE", "auth-profiles.json")
        self.token_url = "https://oauth2.googleapis.com/token"
        
        # Endpoints
        self.primary_endpoint = "https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse"
        self.fallback_endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

    def _get_credentials_from_file(self):
        if not os.path.exists(self.auth_file_path):
             # Fallback to looking in current directory if not found and not absolute
             if not os.path.isabs(self.auth_file_path):
                 cwd_path = os.path.join(os.getcwd(), self.auth_file_path)
                 if os.path.exists(cwd_path):
                     return cwd_path, self._read_json(cwd_path)
             raise FileNotFoundError(f"Auth profiles file not found at {self.auth_file_path}")
        
        return self.auth_file_path, self._read_json(self.auth_file_path)

    def _read_json(self, path):
        with open(path, 'r') as f:
            return json.load(f)
            
    def _write_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _refresh_access_token(self, profile_key: str, profile_data: dict, lock_path: str):
        """
        Refreshes access token if expired, using file lock.
        Returns the valid access token.
        """
        # Double check expiry with a buffer (5 mins)
        now_ms = int(time.time() * 1000)
        expires_at = profile_data.get("expires", 0)
        
        if now_ms < (expires_at - 5 * 60 * 1000):
            return profile_data.get("access")

        with SimpleFileLock(lock_path):
            # Re-read file to check if another process refreshed it
            path, full_data = self._get_credentials_from_file()
            profile_data = full_data["profiles"].get(profile_key)
            if not profile_data:
                raise ValueError(f"Profile {profile_key} not found during refresh")
            
            # Check expiry again
            expires_at = profile_data.get("expires", 0)
            if now_ms < (expires_at - 5 * 60 * 1000):
                return profile_data.get("access")
                
            # Actually refresh
            refresh_token = profile_data.get("refresh")
            if not refresh_token:
                raise ValueError("No refresh token available")
                
            # Default constants (from user request)
            # Users can override these via env vars if needed, but defaults are handy
            client_id = os.getenv("ANTIGRAVITY_CLIENT_ID", "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com")
            client_secret = os.getenv("ANTIGRAVITY_CLIENT_SECRET", "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")
            
            response = httpx.post(
                self.token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            )
            response.raise_for_status()
            new_tokens = response.json()
            
            access_token = new_tokens["access_token"]
            expires_in_s = new_tokens.get("expires_in", 3599)
            new_expires_at = int(time.time() * 1000) + (expires_in_s * 1000)
            
            # Update data
            profile_data["access"] = access_token
            profile_data["expires"] = new_expires_at
            
            full_data["profiles"][profile_key] = profile_data
            self._write_json(path, full_data)
            
            return access_token

    def _get_access_token(self, litellm_params: dict):
        """
        Retrieves access token, handling auto-refresh.
        Expects 'auth_profile_email' or similar in params, or iterates to find first valid oauth profile?
        User provided `auth-profiles.json` structure.
        """
        # User prompt implies we can specify the "auth" block in litellm_params.
        # model_list:
        #   litellm_params:
        #     auth: { type: oauth, provider: google-antigravity, refresh_token: ... }
        
        # But for full automation with the file, we might just look up by a key.
        # Let's support both reading from the file based on a key (e.g. email) or using provided params.
        
        # Assuming we use the file approach as primary as requested ("Creds Storage").
        
        path, full_data = self._get_credentials_from_file()
        
        # Determine which profile to use
        # 1. Try to find a profile matching the provider 'google-antigravity'
        target_profile_key = None
        for key, p in full_data.get("profiles", {}).items():
            if p.get("provider") == "google-antigravity":
                 target_profile_key = key
                 break
        
        # If specific email requested, could filter by that. For now, take first matching provider.
        if not target_profile_key:
             # Just use access token from params if passed directly?
             return litellm_params.get("api_key") # Fallback

        lock_path = path + ".lock"
        profile_data = full_data["profiles"][target_profile_key]
        return self._refresh_access_token(target_profile_key, profile_data, lock_path)
    
    def _construct_body(self, model: str, messages: list, optional_params: dict, litellm_params: dict):
        # Construct the specialized body
        # Need to map messages to "contents" format
        # This is likely Gemini/Vertex style format.
        
        # Basic mapping - this might need more robust handling logic from vertex implementation
        contents = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            
            # Map roles
            if role == "user":
                parts = [{"text": content}]
                contents.append({"role": "user", "parts": parts})
            elif role == "assistant":
                parts = [{"text": content}]
                contents.append({"role": "model", "parts": parts})
            elif role == "system":
                # System instructions are separate in the body schema provided
                # "systemInstruction": {"parts": [{"text": "..."}]}
                # handled outside loop
                pass

        # Extract system prompt
        system_instruction = None
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        if system_msg:
             system_instruction = {"parts": [{"text": system_msg["content"]}]}

        # Project ID - optional for Antigravity
        project_id = litellm_params.get("project_id") or optional_params.get("project_id")
        if not project_id:
             # Try to find in auth file
             try:
                 _, data = self._get_credentials_from_file()
                 for p in data.get("profiles", {}).values():
                     if p.get("provider") == "google-antigravity":
                         project_id = p.get("projectId")
                         if project_id and project_id != "default":
                             break
                         project_id = None
             except:
                 pass

        thinking_config = None
        # Handle thinking config mapping if present in optional_params
        # User defined: thinkingConfig: {"includeThoughts": true, "thinkingBudget": 4096}
        if "thinking" in optional_params: # e.g. from litellm pass through
             thinking_config = optional_params["thinking"]
             # Ensure includeThoughts is true
             if isinstance(thinking_config, dict):
                 thinking_config["includeThoughts"] = True

        # Support litellm 'reasoning_effort' param -> thinkingLevel
        # 'low', 'medium', 'high' -> 'LOW', 'MEDIUM', 'HIGH'
        reasoning_effort = optional_params.get("reasoning_effort")
        if reasoning_effort:
            if not thinking_config:
                thinking_config = {"includeThoughts": True}
            
            # Map common values to uppercase for API
            thinking_config["thinkingLevel"] = str(reasoning_effort).upper() 
            
        # Model name heuristic matching (e.g. gemini-3-pro-high)
        # Map model variants to actual API model names
        base_model = model
        if not thinking_config and model:
            model_lower = model.lower()
            level = None

            # Extract thinking level from suffix
            if model_lower.endswith("-high"):
                level = "HIGH"
                base_model = model[:-5]  # Strip "-high"
            elif model_lower.endswith("-medium"):
                level = "MEDIUM"
                base_model = model[:-7]  # Strip "-medium"
            elif model_lower.endswith("-low"):
                level = "LOW"
                base_model = model[:-4]  # Strip "-low"
            elif model_lower.endswith("-lo"):
                level = "LOW"
                base_model = model[:-3]  # Strip "-lo"

            # CRITICAL: Map gemini-3-pro-* to gemini-3-flash
            # There is NO gemini-3-pro model on Google's API
            # gemini-3-pro-high -> gemini-3-flash + HIGH thinking
            # gemini-3-pro-low -> gemini-3-flash + LOW thinking
            if "gemini-3-pro" in base_model.lower():
                base_model = "gemini-3-flash"

            if level:
                thinking_config = {"includeThoughts": True, "thinkingLevel": level} 

        generation_config = {
             "maxOutputTokens": optional_params.get("max_tokens", 8192),
             "temperature": optional_params.get("temperature"),
             "topP": optional_params.get("top_p"),
        }
        
        if thinking_config:
            generation_config["thinkingConfig"] = thinking_config
            
        # Filter None
        generation_config = {k: v for k, v in generation_config.items() if v is not None}

        body = {
            "model": base_model,  # Use base model without thinking suffix
            "request": {
                "contents": contents,
                "generationConfig": generation_config,
                # "tools": ... (TODO: support tools)
            },
            "userAgent": "antigravity",
            "requestType": "agent",
            "requestId": f"agent-{int(time.time()*1000)}-{uuid.uuid4()}"
        }
        
        # Only include project if set
        if project_id:
            body["project"] = project_id
        
        if system_instruction:
            body["request"]["systemInstruction"] = system_instruction
            
        return body

    async def acompletion(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: Any, # ModelResponse
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        litellm_params: dict,
        logger_fn=None,
        headers={},
        timeout=None,
        client=None  # AsyncHTTPHandler
    ):
        # Auth
        try:
            access_token = self._get_access_token(litellm_params)
        except Exception as e:
            # Fallback to provided api_key if any (static)
            if api_key:
                access_token = api_key
            else:
                raise e

        # Endpoints - try sandbox first, then production (like OpenClaw)
        endpoints = [
            "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse",
            "https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse",
        ]
        
        # Headers
        headers = headers or {}
        headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "antigravity/1.15.8 darwin/arm64",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": json.dumps({
                "ideType": "IDE_UNSPECIFIED",
                "platform": "PLATFORM_UNSPECIFIED",
                "pluginType": "GEMINI"
            })
        })
        
        # Add thinking header for Claude thinking models
        if "thinking" in model or "claude" in model:
             headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"

        data = self._construct_body(model, messages, optional_params, litellm_params)

        if client is None:
             client = litellm.client_session or httpx.AsyncClient()

        # Retry logic with endpoint fallback
        last_error = None
        max_retries = 3
        
        for attempt in range(max_retries):
            endpoint = endpoints[min(attempt, len(endpoints) - 1)]
            
            try:
                response = await client.post(endpoint, json=data, headers=headers, timeout=timeout)
                response.raise_for_status()
                break  # Success
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                
                # On 404 (endpoint/model not found), 429 (rate limit), or 5xx (server error), retry with next endpoint
                if status_code == 404 or status_code == 429 or status_code >= 500:
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        await asyncio.sleep((2 ** attempt) * 0.5)
                        continue
                
                raise AntigravityError(status_code=status_code, message=e.response.text)
        else:
            # All retries exhausted
            if last_error:
                raise AntigravityError(status_code=last_error.response.status_code, message=last_error.response.text)


        # Handle SSE Response
        # User defined format:
        # data: {"response": {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}}
        
        async def _stream_generator():
            async for line in response.aiter_lines():
                if not line or line.strip() == "":
                    continue
                
                if line.startswith("data: "):
                     json_str = line[6:]
                     try:
                         data = json.loads(json_str)
                         # Transform to LiteLLM ModelResponse info
                         # Extract text chunks
                         candidates = data.get("response", {}).get("candidates", [])
                         for candidate in candidates:
                             parts = candidate.get("content", {}).get("parts", [])
                             for part in parts:
                                 text = part.get("text")
                                 if text:
                                     chunk = {
                                         "choices": [{"delta": {"content": text}}],
                                         "created": int(time.time()),
                                         "model": model,
                                         "object": "chat.completion.chunk"
                                     }
                                     yield chunk
                                 
                                 # Thoughts?
                                 if "thoughtSignature" in part:
                                     # handle signature?
                                     pass
                     except json.JSONDecodeError:
                         continue

        # Handle streaming vs non-streaming
        if optional_params.get("stream", False):
            return _stream_generator()
        else:
            # Non-streaming: collect all chunks and return complete response
            full_text = ""
            usage_metadata = None

            # Collect both text and usage from SSE stream
            async for line in response.aiter_lines():
                if not line or line.strip() == "":
                    continue

                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])

                        # Extract text
                        candidates = data.get("response", {}).get("candidates", [])
                        for candidate in candidates:
                            parts = candidate.get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text")
                                if text:
                                    full_text += text

                        # Extract usage (usually in final event)
                        usage = data.get("response", {}).get("usageMetadata")
                        if usage:
                            usage_metadata = usage

                    except json.JSONDecodeError:
                        continue

            # Build complete response
            from litellm.types.utils import ModelResponse, Choices, Message, Usage

            model_response = ModelResponse(
                id=f"antigravity-{int(time.time()*1000)}",
                created=int(time.time()),
                model=model,
                object="chat.completion",
                choices=[
                    Choices(
                        finish_reason="stop",
                        index=0,
                        message=Message(
                            content=full_text,
                            role="assistant"
                        )
                    )
                ]
            )

            # Add usage if available
            if usage_metadata:
                model_response.usage = Usage(
                    prompt_tokens=usage_metadata.get("promptTokenCount", 0),
                    completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
                    total_tokens=usage_metadata.get("totalTokenCount", 0)
                )

            return model_response

    def completion(self, *args, **kwargs):
        # Sync version - run the async version in an event loop
        import asyncio
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # We're already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.acompletion(*args, **kwargs))
                return future.result()
        else:
            return asyncio.run(self.acompletion(*args, **kwargs))


