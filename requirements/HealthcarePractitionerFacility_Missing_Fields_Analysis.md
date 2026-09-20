# HealthcarePractitionerFacility Missing Fields Analysis

## Current Implementation vs OmniScript Implementation

### Fields Currently Set (Our Code)
```apex
// PRM_AddressManagementService.cls:656-661
hpf.PractitionerId = practitionerId;
hpf.HealthcareFacilityId = facilityId;
hpf.PRM_CaseManager__c = caseManagerId;
hpf.PRM_IsErrorRecord__c = false;
```

### Fields Set by OmniScript
Based on `PRMDRPDelegatedPractionerPracticeLocations` DataRaptor:

1. **RecordTypeId** ✗ MISSING
   - Line 289: Maps from `PractitionerFacilities:RecordTypeId`
   - Retrieved from query: `SELECT Id FROM RecordType WHERE SobjectType = 'HealthcarePractitionerFacility' AND (DeveloperName = 'PRM_PractitionerPracticeAffiliation' OR DeveloperName = 'PRM_PractitionerLocationAffiliation') ORDER BY DeveloperName`
   - Uses: `%RecordTypeList|2:Id%` (Practice Location to Practitioner)

2. **AccountId** ✗ MISSING
   - Line 67: Maps from `PractitionerFacilities:AccountId`
   - This is the Group Account ID

3. **EffectiveFrom** ✗ MISSING
   - Line 89: Maps from `EffectiveFrom`
   - Typically set to TODAY() or effective date

4. **EffectiveTo** ✗ MISSING
   - Line 111: Maps from `EffectiveTo`
   - Typically null for active records

5. **IsActive** ✗ MISSING
   - Line 179: Maps from `IsActive`
   - Should be set based on status (true for active, false for pending)

6. **IsPrimaryFacility** ✗ MISSING
   - Line 201: Maps from `PractitionerFacilities:IsPrimary`
   - Indicates primary practice location

7. **PRM_AttestationDate__c** ✗ MISSING
   - Line 223: Maps from `AttestationDate`
   - Set to TODAY() when record is attested

8. **PRM_CaseManager__c** ✓ ALREADY SET
   - Line 245: Maps from `CaseManagerId`

9. **PractitionerId** ✓ ALREADY SET
   - Line 267: Maps from `PersonContactId`

10. **HealthcareFacilityId** ✓ ALREADY SET
    - Line 133: Maps from `PractitionerFacilities:PracticeLocation`

11. **PRM_IsErrorRecord__c** ✓ ALREADY SET
    - Not in OmniScript but set by our code

## Record Type Issue

**Problem:** Records are being created with the WRONG record type

**Expected Record Type:** 
- Developer Name: `PRM_PractitionerLocationAffiliation`  
- Label: `Practice Location to Practitioner`

**How OmniScript Gets It:**
```sql
SELECT Id FROM RecordType 
WHERE SobjectType = 'HealthcarePractitionerFacility' 
AND (DeveloperName = 'PRM_PractitionerPracticeAffiliation' 
     OR DeveloperName = 'PRM_PractitionerLocationAffiliation') 
ORDER BY DeveloperName
```

Returns (alphabetically):
1. Index 0: PRM_PractitionerLocationAffiliation (L < P)
2. Index 1: PRM_PractitionerPracticeAffiliation

Uses: `%RecordTypeList|2:Id%` → Should use index 1 (PRM_PractitionerPracticeAffiliation) or check the exact label

## Required Fix

Update `bulkAddLocations()` and `createNewLocation()` methods to include ALL missing fields:

```apex
@AuraEnabled
public static DeleteResponse bulkAddLocations(
    List<String> facilityIds, 
    String practitionerId, 
    String caseManagerId,
    String groupAccountId,  // NEW: Add this parameter
    Boolean isPrimary       // NEW: Add this parameter
) {
    // Get Record Type
    Id recordTypeId = Schema.SObjectType.HealthcarePractitionerFacility
        .getRecordTypeInfosByDeveloperName()
        .get('PRM_PractitionerLocationAffiliation')
        .getRecordTypeId();
    
    for (String facilityId : facilityIds) {
        HealthcarePractitionerFacility hpf = new HealthcarePractitionerFacility();
        hpf.RecordTypeId = recordTypeId;  // NEW
        hpf.PractitionerId = practitionerId;
        hpf.HealthcareFacilityId = facilityId;
        hpf.AccountId = groupAccountId;  // NEW
        hpf.PRM_CaseManager__c = caseManagerId;
        hpf.IsActive = false;  // NEW: Pending status
        hpf.IsPrimaryFacility = isPrimary;  // NEW
        hpf.EffectiveFrom = Date.today();  // NEW
        hpf.PRM_AttestationDate__c = Date.today();  // NEW
        hpf.PRM_IsErrorRecord__c = false;
        hpfRecords.add(hpf);
    }
}
```

## Summary

**Critical Missing Fields:**
1. ✗ RecordTypeId (CRITICAL - wrong record type)
2. ✗ AccountId (Group Account)
3. ✗ EffectiveFrom
4. ✗ IsActive
5. ✗ IsPrimaryFacility
6. ✗ PRM_AttestationDate__c

7. **PRM_Pending__c** ✗ MISSING
   - Line 1231: Maps from default value "true"
   - Should be set to true (records are pending until approved)

**Total Fields:** 12 total, 4 set correctly, 8 MISSING (7 before + PRM_Pending__c)
