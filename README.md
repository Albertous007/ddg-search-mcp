# ddg-search-mcp

DuckDuckGo Search MCP Server. Scrapes DuckDuckGo HTML directly — no API key or third-party library needed.

## Features

- Searches DuckDuckGo and returns results with titles, URLs, and snippets
- Full page content extraction via Trafilatura (falls back to snippet on failure)
- Concurrent page fetching for low latency
- Region support (global, country-specific)
- No API key or authentication needed
- Built with FastMCP (Python MCP SDK)
- Cross-platform (Windows, Linux, macOS)

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
| `region`  | No       | wt-wt   | Region: wt-wt (global), us-en (USA), mx-es (Mexico), etc. |

## Cross-platform

Works on Windows, Linux, and macOS. Requires only Python 3.10+.

| OS | Setup |
|----|-------|
| Windows | `pip install -r requirements.txt` |
| Linux | `pip install -r requirements.txt` |
| macOS | `pip install -r requirements.txt` |

## Known Issues

### Rate limiting (visual CAPTCHA)

DuckDuckGo aggressively rate-limits requests from a single IP. When triggered, DDG returns a visual CAPTCHA page ("Unfortunately, bots use DuckDuckGo too — Select all squares containing a duck") instead of search results.

**Symptoms:** The tool returns `No results found` for all queries, even simple ones.

**Why it happens:** DuckDuckGo detects repeated searches from the same source and challenges them. This MCP makes direct HTTP requests to DDG's HTML endpoint, and DDG treats it like any other browser request. Too many searches = CAPTCHA.

**Fix:** Wait a few hours. The rate limit expires automatically. Spread out searches to avoid triggering it. There is no way to solve the visual CAPTCHA programmatically.

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
- `httpx` (HTTP client)
- `beautifulsoup4` (HTML parsing)
- `trafilatura` (content extraction)
- `mcp` (MCP Python SDK)

## License

MIT
