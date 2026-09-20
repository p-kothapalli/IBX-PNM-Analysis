# Concierge Info Code Assignment - Complete Flow Update Summary

**Document Version:** 1.0  
**Created Date:** April 7, 2026  
**Purpose:** Comprehensive list of ALL Practitioner Participation subsequent flows that need Info Code Assignment activation/denial logic

---

## Executive Summary

**Critical Finding:** Info Code Assignment logic must be added at **ALL THREE LEVELS**:
1. ✅ Practitioner level (`PRM_Account__c`)
2. ✅ Practice Location level (`PRM_HealthcareFacility__c`)
3. ❌ **MISSING: Practitioner Practice Location level** (`PRM_PractitionerFacilityAssignment__c`) ⬅️ **MUST BE ADDED EVERYWHERE**

**Total Flows Requiring Updates:** 12+ flows across 4 categories

---

## Flow Categories Overview

| Category | # of Flows | Complexity | Priority |
|----------|-----------|------------|----------|
| **1. Case Approval Flows** | 3 flows | Medium | P0 - BLOCKER |
| **2. Case Denial/Closure Flows** | 2 flows | Low-Medium | P0 - BLOCKER |
| **3. Termination Flows** | 3 flows | Medium | P0 - Critical |
| **4. Add Location Flows** | 4 flows | High | P1 - High |

---

## Category 1: Case Approval Flows (Activation)

### **When:** Case is approved, records transition from Pending to Active
### **Action:** Set `PRM_Pending__c = false` (activates Info Code Assignments)

---

### Flow 1.1: Initial Cred PDA Review and Update

**Flow Name:** `PRM_InitialCredPDAReviewUpdateSubIPInsert` (Integration Procedure)

**When It Runs:**
- After Committee approves Initial Credentialing case
- During PDA Review and Update phase

**Current Query (INCOMPLETE):**
```apex
WHERE PRM_CaseManager__c = :caseManagerId
AND PRM_Pending__c = true
AND (PRM_Account__c IN :practitionerAccIds
     OR PRM_HealthcareFacility__c IN :hcFacilityIds)
```

**REQUIRED FIX:**
```apex
// ADD: Get Practitioner Practice Location Ids
Set<Id> pplIds = new Set<Id>();
for(HealthcarePractitionerFacility ppl : [
    SELECT Id 
    FROM HealthcarePractitionerFacility
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
]) {
    pplIds.add(ppl.Id);
}

// UPDATED QUERY:
List<PRM_InfoCodeAssignment__c> assignments = [
    SELECT Id, PRM_Pending__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
    AND PRM_IsErrorRecord__c = false
    AND (PRM_Account__c IN :practitionerAccIds
         OR PRM_HealthcareFacility__c IN :hcFacilityIds
         OR PRM_PractitionerFacilityAssignment__c IN :pplIds)  ⬅️ ADDED
];

// Set to active
for(PRM_InfoCodeAssignment__c ica : assignments) {
    ica.PRM_Pending__c = false;
}
update assignments;
```

**Objects Updated:**
| Object | Field | Action |
|--------|-------|--------|
| PRM_InfoCodeAssignment__c (Practitioner level) | PRM_Pending__c | true → false |
| PRM_InfoCodeAssignment__c (Practice Location level) | PRM_Pending__c | true → false |
| PRM_InfoCodeAssignment__c (Practitioner Practice Location level) | PRM_Pending__c | true → false ⬅️ **NEW** |

**Effort:** 5 story points  
**Priority:** P0 - BLOCKER (without this, Concierge assignments never activate)

---

### Flow 1.2: PNC PDA Review and Update

**Flow Name:** `PRM_PNCPDAReviewUpdate` → calls `PRM_PNCPDABatch` / `PRM_PNCPDAService`

**When It Runs:**
- After Committee approves PNC (Practice/Network Change) case
- During PDA Review and Update phase

**Current State:**
- Similar to Initial Cred flow (Line 165 of Close_Case_PNC_Ancillary_User_Stories.md)
- Creates/updates: HealthcareFacilityNetwork, PRM_InfoCodeAssignment__c, HealthcareFacility

**REQUIRED FIX:**
- Same as Flow 1.1
- Add `PRM_PractitionerFacilityAssignment__c IN :pplIds` to query

**Effort:** 3 story points  
**Priority:** P0 - BLOCKER

---

### Flow 1.3: Recredentialing PDA Review and Update

**Flow Name:** `PRM_RecredPDAReviewUpdate` (or similar Recred flow)

**When It Runs:**
- After Recredentialing case approved
- During PDA Review phase

**Current State:**
- May or may not currently handle Info Code Assignments (verify)
- If Recred PSV creates Info Code Assignments (Epic 6), this flow must activate them

**REQUIRED FIX:**
- Add Info Code Assignment activation logic (same as Flow 1.1)
- Include all 3 levels

**Effort:** 5 story points  
**Priority:** P0 - BLOCKER (if Recred creates assignments)

---

## Category 2: Case Denial/Closure Flows (Denial)

### **When:** Case is denied or closed without approval
### **Action:** Set `PRM_Pending__c = false` (marks as denied, not active)

---

### Flow 2.1: Case Manager Denial Utility (Universal)

**Flow Name:** `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` (Apex class)

**When It Runs:**
- When any case (Initial Cred, PNC, Recred, etc.) is denied
- Universal utility used across all case types

**Current Query (INCOMPLETE):**
```apex
WHERE PRM_CaseManager__c = :caseManagerId
AND PRM_Pending__c = true
AND (PRM_Account__c IN :practitionerAccIds
     OR PRM_HealthcareFacility__c IN :hcFacilityIds)
```

**REQUIRED FIX:**
```apex
// ADD: Get Practitioner Practice Location Ids
Set<Id> pplIds = new Set<Id>();
for(HealthcarePractitionerFacility ppl : [
    SELECT Id 
    FROM HealthcarePractitionerFacility
    WHERE PRM_CaseManager__c = :caseManagerId
]) {
    pplIds.add(ppl.Id);
}

// UPDATED QUERY:
List<PRM_InfoCodeAssignment__c> assignments = [
    SELECT Id, PRM_Pending__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
    AND PRM_IsErrorRecord__c = false
    AND (PRM_Account__c IN :practitionerAccIds
         OR PRM_HealthcareFacility__c IN :hcFacilityIds
         OR PRM_PractitionerFacilityAssignment__c IN :pplIds)  ⬅️ ADDED
];

// Mark as denied (not active)
for(PRM_InfoCodeAssignment__c ica : assignments) {
    ica.PRM_Pending__c = false; // False + Case Denied = Not Active
}
update assignments;
```

**Effort:** 3 story points  
**Priority:** P0 - BLOCKER

---

### Flow 2.2: Close Case Guided Flow

**Flow Name:** `PRM_CloseCaseGuidedFlow_English` (OmniScript)

**When It Runs:**
- When user manually closes a case from UI
- Calls `PRM_CaseManagerDenialUtility` in backend

**Current State:**
- Relies on Flow 2.1 (Denial Utility)

**REQUIRED FIX:**
- No direct change needed (handled by Flow 2.1)
- Verify that Flow 2.1 is called correctly

**Effort:** 0 points (no change if Flow 2.1 is updated)  
**Priority:** P1 - Verify only

---

## Category 3: Termination Flows (Auto-Terminate Assignments)

### **When:** Practitioner or Practice Location is terminated
### **Action:** Set `PRM_TerminationDate__c` on active Info Code Assignments

---

### Flow 3.1: Practitioner Termination (Manual)

**Flow Name:** `PRM_PractitionerTerminationForm_English` (OmniScript)

**When It Runs:**
- When user manually terminates a practitioner via Termination Form
- Updates Account credentialing status to "Terminated"

**Current State:**
- Does NOT currently terminate Info Code Assignments

**REQUIRED CHANGE:**
```apex
// After practitioner Account is terminated:
Date terminationDate = [termination effective date from form];

// Query active Info Code Assignments at ALL 3 LEVELS
List<PRM_InfoCodeAssignment__c> activeAssignments = [
    SELECT Id, PRM_TerminationDate__c, PRM_Account__c, 
           PRM_PractitionerFacilityAssignment__c
    FROM PRM_InfoCodeAssignment__c
    WHERE (PRM_Account__c = :practitionerAccountId
           OR PRM_PractitionerFacilityAssignment__r.PractitionerId = :practitionerAccountId)
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
];

// Terminate all assignments
for(PRM_InfoCodeAssignment__c ica : activeAssignments) {
    ica.PRM_TerminationDate__c = terminationDate;
}
update activeAssignments;
```

**Effort:** 5 story points  
**Priority:** P0 - Critical

---

### Flow 3.2: Practitioner Termination (Batch)

**Flow Name:** `PRM_PractitionerTerminationBatchHelper.cls` (Apex batch)

**When It Runs:**
- Batch job that terminates practitioners automatically based on criteria
- Runs on schedule

**Current State:**
- Does NOT currently terminate Info Code Assignments

**REQUIRED CHANGE:**
- Same logic as Flow 3.1
- Bulkified for batch processing (200+ practitioners)

**Effort:** 5 story points  
**Priority:** P0 - Critical

---

### Flow 3.3: Practice Location Termination / Practitioner Practice Location Termination

**Flow Name:** Practice Location termination flows (various)

**When It Runs:**
- When HealthcareFacility is terminated
- When HealthcarePractitionerFacility (PPL) is terminated

**Current State:**
- Does NOT currently terminate Info Code Assignments

**REQUIRED CHANGE:**
```apex
// When HealthcareFacility is terminated:
List<PRM_InfoCodeAssignment__c> facilityAssignments = [
    SELECT Id, PRM_TerminationDate__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_HealthcareFacility__c = :healthcareFacilityId
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
];

// When HealthcarePractitionerFacility is terminated:
List<PRM_InfoCodeAssignment__c> pplAssignments = [
    SELECT Id, PRM_TerminationDate__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_PractitionerFacilityAssignment__c = :pplId
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
];

// Terminate assignments
Date terminationDate = [effective termination date];
for(PRM_InfoCodeAssignment__c ica : [combined list]) {
    ica.PRM_TerminationDate__c = terminationDate;
}
update [combined list];
```

**Effort:** 5 story points  
**Priority:** P0 - Critical

---

## Category 4: Add Location Flows (Create New Assignments)

### **When:** Practitioner adds a new practice location to existing credentialing
### **Action:** Create new Info Code Assignment if practitioner is concierge

---

### Flow 4.1: Initial Cred - Add Practice Location (App Review & PSV)

**Flow Name:** `PRM_PSVSubOsTxnyRole_English` / `PRM_CredApplicationReviewOSTxnyRole_English`

**When It Runs:**
- During Initial Credentialing, at App Review & PSV Service Verification step
- User adds new practice location not listed

**Current State:**
- Adds new HealthcarePractitionerFacility records
- Does NOT create Info Code Assignments

**REQUIRED CHANGE:**
```
BUSINESS DECISION NEEDED:
When a practitioner adds a new location during Initial Cred:
- Should system ASK if they practice concierge at this new location?
- OR automatically apply concierge status if practitioner already has it?

Option A: ASK USER
- Add question: "Do you practice concierge medicine at this location?"
- If Yes, create Info Code Assignment at PPL level with PRM_Pending__c = true

Option B: AUTO-APPLY
- Query if practitioner has existing concierge assignments
- If yes, automatically create assignment for new location
- Less user friction but may not be accurate

RECOMMENDATION: Option A (ask user) for accuracy
```

**If Option A selected:**
- Add concierge question to Add Location flow
- Create Info Code Assignment when user answers Yes
- Same logic as PAR form (Story 2.2/2.5)

**Effort:** 8 story points (new UI + backend logic)  
**Priority:** P1 - High

---

### Flow 4.2: Recredentialing - Add Practice Location

**Flow Name:** Recredentialing Add Location flows (various)

**When It Runs:**
- During Recredentialing, when practitioner adds new practice location

**Current State:**
- Similar to Flow 4.1

**REQUIRED CHANGE:**
- Same as Flow 4.1
- Ask user if they practice concierge at new location
- Create assignment if Yes

**Effort:** 8 story points  
**Priority:** P1 - High

---

### Flow 4.3: Off-Cycle Group Selection - Add Location

**Flow Name:** `prmGroupSelectionOffCycle` (LWC component)

**When It Runs:**
- Off-cycle changes when practitioner adds new practice location

**Current State:**
- Adds location via Off-Cycle process
- Does NOT handle Info Code Assignments

**REQUIRED CHANGE:**
- Same as Flow 4.1
- May need separate Off-Cycle case approval flow

**Effort:** 8 story points  
**Priority:** P2 - Medium

---

### Flow 4.4: PNC (Practice/Network Change) - Add Location

**Flow Name:** PNC Add Location flows

**When It Runs:**
- During PNC case, when adding new practice location

**Current State:**
- Creates HealthcarePractitionerFacility via PNC flows
- Does NOT create Info Code Assignments

**REQUIRED CHANGE:**
- Same as Flow 4.1
- PNC-specific UI and backend

**Effort:** 8 story points  
**Priority:** P2 - Medium

---

## Additional Flows (Lower Priority)

### Flow 5.1: Provider Change Form

**Flow Name:** `PRM_ProviderChangeForm_English`

**When It Runs:**
- Practitioners submit changes to their profile/locations

**Required Change:**
- May need to support concierge status changes
- Business decision needed

**Effort:** TBD  
**Priority:** P2 - Medium

---

### Flow 5.2: PDM Manual Update

**Flow Name:** `PRM_PDMManualUpdate_English`

**When It Runs:**
- PDM team makes manual updates to practitioner/location data

**Required Change:**
- May need UI for manually adding/removing concierge assignments

**Effort:** TBD  
**Priority:** P2 - Medium

---

## Summary Table: All Flows Requiring Updates

| # | Flow Name | Category | Action | Levels Affected | Effort (SP) | Priority |
|---|-----------|----------|--------|-----------------|-------------|----------|
| 1.1 | **PRM_InitialCredPDAReviewUpdateSubIPInsert** | Case Approval | Set Pending = false | All 3 | 5 | **P0 - BLOCKER** |
| 1.2 | **PRM_PNCPDAReviewUpdate** | Case Approval | Set Pending = false | All 3 | 3 | **P0 - BLOCKER** |
| 1.3 | **PRM_RecredPDAReviewUpdate** | Case Approval | Set Pending = false | All 3 | 5 | **P0 - BLOCKER** |
| 2.1 | **PRM_CaseManagerDenialUtility** | Case Denial | Set Pending = false | All 3 | 3 | **P0 - BLOCKER** |
| 2.2 | PRM_CloseCaseGuidedFlow_English | Case Denial | (Handled by 2.1) | All 3 | 0 | P1 - Verify |
| 3.1 | **PRM_PractitionerTerminationForm** | Termination | Set TermDate | Prac + PPL | 5 | **P0 - Critical** |
| 3.2 | **PRM_PractitionerTerminationBatch** | Termination | Set TermDate | Prac + PPL | 5 | **P0 - Critical** |
| 3.3 | **Practice Location Termination** | Termination | Set TermDate | Location + PPL | 5 | **P0 - Critical** |
| 4.1 | **PRM_PSVSubOsTxnyRole (Add Location)** | Add Location | Create assignment | PPL | 8 | P1 - High |
| 4.2 | **Recred Add Location** | Add Location | Create assignment | PPL | 8 | P1 - High |
| 4.3 | Off-Cycle Add Location | Add Location | Create assignment | PPL | 8 | P2 - Medium |
| 4.4 | PNC Add Location | Add Location | Create assignment | PPL | 8 | P2 - Medium |
| 5.1 | Provider Change Form | Manual Change | TBD | TBD | TBD | P2 - Medium |
| 5.2 | PDM Manual Update | Manual Update | TBD | TBD | TBD | P2 - Medium |

---

## Critical Path (BLOCKERS)

**These flows MUST be updated before Production deployment:**

### Phase 1: Case Approval Flows (P0 - BLOCKER)
1. ✅ **PRM_InitialCredPDAReviewUpdateSubIPInsert** - 5 SP
2. ✅ **PRM_PNCPDAReviewUpdate** - 3 SP
3. ✅ **PRM_RecredPDAReviewUpdate** - 5 SP

**Subtotal:** 13 story points

### Phase 2: Case Denial Flows (P0 - BLOCKER)
4. ✅ **PRM_CaseManagerDenialUtility** - 3 SP

**Subtotal:** 3 story points

### Phase 3: Termination Flows (P0 - Critical)
5. ✅ **PRM_PractitionerTerminationForm** - 5 SP
6. ✅ **PRM_PractitionerTerminationBatch** - 5 SP
7. ✅ **Practice Location Termination** - 5 SP

**Subtotal:** 15 story points

**Total Critical Path:** 31 story points (close to original 37 point estimate from Flow Impact Analysis)

---

## Implementation Recommendations

### 1. Create Reusable Utility Class

**Class Name:** `PRM_InfoCodeAssignmentUtility`

**Methods:**
```apex
// Activate assignments for a case manager
public static void activateAssignments(Id caseManagerId)

// Deny assignments for a case manager
public static void denyAssignments(Id caseManagerId)

// Terminate assignments for a practitioner
public static void terminateAssignments(Id practitionerId, Date terminationDate)

// Terminate assignments for a practice location
public static void terminateAssignments(Id healthcareFacilityId, Date terminationDate)

// Terminate assignments for a practitioner practice location
public static void terminateAssignments(Id pplId, Date terminationDate)

// Get active assignments for a practitioner (all 3 levels)
public static List<PRM_InfoCodeAssignment__c> getActiveAssignments(Id practitionerId)
```

**Benefit:**
- Reuse logic across all flows
- Centralized maintenance
- Consistent behavior
- Easier testing

**Effort:** 8 story points (one-time, saves effort across all flows)

---

### 2. Update All Flows to Use Utility

**For each flow:**
- Replace inline query logic with utility method calls
- Pass appropriate parameters (caseManagerId, practitionerId, terminationDate, etc.)

**Example:**
```apex
// OLD (inline):
List<PRM_InfoCodeAssignment__c> assignments = [SELECT...];
for(...) { ica.PRM_Pending__c = false; }
update assignments;

// NEW (utility):
PRM_InfoCodeAssignmentUtility.activateAssignments(caseManagerId);
```

---

### 3. Add Comprehensive Testing

**Test Coverage Required:**
- Unit tests for utility class (90%+ coverage)
- Integration tests for each flow
- End-to-end tests: PAR form → Case Approval → Assignments Active
- Negative tests: Case Denial → Assignments Not Active
- Termination tests: Practitioner Terminated → Assignments Terminated

---

## Effort Summary

| Phase | Flows | Story Points |
|-------|-------|--------------|
| **Utility Class** | 1 reusable class | 8 |
| **Critical Path (P0)** | 7 flows | 31 |
| **Add Location Flows (P1)** | 4 flows | 32 |
| **Manual Update Flows (P2)** | 2 flows | TBD |
| **Total** | 14 flows | **~71 points** |

**Note:** This is higher than the original 37-point estimate because:
1. Original estimate assumed only Practitioner + Practice Location levels (2 levels)
2. Now we have **3 levels** (added Practitioner Practice Location)
3. Add Location flows were not included in original estimate
4. Utility class creation was not included

---

## Next Steps

1. **Get Business Decisions:**
   - Flow 4.1-4.4: Should Add Location flows ask user about concierge status? (Option A vs Option B)
   - Flow 5.1-5.2: Should manual update flows support concierge changes?

2. **Create Utility Class (Story 1):**
   - Priority: P0 - BLOCKER
   - Must complete first, then all other flows use it

3. **Update Critical Path Flows (Stories 2-8):**
   - Phase 1: Case Approval (3 flows)
   - Phase 2: Case Denial (1 flow)
   - Phase 3: Termination (3 flows)

4. **Update Add Location Flows (Stories 9-12):**
   - After business decision received
   - Can run in parallel with Critical Path

5. **Testing:**
   - Comprehensive test plan
   - Integration tests across all flows
   - UAT with PDA team

---

**End of Document**
