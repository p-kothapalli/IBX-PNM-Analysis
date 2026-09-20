# Practitioner Participation Form - Address/Group Selection Screen Editability Requirements

## Document Control
- **Version**: 1.0
- **Created**: April 10, 2026
- **Last Updated**: April 10, 2026
- **Author**: Business & Technical Requirements Team
- **Status**: Draft for Review

---

## Executive Summary

Business requires the ability to edit and manage address/group selections in the Practitioner Participation Form after submission. The current implementation locks data post-submission, making it difficult to correct mistakes or update information. This document outlines requirements for making the group selection screen fully editable with improved address matching and soft-delete capabilities.

### Key Improvements
1. **Post-Submission Editability**: Enable editing of address/group selections after form submission
2. **Soft Delete Capability**: Mark records as error/pending instead of hard deletes
3. **Pre-Population**: Load existing addresses with full edit capabilities
4. **Smart Address Matching**: Enhanced search using TaxID, NPI, and Address fields

---

## Current State Analysis

### Current Implementation Overview

**OmniScript**: PRM_PractitionerParticipationForm_English_112
**Custom LWC Component**: `prmTextElementOverrideForGroupSelection`
**Apex Classes**: 
- `PRM_PARProviderSearch` - Searches for existing groups and practice locations
- `PRM_ExistingAccountService` - Validates account status (terminated/duplicate)

### Current Group Selection Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Provider Enters Group Information                  │
│  - Group NPI (Required)                                      │
│  - Group Tax ID (Required)                                   │
│  - Group Name via Type-Ahead (Required)                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Automatic Group/Address Search                     │
│  - fetchProviderSearch() called via Apex                     │
│  - Searches for HealthcareFacility records                   │
│  - Retrieves PracticeLocation addresses                      │
│  - Returns: Primary, Mailing, Billing, Additional addresses │
└─────────────────────────────────────────────────────────────┘
                           ↓
         ┌─────────────────┴─────────────────┐
         ↓                                     ↓
┌──────────────────────┐          ┌──────────────────────┐
│ Single Match Found    │          │ Multiple Matches     │
│ - Auto-select         │          │ - Show Modal         │
│ - Skip to next step   │          │ - User selects       │
└──────────────────────┘          └──────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Group Selection Modal (if multiple matches)        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Main Address Selection Table                         │   │
│  │ Columns: Group Name, Full Address, Primary Specialty│   │
│  │          NPI, Phone, Primary Practice (Checkbox)    │   │
│  │ Action: Select 1 Primary Practice Location          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Additional Address Selection Table                   │   │
│  │ (Appears after main selection)                       │   │
│  │ Action: Select up to 10 Additional Locations         │   │
│  │ Note: Can click "here" to add unlisted locations    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  [Cancel]  [Save]                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Address Details Screen                             │
│  - Primary Address: Pre-populated (Current: READ-ONLY)      │
│  - Mailing Address: Pre-populated (Current: READ-ONLY)      │
│  - Billing Address: Pre-populated (Current: READ-ONLY)      │
│  - Additional Addresses: Pre-populated (Current: READ-ONLY) │
│  - Newly Added: Editable during current session only        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Submit Participation Form                          │
│  - Creates HealthcareFacility records                        │
│  - Creates Address records (Practice Location)               │
│  - Creates HealthcarePractitionerFacility associations       │
│  - Status: LOCKED - No further edits allowed                │
└─────────────────────────────────────────────────────────────┘
```

### Current Data Model

```
Account (Vendor/Group)
    ├── Identifier (TaxID/EIN)
    │   ├── PRM_Type__c = 'EIN'
    │   ├── IdValue = TaxID
    │   ├── PRM_Active__c (Boolean)
    │   ├── PRM_Pending__c (Boolean)
    │   └── PRM_IsErrorRecord__c (Boolean)
    │
    └── HealthcareFacility (Practice Locations)
        ├── LocationId (Links to Location/Address)
        ├── PRM_Primary__c (Boolean - Primary Practice)
        ├── PRM_Pending__c (Boolean)
        ├── PRM_IsErrorRecord__c (Boolean)
        └── HealthcarePractitionerFacility (Junction)
            ├── PractitionerId (Account - Practitioner)
            ├── FacilityId (HealthcareFacility)
            ├── PRM_Pending__c (Boolean)
            └── PRM_IsErrorRecord__c (Boolean)

Location (Standard Object - Addresses)
    └── Address (Compound Field)
        ├── PRM_AddressType__c ('Primary Practice', 'Practice', 'Mailing', 'Billing')
        ├── PRM_AddressLine1__c
        ├── PRM_AddressLine2__c
        ├── PRM_City__c
        ├── PRM_State__c
        ├── PRM_Zip__c
        ├── PRM_Zip4__c
        ├── PRM_County__c
        ├── PRM_Phone__c
        └── PRM_Fax__c
```

---

## Business Issues & Requirements

### Issue #1: Not Able to Edit After Submission

**Current Behavior**:
- Once practitioner participation form is submitted, address selections are locked
- Users cannot modify group selection or address information
- Requires opening a new case/form to make changes

**Business Impact**:
- Time-consuming workarounds (creating new forms)
- Data inconsistency (duplicate cases for same practitioner)
- Poor user experience for credentialing staff
- Delayed onboarding of practitioners

**Required Solution**:
```
┌─────────────────────────────────────────────────────────────┐
│  Post-Submission Edit Flow                                   │
│                                                              │
│  Case Status: Submitted/In Progress                          │
│  ↓                                                           │
│  [Edit Address/Group Selection] Button                       │
│  ↓                                                           │
│  Re-open Group Selection Modal                               │
│  - Display currently selected addresses                      │
│  - Allow changing primary practice                           │
│  - Allow adding/removing additional addresses                │
│  - Allow marking addresses as error                          │
│  ↓                                                           │
│  [Save Changes]                                              │
│  - Update HealthcareFacility associations                    │
│  - Update Address records                                    │
│  - Create audit trail (Field History Tracking)              │
│  - Update Case Activity Timeline                             │
└─────────────────────────────────────────────────────────────┘
```

**Technical Requirements**:
- Add "Edit Group Selection" button on submitted form review screen
- Store current selections in temporary object during edit session
- Implement versioning/audit trail for changes
- Validate that at least one primary practice is selected
- Support rollback if user cancels changes

---

### Issue #2: Cannot Delete Address Added by Mistake

**Current Behavior**:
- No delete functionality in address selection
- Once address is selected and saved, it cannot be removed
- Workaround: Manual backend data cleanup by administrators

**Business Impact**:
- Incorrect practitioner-to-location associations
- Network management issues (provider shows up in wrong networks)
- Billing/claims routing errors
- Manual cleanup overhead

**Required Solution - Soft Delete Pattern**:

Instead of hard deleting records (which would break referential integrity and audit trails), implement soft-delete using existing fields:

```sql
-- Soft Delete: Mark as Error Record
UPDATE HealthcareFacility 
SET PRM_IsErrorRecord__c = true,
    PRM_ErrorReason__c = 'Address added by mistake - removed by user',
    PRM_ErrorDate__c = TODAY
WHERE Id = :facilityIdToDelete;

-- Alternative: Mark as Non-Pending (if not yet activated)
UPDATE HealthcareFacility 
SET PRM_Pending__c = false,
    PRM_Active__c = false,
    PRM_InactivationReason__c = 'Address selection error'
WHERE Id = :facilityIdToDelete 
  AND PRM_Active__c = false; -- Only if not yet activated
```

**UI Design**:

```
┌─────────────────────────────────────────────────────────────┐
│  Selected Addresses                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ✓ Primary Practice                                    │   │
│  │   123 Main St, New York, NY 10001                     │   │
│  │   NPI: 1234567890                                     │   │
│  │   [Remove] (Disabled for Primary)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   Additional Address #1                               │   │
│  │   456 Oak Ave, Brooklyn, NY 11201                     │   │
│  │   NPI: 9876543210                                     │   │
│  │   [🗑️ Remove Address]  ← NEW FUNCTIONALITY             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   Additional Address #2                               │   │
│  │   789 Park Blvd, Queens, NY 11354                     │   │
│  │   NPI: 5555555555                                     │   │
│  │   [🗑️ Remove Address]  ← NEW FUNCTIONALITY             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Business Rules for Soft Delete**:
1. **Cannot remove Primary Practice** - Must always have exactly 1 primary
2. **Can remove Additional Addresses** - Up to 10, minimum 0
3. **Confirmation Dialog Required**:
   ```
   ⚠️ Remove Address?
   
   You are about to remove:
   456 Oak Ave, Brooklyn, NY 11201
   
   This will:
   - Mark the address as error record
   - Remove practitioner-facility association
   - Update network assignments
   
   ⚠️ This action can be undone by re-adding the address.
   
   [Cancel]  [Confirm Remove]
   ```

4. **Audit Trail**: Track who removed, when, and why
5. **Restoration Capability**: Admin can restore error-marked records if needed

**Technical Implementation**:

```javascript
// prmTextElementOverrideForGroupSelection.js
handleRemoveAddress(event) {
    const addressId = event.target.dataset.id;
    const addressInfo = this.selectedAdditionalLocs.find(loc => loc.FacilityId === addressId);
    
    // Prevent removing primary practice
    if (addressInfo.PrimaryPractice) {
        this.showToast('Error', 'Cannot remove primary practice location', 'error');
        return;
    }
    
    // Show confirmation modal
    this.addressToRemove = addressInfo;
    this.showRemoveConfirmation = true;
}

async confirmRemoveAddress() {
    try {
        // Call Apex to soft-delete
        await markAddressAsError({
            facilityId: this.addressToRemove.FacilityId,
            reason: 'Address added by mistake - removed by user',
            removedBy: this.currentUserId
        });
        
        // Remove from UI
        this.selectedAdditionalLocs = this.selectedAdditionalLocs.filter(
            loc => loc.FacilityId !== this.addressToRemove.FacilityId
        );
        
        // Update OmniScript JSON
        this.updateOmniDataJson();
        
        this.showToast('Success', 'Address removed successfully', 'success');
        this.showRemoveConfirmation = false;
    } catch (error) {
        this.showToast('Error', 'Failed to remove address: ' + error.message, 'error');
    }
}
```

```apex
// PRM_AddressManagementService.cls (NEW)
public class PRM_AddressManagementService {
    
    @AuraEnabled
    public static void markAddressAsError(String facilityId, String reason, String removedBy) {
        try {
            HealthcareFacility facility = [
                SELECT Id, PRM_IsErrorRecord__c, PRM_Pending__c, PRM_Active__c 
                FROM HealthcareFacility 
                WHERE Id = :facilityId 
                LIMIT 1
            ];
            
            // Soft delete logic
            facility.PRM_IsErrorRecord__c = true;
            facility.PRM_ErrorReason__c = reason;
            facility.PRM_ErrorDate__c = Date.today();
            facility.PRM_ErrorRecordCreatedBy__c = removedBy;
            
            // If not yet activated, also set pending to false
            if (!facility.PRM_Active__c) {
                facility.PRM_Pending__c = false;
            }
            
            update facility;
            
            // Log audit trail
            PRM_AuditLogger.log('Address Removal', facilityId, reason, removedBy);
            
        } catch (Exception e) {
            throw new AuraHandledException('Error removing address: ' + e.getMessage());
        }
    }
    
    @AuraEnabled
    public static void restoreAddress(String facilityId, String restoredBy) {
        try {
            HealthcareFacility facility = [
                SELECT Id, PRM_IsErrorRecord__c, PRM_Pending__c 
                FROM HealthcareFacility 
                WHERE Id = :facilityId 
                LIMIT 1
            ];
            
            facility.PRM_IsErrorRecord__c = false;
            facility.PRM_ErrorReason__c = null;
            facility.PRM_ErrorDate__c = null;
            facility.PRM_Pending__c = true; // Restore to pending status
            
            update facility;
            
            PRM_AuditLogger.log('Address Restoration', facilityId, 'Restored by ' + restoredBy, restoredBy);
            
        } catch (Exception e) {
            throw new AuraHandledException('Error restoring address: ' + e.getMessage());
        }
    }
}
```

---

### Issue #3: Pre-Population and Editability of Existing Addresses

**Current Behavior**:
- Existing addresses are pre-populated when practitioner reopens form
- Pre-populated addresses are READ-ONLY
- Only newly added addresses (in current session) are editable
- Creates confusion: "Why can't I edit this address?"

**Business Impact**:
- Users cannot correct outdated address information
- Phone numbers, fax numbers cannot be updated
- Suite/floor numbers in Address Line 2 cannot be modified
- Forces users to remove and re-add entire address

**Required Solution**:

```
┌─────────────────────────────────────────────────────────────┐
│  ALL Addresses Should Be Editable                            │
│                                                              │
│  Address Type: Primary Practice                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Address Line 1:  [123 Main Street           ] ← Edit  │   │
│  │ Address Line 2:  [Suite 400                ] ← Edit  │   │
│  │ City:            [New York                  ] ← Edit  │   │
│  │ State:           [NY ▼]                     ← Edit  │   │
│  │ Zip:             [10001                     ] ← Edit  │   │
│  │ Zip+4:           [1234                      ] ← Edit  │   │
│  │ County:          [New York                  ] ← Edit  │   │
│  │ Phone:           [(212) 555-0100            ] ← Edit  │   │
│  │ Phone Ext:       [123                       ] ← Edit  │   │
│  │ Fax:             [(212) 555-0199            ] ← Edit  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Status: ✓ Existing Address (Editable)                      │
│  Last Updated: 03/15/2026 by John Smith                     │
│  [Save Changes]  [Cancel]                                    │
└─────────────────────────────────────────────────────────────┘
```

**Edit Modes**:

| Address Source | Current Behavior | New Behavior |
|----------------|------------------|--------------|
| **Newly Added (Current Session)** | ✅ Editable | ✅ Editable |
| **Pre-Populated Existing** | ❌ Read-Only | ✅ Editable |
| **System-Generated** | ❌ Read-Only | ✅ Editable |
| **After Form Submission** | ❌ Locked | ✅ Editable (with permissions) |

**Field-Level Edit Rules**:

| Field | Editable? | Validation |
|-------|-----------|------------|
| Address Line 1 | ✅ Yes | Required, Max 255 chars |
| Address Line 2 | ✅ Yes | Optional, Max 255 chars |
| City | ✅ Yes | Required, Max 100 chars |
| State | ✅ Yes | Required, Picklist |
| Zip | ✅ Yes | Required, 5 digits |
| Zip+4 | ✅ Yes | Optional, 4 digits |
| County | ✅ Yes | Optional (auto-populated from Zip) |
| Phone | ✅ Yes | Required, Format: (XXX) XXX-XXXX |
| Phone Extension | ✅ Yes | Optional, Max 10 digits |
| Fax | ✅ Yes | Optional, Format: (XXX) XXX-XXXX |
| **Address Type** | ⚠️ Restricted | Can change between Practice types, cannot change Primary to Mailing/Billing without replacing Primary |
| **NPI** | ⚠️ Restricted | Can only edit if not yet submitted to CAQH |
| **Practice Location Number** | ❌ No | System-generated, read-only |

**Technical Implementation**:

```javascript
// prmAddressDetailsComponent.js (NEW or ENHANCED)
export default class PrmAddressDetailsComponent extends LightningElement {
    @api addressData;
    @api addressType; // 'primary', 'additional', 'mailing', 'billing'
    @api isEditable = true; // NEW: Default to editable
    @api isExisting = false; // NEW: Track if pre-populated
    
    @track editMode = false;
    @track originalData;
    
    handleEdit() {
        this.originalData = { ...this.addressData }; // Store original for cancel
        this.editMode = true;
    }
    
    handleSave() {
        // Validate all fields
        if (!this.validateFields()) {
            return;
        }
        
        // Call Apex to update address
        updateAddress({ 
            locationId: this.addressData.LocationId,
            addressData: this.addressData,
            updatedBy: this.currentUserId
        })
        .then(() => {
            this.showToast('Success', 'Address updated successfully', 'success');
            this.editMode = false;
            
            // Fire event to parent to refresh data
            this.dispatchEvent(new CustomEvent('addressupdated', {
                detail: { addressData: this.addressData }
            }));
        })
        .catch(error => {
            this.showToast('Error', 'Failed to update address: ' + error.message, 'error');
        });
    }
    
    handleCancel() {
        this.addressData = { ...this.originalData }; // Restore original
        this.editMode = false;
    }
    
    validateFields() {
        const allValid = [...this.template.querySelectorAll('lightning-input')]
            .reduce((validSoFar, inputCmp) => {
                inputCmp.reportValidity();
                return validSoFar && inputCmp.checkValidity();
            }, true);
        
        if (!allValid) {
            this.showToast('Error', 'Please correct all validation errors', 'error');
        }
        
        return allValid;
    }
}
```

**Change Tracking**:

```apex
// Track what changed for audit
public class PRM_AddressChangeTracker {
    public static void trackChanges(Location oldLoc, Location newLoc, String updatedBy) {
        List<String> changes = new List<String>();
        
        if (oldLoc.PRM_AddressLine1__c != newLoc.PRM_AddressLine1__c) {
            changes.add('Address Line 1: "' + oldLoc.PRM_AddressLine1__c + '" → "' + newLoc.PRM_AddressLine1__c + '"');
        }
        if (oldLoc.PRM_Phone__c != newLoc.PRM_Phone__c) {
            changes.add('Phone: "' + oldLoc.PRM_Phone__c + '" → "' + newLoc.PRM_Phone__c + '"');
        }
        // ... track all fields
        
        if (!changes.isEmpty()) {
            PRM_AuditLogger.log('Address Modified', newLoc.Id, String.join(changes, ', '), updatedBy);
        }
    }
}
```

---

### Issue #4: Improved Address Selection Process

**Current Challenges**:
- Large result sets (>50 addresses) are difficult to navigate
- Search by Zip only (for large result sets)
- No way to search by TaxID or NPI independently
- No fuzzy matching for address fields
- Users must scroll through long lists

**Business Requirements**:
1. **Multi-Field Search**: Search by TaxID, NPI, Address Line 1, City, State, Zip, Practice Location Number
2. **Smart Matching**: Prioritize exact matches, then partial matches
3. **Result Ranking**: Show "best matches" first based on multiple criteria
4. **Filter by Status**: Show only active, pending, or all addresses
5. **Quick Actions**: "Recently Used Addresses" for this practitioner

**Enhanced Search UI**:

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Smart Address Search                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Search by any combination:                           │   │
│  │                                                        │   │
│  │  Tax ID:              [12-3456789    ] ← NEW          │   │
│  │  NPI:                 [1234567890    ] ← NEW          │   │
│  │  Practice Location #: [PL-001234     ] ← ENHANCED     │   │
│  │  Address:             [123 Main      ] ← ENHANCED     │   │
│  │  City:                [New York      ] ← EXISTING     │   │
│  │  State:               [NY ▼]          ← EXISTING     │   │
│  │  Zip:                 [10001         ] ← EXISTING     │   │
│  │                                                        │   │
│  │  [🔍 Search]  [Clear Filters]                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Results (127 found, showing top 50 by relevance)            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Relevance: ████████░░ 85%                            │   │
│  │ ✓ 123 Main Street, Suite 400                          │   │
│  │   New York, NY 10001-1234                             │   │
│  │   TaxID: **-***6789  NPI: 1234567890                 │   │
│  │   Primary Specialty: Internal Medicine                │   │
│  │   Practice Location #: PL-001234                      │   │
│  │   Status: 🟢 Active                                   │   │
│  │   [Select as Primary]  [Select as Additional]         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  │ Relevance: ██████░░░░ 65%                            │   │
│  │   123 Main Street, Floor 2                            │   │
│  │   New York, NY 10001                                  │   │
│  │   TaxID: **-***4444  NPI: 9999999999                 │   │
│  │   Primary Specialty: Family Medicine                  │   │
│  │   Practice Location #: PL-005678                      │   │
│  │   Status: 🟡 Pending                                  │   │
│  │   [Select as Primary]  [Select as Additional]         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Smart Matching Algorithm**:

```apex
// PRM_SmartAddressSearch.cls (NEW)
public class PRM_SmartAddressSearch {
    
    public class SearchCriteria {
        @AuraEnabled public String taxId;
        @AuraEnabled public String npi;
        @AuraEnabled public String practiceLocationNumber;
        @AuraEnabled public String addressLine1;
        @AuraEnabled public String city;
        @AuraEnabled public String state;
        @AuraEnabled public String zip;
        @AuraEnabled public Boolean activeOnly;
    }
    
    public class SearchResult {
        @AuraEnabled public HealthcareFacility facility;
        @AuraEnabled public AddressData address;
        @AuraEnabled public Integer relevanceScore; // 0-100
        @AuraEnabled public List<String> matchReasons; // Why this matched
    }
    
    @AuraEnabled
    public static List<SearchResult> smartSearch(SearchCriteria criteria) {
        List<SearchResult> results = new List<SearchResult>();
        
        // Build dynamic SOQL query
        String query = buildSmartQuery(criteria);
        List<HealthcareFacility> facilities = Database.query(query);
        
        // Score and rank results
        for (HealthcareFacility facility : facilities) {
            SearchResult result = new SearchResult();
            result.facility = facility;
            result.relevanceScore = calculateRelevance(facility, criteria);
            result.matchReasons = getMatchReasons(facility, criteria);
            results.add(result);
        }
        
        // Sort by relevance score (descending)
        results.sort();
        
        return results;
    }
    
    private static String buildSmartQuery(SearchCriteria criteria) {
        String query = 'SELECT Id, Name, LocationId, PRM_Primary__c, ' +
                       'Location.PRM_AddressLine1__c, Location.PRM_City__c, ' +
                       'Location.PRM_State__c, Location.PRM_Zip__c, ' +
                       'PRM_IdentifierHealthcareFacility__r.Name, ' +
                       'Account.Name, AccountId ' +
                       'FROM HealthcareFacility ' +
                       'WHERE PRM_IsErrorRecord__c = false ';
        
        // Add filters based on criteria
        if (criteria.activeOnly) {
            query += 'AND PRM_Active__c = true ';
        }
        
        if (String.isNotBlank(criteria.taxId)) {
            query += 'AND Account.Id IN ' +
                     '(SELECT ParentRecordId FROM Identifier ' +
                     ' WHERE PRM_Type__c = \'EIN\' AND IdValue = :taxId) ';
        }
        
        if (String.isNotBlank(criteria.npi)) {
            query += 'AND PRM_IdentifierHealthcareFacility__r.IdValue = :npi ';
        }
        
        if (String.isNotBlank(criteria.zip)) {
            query += 'AND Location.PRM_Zip__c LIKE :zipPattern ';
        }
        
        // Add more filters...
        
        query += 'ORDER BY PRM_Primary__c DESC, Name ASC LIMIT 200';
        
        return query;
    }
    
    private static Integer calculateRelevance(HealthcareFacility facility, SearchCriteria criteria) {
        Integer score = 0;
        
        // Exact matches: +30 points each
        if (String.isNotBlank(criteria.taxId) && 
            matchesTaxId(facility, criteria.taxId)) {
            score += 30;
        }
        
        if (String.isNotBlank(criteria.npi) && 
            facility.PRM_IdentifierHealthcareFacility__r?.IdValue == criteria.npi) {
            score += 30;
        }
        
        // Address field matches: +20 points each
        if (String.isNotBlank(criteria.addressLine1) && 
            facility.Location?.PRM_AddressLine1__c?.containsIgnoreCase(criteria.addressLine1)) {
            score += 20;
        }
        
        if (String.isNotBlank(criteria.city) && 
            facility.Location?.PRM_City__c?.equalsIgnoreCase(criteria.city)) {
            score += 20;
        }
        
        // State match: +15 points
        if (String.isNotBlank(criteria.state) && 
            facility.Location?.PRM_State__c == criteria.state) {
            score += 15;
        }
        
        // Zip match: +15 points
        if (String.isNotBlank(criteria.zip) && 
            facility.Location?.PRM_Zip__c?.startsWith(criteria.zip)) {
            score += 15;
        }
        
        // Primary practice bonus: +10 points
        if (facility.PRM_Primary__c) {
            score += 10;
        }
        
        // Active status bonus: +5 points
        if (facility.PRM_Active__c) {
            score += 5;
        }
        
        return Math.min(score, 100); // Cap at 100
    }
    
    private static List<String> getMatchReasons(HealthcareFacility facility, SearchCriteria criteria) {
        List<String> reasons = new List<String>();
        
        if (String.isNotBlank(criteria.taxId) && matchesTaxId(facility, criteria.taxId)) {
            reasons.add('Tax ID Match');
        }
        
        if (String.isNotBlank(criteria.npi) && 
            facility.PRM_IdentifierHealthcareFacility__r?.IdValue == criteria.npi) {
            reasons.add('NPI Match');
        }
        
        if (String.isNotBlank(criteria.addressLine1) && 
            facility.Location?.PRM_AddressLine1__c?.containsIgnoreCase(criteria.addressLine1)) {
            reasons.add('Address Match');
        }
        
        if (String.isNotBlank(criteria.city) && 
            facility.Location?.PRM_City__c?.equalsIgnoreCase(criteria.city)) {
            reasons.add('City Match');
        }
        
        if (String.isNotBlank(criteria.zip) && 
            facility.Location?.PRM_Zip__c?.startsWith(criteria.zip)) {
            reasons.add('Zip Code Match');
        }
        
        if (facility.PRM_Primary__c) {
            reasons.add('Primary Practice');
        }
        
        return reasons;
    }
    
    private static Boolean matchesTaxId(HealthcareFacility facility, String taxId) {
        // Query Identifier for this Account's TaxID
        List<Identifier> ids = [
            SELECT IdValue 
            FROM Identifier 
            WHERE ParentRecordId = :facility.AccountId 
              AND PRM_Type__c = 'EIN' 
              AND IdValue = :taxId 
            LIMIT 1
        ];
        return !ids.isEmpty();
    }
}
```

**UI Component**:

```javascript
// prmSmartAddressSearch.js (NEW)
import { LightningElement, track } from 'lwc';
import smartSearch from '@salesforce/apex/PRM_SmartAddressSearch.smartSearch';

export default class PrmSmartAddressSearch extends LightningElement {
    @track searchCriteria = {
        taxId: '',
        npi: '',
        practiceLocationNumber: '',
        addressLine1: '',
        city: '',
        state: '',
        zip: '',
        activeOnly: true
    };
    
    @track searchResults = [];
    @track isSearching = false;
    
    handleInputChange(event) {
        const field = event.target.name;
        this.searchCriteria[field] = event.target.value;
    }
    
    async handleSearch() {
        this.isSearching = true;
        
        try {
            const results = await smartSearch({ 
                criteria: this.searchCriteria 
            });
            
            this.searchResults = results.map(result => ({
                ...result,
                relevanceBarWidth: result.relevanceScore + '%',
                relevanceColor: this.getRelevanceColor(result.relevanceScore),
                matchReasonsDisplay: result.matchReasons.join(', ')
            }));
            
        } catch (error) {
            this.showToast('Error', 'Search failed: ' + error.message, 'error');
        } finally {
            this.isSearching = false;
        }
    }
    
    getRelevanceColor(score) {
        if (score >= 80) return 'green';
        if (score >= 60) return 'yellow';
        return 'orange';
    }
    
    handleSelectPrimary(event) {
        const facilityId = event.target.dataset.id;
        const selected = this.searchResults.find(r => r.facility.Id === facilityId);
        
        this.dispatchEvent(new CustomEvent('selectprimary', {
            detail: { facility: selected.facility }
        }));
    }
    
    handleSelectAdditional(event) {
        const facilityId = event.target.dataset.id;
        const selected = this.searchResults.find(r => r.facility.Id === facilityId);
        
        this.dispatchEvent(new CustomEvent('selectadditional', {
            detail: { facility: selected.facility }
        }));
    }
    
    handleClearFilters() {
        this.searchCriteria = {
            taxId: '',
            npi: '',
            practiceLocationNumber: '',
            addressLine1: '',
            city: '',
            state: '',
            zip: '',
            activeOnly: true
        };
        this.searchResults = [];
    }
}
```

---

## Additional Enhancements

### Recently Used Addresses

Show practitioner's recent address selections for quick re-selection:

```
┌─────────────────────────────────────────────────────────────┐
│  🕒 Recently Used Addresses (Last 6 months)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ✓ 123 Main St, New York, NY 10001                     │   │
│  │   Last Used: 03/15/2026 (Application Review Case)     │   │
│  │   [Quick Select]                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  │   456 Oak Ave, Brooklyn, NY 11201                      │   │
│  │   Last Used: 02/20/2026 (Off-Cycle Add Location)      │   │
│  │   [Quick Select]                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Address Validation & Standardization

Integrate with USPS or SmartyStreets API to validate and standardize addresses:

```javascript
async validateAddress(addressData) {
    const validationResult = await callUSPSValidation({ address: addressData });
    
    if (!validationResult.isValid) {
        // Show suggestions
        this.showAddressSuggestions(validationResult.suggestions);
    } else if (validationResult.hasStandardization) {
        // Show "Did you mean?" dialog
        this.showStandardizationSuggestion(validationResult.standardized);
    }
}
```

### Bulk Address Operations

Allow selecting multiple addresses at once:

```
┌─────────────────────────────────────────────────────────────┐
│  Bulk Actions for Selected Addresses (3 selected)            │
│  [Mark as Primary] [Remove All] [Export to CSV]              │
└─────────────────────────────────────────────────────────────┘
```

---

## Security & Permissions

### Role-Based Access Control

| Role | View Addresses | Edit Existing | Add New | Remove | Post-Submission Edit |
|------|---------------|---------------|---------|--------|---------------------|
| **Credentialing User** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Credentialing Manager** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **QC Reviewer** | ✅ | ⚠️ Limited | ❌ | ❌ | ⚠️ Requires approval |
| **Provider (Self-Service)** | ✅ Own Only | ⚠️ Before Submission | ✅ | ⚠️ Before Submission | ❌ |
| **Read-Only User** | ✅ | ❌ | ❌ | ❌ | ❌ |

### Audit Trail Requirements

Every address change must be logged with:
- Who made the change (User ID, Name)
- When (Timestamp)
- What changed (Old Value → New Value)
- Why (Optional reason field)
- Source (OmniScript, LWC, API, Manual)

```apex
// Example audit log entry
{
    "ObjectType": "Location",
    "RecordId": "131D1000000VgbnIAC",
    "Action": "Update",
    "Changes": [
        {
            "Field": "PRM_Phone__c",
            "OldValue": "(212) 555-0100",
            "NewValue": "(212) 555-0199"
        }
    ],
    "ModifiedBy": "005xx000001X8Uz",
    "ModifiedByName": "John Smith",
    "ModifiedDate": "2026-04-10T14:32:15Z",
    "Source": "PractitionerParticipationForm",
    "Reason": "Provider updated contact number"
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- ✅ Create `PRM_AddressManagementService` Apex class
- ✅ Implement soft-delete functionality (`markAddressAsError`)
- ✅ Add restore functionality for error-marked addresses
- ✅ Implement audit logging (`PRM_AuditLogger`)
- ✅ Update data model (add fields if needed)

### Phase 2: UI Components (Weeks 3-5)
- ✅ Build `prmAddressDetailsComponent` (editable address fields)
- ✅ Enhance `prmTextElementOverrideForGroupSelection` with remove buttons
- ✅ Add confirmation modals for remove operations
- ✅ Implement field validation and error handling
- ✅ Add "Edit" button to submitted form review screen

### Phase 3: Smart Search (Weeks 6-8)
- ✅ Create `PRM_SmartAddressSearch` Apex class
- ✅ Build relevance scoring algorithm
- ✅ Create `prmSmartAddressSearch` LWC component
- ✅ Integrate with existing group selection modal
- ✅ Add "Recently Used Addresses" feature

### Phase 4: Testing & Validation (Weeks 9-10)
- ✅ Unit tests for Apex classes (95%+ coverage)
- ✅ Integration tests for address edit flow
- ✅ UAT with credentialing team
- ✅ Performance testing (large result sets >1000 addresses)
- ✅ Security review (permissions, audit trail)

### Phase 5: Deployment & Training (Week 11-12)
- ✅ Deploy to UAT environment
- ✅ Conduct training sessions for credentialing staff
- ✅ Create user documentation
- ✅ Production deployment
- ✅ Post-go-live support

---

## Success Metrics

### User Experience Metrics
- **Reduce Time to Edit Addresses**: Target 75% reduction (from ~30 min to ~7 min)
- **Reduce Address Entry Errors**: Target 50% reduction
- **User Satisfaction Score**: Target 4.5/5.0 or higher

### Operational Metrics
- **Reduce Manual Cleanup Requests**: Target 80% reduction
- **Reduce Case Reopen Rate**: Target 60% reduction
- **Improve Data Quality**: Target 90%+ address validation pass rate

### Technical Metrics
- **Search Performance**: <2 seconds for up to 1000 results
- **Page Load Time**: <3 seconds for address details screen
- **Error Rate**: <1% failed saves
- **Audit Coverage**: 100% of address changes logged

---

## Risk & Mitigation

### Risk 1: Performance Degradation with Large Result Sets
**Mitigation**: 
- Implement pagination (show 50 results per page)
- Use indexed fields (TaxID, NPI, Zip) in queries
- Add caching for frequently searched addresses

### Risk 2: Data Integrity Issues with Soft Delete
**Mitigation**:
- Implement validation rules to prevent orphaned records
- Create scheduled job to clean up old error records (>2 years)
- Add restore functionality for accidental removals

### Risk 3: User Confusion with Multiple Edit Modes
**Mitigation**:
- Clear visual indicators (edit mode vs. view mode)
- Tooltips and help text for each field
- Training sessions and documentation

### Risk 4: Audit Trail Storage Growth
**Mitigation**:
- Archive audit logs >1 year to Big Objects
- Implement data retention policy
- Monitor storage usage

---

## Appendix A: Field Mapping

| Salesforce Field | Display Label | Editable | Required | Validation |
|------------------|---------------|----------|----------|------------|
| `PRM_AddressLine1__c` | Address Line 1 | ✅ | ✅ | Max 255 chars |
| `PRM_AddressLine2__c` | Address Line 2 | ✅ | ❌ | Max 255 chars |
| `PRM_City__c` | City | ✅ | ✅ | Max 100 chars |
| `PRM_State__c` | State | ✅ | ✅ | Picklist |
| `PRM_Zip__c` | Zip Code | ✅ | ✅ | 5 digits |
| `PRM_Zip4__c` | Zip+4 | ✅ | ❌ | 4 digits |
| `PRM_County__c` | County | ✅ | ❌ | Max 100 chars |
| `PRM_Phone__c` | Phone | ✅ | ✅ | Format validation |
| `PRM_PhoneExtension__c` | Phone Extension | ✅ | ❌ | Max 10 digits |
| `PRM_Fax__c` | Fax | ✅ | ❌ | Format validation |
| `PRM_AddressType__c` | Address Type | ⚠️ | ✅ | Picklist (restricted) |
| `PRM_IsErrorRecord__c` | Is Error Record | ❌ | - | System field |
| `PRM_Pending__c` | Pending | ❌ | - | System field |

---

## Appendix B: API Specifications

### Apex Methods

```apex
// Soft delete address
PRM_AddressManagementService.markAddressAsError(
    String facilityId, 
    String reason, 
    String removedBy
)

// Restore deleted address
PRM_AddressManagementService.restoreAddress(
    String facilityId, 
    String restoredBy
)

// Update address details
PRM_AddressManagementService.updateAddress(
    String locationId,
    Map<String, Object> addressData,
    String updatedBy
)

// Smart search
PRM_SmartAddressSearch.smartSearch(
    SearchCriteria criteria
) returns List<SearchResult>

// Get recently used addresses
PRM_AddressManagementService.getRecentAddresses(
    String practitionerId,
    Integer limitCount
) returns List<HealthcareFacility>
```

---

## Appendix C: UI Wireframes

See separate document: `Address_Selection_UI_Wireframes.pdf`

---

## Appendix D: Test Scenarios

### Scenario 1: Edit Existing Address After Submission
```
Given: Practitioner participation form has been submitted
When: User clicks "Edit Address/Group Selection"
Then: Group selection modal opens with current selections displayed
And: User can modify address fields
And: User can save changes
And: Audit trail is created
And: Case timeline is updated
```

### Scenario 2: Remove Additional Address
```
Given: User has selected 3 additional practice locations
When: User clicks "Remove" on Additional Address #2
Then: Confirmation dialog appears
When: User confirms removal
Then: Address is marked as error record (PRM_IsErrorRecord__c = true)
And: Address no longer appears in selected addresses list
And: Audit log entry is created
And: User can still select a different address
```

### Scenario 3: Smart Search by TaxID and City
```
Given: User is on group selection modal
When: User enters TaxID "12-3456789" and City "New York"
And: User clicks Search
Then: Results are displayed sorted by relevance score
And: Exact matches appear first
And: Each result shows relevance percentage
And: Each result shows match reasons (e.g., "Tax ID Match, City Match")
```

### Scenario 4: Edit Pre-Populated Address
```
Given: User reopens participation form with existing addresses
When: User navigates to address details screen
Then: All address fields are editable (not read-only)
When: User modifies Phone number from "(212) 555-0100" to "(212) 555-0199"
And: User clicks Save
Then: Location record is updated
And: Audit trail captures: Field="PRM_Phone__c", OldValue="(212) 555-0100", NewValue="(212) 555-0199"
And: Success message displayed
```

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Business Owner | [TBD] | | |
| Technical Lead | [TBD] | | |
| QA Lead | [TBD] | | |
| Security Reviewer | [TBD] | | |

---

**End of Document**
