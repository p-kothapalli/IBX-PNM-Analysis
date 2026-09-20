# Patterns From `~/Documents/AgenticAI/` Notebooks

> What we already proved out in coursework, and which IBXQA use case each pattern unlocks.

---

## Why this document exists

The team has built and tested half a dozen multi-agent systems already. Rather than re-invent the wheel for IBXQA, this doc catalogs the architectural patterns from each notebook, calls out the production-grade lesson, and points to which credentialing/PDM idea reuses it.

---

## 1. Senior Mortgage Underwriting System

**Path:** `~/Documents/AgenticAI/Senior Mortgage Underwriting System/`
**Files:** `Senior_Mortgage_Underwriting_System_Solution.ipynb`, `Senior_Mortgage_Underwriting_System_Implementation_Guide.md`, `mortgage_test_cases.json`, `underwriting_policies.pdf`

### Pattern: Supervisor + N specialists + Critic + Decision + HITL

```
Initialize → Supervisor → {Credit, Income, Asset, Collateral} → Critic → Decision → END
                ↑─────────────────loop back──────────────────────┘
```

**What it does**

- Sequentially routes a mortgage application through 4 specialist analysts.
- Each specialist retrieves relevant policy chunks from a Chroma vector store (RAG over `underwriting_policies.pdf`), invokes 1–3 deterministic `@tool` functions (DTI, LTV, reserves, large-deposit checks), and writes a structured analysis into shared state.
- Critic cross-validates the four analyses, computes a numeric `risk_score` (0–100), runs a bias scan, and lists policy violations.
- Decision agent synthesizes everything into APPROVED / CONDITIONAL / REJECTED + a decision memo, and flags `human_review_required` for borderline cases.
- Memory checkpointing pauses the workflow for human review via `ipywidgets`.

**Key implementation choices we are taking forward verbatim**

- `temperature=0` for reproducibility — same input must yield same output for audit.
- `TypedDict` shared state with `Annotated[list, operator.add]` reasoning_chain → append-only audit trail.
- PII sanitization (`sanitize_pii`) **before** any LLM call — name, SSN (last 4 only), phone, address redacted.
- Bias detection (`detect_bias_signals`) on every agent's free-text output — scans for race, gender, age, religion, national origin, disability, family-status terms.
- Sequential (not parallel) specialist execution because the next specialist sometimes benefits from the prior one's output and the supervisor logic is simpler.

### IBXQA use cases this unlocks

- **Idea 03: Initial Credentialing Triage Agent** — direct 1:1 mapping. Specialists become License/Education/Work History/Sanctions/Malpractice verifiers.
- **Idea 06: Adverse Action Investigator** — same critic+decision pattern for QC cases.
- The **PRM_AgentDecision__c** audit object design is lifted from the `reasoning_chain` field.

---

## 2. Autonomous Financial Analyst

**Path:** `~/Documents/AgenticAI/Autonomous Financial Analyst/`
**Files:** `Autonomous_Financial_Analyst_Complete.ipynb`, `Companies-AI-Initiatives/`

### Pattern: Goal-driven agent + tool-calling + RAG + multi-entity ranking

**What it does**

- Single agent with a "charter" (system prompt) mandating proactive behavior — *always* check 3-year history and sentiment before recommending.
- 4 tools: `get_stock_price`, `get_stock_history`, `search_financial_news` (Tavily), `analyze_sentiment`.
- A 5th tool, `query_private_database`, runs a Chroma RAG retrieval over `Companies-AI-Initiatives/*.pdf` and returns grounded answers with citations.
- LangGraph `agent_node` ↔ `tool_node` loop with a `should_continue` router.
- Ranks 5 companies on a weighted score (60% financial perf + 40% AI innovation from RAG).

**Key implementation choices**

- The **charter** is the architectural primitive — it forces the agent to be proactive and reactive *by spec*, not by hope.
- The agent decides which tools to call and in what order — no hardcoded sequence.
- Citations from the RAG tool are mandatory — the agent must surface document IDs.
- "Multi-entity ranking" — running the same agent over a list and producing a comparable scoreboard.

### IBXQA use cases this unlocks

- **Idea 04: Recredentialing Proactive Monitor** — runs nightly, agent autonomously decides which providers to investigate, what tools to call (license boards, OIG, malpractice feeds), and produces a risk-ranked worklist.
- **Idea 05: Practice-Location Verification Agent** — agent autonomously calls Precisely, NPPES, internal DB, decides what to do with conflicts.
- **Idea 02: Bulk Practitioner Validation** — single agent looped over each spreadsheet row.

---

## 3. LexAgent (Rental Law Reasoning)

**Path:** `~/Documents/AgenticAI/RentalAgent/`
**Files:** `MLS_9_LexAgent_for_Rental_Law_Reasoning.ipynb`, `tenants_rights.pdf`, `previous_cases.pdf`

### Pattern: Jurisdiction-aware legal reasoning + precedent retrieval + plain-language explanation

**What it does**

- Agent reasons over rental laws across multiple jurisdictions (NY, CA, etc.).
- Two RAG corpora: statutes/regulations and prior case outcomes.
- Explains complex legal language in plain English to a non-lawyer.
- Reviews rental agreements for compliance with the relevant jurisdiction's law.
- Reasons over precedent — "given a similar prior case, what was the outcome?"

**Key implementation choices**

- **Two separate RAG corpora** — policy/statute corpus is read-only and immutable for audit; case-precedent corpus grows over time.
- Jurisdiction is an explicit metadata filter on retrieval — no cross-jurisdiction bleed.
- Plain-language summarizer is a separate LLM call with a different prompt — keep the legal reasoner technical and the summarizer accessible.

### IBXQA use cases this unlocks

- **Idea 06: Adverse Action Investigator** — exact analog. NCQA/state-regulation corpus + prior `QC_Case__c` history corpus + plain-language summary for the analyst.
- **Idea 03: Initial Credentialing Triage** — state-by-state license rule reasoning works the same way (NJ vs PA vs DE board rules differ).
- **Idea 08: Provider Portal Q&A Agent** — plain-language explanation of why a provider's case is in the state it's in.

---

## 4. Multi-Agent LinkedIn Post Creator

**Path:** `~/Documents/AgenticAI/MultiAgentLinkedln/`
**File:** `Multi-Agent LinkedIn Post Creator.ipynb`

### Pattern: Supervisor → Researcher → Writer → Critic + groundedness check

```
Start → Supervisor → Researcher → Supervisor → Writer → Critiquer → Supervisor → END
```

**What it does**

- Researcher uses Tavily search to gather facts on a topic.
- Writer drafts the LinkedIn post.
- Critic reviews the draft for tone, accuracy, completeness; returns either "approved" or revision feedback.
- Supervisor decides whether to loop back (more research, rewrite) or terminate.
- **Groundedness checking** verifies every factual claim in the final post is backed by something the Researcher actually retrieved.

**Key implementation choices**

- The **groundedness check** is a final LLM call that takes (a) the draft, (b) the research findings, and asks "is every claim in (a) supported by (b)?". If not, revision loop.
- Supervisor is a *decision-only* node — it routes but does not produce content.
- Critic returns structured feedback (specific bullets), not free prose, so the Writer's revision pass is targeted.

### IBXQA use cases this unlocks

- **Idea 01: PSV Review Copilot** — Researcher (pulls PSV sources) → Writer (drafts review notes) → Critic (verifies each claim is grounded in pulled source) → analyst signs.
- **Idea 07: Application Withdrawal Triage** — drafts the withdrawal response letter, critic checks tone + regulatory phrasing.
- The **groundedness check** becomes a mandatory final step before any agent output is shown to a human or persisted.

---

## 5. Competitive Analysis (MCP Single-Agent System)

**Path:** `~/Documents/AgenticAI/CompetitiveAnalysis/`
**File:** `MLS7_MCP_SingleAgentSystem.ipynb`

### Pattern: Single agent + MCP server tool integration

**What it does**

- Demonstrates how to expose external data sources as MCP (Model Context Protocol) servers.
- A single agent connects to those MCP servers and treats them as a unified toolset.
- Used for competitive-analysis research over multiple external data feeds.

**Key implementation choices**

- MCP standardizes tool integration — same interface for any external system.
- The agent doesn't need to know whether a tool is local Python, a SaaS API, or a database — it just calls the tool.

### IBXQA use cases this unlocks

- **Wrapper for external credentialing data sources** — OIG/LEIE, SAM.gov, NPPES NPI Registry, NPDB, state license boards, DEA. Each becomes an MCP server (or we use an existing AgentExchange MCP).
- **Reusable across all 9 ideas** — every agent that needs external data uses the same MCP layer.
- See `02_Notebook_to_Agentforce_Mapping.md` §"Tools" for the Agentforce equivalent.

---

## 6. AgenticRAG (Workshop notebook)

**Path:** `~/Documents/AgenticAI/Agent/AgenticRAG_W6_Rec_NB (2).ipynb`

### Pattern: Agentic retrieval — agent decides *what* to retrieve, not just *how*

**What it does**

- Standard RAG retrieves blindly on the user query.
- **Agentic RAG** wraps retrieval in agent reasoning: "What do I actually need to answer this question? Should I run multiple retrievals? Should I rewrite the query first?"
- Self-corrective loop: if first retrieval is poor, agent rephrases and retries.

**Key implementation choices**

- Query rewriting before retrieval improves recall on jargon-heavy domains (and credentialing/medical is jargon-heavy).
- Multi-hop retrieval — agent retrieves once, identifies a follow-up gap, retrieves again.
- Confidence scoring on retrieved chunks — agent rejects low-confidence results and asks for human help.

### IBXQA use cases this unlocks

- **All RAG-using ideas** benefit from this — especially `Idea 03` and `Idea 06` where policy questions can have multiple relevant standards across NCQA + IBX policy + state regulation.
- The "Should I retrieve from policy or from prior cases?" decision becomes an agentic choice rather than a hardcoded one.

---

## 7. DualLens / JHU AgenticAI Project 1

**Path:** `~/Documents/AgenticAI/DualLens/`
**Files:** `DualLens_Analytics_Completed.ipynb`, `JHU AgenticAI Project 1 Learners Notebook.ipynb`, `RUBRIC_CHECKLIST.md`, `YFINANCE_TROUBLESHOOTING.md`

### Pattern: Dual-perspective analysis (two agents look at the same data with different lenses)

**What it does**

- Two agents process the same input simultaneously with different system prompts ("financial lens" vs "AI-innovation lens").
- A final synthesizer reconciles the two perspectives.

**Key implementation choices**

- Useful when one analytical lens is insufficient and you want explicit multi-perspective reasoning rather than averaged-together blandness.
- Each lens is a separately auditable opinion — important for explainability.

### IBXQA use cases this unlocks

- **Idea 06: Adverse Action Investigator** — "compliance lens" (does this break a rule?) vs "patient-safety lens" (does this harm members?) vs "due-process lens" (was the provider given fair notice?).
- **Idea 03: Initial Credentialing Triage** — "credentials lens" (does the file meet NCQA?) vs "network-fit lens" (does the provider fill a need? — only if/when network strategy data is in scope).

---

## 8. TravelAgent (Goal-Based & Utility-Based Agent)

**Path:** `~/Documents/AgenticAI/TravelAgent/`
**File:** `Goal_Based_&_Utility_Based_Agent.ipynb`

### Pattern: Goal vs Utility agents

**What it does**

- Goal-based: "find me a trip that satisfies these constraints"
- Utility-based: "find me the *best* trip according to this scoring function"

**Key implementation choices**

- Goal-based is appropriate when the answer is binary (meets / doesn't meet credentialing standards).
- Utility-based is appropriate when we need to rank (which 5 of 50 recred files should an analyst look at first?).

### IBXQA use cases this unlocks

- **Idea 04: Recredentialing Proactive Monitor** — utility-based ranking of providers by risk score for analyst worklist prioritization.
- **Idea 03: Initial Credentialing Triage** — goal-based on individual file (meets standards? Y/N).

---

## 9. Cross-cutting takeaways

These show up in nearly every notebook and become **non-negotiable rules** for IBXQA agents:

1. **Shared state is a `TypedDict` with append-only audit lists.** No mutating prior state — only adding to it.
2. **Every specialist agent gets a focused prompt** with explicit input contract, output schema, and "if you cannot complete X, return null and explain why" failure mode.
3. **Critic agents are separate calls** — never merge "do the work" and "check the work" into one prompt.
4. **HITL pause points are designed in** from day one — even if the v1 always pauses, the architecture has to support eventual auto-pass on low-risk paths.
5. **Bias / fairness scanning is a guardrail, not a check** — it runs on every output, and the score is logged regardless of outcome.
6. **PII redaction happens before the LLM, not after.** The Trust Layer is the production version of the notebook's `sanitize_pii`.
7. **Tools are deterministic, agents are not.** Push as much logic as possible into deterministic tools (DR, Apex, Flow) and reserve LLM calls for natural-language reasoning that can't be coded.
8. **Test cases are checked into source control** alongside the agent. The mortgage notebook's `mortgage_test_cases.json` becomes our `AiEvaluationDefinition` test specs.

---

*See `02_Notebook_to_Agentforce_Mapping.md` for how each of these notebook primitives translates to Salesforce Agentforce.*
