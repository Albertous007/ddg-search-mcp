# ddg-search-mcp

[![PyPI version](https://img.shields.io/pypi/v/ddg-search-mcp)](https://pypi.org/project/ddg-search-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/ddg-search-mcp)](https://pypi.org/project/ddg-search-mcp/)
[![License](https://img.shields.io/pypi/l/ddg-search-mcp)](LICENSE)

DuckDuckGo Search MCP Server. Scrapes DuckDuckGo Lite directly — no API key required, no rate limits, robust anti-bot protection.

## Quick Start

```bash
pip install ddg-search-mcp
# or
uvx ddg-search-mcp
```

Add to your MCP client:

```json
{
    "mcpServers": {
        "ddg-search": {
            "command": "uvx",
            "args": ["ddg-search-mcp"]
        }
    }
}
```

## Features

- **Advanced Anti-bot Protection**: Uses `curl_cffi` to mimic a real Chrome 131 TLS fingerprint (JA3), seamlessly bypassing most bot detection and CAPTCHA systems.
- **Dual Parser Engine**: Primary parser for DuckDuckGo Lite HTML, with automatic legacy fallback if the structure changes.
- **Parser Health Warning**: If the primary parser fails and no results are found, a warning is included in the output with a link to report the issue.
- **Full Content Extraction**: Deep extraction of page content via `trafilatura` (with automatic snippet fallback on fetch failure).
- **Concurrent Processing**: Page content is fetched in parallel to minimize latency.
- **Full Region Support**: Regional searches (e.g., `es-es` for Spain, `mx-es` for Mexico) using the native DuckDuckGo `kl` parameter.
- **Zero Configuration**: No API keys, accounts, or complex setup required.
- **Structured Logging**: All server activity logs to stderr with configurable verbosity.
- **Environment Configuration**: All constants tunable via environment variables (see `.env.example`).

> **No SafeSearch filter**
>
> This server does **not** implement SafeSearch filtering. All search results
> are returned as-is from DuckDuckGo. If you need content filtering, consider
> [nickclyde/duckduckgo-mcp-server](https://github.com/nickclyde/duckduckgo-mcp-server)
> which supports `DDG_SAFE_SEARCH=STRICT | MODERATE | OFF`.
>
> This is a deliberate design choice — keeping the server simple, fast,
> and without feature creep.

## Installation

### From PyPI (recommended)

```bash
pip install ddg-search-mcp
```

### From source

```bash
git clone https://github.com/Albertous007/ddg-search-mcp.git
cd ddg-search-mcp
pip install -e .
```

## Usage with opencode

```json
{
    "mcp": {
        "ddg-search": {
            "type": "local",
            "command": ["python", "-m", "ddg_search_mcp"],
            "enabled": true
        }
    }
}
```

### With `uvx`

```json
{
    "mcp": {
        "ddg-search": {
            "type": "local",
            "command": ["uvx", "ddg-search-mcp"],
            "enabled": true
        }
    }
}
```

## Tool: `search`

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query`   | Yes      | —       | Search terms |
| `count`   | No       | 10      | Max results (1–10, configurable via `DDG_MAX_RESULTS`) |
| `region`  | No       | wt-wt   | Region: wt-wt (global), us-en (USA), es-es (Spain), etc. |

## Environment Variables

All settings are optional — defaults are shown below.

| Variable | Default | Description |
|----------|---------|-------------|
| `DDG_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DDG_SEARCH_DELAY` | `3.0` | Min seconds between search requests |
| `DDG_MAX_CONTENT_CHARS` | `6000` | Max chars of page content per result |
| `DDG_MAX_SNIPPET_CHARS` | `400` | Max chars of snippet fallback |
| `DDG_PAGE_FETCH_TIMEOUT` | `8.0` | Timeout (s) for fetching result pages |
| `DDG_SEARCH_TIMEOUT` | `12.0` | Timeout (s) for the search request itself |
| `DDG_MAX_RESULTS` | `10` | Max results returned per search (1–10) |

Copy `.env.example` to `.env` and customize, or set them directly in your environment.

## Cross-platform

Works on Windows, Linux, and macOS. Requires Python 3.10+.

## Known Issues

### Rate limiting (CAPTCHA)

DuckDuckGo aggressively rate-limits requests from a single IP. This MCP uses **DuckDuckGo Lite**, **browser impersonation**, and an integrated **3.0s delay** with **auto-retries** to be as robust as possible.

**Symptoms:** The tool returns `No results found` for all queries.

**Fix:** If blocked, wait a few minutes. The rate limit expires automatically.

### HTML structure changes

This MCP scrapes DuckDuckGo's HTML directly. If DDG changes their HTML structure, the parsing logic may need to be updated.

When a search returns no results and the parser structure is suspected to have changed, the output includes a warning:

```
⚠️  DuckDuckGo may have changed their HTML structure.
    If searches fail consistently, report at:
    https://github.com/Albertous007/ddg-search-mcp/issues
```

This warning only appears when both the primary and fallback parsers fail to extract results.

## Development

```bash
git clone https://github.com/Albertous007/ddg-search-mcp.git
cd ddg-search-mcp
pip install -e .
cp .env.example .env   # optional: tweak settings
python -m ddg_search_mcp
```

Test with MCP Inspector:

```bash
pip install mcp[cli]
mcp dev src/ddg_search_mcp/server.py
```

Run unit tests:

```bash
pip install pytest
pytest
```

## Requirements

- Python 3.10+
- `curl_cffi` (HTTP client with TLS fingerprinting)
- `beautifulsoup4` (HTML parsing)
- `trafilatura` (content extraction)
- `mcp` (MCP Python SDK)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

This is a personal project maintained by [@Albertous007](https://github.com/Albertous007).
If the repository becomes unmaintained, anyone is welcome to fork it.

## License

MIT
