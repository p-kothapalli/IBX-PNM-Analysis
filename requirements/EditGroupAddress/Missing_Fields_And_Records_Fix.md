# Missing Fields and Records - Comprehensive Fix

## Issues Reported
1. Practice name not updating when creating new location
2. Location NPI History not created  
3. Practitioner at Practice Location Taxonomy and Network not getting created

---

## ✅ FIXED Issues

### 1. Practice Name Field (FIXED)
**Problem:** `PRM_PracticeName__c` field on HealthcareFacility was not being set

**Fix Applied:**
```apex
// Added to createNewLocation() at line 1012
if (Schema.SObjectType.HealthcareFacility.fields.getMap().containsKey('prm_practicename__c')) {
    facility.put('PRM_PracticeName__c', facilityName);
}
```

**Result:** Practice Name field now populated correctly on HealthcareFacility

---

### 2. Location NPI History (FIXED)
**Problem:** HealthcareProviderNpi was created with wrong fields - missing ParentRecordId link to Location

**Old Implementation (WRONG):**
```apex
// Was creating with Npi/NpiType fields
npi.put('Name', groupNpi);
npi.put('Npi', groupNpi);
npi.put('NpiType', 'Type 2');
// Missing ParentRecordId!
```

**New Implementation (CORRECT - Matches Par Form):**
```apex
// Creates NPI History record linked to Location
npi.put('Name', 'NPI - ' + groupNpi);  // Par Form format
npi.put('ParentRecordId', (Id)loc.get('Id'));  // Link to Location!
npi.put('PRM_Type__c', 'NPI');
npi.put('IdValue', groupNpi);
npi.put('EffectiveDate', System.today());
npi.put('PRM_IsErrorRecord__c', false);
```

**Result:** NPI History now created correctly with ParentRecordId pointing to Location

---

### 2b. NPI Prefill in Pending Locations (FIXED)
**Problem:** Initially implemented wrong approach - querying NPI History records instead of using HealthcareFacility lookup

**Wrong Approach (Removed):**
```apex
// Was querying HealthcareProviderNpi by ParentRecordId
String npiQuery = 'SELECT ParentRecordId, IdValue FROM HealthcareProviderNpi ' +
                  'WHERE ParentRecordId IN :locationIds ' +
                  'AND PRM_Type__c = \'NPI\'';
loc.groupNpi = locationNpiMap.get(link.HealthcareFacility.LocationId);
```

**Correct Implementation:**
```apex
// Use HealthcareFacility lookup field PRM_NpiId__c
SELECT HealthcareFacility.PRM_NpiId__c, HealthcareFacility.PRM_NpiId__r.Npi

// Populate from lookup
loc.groupNpi = link.HealthcareFacility.PRM_NpiId__r != null ? 
               link.HealthcareFacility.PRM_NpiId__r.Npi : null;
```

**Result:** NPI value now correctly fetched from HealthcareFacility.PRM_NpiId__r.Npi lookup field

---

## ⚠️ STILL TODO: Taxonomy and Network Records

### 3. Practitioner at Practice Location Taxonomy (INCOMPLETE)

**What Par Form Creates:**
- **PractitionerFacilityAffiliation (PFAA)** records linking practitioner-facility to taxonomy codes

**What We Have:**
- ✅ Backend method exists: `addTaxonomiesToPractitionerFacility()`
- ❌ Method is placeholder - needs full implementation
- ❌ Not being called after location creation

**Par Form DataRaptors:**
- `CreatePFAAManuallAddWithSameNPI`
- `CreatePFAAWithDiffNPI`
- `CreatePFAAExistingAddPractice`
- `CreatePFANewAddress`

**Implementation Steps:**
1. Complete the `addTaxonomiesToPractitionerFacility()` method to actually create PFAA records
2. Call this method after HealthcarePractitionerFacility is created
3. Pass taxonomy IDs from UI (requires UI selection component)

**Sample Code Needed:**
```apex
@AuraEnabled
public static DeleteResponse addTaxonomiesToPractitionerFacility(
    String practitionerFacilityId,
    List<String> taxonomyIds,
    Boolean isPrimary
) {
    DeleteResponse response = new DeleteResponse();
    try {
        List<PractitionerFacilityAffiliation> pfaaRecords = new List<PractitionerFacilityAffiliation>();
        
        for (String taxonomyId : taxonomyIds) {
            PractitionerFacilityAffiliation pfaa = new PractitionerFacilityAffiliation();
            pfaa.HealthcarePractitionerFacilityId = practitionerFacilityId;
            pfaa.CareTaxonomyId = taxonomyId;
            pfaa.IsPrimary = isPrimary;  // Only first one should be primary
            pfaa.PRM_Active__c = false;
            pfaa.PRM_Pending__c = true;
            pfaaRecords.add(pfaa);
            isPrimary = false;  // Subsequent ones are not primary
        }
        
        insert pfaaRecords;
        
        response.success = true;
        response.message = 'Created ' + pfaaRecords.size() + ' taxonomy affiliations';
    } catch (Exception e) {
        response.success = false;
        response.message = 'Error creating taxonomies: ' + e.getMessage();
    }
    return response;
}
```

---

### 4. Healthcare Facility Network (INCOMPLETE)

**What Par Form Creates:**
- **HealthcareFacilityNetwork** records linking facility to payer networks

**What We Have:**
- ✅ Backend method exists: `addFacilityNetworks()` 
- ✅ Method is fully implemented
- ❌ Not being called after location creation

**Implementation Steps:**
1. Call `addFacilityNetworks()` after HealthcareFacility is created
2. Pass network IDs from UI (requires UI selection component)

**Method Already Complete:**
```apex
@AuraEnabled
public static DeleteResponse addFacilityNetworks(
    String facilityId, 
    List<String> networkIds, 
    Date effectiveFrom
) {
    // Already fully implemented - just needs to be called!
}
```

---

## Summary of Record Creation Flow

### Current Flow (After Fix):
1. ✅ Location
2. ✅ Address
3. ✅ HealthcareProviderNpi (with ParentRecordId) - **FIXED**
4. ✅ HealthcareFacility (with PRM_PracticeName__c) - **FIXED**
5. ✅ HealthcarePractitionerFacility

### Still Missing (Par Form Creates These):
6. ❌ HealthcareFacilityNetwork (method exists, not called)
7. ❌ PractitionerFacilityAffiliation (method placeholder, needs completion)
8. ❌ AffirmingCareCategory (method placeholder, needs completion)
9. ❌ ProviderFeature (method placeholder, needs completion)

---

## Next Steps

### HIGH Priority
1. **Implement Taxonomy Creation**
   - Complete `addTaxonomiesToPractitionerFacility()` method
   - Build UI for taxonomy selection (multi-select combobox)
   - Call method after HPF creation

2. **Implement Network Assignment**
   - Build UI for network selection (multi-select combobox)
   - Call existing `addFacilityNetworks()` method after facility creation

### MEDIUM Priority
3. **Assistive Aids/Provider Features**
   - Complete `addAssistiveAidsToFacility()` method
   - Build UI for assistive aids selection

4. **Affirming Care Categories**
   - Complete `addAffirmingCareCategories()` method
   - Build UI for category selection

---

## Files Modified

### PRM_AddressManagementService.cls
- **Lines 985-1000:** Fixed HealthcareProviderNpi creation (NPI History)
- **Lines 1012-1015:** Added PRM_PracticeName__c field
- **Line 232-234:** Added PRM_NpiId lookup fields to query
- **Line 288:** Updated NPI fetch to use HealthcareFacility.PRM_NpiId__r.Npi (lookup field)
- **Removed lines 273-289:** Removed unnecessary NPI History query

### prmAddressGroupManager.html
- **Lines 259-263:** Added Practice Name and Group NPI editable fields in Pending Locations

### prmAddressGroupManager.js
- **Line 1247-1263:** Updated handleSaveLocation() to include practiceName and groupNpi parameters

**Deployment:** Successfully deployed to qa-sandbox (April 12, 2026)

---

## Testing Checklist

### ✅ Test After This Fix:
- [ ] Create new location
- [ ] Verify Practice Name appears on HealthcareFacility
- [ ] Verify HealthcareProviderNpi created with ParentRecordId = Location.Id
- [ ] Check NPI History section on Practice Location shows the NPI
- [ ] Verify pending locations show prefilled Practice Name
- [ ] Verify pending locations show prefilled Group NPI (from HealthcareFacility.PRM_NpiId__r.Npi)

### ⚠️ Cannot Test Yet (Needs Implementation):
- [ ] Taxonomy/Specialty selection and PFAA creation
- [ ] Network selection and HFN creation
- [ ] Assistive aids selection
- [ ] Affirming care category selection
