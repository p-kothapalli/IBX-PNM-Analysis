# USER STORY: Add Georgia (GA) & Target Counties to Provider Credentialing Forms — State & County Picklist Expansion

**Persona:** Developer, Admin  
**Priority:** P1  
**OmniScripts:**
- PRM_PractitionerParticipationForm_English
- PRM_ProviderChangeForm_English
- PRM_OffCycleCredentialing_English
- PRM_PDMManualUpdate_English
- PRM_PSVSubOsTxnyRole_English
- PRM_RecredQC_English
- PRM_AncillaryProviderForm_English

**Integration Procedures:** State/County filtering in relevant IPs; form source routing for GA submissions  
**Relevant Requirements:** GA_Internal_Credentialing_Scope_Implementation_Plan.md (Part 2–3); FHN-04, FHN-05, PIE-02

---

## Story

**As a** Developer/Admin,  
**I want** Georgia (GA) and the target counties (Fulton, Cobb, Clayton, DeKalb, Gwinnett) added to all state and county picklists and OmniScript options used across provider credentialing forms,  
**So that** credentialing specialists can consistently select GA and its counties when processing GA provider applications, and the system supports the AmeriHealth Georgia (AHGA) network expansion.

**Why it matters:** GA providers require GA state and county support across the entire credentialing workflow. Without this, GA applications cannot be entered in PIE or processed through existing flows. This is foundational to GA scope expansion and blocks all dependent work.

---

## Scope

| Flow | OmniScript | Affected Step(s) | Data Source | County Support |
|------|------------|-----------------|-------------|----------------|
| Practitioner Participation | PRM_PractitionerParticipationForm_English | PractitionerState (AddLicenseBlock) | Address.PRM_State__c picklist | Yes – where primary address present |
| Provider Change Request | PRM_ProviderChangeForm_English | Provider details state (if applicable) | Address.PRM_State__c | Conditional |
| PDM Manual Update | PRM_PDMManualUpdate_English | Practice location state/county (if present) | Address.PRM_State__c | Yes – Service Area Verification |
| Off-Cycle Credentialing | PRM_OffCycleCredentialing_English | Provider search; practice location state | Address.PRM_State__c | Conditional |
| PSV (Taxonomy/Role) | PRM_PSVSubOsTxnyRole_English | PSVPracticeState, PSVPracticeCounty | Address.PRM_State__c | **Yes – critical** |
| Recred QC | PRM_RecredQC_English | License state (if select); Service Area; Quick Links | Address.PRM_State__c + DataRaptor | Yes – recred verification |
| Ancillary Provider | PRM_AncillaryProviderForm_English | Primary/practice location state/county | Address.PRM_State__c | Conditional |

---

## Current State (from codebase)

### State Picklists (Salesforce Level)

- **Address.PRM_State__c:** Currently contains PA, NJ, DE, MD (implied from multiple user stories)
- **Location:** Custom field on Address object (related to HealthcarePractitioner, HealthcareFacility, Location)
- **Usage:** OmniScript elements use `optionSource` binding to this picklist

### OmniScript Elements (Examples)

- **PractitionerState** (PRM_PractitionerParticipationForm_English_Element_PractitionerState.json)
  - **Type:** Select (dropdown or radio)
  - **Current Options:** PA, NJ, DE, MD (hardcoded or from Address.PRM_State__c)
  - **Location:** `vlocity_export/OmniScript/PRM_PractitionerParticipationForm_English/`

- **PSVPracticeState, PSVPracticeCounty** (PRM_PSVSubOsTxnyRole_English)
  - **Type:** Select elements in ServiceAreaVerificationStep
  - **Current State:** PA/NJ/DE/MD states; counties likely filtered by state selection
  - **Location:** `vlocity_export/OmniScript/PRM_PSVSubOsTxnyRole_English/`

### DataRaptors (if state/county filtering exists)

- State/county filters may exist in DRs that populate address data (e.g., `PRMExtractAddressOptions`)
- Location: TBD (to be verified during implementation)

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change | Specification |
|-----------|------|--------|----------------|
| **Address.PRM_State__c** | Salesforce Picklist | Add value: Georgia | **New Picklist Value:** Label = "Georgia", API Name = "GA" |
| **County Picklist** (if exists on Address or custom) | Salesforce Picklist | Add 5 values: Fulton, Cobb, Clayton, DeKalb, Gwinnett | **New Picklist Values:** Each as separate record; dependency on state = GA (if available) |
| **PractitionerState** | OmniScript Element | Add GA to options; add 5 counties if primary address step exists | If hardcoded: add `{"name": "Georgia", "value": "GA"}`. If optionSource: ensure picklist is updated. Verify county dependence. |
| **PSVPracticeState** | OmniScript Element | Add GA; verify county field dependency | Add GA to state options; ensure PSVPracticeCounty filters to GA counties when GA selected |
| **PSVPracticeCounty** | OmniScript Element | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett as GA-filtered options | Implement conditional options or DataRaptor lookup: IF PSVPracticeState = GA, THEN show 5 GA counties |
| **PDM Manual Update state/county** | OmniScript | If practice location state/county elements exist, add GA + counties | Scan `PRM_PDMManualUpdate_English` for Address state/county elements; add GA/counties where present |
| **Recred QC state/county** | OmniScript | If Service Area or license state elements exist, add GA + counties | Scan `PRM_RecredQC_English` for state/county elements; ensure GA and counties available |
| **Off-Cycle provider search** | OmniScript / DataRaptor | If geographic filters exist, add GA + counties | Verify `PRM_OffCycleCredentialing_English` practice location search; add GA/counties if filtered |
| **State/county DataRaptors** | DataRaptor (if exists) | Update Extract or Transform to include GA + 5 counties in filter options | Example: `PRMExtractAddressOptions` or `PRMExtractCountyByState` — verify during implementation |

### DataRaptor / Integration Procedure Specifications (if applicable)

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| PRMExtractAddressOptions | Extract (hypothetical) | FormType, Network | StateOptions, CountyOptions | Add GA to state list; add 5 counties when state=GA |
| PRMExtractCountyByState | Extract (hypothetical) | StateCode | CountyList | Add new record: StateCode=GA → CountyList=[Fulton, Cobb, Clayton, DeKalb, Gwinnett] |
| PRM_[FormSource]_IP (hypothetical) | IP | FormSourceType | MappedFormSource | If form source "Provider Participation Form AH GA" is routed here, ensure GA is recognized and mapped |

### Implementation Notes

1. **Picklist Dependency:** If county picklist has conditional visibility based on state, ensure GA and counties are wired in the dependent picklist relationship.
2. **OmniScript optionSource:** Verify each element uses `optionSource: "Address.PRM_State__c"` (dynamic) vs. hardcoded options. Hardcoded requires JSON array edits; dynamic requires only picklist update.
3. **DataRaptor Scans:** Codebase scan needed to identify all DRs that filter by state/county. Use Grep for `Georgia|"GA"|state.*filter|county.*filter`.
4. **Multi-step workflows:** PSVPracticeCounty may be a separate element; county selection may be conditional on state. Verify step-by-step in target OmniScripts.

### Example (State Picklist — Salesforce)

**Before:**
```
PA
NJ
DE
MD
```

**After:**
```
PA
NJ
DE
MD
GA (new)
```

### Example (County Options — OmniScript Element)

**Before (PSVPracticeCounty):**
```json
{
  "name": "PSVPracticeCounty",
  "type": "Select",
  "show": true,
  "optionSource": "...CountyOptions",
  "condition": "PSVPracticeState != null"
}
```

**After (if hardcoded or updated via DR):**
```json
{
  "name": "PSVPracticeCounty",
  "type": "Select",
  "show": true,
  "optionSource": "...CountyOptions",
  "condition": "PSVPracticeState != null",
  "options": [
    // ... existing PA/NJ/DE/MD counties ...
    { "name": "Fulton", "value": "Fulton" },
    { "name": "Cobb", "value": "Cobb" },
    { "name": "Clayton", "value": "Clayton" },
    { "name": "DeKalb", "value": "DeKalb" },
    { "name": "Gwinnett", "value": "Gwinnett" }
  ]
}
```

---

## Acceptance Criteria

### Scenario 1: State Picklist Update (Happy Path)

**Given** the Admin has updated the Address.PRM_State__c picklist to include Georgia,  
**When** any form in PIE attempts to populate state options,  
**Then** Georgia (GA) shall appear in all state dropdowns and selections.

---

### Scenario 2: Practitioner Participation Form — GA Selection

**Given** a Credentialing Specialist is in PRM_PractitionerParticipationForm_English entering data for a GA provider,  
**When** they select License State (PractitionerState element),  
**Then** Georgia (GA) shall be available and selectable.  
**When** they proceed to primary address section (if present) and select state,  
**Then** Georgia (GA) shall be available, and upon selection, county field shall be visible and show only GA-applicable counties (Fulton, Cobb, Clayton, DeKalb, Gwinnett).

---

### Scenario 3: PSV Taxonomy/Role — GA Practice State & County

**Given** a Credentialing Specialist is in PRM_PSVSubOsTxnyRole_English during Service Area Verification,  
**When** they select PSVPracticeState,  
**Then** Georgia (GA) shall be available as an option.  
**When** they select Georgia,  
**Then** PSVPracticeCounty field shall display only Fulton, Cobb, Clayton, DeKalb, Gwinnett (no other states' counties).  
**When** they select a county,  
**Then** the form shall accept it without validation error.

---

### Scenario 4: Recred QC — GA License State

**Given** a Credentialing Specialist is in PRM_RecredQC_English reviewing a recred case for a GA provider,  
**When** license state is displayed or editable,  
**Then** Georgia (GA) shall be recognized and available.  
**When** the specialist views or filters by state,  
**Then** GA shall be a valid filter option.

---

### Scenario 5: Off-Cycle Credentialing — GA Provider Search

**Given** a Credentialing Specialist is in PRM_OffCycleCredentialing_English searching for a provider,  
**When** they filter by practice location state (if applicable),  
**Then** Georgia (GA) shall be available as a filter option.  
**When** they select GA,  
**Then** the search shall return providers with GA practice locations; county filtering (if present) shall show only GA counties.

---

### Scenario 6: PDM Manual Update — GA Practice Location

**Given** a PDM Specialist is in PRM_PDMManualUpdate_English and modifies practice location information,  
**When** they select practice location state or county,  
**Then** Georgia (GA) and its 5 counties shall be available where applicable.  
**When** they save the update,  
**Then** GA state and county data shall persist without validation error.

---

### Scenario 7: Edge Case — State-Only vs. State+County Dependency

**Given** an OmniScript element uses state/county with conditional visibility,  
**When** state is set to GA,  
**Then** county field shall show only GA-applicable counties (no cross-state pollution).  
**When** state is changed back to PA,  
**Then** county options shall revert to PA counties only (no GA counties visible).

---

### Scenario 8: Edge Case — Picklist-Based vs. Hardcoded Options

**Given** OmniScript elements use either `optionSource` (dynamic picklist) or hardcoded options,  
**When** an element is updated,  
**Then** both hardcoded AND dynamic elements shall include Georgia and all 5 counties.  
**When** a developer adds a new form element with state/county later,  
**Then** the element template shall include GA/counties by default.

---

### Scenario 9: DataRaptor Filtering — County by State

**Given** a DataRaptor (if present) has a "Get County Options" type Extract,  
**When** the input state = "GA",  
**Then** the output shall be exactly: ["Fulton", "Cobb", "Clayton", "DeKalb", "Gwinnett"].  
**When** input state = "PA" or other state,  
**Then** the output shall NOT include GA counties.

---

### Scenario 10: Multi-Flow Integration — Consistency

**Given** a provider is created in Practitioner Participation Form with GA state/county,  
**When** the case is routed to PSV (PRM_PSVSubOsTxnyRole_English),  
**Then** GA state and selected county shall be available for reference and update.  
**When** the case moves to Recred (PRM_RecredQC_English),  
**Then** GA state shall remain selectable and recognized.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Picklist vs. Hardcoded:** Do all state/county options in OmniScript elements use `optionSource` binding, or are some hardcoded in JSON? | If hardcoded, each element must be manually edited; if dynamic, single picklist update suffices. | Developer / Tech Lead |
| 2 | **County Dependency:** Is the county picklist dependent on state (i.e., conditional visibility or filtering by state value)? If so, how is this configured in Salesforce or OmniScript? | Determines implementation path: multi-select picklist vs. DataRaptor lookup vs. formula-based filtering. | Salesforce Admin |
| 3 | **DataRaptor County Filters:** Do any DataRaptors (e.g., `PRMExtractCountyByState`, `PRMExtractAddressOptions`) exist that filter counties by state? If yes, must they be updated? | If yes, must identify and update all such DRs to include GA→5 counties mapping. | Developer |
| 4 | **Scope of "All Forms":** Do all 7 OmniScripts listed (Practitioner, Provider Change, PDM Manual, Off-Cycle, PSVTaxony, RecredQC, Ancillary) have state AND county elements? Or do some have only state? | Determines which elements must be updated vs. verified as complete. | Developer / Product |
| 5 | **Provider Change Form — State Scope:** Does PRM_ProviderChangeForm_English include a primary address state/county section, or only facility-level data? | If no primary address in this flow, county updates may be conditional. | Developer |
| 6 | **Off-Cycle Search — Geography Filter:** Does PRM_OffCycleCredentialing_English have a geographic or state filter for provider/facility search? If yes, must GA be added? | If yes, OmniScript element and/or DataRaptor must be updated. | Developer |
| 7 | **Legacy or Existing GA References:** Are there any existing (partial or hidden) GA references in the codebase (e.g., draft DataRaptors, commented-out GA options, config tables) that should be activated rather than created fresh? | If yes, may reduce work; if no, all updates are net-new. | Developer / Codebase Audit |
| 8 | **County Label vs. API Name:** Should counties be stored/displayed as full names (e.g., "Fulton County") or short codes (e.g., "Fulton")? | Affects picklist value naming and data consistency across forms. | Product / BA |
| 9 | **Testing Data Requirements:** Should QA have GA test providers pre-created in sandbox for end-to-end testing? Should test data include all 5 counties? | QA readiness and test plan clarity. | QA / Testing Lead |
| 10 | **Roll-Out Timing:** Is this story blocking other GA work (e.g., Quick Links, Form Source Routing)? Should it be prioritized as P0 instead of P1? | May affect sprint planning and priority. | Product Manager |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|---------------|-------------|
| **Address.PRM_State__c picklist** | Salesforce Field | **HIGH** | Core data model change; affects all forms referencing this picklist. Requires admin update and may need sandbox testing before prod deployment. |
| **PRM_PractitionerParticipationForm_English** | OmniScript | **HIGH** | Primary form for GA provider onboarding; state and county are mandatory. Must support GA entry from first form interaction. |
| **PRM_PSVSubOsTxnyRole_English** | OmniScript | **HIGH** | Service Area Verification is critical PSV step; must accept GA and 5 counties without blocking workflow. |
| **PRM_RecredQC_English** | OmniScript | **MEDIUM** | Recred is downstream; GA support ensures recredentialing GA providers is unblocked. May be tested after initial forms. |
| **County-filtering DataRaptors** (if exist) | DataRaptor | **MEDIUM** | If present, filtering logic must correctly map GA → 5 counties. Otherwise, county selection may fail or show incorrect data. |
| **PRM_OffCycleCredentialing_English** | OmniScript | **MEDIUM** | Off-cycle is optional for GA (depends on business rules); GA support ensures comprehensive coverage if needed. |
| **PRM_PDMManualUpdate_English, PRM_AncillaryProviderForm_English** | OmniScript | **LOW** | PDM and Ancillary updates are less critical to initial GA onboarding but must eventually support GA for complete workflow. |
| **Custom Metadata (Quick Links)** | Configuration | **LOW** | Not in scope of this story but dependent on successful state/county setup. Blocker only if Quick Links lookup fails due to missing GA reference. |

---

## Implementation Order

1. **Salesforce Admin:** Update Address.PRM_State__c picklist; add Georgia.
2. **Salesforce Admin:** Create/update county picklist (if separate); add 5 GA counties; configure dependency on state if needed.
3. **Developer:** Scan codebase for all state/county OmniScript elements and DataRaptors using Grep/Glob.
4. **Developer:** Update hardcoded state options in OmniScript elements (if any) to include GA.
5. **Developer:** Update or create county-filtering DataRaptors to include GA → 5 counties mapping.
6. **Developer:** Verify PSVPracticeCounty conditional visibility/options in PRM_PSVSubOsTxnyRole_English; ensure GA county filtering works.
7. **Developer:** Validate all 7 OmniScripts support GA selection without error.
8. **QA:** Create GA test provider(s) with each county; test end-to-end flow (Practitioner Form → PSV → RecredQC).
9. **QA:** Verify county dropdown filtering by state; test state change edge cases.
10. **Deployment:** Deploy picklist changes to production; then deploy OmniScript/DataRaptor changes.

---

## Out of Scope (This Story)

- **Form Source Routing** (mapping "Provider Participation Form AH GA" to PIE) — covered in separate story
- **Quick Links** (GA contract grid, GA CDS URLs) — covered in separate story
- **FHN Portal changes** (provider-facing form, "Before You Begin" content, provider manual link) — external, out of scope
- **Operational processes** (GA queue, license sources, training, DLP) — out of scope

---

## Definition of Done Checklist

- [ ] Address.PRM_State__c picklist includes Georgia
- [ ] County picklist (if separate) includes Fulton, Cobb, Clayton, DeKalb, Gwinnett
- [ ] Picklist dependency configured (county filtered by state, if applicable)
- [ ] All 7 OmniScripts scanned; state/county elements identified and documented
- [ ] Hardcoded GA/county options added to all OmniScript elements (if present)
- [ ] All state/county-filtering DataRaptors updated with GA → 5 counties mapping
- [ ] PSVPracticeCounty conditional visibility tested: GA selected → only GA counties shown
- [ ] State change edge case tested: PA → GA → PA; counties update correctly
- [ ] End-to-end test: GA provider flow from Practitioner Form through PSV/RecredQC
- [ ] QA sign-off: All acceptance criteria passed
- [ ] Deployment to production completed
- [ ] Post-go-live validation: GA options appear in production forms

---

## Related User Stories

- **GA_Internal_Credentialing_User_Stories.md** – Comprehensive GA scope expansion stories (Practitioner Participation, Provider Change, Application Review/PSV, Quick Links, Form Source Routing, Salesforce Picklists)
- **GA_Internal_Credentialing_Scope_Implementation_Plan.md** – Full implementation plan for GA expansion across FHN Portal, PIE, Salesforce, OmniScripts

---

*Created: 2026-03-29*  
*Source: Cursor AI Agent — User Story Architect*  
*Vertical: Provider Network Management (PNM)*  
*Status: Ready for Development*
