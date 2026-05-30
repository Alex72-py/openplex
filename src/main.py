"""
OpenPlex — Main application loop.
Handles commands, setup wizard, and orchestrates the answer engine.
"""

import sys
import os

from config import (
    load_config, save_config, AVAILABLE_MODELS, PROVIDERS,
    MODELS_BY_PROVIDER, get_model_id, get_active_provider_models,
    switch_provider, CONFIG_FILE, ensure_dirs
)
from engine import AnswerEngine
from ui import UI
from api_client import APIError, validate_api_key


def setup_wizard(ui, config):
    """First-run setup wizard — choose provider and enter API key."""
    ui.info("Welcome to OpenPlex! Let's get you set up.\n")

    # Step 1: Choose provider
    provider_keys = list(PROVIDERS.keys())
    ui.info("Choose your AI provider:\n")
    for i, key in enumerate(provider_keys, 1):
        p = PROVIDERS[key]
        free_tag = "[FREE]" if p.get("free_tier") else "[PAID]"
        ui.info(f"  {i}. {p['name']} {free_tag} — {p['notes']}")
        ui.info(f"     Get key: {p['key_url']}")
        ui.info("")

    try:
        choice = input("  Enter number (default 1 = NVIDIA NIM): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if choice.isdigit() and 1 <= int(choice) <= len(provider_keys):
        provider_name = provider_keys[int(choice) - 1]
    else:
        provider_name = provider_keys[0]

    provider_info = PROVIDERS[provider_name]
    ui.info(f"\nSelected: {provider_info['name']}")
    ui.info(f"Get your free API key at: {provider_info['key_url']}\n")

    # Step 2: Enter API key
    while True:
        try:
            api_key = input(f"  Enter your {provider_info['name']} API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not api_key:
            ui.error("API key cannot be empty.")
            continue

        prefix = provider_info.get("key_prefix", "")
        if prefix and not api_key.startswith(prefix):
            ui.warning(f"Key doesn't start with '{prefix}'. Are you sure it's correct?")
            try:
                confirm = input("  Continue anyway? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(0)
            if confirm != 'y':
                continue

        config["provider"] = provider_name
        config["api_key"] = api_key
        if "api_keys" not in config:
            config["api_keys"] = {}
        config["api_keys"][provider_name] = api_key
        config["base_url"] = provider_info["base_url"]
        break

    # Step 3: Choose default model from that provider
    provider_models = MODELS_BY_PROVIDER.get(provider_name, {})
    model_keys = list(provider_models.keys())
    ui.info(f"\nChoose a default model for {provider_info['name']}:\n")
    for i, key in enumerate(model_keys, 1):
        m = provider_models[key]
        ui.info(f"  {i}. {m['name']} — {m['description']}")

    try:
        choice = input("\n  Enter number (default 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if choice.isdigit() and 1 <= int(choice) <= len(model_keys):
        selected = model_keys[int(choice) - 1]
    else:
        selected = model_keys[0]

    config["model"] = provider_models[selected]["id"]

    save_config(config)
    ui.success(f"Config saved! Provider: {provider_info['name']} | Model: {provider_models[selected]['name']}")
    ui.info(f"  Config file: {CONFIG_FILE}\n")
    return config


def handle_command(command, args, engine, config, ui):
    """Handle slash commands. Returns updated config dict."""

    if command == "help":
        ui.help_text()

    elif command in ("exit", "quit", "q"):
        ui.info("Goodbye!")
        sys.exit(0)

    elif command == "clear":
        engine.clear_history()
        ui.success("Conversation history cleared.")

    elif command == "status":
        prov = config.get("provider", "nvidia")
        history_len = len(engine.conversation_history) // 2
        ui.info(f"  Provider:     {PROVIDERS.get(prov, {}).get('name', prov)}")
        ui.info(f"  Model:        {config['model']}")
        ui.info(f"  Conversation: {history_len} exchanges")
        ui.info(f"  Last sources: {len(engine.last_sources)}")
        ui.info("")

    elif command == "sources":
        if engine.last_sources:
            ui.show_sources(engine.last_sources)
        else:
            ui.info("  No sources from last query.")

    elif command == "provider":
        if not args:
            ui.info(f"  Current provider: {config.get('provider','nvidia')}")
            ui.info("  Use /provider list | /provider set <name> | /provider key <key>")

        elif args[0] == "list":
            ui.provider_list(PROVIDERS, config.get("provider", "nvidia"))

        elif args[0] == "set" and len(args) > 1:
            pname = args[1].lower()
            if pname not in PROVIDERS:
                ui.error(f"Unknown provider '{pname}'. Choose from: {', '.join(PROVIDERS)}")
            else:
                config = switch_provider(config, pname)
                # Check if we have a key for this provider
                stored_key = config.get("api_keys", {}).get(pname, "")
                if not stored_key:
                    pinfo = PROVIDERS[pname]
                    ui.warning(f"No API key set for {pinfo['name']}.")
                    ui.info(f"  Get one free at: {pinfo['key_url']}")
                    ui.info(f"  Then run: /provider key <your-key>")
                else:
                    save_config(config)
                    engine.update_config(config)
                    ui.success(f"Switched to {PROVIDERS[pname]['name']} | Model: {config['model']}")

        elif args[0] == "key" and len(args) > 1:
            new_key = args[1]
            prov = config.get("provider", "nvidia")
            if "api_keys" not in config:
                config["api_keys"] = {}
            config["api_keys"][prov] = new_key
            config["api_key"] = new_key
            save_config(config)
            engine.update_config(config)
            ui.success(f"API key updated for {PROVIDERS.get(prov,{}).get('name', prov)}.")

        elif args[0] == "status":
            prov = config.get("provider", "nvidia")
            pinfo = PROVIDERS.get(prov, {})
            api_keys = config.get("api_keys", {})
            ui.info(f"\n  Active provider: {pinfo.get('name', prov)}")
            ui.info(f"  Base URL:        {config.get('base_url','')}")
            for p, k in api_keys.items():
                status_str = "✓ set" if k else "✗ not set"
                ui.info(f"  {p} key:  {status_str}")
            ui.info("")

        else:
            ui.info("  Usage: /provider list | set <name> | key <key> | status")

    elif command == "model":
        if not args:
            ui.info(f"  Current model: {config['model']}")
            ui.info("  Use /model list or /model set <name>")
        elif args[0] == "list":
            active_models = get_active_provider_models(config)
            ui.model_list(active_models, config["model"])
        elif args[0] == "set" and len(args) > 1:
            prov = config.get("provider", "nvidia")
            model_id = get_model_id(args[1], provider=prov)
            config["model"] = model_id
            save_config(config)
            engine.update_config(config)
            # Find display name
            display = model_id
            for info in AVAILABLE_MODELS.values():
                if info["id"] == model_id:
                    display = info["name"]
                    break
            ui.success(f"Switched to {display}")
        else:
            ui.info("  Usage: /model list | /model set <name>")

    elif command == "config":
        if args and args[0] == "temp" and len(args) > 1:
            try:
                temp = float(args[1])
                if 0 <= temp <= 2:
                    config["temperature"] = temp
                    save_config(config)
                    engine.update_config(config)
                    ui.success(f"Temperature set to {temp}")
                else:
                    ui.error("Temperature must be between 0 and 2.")
            except ValueError:
                ui.error("Invalid temperature value.")
        elif args and args[0] == "tokens" and len(args) > 1:
            try:
                tokens = int(args[1])
                if 100 <= tokens <= 32000:
                    config["max_tokens"] = tokens
                    save_config(config)
                    engine.update_config(config)
                    ui.success(f"Max tokens set to {tokens}")
                else:
                    ui.error("Tokens must be between 100 and 32000.")
            except ValueError:
                ui.error("Invalid token value.")
        else:
            ui.config_display(config)

    elif command == "deep":
        return "deep"

    else:
        ui.warning(f"Unknown command: /{command}. Type /help for commands.")

    return config


def main():
    ui = UI()
    config = load_config()

    if not config.get("api_key"):
        ui.banner()
        config = setup_wizard(ui, config)
    else:
        ui.banner()
        prov = config.get("provider", "nvidia")
        ui.info(f"  Provider: {PROVIDERS.get(prov,{}).get('name', prov)}  |  Model: {config['model'].split('/')[-1]}\n")

    engine = AnswerEngine(config)

    while True:
        try:
            user_input = ui.prompt(config.get("model", ""))
        except (EOFError, KeyboardInterrupt):
            print()
            ui.info("Goodbye!")
            break

        if user_input is None:
            print()
            ui.info("Goodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input[1:].split()
            command = parts[0].lower() if parts else ""
            args = parts[1:] if len(parts) > 1 else []

            if command == "deep":
                query = " ".join(args)
                if not query:
                    ui.warning("Usage: /deep <your question>")
                    continue
                result = engine.answer(query, deep=True, callback=ui.status)
                ui.clear_status()
                ui.answer(result["answer"], result["sources"], result["mode"])
            else:
                result = handle_command(command, args, engine, config, ui)
                if isinstance(result, dict):
                    config = result
            continue

        try:
            result = engine.answer(user_input, deep=False, callback=ui.status)
            ui.clear_status()
            ui.answer(result["answer"], result["sources"], result["mode"])
        except APIError as e:
            ui.clear_status()
            ui.error(str(e))
        except KeyboardInterrupt:
            ui.clear_status()
            ui.info("\n  Search cancelled.")
        except Exception as e:
            ui.clear_status()
            ui.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
