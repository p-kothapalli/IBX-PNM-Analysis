# Epic B — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review. No components, code, scripts, configuration, commands, or other implementation artifacts have been or will be generated until this plan is reviewed and the Open Questions (§7) are answered.**
>
> **Source of truth:** `Epic_B_Foundation_Framework.md` (B1–B7). This plan only restates and expands what that document explicitly defines. Anything not stated there is treated as **UNKNOWN** and surfaced as an Open Question — it is **not** assumed.
>
> **Reading guide:** items are tagged **[CONFIRMED]** (explicitly documented), **[OPEN]** (missing/ambiguous/contradictory — needs a decision), **[RISK]**, or **[RECOMMENDATION]**. Tasks that depend on an unresolved [OPEN] item are marked **⛔ Pending Clarification**.

---

## 1. Confirmed requirements (extracted from Epic B)

### 1.1 Scope & components *(updated per review — see §7.0)*
- **[CONFIRMED]** Epic B delivers **two reusable, form-agnostic Apex classes** + their test classes — no objects, LWC, or UI. *(`PRM_OrchestratorBase` removed — OQ-B2(a); `toSObjectList` removed — OQ-B5.)*
- **[CONFIRMED]** `PRM_FormSubUtility` — stateless utility class; initial method **`NameNormalize(String)`** (title-cases; **replaces** `PRM_OmniUtils.titleCase`). Further helpers added as services need them. *(`toSObjectList` removed from Epic B.)*
- **[CONFIRMED]** `PRM_ServiceBase` — abstract **shell**; `protected Map<String,Object> response;` + abstract `Map<String,Object> execute(Map<String,Object> params)`; **no `FlowContext`**; **no response-key contract in B** (defined later in C/E/F — OQ-B7).
- **❌ REMOVED — `PRM_OrchestratorBase`** (OQ-B2(a)): the async-only pilot has no synchronous orchestrator, so this base is dropped from Epic B (and the doc set).

### 1.2 Conventions & constraints
- **[CONFIRMED]** All classes `PRM_`-prefixed; `with sharing` unless noted; one class per file under `force-app/main/default/classes`; ≥ 85% unit coverage; **no SOQL/DML in utility/payload classes** (B-header conventions).
- **[CONFIRMED]** Test class naming `<Class>Test` (CLAUDE.md, referenced by B5).

### 1.3 Testing (B5)
- **[CONFIRMED]** **Apex unit only** at this tier; **no UI/E2E** (deferred to EPIC C/E).
- **[CONFIRMED]** Per-class test intent: `PRM_FormSubUtility` — `NameNormalize` parity vs `PRM_OmniUtils.titleCase` (multi-word, hyphen, single char, blank/null); `PRM_ServiceBase` — a concrete test subclass implements `execute()` and returns a `Map`. *(`toSObjectList` and `PRM_OrchestratorBase` tests removed.)*
- **[CONFIRMED]** Evidence: a dated **Test Evidence Report** `docs/test-evidence/Epic_B_<date>/report.md` (Apex coverage tables + raw artifact links), attached on each `epic-b/*` PR; ≥ 85% per class; **human sign-off** before `main`→`master` (B5).

### 1.4 Process (B6)
- **[CONFIRMED]** Branch model per Epic A §A8; Epic B branches `epic-b/form-sub-utility`, `epic-b/service-base`, `epic-b/orchestrator-base`, **or** a combined `epic-b/foundation-base-classes`; commit prefix `[B1]`/`[B2]`/`[B3]`; PR into `main`, squash-merge (B6).

### 1.5 Dependencies
- **[CONFIRMED]** **Depends on: nothing** — independent of EPIC A; **can run in parallel**. **Blocks: EPIC C, D, E, F** (which branch only after the foundation lands on `main`) (B-header, B6).

---

## 2. Acceptance criteria (from Epic B)

- **[CONFIRMED]** All three classes deploy and compile.
- **[CONFIRMED]** Apex unit coverage **≥ 85% per class**; all suites green (B5).
- **[CONFIRMED]** Test Evidence Report regenerated + attached on each `epic-b/*` PR; human sign-off recorded before promotion (B5).
- **[CONFIRMED]** `PRM_FormSubUtility.NameNormalize` is **parity-tested** against legacy `PRM_OmniUtils.titleCase` (B1/B5) — see OQ-B3 (oracle availability).

---

## 3. Dependencies & prerequisites

- **[CONFIRMED]** No epic dependency (parallel to A).
- **✅ OQ-B3 RESOLVED — Legacy parity oracle:** `PRM_OmniUtils` is **available in the org**; `NameNormalize` is parity-tested against `PRM_OmniUtils.titleCase` there.
- **◻ OQ-B1 — Target org** for running Apex tests + coverage (you'll confirm). Authoring needs no org; **running tests + evidence does**.

---

## 4. Cross-epic contradiction — RESOLVED

- **✅ OQ-B2 RESOLVED — `PRM_OrchestratorBase` removed (option a).** The async-only pilot has no synchronous orchestrator, so `PRM_OrchestratorBase` is **dropped from Epic B and reconciled out of the doc set** (TDD §11.1, Plan §3/§5, CLAUDE, Epic C dependency). No savepoint/rollback base or `Callable` adapter is built in the pilot.

---

## 5. Phases, milestones & task breakdown

> Each task lists Purpose · Expected outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion criteria.

### Phase 0 — Setup *(milestone M0: ready to author)*

**T0.1 — Establish working branch**
- Purpose: isolate Epic B work per B6.
- Expected outcome: branch per B6 — **single combined `epic-b/foundation-base-classes`** (recommended) or three per-component branches.
- Dependencies: none. Prerequisites: clean `main`.
- Impacted areas: VCS only.
- Validation: branch exists from latest `main`.
- Testing: n/a.
- Risks: **[RISK]** remote push currently blocked (SSH auth, carried from prior turns) — branch is local-only until resolved.
- Completion: branch created. **⛔ Pending Clarification (OQ-B6 — branch granularity).**

**T0.2 — Confirm test org ⛔ Pending Clarification (OQ-B1)**
- Purpose: ensure tests can run + coverage collected.
- Expected outcome: confirmed org alias/type. *(Parity oracle `PRM_OmniUtils` confirmed available in the org — OQ-B3 resolved.)*
- Dependencies: OQ-B1. Prerequisites: org access.
- Impacted areas: none (read-only).
- Validation: org reachable; `PRM_OmniUtils.titleCase` present for parity.
- Testing: n/a.
- Risks: **[RISK]** no org → tests can't run (Phase 3 blocked).
- Completion: org confirmed.

### Phase 1 — Utility class *(milestone M1: utility done)*

**T1.1 — `PRM_FormSubUtility.NameNormalize`**
- Purpose: shared name title-casing (B1).
- Expected outcome: a `with sharing` utility class exposing `NameNormalize(String)` per the documented behavior (title-case words; handle blank/null/single-char/hyphen).
- Dependencies: none. Prerequisites: T0.
- Impacted areas: `force-app/main/default/classes/PRM_FormSubUtility.cls` (+ meta).
- Validation: compiles; unit tests assert documented cases.
- Testing: parity vs `PRM_OmniUtils.titleCase` (oracle in org — OQ-B3); multi-word, hyphen, single char, blank/null.
- Risks: ✅ parity oracle available; expected outputs = legacy `titleCase` behavior.
- Completion: method + tests green; parity confirmed.

> *(`toSObjectList` removed from Epic B — OQ-B5. The utility ships with `NameNormalize` only; further helpers are added when a consuming service defines the need.)*

### Phase 2 — Base class *(milestone M2: base done)*

**T2.1 — `PRM_ServiceBase` (abstract shell)**
- Purpose: entry-point contract for every service (B2).
- Expected outcome: `public abstract with sharing class` with `protected Map<String,Object> response;` + abstract `execute(Map<String,Object>)`. **Shell only — no response-key contract in B** (OQ-B7; keys defined later in C/E/F).
- Dependencies: none. Prerequisites: T0.
- Impacted areas: `classes/PRM_ServiceBase.cls` (+ meta).
- Validation: compiles; a concrete `@isTest` subclass implements `execute()` and returns a `Map`.
- Testing: per B2/B5 (coverage via the test subclass).
- Risks: ✅ OQ-B7 resolved — shell only.
- Completion: class + test green; ≥ 85% via test subclass.

> *(`PRM_OrchestratorBase` removed — OQ-B2(a). No orchestrator base in the pilot.)*

### Phase 3 — Validation *(milestone M3: tested)* ⛔ Pending Clarification (OQ-B1)
- Purpose: run Apex tests + measure coverage (B5).
- Expected outcome: all suites green; ≥ 85% per class.
- Dependencies: T1–T2; OQ-B1 (org). Prerequisites: deployable classes + org.
- Impacted areas: none (test execution).
- Validation: test results + coverage parsed.
- Testing: this is the test run.
- Risks: **[RISK]** abstract classes require concrete `@isTest` subclasses for coverage; **[RISK]** no org → cannot run (OQ-B1).
- Completion: green + ≥ 85% per class.

### Phase 4 — Evidence & governance *(milestone M4: signed off)*
- Purpose: assemble the Test Evidence Report + human sign-off (B5).
- Expected outcome: `docs/test-evidence/Epic_B_<date>/report.md` (Apex coverage tables + artifact links); sign-off on the PR.
- Dependencies: Phase 3. Prerequisites: test results.
- Impacted areas: `docs/test-evidence/Epic_B_<date>/`.
- Validation: report assembled; sign-off recorded.
- Testing: n/a (no UI tier at foundation).
- Risks: **[RISK]** without an org, coverage evidence can't be produced — report would be specs-only (B5 capability boundary).
- Completion: report + sign-off.

### Phase 5 — Version control *(milestone M4)*
- Purpose: integrate per B6/A8.
- Expected outcome: `[B*]` commits; PR into `main`; squash-merge after green CI + review.
- Dependencies: Phase 3 (+ Phase 4). Prerequisites: passing checks.
- Impacted areas: VCS.
- Validation: PR merged; promote `main`→`master` at milestone + tag (optional).
- Testing: CI gates (lint · Apex tests).
- Risks: **[RISK]** remote push blocked (SSH auth).
- Completion: merged per B6.

---

## 6. Decisions log (review round 1) & residual recommendations

- **✅ OQ-B2(a)** — `PRM_OrchestratorBase` **removed** from Epic B and the doc set (no synchronous orchestrator in the async-only pilot).
- **✅ OQ-B5** — `toSObjectList` **removed** from Epic B (`PRM_FormSubUtility` ships `NameNormalize` only; helpers added when a consumer needs them).
- **✅ OQ-B3** — parity oracle `PRM_OmniUtils` **available in the org**; `NameNormalize` parity-tested against `PRM_OmniUtils.titleCase`. *(OQ-B4 expected-outputs is thereby defined by the legacy method's behavior.)*
- **✅ OQ-B7** — `PRM_ServiceBase` ships as an **abstract shell only**; the response-map key contract is defined later in C/E/F.
- **[RECOMMENDATION] OQ-B6 — single combined branch** `epic-b/foundation-base-classes` for the two small classes — proceeding with this unless you object.
- **[NOTE] Out of scope but adjacent (unchanged):** `PRM_RecordTypeUtil` (→ EPIC E), `PRM_ExceptionLogger`/`PRM_ValidationException`/`PRM_PayloadValidator` (reuse existing / EPIC F). Hidden dependencies for C/E/F.

---

## 7. Open Questions — remaining

- **◻ OQ-B1 — Target org** for running Apex tests + coverage (you'll confirm). Blocks Phase 3–4 only (not authoring). *Recommendation:* scratch org for the unit run.

*(Resolved: OQ-B2 removed orchestrator base; OQ-B3 oracle in org; OQ-B4 defined by oracle; OQ-B5 removed toSObjectList; OQ-B6 combined branch (recommended); OQ-B7 shell only.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-B1 | ~~`toSObjectList` undefined~~ | — | — | ✅ Resolved — `toSObjectList` removed from Epic B (OQ-B5) |
| R-B2 | ~~`PRM_OrchestratorBase` dead code~~ | — | — | ✅ Resolved — removed (OQ-B2a) |
| R-B3 | ~~Parity oracle absent~~ | — | — | ✅ Resolved — `PRM_OmniUtils` available in org (OQ-B3) |
| R-B4 | Abstract `PRM_ServiceBase` needs a concrete `@isTest` subclass for ≥85% coverage | Confirmed | Low | author a test subclass |
| R-B5 | No org → tests can't run / no coverage evidence | Medium | Medium | OQ-B1 provide org; else specs-only report |
| R-B6 | Removed classes (logger/validation/RecordTypes) referenced by C/E/F but not built in B | Confirmed | Medium (downstream) | tracked (CL-13 / Epic E CL-E5 / EPIC F) — no B action |
| R-B7 | Remote push blocked (SSH auth) | Confirmed | Low | resolve credentials before Phase 5 |

---

## 9. Gaps & hidden dependencies (summary)

- **Org** for test execution/evidence — the only remaining blocker (OQ-B1).
- **Downstream-only:** `PRM_RecordTypeUtil` (Epic E), `PRM_ExceptionLogger`/validation classes (reuse/Epic F) — not Epic B, but consumers depend on them.

---

## 10. What happens after sign-off

Epic B scope is now **two classes** (`PRM_FormSubUtility` with `NameNormalize`; `PRM_ServiceBase` abstract shell) + their test classes. The only remaining blocker is **OQ-B1 (target org)** for running tests/coverage. On your go-ahead I will: (1) author the two classes + test classes on `epic-b/foundation-base-classes`, then **pause for the org**, then (2) run the Apex unit suite + collect coverage, (3) assemble the Epic-B Test Evidence Report, and (4) pause for human sign-off (B5) before any `main`→`master`. **No artifacts will be created until you say go.**
