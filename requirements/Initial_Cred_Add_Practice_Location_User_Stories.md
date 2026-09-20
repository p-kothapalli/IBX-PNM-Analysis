# Initial Cred – Add Practitioner's Practice Location on App Review & PSV Service Verification

**Reference:** Requirement 1334637  
**Goal:** Enable business users to add new practice locations on the App Review & PSV Service Verification screen, following the same process as PAR form and Off Cycle – Group Selection screen (pick existing or add new; new locations run through Precisely verification and duplicate checks).

---

## 1. Reference Flows – PAR Form & Off Cycle Group Selection (In-Depth Analysis)

### 1.1 PAR Form – Group Selection Screen

**Component:** `prmTextElementOverrideForGroupSelection` (LWC override)  
**OmniScript:** Practitioner Participation Form – Group Selection step  
**Apex:** `PRM_PARProviderSearch.getParProviderSearchData`

| Element | Behavior |
|---------|----------|
| **Main Group Table** | Single-select; user picks the main group that best matches. Columns: Practice Location Number, Address, City, State, Zip, NPI, etc. |
| **Additional Addresses Table** | Multi-select (max 10); shown after main group selected. User selects one or more practice addresses associated to the main group. |
| **"Click here" link** | *"If you wish to join a location that is not listed in the table below, please click here to continue your request."* – Saves current selection, closes modal; user proceeds to address entry flow for new location. |
| **Search Filters** | When result set > 50: Practice Location Number, Address Line 1, City, State, Zip (required), Search button. |

**Validations:**
- `PRMDRCheckExistingGroupNPI` – Checks if Group NPI already exists; returns `ExistingGroupNPIId` when duplicate.
- `PRM_ExistingAccountService.extractExistingAccount` – Validates selected account: `accountTermed`, `accountDuplicate` when Tax ID + Account Name selected.
- `RunAddCheck` – Triggers `PRM_DuplicateAddCheck` IP for duplicate address check (AddressBlock, SelAccountIds).

**Data Flow:** `PractionerGroup` → `GroupInformation` (GroupNPI, GroupTaxId, AccountSelected, ExistingGroupSelected, PrimaryFacilityDetails, AdditionalFacilityDetails, MailingAddressForGroup, BillingAddress).

---

### 1.2 Off Cycle – Group Selection Screen

**Component:** `prmGroupSelectionOffCycle`  
**Apex:** `PRM_OffCycleProviderSearch.getOffcycleProviderSearch`

| Element | Behavior |
|---------|----------|
| **Main Group Table** | Single-select; "Please select the record that best matches the main group you wish to update." |
| **Additional Addresses Table** | Multi-select (max 10); "Please select one or more practice addresses associated to the main group selected above." |
| **"Click here" link** | Same as PAR – saves and closes; user proceeds to add new location not in list. |
| **Search Filters** | `c-prm-address-filter-grid` when `isLargeResultSet` (result set > 50). |

**New Location Path (when "here" clicked):**
- `newPracLoc: true` set in GroupInformation.
- User is taken to address entry (Primary, Mailing, Billing).
- **Precisely API:** `PRM_OffCyclePreciselyAPI` – validates entered addresses via Precisely API callout.
- **Duplicate Check:** Address data compared against existing locations; `PRM_DuplicateAddCheck` or equivalent logic.

**Data Flow:** `PractitionerGroup` → `GroupInformation` (PrimaryFacilityDetails, AdditionalFacilityDetails, MailingAddressForGroup, BillingAddress, newPracLoc).

---

### 1.3 Validations Summary (PAR & Off Cycle)

| Validation | PAR Form | Off Cycle | Purpose |
|------------|----------|-----------|---------|
| **Duplicate NPI** | PRMDRCheckExistingGroupNPI | PRMDRCheckExistingGroupNPI | Prevent duplicate Group NPI |
| **Termed/Duplicate Account** | extractExistingAccount (Tax ID + Name) | — | Account termed or duplicate |
| **Duplicate Address** | PRM_DuplicateAddCheck (AddressBlock, SelAccountIds) | PRM_DuplicateAddCheck / Precisely response | Address already exists for account |
| **Precisely Verification** | PRM_PreciselyAPIForPARForm | PRM_OffCyclePreciselyAPI | Standardize/validate address via Precisely API |
| **Overlapping Address** | PRM_AddressTriggerHandler | PRM_AddressTriggerHandler | Same address type, overlapping dates |

---

## 2. Current State – App Review & PSV Service Verification

### 2.1 Affected OmniScripts

| OmniScript | Step | Current Practice Location Behavior |
|------------|------|-----------------------------------|
| **PRM_PSVSubOsTxnyRole_English** | ServiceAreaVerificationStep | PLRecredBlock (Recred only): HCFTypeAhead to select existing PL; repeatable (max 4). No "add new" option. |
| **PRM_RecredQC_English** | ServiceAreaVerificationStep | Same PLRecredBlock pattern. |
| **PRM_CredApplicationReviewOSTxnyRole_English** | (Embedded PSV) | Uses PSVSubOsTxnyRole; Service Area Verification step. |

### 2.2 Current Service Area Verification Step Structure

- **PlQuestion:** "Would you like to add Practice Locations?" (Yes/No)
- **PLRecredBlock:** Shown when PlQuestion = Yes AND IsRecredentialing = true
- **HCFTypeAhead:** Practice Location Name – type-ahead to select **existing** HealthcareFacility only
- **PracticeAddressBlk:** Address fields (read-only when existing selected)
- **DupPracticeLocationError, TBErrorExistsPL:** Error messages for duplicate/existing PL
- **IPValidatePracticeLocation:** Validates practice location before proceed

**Gap:** No ability to add a **new** practice location (address not in system). User can only select from existing.

---

## 2.3 Object Model – Practice Location Search

| Object | Key Fields | Role in Search |
|--------|------------|----------------|
| **Account** | Id, Name, PRM_PNC__c, PRM_ParticipationStatus__c, PRM_DoingBusinessAsName__c | Vendor/Group; scopes practice locations via HealthcareFacility.AccountId |
| **HealthcareFacility** | Id, AccountId, LocationId, Name, PRM_PracticeName__c, PRM_DoingBusinessAsName__c, PRM_IdentifierHealthcareFacility__r.Name (PL Number), PRM_NpiId__r.Npi, PRM_Primary__c, PRM_Active__c, PRM_PractitionerRole__c | Practice Location; filtered by AccountId, NPI (optional), RecordType != NCPDP, PRM_PracticeClassification__c != 'Facility' |
| **Schema.Address** | ParentId (Location), PRM_AddressType__c, PRM_AddressLine1__c, PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_Phone__c | Physical address; joined via HealthcareFacility.LocationId |
| **Location** | Id | Standard object; Address.ParentId |
| **HealthcareFacilityNetwork** | HealthcareFacilityId, PRM_Taxonomy__r.Name | Taxonomy; used for specialty/Level3B display |

**Search scope:** Practice locations are typically scoped to a Vendor/Group (Account). PAR/Off Cycle require NPI + Tax ID to identify the group first; PDM Manual Update allows NPI, Tax ID, or PL-specific search. **For App Review/PSV Add PL:** Business has confirmed search can span **different vendors** (broader scope).

---

## 2.4 PDM Guided Flows – Practice Location Search Comparison

| Flow | Search Input | Data Source | Selection Mode | Max Select | Search Filters (>50) |
|------|--------------|-------------|----------------|------------|----------------------|
| **PAR Form** | NPI + Tax ID + Group Name (pre-step) | `PRM_PARProviderSearch.getParProviderSearchData` | Main table single + Additional table **multi** | 10 additional | PL Number, Addr1, City, State, Zip (required) |
| **Off Cycle** | NPI + Tax ID (pre-step) | `PRM_OffCycleProviderSearch.getOffcycleProviderSearch` | Main table single + Additional table **multi** | 10 additional | `c-prm-address-filter-grid` |
| **PDM Manual Update** | NPI, Tax ID, or PL (PL Number, PL Name, DBA, Addr1, City, State, Zip) | `PRM_FetchPDMManualUpdateDetails` → PRMFetchVendorAndHCFWithNPI/TaxID | **Single** (cfPRMMainGroupSelection) | 1 | **None** – single result list |
| **Add Ancillary** | NPI + Tax ID + Group (pre-step) | Similar to PAR | Main + Additional **multi** | 10 additional | — |
| **PSV / Recred** | None (pre-loaded from Case) | HCFTypeAhead – `useDataJson: false`; data from parent/JSON | Type-ahead **single** per PLRecredBlock | 4 (repeatable blocks) | **None** |

**Key insight:** PAR and Off Cycle support **multi-select** (up to 10 additional addresses) via a table. PDM Manual Update and PSV are **single-select** only. PSV uses a type-ahead with no search filters; data is pre-loaded from the Case context.

---

## 2.5 Search Recommendations & Questions (Group Selection – Pick Existing or Add New)

### Recommendations for Easier Search & Multi-Select

| # | Recommendation | Rationale |
|---|----------------|-----------|
| **R1** | **Replace type-ahead with table + multi-select** | PAR/Off Cycle use a **table** (Group Name, Full Address) with checkboxes for multi-select. Type-ahead forces one-at-a-time selection; a table lets users see and select multiple locations at once. |
| **R2** | **Add search filters when result set > 50** | PAR uses PL Number, Address Line 1, City, State, Zip (required), Search. Off Cycle uses `c-prm-address-filter-grid`. Without filters, large result sets are hard to navigate. |
| **R3** | **Support multi-select (max 10)** | Align with PAR/Off Cycle "Additional Addresses" pattern. User can select one or more practice locations in a single interaction instead of repeating the type-ahead 4 times (current PLRecredBlock repeat limit). |
| **R4** | **Ensure data source is explicit** | PSV HCFTypeAhead uses `useDataJson: false` – data comes from parent. Create `PRM_ServiceAreaVerificationProviderSearch` (or similar) to fetch practice locations for Case Manager's vendor/group, mirroring PAR/Off Cycle. |
| **R5** | **Reuse PAR/Off Cycle LWC pattern** | `prmTextElementOverrideForGroupSelection` and `prmGroupSelectionOffCycle` already implement: main table, additional table, "click here" for new, search filters. Extend or create `prmServiceAreaVerificationGroupSelection` with same UX. |
| **R6** | **Optional: Search by PL Number, Address, City, State, Zip** | PDM Manual Update allows PL-specific search. If App Review/PSV context has many locations, consider adding similar filters (PL Number, Address Line 1, City, State, Zip) for faster lookup. |

### Proposed UX for "Select Existing" Path

1. **Table view** (not type-ahead): Columns = Group Name, Full Address (per `groupSelectionUtil.js`).
2. **Multi-select**: Checkboxes; max 10 selections (or configurable).
3. **Search filters** (when > 50 results): PL Number, Address Line 1, City, State, Zip (required), Search button.
4. **"Click here" link**: "If you wish to add a location that is not listed above, please click here to enter a new address."
5. **Selected summary**: Show count of selected locations; allow Remove per row.

### Questions for Product / Business

| # | Question | Options / Notes | **Decision** |
|---|----------|-----------------|--------------|
| **Q1** | **Max number of practice locations per add?** | Current PLRecredBlock repeat = 4. PAR/Off Cycle additional = 10. Should App Review/PSV allow 4, 10, or unlimited? | **10** |
| **Q2** | **Search scope – Case Manager's vendor only, or broader?** | PAR/Off Cycle scope by NPI + Tax ID (group). PSV context has Case; does Case Manager's vendor/group define the scope? Or should user be able to search across all vendors? | **Different vendors** (broader scope) |
| **Q3** | **Type-ahead vs table – which is preferred?** | Type-ahead: compact, one-at-a-time. Table: visible list, multi-select. Business preference? | **Table** (many locations) |
| **Q4** | **When to show search filters?** | PAR/Off Cycle show filters when result set > 50. Same threshold for App Review/PSV? | **Yes** (>50) |
| **Q5** | **PDM Manual Update – extend to multi-select?** | PDM currently single-select. Should PDM Manual Update also support multi-select for consistency? | *(Not answered)* |
| **Q6** | **HCFTypeAhead data source for PSV** | Where does HCFTypeAhead get its practice location list? | **See §2.6 below** |

---

### 2.6 PSV HCFTypeAhead Data Source (Investigation Result)

**Source:** Integration Procedure **PRM_FetchPracticeLocationReCred** + DataRaptor **PRMFetchPracticeLocationReCred**

| Element | Role |
|---------|------|
| **HCFTypeAhead** | Type Ahead Block; `useDataJson: false` – uses remote IP for data |
| **SetPracticeLocation** | Child of HCFTypeAhead; **Integration Procedure Action** that runs when user selects |
| **IP:** `PRM_FetchPracticeLocationReCred` | Fetches practice locations; inputs: `TypeAhead`, `VendorNPI` (%NPICred\|n%), `VendorTaxId` (%TaxIdCred\|n%); output: `HealthcareFacility` |
| **DataRaptors** | `DRExtractVendorPracticeLocation` (by NPI+TaxId), `DRExtractVendorPracticeLocationByTaxId` (by TaxId) |

**Current scope:** Single vendor per PLRecredBlock – NPI + Tax ID from NPICred and TaxIdCred in the same block. Practice locations are fetched for that vendor only.

**Implication for new design:** To support **different vendors** (broader scope), the new Apex/IP must search across multiple vendors, not just the one identified by NPI+TaxId in the block. Consider: Case Manager's assigned vendors, or user-entered search criteria (NPI, Tax ID, PL Number, etc.) that can match any vendor.

---

## 3. User Stories (Developer-Focused)

---

### US-IC-ADDPL-1: Practice Location Selection – Table with Multi-Select & Add New

**As a** Credentialing Specialist on the App Review or PSV Service Verification screen  
**I want** to select one or more existing practice locations from a table, or add a new location not in the system  
**So that** I can efficiently add practitioners at multiple office locations in one step.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | When PlQuestion = "Yes", user sees **Location Selection Mode** radio: "Select from existing locations" or "Add a new location" | UI shows both options |
| AC2 | **Select existing:** Table displays practice locations with columns **Group Name**, **Full Address**; user can select up to **10** via checkboxes | Multi-select; max 10 |
| AC3 | Search scope spans **different vendors** (not limited to single NPI+TaxId) | Apex returns PLs from multiple accounts |
| AC4 | When result set > 50, **search filters** appear: PL Number, Address Line 1, City, State, Zip (required), Search button | Filters shown; Zip required to search |
| AC5 | "If you wish to add a location that is not listed above, please click **here**" – click switches to Add New mode | Link toggles mode |
| AC6 | **Add new:** Address entry block (AddrLine1, AddrLine2, City, State, Zip, Zip+4, Phone, Fax); "To select an existing location instead, click **here**" returns to table | Bidirectional toggle |
| AC7 | Selected locations display in Practice Address Block; user can Remove per row | Summary + Remove per row |

---

#### Technical Specification – LWC

**Component:** Create `prmServiceAreaVerificationGroupSelection` (or extend `prmGroupSelectionOffCycle`)

**Reference:** `prmGroupSelectionOffCycle`, `prmTextElementOverrideForGroupSelection`, `groupSelectionUtil.js`

##### Table Columns (from groupSelectionUtil.js)

```javascript
const columns = [
    { label: 'Group Name', fieldName: 'AccountName' },
    { label: 'Full Address', fieldName: 'FullAddress' }
];
```

| Column | fieldName | Source (Apex) | Notes |
|--------|-----------|---------------|-------|
| Group Name | `AccountName` | `FacilityDetails.AccountName` or `HealthcareFacility.Account.Name` | Vendor/group name |
| Full Address | `FullAddress` | Formatted: `PLNumber + ' - ' + AddrLine1 + ' ' + AddrLine2 + ' ' + City + ' ' + State + ' ' + Zip` (or Zip + ' - ' + last 4 of Phone) | Per PRM_PARProviderSearch.buildAddressData |

##### c-prm-enhanced-datatable Props

| Prop | Value | Purpose |
|------|-------|---------|
| `columns` | `[{ label: 'Group Name', fieldName: 'AccountName' }, { label: 'Full Address', fieldName: 'FullAddress' }]` | Column definitions |
| `source` | Array of FacilityDetails | Data to display |
| `maxrowselection` | `10` | Max 10 rows selectable |
| `key-field` | `"FacilityId"` | Unique row key |
| `hidecheckboxcolumn` | `false` | Show checkboxes for multi-select |
| `ongetselectedrows` | Handler for selected rows | Capture selection |
| `allsource` | Same as source | For pagination/sort |
| `apppagesize` | `10` | Rows per page |
| `pagination` | `true` | Enable pagination |
| `enable-search` | `true` | Enable table search |
| `sorteddirection` | `'asc'` | Default sort |
| `sortedby` | Column fieldName | Sort column |
| `defaultsortdirection` | `'asc'` | Default direction |

##### Search Filter Fields (when isLargeResultSet = resultCount > 50)

| Field | name | label | Required |
|-------|------|-------|----------|
| PL Number | `mainSearchPLNumber` | Practice Location Number | No |
| Address Line 1 | `mainSearchAddLine1` | Address Line 1 | No |
| City | `mainSearchCity` | City | No |
| State | `mainSearchState` | State | No |
| Zip | `mainSearchZip` | Zip | **Yes** |

Reference: `prmTextElementOverrideForGroupSelection.html` lines 24–28; filter logic in `handleSearchChange` / `filterMainData`.

##### Apex Response Structure (for table data)

Create `PRM_ServiceAreaVerificationProviderSearch.cls` (or extend). Return JSON with:

```json
{
  "FacilityDetails": [
    {
      "FacilityId": "<HealthcareFacility.Id>",
      "LocationId": "<Location.Id>",
      "AccountName": "<Account.Name>",
      "FullAddress": "<PLNumber> - <AddrLine1> <AddrLine2> <City> <State> <Zip>",
      "PLNumber": "<PRM_IdentifierHealthcareFacility__r.Name>",
      "AddLine1": "...",
      "AddLine2": "...",
      "City": "...",
      "State": "...",
      "Zip": "...",
      "Zip4": "...",
      "Phone": "...",
      "PhoneExt": "...",
      "Fax": "...",
      "PrimaryPractice": true/false
    }
  ],
  "FacilitySize": <number>,
  "FacilityFound": true/false,
  "isLargeResultSet": true/false
}
```

**Search inputs:** CaseId (or ContextId), optional filters: NPI, TaxId, PLNumber, AddrLine1, City, State, Zip. **Scope:** Search across different vendors (not single NPI+TaxId).

##### OmniScript JSON Path Mapping (selected rows → PLRecredBlock)

| Target Path | Source (from table selection) |
|-------------|------------------------------|
| `PLRecredBlock` / `PracticeLocationBlock` | Array of selected FacilityDetails |
| `FacilityId` | `FacilityDetails[i].FacilityId` |
| `LocationId` | `FacilityDetails[i].LocationId` |
| `AddrLine1` | `FacilityDetails[i].AddLine1` |
| `AddrCity` | `FacilityDetails[i].City` |
| `AddrState` | `FacilityDetails[i].State` |
| `AddrZip` | `FacilityDetails[i].Zip` |
| `AddrZip4` | `FacilityDetails[i].Zip4` |
| `AddrPhone` | `FacilityDetails[i].Phone` |
| `AddrPhoneExtension` | `FacilityDetails[i].PhoneExt` |
| `AddrFax` | `FacilityDetails[i].Fax` |
| `Name` | `FacilityDetails[i].AccountName` or PracticeName |
| `isNewLocation` | `false` (existing) |

##### Implementation Steps (Developer Checklist)

1. [ ] Create Apex `PRM_ServiceAreaVerificationProviderSearch.getPracticeLocationsForServiceVerification(CaseId, searchFilters)` – scope: multiple vendors
2. [ ] Create LWC `prmServiceAreaVerificationGroupSelection` – extend `prmGroupSelectionOffCycle` pattern
3. [ ] Define `columns` in LWC (AccountName, FullAddress)
4. [ ] Wire `c-prm-enhanced-datatable` with `maxrowselection=10`, `key-field="FacilityId"`
5. [ ] Add search filter section when `FacilitySize > 50`; implement `handleSearchChange` to filter `source`
6. [ ] Add "click here" link – `handleHereLink` sets `LocationSelectionMode = 'Add new'`
7. [ ] Add "To select an existing location instead, click here" – toggle back
8. [ ] On Save: emit selected rows via `omniApplyCallResp` to `PLRecredBlock` / `PracticeLocationBlock`
9. [ ] Extend PlQuestion / PLRecredBlock show condition for Initial Cred (not only IsRecredentialing)

---

### US-IC-ADDPL-2: Precisely Address Verification for New Locations

**As a** Credentialing Specialist adding a new practice location  
**I want** the entered address validated and standardized via Precisely  
**So that** addresses are correct and consistent with system standards.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | When user enters new address and proceeds, address is sent to Precisely API | IP/DR invoked |
| AC2 | Precisely returns standardized address; UI shows Accept / Decline (per `prmAddressComparisonParForm`) | User can Accept or Decline |
| AC3 | If Decline: address stored as entered; `Standardized = false` | No overwrite |
| AC4 | Integration follows `PRM_OffCyclePreciselyAPI` or `PRM_PreciselyAPIForPARForm` | Same pattern |

#### Technical Specification

| Component | Reference | Notes |
|-----------|-----------|-------|
| IP | `PRM_InitialCredPreciselyAPI` (new or extend) | Input: AddressBlock; Output: Standardized address |
| DataRaptors | PRMDRTPreciselyRequestData, PRMPreciselyAPICalloutResponseTransform | Reuse from PAR/Off Cycle |
| UI | `prmAddressComparisonParForm` | Accept/Decline comparison |

#### Implementation Steps

1. [ ] Create or extend IP for App Review/PSV context
2. [ ] Wire IP to run when user completes Add New address entry and clicks Next
3. [ ] Add address comparison step (Accept/Decline) before proceeding
4. [ ] Map Precisely response to Address fields; set `Standardized` flag

---

### US-IC-ADDPL-3: Duplicate Address Check for New Locations

**As a** Credentialing Specialist adding a new practice location  
**I want** the system to detect if the address already exists before creating a new location  
**So that** we avoid duplicate practice locations.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | Before creating HealthcareFacility, run duplicate check | IP invoked |
| AC2 | Duplicate = same/similar address (AddrLine1, City, State, Zip) for same or related account | Logic matches PAR |
| AC3 | If duplicate: show "A practice location with this address already exists. Please select it from the list or enter a different address." | Error displayed |
| AC4 | User can correct address or switch to Select Existing | No block |

#### Technical Specification

| Component | Reference | Notes |
|-----------|-----------|-------|
| IP | `PRM_DuplicateAddCheck` | Reuse; inputs: AddressBlock, SelAccountIds |
| DataRaptors | DRExtractLocIdByAccountId, DRGetAddressData | Compare to existing Address records |

#### Implementation Steps

1. [ ] Add DuplicateAddressCheck IP action after Precisely (or before record creation)
2. [ ] Pass new address + Case Manager's account IDs (or selected vendor IDs)
3. [ ] If duplicate: set error flag; display DupPracticeLocationError
4. [ ] Block Next until user corrects or selects existing

---

### US-IC-ADDPL-4: Additional Validations (NPI, Account, Overlapping)

**As a** system processing a new practice location  
**I want** PAR/Off Cycle validations to apply  
**So that** data integrity is consistent.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | Group NPI check: `PRMDRCheckExistingGroupNPI` when Group NPI entered | Error if duplicate NPI |
| AC2 | Account validation: not termed, not duplicate (extractExistingAccount) | When applicable |
| AC3 | Overlapping address: PRM_AddressTriggerHandler enforced | No overlapping dates |
| AC4 | Required: AddrLine1, City, State, Zip; Phone recommended | Validation on submit |

#### Implementation Steps

1. [ ] Wire PRMDRCheckExistingGroupNPI when Group NPI present
2. [ ] Ensure PRM_AddressTriggerHandler applies to new Address records
3. [ ] Add client-side and server-side required-field validation

---

### US-IC-ADDPL-5: Record Creation for New Practice Location

**As a** system when user confirms a new practice location  
**I want** Location, Address, HealthcareFacility, HealthcarePractitionerFacility created correctly  
**So that** the new location is linked to the practitioner and Case.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | Location (Schema.Location) created | Record exists |
| AC2 | Address (Schema.Address) with PRM_AddressType__c = Primary Practice | Linked to Location |
| AC3 | HealthcareFacility created; linked to Location, Account | Record exists |
| AC4 | HealthcarePractitionerFacility (PPL) links practitioner to facility | PPL created |
| AC5 | PRM_Pending__c = true for new records | Flag set |
| AC6 | Follows `PRM_CreateRecordsForPCF` or `PRMCreateGroupRecordsForOffCycle` pattern | Same flow |

#### Technical Specification

| Component | Reference | Notes |
|-----------|-----------|-------|
| IP | `PRM_InitialCredAddPracticeLocation` or extend `PRM_ReviewParCaseRecordsUpdate` | New or extend |
| DataRaptors | PRMDRCreateLocation, PRMDRCreateAddress, PRMDRCreateHealthcareFacility, PRMDRCreatePPL | Or equivalent |

#### Implementation Steps

1. [ ] Create/extend IP for Initial Cred / App Review context
2. [ ] Map Add New address block to DataRaptor inputs
3. [ ] Create records in order: Location → Address → HealthcareFacility → PPL
4. [ ] Set PRM_Pending__c = true; link to Case/Practitioner

---

### US-IC-ADDPL-6: Scope – App Review and PSV Flows

**As a** Product Owner  
**I want** add-practice-location available in both App Review and PSV  
**So that** specialists can add locations at the right stage.

---

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | App Review (CredApplicationReviewOSTxnyRole) includes add-location capability | Available in flow |
| AC2 | PSV (PSVSubOsTxnyRole, RecredQC) includes add-location capability | Available in flow |
| AC3 | Behavior consistent across both | Same UI, same validations |

#### Implementation Steps

1. [ ] Update ServiceAreaVerificationStep in PRM_PSVSubOsTxnyRole_English
2. [ ] Update ServiceAreaVerificationStep in PRM_RecredQC_English
3. [ ] Verify CredApplicationReview embeds updated PSVSubOsTxnyRole
4. [ ] Test both entry points

---

## 4. Implementation Order and Dependencies

| Order | User Story | Dependencies |
|-------|------------|--------------|
| 1 | US-IC-ADDPL-1 (Pick Existing or Add New) | None |
| 2 | US-IC-ADDPL-2 (Precisely) | US-IC-ADDPL-1 |
| 3 | US-IC-ADDPL-3 (Duplicate Check) | US-IC-ADDPL-1 |
| 4 | US-IC-ADDPL-4 (Additional Validations) | US-IC-ADDPL-1 |
| 5 | US-IC-ADDPL-5 (Record Creation) | US-IC-ADDPL-1, 2, 3, 4 |
| 6 | US-IC-ADDPL-6 (Scope – App Review & PSV) | US-IC-ADDPL-1–5 |

---

## 5. Reference Components (For Development)

| Purpose | PAR Form | Off Cycle | App Review / PSV (Target) |
|---------|----------|-----------|----------------------------|
| Group/Location selection LWC | prmTextElementOverrideForGroupSelection | prmGroupSelectionOffCycle | **prmServiceAreaVerificationGroupSelection** (new) |
| Provider search Apex | PRM_PARProviderSearch | PRM_OffCycleProviderSearch | **PRM_ServiceAreaVerificationProviderSearch** (new) |
| Precisely IP | PRM_PreciselyAPIForPARForm | PRM_OffCyclePreciselyAPI | PRM_InitialCredPreciselyAPI (new or extend) |
| Duplicate check IP | PRM_DuplicateAddCheck | PRM_DuplicateAddCheck | PRM_DuplicateAddCheck |
| NPI check DR | PRMDRCheckExistingGroupNPI | PRMDRCheckExistingGroupNPI | PRMDRCheckExistingGroupNPI |
| Address comparison UI | prmAddressComparisonParForm | (similar) | Reuse or adapt |

### Key Files for LWC Development

| File | Purpose |
|------|---------|
| `force-app/main/default/lwc/prmGroupSelectionOffCycle/` | Primary reference – modal, table, filters, "here" link |
| `force-app/main/default/lwc/prmGroupSelectionOffCycle/groupSelectionUtil.js` | Column definitions: `AccountName`, `FullAddress` |
| `force-app/main/default/lwc/prmTextElementOverrideForGroupSelection/` | Search filter HTML (mainSearchPLNumber, mainSearchAddLine1, etc.) |
| `force-app/main/default/classes/PRM_PARProviderSearch.cls` | FacilityDetails structure, FullAddress format |
| `force-app/main/default/classes/PRM_OffCycleProviderSearch.cls` | Alternative Apex pattern |

---

## 6. Repro Steps for Validation (Post-Implementation)

1. Login as Cred User. Navigate to App Review or PSV (open existing Case).
2. Proceed to Service Area Verification step.
3. Answer "Yes" to "Would you like to add Practice Locations?"
4. **Select existing path:**
   - Choose "Select from existing locations"
   - Verify table displays with columns **Group Name**, **Full Address**
   - Select 1–10 practice locations via checkboxes; click Save
   - If > 50 results: verify search filters (PL Number, Address Line 1, City, State, Zip) appear; enter Zip + Search
   - Verify selected locations appear in Practice Address Block; test Remove per row
5. **Add New path:**
   - Click "If you wish to add a location that is not listed above, please click **here**"
   - Verify mode switches to Add New; address entry block appears
   - Enter: Address Line 1, City, State, Zip, Phone
   - Click Next – verify Precisely validation runs; Accept or Decline standardized address
   - Verify duplicate check: if address exists, error is shown
   - Complete flow; verify new Location, Address, HealthcareFacility, PPL created with PRM_Pending__c = true
6. **Toggle test:** From Add New, click "To select an existing location instead, click here" – verify return to table view.

---

*Source: Codebase analysis of prmTextElementOverrideForGroupSelection, prmGroupSelectionOffCycle, PRM_PSVSubOsTxnyRole_English, PRM_RecredQC_English, PRM_DuplicateAddCheck, PRM_OffCyclePreciselyAPI, PRM_PreciselyAPIForPARForm, AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md, Ancillary_PSV_Business_Licenses_User_Story.md.*
