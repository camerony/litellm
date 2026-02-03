"""
Test that Anthropic completion() uses stored tokens from claude setup-token.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litellm import completion
from litellm.llms.anthropic.common_utils import AnthropicModelInfo


def test_token_retrieval():
    """Test that get_api_key retrieves stored token."""
    print("\n" + "="*70)
    print("Testing Anthropic Token Retrieval")
    print("="*70)

    # Test the get_api_key function
    api_key = AnthropicModelInfo.get_api_key()

    if api_key:
        print(f"✅ API key/token found: {api_key[:20]}...")
        print("\nSource: ", end="")
        if os.getenv("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY environment variable")
        else:
            print("Stored token from ~/.litellm/anthropic-tokens.json")
        return True
    else:
        print("❌ No API key or token found")
        print("\nTo set up:")
        print("  1. Run: claude setup-token")
        print("  2. Run: poetry run python tests/test_anthropic_setup_token.py")
        print("\nOr set ANTHROPIC_API_KEY environment variable")
        return False


def test_completion():
    """Test a simple completion with Anthropic model."""
    print("\n" + "="*70)
    print("Testing Anthropic Completion")
    print("="*70)

    try:
        print("\nSending request to anthropic/claude-3-5-sonnet-20241022...")

        response = completion(
            model="anthropic/claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": "Say 'hello' in one word"}],
            max_tokens=10,
            timeout=30
        )

        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"✅ SUCCESS!")
            print(f"Response: {content}")
            return True
        else:
            print("❌ No valid response")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ ERROR: {error_str}")

        # Provide helpful error messages
        if "401" in error_str or "authentication" in error_str.lower():
            print("\n💡 Authentication failed - token may be expired or invalid")
            print("   Run: claude setup-token")
            print("   Then: poetry run python tests/test_anthropic_setup_token.py")
        elif "429" in error_str:
            print("\n💡 Rate limited - too many requests")
        elif "402" in error_str:
            print("\n💡 Billing/quota issue - check your Claude subscription")

        return False


def main():
    print("\n" + "="*70)
    print("ANTHROPIC TOKEN-BASED AUTHENTICATION TEST")
    print("="*70)
    print("\nThis test verifies that LiteLLM can use stored tokens from")
    print("`claude setup-token` instead of API keys.\n")

    # Test 1: Token retrieval
    if not test_token_retrieval():
        print("\n" + "="*70)
        print("⚠️  No authentication configured - skipping completion test")
        print("="*70)
        return

    # Test 2: Actual completion
    test_completion()

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
