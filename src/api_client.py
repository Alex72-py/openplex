"""
Multi-provider API client for OpenPlex.
Supports: NVIDIA NIM, Google AI Studio, OpenRouter
Uses urllib (stdlib only) — no external HTTP libraries needed.
All providers use OpenAI-compatible /chat/completions endpoints.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import re

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class APIError(Exception):
    """Raised when the API returns an error."""
    def __init__(self, message, status_code=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _build_headers(provider, api_key):
    """
    Build provider-specific request headers.
    All providers use Bearer auth, but some need extra headers.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    if provider == "openrouter":
        # OpenRouter requires these for tracking / free tier access
        headers["HTTP-Referer"] = "https://github.com/Alex72-py/OpenPlex"
        headers["X-Title"] = "OpenPlex"

    return headers


def _detect_provider(base_url):
    """Detect provider name from base URL."""
    if "nvidia" in base_url:
        return "nvidia"
    elif "generativelanguage.googleapis.com" in base_url or "google" in base_url:
        return "google"
    elif "openrouter.ai" in base_url:
        return "openrouter"
    return "unknown"


def _parse_error(e):
    """Parse an HTTPError into a readable message."""
    try:
        error_body = e.read().decode("utf-8")
        error_json = json.loads(error_body)
        # OpenAI-style: {"error": {"message": "..."}}
        if "error" in error_json:
            err = error_json["error"]
            if isinstance(err, dict):
                return err.get("message", str(err))
            return str(err)
        # Google style: {"error": {"code": 400, "message": "...", "status": "..."}}
        return error_body[:300]
    except Exception:
        return f"HTTP {e.code}"


def chat_completion(base_url, api_key, model, messages, temperature=0.6, max_tokens=4096, provider=None):
    """
    Call the chat completions endpoint for any supported provider.
    Returns the assistant's message content as a clean string.
    Handles retries, rate limits, and provider-specific quirks.
    """
    if not provider:
        provider = _detect_provider(base_url)

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = _build_headers(provider, api_key)

    # Build payload — provider-specific adjustments
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    # Google Gemini 2.5 Flash/Pro are thinking models: they consume tokens for
    # internal reasoning BEFORE generating the response. If max_tokens is too
    # small (< ~200), the model returns empty content. We omit max_tokens for
    # Google so the model can use its default budget, or enforce a safe minimum.
    if provider == "google":
        if max_tokens and max_tokens >= 200:
            payload["max_tokens"] = max_tokens
        # else: omit max_tokens — let Google use its default
    else:
        payload["max_tokens"] = max_tokens

    data = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as resp:
                response_text = resp.read().decode("utf-8")
                response_json = json.loads(response_text)

                # Standard OpenAI-compatible response
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    if content is None:
                        # Some models return null content with finish_reason=stop
                        content = ""
                    return sanitize_response(content)
                else:
                    raise APIError("No choices in API response", retryable=True)

        except urllib.error.HTTPError as e:
            status = e.code
            error_msg = _parse_error(e)

            if status == 429:
                # Rate limited — exponential backoff
                wait_time = RETRY_DELAY * (2 ** attempt)
                last_error = APIError(
                    f"Rate limited by {provider}. Retrying in {wait_time}s...",
                    status, retryable=True
                )
                time.sleep(wait_time)
                continue

            elif status in (500, 502, 503, 504):
                # Transient server error — retry
                wait_time = RETRY_DELAY * (attempt + 1)
                last_error = APIError(
                    f"Server error ({status}) from {provider}. Retrying...",
                    status, retryable=True
                )
                time.sleep(wait_time)
                continue

            elif status in (401, 403):
                provider_hint = {
                    "nvidia": "Get a free key at build.nvidia.com",
                    "google": "Get a free key at aistudio.google.com",
                    "openrouter": "Get a free key at openrouter.ai/keys",
                }.get(provider, "Check your API key")
                raise APIError(
                    f"Invalid or expired {provider} API key. "
                    f"Run /provider key <key> to update it. ({provider_hint})",
                    status
                )

            elif status == 400:
                # Bad request — often a model ID issue
                if "model" in error_msg.lower():
                    raise APIError(
                        f"Model not found or unsupported: '{model}'. "
                        f"Run /model list to see available models.",
                        status
                    )
                raise APIError(f"Bad request to {provider}: {error_msg}", status)

            elif status == 404:
                raise APIError(
                    f"Model '{model}' not found on {provider}. "
                    f"Run /model list to see valid models. Check your API key too.",
                    status
                )

            else:
                raise APIError(f"API error {status} from {provider}: {error_msg}", status)

        except urllib.error.URLError as e:
            last_error = APIError(
                f"Connection error (check internet): {e.reason}",
                retryable=True
            )
            time.sleep(RETRY_DELAY * (attempt + 1))
            continue

        except json.JSONDecodeError:
            last_error = APIError("Invalid JSON response from API", retryable=True)
            time.sleep(RETRY_DELAY)
            continue

        except OSError as e:
            last_error = APIError(f"Network error: {e}", retryable=True)
            time.sleep(RETRY_DELAY * (attempt + 1))
            continue

    # All retries exhausted
    if last_error:
        raise last_error
    raise APIError("Request failed after all retries")


def sanitize_response(text):
    """
    Clean up LLM response to handle common issues across all providers:
    - Strip <think>...</think> reasoning blocks (DeepSeek R1, Qwen3)
    - Remove <reasoning>...</reasoning> blocks
    - Remove duplicate/repeated responses
    - Fix broken markdown
    - Remove system prompt leakage
    - Strip leading/trailing artifacts
    - Handle Google Gemini-specific quirks
    """
    if not text:
        return ""

    # 1. Remove <think>...</think> blocks (DeepSeek R1, Qwen3 thinking mode)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 2. Remove <reasoning>...</reasoning> blocks
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL)

    # 3. Remove other thinking patterns
    text = re.sub(r'\[thinking\].*?\[/thinking\]', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\*\*Thinking:?\*\*.*?(?=\n\n|\*\*Answer|\*\*Response)', '', text, flags=re.DOTALL)

    # 4. Handle double/repeated responses
    lines = text.split('\n')
    if len(lines) > 10:
        mid = len(lines) // 2
        first_half = '\n'.join(lines[:mid]).strip()
        second_half = '\n'.join(lines[mid:]).strip()
        if first_half and second_half and len(first_half) > 100:
            if second_half.startswith(first_half[:100]):
                text = first_half

    # 5. Remove system prompt leakage
    text = re.sub(r'^(You are OpenPlex|I am OpenPlex|As OpenPlex).*?\n\n', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'^(You are|I am an AI|As an AI assistant).*?\n\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\[?(System|Instructions?|Context|STRICT RULES)\]?:.*?\n\n', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 6. Remove "Here's my response:" type prefixes
    text = re.sub(
        r'^(Here\'?s?( is)?( my)?( the)? (response|answer|reply|analysis|summary):?\s*\n+)',
        '', text, flags=re.IGNORECASE
    )

    # 7. Remove "Based on the sources provided, " opener (too verbose)
    text = re.sub(r'^Based on the (provided |above )?sources?,? ', '', text, flags=re.IGNORECASE)

    # 8. Fix common markdown issues
    text = re.sub(r'\*\* +', '**', text)
    text = re.sub(r' +\*\*', '**', text)
    # Fix **Answer:** prefix that some models add
    text = re.sub(r'^\*\*Answer:?\*\*\s*', '', text, flags=re.IGNORECASE)

    # 9. Strip leading/trailing whitespace
    text = text.strip()

    # 10. Remove trailing incomplete sentences
    if text and text[-1] not in '.!?"\')]}:':
        last_newline = text.rfind('\n')
        if last_newline > len(text) * 0.85:
            last_line = text[last_newline:].strip()
            if len(last_line) < 25 and not last_line.endswith(('.', '!', '?', ':', '"')):
                text = text[:last_newline].strip()

    return text


def validate_api_key(base_url, api_key, provider=None):
    """
    Quick validation that the API key and provider work.
    Returns (True, message) or (False, error_message).
    """
    if not provider:
        provider = _detect_provider(base_url)

    # Pick a cheap test model per provider
    test_models = {
        "nvidia": "meta/llama-3.3-70b-instruct",
        "google": "gemini-2.0-flash",
        "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    }
    test_model = test_models.get(provider, "meta/llama-3.3-70b-instruct")

    try:
        result = chat_completion(
            base_url, api_key, test_model,
            [{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5,
            provider=provider,
        )
        return True, f"{provider.title()} API key is valid"
    except APIError as e:
        if e.status_code in (401, 403):
            return False, f"Invalid {provider} API key"
        elif e.status_code == 404:
            # Key works but model might differ — that's fine
            return True, f"{provider.title()} API key is valid (model check skipped)"
        else:
            return False, str(e)
    except Exception as e:
        return False, f"Connection error: {e}"
