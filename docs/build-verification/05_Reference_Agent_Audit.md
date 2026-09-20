# 05 — Audit of the Build-Verification Design vs. the Reference Agents

> A thorough audit of this folder's design ([`00`](00_Architecture.md)–[`04`](04_Adoption_Playbook.md))
> against three **already-built, tested** agent systems in `~/Documents/AgenticAI/`:
> **Senior Mortgage Underwriting System** (multi-agent supervisor/critic/decision), **Autonomous
> Financial Analyst** (single-agent + tools + RAG + weighted ranking), and **Competitive Analysis**
> (MCP single-agent). These are the same prototypes the IBXQA `AgenticAI` strategy was distilled from,
> so they are the closest thing we have to a proven reference implementation.
>
> **Verdict:** the design is directionally right (deterministic-before-LLM, grounded citations, an
> audit-trail artifact, reuse of existing skills) but originally **missed three structural patterns every
> reference agent implements** — a Critic/cross-validation stage with a numeric score, a self-test (eval)
> harness, and an explicit shared state with an append-only reasoning chain. Details below.
>
> **Update:** all three high-severity gaps (G1, G2, G3) have since been **merged into the docs** —
> the Critic is [`01`](01_Agent_Catalog.md) Agent 9, the shared state is [`00`](00_Architecture.md) §4.5,
> and the eval harness is [`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md). See §6 for status.

---

## 1. Pattern-by-pattern conformance

| # | Proven pattern (where it appears) | In our design? | Severity |
|---|-----------------------------------|:--------------:|:--------:|
| P1 | Deterministic tools run **before** the LLM | ✅ Yes ([`00`](00_Architecture.md) §1) | — |
| P2 | RAG/grounding: answer **only** from retrieved docs + citations (Mortgage, Fin-Analyst) | ◐ Implied, informal | Medium |
| P3 | **Critic agent**: cross-validate specialists, find contradictions (Mortgage) | ✅ **Merged** — [`01`](01_Agent_Catalog.md) Agent 9 | **High (resolved)** |
| P4 | **Numeric risk score 0–100** gating the outcome (Mortgage `risk_score`, Fin-Analyst weighted score) | ✅ **Merged** — Critic risk score + review tiers | **High (resolved)** |
| P5 | **Shared state + append-only `reasoning_chain`** (Mortgage `UnderwritingState`) | ✅ **Merged** — [`00`](00_Architecture.md) §4.5 Verification State | Medium (resolved) |
| P6 | **Eval harness**: labeled cases → expected-vs-actual matrix (Mortgage `mortgage_test_cases.json` / `Automated_Test_Report.md`; IBXQA `AiEvaluationDefinition`) | ✅ **Merged** — [`06`](06_Agent_Eval_Harness.md) | **High (resolved)** |
| P7 | **Score-gated HITL** (Mortgage: review if `risk_score > 60` or non-APPROVED) | ◐ Binary sign-off, not tiered | Medium |
| P8 | Deterministic report synthesis, no LLM math (Competitive Analysis `generate_report`) | ◐ Aggregation deterministic; not stated | Low |
| P9 | **MCP tool exposure** + graph-first (Competitive Analysis FastMCP; org `code-review-graph` MCP) | ◐ CLI/skills only; MCP under-used | Medium |
| P10 | Graceful **tool-failure** handling (Fin-Analyst charter; Mortgage NPPES-timeout→retry) | ◐ Partial | Medium |
| P11 | PII sanitization before LLM (Mortgage `sanitize_pii`) | ❌ Not addressed | Low |
| P12 | `temperature=0` / determinism for auditable decisions (all) | ◐ Implied, not stated | Low |
| P13 | Weighted composite + **ranking** of findings (Fin-Analyst 60/40) | ❌ Not used | Low |

✅ aligned · ◐ partial · ❌ missing.

---

## 2. High-severity gaps (fix before scaffolding)

### G1 — No Critic / cross-validation stage (P3)

**Reference.** The mortgage system never lets a specialist's verdict reach the Decision agent directly.
A dedicated **Critic** cross-validates all four specialists, *detects contradictions between them*,
checks policy compliance, and only then does the Decision agent synthesize. ("No specialist → verdict
shortcut" is also an explicit IBXQA guardrail.)

**Our design.** The DoD Verifier only **aggregates** per-agent verdicts (worst-of). That is a combiner,
**not** a critic — it cannot catch a *contradiction between agents*, which is exactly where verification
goes wrong. Concrete failure our current design misses:

- Parity Auditor says **PASS** (the service creates `BusinessLicense`), but Test-Adequacy shows the
  tests never assert a `BusinessLicense` was created → the parity PASS is **unverified**. Worst-of
  aggregation reports "PASS + PASS" because each agent passed *its own* check; only a Critic that reads
  *across* agents catches that the parity claim has no test backing.
- Branch-Coverage says Delegated-only objects are gated, but Governor shows a DML on a Delegated object
  in the IBC path → contradiction.

**Recommendation.** Add a **Critic stage** between the agents and the DoD Verifier's verdict:
cross-validate findings for contradictions (parity-claimed objects must be test-asserted; branch gates
must match the objects actually written; async idempotency claims must have a negative test). Emit
`contradictions[]` into the report. This is the single most important missing piece.

### G2 — No self-test / eval harness for the agents (P6)

**Reference.** Every reference project ships a **labeled test set + an expected-vs-actual report**.
Mortgage: `mortgage_test_cases.json` (3 cases with expected `APPROVED/CONDITIONAL/REJECTED`) →
`Automated_Test_Report.md` with a comparison matrix, a per-case **Match** column, and a 2/3 pass count.
The IBXQA mapping makes this `AiEvaluationDefinition` + `sf agent test run`, gated in CI.

**Our design.** We describe in detail how the agents verify *delivered code* but **never define how we
verify the agents themselves are correct.** There is no golden corpus, no expected verdicts, no
agreement metric — so we cannot know the agents' false-positive/false-negative rate before trusting them.

**Recommendation.** Add an agent eval harness (new `06_Agent_Eval_Harness.md`):
- A **labeled corpus** of deliveries: a handful of already-built, known-good `PRM_*` classes (expected
  `PASS`) plus **seeded-defect** copies (a missing object, a SOQL-in-loop, an ungated Delegated object,
  a duplicate-prone CMA write, an `*__c` left "inferred") with the expected verdict + expected finding.
- A **comparison matrix** report (mirroring `Automated_Test_Report.md`): expected verdict vs. agent
  verdict, per-agent finding match, agreement rate, false-positive / false-negative counts.
- A **calibration gate**: don't make any check *blocking* until its false-positive rate on the corpus is
  acceptable (already hinted in [`04`](04_Adoption_Playbook.md) §6, but with no measurement behind it).

**Lessons baked into the harness from the mortgage report:**
- The mortgage DTI tool produced obviously wrong numbers (86%, 113%, 133%) **and the Critic did not
  catch it** — so deterministic tools are *not* automatically trustworthy. Our analog (the static
  SObject extractor, the parity-ledger lookup) must itself be unit-tested and bounded (see G4).
- The mortgage report shows a **label mismatch** (`DENIED` vs expected `REJECTED`) flagged `⚠️`. Our
  verdict labels (`PASS/NEEDS-FIX/BLOCKED`) need **canonicalization** so a synonym isn't scored as a miss.

### G3 — No explicit shared state / append-only reasoning chain (P5)

**Reference.** Mortgage defines `UnderwritingState` (a `TypedDict` with ~20 fields) and an
`Annotated[list, operator.add]` `reasoning_chain` that **every agent appends to** — the durable,
ordered audit trail. Fin-Analyst uses `Annotated[list, add_messages]`.

**Our design.** We define a **Verification Report** ([`04`](04_Adoption_Playbook.md) §4) as an *output*,
but no **shared state contract** that the router passes to each agent and each agent appends to. Without
it, the Critic (G1) has nothing structured to read, and the report is re-narrated rather than accumulated.

**Recommendation.** Define a **Verification State** schema the DoD Verifier seeds and each agent appends
to (the doc/JSON analog of `UnderwritingState`):

```
artifact, resolved_step, branch,                       # routing
parity_findings, branch_findings, contract_findings,   # per-agent results
governor_findings, async_findings, boundary_findings,
test_findings, cl_findings,
evidence[]              # {tool, command, output_ref, ledger_citation}
contradictions[]        # from the Critic (G1)
risk_score              # 0-100 (G4)
reasoning_chain[]       # append-only, ordered, one line per agent step
verdict                 # PASS | NEEDS-FIX | BLOCKED
review_tier             # auto | architect | owner-block (G7)
```

The Verification Report is then a **deterministic render** of this state (P8), not free LLM prose.

---

## 3. Medium-severity gaps

### G4 — Numeric verification risk score + tool-trust bounds (P4, P12)

We use categorical worst-of aggregation; the references use a **numeric 0–100 score** that gates the
outcome (mortgage `risk_score > 60` → HITL; Fin-Analyst weighted 60/40 → ranking). A score lets us
**prioritize** findings and **tier** the human review (G7). Recommendation: compute a weighted
verification risk score from the per-agent findings (e.g., parity miss and open-CL weigh heaviest;
style nits lightest), normalized 0–100, and record which check contributed what. State `temperature=0`
for the reasoning agents explicitly (auditable, reproducible verdicts).

### G5 — Under-uses MCP / graph-first (P9)

Competitive Analysis exposes its tools behind **FastMCP** so the agent calls them uniformly; the org's
own conventions ([`.cursor/skills/README.md`](../../.cursor/skills/README.md)) mandate **graph-first via
the `code-review-graph` MCP** for callers/impact before Grep/Read. Our design leans on `sf` CLI +
skills and only mentions `analyzing-omnistudio-dependencies`. Recommendation: (a) use the
`code-review-graph` MCP for the Parity Auditor's "who calls / what does this write" impact analysis;
(b) consider exposing the deterministic checks (SObject extractor, parity-ledger lookup, governor-budget
probe) as MCP tools so in-IDE and CI runs call them identically.

### G6 — Score-gated HITL tiers (P7)

Mortgage gates human review by score; ours is a single architect sign-off line. Recommendation: tie the
risk score (G4) to a **review tier** — `PASS` (low score) auto-accept with spot-audit; `NEEDS-FIX`
(mid) architect review; `BLOCKED` (open-CL / unsigned map) owner unblock. Already half-present in the
verdict; make it explicit and score-driven.

### G7 — Graceful tool-failure / degraded mode (P10)

Fin-Analyst's charter mandates handling tool failures gracefully; mortgage maps an NPPES timeout to
`NEEDS_REVIEW` + retry. Our trust table covers some cases but doesn't state the rule: **if a
deterministic check cannot run** (Code Analyzer errors, no scratch org, shadow harness absent), the
dependent verdict is `BLOCKED`/`INCONCLUSIVE` — **never a silent PASS**. Add this as a first-class rule.

### G8 — Formalize RAG grounding (P2)

We cite the Parity Ledger and auto-demote uncited claims ([`00`](00_Architecture.md) §7), which is the
right instinct, but it's informal. The references make it a hard step: retrieve the relevant
ledger/reference chunk, answer **only** from it, and **reject any claim whose citation isn't in the
retrieved set**. Make that an explicit Parity-Auditor sub-step.

---

## 4. Low-severity gaps

- **G9 — PHI in fixtures (P11).** Verification runs on source code (no PHI), but delivered tests / sample
  payloads (`docs/sampleInputs/*`) may carry realistic identifiers. Add a one-line guard: no real
  PHI/Ids in fixtures sent to any external LLM; rely on Trust-Layer discipline.
- **G10 — Weighted ranking of findings (P13).** Optional: rank findings by the G4 weights so the report
  leads with the highest-risk item (Fin-Analyst ranking analog).
- **G11 — Parallelism (Mortgage future scope).** Our agents are independent; state explicitly that the
  eight verifiers run in parallel (the mermaid already implies it) for latency.

---

## 5. What the design already gets right (keep)

- **Deterministic-before-LLM** (P1) is the core principle of [`00`](00_Architecture.md) — matches every
  reference.
- **Grounded, cited verdicts** with auto-demotion of uncited claims — matches the RAG-citation guardrail.
- **Markdown audit trail** (the Verification Report) is the right doc-based analog of the mortgage
  `reasoning_chain` / IBXQA `PRM_AgentDecision__c`.
- **Reuse of existing skills** (`running-code-analyzer`, `running-apex-tests`, etc.) instead of new
  tooling — matches the "tools are deterministic actuators" pattern.
- **Worst-of aggregation is deterministic** — aligns with Competitive Analysis's no-LLM `generate_report`
  (we just need to extend it with the Critic + score).

---

## 6. Prioritized remediation (fold into the docs)

1. ✅ **DONE — Critic stage (G1)** added to [`00`](00_Architecture.md) §2/§4 (flow + mermaid) and
   [`01`](01_Agent_Catalog.md) as **Agent 9 — Critic / Cross-Validator** (DoD Verifier renumbered to
   Agent 10). *(High)*
2. ✅ **DONE — `06_Agent_Eval_Harness.md` (G2)** added — labeled good + seeded-defect corpus,
   expected-vs-actual matrix, agreement metric, calibration gate, verdict-label canonicalization. *(High)*
3. ✅ **DONE — Verification State schema (G3)** added to [`00`](00_Architecture.md) §4.5; the report is
   now a deterministic render of it. *(High / Medium)*
4. **Add the numeric verification risk score + review tiers (G4, G6)** and state `temperature=0`.
   *(Medium — partially folded in via the Critic's risk score + review tiers in [`01`](01_Agent_Catalog.md)
   Agent 9 and the eval-harness thresholds in [`06`](06_Agent_Eval_Harness.md) §5.)*
5. **Adopt graph-first / MCP (G5)** for impact analysis and (optionally) tool exposure. *(Medium)*
6. **Add degraded-mode rule (G7)** and **formalize RAG grounding (G8)**. *(Medium)*
7. **Low-severity notes (G9–G11)** as one-liners. *(Low)*

---

*This audit is itself grounded: the reference patterns are cited from
`~/Documents/AgenticAI/Senior Mortgage Underwriting System/` (`Implementation_Guide.md`,
`Automated_Test_Report.md`, `mortgage_test_cases.json`), `~/Documents/AgenticAI/Autonomous Financial
Analyst/Autonomous_Financial_Analyst_Complete.ipynb`, and
`~/Documents/AgenticAI/CompetitiveAnalysis/MLS7_MCP_SingleAgentSystem.ipynb`.*
