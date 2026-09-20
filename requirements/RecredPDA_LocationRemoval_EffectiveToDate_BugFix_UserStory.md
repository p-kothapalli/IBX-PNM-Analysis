# USER STORY 2: ReCred PDA — Termination Date on Location Removal Must Reflect the Real Termination, Not the Approval Date

**Persona:** Provider Data Admin (PDA) Specialist
**Priority:** P0
**OmniScript:** `PRM_ReCredUpdate_English` (v7, active) — Removed Practitioner at Practice Location Taxonomy and Network block
**Integration Procedures:** `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v11, active); `PRM_RecredPDAHelper_Procedure` (v9, active)
**Relevant Requirements:** Bug **1216121** (second of two root causes); `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §3 G2; sibling story `RecredPDA_LocationRemoval_PractitionerScope_BugFix_UserStory.md` (US-1)

---

## Story

**As a** Provider Data Admin (PDA) Specialist,
**I want** to set the correct termination date when I remove a practice location from a re-credentialing case,
**So that** affiliation and network end-dates match when the practitioner actually stopped practising there, rather than the date the committee approved the re-cred.

**Why it matters:** The Effective To date on a removal is currently forced to the case's approval date and is **read-only**, so a specialist who knows the practitioner left the location months earlier cannot record it. Wrong end-dates mean claims are paid or denied against the wrong period and the provider directory shows the wrong coverage window. Correcting it afterwards requires a manual data fix.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Re-credentialing PDA Update (`Recred Updates` stage) | `PRM_ReCredUpdate_English` | Removed Practitioner at Practice Location Taxonomy and Network | Removal date fields; re-cred termination transforms |

**In scope:** the Effective To value on the removal path, its editability, and its validation.
**Out of scope:** the row-scope defect (US-1); the add-location path, which already has date validation.

---

## Current State (from codebase)

### The removal date is force-stamped and read-only in the PDA Update flow

| Guided flow (active version) | Removal Effective To default | Editable? |
|---|---|---|
| `PRM_ReCredUpdate_English` **v7** (PDA Update — where removals are authored) | **the case's approval date** | **No — read-only** |
| `PRM_ReCredQCUpdate_English` **v3** (Network Management QC) | empty | No — read-only |

The QC side was already corrected to stop defaulting the date; the PDA Update side — the step where the specialist actually authors the removal — still force-stamps it.

- **Location:** `force-app/main/default/omniScripts/PRM_ReCredUpdate_English_7.os-meta.xml`, element `RemovePPLEffTo`

### Date validation exists but only covers the ADD path

A validation formula was added in v7 that compares the **newly added** location's Effective To against its Effective From. It does not reference the removal date field at all, so the removal path has **no** date validation.

- **Location:** same file, element `EffectiveToDateValidFrmla`

### The termination write consumes a single computed date

Both termination transforms write `Effective To` from a computed "final" date value and set `Pending = false`.

- **Location:** `force-app/main/default/omniDataTransforms/PRMTransPPLForTerminationReCred_1.rpt-meta.xml`, `PRMTransTxnyForTerminationReCred_1.rpt-meta.xml`

---

## Acceptance Criteria

**AC-1 — Specialist can set the termination date on a removal**

**Given** a Provider Data Admin (PDA) Specialist is removing a practice location from a re-credentialing case,
**When** they reach the removal review step,
**Then** the Effective To date is editable,
**And** it is pre-filled with the case's approval date as a starting suggestion rather than a fixed value,
**And** the specialist can change it to the date the practitioner actually left the location.

**AC-2 — Termination date cannot precede the affiliation start**

**Given** a Provider Data Admin (PDA) Specialist has entered a termination date **earlier** than the date the practitioner started at that location,
**When** they try to continue from the removal step,
**Then** the submission is blocked with a message explaining the termination date cannot be before the start date,
**And** no records are end-dated,
**And** the specialist stays on the removal step with their other entries preserved.

**AC-3 — Records updated with the specialist's termination date**

**Given** a Provider Data Admin (PDA) Specialist has entered a valid termination date on a location removal,
**When** they submit the re-cred update,
**Then** the following records are updated exactly as specified:

**Practitioner-to-Practice-Location affiliation — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | unchanged |
| Effective To | {termination date entered by the specialist} | replaces the forced approval date |
| Active | per the Active rules in AC-4 | |
| Pending | FALSE | |
| Is Error Record | {existing value} | unchanged |

**Practice-Location-to-Practitioner affiliation — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | unchanged |
| Effective To | {termination date entered by the specialist} | |
| Active | per the Active rules in AC-4 | |
| Pending | FALSE | |
| Is Error Record | {existing value} | unchanged |

**Practitioner at Practice Location Taxonomy and Network — Update**

| Field | Value | Notes |
|---|---|---|
| Effective From | {existing Effective From} | unchanged |
| Effective To | {termination date entered by the specialist} | |
| Active | per the Active rules in AC-4 | |
| Pending | FALSE | |
| Is Error Record | {existing value} | unchanged |
| Case Manager | {this case's Case Manager} | unchanged behaviour |

**AC-4 — Active flag rules on the terminated rows**

**Given** a location removal has been submitted with a termination date,
**When** the records are written,
**Then** the Active flag is set per the rules below:

- **Active =**
  - If Effective From ≤ TODAY **and** Effective To > TODAY → Active
  - If Effective To ≤ TODAY → Inactive
  - If Effective To is empty → If Effective From ≤ TODAY → Active; else → Inactive

**AC-5 — Back-dated termination is accepted and applied immediately**

**Given** a Provider Data Admin (PDA) Specialist enters a termination date in the **past** (the practitioner left three months ago),
**When** they submit,
**Then** the affiliation, taxonomy and network rows are end-dated with that past date,
**And** those rows show as inactive,
**And** the practitioner no longer appears at that location in the provider directory.

**AC-6 — Future-dated termination is accepted and stays active until the date passes**

**Given** a Provider Data Admin (PDA) Specialist enters a termination date in the **future**,
**When** they submit,
**Then** the rows are end-dated with that future date,
**And** the rows remain active until that date passes,
**And** the practitioner continues to appear at that location in the directory until then.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_ReCredUpdate_English` element `RemovePPLEffTo` | Modified OmniScript element (new version) | Change `readOnly` to false; keep `%CaseManager:ApprovedDate%` as an initial default value rather than a locked value | Drives AC-1 |
| `PRM_ReCredUpdate_English` — new removal-path validation | New OmniScript formula + Set Errors | Add a removal-path equivalent of the existing `EffectiveToDateValidFrmla` (which only covers `EffectiveToNew` / `EffectiveFromNew`), comparing the removal Effective To against the row's Effective From | Drives AC-2 |
| `PRMTransPPLForTerminationReCred` | Review / possible modified DataRaptor | Confirm the "EffectiveToFinal" computed input carries the specialist-entered date rather than a re-derived approval date | Drives AC-3 |
| `PRMTransTxnyForTerminationReCred` | Review / possible modified DataRaptor | Same for the taxonomy/network write; confirm the Active derivation matches AC-4 | Drives AC-3, AC-4 |
| `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` | New IP version (if date derivation lives here) | Ensure the date passed to the termination transforms is the entered value | Drives AC-3 |
| `PRM_FullPracTermRecredBatchService` | Review | Confirm the batch cascade uses the same date for the location termination when the practitioner is the last active one | Drives AC-5, AC-6 |

**Relationship to future-dated termination work:** AC-6 must be reconciled with the existing future-dated push-out behaviour described in `requirements/FutureDated_Termination_PushOut_AddressUpdate_UserStory.md` — see Clarification 3.

---

## Definition of done

- [ ] AC-1 verified: the removal Effective To is editable in QA and defaults to the approval date
- [ ] AC-2 verified: a termination date before the affiliation start is blocked with a clear message and writes nothing
- [ ] AC-3 verified by field inspection on all three record sets after a removal
- [ ] AC-4 verified for all three Active branches (past, future, empty Effective To)
- [ ] AC-5 verified with a back-dated termination; practitioner drops out of the directory view
- [ ] AC-6 verified with a future-dated termination; rows stay active until the date passes
- [ ] No regression to the add-location date validation already present in the same flow
- [ ] ≥ 85% Apex coverage on any modified termination class
- [ ] New OmniScript / IP / DataRaptor versions **activated** and verified by a Provider Data Admin (PDA) Specialist in QA

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Should the removal Effective To be per-row (each affiliation gets its own date) or one date for the whole removal? | Per-row is more accurate but a larger UI change; one date is simpler | BA / Product |
| 2 | Is there a maximum allowed back-date (e.g. not earlier than the current credentialing period)? | Determines whether AC-2 needs an additional lower bound beyond the affiliation start date | BA / Compliance |
| 3 | How should a future-dated removal interact with the existing future-dated termination push-out processing? | Risk of the push-out job re-processing or overwriting the date | Technical |
| 4 | Should the QC step (where the date is currently blank and read-only) display the specialist's entered date for review? | QC reviewers currently cannot see the date they are approving | Product |
| 5 | Do existing records already carry an incorrect approval-date end-date that needs remediation? | Adds a backfill task outside this story | BA / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_ReCredUpdate_English` | OmniScript | **HIGH** | Element editability + new validation; new activated version |
| `PRMTransPPLForTerminationReCred` | DataRaptor | **HIGH** | Writes the Effective To on both affiliation sets |
| `PRMTransTxnyForTerminationReCred` | DataRaptor | **HIGH** | Writes the Effective To and Active on network rows |
| `PRM_ReCredQCUpdate_English` | OmniScript | MEDIUM | QC reviews the same removal rows (Clarification 4) |
| Future-dated termination processing | Apex batch | MEDIUM | AC-6 overlaps existing push-out behaviour |
| Claims / directory accuracy | Data | **HIGH** | End-date correctness drives claim adjudication windows |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `RemovePPLEffTo` editability | OmniScript element | **S** | Flip read-only, keep default |
| Removal-path date validation | OmniScript formula + Set Errors | **M** | Mirror the existing add-path formula |
| Termination transform date wiring | DataRaptor review / change | **M** | Confirm the entered date flows through |
| Active-flag rule verification | DataRaptor / Apex | **M** | Three branches to prove |
| Regression (add path + future-dated) | QA | **L** | Overlaps push-out processing |

**Total Estimated Effort:** **M/L** (roughly half a day of build + 1 day of regression) — AI-estimated, validate with team.
