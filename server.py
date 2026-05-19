"""
DuckDuckGo Search MCP Server.
Scrapes DuckDuckGo HTML results — no API key required.
"""

from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

mcp = FastMCP("ddg-search")


@mcp.tool()
def search(query: str, count: int = 10, region: str = "wt-wt") -> str:
    """Search DuckDuckGo and return web results with titles, URLs, and snippets.

    Args:
        query: Search terms.
        count: Max results (1–20, default 10).
        region: Region code (wt-wt = global, us-en = USA, mx-es = Mexico, etc.).
    """
    count = max(1, min(count, 20))

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, max_results=count))
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return f"No results found for: {query}"

    output = []
    for i, r in enumerate(results, 1):
        output.append(f"{i}. {r['title']}")
        output.append(f"   {r['href']}")
        if r.get("body"):
            output.append(f"   {r['body']}")
        output.append("")

    return "\n".join(output)


if __name__ == "__main__":
    mcp.run(transport="stdio")
