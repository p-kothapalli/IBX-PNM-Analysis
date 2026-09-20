# Practitioner Participation Form - Complete Record Creation Analysis

## Executive Summary

When adding a location in the Practitioner Participation Form, the system creates **MULTIPLE related records**, not just HealthcarePractitionerFacility. Our current implementation only creates 1 record, while the Par Form creates at least 5-9 records depending on the scenario.

---

## Complete Record Creation Flow

### Integration Procedure Chain
```
PRM_PractitionerParticipationForm (OmniScript)
  → PRM_CreateParFormRecordsContainer
    → PRM_CreateParFormRecords  
      → PRM_CreatePractitionerAddressRecords
        → PRMDRCreatePractitionerNewAddressRecords (DataRaptor)
        → Multiple other DataRaptors for related records
```

---

## Records Created (In Sequence)

### Scenario: New Practice Location for New Group

#### 1. **Location** (Output Sequence: 1)
```apex
Location loc = new Location();
loc.Name = facilityName;
loc.LocationType = 'Site';
loc.PRM_CaseManager__c = caseManagerId;
loc.PRM_EffectiveFrom__c = effectiveDate;
loc.PRM_Pending__c = true;
loc.PRM_TelehealthOnly__c = isTelehealthOnly;
insert loc;
```

**Fields Set:**
- ✅ Name
- ✅ LocationType  
- ✅ PRM_CaseManager__c (IndividualApplication ID)
- ✅ PRM_EffectiveFrom__c
- ✅ PRM_Pending__c
- ✅ PRM_TelehealthOnly__c

---

#### 2. **Address** (Output Sequence: 2)
```apex
Address addr = new Address();
addr.ParentId = loc.Id;
addr.PRM_AddressLine1__c = addressLine1;
addr.PRM_AddressLine2__c = addressLine2;
addr.PRM_City__c = city;
addr.PRM_State__c = state;
addr.PRM_Zip__c = zip;
addr.PRM_Zip4__c = zip4;
addr.PRM_County__c = county;
addr.PRM_Phone__c = phone;
addr.PRM_PhoneExtension__c = phoneExtension;
addr.PRM_Fax__c = fax;
addr.PRM_IsErrorRecord__c = false;
addr.PRM_Active__c = false;
addr.PRM_Pending__c = true;
insert addr;
```

**Fields Set:**
- ✅ ParentId (Location)
- ✅ PRM_AddressLine1__c
- ✅ PRM_AddressLine2__c
- ✅ PRM_City__c
- ✅ PRM_State__c
- ✅ PRM_Zip__c
- ✅ PRM_Zip4__c
- ✅ PRM_County__c
- ✅ PRM_Phone__c
- ✅ PRM_PhoneExtension__c
- ✅ PRM_Fax__c
- ✅ PRM_IsErrorRecord__c
- ✅ PRM_Active__c
- ✅ PRM_Pending__c

---

#### 3. **HealthcareProviderNpi** (Output Sequence: 3)
```apex
HealthcareProviderNpi hpn = new HealthcareProviderNpi();
hpn.Name = 'NPI - ' + npiNumber;
hpn.ParentRecordId = loc.Id;
hpn.PRM_Type__c = 'NPI';
hpn.IdValue = npiNumber;
hpn.EffectiveDate = effectiveDate;
hpn.PRM_IsErrorRecord__c = false;
insert hpn;
```

**Fields Set:**
- ✅ Name
- ✅ ParentRecordId (Location)
- ✅ PRM_Type__c ('NPI')
- ✅ IdValue (NPI number)
- ✅ EffectiveDate
- ✅ PRM_IsErrorRecord__c

**Note:** This is the NPI for the LOCATION/GROUP, not the practitioner!

---

#### 4. **HealthcareFacility** (Output Sequence: 4)
```apex
HealthcareFacility hcf = new HealthcareFacility();
hcf.Name = facilityName;
hcf.AccountId = groupAccountId;
hcf.LocationId = loc.Id;
hcf.PRM_CaseManager__c = caseManagerId;
hcf.PRM_Primary__c = isPrimary;
hcf.PRM_Active__c = false;
hcf.PRM_Pending__c = true;
hcf.PRM_IsErrorRecord__c = false;
hcf.PRM_TelehealthOnly__c = isTelehealthOnly;
insert hcf;
```

**Fields Set:**
- ✅ Name
- ✅ AccountId (Group Account)
- ✅ LocationId
- ✅ PRM_CaseManager__c
- ✅ PRM_Primary__c
- ✅ PRM_Active__c
- ✅ PRM_Pending__c
- ✅ PRM_IsErrorRecord__c
- ✅ PRM_TelehealthOnly__c

---

#### 5. **HealthcarePractitionerFacility** (Output Sequence: 5)
```apex
Id recordTypeId = [SELECT Id FROM RecordType 
                   WHERE SobjectType = 'HealthcarePractitionerFacility' 
                   AND DeveloperName = 'PRM_PractitionerLocationAffiliation' 
                   LIMIT 1].Id;

HealthcarePractitionerFacility hpf = new HealthcarePractitionerFacility();
hpf.RecordTypeId = recordTypeId;
hpf.PractitionerId = practitionerId;
hpf.HealthcareFacilityId = hcf.Id;
hpf.AccountId = groupAccountId;
hpf.PRM_CaseManager__c = caseManagerId;
hpf.IsActive = false;
hpf.IsPrimaryFacility = isPrimary;
hpf.EffectiveFrom = effectiveDate;
hpf.PRM_AttestationDate__c = Date.today();
hpf.PRM_IsErrorRecord__c = false;
insert hpf;
```

**Fields Set:**
- ✅ RecordTypeId (PRM_PractitionerLocationAffiliation)
- ✅ PractitionerId
- ✅ HealthcareFacilityId
- ✅ AccountId
- ✅ PRM_CaseManager__c
- ✅ IsActive
- ✅ IsPrimaryFacility
- ✅ EffectiveFrom
- ✅ PRM_AttestationDate__c
- ✅ PRM_IsErrorRecord__c
- ✅ PRM_Pending__c (set to true)

---

### Additional Records Created (Based on Context)

#### 6. **HealthcareFacilityNetwork** (Conditional)
Created when the facility needs network assignments.

```apex
HealthcareFacilityNetwork hfn = new HealthcareFacilityNetwork();
hfn.HealthcareFacilityId = hcf.Id;
hfn.HealthPayerNetworkId = networkId;
hfn.EffectiveFrom = effectiveDate;
hfn.PRM_IsErrorRecord__c = false;
insert hfn;
```

**DataRaptor:** `CreatePractitionerFacilityNetwork`, `CreateParHealthCareFacilityNetworkAddaddress`

---

#### 7. **PractitionerFacilityAffiliation (PFAA)** (Conditional)
Created for practitioner facility affiliations.

```apex
// Created via multiple DataRaptors:
// - CreatePFAAManuallAddWithSameNPI
// - CreatePFAAWithDiffNPI
// - CreatePFAAExistingAddPractice
// - CreatePFANewAddress
```

---

#### 8. **AffirmingCareCategory (ACC)** (Conditional)
Created for affirming care categories.

```apex
// Created via multiple DataRaptors:
// - CreateAffirmingCareCategoryWithSameNPI
// - CreateAffirmingCareCategory
// - CreateAffCareCatExistingAddPractice
// - CreateAffCareCatWithDiffNPI
// - CreateAffCareCatNewAddress
```

---

#### 9. **ProviderFeature** (Conditional)
Created for provider features (assistive aids, etc.).

```apex
// Created via multiple DataRaptors:
// - CreateProviderFeatureManuallyAddWithSameNPI
// - CreateProviderFeatureManuallyAddWithDiffNPI
// - CreatePracProviderFeatureExistingAddPrac
// - CreateProviderFeatureNewAddress
// - CreateProviderFeatureACC
// - CreateProviderFeatureAssitiveAids
// - CreatePractitionerProviderFeature
```

---

## Our Current Implementation vs Par Form

### ✅ What We Create
| Record | Status |
|--------|--------|
| HealthcarePractitionerFacility | ✅ Created |

### ❌ What We're MISSING

| Record | Status | Impact |
|--------|--------|---------|
| **Location** | ❌ MISSING | HIGH - Cannot create Address without Location |
| **Address** | ❌ MISSING | HIGH - Address fields not stored |
| **HealthcareProviderNpi** | ❌ MISSING | MEDIUM - Group NPI not linked to location |
| **HealthcareFacility** | ❌ PARTIALLY CREATED | MEDIUM - Using existing, not creating new ones |
| HealthcareFacilityNetwork | ❌ MISSING | LOW - Network assignments not created |
| PractitionerFacilityAffiliation | ❌ MISSING | LOW - Additional affiliation records |
| AffirmingCareCategory | ❌ MISSING | LOW - ACC records not created |
| ProviderFeature | ❌ MISSING | LOW - Feature records not created |

---

## Critical Issues with Our Implementation

### 1. **Location Not Created**
- **Problem:** We link to existing HealthcareFacility but don't create new Location records
- **Impact:** For new practice locations, we should create Location → Address → HealthcareFacility
- **Solution:** Create Location first, then Address, then HealthcareFacility, then link via HealthcarePractitionerFacility

### 2. **Address Not Created**  
- **Problem:** Address details not stored in Address object
- **Impact:** Cannot query/filter by address fields independently
- **Solution:** Create Address record linked to Location

### 3. **HealthcareProviderNpi Not Created**
- **Problem:** Group NPI not linked to location
- **Impact:** Cannot query locations by NPI
- **Solution:** Create HealthcareProviderNpi record for location

### 4. **Only One Scenario Handled**
- **Problem:** We only handle "add existing facility to practitioner" scenario
- **Impact:** Cannot handle:
  - Create new location for existing group
  - Create new location for new group
  - Update existing location details
- **Solution:** Implement all scenarios like Par Form does

---

## Scenarios Handled by Par Form

### Scenario 1: Existing Address, Same NPI
- Uses existing Location/Address/HealthcareFacility
- Only creates HealthcarePractitionerFacility link

### Scenario 2: New Address, Same NPI (Existing Group)
- Creates: Location → Address → HealthcareProviderNpi → HealthcareFacility → HealthcarePractitionerFacility
- **This is what we should implement for "Add New Location"**

### Scenario 3: New Address, Different NPI (New Group)
- Creates: Location → Address → HealthcareProviderNpi → HealthcareFacility → HealthcarePractitionerFacility
- Plus all related records (networks, features, etc.)

---

## Recommended Implementation

### Phase 1: Core Records (CRITICAL)
1. ✅ HealthcarePractitionerFacility (DONE)
2. ❌ Location (TODO)
3. ❌ Address (TODO)
4. ❌ HealthcareProviderNpi (TODO)
5. ❌ HealthcareFacility (TODO - for new locations)

### Phase 2: Network & Features (MEDIUM Priority)
6. ❌ HealthcareFacilityNetwork
7. ❌ PractitionerFacilityAffiliation

### Phase 3: Additional Records (LOW Priority)
8. ❌ AffirmingCareCategory
9. ❌ ProviderFeature

---

## File References

### Integration Procedures
- `PRM_CreateParFormRecordsContainer`
- `PRM_CreateParFormRecords`
- `PRM_CreatePractitionerAddressRecords` ← **Main IP for address/location creation**
- `PRM_CreateDelegatedPractitionerPracticeLocationsRecords`

### DataRaptors
- `PRMDRCreatePractitionerNewAddressRecords` ← **Main DR for 5 core records**
- `PRMDRCreatePractitionerAddressRecordswithNPI`
- `PRMDRCreatePractitionerAddressRecordswithNPIDelg`
- Multiple DataRaptors for PFAA, ACC, ProviderFeature

### Key Files
- `/IBXQA/vlocity_export/IntegrationProcedure/PRM_CreatePractitionerAddressRecords/`
- `/IBXQA/vlocity_export/DataRaptor/PRMDRCreatePractitionerNewAddressRecords/`

---

## Summary

**Our Implementation:** Creates 1 record (HealthcarePractitionerFacility)

**Par Form Implementation:** Creates 5-9 records depending on scenario:
1. Location
2. Address  
3. HealthcareProviderNpi
4. HealthcareFacility
5. HealthcarePractitionerFacility
6. HealthcareFacilityNetwork (conditional)
7. PractitionerFacilityAffiliation (conditional)
8. AffirmingCareCategory (conditional)
9. ProviderFeature (conditional)

**Gap:** We are missing 4-8 records per location added!
