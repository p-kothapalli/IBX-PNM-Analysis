# USER STORY: Set Re-Cred Term on Case Manager when closing a Re-Cred PSV / QC case via the Close Case button

**Persona:** Credentialing Specialist (primary). Stakeholders: Reporting Specialist, Business Admin.
**Priority:** P1 (AI-estimated — confirm with team)
**OmniScript:** `PRM_CloseCaseGuidedFlow_English`
**Integration Procedures:** `PRM_FetchDetailsParent` (load), `PRM_ReviewParCaseRecordsUpdateParent` (submit)
**Relevant Requirements:** `requirements/ReCred_PSV_to_RCAT_DirectPush_Guide.md`, `training-docs/CommitteeReview/02_RCAT_Committee_Review.md`

---

## Story

**As a** Credentialing Specialist,
**I want** the Close Case button to mark a re-credentialing Case Manager as "Re-Cred Term" whenever I close its PSV or QC Review case,
**So that** the practitioner automatically appears on the RCAT (Re-Credentialing Committee) screen for termination, instead of getting stuck in "Pending Closure" and never reaching RCAT.

**Why it matters:** Today, closing a re-cred PSV/QC case via the Close Case button flips the Case Manager to **Pending Closure** but leaves **Re-Cred Term** unset. The RCAT screen only surfaces cases that are *both* `Pending Closure` **and** `Re-Cred Term = true`, so these practitioners silently fall out of the termination pipeline and require a manual data fix (`scripts/ReCredPSVToRCAT.apex`) to recover.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Close Case | `PRM_CloseCaseGuidedFlow_English` | `SetRecordsOtherType` (Set Values) | `PRMExtractCaseDetails` (fetch) → submit via `PRM_ReviewParCaseRecordsUpdateParent` |

**In scope:** Re-Credentialing Case Managers whose closed case `Type` is **PSV** or **QC Review**.
**Out of scope:** Application Review closes, QM Review closes (`SetRecordsQMReview`), and all initial-credentialing record types.

---

## Preconditions

- The Case Manager (`IndividualApplication`) record type is **Re-Credentialing** (`PRM_ReCredentialing`).
- The case being closed has `Type = 'PSV'` or `Type = 'QC Review'`.
- A Denial Reason is entered (the Close Case submit already requires this today).

---

## Current State (from codebase)

### `PRM_CloseCaseGuidedFlow_English` — `SetRecordsOtherType` (active)

- Shown when case `Type` is `Application Review`, `PSV`, or `QC Review`.
- Updates the Case Manager (`IndividualApplication`) with `Status = 'Pending Closure'`, `PRM_Decision_Date__c = TODAY`, `PRM_DenialReason__c`.
- **Does NOT set `PRM_RecredTerm__c`** — this is the gap.
- Location: `vlocity_export/OmniScript/PRM_CloseCaseGuidedFlow_English/..._Element_SetRecordsOtherType.json`

### `PRMExtractCaseDetails` (load DataRaptor)

- Already derives `Case:IsRecredentialing = IF(CaseManager:RecordType.DeveloperName == 'PRM_ReCredentialing', true, false)`.
- Already returns `Case:Type` and `CaseManager:PRM_RecredTerm__c`.
- So the recredentialing indicator and case type are **already available** to the OmniScript as merge fields after the load step — no new fetch fields are required.
- Location: `force-app/main/default/omniDataTransforms/PRMExtractCaseDetails_1.rpt-meta.xml`

### RCAT pickup criteria (unchanged — the reason this matters)

`PRM_RCATProcessingService.screenRecords()` selects Case Managers where `Status = 'Pending Closure'` **AND** `PRM_RecredTerm__c = true` **AND** record type = Re-Credentialing.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`SetRecordsOtherType`** | OmniScript Set Values element | Add `PRM_RecredTerm__c` to the `RecordsToUpdate:IndividualApplication` map, set via a conditional formula. |

### Proposed formula

Add to `RecordsToUpdate.IndividualApplication` inside `SetRecordsOtherType`:

```
"PRM_RecredTerm__c": "=IF(%CaseDetails:IsRecredentialing% == true && (%CaseDetails:Type% == 'PSV' || %CaseDetails:Type% == 'QC Review'), true, null)"
```

- Returns `true` only for a re-cred PSV/QC close.
- Returns `null` for Application Review, initial-cred, or any non-matching case, leaving the field untouched (`term_only` decision — no other fields are modified).
- `Status = 'Pending Closure'` (existing) is retained; together they satisfy the RCAT pickup.

### Notes

- No new custom fields, objects, permission sets, or DataRaptor changes are needed.
- A new version of `PRM_CloseCaseGuidedFlow_English` must be activated and deployed.
- The submit IP `PRM_ReviewParCaseRecordsUpdateParent` writes `RecordsToUpdate` as-is, so no IP change is required.

---

## Acceptance Criteria

**AC-1 — Closing a Re-Cred PSV case marks the Case Manager as Re-Cred Term**

**Given** a Credentialing Specialist is on a re-credentialing practitioner's PSV case,
**When** they complete the Close Case guided flow (enter a denial reason and confirm),
**Then** the Case Manager's status becomes "Pending Closure",
**And** the Case Manager is flagged as "Re-Cred Term",
**And** the practitioner subsequently appears on the RCAT screen for termination.

**AC-2 — Closing a Re-Cred QC Review case marks the Case Manager as Re-Cred Term**

**Given** a Credentialing Specialist is on a re-credentialing practitioner's QC Review case,
**When** they complete the Close Case guided flow,
**Then** the Case Manager's status becomes "Pending Closure",
**And** the Case Manager is flagged as "Re-Cred Term",
**And** the practitioner appears on the RCAT screen.

**AC-3 — Initial-credentialing PSV/QC closes are unaffected**

**Given** a Credentialing Specialist closes a PSV or QC Review case for an **initial-credentialing** practitioner,
**When** they complete the Close Case guided flow,
**Then** the Case Manager's status becomes "Pending Closure" as before,
**And** the "Re-Cred Term" flag is **not** set,
**And** the practitioner does **not** appear on the RCAT screen.

**AC-4 — Application Review closes do not set Re-Cred Term**

**Given** a Credentialing Specialist closes an **Application Review** case (re-cred or initial),
**When** they complete the Close Case guided flow,
**Then** the "Re-Cred Term" flag is **not** set by this action.

**AC-5 — Existing close behavior is preserved**

**Given** any case closed through the Close Case button,
**When** the flow completes,
**Then** the case is set to "Closed" with the entered denial reason,
**And** the Case Manager's decision date and denial reason are stamped exactly as they are today,
**And** no field other than "Re-Cred Term" changes behavior as a result of this story.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CloseCaseGuidedFlow_English` → `SetRecordsOtherType` | Modified OmniScript Set Values element (new OS version) | Add conditional `PRM_RecredTerm__c` to the IndividualApplication update map | Drives AC-1 through AC-4 |
| `PRMExtractCaseDetails` | No change | Already exposes `IsRecredentialing` and `Type` | Used by the new formula |
| `PRM_ReviewParCaseRecordsUpdateParent` | No change | Persists `RecordsToUpdate` as submitted | Drives AC-5 |

---

## Definition of Done

- [ ] `SetRecordsOtherType` sets `PRM_RecredTerm__c = true` only for re-cred PSV / QC Review closes.
- [ ] Re-cred Application Review and all initial-cred closes leave `PRM_RecredTerm__c` untouched.
- [ ] Existing close behavior (Case → Closed, decision date, denial reason, Pending Closure) is unchanged.
- [ ] A closed re-cred PSV/QC practitioner appears on the RCAT screen (`PRM_ReviewRCAT_English`).
- [ ] New OmniScript version activated and deployed to QA, verified by a Credentialing Specialist.
- [ ] Regression: QM Review close (`SetRecordsQMReview`) and PDA/other flows unaffected.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Final priority — is this a P1 enhancement or a P0 production fix given practitioners are currently stranded? | Sprint placement | Product / Ops |
| 2 | Should a re-cred close ever be a *non-termination* close (i.e., a PSV/QC case closed for reasons that should NOT go to RCAT)? If so, gating must move from "always" to reason-based. | Could re-route legitimate non-term closures into termination | BA / Ops |
| 3 | Should an audit note ("Closed to RCAT / Final Development") be added to the Case Manager for traceability, matching the OmniScript FD path? | Reporting / audit | BA |
| 4 | Backfill — are there existing re-cred Case Managers already in `Pending Closure` with `Re-Cred Term` unset that need the one-time `ReCredPSVToRCAT.apex` fix? | Data remediation | Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_CloseCaseGuidedFlow_English` | OmniScript | MEDIUM | One Set Values element changes; new version + activation required |
| RCAT intake (`PRM_RCATProcessingService`) | Apex | LOW | No code change; benefits from correctly-flagged inflow |
| QM Review / PDA / initial-cred closes | OmniScript paths | LOW | Must remain unaffected (regression) |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `SetRecordsOtherType` formula | OmniScript element edit | M | Single conditional field add |
| OmniScript version + deploy | Config/deploy | S | New version, activate, migrate |
| QA verification (PSV, QC, App Review, initial-cred, RCAT appearance) | Test | M | 5 AC paths |

**Total Estimated Effort:** ~M (half day) — AI-estimated, validate with team.
