"""
DuckDuckGo Search MCP Server.
Scrapes DuckDuckGo HTML results — no API key required.
"""

import asyncio
import logging
import os
import re
import sys
import time
import unicodedata
from urllib.parse import urlparse, unquote

from curl_cffi.requests import AsyncSession
import trafilatura
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ddg-search")

# ── Logger ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("ddg-search")

# ── Environment-based configuration ───────────────────────────────────────────

def _env_float(key: str, default: str) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        log.warning("Invalid %s='%s', using default %s", key, raw, default)
        return float(default)

def _env_int(key: str, default: str) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return int(default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        log.warning("Invalid %s='%s', using default %s", key, raw, default)
        return int(default)

# ── Constants ────────────────────────────────────────────────────────────────

DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MAX_CONTENT_CHARS = _env_int("DDG_MAX_CONTENT_CHARS", "6000")
MAX_SNIPPET_CHARS = _env_int("DDG_MAX_SNIPPET_CHARS", "400")
PAGE_FETCH_TIMEOUT = _env_float("DDG_PAGE_FETCH_TIMEOUT", "8.0")
SEARCH_TIMEOUT = _env_float("DDG_SEARCH_TIMEOUT", "12.0")
MAX_RESULTS_CAP = _env_int("DDG_MAX_RESULTS", "10")
SEARCH_DELAY = _env_float("DDG_SEARCH_DELAY", "3.0")

_last_search_time = 0.0
_fallback_triggered: bool = False
_search_lock = asyncio.Lock()

SKIP_FETCH_DOMAINS = {
    "youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com",
    "facebook.com", "linkedin.com", "tiktok.com", "reddit.com",
    "jstor.org", "researchgate.net", "academia.edu",
}

_LOG_LEVEL = os.environ.get("DDG_LOG_LEVEL", "INFO").upper()
log.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

# ── Region validation ─────────────────────────────────────────────────────────

REGION_PATTERN = re.compile(r"^[a-z]{2}-[a-z]{2}$")

def validate_region(region: str) -> str:
    region = region.lower().strip()
    if region == "wt-wt" or REGION_PATTERN.match(region):
        return region
    log.warning("Unknown region code '%s', defaulting to wt-wt", region)
    return "wt-wt"

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
        key = re.sub(r"\W+", "", stripped.lower())
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

async def fetch_page(session: AsyncSession, url: str) -> tuple[str, bool]:
    if should_skip_fetch(url):
        log.info("Skipping %s (blocklisted domain)", url)
        return "", False
    log.debug("Fetching %s", url)
    try:
        resp = await session.get(
            url,
            timeout=PAGE_FETCH_TIMEOUT,
            allow_redirects=True,
            headers=HEADERS,
        )
        if resp.status_code != 200:
            log.warning("HTTP %d fetching %s", resp.status_code, url)
            return "", False
        ct = resp.headers.get("content-type", "")
        if "text/html" not in ct:
            log.warning("Non-HTML content (%s) at %s", ct, url)
            return "", False
        extracted = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        )
        if not extracted or len(extracted.strip()) < 100:
            log.warning("Content too short (%d chars) at %s",
                        len(extracted.strip()) if extracted else 0, url)
            return "", False
        cleaned = clean_content(extracted)
        return cleaned[:MAX_CONTENT_CHARS], True
    except Exception as e:
        log.error("Error fetching %s: %s", url, e)
        return "", False


# ── DuckDuckGo search ────────────────────────────────────────────────────────

async def ddg_search(session: AsyncSession, query: str, num: int, region: str = "wt-wt") -> list[dict]:
    global _last_search_time, _fallback_triggered
    _fallback_triggered = False

    log.info("Searching for '%s' (region=%s, count=%d)", query, region, num)

    for attempt in range(2):
        async with _search_lock:
            now = time.time()
            elapsed = now - _last_search_time
            if elapsed < SEARCH_DELAY:
                wait = SEARCH_DELAY - elapsed
                log.info("Rate limit: sleeping %.1fs", wait)
                await asyncio.sleep(wait)

            try:
                resp = await session.post(
                    DDG_LITE_URL,
                    data={"q": query, "kl": region},
                    headers=HEADERS,
                    timeout=SEARCH_TIMEOUT,
                )
                _last_search_time = time.time()

                if resp.status_code not in (200, 202):
                    log.warning("HTTP %d on search attempt %d/2", resp.status_code, attempt + 1)
                    continue

                if "ddg-captcha" in resp.text.lower() or "captcha" in resp.text.lower():
                    log.warning("Captcha detected (attempt %d/2)", attempt + 1)
                    continue

                results = parse_html(resp.text, num)
                if results:
                    log.debug("Found %d results for '%s'", len(results), query)
                    return results

                if attempt == 0:
                    log.warning("0 results parsed for '%s', retrying...", query)
                    await asyncio.sleep(1.0)
                    continue

                log.warning("0 results for '%s' after retry, exhausted", query)
                return []
            except Exception as e:
                log.error("Search attempt %d/2 failed: %s", attempt + 1, e)
                if attempt == 0:
                    continue
                return []
    log.warning("All search attempts exhausted for '%s'", query)
    return []


# ── HTML parsing ─────────────────────────────────────────────────────────────

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
    global _fallback_triggered
    soup = BeautifulSoup(html, "html.parser")
    results = []

    result_links = soup.select("a.result-link")
    for a in result_links:
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
        parent_tr = a.find_parent("tr")
        if parent_tr:
            next_tr = parent_tr.find_next_sibling("tr")
            if next_tr:
                snippet_el = next_tr.select_one(".result-snippet")
                if snippet_el:
                    raw = snippet_el.get_text(strip=True)
                    raw = re.sub(r'([a-záéíóúñ])(\d)', r'\1 \2', raw, flags=re.I)
                    snippet = raw[:MAX_SNIPPET_CHARS]

        results.append({"title": title, "url": real_url, "snippet": snippet})

    log.debug("Lite parser found %d results", len(results))

    if not results:
        _fallback_triggered = True
        log.warning("Lite parser returned 0 results, falling back to legacy parser")
        result_elements = soup.select(".result, .results_links, .result__body")
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
            if snippet_el:
                raw = snippet_el.get_text(strip=True)
                raw = re.sub(r'([a-záéíóúñ])(\d)', r'\1 \2', raw, flags=re.I)
                snippet = raw[:MAX_SNIPPET_CHARS]
            else:
                snippet = ""
            results.append({"title": title, "url": real_url, "snippet": snippet})

    return results


# ── MCP Tool ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def search(query: str, count: int = 10, region: str = "wt-wt") -> str:
    """Search DuckDuckGo and return web results with titles, URLs, and snippets.

    Scrapes DuckDuckGo Lite directly (no API key needed). For each result,
    the full page content is fetched and extracted, falling back to snippet
    only when the page cannot be retrieved.

    Args:
        query: Search terms.
        count: Max results (1-20, default 10).
        region: Region code (wt-wt = global, us-en = USA, es-es = Spain, etc.).
    """
    count = max(1, min(count, MAX_RESULTS_CAP))
    region = validate_region(region)

    try:
        async with AsyncSession(impersonate="chrome131", headers=HEADERS) as session:
            results = await ddg_search(session, query, count, region=region)
            if not results:
                log.warning("No results for '%s' (region=%s)", query, region)
                msg = f"No results found for: {query}"
                if _fallback_triggered:
                    msg += (
                        "\n\n\u26a0\ufe0f  DuckDuckGo may have changed their HTML structure."
                        "\n    If searches fail consistently, report at:"
                        "\n    https://github.com/Albertous007/ddg-search-mcp/issues"
                    )
                return msg

            fetch_tasks = [fetch_page(session, r["url"]) for r in results]
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
        log.info("Search: %d full + %d snippet results for '%s'",
                 len(full_results), len(fallback_results), query)
        return "\n\n".join(ordered)

    except Exception as e:
        log.error("Search failed: %s", e)
        return f"Search failed: {e}"


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
