# Recredentialing Guided Flow → ReCred PDA Routing Audit

**Date:** 2026-06-08
**Scope:** The Recredentialing guided flow **only**. This document traces, element-by-element from the OmniScript metadata, exactly **where, how, and under what conditions a recred case is routed into "ReCred PDA"** (the *Recred Updates* lane), and what happens inside that lane through QC and closure.

> This supersedes the high-level treatment in `Recred_PDA_PSV_Route_PAR_Form_Audit_2026-06-08.md` for the routing question. All findings below are taken directly from the `vlocity_export/OmniScript/*` element JSON (the deployed OmniScript definitions), not from design docs.

---

## 0. The OmniScripts that make up the recred guided flow

| OmniScript | Process Name | Role in the flow |
|---|---|---|
| `PRM_RecredQC_English` | `RecredQC` | The **recred guided review** (App Review + PSV + QC + MDR collapsed into one script). Produces the routing decision. |
| `PRM_NonRoutineCommitteeReview_English` | `NonRoutineCommitteeReview` | **Committee** review. **This is the script that flips a recred case into "Recred Updates" (ReCred PDA).** |
| `PRM_ReCredUpdate_English` | `ReCredUpdate` | The **ReCred PDA Update** guided flow — the work performed on the *Recred Updates* case. |
| `PRM_ReCredQCUpdate_English` | `ReCredQCUpdate` | The **Network Management QC** of the PDA update (where both open QA defects live). |
| `PRM_PractitionerTerminationRecredForm_English` | termination form | Termination sub-form used on the Final Development / term path. |

The case lifecycle field that drives lane membership is **`IndividualApplication.PRM_Stage__c`** (Case Manager stage). The string **`"Recred Updates"`** is the ReCred PDA stage.

---

## 1. Bottom line — when do we route to ReCred PDA?

**A recred case enters ReCred PDA at exactly one decision point: the committee "Nonroutine Committee Approved" outcome.**

There is **no path from the recred PSV/QC review directly into ReCred PDA.** The recred guided review (`RecredQC`) can only send a case to **Committee**, to **MDR (→ Committee)**, to **Final Development (termination)**, or **back to PSV**. The transition to the *Recred Updates* stage is performed by the **committee** script when it approves a re-credentialing record type.

```
RecredQC review ──(ReCredProceedTo)──► Committee ──(Nonroutine Committee Approved)──► STAGE = "Recred Updates"  ← ReCred PDA entry
                                            │                                          + new "Recred Updates" Case (PRM_PDAInitialCredQueue)
                                            ├─(MD Approved)─► back to Committee
                                            └─(Denied/Closed)─► denial

RecredQC review ──(Route to Final Development)──► RecredTerm=true, Pending Closure ──► RCAT batch ──► "Recred Updates" (termination) case
```

So there are **two ways the "Recred Updates" stage is reached**:
1. **Approval path (primary):** committee approves → Stage `Recred Updates` (cred maintained). *Detailed below.*
2. **Termination path:** review chooses *Route to Final Development* → `PRM_RecredTerm__c = true` → picked up by the RCAT termination batch, which lands the work as a *Recred Updates* (termination) case.

---

## 2. Step 1 — the recred guided review (`PRM_RecredQC_English`)

### 2.1 The decision control: `ReCredProceedTo`

The reviewer's routing decision is captured by the **radio `ReCredProceedTo`** on step `ReCredPSVSummary`.

`PRM_RecredQC_English_Element_ReCredProceedTo.json` options:

| Value | Meaning |
|---|---|
| `Committee Review` | send to committee |
| `Medical Director Review` | send to MDR (which lands at committee) |
| `Route to Final Development` | terminate / RCAT path |
| `Route to PSV` | bounce back to PSV |

(`ReCredDefaultProceedTo` — the formula that would pre-select MDR/Provider-Outreach from verification outcomes — is **`IsActive: false`**, so no default is auto-applied today.)

### 2.2 What each outcome persists (the active Set Values elements)

Only **three** persist elements are live in the recred review. All three share an identical `RecordsToUpdate` map and simply gate themselves on `ReCredProceedTo`:

| Element | `IsActive` | Fires when `ReCredProceedTo` = | Sets `PRM_Stage__c` | Sets Status | Flags |
|---|---|---|---|---|---|
| `SetRecordRecredQC_CR` | **true** | `Committee Review` | `Committee Review` | `In Progress` | `PRM_RoutineCommittee__c = true` |
| `SetRecordRecredQC_MDR` | **true** | `Medical Director Review` | `Committee Review` | `In Progress` | `MedicalDirectorReview = true`, new Case Type `Committee Review`, saves `MDRForm` |
| `SetRecordRecredQC_FD` | **true** | `Route to Final Development` | `QC Review` | `Pending Closure` | `PRM_RecredTerm__c = true` |

Key reads:
- `PRM_RecredQC_English_Element_SetRecordRecredQC_CR.json` →
  `"PRM_Stage__c": "=IF(%ReCredProceedTo% == 'Committee Review', 'Committee Review', IF(%ReCredProceedTo% == 'Medical Director Review','Committee Review','QC Review'))"`
- Same file → `"PRM_RoutineCommittee__c": "=IF(%ReCredProceedTo% == 'Committee Review', true, NULL)"`
- `..._SetRecordRecredQC_FD.json` → `"PRM_RecredTerm__c": "=IF(%ReCredProceedTo% == 'Route to Final Development', true, NULL)"`, Status `Pending Closure`.

**None of these set `PRM_Stage__c = "Recred Updates"`.** The recred review hands off to Committee (or to the RCAT term batch). This is the proof that PDA entry is *not* in the review script.

### 2.3 Elements that are deactivated (legacy / initial-cred pattern, OFF for recred)

These exist in the script but are **`IsActive: false`** and do not run in the live recred flow — important so they aren't mistaken for the routing logic:

| Element | `IsActive` | Note |
|---|---|---|
| `SetRecordReCredPSV` | false | older two-step PSV→QC save (Stage `QC Review`) |
| `SetRecordPSVQC` | false | initial-cred-style PSV→QC save |
| `SetRecordQCReturnTo` | false | QC "Return To" / "Ready for Committee" save (uses `QCProceedTo`) |
| `SetReCredProviderOutreachFinal` | false | Provider-Outreach / Final-Dev full save incl. `PracticeLocationBlock` |
| `ReCredDefaultProceedTo` | false | default-outcome formula |

> The `QCProceedTo` radio (`Ready for Committee` / `Ready for Medical Director Review` / `Return To`) and `QCReturnTo` are part of the deactivated QC-return branch; the live recred review routes through `ReCredProceedTo` instead.

---

## 3. Step 2 — Committee (`PRM_NonRoutineCommitteeReview_English`) — **the ReCred PDA entry point**

The committee outcome is captured in `CaseStatusRecred` / `CaseStatus`. The relevant Set Values elements:

| Element | `IsActive` | Fires when | Effect |
|---|---|---|---|
| `SVNRCommitteeApproved` | true | `Nonroutine Committee Approved` **AND** `PRM_RecredUpdate__c = false` | **→ Recred Updates** |
| `SVForNCApprovedCredTrue` | true | `Nonroutine Committee Approved` **AND** `PRM_RecredUpdate__c = true` | **→ Recred Updates** |
| `SetForMDApproved` | true | `MD Approved` | Stage `Committee Review`, `RoutineCommittee = true` (loops back to committee) |
| `SVNRCommitteeDeniedClosed` | true | denied/closed | denial |

### 3.1 The exact PDA-entry assignment

Both approval elements (`SVNRCommitteeApproved`, `SVForNCApprovedCredTrue`) set the **same** stage formula and spawn the **same** downstream case:

```
IndividualApplication.PRM_Stage__c =
  IF(%CaseRelatedDetails:CaseManager:RCDeveloperName% == "PRM_ReCredentialing",
     "Recred Updates",
     "PDA Review and Update")
IndividualApplication.Status        = "Approved"
IndividualApplication.ApprovedDate  = set (NCApprovedDate / true)
Practitioner.CredentialingStatus    = "Credentialed"
Practitioner.ReCredentialingDueDate = %CaseManager:RecredDueDate%

NewCase.Type      = IF(... == "PRM_ReCredentialing", "Recred Updates", "PDA Review and Update")
NewCase.OwnerName = "PRM_PDAInitialCredQueue"
NewCase.Status    = "New"
NewCase.IsRoundRobinLogic = true
```

**This is the precise moment a recred case becomes a ReCred PDA case:** the Case Manager's stage flips to `Recred Updates` and a brand-new Case of Type `Recred Updates` is created and round-robin assigned to **`PRM_PDAInitialCredQueue`**. The record-type gate `RCDeveloperName == "PRM_ReCredentialing"` is what distinguishes recred (→ `Recred Updates`) from initial PDA (→ `PDA Review and Update`).

The only difference between the two approval elements is `ApprovedDate` handling and the `PRM_RecredUpdate__c` flag (whether the recred case already had updates in flight); both produce the `Recred Updates` case.

---

## 3a. The "route to PDA vs Complete" decision — **there is no real fork in the current build**

A common assumption is that the flow decides *"clean recred with no changes → Complete; recred with location/affiliation changes → ReCred PDA."* **That branch is not implemented.** In the as-built OmniScripts, every committee-approved recred is funneled through ReCred PDA, and `Complete` is only reachable at the *end* of that lane — never as an alternative to it.

### Why there is no fork

1. **The recred review never auto-completes.** `ReCredProceedTo` (active control) only offers `Committee Review`, `Medical Director Review`, `Route to Final Development` (term), `Route to PSV`. No "approve/complete" outcome exists — an approved-looking recred always advances to committee.

2. **Committee approval always routes to PDA.** Both approval Set elements set `PRM_Stage__c = "Recred Updates"` and spawn a `Recred Updates` case:

| Element | Fires when | Stage set | Creates PDA case? |
|---|---|---|---|
| `SVNRCommitteeApproved` | `PRM_RecredUpdate__c = false` | `Recred Updates` | **Yes** |
| `SVForNCApprovedCredTrue` | `PRM_RecredUpdate__c = true` | `Recred Updates` | **Yes** |

   The `PRM_RecredUpdate__c` flag only changes how `ApprovedDate` is stamped (`true` literal vs `=%UpdateCaseStatus:NCApprovedDate%`). **It does not gate PDA-vs-Complete** — both flag values land in PDA.

3. **`Complete` is the terminus of the PDA lane, not a committee outcome.** It is set in exactly one place:
   - `PRM_ReCredUpdate_English` → `SetRecordNtwkMgntQC` **always** forwards to `Network Management QC` (`PRM_NetworkManagementQCQueue`); the only branch is the post-QC return loop (`PDAReturnOutcome`: `Errors Resolved` / `Rebuttal`).
   - `PRM_ReCredQCUpdate_English` → `NtwkMgmtQCReviewOutcome`:
     - `QC Completed` → `SetRecordQCCompleted` → **`PRM_Stage__c = "Complete"`**, `Status = Approved`, Case Closed. *(only completion point)*
     - `Errors Found` → `SetRecordsErrorsFound` → loops back to PDA.

### The `PRM_RecredUpdate__c` flag — exists, carried, but never used to skip PDA

- **Read** in `PRM_CommitteeReviewHelper` (`cmOut.put('RecredPDA', cm.get('PRM_RecredUpdate__c'))`) and surfaced to the committee UI as `RecredPDA`.
- **Written** at the recred PSV-review save by the persistence IP **`PRM_ReviewPSVCaseRecordsUpdate`**, element `DRUpdateCaseCaseManager` (DataRaptor Post Action, bundle `PRMUpdateIDCaseCaseMgr`). The mapping `IndividualApplication:RecredUpdate` is a conditional:

  ```
  IndividualApplication:RecredUpdate =
    IF( FlowType == 'ReCred'
        AND ( CheckServiceAreaStepRecords:PracticeLocationAdded|1:HCFTypeAhead-Block:Id != NULL
              OR CheckServiceAreaStepRecords:PracticeLocationRemoved|1:PSVPracticeLocationName != NULL ),
        true, false )
  ```

  i.e. **`true` when the recred PSV reviewer added or removed a practice location** in the Service Area Verification step; otherwise `false`. The `PRMUpdateIDCaseCaseMgr` / `PRMUpdateIDCaseMgrPNC` DataRaptors then upsert that value onto `PRM_RecredUpdate__c` (passthrough at the DataRaptor layer). It is **not** assigned inside the `PRM_RecredQC_English` OmniScript itself.
- **Net effect:** the flag correctly captures *"this recred involved practice-location/affiliation changes,"* travels with the case, and is shown to the committee — but **no element uses it to route to `Complete` instead of `Recred Updates`.** The data needed for a PDA-vs-Complete fork exists; the fork itself does not.

### Decision diagram (as-built)

```
Recred review (RecredQC)
   └─ ReCredProceedTo ─┬─ Committee Review ───────────► Committee
                       ├─ Medical Director Review ────► Committee (via MDR)
                       ├─ Route to Final Development ─► RecredTerm=true ─► RCAT ─► Recred Updates (termination)
                       └─ Route to PSV ──────────────► back to PSV

Committee (NonRoutineCommitteeReview)
   └─ Nonroutine Committee Approved ─► STAGE = "Recred Updates"  (PDA — MANDATORY, regardless of PRM_RecredUpdate__c)
                                       + new "Recred Updates" case (PRM_PDAInitialCredQueue)

ReCred PDA Update (ReCredUpdate) ─► ALWAYS ─► Network Management QC
Network Management QC (ReCredQCUpdate)
   ├─ QC Completed ─► STAGE = "Complete", Approved, Closed     ◄── ONLY completion
   └─ Errors Found ─► back to PDA (rebuttal / error-resolution loop)
```

### Implication
If the business wants "no-change recreds to complete without a PDA/Network-Management-QC pass," that is a **gap, not a config toggle** — there is currently no branch that consumes `PRM_RecredUpdate__c` (or a "has updates" determination) to bypass the PDA lane. Building it would mean adding a committee-approval branch that, when `PRM_RecredUpdate__c = false` (no updates), sets `PRM_Stage__c = "Complete"` / closes the case instead of creating the `Recred Updates` case.

---

## 4. Step 3 — Inside ReCred PDA: the Update flow (`PRM_ReCredUpdate_English`)

The `Recred Updates` case is worked here. The terminal persist is `SetRecordNtwkMgntQC` (**`IsActive: true`**), which fires when `PDAReturnOutcome == null` (i.e., the PDA worker is sending it forward, not returning it):

```
IndividualApplication.PRM_Stage__c = "Network Management QC"
NewCase.Type      = "Network Management QC"
NewCase.OwnerName = "PRM_NetworkManagementQCQueue"
NewPPLTxnyNtwkRecords    = %PPLStep:PractitionerAtPractitionerLocation%   (added affiliations)
RemovePPLTxnyNtwkRecords = %PPLStep:RemovePPLTxNtwk%                       (removed affiliations)
```

So ReCred PDA Update → **Network Management QC** lane. Other branches in this script: `SetRecordsRebuttal`, `SetRecordsErrorsResolved`, `QCReturnToPDA`, `PDAReturnOutcome` (handle the error/rebuttal loop back from QC).

---

## 5. Step 4 — ReCred PDA QC (`PRM_ReCredQCUpdate_English`) and closure

QC reviewer picks `NtwkMgmtQCReviewOutcome` ∈ { **QC Completed**, **Errors Found** }:

| Outcome | Persist element | Effect |
|---|---|---|
| `QC Completed` | `SetRecordQCCompleted` (active) | `PRM_Stage__c = "Complete"`, Status `Approved`, Case `Closed` → **end of recred** |
| `Errors Found` | `SetRecordsErrorsFound` (active) | routes back to PDA for error resolution / rebuttal (`ErrorReasons`, `PDARebuttalNote`, `ReturnToQC`) |

This is the lane where the **two open QA defects sit**:

- **Bug 1216120 (QC display)** — in `PRM_ReCredQCUpdate_English_Element_RemovePPLTxNtwk.json`, the "Removed Practitioner at Practice Location Taxonomy and Network" table's `show` condition lacks a guard for the `Errors Found` outcome, so it renders when it shouldn't.
- **Bug 1216121 (cascading termination scope)** — `RemovePPLEffTo` hard-defaults to `%CaseManager:ApprovedDate%`, and the upstream fetch (`PRMFetchRecredUpdateData`, currently `<active>false</active>` in the repo) pulls **all** practitioners at the `HealthcareFacilityId`, so removing one location can terminate every practitioner at that facility. The live warning `PLTermWarningMsg` ("location will also be terminated" when `ActivePractitioners = 1`) confirms the cascading behavior is by-design but the scope is wrong.

---

## 6. End-to-end routing map (recred only)

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRM_RecredQC_English  (recred guided review: App+PSV+QC+MDR)          │
│   decision = ReCredProceedTo                                          │
│     • Committee Review        → SetRecordRecredQC_CR  → Stage=Committee Review, RoutineCommittee=true
│     • Medical Director Review → SetRecordRecredQC_MDR → Stage=Committee Review, MedicalDirectorReview=true
│     • Route to Final Development → SetRecordRecredQC_FD → RecredTerm=true, Pending Closure ──► RCAT term batch ──► Recred Updates (term)
│     • Route to PSV            → back to PSV                            │
└───────────────┬───────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PRM_NonRoutineCommitteeReview_English  (committee)                    │
│   outcome = CaseStatusRecred / CaseStatus                             │
│     • MD Approved             → SetForMDApproved → Stage=Committee Review (loop)
│     • Denied/Closed           → SVNRCommitteeDeniedClosed → denial     │
│     • Nonroutine Committee Approved → SVNRCommitteeApproved / SVForNCApprovedCredTrue
│            └── RCDeveloperName == "PRM_ReCredentialing"                │
│                   ⇒ PRM_Stage__c = "Recred Updates"   ◄── ReCred PDA ENTRY
│                   ⇒ new Case Type "Recred Updates", Owner PRM_PDAInitialCredQueue
└───────────────┬───────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PRM_ReCredUpdate_English  (ReCred PDA Update)                         │
│   SetRecordNtwkMgntQC → Stage="Network Management QC",                 │
│     new Case Type "Network Management QC", Owner PRM_NetworkManagementQCQueue
│     carries Added (PractitionerAtPractitionerLocation) + Removed (RemovePPLTxNtwk)
└───────────────┬───────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PRM_ReCredQCUpdate_English  (Network Management QC)                   │
│   NtwkMgmtQCReviewOutcome                                             │
│     • QC Completed → SetRecordQCCompleted → Stage="Complete", Approved, Closed  ✅ DONE
│     • Errors Found → SetRecordsErrorsFound → back to PDA (rebuttal loop)
│   ⚠ Bug 1216120 (RemovePPLTxNtwk display) and Bug 1216121 (term scope) live here
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Precise answer to the routing question

- **Single entry condition into ReCred PDA:** `PRM_NonRoutineCommitteeReview_English`, elements `SVNRCommitteeApproved` / `SVForNCApprovedCredTrue`, when the committee outcome is **`Nonroutine Committee Approved`** and the Case Manager record type is **`PRM_ReCredentialing`** → `PRM_Stage__c = "Recred Updates"` + a new `Recred Updates` case owned by `PRM_PDAInitialCredQueue`.
- **The recred review script never routes to PDA directly** — it only routes to Committee, MDR (→Committee), Final Development (→RCAT term), or back to PSV.
- **Secondary entry into the same stage:** the *Route to Final Development* outcome (`PRM_RecredTerm__c = true`) reaches `Recred Updates` indirectly via the RCAT termination batch (termination, not maintenance).
- **PDA lane internals:** `Recred Updates` (PDA Update) → `Network Management QC` → `Complete`/`Approved`. The error path loops PDA↔QC via `Errors Found`/rebuttal.

## 8. Source elements cited (all under `vlocity_export/OmniScript/`)

- `PRM_RecredQC_English/..._Element_ReCredProceedTo.json`
- `PRM_RecredQC_English/..._Element_SetRecordRecredQC_CR.json` (active)
- `PRM_RecredQC_English/..._Element_SetRecordRecredQC_MDR.json` (active)
- `PRM_RecredQC_English/..._Element_SetRecordRecredQC_FD.json` (active)
- `PRM_RecredQC_English/..._Element_SetRecordReCredPSV.json` (inactive)
- `PRM_RecredQC_English/..._Element_SetRecordPSVQC.json` (inactive)
- `PRM_RecredQC_English/..._Element_SetRecordQCReturnTo.json` (inactive)
- `PRM_RecredQC_English/..._Element_SetReCredProviderOutreachFinal.json` (inactive)
- `PRM_NonRoutineCommitteeReview_English/..._Element_SVNRCommitteeApproved.json` (active)
- `PRM_NonRoutineCommitteeReview_English/..._Element_SVForNCApprovedCredTrue.json` (active)
- `PRM_NonRoutineCommitteeReview_English/..._Element_SetForMDApproved.json` (active)
- `PRM_ReCredUpdate_English/..._Element_SetRecordNtwkMgntQC.json` (active)
- `PRM_ReCredQCUpdate_English/..._Element_NtwkMgmtQCReviewOutcome.json` (active)
- `PRM_ReCredQCUpdate_English/..._Element_SetRecordQCCompleted.json` (active)
- `PRM_ReCredQCUpdate_English/..._Element_RemovePPLTxNtwk.json` (Bug 1216120)
- `PRM_ReCredQCUpdate_English/..._Element_RemovePPLEffTo.json` (Bug 1216121)
