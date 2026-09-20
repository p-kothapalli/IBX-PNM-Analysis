# ReCred Case Manager Conversion to Initial Cred

## Objective

Enable PSV specialists to process a ReCred case through the existing ReCred PSV/QC flow, then route qualifying cases into the **Initial Cred committee + PDA + Network Management QC** path when the case is a conversion use case.

---

## Proposed Future-State Flow (step by step)

1. Case opens in ReCred guided flow (`PRM_RecredQC_English`).
2. In the first PSV step, specialist answers new gating question:
   - "Is this a ReCred to Initial Cred conversion OR practitioner out of compliance?"
3. If **No**:
   - follow existing ReCred flow behavior (no change).
4. If **Yes**:
   - continue current ReCred PSV and QC activities.
   - specialist/QC complete required documentation and submit.
5. At ReCred QC routing, case is sent to **Initial Cred Committee Review queue** (not standard ReCred committee track).
6. Committee user processes case in initial committee flow (`PRM_ReviewInitialCredApplicants_English`) with conversion flag visible.
7. Committee decision routes to **Initial Cred PDA Review and Update** (`PRM_InitialCredPDA_English`).
8. PDA completion routes to **Initial Cred Network Management QC** (`PRM_InitialCredPDAQC_English`).
9. Network Management QC completes final QA and closes/returns per existing Initial Cred outcomes.
10. Case Manager clearly shows "Conversion Use Case" indicators throughout the lifecycle.

---

## Current-State Findings (from metadata)

- ReCred guided flow exists in `PRM_RecredQC_English` and already has routing controls (`ReCredProceedTo`, `QCProceedTo`, `SetRecordRecredQC_*`, `SetQCReady*`, `IPUpdateRecredReviewUpdate`).
- ReCred currently routes to committee/medical/final development using ReCred-specific logic.
- Non-routine committee flow exists in `PRM_NonRoutineCommitteeReview_English` with ReCred-specific status control (`CaseStatusRecred`).
- Initial committee flow exists in `PRM_ReviewInitialCredApplicants_English`, with assignment IP `PRM_ReviewInitialCredAppListAssignment`.
- Initial Cred PDA and Network Mgmt QC flows exist (`PRM_InitialCredPDA_English`, `PRM_InitialCredPDAQC_English`).
- Case/page layout metadata is not present in this repo export, so layout changes are required in org configuration (and should be backfilled to metadata source control if available).

---

## Business User Stories

### US-1: PSV specialist identifies conversion cases
As a PSV specialist, I want to mark a ReCred case as conversion/out-of-compliance at the beginning of PSV so that the case can follow the correct downstream governance path.

**Acceptance Criteria**
- New question appears in the first PSV step of ReCred flow.
- Response is required.
- Value is persisted on Case Manager (or related case context) as a durable conversion flag.
- Audit trail captures who answered and when.
- Case header/compact display shows `Type = Initial Cred` when conversion flag is true.

**Build Spec (configuration-only; no source changes in this repo)**
- **Target object (Case Manager):** `IndividualApplication`
- **Field API Name:** `PRM_ReCredToInitialCredConversion__c`
- **Field Label:** `ReCred to Initial Cred Conversion`
- **Field Type:** Checkbox (PNC-style pattern)
- **Default Value:** `false`
- **Required:** No
- **Field History Tracking:** Enabled
- **Help Text:** "Check when this ReCred case must be routed through Initial Cred committee/PDA/QC flow."

**Page Layout Update**
- Add `PRM_ReCredToInitialCredConversion__c` to Case Manager layout (`IndividualApplication` layout used by credentialing users).
- Suggested section: `Case Routing` or `Credentialing Controls`.
- Place near existing routing/status controls (`PRM_Stage__c`, `Status`, committee flags).

**Display Field (Compact/Header)**
- **Field API Name (suggested):** `PRM_DisplayType__c`
- **Field Type:** Formula (Text)
- **Formula:** `IF(PRM_ReCredToInitialCredConversion__c, "Initial Cred", TEXT(RecordType.Name))`
- Replace Record Type in compact/highlighted display with `PRM_DisplayType__c`.
- UI label should display as `Type`.

**List View Update**
- **List View Name:** `ReCred to Initial Cred Conversions`
- **Object:** `IndividualApplication`
- **Filter:** `PRM_ReCredToInitialCredConversion__c = true`
- **Suggested columns:** `Name`, `Status`, `PRM_Stage__c`, `PRM_ReCredToInitialCredConversion__c`, `LastModifiedDate`

**Admin Validation**
1. Update one sample Case Manager with checkbox = true.
2. Confirm record appears in conversion list view.
3. Confirm field is visible on Case Manager layout for required profiles.
4. Confirm field history captures update event.

### US-2: ReCred PSV/QC work remains intact for conversion cases
As a PSV/QC reviewer, I want conversion cases to still complete the ReCred PSV/QC process so that evidence quality is consistent before committee review.

**Acceptance Criteria**
- AC1: Existing PSV and QC sections are unchanged functionally.
- AC2: Existing validation, notes, and attachments continue to work.
- AC3: Only routing behavior changes for flagged conversion cases.
- AC4: First PSV step asks out-of-compliance/past-due question (required Yes/No).
- AC5: If answer = Yes, Person Education step is displayed in PSV.
- AC6: If answer = Yes, Person Education verification outcome is displayed in the review/summary step of both PSV and QC flows.
- AC7: On submit, answer = Yes updates Case Manager conversion checkbox to true.
- AC8: Case header/compact display shows `Type = Initial Cred` for conversion cases.
- AC9: Business users must have at least one valid (non-errored) Person Education record; all records cannot be marked as error.

**Question design (first PSV step)**
- **Question label (recommended):** `Is practitioner out of compliance or past due for ReCred?`
- **Help text:** `Select Yes when this ReCred should be treated as an Initial Cred conversion path.`
- **Response type:** Radio (required)
- **Options:** `Yes`, `No`
- **Stored data key:** `ReCredInitialCredConversionAnswer` (Yes/No)

**Primary Source Verification OmniScript logic**
- **Parent OmniScript:** `PRM_PrimarySourceVerificationReview_English`
- **Embedded PSV sub-OS:** `PRM_PSVSubOsWSNPDB_English`
- **Step already present:** `EducationVerification` in `PRM_PSVSubOsWSNPDB_English` (contains `CAQHPersonEducation` and `PersonEducationBlock`)
- **Current behavior found:** `EducationVerification` `show` requires `IsRecredentialing = false` (plus existing Work History / CaseType / Specialty checks), which suppresses this step for ReCred.
- **Required behavior change:** update `PRM_PSVSubOsWSNPDB_English_Element_EducationVerification.json` `show` condition to include conversion answer.
  - Recommended expression: show when `ReCredInitialCredConversionAnswer = "Yes"` **OR** existing condition evaluates true.
  - Preserve all existing dependencies (`WorkHistoryVerification` / `ReCredWHVerification` / `CaseType` / `SpecialtyFRML`) to avoid regression.

**Review/Summary step updates for Person Education (AC6)**

When the conversion question is answered Yes, the Person Education verification outcome must also appear on the review/summary step so the specialist can confirm it before final submission.

- **PSV OS (`PRM_PrimarySourceVerificationReview_English`):**
  - Summary is rendered via embedded sub-OS: `PRM_PSVSubOsSummary_English` (element `PSVSubOsSummary`)
  - Inside `PRM_PSVSubOsSummary_English`, `EducationVerificationFormula` already exists as a child of the `PSVSummary` step.
    - Expression: `%EducationVerificationOutcome%`
    - Label: `Education Verification`
    - Current show: `null` (always visible when parent step shows)
  - **Parent step `PSVSummary`** currently has show condition: `IsRecredentialing = false` AND `CaseType <> QC Review`.
  - **Required change:** Update `PSVSummary` show condition in `PRM_PSVSubOsSummary_English` to also show when `ReCredInitialCredConversionAnswer = "Yes"` (same pattern as EducationVerification step).
  - No change needed on the `EducationVerificationFormula` element itself (already shows when parent is visible).

- **ReCred QC OS (`PRM_RecredQC_English`):**
  - Active summary step: `ReCredPSVSummary` (label "Re-Cred QC Summary", show = null, always visible).
  - `EducationVerificationFormula` exists but is a child of the **inactive** `PSVSummary` step (show: `IsRecredentialing = false`).
  - **Required change:** Add a new `EducationVerificationFormula` element as a child of the **active** `ReCredPSVSummary` step:
    - Type: Formula
    - Expression: `%EducationVerificationOutcome%`
    - Label: `Education Verification`
    - Show condition: `CaseManager:PRM_ReCredToInitialCredConversion__c = true` (only display for conversion cases)
  - This ensures conversion ReCred cases see their Education outcome in the QC summary.

- **Inactive steps (no change required):**
  - `PSVSummary` (inactive in RecredQC) already has `EducationVerificationFormula`.
  - `QCReviewSummary` (inactive, label "Initial Cred QC Summary") shown only for `CaseType = QC Review`.

**Submission updates (when answer = Yes)**
- In ReCred submit/update payload (`RecordsToUpdate.IndividualApplication`), set:
  - `PRM_ReCredToInitialCredConversion__c = true`
- Apply this mapping in the PSV guided flow save paths in `PRM_PrimarySourceVerificationReview_English`:
  - `SetRecordPSVQC`
  - `SetRecordReCredPSV`
  - and ensure payload continues through `IPUpdatePSVReviewUpdate`
- If answer = No, set checkbox false (or leave unchanged per final business rule; default recommendation is explicit false for determinism).

**Compact layout / header behavior**
- Requirement: do not show Record Type for conversion cases; show label `Type - Initial Cred`.
- Implementation note:
  - Standard Compact Layout is not conditional by record value; use display-field strategy.
  - Create display formula field (example): `PRM_DisplayType__c`
    - Formula: `IF(PRM_ReCredToInitialCredConversion__c, "Initial Cred", TEXT(RecordType.Name))`
  - Replace Record Type in compact/highlighted display with `PRM_DisplayType__c`.
  - UI label displayed to users should be `Type`.

**Person Education Duplicate Handling (US-2 & US-3)**

- **Display configuration:** Two tables for Person Education records.
  - **Table 1 (Editable - System Records):** Displays existing system Person Education records with `PRM_IsErrorRecord__c` checkbox to mark duplicates. Business can edit/add new records here.
  - **Table 2 (Read-only - CAQH Data):** Displays CAQH Person Education reference data for verification purposes. No editing/saving allowed on this table (reference only).
  
- **Duplicate detection rules:**
  - **Rule 1 (System vs System):** Check if new system Person Education record `Institution`, `Degree`, and `GraduationDate` match any existing record in Table 1 (system records).
  - **Rule 2 (System vs CAQH):** Check if system record matches any record in Table 2 (CAQH reference data).
  - **Condition:** If duplicate detected (either rule), highlight duplicate record in Table 1 and apply error state.
  
- **Error checkbox on Person Education object (Table 1 only):**
  - **Field API Name:** `PRM_IsErrorRecord__c`
  - **Field Type:** Checkbox
  - **Purpose:** Business marks system records identified as duplicates to exclude/suppress them during PSV/QC processing.
  - **Usage:** When business identifies a system record (Table 1) as a duplicate (vs. system or CAQH), they check this box to mark it for exclusion.

- **Duplicate prevention (add new record to Table 1):**
  - **Button label:** `Add Person Education` (on Table 1)
  - **Button state:** Disabled when:
    - New entry matches any existing record in Table 1 (system vs system duplicate).
    - New entry matches any record in Table 2 (system vs CAQH duplicate).
    - Required fields (Institution, Degree, GraduationDate) are incomplete.
  - **UI indication:** Button appears greyed/disabled with tooltip showing reason.

- **Error messages:**
  - **For Table 1 vs Table 1 duplicates (system records):**
    ```
    Error: This Person Education record already exists in system records.
    Institution: [Institution]
    Degree: [Degree]
    Graduation Date: [GraduationDate]
    
    Action: Check PRM_IsErrorRecord__c on the duplicate system record to mark for exclusion, or remove this entry before submitting PSV/QC.
    ```
  
  - **For Table 1 vs Table 2 duplicates (system vs CAQH):**
    ```
    Error: This Person Education record matches existing CAQH data.
    Institution: [Institution]
    Degree: [Degree]
    Graduation Date: [GraduationDate]
    
    Action: Record already verified in CAQH. Check PRM_IsErrorRecord__c to exclude this system record, or remove duplicate entry before submitting PSV/QC.
    ```
  
  - **For validation failures (incomplete fields):**
    ```
    Error: Required fields missing.
    Please complete the following fields before adding new Person Education record to system:
    - Institution
    - Degree
    - Graduation Date
    ```

- **UI behavior on duplicate detection:**
  - Row highlight: Apply warning/error background color (light red/orange) to duplicate row in Table 1 only.
  - Button state: Disable `Add Person Education` button until duplicates are resolved.
  - Inline message: Display error message in-line with duplicate row in Table 1, above button.
  - Tooltip: Hover tooltip on disabled button shows which duplicate rule was triggered.
  - Table 2 (CAQH): No highlighting or error indicators (read-only reference table).

- **PSV/QC submission validation:**
  - **Pre-submission check 1 (duplicates):** Do not allow PSV/QC submit if unresolved Person Education duplicates exist in Table 1.
  - **Resolution options:**
    1. Remove duplicate entry from Table 1 (system records).
    2. Check `PRM_IsErrorRecord__c` on Table 1 record identified as duplicate to mark for exclusion.
  - **Block submission message (duplicates):**
    ```
    Cannot submit PSV/QC: Person Education duplicates detected in system records.
    
    Resolution:
    1. Remove duplicate entries from Table 1 (system records), OR
    2. Check PRM_IsErrorRecord__c on duplicate system records to exclude them from processing.
    
    CAQH data (Table 2) is reference-only and will not be saved/updated.
    Please resolve all duplicate conflicts before resubmitting.
    ```
  - **Pre-submission check 2 (minimum valid records):** Do not allow PSV/QC submit if all Person Education records in Table 1 are marked as error (`PRM_IsErrorRecord__c = true`). At least one non-errored record is required.
  - **Block submission message (no valid records):**
    ```
    Cannot submit PSV/QC: No valid Person Education records.
    
    At least one Person Education record must have PRM_IsErrorRecord__c unchecked.
    Please review and uncheck at least one record before resubmitting.
    ```

- **Minimum one valid record rule (AC9):**
  - **Rule:** At least one Person Education record in Table 1 (system records) must remain with `PRM_IsErrorRecord__c = false`.
  - **Behavior:** If user attempts to check `PRM_IsErrorRecord__c` on the last remaining non-errored record, the action is blocked.
  - **Disable logic:** When only one non-errored record remains, disable the `PRM_IsErrorRecord__c` checkbox on that row (greyed out, non-clickable).
  - **Validation formula (recommended):** `COUNT(PersonEducation WHERE PRM_IsErrorRecord__c = false) >= 1`
  - **Error message (if all errored via edge case):**
    ```
    Error: At least one valid Person Education record is required.
    
    All Person Education records cannot be marked as error.
    Please uncheck PRM_IsErrorRecord__c on at least one record to proceed.
    ```
  - **Submission block:** PSV/QC submit is blocked if zero valid (non-errored) Person Education records exist.
  - **Submission error message:**
    ```
    Cannot submit PSV/QC: No valid Person Education records.
    
    At least one Person Education record must have PRM_IsErrorRecord__c unchecked.
    Please review and uncheck at least one record before resubmitting.
    ```

- **Data persistence:**
  - **Save behavior:** Only Table 1 (system records) are saved/updated on PSV/QC submit.
  - **Table 2 (CAQH):** Read-only reference data, no save/update operations.
  - **Marked records:** Records with `PRM_IsErrorRecord__c = true` are flagged but not deleted; they remain for audit trail.

### US-3: QC routes flagged conversions to Initial Cred committee
As a QC reviewer, I want flagged conversion cases to route to Initial Cred committee review so that they are adjudicated under the initial credentialing framework.

**Acceptance Criteria**
- For flagged cases, QC submit creates/updates work item in Initial Cred committee lane.
- ReCred-specific committee path is bypassed for flagged cases.
- Case status/stage values reflect conversion route.

**ReCredQC OS condition update (Person Education visibility)**
- **OmniScript:** `PRM_RecredQC_English`
- **Step:** `EducationVerification` (currently configured with `IsRecredentialing = false`)
- **Required update for conversion use case:**
  - Extend `EducationVerification` `show` logic to display when `CaseManager:PRM_ReCredToInitialCredConversion__c = true`.
  - Preserve existing OR group for `WorkHistoryVerification` / `ReCredWHVerification` / `CaseType = QC Review`.
  - This keeps current behavior intact and additionally enables Person Education for conversion-flagged ReCred records.

**Committee Review submission mapping (current state)**
- User action: `ReCredProceedTo = "Committee Review"` in ReCred QC summary.
- Active submit element used: `SetRecordRecredQC_CR` (shown only when `ReCredProceedTo = Committee Review`).
- `SetRecordRecredQC_CR` currently sets:
  - `Case.Status = "Closed"` on current case
  - `IndividualApplication.PRM_RoutineCommittee__c = true`
  - `IndividualApplication.PRM_Stage__c = "Committee Review"`
  - `IndividualApplication.Status = "In Progress"`
  - `IndividualApplication.MedicalDirectorReview = null` (unless MDR route)
  - `IndividualApplication.PRM_RecredTerm__c = null` (unless final development route)
  - `ContentNote.title = "Recred QC to Committee Review"`
- Persistence path:
  - `IPUpdateRecredReviewUpdate` sends `RecordsToUpdate` to `PRM_ReviewRecredCaseRecordsUpdateParent`.

**Important implementation note**
- `SetQCReadyForCommittee` and `SetQCReadyForMedicalReview` exist but are currently inactive (`IsActive = false`) in this OS.
- Current routing on submit is driven by `SetRecordRecredQC_*` + `IPUpdateRecredReviewUpdate`, not by `SetQCReady*` elements.

**US-3 enhancement for conversion**
- In `SetRecordRecredQC_CR` add mapping:
  - `IndividualApplication.PRM_ReCredToInitialCredConversion__c = CaseManager:PRM_ReCredToInitialCredConversion__c`
- If conversion flag is true, route to Initial Cred committee intake path (via committee assignment logic) while retaining existing ReCred commit updates above.

### US-4: Committee sees and processes conversion context
As a committee reviewer, I want to clearly see conversion context in committee review so that I can make decisions with full business context.

**Acceptance Criteria**
- Conversion indicator is visible in committee UI and record data.
- Committee report/list includes conversion marker.
- For rows where `PRM_ReCredToInitialCredConversion__c = true`, deny is not available; users can only `Approve` or `Remove`.
- For rows where `PRM_ReCredToInitialCredConversion__c = false`, existing `Approve/Remove/Deny` behavior remains unchanged.
- In `ReviewInitialCredApplicants` committee report, keep existing Initial Cred practitioners and also include ReCred practitioners when `CaseManager.PRM_ReCredToInitialCredConversion__c = true`.
- In ReCred committee report, only ReCred practitioners with `CaseManager.PRM_ReCredToInitialCredConversion__c = false` are included.

**Current implementation baseline (confirmed)**
- OmniScript: `PRM_ReviewInitialCredApplicants_English`
- Header context is currently set by `SetValues2`:
  - `recordTypeDeveloperName = PRM_PractitionerParticipationRequest` -> "Routine Credentialing Committee Report"
  - otherwise -> "Routine Re-Credentialing Committee Report"
- Data load comes from:
  - `PRM_ReviewInitialCredApplicantsIP` -> IP `PRM_ReviewInitialCredApplicants`
  - IP element `GetRelatedRecordForPractitioner` (DR extract bundle `PRMGetRelatedRecordForPractitioner`)
  - current input filters passed: `CaseRecTypeName`, `CaseStage = "Committee Review"`
- Current mapping does not include conversion-flag filtering.

**Required filter criteria updates**
- Update DR/IP query logic in `PRMGetRelatedRecordForPractitioner` (or equivalent IP filter layer) to apply conditional conversion filters:
  1. **Initial Cred Committee Report context**  
     Include:
     - Initial Cred practitioners (existing behavior), and
     - ReCred practitioners when `PRM_ReCredToInitialCredConversion__c = true`.
  2. **ReCred Committee Report context**  
     Include:
     - ReCred practitioners only when `PRM_ReCredToInitialCredConversion__c = false`.
- Keep common criteria unchanged (example: committee stage/status criteria already in use).

**Implementation guidance**
- Add conversion flag to the output payload consumed by `RoutineCredCommitteeTable` so users can see/filter by it.
- Use `recordTypeDeveloperName` (already available in OS context) to drive which conversion-filter mode applies.
- Keep existing approve/remove processing paths, but add conversion-aware deny suppression (UI + server validation) for `conversion=true`.

**Denied/Remove handling (updated requirement)**
- For records shown in `ReviewInitialCredApplicants` where `PRM_ReCredToInitialCredConversion__c = true`, deny is disabled/hidden and must be rejected server-side if passed in payload.
- For records where `PRM_ReCredToInitialCredConversion__c = true`, remove follows the existing `UpdateRemoved` (`PRMUpdateRemovedCaseOnCSManager`) path unless business requests a different terminal state.
- For records where `PRM_ReCredToInitialCredConversion__c = false`, keep current Initial Cred Deny/Remove behavior.

**Current behavior comparison (confirmed)**
- **Initial Cred committee report (`PRM_ReviewInitialCredApplicants_English`)**
  - **Remove path:** `ReviewInitialCredAppListAssignment` -> `PRM_ReviewInitialCredAppListAssignment` -> `UpdateRemoved` (bundle `PRMUpdateRemovedCaseOnCSManager`) on `RemovedCMs`.
  - **Deny path:** `DenialLogic` -> `PRM_CommitteeReviewDenial` -> remote action `PRM_PARRequestDenialUtility.CommitteeReviewDenial` on `NotApprovedRecords` (`Approve == false`).
- **ReCred committee report path (`PRM_NonRoutineCommitteeReview_English`)**
  - Denied/Appeal/outreach statuses update via `SVNRCommitteeDeniedClosed`, `SVNRCommitteeDeniedAppealOpen`, `SVNRCommitteeAppealed`, etc.
  - Example denied-closed updates include:
    - `Case.Status = Closed`
    - `IndividualApplication.Status = Denied`
    - `IndividualApplication.PRM_Stage__c = Complete`
    - `IndividualApplication.PRM_DenialReason__c` and `DecisionDate`
  - Additional denial remote action exists: `NRCommitteeDeniedClosed` -> `PRM_PARRequestDenialUtility.NonCommitteeReviewDenial`.

**Required technical branching**
- In committee table payload, pass `PRM_ReCredToInitialCredConversion__c` (or mapped flag) for each row.
- In `PRM_ReviewInitialCredAppListAssignment`, split decision handling by conversion flag:
  - `conversion = true` -> allow `Approve` and `Remove` only.
  - `conversion = false` -> keep existing `Approve`/`Remove` processing.
- In `PRM_CommitteeReviewDenial` (and caller `DenialLogic`), add guard:
  - if `conversion = true`, do not process denial; return validation error/message to UI.
  - if `conversion = false`, keep existing denial path.
- Preserve existing approve routing split behavior already present in assignment IP (`ApprovedCMsReCredTrue` / `ApprovedCMsReCredFalse`) and align it to `PRM_ReCredToInitialCredConversion__c`.

**Technical spec: exact updates for Removed (conversion=true)**

1. **Detection logic (shared)**
- Source row context: `RoutingCredentialCommitteeReport:RoutineCredCommitteeTable`
- Use this field per selected row: `PRM_ReCredToInitialCredConversion__c` (or mapped `RecredPDA` replacement)
- Route branch:
  - `conversion = true` and `Remove = true` -> **Removed**
  - `conversion = true` and `Approve = false` and `Remove = false` -> **Blocked (deny not allowed)**
  - `conversion = false` and `Approve = false` and `Remove = false` -> **Denied** (existing path)

2. **Removed outcome (conversion=true)**
- Use existing remove implementation in `PRM_ReviewInitialCredAppListAssignment`:
  - `SetMerge:RemovedCMs = FILTER(..., 'Remove == true')`
  - `UpdateRemoved` calls bundle `PRMUpdateRemovedCaseOnCSManager` with `sendJSONPath = SetMerge`
- Update the following records:
  - **IndividualApplication (Case Manager)**
    - `Id = RemovedCMs:CaseManagerRecordId`
    - `OwnerId = RemovedCMs:CommFinalDevQueueId`
    - `PRM_Stage__c = "Committee Review"`
    - `Status = "Additional Review Needed"`
    - keep `PRM_ReCredToInitialCredConversion__c = true`
  - **Case**
    - no direct Case field update is configured in `PRMUpdateRemovedCaseOnCSManager`.
- Implementation points:
  - UI: hide/disable deny controls when `PRM_ReCredToInitialCredConversion__c = true`.
  - Server-side: reject denied payload rows for `conversion=true` before invoking `PRM_CommitteeReviewDenial`.

3. **No-regression branch (conversion=false)**
- Keep current Initial Cred logic unchanged:
  - Denied via `PRM_CommitteeReviewDenial` existing behavior
  - Removed via `UpdateRemoved` existing behavior

4. **Audit and data integrity requirements**
- For Removed (conversion=true):
  - do not clear `PRM_ReCredToInitialCredConversion__c`
  - preserve existing remove-path audit trail
  - preserve attachment links and prior PSV/QC outcomes

5. **Test matrix (minimum)**
- conversion=true + deny attempt -> verify action is blocked in UI and rejected server-side.
- conversion=true + removed -> verify `IndividualApplication.Id`, `OwnerId`, `PRM_Stage__c`, `Status` updated as specified above.
- conversion=false + Denied/Removed -> verify no change from current production behavior.

### US-7: Communication / Notification Review for Conversion Cases

As a credentialing operations team, we need to confirm whether any practitioner or internal communications are required when a ReCred case is converted to Initial Cred, so that affected parties are informed and audit requirements are met.

> **STATUS: Pending business confirmation** -- discuss with business whether any of the below communications should fire for conversion cases.

**Existing communications discovered in codebase:**

| # | Communication | Type | Recipient | Trigger / Stage | Mechanism |
|---|---|---|---|---|---|
| 1 | **ReCred Final Notice Email** | Email (SendGrid) | Practitioner | CAQH validation during Application Review (`PRM_ValidateCAQHAppReview` IP) | SendGrid API via `PRM_sendGridNotifications` IP. IBC template: `PRM_SendGridRecredTemplateIBC`, AH template: `PRM_SendGridRecredTemplateAH`. Subject: "Recredentialing". From: `Recredentialing@mail9.ibx.com`. Content: "Final Notice -- failure to respond will result in voluntary withdrawal from network(s)." Warns of 10 business day deadline. |
| 2 | **ReCred Due Date Monthly Email** | Email (SendGrid) | Practitioner | Scheduled batch `PRM_RecredSendEmailOnDueAccountsBatch` (runs 1st of each month for practitioners where `PRM_IsReCredDue__c = true`) | Calls `PRM_ValidateCAQHAppReview` IP -> same SendGrid flow as #1. |
| 3 | **Welcome Letter** (Initial Cred) | Physical letter (`PRM_Letter__c`, RecordType `PRM_Welcome`) | Practitioner | Batch `PRM_LetterWelcomeBatch` -- picks up `IndividualApplication` where `RecordType = PRM_PractitionerParticipationRequest`, `Category = Credentialing`, `PRM_Stage__c IN ('PDA Review And Update', 'Network Management QC', 'Complete')`, `Status = 'Approved'`, and `PRM_AsyncProcess__c = NULL`. | Creates `PRM_Letter__c` records with practitioner name, NPI, practice location, mailing address, taxonomy, Tax ID, effective date, case number, and letterhead key (IBC vs AH based on `PRM_LetterheadIndicator__c`). |
| 4 | **ReCred Termination Letter** | Physical letter (`PRM_Letter__c`, RecordType `PRM_Termination`) | Practitioner | RCAT processing via `PRM_ReviewRCATLoad` IP -> `PRM_RecredTerminationLetterParent` IP | Generated during RCAT batch processing for practitioners terminated due to non-compliance. |
| 5 | **CMS Preclusion Letter** | Physical letter (`PRM_Letter__c`, RecordType `PRM_Preclusion`) | Practitioner/Facility | Salesforce Flow -> `PRM_FlowCMSPreclusionLetter` Apex `@InvocableMethod` | Creates Case (PDA Termination type) + IndividualApplication + Letter records. |
| 6 | **Ancillary Reassessment Email** | Email (SendGrid) | Ancillary provider | Manual trigger from `PRM_AncillaryReassessmentApplicationEmail_English` OS | Not relevant to practitioner credentialing. |
| 7 | **Internal Bell Notifications** | In-app notification | Internal users / queue members | Various processes via `PRM_NotificationHelper.sendBellNotification()` | Salesforce `Messaging.CustomNotification` API. |
| 8 | **Internal Email with CSV** | Email (native SF) | Internal users / queue members | Various processes via `PRM_NotificationHelper.sendEmailNotification()` | `Messaging.SingleEmailMessage` with CSV attachment. |

**Conversion impact analysis:**

| Communication | Impact for Conversion Cases | Action Needed? |
|---|---|---|
| **ReCred Final Notice Email (#1, #2)** | Conversion cases still go through ReCred PSV, so the CAQH validation may still fire. However, the email subject and body reference "Recredentialing" -- for a conversion case, this could be confusing. | **Ask business:** Should conversion cases be excluded from ReCred Final Notice emails, or should a modified version be sent? |
| **Welcome Letter (#3)** | The batch queries `RecordType = PRM_PractitionerParticipationRequest` (Initial Cred). Conversion cases have a ReCred record type (`PRM_ReCredentialing`), so they will **not** be picked up by the current Welcome Letter batch. | **Ask business:** Should conversion cases generate a Welcome Letter after PDA/QC completion? If yes, the batch query needs to be updated to include ReCred record types where `PRM_ReCredToInitialCredConversion__c = true`. |
| **ReCred Termination Letter (#4)** | Only generated via RCAT. Conversion cases are not routed to RCAT (deny is disabled per US-4). Remove path returns case to `Additional Review Needed`, not termination. | **No change needed.** |
| **Internal Notifications (#7, #8)** | Bell notifications and CSV emails are utility-based. No specific conversion triggers exist today. | **Ask business:** Should an internal bell notification alert the committee or PDA queue that a conversion case has arrived? |

**Decision points for business:**

1. **Should conversion practitioners receive a notification email when their case is converted?** (i.e., at the PSV stage when the specialist marks the case as out-of-compliance/conversion)
2. **Should conversion practitioners receive a Welcome Letter upon approval?** (Welcome Letter batch currently excludes ReCred record types)
3. **Should the existing ReCred Final Notice email be suppressed or modified for conversion cases?**
4. **Should internal users receive a bell notification when a conversion case enters the committee queue or PDA queue?**

**Draft email: Conversion Notification to Practitioner (for business review)**

If business decides a notification email should be sent to the practitioner when the case is converted, below is a draft for both IBC and AmeriHealth brands. This would be sent via SendGrid, following the same pattern as the existing ReCred email (`PRM_sendGridNotifications` IP).

- **Trigger:** PSV submission when `ReCredInitialCredConversionAnswer = "Yes"` (or after committee approval -- per business preference)
- **SendGrid type:** `sendGridConversion` (new conditional block in `PRM_sendGridNotifications`)
- **Template constants:** `PRM_SendGridConversionTemplateIBC`, `PRM_SendGridConversionTemplateAH`
- **From:** `Credentialing@mail9.ibx.com` (fromName: `IBCNoReply`)
- **Subject:** `Important Update Regarding Your Credentialing Status`

**IBC version:**

```
Subject: Important Update Regarding Your Credentialing Status

Dear Health Care Professional,

Independence Blue Cross (Independence) is writing to inform you that your
recredentialing application is being reviewed under our initial credentialing
process due to updated compliance requirements.

What this means for you:
- Your application is being processed through our initial credentialing review,
  which includes committee review and provider data verification.
- No additional action is required from you at this time.
- Your current network participation status remains unchanged during this review.

What to expect next:
Your application will be reviewed by our credentialing committee. Upon approval,
you will proceed through our standard provider data review and quality check
process. You will be notified of the final outcome.

If you have any questions about the status of your application, please contact
the Credentialing Department at credops@ibx.com or via fax at 215-238-2549.

Sincerely,
Credentialing Operations
Independence Blue Cross
```

**AmeriHealth version:**

```
Subject: Important Update Regarding Your Credentialing Status

Dear Health Care Professional,

AmeriHealth HMO, Inc. and AmeriHealth Insurance Company of New Jersey
(collectively, AmeriHealth New Jersey) are writing to inform you that your
recredentialing application is being reviewed under our initial credentialing
process due to updated compliance requirements.

What this means for you:
- Your application is being processed through our initial credentialing review,
  which includes committee review and provider data verification.
- No additional action is required from you at this time.
- Your current network participation status remains unchanged during this review.

What to expect next:
Your application will be reviewed by our credentialing committee. Upon approval,
you will proceed through our standard provider data review and quality check
process. You will be notified of the final outcome.

If you have any questions about the status of your application, please contact
the Credentialing Department at credops@amerihealth.com or via fax at
215-238-2549.

Sincerely,
Credentialing Operations
AmeriHealth New Jersey
```

**Technical implementation (if email is approved by business):**

1. **New SendGrid templates:**
   - Create `PRM_SendGridConversionTemplateIBC` and `PRM_SendGridConversionTemplateAH` in `PRM_SendgridTemplateIds__c` custom setting.
   - Register corresponding SendGrid dynamic templates.

2. **IP changes (`PRM_sendGridNotifications`):**
   - Add new conditional block `SendGridConversionBlock` (condition: `sendGridType == "sendGridConversion"`).
   - Add `SetRequestBodyConversion` Set Values element with IBC/AH HTML content.
   - Add `CalloutSendGridConversionIBC` / `CalloutSendGridConversionAH` HTTP Action elements.

3. **Trigger point:**
   - Option A: Fire from PSV submission IP (`IPUpdatePSVReviewUpdate`) when `PRM_ReCredToInitialCredConversion__c = true`.
   - Option B: Fire from committee approval IP (`PRM_ReviewInitialCredAppListAssignment`) when `conversion = true` and `Approve = true`.
   - Business to confirm preferred trigger point.

4. **Welcome Letter batch update (if approved):**
   - Modify `PRM_LetterWelcomeBatch.start()` query to include:
     ```
     OR (PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_ReCredentialing'
         AND PRM_CaseManager__r.PRM_ReCredToInitialCredConversion__c = true)
     ```
   - Adjust letter record type: use `PRM_Welcome` (same as Initial Cred) for conversion cases.

### US-5: Approved conversions continue through Initial Cred PDA + QC
As an operations user, I want approved conversion cases to proceed to Initial Cred PDA and Network Mgmt QC so that final provider network updates use existing Initial Cred controls.

**Acceptance Criteria**
- Committee approval creates/reroutes to Initial Cred PDA step.
- PDA completion sends case to Initial Cred Network Mgmt QC.
- Existing return/rebuttal/error paths remain active.

**Routing truth table (current implementation baseline)**

| Stage | Decision/Condition | Routing result today |
|---|---|---|
| PSV (`PRM_PrimarySourceVerificationReview_English`) | ReCred path in `SetRecordReCredPSV` (`ReCredProceedTo = Re-Cred PSV QC` or `Medical Director Review`) | Routes to QC lane (`IndividualApplication.PRM_Stage__c = QC Review`, `NewCase.Type = QC Review`) |
| ReCred QC (`PRM_RecredQC_English`) | `ReCredProceedTo = Committee Review` (`SetRecordRecredQC_CR`) | Sets case manager to committee review (`PRM_Stage__c = Committee Review`, `Status = In Progress`, `PRM_RoutineCommittee__c = true`) |
| ReCred QC (`PRM_RecredQC_English`) | `ReCredProceedTo = Medical Director Review` (`SetRecordRecredQC_MDR`) | Sets stage committee review and creates new committee review case |
| ReCred QC (`PRM_RecredQC_English`) | `ReCredProceedTo = Route to Final Development` (`SetRecordRecredQC_FD`) | Marks recred term/final-development style close path; no direct PDA case creation here |
| ReCred QC (`PRM_RecredQC_English`) | `ReCredProceedTo = Route to PSV` (`SetRecordRecredQCReturnToPSV`) | Returns to PSV with new PSV case |
| Non-routine Committee (`PRM_NonRoutineCommitteeReview_English`) | `CaseStatusRecred/CaseStatus = Nonroutine Committee Approved` (`SVNRCommitteeApproved` or `SVForNCApprovedCredTrue`) and `CaseManager.RCDeveloperName = PRM_ReCredentialing` | **Routes to ReCred PDA lane** by setting `IndividualApplication.PRM_Stage__c = Recred Updates` and creating `NewCase.Type = Recred Updates` (owner `PRM_PDAInitialCredQueue`) |
| Non-routine Committee (`PRM_NonRoutineCommitteeReview_English`) | `CaseStatusRecred/CaseStatus = Nonroutine Committee Pend - Provider Outreach` (`SVNRCommitteePenProviderOutreach`) | Sets current case `Status = Provider Outreach`; no ReCred Updates/PDA case created at this step |

**Answer to "when do we route ReCred to ReCred PDA?"**
- ReCred cases are routed to ReCred PDA lane at **committee approved** outcome in `PRM_NonRoutineCommitteeReview_English` (not directly from PSV or ReCred QC submit).

### US-6: Case Manager layout supports conversion transparency
As a case manager user, I want conversion-related fields and milestones visible on the Case Manager page so that I can monitor and report conversion progress.

**Acceptance Criteria**
- New conversion fields are visible in Case Manager layout.
- Routing milestone/status fields clearly distinguish conversion from standard ReCred.
- List views/reports can filter conversion cases.

---

## Technical Change Plan (developers)

## 1) Data model and routing flags

### US-DM-1: Person Education Error Record Field (Checkbox on PersonEducation object)

**User Story:**
As a PSV/QC specialist, I want to mark duplicate Person Education records with an error flag so that the system can suppress/exclude them from processing during PSV and QC review.

**Acceptance Criteria:**
- New checkbox field `PRM_IsErrorRecord__c` exists on PersonEducation object.
- Field is visible in Person Education table views in PSV/QC OmniScripts.
- Business can mark system records as duplicates to suppress them.
- Field supports audit trail for traceability.
- Field behavior matches existing `PRM_IsErrorRecord__c` implementation on HealthcareFacility object.

**Field Specification:**

| Property | Value |
|---|---|
| **API Name** | `PRM_IsErrorRecord__c` |
| **Label** | `Error Record` |
| **Field Type** | Checkbox |
| **Default Value** | `false` |
| **Required** | No |
| **Track Field History** | Yes |
| **Help Text** | "Check to mark this record as an error/duplicate for exclusion from processing." |
| **Description** | "Checkbox to identify and suppress duplicate or error Person Education records during PSV/QC verification." |
| **Object** | `PersonEducation` |

**Build Specification:**

1. Create field metadata file: `PersonEducation.object` → add `PRM_IsErrorRecord__c` field
2. Metadata XML format (similar to HealthcareFacility):
   ```xml
   <CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
       <fullName>PRM_IsErrorRecord__c</fullName>
       <defaultValue>false</defaultValue>
       <description>Checkbox to identify and suppress duplicate or error Person Education records during PSV/QC verification.</description>
       <externalId>false</externalId>
       <label>Error Record</label>
       <required>false</required>
       <trackHistory>true</trackHistory>
       <type>Checkbox</type>
   </CustomField>
   ```

3. Add to page layouts:
   - Person Education record page layout (if exists)
   - Include in Person Education table columns visible in PSV/QC OmniScripts

4. Security/Permissions:
   - Grant Read + Update permissions on field to PSV specialist profiles
   - Grant Read-only to other viewer roles

**Implementation Notes:**
- Field implementation mirrors existing `PRM_IsErrorRecord__c` on HealthcareFacility object for consistency
- Track field history enabled for audit trail of which records were marked as errors and when
- Used in conjunction with Table 1 (System Records) in Person Education Duplicate Handling logic
- No custom validation or triggers initially; manual business marking

**Test Scenarios:**
- Create PersonEducation record and mark `PRM_IsErrorRecord__c = true`
- Verify field persists on update
- Verify field history captures changes
- Verify field is visible in PSV/QC Person Education table views
- Confirm duplicate detection logic respects this flag during submission validation

---

### Other data model fields

Add/confirm fields (proposed names; align with org naming standards):
- `PRM_ReCredToInitialCredConversion__c` (Checkbox/Picklist) on Case Manager (or controlling object used by OmniScripts).
- `PRM_ConversionReason__c` (Picklist: Conversion, OutOfCompliance, Other if needed).
- `PRM_ConversionRoutedToInitialCommittee__c` (Checkbox).
- Optional timestamp/user fields for audit.

Update status model mappings:
- keep existing ReCred statuses for PSV/QC steps.
- add mapping for conversion route at committee handoff.

## 2) ReCred OmniScript updates (`PRM_RecredQC_English`)

Add new control in first PSV section:
- Add required Radio/Select in first PSV step (near first PSV block elements).
- Persist answer into `RecordsToUpdate`.

Adjust routing logic:
- Update `ReCredProceedTo` and/or `QCProceedTo` logic to account for conversion flag.
- Update `SetRecordRecredQC_CR`, `SetRecordRecredQC_MDR`, `SetRecordRecredQC_FD`, and/or add new set-values element for conversion-specific routing.
- Ensure `IPUpdateRecredReviewUpdate` payload includes new conversion fields.

Decision behavior:
- If conversion flag = true, route to Initial Cred committee pipeline.
- If false, keep current behavior.

## 3) ReCred update IP (`PRM_ReviewRecredCaseRecordsUpdateParent` + child IP)

- Extend request schema to accept conversion fields.
- Update child update logic to:
  - mark conversion flag on Case Manager/application.
  - create correct new case record type/type/status for Initial Cred committee path.
  - preserve existing behavior for non-conversion.
- Add exception handling and response payload fields for UI confirmations.

## 4) Initial Cred committee intake (`PRM_ReviewInitialCredApplicants_English`)

- Ensure conversion-routed records appear in committee table (`RoutineCredCommitteeTable` data source and backing IP).
- Show conversion indicator column in table/edit block.
- Validate `ReviewInitialCredAppListAssignment` IP handles conversion records correctly and routes to initial PDA path.

## 5) Committee assignment IP (`PRM_ReviewInitialCredAppListAssignment`)

- Confirm/extend branch elements:
  - `ApprovedCaseReCredRecType` / `ReCredUpdateTrue/False` branches currently indicate mixed logic already exists.
- Normalize conversion branch:
  - when conversion flag true, force initial credentialing downstream transitions (PDA expected path).
  - keep legacy ReCred committee outcomes untouched for non-conversion.

## 6) Initial Cred PDA (`PRM_InitialCredPDA_English`)

- Validate fetch IP (`PRM_FetchFormPDAReviewParent`) resolves conversion-routed records.
- Add read-only conversion banner/field in practitioner info block.
- Ensure `IPInitialCredPDARecordsUpdate` sets next step to Network Mgmt QC for conversion path.

## 7) Initial Cred Network Mgmt QC (`PRM_InitialCredPDAQC_English`)

- Confirm conversion-routed cases are selectable and processed.
- Add conversion indicator in QC summary/header.
- Validate existing outcome branches (`SetRecordsQCCompleted`, `SetRecordsNtwlMgntQC`, return/rebuttal paths) for conversion cases.

## 8) Non-routine committee (`PRM_NonRoutineCommitteeReview_English`) impact

- No mandatory direct change if conversion path bypasses non-routine committee.
- Add guardrail to prevent flagged conversion cases from entering non-routine path unintentionally.

## 9) Case Manager page/layout and UX

Update in org metadata:
- page layout sections for conversion fields.
- dynamic forms/highlights panel for conversion badge.
- related list/list view filters for conversion queue.
- quick actions/buttons visibility rules if needed.

Repo note:
- `layouts` metadata is not included in this repo export; coordinate with Salesforce metadata owner for retrieval and versioning.

## 10) Reporting and audit

- Update operational reports for:
  - conversion volume,
  - turnaround by stage (PSV, QC, Committee, PDA, Ntwk QC),
  - out-of-compliance reason trends.

---

## Component-by-Component Change Matrix

| Component | Current Implementation | Required Change |
|---|---|---|
| `PRM_RecredQC_English` (OmniScript) | ReCred PSV/QC with routing options and updates via `IPUpdateRecredReviewUpdate` | Add conversion question in first PSV step; persist flag; branch routing to Initial Cred committee path |
| `ReCredProceedTo` + `QCProceedTo` elements | Route to committee/MDR/final development/return | Add conversion-aware decision rules (override/conditional routing) |
| `SetRecordRecredQC_*` elements | Update IA/case status and notes for existing ReCred outcomes | Extend/add set-values for conversion stage/status and downstream initial-committee targeting |
| `IPUpdateRecredReviewUpdate` | Sends `RecordsToUpdate` to `PRM_ReviewRecredCaseRecordsUpdateParent` | Include conversion fields and conversion routing payload |
| `PRM_ReviewRecredCaseRecordsUpdateParent` IP | Parent wrapper with try/catch for ReCred updates | Extend child update contract and branching for conversion creation/routing |
| `PRM_NonRoutineCommitteeReview_English` | Non-routine committee statuses including ReCred branch (`CaseStatusRecred`) | Optional guardrails so conversion cases do not incorrectly enter this flow |
| `PRM_ReviewInitialCredApplicants_English` | Initial committee review table + assignment/denial IP actions | Include conversion-routed records and conversion visual indicator |
| `PRM_ReviewInitialCredAppListAssignment` IP | Creates/updates cases from committee decisions; includes ReCred-related elements | Harden explicit conversion branch to PDA path and status updates |
| `PRM_InitialCredPDA_English` | Initial Cred PDA review/update and routing to next stage | Ensure compatibility with conversion-sourced records; display conversion context |
| `PRM_InitialCredPDAQC_English` | Network Mgmt QC outcomes for initial cred cases | Ensure conversion cases flow through standard QC completion and return paths |
| Case Manager page layout / dynamic form | Not represented in repo | Add conversion fields, indicators, and lifecycle visibility |
| Reports/List Views | Existing operational reporting likely not conversion-aware | Add conversion filter dimensions and SLA reporting |

---

## End-to-End Routing Rules (recommended)

- Rule A: If conversion question = No -> existing ReCred behavior.
- Rule B: If conversion question = Yes -> complete ReCred PSV/QC -> route to Initial Cred committee.
- Rule C: Initial committee Approved -> Initial Cred PDA.
- Rule D: Initial Cred PDA complete -> Initial Cred Network Mgmt QC.
- Rule E: Any return/rebuttal/error follows existing owning flow's current return logic (no custom branch unless gap found in SIT).

---

## Test Scenarios (minimum)

1. Non-conversion ReCred case remains unchanged.
2. Conversion case routes to initial committee after QC.
3. Conversion case visible in initial committee table.
4. Committee approve creates/updates PDA path correctly.
5. PDA completion routes to Network Mgmt QC.
6. Conversion case return from QC/committee preserves conversion flag.
7. Non-routine committee cannot pick up flagged conversion by mistake.
8. Case Manager layout displays conversion flag and stage transitions.

---

## Delivery Phasing

1. Data model + ReCred OmniScript question/routing payload.
2. ReCred update IP changes and unit validation.
3. Initial committee intake + assignment IP changes.
4. PDA/QC compatibility updates.
5. Case Manager layout + reporting.
6. SIT/UAT with conversion and non-conversion parallel regression.

