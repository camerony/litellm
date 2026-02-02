"""
Test if gemini-3-flash with different thinking levels is what 'pro' models actually are.
"""

import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_flash_with_thinking(thinking_level: str):
    """Test gemini-3-flash with specific thinking level."""
    print(f"\n{'='*70}")
    print(f"Testing gemini-3-flash with {thinking_level} thinking")
    print(f"{'='*70}")

    handler = GoogleAntigravityChatCompletion()
    access_token = handler._get_access_token({})
    _, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

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

    generation_config = {
        "maxOutputTokens": 100,
        "temperature": 1.0
    }

    if thinking_level:
        generation_config["thinkingConfig"] = {
            "includeThoughts": True,
            "thinkingLevel": thinking_level
        }

    body = {
        "model": "gemini-3-flash",
        "request": {
            "contents": [{
                "role": "user",
                "parts": [{"text": "What is 2+2?"}]
            }],
            "generationConfig": generation_config
        },
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": f"test-{int(asyncio.get_event_loop().time()*1000)}"
    }

    if project_id:
        body["project"] = project_id

    endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=body, headers=headers)

            if response.status_code == 200:
                print(f"✅ 200 OK")

                # Parse response
                full_text = ""
                thinking_tokens = 0
                completion_tokens = 0

                lines = response.text.split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])

                            # Extract text
                            candidates = data.get("response", {}).get("candidates", [])
                            for candidate in candidates:
                                parts = candidate.get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        full_text += text

                            # Extract usage
                            usage = data.get("response", {}).get("usageMetadata", {})
                            if usage:
                                thinking_tokens = usage.get("thoughtsTokenCount", 0)
                                completion_tokens = usage.get("candidatesTokenCount", 0)

                        except:
                            pass

                print(f"Response: '{full_text[:100]}'")
                print(f"Thinking tokens: {thinking_tokens}")
                print(f"Completion tokens: {completion_tokens}")
                print(f"Total tokens used: {thinking_tokens + completion_tokens}")

                return True
            else:
                print(f"❌ {response.status_code}")
                try:
                    error = response.json()
                    print(f"Error: {error.get('error', {}).get('message', 'Unknown')}")
                except:
                    pass
                return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def main():
    print("\n" + "="*70)
    print("HYPOTHESIS: gemini-3-pro-* = gemini-3-flash with thinking levels")
    print("="*70)

    # Test different thinking levels
    thinking_levels = [
        None,      # Base (no thinking config)
        "LOW",     # gemini-3-pro-low?
        "MEDIUM",  # gemini-3-pro-medium?
        "HIGH",    # gemini-3-pro-high?
    ]

    results = []
    for level in thinking_levels:
        success = await test_flash_with_thinking(level)
        results.append((level or "None", success))
        await asyncio.sleep(2)

    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")

    for level, success in results:
        status = "✅" if success else "❌"
        print(f"{status} gemini-3-flash with {level} thinking")

    print("\n" + "="*70)
    print("CONCLUSION:")
    print("="*70)
    print("If all thinking levels work, then:")
    print("  • gemini-3-pro-high = gemini-3-flash + HIGH thinking")
    print("  • gemini-3-pro-low = gemini-3-flash + LOW thinking")
    print("  • gemini-3-flash = gemini-3-flash + default/no thinking config")
    print("\nThere is NO separate 'gemini-3-pro' model!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
