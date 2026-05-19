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

### Rate limiting (visual CAPTCHA)

DuckDuckGo aggressively rate-limits requests from a single IP. When triggered, DDG returns a visual CAPTCHA page ("Unfortunately, bots use DuckDuckGo too — Select all squares containing a duck") instead of search results.

**Symptoms:** The tool returns `No results found` for all queries, even simple ones.

**Why it happens:** DuckDuckGo detects repeated searches from the same source and challenges them. This MCP makes a real HTTP request (via the `duckduckgo-search` library), and DDG treats it like any other browser request. Too many searches = CAPTCHA.

**Fix:** Wait a few hours. The rate limit expires automatically. Spread out searches to avoid triggering it. There is no way to solve the visual CAPTCHA programmatically.

### Inaccurate results for compound queries

Some compound queries (e.g., "nvidia mgx") may return generic results instead of specific ones. The `duckduckgo-search` library processes the query through DDG's HTML endpoint, and DDG's matching algorithm may prioritize different terms or return category pages.

**Workaround:** Use more specific query terms, or try different regions.

### Library deprecation warning

The `duckduckgo-search` Python package has been renamed to `ddgs`. Using the old import produces a `RuntimeWarning`:
```
RuntimeWarning: This package (`duckduckgo_search`) has been renamed to `ddgs`! Use `pip install ddgs` instead.
```

This is cosmetic and does not affect functionality. It will be updated in a future release.

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
