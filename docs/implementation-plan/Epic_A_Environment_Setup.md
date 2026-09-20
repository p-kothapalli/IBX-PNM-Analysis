# Epic A — Environment Setup (Implementation Guide)

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.2) · `PRM_Implementation_Plan.md` (EPIC A)
> **Goal:** stand up the **net-new async data model + config + access** the Practitioner Creation rebuild depends on. This is pure declarative metadata (objects, fields, Custom Metadata, permission set) — no Apex.
> **Estimate:** ~1.0 engineer-day · **Depends on:** none · **Blocks:** EPIC C (async framework), EPIC E (batch services).

> **🔄 Revision — async-only redesign (ratified):** the form is now **fully asynchronous** — there is **no synchronous orchestrator**. Intake accepts a **form submission or CSV upload (multiple practitioners per submission)**; the IP/OmniScript wrapper validates (sync), **calls `PRM_CaseService` to create one Case Manager (`IndividualApplication`) per practitioner**, then **inserts a `PRM_AsyncJob__c` (+ submission JSON file) + one `PRM_AsyncJobRecords__c` per practitioner and returns immediately**. All record creation runs through **five concrete batch classes** (`PractitionerBatch`, `PracticeLocationAndGroupBatch`, `GroupRelatedBatch`, `PLRelatedBatch`, `Level4RecordCreationBatch`) that `PRM_AsyncOrchestrator` sequences from Custom Metadata; each batch wraps its own service(s) and handles the IBC-vs-Delegated branching internally. The chain **halts on first failure** (remaining batches don't run; already-created records remain — no compensating rollback; manual retry resumes from the failed batch). This Epic A revision adds the new **`PRM_AsyncJobRecords__c`** object, **removes `PRM_CaseManager__c` from `PRM_AsyncJob__c`** (Case Managers are now tracked per-row on `PRM_AsyncJobRecords__c`), and repurposes `PRM_AsyncJobConfig__mdt.PRM_ServiceClassName__c` to hold the **batch class name**.

> **⚠ Naming decision (ratified):** to match the org convention (every PRM custom object/field is `PRM_`-prefixed, PascalCase, no inter-word underscores), the async objects are `**PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` / `PRM_AsyncJobRecords__c`** with `PRM_*` fields — **not** the unprefixed `Async_Job__c` used in the parent TDD/plan. The parent docs still carry the old names and must be reconciled (tracked as a follow-up).

> **Decisions applied:** **two Master-Detail children of the Job (siblings, not a chain)** — `PRM_AsyncJobRecords__c` (one **per Case Manager**, tracks the CM↔Job association) and `PRM_AsyncJobDetails__c` (one **per `PRM_AsyncJobConfig__mdt` batch step**, the chained pipeline). Hierarchy: `PRM_AsyncJob__c` → `{PRM_AsyncJobRecords__c, PRM_AsyncJobDetails__c}`. `PRM_CaseManager__c` = **Lookup(IndividualApplication)** on `PRM_AsyncJobRecords__c`; payload/result JSON kept as a **ContentVersion file** on `PRM_AsyncJob__c` (no `InputJson`/`Response` fields); OWD = **Private**; new permission set `**PRM_AsyncJob_Access`**.

---

## A0. Prerequisites & conventions

- SFDX project (`force-app/main/default`), authorized target org, deploy via `sf project deploy start`.
- Field convention (grounded to org): `PRM_` + PascalCase, no underscores between words (e.g. `PRM_BatchSize__c`, `PRM_ProcessName__c`) — matches `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ItemsProcessed__c` on existing objects.
- "Case Manager" = the `**IndividualApplication**` record (grounded: `PRM_CaseDataManager__c.PRM_CaseManager__c` and `PRM_FailedRecordStaging__c.PRM_CaseManager__c` are both Lookup→IndividualApplication).

---

## A1 · Object — `PRM_AsyncJob__c` (parent job)

- **Label / Plural:** Async Job / Async Jobs · **OWD:** Private · **Deployment Status:** Deployed · **Allow Reports / Activities:** Reports yes.
- **Name field:** Auto Number, format `AJ-{0000000}`.


| Field API            | Label        | Type                            | Spec                                                   | Req     | Notes                                  |
| -------------------- | ------------ | ------------------------------- | ------------------------------------------------------ | ------- | -------------------------------------- |
| `PRM_ProcessName__c` | Process Name | Picklist                        | `Practitioner Creation` · `PAR` (no default)           | **Yes** | restricted; routing key                |
| `PRM_Status__c`      | Status       | Picklist                        | `Queued`(default) · `Running` · `Completed` · `Failed` | **Yes** | restricted picklist                    |


> **No `PRM_CaseManager__c` on the parent job** (removed in the async-only redesign): one process run can span **multiple** Case Managers, so the Case Manager correlation moves to the child **`PRM_AsyncJobRecords__c`** (A2.1). The parent job represents the *process run*, not a single Case Manager.

> **Payload storage:** the request/result JSON is **kept as a file (ContentVersion) linked to the `PRM_AsyncJob__c` record**, not in a field — so there is **no `PRM_InputJson__c` / `PRM_Response__c`** on this object. The framework (EPIC C) reads/writes that file via `jsonFileParser`.

**Example field metadata** (`objects/PRM_AsyncJob__c/fields/PRM_Status__c.field-meta.xml`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_Status__c</fullName>
    <label>Status</label>
    <type>Picklist</type>
    <required>true</required>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
            <value><fullName>Queued</fullName><default>true</default><label>Queued</label></value>
            <value><fullName>Running</fullName><default>false</default><label>Running</label></value>
            <value><fullName>Completed</fullName><default>false</default><label>Completed</label></value>
            <value><fullName>Failed</fullName><default>false</default><label>Failed</label></value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

---

## A2 · Object — `PRM_AsyncJobDetails__c` (per–batch-step tracker)

- **Role:** one `PRM_AsyncJobDetails__c` row **per batch step** (per `PRM_AsyncJobConfig__mdt` row — e.g. 4 per Job, **not** per practitioner), **child of the Job**. Tracks that step's mode/size/status as `PRM_AsyncOrchestrator` chains the batch pipeline; retry is per step.
- **Label / Plural:** Async Job Details / Async Job Details · **OWD:** Controlled by Parent (Master-Detail) · **Name field:** Auto Number `AJD-{0000000}`.


| Field API            | Label        | Type                                 | Spec                                                   | Req     | Notes                                          |
| -------------------- | ------------ | ------------------------------------ | ------------------------------------------------------ | ------- | ---------------------------------------------- |
| `PRM_AsyncJob__c`        | Async Job        | **Master-Detail**(`PRM_AsyncJob__c`)        | reparent = false                                       | **Yes** | parent = the Job; cascade delete supports EPIC C cleanup |
| `PRM_ProcessName__c`     | Process Name     | Text(255)                                   | —                                                      | **Yes** | routing key                                    |
| `PRM_Mode__c`            | Mode             | Picklist                                    | `Queueable`(default) · `Batch`                         | **Yes** | restricted                                     |
| `PRM_BatchSize__c`       | Batch Size       | Number(4,0)                                 | default 200                                            | No      | chunk size for Batch/Queueable chunking        |
| `PRM_Sequence__c`        | Sequence         | Number(3,0)                                 | from the MDT row                                       | **Yes** | step order for chaining (halt-on-failure)      |
| `PRM_Status__c`          | Status           | Picklist                                    | `Queued`(default) · `Running` · `Completed` · `Failed` | **Yes** | restricted                                     |
| `PRM_RetryCount__c`      | Retry Count      | Number(2,0)                                 | default 0                                              | No      | incremented on retry                           |


> **No `PRM_InputJson__c` / `PRM_Response__c`** on the step — payload/result are handled via the Job's ContentVersion file (EPIC C).

> **Master-Detail note:** `PRM_AsyncJobDetails__c` and `PRM_AsyncJobRecords__c` are **independent M-D children of `PRM_AsyncJob__c`** (siblings). Cascade delete from the Job removes both (relied on by the EPIC C cleanup batch).

> **Case Manager:** the step has **no `PRM_CaseManager__c`** — a step runs once for the whole Job and processes **all** Case Managers (the `PRM_AsyncJobRecords__c` rows) in one batch. Per-Case-Manager failures are captured in the DLQ (`PRM_FailedRecordStaging__c.PRM_CaseManager__c`).

---

## A2.1 · Object — `PRM_AsyncJobRecords__c` (per–practitioner / per–Case-Manager tracker)

- **Role:** one `PRM_AsyncJobRecords__c` row **per practitioner** (= **per Case Manager**) in a single submission/process run (`PRM_AsyncJob__c`). A form submission or **CSV upload** can contain many practitioners; intake creates one Case Manager (`IndividualApplication`) per practitioner via `PRM_CaseService` and records each here.
- **Seeded at intake:** the IP wrapper calls `PRM_CaseService` (the "Case Manager Service") synchronously, then inserts one `PRM_AsyncJobRecords__c` per practitioner with the returned Case Manager Id — **before** the async batches run. The batches fan out across these rows.
- **Label / Plural:** Async Job Record / Async Job Records · **OWD:** Controlled by Parent (Master-Detail) · **Name field:** standard Auto Number, format `AJR-{0000000}`.
- **Relationship:** **M-D child of `PRM_AsyncJob__c`**, **sibling of `PRM_AsyncJobDetails__c`** (both are direct children of the Job — not a chain). Correlates a Case Manager to the Job; the batch steps (Details) process all these records together.

**Fields — the standard Auto Number `Name` plus only two custom fields** (no `PRM_ProcessName__c` / `PRM_Status__c` / `PRM_ErrorMessage__c` / `PRM_SourceRecordId__c`; status/mode/error live on the child `PRM_AsyncJobDetails__c`):


| Field API            | Label        | Type                                 | Spec              | Req     | Notes                                                  |
| -------------------- | ------------ | ------------------------------------ | ----------------- | ------- | ------------------------------------------------------ |
| `Name`                 | Async Job Record | **Auto Number**                      | format `AJR-{0000000}` | —       | record name (standard Name field, Auto Number)         |
| `PRM_AsyncJob__c`       | Async Job        | **Master-Detail**(`PRM_AsyncJob__c`) | reparent = false  | **Yes** | parent; cascade delete supports EPIC C cleanup          |
| `PRM_CaseManager__c`    | Case Manager     | Lookup(`IndividualApplication`)      | delete = SetNull  | No      | the IA (= Case Manager) for this practitioner — created by `PRM_CaseService` at intake |


> The LWC (`prmAsyncJobProgress`, EPIC C5) resolves a Case Manager's work by querying `PRM_AsyncJobRecords__c` where `PRM_CaseManager__c = :recordId`, then reading the **parent Job's** `PRM_AsyncJobDetails__c` steps (run/step status) and any `PRM_FailedRecordStaging__c` rows for that Case Manager (per-CM errors) — replaces the removed `PRM_AsyncJob__c.PRM_CaseManager__c` filter.

---

## A3 · Custom Metadata — `PRM_AsyncJobConfig__mdt`




| Field API                 | Label              | Type        | Spec                            | Notes                                                                                                           |
| ------------------------- | ------------------ | ----------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `PRM_ProcessName__c`      | Process Name       | Picklist    | `PAR` / `Practitioner Creation` | the process this config applies to (matches `PRM_AsyncJob__c.PRM_ProcessName__c`)                               |
| `PRM_ServiceClassName__c` | Service Class Name | Text(255)   | required                        | **Batch class** name the orchestrator instantiates via `Type.forName` (e.g. `PractitionerBatch`) — field name kept; meaning is now the batch class (resolves CL-12) |
| `PRM_ServiceContext__c`   | Service Context    | Text(255)   |                                 | human-readable context of what the batch/service implements (e.g. "Creates Group, NPI, Practice Location & affiliations") — for config readability / admin reference |
| `PRM_Mode__c`             | Mode               | Picklist    | `Queueable` / `Batch`           | dispatch mode (kept; the five named classes are Batch)                                                          |
| `PRM_BatchSize__c`        | Batch Size         | Number(4,0) |                                 | chunk size                                                                                                      |
| `PRM_Sequence__c`         | Sequence           | Number(3,0) |                                 | batch-step ordering (drives `findNextJob` chaining + halt-on-failure)                                           |


---

## A4 · Reused (no change) — `PRM_FailedRecordStaging__c` (DLQ)

Existing object; **do not recreate**. EPIC C's `logFailure` writes to it. Fields used: `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ErrorMessage__c`, `PRM_ExceptionLog__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_SourceFlow__c`, `PRM_CaseManager__c` (Lookup→IndividualApplication). Confirm the running user/permission set has CRUD here.

**New field to add** (the only change to this existing object):


| Field API                | Label            | Type                             | Spec             | Req | Notes                                                         |
| ------------------------ | ---------------- | -------------------------------- | ---------------- | --- | ------------------------------------------------------------- |
| `PRM_AsyncJobDetails__c` | Async Job Detail | Lookup(`PRM_AsyncJobDetails__c`) | delete = SetNull | No  | links a staged failure back to the child job that produced it |


---

## A5 · Permission Set — `PRM_AsyncJob_Access`

> Permission sets are **not currently tracked in this repo** (`permissionsets/` empty) — this introduces the folder.

- **Objects:** `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c` → Read/Create/Edit/Delete; `PRM_FailedRecordStaging__c` → Read/Create/Edit.
- **Field perms:** all fields above → Read + Edit (Master-Detail/required fields are implicitly editable).
- **Tabs:** `PRM_AsyncJob__c` tab → Visible (for support/monitoring).
- **Apex class access:** add the EPIC C classes (`PRM_AsyncOrchestrator`, the five batch classes, trigger handler) here **when they exist** (EPIC C) — out of scope for A.
- **Custom Metadata:** `PRM_AsyncJobConfig__mdt` is readable by Apex without perms; no entry needed.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>PRM Async Job Access</label>
    <hasActivationRequired>false</hasActivationRequired>
    <objectPermissions>
        <object>PRM_AsyncJob__c</object>
        <allowCreate>true</allowCreate><allowRead>true</allowRead>
        <allowEdit>true</allowEdit><allowDelete>true</allowDelete>
        <viewAllRecords>false</viewAllRecords><modifyAllRecords>false</modifyAllRecords>
    </objectPermissions>
    <!-- repeat for PRM_AsyncJobDetails__c and PRM_AsyncJobRecords__c; field/tab permissions per object -->
</PermissionSet>
```

---

## A6 · Deployment & sequencing

1. Objects first: `PRM_AsyncJob__c`, then its two M-D children `PRM_AsyncJobRecords__c` and `PRM_AsyncJobDetails__c` (both reference the Job).
2. `PRM_AsyncJobConfig__mdt` type + config records (one **per batch step** per process — see A7).
3. `PRM_AsyncJob_Access` permission set.
4. Command: `sf project deploy start -d force-app/main/default/objects/PRM_AsyncJob__c force-app/main/default/objects/PRM_AsyncJobRecords__c force-app/main/default/objects/PRM_AsyncJobDetails__c ...`

---

## A7 · Testing strategy

> **Test architecture.** Quality is enforced through a layered **test pyramid** — Apex and LWC unit suites at the base, a thin **UI/E2E (Selenium-style)** layer at the top — wired into CI as **gating quality checks** on every `epic-*` branch. Each run emits **deterministic, versioned evidence artifacts** (coverage reports + per-step UI captures) consolidated into a single **Test Evidence Report**, traceable to the Epic's deliverables and attached to the PR. The agent owns **automation and evidence assembly**; a **human governance gate** — independent validation and sign-off — is a mandatory control before promotion to a higher environment. UI captures are emitted by the browser-automation harness and embedded as build artifacts (generated, not manually taken).

### Test layers

| Layer | Scope | Tooling | Agent role |
| --- | --- | --- | --- |
| **Apex unit** | objects/triggers/services/orchestrator (`PRM_AsyncJobTrigger`, `PRM_AsyncOrchestrator`, the five batch classes, cleanup batch) | `sf apex run test --code-coverage --result-format json` | author `*Test` classes (≥ 85% per CLAUDE.md), run, parse pass/fail + coverage |
| **LWC unit** | `prmAsyncJobProgress` + its Apex controller | `sfdx-lwc-jest` (`npm run test:unit:coverage`) | author Jest specs, run, parse coverage |
| **UI / E2E (Selenium-style)** | Case-Manager page → `prmAsyncJobProgress` (progress, refresh, retry) against a scratch/sandbox org | Selenium WebDriver / Playwright / Salesforce **UTAM** | author page-object specs, run headless, capture a screenshot per step/assertion |

### Evidence captured per run

- **Apex:** JUnit/JSON results + per-class coverage table + org-wide coverage %.
- **LWC:** Jest summary + lcov/HTML coverage.
- **UI E2E:** one **screenshot per step** (intake → job queued → batch running → completed/failed → retry) + the WebDriver/Playwright run log (pass/fail per scenario).

### Test Evidence Report (the deliverable document)

The agent assembles a dated report — `docs/test-evidence/Epic_A_<date>/report.md` — containing: a summary table (suite, passed/failed, coverage %, duration); the Apex + LWC coverage tables; **embedded UI screenshots** with a caption per scenario step; and links to the raw artifacts.

```
docs/test-evidence/
└─ Epic_A_2026-06-22/
   ├─ report.md                # assembled evidence
   ├─ apex-coverage.json
   ├─ lwc-coverage/            # lcov + html
   └─ ui/
      ├─ 01-intake.png
      ├─ 02-job-queued.png
      ├─ 03-batch-running.png
      ├─ 04-completed.png
      └─ 05-retry.png
```

### Acceptance

- Apex ≥ **85%** per class (org policy); all suites green.
- Every UI scenario has a captured screenshot + a passing assertion.
- The report is regenerated and attached on each `epic-*` PR into `main`.

### Human-in-the-loop

- Agent automation **does not replace** human verification — the team independently tests at their end to confirm the feature works as required.
- **Manual / exploratory + UAT:** a team member runs the key flows in a sandbox (intake → batches → progress LWC → retry) beyond the scripted scenarios.
- **Review gate:** the team reviews the agent's Test Evidence Report (coverage + screenshots), spot-checks records in the org, and **signs off** on the PR before the `main` → `master` promotion.
- **Escalation:** any agent-flagged failure or ambiguous result is triaged by a human before merge; the sign-off is recorded on the PR.

### Agent capability boundary

- The agent **authors** the specs, **runs** them via CLI, **collects** the tool-generated screenshots + coverage, and **assembles** the evidence report.
- UI screenshots are produced by the **browser-automation harness** (Selenium/Playwright/UTAM), not by the agent viewing the UI — this requires a reachable org + browser driver in the runner. Where no org/driver is available, the agent delivers the Apex/LWC report and stubs the UI section with the specs + expected screenshots.

---

## A8 · Git strategy

Work is branched by **EPIC + component**. The shared/generic layer (foundation base classes, selectors, async framework) is built and merged before its consumers, so the generic layer is stable before the service/batch epics fork off it.

### Branch model

| Branch | Role |
| --- | --- |
| `master` | Protected **release** line (repo default branch). Tagged at each release (`v1.0`, `v1.1`, …); deploys to the **higher environment** via `sf project deploy start`. Only `main` merges in. |
| `main` | **Integration** branch. Epic branches merge here via PR; CI (lint · LWC jest · Apex tests) gates it. Promoted to `master` at epic milestones / release (tagged). |
| `epic-<x>/<component>` | Short-lived working branches cut from `main`, one cohesive deliverable each. |

**Naming:** `epic-<letter>/<kebab-component>` — e.g. `epic-a/async-data-model`, `epic-b/foundation-base-classes`, `epic-c/async-orchestrator`, `epic-d/selectors`, `epic-e/case-service`, `epic-e/practitioner-service`.

**Commit convention:** prefix with the plan task id — e.g. `[A1] add PRM_AsyncJob__c object`, `[E2] PRM_PractitionerService HCP + NPI build`.

### Shared classes across epics

1. **Single-owner rule** — every shared/generic class has one owning epic that creates it (foundation/base classes → EPIC B; selectors → EPIC D; async framework → EPIC C). No two branches create or refactor the same class in parallel.
2. **Sequence the shared layer first** — build & merge **B → C → D** into `main` before the EPIC E services branch off it.
3. **Vertical slice per service** — one branch per service (E1, E2, …), localising any edits to a shared class.
4. **Rebase often** — rebase each `epic-*` branch on `main` to absorb shared-class changes early; keep branches short-lived.
5. **Additive over edit** — extend a generic class by adding methods rather than rewriting existing ones, to minimise cross-epic churn.

### Review / merge

- Every `epic-*` branch → **PR into `main`**; require green CI + 1 review.
- **Squash-merge** into `main` to keep history readable; merge `main` → `master` at epic completion / release and tag.
- Rollback = revert the merge commit, or re-point the deploy to the previous release tag on `master`.

---

## A9 · Open items


| Ref                                        | Item                                                                                                     | Status / Action                                                                                                                                                   |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL-6 *(resolved)*                          | High-volume async target object(s) for Practitioner Creation                                            | **Resolved:** target is **`HealthcareFacilityNetwork`** (E17 async + E18 batch; RTs `PRM_FacilityNw` · `PRM_FacilityTx` · `PRM_FacilityPractitionerTxNw`). `NetworkMember`/`NetworkMemberChunk` belong to the existing **roster-sync** framework (`PRM_AsyncProcess__c`) — **not reused** (CL-1/G-1), out of pilot scope. |
| Async config rows *(async-only redesign)*  | `PRM_AsyncJobConfig__mdt` rows the pilot needs                                                          | **Seed one row per batch step under `PRM_ProcessName__c = 'Practitioner Creation'`**, sequenced via `PRM_Sequence__c`; `PRM_ServiceClassName__c` = the **batch class** name. Confirmed order: **1** `PractitionerBatch` → **2** `PracticeLocationAndGroupBatch` → **3** `GroupRelatedBatch` → **4** `PLRelatedBatch` → **5** `Level4RecordCreationBatch`. Each batch wraps its associated EPIC E service(s) and branches IBC vs Delegated internally. Hosted-service mapping: **Plan §8.1**. |
| Batch↔service mapping *(mostly resolved — CL-15)* | Which EPIC E services (E2–E18) run inside each batch                                              | **Mapping captured in Plan §8.1.** Residual: `GroupRelatedBatch` services **TBD**. E1 = sync intake (not a batch); `PractionerPracticeLocationService` = sub-service of E14 `PRM_HPFService`. |


