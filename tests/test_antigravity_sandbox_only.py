"""
Test using ONLY the Sandbox endpoint (which works!).
"""

import os
import sys
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_model_sandbox_only(model_name: str, thinking_level: str = None):
    """Test a model using ONLY the sandbox endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    if thinking_level:
        print(f"Thinking Level: {thinking_level}")
    print(f"{'='*60}")

    handler = GoogleAntigravityChatCompletion()

    # Get access token
    access_token = handler._get_access_token({})
    print(f"Token: {access_token[:30]}...")

    # Get project ID
    auth_file_path, auth_data = handler._get_credentials_from_file()
    profiles = auth_data.get("profiles", {})
    project_id = None
    for profile in profiles.values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    # Prepare request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "User-Agent": "antigravity/1.15.8 darwin/arm64",
        "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
        "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
    }

    # Build generation config
    generation_config = {
        "maxOutputTokens": 100,
        "temperature": 1.0
    }

    if thinking_level:
        generation_config["thinkingConfig"] = {
            "thinkingLevel": thinking_level,
            "includeThoughts": True
        }

    body = {
        "model": model_name,
        "request": {
            "contents": [{
                "role": "user",
                "parts": [{"text": "Say hello in one word"}]
            }],
            "generationConfig": generation_config
        },
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": f"test-{int(time.time()*1000)}"
    }

    if project_id:
        body["project"] = project_id

    # Use ONLY sandbox endpoint
    endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"[{time.strftime('%H:%M:%S')}] Sending request to SANDBOX...")
            response = await client.post(endpoint, json=body, headers=headers)

            if response.status_code == 200:
                print(f"[{time.strftime('%H:%M:%S')}] ✅ 200 OK!")

                # Parse SSE response
                lines = response.text.strip().split('\n')
                full_text = ""

                for line in lines:
                    if line.startswith('data: '):
                        try:
                            import json
                            data = json.loads(line[6:])
                            candidates = data.get("response", {}).get("candidates", [])

                            for candidate in candidates:
                                parts = candidate.get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        full_text += text

                            # Show usage metadata
                            usage = data.get("response", {}).get("usageMetadata", {})
                            if usage:
                                print(f"Usage: {usage}")

                        except json.JSONDecodeError:
                            pass

                if full_text:
                    print(f"Response: '{full_text}'")
                    return True
                else:
                    print(f"⚠️  Empty response (check if maxTokens too low or thinking-only)")
                    return True  # Still a success - server responded

            else:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Status {response.status_code}")
                print(f"Error: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ ERROR: {e}")
        return False

async def main():
    print("\n" + "="*60)
    print("SANDBOX-ONLY MODEL VALIDATION")
    print("Testing models on Sandbox endpoint (which works!)")
    print("="*60)

    tests = [
        ("gemini-3-flash", None, "Gemini 3 Flash (base)"),
        ("gemini-3-pro-high", None, "Gemini 3 Pro High (configured name)"),
        ("gemini-3-pro-low", None, "Gemini 3 Pro Low (configured name)"),
        ("claude-sonnet-4-5", None, "Claude Sonnet 4.5 (NOT Opus)"),
    ]

    results = []

    for model_name, thinking, description in tests:
        print(f"\n--- Test: {description} ---")
        success = await test_model_sandbox_only(model_name, thinking)
        results.append((description, success))

        # Wait between tests
        await asyncio.sleep(2)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All models accessible on Sandbox!")
        print("\n⚠️  Note: Production endpoint is rate limited (429)")
        print("Consider using Sandbox-only or fixing endpoint fallback logic")
    elif passed > 0:
        print(f"\n✅ Some models working on Sandbox!")
    else:
        print("\n❌ No models accessible")

if __name__ == "__main__":
    asyncio.run(main())
