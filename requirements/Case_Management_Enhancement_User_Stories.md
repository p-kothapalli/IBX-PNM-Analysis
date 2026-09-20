# Case Management Enhancement - User Stories

---

## User Story 1: ReRoute Case to Original Stage Owner (Bypass Round-Robin)

### Title
Preserve and Restore Original Case Owner When Routing Between PSV and QC Review Stages

### User Story
**As a** Credentialing Operations Manager,  
**I want** the system to automatically re-assign the case back to the original stage owner when a case is returned to a previously-visited stage (PSV or QC Review),  
**So that** the same analyst who originally worked the case continues ownership without triggering round-robin reassignment, ensuring continuity and efficiency.

### Description / Background
Currently, when a case is pushed back from QC Review to PSV and then returned to QC Review, the system triggers a round-robin assignment — potentially assigning the case to a different QC Reviewer. This disrupts continuity because the original reviewer already has context on the case.

**Expected Flow:**
```
App Review -> PSV (Owner: John) -> QC Review (Owner: Joe) -> Return to PSV (Owner: John ✓ No Round Robin) -> Return to QC Review (Owner: Joe ✓ No Round Robin)
```

The system must "remember" the last owner at each stage and bypass round-robin logic when returning to that stage.

### Acceptance Criteria

| # | Criteria | Testable Condition |
|---|----------|-------------------|
| 1 | When a case moves from QC Review back to PSV, the system assigns the case to the **last PSV owner** (not round-robin). | Case Owner = original PSV owner after return |
| 2 | When a case moves from PSV back to QC Review, the system assigns the case to the **last QC Review owner** (not round-robin). | Case Owner = original QC Review owner after return |
| 3 | The system stores the previous owner for each stage on the Case record (or related object). | Fields `Previous_PSV_Owner__c` and `Previous_QC_Review_Owner__c` are populated after first assignment |
| 4 | On the **first** visit to a stage, normal round-robin assignment applies. | Round-robin only fires when `Previous_[Stage]_Owner__c` is null |
| 5 | If the previous owner is inactive/deactivated, the system falls back to round-robin. | Inactive user triggers standard round-robin |
| 6 | The routing logic works correctly for multiple back-and-forth cycles (e.g., PSV -> QC -> PSV -> QC -> PSV -> QC). | Owner is preserved across 3+ cycles |
| 7 | Audit trail / Case History captures each ownership change with reason. | Case History shows "Returned to previous owner" notation |

### Technical Implementation Notes

| Component | Details |
|-----------|---------|
| **Custom Fields (Case)** | `Previous_PSV_Owner__c` (Lookup to User), `Previous_QC_Review_Owner__c` (Lookup to User), `Previous_App_Review_Owner__c` (Lookup to User) |
| **Flow / Apex Trigger** | Before the round-robin assignment fires, check if `Previous_[Stage]_Owner__c` is populated and the user is active. If yes, assign directly; if no, proceed with round-robin. |
| **OmniScript / Stage Transition** | On stage transition actions (e.g., "Return to PSV" button in OmniScript), stamp the current owner into the appropriate `Previous_[Stage]_Owner__c` field before transitioning. |
| **Assignment Rule Bypass** | When re-routing to a previous owner, set `DMLOptions.AssignmentRuleHeader.useDefaultRule = false` or use equivalent Flow logic to skip assignment rules. |
| **Edge Case Handling** | If previous owner is inactive → fall back to round-robin. If previous owner's queue has changed → fall back to round-robin. |

### Dependencies / Assumptions
- Existing round-robin logic is implemented via Flow or Apex (need to identify which)
- Stage transitions are managed via OmniScript or Case Status field updates
- The "Return to PSV" and "Return to QC Review" actions already exist as buttons/flow steps

### Effort Estimation
**Size: Medium (M)** — ~5-8 story points  
- Custom field creation: 0.5 day  
- Flow/Apex logic modification: 2-3 days  
- Testing (unit + integration): 1-2 days  
- UAT support: 1 day

---

## User Story 2: Route Case Button on Case Manager (QC Review Stage)

### Title
Add "Route Case" Quick Action Button to Case Manager List View for QC Review Stage

### User Story
**As a** QC Review team lead or Case Manager,  
**I want** a "Route Case" button available on the Case Manager list view when a case is in QC Review stage,  
**So that** I can quickly route the case back to PSV or App Review without having to open the case record and navigate into the QC Review details.

### Description / Background
Currently, to route a case back from QC Review to PSV or App Review, the user must open the case record, enter the QC Review section, and execute the routing action. This is inefficient when managing multiple cases. A quick-action button directly on the Case Manager list view will allow supervisors to reroute cases in bulk or individually without extra navigation.

### Acceptance Criteria

| # | Criteria | Testable Condition |
|---|----------|-------------------|
| 1 | A "Route Case" button is visible on the Case Manager list view **only** when the case is in QC Review stage. | Button hidden for cases in App Review, PSV, or other stages |
| 2 | Clicking the button opens a modal/screen flow with options: "Route to PSV" and "Route to App Review". | Modal displays exactly two routing options |
| 3 | Selecting "Route to PSV" routes the case back to the previous PSV owner (per Story #1 logic). | Case stage = PSV, Owner = previous PSV owner |
| 4 | Selecting "Route to App Review" routes the case back to the previous App Review owner (per Story #1 logic). | Case stage = App Review, Owner = previous App Review owner |
| 5 | The button respects user permissions — only users with the appropriate profile/permission set can see and use it. | Users without permission do not see the button |
| 6 | After routing, the Case Manager list view refreshes to reflect the updated stage/owner. | List view auto-refreshes or shows success toast |
| 7 | A confirmation step is shown before executing the route (e.g., "Are you sure you want to route Case #12345 to PSV?"). | Confirmation dialog appears before execution |
| 8 | The button supports single-case action (row-level action on the list). | Button appears as a row action or is accessible per-case |

### Technical Implementation Notes

| Component | Details |
|-----------|---------|
| **LWC Quick Action / Custom Button** | Create a custom LWC component (`routeCaseButton`) that renders conditionally based on `Case.Stage__c = 'QC Review'`. |
| **Screen Flow** | Build a Screen Flow (`Route_Case_From_CaseManager`) with: (1) Choice screen (Route to PSV / Route to App Review), (2) Confirmation screen, (3) Assignment logic (invoke Story #1's bypass-round-robin logic), (4) Stage update. |
| **List View Button / Row Action** | Configure as a List View Button or Lightning Action on the Case object, filtered by record type/stage. Alternatively, embed in a custom Case Manager LWC if using a custom list component. |
| **Visibility Rule** | Use Dynamic Action visibility: `Case.Stage__c EQUALS 'QC Review'` AND user has permission set `QC_Review_Route_Case`. |
| **Integration with Story #1** | Reuse the same Apex/Flow logic for owner preservation from Story #1. |

### Dependencies / Assumptions
- The Case Manager is either a standard List View or a custom LWC component (need to confirm which)
- Story #1 (preserve previous owner) should be implemented first or in parallel
- Appropriate permission sets exist or will be created

### Effort Estimation
**Size: Small-Medium (S/M)** — ~3-5 story points  
- LWC / Button creation: 1-2 days  
- Screen Flow build: 1 day  
- Visibility rules & permissions: 0.5 day  
- Testing: 1 day

---

## User Story 3: Display Specialties in Practitioner FlexCard

### Title
Show Practitioner Specialties Below Practitioner Role in the Practitioner FlexCard

### User Story
**As a** Credentialing Specialist reviewing practitioner information,  
**I want** to see the practitioner's specialties displayed directly on the Practitioner FlexCard, positioned right below the Practitioner Role,  
**So that** I can quickly identify the practitioner's areas of expertise without navigating to a separate section or record.

### Description / Background
The current Practitioner FlexCard displays the Practitioner Role but does not show the associated Specialties. Users must navigate to a related list or separate tab to view specialty information. Adding specialties directly below the role on the FlexCard improves visibility and reduces clicks during case review workflows.

### Acceptance Criteria

| # | Criteria | Testable Condition |
|---|----------|-------------------|
| 1 | Specialties are displayed on the Practitioner FlexCard directly below the "Practitioner Role" field. | Visual position is immediately below Practitioner Role |
| 2 | All active specialties associated with the practitioner are shown. | Count matches related specialty records where Status = Active |
| 3 | If a practitioner has multiple specialties, they are displayed as a comma-separated list or stacked list (per UX review). | Multiple specialties render correctly |
| 4 | If no specialties exist, the field/section is hidden (not shown as blank). | No empty label or space when specialties are null |
| 5 | The specialty data is sourced from the correct object/field (e.g., `HealthcarePractitionerFacility.Specialty__c` or `CareSpecialty` junction). | Data matches source of truth |
| 6 | The FlexCard renders correctly on both desktop and mobile (if applicable). | Responsive layout maintained |
| 7 | Performance: The additional data fetch does not add more than 200ms to FlexCard load time. | Load time delta < 200ms |

### Technical Implementation Notes

| Component | Details |
|-----------|---------|
| **FlexCard** | Modify the existing Practitioner FlexCard (identify exact FlexCard name — likely `PractitionerSummary` or `PractitionerDetail`). |
| **DataRaptor / Integration Procedure** | Update the existing DataRaptor (Extract) or Integration Procedure that feeds the FlexCard to include specialty data. Add a child extract or SOQL join to pull `CareSpecialty` or equivalent records. |
| **FlexCard Layout** | Add a new text/field node below the Practitioner Role node. Use conditional rendering (`{Specialties} != null`) to hide when empty. |
| **Data Source** | Likely from `HealthcarePractitionerFacilitySpecialty` or `PractitionerRole.specialty` (Health Cloud standard object). Confirm the data model. |
| **Styling** | Use standard SLDS text styling, slightly smaller font or muted color to differentiate from Role. Label: "Specialties" or no label (just values). |

### Dependencies / Assumptions
- Specialty data is already captured on practitioner records (no new data entry required)
- The Practitioner FlexCard and its backing DataRaptor/IP already exist
- UX team confirms display format (comma-separated vs. stacked list)

### Effort Estimation
**Size: Small (S)** — ~2-3 story points  
- DataRaptor/IP update: 0.5 day  
- FlexCard modification: 0.5 day  
- Testing & styling: 0.5 day

---

## User Story 4: Add "Duplicate Case" and "Off-cycle" Options to Close Case Denial Flow

### Title
Add "Duplicate Case" and "Off-cycle" Denial Reasons to the Close Case Denial Flow Dropdown

### User Story
**As a** Credentialing Specialist closing a case with a denial,  
**I want** "Duplicate Case" and "Off-cycle" available as options in the denial reason dropdown within the Close Case Denial flow,  
**So that** I can accurately categorize the denial reason and ensure proper reporting and tracking of these common denial scenarios.

### Description / Background
The Close Case Denial flow currently has a dropdown for selecting the denial reason, but it lacks two commonly-needed options: "Duplicate Case" (when a case was opened in error as a duplicate of an existing case) and "Off-cycle" (when a case is denied because it falls outside the normal credentialing cycle). Adding these options will reduce the use of "Other" with free-text explanations and improve reporting accuracy.

### Acceptance Criteria

| # | Criteria | Testable Condition |
|---|----------|-------------------|
| 1 | "Duplicate Case" appears as a selectable option in the denial reason dropdown. | Option is visible and selectable in the dropdown |
| 2 | "Off-cycle" appears as a selectable option in the denial reason dropdown. | Option is visible and selectable in the dropdown |
| 3 | Both new options are positioned alphabetically (or per business-specified order) within the existing dropdown list. | Order matches specification |
| 4 | Selecting "Duplicate Case" correctly saves the value to the denial reason field on the Case record. | `Case.Denial_Reason__c` = "Duplicate Case" after save |
| 5 | Selecting "Off-cycle" correctly saves the value to the denial reason field on the Case record. | `Case.Denial_Reason__c` = "Off-cycle" after save |
| 6 | Existing denial reasons continue to work as before (no regression). | All existing options remain functional |
| 7 | Reports/Dashboards that reference denial reasons correctly include the new values. | Report filters can select new values; existing reports not broken |
| 8 | Any downstream automation (e.g., notifications, status updates) triggered by denial reason handles the new values appropriately. | No errors or unexpected behavior with new values |

### Technical Implementation Notes

| Component | Details |
|-----------|---------|
| **Picklist / Value Set** | Add "Duplicate Case" and "Off-cycle" to the `Denial_Reason__c` picklist field (or Global Value Set if shared). Check if it's a dependent picklist. |
| **OmniScript / Flow** | Update the Close Case Denial OmniScript (or Screen Flow) dropdown component to include the new values. If the dropdown is dynamically sourced from the picklist metadata, no OmniScript change needed — just the picklist update. If hardcoded, update the option list. |
| **DataRaptor** | If the dropdown values are fed via DataRaptor, update the DataRaptor to include new values. |
| **Validation Rules** | Review any validation rules on `Denial_Reason__c` to ensure new values are accepted. |
| **Reports** | Verify existing report filters and groupings accommodate new values without manual intervention. |

### Dependencies / Assumptions
- The Close Case Denial flow already exists (OmniScript or Screen Flow)
- The denial reason field is a picklist (not free text)
- No approval process or workflow is gated on specific denial reason values that would conflict
- Business confirms exact label text: "Duplicate Case" and "Off-cycle" (with hyphen)

### Effort Estimation
**Size: Extra Small (XS)** — ~1-2 story points  
- Picklist value addition: 0.5 day  
- OmniScript/Flow update (if needed): 0.5 day  
- Testing & validation: 0.5 day

---

## Summary Table

| Story # | Title | Size | Points | Priority |
|---------|-------|------|--------|----------|
| 1 | ReRoute Case to Original Stage Owner | M | 5-8 | High |
| 2 | Route Case Button on Case Manager | S/M | 3-5 | High |
| 3 | Show Specialties in Practitioner FlexCard | S | 2-3 | Medium |
| 4 | Close Case Denial - Add Duplicate Case & Off-cycle | XS | 1-2 | Medium |

**Total Estimated Effort: 11-18 story points**
