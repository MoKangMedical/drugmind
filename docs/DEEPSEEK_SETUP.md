# DeepSeek LLM Setup

DrugMind now defaults to the DeepSeek OpenAI-compatible API for text-model calls.

## Required environment

```bash
export LLM_PROVIDER=deepseek
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_API_KEY=your-deepseek-api-key
export LLM_MODEL=deepseek-v4-pro
```

Equivalent DeepSeek-specific variables are also supported:

```bash
export DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
export DEEPSEEK_API_KEY=your-deepseek-api-key
export DEEPSEEK_MODEL=deepseek-v4-pro
```

`LLM_*` takes precedence over `DEEPSEEK_*`.

## Security

Do not commit real API keys. Put the production key in server environment variables or a private `.env` file only.

## Compatibility

Older code paths that import `get_mimo_client()` are still supported as aliases, but they now return the configured DeepSeek/OpenAI-compatible client.
