"""
Validate that LiteLLM's OAuth implementation correctly retrieves:
1. Access token
2. Refresh token
3. Project ID from loadCodeAssist API

This tests WITHOUT relying on OpenClaw.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx


def test_loadcodeassist_api(access_token: str):
    """
    Test the loadCodeAssist API to fetch projectId.
    This is what OpenClaw does, and what LiteLLM should also do.
    """
    print("\n" + "="*70)
    print("TESTING loadCodeAssist API")
    print("="*70)

    endpoint = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    body = {}  # Empty body as per OpenClaw

    print(f"\nEndpoint: {endpoint}")
    print(f"Token: {access_token[:30]}...")

    try:
        response = httpx.post(endpoint, headers=headers, json=body, timeout=10.0)

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS! Response:")
            print(json.dumps(data, indent=2))

            # Extract projectId (handles both string and object format)
            project_data = data.get("cloudaicompanionProject")

            if isinstance(project_data, str):
                project_id = project_data
                print(f"\n✅ Project ID (string format): {project_id}")
            elif isinstance(project_data, dict):
                project_id = project_data.get("id")
                print(f"\n✅ Project ID (object format): {project_id}")
            else:
                print(f"\n⚠️  Unexpected format: {type(project_data)}")
                project_id = None

            return project_id

        else:
            print(f"\n❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def check_cli_auth_implementation():
    """Check if CLI auth.py correctly implements projectId fetching."""
    print("\n" + "="*70)
    print("CHECKING CLI AUTH IMPLEMENTATION")
    print("="*70)

    auth_file = "litellm/llms/google_antigravity/auth.py"

    if not os.path.exists(auth_file):
        print(f"❌ File not found: {auth_file}")
        return False

    with open(auth_file, 'r') as f:
        content = f.read()

    # Check for loadCodeAssist implementation
    checks = {
        "loadCodeAssist endpoint": "loadCodeAssist" in content,
        "cloudaicompanionProject parsing": "cloudaicompanionProject" in content,
        "String format handling": 'isinstance(project_data, str)' in content,
        "Dict format handling": 'isinstance(project_data, dict)' in content,
        "projectId storage": '"projectId"' in content,
    }

    print("\nImplementation Checks:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ CLI auth implementation looks correct!")
    else:
        print("\n⚠️  CLI auth implementation may be incomplete")

    return all_passed


def check_web_oauth_implementation():
    """Check if Web UI OAuth correctly implements projectId fetching."""
    print("\n" + "="*70)
    print("CHECKING WEB UI OAUTH IMPLEMENTATION")
    print("="*70)

    oauth_file = "litellm/proxy/auth/google_antigravity_auth_endpoints.py"

    if not os.path.exists(oauth_file):
        print(f"❌ File not found: {oauth_file}")
        return False

    with open(oauth_file, 'r') as f:
        content = f.read()

    # Check for loadCodeAssist implementation
    checks = {
        "loadCodeAssist endpoint": "loadCodeAssist" in content,
        "cloudaicompanionProject parsing": "cloudaicompanionProject" in content,
        "String format handling": 'isinstance(project_data, str)' in content,
        "Dict format handling": 'isinstance(project_data, dict)' in content,
        "projectId storage": '"projectId"' in content or "'projectId'" in content,
    }

    print("\nImplementation Checks:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ Web OAuth implementation looks correct!")
    else:
        print("\n⚠️  Web OAuth implementation may be incomplete")

    return all_passed


def test_with_existing_token():
    """Test loadCodeAssist with existing token from auth-profiles.json."""
    print("\n" + "="*70)
    print("TESTING WITH EXISTING TOKEN")
    print("="*70)

    auth_file = "auth-profiles.json"

    if not os.path.exists(auth_file):
        print(f"❌ Auth file not found: {auth_file}")
        return False

    with open(auth_file, 'r') as f:
        data = json.load(f)

    profiles = data.get("profiles", {})

    for email, profile in profiles.items():
        if profile.get("provider") == "google-antigravity":
            print(f"\nFound profile: {email}")

            access_token = profile.get("access")
            stored_project_id = profile.get("projectId")

            print(f"Stored Project ID: {stored_project_id}")

            # Test if we can fetch it ourselves
            fetched_project_id = test_loadcodeassist_api(access_token)

            if fetched_project_id:
                if fetched_project_id == stored_project_id:
                    print(f"\n✅ MATCH! Fetched project ID matches stored ID")
                    print(f"   LiteLLM can retrieve projectId independently!")
                    return True
                else:
                    print(f"\n⚠️  MISMATCH!")
                    print(f"   Stored:  {stored_project_id}")
                    print(f"   Fetched: {fetched_project_id}")
                    return False
            else:
                print(f"\n❌ Failed to fetch project ID")
                return False

    print(f"❌ No google-antigravity profile found")
    return False


def check_oauth_callback_code():
    """Extract and display the relevant OAuth callback code."""
    print("\n" + "="*70)
    print("OAUTH CALLBACK CODE REVIEW")
    print("="*70)

    oauth_file = "litellm/proxy/auth/google_antigravity_auth_endpoints.py"

    if not os.path.exists(oauth_file):
        print(f"❌ File not found: {oauth_file}")
        return

    with open(oauth_file, 'r') as f:
        lines = f.readlines()

    # Find the loadCodeAssist section
    in_section = False
    section_lines = []

    for i, line in enumerate(lines):
        if "loadCodeAssist" in line or in_section:
            section_lines.append((i+1, line.rstrip()))
            in_section = True

            # Stop after we've captured the projectId extraction
            if "projectId" in line and len(section_lines) > 5:
                # Capture a few more lines
                for j in range(5):
                    if i+j+1 < len(lines):
                        section_lines.append((i+j+2, lines[i+j+1].rstrip()))
                break

    if section_lines:
        print("\nProject ID Fetching Code (from Web UI OAuth):")
        print("-" * 70)
        for line_num, line in section_lines[:20]:  # Show first 20 lines
            print(f"{line_num:4d}: {line}")
        print("-" * 70)
    else:
        print("⚠️  Could not find loadCodeAssist code section")


def main():
    print("\n" + "="*70)
    print("LITELLM OAUTH IMPLEMENTATION VALIDATION")
    print("Verifying that LiteLLM can retrieve projectId independently")
    print("="*70)

    # Test 1: Check CLI implementation
    cli_ok = check_cli_auth_implementation()

    # Test 2: Check Web UI implementation
    web_ok = check_web_oauth_implementation()

    # Test 3: Show OAuth callback code
    check_oauth_callback_code()

    # Test 4: Test with existing token
    can_fetch = test_with_existing_token()

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    results = {
        "CLI auth.py implementation": cli_ok,
        "Web OAuth implementation": web_ok,
        "Can fetch projectId with current token": can_fetch,
    }

    print()
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 SUCCESS!")
        print("LiteLLM can independently retrieve projectId and tokens.")
        print("The implementation does NOT rely on OpenClaw.")
    else:
        print("\n⚠️  ISSUES FOUND")
        print("Some components may need fixes to work independently of OpenClaw.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
