# Aster & Row Customer Support Agent

A reliable, privacy-preserving, and precedence-aware AI customer support agent for **Aster & Row** (ecommerce bags, drinkware, and travel accessories).

The system handles policy questions via grounded RAG, checks order status via read-only tools, maintains multi-turn conversation memory, strictly prevents private data leakage, defends against prompt injection, surfaces active source conflicts, and abstains with human handoffs when information is insufficient.

---

## 1. Overview

- **Knowledge-Base RAG:** Answers customer questions using verified policy documents with mandatory source citations (`[filename - Section Heading]`).
- **Read-Only Order Lookup:** Retrieves order status and tracking details with automatic ID normalization and PII redaction.
- **Multi-Turn Conversations:** Retains context and active order IDs across conversational turns.
- **Privacy & Safety Protection:** Strict allowlisting prevents disclosure of customer emails, shipping addresses, internal risk scores, and warehouse notes.
- **Prompt Injection Defense:** Treats retrieved documents and user messages as untrusted data, refusing system prompt overrides and unauthorized actions.
- **Active Conflict Surfacing:** Detects contradictions between active official documents, presents both positions with safest interim guidance, and triggers human handoff.
- **Safe Abstention:** Gracefully abstains and flags human handoff when knowledge is absent (e.g., vegan certification claims).

---

## 2. Key Features

- **Precedence-Aware Retrieval:** Automatically prioritizes active official policies over superseded (`02-returns-policy-legacy.md`) and draft/unapproved documents (`14-internal-content-migration-notes.md`).
- **Dynamic Confidence Filtering:** Applies relative score drop-off thresholding (`relative_threshold=0.22`) and confidence floors (`min_score=0.04`) to eliminate irrelevant tail chunks.
- **Status Precedence Masking:** Suppresses stale tracking numbers and delivery estimates for `cancelled` and `returned` orders.
- **Deterministic Offline Fallback:** Operates out-of-the-box with a stemmed subword TF-IDF vectorizer; seamlessly upgrades to dense embeddings (`text-embedding-3-small`) and structured generation (`gpt-4o-mini`) when configured.
- **Zero Action Hallucination:** Safety validator verifies the agent never claims an order was modified or cancelled without backend system confirmation.

---

## 3. Architecture

```
User Query
   ↓
Intent / Safety Routing (Router)
   ↓
RAG Retrieval ─────→ Knowledge Base (14 Documents)
   ↓
Ranking / Precedence (MetadataRanker)
   ↓
Context + Session State (SessionManager)
   ↓
Response Generation (Grounded Synthesizer / LLM)
   ↓
Safety Validation (SafetyValidator)
   ↓
Final Answer / Human Handoff (AgentResponse)
```

### Directory Roles
- `app/agent/`: Agent orchestration (`SupportAgent`), intent routing, session memory state, prompt templates, grounded generation, and safety validation.
- `app/rag/`: Markdown loading, hierarchical chunking, embedding generation, vector indexing, metadata precedence ranking, dynamic conflict detection, and retrieval coordination.
- `app/tools/`: Read-only order lookup tool and order sanitization filter.
- `app/models/`: Pydantic v2 data schemas (`AgentResponse`, `DocumentChunk`, `CustomerOrder`, etc.).
- `data/`: Mock order database (`orders.json`) and data dictionary.
- `knowledge-base/`: 14 policy and product care Markdown documents.
- `evaluation/`: Benchmark evaluation cases (`visible-cases.json`, `custom-cases.json`) and evaluation runner (`run_evaluation.py`).
- `tests/`: 61 automated pytest test cases across 13 test modules.

---

## 4. RAG / Retrieval Design

1. **Ingestion & Hierarchical Chunking:** Markdown documents with YAML frontmatter are loaded by `loader.py` and section-chunked by `chunker.py`, preserving `document_id`, `status`, `policy_authority`, `audience`, and supersession links.
2. **Fielded Vector Indexing:** Chunks are indexed as `f"{title} — {heading}\n{content}"` using `VectorIndex`.
3. **Embedding Engine:** Supports OpenAI `text-embedding-3-small` dense embeddings with a deterministic fallback using scikit-learn's `TfidfVectorizer` with rule-based suffix stemming and English stop-word filtering.
4. **Metadata-Aware Ranking:** `MetadataRanker` boosts active official policies (`1.25x`), demotes internal documents (`0.8x`), and excludes superseded/draft documents from customer-facing answers.
5. **Dynamic Precision Filtering:** Prunes candidates scoring below `max_score * 0.22` or `min_score = 0.04`, eliminating unrelated tail chunks for narrow queries while preserving multi-source context.
6. **Conflict Detection:** `ConflictDetector` evaluates active document contradictions (e.g. `11-product-care.md` hand-wash vs `12-breeze-tumbler-product-card.md` dishwasher-safe) and compiles dual-position guidance.

---

## 5. Order Lookup

- **ID Normalization:** `OrderLookupTool.normalize_order_id` converts inputs like `ord_1007`, `ord 1007`, `ord1007` to canonical `ORD-1007`.
- **Strict Allowlist:** `OrderSanitizer` passes only customer-safe fields: `order_id`, `membership_tier`, `items`, `status`, `carrier`, `tracking_number`, `estimated_delivery`, and `customer_safe_message`.
- **PII & Internal Data Protection:** Customer names, email addresses, shipping addresses, fraud risk scores, internal notes, and support tags are never exposed.
- **Stale ETA Suppression:** When status is `cancelled` or `returned`, stale estimated delivery dates and tracking numbers are stripped.
- **Missing / Unknown IDs:** Prompts for missing order IDs without fabricating status; flags human handoff for unknown IDs (`ORD-9999`).

---

## 6. Safety and Reliability

- **Prompt Injection Defense:** Refuses adversarial attempts to reveal internal system prompts or follow instructions embedded in retrieved scratchpads.
- **Privacy Protection:** Rejects direct queries for customer PII and internal operational notes, routing to human support.
- **Action Protection:** Explains policies for address changes or cancellations while enforcing human confirmation for non-pending orders.
- **Safe Abstention:** Acknowledges missing information and sets `handoff: true` when answering out-of-scope questions.
- **Multi-Turn Context:** Tracks `last_order_id` and conversational history so follow-up questions resolve accurately.

---

## 7. Project Structure

```
ai-agent-intern-test-main/
├── app/
│   ├── agent/             # Orchestration, router, prompts, generator, safety, state
│   ├── rag/               # Chunker, embeddings, index, loader, ranking, retriever, conflicts
│   ├── tools/             # Order lookup and privacy sanitizer
│   ├── models/            # Pydantic v2 schemas
│   ├── config.py          # Centralized configuration & environment loader
│   ├── main.py            # CLI entrypoint
│   └── utils.py           # Shared date and text formatting helpers
├── data/                  # Mock order records and data dictionary
├── knowledge-base/        # 14 policy and product care documents
├── evaluation/            # Automated 22-case benchmark suite and runner
├── tests/                 # 61 pytest test cases across 13 modules
├── .env.example           # Example environment configuration
├── .gitignore             # Git ignore rules for cache & environments
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```

---

## 8. Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language |
| **Pydantic v2** | Domain modeling, data validation, and schema definitions |
| **scikit-learn** | Subword TF-IDF text vectorization and cosine similarity calculation |
| **NumPy** | Array manipulations, vector normalization, and dot-product similarity |
| **PyYAML** | YAML frontmatter parsing and document metadata loading |
| **OpenAI API** | Optional LLM generation (`gpt-4o-mini`) and dense embeddings (`text-embedding-3-small`) |
| **pytest** | Unit, integration, and regression test framework |
| **python-dotenv** | Environment variable management |

---

## 9. Setup and Installation

### Windows PowerShell Setup
```powershell
# 1. Clone repository and navigate to folder
git clone <repository-url>
cd ai-agent-intern-test-main

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment configuration (optional)
copy .env.example .env
```

### Environment Variables (`.env`)
```ini
OPENAI_API_KEY=               # Optional: OpenAI API Key (offline fallback used if omitted)
OPENAI_MODEL=gpt-4o-mini      # Optional: LLM model name
OPENAI_EMBEDDING_MODEL=text-embedding-3-small # Optional: Embedding model name
DEBUG_MODE=false              # Optional: Output structured debug traces in CLI
```
*Note: All 61 pytest tests and 22 evaluation benchmarks run deterministically offline without requiring an API key.*

---

## 10. Running the Application

### Interactive CLI Mode
```powershell
python -m app.main --interactive
```
*Type `exit` or `quit` to end the session.*

### Single Query Mode
```powershell
python -m app.main --query "Where is ORD-1007 and when should it arrive?"
```

### Debug Trace Mode
```powershell
python -m app.main --query "Where is ORD-1007?" --debug
```

---

## 11. Testing

```powershell
pytest tests/ -v
```
**Verified Result: `61 passed`** (100% pass rate across 13 test modules covering RAG, router, agent, multi-turn state, order sanitization, safety validator, and regression tests).

---

## 12. Evaluation

```powershell
python evaluation/run_evaluation.py
```

**Verified Result: `22/22 passed` (100.0% Pass Rate)**

| Category | Total Cases | Passed | Failed | Pass Rate |
|---|---|---|---|---|
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
| **Total Benchmark** | **22** | **22** | **0** | **100.0%** |

---

## 13. Bug Diary / Engineering Lessons

### Bug 1 — Non-Hyphen Delimiters in Order ID Normalization
- **Reproduction:** Inputting `ORD_1007` or `ord 1007` resulted in lookup failure `Order ORD-_1007 was not found`.
- **Root Cause:** Slicing logic `val[:3] + '-' + val[3:]` inserted a hyphen without stripping the existing delimiter `_`.
- **Fix:** Replaced naive slicing with regex prefix and digit extraction `re.search(r"ORD\D*(\d+)", raw_id) -> f"ORD-{digits}"`.
- **Regression Test:** `tests/test_regression.py::test_regression_bug1_order_id_punctuation_normalization`.

### Bug 2 — Raw ISO Date Formatting in Order Delivery Responses
- **Reproduction:** Querying `Where is ORD-1007 and when should it arrive?` returned raw ISO string `2026-08-22`.
- **Root Cause:** The generator interpolated the raw database ISO string instead of formatting customer-friendly dates.
- **Fix:** Created `format_date_human` in `app/utils.py` converting ISO dates to `Month D, YYYY` format (`August 22, 2026`).
- **Regression Test:** `tests/test_regression.py::test_regression_bug2_date_formatting_in_order_response`.

### Bug 3 — Retrieval Noise from Static Top-K Slicing
- **Reproduction:** Focused queries like `Do you ship internationally?` retrieved 6 mixed chunks across domestic delivery and address changes.
- **Root Cause:** Unconditional top-k slicing retained low-similarity tail chunks (80% score drop-off) in prompt context.
- **Fix:** Implemented dynamic relative score thresholding (`relative_threshold=0.22`) and minimum confidence floor (`min_score=0.04`) in `MetadataRanker.rank()`.
- **Regression Test:** `tests/test_rag.py::test_retriever_trailplus_policy` and `tests/test_multiturn.py::test_multiturn_canada_followup`.

---

## 14. Known Limitations

- **Offline Lexical Matching:** When run without an OpenAI API key, fallback retrieval relies on stemmed TF-IDF vector similarity.
- **Read-Only Scope:** Order management is strictly read-only; address modifications and cancellations for processing orders require human specialist handoff.
- **CLI Interface:** Current implementation provides interactive and single-query terminal interfaces rather than a hosted web UI.

---

## 15. Production Improvements

- **Hybrid Vector Database:** Transition from in-memory indexing to a persistent hybrid vector database (e.g. Qdrant / Pinecone) with a cross-encoder neural reranker (e.g. Cohere Rerank).
- **Session Persistence:** Implement Redis or PostgreSQL session stores for production multi-turn conversational history.
- **API Gateway:** Wrap agent in a FastAPI service with OpenAPI documentation and WebSocket streaming support.
- **Observability:** Integrate OpenTelemetry tracing to monitor retrieval latency, token consumption, and hallucination metrics.

---

## 16. AI-Assisted Development

- **Tools Used:** Antigravity IDE and Gemini AI Assistant were used for boilerplate generation, test scaffolding, and regex pattern refinement.
- **Example Correction:** An early AI suggestion proposed using fuzzy string distance matching across all order fields during lookup. This was rejected because fuzzy matching on invalid order IDs risked returning another customer's order status; it was replaced with strict regex normalization and allowlist filtering.

---

## 17. Demo

A short demo should demonstrate:
1. Knowledge-base question with citations
2. Order lookup
3. Multi-turn conversation
4. Refusal / human handoff
5. Evaluation suite

> Demo video/GIF: to be added before submission.

---

## 18. Submission Notes

- Repository contains complete source code, test suites, evaluation benchmark harness, policy knowledge base, and mock data.
- No real API keys or sensitive secrets are committed; environment configuration is managed via `.env.example`.
- Generated runtime artifacts (`.pytest_cache/`, `__pycache__/`, `*.pyc`) are excluded via `.gitignore`.

