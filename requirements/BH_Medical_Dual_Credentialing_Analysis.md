# Behavioral Health ↔ Medical Dual Credentialing Implementation Analysis

**Business Request:** Nicole Brown
**Date:** 2026-04-01
**Practitioners Affected:** Sajani Sukhadia (1023309382), Margaret Oduro (1417443367)

---

## Executive Summary

The current system **blocks dual credentialing** because it assumes **one credentialing type per NPI**. The business needs practitioners to be credentialed for **both** Behavioral Health (BH) and Medical simultaneously, either at:
- **Same practice location** with different taxonomies, OR
- **Different practice locations** with different taxonomies

---

## 1. Current State — How BH vs Medical Works Today

### 1.1 Core Logic: SpecialtyGroupingFormula

**Location:** `PRM_PractitionerParticipationForm_English` → `SpecialtyGroupingFormula` (sequence 36)

```javascript
%PractitionerForm:isAddSpecBehavioralHealth%
||
%ProviderSpecialty-Block:Grouping% == "Behavioral Health & Social Service Providers"
```

**What it does:**
- Evaluates to `true` when the practitioner's specialty grouping is BH
- Controls visibility of BH-specific fields:
  - `PractitionerTelehealth` — "Are any of the practitioner's groups telehealth only?"
  - BH-specific COI (Certificate of Insurance) requirements
  - BH-specific Committee review context

### 1.2 Current Data Model

| Object | Current Behavior | Issue for Dual Credentialing |
|--------|------------------|------------------------------|
| **Account** (RecordType: `PRM_Practitioner`) | One per NPI | ✅ Can be shared (same practitioner person) |
| **IndividualApplication** (Case Manager) | One per credentialing request | ❌ Currently blocks second PAR for same NPI |
| **HealthcareProviderTaxonomy** | Links practitioner to taxonomy code | ❌ System expects one primary taxonomy per NPI |
| **HealthcarePractitionerFacility** | Practitioner ↔ Practice Location link | ❌ One per location — needs to support multiple taxonomies at same location |
| **HealthcareFacilityNetwork** | Network participation | ❌ Assumes single taxonomy per network |
| **CareTaxonomy.PRM_TaxonomyGrouping__c** | "Behavioral Health & Social Service Providers" vs Medical groupings | ✅ Already supports classification |

### 1.3 Current PAR Form Conditions

**Key Elements with BH-Specific Logic:**

| Element Name | Type | Show Condition | Purpose |
|--------------|------|----------------|---------|
| **SpecialtyGroupingFormula** | Formula | (hidden) | Sets flag for BH specialty |
| **PractitionerTelehealth** | Radio | `SpecialtyGroupingFormula == true` | BH-only question: telehealth groups? |
| **PractitionerTelehealthMessage** | Text Block | Shows when telehealth = Yes | Warning about telehealth limitations |
| **IsGroupBehavioralHealthCOI** | Formula (Provider Change Form) | `CONTAINS(%addSelect1COI|n%, 'Behavioral Health & Social Service Providers')` | COI verification for BH |

---

## 2. Dual Credentialing — What Needs to Change

### 2.1 High-Level Requirements

1. **Allow Second PAR Submission** — Same NPI, different taxonomy grouping
2. **Separate Case Managers** — Two `IndividualApplication` records for the same Account
3. **Separate Taxonomy Records** — BH and Medical `HealthcareProviderTaxonomy` at same Practice Location
4. **Separate Network Affiliations** — BH networks vs Medical networks
5. **Update Duplicate Detection** — Match on `NPI + TaxonomyGrouping`, not just `NPI`

### 2.2 Six Phases of Implementation

| Phase | Component | Changes Required | Priority |
|-------|-----------|------------------|----------|
| **Phase 1** | PAR Form (US-1) | Allow second PAR; display existing credentialing info | **P0 (Critical)** |
| **Phase 2** | Application Review (US-2) | Show credentialing type context | **P0 (Critical)** |
| **Phase 3** | PSV Review (US-3) | Verify correct taxonomy, create separate taxonomy records | **P0 (Critical)** |
| **Phase 4** | Committee Review (US-4) | Display dual credentialing context | **P1 (Should-have)** |
| **Phase 5** | PDA Review & Update (US-5) | Create separate network/taxonomy/facility records | **P0 (Critical)** |
| **Phase 6** | Network Management QC (US-6) | Label BH vs Medical records, read-only existing | **P1 (Should-have)** |

---

## 3. Step-by-Step Implementation Guide

### PHASE 1: PAR Form (US-1) — Allow Second PAR for Same NPI

#### Step 1.1: Add Existing Credentialing Detection

**Component:** `PRM_PractitionerParticipationForm_English`
**Location:** After `FetchExistingNPIInfo` Integration Procedure

**New DataRaptor:** `PRMDRCheckExistingCredentialingType`

**Input:**
```json
{
  "NPINumber": "%PractitionerIndividualNPI%",
  "AccountId": "%FetchExistingNPIInfo:AccountId%"
}
```

**Query (SOQL):**
```sql
SELECT Id, Name, PRM_FormType__c, Status, PRM_PractitionerSpecialty__c,
       (SELECT Id, Name, PRM_TaxonomyGrouping__c FROM HealthcareProviderTaxonomies__r),
       PRM_ApprovedDate__c, PRM_CredentialingStatus__c
FROM IndividualApplication
WHERE PRM_PractitionerAccount__c = :AccountId
  AND Status IN ('Active', 'Credentialed', 'In-Progress')
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
```

**Output:**
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
  ]
}
```

#### Step 1.2: Add Notification Block

**New Element:** `ExistingCredentialingNotification` (Text Block)

**Show Condition:**
```javascript
%PRMDRCheckExistingCredentialingType:ExistingCredentialings|n% > 0
```

**Label:**
```
⚠️ DUAL CREDENTIALING NOTICE

This practitioner already has an active credentialing:

Type: {{ExistingCredentialingType}}
Status: {{ExistingCredentialingStatus}}
Approved: {{ExistingCredentialingDate}}

You are initiating a NEW {{CurrentCredentialingType}} credentialing request.
```

#### Step 1.3: Update Duplicate Detection Logic

**Component:** `PRM_PractitionerScreenRecordCreation` Integration Procedure

**Current Logic (BLOCKS dual credentialing):**
```javascript
// Check if IndividualApplication exists for this NPI
IF (existingCM != null && existingCM.Status == 'Active') {
    THROW ERROR: "Duplicate application — practitioner already has active CM"
}
```

**New Logic (ALLOWS dual credentialing):**
```javascript
// Check if IndividualApplication exists for this NPI + TaxonomyGrouping
existingCMs = SELECT Id, TaxonomyGrouping FROM IndividualApplication
              WHERE AccountId = :inputAccountId
              AND Status IN ('Active', 'Credentialed')

currentTaxonomyGrouping = %ProviderSpecialty-Block:Grouping%

FOR EACH existingCM IN existingCMs {
    IF (existingCM.TaxonomyGrouping == currentTaxonomyGrouping) {
        THROW ERROR: "Duplicate application — practitioner already has active {currentTaxonomyGrouping} credentialing"
    }
}

// If we reach here, no duplicate for THIS taxonomy grouping → ALLOW
```

#### Step 1.4: Physician Assistant Exception

**New Validation Element:** `PAExceptionWarning`

**Show Condition:**
```javascript
%ProviderRole% == "Physician Assistant"
&& %PRMDRCheckExistingCredentialingType:ExistingCredentialings|n% > 0
```

**Label:**
```
⚠️ PHYSICIAN ASSISTANT TAXONOMY WARNING

Physician Assistant taxonomy is the same for BH and Medical.
Please confirm this is a NEW credentialing request and not a duplicate.

Confirm to proceed: [ ] Yes, this is a new request
```

---

### PHASE 2: Application Review (US-2) — Show Credentialing Type Context

#### Step 2.1: Add Credentialing Type Header

**Component:** `PRM_RecredQC_English` → `ReviewPractitioner` step

**New Element:** `CredentialingTypeHeader` (Text Block)

**Label:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREDENTIALING TYPE: {{CurrentCredentialingType}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Value Calculation:**
```javascript
IF (%ProviderSpecialty-Block:Grouping% == "Behavioral Health & Social Service Providers") {
    "BEHAVIORAL HEALTH"
} ELSE {
    "MEDICAL"
}
```

#### Step 2.2: Add Other Credentialing Info Block

**New Element:** `OtherCredentialingInfoBlock` (Text Block)

**Show Condition:**
```javascript
%IPFetchParInformation:OtherCredentialingInfo|n% > 0
```

**Label:**
```
ℹ️ EXISTING CREDENTIALING INFORMATION

This practitioner also has: {{OtherCredentialingType}}
Status: {{OtherCredentialingStatus}}
Approved Date: {{OtherApprovedDate}}
```

---

### PHASE 3: PSV Review (US-3) — Taxonomy-Specific Verification

#### Step 3.1: Update VerifySpecialty Step

**Component:** `PRM_PSVSubOsTxnyRole_English` → `VerifySpecialty`

**Key Change:** Ensure taxonomy verification uses **current CM's taxonomy**, not Account-level existing taxonomy

**DataRaptor:** `DRTransformPSVScreenData`

**Update Logic:**
```javascript
// OLD (pulls any taxonomy from Account):
TaxonomyToVerify = Account.HealthcareProviderTaxonomy[0]

// NEW (pulls taxonomy from current CM only):
TaxonomyToVerify = IndividualApplication.PRM_RequestedTaxonomy__c
```

#### Step 3.2: Update COI Verification

**Component:** `CertificateofInsuranceVerification` step

**Formula:** `IsGroupBehavioralHealthCOI`

**Update:**
```javascript
// OLD (checks Account-level data):
CONTAINS(Account.PRM_TaxonomyGrouping__c, 'Behavioral Health')

// NEW (checks CURRENT CM's taxonomy):
CONTAINS(%IPFetchParInformation:CurrentCMTaxonomyGrouping%, 'Behavioral Health')
```

#### Step 3.3: Create Separate Taxonomy Records

**Component:** `VerifyPractitionerRole` step

**Key Requirement:** Create NEW `HealthcareProviderTaxonomy` and `HealthcarePractitionerFacility` records for Medical taxonomy, **separate from existing BH records**

**Apex/DataRaptor Logic:**
```java
// Check if practitioner already has BH taxonomy at this practice location
List<HealthcareProviderTaxonomy> existingTaxonomies =
    [SELECT Id, TaxonomyCode__c, TaxonomyGrouping__c
     FROM HealthcareProviderTaxonomy
     WHERE HealthcareProvider__c = :practitionerId
     AND HealthcareFacility__c = :practiceLocationId];

// Create NEW Medical taxonomy record alongside existing BH
HealthcareProviderTaxonomy medicalTaxonomy = new HealthcareProviderTaxonomy(
    HealthcareProvider__c = practitionerId,
    HealthcareFacility__c = practiceLocationId,
    TaxonomyCode__c = requestedMedicalTaxonomyCode,
    TaxonomyGrouping__c = 'Medical Grouping',
    IsPrimary__c = true  // Can be primary for Medical track
);
insert medicalTaxonomy;

// Do NOT update or delete existing BH taxonomy
```

---

### PHASE 4: Committee Review (US-4) — Display Context

#### Step 4.1: Add Credentialing Type Column

**Component:** `PRM_ReviewInitialCredApplicants_English` → `RoutineCredCommitteeTable`

**New Column:** `CredentialingType`

**Value:**
```javascript
IF (CM.TaxonomyGrouping == "Behavioral Health & Social Service Providers") {
    "BH"
} ELSE {
    "Medical"
}
```

**New Column:** `DualCredentialing`

**Value:**
```javascript
// Count other active CMs for same AccountId with different TaxonomyGrouping
IF (otherCMsCount > 0) {
    "Yes — Also {{OtherType}}"
} ELSE {
    "No"
}
```

---

### PHASE 5: PDA Review & Update (US-5) — Create Separate Network Records

#### Step 5.1: Update PDA Processing

**Component:** `PRM_ProviderChangePDAUpdate_English` → `PRM_ProviderChangePDAUpdatesParent` IP

**Key Requirements:**

1. **Separate HealthcareProviderTaxonomy records** — One BH, one Medical at same location
2. **Separate HealthcarePractitionerFacility records** — One per taxonomy
3. **Separate HealthcareFacilityNetwork records** — BH networks vs Medical networks
4. **Separate Info Codes** — Medical info codes may differ from BH

**Apex Service:** `PRM_PNCPDAService`

**Update Logic:**
```java
// OLD (assumes one taxonomy per location):
if (existingTaxonomy != null) {
    existingTaxonomy.TaxonomyCode__c = newTaxonomyCode;
    update existingTaxonomy;
}

// NEW (creates alongside existing):
// Check for existing taxonomies
List<HealthcareProviderTaxonomy> existingTaxonomies =
    [SELECT Id, TaxonomyGrouping__c FROM HealthcareProviderTaxonomy
     WHERE HealthcareProvider__c = :practitionerId
     AND HealthcareFacility__c = :facilityId];

String currentTaxonomyGrouping = CM.TaxonomyGrouping__c;

// Only create if this taxonomy grouping doesn't exist
Boolean alreadyExists = false;
for (HealthcareProviderTaxonomy existing : existingTaxonomies) {
    if (existing.TaxonomyGrouping__c == currentTaxonomyGrouping) {
        alreadyExists = true;
        break;
    }
}

if (!alreadyExists) {
    // Create NEW taxonomy record
    HealthcareProviderTaxonomy newTaxonomy = new HealthcareProviderTaxonomy(
        HealthcareProvider__c = practitionerId,
        HealthcareFacility__c = facilityId,
        TaxonomyCode__c = newTaxonomyCode,
        TaxonomyGrouping__c = currentTaxonomyGrouping,
        IsPrimary__c = true  // Can have one primary per grouping
    );
    insert newTaxonomy;
}
```

#### Step 5.2: Network Creation

**Component:** `PRM_PNCPracTxnyNetworkBatch`

**Key Change:** Support **multiple taxonomies per Practice Location per Practitioner**

```java
// Create Medical-specific HealthcareFacilityNetwork
HealthcareFacilityNetwork medicalNetwork = new HealthcareFacilityNetwork(
    HealthcareFacility__c = facilityId,
    HealthcareProvider__c = practitionerId,
    TaxonomyGrouping__c = 'Medical',
    NetworkName__c = 'Medical Network XYZ',
    EffectiveFrom__c = approvalDate,
    Status__c = 'Active'
);
insert medicalNetwork;

// Existing BH network remains UNCHANGED
```

---

### PHASE 6: Network Management QC (US-6) — Label Records

#### Step 6.1: Add Credentialing Type Labels

**Component:** `PRM_ManualUpdatesQCReview3_English`

**New Column in Taxonomy/Network Tables:** `CredentialingType`

**Value:**
```javascript
%TaxonomyGrouping% == "Behavioral Health & Social Service Providers" ? "BH" : "Medical"
```

**New Column:** `RecordSource`

**Value:**
```javascript
// New records from current CM → Editable
// Existing records from other CM → Read-only
IF (%TaxonomyRecord.CaseManagerId% == %CurrentCaseManagerId%) {
    "NEW — Editable"
} ELSE {
    "EXISTING — Read-Only"
}
```

---

## 4. Potential Issues & Risks

### 4.1 Critical Issues

| # | Issue | Impact | Mitigation |
|---|-------|--------|------------|
| **1** | **Duplicate Detection Breaks Flow** | Prevents second PAR submission entirely | Update `PRM_PractitionerScreenRecordCreation` IP to allow second CM when TaxonomyGrouping differs |
| **2** | **Existing BH Records Overwritten** | Medical PDA may update/delete BH taxonomy records | Modify PDA logic to CREATE new records, not UPDATE existing |
| **3** | **Primary Taxonomy Conflict** | System may enforce "only one primary taxonomy" | Allow one primary per TaxonomyGrouping (not one per Account) |
| **4** | **Network Creation Logic** | `PRM_PNCPDAService` assumes one taxonomy per location | Extend to support multiple taxonomies at same location |
| **5** | **Queue Routing Confusion** | Two active CMs for same NPI may cause round-robin conflicts | Consider separate queues for BH vs Medical, or tag CMs with taxonomy type |

### 4.2 Data Integrity Risks

| # | Risk | Scenario | Prevention |
|---|------|----------|------------|
| **1** | **Orphaned Taxonomy Records** | Medical PAR denied after PSV creates taxonomy | Rollback taxonomy records if CM denied |
| **2** | **Duplicate Networks** | PDA runs twice, creates duplicate `HealthcareFacilityNetwork` | Add unique constraint on `(HealthcareFacility__c, HealthcareProvider__c, TaxonomyGrouping__c)` |
| **3** | **Mixed Taxonomy Data** | Committee approves BH but Medical taxonomy shows in records | Strict scope: only update records for CURRENT CM's taxonomy grouping |
| **4** | **Pending Flag Conflict** | Medical PDA sets `PRM_Pending__c` on BH records | Scope pending flags to current CM's records only |

### 4.3 User Experience Issues

| # | Issue | Impact | Mitigation |
|---|-------|--------|------------|
| **1** | **Reviewers Don't See Dual Context** | Confusion during App Review, PSV, Committee | Add clear headers: "Credentialing Type: BH/Medical" + "Other Active Credentialing: X" |
| **2** | **QC Sees Too Many Records** | Network Management QC shows both BH and Medical records — may flag as duplicate | Label records: "BH — Read-Only" vs "Medical — Editable" |
| **3** | **No Distinction in Case Manager Name** | Two CMs with same name pattern: "APP-12345" | Add suffix: "APP-12345-BH" vs "APP-12345-MED" |

---

## 5. Test Scenarios & QA Cases

### 5.1 Test Case 1: New Medical PAR for Existing BH Practitioner

**Given:**
- Practitioner NPI 1023309382 (Sajani Sukhadia) is credentialed as BH
- BH taxonomy: "Behavioral Health & Social Service Providers"
- BH practice: Group A

**When:**
- Credentialing Specialist opens PAR form
- Enters NPI 1023309382
- Selects Medical specialty (e.g., "Family Medicine")
- Selects Medical practice: Group B (or Group A — same practice)

**Then:**
1. System displays notification: "This practitioner already has BH credentialing"
2. PAR form allows submission
3. New `IndividualApplication` created (separate from BH CM)
4. BH Case Manager and records remain UNCHANGED

**Expected Records:**
- Account: 1 (shared)
- IndividualApplication: 2 (one BH, one Medical)
- HealthcareProviderTaxonomy: 2+ (one BH at Group A, one Medical at Group B or Group A)
- HealthcarePractitionerFacility: 2+
- HealthcareFacilityNetwork: 2+ (BH networks, Medical networks)

### 5.2 Test Case 2: Same Practice, Dual Taxonomy

**Given:**
- Practitioner credentialed as BH at Practice Location X

**When:**
- New Medical PAR for same practitioner at SAME Practice Location X

**Then:**
1. PSV creates **new** `HealthcareProviderTaxonomy` for Medical at Location X
2. Existing BH `HealthcareProviderTaxonomy` at Location X remains ACTIVE
3. Practice Location X has TWO taxonomy records for this practitioner

**Verification Query:**
```sql
SELECT Id, HealthcareProvider__r.Name, HealthcareFacility__r.Name,
       TaxonomyCode__c, TaxonomyGrouping__c, IsPrimary__c
FROM HealthcareProviderTaxonomy
WHERE HealthcareProvider__r.NPI__c = '1023309382'
  AND HealthcareFacility__r.Name = 'Practice Location X'
ORDER BY TaxonomyGrouping__c
```

**Expected Result:**
```
| Practitioner     | Practice Location | Taxonomy Grouping | IsPrimary |
|------------------|-------------------|-------------------|-----------|
| Sajani Sukhadia  | Location X        | BH & Social Service | true    |
| Sajani Sukhadia  | Location X        | Medical           | true      |
```

### 5.3 Test Case 3: Physician Assistant Exception

**Given:**
- Practitioner role: Physician Assistant
- Taxonomy code is same for BH and Medical

**When:**
- Credentialing Specialist attempts second PAR for PA with same taxonomy

**Then:**
1. System displays warning: "PA taxonomy is same for BH and Medical — confirm this is not a duplicate"
2. Specialist must explicitly confirm
3. If confirmed, PAR proceeds

### 5.4 Test Case 4: Committee Review Context

**Given:**
- Practitioner has existing BH credential (approved 2025-03-15)
- New Medical PAR goes to Committee

**When:**
- Committee member opens `PRM_ReviewInitialCredApplicants_English`

**Then:**
1. `RoutineCredCommitteeTable` shows:
   - **Credentialing Type:** Medical
   - **Dual Credentialing:** Yes — Also BH
2. Tooltip or detail text: "Also credentialed as BH since 03/15/2025"

### 5.5 Test Case 5: PDA Creates Separate Networks

**Given:**
- Medical PAR approved by Committee
- Practitioner already has BH network at Group A

**When:**
- PDA runs (`PRM_ProviderChangePDAUpdate_English`)

**Then:**
1. **NEW** `HealthcareFacilityNetwork` created for Medical at Group A (or Group B)
2. Existing BH `HealthcareFacilityNetwork` at Group A remains UNCHANGED
3. Practitioner appears in BOTH BH and Medical network directories

**Verification Query:**
```sql
SELECT Id, HealthcareProvider__r.Name, HealthcareFacility__r.Name,
       NetworkName__c, TaxonomyGrouping__c, Status__c
FROM HealthcareFacilityNetwork
WHERE HealthcareProvider__r.NPI__c = '1023309382'
ORDER BY TaxonomyGrouping__c
```

---

## 6. Key Questions for Business (Must Resolve Before Implementation)

### 6.1 Core Logic Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| **Q1** | **How do we determine BH vs Medical?** Is it solely `CareTaxonomy.PRM_TaxonomyGrouping__c`? Or is there another field? | Core branching logic | BA / Business |
| **Q2** | **Should the Account have a field tracking credentialing types** (e.g., `PRM_CredentialingTypes__c` = "BH;Medical")? Or is presence of multiple CMs sufficient? | Data model design | Technical / BA |
| **Q3** | **Should Case Manager Name distinguish BH from Medical?** (e.g., "APP-12345-BH" vs "APP-12345-MED") | Reporting, identification | BA / Business |

### 6.2 Process Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| **Q4** | **Does dual credentialing follow the same lifecycle** (PAR → App → PSV → QC → Committee → PDA → NM QC), or are steps shortened/skipped? | Scope of changes | BA / Operations |
| **Q5** | **Queue routing:** When one NPI has two active CMs (BH + Medical), should both go to same specialist or different queues? | Queue assignment logic | Operations / BA |
| **Q6** | **Can previously verified PSV items (NPI, NPDB, work history) be carried over** from BH credentialing to Medical? Or must everything be re-verified? | Efficiency vs compliance | BA / Operations |

### 6.3 Data Model Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| **Q7** | **When practitioner works as BH/Medical at SAME practice, should they have one or two vendor group records?** Old system had two groups. Should PIE replicate this? | PDA data model | BA / Business |
| **Q8** | **Are there separate contracts for BH vs Medical?** Does Contract Hierarchy need to support dual contracts at same practice? | Contract configuration | BA / Operations |

### 6.4 Compliance & Volume Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| **Q9** | **Is there a regulatory requirement for separate credentialing files?** (NCQA, CMS) | Compliance — file management | Legal / Compliance |
| **Q10** | **What is the expected volume?** Handful per quarter or regular occurrence? | Priority, architecture complexity | BA / Business |

---

## 7. Implementation Priority & Timeline

### Phase 1 (P0 — Critical) — Must-Have for Launch

| Component | Effort | Dependencies |
|-----------|--------|--------------|
| **US-1: PAR Form** | 2-3 weeks | None (first step) |
| **US-3: PSV Taxonomy Verification** | 2-3 weeks | US-1 complete |
| **US-5: PDA Record Creation** | 3-4 weeks | US-1, US-3 complete |

**Total Phase 1:** ~8-10 weeks

### Phase 2 (P1 — Should-Have) — Post-Launch Enhancement

| Component | Effort | Dependencies |
|-----------|--------|--------------|
| **US-2: Application Review Context** | 1-2 weeks | Phase 1 complete |
| **US-4: Committee Review Context** | 1 week | Phase 1 complete |
| **US-6: Network Management QC Labeling** | 1-2 weeks | Phase 1 complete |

**Total Phase 2:** ~3-5 weeks

---

## 8. Summary & Recommendations

### 8.1 Current Blockers

1. **PAR Duplicate Detection** — Blocks second PAR submission
2. **PDA Overwrite Logic** — May update/delete existing BH records when creating Medical records
3. **Primary Taxonomy Constraint** — System may enforce only one primary taxonomy per practitioner

### 8.2 Recommended Approach

1. ✅ **Implement in Phases** — Phase 1 (P0) enables core dual credentialing; Phase 2 (P1) adds context/polish
2. ✅ **Do NOT modify existing records** — Always CREATE new records for Medical, leave BH records untouched
3. ✅ **Update duplicate detection** — Match on `NPI + TaxonomyGrouping`, not just `NPI`
4. ✅ **Add clear UI context** — Headers, notifications, labels to distinguish BH from Medical at every step
5. ✅ **Test thoroughly** — Use Sajani Sukhadia (1023309382) and Margaret Oduro (1417443367) as test cases

### 8.3 Success Criteria

- [ ] Sajani Sukhadia (1023309382) can submit new Medical PAR while BH credential remains active
- [ ] Two `IndividualApplication` records exist for same NPI with different taxonomies
- [ ] PSV creates separate `HealthcareProviderTaxonomy` for Medical without affecting BH taxonomy
- [ ] PDA creates separate `HealthcareFacilityNetwork` for Medical without affecting BH network
- [ ] Committee sees dual credentialing context: "BH — Also Medical"
- [ ] Network Management QC sees labeled records: "BH — Read-Only" vs "Medical — Editable"

---

**Next Steps:**
1. **Resolve business questions** (Q1-Q10) with Nicole Brown / BA team
2. **Design technical solution** for duplicate detection update
3. **Create detailed DataRaptor/IP specifications** for each phase
4. **Build Phase 1 in Dev/QA sandbox** with test NPIs
5. **Validate with Sajani Sukhadia / Margaret Oduro records**

---

*Generated: 2026-04-01*
*Analyst: Claude Code*
*Source: BH_Medical_Dual_Credentialing_User_Stories.md, PRM_PractitionerParticipationForm_English OmniScript*
