"""
Test different model name variations to find correct Pro model names.
"""

import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_model_name(model_name: str, handler, access_token, project_id, endpoint):
    """Test a specific model name."""
    headers = {
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
    }

    body = {
        "model": model_name,
        "request": {
            "contents": [{
                "role": "user",
                "parts": [{"text": "hi"}]
            }],
            "generationConfig": {
                "maxOutputTokens": 10,
                "temperature": 1.0
            }
        },
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": f"test-{int(asyncio.get_event_loop().time()*1000)}"
    }

    if project_id:
        body["project"] = project_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(endpoint, json=body, headers=headers)

            if response.status_code == 200:
                return (model_name, "✅ 200 OK", None)
            elif response.status_code == 404:
                return (model_name, "❌ 404 Not Found", "Model doesn't exist")
            elif response.status_code == 429:
                return (model_name, "❌ 429 Rate Limited", "Quota exhausted")
            elif response.status_code == 403:
                return (model_name, "❌ 403 Forbidden", "No license")
            else:
                return (model_name, f"❌ {response.status_code}", response.text[:100])

    except Exception as e:
        return (model_name, "❌ ERROR", str(e)[:100])


async def main():
    print("\n" + "="*70)
    print("MODEL NAME DISCOVERY")
    print("="*70)

    handler = GoogleAntigravityChatCompletion()
    access_token = handler._get_access_token({})
    _, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

    # Test various model name patterns
    model_candidates = [
        # Flash variants (known to work)
        "gemini-3-flash",
        "gemini-3.0-flash",
        "gemini-3-flash-001",

        # Pro variants
        "gemini-3-pro",
        "gemini-3.0-pro",
        "gemini-3-pro-001",
        "gemini-3-pro-exp",
        "gemini-3-pro-latest",
        "gemini-pro-3",
        "gemini-3-pro-002",

        # Gemini 2 (in case naming changed)
        "gemini-2.0-flash-exp",
        "gemini-2.0-pro-exp",

        # Claude variants
        "claude-sonnet-4-5",
        "claude-3-5-sonnet",
        "claude-sonnet-3-5",
    ]

    print(f"\nTesting {len(model_candidates)} model name candidates...")
    print(f"Project: {project_id}")
    print(f"Endpoint: {endpoint}\n")

    results = []
    for model_name in model_candidates:
        result = await test_model_name(model_name, handler, access_token, project_id, endpoint)
        results.append(result)
        print(f"{result[1]:20s} {result[0]}")

        if result[2]:
            print(f"{'':20s} → {result[2]}")

        await asyncio.sleep(0.5)  # Small delay between requests

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")

    working = [r for r in results if "200 OK" in r[1]]
    not_found = [r for r in results if "404" in r[1]]
    rate_limited = [r for r in results if "429" in r[1]]
    forbidden = [r for r in results if "403" in r[1]]

    if working:
        print(f"✅ WORKING MODELS ({len(working)}):")
        for model, status, _ in working:
            print(f"   • {model}")

    if rate_limited:
        print(f"\n⏸️  RATE LIMITED ({len(rate_limited)}) - Model exists but quota exhausted:")
        for model, status, _ in rate_limited:
            print(f"   • {model}")

    if forbidden:
        print(f"\n🔒 FORBIDDEN ({len(forbidden)}) - Model exists but no license:")
        for model, status, _ in forbidden:
            print(f"   • {model}")

    if not_found:
        print(f"\n❌ NOT FOUND ({len(not_found)}) - Model doesn't exist:")
        for model, status, _ in not_found:
            print(f"   • {model}")


if __name__ == "__main__":
    asyncio.run(main())
