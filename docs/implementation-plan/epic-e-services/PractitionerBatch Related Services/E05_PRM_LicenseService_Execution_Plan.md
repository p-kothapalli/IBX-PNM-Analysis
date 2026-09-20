# E05 · `PRM_LicenseService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan is **self‑contained for component generation** — it specifies and includes **every artifact** needed to build E05 (see **§0 Component inventory**): the Apex class + `.cls-meta.xml` (**Appendix A**), the `BusinessLicense.PRM_RecordKey__c` field metadata (**Appendix B**), the `PRM_AsyncJob_Access` permission‑set FLS (**Appendix C**), the Apex test class + meta (**Appendix D**), and deploy/validation steps (**Appendix E**). **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered — **especially the BLOCKING dedupe‑grain (OQ‑E5‑2)** — and the target org (OQ‑E5‑1) is confirmed.
>
> **Source of truth:** `E05_PRM_LicenseService.md` (design §1–§9, incl. the org‑validation results, CL‑E8, and the NPI‑anchored idempotency decision). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved **[OPEN]** item are **⛔ Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `BusinessLicense.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/BusinessLicense/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E05‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` entry (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_LicenseService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_LicenseService.cls` (+ `.cls-meta.xml`) | **NEW** | Appendix A |
| 4 | `PRM_LicenseServiceTest` | Apex test class | `force-app/main/default/classes/PRM_LicenseServiceTest.cls` (+ `.cls-meta.xml`) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test` skills):** `PRM_` prefix; `with sharing`; bulkified (no SOQL/DML in loops, one bulk DML per object); CRUD/FLS via **`WITH USER_MODE`**; **API version 66.0**; test class `PRM_LicenseServiceTest` reuses **`PRM_TestDataFactory`** (never a new factory, no inline `@TestSetup` data) and uses the modern **`Assert`** class with messages; bulk path tested at **251+**. **Error handling is at the batch level** — the service lets exceptions propagate; the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain, so the service has **no inline try/catch**.

---

## 1. Confirmed requirements (from `E05_PRM_LicenseService.md`)

- **[CONFIRMED]** `PRM_LicenseService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1)**, after E1 created the Case Managers at intake. **Writes:** `BusinessLicense`. (Design §1, §4.)
- **[CONFIRMED]** **Gated** — process **only** practitioners whose payload has a **non‑empty `businessLicenses[]`**; skip the rest. (Design §1, §7.)
- **[CONFIRMED]** **Branch: BOTH** (IBC + Delegated). Input is a **single unified `businessLicenses[]`** per practitioner (each element carries its own `licenseType`); the legacy two‑array split (DEA/CDS vs SBRD) + transform/merge are collapsed. (Design §1, §5, §6 — CL‑E8.)
- **[CONFIRMED]** **Independent of E2** — needs only E1's `Account` / `PersonContact` / Case Manager; no `HealthcareProvider` dependency. Runs in the same batch. (Design §1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk (`List`), each element `{ practitionerInfo (incl. `id` = **E1 Account Id**, `npi`), businessLicenses[] }`, plus `params.flow`. Build all rows in memory, then **one bulk DML**. (Design §4, §4.1, §5.)
- **[CONFIRMED]** **Correlation / Id resolution:** `practitionerInfo.id` = Account Id → resolve `practitionerId` (`PersonContactId`) via **one bulk Account query**. `caseManagerId` comes from the **`PRM_AsyncJobRecords__c`** row (stable batch scope), **not** the mutable `Account.PRM_CaseManager__c`. A per‑practitioner wrapper holds references. (Design §4.1.)
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — business‑confirmed, E02 §8 CL‑E2): `upsert` `BusinessLicense` by **`PRM_RecordKey__c`**; **provisional** key = `{npi}_{licenseType}_{licenseNumber}_{practitionerState}` (delimiter `_`, blanks normalized to `''`). **The grain is provisional — see OQ‑E5‑2 (BLOCKING).** (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E05‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`BusinessLicense`** + Read+Edit FLS on the permission set **`PRM_AsyncJob_Access`** (base permset is Epic A's; the field + FLS are **E05's own**). **The field does not exist yet — creating it is a required E05 deliverable (Phase 1, T1.1).** (Design §3 WI‑1/WI‑2.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV01):** `AccountId`←accountId, `ContactId`←practitionerId, `Name`/`LicenseNumber`←`practitionerLicenseNumber`, `LicenseClass`←`licenseType`, `PRM_LicenseState__c`←`practitionerState`, `PRM_ProviderLicenseEffectiveDate__c`←`licenseIssuedDate`, `PRM_ProviderLicenseExpirationDate__c`←`licenseExpirationDate`, `VerifiedDate`=`Date.today()`, `PRM_CaseManager__c`←caseManagerId, `Status` (optional, payload), `PRM_RecordKey__c` (computed). (Design §6.)
- **[CONFIRMED]** **Org‑validated field facts:** `Name` is **required**; `LicenseClass` / `Status` / `PRM_LicenseState__c` are **picklists** (`LicenseClass` may be null); all E5 fields exist with expected types. (Design §2 org results, §6.)
- **[CONFIRMED]** **In‑service computed:** `VerifiedDate = Date.today()`; `PRM_RecordKey__c` (per §2). FK fields set in‑service. (Design §5, §6.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** of `BusinessLicense[]` by `PRM_RecordKey__c`; gated; returns `businessLicenseIds` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, businessLicenseIds }`. (Design §4.)
- **[CONFIRMED]** **Governor budget:** 1 SOQL (Account resolution) + 1 bulk DML (BusinessLicense), constant regardless of chunk size; no DML/SOQL in loops. (Design §4.2 note.)
- **[CONFIRMED]** **Effort:** ~0.5 engineer‑day. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set `PRM_AsyncJob_Access`), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility`), **E1** (Account/Contact/CaseManager + `PRM_AsyncJobRecords__c` seeding), the **`PractitionerBatch`** wiring, and E05's own `PRM_RecordKey__c` field + FLS. **No E2 dependency.**

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL in loops; one bulk query (Account) + one bulk `upsert`.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch** (already‑committed chunks must not duplicate). (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch running user via `PRM_AsyncJob_Access`) — so `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E5‑4).
- **[CONFIRMED]** **Gated:** practitioners with empty `businessLicenses[]` are skipped (no rows, not in the response).
- **[OPEN/BLOCKING]** The **dedupe grain** (key composition) is provisional (OQ‑E5‑2); the `key(...)` line in Appendix A is the only place that changes if the grain decision adds `effectiveDate`.

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds `BusinessLicense[]` with the correct field map + `VerifiedDate`; **1 bulk DML** regardless of chunk size.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running `execute()` on the same chunk produces **no duplicates** (contingent on the confirmed grain — OQ‑E5‑2).
- **[CONFIRMED]** `caseManagerId` FK sourced from `PRM_AsyncJobRecords__c` (not the mutable Account back‑link).
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, businessLicenseIds }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (chunk of practitioners, multiple licenses each) asserting governor‑safe DML counts and (b) a **re‑run/idempotency** test (execute twice → counts unchanged); Test Evidence Report + human sign‑off (Epic A §A7) before promotion.
- **[CONFIRMED]** Field API names/types validated against the org (already done, IBXDEV01 — re‑confirm on the target org, OQ‑E5‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E5‑1…OQ‑E5‑9)
- **T0.1 — Target org** (OQ‑E5‑1) for deploy + tests. Completion: org confirmed.
- **T0.2 — Resolve the BLOCKING dedupe grain** (OQ‑E5‑2): is a license unique per practitioner by `licenseType+licenseNumber+state`, or must `effectiveDate` (renewals) be part of the key? Purpose: fixes the `PRM_RecordKey__c` composition. Outcome: grain decided. Validation: business sign‑off (org data is test‑polluted, can't decide it). Risks: **[RISK]** wrong grain → renewals collapse or duplicates. Completion: grain confirmed → Appendix A `key(...)` finalized.
- **T0.3 — Verify dependencies present on `main`:** `PRM_ServiceBase`; `PRM_FormSubUtility`; E1 (Account/Case/IA + `PRM_AsyncJobRecords__c` seeding); the permission set `PRM_AsyncJob_Access` (base). *(E05's `PRM_RecordKey__c` on `BusinessLicense` is **NOT pre‑existing** — it is created in Phase 1, T1.1.)* Validation: describe / deploy dry‑run. Completion: all present (or gaps logged).
- **T0.4 — Resolve open business/data items:** no‑NPI policy (OQ‑E5‑4), CL‑E8 payload shape (OQ‑E5‑5), `Name` always present (OQ‑E5‑6), `Status` default (OQ‑E5‑7), date format (OQ‑E5‑8), picklist value validity (OQ‑E5‑9), `caseManagerId` wiring (OQ‑E5‑3). Completion: each decided or explicitly deferred.

### Phase 1 — E05 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `BusinessLicense`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (design §3 WI‑1/WI‑2). **Confirmed: the field does not exist yet — this task creates it (E05‑owned).**
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS created & deployed.
  - Dependencies: T0.1. Prerequisites: Phase 0. Impacted: `objects/BusinessLicense/fields/PRM_RecordKey__c.field-meta.xml`, `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` *(metadata authored separately — not generated in this plan; field spec = Text 255, externalId=true, unique=true, caseSensitive=false, per design §3)*.
  - Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing data (field new/empty → low). Completion: field + FLS deployed.

### Phase 2 — `PRM_LicenseService` core *(M2)*
- **T2.1 — Class + `execute` + `PractUow`; parse + gate + bulk Id resolution**
  - Purpose: parse `practitioners[]`; keep only gated practitioners (non‑empty `businessLicenses`); resolve `practitionerId` in one bulk Account query; obtain `caseManagerId` from the batch context (`PRM_AsyncJobRecords__c` — OQ‑E5‑3).
  - Outcome: Appendix A steps 1–2.
  - Dependencies: T0.3, Phase 1. Impacted: `classes/PRM_LicenseService.cls` (+ `…Test.cls`).
  - Validation: compiles; parses sample payload; gating correct; Account resolution batched. Testing: unit (parse + gate + resolution). Risks: **[RISK]** `caseManagerId` wiring (OQ‑E5‑3); payload shape drift (CL‑E8). Completion: parse + gate + resolution green.
- **T2.2 — `buildLicense` + `VerifiedDate` + `PRM_RecordKey__c`**
  - Purpose: in‑memory `BusinessLicense` build per the §6 field map; `VerifiedDate = Date.today()`; NPI‑anchored key (provisional grain — OQ‑E5‑2).
  - Outcome: Appendix A `buildLicense` + `key`.
  - Dependencies: T2.1, T0.2 (grain). Validation: field‑by‑field unit assertions; key string correct. Testing: builder unit (DEA/CDS/SBRD types; blank dates; null `LicenseClass`). Risks: **[RISK]** grain (OQ‑E5‑2); `Name` blank (OQ‑E5‑6); picklist values (OQ‑E5‑9); date parse (OQ‑E5‑8). Completion: builder unit‑tested.
- **T2.3 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; build per‑practitioner response (gated subset, input order).
  - Outcome: Appendix A steps 4–5.
  - Dependencies: T2.2. Validation: created rows have correct FKs + key; DML count = 1; response shape. Testing: bulk test. Risks: **[RISK]** upsert by external Id semantics. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildLicense` (types, blanks, null `LicenseClass`, `VerifiedDate`), `key` (blank normalization), gating.
- **T3.2 Bulk/governor:** chunk of N practitioners × multiple licenses → 1 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → `BusinessLicense` count unchanged (upsert by key).
- **T3.4 Negative/edge:** empty `businessLicenses` (skipped), blank `Name`/`practitionerLicenseNumber` (per OQ‑E5‑6), invalid picklist value (per OQ‑E5‑9), blank dates, no‑NPI (per OQ‑E5‑4).
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `BusinessLicense` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E5‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/license-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. Commit prefix `[E5]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RISK — BLOCKING] Dedupe grain (OQ‑E5‑2).** Org data is test‑polluted, so it can't confirm whether `licenseType+licenseNumber+state` is unique per practitioner or whether **renewals** (same license, new `effectiveDate`) are legitimate distinct rows. **Options:**
  - **(A) Triple** `{npi}_{licenseType}_{licenseNumber}_{state}` *(provisional / current design)* — simplest; **risk:** a renewal `upsert`-overwrites the prior row (history lost).
  - **(B) Triple + effectiveDate** `…_{effectiveDate}` — preserves renewals; **risk:** if the same license is re‑sent with a corrected date it creates a second row.
  - *Recommendation:* **confirm with business**; if renewals are tracked, prefer (B). **Do not build the key until decided.** Only the `key(...)` line in Appendix A changes.
- **[RECOMMENDATION] `caseManagerId` wiring (OQ‑E5‑3).** The design says it comes from `PRM_AsyncJobRecords__c` (batch scope). The cleanest contract is for `PractitionerBatch` to **inject a resolved `caseManagerId` per practitioner node** (Appendix A reads `app.get('caseManagerId')`). Confirm this vs. an in‑service lookup; the §5 payload doesn't carry it today.
- **[RECOMMENDATION] Validate picklist + `Name` at intake (OQ‑E5‑6/E5‑9).** `Name` is required and `LicenseClass`/`Status`/`PRM_LicenseState__c` are picklists; a bad value throws on `upsert` and (since the chunk is one DML) can fail the batch chunk. Prefer fail‑fast validation at intake over a DML exception.
- **[RECOMMENDATION] Explicit date parsing (OQ‑E5‑8).** `Date.parse` is locale‑dependent; if the payload format is fixed (e.g. `MM/dd/yyyy` as in the sample), add an explicit parser (single‑owner `PRM_FormSubUtility`) to avoid org‑locale drift.
- **[RECOMMENDATION] CL‑E8 payload shape (OQ‑E5‑5).** Confirm the OmniScript emits a **single** unified `businessLicenses[]`; if it still sends two blocks (DEA/CDS + SBRD), normalize in `PRM_FormSubUtility` before E5 (don't reintroduce the legacy transform in the service).
- **[RECOMMENDATION] Partial‑failure semantics.** With one bulk `upsert`, decide all‑or‑nothing vs `Database.upsert(rows, false)` + per‑row error handling. The design implies all‑or‑nothing (chunk rolls back on error); confirm that's desired for the pilot.

---

## 6. Gaps & hidden dependencies

- **Dedupe grain (OQ‑E5‑2)** — BLOCKING; gates the key + idempotency test.
- **Target org (OQ‑E5‑1)** — gates deploy/test.
- **E05 `PRM_RecordKey__c` + FLS** — E05's own; **not yet created → built in Phase 1 (T1.1)**.
- **`caseManagerId` wiring (OQ‑E5‑3)** — batch must supply it from `PRM_AsyncJobRecords__c`; not in the §5 payload today.
- **CL‑E8** — single `businessLicenses[]` vs two legacy blocks (normalize in `PRM_FormSubUtility`).
- **`PRM_FormSubUtility`** — date parser / normalization helpers (single‑owner).
- **E1** — Account/Contact/CaseManager + `PRM_AsyncJobRecords__c` seeding.
- **Open business/data:** no‑NPI policy, `Name` presence, `Status` default, picklist validity, date format.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E5‑1 — Target org** for deploy/test. *(Blocks Phase 0/1/4.)*
- **OQ‑E5‑2 (BLOCKING) — License dedupe grain.** `licenseType+licenseNumber+state` only, or `+ effectiveDate` (renewals)? *(See §5 options; recommend confirming with business.)* **Gates the key + Appendix A `key(...)`.**
- **OQ‑E5‑3 — `caseManagerId` source/wiring.** Confirm `PractitionerBatch` injects a resolved `caseManagerId` per practitioner node (from `PRM_AsyncJobRecords__c`), vs an in‑service lookup. *(Appendix A assumes per‑node injection — flagged.)*
- **OQ‑E5‑4 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key for practitioners without an NPI.
- **OQ‑E5‑5 (CL‑E8) — License payload shape.** Single unified `businessLicenses[]` (with `licenseType` per element), or two legacy blocks needing normalization in `PRM_FormSubUtility`?
- **OQ‑E5‑6 — `Name` always present?** `Name` (required) ← `practitionerLicenseNumber`; define a fallback if it can be blank.
- **OQ‑E5‑7 — `Status` source.** Set by payload or defaulted? (Currently optional pass‑through.)
- **OQ‑E5‑8 — Date format.** Locale‑parse vs a fixed format for `licenseIssuedDate` / `licenseExpirationDate`.
- **OQ‑E5‑9 — Picklist value validity.** Are `licenseType` / `Status` / `practitionerState` guaranteed active picklist entries? *Recommendation:* validate at intake.

*(Already resolved: org validation done — fields exist, types confirmed; new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E05's `PRM_RecordKey__c` on `BusinessLicense` is NOT yet created → built as E05 Phase 1, T1.1** (was OQ‑E5‑10).)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | **Dedupe grain wrong** (renewals collapse, or over‑split) | Medium | High | OQ‑E5‑2 business decision **before** building the key; T0.2 |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | `caseManagerId` wiring (mutable Account vs job record) | Medium | High | OQ‑E5‑3; batch injects from `PRM_AsyncJobRecords__c` |
| R‑4 | `Name`/`practitionerLicenseNumber` blank → insert fails | Medium | Medium | OQ‑E5‑6; intake validation; T3.4 |
| R‑5 | Picklist value mismatch → insert fails | Medium | Medium | OQ‑E5‑9; validate at intake; T3.4 |
| R‑6 | Date locale drift on parse | Medium | Medium | OQ‑E5‑8; explicit parser |
| R‑7 | CL‑E8 payload still two blocks | Low–Med | Medium | OQ‑E5‑5; normalize in `PRM_FormSubUtility` |
| R‑8 | No target org → can't deploy/test | Medium | High | OQ‑E5‑1 |
| R‑9 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner coordination |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. resolve OQ‑E5‑2 grain) → 1 (**create the `PRM_RecordKey__c` field + FLS**) → 2 (service) → 3 → 4 → 5. `PractitionerBatch` wiring pairs with E5.
- **Effort:** within the ~0.5 d catalog estimate — class + builder + key ~0.25 · tests (bulk/idempotency/negative) ~0.2 · evidence/VCS folded in. *(Schema is a small declarative add; grain decision is a business action, not dev effort.)*
- **Depends on:** Epic A (permission set) + Epic B + E1 on `main`, plus `PractitionerBatch`. **No E2 dependency.** **Blocks/feeds:** nothing downstream consumes E5 outputs directly (BusinessLicense is a leaf for the practitioner graph).

---

## 10. What happens after sign‑off

Resolve OQ‑E5‑1…OQ‑E5‑9 — **the dedupe grain (OQ‑E5‑2) is the gate**. Then: **create + deploy the E05 `PRM_RecordKey__c` field + FLS (Phase 1 — the field does not exist yet)** → build the service per **Appendix A** (parse + gate → bulk Account resolution → `buildLicense` + key → one bulk `upsert` → response) → tests (unit/bulk/idempotency/negative) → Test Evidence Report → human governance sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E5‑1) and the grain (OQ‑E5‑2) are confirmed.**

---

## Appendix A — Apex class `PRM_LicenseService` (+ meta)

> Full `PRM_LicenseService` (expands `E05_PRM_LicenseService.md` §4.2). **Depends on** `PRM_ServiceBase` and `PRM_FormSubUtility`. **Provisional:** the `key(...)` composition reflects the **current design grain** (triple) — **finalize after OQ‑E5‑2**. `caseManagerId` is read from the batch‑injected per‑practitioner node (OQ‑E5‑3). The class `.cls-meta.xml` follows the class; field + permission‑set metadata are in **Appendices B–C**.

```apex
public with sharing class PRM_LicenseService extends PRM_ServiceBase {

    // one per GATED practitioner (non-empty businessLicenses), in input order —
    // holds inputs + resolved Ids + the built rows for correlation
    @TestVisible
    private class PractUow {
        Map<String, Object> p;          // practitionerInfo (incl. id = Account Id, npi)
        List<Object> licenses;          // businessLicenses[]
        Id accountId;                   // = practitionerInfo.id (E1)
        Id practitionerId;              // PersonContactId (resolved)
        Id caseManagerId;               // from PRM_AsyncJobRecords__c (batch context) — OQ-E5-3
        List<BusinessLicense> rows = new List<BusinessLicense>();
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');                       // IBC vs Delegated (context)
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) build UoWs ONLY for gated practitioners; collect Account Ids (no DML/SOQL in loop)
        List<PractUow> uows = new List<PractUow>();
        Set<Id> accountIds = new Set<Id>();
        if (practitioners != null) {
            for (Object o : practitioners) {
                Map<String, Object> app = (Map<String, Object>) o;
                List<Object> lics = (List<Object>) app.get('businessLicenses');
                if (lics == null || lics.isEmpty()) continue;            // GATED: skip
                PractUow u = new PractUow();
                u.p             = (Map<String, Object>) app.get('practitionerInfo');
                u.licenses      = lics;
                u.accountId     = (Id) u.p.get('id');                    // E1 Account Id
                u.caseManagerId = (Id) app.get('caseManagerId');         // batch-injected (OQ-E5-3)
                accountIds.add(u.accountId);
                uows.add(u);
            }
        }
        if (uows.isEmpty()) {
            response = new Map<String, Object>{ 'practitioners' => new List<Object>() };
            return response;
        }

        // 2) ONE bulk query: Account -> PersonContactId (CRUD/FLS enforced)
        Map<Id, Account> accById = new Map<Id, Account>(
            [SELECT Id, PersonContactId FROM Account WHERE Id IN :accountIds WITH USER_MODE]);
        for (PractUow u : uows) {
            Account a = accById.get(u.accountId);
            u.practitionerId = (a != null) ? a.PersonContactId : null;
        }

        // 3) build BusinessLicense rows (formulas in-service; key per §2 — provisional grain, OQ-E5-2)
        List<BusinessLicense> allRows = new List<BusinessLicense>();
        for (PractUow u : uows) {
            String npi = (String) u.p.get('npi');
            for (Object lo : u.licenses) {
                BusinessLicense bl = buildLicense(u, (Map<String, Object>) lo, npi);
                u.rows.add(bl);
                allRows.add(bl);
            }
        }

        // 4) ONE bulk upsert by the External Id (idempotent — §7)
        upsert allRows PRM_RecordKey__c;     // populates Id on the same instances held by the UoWs

        // 5) response (input order; gated subset only)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (PractUow u : uows) {
            List<Id> ids = new List<Id>();
            for (BusinessLicense bl : u.rows) ids.add(bl.Id);
            results.add(new Map<String, Object>{
                'accountId'          => u.accountId,
                'businessLicenseIds' => ids
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── builder (pure in-memory; field map per §6) ──
    private BusinessLicense buildLicense(PractUow u, Map<String, Object> l, String npi) {
        String licenseType   = (String) l.get('licenseType');
        String licenseNumber = (String) l.get('practitionerLicenseNumber');
        String state         = (String) l.get('practitionerState');

        BusinessLicense bl = new BusinessLicense();
        bl.AccountId      = u.accountId;
        bl.ContactId      = u.practitionerId;
        bl.Name           = licenseNumber;                 // Name REQUIRED (← practitionerLicenseNumber; OQ-E5-6)
        bl.LicenseNumber  = licenseNumber;
        bl.LicenseClass   = licenseType;                   // picklist (OQ-E5-9)
        bl.PRM_LicenseState__c = state;                    // picklist (OQ-E5-9)
        bl.PRM_ProviderLicenseEffectiveDate__c  = parseDate((String) l.get('licenseIssuedDate'));      // OQ-E5-8
        bl.PRM_ProviderLicenseExpirationDate__c = parseDate((String) l.get('licenseExpirationDate'));  // OQ-E5-8
        bl.VerifiedDate       = Date.today();
        bl.PRM_CaseManager__c = u.caseManagerId;
        if (l.get('status') != null) bl.Status = (String) l.get('status');   // optional (OQ-E5-7)

        // PROVISIONAL key — finalize grain after OQ-E5-2 (triple vs +effectiveDate)
        bl.PRM_RecordKey__c = key(new List<String>{ npi, licenseType, licenseNumber, state });
        return bl;
    }

    // ── helpers ──
    private String key(List<String> parts) {
        List<String> safe = new List<String>();
        for (String s : parts) safe.add(s == null ? '' : s);   // normalize blanks
        return String.join(safe, '_');                          // '_' delimiter (§2)
    }

    private Date parseDate(String s) {
        return String.isBlank(s) ? null : Date.parse(s);        // ⚠ locale-dependent — OQ-E5-8
    }
}
```

**`PRM_LicenseService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep this in sync with `E05_PRM_LicenseService.md` (the design source). Open items (OQ‑E5‑1…OQ‑E5‑9) above still apply — **especially OQ‑E5‑2 (grain), which determines the final `key(...)`.**

---

## Appendix B — Field metadata `BusinessLicense.PRM_RecordKey__c`

> **NEW (E05‑owned).** Path: `force-app/main/default/objects/BusinessLicense/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`. **Unique External Id** is what makes the `upsert` idempotent.

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
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E05 — BusinessLicense). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

> ⚠ If **OQ‑E5‑2** adds `effectiveDate` to the grain, the **field shape is unchanged** — only the value composed in `key(...)` (Appendix A) changes.

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`. Add this `fieldPermissions` entry (the running batch user must read+edit the key to `upsert`).

```xml
<fieldPermissions>
    <field>BusinessLicense.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_LicenseServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`** (no new factory, no inline `@TestSetup` data), modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, and a **re‑run/idempotency** test. ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`) — exact names/signatures must match the factory; add them (per the `doInsert` convention) if missing. The blank‑Name negative test is **contingent on OQ‑E5‑6**.

```apex
@isTest
private class PRM_LicenseServiceTest {

    private static final Integer BULK = 251;

    // ⚠ Confirm/add these builders in PRM_TestDataFactory (do NOT inline data here):
    //   createPractitionersWithCaseManagers(count, doInsert) -> inserts Person Accounts
    //     (each with PersonContactId) + one Case Manager (IndividualApplication) each.
    //   caseManagerByAccount(List<Account>) -> Map<AccountId, CaseManagerId> from the seeded data.
    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);
    }

    // build the service params from setup records (input order)
    private static Map<String, Object> buildParams(List<Account> accts, Map<Id, Id> cmByAccount, Integer licensesPer) {
        List<Object> practitioners = new List<Object>();
        Integer n = 0;
        for (Account a : accts) {
            List<Object> lics = new List<Object>();
            for (Integer i = 0; i < licensesPer; i++) {
                lics.add(new Map<String, Object>{
                    'practitionerLicenseNumber' => 'LIC-' + n + '-' + i,
                    'licenseType'               => 'SBRD',
                    'practitionerState'         => 'PA',
                    'licenseIssuedDate'         => '12/30/2024',
                    'licenseExpirationDate'     => '02/01/2025'
                });
            }
            practitioners.add(new Map<String, Object>{
                'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '10000000' + n },
                'businessLicenses' => lics,
                'caseManagerId'    => cmByAccount.get(a.Id)
            });
            n++;
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    @isTest
    static void shouldCreateOneRowPerLicense_WhenBulk() {
        // Given
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = buildParams(accts, cm, 2);

        // When
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_LicenseService().execute(params);
        Test.stopTest();

        // Then
        Assert.areEqual(BULK * 2, [SELECT COUNT() FROM BusinessLicense],
            'Two licenses per practitioner should be created');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(),
            'Response should carry one entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        // Given
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = buildParams(accts, cm, 1);

        // When
        Test.startTest();
        new PRM_LicenseService().execute(params);   // first run
        new PRM_LicenseService().execute(params);   // re-run (idempotent upsert by key)
        Test.stopTest();

        // Then
        Assert.areEqual(BULK, [SELECT COUNT() FROM BusinessLicense],
            'Re-running with the same key must upsert, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoLicenses() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'IBC',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '1999999999' },
                    'businessLicenses' => new List<Object>()      // empty -> gated out
                }
            }
        };

        // When
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_LicenseService().execute(params);
        Test.stopTest();

        // Then
        Assert.areEqual(0, [SELECT COUNT() FROM BusinessLicense], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(),
            'Response should exclude gated-out practitioners');
    }

    @isTest
    static void shouldSetVerifiedDateAndKey_WhenBuilt() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, 1);

        // When
        Test.startTest();
        new PRM_LicenseService().execute(params);
        Test.stopTest();

        // Then
        BusinessLicense bl = [
            SELECT VerifiedDate, PRM_RecordKey__c, LicenseClass, PRM_LicenseState__c
            FROM BusinessLicense LIMIT 1
        ];
        Assert.areEqual(Date.today(), bl.VerifiedDate, 'VerifiedDate should be today');
        Assert.isNotNull(bl.PRM_RecordKey__c, 'Record key should be set');
        Assert.isTrue(bl.PRM_RecordKey__c.contains('_'), 'Key should be underscore-joined');
    }

    // ⚠ Contingent on OQ-E5-6 (Name required, no fallback): a blank license number should fail the insert.
    @isTest
    static void shouldThrow_WhenLicenseNumberBlank() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Delegated',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '1888888888' },
                    'caseManagerId'    => cm.get(a.Id),
                    'businessLicenses' => new List<Object>{
                        new Map<String, Object>{ 'licenseType' => 'DEA', 'practitionerState' => 'PA' }  // no number -> blank Name
                    }
                }
            }
        };

        // When / Then
        Test.startTest();
        try {
            new PRM_LicenseService().execute(params);
            Assert.fail('Expected a DmlException for the required Name (license number blank)');
        } catch (DmlException e) {
            Assert.isTrue(e.getMessage().length() > 0, 'DmlException should be raised for the missing required field');
        }
        Test.stopTest();
    }
}
```

**`PRM_LicenseServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ × 2 licenses → governor‑safe), re‑run idempotency, gating (empty `businessLicenses`), field/formula correctness (`VerifiedDate`, key), and the OQ‑E5‑6‑contingent blank‑Name negative. Add picklist‑value negative (OQ‑E5‑9) and date‑format (OQ‑E5‑8) cases once those are decided. Coverage target ≥ 85%.

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E5‑1). **Field + FLS first**, then the classes, then tests. *(These are reference commands, not a script to auto‑run.)*

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/BusinessLicense/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_LicenseService.cls" \
  -d "force-app/main/default/classes/PRM_LicenseServiceTest.cls" \
  -o <alias>

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_LicenseServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check the created rows + idempotency key
sf data query -o <alias> \
  -q "SELECT Id, Name, LicenseClass, PRM_LicenseState__c, VerifiedDate, PRM_RecordKey__c FROM BusinessLicense ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E5‑2 (grain) decided → `key(...)` finalized (Appendix A).
- [ ] Target org confirmed (OQ‑E5‑1); `caseManagerId` wiring confirmed (OQ‑E5‑3).
- [ ] `PRM_TestDataFactory` builders (Appendix D) exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_LicenseService` compiles; `upsert … PRM_RecordKey__c` resolves; `WITH USER_MODE` query passes for the batch user.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
