# PDM Address Validation Error - Root Cause Analysis

## Error
```
"An Address is already Active for this Location with the same Type. Please verify there are no overlapping dates and deactivate before proceeding."
```

## Scenario
PDM user selects **"Add/Update/Terminate Current Office Information"** under the PDM Manual Updates - Practice Location request type and only wants to update the **email address** (or **website address**). The error fires even though no physical address change was intended.

---

## Root Cause

### The Trigger (`PRM_AddressTriggerHandler.cls`, Line 180)

The `checkForOverlappingDatesOfAddresses()` method runs on `beforeInsert` and `beforeUpdate` of the `Address` object. It:
1. Checks if `PRM_AddressType__c != null` and `PRM_Pending__c == false`
2. Queries all active addresses for the same Location (`ParentId`) with the same address type
3. If an active address already exists with overlapping dates **and** it's a different record ID, it throws the error

### Why Email/Website Update Triggers an Address DML

The OmniScript `PRM_PDMManualUpdatePracticeLocation_English` (v9) groups **website address** and **email address** on the same form step as the **physical practice address fields** (Address Line 1, City, State, Zip, Phone, Fax) under the "Add/Update/Terminate Current Office Information" action.

The downstream processing flows through:
1. **OmniScript** `PRM_PDMManualUpdatePracticeLocation_English` collects all COI fields together
2. **IP** `PRM_PDMRecordsCreationPracLocation` (v3) calls → `PRM_PDMCOIHelper` (v11)
3. **IP** `PRM_PDMCOIHelper` calls → **DataRaptor** `DRLoadFacLocAddPCFUpdateCOI` (via `PRMLoadFacLocAddPCFUpdateCOI`)

The DataRaptor `PRMLoadFacLocAddPCFUpdateCOI` writes to **BOTH**:
- **`HealthcareFacility`** object — for `PRM_WebsiteAddress__c` and `PRM_OfficeEmail__c`
- **`Address`** object — for physical address fields (`PRM_AddressLine1__c`, `PRM_City__c`, etc.) AND `PRM_AddressType__c`, `PRM_Active__c`

**Critical issue**: The DataRaptor **always** upserts an Address record as part of the COI update, even when only website/email changed. When it upserts the Address record with:
- `PRM_Active__c = true`  
- `PRM_Pending__c = false` (set in the IP, line 362)
- `PRM_AddressType__c` set to the existing type (e.g., "Primary;Practice")

...the trigger detects "a new active address of the same type on the same location with overlapping dates" and throws the error.

### The `PRM_Pending__c = false` Problem

In the IP `PRM_PDMCOIHelper` (line 362), the `DRLoadAddressWithId` step explicitly sets:
```
"Address:Pending" : false
```

This means the trigger's bypass condition (`PRM_Pending__c == true` would skip validation) is NOT met, so the validation always fires.

### Data Model Mismatch

- **Website Address** → stored on `HealthcareFacility.PRM_WebsiteAddress__c` (NOT on Address)
- **Office Email** → stored on `HealthcareFacility.PRM_OfficeEmail__c` (NOT on Address)
- **Physical Address** → stored on the `Address` object

Yet the Integration Procedure bundles all these updates into a single flow that always touches the `Address` record.

---

## The "ErrorForCOIUpdate" Formula (Line 14201 of OmniScript v9)

The OmniScript uses this formula to determine if there were changes:
```
%locAddrLine1COI% != %OfficeAddress:AddLine1% || 
%locAddrLine2COI% != %OfficeAddress:AddLine2% || 
%locCityCOI% != %OfficeAddress:City% || 
%locStateCOI% != %OfficeAddress:State% || 
%OfficeAddress:Zip% != %locZipCOI% || 
%OfficeAddress:Zip4% != %locZip4COI% || 
%locPhoneCOI% != %OfficeAddress:Phone% || 
%locFaxCOI% != %OfficeAddress:Fax% || 
%OfficeAddress:WebsiteAddress% != %locWebAddrCOI% || 
%OfficeAddress:OfficeEmail% != %locOfficeEmailCOI% || 
%blkPatientAgeRange:locAgeFromCOI% != %OfficeAddress:MinAge% || 
%blkPatientAgeRange:locAgeToCOI% != %OfficeAddress:MaxAge% || 
%OfficeAddress:BillingType% != %locBillingTypeCOI%
```

This formula treats ALL changes (including website/email) as a single COI update — there's no separation between address changes vs. non-address changes.

---

## Business Request: Move Website/Email to "Update Office Hours" Request Type

### Current State
| Field | Request Type | Required? |
|-------|-------------|-----------|
| Website Address | Add/Update/Terminate Current Office Information | Yes (part of address form) |
| Office Email | Add/Update/Terminate Current Office Information | Yes (part of address form) |

### Requested State
| Field | Request Type | Required? |
|-------|-------------|-----------|
| Website Address | Update Office Hours | No (optional) |
| Office Email | Update Office Hours | No (optional) |

---

## Recommended Fix Approach

### Option A: Quick Fix - Separate Email/Website from Address DML (Preferred)

1. **In the IP `PRM_PDMCOIHelper`**: Add a conditional check before calling `DRLoadAddressWithId` — only call it when there's an actual physical address change (not just website/email). The condition `ISNOTBLANK(%SelectedAddressIdFinal%)` already partially does this, but the COI update path still fires.

2. **In the DataRaptor `PRMLoadFacLocAddPCFUpdateCOI`**: Ensure the Address upsert only fires when address fields actually changed. Currently it always writes to Address.

### Option B: Move to "Update Office Hours" Request Type (Business Request)

1. **OmniScript Changes** (`PRM_PDMManualUpdatePracticeLocation_English`):
   - Remove Website Address and Office Email fields from the "Add/Update/Terminate Current Office Information" step
   - Add Website Address and Office Email fields to the "Update Office Hours" step
   - Make both fields **NOT required** (currently they're part of a required address block)
   - Update the "ErrorForCOIUpdate" formula to remove `%OfficeAddress:WebsiteAddress%` and `%OfficeAddress:OfficeEmail%` comparisons

2. **Integration Procedure Changes** (`PRM_PDMPLRecordsCreationHelper`):
   - The "Update Office Hours" IP flow (`CB_UpdateOfficeHours`) needs to be enhanced to also update `HealthcareFacility.PRM_WebsiteAddress__c` and `HealthcareFacility.PRM_OfficeEmail__c`
   - This should ONLY update the HealthcareFacility object (no Address DML needed)

3. **DataRaptor Changes**:
   - Create or modify the office hours DataRaptor to include `PRM_WebsiteAddress__c` and `PRM_OfficeEmail__c` fields on the HealthcareFacility output
   - No Address object mapping needed since website/email are HealthcareFacility fields

### Option C: Fix the Trigger Bypass (Not Recommended)

Setting `PRM_Pending__c = true` on the Address upsert would bypass the validation, but this would incorrectly mark the address as pending, which has downstream implications.

---

## Files to Modify

| Component | File/Location | Change |
|-----------|---------------|--------|
| OmniScript | `PRM_PDMManualUpdatePracticeLocation_English` (v9+) | Remove website/email from COI step, add to Office Hours step |
| IP | `PRM_PDMPLRecordsCreationHelper` (v4+) | Add HCF update for website/email in office hours flow |
| IP | `PRM_PDMCOIHelper` (v11+) | Add condition to skip Address DML when only website/email changed |
| DataRaptor | `PRMLoadFacLocAddPCFUpdateCOI` | Conditionally skip Address upsert |
| DataRaptor | New/Modified office hours DR | Add PRM_WebsiteAddress__c and PRM_OfficeEmail__c to HealthcareFacility |
| Formula | `ErrorForCOIUpdate` in OmniScript | Remove website/email comparisons |

---

## Key Source References

| File | Purpose |
|------|---------|
| `force-app/main/default/classes/PRM_AddressTriggerHandler.cls` (Line 180) | Error message and validation logic |
| `vlocity_export/DataRaptor/PRMLoadFacLocAddPCFUpdateCOI/PRMLoadFacLocAddPCFUpdateCOI_Items.json` | DataRaptor that writes to BOTH Address and HealthcareFacility |
| `force-app/main/default/omniIntegrationProcedures/PRM_PDMCOIHelper_Procedure_11.oip-meta.xml` (Line 362) | Sets `Address:Pending = false` |
| `force-app/main/default/omniScripts/PRM_PDMManualUpdatePracticeLocation_English_9.os-meta.xml` | OmniScript with bundled fields |
