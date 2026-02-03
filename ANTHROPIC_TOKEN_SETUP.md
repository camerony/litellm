# Anthropic Token-Based Authentication (like OpenClaw)

This guide shows how to use Anthropic's Claude models with **session tokens** instead of API keys - the same method OpenClaw uses.

## Why Use Tokens Instead of API Keys?

✅ **No API key management** - Use tokens from `claude setup-token`
✅ **Your Claude subscription** - Uses your existing Claude account
✅ **Compatible with OpenClaw** - Same authentication method
✅ **Simpler workflow** - No need to manage API keys

## Setup Process

### Step 1: Install Claude CLI

Install Anthropic's official Claude CLI tool:

```bash
# Using npm (recommended)
npm install -g @anthropic-ai/claude-cli

# Or using pip
pip install anthropic-claude-cli
```

Verify installation:
```bash
claude --version
```

### Step 2: Generate Setup Token

Run Claude's token generator:

```bash
claude setup-token
```

This will:
1. Open a browser for authentication
2. Generate a session token
3. Display the token in your terminal

**Copy the token** - you'll need it in the next step.

### Step 3: Configure LiteLLM

Run LiteLLM's interactive setup:

```bash
cd /path/to/litellm
poetry run python tests/test_anthropic_setup_token.py
```

Follow the prompts:
1. Confirm you've run `claude setup-token`
2. Paste your token
3. Optionally set expiration (default: 365 days)

Your token will be stored in `~/.litellm/anthropic-tokens.json`

## Usage

### Python API

```python
from litellm import completion

# LiteLLM will automatically use your stored token
response = completion(
    model="anthropic/claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### Async Usage

```python
from litellm import acompletion
import asyncio

async def main():
    response = await acompletion(
        model="anthropic/claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

### Streaming

```python
from litellm import completion

response = completion(
    model="anthropic/claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Write a story"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Available Models

Once configured, you can use any Anthropic model:

| Model | Description |
|-------|-------------|
| `anthropic/claude-opus-4-20250514` | Most capable model |
| `anthropic/claude-3-5-sonnet-20241022` | Balanced performance |
| `anthropic/claude-3-5-haiku-20241022` | Fast responses |

## How It Works

### OpenClaw's Approach

OpenClaw's `models auth setup-token --provider anthropic` command:
1. Prompts user to run `claude setup-token`
2. Validates and stores the token
3. Configures OpenClaw to use token authentication

### LiteLLM's Implementation

We've implemented the same flow:

```python
# In OpenClaw:
await modelsAuthSetupTokenCommand({ provider: "anthropic" }, runtime)

# In LiteLLM:
from litellm.llms.anthropic_token.auth import setup_token_interactive
setup_token_interactive()
```

Both store tokens in a profile-based JSON file with the same structure.

## Comparison: Two Authentication Methods

### Option A: API Key (Traditional)

```python
import os
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

completion(model="anthropic/claude-3-5-sonnet-20241022", ...)
```

**Pros:**
- Simple to set up
- Well documented
- Works everywhere

**Cons:**
- Need to manage API keys securely
- Keys can expire or be revoked
- Requires separate key management

### Option B: Setup Token (OpenClaw-style)

```python
# No environment variables needed!
# Token automatically loaded from ~/.litellm/anthropic-tokens.json

completion(model="anthropic/claude-3-5-sonnet-20241022", ...)
```

**Pros:**
- No API key management
- Uses your Claude subscription
- Same method as Claude CLI
- Compatible with OpenClaw workflows

**Cons:**
- Requires Claude CLI installation
- Token may need periodic renewal
- Less commonly documented

## Token Storage

Tokens are stored in `~/.litellm/anthropic-tokens.json`:

```json
{
  "profiles": {
    "anthropic:manual": {
      "type": "token",
      "provider": "anthropic",
      "token": "your-setup-token-here",
      "expires": 1770065400311
    }
  }
}
```

**Security:**
- File permissions set to `600` (owner read/write only)
- Tokens are stored in plain text (like OpenClaw)
- Expires timestamp is optional

## Token Expiration

If you set an expiration, LiteLLM will:
1. Check token expiration before each request
2. Warn if token is expired
3. Automatically skip expired tokens

To refresh:
```bash
# Generate new token
claude setup-token

# Re-run setup
poetry run python tests/test_anthropic_setup_token.py
```

## Multiple Profiles

You can store multiple tokens:

```python
from litellm.llms.anthropic_token.auth import store_anthropic_token

# Personal account
store_anthropic_token(token1, profile_id="anthropic:personal")

# Work account
store_anthropic_token(token2, profile_id="anthropic:work")
```

Then use specific profiles:
```python
# TODO: Implement profile selection in completion()
```

## Troubleshooting

### "Claude CLI not found"

```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-cli

# Verify
claude --version
```

### "Token expired"

```bash
# Generate new token
claude setup-token

# Update stored token
poetry run python tests/test_anthropic_setup_token.py
```

### "Invalid token"

- Ensure you copied the complete token from `claude setup-token`
- Tokens should not contain whitespace
- Minimum length: 20 characters

### "Permission denied"

```bash
# Fix file permissions
chmod 600 ~/.litellm/anthropic-tokens.json
```

## Compatibility with OpenClaw

This implementation matches OpenClaw's token authentication:

| Feature | OpenClaw | LiteLLM |
|---------|----------|---------|
| Token source | `claude setup-token` | ✅ Same |
| Storage format | JSON profiles | ✅ Same |
| Validation | Custom validator | ✅ Same |
| Expiration | Optional | ✅ Same |
| Multiple profiles | Yes | ✅ Yes |

You can even **share tokens** between OpenClaw and LiteLLM by using compatible storage locations.

## Future Enhancements

- [ ] Auto-detect OpenClaw token storage
- [ ] Share tokens between OpenClaw and LiteLLM
- [ ] Automatic token refresh
- [ ] Profile selection in completion()
- [ ] CLI command: `litellm auth setup-token --provider anthropic`

## References

- [OpenClaw Anthropic Setup](https://docs.openclaw.ai/providers/anthropic)
- [Claude CLI Documentation](https://docs.anthropic.com/claude/docs/cli)
- [Anthropic API Documentation](https://docs.anthropic.com/claude/reference)

## Support

For issues or questions:
- LiteLLM: https://github.com/BerriAI/litellm/issues
- Claude CLI: https://github.com/anthropics/anthropic-sdk-python
