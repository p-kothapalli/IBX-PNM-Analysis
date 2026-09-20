# E07 · `PRM_BoardCertificationService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan is **self‑contained for component generation** — it specifies and includes **every artifact** needed to build E07 (see **§0 Component inventory**): the Apex class + `.cls-meta.xml` (**Appendix A**), the `BoardCertification.PRM_RecordKey__c` field metadata (**Appendix B**), the `PRM_AsyncJob_Access` permission‑set FLS (**Appendix C**), the Apex test class + meta (**Appendix D**), and deploy/validation steps (**Appendix E**). *(Metadata appendices included for parity with E05/E06/E08; say the word to drop them for code‑only.)* **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered — **especially the dedupe grain (OQ‑E7‑2) and the two required fields `Name`/`PRM_EffectiveFrom__c` (OQ‑E7‑6/7)** — and the target org (OQ‑E7‑1) is confirmed.
>
> **Source of truth:** `E07_PRM_BoardCertificationService.md` (design §1–§9, incl. org‑validation + NPI‑anchored idempotency). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved **[OPEN]** item are **⛔ Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `BoardCertification.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/BoardCertification/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E07‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_BoardCertificationService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_BoardCertificationService.cls` (+ meta) | **NEW** | Appendix A |
| 4 | `PRM_BoardCertificationServiceTest` | Apex test class | `force-app/main/default/classes/PRM_BoardCertificationServiceTest.cls` (+ meta) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test`):** `PRM_` prefix; `with sharing`; bulkified (no SOQL/DML in loops, one bulk DML per object); CRUD/FLS via **`WITH USER_MODE`**; **API version 66.0**; test class `PRM_BoardCertificationServiceTest` reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class; bulk path tested at **251+**. **Error handling at the batch level** — the service lets exceptions propagate; the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain, so the service has **no inline try/catch**.

---

## 1. Confirmed requirements (from `E07_PRM_BoardCertificationService.md`)

- **[CONFIRMED]** `PRM_BoardCertificationService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1), after E2** (needs E2's `HealthcareProvider` Id). **Writes:** `BoardCertification`. (Design §1, §4.)
- **[CONFIRMED]** **Gated** — only practitioners with a **non‑empty `boardCertifications[]`**. **DELEGATED branch only.** (Design §1.)
- **[CONFIRMED]** **Depends on E2** (same batch) for `healthcareProviderId`; needs E1's Account/PersonContact/Case Manager. (Design §1, §4.1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk, each `{ practitionerInfo (id, npi, effectiveFrom/To), boardCertifications[] }`, plus `params.flow`; build all rows, then **one bulk DML**. (Design §4, §5.)
- **[CONFIRMED]** **Correlation:** `practitionerInfo.id` = Account Id → `practitionerId` (`PersonContactId`) via one bulk Account query; `healthcareProviderId` from E2 (resolve by NPI — E2 stamps `HealthcareProvider.PRM_RecordKey__c = npi`); `caseManagerId` from the `PRM_AsyncJobRecords__c` row (batch‑injected), not the mutable Account back‑link. (Design §4.1.)
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — E02 §8 CL‑E2): `upsert` `BoardCertification` by **`PRM_RecordKey__c`**; key = `{npi}_{boardName}_{certificationType}` (delimiter `_`, blanks normalized). **`BoardName` alone is insufficient** (org data: same practitioner+board under 2 certification types) → `certificationType` is in the key. **Grain provisional — OQ‑E7‑2.** (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E07‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`BoardCertification`** + Read+Edit FLS on `PRM_AsyncJob_Access`. **The field does not exist yet — creating it is a required E07 deliverable (Phase 1, T1.1).** *(Org: only `SourceSystemIdentifier` exists — unique but **not** External Id, so not upsertable; no `PRM_ExternalId__c`.)* (Design §3.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV01):** `AccountId`←accountId, `HealthcareProviderId`←healthcareProviderId, `PractitionerId`←practitionerId, `Name`←`boardCertificationName`, `BoardName`←`boardName`, `CertificationType`←`certificationType` (picklist), `ExpirationDate`←`boardExpires`, `PRM_BoardOriginal__c`←`boardOriginal`, `PRM_BoardReCert__c`←`boardRecret`, `PRM_EffectiveFrom__c`←`practitionerInfo.effectiveFrom`, `PRM_EffectiveTo__c`←`practitionerInfo.effectiveTo`, `PRM_CaseManager__c`←caseManagerId, `PRM_RecordKey__c` (computed). (Design §6.)
- **[CONFIRMED]** **Org‑validated field facts:** `Name` **required**; **`PRM_EffectiveFrom__c` REQUIRED** (`nillable=false`); `CertificationType` is a **picklist** (37 specialty values); `ExpirationDate`/`PRM_BoardOriginal__c`/`PRM_BoardReCert__c`/`PRM_EffectiveTo__c` are **date, nullable**; FKs to Account/HealthcareProvider/Contact(Practitioner)/IndividualApplication. (Design §2, §6 + this plan's org check.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** of `BoardCertification[]` by `PRM_RecordKey__c`; gated; returns `boardCertificationIds` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, boardCertificationIds }`. (Design §4.)
- **[CONFIRMED]** **Governor:** ~2 SOQL (Account + HealthcareProvider) + 1 bulk DML; no DML/SOQL in loops. (Design §4.2.)
- **[CONFIRMED]** **Effort:** ~0.5 engineer‑day. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility`), **E1**, **E2** (HealthcareProvider), the **`PractitionerBatch`** wiring, and E07's own `PRM_RecordKey__c` field + FLS.

> **🔎 Org validation (IBXDEV01, 2026‑06‑29):**
> - `AccountId`→Account, `HealthcareProviderId`→HealthcareProvider, `PractitionerId`→Contact (rel `Practitioner`), `PRM_CaseManager__c`→IndividualApplication — all nullable.
> - `Name` **required** (Text 255). `BoardName` Text 255 (nullable).
> - `CertificationType` **picklist** (37 active values — specialties: Internal Medicine, Allergy and Immunology, Emergency Medicine, Radiology, …). Inbound `certificationType` must be an **active value** (OQ‑E7‑5).
> - `ExpirationDate`, `PRM_BoardOriginal__c`, `PRM_BoardReCert__c`, `PRM_EffectiveTo__c` = date, nullable. **`PRM_EffectiveFrom__c` = date, REQUIRED** (`nillable=false`).
> - **No `PRM_ExternalId__c`**; `SourceSystemIdentifier` is **unique but not External Id** → not upsertable → new `PRM_RecordKey__c` (External Id, Unique) per design §3.

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL in loops; ≤ 2 bulk queries (Account + HealthcareProvider) + one bulk `upsert`.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch**. (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch user via `PRM_AsyncJob_Access`) — `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E7‑8).
- **[CONFIRMED]** **Two required fields gate the insert:** `Name` (← `boardCertificationName`) and **`PRM_EffectiveFrom__c`** (← `practitionerInfo.effectiveFrom`) must be set — a blank either fails the chunk (OQ‑E7‑6/7).
- **[CONFIRMED]** **Gated:** practitioners with empty `boardCertifications[]` are skipped (no rows, not in the response).
- **[OPEN]** `certificationType` must be a valid **picklist** value, and **non‑blank for the key** to be meaningful — a blank `certificationType` makes the key `{npi}_{boardName}_` (collapses two blank‑type certs on the same board; OQ‑E7‑2/5).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds `BoardCertification[]` per the §6 map; **one bulk DML** regardless of chunk size.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running on the same chunk produces **no duplicates** (contingent on the confirmed grain — OQ‑E7‑2).
- **[CONFIRMED]** `practitionerId` + `healthcareProviderId` resolved in bulk; `caseManagerId` from the job record.
- **[CONFIRMED]** Required fields satisfied: `Name` and `PRM_EffectiveFrom__c` set; `CertificationType` from a valid picklist value.
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, boardCertificationIds }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners × multiple certs), (b) a **re‑run/idempotency** test, and (c) **required‑field negatives** (blank `boardCertificationName`; blank `effectiveFrom` → `DmlException`); Test Evidence Report + human sign‑off (Epic A §A7).
- **[CONFIRMED]** Field API names/types validated against the org (done — re‑confirm on the target org, OQ‑E7‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E7‑1…OQ‑E7‑9)
- **T0.1 — Target org** (OQ‑E7‑1). Completion: org confirmed.
- **T0.2 — Confirm the dedupe grain** (OQ‑E7‑2): is `npi_boardName_certificationType` the right grain (incl. how blank `certificationType` is handled), or do renewals/dates legitimately repeat it? Validation: business sign‑off (data is test‑polluted). Completion: grain confirmed → Appendix A `key(...)` finalized.
- **T0.3 — Verify dependencies present on `main`:** `PRM_ServiceBase`; `PRM_FormSubUtility`; E1; E2 (HealthcareProvider with `PRM_RecordKey__c = npi`); the permission set `PRM_AsyncJob_Access`. *(E07's `PRM_RecordKey__c` is **NOT pre‑existing** — created in Phase 1.)* Completion: all present (or gaps logged).
- **T0.4 — Resolve open data items:** `CertificationType` picklist mapping (OQ‑E7‑5), `Name`/`boardCertificationName` presence (OQ‑E7‑7), `PRM_EffectiveFrom__c`/`effectiveFrom` presence (OQ‑E7‑6), date parsing (OQ‑E7‑9), no‑NPI policy (OQ‑E7‑8), `healthcareProviderId` resolution (OQ‑E7‑4), `caseManagerId` wiring (OQ‑E7‑3), `effectiveFrom`/`To` source (practitioner vs per‑cert). Completion: each decided or deferred.

### Phase 1 — E07 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `BoardCertification`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (Appendices B–C). **Confirmed: the field does not exist yet** (org has only the non‑External‑Id `SourceSystemIdentifier`).
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS deployed.
  - Dependencies: T0.1. Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing data (field new/empty → low). Completion: field + FLS deployed.

### Phase 2 — `PRM_BoardCertificationService` core *(M2)*
- **T2.1 — Class + `execute` + `PractUow`; parse + gate + bulk resolution**
  - Purpose: parse `practitioners[]`; keep only gated (non‑empty `boardCertifications`); resolve `practitionerId` (Account query) + `healthcareProviderId` (HCP by NPI); read `caseManagerId` (batch‑injected — OQ‑E7‑3); capture practitioner‑level `effectiveFrom`/`To`.
  - Outcome: Appendix A steps 1–2. Impacted: `classes/PRM_BoardCertificationService.cls` (+ test).
  - Validation: compiles; gating correct; resolution batched. Testing: unit (parse + gate + resolution). Risks: **[RISK]** HCP resolution (OQ‑E7‑4); `caseManagerId` wiring (OQ‑E7‑3). Completion: parse + resolution green.
- **T2.2 — `buildCert` + required fields + `PRM_RecordKey__c`**
  - Purpose: in‑memory `BoardCertification` per §6; `PRM_EffectiveFrom__c` from practitioner `effectiveFrom`; `CertificationType` (valid picklist); NPI‑anchored key.
  - Dependencies: T2.1, T0.2 (grain). Validation: field‑by‑field unit assertions; key string correct. Testing: builder unit (cert type set/blank; dates; required fields). Risks: **[RISK]** grain (OQ‑E7‑2); `Name`/`effectiveFrom` blank (OQ‑E7‑6/7); CertificationType value (OQ‑E7‑5). Completion: builder unit‑tested.
- **T2.3 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; per‑practitioner response (gated subset, input order).
  - Dependencies: T2.2. Validation: rows have correct FKs + key; DML count = 1. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildCert` (cert type, dates, effective dates, key), `key` (blank normalization), gating.
- **T3.2 Bulk/governor:** 251+ practitioners × multiple certs → ≤2 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → row count unchanged.
- **T3.4 Negative/edge:** empty `boardCertifications` (skipped), **blank `boardCertificationName` → `DmlException`** (Name required, OQ‑E7‑7), **blank `effectiveFrom` → `DmlException`** (PRM_EffectiveFrom__c required, OQ‑E7‑6), invalid `CertificationType` (OQ‑E7‑5), missing HCP, no‑NPI (OQ‑E7‑8).
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `BoardCertification` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E7‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/boardcert-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. Commit prefix `[E7]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RISK] Dedupe grain + blank `certificationType` (OQ‑E7‑2/5).** Org data proves `BoardName` alone is insufficient (same practitioner+board, 2 types). The key `{npi}_{boardName}_{certificationType}` fixes that — **but** the sample payload allows `certificationType: ""`. A blank type makes the key `{npi}_{boardName}_` and would **collapse two blank‑type certs on the same board**. Confirm whether `certificationType` is always present (and a valid picklist value), or whether another attribute (e.g. `boardCertificationName`) belongs in the key.
- **[RISK] Two required fields (OQ‑E7‑6/7).** Both `Name` (← `boardCertificationName`) and **`PRM_EffectiveFrom__c`** (← `practitionerInfo.effectiveFrom`) are required on the org; a blank either fails the whole chunk. Validate/normalize at intake (fail‑fast) rather than at `upsert`.
- **[RECOMMENDATION] `healthcareProviderId` resolution (OQ‑E7‑4).** Resolve HCP by **`PRM_RecordKey__c = npi`** (E2's unique stamp) rather than by `AccountId` (an Account can have multiple HCPs in polluted data) — or have `PractitionerBatch` pass E2's per‑practitioner `healthcareProviderId` in‑memory (E20 §9 / OQ‑E2‑9).
- **[RECOMMENDATION] `caseManagerId` wiring (OQ‑E7‑3).** Batch injects a resolved `caseManagerId` per practitioner node (from `PRM_AsyncJobRecords__c`); the §5 payload doesn't carry it today.
- **[RECOMMENDATION] `effectiveFrom`/`To` grain.** The design applies practitioner‑level `effectiveFrom`/`To` to every cert. Confirm that's intended vs per‑cert dates (the payload only has practitioner‑level today).
- **[RECOMMENDATION] Explicit date parsing (OQ‑E7‑9).** `boardExpires`/`boardOriginal`/`boardRecret`/`effectiveFrom` are dates; `Date.parse` is locale‑dependent — parse explicitly if the format is fixed (single‑owner `PRM_FormSubUtility`).

---

## 6. Gaps & hidden dependencies

- **Dedupe grain + blank cert type (OQ‑E7‑2/5)** — gates the key + idempotency test.
- **Required `Name` + `PRM_EffectiveFrom__c` (OQ‑E7‑6/7)** — intake must guarantee both.
- **Target org (OQ‑E7‑1)**; **E07 `PRM_RecordKey__c` + FLS** — not yet created → Phase 1.
- **E2 dependency** — HealthcareProvider with `PRM_RecordKey__c = npi` (or in‑memory output).
- **`caseManagerId` wiring (OQ‑E7‑3)**; **date parsing (OQ‑E7‑9)**; **no‑NPI (OQ‑E7‑8)**.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E7‑1 — Target org** for deploy/test.
- **OQ‑E7‑2 — Board‑cert dedupe grain.** `npi_boardName_certificationType` confirmed sufficient (incl. blank‑type handling)? Or do renewals/dates repeat it? **Gates the key + Appendix A `key(...)`.**
- **OQ‑E7‑3 — `caseManagerId` source/wiring.** Confirm `PractitionerBatch` injects a resolved `caseManagerId` per practitioner node.
- **OQ‑E7‑4 — `healthcareProviderId` resolution.** By `PRM_RecordKey__c = npi` (recommended), by `AccountId`, or passed in‑memory from E2?
- **OQ‑E7‑5 — `CertificationType` picklist.** Confirm inbound `certificationType` maps to one of the 37 active values; and whether it can be **blank** (impacts the key).
- **OQ‑E7‑6 — `PRM_EffectiveFrom__c` always present?** Required field ← `practitionerInfo.effectiveFrom`; confirm intake guarantees it, or define a default.
- **OQ‑E7‑7 — `Name` (`boardCertificationName`) always present?** Required field — confirm or define a fallback.
- **OQ‑E7‑8 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key.
- **OQ‑E7‑9 — Date format / `effectiveFrom` grain.** Locale‑parse vs fixed format for `boardExpires`/`boardOriginal`/`boardRecret`/`effectiveFrom`; and confirm `effectiveFrom`/`To` are practitioner‑level (applied to all certs) vs per‑cert.

*(Already resolved: org validation done — fields/types confirmed; `BoardName` alone insufficient → `certificationType` in the key; new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E07's `PRM_RecordKey__c` is NOT yet created → built as E07 Phase 1**.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | Blank/invalid `certificationType` → key collapse or insert fail | Medium | High | OQ‑E7‑2/5; validate/map at intake; T3.4 |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | `Name` or `PRM_EffectiveFrom__c` blank → chunk insert fails | Medium | High | OQ‑E7‑6/7; intake validation; T3.4 |
| R‑4 | Dedupe grain wrong (renewals collapse) | Low–Med | Medium | OQ‑E7‑2 business decision; only `key(...)` changes |
| R‑5 | HCP not resolvable by NPI (E2 not run / stamp missing) | Low–Med | Medium | OQ‑E7‑4; run after E2; resolve by `PRM_RecordKey__c=npi` |
| R‑6 | `caseManagerId` wiring (mutable Account vs job record) | Medium | High | OQ‑E7‑3; batch injects from `PRM_AsyncJobRecords__c` |
| R‑7 | Date locale drift on parse | Medium | Medium | OQ‑E7‑9; explicit parser |
| R‑8 | No target org → can't deploy/test | Medium | High | OQ‑E7‑1 |
| R‑9 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner coordination |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. OQ‑E7‑2 grain) → 1 (**create the field + FLS**) → 2 (service) → 3 → 4 → 5. Runs **after E2** in `PractitionerBatch`.
- **Effort:** within the ~0.5 d catalog estimate — class + builder + key ~0.25 · tests ~0.2 · evidence/VCS folded in.
- **Depends on:** Epic A + Epic B + E1 + **E2** on `main`, plus `PractitionerBatch`. **Feeds:** nothing downstream consumes E7 (BoardCertification is a leaf).

---

## 10. What happens after sign‑off

Resolve OQ‑E7‑1…OQ‑E7‑9 — **the grain (OQ‑E7‑2) and the two required fields (OQ‑E7‑6/7) are the gates**. Then: **create + deploy the E07 `PRM_RecordKey__c` field + FLS (Phase 1)** → build the service per **Appendix A** (parse + gate → resolve Contact/HCP → build + key → one bulk `upsert` → response) → tests → Test Evidence Report → human sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E7‑1) and the grain (OQ‑E7‑2) are confirmed.**

---

## Appendix A — Apex class `PRM_BoardCertificationService` (+ meta)

> Full `PRM_BoardCertificationService` (expands `E07…md` §4.2). **Depends on** `PRM_ServiceBase`. **Provisional:** the `key(...)` reflects the current grain — finalize after OQ‑E7‑2. `caseManagerId` is batch‑injected (OQ‑E7‑3); HCP resolved by `PRM_RecordKey__c = npi` (OQ‑E7‑4); `effectiveFrom`/`To` are practitioner‑level applied to each cert.

```apex
public with sharing class PRM_BoardCertificationService extends PRM_ServiceBase {

    // one per GATED practitioner (non-empty boardCertifications), in input order
    @TestVisible
    private class PractUow {
        Map<String, Object> p;          // practitionerInfo (id, npi, effectiveFrom/To)
        List<Object> certs;             // boardCertifications[]
        Id accountId;                   // = practitionerInfo.id (E1)
        Id caseManagerId;               // from PRM_AsyncJobRecords__c (batch context) — OQ-E7-3
        Id practitionerId;              // PersonContactId (resolved)
        Id healthcareProviderId;        // from E2 (resolved by NPI) — OQ-E7-4
        Date effFrom;                   // practitioner-level (REQUIRED on the object)
        Date effTo;
        List<BoardCertification> rows = new List<BoardCertification>();
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
                List<Object> certs = (List<Object>) app.get('boardCertifications');
                if (certs == null || certs.isEmpty()) continue;           // GATED: skip
                PractUow u = new PractUow();
                u.p             = (Map<String, Object>) app.get('practitionerInfo');
                u.certs         = certs;
                u.accountId     = (Id) u.p.get('id');
                u.caseManagerId = (Id) app.get('caseManagerId');          // batch-injected (OQ-E7-3)
                u.effFrom       = parseDate((String) u.p.get('effectiveFrom'));   // REQUIRED on insert (OQ-E7-6)
                u.effTo         = parseDate((String) u.p.get('effectiveTo'));
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

        // 3) build BoardCertification rows; key per §2 (provisional grain — OQ-E7-2)
        List<BoardCertification> allRows = new List<BoardCertification>();
        for (PractUow u : uows) {
            Account a = accById.get(u.accountId);
            u.practitionerId       = (a != null) ? a.PersonContactId : null;
            String npi             = (String) u.p.get('npi');
            u.healthcareProviderId = hcpByNpi.get(npi);
            for (Object co : u.certs) {
                BoardCertification bc = buildCert(u, (Map<String, Object>) co, npi);
                u.rows.add(bc);
                allRows.add(bc);
            }
        }

        // 4) ONE bulk upsert by the External Id (idempotent — §7)
        upsert allRows PRM_RecordKey__c;

        // 5) response (input order; gated subset)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (PractUow u : uows) {
            List<Id> ids = new List<Id>();
            for (BoardCertification bc : u.rows) ids.add(bc.Id);
            results.add(new Map<String, Object>{
                'accountId'              => u.accountId,
                'boardCertificationIds'  => ids
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── builder (pure in-memory; field map per §6) ──
    private BoardCertification buildCert(PractUow u, Map<String, Object> c, String npi) {
        String boardName = (String) c.get('boardName');
        String certType  = (String) c.get('certificationType');      // picklist (OQ-E7-5)

        BoardCertification bc = new BoardCertification();
        bc.AccountId            = u.accountId;
        bc.HealthcareProviderId = u.healthcareProviderId;
        bc.PractitionerId       = u.practitionerId;
        bc.Name                 = (String) c.get('boardCertificationName');   // REQUIRED (OQ-E7-7)
        bc.BoardName            = boardName;
        if (String.isNotBlank(certType)) bc.CertificationType = certType;     // picklist
        bc.ExpirationDate       = parseDate((String) c.get('boardExpires'));
        bc.PRM_BoardOriginal__c = parseDate((String) c.get('boardOriginal'));
        bc.PRM_BoardReCert__c   = parseDate((String) c.get('boardRecret'));
        bc.PRM_EffectiveFrom__c = u.effFrom;                                  // REQUIRED (OQ-E7-6)
        bc.PRM_EffectiveTo__c   = u.effTo;
        bc.PRM_CaseManager__c   = u.caseManagerId;
        bc.PRM_RecordKey__c     = key(new List<String>{ npi, boardName, certType });
        return bc;
    }

    // ── helpers ──
    private String key(List<String> parts) {
        List<String> safe = new List<String>();
        for (String s : parts) safe.add(s == null ? '' : s);   // normalize blanks
        return String.join(safe, '_');                          // '_' delimiter (§2)
    }
    private Date parseDate(String s) { return String.isBlank(s) ? null : Date.parse(s); }   // ⚠ locale — confirm format
}
```

**`PRM_BoardCertificationService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E07_PRM_BoardCertificationService.md`. Open items (OQ‑E7‑1…OQ‑E7‑9) above still apply — **especially OQ‑E7‑2 (grain) and OQ‑E7‑6/7 (required fields).**

---

## Appendix B — Field metadata `BoardCertification.PRM_RecordKey__c`

> **NEW (E07‑owned).** Path: `force-app/main/default/objects/BoardCertification/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`.

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
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E07 — BoardCertification). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

> ⚠ If **OQ‑E7‑2** changes the grain, the **field shape is unchanged** — only the value composed in `key(...)` (Appendix A) changes.

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`.

```xml
<fieldPermissions>
    <field>BoardCertification.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_BoardCertificationServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`**, modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, re‑run/idempotency. ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`, `createHealthcareProvidersByNpi`). The blank‑Name / blank‑effectiveFrom negatives are **contingent on OQ‑E7‑6/7**; `CertificationType` uses a confirmed picklist value (OQ‑E7‑5).

```apex
@isTest
private class PRM_BoardCertificationServiceTest {

    private static final Integer BULK = 251;
    private static final String CERT_TYPE = 'Internal Medicine';   // valid CertificationType picklist value (OQ-E7-5)
    private static final String EFF_FROM = '01/01/2020';           // PRM_EffectiveFrom__c required (OQ-E7-6)

    // ⚠ Confirm/add these builders in PRM_TestDataFactory (do NOT inline data here):
    //   createPractitionersWithCaseManagers(count, doInsert) -> Person Accounts + a Case Manager each
    //   caseManagerByAccount(List<Account>) -> Map<AccountId, CaseManagerId>
    //   createHealthcareProvidersByNpi(Map<AccountId,npi>, doInsert) -> HCP per account w/ PRM_RecordKey__c=npi
    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);
    }

    private static Map<String, Object> buildParams(
            List<Account> accts, Map<Id, Id> cm, Map<Id, String> npiByAcct,
            Integer certsPer, String certName, String effFrom) {
        List<Object> practitioners = new List<Object>();
        for (Account a : accts) {
            List<Object> certs = new List<Object>();
            for (Integer i = 0; i < certsPer; i++) {
                certs.add(new Map<String, Object>{
                    'boardName'             => 'ABIM-' + i,
                    'boardCertificationName'=> certName,
                    'certificationType'     => CERT_TYPE,
                    'boardExpires'          => '12/31/2030',
                    'boardOriginal'         => '06/30/2010',
                    'boardRecret'           => '06/30/2020'
                });
            }
            practitioners.add(new Map<String, Object>{
                'practitionerInfo' => new Map<String, Object>{
                    'id' => a.Id, 'npi' => npiByAcct.get(a.Id),
                    'effectiveFrom' => effFrom, 'effectiveTo' => ''
                },
                'boardCertifications' => certs,
                'caseManagerId'       => cm.get(a.Id)
            });
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    private static Map<Id, String> npiMap(List<Account> accts) {
        Map<Id, String> m = new Map<Id, String>();
        Integer n = 0; for (Account a : accts) m.put(a.Id, '30000000' + n++);
        return m;
    }

    @isTest
    static void shouldCreateOneRowPerCert_WhenBulk() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<Id, String> npis = npiMap(accts);
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<String, Object> params = buildParams(accts, cm, npis, 2, 'Internal Medicine', EFF_FROM);

        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_BoardCertificationService().execute(params);
        Test.stopTest();

        Assert.areEqual(BULK * 2, [SELECT COUNT() FROM BoardCertification],
            'Two certs per practitioner should be created');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(),
            'Response should carry one entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<Id, String> npis = npiMap(accts);
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<String, Object> params = buildParams(accts, cm, npis, 1, 'Internal Medicine', EFF_FROM);

        Test.startTest();
        new PRM_BoardCertificationService().execute(params);   // first
        new PRM_BoardCertificationService().execute(params);   // re-run (idempotent)
        Test.stopTest();

        Assert.areEqual(BULK, [SELECT COUNT() FROM BoardCertification],
            'Re-running with the same key must upsert, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoCerts() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Delegated',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '3999999999', 'effectiveFrom' => EFF_FROM },
                    'boardCertifications' => new List<Object>()      // empty -> gated out
                }
            }
        };

        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_BoardCertificationService().execute(params);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM BoardCertification], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(),
            'Response should exclude gated-out practitioners');
    }

    @isTest
    static void shouldSetFieldsAndKey_WhenBuilt() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<Id, String> npis = new Map<Id, String>{ a.Id => '3111111111' };
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, npis, 1, 'Internal Medicine', EFF_FROM);

        Test.startTest();
        new PRM_BoardCertificationService().execute(params);
        Test.stopTest();

        BoardCertification bc = [
            SELECT CertificationType, PRM_EffectiveFrom__c, HealthcareProviderId, PRM_RecordKey__c
            FROM BoardCertification LIMIT 1
        ];
        Assert.areEqual(CERT_TYPE, bc.CertificationType, 'CertificationType should be the mapped picklist value');
        Assert.areEqual(Date.parse(EFF_FROM), bc.PRM_EffectiveFrom__c, 'PRM_EffectiveFrom__c should be set (required)');
        Assert.isNotNull(bc.HealthcareProviderId, 'HCP should be resolved by NPI');
        Assert.isTrue(bc.PRM_RecordKey__c.contains('_'), 'Key should be underscore-joined');
    }

    // PRM_EffectiveFrom__c is required (org) -> blank effectiveFrom must fail the insert (OQ-E7-6).
    @isTest
    static void shouldThrow_WhenEffectiveFromBlank() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<Id, String> npis = new Map<Id, String>{ a.Id => '3122222222' };
        PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, npis, 1, 'Internal Medicine', '');  // blank effFrom

        Test.startTest();
        try {
            new PRM_BoardCertificationService().execute(params);
            Assert.fail('Expected a DmlException for the required PRM_EffectiveFrom__c');
        } catch (DmlException e) {
            Assert.isTrue(e.getMessage().length() > 0, 'DmlException should be raised for the missing required field');
        }
        Test.stopTest();
    }
}
```

**`PRM_BoardCertificationServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ × 2 certs), re‑run idempotency, gating (empty `boardCertifications`), field/key correctness (`CertificationType`, `PRM_EffectiveFrom__c`, HCP resolution, key), required‑field negatives (blank `boardCertificationName`, blank `effectiveFrom`). Add an invalid‑`CertificationType` negative once OQ‑E7‑5 is set. Coverage ≥ 85%.

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E7‑1). **Field + FLS first**, then classes, then tests.

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/BoardCertification/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_BoardCertificationService.cls" \
  -d "force-app/main/default/classes/PRM_BoardCertificationServiceTest.cls" \
  -o <alias>

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_BoardCertificationServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check
sf data query -o <alias> \
  -q "SELECT Id, BoardName, CertificationType, PRM_EffectiveFrom__c, HealthcareProviderId, PRM_RecordKey__c FROM BoardCertification ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E7‑2 (grain incl. blank cert type) decided → `key(...)` finalized.
- [ ] OQ‑E7‑5 (`CertificationType` values) + OQ‑E7‑6/7 (required `PRM_EffectiveFrom__c` + `Name`) confirmed.
- [ ] Target org confirmed (OQ‑E7‑1); `caseManagerId` wiring (OQ‑E7‑3) + HCP resolution (OQ‑E7‑4) confirmed.
- [ ] `PRM_TestDataFactory` builders exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_BoardCertificationService` compiles; `upsert … PRM_RecordKey__c` resolves; runs after E2.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
