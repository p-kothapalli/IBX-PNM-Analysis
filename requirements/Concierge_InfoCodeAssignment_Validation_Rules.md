# Concierge Info Code Assignment - Validation Rules

**Document Version:** 1.0  
**Created Date:** April 7, 2026  
**Purpose:** Comprehensive validation rules for manual Concierge Provider Info Code Assignment entry with all scenarios and test cases

---

## Executive Summary

When users manually create Concierge Provider Info Code Assignments via page layout, we need strict validation rules to ensure data integrity across three levels:
1. **Practitioner Level** - Role must be PCP or Dual
2. **Practitioner Practice Location Level** - Both practitioner and PPL roles must be PCP or Dual, practitioner must have concierge flag
3. **Practice Location Level** - ALL practitioners must be PCP/Dual with concierge flag

**Date Validations:** All effective dates must fall within parent record date ranges.

---

## Validation Categories

### Category A: Field-Level Validations (Basic)
### Category B: Role-Based Validations
### Category C: Date Range Validations
### Category D: Cross-Record Validations (Requires Triggers/Flows)
### Category E: Concierge Flag Validations

---

## Level 1: Practitioner Level Info Code Assignments

**Object:** `PRM_InfoCodeAssignment__c`  
**Parent Relationship:** `PRM_Account__c` (Practitioner)

---

### Validation Rule 1.1: Info Code Must Be Concierge Provider

**API Name:** `PRM_ICA_Practitioner_MustBeConciergeCode`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_Account__c)),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name != "Concierge Provider"
)
```

**Error Message:**
> "At Practitioner level, only 'Concierge Provider' Info Code can be assigned. Please select the correct Info Code."

**Error Location:** `PRM_InfoCode__c` field

---

### Validation Rule 1.2: Practitioner Role Must Be PCP or Dual

**API Name:** `PRM_ICA_Practitioner_RoleMustBePCPOrDual`

**Type:** Category B - Role-Based

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_Account__c)),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name = "Concierge Provider",
    NOT(INCLUDES(PRM_Account__r.HealthcarePractitionerRole__c, "PCP")),
    NOT(INCLUDES(PRM_Account__r.HealthcarePractitionerRole__c, "Dual"))
)
```

**Error Message:**
> "Concierge Provider can only be assigned to practitioners with PCP or Dual role. Current practitioner role: {PRM_Account__r.HealthcarePractitionerRole__c}. Please update practitioner role first."

**Error Location:** `PRM_Account__c` field

**Note:** Assumes `HealthcarePractitionerRole__c` is a multi-select picklist on Account

---

### Validation Rule 1.3: Effective Date Cannot Be Blank

**API Name:** `PRM_ICA_Practitioner_EffectiveDateRequired`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_Account__c)),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_HealthcareFacility__c),
    ISBLANK(PRM_EffectiveDate__c)
)
```

**Error Message:**
> "Effective Date is required for Concierge Provider assignment."

**Error Location:** `PRM_EffectiveDate__c` field

---

### Validation Rule 1.4: Effective Date Cannot Be Before Practitioner Credentialing Start

**API Name:** `PRM_ICA_Practitioner_EffectiveDateBeforeCredStart`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_Account__c)),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_HealthcareFacility__c),
    NOT(ISBLANK(PRM_EffectiveDate__c)),
    NOT(ISBLANK(PRM_Account__r.PRM_CredentialingStartDate__c)),
    PRM_EffectiveDate__c < PRM_Account__r.PRM_CredentialingStartDate__c
)
```

**Error Message:**
> "Effective Date ({PRM_EffectiveDate__c}) cannot be before practitioner's credentialing start date ({PRM_Account__r.PRM_CredentialingStartDate__c})."

**Error Location:** `PRM_EffectiveDate__c` field

**Example:**
- Practitioner Credentialing Start: 01/01/2025
- Info Code Assignment Effective Date: 12/15/2024 ❌ INVALID
- Info Code Assignment Effective Date: 01/15/2025 ✅ VALID

---

### Validation Rule 1.5: Termination Date Cannot Be After Practitioner Credentialing End

**API Name:** `PRM_ICA_Practitioner_TermDateAfterCredEnd`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_Account__c)),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_HealthcareFacility__c),
    NOT(ISBLANK(PRM_TerminationDate__c)),
    NOT(ISBLANK(PRM_Account__r.PRM_CredentialingEndDate__c)),
    PRM_TerminationDate__c > PRM_Account__r.PRM_CredentialingEndDate__c
)
```

**Error Message:**
> "Termination Date ({PRM_TerminationDate__c}) cannot be after practitioner's credentialing end date ({PRM_Account__r.PRM_CredentialingEndDate__c})."

**Error Location:** `PRM_TerminationDate__c` field

---

### Validation Rule 1.6: Effective Date Cannot Be After Termination Date

**API Name:** `PRM_ICA_EffectiveDateAfterTermDate`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_EffectiveDate__c)),
    NOT(ISBLANK(PRM_TerminationDate__c)),
    PRM_EffectiveDate__c > PRM_TerminationDate__c
)
```

**Error Message:**
> "Effective Date ({PRM_EffectiveDate__c}) cannot be after Termination Date ({PRM_TerminationDate__c})."

**Error Location:** Top of page

**Note:** This applies to ALL levels (Practitioner, PPL, Location)

---

## Level 2: Practitioner Practice Location Level Info Code Assignments

**Object:** `PRM_InfoCodeAssignment__c`  
**Parent Relationship:** `PRM_PractitionerFacilityAssignment__c` (links to HealthcarePractitionerFacility)

---

### Validation Rule 2.1: Info Code Must Be Concierge Provider

**API Name:** `PRM_ICA_PPL_MustBeConciergeCode`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name != "Concierge Provider"
)
```

**Error Message:**
> "At Practitioner Practice Location level, only 'Concierge Provider' Info Code can be assigned. Please select the correct Info Code."

**Error Location:** `PRM_InfoCode__c` field

---

### Validation Rule 2.2: Practitioner Role Must Be PCP or Dual

**API Name:** `PRM_ICA_PPL_PractitionerRoleMustBePCPOrDual`

**Type:** Category B - Role-Based

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name = "Concierge Provider",
    NOT(INCLUDES(PRM_PractitionerFacilityAssignment__r.PractitionerId.HealthcarePractitionerRole__c, "PCP")),
    NOT(INCLUDES(PRM_PractitionerFacilityAssignment__r.PractitionerId.HealthcarePractitionerRole__c, "Dual"))
)
```

**Error Message:**
> "Concierge Provider can only be assigned when practitioner role is PCP or Dual. Current practitioner role: {PRM_PractitionerFacilityAssignment__r.PractitionerId.HealthcarePractitionerRole__c}. Please update practitioner role first."

**Error Location:** `PRM_PractitionerFacilityAssignment__c` field

---

### Validation Rule 2.3: PPL Role Must Be PCP or Dual

**API Name:** `PRM_ICA_PPL_PPLRoleMustBePCPOrDual`

**Type:** Category B - Role-Based

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name = "Concierge Provider",
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__r.Role)),
    NOT(INCLUDES(PRM_PractitionerFacilityAssignment__r.Role, "PCP")),
    NOT(INCLUDES(PRM_PractitionerFacilityAssignment__r.Role, "Dual"))
)
```

**Error Message:**
> "Concierge Provider can only be assigned when Practitioner Practice Location role is PCP or Dual. Current PPL role: {PRM_PractitionerFacilityAssignment__r.Role}. Please update PPL role first."

**Error Location:** `PRM_PractitionerFacilityAssignment__c` field

**Note:** Assumes `Role` field exists on HealthcarePractitionerFacility and is multi-select picklist

---

### Validation Rule 2.4: Practitioner Must Have Concierge Flag Set

**API Name:** `PRM_ICA_PPL_PractitionerMustHaveConciergeFlag`

**Type:** Category E - Concierge Flag

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    PRM_InfoCode__r.Name = "Concierge Provider",
    PRM_PractitionerFacilityAssignment__r.PractitionerId.PRM_IsConciergeProvider__c = FALSE
)
```

**Error Message:**
> "Cannot assign Concierge Provider at Practitioner Practice Location level because the practitioner does not have an active Concierge Provider assignment at the Practitioner level. Please create a Practitioner-level assignment first or ensure PRM_IsConciergeProvider__c = true on the practitioner record."

**Error Location:** `PRM_PractitionerFacilityAssignment__c` field

---

### Validation Rule 2.5: Effective Date Cannot Be Before PPL Effective From

**API Name:** `PRM_ICA_PPL_EffectiveDateBeforePPLStart`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    NOT(ISBLANK(PRM_EffectiveDate__c)),
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__r.EffectiveFrom)),
    PRM_EffectiveDate__c < PRM_PractitionerFacilityAssignment__r.EffectiveFrom
)
```

**Error Message:**
> "Effective Date ({PRM_EffectiveDate__c}) cannot be before Practitioner Practice Location's Effective From date ({PRM_PractitionerFacilityAssignment__r.EffectiveFrom}). The assignment can only be effective when the practitioner is active at this location."

**Error Location:** `PRM_EffectiveDate__c` field

**Example:**
- PPL Effective From: 01/01/2026
- Info Code Assignment Effective Date: 12/12/2025 ❌ INVALID
- Info Code Assignment Effective Date: 01/15/2026 ✅ VALID

---

### Validation Rule 2.6: Termination Date Cannot Be After PPL Effective To

**API Name:** `PRM_ICA_PPL_TermDateAfterPPLEnd`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    NOT(ISBLANK(PRM_TerminationDate__c)),
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__r.EffectiveTo)),
    PRM_TerminationDate__c > PRM_PractitionerFacilityAssignment__r.EffectiveTo
)
```

**Error Message:**
> "Termination Date ({PRM_TerminationDate__c}) cannot be after Practitioner Practice Location's Effective To date ({PRM_PractitionerFacilityAssignment__r.EffectiveTo}). The assignment must terminate when practitioner leaves this location."

**Error Location:** `PRM_TerminationDate__c` field

**Example:**
- PPL Effective To: 12/31/2026
- Info Code Assignment Termination Date: 01/15/2027 ❌ INVALID
- Info Code Assignment Termination Date: 12/15/2026 ✅ VALID

---

### Validation Rule 2.7: Effective Date Cannot Be Blank

**API Name:** `PRM_ICA_PPL_EffectiveDateRequired`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_HealthcareFacility__c),
    ISBLANK(PRM_EffectiveDate__c)
)
```

**Error Message:**
> "Effective Date is required for Concierge Provider assignment."

**Error Location:** `PRM_EffectiveDate__c` field

---

## Level 3: Practice Location Level Info Code Assignments

**Object:** `PRM_InfoCodeAssignment__c`  
**Parent Relationship:** `PRM_HealthcareFacility__c` (Practice Location)

**Note:** Some validations at this level CANNOT be implemented as standard validation rules because they require aggregation queries (e.g., "ALL practitioners at location must have concierge flag"). These require Apex triggers or Flow-based validations.

---

### Validation Rule 3.1: Info Code Must Be Concierge Provider

**API Name:** `PRM_ICA_Location_MustBeConciergeCode`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_HealthcareFacility__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    PRM_InfoCode__r.Name != "Concierge Provider"
)
```

**Error Message:**
> "At Practice Location level, only 'Concierge Provider' Info Code can be assigned. Please select the correct Info Code."

**Error Location:** `PRM_InfoCode__c` field

---

### Validation Rule 3.2: Effective Date Cannot Be Blank

**API Name:** `PRM_ICA_Location_EffectiveDateRequired`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_HealthcareFacility__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    ISBLANK(PRM_EffectiveDate__c)
)
```

**Error Message:**
> "Effective Date is required for Concierge Provider assignment."

**Error Location:** `PRM_EffectiveDate__c` field

---

### Validation Rule 3.3: Effective Date Cannot Be Before Location Operational Date

**API Name:** `PRM_ICA_Location_EffectiveDateBeforeOperational`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_HealthcareFacility__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    NOT(ISBLANK(PRM_EffectiveDate__c)),
    NOT(ISBLANK(PRM_HealthcareFacility__r.PRM_OperationalStartDate__c)),
    PRM_EffectiveDate__c < PRM_HealthcareFacility__r.PRM_OperationalStartDate__c
)
```

**Error Message:**
> "Effective Date ({PRM_EffectiveDate__c}) cannot be before Practice Location's operational start date ({PRM_HealthcareFacility__r.PRM_OperationalStartDate__c})."

**Error Location:** `PRM_EffectiveDate__c` field

**Note:** Assumes `PRM_OperationalStartDate__c` field exists on HealthcareFacility. If not, use a different date field.

---

### Validation Rule 3.4: Termination Date Cannot Be After Location Closure Date

**API Name:** `PRM_ICA_Location_TermDateAfterClosure`

**Type:** Category C - Date Range

**Rule Logic:**
```apex
AND(
    NOT(ISBLANK(PRM_HealthcareFacility__c)),
    ISBLANK(PRM_Account__c),
    ISBLANK(PRM_PractitionerFacilityAssignment__c),
    NOT(ISBLANK(PRM_TerminationDate__c)),
    NOT(ISBLANK(PRM_HealthcareFacility__r.PRM_OperationalEndDate__c)),
    PRM_TerminationDate__c > PRM_HealthcareFacility__r.PRM_OperationalEndDate__c
)
```

**Error Message:**
> "Termination Date ({PRM_TerminationDate__c}) cannot be after Practice Location's operational end date ({PRM_HealthcareFacility__r.PRM_OperationalEndDate__c})."

**Error Location:** `PRM_TerminationDate__c` field

---

### Trigger-Based Validation 3.5: All Practitioners Must Be PCP or Dual

**Trigger Name:** `PRM_InfoCodeAssignmentTrigger` (Before Insert, Before Update)

**Type:** Category D - Cross-Record Validation (Cannot use standard validation rule)

**Logic:**
```apex
// When creating Location-level Concierge assignment:
if (newAssignment.PRM_HealthcareFacility__c != null 
    && newAssignment.PRM_InfoCode__r.Name == 'Concierge Provider') {
    
    // Query all practitioners at this location
    List<HealthcarePractitionerFacility> practitioners = [
        SELECT Id, PractitionerId.HealthcarePractitionerRole__c, Role
        FROM HealthcarePractitionerFacility
        WHERE FacilityId = :newAssignment.PRM_HealthcareFacility__c
        AND (EffectiveTo = null OR EffectiveTo >= TODAY)
    ];
    
    // Check each practitioner's role
    for (HealthcarePractitionerFacility ppl : practitioners) {
        String practitionerRole = ppl.PractitionerId.HealthcarePractitionerRole__c;
        String pplRole = ppl.Role;
        
        // Practitioner must be PCP or Dual
        if (!practitionerRole.contains('PCP') && !practitionerRole.contains('Dual')) {
            newAssignment.addError(
                'Cannot assign Concierge Provider at Practice Location level because ' +
                'practitioner ' + ppl.PractitionerId.Name + ' has role: ' + practitionerRole + 
                '. All practitioners at this location must have PCP or Dual role.'
            );
            return;
        }
        
        // PPL role must be PCP or Dual
        if (!pplRole.contains('PCP') && !pplRole.contains('Dual')) {
            newAssignment.addError(
                'Cannot assign Concierge Provider at Practice Location level because ' +
                'practitioner ' + ppl.PractitionerId.Name + ' has PPL role: ' + pplRole + 
                '. All practitioner practice location roles must be PCP or Dual.'
            );
            return;
        }
    }
}
```

**Error Message (Dynamic):**
> "Cannot assign Concierge Provider at Practice Location level because practitioner [Dr. John Smith] has role: [Specialist]. All practitioners at this location must have PCP or Dual role."

**Error Location:** Top of page

---

### Trigger-Based Validation 3.6: All Practitioners Must Have Concierge Flag

**Trigger Name:** `PRM_InfoCodeAssignmentTrigger` (Before Insert, Before Update)

**Type:** Category D - Cross-Record Validation (Cannot use standard validation rule)

**Logic:**
```apex
// When creating Location-level Concierge assignment:
if (newAssignment.PRM_HealthcareFacility__c != null 
    && newAssignment.PRM_InfoCode__r.Name == 'Concierge Provider') {
    
    // Query all practitioners at this location
    List<HealthcarePractitionerFacility> practitioners = [
        SELECT Id, PractitionerId.Name, PractitionerId.PRM_IsConciergeProvider__c
        FROM HealthcarePractitionerFacility
        WHERE FacilityId = :newAssignment.PRM_HealthcareFacility__c
        AND (EffectiveTo = null OR EffectiveTo >= TODAY)
    ];
    
    // Check each practitioner's concierge flag
    for (HealthcarePractitionerFacility ppl : practitioners) {
        if (ppl.PractitionerId.PRM_IsConciergeProvider__c == false) {
            newAssignment.addError(
                'Cannot assign Concierge Provider at Practice Location level because ' +
                'practitioner ' + ppl.PractitionerId.Name + ' does not have Concierge Provider flag set. ' +
                'All practitioners at this location must have active Concierge Provider assignments.'
            );
            return;
        }
    }
}
```

**Error Message (Dynamic):**
> "Cannot assign Concierge Provider at Practice Location level because practitioner [Dr. Jane Doe] does not have Concierge Provider flag set. All practitioners at this location must have active Concierge Provider assignments."

**Error Location:** Top of page

---

## General Validations (All Levels)

### Validation Rule G.1: Only One Lookup Field Populated

**API Name:** `PRM_ICA_OnlyOneLookupPopulated`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
OR(
    // More than one lookup populated
    AND(NOT(ISBLANK(PRM_Account__c)), NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c))),
    AND(NOT(ISBLANK(PRM_Account__c)), NOT(ISBLANK(PRM_HealthcareFacility__c))),
    AND(NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)), NOT(ISBLANK(PRM_HealthcareFacility__c))),
    
    // All three lookups populated
    AND(
        NOT(ISBLANK(PRM_Account__c)), 
        NOT(ISBLANK(PRM_PractitionerFacilityAssignment__c)),
        NOT(ISBLANK(PRM_HealthcareFacility__c))
    ),
    
    // No lookups populated
    AND(
        ISBLANK(PRM_Account__c), 
        ISBLANK(PRM_PractitionerFacilityAssignment__c),
        ISBLANK(PRM_HealthcareFacility__c)
    )
)
```

**Error Message:**
> "Info Code Assignment must be at exactly ONE level: Practitioner (Account), Practitioner Practice Location, OR Practice Location (Healthcare Facility). Please select only one."

**Error Location:** Top of page

---

### Validation Rule G.2: Termination Date Cannot Be In Future If Setting To Denied

**API Name:** `PRM_ICA_NoFutureTermIfDenied`

**Type:** Category A - Field-Level

**Rule Logic:**
```apex
AND(
    PRM_Pending__c = FALSE,
    NOT(ISBLANK(PRM_TerminationDate__c)),
    PRM_TerminationDate__c > TODAY(),
    // Check if this is a denied assignment (has case manager with denied status)
    NOT(ISBLANK(PRM_CaseManager__c))
)
```

**Error Message:**
> "Termination Date cannot be in the future for denied assignments. If this assignment was denied, set Termination Date to today or earlier."

**Error Location:** `PRM_TerminationDate__c` field

**Note:** This is a simplified check. More robust logic would check actual case status.

---

## Complete Scenario Test Matrix

### Scenario Matrix: Practitioner Level

| # | Scenario | Practitioner Role | Effective From | Termination Date | Practitioner Cred Start | Practitioner Cred End | Expected Result | Validation Rule Triggered |
|---|----------|-------------------|----------------|------------------|-------------------------|----------------------|-----------------|---------------------------|
| **1.1** | Valid - PCP role, dates within range | PCP | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **1.2** | Valid - Dual role, dates within range | Dual | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **1.3** | Valid - No termination date | PCP | 02/01/2026 | null | 01/01/2026 | null | ✅ PASS | None |
| **1.4** | Invalid - Specialist role | Specialist | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.2: RoleMustBePCPOrDual |
| **1.5** | Invalid - Effective before cred start | PCP | 12/01/2025 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.4: EffectiveDateBeforeCredStart |
| **1.6** | Invalid - Term after cred end | PCP | 02/01/2026 | 01/15/2028 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.5: TermDateAfterCredEnd |
| **1.7** | Invalid - Effective after termination | PCP | 06/01/2026 | 03/01/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.6: EffectiveDateAfterTermDate |
| **1.8** | Invalid - Missing effective date | PCP | null | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.3: EffectiveDateRequired |
| **1.9** | Invalid - Wrong Info Code | PCP | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.1: MustBeConciergeCode |
| **1.10** | Edge - Effective equals cred start | PCP | 01/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **1.11** | Edge - Term equals cred end | PCP | 02/01/2026 | 12/31/2027 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **1.12** | Invalid - PCP AND Specialist (multi-select) | PCP;Specialist | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (has PCP) |
| **1.13** | Invalid - Only Hospitalist role | Hospitalist | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.2: RoleMustBePCPOrDual |

---

### Scenario Matrix: Practitioner Practice Location Level

| # | Scenario | Prac Role | PPL Role | Prac Concierge Flag | Effective From | Term Date | PPL Eff From | PPL Eff To | Expected Result | Validation Rule |
|---|----------|-----------|----------|---------------------|----------------|-----------|--------------|------------|-----------------|-----------------|
| **2.1** | Valid - All conditions met | PCP | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **2.2** | Valid - Dual practitioner role | Dual | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **2.3** | Valid - Dual PPL role | PCP | Dual | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **2.4** | Valid - Both Dual roles | Dual | Dual | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **2.5** | Invalid - Practitioner is Specialist | Specialist | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.2: PractitionerRoleMustBePCPOrDual |
| **2.6** | Invalid - PPL is Specialist | PCP | Specialist | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.3: PPLRoleMustBePCPOrDual |
| **2.7** | Invalid - Practitioner no concierge flag | PCP | PCP | FALSE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.4: PractitionerMustHaveConciergeFlag |
| **2.8** | Invalid - Effective before PPL start | PCP | PCP | TRUE | 12/15/2025 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.5: EffectiveDateBeforePPLStart |
| **2.9** | Invalid - Term after PPL end | PCP | PCP | TRUE | 02/01/2026 | 01/15/2028 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.6: TermDateAfterPPLEnd |
| **2.10** | Invalid - Effective after termination | PCP | PCP | TRUE | 06/01/2026 | 03/01/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.6: EffectiveDateAfterTermDate |
| **2.11** | Invalid - Missing effective date | PCP | PCP | TRUE | null | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.7: EffectiveDateRequired |
| **2.12** | Invalid - Wrong Info Code | PCP | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.1: MustBeConciergeCode |
| **2.13** | Edge - Effective equals PPL start | PCP | PCP | TRUE | 01/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **2.14** | Edge - Term equals PPL end | PCP | PCP | TRUE | 02/01/2026 | 12/31/2027 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **2.15** | Valid - PPL has no end date | PCP | PCP | TRUE | 02/01/2026 | null | 01/01/2026 | null | ✅ PASS | None |
| **2.16** | Edge - Multiple roles: PCP + Spec | PCP;Specialist | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (has PCP) |
| **2.17** | Invalid - Both Specialist roles | Specialist | Specialist | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 2.2 AND 2.3 |

---

### Scenario Matrix: Practice Location Level

| # | Scenario | All Prac Roles | All PPL Roles | All Prac Concierge Flags | Effective From | Term Date | Location Oper Start | Location Oper End | Expected Result | Validation Rule |
|---|----------|----------------|---------------|--------------------------|----------------|-----------|---------------------|-------------------|-----------------|-----------------|
| **3.1** | Valid - Single PCP practitioner | PCP | PCP | TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **3.2** | Valid - Multiple PCP practitioners | All PCP | All PCP | All TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **3.3** | Valid - Mix of PCP and Dual | PCP, Dual | PCP, Dual | All TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None |
| **3.4** | Invalid - One practitioner is Specialist | PCP, Specialist | PCP, PCP | TRUE, TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.5: AllPractitionersMustBePCPOrDual (Trigger) |
| **3.5** | Invalid - One PPL role is Specialist | PCP, PCP | PCP, Specialist | TRUE, TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.5: AllPractitionersMustBePCPOrDual (Trigger) |
| **3.6** | Invalid - One practitioner no concierge | PCP, PCP | PCP, PCP | TRUE, FALSE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.6: AllPractitionersMustHaveConciergeFlag (Trigger) |
| **3.7** | Invalid - Effective before location start | All PCP | All PCP | All TRUE | 12/15/2025 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.3: EffectiveDateBeforeOperational |
| **3.8** | Invalid - Term after location closure | All PCP | All PCP | All TRUE | 02/01/2026 | 01/15/2028 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.4: TermDateAfterClosure |
| **3.9** | Invalid - Effective after termination | All PCP | All PCP | All TRUE | 06/01/2026 | 03/01/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 1.6: EffectiveDateAfterTermDate |
| **3.10** | Invalid - Missing effective date | All PCP | All PCP | All TRUE | null | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.2: EffectiveDateRequired |
| **3.11** | Invalid - Wrong Info Code | All PCP | All PCP | All TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.1: MustBeConciergeCode |
| **3.12** | Edge - Effective equals location start | All PCP | All PCP | All TRUE | 01/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **3.13** | Edge - Term equals location closure | All PCP | All PCP | All TRUE | 02/01/2026 | 12/31/2027 | 01/01/2026 | 12/31/2027 | ✅ PASS | None (equals is valid) |
| **3.14** | Valid - Location has no closure date | All PCP | All PCP | All TRUE | 02/01/2026 | null | 01/01/2026 | null | ✅ PASS | None |
| **3.15** | Invalid - Location has 3 PCPs, 1 Specialist | 3 PCP, 1 Spec | All PCP | All TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.5: AllPractitionersMustBePCPOrDual (Trigger) |
| **3.16** | Edge - Empty location (no practitioners) | N/A | N/A | N/A | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ⚠️ EDGE CASE | Business decision needed |
| **3.17** | Invalid - All practitioners Dual except 1 Spec | Dual, Dual, Spec | All Dual | TRUE, TRUE, TRUE | 02/01/2026 | 12/31/2026 | 01/01/2026 | 12/31/2027 | ❌ FAIL | 3.5: AllPractitionersMustBePCPOrDual (Trigger) |

---

### Scenario Matrix: General Validations (All Levels)

| # | Scenario | Practitioner Lookup | PPL Lookup | Location Lookup | Effective From | Term Date | Expected Result | Validation Rule |
|---|----------|---------------------|------------|-----------------|----------------|-----------|-----------------|-----------------|
| **G.1** | Valid - Only Practitioner populated | Populated | Blank | Blank | 02/01/2026 | 12/31/2026 | ✅ PASS | None |
| **G.2** | Valid - Only PPL populated | Blank | Populated | Blank | 02/01/2026 | 12/31/2026 | ✅ PASS | None |
| **G.3** | Valid - Only Location populated | Blank | Blank | Populated | 02/01/2026 | 12/31/2026 | ✅ PASS | None |
| **G.4** | Invalid - Practitioner AND PPL populated | Populated | Populated | Blank | 02/01/2026 | 12/31/2026 | ❌ FAIL | G.1: OnlyOneLookupPopulated |
| **G.5** | Invalid - Practitioner AND Location populated | Populated | Blank | Populated | 02/01/2026 | 12/31/2026 | ❌ FAIL | G.1: OnlyOneLookupPopulated |
| **G.6** | Invalid - PPL AND Location populated | Blank | Populated | Populated | 02/01/2026 | 12/31/2026 | ❌ FAIL | G.1: OnlyOneLookupPopulated |
| **G.7** | Invalid - All three populated | Populated | Populated | Populated | 02/01/2026 | 12/31/2026 | ❌ FAIL | G.1: OnlyOneLookupPopulated |
| **G.8** | Invalid - None populated | Blank | Blank | Blank | 02/01/2026 | 12/31/2026 | ❌ FAIL | G.1: OnlyOneLookupPopulated |

---

## Date Validation Examples in Detail

### Example 1: Practitioner Level - Valid Date Range

**Scenario:**
- Practitioner Credentialing Start Date: 01/01/2025
- Practitioner Credentialing End Date: 12/31/2027
- Info Code Assignment Effective Date: 06/01/2025
- Info Code Assignment Termination Date: 06/30/2027

**Result:** ✅ VALID
- Effective (06/01/2025) is after Cred Start (01/01/2025) ✓
- Termination (06/30/2027) is before Cred End (12/31/2027) ✓
- Effective is before Termination ✓

---

### Example 2: PPL Level - Invalid Effective Date Before PPL Start

**Scenario:**
- PPL Effective From: 01/01/2026
- PPL Effective To: 12/31/2027
- Info Code Assignment Effective Date: 12/15/2025 ❌
- Info Code Assignment Termination Date: 06/30/2027

**Result:** ❌ INVALID
- **Validation Triggered:** 2.5: EffectiveDateBeforePPLStart
- **Error Message:** "Effective Date (12/15/2025) cannot be before Practitioner Practice Location's Effective From date (01/01/2026). The assignment can only be effective when the practitioner is active at this location."

---

### Example 3: PPL Level - Valid Edge Case (Equals PPL Start)

**Scenario:**
- PPL Effective From: 01/01/2026
- PPL Effective To: 12/31/2027
- Info Code Assignment Effective Date: 01/01/2026 ✅
- Info Code Assignment Termination Date: 12/31/2027 ✅

**Result:** ✅ VALID (Edge case: equals is allowed)
- Effective equals PPL Start (boundary inclusive) ✓
- Termination equals PPL End (boundary inclusive) ✓

---

### Example 4: Location Level - Invalid Termination After Closure

**Scenario:**
- Practice Location Operational Start: 01/01/2020
- Practice Location Operational End: 12/31/2026
- Info Code Assignment Effective Date: 06/01/2025
- Info Code Assignment Termination Date: 03/15/2027 ❌

**Result:** ❌ INVALID
- **Validation Triggered:** 3.4: TermDateAfterClosure
- **Error Message:** "Termination Date (03/15/2027) cannot be after Practice Location's operational end date (12/31/2026)."

---

### Example 5: Multiple Date Violations

**Scenario:**
- PPL Effective From: 01/01/2026
- PPL Effective To: 12/31/2026
- Info Code Assignment Effective Date: 06/01/2026
- Info Code Assignment Termination Date: 03/01/2026 ❌

**Result:** ❌ INVALID
- **Validation Triggered:** 1.6: EffectiveDateAfterTermDate
- **Error Message:** "Effective Date (06/01/2026) cannot be after Termination Date (03/01/2026)."
- **Note:** This validation fires FIRST before checking PPL date ranges

---

## Implementation Order

### Phase 1: Standard Validation Rules (Can Deploy Immediately)
1. Field-level validations (1.1, 1.3, 1.6, 2.1, 2.7, 3.1, 3.2, G.1)
2. Role-based validations (1.2, 2.2, 2.3)
3. Date range validations (1.4, 1.5, 2.5, 2.6, 3.3, 3.4)
4. Concierge flag validations (2.4)

**Total:** 16 validation rules

---

### Phase 2: Trigger-Based Validations (Requires Apex Development)
1. Practice Location level: All practitioners must be PCP/Dual (3.5)
2. Practice Location level: All practitioners must have concierge flag (3.6)

**Effort:** 5 story points
- Create trigger: `PRM_InfoCodeAssignmentTrigger`
- Create handler class: `PRM_InfoCodeAssignmentTriggerHandler`
- Unit tests with 90%+ coverage
- Integration tests for all scenarios

---

### Phase 3: Testing (QA Required)
- Test all 45 scenarios in test matrices
- Negative testing for each validation rule
- Edge case testing (boundary values, null checks)
- Integration testing with PAR form flow
- UAT with PDA team

---

## Summary Statistics

| Category | # of Validation Rules | Implementation Type | Effort |
|----------|----------------------|---------------------|--------|
| **Practitioner Level** | 6 rules | Standard Validation Rules | 0 SP (config) |
| **PPL Level** | 7 rules | Standard Validation Rules | 0 SP (config) |
| **Location Level** | 6 rules | 4 Standard VR + 2 Triggers | 5 SP (triggers) |
| **General Level** | 2 rules | Standard Validation Rules | 0 SP (config) |
| **TOTAL** | **21 validations** | 19 VRs + 2 Triggers | **5 SP** |

---

## User Story for Implementation

### Story: Add Validation Rules for Manual Concierge Info Code Assignment Entry

**As a** PDA Admin  
**I want** strict validation rules when manually creating Concierge Provider Info Code Assignments  
**So that** data integrity is maintained across all three levels (Practitioner, PPL, Location)

**Acceptance Criteria:**

1. ✅ 16 standard validation rules deployed covering:
   - Field-level validations (Info Code, Effective Date required)
   - Role-based validations (PCP/Dual only)
   - Date range validations (within parent record dates)
   - Cross-field validations (only one lookup populated)

2. ✅ Trigger-based validations for Practice Location level:
   - Cannot create if any practitioner lacks PCP/Dual role
   - Cannot create if any practitioner lacks concierge flag
   - Clear error messages with practitioner names

3. ✅ All 45 test scenarios pass:
   - 13 Practitioner level scenarios
   - 17 PPL level scenarios
   - 17 Practice Location level scenarios
   - 8 General level scenarios

4. ✅ Error messages are clear and actionable

5. ✅ Validation rules documented in Salesforce metadata

**Effort:** 5 story points  
**Priority:** P1 - High (Must deploy with Concierge feature)

---

**End of Document**
