# Re-Credentialing PSV Review LWC Redesign - Detailed Design Document

## Executive Summary

**Problem:** The current Re-Credentialing Primary Source Verification (PSV) Review OmniScript (`PRM_PrimarySourceVerificationReview_English` when `IsRecredentialing = true`) suffers from:
1. **4MB Payload Limitation** - "Save for Later" fails with large datasets (100+ practice locations + Board Certifications)
2. **Read-Only Fields** - Business users cannot edit fields during Re-Cred PSV review, forcing them to exit and manually update records
3. **All-or-Nothing Flow** - 2-4 hour sessions with no ability to pause and resume
4. **No Visual Progress** - Users don't know what's verified vs pending
5. **Complex Conditional Logic** - Re-Cred specific fields (Board Certification, CMS Preclusion, Medical Director Review) are conditionally shown within same OmniScript as Initial Cred

**Solution:** Redesign from OmniScript to a tile-based LWC architecture where:
- Each verification step is independent and can be completed in any order
- **ALL FIELDS ARE EDITABLE** (key business requirement)
- Saves immediately upon tile completion
- Provides visual progress tracking
- Auto-saves every 2 minutes
- Supports resume from anywhere, anytime

---

## Current State Analysis

### Current OmniScript Structure

**Main OmniScript:** `PRM_PrimarySourceVerificationReview_English` (Version 47)

**Condition:** `IsRecredentialing = true`

### Key Differences: Re-Cred PSV vs Initial Cred PSV

| Feature | Initial Cred PSV | Re-Cred PSV (`IsRecredentialing = true`) |
|---------|-----------------|------------------------------------------|
| **Board Certification Section** | ✗ (Not shown) | **✓ (SHOWN for Re-Cred)** |
| **CMS Preclusion Review** | ✗ | **✓ (Re-Cred specific)** |
| **Medical Director Review** | ✗ | **✓ (Can route to Medical Director)** |
| **File Notes Section** | ✗ | **✓ (`showFileNotes = true` for Re-Cred)** |
| **Re-Cred File Attachments** | ✗ | **✓ (Re-Cred specific attachments)** |
| **DataRaptor Transforms** | Standard PSV transforms | **Additional: `DRTransformReCredData`, `DRTransformRecredFiles`** |
| **Submit Next Step** | PDA or Committee | **Medical Director Review, PSV QC, Provider Outreach, Final Development** |
| **Title Labels** | "PSV - Notes" | **"Re-Cred PSV - Notes"** |

### Re-Cred Specific Flow Steps

**1. Standard PSV Sections (Same as Initial Cred):**
- Practitioner Information Review
- Group/Practice Information
- Address Verification
- Demographics & Diversity Information
- Languages Spoken
- Contact Information
- Contract Status Validation

**2. Re-Cred ONLY Sections:**

**Board Certification Verification** (Shown ONLY when `IsRecredentialing = true`)
- **CAQH Board Certification Table** (Display only):
  - Board Certification Name (from CAQH)
  - Board Certification Number (from CAQH)
  - Original Certification Date
  - Expiration Date
  - Board Re-Cert (Checkbox)
- **Salesforce Board Certification** (Editable):
  - Board Certification Name (Lookup)
  - Board Certification Number
  - Original Certification Date
  - Board Re-Cert Date
  - Board Expires
  - Certification Type (Picklist)
- **Board Certification Verification** (Radio):
  - Data Looks Good
  - Not Applicable
  - Missing Information
- **Board Certification Note** (Text Area)

**CMS Preclusion Review** (Conditional for Re-Cred)
- `CMSPreclusionReview` flag
- Determines if practitioner needs CMS preclusion screening

**Re-Cred File Attachments** (Required for Re-Cred)
- `showFileNotes = IF(IsRecredentialing == true, true, false)`
- Re-Cred specific file upload section
- Different file requirements than Initial Cred

**3. Final Outcome (Different from Initial Cred):**

**Re-Cred Specific Outcome:**
- `ReCredProceedTo` (Picklist):
  - **Medical Director Review** (Additional step for complex Re-Cred cases)
  - **PSV QC** (Quality Control review)
  - **Provider Outreach Needed** (Missing information)
  - **Final Development** (Skip QC, proceed to final steps)

---

## Proposed LWC Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│         RE-CREDENTIALING PRIMARY SOURCE VERIFICATION          │
│                        DASHBOARD                              │
├──────────────────────────────────────────────────────────────┤
│  Progress: ████████░░ 80% Complete                          │
│  Auto-saved 2 minutes ago                                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │     ✓     │  │     ✓     │  │     ⚠     │  │          ││
│  │Practitioner│ │   Group   │  │ Address   │  │Demographics│
│  │   Info    │  │ /Practice │  │Verification│ │ & Diversity││
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘│
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │           │  │           │  │           │  │          ││
│  │Languages  │  │  Contact  │  │   Board   │  │Contract  ││
│  │  Spoken   │  │Information│  │   Cert    │  │ Status   ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘│
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  🆕 RE-CRED     │  │                 │  │              ││
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │           │  │           │  │     ✓     │              │
│  │CMS Preclu-│  │  Upload   │  │Re-Cred PSV│              │
│  │sion Review│  │  Files    │  │Confirmation│              │
│  └───────────┘  └───────────┘  └───────────┘              │
│                                                              │
│  [Resume Later]  [Save & Exit]  [Help]                     │
└──────────────────────────────────────────────────────────────┘
```

### Component Structure

```
prm_reCredPsvReviewDashboard (Parent - REUSE from PSV & App Review)
  ├── prm_progressHeader (REUSE 100%)
  ├── prm_verificationTile (Repeated 11x)
  │     └── prm_verificationModal (Dynamic)
  │           ├── prm_psvPractitionerInfo (REUSE from Initial Cred PSV)
  │           ├── prm_psvGroupPractice (REUSE from Initial Cred PSV)
  │           ├── prm_psvAddressVerification (REUSE from Initial Cred PSV)
  │           ├── prm_psvDemographicsDiversity (REUSE from Initial Cred PSV)
  │           ├── prm_psvLanguagesSpoken (REUSE from Initial Cred PSV)
  │           ├── prm_psvContactInformation (REUSE from Initial Cred PSV)
  │           ├── prm_reCredBoardCertification 🆕 (RE-CRED ONLY)
  │           ├── prm_psvContractStatus (REUSE from Initial Cred PSV)
  │           ├── prm_reCredCMSPreclusionReview 🆕 (RE-CRED ONLY)
  │           ├── prm_fileUpload (REUSE from App Review)
  │           └── prm_reCredFinalConfirmation 🆕 (RE-CRED specific submit logic)
  └── prm_navigationFooter (REUSE 100%)
```

---

## Reusability Analysis: Re-Cred PSV vs Initial Cred PSV vs App Review

### Framework Components (100% Reuse)

| Component | App Review | Initial Cred PSV | Re-Cred PSV | Reusable? |
|-----------|-----------|-----------------|-------------|-----------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | **100%** |
| **prm_progressHeader** | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationTile** | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationModal** | ✓ | ✓ | ✓ | **100%** |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | **100%** |

**Framework Reuse: 100%** ✅

### Child Component Reusability

| Tile | Initial Cred PSV | Re-Cred PSV | Reusable From Initial Cred PSV | Reuse % |
|------|-----------------|-------------|-------------------------------|---------|
| **Practitioner Info** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Group/Practice** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Address Verification** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Demographics & Diversity** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Languages Spoken** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Contact Information** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **Board Certification** | ✗ (Not in Initial Cred) | ✓ 🆕 (RE-CRED ONLY) | **New component** | **0%** |
| **Contract Status** | ✓ (Editable) | ✓ (Editable) | **100% reuse** | **100%** |
| **CMS Preclusion Review** | ✗ (Not in Initial Cred) | ✓ 🆕 (RE-CRED ONLY) | **New component** | **0%** |
| **File Upload** | ✓ | ✓ | **Shared** | **100%** |
| **Final Confirmation** | ✓ (PDA/Committee) | ✓ 🆕 (Medical Director/QC/Outreach) | Extend `prm_finalSubmitBase` | **80%** |

**Child Component Reuse: ~80%** (8 of 11 tiles are 100% reusable from Initial Cred PSV, 3 new tiles for Re-Cred)

**Key Insight:** Re-Cred PSV adds **3 new tiles** on top of Initial Cred PSV:
1. Board Certification Verification
2. CMS Preclusion Review
3. Different Final Confirmation (routing logic)

---

## Detailed Tile Design (Re-Cred Specific Tiles Only)

### Tile 8: Board Certification Verification 🆕 (RE-CRED ONLY)

**Component:** `prm_reCredBoardCertification`

**Show When:** `IsRecredentialing = true`

**Purpose:** Verify board certifications from CAQH and update Salesforce BoardCertification records

**Data Sources:**
- **CAQH:** Board certifications
- **Salesforce:** BoardCertification

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│                BOARD CERTIFICATION VERIFICATION          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CAQH BOARD CERTIFICATION (Display Only)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Board Name: American Board of Internal Medicine │   │
│  │ Board Number: ABIM123456                        │   │
│  │ Original Cert Date: 2015-01-01                  │   │
│  │ Expiration Date: 2025-01-01                     │   │
│  │ Board Re-Cert: ☑ Yes                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  SALESFORCE BOARD CERTIFICATION (Editable)              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Board Certification Name: [Lookup: ABIM     ]   │   │
│  │ Board Number: [ABIM123456                   ]   │   │
│  │ Original Cert Date: [2015-01-01] (Date)         │   │
│  │ Board Re-Cert Date: [2020-01-01] (Date)         │   │
│  │ Board Expires: [2025-01-01] (Date)              │   │
│  │ Certification Type: [Primary Specialty    ▼]    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  VERIFICATION STATUS (Editable)                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Board Certification Verification:               │   │
│  │   ○ Data Looks Good                             │   │
│  │   ○ Not Applicable                              │   │
│  │   ○ Missing Information                         │   │
│  │                                                 │   │
│  │ Board Certification Note:                       │   │
│  │ [_____________________________________________] │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Add Board Certification]  [Remove]                   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit & Review Next ▼]     │
└─────────────────────────────────────────────────────────┘
```

**Fields (ALL EDITABLE):**

| Field | CAQH | Salesforce Object | Field Name | Edit Behavior |
|-------|------|------------------|------------|---------------|
| **CAQH Board Name** | ✓ (Display) | N/A | N/A | Display only |
| **CAQH Board Number** | ✓ (Display) | N/A | N/A | Display only |
| **CAQH Original Cert Date** | ✓ (Display) | N/A | N/A | Display only |
| **CAQH Expiration Date** | ✓ (Display) | N/A | N/A | Display only |
| **CAQH Board Re-Cert** | ✓ (Display) | N/A | N/A | Display only (Checkbox) |
| **Board Certification Name** | Manual | BoardCertification | BoardName__c | **Lookup/Combobox** |
| **Board Number** | Manual | BoardCertification | CertificationNumber__c | **Text input** |
| **Original Cert Date** | Manual | BoardCertification | OriginalCertificationDate__c | **Date picker** |
| **Board Re-Cert Date** | Manual | BoardCertification | RecertificationDate__c | **Date picker** |
| **Board Expires** | Manual | BoardCertification | ExpirationDate__c | **Date picker** |
| **Certification Type** | Manual | BoardCertification | CertificationType__c | **Picklist (Primary, Secondary, etc.)** |
| **Verification Status** | Manual | IndividualApplication | PSV_BoardCert_Status__c | **Radio (Data Looks Good, Not Applicable, Missing Information)** |
| **Board Cert Note** | Manual | IndividualApplication | PSV_BoardCert_Notes__c | **Long text area** |

**UI Features:**
- **Side-by-side comparison:** CAQH (left) ↔ Salesforce (right)
- **Auto-populate from CAQH** with "Copy from CAQH" button
- **Multiple Board Certifications:** Lightning Datatable showing all board certs
- **"Add Board Certification"** button (manual entry if CAQH doesn't have it)
- **"Remove"** action for each board cert
- **Warning badge** if expiration date is within 90 days
- **Error badge** if expired

**Data Structure:**
```javascript
{
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
      isExpiringSoon: false,
      isExpired: false,
      action: 'none' // 'add', 'update', 'remove'
    }
  ],
  verificationStatus: 'Data Looks Good',
  boardCertNote: '',
  tileStatus: 'Completed'
}
```

**Validation Rules:**
- If Verification Status = "Data Looks Good", at least one board certification must be entered in Salesforce
- If expiration date < Today, mark as expired
- If expiration date < Today + 90 days, mark as expiring soon

---

### Tile 9: CMS Preclusion Review 🆕 (RE-CRED ONLY)

**Component:** `prm_reCredCMSPreclusionReview`

**Show When:** `IsRecredentialing = true` AND `CMSPreclusionReview = true`

**Purpose:** Flag practitioner for CMS preclusion screening if required

**Data Sources:**
- **Salesforce:** Case Manager, IndividualApplication

**Fields (EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **CMS Preclusion Review Required** | Case Manager | CMSPreclusionReview__c | **Checkbox** |
| **CMS Preclusion Reason** | Case Manager | CMSPreclusionReason__c | **Picklist (if checkbox = true)** |
| **CMS Preclusion Notes** | Case Manager | CMSPreclusionNotes__c | **Long text area** |

**UI Features:**
- Simple checkbox: "CMS Preclusion Review Required"
- If checked, show reason picklist and notes
- Information banner: "Checking this will route to CMS Preclusion screening before final approval"

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│              CMS PRECLUSION REVIEW                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ℹ️ CMS Preclusion screening verifies that the         │
│     practitioner is not on Medicare/Medicaid            │
│     exclusion lists.                                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ☑ CMS Preclusion Review Required                │   │
│  │                                                 │   │
│  │ CMS Preclusion Reason:                          │   │
│  │ [Prior exclusion                              ▼]│   │
│  │                                                 │   │
│  │ CMS Preclusion Notes:                           │   │
│  │ [_____________________________________________] │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit & Review Next ▼]     │
└─────────────────────────────────────────────────────────┘
```

**Data Structure:**
```javascript
{
  cmsPreclisionReviewRequired: false,
  cmsPreclisionReason: '', // Picklist: 'Prior exclusion', 'State license issue', 'Other'
  cmsPreclisionNotes: '',
  tileStatus: 'Pending'
}
```

---

### Tile 11: Re-Cred PSV Final Confirmation 🆕 (RE-CRED SPECIFIC ROUTING)

**Component:** `prm_reCredFinalConfirmation`

**Purpose:** Submit Re-Cred PSV review with Re-Cred specific routing options

**Data Sources:**
- **Aggregated data from all tiles**

**Fields (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| CAQH Validation Confirmed | IndividualApplication | CAQH_Validated__c | Checkbox (required) |
| **Re-Cred PSV Outcome** | Case Manager | ReCredProceedTo__c | **Picklist (Medical Director Review, PSV QC, Provider Outreach, Final Development)** |
| PSV Review Date | IndividualApplication | PSV_ReviewDate__c | Date (auto-populated) |
| PSV Reviewer | IndividualApplication | PSV_ReviewedBy__c | User lookup (auto-populated) |
| **Medical Director Review Required** | Case Manager | MedicalDirectorReview__c | Checkbox (auto-populated if outcome = "Medical Director Review") |
| **CMS Preclusion Review Required** | Case Manager | CMSPreclusionReview__c | Checkbox (auto-populated from Tile 9) |
| Final Notes | Case Manager | PSV_FinalNotes__c | Long text area |

**Re-Cred Specific Outcome Options:**

| Outcome | Description | Next Step | When to Use |
|---------|-------------|-----------|-------------|
| **Medical Director Review** | Complex Re-Cred case requiring Medical Director approval | → Medical Director Review → QC | Board cert issues, CMS preclusion, credential gaps |
| **PSV QC** | Standard Re-Cred case | → PSV QC Review | Normal Re-Cred path (most common) |
| **Provider Outreach Needed** | Missing information | → Outreach Team | Documents missing, need more info from provider |
| **Final Development** | Skip QC, proceed to final steps | → Final Development | Low-risk Re-Cred, no QC needed |

**UI Features:**
- Summary table showing all tile statuses
- Red warning for incomplete/pending tiles
- **Outcome-specific routing explanation:**
  - "Medical Director Review" → Shows warning: "This will route to Medical Director before QC"
  - "Provider Outreach Needed" → Shows warning: "Case will be put On Hold"
  - "Final Development" → Shows warning: "This will skip QC review"
- "Review Tile" quick action to jump back to incomplete tiles
- Confirmation dialog: "Are you sure you want to submit?"
- Submit button disabled until all required tiles are completed

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│           RE-CRED PSV FINAL CONFIRMATION                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TILE STATUS SUMMARY                                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Tile                        Status              │   │
│  │ ──────────────────────────────────────────────  │   │
│  │ ✓ Practitioner Info         Completed           │   │
│  │ ✓ Group/Practice            Completed           │   │
│  │ ✓ Address Verification      Completed           │   │
│  │ ✓ Demographics & Diversity  Completed           │   │
│  │ ✓ Languages Spoken          Completed           │   │
│  │ ✓ Contact Information       Completed           │   │
│  │ ✓ Board Certification       Completed (RE-CRED)│   │
│  │ ✓ Contract Status           Completed           │   │
│  │ ✓ CMS Preclusion Review     Completed (RE-CRED)│   │
│  │ ✓ File Upload               Completed           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  RE-CRED PSV OUTCOME (Required)                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Re-Cred PSV Outcome:                            │   │
│  │   ○ Medical Director Review (Complex cases)     │   │
│  │   ○ PSV QC (Standard Re-Cred path)              │   │
│  │   ○ Provider Outreach Needed (Missing info)     │   │
│  │   ○ Final Development (Skip QC)                 │   │
│  │                                                 │   │
│  │ ⚠️ Medical Director Review: This will route to  │   │
│  │    Medical Director before QC                   │   │
│  │                                                 │   │
│  │ ☑ CAQH Validation Confirmed (Required)          │   │
│  │ ☑ Medical Director Review Required              │   │
│  │ ☑ CMS Preclusion Review Required                │   │
│  │                                                 │   │
│  │ Final Notes:                                    │   │
│  │ [_____________________________________________] │   │
│  │                                                 │   │
│  │ PSV Reviewed By: [Auto-populated]               │   │
│  │ PSV Review Date: [Auto-populated]               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]  [Save Draft]  [Submit Re-Cred PSV]         │
└─────────────────────────────────────────────────────────┘
```

**Data Structure:**
```javascript
{
  tileSummary: [
    { tileId: 'practitionerInfo', tileLabel: 'Practitioner Info', status: 'Completed' },
    { tileId: 'boardCertification', tileLabel: 'Board Certification (RE-CRED)', status: 'Completed' },
    { tileId: 'cmsPreclisionReview', tileLabel: 'CMS Preclusion Review (RE-CRED)', status: 'Completed' },
    // ... more tiles
  ],
  reCredPSVOutcome: 'Medical Director Review', // or 'PSV QC', 'Provider Outreach Needed', 'Final Development'
  caqhValidationConfirmed: true,
  medicalDirectorReviewRequired: true, // Auto-set if outcome = "Medical Director Review"
  cmsPreclisionReviewRequired: true, // From Tile 9
  psvReviewDate: '2026-04-09',
  psvReviewer: 'Jane Smith',
  finalNotes: '',
  allTilesCompleted: true,
  incompleteTiles: []
}
```

**Validation Rules:**
- All required tiles must be "Completed"
- CAQH Validation Confirmed must be checked
- Re-Cred PSV Outcome must be selected
- If Board Certification verification status = "Missing Information", cannot select "Final Development"

---

## Reusability Impact on Timeline

### Timeline Comparison

| Flow | Timeline | Explanation |
|------|----------|-------------|
| **Initial Cred PSV** | 7 weeks | Reuse framework (100%) + Extend shared components + Build 7 PSV-specific tiles |
| **Re-Cred PSV** | **4 weeks** | Reuse framework (100%) + Reuse 8 of 11 tiles (100%) + Build 3 Re-Cred specific tiles |

**Time Savings: 3 weeks** (from 7 weeks to 4 weeks) thanks to 73% tile reusability from Initial Cred PSV

---

## Implementation Roadmap

**Total Timeline: 4 weeks** (down from 7 weeks for Initial Cred PSV, thanks to reusability)

### Assumptions:
- Initial Cred PSV Review tile framework and all Initial Cred PSV components are already built
- Framework (`prm_verificationDashboard`, `prm_progressHeader`, etc.) exists
- Custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`) exist

---

### Week 1: Configuration & Re-Cred DataRaptor Integration

**Days 1-2: Configure Re-Cred Tile Metadata**
- Configure 11 Re-Cred PSV tiles in `reCredPsvTileConfig`
- Add `Flow_Type__c = "ReCredPSVReview"` to configuration
- Wire up Re-Cred specific DataRaptor transforms:
  - `DRTransformReCredData` - Transforms Re-Cred specific data
  - `DRTransformRecredFiles` - Transforms Re-Cred file attachments
- Update `prm_verificationDashboard` to support Re-Cred configuration

**Days 3-5: Build ReCredPSVReviewController Apex Class**
- Apex controller methods:
  - `fetchReCredPSVReviewData()` - Fetch CAQH + Salesforce data + Board Certifications
  - `saveReCredPSVVerificationSession()` - Auto-save session
  - `saveReCredPSVVerificationTileStatus()` - Save individual tile
  - `submitReCredPSVReview()` - Submit with Re-Cred specific routing logic
- Integration with existing Integration Procedure: `PRM_ReviewPSVCaseRecordsUpdate`
- Unit tests for Apex controllers

---

### Week 2: Build Re-Cred Specific Tiles

**Days 1-3: prm_reCredBoardCertification (Most Complex)**
- CAQH Board Certification display section (read-only)
- Salesforce Board Certification edit section (editable)
- Board Certification Verification section (radio + notes)
- "Copy from CAQH" functionality
- Multiple board certifications support (Lightning Datatable)
- Add/Remove board certification actions
- Expiration date warnings (90 days, expired)
- Unit tests

**Day 4: prm_reCredCMSPreclusionReview**
- Simple checkbox for CMS Preclusion Review Required
- Conditional fields: Reason picklist, Notes
- Information banner
- Unit tests

**Day 5: prm_reCredFinalConfirmation (Extend prm_finalSubmitBase)**
- Extend `prm_finalSubmitBase` component from App Review
- Override submit logic for Re-Cred routing:
  - Medical Director Review
  - PSV QC
  - Provider Outreach Needed
  - Final Development
- Outcome-specific routing explanation and warnings
- Auto-populate flags: `MedicalDirectorReview__c`, `CMSPreclusionReview__c`
- Unit tests

---

### Week 3: Integration Testing & File Upload

**Days 1-2: Re-Cred File Upload Integration**
- Configure `prm_fileUpload` for Re-Cred specific file requirements
- Wire up `showFileNotes` logic (`IF(IsRecredentialing == true, true, false)`)
- Test Re-Cred file attachments (`RecredAttachments`)
- Test `DRTransformRecredFiles` integration

**Days 3-4: Full Flow Integration Testing**
- Test full Re-Cred PSV flow: Load → Verify → Save → Submit
- Test all 3 Re-Cred specific tiles (Board Cert, CMS Preclusion, Final Confirmation)
- Test routing to Medical Director Review vs PSV QC vs Provider Outreach
- Test resume functionality
- Test auto-save (every 2 minutes)
- Test with realistic data:
  - 100+ addresses
  - Multiple board certifications
  - CMS Preclusion Review required

**Day 5: Bug Fixes**
- Fix bugs from integration testing
- Performance testing
- UI/UX polish

---

### Week 4: User Acceptance Testing & Deployment

**Days 1-2: User Acceptance Testing**
- UAT with Re-Cred PSV specialists
- Test Board Certification verification workflow
- Test Medical Director Review routing
- Test CMS Preclusion Review workflow

**Days 3-4: Bug Fixes from UAT**
- Fix bugs from UAT feedback
- Final regression testing
- Accessibility testing (WCAG compliance)

**Day 5: Deployment Preparation**
- Prepare deployment artifacts
- Update user training materials
- Create "Try New Re-Cred PSV Experience" button

---

### Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Week 1** | 5 days | Re-Cred Configuration, DataRaptor Integration, Apex Controller |
| **Week 2** | 5 days | 3 Re-Cred Specific Tiles (Board Cert, CMS Preclusion, Final Confirmation) |
| **Week 3** | 5 days | File Upload Integration, Full Flow Testing, Bug Fixes |
| **Week 4** | 5 days | UAT, Bug Fixes, Deployment Prep |
| **Total** | **4 weeks** | Re-Cred PSV Review fully functional |

**Time Savings: 3 weeks** (from 7 weeks for Initial Cred PSV to 4 weeks for Re-Cred PSV thanks to 73% tile reusability)

---

## Data Storage Strategy

### Shared Custom Objects (RECOMMENDED)

**Reuse from App Review, Initial Cred PSV, PSV QC, PDA QC:**

**1. Verification Session (`PRM_VerificationSession__c`)**
```
Fields:
- Case_Manager__c (Lookup to Case Manager)
- Flow_Type__c (Picklist: "ApplicationReview", "PSVReview", "PSVQCReview", "PDAQCReview", "ReCredPSVReview") ← ADD ReCredPSVReview
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
- Tile_Id__c (Text: 'practitionerInfo', 'boardCertification', 'cmsPreclisionReview', etc.)
- Tile_Label__c (Text)
- Status__c (Pending, In Progress, Completed, Error)
- Completed_By__c (User)
- Completed_Date__c (DateTime)
- Has_Warnings__c (Checkbox)
- Warning_Message__c (Text)
- Verification_Data__c (Long Text Area - JSON)
- Verification_Status__c (Picklist: Verified, Needs Review, Rejected)
- Notes__c (Long Text Area)
```

---

## Success Criteria

### Functional Requirements

✅ **All 11 tiles functional** for Re-Cred PSV flow
✅ **Board Certification verification working** (Re-Cred specific)
✅ **CMS Preclusion Review functional** (Re-Cred specific)
✅ **Re-Cred specific routing working** (Medical Director Review, PSV QC, Provider Outreach, Final Development)
✅ **All fields editable** (business requirement met)
✅ **Auto-save working** every 2 minutes
✅ **Resume capability** tested and verified
✅ **Integration with existing IP** (`PRM_ReviewPSVCaseRecordsUpdate`)
✅ **Re-Cred DataRaptor transforms** working (`DRTransformReCredData`, `DRTransformRecredFiles`)
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
✅ **Inline field validation**
✅ **CAQH vs Salesforce comparison** view for Board Certifications
✅ **"Copy from CAQH"** buttons
✅ **Warning badges** for expiring board certifications
✅ **Outcome-specific routing explanations** (Medical Director Review vs PSV QC)

---

## Overall Timeline Summary (All 5 Flows)

| Flow | Timeline | Key Factor |
|------|----------|------------|
| **App Review** | 12 weeks | Baseline (builds shared framework & components) |
| **Initial Cred PSV** | 7 weeks | 80-100% reuse of shared components |
| **Re-Cred PSV** | **4 weeks** | 73% reuse from Initial Cred PSV + 3 new tiles |
| **PSV QC Review** | 3 weeks | QC wrapper pattern (95% reuse from PSV) |
| **PDA QC Review** | 7 weeks | Limited reuse but simpler tiles |
| **Total Sequential** | **33 weeks** | - |
| **Total Parallel** | **~19 weeks** | Build App Review first → PSV flows in parallel → QC flows last |

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-09  
**Author:** Claude Code  
**Reviewers:** [TBD]  
**Status:** DRAFT - Awaiting Stakeholder Feedback

---

## Appendix A: Complete Tile Configuration

```javascript
// Re-Cred PSV Review Tile Configuration
const reCredPsvTileConfig = {
  flowType: 'ReCredPSVReview',
  integrationProcedure: 'PRM_ReviewPSVCaseRecordsUpdate', // Same as Initial Cred PSV
  dataRaptorTransforms: [
    'DRTransformReCredData',     // Re-Cred specific transform
    'DRTransformRecredFiles'     // Re-Cred file attachments
  ],
  tiles: [
    {
      id: 'practitionerInfo',
      label: 'Practitioner Info',
      icon: 'standard:user',
      sequence: 1,
      required: true,
      component: 'c-prm-psv-practitioner-info', // REUSE from Initial Cred PSV
      dataKey: 'practitionerData',
      description: 'Verify practitioner demographics and identity',
      estimatedTime: '5 min'
    },
    {
      id: 'groupPractice',
      label: 'Group/Practice',
      icon: 'standard:account',
      sequence: 2,
      required: true,
      component: 'c-prm-psv-group-practice', // REUSE from Initial Cred PSV
      dataKey: 'groupData',
      description: 'Verify group affiliation and practice type',
      estimatedTime: '3 min'
    },
    {
      id: 'addressVerification',
      label: 'Address Verification',
      icon: 'standard:address',
      sequence: 3,
      required: true,
      component: 'c-prm-psv-address-verification', // REUSE from Initial Cred PSV
      dataKey: 'addressData',
      description: 'Verify all practice locations',
      estimatedTime: '15 min',
      warning: 'Large dataset - may trigger async processing'
    },
    {
      id: 'demographicsDiversity',
      label: 'Demographics & Diversity',
      icon: 'standard:people',
      sequence: 4,
      required: false,
      component: 'c-prm-psv-demographics-diversity', // REUSE from Initial Cred PSV
      dataKey: 'demographicsData',
      description: 'Verify diversity and cultural identity information',
      estimatedTime: '3 min',
      sensitiveData: true
    },
    {
      id: 'languagesSpoken',
      label: 'Languages Spoken',
      icon: 'standard:knowledge',
      sequence: 5,
      required: false,
      component: 'c-prm-psv-languages-spoken', // REUSE from Initial Cred PSV
      dataKey: 'languagesData',
      description: 'Verify language proficiency',
      estimatedTime: '3 min'
    },
    {
      id: 'contactInformation',
      label: 'Contact Information',
      icon: 'standard:contact',
      sequence: 6,
      required: true,
      component: 'c-prm-psv-contact-information', // REUSE from Initial Cred PSV
      dataKey: 'contactData',
      description: 'Verify primary and secondary contacts',
      estimatedTime: '3 min'
    },
    {
      id: 'boardCertification', // 🆕 RE-CRED SPECIFIC
      label: 'Board Certification',
      icon: 'standard:reward',
      sequence: 7,
      required: true,
      component: 'c-prm-re-cred-board-certification', // NEW for Re-Cred
      dataKey: 'boardCertData',
      description: 'Verify board certifications (RE-CRED ONLY)',
      estimatedTime: '5 min',
      showWhen: 'IsRecredentialing = true',
      isReCredOnly: true
    },
    {
      id: 'contractStatus',
      label: 'Contract Status',
      icon: 'standard:contract',
      sequence: 8,
      required: true,
      component: 'c-prm-psv-contract-status', // REUSE from Initial Cred PSV
      dataKey: 'contractData',
      description: 'Validate contract and NPI status',
      estimatedTime: '3 min'
    },
    {
      id: 'cmsPreclisionReview', // 🆕 RE-CRED SPECIFIC
      label: 'CMS Preclusion Review',
      icon: 'standard:people',
      sequence: 9,
      required: false,
      component: 'c-prm-re-cred-cms-preclusion-review', // NEW for Re-Cred
      dataKey: 'cmsPreclisionData',
      description: 'CMS preclusion screening (RE-CRED ONLY)',
      estimatedTime: '2 min',
      showWhen: 'IsRecredentialing = true AND CMSPreclusionReview = true',
      isReCredOnly: true
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
      showFileNotes: true // Re-Cred specific: showFileNotes = IF(IsRecredentialing == true, true, false)
    },
    {
      id: 'finalConfirmation', // 🆕 RE-CRED SPECIFIC ROUTING
      label: 'Re-Cred PSV Confirmation',
      icon: 'standard:approval',
      sequence: 11,
      required: true,
      component: 'c-prm-re-cred-final-confirmation', // NEW for Re-Cred (extends prm_finalSubmitBase)
      dataKey: 'summaryData',
      description: 'Review and submit Re-Cred PSV verification',
      estimatedTime: '5 min',
      isReCredOnly: true
    }
  ]
};
```

---

## Appendix B: Comparison Matrix - Initial Cred PSV vs Re-Cred PSV

| Feature | Initial Cred PSV | Re-Cred PSV | Difference |
|---------|-----------------|-------------|------------|
| **Tile Count** | 10 tiles | 11 tiles | +1 (Board Cert, CMS Preclusion split) |
| **Board Certification** | ✗ | ✓ 🆕 | Re-Cred ONLY |
| **CMS Preclusion Review** | ✗ | ✓ 🆕 | Re-Cred ONLY |
| **Medical Director Review** | ✗ | ✓ 🆕 | Re-Cred routing option |
| **File Notes** | ✗ | ✓ | Re-Cred specific file requirements |
| **DataRaptor Transforms** | Standard | +2 Re-Cred transforms | DRTransformReCredData, DRTransformRecredFiles |
| **Submit Next Step** | PDA or Committee | Medical Director / QC / Outreach / Final Dev | Different routing logic |
| **Reusable Tiles** | N/A | 8 of 11 tiles (73%) | High reusability |
| **Implementation Time** | 7 weeks | 4 weeks | 3 weeks saved |

**Overall Improvement:** 🚀 **43% faster implementation** (4 weeks vs 7 weeks) thanks to tile reusability
