# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mirobaldo is a Portuguese-language chatbot for Sporting Clube Farense (football club), featuring a local LoRA fine-tuned LLM with a biography RAG system. The model is Qwen2.5-3B-Instruct-4bit fine-tuned via MLX LoRA.

## Commands

```bash
# Install dependencies
pip install -r requirements_combined.txt

# Start server (port 5001, auto-increments if busy)
source venv/bin/activate && python backend/app.py

# Or use the convenience script
./start.sh

# Run tests
pytest backend/test_rag.py -v

# Generate training dataset (v3 pipeline)
python backend/generate_qa_pairs.py

# Run LoRA fine-tuning
python backend/train_lora.py

# Scrape live data
python backend/scraper.py
```

## Architecture

**Backend** (`backend/`):
- `app.py` — Flask API server. Serves frontend, exposes `/api/farense-chat` and other routes. **Critical**: all routes must be defined BEFORE `if __name__ == '__main__': main()`, because `app.run()` inside `main()` blocks execution.
- `chatbot.py` — Main chat logic. Routes queries to biography RAG, results handler, or the LLM agent. Biography queries bypass the LLM entirely via `format_biography_as_answer()`.
- `mlx_interface.py` — Loads the LoRA-adapted Qwen2.5-3B-Instruct-4bit model via MLX and handles inference. Adapter path: `lora_adapters/`.
- `utils.py` — `find_biography_for_query()` searches biography files by player name; `format_biography_as_answer()` extracts structured facts without calling the LLM.
- `adaptive_rag_system.py` / `hybrid_rag_system.py` — RAG retrieval over game results and club history.
- `agents/biography_agent.py`, `agents/results_agent.py`, `agents/classification_agent.py` — Specialized agents called by chatbot.py.
- `scraper.py` / `live_data_manager.py` — Fetches current season results and squad from the web.

**Data** (`data/`):
- `chatbot_dados/biografias/` — 208 biography files (`.md` structured or `.txt` prose) for individual players.
- `Planteis/` — 54 seasons of squad data in JSON.
- `dados_jogos.db` — SQLite database of historical match results.
- `chatbot_dados/historia_farense.txt` — Club narrative history.

**Frontend** (`frontend/`):
- `mirobaldo_src/` — Classic HTML/CSS/JS frontend (served by Flask).
- `public/` — Modern React-style frontend.

**LoRA pipeline**:
1. `generate_qa_pairs.py` → `training_data_lora.jsonl` (1664 Q&A pairs, dataset v3)
2. `train_lora.py` → `lora_adapters/` (0.216% trainable params, ~3h on Apple Silicon)

## RAG Design

**Biography queries** (e.g. "quem foi João Gralho?"):
1. `find_biography_for_query()` matches player name against filenames in `data/chatbot_dados/biografias/`
2. `format_biography_as_answer()` extracts facts directly from the file — bypasses LLM entirely
3. For structured `.md` files: extracts `**DD/MM/YYYY, Place** | **Position**` header + clubs + titles
4. For prose `.txt` files: returns first 2 clean paragraphs

**LoRA model limitation**: The 3B model teaches response format/style but cannot reliably memorize 208 players' biographical facts. RAG must supply facts at inference time.

## Biography File Format

Structured `.md` files use this header pattern (required for `_is_structured_markdown`):
```
**DD/MM/YYYY, Place** | **Position**
```

Placeholder/stub files are skipped if they contain: `"nao disponiv"`, `"informacoes: n/a"`, `"sem informacao"`, `"sem dados"`, or are under 80 characters.

## Key Paths

- Flask template folder: `frontend/mirobaldo_src/`
- Flask static folder: `frontend/mirobaldo_src/static/`
- LoRA adapters: `lora_adapters/`
- Biography files: `data/chatbot_dados/biografias/`
- Training data: `training_data_lora.jsonl`
- App log: `/tmp/mirobaldo_app.log`
