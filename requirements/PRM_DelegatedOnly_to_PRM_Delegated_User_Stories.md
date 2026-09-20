# PRM_DelegatedOnly → PRM_Delegated – User Stories (Flow-Centric)

**Related:** PNC migration (`PRM_PNC_Logic_Change_Implementation_Plan.md`) touches the same flows (PDM, Provider Change, Off-Cycle, Termination, Demographics). When implementing both, use the overlap table below and do changes together.

## Quick Reference for Junior Developers

| Concept | Before | After |
|---------|--------|-------|
| **Field name** | `PRM_DelegatedOnly__c` | `PRM_Delegated__c` |
| **Practitioner delegated logic** | True if **all** practice locations delegated | True if **any** practice location delegated |
| **delegatedOnlyPractitioner()** | Start true, set false when any location NOT delegated | Start false, set true when any location IS delegated |
| **accToDelInfoCodeMap (CommonServiceHelper)** | True when all facilities delegated | True when any facility delegated |
| **CAQH batch filter** | `PRM_DelegatedOnly__c = false` | Removed; use `PRM_CredentialingStatus__c = 'Credentialed'` |
| **DataRaptor field** | `PRM_DelegatedOnly__c` | `PRM_Delegated__c` |
| **Output name** | `IsPractitionerDelegated` (unchanged) | Same |

---

## PNC + Delegated Overlap: Same Flows, Same Components

**If you are implementing both PNC migration and Delegated changes, do them together for these flows.**

| Flow | OmniScript | PNC Change | Delegated Change | Implement Together? |
|------|------------|-----------|-----------------|---------------------|
| **PDM Manual Update** | PRM_PDMManualUpdate_English | Facility PNC (PracLocPNC), PNCValid | DelegatedValid, IsPractitionerDelegated | **Yes** – PRM_VerifyPractitionerDetails |
| **Provider Change Form** | PRM_ProviderChangeForm_English | ProviderDetails:PNC, PNCValid | DelegatedValid, IsPractitionerDelegated | **Yes** – PRM_VerifyPractitionerDetails |
| **Off-Cycle Credentialing** | PRM_OffCycleCredentialing_English | Facility PNC display | Block delegated practitioners, IsPractitionerDelegated | **Yes** – Off-Cycle search |
| **Practitioner Termination** | PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English | PracLocPNC (location PNC) | IsPractitionerDelegated (practitioner) | **Yes** – Termination data |
| **Practitioner Demographics** | PRMPractitionerDemographics FlexCard | Practitioner PNC (rollup) | IsPractitionerDelegated (new field) | **Yes** – PRM_FetchPractitionerDemographics |

**Shared components (PNC + Delegated):**
- **PRM_VerifyPractitionerDetails** – PNCValid (PNC) + DelegatedValid (Delegated)
- **PRMExtractPractitionerForVerification, PRMExtractInactivePractitionerForVerification** – Practitioner PNC + IsPractitionerDelegated
- **PRMFetchAccountAndPracticeLocations, PRMDrExtractPractForProfStaff** – Used by PDM; both PNC and Delegated
- **PRM_OffCycleWrapper, PRM_FetchPractTermDataHandler** – Off-Cycle and Termination; both display PNC and Delegated

---

## Part 1: Background & Current State

### 1.1 What is Delegated?

**Delegated** = A practice location (HealthcareFacility) has delegated credentialing authority—the group can credential practitioners on behalf of the health plan. `PRM_IsDelegated__c` on HealthcareFacility indicates this.

**PRM_DelegatedOnly__c** (on Practitioner Account) = A rollup indicating the practitioner is affiliated **only** with delegated practice locations (all locations are delegated). Used to:
- Block delegated practitioners from Off-Cycle Credentialing (they must use Practitioner Participation Form)
- Validate practitioner lists in PDM/COI flows (DelegatedValid formula)
- Exclude from CAQH batch (replaced by credentialing status) and other business rules

### 1.2 Current Logic (All = Delegated)

- Practitioner `PRM_DelegatedOnly__c = true` only when **all** of their practice locations have `PRM_IsDelegated__c = true`.
- If **any** location has `PRM_IsDelegated__c = false` → Practitioner `PRM_DelegatedOnly__c = false`.

### 1.3 Target State (Any = Delegated)

- Practitioner `PRM_Delegated__c = true` when **any** practice location has `PRM_IsDelegated__c = true`.
- Practitioner `PRM_Delegated__c = false` when **no** location is delegated.

---

# USER STORY 1: Data Model – Create PRM_Delegated__c Field

**Persona:** Admin  
**Priority:** P0 (Must be done first)

## Story

**As an** Admin,  
**I want to** create a new field `PRM_Delegated__c` on Account (same type as `PRM_DelegatedOnly__c`),  
**So that** we can migrate to the new field and logic without breaking existing functionality until the cutover is complete.

## Acceptance Criteria

### AC1: Create the field

**Given** the Account object exists and has `PRM_DelegatedOnly__c`,  
**When** the Admin creates a new custom field on Account,  
**Then** the field shall have: API Name `PRM_Delegated__c`, Type Checkbox, Label "Delegated", Description indicating "any location delegated" logic, FLS same as PRM_DelegatedOnly__c.

### AC2: Deprecation plan

**Given** all code and OmniStudio assets reference `PRM_Delegated__c`,  
**When** the Admin is ready to deprecate `PRM_DelegatedOnly__c`,  
**Then** remove from page layouts, then delete the field after confirming no external integrations use it.

---

# USER STORY 2: Apex Core Logic – All → Any

**Persona:** Product Owner, Credentialing Operations / Developer (Apex)  
**Priority:** P0  
**Depends on:** User Story 1

## Story (Business-Friendly)

**As a** Credentialing Operations team,  
**I want** the system to treat a practitioner as "delegated" when they have **at least one** delegated practice location (instead of requiring all locations to be delegated),  
**So that** we correctly route credentialing requests, avoid blocking valid practitioners who work at both delegated and non-delegated sites, and align with business rules for delegated groups.

**Why it matters:** Today, a practitioner with 5 locations—4 delegated and 1 non-delegated—is treated as non-delegated. That blocks them from flows where they should be allowed. With the new logic, having any delegated location correctly identifies them as delegated for Off-Cycle blocking, PDM verification, and CAQH batch filtering.

---

## Technical Section (For Developers)

### AC1: delegatedOnlyPractitioner (PRM_RCATTerminationBatchHelper)

**Given** the method initializes each practitioner to `true` and sets `false` when any facility is NOT delegated,  
**When** the developer updates it,  
**Then** initialize with `false`; set `true` when any HealthcareFacility has `PRM_IsDelegated__c == true`. Update all `PRM_DelegatedOnly__c` references to `PRM_Delegated__c`.

### AC2: accToDelInfoCodeMap (PRM_CommonServiceHelper)

**Given** the logic sets `true` only when **all** facilities are delegated,  
**When** the developer updates it,  
**Then** set `true` when **any** facility is in `pracLocToDelInfoCodeMap`. Update all `PRM_DelegatedOnly__c` references to `PRM_Delegated__c`.

### AC3: CAQH batch (PRM_CheckCAQHAccessOnDueAccountsBatch)

**Given** the query uses `PRM_DelegatedOnly__c = false`,  
**When** the developer updates it,  
**Then** remove that condition; add `PRM_CredentialingStatus__c = 'Credentialed'`. Retain `PRM_PNC__c = false`.

### AC4: Unit tests

**Given** test classes exist,  
**When** the developer updates tests,  
**Then** all tests shall pass. Add tests for: (a) one delegated location → delegated = true; (b) one delegated + one non-delegated → delegated = true; (c) no delegated locations → delegated = false.

---

# USER STORY 3: PDM Manual Update (PRM_PDMManualUpdate_English)

**Persona:** Product Owner, PDM Specialist, Developer  
**Priority:** P0  
**Depends on:** User Stories 1–2  
**OmniScript:** PRM_PDMManualUpdate_English  
**PNC overlap:** Yes – PRM_VerifyPractitionerDetails (PNCValid + DelegatedValid)

## Story

**As a** PDM Specialist,  
**I want** practitioner verification in PDM Manual Update to use the new "any location delegated" logic,  
**So that** practitioners with at least one delegated location are correctly validated when adding or removing them in delegated groups.

**Why it matters:** PDM Specialists add/remove practitioners in delegated groups. Wrong delegated logic could block valid practitioners or allow invalid ones.

## Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRMExtractPractitionerForVerification** | DataRaptor | `InputFieldName`: `NPI:Account.PRM_DelegatedOnly__c` → `NPI:Account.PRM_Delegated__c` |
| **PRMExtractInactivePractitionerForVerification** | DataRaptor | Same |
| **PRMFetchAccountAndPracticeLocations** | DataRaptor | `Practitioner:PRM_DelegatedOnly__c` → `Practitioner:PRM_Delegated__c` |
| **PRMDrExtractPractForProfStaff** | DataRaptor | `Practr:PRM_DelegatedOnly__c` → `Practr:PRM_Delegated__c` |
| **PRM_VerifyPractitionerDetails** | Integration Procedure | DelegatedValid formula uses `IsPractitionerDelegated` from practitioner list. DataRaptors supply it; ensure field reference is `PRM_Delegated__c`. No formula change if DataRaptors updated. |

## Acceptance Criteria

**Given** the PDM Specialist is in PRM_PDMManualUpdate_English and adds or removes practitioners,  
**When** PRM_VerifyPractitionerDetails runs (SetDelegatedPNC),  
**Then** the DelegatedValid formula shall evaluate correctly. Practitioners with any delegated location shall be treated as delegated for validation.

---

# USER STORY 4: Provider Change Form (PRM_ProviderChangeForm_English)

**Persona:** Product Owner, PDM Specialist, Developer  
**Priority:** P0  
**Depends on:** User Stories 1–2  
**OmniScript:** PRM_ProviderChangeForm_English  
**PNC overlap:** Yes – PRM_VerifyPractitionerDetails (PNCValid + DelegatedValid)

## Story

**As a** PDM Specialist,  
**I want** practitioner verification in Provider Change Form to use the new "any location delegated" logic,  
**So that** practitioners with at least one delegated location can proceed when adding practitioners or updating COI in delegated groups.

**Why it matters:** Provider Change Form validates practitioners before submission. Incorrect delegated logic breaks validation.

## Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRMExtractPractitionerForVerification** | DataRaptor | Same as US3 – used by PRM_VerifyPractitionerDetailsParent |
| **PRMExtractInactivePractitionerForVerification** | DataRaptor | Same |
| **PRM_VerifyPractitionerDetails** | Integration Procedure | DelegatedValid uses IsPractitionerDelegated; ensure DataRaptors supply from `PRM_Delegated__c` |

## Acceptance Criteria

**Given** the PDM Specialist is in PRM_ProviderChangeForm_English and verifies practitioners,  
**When** PRM_VerifyPractitionerDetailsParent → PRM_VerifyPractitionerDetails runs,  
**Then** DelegatedValid validation shall work as in US3. Practitioners with any delegated location shall be treated as delegated.

---

# USER STORY 5: Off-Cycle Credentialing (PRM_OffCycleCredentialing_English) – PNC + Delegated Combined

**Persona:** Product Owner, Credentialing Specialist, Developer  
**Priority:** P0  
**Depends on:** User Stories 1–2 (Delegated); PNC field migration & pncOnlyPractitioner logic (PNC)  
**OmniScript:** PRM_OffCycleCredentialing_English  
**Implement together:** This flow touches both PNC and Delegated. Do both changes in one pass.

---

## Story

**As a** Credentialing Specialist,  
**I want** Off-Cycle Credentialing to display correct PNC and delegated status when I search for providers,  
**So that** I can route cases correctly, validate practitioner/location alignment, and block delegated practitioners from Off-Cycle (they must use Practitioner Participation Form).

**Why it matters:**
- **PNC:** Facility PNC must come from each practice location (HealthcareFacility), not the vendor Account. Credentialing Specialists need correct PNC to validate practitioner/location alignment and route cases.
- **Delegated:** Off-Cycle is for fully credentialed practitioners. Delegated practitioners use a different path. Practitioners with any delegated location must be blocked.

---

## PNC Changes (Facility PNC Display)

| What the user sees | What changes |
|--------------------|--------------|
| **Provider search results** – PNC for group and each facility | Facility PNC comes from HealthcareFacility.PRM_PNC__c (each practice location). Group PNC may aggregate locations (e.g., any location PNC = group PNC). |
| **PNC consistency validation** (SetErrorsWhenPracTrueandAccFalse, TextBlock14, TextBlock15) | Continues to work; only the data source changes to HealthcareFacility. |

### Technical Section – PNC

| Component | Type | Change |
|-----------|------|--------|
| **PRM_OffCycleProviderSearch** | Apex | Facility PNC: `fac.Account.PRM_PNC__c` → `fac.PRM_PNC__c` (HealthcareFacility). Group PNC: clarify with BA (aggregate from locations or deprecated). |
| **PRMFetchVendorAndHCFWithNPI** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` (if used by Off-Cycle search) |
| **Provider Search DataRaptors** | DataRaptor | Any path `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` |

---

## Delegated Changes (Block Delegated Practitioners)

| What the user sees | What changes |
|--------------------|--------------|
| **Provider search** – delegated practitioner blocked | Practitioners with **any** delegated location are blocked from Off-Cycle. They must submit Practitioner Participation Form. |
| **Error message** | "Practitioner must be fully credentialed, please submit a Practitioner Participation Request" when IsPractitionerDelegated = true and credentialing status ≠ Denied. |
| **Non-delegated practitioner** | Allowed to proceed with Off-Cycle (subject to other validations). |

### Technical Section – Delegated

| Component | Type | Change |
|-----------|------|--------|
| **PRM_OffCycleWrapper** | Apex | `npiRecord.account.PRM_DelegatedOnly__c` → `npiRecord.account.PRM_Delegated__c` (IsPractitionerDelegated mapping) |
| **PRM_FetchOffCycleCredHelper** | Apex | Query Account.PRM_Delegated__c (if used); pass to OffCycleWrapper |
| **NPI / Provider search DataRaptors** | DataRaptor | Any `Account.PRM_DelegatedOnly__c` → `Account.PRM_Delegated__c` in InputFieldName |

---

## Acceptance Criteria

### PNC

**Given** the Credentialing Specialist searches for a provider in PRM_OffCycleCredentialing_English,  
**When** they view search results,  
**Then** the PNC value for each facility shall come from HealthcareFacility.PRM_PNC__c. PNC consistency validation (SetErrorsWhenPracTrueandAccFalse, TextBlock14, TextBlock15) shall continue to work with the new data source.

### Delegated

**Given** the Credentialing Specialist searches for a provider in PRM_OffCycleCredentialing_English,  
**When** the provider has at least one delegated practice location,  
**Then** IsPractitionerDelegated shall be true. SetErrorForDelegatedPractitioner shall block progression.  
**When** the provider has no delegated locations,  
**Then** IsPractitionerDelegated shall be false. The practitioner shall be allowed to proceed.

---

# USER STORY 6: Practitioner Termination (PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English)

**Persona:** Product Owner, Credentialing Specialist, Developer  
**Priority:** P0  
**Depends on:** User Stories 1–2  
**OmniScripts:** PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English  
**PNC overlap:** Yes – Termination data (PracLocPNC + IsPractitionerDelegated)

## Story

**As a** Credentialing Specialist,  
**I want** Practitioner Termination flows to display delegated status using the new "any location delegated" logic,  
**So that** I see the correct delegated status when processing terminations and recred terminations.

**Why it matters:** Termination flows must show correct delegated status for accurate processing.

## Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_FetchPractTermDataHandler** | Apex | `npiData.account.prm_delegatedonly__c` → `npiData.account.PRM_Delegated__c` (IsPractitionerDelegated) |
| **PRMDRExtractHealthCareProviderNpiRecords** | DataRaptor | `InputFieldName`: `Account.PRM_DelegatedOnly__c` → `Account.PRM_Delegated__c` |
| **PRMDRExtractHealthCareProviderNPIWithBothValues, WithLastName, WithFirstName** | DataRaptor | Same |
| **PRMDRExtractNPIfromContextId** | DataRaptor | Same |
| **PRM_GetHealthCareProviderNpiRecords** | IP | Uses DataRaptors; no change if DataRaptors updated |
| **PRM_GetPractitionerTerminationData** | IP | Uses GetHealthProviderNpiWithAccountId; no change if DataRaptor updated |
| **PRM_FetchPracTermDataUtilityTest** | Test | Update `PRM_DelegatedOnly__c` → `PRM_Delegated__c` references |
| **PRM_CrossReferencePracticeLocationTest** | Test | Update `PRM_DelegatedOnly__c` → `PRM_Delegated__c` references |

## Acceptance Criteria

**Given** the Credentialing Specialist is in PRM_PractitionerTerminationForm_English or PRM_PractitionerTerminationRecredForm_English,  
**When** they load practitioner data,  
**Then** IsPractitionerDelegated shall reflect the new "any" logic. Practitioners with any delegated location shall show as delegated.

---

# USER STORY 7: Practitioner Demographics FlexCard + Page Layouts – PNC + Delegated Combined

**Persona:** Product Owner, PDM Specialist, Credentialing Specialist, Admin, Developer  
**Priority:** P1  
**Depends on:** User Stories 1–2 (Delegated); PNC field creation & migration (PNC)  
**Components:** PRMPractitionerDemographics FlexCard, Page Layouts, Reports, List Views  
**Implement together:** Demographics and page layouts touch both PNC and Delegated. Do both changes in one pass.

---

## Story

**As a** PDM Specialist, Credentialing Specialist, or Admin,  
**I want** practitioner demographics to display correct PNC and delegated status, and page layouts, reports, and list views to show the right fields,  
**So that** I see accurate practitioner information when viewing details and can filter/report on PNC and delegated status correctly.

**Why it matters:**
- **Demographics:** The FlexCard is a key view for practitioner details. PNC (rollup) and Delegated must display correctly.
- **Page layouts:** Users edit Practitioner Accounts and HealthcareFacility (practice locations). Layouts must reflect where PNC and Delegated live.
- **Reports & list views:** Filters and columns must use the correct fields for accurate reporting.

---

## Part A: Practitioner Demographics FlexCard (PRMPractitionerDemographics)

### PNC

| What the user sees | What changes |
|--------------------|--------------|
| **Practitioner PNC** in demographics | No change. Practitioner PNC is the rollup on practitioner Account; the HealthcareFacility trigger keeps it in sync. Data source remains Account.PRM_PNC__c. |

**Technical:** PRM_FetchPractitionerDemographics – PractitionerData:PNC from Account.PRM_PNC__c. **No change** – rollup remains on Account.

### Delegated

| What the user sees | What changes |
|--------------------|--------------|
| **Practitioner delegated status** | Displays from new field PRM_Delegated__c. Reflects "any" logic. |

**Technical Section – Delegated**

| Component | Type | Change |
|-----------|------|--------|
| **PRM_FetchPractitionerDemographics** | Integration Procedure | Ensure practitioner delegated comes from Account.PRM_Delegated__c (or DataRaptor output). Update if it references PRM_DelegatedOnly__c. |
| **PRMDRGetAccountFromCaseAccountId** (or equivalent) | DataRaptor | If used for demographics, `PRM_DelegatedOnly__c` → `PRM_Delegated__c` |

---

## Part B: Page Layouts, Reports, List Views

### PNC

| Item | Change |
|------|--------|
| **HealthcareFacility page layouts** | Add PRM_PNC__c (Par Non Cred) to layouts where practice location details are edited. Place in appropriate section (e.g., Participation or Credentialing). |
| **HealthcareFacility list views & reports** | Add PRM_PNC__c for filtering and display where practice location PNC status is needed. |
| **Vendor Account page layout** | Remove PRM_PNC__c from Vendor/Group Account layout (deprecation – after migration complete). |

### Delegated

| Item | Change |
|------|--------|
| **Practitioner Account page layouts** | Replace PRM_DelegatedOnly__c with PRM_Delegated__c. |
| **Reports** | Replace PRM_DelegatedOnly__c in columns, filters, groupings with PRM_Delegated__c. |
| **List views** | Replace PRM_DelegatedOnly__c in filters and display columns with PRM_Delegated__c. |

### Documentation

- **Data dictionary:** Document PNC on HealthcareFacility (practice location); practitioner Account.PRM_PNC__c as rollup (any location PNC = true). Document PRM_Delegated__c as "any location delegated" logic.
- **Release notes:** Summarize both PNC and Delegated changes for Admins and end users.

---

## Acceptance Criteria

### Demographics

**Given** the user views practitioner demographics (PRMPractitionerDemographics FlexCard),  
**When** PNC is displayed, **Then** it shall come from practitioner Account.PRM_PNC__c (rollup).  
**When** delegated status is displayed, **Then** it shall come from PRM_Delegated__c and reflect the new "any" logic.

### Page Layouts, Reports, List Views

**Given** the Admin has completed PNC and Delegated field changes,  
**When** page layouts, reports, and list views are updated,  
**Then** HealthcareFacility layouts shall include PRM_PNC__c; Practitioner Account layouts shall use PRM_Delegated__c (not PRM_DelegatedOnly__c); reports and list views shall use the correct fields for both PNC and Delegated.

---

# USER STORY 8: Apex – Trigger & Batch (No Guided Flow)

**Persona:** Developer (Apex)  
**Priority:** P0  
**Depends on:** User Story 1  
**Note:** These components have no user-facing OmniScript. They update `PRM_DelegatedOnly__c` on Account when InfoCodeAssignment changes or when batch jobs run.

## Story

**As a** Developer,  
**I want to** update the trigger helper and batch classes that write `PRM_DelegatedOnly__c` to use `PRM_Delegated__c`,  
**So that** the practitioner delegated flag is correctly maintained when InfoCodeAssignment records change or when RCAT, future-dated, and activation batches run.

## Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_InfoCodeAssTriggerHelper** | Apex | `PRM_DelegatedOnly__c` → `PRM_Delegated__c` (in setAccountData; trigger fires on PRM_InfoCodeAssignment__c) |
| **PRM_FutureDatedProcessingBatchHandler** | Apex | All `PRM_DelegatedOnly__c` → `PRM_Delegated__c` |
| **PRM_PractitionerActivationBatchHelper** | Apex | All `PRM_DelegatedOnly__c` → `PRM_Delegated__c` |
| **PRMDRCreateCaseCaseManagerAndAccount** | DataRaptor | `OutputFieldName`: `PRM_DelegatedOnly__c` → `PRM_Delegated__c` (writes on Account create) |
| **PRMDRGetPractitionerFromNPI** | DataRaptor | `InputFieldName`: `HealthcareProviderNPI:Account.PRM_DelegatedOnly__c` → `PRM_Delegated__c` |
| **PRMDRExtractExistingAccount** | DataRaptor | `InputFieldName`: `PRM_DelegatedOnly__c` → `PRM_Delegated__c` |
| **PRMDRExtractExistingNPIInfo** | DataRaptor | `InputFieldName`: `Account:PRM_DelegatedOnly__c` → `PRM_Delegated__c` |

## Acceptance Criteria

**Given** PRM_InfoCodeAssignment__c records are inserted, updated, or deleted (Delegated info codes),  
**When** PRM_InfoCodeAssTrigger runs,  
**Then** Account.PRM_Delegated__c shall be updated (via PRM_InfoCodeAssTriggerHelper → PRM_CommonServiceHelper).

**Given** RCAT, future-dated processing, or practitioner activation batches run,  
**When** they read or write practitioner delegated status,  
**Then** they shall use PRM_Delegated__c.

---

## Cross-Cutting: IPs & OmniScripts Validation

**Given** all DataRaptors have been updated,  
**When** the developer searches vlocity_export for `PRM_DelegatedOnly__c` and `DelegatedOnly`,  
**Then** no remaining references shall exist in Integration Procedures or OmniScript JSON. Any formula shall use the path provided by DataRaptor output (e.g., IsPractitionerDelegated).

**PRM_GetInfoCodeAndOtherRecordsForRCATReview:** DelegatedOnlyList is based on practice location IsDelegated, not Account field. No change unless it explicitly references PRM_DelegatedOnly__c.

**Flows and Process Builder:** Search for `PRM_DelegatedOnly__c`; update to `PRM_Delegated__c`.

---

# USER STORY 9: Data Model – Deprecate PRM_DelegatedOnly__c

**Persona:** Admin  
**Priority:** P2 (After all flows validated)  
**Depends on:** User Stories 1–8 complete and tested

## Story

**As an** Admin,  
**I want to** remove the `PRM_DelegatedOnly__c` field from Account after migration is complete,  
**So that** we avoid confusion and maintain a single source of truth.

## Acceptance Criteria

- **Confirm no references:** Global search for PRM_DelegatedOnly__c shall return no results.
- **Remove or hide field:** Remove from page layouts; delete or deprecate the field.
- **External dependencies:** Ensure no integrations or managed packages depend on it.

---

## Quick Reference: Flow → Components (Delegated)

| Flow | OmniScript | Apex | DataRaptors | Integration Procedures |
|------|------------|------|-------------|------------------------|
| PDM Manual Update | PRM_PDMManualUpdate_English | — | PRMExtractPractitionerForVerification, PRMExtractInactivePractitionerForVerification, PRMFetchAccountAndPracticeLocations, PRMDrExtractPractForProfStaff | PRM_VerifyPractitionerDetails |
| Provider Change Form | PRM_ProviderChangeForm_English | — | PRMExtractPractitionerForVerification, PRMExtractInactivePractitionerForVerification | PRM_VerifyPractitionerDetails |
| Off-Cycle Credentialing | PRM_OffCycleCredentialing_English | PRM_OffCycleWrapper, PRM_FetchOffCycleCredHelper | NPI/Provider search DRs | — |
| Practitioner Termination | PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English | PRM_FetchPractTermDataHandler | PRMDRExtractHealthCareProviderNpiRecords, PRMDRExtractHealthCareProviderNPIWith*, PRMDRExtractNPIfromContextId | PRM_GetPractitionerTerminationData, PRM_GetHealthCareProviderNpiRecords |
| Practitioner Demographics | PRMPractitionerDemographics FlexCard | — | PRMDRGetAccountFromCaseAccountId (or equivalent) | PRM_FetchPractitionerDemographics |
| Background Jobs | — | PRM_FutureDatedProcessingBatchHandler, PRM_PractitionerActivationBatchHelper | PRMDRCreateCaseCaseManagerAndAccount, PRMDRGetPractitionerFromNPI, PRMDRExtractExistingAccount, PRMDRExtractExistingNPIInfo | — |

---

## Implementation Order

| Order | User Story | Owner |
|-------|------------|-------|
| 1 | US1: Create PRM_Delegated__c field | Admin |
| 2 | US2: Apex core logic (delegatedOnlyPractitioner, CommonServiceHelper, CAQH) | Developer |
| 3 | US3: PDM Manual Update (PRM_PDMManualUpdate_English) | Developer |
| 4 | US4: Provider Change Form (PRM_ProviderChangeForm_English) | Developer |
| 5 | US5: Off-Cycle Credentialing (PRM_OffCycleCredentialing_English) – PNC + Delegated | Developer |
| 6 | US6: Practitioner Termination (PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English) | Developer |
| 7 | US7: Demographics FlexCard + Page Layouts – PNC + Delegated | Developer + Admin |
| 8 | US8: Apex – Trigger & Batch (No Guided Flow) | Developer |
| 9 | US9: Deprecate PRM_DelegatedOnly__c | Admin |

---

## Testing Checklist

- [ ] Unit tests for delegatedOnlyPractitioner (any logic)
- [ ] Unit tests for PRM_CommonServiceHelper (any logic)
- [ ] PRM_CheckCAQHAccessOnDueAccountsBatch – credentialing status filter
- [ ] DataRaptor export/import validation
- [ ] Off-Cycle Credentialing – delegated practitioner blocked
- [ ] Off-Cycle Credentialing – non-delegated practitioner allowed
- [ ] Practitioner Termination Form – delegated status display
- [ ] Practitioner Termination Recred Form – delegated status display
- [ ] PDM Manual Update – DelegatedValid validation
- [ ] Provider Change Form – DelegatedValid validation
- [ ] Practitioner Demographics FlexCard – delegated display
- [ ] RCAT / Future-dated processing – delegated rollup correct

---

## Rollback Plan

If issues are found post-deployment:
1. Revert Apex changes (logic and field references) to previous version.
2. Revert DataRaptor and IP changes via version control.
3. Keep PRM_Delegated__c field (no need to delete).
4. Re-enable PRM_DelegatedOnly__c on page layouts if removed.
5. Communicate to Credentialing and PDM teams to use previous behavior until fix is deployed.
