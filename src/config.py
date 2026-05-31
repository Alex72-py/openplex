"""
Configuration management for OpenPlex.
Stores settings in ~/.openplex/config.json
Supports multiple providers: NVIDIA NIM, Google AI Studio, OpenRouter
"""

import os
import json

CONFIG_DIR = os.path.expanduser("~/.openplex")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_DIR = os.path.join(CONFIG_DIR, "history")

# ─────────────────────────────────────────────
# Provider definitions
# ─────────────────────────────────────────────

PROVIDERS = {
    "nvidia": {
        "name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_prefix": "nvapi-",
        "key_url": "https://build.nvidia.com",
        "key_hint": "Starts with 'nvapi-'",
        "free_tier": True,
        "notes": "40 req/min",
    },
    "google": {
        "name": "Google AI Studio",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_prefix": "AIza",
        "key_url": "https://aistudio.google.com/app/apikey",
        "key_hint": "Starts with 'AIza'",
        "free_tier": True,
        "notes": "Free tier: 15 req/min, 1M tokens/day",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "key_prefix": "sk-or-",
        "key_url": "https://openrouter.ai/keys",
        "key_hint": "Starts with 'sk-or-'",
        "free_tier": True,
        "notes": "Many free models available (marked :free)",
    },
}

# ─────────────────────────────────────────────
# Models per provider
# ─────────────────────────────────────────────

MODELS_BY_PROVIDER = {
    "nvidia": {
        "deepseek-r1": {
            "id": "deepseek-ai/deepseek-r1",
            "name": "DeepSeek R1",
            "description": "Best for reasoning, math, and code",
            "context": 32768,
            "provider": "nvidia",
        },
        "llama-3.3-70b": {
            "id": "meta/llama-3.3-70b-instruct",
            "name": "Llama 3.3 70B",
            "description": "General-purpose, fast responses",
            "context": 32768,
            "provider": "nvidia",
        },
        "nemotron-super": {
            "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "name": "Nemotron Ultra 253B",
            "description": "NVIDIA's best reasoning model",
            "context": 32768,
            "provider": "nvidia",
        },
        "qwen-2.5-72b": {
            "id": "qwen/qwen2.5-72b-instruct",
            "name": "Qwen 2.5 72B",
            "description": "Strong multilingual and coding",
            "context": 32768,
            "provider": "nvidia",
        },
        "mistral-small": {
            "id": "mistralai/mistral-small-24b-instruct-2501",
            "name": "Mistral Small 24B",
            "description": "Fast, efficient, multilingual",
            "context": 32768,
            "provider": "nvidia",
        },
    },
    "google": {
        "gemini-2.5-flash": {
            "id": "models/gemini-2.5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "Fast, smart, free — best overall",
            "context": 1048576,
            "provider": "google",
        },
        "gemini-2.0-flash": {
            "id": "models/gemini-2.0-flash",
            "name": "Gemini 2.0 Flash",
            "description": "Stable, fast multimodal model",
            "context": 1048576,
            "provider": "google",
        },
        "gemini-2.0-flash-lite": {
            "id": "models/gemini-2.0-flash-lite",
            "name": "Gemini 2.0 Flash Lite",
            "description": "Lightest, fastest, free tier",
            "context": 1048576,
            "provider": "google",
        },
        "gemini-2.5-pro": {
            "id": "models/gemini-2.5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "Most capable Gemini, complex tasks",
            "context": 2097152,
            "provider": "google",
        },
    },
    "openrouter": {
        "llama-3.3-70b-free": {
            "id": "meta-llama/llama-3.3-70b-instruct:free",
            "name": "Llama 3.3 70B (Free)",
            "description": "Free tier, general purpose",
            "context": 131072,
            "provider": "openrouter",
        },
        "deepseek-r1-free": {
            "id": "deepseek/deepseek-r1:free",
            "name": "DeepSeek R1 (Free)",
            "description": "Free tier, reasoning model",
            "context": 163840,
            "provider": "openrouter",
        },
        "deepseek-v3-free": {
            "id": "deepseek/deepseek-chat-v3-0324:free",
            "name": "DeepSeek V3 (Free)",
            "description": "Free tier, fast and capable",
            "context": 163840,
            "provider": "openrouter",
        },
        "gemma-3-27b-free": {
            "id": "google/gemma-3-27b-it:free",
            "name": "Gemma 3 27B (Free)",
            "description": "Google open model, free tier",
            "context": 131072,
            "provider": "openrouter",
        },
        "qwen3-235b-free": {
            "id": "qwen/qwen3-235b-a22b:free",
            "name": "Qwen3 235B MoE (Free)",
            "description": "Massive MoE, free tier",
            "context": 40960,
            "provider": "openrouter",
        },
        "mistral-7b-free": {
            "id": "mistralai/mistral-7b-instruct:free",
            "name": "Mistral 7B (Free)",
            "description": "Lightweight, fast, free",
            "context": 32768,
            "provider": "openrouter",
        },
    },
}

# Flat merged model list (for backward compat / quick lookup)
AVAILABLE_MODELS = {}
for _provider_models in MODELS_BY_PROVIDER.values():
    AVAILABLE_MODELS.update(_provider_models)

# Default provider and model
DEFAULT_PROVIDER = "nvidia"
DEFAULT_MODEL = "deepseek-ai/deepseek-r1"

DEFAULT_CONFIG = {
    "provider": DEFAULT_PROVIDER,
    "api_key": "",
    # Per-provider keys stored separately
    "api_keys": {
        "nvidia": "",
        "google": "",
        "openrouter": "",
    },
    "model": DEFAULT_MODEL,
    "base_url": PROVIDERS[DEFAULT_PROVIDER]["base_url"],
    "temperature": 0.6,
    "max_tokens": 4096,
    "max_sources": 8,
    "search_depth": "standard",
    "verify_sources": True,
    "show_sources": True,
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
            # Deep merge: start from defaults, overlay stored values
            config = {**DEFAULT_CONFIG, **stored}
            # Ensure api_keys dict exists and is complete
            if "api_keys" not in config:
                config["api_keys"] = DEFAULT_CONFIG["api_keys"].copy()
            else:
                for p in DEFAULT_CONFIG["api_keys"]:
                    if p not in config["api_keys"]:
                        config["api_keys"][p] = ""
            # Back-compat: if old single api_key exists, migrate it
            if config.get("api_key") and not config["api_keys"].get(config.get("provider", DEFAULT_PROVIDER)):
                prov = config.get("provider", DEFAULT_PROVIDER)
                config["api_keys"][prov] = config["api_key"]
        except (json.JSONDecodeError, IOError):
            config = DEFAULT_CONFIG.copy()
            config["api_keys"] = DEFAULT_CONFIG["api_keys"].copy()
    else:
        config = DEFAULT_CONFIG.copy()
        config["api_keys"] = DEFAULT_CONFIG["api_keys"].copy()

    # Environment variable overrides
    if os.environ.get("OPENPLEX_API_KEY"):
        prov = config.get("provider", DEFAULT_PROVIDER)
        config["api_keys"][prov] = os.environ["OPENPLEX_API_KEY"]
        config["api_key"] = os.environ["OPENPLEX_API_KEY"]
    if os.environ.get("OPENPLEX_NVIDIA_KEY"):
        config["api_keys"]["nvidia"] = os.environ["OPENPLEX_NVIDIA_KEY"]
    if os.environ.get("OPENPLEX_GOOGLE_KEY"):
        config["api_keys"]["google"] = os.environ["OPENPLEX_GOOGLE_KEY"]
    if os.environ.get("OPENPLEX_OPENROUTER_KEY"):
        config["api_keys"]["openrouter"] = os.environ["OPENPLEX_OPENROUTER_KEY"]
    if os.environ.get("OPENPLEX_MODEL"):
        config["model"] = os.environ["OPENPLEX_MODEL"]
    if os.environ.get("OPENPLEX_PROVIDER"):
        config["provider"] = os.environ["OPENPLEX_PROVIDER"]

    # Always sync active api_key from provider-specific key
    prov = config.get("provider", DEFAULT_PROVIDER)
    active_key = config["api_keys"].get(prov, "")
    config["api_key"] = active_key

    # Always sync base_url from provider
    config["base_url"] = PROVIDERS.get(prov, PROVIDERS[DEFAULT_PROVIDER])["base_url"]

    return config


def save_config(config):
    """Save config to file."""
    ensure_dirs()
    # Always sync api_key into api_keys before saving
    prov = config.get("provider", DEFAULT_PROVIDER)
    if config.get("api_key"):
        if "api_keys" not in config:
            config["api_keys"] = {}
        config["api_keys"][prov] = config["api_key"]
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def switch_provider(config, provider_name):
    """
    Switch to a different provider. Updates base_url and active api_key.
    Returns updated config.
    """
    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_name}. Choose from: {', '.join(PROVIDERS)}")

    config["provider"] = provider_name
    config["base_url"] = PROVIDERS[provider_name]["base_url"]
    config["api_key"] = config.get("api_keys", {}).get(provider_name, "")

    # Set a sensible default model for the new provider
    provider_models = MODELS_BY_PROVIDER.get(provider_name, {})
    if provider_models:
        first_model = list(provider_models.values())[0]
        config["model"] = first_model["id"]

    return config


def get_model_id(short_name, provider=None):
    """
    Get full model ID from short name.
    Optionally scoped to a provider.
    """
    # Check provider-scoped models first
    if provider and provider in MODELS_BY_PROVIDER:
        provider_models = MODELS_BY_PROVIDER[provider]
        if short_name in provider_models:
            return provider_models[short_name]["id"]

    # Check all models
    if short_name in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[short_name]["id"]

    # Maybe they passed a full model ID directly
    for key, val in AVAILABLE_MODELS.items():
        if val["id"] == short_name:
            return short_name

    return short_name  # Return as-is (custom model)


def get_active_provider_models(config):
    """Get the model dict for the currently active provider."""
    prov = config.get("provider", DEFAULT_PROVIDER)
    return MODELS_BY_PROVIDER.get(prov, MODELS_BY_PROVIDER[DEFAULT_PROVIDER])
