# GA Internal Credentialing Scope – User Stories (Flow-Centric)

**Source:** 2.20 Internal Credentialing Scope Read Out.pdf, GA_Internal_Credentialing_Scope_Implementation_Plan.md  
**Target:** Georgia (GA) + 5 counties: Fulton, Cobb, Clayton, DeKalb, Gwinnett

---

## Quick Reference

| Area | Change Summary |
|------|----------------|
| **State options** | Add Georgia (GA) to state dropdowns |
| **County options** | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett where county selection exists |
| **Form source** | Map "Provider Participation Form AH GA" for GA requests (PIE/FHNatic) |
| **Quick Links** | Add GA contract grid; add GA CDS verification (if required) |
| **Provider Change Form** | Remove capsite (Capitation Site) section |

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **License state source:** Is license state in DEA/CDS/Application Review sourced from the PAR form, CAQH, or Salesforce? DEAState in PRM_PSVSubOsWSNPDB is readOnly—does it come from a DataRaptor or Address.PRM_State__c? | Determines where to add GA (OmniScript options vs. picklist vs. IP) | Technical |
| 2 | **FHN Portal vs. PIE:** The FHN Portal has the provider-facing form. Is PRM_PractitionerParticipationForm_English the credentialing specialist form in PIE? If so, does it need GA state/county for primary address, or only for license state? | Scope of Practitioner Participation Form changes | BA |
| 3 | **Primary address state/county:** Where does primary address state and county appear in Practitioner Participation Form? PractitionerState is in AddLicenseBlock (license state). Is there a separate primary address step with state/county? | Which elements need GA + 5 counties | Developer |
| 4 | **Admitting privileges for GA:** Today only DE requires admitting privileges. Is it required for GA? | PRM_PSVSubOsTxnyRole_English – AdmittingPrivilegesReview visibility | Legal/RPM |
| 5 | **CDS verification for GA:** Today required for all states except PA. Is it required for Georgia? | Add GA CDS link to Quick Links; CDS verification step visibility | Legal/RPM |
| 6 | **GA contract grid URL:** What is the URL for the new GA ACA provider network contract grid? | Quick Links custom metadata | Ops |
| 7 | **GA CDS verification URL:** If CDS is required for GA, what is the verification URL? | Quick Links custom metadata | Ops/Legal |

---

# USER STORY 1: Practitioner Participation Form (PRM_PractitionerParticipationForm_English) – State & License

**Persona:** Credentialing Specialist, Developer  
**Priority:** P0  
**OmniScript:** PRM_PractitionerParticipationForm_English  
**Relevant requirements:** FHN-04, FHN-05 (Portal); PIE-02 (License State)

## Story

**As a** Credentialing Specialist,  
**I want** to select Georgia as a state option and the 5 GA counties when entering practitioner participation data for GA providers,  
**So that** I can correctly capture primary address and license information for AmeriHealth Georgia (AHGA) network providers.

**Why it matters:** GA providers will submit via the new Provider Participation Form AH GA. Specialists must be able to enter GA state and county in PIE.

## Technical Section (For Developers)

### Current State (from codebase)

- **PractitionerState** (AddLicenseBlock): Options are PA, NJ, DE, MD. OptionSource: `Address.PRM_State__c`.
- **Location:** `PRM_PractitionerParticipationForm_English_Element_PractitionerState.json`

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **PractitionerState** | OmniScript Element | Add `{"name": "GA", "value": "GA"}` to options array. If optionSource is used, ensure Address.PRM_State__c picklist includes GA. |
| **Primary address state** | OmniScript | If Practitioner Participation Form has primary address with state/county, add Georgia and 5 counties (Fulton, Cobb, Clayton, DeKalb, Gwinnett). *Verify element names during implementation.* |
| **Address.PRM_State__c** | Salesforce Picklist | Add Georgia if PractitionerState uses optionSource. |
| **County picklist** | Salesforce / DataRaptor | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett where county is used. |

### Example (PractitionerState options)

```json
"options": [
    {"name": "PA", "value": "PA"},
    {"name": "NJ", "value": "NJ"},
    {"name": "DE", "value": "DE"},
    {"name": "MD", "value": "MD"},
    {"name": "GA", "value": "GA"}
]
```

## Acceptance Criteria

**Given** the Credentialing Specialist is in PRM_PractitionerParticipationForm_English entering data for a GA provider,  
**When** they select license state or primary address state,  
**Then** Georgia (GA) shall be available.  
**When** they select county (if applicable),  
**Then** Fulton, Cobb, Clayton, DeKalb, Gwinnett shall be available.

---

# USER STORY 2: Provider Change Form (PRM_ProviderChangeForm_English) – Remove Capsite

**Persona:** PDM Specialist, Developer  
**Priority:** P0  
**OmniScript:** PRM_ProviderChangeForm_English  
**Relevant requirements:** FHN-06 (Provider Change Request Form – remove capsite)

## Story

**As a** PDM Specialist,  
**I want** the Provider Change Form to no longer show the Capitation Site section,  
**So that** the form aligns with the updated provider change request requirements (confirmed 2/20).

**Why it matters:** Capsite information is being removed from the Provider Change Request Form.

## Technical Section (For Developers)

### Current State (from codebase)

- **ProviderChangeFormCapitationSite**: Embedded OmniScript shown when `CapitationSite = "Capitation Site"`.
- **Location:** `PRM_ProviderChangeForm_English_Element_ProviderChangeFormCapitationSite.json`

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **ProviderChangeFormCapitationSite** | OmniScript Element | Remove or hide. Options: (a) Remove the element from the flow; (b) Set `show` to always false; (c) Remove Capitation Site from the parent action type options so it is never selected. |

### Recommendation

Remove the ProviderChangeFormCapitationSite element from PRM_ProviderChangeForm_English, and remove "Capitation Site" from any action type/radio options that trigger it.

## Acceptance Criteria

**Given** the PDM Specialist opens PRM_ProviderChangeForm_English,  
**When** they proceed through the form,  
**Then** the Capitation Site section shall not appear.

---

# USER STORY 3: Application Review & PSV – License State (GA)

**Persona:** Credentialing Specialist, Developer  
**Priority:** P0  
**OmniScripts:** PRM_CredApplicationReviewSubOS_English, PRM_PSVSubOsWSNPDB_English, PRM_PSVSubOsTxnyRole_English, PRM_RecredQC_English  
**Relevant requirements:** PIE-02 (License State in Application Review, DEA Verification, CDS Verification)

## Story

**As a** Credentialing Specialist,  
**I want** GA to be a supported value in the license state field across Application Review, DEA Verification, and CDS Verification flows,  
**So that** I can process GA provider applications and verify GA licenses correctly.

**Why it matters:** GA providers will have GA-issued licenses. The system must accept and display GA as a license state.

## Technical Section (For Developers)

### Current State (from codebase)

- **PRM_PSVSubOsWSNPDB_English**: DEAState, CDSState – Text fields, readOnly. Likely populated from CAQH or DataRaptor.
- **PRM_CredApplicationReviewSubOS_English**: CDSVerification, DEA-related elements.
- **PRM_RecredQC_English**: DEAState, CDSState in recred context.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **License state source** | TBD | *Clarify:* If from picklist, add GA to Address.PRM_State__c or relevant picklist. If from PAR form/CAQH, ensure GA is passed through. |
| **DEAState, CDSState** | OmniScript / DataRaptor | If these are display-only from CAQH, no OmniScript change. If there is a select/dropdown for license state, add GA. |
| **Salesforce picklists** | Admin | Add Georgia to any State/License State picklists used by these flows. |

### Flows to verify

- **PRM_CredApplicationReviewSubOS_English** – Initial Application Review, DEA Verification, CDS Verification
- **PRM_PSVSubOsWSNPDB_English** – DEA, CDS (WSNPDB = With Specialty No Pending Denied Board?)
- **PRM_PSVSubOsTxnyRole_English** – Taxonomy/role-based PSV
- **PRM_RecredQC_English** – Recred DEA/CDS

## Acceptance Criteria

**Given** the Credentialing Specialist is in Application Review, DEA Verification, or CDS Verification for a GA provider,  
**When** license state is displayed or selected,  
**Then** GA shall be a valid value. Data shall flow correctly from form/CAQH to Salesforce.

---

# USER STORY 4: PSV & Credentialing – Quick Links (GA Contract Grid, CDS)

**Persona:** Credentialing Specialist, Developer, Admin  
**Priority:** P1  
**OmniScripts:** PRM_RecredQC_English, PRM_PSVSubOsSummary_English, PRM_CredApplicationReviewSubOS_English, PRM_PrimarySourceVerificationReview_English  
**Relevant requirements:** PIE-03, PIE-04 (Quick Links)

## Story

**As a** Credentialing Specialist,  
**I want** quick links in the PSV and credentialing flows to include the GA contract grid and (if required) GA CDS verification,  
**So that** I can access GA-specific verification sources when processing GA providers.

**Why it matters:** Contract grid and CDS verification are state-specific. GA needs its own links.

## Technical Section (For Developers)

### Current State (from codebase)

- **PRMExtractQuickLinks** DataRaptor: Reads from `PRM_Quick_Links__mdt` custom metadata. Filtered by `QuickLinkNames` input.
- **prmDisplayQuickLinks** LWC: Displays quick links in flows.
- **Flows using Quick Links:** PRM_RecredQC_English (CustomLWC2–6), PRM_PSVSubOsSummary_English, PRM_CredApplicationVerificationReview, PRM_PrimarySourceVerificationReview_English.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **PRM_Quick_Links__mdt** | Custom Metadata | Add new records: (a) GA Contract Grid – Label, URL for GA ACA provider network contract grid; (b) GA CDS Verification – if Legal/RPM confirms required. |
| **QuickLinkNames** | Integration Procedure / OmniScript | Ensure GA contract grid and GA CDS (if applicable) are included in the QuickLinkNames array passed to PRMExtractQuickLinks when the flow context is GA. *May require state-based logic.* |
| **State-based Quick Links** | IP / Formula | If quick links vary by state, add logic to include GA-specific links when license state or case state = GA. |

### Example (Custom Metadata)

| Label | PRM_URLLink__c | PRM_NameIfURLNotPresent__c |
|-------|----------------|----------------------------|
| GA Contract Grid | [URL from Ops] | GA ACA Provider Network Contract Grid |
| GA CDS Verification | [URL if required] | GA CDS Verification |

## Acceptance Criteria

**Given** the Credentialing Specialist is in a PSV or credentialing flow for a GA provider,  
**When** they view quick links,  
**Then** the GA contract grid link shall be available.  
**When** CDS verification is required for GA,  
**Then** the GA CDS verification link shall be available.

---

# USER STORY 5: Form Source & Routing (PAR Request – Provider Participation Form AH GA)

**Persona:** Developer, BA  
**Priority:** P0  
**Relevant requirements:** PIE-01 (Form source for GA requests)

## Story

**As a** system,  
**I want** credentialing requests from GA providers to be routed with form source "Provider Participation Form AH GA",  
**So that** the correct form type is associated with GA applications and PIE can auto-populate provider information from the GA form.

**Why it matters:** Form source drives routing and auto-population. GA needs its own form identifier.

## Technical Section (For Developers)

### Notes

- **FHN Portal:** Provider-facing. New form "Provider Participation Form AH GA" will be created there. *Out of scope for OmniScript changes in this codebase.*
- **PIE / FHNatic:** When a GA PAR request is received (PDF or data), the form source must map to "Provider Participation Form AH GA".
- **Possible locations:** Case routing rules, Integration Procedure that creates/updates Case, DataRaptor that maps form type, or configuration in FHNatic.

### Changes (to be confirmed)

| Component | Type | Change |
|-----------|------|--------|
| **Form source mapping** | Configuration / IP | Map GA submissions to "Provider Participation Form AH GA". |
| **Case/Application routing** | Salesforce | Routing rules for GA applications. |
| **Auto-population** | IP / DataRaptor | Ensure GA form fields map to PIE provider fields. |

## Acceptance Criteria

**Given** a GA provider submits a Practitioner Participation Request via the FHN Portal,  
**When** the request is received in FHNatic/PIE,  
**Then** the form source shall be "Provider Participation Form AH GA".  
**When** the credentialing specialist opens the case,  
**Then** provider information shall be auto-populated from the GA form where applicable.

---

# USER STORY 6: State & County Picklists (Salesforce / Shared)

**Persona:** Admin, Developer  
**Priority:** P0  
**Relevant requirements:** FHN-04, FHN-05; Salesforce state/county picklists

## Story

**As an** Admin,  
**I want** Georgia and the 5 GA counties (Fulton, Cobb, Clayton, DeKalb, Gwinnett) added to all relevant state and county picklists,  
**So that** GA can be selected consistently across Address, License State, Service Area, and any other objects that use state/county.

## Technical Section (For Developers)

### Changes

| Object / Field | Change |
|----------------|--------|
| **Address.PRM_State__c** (or equivalent) | Add Georgia |
| **County picklist** (if exists) | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett |
| **Service Area / Network Config** | Add GA and counties if used |
| **License State** (if picklist) | Add GA |

### OmniScripts that may use state/county

- PRM_PractitionerParticipationForm_English
- PRM_ProviderChangeForm_English
- PRM_OffCycleCredentialing_English
- PRM_PDMManualUpdate_English
- PRM_PDMManualChanges_English
- PRM_PSVSubOsTxnyRole_English (PSVPracticeState, PSVPracticeCounty)
- PRM_RecredQC_English
- PRM_AncillaryProviderForm_English

## Acceptance Criteria

**Given** the Admin has added GA and 5 counties to picklists,  
**When** any guided flow or address component uses state or county,  
**Then** Georgia and the 5 counties shall be available where applicable.

---

## Implementation Order

| Order | User Story | Owner |
|-------|------------|-------|
| 1 | US6: State & County Picklists (Salesforce) | Admin |
| 2 | US1: Practitioner Participation Form – State & License | Developer |
| 3 | US2: Provider Change Form – Remove Capsite | Developer |
| 4 | US3: Application Review & PSV – License State | Developer |
| 5 | US4: Quick Links (GA Contract Grid, CDS) | Developer + Admin |
| 6 | US5: Form Source & Routing | Developer / PIE |

---

## Flow → Component Reference (GA)

| Flow | OmniScript | GA Changes |
|------|------------|------------|
| Practitioner Participation Form | PRM_PractitionerParticipationForm_English | PractitionerState + GA; primary address state/county if present |
| Provider Change Form | PRM_ProviderChangeForm_English | Remove ProviderChangeFormCapitationSite |
| Application Review / PSV | PRM_CredApplicationReviewSubOS_English | License state GA |
| DEA / CDS Verification | PRM_PSVSubOsWSNPDB_English | License state GA |
| PSV (Taxonomy/Role) | PRM_PSVSubOsTxnyRole_English | License state; Admitting privileges if GA requires |
| Recred QC | PRM_RecredQC_English | License state; Quick Links |
| Quick Links | PRM_Quick_Links__mdt, PRMExtractQuickLinks | GA contract grid; GA CDS (if required) |

---

## Out of Scope (This Document)

- **FHN Portal:** New AHGA portal version, Provider Participation Form AH GA, "Before You Begin" content, AHGA provider manual link. *Handled separately.*
- **Operational:** GA queue intake, license sources, contract grid creation, training, DLP. *See GA_Internal_Credentialing_Scope_Implementation_Plan.md Part 3.*

---

*Source: 2.20 Internal Credentialing Scope Read Out.pdf, GA_Internal_Credentialing_Scope_Implementation_Plan.md*
