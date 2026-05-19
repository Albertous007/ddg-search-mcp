"""
DuckDuckGo Search MCP Server.
Scrapes DuckDuckGo HTML results — no API key required.
"""

import asyncio
import hashlib
import re
import unicodedata
from urllib.parse import urlparse, unquote

import httpx
import trafilatura
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ddg-search")

# ── Constants ────────────────────────────────────────────────────────────────

DDG_HTML_URL = "https://html.duckduckgo.com/html/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MAX_CONTENT_CHARS = 6000
MAX_SNIPPET_CHARS = 400
PAGE_FETCH_TIMEOUT = 8.0
SEARCH_TIMEOUT = 12.0
MAX_RESULTS_CAP = 10

SKIP_FETCH_DOMAINS = {
    "youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com",
    "facebook.com", "linkedin.com", "tiktok.com", "reddit.com",
    "jstor.org", "researchgate.net", "academia.edu",
}

# ── URL utilities ────────────────────────────────────────────────────────────

def extract_real_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    if "//duckduckgo.com/y.js" in href or "uddg=/l/" in href:
        return None
    m = re.search(r'[?&]uddg=([^&]+)', href)
    if m:
        return unquote(m.group(1))
    if href.startswith(("http://", "https://")):
        return href
    return None


# ── Text utilities ───────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        key = hashlib.md5(re.sub(r"\W+", "", stripped.lower()).encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            out.append(line)
    return "\n".join(out)


def clean_content(raw: str) -> str:
    text = normalize(raw)
    text = dedupe_lines(text)
    lines = [
        l for l in text.splitlines()
        if not re.match(
            r"^\s*(share|tweet|follow us|subscribe|sign up|log in|cookie|privacy policy"
            r"|terms of service|all rights reserved|©|\d+ comments?)\s*$",
            l, re.IGNORECASE
        )
    ]
    return "\n".join(lines).strip()


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


def should_skip_fetch(url: str) -> bool:
    d = domain(url)
    return any(d == skip or d.endswith("." + skip) for skip in SKIP_FETCH_DOMAINS)


# ── Page fetcher ─────────────────────────────────────────────────────────────

async def fetch_page(client: httpx.AsyncClient, url: str) -> tuple[str, bool]:
    if should_skip_fetch(url):
        return "", False
    try:
        resp = await client.get(
            url,
            timeout=PAGE_FETCH_TIMEOUT,
            follow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            return "", False
        ct = resp.headers.get("content-type", "")
        if "text/html" not in ct:
            return "", False
        extracted = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        )
        if not extracted or len(extracted.strip()) < 100:
            return "", False
        cleaned = clean_content(extracted)
        return cleaned[:MAX_CONTENT_CHARS], True
    except (httpx.TimeoutException, httpx.ConnectError):
        return "", False
    except Exception:
        return "", False


# ── DuckDuckGo search ────────────────────────────────────────────────────────

async def ddg_search(client: httpx.AsyncClient, query: str, num: int) -> list[dict]:
    try:
        resp = await client.post(
            DDG_HTML_URL,
            data={"q": query, "kl": "wt-wt"},
            headers=HEADERS,
            timeout=SEARCH_TIMEOUT,
        )
        if resp.status_code not in (200, 202):
            return []
        return parse_html(resp.text, num)
    except Exception:
        return []


def is_ad_element(tag) -> bool:
    classes = tag.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    class_str = " ".join(classes)
    if "badge--ad" in class_str or "result--ad" in class_str:
        return True
    parent = tag.parent
    if parent:
        pc = parent.get("class", [])
        if isinstance(pc, str):
            pc = pc.split()
        if "badge--ad" in " ".join(pc) or "result--ad" in " ".join(pc):
            return True
    return False


def parse_html(html: str, num: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    result_elements = soup.select(".result, .results_links, .result__body")

    if not result_elements:
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            real_url = extract_real_url(href)
            if not real_url:
                continue
            title = a.get_text(strip=True)
            if not title:
                continue
            snippet = ""
            parent = a.find_parent()
            if parent:
                snippet_el = parent.select_one(".result__snippet")
                if snippet_el:
                    snippet = snippet_el.get_text(strip=True)[:MAX_SNIPPET_CHARS]
            results.append({"title": title, "url": real_url, "snippet": snippet})
            if len(results) >= num:
                break
        return results

    for el in result_elements:
        if len(results) >= num:
            break
        if is_ad_element(el):
            continue
        a = el.select_one("a.result__a")
        if not a:
            a = el.select_one("a[href]")
        if not a:
            continue
        href = a.get("href", "")
        real_url = extract_real_url(href)
        if not real_url:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        snippet_el = el.select_one(".result__snippet")
        snippet = snippet_el.get_text(strip=True)[:MAX_SNIPPET_CHARS] if snippet_el else ""
        results.append({"title": title, "url": real_url, "snippet": snippet})

    if not results:
        for a in soup.select("a.result__a"):
            if len(results) >= num:
                break
            href = a.get("href", "")
            real_url = extract_real_url(href)
            if not real_url:
                continue
            title = a.get_text(strip=True)
            if not title:
                continue
            snippet = ""
            parent = a.find_parent()
            if parent:
                se = parent.select_one(".result__snippet")
                if se:
                    snippet = se.get_text(strip=True)[:MAX_SNIPPET_CHARS]
            results.append({"title": title, "url": real_url, "snippet": snippet})

    return results


# ── MCP Tool ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def search(query: str, count: int = 10, region: str = "wt-wt") -> str:
    """Search DuckDuckGo and return web results with titles, URLs, and snippets.

    Scrapes DuckDuckGo HTML directly (no API key needed). For each result,
    the full page content is fetched and extracted, falling back to snippet
    only when the page cannot be retrieved.

    Args:
        query: Search terms.
        count: Max results (1–20, default 10).
        region: Region code (wt-wt = global, us-en = USA, mx-es = Mexico, etc.).
    """
    count = max(1, min(count, 20))

    try:
        async with httpx.AsyncClient(headers=HEADERS) as client:
            results = await ddg_search(client, query, count)
            if not results:
                return f"No results found for: {query}"

            fetch_tasks = [fetch_page(client, r["url"]) for r in results]
            page_data = await asyncio.gather(*fetch_tasks)

        full_results = []
        fallback_results = []

        for result, (content, is_full) in zip(results, page_data):
            title = result["title"]
            url = result["url"]
            snippet = result["snippet"]

            if is_full:
                entry = (
                    f"{len(full_results) + 1}. {title}\n"
                    f"   URL: {url}\n"
                    f"   {content}"
                )
                full_results.append(entry)
            else:
                body = snippet if snippet else "_Page content unavailable._"
                entry = (
                    f"{len(full_results) + len(fallback_results) + 1}. {title}\n"
                    f"   URL: {url}\n"
                    f"   {body}"
                )
                fallback_results.append(entry)

        ordered = full_results + fallback_results
        return "\n\n".join(ordered)

    except Exception as e:
        return f"Search failed: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
