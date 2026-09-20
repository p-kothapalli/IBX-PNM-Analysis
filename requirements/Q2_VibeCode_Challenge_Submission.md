# Q2 Vibe Coding Challenge — Submission

> Formatted to match the standard `#temp-reg-vibe-code-challenge` submission template
> (Submitter · Competency · App Name · Problem Statement · Value Delivered · Key Challenges ·
> Tech Stack and Tools · Asset Information). Copy the block below straight into the channel.

---

:bot-sweat: *#REG_VCC_SolCon_Q2_Challenge*

_Submitter_ : Prashanth Kothapalli
_Competency_: SolCon
_App Name_: Build-Verification Agent Layer — a reusable, Cursor-native agentic verification framework

_Problem Statement_ : On almost any non-trivial Salesforce delivery, the hard part isn't writing the code —
it's *proving* the code does what the spec requires before it ships. On every delivery, someone has to confirm,
by hand and inconsistently, that the work (1) **matches a source of truth** (creates the same objects / fields /
record types — or produces the same outcome — the legacy flow, requirement, or design says it should),
(2) **handles every branch / variant** and its sub-gates exactly as specified, (3) **enforces business rules in
the right layer** (eligibility / validation that used to live only in a UI now ported server-side and actually
firing), (4) **meets engineering standards** (bulk-first DML, FLS / user-mode, governor budgets, idempotency,
durable async, dead-letter handling), and (5) **clears process gates** (no open design decision silently
resolved; no field map left "inferred"; tests assert real outcomes at the coverage bar). Doing this by hand is
slow, error-prone, and varies reviewer-to-reviewer — and a missed parity or branch defect is exactly the kind of
bug that's cheap to catch at review and very expensive in production. I proved the solution on a demanding,
high-volume program — the IBX Practitioner Creation re-platforming (a complex OmniStudio guided flow being
rebuilt on bulk-first, async-only Apex by many engineers) — but **nothing about the framework is specific to it**;
the same five problem categories apply to any team shipping Salesforce code against a spec.

_Value Delivered_: Using Cursor + Claude I vibe-coded a **reusable, domain-agnostic agentic verification
framework** — a router agent plus **8 specialist verifier agents and a Critic** (10 in all), each a thin LLM
reasoning layer over a deterministic Salesforce check. A developer just asks Cursor to *"verify this delivery"*
and gets back one citation-grounded **Verification Report** with a `PASS` / `NEEDS-FIX` / `BLOCKED` verdict an
architect can sign in minutes.

• *Deterministic-before-LLM (the trust pattern).* If a fact can be produced by a command (a static DML scan, a
SOQL count, `sf code-analyzer run`, a test-coverage number), it runs as a command first; the LLM only interprets,
correlates, and explains the evidence — it never invents a "pass." Every agent writes findings into one shared,
**append-only Verification State**, and the final report is a *deterministic render* of that state.

• *The 10 agents (each answers a generic engineering question; IBX specifics are just examples):*
   1. *Parity Auditor* — same objects / fields / record types / outcome as the source of truth? *(e.g. legacy DataRaptor chain)*
   2. *Branch-Coverage* — every branch / variant and sub-gate handled as specified? *(e.g. IBC vs Delegated)*
   3. *Contract Conformance* — input + output contract conforms; business rules enforced in the right layer? *(e.g. eligibility gates ported server-side)*
   4. *Governor & Bulk-Safety* — bulk-first, within governor / FLS / security budgets? *(domain-agnostic)*
   5. *Async / Reliability* — durable: halt-on-failure, idempotent, dead-letter-handled? *(domain-agnostic)*
   6. *Service-Boundary* — architectural layer responsibilities respected? *(e.g. service vs batch)*
   7. *Test-Adequacy* — tests assert real outcomes at the coverage bar? *(domain-agnostic)*
   8. *Open-Decisions Gate* — any open / undecided item silently resolved? *(e.g. the program's Clarification Log)*
   9. *Critic / Cross-Validator* — do any agents contradict each other? scores risk 0–100 → review tier *(domain-agnostic)*
   10. *DoD Verifier (router)* — is this delivery done end-to-end against its spec? classifies the artifact, runs tools, routes the roster, renders the report.

• *Impact, proven live on its first program (IBX).* All 10 agents run as Cursor skills + an auto-trigger rule. A
recent sweep of **22 commits / 7 Apex classes** (5 new services + 2 modified) produced one consolidated,
sign-off-ready report: deterministic backbone (`sf code-analyzer run` + `sf apex run test`) → **41/41 tests pass,
93–99% coverage** per class, captured as evidence; it **caught a systemic defect early** (the same FLS / user-mode
gap repeated across 5 services — turning five investigations into *one* pattern fix), **surfaced an architecture
decision rather than noise** (a service-boundary question needing *one* architect ruling, not five ad-hoc fixes),
**distinguished real blocks from false positives** (the Critic flagged 2 "High" analyzer violations as PMD failing
to trace `Security.stripInaccessible` — suppress-with-justification, not "fix"), and gave every reviewer the *same*
check with a numeric risk score (0–100) that auto-routes to *auto-accept / architect review / owner-block* tiers.
Net effect: review that was slow, manual, and inconsistent is now a single command returning a grounded, auditable
report — accelerating delivery while *raising* the quality bar.

• *Why it's reusable (re-pointed, not rebuilt).* Six of the ten agents are already **100% domain-agnostic**
(router, Governor, Async, Service-Boundary, Test-Adequacy, Critic); the other four are *pattern*-generic and read a
swappable grounding corpus. To apply the framework to a different domain you swap **only three things** — the
**grounding corpus** (your spec / source of truth), the **deterministic checks** (your CLI / tests / metadata +
SOQL probes), and the **routing matrix** (which checks apply to which artifact) — while the router, Critic, scoring,
shared state, and report machinery are reused verbatim. The same roster re-points with no orchestration change to a
different PRM / Health Cloud form, an integration build (grounding = the integration contract), a data-migration /
ETL delivery (parity = source-vs-target reconciliation), or green-field work with no legacy (drop the Parity/Branch
agents; the other six still enforce standards, contracts, async reliability, and tests). It runs **in-IDE** for a
single delivery and as a **PR-scoped subagent** on a diff, and the backbone commands are CI-ready.

_Key Challenges_: The breakthrough — and the hardest part — was **grounding the AI so it can't hand-wave.** Every
claim must cite evidence (a Parity Ledger row, a `docs/reference/` line, or a tool output); an uncited parity claim
is auto-demoted to a manual check, which is what makes the output trustworthy enough to sign. Other non-trivial
problems solved: making the verdict + risk score **computed deterministically** from the shared state (the LLM
writes only the explanation prose, never the math) to kill the "confident but wrong" failure mode; adding a
dedicated **Critic** that reads *all* findings to catch cross-agent contradictions (e.g. "parity says this record is
created, but no test asserts it") no single-concern check could see; and deliberately keeping the framework
**reviewer-augmenting, not reviewer-replacing** — in a multi-tenant platform, a strong architect plus AI beats
either alone. The highest-leverage insight: vibe coding shines for **orchestration**, not just code — days of
multi-agent design work compressed into hours.

_Tech Stack and Tools_: Cursor (agent mode) · Claude (Sonnet / Opus) · Salesforce CLI (`sf code-analyzer`, `sf apex
run test`) · custom `.cursor` skills + rules · markdown grounding corpus (Parity Ledger, Validation / Eligibility
Rule Ledger, reference docs) · Git worktrees for read-only verification.

_Asset Information_ : All assets are version-controlled in the repo and carried with the code (no bespoke
infrastructure):
• *Framework docs:* `docs/build-verification/` — architecture, agent catalog, parity ledger, adoption playbook, eval harness, plain-language walkthrough.
• *Live agents:* `.cursor/skills/verifying-*` (10 skills) + `.cursor/rules/prm-build-verification.mdc` (auto-trigger).
• *Example output:* `docs/build-verification/reports/2026-06-29_NewServices_Delivery_Sweep.md` — a real multi-service Verification Report.
• *Re-point recipe (any team):* `docs/build-verification/04_Adoption_Playbook.md`.
• *Invocation:* ask Cursor to *"verify this delivery"* (or *"run build verification on the changed files"*) — the router classifies the artifact and selects the roster automatically; no project-specific phrasing required.
*No production or PHI data is included; examples reference object / field metadata and delivery artifacts only.*
