# Address Validation Implementation Plan - Precisely Integration

**Date:** April 13, 2026  
**Feature:** Amazon-style Address Validation with Precisely API  
**Target:** prmAddressGroupManager LWC Component

---

## Overview

Implement address validation similar to Amazon's checkout process - show user what they entered vs. what Precisely API recommends, then let them choose which address to use.

**Triggers:**
1. When user creates a new location (Create and Add Location button)
2. When user saves changes to a pending location (Save button)

---

## Research Summary - Par Form Pattern

### How Par Form Implements This:

**Flow:**
1. User fills out address fields → Clicks Next/Submit
2. Backend calls **PRM_PreciselyAPIForParFormContainer** Integration Procedure
3. Precisely API validates address → Returns standardized version
4. User sees **"Address Validation"** screen with comparison
5. **Side-by-side display:**
   - Left: "Recommended Address" (Precisely validated)
   - Right: "Provided Address" (user entered)
6. User chooses: **Confirm** (use validated) or **Decline** (use entered)
7. Selected address continues to record creation

**UI Components Used:**
- `prmAddressComparisonParForm` - Container component
- `prmAdressBlockForParForm` - Individual address comparison blocks
- `lightning-radio-group` with "Confirm" / "Decline" buttons
- Warning messages for low confidence (≤ 50) or "No match found"

**Data Structure:**
```json
{
  "Recommended": {
    "AddressLine1": "1901 MARKET ST",
    "City": "PHILADELPHIA",
    "State": "PA",
    "PostalCode": "19103",
    "Zip4": "1234",
    "Confidence": 95,
    "Latitude": "39.9526",
    "Longitude": "-75.1652"
  },
  "Provided": {
    "AddressLine1": "1901 Market St",
    "City": "Philadelphia",
    "State": "PA",
    "PostalCode": "19103"
  }
}
```

---

## Implementation Plan for prmAddressGroupManager

### Phase 1: Backend Integration (Apex)

#### 1.1 Create Apex Method: `validateAddress()`

**Location:** `PRM_AddressManagementService.cls`

```apex
/**
 * Validates address using Precisely API via Integration Procedure
 * @param addressData Map containing address fields
 * @return Map with validated address and original address
 */
@AuraEnabled
public static Map<String, Object> validateAddress(Map<String, String> addressData) {
    Map<String, Object> result = new Map<String, Object>();
    
    try {
        // Prepare request payload
        Map<String, Object> requestPayload = new Map<String, Object>{
            'AddressLine1' => addressData.get('addressLine1'),
            'AddressLine2' => addressData.get('addressLine2'),
            'City' => addressData.get('city'),
            'StateProvince' => addressData.get('state'),
            'PostalCode' => addressData.get('zip'),
            'Country' => 'US'
        };
        
        // Call Integration Procedure
        Map<String, Object> ipInput = new Map<String, Object>{
            'address' => requestPayload
        };
        
        Map<String, Object> ipOutput = new Map<String, Object>();
        Map<String, Object> ipOptions = new Map<String, Object>();
        
        // Call PRM_IPPreciselyAPICall Integration Procedure
        vlocity_cmt.IntegrationProcedureService.runIntegrationProcedure(
            'PRM_IPPreciselyAPICall',
            ipInput,
            ipOutput,
            ipOptions
        );
        
        // Parse response
        if (ipOutput.containsKey('PreciselyResponse')) {
            Map<String, Object> apiResponse = (Map<String, Object>) ipOutput.get('PreciselyResponse');
            
            // Build result with validated and original addresses
            result.put('success', true);
            result.put('validated', parseValidatedAddress(apiResponse));
            result.put('original', addressData);
            result.put('confidence', apiResponse.get('Confidence'));
            result.put('hasMatch', apiResponse.get('Status.Code') != 'No match found');
            
        } else {
            // API call failed or no response
            result.put('success', false);
            result.put('error', 'Address validation service is currently unavailable');
            result.put('original', addressData);
        }
        
    } catch (Exception e) {
        result.put('success', false);
        result.put('error', e.getMessage());
        result.put('original', addressData);
    }
    
    return result;
}

private static Map<String, String> parseValidatedAddress(Map<String, Object> apiResponse) {
    Map<String, String> validated = new Map<String, String>();
    
    validated.put('addressLine1', (String) apiResponse.get('AddressLine1'));
    validated.put('addressLine2', (String) apiResponse.get('AddressLine2'));
    validated.put('city', (String) apiResponse.get('City'));
    validated.put('state', (String) apiResponse.get('StateProvince'));
    validated.put('zip', (String) apiResponse.get('PostalCode.Base'));
    validated.put('zip4', (String) apiResponse.get('PostalCode.AddOn'));
    validated.put('latitude', (String) apiResponse.get('Latitude'));
    validated.put('longitude', (String) apiResponse.get('Longitude'));
    validated.put('county', (String) apiResponse.get('USCountyName'));
    
    return validated;
}
```

---

### Phase 2: Frontend - Address Validation Modal Component

#### 2.1 Create New LWC: `addressValidationModal`

**Location:** `/force-app/main/default/lwc/addressValidationModal/`

**Purpose:** Show side-by-side comparison of addresses and let user choose

**Files:**
- `addressValidationModal.html`
- `addressValidationModal.js`
- `addressValidationModal.css`

**HTML Structure:**
```html
<template>
    <template if:true={showModal}>
        <section role="dialog" class="slds-modal slds-fade-in-open" aria-modal="true">
            <div class="slds-modal__container">
                
                <!-- Header -->
                <header class="slds-modal__header">
                    <h2 class="slds-modal__title">Address Validation</h2>
                    <p class="slds-m-top_x-small">
                        We found a standardized version of your address. Please review and select which address to use.
                    </p>
                </header>

                <!-- Body -->
                <div class="slds-modal__content slds-p-around_medium">
                    
                    <!-- Low Confidence Warning -->
                    <template if:true={showLowConfidenceWarning}>
                        <div class="slds-notify slds-notify_toast slds-theme_warning slds-m-bottom_medium" role="alert">
                            <lightning-icon icon-name="utility:warning" size="x-small" variant="warning"></lightning-icon>
                            <div class="slds-notify__content">
                                <p>
                                    The address validation service returned a low confidence match. 
                                    Please verify the recommended address is correct.
                                </p>
                            </div>
                        </div>
                    </template>

                    <!-- Side-by-Side Comparison -->
                    <div class="slds-grid slds-gutters slds-wrap">
                        
                        <!-- Recommended Address (Left) -->
                        <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                            <div class="address-block recommended">
                                <h3 class="slds-text-heading_small slds-m-bottom_x-small">
                                    <lightning-icon icon-name="utility:check" size="x-small" variant="success"></lightning-icon>
                                    Recommended Address
                                </h3>
                                <lightning-formatted-address
                                    street={validatedAddress.addressLine1}
                                    city={validatedAddress.city}
                                    province={validatedAddress.state}
                                    postal-code={validatedAddress.zip}
                                    country="US">
                                </lightning-formatted-address>
                                
                                <!-- Additional Details -->
                                <div class="slds-m-top_small slds-text-body_small">
                                    <template if:true={validatedAddress.zip4}>
                                        <p><strong>ZIP+4:</strong> {validatedAddress.zip}-{validatedAddress.zip4}</p>
                                    </template>
                                    <template if:true={validatedAddress.county}>
                                        <p><strong>County:</strong> {validatedAddress.county}</p>
                                    </template>
                                    <template if:true={confidence}>
                                        <p><strong>Confidence:</strong> {confidence}%</p>
                                    </template>
                                </div>

                                <!-- Confirm Button -->
                                <div class="slds-m-top_medium">
                                    <lightning-button
                                        label="Use Recommended Address"
                                        variant="brand"
                                        icon-name="utility:check"
                                        class="slds-size_1-of-1"
                                        onclick={handleConfirmValidated}>
                                    </lightning-button>
                                </div>
                            </div>
                        </div>

                        <!-- Provided Address (Right) -->
                        <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                            <div class="address-block provided">
                                <h3 class="slds-text-heading_small slds-m-bottom_x-small">
                                    Provided Address
                                </h3>
                                <lightning-formatted-address
                                    street={originalAddress.addressLine1}
                                    city={originalAddress.city}
                                    province={originalAddress.state}
                                    postal-code={originalAddress.zip}
                                    country="US">
                                </lightning-formatted-address>

                                <!-- Decline Button -->
                                <div class="slds-m-top_medium">
                                    <lightning-button
                                        label="Use Provided Address"
                                        variant="neutral"
                                        class="slds-size_1-of-1"
                                        onclick={handleDeclineValidated}>
                                    </lightning-button>
                                </div>
                            </div>
                        </div>

                    </div>

                    <!-- No Match Message -->
                    <template if:true={noMatch}>
                        <div class="slds-notify slds-notify_alert slds-theme_info slds-m-top_medium" role="alert">
                            <lightning-icon icon-name="utility:info" size="x-small"></lightning-icon>
                            <div class="slds-notify__content">
                                <p>
                                    We could not find a standardized match for this address. 
                                    You can proceed with the address you provided.
                                </p>
                            </div>
                        </div>
                    </template>

                </div>

                <!-- Footer -->
                <footer class="slds-modal__footer">
                    <lightning-button label="Cancel" onclick={handleCancel}></lightning-button>
                </footer>

            </div>
        </section>
        <div class="slds-backdrop slds-backdrop_open"></div>
    </template>
</template>
```

**JavaScript:**
```javascript
import { LightningElement, api } from 'lwc';

export default class AddressValidationModal extends LightningElement {
    @api validatedAddress;
    @api originalAddress;
    @api confidence;
    @api hasMatch;
    
    showModal = true;

    get showLowConfidenceWarning() {
        return this.confidence && this.confidence <= 50;
    }

    get noMatch() {
        return !this.hasMatch;
    }

    handleConfirmValidated() {
        // User selected validated address
        const selectedEvent = new CustomEvent('addressselected', {
            detail: {
                selectedAddress: this.validatedAddress,
                useValidated: true,
                standardized: true,
                latitude: this.validatedAddress.latitude,
                longitude: this.validatedAddress.longitude
            }
        });
        this.dispatchEvent(selectedEvent);
        this.showModal = false;
    }

    handleDeclineValidated() {
        // User selected original address
        const selectedEvent = new CustomEvent('addressselected', {
            detail: {
                selectedAddress: this.originalAddress,
                useValidated: false,
                standardized: false
            }
        });
        this.dispatchEvent(selectedEvent);
        this.showModal = false;
    }

    handleCancel() {
        const cancelEvent = new CustomEvent('cancel');
        this.dispatchEvent(cancelEvent);
        this.showModal = false;
    }
}
```

**CSS:**
```css
.address-block {
    border: 1px solid #dddbda;
    border-radius: 0.25rem;
    padding: 1rem;
    height: 100%;
}

.address-block.recommended {
    border-color: #4bca81;
    background-color: #f3f9f6;
}

.address-block.provided {
    background-color: #fafaf9;
}
```

---

### Phase 3: Integration into prmAddressGroupManager

#### 3.1 Update `prmAddressGroupManager.js`

**Add Import:**
```javascript
import validateAddress from '@salesforce/apex/PRM_AddressManagementService.validateAddress';
```

**Add State Variables:**
```javascript
@track showAddressValidationModal = false;
@track validationResult = null;
@track pendingAddressData = null;
```

**Update `handleCreateNewLocation()` Method:**
```javascript
async handleCreateNewLocation() {
    try {
        // Validate all required fields
        if (!this.validateNewLocationFields()) {
            return;
        }

        this.showSpinner = true;

        // STEP 1: Validate address with Precisely
        const addressToValidate = {
            addressLine1: this.newLocationAddress1,
            addressLine2: this.newLocationAddress2,
            city: this.newLocationCity,
            state: this.newLocationState,
            zip: this.newLocationZip,
            zip4: this.newLocationZip4
        };

        this.pendingAddressData = {
            ...addressToValidate,
            phone: this.newLocationPhone,
            phoneExtension: this.newLocationPhoneExtension,
            fax: this.newLocationFax,
            facilityName: this.newLocationName,
            groupNpi: this.newLocationGroupNpi,
            isPrimary: this.newLocationIsPrimary,
            isTelehealthOnly: this.newLocationIsTelehealthOnly,
            county: this.newLocationCounty
        };

        // Call Precisely API
        const validationResponse = await validateAddress({ addressData: addressToValidate });

        this.showSpinner = false;

        // STEP 2: Show validation modal if API succeeded
        if (validationResponse.success && validationResponse.validated) {
            this.validationResult = validationResponse;
            this.showAddressValidationModal = true;
            // Wait for user selection (handled in handleAddressSelected)
        } else {
            // API failed or unavailable - proceed with entered address
            console.warn('Address validation unavailable:', validationResponse.error);
            await this.proceedWithLocationCreation(this.pendingAddressData, false);
        }

    } catch (error) {
        this.showSpinner = false;
        this.showToast('Error', 'Error validating address: ' + error.body?.message || error.message, 'error');
    }
}

handleAddressSelected(event) {
    const { selectedAddress, useValidated, standardized, latitude, longitude } = event.detail;
    
    // Merge selected address with pending data
    const finalAddressData = {
        ...this.pendingAddressData,
        ...selectedAddress,
        standardized: standardized,
        latitude: latitude,
        longitude: longitude
    };

    this.showAddressValidationModal = false;
    this.proceedWithLocationCreation(finalAddressData, standardized);
}

handleAddressValidationCancel() {
    this.showAddressValidationModal = false;
    this.pendingAddressData = null;
    this.validationResult = null;
}

async proceedWithLocationCreation(addressData, isStandardized) {
    try {
        this.showSpinner = true;

        // Call existing createNewLocation method with selected address
        const result = await createNewLocation({
            practitionerId: this.practitionerId,
            groupAccountId: this.groupAccountId,
            facilityName: addressData.facilityName,
            groupNpi: addressData.groupNpi,
            telehealthOnly: addressData.isTelehealthOnly,
            isPrimary: addressData.isPrimary,
            addressLine1: addressData.addressLine1,
            addressLine2: addressData.addressLine2,
            city: addressData.city,
            state: addressData.state,
            zip: addressData.zip,
            zip4: addressData.zip4,
            phone: addressData.phone,
            phoneExtension: addressData.phoneExtension,
            fax: addressData.fax,
            county: addressData.county,
            latitude: addressData.latitude,
            longitude: addressData.longitude,
            standardized: isStandardized,
            taxonomyIds: [],
            networkIds: []
        });

        this.showSpinner = false;

        if (result.success) {
            this.showToast('Success', 'Location created successfully', 'success');
            this.resetNewLocationForm();
            await this.loadExistingLocations();
        } else {
            this.showToast('Error', result.message, 'error');
        }

    } catch (error) {
        this.showSpinner = false;
        this.showToast('Error', 'Error creating location: ' + error.body?.message || error.message, 'error');
    }
}
```

**Update `handleSaveLocation()` Method (for Pending Locations):**
```javascript
async handleSaveLocation(event) {
    try {
        const locationId = event.target.dataset.id;
        const location = this.pendingLocationsList.find(loc => loc.id === locationId);

        if (!location) {
            return;
        }

        // Validate required fields
        if (!this.validatePendingLocationFields(location)) {
            return;
        }

        this.showSpinner = true;

        // STEP 1: Validate address with Precisely
        const addressToValidate = {
            addressLine1: location.addressLine1,
            addressLine2: location.addressLine2,
            city: location.city,
            state: location.state,
            zip: location.zip,
            zip4: location.zip4
        };

        this.pendingAddressData = {
            ...location,
            locationId: locationId
        };

        // Call Precisely API
        const validationResponse = await validateAddress({ addressData: addressToValidate });

        this.showSpinner = false;

        // STEP 2: Show validation modal if API succeeded
        if (validationResponse.success && validationResponse.validated) {
            this.validationResult = validationResponse;
            this.showAddressValidationModal = true;
            // Wait for user selection
        } else {
            // API failed - proceed with entered address
            console.warn('Address validation unavailable:', validationResponse.error);
            await this.proceedWithLocationUpdate(this.pendingAddressData, false);
        }

    } catch (error) {
        this.showSpinner = false;
        this.showToast('Error', 'Error validating address: ' + error.body?.message || error.message, 'error');
    }
}

async proceedWithLocationUpdate(locationData, isStandardized) {
    try {
        this.showSpinner = true;

        // Call existing updatePractitionerLocation method
        const result = await updatePractitionerLocation({
            practitionerFacilityId: locationData.id,
            facilityId: locationData.facilityId,
            practitionerId: this.practitionerId,
            groupAccountId: this.groupAccountId,
            facilityName: locationData.facilityName,
            practiceName: locationData.practiceName,
            groupNpi: locationData.groupNpi,
            addressLine1: locationData.addressLine1,
            addressLine2: locationData.addressLine2,
            city: locationData.city,
            state: locationData.state,
            zip: locationData.zip,
            zip4: locationData.zip4,
            phone: locationData.phone,
            phoneExtension: locationData.phoneExtension,
            fax: locationData.fax,
            county: locationData.county,
            latitude: locationData.latitude,
            longitude: locationData.longitude,
            standardized: isStandardized,
            isPrimary: locationData.isPrimary,
            isActive: locationData.isActive
        });

        this.showSpinner = false;

        if (result.success) {
            this.showToast('Success', 'Location updated successfully', 'success');
            await this.loadExistingLocations();
        } else {
            this.showToast('Error', result.message, 'error');
        }

    } catch (error) {
        this.showSpinner = false;
        this.showToast('Error', 'Error updating location: ' + error.body?.message || error.message, 'error');
    }
}
```

#### 3.2 Update `prmAddressGroupManager.html`

**Add Address Validation Modal:**
```html
<!-- Address Validation Modal -->
<template if:true={showAddressValidationModal}>
    <c-address-validation-modal
        validated-address={validationResult.validated}
        original-address={validationResult.original}
        confidence={validationResult.confidence}
        has-match={validationResult.hasMatch}
        onaddressselected={handleAddressSelected}
        oncancel={handleAddressValidationCancel}>
    </c-address-validation-modal>
</template>
```

---

### Phase 4: Backend Updates

#### 4.1 Update `createNewLocation()` Method Parameters

**Add to PRM_AddressManagementService.cls:**

```apex
@AuraEnabled
public static DeleteResponse createNewLocation(
    String practitionerId,
    String groupAccountId,
    String facilityName,
    String groupNpi,
    Boolean telehealthOnly,
    Boolean isPrimary,
    String addressLine1,
    String addressLine2,
    String city,
    String state,
    String zip,
    String zip4,
    String phone,
    String phoneExtension,
    String fax,
    String county,
    Decimal latitude,    // NEW
    Decimal longitude,   // NEW
    Boolean standardized, // NEW
    List<String> taxonomyIds,
    List<String> networkIds
) {
    // Existing logic...
    
    // Add geocoding to Location if standardized
    if (standardized && latitude != null && longitude != null) {
        loc.put('Latitude__c', latitude);
        loc.put('Longitude__c', longitude);
    }
    
    // Add standardized flag to Address
    if (Schema.SObjectType.Address.fields.getMap().containsKey('prm_standardized__c')) {
        addr.put('PRM_Standardized__c', standardized);
    }
    
    // Rest of existing logic...
}
```

#### 4.2 Update `updatePractitionerLocation()` Method

Add same parameters: `latitude`, `longitude`, `standardized`

---

### Phase 5: Configuration & Deployment

#### 5.1 Prerequisites

**Named Credential Configuration:**
- Ensure `PRM_Precisely_API` Named Credential exists
- Verify API credentials are valid
- Test endpoint connectivity

**Integration Procedure:**
- Verify `PRM_IPPreciselyAPICall` is deployed
- Test API callout manually
- Check response structure matches expected format

#### 5.2 Field Creation

**Location Object:**
- `Latitude__c` (Number, 18, 15)
- `Longitude__c` (Number, 18, 15)

**Address Object:**
- `PRM_Standardized__c` (Checkbox) - Flag to indicate if address was validated

#### 5.3 Deployment Order

1. Deploy Apex class updates (`PRM_AddressManagementService`)
2. Deploy new LWC component (`addressValidationModal`)
3. Deploy updated parent LWC (`prmAddressGroupManager`)
4. Create custom fields (if not exists)
5. Test end-to-end flow

---

## Testing Checklist

### ✅ Create New Location Flow

- [ ] Enter address fields
- [ ] Click "Create and Add Location"
- [ ] Verify Precisely API is called
- [ ] Modal appears with side-by-side comparison
- [ ] "Recommended Address" shows validated address
- [ ] "Provided Address" shows entered address
- [ ] Confidence score displays
- [ ] Low confidence warning shows if ≤ 50
- [ ] Click "Use Recommended Address" → Creates location with validated data
- [ ] Click "Use Provided Address" → Creates location with entered data
- [ ] Geocoding (lat/long) saved if validated address used
- [ ] Standardized flag set correctly

### ✅ Edit Pending Location Flow

- [ ] Edit address fields in pending location
- [ ] Click "Save"
- [ ] Verify Precisely API is called
- [ ] Modal appears with comparison
- [ ] Select address → Location updates correctly
- [ ] Geocoding updates if validated address used

### ✅ Error Handling

- [ ] Precisely API unavailable → Proceed with entered address
- [ ] Precisely API timeout → Show error, allow to proceed
- [ ] No match found → Modal shows info message, allow either address
- [ ] User clicks "Cancel" → Returns to form without saving

---

## Future Enhancements

1. **Batch Validation:** Validate multiple addresses at once (for bulk imports)
2. **Auto-Select:** If confidence > 90, auto-select validated address with option to change
3. **Address Suggestions:** Show multiple validated options if Precisely returns alternates
4. **Validation History:** Track which addresses were validated and when
5. **Configuration:** Admin setting to make validation optional vs. required

---

## Summary

This implementation replicates Amazon's address validation pattern using Precisely API, similar to how the Par Form implements it. The key differences:

- **Par Form:** Uses OmniScript with Integration Procedures
- **Our Implementation:** Uses custom LWC with Apex callout to same Integration Procedures

**Benefits:**
- ✅ Improved data quality with validated addresses
- ✅ Geocoding for mapping/routing features
- ✅ Clear user choice between entered and validated addresses
- ✅ Low confidence warnings prevent bad data
- ✅ Consistent with Par Form user experience

**Implementation Time:** 3-5 days
- Day 1: Apex methods and IP integration
- Day 2: LWC modal component
- Day 3: Integration into parent component
- Day 4: Testing and refinement
- Day 5: Deployment and user training
