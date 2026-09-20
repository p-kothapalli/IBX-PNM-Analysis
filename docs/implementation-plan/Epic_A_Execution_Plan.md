# Epic A — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review. No components, code, scripts, configuration, commands, or other implementation artifacts have been or will be generated until this plan is reviewed and the Open Questions (§7) are answered.**
>
> **Source of truth:** `Epic_A_Environment_Setup.md` (A0–A9). This plan only restates and expands what that document explicitly defines. Anything not stated there is treated as **UNKNOWN** and surfaced as an Open Question — it is **not** assumed.
>
> **Reading guide:** items are tagged **[CONFIRMED]** (explicitly documented), **[OPEN]** (missing/ambiguous/contradictory — needs a decision), **[RISK]**, or **[RECOMMENDATION]**. Tasks that depend on an unresolved [OPEN] item are marked **⛔ Pending Clarification**.

---

## 1. Confirmed requirements (extracted from Epic A)

> Each line is traceable to the cited Epic A section.

### 1.1 Objects & hierarchy
- **[CONFIRMED]** Three **net-new** custom objects: `PRM_AsyncJob__c` with **two Master-Detail children (siblings)** — `PRM_AsyncJobRecords__c` (per Case Manager) and `PRM_AsyncJobDetails__c` (per batch step) (A0/A2/A2.1, "Decisions applied").
- **[CONFIRMED]** `PRM_AsyncJob__c` — parent / process run. OWD **Private**; Deployment Status **Deployed**; **Reports = yes**; Name = **Auto Number** `AJ-{0000000}` (A1).
- **[CONFIRMED]** `PRM_AsyncJobRecords__c` — one row **per practitioner (= per Case Manager)**. OWD **Controlled by Parent**; Name = **Auto Number** `AJR-{0000000}` (A2.1).
- **[CONFIRMED]** `PRM_AsyncJobDetails__c` — one row **per batch step** (e.g. 4 per Job), **M-D child of the Job** (sibling of Records). OWD **Controlled by Parent**; Name = **Auto Number** `AJD-{0000000}` (A2).

### 1.2 Fields
- **[CONFIRMED]** `PRM_AsyncJob__c`: `PRM_ProcessName__c` (Picklist, restricted, values `Practitioner Creation`/`PAR`, no default, **required**) and `PRM_Status__c` (Picklist, restricted, `Queued`(default)/`Running`/`Completed`/`Failed`, **required**) (A1).
- **[CONFIRMED]** `PRM_AsyncJob__c` has **no** `PRM_CaseManager__c`, `PRM_InputJson__c`, or `PRM_Response__c` (A1 notes).
- **[CONFIRMED]** `PRM_AsyncJobRecords__c`: standard **Auto Number `Name`** + exactly two custom fields — `PRM_AsyncJob__c` (Master-Detail → `PRM_AsyncJob__c`, reparent = false) and `PRM_CaseManager__c` (Lookup → `IndividualApplication`, delete = SetNull). Explicitly **no** ProcessName/Status/ErrorMessage/SourceRecordId (A2.1).
- **[CONFIRMED]** `PRM_AsyncJobDetails__c` *(one per MDT step, M-D child of the **Job** — sibling of Records)*: `PRM_AsyncJob__c` (Master-Detail → `PRM_AsyncJob__c`, reparent = false, **required**), `PRM_ProcessName__c` (Text(255), **required**), `PRM_Mode__c` (Picklist restricted, `Queueable`(default)/`Batch`, **required**), `PRM_BatchSize__c` (Number(4,0), default 200), `PRM_Sequence__c` (Number(3,0), **required** — step order), `PRM_Status__c` (Picklist restricted, `Queued`(default)/`Running`/`Completed`/`Failed`, **required**), `PRM_RetryCount__c` (Number(2,0), default 0). No CaseManager/InputJson/Response (A2).

### 1.3 Custom Metadata Type
- **[CONFIRMED]** `PRM_AsyncJobConfig__mdt` with six fields: `PRM_ProcessName__c` (Picklist `PAR`/`Practitioner Creation`), `PRM_ServiceClassName__c` (Text(255), **required**, holds the **batch class name**), `PRM_ServiceContext__c` (Text(255), human-readable), `PRM_Mode__c` (Picklist `Queueable`/`Batch`), `PRM_BatchSize__c` (Number(4,0)), `PRM_Sequence__c` (Number(3,0)) (A3).
- **[CONFIRMED]** Seed **one config record per batch step** under `PRM_ProcessName__c = 'Practitioner Creation'`, in order: 1 `PractitionerBatch` → 2 `PracticeLocationAndGroupBatch` → 3 `GroupRelatedBatch` → 4 `PLRelatedBatch` → 5 `Level4RecordCreationBatch` (A9; mapping mirrors Plan §8.1).

### 1.4 Existing object change
- **[CONFIRMED]** Add **one** field to the existing `PRM_FailedRecordStaging__c`: `PRM_AsyncJobDetails__c` (Lookup → `PRM_AsyncJobDetails__c`, delete = SetNull). **Do not recreate** the object (A4).

### 1.5 Access
- **[CONFIRMED]** New permission set `PRM_AsyncJob_Access` (label "PRM Async Job Access", `hasActivationRequired = false`): R/C/E/D on the three new objects; R/C/E on `PRM_FailedRecordStaging__c`; field Read+Edit on the above fields; `PRM_AsyncJob__c` **tab → Visible** (A5).
- **[CONFIRMED]** No Custom Metadata access entry needed (readable by Apex without perms) (A5).
- **[CONFIRMED]** EPIC C Apex class access is **out of scope for Epic A** (A5).

### 1.6 Process & governance
- **[CONFIRMED]** Deploy via the documented SFDX source-deploy mechanism (A0), objects in chain order, then CMDT + records, then permission set (A6).
- **[CONFIRMED]** Git: work on a branch `epic-a/async-data-model` cut from `main`; commit prefix `[A1]`; PR into `main`; squash-merge; promote `main`→`master` at milestone (A8).
- **[CONFIRMED]** Testing/evidence governance, test pyramid, and human sign-off gate are defined in A7 (see §6 caveat — A7's Apex/LWC/UI layers target later epics' artifacts, not Epic A's declarative metadata).

---

## 2. Constraints (documented)

- **[CONFIRMED]** Epic A is **declarative metadata only — no Apex** (A0/Goal).
- **[CONFIRMED]** Naming: `PRM_` prefix, PascalCase, no inter-word underscores; restricted picklists where stated (A0/§9 naming).
- **[CONFIRMED]** Master-Detail parents must exist before children (A2 note) — constrains deploy order.
- **[CONFIRMED]** `IndividualApplication` is the Case Manager object (A0).

---

## 3. Dependencies & prerequisites

- **[CONFIRMED]** Epic A **Depends on: none**; **Blocks: EPIC C, EPIC E** (A header).
- **[CONFIRMED]** Existing org objects relied upon: `IndividualApplication` (lookup target) and `PRM_FailedRecordStaging__c` (field add).
- **[OPEN] OQ-1 — Target org** (alias, and whether scratch org from `config/project-scratch-def.json` or a sandbox) is **not documented**. Required before any deploy/validation task.
- **[OPEN] OQ-2 — Org capability:** that `IndividualApplication` exists/is enabled in the target org is **not verified in-doc** (it depends on org licensing/features). Must be confirmed (it is a hard dependency for the M-D-adjacent lookup).

---

## 4. Acceptance criteria (from Epic A)

- **[CONFIRMED]** All three objects deployable (A6/Goal).
- **[CONFIRMED]** `PRM_AsyncJobConfig__mdt` records present — one per batch step for `Practitioner Creation` (A9).
- **[CONFIRMED]** `PRM_AsyncJob_Access` permission set assignable (A5/Implementation-Plan EPIC A acceptance).
- **[OPEN] OQ-3 — Epic-A-specific test evidence:** A7 defines Apex/LWC/UI evidence, but Epic A produces **no Apex/LWC/UI**. The concrete "done" evidence for a metadata-only epic is undefined (see §6).

---

## 5. Phases, milestones & task breakdown

> Sequencing follows the documented deploy order (A6) and the Master-Detail constraint. Each task lists Purpose · Expected outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion criteria.

### Phase 0 — Setup *(milestone M0: ready to author)*

**T0.1 — Establish working branch**
- Purpose: isolate Epic A work per A8.
- Expected outcome: branch `epic-a/async-data-model` from `main`.
- Dependencies: none. Prerequisites: clean `main`.
- Impacted areas: VCS only.
- Validation: branch exists, based on latest `main`.
- Testing: n/a.
- Risks: **[RISK]** local commits not yet pushed to remote (prior auth failure) — branch is local-only until SSH/HTTPS access is resolved.
- Completion: branch created.

**T0.2 — Confirm target org & dependencies ⛔ Pending Clarification (OQ-1, OQ-2)**
- Purpose: ensure a deploy target and that hard dependencies exist.
- Expected outcome: confirmed org alias/type; confirmed `IndividualApplication` + `PRM_FailedRecordStaging__c` present.
- Dependencies: OQ-1, OQ-2. Prerequisites: org access.
- Impacted areas: none (read-only checks).
- Validation: object describes succeed for the two existing objects.
- Testing: n/a.
- Risks: **[RISK]** missing `IndividualApplication` (licensing) blocks the lookup; missing staging object blocks the field add.
- Completion: both confirmed in writing.

### Phase 1 — Data model *(milestone M1: objects deployable)*

**T1.1 — `PRM_AsyncJob__c` object + Auto Number Name**
- Purpose: parent of the M-D chain / process-run record (A1).
- Expected outcome: object defined with OWD Private, Deployment Status Deployed, Reports enabled, Name Auto Number `AJ-{0000000}`.
- Dependencies: none. Prerequisites: T0.
- Impacted areas: `force-app/main/default/objects/PRM_AsyncJob__c/` (object definition).
- Validation: object present after deploy (describe).
- Testing: deploy success; no unit tests (declarative).
- Risks: **[RISK]** undocumented object settings (Activities, Field History, Search, Sharing model nuances) — see OQ-4.
- Completion: object deploys; settings match A1 documented values; undocumented settings deferred to OQ-4.
- **⛔ Pending Clarification (OQ-4)** for the non-documented object settings.

**T1.2 — `PRM_AsyncJob__c` fields (`PRM_ProcessName__c`, `PRM_Status__c`)**
- Purpose: routing key + run status (A1).
- Expected outcome: two restricted picklists per A1 (values, defaults, required as documented).
- Dependencies: T1.1. Prerequisites: T1.1.
- Impacted areas: object's `fields/`.
- Validation: describe shows fields, restricted value sets, defaults, required flags.
- Testing: deploy success.
- Risks: **✅ OQ-5 RESOLVED** — use **inline restricted picklists** (no Global Value Set); values defined inline per A1.
- Completion: fields deploy with documented spec.

**T1.3 — `PRM_AsyncJobRecords__c` object + Auto Number Name**
- Purpose: per-practitioner/per-Case-Manager tracker (A2.1).
- Expected outcome: object, OWD Controlled by Parent, Name Auto Number `AJR-{0000000}`.
- Dependencies: T1.1 (M-D parent must exist). Prerequisites: T1.1.
- Impacted areas: `objects/PRM_AsyncJobRecords__c/`.
- Validation: describe.
- Testing: deploy success.
- Risks: **[RISK]** OWD on a Master-Detail child is implicitly Controlled by Parent — confirm no conflicting setting; **[RISK]** undocumented object settings (OQ-4).
- Completion: object deploys.

**T1.4 — `PRM_AsyncJobRecords__c` fields (M-D `PRM_AsyncJob__c`, Lookup `PRM_CaseManager__c`)**
- Purpose: link to the run; correlate the Case Manager (A2.1).
- Expected outcome: Master-Detail (reparent = false) + Lookup→`IndividualApplication` (SetNull). **Only these two custom fields.**
- Dependencies: T1.1, T1.3, OQ-2 (`IndividualApplication`). Prerequisites: those.
- Impacted areas: object's `fields/`.
- Validation: describe confirms relationships + delete behaviors.
- Testing: deploy success.
- Risks: **[RISK]** lookup to `IndividualApplication` fails if object/feature absent (OQ-2 deferred). **✅ OQ-6 RESOLVED** — M-D is **required**; relationship name `AsyncJobRecords`; platform defaults otherwise.
- Completion: fields deploy with documented spec.

**T1.5 — `PRM_AsyncJobDetails__c` object + Auto Number Name**
- Purpose: per-batch-step tracker (A2). *(M-D child of the **Job** — sibling of Records.)*
- Expected outcome: object, Controlled by Parent, Name Auto Number `AJD-{0000000}`.
- Dependencies: T1.1 (the Job is the M-D parent). Prerequisites: T1.1.
- Impacted areas: `objects/PRM_AsyncJobDetails__c/`.
- Validation: describe.
- Testing: deploy success.
- Risks: OQ-4 (undocumented settings).
- Completion: object deploys.

**T1.6 — `PRM_AsyncJobDetails__c` fields (6 fields per A2)**
- Purpose: step orchestration state (A2).
- Expected outcome: M-D→`PRM_AsyncJob__c` (sibling of Records), ProcessName Text(255), Mode picklist, BatchSize Number(4,0) default 200, **Sequence Number(3,0)**, Status picklist, RetryCount Number(2,0) default 0 — per A2.
- Dependencies: T1.5, T1.1. Prerequisites: those.
- Impacted areas: object's `fields/`.
- Validation: describe confirms each field's type/spec/defaults/required.
- Testing: deploy success.
- Risks: ✅ OQ-5 resolved (inline picklists); ✅ OQ-6 resolved (M-D to the Job, required; relationship name `AsyncJobDetails`); **[RISK]** required M-D + required picklists affect permission-set field-perm handling (see T4.2).
- Completion: fields deploy with documented spec.

### Phase 2 — Configuration *(milestone M2: config present)*

**T2.1 — `PRM_AsyncJobConfig__mdt` type + 6 fields**
- Purpose: metadata-driven batch routing/sequencing (A3).
- Expected outcome: CMDT with the six documented fields/types.
- Dependencies: none structurally (but referenced by EPIC C). Prerequisites: T0.
- Impacted areas: `objects/PRM_AsyncJobConfig__mdt/`.
- Validation: type + fields present (describe / Setup).
- Testing: deploy success.
- Risks: **✅ OQ-7 RESOLVED** — required: `PRM_ServiceClassName__c`, `PRM_ProcessName__c`, `PRM_Sequence__c`, `PRM_Mode__c`; optional: `PRM_BatchSize__c`, `PRM_ServiceContext__c`. **✅ OQ-5 RESOLVED** — CMDT picklists use inline value sets.
- Completion: type + fields deploy with the resolved spec.

**T2.2 — Seed four `PRM_AsyncJobConfig__mdt` records**
- Purpose: define the pilot batch chain (A9).
- Expected outcome: **four** records under `Practitioner Creation`, each `PRM_BatchSize__c = 1` (OQ-9, temporary), named `<ProcessName>_<BatchName>` (OQ-10):

  | DeveloperName | Label | `PRM_ServiceClassName__c` | `PRM_Sequence__c` | `PRM_Mode__c` | `PRM_BatchSize__c` |
  |---|---|---|---|---|---|
  | `Practitioner_Creation_PractitionerBatch` | Practitioner Creation PractitionerBatch | `PractitionerBatch` | 1 | Batch | 1 |
  | `Practitioner_Creation_PracticeLocationAndGroupBatch` | Practitioner Creation PracticeLocationAndGroupBatch | `PracticeLocationAndGroupBatch` | 2 | Batch | 1 |
  | `Practitioner_Creation_PLRelatedBatch` | Practitioner Creation PLRelatedBatch | `PLRelatedBatch` | 4 | Batch | 1 |
  | `Practitioner_Creation_Level4RecordCreationBatch` | Practitioner Creation Level4RecordCreationBatch | `Level4RecordCreationBatch` | 5 | Batch | 1 |

  **Seq 3 `GroupRelatedBatch` omitted for now** (OQ-8); the slot is reserved for CL-15.
- Dependencies: T2.1. Prerequisites: T2.1.
- Impacted areas: `customMetadata/`.
- Validation: query returns four rows ordered by `PRM_Sequence__c` (1, 2, 4, 5).
- Testing: deploy success + row count/order.
- Notes / risks:
  - ✅ OQ-8 (GroupRelatedBatch omitted), ✅ OQ-9 (BatchSize = 1, temporary), ✅ OQ-10 (naming) resolved.
  - **[NOTE]** `PRM_ServiceContext__c` text per row is illustrative.
  - **[RISK]** the sequence gap (no 3) is harmless for `findNextJob` ordering, but EPIC C must order rows, not assume contiguous numbering.
- Completion: four records deploy with the spec above.

### Phase 3 — Existing-object change *(milestone M2)*

**T3.1 — `PRM_FailedRecordStaging__c` add `PRM_AsyncJobDetails__c` lookup**
- Purpose: link a staged failure to the detail that produced it (A4).
- Expected outcome: single Lookup field (→`PRM_AsyncJobDetails__c`, SetNull); object **not** recreated.
- Dependencies: T1.5 (`PRM_AsyncJobDetails__c` must exist). Prerequisites: OQ-2 (object exists in org).
- Impacted areas: `objects/PRM_FailedRecordStaging__c/fields/` (field only, no object-meta).
- Validation: describe shows the new field.
- Testing: deploy success.
- Risks: **[RISK]** if the field is added only in source but the object is managed/locked, deploy may fail; **[RISK]** retrieving vs not retrieving the existing object definition — adding a field-only file is the documented intent (A4 "do not recreate").
- Completion: field deploys against the existing object.

### Phase 4 — Access *(milestone M3: assignable access)*

**T4.1 — `PRM_AsyncJob__c` tab — ❌ CANCELLED (OQ-11 → drop)**
- Decision: **no tab created in Epic A**; tab visibility is dropped from the permission set (OQ-11 option b). Tab can be added in a later epic if monitoring UI is needed.

**T4.2 — Permission set `PRM_AsyncJob_Access`** — **OQ-12 RESOLVED (with platform constraint); OQ-11 → no tab settings**
- Purpose: grant object + field access (A5), **without** tab settings (OQ-11).
- Expected outcome: object perms (R/C/E/D on the 3 new objects; R/C/E on staging) + **FLS Read+Edit on every FLS-eligible custom field**. **No `tabSettings`.**
  - **FLS entries included:** `PRM_AsyncJobRecords__c.PRM_CaseManager__c`, `PRM_AsyncJobDetails__c.PRM_BatchSize__c`, `PRM_AsyncJobDetails__c.PRM_RetryCount__c`.
  - **NOT listed (platform constraint — implicit via object access):** required picklists `PRM_AsyncJob__c.PRM_ProcessName__c` / `PRM_AsyncJob__c.PRM_Status__c` / `PRM_AsyncJobDetails__c.PRM_ProcessName__c` / `PRM_AsyncJobDetails__c.PRM_Status__c` / `PRM_AsyncJobDetails__c.PRM_Mode__c`; Master-Detail fields; Auto-Number `Name`.
- Dependencies: T1.*, T3.1 (no tab dependency). Prerequisites: those.
- Impacted areas: `permissionsets/`.
- Validation: deploys; assignable; grants present.
- Testing: deploy success + self-assignment smoke check.
- Risks: **[RISK]** Salesforce rejects `fieldPermissions` on required/M-D/Auto-Number fields → those are intentionally excluded (object access covers them).
- Completion: permission set deploys and assigns; FLS covers the three eligible fields.

### Phase 5 — Deploy & validate *(milestone M4: deployed & verified)*

**T5.1 — Validate-only deploy ⛔ Pending Clarification (OQ-1)**
- Purpose: confirm the package deploys without committing changes.
- Expected outcome: clean validation result.
- Dependencies: all authoring tasks; OQ-1 (target org). Prerequisites: org access.
- Impacted areas: none (check-only).
- Validation: validation succeeds; dependency order resolves in one package.
- Testing: this is the validation.
- Risks: **[RISK]** intra-package M-D ordering; **[RISK]** restricted picklist/permset field-perm errors (T4.2 risk).
- Completion: validation passes.

**T5.2 — Deploy**
- Purpose: apply the metadata (A6).
- Expected outcome: all Epic A metadata in the target org.
- Dependencies: T5.1. Prerequisites: passing validation.
- Impacted areas: target org.
- Validation: deploy success.
- Testing: post-deploy verification (T5.3).
- Risks: as T5.1.
- Completion: deploy succeeds.

**T5.3 — Verification**
- Purpose: prove acceptance criteria (§4).
- Expected outcome: objects describe; CMDT rows present & ordered; permission set assignable.
- Dependencies: T5.2. Prerequisites: deploy.
- Impacted areas: none (read checks + a self-assignment).
- Validation: object describes succeed; config row count/order correct; permset assigns without error.
- Testing: this is the acceptance check.
- Risks: **[RISK]** assignment may require a license/app context not documented.
- Completion: all three acceptance criteria (§4) met.

### Phase 6 — Evidence & governance *(milestone M5: signed off)* — **OQ-3 RESOLVED (lightweight)**
- Purpose: provide Epic-A evidence + human sign-off (A7 governance gate), scaled to a metadata-only epic.
- Expected outcome: a **lightweight Epic-A evidence set** — validate-only result, deploy result, object describes (3 objects), CMDT query (seeded rows + order), permission-set assignment result — assembled into a dated report; human sign-off recorded on the PR.
- Dependencies: T5.3. Prerequisites: T5.3.
- Impacted areas: `docs/test-evidence/Epic_A_<date>/`.
- Validation: report assembled; sign-off recorded on the PR.
- Testing: the A7 **Apex/LWC/UI test pyramid is deferred to EPIC C/E** (no such artifacts exist in Epic A).
- Completion: lightweight evidence assembled + human sign-off before `main`→`master`.

### Phase 7 — Version control *(milestone M5)*
- Purpose: integrate per A8.
- Expected outcome: `[A1]` commit(s) on `epic-a/async-data-model`; PR into `main`; squash-merge after green checks + review.
- Dependencies: T5.3 (+ Phase 6). Prerequisites: passing checks.
- Impacted areas: VCS.
- Validation: PR merged; (optionally) `main`→`master` tagged at milestone.
- Testing: CI gates per A8.
- Risks: **[RISK]** remote push currently blocked (SSH auth) — see T0.1.
- Completion: merged per A8.

---

## 6. Challenge / review of the proposed approach

- **✅ RESOLVED — A7 testing layers vs Epic A reality.** A7's Apex/LWC/UI pyramid does not fit a declarative-only epic; **lightweight Epic-A evidence** adopted and the pyramid deferred to EPIC C/E (OQ-3).
- **✅ RESOLVED — Picklist value-set strategy.** **Inline restricted picklists** (no Global Value Set) per OQ-5.
- **✅ RESOLVED — `GroupRelatedBatch` seed.** **Omitted for now** (OQ-8); slot 3 reserved for CL-15.
- **✅ RESOLVED — Permission-set field perms.** Include FLS only on FLS-eligible custom fields; required/M-D/Auto-Number excluded by platform rule (OQ-12).
- **[RISK] Single-package vs staged deploy.** A6 shows a single multi-object command. M-D ordering usually resolves within one package; if it doesn't, fall back to staged deploys (job → records → details → staging field → CMDT → tab → permset). No assumption made on which the org requires.

---

## 7. Open Questions & Decisions Log

### 7.0 Decisions confirmed (review round 1)

- **✅ OQ-3 — Epic-A evidence:** **lightweight metadata evidence** — validate-only result, deploy result, object describes, CMDT query, permission-set assignment. The Apex/LWC/UI test pyramid (A7) is **deferred to EPIC C/E**, where those artifacts first exist. *(Phase 6 updated.)*
- **✅ OQ-5 — Picklist value sets:** **Global Value Sets NOT required** → use **inline restricted picklists** per object/CMDT (as A1 shows for `PRM_Status__c`). *(T1.2, T1.6, T2.1 updated.)*
- **✅ OQ-8 — `GroupRelatedBatch`:** **ignore for now** → **omit the seq-3 config record**; seed only the four defined steps. Sequence numbers keep the slot (1, 2, 4, 5) so `GroupRelatedBatch` can be added as 3 later. *(T2.2 updated.)*
- **✅ OQ-12 — Permission-set fields:** include **all applicable custom fields**. ⚠ **Platform constraint:** Salesforce does **not** allow field-level security entries on **Required**, **Master-Detail**, or **Auto-Number** fields — those are accessible implicitly via object permissions and must **not** be listed in `fieldPermissions` (doing so fails the deploy). Resolution: grant Read+Edit FLS on the **FLS-eligible** custom fields — `PRM_CaseManager__c` (Records), `PRM_BatchSize__c` (Details), `PRM_RetryCount__c` (Details); the required picklists (`PRM_ProcessName__c`, `PRM_Status__c`, `PRM_Mode__c`) and M-D/Auto-Number fields are covered by object access without FLS entries. *(T4.2 updated.)* — **please confirm this interpretation, since "include required fields" isn't directly possible on the platform.**
- **✅ OQ-6 — Master-Detail relationship:** the M-D relationship is **required** (platform-inherent for Master-Detail). Relationship names: `AsyncJobRecords` (Job→Records) and `AsyncJobDetails` (Records→Details); platform defaults otherwise. *(T1.4, T1.6 updated.)*
- **✅ OQ-9 — Batch size:** set `PRM_BatchSize__c = 1` on the seeded config records **for now** (to be updated later). *(T2.2 updated.)*
- **✅ OQ-10 — CMDT record naming:** **`<ProcessName> + <Batch name>`** → DeveloperName `Practitioner_Creation_<BatchName>` (e.g. `Practitioner_Creation_PractitionerBatch`); Label `Practitioner Creation <BatchName>`. *(T2.2 updated.)*
- **✅ OQ-11 — Tab:** **drop tab visibility from the Epic A permission set** — **no tab created** in Epic A. *(T4.1 cancelled; T4.2 updated to remove tab settings.)*
- **✅ OQ-4 — Object settings:** **ignore for now** → apply only the documented settings (Reports = yes on the Job per A1) and **platform defaults** elsewhere; no explicit Activities/History/Search configuration in Epic A.
- **✅ OQ-2 — `IndividualApplication` availability:** **deferred/ignored for now** — will rely on the target org when provided (OQ-1).
- **◻ OQ-1 — Target org:** **to be confirmed later** (you'll provide). All deploy/validation tasks (Phase 5–7) remain blocked until then.

- **✅ OQ-7 — CMDT field requiredness:** **required** = `PRM_ServiceClassName__c` (doc), `PRM_ProcessName__c`, `PRM_Sequence__c`, `PRM_Mode__c`; **optional** = `PRM_BatchSize__c`, `PRM_ServiceContext__c`. *(T2.1 updated.)*

### 7.1 Still open

- **◻ OQ-1 — Target org** (you'll confirm later) — gates deploy/validation only.

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-A1 | `IndividualApplication` not enabled in target org | Medium | High (blocks lookup + staging field) | OQ-2 verify before authoring |
| R-A2 | Permission-set field perms on required/M-D/Auto-Number fields → deploy error | High if taken literally | Medium | ✅ Resolved (OQ-12): FLS only on the 3 eligible fields; required/M-D/Auto-Number excluded |
| R-A3 | Intra-package Master-Detail ordering rejected | Low | Medium | Fall back to staged deploy (A6 order) |
| R-A4 | Seq gap (no 3) — EPIC C assumes contiguous sequence | Low | Medium | ✅ Resolved (OQ-8): `GroupRelatedBatch` omitted; EPIC C must order, not assume contiguity |
| R-A5 | Undocumented object settings cause drift / rework | Medium | Low–Medium | OQ-4 confirm explicitly |
| R-A6 | Staging object managed/locked → field add fails | Low | Medium | OQ-2 + verify object is editable |
| R-A7 | Remote push blocked (SSH auth) | Confirmed | Low (local commits safe) | resolve credentials before Phase 7 |
| R-A8 | A7 evidence not achievable for metadata-only epic | Confirmed | Low | OQ-3 lightweight evidence |

---

## 9. Gaps & hidden dependencies (summary)

**Still open:**
- **OQ-1 — Target org** (you'll confirm later) — blocks deploy/validate only, not authoring.

**Resolved:** OQ-2 (deferred), OQ-3 (lightweight evidence), OQ-4 (defaults), OQ-5 (inline picklists), OQ-6 (M-D required + relationship names), OQ-7 (CMDT requiredness), OQ-8 (GroupRelatedBatch omitted), OQ-9 (BatchSize=1 temp), OQ-10 (naming `<ProcessName>_<BatchName>`), OQ-11 (no tab), OQ-12 (FLS on eligible fields only).

---

## 10. What happens after sign-off

**Decisions complete except OQ-1 (org).** Resolved: OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8, OQ-9, OQ-10, OQ-11, OQ-12.

**Authoring is now fully specified** — the only remaining blocker is **OQ-1 (target org alias/type)**, which gates deploy/validation (Phase 5+), not file authoring.

Next: on your go-ahead I will (1) author the Epic A metadata files per this resolved spec on `epic-a/async-data-model`, then **pause** for the **target org (OQ-1)** before (2) validate-only deploy, (3) deploy + verify, (4) assemble the lightweight evidence, and (5) human sign-off (A7) before any `main`→`master`. **No artifacts will be created until you say go.**
