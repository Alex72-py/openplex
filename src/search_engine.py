"""
Web search engine for OpenPlex.
Uses DuckDuckGo HTML search — no API key needed, works on Termux.
Also fetches and extracts content from result pages for citation.
"""

import urllib.request
import urllib.parse
import urllib.error
import re
import html
import ssl
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


# Disable SSL verification for Termux compatibility (some certs are missing)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _make_request(url, timeout=10):
    """Make an HTTP GET request and return response text."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, Exception):
        return None


def search_duckduckgo(query, num_results=8):
    """
    Search DuckDuckGo HTML version and extract results.
    Returns list of dicts: [{title, url, snippet}, ...]
    """
    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    page = _make_request(search_url, timeout=15)
    if not page:
        return []

    results = []

    # Parse DuckDuckGo HTML results
    # Results are in <div class="result"> blocks
    result_blocks = re.findall(
        r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>',
        page,
        re.DOTALL
    )

    if not result_blocks:
        # Alternative pattern
        result_blocks = re.findall(
            r'<div class="links_main[^"]*"[^>]*>(.*?)</div>',
            page,
            re.DOTALL
        )

    # Extract links and snippets from the page more broadly
    # DuckDuckGo HTML uses <a class="result__a" href="...">title</a>
    links = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        page,
        re.DOTALL
    )

    snippets = re.findall(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        page,
        re.DOTALL
    )

    for i, (url, title) in enumerate(links[:num_results]):
        # Clean up the URL (DDG sometimes wraps them)
        if "uddg=" in url:
            url_match = re.search(r'uddg=([^&]+)', url)
            if url_match:
                url = urllib.parse.unquote(url_match.group(1))
        elif url.startswith("//"):
            url = "https:" + url

        # Clean HTML from title and snippet
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        clean_title = html.unescape(clean_title)

        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            snippet = html.unescape(snippet)

        # Skip ads (DDG ads route through duckduckgo.com/y.js)
        if "duckduckgo.com" in url:
            continue

        if url and clean_title and url.startswith("http"):
            results.append({
                "title": clean_title,
                "url": url,
                "snippet": snippet,
            })

    return results


def fetch_page_content(url, max_chars=3000):
    """
    Fetch a web page and extract its main text content.
    Returns cleaned text suitable for LLM context.
    """
    page = _make_request(url, timeout=10)
    if not page:
        return None

    # Remove script, style, nav, header, footer tags
    for tag in ["script", "style", "nav", "header", "footer", "aside", "iframe"]:
        page = re.sub(
            rf'<{tag}[^>]*>.*?</{tag}>',
            '',
            page,
            flags=re.DOTALL | re.IGNORECASE
        )

    # Remove HTML comments
    page = re.sub(r'<!--.*?-->', '', page, flags=re.DOTALL)

    # Try to find main content area
    main_content = None
    for pattern in [
        r'<main[^>]*>(.*?)</main>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
    ]:
        match = re.search(pattern, page, re.DOTALL | re.IGNORECASE)
        if match:
            main_content = match.group(1)
            break

    if not main_content:
        # Fall back to body
        body_match = re.search(r'<body[^>]*>(.*?)</body>', page, re.DOTALL | re.IGNORECASE)
        main_content = body_match.group(1) if body_match else page

    # Convert some HTML to readable text
    # Paragraphs and headings get newlines
    main_content = re.sub(r'<(p|h[1-6]|li|br|div)[^>]*>', '\n', main_content, flags=re.IGNORECASE)
    main_content = re.sub(r'</(p|h[1-6]|li|div)>', '\n', main_content, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', main_content)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()

    # Truncate to max_chars
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    return text if len(text) > 100 else None


def search_and_fetch(query, num_results=6, max_content_chars=2500):
    """
    Full search pipeline: search DuckDuckGo, then fetch content from top results.
    Returns enriched results with page content for citation.
    """
    results = search_duckduckgo(query, num_results=num_results)

    if not results:
        return []

    # Fetch content from results in parallel
    def fetch_one(result):
        content = fetch_page_content(result["url"], max_chars=max_content_chars)
        result["content"] = content
        return result

    enriched = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_one, r): r for r in results}
        for future in as_completed(futures, timeout=20):
            try:
                result = future.result()
                enriched.append(result)
            except Exception:
                pass

    # Sort back to original order
    url_order = {r["url"]: i for i, r in enumerate(results)}
    enriched.sort(key=lambda x: url_order.get(x["url"], 99))

    return enriched


def multi_search(queries, num_results_per=4, max_content_chars=2000):
    """
    Execute multiple search queries concurrently and combine results.
    Used for query decomposition — searches sub-queries in parallel.
    Deduplicates by URL.
    """
    if not queries:
        return []
        
    all_results = []
    seen_urls = set()

    with ThreadPoolExecutor(max_workers=min(len(queries), 6)) as executor:
        futures = {executor.submit(search_and_fetch, q, num_results_per, max_content_chars): q for q in queries}
        for future in as_completed(futures, timeout=30):
            try:
                results = future.result()
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_results.append(r)
            except Exception:
                continue

    return all_results


# ─────────────────────────────────────────────
# Tavily search adapters
# ─────────────────────────────────────────────

def _get_tavily_client(api_key):
    """Create a TavilyClient instance."""
    if TavilyClient is None:
        raise ImportError("tavily-python is not installed. Run: pip install tavily-python")
    return TavilyClient(api_key=api_key)


def _tavily_result_to_dict(result):
    """Convert a Tavily result to the standard {title, url, snippet, content} format."""
    return {
        "title": result.get("title", ""),
        "url": result.get("url", ""),
        "snippet": result.get("content", ""),
        "content": result.get("raw_content") or result.get("content", ""),
    }


def tavily_search_and_fetch(query, api_key, num_results=6, max_content_chars=2500):
    """
    Search using Tavily and return results in the same format as search_and_fetch().
    Tavily's include_raw_content populates 'content' directly, no separate fetch needed.
    """
    client = _get_tavily_client(api_key)
    try:
        response = client.search(
            query=query,
            max_results=num_results,
            search_depth="advanced",
            include_raw_content=True,
        )
    except Exception:
        return []

    results = []
    for r in response.get("results", []):
        item = _tavily_result_to_dict(r)
        # Truncate content to match existing behaviour
        if item["content"] and len(item["content"]) > max_content_chars:
            item["content"] = item["content"][:max_content_chars] + "..."
        results.append(item)

    return results


def tavily_multi_search(queries, api_key, num_results_per=4, max_content_chars=2000):
    """
    Execute multiple Tavily searches concurrently and combine results.
    Deduplicates by URL, matching multi_search() behaviour.
    """
    if not queries:
        return []

    all_results = []
    seen_urls = set()

    with ThreadPoolExecutor(max_workers=min(len(queries), 6)) as executor:
        futures = {
            executor.submit(tavily_search_and_fetch, q, api_key, num_results_per, max_content_chars): q
            for q in queries
        }
        for future in as_completed(futures, timeout=30):
            try:
                results = future.result()
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_results.append(r)
            except Exception:
                continue

    return all_results
