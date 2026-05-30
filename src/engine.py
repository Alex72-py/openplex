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


# System prompt that forces citation-grounded answers
SEARCH_SYSTEM_PROMPT = """You are OpenPlex, an AI answer engine. Your job is to provide accurate, well-cited answers based ONLY on the provided source documents.

STRICT RULES:
1. ONLY use information from the provided sources. Do NOT use prior knowledge.
2. Cite sources using [1], [2], etc. inline after each claim.
3. If sources conflict, mention the disagreement and cite both sides.
4. If sources don't contain enough info to answer, say so explicitly.
5. Never fabricate or hallucinate information not in the sources.
6. Be concise but thorough. Use paragraphs, not bullet lists.
7. Start with a direct answer, then elaborate with details.
8. End with a brief summary if the answer is long.

FORMAT:
- Use inline citations like [1], [2] after statements
- Bold key terms with **term**
- Use paragraphs for readability"""

# Prompt for query decomposition
DECOMPOSE_PROMPT = """Break this question into 2-4 focused search queries that would help find comprehensive information to answer it. Each query should target a different aspect of the question.

Return ONLY a JSON array of search query strings. No explanation.
Example: ["query 1", "query 2", "query 3"]

Question: {question}"""

# Prompt for determining if a query needs web search
NEEDS_SEARCH_PROMPT = """Determine if this message requires a web search to answer properly, or if it's a conversational/follow-up message that can be answered from the existing conversation context.

Reply with ONLY "search" or "chat". Nothing else.

Message: {message}"""

# Prompt for follow-up context resolution
FOLLOWUP_PROMPT = """Given the conversation history and the user's latest message, determine what they're actually asking about. Resolve any pronouns or references to previous topics.

Rewrite their message as a clear, standalone question suitable for web search.
Return ONLY the rewritten question, nothing else.

Conversation context:
{context}

Latest message: {message}"""


class AnswerEngine:
    """Core engine that orchestrates the search-and-answer pipeline."""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.conversation_history = []
        self.last_sources = []

    def update_config(self, config):
        """Update engine config (e.g., after model switch)."""
        self.config = config

    def _call_llm(self, messages, temperature=None, max_tokens=None):
        """Make an LLM call with current config."""
        return chat_completion(
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            model=self.config["model"],
            messages=messages,
            temperature=temperature or self.config["temperature"],
            max_tokens=max_tokens or self.config["max_tokens"],
        )

    def _needs_search(self, message):
        """Determine if a message needs web search or is just conversation."""
        # Short messages that are clearly conversational
        conversational_patterns = [
            r'^(hi|hello|hey|thanks|thank you|ok|okay|got it|sure|yes|no|bye)',
            r'^(what do you think|can you explain|tell me more)',
        ]
        for pattern in conversational_patterns:
            if re.match(pattern, message.lower().strip()):
                # But "tell me more" might need search if no context
                if "more" in message.lower() and self.conversation_history:
                    return True
                if len(self.conversation_history) == 0:
                    return True
                return False

        # If it's clearly a question or request for information, search
        if any(w in message.lower() for w in ["what is", "how to", "why does", "when did", "who is", "where", "latest", "news", "current", "2024", "2025", "2026"]):
            return True

        # Default: use LLM to decide (but only if we have conversation context)
        if self.conversation_history:
            try:
                result = self._call_llm(
                    [{"role": "user", "content": NEEDS_SEARCH_PROMPT.format(message=message)}],
                    temperature=0.1,
                    max_tokens=10,
                )
                return "search" in result.lower()
            except APIError:
                return True  # Default to search on error
        return True

    def _resolve_followup(self, message):
        """Resolve follow-up questions using conversation context."""
        if not self.conversation_history:
            return message

        # Build context from last 3 exchanges
        context_parts = []
        for entry in self.conversation_history[-6:]:
            role = entry["role"]
            content = entry["content"][:200]
            context_parts.append(f"{role}: {content}")
        context = "\n".join(context_parts)

        try:
            result = self._call_llm(
                [{"role": "user", "content": FOLLOWUP_PROMPT.format(context=context, message=message)}],
                temperature=0.2,
                max_tokens=100,
            )
            resolved = result.strip().strip('"').strip("'")
            return resolved if len(resolved) > 5 else message
        except APIError:
            return message

    def _decompose_query(self, question):
        """Break a complex question into sub-queries for multi-source search."""
        try:
            result = self._call_llm(
                [{"role": "user", "content": DECOMPOSE_PROMPT.format(question=question)}],
                temperature=0.3,
                max_tokens=200,
            )

            # Parse JSON array from response
            # Handle cases where model wraps in markdown code block
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            result = result.strip()

            queries = json.loads(result)
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:4]  # Max 4 sub-queries
        except (json.JSONDecodeError, APIError, Exception):
            pass

        # Fallback: just use the original question
        return [question]

    def _rank_sources(self, sources, query):
        """
        Rank sources by relevance to the query.
        Simple keyword-based scoring (no ML needed, keeps it lightweight).
        """
        query_words = set(query.lower().split())

        for source in sources:
            score = 0
            text = f"{source.get('title', '')} {source.get('snippet', '')} {source.get('content', '')}".lower()

            # Keyword overlap scoring
            for word in query_words:
                if len(word) > 3:  # Skip short words
                    count = text.count(word)
                    score += min(count, 5)  # Cap per-word contribution

            # Bonus for having actual content
            if source.get("content"):
                score += 3

            # Bonus for snippet relevance
            if source.get("snippet"):
                snippet_words = set(source["snippet"].lower().split())
                overlap = len(query_words & snippet_words)
                score += overlap * 2

            source["relevance_score"] = score

        # Sort by relevance score descending
        sources.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return sources

    def _build_context_prompt(self, sources, question):
        """
        Build the citation-embedded prompt (Perplexity's key mechanism).
        Sources are injected INTO the prompt BEFORE generation.
        """
        source_blocks = []
        for i, source in enumerate(sources, 1):
            content = source.get("content") or source.get("snippet", "No content available")
            # Truncate individual sources to keep total context manageable
            if len(content) > 2000:
                content = content[:2000] + "..."

            source_blocks.append(
                f"[Source {i}] {source['title']}\n"
                f"URL: {source['url']}\n"
                f"Content: {content}\n"
            )

        sources_text = "\n---\n".join(source_blocks)

        user_prompt = f"""Based on the following sources, answer this question: {question}

SOURCES:
{sources_text}

INSTRUCTIONS:
- Cite sources using [1], [2], etc. after each claim
- Only use information from the sources above
- If sources disagree, mention both perspectives
- If information is insufficient, say so
- Be thorough but concise"""

        return user_prompt

    def _verify_response(self, response, sources):
        """
        Basic verification: check that cited source numbers actually exist.
        Remove citations to non-existent sources.
        """
        max_source = len(sources)
        # Find all citations like [1], [2], etc.
        citations = re.findall(r'\[(\d+)\]', response)
        for cite in citations:
            num = int(cite)
            if num > max_source or num < 1:
                # Remove invalid citation
                response = response.replace(f'[{cite}]', '')

        return response

    def answer(self, message, deep=False, callback=None):
        """
        Main entry point: process a user message and return an answer.

        Args:
            message: User's question/message
            deep: If True, use deep research mode (more sources, decomposition)
            callback: Optional function to call with status updates

        Returns:
            dict with keys: answer, sources, mode ("search" or "chat")
        """
        def status(msg):
            if callback:
                callback(msg)

        # Step 1: Determine if we need to search
        needs_search = self._needs_search(message)

        if not needs_search:
            # Pure conversational response using history
            status("Thinking...")
            messages = self.conversation_history[-10:] + [{"role": "user", "content": message}]
            try:
                response = self._call_llm(messages)
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": response})
                return {"answer": response, "sources": [], "mode": "chat"}
            except APIError as e:
                return {"answer": f"Error: {e}", "sources": [], "mode": "error"}

        # Step 2: Resolve follow-up references
        resolved_query = self._resolve_followup(message)
        status(f"Searching: {resolved_query[:60]}...")

        # Step 3: Decompose query (for deep mode or complex questions)
        if deep or len(message.split()) > 10:
            status("Breaking down question...")
            queries = self._decompose_query(resolved_query)
            status(f"Searching {len(queries)} sub-queries...")
        else:
            queries = [resolved_query]

        # Step 4: Search the web
        if len(queries) > 1:
            sources = multi_search(queries, num_results_per=4, max_content_chars=2000)
        else:
            sources = search_and_fetch(queries[0], num_results=8, max_content_chars=2500)

        if not sources:
            # Fallback: try a simpler search
            status("Retrying search...")
            sources = search_and_fetch(message, num_results=6, max_content_chars=2000)

        if not sources:
            return {
                "answer": "I couldn't find any relevant sources for this query. Please try rephrasing your question.",
                "sources": [],
                "mode": "search"
            }

        # Step 5: Rank and filter sources
        status(f"Analyzing {len(sources)} sources...")
        sources = self._rank_sources(sources, resolved_query)

        # Keep top sources (quality threshold)
        max_sources = self.config.get("max_sources", 8)
        if deep:
            max_sources = min(len(sources), 12)
        sources = sources[:max_sources]

        # Filter out sources with zero relevance
        sources = [s for s in sources if s.get("relevance_score", 0) > 0]

        if not sources:
            return {
                "answer": "Found some results but none were relevant enough to provide a reliable answer. Try being more specific.",
                "sources": [],
                "mode": "search"
            }

        # Step 6: Build citation-embedded prompt and generate answer
        status("Generating answer...")
        context_prompt = self._build_context_prompt(sources, resolved_query)

        messages = [
            {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
        ]

        # Add relevant conversation history for context
        if self.conversation_history:
            # Only last 2 exchanges to save tokens
            messages.extend(self.conversation_history[-4:])

        messages.append({"role": "user", "content": context_prompt})

        try:
            response = self._call_llm(messages)
        except APIError as e:
            return {"answer": f"Error generating answer: {e}", "sources": sources, "mode": "error"}

        # Step 7: Verify and clean response
        response = self._verify_response(response, sources)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": response})
        self.last_sources = sources

        return {"answer": response, "sources": sources, "mode": "search"}

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.last_sources = []
