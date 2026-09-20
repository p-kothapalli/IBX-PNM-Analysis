# Phase 3 Implementation Guide - Taxonomy, Assistive Aids, and New Group Creation

## Executive Summary

Phase 3 adds **conditional record types** that depend on user selections:
- **Taxonomy/Specialty** codes (creates PractitionerFacilityAffiliation records)
- **Assistive Aids** (creates ProviderFeature records)
- **Affirming Care Categories** (creates AffirmingCareCategory records)
- **New Group Creation** (creates Account + HealthcareProviderNpi)

**Status:**
- ✅ Backend placeholder methods created
- ✅ New Group creation fully implemented
- ⚠️ Taxonomy/Assistive Aids awaiting UI implementation

---

## What's Implemented

### 1. **Backend Methods** ✅

Added to `PRM_AddressManagementService.cls`:

#### `addTaxonomiesToPractitionerFacility()`
```apex
@AuraEnabled
public static DeleteResponse addTaxonomiesToPractitionerFacility(
    String practitionerFacilityId,
    List<String> taxonomyIds,
    Boolean isPrimary
)
```
- **Purpose:** Link taxonomy/specialty codes to practitioner-facility relationship
- **Creates:** PractitionerFacilityAffiliation records
- **Status:** Placeholder - awaiting UI for taxonomy selection

#### `addAssistiveAidsToFacility()`
```apex
@AuraEnabled
public static DeleteResponse addAssistiveAidsToFacility(
    String facilityId,
    List<String> assistiveAidCodes
)
```
- **Purpose:** Add assistive aids/capabilities to location
- **Creates:** ProviderFeature records
- **Status:** Placeholder - awaiting UI for assistive aids selection

#### `addAffirmingCareCategories()`
```apex
@AuraEnabled
public static DeleteResponse addAffirmingCareCategories(
    String practitionerFacilityId,
    List<String> affirmingCareCategoryCodes
)
```
- **Purpose:** Add affirming care categories to practitioner-facility
- **Creates:** AffirmingCareCategory records
- **Status:** Placeholder - awaiting UI for category selection

#### `createNewGroup()` ✅ **FULLY IMPLEMENTED**
```apex
@AuraEnabled
public static DeleteResponse createNewGroup(
    String accountName,
    String taxId,
    String npi,
    String vendorType
)
```
- **Purpose:** Create new Group/Account when it doesn't exist
- **Creates:** 
  - Account record
  - HealthcareProviderNpi record (if NPI provided)
- **Status:** Fully implemented and ready to use
- **Validation:**
  - Checks for existing account with same name
  - Validates NPI is 10 digits
  - Sets Tax ID and Vendor Type if provided

---

## What's Needed for Full Implementation

### 2. **UI Components** ⚠️ **NOT YET IMPLEMENTED**

#### Taxonomy/Specialty Selection UI

**Requirements:**
- Multi-select component for taxonomy codes
- Primary specialty designation (radio or checkbox)
- Integration with CareTaxonomy object
- Display specialty names, not just codes

**Par Form Reference:**
- OmniScript Element: `prmPrimarySpecialtyLogicForAddressScreen`
- Location: `/vlocity_export/OmniScript/PRM_PractitionerParticipationAddressForm_English/`

**Sample Data Structure:**
```json
"CareTaxxonomyData": [
    {
        "CareTaxonomyCode": "207RG0300X",
        "CareTaxonomyId": "0bKD10000008Oq4MAE",
        "CareTaxonomyName": "Geriatric Medicine (Internal Medicine) Physician",
        "isPrimarySpecialty": true
    },
    {
        "CareTaxonomyCode": "2084P0805X",
        "CareTaxonomyId": "0bKD10000008OwVMAU",
        "CareTaxonomyName": "Geriatric Psychiatry Physician",
        "isPrimarySpecialty": false
    }
]
```

**Implementation Steps:**
1. Query CareTaxonomy object for available codes
2. Display in multi-select picklist or dual listbox
3. Allow user to mark one as primary
4. Pass selected IDs to `addTaxonomiesToPractitionerFacility()`

---

#### Assistive Aids Selection UI

**Requirements:**
- Multi-select component for assistive aid codes
- Common aids: 
  - AS = American Sign Language
  - TT = Taped Text
  - TR = Public Transportation
  - (many more - query from picklist)

**Par Form Reference:**
- OmniScript Element: `prmAssisstiveAids`
- Location: `/vlocity_export/OmniScript/PRM_PractitionerParticipationAddressForm_English/`

**Sample Data:**
```json
"CapabilitiesAtLocation": "American Sign Language;TT: Taped Text;TR: Public Transportation"
```

**Implementation Steps:**
1. Query ProviderFeature picklist values or custom object
2. Display as multi-select checkboxes
3. Pass selected codes to `addAssistiveAidsToFacility()`

---

#### Affirming Care Categories UI

**Requirements:**
- Multi-select for affirming care category codes
- Categories specific to LGBTQ+ care, etc.

**Implementation Steps:**
1. Query AffirmingCareCategory picklist values
2. Display as multi-select
3. Pass selected codes to `addAffirmingCareCategories()`

---

### 3. **New Group Creation UI** ⚠️ **BACKEND READY**

**UI Needed:**
```html
<!-- Add to prmAddressGroupManager.html -->
<lightning-button 
    label="Create New Group" 
    onclick={handleShowCreateNewGroup}>
</lightning-button>

<!-- New Group Form Modal -->
<template if:true={showCreateNewGroup}>
    <lightning-input label="Group Name" value={newGroupName} required></lightning-input>
    <lightning-input label="Tax ID / EIN" value={newGroupTaxId}></lightning-input>
    <lightning-input label="Group NPI" value={newGroupNpi} pattern="[0-9]{10}"></lightning-input>
    <lightning-combobox label="Vendor Type" value={newGroupVendorType} options={vendorTypeOptions}></lightning-combobox>
    <lightning-button label="Create Group" onclick={handleCreateNewGroup}></lightning-button>
</template>
```

**JavaScript:**
```javascript
import createNewGroup from '@salesforce/apex/PRM_AddressManagementService.createNewGroup';

async handleCreateNewGroup() {
    const result = await createNewGroup({
        accountName: this.newGroupName,
        taxId: this.newGroupTaxId,
        npi: this.newGroupNpi,
        vendorType: this.newGroupVendorType
    });
    
    if (result.success) {
        this.groupAccountId = result.facilityId; // New Account ID
        this.showToast('Success', result.message, 'success');
    } else {
        this.showToast('Error', result.message, 'error');
    }
}
```

---

## Phase 3 Implementation Priority

### **HIGH Priority** (Can implement now)
✅ **New Group Creation UI**
- Backend is fully ready
- Just needs simple form in LWC
- 4 fields: Name, Tax ID, NPI, Vendor Type

### **MEDIUM Priority** (Requires research)
⚠️ **Taxonomy Selection**
- Most important for practitioner credentialing
- Requires querying CareTaxonomy object
- Backend placeholder ready

### **LOW Priority** (Nice to have)
⚠️ **Assistive Aids Selection**
- Less commonly used
- Requires custom picklist or object query

⚠️ **Affirming Care Categories**
- Least commonly used
- Requires custom picklist or object query

---

## Testing Checklist

### When Taxonomy UI is Ready:
- [ ] Query CareTaxonomy object successfully
- [ ] Display available taxonomies in UI
- [ ] Allow selection of multiple taxonomies
- [ ] Allow marking one as primary
- [ ] Call `addTaxonomiesToPractitionerFacility()` successfully
- [ ] Verify PractitionerFacilityAffiliation records created

### When Assistive Aids UI is Ready:
- [ ] Query ProviderFeature picklist/object
- [ ] Display available aids in UI
- [ ] Allow selection of multiple aids
- [ ] Call `addAssistiveAidsToFacility()` successfully
- [ ] Verify ProviderFeature records created

### New Group Creation (Ready Now):
- [ ] Display New Group form
- [ ] Validate required field (Group Name)
- [ ] Validate NPI format (10 digits)
- [ ] Create Account record successfully
- [ ] Create HealthcareProviderNpi record if NPI provided
- [ ] Handle duplicate group names gracefully
- [ ] Return new Account ID to use in location creation

---

## Database Schema

### Objects Used in Phase 3:

**CareTaxonomy**
- Standard object for taxonomy/specialty codes
- Fields: Code, Name, Description

**PractitionerFacilityAffiliation (PFAA)**
- Custom object linking practitioner-facility to taxonomies
- Fields: PractitionerFacilityId, TaxonomyId, IsPrimary

**ProviderFeature**
- Custom object for assistive aids/capabilities
- Fields: FacilityId, FeatureCode, FeatureName

**AffirmingCareCategory**
- Custom object for affirming care categories
- Fields: PractitionerFacilityId, CategoryCode

**Account**
- Standard object for Groups
- Custom Fields: PRM_TaxId__c, PRM_VendorType__c

**HealthcareProviderNpi**
- Standard Health Cloud object for NPIs
- Fields: Npi, NpiType, AccountId

---

## File Locations

**Backend:**
- `/IBXQA/force-app/main/default/classes/PRM_AddressManagementService.cls`
  - Lines 1573-1795: Phase 3 methods

**Frontend (To Be Created):**
- `/IBXQA/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.html`
  - Add New Group creation form
  - Add Taxonomy selection (when ready)
  - Add Assistive Aids selection (when ready)

**Par Form Reference:**
- `/IBXQA/vlocity_export/OmniScript/PRM_PractitionerParticipationAddressForm_English/`
  - Element: `prmPrimarySpecialtyLogicForAddressScreen` (Taxonomy)
  - Element: `prmAssisstiveAids` (Assistive Aids)

---

## Summary

**✅ What's Ready:**
- Backend methods for all Phase 3 features
- Full implementation of New Group creation
- Placeholder methods for Taxonomy/Assistive Aids

**⚠️ What's Needed:**
- UI for Taxonomy selection → HIGH PRIORITY
- UI for New Group creation → HIGH PRIORITY (backend ready)
- UI for Assistive Aids selection → MEDIUM PRIORITY
- UI for Affirming Care selection → LOW PRIORITY

**Next Steps:**
1. Deploy Phase 3 backend methods
2. Implement New Group Creation UI (simple form)
3. Research CareTaxonomy object structure
4. Build Taxonomy selection UI
5. Test end-to-end with all Phase 3 features
