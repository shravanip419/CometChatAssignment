# Aster & Row Customer Support AI Agent

## Project Overview

This repository contains an intelligent, privacy-preserving, and grounded customer support AI agent for **Aster & Row** (an ecommerce retailer for travel bags, drinkware, and outdoor accessories).

The system reliably handles customer inquiries through:
- **Grounded Knowledge-Base RAG**: Answers policy and product care questions using verified Markdown documents with exact section citations (`[filename - Section Heading]`).
- **Read-Only Order Lookup**: Retrieves live order status, carrier information, and tracking details with automatic ID normalization and PII redaction.
- **Multi-Turn Context**: Maintains conversational state and tracks active order references across follow-up queries.
- **Privacy & Security Protection**: Prevents disclosure of customer PII (emails, shipping addresses), internal risk scores, and warehouse notes.
- **Prompt Injection Defense**: Neutralizes system prompt overrides and ignores instructions embedded inside retrieved content.
- **Source Conflict Handling**: Detects contradictions between active official documents, presents dual-position guidance, and flags human handoff.
- **Safe Human Handoff**: Gracefully abstains and flags human review for ungrounded queries or unsupported actions (e.g. modifying processed orders).

---

## Demo Video

Demo: [▶️ Watch the 2–4 Minute Demo Video](https://drive.google.com/file/d/12u9K8hNQVJ24NyXHBHiQzFsya7FzmIF7/view?usp=sharing)

The demonstration covers:
1. Knowledge-base question answering with source citations
2. Order status lookup and PII redaction
3. Multi-turn conversational context retention
4. Safe refusal and human handoff routing
5. Automated evaluation suite execution

---

## Key Features

- **Precedence-Aware Retrieval**: Prioritizes active official policies over legacy (`02-returns-policy-legacy.md`) and internal drafts (`14-internal-content-migration-notes.md`).
- **Deterministic Local Engine**: Operates completely offline out-of-the-box using a stemmed subword TF-IDF vectorizer and structured synthesis; seamlessly integrates with OpenAI models (`gpt-4o-mini`, `text-embedding-3-small`) if configured.
- **Strict PII Allowlist**: Sanitizes order records before data reaches response generation, suppressing stale ETAs for cancelled/returned orders.
- **Zero Action Hallucination**: Explains modification/cancellation rules without fabricating order state changes.

---

## Architecture / Workflow

```text
User Query
   ↓
Request Router (Intent: Knowledge RAG | Order Lookup | Privacy | Action | Prompt Injection)
   ↓
Knowledge Retriever / Order Lookup Tool
   ↓
Ranking / Safety Filtering / Conflict Handling
   ↓
Response Generation (Grounded Synthesizer / Optional LLM)
   ↓
Final Response + Citations / Human Handoff Flag
```

### Flow Breakdown
1. **Routing**: Analyzes intent and extracts order IDs or action intents.
2. **Retrieval / Tool Execution**: Queries section-chunked policy index or retrieves sanitized order records.
3. **Ranking & Filtering**: Applies metadata boosts (1.25x for official active policies) and suppresses superseded documents.
4. **Response Generation**: Synthesizes grounded answers citing verified sections.
5. **Safety Validation**: Validates output against PII leaks and action hallucinations.

---

## Project Structure

```text
CometChatAssignment/
├── app/                  # Application source code
│   ├── agent/            # Orchestrator, router, session state, generator, safety validator
│   ├── models/           # Pydantic schemas for documents, orders, citations, and responses
│   ├── rag/              # Markdown loader, chunker, vector index, retriever, conflict detector
│   ├── tools/            # Read-only order lookup tool and privacy sanitization filter
│   ├── config.py         # Environment configuration and snapshot defaults
│   ├── main.py           # Interactive and single-query CLI entrypoint
│   └── utils.py          # Date formatting and helper functions
├── data/                 # Mock order records (orders.json) and data dictionary
├── evaluation/           # 22-case benchmark suite and runner (run_evaluation.py)
├── knowledge-base/       # 14 Markdown policy and product care documents
├── tests/                # 61 unit, integration, and regression pytest test cases
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Git

### Quickstart

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd CometChatAssignment
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration (Optional):**
   ```bash
   copy .env.example .env   # Windows
   cp .env.example .env     # Linux / macOS
   ```
   *Note: An OpenAI API key is optional. All tests and evaluation benchmarks run 100% offline without external services.*

---

## Running the Application

### Interactive CLI
```bash
python -m app.main --interactive
```
*(Type `exit`, `quit`, or `q` to leave the chat session)*

### Single Query
```bash
python -m app.main --query "What is your return policy for international orders?"
```

### Debug Trace Mode
```bash
python -m app.main --query "Where is ORD-1007?" --debug
```

---

## Running Tests & Evaluation

### Run Pytest Suite
```bash
pytest tests/ -v
```
**Result**: `61/61 passed` (100%)

### Run Evaluation Suite
```bash
python evaluation/run_evaluation.py
```
**Result**: `22/22 passed` (100% pass rate)

| Category | Total Cases | Passed | Failed | Pass Rate |
|---|:---:|:---:|:---:|:---:|
| **abstention** | 2 | 2 | 0 | 100.0% |
| **conversation** | 1 | 1 | 0 | 100.0% |
| **groundedness** | 4 | 4 | 0 | 100.0% |
| **multi-source-grounding** | 1 | 1 | 0 | 100.0% |
| **privacy** | 1 | 1 | 0 | 100.0% |
| **prompt-security** | 2 | 2 | 0 | 100.0% |
| **retrieval** | 4 | 4 | 0 | 100.0% |
| **source-conflict** | 1 | 1 | 0 | 100.0% |
| **tool-reliability** | 4 | 4 | 0 | 100.0% |
| **tool-use** | 2 | 2 | 0 | 100.0% |
| **Total** | **22** | **22** | **0** | **100.0%** |

---

## Example Interactions

### 1. Grounded Policy Query with Citation
```text
Customer > What is the standard return window?
Agent    > Items can be returned within 30 days of delivery for a full refund if unused and in original packaging with tags attached.
Sources  : [01-returns-and-exchanges.md - Standard Return Policy]
```

### 2. Multi-Turn Order Tracking
```text
Customer > Where is ORD-1007?
Agent    > Order ORD-1007 contains 1x TrailPlus Backpack (Olive) and 1x Breeze Tumbler 20oz (Matte Black). It is currently Shipped via FedEx (Tracking: FDX-99281-X) and estimated to arrive on August 22, 2026.

Customer > When will it arrive?
Agent    > Your order ORD-1007 is estimated to be delivered on August 22, 2026 via FedEx.
```

### 3. Source Conflict Surfacing & Safe Handoff
```text
Customer > Is the Breeze Tumbler dishwasher safe?
Agent    > There is conflicting official guidance regarding the Breeze Tumbler:
           - Product Care policy indicates that insulated drinkware is hand-wash only.
           - Breeze Tumbler product card states that it is top-rack dishwasher safe.
           For safety, we recommend hand washing pending clarification. A customer specialist has been notified.
Sources  : [11-product-care.md - Drinkware], [12-breeze-tumbler-product-card.md - Care Instructions]
[Human Handoff Flag: True]
```

---

## Bug Diary / Engineering Lessons

### Bug 1: Non-Hyphen Delimiters in Order ID Normalization
- **Failure**: Inputting `ORD_1007` or `ord 1007` resulted in lookup failure `Order ORD-_1007 was not found`.
- **How it was reproduced**: Calling `OrderLookupTool.lookup("ORD_1007")`.
- **Root cause**: Slicing logic (`val[:3] + '-' + val[3:]`) inserted a hyphen without stripping existing punctuation or space delimiters.
- **Fix**: Replaced slicing with regex digit extraction `re.search(r"ORD\D*(\d+)", raw_id) -> f"ORD-{digits}"`.
- **Regression test**: `tests/test_regression.py::test_regression_bug1_order_id_punctuation_normalization`

### Bug 2: Raw ISO Date Formatting in Customer Order Responses
- **Failure**: Order responses included raw ISO dates (`2026-08-22`) instead of formatted natural language dates.
- **How it was reproduced**: Querying `Where is ORD-1007 and when should it arrive?`.
- **Root cause**: The generator interpolated raw timestamp strings directly from `orders.json`.
- **Fix**: Implemented `format_date_human()` to format dates into `Month D, YYYY` (e.g. `August 22, 2026`).
- **Regression test**: `tests/test_regression.py::test_regression_bug2_date_formatting_in_order_response`

### Bug 3: Active Order Context Loss Across Follow-up Turns
- **Failure**: Follow-up query "When will it arrive?" lost the previously referenced order ID and re-prompted the user.
- **How it was reproduced**: Sending "Where is ORD-1007?" followed by "When will it arrive?" in the same session.
- **Root cause**: The router analyzed follow-up turns in isolation without checking session memory.
- **Fix**: Updated `RequestRouter` to inherit `session.last_order_id` for contextual order follow-ups.
- **Regression test**: `tests/test_regression.py::test_regression_bug3_multiturn_order_context_retention`

---

## Design Decisions & Limitations

- **Deterministic Fallback vs. Semantic Embeddings**: The offline TF-IDF vectorizer provides instant, zero-dependency local execution. For large corpora with extreme paraphrasing, switching to dense embeddings (`OPENAI_API_KEY`) is supported.
- **Read-Only Scope**: Order management is strictly read-only to prevent unauthorized state mutations; cancellation and address modification requests are routed to human agents.
- **In-Memory Session Store**: Session state is held in-memory for the CLI runtime lifecycle.

---

## AI Coding Tools Disclosure

**Antigravity IDE / AI assistance** was used during development for scaffolding, unit test generation, regex refinement, and documentation.
- **Correction Example**: An early AI suggestion proposed fuzzy string matching across all order records for order lookup. This was rejected because fuzzy matching could return false-positive matches for other customers' orders; it was replaced with strict regex normalization and allowlist validation.
