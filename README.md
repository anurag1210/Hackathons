#HackerRank Hackathon

# Support Triage Agent

A terminal-based AI support triage agent that handles support tickets across three ecosystems — **HackerRank**, **Claude**, and **Visa** — using retrieval-augmented generation (RAG) grounded strictly in each platform's official support corpus.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Pipeline Walkthrough](#pipeline-walkthrough)
- [Escalation Logic](#escalation-logic)
- [Installation](#installation)
- [Usage](#usage)
- [Input Format](#input-format)
- [Output Format](#output-format)
- [Design Decisions](#design-decisions)

---

## Overview

Given a CSV of support tickets, the agent:

1. Reads each ticket (issue, subject, company)
2. Infers the domain if `company` is missing or `None`
3. Pre-screens for malicious or adversarial content
4. Routes to the correct support corpus
5. Retrieves the most relevant documentation
6. Applies a safety gate to decide whether to reply or escalate
7. Generates a grounded, user-facing response via an LLM
8. Outputs structured results to a CSV

The agent never invents policies or procedures. Every response is grounded in the retrieved support corpus only.

---

## Architecture

```
support_tickets.csv
        │
        ▼
┌───────────────────┐
│   Orchestrator    │  Reads rows, drives the full pipeline per ticket
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Pre-screen      │  Detects malicious, adversarial, empty, or injection attempts
└────────┬──────────┘
         │ invalid / escalate (early exit) ──────────────────────────────────┐
         ▼                                                                    │
┌───────────────────┐                                                         │
│ Company Classifier│  Infers HackerRank / Claude / Visa from content         │
│                   │  when company field is None, nan, or ambiguous          │
└────────┬──────────┘                                                         │
         │                                                                    │
    ┌────┴─────┬──────────────┐                                               │
    ▼          ▼              ▼                                                │
┌────────┐ ┌────────┐ ┌────────────┐                                          │
│HackerRk│ │ Claude │ │    Visa    │  ChromaDB collections (one per domain)   │
│ corpus │ │ corpus │ │   corpus   │                                          │
└────┬───┘ └───┬────┘ └─────┬──────┘                                          │
     └─────────┴────────────┘                                                 │
                │                                                             │
                ▼                                                             │
┌───────────────────┐                                                         │
│    Retriever      │  Queries ChromaDB for top-k relevant docs               │
└────────┬──────────┘                                                         │
         │                                                                    │
         ▼                                                                    │
┌───────────────────┐                                                         │
│   Safety Gate     │  Checks for billing, fraud, access, identity theft,     │
│                   │  vague tickets, or low retrieval confidence             │
└────────┬──────────┘                                                         │
         │ escalate ───────────────────────────────────────────────────────┐  │
         ▼                                                                 │  │
┌───────────────────────────────────────┐                                  │  │
│              LLM                      │  GPT-4o-mini                     │  │
│  System prompt + retrieved docs       │  Grounded response only          │  │
│  + few-shot examples                  │                                  │  │
└────────┬──────────────────────────────┘                                  │  │
         │                                                                 │  │
         └──────────────────────────┬──────────────────────────────────────┘  │
                                    │◄────────────────────────────────────────┘
                                    ▼
              status · product_area · response · justification · request_type
```

---

## Project Structure

```
support-triage-agent/
├── agent.py              # CLI entry point and orchestrator
├── scraper.py            # Scrapes and chunks the three support corpora
├── retriever.py          # ChromaDB setup, embedding, and query logic
├── classifier.py         # Company inference and request_type classification
├── safety.py             # Escalation decision logic (rule-based pre-check)
├── pipeline.py           # Per-ticket orchestration: classify → retrieve → gate → LLM
├── prompts.py            # System prompt, user prompt templates, few-shot examples
├── corpus/               # Scraped and chunked documents (auto-generated)
│   ├── hackerrank/
│   ├── claude/
│   └── visa/
├── data/
│   ├── sample_support_tickets.csv   # Labelled examples (used for few-shot)
│   └── support_tickets.csv          # Input tickets to triage
├── requirements.txt
└── README.md
```

---

## Pipeline Walkthrough

### 1. Orchestrator (`agent.py`)

The entry point. Reads the input CSV row by row, passes each ticket through the pipeline, and writes the output CSV. Optionally rebuilds the corpus from scratch via `--build-corpus`.

### 2. Pre-screen (`safety.py`)

The first line of defence. Before any retrieval or LLM call, the ticket is scanned for:

- Malicious instructions (`"delete all files"`, `"ignore previous instructions"`)
- Prompt injection attempts (unusual formatting, commands in foreign languages)
- Empty or meaningless content (`"thank you"`, single-word tickets)

These are immediately assigned `request_type: invalid` and `status: escalated` or `replied` with an out-of-scope message, without touching the LLM.

### 3. Company Classifier (`classifier.py`)

When the `company` field is `None`, `nan`, or missing, the classifier infers the domain from ticket content using keyword signals:

| Signal keywords | Inferred domain |
|---|---|
| test, assessment, candidate, interview, score, HackerRank | HackerRank |
| Claude, API, conversation, model, prompt, Bedrock, training data | Claude |
| Visa card, charge, dispute, merchant, card blocked, ATM, transaction | Visa |
| No match | Out-of-scope → `invalid` |

### 4. Corpus Router & Retriever (`retriever.py`)

Routes the ticket to the correct ChromaDB collection (one per domain). Performs a semantic similarity search using OpenAI embeddings and returns the top-k most relevant document chunks. A low maximum similarity score (below threshold) is itself an escalation signal — if the corpus has nothing relevant, the agent will not hallucinate an answer.

### 5. Safety Gate (`safety.py`)

A rule-based check applied *after* retrieval. Escalates when:

- **Billing / payments**: order IDs, refund requests, payment failures
- **Account access**: user explicitly not the owner or admin
- **Score / outcome disputes**: requests to change results or influence third parties
- **Fraud / identity theft**: stolen cards, identity theft, fraudulent transactions
- **Security vulnerabilities**: any report of a security bug or exploit
- **Adversarial content**: injection attempts, requests for harmful actions
- **Low retrieval confidence**: no relevant docs found in the corpus

### 6. LLM Response Generation (`pipeline.py` + `prompts.py`)

Combines three inputs into the LLM call:

- **System prompt**: defines the agent's role, routing rules, escalation rules, output format
- **Retrieved docs**: the top-k corpus chunks relevant to this ticket
- **Few-shot examples**: 2-3 relevant rows from `sample_support_tickets.csv` to calibrate tone and output structure

The LLM is instructed to respond only with a JSON object. Output is validated and re-prompted if malformed.

---

## Escalation Logic

The agent escalates (sets `status: escalated`) in these scenarios:

| Trigger | Reason |
|---|---|
| Order ID or transaction ID in ticket | Requires account lookup, not answerable from docs |
| User admits they are not the account owner/admin | Cannot action without authorisation |
| Request to change score or influence recruiter | Involves third party, outside agent's authority |
| Identity theft or card stolen | High personal risk, needs human urgency |
| Security vulnerability report | Must reach security team, not auto-responded |
| Malicious or adversarial content | Safety violation |
| No relevant docs retrieved | Agent will not hallucinate — escalates instead |
| Vague ticket with no actionable detail | Cannot resolve without more information |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/anurag1210/support-triage-agent
cd support-triage-agent

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY=your_key_here
```

**requirements.txt**
```
openai
langchain
chromadb
pandas
requests
beautifulsoup4
playwright
tqdm
python-dotenv
```

---

## Usage

```bash
# First run — scrape corpora and build vectorstore
python agent.py --input data/support_tickets.csv --output results.csv --build-corpus

# Subsequent runs — use cached corpus (much faster)
python agent.py --input data/support_tickets.csv --output results.csv

# Verbose mode — prints retrieved docs and reasoning per ticket
python agent.py --input data/support_tickets.csv --output results.csv --verbose
```

**Example terminal output:**

```
[*] Building corpus from support sites...
    → Scraped HackerRank: 84 chunks
    → Scraped Claude: 61 chunks
    → Scraped Visa: 73 chunks
[*] Initialising vectorstore...

[1/29] Processing: "I lost access to my Claude team workspace..."
       Company: Claude | Route: Claude corpus
       Retrieved: 3 docs (max score: 0.87)
       Safety gate: ESCALATE — user is not account owner/admin
       Status: escalated

[2/29] Processing: "I completed a HackerRank test, but the recruiter rejected me..."
       Company: HackerRank | Route: HackerRank corpus
       Retrieved: 3 docs (max score: 0.71)
       Safety gate: ESCALATE — score dispute involving third party
       Status: escalated
...
[29/29] Processing: "i am in US Virgin Islands and the merchant is saying..."
        Company: Visa | Route: Visa corpus
        Retrieved: 3 docs (max score: 0.83)
        Safety gate: PASS
        Status: replied

[✓] Done. Results written to results.csv
```

---

## Input Format

Each row in the input CSV must contain:

| Field | Description | Notes |
|---|---|---|
| `Issue` | Main ticket body or question | Required |
| `Subject` | Ticket subject line | May be blank, noisy, or irrelevant |
| `Company` | `HackerRank`, `Claude`, `Visa`, or `None` | If missing, inferred from content |

---

## Output Format

Each row in the output CSV contains:

| Field | Allowed values | Description |
|---|---|---|
| `status` | `replied`, `escalated` | Whether the agent answered or routed to a human |
| `product_area` | Free text | Most relevant support category or domain area |
| `response` | Free text | User-facing answer grounded in the support corpus |
| `justification` | Free text | Concise internal reasoning for the decision |
| `request_type` | `product_issue`, `feature_request`, `bug`, `invalid` | Best-fit classification |

---

## Design Decisions

**Single agent, three corpus collections — not multi-agent.** All three domains share the same pipeline (classify → retrieve → gate → respond). Separate agents would add orchestration complexity with no benefit, since there are no domain-specific tools or APIs involved.

**Rule-based pre-screen before the LLM.** Hard safety signals (order IDs, identity theft keywords, injection patterns) are caught by a fast rule-based check before any LLM call. This saves tokens, reduces latency, and avoids the risk of the LLM reasoning its way into a bad decision on clear-cut cases.

**Escalation over hallucination.** When the retriever finds no relevant docs (max similarity below threshold), the agent escalates rather than generating an unsupported response. Grounding is a hard constraint, not a preference.

**Few-shot from sample CSV, not fine-tuning.** The labelled examples in `sample_support_tickets.csv` are injected as few-shot context at inference time. This gives the LLM calibration on output format and decision tone without requiring any model training.

**`--build-corpus` flag separates scraping from inference.** Scraping is slow and should only happen once. Subsequent runs use the cached ChromaDB vectorstore, making the pipeline fast for repeated evaluation.



Folder Structure :



support-triage-agent/
├── agent.py                 # main entry point, CLI runner
├── scraper.py               # builds corpus from 3 URLs
├── retriever.py             # ChromaDB setup + query logic
├── classifier.py            # company inference, request_type, urgency
├── safety.py                # escalation decision logic
├── pipeline.py              # orchestrates the full per-ticket flow
├── corpus/                  # scraped + chunked docs stored here
│   ├── hackerrank/
│   ├── claude/
│   └── visa/
├── data/
│   ├── sample_support_tickets.csv
│   └── support_tickets.csv
├── requirements.txt
└── README.md
