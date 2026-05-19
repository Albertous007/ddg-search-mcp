# ddg-search-mcp

DuckDuckGo Search MCP Server. Uses DuckDuckGo's HTML search via the `duckduckgo-search` library — no API key required.

## Features

- Searches DuckDuckGo and returns results with titles, URLs, and snippets
- Region support (global, country-specific)
- No API key or authentication needed
- Built with FastMCP (Python MCP SDK)

## Usage with opencode

Add to your `opencode.json`:

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

## Tool: `search`

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query`   | Yes      | —       | Search terms |
| `count`   | No       | 10      | Max results (1–20) |
| `region`  | No       | wt-wt   | Region: wt-wt (global), us-en (USA), mx-es (Mexico), etc. |

## Installation

```bash
pip install -r requirements.txt
```

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
