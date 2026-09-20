# USER STORY: Rush-Review Reason on the Provider Change Form (visible downstream on the Case Manager)

**Persona:** PDM Specialist
**Priority:** P1
**OmniScript:** `PRM_ProviderChangeForm_English` (active v83) — capture; `PRM_ProviderChangeQC_English` (active v13) — downstream read-only display
**Integration Procedures:** Provider Change submission/save IP chain that writes the form to the Case Manager (to be confirmed — see Clarification Q1)
**Relevant Requirements:** `requirements/Provider_Change_Form_PNC_Deep_Dive_Analysis.md`, `requirements/GA_State_County_Picklist_Expansion_User_Story.md` (Provider Change is one of the 7 affected forms)

---

## Story

**As a** PDM Specialist,
**I want** to flag a Provider Change submission for expedited review and capture the reason it is urgent,
**So that** downstream reviewers immediately see which submissions need to be worked first and why, without a side-channel email or phone call.

**Why it matters:** Today urgency is communicated informally, so time-sensitive Provider Change requests (e.g., an imminent effective-date deadline or member-access impact) get worked in the same FIFO order as routine changes. Surfacing a rush flag and its reason on the Case Manager lets reviewers triage by business urgency and reduces missed deadlines.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Provider Change (capture) | `PRM_ProviderChangeForm_English` (v83) | Submission/details step where the change is described | New "Rush Review" toggle + "Rush Review Reason" picklist elements; save IP/DataRaptor maps them to the Case Manager |
| Provider Change QC (downstream review) | `PRM_ProviderChangeQC_English` (v13) | Review/summary step | Read-only display sourced from the Case Manager's rush-review fields |
| Case Manager record view | N/A (Lightning record page / FlexCard) | Case Manager (IndividualApplication) page | New rush-review fields + visual indicator |

**In scope:** the main Provider Change Form only. **Out of scope:** the Capitation Site and PDA Update variants (`PRM_ProviderChangeFormCapitationSite_English`, `PRM_ProviderChangePDAUpdate_English`) — a follow-up story if the business wants parity.

---

## Current State (from codebase)

- `PRM_ProviderChangeForm_English` — active version is **v83** (v62–v83 present; only v83 is the live OmniScript). No rush-review or expedited-review element exists today.
- `PRM_ProviderChangeQC_English` — active version is **v13** (v14 exists but is inactive). No rush-review display today.
- Downstream "Case Manager" = the **`IndividualApplication`** object (per the PNM object model). No rush-review fields exist on it today.
- Component discovery note: the `code-review-graph` knowledge graph is currently unpopulated for this repo (2 files indexed), so components were verified by scanning `force-app/main/default/omniScripts/**` directly.

---

## Acceptance Criteria

**AC-1 — PDM Specialist flags a submission for rush review with a reason**

**Given** a PDM Specialist is completing a Provider Change submission,
**When** they turn on the "Rush Review" toggle, select a Rush Review Reason, and submit,
**Then** the submission is saved and the Case Manager records that it is flagged for rush review together with the selected reason,
**And** the PDM Specialist sees a confirmation that the change was submitted for expedited review.

**AC-2 — Reason is mandatory when rush review is turned on (negative path)**

**Given** a PDM Specialist has turned on the "Rush Review" toggle on the Provider Change form,
**When** they attempt to submit without selecting a Rush Review Reason,
**Then** the form blocks submission and shows a validation message asking them to provide the reason for the rush review,
**And** no submission is saved until a reason is selected.

**AC-3 — Routine submissions are unaffected**

**Given** a PDM Specialist leaves the "Rush Review" toggle off,
**When** they complete and submit the Provider Change form,
**Then** the Rush Review Reason is neither shown nor required,
**And** the submission is saved as a routine change,
**And** the Case Manager shows no rush-review indicator.

**AC-4 — Rush flag and reason are visible on the Case Manager**

**Given** a submission was flagged for rush review with a reason,
**When** a reviewer opens the resulting Case Manager,
**Then** a clear visual rush-review indicator is displayed on the Case Manager,
**And** the captured Rush Review Reason is shown next to it,
**And** the indicator is not shown for Case Managers created from routine (non-rush) submissions.

**AC-5 — Reason is visible read-only during downstream QC review**

**Given** a Case Manager flagged for rush review moves into Provider Change QC review,
**When** a reviewer opens the Provider Change QC flow for that Case Manager,
**Then** the rush-review indicator and the Rush Review Reason are shown read-only within the QC review,
**And** the reviewer cannot edit the reason from the QC flow.

**AC-6 — Create the following fields on Case Manager (IndividualApplication)**

- **API Name:** `PRM_RushReview__c`
  - **Object:** IndividualApplication (Case Manager)
  - **Type:** Checkbox
  - **Label:** Rush Review
  - **Default:** false
  - **Track History:** true
  - **Reportable:** yes
- **API Name:** `PRM_RushReviewReason__c`
  - **Object:** IndividualApplication (Case Manager)
  - **Type:** Picklist (restricted)
  - **Label:** Rush Review Reason
  - **Proposed values (confirm with business — see Clarification Q2):** Member Access Impact; Effective-Date / Contractual Deadline; Regulatory or Compliance Deadline; Provider Termination Risk; Leadership / Escalation Request; Other
  - **Required:** false at the object level; enforced as required in the OmniScript only when Rush Review is on (AC-2)
  - **Track History:** true
  - **Reportable:** yes

**AC-7 — Field access & permission sets**

- **PRM_DataModifyAll:**
  - Field level: Read and Edit on `PRM_RushReview__c` and `PRM_RushReviewReason__c`
- **PRM_ProviderDataAdmin, PRM_CredentialingUser** (persona-facing PDM/credentialing perm sets — confirm exact set names, Clarification Q4):
  - Field level: Read and Edit on both new fields (capture on the form)
- **PRM_DataViewAll, PRM_NetworkManagementQC:**
  - Field level: Read on both new fields (downstream review)

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_RushReview__c` on IndividualApplication | New custom field (Checkbox) | Stores the rush flag; history tracked | Drives AC-1, AC-4, AC-6 |
| `PRM_RushReviewReason__c` on IndividualApplication | New custom field (restricted Picklist) | Stores the reason; history tracked | Drives AC-1, AC-6; value set per Clarification Q2 |
| `PRM_ProviderChangeForm_English` (v83 → new version) | Modified OmniScript | Add "Rush Review" toggle + conditionally-shown "Rush Review Reason" picklist; make reason conditionally required; map both to the save payload | Drives AC-1, AC-2, AC-3 |
| Provider Change save IP / DataRaptor | Modified IP step / DR mapping | Map the two new elements onto the Case Manager on submit | Drives AC-1; exact component TBD (Clarification Q1) |
| Case Manager Lightning record page / FlexCard | Modified UI | Add rush-review indicator + reason, conditional on `PRM_RushReview__c` | Drives AC-4 |
| `PRM_ProviderChangeQC_English` (v13 → new version) | Modified OmniScript | Add read-only rush-review indicator + reason to the review step | Drives AC-5 |
| Permission sets (FLS) | Config | Apply Read / Read-Edit per AC-7 | Drives AC-7 |
| Field history / report type | Config | Enable history tracking on both fields; ensure fields available to Case Manager reporting | Reporting + audit requirement |

No new Apex is anticipated; if the save path is Apex-driven rather than DR-driven (Clarification Q1), add unit coverage ≥85% for the new mapping.

---

## Definition of done

- [ ] With "Rush Review" on and a reason selected, the submission saves and the Case Manager reflects the flag + reason (AC-1).
- [ ] With "Rush Review" on and no reason, submission is blocked with a clear message and nothing is saved (AC-2).
- [ ] With "Rush Review" off, the reason is hidden/not required and no indicator appears on the Case Manager (AC-3).
- [ ] The rush-review indicator + reason render on the Case Manager record and only for rush submissions (AC-4).
- [ ] The reason renders read-only inside the Provider Change QC flow (AC-5).
- [ ] Both fields deployed with FLS applied per AC-7 and field history tracking enabled.
- [ ] Both fields are available in Case Manager reporting.
- [ ] No regression to non-rush Provider Change submissions or to the Capitation Site / PDA Update variants.
- [ ] ≥85% Apex coverage incl. negative path, *if* any Apex is touched in the save path.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which component writes the Provider Change submission to the Case Manager (a DataRaptor Post, or an Apex/IP save chain), so the two new fields are mapped in the right place? Does Provider Change always create/associate an `IndividualApplication`, or only in some paths? | Determines where mapping goes and whether Apex + tests are needed; if some paths have no Case Manager, we need an alternate home for the reason | Technical |
| 2 | Confirm the exact Rush Review Reason picklist values (the six proposed are a starting set). | Wrong/short list forces a rework and re-training | BA / Ops |
| 3 | Should turning off "Rush Review" after a reason was chosen clear the stored reason, or retain it for audit? | Data-retention + reporting behavior | BA / Ops |
| 4 | Confirm the exact PDM/credentialing permission set API names that capture vs. only view these fields. | FLS correctness; wrong set blocks the persona or over-exposes | Technical / Ops |
| 5 | Should the rush indicator also appear on any list views, queues, or the Case Manager UI redesign (`requirements/PRM_UIRedesign_CaseManager_SK_Estimation.md`)? | Scope of downstream visibility | Product |
| 6 | Is any SLA/turnaround expectation attached to "rush" (even if not automated now), for reporting? | May add a target/received-date field later | Product / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_ProviderChangeForm_English` (v83) | OmniScript | MEDIUM | New elements + conditional required rule + payload mapping |
| `PRM_ProviderChangeQC_English` (v13) | OmniScript | MEDIUM | New read-only display element |
| IndividualApplication (Case Manager) | Object | MEDIUM | Two new fields + history tracking |
| Provider Change save IP / DataRaptor | IP / DataRaptor | MEDIUM | Field mapping on submit (component TBD, Q1) |
| Case Manager record page / FlexCard | UI | LOW | Conditional indicator + reason display |
| Permission sets | Config | LOW | FLS for two fields |
| Capitation Site / PDA Update variants | OmniScript | NONE (this story) | Explicitly out of scope; candidates for a parity follow-up |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_RushReview__c` + `PRM_RushReviewReason__c` | Custom fields + picklist value set | S | Config; restricted picklist |
| Field history + report availability | Config | S | Enable tracking on both fields |
| `PRM_ProviderChangeForm_English` | OmniScript element + conditional-required + mapping | M | New OmniScript version |
| Provider Change save IP / DataRaptor | IP step / DR mapping | M | Depends on Q1 (may add Apex + tests) |
| Case Manager record page / FlexCard indicator | UI | M | Conditional visual indicator |
| `PRM_ProviderChangeQC_English` | OmniScript read-only display | M | New OmniScript version |
| Permission sets (FLS) | Config | S | Per AC-7 |
| Testing (happy + negative + downstream display) | QA | M | Incl. Apex coverage if save path is Apex |

**Total Estimated Effort:** ~L overall (bumps toward XL if the save path is Apex-driven, per Q1). *AI-estimated — validate with team.*
