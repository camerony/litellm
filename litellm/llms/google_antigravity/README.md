# Google Antigravity Provider

Google Antigravity is Google's internal AI development platform that provides access to both Gemini and Claude models through a unified API.

## Features

- ✅ OAuth 2.0 PKCE authentication (CLI + Web UI)
- ✅ Automatic token refresh with file locking
- ✅ Project ID retrieval from Google's loadCodeAssist API
- ✅ Support for both streaming and non-streaming responses
- ✅ Thinking configuration (LOW, MEDIUM, HIGH levels)
- ✅ Endpoint fallback (Sandbox → Production)
- ✅ Support for Gemini and Claude models

## Authentication

### CLI Authentication

```bash
# Interactive OAuth flow
litellm --provider google_antigravity

# The CLI will:
# 1. Start a local OAuth server
# 2. Open browser for Google OAuth consent
# 3. Retrieve access token, refresh token, and project ID
# 4. Save credentials to ~/.antigravity/auth-profiles.json
```

### Web UI Authentication

1. Navigate to the LiteLLM dashboard
2. Click "Add Model"
3. Select "Google Antigravity"
4. Click "Authenticate with Google"
5. Complete OAuth flow
6. Credentials are stored in auth-profiles.json

### Credentials Storage

```json
{
  "profiles": {
    "user@gmail.com": {
      "type": "oauth",
      "provider": "google-antigravity",
      "access": "ya29...",
      "refresh": "1//01...",
      "expires": 1770065400311,
      "email": "user@gmail.com",
      "projectId": "your-project-id"
    }
  }
}
```

## Supported Models

### Gemini Models

| Model Name | API Model | Thinking Level | Description |
|------------|-----------|----------------|-------------|
| `gemini-3-flash` | `gemini-3-flash` | Default | Fast responses, automatic thinking |
| `gemini-3-pro-low` | `gemini-3-flash` | LOW | Flash with reduced thinking |
| `gemini-3-pro-medium` | `gemini-3-flash` | MEDIUM | Flash with medium thinking |
| `gemini-3-pro-high` | `gemini-3-flash` | HIGH | Flash with maximum thinking |

**Note:** There is NO separate `gemini-3-pro` base model on Google's API. The "pro" variants are `gemini-3-flash` with different thinking configurations.

### Claude Models

| Model Name | API Model | Status |
|------------|-----------|--------|
| `claude-sonnet-4-5` | `claude-sonnet-4-5` | ⚠️ Requires premium subscription |
| `claude-opus-4-5-thinking` | `claude-opus-4-5-thinking` | ⚠️ Rate limited for most users |

## Usage Examples

### Basic Completion

```python
from litellm import completion

response = completion(
    model="google_antigravity/gemini-3-flash",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### With Thinking Configuration

```python
# Use Pro-High for complex reasoning
response = completion(
    model="google_antigravity/gemini-3-pro-high",
    messages=[{"role": "user", "content": "Solve this step by step: ..."}],
    max_tokens=500
)

# Access thinking token usage
print(f"Thinking tokens: {response.usage.total_tokens - response.usage.prompt_tokens - response.usage.completion_tokens}")
```

### Streaming

```python
from litellm import completion

response = completion(
    model="google_antigravity/gemini-3-flash",
    messages=[{"role": "user", "content": "Write a story"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Async Usage

```python
from litellm import acompletion
import asyncio

async def main():
    response = await acompletion(
        model="google_antigravity/gemini-3-flash",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

## Model Name Mapping

The provider automatically handles model name transformations:

```python
# User specifies:
model="google_antigravity/gemini-3-pro-high"

# Handler transforms to:
{
  "model": "gemini-3-flash",  # Base model
  "request": {
    "generationConfig": {
      "thinkingConfig": {
        "includeThoughts": true,
        "thinkingLevel": "HIGH"  # Extracted from suffix
      }
    }
  }
}
```

## Thinking Configuration

### Automatic Suffix Detection

The handler automatically detects thinking levels from model name suffixes:

- `*-high` → `thinkingLevel: "HIGH"`
- `*-medium` → `thinkingLevel: "MEDIUM"`
- `*-low` → `thinkingLevel: "LOW"`

### Manual Configuration

```python
response = completion(
    model="google_antigravity/gemini-3-flash",
    messages=[{"role": "user", "content": "..."}],
    reasoning_effort="high"  # LiteLLM's standard parameter
)
```

### Thinking Token Usage

Different thinking levels use different amounts of thinking tokens:

| Level | Thinking Tokens (approx) | Use Case |
|-------|--------------------------|----------|
| Default | 30-100 | General queries |
| LOW | 200-400 | Simple reasoning |
| MEDIUM | 400-800 | Moderate complexity |
| HIGH | 800-1500 | Complex reasoning |

## Configuration

### Proxy Configuration (YAML)

```yaml
model_list:
  - model_name: gemini-flash
    litellm_params:
      model: google_antigravity/gemini-3-flash

  - model_name: gemini-pro-high
    litellm_params:
      model: google_antigravity/gemini-3-pro-high

  - model_name: claude-sonnet
    litellm_params:
      model: google_antigravity/claude-sonnet-4-5
```

### Environment Variables

```bash
# Optional: Specify custom auth file location
export ANTIGRAVITY_AUTH_FILE=~/.config/antigravity/auth.json
```

## Endpoint Configuration

The provider uses a fallback strategy:

1. **Sandbox (Primary):** `https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:streamGenerateContent?alt=sse`
2. **Production (Fallback):** `https://cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse`

Retries on 404, 429, and 5xx errors with exponential backoff (3 attempts).

## Token Refresh

The provider automatically refreshes expired access tokens:

1. Checks token expiration before each request
2. Uses file locking to prevent race conditions
3. Refreshes token if expired or expiring within 5 minutes
4. Updates auth-profiles.json with new tokens

## Error Handling

| Status Code | Error | Meaning |
|-------------|-------|---------|
| 404 | Model Not Found | Invalid model name or endpoint |
| 429 | Rate Limited | Quota exhausted or model restricted |
| 403 | Forbidden | No license for this model |
| 500 | Server Error | Google API issue |

## Troubleshooting

### "Model not found" (404)

- Ensure you're using supported model names
- `gemini-3-pro` doesn't exist - use `gemini-3-flash` or `gemini-3-pro-high`

### "Rate limited" (429)

- Check your Google Cloud quota
- Some models (Claude) require premium subscription
- Wait and retry with exponential backoff

### "No valid credentials"

```bash
# Re-authenticate
litellm --provider google_antigravity --auth

# Or delete and recreate
rm ~/.antigravity/auth-profiles.json
litellm --provider google_antigravity
```

### Token refresh fails

- Check that refresh token hasn't been revoked
- Ensure auth-profiles.json has correct permissions (600)
- Re-authenticate if needed

## Architecture

### File Structure

```
litellm/llms/google_antigravity/
├── __init__.py              # Provider registration
├── auth.py                  # OAuth & token management (CLI)
├── chat/
│   └── handler.py          # Main completion handler
└── README.md               # This file

litellm/proxy/auth/
└── google_antigravity_auth_endpoints.py  # Web UI OAuth
```

### Request Flow

```
1. User calls completion()
2. Handler checks auth-profiles.json
3. Gets/refreshes access token
4. Fetches project ID (if needed)
5. Transforms model name & extracts thinking config
6. Constructs request body
7. Tries Sandbox endpoint
8. Falls back to Production if needed
9. Parses SSE response
10. Returns ModelResponse with usage
```

## Development

### Running Tests

```bash
# Test all models (except Opus)
poetry run pytest tests/test_all_models_except_opus.py -v

# Test OAuth flow
poetry run pytest tests/test_oauth_flow_validation.py -v

# Validate thinking levels
poetry run pytest tests/test_validate_thinking_levels.py -v
```

### Adding New Models

1. Add model name to supported list in handler.py
2. Add any model-specific headers (e.g., anthropic-beta)
3. Test with validation suite
4. Update documentation

## References

- [IMPLEMENTATION_PLAN.md](../../../IMPLEMENTATION_PLAN.md) - Original implementation plan
- [ANTIGRAVITY_FIX_SUMMARY.md](../../../ANTIGRAVITY_FIX_SUMMARY.md) - Model name mapping fix
- [ANTIGRAVITY_FINAL_STATUS.md](../../../ANTIGRAVITY_FINAL_STATUS.md) - Current status & validation

## Support

For issues or questions:
- Create an issue: https://github.com/BerriAI/litellm/issues
- Documentation: https://docs.litellm.ai
