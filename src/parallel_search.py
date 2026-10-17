"""Anonymous Parallel Search MCP adapter, using only the Python standard library."""

import json
import urllib.error
import urllib.request
import uuid


ENDPOINT = "https://search.parallel.ai/mcp"
USER_AGENT = "OpenPlex/1.0 (+https://github.com/Alex72-py/openplex)"
PROTOCOL_VERSION = "2025-03-26"
REQUEST_TIMEOUT = 20


class ParallelSearchError(Exception):
    """The selected search backend could not supply usable results."""


def _read_response(response, request_id):
    """Read a JSON response or the matching message in a Streamable HTTP SSE stream."""
    if "text/event-stream" not in response.headers.get("Content-Type", ""):
        return json.loads(response.read().decode("utf-8"))

    data = []
    for raw_line in response:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        elif not line and data:
            message = json.loads("\n".join(data))
            data = []
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
    raise ValueError("Missing MCP response")


def _rpc(method, params, request_id, headers):
    payload = {"jsonrpc": "2.0", "method": method, "params": params}
    if request_id is not None:
        payload["id"] = request_id
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers=headers,
    )
    # Use Python's verified TLS defaults, independently of the legacy HTML scraper.
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        if request_id is None:
            return {}
        message = _read_response(response, request_id)
        if (not isinstance(message, dict) or message.get("id") != request_id
                or "error" in message or not isinstance(message.get("result"), dict)):
            raise ValueError("Invalid MCP response")
        session = response.headers.get("Mcp-Session-Id")
        if session:
            headers["Mcp-Session-Id"] = session
        return message["result"]


def parallel_search(objective, queries=None, num_results=5, max_content_chars=2500,
                    session_id=None):
    """Return ranked source excerpts in OpenPlex's {title, url, snippet, content} shape.

    Related deep-research queries share a single web_search call. Search excerpts
    already contain source text, so this adapter does not fetch every page again.
    Network/protocol errors are surfaced without retrying or changing providers.
    KeyboardInterrupt is deliberately allowed to propagate to the terminal loop.
    """
    if num_results <= 0:
        return []
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": USER_AGENT,
    }
    try:
        initialized = _rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "openplex", "version": "1.0"},
        }, 1, headers)
        if initialized.get("protocolVersion") != PROTOCOL_VERSION:
            raise ValueError("Unsupported MCP protocol version")
        headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        _rpc("notifications/initialized", {}, None, headers)
        result = _rpc("tools/call", {
            "name": "web_search",
            "arguments": {
                "objective": objective,
                "search_queries": queries or [objective],
                "session_id": session_id or uuid.uuid4().hex,
            },
        }, 2, headers)
        if result.get("isError"):
            raise ParallelSearchError("Parallel search is unavailable. Please try again later.")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            # MCP clients may receive structured output serialized as text instead.
            structured = json.loads(next(
                block["text"] for block in result.get("content", [])
                if block.get("type") == "text"
            ))
        rows = structured.get("results")
        if not isinstance(rows, list):
            raise ValueError("Missing search results")
        sources = []
        seen = set()
        for row in rows:
            url = row.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")) or url in seen:
                continue
            content = "\n\n".join(row.get("excerpts", []))[:max_content_chars]
            sources.append({
                "title": row.get("title") or url,
                "url": url,
                "snippet": content,
                "content": content,
            })
            seen.add(url)
            if len(sources) >= num_results:
                break
        return sources
    except urllib.error.HTTPError as error:
        raise ParallelSearchError(
            f"Parallel search request failed (HTTP {error.code}). Please try again later."
        ) from error
    except (urllib.error.URLError, OSError) as error:
        raise ParallelSearchError("Could not reach Parallel search. Please try again later.") from error
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as error:
        raise ParallelSearchError("Parallel search returned an invalid response.") from error
