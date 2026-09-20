# E08 · `PRM_InfoCodeService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan is **self‑contained for component generation** — it specifies and includes **every artifact** needed to build E08 (see **§0 Component inventory**): the Apex class + `.cls-meta.xml` (**Appendix A**), the `PRM_InfoCodeAssignment__c.PRM_RecordKey__c` field metadata (**Appendix B**), the `PRM_AsyncJob_Access` permission‑set FLS (**Appendix C**), the Apex test class + meta (**Appendix D**), and deploy/validation steps (**Appendix E**). **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered — **especially CL‑E9 (InfoCode Id vs code — OQ‑E8‑5) and the dedupe grain (OQ‑E8‑2)** — and the target org (OQ‑E8‑1) is confirmed.
>
> **Scope:** this plan covers the **practitioner‑grain** entry point (`execute` / `createIfPresent`). The **facility‑grain** method `prepareBulkForLocations(addresses)` is **out of scope here** — it is detailed with **§E14 (Part 3)**.
>
> **Source of truth:** `E08_PRM_InfoCodeService.md` (design §1–§9, incl. the org‑validation results, CL‑E9, and the NPI‑anchored idempotency decision). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved **[OPEN]** item are **⛔ Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PRM_InfoCodeAssignment__c.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/PRM_InfoCodeAssignment__c/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E08‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` entry (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_InfoCodeService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_InfoCodeService.cls` (+ `.cls-meta.xml`) | **NEW** | Appendix A |
| 4 | `PRM_InfoCodeServiceTest` | Apex test class | `force-app/main/default/classes/PRM_InfoCodeServiceTest.cls` (+ `.cls-meta.xml`) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |
| 6 | ~~`PRM_InfoCodeSelector`~~ | — | — | **DROPPED** — CL‑E9 resolved (codes); code→Id resolution is in‑service (one bulk SOQL), mirroring E6 | §4 / Appendix A |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test` skills):** `PRM_` prefix; `with sharing`; bulkified (no SOQL/DML in loops, one bulk DML per object); CRUD/FLS via **`WITH USER_MODE`** where a query is needed; **API version 66.0**; test class `PRM_InfoCodeServiceTest` reuses **`PRM_TestDataFactory`** (never a new factory, no inline `@TestSetup` data) and uses the modern **`Assert`** class with messages; bulk path tested at **251+**. **Error handling is at the batch level** — the service lets exceptions propagate; the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain, so the service has **no inline try/catch**.

---

## 1. Confirmed requirements (from `E08_PRM_InfoCodeService.md`)

- **[CONFIRMED]** `PRM_InfoCodeService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1)**, after E1 created the Case Managers at intake. **Writes:** `PRM_InfoCodeAssignment__c` (custom object). (Design §1, §4.)
- **[CONFIRMED]** **Gated** — process **only** practitioners with a **non‑empty `infoCodes[]`**; skip the rest. (Design §1, §7.)
- **[CONFIRMED]** **Branch: BOTH** (IBC + Delegated). (Design §1.)
- **[CONFIRMED]** **No E2 dependency, no PersonContact/HealthcareProvider** — `practitionerInfo.id` (E1 Account Id) is used **directly** as `PRM_Account__c`; the simplest PractitionerBatch service. **No Account SOQL needed** (unless CL‑E9 code→Id resolution applies). (Design §1, §4.1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk (`List`), each element `{ practitionerInfo (incl. `id`, `npi`, `isActive`, `effectiveFrom`/`effectiveTo`), infoCodes[] }`, plus `params.flow`. Build all rows in memory, then **one bulk DML**. (Design §4, §5.)
- **[CONFIRMED]** **`caseManagerId` FK source:** the `PRM_AsyncJobRecords__c` row (stable batch scope), **not** the mutable `Account.PRM_CaseManager__c`. (Design §4.1.)
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — business‑confirmed, E02 §8 CL‑E2): `upsert` `PRM_InfoCodeAssignment__c` by **`PRM_RecordKey__c`**; key = `{npi}_{infoCodeId}` (delimiter `_`, blanks normalized). One assignment per practitioner per InfoCode. **Grain provisional — see OQ‑E8‑2.** (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E08‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`PRM_InfoCodeAssignment__c`** + Read+Edit FLS on `PRM_AsyncJob_Access` (base permset = Epic A; field + FLS are **E08's own**). **The field does not exist yet — creating it is a required E08 deliverable (Phase 1, T1.1).** (Design §3 WI‑1/WI‑2.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV 2026‑06‑30):** `PRM_Account__c`←accountId (→ Account), `PRM_InfoCode__c`←resolved master Id from `infoCodes[].code` (→ **`PRM_InfoCode__c`** object — CL‑E9), `PRM_EffectiveFrom__c`←`effectiveFrom`, `PRM_EffectiveTo__c`←`effectiveTo`, `PRM_CaseManager__c`←caseManagerId (→ IndividualApplication), `PRM_RecordKey__c` (computed = `{npi}_{code}`). **`PRM_Active__c` is a read‑only formula — NOT set.** (Design §6.)
- **[CONFIRMED]** **Org‑validated field facts:** object exists; **`PRM_EffectiveFrom__c` is REQUIRED** (`nillable=false`) — must be supplied or insert fails; **⚠ `PRM_Active__c` is a read‑only FORMULA** (`calculated=true`, `createable=false`) — **must NOT be set** (the original "required boolean" note was wrong; re‑validated 2026‑06‑30); `PRM_InfoCode__c` is a **lookup to `PRM_InfoCode__c`**. (Design §2 org results, §6.)
- **[CONFIRMED]** **No formulas to compute** — straight map; only `PRM_RecordKey__c` + date parse are computed. (Design §6.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** of `PRM_InfoCodeAssignment__c[]` by `PRM_RecordKey__c`; gated; returns `infoCodeAssignmentIds` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, infoCodeAssignmentIds }`. (Design §4.)
- **[CONFIRMED]** **Governor budget:** **0–1 SOQL** (only if CL‑E9 code→Id resolution is needed) + **1 bulk DML**; no DML/SOQL in loops. (Design §4.2 note.)
- **[CONFIRMED]** **Effort:** ~1.5 engineer‑days (design header — incl. CL‑E9 handling; this plan covers the practitioner‑grain method only). (Design header, §7.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set `PRM_AsyncJob_Access`), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility`), **E1** (Account + Case Manager + `PRM_AsyncJobRecords__c` seeding), the **`PractitionerBatch`** wiring, E08's own `PRM_RecordKey__c` field + FLS, and **(conditional)** a `PRM_InfoCode__c` selector if CL‑E9 = codes. **No E2 dependency.**

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL in loops; at most one bulk query (CL‑E9 resolution) + one bulk `upsert`.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch** (already‑committed chunks must not duplicate). (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch running user via `PRM_AsyncJob_Access`) — so `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E8‑4).
- **[CONFIRMED]** **Required field gates the insert:** `PRM_EffectiveFrom__c` (Date) must be set — a blank `effectiveFrom` fails the chunk (OQ‑E8‑6). *(`PRM_Active__c` is a read‑only formula — not set.)*
- **[CONFIRMED]** **Gated:** practitioners with empty `infoCodes[]` are skipped (no rows, not in the response).
- **[CONFIRMED]** **CL‑E9 RESOLVED — the payload sends `code`, not an Id.** Each `infoCodes[]` element is `{ infoCode, code }`; `code` = `PRM_InfoCode__c.PRM_Code__c` (unique). The service bulk‑resolves the master Id from `code` (**one SOQL**, `WHERE PRM_Code__c IN :codes`) and skips unresolved codes. No separate `PRM_InfoCodeSelector` component — resolution is in‑service (mirrors E6 degree/institution). Governor cost is **1 SOQL + 1 bulk DML**.

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds `PRM_InfoCodeAssignment__c[]` per the §6 map; **1 bulk DML** regardless of chunk size.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running `execute()` on the same chunk produces **no duplicates** (contingent on the confirmed grain — OQ‑E8‑2).
- **[CONFIRMED]** `caseManagerId` FK sourced from `PRM_AsyncJobRecords__c` (not the mutable Account back‑link).
- **[CONFIRMED]** Required field satisfied: `PRM_EffectiveFrom__c` set. *(`PRM_Active__c` is a read‑only formula — not set.)*
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, infoCodeAssignmentIds }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners × multiple infoCodes) asserting governor‑safe DML counts, (b) a **re‑run/idempotency** test, and (c) a **required‑field negative** (blank `effectiveFrom` → `DmlException`); Test Evidence Report + human sign‑off (Epic A §A7) before promotion.
- **[CONFIRMED]** Field API names/types validated against the org (already done, IBXDEV01 — re‑confirm on the target org, OQ‑E8‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E8‑1…OQ‑E8‑7)
- **T0.1 — Target org** (OQ‑E8‑1) for deploy + tests. Completion: org confirmed.
- **T0.2 — CL‑E9 ✅ RESOLVED (codes).** The payload sends `{ infoCode, code }` (no Id); `code` = `PRM_InfoCode__c.PRM_Code__c` (unique). Code→Id resolution is **in‑service** (one bulk SOQL); component #6 dropped; governor cost = 1 SOQL + 1 DML. Completion: done.
- **T0.3 — Confirm the dedupe grain** (OQ‑E8‑2): is `npi_infoCodeId` unique per practitioner, or can the same InfoCode legitimately repeat with different effective periods (→ add `effectiveFrom` to the key)? Validation: business sign‑off (org data is test‑polluted). Completion: grain confirmed → Appendix A `key(...)` finalized.
- **T0.4 — Verify dependencies present on `main`:** `PRM_ServiceBase`; `PRM_FormSubUtility`; E1 (Account + Case Manager + `PRM_AsyncJobRecords__c` seeding); the permission set `PRM_AsyncJob_Access` (base). *(E08's `PRM_RecordKey__c` on `PRM_InfoCodeAssignment__c` is **NOT pre‑existing** — created in Phase 1, T1.1.)* Completion: all present (or gaps logged).
- **T0.5 — Resolve open business/data items:** no‑NPI policy (OQ‑E8‑4), `PRM_EffectiveFrom__c` always present (OQ‑E8‑6), `isActive`/`effectiveFrom`/`effectiveTo` source (OQ‑E8‑7), `caseManagerId` wiring (OQ‑E8‑3). Completion: each decided or explicitly deferred.

### Phase 1 — E08 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `PRM_InfoCodeAssignment__c`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (design §3 WI‑1/WI‑2). **Confirmed: the field does not exist yet — this task creates it (E08‑owned).**
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS created & deployed.
  - Dependencies: T0.1. Prerequisites: Phase 0. Impacted: `objects/PRM_InfoCodeAssignment__c/fields/PRM_RecordKey__c.field-meta.xml`, `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` (Appendices B–C).
  - Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing data (field new/empty → low; object has 1,317 rows but the field is empty). Completion: field + FLS deployed.

### Phase 2 — `PRM_InfoCodeService` core *(M2)*
- **T2.1 — Class + `execute` + `PractUow`; parse + gate**
  - Purpose: parse `practitioners[]`; keep only gated practitioners (non‑empty `infoCodes`); read `accountId` directly; obtain `caseManagerId` from the batch context (`PRM_AsyncJobRecords__c` — OQ‑E8‑3).
  - Outcome: Appendix A step 1.
  - Dependencies: T0.4, Phase 1. Impacted: `classes/PRM_InfoCodeService.cls` (+ `…Test.cls`).
  - Validation: compiles; gating correct. Testing: unit (parse + gate). Risks: **[RISK]** `caseManagerId` wiring (OQ‑E8‑3). Completion: parse + gate green.
- **T2.2 — (Conditional) CL‑E9 code→Id resolution**
  - Purpose: if the payload sends codes (OQ‑E8‑5), bulk‑resolve `PRM_InfoCode__c` Ids via `PRM_InfoCodeSelector` (one query, `WITH USER_MODE`).
  - Outcome: a `Map<code, Id>`; or **skipped** if Ids are sent.
  - Dependencies: T0.2. Impacted: `classes/PRM_InfoCodeSelector.cls` (conditional). Validation: one bulk query; no loop SOQL. Risks: **[RISK]** unknown payload shape. Completion: resolution path decided + implemented (or confirmed not needed).
- **T2.3 — Build assignments + `PRM_RecordKey__c` + required fields**
  - Purpose: in‑memory `PRM_InfoCodeAssignment__c` per the §6 map; `PRM_Active__c` via `toBool`; `PRM_EffectiveFrom__c`/`To`; NPI‑anchored key.
  - Outcome: Appendix A step 3 + `buildAssignment`/`key`.
  - Dependencies: T2.1, T0.3 (grain). Validation: field‑by‑field unit assertions; key string correct. Testing: builder unit (active true/false; blank dates → required‑field behavior). Risks: **[RISK]** `PRM_EffectiveFrom__c` blank (OQ‑E8‑6); grain (OQ‑E8‑2). Completion: builder unit‑tested.
- **T2.4 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; per‑practitioner response (gated subset, input order).
  - Outcome: Appendix A steps 4–5.
  - Dependencies: T2.3. Validation: rows have correct FKs + key; DML count = 1; response shape. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildAssignment` (InfoCode resolved from code, effective dates, key), `key` (blank normalization), gating, unresolved‑code skip.
- **T3.2 Bulk/governor:** 251+ practitioners × multiple infoCodes → ≤1 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → assignment count unchanged (upsert by key).
- **T3.4 Negative/edge:** empty `infoCodes` (skipped), **blank `effectiveFrom` → `DmlException`** (PRM_EffectiveFrom__c required, OQ‑E8‑6), no‑NPI (per OQ‑E8‑4), (if CL‑E9=codes) unknown code resolution.
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `PRM_InfoCodeAssignment__c` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E8‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/infocode-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. Commit prefix `[E8]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RESOLVED] CL‑E9 — code, not Id (OQ‑E8‑5).** The payload sends `{ infoCode, code }`; `code` = `PRM_InfoCode__c.PRM_Code__c` (unique). The service bulk‑resolves the master Id from `code` in‑service (one SOQL, `WHERE PRM_Code__c IN :codes`) and skips unresolved codes — mirroring E6's degree/institution resolution. **No separate `PRM_InfoCodeSelector`** (component #6 dropped). Governor budget = 1 SOQL + 1 bulk DML.
- **[RISK] `PRM_EffectiveFrom__c` is required (OQ‑E8‑6).** A blank `effectiveFrom` fails the whole chunk on insert. Confirm intake guarantees it, or define a default; otherwise add fail‑fast validation at intake.
- **[RECOMMENDATION] Dedupe grain (OQ‑E8‑2).** Org data is test‑polluted (same `Account + InfoCode` repeats 10×). The provisional `npi_infoCodeId` assumes an InfoCode can't legitimately repeat with different effective periods; confirm with business. If renewals/periods matter, add `effectiveFrom` to the key (only the `key(...)` line changes).
- **[RECOMMENDATION] `caseManagerId` wiring (OQ‑E8‑3).** Cleanest is for `PractitionerBatch` to **inject a resolved `caseManagerId` per practitioner node** (from `PRM_AsyncJobRecords__c`); the §5 payload doesn't carry it today.
- **[RECOMMENDATION] No Account query needed.** Unlike E5/E6/E7, E8 uses `accountId` directly as `PRM_Account__c` — keep it that way (0 SOQL unless CL‑E9 resolution). Don't add a PersonContact lookup the design doesn't require.
- **[RECOMMENDATION] Partial‑failure semantics.** With one bulk `upsert`, confirm all‑or‑nothing (chunk rolls back on error) for the pilot vs `Database.upsert(rows, false)` + per‑row handling.

---

## 6. Gaps & hidden dependencies

- **CL‑E9 payload shape (OQ‑E8‑5)** — Ids vs codes; gates the selector component + SOQL count.
- **Dedupe grain (OQ‑E8‑2)** — gates the key + idempotency test.
- **Target org (OQ‑E8‑1)** — gates deploy/test.
- **E08 `PRM_RecordKey__c` + FLS** — E08's own; **not yet created → built in Phase 1 (T1.1)**.
- **`caseManagerId` wiring (OQ‑E8‑3)** — batch must supply it from `PRM_AsyncJobRecords__c`; not in the §5 payload today.
- **`PRM_EffectiveFrom__c` required (OQ‑E8‑6)** — intake must guarantee it.
- **E1** — Account + Case Manager + `PRM_AsyncJobRecords__c` seeding.
- **(Conditional) `PRM_InfoCodeSelector`** — only if CL‑E9 = codes.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E8‑1 — Target org** for deploy/test. *(Blocks Phase 0/1/4.)*
- **OQ‑E8‑2 — InfoCode dedupe grain.** `npi_infoCodeId` only, or `+ effectiveFrom` (can the same InfoCode repeat with different effective periods)? *(Org data test‑polluted; confirm with business.)* **Gates the key + Appendix A `key(...)`.**
- **OQ‑E8‑3 — `caseManagerId` source/wiring.** Confirm `PractitionerBatch` injects a resolved `caseManagerId` per practitioner node (from `PRM_AsyncJobRecords__c`), vs an in‑service lookup. *(Appendix A assumes per‑node injection — flagged.)*
- **OQ‑E8‑4 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key.
- **OQ‑E8‑5 (CL‑E9) — ✅ RESOLVED: codes.** The payload sends `{ infoCode, code }` (no Id); `code` = `PRM_InfoCode__c.PRM_Code__c` (unique). The service resolves the master Id in‑bulk (one SOQL) and skips unresolved codes. **No separate selector component** (#6 dropped) — resolution is in‑service, mirroring E6.
- **OQ‑E8‑6 — `PRM_EffectiveFrom__c` always present?** Required field — confirm intake guarantees it, or define a default.
- **OQ‑E8‑7 — `isActive` / `effectiveFrom` / `effectiveTo` source.** Confirm these are practitioner‑level (`practitionerInfo`), not per‑infoCode.

*(Already resolved: org validation done — object + fields exist, types confirmed; new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E08's `PRM_RecordKey__c` on `PRM_InfoCodeAssignment__c` is NOT yet created → built as E08 Phase 1, T1.1**.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | CL‑E9 payload sends codes, not Ids → missing selector / wrong FK | Medium | High | OQ‑E8‑5 before build; conditional `PRM_InfoCodeSelector` (comp #6) |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | `PRM_EffectiveFrom__c` blank → chunk insert fails | Medium | High | OQ‑E8‑6; intake validation/default; T3.4 |
| R‑4 | Dedupe grain wrong (periods collapse) | Low–Med | Medium | OQ‑E8‑2 business decision; only `key(...)` changes |
| R‑5 | `caseManagerId` wiring (mutable Account vs job record) | Medium | High | OQ‑E8‑3; batch injects from `PRM_AsyncJobRecords__c` |
| R‑6 | No target org → can't deploy/test | Medium | High | OQ‑E8‑1 |
| R‑7 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner coordination |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. OQ‑E8‑5 CL‑E9 + OQ‑E8‑2 grain) → 1 (**create the `PRM_RecordKey__c` field + FLS**) → 2 (service; + conditional selector) → 3 → 4 → 5. `PractitionerBatch` wiring pairs with E8.
- **Effort:** within the ~1.5 d catalog estimate — class + builder + key ~0.5 · conditional CL‑E9 selector ~0.25 (if needed) · tests (bulk/idempotency/required‑field/negative) ~0.4 · evidence/VCS folded in. *(The facility‑grain `prepareBulkForLocations` is separate — with §E14.)*
- **Depends on:** Epic A (permission set) + Epic B + E1 on `main`, plus `PractitionerBatch`. **No E2 dependency.** **Blocks/feeds:** nothing downstream consumes E8 outputs directly (InfoCodeAssignment is a leaf for the practitioner graph).

---

## 10. What happens after sign‑off

Resolve OQ‑E8‑1…OQ‑E8‑7 — **CL‑E9 (OQ‑E8‑5) and the grain (OQ‑E8‑2) are the gates**. Then: **create + deploy the E08 `PRM_RecordKey__c` field + FLS (Phase 1 — the field does not exist yet)** → build the service per **Appendix A** (parse + gate → optional CL‑E9 resolution → build + key → one bulk `upsert` → response) → tests (unit/bulk/idempotency/required‑field/negative) → Test Evidence Report → human governance sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E8‑1), CL‑E9 (OQ‑E8‑5), and the grain (OQ‑E8‑2) are confirmed.**

---

## Appendix A — Apex class `PRM_InfoCodeService` (+ meta)

> Full `PRM_InfoCodeService` (expands `E08_PRM_InfoCodeService.md` §4.2) — the **practitioner‑grain** entry point. **Depends on** `PRM_ServiceBase`. **Provisional:** the `key(...)` reflects the current grain (`npi_infoCodeId`) — finalize after OQ‑E8‑2. **CL‑E9:** assumes `infoCodes[].id` are `PRM_InfoCode__c` record Ids; the code→Id branch (OQ‑E8‑5) is marked and would use a `PRM_InfoCodeSelector`. `caseManagerId` is read from the batch‑injected per‑practitioner node (OQ‑E8‑3). The class `.cls-meta.xml` follows; field + permission‑set metadata are in **Appendices B–C**. *(The facility‑grain `prepareBulkForLocations(addresses)` is out of scope here — with §E14.)*

```apex
public with sharing class PRM_InfoCodeService extends PRM_ServiceBase {

    // one per GATED practitioner (non-empty infoCodes), in input order
    @TestVisible
    private class PractUow {
        Map<String, Object> p;          // practitionerInfo (id, npi, isActive, effectiveFrom/To)
        List<Object> infoCodes;         // infoCodes[]
        Id accountId;                   // = practitionerInfo.id (E1) -> PRM_Account__c (used directly)
        Id caseManagerId;               // from PRM_AsyncJobRecords__c (batch context) — OQ-E8-3
        List<PRM_InfoCodeAssignment__c> rows = new List<PRM_InfoCodeAssignment__c>();
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');                       // IBC vs Delegated (context)
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) build UoWs ONLY for gated practitioners (no DML/SOQL in loop)
        List<PractUow> uows = new List<PractUow>();
        if (practitioners != null) {
            for (Object o : practitioners) {
                Map<String, Object> app = (Map<String, Object>) o;
                List<Object> codes = (List<Object>) app.get('infoCodes');
                if (codes == null || codes.isEmpty()) continue;          // GATED: skip
                PractUow u = new PractUow();
                u.p             = (Map<String, Object>) app.get('practitionerInfo');
                u.infoCodes     = codes;
                u.accountId     = (Id) u.p.get('id');                    // used directly as PRM_Account__c
                u.caseManagerId = (Id) app.get('caseManagerId');         // batch-injected (OQ-E8-3)
                uows.add(u);
            }
        }
        if (uows.isEmpty()) {
            response = new Map<String, Object>{ 'practitioners' => new List<Object>() };
            return response;
        }

        // 2) CL-E9 (RESOLVED): payload sends { infoCode, code } (no Id). Collect all codes ->
        //    ONE bulk query PRM_InfoCode__c by the unique PRM_Code__c -> Map<code, Id>.
        Map<String, Id> infoCodeIdByCode = resolveInfoCodeIds(uows);

        // 3) build assignments (no DML/SOQL in loop); key = {npi}_{code} (§2); skip unresolved codes
        List<PRM_InfoCodeAssignment__c> allRows = new List<PRM_InfoCodeAssignment__c>();
        for (PractUow u : uows) {
            String npi   = (String) u.p.get('npi');
            Date effFrom = parseDate((String) u.p.get('effectiveFrom'));   // REQUIRED on the object (OQ-E8-6)
            Date effTo   = parseDate((String) u.p.get('effectiveTo'));
            for (Object co : u.infoCodes) {
                String code = (String) ((Map<String, Object>) co).get('code');  // unique PRM_Code__c (CL-E9)
                Id infoCodeId = infoCodeIdByCode.get(code);
                if (infoCodeId == null) continue;                                // skip unresolved code
                PRM_InfoCodeAssignment__c row = buildAssignment(u, infoCodeId, npi, code, effFrom, effTo);
                u.rows.add(row);
                allRows.add(row);
            }
        }

        // 4) ONE bulk upsert by the External Id (idempotent — §7)
        upsert allRows PRM_RecordKey__c;     // populates Id on the same instances held by the UoWs

        // 5) response (input order; gated subset only)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (PractUow u : uows) {
            List<Id> ids = new List<Id>();
            for (PRM_InfoCodeAssignment__c a : u.rows) ids.add(a.Id);
            results.add(new Map<String, Object>{
                'accountId'             => u.accountId,
                'infoCodeAssignmentIds' => ids
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── code -> master Id resolution (ONE bulk SOQL; in-service, mirrors E6) ──
    private Map<String, Id> resolveInfoCodeIds(List<PractUow> uows) {
        Set<String> codes = new Set<String>();
        for (PractUow u : uows) {
            for (Object co : u.infoCodes) {
                String code = (String) ((Map<String, Object>) co).get('code');
                if (String.isNotBlank(code)) codes.add(code);
            }
        }
        Map<String, Id> byCode = new Map<String, Id>();
        if (codes.isEmpty()) return byCode;
        for (PRM_InfoCode__c m : [SELECT Id, PRM_Code__c FROM PRM_InfoCode__c WHERE PRM_Code__c IN :codes]) {
            byCode.put(m.PRM_Code__c, m.Id);
        }
        return byCode;
    }

    // ── builder (pure in-memory; field map per §6; no formulas) ──
    private PRM_InfoCodeAssignment__c buildAssignment(
            PractUow u, Id infoCodeId, String npi, String code, Date effFrom, Date effTo) {
        PRM_InfoCodeAssignment__c a = new PRM_InfoCodeAssignment__c();
        a.PRM_Account__c       = u.accountId;                 // -> Account
        a.PRM_InfoCode__c      = infoCodeId;                  // resolved from code (CL-E9)
        // PRM_Active__c is a READ-ONLY formula (org-validated) — do NOT set.
        a.PRM_EffectiveFrom__c = effFrom;                     // REQUIRED (OQ-E8-6)
        a.PRM_EffectiveTo__c   = effTo;
        a.PRM_CaseManager__c   = u.caseManagerId;             // -> IndividualApplication
        a.PRM_RecordKey__c     = key(new List<String>{ npi, code });  // {npi}_{code} (§2) — grain OQ-E8-2
        return a;
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

**`PRM_InfoCodeService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep this in sync with `E08_PRM_InfoCodeService.md` (the design source). Open items (OQ‑E8‑1…OQ‑E8‑7) above still apply — **especially OQ‑E8‑5 (CL‑E9) and OQ‑E8‑2 (grain).**

---

## Appendix B — Field metadata `PRM_InfoCodeAssignment__c.PRM_RecordKey__c`

> **NEW (E08‑owned).** Path: `force-app/main/default/objects/PRM_InfoCodeAssignment__c/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`. **Unique External Id** is what makes the `upsert` idempotent.

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
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E08 — PRM_InfoCodeAssignment__c). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

> ⚠ If **OQ‑E8‑2** adds `effectiveFrom` to the grain, the **field shape is unchanged** — only the value composed in `key(...)` (Appendix A) changes.

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`. Add this `fieldPermissions` entry (the running batch user must read+edit the key to `upsert`).

```xml
<fieldPermissions>
    <field>PRM_InfoCodeAssignment__c.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_InfoCodeServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`** (no new factory, no inline `@TestSetup` data), modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, and a **re‑run/idempotency** test. ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`, `createInfoCodes`) — exact names/signatures must match the factory; add them (per the `doInsert` convention) if missing.

```apex
@isTest
private class PRM_InfoCodeServiceTest {

    private static final Integer BULK = 251;
    private static final Integer CODES_PER = 2;

    // ⚠ Confirm/add these builders in PRM_TestDataFactory (do NOT inline data here):
    //   createPractitionersWithCaseManagers(count, doInsert) -> Person Accounts + a Case Manager each
    //   caseManagerByAccount(List<Account>) -> Map<AccountId, CaseManagerId>
    //   createInfoCodes(count, doInsert) -> List<PRM_InfoCode__c>
    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);
        PRM_TestDataFactory.createInfoCodes(CODES_PER, true);
    }

    private static Map<String, Object> buildParams(
            List<Account> accts, Map<Id, Id> cmByAccount, List<PRM_InfoCode__c> codes,
            String effectiveFrom) {
        List<Object> infoCodeNodes = new List<Object>();
        for (PRM_InfoCode__c c : codes) {
            // CL-E9: payload sends { infoCode, code } (no Id); service resolves by PRM_Code__c
            infoCodeNodes.add(new Map<String, Object>{ 'infoCode' => c.PRM_InfoCode__c, 'code' => c.PRM_Code__c });
        }
        List<Object> practitioners = new List<Object>();
        Integer n = 0;
        for (Account a : accts) {
            practitioners.add(new Map<String, Object>{
                'practitionerInfo' => new Map<String, Object>{
                    'id' => a.Id, 'npi' => '10000000' + n,
                    'isActive' => true, 'effectiveFrom' => effectiveFrom, 'effectiveTo' => ''
                },
                'infoCodes'     => infoCodeNodes,
                'caseManagerId' => cmByAccount.get(a.Id)
            });
            n++;
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    @isTest
    static void shouldCreateOneRowPerInfoCode_WhenBulk() {
        // Given
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        List<PRM_InfoCode__c> codes = [SELECT Id, PRM_Code__c, PRM_InfoCode__c FROM PRM_InfoCode__c];
        Map<String, Object> params = buildParams(accts, cm, codes, '12/30/2024');

        // When
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_InfoCodeService().execute(params);
        Test.stopTest();

        // Then
        Assert.areEqual(BULK * CODES_PER, [SELECT COUNT() FROM PRM_InfoCodeAssignment__c],
            'One assignment per (practitioner, infoCode) should be created');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(),
            'Response should carry one entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        // Given
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        List<PRM_InfoCode__c> codes = [SELECT Id, PRM_Code__c, PRM_InfoCode__c FROM PRM_InfoCode__c];
        Map<String, Object> params = buildParams(accts, cm, codes, '12/30/2024');

        // When
        Test.startTest();
        new PRM_InfoCodeService().execute(params);   // first run
        new PRM_InfoCodeService().execute(params);   // re-run (idempotent upsert by key)
        Test.stopTest();

        // Then
        Assert.areEqual(BULK * CODES_PER, [SELECT COUNT() FROM PRM_InfoCodeAssignment__c],
            'Re-running with the same key must upsert, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoInfoCodes() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'IBC',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{
                        'id' => a.Id, 'npi' => '1999999999', 'isActive' => true, 'effectiveFrom' => '12/30/2024'
                    },
                    'infoCodes' => new List<Object>()      // empty -> gated out
                }
            }
        };

        // When
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_InfoCodeService().execute(params);
        Test.stopTest();

        // Then
        Assert.areEqual(0, [SELECT COUNT() FROM PRM_InfoCodeAssignment__c], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(),
            'Response should exclude gated-out practitioners');
    }

    @isTest
    static void shouldSetActiveAndKey_WhenBuilt() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        List<PRM_InfoCode__c> codes = [SELECT Id, PRM_Code__c, PRM_InfoCode__c FROM PRM_InfoCode__c LIMIT 1];
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, codes, '12/30/2024');

        // When
        Test.startTest();
        new PRM_InfoCodeService().execute(params);
        Test.stopTest();

        // Then
        PRM_InfoCodeAssignment__c row = [
            SELECT PRM_EffectiveFrom__c, PRM_RecordKey__c, PRM_Account__c, PRM_InfoCode__c
            FROM PRM_InfoCodeAssignment__c LIMIT 1
        ];
        Assert.isNotNull(row.PRM_InfoCode__c, 'PRM_InfoCode__c should be resolved from the code');
        Assert.areEqual(a.Id, row.PRM_Account__c, 'PRM_Account__c should be the practitioner Account');
        Assert.isNotNull(row.PRM_RecordKey__c, 'Record key should be set');
        Assert.isTrue(row.PRM_RecordKey__c.contains('_'), 'Key should be underscore-joined');
    }

    // PRM_EffectiveFrom__c is required (org-validated) -> blank effectiveFrom must fail the insert.
    @isTest
    static void shouldThrow_WhenEffectiveFromBlank() {
        // Given
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a });
        List<PRM_InfoCode__c> codes = [SELECT Id, PRM_Code__c, PRM_InfoCode__c FROM PRM_InfoCode__c LIMIT 1];
        Map<String, Object> params = buildParams(new List<Account>{ a }, cm, codes, '');  // blank effectiveFrom

        // When / Then
        Test.startTest();
        try {
            new PRM_InfoCodeService().execute(params);
            Assert.fail('Expected a DmlException for the required PRM_EffectiveFrom__c');
        } catch (DmlException e) {
            Assert.isTrue(e.getMessage().length() > 0, 'DmlException should be raised for the missing required field');
        }
        Test.stopTest();
    }
}
```

**`PRM_InfoCodeServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ × 2 infoCodes → governor‑safe), re‑run idempotency, gating (empty `infoCodes`), field/key correctness (`PRM_InfoCode__c` resolved from `code`, `PRM_Account__c`, key), unresolved‑code skip, and the required‑field negative (blank `effectiveFrom` → `DmlException`). Coverage target ≥ 85%.

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E8‑1). **Field + FLS first**, then the classes, then tests. *(Reference commands, not a script to auto‑run.)*

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/PRM_InfoCodeAssignment__c/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service (+ conditional selector) + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_InfoCodeService.cls" \
  -d "force-app/main/default/classes/PRM_InfoCodeServiceTest.cls" \
  -o <alias>
#   (+ PRM_InfoCodeSelector.cls only if CL-E9 = codes — OQ-E8-5)

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_InfoCodeServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check the created rows + idempotency key
sf data query -o <alias> \
  -q "SELECT Id, PRM_Account__c, PRM_InfoCode__c, PRM_Active__c, PRM_EffectiveFrom__c, PRM_RecordKey__c FROM PRM_InfoCodeAssignment__c ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E8‑5 (CL‑E9 Id vs code) decided → selector built or confirmed not needed.
- [ ] OQ‑E8‑2 (grain) decided → `key(...)` finalized (Appendix A).
- [ ] Target org confirmed (OQ‑E8‑1); `caseManagerId` wiring confirmed (OQ‑E8‑3); `effectiveFrom` guaranteed (OQ‑E8‑6).
- [ ] `PRM_TestDataFactory` builders (Appendix D) exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_InfoCodeService` compiles; `upsert … PRM_RecordKey__c` resolves.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
