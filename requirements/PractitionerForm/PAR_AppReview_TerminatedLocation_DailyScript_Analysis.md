# PAR App Review — "Required Fields Missing" Production Bug
## Root Cause Analysis, Business Questions & User Stories

**Reported By:** Heather  
**Environment:** Production  
**Guided Flow:** PAR-App Review  
**Date of Analysis:** April 26, 2026  
**Related Existing Documents:**
- `PAR_AppReview_TerminatedLocation_InFlight_BugFix.md` (US4)
- `PAR_DeniedTerminated_RecordReuse_User_Stories.md` (US1, US2, US3)

---

## 1. What Happened — Exact Sequence of Events

| Date | Event | Record | Detail |
|------|-------|--------|--------|
| 12/10/2025 9:28 AM | PAR submitted | IA-0000063527 | Single affiliation to Practice Location: Regional Women's Health Group LLC (247 Hurffville Crosskeys Rd Ste C3-8017) |
| 01/28/2026 5:45 AM | Practice Location **terminated** | IA-0000093618 | `HealthcareFacility.PRM_Active__c = false` set via Provider Change Request |
| 01/30/2026 9:36 AM | First PAR **denied** | IA-0000063527 | HCPF should have been marked: `IsActive=false`, `PRM_Pending__c=false` |
| 01/31/2026 9:34 AM | New PAR **re-submitted** | IA-0000096229 | **No new affiliation/HCPF was created** — gap in re-submission path (US1 issue) |
| 03/03/2026 5:33 PM | Daily script (bug 1331370) ran | IA-0000096229 | "Stamp latest Case Manager + set Pending flag for re-submitted PAR records" — Script stamped IA-0000096229 onto the **existing HCPF** (still linked to the terminated Practice Location) |
| Current | App Review attempt | IA-0000096229 | **Required Fields Missing error** — HCPF has `PRM_Pending__c=true` + `HealthcareFacility.PRM_Active__c=false` + `PRM_CaseManager__c=IA-0000096229` |

---

## 2. How This Differs From Existing US4 (PAR_AppReview_TerminatedLocation_InFlight_BugFix)

The existing **US4** document covers:
> *"Location terminated via Provider Change Request WHILE the case is in-flight (App Review stage)"*

**This reported issue is a compound scenario** that combines THREE separate gaps:

| Gap | Existing Story | Status |
|-----|---------------|--------|
| App Review fails because HCPF points to terminated Practice Location | **US4** — guard in `PRMDREGetPracticeLocation` | Proposed — not yet deployed |
| Re-submitted PAR doesn't create a new affiliation | **US1** — IP routing for denied/terminated reuse | Proposed — not yet deployed |
| **Daily script (bug 1331370) stamps new Case Manager onto HCPF without validating Practice Location is still active** | **NOT COVERED — NEW GAP** | Not analyzed |

The **new gap** is the daily script: it was designed to repair cases where re-submitted PARs had no Case Manager stamp. It did its job — but it didn't check whether the HCPF it was stamping is linked to a **terminated** Practice Location. Stamping a new Case Manager onto a stale HCPF (terminated location) and re-activating `PRM_Pending__c=true` recreated the US4 error condition artificially.

---

## 3. Root Cause Chain

```
[Step 1] PAR submitted (IA-0000063527) with Practice Location
              ↓
[Step 2] Practice Location terminated via PCR → HealthcareFacility.PRM_Active__c = false
              ↓
[Step 3] First PAR DENIED (IA-0000063527)
         → HCPF updated: IsActive=false, PRM_Pending__c=false
         → BUG US3: ExternalId NOT cleared on HCPF
              ↓
[Step 4] New PAR re-submitted (IA-0000096229)
         → BUG US1: IP routing gap → No new HCPF created for the new case
         → IA-0000096229 has no affiliation record
              ↓
[Step 5] Daily script (bug 1331370) runs
         → Finds IA-0000096229 has no Case Manager stamp
         → Finds the existing HCPF (from IA-0000063527, now IsActive=false, Pending=false)
         → Stamps: PRM_CaseManager__c = IA-0000096229, PRM_Pending__c = true
         → BUG NEW: Script does NOT check HealthcareFacility.PRM_Active__c
         → HCPF now: PRM_Pending__c=true, PRM_CaseManager__c=IA-0000096229,
                     HealthcareFacility.PRM_Active__c=false
              ↓
[Step 6] App Review for IA-0000096229
         → PRMDREGetPracticeLocation COUNTQUERY fires:
           "SELECT Count() FROM HealthcarePractitionerFacility
            WHERE HealthcareFacilityId = '{0}'
            AND PRM_Pending__c = true
            AND HealthcareFacility.PRM_Active__c = false"
         → Returns count = 1 → EligibleForUpdate = TRUE ← FALSE POSITIVE
              ↓
[Step 7] PRMDRPPractitionerDataUpdate fires:
         Active=false, Error=true, Pending=false
         → Tries to write PRM_IsErrorRecord__c=true to HCPF
         → REQUIRED FIELDS MISSING ERROR (linked HealthcareFacility is inactive)
```

---

## 4. Fix Options

### Option A: Immediate / Tactical (Unblock Production — Manual Data Correction)

For the specific records in production:
- Admin manually updates the HCPF linked to IA-0000096229:
  - Set `PRM_Pending__c = false`
  - Set `IsActive = false`
  - Set `PRM_CaseManager__c = null`
- This disconnects the stale HCPF from the new case
- The new case IA-0000096229 will need a valid practice location association created manually before App Review can proceed

**Risk:** Does not fix the underlying system behavior. Will recur.

---

### Option B: Deploy US4 Fix (Guard in PRMDREGetPracticeLocation)

The US4 guard prevents the false positive by adding a case-ownership check:

**Proposed `EligibleForUpdate` formula:**
```
IF(COUNTQUERY("SELECT Count() FROM HealthcarePractitionerFacility
  WHERE HealthcareFacilityId = '{0}'
  AND PRM_Pending__c = true
  AND HealthcareFacility.PRM_Active__c = false
  AND PRM_CaseManager__c != '{1}'",
  %HealthcarePractitionerFacility:HealthcareFacilityId%,
  %currentIndividualAppId%) == 1, true, false)
```

**Why this also fixes this specific case:**
- The HCPF now has `PRM_CaseManager__c = IA-0000096229` = `currentIndividualAppId`
- The guard condition `PRM_CaseManager__c != currentIndividualAppId` evaluates to **FALSE**
- COUNTQUERY returns **0** → `EligibleForUpdate = FALSE`
- `PRMDRPPractitionerDataUpdate` does NOT fire
- App Review proceeds

**Warning displayed to user per US4 Scenario 2:**
> *"One or more practice locations were terminated via a Provider Change Request. The credentialing review will continue. The location will be evaluated for reactivation at the PDA stage."*

**Risk:** Treats the symptom at App Review. The underlying data state (HCPF pointing to a terminated location being marked Pending=true) is still wrong. Need the daily script fix too.

---

### Option C: Fix the Daily Script (Bug 1331370) — Root Cause Prevention

Add a validation guard to the daily script before it stamps a new Case Manager:

```
BEFORE stamping PRM_CaseManager__c and PRM_Pending__c = true:
  Check: HealthcareFacility.PRM_Active__c == true
  IF false (Practice Location is terminated):
    → DO NOT stamp the HCPF
    → Log a warning/exception for manual review
    → Optionally: create a task/case for the credentialing team to select a new location
```

**Criteria for the daily script to safely stamp an HCPF:**
1. `HealthcareFacility.PRM_Active__c = true` (Practice Location must be active)
2. `HCPF.IsActive = false` AND `HCPF.PRM_Pending__c = false` (record must be a prior denied/terminated state)
3. `HCPF.PRM_IsErrorRecord__c = false` (not an error record)
4. No other HCPF for the same practitioner-group pair is currently `PRM_Pending__c = true` (avoid double-stamping)

---

### Recommended Fix Order

| Priority | Fix | Type | Effort |
|----------|-----|------|--------|
| P0 (immediate) | Manual data correction for IA-0000096229 | Admin action | Hours |
| P0 (systemic) | Deploy US4 guard in `PRMDREGetPracticeLocation` | DataRaptor formula + IP conditional | M |
| P0 (root cause) | Add Practice Location active validation to daily script (bug 1331370) | Script/Apex update | M |
| P1 | Deploy US1 (re-submission IP routing fix) | IP conditional | M |
| P1 | Deploy US3 (clear ExternalId on denial) | New DR + IP step | S-M |

---

## 5. Questions for Business

### Category A — Daily Script Behavior (Bug 1331370)

| # | Question | Why It Matters |
|---|----------|----------------|
| **A1** | The daily script for bug 1331370 was designed to stamp the latest Case Manager and set Pending=true for re-submitted PAR records. Should this script also validate that the Practice Location linked to the existing HCPF is still active (`PRM_Active__c = true`) before stamping? | Prevents the script from re-activating stale HCPF records tied to terminated locations — the direct cause of this production error |
| **A2** | When the daily script finds a re-submitted PAR case but the existing HCPF is linked to a terminated Practice Location — what should happen? (a) Skip the stamp and create an exception log / task, (b) Create a new HCPF without a practice location and require the user to select one, (c) Stamp anyway and let App Review handle it | Determines the script's error-handling path |
| **A3** | Is the daily script (bug 1331370) intended to be a permanent ongoing automation, or was it a one-time backfill? If ongoing, what is its trigger condition and recurrence schedule? | Determines whether the fix is a script update or a permanent business rule |
| **A4** | How many other records may have been incorrectly stamped by this script with terminated practice locations? Is a data audit needed to identify and remediate additional cases? | Blast radius assessment |

### Category B — Re-submission Behavior (US1 Context)

| # | Question | Why It Matters |
|---|----------|----------------|
| **B1** | When a PAR is denied and the practitioner re-submits, is the expectation that the system will reuse the existing HCPF from the denied case (update path), or always create a new HCPF? | Determines whether US1 (HCPF reuse) is the right approach or whether new record creation is required |
| **B2** | In this specific scenario, the practice location was terminated BEFORE the new PAR was re-submitted. When a practitioner re-submits a PAR for a practice location that is now terminated, should the form: (a) Block submission and require them to choose a new location, (b) Allow submission and surface a warning about the terminated location, (c) Allow submission and handle at PDA stage? | Directly impacts PAR form validation UX for the re-submission case |
| **B3** | When IA-0000096229 was re-submitted on 01/31/2026 with no new affiliation created, did the form appear to complete successfully to the user? Was any error surfaced at submission time? | Determines whether there is a silent failure at the re-submission step that needs to be surfaced |

### Category C — App Review Behavior (US4 Context)

| # | Question | Why It Matters |
|---|----------|----------------|
| **C1** | When App Review encounters an HCPF tied to a terminated practice location, should the App Review: (a) Continue with a warning (as proposed in US4), (b) Block and require the specialist to update the practice location, (c) Auto-remove the terminated location and allow App Review to proceed with remaining locations? | Determines the UX behavior of the US4 fix |
| **C2** | At the PDA stage, when the location is to be reactivated — is there a specific step that handles the case where the practice location was terminated BEFORE App Review (vs. terminated after App Review)? | Determines whether the PDA stage has a different remediation path for this scenario |
| **C3** | Should PSV, QC, and Committee Review flows also have the same guard against terminated-location false positives? These flows may hit the same error if the US4 fix is only applied to App Review. | Determines blast radius of the US4 fix |

### Category D — Data Integrity

| # | Question | Why It Matters |
|---|----------|----------------|
| **D1** | For the specific case IA-0000096229 today: should the HCPF be manually disconnected from the terminated Practice Location, and should the credentialing specialist be required to select a new/active Practice Location before App Review can proceed? | Unblocks the immediate production case |
| **D2** | Is there an existing field on `HealthcarePractitionerFacility` that distinguishes "terminated by Provider Change" vs. "removed in App Review" vs. "terminated by credentialing denial"? | Could simplify the discriminator logic in the fix |
| **D3** | When a case manager is stamped onto an existing HCPF via the daily script, should the original Case Manager (from the denied case) be preserved in a history field, or is overwriting acceptable? | Audit trail requirement |

---

## 6. User Stories

---

### USER STORY 5 (NEW): Daily Script — Validate Practice Location Active Status Before Stamping Re-submitted PAR Records

**Persona:** System Automation / Salesforce Admin  
**Priority:** P0  
**Component:** Daily Script — "Stamp latest Case Manager + set Pending flag for re-submitted PAR records" (Bug 1331370)  
**Related Stories:** US1 (denied/terminated HCPF reuse), US4 (App Review guard for terminated locations)

---

#### Story

**As a** system (and as a credentialing specialist trusting the automation),  
**I want** the daily re-submission stamping script to validate that a linked Practice Location is still active before stamping the new Case Manager and setting `PRM_Pending__c = true` on an existing HCPF record,  
**So that** the script does not artificially re-activate HCPF records tied to terminated practice locations, which would trigger "Required Fields Missing" errors when App Review is subsequently attempted.

**Why it matters:** The daily script (bug 1331370) correctly identifies re-submitted PAR cases that have no Case Manager stamp and fills that gap. However, it does not validate whether the underlying Practice Location (`HealthcareFacility`) is still active. When a Practice Location was terminated between the original PAR submission and the re-submission, the script re-activates a stale HCPF that should never be used — creating a cascading failure in App Review.

---

#### Acceptance Criteria

**Scenario 1 — Happy Path: Script stamps only active Practice Locations**

**Given** the daily script runs and finds a re-submitted PAR case (e.g., IA-0000096229) with no Case Manager stamp,  
**AND** the existing HCPF record for the practitioner-group pair has `HealthcareFacility.PRM_Active__c = true`,  
**When** the script executes,  
**Then** the script stamps `PRM_CaseManager__c = <new case Id>` and sets `PRM_Pending__c = true` on the HCPF,  
**AND** the record is correctly re-activated for App Review (existing expected behavior preserved).

---

**Scenario 2 — Guard: Script skips HCPF when Practice Location is terminated**

**Given** the daily script finds a re-submitted PAR case with no Case Manager stamp,  
**AND** the existing HCPF has `HealthcareFacility.PRM_Active__c = false` (terminated Practice Location),  
**When** the script executes,  
**Then** the script does NOT stamp the new Case Manager onto the HCPF,  
**AND** the HCPF remains in its current state (`PRM_Pending__c = false`, `PRM_CaseManager__c = <prior denied case>`),  
**AND** an exception record / task is created for the credentialing team to manually select a valid active Practice Location for the re-submitted case,  
**AND** the script logs the skipped record with: case Id, HCPF Id, terminated Practice Location name/Id.

---

**Scenario 3 — Multiple locations: partial stamp allowed**

**Given** a re-submitted PAR has two practice locations — one with an active `HealthcareFacility` and one with a terminated `HealthcareFacility`,  
**When** the script executes,  
**Then** the HCPF for the **active** Practice Location is stamped with the new Case Manager and `PRM_Pending__c = true`,  
**AND** the HCPF for the **terminated** Practice Location is skipped (per Scenario 2),  
**AND** both outcomes are logged separately.

---

**Scenario 4 — Retroactive audit: identify previously incorrectly stamped records**

**Given** historical runs of the daily script may have already stamped HCPF records with terminated practice locations,  
**When** a one-time audit query is run against production data,  
**Then** all `HealthcarePractitionerFacility` records where `PRM_Pending__c = true` AND `HealthcareFacility.PRM_Active__c = false` AND `PRM_CaseManager__c` is non-null are identified and surfaced for manual review,  
**AND** a report/list is produced for the credentialing team to correct each affected case.

---

#### Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What is the exact query/logic the daily script uses to identify re-submitted PAR records with no Case Manager? (Need to see the script code to add the active location check in the right place) | Determines where to add the `HealthcareFacility.PRM_Active__c = true` filter | Technical |
| 2 | When the script skips an HCPF due to terminated Practice Location, should it create a Salesforce Task, a Custom Exception Record, or send an email notification? What is the preferred exception-routing mechanism? | Determines the alerting/exception output format | BA |
| 3 | Should the script check `HealthcareFacility.PRM_Active__c` at the time the script runs, or also check whether the location was active at the time of the original PAR submission? | Edge case: location might have been terminated + reactivated | BA / Technical |
| 4 | Is there a recurrence schedule for the daily script? If it runs every night, there may be multiple nights of already-stamped records that need correction | Data audit scope | BA |
| 5 | Is the daily script implemented as an Apex Scheduled Job, a Flow, or an external batch? (Determines which team owns the fix) | Ownership and fix mechanism | Technical |

---

#### Impact Analysis

| Component | Type | Impact | Description |
|-----------|------|--------|-------------|
| Daily script (bug 1331370) | Scheduled job / Apex / Flow | HIGH | Add `HealthcareFacility.PRM_Active__c = true` guard before HCPF stamp |
| Exception logging / task creation | New component | MEDIUM | Log skipped records; create tasks for credentialing team |
| One-time data audit | Query / Report | HIGH | Identify all existing incorrectly-stamped HCPF records in production |
| Manual data remediation for IA-0000096229 | Admin action | CRITICAL (immediate) | Disconnect HCPF from terminated location; enable App Review to proceed |

---

### CROSS-REFERENCE: How This Issue Maps to Existing User Stories

| Story | Contribution to This Bug | Status |
|-------|--------------------------|--------|
| **US1** — IP routing fix for denied/terminated HCPF reuse | Would have prevented the "no new affiliation" gap on 01/31/2026, so the daily script would not have been needed to fill the gap | Proposed — pending implementation |
| **US3** — Clear ExternalId on denial | Would prevent stale ExternalId collisions on the denied HCPF (IA-0000063527), reducing risk of incorrect record matching by the daily script | Proposed — pending implementation |
| **US4** — App Review guard for externally-terminated locations | Directly addresses the "Required Fields Missing" error in App Review for IA-0000096229. Deploy this to unblock App Review NOW. | Proposed — **deploy ASAP as P0 fix** |
| **US5 (NEW)** — Daily script active location validation | Addresses the ROOT CAUSE of why US4 was re-triggered on the new case; prevents future occurrences via the daily script path | **New story** |

---

### Recommended Implementation Order (Updated)

```
IMMEDIATE (production unblock):
  1. Manual admin data correction for IA-0000096229
     → Disconnect HCPF from terminated location
     → Allow credentialing specialist to select new active location

SHORT-TERM (prevent recurrence):
  2. US4 — Deploy PRMDREGetPracticeLocation guard
     → Adds case-ownership check to EligibleForUpdate formula
     → Prevents App Review false positives for all cases where
        terminated locations are linked to in-flight HCPFs
  
  3. US5 (NEW) — Fix daily script (bug 1331370)
     → Add HealthcareFacility.PRM_Active__c = true guard before stamping
     → Add exception logging for skipped records
     → Run one-time audit to identify other affected records in production

MEDIUM-TERM (root cause fixes):
  4. US3 — Clear ExternalId on denial
     → Prevents stale ExternalId collisions from accumulating
  
  5. US1 — Fix re-submission IP routing
     → Creates new HCPF on re-submission (eliminates the gap the daily script was trying to fill)
     → When US1 is complete, the daily script becomes a safety net rather than a primary fix path
```

---

*End of Document*
*Analysis Date: April 26, 2026*
