# Concierge Medicine - Off-Cycle Flow End-to-End User Stories

**Document Version:** 1.0  
**Created Date:** April 7, 2026  
**Purpose:** Comprehensive user stories for Concierge Medicine integration into Off-Cycle Credentialing flow, covering submission, practice location addition, PDA Review, and Info Code Assignment activation

---

## Executive Summary

**Off-Cycle Credentialing** allows practitioners to make mid-cycle changes such as adding new practice locations, updating information, or changing affiliations without waiting for the recredentialing cycle. 

**Critical Integration Points for Concierge Medicine:**
1. **Off-Cycle Submission:** When practitioner adds new practice location, ask if they practice concierge medicine at that location
2. **Info Code Assignment Creation:** Create PPL-level Info Code Assignments with `PRM_Pending__c = true`
3. **PDA Review and Update:** Activate assignments by setting `PRM_Pending__c = false` after case approval
4. **Case Denial:** Mark assignments as denied (not active) when case is denied

**Flow Name:** `PRM_OffCycleCredentialing_English`  
**PDA Review Flow Name:** Similar to PNC → uses `PRM_PNCPDAReviewUpdate` or Off-Cycle-specific PDA flow  
**Case Manager Record Type:** Off-Cycle (IndividualApplication)

---

## Off-Cycle Flow Overview

### Current Off-Cycle Flow (High-Level)

```
Provider Search (NPI, Tax ID, Group Name)
  ↓
Select Main Group + Additional Practice Locations
  ↓
[Option to add NEW practice location if not listed]
  ↓
Enter Practice Location Details (Address, Phone, etc.)
  ↓
Precisely API Validation + Duplicate Check
  ↓
Submit Off-Cycle Request
  ↓
Case Created (Status = Pending)
  ↓
PDA Review and Update
  ↓
Case Approved → Records Activated (PRM_Pending__c = false)
```

**Current Gap:** No concierge question when adding practice locations

**Required Integration:** Add concierge question at practice location level, create Info Code Assignments at PPL level

---

## Off-Cycle Flow Components

### OmniScript Components

| Component | Type | Purpose |
|-----------|------|---------|
| **PRM_OffCycleCredentialing_English** | OmniScript | Main Off-Cycle submission flow |
| **prmGroupSelectionOffCycle** | LWC Component | Group selection with multi-select practice locations |
| **PRM_OffCycleProviderSearch** | Apex Class | Provider search data (getOffcycleProviderSearch method) |
| **PRM_OffCyclePreciselyAPI** | Integration Procedure | Precisely API validation for new addresses |
| **PRM_DuplicateAddCheck** | Integration Procedure | Duplicate address check |

### PDA Review Components (Post-Submission)

| Component | Type | Purpose |
|-----------|------|---------|
| **PRM_OffCyclePDAReviewUpdate** | Integration Procedure | PDA Review and Update for Off-Cycle (similar to PNC) |
| **PRM_CaseManagerDenialUtility** | Apex Class | Handles case denial and pending record updates |
| **PRM_InfoCodeAssignmentUtility** | Apex Class | NEW - Reusable utility for activating/denying Info Code Assignments |

---

## Epic: Concierge Medicine - Off-Cycle Integration

**Epic Goal:** Enable practitioners to indicate concierge medicine practice when adding new practice locations via Off-Cycle flow, create Info Code Assignments, and activate/deny them based on case outcome.

**Total Effort:** 21 story points

**Stories:**
1. Story 1: Add Concierge Question to Off-Cycle "Add New Practice Location" Flow (8 SP)
2. Story 2: Update Off-Cycle PDA Review to Activate Info Code Assignments (8 SP)
3. Story 3: Update Off-Cycle Case Denial to Deny Info Code Assignments (5 SP)

---

## Story 1: Add Concierge Question to Off-Cycle "Add New Practice Location" Flow

### Story 1.1: Add Concierge Question to Off-Cycle Submission

**As a** Practitioner submitting an Off-Cycle request to add a new practice location  
**I want** to be asked if I practice concierge medicine at the new location  
**So that** my concierge status is captured and can be activated after PDA review

---

### Acceptance Criteria

#### AC 1.1.1: Concierge Question Appears After Practice Location Entry

**Given** I am in the Off-Cycle guided flow (`PRM_OffCycleCredentialing_English`)  
**When** I select "Click here to add a location not listed" from the Group Selection screen  
**And** I enter the new practice location details (Address, Phone, etc.)  
**And** I complete Precisely API validation  
**Then** a new question should appear: **"Do you practice concierge medicine at this Practice Location?"**  
**With** Radio button options: Yes / No  
**And** this question should appear AFTER address entry and BEFORE final submission  
**And** this question should be REQUIRED (cannot proceed without answering)

**Location:** After `PRM_OffCyclePreciselyAPI` validation step

---

#### AC 1.1.2: Data Capture on Case Manager

**Given** I have answered the concierge question  
**When** I submit the Off-Cycle request  
**Then** the system should save my answer on the Case Manager (IndividualApplication) record:
- `PRM_PracticesConcierge__c` = true/false

**And** this field should be visible to PDA reviewers

---

#### AC 1.1.3: Info Code Assignment Creation at PPL Level

**Given** I answered "Yes" to "Do you practice concierge medicine at this Practice Location?"  
**When** I submit the Off-Cycle request  
**And** the system creates the HealthcarePractitionerFacility (PPL) record for the new location  
**Then** the system should create a `PRM_InfoCodeAssignment__c` record with:
- `PRM_InfoCode__c` = "Concierge Provider" (lookup by name)
- `PRM_PractitionerFacilityAssignment__c` = [Newly created PPL Id]
- `PRM_EffectiveDate__c` = [Application submission date / PPL effective from date]
- `PRM_Pending__c` = TRUE (not yet active)
- `PRM_CaseManager__c` = [Off-Cycle Case Manager Id]
- `PRM_TerminationDate__c` = null (new assignment)
- `PRM_Account__c` = null (PPL level, not practitioner level)
- `PRM_HealthcareFacility__c` = null (PPL level, not location level)

**Given** I answered "No" to concierge question  
**Then** NO Info Code Assignment should be created

---

#### AC 1.1.4: Boolean Checkbox Update on PPL

**Given** an Info Code Assignment was created for the PPL  
**When** the assignment is created with `PRM_Pending__c = true`  
**Then** a trigger should set:
- `HealthcarePractitionerFacility.PRM_IsConciergeProvider__c` = TRUE

**Note:** This boolean checkbox is for reporting/quick lookups; the Info Code Assignment is the source of truth

---

#### AC 1.1.5: Multiple Practice Locations Scenario

**Given** I am adding 3 new practice locations in a single Off-Cycle request  
**When** I complete the flow  
**Then** I should be asked the concierge questions for EACH practice location individually  
**And** I can answer "Yes" for some locations and "No" for others  
**And** Info Code Assignments should be created only for locations where I answered "Yes"

**Example:**
- Location A (123 Main St): Concierge = Yes → Create assignment
- Location B (456 Oak Ave): Concierge = No → No assignment
- Location C (789 Pine Rd): Concierge = Yes → Create assignment

**Result:** 2 Info Code Assignments created (Locations A and C), 1 PPL without assignment (Location B)

---

### Technical Implementation Details

#### OmniScript Changes

**File:** `PRM_OffCycleCredentialing_English`

**New Elements to Add:**

1. **ConciergeQuestion** (Radio Group)
   - **Label:** "Do you practice concierge medicine at this Practice Location?"
   - **Required:** true
   - **Options:** Yes | No
   - **Variable:** `PracticesConcierge`
   - **Show If:** `newPracLoc = true` (adding new practice location)
   - **Location:** After Precisely validation step

2. **SetConciergeData** (Set Values)
   - **Purpose:** Map answer to Case Manager field
   - **Mappings:**
     ```
     CaseManagerConciergeData.PRM_PracticesConcierge__c = %PracticesConcierge% == "Yes"
     ```

3. **IPCreateConciergeAssignment** (Integration Procedure Call) - NEW
   - **IP Name:** `PRM_CreateConciergeInfoCodeAssignment`
   - **Input:**
     ```json
     {
       "caseManagerId": "%CaseManagerId%",
       "practitionerId": "%PractitionerId%",
       "practitionerFacilityAssignmentId": "%NewPPLId%",
       "effectiveDate": "%SubmissionDate%",
       "practicesConcierge": "%PracticesConcierge%"
     }
     ```
   - **Condition:** `%PracticesConcierge% == "Yes"`

---

#### Integration Procedure: PRM_CreateConciergeInfoCodeAssignment

**Purpose:** Create Info Code Assignment at PPL level when practitioner selects concierge = Yes

**Type:** Vlocity Integration Procedure

**Input:**
```json
{
  "caseManagerId": "a2Z...",
  "practitionerId": "001...",
  "practitionerFacilityAssignmentId": "a1Y...", 
  "effectiveDate": "2026-04-07",
  "practicesConcierge": true
}
```

**Logic:**

1. **Step 1: Get Info Code Id**
   - **DataRaptor Extract:** `PRMGetInfoCodeByName`
   - **Input:** `{ "Name": "Concierge Provider" }`
   - **Output:** `InfoCodeId`

2. **Step 2: Create Info Code Assignment**
   - **DataRaptor Load:** `PRMLoadInfoCodeAssignment`
   - **Input:**
     ```json
     {
       "PRM_InfoCode__c": "%InfoCodeId%",
       "PRM_PractitionerFacilityAssignment__c": "%practitionerFacilityAssignmentId%",
       "PRM_EffectiveDate__c": "%effectiveDate%",
       "PRM_Pending__c": true,
       "PRM_CaseManager__c": "%caseManagerId%",
       "PRM_TerminationDate__c": null,
       "PRM_Account__c": null,
       "PRM_HealthcareFacility__c": null
     }
     ```
   - **Output:** `InfoCodeAssignmentId`

3. **Step 3: Return Success**
   - **Response:**
     ```json
     {
       "success": true,
       "infoCodeAssignmentId": "%InfoCodeAssignmentId%"
     }
     ```

---

#### DataRaptor: PRMGetInfoCodeByName

**Type:** Extract

**Interface:**
```
Input: { "Name": "Concierge Provider" }
Output: { "InfoCodeId": "a0X..." }
```

**Extract Definition:**
```json
{
  "Extract": [
    {
      "OutputFieldName": "InfoCodeId",
      "InputFieldName": "Id",
      "ObjectPath": "PRM_InfoCode__c",
      "Filter": "Name = 'Concierge Provider'"
    }
  ]
}
```

---

#### DataRaptor: PRMLoadInfoCodeAssignment

**Type:** Load

**Interface:**
```
Input: { PRM_InfoCode__c, PRM_PractitionerFacilityAssignment__c, ... }
Output: { Id: "a4Z..." }
```

**Load Definition:**
```json
{
  "Load": [
    {
      "ObjectPath": "PRM_InfoCodeAssignment__c",
      "Mappings": [
        { "InputFieldName": "PRM_InfoCode__c", "OutputFieldName": "PRM_InfoCode__c" },
        { "InputFieldName": "PRM_PractitionerFacilityAssignment__c", "OutputFieldName": "PRM_PractitionerFacilityAssignment__c" },
        { "InputFieldName": "PRM_EffectiveDate__c", "OutputFieldName": "PRM_EffectiveDate__c" },
        { "InputFieldName": "PRM_Pending__c", "OutputFieldName": "PRM_Pending__c" },
        { "InputFieldName": "PRM_CaseManager__c", "OutputFieldName": "PRM_CaseManager__c" },
        { "InputFieldName": "PRM_TerminationDate__c", "OutputFieldName": "PRM_TerminationDate__c" },
        { "InputFieldName": "PRM_Account__c", "OutputFieldName": "PRM_Account__c" },
        { "InputFieldName": "PRM_HealthcareFacility__c", "OutputFieldName": "PRM_HealthcareFacility__c" }
      ]
    }
  ]
}
```

---

#### Trigger: Update Boolean Checkbox on PPL

**Trigger Name:** `PRM_InfoCodeAssignmentTrigger` (After Insert, After Update)

**Handler:** `PRM_InfoCodeAssignmentTriggerHandler.updateConciergeBooleanCheckboxes()`

**Logic:**
```apex
public static void updateConciergeBooleanCheckboxes(List<PRM_InfoCodeAssignment__c> newAssignments) {
    Set<Id> pplIds = new Set<Id>();
    Set<Id> practitionerIds = new Set<Id>();
    Set<Id> locationIds = new Set<Id>();
    
    for (PRM_InfoCodeAssignment__c ica : newAssignments) {
        if (ica.PRM_InfoCode__r.Name == 'Concierge Provider') {
            if (ica.PRM_PractitionerFacilityAssignment__c != null) {
                pplIds.add(ica.PRM_PractitionerFacilityAssignment__c);
            }
            if (ica.PRM_Account__c != null) {
                practitionerIds.add(ica.PRM_Account__c);
            }
            if (ica.PRM_HealthcareFacility__c != null) {
                locationIds.add(ica.PRM_HealthcareFacility__c);
            }
        }
    }
    
    // Update PPL boolean checkbox
    if (!pplIds.isEmpty()) {
        List<HealthcarePractitionerFacility> pplsToUpdate = [
            SELECT Id, PRM_IsConciergeProvider__c
            FROM HealthcarePractitionerFacility
            WHERE Id IN :pplIds
        ];
        
        for (HealthcarePractitionerFacility ppl : pplsToUpdate) {
            // Check if there's at least one active concierge assignment
            Boolean hasActiveAssignment = [
                SELECT COUNT()
                FROM PRM_InfoCodeAssignment__c
                WHERE PRM_PractitionerFacilityAssignment__c = :ppl.Id
                AND PRM_InfoCode__r.Name = 'Concierge Provider'
                AND PRM_Pending__c = false
                AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
            ] > 0;
            
            ppl.PRM_IsConciergeProvider__c = hasActiveAssignment;
        }
        
        update pplsToUpdate;
    }
    
    // Similar logic for Practitioner and Location levels...
}
```

---

### Story 1.2: Field Access and Metadata

**As a** System Administrator  
**I want** proper field access configured for concierge-related fields  
**So that** the right users can view and edit the data

---

#### AC 1.2.1: Case Manager Field Creation

**Given** Off-Cycle flow needs to capture concierge answer  
**Then** the following field should exist on IndividualApplication:

| Field API Name | Label | Type | Default | Description |
|----------------|-------|------|---------|-------------|
| `PRM_PracticesConcierge__c` | Practices Concierge Medicine | Checkbox | false | Does practitioner practice concierge at new location? |

---

#### AC 1.2.2: Field Access Configuration

**Standard Field Access Template:**

**Read Access:**
- Credentialing Permission Set
- PDA Permission Set
- Network Management QC Permission Set

**Edit Access:**
- PRM CredentialingUser Permission Set
- PRM ProviderDataAdmin Permission Set
- PRM-NetworkManagement@C Permission Set

**View All, Read:**
- PRM DataViewAll Permission Set

**Read, Create, Edit, View All:**
- PAM-DataModifyAll Permission Set

**AND:** Notify KISHLAY + ANSHAY to add fields to SF-to-DART Metadata & Data Dictionary

---

#### AC 1.2.3: Page Layout Updates

**Given** new field is created  
**Then** add field to the following page layout:

| Page Layout | Section | Fields to Add |
|-------------|---------|---------------|
| **IndividualApplication (Off-Cycle)** | Concierge Information | PRM_PracticesConcierge__c |

---

### Effort Estimation

| Task | Effort (SP) | Notes |
|------|-------------|-------|
| **OmniScript Changes** | 2 | Add 1 question with set values (no conditional logic) |
| **Integration Procedure** | 2 | Create PRM_CreateConciergeInfoCodeAssignment (simplified) |
| **DataRaptors** | 1 | PRMGetInfoCodeByName, PRMLoadInfoCodeAssignment (fewer fields) |
| **Trigger Logic** | 1 | Update boolean checkboxes on PPL |
| **Field Creation & Access** | 1 | 1 field on IndividualApplication, field-level security |
| **Testing** | 1 | Unit tests, integration tests, UAT |
| **TOTAL** | **8 SP** | |

---

## Story 2: Update Off-Cycle PDA Review to Activate Info Code Assignments

### Story 2.1: Activate Concierge Assignments After Case Approval

**As a** PDA Reviewer  
**I want** Info Code Assignments created during Off-Cycle submission to be activated after I approve the case  
**So that** the practitioner's concierge status is reflected in Provider Directory and DART feeds

---

### Acceptance Criteria

#### AC 2.1.1: PDA Review Flow Activates All 3 Levels

**Given** an Off-Cycle case has been approved by Committee  
**And** the case has pending Info Code Assignments at PPL level with `PRM_Pending__c = true`  
**When** the PDA Review and Update flow runs  
**Then** the system should query and activate Info Code Assignments at ALL 3 LEVELS:
- **Level 1:** Practitioner level (`PRM_Account__c`)
- **Level 2:** Practice Location level (`PRM_HealthcareFacility__c`)
- **Level 3:** Practitioner Practice Location level (`PRM_PractitionerFacilityAssignment__c`) ⬅️ **CRITICAL**

**And** for each assignment found, set `PRM_Pending__c = false`

---

#### AC 2.1.2: Query Logic for All 3 Levels

**Current Query (INCOMPLETE - MISSING PPL LEVEL):**
```apex
List<PRM_InfoCodeAssignment__c> assignments = [
    SELECT Id, PRM_Pending__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
    AND (PRM_Account__c IN :practitionerAccIds
         OR PRM_HealthcareFacility__c IN :facilityIds)
];
// ❌ MISSING: PRM_PractitionerFacilityAssignment__c
```

**REQUIRED QUERY (CORRECT - ALL 3 LEVELS):**
```apex
// Step 1: Get PPL Ids
Set<Id> pplIds = new Set<Id>();
for (HealthcarePractitionerFacility ppl : [
    SELECT Id 
    FROM HealthcarePractitionerFacility
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
]) {
    pplIds.add(ppl.Id);
}

// Step 2: Query all 3 levels
List<PRM_InfoCodeAssignment__c> assignments = [
    SELECT Id, PRM_Pending__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
    AND PRM_IsErrorRecord__c = false
    AND (PRM_Account__c IN :practitionerAccIds
         OR PRM_HealthcareFacility__c IN :facilityIds
         OR PRM_PractitionerFacilityAssignment__c IN :pplIds)  ⬅️ ADDED
];

// Step 3: Activate assignments
for (PRM_InfoCodeAssignment__c ica : assignments) {
    ica.PRM_Pending__c = false; // ACTIVE
}
update assignments;
```

---

#### AC 2.1.3: Use Reusable Utility Class

**Given** we have a reusable `PRM_InfoCodeAssignmentUtility` class  
**When** the Off-Cycle PDA Review flow needs to activate assignments  
**Then** it should call:
```apex
PRM_InfoCodeAssignmentUtility.activateAssignments(caseManagerId);
```

**Instead of** inline query logic (for consistency across all flows)

---

#### AC 2.1.4: Boolean Checkbox Updates After Activation

**Given** Info Code Assignments have been activated (`PRM_Pending__c = false`)  
**When** the activation completes  
**Then** the trigger should update boolean checkboxes:
- `HealthcarePractitionerFacility.PRM_IsConciergeProvider__c` = true (if has active assignment)
- `Account.PRM_IsConciergeProvider__c` = true (if practitioner has active assignment)
- `HealthcareFacility.PRM_IsConciergeProvider__c` = true (if location has active assignment)

---

#### AC 2.1.5: Multiple Assignments Scenario

**Given** an Off-Cycle case has 3 new practice locations:
- Location A: Concierge = Yes (assignment created, pending)
- Location B: Concierge = No (no assignment)
- Location C: Concierge = Yes (assignment created, pending)

**When** PDA Review activates assignments  
**Then** the system should:
- Activate assignment for Location A (`PRM_Pending__c = false`)
- Activate assignment for Location C (`PRM_Pending__c = false`)
- NOT create or update anything for Location B (no assignment exists)

**Result:** 2 active assignments, 1 PPL without concierge status

---

### Technical Implementation Details

#### Off-Cycle PDA Review Flow

**Flow Name:** `PRM_OffCyclePDAReviewUpdate` (Integration Procedure) OR uses PNC flow

**Current Integration:**
- Off-Cycle may use the same PDA flow as PNC: `PRM_PNCPDAReviewUpdate`
- OR have its own Off-Cycle-specific PDA flow

**Required Change:**

**Option A: If Off-Cycle uses PRM_PNCPDAReviewUpdate:**
- Update `PRM_PNCPDAReviewUpdate` to call utility class (already covered in PNC user stories)

**Option B: If Off-Cycle has separate PDA flow:**
- Add new Integration Procedure step: `ActivateInfoCodeAssignments`
- Call `PRM_InfoCodeAssignmentUtility.activateAssignments(caseManagerId)` via Apex Remote Action

---

#### Utility Class: PRM_InfoCodeAssignmentUtility

**Method:** `activateAssignments`

**Signature:**
```apex
public static void activateAssignments(Id caseManagerId)
```

**Implementation:**
```apex
public static void activateAssignments(Id caseManagerId) {
    // Get practitioner and facility Ids
    Set<Id> practitionerAccIds = new Set<Id>();
    Set<Id> facilityIds = new Set<Id>();
    Set<Id> pplIds = new Set<Id>();
    
    // Query Case Manager
    IndividualApplication cm = [
        SELECT Id, PRM_Account__c
        FROM IndividualApplication
        WHERE Id = :caseManagerId
        LIMIT 1
    ];
    
    if (cm.PRM_Account__c != null) {
        practitionerAccIds.add(cm.PRM_Account__c);
    }
    
    // Get PPL Ids and Facility Ids
    for (HealthcarePractitionerFacility ppl : [
        SELECT Id, FacilityId
        FROM HealthcarePractitionerFacility
        WHERE PRM_CaseManager__c = :caseManagerId
        AND PRM_Pending__c = true
    ]) {
        pplIds.add(ppl.Id);
        if (ppl.FacilityId != null) {
            facilityIds.add(ppl.FacilityId);
        }
    }
    
    // Query all 3 levels
    List<PRM_InfoCodeAssignment__c> assignments = [
        SELECT Id, PRM_Pending__c
        FROM PRM_InfoCodeAssignment__c
        WHERE PRM_CaseManager__c = :caseManagerId
        AND PRM_Pending__c = true
        AND PRM_IsErrorRecord__c = false
        AND (PRM_Account__c IN :practitionerAccIds
             OR PRM_HealthcareFacility__c IN :facilityIds
             OR PRM_PractitionerFacilityAssignment__c IN :pplIds)
    ];
    
    // Activate assignments
    for (PRM_InfoCodeAssignment__c ica : assignments) {
        ica.PRM_Pending__c = false; // ACTIVE
    }
    
    if (!assignments.isEmpty()) {
        update assignments;
    }
}
```

---

### Effort Estimation

| Task | Effort (SP) | Notes |
|------|-------------|-------|
| **Update PDA Review Flow** | 3 | Add utility class call to Off-Cycle PDA Review |
| **Utility Class Extension** | 2 | Extend activateAssignments to handle Off-Cycle case type |
| **Integration Testing** | 2 | Test activation flow end-to-end |
| **UAT** | 1 | PDA team validation |
| **TOTAL** | **8 SP** | |

---

## Story 3: Update Off-Cycle Case Denial to Deny Info Code Assignments

### Story 3.1: Mark Concierge Assignments as Denied When Case Denied

**As a** PDA Reviewer  
**I want** Info Code Assignments created during Off-Cycle submission to be marked as denied when I deny the case  
**So that** denied assignments do not feed to Provider Directory or DART

---

### Acceptance Criteria

#### AC 3.1.1: Case Denial Updates All 3 Levels

**Given** an Off-Cycle case has pending Info Code Assignments with `PRM_Pending__c = true`  
**When** the case is denied via Close Case flow or denial path  
**Then** the system should query and deny Info Code Assignments at ALL 3 LEVELS:
- **Level 1:** Practitioner level (`PRM_Account__c`)
- **Level 2:** Practice Location level (`PRM_HealthcareFacility__c`)
- **Level 3:** Practitioner Practice Location level (`PRM_PractitionerFacilityAssignment__c`) ⬅️ **CRITICAL**

**And** for each assignment found, set `PRM_Pending__c = false` (denied, not active)

---

#### AC 3.1.2: Denial Logic Uses Utility Class

**Given** we have a reusable `PRM_InfoCodeAssignmentUtility` class  
**When** the Off-Cycle case is denied  
**Then** the system should call:
```apex
PRM_InfoCodeAssignmentUtility.denyAssignments(caseManagerId);
```

**Logic should be identical to activateAssignments, except:**
- `PRM_Pending__c = false` means DENIED (not active)
- Case status indicates denial
- No further activation possible

---

#### AC 3.1.3: Extend Case Manager Denial Utility

**Given** `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` exists for PAR/PNC  
**When** it is called for an Off-Cycle case  
**Then** it should also update Info Code Assignments (same as PNC)

**Current objects updated (from Close_Case_PNC_Ancillary_User_Stories.md):**
- HealthcarePractitionerFacility
- HealthcareFacility
- HealthcareFacilityNetwork
- Address, Location
- Identifier, HealthcareProvider, HealthcareProviderNpi, HealthcareProviderTaxonomy
- Account (Practitioner + Vendor for PNC/Off-Cycle)
- PRM_ProviderFeature__c
- **PRM_InfoCodeAssignment__c** ⬅️ **MUST BE ADDED**

---

#### AC 3.1.4: Query Logic for Denial (All 3 Levels)

**Same as Story 2.1.2, but for denial:**

```apex
// Call utility class
PRM_InfoCodeAssignmentUtility.denyAssignments(caseManagerId);
```

**Utility method implementation:**
```apex
public static void denyAssignments(Id caseManagerId) {
    // Same query logic as activateAssignments
    // ...get practitionerAccIds, facilityIds, pplIds...
    
    List<PRM_InfoCodeAssignment__c> assignments = [
        SELECT Id, PRM_Pending__c
        FROM PRM_InfoCodeAssignment__c
        WHERE PRM_CaseManager__c = :caseManagerId
        AND PRM_Pending__c = true
        AND PRM_IsErrorRecord__c = false
        AND (PRM_Account__c IN :practitionerAccIds
             OR PRM_HealthcareFacility__c IN :facilityIds
             OR PRM_PractitionerFacilityAssignment__c IN :pplIds)
    ];
    
    // Mark as denied (not active)
    for (PRM_InfoCodeAssignment__c ica : assignments) {
        ica.PRM_Pending__c = false; // DENIED (not active)
    }
    
    if (!assignments.isEmpty()) {
        update assignments;
    }
}
```

**Note:** Both activation and denial set `PRM_Pending__c = false`. The difference is the **Case status** (Approved vs Denied) determines whether the assignment is active or denied.

---

### Technical Implementation Details

#### Update PRM_CaseManagerDenialUtility

**Method:** `updatePendingCheckboxOnDenial`

**Current Logic:** Updates 14+ objects when case is denied

**Required Change:** Add Info Code Assignment logic

**Addition to Line ~193 of Close_Case_PNC_Ancillary_User_Stories.md:**

```apex
// Add to existing denial logic:

// 15. PRM_InfoCodeAssignment__c
PRM_InfoCodeAssignmentUtility.denyAssignments(caseManagerId);
```

**Integration:**
- `PRM_CaseManagerDenialUtility` is called by:
  - `PRM_ReviewParCaseRecordsUpdate` (PAR)
  - `PRM_PNCRecordsUpdate` (PNC)
  - Off-Cycle denial flow (verify which IP calls it)
- Extend to handle Off-Cycle Record Type if not already supported

---

### Effort Estimation

| Task | Effort (SP) | Notes |
|------|-------------|-------|
| **Update Denial Utility** | 2 | Add Info Code Assignment denial logic |
| **Utility Class Extension** | 1 | Add denyAssignments method |
| **Integration Testing** | 1 | Test denial flow end-to-end |
| **UAT** | 1 | PDA team validation |
| **TOTAL** | **5 SP** | |

---

## End-to-End Flow Diagram

### Off-Cycle with Concierge Medicine (Complete Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Off-Cycle Submission (Practitioner)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Practitioner logs in, launches PRM_OffCycleCredentialing_English        │
│ 2. Enters NPI + Tax ID → Provider Search                                    │
│ 3. Group Selection:                                                          │
│    - Selects Main Group (single-select)                                     │
│    - Selects Additional Addresses (multi-select, max 10)                   │
│    - OR clicks "Click here to add a location not listed"                   │
│ 4. IF adding new location:                                                  │
│    - Enters address (Primary, Mailing, Billing)                            │
│    - Precisely API validation                                               │
│    - Duplicate address check                                                │
│    ► NEW: Concierge Question Appears                                        │
│      Q: "Do you practice concierge medicine at this Practice Location?"   │
│ 5. Submits Off-Cycle request                                               │
│                                                                              │
│ RECORDS CREATED:                                                            │
│ ├─ Case (Status = Pending)                                                 │
│ ├─ IndividualApplication (Case Manager, RecordType = Off-Cycle)           │
│ │   └─ PRM_PracticesConcierge__c = true/false                             │
│ ├─ HealthcarePractitionerFacility (PPL, PRM_Pending__c = true)            │
│ └─ PRM_InfoCodeAssignment__c (IF answer = Yes):                           │
│     ├─ PRM_InfoCode__c = "Concierge Provider"                             │
│     ├─ PRM_PractitionerFacilityAssignment__c = [PPL Id]                   │
│     ├─ PRM_Pending__c = TRUE (not yet active)                             │
│     ├─ PRM_CaseManager__c = [Case Manager Id]                             │
│     └─ PRM_EffectiveDate__c = [Submission date]                           │
│                                                                              │
│ ├─ Trigger fires: HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = TRUE │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Committee Review                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ - Case routes through review steps                                          │
│ - Committee reviews and APPROVES case                                       │
│ - NO CHANGES to Info Code Assignments (still PRM_Pending__c = true)        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3A: PDA Review and Update (APPROVAL PATH)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Flow: PRM_OffCyclePDAReviewUpdate (or PRM_PNCPDAReviewUpdate)             │
│                                                                              │
│ ► CRITICAL STEP: Activate Info Code Assignments                            │
│   1. Call: PRM_InfoCodeAssignmentUtility.activateAssignments(caseManagerId)│
│   2. Utility queries ALL 3 LEVELS:                                         │
│      - Practitioner level (PRM_Account__c)                                 │
│      - Practice Location level (PRM_HealthcareFacility__c)                 │
│      - Practitioner Practice Location level (PRM_PractitionerFacilityAssignment__c) ⬅️ ADDED │
│   3. For each assignment found: PRM_Pending__c = FALSE (ACTIVE)           │
│   4. Update assignments                                                     │
│                                                                              │
│ RECORDS UPDATED:                                                            │
│ ├─ PRM_InfoCodeAssignment__c (PPL level):                                 │
│ │   └─ PRM_Pending__c = FALSE (ACTIVE)                                    │
│ ├─ HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = TRUE       │
│ ├─ Account.PRM_IsConciergeProvider__c = TRUE (if practitioner has assignment)│
│ └─ HealthcareFacility (all other records activated as per PNC flow)       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3B: Case Denial (DENIAL PATH - ALTERNATIVE)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Flow: PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial          │
│                                                                              │
│ ► CRITICAL STEP: Deny Info Code Assignments                                │
│   1. Call: PRM_InfoCodeAssignmentUtility.denyAssignments(caseManagerId)   │
│   2. Utility queries ALL 3 LEVELS (same as activation)                     │
│   3. For each assignment found: PRM_Pending__c = FALSE (DENIED)           │
│   4. Update assignments                                                     │
│                                                                              │
│ RECORDS UPDATED:                                                            │
│ ├─ PRM_InfoCodeAssignment__c (PPL level):                                 │
│ │   └─ PRM_Pending__c = FALSE (DENIED, not active)                        │
│ ├─ Case.Status = Closed, PRM_DenialReason__c = [reason]                  │
│ ├─ IndividualApplication.Status = Denied                                  │
│ └─ All other pending records updated (per PNC denial logic)               │
│                                                                              │
│ ► Result: Assignments NOT ACTIVE, will not feed to Provider Directory     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ RESULT: Active Concierge Info Code Assignments                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Query for Active Assignments:                                              │
│   SELECT Id, PRM_PractitionerFacilityAssignment__c, PRM_EffectiveDate__c  │
│   FROM PRM_InfoCodeAssignment__c                                           │
│   WHERE PRM_InfoCode__r.Name = 'Concierge Provider'                       │
│   AND PRM_Pending__c = false                                               │
│   AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)   │
│                                                                              │
│ ► Ready to feed to Provider Directory / DART                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Test Scenarios

### Scenario 1: Off-Cycle Add Location - Concierge Yes (Happy Path)

**Given:** Dr. Smith submits Off-Cycle request to add 1 new practice location  
**When:** Dr. Smith answers "Yes" to "Do you practice concierge medicine at this Practice Location?"  
**And:** Case is approved by Committee  
**And:** PDA Review and Update runs  
**Then:**
- ✅ Info Code Assignment created with PRM_Pending__c = true at submission
- ✅ Assignment activated (PRM_Pending__c = false) after PDA Review
- ✅ HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = true
- ✅ PRM_PracticesConcierge__c = true on Case Manager
- ✅ Assignment feeds to Provider Directory

---

### Scenario 2: Off-Cycle Add Location - Concierge No

**Given:** Dr. Johnson submits Off-Cycle request to add 1 new practice location  
**When:** Dr. Johnson answers "No" to concierge medicine  
**And:** Case is approved  
**Then:**
- ✅ NO Info Code Assignment created
- ✅ HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = false
- ✅ No concierge status in Provider Directory

---

### Scenario 3: Off-Cycle Add Multiple Locations - Mixed Answers

**Given:** Dr. Lee submits Off-Cycle request to add 3 new practice locations  
**When:** Dr. Lee answers:
- Location A (123 Main St): Concierge = Yes
- Location B (456 Oak Ave): Concierge = No
- Location C (789 Pine Rd): Concierge = Yes  
**And:** Case is approved  
**Then:**
- ✅ 2 Info Code Assignments created (Locations A and C)
- ✅ Both activated after PDA Review
- ✅ Location B has no concierge assignment
- ✅ Provider Directory shows concierge for A and C only

---

### Scenario 4: Off-Cycle Add Location - Case Denied

**Given:** Dr. Brown submits Off-Cycle request to add 1 new practice location with concierge = Yes  
**When:** Case is DENIED by Committee  
**And:** Denial utility runs  
**Then:**
- ✅ Info Code Assignment has PRM_Pending__c = false (denied)
- ✅ Assignment NOT active (does not feed to Provider Directory)
- ✅ Case.Status = Closed, PRM_DenialReason__c populated
- ✅ IndividualApplication.Status = Denied

---

### Scenario 5: Off-Cycle - Missing PPL Level in Query (Regression Test)

**Given:** Off-Cycle PDA Review flow uses OLD query (only 2 levels)  
**When:** Practitioner adds location with concierge = Yes  
**And:** Case is approved  
**Then:**
- ❌ **BUG:** Assignment remains PRM_Pending__c = true (never activated)
- ❌ **BUG:** Provider Directory does not show concierge status
- ❌ **ROOT CAUSE:** Query missing PRM_PractitionerFacilityAssignment__c level

**Expected Fix:**
- ✅ Update query to include ALL 3 LEVELS
- ✅ Assignment activates correctly

---

## Summary Table: All Changes Required

| Component | Type | Change | Effort (SP) |
|-----------|------|--------|-------------|
| **PRM_OffCycleCredentialing_English** | OmniScript | Add 1 concierge question (simple radio button) | 2 |
| **PRM_CreateConciergeInfoCodeAssignment** | Integration Procedure | NEW - Create Info Code Assignment at PPL level | 2 |
| **PRMGetInfoCodeByName** | DataRaptor Extract | NEW - Get Info Code Id by name | 1 |
| **PRMLoadInfoCodeAssignment** | DataRaptor Load | NEW - Create Info Code Assignment record | - |
| **PRM_InfoCodeAssignmentTrigger** | Apex Trigger | Update boolean checkboxes on PPL/Account/Facility | 1 |
| **IndividualApplication Fields** | Salesforce Fields | Create 1 field (PRM_PracticesConcierge__c) | 1 |
| **PRM_OffCyclePDAReviewUpdate** | Integration Procedure | Add utility class call to activate assignments | 3 |
| **PRM_InfoCodeAssignmentUtility** | Apex Class | activateAssignments + denyAssignments methods | 3 |
| **PRM_CaseManagerDenialUtility** | Apex Class | Add Info Code Assignment denial logic | 2 |
| **Testing** | Integration Tests | End-to-end tests for all 5 scenarios | 6 |
| **TOTAL** | | | **21 SP** |

---

## Dependencies

### Upstream Dependencies (Must Complete First)

| Story | Dependency | Reason |
|-------|------------|--------|
| **Story 1** | Epic 1 (Core Infrastructure) | Info Code "Concierge Provider" must exist |
| **Story 1** | Story 1.6 (Boolean Checkboxes) | PRM_IsConciergeProvider__c field on PPL |
| **Story 1** | Story 1.7 (Trigger Logic) | Trigger to update boolean checkboxes |
| **Story 2** | Epic 2 (Utility Class) | PRM_InfoCodeAssignmentUtility must exist |
| **Story 3** | Story 2 | Denial utility extends activation utility |

### Downstream Dependencies (Blocked By This Epic)

| Epic | Blocked By | Impact |
|------|------------|--------|
| **Provider Directory Feed** | Story 2 (Activation) | Cannot show concierge status until assignments activated |
| **DART Analytics** | Story 2 (Activation) | Cannot report concierge providers until data is active |
| **Recredentialing** | Story 1 (Questions) | Recred may need similar questions for location changes |

---

## Risks and Mitigations

### Risk 1: Off-Cycle May Use Different PDA Flow Than PNC

**Risk:** Off-Cycle may have a separate PDA flow, requiring duplicate changes  
**Likelihood:** Medium  
**Impact:** High (duplicate effort)  
**Mitigation:**
- ✅ Verify during Sprint Planning whether Off-Cycle uses PRM_PNCPDAReviewUpdate or separate flow
- ✅ If separate, allocate additional 3 SP for second PDA flow update
- ✅ Recommend consolidating PDA flows if possible (long-term)

---

### Risk 2: Case Manager Record Type Differences

**Risk:** Off-Cycle may have different Record Type, causing utility class to skip  
**Likelihood:** Low  
**Impact:** High (feature completely broken)  
**Mitigation:**
- ✅ Verify IndividualApplication Record Type for Off-Cycle (PRM_OffCycle or similar)
- ✅ Ensure utility class handles ALL case types: PAR, PNC, Recred, Off-Cycle
- ✅ Add unit tests for each Record Type

---

### Risk 3: Precisely API Validation May Fail with Concierge Questions

**Risk:** Adding questions may break Precisely validation timing  
**Likelihood:** Low  
**Impact:** Medium (address validation fails)  
**Mitigation:**
- ✅ Place concierge questions AFTER Precisely validation completes
- ✅ Test Precisely API integration in Sandbox before deployment
- ✅ Add error handling if API times out

---

## Next Steps

1. **Sprint Planning:**
   - Allocate Story 1 to Sprint 3 (8 SP)
   - Allocate Stories 2-3 to Sprint 4 (13 SP)
   - Total: 21 SP across 2 sprints

2. **Technical Design Review:**
   - Verify Off-Cycle PDA flow (same as PNC or separate?)
   - Review OmniScript structure and placement of concierge questions
   - Confirm IndividualApplication Record Type

3. **Development:**
   - Story 1: OmniScript changes + Integration Procedure
   - Story 2: PDA Review update + Utility class
   - Story 3: Denial utility update

4. **Testing:**
   - Unit tests for utility class (90%+ coverage)
   - Integration tests for all 5 scenarios
   - UAT with PDA team

5. **Deployment:**
   - Deploy to Sandbox for UAT
   - Production deployment after P0 flows (Initial Cred, PNC, Recred) completed

---

**End of Document**
