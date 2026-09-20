# PSV QC Review LWC Redesign - Detailed Design Document

## Executive Summary

**Problem:** The current PSV Quality Control (QC) Review flow (within `PRM_PrimarySourceVerificationReview_English` when `CaseType = "QC Review"`) suffers from:
1. **4MB Payload Limitation** - "Save for Later" fails with large datasets (100+ addresses reviewed by PSV)
2. **Read-Only Fields** - QC reviewers cannot edit verification status fields inline, forcing them to navigate externally
3. **All-or-Nothing Flow** - Must complete entire QC review session (1-2 hours) or lose progress
4. **No Visual Progress** - Users don't know what's been QC-verified vs pending
5. **Embedded in PSV Flow** - QC-specific fields are conditionally shown within PSV OmniScript, making it complex

**Solution:** Redesign from OmniScript to a tile-based LWC architecture where:
- Each PSV section has a QC verification tile (review what PSV did)
- **ALL VERIFICATION FIELDS ARE EDITABLE** (key business requirement)
- Saves immediately upon tile completion
- Provides visual progress tracking
- Auto-saves every 2 minutes
- Supports resume from anywhere, anytime

**Key Difference from PSV Review:**
- **PSV Review:** PSV Specialist enters/verifies data from CAQH
- **PSV QC Review:** QC Specialist verifies what PSV did (adds verification status: "Data Looks Good", "Not Applicable", "Missing Information")

---

## Current State Analysis

### Current OmniScript Structure

**Main OmniScript:** `PRM_PrimarySourceVerificationReview_English` (Version 47)
**Sub-OmniScript:** `PRM_PSVSubOsSummary_English` (Contains QC-specific step)

**Condition:** `CaseType = "QC Review"`

When this condition is true, additional QC-specific fields are shown:
- **Board Certification Table** (Display only - shows what PSV verified)
- **Board Certification Verification** (Radio: Data Looks Good / Not Applicable / Missing Information)
- **Board Certification Note** (Text Area)
- **QC Review Summary Step** (Special step for QC outcome)

### Flow Differences: PSV vs PSV QC

| Section | PSV Review | PSV QC Review (`CaseType = "QC Review"`) |
|---------|------------|------------------------------------------|
| **Practitioner Info** | Editable (PSV enters data) | **Display + Verification Status** (QC reviews) |
| **Group/Practice** | Editable | **Display + Verification Status** |
| **Addresses** | Editable (PSV adds/updates) | **Display + Verification Status** |
| **Demographics & Diversity** | Editable | **Display + Verification Status** |
| **Languages** | Editable | **Display + Verification Status** |
| **Contact Information** | Editable | **Display + Verification Status** |
| **Board Certification** | Editable (Re-Cred only) | **Display + Verification Status** (SHOWN IN QC) |
| **Contract Status** | Editable | **Display + Verification Status** |
| **QC Review Summary** | ✗ (Not shown) | **✓ (QC-specific step)** |

### Data Being Reviewed (Post-PSV)

| Review Section | Source | Salesforce Objects | QC Actions |
|----------------|--------|-------------------|------------|
| **Practitioner Info** | PSV Output | Account, IndividualApplication | Verify PSV decisions, add notes |
| **Group/Practice** | PSV Output | CareProviderFacilityGroup, Facility | Verify PSV decisions, add notes |
| **Addresses** | PSV Output | Address, PractitionerLocation, HealthcarePractitionerFacility | Verify PSV decisions, add notes |
| **Demographics & Diversity** | PSV Output | Account, IndividualApplication | Verify PSV decisions, add notes |
| **Languages** | PSV Output | LanguageSkill | Verify PSV decisions, add notes |
| **Contact Information** | PSV Output | Account, IndividualApplication | Verify PSV decisions, add notes |
| **Board Certification** | PSV Output (Re-Cred) | BoardCertification | **Verify PSV decisions, add notes** (QC-specific) |
| **Contract Status** | PSV Output | Contract, PractitionerRole | Verify PSV decisions, add notes |

### Data Being Updated at End

**Integration Procedure:** `PRM_ReviewPSVCaseRecordsUpdate` (same IP as PSV, but with QC verification flags)

**Objects Modified:**
- **IndividualApplication** - PSV QC verification fields:
  - `PSV_QC_PractitionerInfo_Status__c`
  - `PSV_QC_PractitionerInfo_Notes__c`
  - `PSV_QC_GroupPractice_Status__c`
  - `PSV_QC_GroupPractice_Notes__c`
  - `PSV_QC_Address_Status__c`
  - `PSV_QC_Address_Notes__c`
  - `PSV_QC_Demographics_Status__c`
  - `PSV_QC_Demographics_Notes__c`
  - `PSV_QC_Languages_Status__c`
  - `PSV_QC_Languages_Notes__c`
  - `PSV_QC_Contact_Status__c`
  - `PSV_QC_Contact_Notes__c`
  - `PSV_QC_BoardCert_Status__c`
  - `PSV_QC_BoardCert_Notes__c`
  - `PSV_QC_Contract_Status__c`
  - `PSV_QC_Contract_Notes__c`
- **Case** - Status, PSV QC Review Results, QC Notes
- **Case Manager** - QC Assignment, Status Updates, Next Step

### Current Pain Points

1. **4MB Payload Limit** - Fails with 100+ addresses reviewed by PSV
2. **Conditional Fields** - QC-specific fields are conditionally shown within PSV OmniScript, making it complex
3. **Read-Only Verification Fields** - Cannot edit verification status inline
4. **All-or-Nothing** - Must complete entire QC review session or lose progress
5. **No Visual Progress** - Users don't know what's QC-verified vs pending
6. **Mixed Context** - PSV and QC logic mixed in same OmniScript (186+ elements)

---

## Proposed LWC Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│            PSV QUALITY CONTROL REVIEW DASHBOARD              │
├──────────────────────────────────────────────────────────────┤
│  Progress: ████████░░ 80% Complete                          │
│  Auto-saved 2 minutes ago                                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │     ✓     │  │     ✓     │  │     ⚠     │  │          ││
│  │Practitioner│ │   Group   │  │ Address   │  │Demographics│
│  │ Info QC   │  │/Practice  │  │Verification│ │ & Diversity││
│  │           │  │   QC      │  │    QC     │  │    QC     ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘│
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │           │  │           │  │           │  │          ││
│  │Languages  │  │  Contact  │  │   Board   │  │Contract  ││
│  │    QC     │  │Information│  │   Cert    │  │ Status   ││
│  │           │  │    QC     │  │    QC     │  │   QC     ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘│
│                                                              │
│  ┌───────────┐  ┌───────────┐                              │
│  │           │  │     ✓     │                              │
│  │  Upload   │  │PSV QC     │                              │
│  │  Files    │  │  Summary  │                              │
│  └───────────┘  └───────────┘                              │
│                                                              │
│  [Resume Later]  [Save & Exit]  [Help]                     │
└──────────────────────────────────────────────────────────────┘

       │ Click Tile
       ▼
┌──────────────────────────────────────────────────────────────┐
│              MODAL: Practitioner Info QC Review              │
│                    ✏️ Verification Fields Editable           │
│                                                              │
│  PSV VERIFIED DATA (Display Only)                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Name: John Doe, MD                                 │    │
│  │ NPI: 1234567890                                    │    │
│  │ DOB: 1980-01-01                                    │    │
│  │ Gender: Male                                       │    │
│  │ Specialty: Internal Medicine                       │    │
│  │ Taxonomy Code: 207R00000X                          │    │
│  │ Practitioner Role: PCP                             │    │
│  │                                                     │    │
│  │ PSV Verified By: Jane Smith                        │    │
│  │ PSV Verified Date: 2026-04-08                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  QC VERIFICATION (Editable)                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Verification Status:                                │    │
│  │   ○ Data Looks Good                                 │    │
│  │   ○ Not Applicable                                  │    │
│  │   ○ Missing Information                             │    │
│  │                                                     │    │
│  │ QC Notes:                                           │    │
│  │ ┌─────────────────────────────────────────────┐   │    │
│  │ │                                             │   │    │
│  │ │                                             │   │    │
│  │ └─────────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  [Cancel]  [Save Draft]  [Submit & Review Next ▼]          │
└──────────────────────────────────────────────────────────────┘
```

### Component Structure

```
prm_psvQCReviewDashboard (Parent - REUSE from PSV & App Review)
  ├── prm_progressHeader (REUSE 100%)
  ├── prm_verificationTile (REUSE 100%)
  │     └── prm_verificationModal (REUSE 100%)
  │           ├── prm_psvQCPractitionerInfo
  │           ├── prm_psvQCGroupPractice
  │           ├── prm_psvQCAddressVerification
  │           ├── prm_psvQCDemographicsDiversity
  │           ├── prm_psvQCLanguagesSpoken
  │           ├── prm_psvQCContactInformation
  │           ├── prm_psvQCBoardCertification
  │           ├── prm_psvQCContractStatus
  │           ├── prm_fileUpload (REUSE 100%)
  │           └── prm_psvQCSummary
  └── prm_navigationFooter (REUSE 100%)
```

---

## Reusability Analysis: PSV QC vs PSV vs App Review vs PDA QC

### Framework Components (100% Reuse)

| Component | App Review | PSV | PSV QC | PDA QC | Reusable? |
|-----------|-----------|-----|--------|--------|-----------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_progressHeader** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationTile** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationModal** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_fileUpload** | ✓ | ✓ | ✓ | ✗ | **100%** |

**Framework Reuse: 100%** ✅

### Child Component Reusability

| Tile | PSV | PSV QC | Reusable From PSV | Reuse % |
|------|-----|--------|-------------------|---------|
| **Practitioner Info** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** (add verification status radio + notes) |
| **Group/Practice** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Address Verification** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Demographics & Diversity** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Languages Spoken** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Contact Information** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Board Certification** | ✓ (Re-Cred, Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **Contract Status** | ✓ (Editable) | ✓ (Display + Verification) | PSV + QC wrapper | **80%** |
| **File Upload** | ✓ | ✓ | **Shared** | **100%** |
| **PSV QC Summary** | ✗ | ✓ (QC Outcome) | **New** | **0%** |

**Child Component Reuse: ~75%** (Wrap PSV components with QC verification layer)

---

## Reusable QC Wrapper Pattern

The key architectural insight for PSV QC Review is the **QC Wrapper Pattern**: Instead of building 8 QC tiles from scratch, we create a single reusable wrapper component that displays PSV data (read-only) and adds a QC verification layer (editable) on top of existing PSV components.

### QC Wrapper Component Architecture

**Generic QC Wrapper Component:**
```javascript
// prm_qcWrapper.js
export default class PrmQcWrapper extends LightningElement {
    @api component;              // Which PSV component to wrap (e.g., 'prm_psvPractitionerInfo')
    @api psvData;                // PSV verified data (read-only)
    @api qcVerificationStatus;   // QC status: 'Data Looks Good', 'Not Applicable', 'Missing Information'
    @api qcNotes;                // QC notes
    @api tileLabel;              // Tile label (e.g., 'Practitioner Info')
    @api fieldMapping;           // Maps PSV fields to display fields
    
    // Layout: Two sections stacked vertically
    get sections() {
        return [
            {
                title: 'PSV VERIFIED DATA (Display Only)',
                component: this.component,
                data: this.psvData,
                isEditable: false,
                showMetadata: true  // Show PSV Verified By/Date
            },
            {
                title: 'QC VERIFICATION (Editable)',
                fields: [
                    {
                        label: 'Verification Status',
                        type: 'radio',
                        options: ['Data Looks Good', 'Not Applicable', 'Missing Information'],
                        required: true,
                        value: this.qcVerificationStatus
                    },
                    {
                        label: 'QC Review Notes',
                        type: 'textarea',
                        required: this.qcVerificationStatus === 'Missing Information',
                        value: this.qcNotes
                    },
                    {
                        label: 'QC Reviewed By',
                        type: 'text',
                        readonly: true,
                        value: this.currentUser
                    },
                    {
                        label: 'QC Reviewed Date',
                        type: 'datetime',
                        readonly: true,
                        value: this.currentDateTime
                    }
                ]
            }
        ];
    }
    
    handleVerificationStatusChange(event) {
        this.qcVerificationStatus = event.detail.value;
        this.dispatchEvent(new CustomEvent('qcstatuschange', {
            detail: {
                tileId: this.tileLabel,
                status: this.qcVerificationStatus,
                notes: this.qcNotes
            }
        }));
    }
}
```

**Usage Example (Practitioner Info QC):**
```javascript
// prm_psvQCPractitionerInfo.js
import PrmQcWrapper from 'c/prmQcWrapper';

export default class PrmPsvQCPractitionerInfo extends LightningElement {
    @api psvVerifiedData;
    @api qcVerificationData;
    
    render() {
        return html`
            <c-prm-qc-wrapper
                component="c-prm-psv-practitioner-info"
                psv-data={psvVerifiedData}
                qc-verification-status={qcVerificationData.verificationStatus}
                qc-notes={qcVerificationData.qcReviewNotes}
                tile-label="Practitioner Info"
                field-mapping={practitionerInfoFieldMapping}
                onqcstatuschange={handleQcStatusChange}>
            </c-prm-qc-wrapper>
        `;
    }
}
```

**Reuse Benefit:** 

Instead of building 8 unique QC components, we:
1. Build **1 reusable QC wrapper** component
2. Apply it to **8 existing PSV components**
3. Each QC tile = **PSV Component + QC Wrapper** (configuration-driven)

**Reusability Matrix:**

| QC Tile | PSV Component (Reuse 100%) | QC Wrapper (Reuse 100%) | New Development | Reuse % |
|---------|---------------------------|------------------------|-----------------|---------|
| **Practitioner Info QC** | prm_psvPractitionerInfo | prm_qcWrapper | Configuration only | **95%** |
| **Group/Practice QC** | prm_psvGroupPractice | prm_qcWrapper | Configuration only | **95%** |
| **Address Verification QC** | prm_psvAddressVerification | prm_qcWrapper | Configuration only | **95%** |
| **Demographics & Diversity QC** | prm_psvDemographicsDiversity | prm_qcWrapper | Configuration only | **95%** |
| **Languages Spoken QC** | prm_psvLanguagesSpoken | prm_qcWrapper | Configuration only | **95%** |
| **Contact Information QC** | prm_psvContactInformation | prm_qcWrapper | Configuration only | **95%** |
| **Board Certification QC** | prm_psvBoardCertification | prm_qcWrapper | Configuration only | **95%** |
| **Contract Status QC** | prm_psvContractStatus | prm_qcWrapper | Configuration only | **95%** |
| **File Upload** | prm_fileUpload | N/A | No wrapper needed | **100%** |
| **PSV QC Summary** | N/A | N/A | New component | **0%** |

**Overall Reusability: ~85%** (9 of 10 tiles reuse existing components)

---

### Timeline Impact: 6 weeks → 3 weeks

**Original Estimate (Without QC Wrapper Pattern): 6 weeks**
- Build 8 QC components from scratch
- Each component = 2-3 days
- Total: 4 weeks for tiles + 2 weeks testing

**Revised Estimate (With QC Wrapper Pattern): 3 weeks**
- Build 1 QC wrapper component: **3 days**
- Apply wrapper to 8 PSV tiles: **4 days** (0.5 days per tile for configuration)
- Build PSV QC Summary: **2 days**
- Testing: **5 days**
- Total: **3 weeks**

---

## Detailed Tile Design

### Tile 1: Practitioner Info QC Review

**Component:** `prm_psvQCPractitionerInfo`

**Purpose:** QC reviews what PSV verified for practitioner information

**Data Sources:**
- **PSV Output:** Account, IndividualApplication (what PSV verified)
- **QC Input:** IndividualApplication (QC verification status)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ PSV VERIFIED DATA (Display Only)                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Full Name: John Doe, MD                             │ │
│ │ NPI: 1234567890                                     │ │
│ │ CAQH Provider ID: CAQH123456                        │ │
│ │ Date of Birth: 1980-01-01                           │ │
│ │ Gender: Male                                        │ │
│ │ Email: john.doe@example.com                         │ │
│ │ Specialty: Internal Medicine                        │ │
│ │ Taxonomy Code: 207R00000X                           │ │
│ │ Practitioner Role: PCP                              │ │
│ │ Degree: MD                                          │ │
│ │ Telehealth Capable: Yes                             │ │
│ │                                                     │ │
│ │ PSV Verified By: Jane Smith                         │ │
│ │ PSV Verified Date: 2026-04-08 10:30 AM             │ │
│ │ PSV Notes: All data verified against CAQH          │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ QC VERIFICATION (Editable)                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Verification Status: (Required)                     │ │
│ │   ○ Data Looks Good                                 │ │
│ │   ○ Not Applicable                                  │ │
│ │   ○ Missing Information                             │ │
│ │                                                     │ │
│ │ QC Review Notes:                                    │ │
│ │ [_____________________________________________]     │ │
│ │                                                     │ │
│ │ QC Reviewed By: [Auto-populated]                   │ │
│ │ QC Reviewed Date: [Auto-populated]                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Fields (EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **Verification Status** | IndividualApplication | PSV_QC_PractitionerInfo_Status__c | **Radio (Data Looks Good, Not Applicable, Missing Information)** |
| **QC Review Notes** | IndividualApplication | PSV_QC_PractitionerInfo_Notes__c | **Long text area** |
| QC Reviewed By | IndividualApplication | PSV_QC_PractitionerInfo_ReviewedBy__c | User (auto-populated) |
| QC Reviewed Date | IndividualApplication | PSV_QC_PractitionerInfo_ReviewedDate__c | DateTime (auto-populated) |

**Data Structure:**
```javascript
{
  // PSV Verified Data (Display Only)
  psvData: {
    practitionerId: '001xxx',
    fullName: 'John Doe, MD',
    npi: '1234567890',
    caqhProviderId: 'CAQH123456',
    dateOfBirth: '1980-01-01',
    gender: 'Male',
    email: 'john.doe@example.com',
    specialty: 'Internal Medicine',
    taxonomyCode: '207R00000X',
    practitionerRole: 'PCP',
    degree: 'MD',
    telehealthCapable: true,
    psvVerifiedBy: 'Jane Smith',
    psvVerifiedDate: '2026-04-08T10:30:00',
    psvNotes: 'All data verified against CAQH'
  },
  // QC Verification (Editable)
  qcVerification: {
    verificationStatus: null, // 'Data Looks Good', 'Not Applicable', 'Missing Information'
    qcReviewNotes: '',
    qcReviewedBy: 'John Smith',
    qcReviewedDate: '2026-04-09T14:20:00'
  },
  tileStatus: 'Pending' // 'Pending', 'In Progress', 'Completed'
}
```

**Validation Rules:**
- Verification Status is required
- QC Review Notes are required if "Missing Information" is selected

---

### Tile 2-8: Same Pattern as Tile 1

All tiles follow the same structure:
1. **PSV Verified Data** (Display Only section - shows what PSV did)
2. **QC Verification** (Editable section - QC adds verification status + notes)

| Tile | PSV Data Shown | QC Verification Fields |
|------|----------------|------------------------|
| **2. Group/Practice QC** | Group Name, Group NPI, Tax ID, Practice Type, PSV Verified By/Date | Verification Status, QC Notes |
| **3. Address Verification QC** | All addresses verified by PSV (100+ addresses), PSV Verified By/Date | Verification Status, QC Notes |
| **4. Demographics & Diversity QC** | Hispanic/Latino, Racial Identity, Cultural Identity, Pronouns, Affirming Care, PSV Verified By/Date | Verification Status, QC Notes |
| **5. Languages Spoken QC** | All languages verified by PSV, PSV Verified By/Date | Verification Status, QC Notes |
| **6. Contact Information QC** | Primary/Secondary contacts verified by PSV, PSV Verified By/Date | Verification Status, QC Notes |
| **7. Board Certification QC** | Board certs verified by PSV (Re-Cred only), PSV Verified By/Date | Verification Status, QC Notes |
| **8. Contract Status QC** | Contract status validated by PSV, PSV Verified By/Date | Verification Status, QC Notes |

**Component Pattern for Tiles 2-8:**
```javascript
// Generic PSV QC Tile Component Structure
{
  psvData: { /* Display only - what PSV verified */ },
  qcVerification: {
    verificationStatus: null, // Radio: Data Looks Good / Not Applicable / Missing Information
    qcReviewNotes: '',
    qcReviewedBy: 'Auto-populated',
    qcReviewedDate: 'Auto-populated'
  }
}
```

---

### Tile 9: File Upload (Reuse from PSV)

**Component:** `prm_fileUpload` (100% reusable)

---

### Tile 10: PSV QC Summary

**Component:** `prm_psvQCSummary`

**Purpose:** Final QC review decision for the entire PSV verification

**Data Sources:**
- **Aggregated:** All PSV QC tile statuses
- **Case Manager:** QC outcome

**Fields (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **PSV QC Review Outcome** | Case Manager | PSV_QC_ReviewOutcome__c | **Picklist (Approved, Returned to PSV, Needs More Info)** |
| **PSV QC Error Reasons** | Case Manager | PSV_QC_ErrorReasons__c | **Multi-select Picklist (if Returned to PSV)** |
| **PSV QC Review Notes** | Case Manager | PSV_QC_ReviewNotes__c | **Long text area** |
| PSV QC Reviewer | Case Manager | PSV_QC_ReviewedBy__c | User (auto-populated) |
| PSV QC Review Date | Case Manager | PSV_QC_ReviewDate__c | Date (auto-populated) |

**UI Features:**

**Summary Section:**
```
┌─────────────────────────────────────────────────────────┐
│ PSV QC REVIEW SUMMARY                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Tile                        Status          QC Status   │
│ ────────────────────────────────────────────────────    │
│ ✓ Practitioner Info         Verified        ✓ Good     │
│ ✓ Group/Practice            Verified        ✓ Good     │
│ ⚠ Address Verification      Verified        ⚠ Missing  │
│ ✓ Demographics & Diversity  Verified        ✓ Good     │
│ ✓ Languages Spoken          Verified        ✓ Good     │
│ ✓ Contact Information       Verified        ✓ Good     │
│ ✓ Board Certification       Verified        ✓ Good     │
│ ✓ Contract Status           Verified        ✓ Good     │
│                                                         │
│ Overall Progress: 7/8 tiles QC verified (87%)          │
│ ⚠ Incomplete tiles: Address Verification               │
│                                                         │
│ PSV Reviewer: Jane Smith                                │
│ PSV Completed: 2026-04-08 10:30 AM                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ QC OUTCOME (Editable)                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ PSV QC Review Outcome: (Required)                       │
│   ○ Approved (Send to PDA or Committee)                 │
│   ○ Returned to PSV (PSV must correct)                  │
│   ○ Needs More Information (Request from PSV)           │
│                                                         │
│ [If Returned to PSV]                                    │
│ PSV QC Error Reasons: (Multi-select)                    │
│   ☐ Practitioner Info Incorrect                         │
│   ☐ Address Data Missing                                │
│   ☐ Demographics Incomplete                             │
│   ☐ Language Proficiency Not Verified                   │
│   ☐ Contact Information Wrong                           │
│   ☐ Board Certification Expired                         │
│   ☐ Contract Status Mismatch                            │
│   ☐ Other (specify in notes)                            │
│                                                         │
│ PSV QC Review Notes: (Required if Returned)             │
│ [______________________________________________]        │
│                                                         │
│ QC Reviewed By: John Smith                              │
│ QC Review Date: 2026-04-09                              │
└─────────────────────────────────────────────────────────┘
```

**Data Structure:**
```javascript
{
  tileSummary: [
    { tileId: 'practitionerInfo', tileLabel: 'Practitioner Info', psvStatus: 'Verified', qcStatus: 'Data Looks Good' },
    { tileId: 'groupPractice', tileLabel: 'Group/Practice', psvStatus: 'Verified', qcStatus: 'Data Looks Good' },
    { tileId: 'addressVerification', tileLabel: 'Address Verification', psvStatus: 'Verified', qcStatus: 'Missing Information' },
    // ... more tiles
  ],
  overallProgress: 87,
  incompleteTiles: ['addressVerification'],
  psvReviewer: 'Jane Smith',
  psvCompletedDate: '2026-04-08T10:30:00',
  qcOutcome: {
    reviewOutcome: null, // 'Approved', 'Returned to PSV', 'Needs More Information'
    errorReasons: [], // Multi-select
    qcReviewNotes: '',
    qcReviewedBy: 'John Smith',
    qcReviewDate: '2026-04-09'
  }
}
```

**Validation Rules:**
- All required tiles must have QC verification status
- PSV QC Review Outcome is required
- If outcome = "Returned to PSV", at least one error reason must be selected
- If outcome = "Returned to PSV", QC Review Notes are required

---

## Data Storage Strategy

### Shared Custom Objects (RECOMMENDED)

**Reuse from App Review, PSV, and PDA QC:**

**1. Verification Session (`PRM_VerificationSession__c`)**
```
Fields:
- Case_Manager__c (Lookup to Case Manager)
- Flow_Type__c (Picklist: "ApplicationReview", "PSVReview", "PSVQCReview", "PDAQCReview") ← ADD PSVQCReview
- Status__c (In Progress, Completed, Abandoned)
- Started_By__c (User)
- Started_Date__c (DateTime)
- Last_Modified_Date__c (DateTime)
- Overall_Progress__c (Number: 0-100)
- Session_Data__c (Long Text Area - JSON for draft data)
```

**2. Verification Tile Status (`PRM_VerificationTileStatus__c`)**
```
Fields:
- Verification_Session__c (Master-Detail to Verification Session)
- Tile_Id__c (Text: 'practitionerInfoQC', 'addressVerificationQC', etc.)
- Tile_Label__c (Text)
- Status__c (Pending, In Progress, Completed, Error)
- Completed_By__c (User)
- Completed_Date__c (DateTime)
- Has_Warnings__c (Checkbox)
- Warning_Message__c (Text)
- Verification_Data__c (Long Text Area - JSON)
- Verification_Status__c (Picklist: Data Looks Good, Not Applicable, Missing Information)
- Notes__c (Long Text Area)
```

---

## API Design

### Apex Controllers

**1. PSVQCReviewController**

```apex
public with sharing class PSVQCReviewController {
    
    @AuraEnabled(cacheable=true)
    public static PSVQCReviewData fetchPSVQCReviewData(Id caseManagerId) {
        // Fetch Case, Case Manager, PSV output data
        // Return structured data for all QC tiles
    }
    
    @AuraEnabled
    public static void savePSVQCVerificationSession(Id caseManagerId, String sessionData) {
        // Auto-save session data
    }
    
    @AuraEnabled
    public static void savePSVQCVerificationTileStatus(
        Id sessionId, 
        String tileId, 
        String verificationStatus,
        String qcNotes
    ) {
        // Save individual tile QC verification status
    }
    
    @AuraEnabled
    public static void submitPSVQCReview(
        Id caseManagerId, 
        String qcOutcome, 
        List<String> errorReasons,
        Map<String, Object> qcVerificationData
    ) {
        // Call existing Integration Procedure
        // PRM_ReviewPSVCaseRecordsUpdate (with QC verification fields)
    }
}
```

---

## Key Differences: PSV QC vs PSV vs PDA QC

| Feature | PSV Review | PSV QC Review | PDA QC Review |
|---------|-----------|---------------|---------------|
| **Purpose** | PSV verifies CAQH data | QC verifies PSV work | QC verifies PDA network assignments |
| **Tile Count** | 10 tiles | 10 tiles | 7 tiles |
| **Focus** | Data entry/verification from CAQH | **Quality control of PSV** | Network management QC |
| **Data Entry** | Editable (PSV enters data) | **Display + Verification Status** | Mix (some display, some editable) |
| **Verification Fields** | PSV verifies against CAQH | **QC verifies PSV decisions** | QC verifies PDA decisions |
| **Integration Procedure** | PRM_ReviewPSVCaseRecordsUpdate | **Same IP** (with QC fields) | PRM_NetworkManagementQCUpdate |
| **Submit Next Step** | PDA or Committee | **PDA or Committee** (after QC approval) | Committee or Outreach |
| **Reuse from Framework** | 100% | **100%** ✅ | 100% |
| **Reuse Child Components** | 20% from App Review | **75% from PSV** (add QC layer) | 15% from PSV |

---

## Implementation Roadmap

**Total Timeline: 3 weeks** (down from 6 weeks, thanks to QC Wrapper Pattern)

### Assumptions:
- PSV Review tile framework and all PSV components are already built
- Framework (`prm_verificationDashboard`, `prm_progressHeader`, etc.) exists
- Custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`) exist

---

### Week 1: QC Wrapper Component & Configuration

**Days 1-3: Build prm_qcWrapper (Reusable QC Wrapper Component)**
- **Day 1:** Build wrapper layout structure
  - Two-section design: PSV Data (display) + QC Verification (editable)
  - Props: `component`, `psvData`, `qcVerificationStatus`, `qcNotes`, `tileLabel`, `fieldMapping`
  - Dynamic component rendering (load any PSV component in display section)
- **Day 2:** Build QC verification section
  - Radio buttons: Data Looks Good / Not Applicable / Missing Information
  - Text area: QC Review Notes (required if "Missing Information")
  - Auto-populate: QC Reviewed By, QC Reviewed Date
  - Validation logic
- **Day 3:** Wire up events and state management
  - Event handlers: `qcstatuschange`, `qcnoteschange`
  - Save/submit logic
  - Unit tests for wrapper component

**Days 4-5: Configure PSV QC Tile Metadata**
- Configure 10 PSV QC tiles in `psvQCTileConfig`
- Add `Flow_Type__c = "PSVQCReview"` to configuration
- Set up field mappings for each PSV component
- Build `PSVQCReviewController` Apex class with methods:
  - `fetchPSVQCReviewData()` - Fetch PSV output data for QC review
  - `savePSVQCVerificationSession()` - Auto-save session
  - `savePSVQCVerificationTileStatus()` - Save QC verification status per tile
  - `submitPSVQCReview()` - Submit final QC outcome

---

### Week 2: Apply QC Wrapper to 8 PSV Tiles

**Days 1-2: Apply Wrapper to Core Tiles (4 tiles @ 0.5 days each)**
- `prm_psvQCPractitionerInfo` (Practitioner Info QC) - **0.5 days**
- `prm_psvQCGroupPractice` (Group/Practice QC) - **0.5 days**
- `prm_psvQCContactInformation` (Contact Information QC) - **0.5 days**
- `prm_psvQCContractStatus` (Contract Status QC) - **0.5 days**

**Days 3-4: Apply Wrapper to Complex Tiles (4 tiles @ 0.5 days each)**
- `prm_psvQCAddressVerification` (Address Verification QC) - **0.5 days**
- `prm_psvQCDemographicsDiversity` (Demographics & Diversity QC) - **0.5 days**
- `prm_psvQCLanguagesSpoken` (Languages Spoken QC) - **0.5 days**
- `prm_psvQCBoardCertification` (Board Certification QC) - **0.5 days**

**Day 5: Unit Tests for All 8 QC Tiles**
- Test each tile independently
- Mock PSV data
- Test QC verification status change
- Test validation rules (required fields, conditional requirements)

---

### Week 3: PSV QC Summary & Testing

**Days 1-2: Build prm_psvQCSummary**
- Summary table showing all tile statuses (PSV status + QC status)
- Overall progress indicator
- QC outcome section:
  - Radio: Approved / Returned to PSV / Needs More Information
  - Multi-select: PSV QC Error Reasons (if Returned to PSV)
  - Text area: PSV QC Review Notes (required if Returned to PSV)
- Submit button with validation
- Integration with `PSVQCReviewController.submitPSVQCReview()`

**Days 3-4: Integration Testing**
- Full flow testing: Load PSV QC data → Review tiles → QC verification → Submit
- Test with realistic PSV output data (100+ addresses)
- Test resume functionality
- Test auto-save (every 2 minutes)
- Test validation rules (all required tiles completed, QC outcome required, etc.)
- Test error handling

**Day 5: Bug Fixes & Polish**
- Fix bugs from integration testing
- UI/UX polish (loading indicators, error messages, success toasts)
- Accessibility testing (WCAG compliance)
- Performance testing (page load, tile save, resume session)
- Final regression testing

---

### Deployment Strategy (Post-Development)

**Sprint 1: Parallel Run**
- Deploy PSV QC LWC alongside existing OmniScript
- "Try New PSV QC Experience" button
- Opt-in for PSV QC specialists

**Sprint 2: Full Rollout**
- Make LWC default, keep OmniScript fallback
- Monitor error rates

**Sprint 3: Full Cutover**
- Remove OmniScript

---

### Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Week 1** | 5 days | QC Wrapper Component, PSV QC Tile Configuration, Apex Controller |
| **Week 2** | 5 days | 8 QC Tiles (wrapper applied to PSV components), Unit Tests |
| **Week 3** | 5 days | PSV QC Summary, Integration Testing, Bug Fixes |
| **Total** | **3 weeks** | PSV QC Review fully functional |

**Time Savings: 50%** (from 6 weeks to 3 weeks thanks to QC Wrapper Pattern)

---

## Success Criteria

✅ **All 10 tiles functional** for PSV QC flow
✅ **Verification status fields editable** (business requirement met)
✅ **Auto-save working** every 2 minutes
✅ **Resume capability** tested
✅ **Integration with existing IP** (`PRM_ReviewPSVCaseRecordsUpdate` with QC fields)
✅ **All OmniScript functionality** preserved
✅ **Clear separation** between PSV data (display) and QC verification (editable)

---

## Migration Strategy

### Phase 1: Parallel Run (1 Sprint)
- Deploy PSV QC LWC alongside existing OmniScript
- "Try New PSV QC Experience" button

### Phase 2: Gradual Rollout (1 Sprint)
- Make LWC default, keep OmniScript fallback

### Phase 3: Full Cutover (1 Sprint)
- Remove OmniScript

---

## Open Questions / Decisions Needed

1. **QC Edit Capability:** Can QC edit PSV data or only add verification status?
2. **Verification Status Options:** Are "Data Looks Good", "Not Applicable", "Missing Information" sufficient?
3. **Returned to PSV:** What happens when PSV QC returns to PSV? Does PSV re-open the case?
4. **Board Certification:** Always shown in QC or only for Re-Cred?
5. **Integration Procedure:** Does `PRM_ReviewPSVCaseRecordsUpdate` support QC verification fields?

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-09  
**Author:** Claude Code  
**Reviewers:** [TBD]  
**Status:** DRAFT - Awaiting Stakeholder Feedback

---

## Appendix A: Complete Tile Configuration

```javascript
// PSV QC Review Tile Configuration
const psvQCTileConfig = {
  flowType: 'PSVQCReview',
  integrationProcedure: 'PRM_ReviewPSVCaseRecordsUpdate', // Same as PSV, with QC fields
  tiles: [
    {
      id: 'practitionerInfoQC',
      label: 'Practitioner Info QC',
      icon: 'standard:user',
      sequence: 1,
      required: true,
      component: 'c-prm-psv-qc-practitioner-info',
      dataKey: 'practitionerData',
      description: 'QC verify PSV practitioner information',
      estimatedTime: '5 min',
      qcMode: true // Indicates QC wrapper
    },
    {
      id: 'groupPracticeQC',
      label: 'Group/Practice QC',
      icon: 'standard:account',
      sequence: 2,
      required: true,
      component: 'c-prm-psv-qc-group-practice',
      dataKey: 'groupData',
      description: 'QC verify PSV group/practice information',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'addressVerificationQC',
      label: 'Address Verification QC',
      icon: 'standard:address',
      sequence: 3,
      required: true,
      component: 'c-prm-psv-qc-address-verification',
      dataKey: 'addressData',
      description: 'QC verify PSV address verification',
      estimatedTime: '10 min',
      warning: 'Large dataset - 100+ addresses',
      qcMode: true
    },
    {
      id: 'demographicsDiversityQC',
      label: 'Demographics & Diversity QC',
      icon: 'standard:people',
      sequence: 4,
      required: false,
      component: 'c-prm-psv-qc-demographics-diversity',
      dataKey: 'demographicsData',
      description: 'QC verify PSV demographics',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'languagesSpokenQC',
      label: 'Languages Spoken QC',
      icon: 'standard:knowledge',
      sequence: 5,
      required: false,
      component: 'c-prm-psv-qc-languages-spoken',
      dataKey: 'languagesData',
      description: 'QC verify PSV language proficiency',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'contactInformationQC',
      label: 'Contact Information QC',
      icon: 'standard:contact',
      sequence: 6,
      required: true,
      component: 'c-prm-psv-qc-contact-information',
      dataKey: 'contactData',
      description: 'QC verify PSV contact information',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'boardCertificationQC',
      label: 'Board Certification QC',
      icon: 'standard:reward',
      sequence: 7,
      required: false,
      component: 'c-prm-psv-qc-board-certification',
      dataKey: 'boardCertData',
      description: 'QC verify PSV board certifications',
      estimatedTime: '5 min',
      showWhen: 'IsRecredentialing = true OR CaseType = "QC Review"', // Always shown for QC
      qcMode: true
    },
    {
      id: 'contractStatusQC',
      label: 'Contract Status QC',
      icon: 'standard:contract',
      sequence: 8,
      required: true,
      component: 'c-prm-psv-qc-contract-status',
      dataKey: 'contractData',
      description: 'QC verify PSV contract status',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'fileUpload',
      label: 'Upload Files',
      icon: 'standard:file',
      sequence: 9,
      required: false,
      component: 'c-prm-file-upload',
      dataKey: 'fileData',
      description: 'Upload supporting documents',
      estimatedTime: '5 min',
      qcMode: false // Not QC-specific
    },
    {
      id: 'psvQCSummary',
      label: 'PSV QC Summary',
      icon: 'standard:approval',
      sequence: 10,
      required: true,
      component: 'c-prm-psv-qc-summary',
      dataKey: 'summaryData',
      description: 'PSV QC review decision',
      estimatedTime: '5 min',
      qcMode: true
    }
  ]
};
```

---

## Appendix B: Complete Reusability Matrix (All 4 Flows)

| Component | App Review | PSV | PSV QC | PDA QC | Reusable? |
|-----------|-----------|-----|--------|--------|-----------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | ✓ | **100%** ✅ |
| **prm_progressHeader** | ✓ | ✓ | ✓ | ✓ | **100%** ✅ |
| **prm_verificationTile** | ✓ | ✓ | ✓ | ✓ | **100%** ✅ |
| **prm_verificationModal** | ✓ | ✓ | ✓ | ✓ | **100%** ✅ |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | ✓ | **100%** ✅ |
| **prm_fileUpload** | ✓ | ✓ | ✓ | ✗ | **100%** ✅ |

**Overall Framework Reusability: 100% across all 4 flows** 🎉

**Implementation Time Savings:**
- App Review: 12 weeks (baseline)
- PSV Review: 10 weeks (framework reuse)
- PSV QC Review: 6 weeks (75% reuse from PSV)
- PDA QC Review: 7 weeks (framework reuse)

**Total Sequential:** 35 weeks
**Total Parallel (recommended):** ~22 weeks (build App Review framework first, then parallel PSV + QC implementations)
