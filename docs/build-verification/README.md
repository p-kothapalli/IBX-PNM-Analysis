# Build-Verification Agent Layer — Practitioner Creation

> A Cursor-native layer of **verification agents** that validate every redesign component a developer
> delivers (Apex service / batch / LWC / metadata) against the **business functionality of the current
> Practitioner Creation guided flow** (IBC Professional Staff + Delegated Credentialing), the plan's
> contracts, and this org's coding standards — before it is accepted.

---

## Why this folder exists

A team of developers is re-platforming the **Practitioner Creation Form** off OmniStudio
(OmniScript + Integration Procedure + DataRaptor) onto a layered, bulk-first, async-only Apex
service architecture (see [`docs/implementation-plan/PRM_Implementation_Plan.md`](../implementation-plan/PRM_Implementation_Plan.md)
and [`CLAUDE.md`](../../CLAUDE.md)). The work is shared across many architects and devs, and each
delivery (a `PRM_*Service`, a `PRM_*Batch`, an LWC, a metadata object) must **do the same thing the
legacy guided flow did** — create the same records, in the same branches, honoring the same gates —
while meeting the new framework's reliability and governor goals.

Manually re-checking each delivery against the legacy `PRM_DelegatedPractitionerCreation` v7 /
`PRM_PractitionerAddressCreation` v5 DataRaptor chains is slow, error-prone, and inconsistent between
reviewers. This folder defines an **agentic verification layer** that does that check the same way
every time, grounded in the legacy behavior captured in [`docs/reference/`](../reference/).

This is **engineering verification** — distinct from the *business-process* Agentforce agents
proposed in the separate `IBXQA/requirements/AgenticAI/` folder (PSV Review Copilot, Credentialing
Triage, etc.). We reuse that folder's discipline (audit trail, eval-first, deterministic-before-LLM)
but the agents here review **delivered code against the legacy spec**, not provider data against policy.

---

## TL;DR

1. A developer delivers a class/component for the redesign.
2. An architect (or the dev) asks Cursor to **"verify this Practitioner Creation delivery."**
3. The **DoD Verifier** agent routes the artifact to the relevant verification agents (parity, branch
   coverage, contract, governor/bulk-safety, async/reliability, service-boundary, test-adequacy,
   clarification-log gate).
4. Each agent grounds its verdict in deterministic evidence (`sf code-analyzer`,
   `sf apex run test --code-coverage`, the shadow-mode parity harness) **plus** the legacy behavior in
   the [Parity Ledger](02_Parity_Ledger.md), appending findings to a shared **Verification State**.
5. A **Critic** then cross-validates the findings across agents (catching contradictions) and computes a
   numeric risk score that sets the review tier.
6. The run emits one **Verification Report** (a deterministic render of the state) with a verdict:
   `PASS` / `NEEDS-FIX` / `BLOCKED`, and an audit trail the architect signs off on.

---

## How to read this folder

| File | What it covers |
|------|----------------|
| `README.md` | This index + TL;DR + how to invoke |
| [`07_Agents_Glossary_Walkthrough.md`](07_Agents_Glossary_Walkthrough.md) | **Start here** — plain-language walkthrough + mind map of all 10 agents (what each does, when it runs, how the team uses them) and a glossary of every key term |
| [`00_Architecture.md`](00_Architecture.md) | The hybrid (deterministic backbone + LLM reasoning) architecture; where the agents live (skills / rules / subagents); the shared **Verification State** schema; the Critic stage; in-IDE and PR run flows; the report artifact |
| [`01_Agent_Catalog.md`](01_Agent_Catalog.md) | The 10 agents (8 verifiers + Critic / Cross-Validator + DoD Verifier) — purpose, inputs, source-of-truth, deterministic vs LLM checks, pass/fail criteria, which delivery triggers each |
| [`02_Parity_Ledger.md`](02_Parity_Ledger.md) | The machine-checkable legacy → target map (step → legacy DR/IP → objects/fields → new service/batch) and the parity nuances every reviewer gets wrong |
| [`02b_Validation_Rule_Ledger.md`](02b_Validation_Rule_Ledger.md) | The **eligibility / "must-have / can-only" rule** ground truth — branch gates, the duplicate/already-credentialed/NPI-exists/practice-location-known gates, date rules, required fields — extracted from the active OmniScript v25 + the Apex validator. Flags which rules live **only in the UI today** and must be ported server-side |
| [`03_Plan_Audit_Findings.md`](03_Plan_Audit_Findings.md) | A thorough audit of the implementation plan's *verifiability* — what is checkable now, what is blocked, and the contract/transaction-model divergences |
| [`04_Adoption_Playbook.md`](04_Adoption_Playbook.md) | How the team uses the agents day-to-day; invocation phrases; the deterministic backbone commands; the DoD checklist; the report template; specs for the new `.cursor/skills/` and `.cursor/rules/` to scaffold next |
| [`05_Reference_Agent_Audit.md`](05_Reference_Agent_Audit.md) | Audit of this design against three already-built reference agents (Mortgage Underwriting, Financial Analyst, Competitive Analysis) — the structural gaps (Critic stage, eval harness, shared state) and prioritized remediation. The three **high-severity** gaps are now merged into `00`, `01`, and `06`. |
| [`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md) | How we verify **the agents themselves** — a labeled good + seeded-defect corpus, the expected-vs-actual matrix, label canonicalization, and the calibration gate that decides when a check may block (closes audit gap G2) |

---

## Status

- **Form factor:** Cursor-native — agents are delivered as `.cursor/skills/` skills + `.cursor/rules/`
  rules, backed by deterministic Salesforce CLI / Apex checks. This slots into the org's existing
  [`.cursor/skills/`](../../.cursor/skills/) and
  [`.cursor/rules/prm-service-class-boundaries.mdc`](../../.cursor/rules/prm-service-class-boundaries.mdc).
- **Implemented (2026-06-28):** all 10 agents are now live as skills, plus an auto-trigger rule:

  | Agent (catalog) | Skill folder |
  |-----------------|--------------|
  | DoD Verifier (router) | [`.cursor/skills/verifying-practitioner-build/`](../../.cursor/skills/verifying-practitioner-build/SKILL.md) |
  | 1 Parity Auditor | [`.cursor/skills/verifying-parity/`](../../.cursor/skills/verifying-parity/SKILL.md) |
  | 2 Branch-Coverage | [`.cursor/skills/verifying-branch-coverage/`](../../.cursor/skills/verifying-branch-coverage/SKILL.md) |
  | 3 Contract Conformance | [`.cursor/skills/verifying-contract-conformance/`](../../.cursor/skills/verifying-contract-conformance/SKILL.md) |
  | 4 Governor & Bulk-Safety | [`.cursor/skills/verifying-governor-safety/`](../../.cursor/skills/verifying-governor-safety/SKILL.md) |
  | 5 Async / Reliability | [`.cursor/skills/verifying-async-reliability/`](../../.cursor/skills/verifying-async-reliability/SKILL.md) |
  | 6 Service-Boundary | [`.cursor/skills/verifying-service-boundary/`](../../.cursor/skills/verifying-service-boundary/SKILL.md) |
  | 7 Test-Adequacy | [`.cursor/skills/verifying-test-adequacy/`](../../.cursor/skills/verifying-test-adequacy/SKILL.md) |
  | 8 Clarification-Log Gate | [`.cursor/skills/verifying-clarification-log/`](../../.cursor/skills/verifying-clarification-log/SKILL.md) |
  | 9 Critic / Cross-Validator | [`.cursor/skills/verifying-cross-validation/`](../../.cursor/skills/verifying-cross-validation/SKILL.md) |
  | auto-trigger on delivery | [`.cursor/rules/prm-build-verification.mdc`](../../.cursor/rules/prm-build-verification.mdc) |

  Invoke by asking Cursor to **"verify this Practitioner Creation delivery"** (or naming
  `verifying-practitioner-build`). **Still pending:** the eval-harness corpus
  ([`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md)) that calibrates when a check may block — build
  it before promoting any check from advisory to gating.

---

## Grounding sources (the "spec" the agents check against)

The legacy guided flow is the **parity source** (per the golden source-of-truth hierarchy in
[`CLAUDE.md`](../../CLAUDE.md) §0). The agents read these as authoritative for *what records must result*:

- [`docs/reference/PRM_PractitionerCreationContainer_Process.md`](../reference/PRM_PractitionerCreationContainer_Process.md)
  — legacy container / child IP hierarchy + **DataRaptor → object impact** tables (active versions only).
- [`docs/reference/PRM_PractitionerCreation_Apex_Service_Flow.md`](../reference/PRM_PractitionerCreation_Apex_Service_Flow.md)
  — step-by-step call sequence, **object + DML counts per step**, branch decision trees, and the
  **request/response JSON contracts**.
- [`docs/reference/PRM_PractitionerCreation_Hierarchy.md`](../reference/PRM_PractitionerCreation_Hierarchy.md)
  — object hierarchy.
- [`docs/implementation-plan/PRM_Implementation_Plan.md`](../implementation-plan/PRM_Implementation_Plan.md)
  + `Epic_E_Practitioner_Services*.md` — the target services E1–E19, the five batch classes, and the
  grounded field maps (the **new** side of parity).
- [`docs/sampleInputs/PractitionerCreation/`](../sampleInputs/PractitionerCreation/) — real payloads
  (low/high volume, link-all-locations) used as contract fixtures.
