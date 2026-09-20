# Life Sciences Cloud: Visit Management — Detailed User Stories

**Source Document:** LifeSciencesVisitManagement.md  
**Vertical:** Health & Life Sciences (HLS)  
**Date:** 2026-03-30  
**Status:** Ready for Development

---

## Epic 1: Visit Planning & Preparation

### USER STORY 1.1: Schedule Multi-HCP Group Visits with Attendee Management

**Persona:** Field Sales Representative, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, Account, User, HealthcareProvider, VisitAttendee__c (if applicable)  
**Integration Procedures:** N/A (OmniScript-based for mobile)  
**Relevant Requirements:** FHN-14, FHN-15 (Visit scheduling), FHN-95 (Group visit attendees)

---

## Story

**As a** Field Sales Representative,  
**I want** to schedule a visit to an HCP account and add multiple Healthcare Professionals (both internal users and external HCP accounts) as attendees to a single visit record,  
**So that** I can efficiently plan and document group visits, lunch-and-learn sessions, and multi-stakeholder meetings without creating duplicate visit records.

**Why it matters:** Life Sciences field teams frequently conduct group engagements (e.g., lunch-and-learn sessions with multiple clinicians, facility-wide training). Without native multi-attendee support, reps must create redundant visit records or manually track attendees outside the system, creating compliance gaps and data inconsistency.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Visit Planning | Mobile/Web Visit Form | Schedule Visit + Add Attendees | Account Lookup, User Lookup, HCP Contacts | Visit__c, VisitAttendee__c |
| Post-Visit Audit | Visit Summary | View All Attendees | VisitAttendee__c records | Visit__c (parent) |

---

## Current State (from Salesforce Object Model)

### Visit__c Object

- **Field:** `VisitDate__c` (Date) — Date and time of the visit
- **Field:** `VisitType__c` (Picklist) — Type of visit (e.g., Individual HCP Visit, Group Presentation, Lunch & Learn)
- **Field:** `Location__c` (Text) — Physical location or virtual meeting link
- **Field:** `PrimaryHCP__c` (Lookup to Account) — Primary HCP account for the visit
- **Field:** `VisitStatus__c` (Picklist) — Planned, In Progress, Completed, Cancelled, Submitted (locked)
- **Field:** `RecordType` — Maps to Account RecordType (HCP vs. Pharmacy vs. Healthcare Facility)
- **Related List:** VisitAttendee__c (if object exists) or use standard Contact Role / Account Relationship

### Account Object (HCP Record Type)

- **Field:** `Name` (Text) — Name of Healthcare Professional or practice
- **Field:** `RecordType` — HCP, Healthcare Facility, Pharmacy, etc.
- **Field:** `AccountNumber` — DEA/NPI identifier
- **Relationship:** Contacts, Users (through Account Team)

### User Object (Internal Attendees)

- **Field:** `Name`, `Email`, `Phone`
- **Field:** `Department__c` (if custom) — Sales, Marketing, Medical Affairs
- **Lookup relationship** from VisitAttendee__c

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **VisitAttendee__c Object** | Custom Object (if new) or Relationship | Create or extend to support multiple attendee records per visit | Lookup to Visit__c (Master-Detail), Lookup to Account (HCP attendees), Lookup to User (internal attendees), Role__c picklist (Attendee, Speaker, Organizer), IsExternal__c checkbox |
| **Visit__c Page Layout** | OmniScript / Mobile Card | Add attendee section with inline add/remove capability | Repeatable block: Account/User lookup, Role selection, Remove button |
| **Visit Attendee Picklist** | Salesforce List | Define attendee types and roles | Principal HCP, Secondary HCP, Internal Speaker, Marketing Support, Medical Affairs, Compliance Observer |
| **Visit__c Validation Rule** | Apex / Flow | Ensure PrimaryHCP__c is also in VisitAttendee__c records | If VisitType = "Group" AND PrimaryHCP__c is not null, then PrimaryHCP__c must exist in VisitAttendee__c with Role = "Principal HCP" |
| **Attendee Cascading Logic** | Apex Trigger / Flow | When VisitStatus = "Submitted", lock all VisitAttendee__c records | Set Locked__c = true; prevent edits post-submission |

### VisitAttendee__c Object Schema (if new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Visit__c | Master-Detail | Yes | Lookup to Visit__c (Master); delete cascade |
| AttendeeType__c | Picklist | Yes | Internal (User) or External (Account/HCP) |
| InternalAttendee__c | Lookup (User) | Conditional | If AttendeeType = "Internal", required |
| ExternalAttendee__c | Lookup (Account) | Conditional | If AttendeeType = "External", required |
| AttendeeRole__c | Picklist | Yes | Principal HCP, Secondary HCP, Speaker, Support, Observer |
| IsConfirmed__c | Checkbox | No | True if attendee confirmed attendance |
| ConfirmedDate__c | DateTime | No | Auto-populated when IsConfirmed = true |

### Example (Visit Attendee Data Structure)

```json
{
  "Visit__c": {
    "VisitId": "a012t000003A1ZAAX",
    "VisitDate__c": "2026-04-15",
    "VisitType__c": "Lunch & Learn",
    "PrimaryHCP__c": "0012t000001a2cZAAQ",  // Account lookup
    "Location__c": "Memorial Hospital - Cafeteria",
    "VisitStatus__c": "Planned",
    "RecordType": "HCP Visit"
  },
  "VisitAttendees": [
    {
      "AttendeeType__c": "External",
      "ExternalAttendee__c": "0012t000001a2cZAAQ",  // Principal HCP
      "AttendeeRole__c": "Principal HCP",
      "IsConfirmed__c": true
    },
    {
      "AttendeeType__c": "External",
      "ExternalAttendee__c": "0012t000001a2daAAB",  // Secondary HCP (physician colleague)
      "AttendeeRole__c": "Secondary HCP",
      "IsConfirmed__c": true
    },
    {
      "AttendeeType__c": "Internal",
      "InternalAttendee__c": "0052t000001ABCDEF",  // Sales Rep
      "AttendeeRole__c": "Organizer",
      "IsConfirmed__c": true
    },
    {
      "AttendeeType__c": "Internal",
      "InternalAttendee__c": "0052t000001GHIJKL",  // Marketing Support
      "AttendeeRole__c": "Support",
      "IsConfirmed__c": false
    }
  ]
}
```

---

## Acceptance Criteria

### Scenario 1: Add Multiple External HCPs (Happy Path)

**Given** a Field Sales Rep is in the Visit scheduling screen for a new "Lunch & Learn" visit type,  
**When** they enter visit date, location, and select the primary HCP account (e.g., Memorial Hospital),  
**Then** the form displays an "Add Attendees" section with options to:
- Search and add external attendees (HCP Accounts) by name/NPI
- Search and add internal attendees (Users) by name/email
- Assign role to each attendee (Principal HCP, Secondary HCP, Speaker, Support, Observer)
- Save each attendee by clicking "Add Attendee" button

**And when** the rep adds multiple attendees (e.g., 3 physicians + 2 internal staff),  
**Then** all attendees display in a list with confirmation status, and the system validates that the primary HCP is included.

---

### Scenario 2: Edit Attendee List Before Submission

**Given** a scheduled visit with 4 confirmed attendees,  
**When** the rep opens the visit record before submission,  
**Then** they can:
- View all attendees in a read-only table showing Name, Role, Attendance Status
- Click "Edit Attendees" to add/remove attendees or change roles
- Remove an attendee by clicking the trash icon

**And when** the rep removes the Marketing Support attendee and saves,  
**Then** the VisitAttendee__c record is deleted, and the attendee list updates immediately without reloading the page.

---

### Scenario 3: Prevent Submission Without Primary HCP

**Given** a rep tries to submit a visit with VisitType = "Group",  
**When** the PrimaryHCP__c is set but NOT included in VisitAttendee__c records,  
**Then** the system displays a validation error:
- **Error Message:** "Primary HCP '{Account Name}' must be listed as an attendee with role 'Principal HCP' before submission."
- **UI:** Red banner at top of form; disabled Submit button until corrected

---

### Scenario 4: Lock Attendee Records on Visit Submission

**Given** a rep has completed and is submitting a visit with 3 attendees,  
**When** they click "Submit Visit",  
**Then** the visit status changes to "Submitted" and all VisitAttendee__c records are locked (Locked__c = true).  
**And when** the rep (or manager) later opens the submitted visit,  
**Then** the attendee list is read-only, and attempting to edit displays:
- **Message:** "This visit has been submitted and locked. Contact your manager to request changes."

---

### Scenario 5: Edge Case — External Attendee with Multiple Roles

**Given** a rep schedules a visit where one HCP wears two hats (e.g., Principal Clinician AND Speaker),  
**When** they try to add the same Account as both "Principal HCP" and "Speaker",  
**Then** the system prevents duplicate attendee entries and displays:
- **Warning:** "{Account Name} is already added to this visit. Edit the existing record to change their role."

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **VisitAttendee__c Exists?** Does the Salesforce LS Cloud package already include a VisitAttendee__c object, or must it be created as a custom object? | Determines development approach (extend existing vs. build new); affects data model migration | Technical Lead |
| 2 | **Attendee Lookup Strategy** Should attendees be looked up by Account name/NPI, or should there be a filtered list of "Available HCPs"? | UX design; may require custom lookup filter; audit/compliance implications | Product Manager |
| 3 | **Attendance Confirmation** Do attendees need to confirm attendance before/after the visit, or is attendance recorded post-visit? | Impacts object schema (IsConfirmed__c, ConfirmedDate__c placement) | Business Analyst |
| 4 | **Attendee Privacy** Should external HCP attendees (from non-primary accounts) be visible in reports/dashboards, or should only primary HCP data be exposed? | Privacy and data residency; may require row-level security | Compliance Officer |
| 5 | **Max Attendee Limit** Should there be a maximum number of attendees per visit (e.g., 20 max) for performance/UX reasons? | Validation rule design; mobile app performance | Technical Lead |
| 6 | **Role-Based Permissions** Can Compliance Managers edit attendee lists post-submission, or is submission permanent? | Audit trail implications; may require custom permission set | Compliance Manager |
| 7 | **Attendee Reporting** Which attendee data should flow to reporting (e.g., "All HCPs Engaged by Rep by Quarter")? | Analytics implementation; data warehouse sync | BI Analyst |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **VisitAttendee__c Object** | Custom Object | HIGH | New object; affects data model, reporting, permissions, and audit trails |
| **Visit__c Page Layout** | OmniScript / Form | HIGH | User-facing change; affects 100% of visit creation workflows |
| **Validation Rules** | Apex / Flow | HIGH | Blocks invalid visit submissions; affects compliance audits |
| **Trigger Handlers** | Apex | HIGH | Cascade deletes, locking, parent-child sync; must be thoroughly tested |
| **Security & Permissions** | RBAC / OLS | MEDIUM | Row-level security and field-level permissions must be configured per role |
| **Reporting & Analytics** | Dashboards | MEDIUM | New attendee data requires dashboard updates and BI coordination |
| **Mobile App** | Salesforce Mobile / Custom App | MEDIUM | Attendee UI must be mobile-friendly; performance testing required |
| **Integration Procedures** | Data Sync | LOW | If external HCP data syncs from CRM upstream, ensure attendee records sync correctly |

---

## Definition of Done Checklist

- [ ] VisitAttendee__c object created (or existing object extended) with all required fields
- [ ] Visit__c page layout updated with attendee section; mobile view optimized
- [ ] Attendee lookup filters configured (HCP Accounts only; exclude non-applicable record types)
- [ ] Validation rule: PrimaryHCP__c must exist in VisitAttendee__c for group visits
- [ ] Validation rule: Prevent duplicate attendee entries for same account/user
- [ ] Apex trigger: Lock VisitAttendee__c records when Visit__c.VisitStatus = "Submitted"
- [ ] Apex trigger: Cascade delete VisitAttendee__c when Visit__c is deleted
- [ ] Role-based field-level permissions set (e.g., Compliance can view, Reps can edit pre-submission)
- [ ] Test scenario: Add 5 attendees, submit visit, verify lock, attempt edit (fails gracefully)
- [ ] Test scenario: Remove attendee before submission, verify list updates
- [ ] Test scenario: Prevent submission without primary HCP attendee
- [ ] QA sign-off: Mobile app attendee picker works smoothly
- [ ] Documentation: Field reference guide for VisitAttendee__c fields
- [ ] Training materials: User guide for adding group visit attendees

---

## Related User Stories

- **US 1.2** — Visit conflict validation (affects attendee frequency rules)
- **US 3.4** — Visit submission & audit trail (locks attendee records)
- **US 4.1** — Visit Record Type to Account Record Type mapping (filters visible attendee types)

---

---

## USER STORY 1.2: Visit Conflict Validation & Compliance Alerts

**Persona:** Field Sales Representative, Compliance Manager, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, Account, HealthcareProvider, VisitFrequencyRule__c (custom metadata or config object)  
**Integration Procedures:** PRM_VisitConflictValidator (hypothetical IP)  
**Relevant Requirements:** FHN-15, FHN-81 (Visit conflict validation)

---

## Story

**As a** Field Sales Representative,  
**I want** the system to automatically validate that my scheduled visit does not violate visit frequency compliance rules for a specific HCP,  
**So that** I can avoid over-engaging HCPs and maintain compliance with industry guidelines (e.g., maximum 3 visits per quarter per HCP).

**Why it matters:** Life Sciences companies face regulatory scrutiny on frequency and intensity of field interactions with HCPs. Over-engagement can trigger compliance violations, mandatory audits, and reputational damage. Automated conflict detection prevents reps from scheduling visits that breach these rules and provides real-time guidance.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Visit Planning | Visit Scheduling Form | After HCP selection, before save | VisitFrequencyRule__c (config), Past Visit__c records | Visit__c |
| Conflict Alert | Modal / Toast | Display warning if violation detected | Visit__c history + rule config | VisitFrequencyRule__c |

---

## Current State (from Salesforce Object Model)

### VisitFrequencyRule__c (Custom Metadata or Configuration Object)

- **Field:** `RuleName__c` (Text) — "Max Visits per Quarter", "Max Visits per Fiscal Year", "Min Days Between Visits"
- **Field:** `Frequency__c` (Number) — Number of allowed visits in the time period
- **Field:** `TimePeriod__c` (Picklist) — "Calendar Quarter", "Fiscal Quarter", "Calendar Year", "Fiscal Year", "Days"
- **Field:** `ApplicableAccountRecordType__c` (Picklist) — HCP, Healthcare Facility, Pharmacy, or "All"
- **Field:** `BypassRoles__c` (Multi-select Picklist) — Roles that can override rule (e.g., "Compliance Manager", "Regional Manager")
- **Field:** `AlertBehavior__c` (Picklist) — "Warn & Allow", "Block", "Warn & Require Approval"

### Visit__c Object (Relevant Fields)

- **Field:** `VisitDate__c` (Date)
- **Field:** `PrimaryHCP__c` (Lookup to Account)
- **Field:** `VisitType__c` (Picklist)
- **Field:** `ConflictFlags__c` (Text, read-only) — JSON array of triggered rules
- **Field:** `ApprovedByCompliance__c` (Lookup to User) — Who approved override, if any
- **Field:** `ApprovalReason__c` (Text) — Why compliance approved override

### Visit__c Query History

```
SELECT COUNT() FROM Visit__c 
WHERE PrimaryHCP__c = :hcpId 
AND CALENDAR_QUARTER(VisitDate__c) = :currentQuarter 
AND VisitStatus__c != 'Cancelled'
```

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **VisitFrequencyRule__c** | Custom Metadata Type | Create centralized config for visit frequency rules | Queryable from OmniScript via Integration Procedure; supports org-wide and role-based rules |
| **Visit__c Save Flow** | Apex Trigger / Flow | Before inserting/updating Visit__c, query frequency rules and check visit history | Trigger on before insert/update; call `VisitConflictValidator.checkConflicts()` |
| **PRM_VisitConflictValidator** | Integration Procedure or Apex Class | Validate visit frequency, return conflict array | Inputs: hcpId, visitDate, visitType; Outputs: conflictList, hasConflict (boolean), alertMessage |
| **Conflict Alert Modal** | OmniScript LWC Component | Display warning/block based on rule configuration | If AlertBehavior = "Warn & Allow": show warning, allow continue; If "Block": show error, prevent save; If "Require Approval": show form for Compliance Manager approval |
| **ApprovedByCompliance__c Field** | Checkbox + Lookup + Text | Track override approvals for audit trail | Required if AlertBehavior = "Require Approval" and user overrides |

### Visit Conflict Validator Logic (Pseudocode)

```javascript
function checkVisitConflicts(hcpId, visitDate, visitType, userId) {
  // 1. Query applicable rules
  rules = query VisitFrequencyRule__c 
    WHERE ApplicableAccountRecordType = HCP_RECORDTYPE;
  
  conflicts = [];
  
  // 2. For each rule, calculate baseline
  for rule in rules {
    timeWindow = calculateTimeWindow(rule.TimePeriod__c, visitDate);
    visitCount = query Visit__c 
      WHERE PrimaryHCP__c = hcpId 
      AND VisitDate__c in timeWindow 
      AND VisitStatus != 'Cancelled';
    
    if (visitCount >= rule.Frequency__c) {
      conflict = {
        ruleName: rule.RuleName__c,
        limit: rule.Frequency__c,
        actual: visitCount + 1,
        timePeriod: rule.TimePeriod__c,
        alertBehavior: rule.AlertBehavior__c
      };
      conflicts.push(conflict);
    }
  }
  
  // 3. Check if user role can bypass
  canBypass = isUserRoleInBypassList(userId, conflicts[0].BypassRoles__c);
  
  // 4. Return result
  return {
    hasConflict: conflicts.length > 0,
    conflicts: conflicts,
    canBypass: canBypass,
    action: determineAction(conflicts, canBypass)
  };
}
```

### Example (Conflict Detection Response)

```json
{
  "hasConflict": true,
  "conflicts": [
    {
      "ruleName": "Max 3 Visits per Calendar Quarter",
      "limit": 3,
      "actual": 4,  // This visit would be the 4th
      "timePeriod": "Q2 2026",
      "alertBehavior": "Warn & Allow",
      "lastVisitDate": "2026-04-10"
    }
  ],
  "canBypass": false,
  "action": "WARN_CONTINUE",
  "message": "This HCP already has 3 visits scheduled in Q2 2026. Proceeding will exceed the recommended frequency. Contact Compliance if this is clinically justified."
}
```

---

## Acceptance Criteria

### Scenario 1: HCP Within Frequency Limits (Happy Path)

**Given** a rep schedules a visit for an HCP with only 1 prior visit in Q2 2026,  
**When** they select the HCP and save the visit,  
**Then** the system queries VisitFrequencyRule__c and calculates: 1 prior visit + 1 new visit = 2 visits (within limit of 3).  
**And the system displays:** No conflict alert; visit saves successfully.

---

### Scenario 2: Warn & Allow — Show Warning, Let Rep Proceed

**Given** a rep schedules a visit for an HCP that already has 3 visits in Q2 2026 (hitting the limit),  
**When** they click "Save Visit",  
**Then** the system displays a warning modal:
- **Title:** "Visit Frequency Alert"
- **Message:** "This HCP already has 3 visits scheduled in Q2 2026 (limit: 3). This visit will exceed the recommended frequency. Do you want to proceed?"
- **Buttons:** "Cancel" (abort save) | "Continue Anyway" (override and save)

**And when** the rep clicks "Continue Anyway",  
**Then** the visit is saved, and `ConflictFlags__c` field is populated with the rule name for audit purposes.

---

### Scenario 3: Block — Prevent Submission

**Given** a rep schedules a visit for a Pharmacy (if rule has AlertBehavior = "Block" for Pharmacy visits),  
**When** they exceed the frequency limit,  
**Then** the system displays an error modal:
- **Title:** "Visit Not Allowed"
- **Message:** "This account has reached the maximum visit frequency for this period. Contact your manager for an exception request."
- **Button:** "OK" (closes modal, prevents save)

---

### Scenario 4: Require Approval — Escalate to Compliance

**Given** a rep schedules a visit that violates an AlertBehavior = "Require Approval" rule,  
**When** they click "Save Visit",  
**Then** the system displays a request form:
- **Fields:** HCP Name (read-only), Reason for Override (text area), Attach Document (optional)
- **Button:** "Request Compliance Approval"

**And when** the rep submits,  
**Then** the visit enters a "Pending Approval" status, and a Compliance Manager receives an email notification with a link to approve/deny.

---

### Scenario 5: Bypass Allowed for Compliance Managers

**Given** a Compliance Manager schedules a visit that exceeds frequency limits,  
**When** the system detects a conflict,  
**Then** it checks VisitFrequencyRule__c.BypassRoles__c and finds "Compliance Manager" in the list.  
**And the system displays:** A warning (informational only, no block) with a note: "You have bypass permissions for this rule."  
**And when** the Compliance Manager clicks "Save",  
**Then** the visit saves immediately without requiring additional approval.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Rule Configuration Location** Should rules be stored in Custom Metadata Types (static, deployment-controlled) or a custom config object (user-editable in UI)? | Developer experience, release management, audit trail | Technical Lead |
| 2 | **Frequency Calculation Window** For rules with TimePeriod = "Fiscal Quarter", which fiscal year end should the system use (e.g., June 30, December 31)? | Query accuracy; affects rule compliance | Finance / Compliance |
| 3 | **Cancelled Visits** Should cancelled or declined visits count toward the frequency limit, or only completed/submitted visits? | Query logic in VisitConflictValidator | Compliance Officer |
| 4 | **Multi-HCP Group Visits** For a group visit with 5 HCP attendees, should the system check frequency for all attendees, only the primary, or configurable? | Complex validation logic; impacts rule design | Product Manager |
| 5 | **Approval Workflow** If Require Approval rule is triggered, who are the default Compliance Managers to notify, and what's the SLA for approval? | Email notification logic, escalation rules | Compliance Manager |
| 6 | **Rule Retroactivity** Should rules be retroactively applied to past visits when rule is created/updated, or only to new visits going forward? | Data integrity implications; may require batch job | Compliance Officer |
| 7 | **Bypass Audit Trail** For bypassed visits, should the system generate an audit report for compliance review at month-end? | Reporting, compliance dashboard | Compliance Manager |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **VisitFrequencyRule__c** | Custom Metadata Type | MEDIUM | New config object; affects rule management and deployment process |
| **Visit__c Trigger** | Apex Trigger | HIGH | Synchronous validation on every visit save; must be performant (avoid N+1 queries) |
| **PRM_VisitConflictValidator** | Integration Procedure / Apex Class | HIGH | Core business logic; affects 100% of visit creation flows |
| **Conflict Alert UI** | OmniScript LWC | HIGH | User-facing; blocks/warns on visits; UX critical |
| **ApprovedByCompliance__c Fields** | Custom Fields | MEDIUM | Audit trail; required for compliance reporting |
| **Email Notifications** | Salesforce Flow | MEDIUM | Requires email template creation and Compliance Manager setup |
| **Reporting & Dashboards** | Analytics | MEDIUM | Need to show "Flagged Visits", "Overrides", "Compliance Exceptions" |

---

## Definition of Done Checklist

- [ ] VisitFrequencyRule__c Custom Metadata Type created with all fields
- [ ] Initial frequency rules loaded (e.g., "3 visits per quarter", "1 visit per 30 days")
- [ ] Apex trigger on Visit__c before insert/update calls conflict validator
- [ ] PRM_VisitConflictValidator implemented; handles all rule types (warn, block, approve)
- [ ] Conflict alert modal/toast displays in OmniScript with correct behavior per rule
- [ ] Bypass logic checks user role against BypassRoles__c
- [ ] ConflictFlags__c field populated with rule names for audit
- [ ] Apex test coverage ≥ 90% for VisitConflictValidator
- [ ] Integration test: Schedule 3 visits for HCP in one quarter, verify 4th triggers alert
- [ ] Integration test: Compliance Manager bypasses, verify no alert shown
- [ ] Email notification sent to Compliance Manager when Require Approval rule triggered
- [ ] QA sign-off: Mobile app displays conflict alerts without timeout/error
- [ ] Documentation: Rule configuration guide for admins
- [ ] Compliance dashboard report: "Visits Flagged by Frequency Rule"

---

---

## USER STORY 1.3: AI-Backed Visit Recommendations & Content Insights

**Persona:** Field Sales Representative, Marketing Manager, AI/Analytics Lead, Developer  
**Priority:** P1  
**Related Objects:** Visit__c, Account, HealthcareProvider, Contact, VisitHistory__c, ContentVersion, ContentVersion_Distribution__c (for recommendation tracking)  
**Integration Procedures:** PRM_VisitRecommendationEngine (hypothetical), External AI/ML Service (e.g., Einstein AI, Tableau CRM)  
**Relevant Requirements:** FHN-15, FHN-81 (AI recommendations), FHN-82 (Content personalization)

---

## Story

**As a** Field Sales Representative,  
**I want** to receive AI-backed recommendations for content, talking points, and engagement strategies tailored to the specific HCP I'm about to visit,  
**So that** I can deliver more personalized, effective interactions that address the HCP's known interests, prescribing patterns, and past engagement history.

**Why it matters:** Reps struggle to quickly synthesize account intelligence before visits, leading to generic pitches and missed personalization opportunities. AI recommendations surface high-value insights (e.g., "This cardiologist recently published on heart failure; mention your FDA indication in that area") and suggest pre-approved content, saving prep time and increasing engagement effectiveness.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Pre-Visit Preparation | Visit Prep Card / Dashboard Widget | After visit scheduled, before visit date | HealthcareProvider profile, Past Visit history, Content repository, Prescribing data (if available) | Visit__c, VisitRecommendation__c (custom object) |
| Visit Execution | Visit Detail Screen | Display recommended content inline | Recommended content (Salesforce ContentVersion, external library) | Visit__c |

---

## Current State (from Salesforce Object Model)

### HealthcareProvider Object

- **Field:** `Specialty__c` (Picklist/Lookup) — Cardiology, Orthopedics, etc.
- **Field:** `PrescribingPattern__c` (Lookup or Text) — Most frequently prescribed products/therapeutic areas
- **Field:** `PublicationHistory__c` (Text / Relationship) — Recent publications, presentations (if tracked)
- **Field:** `EngagementScore__c` (Number, calculated) — Derived from past visit frequency, interaction quality
- **Field:** `KeyInterests__c` (Multi-select Picklist or Text) — Clinical areas of interest (from surveys, past interactions)
- **Related List:** Visits, Contacts, Activities

### Visit__c Object (Relevant Fields)

- **Field:** `VisitDate__c`
- **Field:** `PrimaryHCP__c`
- **Field:** `RecommendedContent__c` (JSON or Lookup) — Stores AI-recommended content IDs
- **Field:** `RecommendationScore__c` (Number, calculated) — Confidence score (0-100) of recommendation
- **Field:** `ContentPrepped__c` (Checkbox) — Rep confirms they reviewed recommendations

### VisitRecommendation__c (Custom Object — if needed for tracking)

- **Field:** `Visit__c` (Master-Detail) — Lookup to Visit__c
- **Field:** `RecommendationType__c` (Picklist) — "Content", "Talking Point", "Question", "Product Focus"
- **Field:** `RecommendationText__c` (Text Long) — Natural language recommendation
- **Field:** `Confidence__c` (Number 0-100) — ML model confidence score
- **Field:** `DataSource__c` (Picklist) — "Visit History", "Prescribing Data", "Publication Tracking", "Survey Response"
- **Field:** `ContentLink__c` (URL) — Link to recommended content (Salesforce ContentVersion or external library)
- **Field:** `Accepted__c` (Checkbox) — Did rep use this recommendation during visit?
- **Field:** `Outcome__c` (Picklist) — "Helpful", "Not Applicable", "Outdated"

### ContentVersion Object (from Salesforce)

- **Field:** `Title` — Content name
- **Field:** `VersionData` — File content
- **Field:** `ContentDocumentId` — Parent document ID
- **Field:** `FileExtension` — PDF, PPT, etc.
- **Field:** `Description` — Content summary

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **VisitRecommendation__c Object** | Custom Object (if new) | Track and score AI recommendations | Master-Detail to Visit__c; many-to-one relationship to capture multiple recommendations per visit |
| **PRM_VisitRecommendationEngine** | Integration Procedure | Fetch HealthcareProvider profile, query visit history, invoke ML model | Call before visit date; return ranked list of content + talking points |
| **ML Recommendation Model** | External Service (Einstein AI, Tableau CRM, or custom) | Analyze provider profile, past interactions, content performance; score recommendations | Inputs: hcpId, visitType, productFocus; Outputs: contentIds, talkingPoints, questions, confidence scores |
| **Visit Prep Card / Widget** | OmniScript Component / LWC | Display top 3-5 recommendations in collapsible format | Mobile-friendly; links to content; allow rep to dismiss/accept recommendation |
| **Content Performance Tracking** | Flow / Apex Trigger | Track which recommended content was presented and HCP reaction | Capture Outcome__c (Helpful/Not Applicable/Outdated) post-visit |
| **Recommendation Feedback Loop** | Apex Batch / Scheduled Flow | Post-visit, calculate Accepted vs. Total to refine model accuracy | Monthly job to improve recommendation quality over time |

### PRM_VisitRecommendationEngine Logic (Pseudocode)

```javascript
function generateVisitRecommendations(hcpId, visitType, visitDate) {
  // 1. Fetch HealthcareProvider profile
  hcp = query HealthcareProvider 
    WHERE Id = hcpId;
  
  // 2. Query past 12 months of visits
  visitHistory = query Visit__c 
    WHERE PrimaryHCP__c = hcpId 
    AND VisitDate__c >= LAST_N_MONTHS(12) 
    ORDERED BY VisitDate DESC;
  
  // 3. Extract features for ML model
  features = {
    specialty: hcp.Specialty__c,
    engagementScore: hcp.EngagementScore__c,
    keyInterests: hcp.KeyInterests__c.split(';'),
    visitFrequency: visitHistory.length,
    lastVisitDate: visitHistory[0].VisitDate__c,
    topicsDiscussedPast3Visits: extractTopics(visitHistory.sublist(0, 3)),
    visitType: visitType
  };
  
  // 4. Call external ML model (Einstein AI or custom)
  recommendations = callExternalModel(features);
  // Response: [
  //   { type: "Content", id: "069...", title: "Cardiology Update Q2 2026", confidence: 92 },
  //   { type: "TalkingPoint", text: "Recent indication expansion in HF", confidence: 87 },
  //   { type: "Question", text: "How are you managing treatment-resistant HTN?", confidence: 78 }
  // ]
  
  // 5. Create VisitRecommendation__c records
  for rec in recommendations {
    create VisitRecommendation__c {
      Visit__c = visitId,
      RecommendationType__c = rec.type,
      RecommendationText__c = rec.title OR rec.text,
      Confidence__c = rec.confidence,
      ContentLink__c = resolveContentUrl(rec.id)
    };
  }
  
  // 6. Update Visit__c.RecommendedContent__c (JSON)
  update Visit__c {
    RecommendedContent__c = JSON.serialize(recommendations),
    RecommendationScore__c = AVG(recommendations.confidence)
  };
  
  return recommendations;
}
```

### Example (Visit Recommendations Response)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "hcpId": "0012t000001a2cZAAQ",
  "hcpName": "Dr. Sarah Chen (Cardiology)",
  "recommendations": [
    {
      "type": "Content",
      "rank": 1,
      "confidence": 95,
      "title": "Heart Failure Management 2026 Clinical Update",
      "summary": "Latest data on your approved indication in HF; Dr. Chen published on this topic in Jan 2026",
      "contentType": "PDF Presentation",
      "link": "https://salesforce.com/files/069..."
    },
    {
      "type": "TalkingPoint",
      "rank": 2,
      "confidence": 88,
      "text": "Mention your recent FDA label expansion for Stage C HF (approved March 2026)",
      "dataSource": "Recent publications + prescribing data"
    },
    {
      "type": "Question",
      "rank": 3,
      "confidence": 82,
      "text": "How are you managing patients with HF who are intolerant to current therapies?",
      "rationale": "Dr. Chen frequently prescribes for treatment-resistant cases"
    },
    {
      "type": "Content",
      "rank": 4,
      "confidence": 76,
      "title": "Patient Case Study: 65M with HF + Hypertension",
      "summary": "Real-world example matching Dr. Chen's patient demographic",
      "contentType": "One-pager",
      "link": "https://salesforce.com/files/06a..."
    }
  ]
}
```

---

## Acceptance Criteria

### Scenario 1: Generate Recommendations for Scheduled Visit (Happy Path)

**Given** a rep schedules a visit to Dr. Chen (Cardiology, EngagementScore = 85) for visit type "Product Update",  
**When** the visit is saved,  
**Then** the system triggers PRM_VisitRecommendationEngine asynchronously.  
**And within 30 seconds**, recommendations are generated:
- **Top content recommendation:** Heart Failure Clinical Update (95% confidence) based on Dr. Chen's specialty + recent publication
- **Talking point:** Mention new FDA indication for Stage C HF
- **Question:** Treatment-resistant HF management

**And when** the rep opens the visit detail screen on their mobile app,  
**Then** a "Prep Card" displays at the top with collapsible sections:
- **"Recommended Content"** (1-2 clickable links)
- **"Key Talking Points"** (2-3 bullet points)
- **"Discussion Questions"** (1-2 open-ended questions)

---

### Scenario 2: Rep Reviews and Accepts Recommendation

**Given** the rep opens the prep card,  
**When** they click "View" on the Heart Failure PDF,  
**Then** a modal opens displaying the PDF inline or linking to Salesforce ContentVersion viewer.  
**And after viewing**, the rep can click **"Mark as Helpful"** which:
- Updates VisitRecommendation__c.Accepted__c = true
- Stores the rep's feedback for model improvement

---

### Scenario 3: Rep Dismisses Inapplicable Recommendation

**Given** the prep card displays 4 recommendations,  
**When** the rep reviews and determines that one talking point is outdated (e.g., "old FDA approval date"),  
**Then** they click the "X" button on that recommendation.  
**And the system**:
- Updates VisitRecommendation__c.Outcome__c = "Outdated"
- Removes it from the display
- Logs feedback for model retraining

---

### Scenario 4: Content Performance Tracking Post-Visit

**Given** a rep completes a visit after reviewing recommendations,  
**When** they close the visit record,  
**Then** the system queries VisitRecommendation__c records for that visit and calculates:
- **Acceptance Rate:** 3 out of 4 recommendations marked as "Helpful"
- **Confidence vs. Outcome:** Model's 95% confidence recommendation was indeed helpful (positive feedback loop)

**And at month-end**, a batch job:
- Aggregates recommendation quality metrics
- Identifies high-confidence recommendations with low acceptance (potential model drift)
- Retrains the ML model with new feedback

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **ML Model Source** Should recommendations come from Salesforce Einstein AI, Tableau CRM, or a custom ML model? | Architecture; licensing; integration complexity | Technical Lead + Product |
| 2 | **Real-time vs. Batch** Should recommendations be generated in real-time when visit is scheduled (synchronous), or pre-computed nightly (batch)? | Performance; latency; computational cost | Technical Lead |
| 3 | **External Data Integration** Can the system access external prescribing data (e.g., IQVIA, Symphony IRI) to inform recommendations, or only internal Salesforce data? | Data governance; licensing; privacy compliance | Compliance Officer + IT |
| 4 | **Content Repository** Should recommended content come from Salesforce ContentVersion, an external content library (e.g., Showpad), or both? | UX; content governance; vendor integration | Marketing Operations |
| 5 | **Recommendation Explainability** Should the system explain WHY a recommendation was made (e.g., "Based on your recent publication on HF")? | Transparency; rep trust; UX | Product Manager |
| 6 | **Personalization Scope** Should reps be able to manually override or provide feedback on recommendations ("I don't want to see HF content anymore")? | User control; model tuning | Product Manager |
| 7 | **Feedback Loop Frequency** How often should the model be retrained with new feedback (daily, weekly, monthly)? | Model accuracy; computational cost | Data Science |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **VisitRecommendation__c Object** | Custom Object | MEDIUM | Stores recommendations and feedback; enables feedback loop |
| **PRM_VisitRecommendationEngine** | Integration Procedure | HIGH | Asynchronous calls to external ML service; must handle failures gracefully |
| **External ML Model** | Third-party Service (Einstein/custom) | HIGH | Core intelligence engine; accuracy directly impacts rep effectiveness |
| **Prep Card UI** | OmniScript LWC | HIGH | User-facing; must be fast, mobile-friendly, non-intrusive |
| **Content Performance Tracking** | Batch / Scheduled Flow | MEDIUM | Post-visit analytics; enables model improvement over time |
| **Analytics & Reporting** | Dashboards | MEDIUM | Track recommendation acceptance, impact on deal outcomes, model accuracy |

---

## Definition of Done Checklist

- [ ] VisitRecommendation__c Custom Object created with all fields
- [ ] PRM_VisitRecommendationEngine Integration Procedure implemented and tested
- [ ] External ML model integration complete (Einstein AI or alternative) and authenticated
- [ ] Visit Prep Card LWC component built and responsive on mobile
- [ ] Recommendations display in rank order (by confidence score) on visit detail screen
- [ ] Rep can mark recommendations as "Helpful", "Not Applicable", or "Outdated"
- [ ] Dismissed recommendations removed from display immediately
- [ ] Post-visit feedback captured to VisitRecommendation__c.Outcome__c field
- [ ] Monthly batch job aggregates feedback and prepares model retraining data
- [ ] ML model retrained with feedback (initial run; assess accuracy improvement)
- [ ] Dashboard: "Recommendation Acceptance Rate by Specialty", "Avg Deal Size by Recommendation Usage"
- [ ] Apex test coverage ≥ 85% for recommendation engine
- [ ] QA sign-off: Mobile prep card loads in < 3 seconds, survives 10+ recommendations
- [ ] Documentation: Rep user guide on using recommendations; Admin guide on model tuning
- [ ] Training: Field team onboarding on how to interpret and act on recommendations

---

---

## Summary: Epic 1 Deliverables

Three implementation-ready user stories have been detailed with full technical specifications:

| Story | Feature | Objects | Complexity | Effort Estimate |
|-------|---------|---------|------------|-----------------|
| **US 1.1** | Schedule multi-HCP group visits | Visit__c, VisitAttendee__c, Account, User | Medium | 8-12 days |
| **US 1.2** | Visit conflict validation & alerts | Visit__c, VisitFrequencyRule__c, Apex Trigger | High | 10-14 days |
| **US 1.3** | AI-backed visit recommendations | Visit__c, VisitRecommendation__c, External ML | High | 12-18 days |

**Total Epic 1 Effort:** 30-44 days  
**Priority:** P0 (all three stories are foundational to Visit Management)

---

---

# Epic 2: Visit Execution & Compliance

## USER STORY 2.1: Present Intelligent Content Directly from Mobile Device

**Persona:** Field Sales Representative, Content Manager, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, ContentVersion, ContentDocument, ContentDistribution, PresentationLog__c (custom)  
**Integration Procedures:** PRM_ContentRetrieval (hypothetical), External Content Library (Showpad, Veeva, etc.)  
**Relevant Requirements:** FHN-15, FHN-83 (Intelligent content presentation)

---

## Story

**As a** Field Sales Representative,  
**I want** to access, search, and present pre-approved marketing materials, product slides, clinical studies, and other intelligent content directly from my mobile device during a visit,  
**So that** I can seamlessly share compliant, relevant materials with HCPs without needing to switch between apps or manually search for content.

**Why it matters:** Reps currently waste time searching for content on laptops or email, breaking the flow of conversation. Native in-app content access keeps reps focused on the HCP interaction, reduces non-compliant sharing (outdated materials), and provides audit trails for every piece of content shared.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Visit Execution | Mobile Visit Screen | During visit, rep opens "Content Library" section | Salesforce ContentVersion, external library via API | Visit__c, PresentationLog__c |
| Content Auditing | Post-Visit Report | Capture which content was presented | PresentationLog__c records | Visit__c |

---

## Current State (from Salesforce Object Model)

### ContentVersion Object

- **Field:** `Title` (Text) — Content name/title
- **Field:** `FileExtension` — PDF, PPTX, MP4, etc.
- **Field:** `CreatedDate` (DateTime) — When content was uploaded
- **Field:** `IsLatest` (Checkbox) — Is this the latest version?
- **Field:** `ContentDocumentId` (Lookup) — Parent ContentDocument
- **Field:** `Description` — Content summary or metadata
- **Field:** `VersionNumber` — Version tracking
- **Custom Fields:** `ContentType__c`, `ProductFocus__c`, `TherapeuticArea__c`, `ApprovalStatus__c`, `LastApprovedDate__c`

### Visit__c (Relevant Fields)

- **Field:** `VisitDate__c`
- **Field:** `PrimaryHCP__c`
- **Field:** `ContentPresented__c` (JSON array or related list) — Content IDs shown during visit
- **Field:** `VisitStatus__c`
- **Related List:** PresentationLog__c (if custom object created)

### PresentationLog__c (Custom Object — for tracking)

- **Field:** `Visit__c` (Master-Detail) — Lookup to Visit__c
- **Field:** `ContentVersion__c` (Lookup) — Which content was shown
- **Field:** `PresentationSequence__c` (Number) — Order of presentation (1st, 2nd, 3rd)
- **Field:** `DurationSeconds__c` (Number) — How long was content shown (if tracked)
- **Field:** `HCPReaction__c` (Picklist) — "Very Engaged", "Engaged", "Neutral", "Disengaged", "Not Tracked"
- **Field:** `Notes__c` (Text Long) — Rep's notes on HCP feedback
- **Field:** `PresentedDate__c` (DateTime) — Auto-populated with visit date/time

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **ContentLibrary LWC** | Lightning Web Component | Mobile-friendly content browser/search | Search by title, product, therapeutic area; filter by approval status; display thumbnail preview |
| **Content Filtering Logic** | Apex / Flow | Filter content based on HCP specialty, product focus, and user permissions | Only show content applicable to HCP record type; honor field-level permissions |
| **PresentationLog__c Object** | Custom Object | Track every piece of content presented | Master-Detail to Visit__c; auto-link content; capture reaction/notes |
| **Content Preview Component** | LWC | Display PDF, video, or interactive presentation in mobile browser | Support full-screen mode; allow zoom/pan for mobile; handle large files efficiently |
| **Content Distribution Tracking** | Apex Trigger / Flow | Log presentation to PresentationLog__c when rep clicks "Present" button | Timestamp and associate with visit and HCP |
| **External Content Integration** | Integration Procedure | If using external library (Showpad, Veeva), fetch content metadata and sync to Salesforce | Periodic sync or real-time API calls |

### ContentLibrary LWC Search & Filter Logic (Pseudocode)

```javascript
class ContentLibrary extends LightningElement {
  @api visitId;
  @api hcpId;
  
  contentList = [];
  filteredList = [];
  searchTerm = '';
  selectedFilters = {};

  async connectedCallback() {
    // 1. Fetch HCP specialty and product focus
    hcp = await fetchHcp(this.hcpId);
    
    // 2. Query ContentVersion with applicable filters
    this.contentList = await queryContentVersions({
      therapeuticArea: hcp.TherapeuticArea__c,
      productFocus: hcp.PrescribingPattern__c,
      approvalStatus: 'Approved',
      isLatest: true
    });
    
    // 3. Apply additional filters (user role, device type)
    this.filteredList = applyPermissionFilters(this.contentList, userRole);
  }

  async handleSearch(event) {
    this.searchTerm = event.target.value;
    this.filteredList = this.contentList.filter(content =>
      content.title.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      content.description.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
  }

  async handleFilterChange(event) {
    const filterKey = event.target.dataset.filterKey;
    const filterValue = event.target.value;
    this.selectedFilters[filterKey] = filterValue;
    
    this.filteredList = this.contentList.filter(content =>
      Object.entries(this.selectedFilters).every(([key, value]) =>
        value === '' || content[key] === value
      )
    );
  }

  async handlePresentContent(event) {
    const contentVersionId = event.currentTarget.dataset.contentId;
    const content = this.filteredList.find(c => c.id === contentVersionId);
    
    // 1. Open full-screen preview
    this.openPreview(content);
    
    // 2. Asynchronously log to PresentationLog__c
    await createPresentationLog({
      visitId: this.visitId,
      contentVersionId: contentVersionId,
      sequenceNumber: this.getPresentationSequence()
    });
  }

  getPresentationSequence() {
    // Count existing PresentationLog__c records for this visit
    return this.existingPresentations.length + 1;
  }
}
```

### Example (Content Library Response)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "hcpId": "0012t000001a2cZAAQ",
  "hcpTherapeuticArea": "Cardiology",
  "contentList": [
    {
      "id": "069...",
      "title": "Heart Failure Management 2026 Clinical Update",
      "type": "PDF Presentation",
      "size": "12 MB",
      "approvalStatus": "Approved",
      "lastApprovedDate": "2026-02-15",
      "therapeuticArea": "Cardiology",
      "productFocus": ["Product A", "Product B"],
      "thumbnail": "https://salesforce.com/thumbs/069..."
    },
    {
      "id": "06a...",
      "title": "Patient Case Study: HF Management",
      "type": "One-pager (PDF)",
      "size": "2 MB",
      "approvalStatus": "Approved",
      "lastApprovedDate": "2026-03-01",
      "therapeuticArea": "Cardiology",
      "productFocus": ["Product A"],
      "thumbnail": "https://salesforce.com/thumbs/06a..."
    },
    {
      "id": "06b...",
      "title": "FDA Label Update: Stage C HF Indication",
      "type": "Summary (PDF)",
      "size": "800 KB",
      "approvalStatus": "Approved",
      "lastApprovedDate": "2026-03-10",
      "therapeuticArea": "Cardiology",
      "productFocus": ["Product A"],
      "thumbnail": "https://salesforce.com/thumbs/06b..."
    }
  ]
}
```

---

## Acceptance Criteria

### Scenario 1: Rep Searches for Content by Title (Happy Path)

**Given** a rep is in a visit to Dr. Chen (Cardiology),  
**When** they click the "Content Library" tab on the visit screen,  
**Then** the app displays:
- Search box at the top
- Filter options (Therapeutic Area, Product, Content Type)
- List of 5-10 pre-filtered "recommended" content items matching HCP's specialty

**And when** the rep types "Heart Failure" in the search box,  
**Then** the list filters to show only content with "Heart Failure" in title or description (typically 3-5 results).

---

### Scenario 2: Rep Presents Content and Views Full Screen

**Given** the filtered content list displays the "Heart Failure Clinical Update" PDF,  
**When** the rep clicks "View" or "Present",  
**Then** the app:
- Opens the PDF in full-screen mode
- Displays page number, zoom controls, and back button
- Logs this presentation action to PresentationLog__c immediately

**And when** the rep exits the preview,  
**Then** they return to the content library list, and the presented content is marked as "Just Presented" (visual indicator).

---

### Scenario 3: Content Approval Status Check

**Given** a rep is browsing the content library,  
**When** they attempt to present content that is NOT marked "Approved",  
**Then** the system prevents presentation and displays:
- **Warning:** "This content is not approved for distribution. Contact Compliance."
- Content grayed out, not clickable

---

### Scenario 4: Large File Handling (Performance)

**Given** a rep is on a slower mobile network (4G),  
**When** they open a 50 MB video file in the content library,  
**Then** the system:
- Shows a loading spinner with estimated download time
- Allows streaming (progressive download) instead of forcing full download
- Gracefully degrades to lower resolution if bandwidth is low

---

### Scenario 5: Track Presentation Details

**Given** a rep presents 3 pieces of content during a visit (PDF, one-pager, summary),  
**When** they close the visit screen,  
**Then** PresentationLog__c contains 3 records:
- Sequence 1: "Heart Failure Clinical Update PDF" | "Very Engaged" | HCP reaction captured
- Sequence 2: "Case Study One-pager" | "Engaged"
- Sequence 3: "FDA Label Summary" | "Neutral"

**And when** the Compliance Manager reviews the audit trail,  
**Then** they can see exactly what was presented in what order.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **External Content Library** Should content come only from Salesforce ContentVersion, or integrate with Showpad/Veeva/external library? | Architecture; licensing; sync complexity | Marketing Operations |
| 2 | **Content Filtering Strategy** Should content be filtered automatically by specialty/product, or should reps see all approved content and filter manually? | UX; compliance risk | Product Manager |
| 3 | **Offline Availability** Should reps be able to pre-download content for offline access during hospital visits with no connectivity? | Mobile app design; storage; sync frequency | Technical Lead |
| 4 | **HCP Reaction Tracking** Should rep feedback on HCP engagement (Very Engaged, Neutral, Disengaged) be required or optional? | Data quality; reporting accuracy | Analytics Lead |
| 5 | **Content Versioning** If content is updated while a visit is in progress, should rep see the new version or continue with old version until visit closes? | Data consistency; UX | Product Manager |
| 6 | **Large File Optimization** For files > 20 MB (videos), should the system transcode to mobile-friendly formats (lower resolution) automatically? | Performance; storage cost | Technical Lead |
| 7 | **Presentation Duration Tracking** Should the system track how long each piece of content is presented (e.g., 30 seconds for one-pager)? | Analytics; engagement metrics | Analytics Lead |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **ContentLibrary LWC** | Mobile Component | HIGH | User-facing; directly affects rep workflow efficiency |
| **PresentationLog__c Object** | Custom Object | HIGH | Audit trail; compliance-critical |
| **Content Filtering Logic** | Apex / Flow | MEDIUM | Performance depends on content volume; must be optimized for mobile |
| **External Library Integration** | Integration Procedure | MEDIUM | If using Showpad/Veeva, requires licensing and API maintenance |
| **Offline Caching** | Mobile Framework | MEDIUM | If implemented, adds complexity to sync and conflict resolution |
| **Performance Optimization** | Mobile Infrastructure | HIGH | Large file handling; network latency; mobile battery consumption |

---

## Definition of Done Checklist

- [ ] ContentLibrary LWC component created and tested on mobile devices
- [ ] Content search and filtering logic implemented (by title, therapeutic area, product, content type)
- [ ] Content permission filtering applied (based on user role and HCP record type)
- [ ] PresentationLog__c custom object created with all required fields
- [ ] Full-screen content preview component built (PDF, video, one-pager support)
- [ ] Zoom, pan, and page navigation controls working on mobile
- [ ] Content presentation automatically logged to PresentationLog__c (with sequence and timestamp)
- [ ] HCP reaction capture form added to content library (optional but encouraged)
- [ ] Approval status validation: blocked content grayed out and non-clickable
- [ ] Large file handling tested (streaming, progressive download, low-bandwidth fallback)
- [ ] Integration with external content library completed (if applicable)
- [ ] Offline content pre-download capability implemented (if applicable)
- [ ] Audit report: "Content Presented by Rep and Date" dashboard built
- [ ] Apex test coverage ≥ 90% for filtering and logging logic
- [ ] QA sign-off: Content library loads in < 2 seconds; preview opens in < 3 seconds
- [ ] Documentation: Rep user guide on accessing and presenting content
- [ ] Training: Field team onboarding on content library navigation

---

## USER STORY 2.2: Disburse Samples and Capture Digital Signature

**Persona:** Field Sales Representative, Sample Inventory Manager, Compliance Officer, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, SampleDistribution__c (custom), HealthcarePractitionerNpi__c, SampleInventory__c, SignatureLog__c (custom)  
**Integration Procedures:** PRM_SampleInventorySync, PRM_SignatureCapture  
**Relevant Requirements:** FHN-15, FHN-101 (Sample distribution), FHN-102 (Digital signatures)

---

## Story

**As a** Field Sales Representative,  
**I want** to select samples from my mobile inventory, document the HCP's receipt through a digital signature, and sync the transaction back to Salesforce,  
**So that** sample inventory is accurately tracked, and we maintain compliance with regulations requiring documented transfer of value.

**Why it matters:** Manual sample tracking (spreadsheets, lost receipts) leads to inventory discrepancies, audit failures, and compliance violations. Digital signatures provide irrefutable proof of transfer, automatically sync to back-office systems, and enable real-time inventory management.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Sample Selection | Visit Screen | Rep selects samples from pre-loaded inventory | Reps' device inventory (synced nightly), SampleInventory__c | Visit__c, SampleDistribution__c |
| Signature Capture | Mobile Signature Pad | HCP signs on rep's device | Touch input, signature engine | SignatureLog__c |
| Inventory Sync | Backend Batch Job | After visit submit, deduct from system inventory | SampleDistribution__c, Inventory API | SampleInventory__c |

---

## Current State (from Salesforce Object Model)

### SampleInventory__c (Custom Object)

- **Field:** `SampleName__c` (Lookup to Product) — Product name or SKU
- **Field:** `Quantity__c` (Number) — Current inventory count
- **Field:** `AssignedToUser__c` (Lookup to User) — Rep assigned this inventory
- **Field:** `Location__c` (Text) — Office, car, warehouse
- **Field:** `ExpirationDate__c` (Date) — Sample expiration
- **Field:** `DistributionStatus__c` (Picklist) — "In Stock", "Distributed", "Expired", "Damaged"

### SampleDistribution__c (Custom Object)

- **Field:** `Visit__c` (Lookup to Visit__c)
- **Field:** `Sample__c` (Lookup to Product)
- **Field:** `QuantityDistributed__c` (Number)
- **Field:** `RecipientNPI__c` (Lookup to HealthcarePractitionerNpi__c)
- **Field:** `DistributionDate__c` (DateTime)
- **Field:** `IsSignedByRecipient__c` (Checkbox)
- **Field:** `SignatureLog__c` (Lookup to SignatureLog__c)

### SignatureLog__c (Custom Object — for tracking signatures)

- **Field:** `Visit__c` (Lookup to Visit__c)
- **Field:** `SignatureImage__c` (LongTextArea, base64-encoded or ContentVersion reference)
- **Field:** `SignedByName__c` (Text) — Name of person who signed
- **Field:** `SignedByTitle__c` (Text) — Title/role (e.g., "MD", "DO")
- **Field:** `SignatureTimestamp__c` (DateTime) — When signature was captured
- **Field:** `SignatureDeviceInfo__c` (Text) — Device and browser info (for forensics)
- **Field:** `AuthenticityCertificate__c` (Text) — Audit/forensic proof of legitimacy

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **SampleDistribution UI** | OmniScript / LWC | Rep selects samples from local inventory, enters quantity | Dropdown by product; real-time quantity validation; prevent over-distribution |
| **Signature Pad Component** | LWC + Third-party Library | Capture digital signature on mobile device | Use HTML5 canvas or Signature.js library; support touch and stylus; generate high-fidelity image |
| **Signature Image Storage** | Salesforce Files (ContentVersion) | Store signature as image (PNG/JPG) in Salesforce | Reference from SignatureLog__c via ContentVersion lookup |
| **Inventory Deduction Logic** | Apex Trigger / Flow | When Visit__c submitted, deduct SampleDistribution__c quantities from SampleInventory__c | Transactional; prevent double-counting |
| **Offline Sample Cache** | Mobile App Service | Pre-sync rep's inventory to device before visit (nightly or on-demand) | Enable offline selection; reconcile on next sync |
| **PRM_SampleInventorySync** | Integration Procedure | Sync SampleDistribution__c back to backend ERP/inventory system | Real-time or batch; handle sync failures gracefully |

### Signature Capture Component (Pseudocode)

```javascript
class SignaturePad extends LightningElement {
  @api visitId;
  @api hcpName;
  
  signaturePadElement;
  signatureCanvas;
  signatureData = null;
  isDrawing = false;

  renderedCallback() {
    // Initialize HTML5 canvas for signature capture
    this.signatureCanvas = this.template.querySelector('canvas#signaturePad');
    const ctx = this.signatureCanvas.getContext('2d');
    
    // Set canvas dimensions to match device viewport
    this.signatureCanvas.width = window.innerWidth - 40;
    this.signatureCanvas.height = 300;
    
    // Attach touch/mouse event listeners
    this.signatureCanvas.addEventListener('touchstart', this.handleSignatureStart.bind(this));
    this.signatureCanvas.addEventListener('touchmove', this.handleSignatureMove.bind(this));
    this.signatureCanvas.addEventListener('touchend', this.handleSignatureEnd.bind(this));
  }

  handleSignatureStart(event) {
    this.isDrawing = true;
    const touch = event.touches[0];
    const x = touch.clientX - this.signatureCanvas.getBoundingClientRect().left;
    const y = touch.clientY - this.signatureCanvas.getBoundingClientRect().top;
    
    const ctx = this.signatureCanvas.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  handleSignatureMove(event) {
    if (!this.isDrawing) return;
    
    event.preventDefault();
    const touch = event.touches[0];
    const x = touch.clientX - this.signatureCanvas.getBoundingClientRect().left;
    const y = touch.clientY - this.signatureCanvas.getBoundingClientRect().top;
    
    const ctx = this.signatureCanvas.getContext('2d');
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    ctx.lineTo(x, y);
    ctx.stroke();
  }

  handleSignatureEnd(event) {
    this.isDrawing = false;
    
    // Capture signature as base64
    this.signatureData = this.signatureCanvas.toDataURL('image/png');
  }

  async handleClearSignature() {
    const ctx = this.signatureCanvas.getContext('2d');
    ctx.clearRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
    this.signatureData = null;
  }

  async handleSubmitSignature() {
    if (!this.signatureData) {
      alert('Please sign before submitting.');
      return;
    }

    // 1. Create ContentVersion for signature image
    const contentVersionId = await createContentVersion(this.signatureData);
    
    // 2. Create SignatureLog__c record
    const signatureLog = await createSignatureLog({
      visitId: this.visitId,
      contentVersionId: contentVersionId,
      signedByName: this.template.querySelector('[data-name]').value,
      signedByTitle: this.template.querySelector('[data-title]').value,
      signatureTimestamp: new Date().toISOString(),
      signatureDeviceInfo: `${navigator.userAgent} | ${window.innerWidth}x${window.innerHeight}`
    });
    
    // 3. Update SampleDistribution__c.IsSignedByRecipient = true
    await updateSampleDistribution({
      visitId: this.visitId,
      isSignedByRecipient: true,
      signatureLogId: signatureLog.id
    });
    
    // 4. Emit success event
    this.dispatchEvent(new CustomEvent('signaturesubmitted', { detail: signatureLog }));
  }
}
```

### Example (Sample Distribution & Signature Response)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "samplesDistributed": [
    {
      "id": "a032t000001B1ZAAX",
      "sampleName": "Product A - 30 Tablets",
      "quantityDistributed": 3,
      "recipientNPI": "1234567890",
      "distributionDate": "2026-04-15T10:30:00Z",
      "isSignedByRecipient": true,
      "signatureLog": {
        "id": "a052t000001C1ZAAX",
        "signedByName": "Dr. Sarah Chen",
        "signedByTitle": "MD",
        "signatureTimestamp": "2026-04-15T10:31:45Z",
        "signatureImageUrl": "https://salesforce.com/files/069..."
      }
    },
    {
      "id": "a032t000001B2ZAAX",
      "sampleName": "Product B - 7-pack",
      "quantityDistributed": 1,
      "recipientNPI": "1234567890",
      "distributionDate": "2026-04-15T10:31:50Z",
      "isSignedByRecipient": true,
      "signatureLog": {
        "id": "a052t000001C2ZAAX",
        "signedByName": "Dr. Sarah Chen",
        "signedByTitle": "MD",
        "signatureTimestamp": "2026-04-15T10:32:00Z",
        "signatureImageUrl": "https://salesforce.com/files/06a..."
      }
    }
  ],
  "inventoryAdjustment": {
    "beforeCount": { "Product A": 10, "Product B": 5 },
    "afterCount": { "Product A": 7, "Product B": 4 },
    "syncStatus": "Pending"
  }
}
```

---

## Acceptance Criteria

### Scenario 1: Select and Distribute Samples (Happy Path)

**Given** a rep has 10 units of Product A and 5 units of Product B in their local inventory,  
**When** they click "Add Sample" on the visit screen,  
**Then** a modal displays:
- Product dropdown (filtered to available inventory)
- Quantity input (max quantity = available stock)
- "Add" button

**And when** the rep selects "Product A" and enters quantity "3",  
**Then** the system:
- Validates that 3 units are in stock (passes)
- Adds Product A (3 units) to SampleDistribution list
- Display: "Product A - 3 units" with remove option

---

### Scenario 2: Prevent Over-Distribution

**Given** a rep attempts to distribute 12 units of Product A (only 10 in stock),  
**When** they enter "12" in the quantity field,  
**Then** the system:
- Displays error: "Only 10 units available. Maximum quantity is 10."
- Disables the "Add" button until corrected

---

### Scenario 3: Capture Signature on Mobile Device

**Given** the rep has added 3 samples and clicks "Get Signature",  
**When** the signature pad displays,  
**Then** the HCP (Dr. Chen) signs on the touch screen.  
**And the system captures**:
- Signature image (base64-encoded PNG)
- HCP name: "Dr. Sarah Chen"
- HCP title: "MD"
- Timestamp: 2026-04-15T10:31:45Z
- Device info: "iPhone 15 Pro, iOS 17"

---

### Scenario 4: Signature Validation and Storage

**Given** the HCP completes the signature,  
**When** they click "Confirm Signature",  
**Then** the system:
- Stores signature image as ContentVersion
- Creates SignatureLog__c record with all metadata
- Updates SampleDistribution__c.IsSignedByRecipient = true
- Displays confirmation: "Signature captured and saved."

---

### Scenario 5: Inventory Deduction on Visit Submission

**Given** the rep submits the visit after distributing 3 units of Product A and 1 unit of Product B,  
**When** Visit__c.VisitStatus changes to "Submitted",  
**Then** an Apex trigger:
- Queries all SampleDistribution__c records for this visit
- Deducts from SampleInventory__c:
  - Product A: 10 - 3 = 7
  - Product B: 5 - 1 = 4
- Syncs change to external inventory system via PRM_SampleInventorySync

**And after sync**, the backend returns success, and the inventory is updated system-wide.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Signature Legitimacy** Should the system capture biometric data or device forensics to verify signature authenticity? | Legal/Compliance implications; technical complexity | Compliance Officer |
| 2 | **Offline Inventory** Should sample inventory be pre-cached on rep's device for offline access, or require real-time sync? | Mobile UX; sync conflicts; data freshness | Technical Lead |
| 3 | **Return of Samples** If HCP returns unused samples, how should inventory be adjusted (e.g., re-add to rep's stock)? | Inventory logic; workflows; reverse transactions | Supply Chain |
| 4 | **Signature Format** Should signatures be captured as image (PNG), digital certificate (PKI), or both? | Legal defensibility; file size | Legal / Compliance |
| 5 | **Inventory Hierarchy** Should inventory tracking be at rep level, territory level, or regional level for distribution? | Reporting; access control; approval workflows | Operations |
| 6 | **Regulatory Compliance** Which regulations apply (e.g., FDA, DEA, state pharma regulations)? | Field requirements; validation logic | Compliance Officer |
| 7 | **Multi-Package Distributions** Should rep be able to distribute same product to multiple HCPs in one visit (e.g., lunch-and-learn)? | Sample tracking; allocation logic | Product Manager |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **SampleDistribution UI** | OmniScript / LWC | HIGH | Direct rep UX; affects sample tracking accuracy |
| **Signature Pad Component** | Mobile Component | HIGH | Compliance-critical; must be legally defensible |
| **SignatureLog__c Object** | Custom Object | HIGH | Audit trail; regulatory compliance requirement |
| **Inventory Deduction Logic** | Apex Trigger | HIGH | Transactional; prevents double-counting or loss of inventory data |
| **Offline Caching** | Mobile Framework | MEDIUM | Performance; sync conflict management |
| **External Inventory Sync** | Integration Procedure | MEDIUM | Requires coordination with back-office ERP |

---

## Definition of Done Checklist

- [ ] SampleDistribution__c custom object created with all required fields
- [ ] SignatureLog__c custom object created with all required fields
- [ ] Sample selection UI built (dropdown by product, quantity input, validation)
- [ ] Signature pad component implemented (HTML5 canvas or library)
- [ ] Touch/stylus input support verified on mobile devices
- [ ] Signature image stored as ContentVersion with metadata
- [ ] Inventory deduction Apex trigger implemented and tested
- [ ] Prevents over-distribution (validation on quantity field)
- [ ] Handles offline inventory cache (nightly pre-sync to device)
- [ ] Apex test coverage ≥ 90% for inventory and signature logic
- [ ] Integration test: Distribute 3 samples, capture signature, submit, verify inventory deduction
- [ ] Compliance review: Signature capture method approved by Legal
- [ ] QA sign-off: Signature pad works smoothly on various mobile devices (iOS, Android)
- [ ] External inventory system sync tested (mock API)
- [ ] Audit report: "Sample Distributions by Rep" dashboard built
- [ ] Documentation: Rep user guide on sample distribution and signature capture
- [ ] Training: Field team onboarding on sample tracking process

---

---

## USER STORY 2.3: Enforce State License Validations and Practitioner Sample Limits

**Persona:** Compliance Manager, Field Sales Representative, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, HealthcarePractitioner, HealthcarePractitionerLicense__c, SampleLimitPolicy__c, ComplianceAuditLog__c  
**Integration Procedures:** PRM_LicenseValidator, PRM_SampleLimitChecker  
**Relevant Requirements:** FHN-15, FHN-85 (License validation), FHN-86 (Sample limits)

---

## Story

**As a** Compliance Manager or Field Sales Representative,  
**I want** the system to automatically validate that the HCP holds a valid, active license in the state where we're distributing samples, and that sample distribution does not exceed regulatory limits (e.g., DEA practitioner sample limits),  
**So that** we maintain compliance with federal and state regulations and avoid distributing samples to unlicensed practitioners.

**Why it matters:** Distributing samples to unlicensed practitioners or exceeding DEA limits is a federal violation that triggers audits, fines, and reputational damage. Manual license checks are error-prone. Automated validation prevents violations at the point of transaction.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Signature Capture | Signature Pad Screen | Before HCP signature accepted, validate license + limits | HealthcarePractitionerLicense__c, SampleLimitPolicy__c, past SampleDistribution__c | Visit__c |
| Compliance Audit | Audit Trail | Log all validations (pass/fail) for compliance review | ComplianceAuditLog__c | Visit__c |

---

## Current State (from Salesforce Object Model)

### HealthcarePractitionerLicense__c (Custom Object)

- **Field:** `HealthcarePractitioner__c` (Lookup)
- **Field:** `State__c` (Picklist) — Two-letter state code (GA, NY, CA, etc.)
- **Field:** `LicenseNumber__c` (Text) — State license number
- **Field:** `LicenseType__c` (Picklist) — "MD", "DO", "RN", "PA", "NP", etc.
- **Field:** `IssuedDate__c` (Date)
- **Field:** `ExpirationDate__c` (Date)
- **Field:** `IsActive__c` (Checkbox, calculated) — True if not expired and no suspension
- **Field:** `DEANumber__c` (Text) — DEA registration number (if applicable)
- **Field:** `DEAExpiration__c` (Date)

### SampleLimitPolicy__c (Custom Metadata Type or Custom Object)

- **Field:** `RuleDescription__c` (Text) — "Max 30 units per year per practitioner", "Max 5 units per month"
- **Field:** `SampleType__c` (Picklist) — "All", "Prescription Only", "OTC"
- **Field:** `LimitQuantity__c` (Number) — Max units allowed
- **Field:** `TimePeriod__c` (Picklist) — "Year", "Month", "Quarter"
- **Field:** `ApplicableStates__c` (Multi-select) — Which states (e.g., "GA,CA,NY" or "All")
- **Field:** `BypassRequiresApproval__c` (Checkbox) — Does exceeding limit require Compliance Manager approval?

### ComplianceAuditLog__c (Custom Object)

- **Field:** `Visit__c` (Lookup)
- **Field:** `ValidationCheckName__c` (Text) — "License Active", "State Match", "Sample Limit"
- **Field:** `Result__c` (Picklist) — "Pass", "Fail", "Warning"
- **Field:** `CheckTimestamp__c` (DateTime)
- **Field:** `FailureReason__c` (Text Long) — Why did it fail?
- **Field:** `ApprovedByCompliance__c` (Lookup to User) — Who overrode the failure?

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **PRM_LicenseValidator** | Integration Procedure | Check if HCP holds valid, active license in visit state | Query HealthcarePractitionerLicense__c; check IsActive and state match; return pass/fail |
| **PRM_SampleLimitChecker** | Integration Procedure | Check if sample distribution exceeds DEA/regulatory limits | Query past SampleDistribution__c for HCP; sum quantities; compare to SampleLimitPolicy__c |
| **Pre-Signature Validation Flow** | Apex Trigger / Flow | Before signature is accepted, run both validators | Block signature if critical validations fail; warn if warning-level issues |
| **Compliance Audit Log** | Apex Trigger | Log all validation results to ComplianceAuditLog__c | Captures all checks (pass/fail); provides full audit trail |

### PRM_LicenseValidator Logic (Pseudocode)

```javascript
function validateLicense(visitId, hcpId, visitState) {
  // 1. Fetch HealthcareP ractitioner and licenses
  hcp = query HealthcarePractitioner WHERE Id = hcpId;
  licenses = query HealthcarePractitionerLicense__c 
    WHERE HealthcarePractitioner__c = hcpId 
    AND State__c = visitState;
  
  // 2. Check if any active license exists in the state
  activeLicenses = licenses.filter(lic => 
    lic.IsActive__c == true 
    AND lic.ExpirationDate__c >= TODAY()
  );
  
  if (activeLicenses.length == 0) {
    return {
      passed: false,
      checkName: "License Active",
      state: visitState,
      reason: `No active license found for ${hcp.Name} in ${visitState}`,
      action: "BLOCK"
    };
  }
  
  // 3. Check DEA if applicable
  if (hcp.SpecialtyType__c == "Prescriber") {
    deaLicense = activeLicenses.find(lic => lic.DEANumber__c != null);
    if (!deaLicense || deaLicense.DEAExpiration__c < TODAY()) {
      return {
        passed: false,
        checkName: "DEA Registration Active",
        reason: `DEA registration expired or missing`,
        action: "BLOCK"
      };
    }
  }
  
  // 4. Return success
  return {
    passed: true,
    checkName: "License Active",
    licenseNumber: activeLicenses[0].LicenseNumber__c,
    deaNumber: activeLicenses[0].DEANumber__c || "N/A",
    action: "ALLOW"
  };
}

function checkSampleLimits(visitId, hcpId, sampleDistributionList) {
  // 1. Query applicable sample limit policies
  policies = query SampleLimitPolicy__c 
    WHERE ApplicableStates__c contains visitState 
    OR ApplicableStates__c = 'All';
  
  failures = [];
  
  // 2. For each policy, check if new distribution would exceed limit
  for policy in policies {
    // Query past distributions in the time period
    pastDistributions = query SampleDistribution__c 
      WHERE RecipientNPI__c = hcpNpi 
      AND CreatedDate >= calculatePeriodStart(policy.TimePeriod__c)
      AND CreatedDate < calculatePeriodEnd(policy.TimePeriod__c);
    
    pastQuantity = pastDistributions.sum(sd => sd.QuantityDistributed__c);
    newQuantity = sampleDistributionList.sum(sd => sd.quantityDistributed);
    totalQuantity = pastQuantity + newQuantity;
    
    if (totalQuantity > policy.LimitQuantity__c) {
      failures.push({
        passed: false,
        checkName: "Sample Limit",
        policyDescription: policy.RuleDescription__c,
        timePeriod: policy.TimePeriod__c,
        limit: policy.LimitQuantity__c,
        current: pastQuantity,
        proposed: newQuantity,
        total: totalQuantity,
        action: policy.BypassRequiresApproval__c ? "REQUIRE_APPROVAL" : "WARN"
      });
    }
  }
  
  return failures.length == 0 ? { passed: true, action: "ALLOW" } : failures;
}
```

### Example (License & Limit Validation Response)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "hcpId": "0012t000001a2cZAAQ",
  "hcpName": "Dr. Sarah Chen",
  "visitState": "GA",
  "validations": [
    {
      "checkName": "License Active",
      "passed": true,
      "state": "GA",
      "licenseNumber": "MD-12345678",
      "licenseType": "MD",
      "expirationDate": "2027-12-31",
      "action": "ALLOW"
    },
    {
      "checkName": "DEA Registration",
      "passed": true,
      "deaNumber": "BC12345678",
      "deaExpiration": "2026-12-31",
      "action": "ALLOW"
    },
    {
      "checkName": "Sample Limit (Monthly)",
      "passed": false,
      "policyDescription": "Max 30 units per month per practitioner",
      "timePeriod": "Month (April 2026)",
      "limit": 30,
      "currentDistribution": 25,
      "proposedDistribution": 8,
      "totalWouldBe": 33,
      "exceededBy": 3,
      "action": "REQUIRE_APPROVAL"
    }
  ],
  "overallResult": "REQUIRE_APPROVAL",
  "recommendedAction": "Contact Compliance Manager for sample limit override approval"
}
```

---

## Acceptance Criteria

### Scenario 1: Valid License in State (Happy Path)

**Given** a rep attempts to distribute samples to Dr. Chen in GA,  
**When** the signature capture screen appears,  
**Then** the system:
- Queries HealthcarePractitionerLicense__c for Dr. Chen with State = "GA"
- Finds active license "MD-12345678" (expires 2027-12-31)
- Logs to ComplianceAuditLog__c: "License Active" = "Pass"
- Allows signature to proceed without warning

---

### Scenario 2: License Expired — Block Signature

**Given** a rep attempts to distribute to an HCP whose GA license expired on 2024-12-31,  
**When** the signature capture screen appears,  
**Then** the system:
- Queries HealthcarePractitionerLicense__c and finds license but ExpirationDate < TODAY()
- Returns validation fail: "License expired on 2024-12-31. Cannot distribute samples."
- **Action:** Red error banner; signature pad disabled; "Contact Compliance" link

---

### Scenario 3: Sample Limit Warning (Warn & Allow)

**Given** an HCP already received 25 units of Product A in April 2026 (limit: 30/month),  
**When** rep attempts to distribute 8 more units,  
**Then** the system:
- Queries SampleDistribution__c for this HCP in April
- Calculates: 25 existing + 8 proposed = 33 (exceeds 30-unit limit by 3)
- Logs to ComplianceAuditLog__c: "Sample Limit" = "Warning"
- **Action:** Yellow warning banner: "This distribution exceeds the monthly sample limit. Proceed?" with "Continue" and "Cancel" buttons

**And when** rep clicks "Continue",  
**Then** signature is allowed, and the override is logged in ComplianceAuditLog__c.

---

### Scenario 4: Sample Limit Block (Require Approval)

**Given** a stricter policy has BypassRequiresApproval__c = true,  
**When** rep tries to exceed the limit,  
**Then** the system:
- Displays error: "Sample limit exceeded. Compliance Manager approval required."
- Prevents signature capture
- Prompts rep to "Request Compliance Override"

**And when** rep clicks the link, a Chatter message or email is sent to Compliance Manager requesting approval.

---

### Scenario 5: Audit Trail Completeness

**Given** a visit is submitted after distribution and signature,  
**When** a Compliance Officer reviews the audit trail for this visit,  
**Then** they see ComplianceAuditLog__c records:
- License Active: Pass (timestamp: 2026-04-15T10:30:00Z)
- DEA Registration: Pass
- Sample Limit: Warning (exceeded by 3 units, override by Rep1)
- All validations timestamped and linked to visit

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **License Data Source** Should licenses be manually entered, synced from state regulatory boards, or both? | Data governance; accuracy; sync frequency | Compliance Officer |
| 2 | **Sample Limit Flexibility** Should Compliance Managers be able to dynamically adjust limits per HCP or state? | Policy management; admin overhead | Compliance Officer |
| 3 | **DEA Verification** Should the system check DEA status against federal database, or rely on internal records? | Real-time compliance; external API calls; cost | Compliance Officer |
| 4 | **Frequency of Validation** Should licenses be validated in real-time (during signature) or pre-visit (at schedule time)? | Performance; freshness of data | Technical Lead |
| 5 | **Regional Variations** Are there state-specific regulations that should be hardcoded or configurable? | Policy management; flexibility | Compliance Officer |
| 6 | **Audit Log Retention** How long should ComplianceAuditLog__c records be retained (1 year, 3 years, 7 years)? | Data retention; regulatory requirement | Compliance Officer |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **HealthcarePractitionerLicense__c** | Custom Object | HIGH | Source of truth for practitioner licenses; accuracy critical |
| **PRM_LicenseValidator** | Integration Procedure | HIGH | Blocks non-compliant transactions; must be reliable |
| **PRM_SampleLimitChecker** | Integration Procedure | HIGH | Regulatory compliance; must handle edge cases |
| **ComplianceAuditLog__c** | Custom Object | HIGH | Audit trail; required for regulatory compliance |
| **Pre-Signature Validation** | Apex Flow | HIGH | Prevents violations at point of transaction |

---

## Definition of Done Checklist

- [ ] HealthcarePractitionerLicense__c custom object created with all fields
- [ ] SampleLimitPolicy__c Custom Metadata Type or object created
- [ ] ComplianceAuditLog__c custom object created
- [ ] PRM_LicenseValidator Integration Procedure implemented
- [ ] PRM_SampleLimitChecker Integration Procedure implemented
- [ ] Pre-signature validation flow built (runs both validators before allowing signature)
- [ ] License validation: checks IsActive and ExpirationDate correctly
- [ ] DEA validation: checks DEA registration if applicable
- [ ] Sample limit calculation: aggregates past distributions accurately
- [ ] Signature blocked if critical validation fails (license expired, DEA missing)
- [ ] Signature allowed with warning if warning-level validation fails
- [ ] Signature requires Compliance approval if policy.BypassRequiresApproval = true
- [ ] ComplianceAuditLog__c populated with all validation results (pass/fail)
- [ ] Apex test coverage ≥ 90% for validator logic
- [ ] Integration test: Attempt distribution to HCP with expired license (blocked)
- [ ] Integration test: Exceed sample limit (warning then override)
- [ ] Compliance dashboard: "Validations by State", "Limit Overrides"
- [ ] QA sign-off: Validation runs in < 2 seconds; blocks/warns appropriately
- [ ] Documentation: Compliance officer guide on license management and limit policies
- [ ] Training: Rep onboarding on validation rules and override process

---

## USER STORY 2.4: Capture Medical Inquiries and Launch In-App Surveys

**Persona:** Field Sales Representative, Medical Affairs Manager, Developer  
**Priority:** P1  
**Related Objects:** Visit__c, MedicalInquiry__c, Survey__c, SurveyResponse__c, SurveyQuestion__c  
**Integration Procedures:** PRM_MedicalInquiryRouter, PRM_SurveySync  
**Relevant Requirements:** FHN-15, FHN-100 (Medical inquiries and surveys)

---

## Story

**As a** Field Sales Representative,  
**I want** to seamlessly capture medical inquiries and inquiries raised by HCPs during my visit without switching apps, and launch quick pulse surveys (1-3 questions) to gather feedback,  
**So that** Medical Affairs can route inquiries to experts for timely response, and we collect valuable market intelligence about HCP preferences and concerns.

**Why it matters:** Reps currently email inquiries or manually enter them into separate systems, causing delays and data loss. In-app capture ensures all inquiries are systematically tracked, routed to Medical Affairs for expert response, and linked to the original visit context for follow-up.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Medical Inquiry Capture | Visit Screen | During/after visit, rep submits inquiry | Text input, HCP context, product context | MedicalInquiry__c |
| Survey Launch | Visit Screen | Optional: launch pulse survey (1-3 questions) | Pre-defined Survey__c templates | SurveyResponse__c |
| Response Tracking | Post-Visit | Medical Affairs reviews and responds to inquiries | MedicalInquiry__c queue | MedicalInquiry__c |

---

## Current State (from Salesforce Object Model)

### MedicalInquiry__c (Custom Object)

- **Field:** `Visit__c` (Lookup to Visit__c)
- **Field:** `InquiryType__c` (Picklist) — "Safety Question", "Efficacy Question", "Dosing", "Drug Interaction", "Off-Label Use", "General Question"
- **Field:** `InquiryText__c` (Text Long) — The question/inquiry text
- **Field:** `Product__c` (Lookup to Product) — Which product is the inquiry about
- **Field:** `Priority__c` (Picklist) — "High", "Medium", "Low"
- **Field:** `SubmittedBy__c` (Lookup to User) — Rep who captured inquiry
- **Field:** `Status__c` (Picklist) — "New", "Assigned", "In Progress", "Responded", "Closed"
- **Field:** `AssignedToUser__c` (Lookup to User) — Medical Affairs expert
- **Field:** `ResponseText__c` (Text Long) — Expert response
- **Field:** `ResponseDate__c` (DateTime)

### Survey__c (Standard or Custom Object)

- **Field:** `SurveyName__c` (Text) — "HCP Satisfaction", "Product Interest", "Competitive Threat"
- **Field:** `IsActive__c` (Checkbox) — Can be deployed?
- **Field:** `SurveyType__c` (Picklist) — "Pulse (1-3 Q)", "Standard (5-10 Q)", "Comprehensive (20+ Q)"
- **Related List:** SurveyQuestion__c records

### SurveyQuestion__c (Custom Object)

- **Field:** `Survey__c` (Master-Detail)
- **Field:** `QuestionText__c` (Text)
- **Field:** `AnswerType__c` (Picklist) — "Yes/No", "5-Point Scale", "Text", "Multiple Choice"
- **Field:** `SequenceNumber__c` (Number)

### SurveyResponse__c (Custom Object)

- **Field:** `Survey__c` (Lookup)
- **Field:** `Visit__c` (Lookup)
- **Field:** `Respondent__c` (Lookup to Account / HCP) — Who responded
- **Field:** `ResponseDate__c` (DateTime) — When completed
- **Field:** `SurveyAnswers__c` (JSON) — Responses to each question

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Medical Inquiry Modal** | OmniScript / LWC | Form for rep to capture inquiry text, select type, product, priority | Text area, product lookup, priority picklist; auto-populate HCP and rep from visit context |
| **Survey Launcher** | OmniScript / LWC | Display available pulse surveys; allow rep to launch during or after visit | Show survey name, description, question count; "Launch Survey" button |
| **In-App Survey Form** | OmniScript / LWC | Render survey questions dynamically (Yes/No, 5-point scale, text, MC) | Mobile-optimized; progress bar; submit/skip options |
| **PRM_MedicalInquiryRouter** | Integration Procedure | Route new inquiries to appropriate Medical Affairs expert queue | Rules: by product, by inquiry type, by priority; create Task for assignment |
| **Inquiry Response Notification** | Apex Trigger / Flow | When Medical Affairs responds, notify rep via app/email | Include response text; allow rep to acknowledge |

### Medical Inquiry Capture Component (Pseudocode)

```javascript
class MedicalInquiryModal extends LightningElement {
  @api visitId;
  @api hcpId;
  @api hcpName;
  @api repId;

  inquiryType = '';
  inquiryText = '';
  product = '';
  priority = 'Medium';
  availableProducts = [];

  async connectedCallback() {
    // Fetch products available for this HCP's therapeutic area
    this.availableProducts = await fetchProducts();
  }

  async handleSubmitInquiry() {
    if (!this.inquiryText.trim()) {
      alert('Please enter an inquiry.');
      return;
    }

    // 1. Create MedicalInquiry__c
    const inquiry = await createMedicalInquiry({
      visitId: this.visitId,
      inquiryType: this.inquiryType,
      inquiryText: this.inquiryText,
      productId: this.product,
      priority: this.priority,
      submittedBy: this.repId
    });

    // 2. Route to Medical Affairs via PRM_MedicalInquiryRouter
    await routeInquiry(inquiry.id);

    // 3. Display confirmation
    this.dispatchEvent(new CustomEvent('inquirysubmitted', { 
      detail: { inquiryId: inquiry.id, message: 'Inquiry submitted to Medical Affairs.' } 
    }));

    // 4. Close modal
    this.handleCloseModal();
  }

  handleCloseModal() {
    this.dispatchEvent(new CustomEvent('close'));
  }
}

class SurveyLauncher extends LightningElement {
  @api visitId;
  @api hcpId;

  availableSurveys = [];
  selectedSurvey = null;

  async connectedCallback() {
    // Fetch available surveys (filtered by type and HCP specialty)
    this.availableSurveys = await querySurveys({
      isActive: true,
      surveyType: 'Pulse'
    });
  }

  handleSelectSurvey(event) {
    const surveyId = event.target.dataset.surveyId;
    this.selectedSurvey = this.availableSurveys.find(s => s.id === surveyId);
    this.launchSurvey();
  }

  async launchSurvey() {
    // 1. Fetch survey questions
    const questions = await querySurveyQuestions(this.selectedSurvey.id);

    // 2. Render survey form
    this.dispatchEvent(new CustomEvent('surveylaunched', { 
      detail: { survey: this.selectedSurvey, questions } 
    }));
  }
}

class SurveyForm extends LightningElement {
  @api survey;
  @api questions;
  @api visitId;
  @api hcpId;

  answers = {};
  currentQuestionIndex = 0;

  handleAnswerChange(event) {
    const questionId = event.target.dataset.questionId;
    const answer = event.target.value;
    this.answers[questionId] = answer;
  }

  handleNextQuestion() {
    if (this.currentQuestionIndex < this.questions.length - 1) {
      this.currentQuestionIndex++;
    }
  }

  handlePreviousQuestion() {
    if (this.currentQuestionIndex > 0) {
      this.currentQuestionIndex--;
    }
  }

  async handleSubmitSurvey() {
    // 1. Create SurveyResponse__c
    const response = await createSurveyResponse({
      surveyId: this.survey.id,
      visitId: this.visitId,
      respondentId: this.hcpId,
      answers: JSON.stringify(this.answers)
    });

    // 2. Display confirmation
    this.dispatchEvent(new CustomEvent('surveycompleted', { 
      detail: { responseId: response.id } 
    }));
  }

  handleSkipSurvey() {
    this.dispatchEvent(new CustomEvent('surveyskipped'));
  }
}
```

### Example (Medical Inquiry & Survey Response)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "inquiry": {
    "id": "a072t000001D1ZAAX",
    "inquiryType": "Safety Question",
    "inquiryText": "What is the risk profile for patients with renal impairment?",
    "product": "Product A",
    "priority": "High",
    "submittedBy": "Rep1",
    "submittedDate": "2026-04-15T10:45:00Z",
    "status": "New",
    "assignedTo": null
  },
  "survey": {
    "id": "a062t000001E1ZAAX",
    "surveyName": "HCP Product Interest",
    "surveyType": "Pulse",
    "totalQuestions": 3,
    "questions": [
      {
        "id": "a082t000001F1ZAAX",
        "text": "How familiar are you with Product A?",
        "answerType": "5-Point Scale",
        "sequence": 1
      },
      {
        "id": "a082t000001F2ZAAX",
        "text": "Would you consider prescribing Product A?",
        "answerType": "Yes/No",
        "sequence": 2
      },
      {
        "id": "a082t000001F3ZAAX",
        "text": "What barriers exist to adoption?",
        "answerType": "Text",
        "sequence": 3
      }
    ]
  },
  "surveyResponse": {
    "id": "a092t000001G1ZAAX",
    "surveyId": "a062t000001E1ZAAX",
    "visitId": "a012t000003A1ZAAX",
    "respondentId": "0012t000001a2cZAAQ",
    "responseDate": "2026-04-15T10:50:00Z",
    "answers": {
      "a082t000001F1ZAAX": "4",
      "a082t000001F2ZAAX": "Yes",
      "a082t000001F3ZAAX": "Pricing and insurance coverage"
    }
  }
}
```

---

## Acceptance Criteria

### Scenario 1: Capture Medical Inquiry (Happy Path)

**Given** a rep is in a visit to Dr. Chen,  
**When** the doctor asks: "What is the renal dosing for Product A?",  
**Then** the rep clicks "Capture Inquiry" button.  
**And a modal displays**:
- Inquiry Type (dropdown): "Safety Question", "Efficacy", "Dosing", etc.
- Inquiry Text (text area)
- Product (product lookup, pre-filtered)
- Priority (radio: High/Medium/Low)

**And when** rep enters the inquiry details and clicks "Submit",  
**Then** the system:
- Creates MedicalInquiry__c record
- Routes to Medical Affairs via PRM_MedicalInquiryRouter
- Displays: "Inquiry submitted to Medical Affairs. Expert response will be emailed to you."
- Closes modal

---

### Scenario 2: Launch Pulse Survey

**Given** the rep is wrapping up the visit,  
**When** they click "Offer Survey" button,  
**Then** a list of available pulse surveys displays:
- "HCP Product Interest" (3 questions)
- "Competitive Threat Assessment" (2 questions)

**And when** rep clicks "Launch Survey",  
**Then** a 3-question survey form loads:
- Q1: "How familiar are you with Product A?" (5-point scale)
- Q2: "Would you consider prescribing?" (Yes/No)
- Q3: "What barriers to adoption?" (Text area)

---

### Scenario 3: Complete Survey

**Given** the survey form is displayed,  
**When** the HCP answers all 3 questions,  
**Then** a progress bar shows "3/3 complete".  
**And when** they click "Submit Survey",  
**Then** the system:
- Creates SurveyResponse__c with all answers
- Displays: "Thank you! Your feedback helps us improve."
- Syncs survey data to analytics platform (overnight batch)

---

### Scenario 4: Medical Affairs Responds to Inquiry

**Given** a rep submitted an inquiry 24 hours ago,  
**When** a Medical Affairs expert responds to the inquiry,  
**Then** the system:
- Creates a follow-up record in MedicalInquiry__c.ResponseText__c
- Sends notification to rep via app: "New response to your inquiry: '[excerpt of response]'"
- Rep can click to view full response in MedicalInquiry__c record

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Survey Templates** Should surveys be pre-defined by Marketing, or should reps customize surveys per visit? | Survey design; data quality; admin overhead | Product Manager |
| 2 | **Inquiry Assignment** Should inquiries auto-route to Medical Affairs experts, or should reps manually assign to a specific expert? | Workflow automation; response time | Medical Affairs |
| 3 | **Survey Response Frequency** Should reps launch surveys on every visit, or only on strategic accounts? | Data collection strategy; user burden | Product Manager |
| 4 | **Inquiry SLA** What is the expected SLA for Medical Affairs to respond to inquiries (e.g., 24 hours)? | Workflow design; escalation rules | Medical Affairs |
| 5 | **Survey Results Rollup** Should survey responses roll up to Account or Rep dashboards for visibility? | Analytics; rep accountability | Product Manager |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **MedicalInquiry__c Object** | Custom Object | HIGH | Core intake mechanism for medical inquiries; enables audit trail |
| **Medical Inquiry Modal** | OmniScript / LWC | MEDIUM | Adds workflow step; minimal friction required |
| **Survey Launcher & Form** | OmniScript / LWC | MEDIUM | Optional feature; UX must be simple |
| **PRM_MedicalInquiryRouter** | Integration Procedure | HIGH | Routes inquiries to right expert; affects response time |
| **SurveyResponse Tracking** | Salesforce Data | MEDIUM | Analytics and BI implications |

---

## Definition of Done Checklist

- [ ] MedicalInquiry__c custom object created with all fields
- [ ] SurveyQuestion__c and SurveyResponse__c objects created
- [ ] Medical Inquiry modal built (type, text, product, priority)
- [ ] Survey Launcher component built (list available surveys)
- [ ] Survey Form component built (render questions dynamically)
- [ ] PRM_MedicalInquiryRouter Integration Procedure implemented
- [ ] Inquiry auto-routes to Medical Affairs queue (Task created)
- [ ] Survey responses stored in SurveyResponse__c with answers JSON
- [ ] Notification sent to rep when Medical Affairs responds
- [ ] Rep can view inquiry status and response in visit record
- [ ] Apex test coverage ≥ 85% for inquiry routing and survey tracking
- [ ] Integration test: Submit inquiry, verify routes to Medical Affairs, verify response triggers notification
- [ ] Integration test: Launch survey, complete 3 questions, verify stored correctly
- [ ] QA sign-off: Inquiry and survey UX are smooth and non-intrusive
- [ ] Medical Affairs dashboard: "Inquiries by Type", "Response Time", "Open Inquiries"
- [ ] Analytics dashboard: "Survey Response Rates", "Top Barriers to Adoption"
- [ ] Documentation: Rep user guide on capturing inquiries and completing surveys
- [ ] Training: Field team and Medical Affairs team onboarding

---

---

# Epic 3: Visit Closure & Auditing

## USER STORY 3.1: Log Product Discussions and HCP Reactions

**Persona:** Field Sales Representative, Sales Manager, Compliance Officer, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, ProductDiscussion__c, HCPReaction__c, VisitProductMatrix__c  
**Integration Procedures:** N/A (OmniScript-based)  
**Relevant Requirements:** FHN-15, FHN-105 (Product discussion logging)

---

## Story

**As a** Field Sales Representative,  
**I want** to systematically document which products were discussed during my visit, capture detailed information about the HCP's reaction and interest level, and log specific messages or selling points that resonated,  
**So that** we maintain accurate historical records for future interactions, sales managers can track engagement trends, and we optimize future visits based on what messaging works best for each HCP.

**Why it matters:** Without structured product discussion logs, reps rely on memory or generic visit summaries, leading to lost context for follow-ups. HCP reaction tracking provides valuable signals for sales pipeline management and personalization.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Post-Visit Documentation | Visit Detail Screen | After visit, rep logs products discussed | Product list, HCP reactions, rep notes | ProductDiscussion__c, HCPReaction__c |
| Historical Analysis | Sales Dashboard | Sales managers analyze discussion history by HCP | Past ProductDiscussion__c records | VisitProductMatrix__c (rollup) |

---

## Current State (from Salesforce Object Model)

### ProductDiscussion__c (Custom Object)

- **Field:** `Visit__c` (Master-Detail to Visit__c)
- **Field:** `Product__c` (Lookup to Product)
- **Field:** `DiscussionSequence__c` (Number) — Order in which product was discussed (1st, 2nd, 3rd)
- **Field:** `TimeSpentMinutes__c` (Number) — How long was product discussed
- **Field:** `MessagesFocused__c` (Multi-select Picklist) — "Efficacy", "Safety", "Cost", "Ease of Use", "Patient Outcomes"
- **Field:** `CompetitiveContext__c` (Text) — What competitor products were mentioned?
- **Field:** `HCPReaction__c` (Picklist) — "Very Interested", "Interested", "Neutral", "Skeptical", "Not Interested"
- **Field:** `ReactionNotes__c` (Text Long) — Rep's detailed observation of reaction
- **Field:** `NextSteps__c` (Picklist) — "Follow-up Call", "Sample Request", "Prescription", "No Action", "Return Visit"

### VisitProductMatrix__c (Rollup or Custom Report Object)

- Aggregates ProductDiscussion__c data for dashboard/reporting
- Enables queries like: "Products discussed most frequently", "HCP reactions by product", "Conversion from discussion to prescription"

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Product Discussion Form** | OmniScript / LWC | Repeating section: select product, capture reaction, notes | Repeating block with product lookup, reaction picklist, time spent, messages focused, next steps |
| **Reaction Feedback Component** | OmniScript / LWC | Visual reaction selector (emoticons or 5-point scale) | Emoji scale or text options; auto-populate ReactionNotes helper text |
| **Time Spent Tracker** | OmniScript Field | Number input for minutes spent discussing each product | Validation: 0-120 minutes reasonable range |
| **Competitive Context Tracking** | OmniScript Field | Free-text field for rep to note competitive products mentioned | Auto-suggest competitor product list |
| **ProductDiscussion Rollup** | Scheduled Apex Batch | Nightly rollup to VisitProductMatrix__c for reporting | Aggregate by product, by HCP, by rep; calculate metrics |

### Product Discussion Logging Logic (Pseudocode)

```javascript
class ProductDiscussionForm extends LightningElement {
  @api visitId;
  @api hcpId;

  productDiscussions = [];
  availableProducts = [];

  async connectedCallback() {
    // Fetch products available for discussion
    this.availableProducts = await fetchProducts();
  }

  handleAddProductDiscussion() {
    // Initialize new row
    const newDiscussion = {
      product: null,
      timeSpent: 0,
      reaction: '',
      messages: [],
      competitiveContext: '',
      nextSteps: ''
    };
    this.productDiscussions.push(newDiscussion);
  }

  handleRemoveProductDiscussion(event) {
    const index = event.currentTarget.dataset.index;
    this.productDiscussions.splice(index, 1);
  }

  async handleSaveProductDiscussions() {
    if (this.productDiscussions.length === 0) {
      alert('Please log at least one product discussion.');
      return;
    }

    // 1. For each product discussion, create ProductDiscussion__c record
    for (let i = 0; i < this.productDiscussions.length; i++) {
      const disc = this.productDiscussions[i];
      const productDiscussionRecord = await createProductDiscussion({
        visitId: this.visitId,
        productId: disc.product.id,
        discussionSequence: i + 1,
        timeSpentMinutes: disc.timeSpent,
        messagesFocused: disc.messages.join(';'),
        competitiveContext: disc.competitiveContext,
        hcpReaction: disc.reaction,
        reactionNotes: disc.reactionNotes,
        nextSteps: disc.nextSteps
      });
    }

    // 2. Display confirmation
    this.dispatchEvent(new CustomEvent('discussionssaved', { 
      detail: { count: this.productDiscussions.length } 
    }));
  }
}
```

### Example (Product Discussion Data)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "hcpId": "0012t000001a2cZAAQ",
  "productDiscussions": [
    {
      "id": "a032t000001B1ZAAX",
      "product": "Product A",
      "discussionSequence": 1,
      "timeSpentMinutes": 15,
      "messagesFocused": ["Efficacy", "Patient Outcomes"],
      "competitiveContext": "Competitor B's product mentioned by HCP",
      "hcpReaction": "Very Interested",
      "reactionNotes": "Dr. Chen asked about head-to-head trial data. Expressed interest in sample.",
      "nextSteps": "Sample Request"
    },
    {
      "id": "a032t000001B2ZAAX",
      "product": "Product B",
      "discussionSequence": 2,
      "timeSpentMinutes": 8,
      "messagesFocused": ["Cost", "Ease of Use"],
      "competitiveContext": null,
      "hcpReaction": "Interested",
      "reactionNotes": "Concern about pricing. Asked about insurance coverage.",
      "nextSteps": "Follow-up Call"
    }
  ]
}
```

---

## Acceptance Criteria

### Scenario 1: Log Multiple Products (Happy Path)

**Given** a rep completes a visit where they discussed Product A and Product B,  
**When** they open the Post-Visit Documentation screen,  
**Then** they see a repeating form:
- Row 1: Product (dropdown) | Time Spent (number) | Reaction (dropdown) | Messages Focused (checkbox)
- Row 2: [empty, ready to add]

**And when** they select Product A, enter 15 minutes, select "Very Interested", and check "Efficacy",  
**Then** the row populates with that data.

**And when** they click "Add Another Product" and repeat for Product B,  
**Then** two product discussions are captured.

**And when** they click "Save",  
**Then** two ProductDiscussion__c records are created linked to the visit.

---

### Scenario 2: Capture HCP Reaction Detail

**Given** a product discussion row displays the Reaction dropdown,  
**When** the rep selects "Skeptical",  
**Then** an optional text field appears:
- Label: "What was the concern?"
- Placeholder: "e.g., Safety concerns, pricing, efficacy questions"

**And when** the rep types: "Concerned about liver enzyme elevation based on Competitor B trial",  
**Then** this is saved to ReactionNotes__c for follow-up context.

---

### Scenario 3: Track Competitive Context

**Given** during the visit, the HCP mentions Competitor B's product,  
**When** the rep is logging Product A discussion,  
**Then** they can enter: "Competitor mentioned: Competitor B's Product X (claims faster onset)"

**And when** saved, this is captured in CompetitiveContext__c for competitive intelligence tracking.

---

### Scenario 4: Set Next Steps Based on Reaction

**Given** the rep logs Product A with "Very Interested" reaction,  
**When** they select Next Steps,  
**Then** the dropdown suggests:
- "Sample Request" (default for "Very Interested")
- "Follow-up Call"
- "Prescription Expected"
- "No Action"

**And when** rep selects "Sample Request", this is logged for sales team action.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Reaction Granularity** Should reaction be at product level (as designed) or visit level (overall impression)? | Data granularity; analysis depth | Product Manager |
| 2 | **Time Spent Tracking** Is time spent per product critical, or is it optional metadata? | UX complexity; data quality | Product Manager |
| 3 | **Competitive Intelligence** Should competitive context be captured for every product, or only when competitor mentioned? | Data quality; rep burden | Product Manager |
| 4 | **Historical Analysis** Which metrics are most important for sales dashboards (reaction trends, time spent per product, competitive mentions)? | Reporting requirements | Analytics Lead |
| 5 | **Follow-up Automation** Should "Sample Request" automatically trigger a task for the sample team, or require manual action? | Workflow automation; integration | Operations |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **ProductDiscussion__c Object** | Custom Object | HIGH | Historical record of all product discussions; enables analysis |
| **Product Discussion Form** | OmniScript / LWC | MEDIUM | User-facing; requires clear design for data quality |
| **Reaction Tracking** | Custom Field | HIGH | Key metric for engagement analysis and follow-up strategy |
| **Competitive Context** | Custom Field | MEDIUM | Competitive intelligence; moderate importance |
| **Reporting & Analytics** | Dashboards | MEDIUM | Sales manager visibility; enables optimization |

---

## Definition of Done Checklist

- [ ] ProductDiscussion__c custom object created with all fields
- [ ] Product discussion form built with repeating rows
- [ ] Reaction dropdown with helpful options (Very Interested, Interested, Neutral, Skeptical, Not Interested)
- [ ] Conditional text area for detailed reaction notes (appears for Skeptical/Not Interested)
- [ ] Time spent input with validation (0-120 minutes)
- [ ] Messages Focused multi-select picklist
- [ ] Competitive context free-text field with auto-suggest
- [ ] Next Steps picklist with intelligent defaults based on reaction
- [ ] Form validation: minimum one product discussion required before saving
- [ ] Apex test coverage ≥ 85% for product discussion creation
- [ ] Integration test: Log 3 products, verify all records created with correct sequence
- [ ] Dashboard: "Products Discussed by HCP", "Reaction Trends", "Competitive Mentions"
- [ ] QA sign-off: Form is intuitive; no required fields feel burdensome
- [ ] Documentation: Rep user guide on logging product discussions
- [ ] Training: Field team onboarding on discussion documentation

---

## USER STORY 3.2: Record Visit Expenses and Marketing Items Provided

**Persona:** Field Sales Representative, Sales Manager, Compliance Officer, Financial Analyst, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, VisitExpense__c, VisitMarketingItem__c, ExpenseCategory__c, MarketingItemType__c  
**Integration Procedures:** PRM_ExpenseSync, PRM_TransferOfValueTracking  
**Relevant Requirements:** FHN-15, FHN-16 (Expenses and marketing items)

---

## Story

**As a** Field Sales Representative,  
**I want** to document all visit-related expenses (meals, travel, entertainment) and marketing items provided (gifts, promotional merchandise, meals provided by rep) so that,  
**When combined with sample data**, we maintain transparent, auditable records of all transfer of value to HCPs and comply with regulations like Physician Payments Sunshine Law.

**Why it matters:** Transfer of Value (ToV) reporting is mandatory for regulatory compliance. Manual tracking leads to missing or inaccurate data. Automated in-app capture of expenses and marketing items ensures comprehensive records linked to each visit, enabling accurate ToV reporting and audit compliance.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Post-Visit Documentation | Visit Detail Screen | Rep logs expenses and marketing items provided | Receipt, item list, manual entry | VisitExpense__c, VisitMarketingItem__c |
| Transfer of Value Reporting | Compliance Batch Job | Monthly/quarterly aggregation for ToV reporting | VisitExpense__c + VisitMarketingItem__c + SampleDistribution__c | ToVReport__c (rollup) |

---

## Current State (from Salesforce Object Model)

### VisitExpense__c (Custom Object)

- **Field:** `Visit__c` (Master-Detail)
- **Field:** `ExpenseCategory__c` (Lookup or Picklist) — "Meal", "Travel", "Entertainment", "Other"
- **Field:** `Description__c` (Text) — What was the expense for?
- **Field:** `Amount__c` (Currency) — Expense amount
- **Field:** `ReceiptDate__c` (Date)
- **Field:** `ReceiptImage__c` (ContentVersion reference) — Photo of receipt
- **Field:** `IsPersonal__c` (Checkbox) — Was this personal expense (for reimbursement) or company-paid?
- **Field:** `ApprovedByManager__c` (Lookup to User) — Manager who approved expense

### VisitMarketingItem__c (Custom Object)

- **Field:** `Visit__c` (Master-Detail)
- **Field:** `ItemType__c` (Picklist) — "Promotional Merchandise", "Meal Provided", "Educational Materials", "Branded Items"
- **Field:** `Description__c` (Text) — Description of item (e.g., "Logo T-shirts (5 units)", "Lunch for 4 people")
- **Field:** `ApproximateValue__c` (Currency) — Estimated value of item provided
- **Field:** `Quantity__c` (Number) — How many of this item (if applicable)
- **Field:** `DistributedToCount__c` (Number) — How many HCPs received this item

### MarketingItemType__c (Custom Metadata Type)

- **Field:** `ItemTypeName__c` — "Promotional Merchandise", etc.
- **Field:** `AverageValue__c` (Currency) — Standard value for this item type
- **Field:** `IsApproved__c` (Checkbox) — Is this item type approved for distribution?
- **Field:** `ComplianceNotes__c` (Text) — Any regulatory notes

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Expense Logging Form** | OmniScript / LWC | Repeating section for expense entry | Category, description, amount, receipt image upload, personal/company flag |
| **Marketing Item Form** | OmniScript / LWC | Repeating section for marketing items | Item type, description, quantity, approximate value, distribution count |
| **Receipt Image Capture** | LWC + Mobile Camera | Allow rep to photo receipt on mobile device | Upload as ContentVersion; link to VisitExpense__c |
| **Amount Validation** | Apex / Flow | Enforce reasonable expense limits (e.g., meal < $100, total visit expenses < $500) | Validation rules; optional manager approval for exceeding threshold |
| **PRM_ExpenseSync** | Integration Procedure | Sync expenses to back-office financial system for reimbursement processing | Daily or weekly batch; validate amounts and categories |
| **Transfer of Value Aggregation** | Apex Batch Job | Monthly: aggregate all expenses, marketing items, and samples for ToV reporting | Join VisitExpense__c, VisitMarketingItem__c, SampleDistribution__c; calculate total ToV per HCP |

### Expense & Marketing Item Logging Logic (Pseudocode)

```javascript
class ExpenseAndMarketingForm extends LightningElement {
  @api visitId;
  @api hcpId;

  expenses = [];
  marketingItems = [];
  expenseCategories = [];
  itemTypes = [];
  totalExpenseAmount = 0;
  totalMarketingValue = 0;

  async connectedCallback() {
    this.expenseCategories = await fetchExpenseCategories();
    this.itemTypes = await fetchMarketingItemTypes();
  }

  handleAddExpense() {
    const newExpense = {
      category: '',
      description: '',
      amount: 0,
      receiptDate: new Date().toISOString().split('T')[0],
      receiptImage: null,
      isPersonal: false
    };
    this.expenses.push(newExpense);
  }

  handleAddMarketingItem() {
    const newItem = {
      type: '',
      description: '',
      quantity: 1,
      approximateValue: 0,
      distributedToCount: 1
    };
    this.marketingItems.push(newItem);
  }

  handleAmountChange(event) {
    const index = event.currentTarget.dataset.index;
    const amount = parseFloat(event.currentTarget.value);
    
    this.expenses[index].amount = amount;
    this.totalExpenseAmount = this.expenses.reduce((sum, exp) => sum + exp.amount, 0);
    
    // Validation: warn if exceeding limit
    if (this.totalExpenseAmount > 500) {
      console.warn('Total expenses exceed recommended limit of $500.');
    }
  }

  async handleReceiptUpload(event) {
    const index = event.currentTarget.dataset.index;
    const file = event.target.files[0];
    
    // Upload receipt image
    const contentVersionId = await uploadReceiptImage(file);
    this.expenses[index].receiptImage = contentVersionId;
  }

  async handleSaveExpensesAndItems() {
    if (this.expenses.length === 0 && this.marketingItems.length === 0) {
      alert('Please log at least one expense or marketing item.');
      return;
    }

    // 1. Create VisitExpense__c records
    for (const exp of this.expenses) {
      await createVisitExpense({
        visitId: this.visitId,
        category: exp.category,
        description: exp.description,
        amount: exp.amount,
        receiptDate: exp.receiptDate,
        receiptImageId: exp.receiptImage,
        isPersonal: exp.isPersonal
      });
    }

    // 2. Create VisitMarketingItem__c records
    for (const item of this.marketingItems) {
      await createVisitMarketingItem({
        visitId: this.visitId,
        itemType: item.type,
        description: item.description,
        quantity: item.quantity,
        approximateValue: item.approximateValue,
        distributedToCount: item.distributedToCount
      });
    }

    // 3. Calculate and display ToV summary
    const tovSummary = {
      totalExpenses: this.totalExpenseAmount,
      totalMarketingValue: this.marketingItems.reduce((sum, item) => sum + item.approximateValue, 0),
      totalToV: this.totalExpenseAmount + this.marketingItems.reduce((sum, item) => sum + item.approximateValue, 0)
    };

    this.dispatchEvent(new CustomEvent('expensessaved', { detail: tovSummary }));
  }
}
```

### Example (Expense & Marketing Item Data)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "hcpId": "0012t000001a2cZAAQ",
  "expenses": [
    {
      "id": "a042t000001C1ZAAX",
      "category": "Meal",
      "description": "Lunch at Memorial Hospital Cafeteria (for 2: rep + Dr. Chen)",
      "amount": 48.50,
      "receiptDate": "2026-04-15",
      "receiptImage": "069...",
      "isPersonal": false
    },
    {
      "id": "a042t000001C2ZAAX",
      "category": "Travel",
      "description": "Parking at hospital",
      "amount": 10.00,
      "receiptDate": "2026-04-15",
      "receiptImage": null,
      "isPersonal": true
    }
  ],
  "marketingItems": [
    {
      "id": "a052t000001D1ZAAX",
      "itemType": "Promotional Merchandise",
      "description": "Company-branded pens (pack of 10)",
      "quantity": 1,
      "approximateValue": 15.00,
      "distributedToCount": 2
    },
    {
      "id": "a052t000001D2ZAAX",
      "itemType": "Educational Materials",
      "description": "Printed clinical update brochure",
      "quantity": 3,
      "approximateValue": 9.00,
      "distributedToCount": 3
    }
  ],
  "transferOfValueSummary": {
    "totalExpenses": 58.50,
    "totalMarketingValue": 24.00,
    "totalTransferOfValue": 82.50,
    "associatedSamples": 3,
    "sampleValue": 120.00,
    "totalIncludingFood": 82.50  // Food is separate category in reporting
  }
}
```

---

## Acceptance Criteria

### Scenario 1: Log Meal and Travel Expenses (Happy Path)

**Given** a rep finishes a visit and opens the Expenses section,  
**When** they click "Add Expense",  
**Then** a new row appears with fields:
- Expense Category (dropdown: Meal, Travel, Entertainment, Other)
- Description (text)
- Amount (currency)
- Receipt Date (date picker)
- Receipt Image (camera/upload button)
- Personal/Company (radio)

**And when** rep enters: Category="Meal", Description="Lunch at hospital cafeteria", Amount="48.50", Personal="No",  
**Then** the expense is added to the list.

**And when** they click "Capture Receipt", the mobile camera opens, and they snap a photo of the receipt,  
**Then** the image is uploaded and linked to the expense.

---

### Scenario 2: Add Marketing Items

**Given** the rep provided branded pens and educational materials during the visit,  
**When** they click "Add Marketing Item" in the Marketing Items section,  
**Then** a new row appears with:
- Item Type (dropdown: Promotional Merchandise, Meal Provided, Educational Materials, Branded Items)
- Description (text)
- Quantity (number)
- Approximate Value (currency)
- Distributed to Count (number of HCPs)

**And when** rep enters: Type="Promotional Merchandise", Description="Company pens (pack of 10)", Quantity="1", Value="$15", Distributed="2",  
**Then** the item is added.

---

### Scenario 3: Transfer of Value Summary

**Given** the rep has logged 2 expenses ($48.50 meal + $10 parking) and 2 marketing items ($15 pens + $9 brochures),  
**When** they click "Save" or view the visit summary,  
**Then** the system calculates and displays:
- **Total Expenses:** $58.50
- **Total Marketing Value:** $24.00
- **Total Transfer of Value (Food excluded):** $82.50
- **Associated Samples:** 3 units (from earlier sample distribution)
- **Total ToV including Samples:** $202.50

---

### Scenario 4: Expense Limit Validation

**Given** a rep attempts to log a meal for $250 (exceeds typical limit),  
**When** they enter the amount,  
**Then** the system displays a warning:
- **Yellow Warning:** "This meal expense is unusually high for a single visit. Manager approval may be required."
- **Action:** Allow save but flag for manager review

---

### Scenario 5: Transfer of Value Monthly Report

**Given** a rep completes 20 visits in April with various expenses and samples,  
**When** a compliance manager runs the monthly ToV report,  
**Then** the system aggregates:
- Total ToV by HCP (e.g., Dr. Chen received $500 in ToV across 3 visits)
- Total ToV by rep
- Transfer of Value trends by category (meals, samples, merchandise)
- Flagged items (unusually high expenses)

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Expense Limits** What are the reasonable limits for meals, travel, entertainment per visit? | Validation rules; compliance standards | Finance + Compliance |
| 2 | **Meal Splitting** Should the system handle "meal for N people" as a single expense or split by attendee? | Data granularity; Finance implications | Finance |
| 3 | **Receipt Requirements** Are receipts always required, or optional for amounts < $25? | Data quality; approval workflows | Finance + Compliance |
| 4 | **Personal Expenses** Should personal expenses (parking, tolls) be tracked separately for reimbursement? | Expense reimbursement process | Finance |
| 5 | **ToV Reporting Scope** Should ToV include only direct ToV (meals, samples, items) or also indirect (travel, time)? | Regulatory compliance; reporting definition | Compliance Officer |
| 6 | **Sunshine Law Mapping** Should the system map ToV categories to Sunshine Law fields (e.g., "Meals & Entertainment", "Transfers of Value")? | Regulatory reporting compliance | Compliance Officer |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **VisitExpense__c & VisitMarketingItem__c** | Custom Objects | HIGH | Core ToV tracking; regulatory compliance requirement |
| **Receipt Image Upload** | Mobile Feature | MEDIUM | Audit trail; financial control |
| **Expense Validation** | Apex / Flow | MEDIUM | Prevents outlier expenses; flags for approval |
| **Transfer of Value Reporting** | Compliance Batch Job | HIGH | Mandatory reporting; must be accurate |
| **Financial System Integration** | Integration Procedure | MEDIUM | Sync to back-office for reimbursement |

---

## Definition of Done Checklist

- [ ] VisitExpense__c custom object created with all fields
- [ ] VisitMarketingItem__c custom object created with all fields
- [ ] Expense logging form built (repeating rows, category dropdown, amount input, receipt upload)
- [ ] Marketing item form built (repeating rows, item type, quantity, approximate value)
- [ ] Receipt image upload via mobile camera implemented
- [ ] Expense amount validation (warning if > threshold)
- [ ] Personal/Company expense flag working correctly
- [ ] Automatic ToV summary calculation (expenses + marketing items)
- [ ] Apex test coverage ≥ 90% for expense and item creation
- [ ] Integration test: Log 3 expenses and 2 marketing items, verify all records created and ToV calculated
- [ ] Monthly ToV batch job implemented and tested
- [ ] Sunshine Law mapping fields added (if required by compliance)
- [ ] Compliance dashboard: "ToV by HCP", "ToV by Rep", "Flagged Expenses"
- [ ] Financial system integration tested (mock)
- [ ] QA sign-off: Receipt upload is smooth; form UX is intuitive
- [ ] Documentation: Rep user guide on logging expenses and marketing items; Finance guide on ToV reporting
- [ ] Training: Field team and Finance team onboarding

---

---

## USER STORY 3.3: Set Next Visit Objectives and Auto-Populate Goals

**Persona:** Field Sales Representative, Sales Manager, Developer  
**Priority:** P1  
**Related Objects:** Visit__c, NextVisitObjective__c, Account  
**Integration Procedures:** N/A (OmniScript-based)  
**Relevant Requirements:** FHN-15, FHN-106 (Next visit objectives)

---

## Story

**As a** Field Sales Representative,  
**I want** to document my goals and objectives for the next interaction with an HCP (e.g., "Sample request follow-up", "Present new indication data", "Discuss patient case"),  
**So that** the system automatically surfaces these objectives when I schedule my next visit, helping me stay focused and ensuring continuity across visits.

**Why it matters:** Reps often forget context between visits, losing momentum on follow-ups. Auto-populated objectives create accountability, improve visit preparation, and ensure systematic progression of the sales cycle.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Current Visit Closure | Visit Detail Screen | Rep sets objectives for next visit | Rep input, visit context | NextVisitObjective__c |
| Next Visit Preparation | Visit Scheduler | When scheduling next visit to same HCP, display prior objectives | NextVisitObjective__c from prior visit | Visit__c |

---

## Current State (from Salesforce Object Model)

### NextVisitObjective__c (Custom Object)

- **Field:** `Visit__c` (Master-Detail to current Visit__c)
- **Field:** `ObjectiveType__c` (Picklist) — "Follow-up on Samples", "Present New Data", "Address Objections", "Expand Product Engagement", "Patient Case Discussion", "Deepen Relationship", "Close Business"
- **Field:** `ObjectiveDescription__c` (Text Long) — Specific description
- **Field:** `DesiredOutcome__c` (Picklist) — "Sample Request Approval", "Prescription", "Meeting with Team", "Trial Initiation", "Information Request"
- **Field:** `TargetDate__c` (Date) — Desired date for next visit
- **Field:** `IsCompleted__c` (Checkbox, calculated) — Was objective achieved in next visit?

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Next Visit Objectives Form** | OmniScript / LWC | Repeating section for setting 2-3 objectives | Objective type (picklist), description (text), desired outcome, target date |
| **Objective Auto-Population** | Apex Flow | When rep schedules next visit to HCP, query prior objectives and display in a "Reminders" section | Query NextVisitObjective__c for this HCP; filter by not-yet-completed objectives |
| **Objective Completion Tracking** | Apex Trigger | Compare objectives from prior visit to current visit; mark as completed if objective met | Join prior NextVisitObjective__c to current Visit__c by HCP; analyze current visit details |

### Next Visit Objectives Logic (Pseudocode)

```javascript
class NextVisitObjectivesForm extends LightningElement {
  @api visitId;
  @api hcpId;

  objectives = [];
  objectiveTypes = [];
  desiredOutcomes = [];

  async connectedCallback() {
    this.objectiveTypes = await fetchObjectiveTypes();
    this.desiredOutcomes = await fetchDesiredOutcomes();
  }

  handleAddObjective() {
    const newObjective = {
      type: '',
      description: '',
      desiredOutcome: '',
      targetDate: null
    };
    this.objectives.push(newObjective);
  }

  async handleSaveObjectives() {
    if (this.objectives.length === 0) {
      // Objectives are optional
      return;
    }

    for (const obj of this.objectives) {
      await createNextVisitObjective({
        visitId: this.visitId,
        objectiveType: obj.type,
        description: obj.description,
        desiredOutcome: obj.desiredOutcome,
        targetDate: obj.targetDate
      });
    }

    this.dispatchEvent(new CustomEvent('objectivessaved', { detail: { count: this.objectives.length } }));
  }
}

class VisitScheduler extends LightningElement {
  @api hcpId;

  priorObjectives = [];

  async handleHcpSelected() {
    // Fetch prior visit objectives for this HCP that haven't been completed
    this.priorObjectives = await queryPriorObjectives(this.hcpId);
    
    if (this.priorObjectives.length > 0) {
      // Display reminder banner
      this.showObjectiveReminder(this.priorObjectives);
    }
  }

  showObjectiveReminder(objectives) {
    // Display in banner: "Previous objectives from last visit:
    // 1. Follow up on sample request
    // 2. Present new trial data"
    // This helps rep stay focused on next visit's purpose
  }
}
```

### Example (Next Visit Objectives Data)

```json
{
  "visitId": "a012t000003A1ZAAX",
  "objectives": [
    {
      "id": "a082t000001E1ZAAX",
      "objectiveType": "Follow-up on Samples",
      "objectiveDescription": "Check if Dr. Chen has prescribed Product A to any patients since receiving samples",
      "desiredOutcome": "Prescription",
      "targetDate": "2026-05-15",
      "isCompleted": false
    },
    {
      "id": "a082t000001E2ZAAX",
      "objectiveType": "Present New Data",
      "objectiveDescription": "Share recent clinical trial data (April 2026 publication) on efficacy in HF patients",
      "desiredOutcome": "Trial Initiation",
      "targetDate": "2026-05-15",
      "isCompleted": false
    }
  ],
  "reminderForNextVisit": "When scheduling the next visit to Dr. Chen, the system will remind you: 'Follow up on samples' and 'Present new trial data'"
}
```

---

## Acceptance Criteria

### Scenario 1: Set Objectives After Visit (Happy Path)

**Given** a rep completes a visit and opens the "Next Visit Objectives" section,  
**When** they click "Add Objective",  
**Then** a new row displays with:
- Objective Type (dropdown: Follow-up, Present Data, Address Objections, Expand Engagement, Case Discussion, Deepen Relationship, Close Business)
- Objective Description (text area)
- Desired Outcome (dropdown: Prescription, Sample Request, Trial, Meeting, Info)
- Target Date (date picker)

**And when** rep enters: "Follow up on sample request", "Check if prescribed", desired outcome "Prescription", target date "2026-05-15",  
**Then** the objective is saved to NextVisitObjective__c.

---

### Scenario 2: Auto-Populate Objectives on Next Visit Scheduling

**Given** a rep is scheduling a visit to Dr. Chen (who had 2 prior objectives from last visit),  
**When** the Visit Scheduler loads,  
**Then** a reminder banner displays:
- "📋 Prior Visit Objectives:
  1. Follow up on sample request
  2. Present new trial data
  → Target Date: 2026-05-15"

**And when** the rep clicks the banner, they see full details and can reference them during visit prep.

---

### Scenario 3: Mark Objectives as Completed

**Given** during the current visit, the rep addresses the prior objectives (e.g., discusses samples, presents data),  
**When** they submit the current visit,  
**Then** a batch job queries prior NextVisitObjective__c records and analyzes the current visit:
- If current visit includes "ProductDiscussion__c for Product A", mark "Follow up on samples" objective as completed
- If current visit includes "Content presented: Clinical trial data", mark "Present new data" objective as completed

**And in the system**, IsCompleted__c = true for accomplished objectives.

---

## Definition of Done Checklist

- [ ] NextVisitObjective__c custom object created with all fields
- [ ] Next Visit Objectives form built (repeating rows, type, description, outcome, target date)
- [ ] Optional objectives (not required to save visit)
- [ ] Objective reminder banner displays when scheduling next visit to same HCP
- [ ] Prior objectives query filters by HCP and IsCompleted = false
- [ ] Batch job runs daily to assess objective completion
- [ ] Apex test coverage ≥ 85% for objective creation and tracking
- [ ] Integration test: Set 2 objectives, schedule next visit, verify reminder displays
- [ ] Dashboard: "Open Objectives by Rep", "Objective Completion Rate"
- [ ] QA sign-off: Reminder displays without delay
- [ ] Documentation: Rep user guide on setting and tracking objectives
- [ ] Training: Field team onboarding on objective-driven visit planning

---

---

## USER STORY 3.4: Lock Records and Generate Audit Snapshot on Visit Submission

**Persona:** Field Sales Representative, Compliance Manager, Audit Officer, Developer  
**Priority:** P0  
**Related Objects:** Visit__c, VisitAuditSnapshot__c, Visit-related objects (all child records)  
**Integration Procedures:** N/A (Apex Trigger-based)  
**Relevant Requirements:** FHN-16, FHN-107 (Visit submission, locking, audit trails)

---

## Story

**As a** Compliance Manager and Audit Officer,  
**I want** that when a rep submits a visit for final approval, the entire visit record and all related data (product discussions, samples, expenses, signatures) are locked (read-only) and a frozen snapshot is generated for compliance records,  
**So that** we maintain an immutable audit trail of every interaction and ensure data integrity for regulatory compliance.

**Why it matters:** Submitted visits must be immutable to satisfy compliance audits, regulatory inspections, and legal discovery. Snapshots provide irrefutable proof of what was recorded at submission time, preventing retroactive changes.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Visit Submission | Visit Detail Screen | Rep clicks "Submit Visit" button | Current Visit__c + all child records | Visit__c |
| Post-Submission Lock | Apex Trigger | Immediately on submission, lock all records and generate snapshot | Visit__c and all related objects | VisitAuditSnapshot__c |

---

## Current State (from Salesforce Object Model)

### Visit__c (Relevant Fields)

- **Field:** `VisitStatus__c` (Picklist) — "Planned", "In Progress", "Completed", "Submitted" (locked), "Cancelled"
- **Field:** `SubmittedDate__c` (DateTime, auto-populated on submission)
- **Field:** `SubmittedBy__c` (Lookup to User, auto-populated)
- **Field:** `IsLocked__c` (Checkbox, read-only) — True after submission
- **Field:** `AuditSnapshotId__c` (Lookup to VisitAuditSnapshot__c) — Reference to snapshot

### VisitAuditSnapshot__c (Custom Object)

- **Field:** `Visit__c` (Lookup to Visit__c)
- **Field:** `SnapshotDate__c` (DateTime) — When snapshot was taken
- **Field:** `SnapshotContent__c` (Text Long, JSON) — Frozen copy of visit and all child records
- **Field:** `Checksum__c` (Text) — Hash of snapshot for tamper detection
- **Field:** `Locked__c` (Checkbox) — True (immutable)

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Submit Visit Button** | OmniScript Button | Trigger submission workflow | Button click starts Apex flow |
| **Pre-Submission Validation Flow** | Apex Flow | Validate all required sections before allowing submission | Check required fields, validations, compliance checks |
| **Visit Lock Trigger** | Apex Trigger | After Visit__c.VisitStatus = "Submitted", lock all related records | Trigger on after update; set Locked__c = true on all child records |
| **Audit Snapshot Generator** | Apex Class | Generate JSON snapshot of entire visit + child data | Called from trigger; captures all record field values at submission time |
| **Snapshot Immutability** | Apex Validation Rule | Prevent edits to VisitAuditSnapshot__c | Read-only object; no updates allowed after creation |

### Visit Submission & Locking Logic (Pseudocode)

```javascript
trigger VisitAfterUpdate on Visit__c (after update) {
  // 1. Identify visits that transitioned to "Submitted"
  List<Visit__c> submittedVisits = new List<Visit__c>();
  for (Visit__c visit : Trigger.new) {
    Visit__c oldVisit = Trigger.oldMap.get(visit.Id);
    if (oldVisit.VisitStatus__c != 'Submitted' && visit.VisitStatus__c == 'Submitted') {
      submittedVisits.add(visit);
    }
  }

  if (submittedVisits.isEmpty()) return;

  // 2. For each submitted visit, generate snapshot and lock records
  for (Visit__c visit : submittedVisits) {
    // Generate snapshot
    VisitAuditSnapshot__c snapshot = generateAuditSnapshot(visit);
    insert snapshot;

    // Lock all child records
    lockVisitRecords(visit.Id);

    // Update visit with snapshot reference and lock flag
    visit.AuditSnapshotId__c = snapshot.Id;
    visit.IsLocked__c = true;
    visit.SubmittedDate__c = DateTime.now();
    visit.SubmittedBy__c = UserInfo.getUserId();
  }

  // 3. Update visits
  update submittedVisits;
}

function generateAuditSnapshot(Visit__c visit) {
  // 1. Query visit and all related data
  Map<String, Object> snapshotData = new Map<String, Object>();
  
  snapshotData.put('Visit', new Map<String, Object>{
    'Id' => visit.Id,
    'VisitDate' => visit.VisitDate__c,
    'VisitType' => visit.VisitType__c,
    'PrimaryHCP' => visit.PrimaryHCP__c,
    'VisitStatus' => visit.VisitStatus__c,
    'SubmittedDate' => DateTime.now()
  });

  // 2. Query child records (ProductDiscussion, SampleDistribution, VisitExpense, etc.)
  List<ProductDiscussion__c> productDiscussions = [
    SELECT Id, Product__c, HCPReaction__c, TimeSpentMinutes__c, MessagesFocused__c
    FROM ProductDiscussion__c
    WHERE Visit__c = :visit.Id
  ];
  snapshotData.put('ProductDiscussions', productDiscussions);

  List<SampleDistribution__c> sampleDistributions = [
    SELECT Id, Sample__c, QuantityDistributed__c, RecipientNPI__c, IsSignedByRecipient__c
    FROM SampleDistribution__c
    WHERE Visit__c = :visit.Id
  ];
  snapshotData.put('SampleDistributions', sampleDistributions);

  List<VisitExpense__c> expenses = [
    SELECT Id, ExpenseCategory__c, Description__c, Amount__c, IsPersonal__c
    FROM VisitExpense__c
    WHERE Visit__c = :visit.Id
  ];
  snapshotData.put('Expenses', expenses);

  // ... (repeat for all child objects)

  // 3. Serialize to JSON and calculate checksum
  String snapshotJson = JSON.serialize(snapshotData);
  String checksum = generateChecksum(snapshotJson);

  // 4. Create snapshot record
  VisitAuditSnapshot__c snapshot = new VisitAuditSnapshot__c(
    Visit__c = visit.Id,
    SnapshotDate__c = DateTime.now(),
    SnapshotContent__c = snapshotJson,
    Checksum__c = checksum,
    Locked__c = true
  );

  return snapshot;
}

function lockVisitRecords(String visitId) {
  // Query all child records and set Locked__c = true
  
  List<ProductDiscussion__c> productDiscussions = [
    SELECT Id FROM ProductDiscussion__c WHERE Visit__c = :visitId
  ];
  for (ProductDiscussion__c pd : productDiscussions) {
    pd.Locked__c = true;
  }
  update productDiscussions;

  List<SampleDistribution__c> sampleDistributions = [
    SELECT Id FROM SampleDistribution__c WHERE Visit__c = :visitId
  ];
  for (SampleDistribution__c sd : sampleDistributions) {
    sd.Locked__c = true;
  }
  update sampleDistributions;

  // ... (repeat for all child objects)
}

function String generateChecksum(String content) {
  // SHA-256 hash of snapshot content
  Blob hash = Crypto.generateDigest('SHA-256', Blob.valueOf(content));
  return EncodingUtil.convertToHex(hash);
}
```

---

## Acceptance Criteria

### Scenario 1: Submit Visit — Happy Path

**Given** a rep completes visit documentation (product discussions, samples, expenses, signatures),  
**When** they click the "Submit Visit" button,  
**Then** the system:
- Validates all required sections (at least one product discussion, signature captured, etc.)
- Shows confirmation: "Are you sure? Once submitted, this visit cannot be edited."
- Button displays: "Submit" and "Cancel"

**And when** rep clicks "Submit",  
**Then** the system:
- Changes VisitStatus__c = "Submitted"
- Populates SubmittedDate__c and SubmittedBy__c
- Generates audit snapshot with all child data
- Locks all related records (ProductDiscussion, SampleDistribution, VisitExpense, etc.)

---

### Scenario 2: Attempt to Edit Locked Records

**Given** a visit has been submitted and is locked,  
**When** a rep (or manager) opens the visit detail screen,  
**Then** all child records display in read-only mode.  
**And if they attempt to click "Edit"**, the system displays:
- **Message:** "This visit has been submitted and locked. Contact your manager to request changes."
- **Edit button disabled**

---

### Scenario 3: Audit Snapshot Immutability

**Given** a compliance officer queries the VisitAuditSnapshot__c record for an audited visit,  
**When** they view the snapshot JSON,  
**Then** they can see the frozen state of all child records at submission time.  
**And if an auditor attempts to edit the snapshot**, the system prevents modification:
- **Error:** "Audit snapshots are immutable and cannot be edited."

---

### Scenario 4: Checksum Validation

**Given** an external auditor downloads the audit snapshot to verify integrity,  
**When** they recalculate the SHA-256 hash of the snapshot content,  
**Then** it matches Checksum__c field, confirming the snapshot has not been tampered with.

---

### Scenario 5: Unlock Request for Audit Purposes

**Given** a compliance officer discovers an error in a submitted visit (e.g., incorrect sample amount),  
**When** they request an "Unlock for Correction" approval from a manager,  
**Then** a workflow initiates:
- Manager receives notification
- If approved, a new version of the visit is created for correction
- Original snapshot remains locked and unchanged (for audit trail)
- New snapshot is created after re-submission

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Unlock Approval Process** Should unlocking require single manager approval or multi-level approval? | Governance; compliance risk | Compliance Officer |
| 2 | **Snapshot Retention** How long should audit snapshots be retained (7 years, permanently)? | Data storage; regulatory requirement | Compliance Officer |
| 3 | **Audit Log Completeness** Should every field change (before lock) be captured in a separate audit log in addition to the snapshot? | Granularity of audit trail | Audit Officer |
| 4 | **Cascade Lock** Should locking a visit automatically lock related HCP account records, or just visit child records? | Data governance; potential conflicts | Product Manager |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|------------|-------------|
| **Visit Lock Trigger** | Apex Trigger | HIGH | Affects all visited records; must be reliable |
| **Audit Snapshot Generator** | Apex Class | HIGH | Compliance-critical; accuracy essential |
| **Snapshot Immutability** | Validation Rule | HIGH | Regulatory requirement; cannot be compromised |
| **Checksum Validation** | Cryptographic Hash | HIGH | Data integrity verification |
| **Unlock Approval Workflow** | Apex Flow / Chatter | MEDIUM | Exception handling; governance |

---

## Definition of Done Checklist

- [ ] VisitAuditSnapshot__c custom object created with all fields
- [ ] Visit submission flow built (validation, confirmation dialog, submit button)
- [ ] Apex trigger on Visit after update (transition to "Submitted")
- [ ] Audit snapshot generator implemented (captures all child records as JSON)
- [ ] Checksum calculated (SHA-256 hash) for integrity verification
- [ ] All child records locked (Locked__c = true) on visit submission
- [ ] Read-only field validation on all child objects (prevent edits after lock)
- [ ] Unlock request workflow built (manager approval)
- [ ] Apex test coverage ≥ 95% for submission and locking logic
- [ ] Integration test: Submit visit with 5 child records, verify all locked and snapshot created
- [ ] Integration test: Attempt to edit locked record (fails gracefully)
- [ ] Compliance dashboard: "Submitted Visits", "Audit Snapshot Integrity Checks"
- [ ] QA sign-off: Submission is fast (< 5 seconds); locking is complete
- [ ] Documentation: Compliance officer guide on audit snapshots and unlock procedures
- [ ] Training: Compliance team and rep team onboarding on submission process

---

---

# Epic 4: Administration & Setup

## USER STORY 4.1: Map Visit Record Types to Account Record Types in Admin Console

**Persona:** System Administrator, Configuration Manager, Developer  
**Priority:** P1  
**Related Objects:** Visit__c, RecordType (metadata), VisitRecordTypeMapping__c (custom metadata or object)  
**Integration Procedures:** N/A (Admin Console configuration)  
**Relevant Requirements:** FHN-144 (Visit/Account record type mapping)

---

## Story

**As a** System Administrator,  
**I want** to configure mappings between Visit Record Types (e.g., "HCP Visit", "Facility Visit", "Pharmacy Visit") and Account Record Types (e.g., "Healthcare Professional", "Healthcare Facility", "Pharmacy"),  
**So that** when a rep selects an Account for a visit, only applicable Visit Record Types are displayed, ensuring data consistency and reducing configuration complexity.

**Why it matters:** Without record type mapping, reps can create visits with mismatched types (e.g., "HCP Visit" for a Pharmacy account), breaking reporting and validations. Mapping ensures the right data model for each account type.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Visit Creation | OmniScript / Form | After rep selects Account, filter available Visit Record Types | Account.RecordType, VisitRecordTypeMapping__c | Visit__c |
| Admin Configuration | Setup / Admin Console | Admin defines mappings (Facility → Facility Visit, HCP → HCP Visit, etc.) | Admin input | VisitRecordTypeMapping__c |

---

## Current State (from Salesforce Object Model)

### RecordType Metadata

Account Record Types:
- Healthcare Professional (HCP)
- Healthcare Facility
- Pharmacy
- Hospital System
- Other

Visit Record Types:
- HCP Visit
- Facility Visit
- Pharmacy Visit
- Group Presentation
- Lunch & Learn

### VisitRecordTypeMapping__c (Custom Metadata Type)

- **Field:** `AccountRecordTypeName__c` (Text) — "Healthcare Professional"
- **Field:** `AllowedVisitRecordTypes__c` (Multi-select Picklist or Long Text) — "HCP Visit", "Group Presentation", "Lunch & Learn"
- **Field:** `IsActive__c` (Checkbox) — Enable/disable mapping
- **Field:** `RequiredFields__c` (Text) — Fields specific to this combo (e.g., "DEA License for Prescriber HCPs")

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Admin Console Configuration Page** | Salesforce Setup UI | Create custom admin page showing Account ↔ Visit Record Type matrix | Table showing all account types and checkboxes for applicable visit types |
| **Visit Record Type Filtering** | Apex / Flow | When rep selects Account, dynamically filter Visit Record Types in dropdown | Query VisitRecordTypeMapping__c; return only allowed visit record types |
| **Validation Rule** | Apex | Prevent creation of Visit__c with invalid Account ↔ Visit Record Type combination | Lookup in VisitRecordTypeMapping__c; block if not mapped |
| **Admin Metadata Setup** | Custom Metadata Loader | Pre-populate default mappings (HCP → HCP Visit, Facility → Facility Visit, etc.) | Deployment package with standard mappings |

### Visit Record Type Filtering Logic (Pseudocode)

```javascript
async function filterVisitRecordTypesByAccount(accountId) {
  // 1. Query Account record type
  Account account = [SELECT RecordTypeId FROM Account WHERE Id = :accountId];
  String accountRecordTypeName = accountRecordTypeMap.get(account.RecordTypeId);

  // 2. Query VisitRecordTypeMapping__c
  List<VisitRecordTypeMapping__c> mappings = [
    SELECT AllowedVisitRecordTypes__c
    FROM VisitRecordTypeMapping__c
    WHERE AccountRecordTypeName__c = :accountRecordTypeName
    AND IsActive__c = true
  ];

  if (mappings.isEmpty()) {
    // No specific mapping; show all visit record types
    return getAllVisitRecordTypes();
  }

  // 3. Parse allowed visit record types
  String allowedTypes = mappings[0].AllowedVisitRecordTypes__c;
  List<String> allowedTypeList = allowedTypes.split(';');

  // 4. Query Visit Record Type metadata
  List<RecordType> visitRecordTypes = [
    SELECT Id, Name
    FROM RecordType
    WHERE SobjectType = 'Visit__c'
    AND Name IN :allowedTypeList
    AND IsActive = true
  ];

  return visitRecordTypes;
}
```

---

## Acceptance Criteria

### Scenario 1: Admin Configures Mapping (Happy Path)

**Given** a System Administrator opens the Visit Record Type Mapping configuration page,  
**When** they view the admin console,  
**Then** they see a matrix:
- **Rows:** Account Record Types (HCP, Facility, Pharmacy, Hospital System)
- **Columns:** Visit Record Types (HCP Visit, Facility Visit, Pharmacy Visit, Group Presentation, Lunch & Learn)
- **Cells:** Checkboxes to enable/disable mappings

**And when** admin checks the box for "Healthcare Professional" → "HCP Visit",  
**Then** the mapping is saved to VisitRecordTypeMapping__c.

---

### Scenario 2: Rep Creates Visit with Filtered Record Types

**Given** a rep selects Account "Dr. Sarah Chen" (Record Type = Healthcare Professional),  
**When** they click "New Visit",  
**Then** the Visit Record Type dropdown shows only mapped types:
- HCP Visit ✓
- Group Presentation ✓
- Lunch & Learn ✓
- (Facility Visit, Pharmacy Visit are hidden)

**And when** the rep selects "HCP Visit", the form loads with HCP-specific fields.

---

### Scenario 3: Prevent Invalid Record Type

**Given** a rep tries to create a "Pharmacy Visit" for a Healthcare Professional account,  
**When** they attempt to save the visit,  
**Then** the system displays an error:
- **Validation Error:** "Pharmacy Visit is not applicable for Healthcare Professional accounts. Select HCP Visit instead."

---

## Definition of Done Checklist

- [ ] VisitRecordTypeMapping__c Custom Metadata Type created
- [ ] Admin configuration page built (matrix UI with checkboxes)
- [ ] Default mappings loaded (HCP → HCP Visit, Facility → Facility Visit, etc.)
- [ ] Visit Record Type filtering logic implemented in OmniScript/LWC
- [ ] Validation rule prevents invalid Account ↔ Visit Record Type combos
- [ ] Apex test coverage ≥ 85% for filtering and validation logic
- [ ] Integration test: Configure mapping, create visit, verify filtered record types
- [ ] QA sign-off: Admin console is intuitive; filtering works immediately
- [ ] Documentation: Admin guide on configuring record type mappings
- [ ] Training: Admin team onboarding on setup and configuration

---

## USER STORY 4.2: Enable Trigger Handlers for Record Locking and Cascade Deletes

**Persona:** System Administrator, Developer, Compliance Officer  
**Priority:** P0  
**Related Objects:** All Visit-related objects (Visit__c, ProductDiscussion__c, SampleDistribution__c, etc.)  
**Integration Procedures:** N/A (Apex Triggers)  
**Relevant Requirements:** FHN-151 (Trigger handler administration)

---

## Story

**As a** System Administrator or Compliance Officer,  
**I want** to be able to enable/disable core trigger handlers (such as "Record Locking on Submit", "Parent-Child Sync", "Cascade Delete", "Sample Limits Validation") via an Admin Console configuration, without requiring developer intervention,  
**So that** I can manage data integrity rules, adjust compliance controls, and troubleshoot issues without code changes.

**Why it matters:** Trigger handlers are critical to data consistency and compliance, but they're often hardcoded and inflexible. An admin-configurable trigger handler framework enables governance and rapid issue resolution.

---

## Scope

| Flow | Component | Affected Step | Data Source | Object |
|------|-----------|---------------|-------------|--------|
| Admin Configuration | Setup / Admin Console | Admin enables/disables trigger handlers | Admin input | TriggerHandlerConfig__c (custom metadata or object) |
| Trigger Execution | Apex Triggers | At runtime, check if handler is enabled before executing | TriggerHandlerConfig__c | Relevant objects |

---

## Current State (from Salesforce Object Model)

### TriggerHandlerConfig__c (Custom Metadata Type or Object)

- **Field:** `HandlerName__c` (Text) — "RecordLockingOnSubmit", "CascadeDelete", "SampleLimitValidation", "ParentChildSync"
- **Field:** `IsEnabled__c` (Checkbox) — True/False to enable/disable handler
- **Field:** `Description__c` (Text) — Purpose of handler
- **Field:** `RequiredPermission__c` (Text) — Permission required to disable (e.g., "Compliance Manager")
- **Field:** `BypassUsers__c` (Text) — User IDs who can bypass this handler (comma-separated)

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **TriggerHandlerConfig__c** | Custom Metadata Type | Central registry of all trigger handlers | Queryable; controls handler behavior at runtime |
| **Trigger Handler Base Class** | Apex Class | Framework for checking if handler is enabled before execution | Static method: `isTriggerEnabled(String handlerName)` |
| **Admin Configuration Page** | Salesforce Setup UI | Display list of handlers with toggle to enable/disable | Two-column table: Handler Name | Enabled/Disabled |
| **Audit Log** | Apex Trigger | Log all handler enable/disable changes for compliance | Track who changed what and when |

### Trigger Handler Configuration Pattern (Pseudocode)

```javascript
public class TriggerHandlerConfig {
  // Cache of handler configs (static variable)
  private static Map<String, TriggerHandlerConfig__mdt> handlerConfigs;

  // Fetch handler configs (with caching)
  public static Map<String, TriggerHandlerConfig__mdt> getHandlerConfigs() {
    if (handlerConfigs == null) {
      handlerConfigs = new Map<String, TriggerHandlerConfig__mdt>();
      for (TriggerHandlerConfig__mdt config : [
        SELECT DeveloperName, IsEnabled__c, BypassUsers__c
        FROM TriggerHandlerConfig__mdt
      ]) {
        handlerConfigs.put(config.DeveloperName, config);
      }
    }
    return handlerConfigs;
  }

  // Check if trigger handler is enabled
  public static Boolean isTriggerEnabled(String handlerName) {
    Map<String, TriggerHandlerConfig__mdt> configs = getHandlerConfigs();
    TriggerHandlerConfig__mdt config = configs.get(handlerName);
    
    if (config == null) {
      // Handler not found; default to enabled for safety
      return true;
    }

    // Check if current user is in bypass list
    String currentUserId = UserInfo.getUserId();
    if (config.BypassUsers__c != null && config.BypassUsers__c.contains(currentUserId)) {
      return false; // Bypassed for this user
    }

    return config.IsEnabled__c;
  }
}

trigger VisitAfterUpdate on Visit__c (after update) {
  // Check if RecordLockingOnSubmit handler is enabled
  if (!TriggerHandlerConfig.isTriggerEnabled('RecordLockingOnSubmit')) {
    return; // Handler disabled; skip
  }

  // Proceed with locking logic
  // ... lock records ...
}

trigger ProductDiscussionAfterDelete on ProductDiscussion__c (after delete) {
  // Check if CascadeDelete handler is enabled
  if (!TriggerHandlerConfig.isTriggerEnabled('CascadeDelete')) {
    return; // Handler disabled; skip
  }

  // Proceed with cascade delete logic
  // ... delete related records ...
}
```

---

## Acceptance Criteria

### Scenario 1: Admin Enables/Disables Handlers (Happy Path)

**Given** a System Administrator opens the Trigger Handler Admin page,  
**When** they view the configuration,  
**Then** they see a list of handlers:
- Record Locking on Submit (ENABLED)
- Cascade Delete (ENABLED)
- Sample Limit Validation (ENABLED)
- Parent-Child Sync (DISABLED)
- Each row has a toggle switch

**And when** admin clicks the toggle for "Parent-Child Sync" to ENABLED,  
**Then** the change is saved, and from the next visit update onward, the parent-child sync handler executes.

---

### Scenario 2: Audit Log Tracks Handler Changes

**Given** an admin enables a handler,  
**When** they save the change,  
**Then** an audit log entry is created:
- **Entry:** "[2026-04-15 10:30:00] Admin1 ENABLED 'Parent-Child Sync' handler. Reason: Troubleshooting data inconsistency."
- **User:** Admin1 ID
- **Action:** ENABLED
- **Handler:** Parent-Child Sync
- **Timestamp:** 2026-04-15 10:30:00

---

### Scenario 3: Trigger Checks Handler Status at Runtime

**Given** a rep creates a ProductDiscussion__c record,  
**When** the Apex trigger fires (after insert),  
**Then** the trigger queries TriggerHandlerConfig__mdt for "SomeHandler",  
**And if IsEnabled__c = false**, the handler logic is skipped.

---

## Definition of Done Checklist

- [ ] TriggerHandlerConfig__mdt Custom Metadata Type created
- [ ] TriggerHandlerConfig Apex utility class built with isTriggerEnabled() method
- [ ] All core trigger handlers refactored to use TriggerHandlerConfig check
- [ ] Admin configuration UI page built (list of handlers with toggle)
- [ ] Audit log captures all handler enable/disable changes
- [ ] Default handler configs deployed (all core handlers enabled by default)
- [ ] Apex test coverage ≥ 90% for handler configuration and bypass logic
- [ ] Integration test: Disable handler, verify trigger logic skipped
- [ ] Integration test: Enable handler, verify trigger logic executes
- [ ] QA sign-off: Handler enable/disable is effective immediately
- [ ] Documentation: Admin guide on enabling/disabling trigger handlers and troubleshooting
- [ ] Training: Admin team onboarding on handler management

---

---

# COMPREHENSIVE SUMMARY & EFFORT ESTIMATES

## All Epics & User Stories Summary

### Epic 1: Visit Planning & Preparation (3 stories)
| Story | Title | Effort | Priority |
|-------|-------|--------|----------|
| US 1.1 | Schedule Multi-HCP Group Visits | 8-12 days | P0 |
| US 1.2 | Visit Conflict Validation & Alerts | 10-14 days | P0 |
| US 1.3 | AI-Backed Visit Recommendations | 12-18 days | P1 |
| **Epic 1 Total** | | **30-44 days** | **P0** |

### Epic 2: Visit Execution & Compliance (4 stories)
| Story | Title | Effort | Priority |
|-------|-------|--------|----------|
| US 2.1 | Present Intelligent Content | 8-12 days | P0 |
| US 2.2 | Disburse Samples & Capture Signature | 10-15 days | P0 |
| US 2.3 | Enforce License Validations | 8-12 days | P0 |
| US 2.4 | Capture Medical Inquiries & Surveys | 6-10 days | P1 |
| **Epic 2 Total** | | **32-49 days** | **P0** |

### Epic 3: Visit Closure & Auditing (4 stories)
| Story | Title | Effort | Priority |
|-------|-------|--------|----------|
| US 3.1 | Log Product Discussions | 6-10 days | P0 |
| US 3.2 | Record Expenses & Marketing Items | 8-12 days | P0 |
| US 3.3 | Set Next Visit Objectives | 4-8 days | P1 |
| US 3.4 | Lock Records & Generate Audit Snapshot | 10-14 days | P0 |
| **Epic 3 Total** | | **28-44 days** | **P0** |

### Epic 4: Administration & Setup (2 stories)
| Story | Title | Effort | Priority |
|-------|-------|--------|----------|
| US 4.1 | Map Record Types | 3-5 days | P1 |
| US 4.2 | Enable Trigger Handlers | 4-8 days | P0 |
| **Epic 4 Total** | | **7-13 days** | **P0** |

---

## Overall Project Effort Estimate

**Total Estimated Effort: 97-150 days (development + testing)**

**Recommended Timeline:**
- Phase 1 (Sprint 1-3, 15 days): Epic 4 setup + Epic 1 foundation (US 1.1, 1.2)
- Phase 2 (Sprint 3-6, 30 days): Epic 2 core (US 2.1, 2.2, 2.3) + US 1.3
- Phase 3 (Sprint 7-10, 40 days): Epic 3 (all stories) + US 2.4
- Phase 4 (Sprint 11-14, 20 days): Testing, UAT, deployment, training

**Total Timeline: 16-20 weeks (4-5 months)**

---

## USER STORY DEPENDENCY GRAPH

```
┌─────────────────────────────────────────────────────────────────┐
│                     Life Sciences Visit Management                │
│                      Dependency Graph                             │
└─────────────────────────────────────────────────────────────────┘

PHASE 0 (FOUNDATION)
┌──────────────────────────────┐
│ US 4.1: Map Record Types     │
│ US 4.2: Enable Trigger       │
│ Handlers                      │
└──────────────────────────────┘
         ↓↓↓ (prerequisites)

PHASE 1 (VISIT PLANNING & EXECUTION)
┌──────────────────────────────────────────────────────────────────┐
│                     US 1.1 ←→ US 1.2 ←→ US 1.3                   │
│               Multi-HCP   Conflict    AI-Backed                   │
│               Visits      Validation  Recommendations             │
│                                                                   │
│  (US 1.2 depends on US 1.1 for visit scheduling context)         │
│  (US 1.3 depends on both for HCP profiles)                       │
└──────────────────────────────────────────────────────────────────┘
         ↓↓↓ (foundation laid)

PHASE 2 (VISIT EXECUTION)
┌──────────────────────────────────────────────────────────────────┐
│  US 2.1 ←─── US 2.2 ←─── US 2.3 ←─── US 2.4                     │
│  Content   Samples &    License      Medical                      │
│  Sharing   Signature    Validation   Inquiries                    │
│                                                                   │
│  (US 2.2 depends on US 2.3 for compliance checks)                │
│  (US 2.3 must run before US 2.2 signature is accepted)           │
│  (US 2.4 optional, parallel with others)                         │
└──────────────────────────────────────────────────────────────────┘
         ↓↓↓ (visit data ready)

PHASE 3 (VISIT CLOSURE & AUDIT)
┌──────────────────────────────────────────────────────────────────┐
│  US 3.1 → US 3.2 → US 3.3 → US 3.4 (FINAL)                       │
│  Product  Expenses  Next Visit  Lock & Snapshot                   │
│  Logging  & Items   Objectives  (Immutable)                       │
│                                                                   │
│  (Linear dependency: US 3.4 must be last)                        │
│  (US 3.4 locks all prior records)                                │
└──────────────────────────────────────────────────────────────────┘

CRITICAL PATH (BLOCKING):
US 4.2 → US 1.1 → US 1.2 → US 2.2 → US 2.3 → US 3.4

PARALLEL EXECUTION (NON-BLOCKING):
- US 1.3 (AI recommendations) can develop in parallel with US 1.1/1.2
- US 2.4 (Inquiries) can develop in parallel with US 2.1/2.2/2.3
- US 3.1/3.2/3.3 can develop in parallel with each other
```

## LUCID DIAGRAM REQUIREMENTS

- Create a Lucid diagram for each individual user story.
- Each story-level diagram must show the previous story feeding into the current
  story and the next story that depends on it.
- Create one consolidated end-to-end Lucid diagram for all 12 stories in
  execution order across all 4 epics.
- Show blocking dependencies, shared objects, and shared integrations so the
  diagram works as a delivery map.
- Highlight the current story path when the diagram is generated for a single
  story.

---

## QTA TEST BRIDGE

### Browser Automation Test Coverage Roadmap

```markdown
# Quality Test Agent (QTA) Browser Automation Coverage

## Epic 1: Visit Planning & Preparation

### US 1.1: Schedule Multi-HCP Group Visits
- **Test Scenario 1.1.1:** Create visit, add 3 external HCPs as attendees
  - Test Steps: Navigate to Visit creation → Select Account → Add Attendees (3x) → Save
  - Expected Result: 3 VisitAttendee__c records created, display in list
  - Automation: Form fill, lookup selection, button clicks, record verification

- **Test Scenario 1.1.2:** Remove attendee before submission
  - Test Steps: Open visit → Edit attendees → Remove one → Save
  - Expected Result: Attendee list updates, record deleted
  - Automation: Click remove button, verify record gone

- **Test Scenario 1.1.3:** Prevent submission without primary HCP attendee
  - Test Steps: Create visit, add secondary HCP, try submit without primary
  - Expected Result: Validation error displayed
  - Automation: Form validation, error message capture

### US 1.2: Visit Conflict Validation & Alerts
- **Test Scenario 1.2.1:** Exceed frequency limit, display warning
  - Test Steps: Schedule 4th visit to HCP in same quarter (limit: 3)
  - Expected Result: Warning modal displays "Proceed?" options
  - Automation: Modal dialog interaction, button selection

- **Test Scenario 1.2.2:** HCP with expired license blocked
  - Test Steps: Try to schedule visit to HCP with expired license
  - Expected Result: Error banner displayed, visit save blocked
  - Automation: Form submission, error capture, button state verification

### US 1.3: AI-Backed Visit Recommendations
- **Test Scenario 1.3.1:** Generate recommendations for scheduled visit
  - Test Steps: Schedule visit, open visit detail, verify recommendations display
  - Expected Result: 3-5 recommendations show in prep card
  - Automation: Element visibility wait, content verification

- **Test Scenario 1.3.2:** Mark recommendation as helpful
  - Test Steps: Click "Mark Helpful" on recommendation
  - Expected Result: Recommendation updated, visual feedback
  - Automation: Button click, element state change

## Epic 2: Visit Execution & Compliance

### US 2.1: Present Intelligent Content
- **Test Scenario 2.1.1:** Search content library by title
  - Test Steps: Open Content Library → Search for "Heart Failure" → Verify results
  - Expected Result: 3-5 filtered results display
  - Automation: Search input, result list verification

- **Test Scenario 2.1.2:** Open PDF content in full-screen preview
  - Test Steps: Click "Present" on PDF → Verify full-screen display
  - Expected Result: PDF viewer opens, zoom controls visible
  - Automation: Button click, element visibility, PDF rendering verification

### US 2.2: Disburse Samples & Capture Signature
- **Test Scenario 2.2.1:** Select samples from inventory
  - Test Steps: Click "Add Sample" → Select Product A, Qty=3 → Save
  - Expected Result: SampleDistribution record created
  - Automation: Dropdown selection, number input, form submission

- **Test Scenario 2.2.2:** Capture digital signature on mobile
  - Test Steps: Draw signature on pad → Confirm → Verify saved
  - Expected Result: Signature image uploaded, SignatureLog created
  - Automation: Canvas drawing simulation, file upload capture

- **Test Scenario 2.2.3:** Prevent over-distribution
  - Test Steps: Try to distribute more units than available
  - Expected Result: Error message, form disabled
  - Automation: Validation message capture, button state check

### US 2.3: Enforce License Validations
- **Test Scenario 2.3.1:** Validation passes for active license
  - Test Steps: Select HCP with valid license, attempt signature → Verify success
  - Expected Result: Signature accepted without warning
  - Automation: Form flow, element visibility

- **Test Scenario 2.3.2:** Validation blocks expired license
  - Test Steps: Select HCP with expired license, attempt signature
  - Expected Result: Error message, signature blocked
  - Automation: Error capture, button disabled state

### US 2.4: Medical Inquiries & Surveys
- **Test Scenario 2.4.1:** Capture medical inquiry
  - Test Steps: Click "Capture Inquiry" → Fill form → Submit
  - Expected Result: MedicalInquiry__c created, confirmation displayed
  - Automation: Modal interaction, form fill, record creation verification

- **Test Scenario 2.4.2:** Launch and complete pulse survey
  - Test Steps: Click "Launch Survey" → Answer 3 questions → Submit
  - Expected Result: SurveyResponse created with all answers
  - Automation: Survey form interaction, multi-step navigation

## Epic 3: Visit Closure & Auditing

### US 3.1: Log Product Discussions
- **Test Scenario 3.1.1:** Add product discussion with reaction
  - Test Steps: Click "Add Product" → Select Product A → Select reaction "Very Interested" → Save
  - Expected Result: ProductDiscussion__c created with reaction
  - Automation: Form fill, dropdown selection, record verification

### US 3.2: Record Expenses & Marketing Items
- **Test Scenario 3.2.1:** Log meal expense with receipt photo
  - Test Steps: Click "Add Expense" → Select "Meal" → Enter amount → Upload receipt → Save
  - Expected Result: VisitExpense__c created with receipt image linked
  - Automation: File upload, form submission, record verification

### US 3.3: Next Visit Objectives
- **Test Scenario 3.3.1:** Set objectives for next visit
  - Test Steps: Click "Add Objective" → Enter objective → Save
  - Expected Result: NextVisitObjective__c created
  - Automation: Form fill, record creation

### US 3.4: Lock Records on Submission
- **Test Scenario 3.4.1:** Submit visit, verify all records locked
  - Test Steps: Click "Submit Visit" → Confirm dialog → Verify records locked
  - Expected Result: VisitStatus = "Submitted", all child records read-only
  - Automation: Button click, confirmation dialog, record state verification

- **Test Scenario 3.4.2:** Attempt to edit locked record (fails)
  - Test Steps: Try to edit ProductDiscussion after submission
  - Expected Result: Edit button disabled, message displayed
  - Automation: Button state check, message capture

## Epic 4: Administration & Setup

### US 4.1: Map Record Types
- **Test Scenario 4.1.1:** Admin configures record type mapping
  - Test Steps: Open Admin Console → Configure HCP → HCP Visit mapping
  - Expected Result: Mapping saved, rep sees filtered options on next visit
  - Automation: Admin panel interaction, configuration saving

### US 4.2: Enable/Disable Trigger Handlers
- **Test Scenario 4.2.1:** Admin disables handler, verify logic skipped
  - Test Steps: Disable RecordLockingOnSubmit → Submit visit → Verify not locked
  - Expected Result: Visit submitted but not locked
  - Automation: Admin toggle, record state verification

---

## QTA Test Execution Plan

**Total Test Scenarios: 25**
**Estimated Test Execution Time: 4-6 hours (automated)**
**Test Coverage Goal: 85%+ of user journeys**

**Phase 1 (Sprint 3):** US 4.1, 4.2, US 1.1, 1.2
**Phase 2 (Sprint 6):** US 1.3, US 2.1, 2.2, 2.3
**Phase 3 (Sprint 10):** US 2.4, US 3.1, 3.2, 3.3, 3.4
**Phase 4 (Sprint 14):** Full regression (all 25 scenarios)

---
```

---

## Conclusion

This comprehensive Life Sciences Visit Management documentation provides:

✅ **12 detailed user stories** across 4 epics with full technical specifications
✅ **Effort estimates** ranging from 3-18 days per story
✅ **Object schemas** and field-level design for Salesforce
✅ **Acceptance criteria** with real-world scenarios
✅ **Clarification questions** and impact analysis
✅ **Dependency graph** showing critical path
✅ **QTA browser automation test bridge** with 25+ test scenarios
✅ **Definition of Done checklists** for QA and compliance

**Next Steps:**
1. Review effort estimates with development team
2. Prioritize stories based on business drivers
3. Create Jira/GUS epics and user stories from this document
4. Schedule QTA test automation execution per phase
5. Begin Phase 1 development (US 4.1, 4.2 foundation setup)
6. Generate Lucid diagrams for each story and the consolidated end-to-end flow

---

*Document Complete: Life Sciences Visit Management — Implementation Ready*
*Created: 2026-03-30*
*Version: 1.0*
