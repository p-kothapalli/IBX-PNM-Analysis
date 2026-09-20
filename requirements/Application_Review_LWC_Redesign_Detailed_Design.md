# Application Review LWC Redesign - Detailed Design Document

## Executive Summary

**Problem:** The current Application Review OmniScript has a "Save for Later" payload limitation of 4MB, causing failures when business users need to pause midway through the verification process.

**Solution:** Redesign from OmniScript to a tile-based LWC architecture where each verification step is independent, can be completed in any order, saves immediately upon completion, and provides visual progress tracking.

---

## Current State Analysis

### Current OmniScript Structure

**Main OmniScript:** `PRM_InitialCredentialAppReview_English`

**Flow Steps:**
1. **Practitioner Review Submit Screen** - Initial application details
2. **CAQH Validation** - Validate against CAQH data
3. **Taxonomy/Role/Specialty Review** (`CredApplicationReviewOSTxnyRole`)
4. **Detailed Verification Sub-OS** (`CredApplicationReviewSubOS`):
   - Person Education
   - License Verification (SBRD)
   - DEA License
   - CDS License  
   - Work History
   - Malpractice Coverage
   - Adverse Action Review
5. **File Upload** (`CredentialAppReviewFileLoad`)
6. **Review Complete** (`CredentialAppReviewCompleteOS`) - Summary and final submission

### Data Being Reviewed (CAQH + Salesforce)

| Review Section | CAQH Data | Salesforce Objects | Verification Fields |
|----------------|-----------|-------------------|---------------------|
| **Application** | Provider Demographics | Account (Practitioner) | Name, NPI, Date of Birth |
| **Taxonomy** | Specialty Info | HealthcareProviderTaxonomy | Taxonomy Code, Primary Flag, Practitioner Role |
| **Education** | Education History | PersonEducation | Degree, Institution, Dates, Status |
| **License** | State Licenses | BusinessLicense | License #, State, Class, Effective/Exp Dates, Status |
| **DEA** | DEA Certificates | BusinessLicense (DEA Type) | DEA #, Issue/Exp Dates, Status |
| **CDS** | CDS Certificates | BusinessLicense (CDS Type) | Certificate #, State, Dates, Status |
| **Work History** | Employment History | N/A (Display only) | Employer, Dates, Current Flag, Address |
| **Malpractice** | Insurance Coverage | N/A (Display only) | Carrier, Policy #, Coverage Amounts, Dates |

### Data Being Updated/Created at End

**Integration Procedure:** `PRM_ReviewPSVCaseRecordsUpdate` (70+ elements)

**Objects Modified:**
- **Case** - Status, Review Results, Notes
- **Case Manager** - Assignment, Status Updates
- **HealthcareProviderTaxonomy** - New/Updated taxonomies
- **BusinessLicense** - SBRD, DEA, CDS licenses (Create/Update/Delete)
- **PersonEducation** - Education records (Create/Update)
- **HealthcarePractitionerFacility** - Admitting Privileges (Create/Update/Delete)
- **Identifier** - Medicare, Medicaid IDs
- **Address** - Practice location addresses
- **BoardCertification** - Board certifications (Create/Update)
- **AdverseActionReview** - Adverse action logs
- **ContentDocumentLink** - Uploaded files

### Current Pain Points

1. **4MB Payload Limit** - "Save for Later" fails with large datasets
2. **All-or-Nothing** - Must complete entire flow or lose progress
3. **No Visual Progress** - Users don't know what's verified vs pending
4. **Long Session** - Can take hours to verify all sections
5. **No Flexibility** - Must follow linear sequence
6. **Timeout Risks** - Long sessions can cause timeouts
7. **No Collaboration** - One reviewer must do everything

---

## Proposed LWC Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                  Parent LWC Component                       │
│          (prm_applicationReviewDashboard)                   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Progress Header                          │ │
│  │  ● 7/10 Tiles Completed  ● Auto-saved 2 mins ago    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   ✓      │  │   ✓      │  │   ⚠      │  │          │  │
│  │ Review   │  │ Taxonomy │  │ Education│  │ License  │  │
│  │ App      │  │ & Role   │  │          │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │          │  │          │  │          │  │          │  │
│  │ Work     │  │   DEA    │  │   CDS    │  │Malpractice│ │
│  │ History  │  │          │  │          │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐                                │
│  │          │  │   ✓      │                                │
│  │ Upload   │  │ Final    │                                │
│  │ Files    │  │ Submit   │                                │
│  └──────────┘  └──────────┘                                │
│                                                             │
│  [Resume Later]  [Save & Exit]  [Help]                    │
└─────────────────────────────────────────────────────────────┘

       │ Click Tile
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Modal Component                          │
│          (prm_verificationModal)                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Review Person Education                              │ │
│  │  ─────────────────────────────────────────────────── │ │
│  │                                                       │ │
│  │  CAQH Data             →    Salesforce Data         │ │
│  │  ┌─────────────────┐        ┌─────────────────┐    │ │
│  │  │ Degree: MD     │   →    │ Degree: [MD ▼] │    │ │
│  │  │ School: Harvard│        │ School: Harvard  │    │ │
│  │  │ Year: 2015     │        │ Year: 2015      │    │ │
│  │  └─────────────────┘        └─────────────────┘    │ │
│  │                                                       │ │
│  │  Verification Status: [Verified ▼]                  │ │
│  │  Notes: ___________________________________________  │ │
│  │                                                       │ │
│  │  [Add Record] [Remove Record]                        │ │
│  │                                                       │ │
│  │  [Cancel]  [Save Draft]  [Submit & Review Next ▼]   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```
prm_applicationReviewDashboard (Parent)
  ├── prm_progressHeader
  ├── prm_verificationTile (Repeated)
  │     └── prm_verificationModal (Dynamic)
  │           ├── prm_reviewApplication
  │           ├── prm_reviewTaxonomy
  │           ├── prm_reviewEducation
  │           ├── prm_reviewLicense
  │           ├── prm_reviewWorkHistory
  │           ├── prm_reviewDEA
  │           ├── prm_reviewCDS
  │           ├── prm_reviewMalpractice
  │           ├── prm_fileUpload
  │           └── prm_finalSubmit
  └── prm_navigationFooter
```

---

## Detailed Component Design

### 1. Parent Dashboard Component

**Component:** `prm_applicationReviewDashboard`

**Responsibilities:**
- Fetch Case and all related verification data on load
- Manage tile completion state
- Coordinate auto-save
- Handle navigation between tiles
- Provide "Resume Later" and "Save & Exit" functionality

**Properties:**
```javascript
@api recordId; // Case Manager Record Id
@track tiles = [];
@track overallProgress = 0;
@track currentTile = null;
@track isModalOpen = false;
@track lastSaved = null;
```

**Tile Configuration:**
```javascript
tiles = [
  {
    id: 'application',
    label: 'Review Application',
    icon: 'standard:account',
    status: 'completed', // 'pending', 'in-progress', 'completed', 'error'
    sequence: 1,
    required: true,
    component: 'c-prm-review-application',
    dataKey: 'applicationData',
    hasWarnings: false,
    lastModified: '2026-04-03T10:30:00',
    modifiedBy: 'John Doe'
  },
  {
    id: 'taxonomy',
    label: 'Verify Taxonomy',
    icon: 'standard:product',
    status: 'completed',
    sequence: 2,
    required: true,
    component: 'c-prm-review-taxonomy',
    dataKey: 'taxonomyData',
    hasWarnings: false,
    lastModified: '2026-04-03T11:00:00',
    modifiedBy: 'John Doe'
  },
  {
    id: 'education',
    label: 'Verify Education',
    icon: 'standard:education',
    status: 'in-progress',
    sequence: 3,
    required: true,
    component: 'c-prm-review-education',
    dataKey: 'educationData',
    hasWarnings: true,
    warningMessage: 'Degree mismatch with CAQH',
    lastModified: '2026-04-03T11:15:00',
    modifiedBy: 'John Doe'
  },
  {
    id: 'license',
    label: 'Verify License',
    icon: 'standard:record',
    status: 'pending',
    sequence: 4,
    required: true,
    component: 'c-prm-review-license',
    dataKey: 'licenseData',
    hasWarnings: false
  },
  {
    id: 'workhistory',
    label: 'Verify Work History',
    icon: 'standard:work_order',
    status: 'pending',
    sequence: 5,
    required: false,
    component: 'c-prm-review-work-history',
    dataKey: 'workHistoryData',
    hasWarnings: false
  },
  {
    id: 'dea',
    label: 'Verify DEA',
    icon: 'standard:record',
    status: 'pending',
    sequence: 6,
    required: false,
    component: 'c-prm-review-dea',
    dataKey: 'deaData',
    hasWarnings: false
  },
  {
    id: 'cds',
    label: 'Verify CDS',
    icon: 'standard:record',
    status: 'pending',
    sequence: 7,
    required: false,
    component: 'c-prm-review-cds',
    dataKey: 'cdsData',
    hasWarnings: false
  },
  {
    id: 'malpractice',
    label: 'Verify Malpractice',
    icon: 'standard:case',
    status: 'pending',
    sequence: 8,
    required: true,
    component: 'c-prm-review-malpractice',
    dataKey: 'malpracticeData',
    hasWarnings: false
  },
  {
    id: 'upload',
    label: 'Upload Attachments',
    icon: 'standard:file',
    status: 'pending',
    sequence: 9,
    required: false,
    component: 'c-prm-file-upload',
    dataKey: 'fileData',
    hasWarnings: false
  },
  {
    id: 'final',
    label: 'Final Submit',
    icon: 'standard:approval',
    status: 'pending',
    sequence: 10,
    required: true,
    component: 'c-prm-final-submit',
    dataKey: 'summaryData',
    hasWarnings: false
  }
];
```

**Key Methods:**
```javascript
// Load initial data
async connectedCallback() {
  await this.loadVerificationData();
  this.startAutoSave();
}

// Load all verification data
async loadVerificationData() {
  const result = await fetchApplicationReviewData({ caseManagerId: this.recordId });
  this.tiles.forEach(tile => {
    tile.data = result[tile.dataKey];
    tile.status = result.completionStatus[tile.id];
  });
}

// Handle tile click
handleTileClick(event) {
  const tileId = event.currentTarget.dataset.id;
  this.currentTile = this.tiles.find(t => t.id === tileId);
  this.isModalOpen = true;
}

// Handle save from modal
async handleTileSave(event) {
  const { tileId, data, status } = event.detail;
  await this.saveTileData(tileId, data, status);
  this.updateTileStatus(tileId, status);
  this.calculateProgress();
}

// Auto-save mechanism
startAutoSave() {
  this.autoSaveInterval = setInterval(() => {
    this.autoSaveDraft();
  }, 120000); // Every 2 minutes
}

async autoSaveDraft() {
  const draftData = this.collectDraftData();
  await saveDraftToServer({ caseManagerId: this.recordId, draftData });
  this.lastSaved = new Date();
}
```

---

### 2. Verification Tile Component

**Component:** `prm_verificationTile`

**Properties:**
```javascript
@api tileConfig;
@api onClick;
```

**Template:**
```html
<template>
  <div class={tileClass} onclick={handleClick}>
    <div class="tile-header">
      <lightning-icon icon-name={tileConfig.icon} size="medium"></lightning-icon>
      <div class="status-badge" data-status={tileConfig.status}>
        <lightning-icon icon-name={statusIcon}></lightning-icon>
      </div>
    </div>
    <div class="tile-body">
      <h3>{tileConfig.label}</h3>
      <template if:true={tileConfig.hasWarnings}>
        <div class="warning-message">
          <lightning-icon icon-name="utility:warning" size="x-small"></lightning-icon>
          {tileConfig.warningMessage}
        </div>
      </template>
      <template if:true={tileConfig.lastModified}>
        <div class="tile-footer">
          <span>Modified: {formattedDate}</span>
          <span>By: {tileConfig.modifiedBy}</span>
        </div>
      </template>
    </div>
  </div>
</template>
```

**Status Indicators:**
- ✅ **Completed** - Green checkmark
- ⚠️ **In Progress** - Yellow warning  
- ❌ **Error** - Red X
- ⏳ **Pending** - Gray circle

---

### 3. Verification Modal Component

**Component:** `prm_verificationModal`

**Responsibilities:**
- Dynamically load the appropriate child verification component
- Provide consistent modal UI (header, footer, actions)
- Handle Save, Cancel, and "Submit & Review Next" actions
- Manage unsaved changes warning

**Properties:**
```javascript
@api isOpen = false;
@api tileConfig;
@api tileData;
@track isDirty = false;
@track isSubmitting = false;
```

**Template:**
```html
<template>
  <lightning-modal if:true={isOpen}>
    <lightning-modal-header>
      <h2>{tileConfig.label}</h2>
      <template if:true={isDirty}>
        <lightning-badge label="Unsaved Changes" variant="warning"></lightning-badge>
      </template>
    </lightning-modal-header>
    
    <lightning-modal-body>
      <!-- Dynamic Component Injection -->
      <c-dynamic-component 
        component-name={tileConfig.component}
        data={tileData}
        onchange={handleDataChange}
        onvalidate={handleValidation}>
      </c-dynamic-component>
    </lightning-modal-body>
    
    <lightning-modal-footer>
      <lightning-button label="Cancel" onclick={handleCancel}></lightning-button>
      <lightning-button label="Save Draft" onclick={handleSaveDraft} disabled={isSubmitting}></lightning-button>
      <lightning-button-menu 
        label="Submit & Review Next" 
        variant="brand"
        disabled={isSubmitting || hasErrors}>
        <lightning-menu-item label="Submit & Close" onclick={handleSubmitClose}></lightning-menu-item>
        <lightning-menu-item label="Submit & Next Tile" onclick={handleSubmitNext}></lightning-menu-item>
      </lightning-button-menu>
    </lightning-modal-footer>
  </lightning-modal>
</template>
```

**Key Methods:**
```javascript
handleDataChange(event) {
  this.tileData = event.detail;
  this.isDirty = true;
}

async handleSaveDraft() {
  this.isSubmitting = true;
  await this.saveTile('in-progress');
  this.isDirty = false;
  this.isSubmitting = false;
}

async handleSubmitClose() {
  this.isSubmitting = true;
  await this.saveTile('completed');
  this.closeModal();
  this.isSubmitting = false;
}

async handleSubmitNext() {
  this.isSubmitting = true;
  await this.saveTile('completed');
  this.openNextTile();
  this.isSubmitting = false;
}

async saveTile(status) {
  const result = await saveVerificationData({
    caseManagerId: this.recordId,
    tileId: this.tileConfig.id,
    data: this.tileData,
    status: status
  });
  
  this.dispatchEvent(new CustomEvent('tilesave', {
    detail: {
      tileId: this.tileConfig.id,
      data: this.tileData,
      status: status
    }
  }));
}

handleCancel() {
  if (this.isDirty) {
    // Show confirmation dialog
    this.showUnsavedChangesWarning();
  } else {
    this.closeModal();
  }
}
```

---

### 4. Individual Verification Components

Each verification component follows a standard pattern:

#### **A. Review Application Component**

**Component:** `prm_reviewApplication`

**Data Structure:**
```javascript
{
  practitionerId: '001xxx',
  practitionerName: 'John Doe, MD',
  npi: '1234567890',
  dateOfBirth: '1980-01-01',
  caqhProviderId: 'CAQH123456',
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Template:**
```html
<template>
  <div class="verification-section">
    <h3>Practitioner Information</h3>
    
    <lightning-layout multiple-rows>
      <lightning-layout-item size="6">
        <div class="data-comparison">
          <label>Practitioner Name</label>
          <div class="caqh-value">{data.practitionerName}</div>
        </div>
      </lightning-layout-item>
      
      <lightning-layout-item size="6">
        <lightning-input 
          label="NPI" 
          value={data.npi}
          onchange={handleFieldChange}
          data-field="npi">
        </lightning-input>
      </lightning-layout-item>
    </lightning-layout>
    
    <lightning-combobox 
      label="Verification Status"
      value={data.verificationStatus}
      options={verificationOptions}
      onchange={handleFieldChange}
      data-field="verificationStatus"
      required>
    </lightning-combobox>
    
    <lightning-textarea
      label="Notes"
      value={data.verificationNotes}
      onchange={handleFieldChange}
      data-field="verificationNotes">
    </lightning-textarea>
  </div>
</template>
```

#### **B. Review Taxonomy Component**

**Component:** `prm_reviewTaxonomy`

**Data Structure:**
```javascript
{
  taxonomies: [
    {
      id: 'a1x001',
      specialtyName: 'Internal Medicine',
      taxonomyCode: '207R00000X',
      isPrimary: true,
      practitionerRole: 'PCP',
      caqhData: {
        specialtyName: 'Internal Medicine',
        taxonomyCode: '207R00000X',
        isPrimary: true
      },
      verificationStatus: 'Verified',
      notes: '',
      action: 'none' // 'add', 'remove', 'update'
    }
  ]
}
```

**Template:**
```html
<template>
  <div class="verification-section">
    <h3>Taxonomy & Specialty Verification</h3>
    
    <lightning-datatable
      key-field="id"
      data={data.taxonomies}
      columns={taxonomyColumns}
      onrowaction={handleRowAction}>
    </lightning-datatable>
    
    <lightning-button label="Add CAQH Taxonomy" onclick={handleAddCAQH}></lightning-button>
    <lightning-button label="Add Custom Taxonomy" onclick={handleAddCustom}></lightning-button>
  </div>
</template>
```

**Columns:**
- Specialty Name
- Taxonomy Code
- Primary (Checkbox)
- Practitioner Role (Picklist: PCP, Specialist, Dual)
- CAQH Match (Icon: ✓ or ✗)
- Verification Status
- Actions (Remove, Edit)

#### **C. Review Education Component**

**Component:** `prm_reviewEducation`

**Data Structure:**
```javascript
{
  educationRecords: [
    {
      id: 'edu001',
      degree: 'MD',
      degreeName: 'Doctor of Medicine',
      institution: 'Harvard Medical School',
      institutionId: 'a2y001',
      startDate: '2011-09-01',
      endDate: '2015-06-01',
      completed: true,
      verificationStatus: 'Verified',
      verifiedOn: '2026-04-03',
      notes: '',
      source: 'CAQH', // 'CAQH', 'Manual'
      action: 'none'
    }
  ]
}
```

**Features:**
- Side-by-side comparison: CAQH Data ↔ Salesforce Data
- Inline editing for Salesforce fields
- Add/Remove education records
- Institution lookup

#### **D. Review License Component**

**Component:** `prm_reviewLicense`

**Data Structure:**
```javascript
{
  licenseRecords: [
    {
      id: 'lic001',
      licenseType: 'SBRD',
      state: 'PA',
      licenseNumber: 'MD123456',
      licenseClass: 'Full',
      effectiveDate: '2015-07-01',
      expirationDate: '2027-06-30',
      verificationStatus: 'Verified',
      verifiedOn: '2026-04-03',
      isPracticeLicense: true,
      notes: '',
      source: 'CAQH',
      action: 'none',
      caqhData: { /* CAQH equivalent */ }
    }
  ]
}
```

**Features:**
- Quick links to state licensing boards
- Duplicate detection
- Service area validation (must be in PA, NJ, DE)
- Bulk add from CAQH
- Comparison view

#### **E. Review Work History Component**

**Component:** `prm_reviewWorkHistory`

**Data Structure:**
```javascript
{
  workHistoryRecords: [
    {
      employerName: 'Pennsylvania Hospital',
      startDate: '2015-07-01',
      endDate: null,
      isCurrent: true,
      address: {
        street: '800 Spruce St',
        city: 'Philadelphia',
        state: 'PA',
        postalCode: '19107',
        country: 'USA'
      },
      notes: '',
      source: 'CAQH'
    }
  ],
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Features:**
- Display-only (from CAQH)
- Overall verification status
- Notes for reviewer

#### **F. Review DEA Component**

Similar to License component but specific to DEA certificates.

#### **G. Review CDS Component**

Similar to License component but specific to CDS certificates.

#### **H. Review Malpractice Component**

**Component:** `prm_reviewMalpractice`

**Data Structure:**
```javascript
{
  insuranceRecords: [
    {
      carrier: 'MMIC',
      insuranceType: 'Professional Liability',
      policyNumber: 'POL123456',
      startDate: '2025-01-01',
      endDate: '2026-01-01',
      coveragePerOccurrence: 1000000,
      coverageAggregate: 3000000,
      isSelfInsured: false,
      isUnlimitedCoverage: false,
      coveredLocations: 'All practice locations',
      carrierAddress: {
        street: '123 Insurance Ave',
        city: 'Philadelphia',
        state: 'PA'
      },
      notes: '',
      source: 'CAQH'
    }
  ],
  verificationStatus: 'Verified',
  denialReason: null,
  verificationNotes: ''
}
```

#### **I. File Upload Component**

**Component:** `prm_fileUpload`

**Features:**
- Drag-and-drop interface
- Multi-file upload
- File type restrictions (PDF, JPG, PNG, DOC, DOCX)
- Preview uploaded files
- Link files to specific verification tiles

#### **J. Final Submit Component**

**Component:** `prm_finalSubmit`

**Features:**
- Summary of all verification statuses
- List of incomplete/pending tiles
- NPDB verification checkbox
- Adverse action review
- Final review results (Approved, Returned for QC, Returned to Outreach)
- Final notes

---

## Data Storage Strategy

### Option 1: Database Persistence with Custom Objects (RECOMMENDED)

**New Custom Objects:**

**1. Verification Session (PRM_VerificationSession__c)**
```
Fields:
- Case_Manager__c (Lookup to Case Manager)
- Status__c (In Progress, Completed, Abandoned)
- Started_By__c (User)
- Started_Date__c (DateTime)
- Last_Modified_Date__c (DateTime)
- Overall_Progress__c (Number: 0-100)
- Session_Data__c (Long Text Area - JSON for draft data)
```

**2. Verification Tile Status (PRM_VerificationTileStatus__c)**
```
Fields:
- Verification_Session__c (Master-Detail to Verification Session)
- Tile_Id__c (Text: 'application', 'taxonomy', etc.)
- Tile_Label__c (Text)
- Status__c (Pending, In Progress, Completed, Error)
- Completed_By__c (User)
- Completed_Date__c (DateTime)
- Has_Warnings__c (Checkbox)
- Warning_Message__c (Text)
- Verification_Data__c (Long Text Area - JSON)
- Notes__c (Long Text Area)
```

**Benefits:**
- ✅ Data persists across sessions
- ✅ Can track who completed what and when
- ✅ Supports audit trail
- ✅ No 4MB limit (data stored in individual records)
- ✅ Can query for reporting
- ✅ Supports collaboration (multiple reviewers)

**Drawbacks:**
- ❌ Requires custom object deployment
- ❌ More complex data model

### Option 2: Browser Storage (localStorage) + Final Save

**Strategy:**
- Store tile data in browser localStorage
- Save to Salesforce only when "Submit & Review Next" is clicked
- Final submit aggregates all data and saves to Salesforce

**Benefits:**
- ✅ Fast local performance
- ✅ No database hits during review
- ✅ Simpler implementation

**Drawbacks:**
- ❌ Data lost if browser cleared
- ❌ Can't resume on different device
- ❌ No collaboration support
- ❌ No audit trail until final submit

### Option 3: Hybrid Approach (BEST OF BOTH)

**Strategy:**
1. Store working data in localStorage for performance
2. Auto-save to Verification Session object every 2 minutes
3. On tile "Submit", save to Verification Tile Status object immediately
4. Final submit triggers full data update to actual objects

**Benefits:**
- ✅ Fast local performance
- ✅ Persistent backup
- ✅ Can resume anywhere
- ✅ Supports collaboration
- ✅ Progressive save (no 4MB issue)

---

## API Design

### Apex Controllers

**1. ApplicationReviewController**

```apex
public with sharing class ApplicationReviewController {
    
    @AuraEnabled(cacheable=true)
    public static ApplicationReviewData fetchApplicationReviewData(Id caseManagerId) {
        // Fetch Case, Case Manager, CAQH data, all related records
        // Return structured data for all tiles
    }
    
    @AuraEnabled
    public static void saveVerificationSession(Id caseManagerId, String sessionData) {
        // Auto-save session data
    }
    
    @AuraEnabled
    public static void saveVerificationTileStatus(
        Id sessionId, 
        String tileId, 
        String status, 
        String data, 
        String notes
    ) {
        // Save individual tile status
    }
    
    @AuraEnabled
    public static void submitFinalReview(
        Id caseManagerId, 
        String reviewResult, 
        Map<String, Object> verificationData
    ) {
        // Call existing Integration Procedure
        // PRM_ReviewPSVCaseRecordsUpdate
    }
}
```

**2. CAQHIntegrationController**

```apex
public with sharing class CAQHIntegrationController {
    
    @AuraEnabled
    public static CAQHResponse validateCAQHProvider(String caqhProviderId) {
        // Call existing CAQH validation IP
    }
    
    @AuraEnabled
    public static Map<String, Object> fetchCAQHData(String caqhProviderId) {
        // Fetch all CAQH data categories
    }
}
```

---

## Reusable Sub-Components

### Modular Component Design

To maximize reusability across App Review, PSV, PSV QC, and PDA QC flows, we'll build modular sub-components that can be shared:

#### 1. Practitioner Demographics Sub-Component (`prm_practitionerDemographics`)

**Used In:** App Review (Tile 1), PSV (Tile 1), PSV QC (Tile 1), PDA QC (Tile 1)

**Fields:**
- Common (all flows): Name, NPI, Date of Birth, CAQH ID
- PSV-specific (conditional): Gender, Email, Degree, Telehealth Capable

**Reuse:** 80% across flows

```javascript
// prm_practitionerDemographics.js
export default class PrmPractitionerDemographics extends LightningElement {
    @api data;
    @api showFields; // Configure which fields to show
    @api isEditable;
    @api flowType; // 'AppReview', 'PSVReview', 'PSVQCReview', 'PDAQCReview'
}
```

#### 2. Taxonomy Verification Sub-Component (`prm_taxonomyVerification`)

**Used In:** App Review (Tile 2), PSV (part of Tile 1), PSV QC (Tile 1), PDA QC (Tile 2)

**Fields:**
- Specialty Name, Taxonomy Code, Primary Flag
- Practitioner Role (PCP/Specialist/Dual) - shown in PSV only

**Reuse:** 100% across flows

```javascript
// prm_taxonomyVerification.js
export default class PrmTaxonomyVerification extends LightningElement {
    @api taxonomies;
    @api isEditable;
    @api showPractitionerRole; // Only in PSV
}
```

#### 3. File Upload Component (`prm_fileUpload`)

**Used In:** App Review (Tile 9), PSV (Tile 9), PSV QC (Tile 9)

**Reuse:** 100% identical

#### 4. Final Submit Base Component (`prm_finalSubmitBase`)

**Used In:** App Review (Tile 10), PSV (Tile 10), PSV QC (Tile 10), PDA QC (Tile 7)

**Features:**
- Tile summary (which tiles completed)
- Outcome selection
- Notes
- Validation (all required tiles completed)

**Reuse:** 80% structure, different outcome options per flow

### Reusability Matrix

| Sub-Component | App Review | PSV | PSV QC | PDA QC | Reuse % |
|---------------|-----------|-----|--------|--------|---------|
| `prm_practitionerDemographics` | ✓ | ✓ (extended) | ✓ (wrapped) | ✓ (display) | **80%** |
| `prm_taxonomyVerification` | ✓ | ✓ | ✓ (wrapped) | ✓ (display) | **100%** |
| `prm_fileUpload` | ✓ | ✓ | ✓ | ✗ | **100%** |
| `prm_finalSubmitBase` | ✓ | ✓ (extended) | ✓ (extended) | ✓ (extended) | **80%** |

---

## Implementation Roadmap

### Phase 1: Foundation & Shared Components (4 weeks)

**Week 1-2: Framework**
- `prm_verificationDashboard` (parent container)
- `prm_progressHeader` (progress bar, auto-save indicator)
- `prm_verificationTile` (tile card component)
- `prm_verificationModal` (modal wrapper)
- `prm_navigationFooter` (footer buttons)
- Custom objects: `PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`

**Week 3-4: Shared Sub-Components**
- `prm_practitionerDemographics` (base version with common fields)
- `prm_taxonomyVerification` (complete)
- `prm_fileUpload` (complete)
- `prm_finalSubmitBase` (base structure)

**Deliverable:** Reusable framework + 4 shared sub-components

### Phase 2: App Review-Specific Tiles (6 weeks)

**Week 5: Assemble Tiles 1-2 (Using Shared Components)**
- Tile 1: Review Application (uses `prm_practitionerDemographics`)
- Tile 2: Verify Taxonomy (uses `prm_taxonomyVerification`)

**Week 6-10: Build App Review-Specific Tiles (New)**
- Week 6: Tile 3 - Verify Education (`prm_reviewEducation`)
- Week 7: Tile 4 - Verify License (`prm_reviewLicense`)
- Week 8: Tiles 5-7 - Verify Work History, DEA, CDS (`prm_reviewWorkHistory`, `prm_reviewDEA`, `prm_reviewCDS`)
- Week 9: Tile 8 - Verify Malpractice (`prm_reviewMalpractice`)
- Week 10: Tile 9-10 - File Upload (reuse), Final Submit (use `prm_finalSubmitBase`)

**Deliverable:** 10 functional App Review tiles

### Phase 3: Testing & Refinement (2 weeks)

**Week 11: Unit Testing**
- Test each tile independently
- Mock Apex calls
- Test validation logic

**Week 12: Integration Testing**
- Full flow testing
- Resume functionality
- Auto-save testing
- Performance testing with realistic data

**Total: 12 weeks** for App Review (baseline)

---

## Navigation & UX Flow

### User Journey

**1. Initial Load:**
```
User clicks "Application Review" button on Case Manager
  ↓
LWC loads ApplicationReviewDashboard
  ↓
Fetch all verification data (Apex)
  ↓
Display tiles with status indicators
  ↓
Check for existing session → Resume or Start New
```

**2. Tile Interaction:**
```
User clicks on a tile (e.g., "Verify Education")
  ↓
Modal opens with Education verification component
  ↓
User reviews CAQH vs Salesforce data
  ↓
User makes changes (add/edit/remove records)
  ↓
User clicks "Save Draft" → Saves to DB, modal stays open
  OR
User clicks "Submit & Review Next" → Saves to DB, opens next tile
  OR
User clicks "Cancel" → Shows unsaved changes warning
```

**3. Progress Tracking:**
```
Each tile save updates:
  - Tile status (Pending → In Progress → Completed)
  - Overall progress percentage
  - Last modified timestamp
  - Auto-save indicator
```

**4. Resume Later:**
```
User clicks "Save & Exit"
  ↓
All current state saved to Verification Session
  ↓
User can close browser
  ↓
Later: User returns, clicks "Application Review"
  ↓
System detects existing session
  ↓
Shows "Resume" option
  ↓
Loads previous state with all completed tiles marked
```

**5. Final Submission:**
```
User completes all required tiles
  ↓
"Final Submit" tile becomes available
  ↓
User reviews summary
  ↓
User selects review result (Approved/Returned for QC/Returned to Outreach)
  ↓
User clicks "Submit Application Review"
  ↓
Apex calls PRM_ReviewPSVCaseRecordsUpdate IP
  ↓
Updates all Salesforce objects
  ↓
Closes session, redirects to Case Manager
```

---

## Technical Specifications

### Performance Optimizations

1. **Lazy Loading:**
   - Load tile data only when modal is opened
   - Don't load all verification data upfront

2. **Chunked Saves:**
   - Save individual tiles separately
   - Never aggregate all data in one transaction

3. **Platform Events:**
   - Use Platform Events for async saves
   - Notify user when async save completes

4. **Caching:**
   - Cache CAQH data (changes infrequently)
   - Use `@wire` with cacheable=true for static lookups

5. **Debouncing:**
   - Debounce auto-save (don't save on every keystroke)
   - Auto-save every 2 minutes

### Security

1. **Field-Level Security:**
   - Respect FLS for all fields
   - Show read-only if no edit access

2. **Record-Level Security:**
   - Check Case Manager access before load
   - Validate ownership on save

3. **Concurrent Access:**
   - Lock verification session when opened
   - Show "In Use by X" indicator

### Error Handling

1. **Network Failures:**
   - Retry failed saves (3 attempts)
   - Store failed saves in localStorage
   - Show persistent banner: "Offline mode - changes will sync when online"

2. **Validation Errors:**
   - Show inline field errors
   - Block submit until errors resolved
   - Highlight problematic tiles in red

3. **Timeout Handling:**
   - Extend session if user is active
   - Show "Session expiring in 5 minutes" warning

---

## Migration Strategy

### Phase 1: Parallel Run (2 Sprints)

- Deploy LWC alongside existing OmniScript
- Add "Try New Experience" button
- Users can opt-in to test
- Collect feedback

### Phase 2: Feature Parity (3 Sprints)

- Ensure LWC has all OmniScript features
- Performance testing with real data
- Fix bugs and UX issues

### Phase 3: Gradual Rollout (2 Sprints)

- Make LWC default, keep OmniScript as fallback
- Monitor error rates
- Provide training

### Phase 4: Full Cutover (1 Sprint)

- Remove OmniScript
- Remove fallback logic
- Archive old code

---

## Testing Strategy

### Unit Tests

- Test each verification component independently
- Mock Apex calls
- Test validation logic
- Test auto-save mechanism

### Integration Tests

- Test full flow: Load → Verify → Save → Submit
- Test resume functionality
- Test concurrent user scenarios
- Test network failure recovery

### Performance Tests

- Test with 1500+ licenses (largest payload)
- Measure page load time
- Measure save time
- Test auto-save performance

### User Acceptance Tests

- Business users test real cases
- Validate against existing OmniScript behavior
- Ensure no data loss
- Verify all edge cases

---

## Open Questions / Decisions Needed

1. **Data Persistence:** Which option - Custom Objects, localStorage, or Hybrid?
2. **Navigation:** Sequential vs free-form tile navigation?
3. **File Upload:** Separate tile or embedded in each tile?
4. **CAQH Validation:** Upfront or on-demand?
5. **Concurrent Access:** Allow or block multiple reviewers?
6. **Edit Completed Tiles:** Allow re-opening or lock once completed?
7. **Payload Distribution:** Which tiles have the heaviest data?
8. **Approval Workflow:** Does this integrate with existing approval process?

---

## Next Steps

1. **Stakeholder Review:** Get feedback on design
2. **Technical Spike:** Prototype one tile (Education) to validate approach
3. **Data Model Design:** Finalize custom objects if Option 1 or 3
4. **Development Prioritization:** Order tiles by complexity/risk
5. **Training Plan:** Prepare materials for business users

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-03  
**Author:** Claude Code  
**Reviewers:** [TBD]  
**Status:** DRAFT - Awaiting Stakeholder Feedback
