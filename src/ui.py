"""
OpenPlex Terminal UI.
Uses 'rich' for beautiful terminal output.
Falls back to plain text if rich is not installed.
"""

import sys

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

BRAND_COLOR = "cyan"
ERROR_COLOR = "red"
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"

PROVIDER_COLORS = {
    "nvidia": "green",
    "google": "blue",
    "openrouter": "magenta",
}


class UI:
    def __init__(self):
        self.console = Console() if HAS_RICH else None

    def banner(self):
        if HAS_RICH:
            t = Text()
            t.append("  ╔══════════════════════════════════════╗\n", style=BRAND_COLOR)
            t.append("  ║", style=BRAND_COLOR)
            t.append("         ◆  OpenPlex  ◆               ", style=f"bold {BRAND_COLOR}")
            t.append("║\n", style=BRAND_COLOR)
            t.append("  ║", style=BRAND_COLOR)
            t.append("  AI Search · Cited Answers · 3 Providers ", style="dim")
            t.append("║\n", style=BRAND_COLOR)
            t.append("  ╚══════════════════════════════════════╝", style=BRAND_COLOR)
            self.console.print(t)
            self.console.print("  [dim]Type a question or /help for commands[/dim]\n")
        else:
            print("\n  ◆ OpenPlex ◆  AI Search · Cited Answers · 3 Providers")
            print("  Type a question or /help for commands\n")

    def prompt(self, model_name=""):
        try:
            if HAS_RICH:
                self.console.print(f"[bold {BRAND_COLOR}]❯[/bold {BRAND_COLOR}] ", end="")
            else:
                print("❯ ", end="")
            return input("")
        except (EOFError, KeyboardInterrupt):
            return None

    def status(self, message):
        line = f"  ⟳ {message}"
        if HAS_RICH:
            self.console.print(f"[dim]{line}[/dim]" + " " * 20, end="\r")
        else:
            print(line + " " * 20, end="\r")

    def clear_status(self):
        print(" " * 80, end="\r")

    def answer(self, text, sources=None, mode="search"):
        self.clear_status()
        if HAS_RICH:
            self.console.print()
            if mode in ("search", "chat") and text:
                border = BRAND_COLOR if mode == "search" else "dim"
                title = "[bold]Answer[/bold]" if mode == "search" else None
                self.console.print(Panel(Markdown(text), border_style=border, padding=(1, 2), title=title, title_align="left"))
            else:
                self.console.print(f"\n  {text}\n")
            if sources:
                self.show_sources(sources)
            self.console.print()
        else:
            print(f"\n{text}")
            if sources:
                self.show_sources(sources)
            print()

    def show_sources(self, sources):
        if not sources:
            return
        if HAS_RICH:
            self.console.print(f"\n  [bold]Sources:[/bold]")
            for i, s in enumerate(sources, 1):
                title = s.get("title", "Unknown")[:65]
                url = s.get("url", "")
                self.console.print(f"  [{BRAND_COLOR}][{i}][/{BRAND_COLOR}] [link={url}]{title}[/link]")
                self.console.print(f"      [dim]{url[:72]}[/dim]")
        else:
            print("\n  Sources:")
            for i, s in enumerate(sources, 1):
                print(f"  [{i}] {s.get('title','')[:65]}")
                print(f"      {s.get('url','')[:72]}")

    def error(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {ERROR_COLOR}]✗[/bold {ERROR_COLOR}] [red]{msg}[/red]\n")
        else:
            print(f"\n  ✗ {msg}\n")

    def success(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {SUCCESS_COLOR}]✓[/bold {SUCCESS_COLOR}] [green]{msg}[/green]\n")
        else:
            print(f"\n  ✓ {msg}\n")

    def warning(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {WARNING_COLOR}]![/bold {WARNING_COLOR}] [yellow]{msg}[/yellow]\n")
        else:
            print(f"\n  ! {msg}\n")

    def info(self, msg):
        if HAS_RICH:
            self.console.print(f"  [dim]{msg}[/dim]")
        else:
            print(f"  {msg}")

    def provider_list(self, providers, current_provider):
        if HAS_RICH:
            t = Table(title="Providers", box=box.ROUNDED, border_style=BRAND_COLOR, show_header=True, header_style="bold")
            t.add_column("Key", style="cyan")
            t.add_column("Name")
            t.add_column("Free Tier")
            t.add_column("Notes", style="dim")
            t.add_column("Active", justify="center")
            for key, info in providers.items():
                active = Text("●", style=SUCCESS_COLOR) if key == current_provider else Text("")
                free = Text("✓ Free", style=SUCCESS_COLOR) if info.get("free_tier") else Text("Paid")
                t.add_row(key, info["name"], free, info.get("notes", ""), active)
            self.console.print()
            self.console.print(t)
            self.console.print()
        else:
            print("\n  Providers:")
            for key, info in providers.items():
                active = " ← active" if key == current_provider else ""
                print(f"  • {key}: {info['name']} — {info.get('notes','')}{active}")
            print()

    def model_list(self, models, current_model):
        if HAS_RICH:
            t = Table(title="Models (current provider)", box=box.ROUNDED, border_style=BRAND_COLOR, show_header=True, header_style="bold")
            t.add_column("Short Name", style="cyan")
            t.add_column("Full ID", style="dim")
            t.add_column("Description")
            t.add_column("Active", justify="center")
            for key, info in models.items():
                active = Text("●", style=SUCCESS_COLOR) if info["id"] == current_model else Text("")
                t.add_row(key, info["id"], info["description"], active)
            self.console.print()
            self.console.print(t)
            self.console.print()
        else:
            print("\n  Models:")
            for key, info in models.items():
                active = " ← active" if info["id"] == current_model else ""
                print(f"  • {key}: {info['description']}{active}")
                print(f"    {info['id']}")
            print()

    def help_text(self):
        cmds = [
            ("/provider list", "Show all providers (NVIDIA, Google, OpenRouter)"),
            ("/provider set <name>", "Switch provider (nvidia / google / openrouter)"),
            ("/provider key <key>", "Set API key for current provider"),
            ("/provider status", "Show current provider & key status"),
            ("/model list", "Show models for current provider"),
            ("/model set <name>", "Switch model"),
            ("/deep <question>", "Deep research mode (more sources)"),
            ("/sources", "Show sources from last answer"),
            ("/clear", "Clear conversation history"),
            ("/config", "Show full configuration"),
            ("/config temp <0-2>", "Set temperature"),
            ("/config tokens <n>", "Set max response tokens"),
            ("/status", "Show session status"),
            ("/help", "Show this help"),
            ("/exit", "Exit OpenPlex"),
        ]
        if HAS_RICH:
            t = Table(box=box.SIMPLE, show_header=True, header_style="bold", border_style="dim")
            t.add_column("Command", style="cyan")
            t.add_column("Description")
            for cmd, desc in cmds:
                t.add_row(cmd, desc)
            self.console.print()
            self.console.print(Panel(t, title="[bold]OpenPlex Commands[/bold]", border_style=BRAND_COLOR))
            self.console.print("  [dim]Or just type any question to search and get cited answers.[/dim]\n")
        else:
            print("\n  OpenPlex Commands:")
            for cmd, desc in cmds:
                print(f"  {cmd:<30} {desc}")
            print()

    def config_display(self, config):
        prov = config.get("provider", "nvidia")
        api_key = config.get("api_key", "")
        masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else ("(not set)" if not api_key else api_key)

        # Show all stored keys
        api_keys = config.get("api_keys", {})

        if HAS_RICH:
            t = Table(box=box.ROUNDED, border_style=BRAND_COLOR)
            t.add_column("Setting", style="cyan")
            t.add_column("Value")
            t.add_column("Notes", style="dim")

            t.add_row("Provider", prov, PROVIDER_COLORS.get(prov, ""))
            t.add_row("Active Key", masked, "Use /provider key <key> to set")
            for p, k in api_keys.items():
                mk = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else ("(not set)" if not k else k)
                t.add_row(f"  {p} key", mk, "")
            t.add_row("Model", config.get("model", ""), "")
            t.add_row("Base URL", config.get("base_url", ""), "")
            t.add_row("Temperature", str(config.get("temperature", 0.6)), "")
            t.add_row("Max Tokens", str(config.get("max_tokens", 4096)), "")
            t.add_row("Max Sources", str(config.get("max_sources", 8)), "")
            self.console.print()
            self.console.print(Panel(t, title="[bold]Configuration[/bold]", border_style=BRAND_COLOR))
            self.console.print()
        else:
            print(f"\n  Provider:    {prov}")
            print(f"  Active Key:  {masked}")
            for p, k in api_keys.items():
                mk = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else ("(not set)" if not k else k)
                print(f"    {p}: {mk}")
            print(f"  Model:       {config.get('model','')}")
            print(f"  Temperature: {config.get('temperature',0.6)}")
            print(f"  Max Tokens:  {config.get('max_tokens',4096)}")
            print()
