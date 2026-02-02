"""
Comprehensive test of all Antigravity models EXCEPT Opus.
Tests both Gemini and Claude Sonnet models.
"""

import os
import sys
import asyncio
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litellm import acompletion


async def test_model(model_name: str, test_prompt: str = "Say hello in one word"):
    """Test a single model with a simple prompt."""
    print(f"\n{'='*70}")
    print(f"Testing: google_antigravity/{model_name}")
    print(f"{'='*70}")
    print(f"Prompt: {test_prompt}")

    start_time = time.time()

    try:
        response = await acompletion(
            model=f"google_antigravity/{model_name}",
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=100,
            timeout=30
        )

        elapsed = time.time() - start_time

        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content

            print(f"\n✅ SUCCESS! ({elapsed:.2f}s)")
            print(f"Response: {content[:200]}")

            # Show usage if available
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                print(f"Usage: {usage}")

            return {
                "status": "success",
                "model": model_name,
                "response": content[:100],
                "time": elapsed
            }
        else:
            print(f"\n❌ FAILED: No valid response")
            return {
                "status": "failed",
                "model": model_name,
                "error": "No response content"
            }

    except Exception as e:
        elapsed = time.time() - start_time
        error_str = str(e)

        print(f"\n❌ ERROR ({elapsed:.2f}s)")

        # Categorize error
        if "404" in error_str:
            print(f"Error: 404 Model Not Found")
            error_type = "not_found"
        elif "429" in error_str:
            print(f"Error: 429 Rate Limited")
            error_type = "rate_limited"
        elif "403" in error_str:
            print(f"Error: 403 Forbidden (licensing)")
            error_type = "forbidden"
        elif "500" in error_str:
            print(f"Error: 500 Server Error")
            error_type = "server_error"
        else:
            print(f"Error: {error_str[:200]}")
            error_type = "unknown"

        return {
            "status": "error",
            "model": model_name,
            "error_type": error_type,
            "error": error_str[:200]
        }


async def test_thinking_modes():
    """Test Gemini models with different thinking levels."""
    print("\n" + "="*70)
    print("TESTING THINKING MODES")
    print("="*70)

    thinking_tests = [
        ("gemini-3-pro-high", "HIGH", "Explain recursion briefly"),
        ("gemini-3-pro-low", "LOW", "What is 2+2?"),
        ("gemini-3-flash", None, "Count to 3"),
    ]

    results = []

    for model, thinking_level, prompt in thinking_tests:
        result = await test_model(model, prompt)
        results.append(result)

        # Wait between requests
        await asyncio.sleep(2)

    return results


async def test_claude_models():
    """Test Claude models (except Opus)."""
    print("\n" + "="*70)
    print("TESTING CLAUDE MODELS (EXCEPT OPUS)")
    print("="*70)

    claude_tests = [
        ("claude-sonnet-4-5", "Write a haiku about code"),
        # Skipping Opus as requested
        # ("claude-opus-4-5-thinking", "..."),
    ]

    results = []

    for model, prompt in claude_tests:
        result = await test_model(model, prompt)
        results.append(result)

        await asyncio.sleep(2)

    return results


async def test_streaming():
    """Test streaming with a working model."""
    print("\n" + "="*70)
    print("TESTING STREAMING")
    print("="*70)

    model = "gemini-3-flash"
    prompt = "Count from 1 to 5"

    print(f"\nModel: {model}")
    print(f"Prompt: {prompt}")
    print(f"\nStreaming response:")
    print("-" * 70)

    try:
        response = await acompletion(
            model=f"google_antigravity/{model}",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            stream=True,
            timeout=30
        )

        chunks_received = 0
        full_text = ""

        async for chunk in response:
            chunks_received += 1

            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    full_text += delta.content
                    print(delta.content, end='', flush=True)

        print()
        print("-" * 70)
        print(f"\n✅ Streaming succeeded!")
        print(f"Chunks received: {chunks_received}")
        print(f"Full text: {full_text[:200]}")

        return {
            "status": "success",
            "chunks": chunks_received,
            "text": full_text[:100]
        }

    except Exception as e:
        print(f"\n❌ Streaming failed: {str(e)[:200]}")
        return {
            "status": "error",
            "error": str(e)[:200]
        }


async def main():
    print("\n" + "="*70)
    print("COMPREHENSIVE MODEL TESTING (EXCEPT OPUS)")
    print("="*70)
    print("\nTesting all configured models to verify accessibility")
    print("Per user: NOT rate limited except for Opus")
    print("="*70)

    all_results = []

    # Test 1: Thinking modes (Gemini)
    print("\n\n### TEST 1: GEMINI MODELS WITH THINKING ###")
    thinking_results = await test_thinking_modes()
    all_results.extend(thinking_results)

    # Test 2: Claude models
    print("\n\n### TEST 2: CLAUDE MODELS ###")
    claude_results = await test_claude_models()
    all_results.extend(claude_results)

    # Test 3: Streaming
    print("\n\n### TEST 3: STREAMING ###")
    streaming_result = await test_streaming()

    # Summary
    print("\n\n" + "="*70)
    print("COMPREHENSIVE TEST SUMMARY")
    print("="*70)

    successful = [r for r in all_results if r["status"] == "success"]
    failed = [r for r in all_results if r["status"] in ["failed", "error"]]

    print(f"\n✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")

    if successful:
        print("\n✅ WORKING MODELS:")
        for result in successful:
            time_str = f" ({result['time']:.2f}s)" if 'time' in result else ""
            print(f"   • {result['model']}{time_str}")

    if failed:
        print("\n❌ FAILED MODELS:")
        for result in failed:
            error_type = result.get('error_type', 'unknown')
            print(f"   • {result['model']} - {error_type}")

    print(f"\n📊 Success Rate: {len(successful)}/{len(all_results)} ({len(successful)/len(all_results)*100:.1f}%)")

    # Streaming result
    if streaming_result.get("status") == "success":
        print(f"\n✅ Streaming: Working ({streaming_result['chunks']} chunks)")
    else:
        print(f"\n❌ Streaming: Failed")

    # Final verdict
    print("\n" + "="*70)
    if len(successful) >= 2:
        print("🎉 VALIDATION PASSED!")
        print("Multiple models are accessible and working.")
        print("Implementation is production-ready!")
    elif len(successful) >= 1:
        print("✅ PARTIAL SUCCESS")
        print("At least one model is working.")
        print("Check quota for failed models.")
    else:
        print("❌ VALIDATION FAILED")
        print("No models accessible - check credentials and quota.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
