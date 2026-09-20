# Person Education Empty Fields - Root Cause Analysis

## Executive Summary

**Issue:** PersonEducation records are being created with NULL values for Institution, Start Date, and End Date despite these fields being marked as required on the UI in the Application Review guided flow.

**Date:** 2026-04-22  
**Severity:** HIGH  
**Impact:** Data integrity violation - practitioners with incomplete education records

---

## Issue Description

Business users have reported that PersonEducation records are being saved with:
- **PRM_Institution__c** = NULL
- **PRM_StartDate__c** = NULL  
- **PRM_EndDate__c** = NULL

This occurs even though the UI shows all three fields as **required** in the Application Review OmniScript.

---

## Technical Architecture Overview

### Current Flow Path

```
Application Review OmniScript (PRM_InitialCredentialAppReview_English)
  ↓
CredApplicationReviewSubOS (Step: VerifyEducation)
  ↓
CAQHPersonEducation Edit Block (CAQH data display)
  ↓
User fills fields (Institution, Start Date, End Date marked as required)
  ↓
Final Submit triggers Integration Procedure
  ↓
PRM_ReviewPSVCaseRecordsUpdate
  ↓
CBLogicPersonEducation (Conditional Block)
  ↓
RACompPersonEducation (Remote Action - deduplication logic)
  ↓
LAMergePersonEducation (List Merge)
  ↓
DRLoadPersonEducation (DataRaptor Post Action)
  ↓
PRMLoadPersonEducation DataRaptor
  ↓
PersonEducation record INSERT/UPSERT
```

---

## Root Cause Analysis

### 1. **UI Field Requirements Are NOT Database Constraints**

**Finding:** The OmniScript fields are marked as `required: true` at the UI level, but this does NOT translate to database-level enforcement.

**Evidence from Code:**

#### OmniScript Field: `EduStartDateSF`
```json
{
  "Type": "Date",
  "PropertySetConfig": {
    "label": "Start Date",
    "required": true,
    "dateFormat": "MM/dd/yyyy"
  }
}
```

#### OmniScript Field: `EduEndDateSF`
```json
{
  "Type": "Date",
  "PropertySetConfig": {
    "label": "End Date",
    "required": true,
    "dateFormat": "MM/dd/yyyy"
  }
}
```

#### OmniScript Field: `PersonInstitutionName`
```json
{
  "Type": "Type Ahead Block",
  "PropertySetConfig": {
    "label": "Institution Name",
    "required": true,
    "typeAheadKey": "Name"
  }
}
```

**The Problem:**
- These `required: true` flags only prevent the user from clicking "Next" if fields are empty
- However, they do NOT prevent data from being passed to the Integration Procedure if:
  - User bypasses validation somehow
  - Save-for-later is used (partial save)
  - Data is manipulated in browser console/developer tools
  - Backend logic merges partial data

---

### 2. **DataRaptor Has NO Required Field Validation**

**Finding:** The `PRMLoadPersonEducation` DataRaptor that creates PersonEducation records does NOT enforce required fields.

**Evidence from DataRaptor Configuration:**

All fields in the DataRaptor have:
```json
{
  "IsRequiredForUpsert": false
}
```

Specifically:

**Institution Mapping (Lines 344-365):**
```json
{
  "InputFieldName": "PersonEducation:InstitutionId",
  "OutputFieldName": "PRM_Institution__c",
  "IsRequiredForUpsert": false,
  "IsDisabled": false
}
```

**Start Date Mapping (Lines 366-388):**
```json
{
  "InputFieldName": "PersonEducation:EduStartDateSF",
  "OutputFieldName": "PRM_StartDate__c",
  "IsRequiredForUpsert": false,
  "IsDisabled": false
}
```

**End Date Mapping (Lines 322-343):**
```json
{
  "InputFieldName": "PersonEducation:EduEndDateSF",
  "OutputFieldName": "PRM_EndDate__c",
  "IsRequiredForUpsert": false,
  "IsDisabled": false
}
```

**Impact:**
- If `PersonEducation:InstitutionId` is NULL or missing from the input JSON, the DataRaptor will create a record with `PRM_Institution__c = NULL`
- Same applies to `EduStartDateSF` and `EduEndDateSF`
- No error is thrown, the record is silently created with NULL values

---

### 3. **Institution Lookup Logic Can Return NULL**

**Finding:** The Institution ID resolution logic can fail silently and pass NULL to the DataRaptor.

**Evidence from DataRaptor Formula (Lines 98-121):**

```json
{
  "FormulaExpression": "QUERY(\"SELECT ID FROM PRM_Institution__c WHERE NAME = '{0}' LIMIT 1\",%PersonEducation:InstitutionName%)",
  "FormulaResultPath": "InsitutionId",
  "FormulaSequence": 4
}
```

Then this is used:
```json
{
  "FormulaExpression": "IF(ISNOTBLANK(%PersonEducation:CAQHInstitution-Block:Id%),%PersonEducation:CAQHInstitution-Block:Id%,%InsitutionId%)",
  "FormulaResultPath": "PersonEducation:InstitutionId",
  "FormulaSequence": 5
}
```

**Failure Scenarios:**

| Scenario | Input | QUERY Result | Final InstitutionId | Record Created |
|----------|-------|--------------|---------------------|----------------|
| Happy Path | InstitutionName = "Harvard Medical School" | `a2y001` | `a2y001` | ✅ Valid |
| Typo in Name | InstitutionName = "Harvardd Medical School" | `NULL` | `NULL` | ❌ Invalid Record |
| Empty String | InstitutionName = "" | `NULL` | `NULL` | ❌ Invalid Record |
| User clears field | InstitutionName not sent | `NULL` | `NULL` | ❌ Invalid Record |
| Manual entry not in DB | InstitutionName = "New School" | `NULL` | `NULL` | ❌ Invalid Record |

**The Problem:**
- If the QUERY finds no matching institution, it returns NULL
- The DataRaptor proceeds to create a PersonEducation record with NULL Institution
- No validation error is raised

---

### 4. **No Server-Side Validation in Integration Procedure**

**Finding:** The `PRM_ReviewPSVCaseRecordsUpdate` Integration Procedure has NO validation step before calling the DataRaptor.

**Flow Elements Analyzed:**

1. **CBLogicPersonEducation** (Conditional Block):
   - Execution condition: `ISNOTBLANK(%RecordsToUpdate:PersonEducation%)`
   - Only checks if PersonEducation array exists, NOT if it has required fields

2. **RACompPersonEducation** (Remote Action):
   - Calls `PRM_OmniUtils.genericListComparison`
   - Used for deduplication logic
   - Does NOT validate required fields

3. **LAMergePersonEducation** (List Merge):
   - Merges existing education with new records
   - No validation logic

4. **DRLoadPersonEducation** (DataRaptor Call):
   - Execution condition: `ISNOTBLANK(%PersonEducation%) || ISNOTBLANK(%DRTransPSVNOCAQHData:PersonEducation|1:EducationId%)`
   - This condition is TRUE even if required fields are NULL
   - No field-level validation

**Missing Validation:**
There is NO step that checks:
```javascript
// This validation does NOT exist
IF(
  ISBLANK(%PersonEducation:InstitutionId%) || 
  ISBLANK(%PersonEducation:EduStartDateSF%) || 
  ISBLANK(%PersonEducation:EduEndDateSF%)
) {
  THROW ERROR or SKIP RECORD
}
```

---

### 5. **Salesforce Object Has NO Validation Rules**

**Finding:** The PersonEducation object itself has NO validation rules enforcing required fields.

**Evidence:**
- Searched for validation rules: None found
- Layout shows fields as "Readonly" (Lines 18-66 of layout XML)
- No required field markers at object level

**Database Schema (Inferred from Layout):**
- `PRM_Institution__c` - Lookup field (optional)
- `PRM_StartDate__c` - Date field (optional)
- `PRM_EndDate__c` - Date field (optional)

**The Problem:**
Since there are no Salesforce validation rules, the database accepts:
```sql
INSERT INTO PersonEducation (
  ContactId = '003xxx',
  HealthcareProviderId = '001xxx',
  Name = 'MD',
  PRM_Institution__c = NULL,        -- Allowed!
  PRM_StartDate__c = NULL,          -- Allowed!
  PRM_EndDate__c = NULL             -- Allowed!
)
```

---

## How Invalid Records Are Created - Attack Vectors

### Scenario 1: Type-Ahead Institution Name Mismatch
```
1. User types "Harvard Med School" in Type-Ahead
2. No exact match in PRM_Institution__c.Name
3. User thinks it's valid and proceeds
4. QUERY returns NULL
5. Record created with Institution = NULL
```

### Scenario 2: User Clears Required Fields
```
1. User loads education record from CAQH
2. Fields are pre-populated
3. User accidentally clears Start Date or End Date
4. OmniScript validation might not trigger if other validations pass
5. NULL values sent to Integration Procedure
6. Record created with NULL dates
```

### Scenario 3: Save-for-Later Incomplete Data
```
1. User starts filling education section
2. Clicks "Save for Later" with partial data
3. OmniScript stores incomplete JSON
4. User resumes later, somehow bypasses validation
5. Integration Procedure receives incomplete data
6. DataRaptor creates record with NULLs
```

### Scenario 4: Browser Developer Tools Manipulation
```
1. Malicious or curious user opens browser console
2. Modifies JSON payload to remove required fields
3. Submits form
4. Server has no validation
5. Invalid record created
```

### Scenario 5: Integration Procedure Called Directly
```
1. Some other automation (Flow, Apex, etc.) calls PRM_ReviewPSVCaseRecordsUpdate
2. Passes incomplete PersonEducation data
3. No validation in IP
4. Invalid record created
```

---

## Gap Analysis

| Layer | Expected Validation | Actual Validation | Gap |
|-------|---------------------|-------------------|-----|
| **UI (OmniScript)** | Required fields block "Next" button | ✅ Implemented | ⚠️ Client-side only, bypassable |
| **Integration Procedure** | Validate required fields before DataRaptor | ❌ NOT Implemented | 🔴 **CRITICAL GAP** |
| **DataRaptor** | Mark fields as `IsRequiredForUpsert: true` | ❌ NOT Implemented | 🔴 **CRITICAL GAP** |
| **Salesforce Object** | Validation Rules on PersonEducation | ❌ NOT Implemented | 🔴 **CRITICAL GAP** |
| **Database Constraints** | NOT NULL constraints on fields | ❌ NOT Implemented | 🔴 **CRITICAL GAP** |

---

## Why The UI Shows "Required" But Records Still Get Created

### The Validation Chain Is Broken

```
┌──────────────────────────────────────────────────────────────┐
│                    VALIDATION LAYERS                         │
├──────────────────────────────────────────────────────────────┤
│ Layer 1: UI (OmniScript)                                    │
│   Status: ✅ Required = true                                 │
│   Weakness: Client-side only, can be bypassed               │
│   ▼▼▼                                                        │
│                                                              │
│ Layer 2: Integration Procedure (PRM_ReviewPSVCaseRecordsUpdate) │
│   Status: ❌ NO VALIDATION                                   │
│   Issue: Accepts any data as long as PersonEducation exists  │
│   ▼▼▼                                                        │
│                                                              │
│ Layer 3: DataRaptor (PRMLoadPersonEducation)                │
│   Status: ❌ IsRequiredForUpsert = false for all fields     │
│   Issue: Will create record with NULL values                │
│   ▼▼▼                                                        │
│                                                              │
│ Layer 4: Salesforce Object (PersonEducation)                │
│   Status: ❌ NO VALIDATION RULES                            │
│   Issue: Database accepts NULL values                       │
│   ▼▼▼                                                        │
│                                                              │
│ Layer 5: Database                                           │
│   Status: ❌ NO NOT NULL CONSTRAINTS                        │
│   Result: 🔴 Invalid record created                         │
└──────────────────────────────────────────────────────────────┘
```

**Key Insight:**
- **Layer 1 (UI) is a gate, not a wall**
- If ANY of Layers 2-5 fail, invalid data can enter the system
- Currently, **ALL layers 2-5 are open** - there is NO server-side validation

---

## Recommended Solutions (Prioritized)

### 🔥 Priority 1: Add Salesforce Validation Rules (Immediate - 1 hour)

**Action:** Create validation rules on PersonEducation object

**Validation Rule 1: Required Institution**
```
Rule Name: PersonEducation_Institution_Required
Error Condition Formula: ISBLANK(PRM_Institution__c)
Error Message: "Institution is required for Person Education records."
Error Location: PRM_Institution__c
```

**Validation Rule 2: Required Start Date**
```
Rule Name: PersonEducation_StartDate_Required
Error Condition Formula: ISBLANK(PRM_StartDate__c)
Error Message: "Start Date is required for Person Education records."
Error Location: PRM_StartDate__c
```

**Validation Rule 3: Required End Date**
```
Rule Name: PersonEducation_EndDate_Required
Error Condition Formula: ISBLANK(PRM_EndDate__c)
Error Message: "End Date is required for Person Education records."
Error Location: PRM_EndDate__c
```

**Benefit:**
- Catches invalid records at the database level
- Will cause Integration Procedure to fail with clear error
- **Stops the bleeding immediately**

---

### 🔥 Priority 2: Add Integration Procedure Validation (Short-term - 2 hours)

**Action:** Add a validation step BEFORE calling DataRaptor

**New Element:** `CBValidatePersonEducation` (Conditional Block)
- **Location:** Insert after `CBLogicPersonEducation`, before `RACompPersonEducation`
- **Type:** Conditional Block with child elements

**Child Element 1:** `RAValidateRequiredFields` (Remote Action)
```javascript
// Apex Method: PRM_OmniUtils.validatePersonEducationFields
public static Map<String, Object> validatePersonEducationFields(Map<String, Object> input) {
    List<Object> educationRecords = (List<Object>) input.get('PersonEducation');
    List<Map<String, Object>> invalidRecords = new List<Map<String, Object>>();
    
    for (Object record : educationRecords) {
        Map<String, Object> edu = (Map<String, Object>) record;
        List<String> missingFields = new List<String>();
        
        if (String.isBlank((String) edu.get('InstitutionId'))) {
            missingFields.add('Institution');
        }
        if (String.isBlank((String) edu.get('EduStartDateSF'))) {
            missingFields.add('Start Date');
        }
        if (String.isBlank((String) edu.get('EduEndDateSF'))) {
            missingFields.add('End Date');
        }
        
        if (!missingFields.isEmpty()) {
            invalidRecords.add(new Map<String, Object>{
                'record' => edu,
                'missingFields' => missingFields
            });
        }
    }
    
    return new Map<String, Object>{
        'isValid' => invalidRecords.isEmpty(),
        'invalidRecords' => invalidRecords,
        'errorMessage' => 'Missing required fields: ' + JSON.serialize(invalidRecords)
    };
}
```

**Child Element 2:** `SVSetValidationError` (Set Values)
- Condition: `%RAValidateRequiredFields:isValid% == false`
- Action: Set error flag and stop execution

**Benefit:**
- Provides clear error messages to users
- Prevents invalid data from reaching DataRaptor
- Can handle multiple validation rules

---

### 🔥 Priority 3: Make DataRaptor Fields Required (Medium-term - 1 hour)

**Action:** Update DataRaptor mappings to enforce required fields

**Changes to PRMLoadPersonEducation DataRaptor:**

1. **Institution Field (Line 344-365):**
```json
{
  "InputFieldName": "PersonEducation:InstitutionId",
  "OutputFieldName": "PRM_Institution__c",
  "IsRequiredForUpsert": true,  // Changed from false
  "IsDisabled": false
}
```

2. **Start Date Field (Line 369-388):**
```json
{
  "InputFieldName": "PersonEducation:EduStartDateSF",
  "OutputFieldName": "PRM_StartDate__c",
  "IsRequiredForUpsert": true,  // Changed from false
  "IsDisabled": false
}
```

3. **End Date Field (Line 322-343):**
```json
{
  "InputFieldName": "PersonEducation:EduEndDateSF",
  "OutputFieldName": "PRM_EndDate__c",
  "IsRequiredForUpsert": true,  // Changed from false
  "IsDisabled": false
}
```

**Benefit:**
- DataRaptor will throw error if required fields are missing
- Defense-in-depth approach

---

### 🔧 Priority 4: Improve Institution Lookup Logic (Long-term - 4 hours)

**Action:** Make Type-Ahead lookup more robust

**Option A: Fuzzy Matching**
- Use DISTANCE formula to find closest match
- Present options if no exact match

**Option B: Auto-Create Institution**
- If institution name doesn't exist, create it automatically
- Add to audit log for review

**Option C: Required Selection from Existing**
- Disable free text entry
- Force selection from existing PRM_Institution__c records only
- Add "Request New Institution" button that triggers approval process

**Benefit:**
- Reduces user error
- Ensures InstitutionId is always populated

---

## Testing Recommendations

### Test Case 1: Empty Institution
```
1. Start Application Review
2. Go to Person Education step
3. Clear Institution field (use browser console if needed)
4. Enter Start Date and End Date
5. Submit
Expected: Validation error, record NOT created
```

### Test Case 2: Empty Start Date
```
1. Start Application Review
2. Go to Person Education step
3. Select Institution
4. Clear Start Date
5. Enter End Date
6. Submit
Expected: Validation error, record NOT created
```

### Test Case 3: Empty End Date
```
1. Start Application Review
2. Go to Person Education step
3. Select Institution
4. Enter Start Date
5. Clear End Date
6. Submit
Expected: Validation error, record NOT created
```

### Test Case 4: Institution Name Typo
```
1. Start Application Review
2. Go to Person Education step
3. Type "Harvardd Medical School" (typo)
4. Enter Start Date and End Date
5. Submit
Expected: Validation error indicating Institution not found
```

### Test Case 5: All Fields Valid
```
1. Start Application Review
2. Go to Person Education step
3. Select valid Institution
4. Enter valid Start Date
5. Enter valid End Date
6. Submit
Expected: Record created successfully with all fields populated
```

---

## Data Cleanup Required

### Query to Find Invalid Records

```sql
SELECT Id, Name, ContactId, HealthcareProviderId, 
       PRM_Institution__c, PRM_StartDate__c, PRM_EndDate__c,
       CreatedDate, CreatedBy.Name
FROM PersonEducation
WHERE PRM_Institution__c = NULL
   OR PRM_StartDate__c = NULL
   OR PRM_EndDate__c = NULL
ORDER BY CreatedDate DESC
```

### Cleanup Strategy

1. **Identify Affected Records**
   - Export list of invalid PersonEducation records
   - Group by Practitioner/Contact

2. **Research Original Data**
   - Check CAQH data for missing information
   - Contact case managers who created records

3. **Update or Delete**
   - Option A: Update with correct data if available
   - Option B: Delete invalid records if no data available
   - Option C: Mark as "Needs Review" with custom flag

---

## Prevention Checklist

- [ ] Deploy Salesforce Validation Rules
- [ ] Add Integration Procedure validation step
- [ ] Update DataRaptor required fields
- [ ] Test all scenarios above
- [ ] Clean up existing invalid records
- [ ] Update user training materials
- [ ] Add monitoring for invalid attempts
- [ ] Create dashboard to track validation failures
- [ ] Implement similar validations for other required fields (License, etc.)

---

## References

**Files Analyzed:**
- `PRM_CredApplicationReviewSubOS_English_Element_VerifyEducation.json`
- `PRM_ReviewPSVCaseRecordsUpdate_Element_DRLoadPersonEducation.json`
- `PRMLoadPersonEducation_Items.json` (DataRaptor mapping)
- `PersonEducation-Person Education Layout.layout-meta.xml`
- `Application_Review_LWC_Redesign_Detailed_Design.md`

**Related Components:**
- OmniScript: `PRM_InitialCredentialAppReview_English`
- Integration Procedure: `PRM_ReviewPSVCaseRecordsUpdate`
- DataRaptor: `PRMLoadPersonEducation`
- Object: `PersonEducation`

---

**Analysis Completed By:** Claude Code  
**Date:** 2026-04-22  
**Status:** Ready for Review and Implementation
