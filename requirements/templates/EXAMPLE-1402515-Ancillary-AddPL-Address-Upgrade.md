# Story Design & Technical Kickoff — FILLED EXAMPLE

---

> **This is a completed example** of the IBXQA Pre-Development Story Analysis Template, filled out for Work Item #1402515. Use this as a reference when completing the template for your own stories.

---

| Field | Value |
|-------|-------|
| **Work Item ID** | 1402515 |
| **Story Title** | Ancillary Reassessment - Add / Edit Practice Locations And Business License – Physical, Mailing, and Billing Address |
| **Category** | Ancillary Reassessment |
| **Sprint** | Sprint 53 |
| **Developer** | Kothapalli, Prashanth |
| **Date Completed** | 2026-05-24 |
| **Tech Lead Reviewer** | _[Tech Lead Name]_ |
| **Tags** | Ancillary; BX; Go Live; NFD; npdb; NR; SP1 Candidate |
| **Status** | `Draft` |

---

## 1. Impacted Objects & Components

### 1.1 Salesforce Objects (Data Model)

| Object API Name | Nature of Impact | Fields Added/Modified | Record Types Affected |
|----------------|-----------------|----------------------|----------------------|
| `Address` (standard) | Queried (ExistingAddresses extract) + Upserted (Primary/Mailing/Billing save) | None — existing fields used (AddressLine1, City, State, PostalCode, AddressType) | N/A |
| `PRM_CaseManagerAssociation__c` | Status update on routing | `Status__c` picklist (existing values used) | Ancillary |
| `Case` | Status update per ProceedTo routing | `Status` (existing values: In Progress, Closed, Pending Provider Outreach) | PRM Ancillary |
| `ContentNote` | New record created (Review Note) | N/A — new record, not field change | N/A |
| `PRM_HealthcareFacility__c` | Read only — primary PL lookup | None | N/A |
| `BusinessLicense` (standard) | Created (existing behavior preserved) | None | N/A |
| `PRM_AdverseActionLog__c` | Created (existing behavior preserved) | None | N/A |

### 1.2 OmniStudio Components

| Component Type | Component Name | Version | Change Description |
|---------------|---------------|---------|-------------------|
| **OmniScript** | `PRM_AddAncillaryPLAndBusinessLicense_English` | v2 → **v3** | Major restructure: Remove type-ahead + NewPL repeat; Add PrimaryAddress block (editable), MailingAddressChange/BillingAddressChange radios, ReviewScreen step, ProceedTo radio, SetCaseManagerAndCase, conditional NPDBReportRequest |
| **OmniScript (NEW)** | `PRM_RouteCase_English` | **v1 (new)** | New standalone OmniScript for "Route Case" button — ProceedTo radio + Note + IP call |
| **Integration Procedure** | `PRM_AncillaryAddPLAndLicenseCreation_English` | v2 → **v3** | Add 3 DataRaptor Post Action steps (PRMLoadAddressPrimary, PRMLoadAddressAncesMailing, PRMLoadAddressAncesBilling) before existing CreateBusinessLicenses step; add Case status update + ContentNote creation per ProceedTo; adapt for single-PL input structure |
| **Integration Procedure** | `PRM_AncillaryAddPLAndLicenseCreationParent_English` | v1 | Update extraPayload mapping to pass new address fields + ProceedTo |
| **Integration Procedure** | `PRM_FetchAncillaryReassessmentPSV_Procedure` (reference) | v4 | **No change** — reference only for ExistingAddresses pattern |
| **DataRaptor (Reuse)** | `PRMLoadAddressPrimary` | v1 | **No change** — reuse as-is (same inputs as Ancillary Reassessment) |
| **DataRaptor (Reuse)** | `PRMLoadAddressAncesMailing` | v1 | **No change** — reuse as-is |
| **DataRaptor (NEW)** | `PRMLoadAddressAncesBilling` | **v1 (new)** | Create — mirror PRMLoadAddressAncesMailing but for Billing address type; map ExistingBillingAddr, BillingAddressNew |
| **DataRaptor (Modify)** | FetchDetails DR (within parent IP) | — | Enhance to return ExistingAddresses array [{AddType:"Primary",...}, {AddType:"Mailing",...}, {AddType:"Billing",...}] for the primary PL |

### 1.3 Apex Classes & Triggers

| Class/Trigger Name | Type | Change Description |
|-------------------|------|-------------------|
| `PRM_AncillaryReAssessmentPSVService.cls` | Service (reference) | **No change** — reference for routing logic pattern |
| None (new Apex) | — | No new Apex classes required for this story — all logic handled via OmniStudio (IP/DR/OS) |

> **Note:** This story is entirely OmniStudio-based. No Apex code changes needed. If performance issues arise during testing with large address sets, a future story may move routing logic to Apex.

### 1.4 Lightning Web Components (LWC)

| Component Name | Change Description | Parent/Consumer |
|---------------|-------------------|-----------------|
| None | No LWC changes — OmniScript handles all UI | — |

> **Note:** The "Route Case" button on the Case Manager page will use a standard Lightning Action launching the new `PRM_RouteCase_English` OmniScript — no custom LWC needed.

### 1.5 Flows & Automation

| Flow/Automation Name | Type | Change |
|--------------------|------|--------|
| `PRM_CaseManagerClosureFlow` | Record-Triggered Flow | **Verify not broken** — confirm flow doesn't interfere when Case status = "Closed" from ProceedTo = HACAC routing |
| `PRM_SendBellNotificationtoCaseManagerRequester` | Flow | **Verify** — notification should still fire on Case status change |

### 1.6 External Integrations

| Integration | Direction | Impact |
|------------|-----------|--------|
| Precisely Address API | Outbound callout | **Phase 2 (deferred)** — Optional address validation before save. Not in this sprint. |
| NPDB | Outbound | **Conditional** — NPDB request only fires when ProceedTo = "Pending NPDB Verification". No contract change. |
| CAQH Roster API | N/A | No impact |
| BCBSA Sync | N/A | No impact — address records not in BCBSA sync scope |
| SendGrid | N/A | No impact |
| Mulesoft | N/A | No impact |

### 1.7 Permission Sets & Security

| Permission Set | Change |
|---------------|--------|
| `PRM_AncillaryCredSpecialist` | Verify has access to Address object fields (should already exist) |
| `PRM_CredentialingUser` | Verify can execute new `PRM_RouteCase_English` OmniScript |
| `PRM_OmniStudioPermission` | Verify includes new OmniScript execution |
| Lightning Page (Case Manager) | Add "Route Case" Quick Action button to page layout |

---

## 2. Dependencies & Blockers

| Dependency | Type | Status | Owner | Work Item ID |
|-----------|------|--------|-------|-------------|
| Existing `PRMLoadAddressPrimary` DataRaptor deployed and working in QA | Upstream (code) | `Done` | Existing | — |
| Existing `PRMLoadAddressAncesMailing` DataRaptor deployed and working in QA | Upstream (code) | `Done` | Existing | — |
| Ancillary Reassessment PSV OmniScript (v8) stable as reference | Reference | `Done` | Existing | — |
| Business confirmation: No multi-location, primary only | Product decision | `Resolved` | BA | — |
| Business confirmation: ProceedTo options match Ancillary Reassessment PSV exactly | Product decision | `Resolved` | BA | — |

**Hard Blockers (cannot start development):**
- None — all prerequisites are met.

**Soft Blockers (can start but cannot complete/deploy):**
- Case Manager Lightning page layout access (need admin to add Quick Action for "Route Case" button after OmniScript is deployed)

---

## 3. Technical Implementation Plan

### 3.1 Summary of Approach

Restructure the existing `PRM_AddAncillaryPLAndBusinessLicense_English` OmniScript to remove multi-location selection and add editable address blocks (Primary/Mailing/Billing) mirroring the pattern established in Ancillary Reassessment PSV. Add a ReviewScreen + ProceedTo routing step that allows case routing without waiting for NPDB. Create one new DataRaptor (Billing) and one new standalone OmniScript (Route Case button). All changes are in OmniStudio — no Apex required.

**Approach Type:**
- [x] OmniScript modification (republish required)
- [x] Integration Procedure new/update
- [x] DataRaptor new/update
- [ ] Apex class — new service
- [ ] Apex class — modify existing
- [ ] Batch Apex (new or extending existing framework)
- [ ] Trigger / Trigger Handler update
- [ ] LWC — new component
- [ ] LWC — modify existing
- [ ] Flow — new or update
- [ ] Data Model — new field/object
- [ ] Data Model — field modification
- [x] Permission Set / FLS change
- [ ] Custom Metadata Type (CMT) update
- [ ] Configuration only (no code)
- [ ] Data Fix (DFX framework)

### 3.2 Detailed Implementation Steps

#### Data Model Changes
- [ ] None — using existing objects/fields (Address, Case, ContentNote, PRM_CaseManagerAssociation__c)

#### OmniStudio Changes — `PRM_AddAncillaryPLAndBusinessLicense_English` (v2 → v3)

**Phase 1: Remove multi-location**
- [ ] Remove `PracLoc` type-ahead element
- [ ] Remove `NewPL` repeatable block (or set repeatLimit=1, remove add-more)
- [ ] Keep PLId, PLName as hidden fields populated from FetchDetails

**Phase 2: Enhance FetchDetails**
- [ ] Update FetchDetails IP Action to default primary practice location (primary PL auto-loaded)
- [ ] Add ExistingAddresses output: array with `[{AddType:"Primary",...}, {AddType:"Mailing",...}, {AddType:"Billing",...}]`
- [ ] Map PLId, PLName, LocationId from primary PL

**Phase 3: Add editable address blocks**
- [ ] Create `PrimaryAddress` block — always visible, editable — fields: AddLine1Primary, AddLine2Primary, CityPrimary, StatePrimary, ZipPrimary, Zip4Primary, PhonePrimary, PhoneExtensionPrimary, FaxPrimary
- [ ] Pre-populate PrimaryAddress from ExistingAddresses[AddType="Primary"]
- [ ] Create `MailingAddressChange` radio — "Change of Mailing Address?" (Yes/No)
- [ ] Create `MailingAddressNew` block — visible when MailingAddressChange=Yes — fields: AddLine1Mailing thru Zip4Mailing
- [ ] Create `SameAsPrimary` Set Values — copies Primary to Mailing
- [ ] Create `ClearMailing` Set Values — clears Mailing fields
- [ ] Create `BillingAddressChange` radio — "Change of Billing Address?" (Yes/No)
- [ ] Create `BillingAddressNew` block — visible when BillingAddressChange=Yes

**Phase 4: Add ReviewScreen + ProceedTo**
- [ ] Create `ReviewScreen` step — displays PrimaryAddressReview, MailingAddressReview (conditional), BillingAddressReview (conditional), NewLicenseReview (conditional)
- [ ] Create `ProceedTo` radio — options: Pending NPDB Verification, HACAC, HACAC - Pended, Provider Outreach Needed
- [ ] Create `PendedReason` text — visible when ProceedTo = "HACAC - Pended"
- [ ] Create `ReviewNote` text area — optional
- [ ] Create `SetCaseManagerAndCase` Set Values — CaseStatusToUpdate, NoteTitle formulas per ProceedTo

**Phase 5: Conditional NPDB**
- [ ] Update `NPDBReportRequest` step — add show condition: `ProceedTo == "Pending NPDB Verification"`
- [ ] Update extraPayload: pass `NPDBRequest: "No"` when ProceedTo ≠ Pending NPDB

**Phase 6: Update OmniScript extraPayload to IP**
- [ ] Pass: PrimaryAddress, MailingAddressNew, BillingAddressNew, ExistingAddresses, AddrEffective, ProceedTo, ReviewNote, CaseStatusToUpdate, NoteTitle

#### OmniStudio Changes — `PRM_AncillaryAddPLAndLicenseCreation_English` (IP v2 → v3)

- [ ] Add DataRaptor Post Action: `PRMLoadAddressPrimary` — condition: `ISNOTBLANK(%PrimaryAddress%)`
- [ ] Add DataRaptor Post Action: `PRMLoadAddressAncesMailing` — condition: `ISNOTBLANK(%MailingAddressNew%)`
- [ ] Add DataRaptor Post Action: `PRMLoadAddressAncesBilling` — condition: `ISNOTBLANK(%BillingAddressNew%)`
- [ ] Place all 3 address steps BEFORE `CreateBusinessLicensesAndCaseManagerAssoc`
- [ ] Add Case status update action (DML or DR) using CaseStatusToUpdate
- [ ] Add ContentNote creation action using ReviewNote + NoteTitle
- [ ] Update `CreateBusinessLicensesAndCaseManagerAssoc` to accept single-PL structure (not NewPL array)
- [ ] Update `DRTransformPracLocs` for single-PL input

#### New DataRaptor — `PRMLoadAddressAncesBilling`

- [ ] Create as DataRaptor Load — mirror `PRMLoadAddressAncesMailing`
- [ ] Input mapping: CaseManagerId, EffectiveFromDate, ExistingBillingAddr (filtered from ExistingAddresses), BillingAddressNew, Latitude, Longitude, isStandardized
- [ ] Target object: `Address` with AddressType = "Billing"
- [ ] Match on: ParentId + AddressType (upsert existing or insert new)

#### New OmniScript — `PRM_RouteCase_English` (v1)

- [ ] Create standalone OmniScript for "Route Case" button on Case Manager page
- [ ] Step 1: `ProceedTo` radio (required) — same 4 options
- [ ] Step 1: `Note` text area (required)
- [ ] Set Values: CaseStatusToUpdate, NoteTitle
- [ ] IP Action: Update Case status + create ContentNote (reuse/mirror IP logic from main flow)
- [ ] Navigate Action: Return to Case Manager record

#### Lightning Page — Case Manager Record Page

- [ ] Add Quick Action: "Route Case" — launches `PRM_RouteCase_English` OmniScript
- [ ] Visibility: When Case Manager status indicates PSV complete / pending routing

### 3.3 OmniScript / IP Call Chain

```
OmniScript: PRM_AddAncillaryPLAndBusinessLicense_English (v3)
  ├─ Step: InvalidCase (validation)
  ├─ IP Action: FetchDetails (ENHANCED — returns primary PL + ExistingAddresses)
  ├─ Step: NoLocationAvailable (error, conditional)
  ├─ Step: PrimaryLocationAndAddresses
  │     ├─ PLName (display, read-only)
  │     ├─ PLId (hidden)
  │     ├─ PrimaryAddress (block, editable, pre-populated)
  │     ├─ MailingAddressChange (radio: Yes/No)
  │     ├─ MailingAddressNew (block, conditional)
  │     ├─ SameAsPrimary / ClearMailing (Set Values)
  │     ├─ BillingAddressChange (radio: Yes/No)
  │     └─ BillingAddressNew (block, conditional)
  ├─ AddBLQuestion (radio: Yes/No)
  ├─ NewLicense (block, repeatable max 4, conditional)
  ├─ Step: ReviewScreen (NEW)
  │     ├─ PrimaryAddressReview (always)
  │     ├─ MailingAddressReview (conditional)
  │     ├─ BillingAddressReview (conditional)
  │     └─ NewLicenseReview (conditional)
  ├─ ProceedTo (radio: 4 options) (NEW)
  ├─ PendedReason (conditional on HACAC - Pended)
  ├─ ReviewNote (text area, optional)
  ├─ SetCaseManagerAndCase (Set Values → CaseStatusToUpdate, NoteTitle) (NEW)
  ├─ Step: NPDBReportRequest (CONDITIONAL — only when ProceedTo = "Pending NPDB Verification")
  │     └─ NPDBRequest (radio: Yes/No)
  ├─ IP Action: PRM_AncillaryAddPLAndLicenseCreation_English (v3)
  │     ├─ PRMLoadAddressPrimary (DR Post Action) (NEW)
  │     ├─ PRMLoadAddressAncesMailing (DR Post Action) (NEW)
  │     ├─ PRMLoadAddressAncesBilling (DR Post Action) (NEW — new DR)
  │     ├─ UpdateCaseStatus (action) (NEW)
  │     ├─ CreateContentNote (action) (NEW)
  │     ├─ CreateBusinessLicensesAndCaseManagerAssoc (existing, adapted for single PL)
  │     ├─ CB_CreateAdverseActionLogs (existing)
  │     ├─ DRTransformPracLocs (existing, adapted for single PL)
  │     ├─ RA_CreateAdverseActionLogsBatch (existing)
  │     └─ Response
  └─ NavigateToCaseManager (action)
```

**Standalone (Route Case Button):**
```
OmniScript: PRM_RouteCase_English (v1) — NEW
  ├─ Step: RouteCase
  │     ├─ ProceedTo (radio, required)
  │     └─ Note (text area, required)
  ├─ SetCaseManagerAndCase (Set Values)
  ├─ IP Action: PRM_RouteCaseUpdate_Procedure (update Case + create ContentNote)
  └─ Navigate to Case Manager
```

### 3.4 Governor Limit Assessment

| Limit | Current Usage (estimate) | This Change Adds | Total | Risk |
|-------|------------------------|-----------------|-------|------|
| SOQL queries (sync: 100) | ~25 (FetchDetails + BL creation) | +6 (3 address DR loads + ExistingAddresses extract + Case update + ContentNote) | ~31 | `Safe` |
| DML statements (150) | ~8 (BL + AdverseAction + CaseManager) | +5 (Primary addr + Mailing addr + Billing addr + Case status + ContentNote) | ~13 | `Safe` |
| DML rows (10,000) | ~10 (single PL, max 4 BLs) | +5 (3 address records + 1 Case + 1 ContentNote) | ~15 | `Safe` |
| Heap (6MB sync / 12MB async) | ~2MB | +0.3MB (address payloads) | ~2.3MB | `Safe` |
| CPU time (10s sync / 60s async) | ~3s | +0.5s | ~3.5s | `Safe` |
| Callouts (100) | 0 (Precisely deferred to Phase 2) | +0 | 0 | `Safe` |

**Assessment:** This story operates on a **single practice location** with at most 3 address records. Governor limits are not a concern. The removal of multi-location (previously up to 9) actually **reduces** limit pressure compared to the current design.

---

## 4. Acceptance Criteria Breakdown & Estimation

| # | Acceptance Criteria (from ticket) | Sub-Tasks | Component | Est. (hrs) |
|---|----------------------------------|-----------|-----------|-----------|
| **AC-1** | **Default primary practice location (no type-ahead, no multi-select)** | | | |
| | | 1. Remove PracLoc type-ahead element from OmniScript | OmniScript | 1h |
| | | 2. Remove NewPL repeatable block | OmniScript | 1h |
| | | 3. Enhance FetchDetails to default primary PL (PLId, PLName, LocationId) | IP / DR | 3h |
| | | 4. Build ExistingAddresses array output in FetchDetails | IP / DR | 2h |
| | | 5. Test: Verify primary PL auto-loads, no type-ahead shown | QA testing | 1h |
| **AC-2** | **Edit Primary (Physical) address — always editable, pre-populated** | | | |
| | | 1. Create PrimaryAddress block with 11 fields (editable, pre-populated) | OmniScript | 3h |
| | | 2. Map pre-population from ExistingAddresses[Primary] | OmniScript | 1h |
| | | 3. Test: Fields pre-populate, user can edit, values pass to IP | QA testing | 1h |
| **AC-3** | **Edit Mailing address — conditional on "Change of Mailing Address?" = Yes** | | | |
| | | 1. Create MailingAddressChange radio (Yes/No) | OmniScript | 0.5h |
| | | 2. Create MailingAddressNew block (6 fields, conditional visibility) | OmniScript | 2h |
| | | 3. Create SameAsPrimary + ClearMailing Set Values | OmniScript | 1h |
| | | 4. Test: Block shows/hides, SameAsPrimary copies correctly | QA testing | 1h |
| **AC-4** | **Edit Billing address — conditional on "Change of Billing Address?" = Yes** | | | |
| | | 1. Create BillingAddressChange radio (Yes/No) | OmniScript | 0.5h |
| | | 2. Create BillingAddressNew block (6 fields, conditional visibility) | OmniScript | 2h |
| | | 3. Create PRMLoadAddressAncesBilling DataRaptor (mirror Mailing DR) | DataRaptor | 3h |
| | | 4. Test: Block shows/hides, billing saves correctly | QA testing | 1h |
| **AC-5** | **Add Business Licenses — existing behavior preserved for primary PL** | | | |
| | | 1. Adapt existing AddBLQuestion + NewLicense for single-PL input (PLId from defaulted primary) | OmniScript | 1.5h |
| | | 2. Update CreateBusinessLicensesAndCaseManagerAssoc in IP for single-PL structure | IP | 2h |
| | | 3. Test: BL creates, links to primary PL, duplicate check works | QA testing | 1h |
| **AC-6** | **ReviewScreen — display updated addresses before routing** | | | |
| | | 1. Create ReviewScreen step with PrimaryAddressReview, MailingAddressReview, BillingAddressReview blocks | OmniScript | 3h |
| | | 2. Add conditional visibility for Mailing/Billing review blocks | OmniScript | 0.5h |
| | | 3. Test: Review shows correct updated values | QA testing | 0.5h |
| **AC-7** | **ProceedTo routing — route without waiting for NPDB** | | | |
| | | 1. Create ProceedTo radio (4 options) + PendedReason + ReviewNote | OmniScript | 1.5h |
| | | 2. Create SetCaseManagerAndCase Set Values (CaseStatusToUpdate, NoteTitle formulas) | OmniScript | 2h |
| | | 3. Make NPDBReportRequest conditional (show only when ProceedTo = Pending NPDB) | OmniScript | 1h |
| | | 4. Update IP: Add Case status update + ContentNote creation steps | IP | 3h |
| | | 5. Update extraPayload: pass ProceedTo, NPDBRequest, CaseStatusToUpdate, NoteTitle | OmniScript/IP | 1h |
| | | 6. Test: All 4 routing paths (NPDB shown only for "Pending NPDB"; Case status correct) | QA testing | 2h |
| **AC-8** | **"Route Case" button on Case Manager record page** | | | |
| | | 1. Create `PRM_RouteCase_English` OmniScript (ProceedTo + Note + IP action) | OmniScript | 4h |
| | | 2. Create Route Case IP (update Case status + create ContentNote) | IP | 2h |
| | | 3. Add Quick Action to Case Manager Lightning page | Config | 1h |
| | | 4. Test: Button visible, modal opens, routes correctly for all 4 options | QA testing | 1.5h |
| **AC-9** | **NPDB request — preserved, conditional on ProceedTo** | | | |
| | | 1. Verify NPDBReportRequest/NPDBRequest logic still works when ProceedTo = Pending NPDB | OmniScript/IP | 1h |
| | | 2. Verify NPDB does NOT fire for other ProceedTo values | QA testing | 0.5h |
| | **TOTAL** | | | **~51h** |

| Estimation Summary | |
|--------------------|---|
| Total estimated hours | **~51 hours (6.4 dev days)** |
| Story points assigned | **13** |
| Confidence level | `Medium` |
| Biggest risk to estimate | FetchDetails IP enhancement — building ExistingAddresses array with correct structure matching Ancillary Reassessment pattern. May require debugging DR Extract filter logic for address types. |

---

## 5. Testing Strategy

### 5.1 Apex Test Coverage

| Test Class | Methods to Add/Update | What's Tested | Bulk Test? |
|-----------|----------------------|--------------|-----------|
| N/A | N/A | No Apex changes in this story | N/A |

> **Note:** This story is OmniStudio-only. No new Apex test classes required. Existing `PRM_AncillaryReAssessmentPSVServiceTests` covers the reference pattern.

### 5.2 OmniStudio Manual Testing

| OmniScript / IP | Test Scenario | Test Data | Expected Result |
|----------------|---------------|-----------|-----------------|
| `PRM_AddAncillaryPLAndBusinessLicense_English` v3 | Default primary PL loads (no type-ahead) | Case Manager with primary PL assigned | PLName + addresses auto-populate |
| Same | Edit Primary address + save | Change AddLine1 to "123 Test St" | PRMLoadAddressPrimary fires, Address record updated |
| Same | Change Mailing address = Yes, fill new address | Select Yes, enter mailing address | PRMLoadAddressAncesMailing fires, Mailing address created/updated |
| Same | Change Billing address = Yes, use "Same as Physical" | Select Yes, check Same as Physical | BillingAddressNew = PrimaryAddress; PRMLoadAddressAncesBilling fires |
| Same | ProceedTo = HACAC (skip NPDB) | Select HACAC, enter ReviewNote | Case status = Closed, ContentNote created, NPDB step NOT shown |
| Same | ProceedTo = Pending NPDB Verification | Select Pending NPDB, complete NPDB request | NPDB step shown, request fires, Case status = In Progress |
| Same | ProceedTo = HACAC - Pended | Select HACAC - Pended, fill PendedReason | Case status = Closed, PendedReason captured |
| Same | ProceedTo = Provider Outreach Needed | Select Provider Outreach | Case status = Pending Provider Outreach |
| Same | Add Business License (existing) | Add BL with License Type, Number, State | BL record created, linked to primary PL |
| Same | Duplicate BL check | Enter same License State + Number + Class | Error displayed (existing behavior) |
| Same | No primary PL exists | Case Manager without primary PL | NoLocationAvailable error step shown |
| `PRM_RouteCase_English` v1 | Route via Case Manager button | Click Route Case button | Modal opens, ProceedTo + Note shown, routes correctly |
| `PRM_RouteCase_English` v1 | Validation — Note required | Leave Note blank, try submit | Validation error — Note is required |

### 5.3 LWC Unit Tests (Jest)

| Component | Test File | Scenarios |
|-----------|----------|-----------|
| N/A | N/A | No LWC changes |

### 5.4 Integration / E2E Testing in QA Sandbox

| Flow | Scenario | Steps | Verify |
|------|----------|-------|--------|
| Full path: Add PL/BL → HACAC | Credential specialist edits addresses + adds BL + routes to HACAC | 1. Open Case Manager 2. Launch AddAncillaryPL OS 3. Edit Primary address 4. Change Mailing=Yes, fill 5. Add 2 Business Licenses 6. ReviewScreen shows correct data 7. ProceedTo=HACAC 8. Submit | All records created; Case = Closed; ContentNote exists; NPDB NOT fired |
| Full path: Add PL/BL → Pending NPDB | Same as above but route to NPDB | Same steps 1-6, then ProceedTo=Pending NPDB, request NPDB | NPDB request created; Case = In Progress |
| Route Case button (standalone) | Post-PSV routing after main flow | 1. Complete PSV 2. Click "Route Case" button on Case Manager 3. Select HACAC 4. Enter Note 5. Submit | Case status updated; ContentNote created with Note text |
| Regression: Existing BL behavior | Verify business license creation is unchanged | Add BL without address changes (Primary untouched, Mailing=No, Billing=No) | BL creates correctly, no address DML fires |

---

## 6. Deployment Plan

### 6.1 Deployment Order

| Step | What | Method | Command / Notes |
|------|------|--------|-----------------|
| 1 | `PRMLoadAddressAncesBilling` DataRaptor | OmniStudio Designer (manual) | Create in QA org via DataRaptor UI → mirror PRMLoadAddressAncesMailing |
| 2 | FetchDetails IP/DR enhancement | OmniStudio Designer | Update FetchDetails DR to extract ExistingAddresses; activate new version |
| 3 | `PRM_AncillaryAddPLAndLicenseCreation_English` IP (v3) | OmniStudio Designer | Add address DR post actions + Case update + ContentNote; activate v3 |
| 4 | `PRM_AddAncillaryPLAndBusinessLicense_English` OS (v3) | OmniStudio Designer | Full restructure; activate v3; deactivate v2 |
| 5 | `PRM_RouteCase_English` OS (v1) | OmniStudio Designer | Create new OS; activate |
| 6 | Route Case IP | OmniStudio Designer | Create and activate |
| 7 | Case Manager Lightning Page — Quick Action | Setup → Object Manager → Case Manager → Page Layouts | Add Route Case action to page layout |
| 8 | End-to-end testing | Manual in QA org | Run all scenarios from Section 5.4 |

### 6.2 OmniScript Version Management

| Component | Current Active Version | New Version | Activate After Deploy? |
|-----------|----------------------|-------------|----------------------|
| `PRM_AddAncillaryPLAndBusinessLicense_English` | v2 | **v3** | Yes — deactivate v2 first |
| `PRM_AncillaryAddPLAndLicenseCreation_English` | v2 | **v3** | Yes — deactivate v2 first |
| `PRM_RouteCase_English` | N/A (new) | **v1** | Yes |

### 6.3 Rollback Plan

| If This Fails... | Rollback Action | Reversible? |
|------------------|----------------|-------------|
| New OmniScript v3 has UI bugs or routing errors | Deactivate v3 → Reactivate v2 (original version). Users immediately get old flow. | **Yes** — OmniScript versioning makes this instant |
| New IP v3 causes timeout or DML failures | Deactivate IP v3 → Reactivate IP v2. OmniScript v2 already works with IP v2. | **Yes** |
| PRMLoadAddressAncesBilling DR saves incorrect data | Deactivate the DR in Designer (remove from IP action step condition, or set condition to `false`). Billing won't save but Primary + Mailing still work. | **Yes** — partial rollback |
| Route Case button/OmniScript breaks | Remove Quick Action from page layout (Setup change, no deploy needed). Revert to manual Case routing. | **Yes** — config rollback |
| FetchDetails enhancement returns bad data | Reactivate previous FetchDetails DR/IP version. OmniScript v2 + old FetchDetails = original behavior. | **Yes** |

### 6.4 Feature Toggle (if applicable)

| Toggle Mechanism | Name | Default | How to Disable |
|-----------------|------|---------|---------------|
| OmniScript Version | Revert to v2 | v3 active | Deactivate v3, activate v2 in OmniStudio Designer |
| Page Layout (Route Case button) | Quick Action on Case Manager page | Visible | Remove action from Lightning page layout |

> **Note:** No Custom Setting or CMT toggle needed — OmniScript versioning IS the feature toggle. If anything goes wrong, reactivate v2 and users never see v3.

---

## 7. Security & Data Considerations

| Consideration | Assessment |
|--------------|-----------|
| **New fields contain PHI/PII?** | No new fields. Address data already exists and is already visible to credentialing specialists. |
| **HIPAA implications?** | N/A — no new exposure. Addresses are already accessible in existing flows. |
| **Sharing rules affected?** | No — Address records inherit sharing from parent (PRM_HealthcareFacility__c / Location). No change. |
| **Record-level access?** | Existing FLS on Address object covers. `PRM_AncillaryCredSpecialist` already has Address CRUD. |
| **Trigger Bypass consideration?** | N/A — no triggers being added or modified. `PRM_AddressTrigger` may fire on address upsert but handles it (existing behavior from Ancillary Reassessment). |
| **Portal/Community access?** | N/A — this flow is internal credentialing specialist only. Not portal-facing. |
| **Audit trail needed?** | ContentNote creation per ProceedTo routing provides audit trail for routing decisions. `PRM_ExceptionLog__c` captures IP errors. Sufficient. |

---

## 8. Observability & Error Handling

| Scenario | Error Handling Approach |
|----------|----------------------|
| FetchDetails cannot find primary PL | Show `NoLocationAvailable` step (existing behavior). User cannot proceed. |
| PRMLoadAddressPrimary DR fails | IP returns error in Response; OmniScript shows error message to user (existing OS error handling pattern). Log to `PRM_ExceptionLog__c`. |
| PRMLoadAddressAncesBilling DR fails (new) | Same pattern — IP returns error; OS shows message. User can retry. Address save is independent — Primary/Mailing can still succeed if Billing fails. |
| Case update fails on routing | IP returns error; OS shows error. User retries or uses Route Case button later. |
| ContentNote creation fails | Non-blocking — log to `PRM_ExceptionLog__c` but allow routing to complete. Note is informational. |
| User abandons flow mid-way | No partial state saved (OmniScript does not save until IP Action runs). No stale data risk. |

**Post-deploy monitoring (first 30 minutes):**
- [ ] Check `PRM_ExceptionLog__c` for new error entries related to `PRM_AncillaryAddPLAndLicenseCreation`
- [ ] Execute full flow once: Edit Primary + Mailing + Add 1 BL + ProceedTo = HACAC
- [ ] Verify Address record updated via SOQL: `SELECT Id, AddressLine1, AddressType FROM Address WHERE ParentId = '[primary PL LocationId]'`
- [ ] Verify Case status: `SELECT Id, Status FROM Case WHERE Id = '[CaseId]'`
- [ ] Verify ContentNote created: `SELECT Id, Title FROM ContentNote WHERE CreatedDate = TODAY ORDER BY CreatedDate DESC LIMIT 5`
- [ ] Test Route Case button separately

---

## 9. Open Questions & Assumptions

### Open Questions

| # | Question | Directed To | Status | Answer |
|---|----------|------------|--------|--------|
| Q1 | Should Precisely address validation be included in this sprint or deferred to Phase 2? | Product/BA | `Resolved` | **Deferred to Phase 2** — deliver address editing first, add Precisely later |
| Q2 | Should the "Route Case" button be visible for ALL Case Manager statuses or only specific ones? | Product/BA | `Open` | Awaiting — assume "PSV Complete / Pending Routing" for now |
| Q3 | If FetchDetails finds no primary PL, should we fall back to any active PL or hard-stop? | Product/BA | `Resolved` | **Hard-stop** — show NoLocationAvailable error (confirmed by business) |
| Q4 | For Route Case button — should Note be required or optional? | Product/BA | `Resolved` | **Required** (per mockup/screenshot reference) |

### Assumptions

| # | Assumption | Risk if Wrong | Validated By |
|---|-----------|--------------|-------------|
| A1 | `PRMLoadAddressPrimary` and `PRMLoadAddressAncesMailing` DataRaptors work identically when called from AddAncillaryPL IP as they do from Ancillary Reassessment IP (same input structure) | Medium — would need to debug DR mapping | Unvalidated — verify during Phase 2 testing |
| A2 | ExistingAddresses can be built by querying `Address WHERE ParentId = PrimaryPL.LocationId` | Low — this is how Ancillary Reassessment does it | Validated — confirmed in `PRM_FetchAncillaryReassessmentPSV_Procedure` |
| A3 | Creating ContentNote via IP is supported (not just from LWC/Apex) | Low — ContentNote is a standard object with API access | Validated — Ancillary Reassessment already creates ContentNotes from IP |
| A4 | The "Route Case" OmniScript can be launched from a Quick Action on Case Manager record page | Low — standard OmniScript launch pattern | Validated — other OmniScripts launch this way |
| A5 | Deactivating OmniScript v2 and activating v3 is instant (no downtime for active users) | Low — OmniScript versioning is designed for this | Validated — done many times on this project |

---

## 10. Out of Scope

- **Precisely address validation** — Deferred to Phase 2. Addresses save as-entered without USPS standardization.
- **Multi-location support** — Explicitly removed per business decision. This story handles primary PL only.
- **Existing address migration / data fix** — If existing data has incorrect AddressType values, that's a separate DFX story.
- **Portal-facing visibility** — This is internal credentialing only. Portal providers cannot access this flow.
- **BCBSA sync for address changes** — Address records are not in BCBSA sync scope. No sync impact.
- **Batch processing for address updates** — Single PL with 3 address records is well within synchronous limits.

---

## 11. Retrieval & Sync Notes

**Retrieval scope for teammates after this deploys:**

> **Important:** OmniStudio components (OS/IP/DR) must be retrieved via OmniStudio export or manual metadata retrieval. They cannot be auto-synced with the standard retrieval script.

```bash
# After deploy, teammates should:

# 1. Retrieve OmniScript metadata (if source-tracking enabled):
sf project retrieve start \
  --metadata OmniScript:PRM_AddAncillaryPLAndBusinessLicense_English \
  --metadata OmniScript:PRM_RouteCase_English \
  --target-org qa-sandbox

# 2. Retrieve Integration Procedure metadata:
sf project retrieve start \
  --metadata OmniProcess:PRM_AncillaryAddPLAndLicenseCreation_English \
  --target-org qa-sandbox

# 3. Or use full sync:
./RETRIEVE_COMPONENTS_FROM_QA.sh
# Select option: 1 (ALL)
```

---

## Sign-Off

| Role | Name | Date | Approved? |
|------|------|------|-----------|
| Developer | Kothapalli, Prashanth | 2026-05-24 | Yes |
| Tech Lead | _[name]_ | _[date]_ | `Pending` |
| BA / Product | _[name]_ | _[date]_ | `Pending` |

---

## Changelog

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-24 | Initial template completed | Pre-development analysis |
| _[date]_ | _[future updates during development]_ | _[reason]_ |
