# OpenPlex

> An open-source Perplexity Pro alternative for your terminal.

OpenPlex gives you AI-powered answers grounded in real web results — with citations, source ranking, and a full RAG pipeline. No browser. No subscription. Runs on Termux and Linux with minimal dependencies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![Termux](https://img.shields.io/badge/runs%20on-Termux-brightgreen)]()

---

## What It Does

Most AI chatbots hallucinate because they answer from memory. OpenPlex works like Perplexity Pro:

1. Takes your question
2. Searches the web
3. Fetches and ranks actual page content
4. Injects sources into the prompt
5. Generates a grounded answer with inline citations

```
Question → Search → Rank Sources → Inject into Prompt → Generate → Cite → Clean
```

No hallucinations. Every claim is backed by a real URL.

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
| `gemini-2.5-pro` | Gemini 2.5 Pro |

### OpenRouter — [openrouter.ai](https://openrouter.ai/keys)
Key format: `sk-or-...` · Free models available

| Short Name | Model |
|---|---|
| `deepseek-r1-free` | DeepSeek R1 (free) |
| `deepseek-v3-free` | DeepSeek V3 (free) |
| `llama-3.3-70b-free` | Llama 3.3 70B (free) |
| `qwen3-235b-free` | Qwen3 235B MoE (free) |
| `gemma-3-27b-free` | Gemma 3 27B (free) |
| `mistral-7b-free` | Mistral 7B (free) |

---

## Commands

```
/provider list              list providers
/provider set <name>        switch provider (nvidia / google / openrouter)
/provider key <key>         set API key for current provider
/provider status            show stored keys

/model list                 list models for current provider
/model set <name>           switch model

/deep <question>            deep research mode (more sources)
/sources                    show sources from last answer
/clear                      clear conversation history
/config                     show config
/config temp <0-2>          set temperature
/config tokens <n>          set max tokens
/status                     session info
/help                       show all commands
/exit                       quit
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

## Dependencies

Only `rich` for the terminal UI (optional — falls back to plain text). Everything else is Python stdlib. **No pip installs needed for core functionality.**

Config is stored at `~/.openplex/config.json`. Keys are saved per-provider so switching providers doesn't require re-entering them.

---

## Why OpenPlex?

| | Perplexity Pro | OpenPlex |
|---|---|---|
| Cost | $20/month | Free |
| Open source | ❌ | ✅ |
| Runs on Termux | ❌ | ✅ |
| Bring your own model | ❌ | ✅ |
| Citation-grounded answers | ✅ | ✅ |

---

## License

MIT
