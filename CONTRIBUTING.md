# Contributing to ddg-search-mcp

## Why this project exists

This MCP server was built for thesis research. It prioritizes:

- Robustness against DDG changes (dual parser with automatic fallback)
- Full page content extraction via trafilatura
- No API keys or accounts required

## When DDG changes their HTML

This is the most likely thing to break. If searches stop working:

1. Check if the parser warning appears in the search output
2. Open an issue with the exact error message
3. If you fixed it, send a pull request

## How to contribute

1. Fork the repository
2. Install in dev mode: `pip install -e .`
3. Run tests: `pytest`
4. Submit a PR with a clear description of the change

## Tests

```bash
pytest           # unit tests (no network required)
pytest -v        # verbose output
```

## Maintaining

This project is maintained by [@Albertous007](https://github.com/Albertous007).
If the repository becomes unmaintained, anyone is welcome to fork it or
request transfer to a community organization.
