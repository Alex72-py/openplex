# ◆ OpenPlex

**A Perplexity Pro alternative that runs on Termux.**

OpenPlex is a terminal-based AI search engine that gives you cited, source-verified answers using NVIDIA NIM API free tier models. It searches the web, cross-references multiple sources, and generates answers with inline citations — just like Perplexity Pro, but free and running on your phone.

---

## How It Works

OpenPlex implements a simplified version of Perplexity's RAG (Retrieval-Augmented Generation) pipeline:

```
Question → Decompose → Search → Rank → Cite → Generate → Verify → Answer
```

1. **Query Decomposition** — Complex questions are broken into focused sub-queries
2. **Multi-Source Search** — Searches DuckDuckGo and fetches content from multiple pages
3. **Source Ranking** — Ranks results by relevance, filters out low-quality sources
4. **Citation Embedding** — Sources are injected into the prompt *before* generation (not after)
5. **Constrained Generation** — LLM is forced to cite sources and stick to retrieved evidence
6. **Response Verification** — Invalid citations are removed, formatting is cleaned

---

## Features

| Feature | Description |
|---------|-------------|
| **Cited Answers** | Every claim has an inline citation [1], [2], etc. |
| **Multi-Source Verification** | Cross-references multiple sources for reliability |
| **Deep Research Mode** | `/deep` breaks questions into sub-queries for thorough research |
| **Conversation Memory** | Follow-up questions understand context from previous answers |
| **Model Switching** | Switch between DeepSeek R1, Llama 3.3, Nemotron, Qwen, Mistral |
| **Response Cleaning** | Strips thinking tags, fixes double responses, removes artifacts |
| **Error Recovery** | Auto-retries on rate limits, handles network issues gracefully |
| **Minimal Dependencies** | Only `rich` for UI — everything else is Python stdlib |
| **Termux Native** | Built specifically for Termux on Android |

---

## Installation

### Termux (Android)

```bash
pkg install python git
git clone https://github.com/Alex72-py/OpenPlex.git
cd OpenPlex
pip install rich
chmod +x install.sh
bash install.sh
```

### Linux

```bash
git clone https://github.com/Alex72-py/OpenPlex.git
cd OpenPlex
pip3 install rich
bash install.sh
```

### Quick Start (No Install)

```bash
git clone https://github.com/Alex72-py/OpenPlex.git
cd OpenPlex
pip install rich
python openplex.py
```

---

## Setup

On first run, a wizard lets you pick a provider and enter your API key.

### Supported Providers

| Provider | Free Tier | Get Key | Key Format |
|---|---|---|---|
| **NVIDIA NIM** | 1000 credits on signup, 40 req/min | [build.nvidia.com](https://build.nvidia.com) | `nvapi-...` |
| **Google AI Studio** | 15 req/min, 1M tokens/day | [aistudio.google.com](https://aistudio.google.com/app/apikey) | `AIza...` |
| **OpenRouter** | Many `:free` models | [openrouter.ai/keys](https://openrouter.ai/keys) | `sk-or-...` |

Switch providers anytime:
```
❯ /provider set google
  ✓ Switched to Google AI Studio | Model: gemini-2.5-flash

❯ /provider set openrouter
  ✓ Switched to OpenRouter | Model: deepseek-r1-free

❯ /provider key sk-or-...
  ✓ API key updated for OpenRouter
```

---

## Usage

Just type any question:

```
❯ What is quantum computing and how does it differ from classical computing?

  ┌─ Answer ──────────────────────────────────────────────────────────┐
  │ Quantum computing uses **quantum bits (qubits)** that can exist   │
  │ in superposition states, unlike classical bits which are either    │
  │ 0 or 1 [1]. This allows quantum computers to process multiple     │
  │ possibilities simultaneously [2]...                                │
  └───────────────────────────────────────────────────────────────────┘

  Sources:
  [1] Introduction to Quantum Computing - IBM
      https://www.ibm.com/quantum/what-is-quantum-computing
  [2] Quantum vs Classical Computing - MIT
      https://news.mit.edu/quantum-computing-explained
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/provider list` | Show all providers |
| `/provider set nvidia` | Switch to NVIDIA NIM |
| `/provider set google` | Switch to Google AI Studio |
| `/provider set openrouter` | Switch to OpenRouter |
| `/provider key <key>` | Set API key for current provider |
| `/provider status` | Show key status for all providers |
| `/model list` | Show models for current provider |
| `/model set <name>` | Switch to a different model |
| `/deep <question>` | Deep research mode (more sources, query decomposition) |
| `/sources` | Show sources from the last answer |
| `/clear` | Clear conversation history |
| `/config` | Show current configuration |
| `/config temp <0.0-2.0>` | Set temperature |
| `/config tokens <number>` | Set max response tokens |
| `/status` | Show current model and session info |
| `/help` | Show all commands |
| `/exit` | Exit OpenPlex |

---

## Available Models

### NVIDIA NIM
| Short Name | Model | Best For |
|---|---|---|
| `deepseek-r1` | DeepSeek R1 671B | Reasoning, math, code |
| `llama-3.3-70b` | Llama 3.3 70B | General purpose, fast |
| `nemotron-super` | Nemotron Ultra 253B | Complex reasoning |
| `qwen-2.5-72b` | Qwen 2.5 72B | Multilingual, coding |
| `mistral-small` | Mistral Small 24B | Fast, efficient |

### Google AI Studio
| Short Name | Model | Best For |
|---|---|---|
| `gemini-2.5-flash` | Gemini 2.5 Flash | Best overall, free |
| `gemini-2.0-flash` | Gemini 2.0 Flash | Stable, fast |
| `gemini-2.0-flash-lite` | Gemini 2.0 Flash Lite | Lightest, fastest |
| `gemini-2.5-pro` | Gemini 2.5 Pro | Most capable |

### OpenRouter (all free)
| Short Name | Model | Best For |
|---|---|---|
| `llama-3.3-70b-free` | Llama 3.3 70B | General purpose |
| `deepseek-r1-free` | DeepSeek R1 | Reasoning |
| `deepseek-v3-free` | DeepSeek V3 | Fast, capable |
| `gemma-3-27b-free` | Gemma 3 27B | Google open model |
| `qwen3-235b-free` | Qwen3 235B MoE | Massive model |
| `mistral-7b-free` | Mistral 7B | Lightweight |

Switch models anytime:
```
❯ /model set gemini-2.5-flash
  ✓ Switched to Gemini 2.5 Flash
```

---

## Architecture

```
openplex/
├── openplex.py          — Entry point
├── install.sh           — Termux/Linux installer
├── requirements.txt     — Dependencies (just 'rich')
└── src/
    ├── main.py          — Main loop, command dispatch, setup wizard
    ├── engine.py        — Answer engine (RAG pipeline orchestration)
    ├── api_client.py    — NVIDIA NIM API client (urllib, no deps)
    ├── search_engine.py — Web search via DuckDuckGo HTML (no API key)
    ├── config.py        — Configuration management (~/.openplex/)
    └── ui.py            — Rich terminal UI (graceful fallback)
```

---

## How OpenPlex Differs from Basic Chatbots

| Aspect | Basic Chatbot | OpenPlex |
|--------|--------------|----------|
| Knowledge | Training data only | Real-time web search |
| Citations | None | Inline [1], [2] citations |
| Verification | None | Multi-source cross-reference |
| Reliability | Can hallucinate | Constrained to sources |
| Follow-ups | Limited context | Full conversation memory |
| Transparency | Black box | Shows sources and reasoning |

---

## Dependencies

| Package | Purpose | Required |
|---------|---------|:--------:|
| `rich` | Terminal UI, markdown rendering | Optional* |

*OpenPlex works without `rich` in plain text mode. All HTTP, JSON, threading, and config handling uses Python stdlib (`urllib`, `json`, `concurrent.futures`, `os`).

**Zero external dependencies for core functionality.** The `rich` library is only for prettier terminal output.

---

## Configuration

Stored at `~/.openplex/config.json`:

```json
{
  "api_key": "nvapi-...",
  "model": "deepseek-ai/deepseek-r1",
  "base_url": "https://integrate.api.nvidia.com/v1",
  "temperature": 0.6,
  "max_tokens": 4096,
  "max_sources": 8,
  "search_depth": "standard",
  "verify_sources": true,
  "show_sources": true
}
```

Environment variable overrides:
```bash
export OPENPLEX_NVIDIA_KEY="nvapi-..."
export OPENPLEX_GOOGLE_KEY="AIza..."
export OPENPLEX_OPENROUTER_KEY="sk-or-..."
export OPENPLEX_PROVIDER="google"
export OPENPLEX_MODEL="models/gemini-2.5-flash"
```

---

## Limitations

- Requires internet for both search and AI generation
- DuckDuckGo may rate-limit heavy usage (rare in practice)
- NVIDIA NIM free tier: 40 requests/minute, 1000 credits on signup
- Source content extraction is best-effort (some sites block scraping)
- Not a replacement for academic research — always verify critical claims

---

## License

MIT

---

<div align="center">

**OpenPlex** — Search smarter from your terminal.

[![GitHub](https://img.shields.io/badge/GitHub-Alex72--py-181717?logo=github)](https://github.com/Alex72-py/OpenPlex)

</div>
