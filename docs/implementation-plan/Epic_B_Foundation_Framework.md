# Epic B — Foundation Framework (Implementation Guide)

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.3) · `PRM_Implementation_Plan.md` (EPIC B) · `PRM_Apex_Reference_Implementation.md`
> **Goal:** build the reusable, form-agnostic Apex scaffolding every service/orchestrator depends on — utilities, base classes, shared state, and the typed payload model.
> **Estimate:** ~2.0 engineer-days (typed payload model moved to EPIC F; `FlowContext` dropped — shared state flows in the `params` map; `PRM_ExceptionLogger`/`PRM_ValidationException`/`PRM_PayloadValidator`/`PRM_RecordTypes` removed — see CL-13). · **Depends on:** none. Independent of EPIC A — **can run in parallel**. · **Blocks:** EPIC C, D, E, F.

> **Conventions:** all classes `PRM_`-prefixed, `with sharing` unless noted; one class per file under `force-app/main/default/classes`; ≥ 85% unit coverage; no SOQL/DML in utility/payload classes.

---

## B1 · `PRM_FormSubUtility` — High Volume utility class — *1.0 d*

- **Purpose:** central home for shared, stateless utility/transformation helpers used across the form-submission services. New helpers are added here over time.
- **Methods (initial):**
  - `**NameNormalize(String)`** — title-cases a name; **replaces `PRM_OmniUtils.titleCase`**.
  - *(more transformation helpers to be added as services need them.)*

> **Scope note (ratified):** `toSObjectList` is **not** part of Epic B — removed for now; add a list-reshaping helper here only when a consuming service defines its mapping contract.

```apex
public with sharing class PRM_FormSubUtility {
    public static String NameNormalize(String input) {
        if (String.isBlank(input)) return input;
        List<String> out = new List<String>();
        for (String w : input.toLowerCase().split('\\s+')) {
            out.add(w.length() <= 1 ? w.toUpperCase() : w.substring(0,1).toUpperCase() + w.substring(1));
        }
        return String.join(out, ' ');
    }
}
```

- **Tests:** `NameNormalize` parity with legacy `PRM_OmniUtils.titleCase` (multi-word, hyphen, single char, blank/null).

> **Removed from EPIC B (this revision):** `PRM_ExceptionLogger`, `PRM_ValidationException`, `PRM_PayloadValidator`, `PRM_RecordTypes`. They are still **referenced** by EPIC C (logging → `PRM_ExceptionLog__c`), EPIC F (validation), and EPIC E (`PRM_RecordTypes`) — their home is **TBD** (reuse an existing org class vs relocate to the consuming epic). See TDD §12 **CL-13**.

---

## B2 · `PRM_ServiceBase` — *0.5 d*

- Minimal **abstract shell** + entry-point contract for every service. Each concrete service implements `execute()`.
- **No `FlowContext` class** — the shared state (record Ids + context) flows **inside the `params` map** passed to `execute()`, and results are returned in the response map.
- **Shell only:** the response-map **key contract** (e.g. `success`/`error`) is **not** defined in Epic B — it's specified later in the consuming epics (C/E/F).

```apex
public abstract with sharing class PRM_ServiceBase {
    protected Map<String, Object> response;
    public abstract Map<String, Object> execute(Map<String, Object> params);
}
```

- **Tests:** a concrete (`@isTest`) subclass implements `execute()` and returns a `Map<String,Object>`.

> **❌ `PRM_OrchestratorBase` removed (ratified).** The async-only pilot has **no synchronous orchestrator** (intake is a plain wrapper that validates → calls `PRM_CaseService` → inserts `PRM_AsyncJob__c`), so the orchestrator base + `Callable`/savepoint pattern is **not built** in Epic B. If a future synchronous flow needs it, it can be introduced then.

---

## B4 · Build order, dependencies & effort

```
B1 PRM_FormSubUtility   ·   B2 PRM_ServiceBase
```

- B1/B2 are independent of each other and of EPIC A. (Typed payload model → EPIC F.)


| Task                      | Est (d) |
| ------------------------- | ------- |
| B1 `PRM_FormSubUtility` (NameNormalize) | 0.5 |
| B2 `PRM_ServiceBase`      | 0.5     |
| **EPIC B total**          | **~1.0** |


> The typed payload model is delivered in **EPIC F — Orchestration**. *(B3 `PRM_OrchestratorBase` removed; B1 reduced to `NameNormalize` after `toSObjectList` was dropped.)*

---

---

## B5 · Testing strategy

> **Test architecture.** Foundation classes are validated by **Apex unit tests** wired into CI as **gating quality checks** on every `epic-b/*` branch. There is **no UI/E2E layer at this tier** — the foundation is headless (no LWC); UI/E2E coverage is introduced in the epics that ship UI (C/E). Each run emits **deterministic coverage evidence** consolidated into a **Test Evidence Report**, attached to the PR behind a **human governance gate** (independent review + sign-off) before promotion to a higher environment.

### Test layers

| Layer | Scope | Tooling | Agent role |
| --- | --- | --- | --- |
| **Apex unit** | `PRM_FormSubUtility`, `PRM_ServiceBase` | `sf apex run test --code-coverage --result-format json` | author `*Test` classes (≥ 85% per CLAUDE.md), run, parse pass/fail + coverage |
| **UI / E2E** | — | — | **N/A at the foundation tier (no LWC/UI)** — deferred to EPIC C/E |

### What gets tested

- **`PRM_FormSubUtility`** — `NameNormalize` parity vs legacy `PRM_OmniUtils.titleCase` (multi-word, hyphen, single char, blank/null).
- **`PRM_ServiceBase`** — a concrete test subclass implements `execute()` and returns a `Map<String,Object>`.

### Evidence & report

- **Apex:** JUnit/JSON results + per-class coverage table + org-wide coverage %.
- The agent assembles a dated **Test Evidence Report** — `docs/test-evidence/Epic_B_<date>/report.md` — with the coverage tables and links to raw artifacts, attached on each `epic-b/*` PR.

### Acceptance

- Apex ≥ **85%** per class (org policy); all suites green.
- Report regenerated and attached on each `epic-b/*` PR into `main`.

### Human-in-the-loop

- Agent automation **does not replace** human verification — a team member reviews the Test Evidence Report and the foundation API (method signatures, parity behaviour) and **signs off** on the PR before the `main` → `master` promotion.
- Any agent-flagged failure or ambiguous parity result is triaged by a human before merge; the sign-off is recorded on the PR.

### Agent capability boundary

- The agent **authors** the `*Test` classes, **runs** them via CLI, **collects** coverage, and **assembles** the evidence report. No browser/UI capture applies at this tier.

---

## B6 · Git strategy

> Follows the canonical branch model in **Epic A §A8**: `master` (release line) ← `main` (integration) ← short-lived `epic-b/<component>` branches; PR into `main`, squash-merge, promote `main` → `master` at the epic milestone + tag.

### Epic B branches (`epic-b/<component>`)

| Branch | Scope |
| --- | --- |
| `epic-b/form-sub-utility` | B1 — `PRM_FormSubUtility` |
| `epic-b/service-base` | B2 — `PRM_ServiceBase` |

*(B1/B2 may also be delivered together on a single `epic-b/foundation-base-classes` branch since they are small and independent. `PRM_OrchestratorBase` removed.)*

### Sequencing & dependencies

- **Depends on:** nothing — independent of EPIC A; can run in parallel.
- **Internal order:** B1/B2 are independent of each other (branch/merge in any order, or together).
- **Blocks:** EPIC C, D, E, F — those branch only after the foundation classes land on `main` (single-owner rule for the shared base classes).
- **Commit convention:** prefix with the B-task id — e.g. `[B1] PRM_FormSubUtility NameNormalize`, `[B2] PRM_ServiceBase abstract shell`.
- **Evidence:** per the Testing strategy (B5), attach the Test Evidence Report (Apex coverage) on each `epic-b/*` PR; human sign-off before the `main` → `master` promotion.

---

## B7 · Open items


| Ref                          | Item                                                                                                                               | Status / Action                                                                                            |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| CL-13 (removed base classes) *(mostly resolved)* | Homes for `PRM_ExceptionLogger` / `PRM_ValidationException` / `PRM_PayloadValidator` / `PRM_RecordTypes` (referenced by C/E/F) | **Resolved:** `PRM_ExceptionLogger` **exists in the org** → reuse (Epic C `logFailure`). `PRM_RecordTypes` → replaced by a cached-describe util **`PRM_RecordTypeUtil`** (Epic E §E0.2; home tracked as Epic E CL-E5). `PRM_ValidationException` + `PRM_PayloadValidator` → live in **EPIC F** (validator F2). — Tech Lead to ratify |
| Practitioner RT *(resolved)* | Account "Practitioner" record-type DeveloperName                                                                                 | **Resolved:** `PRM_Practitioner` (grounded from `PRMDRCreateCaseCaseManagerAndAccount` RT `QUERY` — Epic E §E0.3 / E1). |
| Payload shape *(grounded)*   | OmniScript JSON keys + `practitionerCreationType` literals per sub-DTO                                                            | **Grounded per service** in Epic E (`caseManagerInfo`/`practitionerInfo`/`businessLicenses[]`/…; literals `"IBC Professional Staff"` / `"Delegated Credentialing"`). Remaining: consolidate into the **F1 typed payload model** — Eng |
| Logger correlation *(decided)* | correlation id source for `PRM_ExceptionLogger`                                                                                 | **Decided:** async failures use the parent **`PRM_AsyncJob__c.Id`** (Epic C `logFailure`); sync logging uses the case / IndividualApplication id. — confirm at wiring |


