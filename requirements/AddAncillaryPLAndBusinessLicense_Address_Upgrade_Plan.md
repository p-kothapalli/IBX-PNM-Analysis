# Add Practice Location / Business License – Address Edit & Requirements

**Reference:** Ancillary Reassessment PSV OmniScript (Primary + Mailing address edit flow), Ancillary Provider Form (Primary + Mailing + Billing)  
**Target:** PRM_AddAncillaryPLAndBusinessLicense_English OmniScript  
**Goal:** Enable credentialing specialists to **edit Primary, Mailing, and Billing addresses** for the **primary practice location**—mirroring Ancillary Reassessment PSV—while adding business licenses. NPDB request remains as implemented.

---

## 1. Executive Summary

**Business decision:** No adding multiple locations. The flow operates on the **primary practice location only**.

The Add Practice Location / Business License flow will be simplified:

1. **Primary location is defaulted** – The Case Manager's primary practice location is auto-loaded. No type-ahead or location selection.
2. **Address fields** – Primary (Physical) is always editable. Mailing and Billing use the **same question pattern as Ancillary Reassessment PSV**: "Change of Mailing Address?" and "Change of Billing Address?" (Yes/No)—when Yes, show the editable block.
3. **Review step with Proceed To** – Business wants to **see the updated address** in the PSV guided flow and **route without waiting for NPDB**. A Review step displays Primary, Mailing, Billing addresses; a **Proceed To** radio (same as Ancillary Reassessment PSV last step) routes to: Pending NPDB Verification, HACAC, HACAC - Pended, or Provider Outreach Needed. NPDB step is shown only when Proceed To = Pending NPDB Verification.
4. **"Route Case" button on Case Manager** – For post-PSV routing without NPDB report. Button opens modal/OmniScript with Proceed To + Note (required); routes case per selection, same logic as PSV last step.
5. Business license add functionality remains unchanged (for the primary location).
6. Address updates use the same DataRaptors as Ancillary Reassessment: `PRMLoadAddressPrimary`, `PRMLoadAddressAncesMailing`, and (new) `PRMLoadAddressAncesBilling`.

---

## 2. User Stories

### US-ADDPL-1: Default Primary Practice Location

**As a** Credentialing Specialist  
**I want** the primary practice location to be auto-loaded for the Case Manager  
**So that** I don't need to search or select a location—I can immediately edit addresses and add licenses.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **No type-ahead** – Remove PracLoc type-ahead selection | Type-ahead removed |
| AC2 | **No multi-location** – Remove NewPL repeatable block; single location only | NewPL removed or repeatLimit=1, no add-more |
| AC3 | FetchDetails (or equivalent) loads the Case Manager's **primary** practice location | Primary PL auto-populated |
| AC4 | PLId, PLName, LocationId available from defaulted primary | Used for address load and BL creation |
| AC5 | If no primary location exists, show NoLocationAvailable error | Preserved |

---

### US-ADDPL-2: Edit Primary (Physical) Address

**As a** Credentialing Specialist  
**I want** to edit the Primary (Physical) address for the primary practice location  
**So that** address corrections are captured before adding business licenses.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **PrimaryAddress** block – always visible, **editable** – AddLine1, AddLine2, City, State, Zip, Zip4, Phone, Phone Extension, Fax, Website | Pre-populated from primary PL; user can edit |
| AC2 | No "Change Primary Address?" gate – fields are directly editable | Simpler UX than Ancillary Reassessment |
| AC3 | Address updates apply via PRMLoadAddressPrimary DataRaptor | IP calls PRMLoadAddressPrimary on submit |
| AC4 | Effective date for address change (optional) | CredContactInfo:ChangeAddressEffectiveDate or today |

---

### US-ADDPL-3: Edit Mailing Address

**As a** Credentialing Specialist  
**I want** to optionally edit the Mailing/Correspondence address for the primary practice location  
**So that** mailing address changes are captured.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **MailingAddressChange** radio – "Change of Mailing Address?" (Yes/No) | Same pattern as Ancillary Reassessment PSV |
| AC2 | When Yes: **MailingAddressNew** block (editable) – AddLine1, AddLine2, City, State, Zip, Zip4 | Pre-populated from existing or Same as Primary |
| AC3 | **SameAsPrimary** Set Values – copies Primary address to Mailing when selected | Same as Ancillary Reassessment |
| AC4 | **ClearMailing** – clears Mailing address fields | Same as Ancillary Reassessment |
| AC5 | Address updates apply via PRMLoadAddressAncesMailing DataRaptor | IP calls when MailingAddressChange = Yes |

**UI Spec – MailingAddressChange (Radio):**
```
* Change of Mailing Address?
  ○ Yes
  ○ No
```

**Reference:** Ancillary Reassessment PSV – `MailingAddressChange`, `MailingAddressNew`, `SameAsPrimary`, `ClearMailing`.

---

### US-ADDPL-4: Edit Billing Address

**As a** Credentialing Specialist  
**I want** to optionally edit the Billing address for the primary practice location  
**So that** billing address changes are captured.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **BillingAddressChange** radio – "Change of Billing Address?" (Yes/No) | Same pattern as Ancillary Reassessment PSV |
| AC2 | When Yes: **BillingAddressNew** block (editable) – AddLine1, AddLine2, City, State, Zip, Zip4 | Pre-populated from existing or Same as Physical |
| AC3 | **BillingSameAsPhysical** – when Yes, Billing = Primary (optional shortcut) | Same as Ancillary Provider Form |
| AC4 | Address updates apply via PRMLoadAddressAncesBilling DataRaptor | IP calls when BillingAddressChange = Yes |

**UI Spec – BillingAddressChange (Radio):**
```
* Change of Billing Address?
  ○ Yes
  ○ No
```

**Reference:** Ancillary Reassessment PSV – same question pattern for Mailing; Billing follows same UX.

---

### US-ADDPL-5: Add Business Licenses to Primary Location

**As a** Credentialing Specialist  
**I want** to add one or more Business Licenses to the primary practice location  
**So that** licenses are associated with the correct office.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **AddBLQuestion** – "Would you like to add License information?" (Yes/No) | **Preserved** – existing behavior |
| AC2 | When Yes: **NewLicense** block (repeatable, max 4) – License Type, License State, License Number, Effective Date, Expiration Date, Status, Verified On | **Preserved** |
| AC3 | Each license linked to `PRM_HealthcareFacility__c` (primary PL) | BLPracticeLocationId = defaulted PL |
| AC4 | Duplicate check: same License State + License Number + License Class + Practice Location = error | Per Ancillary_PSV_Business_Licenses_User_Story |
| AC5 | Date validations: Effective ≤ Expiration; Effective ≥ PL effective date | Preserved |

---

### US-ADDPL-6: Request NPDB for Primary Location

**As a** Credentialing Specialist  
**I want** to request NPDB for the primary practice location  
**So that** NPDB verification can be completed.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **NPDBRequest** step – request NPDB for primary PL | **Preserved** – shown only when ProceedTo = Pending NPDB Verification |
| AC2 | **NPDBReportRequest** – report request flow | **Preserved** – conditional on ProceedTo |
| AC3 | NPDBReqExistsErrorMsg when duplicate request | Preserved |

---

### US-ADDPL-6a: Review Updated Address & Route Without NPDB (Proceed To)

**As a** Credentialing Specialist  
**I want** to see the updated address in the PSV guided flow and route the case without waiting for NPDB  
**So that** I can complete the Add PL/BL process and send the case to HACAC or Provider Outreach without NPDB completion.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **ReviewScreen** step – displays Primary, Mailing, Billing addresses (as entered) before routing | Same pattern as Ancillary Reassessment PSV ReviewScreen |
| AC2 | **ProceedTo** radio – "Proceed To" with options: Pending NPDB Verification, HACAC, HACAC - Pended, Provider Outreach Needed | Right next to Add Practice Location / Business License (in Review step) |
| AC3 | When ProceedTo = HACAC / HACAC - Pended / Provider Outreach – **skip** NPDB step; save address and BL; route case | No NPDB wait; IP runs with NPDBRequest=No |
| AC4 | When ProceedTo = Pending NPDB Verification – show NPDBReportRequest, NPDBRequest; then save and route | Same as current flow |
| AC5 | **SetCaseManagerAndCase** – updates Case status and Content Note per ProceedTo selection | Same as Ancillary Reassessment |
| AC6 | Updated address visible in ReviewScreen before user completes | PrimaryAddressReview, MailingAddressReview, BillingAddressReview blocks |

**Reference:** Ancillary Reassessment PSV – ReviewScreen, ProceedTo, SetCaseManagerAndCase, PrimaryAddressChangeReview, MailingAddressReview.

---

### US-ADDPL-7: Preserve Existing Behavior

**As a** system  
**I want** all existing AddAncillaryPLAndBusinessLicense behavior preserved where not explicitly changed  
**So that** NPDB, license validation, duplicate checks, adverse action logs, and record creation continue to work.

---

### US-ADDPL-8: Route Case Button on Case Manager (Post-PSV, Without NPDB Report)

**As a** Credentialing Specialist  
**I want** a button on the Case Manager record page to route the case after completing the PSV process  
**So that** I can verify NPDB and route the case (HACAC, Provider Outreach, etc.) without waiting for the NPDB report.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | **Button** on Case Manager record page – suggested name: **"Route Case"** or **"Complete PSV Review"** | Visible on Case Manager layout |
| AC2 | Clicking the button opens a **modal or OmniScript** with the same UI as Ancillary Reassessment PSV last step | Proceed To + Note fields |
| AC3 | **Proceed To** (required radio) – options: Pending NPDB Verification, HACAC, HACAC - Pended, Provider Outreach Needed | Same as screenshot |
| AC4 | **Note** (required text area) – for comments/justification related to the routing decision | Same as screenshot |
| AC5 | On Submit – route the case per selection: update Case status, add Content Note, update owner if applicable | Same logic as Ancillary Reassessment PSV SetCaseManagerAndCase |
| AC6 | Use case: Business has completed PSV (e.g., Add PL/BL) and wants to route without NPDB report | Button available when Case Manager is in appropriate state |

**Suggested Button Name:** **"Route Case"** (concise) or **"Complete PSV Review"** (emphasizes post-PSV context).

**Reference:** Ancillary Reassessment PSV – ReviewScreen, ProceedTo, ReviewNote, SetCaseManagerAndCase.

---

## 3. Current State (OmniScript Analysis)

### PRM_AddAncillaryPLAndBusinessLicense_English – Current Structure (To Be Replaced)

| Step/Element | Type | Current Behavior | Target |
|--------------|------|------------------|--------|
| InvalidCase | Step | Validates Case; shows error if invalid | Keep |
| FetchDetails | IP Action | Fetches Case Manager, Practice Locations | **Enhance** – default primary PL |
| NoLocationAvailable | Step | Shown when no PLs available | Keep |
| AddPracticeLocation | Step | Main step – contains NewPL | **Rename/simplify** – "Primary Location & Addresses" |
| NewPL | Block (repeat) | Repeatable (repeatLimit=9); one per PL | **Remove** – single location |
| PracLoc | Type Ahead | Select existing PL; populates PracLoc-Block | **Remove** – no type-ahead |
| PLName, PLId | Display/Hidden | From PracLoc selection | Keep – from defaulted primary |
| AddrLine1, AddrLine2, PLCity, etc. | Text | **Read-only** | **Replace** – editable PrimaryAddress block |
| AddBLQuestion | Radio | "Do you want to add Business License?" (Yes/No) | Keep |
| NewLicense | Block (repeat) | Business License entry; repeatLimit=4 | Keep |
| NPDBReportRequest, NPDBRequest | Step | NPDB flow | Keep |
| AncillaryAddPLAndLicenseCreation | IP Action | Creates BL, Adverse Action Logs | **Update** – add address load steps |

### PRM_AncillaryAddPLAndLicenseCreation – Current IP Elements

| Order | Element | Purpose |
|-------|---------|---------|
| 1 | CreateBusinessLicensesAndCaseManagerAssoc | Creates Business License records |
| 2 | CB_CreateAdverseActionLogs | Creates Adverse Action Logs |
| 3 | DRTransformPracLocs | Transforms practice location data |
| 4 | RA_CreateAdverseActionLogsBatch | Batch for adverse action logs |
| 5 | Response | Response |

**No address load steps** – addresses are not updated.

---

## 4. Target State – Single Primary Location, Editable Addresses

### 4.1 Flow Structure (Simplified)

**No type-ahead. No multi-location. Single primary location defaulted.**

**Same question pattern as Ancillary Reassessment PSV** – ask if user wants to edit each address type.

| Element | Parent | Type | Label | Notes |
|---------|--------|------|-------|-------|
| PLName | Step | Display | Practice Location Name | Read-only; from defaulted primary |
| PLId | Step | Hidden | Practice Location Id | From defaulted primary |
| PrimaryAddress | Step | Block | Primary (Physical) Address | **Always visible, editable** |
| MailingAddressChange | Step | Radio | Change of Mailing Address? (Yes/No) | Same as Ancillary Reassessment PSV |
| MailingAddressNew | Step | Block | Mailing Address | Show when MailingAddressChange = Yes |
| SameAsPrimary | Step | Set Values | Same As Primary | Copies Primary to Mailing |
| ClearMailing | Step | Set Values | Clear Mailing Address | Same as Ancillary Reassessment |
| BillingAddressChange | Step | Radio | Change of Billing Address? (Yes/No) | Same pattern as Mailing |
| BillingAddressNew | Step | Block | Billing Address | Show when BillingAddressChange = Yes |
| AddBLQuestion | Step | Radio | Would you like to add License information? (Yes/No) | Preserved |
| NewLicense | Step | Block (repeat) | Business License | When AddBLQuestion = Yes; max 4 |

### 4.2 Primary Address Block Fields (PrimaryAddress)

| Field | Type | Label | Required | Default/Source |
|-------|------|-------|----------|----------------|
| AddLine1Primary | Text | Address Line 1 | Yes | From defaulted primary PL |
| AddLine2Primary | Text | Address Line 2 | No | From defaulted primary PL |
| CityPrimary | Text | City | Yes | From defaulted primary PL |
| StatePrimary | Select | State | Yes | From defaulted primary PL |
| ZipPrimary | Text | Zip | Yes | From defaulted primary PL |
| Zip4Primary | Text | Zip +4 | No | From defaulted primary PL |
| PhonePrimary | Text | Phone | Yes | From defaulted primary PL |
| PhoneExtensionPrimary | Text | Phone Extension | No | From defaulted primary PL |
| FaxPrimary | Text | Fax | No | From defaulted primary PL |
| PracticeNamePrimary | Text | Practice Name | No | (optional) |
| DBANamePrimary | Text | DBA Name | No | (optional) |

### 4.3 Mailing Address Block Fields (MailingAddressNew)

| Field | Type | Label | Required |
|-------|------|-------|----------|
| AddLine1Mailing | Text | Mailing Address Line 1 | Yes |
| AddLine2Mailing | Text | Mailing Address Line 2 | No |
| CityMailing | Text | City | Yes |
| StateMailing | Select | State | Yes |
| ZipMailing | Text | Zip | Yes |
| Zip4Mailing | Text | Zip +4 | No |

### 4.4 Billing Address Block Fields (BillingAddressNew)

| Field | Type | Label | Required |
|-------|------|-------|----------|
| AddLine1Billing | Text | Billing Address Line 1 | Yes |
| AddLine2Billing | Text | Billing Address Line 2 | No |
| CityBilling | Text | City | Yes |
| StateBilling | Select | State | Yes |
| ZipBilling | Text | Zip | Yes |
| Zip4Billing | Text | Zip +4 | No |

### 4.5 Element Order (Revised – Single Location)

1. **PLName**, **PLId** – from defaulted primary (FetchDetails loads primary PL)  
2. **PrimaryAddress** (Block) – editable; pre-populated from primary PL  
3. **MailingAddressChange** (Radio) – "Change of Mailing Address?" (Yes/No)  
4. **MailingAddressNew** (Block) – when MailingAddressChange = Yes  
5. **SameAsPrimary**, **ClearMailing** – Set Values for Mailing  
6. **BillingAddressChange** (Radio) – "Change of Billing Address?" (Yes/No)  
7. **BillingAddressNew** (Block) – when BillingAddressChange = Yes  
8. **AddBLQuestion** (Radio)  
9. **NewLicense** (Block) – when AddBLQuestion = Yes  
10. **ReviewScreen** (Step) – see §4.6  
11. **ProceedTo** (Radio) – see §4.6  
12. NPDBReportRequest, NPDBRequest – conditional on ProceedTo  
13. SetCaseManagerAndCase, AncillaryAddPLAndLicenseCreation, NavigateToCaseManager

---

### 4.6 Review Step & Proceed To – Mirror Ancillary Reassessment PSV Last Step

**Business requirement:**  
- Business wants to **see the updated address** in the PSV guided flow before routing.  
- Business does **not** want to wait for NPDB to complete the PSV process.  
- Add a **Proceed To** button/radio right next to Add Practice Location / Business License to route the case similar to the last step in Ancillary Reassessment PSV.

**Reference:** Ancillary Reassessment PSV – `ReviewScreen` step with `ProceedTo` radio, `PrimaryAddressChangeReview`, `MailingAddressReview`, `SetCaseManagerAndCase`.

#### 4.6.1 ReviewScreen Step (New)

| Element | Type | Label | Show Condition |
|---------|------|-------|----------------|
| ReviewScreen | Step | Review | After AddBLQuestion / NewLicense |
| ReAssessmentSummaryTextBlock | Text Block | Summary | Always |
| **PrimaryAddressReview** | Block | Primary (Physical) Address | Always (Primary always editable) |
| AddLine1PrimaryReview … Zip4PrimaryReview | Display/Formula | Address fields | From %PrimaryAddress% |
| **MailingAddressReview** | Block | Mailing Address | When MailingAddressChange = Yes |
| AddLine1MailingReview … Zip4MailingReview | Display/Formula | Address fields | From %MailingAddressNew% |
| **BillingAddressReview** | Block | Billing Address | When BillingAddressChange = Yes |
| AddLine1BillingReview … Zip4BillingReview | Display/Formula | Address fields | From %BillingAddressNew% |
| NewLicenseReview | Block | Business Licenses Added | When AddBLQuestion = Yes |
| **ProceedTo** | Radio | Proceed To | Required; see options below |
| PendedReason | Text | Pended Reason | When ProceedTo = HACAC - Pended |
| ReviewNote | Text Area | Review Note | Optional |

**Purpose:** User sees a summary of all address changes and BL additions before choosing where to route. The updated address is visible in the PSV guided flow at this step.

#### 4.6.2 ProceedTo Radio – Route Without Waiting for NPDB

| Option | Value | Case Status | Note Title |
|--------|-------|-------------|------------|
| Pending NPDB Verification | Pending NPDB Verification | In Progress | Add PL/BL - Pending NPDB |
| HACAC | HACAC | Closed | Add PL/BL - HACAC |
| HACAC - Pended | HACAC - Pended | Closed | Add PL/BL - HACAC Pended |
| Provider Outreach Needed | Provider Outreach Needed | Pending Provider Outreach | Add PL/BL - Provider Outreach |

**Flow logic:**
- **ProceedTo = Pending NPDB Verification** → Show NPDBReportRequest step, NPDBRequest; then run AncillaryAddPLAndLicenseCreation (with NPDBRequest=Yes in extraPayload).
- **ProceedTo = HACAC / HACAC - Pended / Provider Outreach Needed** → Skip NPDB steps; run AncillaryAddPLAndLicenseCreation directly (NPDBRequest=No or omit). User can complete PSV without waiting for NPDB.

#### 4.6.3 SetCaseManagerAndCase (New – Mirror Ancillary Reassessment)

Add **SetCaseManagerAndCase** (Set Values) before AncillaryAddPLAndLicenseCreation:

| Output | Formula |
|--------|---------|
| CaseStatusToUpdate | `IF(ProceedTo=="Pending NPDB Verification","In Progress", IF(ProceedTo=="Provider Outreach Needed","Pending Provider Outreach", IF(OR(ProceedTo=="HACAC",ProceedTo=="HACAC - Pended"),"Closed",null)))` |
| NoteTitle | `IF(ProceedTo=="Pending NPDB Verification","Add PL/BL - Pending NPDB", IF(ProceedTo=="Provider Outreach Needed","Add PL/BL - Provider Outreach", IF(OR(ProceedTo=="HACAC",ProceedTo=="HACAC - Pended"),"Add PL/BL - HACAC",null)))` |

**Reference:** `PRM_AncillaryReassessmentPSV_English_Element_SetCaseManagerAndCase.json`

#### 4.6.4 Step-by-Step Flow (Revised)

| # | Step/Element | Type | Purpose |
|---|--------------|------|---------|
| 1 | InvalidCase | Step | Validate Case |
| 2 | FetchDetails | IP Action | Load Case Manager, default primary PL, ExistingAddresses |
| 3 | NoLocationAvailable | Step | Error when no PL |
| 4 | **PrimaryLocationAndAddresses** | Step | PLName, PLId, PrimaryAddress, MailingAddressChange, MailingAddressNew, BillingAddressChange, BillingAddressNew |
| 5 | AddBLQuestion | Radio | Add Business License? (Yes/No) |
| 6 | NewLicense | Block | License entry (when Yes) |
| 7 | **ReviewScreen** | Step | **NEW** – Display updated Primary, Mailing, Billing addresses; BL summary |
| 8 | **ProceedTo** | Radio | **NEW** – Pending NPDB, HACAC, HACAC - Pended, Provider Outreach |
| 9 | PendedReason | Text | When ProceedTo = HACAC - Pended |
| 10 | ReviewNote | Text Area | Optional note |
| 11 | **SetCaseManagerAndCase** | Set Values | **NEW** – Update Case status, add Content Note per ProceedTo; runs before IP |
| 12 | NPDBReportRequest | Step | **Conditional** – Show only when ProceedTo = Pending NPDB Verification |
| 13 | NPDBRequest | Radio | Inside NPDBReportRequest – "Request NPDB report?" (Yes/No) |
| 14 | AncillaryAddPLAndLicenseCreation | IP Action | Always – saves address, BL; receives NPDBRequest (Yes when ProceedTo=Pending NPDB and user selected Yes; else No) |
| 15 | NavigateToCaseManager | Action | Navigate to Case Manager |

**Conditional visibility for NPDBReportRequest:**  
`show: { group: { rules: [{ condition: "=", data: "Pending NPDB Verification", field: "ProceedTo" }] } }`

**extraPayload for AncillaryAddPLAndLicenseCreation when ProceedTo ≠ Pending NPDB:**  
Pass `NPDBRequest: "No"` (or omit) so IP does not create NPDB request. Address and BL are still saved.

---

### 4.7 Route Case Button on Case Manager (Standalone)

**Purpose:** Business can verify NPDB and route the case after completing the PSV process **without** waiting for the NPDB report. The button is on the **Case Manager record page** (not inside AddAncillaryPL OmniScript).

#### 4.7.1 Button Specification

| Attribute | Value |
|-----------|-------|
| **Suggested Button Name** | **"Route Case"** or **"Complete PSV Review"** |
| **Location** | Case Manager record page (flexipage / Lightning page) |
| **Visibility** | When Case Manager is in appropriate state (e.g., PSV complete, pending routing) |
| **Action on Click** | Launch modal or OmniScript with Proceed To + Note |

#### 4.7.2 Modal / OmniScript Content (Match Screenshot)

| Element | Type | Label | Required |
|---------|------|-------|----------|
| **Proceed To** | Radio | * Proceed To | Yes |
| Option 1 | | Pending NPDB Verification | |
| Option 2 | | HACAC | |
| Option 3 | | HACAC - Pended | |
| Option 4 | | Provider Outreach Needed | |
| **Note** | Text Area | * Note | Yes |

**UI:** Same as Ancillary Reassessment PSV Review step (see screenshot).

#### 4.7.3 Routing Logic (Same as PSV)

| Proceed To | Case Status | Note Title |
|------------|-------------|------------|
| Pending NPDB Verification | In Progress | Add PL/BL - Pending NPDB (or equivalent) |
| HACAC | Closed | Add PL/BL - HACAC |
| HACAC - Pended | Closed | Add PL/BL - HACAC Pended |
| Provider Outreach Needed | Pending Provider Outreach | Add PL/BL - Provider Outreach |

**Implementation:** Create OmniScript `PRM_RouteCase_English` (or similar) with:
1. Review step: ProceedTo (radio), Note (text area)
2. Set Values: CaseStatusToUpdate, NoteTitle per ProceedTo
3. Integration Procedure or Apex: Update Case, add Content Note with Note content
4. Navigate back to Case Manager or refresh

**Reference:** Ancillary Reassessment PSV – SetCaseManagerAndCase, ProceedTo, ReviewNote.

---

## 5. Address Save Flow – Mirror Ancillary Reassessment PSV

### 5.1 How Ancillary Reassessment PSV Saves Addresses

**Source:** `PRM_AncillaryReassessmentPSVFormCreation` IP, `PRMLoadAddressPrimary`, `PRMLoadAddressAncesMailing` DataRaptors.

| Step | DataRaptor | Condition | Key Inputs |
|------|------------|------------|------------|
| 1 | PRMLoadAddressPrimary | `ISNOTBLANK(%PrimaryAddressNew%)` | PracticeLocationId, CaseManagerId, EffectiveFromDate (AddrEffective), ExistingPrimaryAdd (FILTER ExistingAddresses by AddType="Primary"), PrimaryAddressNew, Latitude/Longitude (OutputAPIresponse), isStandardized (AdditionalAddressValidated) |
| 2 | PRMLoadAddressAncesMailing | `ISNOTBLANK(%MailingAddressNew%)` | CaseManagerId, EffectiveFromDate, ExistingMalingAddr (FILTER ExistingAddresses by AddType="Mailing"), MailingAddressNew, Latitude/Longitude, isStandardized |

**extraPayload from OmniScript:**
- `PrimaryAddressNew` = %ReassessmentUpdate:PrimaryAddressNew%
- `MailingAddressNew` = %ReassessmentUpdate:MailingAddressNew%
- `ExistingAddresses` = %ReAssessmentApplication:AddressBlk% (array with AddType: Primary, Mailing, Billing)
- `AddrEffective` = %ReassessmentUpdate:CredContactInfo:ChangeAddressEffectiveDate%
- `PracticeLocationId`
- `AdditionalAddressValidated` (Precisely API confirmation)
- `OutputAPIresponse` (Precisely API – LatitudeAR, LongitudeAR)

**Note:** Ancillary Reassessment has Primary + Mailing only. **No Billing.** PRMLoadAddressAncesBilling does not exist—must be created for AddAncillaryPL.

---

### 5.2 AddAncillaryPL – Same Pattern for Primary, Mailing, Billing

Add address load steps **before** CreateBusinessLicensesAndCaseManagerAssoc. **Mirror Ancillary Reassessment exactly.**

| Order | Element | Type | Condition | Purpose |
|-------|---------|------|-----------|---------|
| 1 | **PRMLoadAddressPrimary** | DataRaptor Post Action | `ISNOTBLANK(%PrimaryAddress%)` or always (Primary always editable) | Same as Ancillary Reassessment |
| 2 | **PRMLoadAddressAncesMailing** | DataRaptor Post Action | `ISNOTBLANK(%MailingAddressNew%)` | Same as Ancillary Reassessment |
| 3 | **PRMLoadAddressAncesBilling** | DataRaptor Post Action | `ISNOTBLANK(%BillingAddressNew%)` | **New** – create DR (mirror Mailing) |
| 4 | CreateBusinessLicensesAndCaseManagerAssoc | (existing) | | Adapt for single PL |
| 5 | CB_CreateAdverseActionLogs | (existing) | | |
| 6 | DRTransformPracLocs | (existing) | | Adapt for single PL |
| 7 | RA_CreateAdverseActionLogsBatch | (existing) | | |
| 8 | Response | (existing) | | |

**Condition logic:** Use `ISNOTBLANK(%MailingAddressNew%)` and `ISNOTBLANK(%BillingAddressNew%)`—same as Ancillary Reassessment. When user selects "Change of Mailing Address? Yes" and fills the block, MailingAddressNew has data. Same for Billing.

---

### 5.3 DataRaptor Input Mapping – Match Ancillary Reassessment

**PRMLoadAddressPrimary** (reuse – same inputs as Ancillary Reassessment):

| Input | Source (AddAncillaryPL) |
|-------|------------------------|
| PracticeLocationId | %PLId% |
| CaseManagerId | %CaseManager:Id% or from PRMDRAncReassesUpdateCaseAndCaseManager equivalent |
| EffectiveFromDate | %AddrEffective% or %CredContactInfo:ChangeAddressEffectiveDate% |
| ExistingPrimaryAdd | `FILTER(LIST(%ExistingAddresses%), 'AddType LIKE("Primary")')` |
| PrimaryAddressNew | %PrimaryAddress% (or %PrimaryAddressNew% – use same field names as Ancillary Reassessment) |
| Latitude | %OutputAPIresponse\|1:LatitudeAR% (if Precisely used) |
| Longitude | %OutputAPIresponse\|1:LongitudeAR% |
| isStandardized | `IF(%AdditionalAddressValidated\|1:Confirm%=="Confirm", true, false)` |

**PRMLoadAddressAncesMailing** (reuse – same inputs as Ancillary Reassessment):

| Input | Source (AddAncillaryPL) |
|-------|------------------------|
| CaseManagerId | %CaseManager:Id% |
| EffectiveFromDate | %AddrEffective% |
| ExistingMalingAddr | `FILTER(LIST(%ExistingAddresses%), 'AddType LIKE("Mailing")')` |
| MailingAddressNew | %MailingAddressNew% |
| Latitude | `IF(ISNOTBLANK(%PrimaryAddress%), %OutputAPIresponse\|2:LatitudeAR%, %OutputAPIresponse\|1:LatitudeAR%)` (index 2 when Primary also changed, else 1) |
| Longitude | Same pattern |
| isStandardized | `IF(ISNOTBLANK(%PrimaryAddress%), IF(%AdditionalAddressValidated\|2:Confirm%=="Confirm", true, false), IF(%AdditionalAddressValidated\|1:Confirm%=="Confirm", true, false))` |

**PRMLoadAddressAncesBilling** (new – mirror PRMLoadAddressAncesMailing):

| Input | Source (AddAncillaryPL) |
|-------|------------------------|
| CaseManagerId | %CaseManager:Id% |
| EffectiveFromDate | %AddrEffective% |
| ExistingBillingAddr | `FILTER(LIST(%ExistingAddresses%), 'AddType LIKE("Billing")')` |
| BillingAddressNew | %BillingAddressNew% |
| Latitude | Index from OutputAPIresponse: 3 if Primary+Mailing+Billing all changed; 2 if Primary+Billing or Mailing+Billing; 1 if only Billing |
| Longitude | Same pattern |
| isStandardized | Same index logic from AdditionalAddressValidated |

**Note:** PRMLoadAddressAncesMailing uses `ExistingMalingAddr:ParentId` for Address ParentId (Location). PRMLoadAddressAncesBilling must use `ExistingBillingAddr:ParentId` similarly.

---

### 5.4 FetchDetails Must Provide ExistingAddresses

**Critical:** Ancillary Reassessment passes `ExistingAddresses` (ReAssessmentApplication:AddressBlk) with AddType for Primary, Mailing, Billing. AddAncillaryPL **FetchDetails** (or equivalent) must:

1. Query `Address` records where `ParentId` = primary PL's LocationId
2. Build **ExistingAddresses** array with structure: `[{ AddType: "Primary", AddLine1, AddLine2, AddCity, AddState, AddZip, AddZip4, AddPhone, AddPhoneExt, AddFax, ... }, { AddType: "Mailing", ... }, { AddType: "Billing", ... }]`
3. Pass to IP in extraPayload

---

### 5.5 extraPayload / OmniScript → IP (Complete)

```json
{
  "CaseManager": "%CaseManager%",
  "MedicareNumber": "%MedicareNumber%",
  "NPDBRequest": "%NPDBRequest%",
  "OrganizationType": "%OrganizationType%",
  "PLId": "%PLId%",
  "PracticeLocationId": "%PLId%",
  "PrimaryAddress": "%PrimaryAddress%",
  "PrimaryAddressNew": "%PrimaryAddress%",
  "MailingAddressNew": "%MailingAddressNew%",
  "BillingAddressNew": "%BillingAddressNew%",
  "ExistingAddresses": "%ExistingAddresses%",
  "AddrEffective": "%CredContactInfo:ChangeAddressEffectiveDate%",
  "CredContactInfo": "%CredContactInfo%",
  "AdditionalAddressValidated": "%AdditionalAddressValidated%",
  "OutputAPIresponse": "%OutputAPIresponse%",
  "AddBLQuestion": "%AddBLQuestion%",
  "NewLicense": "%NewLicense%",
  "TaxId": "%TaxId%"
}
```

**Required for address save (same as Ancillary Reassessment):**
- ExistingAddresses, AddrEffective, PrimaryAddressNew, MailingAddressNew, BillingAddressNew
- AdditionalAddressValidated, OutputAPIresponse (if Precisely address validation used)

---

## 6. Optional: Precisely Address Validation

Ancillary Reassessment uses **AncillaryReassessmentPreciselyApi** when Primary or Mailing address changes. Consider adding:

- **AddAncillaryPLPreciselyApi** – similar to AncillaryReassessmentPreciselyApi
- Trigger when PrimaryAddressChange = Yes or MailingAddressChange = Yes or BillingAddressChange = Yes
- Address confirmation step (Confirm/Use Original) before load

*(Can be Phase 2.)*

---

## 7. Implementation Order

| Phase | Task |
|-------|------|
| 1 | **Remove** type-ahead (PracLoc), NewPL repeatable block |
| 2 | **Enhance FetchDetails** – default/load Case Manager's primary practice location; populate PLId, PLName, address data; build **ExistingAddresses** (AddressBlk) with AddType Primary/Mailing/Billing |
| 3 | Add **PrimaryAddress** block (editable) – replace read-only AddrLine1, etc. |
| 4 | Add **MailingAddressChange**, **MailingAddressNew**, **SameAsPrimary**, **ClearMailing** (mirror Ancillary Reassessment PSV) |
| 5 | Add **BillingAddressChange**, **BillingAddressNew** |
| 6 | Create **PRMLoadAddressAncesBilling** DataRaptor (if not exists) |
| 7 | Update **PRM_AncillaryAddPLAndLicenseCreation** – add PRMLoadAddressPrimary, PRMLoadAddressAncesMailing, PRMLoadAddressAncesBilling (before CreateBusinessLicensesAndCaseManagerAssoc) |
| 8 | Update **CreateBusinessLicensesAndCaseManagerAssoc**, **DRTransformPracLocs** – accept single PL structure (not NewPL array) |
| 9 | Update extraPayload to pass PLId, PrimaryAddress, MailingAddressNew, BillingAddressNew, ExistingAddresses, AddrEffective, CredContactInfo (and Precisely fields if used) |
| 10 | **Add ReviewScreen step** – PrimaryAddressReview, MailingAddressReview, BillingAddressReview (display updated addresses) |
| 11 | **Add ProceedTo radio** – Pending NPDB Verification, HACAC, HACAC - Pended, Provider Outreach Needed |
| 12 | **Add SetCaseManagerAndCase** – update Case status and Content Note per ProceedTo |
| 13 | **Make NPDBReportRequest conditional** – show only when ProceedTo = Pending NPDB Verification |
| 14 | Update extraPayload NPDBRequest – pass "No" when ProceedTo ≠ Pending NPDB |
| 15 | Test: Default primary + edit addresses + add BL + ProceedTo (with and without NPDB) |
| 16 | **Add "Route Case" button** on Case Manager record page – launch modal/OmniScript with Proceed To + Note; route case per selection |
| 17 | (Optional) Add Precisely address validation |

---

## 8. Files to Create/Modify

| File | Action |
|------|--------|
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_PracLoc.json` | **Remove** |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_NewPL.json` | **Remove** |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_PrimaryAddress.json` | Create – editable block |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_AddLine1Primary.json` through `FaxPrimary.json` | Create (inside PrimaryAddress) |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_MailingAddressChange.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_MailingAddressNew.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_SameAsPrimary.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_ClearMailing.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_BillingAddressChange.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_BillingAddressNew.json` | Create |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_ReviewScreen.json` | **Create** – Review step (label: "Review") |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_PrimaryAddressReview.json` | **Create** – Block showing Primary address (always) |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_AddLine1PrimaryReview.json` … `Zip4PrimaryReview.json` | **Create** – Display from %PrimaryAddress% |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_MailingAddressReview.json` | **Create** – Block when MailingAddressChange=Yes |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_BillingAddressReview.json` | **Create** – Block when BillingAddressChange=Yes |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_ProceedTo.json` | **Create** – Radio: Pending NPDB, HACAC, HACAC - Pended, Provider Outreach |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_SetCaseManagerAndCase.json` | **Create** – Set Values for Case status, NoteTitle |
| `PRM_AddAncillaryPLAndBusinessLicense_English_Element_NPDBReportRequest.json` | **Update** – Add `show` condition: ProceedTo = "Pending NPDB Verification" |
| `PRM_AddAncillaryPLAndBusinessLicense_English_DataPack.json` | Update – add ReviewScreen, ProceedTo, SetCaseManagerAndCase; reorder steps |
| `PRM_AncillaryAddPLAndLicenseCreation_Element_PRMLoadAddressPrimary.json` | Create |
| `PRM_AncillaryAddPLAndLicenseCreation_Element_PRMLoadAddressAncesMailing.json` | Create |
| `PRM_AncillaryAddPLAndLicenseCreation_Element_PRMLoadAddressAncesBilling.json` | Create |
| `PRM_AncillaryAddPLAndLicenseCreation` (CreateBusinessLicensesAndCaseManagerAssoc, DRTransformPracLocs) | Update – single PL input |
| FetchDetails IP / DataRaptor | Update – return primary PL and addresses |
| `PRMLoadAddressAncesBilling` (DataRaptor) | Create – if Billing not supported by existing DR |
| **Case Manager page – "Route Case" button** | **Add** – Flexipage/Lightning component; launches Route Case OmniScript |
| `PRM_RouteCase_English` (OmniScript) | **Create** – ProceedTo, Note; SetCaseManagerAndCase; IP to update Case |

---

## 9. Summary

| Capability | Current | Target |
|------------|---------|--------|
| Practice Location | Type-ahead; NewPL repeat (max 9) | **Single primary – defaulted** (no type-ahead) |
| Primary Address | Read-only | **Editable** (always visible) |
| Mailing Address | Not present | **Editable** when MailingAddressChange = Yes ("Change of Mailing Address?") |
| Billing Address | Not present | **Editable** when BillingAddressChange = Yes ("Change of Billing Address?") |
| **Review – Updated Address** | Not present | **ReviewScreen** – displays Primary, Mailing, Billing addresses before routing |
| **Proceed To (Route w/o NPDB)** | Not present | **ProceedTo** radio – Pending NPDB, HACAC, HACAC - Pended, Provider Outreach |
| **Route Case button (Case Manager)** | Not present | **"Route Case"** button – post-PSV routing without NPDB report; Proceed To + Note |
| NPDB Request | Always shown | **Conditional** – only when ProceedTo = Pending NPDB Verification |
| Add Business Licenses | Yes (AddBLQuestion, NewLicense) | Same – for primary location |
| Address DataRaptors | None | PRMLoadAddressPrimary, PRMLoadAddressAncesMailing, PRMLoadAddressAncesBilling |

---

*End of Requirements Document*
