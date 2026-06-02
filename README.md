# OpenPlex

> An open-source Perplexity Pro alternative for your terminal.

OpenPlex gives you AI-powered answers grounded in real web results — with citations, source ranking, and a dual-pass RAG pipeline. No browser. No subscription. Runs on Termux and Linux with minimal dependencies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![Termux](https://img.shields.io/badge/runs%20on-Termux-brightgreen)]()

---

## What's New

- **Pass-through RAG (2-Step Verification):** Deep research mode now uses a dual-pass system. First, it drafts an answer, then a separate verification pass checks every claim against the sources to eliminate hallucinations.
- **Source Trust Engine:** Heuristics-based scoring that prioritizes high-authority domains (Official docs, .gov, .edu) and detects primary sources.
- **Animated Terminal UI:** A new, polished interface with an animated ASCII logo and professional color palettes.
- **Smart Orchestration:** Unified intent detection and query resolution for faster, more accurate searches.

---

## Core Pipeline

OpenPlex works like Perplexity Pro, but natively in your terminal:

1. **Orchestration:** Analyzes your question to decide if it needs a search or just a chat response.
2. **Multi-Source Search:** Searches the web (DuckDuckGo) and fetches content from multiple pages in parallel.
3. **Trust Ranking:** Scores and ranks sources based on domain authority and content quality.
4. **Drafting:** Generates an initial answer with inline citations.
5. **Verification (Deep Mode):** Cross-references the draft against sources to ensure absolute accuracy.

```
Question → Intent → Search → Trust Rank → Draft → Verify → Final Answer
```

---

## Install

**Termux (Android)**
```bash
pkg install python git
git clone https://github.com/Alex72-py/openplex.git
cd openplex
pip install rich
python openplex.py
```

**Linux**
```bash
git clone https://github.com/Alex72-py/openplex.git
cd openplex
pip3 install rich
python3 openplex.py
```

On first run, a setup wizard walks you through choosing a provider and entering your API key.

---

## Providers & Models

All providers have **free tiers** — no paid subscription required.

### NVIDIA NIM — [build.nvidia.com](https://build.nvidia.com)
Key format: `nvapi-...` · Free tier available

| Short Name | Model |
|---|---|
| `deepseek-r1` | DeepSeek R1 671B |
| `llama-3.3-70b` | Llama 3.3 70B |
| `nemotron-super` | Nemotron Ultra 253B |
| `qwen-2.5-72b` | Qwen 2.5 72B |
| `mistral-small` | Mistral Small 24B |

### Google AI Studio — [aistudio.google.com](https://aistudio.google.com)
Key format: `AIza...` · 15 req/min free

| Short Name | Model |
|---|---|
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.0-flash` | Gemini 2.0 Flash |
| `gemini-2.0-flash-lite` | Gemini 2.0 Flash Lite |
| `gemini-2.5-pro` | Gemini 2.5 Pro |

### OpenRouter — [openrouter.ai](https://openrouter.ai/keys)
Key format: `sk-or-...` · Free models available

| Short Name | Model |
|---|---|
| `llama-3.3-70b-free` | Llama 3.3 70B (free) |
| `deepseek-r1-free` | DeepSeek R1 (free) |
| `deepseek-v3-free` | DeepSeek V3 (free) |
| `gemma-3-27b-free` | Gemma 3 27B (free) |
| `qwen3-235b-free` | Qwen3 235B (free) |
| `mistral-7b-free` | Mistral 7B (free) |

---

## Commands

```
/provider list              browse all search providers
/provider set <name>        switch active provider
/provider key <key>         update API credentials

/model list                 view models for current provider
/model set <name>           switch active model

/deep <question>            in-depth research mode (2-step verification)
/sources                    inspect sources from last answer
/clear                      reset conversation state
/config                     view current configuration
/status                     display session analytics
/help                       show this guide
/exit                       terminate OpenPlex
```

---

## Environment Variables

```bash
export OPENPLEX_NVIDIA_KEY="nvapi-..."
export OPENPLEX_GOOGLE_KEY="AIza..."
export OPENPLEX_OPENROUTER_KEY="sk-or-..."
export OPENPLEX_PROVIDER="google"
export OPENPLEX_MODEL="models/gemini-2.5-flash"
```

---

## Why OpenPlex?

| Feature | Perplexity Pro | OpenPlex |
|---|---|---|
| **Cost** | $20/month | **Free** |
| **Open Source** | ❌ | **✅** |
| **Verification Pass** | ✅ | **✅ (Deep Mode)** |
| **Trust Engine** | ✅ | **✅** |
| **Terminal Native** | ❌ | **✅** |
| **BYO Model** | ❌ | **✅** |

---

## License

MIT
