# Concierge Medicine Info Code Implementation - User Stories

**Document Version:** 2.0 (Info Code Approach)
**Created Date:** April 1, 2026
**Project:** PIE & Provider Directory Enhancement - Concierge Medicine Provider Tracking via Info Codes
**Approach:** Info Code + Info Code Assignment (following PNC/Delegated pattern)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Info Code Approach Overview](#info-code-approach-overview)
3. [Epic Overview](#epic-overview)
4. [User Stories - Epic 1: Internal Concierge PCP Info Code](#user-stories---epic-1-internal-concierge-pcp-info-code)
5. [User Stories - Epic 2: External Concierge Provider Info Code](#user-stories---epic-2-external-concierge-provider-info-code)
6. [Cross-Epic Dependencies](#cross-epic-dependencies)
7. [Technical Considerations](#technical-considerations)
8. [Definition of Done](#definition-of-done)
9. [Acceptance Testing Strategy](#acceptance-testing-strategy)
10. [Data Model Comparison](#data-model-comparison)

---

## Executive Summary

This document outlines user stories for implementing **Concierge Medicine Provider tracking using the Info Code pattern** (PRM_InfoCodeAssignment__c), following the proven approach used for PNC and Delegated credentialing.

### Why Info Code Approach?

**Benefits over field-based approach:**
- ✅ **No schema changes** on Account or HealthcareFacility objects
- ✅ **Flexible date tracking** via Info Code Assignment effective/termination dates
- ✅ **Proven pattern** already used for PNC and Delegated
- ✅ **Automatic rollup logic** via existing triggers (PRM_InfoCodeAssTriggerHelper)
- ✅ **Audit trail** built-in with Info Code Assignment history
- ✅ **Integration-friendly** - feeds can query Info Code Assignments
- ✅ **Easier to maintain** - no field-level security complexity

### Two Info Codes to Create:

1. **Internal: "Concierge PCP"** - For internal analytics (DART, Inquire Only only)
2. **External: "Concierge Provider"** - For public Provider Directory

---

## Info Code Approach Overview

### Data Model

```
PRM_InfoCode__c (Master)
├── Name: "Concierge PCP" or "Concierge Provider"
├── PRM_InfoCodeType__c: (e.g., "Provider Attribute")
└── PRM_IsActive__c: true

PRM_InfoCodeAssignment__c (Junction)
├── PRM_InfoCode__c → PRM_InfoCode__c (lookup)
├── PRM_Account__c → Account (Practitioner) (lookup)
├── PRM_HealthcareFacility__c → HealthcareFacility (Practice Location) (lookup)
├── PRM_EffectiveDate__c: Date
├── PRM_TerminationDate__c: Date
├── PRM_Pending__c: Boolean
└── PRM_CaseManager__c: (if applicable)
```

### Assignment Levels

| Info Code | Assigned To | Rollup Logic |
|-----------|-------------|--------------|
| **Concierge PCP** (Internal) | Practitioner Account OR Practice Location (HealthcareFacility) | Optional: Rollup to Account if all practice locations have this code |
| **Concierge Provider** (External) | Practitioner Account OR Practice Location (HealthcareFacility) | No rollup needed; feeds query assignments directly |

### Integration Pattern

| System | Query Pattern |
|--------|---------------|
| **DART** | Query PRM_InfoCodeAssignment__c WHERE PRM_InfoCode__r.Name = 'Concierge PCP' AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY) |
| **Inquire Only** | Same as DART |
| **Provider Directory** | Query PRM_InfoCodeAssignment__c WHERE PRM_InfoCode__r.Name = 'Concierge Provider' AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY) |

---

## Epic Overview

### Epic 1: Internal Concierge PCP Info Code

**Epic Goal:** Create "Concierge PCP" Info Code and implement Info Code Assignment workflow for internal analytics (DART, Inquire Only). Must NOT feed to Provider Directory.

**Business Value:** Track concierge medicine providers for internal analytics without public exposure.

**Priority:** High
**Estimated Story Points:** 28

---

### Epic 2: External Concierge Provider Info Code

**Epic Goal:** Create "Concierge Provider" Info Code and implement Info Code Assignment workflow for public Provider Directory display.

**Business Value:** Enable patients to identify concierge providers in Provider Directory; improve UX for PDA team managing public-facing data.

**Priority:** High
**Estimated Story Points:** 24

---

## User Stories - Epic 1: Internal Concierge PCP Info Code

### Story 1.1: Create "Concierge PCP" Info Code Master Record

**As a** System Administrator
**I want** to create a "Concierge PCP" Info Code master record
**So that** this code can be assigned to practitioners and practice locations for internal tracking

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Info Code Setup

#### Acceptance Criteria

1. **Info Code Creation**
   - PRM_InfoCode__c record created with Name = "Concierge PCP"
   - PRM_InfoCodeType__c = "Provider Attribute" (or appropriate type)
   - PRM_IsActive__c = true
   - Description field includes: "Internal use only - identifies concierge primary care physicians for DART and Inquire Only analytics"
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

### Story 1.2: Enable Info Code Assignment Creation for Concierge PCP (Practitioner Level)

**As a** Provider Data Administrator
**I want** to assign the "Concierge PCP" Info Code to individual practitioner accounts
**So that** I can track which practitioners operate concierge practices for internal analytics

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI**
   - PDA user can create PRM_InfoCodeAssignment__c record from Practitioner Account page
   - PRM_InfoCode__c lookup shows "Concierge PCP" as selectable option
   - PRM_Account__c is auto-populated with current Practitioner Account
   - PRM_EffectiveDate__c field is visible and editable (MM/DD/YYYY format)
   - PRM_TerminationDate__c field is visible and editable (MM/DD/YYYY format)
   - Save button persists the assignment

2. **Validation Rules**
   - PRM_InfoCode__c is required
   - PRM_Account__c OR PRM_HealthcareFacility__c must be populated (not both)
   - PRM_EffectiveDate__c cannot be in the future
   - PRM_TerminationDate__c cannot be before PRM_EffectiveDate__c
   - PRM_TerminationDate__c cannot be in the future
   - Duplicate assignment prevention: Cannot create duplicate active assignment (same Info Code + Account + no termination date)

3. **List View / Related List**
   - "Info Code Assignments" related list appears on Practitioner Account page
   - List shows: Info Code Name, Effective Date, Termination Date, Pending status
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

4. **Assignment Visibility**
   - Assignments are visible to PDA team
   - Assignments are visible in DART/Inquire Only (via feeds)
   - Assignments are NOT visible in Provider Directory feeds

#### Technical Considerations

- Object: PRM_InfoCodeAssignment__c
- Relationships: PRM_InfoCode__c (lookup), PRM_Account__c (lookup), PRM_HealthcareFacility__c (lookup)
- Page Layout: Add "Info Code Assignments" related list to Practitioner Account layout
- Validation Rules: Implement as Apex trigger or validation rule
- Consider Lightning component for inline assignment creation

#### Dependencies

- Story 1.1 completed ("Concierge PCP" Info Code exists)
- PRM_InfoCodeAssignment__c object access
- Practitioner Account page layout editable

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practitioner
- [ ] "Concierge PCP" Info Code is selectable
- [ ] Effective Date and Termination Date fields work correctly
- [ ] Validation rules prevent invalid assignments
- [ ] Related list displays assignments on Practitioner page
- [ ] Unit tests for validation rules pass
- [ ] UAT completed by PDA team

---

### Story 1.3: Enable Info Code Assignment Creation for Concierge PCP (Practice Location Level)

**As a** Provider Data Administrator
**I want** to assign the "Concierge PCP" Info Code to practice locations (HealthcareFacility)
**So that** I can track which practice locations operate as concierge practices (when all PCPs are concierge)

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI**
   - PDA user can create PRM_InfoCodeAssignment__c record from HealthcareFacility (Practice Location) page
   - PRM_InfoCode__c lookup shows "Concierge PCP" as selectable option
   - PRM_HealthcareFacility__c is auto-populated with current Practice Location
   - PRM_EffectiveDate__c and PRM_TerminationDate__c fields are visible and editable
   - Save button persists the assignment

2. **Validation Rules**
   - Same validation rules as Story 1.2 (future dates, date order, duplicates)
   - PRM_HealthcareFacility__c is populated (PRM_Account__c is null for practice-level assignment)

3. **List View / Related List**
   - "Info Code Assignments" related list appears on Practice Location page
   - List shows: Info Code Name, Effective Date, Termination Date, Pending status
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

4. **Assignment Visibility**
   - Assignments are visible to PDA team
   - Assignments are visible in DART/Inquire Only (via feeds)
   - Assignments are NOT visible in Provider Directory feeds

5. **Use Case Guidance**
   - Field help text clarifies: "Assign at Practice Location level when ALL PCPs at this location operate concierge practices"
   - Warning message if trying to assign at practice level when individual practitioners already have the code (data quality check - optional)

#### Technical Considerations

- Same as Story 1.2 but for HealthcareFacility object
- Page Layout: Add "Info Code Assignments" related list to Practice Location layout
- Consider data quality check: compare practice-level assignment to practitioner-level assignments

#### Dependencies

- Story 1.1 completed ("Concierge PCP" Info Code exists)
- PRM_InfoCodeAssignment__c object access
- Practice Location page layout editable

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practice Location
- [ ] "Concierge PCP" Info Code is selectable
- [ ] Validation rules work correctly
- [ ] Related list displays assignments on Practice Location page
- [ ] Help text clarifies practice-level use case
- [ ] Unit tests pass
- [ ] UAT completed by PDA team

---

### Story 1.4: Configure DART Integration to Read Concierge PCP Info Code Assignments

**As a** Data Analytics Team Member
**I want** DART to receive Concierge PCP Info Code Assignment data from PIE
**So that** I can analyze concierge provider trends and create executive reports

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / DART

#### Acceptance Criteria

1. **Data Feed Configuration**
   - PIE-to-DART ETL feed includes PRM_InfoCodeAssignment__c records WHERE PRM_InfoCode__r.Name = 'Concierge PCP'
   - Feed includes: Account (Practitioner), HealthcareFacility (Practice Location), Effective Date, Termination Date, Pending status
   - Feed includes both practitioner-level and practice-level assignments
   - Feed configuration is documented

2. **Data Mapping**
   - Source fields correctly mapped to DART target fields:
     - PRM_Account__c → Practitioner ID
     - PRM_HealthcareFacility__c → Practice Location ID
     - PRM_EffectiveDate__c → Effective Date
     - PRM_TerminationDate__c → Termination Date
     - Derived field: "Currently Active" = (Termination Date IS NULL OR Termination Date > TODAY)
   - Null values handled appropriately
   - Field mapping document created/updated

3. **Feed Schedule and Reliability**
   - Data refresh frequency defined (e.g., daily)
   - Initial full load successfully transfers all existing Info Code Assignments
   - Incremental updates capture new/changed assignments within expected timeframe (e.g., 24 hours)
   - Error handling and retry logic in place
   - Feed failures trigger alerts to appropriate team

4. **Data Validation in DART**
   - Sample of 10+ records verified in DART after feed
   - Assignment values match PIE source data
   - Date values match PIE source data (format preserved)
   - DART can filter/group by concierge status (via Info Code Assignment)
   - DART can calculate "currently active concierge" providers

5. **Exclusion from Provider Directory**
   - Verify "Concierge PCP" Info Code Assignments do NOT feed to Provider Directory
   - Provider Directory feed configuration explicitly excludes this Info Code
   - Test scenarios confirm no leakage to public systems

#### Technical Considerations

- ETL Pipeline: Update existing PIE-to-DART pipeline or create new
- Query: `SELECT Id, PRM_Account__c, PRM_Account__r.Name, PRM_HealthcareFacility__c, PRM_HealthcareFacility__r.Name, PRM_EffectiveDate__c, PRM_TerminationDate__c, PRM_Pending__c FROM PRM_InfoCodeAssignment__c WHERE PRM_InfoCode__r.Name = 'Concierge PCP'`
- Data Format: Ensure date format compatibility
- Performance: Monitor feed performance impact
- Monitoring: Set up alerting for feed failures

#### Dependencies

- Stories 1.1, 1.2, 1.3 completed (Info Code and Assignments exist)
- DART target schema updated to accept Info Code Assignment data
- ETL infrastructure available
- DART team coordination required

#### Definition of Done

- [ ] PIE-to-DART feed configuration updated
- [ ] Field mapping documented and approved
- [ ] Initial full data load completed successfully
- [ ] Incremental update tested and verified
- [ ] Data validation completed (sample records verified)
- [ ] Exclusion from Provider Directory verified
- [ ] Monitoring and alerting configured
- [ ] DART team sign-off received
- [ ] Technical documentation updated

---

### Story 1.5: Configure "Inquire Only" System Integration to Read Concierge PCP Info Code Assignments

**As a** Customer Service Representative
**I want** to view Concierge PCP Info Code Assignments in the "Inquire Only" system
**So that** I can provide accurate information when responding to internal inquiries about provider concierge status

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - Data Integration / Inquire Only System

#### Acceptance Criteria

1. **Data Feed Configuration**
   - PIE-to-Inquire Only feed includes PRM_InfoCodeAssignment__c records WHERE PRM_InfoCode__r.Name = 'Concierge PCP'
   - Feed includes: Account (Practitioner), HealthcareFacility (Practice Location), Effective Date, Termination Date
   - Feed includes both practitioner-level and practice-level assignments
   - Feed configuration is documented

2. **User Interface Display**
   - Info Code Assignments are visible in provider detail view in Inquire Only
   - Fields clearly labeled: "Concierge PCP", "Effective Date", "Termination Date"
   - Dates formatted consistently (MM/DD/YYYY)
   - Visual indicator shows current status (Active if no termination date or termination date > today)
   - Data is read-only (no edit capability in Inquire Only)

3. **Search and Filter Capability**
   - Users can search for providers with "Concierge PCP" Info Code Assignment
   - Users can filter by date ranges (effective date, termination date)
   - Search results display concierge status clearly
   - Search performance is acceptable (< 3 seconds for typical queries)

4. **Data Synchronization**
   - Data refresh frequency defined and documented
   - Data in Inquire Only matches PIE source within acceptable lag time
   - Updates to Info Code Assignments in PIE appear in Inquire Only within expected timeframe
   - Error handling for feed failures in place

5. **Exclusion from Provider Directory**
   - Verify "Concierge PCP" Info Code Assignments do NOT feed to Provider Directory
   - Test scenarios confirm no leakage to public systems

#### Technical Considerations

- Integration: Update existing PIE-to-Inquire Only integration
- UI: Update Inquire Only UI to display Info Code Assignments
- Performance: Ensure search/filter queries are optimized
- Caching: Consider caching strategy if applicable
- Documentation: Update Inquire Only user guide

#### Dependencies

- Stories 1.1, 1.2, 1.3 completed (Info Code and Assignments exist)
- Inquire Only system access for testing
- Inquire Only development team coordination
- UI mockups/wireframes approved

#### Definition of Done

- [ ] PIE-to-Inquire Only feed configuration updated
- [ ] UI changes implemented and tested
- [ ] Search and filter functionality tested
- [ ] Data synchronization verified
- [ ] Performance testing completed
- [ ] Exclusion from Provider Directory verified
- [ ] User acceptance testing completed by CSR team
- [ ] User guide updated
- [ ] Technical documentation updated

---

### Story 1.6: Implement Trigger Logic for Concierge PCP Info Code Assignment Changes

**As a** System Processing Info Code Assignment Changes
**I want** triggers to fire when Concierge PCP Info Code Assignments are created, updated, or deleted
**So that** downstream systems and batch jobs are aware of concierge status changes

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - Apex Triggers

#### Acceptance Criteria

1. **Trigger Implementation**
   - PRM_InfoCodeAssTrigger fires on INSERT, UPDATE, DELETE of PRM_InfoCodeAssignment__c
   - Trigger includes logic for "Concierge PCP" Info Code (filter by PRM_InfoCode__r.Name)
   - Trigger calls appropriate helper classes (e.g., PRM_InfoCodeAssTriggerHelper or new ConciergePCPHelper)
   - Trigger is bulkified (handles 200+ records)

2. **Rollup Logic (Optional - Based on Business Requirements)**
   - **Option A: No Rollup** - Info Code Assignments are queried directly by feeds; no field on Account
   - **Option B: Rollup to Account.PRM_ConciergePCP__c** - If business requires a flag on Account for quick access:
     - When Info Code Assignment created/updated/deleted, recalculate practitioner's concierge status
     - Practitioner Account.PRM_ConciergePCP__c = true ONLY IF practitioner has active "Concierge PCP" assignment at practitioner level OR all practice locations have active "Concierge PCP" assignment
     - Update Account.PRM_ConciergePCP__c accordingly

3. **Trigger Actions**
   - Log Info Code Assignment changes (if audit logging required)
   - Queue batch jobs if needed (e.g., recalculate derived fields)
   - Send platform events if downstream systems require real-time notifications (optional)

4. **Error Handling**
   - Trigger includes try-catch blocks
   - Errors are logged and do not block DML operations (or block with clear error messages)
   - Unit tests cover error scenarios

5. **Performance**
   - Trigger executes within acceptable time (< 2 seconds for typical batches)
   - No SOQL queries inside loops
   - Bulkified logic handles large data volumes

#### Technical Considerations

- Trigger: PRM_InfoCodeAssTrigger (may already exist for other Info Codes)
- Helper Class: Extend PRM_InfoCodeAssTriggerHelper or create PRM_ConciergePCPTriggerHelper
- Rollup Logic: Follow PNC pattern (PRM_CommonUtils.updateAccountPNCHelper) if rollup is needed
- Testing: Unit tests with 200+ records

#### Dependencies

- Stories 1.1, 1.2, 1.3 completed (Info Code and Assignments exist)
- Decision on rollup logic (Option A or B)
- Access to trigger and helper class code

#### Definition of Done

- [ ] Trigger implemented and deployed
- [ ] Rollup logic implemented (if Option B selected)
- [ ] Unit tests written and passing (200+ records)
- [ ] Error handling tested
- [ ] Performance testing completed
- [ ] Code review completed
- [ ] Technical documentation updated

---

### Story 1.7: Create Internal Reporting Dashboard for Concierge PCP Analytics (DART)

**As a** Healthcare Analytics Manager
**I want** a dedicated reporting dashboard showing Concierge PCP trends and statistics
**So that** I can monitor the growth of concierge medicine in our network and make data-driven business decisions

**Priority:** P2 - Medium
**Story Points:** 5
**Component:** DART - Reporting

#### Acceptance Criteria

1. **Dashboard Metrics**
   - Total count of active Concierge PCP practitioners (currently active Info Code Assignments)
   - Total count of active Concierge PCP practice locations (currently active Info Code Assignments)
   - Total count of historical Concierge PCPs (all time)
   - Trend over time (new Concierge PCPs by month/quarter)
   - Terminations over time (Concierge PCPs who stopped by month/quarter)
   - Average duration of concierge practice

2. **Filtering and Segmentation**
   - Filter by date range (effective date, termination date)
   - Filter by assignment level (practitioner vs practice location)
   - Filter by geographic region/state (if available)
   - Filter by specialty (if available)

3. **Visualizations**
   - Line chart: Concierge PCP count trend over time
   - Bar chart: New Concierge PCPs by month/quarter
   - Pie chart: Active vs inactive Concierge PCPs
   - Table: List of all Concierge PCP assignments with key details (practitioner name, practice location, effective date, termination date, status)

4. **Export and Sharing**
   - Dashboard can be exported to PDF
   - Dashboard can be exported to Excel
   - Dashboard can be scheduled for automated email delivery
   - Dashboard link can be shared with appropriate stakeholders

#### Technical Considerations

- Platform: Build in DART's native reporting tool
- Data Source: Use Info Code Assignment data from Story 1.4 (DART integration)
- Performance: Optimize queries for acceptable load time (< 5 seconds)
- Security: Restrict access to internal users only
- Refresh: Define data refresh schedule

#### Dependencies

- Story 1.4 completed (DART integration with data flowing)
- DART reporting platform access
- Sample data for testing visualizations

#### Definition of Done

- [ ] Dashboard created in DART
- [ ] All metrics and visualizations implemented
- [ ] Filters working correctly
- [ ] Export functionality tested (PDF, Excel)
- [ ] Performance testing completed
- [ ] Security/access controls verified
- [ ] UAT completed by Analytics team
- [ ] Dashboard documented in DART user guide

---

### Story 1.8: Develop Data Quality Rules for Concierge PCP Info Code Assignments

**As a** Data Governance Lead
**I want** automated data quality rules and alerts for Concierge PCP Info Code Assignments
**So that** I can ensure data integrity and prevent invalid data states

**Priority:** P2 - Medium
**Story Points:** 3
**Component:** PIE - Data Quality

#### Acceptance Criteria

1. **Validation Rules Implemented**
   - Rule: Termination date cannot be before effective date (error - enforced via trigger or validation rule)
   - Rule: Dates cannot be in the future (error)
   - Rule: If termination date is in the past, consider the assignment inactive (system calculates; no manual flag)
   - Rule: No duplicate active assignments (same Info Code + Account/Facility, no termination date) (error)
   - Rule: If Info Code Assignment has termination date, effective date should be present (warning)

2. **Automated Data Quality Checks**
   - Daily batch job scans for data quality violations
   - Report generated listing all violations (practitioner ID, violation type, current values)
   - Report sent to PDA team via email
   - Dashboard showing data quality metrics (% compliant records, violation counts by type)

3. **User Alerts**
   - Real-time validation errors prevent saving invalid data (hard stops)
   - Real-time validation warnings allow saving but notify user (soft stops)
   - Clear, actionable error/warning messages
   - Inline help explains how to resolve violations

4. **Remediation Workflow**
   - PDA team can view list of data quality violations
   - PDA team can edit Info Code Assignments to fix issues
   - Audit trail tracks when violations were resolved
   - Metrics show trend of data quality improvement over time

#### Technical Considerations

- Validation Engine: Leverage existing PIE validation framework or Apex triggers
- Batch Processing: Schedule daily DQ job during off-peak hours
- Performance: Ensure DQ checks don't significantly impact save operations
- Notification: Use existing email notification system
- Dashboard: Consider embedding in existing DQ dashboard if available

#### Dependencies

- Stories 1.1, 1.2, 1.3, 1.6 completed (Info Code, Assignments, and triggers exist)
- Access to PIE validation framework
- Email notification system available
- DQ dashboard platform available (or new dashboard needed)

#### Definition of Done

- [ ] All validation rules implemented and tested
- [ ] Daily batch DQ job scheduled and running
- [ ] DQ report generated and distributed
- [ ] Real-time validation working (errors and warnings)
- [ ] DQ dashboard created (or integrated into existing)
- [ ] Remediation workflow tested
- [ ] Documentation updated (DQ rules, report interpretation)
- [ ] PDA team trained on DQ reports and remediation

---

## User Stories - Epic 2: External Concierge Provider Info Code

### Story 2.1: Create "Concierge Provider" Info Code Master Record

**As a** System Administrator
**I want** to create a "Concierge Provider" Info Code master record
**So that** this code can be assigned to practitioners and practice locations for public Provider Directory display

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Info Code Setup

#### Acceptance Criteria

1. **Info Code Creation**
   - PRM_InfoCode__c record created with Name = "Concierge Provider"
   - PRM_InfoCodeType__c = "Provider Attribute" (or appropriate type)
   - PRM_IsActive__c = true
   - Description field includes: "Public-facing - identifies concierge providers for Provider Directory"
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
- Ensure Info Code is available in all environments (sandbox, UAT, prod)
- Consider adding custom checkbox: PRM_PublicFacing__c = true (optional)

#### Dependencies

- Access to PRM_InfoCode__c object in org
- Permissions to create Info Code records
- Info Code Type picklist values defined

#### Definition of Done

- [ ] "Concierge Provider" Info Code record created in all environments
- [ ] Info Code is active and visible to PDA team
- [ ] Info Code description includes "Public-facing"
- [ ] Info Code documentation updated
- [ ] PDA team notified of new Info Code availability

---

### Story 2.2: Enable Info Code Assignment Creation for Concierge Provider (Practitioner Level)

**As a** Provider Data Administrator
**I want** to assign the "Concierge Provider" Info Code to individual practitioner accounts
**So that** patients can identify concierge practitioners in Provider Directory

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI**
   - PDA user can create PRM_InfoCodeAssignment__c record from Practitioner Account page
   - PRM_InfoCode__c lookup shows "Concierge Provider" as selectable option
   - PRM_Account__c is auto-populated with current Practitioner Account
   - **Note:** Effective Date and Termination Date MAY be optional for external flag (depends on business requirements)
   - Save button persists the assignment

2. **Validation Rules**
   - PRM_InfoCode__c is required
   - PRM_Account__c OR PRM_HealthcareFacility__c must be populated (not both)
   - If dates are used: Termination date cannot be before effective date
   - Duplicate assignment prevention: Cannot create duplicate active assignment

3. **List View / Related List**
   - "Info Code Assignments" related list appears on Practitioner Account page (or separate related list for public vs internal codes)
   - List shows: Info Code Name, Effective Date (if used), Termination Date (if used)
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

4. **Assignment Visibility**
   - Assignments are visible to PDA team
   - Assignments feed to Provider Directory (Story 2.5)
   - Assignments do NOT feed to DART or Inquire Only (unless business requires both internal and external tracking)

#### Technical Considerations

- Same object and relationships as Story 1.2
- Page Layout: Related list may already exist from Epic 1; ensure "Concierge Provider" is visible
- Consider: Do external assignments need effective/termination dates, or just a simple on/off flag?

#### Dependencies

- Story 2.1 completed ("Concierge Provider" Info Code exists)
- PRM_InfoCodeAssignment__c object access
- Practitioner Account page layout editable

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practitioner
- [ ] "Concierge Provider" Info Code is selectable
- [ ] Validation rules work correctly
- [ ] Related list displays assignments on Practitioner page
- [ ] Unit tests pass
- [ ] UAT completed by PDA team

---

### Story 2.3: Enable Info Code Assignment Creation for Concierge Provider (Practice Location Level)

**As a** Provider Data Administrator
**I want** to assign the "Concierge Provider" Info Code to practice locations (HealthcareFacility)
**So that** patients can identify concierge practice locations in Provider Directory

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Info Code Assignment

#### Acceptance Criteria

1. **Assignment Creation UI**
   - PDA user can create PRM_InfoCodeAssignment__c record from HealthcareFacility (Practice Location) page
   - PRM_InfoCode__c lookup shows "Concierge Provider" as selectable option
   - PRM_HealthcareFacility__c is auto-populated with current Practice Location
   - Save button persists the assignment

2. **Validation Rules**
   - Same validation rules as Story 2.2
   - PRM_HealthcareFacility__c is populated (PRM_Account__c is null for practice-level assignment)

3. **List View / Related List**
   - "Info Code Assignments" related list appears on Practice Location page
   - List shows: Info Code Name, dates (if applicable)
   - List is sortable and filterable
   - PDA team can edit or delete assignments from list

4. **Assignment Visibility**
   - Assignments are visible to PDA team
   - Assignments feed to Provider Directory (Story 2.5)

5. **Use Case Guidance**
   - Field help text clarifies: "Assign at Practice Location level when the entire practice operates as concierge"

#### Technical Considerations

- Same as Story 2.2 but for HealthcareFacility object
- Page Layout: Add or ensure "Info Code Assignments" related list on Practice Location layout

#### Dependencies

- Story 2.1 completed ("Concierge Provider" Info Code exists)
- PRM_InfoCodeAssignment__c object access
- Practice Location page layout editable

#### Definition of Done

- [ ] PDA user can create Info Code Assignment for Practice Location
- [ ] "Concierge Provider" Info Code is selectable
- [ ] Validation rules work correctly
- [ ] Related list displays assignments on Practice Location page
- [ ] Help text clarifies practice-level use case
- [ ] Unit tests pass
- [ ] UAT completed by PDA team

---

### Story 2.4: Improve UX for Managing Concierge Provider Info Code Assignments

**As a** Provider Data Administrator
**I want** a user-friendly interface for managing Concierge Provider Info Code Assignments
**So that** I can quickly add/remove concierge status without navigating through multiple screens

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - UX Enhancement

#### Acceptance Criteria

1. **Quick Action Button**
   - "Manage Concierge Status" quick action button on Practitioner and Practice Location pages
   - Button opens modal/component for inline editing of "Concierge Provider" assignment
   - User can toggle concierge status on/off (creates or terminates Info Code Assignment)
   - Changes save immediately with confirmation message

2. **Inline Editing (Optional Enhancement)**
   - Lightning component embedded on provider page shows current concierge status
   - Component displays: "Concierge Provider: Yes" or "Concierge Provider: No"
   - Click to edit toggles status and creates/terminates assignment
   - Visual indicator (badge, icon) shows concierge status at a glance

3. **Bulk Management (Optional Enhancement)**
   - List view action: "Manage Concierge Status" for multiple providers
   - PDA user selects multiple providers from list
   - Bulk action creates Info Code Assignments for selected providers
   - Confirmation screen shows preview before saving

4. **User Experience**
   - All actions complete within 3 clicks
   - Success/error messages display clearly
   - Help text explains concierge provider definition
   - Consistent with other Info Code management UX

#### Technical Considerations

- Lightning Web Component or Aura Component for quick action
- Apex controller for creating/terminating Info Code Assignments
- Bulkification for bulk actions
- UI/UX design review and approval

#### Dependencies

- Stories 2.1, 2.2, 2.3 completed (Info Code and Assignments exist)
- Lightning component development resources
- UX design mockups approved

#### Definition of Done

- [ ] Quick action implemented and tested
- [ ] Inline editing component deployed (if included)
- [ ] Bulk action implemented and tested (if included)
- [ ] User experience validated by PDA team
- [ ] Performance testing completed (< 2 seconds for typical actions)
- [ ] UAT completed by PDA team
- [ ] User guide updated with new UX features

---

### Story 2.5: Configure Provider Directory Feed to Include Concierge Provider Info Code Assignments

**As a** Integration Engineer
**I want** the external Concierge Provider Info Code Assignments to feed correctly to the Provider Directory
**So that** patients and members can identify concierge providers when searching for care

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / Provider Directory

#### Acceptance Criteria

1. **Feed Configuration**
   - PIE-to-Provider Directory feed includes PRM_InfoCodeAssignment__c records WHERE PRM_InfoCode__r.Name = 'Concierge Provider'
   - Feed includes: Account (Practitioner), HealthcareFacility (Practice Location), assignment status (active/inactive)
   - Field mapping is correct (PIE field → Provider Directory target field)
   - Data type compatibility verified (boolean/yes-no flag or Info Code name)
   - Null values are handled appropriately (e.g., no assignment = not concierge)
   - Feed configuration is documented

2. **Data Synchronization**
   - Initial full load transfers all existing "Concierge Provider" Info Code Assignments to Provider Directory
   - Incremental updates capture new/changed/terminated assignments within expected timeframe (e.g., within 24 hours)
   - Test: Create new assignment in PIE → verify appears in Provider Directory within SLA
   - Test: Terminate assignment in PIE → verify removed from Provider Directory within SLA
   - Verify 10+ sample records in Provider Directory match PIE source

3. **Provider Directory Display**
   - Info Code Assignment appears in provider search results (if applicable)
   - Info Code Assignment appears on provider detail page in Provider Directory
   - Labeled appropriately for consumer audience (e.g., "Concierge Medicine", "Concierge Practice")
   - Visual design is consistent with Provider Directory standards (badge, icon, or text label)

4. **Feed Reliability**
   - Error handling and retry logic is in place
   - Feed failures trigger alerts to appropriate team
   - Monitoring dashboard shows feed health metrics
   - Feed SLA is defined and documented

5. **Testing in Test Environment**
   - Feed tested end-to-end in Test environment (PIE → Provider Directory Test)
   - Test scenarios: new provider with assignment, update existing provider, assignment active→terminated, assignment terminated→active
   - All test scenarios pass successfully

6. **Exclusion from DART / Inquire Only**
   - Verify "Concierge Provider" Info Code Assignments do NOT feed to DART or Inquire Only (unless business requires both)
   - Feed configuration explicitly separates internal vs external Info Codes

#### Technical Considerations

- ETL Pipeline: Update existing PIE-to-Provider Directory pipeline
- Query: `SELECT Id, PRM_Account__c, PRM_Account__r.Name, PRM_HealthcareFacility__c, PRM_HealthcareFacility__r.Name, (derive IsActive: PRM_TerminationDate__c IS NULL OR PRM_TerminationDate__c > TODAY) FROM PRM_InfoCodeAssignment__c WHERE PRM_InfoCode__r.Name = 'Concierge Provider'`
- Timing: Coordinate feed schedule to minimize latency
- Performance: Monitor feed performance impact
- Rollback Plan: Document rollback procedure if feed issues occur
- Consumer UX: Ensure label/display is appropriate for patient audience

#### Dependencies

- Stories 2.1, 2.2, 2.3 completed (Info Code and Assignments exist)
- Provider Directory target field/table created (or existing table extended)
- Provider Directory team coordination required
- ETL infrastructure available

#### Definition of Done

- [ ] Feed configuration updated and tested in Test environment
- [ ] Data mapping documented and approved
- [ ] Initial full load completed in Test
- [ ] Incremental updates tested in Test
- [ ] End-to-end test scenarios pass (PIE → Provider Directory Test)
- [ ] Provider Directory display verified in Test
- [ ] Exclusion from DART/Inquire Only verified
- [ ] Monitoring and alerting configured
- [ ] Provider Directory team sign-off
- [ ] Ready for Production deployment

---

### Story 2.6: Deploy Concierge Provider Info Code to Production and Update Provider Directory

**As a** Release Manager
**I want** to deploy all Concierge Provider Info Code changes to Production
**So that** the public-facing Provider Directory shows accurate concierge provider information

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Production Deployment

#### Acceptance Criteria

1. **Pre-Deployment Checklist**
   - All Test environment testing completed successfully (Stories 2.1-2.5)
   - UAT sign-off received from PDA team
   - UAT sign-off received from Provider Directory team
   - Deployment plan reviewed and approved
   - Rollback plan documented and ready
   - Communication plan executed (stakeholders notified of deployment window)

2. **Deployment Execution**
   - "Concierge Provider" Info Code deployed (metadata or data)
   - Related list configurations deployed (page layouts)
   - Lightning components deployed (if Story 2.4 included)
   - Feed configuration deployed (Provider Directory integration)
   - Deployment completes within planned maintenance window
   - Deployment checklist completed (all steps verified)

3. **Post-Deployment Verification**
   - Smoke testing completed in Production
   - PDA team can create "Concierge Provider" Info Code Assignments in Production
   - Sample of 5+ Info Code Assignments created and verified in Provider Directory
   - No errors in Production logs
   - Monitoring dashboards show green status

4. **Post-Deployment Communication**
   - Deployment success notification sent to stakeholders
   - Release notes published
   - User documentation updated and published
   - Training reminder sent to PDA team (if needed)

#### Technical Considerations

- Maintenance Window: Schedule during low-usage period
- Rollback: Have rollback plan ready (Info Code deactivation, feed rollback)
- Monitoring: Enhanced monitoring during and after deployment
- Support: Ensure support team is aware and ready to handle issues
- Documentation: Update production runbook

#### Dependencies

- All prior stories in Epic 2 completed (2.1-2.5)
- Change control approval received
- Deployment window scheduled
- Deployment team availability
- Stakeholder communication completed

#### Definition of Done

- [ ] Pre-deployment checklist completed
- [ ] Production deployment executed successfully
- [ ] Post-deployment smoke testing passed
- [ ] PDA team verified functionality in Production
- [ ] Provider Directory feed verified in Production
- [ ] Monitoring confirms system health
- [ ] Post-deployment communication sent
- [ ] Release notes published
- [ ] Deployment retrospective completed

---

### Story 2.7: Immediate Update of Provider Directory Tags/Display After Deployment

**As a** Provider Directory Administrator
**I want** to update/refresh provider tags or display elements in Provider Directory immediately after "Concierge Provider" Info Code deployment
**So that** the public-facing directory shows accurate, current concierge provider information ASAP

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** Provider Directory - Tag/Display Management

#### Acceptance Criteria

1. **Update Trigger**
   - Process initiated within 4 hours of Production deployment (Story 2.6)
   - Mechanism identified for updating display (batch job, API call, cache refresh, manual tag update, etc.)
   - Responsible person/team assigned and notified

2. **Update Execution**
   - All providers with active "Concierge Provider" Info Code Assignment are displayed as concierge in Provider Directory
   - Providers without assignment (or terminated assignment) do NOT show concierge indicator
   - Display naming is consistent (e.g., "Concierge Medicine", "Concierge Practice", badge/icon)
   - Update completion confirmed (count of concierge providers matches PIE source)

3. **Verification**
   - Spot-check 10+ providers in Provider Directory UI (concierge indicator displays correctly)
   - Search by concierge filter returns correct providers (if applicable)
   - Providers without Info Code Assignment do not show concierge indicator
   - Update process logged and auditable

4. **Stakeholder Communication**
   - Provider Directory team notified when update is complete
   - PDA team notified when update is complete
   - Business owner notified of successful completion
   - Any issues or discrepancies reported and documented

#### Technical Considerations

- Timing: Coordinate with Story 2.6 deployment timeline
- Batch Size: If large volume, consider batching to avoid system overload
- Error Handling: Document any providers that failed to update and remediation plan
- Monitoring: Monitor Provider Directory system health during update
- Rollback: Document display rollback process if needed

#### Dependencies

- Story 2.6 completed (Production deployment successful)
- Provider Directory display management system access
- Provider Directory team availability
- Update process documented

#### Definition of Done

- [ ] Update process initiated within 4 hours of Production deployment
- [ ] Update completed successfully
- [ ] Verification spot-checks passed (10+ providers)
- [ ] Count of concierge providers reconciled with PIE source
- [ ] Provider Directory search/filter working correctly (if applicable)
- [ ] Completion notification sent to stakeholders
- [ ] Any issues/discrepancies documented and resolved (or remediation plan created)
- [ ] Update process documented for future reference

---

## Cross-Epic Dependencies

### Integration Points

1. **Internal vs External Info Codes - Clear Distinction**
   - Epic 1 ("Concierge PCP") Info Code Assignments must NOT feed to Provider Directory
   - Epic 2 ("Concierge Provider") Info Code Assignments MUST feed to Provider Directory
   - Testing must verify this separation (Stories 1.4, 1.5, 2.5)
   - Feed configurations must explicitly filter by Info Code Name

2. **PDA Team Training**
   - Single training session can cover both Info Codes
   - PDA team must understand when to use "Concierge PCP" vs "Concierge Provider"
   - Documentation must clearly differentiate the two Info Codes

3. **Naming Clarity**
   - Internal Info Code: "Concierge PCP"
   - External Info Code: "Concierge Provider"
   - Clear naming prevents confusion

4. **Reporting Considerations**
   - Analytics team may need reports that show both Info Code types
   - Consider creating unified dashboard that displays both (internal use)
   - Query pattern: `WHERE PRM_InfoCode__r.Name IN ('Concierge PCP', 'Concierge Provider')`

5. **Testing Coordination**
   - Both epics should be tested together for end-to-end validation
   - Verify that both Info Code types can coexist on same practitioner/practice location
   - Verify that changes to one Info Code Assignment do not affect the other

6. **Trigger Coordination**
   - Single trigger (PRM_InfoCodeAssTrigger) handles both Info Code types
   - Trigger helper logic must differentiate behavior based on Info Code Name
   - Avoid duplicate processing when both assignments exist

---

## Technical Considerations

### Architecture

```
PIE (Source of Truth)
├── PRM_InfoCode__c (Master Records)
│   ├── "Concierge PCP" (Internal)
│   └── "Concierge Provider" (External)
│
├── PRM_InfoCodeAssignment__c (Assignments)
│   ├── Practitioner-level assignments (PRM_Account__c)
│   └── Practice Location-level assignments (PRM_HealthcareFacility__c)
│
└── Triggers & Helpers
    └── PRM_InfoCodeAssTrigger → PRM_InfoCodeAssTriggerHelper

Downstream Systems
├── DART (receives "Concierge PCP" assignments only)
├── Inquire Only (receives "Concierge PCP" assignments only)
└── Provider Directory (receives "Concierge Provider" assignments only)
```

### Data Isolation

| Info Code | Feeds To | Does NOT Feed To |
|-----------|----------|------------------|
| Concierge PCP (Internal) | DART, Inquire Only | Provider Directory |
| Concierge Provider (External) | Provider Directory | DART, Inquire Only (unless business requires) |

### Security & Access Control

- **PDA Team**: Create, edit, delete Info Code Assignments for both Info Code types
- **Internal Users**: View "Concierge PCP" assignments via DART/Inquire Only
- **Public**: View "Concierge Provider" assignments via Provider Directory
- **Object-Level Security**: Info Code and Info Code Assignment objects accessible to PDA team
- **Field-Level Security**: Not required (security via object-level and data feeds)

### Data Model - Info Code Assignment Fields

| Field | Type | Purpose |
|-------|------|---------|
| PRM_InfoCode__c | Lookup | Link to Info Code master ("Concierge PCP" or "Concierge Provider") |
| PRM_Account__c | Lookup | Practitioner Account (for practitioner-level assignment) |
| PRM_HealthcareFacility__c | Lookup | Practice Location (for practice-level assignment) |
| PRM_EffectiveDate__c | Date | When concierge status became effective |
| PRM_TerminationDate__c | Date | When concierge status ended (null = currently active) |
| PRM_Pending__c | Checkbox | If assignment is pending (used in case workflows) |
| PRM_CaseManager__c | Lookup | Case Manager if assignment created via case flow (optional) |

### Performance

- **Database Indexing**: Index PRM_InfoCode__c, PRM_Account__c, PRM_HealthcareFacility__c, PRM_EffectiveDate__c, PRM_TerminationDate__c for query performance
- **Feed Optimization**: Ensure feeds only query delta (new/changed assignments) after initial full load
- **Caching**: Provider Directory may cache Info Code Assignment data; define cache refresh strategy
- **Query Optimization**: Use selective queries with Info Code Name filter

### Testing Strategy

- **Unit Tests**: Trigger logic, validation rules, assignment creation/deletion
- **Integration Tests**: Feeds to DART, Inquire Only, Provider Directory
- **End-to-End Tests**: PDA workflow from assignment creation → downstream system display
- **Performance Tests**: Feed performance, search performance in downstream systems, trigger performance (200+ records)
- **Security Tests**: Verify "Concierge PCP" does not appear in Provider Directory; "Concierge Provider" appears correctly
- **Data Quality Tests**: Validation rules, date logic, duplicate prevention
- **UAT**: PDA team, Analytics team, Provider Directory team, Customer Service team

---

## Definition of Done

### Story-Level Definition of Done

Each user story is considered done when:

- [ ] Acceptance criteria met (all criteria pass)
- [ ] Code implemented and unit tests written (if applicable)
- [ ] Code review completed (2+ reviewers)
- [ ] Integration tests pass (if applicable)
- [ ] Deployed to Test environment
- [ ] UAT completed by relevant stakeholders (sign-off received)
- [ ] Documentation updated (technical and user documentation)
- [ ] No critical or high-priority bugs remaining
- [ ] Performance benchmarks met
- [ ] Security review completed (if applicable)

### Epic-Level Definition of Done

Each epic is considered done when:

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

### Test Scenarios - Epic 1 (Internal Concierge PCP Info Code)

#### Scenario 1: PDA User Creates Concierge PCP Info Code Assignment (Practitioner Level)

**Given** a PDA user is viewing a Practitioner Account in PIE
**When** the user creates a new Info Code Assignment with Info Code = "Concierge PCP", Effective Date = 01/01/2026
**Then** the Info Code Assignment is saved successfully
**And** the assignment appears in DART within [defined timeframe]
**And** the assignment appears in Inquire Only within [defined timeframe]
**And** the assignment does NOT appear in Provider Directory

#### Scenario 2: PDA User Creates Concierge PCP Info Code Assignment (Practice Location Level)

**Given** a PDA user is viewing a Practice Location (HealthcareFacility) in PIE
**When** the user creates a new Info Code Assignment with Info Code = "Concierge PCP", Effective Date = 01/01/2026
**Then** the Info Code Assignment is saved successfully
**And** the assignment appears in DART within [defined timeframe]
**And** the assignment appears in Inquire Only within [defined timeframe]
**And** the assignment does NOT appear in Provider Directory

#### Scenario 3: Date Validation

**Given** a PDA user is creating a Concierge PCP Info Code Assignment
**When** the user enters a Termination Date that is before the Effective Date
**Then** the system displays an error message
**And** the save operation is blocked

#### Scenario 4: Duplicate Assignment Prevention

**Given** a Practitioner Account already has an active Concierge PCP Info Code Assignment (no Termination Date)
**When** a PDA user tries to create another Concierge PCP assignment for the same practitioner
**Then** the system displays an error message: "Duplicate active assignment not allowed"
**And** the save operation is blocked

#### Scenario 5: Reporting in DART

**Given** the Concierge PCP dashboard in DART
**When** a user views the dashboard
**Then** the dashboard shows accurate counts of active Concierge PCPs (based on Info Code Assignments)
**And** the trend line shows historical changes over time

#### Scenario 6: Terminate Concierge PCP Status

**Given** a Practitioner has an active Concierge PCP Info Code Assignment
**When** a PDA user edits the assignment and sets Termination Date = 12/31/2025
**Then** the assignment is saved with the termination date
**And** DART shows the practitioner as no longer active Concierge PCP (after feed refresh)

---

### Test Scenarios - Epic 2 (External Concierge Provider Info Code)

#### Scenario 1: PDA User Creates Concierge Provider Info Code Assignment (Practitioner Level)

**Given** a PDA user is viewing a Practitioner Account in PIE
**When** the user creates a new Info Code Assignment with Info Code = "Concierge Provider"
**Then** the Info Code Assignment is saved successfully
**And** the assignment appears in Provider Directory within [defined timeframe]
**And** the assignment does NOT appear in DART or Inquire Only (unless both are configured)

#### Scenario 2: PDA User Creates Concierge Provider Info Code Assignment (Practice Location Level)

**Given** a PDA user is viewing a Practice Location in PIE
**When** the user creates a new Info Code Assignment with Info Code = "Concierge Provider"
**Then** the Info Code Assignment is saved successfully
**And** the assignment appears in Provider Directory within [defined timeframe]

#### Scenario 3: Provider Directory Display

**Given** a Practitioner has an active Concierge Provider Info Code Assignment in PIE
**When** a patient searches for the practitioner in Provider Directory
**Then** the practitioner profile shows a "Concierge Medicine" indicator (badge, icon, or text label)
**And** the practitioner can be found by filtering for concierge providers (if filter exists)

#### Scenario 4: Quick Action UX (Story 2.4)

**Given** a PDA user is viewing a Practitioner Account page
**When** the user clicks "Manage Concierge Status" quick action button
**Then** a modal opens showing current status and toggle option
**When** the user toggles concierge status to "On" and saves
**Then** a new "Concierge Provider" Info Code Assignment is created with today's date as Effective Date
**And** a success message displays

#### Scenario 5: Remove Concierge Provider Status

**Given** a Practitioner has an active Concierge Provider Info Code Assignment
**When** a PDA user deletes the assignment or sets a Termination Date
**Then** the assignment is terminated
**And** the practitioner no longer shows as concierge in Provider Directory (after feed refresh)

---

### Cross-Epic Test Scenarios

#### Scenario 1: Both Info Code Assignments on Same Practitioner

**Given** a Practitioner has both "Concierge PCP" (internal) and "Concierge Provider" (external) Info Code Assignments
**When** a PDA user views the Practitioner Account in PIE
**Then** both assignments are visible in the Info Code Assignments related list
**And** changes to one assignment do not affect the other

#### Scenario 2: Internal Info Code Does Not Leak to Provider Directory

**Given** a Practitioner has "Concierge PCP" (internal) Info Code Assignment = active
**And** the Practitioner has "Concierge Provider" (external) Info Code Assignment = not present (or terminated)
**When** Provider Directory is viewed
**Then** the Practitioner does NOT appear as a concierge provider
**And** only the external Info Code Assignment influences Provider Directory display

#### Scenario 3: DART Only Shows Internal Info Code Assignments

**Given** a Practitioner has both "Concierge PCP" and "Concierge Provider" Info Code Assignments
**When** the DART reporting dashboard is viewed
**Then** only the "Concierge PCP" Info Code Assignment data is displayed in DART
**And** the external "Concierge Provider" assignment does not appear in DART

#### Scenario 4: Trigger Fires for Both Info Code Types

**Given** a PDA user creates both "Concierge PCP" and "Concierge Provider" Info Code Assignments for the same practitioner in quick succession
**When** PRM_InfoCodeAssTrigger fires
**Then** trigger processes both assignments correctly
**And** no errors occur
**And** both assignments are visible in PIE and feed to their respective downstream systems

---

## Data Model Comparison

### Old Approach (Field-Based) vs New Approach (Info Code-Based)

| Aspect | Old Approach (Fields) | New Approach (Info Codes) |
|--------|----------------------|---------------------------|
| **Schema Changes** | Add PRM_ConciergePCP__c, PRM_ConciergeProvider__c, PRM_ConciergePCP_EffectiveDate__c, PRM_ConciergePCP_TerminationDate__c fields on Account and HealthcareFacility | **No schema changes** - use existing PRM_InfoCodeAssignment__c |
| **Date Tracking** | Separate fields for each flag | **Single pattern** - Effective Date and Termination Date on Info Code Assignment |
| **Audit Trail** | Field history tracking (limited) | **Full object history** - Info Code Assignment creation/deletion/changes |
| **Rollup Logic** | Custom Apex for each flag | **Reuse existing trigger** (PRM_InfoCodeAssTrigger) |
| **Integration Feeds** | Query Account/HealthcareFacility fields | **Query Info Code Assignments** filtered by Info Code Name |
| **Flexibility** | Hard-coded fields; difficult to add new types | **Highly flexible** - add new Info Codes without schema changes |
| **Data Quality** | Validation rules on multiple fields | **Single validation pattern** on Info Code Assignment |
| **UX** | Fields on object page layouts | **Consistent UX** - Info Code Assignment related list + quick actions |
| **Maintenance** | Field-level security, page layouts, profiles | **Object-level security** - simpler permission model |
| **Proven Pattern** | New pattern | **Proven pattern** - already used for PNC and Delegated |

**Recommendation:** Info Code approach is **superior** in every aspect.

---

## Appendix: Field Reference

### PRM_InfoCode__c (Master)

| Field | Type | Purpose |
|-------|------|---------|
| Name | Text | Info Code name (e.g., "Concierge PCP", "Concierge Provider") |
| PRM_InfoCodeType__c | Picklist | Type/category (e.g., "Provider Attribute") |
| PRM_IsActive__c | Checkbox | Is this Info Code active? |
| Description | Long Text | Purpose and usage of Info Code |
| PRM_InternalOnly__c (optional) | Checkbox | Is this Info Code internal-only? (for "Concierge PCP") |
| PRM_PublicFacing__c (optional) | Checkbox | Is this Info Code public-facing? (for "Concierge Provider") |

### PRM_InfoCodeAssignment__c (Junction)

| Field | Type | Purpose |
|-------|------|---------|
| PRM_InfoCode__c | Lookup (PRM_InfoCode__c) | Link to Info Code master |
| PRM_Account__c | Lookup (Account) | Practitioner Account (for practitioner-level assignment) |
| PRM_HealthcareFacility__c | Lookup (HealthcareFacility) | Practice Location (for practice-level assignment) |
| PRM_EffectiveDate__c | Date | When this assignment became effective |
| PRM_TerminationDate__c | Date | When this assignment ended (null = currently active) |
| PRM_Pending__c | Checkbox | Is this assignment pending (used in case workflows)? |
| PRM_CaseManager__c | Lookup (IndividualApplication) | Case Manager if assignment created via case flow |
| PRM_IsErrorRecord__c | Checkbox | Is this an error record? (for data quality) |

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **PIE** | Provider Information Exchange - the central system for managing provider data |
| **PDA Team** | Provider Data Administration Team - responsible for maintaining provider data accuracy |
| **Info Code** | Master record (PRM_InfoCode__c) representing a provider attribute or characteristic |
| **Info Code Assignment** | Junction record (PRM_InfoCodeAssignment__c) assigning an Info Code to a Practitioner or Practice Location |
| **DART** | Data Analytics and Reporting Tool - internal analytics platform |
| **Inquire Only** | Internal system used by customer service for viewing provider information |
| **Provider Directory** | Public-facing system where patients/members search for providers |
| **Concierge PCP** | Internal Info Code for tracking concierge primary care physicians (analytics only) |
| **Concierge Provider** | External Info Code displayed in Provider Directory (public-facing) |
| **Practitioner** | Individual doctor/provider (Account object, Person Account record type) |
| **Practice Location** | Group practice or facility where practitioners work (HealthcareFacility object) |
| **Effective Date** | Date when a provider started operating under concierge medicine model |
| **Termination Date** | Date when a provider stopped operating under concierge medicine model |
| **Active Assignment** | Info Code Assignment with no Termination Date or Termination Date > today |

---

**End of Document**

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-01 | Requirements Analysis | Initial creation of user stories (field-based approach) |
| 2.0 | 2026-04-01 | Requirements Analysis | **Complete rewrite using Info Code approach** (following PNC/Delegated pattern) |

---

## Next Steps

1. **Review and Approval**: Present this Info Code approach to product owner and key stakeholders; compare benefits vs. field-based approach
2. **Decision**: Confirm Info Code approach is approved (strongly recommended)
3. **Technical Design**: Detailed technical design for trigger logic, feed configurations, rollup rules (if any)
4. **Story Estimation**: Conduct planning poker or similar estimation session with development team to validate story points
5. **Prioritization**: Finalize story prioritization within each epic with product owner
6. **Sprint Planning**: Assign stories to sprints based on team capacity and dependencies
7. **Kickoff**: Conduct epic kickoff meetings for Epic 1 and Epic 2 with all stakeholders
8. **Begin Development**: Start with highest-priority stories (Story 1.1, 2.1) after approval
