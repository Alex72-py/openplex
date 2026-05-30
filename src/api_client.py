"""
NVIDIA NIM API client for OpenPlex.
Uses urllib (stdlib) — no external HTTP libraries needed.
OpenAI-compatible endpoint at integrate.api.nvidia.com/v1
"""

import json
import urllib.request
import urllib.error
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


def chat_completion(base_url, api_key, model, messages, temperature=0.6, max_tokens=4096, stream=False):
    """
    Call the NVIDIA NIM chat completions endpoint.
    Returns the assistant's message content.
    Handles retries, rate limits, and common API errors.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,  # Non-streaming for reliability on mobile
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as resp:
                response_text = resp.read().decode("utf-8")
                response_json = json.loads(response_text)

                # Extract the message content
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    return sanitize_response(content)
                else:
                    raise APIError("No choices in API response", retryable=True)

        except urllib.error.HTTPError as e:
            status = e.code
            try:
                error_body = e.read().decode("utf-8")
                error_json = json.loads(error_body)
                error_msg = error_json.get("error", {}).get("message", error_body[:200])
            except Exception:
                error_msg = f"HTTP {status}"

            if status == 429:
                # Rate limited — wait and retry
                wait_time = RETRY_DELAY * (attempt + 1) * 2
                last_error = APIError(f"Rate limited. Waiting {wait_time}s...", status, retryable=True)
                time.sleep(wait_time)
                continue
            elif status in (500, 502, 503, 504):
                # Server error — retry
                last_error = APIError(f"Server error ({status}): {error_msg}", status, retryable=True)
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            elif status in (401, 403):
                raise APIError("Invalid or expired API key. Run /config key <your-key> to update it.", status)
            elif status == 400:
                raise APIError(f"Bad request: {error_msg}", status)
            elif status == 404:
                raise APIError(f"Model not found: {model}. Try /model list", status)
            else:
                raise APIError(f"API error ({status}): {error_msg}", status)

        except urllib.error.URLError as e:
            last_error = APIError(f"Connection error: {e.reason}", retryable=True)
            time.sleep(RETRY_DELAY * (attempt + 1))
            continue

        except json.JSONDecodeError as e:
            last_error = APIError(f"Invalid JSON response from API", retryable=True)
            time.sleep(RETRY_DELAY)
            continue

        except OSError as e:
            last_error = APIError(f"Network error: {e}", retryable=True)
            time.sleep(RETRY_DELAY * (attempt + 1))
            continue

    # All retries exhausted
    if last_error:
        raise last_error
    raise APIError("Failed after all retries")


def sanitize_response(text):
    """
    Clean up LLM response to handle common issues:
    - Strip <think>...</think> reasoning blocks (DeepSeek R1)
    - Remove duplicate responses
    - Fix broken markdown
    - Remove system prompt leakage
    - Strip leading/trailing artifacts
    """
    if not text:
        return ""

    # 1. Remove <think>...</think> blocks (DeepSeek R1 reasoning)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 2. Remove <reasoning>...</reasoning> blocks
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL)

    # 3. Remove other common thinking patterns
    text = re.sub(r'\[thinking\].*?\[/thinking\]', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\*\*Thinking:?\*\*.*?(?=\n\n|\*\*Answer)', '', text, flags=re.DOTALL)

    # 4. Handle double/repeated responses
    # If the response contains the same content twice, keep only the first
    lines = text.split('\n')
    if len(lines) > 10:
        mid = len(lines) // 2
        first_half = '\n'.join(lines[:mid]).strip()
        second_half = '\n'.join(lines[mid:]).strip()
        # Check similarity (simple check: if second half starts same as first)
        if first_half and second_half:
            first_words = first_half[:200]
            if second_half.startswith(first_words[:100]):
                text = first_half

    # 5. Remove system prompt leakage patterns
    text = re.sub(r'^(You are|I am|As an AI|As a helpful).*?\n\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\[?(System|Instructions?|Context)\]?:.*?\n\n', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 6. Remove "Here's my response:" type prefixes
    text = re.sub(r'^(Here\'?s?( is)?( my)?( the)? (response|answer|reply):?\s*\n)', '', text, flags=re.IGNORECASE)

    # 7. Fix common markdown issues
    # Double asterisks with spaces
    text = re.sub(r'\*\* +', '**', text)
    text = re.sub(r' +\*\*', '**', text)

    # 8. Strip leading/trailing whitespace and artifacts
    text = text.strip()

    # 9. Remove trailing incomplete sentences (if response was cut off)
    if text and not text[-1] in '.!?"\')]}:':
        # Check if last line seems incomplete
        last_newline = text.rfind('\n')
        if last_newline > len(text) * 0.8:
            last_line = text[last_newline:].strip()
            if len(last_line) < 20 and not last_line.endswith(('.', '!', '?', ':', '"')):
                text = text[:last_newline].strip()

    return text


def validate_api_key(base_url, api_key):
    """
    Quick validation that the API key works.
    Returns (True, model_info) or (False, error_message).
    """
    try:
        # Try a minimal request
        result = chat_completion(
            base_url, api_key,
            "meta/llama-3.3-70b-instruct",
            [{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        return True, "API key is valid"
    except APIError as e:
        if e.status_code == 401:
            return False, "Invalid API key"
        elif e.status_code == 404:
            # Key works but model might not exist — that's fine
            return True, "API key is valid (model check skipped)"
        else:
            return False, str(e)
    except Exception as e:
        return False, f"Connection error: {e}"
