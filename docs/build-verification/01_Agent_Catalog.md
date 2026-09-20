# 01 — Agent Catalog

> Ten agents: eight verifiers + a Critic / Cross-Validator + the DoD Verifier router. Each is a thin LLM
> reasoning layer over a deterministic check, grounded in the [Parity Ledger](02_Parity_Ledger.md) and
> [`docs/reference/`](../reference/). All agents read/write the shared **Verification State**
> ([`00_Architecture.md`](00_Architecture.md) §4.5). This file is the spec each agent's skill/rule is
> built from.

Every agent emits a per-check verdict:

- **PASS** — verified against deterministic evidence + cited legacy spec.
- **NEEDS-FIX** — a concrete, citable defect; the report names the file/line and the legacy expectation.
- **BLOCKED** — cannot be certified because an upstream input is open (an unresolved Clarification-Log
  item, an "inferred" field map, an unassigned batch step). Names the owner who must unblock.

---

## Routing matrix (which agents run for which delivery)

| Delivered artifact | Parity | Branch | Contract | Governor | Async | Svc-Boundary | Test | CL-Gate |
|--------------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `PRM_*Service.cls` (E1–E19) | ✅ | ✅ | – | ✅ | ◐ | ✅ | ✅ | ✅ |
| `PRM_*Batch.cls` (the five) | ✅ | ✅ | – | ✅ | ✅ | – | ✅ | ✅ |
| `PRM_AsyncOrchestrator` / trigger / `*CleanupBatch` | – | – | – | ✅ | ✅ | – | ✅ | ✅ |
| `PRM_*Selector.cls` (Epic D) | ◐ | – | – | ✅ | – | – | ✅ | ✅ |
| `PractitionerCreationPayloadValidator` / IP wrapper (Epic F) | – | ✅ | ✅ | ✅ | ◐ | – | ✅ | ✅ |
| `prm*` LWC (Epic C5 / intake) | – | – | ✅ | – | ◐ | – | ✅ | ✅ |
| `objects/` · `customMetadata/` · `permissionsets/` (Epic A) | ◐ | – | – | – | ◐ | – | – | ✅ |

✅ = always · ◐ = conditional (only if the artifact touches that concern) · – = not applicable.
The **DoD Verifier** (Agent 10, router) always runs, the **Clarification-Log Gate** always runs, and the
**Critic** (Agent 9) always runs after the routed verifiers — it cross-validates whatever subset ran.

---

## Agent 1 — Parity Auditor

**Purpose.** Prove the delivered service/batch creates/updates the **same objects and fields** the
legacy DataRaptor chain created for the equivalent step — no missing objects, no extra objects, correct
record types.

**Inputs.** The delivered `PRM_*Service` / `PRM_*Batch`; its resolved legacy step (Plan §8.1); the
[Parity Ledger](02_Parity_Ledger.md) row(s) for that step; the legacy DR→object tables in
[`PRM_PractitionerCreationContainer_Process.md`](../reference/PRM_PractitionerCreationContainer_Process.md) §5
and the step tables in [`PRM_PractitionerCreation_Apex_Service_Flow.md`](../reference/PRM_PractitionerCreation_Apex_Service_Flow.md).

**Deterministic checks.**
- Extract the SObject types touched by the delivered class (DML statements + `newSObject`/typed
  builders) — a static scan, not opinion.
- Cross-reference record types resolved (must be by cached describe, not SOQL on `RecordType`).
- Reconcile the legacy reference against **active** OmniStudio metadata via the
  `analyzing-omnistudio-dependencies` skill before trusting a reference table.

**LLM reasoning.** Map delivered object set ↔ Parity Ledger expected set; classify each as
`matched / missing / extra / renamed-by-CL`; explain each delta with citations.

**Pass/fail.**
- PASS — every expected object is produced, no unexplained extras, RTs correct, and (if the field map
  is signed off) every required field is mapped.
- NEEDS-FIX — a missing/extra object, a wrong record type, or a field mapped to the wrong target.
- BLOCKED — the service's DR→object **field map is still "inferred"** (CL-11): certify object-level,
  block field-level until the per-service map is signed off.

**Watch the traps (from the Parity Ledger):** PPL means `HealthcarePractitionerFacility` (CL-2);
`HealthcarePractitionerFacilityNetwork` must **not** be created (CL-3) — async creates
`HealthcareFacilityNetwork` only; CDM is **one** coalesced write (assert final field state, never write
count).

---

## Agent 2 — Branch-Coverage

**Purpose.** Prove the delivery branches **IBC Professional Staff vs Delegated Credentialing** exactly
as legacy, and honors the Delegated sub-gates.

**Inputs.** Delivered class; the branch decision trees in
[`PRM_PractitionerCreation_Apex_Service_Flow.md`](../reference/PRM_PractitionerCreation_Apex_Service_Flow.md) §"Branch decision tree"
and [`PRM_PractitionerCreationContainer_Process.md`](../reference/PRM_PractitionerCreationContainer_Process.md) §6.

**Checks.**
- The branch key is `PractitionerCreationType` and the two values match legacy exactly.
- Delegated-only services (E3 Group, E6 Education, E7 BoardCert, E9 File, E10 Contact, E11 Language,
  E13–E15, E17–E18) do **not** run on the IBC branch.
- Sub-gates honored: `CaseManagerId` present → location/facility/network block (steps 11–15 legacy);
  `FileData` present → file pipeline; `languages` non-empty → PersonLanguage; existing-primary path.
- `isExistingNPI` delta behavior (only deltas processed) matches legacy.

**Pass/fail.** NEEDS-FIX if a Delegated-only object is created on IBC, a gate is missing/inverted, or
an existing-NPI path creates records it should skip.

---

## Agent 3 — Contract Conformance

**Purpose.** Prove the request payload model and the response shape conform to the contract, and make
the **async response divergence explicit** so it is not mistaken for a regression.

**Inputs.** F1 typed payload model; the JSON contracts + sample responses in
[`PRM_PractitionerCreation_Apex_Service_Flow.md`](../reference/PRM_PractitionerCreation_Apex_Service_Flow.md) §"Sample Input JSON contracts";
the fixtures in [`docs/sampleInputs/PractitionerCreation/`](../sampleInputs/PractitionerCreation/); and
**the [Validation / Eligibility Rule Ledger](02b_Validation_Rule_Ledger.md)** (the eligibility-rule ground truth).

**Checks.**
- The payload model deserializes every sample fixture losslessly (round-trip).
- Required keys per branch (`practitionerCreationType`, `practitioner.npi`, `caseInfo`, `group` for
  Delegated, `locationsToUpsert`, …) are present and typed.
- **Eligibility / "must / can-only" rules:** for a delivered `PractitionerCreationPayloadValidator` (or
  intake artifact), every rule in [`02b_Validation_Rule_Ledger.md`](02b_Validation_Rule_Ledger.md) §2–§4
  (R-E*, R-D*, R-F*) has a **server-side check + a negative test** proving the rejection. These rules
  live in the **OmniScript UI today** and must be ported server-side for the async model — an unported
  eligibility gate (R-E1–R-E3 duplicate / already-credentialed) is the highest-risk miss.
- **Response contract:** the new intake returns `{ success, AsyncJobId }` immediately and defers heavy
  creation. The agent verifies this is the *intended* new contract (not legacy
  `PractitionerScreenRecordIds` synchronously) and that downstream consumers/null-guards are accounted
  for. Legacy IBC responses were already sparse — that asymmetry is expected.

**Pass/fail.** NEEDS-FIX on a lossy round-trip, a missing required key, an eligibility rule from the
ledger with no server-side check/negative test, or a response that silently drops a field a consumer
depends on without documenting the async deferral. **BLOCKED** if an R-E1–R-E3 duplicate/already-being-
credentialed gate is absent (it prevents bad data, not just a noisy field).

---

## Agent 4 — Governor & Bulk-Safety

**Purpose.** Prove the delivery is bulk-first and within the per-batch governor budgets.

**Inputs.** Delivered class; org standards ([`CLAUDE.md`](../../CLAUDE.md) §6); the legacy DML/SOQL
baselines in [`PRM_PractitionerCreation_Apex_Service_Flow.md`](../reference/PRM_PractitionerCreation_Apex_Service_Flow.md) §"Sync DML count audit".

**Deterministic checks (this agent is mostly deterministic).**
- `sf code-analyzer run` (PMD/SFGE) over changed files via the `running-code-analyzer` skill — no
  SOQL/DML in loops, FLS/CRUD enforced, no hardcoded Ids.
- Static scan: at most **one bulk DML per object type**; parents inserted before children.
- Perf harness (G3): `Test.startTest()/stopTest()` capture asserting per-submission budgets —
  **IBC DML ≤ 12 · Delegated DML ≤ 28 · SOQL ≤ 40 · CPU < 5000 ms · heap < 2 MB** (now per-batch
  ceilings, CL-10).
- `WITH USER_MODE` / `Security.stripInaccessible`; record types via cached describe.

**LLM reasoning.** Explain any analyzer finding in the context of this service's job; flag loops that
*look* bulk-safe but accumulate per-record DML across helper calls.

**Pass/fail.** NEEDS-FIX on any SOQL/DML-in-loop, multiple DML per object type, missing FLS, or a
budget breach in the perf harness.

---

## Agent 5 — Async / Reliability

**Purpose.** Prove the async-framework semantics: halt-on-failure chain, idempotency, DLQ, resumable
retry, no whole-submission savepoint.

**Inputs.** Delivered batch / `PRM_AsyncOrchestrator` / trigger; the async design in
[`CLAUDE.md`](../../CLAUDE.md) §4.3 + [`PRM_Implementation_Plan.md`](../implementation-plan/PRM_Implementation_Plan.md) §6;
the CMA spec (`epic-e-services/E19_PRM_CMAService.md`).

**Checks.**
- Chain **halts on first `Failed` step** (later steps do not run; completed records persist).
- **Idempotency:** External-Id upserts and/or status guards (a `Completed` step is never reprocessed);
  CMA uses the **pre-check** dedup (`PRM_CaseManager__c` + RecordType + primary lookup), no duplicate
  `PRM_CaseManagerAssociation__c`.
- Failures logged via `PRM_ExceptionLogger` → `PRM_FailedRecordStaging__c` (DLQ) with the
  `PRM_AsyncJobDetails__c` lookup.
- **No whole-submission savepoint/rollback** (that contradicts the async-only model — legacy's
  `rollbackOnError` is intentionally *not* reproduced; see [Audit](03_Plan_Audit_Findings.md)).
- Batch calls back `findNextJob` in `finish()`; `Database.executeBatch` not started from a trigger body.
- Payload read from the ContentVersion file (`jsonFileParser`), not a Long Text field.

**Pass/fail.** NEEDS-FIX on a missing status guard, a duplicate-prone CMA write, a savepoint that
re-introduces synchronous atomicity, or a chain that continues past a failure.

---

## Agent 6 — Service-Boundary

**Purpose.** Enforce the existing [`prm-service-class-boundaries.mdc`](../../.cursor/rules/prm-service-class-boundaries.mdc)
on delivery — a service is a generic transformer; the batch supplies context.

**Inputs.** Delivered `PRM_*Service`; the rule.

**Checks.**
- No SOQL / selector / describe-for-context inside the service to fetch inputs.
- No cross-object correlation (e.g. CaseManager → Account → NPI) inside the service.
- Reads every dependency from `params`; builds in memory; one bulk DML per object type; returns a
  generic response map; `extends PRM_ServiceBase` implementing `execute(Map<String,Object>) : Map<String,Object>`.

**Pass/fail.** NEEDS-FIX on any self-context SOQL or flow/source-specific branching that belongs in the
batch/intake.

---

## Agent 7 — Test-Adequacy

**Purpose.** Prove the delivery's tests actually exercise the parity behavior, not just compile-coverage.

**Inputs.** The `PRM_*Test` class; org test standards ([`CLAUDE.md`](../../CLAUDE.md) §6 Tests); the
`running-apex-tests` skill.

**Deterministic checks.**
- `sf apex run test -n <Class>Test --code-coverage` → **≥ 85%** (deploy gate is 75%).
- Coverage spans **bulk (200) · single · empty · negative/halt-on-failure** paths.

**LLM reasoning.**
- Assertions check **outcomes** (records created with the right fields/RTs per the Parity Ledger), not
  just "no exception."
- No `@isTest(SeeAllData=true)`; uses `PRM_TestDataFactory`.
- Async wrapped in `Test.startTest()/stopTest()`; asserts the async completed and the DLQ behaves on
  forced failure.

**Pass/fail.** NEEDS-FIX on < 85%, missing bulk/negative path, `SeeAllData`, or assertion-free "happy
path only" tests.

---

## Agent 8 — Clarification-Log Gate

**Purpose.** Stop deliveries that silently resolve or contradict an **open** Clarification-Log item, or
diverge from the golden source-of-truth hierarchy.

**Inputs.** Delivered artifact; the Clarification Log ([`CLAUDE.md`](../../CLAUDE.md) §3.4, TDD §12).

**Checks.**
- No `*__c` left "inferred" in the delivered service before its tests (CL-11 gate).
- `GroupRelatedBatch` deliveries are flagged `BLOCKED` until the batch↔service mapping is assigned
  (CL-15).
- Async target scope honored — `HealthcareFacilityNetwork` only; **not** `NetworkMember`/`NetworkMemberChunk`
  (CL-6 partial: those are roster-sync, out of pilot scope).
- Uses real log object names `PRM_ExceptionLog__c` / `PRM_ExceptionLogEvent__e` (CL-5), not the legacy
  `PRM_Exception_Log__c`.
- Reuses existing selectors/validator (CL-8/CL-9) rather than rebuilding.

**Pass/fail.** BLOCKED on any open-CL contradiction; NEEDS-FIX on a stale name / rebuilt-instead-of-reused
component.

---

## Agent 9 — Critic / Cross-Validator

**Purpose.** A dedicated adversarial reviewer that runs **after** the routed verifiers and reads the
*whole* [Verification State](00_Architecture.md#45-verification-state-the-shared-append-only-object).
A single verifier only sees its own concern; the Critic catches conflicts **between** agents and assigns
a numeric risk score. This is the pattern proven in the Senior Mortgage Underwriting system (specialists
→ Critic → decision) — see [`05_Reference_Agent_Audit.md`](05_Reference_Agent_Audit.md).

**Inputs.** The full Verification State: every agent's findings + evidence + `reasoning_chain`. It runs
**no** new tools and produces **no** new parity claims — it only reasons over what the verifiers already
proved.

**Checks (cross-agent contradictions).**
- **Parity PASS but Test-Adequacy has no assertion** for that object/field → contradiction (parity is
  unproven by tests).
- **Branch-Coverage says Delegated-only** but the Parity Auditor cited an **IBC-only** object (or vice
  versa) → branch/parity conflict.
- **Contract Conformance PASS** for an output field that **no** parity finding shows being written →
  contract claims a record the service never creates.
- **Governor PASS** (one bulk DML) but a parity finding implies a **per-record** child insert → bulk vs.
  parity conflict.
- **Async/Reliability PASS** but a finding references a synchronous response field → model conflict.
- **Any verdict that rests on uncited evidence** (no Ledger row / tool output) → low-confidence flag.

**Risk score (0–100, deterministic weights).** Computed from the State, *not* by the LLM: e.g.
`BLOCKED` finding = 40, unresolved contradiction = 25, `NEEDS-FIX` = 15, uncited claim = 10, low test
coverage delta = 10 (capped at 100). The score sets the **review tier**: `0–20 auto-accept`,
`21–60 architect review`, `61–100 owner-block`. Thresholds are tunable and pinned by the eval harness
([`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md)).

**Pass/fail.** The Critic does not overturn a verifier verdict; it **appends contradictions + the risk
score** to the State. An **unresolved** contradiction demotes the aggregate to at least `NEEDS-FIX`.

**Output.** `contradictions[]` + `risk_score` + `review_tier` written to the Verification State.

---

## Agent 10 — DoD Verifier (router / orchestrator)

**Purpose.** The single entry point. Classifies the artifact, maps it to its legacy step, selects and
sequences the agent subset, runs the deterministic backbone, invokes the Critic, and renders one report
+ verdict from the Verification State.

**Aggregation rule (deterministic).** Any `BLOCKED` → overall `BLOCKED`; else any unresolved Critic
contradiction or any `NEEDS-FIX` → `NEEDS-FIX`; else `PASS`. The risk score sets the review tier. The
verdict is computed from the State — the LLM never decides it.

**Definition of Done it enforces** (per [`CLAUDE.md`](../../CLAUDE.md) §7.3):
- DR→object field map extracted + signed off (no `*__c` "inferred").
- `extends PRM_ServiceBase`; hosted in its batch per CL-15; batch branches IBC/Delegated and calls back
  `findNextJob`.
- One bulk DML per object type; reads via Epic D selectors; RTs via cached describe.
- ≥ 85% coverage incl. bulk (200) + negative/halt-on-failure; real assertions.
- Conforms to the §6 pre-commit checklist.

**Output.** The Verification Report (template in [`04_Adoption_Playbook.md`](04_Adoption_Playbook.md)).
