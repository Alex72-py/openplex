"""
OpenPlex Terminal UI.
Uses 'rich' for beautiful terminal output.
Falls back to plain text if rich is not installed.
"""

import sys
import os

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.rule import Rule
    from rich.style import Style
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# Color scheme
BRAND_COLOR = "cyan"
ACCENT_COLOR = "bright_blue"
SOURCE_COLOR = "dim"
ERROR_COLOR = "red"
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"


class UI:
    """Terminal UI handler for OpenPlex."""

    def __init__(self):
        if HAS_RICH:
            self.console = Console()
        else:
            self.console = None

    def banner(self):
        """Display the OpenPlex banner."""
        if HAS_RICH:
            banner_text = Text()
            banner_text.append("  ╔═══════════════════════════════════╗\n", style=BRAND_COLOR)
            banner_text.append("  ║", style=BRAND_COLOR)
            banner_text.append("        ◆ OpenPlex ◆              ", style=f"bold {BRAND_COLOR}")
            banner_text.append("║\n", style=BRAND_COLOR)
            banner_text.append("  ║", style=BRAND_COLOR)
            banner_text.append("   AI Search • Cited Answers      ", style="dim")
            banner_text.append("║\n", style=BRAND_COLOR)
            banner_text.append("  ╚═══════════════════════════════════╝", style=BRAND_COLOR)
            self.console.print(banner_text)
            self.console.print(f"  [dim]Type your question or /help for commands[/dim]\n")
        else:
            print("\n  ◆ OpenPlex ◆")
            print("  AI Search • Cited Answers")
            print("  Type your question or /help for commands\n")

    def prompt(self, model_name=""):
        """Get user input with styled prompt."""
        if HAS_RICH:
            try:
                short_model = model_name.split("/")[-1][:20] if model_name else ""
                prompt_text = f"[bold {BRAND_COLOR}]❯[/bold {BRAND_COLOR}] "
                self.console.print(prompt_text, end="")
                return input("")
            except (EOFError, KeyboardInterrupt):
                return None
        else:
            try:
                return input("❯ ")
            except (EOFError, KeyboardInterrupt):
                return None

    def status(self, message):
        """Show a status message (searching, thinking, etc.)."""
        if HAS_RICH:
            self.console.print(f"  [dim]⟳ {message}[/dim]", end="\r")
        else:
            print(f"  ⟳ {message}", end="\r")

    def clear_status(self):
        """Clear the status line."""
        if HAS_RICH:
            self.console.print(" " * 80, end="\r")
        else:
            print(" " * 80, end="\r")

    def answer(self, text, sources=None, mode="search"):
        """Display an answer with optional sources."""
        self.clear_status()

        if HAS_RICH:
            self.console.print()

            if mode == "search" and sources:
                # Show answer as markdown in a panel
                md = Markdown(text)
                self.console.print(Panel(
                    md,
                    border_style=BRAND_COLOR,
                    padding=(1, 2),
                    title="[bold]Answer[/bold]",
                    title_align="left",
                ))

                # Show sources
                self.show_sources(sources)
            elif mode == "chat":
                md = Markdown(text)
                self.console.print(Panel(
                    md,
                    border_style="dim",
                    padding=(1, 2),
                ))
            else:
                self.console.print(f"\n  {text}\n")

            self.console.print()
        else:
            print(f"\n{text}")
            if sources:
                self.show_sources(sources)
            print()

    def show_sources(self, sources):
        """Display source citations."""
        if not sources:
            return

        if HAS_RICH:
            self.console.print(f"\n  [bold]Sources:[/bold]")
            for i, source in enumerate(sources, 1):
                title = source.get("title", "Unknown")[:60]
                url = source.get("url", "")
                self.console.print(f"  [{BRAND_COLOR}][{i}][/{BRAND_COLOR}] [link={url}]{title}[/link]")
                self.console.print(f"      [dim]{url[:70]}[/dim]")
        else:
            print("\n  Sources:")
            for i, source in enumerate(sources, 1):
                title = source.get("title", "Unknown")[:60]
                url = source.get("url", "")
                print(f"  [{i}] {title}")
                print(f"      {url[:70]}")

    def error(self, message):
        """Display an error message."""
        if HAS_RICH:
            self.console.print(f"\n  [bold {ERROR_COLOR}]✗[/bold {ERROR_COLOR}] [red]{message}[/red]\n")
        else:
            print(f"\n  ✗ {message}\n")

    def success(self, message):
        """Display a success message."""
        if HAS_RICH:
            self.console.print(f"\n  [bold {SUCCESS_COLOR}]✓[/bold {SUCCESS_COLOR}] [green]{message}[/green]\n")
        else:
            print(f"\n  ✓ {message}\n")

    def warning(self, message):
        """Display a warning message."""
        if HAS_RICH:
            self.console.print(f"\n  [bold {WARNING_COLOR}]![/bold {WARNING_COLOR}] [yellow]{message}[/yellow]\n")
        else:
            print(f"\n  ! {message}\n")

    def info(self, message):
        """Display an info message."""
        if HAS_RICH:
            self.console.print(f"  [dim]{message}[/dim]")
        else:
            print(f"  {message}")

    def model_list(self, models, current_model):
        """Display available models."""
        if HAS_RICH:
            table = Table(
                title="Available Models",
                box=box.ROUNDED,
                border_style=BRAND_COLOR,
                show_header=True,
                header_style="bold",
            )
            table.add_column("Short Name", style="cyan")
            table.add_column("Full ID", style="dim")
            table.add_column("Description")
            table.add_column("Active", justify="center")

            for key, info in models.items():
                active = "●" if info["id"] == current_model else ""
                active_style = SUCCESS_COLOR if active else ""
                table.add_row(
                    key,
                    info["id"],
                    info["description"],
                    Text(active, style=active_style),
                )

            self.console.print()
            self.console.print(table)
            self.console.print()
        else:
            print("\n  Available Models:")
            for key, info in models.items():
                active = " ← active" if info["id"] == current_model else ""
                print(f"  • {key}: {info['description']}{active}")
                print(f"    ID: {info['id']}")
            print()

    def help_text(self):
        """Display help information."""
        if HAS_RICH:
            help_table = Table(
                box=box.SIMPLE,
                show_header=True,
                header_style="bold",
                border_style="dim",
            )
            help_table.add_column("Command", style="cyan")
            help_table.add_column("Description")

            commands = [
                ("/model list", "Show available models"),
                ("/model set <name>", "Switch to a different model"),
                ("/deep <question>", "Deep research mode (more sources)"),
                ("/sources", "Show sources from last answer"),
                ("/clear", "Clear conversation history"),
                ("/config", "Show/edit configuration"),
                ("/config key <api_key>", "Set API key"),
                ("/status", "Show current status"),
                ("/help", "Show this help"),
                ("/exit", "Exit OpenPlex"),
            ]

            for cmd, desc in commands:
                help_table.add_row(cmd, desc)

            self.console.print()
            self.console.print(Panel(
                help_table,
                title="[bold]OpenPlex Commands[/bold]",
                border_style=BRAND_COLOR,
            ))
            self.console.print("  [dim]Or just type any question to search and get cited answers.[/dim]\n")
        else:
            print("\n  OpenPlex Commands:")
            print("  /model list         - Show available models")
            print("  /model set <name>   - Switch model")
            print("  /deep <question>    - Deep research mode")
            print("  /sources            - Show last sources")
            print("  /clear              - Clear history")
            print("  /config             - Show configuration")
            print("  /config key <key>   - Set API key")
            print("  /status             - Current status")
            print("  /help               - This help")
            print("  /exit               - Exit")
            print("\n  Or just type any question.\n")

    def config_display(self, config):
        """Display current configuration."""
        if HAS_RICH:
            table = Table(box=box.ROUNDED, border_style=BRAND_COLOR)
            table.add_column("Setting", style="cyan")
            table.add_column("Value")

            # Mask API key
            api_key = config.get("api_key", "")
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "(not set)"

            table.add_row("API Key", masked_key)
            table.add_row("Model", config.get("model", ""))
            table.add_row("Base URL", config.get("base_url", ""))
            table.add_row("Temperature", str(config.get("temperature", 0.6)))
            table.add_row("Max Tokens", str(config.get("max_tokens", 4096)))
            table.add_row("Max Sources", str(config.get("max_sources", 8)))
            table.add_row("Search Depth", config.get("search_depth", "standard"))

            self.console.print()
            self.console.print(Panel(table, title="[bold]Configuration[/bold]", border_style=BRAND_COLOR))
            self.console.print()
        else:
            api_key = config.get("api_key", "")
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "(not set)"
            print(f"\n  Configuration:")
            print(f"  API Key:      {masked_key}")
            print(f"  Model:        {config.get('model', '')}")
            print(f"  Base URL:     {config.get('base_url', '')}")
            print(f"  Temperature:  {config.get('temperature', 0.6)}")
            print(f"  Max Tokens:   {config.get('max_tokens', 4096)}")
            print(f"  Max Sources:  {config.get('max_sources', 8)}")
            print()
