# Concierge Medicine - Recredentialing PSV Guided Flow User Stories

**Document Version:** 1.0  
**Created Date:** April 6, 2026  
**Project:** PIE & Recredentialing - Concierge Medicine Provider Tracking in Recredentialing  
**Epic:** Epic 6 - Recredentialing PSV Guided Flow Integration  

---

## Epic 6: Recredentialing PSV Guided Flow Integration

**Epic Goal:** Add concierge medicine questions to the Recredentialing PSV Guided Flow and capture practitioner responses on the Case Manager (IndividualApplication) object.

**Business Value:** Capture updated concierge medicine information during recredentialing; maintain historical record of practitioner responses over time.

**Priority:** P0 - Critical  
**Estimated Story Points:** 12  

---

## Story 6.1: Create Case Manager Fields for Recredentialing Concierge Responses

**As a** System Administrator  
**I want** four checkbox fields on the Case Manager (IndividualApplication) object to capture recredentialing concierge responses  
**So that** we preserve the practitioner's recredentialing answers for audit, reporting, and compliance purposes  

**Priority:** P0 - Critical  
**Story Points:** 3  
**Component:** PIE - Schema / Field Creation  

---

### Acceptance Criteria

#### 1. Field Creation - Concierge Service Offered Prior to Date

**Field Details:**
- **Object:** IndividualApplication (Case Manager)
- **Field API Name:** `PRM_ConciergeOfferedPriorToDate__c`
- **Field Type:** Checkbox (Boolean)
- **Field Label:** "Concierge Service Offered Prior to 01/01/2025"
- **Help Text:** "Indicates whether the practitioner offered concierge services prior to January 1, 2025 (answered during recredentialing)"
- **Default Value:** false

**Use Case:** Tracks if practitioner is newly offering concierge services vs. continuing existing practice

---

#### 2. Field Creation - Concierge Fee Optional for Existing Patients

**Field Details:**
- **Object:** IndividualApplication (Case Manager)
- **Field API Name:** `PRM_ConciergeFeeOptionalExisting__c`
- **Field Type:** Checkbox (Boolean)
- **Field Label:** "Concierge Fee Optional for Existing Patients"
- **Help Text:** "Indicates whether the practitioner's concierge fee is optional for existing patients (answered during recredentialing)"
- **Default Value:** false

**Use Case:** Distinguishes between mandatory vs. optional concierge fee models for existing patient base

---

#### 3. Field Creation - Accepts New Patients Without Concierge Fee

**Field Details:**
- **Object:** IndividualApplication (Case Manager)
- **Field API Name:** `PRM_AcceptsNewPatientsNonConcierge__c`
- **Field Type:** Checkbox (Boolean)
- **Field Label:** "Accepts New Patients Without Concierge Fee"
- **Help Text:** "Indicates whether the practitioner accepts new patients who are not enrolled in concierge services and not paying the concierge fee (answered during recredentialing)"
- **Default Value:** false

**Use Case:** Critical for network adequacy - identifies if practitioner accepts non-concierge patients

---

#### 4. Field Visibility on Page Layout

- Add all three fields to Case Manager page layout
- Place in "Recredentialing Details" or "Provider Information" section
- Fields are visible in edit and view modes
- Fields appear in related lists and reports
- Group with existing concierge fields: `PRM_ConciergeMedicineIndicator__c` and `PRM_ConciergeFeeOptional__c`

---

#### 5. Field Access, Permission Sets, and Metadata Notification

**Given** the new fields have been created in Salesforce,  
**When** the Admin configures user access and deployment documentation,  
**Then** the access levels shall be explicitly mapped as follows:

| Permission Set / Profile | Access Level |
|-------------------------|--------------|
| **Credentialing** | Read Access |
| **PDA** | Read Access |
| **Network Management QC Permission Set** | Read Access |
| **PRM CredentialingUser** | Edit Access |
| **PRM ProviderDataAdmin** | Edit Access |
| **PRM-NetworkManagement@C** | Edit Access |
| **PRM DataViewAll** | View All, Read |
| **PAM-DataModifyAll** | Read, Create, Edit, View All |

**And** the Admin shall explicitly **NOTIFY KISHLAY + ANSHAY** to add the fields for SF to DART Metadata & Data Dictionary:
- `PRM_ConciergeOfferedPriorToDate__c`
- `PRM_ConciergeFeeOptionalExisting__c`
- `PRM_AcceptsNewPatientsNonConcierge__c`

---

#### 6. Backward Compatibility

- Existing Case Manager records have default values (false)
- New Case Manager records will be populated by Recredentialing PSV Guided Flow (Story 6.2)
- Fields are independent of initial credentialing fields (`PRM_ConciergeMedicineIndicator__c`, `PRM_ConciergeFeeOptional__c`)

---

#### 7. Data Relationship

**Relationship to Initial Credentialing Fields:**
- `PRM_ConciergeMedicineIndicator__c` - Captured during initial credentialing (PAR form)
- `PRM_ConciergeFeeOptional__c` - Captured during initial credentialing (PAR form)
- **NEW:** `PRM_ConciergeOfferedPriorToDate__c` - Captured during recredentialing only
- **NEW:** `PRM_ConciergeFeeOptionalExisting__c` - Captured during recredentialing only (existing patients)
- **NEW:** `PRM_AcceptsNewPatientsNonConcierge__c` - Captured during recredentialing only

**Note:** Initial credentialing fields and recredentialing fields coexist on Case Manager. A practitioner may have multiple Case Manager records over time (initial + recred cycles).

---

### Technical Considerations

- **Object:** IndividualApplication
- **Field Type:** Checkbox (Boolean) - easier to query and use in reports than picklist
- **Reporting:** These fields enable tracking of concierge status changes during recredentialing cycles
- **Historical Tracking:** Case Manager records preserve historical responses; new recred case = new Case Manager record
- **Naming Convention:** Fields clearly indicate they are recredentialing-specific (e.g., "Existing Patients", "Prior to Date")

---

### Dependencies

- Access to IndividualApplication object schema
- Page layout edit access
- Permission set configuration access

---

### Definition of Done

- [ ] `PRM_ConciergeOfferedPriorToDate__c` field created on IndividualApplication
- [ ] `PRM_ConciergeFeeOptionalExisting__c` field created on IndividualApplication
- [ ] `PRM_AcceptsNewPatientsNonConcierge__c` field created on IndividualApplication
- [ ] Fields added to Case Manager page layout
- [ ] Fields grouped with existing concierge fields
- [ ] Field-level security configured per acceptance criteria
- [ ] Permission sets updated:
  - [ ] Credentialing - Read Access
  - [ ] PDA - Read Access
  - [ ] Network Management QC - Read Access
  - [ ] PRM CredentialingUser - Edit Access
  - [ ] PRM ProviderDataAdmin - Edit Access
  - [ ] PRM-NetworkManagement@C - Edit Access
  - [ ] PRM DataViewAll - View All, Read
  - [ ] PAM-DataModifyAll - Read, Create, Edit, View All
- [ ] Help text clearly explains purpose
- [ ] Fields deployed to all environments (Dev, QA, UAT, Prod)
- [ ] **KISHLAY + ANSHAY notified** to add fields to SF-to-DART Metadata & Data Dictionary
- [ ] DART team confirmation received
- [ ] Documentation updated
- [ ] Reporting team notified of new fields

---

---

## Story 6.2: Add Concierge Questions to Recredentialing PSV Guided Flow and Save Responses to Case Manager

**As a** Practitioner completing recredentialing via PSV Guided Flow  
**I want** to answer concierge medicine questions specific to recredentialing  
**So that** the credentialing team has updated information about my concierge practice model  

**Priority:** P0 - Critical  
**Story Points:** 9  
**Component:** PSV Guided Flow - Recredentialing  

---

### Acceptance Criteria

#### 1. Question Display Logic - Practitioner-Level Concierge Question

**Display Condition:**
- Question is displayed ONLY when `Practitioner Role = PCP` OR `Practitioner Role = Dual`
- Question is NOT displayed for other practitioner roles (Specialist, Ancillary, etc.)
- Question is required (cannot proceed without answering)
- Question appears in "Provider Information" or "Practice Details" section of PSV Guided Flow

**Question Text:**
```
*(For PCPs only) Do you practice concierge medicine (or retainer medicine) by charging your 
patients a concierge fee (or retainer) separate from the applicable patient cost-sharing 
(e.g., co-pays, deductibles, etc.)?
```

**Answer Options:**
- ○ Yes
- ○ No

**Conditional Logic:**
- If user selects "Yes", display Questions 2, 3, and 4 below
- If user selects "No", hide Questions 2, 3, and 4
- Changing answer from "Yes" to "No" hides subsequent questions and clears their responses

---

#### 2. Question 2 - Concierge Service Offered Prior to Date (Conditional)

**Display Condition:**
- Only displayed if Question 1 = "Yes"
- Required when displayed

**Question Text:**
```
*Did you offer concierge services to your patients prior to January 1, 2025?
```

**Answer Options:**
- ○ Yes
- ○ No

**Business Purpose:** Identifies if practitioner is newly offering concierge vs. continuing existing practice

---

#### 3. Question 3 - Concierge Fee Optional for Existing Patients (Conditional)

**Display Condition:**
- Only displayed if Question 1 = "Yes"
- Required when displayed

**Question Text:**
```
*Is your concierge fee for additional services optional for your existing patients?
```

**Answer Options:**
- ○ Yes
- ○ No

**Business Purpose:** Determines if existing patients can opt out of concierge fee

---

#### 4. Question 4 - Accepts New Patients Without Concierge Fee (Conditional)

**Display Condition:**
- Only displayed if Question 1 = "Yes"
- Required when displayed

**Question Text:**
```
*Will you accept new patients who are not enrolled in concierge services and are not paying 
the concierge fee?
```

**Answer Options:**
- ○ Yes
- ○ No

**Business Purpose:** Critical for network adequacy - determines if practitioner accepts non-concierge patients

---

#### 5. Concierge Attestation Warning Message with Hyperlinks

**Display Condition:**
- Warning message is displayed for ALL practitioners with Role = PCP OR Dual
- Message is displayed regardless of answer to concierge medicine question
- Message appears AFTER concierge questions

**Message Text:**
```
⚠️ Please ensure that you review and execute the concierge attestation form during your 
credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and 
Provider Attestation can be found within the Provider Manual located:
[IBX] | [AHNJ] | [AHPA]

Noncompliance with executing the concierge attestation may result in the delay or 
rejection of your application.
```

**Hyperlinks:**
- **IBX** → https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx
- **AHNJ** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx
- **AHPA** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx
- Links open in new tab/window

**Visual Design:**
- Message is visually distinct (bordered box, colored background)
- Warning icon (⚠️) or visual indicator
- Consistent with other warning messages in PSV Guided Flow

---

#### 6. Response Capture and Mapping to Case Manager

**When PSV Guided Flow is submitted, update `IndividualApplication` (Case Manager) record:**

**Scenario A: Practitioner answers "Yes" to concierge (Question 1 = Yes):**
- `PRM_ConciergeMedicineIndicator__c` = true (reused from initial cred)
- `PRM_ConciergeOfferedPriorToDate__c` = true if Question 2 = "Yes", false if "No"
- `PRM_ConciergeFeeOptionalExisting__c` = true if Question 3 = "Yes", false if "No"
- `PRM_AcceptsNewPatientsNonConcierge__c` = true if Question 4 = "Yes", false if "No"
- `PRM_ConciergeFeeOptional__c` = Not updated during recred (initial cred field)

**Scenario B: Practitioner answers "No" to concierge (Question 1 = No):**
- `PRM_ConciergeMedicineIndicator__c` = false
- `PRM_ConciergeOfferedPriorToDate__c` = false (or null)
- `PRM_ConciergeFeeOptionalExisting__c` = false (or null)
- `PRM_AcceptsNewPatientsNonConcierge__c` = false (or null)

**Persistence:**
- Responses are persisted when PSV Guided Flow is saved (draft or submitted)
- Responses are visible in Case Manager record
- Responses are independent of case approval/denial status
- If recred case is reopened or amended, fields are updated with new responses

---

#### 7. Validation Rules

- Question 1 is required if PCP/Dual (cannot proceed without answering)
- If Question 1 = "Yes", Questions 2, 3, and 4 are required
- Error messages:
  - "Please indicate whether you practice concierge medicine."
  - "Please answer all concierge-related questions before proceeding."

---

#### 8. Practice Location Selection (Optional - Future Enhancement)

**Note:** Similar to PAR form (Story 2.2), future enhancement may include practice location-level selection during recredentialing. For initial implementation (this story), recredentialing questions are at practitioner level only.

**If future enhancement is needed:**
- Allow practitioner to select which practice locations have concierge status during recredentialing
- Update or create Practitioner Practice Location-level Info Code Assignments based on selections
- Requires additional user story

---

### Technical Considerations

- **PSV Guided Flow:** Update existing recredentialing PSV Guided Flow (likely a Screen Flow or LWC component)
- **Question Elements:**
  - Element Type: Radio Button Group
  - Element Names: 
    - `RadioConciergeMedicineRecred`
    - `RadioConciergeOfferedPrior`
    - `RadioConciergeFeeOptionalExisting`
    - `RadioAcceptsNewPatientsNonConcierge`
  - Show Condition: `{!PractitionerRole} == 'PCP' OR {!PractitionerRole} == 'Dual'`
  - Required: Yes
- **Conditional Visibility:**
  - Questions 2, 3, 4 visible when: `{!RadioConciergeMedicineRecred} == 'Yes'`
- **Data Mapping:**
  - Flow or Apex controller updates IndividualApplication fields
  - String to Boolean conversion: `IF({!RadioConciergeMedicineRecred} == 'Yes', true, false)`
- **Integration with Case Manager:**
  - Case Manager Id is available in PSV Guided Flow context
  - Update Case Manager record via DML or Record Update element in Flow

---

### Dependencies

- Story 6.1 completed (Case Manager fields exist: `PRM_ConciergeOfferedPriorToDate__c`, `PRM_ConciergeFeeOptionalExisting__c`, `PRM_AcceptsNewPatientsNonConcierge__c`)
- Access to Recredentialing PSV Guided Flow (Flow designer or LWC code)
- Practitioner Role field exists and is populated earlier in PSV Guided Flow
- Case Manager record is created/available at time of PSV Guided Flow submission

---

### Definition of Done

- [ ] Question 1 (practitioner-level concierge) added to PSV Guided Flow
- [ ] Question 2 (concierge offered prior to date) added with conditional display logic
- [ ] Question 3 (fee optional for existing patients) added with conditional display logic
- [ ] Question 4 (accepts new non-concierge patients) added with conditional display logic
- [ ] Concierge attestation warning message added with hyperlinks
- [ ] Conditional display logic works (PCP/Dual only)
- [ ] Questions 2, 3, 4 are hidden when Question 1 = "No"
- [ ] Questions 2, 3, 4 are shown and required when Question 1 = "Yes"
- [ ] All questions are required when displayed
- [ ] Validation rules work correctly
- [ ] Case Manager field mapping implemented (Flow or Apex)
- [ ] String to boolean conversion works correctly
- [ ] Responses saved correctly to Case Manager fields
- [ ] Responses visible on Case Manager record
- [ ] Hyperlinks in warning message work correctly (open in new tab)
- [ ] Visual styling is consistent with existing PSV Guided Flow
- [ ] Accessibility tested (keyboard navigation, screen reader)
- [ ] Cross-browser testing completed
- [ ] Mobile/responsive testing completed (if applicable)
- [ ] Unit tests pass (if Apex involved)
- [ ] Integration test: Submit PSV with "Yes" → all 4 fields populated on Case Manager
- [ ] Integration test: Submit PSV with "No" → only Question 1 field populated (false), others null/false
- [ ] Integration test: Change "Yes" to "No" → Questions 2-4 hidden and cleared
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off by Credentialing team
- [ ] User documentation updated

---

---

## Test Scenarios for Epic 6

### Scenario 6.1: PCP Answers Yes to Concierge During Recredentialing

**Given** a PCP practitioner is completing recredentialing via PSV Guided Flow  
**When** the practitioner answers:
- Question 1 (Concierge Medicine): Yes
- Question 2 (Offered Prior to 01/01/2025): No
- Question 3 (Fee Optional for Existing): Yes
- Question 4 (Accepts New Non-Concierge): Yes  
**Then**:
- All 4 questions are displayed
- Practitioner can submit successfully
- Case Manager (IndividualApplication) record is updated:
  - `PRM_ConciergeMedicineIndicator__c` = true
  - `PRM_ConciergeOfferedPriorToDate__c` = false
  - `PRM_ConciergeFeeOptionalExisting__c` = true
  - `PRM_AcceptsNewPatientsNonConcierge__c` = true
- Fields are visible on Case Manager page

---

### Scenario 6.2: PCP Answers No to Concierge During Recredentialing

**Given** a PCP practitioner is completing recredentialing via PSV Guided Flow  
**When** the practitioner answers:
- Question 1 (Concierge Medicine): No  
**Then**:
- Questions 2, 3, and 4 are NOT displayed
- Warning message is still displayed
- Practitioner can submit successfully
- Case Manager record is updated:
  - `PRM_ConciergeMedicineIndicator__c` = false
  - `PRM_ConciergeOfferedPriorToDate__c` = false (or null)
  - `PRM_ConciergeFeeOptionalExisting__c` = false (or null)
  - `PRM_AcceptsNewPatientsNonConcierge__c` = false (or null)

---

### Scenario 6.3: Specialist Does Not See Concierge Questions

**Given** a Specialist practitioner is completing recredentialing via PSV Guided Flow  
**When** the practitioner proceeds through the flow  
**Then**:
- Concierge questions (1-4) are NOT displayed
- Warning message is NOT displayed
- Practitioner can submit successfully without answering concierge questions
- Case Manager fields remain at default values (false/null)

---

### Scenario 6.4: PCP Changes Answer from Yes to No

**Given** a PCP practitioner is completing recredentialing via PSV Guided Flow  
**When** the practitioner:
1. Answers Question 1 = "Yes"
2. Sees Questions 2, 3, 4 appear
3. Answers Questions 2, 3, 4
4. Changes Question 1 to "No"  
**Then**:
- Questions 2, 3, 4 are immediately hidden
- Responses to Questions 2, 3, 4 are cleared
- Practitioner can submit with only Question 1 = "No"
- Case Manager record reflects Question 1 = false, Questions 2-4 = false/null

---

### Scenario 6.5: Validation Error - Missing Required Question

**Given** a PCP practitioner is completing recredentialing via PSV Guided Flow  
**When** the practitioner:
1. Answers Question 1 = "Yes"
2. Questions 2, 3, 4 appear
3. Answers only Question 2, leaves Questions 3 and 4 blank
4. Attempts to submit  
**Then**:
- Validation error is displayed: "Please answer all concierge-related questions before proceeding."
- Submission is blocked
- Practitioner must answer Questions 3 and 4 to proceed

---

### Scenario 6.6: Warning Message Hyperlinks Work

**Given** a PCP practitioner views the concierge attestation warning message  
**When** the practitioner clicks on:
- IBX link → https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx opens in new tab
- AHNJ link → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx opens in new tab
- AHPA link → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx opens in new tab  
**Then**:
- All links open correctly in new tabs
- User remains on PSV Guided Flow page

---

### Scenario 6.7: Historical Tracking - Multiple Recredentialing Cycles

**Given** a practitioner has completed multiple recredentialing cycles:
- Initial Cred (2024): Answered "No" to concierge
- Recred 1 (2025): Answered "Yes" to concierge
- Recred 2 (2026): Answered "Yes" to concierge (updated answers)  
**When** admin views Case Manager records  
**Then**:
- Three separate Case Manager records exist (one per cycle)
- Each record has its own concierge field values
- Historical trend is visible: No → Yes → Yes
- Latest Case Manager record reflects current status

---

### Scenario 6.8: Field Access - Credentialing User Can Edit

**Given** a Credentialing user with "PRM CredentialingUser" permission set  
**When** the user opens a Case Manager record with recredentialing concierge fields  
**Then**:
- User can view all concierge fields
- User can edit all concierge fields (Edit Access granted)
- User can save changes successfully

---

### Scenario 6.9: Field Access - PDA User Can Read Only

**Given** a PDA user with "PDA" permission set  
**When** the user opens a Case Manager record with recredentialing concierge fields  
**Then**:
- User can view all concierge fields (Read Access granted)
- User CANNOT edit concierge fields (Edit Access not granted)
- Fields appear as read-only

---

### Scenario 6.10: DART Metadata Notification

**Given** the new recredentialing concierge fields have been deployed to Production  
**When** the Admin completes deployment  
**Then**:
- KISHLAY has been notified via email/Slack
- ANSHAY has been notified via email/Slack
- Notification includes field API names:
  - `PRM_ConciergeOfferedPriorToDate__c`
  - `PRM_ConciergeFeeOptionalExisting__c`
  - `PRM_AcceptsNewPatientsNonConcierge__c`
- DART team adds fields to SF-to-DART Metadata & Data Dictionary
- Confirmation received from DART team

---

## Summary

**Total Story Points:** 12 (Story 6.1: 3 points, Story 6.2: 9 points)

**Key Features:**
1. Four concierge-related fields on Case Manager for recredentialing
2. Conditional question logic in PSV Guided Flow (PCP/Dual only)
3. Three additional questions specific to recredentialing (offered prior to date, fee optional for existing, accepts new non-concierge)
4. Warning message with hyperlinks to Provider Manuals
5. Automatic field mapping to Case Manager on submission
6. Field-level security and permission set configuration
7. DART metadata notification workflow

**Dependencies:**
- Story 6.1 must complete before Story 6.2
- Access to PSV Guided Flow designer
- Permission set configuration access

**Integration Points:**
- Case Manager (IndividualApplication) object
- Recredentialing PSV Guided Flow (Screen Flow or LWC)
- DART feed (for metadata updates)

---

**End of Document**
