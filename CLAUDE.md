Project: Multi-Domain Support Triage Agent
Stack: Python, ChromaDB, LangChain, OpenAI, Click
Entry point: agent_orchestrator.py
Do not modify: data/ folder
Conventions: snake_case, type hints, docstrings on all functions
Secrets: loaded from .env via python-dotenv


## Architecture
- agent_orchestrator.py  → CLI entry point, drives the pipeline
- scraper.py             → scrapes 3 support sites, saves chunks to disk
- retriever.py           → ChromaDB setup and query logic
- classifier.py          → infers company when None, classifies request_type
- safety.py              → pre-screen and escalation gate logic
- pipeline.py            → per-ticket orchestration
- prompts.py             → system prompt and user prompt templates
- corpus/                → scraped docs (auto-generated, don't edit)
- data/                  → input CSVs (don't modify)