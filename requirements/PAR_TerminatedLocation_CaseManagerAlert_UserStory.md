# PAR Terminated Practice Location Alert — Case Manager Record Page
## Tactical Shortcut: Option 1 — LWC Alert Component on IndividualApplication Page

Document Version: 1.1 — Query approach updated: PRM_EffectiveTo__c as termination signal, all HCPF rows fetched and flagged in component
Created Date: April 29, 2026
Story Type: Tactical / Quick Win
Epic: PAR Case Manager Association via CMA Object
Complements: PAR_CaseManager_Association_CMA_Redesign_User_Stories.md (long-term fix US6-US12)
Priority: P0 — Production Blocker Mitigation
Estimated Effort: S (2-3 days end-to-end)

---

## Why This Story Exists

The full CMA redesign (US6-US12) is the permanent architectural fix, but it spans multiple
sprints. In the meantime, Credentialing Specialists are walking into App Review flows for
practitioners whose practice locations have been terminated via PDM or Provider Change. The
review fails at the submit step with a "Required Fields Missing" error — with no warning
beforehand.

This story delivers one targeted change: a visible alert on the IndividualApplication
(Case Manager) record page that fires BEFORE the specialist ever opens a review flow.
No OmniScript changes. No DataRaptor rewiring. No CMA. Just a query on load.

---

## How the Detection Works (No CMA Needed)

### Query anchor: PractitionerId

HealthcarePractitionerFacility.PractitionerId is never overwritten by PDM or Provider
Change. Even when HCPF.PRM_CaseManager__c gets stamped with a PDM case manager ID,
PractitionerId stays accurate.

PractitionerId is available on the IndividualApplication page as:
  IndividualApplication.AccountId = PractitionerId (confirmed: PRMExtractCaseDetails
  maps Case:AccountId → PractitionerId for all downstream review flows)

### Termination signal: HealthcareFacility.PRM_EffectiveTo__c != null

Earlier approaches using PRM_Pending__c = true as the scope filter had a gap: when PDM
terminates an in-flight practice location, it sets HealthcareFacility.PRM_EffectiveTo__c
to the termination date (confirmed in PRM_AccountTerminationBatchHelper.cls line 88,
PRM_AccountTermInitalCredService.cls line 96, PRM_PracLocTermHelper.cls). However,
PRM_Pending__c is only set to false by PRM_PractitionerActivationBatchHelper.cls — which
runs on PAR APPROVAL, not on termination. This means that for an in-flight PAR whose
location gets terminated, PRM_Pending__c remains true while the facility is already gone.

Using PRM_Pending__c = true alone as the in-flight scope causes a false-positive risk:
an old denied/abandoned PAR for the same practitioner that was never activated also has
PRM_Pending__c = true on its HCPF — and if that facility was later terminated, it would
incorrectly trigger the alert for a completely different case.

The reliable, unambiguous termination signal is HealthcareFacility.PRM_EffectiveTo__c:
  - Stamped ONLY by intentional, formal termination flows (PDM, Provider Change, Account Term)
  - Error records get PRM_IsErrorRecord__c = true with PRM_EffectiveTo__c = NULL — not flagged
  - Future-dated terminations have PRM_EffectiveTo__c set but PRM_Active__c still true — guarded
  - Normal active locations: PRM_EffectiveTo__c = null — not flagged
  - Once stamped, it survives PDM CaseManager overwrite completely unaffected

### Query: fetch ALL HCPF rows for the practitioner, flag in component logic

The DR fetches ALL HealthcarePractitionerFacility records for the practitioner
(scoped to PAR RecordType). The component then splits them into two groups:

  TerminatedLocations: where HealthcareFacility.PRM_EffectiveTo__c != null
                       AND HealthcareFacility.PRM_Active__c = false
  ActiveLocations:     all others

De-duplication by HealthcareFacilityId is applied before rendering to ensure the same
physical facility does not appear twice (a facility can have multiple HCPF records from
different PAR cycles — we show the facility once, not once per HCPF record).

  SELECT HealthcareFacilityId,
         HealthcareFacility.Name,
         HealthcareFacility.PRM_Active__c,
         HealthcareFacility.PRM_EffectiveTo__c,
         HealthcareFacility.BillingStreet,
         HealthcareFacility.BillingCity,
         HealthcareFacility.BillingState,
         HealthcareFacility.BillingPostalCode,
         Account.Name,
         PRM_Pending__c,
         IsActive,
         Id
  FROM HealthcarePractitionerFacility
  WHERE PractitionerId = :PractitionerId
  AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'

Component flags a row as Terminated when:
  HealthcareFacility.PRM_EffectiveTo__c != null
  AND HealthcareFacility.PRM_Active__c = false

Why this approach:
  - PRM_EffectiveTo__c is stamped by all formal termination paths (PDM, Provider Change, Account Term)
  - It is NOT stamped on error records (those get PRM_IsErrorRecord__c = true, EffectiveTo = NULL)
  - It correctly covers PDM-overwritten HCPF records because it lives on HealthcareFacility, not HCPF
  - Future-dated terminations (EffectiveTo stamped but PRM_Active__c still true) are excluded
  - De-duplication by HealthcareFacilityId eliminates cross-PAR-cycle noise
  - No dependency on PRM_CaseManager__c (overwritten by PDM) or PRM_Pending__c (only cleared on activation)

---

## USER STORY: Terminated Practice Location Alert on Case Manager Record Page

Story Number: US-ALERT-01
Priority: P0
Persona: Credentialing Specialist
Component Type: LWC (new) + DataRaptor Extract (new) + Record Page configuration
Placement: IndividualApplication (Case Manager) record page — top of page, above highlights panel
Depends On: None
Blocks: Nothing (standalone — does not affect any existing component)
Sprint: Sprint 1 (before full CMA redesign)

---

### Story

As a Credentialing Specialist viewing an IndividualApplication (Case Manager) record,
I want to see all practice locations associated with this practitioner displayed at
the top of the page — with any formally terminated locations (HealthcareFacility.PRM_EffectiveTo__c
stamped and PRM_Active__c = false) clearly flagged —
So that I am immediately aware of terminated locations before I open any review flow
(App Review, PSV, QC, PDA, or Network Management QC) and can take corrective action
rather than hitting a cryptic "Required Fields Missing" error mid-review.

---

### Scope of Changes

Component                                 | Type            | Change
------------------------------------------|-----------------|-----------------------------------------------
PRMDREPractitionerLocationsAlert          | DataRaptor Extract (new) | Fetches ALL HCPF records for PractitionerId scoped to RecordType = PRM_PractitionerLocationAffiliation. Returns full set including HealthcareFacility.PRM_EffectiveTo__c and PRM_Active__c. Component logic performs terminated/active split.
prmTerminatedLocationAlert                | LWC (new)       | Alert component on IndividualApplication page. On load: reads AccountId, calls DR, splits results into TerminatedLocations (PRM_EffectiveTo__c != null AND PRM_Active__c = false) and ActiveLocations, de-duplicates by HealthcareFacilityId, renders alert header if any terminated, renders nothing if none.
PRM_CaseManagerRecordPage.flexipage-meta.xml | Page layout - update | Add prmTerminatedLocationAlert to the top region of the IndividualApplication record page, ABOVE force:highlightsPanel

---

### New DataRaptor: PRMDREPractitionerLocationsAlert

Type: DataRaptor Extract
API Name: PRMDREPractitionerLocationsAlert
Version: 1

Purpose: Fetch ALL HealthcarePractitionerFacility records for a given practitioner
scoped to the PAR practice location RecordType. Returns the full set including termination
fields. The component performs the terminated/active split in JavaScript — this keeps the
DR simple and reusable, and avoids needing DataRaptor formula support for null checks.

Input:
  Key: PractitionerId
  Type: String
  Source: Passed from LWC on load (IndividualApplication.AccountId)

Base Object: HealthcarePractitionerFacility

Filter Group 0 (AND logic):
  Field: PractitionerId
  Operator: =
  Value: :PractitionerId (input variable)

  Field: RecordType.DeveloperName
  Operator: =
  Value: 'PRM_PractitionerLocationAffiliation'

  Note: No PRM_Pending__c filter. No PRM_Active__c filter.
  All HCPF rows for the practitioner (this RecordType) are returned.
  The component applies the terminated/active classification.

Output Fields (mapped to output node "Locations"):

  Input Field                                    | Output Node Path
  ------------------------------------------------|-------------------------------------------
  HealthcarePractitionerFacility:Id              | Locations:HCPFId
  HealthcareFacilityId                           | Locations:FacilityId
  HealthcareFacility.Name                        | Locations:FacilityName
  HealthcareFacility.PRM_Active__c               | Locations:FacilityActive
  HealthcareFacility.PRM_EffectiveTo__c          | Locations:FacilityEffectiveTo
  HealthcareFacility.BillingStreet               | Locations:Street
  HealthcareFacility.BillingCity                 | Locations:City
  HealthcareFacility.BillingState                | Locations:State
  HealthcareFacility.BillingPostalCode           | Locations:Zip
  Account.Name                                   | Locations:GroupName
  PRM_Pending__c                                 | Locations:HCPFPending
  IsActive                                       | Locations:HCPFIsActive
  PRM_CaseManager__c                             | Locations:CaseManagerId

No formula outputs — all classification logic handled in the LWC component.

Note on existing DR: PRMDRGetLocationTerminationData exists in the codebase but is
scoped to a different flow context. Build PRMDREPractitionerLocationsAlert as a clean,
purpose-built DR. Do not retrofit the existing one.

---

### New LWC: prmTerminatedLocationAlert

File Location: force-app/main/default/lwc/prmTerminatedLocationAlert/

Files to create:
  prmTerminatedLocationAlert.js
  prmTerminatedLocationAlert.html
  prmTerminatedLocationAlert.css
  prmTerminatedLocationAlert.js-meta.xml

Target: lightning__RecordPage → IndividualApplication object
Exposed: true
Label: "PRM Terminated Location Alert"
API Version: 62.0

#### Component Behavior

On load:
  1. Wire to IndividualApplication record, read AccountId
  2. If AccountId is null: render nothing (edge case — draft records)
  3. Call PRMDREPractitionerLocationsAlert imperatively with PractitionerId = AccountId
  4. On DR response — classify each row:
       Terminated = FacilityEffectiveTo != null AND FacilityActive == false
       Active     = all other rows
  5. De-duplicate by FacilityId: if multiple HCPF rows reference the same HealthcareFacilityId,
       keep only one entry per facility (use the most recent: prefer row where HCPFPending = true
       if both terminated and active rows exist for the same facility — that is the current PAR record)
  6. If TerminatedLocations.length === 0: render nothing (zero DOM footprint)
  7. If TerminatedLocations.length >= 1: render the alert panel (see UI spec below)
  8. If DR call throws error: render neutral fallback bar (do NOT block the page)

Loading state: small spinner with "Checking practice locations..."
  Timeout: if DR takes > 5 seconds, hide spinner and render neutral fallback.

#### prmTerminatedLocationAlert.js-meta.xml

<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
  <apiVersion>62.0</apiVersion>
  <isExposed>true</isExposed>
  <masterLabel>PRM Terminated Location Alert</masterLabel>
  <description>
    Displays an alert banner on the Case Manager (IndividualApplication) record page
    when one or more practice locations for this practitioner have been formally terminated
    (HealthcareFacility.PRM_EffectiveTo__c != null AND PRM_Active__c = false).
    Fetches all HealthcarePractitionerFacility records by PractitionerId (AccountId),
    classifies and de-duplicates in component logic. Zero visual footprint when no
    terminated locations exist.
  </description>
  <targets>
    <target>lightning__RecordPage</target>
  </targets>
  <targetConfigs>
    <targetConfig targets="lightning__RecordPage">
      <objects>
        <object>IndividualApplication</object>
      </objects>
    </targetConfig>
  </targetConfigs>
</LightningComponentBundle>

---

### UI Specification

#### State 1: No Terminated Locations (default / happy path)

Render: NOTHING — zero DOM output.
The component must have zero visual footprint when there is no alert to show.
Do not show a "No terminated locations found" message. Absence of the alert IS the confirmation.

---

#### State 2: One or More Terminated Locations (alert state)

Visual treatment: Full-width alert banner, SLDS theme "error" severity (red left border,
error icon). Positioned at the very top of the record page content area, above the
highlights panel.

```
┌────────────────────────────────────────────────────────────────────┐
│ ⛔  Terminated Practice Location(s) — Review Required              │
│                                                                    │
│ One (or more) practice locations on this application have been     │
│ terminated. Opening any review flow (App Review, PSV, QC, PDA)    │
│ will fail at the submit step. Please take action before proceeding.│
│                                                                    │
│ ┌─────────────────────────────────────┬──────────────────────────┐ │
│ │ Practice Location                   │ Termination Date         │ │
│ ├─────────────────────────────────────┼──────────────────────────┤ │
│ │ Regional Women's Health Group LLC   │ 12/15/2025               │ │
│ │ 247 Hurffville Crosskeys Rd Ste C3  │                          │ │
│ │ Sewell, NJ 08080                    │                          │ │
│ │ Group: Regional Women's Health LLC  │                          │ │
│ ├─────────────────────────────────────┼──────────────────────────┤ │
│ │ (additional rows if multiple)       │ (date)                   │ │
│ └─────────────────────────────────────┴──────────────────────────┘ │
│                                                                    │
│ Contact your credentialing supervisor to update or close this case.│
└────────────────────────────────────────────────────────────────────┘
```

Exact message text:

  HEADER (h3, bold):
    "⛔ Terminated Practice Location(s) — Review Required"

  BODY paragraph 1:
    Singular (1 location):
      "1 practice location on this application has been terminated via a
      Provider Change Request. Opening any review flow (App Review, PSV, QC,
      PDA Review) will result in an error at the submit step. Please take
      action before proceeding with the review."

    Plural (2+ locations):
      "{N} practice locations on this application have been terminated via
      Provider Change Requests. Opening any review flow (App Review, PSV,
      QC, PDA Review) will result in an error at the submit step. Please
      take action before proceeding with the review."

  TABLE heading row:
    Column 1: "Practice Location"
    Column 2: "Termination Date"

  TABLE per row (one per terminated HCPF result):
    Column 1 (stacked):
      Line 1: {FacilityName} (bold)
      Line 2: {Street}
      Line 3: {City}, {State} {Zip}
      Line 4: Group: {GroupName}  (show only if GroupName is not blank)
    Column 2:
      {TerminationDate} formatted as MM/DD/YYYY
      If TerminationDate is null: "Date Not Recorded"

  FOOTER paragraph (italic, grey):
    "Contact your credentialing supervisor to determine the correct action:
    update the practice location selection or close this case."

---

#### State 3: DR Error / Timeout Fallback

Render: Neutral grey informational bar (NOT a red error — do not alarm user).

Text:
  "⚠ Unable to verify practice location status at this time.
   Please check manually before opening a review flow."

This state must never crash or freeze the record page.

---

### Record Page Configuration

File: force-app/main/default/flexipages/PRM_CaseManagerRecordPage.flexipage-meta.xml

Current top region of the IndividualApplication page (in order):
  1. force:highlightsPanel
  2. runtime_sales_pathassistant:pathAssistant
  3. prmBatchRecordException

Updated order:
  1. prmTerminatedLocationAlert   ← NEW — add before highlightsPanel
  2. force:highlightsPanel
  3. runtime_sales_pathassistant:pathAssistant
  4. prmBatchRecordException

Rationale for ordering: The alert must be the first thing a specialist sees when
opening the record. Placing it above the highlights panel and path assistant ensures
it cannot be missed, even on smaller screens.

Page config change (add this componentInstance block to the top region):

  <componentInstance>
    <componentName>prmTerminatedLocationAlert</componentName>
  </componentInstance>

No componentInstanceProperties needed — the component reads recordId from the
standard lightning__RecordPage context.

---

### Acceptance Criteria

---

Scenario 1 — Happy path: no formally terminated locations, no alert rendered

Given an IndividualApplication where all HCPF records linked to PractitionerId
have HealthcareFacility.PRM_EffectiveTo__c = null (no formal termination stamped),
When the Credentialing Specialist opens the Case Manager record page,
Then PRMDREPractitionerLocationsAlert returns rows but none satisfy the terminated
  condition (EffectiveTo != null AND FacilityActive = false),
AND the prmTerminatedLocationAlert component renders NOTHING on the page,
AND the page layout is unchanged from its current state (no regression).

---

Scenario 2 — Single terminated location: alert renders correctly

Given an IndividualApplication where 1 HCPF record has:
  HealthcareFacility.PRM_EffectiveTo__c = 12/15/2025 (formally terminated)
  AND HealthcareFacility.PRM_Active__c = false
  AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  (regardless of HCPF.PRM_Pending__c value or HCPF.PRM_CaseManager__c value),
When the Credentialing Specialist opens the Case Manager record page,
Then the component classifies this HCPF as Terminated,
AND the red alert banner renders at the TOP of the page above the highlights panel,
AND the header reads: "⛔ Terminated Practice Location(s) — Review Required",
AND the body reads the singular variant: "1 practice location for this practitioner
  has been formally terminated. Opening any review flow may result in an error.",
AND the table shows 1 row with:
  Practice Location Name (bold)
  Street address
  City, State Zip
  Termination Date: 12/15/2025 (MM/DD/YYYY format)
AND the footer advisory message is displayed.

---

Scenario 3 — Multiple terminated locations: all shown, plural message, de-duplicated

Given a practitioner has 3 HCPF records:
  HCPF-A: FacilityId = F1, PRM_EffectiveTo__c = 12/15/2025, PRM_Active__c = false (terminated)
  HCPF-B: FacilityId = F2, PRM_EffectiveTo__c = 10/01/2025, PRM_Active__c = false (terminated)
  HCPF-C: FacilityId = F1, PRM_EffectiveTo__c = null, PRM_Active__c = true (same facility F1, different PAR cycle)
When the Credentialing Specialist opens the Case Manager record page,
Then the component de-duplicates by FacilityId: F1 appears once (not twice),
AND the plural variant renders: "2 practice locations for this practitioner have
  been formally terminated.",
AND the table shows 2 rows (one for F1, one for F2),
AND HCPF-C (active, same FacilityId as HCPF-A) does not appear as a terminated row.

---

Scenario 4 — Regression: production case IA-0000096229 scenario

Given IndividualApplication IA-0000096229 linked to the practitioner whose
HCPF for Regional Women's Health Group LLC (247 Hurffville Crosskeys Rd Ste C3-8017)
has HealthcareFacility.PRM_EffectiveTo__c = [termination date stamped by PDM/Provider Change]
AND HealthcareFacility.PRM_Active__c = false
(regardless of the current value of HCPF.PRM_CaseManager__c — which may have been
overwritten by the PDM termination to IA-0000093618),
When the Credentialing Specialist opens the Case Manager record for IA-0000096229,
Then the component classifies the location as Terminated via the EffectiveTo signal,
AND the alert banner fires immediately on page load,
AND the table row shows:
  Practice Location: Regional Women's Health Group LLC
  Address: 247 Hurffville Crosskeys Rd Ste C3-8017, Sewell, NJ 08080
  Termination Date: [actual PRM_EffectiveTo__c from the HealthcareFacility record]
AND the specialist knows NOT to proceed into App Review without resolving the location.

---

Scenario 5 — DR call timeout or error: fallback renders, page does not crash

Given the DataRaptor call fails (network error, governor limit, or timeout > 5s),
When the Credentialing Specialist opens the Case Manager record page,
Then the component renders the neutral fallback bar:
  "⚠ Unable to verify practice location status at this time.
   Please check manually before opening a review flow."
AND the rest of the record page (highlights panel, path assistant, related lists)
  loads and functions normally,
AND no JavaScript error is thrown to the user.

---

Scenario 6 — Terminated location IS shown even on a previously activated HCPF

Given a practitioner has a previously completed and activated PAR case
  where the HCPF has PRM_Pending__c = false (activation set this)
  AND HealthcareFacility.PRM_EffectiveTo__c was later stamped by PDM termination
  AND HealthcareFacility.PRM_Active__c = false,
When the Credentialing Specialist opens a NEW IndividualApplication for the same
  practitioner that includes the same now-terminated facility,
Then the terminated location IS shown in the alert
  (PRM_EffectiveTo__c is the signal — PRM_Pending__c is irrelevant to the detection),
AND the specialist is correctly warned that this facility is no longer active.

  Rationale: A practitioner may have been activated at a location, the location was
  later terminated, and a new re-credentialing or re-application PAR now includes
  that same location. The specialist must see the termination warning regardless of
  whether the prior HCPF was in pending or activated state.

---

Scenario 7 — RecordType guard: non-PAR HCPF records do NOT trigger the alert

Given a practitioner has HCPF records of RecordType = 'PRM_AdmittingPrivileges'
  (hospital admitting privileges, not a practice location affiliation),
When those records have HealthcareFacility.PRM_Active__c = false,
Then those records do NOT appear in the alert
  (filtered by RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'),
AND only true practice location affiliation records trigger the alert.

---

Scenario 8 — Future-dated termination: NOT flagged as terminated yet

Given a HCPF where HealthcareFacility.PRM_EffectiveTo__c is set to a FUTURE date
  (termination is scheduled but not yet effective)
  AND HealthcareFacility.PRM_Active__c = true (still currently active),
When the Credentialing Specialist opens the Case Manager page,
Then this HCPF does NOT appear in the terminated list
  (PRM_Active__c = true fails the terminated condition),
AND the location is shown as active (or not shown if we only render the alert section),
AND the alert does not fire for future-dated scheduled terminations.

  Rationale: PRM_Active__c is the operational active status. A future-dated termination
  is a planned event, not a current blocker. The guard PRM_Active__c = false ensures
  only currently-inactive terminated locations trigger the alert.

---

Scenario 9 — Error records: NOT flagged as terminated

Given a HCPF where PRM_IsErrorRecord__c = true
  AND HealthcareFacility.PRM_EffectiveTo__c = null (error records have EffectiveTo nulled)
  AND HealthcareFacility.PRM_Active__c = false,
When the Credentialing Specialist opens the Case Manager page,
Then this HCPF does NOT appear in the terminated list
  (EffectiveTo = null fails the terminated condition),
AND error records are correctly excluded from the alert.

  Rationale: Confirmed in PRM_PracLocTermHelper.cls — error records
  (PRM_IsErrorRecord__c = true) have their EffectiveTo set to NULL explicitly.
  Our EffectiveTo != null guard cleanly separates intentional terminations from errors.

---

### Test Plan

Unit Tests (Jest — prmTerminatedLocationAlert.test.js):

  Test 1: renders nothing when DR returns rows but none are terminated
    Mock DR return: [{ FacilityEffectiveTo: null, FacilityActive: true, ... }]
    Assert: no DOM nodes rendered with class prm-terminated-alert

  Test 2: renders alert when 1 row has EffectiveTo stamped and FacilityActive = false
    Mock DR return: [{ FacilityEffectiveTo: '2025-12-15', FacilityActive: false, ... }]
    Assert: alert banner rendered, 1 table row, singular message

  Test 3: de-duplication: 2 HCPF rows same FacilityId → 1 alert row
    Mock DR return: 2 rows with same FacilityId, both terminated
    Assert: table shows 1 row only (de-duplicated by FacilityId)

  Test 4: future-dated termination (EffectiveTo set, FacilityActive = true) → no alert
    Mock DR return: [{ FacilityEffectiveTo: '2027-01-01', FacilityActive: true, ... }]
    Assert: no alert rendered (FacilityActive = true excludes it)

  Test 5: error record (EffectiveTo = null, FacilityActive = false) → no alert
    Mock DR return: [{ FacilityEffectiveTo: null, FacilityActive: false, ... }]
    Assert: no alert (EffectiveTo = null excludes it)

  Test 6: plural message when 2 distinct terminated facilities
    Mock DR return: 2 rows, different FacilityId, both terminated
    Assert: body text contains "2 practice locations", table has 2 rows

  Test 7: fallback bar on DR error
    Mock: DR call rejects with Error("Network error")
    Assert: fallback bar rendered, no error thrown

  Test 8: renders nothing when AccountId is null
    Mock: wire returns IndividualApplication with AccountId = null
    Assert: no DOM output, no DR called

DataRaptor Integration Test (sandbox):
  Run PRMDREPractitionerLocationsAlert with:
    - PractitionerId of a practitioner with a known terminated HCPF
      (HealthcareFacility.PRM_EffectiveTo__c stamped, PRM_Active__c = false)
    - Verify Locations array returned with FacilityEffectiveTo populated
    - Verify component classifies it as Terminated
    - PractitionerId of a practitioner with no terminated HCPF
    - Verify all rows have FacilityEffectiveTo = null → component renders nothing

Manual Regression (sandbox):
  - Open IndividualApplication record for a case with no terminated locations → confirm no alert
  - Open IndividualApplication record for IA-0000096229 equivalent → confirm alert fires
  - Verify highlights panel, path assistant, related lists all load normally (no visual regression)
  - Test on mobile layout (if used by specialists)

---

### Estimated Effort

Component                                      | Effort | Notes
-----------------------------------------------|--------|----------------------------------------------
PRMDREPractitionerLocationsAlert (new DR)      | XS     | Simple extract; 2-field filter group; 13 output fields; no formula outputs needed
prmTerminatedLocationAlert LWC (new)           | S      | Wire + imperative call + terminated/active split in JS + de-dup by FacilityId + 3 render states + SLDS styling
PRM_CaseManagerRecordPage flexipage update     | XS     | Add 1 componentInstance to top region
Unit tests                                     | S      | 8 Jest scenarios including de-dup, future-dated, error record edge cases
Sandbox integration testing + regression       | S      | DR test + manual record page test with known terminated facility
TOTAL                                          | S      | 2-3 days end-to-end

---

## Relationship to the Long-Term Fix (US6-US12)

This story is a DETECTION-ONLY shortcut. It does NOT fix the underlying failure.
If a specialist ignores the alert and opens App Review anyway, the "Required Fields
Missing" error will still occur at submit (until US7 + US8 are delivered).

This story:
  ✓ Gives specialists immediate visibility on the Case Manager page
  ✓ Works for all review types (App Review, PSV, QC, PDA, NMQC) equally — informational
  ✓ Requires zero changes to OmniScripts, Integration Procedures, or DataRaptors
  ✓ Zero risk to existing review flows (no shared components touched)
  ✓ Deployable independently in 1 sprint

This story does NOT:
  ✗ Fix the HCPF resolution inside review flows (that is US7)
  ✗ Add action buttons (Close Case, Update Locations) — those are in US8
  ✗ Create CMA records (that is US6)
  ✗ Remove the risk of the error if specialist bypasses the alert

Sprint plan recommendation:
  Sprint 1: US-ALERT-01 (this story) + US5 (daily script guard) — stop the bleeding
  Sprint 2: US6 + US7 — foundation CMA work
  Sprint 3: US8 + US9 + US10 — in-flow hard blocks replace this alert

Once US8 is live (in-flow hard block on App Review Step 1), this alert component
becomes a complementary early-warning system rather than the sole protection.

---

## Optional Enhancement: Also Add to Case Record Page

The Case record page (PRM_CaseRecordPage.flexipage-meta.xml) is where specialists
often start. The same prmTerminatedLocationAlert component can be added to that page too.

For the Case record page, the component would use Case.AccountId as the PractitionerId
(same field, different parent object). The LWC already reads recordId from context —
add a property to accept the object type so it can resolve AccountId from either
IndividualApplication or Case.

Effort delta: XS (add targetConfig entry for Case object + conditional field API name).
Recommended: include in Sprint 1 scope if the team uses the Case page as their
primary workspace.

---

End of Document
Story: US-ALERT-01
Created: April 29, 2026
