# E06 · `PRM_EducationService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan is **self‑contained for component generation** — it specifies and includes **every artifact** needed to build E06 (see **§0 Component inventory**): the Apex class + `.cls-meta.xml` (**Appendix A**), the `PersonEducation.PRM_RecordKey__c` field metadata (**Appendix B**), the `PRM_AsyncJob_Access` permission‑set FLS (**Appendix C**), the Apex test class + meta (**Appendix D**), and deploy/validation steps (**Appendix E**). *(Metadata appendices included for parity with E05/E08; say the word to drop them if you want code‑only.)* **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered — **especially the dedupe grain (OQ‑E6‑2) and degree/institution Id resolution (OQ‑E6‑5)** — and the target org (OQ‑E6‑1) is confirmed.
>
> **Source of truth:** `E06_PRM_EducationService.md` (design §1–§9, incl. org‑validation, CL‑E3, NPI‑anchored idempotency). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved **[OPEN]** item are **⛔ Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PersonEducation.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/PersonEducation/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E06‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_EducationService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_EducationService.cls` (+ meta) | **NEW** | Appendix A |
| 4 | `PRM_EducationServiceTest` | Apex test class | `force-app/main/default/classes/PRM_EducationServiceTest.cls` (+ meta) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |
| 6 | Degree/Institution Id resolver | Apex selector (name→Id) | `force-app/main/default/classes/PRM_DegreeInstitutionSelector.cls` (+ meta) | **CONDITIONAL** — only if source sends names (OQ‑E6‑5) | §5 |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test`):** `PRM_` prefix; `with sharing`; bulkified (no SOQL/DML in loops, one bulk DML per object); CRUD/FLS via **`WITH USER_MODE`**; **API version 66.0**; test class `PRM_EducationServiceTest` reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class; bulk path tested at **251+**. **Error handling at the batch level** — the service lets exceptions propagate; the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain, so the service has **no inline try/catch**.

---

## 1. Confirmed requirements (from `E06_PRM_EducationService.md`)

- **[CONFIRMED]** `PRM_EducationService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1), after E2** (needs E2's `HealthcareProvider` Id). **Writes:** `PersonEducation`. (Design §1, §4.)
- **[CONFIRMED]** **Gated** — only practitioners with a **non‑empty `education[]`**. **DELEGATED branch only.** (Design §1.)
- **[CONFIRMED]** **Depends on E2** (same batch) for `healthcareProviderId`; needs E1's Account/PersonContact/Case Manager. (Design §1, §4.1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk, each `{ practitionerInfo (id, npi), education[] }`, plus `params.flow`; build all rows, then **one bulk DML**. (Design §4, §5.)
- **[CONFIRMED]** **Correlation:** `practitionerInfo.id` = Account Id → `practitionerId` (`PersonContactId`) via one bulk Account query; `healthcareProviderId` from E2 (resolve by NPI — E2 stamps `HealthcareProvider.PRM_RecordKey__c = npi`); `caseManagerId` from the `PRM_AsyncJobRecords__c` row (batch‑injected), not the mutable Account back‑link. (Design §4.1.)
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — E02 §8 CL‑E2): `upsert` `PersonEducation` by **`PRM_RecordKey__c`**; **provisional** key = `{npi}_{degreeId}_{institutionId}_{educationLevel}` (delimiter `_`, blanks normalized). **Grain provisional — OQ‑E6‑2.** (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E06‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`PersonEducation`** + Read+Edit FLS on `PRM_AsyncJob_Access`. **The field does not exist yet — creating it is a required E06 deliverable (Phase 1, T1.1).** (Design §3.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV01):** `ContactId`←practitionerId, `HealthcareProviderId`←healthcareProviderId, `Name`←`practitionerDegree`, `PRM_Degree__c`←`degreeId` (lookup), `PRM_Institution__c`←`institutionId` (lookup), `EducationLevel`←`educationLevel`, `PRM_StartDate__c`/`PRM_EndDate__c`←`educationStartDate`/`educationEndDate`, `PRM_Completed__c`←`educationCompleted ? 'Yes' : 'No'`, `PRM_Primary__c`←`primaryPersonEdu` (toBool), `PRM_CaseManager__c`←caseManagerId, `PRM_RecordKey__c` (computed). (Design §6.)
- **[CONFIRMED]** **Org‑validated field facts (CL‑E3):** `Name` **required**; `PRM_Degree__c`/`PRM_Institution__c` are **lookups** (→ `PRM_Degree__c`/`PRM_Institution__c` objects); `PRM_Completed__c` is a **picklist `Yes`/`No`** (single field — no separate `_picklist`); `PRM_Primary__c` is a **required boolean**; **`EducationLevel` is a picklist** (see §org‑note). (Design §2, §6 + this plan's org check.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** of `PersonEducation[]` by `PRM_RecordKey__c`; gated; returns `personEducationIds` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, personEducationIds }`. (Design §4.)
- **[CONFIRMED]** **Governor:** ~2 SOQL (Account + HealthcareProvider) + 1 bulk DML; no DML/SOQL in loops. (Design §4.2.)
- **[CONFIRMED]** **Effort:** ~0.5 engineer‑day. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility`), **E1** (Account/Contact/CaseManager + `PRM_AsyncJobRecords__c`), **E2** (HealthcareProvider), the **`PractitionerBatch`** wiring, and E06's own `PRM_RecordKey__c` field + FLS. **(Conditional)** a degree/institution name→Id resolver if the source sends names (OQ‑E6‑5).

> **🔎 Org validation (IBXDEV01, 2026‑06‑29):**
> - `ContactId` → Contact (nullable); `HealthcareProviderId` → HealthcareProvider (nullable); `PRM_CaseManager__c` → IndividualApplication (nullable).
> - `Name` **required** (Text 255). `PRM_Primary__c` **required boolean**. `PRM_StartDate__c`/`PRM_EndDate__c` date (nullable).
> - `PRM_Completed__c` **picklist** = `Yes` / `No` (nullable). `PRM_Degree__c` → **`PRM_Degree__c`** lookup; `PRM_Institution__c` → **`PRM_Institution__c`** lookup.
> - **⚠ `EducationLevel` is a picklist** (nullable) — values: `Additional Years, Chiropractic School, Dental School, Fellowship, Graduate, Internship, Medical School, Optometry School, Podiatry School, Post Doctoral, Postgraduate, Preceptorship, Professional School, Residency, Sleep Medicine Program, Training, Undergraduate`. Inbound `educationLevel` must be an **active picklist value** (OQ‑E6‑6).
> - `PRM_ExternalId__c` exists (Text 255, **not unique**) — not reused; new `PRM_RecordKey__c` (Unique) per design §3.

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL in loops; ≤ 2 bulk queries (Account + HealthcareProvider) + one bulk `upsert`.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch**. (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch user via `PRM_AsyncJob_Access`) — `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E6‑8).
- **[CONFIRMED]** **Required field gates the insert:** `Name` (← `practitionerDegree`) must be set; `PRM_Primary__c` defaulted via `toBool`.
- **[CONFIRMED]** **Gated:** practitioners with empty `education[]` are skipped (no rows, not in the response).
- **[OPEN]** `education[].degreeId` / `institutionId` must be **`PRM_Degree__c` / `PRM_Institution__c` record Ids**. If the source sends **names** (the `JSON structure.json` sample sends `institution`/`degree` *names*), a resolver step is required (OQ‑E6‑5).
- **[OPEN]** `educationLevel` must be a valid **picklist** value (OQ‑E6‑6).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds `PersonEducation[]` per the §6 map; **one bulk DML** regardless of chunk size.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running on the same chunk produces **no duplicates** (contingent on the confirmed grain — OQ‑E6‑2).
- **[CONFIRMED]** `practitionerId` + `healthcareProviderId` resolved in bulk; `caseManagerId` from the job record.
- **[CONFIRMED]** `PRM_Completed__c` = `Yes`/`No`; `PRM_Primary__c` defaulted; `EducationLevel` set from a valid picklist value.
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, personEducationIds }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners × multiple education rows), (b) a **re‑run/idempotency** test, and (c) a **required‑field negative** (blank `practitionerDegree` → `DmlException`); Test Evidence Report + human sign‑off (Epic A §A7).
- **[CONFIRMED]** Field API names/types validated against the org (done — re‑confirm on the target org, OQ‑E6‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E6‑1…OQ‑E6‑8)
- **T0.1 — Target org** (OQ‑E6‑1). Completion: org confirmed.
- **T0.2 — Resolve the dedupe grain** (OQ‑E6‑2): is `npi_degreeId_institutionId_educationLevel` unique per practitioner, or can renewals/dates legitimately repeat it? Validation: business sign‑off (org data is test‑polluted). Completion: grain confirmed → Appendix A `key(...)` finalized.
- **T0.3 — Resolve degree/institution Id source** (OQ‑E6‑5): does the payload send **`PRM_Degree__c`/`PRM_Institution__c` record Ids** (no resolver) or **names** (needs `PRM_DegreeInstitutionSelector`, +1–2 SOQL)? Completion: shape confirmed → component #6 built or not.
- **T0.4 — Verify dependencies present on `main`:** `PRM_ServiceBase`; `PRM_FormSubUtility`; E1; E2 (HealthcareProvider with `PRM_RecordKey__c = npi`); the permission set `PRM_AsyncJob_Access`. *(E06's `PRM_RecordKey__c` on `PersonEducation` is **NOT pre‑existing** — created in Phase 1.)* Completion: all present (or gaps logged).
- **T0.5 — Resolve open data items:** `EducationLevel` picklist values (OQ‑E6‑6), `Name`/`practitionerDegree` presence (OQ‑E6‑7), no‑NPI policy (OQ‑E6‑8), `healthcareProviderId` resolution path (OQ‑E6‑4), `caseManagerId` wiring (OQ‑E6‑3). Completion: each decided or deferred.

### Phase 1 — E06 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `PersonEducation`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (Appendices B–C). **Confirmed: the field does not exist yet.**
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS deployed.
  - Dependencies: T0.1. Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing data (field new/empty → low). Completion: field + FLS deployed.

### Phase 2 — `PRM_EducationService` core *(M2)*
- **T2.1 — Class + `execute` + `PractUow`; parse + gate + bulk resolution**
  - Purpose: parse `practitioners[]`; keep only gated (non‑empty `education`); resolve `practitionerId` (Account query) + `healthcareProviderId` (HCP by NPI); read `caseManagerId` (batch‑injected — OQ‑E6‑3).
  - Outcome: Appendix A steps 1–2. Impacted: `classes/PRM_EducationService.cls` (+ test).
  - Validation: compiles; gating correct; resolution batched. Testing: unit (parse + gate + resolution). Risks: **[RISK]** HCP resolution path (OQ‑E6‑4); `caseManagerId` wiring (OQ‑E6‑3). Completion: parse + resolution green.
- **T2.2 — (Conditional) degree/institution name→Id resolution** (OQ‑E6‑5)
  - Purpose: if the payload sends names, bulk‑resolve `PRM_Degree__c`/`PRM_Institution__c` Ids via `PRM_DegreeInstitutionSelector` (`WITH USER_MODE`). Outcome: code→Id maps; or **skipped** if Ids are sent. Risks: **[RISK]** unknown payload shape. Completion: path decided + implemented (or confirmed not needed).
- **T2.3 — `buildEducation` + `PRM_Completed__c`/`PRM_Primary__c` + `PRM_RecordKey__c`**
  - Purpose: in‑memory `PersonEducation` per §6; `PRM_Completed__c` = Yes/No; `PRM_Primary__c` via toBool; `EducationLevel` (valid picklist); NPI‑anchored key.
  - Dependencies: T2.1, T0.2 (grain), T0.3 (Ids). Validation: field‑by‑field unit assertions; key string correct. Testing: builder unit (completed Y/N; blank dates; picklist level). Risks: **[RISK]** grain (OQ‑E6‑2); `Name` blank (OQ‑E6‑7); EducationLevel value (OQ‑E6‑6). Completion: builder unit‑tested.
- **T2.4 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; per‑practitioner response (gated subset, input order).
  - Dependencies: T2.3. Validation: rows have correct FKs + key; DML count = 1. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildEducation` (completed Y/N, primary, dates, EducationLevel, key), `key` (blank normalization), gating.
- **T3.2 Bulk/governor:** 251+ practitioners × multiple education rows → ≤2 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → row count unchanged.
- **T3.4 Negative/edge:** empty `education` (skipped), **blank `practitionerDegree` → `DmlException`** (Name required, OQ‑E6‑7), invalid `EducationLevel` (OQ‑E6‑6), missing HCP (unresolved NPI), no‑NPI (OQ‑E6‑8).
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `PersonEducation` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E6‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/education-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. Commit prefix `[E6]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RISK] Degree/Institution Id resolution (OQ‑E6‑5).** `PRM_Degree__c`/`PRM_Institution__c` are **lookups**, so `education[].degreeId`/`institutionId` must be **record Ids**. The `JSON structure.json` sample sends `institution`/`degree` as **names** — so a resolver (`PRM_DegreeInstitutionSelector`, component #6) or intake normalization is required, **and** the dedupe key uses `degreeId`/`institutionId` → the key can't be built until these are Ids. Confirm the payload shape **before** building.
- **[RISK] Dedupe grain (OQ‑E6‑2).** Org data is test‑polluted (same triple repeats 15×). The provisional `npi_degreeId_institutionId_educationLevel` assumes a degree+institution+level can't legitimately repeat; confirm with business (renewals/dates).
- **[RISK] `EducationLevel` picklist (OQ‑E6‑6).** It's a restricted picklist — an inbound value not in the active set throws on `upsert`. Validate at intake (map source → picklist) rather than letting the DML fail.
- **[RECOMMENDATION] `healthcareProviderId` resolution (OQ‑E6‑4).** Resolve HCP by **`PRM_RecordKey__c = npi`** (E2's stamp, unique) rather than by `AccountId` (an Account can have multiple HCPs in polluted data). Or have `PractitionerBatch` pass E2's per‑practitioner `healthcareProviderId` in‑memory (E20 §9 / OQ‑E2‑9) — cleaner, no query.
- **[RECOMMENDATION] `caseManagerId` wiring (OQ‑E6‑3).** Batch injects a resolved `caseManagerId` per practitioner node (from `PRM_AsyncJobRecords__c`); the §5 payload doesn't carry it today.
- **[RECOMMENDATION] `Name` (required) at intake (OQ‑E6‑7).** `Name ← practitionerDegree` — a blank fails the whole chunk; validate/normalize at intake or define a fallback.
- **[RECOMMENDATION] Explicit date parsing.** `Date.parse` is locale‑dependent; if the format is fixed, parse explicitly (single‑owner `PRM_FormSubUtility`).

---

## 6. Gaps & hidden dependencies

- **Degree/Institution Id source (OQ‑E6‑5)** — names vs Ids; gates the resolver (#6) + the key.
- **Dedupe grain (OQ‑E6‑2)** — gates the key + idempotency test.
- **`EducationLevel` picklist (OQ‑E6‑6)** — inbound values must be active entries.
- **Target org (OQ‑E6‑1)**; **E06 `PRM_RecordKey__c` + FLS** — not yet created → Phase 1.
- **E2 dependency** — HealthcareProvider with `PRM_RecordKey__c = npi` (or in‑memory output).
- **`caseManagerId` wiring (OQ‑E6‑3)**; **`Name` presence (OQ‑E6‑7)**; **no‑NPI (OQ‑E6‑8)**.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E6‑1 — Target org** for deploy/test.
- **OQ‑E6‑2 — Education dedupe grain.** `npi_degreeId_institutionId_educationLevel` only, or `+ dates` (renewals)? **Gates the key + Appendix A `key(...)`.**
- **OQ‑E6‑3 — `caseManagerId` source/wiring.** Confirm `PractitionerBatch` injects a resolved `caseManagerId` per practitioner node.
- **OQ‑E6‑4 — `healthcareProviderId` resolution.** By `PRM_RecordKey__c = npi` (recommended), by `AccountId`, or passed in‑memory from E2?
- **OQ‑E6‑5 — Degree/Institution Ids vs names.** Does the payload send `PRM_Degree__c`/`PRM_Institution__c` **record Ids** (no resolver) or **names** (needs `PRM_DegreeInstitutionSelector`)? *(Sample JSON sends names.)*
- **OQ‑E6‑6 — `EducationLevel` picklist values.** Confirm inbound `educationLevel` maps to active picklist entries (e.g. `Medical School`, `Residency`, …).
- **OQ‑E6‑7 — `Name` (`practitionerDegree`) always present?** Required field — confirm intake guarantees it, or define a fallback.
- **OQ‑E6‑8 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key.

*(Already resolved: org validation done — fields/types confirmed; CL‑E3 (single `PRM_Completed__c` picklist); new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E06's `PRM_RecordKey__c` is NOT yet created → built as E06 Phase 1**.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | Degree/Institution sent as **names**, not Ids → wrong FKs / unbuildable key | Medium | High | OQ‑E6‑5 before build; conditional `PRM_DegreeInstitutionSelector` (#6) |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | Dedupe grain wrong (renewals collapse) | Low–Med | Medium | OQ‑E6‑2 business decision; only `key(...)` changes |
| R‑4 | `EducationLevel` value not in picklist → chunk insert fails | Medium | Medium | OQ‑E6‑6; validate/map at intake; T3.4 |
| R‑5 | `Name`/`practitionerDegree` blank → chunk insert fails | Medium | Medium | OQ‑E6‑7; intake validation; T3.4 |
| R‑6 | HCP not resolvable by NPI (E2 not run / stamp missing) | Low–Med | Medium | OQ‑E6‑4; run after E2; resolve by `PRM_RecordKey__c=npi` |
| R‑7 | `caseManagerId` wiring (mutable Account vs job record) | Medium | High | OQ‑E6‑3; batch injects from `PRM_AsyncJobRecords__c` |
| R‑8 | No target org → can't deploy/test | Medium | High | OQ‑E6‑1 |
| R‑9 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner coordination |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. OQ‑E6‑2 grain + OQ‑E6‑5 Id source) → 1 (**create the field + FLS**) → 2 (service; + conditional resolver) → 3 → 4 → 5. Runs **after E2** in `PractitionerBatch`.
- **Effort:** within the ~0.5 d catalog estimate — class + builder + key ~0.25 · conditional resolver ~0.15 (if needed) · tests ~0.2 · evidence/VCS folded in.
- **Depends on:** Epic A + Epic B + E1 + **E2** on `main`, plus `PractitionerBatch`. **Feeds:** nothing downstream consumes E6 (PersonEducation is a leaf).

---

## 10. What happens after sign‑off

Resolve OQ‑E6‑1…OQ‑E6‑8 — **the grain (OQ‑E6‑2) and the degree/institution Id source (OQ‑E6‑5) are the gates**. Then: **create + deploy the E06 `PRM_RecordKey__c` field + FLS (Phase 1)** → build the service per **Appendix A** (parse + gate → resolve Contact/HCP → optional name→Id resolution → build + key → one bulk `upsert` → response) → tests → Test Evidence Report → human sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E6‑1), the grain (OQ‑E6‑2), and the Id source (OQ‑E6‑5) are confirmed.**

---

## Appendix A — Apex class `PRM_EducationService` (+ meta)

> Full `PRM_EducationService` (expands `E06_PRM_EducationService.md` §4.2). **Depends on** `PRM_ServiceBase`. **Provisional:** the `key(...)` reflects the current grain — finalize after OQ‑E6‑2. Assumes `education[].degreeId`/`institutionId` are **record Ids** (OQ‑E6‑5); the name→Id branch would use a `PRM_DegreeInstitutionSelector`. `caseManagerId` is read from the batch‑injected per‑practitioner node (OQ‑E6‑3); HCP resolved by `PRM_RecordKey__c = npi` (OQ‑E6‑4).

```apex
public with sharing class PRM_EducationService extends PRM_ServiceBase {

    // one per GATED practitioner (non-empty education), in input order
    @TestVisible
    private class PractUow {
        Map<String, Object> p;          // practitionerInfo (id, npi)
        List<Object> education;         // education[]
        Id accountId;                   // = practitionerInfo.id (E1)
        Id caseManagerId;               // from PRM_AsyncJobRecords__c (batch context) — OQ-E6-3
        Id practitionerId;              // PersonContactId (resolved)
        Id healthcareProviderId;        // from E2 (resolved by NPI) — OQ-E6-4
        List<PersonEducation> rows = new List<PersonEducation>();
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');                        // DELEGATED (context)
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) build UoWs ONLY for gated practitioners (no DML/SOQL in loop)
        List<PractUow> uows = new List<PractUow>();
        Set<Id> accountIds = new Set<Id>();
        Set<String> npis = new Set<String>();
        if (practitioners != null) {
            for (Object o : practitioners) {
                Map<String, Object> app = (Map<String, Object>) o;
                List<Object> edu = (List<Object>) app.get('education');
                if (edu == null || edu.isEmpty()) continue;               // GATED: skip
                PractUow u = new PractUow();
                u.p             = (Map<String, Object>) app.get('practitionerInfo');
                u.education     = edu;
                u.accountId     = (Id) u.p.get('id');
                u.caseManagerId = (Id) app.get('caseManagerId');          // batch-injected (OQ-E6-3)
                accountIds.add(u.accountId);
                if (u.p.get('npi') != null) npis.add((String) u.p.get('npi'));
                uows.add(u);
            }
        }
        if (uows.isEmpty()) {
            response = new Map<String, Object>{ 'practitioners' => new List<Object>() };
            return response;
        }

        // 2) bulk resolve: Account -> PersonContactId; HealthcareProvider by NPI (E2 stamp) -> hcpId
        Map<Id, Account> accById = new Map<Id, Account>(
            [SELECT Id, PersonContactId FROM Account WHERE Id IN :accountIds WITH USER_MODE]);
        Map<String, Id> hcpByNpi = new Map<String, Id>();
        for (HealthcareProvider h : [
                SELECT Id, PRM_RecordKey__c FROM HealthcareProvider
                WHERE PRM_RecordKey__c IN :npis WITH USER_MODE]) {
            hcpByNpi.put(h.PRM_RecordKey__c, h.Id);                       // PRM_RecordKey__c = npi (E2)
        }
        // (OQ-E6-5) if education[].degreeId/institutionId are NAMES, resolve to Ids here via a selector.

        // 3) build PersonEducation rows; key per §2 (provisional grain — OQ-E6-2)
        List<PersonEducation> allRows = new List<PersonEducation>();
        for (PractUow u : uows) {
            Account a = accById.get(u.accountId);
            u.practitionerId      = (a != null) ? a.PersonContactId : null;
            String npi            = (String) u.p.get('npi');
            u.healthcareProviderId = hcpByNpi.get(npi);
            for (Object eo : u.education) {
                PersonEducation pe = buildEducation(u, (Map<String, Object>) eo, npi);
                u.rows.add(pe);
                allRows.add(pe);
            }
        }

        // 4) ONE bulk upsert by the External Id (idempotent — §7)
        upsert allRows PRM_RecordKey__c;

        // 5) response (input order; gated subset)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (PractUow u : uows) {
            List<Id> ids = new List<Id>();
            for (PersonEducation pe : u.rows) ids.add(pe.Id);
            results.add(new Map<String, Object>{
                'accountId'          => u.accountId,
                'personEducationIds' => ids
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── builder (pure in-memory; field map per §6) ──
    private PersonEducation buildEducation(PractUow u, Map<String, Object> e, String npi) {
        String degreeId       = (String) e.get('degreeId');         // PRM_Degree__c Id (OQ-E6-5)
        String institutionId  = (String) e.get('institutionId');    // PRM_Institution__c Id (OQ-E6-5)
        String educationLevel = (String) e.get('educationLevel');   // picklist value (OQ-E6-6)

        PersonEducation pe = new PersonEducation();
        pe.ContactId            = u.practitionerId;
        pe.HealthcareProviderId = u.healthcareProviderId;
        pe.Name                 = (String) e.get('practitionerDegree');   // REQUIRED (OQ-E6-7)
        if (String.isNotBlank(degreeId))      pe.PRM_Degree__c      = (Id) degreeId;       // lookup
        if (String.isNotBlank(institutionId)) pe.PRM_Institution__c = (Id) institutionId;  // lookup
        pe.EducationLevel       = educationLevel;                          // picklist (OQ-E6-6)
        pe.PRM_StartDate__c     = parseDate((String) e.get('educationStartDate'));
        pe.PRM_EndDate__c       = parseDate((String) e.get('educationEndDate'));
        pe.PRM_Completed__c     = toBool(e.get('educationCompleted')) ? 'Yes' : 'No';  // picklist (CL-E3)
        pe.PRM_Primary__c       = toBool(e.get('primaryPersonEdu'));       // required boolean
        pe.PRM_CaseManager__c   = u.caseManagerId;
        pe.PRM_RecordKey__c     = key(new List<String>{ npi, degreeId, institutionId, educationLevel });
        return pe;
    }

    // ── helpers ──
    private String key(List<String> parts) {
        List<String> safe = new List<String>();
        for (String s : parts) safe.add(s == null ? '' : s);   // normalize blanks
        return String.join(safe, '_');                          // '_' delimiter (§2)
    }
    private Boolean toBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date parseDate(String s) { return String.isBlank(s) ? null : Date.parse(s); }   // ⚠ locale — confirm format
}
```

**`PRM_EducationService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E06_PRM_EducationService.md`. Open items (OQ‑E6‑1…OQ‑E6‑8) above still apply — **especially OQ‑E6‑2 (grain) and OQ‑E6‑5 (Id source).**

---

## Appendix B — Field metadata `PersonEducation.PRM_RecordKey__c`

> **NEW (E06‑owned).** Path: `force-app/main/default/objects/PersonEducation/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_RecordKey__c</fullName>
    <label>Record Key</label>
    <type>Text</type>
    <length>255</length>
    <externalId>true</externalId>
    <unique>true</unique>
    <caseSensitive>false</caseSensitive>
    <required>false</required>
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E06 — PersonEducation). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

> ⚠ If **OQ‑E6‑2** changes the grain, the **field shape is unchanged** — only the value composed in `key(...)` (Appendix A) changes.

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`.

```xml
<fieldPermissions>
    <field>PersonEducation.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_EducationServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`**, modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, re‑run/idempotency. ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`, `createHealthcareProvidersByNpi`, `createDegree`, `createInstitution`). The blank‑Name negative is **contingent on OQ‑E6‑7**; `EducationLevel` uses a confirmed picklist value (OQ‑E6‑6).

```apex
@isTest
private class PRM_EducationServiceTest {

    private static final Integer BULK = 251;
    private static final String LEVEL = 'Medical School';   // valid EducationLevel picklist value (OQ-E6-6)

    // ⚠ Confirm/add these builders in PRM_TestDataFactory (do NOT inline data here):
    //   createPractitionersWithCaseManagers(count, doInsert) -> Person Accounts + a Case Manager each
    //   caseManagerByAccount(List<Account>) -> Map<AccountId, CaseManagerId>
    //   createHealthcareProvidersByNpi(Map<AccountId,npi>, doInsert) -> HCP per account w/ PRM_RecordKey__c=npi
    //   createDegree(doInsert) / createInstitution(doInsert) -> PRM_Degree__c / PRM_Institution__c
    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);
        PRM_TestDataFactory.createDegree(true);
        PRM_TestDataFactory.createInstitution(true);
    }

    private static Map<String, Object> buildParams(
            List<Account> accts, Map<Id, Id> cm, Map<Id, String> npiByAcct,
            Id degreeId, Id institutionId, Integer eduPer, String degreeName) {
        List<Object> practitioners = new List<Object>();
        for (Account a : accts) {
            List<Object> edu = new List<Object>();
            for (Integer i = 0; i < eduPer; i++) {
                edu.add(new Map<String, Object>{
                    'practitionerDegree' => degreeName,
                    'degreeId'           => degreeId,
                    'institutionId'      => institutionId,
                    'educationLevel'     => LEVEL,
                    'educationStartDate' => '08/01/2000',
                    'educationEndDate'   => '05/18/2004',
                    'educationCompleted' => true,
                    'primaryPersonEdu'   => (i == 0)
                });
            }
            practitioners.add(new Map<String, Object>{
                'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => npiByAcct.get(a.Id) },
                'education'        => edu,
                'caseManagerId'    => cm.get(a.Id)
            });
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    @isTest
    static void shouldCreateOneRowPerEducation_WhenBulk() {
        // Given
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<Id, String> npiByAcct = new Map<Id, String>();
        Integer n = 0; for (Account a : accts) npiByAcct.put(a.Id, '20000000' + n++);
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npiByAcct, true);   // HCP.PRM_RecordKey__c = npi
        Id deg = [SELECT Id FROM PRM_Degree__c LIMIT 1].Id;
        Id inst = [SELECT Id FROM PRM_Institution__c LIMIT 1].Id;
        Map<String, Object> params = buildParams(accts, cm, npiByAcct, deg, inst, 2, 'MD');

        // When
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_EducationService().execute(params);
        Test.stopTest();

        // Then
        Assert.areEqual(BULK * 2, [SELECT COUNT() FROM PersonEducation],
            'Two education rows per practitioner should be created');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(),
            'Response should carry one entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<Id, String> npiByAcct = new Map<Id, String>();
        Integer n = 0; for (Account a : accts) npiByAcct.put(a.Id, '20000000' + n++);
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npiByAcct, true);
        Id deg = [SELECT Id FROM PRM_Degree__c LIMIT 1].Id;
        Id inst = [SELECT Id FROM PRM_Institution__c LIMIT 1].Id;
        Map<String, Object> params = buildParams(accts, cm, npiByAcct, deg, inst, 1, 'MD');

        Test.startTest();
        new PRM_EducationService().execute(params);   // first run
        new PRM_EducationService().execute(params);   // re-run (idempotent)
        Test.stopTest();

        Assert.areEqual(BULK, [SELECT COUNT() FROM PersonEducation],
            'Re-running with the same key must upsert, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoEducation() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Delegated',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '2999999999' },
                    'education' => new List<Object>()      // empty -> gated out
                }
            }
        };

        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_EducationService().execute(params);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM PersonEducation], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(),
            'Response should exclude gated-out practitioners');
    }

    @isTest
    static void shouldSetCompletedAndKey_WhenBuilt() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<Id, String> npiByAcct = new Map<Id, String>{ a.Id => '2111111111' };
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npiByAcct, true);
        Id deg = [SELECT Id FROM PRM_Degree__c LIMIT 1].Id;
        Id inst = [SELECT Id FROM PRM_Institution__c LIMIT 1].Id;
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, npiByAcct, deg, inst, 1, 'MD');

        Test.startTest();
        new PRM_EducationService().execute(params);
        Test.stopTest();

        PersonEducation pe = [
            SELECT PRM_Completed__c, PRM_Primary__c, EducationLevel, PRM_RecordKey__c, HealthcareProviderId
            FROM PersonEducation LIMIT 1
        ];
        Assert.areEqual('Yes', pe.PRM_Completed__c, 'PRM_Completed__c should be Yes for educationCompleted=true');
        Assert.areEqual(LEVEL, pe.EducationLevel, 'EducationLevel should be the mapped picklist value');
        Assert.isNotNull(pe.HealthcareProviderId, 'HCP should be resolved by NPI');
        Assert.isTrue(pe.PRM_RecordKey__c.contains('_'), 'Key should be underscore-joined');
    }

    // Name is required (org) -> blank practitionerDegree must fail the insert (OQ-E6-7).
    @isTest
    static void shouldThrow_WhenDegreeNameBlank() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<Id, String> npiByAcct = new Map<Id, String>{ a.Id => '2122222222' };
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npiByAcct, true);
        Id deg = [SELECT Id FROM PRM_Degree__c LIMIT 1].Id;
        Id inst = [SELECT Id FROM PRM_Institution__c LIMIT 1].Id;
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, npiByAcct, deg, inst, 1, '');  // blank name

        Test.startTest();
        try {
            new PRM_EducationService().execute(params);
            Assert.fail('Expected a DmlException for the required Name (blank practitionerDegree)');
        } catch (DmlException e) {
            Assert.isTrue(e.getMessage().length() > 0, 'DmlException should be raised for the missing required field');
        }
        Test.stopTest();
    }
}
```

**`PRM_EducationServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ × 2 education → governor‑safe), re‑run idempotency, gating (empty `education`), field/key correctness (`PRM_Completed__c`, `EducationLevel`, HCP resolution, key), required‑field negative (blank `practitionerDegree`). Add an invalid‑`EducationLevel` negative once OQ‑E6‑6 is set, and a name→Id resolution test if OQ‑E6‑5 = names. Coverage ≥ 85%.

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E6‑1). **Field + FLS first**, then classes, then tests.

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/PersonEducation/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service (+ conditional selector) + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_EducationService.cls" \
  -d "force-app/main/default/classes/PRM_EducationServiceTest.cls" \
  -o <alias>
#   (+ PRM_DegreeInstitutionSelector.cls only if OQ-E6-5 = names)

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_EducationServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check
sf data query -o <alias> \
  -q "SELECT Id, ContactId, HealthcareProviderId, EducationLevel, PRM_Completed__c, PRM_RecordKey__c FROM PersonEducation ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E6‑2 (grain) decided → `key(...)` finalized; OQ‑E6‑5 (Id source) decided → resolver built or not.
- [ ] OQ‑E6‑6 (`EducationLevel` values) + OQ‑E6‑7 (`Name` presence) confirmed.
- [ ] Target org confirmed (OQ‑E6‑1); `caseManagerId` wiring (OQ‑E6‑3) + HCP resolution (OQ‑E6‑4) confirmed.
- [ ] `PRM_TestDataFactory` builders exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_EducationService` compiles; `upsert … PRM_RecordKey__c` resolves; runs after E2.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
