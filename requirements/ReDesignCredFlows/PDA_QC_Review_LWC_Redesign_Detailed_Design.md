# PDA QC Review (Network Management QC) LWC Redesign - Detailed Design Document

## Executive Summary

**Problem:** The current PDA Quality Control (QC) Review OmniScript (`PRM_InitialCredPDAQC_English` - Network Management QC AFTER PDA completes) suffers from:
1. **4MB Payload Limitation** - "Save for Later" fails with large datasets (100+ networks)
2. **Read-Only Fields** - Business users cannot edit network assignments, info codes, or directory indicators during QC review
3. **All-or-Nothing Flow** - Must complete entire QC session (1-2 hours) or lose progress
4. **No Visual Progress** - Users don't know what's reviewed vs pending
5. **Complex Network Assignment** - 100+ network options difficult to manage in linear flow

**Solution:** Redesign from OmniScript to a tile-based LWC architecture where:
- Each QC review step is independent and can be completed in any order
- **ALL FIELDS ARE EDITABLE** (key business requirement)
- Saves immediately upon tile completion
- Provides visual progress tracking
- Auto-saves every 2 minutes
- Supports resume from anywhere, anytime

---

## Current State Analysis

### Current OmniScript Structure

**Main OmniScript:** `PRM_InitialCredPDAQC_English` (Version 15)

**Purpose:** Quality Control review AFTER PDA (Peer Data Analyst) has completed their review. QC verifies:
- PDA decisions are accurate
- Network assignments are correct
- Info codes are assigned properly
- Directory indicators are set correctly
- Capitation sites are assigned (for PCP/Dual only)

**Flow Steps:**

1. **Initial Setup & Validation**
   - Fetch PDA review data (`DRTransformPDAReview`)
   - Validate Case (must be "PDA Completed" status)
   - Error screens for invalid cases

2. **Practitioner Information** (Display Only)
   - Name
   - NPI
   - Provider Number
   - Practitioner Role (PCP/Specialist/Dual)
   - Decision Date (PDA approval date)
   - Approved Date

3. **Specialties & Hospital Privileges** (Display Only)
   - Practitioner Specialties (Taxonomy codes)
   - Board Certifications
   - Hospital Privileges (read-only tables)

4. **Practice Location Network Assignment** (EDITABLE - LARGE DATASET)
   - For each Practice Location:
     - Practice Location Name, City, State, County, Zip
     - **Networks** (Multi-select: 100+ network options)
     - **Info Codes** (Multi-select: 50+ info code options)
     - Show in Directory (Yes/No)
   - Custom LWC: `prmInitialCredPDACaptiationLogic`

5. **Practitioner-Level Network Assignment** (EDITABLE)
   - Practitioner-level Networks (different from practice location networks)
   - Practitioner Info Codes
   - Practitioner Show in Directory (Yes/No)

6. **Directory Indicators** (EDITABLE)
   - Practice Location Directory (Yes/No per location)
   - Practice Location Network Directory (Yes/No per network per location)
   - Practitioner Directory (Yes/No)
   - Warning: Setting practitioner directory to "No" sets all child records to "No"

7. **Capitation Sites Assignment** (EDITABLE - PCP/Dual Only)
   - Assign capitation sites to practice locations
   - Show which networks are capitated
   - Custom LWC component

8. **QC Outcome** (EDITABLE)
   - QC Review Outcome (Approved / Returned to PDA / Returned to Outreach)
   - PDA QC Error Reasons (Multi-select if returned)
   - QC Review Notes (Long text)
   - Rebuttal Outcome (if applicable)
   - Rebuttal Notes

9. **File Upload** (`PRM_FileUploadOS`)
   - Upload supporting documents
   - Attach to case

### Data Being Reviewed (Post-PDA)

| Review Section | Source | Salesforce Objects | Fields Reviewed |
|----------------|--------|-------------------|-----------------|
| **Practitioner Summary** | PDA Output | Account, IndividualApplication, Case | Name, NPI, Provider Number, Role, Decision Date, Approved Date |
| **Specialties & Privileges** | PDA Output | HealthcareProviderTaxonomy, BoardCertification, HealthcarePractitionerFacility | Specialties, Board Certs, Hospital Privileges |
| **Practice Location Networks** | PDA Output + QC Edits | PractitionerLocation, PractitionerLocationNetwork, PractitionerLocationInfoCode | Networks, Info Codes, Directory Flags |
| **Practitioner Networks** | PDA Output + QC Edits | PractitionerNetwork, PractitionerInfoCode | Practitioner-level Networks, Info Codes |
| **Directory Indicators** | QC Edits | PractitionerLocation, PractitionerLocationNetwork, PractitionerLocationTaxonomy | ShowInDirectory flags |
| **Capitation Sites** | QC Edits | PractitionerLocationCapitation | Capitation Site assignments |
| **QC Outcome** | QC Input | Case, Case Manager | QC Result, Error Reasons, Notes |

### Data Being Updated at End

**Integration Procedure:** `PRM_NetworkManagementQCUpdate` (custom IP for QC)

**Objects Modified:**
- **PractitionerLocation** - Practice locations (already exist from PDA)
- **PractitionerLocationNetwork** - Networks assigned to practice locations (Create/Update/Delete)
- **PractitionerLocationInfoCode** - Info codes at practice location level (Create/Update/Delete)
- **PractitionerLocationTaxonomy** - Taxonomy at practice location level (Update directory flags)
- **PractitionerNetwork** - Networks assigned at practitioner level (Create/Update/Delete)
- **PractitionerInfoCode** - Info codes at practitioner level (Create/Update/Delete)
- **PractitionerLocationCapitation** - Capitation site assignments (Create/Update/Delete)
- **Case** - Status, QC Review Results, QC Notes
- **Case Manager** - QC Assignment, Status Updates, Next Step
- **ContentDocumentLink** - Uploaded files

### Current Pain Points

1. **4MB Payload Limit** - Fails with practitioners having 100+ network options across 20+ practice locations
2. **Complex Network Assignment** - Must assign networks to 20+ practice locations, each with 100+ network options
3. **Read-Only Fields** - Cannot edit network assignments inline, forcing external updates
4. **All-or-Nothing** - Must complete entire 1-2 hour QC session or lose progress
5. **No Visual Progress** - Users don't know what's reviewed vs pending
6. **Directory Flag Complexity** - Directory flags at 3 levels (location, location-network, practitioner) are confusing
7. **Capitation Sites** - Custom LWC embedded in OmniScript, hard to maintain
8. **No Collaboration** - One QC specialist must do everything

---

## Proposed LWC Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│            INITIAL CRED PDA QUALITY CONTROL DASHBOARD        │
├──────────────────────────────────────────────────────────────┤
│  Progress: ██████░░░░ 60% Complete                          │
│  Auto-saved 2 minutes ago                                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │     ✓     │  │     ✓     │  │     ⚠     │  │          ││
│  │Practitioner│ │Specialties│  │ Practice  │  │Practitioner│
│  │  Summary  │  │& Privileges│  │ Location  │  │  Networks││
│  │           │  │           │  │ Networks  │  │          ││
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘│
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │           │  │           │  │           │              │
│  │ Directory │  │Capitation │  │    QC     │              │
│  │Indicators │  │   Sites   │  │  Outcome  │              │
│  └───────────┘  └───────────┘  └───────────┘              │
│                                                              │
│  [Resume Later]  [Save & Exit]  [Help]                     │
└──────────────────────────────────────────────────────────────┘

       │ Click Tile
       ▼
┌──────────────────────────────────────────────────────────────┐
│              MODAL: Practice Location Networks               │
│                    ✏️ All Fields Editable                    │
│                                                              │
│  Practice Location: 800 Spruce St, Philadelphia, PA        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Assigned Networks (15 selected)                     │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ ☑ IBC PPO                                       │ │   │
│  │ │ ☑ IBC HMO                                       │ │   │
│  │ │ ☑ Keystone Health Plan East                     │ │   │
│  │ │ ☐ Medicare Advantage                            │ │   │
│  │ │ ☐ Medicaid                                      │ │   │
│  │ │ ... (100+ more networks)                        │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Info Codes (5 selected)                             │   │
│  │ ☑ Accepting New Patients                            │   │
│  │ ☑ Wheelchair Accessible                             │   │
│  │ ☐ Telehealth Available                              │   │
│  │ ☐ Spanish Speaking                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Show in Directory: [☑ Yes]                                 │
│                                                              │
│  [Cancel]  [Save & Next Location]  [Submit & Review Next ▼]│
└──────────────────────────────────────────────────────────────┘
```

### Component Structure

```
prm_qcReviewDashboard (Parent - REUSE from App Review & PSV)
  ├── prm_progressHeader (REUSE 100%)
  ├── prm_verificationTile (REUSE 100%)
  │     └── prm_verificationModal (REUSE 100%)
  │           ├── prm_qcPractitionerSummary
  │           ├── prm_qcSpecialtiesPrivileges
  │           ├── prm_qcPracticeLocationNetworks
  │           ├── prm_qcPractitionerNetworks
  │           ├── prm_qcDirectoryIndicators
  │           ├── prm_qcCapitationSites
  │           └── prm_qcOutcome
  └── prm_navigationFooter (REUSE 100%)
```

---

## Reusability Analysis: QC vs PSV vs App Review

### Framework Components (100% Reuse)

| Component | QC | PSV | App Review | Reusable? |
|-----------|-----|-----|------------|-----------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | **100%** - Same tile grid, progress, auto-save |
| **prm_progressHeader** | ✓ | ✓ | ✓ | **100%** - Same progress bar |
| **prm_verificationTile** | ✓ | ✓ | ✓ | **100%** - Same tile status |
| **prm_verificationModal** | ✓ | ✓ | ✓ | **100%** - Same modal structure |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | **100%** - Same footer buttons |
| **prm_fileUpload** | ✓ | ✓ | ✓ | **100%** - Same file upload |

**Framework Reuse: 100%** ✅

### Child Component Reusability

| Tile | QC | PSV | App Review | Reusable From | Reuse % |
|------|-----|-----|------------|---------------|---------|
| **Practitioner Info/Summary** | ✓ (Display only) | ✓ (Editable) | ✓ (Editable) | PSV | 60% (QC is read-only) |
| **Specialties & Privileges** | ✓ (Display only) | ✗ | ✗ | **New** | 0% |
| **Practice Location Networks** | ✓ | ✗ | ✗ | **New** | 0% |
| **Practitioner Networks** | ✓ | ✗ | ✗ | **New** | 0% |
| **Directory Indicators** | ✓ | ✗ | ✗ | **New** | 0% |
| **Capitation Sites** | ✓ | ✗ | ✗ | **New** (existing LWC) | 50% (reuse existing LWC) |
| **QC Outcome** | ✓ | ✗ | ✗ | **New** | 0% |
| **Address Verification** | ✗ | ✓ | ✗ | N/A | - |
| **Demographics & Diversity** | ✗ | ✓ | ✗ | N/A | - |
| **Languages Spoken** | ✗ | ✓ | ✗ | N/A | - |
| **Contact Information** | ✗ | ✓ | ✗ | N/A | - |
| **Board Certification** | ✗ | ✓ (Re-Cred) | ✗ | N/A | - |
| **Education** | ✗ | ✗ | ✓ | N/A | - |
| **License (SBRD/DEA/CDS)** | ✗ | ✗ | ✓ | N/A | - |
| **Work History** | ✗ | ✗ | ✓ | N/A | - |
| **Malpractice** | ✗ | ✗ | ✓ | N/A | - |
| **File Upload** | ✓ | ✓ | ✓ | **Shared** | **100%** |

**Child Component Reuse: ~15%** (Mostly QC-specific tiles)

### Recommendation

**Reuse the same framework (`prm_verificationDashboard`) and create 6 QC-specific child components + reuse existing capitation LWC.**

---

## Cross-Flow Reusability Analysis

### Framework Reusability: 100% Across All 4 Flows

The tile-based LWC architecture is designed with a **configuration-driven framework** that is 100% reusable across all flows (Application Review, PSV Review, PSV QC Review, PDA QC Review).

| Framework Component | App Review | PSV Review | PSV QC Review | PDA QC Review | Reusability % |
|---------------------|-----------|-----------|---------------|---------------|---------------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_progressHeader** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationTile** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_verificationModal** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | ✓ | **100%** |
| **Custom Objects** | PRM_VerificationSession__c, PRM_VerificationTileStatus__c | Same | Same | Same | **100%** |

**Key Architectural Decision:**
The framework components are flow-agnostic. They accept a configuration object that defines:
- Tile count and labels
- Tile sequence
- Which child components to render
- Data keys and validation rules

```javascript
// Example: PDA QC Configuration
const pdaQCConfig = {
  flowType: 'PDAQCReview',
  integrationProcedure: 'PRM_NetworkManagementQCUpdate',
  tiles: [
    { id: 'practitionerSummary', component: 'c-prm-qc-practitioner-summary', ... },
    { id: 'practiceLocationNetworks', component: 'c-prm-qc-practice-location-networks', ... },
    // ... 7 tiles total
  ]
};
```

This configuration-driven approach means **all 4 flows share the same dashboard, progress tracker, tile container, modal, and navigation components**.

---

### Sub-Component Reusability: Why PDA QC is Different

Unlike PSV QC Review (which reuses 75% from PSV through a QC wrapper pattern), PDA QC Review has **limited sub-component reuse (~15%)** because it focuses on a fundamentally different domain:

| Flow | Focus | Key Data Entities |
|------|-------|------------------|
| **Application Review** | Credentials | Education, Licenses, DEA, CDS, Work History, Malpractice |
| **PSV Review** | Demographics & Practice Info | Address, Group/Practice, Languages, Contacts, Demographics |
| **PSV QC Review** | QC Verification of PSV | Same as PSV + QC verification layer |
| **PDA QC Review** | **Network Management & Business Config** | **Networks, Info Codes, Directory Indicators, Capitation Sites** |

**Why Limited Reuse:**

1. **Different Data Domain:**
   - App Review & PSV: Focus on practitioner credentials and demographics
   - PDA QC: Focus on **business configuration** (networks, info codes, directory flags)
   
2. **Different UI Patterns:**
   - App Review & PSV: Form-based data entry (text inputs, date pickers, checkboxes)
   - PDA QC: **Complex multi-select with 100+ options** (dual list boxes, hierarchical trees)
   
3. **Different Business Logic:**
   - App Review & PSV: Validate against CAQH, verify credentials
   - PDA QC: **Assign networks, configure directory visibility, handle capitation**

**Reusability Matrix:**

| Sub-Component | App Review | PSV Review | PSV QC Review | PDA QC Review | Reuse % | Notes |
|--------------|-----------|-----------|---------------|---------------|---------|-------|
| **prm_practitionerDemographics** | ✓ | ✓ (extended) | ✓ (QC wrapper) | ✓ (display-only) | **60%** | PDA QC only displays practitioner summary (no editing) |
| **prm_taxonomyVerification** | ✓ | ✓ | ✓ (QC wrapper) | ✗ | 0% | Not needed in PDA QC (PDA already verified) |
| **prm_fileUpload** | ✓ | ✓ | ✓ | ✗ | 0% | File upload happens in earlier flows, not in PDA QC |
| **prm_finalSubmitBase** | ✓ | ✓ | ✓ | ✗ | 0% | PDA QC uses different submit logic (QC outcome, not PSV/App Review outcome) |
| **prmInitialCredPDACaptiationLogic** | ✗ | ✗ | ✗ | ✓ (wrap in modal) | **50%** | Existing LWC from current OmniScript, can be reused |

**Overall Sub-Component Reusability: ~15%** (1 component at 60% + 1 component at 50% = 55% total / 7 tiles ≈ 15% average)

---

### Why 7 Weeks Timeline Despite 100% Framework Reuse?

**Timeline Breakdown:**

| Flow | Timeline | Explanation |
|------|----------|-------------|
| **Application Review** | 12 weeks | Build framework (4 weeks) + Build 10 tiles (6 weeks) + Testing (2 weeks) |
| **PSV Review** | 7 weeks | Reuse framework + Extend shared components (2 weeks) + Build 7 PSV-specific tiles (3 weeks) + Testing (2 weeks) |
| **PSV QC Review** | 3 weeks | Reuse framework + Build QC wrapper (1 week) + Apply to 8 tiles (1 week) + QC summary + Testing (1 week) |
| **PDA QC Review** | **7 weeks** | Reuse framework (0 weeks) + Build 6 PDA-specific tiles (3 weeks) + Capitation integration (1 week) + Testing (2 weeks) + Deployment (1 week) |

**Why PDA QC Takes 7 Weeks:**

1. **Complex Tile Development (3 weeks):**
   - **Practice Location Networks** (most complex): 1.5 weeks
     - Dual list boxes with 100+ network options
     - Multi-location management (20+ locations)
     - Bulk actions ("Apply to All Locations", "Copy from Location")
     - Search/filter/pagination
   - **Directory Indicators** (hierarchical cascade): 0.5 weeks
     - 3-level hierarchy (Practitioner → Location → Network/Taxonomy)
     - Cascade logic (if practitioner = No → all children = No)
     - Bulk actions
   - **Practitioner Networks**: 0.5 weeks
   - **Specialties & Privileges**: 0.5 weeks
   - **Practitioner Summary** (reuse from PSV): 0.5 weeks (minimal customization for display-only)
   - **QC Outcome**: 0.5 weeks

2. **Capitation Sites Integration (1 week):**
   - Existing LWC: `prmInitialCredPDACaptiationLogic` (currently embedded in OmniScript)
   - Effort: Wrap existing LWC in new modal component
   - Testing: Ensure existing logic works in new tile-based architecture

3. **Testing & Performance (2 weeks):**
   - **Week 1:** Unit tests for each tile
   - **Week 2:** Integration testing
     - Full flow testing (Load → Network Assignment → Directory Config → Submit)
     - Performance testing with large datasets:
       - 100+ networks × 20+ practice locations = 2,000+ network assignments
       - Dual list box performance (search, select, move)
       - Cascade logic testing (directory flags)
     - Resume functionality
     - Auto-save testing

4. **Deployment (1 week):**
   - Parallel run with OmniScript
   - User training
   - Monitor error rates

**Comparison:**

| Factor | PSV Review (7 weeks) | PDA QC Review (7 weeks) | Why Similar? |
|--------|---------------------|------------------------|--------------|
| **Framework Reuse** | 100% | 100% | Same framework |
| **Sub-Component Reuse** | 80-100% (4 components) | 15% (1.5 components) | **PDA QC has less reuse** |
| **Unique Tiles** | 7 PSV-specific | 6 PDA-specific | Similar count |
| **Complexity** | High (100+ addresses, async) | High (100+ networks × 20+ locations) | Similar complexity |
| **Testing** | 2 weeks (address volume) | 2 weeks (network volume) | Similar testing effort |
| **Total** | 7 weeks | 7 weeks | **Different reasons, same timeline** |

**Key Insight:** PSV Review saves time through sub-component reuse (80-100%), but PDA QC Review compensates for lower reuse (15%) by having fewer unique tiles (6 vs 7) and reusing an existing Capitation LWC (50% reuse). The result is the same 7-week timeline, but for different reasons.

---

## Detailed Tile Design

### Tile 1: Practitioner Summary (Display Only)

**Component:** `prm_qcPractitionerSummary`

**Purpose:** Display PDA-approved practitioner information for QC verification (not editable in QC)

**Data Sources:**
- **Salesforce:** Account, IndividualApplication, Case (PDA output)

**Fields (DISPLAY ONLY - No Editing in QC):**

| Field | Salesforce Object | Field Name | Display Format |
|-------|------------------|------------|----------------|
| Practitioner Name | Account | Name | Text (bold, large) |
| NPI | Account | NPI__c | Text (10 digits) |
| Provider Number | IndividualApplication | ProviderNumber__c | Text |
| Practitioner Role | HealthcareProviderTaxonomy | Role__c | Badge (PCP, Specialist, Dual) |
| Decision Date | Case | PDA_DecisionDate__c | Date |
| Approved Date | Case | PDA_ApprovedDate__c | Date |
| PDA Reviewer | Case | PDA_ReviewedBy__c | User name |

**UI Features:**
- Large, clear display of key practitioner info
- Color-coded role badge (PCP = Blue, Specialist = Green, Dual = Purple)
- Link to Practitioner record
- Link to Case record
- "View PDA Notes" button (opens PDA notes in modal)

**Data Structure:**
```javascript
{
  practitionerId: '001xxx',
  practitionerName: 'John Doe, MD',
  npi: '1234567890',
  providerNumber: 'IBX123456',
  practitionerRole: 'PCP',
  decisionDate: '2026-04-01',
  approvedDate: '2026-04-05',
  pdaReviewer: 'Jane Smith',
  pdaNotes: 'Approved after committee review',
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Verification Actions:**
- ✅ Mark as "Verified" (QC confirms PDA data is correct)
- ⚠️ Mark as "Needs Review" (QC has questions)
- Add QC notes

---

### Tile 2: Specialties & Hospital Privileges (Display Only)

**Component:** `prm_qcSpecialtiesPrivileges`

**Purpose:** Display PDA-approved specialties, board certifications, and hospital privileges for QC verification

**Data Sources:**
- **Salesforce:** HealthcareProviderTaxonomy, BoardCertification, HealthcarePractitionerFacility

**Fields (DISPLAY ONLY):**

| Section | Fields | Display Format |
|---------|--------|----------------|
| **Practitioner Specialties** | Specialty Name, Taxonomy Code, Is Primary | Data table |
| **Board Certifications** | Board Name, Certification Date, Expiration Date, Status | Data table |
| **Hospital Privileges** | Hospital Name, Privilege Type, Effective Date, End Date | Data table |

**UI Features:**
- Three separate tables (Specialties, Board Certs, Hospital Privileges)
- Read-only tables with "View Details" action
- Warning badges for expired board certifications
- Link to full records

**Data Structure:**
```javascript
{
  specialties: [
    { id: 'tax001', specialtyName: 'Internal Medicine', taxonomyCode: '207R00000X', isPrimary: true }
  ],
  boardCertifications: [
    { id: 'board001', boardName: 'ABIM', certDate: '2015-01-01', expDate: '2025-01-01', status: 'Current' }
  ],
  hospitalPrivileges: [
    { id: 'hosp001', hospitalName: 'Pennsylvania Hospital', privilegeType: 'Admitting', effectiveDate: '2020-01-01' }
  ],
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Verification Actions:**
- ✅ Mark as "Verified"
- ⚠️ Mark as "Needs Review"
- Add QC notes

---

### Tile 3: Practice Location Networks ⚠️ (MOST COMPLEX - EDITABLE)

**Component:** `prm_qcPracticeLocationNetworks`

**Purpose:** Assign networks and info codes to each practice location (QC adds/removes networks missed by PDA)

**Data Sources:**
- **Salesforce:** PractitionerLocation, PractitionerLocationNetwork, PractitionerLocationInfoCode, Network, InfoCode

**Fields per Practice Location (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| Practice Location Name | PractitionerLocation | Location__r.Name | Display only |
| Street | Address | Street | Display only |
| City | Address | City | Display only |
| State | Address | State | Display only |
| County | Address | County__c | Display only |
| Zip | Address | PostalCode | Display only |
| **Networks** | PractitionerLocationNetwork | Network__c | **Multi-select (100+ options)** |
| **Info Codes** | PractitionerLocationInfoCode | InfoCode__c | **Multi-select (50+ options)** |
| **Show in Directory** | PractitionerLocation | ShowInDirectory__c | **Checkbox** |

**UI Features:**
- **Master-Detail View:**
  - Left panel: List of all practice locations (card view)
  - Right panel: Network assignment for selected location
- **Dual List Box for Networks:**
  - Available Networks (left) ↔ Assigned Networks (right)
  - Search/filter networks
  - Bulk select/deselect
- **Dual List Box for Info Codes:**
  - Available Info Codes (left) ↔ Assigned Info Codes (right)
- **Network Categories:** Group networks by type (Commercial, Medicare, Medicaid, etc.)
- **Show in Directory** toggle
- **"Apply to All Locations"** button (bulk assign networks to all locations)
- **"Copy from Location"** button (copy network assignment from another location)
- **Pagination** (if >10 locations)

**Data Structure:**
```javascript
{
  practiceLocations: [
    {
      id: 'pl001',
      locationName: '800 Spruce St',
      street: '800 Spruce St',
      city: 'Philadelphia',
      state: 'PA',
      county: 'Philadelphia',
      postalCode: '19107',
      assignedNetworks: ['nw001', 'nw002', 'nw003'], // Network IDs
      assignedInfoCodes: ['ic001', 'ic002'],
      showInDirectory: true,
      hasChanges: false
    },
    // ... more locations
  ],
  availableNetworks: [
    { id: 'nw001', name: 'IBC PPO', category: 'Commercial', isCapitated: false },
    { id: 'nw002', name: 'IBC HMO', category: 'Commercial', isCapitated: true },
    // ... 100+ networks
  ],
  availableInfoCodes: [
    { id: 'ic001', name: 'Accepting New Patients', category: 'Access' },
    { id: 'ic002', name: 'Wheelchair Accessible', category: 'Accessibility' },
    // ... 50+ info codes
  ],
  verificationStatus: 'In Progress',
  verificationNotes: ''
}
```

**Validation Rules:**
- At least one network must be assigned to each active practice location
- Show in Directory can only be "Yes" if at least one network is assigned
- Warn if no Info Codes assigned (not required but recommended)

---

### Tile 4: Practitioner Networks (EDITABLE)

**Component:** `prm_qcPractitionerNetworks`

**Purpose:** Assign networks and info codes at PRACTITIONER level (not location-specific)

**Data Sources:**
- **Salesforce:** PractitionerNetwork, PractitionerInfoCode, Network, InfoCode

**Fields (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **Practitioner Networks** | PractitionerNetwork | Network__c | **Multi-select (100+ options)** |
| **Practitioner Info Codes** | PractitionerInfoCode | InfoCode__c | **Multi-select (50+ options)** |
| **Show in Directory** | Account | ShowInDirectory__c | **Checkbox** |

**UI Features:**
- Similar to Practice Location Networks but at practitioner level
- **Dual List Box for Networks**
- **Dual List Box for Info Codes**
- **Show in Directory** toggle
- Warning: "Setting to 'No' will override all location-level directory settings"

**Data Structure:**
```javascript
{
  practitionerId: '001xxx',
  practitionerName: 'John Doe, MD',
  assignedNetworks: ['nw001', 'nw002', 'nw003'],
  assignedInfoCodes: ['ic001', 'ic002'],
  showInDirectory: true,
  availableNetworks: [...], // Same as location networks
  availableInfoCodes: [...], // Same as location info codes
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Validation Rules:**
- If practitioner "Show in Directory" = No, all child records (location, location-network) must also be No

---

### Tile 5: Directory Indicators (EDITABLE)

**Component:** `prm_qcDirectoryIndicators`

**Purpose:** Configure "Show in Directory" flags at 3 levels (Practice Location, Location-Network, Practitioner)

**Data Sources:**
- **Salesforce:** PractitionerLocation, PractitionerLocationNetwork, PractitionerLocationTaxonomy, Account

**Fields (ALL EDITABLE):**

| Level | Object | Field | Edit Behavior |
|-------|--------|-------|---------------|
| **Practitioner Directory** | Account | ShowInDirectory__c | **Checkbox** |
| **Practice Location Directory** | PractitionerLocation | ShowInDirectory__c | **Checkbox per location** |
| **Location-Network Directory** | PractitionerLocationNetwork | ShowInDirectory__c | **Checkbox per network per location** |
| **Location-Taxonomy Directory** | PractitionerLocationTaxonomy | ShowInDirectory__c | **Checkbox per taxonomy per location** |

**UI Features:**
- **Hierarchical View:**
  ```
  [☑] Practitioner: John Doe (Show in Directory)
    └── [☑] Practice Location: 800 Spruce St
        ├── [☑] Network: IBC PPO
        ├── [☑] Network: IBC HMO
        └── [☑] Taxonomy: Internal Medicine
    └── [☐] Practice Location: 123 Market St
        ├── [☐] Network: Medicare Advantage
        └── [☐] Taxonomy: Internal Medicine
  ```
- **Cascade Logic:**
  - If practitioner = No → All child records = No
  - If location = No → All networks/taxonomies at that location = No
- **Bulk Actions:**
  - "Set All to Yes"
  - "Set All to No"
  - "Copy from Existing Practitioner"
- **Warning Messages:**
  - "Setting practitioner to No will hide ALL locations and networks"
  - "This will affect provider directory visibility"

**Data Structure:**
```javascript
{
  practitionerDirectory: {
    practitionerId: '001xxx',
    practitionerName: 'John Doe, MD',
    showInDirectory: true
  },
  practiceLocationDirectory: [
    {
      id: 'pl001',
      locationName: '800 Spruce St',
      showInDirectory: true,
      networks: [
        { networkId: 'nw001', networkName: 'IBC PPO', showInDirectory: true },
        { networkId: 'nw002', networkName: 'IBC HMO', showInDirectory: true }
      ],
      taxonomies: [
        { taxonomyId: 'tax001', taxonomyName: 'Internal Medicine', showInDirectory: true }
      ]
    }
  ],
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Validation Rules:**
- If practitioner ShowInDirectory = No, all child records must be No
- If location ShowInDirectory = No, all networks/taxonomies at that location must be No

---

### Tile 6: Capitation Sites (EDITABLE - PCP/Dual Only)

**Component:** `prm_qcCapitationSites`

**Purpose:** Assign capitation sites to practice locations (only for PCP or Dual practitioners with capitated networks)

**Show When:** `PractitionerRole = 'PCP' OR PractitionerRole = 'Dual'` AND at least one assigned network is capitated

**Data Sources:**
- **Salesforce:** PractitionerLocationCapitation, CapitationSite, Network

**Fields (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| Practice Location | PractitionerLocation | Location__c | Display only |
| Capitated Networks | PractitionerLocationNetwork | Network__c (where IsCapitated = true) | Display only |
| **Capitation Site** | PractitionerLocationCapitation | CapitationSite__c | **Lookup/Combobox** |

**UI Features:**
- **Reuse existing LWC:** `prmInitialCredPDACaptiationLogic` (already exists)
- Wrap existing LWC in modal
- For each practice location:
  - Show which networks are capitated
  - Assign capitation site (lookup)
- **Table View:**
  - Columns: Practice Location | Capitated Networks | Assigned Capitation Site | Action (Edit)
- **Bulk Action:** "Assign Same Capitation Site to All Locations"

**Data Structure:**
```javascript
{
  practiceLocationsWithCapitation: [
    {
      id: 'pl001',
      locationName: '800 Spruce St',
      capitatedNetworks: [
        { networkId: 'nw002', networkName: 'IBC HMO', isCapitated: true }
      ],
      assignedCapitationSite: 'cap001',
      capitationSiteName: 'Philadelphia Capitation Group'
    }
  ],
  availableCapitationSites: [
    { id: 'cap001', name: 'Philadelphia Capitation Group', region: 'Southeast PA' },
    { id: 'cap002', name: 'Montgomery Capitation Group', region: 'Montgomery County' }
  ],
  verificationStatus: 'Verified',
  verificationNotes: ''
}
```

**Validation Rules:**
- If practitioner has capitated networks, at least one capitation site must be assigned
- Warn if capitation site is assigned but no capitated networks exist

---

### Tile 7: QC Outcome (EDITABLE)

**Component:** `prm_qcOutcome`

**Purpose:** Record QC review decision and notes

**Data Sources:**
- **Salesforce:** Case, Case Manager

**Fields (ALL EDITABLE):**

| Field | Salesforce Object | Field Name | Edit Behavior |
|-------|------------------|------------|---------------|
| **QC Review Outcome** | Case Manager | QC_ReviewOutcome__c | **Picklist (Approved, Returned to PDA, Returned to Outreach)** |
| **PDA QC Error Reasons** | Case Manager | PDA_QC_ErrorReasons__c | **Multi-select Picklist (shown if Returned to PDA)** |
| **QC Review Notes** | Case Manager | QC_ReviewNotes__c | **Long text area** |
| **Rebuttal Outcome** | Case Manager | RebuttalOutcome__c | **Picklist (if PDA submitted rebuttal)** |
| **Rebuttal Notes** | Case Manager | RebuttalNotes__c | **Long text area** |
| QC Reviewer | Case Manager | QC_ReviewedBy__c | User (auto-populated) |
| QC Review Date | Case Manager | QC_ReviewDate__c | Date (auto-populated) |

**UI Features:**
- **Summary Section:**
  - Show all tile statuses (which tiles are complete vs pending)
  - Red warning for incomplete/pending tiles
- **Outcome Selection:**
  - Radio buttons: Approved / Returned to PDA / Returned to Outreach
- **Error Reasons (if Returned to PDA):**
  - Multi-select picklist:
    - Network Assignment Incorrect
    - Info Codes Missing
    - Directory Indicators Wrong
    - Capitation Sites Not Assigned
    - Specialty/Taxonomy Mismatch
    - Other (specify in notes)
- **Notes Section:**
  - QC Review Notes (required if Returned)
- **Rebuttal Section (if applicable):**
  - Show PDA Rebuttal Notes (read-only)
  - Rebuttal Outcome (Approved / Still Rejected)
  - Rebuttal Notes
- **Confirmation Dialog:**
  - "Are you sure you want to submit QC review?"
  - Show outcome and notes before final submit

**Data Structure:**
```javascript
{
  qcOutcome: 'Approved', // 'Approved', 'Returned to PDA', 'Returned to Outreach'
  errorReasons: [], // ['Network Assignment Incorrect', 'Capitation Sites Not Assigned']
  qcReviewNotes: '',
  rebuttalOutcome: null, // 'Approved', 'Still Rejected'
  rebuttalNotes: '',
  qcReviewer: 'John Smith',
  qcReviewDate: '2026-04-09',
  allTilesCompleted: false,
  incompleteTiles: ['practiceLocationNetworks', 'capitationSites'],
  verificationStatus: 'Pending',
  verificationNotes: ''
}
```

**Validation Rules:**
- All required tiles must be completed before submitting QC review
- If outcome = "Returned to PDA", at least one error reason must be selected
- If outcome = "Returned", QC Review Notes are required

---

## Data Storage Strategy

### Option 1: Shared Custom Objects (RECOMMENDED)

**Reuse from App Review & PSV:**

**1. Verification Session (`PRM_VerificationSession__c`)**
```
Fields:
- Case_Manager__c (Lookup to Case Manager)
- Flow_Type__c (Picklist: "ApplicationReview", "PSVReview", "QCReview") ← NEW
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
- Tile_Id__c (Text: 'practitionerSummary', 'practiceLocationNetworks', etc.)
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

**Benefits:**
- ✅ Same data model across all flows (Application Review, PSV, QC)
- ✅ Single framework, multiple configurations
- ✅ Data persists across sessions
- ✅ Supports collaboration and audit trail
- ✅ No 4MB limit (data chunked by tile)

---

## API Design

### Apex Controllers

**1. QCReviewController**

```apex
public with sharing class QCReviewController {
    
    @AuraEnabled(cacheable=true)
    public static QCReviewData fetchQCReviewData(Id caseManagerId) {
        // Fetch Case, Case Manager, PDA output data
        // Return structured data for all tiles
    }
    
    @AuraEnabled
    public static void saveQCVerificationSession(Id caseManagerId, String sessionData) {
        // Auto-save session data
    }
    
    @AuraEnabled
    public static void saveQCVerificationTileStatus(
        Id sessionId, 
        String tileId, 
        String status, 
        String data, 
        String notes
    ) {
        // Save individual tile status
        // Update Salesforce objects (PractitionerLocationNetwork, etc.)
    }
    
    @AuraEnabled
    public static void submitQCReview(
        Id caseManagerId, 
        String qcOutcome, 
        List<String> errorReasons,
        Map<String, Object> verificationData
    ) {
        // Call existing Integration Procedure
        // PRM_NetworkManagementQCUpdate
    }
    
    @AuraEnabled(cacheable=true)
    public static List<Network> fetchAvailableNetworks() {
        // Fetch all active networks (100+)
        // Cache for performance
    }
    
    @AuraEnabled(cacheable=true)
    public static List<InfoCode> fetchAvailableInfoCodes() {
        // Fetch all active info codes (50+)
        // Cache for performance
    }
    
    @AuraEnabled(cacheable=true)
    public static List<CapitationSite> fetchCapitationSites(String region) {
        // Fetch capitation sites for a given region
    }
}
```

---

## Key Differences: QC vs PSV vs App Review

| Feature | Application Review | PSV Review | QC Review |
|---------|-------------------|-----------|-----------|
| **Purpose** | Verify credentials from CAQH | Verify demographics & practice info | Verify PDA decisions, assign networks |
| **Tile Count** | 10 tiles | 10 tiles | 7 tiles |
| **Focus** | Credentials (Education, Licenses, DEA, CDS, Work History, Malpractice) | Demographics (Address, Languages, Contacts, Demographics) | **Networks & Business Config** |
| **Largest Tile** | License (50+ licenses) | Address (100+ addresses) | **Practice Location Networks (100+ networks × 20+ locations)** |
| **Data Entry** | Mostly from CAQH | Mostly from CAQH | **Mostly QC edits** (networks, info codes) |
| **Display vs Edit** | 70% editable | 100% editable | **50% display-only (PDA output), 50% editable (QC decisions)** |
| **Complexity** | Medium | High (address volume) | **High (network complexity, 3-level directory flags)** |
| **Integration Procedure** | PRM_ReviewPSVCaseRecordsUpdate | PRM_ReviewPSVCaseRecordsUpdate | **PRM_NetworkManagementQCUpdate** (different IP) |
| **Submit Next Step** | PDA Review or Committee | PDA Review or Committee | **Committee Review or Outreach** |
| **Async Processing** | Not required | Required (100+ addresses) | May be required (100+ networks × 20+ locations) |
| **Reuse from Framework** | 100% | 100% | **100%** ✅ |
| **Reuse Child Components** | N/A (first implementation) | 20% from App Review | **15% from PSV** (practitioner summary) |

---

## Implementation Roadmap

### Phase 1: Foundation (2 weeks) - REUSE FROM APP REVIEW & PSV

Since App Review and PSV tile frameworks already exist (or will be built first), we can reuse:
- ✅ `prm_verificationDashboard`
- ✅ `prm_progressHeader`
- ✅ `prm_verificationTile`
- ✅ `prm_verificationModal`
- ✅ `prm_navigationFooter`
- ✅ Custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`)

**New Work:**
- **Week 1:** Configure QC tile metadata, update Apex for QC data structure
- **Week 2:** Testing and integration

### Phase 2: QC-Specific Tiles (3 weeks)

**Week 3: Display-Only Tiles**
- `prm_qcPractitionerSummary` (reuse from PSV, make read-only)
- `prm_qcSpecialtiesPrivileges` (new)

**Week 4: Network Assignment Tiles (Most Complex)**
- `prm_qcPracticeLocationNetworks` (most complex, dual list boxes, 100+ networks)
- `prm_qcPractitionerNetworks`

**Week 5: Business Config Tiles**
- `prm_qcDirectoryIndicators` (3-level hierarchy, cascade logic)
- `prm_qcCapitationSites` (reuse existing `prmInitialCredPDACaptiationLogic` LWC)
- `prm_qcOutcome`

### Phase 3: Testing & Refinement (1 week)

**Week 6: Testing**
- Unit testing (each tile)
- Integration testing (full QC flow)
- Test with realistic data (100+ networks, 20+ locations)
- Network performance testing (dual list boxes with 100+ options)

### Phase 4: Deployment (1 week)

**Week 7: Production Deployment**
- Parallel run with OmniScript
- "Try New QC Experience" button
- Monitor error rates
- Collect user feedback

**Total: 7 weeks** (vs 10 weeks for PSV, 12 weeks for App Review, thanks to framework reuse)

---

## Success Criteria

### Functional Requirements

✅ **All 7 tiles functional** for QC flow
✅ **Network assignment fields editable** (business requirement met)
✅ **Auto-save working** every 2 minutes
✅ **Resume capability** tested and verified
✅ **Integration with existing IP** (`PRM_NetworkManagementQCUpdate`)
✅ **All OmniScript functionality** preserved
✅ **Capitation LWC integration** working

### Performance Requirements

✅ **0 save failures** (no 4MB limit)
✅ **Page load < 3 seconds**
✅ **Save tile < 2 seconds**
✅ **Network dual list box loads < 2 seconds** (100+ options)
✅ **Resume session < 3 seconds**

### User Experience Requirements

✅ **Visual progress tracking**
✅ **Tile-based navigation** (non-linear)
✅ **Dual list boxes** for network assignment
✅ **Bulk actions** (apply to all locations)
✅ **Hierarchical directory indicator** view
✅ **Error reasons** for QC returns

---

## Migration Strategy

### Phase 1: Parallel Run (1 Sprint)

- Deploy QC LWC alongside existing OmniScript
- Add "Try New QC Experience" button on Case Manager
- Users can opt-in to test
- Collect feedback

### Phase 2: Feature Parity (1 Sprint)

- Ensure LWC has all OmniScript features
- Performance testing with real data (100+ networks, 20+ locations)
- Fix bugs and UX issues

### Phase 3: Gradual Rollout (1 Sprint)

- Make LWC default, keep OmniScript as fallback
- Monitor error rates
- Provide training

### Phase 4: Full Cutover (1 Sprint)

- Remove OmniScript
- Archive old code

---

## Open Questions / Decisions Needed

1. **Network Assignment:** Should we support bulk network assignment across all practice locations?
2. **Directory Flag Cascade:** Should changing practitioner directory flag automatically cascade to all locations?
3. **Capitation LWC:** Reuse existing `prmInitialCredPDACaptiationLogic` or rebuild?
4. **QC Error Reasons:** Are the current error reasons sufficient or need more options?
5. **Concurrent Access:** Allow multiple QC specialists or lock session?
6. **Edit PDA Decisions:** Should QC be able to edit PDA-approved data (specialties, etc.) or only add networks?
7. **Integration Procedure:** Reuse `PRM_NetworkManagementQCUpdate` as-is or modify for tile-based save?

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Network Assignment Complexity** | Medium | High | Dual list boxes, search/filter, bulk actions |
| **Directory Flag Cascade Logic** | Low | High | Clear UI warnings, confirmation dialogs |
| **Capitation LWC Integration** | Low | Medium | Reuse existing LWC, wrap in modal |
| **Performance with 100+ Networks** | Medium | Medium | Caching, lazy loading, pagination |
| **User Adoption Resistance** | Medium | High | Training, pilot with champions, keep OmniScript fallback |

---

## Next Steps

1. ✅ **Stakeholder Review:** Get feedback on QC tile design (esp. network assignment approach)
2. ⏳ **Technical Spike:** Prototype Practice Location Networks tile (most complex, dual list boxes)
3. ⏳ **Reuse Assessment:** Confirm App Review & PSV frameworks are ready for reuse
4. ⏳ **Integration Procedure Analysis:** Ensure `PRM_NetworkManagementQCUpdate` can handle tile-based saves
5. ⏳ **Capitation LWC Review:** Validate existing `prmInitialCredPDACaptiationLogic` can be wrapped in modal

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-09  
**Author:** Claude Code  
**Reviewers:** [TBD]  
**Status:** DRAFT - Awaiting Stakeholder Feedback

---

## Appendix A: Complete Tile Configuration

```javascript
// QC Review Tile Configuration
const qcTileConfig = {
  flowType: 'QCReview',
  integrationProcedure: 'PRM_NetworkManagementQCUpdate',
  tiles: [
    {
      id: 'practitionerSummary',
      label: 'Practitioner Summary',
      icon: 'standard:user',
      sequence: 1,
      required: true,
      component: 'c-prm-qc-practitioner-summary',
      dataKey: 'practitionerData',
      description: 'Verify PDA-approved practitioner information',
      estimatedTime: '3 min',
      editable: false // Display only
    },
    {
      id: 'specialtiesPrivileges',
      label: 'Specialties & Privileges',
      icon: 'standard:product',
      sequence: 2,
      required: true,
      component: 'c-prm-qc-specialties-privileges',
      dataKey: 'specialtiesData',
      description: 'Review specialties, board certs, and hospital privileges',
      estimatedTime: '5 min',
      editable: false // Display only
    },
    {
      id: 'practiceLocationNetworks',
      label: 'Practice Location Networks',
      icon: 'standard:location',
      sequence: 3,
      required: true,
      component: 'c-prm-qc-practice-location-networks',
      dataKey: 'practiceLocationNetworksData',
      description: 'Assign networks and info codes to practice locations',
      estimatedTime: '15 min',
      warning: 'Large dataset - 100+ network options',
      editable: true
    },
    {
      id: 'practitionerNetworks',
      label: 'Practitioner Networks',
      icon: 'standard:team_member',
      sequence: 4,
      required: true,
      component: 'c-prm-qc-practitioner-networks',
      dataKey: 'practitionerNetworksData',
      description: 'Assign practitioner-level networks and info codes',
      estimatedTime: '5 min',
      editable: true
    },
    {
      id: 'directoryIndicators',
      label: 'Directory Indicators',
      icon: 'standard:display_rich_text',
      sequence: 5,
      required: true,
      component: 'c-prm-qc-directory-indicators',
      dataKey: 'directoryData',
      description: 'Configure show in directory flags',
      estimatedTime: '5 min',
      editable: true
    },
    {
      id: 'capitationSites',
      label: 'Capitation Sites',
      icon: 'standard:currency',
      sequence: 6,
      required: false,
      component: 'c-prm-qc-capitation-sites',
      dataKey: 'capitationData',
      description: 'Assign capitation sites to practice locations',
      estimatedTime: '5 min',
      showWhen: 'PractitionerRole = PCP OR PractitionerRole = Dual',
      editable: true
    },
    {
      id: 'qcOutcome',
      label: 'QC Outcome',
      icon: 'standard:approval',
      sequence: 7,
      required: true,
      component: 'c-prm-qc-outcome',
      dataKey: 'qcOutcomeData',
      description: 'Record QC review decision and notes',
      estimatedTime: '5 min',
      editable: true
    }
  ]
};
```

---

## Appendix B: Complete Reusability Matrix

| Component | App Review | PSV Review | QC Review | Reusable? | Source |
|-----------|-----------|-----------|-----------|-----------|--------|
| **prm_verificationDashboard** | ✓ | ✓ | ✓ | **100%** | Shared framework |
| **prm_progressHeader** | ✓ | ✓ | ✓ | **100%** | Shared framework |
| **prm_verificationTile** | ✓ | ✓ | ✓ | **100%** | Shared framework |
| **prm_verificationModal** | ✓ | ✓ | ✓ | **100%** | Shared framework |
| **prm_navigationFooter** | ✓ | ✓ | ✓ | **100%** | Shared framework |
| **prm_fileUpload** | ✓ | ✓ | ✗ | **100%** | Shared (not in QC) |
| **prm_qcPractitionerSummary** | ✗ | ✓ | ✓ | **60%** | Adapted from PSV (display-only) |
| **prm_qcSpecialtiesPrivileges** | ✗ | ✗ | ✓ | **0%** | New (QC-specific) |
| **prm_qcPracticeLocationNetworks** | ✗ | ✗ | ✓ | **0%** | New (QC-specific) |
| **prm_qcPractitionerNetworks** | ✗ | ✗ | ✓ | **0%** | New (QC-specific) |
| **prm_qcDirectoryIndicators** | ✗ | ✗ | ✓ | **0%** | New (QC-specific) |
| **prm_qcCapitationSites** | ✗ | ✗ | ✓ | **50%** | Wrapper for existing `prmInitialCredPDACaptiationLogic` LWC |
| **prm_qcOutcome** | ✗ | ✗ | ✓ | **0%** | New (QC-specific) |

**Overall Reusability:**
- **Framework:** 100% ✅
- **Child Components:** ~15%
- **Development Time Savings:** 40% (vs building from scratch)

---

## Appendix C: Comparison - All Three Flows

| Metric | Application Review | PSV Review | QC Review |
|--------|-------------------|-----------|-----------|
| **Tile Count** | 10 | 10 | 7 |
| **Editable Tiles** | 10 (100%) | 10 (100%) | 4 (57%) - Others display-only |
| **Largest Tile** | License (50+ licenses) | Address (100+ addresses) | Practice Location Networks (100+ networks × 20+ locations) |
| **Avg Session Time** | 2-4 hours | 2-4 hours | 1-2 hours |
| **Complexity** | Medium (credentials) | High (addresses) | High (networks) |
| **Current Elements** | ~150 | 186+ | ~120 |
| **Async Processing** | No | Yes (100+ addresses) | Maybe (100+ networks) |
| **Implementation Time** | 12 weeks | 10 weeks | 7 weeks |
| **Framework Reuse** | N/A (first) | 100% | 100% |
| **Child Reuse** | N/A | 20% | 15% |

**Total Combined Implementation:** **29 weeks** if done sequentially, **~20 weeks** if done in parallel (with shared framework)
