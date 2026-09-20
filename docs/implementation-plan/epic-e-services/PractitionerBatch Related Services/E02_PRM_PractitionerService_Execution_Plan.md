# E02 · `PRM_PractitionerService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review. NO code generated.** Per the build instruction, this plan **does not** generate code, scripts, configs, commands, or implementation artifacts. It reviews and expands `E02_PRM_PractitionerService.md` into a phased execution plan only. **Nothing is built or deployed** until this plan is reviewed, the Open Questions (§7) are answered, and the target org (OQ‑E2‑1) is confirmed. *(The prerequisite **E02 schema work items — §3 / Phase 1 — are already deployed ✅**. These are the `PRM_RecordKey__c` fields + FLS, which belong to **E02's scope, not Epic A**; only a presence re‑check (T0.3) remains.)*
>
> **Source of truth:** `E02_PRM_PractitionerService.md` (design §1–§9, incl. CL‑E1 and the CL‑E2 **NPI‑uniqueness** resolution — business‑confirmed NPI is unique, so the dedupe key stays NPI‑anchored). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved **[OPEN]** item are **⛔ Pending Clarification**.
>
> **Note on reference implementation:** unlike `E01_PRM_CaseService.md` (which carries a complete `§2.2` class), the E02 design currently provides only a **skeleton** (`§4.2`, with comment placeholders for steps 3–6). Producing a full class would be code generation, which this instruction forbids — so **no Appendix A class is included here**. If you want a full inline reference implementation added (as was later done for E01/E19), say so and I'll produce it as a follow‑up (see OQ‑E2‑10).

---

## 1. Confirmed requirements (from `E02_PRM_PractitionerService.md`)

- **[CONFIRMED]** `PRM_PractitionerService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1)** — *not* at intake. By the time it runs, E1 has created (per practitioner) the Person `Account`, `Case`, `IndividualApplication` (= Case Manager), and seeded one `PRM_AsyncJobRecords__c` per Case Manager. (Design §1, §4.)
- **[CONFIRMED]** **Writes** four objects per practitioner: `HealthcareProvider` → `HealthcareProviderNpi` → `Identifier[]` → `HealthcareProviderTaxonomy[]`. E2 owns `HealthcareProviderTaxonomy` (supersedes the standalone E4 for Practitioner Creation). (Design §1 scope note, §4.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk (`List`), each element `{ practitionerInfo (incl. `id` = **E1 Account Id**, `npi`, …), taxonomies[], identifiers[] }`, plus `params.flow` (IBC vs Delegated). Build all records in memory, then **one bulk DML per object type**. (Design §4, §4.1, §5.)
- **[CONFIRMED]** **Correlation / Id resolution:** `practitionerInfo.id` = Account Id is the **FK correlation key** (distinct from the **dedupe anchor**, which is `npi` — §2). `practitionerId` (`PersonContactId`) resolved via **one bulk Account query**. A per‑practitioner **`PractUow`** reference wrapper carries Ids forward across inserts (E1 `AppUow` pattern). (Design §4.1, §4.2.)
- **[CONFIRMED]** **`caseManagerId` FK source:** the `PRM_CaseManager__c` FK on E2's records is taken from the **`PRM_AsyncJobRecords__c`** row (stable, batch scope) — **not** `Account.PRM_CaseManager__c` (mutable "latest" pointer). (Design §4.1 note, §8.)
- **[CONFIRMED]** **Idempotency (re‑run safe), NPI‑anchored:** NPI is **unique (business‑confirmed — CL‑E2)**, so keys anchor on `npi`:
  - `HealthcareProvider` → `upsert` by `PRM_RecordKey__c = {npi}`
  - `Identifier` → `upsert` by `PRM_RecordKey__c = {npi}_{type}_{idValue}`
  - `HealthcareProviderTaxonomy` → `upsert` by `PRM_RecordKey__c = {npi}_{taxonomyCode}`
  - `HealthcareProviderNpi` → **existence pre‑check on `Npi`** (no new field); insert only NPIs not already present. (Design §2, §7.)
- **[CONFIRMED]** **Prerequisite schema (E02 declarative work items) — ✅ already deployed:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **HealthcareProvider / Identifier / HealthcareProviderTaxonomy** + Read+Edit FLS on the permission set **`PRM_AsyncJob_Access`** (the base permission set is Epic A's; **the `PRM_RecordKey__c` fields + their FLS are E02's own**). HealthcareProviderNpi gets **no** new field (deduped via the `Npi` pre‑check; a unique constraint on `Npi` is **optional** — OQ). Remaining action: a presence re‑check (T0.3). (Design §3 WI‑1…WI‑5, §8.)
- **[CONFIRMED]** **DML order** (dependency order; HCP first because it feeds E7): (1) upsert `HealthcareProvider` → (2) pre‑check + insert `HealthcareProviderNpi` → (3) upsert `Identifier[]` → (4) upsert `HealthcareProviderTaxonomy[]`. **No circular FKs** (all reference E1 records) → no back‑link updates. `upsert` populates `Id` on the passed instances → `PractUow` correlation holds; HCP Id feeds E7. (Design §6 ordering note, §7.)
- **[CONFIRMED]** **In‑service formulas:** `HCPName` (NameNormalize first+last), `HCPStatus` (Active/InActive), NPI gating (`existingHcpNpiId` → null active/effective), Identifier `RecordTypeId` (`PRM_Practitioner` via cached describe) + `PRM_Pending__c` (`type != 'Document'`), taxonomy `FinalName`/`IsPrimaryTaxonomy`/`ProviderType` (primary‑only), and `PRM_RecordKey__c`. (Design §6, formulas subsection.)
- **[CONFIRMED]** **Branching:** IBC vs Delegated handled internally via `flow`; both branches build NPI + Identifier (per the ratified CL‑E1 decision). IBC feeds taxonomy/license directly; Delegated routes taxonomy via transform + adds `ProviderType`/`Identifiers`/`BoardCertifications`. (Design §1, §6 IP grounding.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, healthcareProviderId, healthcareProviderNpiId, identifierIds, taxonomyIds }` — feeds E5/E6/E7/E8/E11. (Design §4, §7.)
- **[CONFIRMED]** **Governor budget:** ~2 SOQL (Account resolution + NPI pre‑check; +1 taxonomy‑ref selector) + **4 bulk DML**, constant regardless of chunk size; no DML/SOQL/describe in loops. (Design §4.2 note.)
- **[CONFIRMED]** **Effort:** ~2.5 engineer‑days (design header / Plan catalog).
- **[CONFIRMED]** **Depends on:** Epic A (objects/RTs + the base permission set `PRM_AsyncJob_Access`), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility` incl. `recordTypeId` + `NameNormalize`), Epic D (`PRM_TaxonomySelector`), **E1** (creates Account/Contact/CaseManager + seeds `PRM_AsyncJobRecords__c`), and the **`PractitionerBatch`** wiring (Epic C/E). E2's own `PRM_RecordKey__c` fields + FLS (§3 / Phase 1) are **already deployed ✅**. **Note: E2 does not call CMA** — the Practitioner CMA is created by E1.

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL/describe in loops; RT Ids + taxonomy refs resolved once in bulk; one bulk DML per object type.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**. Within one chunk an unhandled exception rolls back that chunk; the idempotency design exists because **manual retry re‑runs the whole batch**, including already‑committed chunks. (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch running user via `PRM_AsyncJob_Access`); the `PRM_RecordKey__c` FLS is **already on the permission set** (Phase 1 deployed).
- **[CONFIRMED]** Idempotency is **NPI‑anchored** (NPI unique — CL‑E2); a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E2‑7).
- **[CONFIRMED]** **New fields** (unlike E1): `PRM_RecordKey__c` on 3 objects — **E02's own, already deployed ✅**. HealthcareProviderNpi uses an existing‑field pre‑check (no new field).
- **[CONFIRMED]** HCP must be upserted **before** NPI/Identifier/Taxonomy (HCP Id feeds E7 BoardCertification).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; builds HCP/NPI/Identifier[]/Taxonomy[] per practitioner with correct field maps + in‑service formulas; **4 bulk DML** regardless of chunk size.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c` (HCP/Identifier/Taxonomy) + `Npi` pre‑check (NPI object); re‑running `execute()` on the same chunk produces **no duplicates**.
- **[CONFIRMED]** **No‑NPI policy (CL‑E2):** NPI is unique (business‑confirmed); a practitioner must have an NPI for the key to be valid (reject‑at‑intake recommended) — see OQ‑E2‑7.
- **[CONFIRMED]** `caseManagerId` FK sourced from `PRM_AsyncJobRecords__c` (not the mutable Account back‑link).
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, healthcareProviderId, healthcareProviderNpiId, identifierIds, taxonomyIds }` in input order (feeds E5/E6/E7/E8/E11).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners) asserting governor‑safe DML counts and (b) a **re‑run/idempotency** test (execute twice → counts unchanged), plus a **key‑correctness** test (distinct NPIs → distinct graphs; same NPI re‑submit → upsert, no dup); Test Evidence Report + human sign‑off (Epic A §A7) before promotion.
- **[CONFIRMED]** Field API names/types validated against the org (not yet done — OQ‑E2‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E2‑1…OQ‑E2‑9)
- **T0.1 — Target org** (OQ‑E2‑1) for schema validation, deploy, and tests. Completion: org confirmed.
- **T0.2 — Org schema validation (design §8, not yet run).**
  - Purpose: verify field API names, types, nillability, required flags, picklist values, and RT existence for `HealthcareProvider` / `HealthcareProviderNpi` / `Identifier` / `HealthcareProviderTaxonomy` (as done for E1).
  - Outcome: a validated field‑fact set; the §6 field maps confirmed or corrected.
  - Dependencies: T0.1. Validation: `sf` describe / SOQL. Testing: n/a (analysis). Risks: **[RISK]** map drift if fields differ. Completion: §6 maps reconciled to the org.
- **T0.3 — Verify upstream dependencies present on `main`:** the **deployed E02 `PRM_RecordKey__c` fields + their `PRM_AsyncJob_Access` FLS (Phase 1)**; `PRM_ServiceBase`; `PRM_FormSubUtility` (with `NameNormalize` **and** `recordTypeId`); `PRM_TaxonomySelector` (Epic D); Identifier RT `PRM_Practitioner` active; E1 in place (Account/Case/IA + `PRM_AsyncJobRecords__c` seeding). Validation: describe / deploy dry‑run. Completion: all present (or gaps logged).
- **T0.4 — Resolve open business/data items:** missing‑NPI policy (OQ‑E2‑7), CL‑E1 IBC NPI/Identifier values (OQ‑E2‑4), taxonomy resolution path (OQ‑E2‑5), existing‑NPI gating scope (OQ‑E2‑6), batch payload enrichment + `caseManagerId` source wiring (OQ‑E2‑2/3). Completion: each decided or explicitly deferred.

### Phase 1 — E02 schema prerequisites (declarative) *(M1)* — ✅ DONE (already deployed)
> ✅ **Already deployed.** The 3 `PRM_RecordKey__c` fields + their `PRM_AsyncJob_Access` FLS are in the target org — **these are E02's own work items, not Epic A**. Tasks below are retained for traceability; the only remaining action is a presence re‑check (T0.3).
- **T1.1 — Create `PRM_RecordKey__c`** (Text 255, External Id, Unique, case‑insensitive) on **HealthcareProvider**, **Identifier**, **HealthcareProviderTaxonomy** (design §3 WI‑1…WI‑3).
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: 3 fields deployed as External Id.
  - Dependencies: T0.1. Prerequisites: Phase 0. Impacted: `objects/<obj>/fields/PRM_RecordKey__c.field-meta.xml` ×3.
  - Validation: field deploys; describe resolves; `isUpdateable()` true for running user. Testing: a trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint conflict with existing data (fields are new/empty → low). Completion: ✅ **3 fields live (deployed)**.
- **T1.2 — Permission‑set FLS (WI‑4):** add Read+Edit for the 3 `PRM_RecordKey__c` fields to **`PRM_AsyncJob_Access`** (E02's additions to the Epic A permission set).
  - Dependencies: T1.1. Validation: permset deploys; running user can edit. Completion: ✅ **FLS present (deployed)**.
- **T1.3 — HealthcareProviderNpi dedupe approach (WI‑5):** confirm **no new field**; pre‑check on `Npi`; (optional) decide whether to add a unique constraint on `Npi`. Completion: ✅ approach recorded; no schema change.

### Phase 2 — `PRM_PractitionerService` core *(M2)*
- **T2.1 — Class + `execute` + `PractUow`; parse + bulk Id resolution**
  - Purpose: parse `practitioners[]`; build UoWs (no DML in loop); resolve `practitionerId` (PersonContactId) in one bulk Account query; obtain `caseManagerId` from the batch (`PRM_AsyncJobRecords__c`, per OQ‑E2‑2); bulk‑resolve taxonomy refs (`PRM_TaxonomySelector`).
  - Outcome: skeleton (design §4.2) realized through step 2.
  - Dependencies: T0.3, Phase 1. Impacted: `classes/PRM_PractitionerService.cls`.
  - Validation: compiles; parses sample payload; Account/taxonomy resolution batched. Testing: unit (parse + resolution). Risks: **[RISK]** payload shape drift; **[RISK]** `caseManagerId` wiring (OQ‑E2‑2). Completion: parse + resolution green.
- **T2.2 — Builders (HCP / NPI / Identifier[] / Taxonomy[]) + formulas + `PRM_RecordKey__c`**
  - Purpose: in‑memory record build with in‑service formulas (HCPName, HCPStatus, NPI gating, Identifier RT/Pending, taxonomy primary/providerType) and NPI‑anchored keys.
  - Outcome: per §6 field maps + §2 keys.
  - Dependencies: T2.1, T0.2 (validated maps). Validation: field‑by‑field unit assertions; key strings correct (`{npi}…`). Testing: builder unit cases (IBC vs Delegated; new vs existing NPI gating). Risks: **[RISK]** CL‑E1 IBC values (OQ‑E2‑4); **[RISK]** field/type drift (OQ‑E2‑1). Completion: builders unit‑tested.
- **T2.3 — Bulk DML order + idempotent writes**
  - Purpose: (1) upsert HCP by key → (2) pre‑check `Npi` then insert missing NPI rows → (3) upsert Identifier[] by key → (4) upsert Taxonomy[] by key; correlate Ids via `PractUow`.
  - Outcome: per §7; 4 bulk DML; HCP before NPI/Identifier/Taxonomy.
  - Dependencies: T2.2. Validation: created records have correct FKs + keys; DML count = 4; HCP Id available for E7. Testing: bulk test (251+). Risks: **[RISK]** ordering regressions; **[RISK]** missing‑NPI handling (OQ‑E2‑7). Completion: bulk DML + idempotency green.

### Phase 3 — Response & downstream contract *(M2)*
- **T3.1 — Build the response** (per‑practitioner `{ accountId, healthcareProviderId, healthcareProviderNpiId, identifierIds, taxonomyIds }`, input order).
  - Purpose: feed E5/E6/E7/E8/E11 (esp. `healthcareProviderId` for E6/E7/E11).
  - Dependencies: T2.3. Validation: response shape + order. Risks: **[RISK]** downstream resolution path (E6/E7/E11 resolve HCP by `PRM_RecordKey__c=npi` or `AccountId`) — confirm batch passes outputs in‑memory vs re‑query. Completion: response asserted.

### Phase 4 — Testing *(M3)*
- **T4.1 Unit:** builders/formulas (IBC vs Delegated; HCPStatus; NPI gating; Identifier RT/Pending; taxonomy primary/providerType; key construction).
- **T4.2 Bulk/governor:** 251+ practitioners → 4 DML + ~2 SOQL; assert limits.
- **T4.3 Idempotency (re‑run):** execute twice on the same chunk → record counts unchanged (upsert keys + NPI pre‑check).
- **T4.4 Key correctness (CL‑E2):** distinct NPIs → distinct graphs; the **same NPI re‑submitted → `upsert` updates (no duplicate)** (NPI business‑confirmed unique).
- **T4.5 Negative/edge:** blank NPI (per OQ‑E2‑7 policy), existing‑NPI gating (per OQ‑E2‑6), missing taxonomy ref, blank Identifier name gating.
  - Dependencies: Phases 1–3. Completion: ≥ 85% coverage; suites green.

### Phase 5 — Evidence & governance *(M3)* (Epic A §A7)
- **T5.1 —** Test Evidence Report (coverage + org spot‑check of the 4 objects incl. a re‑run/key‑correctness case) + human sign‑off. Risks: **[RISK]** no org → can't run (OQ‑E2‑1). Completion: evidence + sign‑off.

### Phase 6 — Version control *(M3)* (Epic A §A8)
- **T6.1 —** Branch `epic-e/practitioner-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. Commit prefix `[E2]`. **Schema (Phase 1) already deployed; the service PR proceeds.**

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Schema (Phase 1) is already deployed** — these `PRM_RecordKey__c` fields + FLS are **E02's** (not Epic A). Just **re‑confirm presence** (T0.3) before the service PR; the service won't compile/upsert without them.
- **[RECOMMENDATION] Run org schema validation (T0.2) before writing builders.** E2's §6 maps are grounded from legacy DRs but **not yet org‑verified** (unlike E1). Validating first avoids rework on field API names/types/required flags (esp. `Npi`, Identifier RT, taxonomy lookups).
- **[RISK] Batch wiring is the critical hidden dependency.** Two things must be true for E2 to work and stay idempotent: (a) the stored payload carries `practitionerInfo.id` = the E1 Account Id (FK correlation) **and** `practitionerInfo.npi` (the dedupe anchor); (b) `caseManagerId` comes from `PRM_AsyncJobRecords__c`, not the mutable Account. The design §4.2 skeleton still shows an Account‑based `caseManagerId` read — **reconcile when wiring `PractitionerBatch`** (OQ‑E2‑2/3).
- **[RISK] CL‑E1 (IBC source gap).** The active IBC IP has no DR creating NPI/Identifier, yet E2 builds them for both branches. The IBC field values are an assumption (default: reuse Delegated maps) — confirm (OQ‑E2‑4) or the IBC NPI/Identifier rows may be wrong.
- **[RECOMMENDATION] Make NPI mandatory at intake (OQ‑E2‑7).** NPI **anchors the key** (and the NPI object + pre‑check use it), so a blank NPI breaks idempotency. A clear "reject blank NPI at intake" rule keeps the key clean; otherwise define skip‑vs‑reject.
- **[RECOMMENDATION] Keep the existing‑NPI path deferred for the pilot (OQ‑E2‑6).** `existingHcpNpiId` gating parallels E1's deferred existing‑account path; defer unless explicitly in scope.
- **[RECOMMENDATION] Confirm the E6/E7/E11 hand‑off.** Those services resolve HCP by E2's `PRM_RecordKey__c` (= `npi`) or by `AccountId`. Decide whether `PractitionerBatch` passes E2's in‑memory `healthcareProviderId` outputs or each service re‑queries — either is bulk‑safe; pick one to avoid an extra query.
- **[RECOMMENDATION] Single‑owner `PRM_FormSubUtility`.** `recordTypeId`/`NameNormalize` are shared; coordinate edits to avoid merge churn.

---

## 6. Gaps & hidden dependencies

- **Target org** (OQ‑E2‑1) — gates schema validation, deploy, and tests.
- **Org schema validation** — not yet run for E2; §6 maps unverified.
- **E02 `PRM_RecordKey__c` fields + FLS** — **already deployed ✅** (E02's own, not Epic A; re‑confirm present — compile + runtime dep).
- **`PractitionerBatch` wiring (cross‑epic)** — payload enrichment with the E1 Account Id; `caseManagerId` from `PRM_AsyncJobRecords__c`; how the chunk (`practitioners[]`) is assembled.
- **Epic D `PRM_TaxonomySelector`** — taxonomy `careTaxonomyId` resolution from `taxonomyCode`.
- **Epic B `PRM_FormSubUtility`** (`recordTypeId`, `NameNormalize`) — shared helper, single‑owner.
- **E1** — creates Account/Contact/CaseManager + seeds `PRM_AsyncJobRecords__c` (E2 reads these).
- **CL‑E1** — IBC NPI/Identifier source values.
- **Open business/data:** missing‑NPI policy, existing‑NPI gating scope.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E2‑1 — Target org** for schema validation, deploy, and tests. *(Blocks Phase 0/1/5.)*
- **OQ‑E2‑2 — `caseManagerId` source & batch wiring.** Confirm E2 receives `caseManagerId` from `PRM_AsyncJobRecords__c` (batch scope), and reconcile the §4.2 skeleton's Account‑based read. *Recommendation:* pass it in via the batch context.
- **OQ‑E2‑3 — Payload enrichment with the E1 Account Id.** Confirm intake/`PractitionerBatch` writes `practitionerInfo.id` (= E1 Account Id, the **FK correlation key**) into the stored payload, alongside `practitionerInfo.npi` (the **dedupe anchor**). Cross‑epic (E1/EPIC F + Epic C batch).
- **OQ‑E2‑4 (CL‑E1) — IBC NPI/Identifier field values.** The IBC IP has no DR for NPI/Identifier. Confirm IBC values (default: reuse the Delegated maps) or supply the correct mapping.
- **OQ‑E2‑5 — Taxonomy resolution.** Confirm `PRM_TaxonomySelector` (Epic D) is available and resolves `careTaxonomyId` from `taxonomyCode` in bulk.
- **OQ‑E2‑6 — Existing‑NPI path scope.** Is `existingHcpNpiId` gating (insert vs reuse) in pilot scope, or deferred (recommended) like E1's existing‑account path?
- **OQ‑E2‑7 — Missing‑NPI handling.** Is NPI mandatory at intake (recommended)? If a practitioner has no NPI, does the NPI object **skip** or the submission **reject**?
- **OQ‑E2‑8 — Picklist/value validity.** Are forwarded values guaranteed active picklist entries where applicable (e.g. `NpiType`, taxonomy `ProviderType`, Identifier `PRM_Type__c`)? *Recommendation:* validate at intake. *(Confirm after T0.2.)*
- **OQ‑E2‑9 — Downstream HCP hand‑off.** For E6/E7/E11, does `PractitionerBatch` pass E2's in‑memory `healthcareProviderId`, or do they re‑query `HealthcareProvider` by `PRM_RecordKey__c=npi` (or `AccountId`)? Pick one.
- **OQ‑E2‑10 — Reference implementation in this plan?** Do you want a **complete inline class (Appendix A)** added here (as later done for E01/E19)? Default per this instruction: **no** (skeleton only).

*(Already resolved in E02 §8: bulkification contract; NPI‑anchored idempotency decision (CL‑E2: NPI confirmed unique by business); CL‑E5 `recordTypeId`.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | `PRM_RecordKey__c` fields/FLS not present → service won't compile/upsert | Low | High | **already deployed ✅** (E02 scope); T0.3 re‑confirm |
| R‑2 | Org schema not validated → §6 field‑map drift | Medium | High | T0.2 before builders (OQ‑E2‑1) |
| R‑3 | Batch wiring wrong (`caseManagerId` from mutable Account; payload missing Account Id) | Medium | High | OQ‑E2‑2/3; reconcile §4.2 when wiring |
| R‑4 | CL‑E1 IBC NPI/Identifier values incorrect | Medium | Medium | OQ‑E2‑4 confirm; T4.1 |
| R‑5 | `PRM_TaxonomySelector` (Epic D) unavailable | Medium | Medium | OQ‑E2‑5; T0.3 |
| R‑6 | HCP not upserted before NPI/Identifier/Taxonomy (breaks E7 feed) | Low | Medium | enforce §7 order; T2.3 |
| R‑7 | Missing‑NPI behavior undefined | Medium | Medium | OQ‑E2‑7 policy; T4.5 |
| R‑8 | No target org → can't validate/deploy/test | Medium | High | OQ‑E2‑1 |
| R‑9 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner coordination |

---

## 9. Sequencing & effort

- **Order:** Phase 0 → **Phase 1 (E02 schema) ✅ already deployed** → 2 (service) → 3 → 4 → 5 → 6. `PractitionerBatch` wiring pairs with E2.
- **Effort:** within the ~2.5 d catalog estimate — schema (Phase 1) ✅ **done (deployed)** · core class + resolution ~0.75 · builders/formulas/keys ~0.75 · DML/idempotency ~0.25 · response ~0.1 · tests (bulk/idempotency/key‑correctness/negative) ~0.5 · evidence/VCS folded in. *(Re‑confirm after OQ‑E2‑1…OQ‑E2‑9.)*
- **Depends on:** Epic A + Epic B + Epic D + E1 on `main`, plus `PractitionerBatch`. **Blocks/feeds:** E5/E6/E7/E8/E11 (and E7 needs the HCP Id).

---

## 10. What happens after sign‑off

Resolve OQ‑E2‑1…OQ‑E2‑10 (esp. target org, org schema validation, batch wiring, CL‑E1, taxonomy selector, no‑NPI policy). Then (the **E02 schema — Phase 1 — is already deployed ✅**; just re‑confirm via T0.3): build the service per the design (parse + bulk resolution → builders/formulas/keys → 4 bulk DML with NPI‑anchored idempotency + NPI pre‑check → response) → tests (unit/bulk/idempotency/key‑correctness/negative) → Test Evidence Report → human governance sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E2‑1) and the remaining items are confirmed.** If you want the full inline reference class (OQ‑E2‑10), I'll add it as a follow‑up.
