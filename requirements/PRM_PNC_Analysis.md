# PRM_PNC__c – Detailed Analysis

## What is PNC?

**PNC** stands for **"Par Non Cred"** (Participating Non-Credentialed). It is a boolean flag on Account that indicates whether a **practice location (vendor)** or **practitioner** participates in the network without full credentialing—typically through a group/vendor affiliation rather than individual credentialing.

- **On Vendor/Group Account:** `PRM_PNC__c = true` means the practice location is a PNC group (participates without full credentialing).
- **On Practitioner Account:** `PRM_PNC__c = true` means the practitioner is affiliated **only** with PNC practice locations (all their practice affiliations are PNC).

> **📌 This document describes the CURRENT (as-built) state.** The target state moves PNC from the vendor Account to `HealthcareFacility.PRM_PNC__c` (practice location) and makes the practitioner rollup **configurable per practitioner** via a new checkbox `Account.PRM_PNCAnyLocation__c`:
> - **Default (flag false):** practitioner PNC = true only when **all** participating practice locations are PNC (same rule as today, new source).
> - **Flag true:** practitioner PNC = true when **any** participating practice location is PNC.
>
> This is **not** an unconditional "all → any" change (unlike PRM_DelegatedOnly → PRM_Delegated). See `PRM_PNC_Logic_Change_Implementation_Plan.md` for the full target-state stories.

---

## 1. Data Model & Rollup Logic

### 1.1 Practitioner PNC Rollup (Vendor → Practitioner)

**PRM_AccountTriggerHelper.updateAccountPNC** (Story #1089847)

When a **Vendor** account’s `PRM_PNC__c` changes:
1. Find all `HealthcarePractitionerFacility` records linking practitioners to that vendor.
2. For each practitioner, determine new PNC: **true** only if **all** their practice affiliations have `PRM_PNC__c = true`; **false** if **any** affiliation has `PRM_PNC__c = false`.
3. Update the practitioner’s Account `PRM_PNC__c` accordingly.

**PRM_CommonUtils.updateAccountPNCHelper** – Core logic:
- If any HCPF Account has `PRM_PNC__c = false` → Practitioner Account `PRM_PNC__c = false`
- If all HCPF Accounts have `PRM_PNC__c = true` → Practitioner Account `PRM_PNC__c = true`

### 1.2 PNC-Only Practitioner (Batch Logic)

**PRM_RCATTerminationBatchHelper.pncOnlyPractitioner()**

Determines if a practitioner is “PNC only” (all practice affiliations are PNC):
- Starts with `true` for each practitioner.
- If **any** `HealthcarePractitionerFacility` (RecordType = `PRM_PractitionerPracticeAffiliation`) has `Account.PRM_PNC__c = false` → sets that practitioner to `false`.
- Practitioners with no affiliations → `false`.

**PRM_FutureDatedProcessingBatchHandler** – Similar logic:
- Queries `HealthcarePractitionerFacility` where `RecordType = PRM_PractitionerPracticeAffiliation` and `Account.PRM_PNC__c = true`.
- Practitioner is PNC if they have **any** such affiliation.
- Used with `pncOnlyPractitioner()` to update practitioner Account `PRM_PNC__c` during future-dated processing.

---

## 2. DataRaptor → IP → OmniScript Trace

### 2.1 DataRaptors Using PRM_PNC__c

| DataRaptor | Input/Output | Purpose |
|------------|--------------|---------|
| **PRMDRExtractHealthCareProviderNPIWithBothValues** | Input: Account.PRM_PNC__c, HealthCareProvider:Practitioner:Account:PRM_PNC__c | Maps PNC to practitioner search results |
| **PRMDRExtractHealthCareProviderNPIWithLastName** | Input: Account.PRM_PNC__c | Same |
| **PRMDRExtractHealthCareProviderNPIWithFirstName** | Input: Account.PRM_PNC__c | Same |
| **PRMDRExtractHealthCareProviderNpiRecords** | Input: Account.PRM_PNC__c | Same |
| **PRMDRExtractNPIfromContextId** | Input: Account.PRM_PNC__c | Same |
| **PRMDRGetPractitionerFromNPI** | Input: HealthcareProviderNPI:Account.PRM_PNC__c | Practitioner lookup by NPI; outputs PNC |
| **PRMDRCreateCaseCaseManagerAndAccount** | Output: PRM_PNC__c | Writes PNC when creating Account |
| **PRMDRCreateCaseCaseManagerExistingNPI** | Output: PRM_PNC__c | Same for existing NPI |
| **PRMExtractPractitionerForVerification** | Input: NPI:Account.PRM_PNC__c | Practitioner verification; outputs PNC |
| **PRMExtractInactivePractitionerForVerification** | Input: NPI:Account.PRM_PNC__c | Same for inactive practitioners |
| **PRMFetchAccountAndPracticeLocations** | Input: Practitioner:PRM_PNC__c | PDM manual update – practitioner PNC |
| **PRMDrExtractPractForProfStaff** | Input: Practr:PRM_PNC__c | Same |
| **PRMDRExtractExistingNPIInfo** | Input: Account:PRM_PNC__c | Existing NPI info extraction |
| **PRMDRExtractAccountDetails** | Input: PRM_PNC__c | Account details extraction |
| **PRMDRExtractPDMAccountDetails** | Input/Output: AccountDetails:PRM_PNC__c | PDM account details |
| **PRMDRExtractHCPFDetails** | Input: Account.PRM_PNC__c | HCPF details for recred termination letter |
| **PRMDRExtractFetchCaseManagerDetails** | Input: Account:PRM_PNC__c | Case manager details |
| **PRMDRSearchBasedOnAccount** | Input: Account:PRM_PNC__c | Provider search by account |
| **PRMDRPRoviderSearchNPITaxID** | Input: Account:PRM_PNC__c | Provider search by NPI/Tax ID |
| **PRMDRSearchBasedOnNPITINAccount** | Input: Account:PRM_PNC__c | Provider search by NPI/TIN/Account |
| **PRMProviderSearchNPITaxID** | Input: Account:PRM_PNC__c | Provider search |
| **PRMExtractPracticeLocationsProvChange** | Input: Facility:Account.PRM_PNC__c | Provider change – practice location PNC |
| **PRMExtractPracticeLocationsAncillaryChange** | Input: Facility:Account.PRM_PNC__c | Ancillary change |
| **PRMExtractPracticeLocationsPARChange** | Input: Facility:Account.PRM_PNC__c | PAR change |
| **PRMFetchVendorAccWithTaxIdAndBillingZip** | Formula: Vendor:PRM_PNC__c | Vendor fetch |
| **PRMFetchVendorAccWithTaxId** | Formula: Vendor:PRM_PNC__c | Vendor fetch |
| **PRMFetchVendorAndHCFWithTaxID** | Formula + Input: Vendor:PRM_PNC__c | Vendor + HCF fetch |
| **PRMFetchVendorAndHCFWithNPI** | Input: Facility:Account.PRM_PNC__c, Vendor:PRM_PNC__c | Vendor + HCF by NPI |
| **PRMDRExtractVendorPracticeLocations** | Input: Facility:Account.PRM_PNC__c, Vendor:PRM_PNC__c | Vendor practice locations |
| **PRMExtractLocationsforHCPNPI** | Input: HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c | Locations for HCP NPI |
| **PRMDRGetLocationTerminationData** | Input: HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c | Location termination data |
| **PRMExtractGroupNameByTIN** | Input: Identifier:Account:PRM_PNC__c | Group name by TIN |
| **PRMDRExtractGroupNameBasedOnTINNPIPNC** | Input: Identifier:Account:PRM_PNC__c, PRM_PNC__c | Group name by TIN/NPI/PNC |
| **PRMDRExtractGroupNameBasedOnTINNPI** | Input: Identifier:Account:PRM_PNC__c | Group name by TIN/NPI |
| **PRMGetRelatedRecordForPractitioner** | Input: CaseManagers:Account.PRM_PNC__c | Related records for practitioner |
| **PRMGetRelatedRecordForRCATReview** | Input: CaseManagers:PractionerPracticeLocation:Account.PRM_PNC__c | RCAT review related records |
| **PRMGetRelatedDataforPNCAndDelegatedRCATReview** | Formula + Input/Output: Account.PRM_PNC__c | Filters HCPF for RCAT review: excludes PNC locations from certain checks |
| **PRMGetPLVendorPNCRCAT** | Formula: HCF:Account.PRM_PNC__c | Determines IsVendorPNC for RCAT |
| **PRMDRGetFacilityInfoDelegatedPNCReCred** | Formula: HCF:Account.PRM_PNC__c | Facility info for delegated/PNC recred |
| **PRMExtractCaseDetails** | Input: Case:Account.PRM_PNC__c | Case details |
| **PRMGetAccountFromCaseAccountId** | Input: PRM_PNC__c | Account from case |
| **PRMDRUpdateAccountReviewPDM** | Output: PRM_PNC__c | Updates Account PNC during PDM review |
| **PRMDRUpdateAccountPDM** | Output: PRM_PNC__c | Same |
| **PRMDRUpdatePNCCase** | Output: PRM_PNC__c | Updates PNC case |
| **PRMDRLoadNPITaxHCFNPNC** | Output: PRM_PNC__c | Load NPI/Tax/HCF/PNC data |

---

## 3. Integration Procedure → OmniScript Trace and Purpose

### 3.1 PRM_VerifyPractitionerDetails / PRM_VerifyPractitionerDetailsForDelegated

**Element: SetDelegatedPNC**

| Formula | Purpose |
|---------|---------|
| **DelegatedValid** | Validates practitioner list. Fails if non-credentialed, non-PNC practitioners exist when group is delegated. Uses `PNC == false` in filter: `'CredentialingStatus != "Credentialed" && PNC == false && IsActivePrac == true && ...'` – ensures only credentialed or PNC practitioners can proceed in delegated groups. |
| **PNCValid** | If `%PNC% = true` (selected facility is PNC), validation passes. Otherwise (COI from PDM): must have at least one PNC practitioner. Uses `'PNC = true'` filter – ensures PNC groups have at least one PNC practitioner. |

**OmniScripts:** PRM_PDMManualUpdate_English, PRM_ProviderChangeForm_English

**Purpose:** Validates practitioners for COI/PDM flows. PNC practitioners are treated differently: they can be in delegated groups without full credentialing; non-PNC, non-credentialed practitioners are blocked.

---

### 3.2 PRM_RecredTerminationLetter

**Element: FilterHCPFRecords**

```json
"EligibleHCPF": "=LIST(FILTER(LIST(%DRExtractHCPFDetails:HCPF%),'Account:PRM_PNC__c != true'))"
```

**Purpose:** Excludes PNC practice locations from recredentialing termination letters. Only practice locations where `PRM_PNC__c != true` are eligible for the letter.

**Called by:** PRM_ReviewRCATLoad, PRM_TerminationLetterModifier (IPs) → used in RCAT review and termination letter flows.

---

### 3.3 PRM_FetchPractitionerDemographics

**Element: ResponseAction**

```json
"PractitionerData:PNC": "=%DRGetAccountFromCaseAccountId:Account|1:PRM_PNC__c%"
```

**Purpose:** Fetches practitioner demographics including PNC status for display.

**Called by:** PRMPractitionerDemographics FlexCard (displays PNC on practitioner demographics).

---

### 3.4 PRM_GetHealthCareProviderNpiRecords

**DataRaptors:** PRMDRExtractHealthCareProviderNPIWithBothValues, WithLastName, WithFirstName, WithOnlyNpi, PRMDRExtractNPIfromContextId, PRMDRExtractHealthCareProviderNpiRecords

**Purpose:** Returns practitioner search results including PNC (from Account) for NPI-based lookups.

**OmniScripts:** PRM_PractitionerTerminationRecredForm_English, PRM_PractitionerTerminationForm_English (via GetPractitionerTerminationData)

---

### 3.5 PRM_GetPractitionerTerminationData

**DataRaptor:** GetHealthProviderNpiWithAccountId (PRMDRExtractHealthCareProviderNpiRecords)

**Purpose:** Fetches practitioner termination data including PNC for termination flows.

**OmniScript:** PRM_PractitionerTerminationForm_English

---

### 3.6 PRM_FetchPDMManualUpdateDetails

**DataRaptors:** PRMFetchAccountAndPracticeLocations, PRMDrExtractPractForProfStaff

**Purpose:** Fetches PDM manual update details; PNC is used for practitioner/vendor filtering and display (e.g., "Add/Remove PNC" option, PracLocPNC, SelectedPLPNC).

**OmniScript:** PRM_PDMManualUpdate_English

---

## 4. Apex Usage

| Class | Purpose |
|-------|---------|
| **PRM_CheckCAQHAccessOnDueAccountsBatch** | Excludes PNC practitioners from CAQH access checks: `PRM_PNC__c = false` in query. PNC practitioners don’t need CAQH recredentialing validation. |
| **PRM_AccountTriggerHelper** | Rolls up Vendor PNC changes to Practitioner Accounts via `updateAccountPNC`. |
| **PRM_CommonUtils** | `updateAccountPNCHelper` – Practitioner PNC = true only if all practice affiliations are PNC. |
| **PRM_RCATTerminationBatchHelper** | `pncOnlyPractitioner()` – Practitioner is PNC-only if all practice affiliations have PNC=true. Updates `PRM_PNC__c` on practitioner Accounts during RCAT processing. |
| **PRM_FutureDatedProcessingBatchHandler** | Uses `pncOnlyPractitioner()` and HCPF Account PNC to update practitioner participation/credentialing status. PNC or delegated practitioners may stay Participating or become Non-Par based on plan-based membership. |
| **PRM_FetchPractTermDataHandler** | Maps `npiData.Account.PRM_PNC__c` → `accData.PNC` and `searchRecord.PNC` for practitioner termination data API. |
| **PRM_OffCycleProviderSearch** | Returns `PNC` (group and facility) in provider search results. |
| **PRM_PARProviderSearch** | Returns `PNC` for PAR provider search. |
| **PRM_IPUtilityHelper** | Maps `hcfRecord.Account.PRM_PNC__c` → `PracLocPNC`, `vendorRecord.PRM_PNC__c` → `PNC` for IP responses. |
| **PRM_AncillaryProviderUtilsService** | Maps `fac?.Account?.PRM_PNC__c` → `PNC` in provider data. |
| **PRM_OmniUtils** | Uses `PNC` input and `acc.prm_pnc__c` for OmniScript utilities. |
| **PRM_PractitionerTerminationBatchHelper** | Queries `Account.PRM_PNC__c` for facility termination logic. |

---

## 5. OmniScript-Specific Usage

| OmniScript | Element / Usage | Purpose |
|------------|-----------------|---------|
| **PRM_PDMManualUpdate_English** | PracPNC, PracPNC2, SelectedPLPNC, CBPNCCkd, CBPNCUnCkd, AddOrRemovePNCRecords, SV_PNC | PDM manual update: Add/Remove PNC option; displays PNC (Par Non Cred) for practitioner and practice location; step validation when PNC type selected. |
| **PRM_ProviderChangeForm_English** | PNC in SetValues2, IPVerifyPractitionerDetails | Passes PNC to verification IP; default PNC=false for new practitioners. |
| **PRM_PractitionerTerminationForm_English** | PNC, PracLocPNC | Displays practitioner and practice location PNC in termination flow. |
| **PRM_PractitionerTerminationRecredForm_English** | PNC, PracLocPNC | Same for recredentialing termination. |
| **PRM_PractitionerParticipationForm_English** | IsPNCGroup, SetErrorNonPNCGroup, MSG_PNCGroup, IPExtractGroupName | When adding to PNC group: `IsPNC=true` passed to IP; error if non-PNC group selected when practitioner is PNC. |
| **PRM_PractitionerCreation_English** | isPNCGroup | Passes IsPNCGroup when creating practitioner. |
| **PRM_OffCycleCredentialing_English** | SetErrorsWhenPracTrueandAccFalse, TextBlock14, TextBlock15 | Validates PNC consistency: practitioner PNC vs. group PNC; shows error when mismatched. |
| **PRM_PNCReview_English** | (entire OmniScript) | PNC case review – initial credentialing for PNC practitioners. |
| **PRM_PNCPDA_English** | (entire OmniScript) | PNC PDA (Provider Data Audit) flow. |
| **PRM_PNCQC_English** | (entire OmniScript) | PNC QC (Quality Check) flow. |

---

## 6. FlexCard

| FlexCard | Purpose |
|----------|---------|
| **PRMPractitionerDemographics** | Displays `Account.PRM_PNC__c` in practitioner demographics (optionalFields, selectedFields). |

---

## 7. Business Rules Summary

| Rule | Description |
|------|-------------|
| **CAQH Batch Exclusion** | Practitioners with `PRM_PNC__c = true` are excluded from CAQH access checks (they don’t use CAQH for recredentialing). |
| **Recred Termination Letter** | PNC practice locations (`Account.PRM_PNC__c = true`) are excluded from recredentialing termination letters. |
| **Practitioner Rollup (current)** | Practitioner `PRM_PNC__c = true` only when **all** practice affiliations (HCPF) have `Account.PRM_PNC__c = true`. |
| **Practitioner Rollup (target)** | Source becomes `HealthcareFacility.PRM_PNC__c` via `PRM_PractitionerLocationAffiliation`. **Default:** true only when **all** participating locations PNC. **When `Account.PRM_PNCAnyLocation__c = true`:** true when **any** participating location PNC. No participating locations → false. |
| **DelegatedValid (VerifyPractitionerDetails)** | Non-credentialed practitioners with `PNC = false` cannot be in delegated groups; PNC practitioners can. |
| **PNCValid (VerifyPractitionerDetails)** | When facility is not PNC, at least one PNC practitioner is required for COI/PDM flows. |
| **RCAT / Future-Dated Processing** | PNC and delegated practitioners are processed together; participation status depends on plan-based membership. |

---

## 8. Key Differences: PRM_PNC__c vs PRM_DelegatedOnly__c

| Aspect | PRM_PNC__c | PRM_DelegatedOnly__c |
|--------|------------|------------------------|
| **Meaning** | Par Non Cred – participates without full credentialing via group | All practice locations delegated |
| **Applies to** | Vendor (practice location) and Practitioner | Practitioner only |
| **Rollup logic** | Current: true if **all** affiliations PNC. Target: **all** locations PNC by default, **any** location PNC when `PRM_PNCAnyLocation__c = true` (configurable per practitioner) | Practitioner delegated = true if **all** locations delegated (old) / **any** (new, unconditional) |
| **CAQH** | Excludes PNC practitioners | (Replaced by credentialing status) |
| **Recred Letter** | Excludes PNC locations from letter | N/A |
| **VerifyPractitionerDetails** | PNCValid, DelegatedValid formulas | DelegatedValid formula |
