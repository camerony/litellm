"""
Test and setup Anthropic token-based authentication (claude setup-token).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from litellm.llms.anthropic_token.auth import setup_token_interactive


def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    ANTHROPIC TOKEN SETUP                           ║
╚════════════════════════════════════════════════════════════════════╝

This setup allows you to use Anthropic's Claude models with session tokens
instead of API keys - just like OpenClaw does!

PREREQUISITES:
1. Install Anthropic's Claude CLI:
   npm install -g @anthropic-ai/claude-cli

2. Run the token generator:
   claude setup-token

3. Copy the token it generates

4. Paste it here

═══════════════════════════════════════════════════════════════════════

BENEFITS vs API KEYS:
✓ No API key management needed
✓ Uses your Claude subscription directly
✓ Same authentication method as Claude CLI
✓ Compatible with OpenClaw workflows

═══════════════════════════════════════════════════════════════════════
""")

    success = setup_token_interactive()

    if success:
        print("\n\n═══════════════════════════════════════════════════════════════════════")
        print("NEXT STEPS:")
        print("═══════════════════════════════════════════════════════════════════════\n")
        print("Test your setup:")
        print("  poetry run python tests/test_anthropic_token_usage.py")
        print("\nUse in your code:")
        print("  from litellm import completion")
        print("  response = completion(")
        print("      model='anthropic/claude-3-5-sonnet-20241022',")
        print("      messages=[{'role': 'user', 'content': 'Hello'}]")
        print("  )")
        print("\n═══════════════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
