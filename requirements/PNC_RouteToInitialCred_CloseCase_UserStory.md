# USER STORY: Route a PNC Case to Initial Cred (Practitioner Participation) Instead of Closing It

**Persona:** Credentialing Specialist
**Priority:** P1
**OmniScript:** `PRM_CloseCaseGuidedFlow_English` (entry), `PRM_CredApplicationReviewOSTxnyRole_English` (downstream Initial Cred App Review)
**Integration Procedures:** `PRM_ReviewParCaseRecordsUpdateParent` → `PRM_ReviewParCaseRecordsUpdate`
**Relevant Requirements:** `Close_Case_PNC_Ancillary_User_Stories.md`, `ReCred_to_InitialCred_Conversion_Plan.md` (closest working analog), `PRM_PNC_CredentialingStatus_Blank_User_Story.md`, `PRM_PNC_Analysis.md`, `PRM_PNC_AppReview_Flows_Update_Analysis.md`

---

## Story

**As a** Credentialing Specialist working a PNC (Par Non Cred) case that is about to be closed,
**I want** to choose "Route to Initial Cred" as an outcome so the same Case Manager is converted into a Practitioner Participation (Initial Cred) case and enters the Application Review stage,
**So that** a practitioner who should be fully credentialed continues through the credentialing lifecycle instead of being dropped, without me re-keying the practitioner from scratch.

**Why it matters:** Closing a PNC case ends participation and discards the practitioner, vendor, NPI, taxonomy, education, license, and practice-location data already captured. When the business decision is really "this practitioner must be credentialed," closing forces a full re-entry via the PAR form. Routing the existing case into Initial Cred preserves the captured data and the audit trail, and puts the case on the correct governance track (Application Review → PSV → QC → Committee → PDA → Network Mgmt QC).

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Close Case (PNC) | `PRM_CloseCaseGuidedFlow_English` | New outcome branch on the Close Case step | `PRM_ReviewParCaseRecordsUpdateParent` IP |
| Initial Cred App Review (downstream) | `PRM_CredApplicationReviewOSTxnyRole_English` | Case Manager enters at Application Review | Existing Initial Cred intake/worklist |

**In scope:** the "Route to Initial Cred" outcome on the PNC Close Case flow; the record re-key of the existing `IndividualApplication` from `PRM_PNC` to `PRM_PractitionerParticipationRequest`; setting the case to the Application Review entry state; making the Credentialing Status non-blank on conversion (reversing the PNC blank rule for this case).

**Out of scope:** collecting CAQH and PSV verification data (the converted case runs through the normal Initial Cred CAQH pull + PSV afterward — nothing is pre-populated); Ancillary and Provider Change close flows; bulk conversion.

---

## Current State (from codebase)

### `PRM_CloseCaseGuidedFlow_English` (Close Case flow)
- Today the Close Case step captures **Denial Reason** (required) and **Note** (required), then `SetRecordsOtherType` / `SetRecordsQMReview` set the Case to **Closed** and the Case Manager to **Pending Closure** / **Denied**, persisted via `PRM_ReviewParCaseRecordsUpdateParent`. There is **no "route/convert" outcome** — every path terminates the case.

### PNC Case Manager identity (verified in metadata)
- `IndividualApplication` record types `PRM_PNC` and `PRM_PractitionerParticipationRequest` both exist (`force-app/main/default/objects/IndividualApplication/recordTypes/`).
- A PNC case carries **blank** `Account.PRM_CredentialingStatus__c` and blank `PRM_ReCredDueDate__c` **by design** (business rule confirmed Jul 2026 — `PRM_PNC_CredentialingStatus_Blank_User_Story.md`; write occurs in `PRM_PNCPDABatchHelper`), and PNC practitioners are **excluded from CAQH** (`PRM_CheckCAQHAccessOnDueAccountsBatch`).
- PNC creation (`PRM_PractitionerScreenRecordCreation`) already produces Account, Case, IndividualApplication, CaseDataManager, HealthcareProviderNpi, Identifier, PersonEducation, Degree, HealthcareProviderTaxonomy, BusinessLicense; PNC PDA adds the practice-location stack (HealthcareFacility, HealthcarePractitionerFacility, HealthcareFacilityNetwork, ProviderFeature, InfoCodeAssignment).

### Data gap vs. Initial Cred
- A PNC case has the demographic + NPI + taxonomy + education + license + practice-location **shell**, but is **missing the credentialing-verification layer** (CAQH attestation, PSV verifications, board certification, work history) and the **Initial Cred routing/identity fields** (record type, Stage = Application Review, Credentialing Status = In Progress, Category = Credentialing). This is the reason a straight "carry-over" is not sufficient; the converted case must run the credentialing steps.

---

## Acceptance Criteria

**AC-1 — "Route to Initial Cred" is available as a Close Case outcome for a PNC case**

**Given** I am a Credentialing Specialist on the Close Case flow for an open PNC case,
**When** I open the outcome options,
**Then** I see a "Route to Initial Cred" option alongside the existing close/deny options,
**And** the option is shown only when the case is a PNC case and is not already closed,
**And** choosing it requires me to enter a routing reason and a note before I can confirm.

**AC-2 — Confirming "Route to Initial Cred" converts the case and moves it to Application Review**

**Given** I selected "Route to Initial Cred" and entered a routing reason and note,
**When** I click Confirm,
**Then** the same Case Manager is converted to an Initial Cred (Practitioner Participation) case,
**And** the case enters the Application Review stage of the credentialing lifecycle,
**And** the practitioner's Credentialing Status is set to "Credentialing In Progress" (no longer blank),
**And** I am navigated to the converted Case Manager,
**And** the practitioner's existing NPI, taxonomy, education, license, and practice-location records are retained (nothing is deleted or re-created).

**AC-3 — Records updated on Confirm (outcome = Route to Initial Cred)** *(Pattern E)*

**Given** a Credentialing Specialist confirms the "Route to Initial Cred" outcome for a PNC case,
**When** they click Confirm,
**Then** the following records are updated/created exactly as specified:

**Case Manager (IndividualApplication) — Update**

| Field | Value | Notes |
|---|---|---|
| Record Type | Practitioner Participation Request | changed from PNC (`PRM_PractitionerParticipationRequest`) |
| Stage | Application Review | entry point of Initial Cred |
| Status | New / In Progress | per Initial Cred App Review entry state (confirm value) |
| Category | Credentialing | required by Welcome Letter + credentialing selectors |
| Owner | Application Review Queue | Initial Cred intake assignment (confirm queue) |
| Routing Reason | {selected reason} | why it was routed instead of closed |
| Conversion Flag | true | durable "PNC → Initial Cred" marker (see Technical Implementation) |

**Practitioner Account — Update**

| Field | Value | Notes |
|---|---|---|
| Credentialing Status | Credentialing In Progress | reverses the PNC blank rule for this practitioner |
| Recred Due Date | {unchanged / null} | set later on credentialing completion, not here |

**Case — Update**

| Field | Value | Notes |
|---|---|---|
| Type | Application Review | routes the case into the Initial Cred worklist |
| Status | New / Open | not Closed (this is the whole point of the story) |

**Note (ContentNote) — Create**

| Field | Value | Notes |
|---|---|---|
| Title | PNC Routed to Initial Cred | |
| Body | {routing note} | entered by the specialist |

**AC-4 — Credentialing Status / PNC-flag computation on conversion** *(Pattern D)*

**Given** a PNC case is being converted to Initial Cred,
**When** the conversion records are written,
**Then** the following are set per the rules below:

- **Credentialing Status =**
  - On conversion → "Credentialing In Progress"
  - (The PNC "keep blank" rule in the PNC PDA path must NOT re-blank this practitioner while the Initial Cred case is in flight.)
- **PNC flag (`Account.PRM_PNC__c`) =**
  - Business decision required — see Clarification Q1 (keep as-is until credentialed, or clear on conversion).
- **Recred Due Date =**
  - Unchanged at conversion; populated by the normal credentialing-completion path.

**AC-5 — Converted case runs the full Initial Cred credentialing path**

**Given** a case was routed from PNC to Initial Cred and sits at Application Review,
**When** the Credentialing Specialist works it forward,
**Then** the case follows the standard Initial Cred lifecycle (Application Review → PSV → QC → Committee → PDA → Network Management QC → Complete),
**And** CAQH pull and PSV verifications are performed as part of that path (they are not pre-populated from the PNC case),
**And** the case appears in the Initial Cred committee report (not the PNC/RCAT review worklist).

**AC-6 — Edge case: case already closed or not a PNC case**

**Given** the case is already closed, or its record type is not PNC,
**When** I open the Close Case flow,
**Then** the "Route to Initial Cred" option is not offered,
**And** the existing invalid-case / unsupported-type behavior is unchanged.

**AC-7 — Edge case: practitioner is already Credentialed on another active case**

**Given** the practitioner tied to the PNC case is already Credentialed (or has an in-flight Initial Cred/PAR case),
**When** I attempt to route the PNC case to Initial Cred,
**Then** I am blocked (or warned per business rule) so a duplicate credentialing case is not created,
**And** a clear message explains why (see Clarification Q4).

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CloseCaseGuidedFlow_English` | Modified OmniScript | Add a "Route to Initial Cred" outcome + reason/note capture; add a Set Values element (e.g., `SetRecordsRouteToInitialCred`) shown only when RecordType = PRM_PNC and case open | Drives AC-1, AC-2, AC-6 |
| `PRM_ReviewParCaseRecordsUpdate` (+ Parent) | Modified IP | Handle the new outcome: re-key IndividualApplication RecordType → `PRM_PractitionerParticipationRequest`, set Stage/Status/Category/Owner, write Account credentialing status, create the note; do NOT close the case | Drives AC-2, AC-3, AC-4 |
| `PRMUpdateIDCaseCaseMgr` (or a new PNC-conversion DR) | Modified/New DataRaptor | Support writing the PNC→PAR record-type change + Initial Cred entry fields | Confirm the bundle supports a record-type change; else add one |
| Conversion flag on `IndividualApplication` | New custom field | Durable marker (e.g. `PRM_PNCToInitialCredConversion__c`, Checkbox, track history) so reports/UI/downstream can identify converted cases (mirrors `PRM_ReCredToInitialCredConversion__c`) | Drives AC-3, reporting |
| `PRM_PNCPDABatchHelper` | Verify/Guard | Ensure the PNC "blank Credentialing Status / Recred Due Date" write does not re-blank a practitioner whose case has been converted to Initial Cred | Protects AC-2/AC-4 |
| Account `PRM_PNC__c` handling | Verify | Decide whether the PNC flag stays or clears on conversion (Clarification Q1); if it stays true, confirm CAQH-exclusion / recred selectors don't wrongly skip the converted case | Drives AC-4, AC-5 |
| Initial Cred App Review intake (`PRM_CredApplicationReviewOSTxnyRole_English`, committee report `PRM_ReviewInitialCredApplicants_English`) | Verify | Confirm a converted case (correct RecordType + Stage + Category) is picked up by the Initial Cred worklist and committee report | Drives AC-5 |
| Duplicate-case guard | New Apex/validation | Block/warn when the practitioner is already Credentialed or has an in-flight credentialing case | Drives AC-7 |

> Deep design (record re-key vs. new-case trade-offs, PNC-flag lifecycle, CAQH/PSV impact) can be captured in `requirements/Enhancements/PNC_RouteToInitialCred_Architecture.md` if needed.

---

## Definition of done

- [ ] "Route to Initial Cred" outcome appears on the PNC Close Case flow only for open PNC cases (AC-1, AC-6).
- [ ] Confirming the outcome converts the Case Manager (RecordType → Practitioner Participation Request), sets Stage = Application Review, Category = Credentialing, and does NOT close the case (AC-2, AC-3).
- [ ] Practitioner Credentialing Status becomes "Credentialing In Progress" and is not re-blanked by the PNC PDA path (AC-2, AC-4).
- [ ] Existing NPI/taxonomy/education/license/practice-location records are retained, not re-created (AC-2).
- [ ] Converted case flows through the full Initial Cred lifecycle and appears in the Initial Cred committee report; CAQH/PSV run as normal (AC-5).
- [ ] Duplicate credentialing case is prevented/warned when the practitioner is already Credentialed or in-flight (AC-7).
- [ ] New conversion field deployed with FLS for Credentialing Specialist profiles/permission sets; field history enabled.
- [ ] ≥85% Apex coverage on any new/changed Apex incl. bulk + negative paths; no regression to the existing PNC close/deny paths or the PAR close path.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | On conversion, should `Account.PRM_PNC__c` be **cleared** (practitioner is now on a credentialing track) or **kept true** until credentialing completes? Keeping it true risks CAQH-exclusion and recred selectors skipping the converted case. | Core data correctness; affects AC-4/AC-5 | BA / Product + Technical |
| 2 | Exact Initial Cred **entry state** values: what `Status`, `Owner`/Queue, and Case `Type` should a converted case have at Application Review? Should it match a fresh PAR submission exactly? | Routing/worklist correctness (AC-3) | Technical / Ops |
| 3 | Should conversion be gated by any **data-completeness check** (e.g., valid Person Education with Institution, active practice location) before allowing "Route to Initial Cred", given known PNC data-quality gaps (`SOQL/2026-06-23_CaseManagersMissingInstitution.md`)? | Prevents cases entering PSV with missing required data | BA / Technical |
| 4 | When the practitioner is **already Credentialed or has an in-flight credentialing case**, should conversion be **hard-blocked** or **warn-and-allow**? What message? | Duplicate-case prevention (AC-7) | BA / Product |
| 5 | Should converted cases be **excluded from any PNC batch processing** already queued (RCAT/PNC PDA) at the moment of conversion? | Prevents the case being processed on two tracks | Technical |
| 6 | Is a **notification** required (to the practitioner and/or an internal queue) when a PNC case is routed to Initial Cred, similar to the ReCred→Initial Cred conversion draft? | Comms scope | Product / Ops |
| 7 | Should the existing **Close Case denial reason** picklist be reused for the routing reason, or a new "Routing Reason" picklist created? | Field/config scope (AC-1) | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CloseCaseGuidedFlow_English` | OmniScript | HIGH | New outcome branch + conditional visibility; must not regress existing close/deny paths |
| `PRM_ReviewParCaseRecordsUpdate` / `...Parent` | Integration Procedure | HIGH | New conversion branch (record-type re-key, non-close updates) |
| `IndividualApplication` (PNC → PAR record type) | Object / RecordType | HIGH | Record-type change drives layouts, flows, committee report, Welcome Letter batch |
| `Account.PRM_CredentialingStatus__c` / `PRM_PNC__c` | Field logic | HIGH | Conversion must override the PNC blank rule; PNC-flag lifecycle decision (Q1) |
| `PRM_PNCPDABatchHelper` | Apex | MEDIUM | Guard so PNC blanking doesn't fight the converted case |
| `PRM_CredApplicationReviewOSTxnyRole_English` / `PRM_ReviewInitialCredApplicants_English` | OmniScript | MEDIUM | Verify converted case is picked up by App Review + committee |
| CAQH / PSV path | Process | MEDIUM | Converted case must run CAQH pull + PSV (not pre-populated) |
| New conversion field + FLS | Object / Perm set | LOW | Config for reporting + downstream identification |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_CloseCaseGuidedFlow_English` — new outcome + reason/note + visibility | OmniScript | L | New Set Values element + conditional show; regression on existing paths |
| `PRM_ReviewParCaseRecordsUpdate(+Parent)` — conversion branch | IP | XL | Record-type re-key + Initial Cred entry writes + note; non-close path |
| `PRMUpdateIDCaseCaseMgr` / new conversion DR | DataRaptor | L | Support record-type change + entry fields |
| Conversion flag field + FLS + history | Field / Perm set | S–M | Mirror `PRM_ReCredToInitialCredConversion__c` |
| `PRM_PNCPDABatchHelper` guard + duplicate-case guard | Apex | L | Prevent re-blank + duplicate credentialing case |
| App Review / committee pickup verification | Analysis / config | M | Confirm worklist + report inclusion |
| Tests (Apex ≥85% + OmniScript regression) | QA / Apex | L | Convert, non-close, edge cases, bulk, PNC/PAR close regression |

**Total Estimated Effort:** AI-estimated — validate with team — **XL** (primarily the IP conversion branch, the record-type re-key, and the PNC-blank/duplicate guards).

---

## Related User Stories

- `ReCred_to_InitialCred_Conversion_Plan.md` — closest working analog (re-key in place + durable conversion flag + committee handling); reuse its pattern (`PRM_ReCredToInitialCredConversion__c`, `PRM_DisplayType__c`).
- `Close_Case_PNC_Ancillary_User_Stories.md` — the PNC Close Case flow this story extends with a non-close outcome.
- `PRM_PNC_CredentialingStatus_Blank_User_Story.md` — the PNC "blank Credentialing Status / Recred Due Date" rule this story must reverse for converted cases.
- `PRM_PNC_Analysis.md`, `PRM_PNC_AppReview_Flows_Update_Analysis.md` — PNC data model + review/PDA/QC lifecycle context.

---

*End of Story*
