"""
Configuration management for OpenPlex.
Stores settings in ~/.openplex/config.json
"""

import os
import json

CONFIG_DIR = os.path.expanduser("~/.openplex")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_DIR = os.path.join(CONFIG_DIR, "history")

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "deepseek-ai/deepseek-r1",
    "base_url": "https://integrate.api.nvidia.com/v1",
    "temperature": 0.6,
    "max_tokens": 4096,
    "max_sources": 8,
    "search_depth": "standard",  # "standard" or "deep"
    "verify_sources": True,
    "show_sources": True,
}

AVAILABLE_MODELS = {
    "deepseek-r1": {
        "id": "deepseek-ai/deepseek-r1",
        "name": "DeepSeek R1",
        "description": "Best for reasoning, math, and code",
        "context": 32768,
    },
    "llama-3.3-70b": {
        "id": "meta/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B",
        "description": "General-purpose, fast responses",
        "context": 32768,
    },
    "nemotron-super": {
        "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "name": "Nemotron Ultra 253B",
        "description": "NVIDIA's best reasoning model",
        "context": 32768,
    },
    "qwen-2.5-72b": {
        "id": "qwen/qwen2.5-72b-instruct",
        "name": "Qwen 2.5 72B",
        "description": "Strong multilingual and coding",
        "context": 32768,
    },
    "mistral-small": {
        "id": "mistralai/mistral-small-24b-instruct-2501",
        "name": "Mistral Small 24B",
        "description": "Fast, efficient, multilingual",
        "context": 32768,
    },
}


def ensure_dirs():
    """Create config and history directories if they don't exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)


def load_config():
    """Load config from file, creating defaults if needed. Env vars override."""
    ensure_dirs()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                stored = json.load(f)
            # Merge with defaults (in case new keys were added)
            config = {**DEFAULT_CONFIG, **stored}
        except (json.JSONDecodeError, IOError):
            config = DEFAULT_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()

    # Environment variable overrides
    if os.environ.get("OPENPLEX_API_KEY"):
        config["api_key"] = os.environ["OPENPLEX_API_KEY"]
    if os.environ.get("OPENPLEX_MODEL"):
        config["model"] = os.environ["OPENPLEX_MODEL"]
    if os.environ.get("OPENPLEX_BASE_URL"):
        config["base_url"] = os.environ["OPENPLEX_BASE_URL"]

    return config


def save_config(config):
    """Save config to file."""
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_model_id(short_name):
    """Get full model ID from short name."""
    if short_name in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[short_name]["id"]
    # Maybe they passed a full model ID directly
    for key, val in AVAILABLE_MODELS.items():
        if val["id"] == short_name:
            return short_name
    return short_name  # Return as-is, might be a custom model
