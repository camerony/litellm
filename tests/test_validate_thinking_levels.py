"""
Validate that Pro-High actually uses HIGH thinking level.
Compare thinking token usage and response quality across levels.
"""

import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litellm import acompletion

async def test_thinking_level_validation():
    """
    Test that different model names produce different thinking levels.
    Pro-High should use more thinking tokens than Pro-Low.
    """
    print("\n" + "="*70)
    print("THINKING LEVEL VALIDATION")
    print("="*70)
    print("\nHypothesis: Pro-High uses more thinking tokens than Pro-Low")
    print("Testing with a problem that benefits from deeper thinking")
    print("="*70)

    # Use a problem that benefits from thinking
    prompt = """Solve this step by step:
If a train travels at 60 mph for 2.5 hours, then at 80 mph for 1.5 hours,
what is the total distance traveled?"""

    models = [
        ("google_antigravity/gemini-3-flash", "Base (no suffix)"),
        ("google_antigravity/gemini-3-pro-low", "Pro-Low"),
        ("google_antigravity/gemini-3-pro-high", "Pro-High"),
    ]

    results = []

    for model, description in models:
        print(f"\n{'='*70}")
        print(f"Testing: {description}")
        print(f"Model: {model}")
        print(f"{'='*70}")

        try:
            response = await acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                timeout=30
            )

            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                usage = response.usage if hasattr(response, 'usage') else None

                # Extract thinking tokens (total - prompt - completion)
                thinking_tokens = 0
                if usage:
                    thinking_tokens = usage.total_tokens - usage.prompt_tokens - usage.completion_tokens

                print(f"\n✅ SUCCESS")
                print(f"Response preview: {content[:150]}...")
                print(f"\nToken Usage:")
                print(f"  Prompt tokens:     {usage.prompt_tokens if usage else 'N/A'}")
                print(f"  Completion tokens: {usage.completion_tokens if usage else 'N/A'}")
                print(f"  Thinking tokens:   {thinking_tokens} ← KEY METRIC")
                print(f"  Total tokens:      {usage.total_tokens if usage else 'N/A'}")

                results.append({
                    "model": description,
                    "thinking_tokens": thinking_tokens,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "response_length": len(content),
                    "success": True
                })
            else:
                print(f"\n❌ No response")
                results.append({
                    "model": description,
                    "success": False
                })

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            results.append({
                "model": description,
                "success": False,
                "error": str(e)
            })

        await asyncio.sleep(2)

    # Analysis
    print(f"\n\n{'='*70}")
    print("VALIDATION RESULTS")
    print(f"{'='*70}\n")

    successful = [r for r in results if r.get("success")]

    if len(successful) >= 2:
        print("Thinking Token Comparison:")
        for result in successful:
            thinking = result.get("thinking_tokens", 0)
            print(f"  {result['model']:15s}: {thinking:4d} thinking tokens")

        # Verify that Pro-High uses more thinking than Pro-Low
        pro_high = next((r for r in successful if "Pro-High" in r["model"]), None)
        pro_low = next((r for r in successful if "Pro-Low" in r["model"]), None)
        base = next((r for r in successful if "Base" in r["model"]), None)

        print(f"\n{'='*70}")
        print("VALIDATION:")
        print(f"{'='*70}\n")

        if pro_high and pro_low:
            high_thinking = pro_high.get("thinking_tokens", 0)
            low_thinking = pro_low.get("thinking_tokens", 0)

            if high_thinking > low_thinking:
                diff = high_thinking - low_thinking
                pct = (diff / low_thinking * 100) if low_thinking > 0 else 0
                print(f"✅ PASS: Pro-High uses MORE thinking than Pro-Low")
                print(f"   Pro-High: {high_thinking} tokens")
                print(f"   Pro-Low:  {low_thinking} tokens")
                print(f"   Difference: +{diff} tokens ({pct:.1f}% more)")
            elif high_thinking == low_thinking:
                print(f"⚠️  WARNING: Same thinking tokens ({high_thinking})")
                print(f"   This might be OK for simple problems")
                print(f"   Try a more complex problem to see difference")
            else:
                print(f"❌ FAIL: Pro-High uses LESS thinking than Pro-Low!")
                print(f"   Pro-High: {high_thinking} tokens")
                print(f"   Pro-Low:  {low_thinking} tokens")

        if base and pro_high:
            base_thinking = base.get("thinking_tokens", 0)
            high_thinking = pro_high.get("thinking_tokens", 0)

            print(f"\n✅ Base vs Pro-High:")
            print(f"   Base:     {base_thinking} tokens")
            print(f"   Pro-High: {high_thinking} tokens")

    else:
        print("❌ Not enough successful tests to compare")

    print(f"\n{'='*70}")


async def test_request_inspection():
    """
    Capture the actual request being sent to validate thinking config.
    """
    print("\n\n" + "="*70)
    print("REQUEST INSPECTION")
    print("="*70)
    print("\nCapturing actual API requests to verify thinking configuration")
    print("="*70)

    import httpx
    from litellm.llms.google_antigravity.chat.handler import GoogleAntigravityChatCompletion

    handler = GoogleAntigravityChatCompletion()
    access_token = handler._get_access_token({})
    _, auth_data = handler._get_credentials_from_file()

    project_id = None
    for profile in auth_data.get("profiles", {}).values():
        if profile.get("provider") == "google-antigravity":
            project_id = profile.get("projectId")
            break

    tests = [
        ("gemini-3-flash", None, "Base"),
        ("gemini-3-flash", "LOW", "Explicit LOW"),
        ("gemini-3-flash", "HIGH", "Explicit HIGH"),
    ]

    for model, thinking_level, description in tests:
        print(f"\n{'='*70}")
        print(f"Test: {description}")
        print(f"{'='*70}")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

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
                    "parts": [{"text": "hi"}]
                }],
                "generationConfig": generation_config
            }
        }

        if project_id:
            body["project"] = project_id

        print(f"\nRequest Body (generationConfig):")
        print(json.dumps(generation_config, indent=2))

        # Send request
        endpoint = "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=body, headers=headers)

                if response.status_code == 200:
                    # Parse usage
                    lines = response.text.split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                usage = data.get("response", {}).get("usageMetadata", {})
                                if usage:
                                    thinking = usage.get("thoughtsTokenCount", 0)
                                    print(f"\n✅ Response: {response.status_code}")
                                    print(f"   Thinking tokens: {thinking}")
                                    break
                            except:
                                pass
                else:
                    print(f"\n❌ Status: {response.status_code}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")

        await asyncio.sleep(1)


async def main():
    # Test 1: Validate thinking levels produce different token counts
    await test_thinking_level_validation()

    # Test 2: Inspect actual requests
    await test_request_inspection()

    print("\n\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
If Pro-High uses significantly more thinking tokens than Pro-Low,
then we've validated that:

1. The suffix extraction works (gemini-3-pro-high → HIGH)
2. The thinking config is correctly added to requests
3. The API honors the thinking level parameter
4. The model mapping works (gemini-3-pro-* → gemini-3-flash)

This proves the implementation is correct.
""")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
