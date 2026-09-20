# Concierge Medicine - PAR Form Changes - User Stories

**Document Version:** 1.0
**Created Date:** April 1, 2026
**Related Documents:**
- Concierge_Medicine_User_Stories_InfoCode_Approach.md (Backend Info Code implementation)
- Concierge_Medicine_InfoCode_Flow_Impact_Analysis.md (Flow integration)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Form Changes Overview](#form-changes-overview)
3. [User Stories - PAR Form Updates](#user-stories---par-form-updates)
4. [Technical Mapping](#technical-mapping)
5. [Acceptance Testing](#acceptance-testing)

---

## Executive Summary

This document outlines user stories for **updating the Practitioner Participation Request (PAR) form** to capture concierge medicine information. These changes are **in addition to** the Info Code backend implementation documented in the main user stories.

### Key Changes

| Change Type | Description | Impact |
|-------------|-------------|--------|
| **Remove Questions** | Remove 2 existing generic fee questions | Simplify form |
| **Add New Questions** | Add concierge-specific questions for PCPs/Dual practitioners | Better data capture |
| **Conditional Logic** | Show "optional fee" question only if concierge = Yes | Improved UX |
| **Warning Message** | Add attestation reminder with provider manual links | Compliance |
| **Backend Integration** | Map form responses to Info Code Assignments | Data integration |

---

## Form Changes Overview

### Current State (To Be Removed)

**Location:** Practitioner Participation Request → Practitioner Screen

**Questions to Remove:**
1. ❌ *Do you require patients to pay a fee in order to be a patient of the practice or for additional services (e.g., concierge fees) beyond applicable member cost sharing?*
2. ❌ *Do you offer patients the options to pay a fee in order to receive enhanced services such as longer visit times, access to a physician's cell phone, priority scheduling, etc?*

**Reason for Removal:** Too generic; does not specifically capture concierge medicine practice.

---

### New State (To Be Added)

**Location:** Practitioner Participation Request → Practitioner Screen

**Conditional Display:** Only shown if `Practitioner Role = PCP` OR `Practitioner Role = Dual`

**Question 1 (Required):**
```
*(For PCPs only) Do you practice concierge medicine (or retainer medicine) by charging your
patients a concierge fee (or retainer) separate from the applicable patient cost sharing
(e.g., co-pays, deductibles, etc.)?

○ Yes
○ No
```

**Question 2 (Conditional - shown only if Question 1 = Yes):**
```
*Is your concierge fee for additional services optional to your patients?

○ Yes
○ No
```

**Warning Message (Always Shown for PCP/Dual):**
```
⚠️ Please ensure that you review and execute the concierge attestation form during your
credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and
Provider Attestation can be found within the Provider Manual located:
[IBX] | [AHNJ] | [AHPA]

Noncompliance with executing the concierge attestation may result in the delay or
rejection of your application.
```

**Hyperlinks:**
- **IBX:** https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx
- **AHNJ:** https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx
- **AHPA:** https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx

**Placement:** Above the question "*Are you joining an existing group?"

---

## User Stories - PAR Form Updates

### Epic 3: PAR Form Concierge Medicine Questions

**Epic Goal:** Update the Practitioner Participation Request form to capture concierge medicine information and create corresponding Info Code Assignments.

**Business Value:** Accurate capture of concierge medicine practice during credentialing; compliance with attestation requirements.

**Priority:** High
**Estimated Story Points:** 18

---

### Story 3.1: Remove Existing Generic Fee Questions from PAR Form

**As a** Form Designer
**I want** to remove the two existing generic fee questions from the Practitioner screen
**So that** we can replace them with more specific concierge medicine questions

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Questions Removed**
   - Question: "Do you require patients to pay a fee in order to be a patient of the practice or for additional services (e.g., concierge fees) beyond applicable member cost sharing?" is removed from Practitioner screen
   - Question: "Do you offer patients the options to pay a fee in order to receive enhanced services such as longer visit times, access to a physician's cell phone, priority scheduling, etc?" is removed from Practitioner screen
   - Removed questions do not appear in any PAR form views (create, edit, review)
   - Removed questions do not appear in any data collection or submission flows

2. **Backward Compatibility**
   - Existing PAR applications submitted before this change retain their responses to old questions (data not deleted)
   - Old responses are visible in historical records but not editable
   - Reporting/analytics can still access historical data for old questions

3. **OmniScript Elements**
   - OmniScript elements for removed questions are deleted or hidden (not just conditionally hidden)
   - Related validation rules for removed questions are disabled/removed
   - Navigation/step logic is updated (no broken flows)

4. **Testing**
   - New PAR form submissions do not show removed questions
   - Old PAR applications can still be viewed in read-only mode
   - No console errors or broken UI elements

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English` (or similar name)
- **Elements to Remove:** Identify element names for the two old fee questions (e.g., `RadioOldFeeQuestion1`, `RadioOldFeeQuestion2`)
- **DataRaptor Impact:** Verify if any DataRaptors reference these old fields; update mappings if needed
- **Integration Procedure Impact:** Verify if any IPs use these old fields; update or remove references
- **Data Model:** Old fields may exist on IndividualApplication or Account; decide if they should be deprecated or hidden

#### Dependencies

- Access to OmniScript designer
- Approval to remove questions (business sign-off)
- Coordination with reporting team (if reports use old questions)

#### Definition of Done

- [ ] Old questions removed from PAR form OmniScript
- [ ] Form renders correctly without errors
- [ ] Navigation flows work correctly
- [ ] Historical data remains accessible (if needed)
- [ ] Regression testing completed (form submission end-to-end)
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off from PDA team

---

### Story 3.2: Add Concierge Medicine Question for PCP/Dual Practitioners

**As a** PCP or Dual practitioner completing the PAR form
**I want** to answer whether I practice concierge medicine
**So that** the credentialing team accurately captures my practice model

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Question Display Logic**
   - New question is displayed ONLY when `Practitioner Role = PCP` OR `Practitioner Role = Dual`
   - Question is NOT displayed for other practitioner roles (e.g., Specialist, Behavioral Health, etc.)
   - Question is required (cannot proceed without answering)
   - Question appears on Practitioner screen before "*Are you joining an existing group?"

2. **Question Text and Format**
   - Question text exactly as specified:
     ```
     *(For PCPs only) Do you practice concierge medicine (or retainer medicine) by charging your
     patients a concierge fee (or retainer) separate from the applicable patient cost sharing
     (e.g., co-pays, deductibles, etc.)?
     ```
   - Radio button control with two options:
     - ○ Yes
     - ○ No
   - Asterisk (*) indicates required field
   - Help text (optional tooltip): "Concierge medicine is a membership-based healthcare model where patients pay a retainer fee for enhanced access and services."

3. **Response Capture**
   - User selection is saved to OmniScript data
   - Response is mapped to appropriate field/object (see Technical Mapping section)
   - Response is visible in form review/summary step
   - Response is persisted when form is saved (draft or submitted)

4. **Conditional Trigger for Next Question**
   - If user selects "Yes", the optional fee question (Story 3.3) is displayed immediately below
   - If user selects "No", the optional fee question is hidden
   - Changing answer from "Yes" to "No" hides the optional fee question and clears its response

5. **Validation**
   - Cannot submit form without answering this question (if PCP/Dual)
   - Error message if validation fails: "Please indicate whether you practice concierge medicine."
   - Validation occurs before form submission

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English`
- **Element Type:** Radio Button (OmniScript Element)
- **Element Name:** `RadioConciergeMedicine` (or similar)
- **Show Condition:** `%PractitionerRole% == 'PCP' OR %PractitionerRole% == 'Dual'` (verify exact picklist values)
- **Required:** Yes
- **Options:**
  - Label: "Yes", Value: "Yes"
  - Label: "No", Value: "No"
- **Data Mapping:** Map to custom field or use in Integration Procedure to create Info Code Assignment (see Story 3.5)

#### Dependencies

- Story 3.1 completed (old questions removed)
- Practitioner Role field exists and is populated earlier in form
- Approval on exact question wording

#### Definition of Done

- [ ] Question added to OmniScript
- [ ] Conditional display logic works correctly (PCP/Dual only)
- [ ] Question is required and validation works
- [ ] Response is saved correctly
- [ ] Conditional trigger for optional fee question works (Story 3.3)
- [ ] UI/UX review completed
- [ ] Unit tests pass (OmniScript validation)
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 3.3: Add Optional Fee Question (Conditional on Concierge = Yes)

**As a** PCP or Dual practitioner who practices concierge medicine
**I want** to indicate whether my concierge fee is optional for patients
**So that** the credentialing team understands my fee structure

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Question Display Logic**
   - Question is displayed ONLY when:
     - Practitioner Role = PCP OR Dual
     - AND Concierge Medicine Question (Story 3.2) = "Yes"
   - Question is hidden if Concierge Medicine Question = "No" or unanswered
   - Question appears immediately below Concierge Medicine Question
   - Question is required (if displayed)

2. **Question Text and Format**
   - Question text exactly as specified:
     ```
     *Is your concierge fee for additional services optional to your patients?
     ```
   - Radio button control with two options:
     - ○ Yes
     - ○ No
   - Asterisk (*) indicates required field

3. **Response Capture**
   - User selection is saved to OmniScript data
   - Response is mapped to appropriate field/object
   - Response is visible in form review/summary step
   - Response is persisted when form is saved

4. **Clearing Logic**
   - If parent question (Concierge Medicine) changes from "Yes" to "No", this question is hidden AND its response is cleared
   - If user navigates back and changes parent answer, this question reacts dynamically

5. **Validation**
   - Cannot submit form without answering this question (if displayed)
   - Error message if validation fails: "Please indicate whether your concierge fee is optional."
   - Validation occurs before form submission

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English`
- **Element Type:** Radio Button
- **Element Name:** `RadioConciergeFeeOptional` (or similar)
- **Show Condition:** `%RadioConciergeMedicine% == 'Yes'`
- **Required:** Yes (when shown)
- **Options:**
  - Label: "Yes", Value: "Yes"
  - Label: "No", Value: "No"
- **Data Mapping:** Map to custom field or pass to Integration Procedure

#### Dependencies

- Story 3.2 completed (parent question exists)
- Conditional logic framework in OmniScript

#### Definition of Done

- [ ] Question added to OmniScript
- [ ] Conditional display logic works correctly
- [ ] Question is required when displayed
- [ ] Response is saved correctly
- [ ] Clearing logic works when parent changes
- [ ] UI/UX review completed
- [ ] Unit tests pass
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 3.4: Add Concierge Attestation Warning Message with Hyperlinks

**As a** PCP or Dual practitioner completing the PAR form
**I want** to see a warning message about the concierge attestation requirement
**So that** I am aware of the attestation form I need to execute during credentialing

**Priority:** P1 - High
**Story Points:** 3
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Message Display Logic**
   - Warning message is displayed for ALL practitioners with Role = PCP OR Dual
   - Message is displayed regardless of answer to concierge medicine question
   - Message appears AFTER the concierge questions (Story 3.2 and 3.3) and BEFORE the question "*Are you joining an existing group?"
   - Message is always visible (not hidden by conditional logic)

2. **Message Text and Format**
   - Text exactly as specified:
     ```
     ⚠️ Please ensure that you review and execute the concierge attestation form during your
     credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and
     Provider Attestation can be found within the Provider Manual located:
     [IBX] | [AHNJ] | [AHPA]

     Noncompliance with executing the concierge attestation may result in the delay or
     rejection of your application.
     ```
   - Warning icon (⚠️) or visual indicator (yellow background, alert style)
   - Three hyperlinks embedded:
     - **IBX** → https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx
     - **AHNJ** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx
     - **AHPA** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx
   - Hyperlinks are styled as clickable links (blue, underlined)
   - Links open in new tab/window

3. **Visual Design**
   - Message is visually distinct (e.g., bordered box, colored background, icon)
   - Font size is readable (not too small)
   - Spacing/padding around message for emphasis
   - Consistent with other warning/alert messages in form

4. **Hyperlink Functionality**
   - Clicking each link opens the correct URL in new tab
   - Links are accessible (keyboard navigation, screen reader compatible)
   - Links work in all supported browsers (Chrome, Firefox, Edge, Safari)
   - Links work on mobile/tablet (if form is mobile-accessible)

5. **No User Interaction Required**
   - Message is informational only (no checkbox or acknowledgment required)
   - User can proceed with form submission without interacting with message
   - Message does not block form submission

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English`
- **Element Type:** Text Block (or HTML element for rich formatting)
- **Element Name:** `TextBlockConciergeAttestation`
- **Show Condition:** `%PractitionerRole% == 'PCP' OR %PractitionerRole% == 'Dual'`
- **HTML Content:** Use HTML tags for hyperlinks:
  ```html
  <div class="concierge-warning">
    <p>⚠️ Please ensure that you review and execute the concierge attestation form during your
    credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and
    Provider Attestation can be found within the Provider Manual located:
    <a href="https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx" target="_blank">IBX</a> |
    <a href="https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx" target="_blank">AHNJ</a> |
    <a href="https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx" target="_blank">AHPA</a></p>
    <p>Noncompliance with executing the concierge attestation may result in the delay or
    rejection of your application.</p>
  </div>
  ```
- **CSS Styling:** Apply custom CSS for warning box styling (if needed)
- **Accessibility:** Ensure links have `target="_blank"` and `rel="noopener noreferrer"` for security

#### Dependencies

- Story 3.2 completed (concierge questions exist)
- Approval on exact message wording and URLs
- Design/UX approval on visual styling

#### Definition of Done

- [ ] Warning message added to OmniScript
- [ ] Message displays for PCP/Dual practitioners
- [ ] Three hyperlinks work correctly (open in new tab)
- [ ] Visual styling is consistent with form design
- [ ] Accessibility tested (keyboard, screen reader)
- [ ] Cross-browser testing completed
- [ ] Mobile/responsive testing completed (if applicable)
- [ ] UI/UX review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 3.5: Map PAR Form Concierge Responses to Info Code Assignments

**As a** Integration Developer
**I want** the PAR form concierge responses to create appropriate Info Code Assignments
**So that** the backend system accurately reflects the practitioner's concierge status

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** Integration Procedure / DataRaptor

#### Acceptance Criteria

1. **Data Mapping Logic**
   - When PAR form is submitted with `Concierge Medicine = Yes`:
     - Create `PRM_InfoCodeAssignment__c` record with:
       - `PRM_InfoCode__c` = "Concierge Provider" (external Info Code)
       - `PRM_Account__c` = Practitioner Account Id
       - `PRM_EffectiveDate__c` = Application submission date or credentialing effective date
       - `PRM_Pending__c` = true (if case workflow is used)
       - `PRM_CaseManager__c` = Case Manager Id (if applicable)
   - When PAR form is submitted with `Concierge Medicine = No`:
     - Do NOT create Info Code Assignment
     - If an existing "Concierge Provider" assignment exists and is pending, consider terminating it or leaving it for manual review

2. **Optional Fee Capture (Future Enhancement)**
   - Response to "Is your concierge fee optional?" is captured but not necessarily stored in Info Code Assignment
   - Consider adding custom field on `PRM_InfoCodeAssignment__c`: `PRM_IsFeeOptional__c` (checkbox) - Optional for future use
   - Or store in IndividualApplication custom field: `PRM_ConciergeFeeOptional__c`

3. **Integration Procedure Logic**
   - Integration Procedure (e.g., `PRM_CreatePARCaseAndRecords` or similar) includes step to create Info Code Assignment
   - Step is conditional: Only execute if `%RadioConciergeMedicine% == 'Yes'`
   - Error handling: If Info Code Assignment creation fails, log error but do not block entire form submission (allow manual follow-up)

4. **DataRaptor Mapping**
   - Create or update DataRaptor to insert `PRM_InfoCodeAssignment__c` record
   - Input from OmniScript:
     - `RadioConciergeMedicine` (Yes/No)
     - `RadioConciergeFeeOptional` (Yes/No) - optional
     - `PractitionerAccountId`
     - `CaseManagerId`
     - `EffectiveDate` (derived from application date)
   - Output: `PRM_InfoCodeAssignment__c` Id

5. **Lookup Info Code by Name**
   - Integration Procedure or DataRaptor must look up `PRM_InfoCode__c` record WHERE `Name = 'Concierge Provider'`
   - Use Extract DataRaptor or SOQL in IP to get Info Code Id
   - Error handling: If Info Code does not exist, log error and alert admin (should not happen if setup is correct)

6. **Pending and Case Manager Linkage**
   - If PAR form uses case workflow:
     - Set `PRM_Pending__c = true` on Info Code Assignment
     - Link `PRM_CaseManager__c` to IndividualApplication (Case Manager) Id
   - When case is approved:
     - `PRM_Pending__c` is set to false (via existing case approval logic)
   - When case is denied:
     - `PRM_Pending__c` is set to false (via `PRM_CaseManagerDenialUtility` - already handled per Flow Impact Analysis)

#### Technical Considerations

- **Integration Procedure:** `PRM_CreatePARCaseAndRecords` (or similar IP that creates PAR case and related records)
- **DataRaptor:** Create new DataRaptor `PRMDRInsertConciergeInfoCodeAssignment` or extend existing
- **Info Code Lookup:** Use Extract DataRaptor `PRMDRExtractInfoCodeByName` with Input: `InfoCodeName = 'Concierge Provider'`, Output: `InfoCodeId`
- **Conditional Execution:** Use Set Values or Decision element in IP to check `%RadioConciergeMedicine%` before creating assignment
- **Error Handling:** Use Try-Catch or Response Action to handle errors gracefully
- **Transaction Boundary:** Ensure Info Code Assignment creation is part of the same transaction as PAR case creation (if possible), or use rollback logic

#### Dependencies

- Story 3.2 completed (concierge question exists and captures data)
- Story 3.3 completed (optional fee question exists)
- Epic 2, Story 2.1 completed ("Concierge Provider" Info Code master record exists)
- Info Code Assignment object and fields are available in org
- Access to Integration Procedure and DataRaptor designer

#### Definition of Done

- [ ] Integration Procedure updated to create Info Code Assignment
- [ ] DataRaptor created/updated for Info Code Assignment insertion
- [ ] Info Code lookup by name works correctly
- [ ] Conditional logic tested (Yes creates assignment, No does not)
- [ ] Pending and Case Manager fields populated correctly
- [ ] Error handling tested (Info Code not found, SOQL failure, etc.)
- [ ] Unit tests pass (IP execution with various inputs)
- [ ] Integration test: Submit PAR form with concierge = Yes → verify assignment created
- [ ] Integration test: Submit PAR form with concierge = No → verify no assignment created
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

## Technical Mapping

### OmniScript to Backend Mapping

| OmniScript Field | Type | Value | Backend Action |
|------------------|------|-------|----------------|
| `RadioConciergeMedicine` | Radio | "Yes" | Create PRM_InfoCodeAssignment__c with PRM_InfoCode__c = "Concierge Provider" (lookup by name) |
| `RadioConciergeMedicine` | Radio | "No" | Do NOT create Info Code Assignment |
| `RadioConciergeFeeOptional` | Radio | "Yes" / "No" | (Optional) Store in PRM_InfoCodeAssignment__c.PRM_IsFeeOptional__c OR IndividualApplication.PRM_ConciergeFeeOptional__c |

### Info Code Assignment Fields Populated

| Field | Source | Value |
|-------|--------|-------|
| `PRM_InfoCode__c` | Lookup | Id of "Concierge Provider" Info Code |
| `PRM_Account__c` | OmniScript | Practitioner Account Id |
| `PRM_HealthcareFacility__c` | N/A | null (practitioner-level assignment) |
| `PRM_EffectiveDate__c` | Derived | Application submission date OR credentialing effective date (business rule) |
| `PRM_TerminationDate__c` | N/A | null (active assignment) |
| `PRM_Pending__c` | Business Logic | true (if case workflow; false if auto-approved) |
| `PRM_CaseManager__c` | OmniScript | IndividualApplication (Case Manager) Id |

### Optional Field (Future Enhancement)

**Option A: Add to PRM_InfoCodeAssignment__c**
- Field Name: `PRM_IsFeeOptional__c`
- Type: Checkbox
- Description: Indicates if concierge fee is optional to patients

**Option B: Add to IndividualApplication**
- Field Name: `PRM_ConciergeFeeOptional__c`
- Type: Checkbox
- Description: (Same as above)

**Recommendation:** Option A (on Info Code Assignment) for better data encapsulation.

---

## Acceptance Testing

### Test Scenario 1: PCP Answers Yes to Concierge

**Given** a user is completing PAR form for a practitioner with Role = PCP
**When** the user reaches Practitioner screen
**Then** concierge medicine question is displayed
**When** the user selects "Yes" to concierge medicine
**Then** optional fee question is displayed
**When** the user selects "No" to optional fee
**And** the user submits the form
**Then** a "Concierge Provider" Info Code Assignment is created with:
- PRM_Account__c = Practitioner Account Id
- PRM_EffectiveDate__c = Application date
- PRM_Pending__c = true
- PRM_CaseManager__c = Case Manager Id
**And** the assignment is visible in PIE (Info Code Assignments related list)

---

### Test Scenario 2: PCP Answers No to Concierge

**Given** a user is completing PAR form for a practitioner with Role = PCP
**When** the user reaches Practitioner screen
**Then** concierge medicine question is displayed
**When** the user selects "No" to concierge medicine
**Then** optional fee question is NOT displayed
**When** the user submits the form
**Then** NO "Concierge Provider" Info Code Assignment is created
**And** no concierge-related records exist for this practitioner

---

### Test Scenario 3: Specialist Does Not See Concierge Questions

**Given** a user is completing PAR form for a practitioner with Role = Specialist (not PCP or Dual)
**When** the user reaches Practitioner screen
**Then** concierge medicine question is NOT displayed
**And** optional fee question is NOT displayed
**And** warning message is NOT displayed
**When** the user submits the form
**Then** form submission is successful (concierge logic does not apply)

---

### Test Scenario 4: Dual Practitioner Sees Questions

**Given** a user is completing PAR form for a practitioner with Role = Dual
**When** the user reaches Practitioner screen
**Then** concierge medicine question is displayed
**And** warning message is displayed
**When** the user selects "Yes" to concierge medicine
**Then** optional fee question is displayed
**When** the user submits the form
**Then** a "Concierge Provider" Info Code Assignment is created

---

### Test Scenario 5: User Changes Answer from Yes to No

**Given** a user has selected "Yes" to concierge medicine
**And** optional fee question is displayed
**When** the user changes answer to "No" to concierge medicine
**Then** optional fee question is hidden
**And** optional fee response is cleared (if previously answered)
**When** the user submits the form
**Then** NO "Concierge Provider" Info Code Assignment is created

---

### Test Scenario 6: Warning Message Links Work

**Given** a user is completing PAR form for a practitioner with Role = PCP
**When** the user reaches Practitioner screen
**Then** warning message is displayed with three hyperlinks
**When** the user clicks "IBX" link
**Then** https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx opens in new tab
**When** the user clicks "AHNJ" link
**Then** https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx opens in new tab
**When** the user clicks "AHPA" link
**Then** https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx opens in new tab

---

### Test Scenario 7: Form Validation Requires Answer

**Given** a user is completing PAR form for a practitioner with Role = PCP
**When** the user reaches Practitioner screen
**And** the user does NOT answer the concierge medicine question
**When** the user tries to proceed to next step
**Then** validation error is displayed: "Please indicate whether you practice concierge medicine."
**And** user cannot proceed until question is answered

---

### Test Scenario 8: Optional Fee Validation (Conditional Required)

**Given** a user has selected "Yes" to concierge medicine
**When** optional fee question is displayed
**And** the user does NOT answer the optional fee question
**When** the user tries to proceed to next step
**Then** validation error is displayed: "Please indicate whether your concierge fee is optional."
**And** user cannot proceed until question is answered

---

### Test Scenario 9: Historical PAR Applications Still Viewable

**Given** a PAR application was submitted BEFORE these form changes were deployed
**When** an admin views the historical application
**Then** old fee questions and responses are visible (read-only)
**And** new concierge questions are NOT displayed (did not exist at time of submission)
**And** no errors occur when viewing historical data

---

### Test Scenario 10: Case Approval Updates Info Code Assignment

**Given** a PAR form was submitted with concierge medicine = Yes
**And** a "Concierge Provider" Info Code Assignment was created with PRM_Pending__c = true
**When** the Case Manager (IndividualApplication) is approved
**Then** the Info Code Assignment is updated with PRM_Pending__c = false
**And** the assignment is now active (visible in Provider Directory feed)

---

### Test Scenario 11: Case Denial Updates Info Code Assignment

**Given** a PAR form was submitted with concierge medicine = Yes
**And** a "Concierge Provider" Info Code Assignment was created with PRM_Pending__c = true
**When** the Case Manager (IndividualApplication) is denied
**Then** the Info Code Assignment is updated with PRM_Pending__c = false (via PRM_CaseManagerDenialUtility)
**And** the assignment is NOT active (does not appear in Provider Directory)

---

## Implementation Checklist

### Phase 1: OmniScript Updates
- [ ] **Story 3.1**: Remove old fee questions from PAR form
- [ ] **Story 3.2**: Add concierge medicine question with conditional logic
- [ ] **Story 3.3**: Add optional fee question (conditional)
- [ ] **Story 3.4**: Add warning message with hyperlinks
- [ ] Unit test: OmniScript renders correctly for all practitioner roles
- [ ] Regression test: Existing PAR form flows still work

### Phase 2: Backend Integration
- [ ] **Story 3.5**: Create Integration Procedure logic to create Info Code Assignment
- [ ] **Story 3.5**: Create/update DataRaptor for Info Code Assignment insertion
- [ ] **Story 3.5**: Add Info Code lookup logic (by name: "Concierge Provider")
- [ ] Unit test: IP creates assignment correctly when concierge = Yes
- [ ] Unit test: IP does NOT create assignment when concierge = No
- [ ] Integration test: End-to-end PAR form submission → Info Code Assignment creation

### Phase 3: Case Workflow Integration
- [ ] Verify `PRM_Pending__c` flag is set correctly on Info Code Assignment
- [ ] Verify `PRM_CaseManager__c` link is populated correctly
- [ ] Test case approval: `PRM_Pending__c` set to false (existing logic)
- [ ] Test case denial: `PRM_Pending__c` set to false (via `PRM_CaseManagerDenialUtility`)

### Phase 4: Testing
- [ ] Execute all 11 test scenarios above
- [ ] Cross-browser testing (Chrome, Firefox, Edge, Safari)
- [ ] Mobile/responsive testing (if applicable)
- [ ] Accessibility testing (keyboard navigation, screen reader)
- [ ] Performance testing (form submission time acceptable)

### Phase 5: Deployment
- [ ] Deploy OmniScript changes to Test environment
- [ ] Deploy Integration Procedure and DataRaptor changes to Test environment
- [ ] UAT with PDA team (complete PAR form with concierge questions)
- [ ] UAT with Credentialing team (verify Info Code Assignment creation)
- [ ] Deploy to Production (after UAT sign-off)
- [ ] Monitor Production for errors (first week after deployment)

---

## Estimated Effort

| Story | Story Points |
|-------|--------------|
| 3.1: Remove old questions | 2 |
| 3.2: Add concierge question | 5 |
| 3.3: Add optional fee question | 3 |
| 3.4: Add warning message | 3 |
| 3.5: Backend integration | 5 |
| **Total (Epic 3)** | **18** |

**Combined Total (All Epics):**
- Epic 1 (Internal Concierge PCP Info Code): 28 points
- Epic 2 (External Concierge Provider Info Code): 24 points
- Epic 3 (PAR Form Changes): 18 points
- Flow Integration Changes: 37 points
- **Grand Total: ~107 story points**

---

## Next Steps

1. **Review PAR form changes** with business stakeholders (confirm question wording, URLs, placement)
2. **Prioritize** PAR form changes alongside Info Code backend implementation
3. **Design mockups** for PAR form changes (warning message styling, question layout)
4. **Begin development** of OmniScript changes (Stories 3.1-3.4)
5. **Develop backend integration** (Story 3.5) in parallel with main Info Code implementation
6. **Test end-to-end** (PAR form submission → Info Code Assignment creation → Provider Directory feed)

---

**End of Document**
