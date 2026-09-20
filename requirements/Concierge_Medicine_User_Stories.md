# Concierge Medicine Provider Flag Implementation - User Stories

**Document Version:** 1.0
**Created Date:** April 1, 2026
**Project:** PIE & Provider Directory Enhancement - Concierge Medicine Provider Tracking

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Epic Overview](#epic-overview)
3. [User Stories - Epic 1: Internal Concierge PCP Flag](#user-stories---epic-1-internal-concierge-pcp-flag)
4. [User Stories - Epic 2: External Concierge Provider Flag Migration](#user-stories---epic-2-external-concierge-provider-flag-migration)
5. [Cross-Epic Dependencies](#cross-epic-dependencies)
6. [Technical Considerations](#technical-considerations)
7. [Definition of Done](#definition-of-done)
8. [Acceptance Testing Strategy](#acceptance-testing-strategy)

---

## Executive Summary

This document outlines detailed user stories for implementing two distinct concierge medicine provider flags in the PIE (Provider Information Exchange) system:

1. **Internal Flag**: "Concierge PCP" - For internal data analytics and reporting (DART/Inquire Only)
2. **External Flag**: "Concierge Provider" - For public-facing Provider Directory

Both flags support date tracking, PDA team editing capabilities, and can be applied at practitioner or practice levels.

---

## Epic Overview

### Epic 1: Internal Concierge PCP Flag in PIE

**Epic Goal:** Implement an internal-only "Concierge PCP" flag in PIE that feeds to DART and Inquire Only systems for analytics and reporting, with date tracking and PDA edit capabilities.

**Business Value:** Enable data-driven insights into concierge medicine providers without exposing this information publicly.

**Priority:** High
**Estimated Story Points:** 34

---

### Epic 2: External Concierge Provider Flag Migration

**Epic Goal:** Migrate and improve the existing "Concierge Medicine Provider Only" flag by relocating it to a user-friendly location, renaming it, and ensuring proper propagation to Provider Directory.

**Business Value:** Improve user experience for managing public-facing concierge provider information and ensure accurate Provider Directory data.

**Priority:** High
**Estimated Story Points:** 21

---

## User Stories - Epic 1: Internal Concierge PCP Flag

### Story 1.1: Create Internal "Concierge PCP" Flag in PIE

**As a** PIE System Administrator
**I want** to create a new internal-only flag field named "Concierge PCP" in the PIE system
**So that** we can track concierge primary care physicians for internal analytics without exposing this data publicly

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Model

#### Acceptance Criteria

1. **Field Creation**
   - New checkbox/flag field "Concierge PCP" exists in PIE database
   - Field is labeled "Concierge PCP" in system (exact naming required)
   - Field metadata includes description: "Internal use only - identifies concierge primary care physicians"
   - Field is created for both Practitioner and Practice object types

2. **Internal-Only Configuration**
   - Flag is explicitly marked as "Internal Use Only" in field configuration
   - Flag does NOT appear in any Provider Directory feed configuration
   - Flag is explicitly excluded from external API responses
   - Documentation confirms internal-only status

3. **Data Integrity**
   - Field supports null/true/false states
   - Field has appropriate data validation rules
   - Field change history is tracked (audit trail enabled)
   - Field is included in PIE backup processes

#### Technical Considerations

- Database: Add column to both `Practitioner` and `Practice` tables
- Field Type: Boolean (nullable)
- Index: Consider indexing for reporting query performance
- Security: Implement field-level security to restrict visibility
- API: Exclude from external-facing GraphQL/REST schemas

#### Dependencies

- PIE database schema update approval
- Security model review and approval
- Data governance team sign-off on internal-only classification

#### Definition of Done

- [ ] Field created in PIE database (Practitioner and Practice tables)
- [ ] Field-level security configured (internal visibility only)
- [ ] Excluded from Provider Directory feed mapping
- [ ] Unit tests pass (field creation, validation, security)
- [ ] Database migration script reviewed and approved
- [ ] Technical documentation updated
- [ ] Code review completed and approved

---

### Story 1.2: Implement Effective Date Field for Concierge PCP Flag

**As a** Provider Data Administrator
**I want** to record when a provider became a concierge PCP using an "Effective Date" field
**So that** I can track the timeline of concierge practice transitions and generate accurate historical reports

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Data Model

#### Acceptance Criteria

1. **Field Specifications**
   - Field name: "Concierge PCP Effective Date"
   - Field type: Date (MM/DD/YYYY format)
   - Field is nullable (not required when flag is false)
   - Field exists for both Practitioner and Practice records

2. **Validation Rules**
   - Effective date cannot be in the future
   - If "Concierge PCP" flag is true, effective date should be present (warning if missing)
   - Date format validation: MM/DD/YYYY
   - Date must be valid calendar date

3. **User Experience**
   - Date picker UI component for easy date selection
   - Manual text entry supported with format validation
   - Clear format hint displayed (MM/DD/YYYY)
   - Appropriate error messages for invalid dates

4. **Data Relationships**
   - Effective date cannot be after termination date (if termination date exists)
   - System tracks who last modified the effective date
   - System tracks when effective date was last modified

#### Technical Considerations

- Database: Add `concierge_pcp_effective_date` column (Date type)
- Validation: Server-side validation for date logic
- UI: Implement date picker component (Lightning Design System or equivalent)
- Performance: Include in relevant indexes for date-range queries

#### Dependencies

- Story 1.1 must be completed (Concierge PCP flag exists)
- Date utility libraries/components available

#### Definition of Done

- [ ] Effective date field created in database
- [ ] Date validation rules implemented and tested
- [ ] UI date picker component integrated
- [ ] Edge cases tested (leap years, invalid dates, future dates)
- [ ] Field included in audit trail
- [ ] Unit and integration tests pass
- [ ] Documentation updated

---

### Story 1.3: Implement Termination Date Field for Concierge PCP Flag

**As a** Provider Data Administrator
**I want** to record when a provider stopped being a concierge PCP using a "Termination Date" field
**So that** I can track when providers exit concierge practice models and maintain accurate current state

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Data Model

#### Acceptance Criteria

1. **Field Specifications**
   - Field name: "Concierge PCP Termination Date"
   - Field type: Date (MM/DD/YYYY format)
   - Field is nullable (not required when flag is true)
   - Field exists for both Practitioner and Practice records

2. **Validation Rules**
   - Termination date cannot be in the future
   - Termination date cannot be before effective date (if effective date exists)
   - If termination date is present, system should prompt to uncheck "Concierge PCP" flag (warning/recommendation)
   - Date format validation: MM/DD/YYYY
   - Date must be valid calendar date

3. **Business Logic**
   - When termination date is entered and is in the past, consider auto-updating flag to false (with confirmation)
   - If flag is unchecked and no termination date exists, system prompts for termination date
   - Clear audit trail of when termination date was added/modified

4. **User Experience**
   - Date picker UI component for easy date selection
   - Manual text entry supported with format validation
   - Clear format hint displayed (MM/DD/YYYY)
   - Appropriate error messages for invalid dates
   - Warning message if termination date is set but flag is still checked

#### Technical Considerations

- Database: Add `concierge_pcp_termination_date` column (Date type)
- Business Rules Engine: Implement date cross-validation logic
- UI: Implement date picker component with validation feedback
- Reporting: Support "currently active" queries (effective date <= today AND (termination date IS NULL OR termination date > today))

#### Dependencies

- Story 1.1 must be completed (Concierge PCP flag exists)
- Story 1.2 must be completed (Effective date exists for cross-validation)
- Date utility libraries/components available

#### Definition of Done

- [ ] Termination date field created in database
- [ ] Date validation rules implemented (future dates, before effective date)
- [ ] Cross-field validation with effective date working
- [ ] UI date picker component integrated
- [ ] Warning messages display correctly
- [ ] Unit and integration tests pass (including edge cases)
- [ ] Documentation updated with business rules

---

### Story 1.4: Enable PDA Team Edit Access for Internal Concierge PCP Flag

**As a** Provider Data Administrator
**I want** to have edit permissions for the Concierge PCP flag and its associated dates
**So that** I can maintain accurate provider concierge status information in PIE

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Security & Permissions

#### Acceptance Criteria

1. **Permission Configuration**
   - PDA team role/profile has edit access to "Concierge PCP" flag
   - PDA team has edit access to "Concierge PCP Effective Date"
   - PDA team has edit access to "Concierge PCP Termination Date"
   - Other non-PDA users have read-only access (or no access based on security model)

2. **User Interface Access**
   - PDA team members can see edit controls for the flag and dates
   - Edit controls are visible on both Practitioner and Practice record pages
   - Changes are saved successfully without permission errors
   - Non-PDA users see read-only view (or no view if restricted)

3. **Security Testing**
   - PDA user can successfully update flag from false to true
   - PDA user can successfully enter effective date
   - PDA user can successfully enter termination date
   - Non-PDA user receives appropriate error message when attempting edit
   - Permission changes do not impact other PIE functionality

4. **Audit Trail**
   - All flag and date changes are logged with user ID
   - All changes include timestamp
   - Audit log includes before/after values

#### Technical Considerations

- Security: Configure field-level security or profile permissions
- Role Hierarchy: Ensure PDA team role is properly defined
- Testing: Create test users for PDA and non-PDA roles
- Documentation: Update security matrix documentation

#### Dependencies

- Stories 1.1, 1.2, 1.3 must be completed (fields exist)
- PDA team role/profile must be defined in system
- Security model review completed

#### Definition of Done

- [ ] Field-level security configured for PDA team
- [ ] Permission sets or profiles updated
- [ ] Security testing completed (positive and negative tests)
- [ ] Audit trail verified for all changes
- [ ] Non-PDA user restrictions verified
- [ ] Security documentation updated
- [ ] UAT sign-off from PDA team lead

---

### Story 1.5: Configure DART Integration for Internal Concierge PCP Flag

**As a** Data Analytics Team Member
**I want** the internal Concierge PCP flag and dates to feed into DART (Data Analytics and Reporting Tool)
**So that** I can analyze concierge provider trends and create executive reports

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / DART

#### Acceptance Criteria

1. **Data Feed Configuration**
   - Concierge PCP flag is included in PIE-to-DART data feed
   - Concierge PCP Effective Date is included in feed
   - Concierge PCP Termination Date is included in feed
   - Feed includes both Practitioner and Practice level data
   - Feed configuration is documented

2. **Data Mapping**
   - PIE field names correctly mapped to DART target fields
   - Data types are compatible (boolean for flag, date for dates)
   - Null values are handled appropriately
   - Field mapping document is created/updated

3. **Feed Schedule and Reliability**
   - Data refresh frequency is defined and documented
   - Initial full load successfully transfers all existing data
   - Incremental updates capture flag changes within expected timeframe
   - Error handling and retry logic is in place
   - Feed failures trigger appropriate alerts

4. **Data Validation in DART**
   - Sample of 10+ records verified in DART after feed
   - Flag values match PIE source data
   - Date values match PIE source data (format preserved)
   - DART reporting can filter/group by concierge status
   - DART can calculate "currently active concierge" providers

#### Technical Considerations

- ETL Pipeline: Update existing PIE-to-DART pipeline or create new
- Data Format: Ensure date format compatibility between systems
- Performance: Monitor feed performance impact
- Monitoring: Set up alerting for feed failures
- Documentation: Update data dictionary and feed specifications

#### Dependencies

- Stories 1.1, 1.2, 1.3 must be completed (fields exist)
- DART target schema must be updated to accept new fields
- ETL infrastructure must be available
- DART team coordination required

#### Definition of Done

- [ ] PIE-to-DART feed configuration updated
- [ ] Field mapping documented and approved
- [ ] Initial full data load completed successfully
- [ ] Incremental update tested and verified
- [ ] Data validation completed (sample records verified)
- [ ] Monitoring and alerting configured
- [ ] DART team sign-off received
- [ ] Technical documentation updated

---

### Story 1.6: Configure "Inquire Only" System Integration for Internal Concierge PCP Flag

**As a** Customer Service Representative
**I want** to view the internal Concierge PCP flag and dates in the "Inquire Only" system
**So that** I can provide accurate information when responding to internal inquiries about provider concierge status

**Priority:** P1 - High
**Story Points:** 5
**Component:** PIE - Data Integration / Inquire Only System

#### Acceptance Criteria

1. **Data Feed Configuration**
   - Concierge PCP flag is included in PIE-to-Inquire Only feed
   - Concierge PCP Effective Date is included in feed
   - Concierge PCP Termination Date is included in feed
   - Feed includes both Practitioner and Practice level data
   - Feed configuration is documented

2. **User Interface Display**
   - Flag and dates are visible in provider detail view
   - Fields are clearly labeled ("Concierge PCP", "Effective Date", "Termination Date")
   - Dates are formatted consistently (MM/DD/YYYY)
   - Visual indicator shows current status (active/inactive based on dates)
   - Data is read-only (no edit capability in Inquire Only)

3. **Search and Filter Capability**
   - Users can search for providers with Concierge PCP flag = true
   - Users can filter by date ranges (effective date, termination date)
   - Search results display concierge status clearly
   - Search performance is acceptable (< 3 seconds for typical queries)

4. **Data Synchronization**
   - Data refresh frequency is defined and documented
   - Data in Inquire Only matches PIE source within acceptable lag time
   - Updates to flag/dates in PIE appear in Inquire Only within expected timeframe
   - Error handling for feed failures is in place

#### Technical Considerations

- Integration: Update existing PIE-to-Inquire Only integration
- UI: Update Inquire Only UI to display new fields
- Performance: Ensure search/filter queries are optimized
- Caching: Consider caching strategy if applicable
- Documentation: Update Inquire Only user guide

#### Dependencies

- Stories 1.1, 1.2, 1.3 must be completed (fields exist)
- Inquire Only system access for testing
- Inquire Only development team coordination
- UI mockups/wireframes approved

#### Definition of Done

- [ ] PIE-to-Inquire Only feed configuration updated
- [ ] UI changes implemented and tested
- [ ] Search and filter functionality tested
- [ ] Data synchronization verified
- [ ] Performance testing completed
- [ ] User acceptance testing completed by CSR team
- [ ] User guide updated
- [ ] Technical documentation updated

---

### Story 1.7: Implement Practitioner-Level Concierge PCP Flag Application

**As a** Provider Data Administrator
**I want** to apply the Concierge PCP flag at the individual practitioner level
**So that** I can accurately track concierge status for specific doctors regardless of their practice affiliations

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Business Logic

#### Acceptance Criteria

1. **Practitioner Record Support**
   - Concierge PCP flag can be set on individual Practitioner records
   - Effective Date can be set on Practitioner record
   - Termination Date can be set on Practitioner record
   - All validation rules apply at practitioner level
   - Practitioner-level flag is independent of practice-level flag

2. **User Interface**
   - Flag and date fields appear on Practitioner detail page
   - Fields are in logical grouping/section (e.g., "Concierge Practice Information")
   - Edit mode allows PDA team to modify values
   - Changes save successfully
   - Success/error messages display appropriately

3. **Business Logic**
   - Practitioner-level flag does not automatically propagate to practice
   - If practitioner is marked as concierge, this status follows them across all practice locations
   - Reporting can distinguish between practitioner-level and practice-level flags
   - Practitioner-level flag takes precedence in reporting (if both exist)

4. **Data Feeds**
   - Practitioner-level flag feeds to DART correctly
   - Practitioner-level flag feeds to Inquire Only correctly
   - Practitioner-level flag does NOT feed to Provider Directory (internal only)

#### Technical Considerations

- UI Layout: Integrate fields into existing practitioner detail page
- Business Rules: Clarify precedence rules when both practitioner and practice flags exist
- Reporting: Ensure reporting queries can differentiate source (practitioner vs practice)
- Testing: Test various scenarios (practitioner only, practice only, both, neither)

#### Dependencies

- Stories 1.1, 1.2, 1.3, 1.4 must be completed
- Story 1.5 and 1.6 feed configurations must support practitioner-level data

#### Definition of Done

- [ ] Flag and dates display on practitioner record page
- [ ] PDA team can edit values on practitioner record
- [ ] Validation rules work correctly
- [ ] Practitioner-level data feeds to DART
- [ ] Practitioner-level data feeds to Inquire Only
- [ ] Practitioner-level data does NOT feed to Provider Directory (verified)
- [ ] Unit and integration tests pass
- [ ] UAT completed by PDA team

---

### Story 1.8: Implement Practice-Level Concierge PCP Flag Application

**As a** Provider Data Administrator
**I want** to apply the Concierge PCP flag at the practice level (when all PCPs are concierge)
**So that** I can efficiently manage concierge status for practices where the entire primary care team operates under a concierge model

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Business Logic

#### Acceptance Criteria

1. **Practice Record Support**
   - Concierge PCP flag can be set on Practice records
   - Effective Date can be set on Practice record
   - Termination Date can be set on Practice record
   - All validation rules apply at practice level
   - Practice-level flag is independent of practitioner-level flags

2. **User Interface**
   - Flag and date fields appear on Practice detail page
   - Fields are in logical grouping/section (e.g., "Practice-Wide Settings" or "Concierge Practice Information")
   - Edit mode allows PDA team to modify values
   - Changes save successfully
   - Success/error messages display appropriately

3. **Business Logic & Use Case**
   - Practice-level flag is appropriate when ALL PCPs at practice are concierge
   - Help text / field description clarifies this use case
   - Practice-level flag does not automatically propagate to individual practitioners
   - Warning message if trying to set practice-level flag when some practitioners are NOT marked concierge (data quality check)

4. **Data Feeds**
   - Practice-level flag feeds to DART correctly
   - Practice-level flag feeds to Inquire Only correctly
   - Practice-level flag does NOT feed to Provider Directory (internal only)
   - Reporting can distinguish between practitioner-level and practice-level flags

#### Technical Considerations

- UI Layout: Integrate fields into existing practice detail page
- Data Quality: Consider implementing check that compares practice-level flag to practitioner-level flags (warning if mismatch)
- Reporting: Ensure reporting can aggregate both practitioner and practice level appropriately
- Documentation: Clearly document when to use practice-level vs practitioner-level

#### Dependencies

- Stories 1.1, 1.2, 1.3, 1.4 must be completed
- Story 1.5 and 1.6 feed configurations must support practice-level data
- Story 1.7 completed (to understand interaction between levels)

#### Definition of Done

- [ ] Flag and dates display on practice record page
- [ ] PDA team can edit values on practice record
- [ ] Validation rules work correctly
- [ ] Help text clarifies when to use practice-level flag
- [ ] Practice-level data feeds to DART
- [ ] Practice-level data feeds to Inquire Only
- [ ] Practice-level data does NOT feed to Provider Directory (verified)
- [ ] Data quality warning implemented (if applicable)
- [ ] Unit and integration tests pass
- [ ] UAT completed by PDA team

---

### Story 1.9: Create Internal Reporting Dashboard for Concierge PCP Analytics

**As a** Healthcare Analytics Manager
**I want** a dedicated reporting dashboard showing concierge PCP trends and statistics
**So that** I can monitor the growth of concierge medicine in our network and make data-driven business decisions

**Priority:** P2 - Medium
**Story Points:** 5
**Component:** DART - Reporting

#### Acceptance Criteria

1. **Dashboard Metrics**
   - Total count of active concierge PCPs (currently active)
   - Total count of historical concierge PCPs (all time)
   - Total count of practices with concierge flag
   - Trend over time (new concierge PCPs by month/quarter)
   - Terminations over time (concierge PCPs who stopped by month/quarter)
   - Average duration of concierge practice

2. **Filtering and Segmentation**
   - Filter by date range (effective date, termination date)
   - Filter by practitioner vs practice level
   - Filter by geographic region/state (if available)
   - Filter by specialty (if available)

3. **Visualizations**
   - Line chart: Concierge PCP count trend over time
   - Bar chart: New concierge PCPs by month/quarter
   - Pie chart: Active vs inactive concierge PCPs
   - Table: List of all concierge PCPs with key details (name, effective date, termination date, status)

4. **Export and Sharing**
   - Dashboard can be exported to PDF
   - Dashboard can be exported to Excel
   - Dashboard can be scheduled for automated email delivery
   - Dashboard link can be shared with appropriate stakeholders

#### Technical Considerations

- Platform: Build in DART's native reporting tool
- Data Source: Use data from Story 1.5 (DART integration)
- Performance: Optimize queries for acceptable load time (< 5 seconds)
- Security: Restrict access to internal users only
- Refresh: Define data refresh schedule

#### Dependencies

- Story 1.5 must be completed (DART integration with data flowing)
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

### Story 1.10: Develop Data Quality Rules for Concierge PCP Flag Integrity

**As a** Data Governance Lead
**I want** automated data quality rules and alerts for the Concierge PCP flag and dates
**So that** I can ensure data integrity and prevent invalid data states

**Priority:** P2 - Medium
**Story Points:** 4
**Component:** PIE - Data Quality

#### Acceptance Criteria

1. **Validation Rules Implemented**
   - Rule: If Concierge PCP flag = true, effective date should be present (warning)
   - Rule: Termination date cannot be before effective date (error)
   - Rule: Dates cannot be in the future (error)
   - Rule: If termination date is in the past, flag should be false (warning)
   - Rule: If flag = false and termination date is null, consider requiring termination date if effective date exists (warning)

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
   - PDA team can bulk fix common issues (if applicable)
   - Audit trail tracks when violations were resolved
   - Metrics show trend of data quality improvement over time

#### Technical Considerations

- Validation Engine: Leverage existing PIE validation framework
- Batch Processing: Schedule daily DQ job during off-peak hours
- Performance: Ensure DQ checks don't significantly impact save operations
- Notification: Use existing email notification system
- Dashboard: Consider embedding in existing DQ dashboard if available

#### Dependencies

- Stories 1.1, 1.2, 1.3 must be completed (fields and basic validation exist)
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

## User Stories - Epic 2: External Concierge Provider Flag Migration

### Story 2.1: Analyze Current "Concierge Medicine Provider Only" Flag Usage

**As a** Business Analyst
**I want** to analyze the current usage and location of the "Concierge Medicine Provider Only" flag
**So that** I can document existing dependencies and plan a safe migration

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Analysis

#### Acceptance Criteria

1. **Current State Documentation**
   - Document exact current location of flag (Locations/Properties tab, specific section)
   - Document current field name exactly as it appears
   - Screenshot of current UI location
   - Document field type and allowed values
   - Document if flag exists on practitioner, practice, or both

2. **Usage Analysis**
   - Count of records with flag = true (current usage volume)
   - Count of records with flag = false
   - Count of records with flag = null/empty
   - Identify users who currently access/edit this flag
   - Document frequency of updates (how often is it changed)

3. **Dependency Analysis**
   - List all downstream systems that consume this flag
   - Confirm whether flag currently feeds to Provider Directory
   - Identify any reports, dashboards, or queries using this flag
   - Identify any automated processes or integrations using this flag
   - Document any business rules or workflows triggered by this flag

4. **Stakeholder Identification**
   - Identify all teams that use this flag
   - Identify all systems that depend on this flag
   - Document business owners for this flag
   - List impacted user groups for migration communication

#### Technical Considerations

- Data Analysis: Query PIE database for usage statistics
- System Architecture: Review PIE system documentation and data flow diagrams
- Interviews: Conduct stakeholder interviews (PDA team, Provider Directory team, etc.)
- Documentation: Create comprehensive current state document

#### Dependencies

- Access to PIE production database (read-only)
- Access to system architecture documentation
- Stakeholder availability for interviews

#### Definition of Done

- [ ] Current state document completed and reviewed
- [ ] Usage statistics collected and documented
- [ ] Dependency map created (all downstream systems)
- [ ] Stakeholder list compiled
- [ ] Risk assessment completed (migration risks identified)
- [ ] Analysis presented to project team
- [ ] Sign-off from business owner on current state documentation

---

### Story 2.2: Design New User-Friendly Location for External Concierge Provider Flag

**As a** UX Designer
**I want** to design a user-friendly location for the "Concierge Provider" flag
**So that** PDA team members can easily find and update this important provider attribute

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - UX Design

#### Acceptance Criteria

1. **Design Requirements Gathered**
   - Conduct workshop with PDA team to understand workflow
   - Understand frequency of access and typical use cases
   - Identify related fields that should be grouped together
   - Review PIE UI standards and patterns

2. **Proposed Design Options**
   - Create 2-3 design options for new flag location
   - Options should be in prominent, logical locations (e.g., "Provider Attributes" section on main provider page)
   - Designs include clear labeling ("Concierge Provider" instead of buried in properties)
   - Designs consider mobile responsiveness (if applicable)
   - Designs follow PIE design system and accessibility standards

3. **User Feedback and Selection**
   - Present design options to PDA team for feedback
   - Conduct usability testing with 3-5 PDA users
   - Document feedback and preferences
   - Select final design based on user feedback and feasibility

4. **Design Specifications**
   - Create detailed design specifications (wireframes/mockups)
   - Document exact field placement (page, section, order)
   - Specify field label: "Concierge Provider"
   - Specify field type (checkbox, yes/no toggle, etc.)
   - Include any help text or tooltips needed
   - Document responsive behavior (desktop, tablet, mobile if applicable)

#### Technical Considerations

- PIE Design System: Follow established UI patterns
- Accessibility: Ensure WCAG 2.1 AA compliance
- Responsive Design: Consider all viewport sizes
- Future-Proofing: Consider if this section could accommodate other flag types

#### Dependencies

- Story 2.1 completed (current state understood)
- PDA team availability for workshops and usability testing
- PIE design system documentation available
- UX tools available (Figma, Sketch, etc.)

#### Definition of Done

- [ ] User research completed (workshops, interviews)
- [ ] Design options created (2-3 options)
- [ ] Usability testing completed
- [ ] Final design selected and documented
- [ ] Design specifications created (wireframes/mockups)
- [ ] Design review completed by UX and development teams
- [ ] Accessibility review completed
- [ ] PDA team sign-off on final design

---

### Story 2.3: Rename Flag from "Concierge Medicine Provider Only" to "Concierge Provider"

**As a** Provider Data Administrator
**I want** the flag to be renamed to "Concierge Provider" (simplified name)
**So that** the naming is clear, concise, and consistent with our updated terminology

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Data Model & UI

#### Acceptance Criteria

1. **Database Field Rename**
   - Database field/column renamed (if feasible) or alias created
   - Field metadata updated with new display label "Concierge Provider"
   - Field description updated to reflect new name and purpose
   - API responses use new field name (or include both old and new for backward compatibility)

2. **UI Label Updates**
   - All UI references updated to "Concierge Provider"
   - Old name "Concierge Medicine Provider Only" removed from all screens
   - Updated label appears on provider detail page (new location from Story 2.2)
   - Updated label appears in any search/filter interfaces
   - Updated label appears in any bulk edit tools

3. **Documentation Updates**
   - User guides updated with new name
   - System documentation updated
   - API documentation updated (field name in requests/responses)
   - Training materials updated
   - FAQ or knowledge base articles updated

4. **Backward Compatibility (if applicable)**
   - If API field name must change, ensure backward compatibility period
   - Deprecation notice for old field name (if applicable)
   - Both old and new field names accepted during transition period (if applicable)

#### Technical Considerations

- Database Migration: Assess feasibility and risk of renaming database column vs. using display label only
- API Versioning: Consider API versioning strategy if field name changes
- Caching: Clear any cached field metadata after rename
- Testing: Test all UI screens and API endpoints

#### Dependencies

- Story 2.1 completed (current usage understood)
- Story 2.2 completed (new location designed)
- Change control approval for field rename
- Communication plan for downstream system owners

#### Definition of Done

- [ ] Database field metadata updated
- [ ] UI labels updated across all screens
- [ ] API documentation updated
- [ ] User documentation updated
- [ ] Backward compatibility tested (if applicable)
- [ ] Smoke testing completed (all key screens and workflows)
- [ ] Downstream systems notified of rename
- [ ] Change deployed to Test environment
- [ ] UAT completed in Test environment

---

### Story 2.4: Relocate "Concierge Provider" Flag to New User-Friendly Location

**As a** PIE Developer
**I want** to implement the relocation of the Concierge Provider flag to the new approved location
**So that** PDA users can easily access and update this field in their daily workflow

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Frontend Development

#### Acceptance Criteria

1. **UI Implementation**
   - Flag moved from Locations/Properties tab to new location (per Story 2.2 design)
   - New location is on main provider detail page (or approved alternative)
   - Field is in a logical section/grouping (e.g., "Provider Attributes")
   - Field label is "Concierge Provider" (per Story 2.3)
   - Field uses appropriate UI control (checkbox, toggle, etc. per design)

2. **Functionality**
   - Field is editable by PDA team (permissions from existing setup)
   - Changes save successfully
   - Success/error messages display appropriately
   - Field value persists after save
   - Page refresh shows correct saved value

3. **Old Location Cleanup**
   - Flag removed from old location (Locations/Properties tab) in UI
   - No broken links or references to old location
   - Old location code commented or removed (per team standards)

4. **Cross-Browser and Responsive**
   - New location displays correctly in all supported browsers (Chrome, Firefox, Edge, Safari)
   - Responsive design works on tablet and mobile (if applicable)
   - No layout issues or visual bugs
   - Accessibility standards met (keyboard navigation, screen reader support)

5. **Performance**
   - Page load time not significantly impacted (< 200ms increase)
   - Field updates save within acceptable time (< 2 seconds)

#### Technical Considerations

- Frontend Framework: Use existing PIE frontend framework (React, Angular, etc.)
- Component Library: Use existing PIE component library for consistency
- State Management: Ensure proper state management for field value
- API: Ensure save operation calls correct backend API
- Testing: Unit tests for new component, integration tests for save flow

#### Dependencies

- Story 2.2 completed (design approved)
- Story 2.3 completed (field renamed)
- Development environment access
- Frontend component library available

#### Definition of Done

- [ ] UI implementation completed per design specs
- [ ] Flag removed from old location
- [ ] Manual testing completed (all browsers)
- [ ] Responsive testing completed
- [ ] Accessibility testing completed
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Code review completed
- [ ] Deployed to Test environment
- [ ] UAT completed by PDA team

---

### Story 2.5: Ensure External Concierge Provider Flag Exists in Test Environment

**As a** QA Engineer
**I want** the Concierge Provider flag to exist and function correctly in the Test environment
**So that** I can perform thorough testing before production deployment

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** PIE - Test Environment

#### Acceptance Criteria

1. **Test Environment Configuration**
   - Concierge Provider flag exists in Test environment database
   - Flag appears in Test environment UI at new location
   - Flag has correct label ("Concierge Provider")
   - Field metadata matches Production configuration (pre-migration)

2. **Test Data Setup**
   - Test data includes providers with flag = true
   - Test data includes providers with flag = false
   - Test data includes providers with flag = null
   - At least 20 test records available for various test scenarios
   - Test data mirrors production data patterns

3. **Functionality Verification**
   - PDA test users can edit flag in Test environment
   - Changes save successfully in Test
   - Provider Directory feed in Test includes flag (pending Story 2.6 configuration)
   - No errors or warnings in Test environment logs

4. **Test Environment Readiness**
   - Test environment is stable and accessible
   - Test users have appropriate access/permissions
   - Test environment data is refreshed and current
   - Monitoring and logging enabled for troubleshooting

#### Technical Considerations

- Data Refresh: Coordinate with DevOps for Test data refresh from Production
- Permissions: Ensure test user accounts have PDA permissions
- Monitoring: Enable detailed logging for testing phase
- Documentation: Document test environment configuration

#### Dependencies

- Stories 2.3 and 2.4 completed (rename and relocation implemented)
- Test environment available and stable
- Test user accounts provisioned
- DevOps support for environment configuration

#### Definition of Done

- [ ] Flag exists and is functional in Test environment
- [ ] Test data created/refreshed
- [ ] Test user permissions verified
- [ ] Smoke testing completed in Test
- [ ] Test environment documented and ready for QA
- [ ] QA team notified that Test environment is ready
- [ ] Deployment checklist created for Production deployment

---

### Story 2.6: Configure Provider Directory Feed to Include External Concierge Provider Flag

**As a** Integration Engineer
**I want** to ensure the external Concierge Provider flag feeds correctly to the Provider Directory
**So that** patients and members can identify concierge providers when searching for care

**Priority:** P0 - Critical
**Story Points:** 5
**Component:** PIE - Data Integration / Provider Directory

#### Acceptance Criteria

1. **Feed Configuration**
   - PIE-to-Provider Directory feed includes Concierge Provider flag
   - Field mapping is correct (PIE field → Provider Directory target field)
   - Data type compatibility verified (boolean/yes-no/checkbox)
   - Null values are handled appropriately (e.g., treated as false or excluded)
   - Feed configuration is documented

2. **Data Synchronization**
   - Initial full load transfers all existing flag values to Provider Directory
   - Incremental updates capture flag changes within expected timeframe (e.g., within 24 hours)
   - Test updates in PIE and verify propagation to Provider Directory
   - Verify 10+ sample records in Provider Directory match PIE source

3. **Provider Directory Display**
   - Flag appears in provider search results (if applicable)
   - Flag appears on provider detail page in Provider Directory
   - Flag is labeled appropriately for consumer audience (e.g., "Concierge Medicine")
   - Visual design is consistent with Provider Directory standards

4. **Feed Reliability**
   - Error handling and retry logic is in place
   - Feed failures trigger alerts to appropriate team
   - Monitoring dashboard shows feed health metrics
   - Feed SLA is defined and documented

5. **Testing in Test Environment**
   - Feed tested end-to-end in Test environment (PIE → Provider Directory Test)
   - Test scenarios: new provider with flag, update existing provider, flag true→false, flag false→true
   - All test scenarios pass successfully

#### Technical Considerations

- ETL Pipeline: Update existing PIE-to-Provider Directory pipeline
- Timing: Coordinate feed schedule to minimize latency
- Performance: Monitor feed performance impact
- Rollback Plan: Document rollback procedure if feed issues occur
- Consumer UX: Ensure label/display is appropriate for patient audience

#### Dependencies

- Stories 2.3, 2.4, 2.5 completed (flag renamed, relocated, in Test)
- Provider Directory target field created (or existing field identified)
- Provider Directory team coordination required
- ETL infrastructure available

#### Definition of Done

- [ ] Feed configuration updated and tested in Test environment
- [ ] Data mapping documented and approved
- [ ] Initial full load completed in Test
- [ ] Incremental updates tested in Test
- [ ] End-to-end test scenarios pass (PIE → Provider Directory Test)
- [ ] Provider Directory display verified in Test
- [ ] Monitoring and alerting configured
- [ ] Provider Directory team sign-off
- [ ] Ready for Production deployment (pending Story 2.7)

---

### Story 2.7: Deploy External Concierge Provider Flag to Production Environment

**As a** Release Manager
**I want** to deploy all external Concierge Provider flag changes to Production
**So that** the improved flag is available to PDA users and flows to the live Provider Directory

**Priority:** P0 - Critical
**Story Points:** 3
**Component:** PIE - Production Deployment

#### Acceptance Criteria

1. **Pre-Deployment Checklist**
   - All Test environment testing completed successfully (Stories 2.3-2.6)
   - UAT sign-off received from PDA team
   - UAT sign-off received from Provider Directory team
   - Deployment plan reviewed and approved
   - Rollback plan documented and ready
   - Communication plan executed (stakeholders notified of deployment window)

2. **Deployment Execution**
   - Database changes deployed (field rename/metadata if applicable)
   - UI changes deployed (new location, label updates)
   - Feed configuration deployed (Provider Directory integration)
   - Deployment completes within planned maintenance window
   - Deployment checklist completed (all steps verified)

3. **Post-Deployment Verification**
   - Smoke testing completed in Production
   - PDA team can access flag at new location in Production
   - PDA team can successfully edit and save flag in Production
   - Sample of 5+ records verified in Provider Directory (flag values match PIE)
   - No errors in Production logs
   - Monitoring dashboards show green status

4. **Post-Deployment Communication**
   - Deployment success notification sent to stakeholders
   - Release notes published
   - User documentation updated and published
   - Training reminder sent to PDA team (if needed)

#### Technical Considerations

- Maintenance Window: Schedule during low-usage period
- Rollback: Have rollback plan ready (database and UI)
- Monitoring: Enhanced monitoring during and after deployment
- Support: Ensure support team is aware and ready to handle issues
- Documentation: Update production runbook

#### Dependencies

- All prior stories in Epic 2 completed (2.1-2.6)
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

### Story 2.8: Update Provider Directory Tags ASAP After Production Deployment

**As a** Provider Directory Administrator
**I want** to update/refresh provider tags in the Provider Directory immediately after the Concierge Provider flag is deployed
**So that** the public-facing directory shows accurate, current concierge provider information

**Priority:** P0 - Critical
**Story Points:** 2
**Component:** Provider Directory - Tag Management

#### Acceptance Criteria

1. **Tag Update Trigger**
   - Process initiated within 4 hours of Production deployment (Story 2.7)
   - Mechanism identified for updating tags (manual, batch job, API call, etc.)
   - Responsible person/team assigned and notified

2. **Tag Update Execution**
   - All providers with Concierge Provider flag = true are tagged appropriately in Provider Directory
   - Providers with flag = false have concierge tags removed (if previously present)
   - Tag naming is consistent (e.g., "Concierge Medicine", "Concierge PCP", etc. per Provider Directory standards)
   - Tag update completion confirmed (count of tagged providers matches PIE source)

3. **Verification**
   - Spot-check 10+ providers in Provider Directory UI (tags display correctly)
   - Search by concierge tag returns correct providers
   - Providers without flag do not show concierge tag
   - Tag update process logged and auditable

4. **Stakeholder Communication**
   - Provider Directory team notified when tag update is complete
   - PDA team notified when tag update is complete
   - Business owner notified of successful completion
   - Any issues or discrepancies reported and documented

#### Technical Considerations

- Timing: Coordinate with Story 2.7 deployment timeline
- Batch Size: If large volume, consider batching to avoid system overload
- Error Handling: Document any providers that failed to update and remediation plan
- Monitoring: Monitor Provider Directory system health during update
- Rollback: Document tag rollback process if needed

#### Dependencies

- Story 2.7 completed (Production deployment successful)
- Provider Directory tag management system access
- Provider Directory team availability
- Tag update process documented

#### Definition of Done

- [ ] Tag update process initiated within 4 hours of Production deployment
- [ ] Tag update completed successfully
- [ ] Verification spot-checks passed (10+ providers)
- [ ] Count of tagged providers reconciled with PIE source
- [ ] Provider Directory search by tag working correctly
- [ ] Completion notification sent to stakeholders
- [ ] Any issues/discrepancies documented and resolved (or remediation plan created)
- [ ] Tag update process documented for future reference

---

## Cross-Epic Dependencies

### Integration Points

1. **Internal vs External Flags - Clear Distinction**
   - Epic 1 (Internal Flag) must NOT feed to Provider Directory
   - Epic 2 (External Flag) MUST feed to Provider Directory
   - Testing must verify this separation (Story 1.5, 1.6, 2.6)

2. **PDA Team Training**
   - Single training session can cover both flags
   - PDA team must understand when to use internal vs external flag
   - Documentation must clearly differentiate the two flags

3. **Naming Conflicts**
   - Internal flag: "Concierge PCP"
   - External flag: "Concierge Provider"
   - Clear naming prevents confusion

4. **Reporting Considerations**
   - Analytics team may need reports that show both flags
   - Consider creating unified dashboard that displays both (internal use)

5. **Testing Coordination**
   - Both epics should be tested together for end-to-end validation
   - Verify that both flags can coexist on same practitioner/practice
   - Verify that changes to one flag do not affect the other

---

## Technical Considerations

### Architecture

- **PIE System**: Central source of truth for both flags
- **DART**: Receives internal flag only (Epic 1)
- **Inquire Only**: Receives internal flag only (Epic 1)
- **Provider Directory**: Receives external flag only (Epic 2)
- **Data Isolation**: Internal and external flags must be clearly separated in feed configurations

### Security & Access Control

- **PDA Team**: Edit access to both flags
- **Internal Users**: View access to internal flag (via DART/Inquire Only)
- **Public**: View access to external flag (via Provider Directory)
- **Field-Level Security**: Implement for internal flag to prevent accidental exposure

### Data Model

- Both flags exist at **Practitioner** and **Practice** levels
- Internal flag includes **Effective Date** and **Termination Date**
- External flag may not need dates (as per requirements)
- Consider using a shared parent object or section for both flags to keep related data together

### Performance

- **Database Indexing**: Index both flags for reporting performance
- **Feed Optimization**: Ensure feeds do not double-load (only send deltas)
- **Caching**: Consider caching strategy for Provider Directory

### Testing Strategy

- **Unit Tests**: Each field, validation rule, permission
- **Integration Tests**: Feeds to DART, Inquire Only, Provider Directory
- **End-to-End Tests**: PDA workflow from flag update → downstream system display
- **Performance Tests**: Feed performance, search performance in downstream systems
- **Security Tests**: Verify internal flag does not appear in Provider Directory, external flag appears correctly
- **UAT**: PDA team, Analytics team, Provider Directory team

---

## Definition of Done

### Story-Level Definition of Done

Each user story is considered done when:

- [ ] Acceptance criteria met (all criteria pass)
- [ ] Code implemented and unit tests written (100% of new code covered)
- [ ] Code review completed (2+ reviewers)
- [ ] Integration tests pass
- [ ] Deployed to Test environment
- [ ] UAT completed by relevant stakeholders (sign-off received)
- [ ] Documentation updated (technical and user documentation)
- [ ] No critical or high-priority bugs remaining
- [ ] Performance benchmarks met
- [ ] Security review completed (if applicable)
- [ ] Accessibility review completed (if applicable)

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

### Test Scenarios - Epic 1 (Internal Concierge PCP Flag)

#### Scenario 1: PDA User Updates Practitioner-Level Flag

**Given** a PDA user is viewing a Practitioner record in PIE
**When** the user checks the "Concierge PCP" flag and enters an effective date
**Then** the flag and date are saved successfully
**And** the flag appears in DART within [defined timeframe]
**And** the flag appears in Inquire Only within [defined timeframe]
**And** the flag does NOT appear in Provider Directory

#### Scenario 2: PDA User Updates Practice-Level Flag

**Given** a PDA user is viewing a Practice record in PIE
**When** the user checks the "Concierge PCP" flag and enters an effective date
**Then** the flag and date are saved successfully
**And** the flag appears in DART within [defined timeframe]
**And** the flag appears in Inquire Only within [defined timeframe]
**And** the flag does NOT appear in Provider Directory

#### Scenario 3: Date Validation

**Given** a PDA user is updating the Concierge PCP flag
**When** the user enters a termination date that is before the effective date
**Then** the system displays an error message
**And** the save operation is blocked

#### Scenario 4: Data Quality Alert

**Given** a provider has Concierge PCP flag = true with no effective date
**When** the daily data quality job runs
**Then** this record appears in the data quality report sent to the PDA team

#### Scenario 5: Reporting in DART

**Given** the Concierge PCP dashboard in DART
**When** a user views the dashboard
**Then** the dashboard shows accurate counts of active concierge PCPs
**And** the trend line shows historical changes over time

---

### Test Scenarios - Epic 2 (External Concierge Provider Flag)

#### Scenario 1: PDA User Accesses Flag at New Location

**Given** a PDA user is viewing a Provider record in PIE
**When** the user navigates to the [new section name] section
**Then** the user sees the "Concierge Provider" flag clearly labeled
**And** the user does NOT see the old "Concierge Medicine Provider Only" label on the Locations/Properties tab

#### Scenario 2: Flag Update Flows to Provider Directory

**Given** a PDA user has updated a provider's "Concierge Provider" flag to true in PIE
**When** the PIE-to-Provider Directory feed runs
**Then** the provider shows as a concierge provider in Provider Directory
**And** the provider can be found by searching/filtering for concierge providers

#### Scenario 3: Flag Rename Verification

**Given** the "Concierge Provider" flag in PIE
**When** a user views any screen where the flag appears
**Then** the label is consistently "Concierge Provider" (not the old name)

#### Scenario 4: Test Environment Validation

**Given** the Test environment is configured for the Concierge Provider flag
**When** a QA engineer tests the flag in Test
**Then** all functionality works identically to Production (after deployment)

#### Scenario 5: Provider Directory Tag Update

**Given** the Production deployment is complete
**When** the tag update process runs
**Then** all providers with flag = true are tagged in Provider Directory
**And** the tag appears correctly in search results and provider profiles

---

### Cross-Epic Test Scenarios

#### Scenario 1: Both Flags on Same Provider

**Given** a practitioner has both "Concierge PCP" (internal) and "Concierge Provider" (external) flags
**When** a PDA user views the practitioner record in PIE
**Then** both flags are visible in their respective sections
**And** changes to one flag do not affect the other

#### Scenario 2: Internal Flag Does Not Leak to Provider Directory

**Given** a practitioner has "Concierge PCP" (internal) flag = true
**And** the practitioner has "Concierge Provider" (external) flag = false
**When** the Provider Directory is viewed
**Then** the practitioner does NOT appear as a concierge provider
**And** only the external flag influences Provider Directory display

#### Scenario 3: DART Only Shows Internal Flag

**Given** a practitioner has both flags set to true
**When** the DART reporting dashboard is viewed
**Then** only the "Concierge PCP" (internal) flag data is displayed in DART
**And** the external flag data does not appear in DART

---

## Appendix: Field Reference

### Internal Concierge PCP Flag (Epic 1)

| Attribute | Value |
|-----------|-------|
| **Field Name** | Concierge PCP |
| **Field Type** | Boolean (checkbox) |
| **Nullable** | Yes |
| **Applies To** | Practitioner, Practice |
| **Visibility** | Internal only (PDA, DART, Inquire Only) |
| **Feeds To** | DART, Inquire Only |
| **Does NOT Feed To** | Provider Directory |
| **Editable By** | PDA Team |
| **Audit Trail** | Yes |

### Internal Concierge PCP Effective Date (Epic 1)

| Attribute | Value |
|-----------|-------|
| **Field Name** | Concierge PCP Effective Date |
| **Field Type** | Date |
| **Format** | MM/DD/YYYY |
| **Nullable** | Yes (recommended when flag = true) |
| **Applies To** | Practitioner, Practice |
| **Validation** | Cannot be in future; should be <= termination date |
| **Editable By** | PDA Team |
| **Audit Trail** | Yes |

### Internal Concierge PCP Termination Date (Epic 1)

| Attribute | Value |
|-----------|-------|
| **Field Name** | Concierge PCP Termination Date |
| **Field Type** | Date |
| **Format** | MM/DD/YYYY |
| **Nullable** | Yes |
| **Applies To** | Practitioner, Practice |
| **Validation** | Cannot be in future; must be >= effective date |
| **Editable By** | PDA Team |
| **Audit Trail** | Yes |

### External Concierge Provider Flag (Epic 2)

| Attribute | Value |
|-----------|-------|
| **Field Name** | Concierge Provider |
| **Previous Name** | Concierge Medicine Provider Only |
| **Field Type** | Boolean (checkbox or similar) |
| **Nullable** | Yes |
| **Applies To** | Practitioner, Practice |
| **Visibility** | Public (Provider Directory) |
| **Feeds To** | Provider Directory |
| **Does NOT Feed To** | DART, Inquire Only (unless also internal flag) |
| **Editable By** | PDA Team |
| **Old Location** | Locations/Properties tab (buried) |
| **New Location** | [To Be Determined in Story 2.2] - User-friendly location |

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **PIE** | Provider Information Exchange - the central system for managing provider data |
| **PDA Team** | Provider Data Administration Team - responsible for maintaining provider data accuracy |
| **DART** | Data Analytics and Reporting Tool - internal analytics platform |
| **Inquire Only** | Internal system used by customer service for viewing provider information |
| **Provider Directory** | Public-facing system where patients/members search for providers |
| **Concierge PCP** | Internal flag for tracking concierge primary care physicians (analytics only) |
| **Concierge Provider** | External flag displayed in Provider Directory (public-facing) |
| **Practitioner** | Individual doctor/provider |
| **Practice** | Group practice or organization where practitioners work |
| **Effective Date** | Date when a provider started operating under concierge medicine model |
| **Termination Date** | Date when a provider stopped operating under concierge medicine model |

---

**End of Document**

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-01 | Requirements Analysis | Initial creation of user stories document |

---

## Next Steps

1. **Review and Approval**: Present this user story document to product owner and key stakeholders for review and approval
2. **Story Estimation**: Conduct planning poker or similar estimation session with development team to validate story points
3. **Prioritization**: Finalize story prioritization within each epic with product owner
4. **Sprint Planning**: Assign stories to sprints based on team capacity and dependencies
5. **Kickoff**: Conduct epic kickoff meetings for Epic 1 and Epic 2 with all stakeholders
6. **Begin Development**: Start with highest-priority stories (Story 1.1, 2.1) after approval
