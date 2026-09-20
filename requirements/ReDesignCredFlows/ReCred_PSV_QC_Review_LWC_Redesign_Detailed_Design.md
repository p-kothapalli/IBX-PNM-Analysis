# Re-Credentialing PSV QC Review LWC Redesign - Detailed Design Document

## Executive Summary

**Problem:** The current Re-Credentialing PSV Quality Control (QC) Review flow (within `PRM_PrimarySourceVerificationReview_English` when `IsRecredentialing = true` AND `CaseType = "QC Review"`) suffers from:
1. **4MB Payload Limitation** - "Save for Later" fails with large datasets (100+ addresses + Board Certifications reviewed by Re-Cred PSV)
2. **Read-Only Fields** - QC reviewers cannot edit verification status fields inline
3. **All-or-Nothing Flow** - Must complete entire QC review session (1-2 hours) or lose progress
4. **No Visual Progress** - Users don't know what's been QC-verified vs pending
5. **Complex Conditional Logic** - Re-Cred PSV QC specific fields are conditionally shown within the same OmniScript (both `IsRecredentialing = true` AND `CaseType = "QC Review"`)

**Solution:** Redesign from OmniScript to a tile-based LWC architecture where:
- Each Re-Cred PSV section has a QC verification tile (review what Re-Cred PSV did)
- **ALL VERIFICATION FIELDS ARE EDITABLE** (key business requirement)
- Saves immediately upon tile completion
- Provides visual progress tracking
- Auto-saves every 2 minutes
- Supports resume from anywhere, anytime

**Key Difference from Initial Cred PSV QC:**
- **Initial Cred PSV QC:** QC reviews 8 tiles (no Board Certification)
- **Re-Cred PSV QC:** QC reviews **11 tiles** (includes Board Certification, CMS Preclusion Review, Re-Cred specific routing)

---

## Current State Analysis

### Current OmniScript Structure

**Main OmniScript:** `PRM_PrimarySourceVerificationReview_English` (Version 47)
**Sub-OmniScript:** `PRM_PSVSubOsSummary_English` (Contains QC-specific step)

**Conditions:** 
- `IsRecredentialing = true` (Re-Cred flow)
- `CaseType = "QC Review"` (QC review mode)

### Flow Differences: Re-Cred PSV vs Re-Cred PSV QC

| Section | Re-Cred PSV (`IsRecredentialing = true`) | Re-Cred PSV QC (`IsRecredentialing = true` AND `CaseType = "QC Review"`) |
|---------|-------------------------------------------|---------------------------------------------------------------------------|
| **Practitioner Info** | Editable (PSV enters data) | **Display + Verification Status** (QC reviews) |
| **Group/Practice** | Editable | **Display + Verification Status** |
| **Addresses** | Editable (PSV adds/updates) | **Display + Verification Status** |
| **Demographics & Diversity** | Editable | **Display + Verification Status** |
| **Languages** | Editable | **Display + Verification Status** |
| **Contact Information** | Editable | **Display + Verification Status** |
| **Board Certification** 🆕 | Editable (RE-CRED ONLY) | **Display + Verification Status** (QC-SPECIFIC FOR RE-CRED) |
| **Contract Status** | Editable | **Display + Verification Status** |
| **CMS Preclusion Review** 🆕 | Editable (RE-CRED ONLY) | **Display + Verification Status** (QC-SPECIFIC FOR RE-CRED) |
| **File Upload** | Editable | **Display + Verification Status** |
| **QC Review Summary** | ✗ (Not shown) | **✓ (QC-specific step)** |

---

## Proposed LWC Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│      RE-CREDENTIALING PSV QUALITY CONTROL DASHBOARD          │
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
│  🆕 RE-CRED QC TILES                                        │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │           │  │           │  │     ✓     │              │
│  │CMS Preclu-│  │  Upload   │  │Re-Cred PSV│              │
│  │sion QC    │  │  Files    │  │  QC Summary│              │
│  └───────────┘  └───────────┘  └───────────┘              │
│                                                              │
│  [Resume Later]  [Save & Exit]  [Help]                     │
└──────────────────────────────────────────────────────────────┘
```

### Component Structure

```
prm_reCredPsvQCReviewDashboard (Parent - REUSE from PSV QC & App Review)
  ├── prm_progressHeader (REUSE 100%)
  ├── prm_verificationTile (Repeated 11x)
  │     └── prm_verificationModal (Dynamic)
  │           ├── prm_psvQCPractitionerInfo (REUSE from Initial Cred PSV QC)
  │           ├── prm_psvQCGroupPractice (REUSE from Initial Cred PSV QC)
  │           ├── prm_psvQCAddressVerification (REUSE from Initial Cred PSV QC)
  │           ├── prm_psvQCDemographicsDiversity (REUSE from Initial Cred PSV QC)
  │           ├── prm_psvQCLanguagesSpoken (REUSE from Initial Cred PSV QC)
  │           ├── prm_psvQCContactInformation (REUSE from Initial Cred PSV QC)
  │           ├── prm_reCredQCBoardCertification 🆕 (RE-CRED QC ONLY - NEW)
  │           ├── prm_psvQCContractStatus (REUSE from Initial Cred PSV QC)
  │           ├── prm_reCredQCCMSPreclusionReview 🆕 (RE-CRED QC ONLY - NEW)
  │           ├── prm_fileUpload (REUSE 100%)
  │           └── prm_reCredPsvQCSummary 🆕 (RE-CRED QC SPECIFIC - NEW)
  └── prm_navigationFooter (REUSE 100%)
```

---

## Reusability Analysis: Re-Cred PSV QC vs Initial Cred PSV QC vs Re-Cred PSV

### Framework Components (100% Reuse)

| Component | Initial Cred PSV QC | Re-Cred PSV QC | Reusable? |
|-----------|---------------------|----------------|-----------|
| **prm_verificationDashboard** | ✓ | ✓ | **100%** |
| **prm_progressHeader** | ✓ | ✓ | **100%** |
| **prm_verificationTile** | ✓ | ✓ | **100%** |
| **prm_verificationModal** | ✓ | ✓ | **100%** |
| **prm_navigationFooter** | ✓ | ✓ | **100%** |
| **prm_qcWrapper** | ✓ | ✓ | **100%** (QC wrapper pattern) |

**Framework Reuse: 100%** ✅

### Child Component Reusability

| Tile | Initial Cred PSV QC | Re-Cred PSV QC | Reusable From Initial Cred PSV QC | Reuse % |
|------|---------------------|----------------|-----------------------------------|---------|
| **Practitioner Info QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Group/Practice QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Address Verification QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Demographics & Diversity QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Languages Spoken QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Contact Information QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **Board Certification QC** 🆕 | ✗ (Not in Initial Cred) | ✓ (Display + QC) 🆕 | **New component** | **0%** (RE-CRED ONLY) |
| **Contract Status QC** | ✓ (Display + QC) | ✓ (Display + QC) | **100% reuse** | **100%** |
| **CMS Preclusion Review QC** 🆕 | ✗ (Not in Initial Cred) | ✓ (Display + QC) 🆕 | **New component** | **0%** (RE-CRED ONLY) |
| **File Upload** | ✓ | ✓ | **Shared** | **100%** |
| **PSV QC Summary** | ✓ (Initial Cred) | ✓ 🆕 (Re-Cred specific routing) | Extend `prm_psvQCSummary` | **90%** (extend for Re-Cred routing) |

**Child Component Reuse: ~80%** (8 of 11 tiles are 100% reusable from Initial Cred PSV QC, 3 new tiles for Re-Cred QC)

**Key Insight:** Re-Cred PSV QC adds **3 new QC tiles** on top of Initial Cred PSV QC:
1. Board Certification QC (Re-Cred specific)
2. CMS Preclusion Review QC (Re-Cred specific)
3. Different QC Summary (Re-Cred specific routing logic)

---

## Detailed Tile Design (Re-Cred QC Specific Tiles Only)

### Tile 7: Board Certification QC 🆕 (RE-CRED QC ONLY)

**Component:** `prm_reCredQCBoardCertification`

**Purpose:** QC reviews Board Certification verification completed by Re-Cred PSV

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│          BOARD CERTIFICATION QC REVIEW                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  RE-CRED PSV VERIFIED DATA (Display Only)               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CAQH Board Certification:                       │   │
│  │  - Board Name: American Board of Internal Med   │   │
│  │  - Board Number: ABIM123456                     │   │
│  │  - Original Cert Date: 2015-01-01               │   │
│  │  - Expiration Date: 2025-01-01                  │   │
│  │  - Board Re-Cert: ☑ Yes                         │   │
│  │                                                 │   │
│  │ Salesforce Board Certification:                 │   │
│  │  - Board Name: ABIM                             │   │
│  │  - Board Number: ABIM123456                     │   │
│  │  - Original Cert Date: 2015-01-01               │   │
│  │  - Board Re-Cert Date: 2020-01-01               │   │
│  │  - Board Expires: 2025-01-01                    │   │
│  │  - Certification Type: Primary Specialty        │   │
│  │                                                 │   │
│  │ Re-Cred PSV Verified By: Jane Smith             │   │
│  │ Re-Cred PSV Verified Date: 2026-04-09 10:30 AM │   │
│  │ Re-Cred PSV Notes: Board cert verified against  │   │
│  │                    CAQH, expiring in 2025      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  QC VERIFICATION (Editable)                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Board Certification QC Status:                  │   │
│  │   ○ Data Looks Good                             │   │
│  │   ○ Not Applicable                              │   │
│  │   ○ Missing Information                         │   │
│  │                                                 │   │
│  │ Board Certification QC Notes:                   │   │
│  │ [_____________________________________________] │   │
│  │                                                 │   │
│  │ QC Reviewed By: [Auto-populated]                │   │
│  │ QC Reviewed Date: [Auto-populated]              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit & Review Next ▼]     │
└─────────────────────────────────────────────────────────┘
```

**Fields (EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **Board Cert QC Status** | IndividualApplication | PSV_QC_BoardCert_Status__c | **Radio (Data Looks Good, Not Applicable, Missing Information)** |
| **Board Cert QC Notes** | IndividualApplication | PSV_QC_BoardCert_Notes__c | **Long text area** |
| QC Reviewed By | IndividualApplication | PSV_QC_BoardCert_ReviewedBy__c | User (auto-populated) |
| QC Reviewed Date | IndividualApplication | PSV_QC_BoardCert_ReviewedDate__c | DateTime (auto-populated) |

**Data Structure:**
```javascript
{
  // Re-Cred PSV Verified Data (Display Only)
  reCredPsvData: {
    caqhBoardCertifications: [
      {
        boardName: 'American Board of Internal Medicine',
        boardNumber: 'ABIM123456',
        originalCertDate: '2015-01-01',
        expirationDate: '2025-01-01',
        boardReCert: true
      }
    ],
    salesforceBoardCertifications: [
      {
        id: 'board001',
        boardName: 'ABIM',
        boardNumber: 'ABIM123456',
        originalCertDate: '2015-01-01',
        reCertDate: '2020-01-01',
        expirationDate: '2025-01-01',
        certificationType: 'Primary Specialty',
        isExpiringSoon: true,
        isExpired: false
      }
    ],
    reCredPsvVerifiedBy: 'Jane Smith',
    reCredPsvVerifiedDate: '2026-04-09T10:30:00',
    reCredPsvNotes: 'Board cert verified against CAQH, expiring in 2025'
  },
  // QC Verification (Editable)
  qcVerification: {
    boardCertQCStatus: null, // 'Data Looks Good', 'Not Applicable', 'Missing Information'
    boardCertQCNotes: '',
    qcReviewedBy: 'John Smith',
    qcReviewedDate: '2026-04-10T14:20:00'
  },
  tileStatus: 'Pending'
}
```

**Validation Rules:**
- Board Certification QC Status is required
- Board Cert QC Notes are required if "Missing Information" is selected

---

### Tile 9: CMS Preclusion Review QC 🆕 (RE-CRED QC ONLY)

**Component:** `prm_reCredQCCMSPreclusionReview`

**Purpose:** QC reviews CMS Preclusion Review flag set by Re-Cred PSV

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│              CMS PRECLUSION REVIEW QC                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  RE-CRED PSV VERIFIED DATA (Display Only)               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CMS Preclusion Review Required: ☑ Yes           │   │
│  │ CMS Preclusion Reason: Prior exclusion          │   │
│  │ CMS Preclusion Notes: Practitioner was on       │   │
│  │   Medicare exclusion list in 2020, need to      │   │
│  │   verify current status                         │   │
│  │                                                 │   │
│  │ Re-Cred PSV Verified By: Jane Smith             │   │
│  │ Re-Cred PSV Verified Date: 2026-04-09           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  QC VERIFICATION (Editable)                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CMS Preclusion QC Status:                       │   │
│  │   ○ Data Looks Good                             │   │
│  │   ○ Not Applicable                              │   │
│  │   ○ Missing Information                         │   │
│  │                                                 │   │
│  │ CMS Preclusion QC Notes:                        │   │
│  │ [_____________________________________________] │   │
│  │                                                 │   │
│  │ QC Reviewed By: [Auto-populated]                │   │
│  │ QC Reviewed Date: [Auto-populated]              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit & Review Next ▼]     │
└─────────────────────────────────────────────────────────┘
```

**Fields (EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **CMS Preclusion QC Status** | IndividualApplication | PSV_QC_CMSPreclusion_Status__c | **Radio (Data Looks Good, Not Applicable, Missing Information)** |
| **CMS Preclusion QC Notes** | IndividualApplication | PSV_QC_CMSPreclusion_Notes__c | **Long text area** |
| QC Reviewed By | IndividualApplication | PSV_QC_CMSPreclusion_ReviewedBy__c | User (auto-populated) |
| QC Reviewed Date | IndividualApplication | PSV_QC_CMSPreclusion_ReviewedDate__c | DateTime (auto-populated) |

**Data Structure:**
```javascript
{
  // Re-Cred PSV Verified Data (Display Only)
  reCredPsvData: {
    cmsPreclisionReviewRequired: true,
    cmsPreclisionReason: 'Prior exclusion',
    cmsPreclisionNotes: 'Practitioner was on Medicare exclusion list in 2020, need to verify current status',
    reCredPsvVerifiedBy: 'Jane Smith',
    reCredPsvVerifiedDate: '2026-04-09'
  },
  // QC Verification (Editable)
  qcVerification: {
    cmsPreclisionQCStatus: null, // 'Data Looks Good', 'Not Applicable', 'Missing Information'
    cmsPreclisionQCNotes: '',
    qcReviewedBy: 'John Smith',
    qcReviewedDate: '2026-04-10'
  },
  tileStatus: 'Pending'
}
```

---

### Tile 11: Re-Cred PSV QC Summary 🆕 (RE-CRED QC SPECIFIC)

**Component:** `prm_reCredPsvQCSummary`

**Purpose:** Final QC review decision for the entire Re-Cred PSV verification (includes Re-Cred specific routing)

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│           RE-CRED PSV QC REVIEW SUMMARY                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TILE STATUS SUMMARY                                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Tile                        Status    QC Status │   │
│  │ ──────────────────────────────────────────────  │   │
│  │ ✓ Practitioner Info         Verified  ✓ Good   │   │
│  │ ✓ Group/Practice            Verified  ✓ Good   │   │
│  │ ✓ Address Verification      Verified  ✓ Good   │   │
│  │ ✓ Demographics & Diversity  Verified  ✓ Good   │   │
│  │ ✓ Languages Spoken          Verified  ✓ Good   │   │
│  │ ✓ Contact Information       Verified  ✓ Good   │   │
│  │ ✓ Board Certification       Verified  ⚠ Missing│   │
│  │ ✓ Contract Status           Verified  ✓ Good   │   │
│  │ ✓ CMS Preclusion Review     Verified  ✓ Good   │   │
│  │                                                 │   │
│  │ Overall Progress: 8/9 tiles QC verified (89%)  │   │
│  │ ⚠ Incomplete tiles: Board Certification        │   │
│  │                                                 │   │
│  │ Re-Cred PSV Reviewer: Jane Smith                │   │
│  │ Re-Cred PSV Completed: 2026-04-09 10:30 AM     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  RE-CRED PSV QC OUTCOME (Editable)                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Re-Cred PSV QC Outcome: (Required)              │   │
│  │   ○ Approved (Send to Committee or Final Dev)   │   │
│  │   ○ Returned to Re-Cred PSV (PSV must correct)  │   │
│  │   ○ Needs More Information                      │   │
│  │                                                 │   │
│  │ [If Returned to Re-Cred PSV]                    │   │
│  │ Re-Cred PSV QC Error Reasons: (Multi-select)    │   │
│  │   ☐ Practitioner Info Incorrect                 │   │
│  │   ☐ Address Data Missing                        │   │
│  │   ☐ Board Certification Issues                  │   │
│  │   ☐ CMS Preclusion Review Incomplete            │   │
│  │   ☐ Demographics Incomplete                     │   │
│  │   ☐ Language Proficiency Not Verified           │   │
│  │   ☐ Contact Information Wrong                   │   │
│  │   ☐ Contract Status Mismatch                    │   │
│  │   ☐ Other (specify in notes)                    │   │
│  │                                                 │   │
│  │ Re-Cred PSV QC Review Notes: (Required if Ret'd)│   │
│  │ [______________________________________________]│   │
│  │                                                 │   │
│  │ QC Reviewed By: John Smith                      │   │
│  │ QC Review Date: 2026-04-10                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit Re-Cred PSV QC]      │
└─────────────────────────────────────────────────────────┘
```

**Re-Cred PSV QC Specific Outcome Options:**

| Outcome | Description | Next Step | When to Use |
|---------|-------------|-----------|-------------|
| **Approved** | Re-Cred PSV QC approved | → Committee or Final Development | Standard Re-Cred QC approval |
| **Returned to Re-Cred PSV** | Board cert or CMS preclusion issues | → Re-Cred PSV Team | Board cert expired, CMS preclusion incomplete |
| **Needs More Information** | Missing information | → Re-Cred PSV Team | Need more info from Re-Cred PSV |

**Validation Rules:**
- All required tiles must have QC verification status
- Re-Cred PSV QC Outcome is required
- If outcome = "Returned to Re-Cred PSV", at least one error reason must be selected
- If outcome = "Returned to Re-Cred PSV", QC Review Notes are required

---

## Reusability Impact on Timeline

### Timeline Comparison

| Flow | Timeline | Explanation |
|------|----------|-------------|
| **Initial Cred PSV QC** | 3 weeks | Reuse framework + Build QC wrapper + Apply to 8 PSV tiles + QC summary + Testing |
| **Re-Cred PSV QC** | **2 weeks** | Reuse framework + Reuse QC wrapper + Reuse 8 of 11 QC tiles + Build 3 Re-Cred QC tiles |

**Time Savings: 1 week** (from 3 weeks to 2 weeks) thanks to 73% tile reusability from Initial Cred PSV QC

---

## Implementation Roadmap

**Total Timeline: 2 weeks** (down from 3 weeks for Initial Cred PSV QC, thanks to reusability)

### Assumptions:
- Initial Cred PSV QC framework and all Initial Cred PSV QC components are already built
- QC wrapper pattern (`prm_qcWrapper`) exists
- Framework (`prm_verificationDashboard`, `prm_progressHeader`, etc.) exists
- Custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`) exist

---

### Week 1: Configuration & Re-Cred QC Specific Tiles

**Days 1-2: Configure Re-Cred PSV QC Tile Metadata**
- Configure 11 Re-Cred PSV QC tiles in `reCredPsvQCTileConfig`
- Add `Flow_Type__c = "ReCredPSVQCReview"` to configuration
- Update `prm_verificationDashboard` to support Re-Cred PSV QC configuration

**Days 2-3: Build prm_reCredQCBoardCertification**
- Re-Cred PSV Board Certification display section (read-only)
  - CAQH Board Certification (display)
  - Salesforce Board Certification (display)
  - Re-Cred PSV Verified By/Date (display)
- QC Verification section (editable)
  - Board Cert QC Status (radio + notes)
- Apply QC wrapper pattern
- Unit tests

**Day 4: Build prm_reCredQCCMSPreclusionReview**
- Re-Cred PSV CMS Preclusion display section (read-only)
- QC Verification section (editable)
  - CMS Preclusion QC Status (radio + notes)
- Apply QC wrapper pattern
- Unit tests

**Day 5: Build prm_reCredPsvQCSummary (Extend prm_psvQCSummary)**
- Extend `prm_psvQCSummary` component from Initial Cred PSV QC
- Override outcome logic for Re-Cred routing:
  - Approved (→ Committee or Final Development)
  - Returned to Re-Cred PSV
  - Needs More Information
- Add Re-Cred specific error reasons:
  - Board Certification Issues
  - CMS Preclusion Review Incomplete
- Unit tests

---

### Week 2: Integration Testing & Deployment

**Days 1-2: Build ReCredPSVQCReviewController Apex Class**
- Apex controller methods:
  - `fetchReCredPSVQCReviewData()` - Fetch Re-Cred PSV output data for QC review
  - `saveReCredPSVQCVerificationSession()` - Auto-save session
  - `saveReCredPSVQCVerificationTileStatus()` - Save QC verification status per tile
  - `submitReCredPSVQCReview()` - Submit final QC outcome with Re-Cred routing logic
- Integration with existing Integration Procedure (may need updates for Re-Cred QC fields)
- Unit tests for Apex controllers

**Days 3-4: Full Flow Integration Testing**
- Test full Re-Cred PSV QC flow: Load Re-Cred PSV QC data → Review tiles → QC verification → Submit
- Test all 3 Re-Cred QC specific tiles (Board Cert QC, CMS Preclusion QC, Re-Cred QC Summary)
- Test routing to Committee vs Returned to Re-Cred PSV vs Needs More Info
- Test resume functionality
- Test auto-save (every 2 minutes)
- Test with realistic Re-Cred PSV data:
  - 100+ addresses
  - Multiple board certifications
  - CMS Preclusion Review required
- Test validation rules

**Day 5: Bug Fixes & Deployment Preparation**
- Fix bugs from integration testing
- UI/UX polish (loading indicators, error messages, success toasts)
- Accessibility testing (WCAG compliance)
- Performance testing
- Final regression testing
- Prepare deployment artifacts
- Update user training materials
- Create "Try New Re-Cred PSV QC Experience" button

---

### Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Week 1** | 5 days | Re-Cred PSV QC Configuration, 3 Re-Cred QC Specific Tiles (Board Cert QC, CMS Preclusion QC, Re-Cred QC Summary) |
| **Week 2** | 5 days | Apex Controller, Full Flow Testing, Bug Fixes, Deployment Prep |
| **Total** | **2 weeks** | Re-Cred PSV QC Review fully functional |

**Time Savings: 1 week** (from 3 weeks for Initial Cred PSV QC to 2 weeks for Re-Cred PSV QC thanks to 73% tile reusability)

---

## Data Storage Strategy

### Shared Custom Objects (RECOMMENDED)

**Reuse from App Review, Initial Cred PSV, PSV QC, Re-Cred PSV, PDA QC:**

**1. Verification Session (`PRM_VerificationSession__c`)**
```
Fields:
- Case_Manager__c (Lookup to Case Manager)
- Flow_Type__c (Picklist: "ApplicationReview", "PSVReview", "PSVQCReview", "ReCredPSVReview", "ReCredPSVQCReview", "PDAQCReview") ← ADD ReCredPSVQCReview
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
- Tile_Id__c (Text: 'practitionerInfoQC', 'boardCertificationQC', 'cmsPreclisionQC', etc.)
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

## Success Criteria

### Functional Requirements

✅ **All 11 tiles functional** for Re-Cred PSV QC flow
✅ **Board Certification QC working** (Re-Cred specific)
✅ **CMS Preclusion Review QC functional** (Re-Cred specific)
✅ **Re-Cred specific routing working** (Approved, Returned to Re-Cred PSV, Needs More Info)
✅ **All verification fields editable** (business requirement met)
✅ **Auto-save working** every 2 minutes
✅ **Resume capability** tested and verified
✅ **Integration with existing IP** (may need updates for Re-Cred QC)
✅ **All OmniScript functionality** preserved

### Performance Requirements

✅ **0 save failures** (no 4MB limit)
✅ **Page load < 3 seconds** (with lazy loading)
✅ **Save tile < 2 seconds** (for normal datasets)
✅ **Resume session < 3 seconds**
✅ **Handle 200+ addresses + Board Certifications** without timeout

### User Experience Requirements

✅ **Visual progress tracking**
✅ **Tile-based navigation** (non-linear)
✅ **QC wrapper pattern** (display + verification)
✅ **Outcome-specific routing explanations**
✅ **Board Certification expiration warnings**
✅ **CMS Preclusion Review flagging**

---

## Overall Timeline Summary (All 7 Flows)

| Flow | Timeline | Key Factor |
|------|----------|------------|
| **App Review** | 12 weeks | Baseline (builds shared framework & components) |
| **Initial Cred PSV** | 7 weeks | 80-100% reuse of shared components |
| **Re-Cred PSV** | 4 weeks | 73% reuse from Initial Cred PSV + 3 new tiles |
| **Initial Cred PSV QC** | 3 weeks | QC wrapper pattern (95% reuse from PSV) |
| **Re-Cred PSV QC** | **2 weeks** | **73% reuse from Initial Cred PSV QC + 3 new QC tiles** |
| **PDA QC Review** | 7 weeks | Limited reuse but simpler tiles |
| **Re-Cred Network Mgmt QC** | 5 weeks | Similar to PDA QC but for Re-Cred context |
| **Total Sequential** | **40 weeks** | - |
| **Total Parallel** | **~20 weeks** | Build flows in parallel after framework |

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-10  
**Author:** Claude Code  
**Reviewers:** [TBD]  
**Status:** DRAFT - Awaiting Stakeholder Feedback

---

## Appendix A: Complete Tile Configuration

```javascript
// Re-Cred PSV QC Review Tile Configuration
const reCredPsvQCTileConfig = {
  flowType: 'ReCredPSVQCReview',
  integrationProcedure: 'PRM_ReviewPSVCaseRecordsUpdate', // Same as PSV, with QC fields
  tiles: [
    {
      id: 'practitionerInfoQC',
      label: 'Practitioner Info QC',
      icon: 'standard:user',
      sequence: 1,
      required: true,
      component: 'c-prm-psv-qc-practitioner-info', // REUSE from Initial Cred PSV QC
      dataKey: 'practitionerData',
      description: 'QC verify Re-Cred PSV practitioner information',
      estimatedTime: '5 min',
      qcMode: true
    },
    {
      id: 'groupPracticeQC',
      label: 'Group/Practice QC',
      icon: 'standard:account',
      sequence: 2,
      required: true,
      component: 'c-prm-psv-qc-group-practice', // REUSE from Initial Cred PSV QC
      dataKey: 'groupData',
      description: 'QC verify Re-Cred PSV group/practice information',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'addressVerificationQC',
      label: 'Address Verification QC',
      icon: 'standard:address',
      sequence: 3,
      required: true,
      component: 'c-prm-psv-qc-address-verification', // REUSE from Initial Cred PSV QC
      dataKey: 'addressData',
      description: 'QC verify Re-Cred PSV address verification',
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
      component: 'c-prm-psv-qc-demographics-diversity', // REUSE from Initial Cred PSV QC
      dataKey: 'demographicsData',
      description: 'QC verify Re-Cred PSV demographics',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'languagesSpokenQC',
      label: 'Languages Spoken QC',
      icon: 'standard:knowledge',
      sequence: 5,
      required: false,
      component: 'c-prm-psv-qc-languages-spoken', // REUSE from Initial Cred PSV QC
      dataKey: 'languagesData',
      description: 'QC verify Re-Cred PSV language proficiency',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'contactInformationQC',
      label: 'Contact Information QC',
      icon: 'standard:contact',
      sequence: 6,
      required: true,
      component: 'c-prm-psv-qc-contact-information', // REUSE from Initial Cred PSV QC
      dataKey: 'contactData',
      description: 'QC verify Re-Cred PSV contact information',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'boardCertificationQC', // 🆕 RE-CRED QC SPECIFIC
      label: 'Board Certification QC',
      icon: 'standard:reward',
      sequence: 7,
      required: true,
      component: 'c-prm-re-cred-qc-board-certification', // NEW for Re-Cred QC
      dataKey: 'boardCertData',
      description: 'QC verify Re-Cred PSV board certifications (RE-CRED QC ONLY)',
      estimatedTime: '5 min',
      showWhen: 'IsRecredentialing = true AND CaseType = "QC Review"',
      qcMode: true,
      isReCredQCOnly: true
    },
    {
      id: 'contractStatusQC',
      label: 'Contract Status QC',
      icon: 'standard:contract',
      sequence: 8,
      required: true,
      component: 'c-prm-psv-qc-contract-status', // REUSE from Initial Cred PSV QC
      dataKey: 'contractData',
      description: 'QC verify Re-Cred PSV contract status',
      estimatedTime: '3 min',
      qcMode: true
    },
    {
      id: 'cmsPreclisionQC', // 🆕 RE-CRED QC SPECIFIC
      label: 'CMS Preclusion Review QC',
      icon: 'standard:people',
      sequence: 9,
      required: false,
      component: 'c-prm-re-cred-qc-cms-preclusion-review', // NEW for Re-Cred QC
      dataKey: 'cmsPreclisionData',
      description: 'QC verify CMS preclusion screening (RE-CRED QC ONLY)',
      estimatedTime: '2 min',
      showWhen: 'IsRecredentialing = true AND CaseType = "QC Review" AND CMSPreclusionReview = true',
      qcMode: true,
      isReCredQCOnly: true
    },
    {
      id: 'fileUpload',
      label: 'Upload Files',
      icon: 'standard:file',
      sequence: 10,
      required: false,
      component: 'c-prm-file-upload', // REUSE from App Review
      dataKey: 'fileData',
      description: 'Upload supporting documents',
      estimatedTime: '5 min',
      qcMode: false
    },
    {
      id: 'reCredPsvQCSummary', // 🆕 RE-CRED QC SPECIFIC
      label: 'Re-Cred PSV QC Summary',
      icon: 'standard:approval',
      sequence: 11,
      required: true,
      component: 'c-prm-re-cred-psv-qc-summary', // NEW for Re-Cred QC (extends prm_psvQCSummary)
      dataKey: 'summaryData',
      description: 'Re-Cred PSV QC review decision',
      estimatedTime: '5 min',
      qcMode: true,
      isReCredQCOnly: true
    }
  ]
};
```

---

## Appendix B: Comparison Matrix - Initial Cred PSV QC vs Re-Cred PSV QC

| Feature | Initial Cred PSV QC | Re-Cred PSV QC | Difference |
|---------|---------------------|----------------|------------|
| **Tile Count** | 10 tiles | 11 tiles | +1 (Board Cert QC, CMS Preclusion QC, Re-Cred QC Summary split) |
| **Board Certification QC** | ✗ | ✓ 🆕 | Re-Cred QC ONLY |
| **CMS Preclusion Review QC** | ✗ | ✓ 🆕 | Re-Cred QC ONLY |
| **QC Outcome Options** | Approved / Returned to PSV / Needs More Info | Approved / Returned to Re-Cred PSV / Needs More Info | Different routing logic |
| **QC Error Reasons** | 8 options | +2 Re-Cred options (Board Cert Issues, CMS Preclusion Incomplete) | Re-Cred specific |
| **Reusable Tiles** | N/A | 8 of 11 tiles (73%) | High reusability |
| **Implementation Time** | 3 weeks | 2 weeks | 1 week saved |

**Overall Improvement:** 🚀 **33% faster implementation** (2 weeks vs 3 weeks) thanks to tile reusability
