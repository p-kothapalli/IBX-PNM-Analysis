# Par Form vs Our Implementation - Complete UI & Backend Comparison

## Executive Summary

Our LWC has **4 tracked fields that are NOT shown in the UI**, and is missing **4 additional fields** that Par Form shows. The Apex backend supports all these fields, but the UI form is incomplete.

---

## Field-by-Field Comparison

### ✅ Fields We Have in Both UI & Apex

| Field | UI Label | Par Form Label | Status |
|-------|----------|----------------|--------|
| Facility Name | "Facility Name" | "Group Practice Name" | ✅ Complete |
| Address Line 1 | "Address Line 1" | "Primary Office Address Line 1" | ✅ Complete |
| Address Line 2 | "Address Line 2" | "Primary Office Address Line 2" | ✅ Complete |
| City | "City" | "Primary Office City" | ✅ Complete |
| State | "State" | "Primary Office State" | ✅ Complete |
| Zip | "Zip Code" | "Primary Office Zip" | ✅ Complete |
| Zip4 | "Zip + 4" | "Primary Office Zip Four" | ✅ Complete |
| Phone | "Phone" | "Primary Office Phone" | ✅ Complete |
| Fax | "Fax" | "Primary Office Fax" | ✅ Complete |

**Total: 9 fields complete**

---

### ⚠️ Fields We Have in Apex & JS but NOT in UI

| Field | JavaScript Variable | Apex Parameter | Par Form Label | UI Location |
|-------|---------------------|----------------|----------------|-------------|
| County | `newLocationCounty` | `county` | "Primary Office County (*)" | ❌ MISSING |
| Phone Extension | `newLocationPhoneExtension` | `phoneExtension` | "Primary Phone Extension" | ❌ MISSING |
| Is Primary | `newLocationIsPrimary` | `isPrimary` | "Primary Practice (*)" | ❌ MISSING |
| Telehealth Only | `newLocationIsTelehealthOnly` | `isTelehealthOnly` | "Telehealth Only (*)" | ❌ MISSING |

**Impact:** Users cannot set these critical fields when creating locations, even though the backend fully supports them!

---

### ❌ Fields Par Form Has That We Don't Have Anywhere

| Par Form Field | Type | Description | Priority |
|----------------|------|-------------|----------|
| **Group NPI** | Text Input | NPI number for the group/location | MEDIUM |
| **Telehealth Enabled** | Checkbox | Whether telehealth is enabled (separate from "Telehealth Only") | LOW |
| **Taxonomy Codes** | Custom LWC | Specialty/taxonomy codes for the location | MEDIUM |
| **Assistive Aids** | Custom LWC | Assistive aids available at location | LOW |
| **Vendor Type** | Text (Read-only) | Auto-populated vendor type | LOW |

**Notes:**
- **Group NPI:** We already pass `groupNpi` parameter from the component context (from group search), but Par Form allows manual entry
- **Telehealth Enabled vs Telehealth Only:** Par Form has TWO separate fields
  - "Telehealth Enabled": Location offers telehealth as an option
  - "Telehealth Only": Location ONLY does telehealth (no physical visits)
- **Taxonomy Codes:** Uses custom LWC `prmPrimarySpecialtyLogicForAddressScreen`
- **Assistive Aids:** Uses custom LWC `prmAssisstiveAids`

---

## Par Form Address Screen Structure

### Primary Office Address Block
```
Group Practice Name                         (Text Input)
Group NPI                                   (Text Input)
Primary Practice (*)                        (Checkbox)
Telehealth Enabled                          (Checkbox)
Telehealth Only (*)                         (Checkbox)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Address Line 1 (*)                          (Text Input)
Address Line 2                              (Text Input)
City (*)                                    (Text Input)
State (*)                                   (Dropdown)
County (*)                                  (Dropdown - dependent on State)
Zip (*)                                     (Text Input)
Zip + 4                                     (Text Input)
Phone (*)                                   (Tel Input)
Phone Extension                             (Text Input)
Fax                                         (Tel Input)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vendor Type                                 (Text - Read-only)
[Taxonomy/Specialty Selection Component]    (Custom LWC)
[Assistive Aids Selection Component]        (Custom LWC)
```

### Additional Address Block
Same structure as Primary, with these additions:
- Can select existing address from dropdown
- Or manually enter new address
- Shows "Additional Address County" instead of "Primary Office County"

---

## Our Current UI Structure

### Create New Practice Location Form
```
Facility Name (*)                           (Text Input)      ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Address Line 1 (*)                          (Text Input)      ✅
Address Line 2                              (Text Input)      ✅
City (*)                                    (Text Input)      ✅
State (*)                                   (Text Input)      ✅
Zip Code (*)                                (Text Input)      ✅
Zip + 4                                     (Text Input)      ✅
Phone (*)                                   (Tel Input)       ✅
Fax                                         (Tel Input)       ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Cancel] [Create and Add Location]
```

---

## Missing UI Elements - Detailed Breakdown

### 🔴 CRITICAL - Backend Ready, Just Needs UI

#### 1. County Dropdown
- **Variable:** `newLocationCounty`
- **Apex Parameter:** `county`
- **Implementation:**
  ```html
  <lightning-combobox
      label="County"
      value={newLocationCounty}
      options={countyOptions}
      onchange={handleNewLocationFieldChange}
      data-field="county"
      required
      placeholder="Select county"
  ></lightning-combobox>
  ```
- **Dependency:** Need to implement state-to-county mapping
  - Par Form uses: `Address.PRM_CountyForUserInterface__c` (dependent on `Address.PRM_StateCounty__c`)
  - Options should update when State changes

#### 2. Phone Extension
- **Variable:** `newLocationPhoneExtension`
- **Apex Parameter:** `phoneExtension`
- **Implementation:**
  ```html
  <lightning-input
      label="Phone Extension"
      value={newLocationPhoneExtension}
      onchange={handleNewLocationFieldChange}
      data-field="phoneExtension"
      max-length="10"
      placeholder="1234 (optional)"
  ></lightning-input>
  ```

#### 3. Is Primary Practice Checkbox
- **Variable:** `newLocationIsPrimary`
- **Apex Parameter:** `isPrimary`
- **Implementation:**
  ```html
  <lightning-input
      type="checkbox"
      label="Primary Practice"
      checked={newLocationIsPrimary}
      onchange={handleNewLocationFieldChange}
      data-field="isPrimary"
  ></lightning-input>
  ```
- **Note:** Should show before address fields (like Par Form)

#### 4. Telehealth Only Checkbox
- **Variable:** `newLocationIsTelehealthOnly`
- **Apex Parameter:** `isTelehealthOnly`
- **Implementation:**
  ```html
  <lightning-input
      type="checkbox"
      label="Telehealth Only"
      checked={newLocationIsTelehealthOnly}
      onchange={handleNewLocationFieldChange}
      data-field="isTelehealthOnly"
  ></lightning-input>
  ```

---

### 🟡 MEDIUM PRIORITY - Need Full Implementation

#### 5. Group NPI Field
- **Current State:** We get NPI from group search context, but don't allow manual entry
- **Par Form:** Allows manual entry/override
- **Implementation:**
  ```html
  <lightning-input
      label="Group NPI"
      value={groupNpi}
      onchange={handleNpiChange}
      max-length="10"
      pattern="[0-9]{10}"
      placeholder="1234567890"
  ></lightning-input>
  ```

#### 6. Taxonomy/Specialty Codes
- **Par Form Component:** `prmPrimarySpecialtyLogicForAddressScreen`
- **Purpose:** Select specialty/taxonomy codes specific to this location
- **Implementation:** Would need to create similar custom component or integrate existing one
- **Related Records:** Creates PractitionerFacilityAffiliation records

---

### 🟢 LOW PRIORITY - Nice to Have

#### 7. Telehealth Enabled Checkbox
- **Different from "Telehealth Only"**
- "Telehealth Enabled" = Location offers telehealth as an option
- "Telehealth Only" = Location ONLY does telehealth
- Most locations are neither or just "Enabled"

#### 8. Assistive Aids Selection
- **Par Form Component:** `prmAssisstiveAids`
- **Purpose:** Select assistive aids available at location
- **Related Records:** Creates ProviderFeature records

#### 9. Vendor Type (Read-only)
- Auto-populated field showing vendor type
- Likely calculated from other fields

---

## Recommended Implementation Plan

### Phase 1: Add Missing UI Fields (CRITICAL)
**Effort:** 2-3 hours  
**Impact:** HIGH - Users can now set all supported backend fields

1. Add County dropdown (with state dependency logic)
2. Add Phone Extension input
3. Add Is Primary checkbox
4. Add Telehealth Only checkbox

**Files to Update:**
- `prmAddressGroupManager.html` - Add 4 form fields
- `prmAddressGroupManager.js` - Add county options logic, update `handleNewLocationFieldChange()` for checkboxes

### Phase 2: Group NPI Manual Entry (MEDIUM)
**Effort:** 1 hour  
**Impact:** MEDIUM - Allows override of auto-detected NPI

1. Add Group NPI input field
2. Allow editing even when NPI comes from group search

**Files to Update:**
- `prmAddressGroupManager.html` - Add NPI field
- `prmAddressGroupManager.js` - Add NPI validation

### Phase 3: Advanced Features (LOW Priority)
**Effort:** 8-16 hours  
**Impact:** LOW - Specialty codes and assistive aids

1. Integrate or create Taxonomy/Specialty selection component
2. Integrate or create Assistive Aids selection component
3. Update backend to create related records (PractitionerFacilityAffiliation, ProviderFeature)

---

## County Dropdown Implementation Details

### State-to-County Dependency
Par Form uses conditional picklist based on State selection:
- **Controlling Field:** `PrimaryOfficeAddressState` (State dropdown)
- **Dependent Field:** `PrimaryOfficeAddressCountry` (actually County, mislabeled in schema)
- **Option Source:** `Address.PRM_CountyForUserInterface__c`

### Implementation Options

#### Option 1: Apex Method (Recommended)
```apex
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getCountiesByState(String state) {
    List<Map<String, String>> countyOptions = new List<Map<String, String>>();
    
    // Query custom metadata or picklist values
    Schema.DescribeFieldResult fieldResult = Address.PRM_CountyForUserInterface__c.getDescribe();
    List<Schema.PicklistEntry> ple = fieldResult.getPicklistValues();
    
    // Filter by controlling value (State)
    for (Schema.PicklistEntry entry : ple) {
        if (entry.isActive()) {
            countyOptions.add(new Map<String, String>{
                'label' => entry.getLabel(),
                'value' => entry.getValue()
            });
        }
    }
    
    return countyOptions;
}
```

#### Option 2: Static County Mapping
Create static map in JS:
```javascript
const STATE_COUNTIES = {
    'NJ': ['Bergen', 'Essex', 'Hudson', 'Middlesex', ...],
    'PA': ['Philadelphia', 'Montgomery', 'Delaware', ...],
    'DE': ['New Castle', 'Kent', 'Sussex']
};
```

---

## Par Form Field Grouping

### Visual Layout Sections
1. **Header Section**
   - Group Name
   - Group NPI
   
2. **Location Attributes**
   - Primary Practice checkbox
   - Telehealth Enabled checkbox
   - Telehealth Only checkbox
   
3. **Physical Address**
   - Address lines, City, State, County, Zip
   
4. **Contact Information**
   - Phone, Extension, Fax
   
5. **Additional Information**
   - Vendor Type
   - Taxonomy codes
   - Assistive aids

---

## Summary of Action Items

### Immediate (Phase 1)
- [ ] Add County dropdown with state dependency
- [ ] Add Phone Extension input
- [ ] Add Is Primary checkbox
- [ ] Add Telehealth Only checkbox
- [ ] Update `handleNewLocationFieldChange()` to handle checkboxes
- [ ] Test all 4 fields flow through to Apex correctly

### Short Term (Phase 2)
- [ ] Add Group NPI manual entry field
- [ ] Add NPI validation (10 digits)
- [ ] Test NPI override functionality

### Long Term (Phase 3)
- [ ] Research taxonomy/specialty component requirements
- [ ] Research assistive aids component requirements
- [ ] Evaluate if these components are reusable from Par Form
- [ ] Implement backend record creation for PFAA and ProviderFeature

---

## File Locations

### Current Implementation
- **LWC HTML:** `/IBXQA/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.html`
- **LWC JS:** `/IBXQA/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.js`
- **Apex Class:** `/IBXQA/force-app/main/default/classes/PRM_AddressManagementService.cls`

### Par Form Reference
- **OmniScript:** `/IBXQA/vlocity_export/OmniScript/PRM_PractitionerParticipationAddressForm_English/`
- **Primary Address Block Elements:** Lines 13-89 in OmniScript structure
- **Additional Address Block Elements:** Lines 90-180 in OmniScript structure
- **Custom LWC Components:**
  - `prmPrimarySpecialtyLogicForAddressScreen` (Taxonomy)
  - `prmAssisstiveAids` (Assistive Aids)

---

## Testing Checklist

After implementing Phase 1 UI fields:

- [ ] County dropdown populates based on State selection
- [ ] County value saves to `newLocationCounty` variable
- [ ] Phone Extension saves to `newLocationPhoneExtension` variable
- [ ] Is Primary checkbox toggles `newLocationIsPrimary` boolean
- [ ] Telehealth Only checkbox toggles `newLocationIsTelehealthOnly` boolean
- [ ] All 4 fields pass through to `createNewLocation()` Apex call
- [ ] Verify County saves to Address.PRM_County__c
- [ ] Verify Phone Extension saves to Address.PRM_PhoneExtension__c
- [ ] Verify Is Primary saves to HealthcareFacility.PRM_Primary__c and HealthcarePractitionerFacility.IsPrimaryFacility
- [ ] Verify Telehealth Only saves to Location.PRM_TelehealthOnly__c and HealthcareFacility.PRM_TelehealthOnly__c
- [ ] Test required field validation for County (if required)
- [ ] Test form submission with all fields populated
- [ ] Test form submission with only required fields
