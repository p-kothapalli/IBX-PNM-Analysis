# USER STORY: Non-Routine Committee Status Update — Application Withdrawal

**Persona:** Cred Compliance Specialist
**Priority:** P1 — adds a missing terminal decision path to a live production flow
**OmniScript:** `PRM_NonRoutineCommitteeReview_English` (v4 = latest in repo; confirm active version before build)
**Integration Procedures:** `PRM_NonroutineCommitteeReviewUpdateParent` → `PRM_NonroutineCommitteeReviewUpdate` (**no change required** — see Technical Implementation)
**Apex:** `PRM_PARRequestDenialUtility`, `PRM_CaseManagerDenialUtility`
**Relevant Requirements:** REQ **1313808** (this story) · similar to #1254897 · builds on story numbers 1295081, 1334611, 1443813
**Document Version:** 2.0 (supersedes v1.0 of 2026-05-20 — see *Corrections to v1.0* below)
**Vertical:** Provider Network Management (PNM) — Independence Blue Cross

---

## Story

**As a** Cred Compliance Specialist,
**I want** an explicit **"Application Withdrawal"** option on the *Update Status for Nonroutine Committee Case* step for both Initial Cred and Recred, which closes the committee case, completes the Case Manager as withdrawn, marks the practitioner as not credentialed, records an audit note, and clears the pending flag from every related record the application created,
**So that** a practitioner who voluntarily withdraws is closed out with the same data integrity as a committee denial, without me having to mis-record the outcome as a denial.

**Why it matters:** There is no terminal option for a voluntary withdrawal today. Specialists either select **"Nonroutine Committee Denied - Closed"** and type "withdrew" into Notes — which is factually and legally wrong, because the committee never denied the provider — or they close the case manually outside the guided flow, which skips the pending-flag cleanup entirely. The manual route leaves pending practice locations, NPIs, identifiers, and taxonomies stranded on the provider record, so downstream future-dated processing, re-credentialing windows, and network reporting keep treating the application as in-flight. This is a recurring data-quality defect class, not a cosmetic gap.

---

## Scope

| Flow | OmniScript | Affected Step | Branch | Data source behind it |
|---|---|---|---|---|
| Initial Cred — Nonroutine Committee Review | `PRM_NonRoutineCommitteeReview_English` | `UpdateCaseStatus` | New option on the Initial Cred dropdown (`CaseStatus`) | New Set Values + new Remote Action; existing generic IP branch + `PRMUpdateIDCaseCaseMgr` / `PRMDRUpdatePractitioner` |
| Recred — Nonroutine Committee Review | `PRM_NonRoutineCommitteeReview_English` | `UpdateCaseStatus` | New option on the Recred dropdown (`CaseStatusRecred`) | Same as above |

**Out of scope (explicit):**

- Routine Committee Review and HACAC committee flows — separate OmniScripts, separate dropdowns, not in this request.
- Provider-facing withdrawal letter / email generation (see Clarification Q6).
- Behaviour of the existing 9 (Initial Cred) / 10 (Recred) status options — unchanged, but regression-tested.
- Adding Board Certification to the pending sweep for the **existing denial** paths (see Clarification Q3 — this story scopes it to the Withdrawal path only).

---

## Current State (from codebase)

Verified by reading the OmniScript datapack elements, the Integration Procedure element tree, the DataRaptor field mappings, and the Apex utilities. The `code-review-graph` MCP was tried first per workspace rule but holds only 2 indexed JavaScript files for this repo, so file inspection was used as the documented fallback.

### The decision step — `UpdateCaseStatus`

| Element | Type | Current behaviour |
|---|---|---|
| `CaseStatus` | Select, **required** | 9 options, shown when the Case Manager record type is **not** Re-Credentialing. Last option = "Nonroutine Committee Specialist Review". |
| `CaseStatusRecred` | Select, **not required** | 10 options, shown when the record type **is** Re-Credentialing. Last option = "Nonroutine Due Processing Hearing". |
| `DecisionDate` | Date, required | Shown for "Nonroutine Committee Approved" and "Nonroutine Committee Denied - Closed" on either dropdown (4 OR rules). |
| `DenialReason` | Select, required | 16 hardcoded options; shown only for "Nonroutine Committee Denied - Closed" on either dropdown (2 OR rules). |
| `Notes` | Text Area, required | `show: null` — always visible for every status. **No change needed.** |
| `SVNRCommitteeDeniedClosed` | Set Values | Builds the `RecordsToUpdate` payload for the denial branch. Behavioural reference for the new element. |
| `NRCommitteeDeniedClosed` | Remote Action | Calls the pending-cleanup engine with the Case Manager Id. Wiring reference for the new element. |

### The Integration Procedure has three top-level branches, keyed on the committee decision

| Branch | Fires when | What runs inside |
|---|---|---|
| `NotNonRoutineCommDeniedClosed` | decision **≠** "Nonroutine Committee Denied - Closed" | Create new Case (only if a new-case parent is supplied) · **update Case + Case Manager** via `PRMUpdateIDCaseCaseMgr` · **update Practitioner** via `PRMDRUpdatePractitioner` (only if a Practitioner Id is supplied) · **create the Note** |
| `isLastManStanding` | decision **=** Denied - Closed **and** other active practitioners remain | `PRMDRUpdateCaseAndCMForNonroutineCommitteeReview` + `PRMUpdateCaseCsMgrNonRoutineUpdateDenied` |
| `isNotLastManStanding` | decision **=** Denied - Closed **and** no active practitioners remain | Related-data extracts + termination / convert-to-non-par table updates + note |

**This is the single most important current-state fact for this story:** because "Application Withdrawal" is *not* "Nonroutine Committee Denied - Closed", it routes through the **generic first branch automatically**, and that branch already writes the Case, the Case Manager, the Practitioner, and the Note. **No Integration Procedure change is required.**

### Field coverage of the generic branch's DataRaptors

| DataRaptor | Writes |
|---|---|
| `PRMUpdateIDCaseCaseMgr` | Case: `Id`, `Status`, `OwnerId`, `PRM_DenialReason__c`, round-robin flag · Case Manager: `Status`, `PRM_Stage__c`, **`PRM_Decision_Date__c` (payload key `PRM_DecisionDate__c`)**, `PRM_DenialReason__c`, `ApplicationCaseId`, and ~50 other verification fields |
| `PRMDRUpdatePractitioner` | Account: `Id`, `PRM_CredentialingStatus__c`, `PRM_ReCredDueDate__c` |

The `Practitioner` payload node is already used by other branches (e.g. the Denied - Appeal Open and Approved branches set Credentialing Status declaratively), so **the practitioner's credentialing status can be set for both Initial Cred and Recred with no Apex change.**

### The pending-cleanup engine — `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial`

Called today from the Nonroutine denial Remote Action, the Routine committee denial, an off-cycle denial, and an Invocable entry point for Flow. It clears the pending flag on **15 of the 16** object types the requirement lists, each filtered to rows that are not error records and are currently pending:

Practitioner Practice Location · Practice Location · Practice Location Summary · Address · Location Address · Identifier · Location NPI History · Healthcare Provider · Healthcare Provider NPI · Healthcare Provider Taxonomy · Vendor Account · Alternative Contact Methods · Provider Feature · Account-Account Relationship *(Initial Cred / PNC only)* · Practitioner Person Account *(Initial Cred / PNC only, also sets Credentialing Status)*

**Two confirmed gaps versus REQ 1313808:**

1. **Board Certification is never touched.** The object does carry the required field shape (`PRM_Pending__c`, `PRM_Active__c`, `PRM_CaseManager__c`, `PRM_IsErrorRecord__c`), so it can be added.
2. **There is no explicit "Active = FALSE" filter.** The engine filters on *pending* only, and relies on the assumption that pending is only ever true on inactive rows.

The requirement's highlighted rule — *"unless record is Pending for another Case Manager"* — is **already implemented** for the shared group and practice location by the in-progress-sibling guard added under story 1443813 (and mirrored for the closure path by `PRM_DenialSharedPendingGuard`). Every other object type is read through a Case-Manager-scoped sub-query, so it is inherently scoped to this application.

### Terminal picklist availability (blocking finding)

| Record type | `Status` values available | Withdrawal-capable? |
|---|---|---|
| Practitioner Participation Request (Initial Cred) | 9, including **Denied** and **Withdrew** | ✅ Yes |
| Re-Credentialing | 8 — *Additional Review Needed, Approved, CAQH Action Needed, In Progress, On Hold, Pending CAQH Access, Pending Closure, Pending NPDB* | ❌ **No — neither Withdrew nor Denied is available** |

`PRM_DenialReason__c` has 54 values defined at field level but only 16 (Recred) / 17 (Initial Cred) exposed per record type — and **no withdrawal-related value is exposed on either**, even though the field already defines *"Provider withdrew after app submitted"* and *"Provider withdrew App. after submitting"*. See Clarification Q2.

---

## Acceptance Criteria

> Patterns per `.cursor/skills/user-story-architect/references/ac-pattern-library.md`:
> A = behavioural Given/When/Then, B = field/metadata spec, D = update rules, E = per-object record recipe.

### AC-1 — The new option is available to Initial Cred committee cases

**Given** I am a Cred Compliance Specialist reviewing a Nonroutine Committee case for an initial credentialing application,
**When** I open the Nonroutine Committee Review flow and reach the *Update Status for Nonroutine Committee Case* step,
**Then** **"Application Withdrawal"** appears as the **last** option in the status dropdown, after "Nonroutine Committee Specialist Review",
**And** the nine existing options appear unchanged, in their existing order.

### AC-2 — The new option is available to Recred committee cases

**Given** I am a Cred Compliance Specialist reviewing a Nonroutine Committee case for a re-credentialing application,
**When** I open the Nonroutine Committee Review flow and reach the *Update Status for Nonroutine Committee Case* step,
**Then** **"Application Withdrawal"** appears as the **last** option in the status dropdown, after "Nonroutine Due Processing Hearing",
**And** the ten existing options appear unchanged, in their existing order.

### AC-3 — Choosing Application Withdrawal asks for decision date, reason and notes

**Given** I am on the *Update Status for Nonroutine Committee Case* step for either an initial credentialing or a re-credentialing case,
**When** I select **"Application Withdrawal"**,
**Then** the Decision Date field, the Reason dropdown, and the Notes box are all displayed,
**And** all three are mandatory — I cannot complete the step until every one is filled,
**And** the Reason dropdown offers a withdrawal-specific reason I can select.

### AC-4 — Metadata required to make the withdrawal outcome selectable and reportable

*Pattern B — configuration spec.*

- **Guided-flow status dropdowns** (Initial Cred and Recred): add option
  - **Label:** `Application Withdrawal`
  - **Stored value:** `Application Withdrawal`
  - **Position:** last option in both dropdowns
  - **Required flag:** unchanged (Initial Cred dropdown stays required; Recred dropdown stays not-required)
- **Case Manager → Status**, Re-Credentialing record type: make available the value
  - **Value:** `Withdrew`
  - **Reason:** the Re-Credentialing record type currently exposes only 8 in-progress Status values; the withdrawal outcome cannot be reported or set from the UI without it. Already available on the Initial Cred record type — no change there.
- **Case Manager → Denial Reason**, *both* Practitioner Participation Request and Re-Credentialing record types: make available the withdrawal reason value
  - **Recommended value:** `Provider withdrew after app submitted` *(already defined at field level — no new picklist value needed)*
  - **Alternative if Product prefers new wording:** add `Voluntary Withdrawal` at field level, then expose on both record types (see Clarification Q2)
- **Guided-flow Reason dropdown:** add the same value as a new option, and expand its display condition so it also shows for `Application Withdrawal`
- **Guided-flow Decision Date:** expand its display condition so it also shows for `Application Withdrawal` on both dropdowns
- **Track History:** no change · **New fields:** none · **New objects:** none

### AC-5 — Completing the withdrawal closes out the application end to end

**Given** I have selected **"Application Withdrawal"** and supplied a decision date, a reason, and notes,
**When** I click **Done**,
**Then** the committee case is closed,
**And** the Case Manager is completed with a withdrawn outcome carrying my decision date and reason,
**And** the practitioner is no longer shown as credentialed,
**And** an audit note titled "Application Withdrawal" holding my notes is attached to the Case Manager,
**And** every record this application had left in a pending state is no longer flagged as pending,
**And** I am returned an acknowledgement rather than an error.

### AC-6 — Records updated on Done (Initial Cred)

*Pattern E — exact record recipe. Parents before children.*

**Given** the Case Manager is an **initial credentialing** application and the outcome is **Application Withdrawal**,
**When** I click **Done**,
**Then** the following records are updated exactly as specified:

**Case (Committee Review) — Update**

| Field | Value | Notes |
|---|---|---|
| Case | {current committee case} | the record the flow was launched from |
| Status | `Closed` | `IsClosed` follows automatically from the status |

**Case Manager — Update**

| Field | Value | Notes |
|---|---|---|
| Case Manager | {Case Manager of the committee case} | |
| Stage | `Complete` | |
| Status | `Withdrew` | requirement left this blank; ratified as `Withdrew` |
| Decision Date | {Decision Date entered on the step} | must persist on the Case Manager — see Technical Implementation for the mapping caveat |
| Denial Reason | {Reason selected on the step} | |

**Practitioner (Person Account) — Update**

| Field | Value | Notes |
|---|---|---|
| Practitioner Account | {Account of the committee case} | |
| Credentialing Status | `Denied` | set declaratively by the guided flow |
| Pending | `FALSE` | set by the cleanup engine; applies where the practitioner account is pending |

**Note — Create**

| Field | Value | Notes |
|---|---|---|
| Title | `Application Withdrawal` | |
| Body | {Notes entered on the step} | |
| Related to | {Case Manager} | |

**And** no new downstream case is created (see AC-9).

### AC-7 — Records updated on Done (Recred)

*Pattern E — the Recred branch, called out separately so QA can test it independently.*

**Given** the Case Manager is a **re-credentialing** application and the outcome is **Application Withdrawal**,
**When** I click **Done**,
**Then** every record listed in AC-6 is updated with the same values, with these branch differences:

| Object | Difference from the Initial Cred recipe |
|---|---|
| Practitioner (Person Account) → Credentialing Status | Still set to `Denied` — this is a **behaviour change**: today's cleanup engine only sets it for initial credentialing and PNC. Delivered declaratively via the guided flow so it applies to both branches. |
| Practitioner (Person Account) → Pending | Not changed on the Recred branch — the practitioner account is not flagged pending by a re-credentialing application. |
| Account-Account Relationship → Pending | Not changed on the Recred branch — the cleanup engine scopes this to initial credentialing and PNC only. Confirm with Product (Clarification Q4). |
| Case Manager → Status | Requires the metadata change in AC-4; the value is not currently available on the Re-Credentialing record type. |

### AC-8 — Pending flag is cleared across all 16 impacted record types

*Pattern D + E — the sweep, with its guards.*

**Given** the withdrawn application left related records in a pending state,
**When** I click **Done**,
**Then** each record type below has **Pending = FALSE** applied, subject to the guards:

| # | Record type (business label) | Field set | Guard |
|---|---|---|---|
| 1 | Vendor / Group Account | Pending = FALSE | skipped when another practitioner or another in-progress application still references the group |
| 2 | Practitioner Person Account | Pending = FALSE | initial credentialing / PNC only |
| 3 | Account-Account Relationship | Pending = FALSE | initial credentialing / PNC only |
| 4 | Healthcare Provider | Pending = FALSE | pinned to this Case Manager |
| 5 | Healthcare Provider Taxonomy | Pending = FALSE | pinned to this Case Manager |
| 6 | Identifier (not Document) | Pending = FALSE | parented to a swept group or the practitioner; excludes retained groups |
| 7 | **Board Certification** | Pending = FALSE | **NEW** — pinned to this Case Manager |
| 8 | Practitioner Practice Location | Pending = FALSE | pinned to this Case Manager |
| 9 | Practice Location | Pending = FALSE | skipped when pending for another Case Manager or another in-progress application |
| 10 | Location Address | Pending = FALSE | via the swept practice locations |
| 11 | Address | Pending = FALSE | via the swept location addresses |
| 12 | Practice Location Summary | Pending = FALSE | pinned to this Case Manager |
| 13 | Healthcare Provider NPI | Pending = FALSE | individual NPI of this practitioner, or NPI of a swept practice location |
| 14 | Location NPI History | Pending = FALSE | via the swept practice locations |
| 15 | Alternative Contact Methods | Pending = FALSE | via the swept practice locations |
| 16 | Provider Feature | Pending = FALSE | via the swept practice locations or practitioner practice locations |

**And** in every case only records that are currently pending, are not error records, and have **Active = FALSE** are considered,
**And** the Active flag itself is never modified by this flow.

### AC-9 — Withdrawal is terminal: no follow-on case is created

**Given** I complete an Application Withdrawal,
**When** the flow finishes,
**Then** no new downstream case (PDA review, Recred update, or otherwise) is created for this Case Manager,
**And** the Case Manager's link to its current case is left intact,
**And** the practitioner's re-credentialing due date is left unchanged.

### AC-10 — Records that are active are left alone

**Given** the practitioner has a related record that is flagged pending but is also **Active**,
**When** I complete an Application Withdrawal,
**Then** that record remains flagged pending and remains active,
**And** nothing about its effective dates changes.

*Requirement dev note, verbatim: "Do not update Active = FALSE for Existing/Active Records".*

### AC-11 — Records still needed by another Case Manager are left alone

**Given** the same provider has a second, still in-progress application whose pending records overlap with the withdrawn application's group or practice location,
**When** I complete an Application Withdrawal on the first application,
**Then** the shared group and practice location remain flagged pending,
**And** only the withdrawn application's own links are cleared,
**And** the second application can still be completed normally.

### AC-12 — Re-running the flow on an already-withdrawn case is blocked

**Given** a committee case has already been closed through Application Withdrawal,
**When** I launch the Nonroutine Committee Review flow on it again,
**Then** I am shown the existing invalid-case message instead of the decision step,
**And** no second audit note is created and no records are swept a second time.

### AC-13 — A failure during cleanup surfaces to me and is logged

**Given** the pending-record cleanup fails part-way through,
**When** I click **Done**,
**Then** I am shown the flow's error message rather than a success acknowledgement,
**And** the failure is written to the exception log with the Case Manager reference,
**And** I can re-run the flow once the underlying problem is fixed.

### AC-14 — The nine/ten existing decision paths are unaffected

**Given** any of the existing committee decisions (MD Approved, Sent to Committee, Committee Approved, Denied - Appeal Open, Appealed, Denied - Closed, Medical Director Pend, Pend - Provider Outreach, Specialist Review, Due Processing Hearing),
**When** I complete the flow with that decision,
**Then** the resulting records, notes, follow-on cases and pending flags are exactly as they were before this change.

---

## Technical Implementation (high-level)

| # | Component | Type | Change | Drives |
|---|---|---|---|---|
| C1 | `PRM_NonRoutineCommitteeReview_English` / `CaseStatus` | OmniScript element (Select) | Append option `Application Withdrawal` as the last entry; `required` unchanged | AC-1, AC-4 |
| C2 | `PRM_NonRoutineCommitteeReview_English` / `CaseStatusRecred` | OmniScript element (Select) | Append the same option as the last entry; `required` unchanged | AC-2, AC-4 |
| C3 | `PRM_NonRoutineCommitteeReview_English` / `DecisionDate` | OmniScript element (Date) | Add 2 rules to the existing OR group: `CaseStatus = "Application Withdrawal"`, `CaseStatusRecred = "Application Withdrawal"` | AC-3 |
| C4 | `PRM_NonRoutineCommitteeReview_English` / `DenialReason` | OmniScript element (Select) | Add the same 2 show rules, plus a new option for the withdrawal reason value ratified in Q2 | AC-3, AC-4 |
| C5 | `PRM_NonRoutineCommitteeReview_English` / **NEW** `SVApplicationWithdrawal` | OmniScript element (Set Values) | Mirror of `SVNRCommitteeDeniedClosed`, shown when either dropdown = `Application Withdrawal`. Payload: `Case{Id, Status:"Closed"}`, `CommitteeCase:"Application Withdrawal"`, `ContentNote{Title:"Application Withdrawal", Content, EntityId}`, `IndividualApplication{Id, Status:"Withdrew", PRM_Stage__c:"Complete", PRM_DecisionDate__c, PRM_DenialReason__c}`, `Practitioner{Id, CredentialingStatus:"Denied"}`, `NewCase{}` empty. **Omit `LatestCase`** so no follow-on case is created | AC-5, AC-6, AC-7, AC-9 |
| C6 | `PRM_NonRoutineCommitteeReview_English` / **NEW** `RAApplicationWithdrawal` | OmniScript element (Remote Action) | Mirror of `NRCommitteeDeniedClosed`: `remoteClass = PRM_PARRequestDenialUtility`, `remoteMethod = ApplicationWithdrawal`, `extraPayload = { CaseManagerId }`, `sendOnlyExtraPayload = true`, same show rules as C5 | AC-5, AC-8 |
| C7 | `PRM_NonroutineCommitteeReviewUpdate` (IP) | Integration Procedure | **NO CHANGE.** The decision value differs from "Nonroutine Committee Denied - Closed", so the payload routes through the existing `NotNonRoutineCommDeniedClosed` branch, which already updates Case + Case Manager + Practitioner and creates the Note | AC-5, AC-6 |
| C8 | `IndividualApplication` → `Status`, Re-Credentialing record type | Record type metadata | Make `Withdrew` available | AC-4, AC-7 |
| C9 | `IndividualApplication` → `PRM_DenialReason__c`, both record types | Record type metadata | Make the ratified withdrawal reason value available (no new field-level value needed if `Provider withdrew after app submitted` is accepted) | AC-4 |
| C10 | `PRM_PARRequestDenialUtility` | Apex (existing) | Add an `ApplicationWithdrawal` branch to `invokeMethod` that reads `CaseManagerId`, guards against null, and calls the new withdrawal entry point on the cleanup utility | AC-5, AC-8, AC-13 |
| C11 | `PRM_CaseManagerDenialUtility` | Apex (existing) | (a) Extract today's `updatePendingCheckboxOnDenial` body into a private helper taking an `includeBoardCertification` flag. (b) Keep `updatePendingCheckboxOnDenial` delegating with the flag `false` so all four existing callers are byte-for-byte unchanged. (c) Add `updatePendingCheckboxOnWithdrawal` delegating with `true`. (d) Add a Board Certification block plus its sub-query on the Case Manager fetch, filtered to not-error, pending, and not-active. (e) Add an explicit `PRM_Active__c = false` filter to the existing sub-queries | AC-8, AC-10 |
| C12 | `PRM_CaseManagerDenialUtilityTest`, `PRM_PARRequestDenialUtilityTest` | Apex tests | New methods for: Initial Cred withdrawal, Recred withdrawal, active-record preservation, second-Case-Manager preservation, Board Certification sweep, dispatcher routing, and an unchanged-legacy-denial regression. Target ≥ 85% on both classes | AC-8, AC-10, AC-11, AC-14 |
| C13 | OmniScript datapack deployment | Release | Compile + export + deploy the OmniScript bundle; deploy record type metadata **before** the bundle | all |

**Design note — why the practitioner update is declarative.** The requirement asks for Credentialing Status = Denied on both branches, but the Apex engine gates that on initial credentialing and PNC. Rather than widen a utility shared by four callers, the new Set Values supplies a `Practitioner` node, which the generic IP branch already forwards to `PRMDRUpdatePractitioner`. This satisfies AC-7 with zero Apex risk.

**Build-time verification item.** The generic branch computes the Case Manager's case link from the `LatestCase` payload key. Confirm in a scratch/QA run that omitting `LatestCase` leaves the existing link untouched rather than blanking it; if it blanks, pass the current case Id explicitly instead.

---

## Corrections to v1.0 of this document

Recorded so reviewers who read the May 2026 draft do not rebuild the wrong design.

| v1.0 said | Verified reality |
|---|---|
| Change the IP's conditional formula to *exclude* Application Withdrawal from the generic branch, because "the Remote Action does the equivalent" | **Wrong and breaking.** The Remote Action only clears pending flags — it never writes the Case, the Case Manager, or the Note. Excluding Withdrawal from the generic branch would leave the case open and produce no note. The IP needs **no change at all.** |
| The denial path re-uses `PRMUpdateCaseCsMgrNonRoutineUpdateDenied`, and so should the Withdrawal path | That DataRaptor belongs to the *last-man-standing* denial branch and maps only 4 fields. The generic branch uses `PRMUpdateIDCaseCaseMgr`, which is what the Withdrawal path will use. |
| Decision Date flows through the payload key `DecisionDate` | The generic DataRaptor maps the input key **`PRM_DecisionDate__c`** to `PRM_Decision_Date__c`. The standard `DecisionDate` key is not mapped and would be silently dropped. |
| Recred credentialing status requires widening the Apex utility with a `forceCredStatusOnRecred` flag | Achievable declaratively via the `Practitioner` payload node, which the generic branch already supports. |
| The practitioner credentialing flip is gated on initial credentialing only | It is gated on initial credentialing **or PNC**; the engine has since gained the story-1443813 in-progress-sibling guard. |
| Not identified | The Re-Credentialing record type exposes **neither `Withdrew` nor `Denied`** as Status values, and no withdrawal reason is exposed on either record type. Metadata changes are required (AC-4). |
| Not identified | `PRM_DenialReason__c` already defines *"Provider withdrew after app submitted"* — a new picklist value is probably unnecessary. |

---

## Definition of done

- [ ] "Application Withdrawal" is selectable as the last option on both the Initial Cred and Recred status dropdowns in the target org (AC-1, AC-2).
- [ ] Selecting it makes Decision Date, Reason and Notes visible and mandatory, and a withdrawal reason is selectable (AC-3).
- [ ] Completing it on an **initial credentialing** case produces exactly the AC-6 record recipe, verified field by field.
- [ ] Completing it on a **re-credentialing** case produces exactly the AC-7 record recipe, verified field by field, including Credentialing Status.
- [ ] All 16 record types in AC-8 show Pending = FALSE after a withdrawal, including Board Certification.
- [ ] A pending **and active** record is left untouched (AC-10), and a record shared with a second in-progress application is left pending (AC-11).
- [ ] No follow-on case is created and the re-credentialing due date is unchanged (AC-9).
- [ ] Re-launching on an already-withdrawn case shows the invalid-case message (AC-12).
- [ ] A forced cleanup failure surfaces the error message and writes an exception log entry (AC-13).
- [ ] Record type metadata deployed: withdrawal Status value on Re-Credentialing, withdrawal reason on both record types (AC-4).
- [ ] ≥ 85% coverage on both Apex classes, including bulk and negative paths; **every pre-existing test in both test classes passes without modification** (AC-14).
- [ ] All 9/10 existing decision paths regression-tested with unchanged outcomes (AC-14).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| Q1 | The requirement leaves Case Manager "Status =" blank. Ratified in this story as **`Withdrew`**. Please confirm in writing, since it drives reporting filters and the record type metadata change. | Wrong value silently corrupts committee outcome reporting and the terminal-status set used by the shared-pending guard. | Product / BA |
| Q2 | `PRM_DenialReason__c` already defines *"Provider withdrew after app submitted"* and *"Provider withdrew App. after submitting"* — neither exposed on these record types. Re-use one of them, or create a new `Voluntary Withdrawal` value? | Determines whether AC-4 is a record-type exposure change only, or also a field-level picklist addition. | Product / BA |
| Q3 | Should Board Certification also be swept by the **existing denial** paths (Nonroutine denial, Routine committee denial, off-cycle denial, Flow entry point), or only by Withdrawal? This story scopes it to Withdrawal only. | If "all paths", C11 collapses to a simpler change but becomes a behaviour change to three live flows requiring their own regression. | Product / Technical |
| Q4 | On the **Recred** branch, should Account-Account Relationship and the practitioner account's Pending flag also be cleared? Today both are initial-credentialing/PNC only. The requirement lists them without a record-type qualifier. | Widens C11 and changes AC-7; affects provider visibility in dependent dashboards. | Product / Compliance |
| Q5 | Is a withdrawal ever **reversible** (provider re-submits)? If yes, is a new application created, or is the withdrawn Case Manager reopened? | Determines whether AC-12's hard block is correct, or whether a reopen path is needed. | Product |
| Q6 | Should a provider-facing withdrawal acknowledgement letter or email be generated? Today the denial path generates no letter from this flow. | Out of scope unless yes; would add an IP step and a template. | Product / Communications |
| Q7 | Should "Application Withdrawal" also be added to the HACAC and Routine Committee Review flows? This request says Nonroutine only. | Each is a separate OmniScript with its own decision date field; would roughly double the effort. | Product |
| Q8 | Confirm which OmniScript version is active in the target org (repo holds v1–v4; v4 presumed) and the deployment window for the record type metadata. | Wrong version edited = change silently absent after deploy. | Technical / Release |
| Q9 | Reporting: withdrawn Case Managers will carry a withdrawn status, not a denied one, while the practitioner's credentialing status reads Denied. Confirm no dashboard depends on those two agreeing. | Existing denial dashboards stay accurate; withdrawal volume appears in a different bucket. | Reporting / BA |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_NonRoutineCommitteeReview_English` | OmniScript | **HIGH** | Two dropdowns extended, two show-rule groups extended, two new elements. Whole bundle redeploys, so all 10 decision paths need regression. |
| `PRM_CaseManagerDenialUtility` | Apex | **HIGH** | Body refactored into a flagged helper and given a new object block. Shared by four live callers (Nonroutine denial, Routine committee denial, off-cycle denial, Flow) — the legacy public method must stay behaviourally identical. |
| `PRM_PARRequestDenialUtility` | Apex | **MEDIUM** | Additive dispatcher branch; existing branches untouched. |
| `IndividualApplication` record types | Metadata | **MEDIUM** | Status and Denial Reason availability changed on Re-Credentialing (and Denial Reason on Initial Cred). Affects UI pickers and report filters org-wide, not just this flow. |
| `PRM_NonroutineCommitteeReviewUpdate` (IP) | Integration Procedure | **LOW** | No change — but its generic branch now carries a new decision value, so that branch is on the regression path. |
| `PRMUpdateIDCaseCaseMgr`, `PRMDRUpdatePractitioner` | DataRaptors | **LOW** | Re-used as-is; no mapping changes. |
| `BoardCertification` | Object | **LOW** | New write target for the pending flag. No schema change. |
| Note | Object | **LOW** | New notes titled "Application Withdrawal". No schema change. |
| Future-dated / re-cred batch jobs and network reports | Downstream | **MEDIUM** | Withdrawn applications will now correctly drop out of the pending population — expect a one-off change in in-flight counts after go-live. |

---

## Estimated Effort

*AI-estimated — validate with the team during sprint planning.*

| # | Component | Change type | Effort | Points | Notes |
|---|---|---|---|---|---|
| C1 | Initial Cred status dropdown | Option add | S | 1 | One option appended. |
| C2 | Recred status dropdown | Option add | S | 1 | One option appended. |
| C3 | Decision Date visibility | Show-rule expand | S | 1 | Two rules added to an existing OR group. |
| C4 | Reason dropdown | Show-rule + option add | S | 1 | Two rules plus one option. |
| C5 | New Set Values element | New element | M | 2 | Mirrors the denial element; payload must use the correct decision-date key. |
| C6 | New Remote Action element | New element | M | 2 | Mirrors the denial Remote Action; show rules + extra payload. |
| C7 | Integration Procedure | None | — | 0 | Confirmed no change needed. |
| C8 | Recred Status value availability | Record type metadata | S | 1 | Deploy before the OmniScript bundle. |
| C9 | Denial Reason value availability | Record type metadata | S | 1 | Both record types. |
| C10 | Dispatcher branch | Apex add | M | 2 | ~10 lines plus a null guard. |
| C11 | Cleanup utility refactor + Board Certification + Active filter | Apex refactor | **L** | 3 | Highest-risk item: four live callers must be provably unchanged. |
| C12 | Apex tests | Test add | **L** | 3 | 7 new methods across 2 classes; legacy tests must pass untouched. |
| C13 | Datapack deployment | Release | M | 2 | Compile, export, ordered deploy. |
| — | QA pass — manual + automated | QA | **L** | 3 | Both branches, 11 negative/edge ACs, plus regression of all 10 existing paths. |

**Total Estimated Effort:** **L** — approximately **7–9 person-days** (~23 points) for one OmniStudio/Apex developer plus one QA engineer, roughly one sprint. Sizing is dominated by C11, C12 and the regression pass; the configuration work alone would be **M**.

---

## Dependencies & Sequencing

| Order | Step | Owner | Blocks |
|---|---|---|---|
| 1 | Answer Q1–Q4 (terminal status, withdrawal reason, Board Certification scope, Recred sweep scope) | Product / Compliance | Everything below |
| 2 | Deploy record type metadata (C8, C9) | Admin / Release | C1–C6 testing |
| 3 | Refactor the cleanup utility with the flag, add Board Certification, add tests (C11, C12) — legacy public method behaviour frozen | Backend Dev | C6, C10 |
| 4 | Add the dispatcher branch (C10) | Backend Dev | C6 |
| 5 | Build the OmniScript changes (C1–C6) | OmniStudio Dev | QA |
| 6 | Deploy to QA (C13) and run the 14 ACs plus regression of all 10 existing paths | Release / QA | UAT |
| 7 | UAT sign-off with a Cred Compliance Specialist on both an initial credentialing and a re-credentialing case | Product | Production |

---

## Cross-references

| Document | Relationship |
|---|---|
| `requirements/Permission_Set_Case_Manager_Owner_Change.md` | Same flow — confirm the withdrawal path does not regress owner-change behaviour. |
| `requirements/ReCred_CommitteeToQCReview_Rollback_Guide.md` | Adjacent Recred rollback path; be aware of co-existing data-fix scripts. |
| `requirements/FutureDated_Termination_PushOut_AddressUpdate_UserStory.md` | Source of the pending-sweep and "do not touch active records" semantics used in AC-8 and AC-10. |
| `requirements/PSV_Review_LWC_Redesign_Detailed_Design.md` | Upstream stage — a withdrawal can follow PSV; confirm PSV records are covered by the sweep. |
| `requirements/AgenticAI/ideas/Idea07_Application_Withdrawal_Triage_Agent.md` | Future automation idea that depends on this terminal path existing. |

---

*Review with BA, Tech Lead, and a Cred Compliance Specialist before implementation kickoff.*
