"""
Careful validation - one model at a time with delays.
Focus on Gemini models since Opus is known to be rate limited.
"""

import os
import sys
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litellm import acompletion
import litellm

# Enable debug mode
litellm.set_verbose = True

async def test_single_model(model_name: str, description: str):
    """Test a single model carefully."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Description: {description}")
    print(f"{'='*60}")

    try:
        print(f"[{time.strftime('%H:%M:%S')}] Sending request...")

        response = await acompletion(
            model=f"google_antigravity/{model_name}",
            messages=[{"role": "user", "content": "Say 'hello' in one word"}],
            max_tokens=10,
            timeout=30
        )

        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"[{time.strftime('%H:%M:%S')}] ✅ SUCCESS!")
            print(f"Response: {content}")
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ No valid response")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"[{time.strftime('%H:%M:%S')}] ❌ ERROR: {error_str[:200]}")

        # Check specific error types
        if "403" in error_str:
            print("  → 403: Licensing issue (Gemini Code Assist license needed)")
        elif "429" in error_str:
            print("  → 429: Rate limited (quota exhausted or too many requests)")
        elif "404" in error_str:
            print("  → 404: Model not found (may not be available)")
        elif "500" in error_str:
            print("  → 500: Server error (Google backend issue)")

        return False

async def main():
    print("\n" + "="*60)
    print("CAREFUL ANTIGRAVITY MODEL VALIDATION")
    print("Testing one model at a time with delays")
    print("="*60)

    # Test Gemini models (skip Opus which is rate limited)
    models = [
        ("gemini-3-pro", "Gemini 3 Pro (base)"),
        ("gemini-3-pro-high", "Gemini 3 Pro with HIGH thinking"),
        ("gemini-3-flash", "Gemini 3 Flash (faster)"),
        ("claude-sonnet-4-5", "Claude Sonnet 4.5 (not Opus)"),
    ]

    results = []

    for i, (model, desc) in enumerate(models):
        success = await test_single_model(model, desc)
        results.append((model, success))

        # Wait between requests (except after last one)
        if i < len(models) - 1:
            print(f"\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for model, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {model}")

    print(f"\nTotal: {passed}/{total} models accessible")

    if passed == 0:
        print("\n⚠️  No models accessible - Check:")
        print("  1. Gemini Code Assist license in Google Cloud Console")
        print("  2. Project billing is active")
        print("  3. API quotas at console.cloud.google.com/apis/dashboard")
    elif passed < total:
        print(f"\n⚠️  Some models unavailable - May be licensing/quota specific")
    else:
        print("\n🎉 All tested models working!")

if __name__ == "__main__":
    asyncio.run(main())
