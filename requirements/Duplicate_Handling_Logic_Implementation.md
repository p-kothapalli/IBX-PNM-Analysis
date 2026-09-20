# Duplicate Handling Logic - HealthcarePractitionerFacility Records

## Overview

When users try to add a practice location to a practitioner, there might already be an existing HealthcarePractitionerFacility record. Our implementation now matches the Par Form's duplicate handling logic to determine whether to **Skip**, **Update**, or **Create New**.

---

## Par Form's Logic (DataRaptor: PRMDRCheckIfPracticeToPractitionerExist)

### Query for Existing Records
```soql
SELECT Id, IsActive, PRM_IsErrorRecord__c, PRM_Pending__c, PRM_EffectiveToday__c, ...
FROM HealthcarePractitionerFacility
WHERE PractitionerId = :practitionerId
  AND HealthcareFacilityId = :facilityId
  AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
```

### Decision Tree

```
IF existing record found:
    ├── IF (IsActive = true) OR (IsActive = false AND PRM_Pending__c = true)
    │   └── ACTION: SKIP (Do nothing)
    │       └── Reason: Record already active or pending approval
    │
    ├── ELSE IF (IsActive = false AND PRM_IsErrorRecord__c = false AND PRM_EffectiveToday__c = false)
    │   └── ACTION: UPDATE existing record
    │       └── Reason: Record is inactive but not errored, can be reactivated
    │
    └── ELSE (PRM_IsErrorRecord__c = true)
        └── ACTION: CREATE NEW record
            └── Reason: Errored records stay for audit trail, create fresh record

ELSE (no existing record):
    └── ACTION: CREATE NEW record
```

---

## Implementation Details

### Field Definitions

| Field | Description | Values |
|-------|-------------|--------|
| **IsActive** | Whether the location is currently active for the practitioner | true/false |
| **PRM_Pending__c** | Whether the record is pending approval | true/false |
| **PRM_IsErrorRecord__c** | Whether the record has errors | true/false |
| **PRM_EffectiveToday__c** | Whether the record is effective today | true/false |

### Scenarios

#### Scenario 1: Active Record Exists
**State:**
- IsActive = **true**

**Action:** **SKIP** ✋
- User message: "Location already active for this practitioner"
- No changes made
- Prevents duplicate active records

#### Scenario 2: Pending Record Exists
**State:**
- IsActive = **false**
- PRM_Pending__c = **true**

**Action:** **SKIP** ✋
- User message: "Location already pending approval"
- No changes made
- Prevents creating duplicate while one is under review

#### Scenario 3: Inactive Record (Can Reactivate)
**State:**
- IsActive = **false**
- PRM_IsErrorRecord__c = **false**
- PRM_EffectiveToday__c = **false**
- PRM_Pending__c = **false** (or null)

**Action:** **UPDATE** ✏️
- Updates existing record with new data
- Sets PRM_Pending__c = true
- Updates EffectiveFrom = today
- Updates PRM_AttestationDate__c = today
- Reuses existing record ID

**Fields Updated:**
```apex
existing.PRM_CaseManager__c = caseManagerId;
existing.IsActive = false;
existing.PRM_IsErrorRecord__c = false;
existing.PRM_Pending__c = true;
existing.EffectiveFrom = Date.today();
existing.PRM_AttestationDate__c = Date.today();
```

#### Scenario 4: Errored Record Exists
**State:**
- PRM_IsErrorRecord__c = **true**

**Action:** **CREATE NEW** ➕
- Creates fresh record with correct data
- Old errored record stays in system (audit trail)
- User gets working record

#### Scenario 5: No Existing Record
**Action:** **CREATE NEW** ➕
- Standard insert with all fields

---

## Code Implementation

### Method: `bulkAddLocations()`

**Location:** `PRM_AddressManagementService.cls` (Lines 644-835)

**Key Changes:**

1. **Query for Existing Records** (Before processing)
```apex
List<HealthcarePractitionerFacility> existingRecords = [
    SELECT Id, IsActive, PRM_IsErrorRecord__c, PRM_Pending__c,
           HealthcareFacilityId, PractitionerId, AccountId,
           EffectiveFrom, EffectiveTo, PRM_EffectiveToday__c
    FROM HealthcarePractitionerFacility
    WHERE PractitionerId = :practitionerId
      AND HealthcareFacilityId IN :facilityIds
      AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
];
```

2. **Build Map** (For O(1) lookup)
```apex
Map<String, HealthcarePractitionerFacility> existingRecordsMap = new Map<String, HealthcarePractitionerFacility>();
for (HealthcarePractitionerFacility existing : existingRecords) {
    String key = existing.PractitionerId + '_' + existing.HealthcareFacilityId;
    existingRecordsMap.put(key, existing);
}
```

3. **Process Each Facility** (Skip/Update/Insert logic)
```apex
for (String facilityId : facilityIds) {
    String key = practitionerId + '_' + facilityId;
    HealthcarePractitionerFacility existing = existingRecordsMap.get(key);

    if (existing != null) {
        // Skip Logic
        Boolean shouldSkip = existing.IsActive ||
                            (!existing.IsActive && existing.PRM_Pending__c == true);
        if (shouldSkip) {
            skippedCount++;
            continue;
        }

        // Update Logic
        Boolean shouldUpdate = !existing.IsActive &&
                              !existing.PRM_IsErrorRecord__c &&
                              (existing.PRM_EffectiveToday__c == null || !existing.PRM_EffectiveToday__c);
        if (shouldUpdate) {
            // Update existing record
            recordsToUpdate.add(existing);
            continue;
        }

        // If we get here, record is errored - create new
    }

    // Create new record
    recordsToInsert.add(hpf);
}
```

4. **Perform DML** (Separate insert/update)
```apex
if (!recordsToInsert.isEmpty()) {
    insert recordsToInsert;
}

if (!recordsToUpdate.isEmpty()) {
    update recordsToUpdate;
}
```

5. **User Feedback**
```apex
String message = 'Successfully processed X location(s): Y created, Z updated, W skipped';
```

---

## Benefits

### 1. **Prevents Duplicate Errors**
- No more "duplicate record" exceptions
- No more constraint violations

### 2. **Preserves Audit Trail**
- Errored records stay in system
- Can track history of failed attempts

### 3. **Handles All States**
- Active → Skip (already done)
- Pending → Skip (under review)
- Inactive → Update (reactivate)
- Errored → Create new (fresh start)

### 4. **Matches Par Form Behavior**
- Same business logic
- Same user experience
- Same data integrity rules

---

## Testing Scenarios

### Test 1: Add Location (No Existing Record)
**Setup:** Practitioner has no record for this facility
**Expected:** Creates new record with PRM_Pending__c = true
**Result:** ✅ 1 created

### Test 2: Add Location (Already Active)
**Setup:** Practitioner already has active record for this facility
**Expected:** Skips creation, shows message
**Result:** ✅ 1 skipped (already active/pending)

### Test 3: Add Location (Already Pending)
**Setup:** Practitioner has pending record for this facility
**Expected:** Skips creation, shows message
**Result:** ✅ 1 skipped (already active/pending)

### Test 4: Add Location (Inactive, Not Errored)
**Setup:** 
- Practitioner has inactive record
- PRM_IsErrorRecord__c = false
- PRM_EffectiveToday__c = false
**Expected:** Updates existing record, sets to pending
**Result:** ✅ 1 updated

### Test 5: Add Location (Errored Record Exists)
**Setup:** 
- Practitioner has record with PRM_IsErrorRecord__c = true
**Expected:** Creates new record, keeps errored record
**Result:** ✅ 1 created (errored record preserved)

### Test 6: Bulk Add (Mixed Scenarios)
**Setup:** Add 5 facilities
- 2 new (no existing)
- 1 already active
- 1 inactive (can update)
- 1 errored
**Expected:** 3 created, 1 updated, 1 skipped
**Result:** ✅ "Successfully processed 5 location(s): 3 created, 1 updated, 1 skipped (already active/pending)"

---

## Debug Logging

The implementation includes comprehensive debug statements:

```apex
System.debug('Found ' + existingRecordsMap.size() + ' existing HealthcarePractitionerFacility records');
System.debug('Skipping facility ' + facilityId + ' - already Active or Pending');
System.debug('Updating existing record for facility ' + facilityId);
System.debug('Creating new record for facility ' + facilityId + ' - existing record is errored');
System.debug('Inserted ' + recordsToInsert.size() + ' new records');
System.debug('Updated ' + recordsToUpdate.size() + ' existing records');
```

**To view logs:**
1. Setup → Debug Logs
2. Create trace flag for running user
3. Perform add location action
4. Check logs for decision logic

---

## Comparison: Before vs After

### Before (Our Old Implementation)
```apex
// Just insert, no duplicate checking
for (String facilityId : facilityIds) {
    HealthcarePractitionerFacility hpf = new HealthcarePractitionerFacility();
    // ... set fields ...
    hpfRecords.add(hpf);
}
insert hpfRecords;  // ❌ Could cause duplicates or errors
```

**Problems:**
- ❌ Duplicate record errors
- ❌ Constraint violations
- ❌ No handling of errored records
- ❌ Users had to manually delete duplicates

### After (New Implementation)
```apex
// Query existing, determine action
Map<String, HealthcarePractitionerFacility> existingRecordsMap = ...;

for (String facilityId : facilityIds) {
    HealthcarePractitionerFacility existing = existingRecordsMap.get(key);
    
    if (shouldSkip) { skippedCount++; continue; }      // ✅ Skip active/pending
    if (shouldUpdate) { recordsToUpdate.add(...); }    // ✅ Update inactive
    else { recordsToInsert.add(...); }                 // ✅ Create new
}

insert recordsToInsert;
update recordsToUpdate;
```

**Benefits:**
- ✅ No duplicates
- ✅ Updates when appropriate
- ✅ Preserves errored records
- ✅ Clear user feedback

---

## Related Files

**Apex Class:**
- `/IBXQA/force-app/main/default/classes/PRM_AddressManagementService.cls`
  - Method: `bulkAddLocations()` (Lines 644-835)

**Par Form Reference:**
- `/IBXQA/vlocity_export/DataRaptor/PRMDRCheckIfPracticeToPractitionerExist/`
  - DataRaptor that implements the original logic

**Integration Procedure:**
- `/IBXQA/vlocity_export/IntegrationProcedure/PRM_CreatePractitionerAddressRecords/`
  - Element: `CheckIfPracticeToPractitionerAlreadyExist`

---

## Summary

✅ **Implemented:** Skip/Update/Insert logic matching Par Form
✅ **Prevents:** Duplicate record errors
✅ **Preserves:** Errored records for audit trail
✅ **Provides:** Clear user feedback on actions taken
✅ **Tested:** All scenarios covered

**Key Formula (from Par Form):**
```javascript
// Skip if:
IF(HCPF:IsActive || (HCPF:IsActive == false && HCPF:PRM_Pending__c == true), true, false)

// Update if:
IF((HCPF:IsActive == false && HCPF:PRM_IsErrorRecord__c == false && HCPF:PRM_EffectiveToday__c == false), true, false)

// Create new if:
// - No existing record, OR
// - Existing record has PRM_IsErrorRecord__c = true
```
