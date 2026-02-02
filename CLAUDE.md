# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

LiteLLM uses **Poetry** for dependency management and the Makefile for common tasks.

### Installation
- `make install-dev` - Install core development dependencies
- `make install-proxy-dev` - Install proxy development dependencies with full feature set
- `make install-dev-ci` - Install dev dependencies (CI-compatible, pins OpenAI version)
- `make install-proxy-dev-ci` - Install proxy dev dependencies (CI-compatible)
- `make install-test-deps` - Install all test dependencies

### Testing
- `make test` - Run all tests
- `make test-unit` - Run unit tests (tests/test_litellm) with 4 parallel workers
- `make test-integration` - Run integration tests (excludes unit tests)
- `make test-unit-helm` - Run Helm unit tests
- `poetry run pytest tests/path/to/test_file.py -v` - Run specific test file
- `poetry run pytest tests/path/to/test_file.py::test_function -v` - Run specific test function

### Code Quality
- `make lint` - Run all linting (Ruff, MyPy, Black, circular imports, import safety)
- `make format` - Apply Black code formatting
- `make format-check` - Check Black formatting without applying (matches CI)
- `make lint-ruff` - Run Ruff linting only
- `make lint-mypy` - Run MyPy type checking only
- `make check-circular-imports` - Check for circular imports
- `make check-import-safety` - Check import safety

### Running the Proxy Server Locally
- `poetry run litellm --config config.yaml` - Start proxy with config file
- `poetry run litellm --model gpt-4o` - Quick start with single model
- `python litellm/proxy/proxy_cli.py` - Start proxy backend (alternative)

### Docker Development
- `docker-compose up db prometheus` - Start database and Prometheus services only
- `docker-compose up` - Start all services (litellm, database, Prometheus)

### Frontend Development (UI Dashboard)
Navigate to `ui/litellm-dashboard`:
- `npm install` - Install dependencies
- `npm run dev` - Start development server

## Contributing Requirements

### Contributor License Agreement (CLA)
**IMPORTANT:** All contributors must sign the [Contributor License Agreement](https://cla-assistant.io/BerriAI/litellm) before their PRs can be merged. Sign the CLA early to avoid delays in the review process.

### Pull Request Requirements
- **Add at least 1 test** in `tests/test_litellm/` (hard requirement)
- **Pass all checks**: `make test-unit` and `make lint` must pass
- **Keep PRs focused**: Address one specific problem per PR
- **Follow test file naming**: Mirror the structure of `litellm/` directory
  - Example: `litellm/proxy/caching_routes.py` → `tests/test_litellm/proxy/test_caching_routes.py`

### GitHub Issue & PR Templates
**Bug Reports** (`.github/ISSUE_TEMPLATE/bug_report.yml`):
- Describe what happened vs. what you expected
- Include relevant log output
- Specify your LiteLLM version

**Feature Requests** (`.github/ISSUE_TEMPLATE/feature_request.yml`):
- Describe the feature clearly
- Explain the motivation and use case

## Architecture Overview

LiteLLM is a unified interface for 100+ LLM providers with two main components:

### Core Library (`litellm/`)
- **Main entry point**: `litellm/main.py` - Contains core `completion()` and `acompletion()` functions
- **Provider implementations**: `litellm/llms/` - Each provider has its own subdirectory (100+ providers)
- **Router system**: `litellm/router.py` + `litellm/router_utils/` - Load balancing, fallback logic, and deployment management
- **Type definitions**: `litellm/types/` - Pydantic v2 models and type hints for all APIs
- **Integrations**: `litellm/integrations/` - Third-party observability (Langfuse, MLflow), caching, logging
- **Caching**: `litellm/caching/` - Multiple cache backends (Redis, in-memory, S3, DiskCache)
- **Cost tracking**: `litellm/cost_calculator.py` - Token usage and cost calculation across providers
- **Utilities**: `litellm/utils.py` - Common utilities, model mapping, parameter transformation

### Proxy Server (`litellm/proxy/`)
The proxy is a FastAPI application that acts as a centralized AI Gateway.

- **Main server**: `proxy_server.py` - FastAPI application with all endpoints
- **CLI entry**: `proxy_cli.py` - Command-line interface for starting the proxy
- **Authentication**: `auth/` - API key management, JWT, OAuth2, SSO (via fastapi-sso)
- **Database**: `db/` - Prisma ORM with PostgreSQL/SQLite support
  - Schema defined in `schema.prisma`
  - Migrations handled automatically by Prisma
- **Management endpoints**: `management_endpoints/` - Admin APIs for keys, teams, models, budgets
- **Pass-through endpoints**: `pass_through_endpoints/` - Provider-specific API forwarding
- **Guardrails**: `guardrails/` - Safety and content filtering hooks
- **Hooks**: `hooks/` - Custom pre-call and post-call processing
- **UI Dashboard**: Served from `_experimental/out/` (Next.js static build)
- **Configuration**: Example configs in `example_config_yaml/` directory

### Frontend (`ui/litellm-dashboard/`)
- Next.js application for the admin dashboard
- Build output served by proxy at `/_experimental/out/`

## Key Patterns

### Provider Implementation
New LLM providers are added in `litellm/llms/<provider_name>/`:
- Providers inherit from base classes in `litellm/llms/base.py`
- Each provider implements transformation functions for:
  - Request formatting (OpenAI format → provider format)
  - Response formatting (provider format → OpenAI format)
- Support both sync and async operations (`completion()` and `acompletion()`)
- Handle streaming responses and function/tool calling
- Provider-specific parameters defined in constants

### Error Handling
- Provider-specific exceptions mapped to OpenAI-compatible errors (defined in `exceptions.py`)
- Fallback logic handled by Router system with configurable retries
- Comprehensive logging through `litellm/_logging.py` with debug mode support
- Set `LITELLM_LOG=DEBUG` environment variable for detailed logging

### Configuration
- **Proxy Server**: YAML config files (see `litellm/proxy/example_config_yaml/` for examples)
- **Environment Variables**: API keys, credentials, and feature flags
- **Database Schema**: Managed via Prisma (`litellm/proxy/schema.prisma`)
  - Run `prisma generate` after schema changes
  - Run `prisma migrate dev` to create migrations

## Development Notes

### Code Style
- **Black** formatter for consistent code formatting
- **Ruff** for linting and code quality checks
- **MyPy** for static type checking
- **Pydantic v2** for data validation and serialization
- Async/await patterns throughout codebase
- Type hints required for all public APIs
- Follows [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

### Testing Strategy
- **Unit tests**: `tests/test_litellm/` - Mirrors structure of `litellm/` directory
  - Must use mocked responses, no real API calls
  - Run with `make test-unit` (uses 4 parallel workers)
- **Integration tests**: `tests/llm_translation/` - Real provider API tests
- **Proxy tests**: `tests/proxy_unit_tests/` - Proxy-specific functionality
- **Load tests**: `tests/load_tests/` - Performance and stress testing
- All PRs must add at least 1 test in `tests/test_litellm/`

### Database Migrations (Prisma)
- Schema defined in `litellm/proxy/schema.prisma`
- After schema changes:
  1. `prisma generate` - Regenerate Prisma client
  2. `prisma migrate dev --name your_migration_name` - Create migration
- Always test migrations against both PostgreSQL and SQLite
- Database URL configured via `DATABASE_URL` environment variable

### Local Development Setup
1. **Install dependencies**: `make install-proxy-dev`
2. **Start services**: `docker-compose up db prometheus`
3. **Setup database**: `prisma generate && prisma db push` (if needed)
4. **Start proxy**: `poetry run litellm --config config.yaml`
5. **Start UI** (optional): `cd ui/litellm-dashboard && npm run dev`

### Enterprise Features
- Enterprise-specific code in `enterprise/` directory (symlinked in `litellm/proxy/`)
- Optional features enabled via environment variables
- Separate licensing and authentication for enterprise features
- Available via litellm-enterprise package