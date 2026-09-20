# Close Case Button – PNC and Ancillary Guided Flows – User Stories

**Reference:** Par Participation Form Close Case (CloseCaseGuidedFlow)  
**Goal:** Implement similar Close Case functionality for PNC and Ancillary guided flows, including handling of records in progress (e.g., HealthcarePractitionerFacility, HealthcareFacility in pending state).

---

## 1. Current PAR Close Case Behavior (Reference)

### 1.1 Entry Point
- **OmniScript:** `PRM_CloseCaseGuidedFlow_English` (PRM/CloseCaseGuidedFlow/English)
- **Context:** Launched from Case record (`ContextId` = Case Id)
- **Case Types Supported:** Application Review, PSV, QC Review, QM Review
- **Invalid Case:** Shown when Case is already closed OR Case Type is not in the supported list

### 1.2 Flow Steps
1. **IPFetchCaseDetails** – Fetches Case and Case Manager (IndividualApplication) via `PRM_FetchDetailsParent`
2. **InvalidCase** – Conditional step when Case closed or invalid type
3. **TextBlockCa** – Display case info
4. **CloseCase** – Denial Reason (required), Note (required)
5. **SetRecordsOtherType** (Application Review, PSV, QC Review):
   - Case: Status = Closed, PRM_DenialReason__c = DenialReason
   - IndividualApplication: Status = Pending Closure, PRM_Decision_Date__c = today, PRM_DenialReason__c
   - ContentNote: Case closure note on Case Manager
6. **SetRecordsQMReview** (QM Review only):
   - Case: Status = Closed, PRM_DenialReason__c
   - IndividualApplication: Status = Denied, PRM_Stage__c = Case Complete, PRM_Decision_Date__c, PRM_DenialReason__c
   - ContentNote: "QM Review Case" note
7. **IPReviewUpdateCaseCloseReview** – Calls `PRM_ReviewParCaseRecordsUpdateParent` with RecordsToUpdate
8. **NavigateToCaseManager** – On success, navigate to Case Manager record

### 1.3 Integration Procedure – Records Updated
**PRM_ReviewParCaseRecordsUpdateParent** → **PRM_ReviewParCaseRecordsUpdate**:
- **DRUpdateCaseCaseManager** – Updates Case and IndividualApplication via DataRaptor `PRMUpdateIDCaseCaseMgr`
- **RA_UpdatePendingRecords** – When `IndividualApplication.Status = Denied`, calls `PRM_CaseManagerDenialUtility.offCycleDenial(accountId, caseManagerId)`

### 1.4 Records in Progress – PAR Close Case Handling

When Case Manager is **Denied**, `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` sets `PRM_Pending__c = false` on the following objects (where `PRM_Pending__c = true` and linked to the Case Manager):

| # | Object | Condition | Action |
|---|--------|-----------|--------|
| 1 | **HealthcarePractitionerFacility** | Case Manager's PPLs with PRM_Pending__c = true | PRM_Pending__c = false |
| 2 | **HealthcareFacility** | Practice locations linked to Case Manager PPLs, not in other CM's pending PPLs | PRM_Pending__c = false |
| 3 | **HealthcareFacilityNetwork** | Case Manager's HFN where Practitioner Account in practitionerAccIds | PRM_Pending__c = false |
| 4 | **Address** (Schema.Address) | Location addresses where Location in denial scope | PRM_Pending__c = false |
| 5 | **Location** | Locations of denied HealthcareFacilities | PRM_Pending__c = false |
| 6 | **Identifier** | Vendor/Practitioner identifiers, PRM_Pending__c = true, not excluded | PRM_Pending__c = false |
| 7 | **PRM_HealthcareFacilityNPI__c** | Location NPI History for denied HealthcareFacilities | PRM_Pending__c = false |
| 8 | **HealthcareProvider** | Case Manager's HealthcareProviders | PRM_Pending__c = false |
| 9 | **HealthcareProviderNpi** | Case Manager's NPIs (with conditions) | PRM_Pending__c = false |
| 10 | **HealthcareProviderTaxonomy** | Case Manager's Taxonomies | PRM_Pending__c = false |
| 11 | **Account** | Practitioner Account (PAR only): PRM_Pending__c = false, PRM_CredentialingStatus__c = Denied | When RecordType = PRM_PractitionerParticipationRequest |
| 12 | **PRM_ContactMethod__c** | Alternative contact methods for denied HealthcareFacilities | PRM_Pending__c = false |
| 13 | **PRM_ProviderFeature__c** | Provider features for denied HCF/PPL | PRM_Pending__c = false |
| 14 | **HealthCloudGA__AccountAccountRelation__c** | Account-Account relationships (PAR only) | When RecordType = PRM_PractitionerParticipationRequest |

**Key Logic:** The utility identifies Case Manager's pending HealthcarePractitionerFacilities and HealthcareFacilities, excludes those belonging to other Case Managers, and updates all related pending records to `PRM_Pending__c = false`.

---

## 1.5 PAR Application Review Denial – Practitioner Credentialing Status (BUG 1223476)

### US-PAR-DENIAL-1: Update Practitioner Credentialing Status to Denied When PAR Application Is Denied During Application Review

**As a** Credentialing user who denies a Practitioner Participation (PAR) application during the Application Review process  
**I want** the Practitioner's Credentialing Status to be updated to "Denied"  
**So that** the Practitioner record accurately reflects the denial and is consistent with the Case Manager status.

**Defect Reference:** BUG 1223476

**Problem Statement:**  
For the Practitioner Participation guided flow, when a user denies the PAR application during the App Review process (Verify Taxonomy screen), the Case Manager status correctly displays "Denied." However, the Practitioner's Credentialing Status remains "Credentialing In-progress" instead of being updated to "Denied."

**Environment:** `https://ibx--uat.sandbox.lightning.force.com/`

**Acceptance Criteria:**
- [ ] When a user denies a PAR application during Application Review (Verify Taxonomy screen) by selecting "Unable to proceed," entering Denial Reason and Specialty note, and clicking Next, the Case Manager status is set to Denied (existing behavior)
- [ ] When the same denial occurs, the Practitioner Account's `PRM_CredentialingStatus__c` is updated to "Denied"
- [ ] Navigating to the Practitioner details after denial shows Credentialing Status as "Denied" (not "Credentialing In-progress")

**Repro Steps:**
1. Login as Cred User. Navigate to Practitioner participation form.
2. Submit a PAR form with relevant details.
3. In Application Review, on the Verify Taxonomy screen, select "Unable to proceed," enter Denial Reason, Specialty note, and click Next.
4. Notice the Case Manager status is set to Denied.
5. Navigate to the Practitioner details.
6. Notice the Credentialing Status is still displaying as "Credentialing In-progress" *(defect)* — **Expected:** Credentialing Status should display as "Denied"

**Implementation Notes:**
- The denial path uses `PRM_CredApplicationReviewOSTxnyRole_English` → `SetRecordstoUpdateSpecialtyVerify` → `IPReviewSpecialtyStatus` → `PRM_ReviewParCaseRecordsUpdateParent`
- `PRM_ReviewParCaseRecordsUpdate` includes `RA_UpdatePendingRecords`, which calls `PRM_CaseManagerDenialUtility.offCycleDenial(accountId, caseManagerId)` when `IndividualApplication.Status == "Denied"`
- `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` updates `Account.PRM_CredentialingStatus__c = 'Denied'` for Practitioner Accounts when Case Manager RecordType = `PRM_PractitionerParticipationRequest`
- Investigate why the Practitioner Account update is not occurring: verify `RA_UpdatePendingRecords` execution (e.g., `DRTransformCaseManagerId` output structure, `accountId`/`caseManagerId` mapping), and ensure `offCycleDenial` is invoked with correct parameters for the Verify Taxonomy denial path

---

## 2. PNC Close Case – User Stories

### US-PNC-1: Extend Close Case OmniScript to Support PNC Case Types

**As a** Case Manager user working on a PNC case  
**I want** a Close Case button available when viewing the PNC Case Manager (IndividualApplication)  
**So that** I can close the case with denial reason and notes, similar to PAR.

**Acceptance Criteria:**
- [ ] Close Case button/action is visible on PNC Case Manager record page (or Case page when Case Type indicates PNC)
- [ ] Close Case OmniScript is launched with Case as context (ContextId = Case Id)
- [ ] Case Types for PNC that must be supported: Identify from existing PNC flows (e.g., "PDA Review and Update", "Network Management QC", "PNC PDA", etc.)
- [ ] InvalidCase step does NOT show for valid PNC Case Types
- [ ] Denial Reason and Note fields are required before Confirm

**Implementation Notes:**
- Update `PRM_CloseCaseGuidedFlow_English_Element_InvalidCase.json` – add PNC Case Types to the "valid" list (inverse of InvalidCase show condition)
- Add new Set Values element(s) for PNC Case Types – e.g., `SetRecordsPNC` – or extend `SetRecordsOtherType` show condition to include PNC types
- Determine PNC-specific IndividualApplication status: "Pending Closure" vs "Denied" based on business rules
- Ensure FlexCard/Page Layout/App Builder includes Close Case action for PNC Case Manager or Case

**Dependencies:** Identify exact PNC Case Type picklist values from Case object and PNC OmniScripts.

---

### US-PNC-2: Create/Extend Integration Procedure for PNC Case Closure

**As a** system processing PNC case closure  
**I want** the same record update flow as PAR (Case, IndividualApplication, ContentNote)  
**So that** Case and Case Manager are correctly updated when the user confirms closure.

**Acceptance Criteria:**
- [ ] Case record: Status = Closed, PRM_DenialReason__c = user-selected value
- [ ] IndividualApplication (Case Manager): Status = Pending Closure or Denied (per business rule), PRM_Decision_Date__c, PRM_DenialReason__c
- [ ] ContentNote created on Case Manager with Case Type + " Case Closure" title
- [ ] Integration Procedure receives RecordsToUpdate from OmniScript and persists via DataRaptor

**Implementation Notes:**
- Option A: Extend `PRM_ReviewParCaseRecordsUpdate` to handle PNC Case Type – add conditional logic or new branch
- Option B: Create new IP `PRM_ReviewPNCCaseRecordsUpdate` and invoke from Close Case OmniScript when Case Type is PNC
- DataRaptor `PRMUpdateIDCaseCaseMgr` (or equivalent) must support IndividualApplication Record Type = PRM_PNC
- Verify PRMUpdateIDCaseCaseMgr bundle handles PRM_PNC record type; if not, create PRMUpdatePNCCaseCaseMgr or extend existing

---

### US-PNC-3: Handle PNC Records in Progress on Case Closure

**As a** system processing PNC case closure when Case Manager is Denied  
**I want** all pending records linked to the Case Manager to be updated (PRM_Pending__c = false)  
**So that** in-progress HealthcareFacility, HealthcarePractitionerFacility, and related records are no longer marked pending.

**Acceptance Criteria:**
- [ ] When IndividualApplication.Status = Denied, invoke pending records update logic
- [ ] All objects in the table below are updated where applicable for PNC Case Manager (same rules as PAR)
- [ ] No duplicate updates; exclude records that belong to other Case Managers
- [ ] Practitioner Account update: For PNC, Vendor Account and Practitioner Account both in scope (per PRM_PNCPDABatchHelper)

---

#### PNC Creation IPs – Records Created (Source of Truth)

The following Integration Procedures and Apex create/update records for PNC flows. All records with `PRM_Pending__c = true` linked to the Case Manager must be set to `PRM_Pending__c = false` on denial.

| IP / Apex | Records Created/Updated | PRM_Pending__c |
|-----------|-------------------------|----------------|
| **PRM_PractitionerScreenRecordCreation** | Case, IndividualApplication, Account, Identifier, HealthcareProviderNpi, PersonEducation, HealthcareProviderTaxonomy, BusinessLicense | Yes (where applicable) |
| **PRM_PNCRecordsUpdate** | Case, IndividualApplication, BusinessLicense, PersonEducation, HealthcareFacilityNetwork (via IPReviewHealthCareFacilityNetwork) | Yes |
| **PRM_PNCPDAReviewUpdate** → **CallPNCPDABatch** (PRM_PNCPDABatch / PRM_PNCPDAService) | HealthcareFacilityNetwork, PRM_InfoCodeAssignment__c, Identifier, HealthcareProviderNpi, HealthcareProvider, HealthcarePractitionerFacility, Address, Location, HealthcareProviderTaxonomy, Account (Practitioner), Account (Vendor), HealthcareFacility, PRM_ProviderFeature__c | Yes |
| **PRM_PNCPDAReviewUpdate** → **PRM_PNCPracTxnyNetworkBatch** (finish) | HealthcareFacilityNetwork (practitioner taxonomy networks) | Yes |
| **PRM_PNCPDAReviewUpdate** → **PRMDRCreateIdentiferAndDocument** | Identifier, ContentDocumentLink | Identifier has PRM_Pending__c |
| **PRM_InitialCredPDAReviewUpdateSubIPInsert** | HealthcareFacilityNetwork, PRM_InfoCodeAssignment__c, HealthcareFacility | Yes |
| **PRM_ReviewHealthcareFacilityNetwork** | HealthcareFacilityNetwork, Location taxonomy records | Yes |

---

#### Objects to Update on PNC Case Closure (Denial) – Same Rules as PAR

Apply the same logic as `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial`: for each object, query records where `PRM_Pending__c = true` AND linked to the Case Manager (via PRM_CaseManager__c or relationship), exclude records belonging to other Case Managers, then set `PRM_Pending__c = false`.

| # | Object | PNC Creation Source | Condition | Action |
|---|--------|---------------------|-----------|--------|
| 1 | **HealthcarePractitionerFacility** | PRM_PNCPDAService (updateHFRelatedData) | Case Manager's PPLs; RecordType PRM_PractitionerLocationAffiliation (HealthcareFacility) | PRM_Pending__c = false |
| 2 | **HealthcareFacility** | PRM_PNCPDAService, InitialCredPDAReviewUpdateSubIPInsert | Practice locations linked to Case Manager PPLs; not in other CM's pending PPLs | PRM_Pending__c = false |
| 3 | **HealthcareFacilityNetwork** | PRM_PNCPDABatch, PRM_PNCPracTxnyNetworkBatch, IPReviewHealthCareFacilityNetwork, InitialCredPDAReviewHFN | Case Manager's HFN; Practitioner Account in practitionerAccIds (for PAR); PNC uses same model | PRM_Pending__c = false |
| 4 | **Address** (Schema.Address) | PRM_PNCPDAService (getAddressData) | Location addresses where Location in denial scope | PRM_Pending__c = false |
| 5 | **Location** | PRM_PNCPDAService (getLocationData) | Locations of denied HealthcareFacilities | PRM_Pending__c = false |
| 6 | **Identifier** | PRM_PractitionerScreenRecordCreation, PRM_PNCPDAService, PRMDRCreateIdentiferAndDocument | Vendor/Practitioner identifiers; PRM_Pending__c = true; not in excludedVendors | PRM_Pending__c = false |
| 7 | **PRM_HealthcareFacilityNPI__c** | (PAR object; verify if PNC creates) | Location NPI History for denied HealthcareFacilities | PRM_Pending__c = false |
| 8 | **HealthcareProvider** | PRM_PractitionerScreenRecordCreation, PRM_PNCPDAService | Case Manager's HealthcareProviders | PRM_Pending__c = false |
| 9 | **HealthcareProviderNpi** | PRM_PractitionerScreenRecordCreation, PRM_PNCPDAService | Case Manager's NPIs (with conditions) | PRM_Pending__c = false |
| 10 | **HealthcareProviderTaxonomy** | PRM_PractitionerScreenRecordCreation, PRM_PNCPDAService | Case Manager's Taxonomies | PRM_Pending__c = false |
| 11 | **Account** | PRM_PNCPDAService (Practitioner + Vendor) | **PNC:** Both Practitioner Account and Vendor Account updated; PRM_Pending__c = false; PRM_CredentialingStatus__c = Denied for Practitioner (confirm) | PRM_Pending__c = false |
| 12 | **PRM_ContactMethod__c** | (PAR object; verify if PNC creates) | Alternative contact methods for denied HealthcareFacilities | PRM_Pending__c = false |
| 13 | **PRM_ProviderFeature__c** | PRM_PNCPDAService | Provider features for denied HCF/PPL | PRM_Pending__c = false |
| 14 | **HealthCloudGA__AccountAccountRelation__c** | (PAR only) | Account-Account relationships | PRM_Pending__c = false when RecordType = PRM_PractitionerParticipationRequest |
| 15 | **PRM_InfoCodeAssignment__c** | PRM_PNCPDABatch, InitialCredPDAReviewUpdateSubIPInsert | Info codes at Practice Location and Practitioner level; PRM_CaseManager__c, PRM_HealthcareFacility__c or PRM_Account__c | PRM_Pending__c = false *(verify field exists)* |
| 16 | **BusinessLicense** | PRM_PractitionerScreenRecordCreation, PRM_PNCRecordsUpdate | License records linked to Case Manager | PRM_Pending__c = false *(verify field exists)* |
| 17 | **PersonEducation** | PRM_PractitionerScreenRecordCreation, PRM_PNCRecordsUpdate | Education records linked to Case Manager | PRM_Pending__c = false *(verify field exists)* |

**Note:** PRM_InfoCodeAssignment__c, BusinessLicense, and PersonEducation may or may not have PRM_Pending__c. Verify in org; if present and linked to Case Manager, apply same rule.

---

**Implementation Notes:**
- Extend `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` to support IndividualApplication Record Type = PRM_PNC
- Add handling for **PRM_InfoCodeAssignment__c** (PRM_CaseManager__c, PRM_HealthcareFacility__c, PRM_Account__c) – query where PRM_Pending__c = true and PRM_CaseManager__c = caseManagerId
- PNC Case Manager links to Vendor Account + HealthcareFacility (practice locations); PRM_PNCPDABatchHelper already updates both Practitioner and Vendor Account
- Ensure HealthcareFacility and HealthcarePractitionerFacility queries include PNC Case Manager's relationships (HealthCarePractitionerFacilities__r, HealthCarefacilities__r)
- Add unit tests for PNC denial scenario covering all 17 objects

---

### US-PNC-4: Add Close Case Button to PNC Case Manager UI

**As a** Case Manager user  
**I want** to see a "Close Case" button when viewing a PNC Case Manager record  
**So that** I can initiate case closure without navigating elsewhere.

**Acceptance Criteria:**
- [ ] Close Case button is present on PNC IndividualApplication record page (or associated Case page)
- [ ] Button is visible only when Case is not already closed
- [ ] Clicking the button launches CloseCaseGuidedFlow with Case Id as context
- [ ] Placement matches PAR (e.g., in header actions or FlexCard)

**Implementation Notes:**
- Identify where PAR Close Case button is configured (FlexCard, App Builder, Lightning Page)
- Replicate or extend that configuration for PNC Case Manager / PNC Case
- Use Record Type or Case Type to control visibility

---

## 3. Ancillary Close Case – User Stories

### US-ANC-1: Extend Close Case OmniScript to Support Ancillary Case Types

**As a** Case Manager user working on an Ancillary case  
**I want** a Close Case button available when viewing the Ancillary Case Manager  
**So that** I can close the case with denial reason and notes, similar to PAR.

**Acceptance Criteria:**
- [ ] Close Case button/action is visible on Ancillary Case Manager record page (or Case page when Case Type indicates Ancillary)
- [ ] Close Case OmniScript is launched with Case as context (ContextId = Case Id)
- [ ] Case Types for Ancillary that must be supported: Identify from existing Ancillary flows (e.g., "Ancillary PSV", "Ancillary Reassessment", "Ancillary PDA", etc.)
- [ ] InvalidCase step does NOT show for valid Ancillary Case Types
- [ ] Denial Reason and Note fields are required before Confirm

**Implementation Notes:**
- Update InvalidCase show condition to include Ancillary Case Types as valid
- Add Set Values element for Ancillary – e.g., `SetRecordsAncillary` – with Case and IndividualApplication updates
- IndividualApplication Record Types: PRM_AncillaryAssessment, PRM_AncillaryReAssessment
- Determine Ancillary-specific IndividualApplication status on closure

**Dependencies:** Identify exact Ancillary Case Type picklist values.

---

### US-ANC-2: Create/Extend Integration Procedure for Ancillary Case Closure

**As a** system processing Ancillary case closure  
**I want** the same record update flow as PAR (Case, IndividualApplication, ContentNote)  
**So that** Case and Case Manager are correctly updated when the user confirms closure.

**Acceptance Criteria:**
- [ ] Case record: Status = Closed, PRM_DenialReason__c
- [ ] IndividualApplication (Case Manager): Status, PRM_Decision_Date__c, PRM_DenialReason__c
- [ ] ContentNote created on Case Manager
- [ ] DataRaptor supports Ancillary IndividualApplication record types

**Implementation Notes:**
- Option A: Extend PRM_ReviewParCaseRecordsUpdate for Ancillary Case Type
- Option B: Create PRM_ReviewAncillaryCaseRecordsUpdate and invoke when Case Type is Ancillary
- Verify DataRaptor PRMUpdateIDCaseCaseMgr or create Ancillary-specific bundle

---

### US-ANC-3: Handle Ancillary Records in Progress on Case Closure

**As a** system processing Ancillary case closure when Case Manager is Denied  
**I want** all pending records linked to the Ancillary Case Manager to be updated (PRM_Pending__c = false)  
**So that** in-progress HealthcareFacility, HealthcarePractitionerFacility, Business License, and Ancillary-specific records are no longer marked pending.

**Acceptance Criteria:**
- [ ] When IndividualApplication.Status = Denied, invoke pending records update logic
- [ ] All standard objects (same as PAR) are updated where applicable
- [ ] Ancillary-specific objects are handled per table below

**Objects to Update – Standard (same as PAR):**

| Object | Ancillary Notes |
|--------|-----------------|
| HealthcarePractitionerFacility | Ancillary Case Manager links to HealthcareFacility (practice locations) via HealthCarePractitionerFacilities__r |
| HealthcareFacility | Ancillary facilities (PRM_Ancillary__c = true); practice locations created by Ancillary flows |
| HealthcareFacilityNetwork | If Ancillary Case Manager has HFN |
| Address | Location addresses |
| Location | Locations of denied HealthcareFacilities |
| Identifier | Vendor/Practitioner identifiers |
| PRM_HealthcareFacilityNPI__c | Location NPI History |
| HealthcareProvider | Case Manager's HealthcareProviders |
| HealthcareProviderNpi | Case Manager's NPIs |
| HealthcareProviderTaxonomy | Case Manager's Taxonomies |
| Account | Vendor Account; Practitioner Account if applicable |
| PRM_ContactMethod__c | Alternative contact methods |
| PRM_ProviderFeature__c | Provider features |
| HealthCloudGA__AccountAccountRelation__c | If Ancillary uses AAR |

**Ancillary-Specific Objects:**

| Object | Condition | Action |
|--------|-----------|--------|
| **PRM_AncillaryAssessment__c** | Linked to Case Manager (PRM_CaseManager__c or similar); PRM_Pending__c = true | PRM_Pending__c = false |
| **PRM_AncillaryStaff__c** | Child of PRM_AncillaryAssessment__c in denial scope; PRM_Pending__c = true | PRM_Pending__c = false |
| **PRM_BusinessLicense__c** (or equivalent) | Business Licenses linked to denied HealthcareFacilities; PRM_Pending__c = true | PRM_Pending__c = false |
| **Schema.Address** (PRM_Address__c or custom) | Addresses for Ancillary locations | PRM_Pending__c = false |

**Implementation Notes:**
- Extend `PRM_CaseManagerDenialUtility` to support Record Types: PRM_AncillaryAssessment, PRM_AncillaryReAssessment
- **Alternative:** Create `PRM_AncillaryCaseManagerDenialUtility` if logic differs significantly (e.g., AncillaryAssessment hierarchy)
- Query IndividualApplication with HealthCarePractitionerFacilities__r, HealthCarefacilities__r – Ancillary uses HealthcareFacility (facility/location) model
- Add logic to update PRM_AncillaryAssessment__c and PRM_AncillaryStaff__c where PRM_Pending__c = true and linked to denied Case Manager
- Verify Business License object and field names; update if PRM_Pending__c exists
- Add unit tests for Ancillary denial scenario

---

### US-ANC-4: Add Close Case Button to Ancillary Case Manager UI

**As a** Case Manager user  
**I want** to see a "Close Case" button when viewing an Ancillary Case Manager record  
**So that** I can initiate case closure without navigating elsewhere.

**Acceptance Criteria:**
- [ ] Close Case button is present on Ancillary IndividualApplication record page (or associated Case page)
- [ ] Button is visible only when Case is not already closed
- [ ] Clicking the button launches CloseCaseGuidedFlow with Case Id as context
- [ ] Placement matches PAR and PNC

**Implementation Notes:**
- Replicate PAR Close Case button configuration for Ancillary Case Manager / Ancillary Case
- Use Record Type (PRM_AncillaryAssessment, PRM_AncillaryReAssessment) or Case Type to control visibility

---

## 4. Detailed Object Handling – Records in Progress

### 4.1 HealthcarePractitionerFacility (Practitioner Practice Location)

| Attribute | PAR | PNC | Ancillary |
|-----------|-----|-----|-----------|
| Record Type | PRM_PractitionerLocationAffiliation | PRM_PractitionerLocationAffiliation or PRM_PractitionerPracticeAffiliation | PRM_PractitionerLocationAffiliation |
| Link | Practitioner → HealthcareFacility | Practitioner → HealthcareFacility or Account | Practitioner → HealthcareFacility |
| PRM_CaseManager__c | Set on PPL | Set on PPL | Set on PPL |
| Update on Denial | PRM_Pending__c = false | Same | Same |
| Query | Case Manager's HealthCarePractitionerFacilities__r | Same | Same |

**Implementation:** Use existing `PRM_CaseManagerDenialUtility` logic; ensure PNC/Ancillary Case Manager is fetched with `HealthCarePractitionerFacilities__r` and `HealthCarefacilities__r`.

---

### 4.2 HealthcareFacility (Practice Location)

| Attribute | PAR | PNC | Ancillary |
|-----------|-----|-----|-----------|
| PRM_Pending__c | Updated when in Case Manager scope | Same | Same; PRM_Ancillary__c = true for Ancillary facilities |
| PRM_CaseManager__c | Links to IndividualApplication | Same | Same |
| Update on Denial | PRM_Pending__c = false | Same | Same |
| Exclusion | Do not update if in otherCMPendingHCFacilityIds | Same | Same |

**Implementation:** Existing logic applies; Ancillary facilities have PRM_Ancillary__c = true.

---

### 4.3 Location and Address

| Object | Update Logic |
|--------|--------------|
| Location | WHERE Id IN locationIds (from denied HealthcareFacilities), PRM_Pending__c = true → PRM_Pending__c = false |
| Address | Child of Location; PRM_Pending__c = true → PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary.

---

### 4.4 Identifier

| Attribute | Update Logic |
|-----------|--------------|
| Scope | ParentRecordId IN (vendorIds OR practitionerAccIds), NOT IN excludedVendors |
| Condition | PRM_IsErrorRecord__c = false, PRM_Pending__c = true |
| Action | PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary; vendorIds/practitionerAccIds derived from Case Manager context.

---

### 4.5 PRM_HealthcareFacilityNPI__c (Location NPI History)

| Attribute | Update Logic |
|-----------|--------------|
| Scope | PRM_HealthcareFacility__c IN hcFacilityIds (denied HealthcareFacilities) |
| Condition | PRM_IsErrorRecord__c = false, PRM_Pending__c = true |
| Action | PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary.

---

### 4.6 PRM_ContactMethod__c (Alternative Contact Methods)

| Attribute | Update Logic |
|-----------|--------------|
| Scope | PRM_HealthcareFacility__c IN hcFacilityIds |
| Condition | PRM_IsErrorRecord__c = false, PRM_Pending__c = true |
| Action | PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary.

---

### 4.7 PRM_ProviderFeature__c

| Attribute | Update Logic |
|-----------|--------------|
| Scope | PRM_HealthcareFacility__c IN hcFacilityIds OR PRM_HealthcarePractitionerFacility__c IN hcPractitionerFacilityIds |
| Condition | PRM_IsErrorRecord__c = false, PRM_Pending__c = true |
| Action | PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary.

---

### 4.8 HealthcareProvider, HealthcareProviderNpi, HealthcareProviderTaxonomy

| Object | Update Logic |
|--------|--------------|
| HealthcareProvider | Case Manager's HealthcareProviders__r → PRM_Pending__c = false |
| HealthcareProviderNpi | Case Manager's HealthcareProviderNPIs__r (with conditions) → PRM_Pending__c = false |
| HealthcareProviderTaxonomy | Case Manager's HealthcareProviderTaxonomies__r → PRM_Pending__c = false |

**Implementation:** Same for PAR, PNC, Ancillary; ensure IndividualApplication query includes these subqueries.

---

### 4.9 Account

| Record Type | Update Logic |
|-------------|--------------|
| PRM_PractitionerParticipationRequest (PAR) | Practitioner Account: PRM_Pending__c = false, PRM_CredentialingStatus__c = Denied |
| PRM_PNC | Confirm with business: Vendor Account and/or Practitioner Account |
| PRM_AncillaryAssessment / PRM_AncillaryReAssessment | Vendor Account: PRM_Pending__c = false; Practitioner if applicable |

**Implementation:** Extend `PRM_CaseManagerDenialUtility` with Record Type branches for PNC and Ancillary.

---

### 4.10 HealthCloudGA__AccountAccountRelation__c

| Record Type | Update Logic |
|-------------|--------------|
| PRM_PractitionerParticipationRequest | Case Manager's AccountToAccountRelationships__r → PRM_Pending__c = false |
| PRM_PNC | If PNC uses AAR, add same logic |
| PRM_AncillaryAssessment / PRM_AncillaryReAssessment | If Ancillary uses AAR, add same logic |

**Implementation:** Add Record Type check; query AccountToAccountRelationships__r for PNC/Ancillary when applicable.

---

### 4.11 Ancillary-Specific: PRM_AncillaryAssessment__c and PRM_AncillaryStaff__c

| Object | Update Logic |
|--------|--------------|
| PRM_AncillaryAssessment__c | WHERE PRM_CaseManager__c = caseManagerId (or linked via IndividualApplication), PRM_Pending__c = true → PRM_Pending__c = false |
| PRM_AncillaryStaff__c | WHERE PRM_AncillaryAssessment__c IN deniedAssessmentIds, PRM_Pending__c = true → PRM_Pending__c = false |

**Implementation:** New logic in denial utility or new Ancillary-specific utility; verify field names (PRM_CaseManager__c, PRM_Pending__c) on PRM_AncillaryAssessment__c and PRM_AncillaryStaff__c.

---

## 5. Implementation Order

| Phase | Task | User Stories |
|-------|------|--------------|
| 1 | Identify PNC and Ancillary Case Types from Case picklist and flows | US-PNC-1, US-ANC-1 |
| 2 | Extend Close Case OmniScript – InvalidCase, SetRecords for PNC/Ancillary | US-PNC-1, US-ANC-1 |
| 3 | Extend or create Integration Procedure for PNC/Ancillary closure | US-PNC-2, US-ANC-2 |
| 4 | Extend PRM_CaseManagerDenialUtility for PNC/Ancillary record types | US-PNC-3, US-ANC-3 |
| 5 | Add Ancillary-specific object handling (PRM_AncillaryAssessment__c, etc.) | US-ANC-3 |
| 6 | Add Close Case button to PNC and Ancillary Case Manager UI | US-PNC-4, US-ANC-4 |
| 7 | Unit tests and integration tests | All |

---

## 6. Files to Create/Modify

| File | Action |
|------|--------|
| `PRM_CloseCaseGuidedFlow_English_Element_InvalidCase.json` | Modify – add PNC/Ancillary Case Types |
| `PRM_CloseCaseGuidedFlow_English_Element_SetRecordsOtherType.json` | Modify – or create SetRecordsPNC, SetRecordsAncillary |
| `PRM_ReviewParCaseRecordsUpdate` or new `PRM_ReviewPNCCaseRecordsUpdate`, `PRM_ReviewAncillaryCaseRecordsUpdate` | Create/Modify |
| `PRM_CaseManagerDenialUtility.cls` | Modify – add PNC/Ancillary Record Type support |
| `PRM_CaseManagerDenialUtilityTest.cls` | Modify – add PNC/Ancillary test methods |
| FlexCard / Lightning Page for PNC and Ancillary Case Manager | Modify – add Close Case action |
| DataRaptor `PRMUpdateIDCaseCaseMgr` or equivalent | Verify/Modify – support PNC/Ancillary record types |

---

*End of User Stories*
