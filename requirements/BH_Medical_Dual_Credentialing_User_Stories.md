# Behavioral Health ↔ Medical Dual Credentialing — User Stories

**Business Request Source:** Nicole Brown
**Vertical:** Provider Network Management (PNM)
**Date Created:** 2026-03-31
**Sprint:** TBD
**Tags:** BH, Medical, Dual Credentialing, Taxonomy, PAR, PSV, QC, Committee, PDA, Network Management

---

## Business Context

> *"We often have practitioners that are credentialed as Behavioral Health but requires credentialing for Medical in addition to the BH. The practitioner needs to go through the credentialing process for Medical. The also applies to Medical practitioners requiring credentialing for BH. Examples practitioners listed below.*
> *Sajani Sukhadia - 1023309382*
> *Margaret Oduro - 1417443367*
> *This is critical because medical and behavior health practitioners require separate credentialing. The taxonomy would be different except for a physician assistant; their taxonomy would be the same. Majority of the time the practitioners are joining a different practice but there could be times where the practitioner is working as a BH/Medical practitioner for the same practice. In our old system one group was setup as Medical and another as BH so they would be linked with the appropriate practices."*

---

## End-to-End Credentialing Flow Impacted

The full practitioner initial credentialing flow must support dual BH/Medical credentialing at every stage:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         PRACTITIONER INITIAL CREDENTIALING FLOW                                     │
│                                                                                                     │
│  1. Practitioner        2. App Review       3. PSV Review      4. Committee      5. PDA Review     │
│     Participation Form     (RecredQC /         (RecredQC /        Review           & Update         │
│     (PAR form via FHN      CredAppReview)      CredAppReview)     (Routine /       (PDA Update)     │
│      Portal + PIE)                                                 Non-routine)                     │
│                                                                                                     │
│  6. Network Management QC                                                                           │
│     (NM QC Queue processing)                                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key OmniScripts in the flow:**

| Stage | OmniScript / Artifact | Key Purpose |
|-------|----------------------|-------------|
| **1. Practitioner Participation** | `PRM_PractitionerParticipationForm_English` | Provider intake, specialty selection, taxonomy, BH telehealth question |
| **2. App Review** | `PRM_CredApplicationReviewSubOS_English` (embedded in RecredQC) | Demographics, specialty, CAQH, role verification |
| **3. PSV Review** | `PRM_PSVSubOsWSNPDB_English`, `PRM_PSVSubOsTxnyRole_English` (embedded in RecredQC) | NPI, CAQH, licenses, DEA, CDS, board cert, NPDB, work history |
| **4. Committee Review** | `PRM_ReviewInitialCredApplicants_English` (Routine), `PRM_NonRoutineCommitteeReview_English` (Non-routine) | Committee decision: Approve/Deny/Pend |
| **5. PDA Review & Update** | `PRM_ProviderChangePDAUpdate_English` | Practice location, taxonomy, network creation, facility records |
| **6. Network Management QC** | `PRM_PNCPDA_English`, `PRM_ManualUpdatesQCReview3_English` | Final QC, network verification, info codes |

**Key Data Model Elements:**

| Object | Role in BH/Medical Split |
|--------|--------------------------|
| `Account` (RecordType: `PRM_Practitioner`) | Practitioner person account — one per NPI |
| `IndividualApplication` (Case Manager) | One per credentialing request — RecordType: `PRM_PractitionerParticipationRequest` |
| `HealthcareProviderTaxonomy` | Links practitioner to taxonomy code — **this is where BH vs Medical is distinguished** |
| `HealthcarePractitionerFacility` | Practitioner ↔ Practice Location affiliation (one per location per taxonomy) |
| `HealthcareFacilityNetwork` | Network participation per practice location |
| `CareTaxonomy` (custom: `PRM_TaxonomyGrouping__c`) | Taxonomy grouping: `"Behavioral Health & Social Service Providers"` vs Medical groupings |

---

## Current State Analysis

### How BH vs Medical is Currently Determined

1. **At Intake (PAR Form):** The `ProviderSpecialty-Block` element captures the practitioner's specialty. The specialty is linked to a `CareTaxonomy` record with `PRM_TaxonomyGrouping__c`. When the grouping = `"Behavioral Health & Social Service Providers"`, the formula `SpecialtyGroupingFormula` evaluates to `true`, triggering BH-specific fields (e.g., `PractitionerTelehealth` — "Are any of the practitioner's groups telehealth only?").

2. **`isAddSpecBehavioralHealth` flag:** Set during PAR form processing — flows into `PRM_PractitionerScreenRecordCreation` IP. When `true`, BH-specific credential requirements are triggered.

3. **Provider Change Form / PDM:** Uses `IsGroupBehavioralHealthCOI` formula: `CONTAINS(%addSelect1COI|n%, 'Behavioral Health & Social Service Providers')` to show/hide BH-specific COI (Certificate of Insurance) fields.

4. **HACAC Committee Report:** The `HACACBehavioralHealth` checkbox is displayed for each facility row, sourced from the assessment data.

### Current Limitation

The system assumes **one credentialing type per practitioner NPI**. A practitioner credentialed as BH cannot simultaneously be credentialed as Medical under the same Account/NPI. The taxonomy grouping drives process branching but does not support **dual-track credentialing** where the same NPI goes through the full lifecycle twice with different taxonomies.

**In the legacy system:** Two separate groups were created — one Medical, one BH — each linked to appropriate practices. This separation is not currently replicated in PIE/Salesforce.

---

# USER STORY 1: Initiate Dual Credentialing — New PAR for Existing Practitioner with Different Specialty Type

**Persona:** Credentialing Specialist
**Priority:** P0 (Critical)
**OmniScript:** `PRM_PractitionerParticipationForm_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** Credentialing Specialist,
**I want** to submit a new Practitioner Participation Request (PAR) for an existing practitioner who is already credentialed under one specialty type (e.g., BH) but now needs credentialing under a different specialty type (e.g., Medical),
**So that** the practitioner can be separately credentialed for both BH and Medical, allowing them to practice under the appropriate taxonomy at one or more practice locations.

**Why it matters:** Practitioners like Sajani Sukhadia (NPI: 1023309382) and Margaret Oduro (NPI: 1417443367) are credentialed as BH but also need Medical credentialing. Today, submitting a new PAR for an existing credentialed practitioner may trigger duplicate detection errors, or the system may attempt to update the existing case manager rather than creating a new one. This blocks the dual-credentialing workflow entirely.

## Technical Section (For Developers)

### Current State (from codebase)

- **`PRM_PractitionerParticipationForm_English`** (OmniScript, version 111 active): The PAR form captures practitioner NPI, specialty, taxonomy, and group info. On submission, it calls `PRM_PractitionerScreenRecordCreation` IP which creates:
  - `IndividualApplication` (Case Manager) with RecordType `PRM_PractitionerParticipationRequest`
  - `Case` with Type = `Application Review`
  - `PRM_CaseDataManager__c` linking the case manager to related objects
- **Duplicate Detection:** The system checks if a practitioner with the same NPI already exists. If found, the existing `Account` is reused. However, the logic may not support creating a **second** `IndividualApplication` for the same practitioner with a different specialty type.
- **`SpecialtyGroupingFormula`** (Formula, seq 36): `%PractitionerForm:isAddSpecBehavioralHealth% || %ProviderSpecialty-Block:Grouping% == "Behavioral Health & Social Service Providers"` — this determines BH-specific branching for the current PAR only.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_PractitionerParticipationForm_English`** | OmniScript | Add logic to detect if an existing `IndividualApplication` (Case Manager) already exists for the same NPI with a different `TaxonomyGrouping`. If yes, present a message: *"This practitioner already has an active [BH/Medical] credentialing. You are initiating a new [Medical/BH] credentialing request."* Allow the specialist to proceed. |
| **`PRM_PractitionerScreenRecordCreation`** | Integration Procedure | Modify to allow creation of a second `IndividualApplication` for the same `AccountId` when the new PAR has a different `TaxonomyGrouping` than any existing active case manager. Ensure the new case manager links to the same practitioner Account but with a distinct specialty/taxonomy. |
| **Duplicate Check Logic** | IP / DataRaptor | Update duplicate detection to match on `NPI + TaxonomyGrouping` (not just `NPI`). An existing BH credentialing should NOT block a new Medical PAR for the same NPI. |
| **`PRM_CaseDataManager__c`** | Custom Object | Ensure a new `PRM_CaseDataManager__c` record is created for the second case manager, independent of the first. |
| **PAR Form — New Field** | OmniScript Element | Add a read-only Text Block or Formula showing the existing credentialing status and type for the practitioner when an active case manager is found: *"Existing Credentialing: Behavioral Health — Status: Credentialed — Approved Date: MM/DD/YYYY"* |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| **PRM_PractitionerScreenRecordCreation** | IP | NPI, Specialty, TaxonomyGrouping, AccountId | IndividualApplication Id, Case Id | Allow second PAR when TaxonomyGrouping differs from existing active CM |
| **PRMDRExtractHCProviderDetails** | DR Extract | NPI | Existing Account, CMs, Taxonomy records | Add filter/output for existing CM RecordType + TaxonomyGrouping to inform the form |
| **New: PRMDRCheckExistingCredentialingType** | DR Extract (new) | AccountId / NPI | Existing IndividualApplication records with specialty/taxonomy grouping | New DataRaptor to check what credentialing types already exist for this NPI |

## Acceptance Criteria

**AC-1 — New PAR for Different Specialty Type**

**Given** a practitioner is already credentialed as "Behavioral Health & Social Service Providers" (e.g., NPI 1023309382),
**When** a Credentialing Specialist opens the Practitioner Participation Form and enters the same NPI with a Medical specialty taxonomy,
**Then** the system SHALL allow the specialist to proceed with the new PAR,
**And** SHALL display a notification that the practitioner has an existing BH credentialing.

---

**AC-2 — Separate Case Manager Created**

**Given** the specialist submits the new PAR with a Medical specialty for an existing BH-credentialed practitioner,
**When** the `PRM_PractitionerScreenRecordCreation` IP runs,
**Then** a new `IndividualApplication` (Case Manager) SHALL be created with RecordType `PRM_PractitionerParticipationRequest`,
**And** it SHALL be linked to the same practitioner `Account` (same NPI),
**And** it SHALL have a distinct specialty/taxonomy grouping (Medical vs BH).

---

**AC-3 — Existing Credentialing Unaffected**

**Given** a new Medical PAR is created for an existing BH-credentialed practitioner,
**When** the new case manager is created and moves through the credentialing lifecycle,
**Then** the existing BH Case Manager, its associated records (`HealthcareProviderTaxonomy`, `HealthcarePractitionerFacility`, `HealthcareFacilityNetwork`), and credentialing status SHALL remain unchanged.

---

**AC-4 — Same Practice, Different Taxonomy Supported**

**Given** a practitioner needs both BH and Medical credentialing at the same practice location,
**When** the PAR form is submitted with the same practice group but a different specialty,
**Then** the system SHALL create a new case manager linked to the same practice (vendor Account) but with a different taxonomy association.

---

**AC-5 — Physician Assistant Exception**

**Given** a practitioner with a Physician Assistant taxonomy (which is the same for both BH and Medical per the business rule),
**When** the specialist attempts to submit a new PAR for the other specialty type,
**Then** the system SHALL display a warning: *"Physician Assistant taxonomy is the same for BH and Medical. Please confirm this is a new credentialing request and not a duplicate."*

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **How do we determine if a practitioner is BH or Medical?** Is it solely based on `CareTaxonomy.PRM_TaxonomyGrouping__c = "Behavioral Health & Social Service Providers"` vs. other groupings? Or is there a field on the Account/NPI that flags this? | Core branching logic for the entire dual-credentialing flow | BA / Business |
| 2 | **Should the practitioner Account (`PRM_Practitioner`) have a new field** to track credentialing types (e.g., `PRM_CredentialingTypes__c` = "BH;Medical")? Or is the presence of multiple `IndividualApplication` records with different taxonomies sufficient? | Data model design | Technical / BA |
| 3 | **When the same NPI has two active Case Managers (BH + Medical), how should the queue routing work?** Should both go to the same Credentialing Specialist, or different queues for BH vs Medical? | Queue assignment and round-robin logic | Operations / BA |
| 4 | **Is there a specific form source for Medical credentialing vs BH?** Today, `PRM_FormType__c` captures the form source. Should a new form type be created (e.g., "Practitioner Participation Request - Medical" vs "Practitioner Participation Request - BH")? | PAR form configuration | BA |
| 5 | **Should the Case Manager Name/Number distinguish BH from Medical?** For example, should the `IndividualApplication.Name` include a suffix like "APP-12345-BH" or "APP-12345-MED"? | Reporting and identification | BA / Business |
| 6 | **For the two example practitioners (Sajani Sukhadia - 1023309382, Margaret Oduro - 1417443367), what is their current status?** Are they fully credentialed as BH, or still in-progress? Do they need new PARs or a conversion from existing data? | Migration vs new-flow decision | BA / Business |
| 7 | **Does the PAR form need any changes to collect additional BH/Medical-specific information** (e.g., separate insurance requirements, different license types)? | Form scope | BA / Business |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_PractitionerParticipationForm_English`** | OmniScript | **HIGH** | Must allow second PAR for same NPI with different taxonomy; display existing credentialing info |
| **`PRM_PractitionerScreenRecordCreation`** | IP | **HIGH** | Must create second IndividualApplication for same Account without duplicate rejection |
| **Duplicate Detection Logic** | IP / DataRaptor | **HIGH** | Must match on NPI + TaxonomyGrouping, not NPI alone |
| **`PRM_CaseDataManager__c`** | Custom Object | **MEDIUM** | Second CaseDataManager for the new case manager |
| **Case Routing / Round Robin** | Flow / Apex | **MEDIUM** | May need separate queues or routing rules for BH vs Medical |
| **Existing Case Manager Records** | Data | **LOW** | No change to existing records; new records created alongside |

---

---

# USER STORY 2: Application Review — Handle Dual-Credentialed Practitioner in App Review

**Persona:** Credentialing Specialist (App Reviewer)
**Priority:** P0 (Critical)
**OmniScript:** `PRM_RecredQC_English` (Application Review step: `ReviewPractitioner`), `PRM_CredApplicationReviewSubOS_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** Credentialing Specialist performing Application Review,
**I want** the Application Review step to clearly display which credentialing type (BH or Medical) is being reviewed, and show the practitioner's other active credentialing status,
**So that** I can accurately review the application in the context of the correct specialty type without confusion about the practitioner's existing credentials.

**Why it matters:** When a practitioner has two active Case Managers (one BH, one Medical), the Application Review step must contextualize the review. The reviewer needs to know that this practitioner is already credentialed for BH and is now going through Medical (or vice versa), as the taxonomy, specialty, and group information will differ. Without this context, reviewers may inadvertently apply BH-specific review criteria to a Medical application.

## Technical Section (For Developers)

### Current State (from codebase)

- **`ReviewPractitioner`** step (inside `PRM_RecredQC_English`): Contains demographics, NPI, CAQH ID, specialty blocks, group info, addresses, DEI fields. The `SpecialtyGroupingFormula` and `isAddSpecBehavioralHealth` flag drive BH-specific fields (like telehealth questions).
- **`SetPractitionerSpecialtyFields`** (Set Values): Sets specialty-related data at end of App Review — drives downstream PSV branching.
- **`DRTransformGroupData`** (DataRaptor Transform): Transforms group/practice data for the review screens.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`ReviewPractitioner`** step | OmniScript Step | Add a Text Block header showing: *"Credentialing Type: [Medical / Behavioral Health]"* sourced from the Case Manager's taxonomy grouping. Add a secondary info block: *"Other Active Credentialing: [BH — Status: Credentialed — Since: MM/DD/YYYY]"* if another Case Manager exists for the same NPI. |
| **`IPFetchParInformation`** | IP | Extend to query for other active `IndividualApplication` records for the same `AccountId` with a different taxonomy grouping. Return as `OtherCredentialingInfo` node. |
| **`SetPractitionerSpecialtyFields`** | Set Values | Ensure the specialty fields are set based on the **current** Case Manager's taxonomy, not the practitioner's Account-level data (which may reflect the other credentialing type). |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| **IPFetchParInformation** | IP | CaseId, AccountId | PAR context + OtherCredentialingInfo | Query second CM for same AccountId with different TaxonomyGrouping |
| **New: PRMDRFetchOtherCredentialingStatus** | DR Extract (new) | AccountId, CurrentCMId | Other CM Name, Status, TaxonomyGrouping, ApprovedDate | New DataRaptor to fetch the other credentialing track |

## Acceptance Criteria

**AC-1 — Credentialing Type Visible in App Review**

**Given** a Credentialing Specialist opens the Application Review for a Medical PAR on a practitioner who is already credentialed as BH,
**When** the `ReviewPractitioner` step loads,
**Then** a header SHALL display: *"Credentialing Type: Medical"*,
**And** an info block SHALL display: *"Existing Credentialing: Behavioral Health — Status: Credentialed"*.

---

**AC-2 — Correct Specialty Branching**

**Given** the practitioner's existing credentialing is BH (taxonomy grouping = "Behavioral Health & Social Service Providers"),
**When** the Application Review is for a Medical specialty,
**Then** the BH-specific fields (e.g., `PractitionerTelehealth` question) SHALL NOT display,
**And** Medical-specific review criteria SHALL apply.

---

**AC-3 — Reverse Direction Supported**

**Given** a Medical-credentialed practitioner submits a new PAR for BH credentialing,
**When** the Application Review loads,
**Then** the header SHALL display: *"Credentialing Type: Behavioral Health"*,
**And** BH-specific fields (telehealth, BH-specific COI) SHALL display,
**And** the info block SHALL show: *"Existing Credentialing: Medical — Status: Credentialed"*.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Are there any fields in the Application Review that should be pre-populated from the existing BH credentialing?** For example, should the practitioner's verified address, NPI, CAQH ID carry over from the existing credential, or must they be re-verified from scratch? | Volume of data entry for the specialist | BA / Business |
| 2 | **Should the Application Review be streamlined for dual credentialing?** Since the practitioner is already credentialed, some data (demographics, DEI, contacts) is already verified. Can this be marked as "Previously Verified" to accelerate review? | Process efficiency | Operations / BA |
| 3 | **Is there any change in the process for dual credentialing vs initial credentialing?** For example, does the Medical credentialing of an existing BH practitioner skip any steps, or does it follow the exact same full lifecycle? | Scope of flow modifications | BA / Business |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_RecredQC_English`** (ReviewPractitioner) | OmniScript Step | **HIGH** | New header/info block; specialty branching must be context-aware |
| **`IPFetchParInformation`** | IP | **MEDIUM** | Extended query for other active CMs |
| **`PRM_CredApplicationReviewSubOS_English`** | Embedded OmniScript | **MEDIUM** | May need context about dual credentialing type |
| **`SetPractitionerSpecialtyFields`** | Set Values | **LOW** | Verify correct taxonomy-based setting for current CM only |

---

---

# USER STORY 3: PSV Review — Taxonomy-Specific Primary Source Verification for Dual-Credentialed Practitioners

**Persona:** PSV Specialist
**Priority:** P0 (Critical)
**OmniScript:** `PRM_RecredQC_English` (PSV steps), `PRM_PSVSubOsWSNPDB_English`, `PRM_PSVSubOsTxnyRole_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** PSV Specialist,
**I want** the PSV review to correctly verify primary sources specific to the credentialing type (BH or Medical), using the appropriate taxonomy and specialty criteria,
**So that** I can complete the PSV for the Medical credentialing of a BH practitioner (or vice versa) with the correct verification steps, board certifications, and specialty-specific checks.

**Why it matters:** BH and Medical have different PSV requirements — different board certifications, potentially different DEA/CDS requirements, different specialty verifications, and different admitting privileges rules. The PSV flow must know which credentialing track it is processing to apply the correct verification standards. The taxonomy code drives which care specialties are verified, and for a dual-credentialed practitioner, the **new** taxonomy (not the existing one) must be the focus of PSV.

## Technical Section (For Developers)

### Current State (from codebase)

- **`PRM_PSVSubOsTxnyRole_English`** (Embedded OmniScript): Handles Service Area Verification, taxonomy role assignment, admitting privileges. Contains `PSVPracticeState`, `PSVPracticeCounty`, `AdmittingPrivilegesReview`.
- **`PRM_PSVSubOsWSNPDB_English`** (Embedded OmniScript): Handles NPI validation, CAQH verification, NPDB results, sanctions, license verification, board certification, work history, education.
- **`VerifySpecialty`** step: Verifies the practitioner's care taxonomy. Uses `VerifyCareTaxonomyRD` and `IPToCountPrimaryTaxonomy`.
- **`CertificateofInsuranceVerification`** step: COI verification — BH has different COI requirements (based on `IsGroupBehavioralHealthCOI` formula).
- **`BoardCertificationsStep`**: Board certifications differ between BH and Medical specialties.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`VerifySpecialty`** | OmniScript Step | Ensure the specialty verification uses the **current Case Manager's** taxonomy, not the Account-level existing taxonomy. For dual-credentialed practitioners, the new taxonomy (e.g., Medical) must be verified, not the existing one (BH). |
| **`CertificateofInsuranceVerification`** | OmniScript Step | The `IsGroupBehavioralHealthCOI` formula must evaluate against the **current Case Manager's** specialty, not the Account-level data. A Medical credentialing for a BH practitioner should show Medical COI requirements. |
| **`BoardCertificationsStep`** | OmniScript Step | Board cert verification must match the new specialty type. Medical board certs differ from BH board certs. |
| **`VerifyPractitionerRole`** | OmniScript Step | Taxonomy/role assignment at Practice Location level — must create new `HealthcareProviderTaxonomy` and `HealthcarePractitionerFacility` records for the Medical taxonomy, separate from existing BH records. |
| **`DRTransformPSVScreenData`** | DataRaptor Transform | Ensure PSV data transformation uses current CM's taxonomy data, not existing credential data. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| **DRTransformPSVScreenData** | DR Transform | Current CM data | PSV screen payload | Filter to current CM's taxonomy grouping only |
| **DRTransformReCredData** | DR Transform | Recred context | Recred PSV payload | Scope to current credentialing type's taxonomy |
| **IPValidateCAQHAppReviewParent** | IP | NPI, TaxonomyCode | CAQH validation result | Ensure CAQH validation uses new taxonomy code, not existing |
| **IPToCountPrimaryTaxonomy** | IP | AccountId, TaxonomySection | Count of primary taxonomies | Must count per credentialing type — one primary per type is valid |

## Acceptance Criteria

**AC-1 — Correct Taxonomy Verified**

**Given** a PSV Specialist opens the PSV Review for a Medical credentialing case of an existing BH-credentialed practitioner,
**When** the `VerifySpecialty` step loads,
**Then** the specialty verification SHALL show the **Medical** taxonomy code and grouping,
**And** SHALL NOT show or validate the existing BH taxonomy.

---

**AC-2 — Correct COI Requirements**

**Given** the PSV is for a Medical credentialing,
**When** the `CertificateofInsuranceVerification` step loads,
**Then** the `IsGroupBehavioralHealthCOI` formula SHALL evaluate to `false` (because this is a Medical credentialing),
**And** Medical-specific COI requirements SHALL be displayed.

---

**AC-3 — Board Certification for New Specialty**

**Given** the PSV is for a Medical credentialing of a BH practitioner,
**When** the `BoardCertificationsStep` loads,
**Then** Medical board certifications SHALL be required/verified,
**And** existing BH board certifications SHALL NOT be the basis for the Medical verification.

---

**AC-4 — Practice Location Taxonomy Role Assignment**

**Given** the practitioner already has BH taxonomy roles at Practice Location X,
**When** the PSV reviewer assigns the Medical taxonomy role at the same Practice Location X,
**Then** a **new** `HealthcareProviderTaxonomy` record SHALL be created for the Medical taxonomy,
**And** the existing BH `HealthcareProviderTaxonomy` record SHALL remain unchanged,
**And** a new `HealthcarePractitionerFacility` record (RecordType: `PRM_FacilityPractitionerTxNw`) SHALL be created for the Medical taxonomy.

---

**AC-5 — Different Practice Location Supported**

**Given** the practitioner is credentialing for Medical at a different practice than where they have BH,
**When** the service area verification step loads,
**Then** the new practice location SHALL be presented for Medical taxonomy assignment,
**And** the existing BH practice location associations SHALL remain unaffected.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Can previously verified PSV items (NPI, NPDB, sanctions, work history, education) be carried over from the BH credentialing?** Or must every PSV item be re-verified for the Medical credentialing? | Significant time savings if items can be shared | BA / Operations |
| 2 | **Are there different CAQH profile requirements for BH vs Medical?** Does the practitioner need a separate CAQH profile or can the same CAQH ID serve both? | CAQH validation logic | BA / Technical |
| 3 | **For admitting privileges, do BH practitioners credentialing for Medical need hospital-based admitting privileges verification?** Currently, admitting privileges are state-specific (DE requires them). Does the Medical track always require them? | PSV step show/hide logic | BA / Legal |
| 4 | **How should the PSV Summary distinguish between the two credentialing tracks?** Should the summary include a header: "PSV Summary — Medical Credentialing for [Practitioner Name]"? | UI clarity | BA |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_PSVSubOsTxnyRole_English`** | Embedded OmniScript | **HIGH** | Taxonomy role assignment must create separate records for new specialty |
| **`PRM_PSVSubOsWSNPDB_English`** | Embedded OmniScript | **HIGH** | NPI/CAQH/NPDB verification must be scoped to current CM's taxonomy |
| **`VerifySpecialty` / `VerifyCareTaxonomyRD`** | OmniScript Step / DR | **HIGH** | Must verify new taxonomy, not existing |
| **`CertificateofInsuranceVerification`** | OmniScript Step | **MEDIUM** | COI requirements differ by specialty type |
| **`BoardCertificationsStep`** | OmniScript Step | **MEDIUM** | Board cert requirements differ by specialty |
| **`IPToCountPrimaryTaxonomy`** | IP | **MEDIUM** | Primary taxonomy count must be per-credentialing-type |
| **`DRTransformPSVScreenData`** | DR Transform | **MEDIUM** | Filter to current CM's taxonomy data |

---

---

# USER STORY 4: Committee Review — Present Dual Credentialing Context to Committee

**Persona:** Committee Member / Medical Director
**Priority:** P1 (Should-have)
**OmniScript:** `PRM_ReviewInitialCredApplicants_English` (Routine), `PRM_NonRoutineCommitteeReview_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** Committee Member or Medical Director reviewing credentialing applications,
**I want** the Committee Review to clearly indicate when a practitioner is seeking dual credentialing (e.g., Medical in addition to existing BH), showing both the current credentialing type under review and the existing credential,
**So that** I can make an informed approve/deny/pend decision with full context of the practitioner's credentialing history and dual-track status.

**Why it matters:** During committee meetings, reviewers see a list of applicants in the `RoutineCredCommitteeTable`. If a practitioner appears for Medical credentialing and is already credentialed as BH, the committee needs to understand this is not a re-credentialing or duplicate — it is a new specialty track. Without this context, the committee may question why a credentialed practitioner is appearing for review again.

## Technical Section (For Developers)

### Current State (from codebase)

- **`PRM_ReviewInitialCredApplicants_English`**: Contains `RoutineCredCommitteeTable` (Edit Block in Table mode) — similar to the HACAC `HACACCommitteeTable`. Displays applicants with decision radios (Approve/Deny/Pend).
- **`PRM_NonRoutineCommitteeReview_English`**: For non-routine committee cases. Contains `CaseStatus`, `DenialReason`, `DecisionDate`, etc. Has specific recred branches (`CaseStatusRecred`, `RecredDueDate`).
- **`SetQCReadyForCommittee`** flag: Set in the QC step of `PRM_RecredQC_English` to route the case to committee.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`RoutineCredCommitteeTable`** | Edit Block | Add a "Credentialing Type" column (BH / Medical) and a "Dual Credentialing" indicator column (Yes/No). When Yes, add tooltip or detail text: *"Also credentialed as [BH/Medical] since [date]"*. |
| **`PRM_NonRoutineCommitteeReview_English`** | OmniScript | Add a Text Block in the case detail section: *"Dual Credentialing: This practitioner is also credentialed as [BH/Medical]."* |
| **IP to Fetch Routine Case Details** | IP | Extend to include other active CMs for the same AccountId with different taxonomy groupings. |

## Acceptance Criteria

**AC-1 — Credentialing Type Column in Committee Table**

**Given** a committee member views the Routine Credentialing Committee table,
**When** a practitioner with dual credentialing (existing BH + new Medical) appears,
**Then** the "Credentialing Type" column SHALL display "Medical",
**And** the "Dual Credentialing" column SHALL display "Yes — Also BH".

---

**AC-2 — Non-routine Committee Context**

**Given** a dual-credentialed practitioner's case is routed to non-routine committee review,
**When** the committee reviewer opens the case,
**Then** a text block SHALL display: *"Dual Credentialing Alert: This practitioner is currently credentialed as Behavioral Health and is now seeking Medical credentialing."*

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Should dual-credentialed practitioners be flagged for non-routine committee review by default?** Or should they follow the normal routine/non-routine routing? | Routing logic | Operations / BA |
| 2 | **Does the committee need to see the BH credentialing history** (approval date, committee decision, any past issues) when reviewing the Medical application? | Data scope for committee review | BA / Medical Director |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_ReviewInitialCredApplicants_English`** | OmniScript | **MEDIUM** | New columns in committee table |
| **`PRM_NonRoutineCommitteeReview_English`** | OmniScript | **MEDIUM** | New text block for dual credentialing context |
| **IP for Routine Case Details** | IP | **LOW** | Extended query for other CMs |

---

---

# USER STORY 5: PDA Review & Update — Create Separate Network Records for Dual-Credentialed Specialty

**Persona:** PDM Specialist / Reporting Specialist
**Priority:** P0 (Critical)
**OmniScript:** `PRM_ProviderChangePDAUpdate_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** PDM Specialist or Reporting Specialist performing PDA Review & Update after committee approval,
**I want** the PDA process to create separate practice location taxonomy (`HealthcareProviderTaxonomy`), practice location affiliation (`HealthcarePractitionerFacility`), and network (`HealthcareFacilityNetwork`) records for the Medical credentialing, independent of the existing BH records,
**So that** the practitioner's Medical credential is properly set up in the system with the correct taxonomy, networks, and info codes, without disturbing the existing BH credentialing records.

**Why it matters:** The PDA (Provider Data Administration) step is where the system "loads" the credential into the provider directory — creating practice locations, taxonomy assignments, and network affiliations. For dual credentialing, this is the most technically critical step because:
1. The same practitioner at the same practice location may need two taxonomy records (one BH, one Medical)
2. Network affiliations may differ (BH networks vs Medical networks)
3. Info codes may differ between BH and Medical
4. The old system handled this by having two groups (one Medical, one BH) linked to the appropriate practices

## Technical Section (For Developers)

### Current State (from codebase)

- **`PRM_ProviderChangePDAUpdate_English`** (OmniScript, versions 19-27+): The PDA flow handles Add/Remove practice locations, taxonomy assignments, network creation, COI processing.
  - **Add Practice Location Taxonomy** section: `AddPracPLTaxCareTaxonomy` / `AddPracPPLTaxTaxonomy` — assigns taxonomy to practice locations
  - **Existing Practitioner Location Taxonomy**: `ExistingPracLocToTaxTaxonomy` — shows existing taxonomy assignments
  - **Remove Practice Location Taxonomy**: `RemovePracPLTaxCareTaxonomy` / `RemovePracPPLTaxTaxonomy` — removes taxonomy assignments
  - **CSA (Change Service Area)**: `CSAPLTaxonomy` / `CSAPLTaxonomyExist` — related practice location taxonomy changes
  - **`PRM_ProviderChangePDAUpdatesParent`** IP: Orchestrates all PDA updates including practice location, taxonomy, network, and info code creation
- **Taxonomy Grouping Check**: `IsGroupBehavioralHealthCOI` = `CONTAINS(%addSelect1COI|n%, 'Behavioral Health & Social Service Providers')` — used to determine COI-related fields in PDA
- **`PRM_PNCPDAService`** (Apex): Handles practice location network creation, pending flag management, and info code assignment

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`AddPracPLTaxCareTaxonomy`** | OmniScript Element | When processing a dual-credentialed practitioner, ensure the taxonomy assignment uses the **Medical** taxonomy (from the new CM), not the existing BH taxonomy. Show existing BH taxonomy records as read-only context. |
| **`PRM_ProviderChangePDAUpdatesParent`** | IP | Must create new `HealthcareProviderTaxonomy`, `HealthcarePractitionerFacility`, and `HealthcareFacilityNetwork` records for the Medical taxonomy. Must NOT update or overwrite existing BH records. |
| **`PRM_PNCPDAService`** | Apex | Network creation logic must support multiple taxonomies at the same practice location for the same practitioner. Ensure `PRM_Pending__c` flags are managed per-taxonomy (not per-practitioner). |
| **Info Code Assignment** | Apex / IP | Info codes for Medical may differ from BH. Ensure `PRM_InfoCodeAssignment__c` records are created specific to the Medical taxonomy/network. |
| **COI Verification in PDA** | OmniScript | For Medical PDA, `IsGroupBehavioralHealthCOI` should evaluate to `false` → Medical COI requirements apply. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| **PRM_ProviderChangePDAUpdatesParent** | IP (Parent) | CM data, taxonomy, practice locations | Created records | Must support creating records alongside existing BH records |
| **PRMDRCreatePractitionerLocationTaxonomy** | DR Load | Taxonomy code, PL Id, AccountId | HealthcareProviderTaxonomy record | Must check for existing BH taxonomy at same PL and create Medical alongside it |
| **PRM_PNCPDAService** | Apex | CM, Practice Locations | HFN, HCPF records | Support multiple taxonomies per PL per practitioner |
| **PRM_PNCPracTxnyNetworkBatch** | Batch Apex | CM approval | Taxonomy network records | Must create Medical-specific taxonomy networks |

## Acceptance Criteria

**AC-1 — Separate Taxonomy Records Created**

**Given** a Medical credentialing is approved for a practitioner who already has BH at Practice Location X,
**When** the PDA Review creates taxonomy records,
**Then** a new `HealthcareProviderTaxonomy` record SHALL be created with the Medical taxonomy code,
**And** the existing BH `HealthcareProviderTaxonomy` record SHALL remain active and unchanged.

---

**AC-2 — Separate Network Affiliations**

**Given** the Medical credentialing is approved for an existing BH practitioner,
**When** the PDA creates `HealthcareFacilityNetwork` records,
**Then** Medical-specific network affiliations SHALL be created,
**And** existing BH network affiliations SHALL remain unchanged,
**And** the practitioner SHALL appear in both BH and Medical network directories.

---

**AC-3 — Same Practice Location, Dual Taxonomy**

**Given** a practitioner is BH-credentialed at Practice Location X and now Medical-credentialed at the same location,
**When** the PDA processes the Medical credentialing,
**Then** the practice location SHALL have two sets of `HealthcareProviderTaxonomy` records (one BH, one Medical),
**And** two sets of `HealthcarePractitionerFacility` records (RecordType: `PRM_FacilityPractitionerTxNw`) SHALL exist — one per taxonomy.

---

**AC-4 — Different Practice Location Supported**

**Given** a BH practitioner is credentialing for Medical at Practice Location Y (different from BH at Location X),
**When** the PDA processes the Medical credentialing,
**Then** Medical taxonomy and network records SHALL be created for Practice Location Y only,
**And** BH records at Practice Location X SHALL remain unaffected.

---

**AC-5 — Pending Flags Per-Taxonomy**

**Given** the Medical PDA is processing while the BH credential is already active,
**When** `PRM_Pending__c` flags are set on new Medical records,
**Then** the pending status SHALL only apply to the new Medical records,
**And** existing BH records SHALL NOT be set to pending.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **In the old system, Medical and BH groups were separate. Should the new system also create separate "groups" (Vendor Accounts)?** Or can the same Vendor Account support both BH and Medical taxonomy assignments? | Data model — separate vendor accounts vs shared | BA / Business |
| 2 | **Are there separate contracts for BH vs Medical?** Does the Contract Hierarchy flow (`PRM_ContractHierarchy_English`) need to support dual contracts at the same practice? | Contract and network configuration | BA / Operations |
| 3 | **Should the Supplier Network Creation (`PRM_SupplierNetworkCreation_English`) create separate supplier network entries for BH vs Medical?** | Network management data model | BA / Technical |
| 4 | **What info codes apply specifically to Medical vs BH?** Are they defined in the Decision Matrix or hardcoded in Apex? | Info code assignment logic | BA / Technical |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_ProviderChangePDAUpdate_English`** | OmniScript | **HIGH** | Taxonomy/network assignment must support dual records at same PL |
| **`PRM_ProviderChangePDAUpdatesParent`** | IP | **HIGH** | Create records alongside existing BH records |
| **`PRM_PNCPDAService`** | Apex | **HIGH** | Network creation must support multiple taxonomies per PL per practitioner |
| **`PRM_PNCPracTxnyNetworkBatch`** | Batch Apex | **HIGH** | Taxonomy network batch must handle dual taxonomy |
| **Info Code Assignment** | Apex / IP | **MEDIUM** | Specialty-specific info codes |
| **Contract Hierarchy** | OmniScript / IP | **MEDIUM** | May need separate contracts for BH vs Medical |

---

---

# USER STORY 6: Network Management QC — Verify Both Credentialing Types in QC

**Persona:** Network Management QC Specialist
**Priority:** P1 (Should-have)
**OmniScript:** `PRM_ManualUpdatesQCReview3_English`, `PRM_PNCPDA_English`
**Relevant Requirements:** Nicole Brown business request — BH/Medical dual credentialing

## Story

**As a** Network Management QC Specialist,
**I want** the QC review to show both the Medical and BH taxonomy/network records for a dual-credentialed practitioner, clearly distinguishing which records are new (from the current credentialing) and which are existing (from the prior credentialing),
**So that** I can verify the new Medical records are correct without accidentally modifying or flagging the existing BH records.

**Why it matters:** The Network Management QC queue (`PRM_NetworkManagementQCQueue`) processes cases after PDA completion. For dual-credentialed practitioners, the QC reviewer will see both BH and Medical taxonomy/network records on the same practice location. Without clear labeling, a reviewer may mistake the BH records as duplicates or errors and attempt to remove them.

## Technical Section (For Developers)

### Current State (from codebase)

- **`PRM_ManualUpdatesQCReview3_English`** (OmniScript, version 2): Contains taxonomy and network verification blocks:
  - `TxNw_TaxonomyName` (label: "Care Taxonomy")
  - `TxNw_IsPrimaryTaxonomy` (label: "Is Primary Taxonomy")
  - `Info_PracticeLocationTaxonomyName` (label: "Practice Location Taxonomy")
  - `Participating Practice Location Taxonomy` section
- **`PRM_PNCPDA_English`** (OmniScript): Handles PNC PDA cases, routes to `PRM_NetworkManagementQCQueue`.
- **Queue Routing:** Cases are routed to `PRM_NetworkManagementQCQueue` via Flows (`PRM_PractitionerNPIUpdate`, `PRM_UpdateNPIHistoryUponPLCreation`, etc.) and `PRM_ReCredUpdate_English`.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_ManualUpdatesQCReview3_English`** | OmniScript | Add a "Credentialing Type" column to taxonomy/network display blocks. Label new records as "New — Medical" and existing records as "Existing — BH". Add visual differentiation (e.g., background color or icon). |
| **QC DataRaptors** | DR Extract | Extend to pull taxonomy grouping (`PRM_TaxonomyGrouping__c`) for each taxonomy/network record so the QC reviewer can distinguish BH from Medical. |
| **Validation Logic** | OmniScript / IP | QC validation should only check new Medical records for completeness. Existing BH records should be read-only and excluded from validation. |

## Acceptance Criteria

**AC-1 — Credentialing Type Labeling in QC**

**Given** a Network Management QC Specialist opens a QC case for a dual-credentialed practitioner,
**When** the taxonomy and network records are displayed,
**Then** each record SHALL be labeled with its credentialing type ("BH" or "Medical"),
**And** new records from the current credentialing SHALL be visually distinguished from existing records.

---

**AC-2 — Existing Records Read-Only**

**Given** the QC reviewer sees both BH and Medical records for the same practice location,
**When** reviewing the records,
**Then** existing BH records SHALL be read-only,
**And** only new Medical records SHALL be editable/verifiable.

---

**AC-3 — QC Validation Scoped to Current Credentialing**

**Given** the QC validation runs on the dual-credentialed practitioner's records,
**When** checking for completeness and accuracy,
**Then** validation SHALL only apply to the new Medical records,
**And** SHALL NOT flag existing BH records as incomplete or erroneous.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Should the QC reviewer see ALL taxonomy/network records for the practitioner, or only the ones related to the current credentialing case?** | UI complexity and data scope | BA / Operations |
| 2 | **Are there separate QC queues for BH vs Medical?** Or does the same `PRM_NetworkManagementQCQueue` handle both? | Queue configuration | Operations |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_ManualUpdatesQCReview3_English`** | OmniScript | **MEDIUM** | New credentialing type labels, read-only existing records |
| **QC DataRaptors** | DR Extract | **MEDIUM** | Extended to include taxonomy grouping |
| **`PRM_PNCPDA_English`** | OmniScript | **LOW** | May need minor context updates for dual credentialing |
| **`PRM_NetworkManagementQCQueue`** | Queue | **LOW** | May need separate queue or sub-queue for BH vs Medical |

---

---

# Summary — Cross-Cutting Questions for Business

These questions apply across all user stories and should be resolved before implementation begins:

| # | Question | Impact Across Stories | Owner |
|---|----------|----------------------|-------|
| 1 | **How do we determine if a practitioner is BH?** Is it solely based on `CareTaxonomy.PRM_TaxonomyGrouping__c = "Behavioral Health & Social Service Providers"` vs. other groupings? Is there a definitive field on the Account or NPI record? | US-1 through US-6 — core branching logic | BA / Business |
| 2 | **Is there any change in the credentialing process for dual credentialing vs. standard initial credentialing?** Does a BH practitioner getting Medical credentialing follow the exact same lifecycle (PAR → App Review → PSV → QC → Committee → PDA → NM QC), or are any steps shortened/skipped? | US-1 through US-6 — scope of changes | BA / Operations |
| 3 | **For Physician Assistants (PAs), whose taxonomy is the same for BH and Medical, how should the system handle dual credentialing?** Can a PA even have dual credentialing, or do they only need one? | US-1, US-3 — PA exception handling | BA / Business |
| 4 | **When a practitioner works as BH/Medical at the SAME practice, should they have one or two vendor group records?** In the old system, two groups were created. Should PIE replicate this? | US-5 — PDA data model | BA / Business |
| 5 | **What is the expected volume of dual-credentialing requests?** Is this a handful of cases per quarter, or a regular occurrence? | All stories — priority and architecture complexity | BA / Business |
| 6 | **Should there be a dashboard or report that shows practitioners with dual credentials?** | Reporting — new FlexCard or report | BA / Operations |
| 7 | **For recredentialing (not initial credentialing), should BH and Medical recredentialing cycles be independent?** If a practitioner's BH credential expires but Medical is still active, are they handled separately? | Future scope — `PRM_ReCredentialing` process | BA / Operations |
| 8 | **Is there a regulatory requirement for separate credentialing files?** NCQA or CMS may require separate credentialing files for BH vs Medical for the same practitioner. | Compliance — file management | Legal / Compliance |
| 9 | **Should the FHN Portal be updated to allow providers to indicate they need dual credentialing at intake?** | US-1 — Portal changes (FHN scope) | BA / Product |
| 10 | **What are the example taxonomy codes for Medical vs BH for the example practitioners?** For Sajani Sukhadia (1023309382) and Margaret Oduro (1417443367), what specific Medical taxonomy codes would they need? | US-1, US-3 — validation of approach | BA / Business |

---

## Credentialing Flow Diagram — Dual BH/Medical Track

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     DUAL CREDENTIALING LIFECYCLE                                 │
│                                                                                  │
│  EXISTING: Practitioner NPI 1023309382 — Credentialed as BH                     │
│  NEW:      Same practitioner — Needs Medical credentialing                       │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────┐                    │
│  │ BH Track (EXISTING — No Changes)                         │                    │
│  │ ✅ PAR Approved → ✅ PSV Complete → ✅ QC Done            │                    │
│  │ ✅ Committee Approved → ✅ PDA Complete → ✅ NM QC Done    │                    │
│  │ Status: CREDENTIALED                                      │                    │
│  │ Taxonomy: "Behavioral Health & Social Service Providers"  │                    │
│  │ Practice: Group A (BH practice)                           │                    │
│  └──────────────────────────────────────────────────────────┘                    │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────┐                    │
│  │ Medical Track (NEW — Goes through full lifecycle)         │                    │
│  │                                                           │                    │
│  │  ❶ New PAR  → ❷ App     → ❸ PSV    → ❹ Committee        │                    │
│  │    (US-1)      Review      Review      Review             │                    │
│  │                (US-2)      (US-3)      (US-4)             │                    │
│  │                                                           │                    │
│  │  ❺ PDA Review → ❻ Network Mgmt QC                        │                    │
│  │    & Update       (US-6)                                  │                    │
│  │    (US-5)                                                 │                    │
│  │                                                           │                    │
│  │ Taxonomy: "Medical" (specific grouping TBD)               │                    │
│  │ Practice: Group B (Medical practice) or Group A (same)    │                    │
│  └──────────────────────────────────────────────────────────┘                    │
│                                                                                  │
│  Result: Same NPI, same Account, two IndividualApplications,                     │
│          two sets of taxonomy/network/PL records                                 │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

| Priority | Story | Rationale |
|----------|-------|-----------|
| **Phase 1 (P0)** | US-1: Initiate Dual Credentialing (PAR) | Nothing works without the ability to create a second PAR |
| **Phase 1 (P0)** | US-2: Application Review Context | Reviewers need context immediately after PAR |
| **Phase 1 (P0)** | US-3: PSV for Correct Taxonomy | PSV must verify the right specialty |
| **Phase 1 (P0)** | US-5: PDA Record Creation | PDA creates the actual network/taxonomy records |
| **Phase 2 (P1)** | US-4: Committee Review Context | Committee context is important but not blocking |
| **Phase 2 (P1)** | US-6: NM QC for Dual Records | QC labeling is important but not blocking |

---

*Generated using User Story Architect approach — PNM vertical, OmniStudio component mapping, Gherkin acceptance criteria.*
