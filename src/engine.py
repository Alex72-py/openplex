"""
OpenPlex Answer Engine.
Implements the Perplexity-like RAG pipeline:
1. Query decomposition
2. Multi-source web search
3. Source ranking and filtering
4. Citation-embedded prompt assembly
5. Constrained LLM synthesis
6. Response validation and cleaning
"""

import json
import re
from api_client import chat_completion, APIError
from search_engine import search_and_fetch, multi_search
from config import load_config
from source_scoring import calculate_trust_score, deduplicate_sources


# Pass 1: System prompt for generating a high-quality initial draft
SEARCH_SYSTEM_PROMPT = """You are OpenPlex, an AI answer engine. Your job is to provide accurate, well-cited answers based ONLY on the provided sources.

STRICT RULES:
1. ONLY use information from the provided sources. Do NOT use prior knowledge.
2. Cite sources using [1], [2], etc. inline after each claim.
3. If sources conflict, mention the disagreement and cite both sides.
4. If sources don't contain enough info to answer, say so explicitly.
5. Never fabricate or hallucinate information not in the sources.
6. Be concise but thorough. Use paragraphs for readability.
7. Start with a direct answer, then elaborate with details.

This is a DRAFT that will be verified for accuracy and citation integrity."""

# Pass 2: System prompt for Verification and Final Polishing
VERIFICATION_PROMPT = """You are the OpenPlex Verifier. Your task is to review the research draft against the sources to ensure absolute accuracy and proper citation.

SOURCE TRUST DATA:
{source_trust_info}

STRICT RULES:
1. Ensure every claim is supported by the sources.
2. Verify that inline citations [1], [2], etc. correctly match the source numbers.
3. If a claim is weak or unverified, remove it or explicitly state the uncertainty.
4. Format the final response as clean Markdown.
5. Do NOT include trust scores or confidence levels in the final output text.

Sources:
{sources_text}

Draft to Verify:
{draft}"""

# Unified Orchestration Prompt: Intent + Resolution + Decomposition
ORCHESTRATION_PROMPT = """Analyze the user's message and the conversation context.
Provide your analysis in JSON format with the following keys:
- "intent": "search" or "chat". Use "search" for facts, news, or info-seeking.
- "resolved_query": Rewrite the user's message as a clear, standalone search query.
- "sub_queries": If deep research is requested or needed, provide 2-4 focused sub-queries. Otherwise, [].

Conversation Context:
{context}

Message: {message}
Deep Mode: {deep}"""


class AnswerEngine:
    """Core engine that orchestrates the search-and-answer pipeline."""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.conversation_history = []
        self.last_sources = []
        self.session_cache = {}

    def update_config(self, config):
        """Update engine config (e.g., after model/provider switch)."""
        self.config = config

    def _call_llm(self, messages, temperature=None, max_tokens=None):
        """Make an LLM call with current config, passing provider info."""
        return chat_completion(
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            model=self.config["model"],
            messages=messages,
            temperature=temperature or self.config["temperature"],
            max_tokens=max_tokens or self.config["max_tokens"],
            provider=self.config.get("provider"),
        )

    def _fast_needs_search(self, message):
        """Fast regex check to bypass LLM for simple greetings."""
        msg_lower = message.lower().strip()
        conversational_patterns = [
            r'^(hi|hello|hey|thanks|thank you|ok|okay|got it|sure|bye|yes|no)',
        ]
        for pattern in conversational_patterns:
            if re.match(pattern, msg_lower):
                return False
        # If starts with "write a" or similar, usually chat
        if any(msg_lower.startswith(w) for w in ["write a", "create a", "generate", "code a", "translate"]):
            return False
        return True

    def _orchestrate(self, message, deep=False):
        """
        Single-pass orchestration: Determine intent, resolve query, and decompose.
        Returns (intent, resolved_query, sub_queries)
        """
        # Fast path heuristics
        if not self._fast_needs_search(message):
            return "chat", message, []

        # Build context
        context_parts = []
        for entry in self.conversation_history[-6:]:
            context_parts.append(f"{entry['role']}: {entry['content'][:200]}")
        context = "\n".join(context_parts)

        try:
            result = self._call_llm(
                [{"role": "user", "content": ORCHESTRATION_PROMPT.format(
                    context=context, message=message, deep=deep
                )}],
                temperature=0.1,
                max_tokens=300,
            )
            # Parse JSON
            match = re.search(r'\{.*\}', result, re.DOTALL)
            data = json.loads(match.group(0)) if match else {"intent": "search", "resolved_query": message, "sub_queries": []}
            
            intent = data.get("intent", "search")
            resolved = data.get("resolved_query", message)
            sub_queries = data.get("sub_queries", [])
            
            # If sub_queries provided but not deep mode, we might ignore them or use them if complex
            if not deep:
                sub_queries = []
                
            return intent, resolved, sub_queries
        except Exception:
            return "search", message, []

    def _rank_sources(self, sources, query):
        """
        Rank sources using the Trust Engine and keyword relevance.
        Applies deduplication to ensure Source Diversity.
        """
        if not sources:
            return []

        # 1. Calculate Trust Scores for all sources
        for source in sources:
            score = calculate_trust_score(
                url=source.get("url", ""),
                title=source.get("title", ""),
                snippet=source.get("snippet", ""),
                content=source.get("content", ""),
                query=query
            )
            source["trust_score"] = score

        # 2. Add keyword relevance bonus to help local ranking
        query_words = set(re.findall(r'\w{3,}', query.lower()))
        for source in sources:
            text = f"{source.get('title', '')} {source.get('snippet', '')} {source.get('content', '')}".lower()
            overlap = sum(1 for word in query_words if word in text)
            # Relevance adds a small modifier to trust for final ranking
            source["relevance_modifier"] = min(overlap * 2, 15)
            source["final_rank_score"] = source["trust_score"] + source["relevance_modifier"]

        # 3. Deduplicate (Source Diversity)
        unique_sources = deduplicate_sources(sources)

        # 4. Final sort by composite score
        unique_sources.sort(key=lambda x: x.get("final_rank_score", 0), reverse=True)
        return unique_sources

    def _build_context_prompt(self, sources, question):
        """Build the sources section for Pass 1 (Drafting)."""
        source_blocks = []
        for i, source in enumerate(sources, 1):
            content = source.get("content") or source.get("snippet", "No content available")
            if len(content) > 3000:
                content = content[:3000] + "..."

            source_blocks.append(
                f"[Source {i}] {source['title']}\n"
                f"URL: {source['url']}\n"
                f"Trust Score: {source.get('trust_score', 0)}\n"
                f"Content: {content}\n"
            )

        sources_text = "\n---\n".join(source_blocks)

        user_prompt = (
            f"Question: {question}\n\n"
            f"SOURCES:\n{sources_text}\n\n"
            f"Task: Write a detailed research draft based on these sources. Cite using [1], [2], etc."
        )
        return user_prompt

    def _verify_claims(self, draft, sources):
        """
        Pass 2: Verify the draft against sources and format the final answer.
        """
        source_trust_info = "\n".join([
            f"- Source {i}: {s.get('url')} (Trust Score: {s.get('trust_score')})"
            for i, s in enumerate(sources, 1)
        ])
        
        source_blocks = []
        for i, source in enumerate(sources, 1):
            content = source.get("content") or source.get("snippet", "No content available")
            source_blocks.append(f"[Source {i}] {source['title']}\nURL: {source['url']}\nContent: {content}\n")
        
        sources_text = "\n---\n".join(source_blocks)

        messages = [
            {"role": "system", "content": VERIFICATION_PROMPT.format(
                source_trust_info=source_trust_info,
                draft=draft,
                sources_text=sources_text
            )}
        ]

        try:
            return self._call_llm(messages, temperature=0.2)
        except APIError:
            return draft # Fallback to draft if verification fails

    def answer(self, message, deep=False, callback=None):
        """
        Main entry point: process a user message and return an answer using the Trust Engine.
        Optimized for speed: single-pass for standard, two-pass for deep.
        """
        def status(msg):
            if callback:
                callback(msg)

        # Check session cache for exact repeats (fastest)
        cache_key = f"{'deep:' if deep else ''}{message.strip().lower()}"
        if cache_key in self.session_cache:
            status("Retrieved from cache...")
            return self.session_cache[cache_key]

        # Step 1: Orchestration (Intent + Resolution + Decomposition)
        status("Analyzing query...")
        intent, resolved_query, sub_queries = self._orchestrate(message, deep=deep)

        if intent == "chat":
            status("Thinking...")
            messages = self.conversation_history[-10:] + [{"role": "user", "content": message}]
            try:
                response = self._call_llm(messages)
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": response})
                result = {"answer": response, "sources": [], "mode": "chat"}
                self.session_cache[cache_key] = result
                return result
            except APIError as e:
                return {"answer": f"Error: {e}", "sources": [], "mode": "error"}

        # Step 2: Search the web
        status(f"Searching: {resolved_query[:60]}...")
        
        if sub_queries:
            # Parallel multi-search (used for /deep)
            sources = multi_search(sub_queries, num_results_per=4, max_content_chars=2000)
        else:
            # Standard search: reduce to 5 results for speed
            sources = search_and_fetch(resolved_query, num_results=5, max_content_chars=2500)

        if not sources:
            status("Retrying search...")
            sources = search_and_fetch(message, num_results=5, max_content_chars=2000)

        if not sources:
            result = {
                "answer": "I couldn't find any relevant sources for this query.",
                "sources": [],
                "mode": "search"
            }
            self.session_cache[cache_key] = result
            return result

        # Step 3: Rank and filter sources using Trust Engine
        status(f"Ranking {len(sources)} sources...")
        sources = self._rank_sources(sources, resolved_query)

        # Step 4: Drafting (Pass 1)
        status("Generating answer...")
        draft_prompt = self._build_context_prompt(sources, resolved_query)

        messages = [{"role": "system", "content": SEARCH_SYSTEM_PROMPT}]
        if self.conversation_history:
            messages.extend(self.conversation_history[-4:])
        messages.append({"role": "user", "content": draft_prompt})

        try:
            answer = self._call_llm(messages, temperature=0.3)
        except APIError as e:
            return {"answer": f"Error generating answer: {e}", "sources": sources, "mode": "error"}

        # Step 5: Verification (Pass 2) - Only for Deep Research
        if deep:
            status("Verifying claims...")
            answer = self._verify_claims(answer, sources)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": answer})
        self.last_sources = sources

        result = {"answer": answer, "sources": sources, "mode": "search" if not deep else "deep"}
        self.session_cache[cache_key] = result
        return result


    def clear_history(self):
        """Clear conversation history and session cache."""
        self.conversation_history = []
        self.last_sources = []
        self.session_cache = {}
