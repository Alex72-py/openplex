"""
OpenPlex — Main application loop.
Handles commands, setup wizard, and orchestrates the answer engine.
"""

import sys
import os
import json

from config import (
    load_config, save_config, AVAILABLE_MODELS,
    get_model_id, CONFIG_FILE, ensure_dirs
)
from engine import AnswerEngine
from ui import UI
from api_client import APIError, validate_api_key


def setup_wizard(ui, config):
    """First-run setup wizard to configure API key and model."""
    ui.info("Welcome to OpenPlex! Let's get you set up.\n")
    ui.info("You need an NVIDIA NIM API key (free at build.nvidia.com)")
    ui.info("1. Go to https://build.nvidia.com")
    ui.info("2. Sign up / Sign in")
    ui.info("3. Go to Settings → API Keys")
    ui.info("4. Generate a key (starts with 'nvapi-')\n")

    while True:
        try:
            api_key = input("  Enter your API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            sys.exit(0)

        if not api_key:
            ui.error("API key cannot be empty.")
            continue

        if not api_key.startswith("nvapi-"):
            ui.warning("Key doesn't start with 'nvapi-'. Are you sure it's correct?")
            try:
                confirm = input("  Continue anyway? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                sys.exit(0)
            if confirm != 'y':
                continue

        config["api_key"] = api_key
        break

    # Model selection
    ui.info("\nChoose a default model:\n")
    model_keys = list(AVAILABLE_MODELS.keys())
    for i, key in enumerate(model_keys, 1):
        info = AVAILABLE_MODELS[key]
        ui.info(f"  {i}. {info['name']} — {info['description']}")

    ui.info(f"\n  Default: 1 ({AVAILABLE_MODELS[model_keys[0]]['name']})")

    try:
        choice = input("\n  Enter number (or press Enter for default): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if choice.isdigit() and 1 <= int(choice) <= len(model_keys):
        selected = model_keys[int(choice) - 1]
    else:
        selected = model_keys[0]

    config["model"] = AVAILABLE_MODELS[selected]["id"]

    # Save config
    save_config(config)
    ui.success(f"Config saved! Using {AVAILABLE_MODELS[selected]['name']}")
    ui.info(f"  Config file: {CONFIG_FILE}\n")

    return config


def handle_command(command, args, engine, config, ui):
    """Handle slash commands. Returns updated config or None."""

    if command == "help":
        ui.help_text()

    elif command == "exit" or command == "quit" or command == "q":
        ui.info("Goodbye!")
        sys.exit(0)

    elif command == "clear":
        engine.clear_history()
        ui.success("Conversation history cleared.")

    elif command == "status":
        model_name = config["model"].split("/")[-1]
        history_len = len(engine.conversation_history) // 2
        ui.info(f"  Model: {config['model']}")
        ui.info(f"  Conversation: {history_len} exchanges")
        ui.info(f"  Last sources: {len(engine.last_sources)}")
        ui.info("")

    elif command == "sources":
        if engine.last_sources:
            ui.show_sources(engine.last_sources)
        else:
            ui.info("  No sources from last query.")

    elif command == "config":
        if args and args[0] == "key" and len(args) > 1:
            # Set API key
            new_key = args[1]
            config["api_key"] = new_key
            save_config(config)
            engine.update_config(config)
            ui.success("API key updated.")
        elif args and args[0] == "temp" and len(args) > 1:
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

    elif command == "model":
        if not args:
            ui.info(f"  Current model: {config['model']}")
            ui.info("  Use /model list or /model set <name>")
        elif args[0] == "list":
            ui.model_list(AVAILABLE_MODELS, config["model"])
        elif args[0] == "set" and len(args) > 1:
            model_name = args[1]
            model_id = get_model_id(model_name)
            config["model"] = model_id
            save_config(config)
            engine.update_config(config)

            # Find display name
            display_name = model_id
            for key, info in AVAILABLE_MODELS.items():
                if info["id"] == model_id:
                    display_name = info["name"]
                    break

            ui.success(f"Switched to {display_name} ({model_id})")
        else:
            ui.info("  Usage: /model list | /model set <name>")

    elif command == "deep":
        # Deep research mode — handled in main loop
        return "deep"

    else:
        ui.warning(f"Unknown command: /{command}. Type /help for available commands.")

    return config


def main():
    """Main application entry point."""
    ui = UI()

    # Load or create config
    config = load_config()

    # Check if first run (no API key)
    if not config.get("api_key"):
        ui.banner()
        config = setup_wizard(ui, config)
    else:
        ui.banner()

    # Initialize engine
    engine = AnswerEngine(config)

    # Main loop
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

        # Handle commands
        if user_input.startswith("/"):
            parts = user_input[1:].split()
            command = parts[0].lower() if parts else ""
            args = parts[1:] if len(parts) > 1 else []

            if command == "deep":
                # Deep research: rest of the line is the query
                query = " ".join(args)
                if not query:
                    ui.warning("Usage: /deep <your question>")
                    continue

                def status_callback(msg):
                    ui.status(msg)

                result = engine.answer(query, deep=True, callback=status_callback)
                ui.clear_status()
                ui.answer(result["answer"], result["sources"], result["mode"])
            else:
                result = handle_command(command, args, engine, config, ui)
                if isinstance(result, dict):
                    config = result
            continue

        # Regular question — run through the answer engine
        def status_callback(msg):
            ui.status(msg)

        try:
            result = engine.answer(user_input, deep=False, callback=status_callback)
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
