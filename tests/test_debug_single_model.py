"""
Debug a single model call to see what's being sent.
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import litellm
from litellm import acompletion

# Enable debug mode
litellm.set_verbose = True

async def test_single_model():
    print("\n" + "="*70)
    print("DEBUG: Testing gemini-3-flash")
    print("="*70)

    try:
        response = await acompletion(
            model="google_antigravity/gemini-3-flash",
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=50,
            timeout=30
        )

        print("\n✅ SUCCESS!")
        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"Response: {content}")

            if hasattr(response, 'usage'):
                print(f"Usage: {response.usage}")
        else:
            print("No response content")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_model())
