# Implementation Plan: PRM_DelegatedOnly__c → PRM_Delegated__c

## Summary of Changes

| Aspect | Old | New |
|--------|-----|-----|
| **Field Name** | `PRM_DelegatedOnly__c` | `PRM_Delegated__c` |
| **Logic** | True only when **all** practice locations are delegated | True when **any** practice location is delegated |

---

## 1. Salesforce Metadata (Field Rename/Create)

**Option A – Rename (recommended if no external dependencies)**
- Create new custom field `PRM_Delegated__c` on Account (same type as `PRM_DelegatedOnly__c`)
- Migrate data: `PRM_Delegated__c = PRM_DelegatedOnly__c` (values stay same; logic changes below)
- Deprecate/delete `PRM_DelegatedOnly__c` after migration

**Option B – In-place rename**
- Rename `PRM_DelegatedOnly__c` to `PRM_Delegated__c` in metadata (if supported)
- Update all references

---

## 2. Logic Changes

### 2.1 PRM_CommonServiceHelper.cls

**Current logic (lines 71-79):**
- `accToDelInfoCodeMap.put(accountId, true)` only when **all** facilities have delegation

**New logic:**
- `accToDelInfoCodeMap.put(accountId, true)` when **any** facility has delegation

```apex
// OLD (lines 71-79):
for(Id accountId : accToPracLoc.keySet()){
    Set<Id> facilityIds = accToPracLoc.get(accountId);
    if(pracLocToDelInfoCodeMap.keySet().containsAll(facilityIds)){
        accToDelInfoCodeMap.put(accountId, true);
    }
    else{
        accToDelInfoCodeMap.put(accountId, false);
    }
}

// NEW:
for(Id accountId : accToPracLoc.keySet()){
    Set<Id> facilityIds = accToPracLoc.get(accountId);
    Boolean hasAnyDelegated = false;
    for(Id facId : facilityIds){
        if(pracLocToDelInfoCodeMap.containsKey(facId)){
            hasAnyDelegated = true;
            break;
        }
    }
    accToDelInfoCodeMap.put(accountId, hasAnyDelegated);
}
```

Also update all `PRM_DelegatedOnly__c` references to `PRM_Delegated__c` (lines 25, 32, 121).

---

### 2.2 PRM_RCATTerminationBatchHelper.cls

**`delegatedOnlyPractitioner()` method (lines 753-787):**

**Current logic:**
- Practitioner is delegated only if **all** facilities are delegated (starts true, sets false when any facility is NOT delegated)

**New logic:**
- Practitioner is delegated if **any** facility is delegated (starts false, sets true when any facility IS delegated)

```apex
// OLD: Start true, set false when any facility is NOT delegated
for (Id pid : practitionerIds) {
    practitionerDelegatedMap.put(pid, true);
}
// ...
if (hpf.HealthcareFacility.PRM_IsDelegated__c == false) {
    practitionerDelegatedMap.put(hpf.PractitionerId, false);
}

// NEW: Start false, set true when any facility IS delegated
for (Id pid : practitionerIds) {
    practitionerDelegatedMap.put(pid, false);
}
// ...
if (hpf.HealthcareFacility.PRM_IsDelegated__c == true) {
    practitionerDelegatedMap.put(hpf.PractitionerId, true);
}
```

Also update `PRM_DelegatedOnly__c` to `PRM_Delegated__c` (lines 833, 847).

---

## 3. CAQH Batch – Business Rule Update

**PRM_CheckCAQHAccessOnDueAccountsBatch.cls (line 82):**

- **Current:** Excludes practitioners with `PRM_DelegatedOnly__c = false` (i.e., only includes non-delegated)
- **New rule:** Exclude practitioners if credentialing status is **not** Credentialed

**Change:** Remove `PRM_DelegatedOnly__c = false` from the query. Add `PRM_CredentialingStatus__c = 'Credentialed'` to only include practitioners who are credentialed (and thus need CAQH access checks).

```apex
// OLD:
' FROM Account Where isActive = true AND RecordTypeID=:pracRecTypeId AND PRM_DelegatedOnly__c = false AND PRM_PNC__c =false AND '+filterQuery;

// NEW:
' FROM Account Where isActive = true AND RecordTypeID=:pracRecTypeId AND PRM_CredentialingStatus__c = \'Credentialed\' AND PRM_PNC__c = false AND '+filterQuery;
```

---

## 4. Field Reference Updates (PRM_DelegatedOnly__c → PRM_Delegated__c)

### Apex Classes

| File | Changes |
|------|---------|
| **PRM_CommonServiceHelper.cls** | Logic change + field rename (lines 25, 32, 121) |
| **PRM_InfoCodeAssTriggerHelper.cls** | Field rename (line 29) |
| **PRM_CheckCAQHAccessOnDueAccountsBatch.cls** | Remove PRM_DelegatedOnly__c; add PRM_CredentialingStatus__c = 'Credentialed' filter (line 82) |
| **PRM_OffCycleWrapper.cls** | Field rename (line 389) |
| **PRM_FetchPractTermDataHandler.cls** | Field rename (lines 111, 172) |
| **PRM_PractitionerActivationBatchHelper.cls** | Field rename (lines 18, 34) |
| **PRM_FutureDatedProcessingBatchHandler.cls** | Field rename (lines 908, 914, 923, 961, 962) |
| **PRM_RCATTerminationBatchHelper.cls** | Logic change + field rename (lines 753-787, 833, 847) |

### Test Classes

| File | Changes |
|------|---------|
| **PRM_CheckCAQHAccessOnDueAccountsTest.cls** | Replace PRM_DelegatedOnly__c with PRM_CredentialingStatus__c in setup and testExecuteMethod (lines 26, 157) |
| **PRM_FetchPracTermDataUtilityTest.cls** | Field rename (lines 170, 444, 452) |
| **PRM_CrossReferencePracticeLocationTest.cls** | Field rename (line 26) |

---

## 5. Omnistudio (DataRaptors)

Update `InputFieldName` / `OutputFieldName` from `PRM_DelegatedOnly__c` to `PRM_Delegated__c` in:

| DataRaptor | File | Field Reference |
|------------|------|-----------------|
| PRMDRGetPractitionerFromNPI | PRMDRGetPractitionerFromNPI_Items.json | InputFieldName |
| PRMDRCreateCaseCaseManagerAndAccount | PRMDRCreateCaseCaseManagerAndAccount_Items.json | OutputFieldName |
| PRMExtractInactivePractitionerForVerification | PRMExtractInactivePractitionerForVerification_Items.json | InputFieldName |
| PRMExtractPractitionerForVerification | PRMExtractPractitionerForVerification_Items.json | InputFieldName |
| PRMDRExtractExistingAccount | PRMDRExtractExistingAccount_Items.json | InputFieldName |
| PRMFetchAccountAndPracticeLocations | PRMFetchAccountAndPracticeLocations_Items.json | InputFieldName |
| PRMDrExtractPractForProfStaff | PRMDrExtractPractForProfStaff_Items.json | InputFieldName |
| PRMDRExtractHealthCareProviderNPIWithBothValues | PRMDRExtractHealthCareProviderNPIWithBothValues_Items.json | InputFieldName |
| PRMDRExtractHealthCareProviderNPIWithLastName | PRMDRExtractHealthCareProviderNPIWithLastName_Items.json | InputFieldName |
| PRMDRExtractHealthCareProviderNPIWithFirstName | PRMDRExtractHealthCareProviderNPIWithFirstName_Items.json | InputFieldName |
| PRMDRExtractNPIfromContextId | PRMDRExtractNPIfromContextId_Items.json | InputFieldName |
| PRMDRExtractExistingNPIInfo | PRMDRExtractExistingNPIInfo_Items.json | InputFieldName |
| PRMDRExtractHealthCareProviderNpiRecords | PRMDRExtractHealthCareProviderNpiRecords_Items.json | InputFieldName |

**Note:** `IsPractitionerDelegated` output field names can remain as-is (they represent the practitioner's delegated status).

---

## 6. Other Considerations

### PRM_GetInfoCodeAndOtherRecordsForRCATReview
- `DelegatedOnlyList` is a formula based on practice location `IsDelegated`, not the Account field
- No change needed unless renaming for consistency

### PRM_PractitionerActivationBatchHelper
- `isPLDelegated` is passed from the IP based on the location being activated
- If that location is delegated, we'd set true (matches new "any" logic)
- No logic change needed; only field rename

### Page Layouts, Reports, List Views
- Update any layouts, reports, list views, or list view filters referencing `PRM_DelegatedOnly__c`

### Flows and Process Builder
- Search for `PRM_DelegatedOnly__c` and update to `PRM_Delegated__c`

---

## 7. DataRaptor → IP → OmniScript Trace (IsPractitionerDelegated / PRM_DelegatedOnly__c)

### DataRaptors Using PRM_DelegatedOnly__c

| DataRaptor | Used By (IP) | Output/Input |
|------------|--------------|--------------|
| **PRMDRExtractHealthCareProviderNPIWithBothValues** | PRM_GetHealthCareProviderNpiRecords | Input: Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRExtractHealthCareProviderNPIWithLastName** | PRM_GetHealthCareProviderNpiRecords | Input: Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRExtractHealthCareProviderNPIWithFirstName** | PRM_GetHealthCareProviderNpiRecords | Input: Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRExtractHealthCareProviderNpiRecords** | PRM_GetHealthCareProviderNpiRecords | Input: Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRExtractNPIfromContextId** | PRM_GetHealthCareProviderNpiRecords | Input: Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRGetPractitionerFromNPI** | (various) | Input: HealthcareProviderNPI:Account.PRM_DelegatedOnly__c → Output: IsPractitionerDelegated |
| **PRMDRCreateCaseCaseManagerAndAccount** | PRM_DelegatedPractitionerCreation, PRM_PractitionerCreation, PRM_PractitionerScreenRecordCreation | Output: PRM_DelegatedOnly__c (writes to Account on create) |
| **PRMExtractPractitionerForVerification** | PRM_VerifyPractitionerDetailsForDelegated, PRM_VerifyAccountCreationPractitioners, PRM_FetchPractitionerForVerification | Input: NPI:Account.PRM_DelegatedOnly__c → Output: Practitioner:IsPractitionerDelegated |
| **PRMExtractInactivePractitionerForVerification** | PRM_VerifyPractitionerDetailsForDelegated | Input: NPI:Account.PRM_DelegatedOnly__c → Output: Practitioner:IsPractitionerDelegated |
| **PRMFetchAccountAndPracticeLocations** | PRM_FetchPDMManualUpdateDetails | Input: Practitioner:PRM_DelegatedOnly__c |
| **PRMDrExtractPractForProfStaff** | PRM_FetchPDMManualUpdateDetails | Input: Practr:PRM_DelegatedOnly__c |
| **PRMDRExtractExistingAccount** | (OmniDataTransform – used in formulas/transforms) | Input: PRM_DelegatedOnly__c |
| **PRMDRExtractExistingNPIInfo** | (various) | Input: Account:PRM_DelegatedOnly__c |

### IP → OmniScript Trace and Purpose

| OmniScript | IP(s) Called | Purpose of IsPractitionerDelegated |
|------------|--------------|-------------------------------------|
| **PRM_OffCycleCredentialing_English** | PRM_FetchOffCycleCredUtility (Apex Remote Action) → uses Account.PRM_DelegatedOnly__c from NPI query | **Blocks delegated practitioners from Off-Cycle flow:** SetErrorForDelegatedPractitioner shows step-level error when IsPractitionerDelegated=true. TextBlock13/16 show message: "Practitioner must be fully credentialed, please submit a Practitioner Participation Request" when delegated AND credentialing status ≠ Denied. Purpose: Prevent delegated-only practitioners from using Off-Cycle Credentialing; they must use Practitioner Participation Form instead. |
| **PRM_PractitionerTerminationForm_English** | PRM_GetPractitionerTerminationData → GetHealthProviderNpiWithAccountId (PRMDRExtractHealthCareProviderNpiRecords) | **Displays practitioner delegated status** in termination flow. Used for validation in PRM_VerifyPractitionerDetails (DelegatedValid formula). |
| **PRM_PractitionerTerminationRecredForm_English** | PRM_GetHealthCareProviderNpiRecords | **Fetches practitioner data** including IsPractitionerDelegated for recredentialing termination. |
| **PRM_PDMManualUpdate_English** | PRM_VerifyPractitionerDetailsParent → PRM_VerifyPractitionerDetails | **DelegatedValid formula:** Validates practitioner list. Fails if non-credentialed, non-PNC practitioners exist when group is delegated (IsPractitionerDelegated used in filter). Ensures only valid practitioners can be added/removed in PDM/COI flows. |
| **PRM_ProviderChangeForm_English** | PRM_VerifyPractitionerDetailsParent → PRM_VerifyPractitionerDetails | **Same as PDM:** DelegatedValid validation for practitioner verification when adding/removing practitioners in Provider Change flow. |

### Apex (Non-IP) Usage

| Class | Purpose |
|-------|---------|
| **PRM_FetchOffCycleCredHelper** | getNPIDetails() queries Account.PRM_DelegatedOnly__c; passed to PRM_OffCycleWrapper for IsPractitionerDelegated in Off-Cycle search response. |
| **PRM_OffCycleWrapper** | Maps npiRecord.account.PRM_DelegatedOnly__c → ipresp.IsPractitionerDelegated for Off-Cycle provider search. |
| **PRM_FetchPractTermDataHandler** | Maps npiData.account.prm_delegatedonly__c → IsPractitionerDelegated in practitioner termination data response. |

### FlexCard

| FlexCard | Purpose |
|----------|---------|
| **PRMPractitionerDemographics** | Displays IsPractitionerDelegated in practitioner demographics sample/data. |

---

## 8. Implementation Order

1. Create `PRM_Delegated__c` field on Account (or rename existing)
2. Update **PRM_CommonServiceHelper** (logic + field references)
3. Update **PRM_RCATTerminationBatchHelper** (logic + field references)
4. Update all other Apex classes and tests
5. Update DataRaptors
6. CAQH batch: use PRM_CredentialingStatus__c = 'Credentialed' (done)
7. Deploy and run tests
8. Migrate data if using new field, then remove `PRM_DelegatedOnly__c` when safe
