# Concierge Medicine - Complete Implementation User Stories

**Document Version:** 4.3 (Recred PSV Address Screen Concierge Question Added)
**Created Date:** April 5, 2026
**Last Updated:** April 16, 2026
**Project:** PIE & Provider Directory Enhancement - Concierge Medicine Provider Tracking
**Approach:** Info Code + Info Code Assignment (following PNC/Delegated pattern) + PAR Form Integration

---

## Version 4.3 Change Summary (April 16, 2026)

### Business Requirements Incorporated:

6. **Recred PSV Address Screen – Per-Location Concierge Question (Version 4.3 - NEW)**
   - Added a required radio question to the Practice Location address screen during the Recred PSV process
   - Question text: "Do you practice concierge medicine at this Practice Location?"
   - Displayed ONLY when `Practitioner Role = PCP` OR `Practitioner Role = Dual`
   - Applies to both **new** practice locations being added and **existing** PCP practice locations being reviewed
   - Pre-populates to "Yes" if an active Concierge Info Code Assignment already exists at the HealthcarePractitionerFacility level
   - **On Yes:** Creates `PRM_InfoCodeAssignment__c` at the Practitioner Practice Location (`PRM_PractitionerFacilityAssignment__c`) level
   - **On No (previously Yes):** Terminates the existing Practitioner Practice Location-level Info Code Assignment by setting `PRM_TerminationDate__c` to today
   - New Story 6.3: Address screen question + Info Code Assignment creation/termination logic (+5 points)

7. **Recred PSV Guided Flow – Practitioner-Level Info Code Assignment Creation on "Yes" (Version 4.3 - UPDATE to Story 6.2)**
   - When a practitioner answers "Yes" to Q1 ("Do you practice concierge medicine?") in the PSV Guided Flow AND all 4 questions are answered:
     - System checks for an existing active `PRM_InfoCodeAssignment__c` at the practitioner (`PRM_Account__c`) level
     - **If none exists:** Automatically creates a new `PRM_InfoCodeAssignment__c` with "Concierge PCP" Info Code at the practitioner level
     - **If one already exists:** No duplicate is created
   - New DataRaptor Extract: `PRMDRFetchConciergeAssignmentAtPractitioner`
   - New Integration Procedure: `PRM_RecredCreateConciergeAtPractitioner`
   - Story 6.2 updated: +2 story points

### Impact Summary (v4.3):

| Area | Change | Story Points Added |
|------|--------|-------------------|
| **Epic 6 (v4.3)** | Recred PSV address screen concierge question + assignment logic (Story 6.3) | +5 |
| **Epic 6 (v4.3)** | Practitioner-level Info Code Assignment creation on Q1=Yes (Story 6.2 updated) | +2 |
| **Total** | | **+7 points** |

### New Total Effort (v4.3):
- **Version 4.2:** ~140 story points
- **Version 4.3 additions:** +7 points (+2 Story 6.2 update, +5 Story 6.3 new)
- **Version 4.3 Total:** ~147 story points

---

## Version 4.0/4.1/4.2 Change Summary (April 5-6, 2026)

### Business Requirements Incorporated:

1. **Multi-Level Info Code Assignments**
   - Added support for Info Code Assignment at **Practitioner Practice Location** (HealthcarePractitionerFacility) level
   - Enables granular tracking: specific practitioner at specific practice location
   - Updated Story 1.3 to include this capability
   - Updated validation rules to allow one of three levels: Account OR HealthcareFacility OR PractitionerFacilityAssignment

2. **Boolean Checkboxes for Quick Access**
   - Added `PRM_IsConciergeProvider__c` (Checkbox) on:
     - Account (Practitioner)
     - HealthcareFacility (Practice Location)
     - HealthcarePractitionerFacility (Practitioner Practice Location)
   - Automatically set to TRUE when active Info Code Assignment exists
   - Maintained by trigger logic (Story 1.7)
   - New Story 1.6: Field creation
   - New Story 1.7: Trigger logic and backfill batch

3. **Case Manager PAR Form Answer Capture**
   - Added two fields on IndividualApplication (Case Manager):
     - `PRM_ConciergeMedicineIndicator__c` (Checkbox) - captures "Do you practice concierge medicine?" answer
     - `PRM_ConciergeFeeOptional__c` (Checkbox) - captures "Is concierge fee optional?" answer
   - Preserves original PAR form responses for audit and reporting
   - Independent of case approval/denial status
   - New Story 2.4A: Field creation
   - Updated Story 2.5: Integration mapping to save answers

4. **Practice Location Selection in PAR Form (Version 4.1 - NEW)**
   - Added practice location-level selection in PAR form
   - Practitioners can select which specific locations they practice concierge medicine at
   - For each selected location, creates Info Code Assignment at Practitioner Practice Location level
   - Validation: Must select at least one location if concierge = Yes
   - Updated Story 2.2: Added practice location iteration UI (+3 points)
   - Updated Story 2.5: Added loop logic to create assignments for each selected location (+3 points)

5. **Recredentialing PSV Guided Flow Integration (Version 4.2 - NEW)**
   - Added concierge medicine questions to Recredentialing PSV Guided Flow
   - Four recredentialing-specific questions:
     1. Do you practice concierge medicine? (Yes/No)
     2. Did you offer concierge prior to 01/01/2025? (Yes/No)
     3. Is fee optional for existing patients? (Yes/No)
     4. Will you accept new non-concierge patients? (Yes/No)
   - Three new fields on Case Manager (IndividualApplication):
     - `PRM_ConciergeOfferedPriorToDate__c`
     - `PRM_ConciergeFeeOptionalExisting__c`
     - `PRM_AcceptsNewPatientsNonConcierge__c`
   - Warning message with hyperlinks to Provider Manuals
   - Standard field access and DART notification requirements
   - New Story 6.1: Case Manager field creation (+3 points)
   - New Story 6.2: PSV Guided Flow updates and mapping (+9 points)

### Impact Summary:

| Area | Change | Story Points Added |
|------|--------|-------------------|
| **Epic 1 (v4.0)** | Boolean checkbox fields (Story 1.6) | +3 |
| **Epic 1 (v4.0)** | Trigger logic for boolean checkboxes (Story 1.7) | +5 |
| **Epic 1 (v4.0)** | Practitioner Practice Location assignment support (Story 1.3 updated) | 0 (absorbed) |
| **Epic 2 (v4.0)** | Case Manager fields creation (Story 2.4A) | +2 |
| **Epic 2 (v4.0)** | Case Manager field mapping (Story 2.5 updated) | 0 (absorbed) |
| **Epic 2 (v4.1)** | Practice location selection UI (Story 2.2 updated) | +3 |
| **Epic 2 (v4.1)** | Loop logic for multiple assignments (Story 2.5 updated) | +3 |
| **Epic 6 (v4.2)** | Recred Case Manager fields creation (Story 6.1) | +3 |
| **Epic 6 (v4.2)** | Recred PSV Guided Flow updates (Story 6.2) | +9 |
| **Total** | | **+28 points** |

### New Total Effort:
- **Version 3.0:** ~105 story points
- **Version 4.0:** ~117 story points (+12 from 3.0)
- **Version 4.1:** ~128 story points (+23 from 3.0)
- **Version 4.2:** ~140 story points (+35 from 3.0)
- **Timeline:** 8-9 sprints (4-4.5 months)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Data Model Overview](#data-model-overview)
3. [Epic Overview](#epic-overview)
4. [Epic 1: Core Infrastructure & Setup](#epic-1-core-infrastructure--setup)
5. [Epic 2: Data Capture via PAR Form](#epic-2-data-capture-via-par-form)
6. [Epic 3: Internal Analytics Integration](#epic-3-internal-analytics-integration)
7. [Epic 4: Public Provider Directory Integration](#epic-4-public-provider-directory-integration)
8. [Epic 5: UX Enhancements & Data Quality](#epic-5-ux-enhancements--data-quality)
9. [Epic 6: Recredentialing PSV Guided Flow](#epic-6-recredentialing-psv-guided-flow)
10. [Cross-Epic Dependencies](#cross-epic-dependencies)
11. [Technical Considerations](#technical-considerations)
12. [Definition of Done](#definition-of-done)
13. [Acceptance Testing Strategy](#acceptance-testing-strategy)
14. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

This document provides a complete implementation plan for **Concierge Medicine Provider tracking** in the PIE system, organized in logical implementation order: configuration → data capture → integration → enhancements.

### Why Info Code Approach?

**Benefits over field-based approach:**
- ✅ **Minimal schema changes** - only rollup boolean fields on key objects for quick access
- ✅ **Flexible date tracking** via Info Code Assignment effective/termination dates
- ✅ **Proven pattern** already used for PNC and Delegated credentialing
- ✅ **Multi-level assignment** - Practitioner, Practice Location, AND Practitioner Practice Location junction
- ✅ **Automatic rollup logic** via triggers to maintain boolean checkboxes
- ✅ **Audit trail** built-in with Info Code Assignment history
- ✅ **Integration-friendly** - feeds can query Info Code Assignments
- ✅ **Easier to maintain** - no field-level security complexity

### New Business Requirements (Version 4.0):

1. **Multi-Level Assignments**: Info Code Assignments can be created at:
   - Practitioner level (Account)
   - Practice Location level (HealthcareFacility)
   - **NEW: Practitioner Practice Location level** (junction object)

2. **Boolean Checkboxes for Quick Access**: Add `PRM_IsConciergeProvider__c` boolean field on:
   - Practitioner (Account)
   - Practitioner Practice Location (junction)
   - Practice Location (HealthcareFacility)
   - Set to TRUE when active Info Code Assignment exists

3. **PAR Form Answer Capture**: Save PAR form responses on Case Manager (IndividualApplication):
   - `PRM_ConciergeMedicineIndicator__c` (Yes/No)
   - `PRM_ConciergeFeeOptional__c` (Yes/No)

### Two Info Codes to Implement:

1. **Internal: "Concierge PCP"** - For internal analytics (DART, Inquire Only only)
2. **External: "Concierge Provider"** - For public Provider Directory

### Implementation Flow:

```
Epic 1: Setup           Epic 2: Capture      Epic 3: Internal     Epic 4: External     Epic 5: Enhancements
(Config)                (PAR Form)           (Analytics)          (Directory)          (UX/Quality)
    ↓                        ↓                     ↓                    ↓                     ↓
Create Info Codes → Capture via Form → Feed to DART → Feed to Directory → Dashboards
                                      ↓ Inquire Only                    ↓ Data Quality
```

---

## Data Model Overview

### Info Code Master Records

```
PRM_InfoCode__c (Master)
├── "Concierge PCP" (Internal use only)
│   ├── PRM_InfoCodeType__c: "Provider Attribute"
│   ├── PRM_IsActive__c: true
│   └── Description: "Internal use only - for DART & Inquire Only analytics"
│
└── "Concierge Provider" (External use)
    ├── PRM_InfoCodeType__c: "Provider Attribute"
    ├── PRM_IsActive__c: true
    └── Description: "Public-facing - for Provider Directory display"
```

### Info Code Assignment (Junction)

```
PRM_InfoCodeAssignment__c
├── PRM_InfoCode__c → PRM_InfoCode__c (lookup to master)
├── PRM_Account__c → Account (Practitioner) (lookup)
├── PRM_HealthcareFacility__c → HealthcareFacility (Practice Location) (lookup)
├── PRM_PractitionerFacilityAssignment__c → HealthcarePractitionerFacility (Practitioner Practice Location) (lookup) **NEW**
├── PRM_EffectiveDate__c: Date (when concierge status started)
├── PRM_TerminationDate__c: Date (when concierge status ended)
├── PRM_Pending__c: Boolean (for case workflow integration)
├── PRM_CaseManager__c: IndividualApplication (link to case)
└── PRM_IsFeeOptional__c: Checkbox (optional - if fee is optional to patients)
```

**Assignment Levels:** One of the following must be populated:
- `PRM_Account__c` (Practitioner-level assignment)
- `PRM_HealthcareFacility__c` (Practice Location-level assignment)
- `PRM_PractitionerFacilityAssignment__c` (Practitioner Practice Location-level assignment) **NEW**

### Boolean Rollup Fields (NEW - Version 4.0)

```
Account (Practitioner)
└── PRM_IsConciergeProvider__c: Checkbox (TRUE if active Info Code Assignment exists)

HealthcareFacility (Practice Location)
└── PRM_IsConciergeProvider__c: Checkbox (TRUE if active Info Code Assignment exists)

HealthcarePractitionerFacility (Practitioner Practice Location)
└── PRM_IsConciergeProvider__c: Checkbox (TRUE if active Info Code Assignment exists)
```

### Case Manager Fields (NEW - Version 4.0)

```
IndividualApplication (Case Manager)
├── PRM_ConciergeMedicineIndicator__c: Checkbox (captures PAR form answer: Do you practice concierge medicine?)
└── PRM_ConciergeFeeOptional__c: Checkbox (captures PAR form answer: Is concierge fee optional?)
```

### Integration Flows

| System | Data Source | Query Pattern |
|--------|-------------|---------------|
| **PAR Form** | User input | Creates "Concierge Provider" assignment when user answers Yes; Updates Case Manager fields (always) **NEW** |
| **Boolean Checkboxes (NEW)** | Trigger logic | Automatically set to TRUE when active assignment exists; Used for quick filtering and UI display |
| **DART** | Info Code Assignments | WHERE PRM_InfoCode__r.Name = 'Concierge PCP' AND (PRM_TerminationDate__c = null OR > TODAY) |
| **Inquire Only** | Info Code Assignments | Same as DART |
| **Provider Directory** | Info Code Assignments | WHERE PRM_InfoCode__r.Name = 'Concierge Provider' AND (PRM_TerminationDate__c = null OR > TODAY) |

### Assignment Levels (Version 4.0)

| Assignment Level | Use Case | Example |
|------------------|----------|---------|
| **Practitioner** | All practices of this practitioner are concierge | Dr. Smith practices concierge medicine at all locations |
| **Practice Location** | All practitioners at this location are concierge | "Concierge Primary Care of Philadelphia" - all PCPs are concierge |
| **Practitioner Practice Location (NEW)** | This specific practitioner at this specific location practices concierge | Dr. Smith practices concierge at Location A, but not at Location B |

---

## Epic Overview

| Epic | Focus Area | Story Points | Priority |
|------|-----------|--------------|----------|
| **Epic 1** | Core Infrastructure & Setup | 23 (+10 for new features) | P0 - Critical |
| **Epic 2** | Data Capture via PAR Form | 26 (+8 for version 4.0 + 4.1) | P0 - Critical |
| **Epic 3** | Internal Analytics Integration | 13 | P0 - Critical |
| **Epic 4** | Public Provider Directory Integration | 16 | P0 - Critical |
| **Epic 5** | UX Enhancements & Data Quality | 13 | P1 - High |
| **Epic 6** | Recredentialing PSV Guided Flow | 19 (12 v4.2 + 7 v4.3) | P0 - Critical |
| **Total** | | **110** | |

**Additional Effort:** Flow Integration Changes (from separate analysis document) = 37 points
**Grand Total:** ~147 story points (8-9 sprints)

**New in Version 4.0:**
- +10 points: Boolean checkbox fields and trigger logic (Epic 1)
- +2 points: Case Manager PAR form answer fields (Epic 2)

**New in Version 4.1:**
- +3 points: Practice location selection UI in PAR form (Epic 2, Story 2.2)
- +3 points: Loop logic to create multiple Practitioner Practice Location assignments (Epic 2, Story 2.5)

**New in Version 4.2:**
- +12 points: Recredentialing PSV Guided Flow integration (Epic 6, Stories 6.1 and 6.2)

**New in Version 4.3:**
- +5 points: Recred PSV address screen per-location concierge question + Info Code Assignment logic (Epic 6, Story 6.3)

---

## Epic 1: Core Infrastructure & Setup

**Epic Goal:** Create Info Code master records and set up Info Code Assignment infrastructure for concierge medicine tracking.

**Business Value:** Foundation for all concierge tracking; enables data capture, integration, and reporting.

**Priority:** P0 - Critical
**Estimated Story Points:** 13

---

### Story 1.1: Create "Concierge PCP" Info Code Master Record (Internal)

**As a** System Administrator
**I want** to create an internal "Concierge PCP" Info Code master record
**So that** this code can be assigned to practitioners and practice locations for internal analytics

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Info Code Setup

#### Acceptance Criteria

1. **Info Code Creation**
   - PRM_InfoCode__c record created with Name = "Concierge PCP"
   - PRM_InfoCodeType__c = "Provider Attribute" (or appropriate type)
   - PRM_IsActive__c = true
   - Description field: "Internal use only - identifies concierge primary care physicians for DART and Inquire Only analytics"
   - Record is visible to PDA team and system admins

2. **Info Code Configuration**
   - Info Code is flagged as "Internal Only" (via custom field or metadata if available)
   - Info Code is NOT included in Provider Directory feed configuration
   - Info Code appears in Info Code picklists/lookups for PDA users
   - Info Code can be searched and selected when creating Info Code Assignments

3. **Documentation**
   - Info Code usage documented in system documentation
   - PDA team training materials updated
   - Info Code purpose and scope clearly documented

#### Technical Considerations

- Object: PRM_InfoCode__c
- Verify field schema: Name, PRM_InfoCodeType__c, PRM_IsActive__c, Description
- Ensure Info Code is available in all environments (sandbox, UAT, prod)
- Consider adding custom checkbox: PRM_InternalOnly__c = true (optional)

#### Dependencies

- Access to PRM_InfoCode__c object in org
- Permissions to create Info Code records
- Info Code Type picklist values defined

#### Definition of Done

- [ ] "Concierge PCP" Info Code record created in all environments
- [ ] Info Code is active and visible to PDA team
- [ ] Info Code description includes "Internal use only"
- [ ] Info Code documentation updated
- [ ] PDA team notified of new Info Code availability

---

### Story 1.2: Create "Concierge Provider" Info Code Master Record (External)

**As a** System Administrator
**I want** to create an external "Concierge Provider" Info Code master record
**So that** this code can be assigned to practitioners and practice locations for public Provider Directory display

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Info Code Setup

#### Acceptance Criteria

1. **Info Code Creation**
   - PRM_InfoCode__c record created with Name = "Concierge Provider"
   - PRM_InfoCodeType__c = "Provider Attribute"
   - PRM_IsActive__c = true
   - Description field: "Public-facing - identifies concierge providers for Provider Directory"
   - Record is visible to PDA team and system admins

2. **Info Code Configuration**
   - Info Code is flagged as "Public" or "External" (if metadata supports)
   - Info Code IS included in Provider Directory feed configuration
   - Info Code appears in Info Code picklists/lookups for PDA users
   - Info Code can be searched and selected when creating Info Code Assignments

3. **Documentation**
   - Info Code usage documented in system documentation
   - PDA team training materials updated
   - Info Code purpose and scope clearly documented

#### Technical Considerations

- Object: PRM_InfoCode__c
- Same field schema as Story 1.1
- Ensure Info Code is available in all environments
- Consider adding custom checkbox: PRM_PublicFacing__c = true (optional)

#### Dependencies

- Access to PRM_InfoCode__c object in org
- Permissions to create Info Code records

#### Definition of Done

- [ ] "Concierge Provider" Info Code record created in all environments
- [ ] Info Code is active and visible to PDA team
- [ ] Info Code description includes "Public-facing"
- [ ] Info Code documentation updated
- [ ] PDA team notified of new Info Code availability

---

### Story 1.3: Enable Info Code Assignment Creation for Practitioners and Practitioner Practice Locations

**As a** Provider Data Administrator
**I want** to create Info Code Assignments for individual practitioners AND for practitioner practice location relationships
**So that** I can track concierge status at the practitioner level and at the practitioner-practice relationship level

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI - Practitioner Level**
   - PDA user can create PRM_InfoCodeAssignment__c record from Practitioner Account page
   - PRM_InfoCode__c lookup shows both "Concierge PCP" and "Concierge Provider" as selectable options
   - PRM_Account__c is auto-populated with current Practitioner Account
   - PRM_EffectiveDate__c field is visible and editable (MM/DD/YYYY format)
   - PRM_TerminationDate__c field is visible and editable (MM/DD/YYYY format)
   - Save button persists the assignment

2. **Assignment Creation UI - Practitioner Practice Location Level (NEW)**
   - PDA user can create PRM_InfoCodeAssignment__c record from HealthcarePractitionerFacility (Practitioner Practice Location) page
   - PRM_InfoCode__c lookup shows both "Concierge PCP" and "Concierge Provider" as selectable options
   - PRM_PractitionerFacilityAssignment__c is auto-populated with current HealthcarePractitionerFacility record
   - PRM_EffectiveDate__c and PRM_TerminationDate__c fields are visible and editable
   - Save button persists the assignment
   - Use Case: Assign concierge status to a specific practitioner at a specific practice location (not all locations)

3. **Validation Rules**
   - PRM_InfoCode__c is required
   - ONE of the following must be populated (not multiple):
     - PRM_Account__c (Practitioner-level)
     - PRM_HealthcareFacility__c (Practice Location-level)
     - PRM_PractitionerFacilityAssignment__c (Practitioner Practice Location-level) **NEW**
   - PRM_EffectiveDate__c cannot be in the future
   - PRM_TerminationDate__c cannot be before PRM_EffectiveDate__c
   - PRM_TerminationDate__c cannot be in the future
   - Duplicate assignment prevention: Cannot create duplicate active assignment (same Info Code + same level + no termination date)

4. **List View / Related List**
   - "Info Code Assignments" related list appears on Practitioner Account page
   - "Info Code Assignments" related list appears on HealthcarePractitionerFacility (Practitioner Practice Location) page **NEW**
   - List shows: Info Code Name, Effective Date, Termination Date, Pending status
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

5. **Assignment Visibility**
   - Assignments are visible to PDA team
   - "Concierge PCP" assignments will feed to DART/Inquire Only (configured in later stories)
   - "Concierge Provider" assignments will feed to Provider Directory (configured in later stories)
   - Practitioner Practice Location-level assignments are distinct from Practitioner-level assignments (more granular)

#### Technical Considerations

- Object: PRM_InfoCodeAssignment__c
- Relationships: 
  - PRM_InfoCode__c (lookup)
  - PRM_Account__c (lookup)
  - PRM_HealthcareFacility__c (lookup)
  - PRM_PractitionerFacilityAssignment__c (lookup) **NEW** - links to HealthcarePractitionerFacility
- Page Layouts: 
  - Add "Info Code Assignments" related list to Practitioner Account layout
  - Add "Info Code Assignments" related list to HealthcarePractitionerFacility layout **NEW**
- Validation Rules: Implement as Apex trigger to ensure only one of the three lookups is populated
- Consider Lightning component for inline assignment creation

#### Dependencies

- Stories 1.1 and 1.2 completed (Info Codes exist)
- PRM_InfoCodeAssignment__c object access
- Practitioner Account page layout editable
- HealthcarePractitionerFacility object and page layout accessible **NEW**

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practitioner
- [ ] PDA user can create Info Code Assignment for Practitioner Practice Location **NEW**
- [ ] Both "Concierge PCP" and "Concierge Provider" Info Codes are selectable
- [ ] Effective Date and Termination Date fields work correctly
- [ ] Validation rules prevent invalid assignments (only one level at a time) **UPDATED**
- [ ] Related list displays assignments on Practitioner page
- [ ] Related list displays assignments on Practitioner Practice Location page **NEW**
- [ ] Unit tests for validation rules pass
- [ ] UAT completed by PDA team

---

### Story 1.4: Enable Info Code Assignment Creation for Practice Locations

**As a** Provider Data Administrator
**I want** to create Info Code Assignments for practice locations
**So that** I can track concierge status at the practice location level (when all PCPs are concierge)

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI**
   - PDA user can create PRM_InfoCodeAssignment__c record from HealthcareFacility (Practice Location) page
   - PRM_InfoCode__c lookup shows both "Concierge PCP" and "Concierge Provider" as selectable options
   - PRM_HealthcareFacility__c is auto-populated with current Practice Location
   - PRM_EffectiveDate__c and PRM_TerminationDate__c fields are visible and editable
   - Save button persists the assignment

2. **Validation Rules**
   - Same validation rules as Story 1.3 (future dates, date order, duplicates)
   - PRM_HealthcareFacility__c is populated (PRM_Account__c is null for practice-level assignment)

3. **List View / Related List**
   - "Info Code Assignments" related list appears on Practice Location page
   - List shows: Info Code Name, Effective Date, Termination Date, Pending status
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

4. **Use Case Guidance**
   - Field help text clarifies: "Assign at Practice Location level when ALL PCPs at this location operate concierge practices"
   - Warning message if trying to assign at practice level when individual practitioners already have the code (data quality check - optional)

#### Technical Considerations

- Same as Story 1.3 but for HealthcareFacility object
- Page Layout: Add "Info Code Assignments" related list to Practice Location layout
- Consider data quality check: compare practice-level assignment to practitioner-level assignments

#### Dependencies

- Stories 1.1 and 1.2 completed (Info Codes exist)
- PRM_InfoCodeAssignment__c object access
- Practice Location page layout editable

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practice Location
- [ ] Both Info Codes are selectable
- [ ] Validation rules work correctly
- [ ] Related list displays assignments on Practice Location page
- [ ] Help text clarifies practice-level use case
- [ ] Unit tests pass
- [ ] UAT completed by PDA team

---

### Story 1.5: Implement Trigger Logic for Info Code Assignment Changes

**As a** System Processing Info Code Assignment Changes
**I want** triggers to fire when Concierge Info Code Assignments are created, updated, or deleted
**So that** downstream systems and batch jobs are aware of concierge status changes

**Priority:** P1 - High
**Story Points:** 3
**Component:** PIE - Apex Triggers

#### Acceptance Criteria

1. **Trigger Reuse**
   - Existing PRM_InfoCodeAssTrigger handles Concierge Info Code Assignments (no new trigger needed)
   - Trigger includes logic for "Concierge PCP" and "Concierge Provider" Info Codes
   - Trigger is bulkified (handles 200+ records)

2. **Trigger Actions**
   - Log Info Code Assignment changes (if audit logging required)
   - Queue batch jobs if needed (e.g., recalculate derived fields - optional)
   - Send platform events if downstream systems require real-time notifications (optional)

3. **Error Handling**
   - Trigger includes try-catch blocks
   - Errors are logged and do not block DML operations (or block with clear error messages)
   - Unit tests cover error scenarios

4. **Performance**
   - Trigger executes within acceptable time (< 2 seconds for typical batches)
   - No SOQL queries inside loops
   - Bulkified logic handles large data volumes

#### Technical Considerations

- Trigger: PRM_InfoCodeAssTrigger (already exists for other Info Codes)
- Helper Class: Reuse PRM_InfoCodeAssTriggerHelper (no changes needed for basic functionality)
- Rollup Logic: NOT recommended - feeds will query Info Code Assignments directly
- Testing: Unit tests with 200+ records

#### Dependencies

- Stories 1.1, 1.2, 1.3, 1.4 completed (Info Codes and Assignments exist)
- Access to trigger and helper class code

#### Definition of Done

- [ ] Trigger handles Concierge Info Code Assignments (verified)
- [ ] No rollup logic added (feeds query directly - confirmed)
- [ ] Unit tests written and passing (200+ records)
- [ ] Error handling tested
- [ ] Performance testing completed
- [ ] Code review completed (if any changes)
- [ ] Technical documentation updated

---

### Story 1.6: Create Boolean Checkbox Fields on Practitioner, Practice Location, and Practitioner Practice Location

**As a** System Administrator
**I want** boolean checkbox fields on Practitioner, Practice Location, and Practitioner Practice Location objects
**So that** users can quickly see concierge provider status without querying Info Code Assignments

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Schema / Field Creation

#### Acceptance Criteria

1. **Field Creation on Account (Practitioner)**
   - Create field: `PRM_IsConciergeProvider__c` (Checkbox)
   - Field Label: "Is Concierge Provider"
   - Help Text: "Indicates whether this practitioner has an active Concierge Provider Info Code Assignment"
   - Default Value: false
   - Field is visible to PDA team and read-only for manual editing (managed by trigger)

2. **Field Creation on HealthcareFacility (Practice Location)**
   - Create field: `PRM_IsConciergeProvider__c` (Checkbox)
   - Field Label: "Is Concierge Provider"
   - Help Text: "Indicates whether this practice location has an active Concierge Provider Info Code Assignment"
   - Default Value: false
   - Field is visible to PDA team and read-only for manual editing (managed by trigger)

3. **Field Creation on HealthcarePractitionerFacility (Practitioner Practice Location)**
   - Create field: `PRM_IsConciergeProvider__c` (Checkbox)
   - Field Label: "Is Concierge Provider"
   - Help Text: "Indicates whether this practitioner-practice relationship has an active Concierge Provider Info Code Assignment"
   - Default Value: false
   - Field is visible to PDA team and read-only for manual editing (managed by trigger)

4. **Field Visibility on Page Layouts**
   - Add `PRM_IsConciergeProvider__c` to Practitioner Account page layout (prominent section)
   - Add `PRM_IsConciergeProvider__c` to Practice Location page layout (prominent section)
   - Add `PRM_IsConciergeProvider__c` to Practitioner Practice Location page layout (prominent section)
   - Visual indicator (icon or badge) shows status clearly

5. **Field Level Security**
   - PDA team: Read access (no edit access - managed by automation)
   - System Admin: Read and Edit access (for manual override if needed)
   - Integration users: Read access
   - Other users: No access or read-only based on object-level security

#### Technical Considerations

- **Objects:** Account, HealthcareFacility, HealthcarePractitionerFacility
- **Field API Name:** `PRM_IsConciergeProvider__c` (consistent across all three objects)
- **Field Type:** Checkbox (Boolean)
- **Automation:** Will be updated by trigger logic in Story 1.7
- **Indexing:** Consider adding index for query performance

#### Dependencies

- Access to schema modification on Account, HealthcareFacility, HealthcarePractitionerFacility
- Page layout edit access

#### Definition of Done

- [ ] `PRM_IsConciergeProvider__c` field created on Account
- [ ] `PRM_IsConciergeProvider__c` field created on HealthcareFacility
- [ ] `PRM_IsConciergeProvider__c` field created on HealthcarePractitionerFacility
- [ ] Fields added to page layouts
- [ ] Field-level security configured
- [ ] Help text clearly explains purpose
- [ ] Fields deployed to all environments
- [ ] Documentation updated

---

### Story 1.7: Implement Trigger Logic to Maintain Boolean Checkbox Fields

**As a** System Processing Info Code Assignment Changes
**I want** trigger logic to automatically update the boolean checkbox fields when Info Code Assignments are created, updated, or deleted
**So that** the `PRM_IsConciergeProvider__c` fields always reflect current concierge status

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Apex Triggers

#### Acceptance Criteria

1. **Trigger Logic for Assignment Creation**
   - When a new Info Code Assignment is created with:
     - `PRM_InfoCode__r.Name = 'Concierge Provider'` AND
     - `PRM_TerminationDate__c` is null or in the future
   - Then update:
     - If `PRM_Account__c` is populated: Set `Account.PRM_IsConciergeProvider__c = true`
     - If `PRM_HealthcareFacility__c` is populated: Set `HealthcareFacility.PRM_IsConciergeProvider__c = true`
     - If `PRM_PractitionerFacilityAssignment__c` is populated: Set `HealthcarePractitionerFacility.PRM_IsConciergeProvider__c = true`

2. **Trigger Logic for Assignment Termination**
   - When an Info Code Assignment is updated and `PRM_TerminationDate__c` is set to a past date:
     - Query if any OTHER active assignments exist for the same record
     - If no other active assignments: Set corresponding `PRM_IsConciergeProvider__c = false`
     - If other active assignments exist: Keep `PRM_IsConciergeProvider__c = true`

3. **Trigger Logic for Assignment Deletion**
   - When an Info Code Assignment is deleted:
     - Query if any OTHER active assignments exist for the same record
     - If no other active assignments: Set corresponding `PRM_IsConciergeProvider__c = false`
     - If other active assignments exist: Keep `PRM_IsConciergeProvider__c = true`

4. **Bulkified Logic**
   - Trigger handles 200+ Info Code Assignments in a single transaction
   - No SOQL queries inside loops
   - All updates are performed as bulk DML operations
   - No governor limit violations

5. **Backfill Logic (Optional Batch)**
   - Create batch class: `PRM_BackfillConciergeBooleanBatch`
   - Batch processes all existing Practitioners, Practice Locations, and Practitioner Practice Locations
   - For each record, checks if active "Concierge Provider" assignment exists
   - Updates `PRM_IsConciergeProvider__c` accordingly
   - Batch is run once after initial deployment

6. **Error Handling**
   - Trigger includes try-catch blocks
   - Errors are logged but do not block Info Code Assignment DML
   - Failed updates are retried or queued for manual review

#### Technical Considerations

- **Trigger:** Extend `PRM_InfoCodeAssTrigger` or create dedicated trigger
- **Helper Class:** Extend `PRM_InfoCodeAssTriggerHelper` or create `PRM_ConciergeAssignmentHelper`
- **Query Logic:** 
  ```apex
  // Pseudo-code
  List<PRM_InfoCodeAssignment__c> activeAssignments = [
    SELECT Id, PRM_Account__c, PRM_HealthcareFacility__c, PRM_PractitionerFacilityAssignment__c
    FROM PRM_InfoCodeAssignment__c
    WHERE PRM_InfoCode__r.Name = 'Concierge Provider'
    AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
    AND (PRM_Account__c = :accountId OR PRM_HealthcareFacility__c = :facilityId OR PRM_PractitionerFacilityAssignment__c = :pfaId)
  ];
  ```
- **Backfill Batch:** Run once, then can be archived or kept for periodic refresh
- **Testing:** Unit tests with bulk data, edge cases (multiple assignments, same-day termination, etc.)

#### Dependencies

- Story 1.6 completed (boolean fields exist)
- Stories 1.1-1.5 completed (Info Codes and Assignments exist)
- Access to trigger and Apex code

#### Definition of Done

- [ ] Trigger logic implemented and deployed
- [ ] Creation scenario tested (assignment created → boolean set to true)
- [ ] Termination scenario tested (assignment terminated → boolean set to false if no other active)
- [ ] Deletion scenario tested
- [ ] Bulkified logic tested (200+ records)
- [ ] Backfill batch created and run once
- [ ] All existing records have correct boolean values
- [ ] Error handling tested
- [ ] Unit tests pass (90%+ code coverage)
- [ ] Integration tests pass
- [ ] Performance testing completed
- [ ] Code review completed
- [ ] Documentation updated

---

## Epic 2: Data Capture via PAR Form

**Epic Goal:** Update the Practitioner Participation Request (PAR) form to capture concierge medicine information from practitioners during credentialing, allow selection of specific practice locations, and automatically create Info Code Assignments at the Practitioner Practice Location level.

**Business Value:** Accurate capture of concierge medicine practice at the point of credentialing with granular location-level tracking; automated Info Code Assignment creation at the correct level.

**Priority:** P0 - Critical
**Estimated Story Points:** 26 (+6 from version 4.0: Story 2.2 +3, Story 2.5 +3)

---

### Story 2.1: Remove Existing Generic Fee Questions from PAR Form

**As a** Form Designer
**I want** to remove the two existing generic fee questions from the Practitioner screen
**So that** we can replace them with more specific concierge medicine questions

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Questions Removed**
   - Question: "Do you require patients to pay a fee in order to be a patient of the practice or for additional services (e.g., concierge fees) beyond applicable member cost sharing?" is removed
   - Question: "Do you offer patients the options to pay a fee in order to receive enhanced services such as longer visit times, access to a physician's cell phone, priority scheduling, etc?" is removed
   - Removed questions do not appear in any PAR form views (create, edit, review)

2. **Backward Compatibility**
   - Existing PAR applications submitted before this change retain their responses to old questions (data not deleted)
   - Old responses are visible in historical records but not editable
   - Reporting/analytics can still access historical data

3. **OmniScript Elements**
   - OmniScript elements for removed questions are deleted or hidden
   - Related validation rules are disabled/removed
   - Navigation/step logic is updated

4. **Testing**
   - New PAR form submissions do not show removed questions
   - Old PAR applications can still be viewed in read-only mode
   - No console errors or broken UI elements

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English`
- **Elements to Remove:** Identify element names for old fee questions
- **DataRaptor Impact:** Verify if any DataRaptors reference these fields; update if needed
- **Integration Procedure Impact:** Verify if any IPs use these fields; update if needed

#### Dependencies

- Access to OmniScript designer
- Approval to remove questions (business sign-off)
- Coordination with reporting team

#### Definition of Done

- [ ] Old questions removed from PAR form
- [ ] Form renders correctly without errors
- [ ] Historical data remains accessible
- [ ] Regression testing completed
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 2.2: Add Concierge Medicine Questions for PCP/Dual Practitioners (Practitioner and Practice Location Level)

**As a** PCP or Dual practitioner completing the PAR form
**I want** to answer whether I practice concierge medicine and select which specific practice locations use the concierge model
**So that** the credentialing team accurately captures my practice model at each location

**Priority:** P0 - Critical
**Story Points:** 8 (+3 for practice location iteration logic)
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Practitioner-Level Question Display Logic**
   - New question is displayed ONLY when `Practitioner Role = PCP` OR `Practitioner Role = Dual`
   - Question is NOT displayed for other practitioner roles
   - Question is required (cannot proceed without answering)
   - Question appears before "*Are you joining an existing group?"

2. **Practitioner-Level Question Text and Format**
   - Question text:
     ```
     *(For PCPs only) Do you practice concierge medicine (or retainer medicine) by charging your
     patients a concierge fee (or retainer) separate from the applicable patient cost sharing
     (e.g., co-pays, deductibles, etc.)?
     ```
   - Radio button control:
     - ○ Yes
     - ○ No
   - Asterisk (*) indicates required field
   - Help text (optional tooltip): "Concierge medicine is a membership-based healthcare model where patients pay a retainer fee for enhanced access and services."

3. **Practice Location-Level Questions (NEW)**
   - If practitioner answers "Yes" to practitioner-level question, additional section appears
   - Section displays: "Please indicate which practice location(s) where you practice concierge medicine:"
   - For EACH practice location in the PAR application:
     - Display practice location name and address
     - Display checkbox or radio button: "I practice concierge medicine at this location"
     - User can select one, multiple, or all locations
     - At least ONE location must be selected if practitioner-level answer is "Yes"
   - If practitioner answers "No" at practitioner level, this section is hidden

4. **Practice Location Selection Logic**
   - Practice locations are dynamically loaded from practitioner's PAR application
   - If only one location: Auto-select and show as checked (user can uncheck if needed)
   - If multiple locations: All unchecked by default, user selects applicable ones
   - Visual grouping: Each location appears as a distinct row/card
   - Validation: If practitioner-level = "Yes" but NO locations selected → error: "Please select at least one practice location where you practice concierge medicine"

5. **Response Capture**
   - Practitioner-level response saved to OmniScript data
   - Practice location selections saved as array/list (e.g., `[locationId1, locationId2, ...]`)
   - Responses visible in form review/summary step
   - Responses persisted when form is saved (draft or submitted)

6. **Conditional Trigger for Optional Fee Question**
   - If user selects "Yes" at practitioner level, the optional fee question (Story 2.3) is displayed immediately below practitioner-level question
   - If user selects "No", the optional fee question is hidden
   - Changing answer from "Yes" to "No" hides both optional fee question AND practice location section

7. **Validation**
   - Cannot submit form without answering practitioner-level question (if PCP/Dual)
   - If practitioner-level = "Yes", must select at least one practice location
   - Error messages:
     - "Please indicate whether you practice concierge medicine."
     - "Please select at least one practice location where you practice concierge medicine."

#### Technical Considerations

- **OmniScript:** `PRM_PractitionerParticipationForm_English`
- **Practitioner-Level Element:**
  - Element Type: Radio Button
  - Element Name: `RadioConciergeMedicine`
  - Show Condition: `%PractitionerRole% == 'PCP' OR %PractitionerRole% == 'Dual'`
  - Required: Yes
- **Practice Location-Level Elements:**
  - Element Type: Block (repeating) or Checkbox Group
  - Element Name: `CheckboxConciergePracticeLocations`
  - Show Condition: `%RadioConciergeMedicine% == 'Yes'`
  - Data Source: Practice locations from current PAR application (from `HealthcarePractitionerFacility` records or form data)
  - Iteration Logic: Use DataRaptor or Integration Procedure to fetch practice locations
  - Output: Array of selected location IDs (e.g., `["001xx000001", "001xx000002"]`)
- **Validation:**
  - Custom validation: If `%RadioConciergeMedicine% == 'Yes'` AND `%CheckboxConciergePracticeLocations%.length == 0` → error

#### Dependencies

- Story 2.1 completed (old questions removed)
- Practitioner Role field exists and is populated earlier in form
- Practice locations are captured/available earlier in PAR form
- DataRaptor or IP to fetch practice locations for current application

#### Definition of Done

- [ ] Practitioner-level question added to OmniScript
- [ ] Practice location-level section added with iteration logic **NEW**
- [ ] Practice locations dynamically loaded from application data **NEW**
- [ ] Conditional display logic works (PCP/Dual only)
- [ ] Practitioner-level question is required and validation works
- [ ] Practice location selection validation works (at least one if Yes) **NEW**
- [ ] Responses saved correctly (practitioner-level and location array) **NEW**
- [ ] Conditional trigger for optional fee question works
- [ ] Conditional trigger for practice location section works **NEW**
- [ ] UI/UX review completed (multiple location selection design) **NEW**
- [ ] Unit tests pass
- [ ] Integration test: Single location scenario **NEW**
- [ ] Integration test: Multiple location selection scenario **NEW**
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 2.3: Add Optional Fee Question (Conditional on Concierge = Yes)

**As a** PCP or Dual practitioner who practices concierge medicine
**I want** to indicate whether my concierge fee is optional for patients
**So that** the credentialing team understands my fee structure

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Question Display Logic**
   - Question is displayed ONLY when:
     - Practitioner Role = PCP OR Dual
     - AND Concierge Medicine Question = "Yes"
   - Question is hidden if Concierge Medicine Question = "No"
   - Question appears immediately below Concierge Medicine Question
   - Question is required (if displayed)

2. **Question Text and Format**
   - Question text:
     ```
     *Is your concierge fee for additional services optional to your patients?
     ```
   - Radio button control:
     - ○ Yes
     - ○ No
   - Asterisk (*) indicates required field

3. **Response Capture**
   - User selection is saved to OmniScript data
   - Response is persisted when form is saved

4. **Clearing Logic**
   - If parent question changes from "Yes" to "No", this question is hidden AND its response is cleared

5. **Validation**
   - Cannot submit form without answering (if displayed)
   - Error message: "Please indicate whether your concierge fee is optional."

#### Technical Considerations

- **Element Name:** `RadioConciergeFeeOptional`
- **Show Condition:** `%RadioConciergeMedicine% == 'Yes'`
- **Required:** Yes (when shown)

#### Dependencies

- Story 2.2 completed (parent question exists)

#### Definition of Done

- [ ] Question added to OmniScript
- [ ] Conditional display logic works
- [ ] Question is required when displayed
- [ ] Response is saved correctly
- [ ] Clearing logic works when parent changes
- [ ] UI/UX review completed
- [ ] Unit tests pass
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 2.4: Add Concierge Attestation Warning Message with Hyperlinks

**As a** PCP or Dual practitioner completing the PAR form
**I want** to see a warning message about the concierge attestation requirement
**So that** I am aware of the attestation form I need to execute during credentialing

**Priority:** P1 - High
**Story Points:** 3
**Component:** OmniScript - PAR Form

#### Acceptance Criteria

1. **Message Display Logic**
   - Warning message is displayed for ALL practitioners with Role = PCP OR Dual
   - Message is displayed regardless of answer to concierge medicine question
   - Message appears AFTER concierge questions and BEFORE "*Are you joining an existing group?"
   - Message is always visible

2. **Message Text and Format**
   - Text:
     ```
     ⚠️ Please ensure that you review and execute the concierge attestation form during your
     credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and
     Provider Attestation can be found within the Provider Manual located:
     [IBX] | [AHNJ] | [AHPA]

     Noncompliance with executing the concierge attestation may result in the delay or
     rejection of your application.
     ```
   - Warning icon (⚠️) or visual indicator
   - Three hyperlinks:
     - **IBX** → https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx
     - **AHNJ** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx
     - **AHPA** → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx
   - Links open in new tab/window

3. **Visual Design**
   - Message is visually distinct (bordered box, colored background)
   - Font size is readable
   - Spacing/padding for emphasis
   - Consistent with other warning messages

4. **Hyperlink Functionality**
   - Clicking each link opens correct URL in new tab
   - Links are accessible (keyboard navigation, screen reader compatible)
   - Links work in all supported browsers

5. **No User Interaction Required**
   - Message is informational only
   - User can proceed without interacting

#### Technical Considerations

- **Element Type:** Text Block or HTML element
- **Element Name:** `TextBlockConciergeAttestation`
- **Show Condition:** `%PractitionerRole% == 'PCP' OR %PractitionerRole% == 'Dual'`
- **HTML Content:** Use HTML tags for hyperlinks with `target="_blank"`

#### Dependencies

- Story 2.2 completed (concierge questions exist)
- Approval on message wording and URLs

#### Definition of Done

- [ ] Warning message added to OmniScript
- [ ] Message displays for PCP/Dual practitioners
- [ ] Three hyperlinks work correctly
- [ ] Visual styling is consistent
- [ ] Accessibility tested
- [ ] Cross-browser testing completed
- [ ] Mobile/responsive testing completed
- [ ] UI/UX review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

### Story 2.4A: Create Case Manager Fields for PAR Form Answer Capture (NEW)

**As a** System Administrator
**I want** two checkbox fields on the Case Manager (IndividualApplication) object to capture PAR form concierge responses
**So that** we preserve the practitioner's original answers for audit and reporting purposes

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Schema / Field Creation

#### Acceptance Criteria

1. **Field Creation - Concierge Medicine Indicator**
   - Create field: `PRM_ConciergeMedicineIndicator__c` (Checkbox)
   - Object: IndividualApplication (Case Manager)
   - Field Label: "Concierge Medicine Indicator"
   - Help Text: "Indicates whether the practitioner answered 'Yes' to practicing concierge medicine on the PAR form"
   - Default Value: false
   - Field is editable by PDA team

2. **Field Creation - Concierge Fee Optional**
   - Create field: `PRM_ConciergeFeeOptional__c` (Checkbox)
   - Object: IndividualApplication (Case Manager)
   - Field Label: "Concierge Fee Optional"
   - Help Text: "Indicates whether the practitioner's concierge fee is optional to patients (answered 'Yes' on PAR form)"
   - Default Value: false
   - Field is editable by PDA team

3. **Field Visibility on Page Layout**
   - Add both fields to Case Manager page layout
   - Place in "Credentialing Details" or "Provider Information" section
   - Fields are visible in edit and view modes
   - Fields appear in related lists and reports

4. **Field Level Security**
   - PDA team: Read and Edit access
   - System Admin: Read and Edit access
   - Reporting users: Read access
   - Other users: No access or read-only based on role

5. **Backward Compatibility**
   - Existing Case Manager records have default values (false)
   - New Case Manager records will be populated by PAR form (Story 2.5)

#### Technical Considerations

- **Object:** IndividualApplication
- **Field API Names:** `PRM_ConciergeMedicineIndicator__c`, `PRM_ConciergeFeeOptional__c`
- **Field Type:** Checkbox (Boolean)
- **Data Type:** Boolean - easier to query and use in reports than picklist
- **Reporting:** These fields enable tracking of how many practitioners answered Yes/No over time

#### Dependencies

- Access to IndividualApplication object schema
- Page layout edit access

#### Definition of Done

- [ ] `PRM_ConciergeMedicineIndicator__c` field created on IndividualApplication
- [ ] `PRM_ConciergeFeeOptional__c` field created on IndividualApplication
- [ ] Fields added to page layout
- [ ] Field-level security configured
- [ ] Help text clearly explains purpose
- [ ] Fields deployed to all environments
- [ ] Documentation updated
- [ ] Reporting team notified of new fields

---

### Story 2.5: Map PAR Form Concierge Responses to Practitioner Practice Location Info Code Assignments and Case Manager

**As an** Integration Developer
**I want** the PAR form concierge responses to automatically create Info Code Assignments at the Practitioner Practice Location level for each selected location AND save answers on the Case Manager
**So that** the backend system accurately reflects which specific practice locations have concierge status and preserves the original responses

**Priority:** P0 - Critical
**Story Points:** 10 (+3 for iterating through selected locations and creating multiple assignments)
**Component:** Integration Procedure / DataRaptor

#### Acceptance Criteria

1. **Data Mapping Logic - Info Code Assignments at Practitioner Practice Location Level (UPDATED)**
   - When PAR form is submitted with `Concierge Medicine = Yes` AND practice locations selected:
     - For EACH selected practice location, create `PRM_InfoCodeAssignment__c` record with:
       - `PRM_InfoCode__c` = "Concierge Provider" (external Info Code - lookup by name)
       - `PRM_PractitionerFacilityAssignment__c` = HealthcarePractitionerFacility Id for this location **UPDATED**
       - `PRM_Account__c` = NULL (not practitioner-level) **UPDATED**
       - `PRM_HealthcareFacility__c` = NULL (not practice location-level) **UPDATED**
       - `PRM_EffectiveDate__c` = Application submission date or credentialing effective date
       - `PRM_Pending__c` = true (if case workflow is used)
       - `PRM_CaseManager__c` = Case Manager Id (if applicable)
       - `PRM_IsFeeOptional__c` = value from optional fee question (optional field)
   - Example: If practitioner selects 3 locations → create 3 Info Code Assignment records (one per location)
   - When PAR form is submitted with `Concierge Medicine = No`:
     - Do NOT create any Info Code Assignments

2. **Data Mapping Logic - Case Manager Fields (NEW)**
   - When PAR form is submitted, update `IndividualApplication` (Case Manager) record with:
     - `PRM_ConciergeMedicineIndicator__c` = true if "Concierge Medicine = Yes", false if "No"
     - `PRM_ConciergeFeeOptional__c` = true if "Optional Fee = Yes", false if "No" (or null if not answered)
   - These fields preserve the practitioner's original answers
   - Fields are populated regardless of case approval/denial status
   - If case is reopened or amended, fields are updated with new responses

3. **Integration Procedure Logic (UPDATED)**
   - Integration Procedure includes THREE steps:
     - Step 1: Update IndividualApplication (Case Manager) with concierge responses
     - Step 2: Iterate through selected practice locations (conditional: Only if `%RadioConciergeMedicine% == 'Yes'`) **UPDATED**
     - Step 3: For each location, create Info Code Assignment at Practitioner Practice Location level **NEW**
   - Iteration Logic:
     - Input: Array of selected location IDs from `%CheckboxConciergePracticeLocations%`
     - For each location ID in array:
       - Look up corresponding HealthcarePractitionerFacility record (junction between practitioner and location)
       - Create Info Code Assignment with `PRM_PractitionerFacilityAssignment__c` = HealthcarePractitionerFacility Id
   - Error handling: If Step 2/3 fails for any location, log error but continue with remaining locations; Step 1 should always succeed

4. **DataRaptor Mapping - Info Code Assignment (UPDATED)**
   - Create or update DataRaptor to insert `PRM_InfoCodeAssignment__c` (will be called in loop)
   - Input from OmniScript:
     - `RadioConciergeMedicine` (Yes/No)
     - `RadioConciergeFeeOptional` (Yes/No)
     - `PractitionerFacilityAssignmentId` (HealthcarePractitionerFacility Id for current iteration) **UPDATED**
     - `CaseManagerId`
     - `EffectiveDate`
   - Output: `PRM_InfoCodeAssignment__c` Id
   - Note: This DataRaptor will be called once per selected location **NEW**

5. **DataRaptor Mapping - Case Manager Fields (NEW)**
   - Create or update DataRaptor to update `IndividualApplication` (Case Manager)
   - Input from OmniScript:
     - `RadioConciergeMedicine` (Yes/No) → `PRM_ConciergeMedicineIndicator__c` (Boolean)
     - `RadioConciergeFeeOptional` (Yes/No) → `PRM_ConciergeFeeOptional__c` (Boolean)
     - `CaseManagerId` (WHERE clause for update)
   - Transformation: Convert "Yes"/"No" string to true/false boolean
   - Output: Updated IndividualApplication record

6. **Lookup HealthcarePractitionerFacility Records (NEW)**
   - For each selected practice location ID:
     - Look up `HealthcarePractitionerFacility` record WHERE:
       - `PractitionerID = Practitioner Account Id` AND
       - `FacilityID = Selected Location Id`
     - Use Extract DataRaptor or SOQL
     - Error handling: If junction record doesn't exist, log error and skip this location (alert admin)

7. **Lookup Info Code by Name**
   - IP or DataRaptor looks up `PRM_InfoCode__c` WHERE `Name = 'Concierge Provider'`
   - Use Extract DataRaptor or SOQL
   - Error handling: If Info Code does not exist, log error and alert admin

8. **Pending and Case Manager Linkage**
   - If PAR form uses case workflow:
     - Set `PRM_Pending__c = true` on each Info Code Assignment **UPDATED**
     - Link `PRM_CaseManager__c` to IndividualApplication Id on each Info Code Assignment **UPDATED**
   - When case is approved: All assignments updated with `PRM_Pending__c` → false (existing logic)
   - When case is denied: All assignments updated with `PRM_Pending__c` → false (existing logic)
   - Note: Case Manager fields (`PRM_ConciergeMedicineIndicator__c`, `PRM_ConciergeFeeOptional__c`) are NOT affected by case approval/denial

#### Technical Considerations

- **Integration Procedure:** `PRM_CreatePARCaseAndRecords` (or similar)
- **DataRaptor 1:** Create `PRMDRInsertConciergeInfoCodeAssignment` (inserts Info Code Assignment) - called in loop **UPDATED**
- **DataRaptor 2:** Create `PRMDRUpdateCaseManagerConciergeFields` (updates IndividualApplication)
- **DataRaptor 3:** Create `PRMDRExtractHealthcarePractitionerFacility` (looks up junction records by practitioner + location) **NEW**
- **Info Code Lookup:** Extract DataRaptor with Input: `InfoCodeName = 'Concierge Provider'`
- **Loop Logic:** Integration Procedure uses "Loop Block" or "Action" with iteration over `%CheckboxConciergePracticeLocations%` array **NEW**
- **Conditional Execution:** Decision element checks `%RadioConciergeMedicine%` for Info Code Assignment creation
- **Case Manager Update:** Always execute (not conditional)
- **String to Boolean Conversion:** Use formula or transformation: `IF(%RadioConciergeMedicine% == 'Yes', true, false)`
- **Performance:** If practitioner selects 10+ locations, consider batch processing or async job **NEW**

#### Dependencies

- Stories 2.2 and 2.3 completed (concierge questions exist with practice location selection) **UPDATED**
- Story 1.2 completed ("Concierge Provider" Info Code exists)
- Story 1.6 completed (Case Manager fields exist)
- Story 2.4A completed (Case Manager fields exist)
- HealthcarePractitionerFacility records exist for practitioner-location relationships
- Access to Integration Procedure and DataRaptor designer

#### Definition of Done

- [ ] Integration Procedure updated with three steps (Case Manager update + Loop through locations + Create assignments) **UPDATED**
- [ ] DataRaptor created/updated for Info Code Assignment (called in loop) **UPDATED**
- [ ] DataRaptor created/updated for Case Manager fields
- [ ] DataRaptor created for HealthcarePractitionerFacility lookup **NEW**
- [ ] Loop logic implemented to iterate through selected locations **NEW**
- [ ] Info Code lookup by name works
- [ ] Conditional logic tested (Yes with locations selected creates assignments, No doesn't)
- [ ] Case Manager fields always populated (Yes and No scenarios)
- [ ] String to boolean conversion works correctly
- [ ] Pending and Case Manager linkage fields populated correctly on all assignments **UPDATED**
- [ ] Error handling tested (missing junction record, Info Code not found, etc.)
- [ ] Unit tests pass
- [ ] Integration test: Submit form with Yes + 1 location → 1 assignment created at Practitioner Practice Location level **NEW**
- [ ] Integration test: Submit form with Yes + 3 locations → 3 assignments created (one per location) **NEW**
- [ ] Integration test: Submit form with Yes + all locations → all assignments created **NEW**
- [ ] Integration test: Submit form with No → no assignments created BUT Case Manager fields updated
- [ ] Integration test: Case approval updates all assignments from pending to active **NEW**
- [ ] Performance test: 10+ locations selected (acceptable performance) **NEW**
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT sign-off

---

## Epic 3: Internal Analytics Integration

**Epic Goal:** Configure DART and Inquire Only systems to receive and display Concierge PCP Info Code Assignment data for internal analytics and reporting.

**Business Value:** Enable data-driven insights into concierge medicine providers for internal use; support customer service inquiries.

**Priority:** P0 - Critical
**Estimated Story Points:** 13

---

### Story 3.1: Configure DART Integration to Read Concierge PCP Info Code Assignments

**As a** Data Analytics Team Member
**I want** DART to receive Concierge PCP Info Code Assignment data from PIE
**So that** I can analyze concierge provider trends and create executive reports

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / DART

#### Acceptance Criteria

1. **Data Feed Configuration**
   - PIE-to-DART ETL feed includes `PRM_InfoCodeAssignment__c` WHERE `PRM_InfoCode__r.Name = 'Concierge PCP'`
   - Feed includes: Account (Practitioner), HealthcareFacility (Practice Location), Effective Date, Termination Date, Pending status
   - Feed includes both practitioner-level and practice-level assignments
   - Feed configuration is documented

2. **Data Mapping**
   - Source fields correctly mapped to DART target fields:
     - `PRM_Account__c` → Practitioner ID
     - `PRM_HealthcareFacility__c` → Practice Location ID
     - `PRM_EffectiveDate__c` → Effective Date
     - `PRM_TerminationDate__c` → Termination Date
     - Derived: "Currently Active" = (Termination Date IS NULL OR > TODAY)
   - Field mapping document created

3. **Feed Schedule and Reliability**
   - Data refresh frequency defined (e.g., daily)
   - Initial full load successfully transfers all existing assignments
   - Incremental updates capture changes within expected timeframe
   - Error handling and retry logic in place
   - Feed failures trigger alerts

4. **Data Validation in DART**
   - Sample of 10+ records verified after feed
   - Assignment values match PIE source data
   - Date values match (format preserved)
   - DART can filter/group by concierge status
   - DART can calculate "currently active concierge" providers

5. **Exclusion from Provider Directory**
   - Verify "Concierge PCP" assignments do NOT feed to Provider Directory
   - Test scenarios confirm no leakage to public systems

#### Technical Considerations

- ETL Pipeline: Update PIE-to-DART pipeline
- Query: `SELECT Id, PRM_Account__c, PRM_HealthcareFacility__c, PRM_EffectiveDate__c, PRM_TerminationDate__c FROM PRM_InfoCodeAssignment__c WHERE PRM_InfoCode__r.Name = 'Concierge PCP'`
- Monitoring: Set up alerting for feed failures

#### Dependencies

- Story 1.1 completed ("Concierge PCP" Info Code exists)
- Stories 1.3 and 1.4 completed (Assignments can be created)
- DART target schema updated
- DART team coordination

#### Definition of Done

- [ ] PIE-to-DART feed configuration updated
- [ ] Field mapping documented and approved
- [ ] Initial full load completed
- [ ] Incremental update tested
- [ ] Data validation completed
- [ ] Exclusion from Provider Directory verified
- [ ] Monitoring configured
- [ ] DART team sign-off
- [ ] Technical documentation updated

---

### Story 3.2: Configure "Inquire Only" System Integration

**As a** Customer Service Representative
**I want** to view Concierge PCP Info Code Assignments in "Inquire Only"
**So that** I can provide accurate information about provider concierge status

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - Data Integration / Inquire Only

#### Acceptance Criteria

1. **Data Feed Configuration**
   - PIE-to-Inquire Only feed includes `PRM_InfoCodeAssignment__c` WHERE `PRM_InfoCode__r.Name = 'Concierge PCP'`
   - Feed includes: Account, HealthcareFacility, Effective Date, Termination Date
   - Feed configuration is documented

2. **User Interface Display**
   - Assignments visible in provider detail view
   - Fields clearly labeled: "Concierge PCP", "Effective Date", "Termination Date"
   - Dates formatted consistently (MM/DD/YYYY)
   - Visual indicator shows current status (Active if no termination date or > today)
   - Data is read-only

3. **Search and Filter Capability**
   - Users can search for providers with "Concierge PCP" assignment
   - Users can filter by date ranges
   - Search results display concierge status clearly
   - Search performance is acceptable (< 3 seconds)

4. **Data Synchronization**
   - Refresh frequency defined and documented
   - Data matches PIE source within acceptable lag time
   - Updates appear within expected timeframe
   - Error handling in place

5. **Exclusion from Provider Directory**
   - Verify no leakage to public systems

#### Technical Considerations

- Integration: Update PIE-to-Inquire Only integration
- UI: Update Inquire Only UI to display assignments
- Performance: Optimize search/filter queries
- Documentation: Update user guide

#### Dependencies

- Story 1.1 completed
- Stories 1.3 and 1.4 completed
- Inquire Only system access
- UI mockups approved

#### Definition of Done

- [ ] Feed configuration updated
- [ ] UI changes implemented and tested
- [ ] Search and filter tested
- [ ] Data synchronization verified
- [ ] Performance testing completed
- [ ] Exclusion from Provider Directory verified
- [ ] UAT completed by CSR team
- [ ] User guide updated
- [ ] Technical documentation updated

---

### Story 3.3: Create Internal Reporting Dashboard for Concierge PCP Analytics

**As a** Healthcare Analytics Manager
**I want** a dedicated reporting dashboard showing Concierge PCP trends
**So that** I can monitor concierge medicine growth and make data-driven decisions

**Priority:** P2 - Medium
**Story Points:** 3
**Component:** DART - Reporting

#### Acceptance Criteria

1. **Dashboard Metrics**
   - Total count of active Concierge PCPs (currently active)
   - Total count of historical Concierge PCPs (all time)
   - Total count of concierge practice locations
   - Trend over time (new by month/quarter)
   - Terminations over time (stopped by month/quarter)
   - Average duration of concierge practice

2. **Filtering and Segmentation**
   - Filter by date range
   - Filter by assignment level (practitioner vs practice)
   - Filter by geographic region (if available)
   - Filter by specialty (if available)

3. **Visualizations**
   - Line chart: Concierge PCP count trend
   - Bar chart: New Concierge PCPs by month
   - Pie chart: Active vs inactive
   - Table: List with key details

4. **Export and Sharing**
   - Export to PDF
   - Export to Excel
   - Scheduled email delivery
   - Shareable link

#### Technical Considerations

- Platform: DART's native reporting tool
- Data Source: From Story 3.1
- Performance: < 5 seconds load time
- Security: Internal users only

#### Dependencies

- Story 3.1 completed (DART integration with data)
- DART reporting platform access

#### Definition of Done

- [ ] Dashboard created
- [ ] All metrics implemented
- [ ] Filters working
- [ ] Export functionality tested
- [ ] Performance testing completed
- [ ] Security/access controls verified
- [ ] UAT completed by Analytics team
- [ ] Dashboard documented

---

## Epic 4: Public Provider Directory Integration

**Epic Goal:** Configure Provider Directory to receive and display Concierge Provider Info Code Assignment data for public consumption.

**Business Value:** Enable patients to identify concierge providers in Provider Directory; improve public-facing provider information.

**Priority:** P0 - Critical
**Estimated Story Points:** 16

---

### Story 4.1: Configure Provider Directory Feed

**As an** Integration Engineer
**I want** Concierge Provider Info Code Assignments to feed to Provider Directory
**So that** patients can identify concierge providers when searching

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / Provider Directory

#### Acceptance Criteria

1. **Feed Configuration**
   - PIE-to-Provider Directory feed includes `PRM_InfoCodeAssignment__c` WHERE `PRM_InfoCode__r.Name = 'Concierge Provider'`
   - Feed includes: Account, HealthcareFacility, assignment status (active/inactive)
   - Field mapping is correct
   - Feed configuration is documented

2. **Data Synchronization**
   - Initial full load transfers all existing "Concierge Provider" assignments
   - Incremental updates capture changes within expected timeframe (e.g., 24 hours)
   - Test: Create assignment in PIE → verify appears in Provider Directory
   - Test: Terminate assignment in PIE → verify removed from Provider Directory
   - Verify 10+ sample records match PIE source

3. **Provider Directory Display**
   - Assignment appears in search results (if applicable)
   - Assignment appears on provider detail page
   - Labeled for consumer audience (e.g., "Concierge Medicine")
   - Visual design consistent with Provider Directory standards

4. **Feed Reliability**
   - Error handling and retry logic
   - Feed failures trigger alerts
   - Monitoring dashboard shows health metrics
   - Feed SLA defined

5. **Testing in Test Environment**
   - Feed tested end-to-end in Test
   - Test scenarios: new, update, terminate assignment
   - All scenarios pass

6. **Exclusion from DART / Inquire Only**
   - Verify "Concierge Provider" does NOT feed to DART/Inquire Only (unless business requires both)

#### Technical Considerations

- ETL Pipeline: Update PIE-to-Provider Directory pipeline
- Query: `SELECT ... WHERE PRM_InfoCode__r.Name = 'Concierge Provider' AND (PRM_TerminationDate__c IS NULL OR > TODAY)`
- Consumer UX: Label appropriate for patient audience

#### Dependencies

- Story 1.2 completed ("Concierge Provider" Info Code exists)
- Stories 1.3 and 1.4 completed (Assignments can be created)
- Story 2.5 completed (PAR form creates assignments)
- Provider Directory target field/table created
- Provider Directory team coordination

#### Definition of Done

- [ ] Feed configuration updated in Test
- [ ] Data mapping documented
- [ ] Initial full load completed in Test
- [ ] Incremental updates tested
- [ ] End-to-end scenarios pass
- [ ] Provider Directory display verified in Test
- [ ] Exclusion from DART/Inquire Only verified
- [ ] Monitoring configured
- [ ] Provider Directory team sign-off
- [ ] Ready for Production deployment

---

### Story 4.2: Design Provider Directory Display for Concierge Indicator

**As a** UX Designer
**I want** to design how concierge providers are displayed in Provider Directory
**So that** patients can easily identify concierge practitioners

**Priority:** P1 - High
**Story Points:** 3
**Component:** Provider Directory - UX Design

#### Acceptance Criteria

1. **Design Requirements**
   - Conduct workshop with Provider Directory team
   - Review existing provider attribute displays
   - Identify best placement for concierge indicator

2. **Design Options**
   - Create 2-3 design options for concierge indicator
   - Options: badge, icon, text label, or combination
   - Mockups for search results and detail page
   - Mobile-responsive designs

3. **User Feedback**
   - Present designs to stakeholders
   - Conduct usability testing with 5+ users (internal)
   - Document feedback
   - Select final design

4. **Design Specifications**
   - Detailed design specs (wireframes/mockups)
   - Exact placement (search results, detail page)
   - Visual elements (badge color, icon, text)
   - Accessibility standards (WCAG 2.1 AA)

#### Technical Considerations

- Provider Directory design system
- Accessibility requirements
- Responsive design (desktop, tablet, mobile)

#### Dependencies

- Story 4.1 in progress (feed configuration)
- Provider Directory team availability

#### Definition of Done

- [ ] User research completed
- [ ] Design options created
- [ ] Usability testing completed
- [ ] Final design selected
- [ ] Design specifications created
- [ ] Design review completed
- [ ] Accessibility review completed
- [ ] Stakeholder sign-off

---

### Story 4.3: Implement Concierge Indicator in Provider Directory UI

**As a** Provider Directory Developer
**I want** to implement the concierge indicator in Provider Directory
**So that** patients see which providers practice concierge medicine

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** Provider Directory - Frontend

#### Acceptance Criteria

1. **Search Results Display**
   - Concierge indicator appears in search results for providers with active assignment
   - Indicator matches approved design
   - Indicator does not appear for providers without assignment
   - Responsive design works on all devices

2. **Detail Page Display**
   - Concierge indicator appears on provider detail page
   - Indicator is prominent and easy to identify
   - Additional details shown (e.g., "This provider practices concierge medicine")
   - Consistent with search results display

3. **Filter Capability (Optional)**
   - Provider Directory search allows filtering by concierge status
   - Filter checkbox: "Concierge Medicine" or similar
   - Filter correctly returns only providers with active assignments

4. **Performance**
   - Search results load within acceptable time (< 3 seconds)
   - Detail page loads within acceptable time (< 2 seconds)
   - No performance degradation

5. **Accessibility**
   - Keyboard navigation works
   - Screen reader announces concierge status
   - Color contrast meets WCAG standards
   - Focus indicators visible

#### Technical Considerations

- Frontend Framework: Use existing Provider Directory framework
- Data Source: Query from feed (Story 4.1)
- Caching: Consider caching strategy
- Testing: Unit tests, integration tests, accessibility tests

#### Dependencies

- Story 4.1 completed (feed providing data)
- Story 4.2 completed (design approved)
- Provider Directory development environment

#### Definition of Done

- [ ] UI implemented per design
- [ ] Search results display working
- [ ] Detail page display working
- [ ] Filter working (if included)
- [ ] Performance testing completed
- [ ] Accessibility testing completed
- [ ] Cross-browser testing completed
- [ ] Mobile/responsive testing completed
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT completed

---

### Story 4.4: Deploy to Production and Update Provider Directory

**As a** Release Manager
**I want** to deploy all Concierge Provider changes to Production
**So that** the public-facing directory shows accurate concierge information

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** Production Deployment

#### Acceptance Criteria

1. **Pre-Deployment Checklist**
   - All Test environment testing completed
   - UAT sign-off received (PDA team, Provider Directory team)
   - Deployment plan reviewed and approved
   - Rollback plan documented
   - Communication plan executed (stakeholders notified)

2. **Deployment Execution**
   - Info Codes deployed
   - PAR form changes deployed
   - Feed configuration deployed
   - Provider Directory UI deployed
   - Deployment completes within maintenance window

3. **Post-Deployment Verification**
   - Smoke testing in Production
   - PDA team can create assignments
   - Sample assignments verified in Provider Directory
   - No errors in logs
   - Monitoring shows green status

4. **Post-Deployment Communication**
   - Success notification sent
   - Release notes published
   - User documentation published
   - Training reminder sent

#### Technical Considerations

- Maintenance window during low-usage period
- Rollback plan ready
- Enhanced monitoring during deployment
- Support team ready

#### Dependencies

- All prior stories completed
- Change control approval
- Deployment window scheduled
- Stakeholder communication completed

#### Definition of Done

- [ ] Pre-deployment checklist completed
- [ ] Production deployment successful
- [ ] Post-deployment smoke testing passed
- [ ] PDA team verified in Production
- [ ] Provider Directory feed verified
- [ ] Monitoring confirms health
- [ ] Post-deployment communication sent
- [ ] Release notes published
- [ ] Deployment retrospective completed

---

## Epic 5: UX Enhancements & Data Quality

**Epic Goal:** Improve user experience for managing concierge assignments and implement data quality rules to ensure data integrity.

**Business Value:** Simplified workflow for PDA team; proactive data quality management.

**Priority:** P1 - High
**Estimated Story Points:** 13

---

### Story 5.1: Create Quick Action for Managing Concierge Status

**As a** Provider Data Administrator
**I want** a quick action button for managing concierge status
**So that** I can quickly add/remove concierge status without navigating through multiple screens

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - UX Enhancement

#### Acceptance Criteria

1. **Quick Action Button**
   - "Manage Concierge Status" button on Practitioner and Practice Location pages
   - Button opens modal/component for inline editing
   - User can select Info Code type ("Concierge PCP" or "Concierge Provider")
   - User can toggle status on/off (creates or terminates assignment)
   - Changes save immediately with confirmation

2. **Inline Editing Component**
   - Lightning component shows current concierge status
   - Displays: "Concierge Provider: Yes" or "No"
   - Click to edit toggles status
   - Visual indicator (badge/icon) shows status at a glance

3. **Effective/Termination Dates**
   - When creating new assignment, user enters Effective Date
   - When terminating existing assignment, user enters Termination Date
   - Date fields use date picker
   - Validation prevents invalid dates

4. **User Experience**
   - All actions complete within 3 clicks
   - Success/error messages display clearly
   - Help text explains concierge provider definition
   - Consistent with other quick actions

#### Technical Considerations

- Lightning Web Component or Aura
- Apex controller for creating/terminating assignments
- UI/UX design review

#### Dependencies

- Stories 1.1-1.4 completed (Info Codes and assignments exist)
- Lightning component development resources

#### Definition of Done

- [ ] Quick action implemented
- [ ] Inline editing component deployed
- [ ] Date validation working
- [ ] User experience validated by PDA team
- [ ] Performance testing completed (< 2 seconds)
- [ ] UAT completed
- [ ] User guide updated

---

### Story 5.2: Implement Data Quality Rules for Info Code Assignments

**As a** Data Governance Lead
**I want** automated data quality rules and alerts for Concierge Info Code Assignments
**So that** I can ensure data integrity and prevent invalid data states

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - Data Quality

#### Acceptance Criteria

1. **Validation Rules Implemented**
   - Rule: Termination date cannot be before effective date (error)
   - Rule: Dates cannot be in the future (error)
   - Rule: No duplicate active assignments (same Info Code + Account/Facility) (error)
   - Rule: If termination date exists, effective date should be present (warning)

2. **Automated Data Quality Checks**
   - Daily batch job scans for violations
   - Report generated listing violations
   - Report sent to PDA team via email
   - Dashboard showing data quality metrics

3. **User Alerts**
   - Real-time validation errors prevent saving invalid data (hard stops)
   - Real-time validation warnings allow saving but notify user (soft stops)
   - Clear, actionable error/warning messages
   - Inline help explains how to resolve violations

4. **Remediation Workflow**
   - PDA team can view list of violations
   - PDA team can edit assignments to fix issues
   - Audit trail tracks when violations resolved
   - Metrics show trend of improvement

#### Technical Considerations

- Validation Engine: Leverage existing PIE validation framework or Apex triggers
- Batch Processing: Schedule daily job during off-peak hours
- Notification: Use existing email system
- Dashboard: Embed in existing DQ dashboard

#### Dependencies

- Stories 1.1-1.4 completed
- Access to PIE validation framework
- Email notification system available

#### Definition of Done

- [ ] All validation rules implemented
- [ ] Daily batch job scheduled and running
- [ ] DQ report generated and distributed
- [ ] Real-time validation working
- [ ] DQ dashboard created
- [ ] Remediation workflow tested
- [ ] Documentation updated
- [ ] PDA team trained

---

### Story 5.3: Develop Consistency Check (Practice vs Practitioner Level)

**As a** Data Quality Analyst
**I want** a consistency check that warns when practice-level assignments don't match practitioner-level assignments
**So that** data quality issues can be identified proactively

**Priority:** P2 - Medium
**Story Points:** 3
**Component:** PIE - Data Quality

#### Acceptance Criteria

1. **Consistency Check Logic**
   - Weekly batch job checks practice locations with "Concierge" assignment
   - For each practice location, query all practitioners at that location (via HealthcarePractitionerFacility)
   - Check if all practitioners have matching concierge assignment
   - If mismatch found, add to report

2. **Report Generation**
   - Report lists practice locations with mismatches
   - For each location, shows:
     - Practice Location name
     - Concierge assignment at practice level (Yes/No)
     - List of practitioners and their concierge status
     - Practitioners without matching status highlighted
   - Report sent to PDA team via email

3. **Dashboard View**
   - Dashboard shows:
     - Count of practice locations with mismatches
     - List of mismatches (sortable/filterable)
     - Trend over time (are mismatches increasing/decreasing)

4. **Manual Review Process**
   - PDA team reviews report
   - PDA team decides action: update practice-level or practitioner-level assignments
   - Audit trail tracks resolution

#### Technical Considerations

- Batch Job: Scheduled weekly
- Query: Join HealthcarePractitionerFacility to get practitioners per location
- Performance: Optimize for large data volumes

#### Dependencies

- Stories 1.1-1.4 completed
- HealthcarePractitionerFacility data is accurate

#### Definition of Done

- [ ] Batch job implemented
- [ ] Report generated correctly
- [ ] Dashboard created
- [ ] Email notification working
- [ ] Manual review process documented
- [ ] PDA team trained
- [ ] Performance testing completed

---

## Epic 6: Recredentialing PSV Guided Flow

**Epic Goal:** Add concierge medicine questions to the Recredentialing PSV Guided Flow and the Practice Location address screen, capture practitioner responses on the Case Manager (IndividualApplication) object, and automatically create or terminate Info Code Assignments at the Practitioner Practice Location level during recredentialing cycles.

**Business Value:** Capture updated concierge medicine information during recredentialing at both the practitioner and per-location level; maintain historical record of practitioner responses over time; enable compliance tracking for concierge attestations; ensure Practitioner Practice Location-level Info Code Assignments reflect the most recent recred attestation.

**Priority:** P0 - Critical  
**Estimated Story Points:** 19 (12 from v4.2 + 7 from v4.3: Story 6.2 +2, Story 6.3 +5)

---

### Story 6.1: Create Case Manager Fields for Recredentialing Concierge Responses

**As a** System Administrator  
**I want** four checkbox fields on the Case Manager (IndividualApplication) object to capture recredentialing concierge responses  
**So that** we preserve the practitioner's recredentialing answers for audit, reporting, and compliance purposes  

**Priority:** P0 - Critical  
**Story Points:** 3  
**Component:** PIE - Schema / Field Creation  

#### Acceptance Criteria

1. **Field Creation - Concierge Service Offered Prior to Date**
   - Create field: `PRM_ConciergeOfferedPriorToDate__c` (Checkbox)
   - Object: IndividualApplication (Case Manager)
   - Field Label: "Concierge Service Offered Prior to 01/01/2025"
   - Help Text: "Indicates whether the practitioner offered concierge services prior to January 1, 2025 (answered during recredentialing)"
   - Default Value: false

2. **Field Creation - Concierge Fee Optional for Existing Patients**
   - Create field: `PRM_ConciergeFeeOptionalExisting__c` (Checkbox)
   - Object: IndividualApplication (Case Manager)
   - Field Label: "Concierge Fee Optional for Existing Patients"
   - Help Text: "Indicates whether the practitioner's concierge fee is optional for existing patients (answered during recredentialing)"
   - Default Value: false

3. **Field Creation - Accepts New Patients Without Concierge Fee**
   - Create field: `PRM_AcceptsNewPatientsNonConcierge__c` (Checkbox)
   - Object: IndividualApplication (Case Manager)
   - Field Label: "Accepts New Patients Without Concierge Fee"
   - Help Text: "Indicates whether the practitioner accepts new patients who are not enrolled in concierge services and not paying the concierge fee (answered during recredentialing)"
   - Default Value: false

4. **Field Visibility on Page Layout**
   - Add all three fields to Case Manager page layout
   - Place in "Recredentialing Details" or "Provider Information" section
   - Group with existing concierge fields: `PRM_ConciergeMedicineIndicator__c` and `PRM_ConciergeFeeOptional__c`

5. **Field Access, Permission Sets, and Metadata Notification**
   - **Given** the new fields have been created in Salesforce,
   - **When** the Admin configures user access and deployment documentation,
   - **Then** the access levels shall be explicitly mapped as follows:

| Permission Set / Profile | Access Level |
|-------------------------|--------------|
| **Credentialing** | Read Access |
| **PDA** | Read Access |
| **Network Management QC Permission Set** | Read Access |
| **PRM CredentialingUser** | Edit Access |
| **PRM ProviderDataAdmin** | Edit Access |
| **PRM-NetworkManagement@C** | Edit Access |
| **PRM DataViewAll** | View All, Read |
| **PAM-DataModifyAll** | Read, Create, Edit, View All |

   - **And** the Admin shall explicitly **NOTIFY KISHLAY + ANSHAY** to add the fields for SF to DART Metadata & Data Dictionary:
     - `PRM_ConciergeOfferedPriorToDate__c`
     - `PRM_ConciergeFeeOptionalExisting__c`
     - `PRM_AcceptsNewPatientsNonConcierge__c`

#### Technical Considerations

- **Object:** IndividualApplication
- **Field Type:** Checkbox (Boolean)
- **Reporting:** Enable tracking of concierge status changes during recredentialing cycles
- **Historical Tracking:** Case Manager records preserve historical responses

#### Dependencies

- Access to IndividualApplication object schema
- Page layout edit access
- Permission set configuration access

#### Definition of Done

- [ ] `PRM_ConciergeOfferedPriorToDate__c` field created on IndividualApplication
- [ ] `PRM_ConciergeFeeOptionalExisting__c` field created on IndividualApplication
- [ ] `PRM_AcceptsNewPatientsNonConcierge__c` field created on IndividualApplication
- [ ] Fields added to page layout
- [ ] Permission sets updated per acceptance criteria
- [ ] **KISHLAY + ANSHAY notified** to add fields to DART Metadata
- [ ] DART team confirmation received
- [ ] Fields deployed to all environments
- [ ] Documentation updated

---

### Story 6.2: Add Concierge Questions to Recredentialing PSV Guided Flow

**As a** Practitioner completing recredentialing via PSV Guided Flow  
**I want** to answer concierge medicine questions specific to recredentialing  
**So that** the credentialing team has updated information about my concierge practice model  

**Priority:** P0 - Critical  
**Story Points:** 11 (9 original + 2 for practitioner-level Info Code Assignment creation — v4.3 update)  
**Component:** PSV Guided Flow - Recredentialing  

#### Acceptance Criteria

1. **Question Display Logic**
   - Questions displayed ONLY when `Practitioner Role = PCP` OR `Practitioner Role = Dual`
   - Questions are required (cannot proceed without answering)

2. **Question 1 - Concierge Medicine (Required)**
   ```
   *(For PCPs only) Do you practice concierge medicine (or retainer medicine) by charging your 
   patients a concierge fee (or retainer) separate from the applicable patient cost-sharing 
   (e.g., co-pays, deductibles, etc.)?
   
   ○ Yes
   ○ No
   ```

3. **Question 2 - Offered Prior to Date (Conditional)**
   - Only displayed if Question 1 = "Yes"
   ```
   *Did you offer concierge services to your patients prior to January 1, 2025?
   
   ○ Yes
   ○ No
   ```

4. **Question 3 - Fee Optional for Existing (Conditional)**
   - Only displayed if Question 1 = "Yes"
   ```
   *Is your concierge fee for additional services optional for your existing patients?
   
   ○ Yes
   ○ No
   ```

5. **Question 4 - Accepts New Non-Concierge (Conditional)**
   - Only displayed if Question 1 = "Yes"
   ```
   *Will you accept new patients who are not enrolled in concierge services and are not paying 
   the concierge fee?
   
   ○ Yes
   ○ No
   ```

6. **Warning Message with Hyperlinks**
   ```
   ⚠️ Please ensure that you review and execute the concierge attestation form during your 
   credentialing and re-credentialing process. Concierge Policy Guidelines/Criteria and 
   Provider Attestation can be found within the Provider Manual located:
   [IBX] | [AHNJ] | [AHPA]
   
   Noncompliance with executing the concierge attestation may result in the delay or 
   rejection of your application.
   ```
   - IBX → https://provcomm.ibx.com/pnc-ibc/Pages/Provider-Manual.aspx
   - AHNJ → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_NJ.aspx
   - AHPA → https://provcomm.amerihealth.com/pnc-ah/Pages/Provider-Manual_PA.aspx

7. **Response Capture to Case Manager**
   - When PSV submitted with Question 1 = "Yes":
     - `PRM_ConciergeMedicineIndicator__c` = true
     - `PRM_ConciergeOfferedPriorToDate__c` = true/false (from Question 2)
     - `PRM_ConciergeFeeOptionalExisting__c` = true/false (from Question 3)
     - `PRM_AcceptsNewPatientsNonConcierge__c` = true/false (from Question 4)
   - When PSV submitted with Question 1 = "No":
     - `PRM_ConciergeMedicineIndicator__c` = false
     - Other fields = false or null

8. **Practitioner-Level Info Code Assignment Creation on "Yes" (NEW — v4.3)**
   - When the PSV is submitted with Question 1 = "Yes" AND all required conditional questions (Q2–Q4) are answered:
     - Query for an existing active `PRM_InfoCodeAssignment__c` where:
       - `PRM_Account__c` = current Practitioner Account Id
       - `PRM_InfoCode__c` = "Concierge PCP" Info Code
       - `PRM_TerminationDate__c` = null (no termination date = still active)
     - **If no active assignment exists:** Create a new `PRM_InfoCodeAssignment__c` record:
       - `PRM_InfoCode__c` = "Concierge PCP" Info Code Id
       - `PRM_Account__c` = Practitioner Account Id
       - `PRM_HealthcareFacility__c` = null
       - `PRM_PractitionerFacilityAssignment__c` = null
       - `PRM_EffectiveDate__c` = today's date
     - **If an active assignment already exists:** Do not create a duplicate; log/skip silently
   - When the PSV is submitted with Question 1 = "No":
     - Do NOT create any Info Code Assignment
     - Do NOT terminate any existing assignment (termination logic, if required, is a separate scoped decision — see Clarification Questions)

9. **Validation Rules**
   - Question 1 is required for PCP/Dual
   - Questions 2-4 are required when Question 1 = "Yes"
   - Error: "Please answer all concierge-related questions before proceeding."

#### Technical Considerations

- **PSV Guided Flow:** Screen Flow or LWC component
- **Element Names:** `RadioConciergeMedicineRecred`, `RadioConciergeOfferedPrior`, `RadioConciergeFeeOptionalExisting`, `RadioAcceptsNewPatientsNonConcierge`
- **Conditional Visibility:** Questions 2-4 visible when Question 1 = "Yes"
- **Data Mapping:** Flow or Apex updates IndividualApplication fields
- **Info Code Assignment Logic (NEW — v4.3):**
  - Pre-check: `PRMDRFetchConciergeAssignmentAtPractitioner` (DataRaptor Extract) — queries `PRM_InfoCodeAssignment__c` by `PRM_Account__c` and null `PRM_TerminationDate__c`; returns `HasActiveAssignment` (Boolean) and `AssignmentId`
  - On submit (Q1 = Yes): Integration Procedure `PRM_RecredCreateConciergeAtPractitionerParent` → `PRM_RecredCreateConciergeAtPractitioner` — conditionally creates assignment only if `HasActiveAssignment = false`
  - Practitioner Account Id must be in scope in the PSV Guided Flow at submission time

| DR/IP Name | Type | Input | Output | Notes |
|-----------|------|-------|--------|-------|
| `PRMDRFetchConciergeAssignmentAtPractitioner` | DataRaptor Extract (NEW) | `PractitionerAccountId`, `ConciergeInfoCodeId` | `HasActiveAssignment` (Boolean), `AssignmentId` | Query WHERE `PRM_Account__c = :acctId` AND `PRM_TerminationDate__c = null` AND `PRM_InfoCode__c = :infoCodeId` |
| `PRM_RecredCreateConciergeAtPractitioner` | Integration Procedure (NEW) | `PractitionerAccountId`, `ConciergeInfoCodeId`, `HasActiveAssignment`, `TodayDate` | `success`, `errorMessage` | Creates `PRM_InfoCodeAssignment__c` only when `HasActiveAssignment = false` |

#### Dependencies

- Story 1.1 completed ("Concierge PCP" Info Code exists)
- Story 1.3 completed (`PRM_InfoCodeAssignment__c` supports `PRM_Account__c` practitioner-level creation)
- Story 1.7 completed (boolean checkbox trigger fires on new programmatic assignments)
- Story 6.1 completed (Case Manager fields exist)
- Access to Recredentialing PSV Guided Flow
- Practitioner Account Id in scope at PSV submission time
- Case Manager record available at submission time

#### Definition of Done

- [ ] All 4 questions added to PSV Guided Flow
- [ ] Conditional display logic works
- [ ] Validation rules work
- [ ] Case Manager field mapping implemented
- [ ] Responses saved correctly
- [ ] Hyperlinks work correctly
- [ ] **`PRMDRFetchConciergeAssignmentAtPractitioner` DataRaptor Extract created and tested (NEW)**
- [ ] **`PRM_RecredCreateConciergeAtPractitioner` Integration Procedure created and tested (NEW)**
- [ ] **Q1 = "Yes" with no existing assignment → new `PRM_InfoCodeAssignment__c` created at practitioner level (NEW)**
- [ ] **Q1 = "Yes" with existing active assignment → no duplicate created (NEW)**
- [ ] **Q1 = "No" → no assignment created (NEW)**
- [ ] Story 1.7 trigger correctly updates `PRM_IsConciergeProvider__c` on practitioner Account after IP-created assignment (NEW)
- [ ] Accessibility tested
- [ ] Integration tests pass
- [ ] UAT sign-off by Credentialing team
- [ ] Deployed to Production

---

### Story 6.3: Add Per-Location Concierge Question to Recred PSV Address Screen

**Persona:** Credentialing Specialist, Developer
**Priority:** P0 - Critical
**OmniScript:** `PRM_PractitionerParticipationAddressForm_English`, `PRM_ReCredUpdate_English`
**Integration Procedures:** TBD — IP to create/terminate `PRM_InfoCodeAssignment__c` at Practitioner Practice Location level
**Relevant Requirements:** Concierge_Medicine_Complete_User_Stories.md v4.3; Epic 1 (Story 1.3); Epic 6 (Stories 6.1, 6.2)

---

## Story

**As a** Credentialing Specialist processing a practitioner's recredentialing PSV,
**I want** the address screen for Primary/Practice Address to display a required radio question asking whether the practitioner practices concierge medicine at that specific location,
**So that** concierge status is captured at the individual practice location level during recredentialing and Info Code Assignments are automatically created or terminated accordingly.

**Why it matters:** The existing Story 6.2 captures a practitioner-level concierge answer; however, practitioners can practice concierge medicine at some locations but not others. This story closes that gap by collecting a per-location response at the exact moment a location is added or reviewed during recred, ensuring Practitioner Practice Location-level Info Code Assignments remain accurate and up-to-date after each recredentialing cycle.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Recredentialing PSV | `PRM_PractitionerParticipationAddressForm_English` | Primary/Practice Address screen | `HealthcarePractitionerFacility` (current HPF record); `PRM_InfoCodeAssignment__c` (existing assignments) |
| Recredentialing PSV | `PRM_ReCredUpdate_English` | Address Step / Add Location Step | Delegates to `PRM_PractitionerParticipationAddressForm_English` sub-OS |

---

## Current State (from codebase)

### PRM_PractitionerParticipationAddressForm_English (v54)

- **AddressComparisonLWC** (Custom Lightning Web Component): Renders standardized vs. entered address comparison; does not currently include any concierge question.
- **Location:** `force-app/main/default/omniScripts/PRM_PractitionerParticipationAddressForm_English_54.os-meta.xml`
- **Note:** This OmniScript is embeddable (`isOmniScriptEmbeddable: true`) and is invoked from the parent recred flow when a location is added or edited.

### PRM_ReCredUpdate_English (v7)

- **Practice Location Step** (lines ~389–857): Captures `Practice Location City`, `Practice Location County`, `Practice Location State` fields; delegates address entry to `PRM_PractitionerParticipationAddressForm_English`.
- **Location:** `force-app/main/default/omniScripts/PRM_ReCredUpdate_English_7.os-meta.xml`
- **No concierge question currently exists** at the address screen level in either OmniScript.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **PRM_PractitionerParticipationAddressForm_English** | OmniScript Element — Radio Button | Add `RadioConciergeMedicineAtLocation` element to the Primary/Practice Address screen |
| **PRM_PractitionerParticipationAddressForm_English** | OmniScript Element — Pre-populate Set Values | Add a Set Values element to pre-populate `RadioConciergeMedicineAtLocation` from existing active InfoCodeAssignment lookup result |
| **PRMDR or IP — Fetch Existing Concierge Assignment** | DataRaptor Extract or Integration Procedure | Query existing active `PRM_InfoCodeAssignment__c` at `PRM_PractitionerFacilityAssignment__c` level for current HPF; return `Yes`/`No` to drive pre-population |
| **IP — Create/Terminate Concierge Assignment at Location** | Integration Procedure | On form submission: if `Yes` and no active assignment → create `PRM_InfoCodeAssignment__c`; if `No` and active assignment exists → set `PRM_TerminationDate__c` = today |
| **PRM_ReCredUpdate_English** | OmniScript — Remote Call | Invoke the create/terminate IP after address screen is confirmed |

### New OmniScript Element Specification

**Element Name:** `RadioConciergeMedicineAtLocation`
**Element Type:** Radio Button
**Parent Step:** Primary/Practice Address step in `PRM_PractitionerParticipationAddressForm_English`
**Question Text:**
```
*Do you practice concierge medicine at this Practice Location?

○ Yes
○ No
```
**Show Condition:** `%PractitionerRole% == 'PCP' || %PractitionerRole% == 'Dual'`
**Required:** Yes (when shown)
**Pre-population:** Set Values element runs `PRMDRFetchConciergeAssignmentAtLocation` (DataRaptor Extract) on step load; maps result to `RadioConciergeMedicineAtLocation`
**Validation Error:** `"Please indicate whether you practice concierge medicine at this practice location."`

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRFetchConciergeAssignmentAtLocation` | DataRaptor Extract (NEW) | `HealthcarePractitionerFacilityId` (current HPF Id) | `HasActiveAssignment` (Boolean), `AssignmentId` (Id) | Query `PRM_InfoCodeAssignment__c` WHERE `PRM_PractitionerFacilityAssignment__c = :hpfId` AND `PRM_TerminationDate__c = null`; return first result |
| `PRM_RecredCreateTerminateConciergeAtLocationParent` → `PRM_RecredCreateTerminateConciergeAtLocation` | Integration Procedure (NEW) | `HPFId`, `RadioConciergeMedicineAtLocation` (Yes/No), `AssignmentId` (if pre-existing), `TodayDate` | `success` (Boolean), `errorMessage` (String) | If `Yes` AND `AssignmentId` is null → Create `PRM_InfoCodeAssignment__c`; if `No` AND `AssignmentId` is not null → Update record: `PRM_TerminationDate__c = TodayDate` |

### Info Code Assignment Record Created on "Yes"

```json
{
  "PRM_InfoCode__c": "<Id of 'Concierge PCP' Info Code>",
  "PRM_PractitionerFacilityAssignment__c": "<HPF Id>",
  "PRM_Account__c": null,
  "PRM_HealthcareFacility__c": null,
  "PRM_EffectiveDate__c": "<Today's Date>"
}
```

> **Clarification needed:** Whether both "Concierge PCP" (internal) and "Concierge Provider" (external) assignments should be created on "Yes", or only "Concierge PCP". See Clarification Questions table.

---

## Acceptance Criteria

**Given** a Credentialing Specialist is processing a recredentialing PSV for a PCP or Dual-role practitioner and the address screen for Primary/Practice Address is displayed,
**When** the screen loads for a **new** practice location,
**Then** a required radio question "Do you practice concierge medicine at this Practice Location?" SHALL appear with options "Yes" and "No", pre-populated to "No" by default.

---

**Given** a Credentialing Specialist is processing a recredentialing PSV for a PCP or Dual-role practitioner and the address screen for an **existing** practice location is displayed,
**When** the HPF record already has an active `PRM_InfoCodeAssignment__c` at the Practitioner Practice Location level,
**Then** the radio question SHALL pre-populate to "Yes".

---

**Given** a Credentialing Specialist is processing a recredentialing PSV for a PCP or Dual-role practitioner and the address screen is displayed,
**When** the practitioner role is NOT PCP or Dual,
**Then** the concierge radio question SHALL NOT appear.

---

**Given** the concierge question is displayed and the user answers "Yes",
**When** the address screen is submitted and no active `PRM_InfoCodeAssignment__c` exists at the Practitioner Practice Location level for this HPF,
**Then** a new `PRM_InfoCodeAssignment__c` record SHALL be created with:
  - `PRM_InfoCode__c` = "Concierge PCP" Info Code
  - `PRM_PractitionerFacilityAssignment__c` = current HPF Id
  - `PRM_Account__c` = null
  - `PRM_HealthcareFacility__c` = null
  - `PRM_EffectiveDate__c` = today's date.

---

**Given** the concierge question pre-populated to "Yes" and the user changes the answer to "No",
**When** the address screen is submitted,
**Then** the existing active `PRM_InfoCodeAssignment__c` at the Practitioner Practice Location level SHALL be terminated by setting `PRM_TerminationDate__c` = today's date.

---

**Given** the concierge question is visible and the user attempts to proceed without answering,
**When** the user clicks "Next",
**Then** a validation error SHALL display: "Please indicate whether you practice concierge medicine at this practice location."

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | On "Yes", should both "Concierge PCP" (internal) and "Concierge Provider" (external) Info Code Assignments be created, or only "Concierge PCP"? | Determines whether one or two `PRM_InfoCodeAssignment__c` records are created per location | BA / Product |
| 2 | Is `PRM_PractitionerParticipationAddressForm_English` shared between PAR and Recred flows? If so, should the concierge question appear in both flows via a show condition, or only in the recred context? | If shared, need a context flag (e.g., `%FlowContext%`) to scope the question to recred only | Technical |
| 3 | When the existing assignment is terminated (user changes from Yes → No), should the `PRM_IsConciergeProvider__c` boolean on the HPF also be updated immediately, or is that handled by the trigger from Story 1.7? | Determines whether the IP needs to explicitly update the checkbox or rely on Story 1.7 trigger | Technical |
| 4 | If the user adds multiple practice locations in a single recred session, does each address screen instance independently call the create/terminate IP, or is there a batch call at the end? | Affects IP invocation design (per-screen vs. batch) | Technical |
| 5 | Should a "Concierge Provider" assignment also be terminated when user answers "No", or only "Concierge PCP"? | Scope of termination logic in the IP | BA / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PractitionerParticipationAddressForm_English` | OmniScript | HIGH | New required element added to address screen; show condition scopes to PCP/Dual |
| `PRM_ReCredUpdate_English` | OmniScript | MEDIUM | May need to pass `HPFId` and `PractitionerRole` context into the embedded address sub-OS |
| `PRMDRFetchConciergeAssignmentAtLocation` | DataRaptor Extract | HIGH | New DR — queries `PRM_InfoCodeAssignment__c` by HPF Id |
| `PRM_RecredCreateTerminateConciergeAtLocation` | Integration Procedure | HIGH | New IP — creates or terminates assignment on submit |
| `PRM_InfoCodeAssignment__c` | Object | MEDIUM | New records created/terminated programmatically during recred |
| Story 1.7 Boolean Checkbox Trigger | Apex Trigger | LOW | Existing trigger on `PRM_InfoCodeAssignment__c` should auto-update `PRM_IsConciergeProvider__c` on HPF — verify trigger fires on IP-created records |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_PractitionerParticipationAddressForm_English` | OmniScript — new Radio + Set Values elements + show condition | M | 2–3 hrs; conditional show logic requires `PractitionerRole` to be in scope |
| `PRMDRFetchConciergeAssignmentAtLocation` | New DataRaptor Extract | M | 2–3 hrs; single object query with filter on HPFId and null TerminationDate |
| `PRM_RecredCreateTerminateConciergeAtLocation` | New Integration Procedure (Parent + Child) | L | 4–6 hrs; conditional branching for create vs. terminate; include error handling |
| `PRM_ReCredUpdate_English` | OmniScript — context wiring (HPFId, PractitionerRole passthrough) | S | 1 hr; verify embedded sub-OS receives required context variables |
| Unit + Integration Tests | QA | M | 2–3 hrs; scenarios: new location Yes, new location No, existing Yes→No, existing No→Yes, non-PCP hidden |

**Total Estimated Effort:** ~11–16 hrs — **L/XL** (5 story points)
*AI-estimated — validate with team*

#### Dependencies

- Stories 1.1 and 1.2 completed (Info Codes exist in `PRM_InfoCode__c`)
- Story 1.3 completed (`PRM_InfoCodeAssignment__c` supports `PRM_PractitionerFacilityAssignment__c` level)
- Story 1.7 completed (boolean checkbox trigger on HPF responds to assignment changes)
- Story 6.1 and 6.2 completed (recred PSV flow context and Case Manager fields exist)
- `HealthcarePractitionerFacility` Id available in scope when address screen renders

#### Definition of Done

- [ ] `RadioConciergeMedicineAtLocation` Radio Button element added to `PRM_PractitionerParticipationAddressForm_English`
- [ ] Show condition limits question to PCP/Dual practitioners only
- [ ] Pre-population logic loads existing active assignment status on step entry
- [ ] `PRMDRFetchConciergeAssignmentAtLocation` DataRaptor Extract created and tested
- [ ] `PRM_RecredCreateTerminateConciergeAtLocation` Integration Procedure created and tested
- [ ] "Yes" answer creates `PRM_InfoCodeAssignment__c` at Practitioner Practice Location level
- [ ] "No" answer (when previously "Yes") terminates existing assignment with today's date
- [ ] Validation error fires when question is skipped
- [ ] Non-PCP/Dual practitioners do not see the question
- [ ] Story 1.7 trigger correctly updates `PRM_IsConciergeProvider__c` on HPF after IP-created assignment
- [ ] Integration test: New location — user answers Yes → assignment created
- [ ] Integration test: Existing location with Yes → user changes to No → assignment terminated
- [ ] Integration test: Non-PCP role → question hidden
- [ ] UAT sign-off by Credentialing team
- [ ] Deployed to all environments

---

## Cross-Epic Dependencies

### Critical Integration Points

1. **Info Code Setup → PAR Form**
   - Epic 1 Stories 1.1-1.2 must complete BEFORE Epic 2 Story 2.5 (PAR form integration)
   - PAR form needs "Concierge Provider" Info Code to exist

2. **PAR Form → Feeds**
   - Epic 2 Story 2.5 creates assignments that feed to downstream systems
   - Epic 3 (DART/Inquire Only) and Epic 4 (Provider Directory) depend on assignments existing

3. **Internal vs External Separation**
   - Epic 3 (Internal) feeds "Concierge PCP" assignments ONLY
   - Epic 4 (External) feeds "Concierge Provider" assignments ONLY
   - Must verify separation in Epic 3 Story 3.1 AC #5 and Epic 4 Story 4.1 AC #6

4. **Testing Coordination**
   - Epic 5 (Data Quality) should be tested alongside Epics 1-4 for end-to-end validation
   - All epics should be deployed together in Production (Story 4.4)

5. **Training**
   - Single PDA team training session can cover all epics
   - Training should occur after Test deployment, before Production

---

## Technical Considerations

### Architecture

```
PIE (Source of Truth)
├── PRM_InfoCode__c (Masters)
│   ├── "Concierge PCP" (Internal)
│   └── "Concierge Provider" (External)
│
├── PRM_InfoCodeAssignment__c (Assignments)
│   ├── Practitioner-level (PRM_Account__c)
│   ├── Practice Location-level (PRM_HealthcareFacility__c)
│   └── Practitioner Practice Location-level (PRM_PractitionerFacilityAssignment__c) **NEW**
│
├── Boolean Rollup Fields (NEW - Version 4.0)
│   ├── Account.PRM_IsConciergeProvider__c (TRUE if active assignment exists)
│   ├── HealthcareFacility.PRM_IsConciergeProvider__c (TRUE if active assignment exists)
│   └── HealthcarePractitionerFacility.PRM_IsConciergeProvider__c (TRUE if active assignment exists)
│
├── Case Manager Fields (NEW - Version 4.0)
│   ├── IndividualApplication.PRM_ConciergeMedicineIndicator__c (PAR form answer: Yes/No)
│   └── IndividualApplication.PRM_ConciergeFeeOptional__c (PAR form answer: Yes/No)
│
├── PAR Form (Data Capture)
│   ├── Creates "Concierge Provider" assignments (when answer = Yes)
│   └── Updates Case Manager fields (always) **NEW**
│
└── Triggers & Helpers
    ├── PRM_InfoCodeAssTrigger (existing, reused)
    └── PRM_ConciergeAssignmentHelper (NEW - maintains boolean checkboxes)

Downstream Systems
├── DART (receives "Concierge PCP" only)
├── Inquire Only (receives "Concierge PCP" only)
└── Provider Directory (receives "Concierge Provider" only)
```

### Data Isolation

| Info Code | Created By | Feeds To | Does NOT Feed To |
|-----------|------------|----------|------------------|
| **Concierge PCP** (Internal) | Manual (PDA team) | DART, Inquire Only | Provider Directory |
| **Concierge Provider** (External) | PAR Form (automatic) OR Manual | Provider Directory | DART, Inquire Only |

### Data Storage Strategy (Version 4.0)

| Data Element | Storage Location | Purpose | Updated By |
|--------------|------------------|---------|------------|
| **Info Code Assignment** | PRM_InfoCodeAssignment__c | Source of truth for concierge status; date-tracked | PDA team or PAR form |
| **Boolean Checkbox** | Account/HealthcareFacility/HealthcarePractitionerFacility | Quick access flag for UI/reporting; denormalized | Trigger (automatic) |
| **PAR Form Answers** | IndividualApplication (Case Manager) | Audit trail of original responses; historical record | PAR form (automatic) |

**Key Insight:** Boolean checkboxes are denormalized for performance, but Info Code Assignments remain the authoritative source. Case Manager fields preserve historical answers even if practitioner changes status later.

### Security & Access

- **PDA Team**: Create, edit, delete Info Code Assignments (both types)
- **Practitioners**: Answer PAR form questions (creates "Concierge Provider" assignment)
- **Internal Users**: View "Concierge PCP" data via DART/Inquire Only
- **Public**: View "Concierge Provider" data via Provider Directory
- **Object-Level Security**: Info Code and Info Code Assignment accessible to PDA team

### Performance

- **Database Indexing**: Index PRM_InfoCode__c, PRM_Account__c, PRM_HealthcareFacility__c, PRM_EffectiveDate__c, PRM_TerminationDate__c
- **Feed Optimization**: Feeds query delta (new/changed) after initial full load
- **Caching**: Provider Directory caches Info Code Assignment data (define refresh strategy)
- **Trigger Performance**: Bulkified logic handles 200+ records

### Testing Strategy

- **Unit Tests**: Trigger logic, validation rules, assignment creation/deletion
- **Integration Tests**: Feeds (DART, Inquire Only, Provider Directory), PAR form → assignment creation
- **End-to-End Tests**: PAR form submission → assignment creation → feed → downstream display
- **Performance Tests**: Feed performance, search performance, trigger performance
- **Security Tests**: Verify "Concierge PCP" not in Provider Directory, "Concierge Provider" appears correctly
- **Data Quality Tests**: Validation rules, date logic, duplicate prevention
- **UAT**: PDA team, Analytics team, Provider Directory team, Customer Service team, Practitioners (PAR form)

---

## Definition of Done

### Story-Level Definition of Done

Each user story is done when:

- [ ] Acceptance criteria met (all pass)
- [ ] Code implemented and unit tests written (if applicable)
- [ ] Code review completed (2+ reviewers)
- [ ] Integration tests pass (if applicable)
- [ ] Deployed to Test environment
- [ ] UAT completed by relevant stakeholders (sign-off received)
- [ ] Documentation updated (technical and user)
- [ ] No critical or high-priority bugs remaining
- [ ] Performance benchmarks met
- [ ] Security review completed (if applicable)

### Epic-Level Definition of Done

Each epic is done when:

- [ ] All user stories in epic are done
- [ ] End-to-end testing completed
- [ ] Deployed to Production environment
- [ ] Production verification completed (smoke testing)
- [ ] Stakeholder sign-off received (business owner)
- [ ] User training completed (if applicable)
- [ ] User documentation published
- [ ] Release notes published
- [ ] Monitoring and alerting configured
- [ ] Support team trained and ready
- [ ] Retrospective completed

---

## Acceptance Testing Strategy

### Test Scenarios by Epic

#### Epic 1 Scenarios: Core Infrastructure

**Scenario 1.1: Create Concierge PCP Info Code**
- Admin creates "Concierge PCP" Info Code in PIE
- Info Code is active and visible to PDA team
- Info Code appears in lookup fields when creating assignments

**Scenario 1.2: Create Info Code Assignment (Practitioner)**
- PDA user creates assignment for practitioner with "Concierge PCP"
- Assignment saves with Effective Date
- Assignment appears in related list on practitioner page

**Scenario 1.3: Validation - Future Dates Blocked**
- PDA user tries to create assignment with future Effective Date
- System displays error: "Effective Date cannot be in the future"
- Save is blocked

**Scenario 1.4: Validation - Duplicate Prevention**
- Practitioner already has active "Concierge PCP" assignment
- PDA user tries to create second assignment with same Info Code
- System displays error: "Duplicate active assignment"
- Save is blocked

**Scenario 1.5: Create Assignment at Practitioner Practice Location Level (NEW)**
- PDA user navigates to HealthcarePractitionerFacility (Practitioner Practice Location) page
- User creates "Concierge Provider" assignment at this level
- Assignment saves successfully
- Assignment is distinct from practitioner-level or practice-level assignments
- Boolean checkbox `PRM_IsConciergeProvider__c` on HealthcarePractitionerFacility is set to TRUE

**Scenario 1.6: Boolean Checkbox Updates on Assignment Creation (NEW)**
- PDA user creates "Concierge Provider" assignment for practitioner
- System automatically sets `Account.PRM_IsConciergeProvider__c = true`
- Practitioner page displays boolean checkbox as checked
- Verify trigger executed successfully

**Scenario 1.7: Boolean Checkbox Updates on Assignment Termination (NEW)**
- Practitioner has active "Concierge Provider" assignment with `PRM_IsConciergeProvider__c = true`
- PDA user terminates the assignment (sets termination date)
- System checks if other active assignments exist
- If no other active assignments: `Account.PRM_IsConciergeProvider__c` is set to false
- Practitioner page displays boolean checkbox as unchecked

**Scenario 1.8: Multiple Active Assignments (NEW)**
- Practitioner has two active "Concierge Provider" assignments (different practice locations via Practitioner Practice Location level)
- PDA user terminates one assignment
- System detects other active assignment exists
- `Account.PRM_IsConciergeProvider__c` remains TRUE
- Verify logic handles multiple assignments correctly

---

#### Epic 2 Scenarios: PAR Form

**Scenario 2.1: PCP Answers Yes to Concierge and Selects Practice Locations (UPDATED)**
- PCP completes PAR form with 3 practice locations, answers "Yes" to concierge question
- Optional fee question is displayed
- Practice location selection section is displayed showing all 3 locations
- User selects 2 out of 3 locations as concierge locations
- User submits form
- TWO "Concierge Provider" Info Code Assignments are created (one per selected location) at Practitioner Practice Location level with PRM_Pending__c = true **UPDATED**
- Case Manager fields are populated with Yes answers
- Boolean checkboxes on the two selected HealthcarePractitionerFacility records are set to TRUE **NEW**

**Scenario 2.2: Specialist Does Not See Questions**
- Specialist (non-PCP) completes PAR form
- Concierge questions are NOT displayed
- Warning message is NOT displayed
- Form submission is successful

**Scenario 2.3: User Changes Yes to No (UPDATED)**
- User selects "Yes", optional fee question appears
- Practice location section appears with checkboxes
- User selects 2 locations
- User changes concierge answer to "No"
- Optional fee question is hidden and cleared
- Practice location section is hidden and selections are cleared **UPDATED**
- Form submits without creating any assignments
- Case Manager fields are populated with No answers

**Scenario 2.4: Warning Message Links Work**
- PCP completes form, sees warning message
- User clicks "IBX" link → opens correct URL in new tab
- User clicks "AHNJ" link → opens correct URL
- User clicks "AHPA" link → opens correct URL

**Scenario 2.3A: Single Practice Location Auto-Selection (NEW)**
- PCP completes PAR form with only 1 practice location
- User answers "Yes" to concierge question
- Practice location section displays with single location pre-selected/checked
- User can uncheck if needed, but must have at least one selected
- User submits form with location checked
- ONE "Concierge Provider" Info Code Assignment is created at Practitioner Practice Location level
- Boolean checkbox on HealthcarePractitionerFacility is set to TRUE

**Scenario 2.3B: Validation - No Locations Selected (NEW)**
- PCP answers "Yes" to concierge question
- Practice location section displays with 3 locations
- User does not select any locations
- User attempts to submit form
- Validation error: "Please select at least one practice location where you practice concierge medicine"
- Form submission is blocked

**Scenario 2.5: Case Approval Updates All Assignments (UPDATED)**
- PAR form submitted with concierge = Yes and 3 locations selected
- THREE assignments created with PRM_Pending__c = true **UPDATED**
- Case is approved
- ALL THREE assignments updated with PRM_Pending__c = false (active) **UPDATED**

**Scenario 2.6: Case Manager Fields Capture PAR Form Answers - Yes Scenario (NEW)**
- PCP completes PAR form, answers "Yes" to concierge medicine
- PCP answers "No" to optional fee question
- User submits form
- Case Manager (IndividualApplication) record is updated:
  - `PRM_ConciergeMedicineIndicator__c = true`
  - `PRM_ConciergeFeeOptional__c = false`
- Fields are visible on Case Manager page
- Verify data persists correctly

**Scenario 2.7: Case Manager Fields Capture PAR Form Answers - No Scenario (NEW)**
- PCP completes PAR form, answers "No" to concierge medicine
- Optional fee question is hidden (not answered)
- User submits form
- Case Manager record is updated:
  - `PRM_ConciergeMedicineIndicator__c = false`
  - `PRM_ConciergeFeeOptional__c = false` (or null)
- No Info Code Assignment is created
- Verify Case Manager fields are still populated

**Scenario 2.8: Case Manager Fields Independent of Case Approval/Denial (NEW)**
- PAR form submitted with concierge = Yes, optional fee = Yes
- Case Manager fields are populated
- Case is denied
- Verify Case Manager fields remain unchanged (still show original answers)
- Info Code Assignment is handled by case denial flow (PRM_Pending__c updated)

---

#### Epic 3 Scenarios: Internal Analytics

**Scenario 3.1: DART Receives Concierge PCP Data**
- Practitioner has active "Concierge PCP" assignment in PIE
- PIE-to-DART feed runs
- Assignment appears in DART within SLA
- DART can filter/report on concierge status

**Scenario 3.2: Inquire Only Displays Status**
- CSR searches for practitioner in Inquire Only
- Practitioner's "Concierge PCP" status is displayed
- Effective Date and Termination Date are shown
- Status indicates "Active" (if no termination date)

**Scenario 3.3: Dashboard Shows Trends**
- Analytics user opens Concierge PCP dashboard in DART
- Dashboard shows accurate count of active concierge PCPs
- Trend line shows historical changes
- Filters work correctly

**Scenario 3.4: Internal Data Does Not Leak**
- Practitioner has "Concierge PCP" assignment (internal)
- Practitioner does NOT have "Concierge Provider" assignment (external)
- Patient searches Provider Directory
- Practitioner does NOT show as concierge (verified)

---

#### Epic 4 Scenarios: Provider Directory

**Scenario 4.1: External Assignment Feeds to Directory**
- Practitioner has active "Concierge Provider" assignment in PIE
- PIE-to-Provider Directory feed runs
- Practitioner appears as concierge in Provider Directory
- Concierge indicator is displayed on detail page

**Scenario 4.2: Patient Searches for Concierge Providers**
- Patient searches Provider Directory
- Patient filters by "Concierge Medicine"
- Search results show only providers with active "Concierge Provider" assignment
- Concierge indicator appears in search results

**Scenario 4.3: Terminated Assignment Removed**
- "Concierge Provider" assignment is terminated in PIE
- PIE-to-Provider Directory feed runs
- Provider no longer shows as concierge in Provider Directory
- Concierge indicator is removed

**Scenario 4.4: External Data Does Not Leak to DART**
- Practitioner has "Concierge Provider" assignment (external)
- Practitioner does NOT have "Concierge PCP" assignment (internal)
- Analytics user queries DART
- Practitioner does NOT appear in Concierge PCP reports (verified)

---

#### Epic 5 Scenarios: UX & Data Quality

**Scenario 5.1: Quick Action Creates Assignment**
- PDA user views practitioner page
- User clicks "Manage Concierge Status" button
- Modal opens, user selects "Concierge Provider" and enters Effective Date
- User saves, assignment is created
- Success message displays

**Scenario 5.2: Data Quality Batch Catches Violation**
- Assignment exists with Termination Date before Effective Date (test data)
- Daily DQ batch runs
- Violation appears in DQ report
- Email is sent to PDA team

**Scenario 5.3: Consistency Check Identifies Mismatch**
- Practice location has "Concierge Provider" assignment
- Not all practitioners at location have matching assignment
- Weekly consistency check runs
- Mismatch appears in report and dashboard
- PDA team reviews and resolves

---

## Implementation Roadmap

### Phase 1: Foundation (Sprints 1-2.5)
**Focus:** Core infrastructure and configuration
- Epic 1: Core Infrastructure & Setup (23 points - includes boolean checkboxes and trigger logic)
- Epic 2: Data Capture via PAR Form (26 points - includes Case Manager field capture and practice location selection)
- **Total:** 49 points
- **Deliverable:** Info Codes exist, boolean checkboxes on key objects, PAR form captures concierge status with location-specific selection and saves to Case Manager, assignments created at Practitioner Practice Location level for selected locations

### Phase 2: Internal Integration (Sprint 3)
**Focus:** Internal analytics systems
- Epic 3: Internal Analytics Integration (13 points)
- **Total:** 13 points
- **Deliverable:** DART and Inquire Only receive and display concierge data

### Phase 3: External Integration (Sprint 4)
**Focus:** Public provider directory
- Epic 4: Public Provider Directory Integration (16 points)
- **Total:** 16 points
- **Deliverable:** Provider Directory displays concierge providers to public

### Phase 4: Enhancements & Quality (Sprint 5)
**Focus:** UX improvements and data quality
- Epic 5: UX Enhancements & Data Quality (13 points)
- **Total:** 13 points
- **Deliverable:** Quick actions, DQ rules, consistency checks

### Phase 5: Recredentialing Integration (Sprint 6)
**Focus:** Recredentialing PSV Guided Flow integration + per-location address screen question
- Epic 6: Recredentialing PSV Guided Flow (19 points — includes Stories 6.1, 6.2, 6.3)
- **Total:** 19 points
- **Deliverable:** Concierge questions in recredentialing PSV, responses saved to Case Manager; practitioner-level Info Code Assignment auto-created when Q1=Yes and no existing assignment; per-location concierge question on address screen with automated Info Code Assignment creation/termination at Practitioner Practice Location level

### Phase 6: Flow Integration (Sprint 7)
**Focus:** Integration with existing flows (from separate analysis doc)
- Case denial/closure integration (3 points)
- RCAT/Recredentialing integration (8 points)
- Termination flows (10 points)
- DataRaptor updates (8 points)
- Validation (3 points)
- **Total:** 32 points (estimated from Flow Impact Analysis)
- **Deliverable:** Full integration with existing credentialing workflows

### Phase 7: Production Deployment & Stabilization (Sprint 8)
**Focus:** Production deployment, monitoring, training
- Production deployment (included in Phase 4)
- Post-deployment monitoring
- User training (PDA team, Analytics team, CSR team)
- Documentation finalization
- Retrospective

---

## Total Effort Summary

| Phase | Focus | Story Points | Sprints |
|-------|-------|--------------|---------|
| Phase 1 | Foundation | 49 (+18 from v3.0) | 2.5-3 |
| Phase 2 | Internal Integration | 13 | 1 |
| Phase 3 | External Integration | 16 | 1 |
| Phase 4 | Enhancements & Quality | 13 | 1 |
| Phase 5 | Recredentialing Integration | 19 (+19 from v3.0 + v4.3) | 1 |
| Phase 6 | Flow Integration | 37 | 1.5 |
| Phase 7 | Deployment & Training | (included) | 0.5 |
| **Total** | | **~147 points** | **8.5-9.5 sprints** |

**Timeline:** 4-5 months (assuming 2-week sprints, 15-20 points/sprint)

**Version 4.0 Changes:**
- +10 points: Boolean checkbox fields and trigger logic (Epic 1, Stories 1.6 and 1.7)
- +2 points: Case Manager PAR form answer fields (Epic 2, Story 2.4A and updated 2.5)

**Version 4.1 Changes:**
- +3 points: Practice location selection UI in PAR form (Epic 2, Story 2.2 updated)
- +3 points: Loop logic to create multiple Practitioner Practice Location assignments (Epic 2, Story 2.5 updated)

**Version 4.2 Changes:**
- +3 points: Recred Case Manager fields (Epic 6, Story 6.1)
- +9 points: Recred PSV Guided Flow updates (Epic 6, Story 6.2)

**Version 4.3 Changes:**
- +2 points: Practitioner-level Info Code Assignment creation on Q1=Yes (Epic 6, Story 6.2 updated)
- +5 points: Recred PSV address screen per-location concierge question + Info Code Assignment logic (Epic 6, Story 6.3)

---

## Next Steps

1. **Review and Approval**
   - Present complete user stories to product owner and stakeholders
   - Obtain approval on approach, scope, and timeline
   - Confirm business decisions (RCAT exclusion, rollup logic, etc.)

2. **Story Refinement**
   - Conduct planning poker or estimation session with dev team
   - Refine story points based on team velocity and technical assessment
   - Break down any stories > 5 points if needed

3. **Sprint Planning**
   - Assign stories to sprints based on roadmap
   - Identify parallel tracks (e.g., backend and UI can run concurrently)
   - Plan dependencies and hand-offs

4. **Technical Design**
   - Create detailed technical design documents for high-complexity stories
   - Review database schema, API contracts, UI mockups
   - Identify reusable components

5. **Begin Development**
   - Start with Phase 1: Epic 1 Story 1.1 (Create Info Codes)
   - Set up development environments
   - Establish CI/CD pipelines for automated testing

6. **Communication**
   - Notify PDA team, Analytics team, Provider Directory team, CSR team of upcoming changes
   - Schedule training sessions
   - Publish implementation roadmap

---

**End of Document**
