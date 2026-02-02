"""
Test the exact model names that are configured in the system.
"""

import os
import sys
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_model_direct(model_name: str):
    """Test a specific model name directly."""
    print(f"\n{'='*70}")
    print(f"Testing: {model_name}")
    print(f"{'='*70}")

    handler = GoogleAntigravityChatCompletion()

    # Get credentials
    access_token = handler._get_access_token({})
    auth_file_path, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    # Try both endpoints
    endpoints = [
        ("Sandbox", "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"),
        ("Production", "https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse")
    ]

    for endpoint_name, endpoint in endpoints:
        print(f"\n--- {endpoint_name} Endpoint ---")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "antigravity/1.15.8 darwin/arm64",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
        }

        # Check if this is a Claude model with thinking
        if "claude" in model_name and "thinking" in model_name:
            headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"

        body = {
            "model": model_name,  # Use exact name
            "request": {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": "Say hi"}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 50,
                    "temperature": 1.0
                }
            },
            "userAgent": "antigravity",
            "requestType": "agent",
            "requestId": f"test-{int(time.time()*1000)}"
        }

        if project_id:
            body["project"] = project_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=body, headers=headers)

                if response.status_code == 200:
                    print(f"✅ 200 OK - Model accessible!")

                    # Parse first line of response
                    lines = response.text.strip().split('\n')
                    for line in lines[:3]:
                        if line.startswith('data: '):
                            try:
                                import json
                                data = json.loads(line[6:])

                                # Extract text
                                candidates = data.get("response", {}).get("candidates", [])
                                for candidate in candidates:
                                    parts = candidate.get("content", {}).get("parts", [])
                                    for part in parts:
                                        text = part.get("text", "")
                                        if text:
                                            print(f"   Response: '{text}'")

                                # Show usage
                                usage = data.get("response", {}).get("usageMetadata", {})
                                if usage:
                                    print(f"   Usage: {usage}")

                            except:
                                pass

                    return True  # Found working endpoint

                elif response.status_code == 404:
                    print(f"❌ 404 Not Found")
                elif response.status_code == 429:
                    print(f"❌ 429 Rate Limited")
                elif response.status_code == 403:
                    print(f"❌ 403 Forbidden (licensing)")
                else:
                    print(f"❌ {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")

        # Small delay between endpoints
        await asyncio.sleep(1)

    return False

async def main():
    print("\n" + "="*70)
    print("TESTING CONFIGURED MODELS")
    print("="*70)

    # Test the exact model names from the configuration
    models = [
        "gemini-3-flash",
        "gemini-3-pro-high",
        "gemini-3-pro-low",
        "claude-opus-4-5-thinking",
    ]

    results = {}

    for model in models:
        success = await test_model_direct(model)
        results[model] = success

        # Wait between tests
        await asyncio.sleep(2)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    working = [m for m, s in results.items() if s]
    not_working = [m for m, s in results.items() if not s]

    if working:
        print("\n✅ WORKING MODELS:")
        for model in working:
            print(f"   • {model}")

    if not_working:
        print("\n❌ NOT ACCESSIBLE:")
        for model in not_working:
            print(f"   • {model}")

    print(f"\nTotal: {len(working)}/{len(models)} models accessible")

if __name__ == "__main__":
    asyncio.run(main())
