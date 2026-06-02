"""
OpenPlex Terminal UI.
Uses 'rich' for beautiful terminal output.
Falls back to plain text if rich is not installed.
"""

import sys
import time
import os

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box
    from rich.status import Status
    from rich.live import Live
    from rich.align import Align
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Balanced Professional Palette (Slate Blue & Cyan)
C_PRIMARY = "#8ab4f8"  # Soft Slate Blue
C_ACCENT = "#5fd7ff"   # Cyan
C_DIM = "#8a8a8a"      # Soft Gray
C_SUCCESS = "#afd787"  # Soft Mint
C_ERROR = "#ff8787"    # Soft Red
C_WARN = "#ffd787"     # Soft Yellow

# Standard width ASCII logo to prevent truncation on smaller terminals
ASCII_LOGO = """
   ____                 ____  __          
  / __ \____  ___  ____/ __ \/ /__  _  __ 
 / / / / __ \/ _ \/ __ \/ /_/ / / _ \| |/_/ 
/ /_/ / /_/ /  __/ / / / ____/ /  __/>  <   
\____/ .___/\___/_/ /_/_/   /_/\___/_/|_|   
    /_/                                     
""".strip("\n")

class UI:
    def __init__(self):
        self.console = Console() if HAS_RICH else None
        self._status = None

    def banner(self):
        if HAS_RICH:
            self.console.clear()
            self._animated_logo()
        else:
            print("\n  OPENPLEX")
            print("  ────────────────────────────────────────────────")

    def _animated_logo(self):
        lines = ASCII_LOGO.splitlines()
        max_width = max(len(line) for line in lines)
        
        with Live(console=self.console, refresh_per_second=30, transient=False) as live:
            for i in range(1, max_width + 1, 2):
                frame = Text()
                for line in lines:
                    visible_part = line[:i]
                    frame.append(visible_part.ljust(max_width) + "\n", style=f"bold {C_PRIMARY}")
                live.update(Align.center(frame))
                time.sleep(0.01)

        self.console.print()
        subtitle = Text("Terminal Native AI Search", style=f"italic {C_DIM}")
        self.console.print(Align.center(subtitle))
        self.console.print()

    def display_hub(self, provider, model, config):
        """Minimal session info. No telemetry."""
        if not HAS_RICH:
            print(f"  Provider: {provider}  |  Model: {model.split('/')[-1]}")
            return

        model_short = model.split('/')[-1]
        
        info_text = Text()
        info_text.append("PROVIDER  ", style=f"bold {C_DIM}")
        info_text.append(f"{provider}    ", style=f"bold {C_ACCENT}")
        info_text.append("MODEL  ", style=f"bold {C_DIM}")
        info_text.append(f"{model_short}", style=f"bold {C_PRIMARY}")

        self.console.print(Align.center(info_text))
        self.console.print()
        self.console.print(Align.center(Text("Type a question or /help", style=f"dim")))

    def prompt(self, model_name=""):
        try:
            if HAS_RICH:
                self.console.print(f"\n  [bold {C_ACCENT}]❯[/bold {C_ACCENT}] ", end="")
            else:
                print("\n  ❯ ", end="")
            return input("")
        except (EOFError, KeyboardInterrupt):
            return None

    def status(self, message):
        if HAS_RICH:
            if not self._status:
                self._status = self.console.status(f"[{C_DIM}]{message}[/{C_DIM}]", spinner="dots")
                self._status.start()
            else:
                self._status.update(f"[{C_DIM}]{message}[/{C_DIM}]")
        else:
            print(f"  ⟳ {message}" + " " * 20, end="\r")

    def clear_status(self):
        if HAS_RICH:
            if self._status:
                self._status.stop()
                self._status = None
        else:
            print(" " * 80, end="\r")

    def answer(self, text, sources=None, mode="search"):
        self.clear_status()
        if HAS_RICH:
            self.console.print()
            if text:
                color = C_PRIMARY
                icon = "✦"
                title = "Answer"
                
                if mode == "chat":
                    color = C_DIM
                    icon = "💬"
                    title = "Chat"
                elif mode == "deep":
                    color = "#b48ead" # Muted Purple
                    icon = "🧠"
                    title = "Deep Research"
                elif mode == "error":
                    color = C_ERROR
                    icon = "✗"
                    title = "Error"

                header = Text(f"{icon} {title}", style=f"bold {color}")
                self.console.print(f"  ", end="")
                self.console.print(header)
                self.console.print(f"  [{color}]────────────────────────────────────────[/{color}]")
                
                md = Markdown(text)
                self.console.print(Panel(
                    md,
                    box=box.MINIMAL,
                    border_style="black", # Padding only
                    padding=(0, 2)
                ))
            
            if sources:
                self.show_sources(sources)
            self.console.print()
        else:
            header = f"[{mode.upper()}]" if mode != "search" else "ANSWER"
            print(f"\n  {header}\n  {text}")
            if sources:
                self.show_sources(sources)

    def show_sources(self, sources):
        if not sources:
            return
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_DIM}]SOURCES[/bold {C_DIM}]")
            
            # Sort by trust internally to show best first
            sorted_sources = sorted(sources, key=lambda x: x.get("trust_score", 0), reverse=True)

            for i, s in enumerate(sorted_sources, 1):
                title = s.get("title", "Unknown")[:80]
                url = s.get("url", "")
                self.console.print(f"  [bold {C_ACCENT}]{i}.[/bold {C_ACCENT}] [bold white]{title}[/bold white]")
                self.console.print(f"     [dim]{url}[/dim]")
        else:
            print("\n  SOURCES:")
            for i, s in enumerate(sources, 1):
                print(f"  {i}. {s.get('title','')[:65]}")
                print(f"     {s.get('url','')[:72]}")

    def error(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_ERROR}]✗ {msg}[/bold {C_ERROR}]\n")
        else:
            print(f"\n  ✗ {msg}\n")

    def success(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_SUCCESS}]✓ {msg}[/bold {C_SUCCESS}]\n")
        else:
            print(f"\n  ✓ {msg}\n")

    def warning(self, msg):
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_WARN}]! {msg}[/bold {C_WARN}]\n")
        else:
            print(f"\n  ! {msg}\n")

    def info(self, msg):
        if HAS_RICH:
            self.console.print(f"  [{C_DIM}]{msg}[/{C_DIM}]")
        else:
            print(f"  {msg}")

    def provider_list(self, providers, current_provider):
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_PRIMARY}]PROVIDERS[/bold {C_PRIMARY}]")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {C_DIM}")
            t.add_column("Key")
            t.add_column("Name")
            t.add_column("Tier")
            t.add_column("Status", justify="center")
            for key, info in providers.items():
                active = f"[bold {C_SUCCESS}]ACTIVE[/bold {C_SUCCESS}]" if key == current_provider else ""
                tier = "Free" if info.get("free_tier") else "Paid"
                t.add_row(key, info["name"], tier, active)
            self.console.print(Panel(t, box=box.MINIMAL, border_style="black", padding=(0, 1)))
        else:
            print("\n  Providers:")
            for key, info in providers.items():
                active = " ← active" if key == current_provider else ""
                print(f"  • {key}: {info['name']} — {info.get('notes','')}{active}")

    def model_list(self, models, current_model):
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_PRIMARY}]MODELS[/bold {C_PRIMARY}]")
            t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {C_DIM}")
            t.add_column("Name")
            t.add_column("Full ID", style=C_DIM)
            t.add_column("Status", justify="center")
            for key, info in models.items():
                active = f"[bold {C_SUCCESS}]ACTIVE[/bold {C_SUCCESS}]" if info["id"] == current_model else ""
                t.add_row(key, info["id"], active)
            self.console.print(Panel(t, box=box.MINIMAL, border_style="black", padding=(0, 1)))
        else:
            print("\n  Models:")
            for key, info in models.items():
                active = " ← active" if info["id"] == current_model else ""
                print(f"  • {key}: {info['description']}{active}")
                print(f"    {info['id']}")

    def help_text(self):
        cmds = [
            ("/provider list", "Browse all search providers"),
            ("/provider set <name>", "Switch active provider"),
            ("/provider key <key>", "Update API credentials"),
            ("/model list", "View models for current provider"),
            ("/model set <name>", "Switch active model"),
            ("/deep <question>", "In-depth research mode"),
            ("/sources", "Inspect sources from last answer"),
            ("/clear", "Reset conversation state"),
            ("/config", "View current configuration"),
            ("/status", "Display session analytics"),
            ("/help", "Show this guide"),
            ("/exit", "Terminate OpenPlex"),
        ]
        if HAS_RICH:
            self.console.print(f"\n  [bold {C_PRIMARY}]COMMANDS[/bold {C_PRIMARY}]")
            t = Table(box=box.SIMPLE_HEAD, show_header=False, padding=(0, 2))
            t.add_column("Command", style=C_ACCENT)
            t.add_column("Description", style=C_DIM)
            for cmd, desc in cmds:
                t.add_row(cmd, desc)
            self.console.print(Panel(t, box=box.MINIMAL, border_style="black", padding=(0, 1)))
        else:
            print("\n  OpenPlex Commands:")
            for cmd, desc in cmds:
                print(f"  {cmd:<30} {desc}")

    def config_display(self, config):
        prov = config.get("provider", "nvidia")
        api_key = config.get("api_key", "")
        masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else ("(not set)" if not api_key else api_key)

        if HAS_RICH:
            self.console.print(f"\n  [bold {C_PRIMARY}]CONFIGURATION[/bold {C_PRIMARY}]")
            t = Table(box=box.SIMPLE_HEAD, show_header=False, padding=(0, 2))
            t.add_column("Setting", style=f"bold {C_DIM}")
            t.add_column("Value")
            
            t.add_row("Provider", prov.upper())
            t.add_row("Model", config.get("model", "").split('/')[-1])
            t.add_row("API Key", masked)
            t.add_row("Temp", str(config.get("temperature", 0.6)))
            t.add_row("Max Tokens", str(config.get("max_tokens", 4096)))
            self.console.print(Panel(t, box=box.MINIMAL, border_style="black", padding=(0, 1)))
        else:
            print(f"\n  Provider:    {prov}")
            print(f"  Model:       {config.get('model','')}")
            print(f"  Temperature: {config.get('temperature',0.6)}")
