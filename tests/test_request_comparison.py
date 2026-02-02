"""
Compare LiteLLM request format with what OpenClaw would send.
"""

import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_openclaw_format():
    """Test using exact OpenClaw request format."""
    print("\n" + "="*70)
    print("TESTING WITH OPENCLAW-STYLE REQUEST")
    print("="*70)

    handler = GoogleAntigravityChatCompletion()
    access_token = handler._get_access_token({})
    _, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    # Test gemini-3-pro (base model without suffix)
    model = "gemini-3-pro"

    # OpenClaw-style headers (from their source)
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

    # OpenClaw-style body with HIGH thinking
    body = {
        "model": model,
        "request": {
            "contents": [{
                "role": "user",
                "parts": [{"text": "Say hi"}]
            }],
            "generationConfig": {
                "maxOutputTokens": 50,
                "temperature": 1.0,
                "thinkingConfig": {
                    "includeThoughts": True,
                    "thinkingLevel": "HIGH"
                }
            }
        },
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": f"test-{int(asyncio.get_event_loop().time()*1000)}"
    }

    if project_id:
        body["project"] = project_id

    print(f"\nModel: {model}")
    print(f"Project ID: {project_id}")
    print(f"\nRequest body:")
    print(json.dumps(body, indent=2))

    # Try sandbox endpoint
    endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

    print(f"\n\nTesting Sandbox endpoint...")
    print(f"URL: {endpoint}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=body, headers=headers)

            print(f"\nStatus: {response.status_code}")

            if response.status_code == 200:
                print(f"✅ SUCCESS!")

                # Parse response
                lines = response.text.split('\n')
                for line in lines[:5]:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            candidates = data.get("response", {}).get("candidates", [])
                            for candidate in candidates:
                                parts = candidate.get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        print(f"Response: '{text}'")

                            usage = data.get("response", {}).get("usageMetadata", {})
                            if usage:
                                print(f"Usage: {usage}")
                        except:
                            pass

                return True
            else:
                print(f"❌ FAILED: {response.status_code}")
                try:
                    error = response.json()
                    print(f"Error: {json.dumps(error, indent=2)}")
                except:
                    print(f"Error: {response.text[:500]}")
                return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def test_all_models_openclaw_format():
    """Test all models using OpenClaw format."""
    print("\n" + "="*70)
    print("TESTING ALL MODELS WITH OPENCLAW FORMAT")
    print("="*70)

    handler = GoogleAntigravityChatCompletion()
    access_token = handler._get_access_token({})
    _, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    # Test different models
    tests = [
        ("gemini-3-flash", None, "Gemini 3 Flash"),
        ("gemini-3-pro", "HIGH", "Gemini 3 Pro with HIGH thinking"),
        ("gemini-3-pro", "LOW", "Gemini 3 Pro with LOW thinking"),
        ("claude-sonnet-4-5", None, "Claude Sonnet 4.5"),
    ]

    endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"
    results = []

    for model, thinking_level, description in tests:
        print(f"\n\n{'='*70}")
        print(f"Testing: {description}")
        print(f"{'='*70}")

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

        # Add thinking header for Claude if needed
        if "claude" in model:
            headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"

        generation_config = {
            "maxOutputTokens": 50,
            "temperature": 1.0
        }

        if thinking_level:
            generation_config["thinkingConfig"] = {
                "includeThoughts": True,
                "thinkingLevel": thinking_level
            }

        body = {
            "model": model,
            "request": {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": "Say hi"}]
                }],
                "generationConfig": generation_config
            },
            "userAgent": "antigravity",
            "requestType": "agent",
            "requestId": f"test-{int(asyncio.get_event_loop().time()*1000)}"
        }

        if project_id:
            body["project"] = project_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=body, headers=headers)

                if response.status_code == 200:
                    print(f"✅ 200 OK")

                    # Parse first response
                    lines = response.text.split('\n')
                    for line in lines[:3]:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                candidates = data.get("response", {}).get("candidates", [])
                                for candidate in candidates:
                                    parts = candidate.get("content", {}).get("parts", [])
                                    for part in parts:
                                        text = part.get("text", "")
                                        if text:
                                            print(f"   Response: '{text[:50]}'")
                            except:
                                pass

                    results.append((description, True))
                else:
                    print(f"❌ {response.status_code}")
                    try:
                        error = response.json()
                        print(f"   Error: {error.get('error', {}).get('message', 'Unknown')}")
                    except:
                        pass
                    results.append((description, False))

        except Exception as e:
            print(f"❌ ERROR: {str(e)[:100]}")
            results.append((description, False))

        await asyncio.sleep(2)

    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} working")


async def main():
    # First test with exact OpenClaw format
    await test_openclaw_format()

    # Then test all models
    await test_all_models_openclaw_format()


if __name__ == "__main__":
    asyncio.run(main())
