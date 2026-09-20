# Concierge Medicine Info Code - Flow Impact Analysis

**Document Version:** 1.0
**Created Date:** April 1, 2026
**Purpose:** Analyze all existing flows that need updates when implementing Concierge Medicine Info Codes

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Flows Requiring Changes](#flows-requiring-changes)
3. [Flows with No Changes Needed](#flows-with-no-changes-needed)
4. [Detailed Flow Analysis](#detailed-flow-analysis)
5. [Implementation Checklist](#implementation-checklist)

---

## Executive Summary

**Good News:** The **PRM_InfoCodeAssignment__c object already has the necessary fields** for integration with existing workflows:
- ✅ **PRM_Pending__c** - For case workflow integration
- ✅ **PRM_CaseManager__c** - For linking to Case Managers
- ✅ **PRM_HealthcareFacility__c** - For practice location assignments
- ✅ **PRM_Account__c** - For practitioner assignments

**Pattern Already Established:** PNC user stories (Close_Case_PNC_Ancillary_User_Stories.md) already document that **PRM_InfoCodeAssignment__c** should be updated when cases are denied/closed (line 193).

### Impact Summary

| Flow Category | Changes Needed? | Complexity |
|---------------|-----------------|------------|
| **Case Denial/Closure** | ✅ Yes - Add Concierge Info Codes to existing logic | Low (extend existing utility) |
| **RCAT (Recredentialing)** | ✅ Yes - Exclude concierge providers per business rules | Medium |
| **Termination Flows** | ✅ Yes - Update Info Code Assignments on termination | Medium |
| **DataRaptor Feeds** | ⚠️ Verify - Ensure feeds include Info Code Assignments | Low |
| **Validation/Cross-Reference** | ⚠️ Maybe - Depends on business rules | Low |
| **Trigger Infrastructure** | ✅ Yes - Reuse existing PRM_InfoCodeAssTrigger | Low (reuse existing) |

---

## Flows Requiring Changes

### 1. Case Denial / Closure Flows

**Files Impacted:**
- `PRM_CaseManagerDenialUtility.cls`
- `PRM_CloseCaseGuidedFlow_English` OmniScript
- Integration Procedures: `PRM_ReviewParCaseRecordsUpdate`, `PRM_ReviewPNCCaseRecordsUpdate`, etc.

**Current State:**
PNC user stories (line 193) already specify:
```
| 15 | PRM_InfoCodeAssignment__c | ... | Info codes at Practice Location and Practitioner level;
     PRM_CaseManager__c, PRM_HealthcareFacility__c or PRM_Account__c | PRM_Pending__c = false
```

**Required Changes:**

#### Change 1.1: Extend PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial

**Location:** `PRM_CaseManagerDenialUtility.cls` (Apex class)

**Change:**
```apex
// EXISTING CODE (from PNC pattern):
// Query Info Code Assignments where PRM_Pending__c = true and PRM_CaseManager__c = caseManagerId

// ADD: Filter to handle Concierge Info Code Assignments specifically
List<PRM_InfoCodeAssignment__c> infoCodeAssignments = [
    SELECT Id, PRM_InfoCode__r.Name, PRM_Account__c, PRM_HealthcareFacility__c,
           PRM_CaseManager__c, PRM_Pending__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_Pending__c = true
    AND PRM_IsErrorRecord__c = false
    AND (PRM_Account__c IN :practitionerAccIds
         OR PRM_HealthcareFacility__c IN :hcFacilityIds)
];

// Set PRM_Pending__c = false for all matching assignments
for(PRM_InfoCodeAssignment__c ica : infoCodeAssignments) {
    ica.PRM_Pending__c = false;
}
update infoCodeAssignments;
```

**Acceptance Criteria:**
- [ ] When Case Manager is denied/closed, all Info Code Assignments (including Concierge PCP and Concierge Provider) with PRM_Pending__c = true are updated to PRM_Pending__c = false
- [ ] Query excludes Info Code Assignments belonging to other Case Managers
- [ ] Query excludes error records (PRM_IsErrorRecord__c = true)
- [ ] Both practitioner-level and practice-level assignments are handled
- [ ] Unit tests cover Concierge Info Code Assignment denial scenarios

**Effort:** 3 story points

---

### 2. RCAT (Recredentialing) Flows

**Files Impacted:**
- RCAT batch jobs (e.g., `PRM_RCATTerminationBatchHelper`, `PRM_CheckCAQHAccessOnDueAccountsBatch`)
- Integration Procedures: `PRM_RecredTerminationLetter`, `PRM_GetInfoCodeAndOtherRecordsForRCATReview`
- DataRaptors: `PRMDRExtractHCPFDetails`, `PRMGetRelatedDataforPNCAndDelegatedRCATReview`

**Business Rule Question:**
❓ **Should concierge providers be excluded from RCAT recredentialing checks?**
- **Option A:** Yes - Similar to PNC logic (`PRM_PNC__c = true` excluded from CAQH checks per line 176 of PRM_PNC_Analysis.md)
- **Option B:** No - Concierge providers still need recredentialing

**Assuming Option A (exclude from RCAT):**

#### Change 2.1: Exclude Concierge Providers from CAQH Batch

**Location:** `PRM_CheckCAQHAccessOnDueAccountsBatch.cls`

**Change:**
```apex
// EXISTING CODE excludes PNC practitioners:
WHERE PRM_PNC__c = false

// ADD: Exclude practitioners with active Concierge PCP Info Code Assignment
// Query for practitioner IDs with active Concierge PCP assignments
Set<Id> conciergeAccountIds = new Set<Id>();
for(PRM_InfoCodeAssignment__c ica : [
    SELECT PRM_Account__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_InfoCode__r.Name = 'Concierge PCP'
    AND PRM_Account__c != null
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
]) {
    conciergeAccountIds.add(ica.PRM_Account__c);
}

// Update main query:
WHERE PRM_PNC__c = false
AND Id NOT IN :conciergeAccountIds
```

**Acceptance Criteria:**
- [ ] Practitioners with active "Concierge PCP" Info Code Assignment are excluded from CAQH access checks
- [ ] Exclusion is based on Termination Date (null or > TODAY = active)
- [ ] Both practitioner-level and practice-level logic considered (if practice-level concierge affects practitioners)
- [ ] Unit tests verify exclusion logic

**Effort:** 3 story points

---

#### Change 2.2: Exclude Concierge Practice Locations from Recred Termination Letter

**Location:** Integration Procedure `PRM_RecredTerminationLetter` → Element: `FilterHCPFRecords`

**Current Logic (from PRM_PNC_Analysis.md, line 119-122):**
```json
"EligibleHCPF": "=LIST(FILTER(LIST(%DRExtractHCPFDetails:HCPF%),'Account:PRM_PNC__c != true'))"
```

**Change:**
```json
// ADD: Also filter out practice locations with active Concierge Provider Info Code Assignment
// Create new DataRaptor or add to existing: PRMDRExtractHCPFWithConciergeStatus
// Output: HCPF records with IsConcierge boolean derived from Info Code Assignment

"EligibleHCPF": "=LIST(FILTER(LIST(%DRExtractHCPFDetails:HCPF%),'Account:PRM_PNC__c != true AND IsConcierge != true'))"
```

**OR use Formula in DataRaptor:**
```
// In PRMDRExtractHCPFDetails, add formula field:
IsConcierge = (check if practice location has active Concierge Provider assignment)
```

**Acceptance Criteria:**
- [ ] Practice locations with active "Concierge Provider" Info Code Assignment are excluded from recred termination letters
- [ ] Filter condition: `(PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)`
- [ ] Existing PNC exclusion logic remains functional
- [ ] Integration tests verify exclusion

**Effort:** 5 story points

---

### 3. Practitioner / Practice Location Termination Flows

**Files Impacted:**
- `PRM_PractitionerTerminationBatchHelper.cls`
- OmniScripts: `PRM_PractitionerTerminationForm_English`, `PRM_PractitionerTerminationRecredForm_English`
- Integration Procedures: Termination IPs

**Business Rule:**
When a practitioner or practice location is terminated, **automatically set Termination Date on all active Info Code Assignments**.

#### Change 3.1: Auto-Terminate Info Code Assignments on Practitioner Termination

**Location:** Practitioner termination Apex/IP

**Change:**
```apex
// When practitioner Account is terminated (e.g., PRM_CredentialingStatus__c = 'Terminated'):
// Query active Info Code Assignments for this practitioner
List<PRM_InfoCodeAssignment__c> activeAssignments = [
    SELECT Id, PRM_TerminationDate__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_Account__c = :practitionerAccountId
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
];

// Set Termination Date = today (or effective termination date)
Date terminationDate = Date.today(); // or pass from termination flow
for(PRM_InfoCodeAssignment__c ica : activeAssignments) {
    ica.PRM_TerminationDate__c = terminationDate;
}
update activeAssignments;
```

**Acceptance Criteria:**
- [ ] When practitioner is terminated, all active Info Code Assignments (Concierge PCP, Concierge Provider, and any others) are automatically terminated (Termination Date = termination effective date)
- [ ] Logic applies to both manual termination and batch termination
- [ ] Termination Date set = effective termination date (not necessarily today)
- [ ] Unit tests verify auto-termination
- [ ] Existing terminated assignments are not modified

**Effort:** 5 story points

---

#### Change 3.2: Auto-Terminate Info Code Assignments on Practice Location Termination

**Location:** Practice location termination Apex/IP

**Change:**
```apex
// When HealthcareFacility is terminated:
// Query active Info Code Assignments for this practice location
List<PRM_InfoCodeAssignment__c> activeAssignments = [
    SELECT Id, PRM_TerminationDate__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_HealthcareFacility__c = :healthcareFacilityId
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
];

// Set Termination Date
Date terminationDate = Date.today(); // or pass from termination flow
for(PRM_InfoCodeAssignment__c ica : activeAssignments) {
    ica.PRM_TerminationDate__c = terminationDate;
}
update activeAssignments;
```

**Acceptance Criteria:**
- [ ] When practice location is terminated, all active Info Code Assignments are automatically terminated
- [ ] Logic applies to both manual and batch termination
- [ ] Unit tests verify auto-termination

**Effort:** 5 story points

---

### 4. DataRaptor Feeds (DART, Inquire Only, Provider Directory)

**Files Impacted:**
- DataRaptors that output practitioner/practice location data
- ETL feed configurations

**Required Changes:**

#### Change 4.1: Add Info Code Assignment Data to Practitioner DataRaptors

**Affected DataRaptors:**
- `PRMDRExtractHealthCareProviderNPIWithBothValues`
- `PRMDRExtractHealthCareProviderNPIWithLastName`
- `PRMDRGetPractitionerFromNPI`
- `PRMExtractPractitionerForVerification`
- `PRMDRExtractAccountDetails`
- Any DataRaptor that outputs practitioner data to DART/Inquire Only

**Change:**
```
// ADD to each DataRaptor:
Output Field: IsConciergePCP
Formula: (Check if Account has active 'Concierge PCP' Info Code Assignment)

Output Field: IsConciergeProvider
Formula: (Check if Account has active 'Concierge Provider' Info Code Assignment)

// OR use Extract step:
Extract from PRM_InfoCodeAssignment__c:
  Relationship: PRM_Account__c = Account.Id
  Filter: PRM_InfoCode__r.Name IN ('Concierge PCP', 'Concierge Provider')
          AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
  Output: ConciergePCP_EffectiveDate, ConciergePCP_TerminationDate,
          ConciergeProvider_EffectiveDate, ConciergeProvider_TerminationDate
```

**Acceptance Criteria:**
- [ ] DataRaptors that output to DART include "Concierge PCP" Info Code Assignment status
- [ ] DataRaptors that output to Inquire Only include "Concierge PCP" Info Code Assignment status
- [ ] DataRaptors that output to Provider Directory include "Concierge Provider" Info Code Assignment status
- [ ] Internal vs External Info Codes are properly separated (internal to DART/Inquire Only; external to Provider Directory)
- [ ] Active status correctly calculated: `(PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)`
- [ ] Effective Date and Termination Date are included for reporting

**Effort:** 8 story points (multiple DataRaptors)

---

#### Change 4.2: Create New DataRaptor for Info Code Assignment Extraction (Optional)

**Name:** `PRMDRExtractInfoCodeAssignments`

**Purpose:** Dedicated DataRaptor to extract Info Code Assignments for a given Account or HealthcareFacility

**Input:**
- `AccountId` (practitioner)
- `HealthcareFacilityId` (practice location)

**Output:**
- `InfoCodeAssignments` (list)
  - `InfoCodeName`
  - `EffectiveDate`
  - `TerminationDate`
  - `IsActive` (formula)
  - `AssignmentLevel` (Practitioner or Practice Location)

**Use Case:** Can be called by other DataRaptors or Integration Procedures to get Info Code Assignment data

**Effort:** 3 story points

---

### 5. Validation / Cross-Reference Flows

**Files Impacted:**
- `PRM_VerifyPractitionerDetails` / `PRM_VerifyPractitionerDetailsForDelegated` (Integration Procedures)
- OmniScripts: `PRM_PDMManualUpdate_English`, `PRM_ProviderChangeForm_English`

**Business Rule Question:**
❓ **Should there be validation when creating Concierge Info Code Assignments?**

**Possible Validations:**

#### Validation 5.1: Prevent Duplicate Active Assignments

**Location:** Validation Rule or Trigger on `PRM_InfoCodeAssignment__c`

**Rule:**
Cannot create duplicate active assignment (same Info Code + Account/Facility + no Termination Date)

**Implementation:**
```apex
// In PRM_InfoCodeAssTrigger or validation rule:
// On INSERT/UPDATE, check if duplicate active assignment exists
Map<String, PRM_InfoCodeAssignment__c> existingActiveMap = new Map<String, PRM_InfoCodeAssignment__c>();

for(PRM_InfoCodeAssignment__c existing : [
    SELECT Id, PRM_InfoCode__c, PRM_Account__c, PRM_HealthcareFacility__c
    FROM PRM_InfoCodeAssignment__c
    WHERE (PRM_Account__c IN :accountIds OR PRM_HealthcareFacility__c IN :facilityIds)
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
    AND Id NOT IN :newRecordIds
]) {
    String key = existing.PRM_InfoCode__c + '_' +
                 (existing.PRM_Account__c != null ? existing.PRM_Account__c : existing.PRM_HealthcareFacility__c);
    existingActiveMap.put(key, existing);
}

// Check new records against existing
for(PRM_InfoCodeAssignment__c newIca : newRecords) {
    String key = newIca.PRM_InfoCode__c + '_' +
                 (newIca.PRM_Account__c != null ? newIca.PRM_Account__c : newIca.PRM_HealthcareFacility__c);
    if(existingActiveMap.containsKey(key)) {
        newIca.addError('Duplicate active Info Code Assignment. Terminate the existing assignment before creating a new one.');
    }
}
```

**Effort:** 3 story points

---

#### Validation 5.2: Warn if Practice-Level Assignment Doesn't Match Practitioner-Level (Optional)

**Business Rule:**
If a practice location is marked as "Concierge Provider" but not all practitioners at that location are marked concierge, display a warning (not an error).

**Implementation:**
```apex
// In trigger or batch job:
// For each practice location with Concierge Info Code Assignment:
//   Query all practitioners at that location (via HealthcarePractitionerFacility)
//   Check if all have Concierge Info Code Assignment
//   If not all, create data quality warning/report
```

**Effort:** 5 story points (low priority)

---

### 6. Trigger Infrastructure (Already Exists - Reuse)

**Files Impacted:**
- `PRM_InfoCodeAssTrigger.trigger`
- `PRM_InfoCodeAssTriggerHelper.cls`

**Current State:**
Per PNC/Delegated pattern, this trigger already exists and handles Info Code Assignment changes. It includes logic for:
- Delegated flag rollup (sets Account.PRM_Delegated__c based on delegation Info Code Assignments)
- PNC integration (if applicable)

**Required Changes:**

#### Change 6.1: Add Concierge Info Code Handling to Trigger Helper (Optional Rollup)

**Location:** `PRM_InfoCodeAssTriggerHelper.cls` → `setAccountData` method

**Business Rule Question:**
❓ **Do we need a rollup field on Account for Concierge status?**
- **Option A:** No - Feeds query Info Code Assignments directly (recommended)
- **Option B:** Yes - Add `Account.PRM_ConciergePCP__c` boolean for quick access

**If Option B (rollup to Account field):**

```apex
// In PRM_InfoCodeAssTriggerHelper.setAccountData:
// After handling Delegated rollup, add Concierge rollup:

// Map: Account Id → Has Active Concierge PCP Assignment
Map<Id, Boolean> accountToConciergePCPMap = new Map<Id, Boolean>();

// Query all active Concierge PCP assignments for affected accounts
for(PRM_InfoCodeAssignment__c ica : [
    SELECT PRM_Account__c, PRM_HealthcareFacility__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_InfoCode__r.Name = 'Concierge PCP'
    AND (PRM_Account__c IN :accountIds OR PRM_HealthcareFacility__c IN :relatedAccountIds)
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
]) {
    if(ica.PRM_Account__c != null) {
        accountToConciergePCPMap.put(ica.PRM_Account__c, true);
    }
    // If practice-level assignment, apply logic (all practices concierge → practitioner concierge?)
}

// Update Account.PRM_ConciergePCP__c
for(Id accId : accountIds) {
    Boolean isConcierge = accountToConciergePCPMap.containsKey(accId) && accountToConciergePCPMap.get(accId);
    // Update account map
}
```

**Effort:** 5 story points (if rollup is needed)

**Recommendation:** **Avoid rollup** - Query Info Code Assignments directly in feeds to keep logic simple and flexible.

---

## Flows with No Changes Needed

### ✅ No Changes Required

| Flow | Reason |
|------|--------|
| **PNC Rollup Logic** | PNC uses `PRM_PNC__c` field; Concierge uses Info Code Assignments - separate patterns |
| **Delegated Rollup Logic** | Delegated uses `PRM_Delegated__c` field; Concierge uses Info Code Assignments - separate patterns |
| **Most OmniScripts** | Unless OmniScript needs to display/edit Concierge status, no changes required (Info Code Assignments managed separately) |
| **Provider Search** | If search already includes Info Code Assignments, no change needed; if not, add as enhancement (optional) |

---

## Detailed Flow Analysis

### Flow: Case Denial/Closure

**Pattern:** PNC Ancillary User Stories (Close_Case_PNC_Ancillary_User_Stories.md)

**Existing Logic (Line 193):**
```
| 15 | PRM_InfoCodeAssignment__c | PRM_PNCPDABatch, InitialCredPDAReviewUpdateSubIPInsert |
     Info codes at Practice Location and Practitioner level; PRM_CaseManager__c,
     PRM_HealthcareFacility__c or PRM_Account__c | PRM_Pending__c = false *(verify field exists)*
```

**Implementation Notes (Line 203):**
```
Add handling for PRM_InfoCodeAssignment__c (PRM_CaseManager__c, PRM_HealthcareFacility__c,
PRM_Account__c) – query where PRM_Pending__c = true and PRM_CaseManager__c = caseManagerId
```

**What This Means for Concierge:**
✅ **No special handling needed!** The existing PNC logic already updates **ALL Info Code Assignments** (including Concierge PCP and Concierge Provider) when a Case Manager is denied/closed. The query filters by `PRM_CaseManager__c = caseManagerId` and does not filter by specific Info Code names, so it handles all Info Code types.

**Verification Needed:**
- [ ] Confirm `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` includes PRM_InfoCodeAssignment__c in its update logic
- [ ] If not yet implemented for PNC, implement for both PNC and Concierge in same change

---

### Flow: RCAT Exclusion

**Pattern:** PNC Analysis (PRM_PNC_Analysis.md, Line 176)
```
PRM_CheckCAQHAccessOnDueAccountsBatch | Excludes PNC practitioners from CAQH access checks:
PRM_PNC__c = false in query. PNC practitioners don't need CAQH recredentialing validation.
```

**Decision Point:**
Should Concierge providers follow the same pattern?
- If **Yes**: Exclude practitioners with active "Concierge PCP" Info Code Assignment from CAQH/RCAT checks
- If **No**: No changes needed

**Recommendation:** Confirm with business stakeholders.

---

### Flow: Termination Auto-Update

**Pattern:** Similar to terminating HealthcarePractitionerFacility when practitioner is terminated

**New Logic Needed:**
When practitioner or practice location is terminated, automatically set `PRM_TerminationDate__c` on all active Info Code Assignments.

**Benefit:** Keeps data consistent; prevents stale "active" assignments for terminated providers.

---

### Flow: DataRaptor Outputs

**Current State:**
Most DataRaptors output `Account.PRM_PNC__c` directly (field-based).

**New State:**
DataRaptors must query or derive Concierge status from Info Code Assignments.

**Options:**
1. **Add Extract step** in each DataRaptor to pull Info Code Assignments
2. **Create reusable DataRaptor** (`PRMDRExtractInfoCodeAssignments`) that other DataRaptors can call
3. **Add formula fields** to output boolean flags (IsConciergePC, IsConciergeProvider) derived from subquery

**Recommendation:** Option 2 (reusable DataRaptor) for maintainability.

---

## Implementation Checklist

### Phase 1: Core Info Code Setup (From Main User Stories)
- [ ] Story 1.1: Create "Concierge PCP" Info Code
- [ ] Story 2.1: Create "Concierge Provider" Info Code
- [ ] Story 1.2, 1.3: Enable assignments (practitioner and practice location) - Internal
- [ ] Story 2.2, 2.3: Enable assignments (practitioner and practice location) - External

### Phase 2: Case Workflow Integration (This Document)
- [ ] **Change 1.1**: Extend `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` to handle Info Code Assignments
  - Verify PRM_InfoCodeAssignment__c is in update list
  - Add unit tests for Concierge Info Code Assignment denial
- [ ] **Validation 5.1**: Add duplicate assignment prevention validation

### Phase 3: RCAT / Recredentialing Integration (This Document)
- [ ] **Business Decision**: Confirm if concierge providers are excluded from RCAT
- [ ] **Change 2.1**: (If yes) Exclude Concierge PCP from CAQH batch
- [ ] **Change 2.2**: (If yes) Exclude Concierge Provider from recred termination letter

### Phase 4: Termination Flow Integration (This Document)
- [ ] **Change 3.1**: Auto-terminate Info Code Assignments on practitioner termination
- [ ] **Change 3.2**: Auto-terminate Info Code Assignments on practice location termination
- [ ] Add unit tests for auto-termination

### Phase 5: DataRaptor / Feed Integration (This Document + Main User Stories)
- [ ] **Change 4.1**: Update practitioner DataRaptors to include Info Code Assignment data
- [ ] **Change 4.2**: (Optional) Create reusable `PRMDRExtractInfoCodeAssignments` DataRaptor
- [ ] Story 1.4: Configure DART feed
- [ ] Story 1.5: Configure Inquire Only feed
- [ ] Story 2.5: Configure Provider Directory feed

### Phase 6: Trigger / Rollup Logic (This Document)
- [ ] **Business Decision**: Confirm if rollup to Account field is needed (Option A: No rollup recommended)
- [ ] **Change 6.1**: (If rollup needed) Extend PRM_InfoCodeAssTriggerHelper for Concierge rollup
- [ ] (If no rollup) Verify existing trigger works without changes

### Phase 7: Validation / Data Quality (This Document + Main User Stories)
- [ ] **Validation 5.2**: (Optional) Add data quality check for practice vs practitioner mismatch
- [ ] Story 1.8: Implement data quality rules for Concierge PCP
- [ ] Extend DQ rules for Concierge Provider if needed

### Phase 8: Testing
- [ ] Unit tests: All Apex changes (case denial, termination, RCAT, trigger)
- [ ] Integration tests: Feeds (DART, Inquire Only, Provider Directory)
- [ ] End-to-end tests: PDA workflow → downstream system display
- [ ] UAT: PDA team, Analytics team, Provider Directory team

---

## Business Decisions Required

| # | Question | Options | Recommended | Impact |
|---|----------|---------|-------------|--------|
| **1** | Should concierge providers be excluded from RCAT/CAQH checks? | A: Yes (like PNC)<br>B: No | **A: Yes** (reduce admin burden for concierge) | Changes 2.1, 2.2 |
| **2** | Should we roll up Concierge status to Account field? | A: No (query assignments)<br>B: Yes (add Account.PRM_ConciergePCP__c) | **A: No** (keep simple) | Change 6.1 |
| **3** | Should Info Code Assignments auto-terminate on provider termination? | A: Yes<br>B: No (manual) | **A: Yes** (data consistency) | Changes 3.1, 3.2 |
| **4** | Should we validate practice-level vs practitioner-level consistency? | A: Yes (warning)<br>B: No | **B: No** (low priority) | Validation 5.2 |

---

## Estimated Effort Summary

| Category | Changes | Story Points | Priority |
|----------|---------|--------------|----------|
| **Case Denial/Closure** | 1 change + tests | 3 | P0 |
| **RCAT / Recredentialing** | 2 changes + tests | 8 | P1 (after business decision) |
| **Termination Flows** | 2 changes + tests | 10 | P1 |
| **DataRaptor / Feeds** | Multiple DataRaptors | 8 | P0 |
| **Validation** | Duplicate prevention | 3 | P1 |
| **Trigger (if rollup)** | 1 change (optional) | 5 | P2 (if needed) |
| **Total** | | **37 points** (excluding rollup) | |

**Combined with Main User Stories (52 points):** **~90 story points total**

---

## Next Steps

1. **Review this analysis** with business stakeholders and dev team
2. **Make business decisions** (RCAT exclusion, rollup, auto-termination)
3. **Prioritize changes** alongside main Info Code implementation
4. **Create detailed technical design** for high-priority changes
5. **Begin implementation** in phases (Core → Case → RCAT → Termination → Feeds)

---

**End of Document**
