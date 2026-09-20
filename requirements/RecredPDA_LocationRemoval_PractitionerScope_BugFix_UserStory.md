# USER STORY 1: ReCred PDA — Location Removal Must Only End-Date the Selected Practitioner

**Persona:** Provider Data Admin (PDA) Specialist
**Priority:** P0
**OmniScript:** `PRM_ReCredUpdate_English` (v7, active) — Removed Practitioner at Practice Location Taxonomy and Network block
**Integration Procedures:** `PRM_FetchFormRecredUpdate_Procedure` (v5, active) → DataRaptor `PRMFetchRecredUpdateData`; `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v11, active)
**Relevant Requirements:** Bug **1216121** (first of two root causes); `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §3 G1; depends on Bug **1331370**; sibling story `RecredPDA_LocationRemoval_EffectiveToDate_BugFix_UserStory.md` (US-2)

---

## Story

**As a** Provider Data Admin (PDA) Specialist,
**I want** removing a practice location from a re-credentialing case to end-date **only the practitioner I am working on** at that location,
**So that** I can process re-cred location changes without silently terminating other practitioners who still practise at the same address.

**Why it matters:** Today a single location removal can end-date affiliation, taxonomy and network rows for **other practitioners at the same facility**. That silently removes providers from networks, corrupts the provider directory, and creates claims-integrity exposure. It is the primary reason the business stopped using the ReCred PDA guided flow for location changes and moved to email workarounds.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Re-credentialing PDA Update (`Recred Updates` stage) | `PRM_ReCredUpdate_English` | Removed Practitioner at Practice Location Taxonomy and Network | `PRMFetchRecredUpdateData` (removal row set), then the re-cred termination service |

**In scope:** the row set the removal block is built from, and the termination write that follows it.
**Out of scope:** the intentional cascade that terminates the *practice location itself* when the practitioner being removed is its last active practitioner (see AC-4 — this behaviour must be preserved); the effective-to date defect (US-2).

---

## Current State (from codebase)

### Removal row set is scoped to the facility, not the practitioner

The removal set is built from three filters only:

- Case Manager matches the case being worked
- Facility matches the selected practice location
- Record type is the practitioner-at-facility taxonomy/network type

There is **no practitioner filter**. The practitioner identifier exists in the DataRaptor only as an **output** mapping, never as a filter.

- **Location:** `force-app/main/default/omniDataTransforms/PRMFetchRecredUpdateData_1.rpt-meta.xml` (extract sequence 2, `HealthcareFacilityNetwork`)

### The termination write re-stamps the Case Manager, widening the set over time

The taxonomy/network termination transform sets **Case Manager = the current case's Case Manager** on every row it writes. Because Case Manager is also the only filter limiting the removal set, each run can make additional rows eligible for the *next* run.

- **Location:** `force-app/main/default/omniDataTransforms/PRMTransTxnyForTerminationReCred_1.rpt-meta.xml`

### Compounding defect

Bug **1331370** (nightly script stamping a new Case Manager onto stale practitioner-at-location rows at terminated locations) directly widens this blast radius, because Case Manager is the only constraint on the removal set.

### The UI already signals the cascade

A warning text block displays when the count of active practitioners at the location is 1, telling the specialist the location will also be terminated. The cascade is intended; the **row scope** is not.

---

## Acceptance Criteria

> Pattern A ACs are in business language; component and field API detail is in Technical Implementation.

**AC-1 — Removal affects only the practitioner on the case**

**Given** a Provider Data Admin (PDA) Specialist is working a re-credentialing case for one practitioner in the Recred Updates stage,
**When** they remove a practice location where **other practitioners are also active**,
**Then** only the selected practitioner's affiliation, taxonomy and network rows at that location are end-dated,
**And** every other practitioner's rows at that same location remain active and unchanged,
**And** the removal review screen lists only the selected practitioner's rows.

**AC-2 — Records updated when a location is removed**

**Given** a Provider Data Admin (PDA) Specialist has removed a practice location and confirmed the termination,
**When** they submit the re-cred update,
**Then** the following records are updated exactly as specified, **for the selected practitioner only**:

**Practitioner-to-Practice-Location affiliation — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | carried forward unchanged |
| Effective To | {termination date} | per US-2's date rules |
| Active | {derived from Effective From / Effective To} | see AC-3 of US-2 |
| Pending | FALSE | |
| Is Error Record | {existing value} | carried forward |

**Practice-Location-to-Practitioner affiliation — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | carried forward unchanged |
| Effective To | {termination date} | per US-2's date rules |
| Active | {derived from Effective From / Effective To} | |
| Pending | FALSE | |
| Is Error Record | {existing value} | carried forward |

**Practitioner at Practice Location Taxonomy and Network — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | carried forward unchanged |
| Effective To | {termination date} | per US-2's date rules |
| Active | {derived from Effective From / Effective To} | |
| Pending | FALSE | |
| Is Error Record | {existing value} | carried forward |
| Case Manager | {this case's Case Manager} | see AC-5 — must not widen the next run's scope |

**AC-3 — Other practitioners at a shared location are untouched**

**Given** a practice location has four active practitioners and the case being worked covers one of them,
**When** the Provider Data Admin (PDA) Specialist removes that location and submits,
**Then** exactly one practitioner's rows carry an Effective To date,
**And** the location's count of active practitioners decreases by exactly one,
**And** no network membership changes for the other three practitioners.

**AC-4 — Last active practitioner still cascades to the location (preserved behaviour)**

**Given** the practitioner being removed is the **only** active practitioner at the practice location,
**When** the Provider Data Admin (PDA) Specialist removes that location,
**Then** the existing warning that the location will also be terminated is still displayed,
**And** the practice location is still terminated along with the practitioner's rows,
**And** this cascade continues to work exactly as it does today.

**AC-5 — Rows carrying a stale Case Manager are not pulled into the removal**

**Given** a practitioner-at-location row at the selected facility carries this case's Case Manager but belongs to a **different** practitioner,
**When** the Provider Data Admin (PDA) Specialist opens the removal step,
**Then** that row is not listed for removal,
**And** it is not end-dated on submit.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRMFetchRecredUpdateData` | Modified DataRaptor Extract | Add a practitioner-scope filter to the extract at query sequence 2 (`HealthcareFacilityNetwork`), alongside the existing `PRM_CaseManager__c`, `HealthcareFacilityId` and `PRM_RecordTypeName__c = 'PRM_FacilityPractitionerTxNw'` filters. Source the practitioner from the case's practitioner context already passed into the fetch chain. | Drives AC-1, AC-3, AC-5 |
| `PRM_FetchFormRecredUpdate_Procedure` | New IP version | Ensure the practitioner identifier is passed into the DataRaptor as a filter input (it is currently only mapped on output). | Drives AC-1 |
| `PRMFetchPPLRecredRemoval`, `PRMFetchTxNwtkReCredRemoveScenario` | Review / possible modified DataRaptor | Confirm the sibling removal-scenario extracts carry the same practitioner scope; re-point if they share the facility-only pattern. | Drives AC-3 |
| `PRMTransPPLForTerminationReCred`, `PRMTransTxnyForTerminationReCred` | Review | Confirm the termination write cannot expand beyond the fetched row set; the taxonomy transform's `PRM_CaseManager__c = CaseManagerId` stamp must not re-widen later runs. | Drives AC-2, AC-5 |
| `PRM_FullPracTermRecredBatchService`, `PRM_PractitionerTerminationBatchHelper` | Review / possible modified Apex | Verify the batch termination path honours practitioner scope for the location cascade in AC-4. | Drives AC-4 |

**Dependency:** Bug **1331370** (nightly Case Manager over-stamping) should be resolved or bounded in parallel — while Case Manager remains an over-broad value, AC-5 is only partially protective.

---

## Definition of done

- [ ] AC-1 verified in the target org on a facility with **at least three** active practitioners under one group: only the case's practitioner is end-dated
- [ ] AC-3 verified by record count: exactly one practitioner's affiliation, taxonomy and network rows carry an Effective To
- [ ] AC-4 verified: single-practitioner location still cascades to location termination, warning still displays
- [ ] AC-5 verified with a deliberately mis-stamped Case Manager row (reproduces the Bug 1331370 condition)
- [ ] No practitioner-at-location rows outside the case's practitioner are modified — confirmed by field history on a control practitioner
- [ ] ≥ 85% Apex coverage on any modified termination class, including a bulk (200-row) and a negative case
- [ ] No regression to the add-location path of the same guided flow, or to the Network Management QC step that follows it
- [ ] New OmniScript / IP / DataRaptor versions **activated** and verified by a Provider Data Admin (PDA) Specialist in QA

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Which practitioner reference should the filter use — the case's practitioner contact, or the practitioner account on the Case Manager? | Determines the filter field and whether the fetch chain already carries the value | Technical |
| 2 | Should the taxonomy/network termination write continue to stamp Case Manager on the rows it touches? It is the mechanism that widens later runs. | If it stays, AC-5 needs an additional guard; if it goes, downstream reporting that joins on Case Manager may break | Technical / BA |
| 3 | Is Bug 1331370 being fixed in the same release? | If not, AC-5 is only partially protective and the release note must say so | Ops / Product |
| 4 | Are there already-damaged records in production from prior over-broad removals that need a backfill/repair? | Adds a data-remediation task outside this story | BA / Ops |
| 5 | Should the removal screen show a read-only count of "other practitioners at this location who will NOT be affected" as reassurance? | Small UI addition; improves specialist confidence at re-launch | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRMFetchRecredUpdateData` | DataRaptor | **HIGH** | The filter change is the core fix |
| `PRM_ReCredUpdate_English` | OmniScript | **HIGH** | Removal block row set changes; requires new activated version |
| `PRM_FetchFormRecredUpdate_Procedure` | Integration Procedure | MEDIUM | Must pass the practitioner as a filter input |
| `PRM_ReCredQCUpdate_English` | OmniScript | MEDIUM | Downstream QC step displays the same removal rows |
| `PRM_FullPracTermRecredBatchService` | Apex | MEDIUM | Executes the location cascade in AC-4 |
| Provider directory / network membership | Data | **HIGH** | Incorrect terminations directly affect directory accuracy and claims |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRMFetchRecredUpdateData` | DataRaptor filter | **M** | Add filter; verify against the existing three |
| `PRM_FetchFormRecredUpdate_Procedure` | IP input mapping | **M** | New version, pass practitioner as filter input |
| Sibling removal extracts | DataRaptor review / re-point | **M** | Two extracts to confirm |
| Termination path review | Apex review | **L** | Confirm scope honoured through the batch |
| Regression + multi-practitioner test data | QA | **L** | Needs a purpose-built multi-practitioner facility |

**Total Estimated Effort:** **L** (roughly 1 day of build + 1 day of regression) — AI-estimated, validate with team.
