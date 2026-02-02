"""
Deep debug - check what's really happening with the endpoints.
"""

import os
import sys
import asyncio
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

async def test_raw_endpoint():
    """Test the raw Antigravity endpoint directly."""
    print("\n" + "="*60)
    print("DIRECT ENDPOINT TEST (No LiteLLM wrapper)")
    print("="*60)

    handler = GoogleAntigravityChatCompletion()

    # Get access token
    try:
        access_token = handler._get_access_token({})
        print(f"\n✅ Access token retrieved: {access_token[:30]}...")
    except Exception as e:
        print(f"\n❌ Failed to get access token: {e}")
        return

    # Get project ID from auth file
    try:
        auth_file_path, auth_data = handler._get_credentials_from_file()
        profiles = auth_data.get("profiles", {})
        project_id = None
        for profile in profiles.values():
            if profile.get("provider") == "google-antigravity":
                project_id = profile.get("projectId")
                break
        print(f"✅ Project ID: {project_id}")
    except Exception as e:
        print(f"❌ Failed to get project ID: {e}")
        project_id = None

    # Test both endpoints
    endpoints = [
        ("Sandbox", "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"),
        ("Production", "https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse")
    ]

    for name, endpoint in endpoints:
        print(f"\n{'='*60}")
        print(f"Testing {name} Endpoint")
        print(f"URL: {endpoint}")
        print(f"{'='*60}")

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "antigravity/1.15.8 darwin/arm64",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
        }

        # Prepare body - minimal test
        body = {
            "model": "gemini-3-flash",
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
            "requestId": f"test-{int(time.time()*1000)}"
        }

        if project_id:
            body["project"] = project_id

        print(f"\nRequest body:")
        print(json.dumps(body, indent=2)[:500])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"\n[{time.strftime('%H:%M:%S')}] Sending request...")
                response = await client.post(endpoint, json=body, headers=headers)

                print(f"[{time.strftime('%H:%M:%S')}] Response Status: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")

                # Try to read response
                if response.status_code == 200:
                    print("\n✅ SUCCESS! Reading response...")

                    # For SSE, read line by line
                    content = response.text[:1000]
                    print(f"Response preview:\n{content}")

                    # Try to parse SSE events
                    lines = content.split('\n')
                    for line in lines[:10]:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                print(f"\nParsed SSE data:")
                                print(json.dumps(data, indent=2)[:500])
                            except:
                                pass

                elif response.status_code == 403:
                    error = response.json()
                    print(f"\n❌ 403 FORBIDDEN")
                    print(f"Error: {json.dumps(error, indent=2)}")
                    print("\n→ This is a LICENSING issue")
                    print("→ The Google Cloud Project needs Gemini Code Assist license")

                elif response.status_code == 429:
                    error = response.json()
                    print(f"\n❌ 429 RATE LIMITED")
                    print(f"Error: {json.dumps(error, indent=2)}")
                    print("\n→ This is a QUOTA issue")
                    print("→ Check quota at: console.cloud.google.com/apis/dashboard")

                elif response.status_code == 500:
                    error = response.json()
                    print(f"\n❌ 500 SERVER ERROR")
                    print(f"Error: {json.dumps(error, indent=2)}")
                    print("\n→ Google's backend issue")

                else:
                    print(f"\n❌ Unexpected status: {response.status_code}")
                    print(f"Response: {response.text[:500]}")

        except httpx.TimeoutException:
            print(f"❌ Request timed out")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Wait between endpoint tests
        await asyncio.sleep(3)

async def main():
    await test_raw_endpoint()

if __name__ == "__main__":
    asyncio.run(main())
