\"\"\"
DuckDuckGo Search MCP Server.
Scrapes DuckDuckGo HTML results — no API key required.
\"\"\"

import asyncio
import hashlib
import re
import unicodedata
import time
from urllib.parse import urlparse, unquote

from curl_cffi.requests import AsyncSession
import trafilatura
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(\"ddg-search\")

# ── Constants ────────────────────────────────────────────────────────────────

DDG_LITE_URL = \"https://lite.duckduckgo.com/lite/\"

# Headers without User-Agent (curl_cffi handles impersonation automatically)
HEADERS = {
    \"Accept\": \"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\",
    \"Accept-Language\": \"en-US,en;q=0.5\",
}

MAX_CONTENT_CHARS = 6000
MAX_SNIPPET_CHARS = 400
PAGE_FETCH_TIMEOUT = 8.0
SEARCH_TIMEOUT = 12.0
MAX_RESULTS_CAP = 10

# Rate limiting: wait at least this many seconds between search requests
SEARCH_DELAY = 3.0
_last_search_time = 0.0
_search_lock = asyncio.Lock()

SKIP_FETCH_DOMAINS = {
    \"youtube.com\", \"youtu.be\", \"twitter.com\", \"x.com\", \"instagram.com\",
    \"facebook.com\", \"linkedin.com\", \"tiktok.com\", \"reddit.com\",
    \"jstor.org\", \"researchgate.net\", \"academia.edu\",
}

# ── URL utilities ────────────────────────────────────────────────────────────

def extract_real_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith(\"//\"):
        href = \"https:\" + href
    if \"//duckduckgo.com/y.js\" in href or \"uddg=/l/\" in href:
        return None
    m = re.search(r'[?&]uddg=([^&]+)', href)
    if m:
        return unquote(m.group(1))
    if href.startswith((\"http://\", \"https://\")):
        return href
    return None


# ── Text utilities ───────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    text = unicodedata.normalize(\"NFKC\", text)
    text = re.sub(r\"\\s{3,}\", \"\\n\\n\", text)
    text = re.sub(r\" {2,}\", \" \", text)
    return text.strip()


def dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(\"\")
            continue
        key = hashlib.md5(re.sub(r\"\\W+\", \"\", stripped.lower()).encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            out.append(line)
    return \"\\n\".join(out)


def clean_content(raw: str) -> str:
    text = normalize(raw)
    text = dedupe_lines(text)
    lines = [
        l for l in text.splitlines()
        if not re.match(
            r\"^\\s*(share|tweet|follow us|subscribe|sign up|log in|cookie|privacy policy\"
            r\"|terms of service|all rights reserved|©|\\d+ comments?)\\s*$\",
            l, re.IGNORECASE
        )
    ]
    return \"\\n\".join(lines).strip()


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix(\"www.\")
    except Exception:
        return url


def should_skip_fetch(url: str) -> bool:
    d = domain(url)
    return any(d == skip or d.endswith(\".\" + skip) for skip in SKIP_FETCH_DOMAINS)


# ── Page fetcher ─────────────────────────────────────────────────────────────

async def fetch_page(session: AsyncSession, url: str) -> tuple[str, bool]:
    if should_skip_fetch(url):
        return \"\", False
    try:
        resp = await session.get(
            url,
            timeout=PAGE_FETCH_TIMEOUT,
            follow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            return \"\", False
        ct = resp.headers.get(\"content-type\", \"\")
        if \"text/html\" not in ct:
            return \"\", False
        extracted = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        )
        if not extracted or len(extracted.strip()) < 100:
            return \"\", False
        cleaned = clean_content(extracted)
        return cleaned[:MAX_CONTENT_CHARS], True
    except Exception:
        return \"\", False


# ── DuckDuckGo search ────────────────────────────────────────────────────────

async def ddg_search(session: AsyncSession, query: str, num: int, region: str = \"wt-wt\") -> list[dict]:
    global _last_search_time
    
    for attempt in range(2):
        async with _search_lock:
            # Simple rate limiting
            now = time.time()
            elapsed = now - _last_search_time
            if elapsed < SEARCH_DELAY:
                await asyncio.sleep(SEARCH_DELAY - elapsed)
            
            try:
                # kl parameter defines the region in DuckDuckGo
                resp = await session.post(
                    DDG_LITE_URL,
                    data={\"q\": query, \"kl\": region},
                    headers=HEADERS,
                    timeout=SEARCH_TIMEOUT,
                )
                _last_search_time = time.time()
                
                if resp.status_code not in (200, 202):
                    continue
                
                if \"ddg-captcha\" in resp.text.lower() or \"captcha\" in resp.text.lower():
                    continue

                results = parse_html(resp.text, num)
                if results:
                    return results
                
                # If no results parsed, wait a bit and retry once
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                
                return []
            except Exception:
                if attempt == 0:
                    continue
                return []
    return []


def is_ad_element(tag) -> bool:
    classes = tag.get(\"class\", [])
    if isinstance(classes, str):
        classes = classes.split()
    class_str = \" \".join(classes)
    if \"badge--ad\" in class_str or \"result--ad\" in class_str:
        return True
    parent = tag.parent
    if parent:
        pc = parent.get(\"class\", [])
        if isinstance(pc, str):
            pc = pc.split()
        if \"badge--ad\" in \" \".join(pc) or \"result--ad\" in \" \".join(pc):
            return True
    return False


def parse_html(html: str, num: int) -> list[dict]:
    soup = BeautifulSoup(html, \"html.parser\")
    results = []

    # DuckDuckGo Lite structure:
    # <tr><td><a class=\"result-link\">Title</a></td></tr>
    # <tr><td class=\"result-snippet\">Snippet</td></tr>
    
    result_links = soup.select(\"a.result-link\")
    for a in result_links:
        if len(results) >= num:
            break
            
        href = a.get(\"href\", \"\")
        real_url = extract_real_url(href)
        if not real_url:
            continue
            
        title = a.get_text(strip=True)
        if not title:
            continue
            
        # The snippet is usually in the next <tr> or a sibling row
        snippet = \"\"
        parent_tr = a.find_parent(\"tr\")
        if parent_tr:
            next_tr = parent_tr.find_next_sibling(\"tr\")
            if next_tr:
                snippet_el = next_tr.select_one(\".result-snippet\")
                if snippet_el:
                    snippet = snippet_el.get_text(strip=True)[:MAX_SNIPPET_CHARS]
        
        results.append({\"title\": title, \"url\": real_url, \"snippet\": snippet})

    # Fallback to old parsing if Lite structure not found
    if not results:
        result_elements = soup.select(\".result, .results_links, .result__body\")
        for el in result_elements:
            if len(results) >= num:
                break
            if is_ad_element(el):
                continue
            a = el.select_one(\"a.result__a\")
            if not a:
                a = el.select_one(\"a[href]\")
            if not a:
                continue
            href = a.get(\"href\", \"\")
            real_url = extract_real_url(href)
            if not real_url:
                continue
            title = a.get_text(strip=True)
            if not title:
                continue
            snippet_el = el.select_one(\".result__snippet\")
            snippet = snippet_el.get_text(strip=True)[:MAX_SNIPPET_CHARS] if snippet_el else \"\"
            results.append({\"title\": title, \"url\": real_url, \"snippet\": snippet})

    return results


# ── MCP Tool ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def search(query: str, count: int = 10, region: str = \"wt-wt\") -> str:
    \"\"\"Search DuckDuckGo and return web results with titles, URLs, and snippets.

    Scrapes DuckDuckGo Lite directly (no API key needed). For each result,
    the full page content is fetched and extracted, falling back to snippet
    only when the page cannot be retrieved.

    Args:
        query: Search terms.
        count: Max results (1–20, default 10).
        region: Region code (wt-wt = global, us-en = USA, es-es = Spain, etc.).
    \"\"\"
    count = max(1, min(count, 20))

    try:
        # Impersonate Chrome 131 to bypass bot detection
        async with AsyncSession(impersonate=\"chrome131\", headers=HEADERS) as session:
            results = await ddg_search(session, query, count, region=region)
            if not results:
                return f\"No results found for: {query}\"

            fetch_tasks = [fetch_page(session, r[\"url\"]) for r in results]
            page_data = await asyncio.gather(*fetch_tasks)

        full_results = []
        fallback_results = []

        for result, (content, is_full) in zip(results, page_data):
            title = result[\"title\"]
            url = result[\"url\"]
            snippet = result[\"snippet\"]

            if is_full:
                entry = (
                    f\"{len(full_results) + 1}. {title}\\n\"
                    f\"   URL: {url}\\n\"
                    f\"   {content}\"
                )
                full_results.append(entry)
            else:
                body = snippet if snippet else \"_Page content unavailable._\"
                entry = (
                    f\"{len(full_results) + len(fallback_results) + 1}. {title}\\n\"
                    f\"   URL: {url}\\n\"
                    f\"   {body}\"
                )
                fallback_results.append(entry)

        ordered = full_results + fallback_results
        return \"\\n\\n\".join(ordered)

    except Exception as e:
        return f\"Search failed: {e}\"


if __name__ == \"__main__\":
    mcp.run(transport=\"stdio\")
