# OpenPlex

A Perplexity-like AI search engine for your terminal. Searches the web, cites sources, and gives you grounded answers — runs on Termux with minimal dependencies.

---

## Install

```bash
# Termux
pkg install python git
git clone https://github.com/Alex72-py/OpenPlex.git
cd OpenPlex
pip install rich
python openplex.py
```

```bash
# Linux
git clone https://github.com/Alex72-py/OpenPlex.git
cd OpenPlex
pip3 install rich
python3 openplex.py
```

On first run, a setup wizard will ask you to choose a provider and enter your API key.

---

## How It Works

```
Question → Search → Rank Sources → Inject into Prompt → Generate → Cite → Clean
```

OpenPlex implements a simplified version of Perplexity's RAG pipeline. It searches the web, fetches actual page content, ranks sources by relevance, and injects them into the prompt *before* generation — so the model is forced to cite and stay grounded, not hallucinate.

---

## Providers & Models

OpenPlex supports **NVIDIA NIM**, **Google AI Studio**, and **OpenRouter** — all with free tiers.

### NVIDIA NIM — [build.nvidia.com](https://build.nvidia.com)
Key format: `nvapi-...` · 1000 free credits on signup

| Short Name | Model |
|---|---|
| `deepseek-r1` | DeepSeek R1 671B |
| `llama-3.3-70b` | Llama 3.3 70B |
| `nemotron-super` | Nemotron Ultra 253B |
| `qwen-2.5-72b` | Qwen 2.5 72B |
| `mistral-small` | Mistral Small 24B |

### Google AI Studio — [aistudio.google.com](https://aistudio.google.com/app/apikey)
Key format: `AIza...` · 15 req/min free

| Short Name | Model |
|---|---|
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.0-flash` | Gemini 2.0 Flash |
| `gemini-2.0-flash-lite` | Gemini 2.0 Flash Lite |
| `gemini-2.5-pro` | Gemini 2.5 Pro |

### OpenRouter — [openrouter.ai/keys](https://openrouter.ai/keys)
Key format: `sk-or-...` · Free models marked `:free`

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

Only `rich` for terminal UI — optional, falls back to plain text. Everything else (`urllib`, `json`, `ssl`, `concurrent.futures`) is Python stdlib. No pip installs required for core functionality.

---

## Config

Stored at `~/.openplex/config.json`. Keys are stored per-provider so switching back doesn't require re-entering them.

---

## License

MIT
