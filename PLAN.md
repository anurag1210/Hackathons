## What we're building
Terminal-based AI triage agent for HackerRank, Claude, Visa support tickets

## Architecture
CSV input → orchestrator → classifier → corpus router → 
retriever (ChromaDB) → safety gate → LLM → CSV output

## Current status
- [x] agent_orchestrator.py — complete
- [ ] scraper.py
- [ ] retriever.py
- [ ] classifier.py
- [ ] safety.py
- [ ] pipeline.py
- [ ] prompts.py

## Remaining work
Build modules in this order:
1. scraper.py
2. retriever.py
3. classifier.py + safety.py
4. pipeline.py + prompts.py
5. End to end test