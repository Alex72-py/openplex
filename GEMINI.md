# OpenPlex: AI Answer Engine for Terminal

OpenPlex is an open-source Perplexity Pro alternative designed for Termux and Linux. It provides AI-powered answers grounded in real-time web search results using a full RAG (Retrieval-Augmented Generation) pipeline, complete with citations and source ranking.

## Project Overview

- **Core Functionality:** Grounded AI answers with web search, source ranking, and inline citations.
- **Tech Stack:** Python 3.8+, `rich` (for terminal UI), DuckDuckGo (for search).
- **Architecture:**
  - `openplex.py`: Entry point.
  - `src/main.py`: Main application loop and command handling.
  - `src/engine.py`: Orchestrates the RAG pipeline (decomposition, search, ranking, synthesis).
  - `src/search_engine.py`: Handles DuckDuckGo search and page content extraction.
  - `src/api_client.py`: Manages communication with AI providers (NVIDIA, Google, OpenRouter).
  - `src/config.py`: Configuration management and provider/model definitions.
  - `src/ui.py`: Terminal interface using `rich`.

## Building and Running

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python openplex.py
```

### Environment Variables
Optionally set API keys via environment variables:
- `OPENPLEX_NVIDIA_KEY`
- `OPENPLEX_GOOGLE_KEY`
- `OPENPLEX_OPENROUTER_KEY`
- `OPENPLEX_PROVIDER`
- `OPENPLEX_MODEL`

## Development Conventions

### Coding Style
- **Modular Design:** Keep search logic, engine logic, and UI separate.
- **Documentation:** Use docstrings for modules and functions.
- **Error Handling:** Use the `APIError` class for API-related issues and ensure the UI handles errors gracefully.

### RAG Pipeline Flow
When modifying the engine or search logic, maintain the established flow:
1. **Query Decomposition:** Breaking complex questions into sub-queries.
2. **Multi-source Search:** Parallel fetching of search results.
3. **Source Ranking:** Scoring sources based on keyword overlap and content quality.
4. **Context Injection:** Feeding ranked sources into the LLM prompt with strict citation rules.
5. **Synthesis:** Generating the final answer with inline citations like `[1]`, `[2]`.

### Testing
Currently, there is no automated test suite. When adding features:
- Manually verify the search pipeline with various query types.
- Ensure provider switching and model selection work correctly.
- Test the terminal UI across different screen sizes.

## Configuration
Settings are stored in `~/.openplex/config.json`. Key-provider mapping is handled in `src/config.py`.
