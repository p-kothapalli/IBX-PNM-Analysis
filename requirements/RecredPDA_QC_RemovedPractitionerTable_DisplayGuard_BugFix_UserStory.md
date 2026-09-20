# USER STORY 3: ReCred Network Management QC — Hide the Removed-Practitioner Table When the Review Is Returned With Errors

**Persona:** Network Management QC Specialist
**Priority:** P2
**OmniScript:** `PRM_ReCredQCUpdate_English` (v3, active) — Removed Practitioner at Practice Location Taxonomy and Network block
**Integration Procedures:** `PRM_RecredPDAUpdateRecords_Procedure` (v1, active)
**Relevant Requirements:** Bug **1216120**; `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §3 G3

---

## Story

**As a** Network Management QC Specialist,
**I want** the "Removed Practitioner at Practice Location Taxonomy and Network" table to appear only when I am completing a QC review,
**So that** when I return a case to the PDA team with errors I am not shown — and do not have to scroll past — a confirmation table of removals that are not being accepted.

**Why it matters:** The table currently renders on both QC outcomes. When a QC Specialist selects "Errors Found" and returns the case, the screen still presents the removals as if they were being confirmed. That is misleading at the moment of rejection, adds review time on an already long screen, and has been raised by QA as a defect.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Re-credentialing Network Management QC (`Network Management QC` stage) | `PRM_ReCredQCUpdate_English` | QC review step — Removed Practitioner at Practice Location Taxonomy and Network block | Removal rows fetched for the case |

**Out of scope:** the content or correctness of the removal rows themselves (US-1); the QC outcome routing, which works correctly today.

---

## Current State (from codebase)

### The table's display condition ignores the QC outcome

The removal table is shown whenever a removed-location name is present on the case. There is **no** condition on the QC outcome, so it renders identically for "QC Completed" and "Errors Found".

- **Location:** `force-app/main/default/omniScripts/PRM_ReCredQCUpdate_English_3.os-meta.xml`, element `RemovePPLTxNtwk` (Edit Block, active)
- **Current display condition:** shown when the removed practice-location name on the removal set is not empty

### The outcome value is already available on the same step

The QC outcome selection lives on the same step and is already used as a display condition by the two persist elements — one shown for "Errors Found", one for "QC Completed". The pattern to follow already exists in this OmniScript.

- **Location:** same file, elements `NtwkMgmtQCReviewOutcome` (Select, required), `SetRecordsErrorsFound`, `SetRecordQCCompleted`

### The element was iterated but the guard was not added

The block's keyed field changed since the defect was first raised (it now keys on the removed location's name rather than the practitioner), confirming the element has been edited — but the outcome guard was never added.

---

## Acceptance Criteria

**AC-1 — Table is shown when completing QC**

**Given** a Network Management QC Specialist is reviewing a re-credentialing case that includes a removed practice location,
**When** they select the QC outcome "QC Completed",
**Then** the Removed Practitioner at Practice Location Taxonomy and Network table is displayed,
**And** it lists the removals exactly as it does today.

**AC-2 — Table is hidden when returning the case with errors**

**Given** a Network Management QC Specialist is reviewing a re-credentialing case that includes a removed practice location,
**When** they select the QC outcome "Errors Found",
**Then** the Removed Practitioner at Practice Location Taxonomy and Network table is hidden,
**And** the error-reason and notes fields required to return the case remain visible and usable.

**AC-3 — Switching the outcome updates the display immediately**

**Given** a Network Management QC Specialist has selected "QC Completed" and can see the removal table,
**When** they change the outcome to "Errors Found",
**Then** the removal table disappears without leaving the step or refreshing the page,
**And** changing the outcome back to "QC Completed" makes it reappear.

**AC-4 — Cases with no removals are unaffected**

**Given** a Network Management QC Specialist is reviewing a re-credentialing case with **no** removed practice locations,
**When** they select either QC outcome,
**Then** the removal table is not displayed in either case,
**And** the behaviour is unchanged from today.

**AC-5 — Rebuttal review is unaffected**

**Given** a case is in a rebuttal state where the QC outcome selection is not presented,
**When** a Network Management QC Specialist opens the review,
**Then** the removal table's visibility behaves exactly as it does today for that path,
**And** the rebuttal outcome and its routing are unchanged.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_ReCredQCUpdate_English` element `RemovePPLTxNtwk` | Modified OmniScript element (new version) | Add a second rule to the existing `show` group: QC outcome equals `QC Completed` (or `<> 'Errors Found'`), combined with the existing removed-location-name rule under `AND` | Drives AC-1, AC-2, AC-3 |
| `PRM_ReCredQCUpdate_English` | New activated version | Version bump from v3; follow the same condition pattern already used by `SetRecordsErrorsFound` / `SetRecordQCCompleted` | Drives all ACs |
| Rebuttal path | Review | The outcome field is itself hidden when the case status is a rebuttal — confirm the new `AND` rule does not permanently hide the table on that path (may need an `OR` branch for the rebuttal outcome field) | Drives AC-5 |

No DataRaptor, Integration Procedure, or Apex change is required — this is a display-condition change only.

---

## Definition of done

- [ ] AC-1 verified in QA: table visible on "QC Completed"
- [ ] AC-2 verified in QA: table hidden on "Errors Found", error-reason and notes fields still usable
- [ ] AC-3 verified: toggling the outcome shows/hides the table without a page refresh
- [ ] AC-4 verified: a case with no removals behaves as today on both outcomes
- [ ] AC-5 verified: the rebuttal path is unchanged and the table is not permanently hidden there
- [ ] Both QC outcomes still route the case correctly (completed → closed; errors → returned to the PDA team)
- [ ] New OmniScript version **activated** and verified by a Network Management QC Specialist in QA

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | On "Errors Found", should the table be hidden entirely or shown collapsed/read-only for reference? | Hiding is the reported request; collapsing preserves context for writing the error reason | Product |
| 2 | On the rebuttal path (where the QC outcome field is hidden), should the table show or hide? | Determines whether the new condition needs an `OR` branch on the rebuttal outcome field | BA |
| 3 | Do the sibling added-location tables on this step have the same missing guard? | May widen the story to cover the add-side blocks for consistency | Technical |
| 4 | Should the same guard apply on the PDA Update side, or is it correct there? | The PDA Update flow authors the removals, so the table is presumably always relevant there | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_ReCredQCUpdate_English` | OmniScript | MEDIUM | Display condition change; new activated version |
| QC outcome routing | OmniScript | LOW | Must be confirmed unchanged, not modified |
| Rebuttal review path | OmniScript | LOW | Shares the step; needs regression |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `RemovePPLTxNtwk` display condition | OmniScript element | **S** | One rule added to an existing show group |
| Rebuttal-path condition handling | OmniScript element | **S** | Possible `OR` branch |
| Regression across both outcomes + rebuttal | QA | **M** | Three paths to verify |

**Total Estimated Effort:** **S/M** (a few hours including regression) — AI-estimated, validate with team.
