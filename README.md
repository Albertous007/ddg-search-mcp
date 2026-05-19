# ddg-search-mcp

DuckDuckGo Search MCP Server. Scrapes DuckDuckGo Lite directly — no API key required. Highly robust against bot detection.

## Features

- **Advanced Anti-bot Protection**: Uses `curl_cffi` to mimic a real Chrome 131 TLS fingerprint (JA3), seamlessly bypassing most bot detection and CAPTCHA systems.
- **DuckDuckGo Lite**: Leverages the Lite version of DuckDuckGo for faster parsing and significantly higher reliability compared to the standard HTML version.
- **Smart Rate Limiting & Retries**: Integrated 3.0s delay between searches and automatic retry logic to ensure stable results even during intensive use.
- **Full Content Extraction**: Deep extraction of page content via `trafilatura` (with automatic snippet fallback on fetch failure).
- **Concurrent Processing**: Page content is fetched in parallel to minimize latency.
- **Full Region Support**: Real support for regional searches (e.g., `es-es` for Spain, `mx-es` for Mexico) using the native DuckDuckGo `kl` parameter.
- **Zero Configuration**: No API keys, accounts, or complex setup required.

## Installation

### Standard (recommended)

```bash
git clone https://github.com/Albertous007/ddg-search-mcp.git
cd ddg-search-mcp
pip install -r requirements.txt
```

### Alternative: using `uvx`

If you have [`uv`](https://docs.astral.sh/uv/) installed:

```bash
pip install uv   # one-time setup
```

Then use `uvx` directly in your config (no clone or pip install needed):

```json
{
    "mcp": {
        "ddg-search": {
            "type": "local",
            "command": ["uvx", "--from", "git+https://github.com/Albertous007/ddg-search-mcp@main", "python", "-m", "server"],
            "enabled": true
        }
    }
}
```

## Usage with opencode

Standard installation:

```json
{
    "mcp": {
        "ddg-search": {
            "type": "local",
            "command": ["python", "path\\to\\ddg-search-mcp\\server.py"],
            "enabled": true
        }
    }
}
```

With `uvx` (auto-installs dependencies):

```json
{
    "mcp": {
        "ddg-search": {
            "type": "local",
            "command": ["uvx", "--from", "git+https://github.com/Albertous007/ddg-search-mcp@main", "python", "-m", "server"],
            "enabled": true
        }
    }
}
```

## Tool: `search`

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query`   | Yes      | —       | Search terms |
| `count`   | No       | 10      | Max results (1–20) |
| `region`  | No       | wt-wt   | Region: wt-wt (global), us-en (USA), es-es (Spain), etc. |

## Cross-platform

Works on Windows, Linux, and macOS. Requires only Python 3.10+.

| OS | Setup |
|----|-------|
| Windows | `pip install -r requirements.txt` |
| Linux | `pip install -r requirements.txt` |
| macOS | `pip install -r requirements.txt` |

## Known Issues

### Rate limiting (CAPTCHA)

DuckDuckGo aggressively rate-limits requests from a single IP. This MCP uses **DuckDuckGo Lite**, **browser impersonation**, and an integrated **3.0s delay** with **auto-retries** to be as robust as possible.

**Symptoms:** The tool returns `No results found` for all queries.

**Fix:** If blocked, wait a few minutes. The rate limit expires automatically. The current 3.0s delay is designed to prevent this under normal usage.

### HTML structure changes

This MCP scrapes DuckDuckGo's HTML directly. If DDG changes their HTML structure, the parsing logic in `server.py` may need to be updated.

## Development

```bash
pip install -r requirements.txt
python server.py
```

Test with MCP Inspector:

```bash
pip install mcp[cli]
mcp dev server.py
```

## Requirements

- Python 3.10+
- `curl_cffi` (Advanced HTTP client with TLS fingerprinting)
- `beautifulsoup4` (HTML parsing)
- `trafilatura` (content extraction)
- `mcp` (MCP Python SDK)

## License

MIT
