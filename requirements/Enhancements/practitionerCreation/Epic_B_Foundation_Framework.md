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
  - `**toSObjectList(List<Object>, SObjectType)**` — reshapes a list of maps → typed SObjects; **replaces `PRM_OmniUtils.convertToListSobjects`**.
  - *(more transformation helpers to be added as services need them.)*

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
    public static List<SObject> toSObjectList(List<Object> rows, SObjectType t) {
        // reshape list of maps → typed SObjects (replaces PRM_OmniUtils.convertToListSobjects)
        List<SObject> result = new List<SObject>();
        // ... mapping logic ...
        return result;
    }
}
```

- **Tests:** `NameNormalize` parity with legacy `PRM_OmniUtils.titleCase` (multi-word, hyphen, single char, blank/null); `toSObjectList` reshapes maps → typed SObjects; empty list → empty.

> **Removed from EPIC B (this revision):** `PRM_ExceptionLogger`, `PRM_ValidationException`, `PRM_PayloadValidator`, `PRM_RecordTypes`. They are still **referenced** by EPIC C (logging → `PRM_ExceptionLog__c`), EPIC F (validation), and EPIC E (`PRM_RecordTypes`) — their home is **TBD** (reuse an existing org class vs relocate to the consuming epic). See TDD §12 **CL-13**.

---

## B2 · `PRM_ServiceBase` — *0.5 d*

- Minimal abstract base + entry-point contract for every service, mirroring `PRM_OrchestratorBase`. Each concrete service implements `execute()`.
- **No `FlowContext` class** — the shared state (record Ids + context) flows **inside the `params` map** passed to `execute()` / `run()`, and results are returned in the response map.

```apex
public abstract with sharing class PRM_ServiceBase {
    protected Map<String, Object> response;
    public abstract Map<String, Object> execute(Map<String, Object> params);
}
```

- **Tests:** a concrete service implements `execute()`; returns a `Map<String,Object>`; behaves per the §8 (EPIC E) service definition of done.

---

## B3 · `PRM_OrchestratorBase` — *0.5 d*

- **Purpose:** minimal abstract base + entry-point contract for every form orchestrator.
- **Entry:** `public abstract Map<String,Object> run(Map<String,Object> params)` — each concrete orchestrator implements `run()` and owns its savepoint / try-catch (validation vs error) / rollback.
  - `params` = the inbound request (business payload + control/context: `action`, `correlationId` / caseManagerId, flags).
  - returns the response `Map<String,Object>` OmniStudio serializes (`success`, `PractitionerScreenRecordIds`, `FeatureConfigSetting`, `AsyncJobId?`, or error shape).
- **Transport:** OmniStudio binds via a thin `Callable.call(action, args)` adapter that passes `args` to `run()`.

```apex
public abstract with sharing class PRM_OrchestratorBase {
    protected Map<String, Object> response;
    public abstract Map<String, Object> run(Map<String, Object> params);
}
```

- **Tests:** a throwaway subclass proves its `run()` opens a savepoint and an injected exception triggers `Database.rollback` (zero records) + a structured error response.

> **Note:** parent TDD/plan still describe the orchestrator entry as `execute(Map)`; reconcile them to `run(Map<String,Object>)` when you're ready (this update is scoped to Epic B only).

---

## B4 · Build order, dependencies & effort

```
B1 PRM_FormSubUtility   ·   B2 PRM_ServiceBase   ·   B3 PRM_OrchestratorBase
```

- B1/B2/B3 are independent of each other and of EPIC A. (Typed payload model → EPIC F.)


| Task                      | Est (d) |
| ------------------------- | ------- |
| B1 `PRM_FormSubUtility`   | 1.0     |
| B2 `PRM_ServiceBase`      | 0.5     |
| B3 `PRM_OrchestratorBase` | 0.5     |
| **EPIC B total**          | **2.0** |


> The typed payload model (formerly B4, 3.0 d) is delivered in **EPIC F — Orchestration**.

---

---

## B6 · Open items


| Ref                          | Item                                                                                                                               | Action / Owner                                                                                            |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Removed base classes (CL-13) | `PRM_ExceptionLogger`, `PRM_ValidationException`, `PRM_PayloadValidator`, `PRM_RecordTypes` removed from B but referenced by C/E/F | Decide their home: reuse existing org class vs relocate to the consuming epic — Platform Arch / Tech Lead |
| Practitioner RT (deferred)   | wherever `PRM_RecordTypes` lands, the "Practitioner" Account RT dev name is still `TODO_CONFIRM`                                   | Confirm RT before EPIC E (`PRM_PractitionerService`) — Tech Lead                                          |
| Payload shape                | Exact OmniScript JSON keys + `practitionerCreationType` literals per sub-DTO                                                       | Extract from OmniScript / `PRM_Service_JSON_Contracts.md` — Eng                                           |
| Logger correlation           | `PRM_CorrelationID__c` source (case Id vs async job Id)                                                                            | Confirm during EPIC C wiring — Eng                                                                        |


