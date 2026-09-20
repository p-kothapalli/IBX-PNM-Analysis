# Concierge Info Code Assignment - Initial Cred PDA Review Field Updates

**Document Version:** 1.0  
**Created Date:** April 7, 2026  
**Purpose:** Document exactly which fields are updated on Info Code Assignments during Initial Cred PDA Review and Update flow

---

## Flow Overview

**Flow Name:** `PRM_InitialCredPDAReviewUpdateSubIPInsert` (Integration Procedure)  
**When It Runs:** After case approval by Committee, during PDA Review and Update phase  
**Objects Updated:** HealthcareFacilityNetwork, PRM_InfoCodeAssignment__c, HealthcareFacility

---

## Info Code Assignment Field Updates - Breakdown

### Fields Updated at END of Initial Cred PDA Review and Update

When the **Initial Cred PDA Review and Update** flow completes (case approved), the following field on `PRM_InfoCodeAssignment__c` is updated:

| Field | Before (PAR Submission) | After (Case Approval/PDA Review) | Description |
|-------|-------------------------|----------------------------------|-------------|
| **PRM_Pending__c** | `true` | **`false`** | Indicates the assignment is now ACTIVE and approved |

**That's it - only 1 field is updated: `PRM_Pending__c`**

---

## When Does This Update Happen?

### Timeline of Info Code Assignment Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: PAR Form Submission                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Practitioner completes PAR form                                             │
│ ├─ Answers "Yes" to concierge medicine                                      │
│ ├─ Selects 2 practice locations                                             │
│ └─ Submits form                                                              │
│                                                                               │
│ INFO CODE ASSIGNMENTS CREATED (via Integration Procedure):                  │
│ ├─ Assignment 1 (Location A):                                               │
│ │   ├─ PRM_InfoCode__c = "Concierge Provider"                               │
│ │   ├─ PRM_PractitionerFacilityAssignment__c = PPL_A_Id                     │
│ │   ├─ PRM_EffectiveDate__c = 04/07/2026 (submission date)                  │
│ │   ├─ PRM_Pending__c = TRUE  ⬅️ PENDING (not yet active)                   │
│ │   ├─ PRM_CaseManager__c = CM_123                                           │
│ │   └─ PRM_TerminationDate__c = null                                         │
│ │                                                                             │
│ └─ Assignment 2 (Location B): (same fields, different PPL)                  │
│                                                                               │
│ BOOLEAN CHECKBOX UPDATED (via Trigger):                                     │
│ ├─ HealthcarePractitionerFacility (PPL_A).PRM_IsConciergeProvider__c = TRUE│
│ └─ HealthcarePractitionerFacility (PPL_B).PRM_IsConciergeProvider__c = TRUE│
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Committee Review                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Case routes through various review steps                                    │
│ ├─ Screen Review                                                             │
│ ├─ Committee Decision                                                        │
│ └─ Committee APPROVES case                                                   │
│                                                                               │
│ NO CHANGES TO INFO CODE ASSIGNMENTS (still PRM_Pending__c = true)           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: PDA Review and Update (THIS IS WHERE UPDATES HAPPEN)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Flow: PRM_InitialCredPDAReviewUpdateSubIPInsert                             │
│                                                                               │
│ INFO CODE ASSIGNMENTS UPDATED:                                              │
│ ├─ Assignment 1 (Location A):                                               │
│ │   ├─ PRM_Pending__c = FALSE  ⬅️ ACTIVE (approved and activated)          │
│ │   └─ All other fields remain unchanged                                     │
│ │                                                                             │
│ └─ Assignment 2 (Location B):                                               │
│     ├─ PRM_Pending__c = FALSE  ⬅️ ACTIVE (approved and activated)          │
│     └─ All other fields remain unchanged                                     │
│                                                                               │
│ QUERY USED:                                                                  │
│   SELECT Id, PRM_Pending__c                                                  │
│   FROM PRM_InfoCodeAssignment__c                                             │
│   WHERE PRM_CaseManager__c = :caseManagerId                                  │
│   AND PRM_Pending__c = true                                                  │
│   AND PRM_IsErrorRecord__c = false                                           │
│                                                                               │
│ BOOLEAN CHECKBOXES: No change (already set to TRUE in Phase 1)             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ RESULT: Info Code Assignments are now ACTIVE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ ├─ PRM_Pending__c = false (approved)                                        │
│ ├─ PRM_EffectiveDate__c = 04/07/2026 (unchanged from submission)            │
│ ├─ PRM_TerminationDate__c = null (still active)                             │
│ └─ Ready to feed to Provider Directory / DART                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What About Case DENIAL?

If the case is **DENIED** instead of approved, the same field is updated but at a different flow:

**Flow Name:** `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial`  
**When It Runs:** When case is denied or closed  

**Field Update:**
- `PRM_Pending__c` = `false` (assignments are marked as denied, not active)

**Note:** Denied assignments have `PRM_Pending__c = false` but they're NOT active for use. The absence of `PRM_TerminationDate__c = null` combined with `PRM_Pending__c = false` and the case status indicates these are denied, not approved.

---

## Complete Field Inventory on PRM_InfoCodeAssignment__c

### Fields Populated During PAR Form Submission

| Field | Populated When | Source | Example Value |
|-------|----------------|--------|---------------|
| `PRM_InfoCode__c` | PAR form submission | Lookup by name "Concierge Provider" | a0X... (Info Code Id) |
| `PRM_PractitionerFacilityAssignment__c` | PAR form submission | Selected location → lookup HealthcarePractitionerFacility | a1Y... (PPL Id) |
| `PRM_EffectiveDate__c` | PAR form submission | Application submission date | 04/07/2026 |
| `PRM_Pending__c` | PAR form submission | Hardcoded | **true** |
| `PRM_CaseManager__c` | PAR form submission | Case Manager Id from form context | a2Z... (IndividualApplication Id) |
| `PRM_IsFeeOptional__c` | PAR form submission | Answer from "Is fee optional?" question | true / false |
| `PRM_TerminationDate__c` | PAR form submission | Null (new assignment) | null |

### Fields Updated During PDA Review and Update (Case Approval)

| Field | Updated When | New Value | Description |
|-------|--------------|-----------|-------------|
| `PRM_Pending__c` | PDA Review and Update (case approved) | **false** | Assignment is now active and approved |

### Fields Updated During Termination (Future)

| Field | Updated When | New Value | Description |
|-------|--------------|-----------|-------------|
| `PRM_TerminationDate__c` | Practitioner terminates or loses concierge status | Date of termination | Assignment is now inactive |
| `PRM_Pending__c` | Termination flow | false | If was still pending |

---

## Other Objects/Records Updated at End of Initial Cred PDA Review

### For Context: Other records updated by the same flow

According to Close_Case_PNC_Ancillary_User_Stories.md (Line 168), the following objects are also updated by `PRM_InitialCredPDAReviewUpdateSubIPInsert`:

| Object | Field Updated | Description |
|--------|---------------|-------------|
| **HealthcareFacilityNetwork** | `PRM_Pending__c = false` | Network assignments activated |
| **PRM_InfoCodeAssignment__c** | `PRM_Pending__c = false` | ⬅️ THIS IS WHAT WE'RE DISCUSSING |
| **HealthcareFacility** | `PRM_Pending__c = false` | Practice locations activated |

---

## Implementation Notes for Concierge Info Codes

### What Needs to Be Done?

**Good News:** The infrastructure already exists!

1. **PRM_InfoCodeAssignment__c already has PRM_Pending__c field** ✅
2. **InitialCredPDAReviewUpdateSubIPInsert already updates Info Code Assignments** ✅
3. **Pattern already documented in PNC user stories (Line 193)** ✅

### What to Verify?

1. **Verify PRM_Pending__c field exists on PRM_InfoCodeAssignment__c**
   - Check if field is already present
   - If not present, add field (Checkbox, default = false)

2. **Verify InitialCredPDAReviewUpdateSubIPInsert includes Info Code Assignment logic**
   - Check Integration Procedure code
   - Confirm query includes: `WHERE PRM_CaseManager__c = :caseManagerId AND PRM_Pending__c = true`
   - If not present, add logic (see Flow Impact Analysis document)

3. **Verify Case Denial flow also updates Info Code Assignments**
   - Check `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial`
   - Confirm Info Code Assignments are included in denial logic
   - If not present, extend utility (3 story points - see Flow Impact Analysis)

---

## Test Scenarios

### Scenario 1: Case Approval - Single Location

**Given:**
- Practitioner completes PAR form with concierge = Yes
- Selects 1 practice location
- Case Manager created with Id = CM_123
- Info Code Assignment created:
  - PRM_InfoCode__c = "Concierge Provider"
  - PRM_PractitionerFacilityAssignment__c = PPL_A
  - PRM_Pending__c = true
  - PRM_CaseManager__c = CM_123

**When:**
- Case is approved by Committee
- PDA Review and Update flow runs (`PRM_InitialCredPDAReviewUpdateSubIPInsert`)

**Then:**
- Query finds Info Code Assignment WHERE PRM_CaseManager__c = CM_123 AND PRM_Pending__c = true
- Update: PRM_Pending__c = false
- Verify: Assignment is now active (PRM_Pending__c = false, PRM_TerminationDate__c = null)
- Verify: HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = true (already set)

---

### Scenario 2: Case Approval - Multiple Locations

**Given:**
- Practitioner completes PAR form with concierge = Yes
- Selects 3 practice locations
- Case Manager created with Id = CM_456
- THREE Info Code Assignments created:
  - Assignment A: PRM_PractitionerFacilityAssignment__c = PPL_A, PRM_Pending__c = true, PRM_CaseManager__c = CM_456
  - Assignment B: PRM_PractitionerFacilityAssignment__c = PPL_B, PRM_Pending__c = true, PRM_CaseManager__c = CM_456
  - Assignment C: PRM_PractitionerFacilityAssignment__c = PPL_C, PRM_Pending__c = true, PRM_CaseManager__c = CM_456

**When:**
- Case is approved
- PDA Review and Update flow runs

**Then:**
- Query finds ALL 3 Info Code Assignments WHERE PRM_CaseManager__c = CM_456 AND PRM_Pending__c = true
- Update ALL 3: PRM_Pending__c = false
- Verify: All 3 assignments are now active
- Verify: All 3 HealthcarePractitionerFacility records have PRM_IsConciergeProvider__c = true

---

### Scenario 3: Case Denial - Assignments Not Activated

**Given:**
- Practitioner completes PAR form with concierge = Yes
- Selects 2 practice locations
- Case Manager created with Id = CM_789
- TWO Info Code Assignments created:
  - Assignment A: PRM_Pending__c = true, PRM_CaseManager__c = CM_789
  - Assignment B: PRM_Pending__c = true, PRM_CaseManager__c = CM_789

**When:**
- Case is DENIED by Committee
- Case Denial flow runs (`PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial`)

**Then:**
- Query finds ALL 2 Info Code Assignments WHERE PRM_CaseManager__c = CM_789 AND PRM_Pending__c = true
- Update ALL 2: PRM_Pending__c = false
- Verify: Assignments are NOT active (PRM_Pending__c = false indicates denied)
- Verify: Case status = Denied or Closed
- Note: These assignments will NOT feed to Provider Directory (not active)

---

## Summary Table

| Phase | Flow | Field Updated | Before | After | Description |
|-------|------|---------------|--------|-------|-------------|
| **PAR Submission** | PAR Form Integration Procedure | Multiple fields populated | N/A | Created | Assignment created with PRM_Pending__c = true |
| **Committee Review** | N/A | None | true | true | No changes to Info Code Assignment |
| **PDA Review (Approval)** | `PRM_InitialCredPDAReviewUpdateSubIPInsert` | `PRM_Pending__c` | true | **false** | Assignment activated |
| **Case Denial** | `PRM_CaseManagerDenialUtility` | `PRM_Pending__c` | true | **false** | Assignment denied (not active) |
| **Termination** | Termination flow | `PRM_TerminationDate__c` | null | Date | Assignment terminated |

---

## Key Takeaway

**At the end of Initial Cred PDA Review and Update flow, ONLY 1 field is updated:**

```
PRM_InfoCodeAssignment__c.PRM_Pending__c = false
```

**This changes the assignment from "Pending" to "Active" (approved) or "Denied" depending on case outcome.**

All other fields (`PRM_InfoCode__c`, `PRM_PractitionerFacilityAssignment__c`, `PRM_EffectiveDate__c`, `PRM_CaseManager__c`, `PRM_IsFeeOptional__c`) remain unchanged from their initial values set during PAR form submission.

---

## Record Activation Definition

**What makes an Info Code Assignment "ACTIVE"?**

An Info Code Assignment is considered **ACTIVE** when:
1. `PRM_Pending__c = false` (approved, not denied)
2. `PRM_TerminationDate__c = null` OR `PRM_TerminationDate__c > TODAY` (not terminated)
3. Associated Case Manager status = Approved/Closed (not Denied)

**Query for Active Assignments:**
```sql
SELECT Id, PRM_InfoCode__r.Name, PRM_PractitionerFacilityAssignment__c, PRM_EffectiveDate__c
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.Name = 'Concierge Provider'
AND PRM_Pending__c = false
AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
```

---

**End of Document**
