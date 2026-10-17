"""Run with: python3 -m unittest discover -s tests -v"""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config
import engine
import parallel_search


SOURCE = {
    "url": "https://docs.python.org/3/library/asyncio.html",
    "title": "asyncio documentation",
    "excerpts": ["asyncio is a library to write concurrent code.", "It uses async/await syntax."],
}


class Response(io.BytesIO):
    def __init__(self, body, content_type="application/json", session=None):
        super().__init__(body.encode("utf-8"))
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if session:
            self.headers["Mcp-Session-Id"] = session


class ParallelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_file = Path(self.temp.name) / "config.json"
        for name, value in [("CONFIG_DIR", self.temp.name),
                            ("CONFIG_FILE", str(self.config_file)),
                            ("HISTORY_DIR", str(Path(self.temp.name) / "history"))]:
            patcher = patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.dict(os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.calls = []

    def transport(self, result=None, sse=False, text=False):
        def send(request, **kwargs):
            payload = json.loads(request.data)
            self.calls.append(payload)
            headers = dict((k.lower(), v) for k, v in request.header_items())
            self.assertEqual(request.full_url, "https://search.parallel.ai/mcp")
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(headers["user-agent"], parallel_search.USER_AGENT)
            self.assertEqual(headers["accept"], "application/json, text/event-stream")
            self.assertNotIn("authorization", headers)
            self.assertEqual(kwargs, {"timeout": 20})  # No unverified SSL context.
            method = payload["method"]
            if method == "initialize":
                self.assertEqual(payload["params"]["clientInfo"]["name"], "openplex")
                return Response(json.dumps({"jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-03-26"}}), session="transport-session")
            self.assertEqual(headers["mcp-session-id"], "transport-session")
            self.assertEqual(headers["mcp-protocol-version"], "2025-03-26")
            if method == "notifications/initialized":
                self.assertNotIn("id", payload)
                return Response("")
            self.assertEqual(method, "tools/call")
            self.assertEqual(payload["params"]["name"], "web_search")
            output = result if result is not None else {"results": [SOURCE]}
            tool_result = ({"content": [{"type": "text", "text": json.dumps(output)}]}
                           if text else {"structuredContent": output})
            message = {"jsonrpc": "2.0", "id": 2, "result": tool_result}
            if sse:
                # Ignore notifications, accept CRLF and multi-line data fields.
                body = ': keepalive\r\ndata: {"method":"notifications/progress"}\r\n\r\n'
                encoded = json.dumps(message)
                body += "event: message\r\ndata: " + encoded[:1] + "\r\ndata: " + encoded[1:] + "\r\n\r\n"
                return Response(body, "text/event-stream; charset=utf-8")
            return Response(json.dumps(message))
        return send

    def make_engine(self):
        os.environ["OPENPLEX_SEARCH_PROVIDER"] = "parallel"
        settings = config.load_config()
        self.assertEqual(settings["api_key"], "")
        self.assertEqual(settings["tavily_api_key"], "")
        return engine.AnswerEngine(settings)

    def test_selected_backend_supplies_citations_to_answer_pipeline(self):
        answerer = self.make_engine()
        with patch.object(parallel_search.urllib.request, "urlopen", side_effect=self.transport()), \
                patch.object(answerer, "_call_llm", side_effect=[
                    json.dumps({"intent": "search", "resolved_query": "Python asyncio documentation", "sub_queries": []}),
                    "asyncio supports concurrent code [1].",
                ]) as llm, patch.object(engine, "search_and_fetch") as ddg, \
                patch.object(engine, "tavily_search_and_fetch") as tavily:
            result = answerer.answer("What is Python asyncio?")
        self.assertEqual(result["mode"], "search")
        self.assertIn("[1]", result["answer"])
        self.assertEqual(result["sources"][0]["url"], SOURCE["url"])
        self.assertEqual(answerer.last_sources, result["sources"])
        prompt = llm.call_args_list[-1].args[0][-1]["content"]
        self.assertIn("[Source 1] asyncio documentation", prompt)
        self.assertIn(SOURCE["excerpts"][0], prompt)
        self.assertEqual(self.calls[-1]["params"]["arguments"]["session_id"], answerer.search_session_id)
        ddg.assert_not_called()
        tavily.assert_not_called()

    def test_deep_queries_batched_and_session_reused_then_reset(self):
        answerer = self.make_engine()
        session = answerer.search_session_id
        queries = ["Python asyncio concurrent tasks", "Python asyncio task cancellation"]
        with patch.object(parallel_search.urllib.request, "urlopen", side_effect=self.transport()), \
                patch.object(answerer, "_orchestrate", return_value=("search", "Python asyncio", queries)), \
                patch.object(answerer, "_call_llm", return_value="Answer [1].") as llm:
            result = answerer.answer("Explain asyncio", deep=True)
            answerer.answer("Explain asyncio again", deep=True)
        tool_calls = [c for c in self.calls if c["method"] == "tools/call"]
        self.assertEqual(len(tool_calls), 2)
        for call in tool_calls:
            self.assertEqual(call["params"]["arguments"]["search_queries"], queries)
            self.assertEqual(call["params"]["arguments"]["session_id"], session)
        self.assertEqual(llm.call_count, 4)  # Draft and verification for both answers.
        self.assertEqual(result["mode"], "deep")
        answerer.clear_history()
        self.assertNotEqual(answerer.search_session_id, session)

    def test_sse_text_output_limits_and_deduplicates_sources(self):
        rows = [dict(SOURCE, url="file:///private"), SOURCE, SOURCE,
                dict(SOURCE, url="https://example.com", title=None)]
        with patch.object(parallel_search.urllib.request, "urlopen",
                          side_effect=self.transport({"results": rows}, sse=True, text=True)):
            results = parallel_search.parallel_search("asyncio", num_results=2, max_content_chars=20)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]["title"], "https://example.com")
        self.assertEqual(results[0]["content"], SOURCE["excerpts"][0][:20])
        self.assertEqual(results[0]["content"], results[0]["snippet"])

    def test_empty_results_and_zero_limit(self):
        with patch.object(parallel_search.urllib.request, "urlopen",
                          side_effect=self.transport({"results": []})) as send:
            self.assertEqual(parallel_search.parallel_search("asyncio"), [])
            count = send.call_count
            self.assertEqual(parallel_search.parallel_search("asyncio", num_results=0), [])
            self.assertEqual(send.call_count, count)

    def test_protocol_and_tool_errors_are_not_empty_successes(self):
        replies = ["not json", json.dumps({"id": 1, "error": {"code": -32603}}),
                   json.dumps({"id": 9, "result": {}}),
                   json.dumps({"id": 1, "result": {"protocolVersion": "unknown"}})]
        for body in replies:
            with self.subTest(body=body), patch.object(parallel_search.urllib.request, "urlopen",
                    return_value=Response(body)):
                with self.assertRaises(parallel_search.ParallelSearchError):
                    parallel_search.parallel_search("asyncio")
        for result in [{}, {"results": "invalid"}, {"results": [None]}]:
            with self.subTest(result=result), patch.object(parallel_search.urllib.request, "urlopen",
                    side_effect=self.transport(result)):
                with self.assertRaises(parallel_search.ParallelSearchError):
                    parallel_search.parallel_search("asyncio")
        send = self.transport()
        def tool_error(request, **kwargs):
            if json.loads(request.data)["method"] == "tools/call":
                return Response(json.dumps({"id": 2, "result": {"isError": True,
                    "content": [{"type": "text", "text": "Service unavailable"}]}}))
            return send(request, **kwargs)
        with patch.object(parallel_search.urllib.request, "urlopen", side_effect=tool_error):
            with self.assertRaisesRegex(parallel_search.ParallelSearchError, "unavailable"):
                parallel_search.parallel_search("asyncio")

    def test_http_and_timeout_errors_no_retry_fallback_or_cache(self):
        for failure in [urllib.error.HTTPError(parallel_search.ENDPOINT, 429, "Too many requests", {}, None),
                        TimeoutError("timed out"), urllib.error.URLError("offline")]:
            with self.subTest(failure=failure):
                answerer = self.make_engine()
                with patch.object(parallel_search.urllib.request, "urlopen", side_effect=failure) as send, \
                        patch.object(answerer, "_orchestrate", return_value=("search", "asyncio", [])), \
                        patch.object(answerer, "_call_llm") as llm, \
                        patch.object(engine, "search_and_fetch") as ddg:
                    result = answerer.answer("asyncio")
                self.assertEqual(result["mode"], "error")
                self.assertEqual(result["sources"], [])
                self.assertEqual(send.call_count, 1)
                self.assertFalse(answerer.session_cache)
                llm.assert_not_called()
                ddg.assert_not_called()

    def test_keyboard_interrupt_propagates_from_actual_caller(self):
        answerer = self.make_engine()
        with patch.object(answerer, "_orchestrate", return_value=("search", "asyncio", [])), \
                patch.object(parallel_search.urllib.request, "urlopen", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                answerer.answer("asyncio")

    def test_configuration_preserves_default_and_saved_choices(self):
        self.assertEqual(config.load_config()["search_provider"], "duckduckgo")
        for choice in ["duckduckgo", "tavily", "parallel"]:
            self.config_file.write_text(json.dumps({"search_provider": choice}))
            self.assertEqual(config.load_config()["search_provider"], choice)
        os.environ["OPENPLEX_SEARCH_PROVIDER"] = " PaRaLlEl "
        self.assertEqual(config.load_config()["search_provider"], "parallel")
        os.environ["OPENPLEX_SEARCH_PROVIDER"] = "invalid"
        self.config_file.write_text(json.dumps({"search_provider": "tavily"}))
        self.assertEqual(config.load_config()["search_provider"], "tavily")

    def test_existing_provider_routes_are_preserved(self):
        for provider, key, route in [("duckduckgo", "", "search_and_fetch"),
                                     ("tavily", "key", "tavily_search_and_fetch"),
                                     ("tavily", "", "search_and_fetch")]:
            with self.subTest(provider=provider, key=key):
                settings = config.load_config()
                settings.update(search_provider=provider, tavily_api_key=key)
                answerer = engine.AnswerEngine(settings)
                with patch.object(answerer, "_orchestrate", return_value=("search", "asyncio", [])), \
                        patch.object(engine, route, return_value=[]) as search, \
                        patch.object(parallel_search.urllib.request, "urlopen") as send:
                    answerer.answer("asyncio")
                self.assertEqual(search.call_count, 2)  # Existing retry behavior.
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
