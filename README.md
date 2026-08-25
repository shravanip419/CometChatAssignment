# Aster & Row Customer Support AI Agent

## 1. Project Overview

This repository contains an intelligent, privacy-preserving, and grounded customer support AI agent for **Aster & Row** (an ecommerce brand specializing in bags, drinkware, and travel accessories). 

The agent provides reliable customer service through:
- **Knowledge-Base RAG**: Answers customer inquiries strictly using verified Markdown policy documents with exact section citations (`[filename - Section Heading]`).
- **Read-Only Order Lookup**: Retrieves live order status, carrier information, and tracking details with automatic ID normalization and PII redaction.
- **Multi-Turn Conversations**: Maintains session context and tracks active order references across multiple turns.
- **Privacy Protection**: Enforces a strict allowlist preventing disclosure of customer PII (names, emails, delivery addresses), internal fraud risk scores, and warehouse notes.
- **Prompt Injection Defense**: Neutralizes adversarial override attempts and ignores instructions embedded inside retrieved content.
- **Source Conflict Handling**: Detects contradictions between active official policies, surfaces both positions with safe interim guidance, and flags human handoff.
- **Safe Human Handoff**: Safely abstains and marks queries for human specialist handoff when knowledge is insufficient or unsupported actions (e.g., modifying processed orders) are requested.

---

## 2. 🎥 Demo Video

https://drive.google.com/file/d/12u9K8hNQVJ24NyXHBHiQzFsya7FzmIF7/view?usp=sharing


The demonstration covers:
- Knowledge-base question answering with source citations
- Order status lookup and PII redaction
- Multi-turn conversational context retention
- Safe refusal / human handoff routing
- Automated evaluation suite execution

---

## 3. Setup & Run

### Prerequisites
- Python 3.10 or higher
- Git

### Installation

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

4. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env     # Linux/macOS
   copy .env.example .env   # Windows
   ```

### Running the CLI
- **Interactive Multi-Turn Mode:**
  ```bash
  python -m app.main --interactive
  ```
  *(Type `exit`, `quit`, or `q` to end the session)*

- **Single Query Mode:**
  ```bash
  python -m app.main --query "What is your return policy for international orders?"
  ```

- **Debug Mode:**
  ```bash
  python -m app.main --query "Where is ORD-1007?" --debug
  ```

### Running the Tests
```bash
pytest tests/ -v
```

### Running the Evaluation Suite
```bash
python evaluation/run_evaluation.py
```

---

## 4. Environment Variables

Configuration is loaded from environment variables or a local `.env` file (see `.env.example`).

| Variable | Description | Default / Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API Key for dense embeddings and LLM generation. | *Optional*. If omitted, the system automatically uses its local deterministic fallback engine. |
| `OPENAI_MODEL` | LLM model identifier for generation. | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Dense embedding model identifier. | `text-embedding-3-small` |
| `DEBUG_MODE` | Enables detailed trace logging in CLI and responses. | `false` |
| `SNAPSHOT_AT` | Reference timestamp used for time-sensitive logic. | `2026-08-15T12:00:00Z` |

> **Note on Local Fallback**: An OpenAI API key is **not mandatory**. When no API key is provided, the agent runs entirely locally using a deterministic TF-IDF vectorizer with suffix stemming and structured grounded synthesis. All 61 pytest unit/regression tests and all 22 evaluation benchmarks pass completely offline without external API access.

---

## 5. Technical Stack

- **Core Language**: Python 3.10+
- **Data Modeling & Validation**: Pydantic v2 (`BaseModel`, `Field`) for strict input/output contracts and response schemas.
- **RAG & Retrieval**: Custom in-memory vector index with hierarchical Markdown chunking, cosine similarity scoring, and metadata-aware precedence filtering.
- **Embedding & Search**: 
  - *Local fallback*: Scikit-Learn `TfidfVectorizer` with rule-based suffix stemming and subword normalization.
  - *Dense vectors (optional)*: OpenAI `text-embedding-3-small` embeddings via the `openai` SDK.
- **Vector Operations**: NumPy for cosine similarity calculations and array normalization.
- **Frontmatter Parsing**: PyYAML for parsing document metadata (authority, status, supersession).
- **Knowledge Base**: 14 Markdown policy and product care documents (`knowledge-base/`).
- **Order Database**: Local JSON mock dataset (`data/orders.json`).
- **Testing & Evaluation**: Pytest and custom benchmark harness (`evaluation/run_evaluation.py`).
- **Configuration**: `python-dotenv` for environment management.

---

## 6. Architecture

```text
User Query
   ↓
Request Router (Intent classification: RAG, Order, Privacy, Action, Injection)
   ↓
Knowledge Retriever / Order Lookup Tool
   ↓
Ranking / Safety Filtering / Conflict Handling
   ↓
Response Generation (Grounded Synthesizer / Optional LLM)
   ↓
Final Response + Citations / Human Handoff Flag
```

### Key Architectural Characteristics
- **Intent Routing**: Directs queries to specific handlers before executing costly operations.
- **Multi-Turn Session State**: Tracks conversational history and retains the active `order_id` across follow-up questions.
- **Order Data Sanitization**: The order lookup tool strictly filters internal records through an allowlisted `CustomerOrder` model, redacting customer PII, internal fraud scores, and warehouse notes before data reaches the prompt or generator.
- **Metadata Precedence Ranking**: Ranks active official policies higher, discounts internal notes, and filters out superseded/draft documents.
- **Safety Post-Validation**: Enforces strict redaction of sensitive patterns (e.g. emails) and blocks unsupported action hallucination.

---

## 7. Evaluation Results

The agent achieves a **100% pass rate** across all automated tests and evaluation benchmarks:

- **pytest Unit & Regression Suite**: `61/61 passed` (100%)
- **Automated Evaluation Benchmark**: `22/22 passed` (100%)

### Category Breakdown

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
| **Overall Total** | **22** | **22** | **0** | **100.0%** |

*(Note: Baseline evaluation figures were not documented prior to final benchmark implementation).*

---

## 8. Bug Diary

### Bug 1: Punctuation & Delimiter Failure in Order ID Normalization
- **Failure**: Entering variations such as `ORD_1007` or `ord 1007` caused the order lookup to fail with "Order ORD-_1007 was not found".
- **How it was reproduced**: Running `OrderLookupTool.lookup("ORD_1007")`.
- **Root cause**: Slicing logic (`val[:3] + '-' + val[3:]`) inserted a hyphen without stripping existing non-alphanumeric delimiters like underscores or spaces.
- **Fix**: Implemented regex digit extraction `re.search(r"ORD\D*(\d+)", raw_id)` to reliably reconstruct canonical `ORD-{digits}`.
- **Regression test**: `tests/test_regression.py::test_regression_bug1_order_id_punctuation_normalization`

### Bug 2: Raw ISO Date Formatting in Customer Order Responses
- **Failure**: Order lookups answered queries like "When will it arrive?" with raw ISO timestamps (`2026-08-22`) instead of customer-friendly formatted dates.
- **How it was reproduced**: Running `agent.process_message("Where is ORD-1007 and when should it arrive?")`.
- **Root cause**: The response generator interpolated raw date strings directly from `orders.json` without passing them through a human-readable date formatter.
- **Fix**: Added `format_date_human()` utility to format ISO timestamps into natural dates (e.g., `August 22, 2026`).
- **Regression test**: `tests/test_regression.py::test_regression_bug2_date_formatting_in_order_response`

### Bug 3: Loss of Active Order Context in Multi-Turn Conversations
- **Failure**: A follow-up query such as "When will it arrive?" immediately after "Where is ORD-1007?" failed to recognize the active order and asked the customer to supply the order ID again.
- **How it was reproduced**: Processing a two-turn conversation in a single session without repeating the order ID in the second turn.
- **Root cause**: The router evaluated the second message in isolation and did not consult `session.last_order_id`.
- **Fix**: Updated `RequestRouter` and `SessionState` to persist `last_order_id` across turns and automatically bind it when follow-up messages omit an explicit ID.
- **Regression test**: `tests/test_regression.py::test_regression_bug3_multiturn_order_context_retention`

---

## 9. Observability & Debugging

The system provides structured trace logging accessible via the `--debug` CLI flag or programmatically through `AgentResponse.debug_info`.

The inspectable trace includes:
- **User Message & Session Context**: Raw user input, session ID, and message history length.
- **Routing Decision**: Identified intent, extracted order ID, detected action type, and confidence flags.
- **Retrieved Knowledge Sources**: Chunk IDs, source filenames, section headings, and similarity scores.
- **Conflict Detection**: Boolean conflict status, conflicting document pairs, and compiled positions.
- **Tool Invocations & Results**: Sanitized tool arguments and returned allowlisted data.
- **Final Response & Flags**: Generated answer, formatted citations, and human handoff recommendation flag.

---

## 10. Known Limitations

- **Local TF-IDF Matching vs. Semantic Nuance**: When running in offline mode without an API key, retrieval relies on stemmed subword TF-IDF. Complex semantic paraphrasing may yield lower similarity scores compared to dense vector models.
- **Read-Only Order Tool**: The agent cannot execute state-changing operations (such as updating shipping addresses or cancelling processed orders) and must route these requests to human agents.
- **In-Memory Session Storage**: Multi-turn conversation sessions are maintained in-memory for the duration of the CLI process rather than persisted to a distributed database.
- **Static Knowledge Corpus**: Ingestion is designed for the current 14 Markdown documents; real-time dynamic document ingestion is not implemented.

---

## 11. AI Coding Tools Disclosure

**Antigravity IDE / Gemini AI coding assistance** was utilized during the development of this project for:
- Initial project scaffolding and Pydantic schema definitions
- Writing unit and regression test cases
- Regular expression refinement for order ID parsing
- Grounded prompt structuring and documentation

### AI Suggestion Correction Example
During initial development, an AI-generated suggestion proposed using loose fuzzy string matching (Levenshtein distance) across all database records to identify orders from partial queries. This was identified as unsafe because typos could silently match a different customer's order and leak status metadata. The suggestion was rejected and replaced with strict regex normalization matching explicit `ORD-<digits>` patterns and strict allowlist filtering.

---

## 12. Project Structure

```text
CometChatAssignment/
├── app/                  # Application source code
│   ├── agent/            # Orchestrator, router, session state, generator, and safety validator
│   ├── models/           # Pydantic schemas for documents, orders, citations, and responses
│   ├── rag/              # Markdown loader, chunker, vector index, retriever, and conflict detector
│   ├── tools/            # Read-only order lookup tool and privacy sanitization filter
│   ├── config.py         # Environment configuration and snapshot defaults
│   ├── main.py           # CLI entrypoint (interactive and single-query modes)
│   └── utils.py          # Date and string formatting helpers
├── data/                 # Mock order database (orders.json) and data dictionary
├── evaluation/           # Evaluation runner and test cases (visible-cases.json, custom-cases.json)
├── knowledge-base/       # 14 Markdown policy and product care documents
├── tests/                # 61 unit, integration, and regression pytest test cases
├── .env.example          # Template environment variable configuration
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation and submission guide
```
