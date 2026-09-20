# AgenticAI for IBXQA Credentialing & PDM

> Discovery & design notes for applying multi-agent AI patterns (LangGraph / Salesforce Agentforce) to Provider Credentialing, Re-credentialing, PSV, and Provider Data Management workflows.

---

## Why this folder exists

The team has prototyped multi-agent systems in `~/Documents/AgenticAI/` (Senior Mortgage Underwriting, Autonomous Financial Analyst, LexAgent rental law, Multi-Agent LinkedIn Post Creator, Competitive Analysis MCP, etc.). Those notebooks already encode the patterns we need to bring **autonomous, auditable, policy-grounded decision agents** into IBXQA.

Salesforce **Agentforce** + **Agent Script** + **Einstein Trust Layer** + **Data Cloud / Intelligent Context** is the production-grade equivalent of those notebooks. This folder maps the patterns we proved out in coursework to **9 concrete IBXQA use cases**, ranks them by ROI/feasibility, and proposes a phased rollout starting with the **PSV Review Copilot** (lowest risk, highest visibility).

---

## How to read this folder

| File | What it covers |
|------|----------------|
| `README.md` | This index |
| `00_Strategy_AgenticAI_for_Credentialing_PDM.md` | Executive-level strategy: why agents now, the 9 ideas at a glance, recommended sequencing, success metrics, risks |
| `01_Patterns_From_AgenticAI_Notebooks.md` | What we learned from each `~/Documents/AgenticAI/*` project — the architecture patterns we're reusing |
| `02_Notebook_to_Agentforce_Mapping.md` | Translation table: LangGraph / LangChain primitives → Salesforce Agentforce equivalents |
| `03_Roadmap_Sequencing.md` | Phased delivery plan with effort, dependencies, kill-criteria |
| `ideas/Idea01_PSV_Review_Copilot.md` | **Tier 1, recommended first build** — embedded in PSV Review LWC redesign |
| `ideas/Idea02_Bulk_Practitioner_Validation_Agent.md` | **Tier 1** — pre-flight validator for spreadsheet uploads |
| `ideas/Idea03_Initial_Credentialing_Triage_Agent.md` | **Tier 1** — full multi-agent triage with shadow-mode rollout (mortgage-underwriting analog) |
| `ideas/Idea04_Recredentialing_Proactive_Monitor.md` | Tier 2 — autonomous nightly monitor (Financial Analyst analog) |
| `ideas/Idea05_Practice_Location_Verification_Agent.md` | Tier 2 — PDM address/location reconciliation |
| `ideas/Idea06_Adverse_Action_Investigator.md` | Tier 2 — QC case triage (LexAgent analog) |
| `ideas/Idea07_Application_Withdrawal_Triage_Agent.md` | Tier 3 — extends the live `Nonroutine_ApplicationWithdrawal` story |
| `ideas/Idea08_Provider_Portal_QA_Agent.md` | Tier 3 — provider-facing Agentforce Service Agent |
| `ideas/Idea09_Credentialing_Analyst_Copilot.md` | Tier 4 — internal "ask my book of work" copilot |

---

## TL;DR

1. **Start with `Idea01` (PSV Review Copilot).** It's an LWC-embedded *drafter*, not a *decider*. Lowest regulatory risk, dovetails with `PSV_Review_LWC_Redesign_Detailed_Design.md` already in flight.
2. **Then `Idea02` (Bulk Practitioner Validation).** Mostly tool-calling (NPI, sanctions, dedup), low LLM-judgment surface. Plugs straight into the existing `BulkPractitionerCreation_Mockup.html`.
3. **Then `Idea03` (Initial Credentialing Triage)** in **shadow mode** — agent predicts, committee decides, we measure agreement before letting the agent ever auto-route.
4. Reuse the verifier sub-agents from #3 to build `Idea04` (Recred Proactive Monitor) on a schedule.
5. Address-graph and adverse-action agents (`Idea05`, `Idea06`) come once we have the pattern locked in.

---

## Guardrails (apply to every idea in this folder)

These come straight from the Senior Mortgage Underwriting notebook, the Einstein Trust Layer docs, and NCQA auditability requirements:

- **Temperature = 0** for any agent whose output influences a credentialing decision.
- **PII redaction before LLM** — Trust Layer handles this on Agentforce; verify in test traces.
- **Critic agent + numeric risk score** before any Decision agent. No specialist → verdict shortcut.
- **Append-only audit trail** (`reasoning_chain`) persisted to a custom object — NCQA needs to be able to ask "why did the system flag this provider in 2026-Q3?" and get a complete reproducible answer.
- **HITL is non-negotiable** for any case in the conditional/borderline band.
- **RAG-ground every policy citation** — the LLM is never allowed to invent NCQA standard numbers, IBX policy section IDs, or state regulation citations.
- **Bias detection** on every free-text agent output, modeled on the mortgage notebook's `detect_bias_signals()`. Maps to Agentforce **Trust Layer guardrails** + a custom protected-class scanner for credentialing-specific terms (specialty, language, country of education).
- **Shadow mode → assist mode → autonomous** is the rollout sequence for any decision-impacting agent. Never ship straight to autonomous.

---

## Open questions to resolve before building

- Which IBX Agentforce / Data Cloud / Einstein license tier is procured? (Drives whether we can use Intelligent Context for unstructured ingestion or have to roll our own RAG.)
- NCQA / state-regulator stance on AI-assisted credentialing decisions — what level of disclosure / explainability is required?
- Source of truth for the policy RAG corpus: NCQA standards PDFs, IBX internal credentialing policy manual, state board rule sets — who owns updates?
- MCP server availability for OIG/LEIE, SAM.gov, NPPES, NPDB, state license boards — buy from AgentExchange vs. wrap existing internal APIs.
- Data residency / PHI handling rules for any external LLM call.

---

*Author: Provider Network Management engineering, IBXQA*
*Created: 2026-05-22*
