# ddg-search-mcp

DuckDuckGo Search MCP Server. Uses DuckDuckGo's HTML search via the `duckduckgo-search` library — no API key required.

## Features

- Searches DuckDuckGo and returns results with titles, URLs, and snippets
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
            "command": ["uvx", "--from", "git+https://github.com/Albertous007/ddg-search-mcp", "python", "server.py"],
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
            "command": ["uvx", "--from", "git+https://github.com/Albertous007/ddg-search-mcp", "python", "server.py"],
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

### Rate limiting

DuckDuckGo may temporarily block requests if too many searches are made in a short period. When rate-limited, DDG returns a visual CAPTCHA ("Select all squares containing a duck") that cannot be solved programmatically.

**Symptoms:** `No results found` or empty responses for all queries.

**Fix:** Wait a few hours. The rate limit expires automatically. Spread out searches to avoid triggering it.

### HTML dependency

This MCP relies on the `duckduckgo-search` library which scrapes DuckDuckGo's HTML. If DDG changes their HTML structure, the library may need to be updated. The library is actively maintained.

## Development

```bash
pip install mcp duckduckgo-search
python server.py
```

Test with MCP Inspector:

```bash
pip install mcp[cli]
mcp dev server.py
```

## Requirements

- Python 3.10+
- `mcp` (MCP Python SDK)
- `duckduckgo-search` (HTML scraping library)

## License

MIT
