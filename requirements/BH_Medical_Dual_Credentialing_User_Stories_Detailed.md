# Behavioral Health ↔ Medical Dual Credentialing — Detailed User Stories

**Business Sponsor:** Nicole Brown
**Epic:** BH-MED-DUAL-CRED
**Date Created:** 2026-04-01
**Priority:** P0 (Critical)
**Target Release:** TBD

---

## Table of Contents

1. [Epic Overview](#epic-overview)
2. [Business Context](#business-context)
3. [User Stories](#user-stories)
   - [US-1: Submit New PAR for Different Specialty Type](#us-1-submit-new-par-for-different-specialty-type)
   - [US-2: Review Dual-Credentialed Application](#us-2-review-dual-credentialed-application)
   - [US-3: Verify Primary Sources for Correct Taxonomy](#us-3-verify-primary-sources-for-correct-taxonomy)
   - [US-4: Committee Review with Dual Context](#us-4-committee-review-with-dual-context)
   - [US-5: Create Provider Data for Dual Taxonomy](#us-5-create-provider-data-for-dual-taxonomy)
   - [US-6: Quality Check Dual-Credentialed Records](#us-6-quality-check-dual-credentialed-records)
4. [Clarifying Questions for Business](#clarifying-questions-for-business)
5. [Appendix: Technical Reference](#appendix-technical-reference)

---

## Epic Overview

### Problem Statement

Practitioners often need to be credentialed for **both** Behavioral Health (BH) and Medical specialties. Examples:
- **Sajani Sukhadia** (NPI: 1023309382) — Credentialed as BH, needs Medical credentialing
- **Margaret Oduro** (NPI: 1417443367) — Credentialed as BH, needs Medical credentialing

**Current System Limitation:** The system assumes **one credentialing type per NPI** and blocks submission of a second Practitioner Participation Request (PAR) for the same practitioner.

### Business Value

**Why This Matters:**
- Practitioners can serve **both** BH and Medical patients
- Same practitioner may work at **different practices** (one BH, one Medical) OR the **same practice** in dual roles
- Taxonomy codes differ between BH and Medical (except Physician Assistants)
- In the legacy system, two separate groups were created — PIE must support this workflow

### Success Criteria

✅ A practitioner credentialed as BH can submit a new PAR for Medical credentialing
✅ Both BH and Medical credentialing tracks exist independently
✅ At the same practice location, both BH and Medical taxonomies are supported
✅ Network directories show the practitioner in both BH and Medical networks
✅ Existing BH credentialing remains unchanged when Medical credentialing is added

---

## Business Context

### How BH vs Medical is Determined

The system uses the **Taxonomy Grouping** field on the Care Taxonomy:

| Taxonomy Grouping | Type |
|-------------------|------|
| `"Behavioral Health & Social Service Providers"` | **BH** |
| All other groupings (e.g., "Allopathic & Osteopathic Physicians", "Physician Assistants", etc.) | **Medical** |

This drives:
- BH-specific questions (e.g., "Are any of the practitioner's groups telehealth only?")
- COI (Certificate of Insurance) requirements (different for BH vs Medical)
- Committee review criteria
- Network assignments

### Data Model Overview

| Object | Purpose | Dual Credentialing Impact |
|--------|---------|---------------------------|
| **Account** (RecordType: PRM_Practitioner) | Practitioner person — one per NPI | ✅ **Shared** between BH and Medical |
| **IndividualApplication** (Case Manager) | One per credentialing request | 🔧 **Two records** needed (one BH, one Medical) |
| **HealthcareProviderTaxonomy** | Practitioner's specialty at a practice location | 🔧 **Two records** at same location (one BH, one Medical) |
| **HealthcarePractitionerFacility** | Practitioner ↔ Practice Location link | 🔧 **Two records** per location (one per taxonomy) |
| **HealthcareFacilityNetwork** | Network participation | 🔧 **Two records** (BH networks, Medical networks) |

---

## User Stories

---

## US-1: Submit New PAR for Different Specialty Type

**Epic:** BH-MED-DUAL-CRED
**Priority:** P0 (Critical)
**Story Points:** 13
**Assignee:** TBD

### User Story

**As a** Credentialing Specialist,
**I want** to submit a new Practitioner Participation Request (PAR) for an existing practitioner who is already credentialed under one specialty type (e.g., BH) but now needs credentialing under a different specialty type (e.g., Medical),
**So that** the practitioner can be separately credentialed for both BH and Medical, allowing them to practice under the appropriate taxonomy at one or more practice locations.

### Business Context

**Why This is Needed:**
- Practitioners like Sajani Sukhadia (NPI: 1023309382) are credentialed as BH but also need Medical credentialing
- Today, the system rejects a second PAR for the same NPI as a "duplicate"
- The specialist cannot proceed, blocking the dual-credentialing workflow entirely

**Current Behavior (Blocks Workflow):**
1. Specialist enters NPI 1023309382 (already credentialed as BH)
2. System finds existing Case Manager
3. System displays error: "Duplicate application — practitioner already has active credentialing"
4. **BLOCKED** — Cannot proceed

**Desired Behavior (Allows Workflow):**
1. Specialist enters NPI 1023309382 (already credentialed as BH)
2. System finds existing Case Manager **with BH taxonomy**
3. System recognizes **new** PAR is for **Medical taxonomy** (different from BH)
4. System displays notification: "⚠️ This practitioner already has BH credentialing. You are initiating a NEW Medical credentialing request."
5. Specialist confirms and proceeds
6. New Case Manager created for Medical (separate from BH)

### Acceptance Criteria

#### AC-1: Existing Credentialing Detection

**Given** a practitioner is already credentialed as "Behavioral Health & Social Service Providers" (e.g., NPI 1023309382),
**When** a Credentialing Specialist opens the Practitioner Participation Form and enters the same NPI with a **Medical specialty taxonomy**,
**Then** the system SHALL:
- Display a notification banner:
  ```
  ⚠️ DUAL CREDENTIALING NOTICE

  This practitioner already has an active credentialing:

  Type: Behavioral Health
  Status: Credentialed
  Approved: 03/15/2025

  You are initiating a NEW Medical credentialing request.
  ```
- Allow the specialist to proceed with the PAR submission

**Verification:**
- PAR form does NOT display duplicate error
- PAR form allows "Next" / "Submit" buttons to be clicked

---

#### AC-2: Separate Case Manager Created

**Given** the specialist submits the new PAR with a Medical specialty for an existing BH-credentialed practitioner,
**When** the system processes the PAR (via `PRM_PractitionerScreenRecordCreation` Integration Procedure),
**Then** the system SHALL:
- Create a **new** `IndividualApplication` (Case Manager) record with:
  - RecordType: `PRM_PractitionerParticipationRequest`
  - Linked to the **same** practitioner `Account` (same NPI)
  - **Distinct** specialty/taxonomy grouping (Medical vs BH)
  - **New** Case Manager number (e.g., "APP-67890" vs existing "APP-12345")
- **NOT** update or modify the existing BH Case Manager

**Verification Query (Salesforce):**
```sql
SELECT Id, Name, PRM_PractitionerAccount__r.NPI__c,
       PRM_PractitionerSpecialty__c, PRM_TaxonomyGrouping__c, Status
FROM IndividualApplication
WHERE PRM_PractitionerAccount__r.NPI__c = '1023309382'
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
ORDER BY CreatedDate DESC
```

**Expected Result:**
```
| CM Name    | NPI         | Specialty           | Taxonomy Grouping | Status      |
|------------|-------------|---------------------|-------------------|-------------|
| APP-67890  | 1023309382  | Family Medicine     | Medical           | In-Progress |
| APP-12345  | 1023309382  | Clinical Psych      | BH & Social Svc   | Credentialed|
```

---

#### AC-3: Existing Credentialing Unaffected

**Given** a new Medical PAR is created for an existing BH-credentialed practitioner,
**When** the new Case Manager is created and moves through the credentialing lifecycle,
**Then** the system SHALL:
- Keep the existing BH Case Manager **Status = "Credentialed"** (unchanged)
- Keep the existing BH `HealthcareProviderTaxonomy` records (unchanged)
- Keep the existing BH `HealthcarePractitionerFacility` records (unchanged)
- Keep the existing BH `HealthcareFacilityNetwork` records (unchanged)

**Verification:**
- BH Case Manager still shows "Credentialed" status
- BH network participation records still show "Active" status

---

#### AC-4: Same Practice Location Supported

**Given** a practitioner needs both BH and Medical credentialing at the **same practice location** (e.g., "Main Street Clinic"),
**When** the specialist submits the new PAR with the same practice group but a different specialty,
**Then** the system SHALL:
- Create a **new** Case Manager linked to the **same** practice (vendor Account)
- Create a **new** taxonomy association for Medical at "Main Street Clinic"
- Keep the existing BH taxonomy association at "Main Street Clinic"

**Result:** Practice Location "Main Street Clinic" has **two** taxonomy records for this practitioner (one BH, one Medical)

---

#### AC-5: Physician Assistant Exception

**Given** a practitioner with a **Physician Assistant** taxonomy (which is the same for both BH and Medical per the business rule),
**When** the specialist attempts to submit a new PAR for the other specialty type,
**Then** the system SHALL display a warning:
```
⚠️ PHYSICIAN ASSISTANT TAXONOMY WARNING

Physician Assistant taxonomy is the same for BH and Medical.
Please confirm this is a NEW credentialing request and not a duplicate.

☐ Yes, I confirm this is a new request for a different practice or role
```
**And** the specialist must check the confirmation box before proceeding.

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_PractitionerParticipationForm_English** | OmniScript | Add detection + notification for existing credentialing |
| **PRMDRCheckExistingCredentialingType** | DataRaptor Extract (NEW) | Query existing IndividualApplications for same NPI |
| **PRM_PractitionerScreenRecordCreation** | Integration Procedure | Update duplicate detection to allow different taxonomy groupings |
| **PRMDRCreateIndividualApplication** | DataRaptor Load | Create second Case Manager without error |

#### Technical Spec: PRMDRCheckExistingCredentialingType

**Type:** DataRaptor Extract
**Purpose:** Check if practitioner already has active credentialing(s)

**Input:**
```json
{
  "AccountId": "%FetchExistingNPIInfo:AccountId%",
  "NPINumber": "%PractitionerIndividualNPI%"
}
```

**SOQL Query:**
```sql
SELECT Id, Name, Status, PRM_PractitionerSpecialty__c,
       PRM_TaxonomyGrouping__c, PRM_ApprovedDate__c,
       PRM_FormType__c, PRM_CredentialingStatus__c
FROM IndividualApplication
WHERE PRM_PractitionerAccount__c = :AccountId
  AND Status IN ('Active', 'Credentialed', 'In-Progress')
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
ORDER BY CreatedDate DESC
```

**Output Node:**
```json
{
  "ExistingCredentialings": [
    {
      "CMId": "0Hx...",
      "CMName": "APP-12345",
      "TaxonomyGrouping": "Behavioral Health & Social Service Providers",
      "Status": "Credentialed",
      "ApprovedDate": "2025-03-15"
    }
  ],
  "HasExistingCredentialing": true,
  "ExistingCredentialingType": "Behavioral Health"
}
```

**DataRaptor Formula (Output Transform):**
```javascript
// ExistingCredentialingType
IF(CONTAINS(%TaxonomyGrouping%, "Behavioral Health"),
   "Behavioral Health",
   "Medical")

// HasExistingCredentialing
%ExistingCredentialings|n% > 0
```

#### Technical Spec: Update Duplicate Detection Logic

**Component:** `PRM_PractitionerScreenRecordCreation` Integration Procedure

**Location:** Action sequence after input validation

**Current Logic (TO REPLACE):**
```javascript
// Current — blocks ANY duplicate for same NPI
Step: "Check Duplicate"
  Query IndividualApplication WHERE AccountId = :inputAccountId
                                AND Status = 'Active'
  IF (result.count > 0) {
      SET ErrorMessage = "Duplicate application — practitioner already has active credentialing"
      STOP with ERROR
  }
```

**New Logic (TO IMPLEMENT):**
```javascript
// New — only block duplicate for SAME taxonomy grouping
Step: "Check Duplicate By Taxonomy"
  // Get current PAR's taxonomy grouping from specialty selection
  SET currentTaxonomyGrouping = %ProviderSpecialty-Block:Grouping%

  // Query existing CMs for this practitioner
  Query IndividualApplication
    WHERE AccountId = :inputAccountId
      AND Status IN ('Active', 'Credentialed', 'In-Progress')
      AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'

  // Check if any existing CM has the SAME taxonomy grouping
  SET isDuplicate = false
  FOR EACH existingCM IN queryResults {
      // Get taxonomy grouping from existing CM's specialty
      Query HealthcareProviderTaxonomy
        WHERE HealthcareProvider__c = :existingCM.PRM_PractitionerAccount__c
        LIMIT 1

      IF (existingTaxonomyGrouping == currentTaxonomyGrouping) {
          SET isDuplicate = true
          SET duplicateType = currentTaxonomyGrouping
          BREAK
      }
  }

  // Only error if SAME taxonomy grouping already exists
  IF (isDuplicate) {
      SET ErrorMessage = "Duplicate application — practitioner already has active "
                       + duplicateType + " credentialing"
      STOP with ERROR
  }

  // If we reach here, different taxonomy grouping → ALLOW
```

#### OmniScript Element Specs

**Element Name:** `ExistingCredentialingNotification`
**Type:** Text Block
**Parent:** `PractitionerForm` step
**Sequence:** After `FetchExistingNPIInfo`, before `PractitionerFirstName`

**Show Condition:**
```javascript
%PRMDRCheckExistingCredentialingType:HasExistingCredentialing% == true
```

**HTML Content:**
```html
<div class="slds-notify slds-notify_alert slds-theme_alert-texture slds-theme_warning" role="alert">
  <span class="slds-assistive-text">warning</span>
  <h2 class="slds-text-heading_small">
    ⚠️ DUAL CREDENTIALING NOTICE
  </h2>
  <p class="slds-m-top_x-small">
    This practitioner already has an active credentialing:
  </p>
  <ul class="slds-list_dotted slds-m-top_x-small">
    <li><strong>Type:</strong> {{ExistingCredentialingType}}</li>
    <li><strong>Status:</strong> {{ExistingCredentialingStatus}}</li>
    <li><strong>Approved:</strong> {{ExistingCredentialingDate}}</li>
  </ul>
  <p class="slds-m-top_small">
    You are initiating a <strong>NEW {{CurrentCredentialingType}} credentialing request</strong>.
  </p>
</div>
```

**Element Name:** `PAExceptionWarning`
**Type:** Text Block + Checkbox
**Show Condition:**
```javascript
%ProviderRole% == "Physician Assistant"
&&
%PRMDRCheckExistingCredentialingType:HasExistingCredentialing% == true
```

**Content:**
```html
<div class="slds-notify slds-notify_alert slds-theme_warning" role="alert">
  <h2 class="slds-text-heading_small">
    ⚠️ PHYSICIAN ASSISTANT TAXONOMY WARNING
  </h2>
  <p class="slds-m-top_x-small">
    Physician Assistant taxonomy is the same for BH and Medical.<br>
    Please confirm this is a NEW credentialing request and not a duplicate.
  </p>
</div>
```

**Checkbox Element:**
```json
{
  "Name": "PAConfirmNewRequest",
  "Type": "Checkbox",
  "Label": "Yes, I confirm this is a new request for a different practice or role",
  "Required": true,
  "Show": "%PAExceptionWarning% is visible"
}
```

---

## US-2: Review Dual-Credentialed Application

**Epic:** BH-MED-DUAL-CRED
**Priority:** P0 (Critical)
**Story Points:** 8
**Assignee:** TBD

### User Story

**As a** Credentialing Specialist performing Application Review,
**I want** the Application Review step to clearly display which credentialing type (BH or Medical) is being reviewed, and show the practitioner's other active credentialing status,
**So that** I can accurately review the application in the context of the correct specialty type without confusion about the practitioner's existing credentials.

### Business Context

**Why This is Needed:**
- When a practitioner has **two active Case Managers** (one BH, one Medical), the Application Review must show context
- Reviewers need to know: "This practitioner is already credentialed for BH and is now going through Medical"
- Without this context, reviewers may apply BH-specific review criteria to a Medical application (or vice versa)

**Example Scenario:**
- Practitioner: Sajani Sukhadia (NPI: 1023309382)
- **Existing:** BH credentialing at Group A — Status: Credentialed (approved 2025-03-15)
- **New:** Medical credentialing at Group B — Status: In-Progress (App Review)

**What the Reviewer Needs to See:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREDENTIALING TYPE: MEDICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ EXISTING CREDENTIALING INFORMATION
This practitioner also has: Behavioral Health
Status: Credentialed
Approved Date: 03/15/2025
```

### Acceptance Criteria

#### AC-1: Credentialing Type Header Visible

**Given** a Credentialing Specialist opens the Application Review (`PRM_RecredQC_English` → `ReviewPractitioner` step) for a **Medical PAR** on a practitioner who is already credentialed as BH,
**When** the `ReviewPractitioner` step loads,
**Then** the system SHALL display:
- A **header** at the top of the step:
  ```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CREDENTIALING TYPE: MEDICAL
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ```
- An **info block** below the header:
  ```
  ℹ️ EXISTING CREDENTIALING INFORMATION

  This practitioner also has: Behavioral Health
  Status: Credentialed
  Approved Date: 03/15/2025
  ```

**Verification:**
- Header text changes based on current CM's taxonomy: "BEHAVIORAL HEALTH" or "MEDICAL"
- Info block only shows when other active CM exists for same NPI with different taxonomy

---

#### AC-2: Correct Specialty Branching

**Given** the practitioner's existing credentialing is BH (taxonomy grouping = "Behavioral Health & Social Service Providers"),
**When** the Application Review is for a **Medical specialty**,
**Then** the system SHALL:
- **NOT display** BH-specific fields (e.g., `PractitionerTelehealth` question: "Are any of the practitioner's groups telehealth only?")
- Display **Medical-specific** review criteria
- Use the **current Case Manager's** specialty data, not the Account-level existing specialty

**Verification:**
- BH telehealth question does NOT appear for Medical review
- Medical-specific fields appear (if any)

---

#### AC-3: Reverse Direction Supported

**Given** a **Medical-credentialed** practitioner submits a new PAR for **BH credentialing**,
**When** the Application Review loads,
**Then** the system SHALL display:
- Header: `CREDENTIALING TYPE: BEHAVIORAL HEALTH`
- Info block: `This practitioner also has: Medical — Status: Credentialed`
- BH-specific fields (telehealth question, BH-specific COI)

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_RecredQC_English** → **ReviewPractitioner** step | OmniScript Step | Add credentialing type header + other credentialing info block |
| **IPFetchParInformation** | Integration Procedure | Extend to query other active CMs for same AccountId with different taxonomy |
| **PRMDRFetchOtherCredentialingStatus** | DataRaptor Extract (NEW) | Fetch other credentialing track info |
| **SetPractitionerSpecialtyFields** | Set Values | Ensure specialty fields use CURRENT CM's taxonomy, not Account-level |

#### Technical Spec: PRMDRFetchOtherCredentialingStatus

**Type:** DataRaptor Extract
**Purpose:** Get other active credentialing(s) for the same practitioner

**Input:**
```json
{
  "AccountId": "%CaseManager:PRM_PractitionerAccount__c%",
  "CurrentCMId": "%CaseManager:Id%"
}
```

**SOQL Query:**
```sql
SELECT Id, Name, Status, PRM_PractitionerSpecialty__c,
       PRM_TaxonomyGrouping__c, PRM_ApprovedDate__c,
       (SELECT Id, TaxonomyGrouping__c FROM HealthcareProviderTaxonomies__r LIMIT 1)
FROM IndividualApplication
WHERE PRM_PractitionerAccount__c = :AccountId
  AND Id != :CurrentCMId
  AND Status IN ('Active', 'Credentialed')
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
ORDER BY CreatedDate DESC
```

**Output:**
```json
{
  "OtherCredentialingInfo": {
    "CMId": "0Hx...",
    "CMName": "APP-12345",
    "TaxonomyGrouping": "Behavioral Health & Social Service Providers",
    "Status": "Credentialed",
    "ApprovedDate": "2025-03-15",
    "Type": "Behavioral Health"
  },
  "HasOtherCredentialing": true
}
```

#### OmniScript Element Specs

**Element Name:** `CredentialingTypeHeader`
**Type:** Text Block
**Parent:** `ReviewPractitioner` step
**Sequence:** 1 (top of step)

**Content:**
```html
<div class="slds-box slds-theme_shade slds-m-bottom_small" style="border-left: 4px solid #0070d2;">
  <h1 class="slds-text-heading_medium slds-text-align_center">
    CREDENTIALING TYPE: {{CurrentCredentialingType}}
  </h1>
</div>
```

**Formula (CurrentCredentialingType):**
```javascript
IF(CONTAINS(%CaseManager:TaxonomyGrouping%, "Behavioral Health"),
   "BEHAVIORAL HEALTH",
   "MEDICAL")
```

**Element Name:** `OtherCredentialingInfoBlock`
**Type:** Text Block
**Show Condition:**
```javascript
%PRMDRFetchOtherCredentialingStatus:HasOtherCredentialing% == true
```

**Content:**
```html
<div class="slds-notify slds-notify_toast slds-theme_info" role="status">
  <span class="slds-icon_container slds-icon-utility-info">
    <svg class="slds-icon slds-icon_small" aria-hidden="true">
      <use xlink:href="/assets/icons/utility-sprite/svg/symbols.svg#info"></use>
    </svg>
  </span>
  <div class="slds-notify__content">
    <h2 class="slds-text-heading_small">
      ℹ️ EXISTING CREDENTIALING INFORMATION
    </h2>
    <p class="slds-m-top_x-small">
      This practitioner also has: <strong>{{OtherCredentialingType}}</strong><br>
      Status: {{OtherCredentialingStatus}}<br>
      Approved Date: {{OtherApprovedDate}}
    </p>
  </div>
</div>
```

---

## US-3: Verify Primary Sources for Correct Taxonomy

**Epic:** BH-MED-DUAL-CRED
**Priority:** P0 (Critical)
**Story Points:** 13
**Assignee:** TBD

### User Story

**As a** PSV (Primary Source Verification) Specialist,
**I want** the PSV review to correctly verify primary sources specific to the credentialing type (BH or Medical), using the appropriate taxonomy and specialty criteria,
**So that** I can complete the PSV for the Medical credentialing of a BH practitioner (or vice versa) with the correct verification steps, board certifications, and specialty-specific checks.

### Business Context

**Why This is Needed:**
- BH and Medical have **different PSV requirements**:
  - Different board certifications
  - Potentially different DEA/CDS requirements
  - Different specialty verifications
  - Different admitting privileges rules
- The taxonomy code drives which care specialties are verified
- For a dual-credentialed practitioner, the **new** taxonomy (not the existing one) must be the focus of PSV

**Example:**
- Practitioner: Margaret Oduro (NPI: 1417443367)
- **Existing BH credentialing:**
  - Board Cert: American Board of Psychiatry and Neurology
  - COI: BH-specific insurance
  - Taxonomy: 103T00000X (Psychologist, Clinical)
- **New Medical credentialing:**
  - Board Cert: American Board of Family Medicine (different!)
  - COI: Medical-specific insurance
  - Taxonomy: 207Q00000X (Family Medicine)

**Critical:** PSV must verify the **Medical** board cert, not assume the BH board cert is sufficient.

### Acceptance Criteria

#### AC-1: Correct Taxonomy Verified

**Given** a PSV Specialist opens the PSV Review (`PRM_RecredQC_English` → PSV steps) for a **Medical credentialing** case of an existing BH-credentialed practitioner,
**When** the `VerifySpecialty` step loads,
**Then** the system SHALL:
- Display the **Medical** taxonomy code and grouping (e.g., "207Q00000X — Family Medicine")
- **NOT** display or validate the existing BH taxonomy (e.g., "103T00000X — Psychologist")

**Verification:**
- PSV specialty screen shows current CM's taxonomy only
- Existing BH taxonomy does not appear in specialty verification

---

#### AC-2: Correct COI Requirements

**Given** the PSV is for a **Medical credentialing**,
**When** the `CertificateofInsuranceVerification` step loads,
**Then** the system SHALL:
- Evaluate the `IsGroupBehavioralHealthCOI` formula against the **current CM's taxonomy** (not Account-level data)
- For Medical credentialing: `IsGroupBehavioralHealthCOI` = `false` → Display **Medical-specific COI** requirements
- For BH credentialing: `IsGroupBehavioralHealthCOI` = `true` → Display **BH-specific COI** requirements

**Verification:**
- Medical PSV shows Medical COI fields
- BH PSV shows BH COI fields

---

#### AC-3: Board Certification for New Specialty

**Given** the PSV is for a **Medical credentialing** of a BH practitioner,
**When** the `BoardCertificationsStep` loads,
**Then** the system SHALL:
- Require verification of **Medical board certifications** (e.g., American Board of Family Medicine)
- **NOT** use existing BH board certifications (e.g., American Board of Psychiatry) as the basis for Medical verification

**Verification:**
- PSV Specialist must enter/verify Medical board cert
- Existing BH board cert does not auto-populate for Medical PSV

---

#### AC-4: Practice Location Taxonomy Role Assignment

**Given** the practitioner already has BH taxonomy roles at Practice Location X,
**When** the PSV reviewer assigns the **Medical taxonomy role** at the **same Practice Location X**,
**Then** the system SHALL:
- Create a **NEW** `HealthcareProviderTaxonomy` record for Medical taxonomy at Location X
- Keep the existing BH `HealthcareProviderTaxonomy` record at Location X (unchanged, still active)
- Create a **NEW** `HealthcarePractitionerFacility` record (RecordType: `PRM_FacilityPractitionerTxNw`) for Medical taxonomy

**Result:** Practice Location X has **TWO** taxonomy records for this practitioner:
```
| Practitioner     | Practice Location | Taxonomy Grouping | IsPrimary |
|------------------|-------------------|-------------------|-----------|
| Margaret Oduro   | Location X        | BH & Social Svc   | true      |
| Margaret Oduro   | Location X        | Medical           | true      |
```

**Verification Query:**
```sql
SELECT Id, HealthcareProvider__r.Name, HealthcareFacility__r.Name,
       TaxonomyCode__c, TaxonomyGrouping__c, IsPrimary__c
FROM HealthcareProviderTaxonomy
WHERE HealthcareProvider__r.NPI__c = '1417443367'
  AND HealthcareFacility__r.Name = 'Location X'
ORDER BY TaxonomyGrouping__c
```

---

#### AC-5: Different Practice Location Supported

**Given** the practitioner is credentialing for Medical at Practice Location Y (different from BH at Location X),
**When** the service area verification step loads,
**Then** the system SHALL:
- Present the **new practice location** (Location Y) for Medical taxonomy assignment
- Keep the existing BH practice location (Location X) associations unchanged

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_PSVSubOsTxnyRole_English** → **VerifySpecialty** | OmniScript Step | Verify CURRENT CM's taxonomy, not Account-level existing taxonomy |
| **CertificateofInsuranceVerification** | OmniScript Step | COI formula must use CURRENT CM's taxonomy grouping |
| **BoardCertificationsStep** | OmniScript Step | Board cert requirements based on CURRENT CM's specialty |
| **VerifyPractitionerRole** | OmniScript Step | Create NEW taxonomy records, do NOT update existing |
| **DRTransformPSVScreenData** | DataRaptor Transform | Filter to CURRENT CM's taxonomy data only |

#### Technical Spec: Update VerifySpecialty Logic

**Component:** `PRM_PSVSubOsTxnyRole_English` → `VerifySpecialty` step

**Current Logic (TO REPLACE):**
```javascript
// Current — pulls ANY taxonomy from Account
Query HealthcareProviderTaxonomy
  WHERE HealthcareProvider__c = :practitionerAccountId
  ORDER BY IsPrimary__c DESC
  LIMIT 1

SET TaxonomyToVerify = queryResult[0]
```

**New Logic (TO IMPLEMENT):**
```javascript
// New — pulls taxonomy from CURRENT CM only
// Option 1: CM has direct link to requested taxonomy
SET TaxonomyToVerify = %CaseManager:PRM_RequestedTaxonomy__c%

// Option 2: Derive from specialty selection in PAR
Query CareTaxonomy
  WHERE Id = %CaseManager:PRM_PrimarySpecialty__c%

SET TaxonomyToVerify = queryResult.TaxonomyCode__c
SET TaxonomyGrouping = queryResult.PRM_TaxonomyGrouping__c
```

#### Technical Spec: Update COI Formula

**Component:** `IsGroupBehavioralHealthCOI` formula

**Current Formula (TO REPLACE):**
```javascript
// Current — checks Account-level data or group selection
CONTAINS(%addSelect1COI|n%, 'Behavioral Health & Social Service Providers')
```

**New Formula (TO IMPLEMENT):**
```javascript
// New — checks CURRENT CM's taxonomy grouping
CONTAINS(%CaseManager:TaxonomyGrouping%, 'Behavioral Health & Social Service Providers')

// Alternative: If taxonomy grouping not stored on CM, derive from specialty
CONTAINS(%DRTransformPSVScreenData:CurrentTaxonomyGrouping%, 'Behavioral Health')
```

#### Technical Spec: Create Separate Taxonomy Records

**Component:** `VerifyPractitionerRole` step → Backend Apex/IP

**Apex Logic (TO IMPLEMENT):**
```java
// Get current CM's taxonomy info
String currentTaxonomyCode = cm.PRM_RequestedTaxonomy__c;
String currentTaxonomyGrouping = cm.PRM_TaxonomyGrouping__c;

// Query existing taxonomies at this practice location
List<HealthcareProviderTaxonomy> existingTaxonomies =
    [SELECT Id, TaxonomyCode__c, TaxonomyGrouping__c, IsPrimary__c
     FROM HealthcareProviderTaxonomy
     WHERE HealthcareProvider__c = :practitionerId
       AND HealthcareFacility__c = :practiceLocationId];

// Check if CURRENT taxonomy grouping already exists
Boolean currentGroupingExists = false;
for (HealthcareProviderTaxonomy existing : existingTaxonomies) {
    if (existing.TaxonomyGrouping__c == currentTaxonomyGrouping) {
        currentGroupingExists = true;
        break;
    }
}

// Only create if this taxonomy grouping doesn't exist yet
if (!currentGroupingExists) {
    HealthcareProviderTaxonomy newTaxonomy = new HealthcareProviderTaxonomy(
        HealthcareProvider__c = practitionerId,
        HealthcareFacility__c = practiceLocationId,
        TaxonomyCode__c = currentTaxonomyCode,
        TaxonomyGrouping__c = currentTaxonomyGrouping,
        IsPrimary__c = true,  // Can be primary for this grouping
        EffectiveFrom__c = Date.today(),
        Status__c = 'Active'
    );
    insert newTaxonomy;

    // Also create corresponding HealthcarePractitionerFacility
    HealthcarePractitionerFacility newPracFac = new HealthcarePractitionerFacility(
        RecordTypeId = Schema.SObjectType.HealthcarePractitionerFacility
                        .getRecordTypeInfosByDeveloperName()
                        .get('PRM_FacilityPractitionerTxNw').getRecordTypeId(),
        HealthcareProvider__c = practitionerId,
        HealthcareFacility__c = practiceLocationId,
        HealthcareProviderTaxonomy__c = newTaxonomy.Id,
        Status__c = 'Active',
        EffectiveFrom__c = Date.today()
    );
    insert newPracFac;
}

// CRITICAL: Do NOT delete or update existing BH taxonomy records
```

---

## US-4: Committee Review with Dual Context

**Epic:** BH-MED-DUAL-CRED
**Priority:** P1 (Should-have)
**Story Points:** 5
**Assignee:** TBD

### User Story

**As a** Committee Member or Medical Director reviewing credentialing applications,
**I want** the Committee Review to clearly indicate when a practitioner is seeking dual credentialing (e.g., Medical in addition to existing BH), showing both the current credentialing type under review and the existing credential,
**So that** I can make an informed approve/deny/pend decision with full context of the practitioner's credentialing history and dual-track status.

### Business Context

**Why This is Needed:**
- During committee meetings, reviewers see a list of applicants in the `RoutineCredCommitteeTable`
- If a practitioner appears for **Medical credentialing** and is already credentialed as **BH**, the committee needs to understand:
  - This is **NOT** a re-credentialing
  - This is **NOT** a duplicate
  - This is a **new specialty track**
- Without this context, the committee may question why a credentialed practitioner is appearing for review again

### Acceptance Criteria

#### AC-1: Credentialing Type Column in Committee Table

**Given** a committee member views the Routine Credentialing Committee table (`PRM_ReviewInitialCredApplicants_English` → `RoutineCredCommitteeTable`),
**When** a practitioner with dual credentialing (existing BH + new Medical) appears in the table,
**Then** the table SHALL display:
- **Column: Credentialing Type** → "Medical"
- **Column: Dual Credentialing** → "Yes — Also BH"

**Table View:**
```
| Practitioner Name  | NPI        | Credentialing Type | Dual Credentialing | Decision |
|--------------------|------------|--------------------|--------------------|----------|
| Margaret Oduro     | 1417443367 | Medical            | Yes — Also BH      | [Approve/Deny/Pend] |
| John Smith         | 1234567890 | BH                 | No                 | [Approve/Deny/Pend] |
```

---

#### AC-2: Non-routine Committee Context

**Given** a dual-credentialed practitioner's case is routed to non-routine committee review (`PRM_NonRoutineCommitteeReview_English`),
**When** the committee reviewer opens the case,
**Then** the system SHALL display a text block:
```
⚠️ DUAL CREDENTIALING ALERT

This practitioner is currently credentialed as Behavioral Health
and is now seeking Medical credentialing.

Existing Credentialing:
- Type: Behavioral Health
- Status: Credentialed
- Approved: 03/15/2025
```

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_ReviewInitialCredApplicants_English** → **RoutineCredCommitteeTable** | Edit Block (Table) | Add "Credentialing Type" and "Dual Credentialing" columns |
| **PRM_NonRoutineCommitteeReview_English** | OmniScript | Add dual credentialing alert text block |
| **IP to Fetch Routine Case Details** | Integration Procedure | Query other active CMs for same AccountId |

#### Technical Spec: Committee Table Columns

**Table:** `RoutineCredCommitteeTable` (Edit Block in Table mode)

**New Column 1:**
```json
{
  "Name": "CredentialingType",
  "Label": "Credentialing Type",
  "Type": "Text",
  "Value": "{{DeriveCredentialingType}}"
}
```

**Formula (DeriveCredentialingType):**
```javascript
IF(CONTAINS(%TaxonomyGrouping%, "Behavioral Health"), "BH", "Medical")
```

**New Column 2:**
```json
{
  "Name": "DualCredentialing",
  "Label": "Dual Credentialing",
  "Type": "Text",
  "Value": "{{DeriveDualCredStatus}}"
}
```

**Formula (DeriveDualCredStatus):**
```javascript
IF(%OtherCredentialingExists% == true,
   "Yes — Also " + %OtherCredentialingType%,
   "No")
```

---

## US-5: Create Provider Data for Dual Taxonomy

**Epic:** BH-MED-DUAL-CRED
**Priority:** P0 (Critical)
**Story Points:** 21
**Assignee:** TBD

### User Story

**As a** PDM (Provider Data Management) Specialist or Reporting Specialist performing PDA Review & Update after committee approval,
**I want** the PDA process to create separate practice location taxonomy (`HealthcareProviderTaxonomy`), practice location affiliation (`HealthcarePractitionerFacility`), and network (`HealthcareFacilityNetwork`) records for the Medical credentialing, independent of the existing BH records,
**So that** the practitioner's Medical credential is properly set up in the system with the correct taxonomy, networks, and info codes, without disturbing the existing BH credentialing records.

### Business Context

**Why This is Critical:**
- The PDA (Provider Data Administration) step is where the system **"loads" the credential** into the provider directory
- Creates practice locations, taxonomy assignments, and network affiliations
- For dual credentialing, this is the **most technically critical step** because:
  1. The same practitioner at the same practice location may need **two taxonomy records** (one BH, one Medical)
  2. Network affiliations may differ (BH networks vs Medical networks)
  3. Info codes may differ between BH and Medical
  4. The old system handled this by having **two groups** (one Medical, one BH) linked to appropriate practices

**Key Rule:** **CREATE new records**, do NOT UPDATE existing records

### Acceptance Criteria

#### AC-1: Separate Taxonomy Records Created

**Given** a Medical credentialing is approved for a practitioner who already has BH at Practice Location X,
**When** the PDA Review creates taxonomy records (`PRM_ProviderChangePDAUpdate_English` → taxonomy assignment steps),
**Then** the system SHALL:
- Create a **NEW** `HealthcareProviderTaxonomy` record with the Medical taxonomy code
- Keep the existing BH `HealthcareProviderTaxonomy` record **active and unchanged**

**Result:** Practice Location X has TWO taxonomy records for this practitioner

**Verification Query:**
```sql
SELECT Id, HealthcareProvider__r.Name, HealthcareFacility__r.Name,
       TaxonomyCode__c, TaxonomyGrouping__c, IsPrimary__c, Status__c
FROM HealthcareProviderTaxonomy
WHERE HealthcareProvider__r.NPI__c = '1023309382'
  AND HealthcareFacility__r.Name = 'Practice Location X'
ORDER BY TaxonomyGrouping__c
```

**Expected Result:**
```
| Practitioner     | Location | Taxonomy Code | Taxonomy Grouping | IsPrimary | Status |
|------------------|----------|---------------|-------------------|-----------|--------|
| Sajani Sukhadia  | X        | 103T00000X    | BH & Social Svc   | true      | Active |
| Sajani Sukhadia  | X        | 207Q00000X    | Medical           | true      | Active |
```

---

#### AC-2: Separate Network Affiliations

**Given** the Medical credentialing is approved for an existing BH practitioner,
**When** the PDA creates `HealthcareFacilityNetwork` records (`PRM_PNCPDAService` Apex class),
**Then** the system SHALL:
- Create **Medical-specific network affiliations** (e.g., "Independence Medical Network")
- Keep existing BH network affiliations (e.g., "Magellan Behavioral Health Network") **unchanged**
- The practitioner SHALL appear in **both** BH and Medical network directories

**Verification Query:**
```sql
SELECT Id, HealthcareProvider__r.Name, HealthcareFacility__r.Name,
       NetworkName__c, TaxonomyGrouping__c, Status__c, EffectiveFrom__c
FROM HealthcareFacilityNetwork
WHERE HealthcareProvider__r.NPI__c = '1023309382'
ORDER BY TaxonomyGrouping__c, NetworkName__c
```

**Expected Result:**
```
| Practitioner     | Location | Network Name               | Taxonomy Grouping | Status |
|------------------|----------|----------------------------|-------------------|--------|
| Sajani Sukhadia  | X        | Magellan BH Network        | BH & Social Svc   | Active |
| Sajani Sukhadia  | X        | Independence Medical Net   | Medical           | Active |
```

---

#### AC-3: Same Practice Location, Dual Taxonomy

**Given** a practitioner is BH-credentialed at Practice Location X and now Medical-credentialed at the **same** location,
**When** the PDA processes the Medical credentialing,
**Then** the practice location SHALL have:
- **Two** `HealthcareProviderTaxonomy` records (one BH, one Medical)
- **Two** `HealthcarePractitionerFacility` records (RecordType: `PRM_FacilityPractitionerTxNw`) — one per taxonomy

---

#### AC-4: Different Practice Location Supported

**Given** a BH practitioner is credentialing for Medical at Practice Location Y (different from BH at Location X),
**When** the PDA processes the Medical credentialing,
**Then** the system SHALL:
- Create Medical taxonomy and network records for Practice Location **Y only**
- Keep BH records at Practice Location **X unchanged**

---

#### AC-5: Pending Flags Per-Taxonomy

**Given** the Medical PDA is processing while the BH credential is already active,
**When** `PRM_Pending__c` flags are set on new Medical records,
**Then** the system SHALL:
- Set pending status **only** on the new Medical records
- **NOT** set existing BH records to pending

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_ProviderChangePDAUpdate_English** | OmniScript | Taxonomy/network assignment must support dual records at same PL |
| **PRM_ProviderChangePDAUpdatesParent** | Integration Procedure | CREATE records alongside existing, do NOT UPDATE existing |
| **PRM_PNCPDAService** | Apex Service | Network creation must support multiple taxonomies per PL per practitioner |
| **PRMDRCreatePractitionerLocationTaxonomy** | DataRaptor Load | Check for existing + create new, do NOT replace |
| **PRM_PNCPracTxnyNetworkBatch** | Batch Apex | Taxonomy network batch must handle dual taxonomy |

#### Technical Spec: Update PRM_ProviderChangePDAUpdatesParent

**Component:** `PRM_ProviderChangePDAUpdatesParent` Integration Procedure

**Current Logic (TO REPLACE — DANGER):**
```javascript
// Current — OVERWRITES existing taxonomy (WRONG for dual credentialing)
Query HealthcareProviderTaxonomy
  WHERE HealthcareProvider__c = :practitionerId
    AND HealthcareFacility__c = :facilityId

IF (queryResult.count > 0) {
    // UPDATE existing taxonomy
    UPDATE HealthcareProviderTaxonomy
    SET TaxonomyCode__c = :newTaxonomyCode
    WHERE Id = :queryResult[0].Id
}
```

**New Logic (TO IMPLEMENT):**
```javascript
// New — CREATE alongside existing, do NOT UPDATE
// Get current CM's taxonomy grouping
SET currentTaxonomyGrouping = %CaseManager:TaxonomyGrouping%

// Query existing taxonomies at this practice location
Query HealthcareProviderTaxonomy
  WHERE HealthcareProvider__c = :practitionerId
    AND HealthcareFacility__c = :facilityId

// Check if CURRENT taxonomy grouping already exists
SET alreadyExists = false
FOR EACH existingTaxonomy IN queryResults {
    IF (existingTaxonomy.TaxonomyGrouping__c == currentTaxonomyGrouping) {
        SET alreadyExists = true
        BREAK
    }
}

// Only create if this taxonomy grouping doesn't exist
IF (!alreadyExists) {
    // CREATE NEW taxonomy record
    INSERT HealthcareProviderTaxonomy {
        HealthcareProvider__c: practitionerId,
        HealthcareFacility__c: facilityId,
        TaxonomyCode__c: newTaxonomyCode,
        TaxonomyGrouping__c: currentTaxonomyGrouping,
        IsPrimary__c: true,  // Can have one primary per grouping
        Status__c: 'Active',
        EffectiveFrom__c: approvalDate
    }
}

// CRITICAL: Existing BH records remain UNCHANGED
```

#### Technical Spec: Update PRM_PNCPDAService

**Component:** `PRM_PNCPDAService` Apex Service (network creation)

**Method:** `createPractitionerNetworks()`

**New Logic (TO IMPLEMENT):**
```java
public static void createPractitionerNetworks(Id caseManagerId,
                                               List<Id> facilityIds) {
    // Get CM with taxonomy info
    IndividualApplication cm = [SELECT Id, PRM_PractitionerAccount__c,
                                 PRM_TaxonomyGrouping__c, PRM_ApprovedDate__c
                                 FROM IndividualApplication WHERE Id = :caseManagerId];

    String currentTaxonomyGrouping = cm.PRM_TaxonomyGrouping__c;

    // For each practice location
    for (Id facilityId : facilityIds) {
        // Check if network already exists for THIS taxonomy grouping
        List<HealthcareFacilityNetwork> existingNetworks =
            [SELECT Id FROM HealthcareFacilityNetwork
             WHERE HealthcareProvider__c = :cm.PRM_PractitionerAccount__c
               AND HealthcareFacility__c = :facilityId
               AND TaxonomyGrouping__c = :currentTaxonomyGrouping];

        // Only create if network for this grouping doesn't exist
        if (existingNetworks.isEmpty()) {
            HealthcareFacilityNetwork newNetwork = new HealthcareFacilityNetwork(
                HealthcareProvider__c = cm.PRM_PractitionerAccount__c,
                HealthcareFacility__c = facilityId,
                TaxonomyGrouping__c = currentTaxonomyGrouping,
                NetworkName__c = deriveNetworkName(currentTaxonomyGrouping, facilityId),
                EffectiveFrom__c = cm.PRM_ApprovedDate__c,
                Status__c = 'Active',
                PRM_Pending__c = true  // Set pending only for new records
            );
            insert newNetwork;
        }
    }

    // CRITICAL: Existing BH networks remain UNCHANGED
}

private static String deriveNetworkName(String taxonomyGrouping, Id facilityId) {
    // Logic to determine network name based on taxonomy grouping and location
    if (taxonomyGrouping.contains('Behavioral Health')) {
        return 'Magellan Behavioral Health Network';
    } else {
        return 'Independence Medical Network';
    }
}
```

---

## US-6: Quality Check Dual-Credentialed Records

**Epic:** BH-MED-DUAL-CRED
**Priority:** P1 (Should-have)
**Story Points:** 8
**Assignee:** TBD

### User Story

**As a** Network Management QC Specialist,
**I want** the QC review to show both the Medical and BH taxonomy/network records for a dual-credentialed practitioner, clearly distinguishing which records are new (from the current credentialing) and which are existing (from the prior credentialing),
**So that** I can verify the new Medical records are correct without accidentally modifying or flagging the existing BH records.

### Business Context

**Why This is Needed:**
- The Network Management QC queue (`PRM_NetworkManagementQCQueue`) processes cases after PDA completion
- For dual-credentialed practitioners, the QC reviewer will see **both BH and Medical** taxonomy/network records on the same practice location
- Without clear labeling, a reviewer may mistake the BH records as duplicates or errors and attempt to remove them

### Acceptance Criteria

#### AC-1: Credentialing Type Labeling in QC

**Given** a Network Management QC Specialist opens a QC case (`PRM_ManualUpdatesQCReview3_English`) for a dual-credentialed practitioner,
**When** the taxonomy and network records are displayed,
**Then** each record SHALL be labeled with:
- **Credentialing Type:** "BH" or "Medical"
- **Record Source:** "NEW — Editable" or "EXISTING — Read-Only"

**Table View:**
```
| Care Taxonomy        | Is Primary | Credentialing Type | Record Source          |
|----------------------|------------|--------------------|------------------------|
| 103T00000X (Psych)   | Yes        | BH                 | EXISTING — Read-Only   |
| 207Q00000X (Fam Med) | Yes        | Medical            | NEW — Editable         |
```

---

#### AC-2: Existing Records Read-Only

**Given** the QC reviewer sees both BH and Medical records for the same practice location,
**When** reviewing the records,
**Then** the system SHALL:
- Make existing BH records **read-only** (grayed out or locked icon)
- Make only new Medical records **editable/verifiable**

---

#### AC-3: QC Validation Scoped to Current Credentialing

**Given** the QC validation runs on the dual-credentialed practitioner's records,
**When** checking for completeness and accuracy,
**Then** validation SHALL:
- Only apply to the **new Medical records**
- **NOT** flag existing BH records as incomplete or erroneous

---

### Technical Details for Developers

#### Component Changes

| Component | Type | Change Required |
|-----------|------|-----------------|
| **PRM_ManualUpdatesQCReview3_English** | OmniScript | Add credentialing type labels, read-only existing records |
| **QC DataRaptors** | DataRaptor Extract | Include taxonomy grouping and CM linkage |
| **Validation Logic** | OmniScript / IP | Scope validation to current CM's records only |

#### Technical Spec: QC Table Enhancements

**Table:** Taxonomy/Network display blocks in `PRM_ManualUpdatesQCReview3_English`

**New Column 1: Credentialing Type**
```json
{
  "Name": "CredentialingType",
  "Label": "Credentialing Type",
  "Value": "{{DeriveCredTypeFromGrouping}}"
}
```

**Formula:**
```javascript
IF(CONTAINS(%TaxonomyGrouping%, "Behavioral Health"), "BH", "Medical")
```

**New Column 2: Record Source**
```json
{
  "Name": "RecordSource",
  "Label": "Record Source",
  "Value": "{{DeriveRecordSource}}"
}
```

**Formula:**
```javascript
// If this taxonomy record was created by the current CM → NEW
// If it was created by a different CM → EXISTING
IF(%TaxonomyRecord.CaseManagerId% == %CurrentCaseManagerId%,
   "NEW — Editable",
   "EXISTING — Read-Only")
```

**Read-Only Logic:**
```javascript
// For each row in the table
SET isReadOnly = (%RecordSource% == "EXISTING — Read-Only")

// Apply to all input fields in that row
IF (isReadOnly) {
    SET fieldReadOnly = true
    SET fieldStyle = "background-color: #f3f3f3; color: #666;"
}
```

---

## Clarifying Questions for Business

**Please answer these questions BEFORE development begins. Failure to resolve these will block implementation.**

---

### Section 1: Core Logic & Taxonomy

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q1** | **How do we determine if a practitioner is BH vs Medical?** Is it solely based on `CareTaxonomy.PRM_TaxonomyGrouping__c = "Behavioral Health & Social Service Providers"` vs. other groupings? Or is there another field on the Account or NPI record? | This is the **core branching logic** for the entire dual-credentialing flow. If there's a different field, all our conditions must use that instead. | **Answer:** _____________ |
| **Q2** | **What are the example taxonomy codes?** For Sajani Sukhadia (1023309382) and Margaret Oduro (1417443367), what specific **Medical taxonomy codes** would they need? (e.g., "207Q00000X" for Family Medicine) | We need real examples to validate our approach and test in sandbox. | **Answer:** _____________ |
| **Q3** | **For Physician Assistants (PAs), whose taxonomy is the same for BH and Medical, can a PA even have dual credentialing?** Or do they only need one credentialing that covers both? | Determines if PA exception logic is needed or if we should block PAs from dual credentialing entirely. | **Answer:** _____________ |

---

### Section 2: Data Model & Records

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q4** | **Should the practitioner Account (`PRM_Practitioner`) have a new field to track credentialing types?** For example, `PRM_CredentialingTypes__c` = "BH;Medical". Or is the presence of multiple `IndividualApplication` records with different taxonomies sufficient? | Determines if we need a data model change to the Account object. | **Answer:** _____________ |
| **Q5** | **Should the Case Manager Name/Number distinguish BH from Medical?** For example, should the `IndividualApplication.Name` include a suffix like "APP-12345-BH" or "APP-12345-MED"? | Affects reporting, identification, and user experience. | **Answer:** _____________ |
| **Q6** | **When a practitioner works as BH/Medical at the SAME practice, should they have one or two vendor group records?** In the old system, two separate groups were created (one Medical, one BH). Should PIE replicate this, or can the same Vendor Account support both? | Critical for PDA data model — separate vendor accounts vs. shared. | **Answer:** _____________ |

---

### Section 3: Process & Workflow

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q7** | **Does dual credentialing follow the exact same lifecycle** (PAR → App Review → PSV → QC → Committee → PDA → NM QC), or are any steps shortened/skipped? For example, does a BH practitioner getting Medical credentialing skip some verification steps? | Determines scope of changes to each step. If steps are skipped, we need different routing logic. | **Answer:** _____________ |
| **Q8** | **Queue routing:** When one NPI has two active Case Managers (BH + Medical), should both go to the same Credentialing Specialist, or different queues for BH vs Medical? | Affects case routing and round-robin logic. | **Answer:** _____________ |
| **Q9** | **Can previously verified PSV items (NPI, NPDB, sanctions, work history, education) be carried over from BH credentialing to Medical?** Or must every PSV item be re-verified from scratch? | Significant time savings if items can be shared; compliance risk if not allowed. | **Answer:** _____________ |

---

### Section 4: Contracts & Networks

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q10** | **Are there separate contracts for BH vs Medical?** Does the Contract Hierarchy flow (`PRM_ContractHierarchy_English`) need to support dual contracts at the same practice? | Determines if contract logic needs updates. | **Answer:** _____________ |
| **Q11** | **What info codes apply specifically to Medical vs BH?** Are they defined in the Decision Matrix or hardcoded in Apex? | Info code assignment logic in PDA. | **Answer:** _____________ |
| **Q12** | **Should the Supplier Network Creation (`PRM_SupplierNetworkCreation_English`) create separate supplier network entries for BH vs Medical?** | Network management data model. | **Answer:** _____________ |

---

### Section 5: Compliance & Volume

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q13** | **Is there a regulatory requirement for separate credentialing files?** NCQA or CMS may require separate credentialing files for BH vs Medical for the same practitioner. | Compliance — file management and record retention. | **Answer:** _____________ |
| **Q14** | **What is the expected volume of dual-credentialing requests?** Is this a handful of cases per quarter, or a regular occurrence (e.g., 10+ per month)? | Determines priority and whether we need performance optimizations (e.g., batch processing, indexes). | **Answer:** _____________ |
| **Q15** | **For the two example practitioners (Sajani Sukhadia - 1023309382, Margaret Oduro - 1417443367), what is their current status?** Are they fully credentialed as BH, or still in-progress? Do they need new PARs or a conversion from existing data? | Determines if this is a migration scenario or new-flow scenario. | **Answer:** _____________ |

---

### Section 6: Forms & User Experience

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q16** | **Does the PAR form need any changes to collect additional BH/Medical-specific information?** For example, separate insurance requirements, different license types? | Form scope and field additions. | **Answer:** _____________ |
| **Q17** | **Should the FHN Portal be updated to allow providers to indicate they need dual credentialing at intake?** Or is this an internal specialist workflow only? | Portal changes (out of scope for PIE, but affects user experience). | **Answer:** _____________ |
| **Q18** | **Should there be a dashboard or report that shows practitioners with dual credentials?** | Reporting requirement — new FlexCard or report. | **Answer:** _____________ |

---

### Section 7: Recredentialing (Future Scope)

| # | Question | Why It Matters | Decision |
|---|----------|----------------|----------|
| **Q19** | **For recredentialing (not initial credentialing), should BH and Medical recredentialing cycles be independent?** If a practitioner's BH credential expires but Medical is still active, are they handled separately? | Future scope — recredentialing process design. | **Answer:** _____________ |
| **Q20** | **Should one credentialing type (BH or Medical) be designated as "primary" for reporting purposes?** Or are they always equal? | Affects reporting and dashboards. | **Answer:** _____________ |

---

## Appendix: Technical Reference

### Key Objects

| Object API Name | Purpose |
|-----------------|---------|
| `Account` (RecordType: `PRM_Practitioner`) | Practitioner person — one per NPI |
| `IndividualApplication` | Case Manager — one per credentialing request |
| `HealthcareProviderTaxonomy` | Taxonomy assignment at practice location |
| `HealthcarePractitionerFacility` | Practitioner ↔ Practice Location link |
| `HealthcareFacilityNetwork` | Network participation |
| `CareTaxonomy` | Taxonomy master data (includes `PRM_TaxonomyGrouping__c`) |

### Key Fields

| Object | Field API Name | Purpose |
|--------|----------------|---------|
| `IndividualApplication` | `PRM_PractitionerAccount__c` | Lookup to practitioner Account |
| `IndividualApplication` | `PRM_PractitionerSpecialty__c` | Primary specialty |
| `IndividualApplication` | `PRM_TaxonomyGrouping__c` | BH vs Medical grouping (may need to add) |
| `HealthcareProviderTaxonomy` | `TaxonomyCode__c` | Taxonomy code (e.g., "207Q00000X") |
| `HealthcareProviderTaxonomy` | `TaxonomyGrouping__c` | BH vs Medical grouping |
| `HealthcareProviderTaxonomy` | `IsPrimary__c` | Primary taxonomy flag |
| `CareTaxonomy` | `PRM_TaxonomyGrouping__c` | "Behavioral Health & Social Service Providers" vs others |

### Key Formulas

| Formula Name | Location | Purpose |
|--------------|----------|---------|
| `SpecialtyGroupingFormula` | PRM_PractitionerParticipationForm_English | Determines if BH specialty |
| `IsGroupBehavioralHealthCOI` | Provider Change Form / PSV | Determines BH-specific COI requirements |

### Key Integration Procedures

| IP Name | Purpose |
|---------|---------|
| `PRM_PractitionerScreenRecordCreation` | Creates IndividualApplication (Case Manager) from PAR |
| `PRM_ProviderChangePDAUpdatesParent` | Orchestrates PDA updates (taxonomy, network, info codes) |
| `IPFetchParInformation` | Fetches PAR context for Application Review |

### Key DataRaptors

| DR Name | Type | Purpose |
|---------|------|---------|
| `PRMDRCheckExistingCredentialingType` | Extract (NEW) | Check existing credentialing for same NPI |
| `PRMDRFetchOtherCredentialingStatus` | Extract (NEW) | Get other active credentialing track |
| `PRMDRCreateIndividualApplication` | Load | Create Case Manager |
| `PRMDRCreatePractitionerLocationTaxonomy` | Load | Create HealthcareProviderTaxonomy |
| `DRTransformPSVScreenData` | Transform | PSV screen data prep |

### Key Apex Classes

| Class Name | Purpose |
|------------|---------|
| `PRM_PNCPDAService` | Network creation and PDA processing |
| `PRM_PNCPracTxnyNetworkBatch` | Batch job for taxonomy network creation |
| `PRM_CDMTriggerHandler` | Case Data Manager trigger handler |

---

**End of User Stories**

*Please complete the Clarifying Questions section and return to the development team before implementation begins.*

---

*Document Created: 2026-04-01*
*Author: Claude Code (AI Assistant)*
*Business Sponsor: Nicole Brown*
*Epic: BH-MED-DUAL-CRED*
