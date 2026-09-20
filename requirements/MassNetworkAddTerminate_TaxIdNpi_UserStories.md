# Mass Network Add / Terminate by Tax ID + NPI — User Stories

**Vertical:** Provider Network Management (PNM) — Provider Data Management (PDM)
**Persona:** PDM Specialist
**Priority:** P1
**Delivery surface:** "Add / Remove Networks" tile in the shared **Mass Update Hub** (`prmMassUpdateHub`), reusing the Wave 4 async framework and mass batches — **not** a net-new app.
**OmniScript:** N/A (LWC tile dashboard). Individual-record precedent: `PRM_PDMManualUpdate_English` → `CB_AddRemoveNetworks` → `DRLoadManualUpdatePLNetworks`
**Integration Procedures:** `PRM_SubmitAsyncJob` (intake → staging + event)
**Batch (reused, Wave 4):** `PRM_MassAddNetworkBatch`, `PRM_MassRemoveNetworkBatch`
**Async backbone (reused):** `PRM_AsyncJobRequest__c`, `PRM_AsyncJobQueued__e`, `PRM_AsyncJobQueuedTrigger`, `PRM_AsyncJobDispatcher`, `PRM_PDMJobStatusCard` (FlexCard), `PRM_FailedRecordStaging__c` (DLQ), `PRM_ExceptionLogEvent__e` / `PRM_ExceptionLogger`
**Validation (reused):** `prmCheckClosedNetworkLogic`, `PRM_ClosedNetworkConfig__mdt`
**Cell UI (reused):** `prmAddNetworks`, `prmEditBlockMultiSelect`
**Mockups:** `docs/implementation-plan/prmMassUpdateNetworks_Mockup.html`, `docs/implementation-plan/prmMassUpdateHub_Mockup.html`
**Relevant Requirements:** `requirements/Enhancements/MassGrid_Reuse_And_CrossFlow_Analysis.md` (§2.1 op #9 "Networks"), `requirements/Enhancements/HighVolume_GuidedFlows_Performance_Estimation.md`, `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` (effective-date rule precedent), `requirements/UPHS_MASS_LOAD_SOLUTIONS.md`

---

## Epic context (shared by both stories)

A PDM Specialist frequently receives a contracting instruction that reads *"add"* or *"terminate"* a set of health-plan **networks** for an entire group — identified by a **Tax ID + Group NPI** combination — that must apply to **every practice location** under that group **and** **every practitioner practicing at those locations**. Today this is done one record at a time in `PRM_PDMManualUpdate_English` (`CB_AddRemoveNetworks`), which caps at roughly 30 network records before hitting governor limits and forces the specialist to open and edit each location/practitioner by hand.

These two stories add a **mass** path on the already-planned shared async framework: one Tax ID + NPI submission fans out across three network-participation object types, processed asynchronously with after-the-fact QC.

### Network object model (grounded)

| Level | Object | What one record represents |
|---|---|---|
| Practice location | `HealthcareFacilityNetwork` (HFN) | A location's participation in a network |
| Practitioner at a location | `PractitionerLocationNetwork` (PLN) | A practitioner's participation in a network **at a specific location** |
| Practitioner (group-wide) | `PractitionerNetwork` (PN) | A practitioner's participation in a network |

> Both stories touch **all three** (per scoping decision): the location links (HFN) and, for every practitioner at those locations, the practitioner-at-location links (PLN) **and** the practitioner-level links (PN).

### Shared scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Network Add | `prmMassUpdateHub` → "Add / Remove Networks" tile | Identify → Review → Confirm → Progress → QC | `PRM_SmartAddressSearch` / group resolver by Tax ID + NPI → `PRM_SubmitAsyncJob` → `PRM_MassAddNetworkBatch` |
| Mass Network Terminate | Same tile (action = Terminate) | Same 5 steps | Same resolver → `PRM_SubmitAsyncJob` → `PRM_MassRemoveNetworkBatch` |

**Out of scope (both):** taxonomy/specialty changes, capitation-site assignment, panel-status flips, address changes (separate Mass Update Hub tiles); the roster-sync framework (`PRM_AsyncProcess__c`); historical data backfill. Individual-record `PRM_PDMManualUpdate_English` network editing is unchanged.

---

# USER STORY 1: Mass **Add** Networks for a Tax ID + NPI (locations + practitioners at those locations)

## Story

**As a** PDM Specialist,
**I want** to add one or more networks to every practice location under a given Tax ID + Group NPI — and to every practitioner practicing at those locations — in a single submission,
**So that** a group's new network participation is applied consistently across the whole group in minutes instead of editing hundreds of records by hand.

**Why it matters:** Network adds for a newly contracted group routinely span 10–20 locations and 100+ practitioners; the current one-at-a-time flow hits governor limits (~30 network records) and takes days, causing directory inaccuracy and delayed claims eligibility.

---

## Acceptance Criteria

**AC-1.1 — Resolve the group by Tax ID + NPI**

**Given** a PDM Specialist opens the "Add / Remove Networks" tile with the action set to **Add**,
**When** they enter a valid Tax ID and Group NPI and continue,
**Then** the system resolves and displays every active practice location under that group **and** every practitioner practicing at those locations, with a count of each,
**And** the specialist can review and deselect specific locations or practitioners before submitting.

**AC-1.2 — Select networks and submit asynchronously**

**Given** the group is resolved and at least one location or practitioner is selected,
**When** the specialist selects one or more networks, sets an effective date, enters a mandatory reason, and clicks Submit,
**Then** the submission is accepted and returns within a few seconds with a job reference,
**And** the heavy record creation runs in the background,
**And** the specialist can watch the job move from Queued → Processing → Completed and is free to leave the page.

**AC-1.3 — Networks are added at location and practitioner levels** *(pair with Pattern E below)*

**Given** an accepted Add job for the selected networks and effective date,
**When** the background job completes,
**Then** each selected practice location participates in each selected network (a location network link),
**And** each selected practitioner participates in each selected network **at each of those locations** (a practitioner-at-location network link),
**And** each selected practitioner participates in each selected network at the group level (a practitioner network link),
**And** every created link carries the effective date, the correct active/pending state, and is stamped to the job's case manager for the group.

**AC-1.4 — Record & Field Specification for an Add** *(Pattern E — records created on job completion)*

**Given** an Add job completes for a selected network,
**When** the records are written,
**Then** the following records are created/updated exactly as specified (business labels; API mapping in Technical Implementation; effective-date fields follow AC-1.5):

**Practice Location Network (`HealthcareFacilityNetwork`) — Create (one per location × network)**

| Field | Value | Notes |
|---|---|---|
| Practice Location | {Resolved HealthcareFacility} | lookup |
| Network | {Selected network} | |
| Effective From | per AC-1.5 | |
| Effective To | per AC-1.5 | typically blank on add |
| Active | per AC-1.5 | |
| Pending | TRUE until effective/activated, else FALSE | per AC-1.5 |
| Case Manager | {Job Case Manager for the group} | correlation |

**Practitioner-at-Location Network (`PractitionerLocationNetwork`) — Create (one per practitioner × location × network)**

| Field | Value | Notes |
|---|---|---|
| Practitioner | {Resolved practitioner Account} | lookup |
| Practice Location | {Resolved HealthcareFacility} | lookup |
| Network | {Selected network} | |
| Effective From | per AC-1.5 | |
| Effective To | per AC-1.5 | |
| Active | per AC-1.5 | |
| Pending | per AC-1.5 | |
| Case Manager | {Job Case Manager for the group} | |

**Practitioner Network (`PractitionerNetwork`) — Create (one per practitioner × network, if none active)**

| Field | Value | Notes |
|---|---|---|
| Practitioner | {Resolved practitioner Account} | lookup |
| Network | {Selected network} | |
| Effective From | per AC-1.5 | |
| Effective To | per AC-1.5 | |
| Active | per AC-1.5 | |
| Pending | per AC-1.5 | |
| Case Manager | {Job Case Manager for the group} | |

**AC-1.5 — Effective-date & active rules for added links** *(Pattern D)*

**Given** any link created by AC-1.4,
**When** the job sets its dates,
**Then** the following rules apply uniformly:

- **Effective From =** {Effective Date of Change entered on the form}
- **Effective To =** NULL (unless an end date was supplied on the form, then {supplied Effective To})
- **Active =**
  - If Effective From ≤ TODAY and (Effective To is NULL or Effective To > TODAY) → Active (TRUE)
  - Else → Inactive (FALSE)
- **Pending =**
  - If Effective From > TODAY (future-dated) → TRUE (activation deferred to Future-Dated Processing)
  - Else → FALSE
- **Case Manager =** the job's case manager for the group

**AC-1.6 — Closed / directional network routes to contracting (edge)**

**Given** one or more selected networks is a closed or directional network per the closed-network configuration,
**When** the specialist submits,
**Then** those location/practitioner links are **not** silently created,
**And** they are flagged in Review and routed to a Provider Contracting child case for approval,
**And** the non-closed networks in the same submission still process normally.

**AC-1.7 — Already-participating links are skipped (idempotency edge)**

**Given** a location or practitioner already has an **active** participation in a selected network,
**When** the Add job runs,
**Then** no duplicate link is created for that record/network,
**And** the run reports it as "already participating" rather than an error.

**AC-1.8 — Partial-failure isolation (edge)**

**Given** one or more records in the resolved scope fail to write,
**When** the Add job runs the remaining scope,
**Then** each failed record is staged to the dead-letter queue with its error and is retryable,
**And** the successfully created links persist,
**And** the specialist sees the failed count and can retry the failures without re-running the whole submission.

**AC-1.9 — After-the-fact QC via Case Manager Associations**

**Given** an Add job completes,
**When** the specialist opens the resulting QC case,
**Then** there is one QC association record per created network link (location and practitioner) to verify,
**And** the specialist can mark associations Verified or Flagged.

**AC-1.10 — Invalid or termed group (negative)**

**Given** a Tax ID + NPI combination that matches no active group (or a fully termed group),
**When** the specialist tries to continue,
**Then** nothing is queued and no records are created,
**And** a clear "no matching active group" message is shown.

---

# USER STORY 2: Mass **Terminate** Networks for a Tax ID + NPI (locations + practitioners at those locations)

## Story

**As a** PDM Specialist,
**I want** to terminate one or more networks from every practice location under a given Tax ID + Group NPI — and from every practitioner practicing at those locations — in a single submission with a termination date,
**So that** a group's exit from a network is applied consistently and on-date across the whole group, keeping the directory and claims eligibility accurate.

**Why it matters:** Network terminations for a group carry claims and directory-accuracy risk if a single location or practitioner is missed; the manual flow is slow and error-prone, and leaves stale active participation behind.

---

## Acceptance Criteria

**AC-2.1 — Resolve the group by Tax ID + NPI**

**Given** a PDM Specialist opens the "Add / Remove Networks" tile with the action set to **Terminate**,
**When** they enter a valid Tax ID and Group NPI and continue,
**Then** the system resolves and displays every active practice location under that group and every practitioner practicing at those locations, showing their current participation in the networks being terminated,
**And** the specialist can deselect specific locations or practitioners before submitting.

**AC-2.2 — Select networks + termination date and submit asynchronously**

**Given** the group is resolved and at least one location or practitioner is selected,
**When** the specialist selects the networks to terminate, sets a termination (effective) date, enters a mandatory termination reason, and clicks Submit,
**Then** the submission is accepted and returns within a few seconds with a job reference,
**And** the terminations run in the background with a live Queued → Processing → Completed status.

**AC-2.3 — Networks are terminated at location and practitioner levels** *(pair with Pattern E below)*

**Given** an accepted Terminate job,
**When** the background job completes,
**Then** each selected location's participation in each selected network is effective-dated closed,
**And** each selected practitioner's participation in each selected network **at those locations** is effective-dated closed,
**And** each selected practitioner's group-level participation in each selected network is effective-dated closed **only when it is the last remaining active location link for that network** (otherwise the group-level link stays active),
**And** every updated link is stamped to the job's case manager for the group.

**AC-2.4 — Record & Field Specification for a Terminate** *(Pattern E — records updated on job completion)*

**Given** a Terminate job completes for a selected network,
**When** the records are written,
**Then** the following records are updated exactly as specified (effective-date fields follow AC-2.5):

**Practice Location Network (`HealthcareFacilityNetwork`) — Update (one per active location × network)**

| Field | Value | Notes |
|---|---|---|
| Effective To | per AC-2.5 | = termination date (normal case) |
| Active | per AC-2.5 | |
| Is Error Record | per AC-2.5 | TRUE if Effective From ≥ termination date |
| Pending | FALSE | per AC-2.5 |
| Case Manager | {Job Case Manager for the group} | |

**Practitioner-at-Location Network (`PractitionerLocationNetwork`) — Update (one per active practitioner × location × network)**

| Field | Value | Notes |
|---|---|---|
| Effective To | per AC-2.5 | |
| Active | per AC-2.5 | |
| Is Error Record | per AC-2.5 | |
| Pending | FALSE | |
| Case Manager | {Job Case Manager for the group} | |

**Practitioner Network (`PractitionerNetwork`) — Update (only when last remaining active location link for the practitioner × network)**

| Field | Value | Notes |
|---|---|---|
| Effective To | per AC-2.5 | |
| Active | per AC-2.5 | |
| Is Error Record | per AC-2.5 | |
| Pending | FALSE | |
| Case Manager | {Job Case Manager for the group} | |

**AC-2.5 — Effective-date & error-record rules for terminated links** *(Pattern D — mirrors the RCAT `resolveEffectivity` rule)*

**Given** any link touched by AC-2.4,
**When** the job calculates its dates,
**Then** the following rules apply uniformly:

- **If the link's Effective From is on or after the Termination Date → it is an error record:**
  - Effective From = TODAY
  - Is Error Record = TRUE
  - Active = FALSE
  - Effective To = NULL
  - Pending = FALSE
- **Else, resolve Effective To against the Termination Date:**
  - Effective To is blank → set Effective To = Termination Date (normal case)
  - Effective To is **prior to** the Termination Date → leave unchanged (already ended earlier)
  - Effective To is **after** the Termination Date → set Effective To = Termination Date
- **Active =** TRUE if Effective From ≤ TODAY and Effective To > TODAY; otherwise FALSE (future-dated terminations stay Active until the date arrives, then close via Future-Dated Processing)
- **Case Manager =** the job's case manager for the group

**AC-2.6 — Practitioner left with no remaining active network (edge → QC)**

**Given** terminating the selected networks would leave a practitioner with **no remaining active network** at a location,
**When** the Terminate job runs,
**Then** that practitioner/location is flagged for QC review to confirm intent,
**And** the termination still applies but the flag surfaces on the QC case.

**AC-2.7 — Already-terminated / earlier-ended links unchanged (edge)**

**Given** a link that is already inactive or whose Effective To is already before the termination date,
**When** the Terminate job runs,
**Then** that link is left unchanged (no re-termination, no error).

**AC-2.8 — Partial-failure isolation (edge)**

**Given** one or more records in scope fail to update,
**When** the Terminate job runs the remaining scope,
**Then** each failed record is staged to the dead-letter queue with its error and is retryable,
**And** the successful terminations persist,
**And** the failures can be retried without re-running the whole submission.

**AC-2.9 — After-the-fact QC via Case Manager Associations**

**Given** a Terminate job completes,
**When** the specialist opens the resulting QC case,
**Then** there is one QC association record per terminated link (location and practitioner) to verify,
**And** links flagged by AC-2.6 are visibly marked.

**AC-2.10 — Invalid or termed group (negative)**

**Given** a Tax ID + NPI combination that matches no active group,
**When** the specialist tries to continue,
**Then** nothing is queued and no records are updated,
**And** a clear "no matching active group" message is shown.

---

## Technical Implementation (high-level)

> Assembly on the shared Wave 4 async framework (per `MassGrid_Reuse_And_CrossFlow_Analysis.md` — Networks = "zero new batch work; only UI plumbing"). No whole-submission synchronous DML; per-batch governor isolation with per-row DLQ.

| Component | Type | Change | Notes |
|---|---|---|---|
| `prmMassUpdateHub` → `prm_gridCellNetworks` / `prmAddNetworks` | LWC (reuse/config) | Wire the "Add / Remove Networks" tile: Tax ID + NPI identify, network multi-select, scope toggle (locations / practitioners), review grids | Drives AC-1.1/1.2, AC-2.1/2.2; mockup `prmMassUpdateNetworks_Mockup.html` |
| Group resolver by Tax ID + NPI | Apex (reuse) | Resolve HealthcareFacility set + practitioners-at-locations from Tax ID + Group NPI | Reuse `PRM_SmartAddressSearch` / `PRM_LocationQueryService` / `PRM_PARProviderSearch`; Drives AC-1.1, AC-2.1 |
| `PRM_SubmitAsyncJob` (IP) | IP (reuse) | Capture payload (networks, effective/term date, reason, selected scope, action) → `PRM_AsyncJobRequest__c` → fire `PRM_AsyncJobQueued__e` | `FlowType='MassNetworks'`, `SubType='Add'|'Terminate'`; Drives AC-1.2, AC-2.2 |
| `PRM_AsyncJobDispatcher` | Apex (mode-extend) | Route `SubType` to `PRM_MassAddNetworkBatch` / `PRM_MassRemoveNetworkBatch`, scoped to HFN + PLN + PN | ~1 SP switch case; Drives AC-1.3, AC-2.3 |
| `PRM_MassAddNetworkBatch` | Batch Apex (reuse) | Bulk create HFN + PLN + PN with idempotency (skip active dupes) | Drives AC-1.3/1.4/1.7 |
| `PRM_MassRemoveNetworkBatch` | Batch Apex (reuse) | Bulk close HFN + PLN + PN; PN only on last-remaining-link; skip already-ended | Drives AC-2.3/2.4/2.7 |
| Effective-date resolver | Apex (reuse) | Add uses AC-1.5 rules; Terminate routes through the RCAT `resolveEffectivity` rule (AC-2.5) | Single source of truth across levels; Drives AC-1.5, AC-2.5 |
| Future-Dated Processing | Apex (reuse/verify) | Future-dated adds/terminations activate/close on date via `PRM_FutureDatedProcessingBatch` | Requires `PRM_IsActive__c=true` filter (tracked risk); Drives AC-1.5, AC-2.5 |
| `prmCheckClosedNetworkLogic` + `PRM_ClosedNetworkConfig__mdt` | LWC + CMDT (reuse) | Closed/directional detection + Provider Contracting child-case routing on Add | Drives AC-1.6 |
| Last-remaining scoping | Apex | Compute whether a PN link is the last active location link before closing it | Drives AC-2.3, AC-2.6 |
| `PRM_FailedRecordStaging__c` (DLQ) + `prmBatchRecordException` | Object + LWC (reuse) | Per-row failure staging + Data Admin retry | Drives AC-1.8, AC-2.8 |
| `PRM_CaseManagerAssociation__c` | Object (reuse) | One QC association per touched link; QC case creation on finish | Drives AC-1.9, AC-2.9 |
| `PRM_PDMJobStatusCard` (FlexCard) + async email templates | FlexCard + Email (reuse) | Live status + completion notification | Drives AC-1.2, AC-2.2 |
| `PRM_ExceptionLogger.logExceptionViaEvent` | Apex (reuse) | Rollback-safe logging in every catch | Drives AC-1.8, AC-2.8 |

**Reuse-first principle:** the batches, staging, dispatcher, event, FlexCard, closed-network validation, and the QC association object all pre-exist (Wave 1/Wave 4 + existing PDA-QC LWCs). This story is **UI plumbing + dispatcher mode-extension + practitioner-level (PLN/PN) scoping + QC association fan-out**, not a ground-up build.

---

## Definition of done

- [ ] Add: resolving a Tax ID + NPI creates location (HFN), practitioner-at-location (PLN), and practitioner (PN) network links with correct effective dating (AC-1.1–1.5) — verified in QA.
- [ ] Terminate: resolving a Tax ID + NPI closes HFN + PLN links and PN only on last-remaining-link, with the RCAT error-record rule applied (AC-2.1–2.5) — verified in QA.
- [ ] Closed/directional networks route to a Provider Contracting child case and are not silently added (AC-1.6).
- [ ] Idempotency (AC-1.7) and already-ended (AC-2.7) edge cases verified — no duplicates, no re-termination.
- [ ] Future-dated adds/terminations activate/close on date via Future-Dated Processing.
- [ ] Partial-failure rows land in the DLQ and are retryable without re-running the submission (AC-1.8, AC-2.8).
- [ ] A QC case is created with one Case Manager Association per touched link; no-remaining-network practitioners are flagged (AC-1.9, AC-2.9, AC-2.6).
- [ ] Invalid/termed Tax ID + NPI queues nothing and shows a clear message (AC-1.10, AC-2.10).
- [ ] Each mass batch stays within governor limits at scale (200+ per chunk; one bulk DML per object type); ≥85% Apex coverage incl. bulk, single, empty, and negative/error-record paths with real assertions on effective dates, Active, Is Error Record, and Case Manager.
- [ ] No regression to individual-record network editing in `PRM_PDMManualUpdate_English`.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the exact API names + effective-date field names on `HealthcareFacilityNetwork`, `PractitionerLocationNetwork`, and `PractitionerNetwork` (the field-map sign-off gate). The ACs use business labels. | Blocks Pattern E field-level build and tests | Technical / BA |
| 2 | For **Add**, are practitioner-level (`PractitionerNetwork`) links created for **every** selected network, or only where a location link is added and none active exists? (Story assumes create-if-none-active.) | PN record volume + dedup logic (AC-1.3/1.7) | BA |
| 3 | For **Terminate**, confirm the "last remaining active location link" rule that gates closing the group-level `PractitionerNetwork` (vs. always closing PN). | Correctness of practitioner-level termination (AC-2.3) | BA / Technical |
| 4 | Is the network scope **network only**, or does each network link also carry taxonomy/role (i.e., must adds clone per taxonomy × role like the delegated-create path)? | Batch record cardinality; possible `PRM_MassAddTaxonomyBatch` involvement | Technical |
| 5 | Should closed/directional networks **block** the whole submission or **split** (process open networks, route closed to contracting)? Story assumes split (AC-1.6). | Submission UX + contracting case creation | BA / Ops |
| 6 | Does the group resolver key on Group NPI = the group Account NPI, or a facility/location NPI? Confirm the exact identifier used to resolve "the group." | Resolver query correctness (AC-1.1/2.1) | Technical |
| 7 | Confirm `FlowType`/`SubType` values and that `PRM_AsyncJobDispatcher` + Wave 4 batches are deployed and can be scoped to all three network objects in one run. | Dispatcher mode-extension scope | Technical |
| 8 | QC ownership/routing: which queue owns the resulting `PRM_CaseManagerAssociation__c` QC case, and does terminate route differently than add? | QC case routing (AC-1.9/2.9) | Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `prmMassUpdateHub` / `prm_gridCellNetworks` / `prmAddNetworks` | LWC | HIGH | New tile behaviour: Tax ID+NPI identify, scope toggle, review grids, action toggle |
| `PRM_AsyncJobDispatcher` | Apex | MEDIUM | New `MassNetworks` route (Add/Terminate) scoped across HFN + PLN + PN |
| `PRM_MassAddNetworkBatch` / `PRM_MassRemoveNetworkBatch` | Batch Apex | MEDIUM | Extended to fan out to practitioner-level (PLN + PN), not just HFN |
| `PRM_SubmitAsyncJob` / `PRM_AsyncJobRequest__c` / `PRM_AsyncJobQueued__e` | IP / Object / Event | LOW | Reused as-is; new payload shape |
| `prmCheckClosedNetworkLogic` / `PRM_ClosedNetworkConfig__mdt` | LWC / CMDT | LOW | Reused for closed-network routing |
| `PRM_FutureDatedProcessingBatch` | Batch Apex | MEDIUM | Future-dated add/terminate activation/closure |
| `PRM_CaseManagerAssociation__c` | Object | MEDIUM | QC association fan-out per touched link |
| `PRM_FailedRecordStaging__c` / `prmBatchRecordException` | Object / LWC | LOW | Reused DLQ + Data Admin retry |
| `HealthcareFacilityNetwork`, `PractitionerLocationNetwork`, `PractitionerNetwork` | Objects | HIGH | Records created/updated by the fan-out |

---

## Estimated Effort

> AI-estimated — validate with team. Story points calibrated to `MassGrid_Reuse_And_CrossFlow_Analysis.md` (Networks op = "0 SP new batch work; only UI plumbing", with incremental for practitioner-level cascade + QC + future-dated).

| Component | Change Type | Effort | Story Points | Notes |
|-----------|-----------|--------|--------------|-------|
| "Add / Remove Networks" tile UI (identify, scope toggle, review grids, action toggle) | LWC config/wiring | L | 3 | Reuses hub primitives + `prmAddNetworks` |
| Group resolver by Tax ID + NPI | Apex reuse | M | 2 | Reuse `PRM_SmartAddressSearch` / `PRM_LocationQueryService` / `PRM_PARProviderSearch` |
| Dispatcher mode-extension (`MassNetworks` Add/Terminate) | Apex | M | 2 | One switch case per subtype |
| Practitioner-level fan-out (PLN + PN) in the mass batches | Batch Apex | L | 3 | Existing HFN path extended to two more objects |
| Terminate effective-date rule (reuse `resolveEffectivity`) + last-remaining scoping | Apex | M | 2 | Reuse RCAT helper; new last-remaining calc |
| Closed-network routing to contracting child case (Add) | Apex/LWC reuse | M | 2 | Reuse `prmCheckClosedNetworkLogic` |
| QC `PRM_CaseManagerAssociation__c` fan-out + QC case creation | Apex reuse | M | 2 | One association per touched link |
| Future-dated add/terminate verification | Config/verify | S | 1 | Confirm `PRM_IsActive__c=true` filter |
| Tests (bulk 200+, single, empty, negative/error-record, both actions) | Apex test | L | 3 | ≥85% coverage gate |

**Total Estimated Effort:** **XL** (~20 story points across both stories) — AI-estimated, validate with team. Lands lower if the Wave 4 batches already fan out to PLN/PN; higher if network links must clone per taxonomy × role (Clarification #4).
