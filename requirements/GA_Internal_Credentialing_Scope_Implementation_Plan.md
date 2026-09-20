# GA Internal Credentialing Scope Expansion – Implementation Plan

---

## Quick Reference

| Area | Change Summary |
|------|----------------|
| **FHN Portal** | New AHGA portal version; GA form; add Georgia + 5 counties (Fulton, Cobb, Clayton, DeKalb, Gwinnett) |
| **PIE Guided Flows** | New form source (Provider Participation Form AH GA); GA license state; new quick links (contract grid, CDS) |
| **Salesforce / FHNatic** | Add GA to state/county picklists; GA form routing; record types if needed |
| **OmniScript / IPs** | Add GA and counties to state/county options; form routing logic |
| **Operations** | GA queue intake; new license sources; GA contract grid; training |

**Target Counties:** Fulton, Cobb, Clayton, DeKalb, Gwinnett

---

## Executive Summary

This document describes the implementation of expanding Internal Credentialing scope to **Georgia (GA)** for the **AmeriHealth Georgia (AHGA)** network. The expansion requires changes across the FHN Portal, PIE guided flows, Salesforce/FHNatic, OmniScript/Integration Procedures, and operational processes.

**Source Document:** 2.20 Internal Credentialing Scope Read Out.pdf

---

## Part 1: Background & Current State

### 1.1 Current Internal Credentialing Process

1. Provider submits Practitioner Participation Request form via FHN Portal
2. Data validated in FHNatic and keyed into PIE
3. Credentialing specialist reviews in FHNatic
4. Specialist enters data into Practitioner Participation Form in PIE
5. Application review (CAQH verification, taxonomy, role, education, attachments)
6. Case manager updated to PSV stage; specialist assigned
7. PSV specialist completes review; case auto-assigned to QC
8. QC completes; committee review case created
9. Committee approves → reporting specialists approve in Salesforce → PDM team; or moves to final development if not approved

### 1.2 Current Geographic Scope

- **States:** PA, NJ, DE, MD
- **Forms:** State-specific Practitioner Participation forms
- **Portal:** State-specific FHN portal versions

### 1.3 Target State for GA

- **New State:** Georgia (GA)
- **Target Counties:** Fulton, Cobb, Clayton, DeKalb, Gwinnett
- **New Form:** Provider Participation Form AH GA
- **New Portal:** AHGA version of FHN portal

---

## Part 2: Requirements by Category

### 2.1 FHN Portal Requirements

| ID | Category | Requirement | Notes |
|----|----------|-------------|-------|
| FHN-01 | Website | Create new AHGA version of FHN portal | Same structure; modify content and form structure |
| FHN-02 | Provider Participation Form | Add GA service locations to "Before You Begin" | Fulton, Cobb, Clayton, DeKalb, Gwinnett |
| FHN-03 | Provider Participation Form | Replace AHNJ link with AHGA provider manual link | Owner TBD; link embedded in form |
| FHN-04 | Provider Participation Form | Add Georgia as state option in primary address | Currently only PA, NJ, DE, MD |
| FHN-05 | Provider Participation Form | Add counties as options in primary address | Fulton, Cobb, Clayton, DeKalb, Gwinnett |
| FHN-06 | Provider Change Request Form | Remove capsite information | Confirmed 2/20 |

### 2.2 PIE Guided Flow Requirements

| ID | Category | Requirement | Notes |
|----|----------|-------------|-------|
| PIE-01 | PAR Request Form | Update form source to "Provider Participation Form AH GA" for GA requests | PDF format; auto-populate provider info |
| PIE-02 | License State | Add GA as supported value in license state field | Application Review, DEA Verification, CDS Verification flows |
| PIE-03 | Quick Links | Add link to new GA contract grid | New ACA provider network contract grid |
| PIE-04 | Quick Links | Add GA CDS verification link (if required) | Legal/RPM to decide; required for all states except PA today |

### 2.3 Operational / Process Requirements

| ID | Category | Requirement | Notes |
|----|----------|-------------|-------|
| OPS-01 | Queue | Credentialing specialists intake GA applications | In addition to PA, NJ, DE, MD |
| OPS-02 | License Sources | New GA license sources accessible to specialists | Training / DLP may be required |
| OPS-03 | Contract Grid | New GA contract grid for PSV | Process same as PA/NJ |
| OPS-04 | Board Information | Access GA board info via national sources | Same process as PA/NJ |
| OPS-05 | State Requirements | Define GA-specific field applicability in guided flows | Document which fields apply |
| OPS-06 | Admitting Privileges | Determine if required for GA | Today only DE requires |
| OPS-07 | CDS Verification | Determine if required for GA | Today required for all except PA |

---

## Part 3: Technical Implementation

### 3.1 FHN Portal Changes

| Component | Change |
|-----------|--------|
| **Portal Instance** | Create/clone AHGA portal; update branding and content |
| **Provider Participation Form** | New form variant or new form type for GA |
| **State Picklist** | Add "Georgia" |
| **County Picklist** | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett |
| **"Before You Begin"** | Update with GA service locations and counties |
| **Provider Manual Link** | Replace AHNJ with AHGA link |
| **Provider Change Request Form** | Remove capsite fields/sections |

### 3.2 Salesforce / FHNatic Changes

| Object / Area | Change |
|---------------|--------|
| **State Picklists** | Add Georgia (e.g., Address, License State, Service Area) |
| **County Picklists** | Add Fulton, Cobb, Clayton, DeKalb, Gwinnett |
| **Practitioner Participation Form** | New GA form type or record type |
| **Case/Application Routing** | Routing rules for GA applications |
| **Service Area / Network Config** | GA network and county configuration |

### 3.3 OmniScript / Integration Procedure Changes

| Component | Change |
|-----------|--------|
| **State Options** | Add Georgia to state dropdowns/radio in relevant OmniScripts |
| **County Options** | Add 5 GA counties where county selection exists |
| **Form Routing** | Logic to route GA submissions to correct form and PIE flow |
| **DataRaptors / IPs** | Update if state/county filters exist |

**OmniScripts to Review:**
- Practitioner Participation Form (or equivalent)
- Provider Change Request Form
- Any form with primary address (state, county)

### 3.4 PIE Integration

| Area | Change |
|-----|--------|
| **Form Source Mapping** | Map "Provider Participation Form AH GA" to PIE intake |
| **Auto-Population** | Ensure GA form fields map to PIE provider fields |
| **License State Field** | Add GA; verify data source (form vs. Salesforce) |
| **Quick Links** | Add GA contract grid URL |
| **Quick Links** | Add GA CDS verification URL (if applicable) |

---

## Part 4: Implementation Phases

### Phase 1: Configuration & Data (Weeks 1–2)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Add Georgia to all state picklists | Dev | Deployed picklist values |
| Add 5 GA counties to county picklists | Dev | Deployed picklist values |
| Create GA Practitioner Participation Form | Dev/BA | New form in portal |
| Update "Before You Begin" with GA locations | Content | Updated form content |
| Replace AHNJ link with AHGA provider manual | Content/BA | Updated link |
| Remove capsite from Provider Change Request Form | Dev | Updated form |

### Phase 2: PIE Integration (Weeks 3–4)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Configure PIE form source for GA form | PIE/Dev | GA form recognized |
| Add GA to license state in guided flows | PIE/Dev | GA selectable |
| Create GA contract grid (Operations) | Ops | Excel/document |
| Add GA contract grid link to quick links | PIE/Dev | Link in flow |
| Determine CDS requirement for GA (Legal/RPM) | Legal | Decision documented |
| Add GA CDS link if required | PIE/Dev | Link in flow |

### Phase 3: Operational Readiness (Weeks 5–6)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Identify GA state-specific license sources | Ops/Compliance | Source list |
| Create/maintain GA contract grid | Ops | Contract grid |
| Define GA field applicability (admitting privileges, CDS, etc.) | Ops/Compliance | Requirements doc |
| Training for credentialing specialists on GA | Ops | Training completed |
| DLP updates for GA sources | Ops | DLP updated |

### Phase 4: Testing & Go-Live (Weeks 7–8)

| Task | Owner | Deliverable |
|------|-------|-------------|
| End-to-end testing (Portal → FHNatic → PIE) | QA | Test results |
| UAT with credentialing specialists | Ops | UAT sign-off |
| Go-live | PM | Live in production |
| Post-go-live monitoring | Ops | Issue log |

---

## Part 5: Open Questions & Decisions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | Who owns the AHGA provider manual and what updates are needed? | TBD | Open |
| 2 | How is license state sourced today (form vs. Salesforce)? | Technical | Open |
| 3 | Are Salesforce schema changes required for GA? | Salesforce | Open |
| 4 | Is admitting privileges required for GA providers? | Legal/RPM | Open |
| 5 | Is CDS verification required for Georgia? | Legal/RPM | Open |
| 6 | What are the GA state-specific licensure sources? | Ops/Compliance | Open |
| 7 | What is the process for creating/maintaining the GA contract grid? | Ops | Open |

---

## Part 6: Working Assumptions

1. PIE will support intake of the new GA PAR provider request form and auto-populate provider information, consistent with PA and NJ.
2. Relevant CAQH data for GA providers will be accessible for credentialing review and verification.
3. Internal credentialing for GA will follow the existing PA and NJ workflow, with configuration updates only.
4. National verification sources (licensure, board certification) can be used for GA; state-specific licensure sources will be identified and made accessible.

---

## Part 7: Risk & Dependencies

| Risk | Mitigation |
|------|------------|
| GA-specific requirements not defined | Engage Legal/RPM early for admitting privileges and CDS |
| License sources not available | Identify sources in Phase 3; plan training |
| Form structure differs from PA/NJ | Align GA form with existing form structure for PIE compatibility |

---

## Part 8: File / Component Reference

**User Stories (flow-centric):** See `GA_Internal_Credentialing_User_Stories.md` for OmniScript-guided flow user stories with technical details and examples.

| Area | Files / Components |
|------|---------------------|
| FHN Portal | TBD (external) |
| **Practitioner Participation Form** | PRM_PractitionerParticipationForm_English – PractitionerState (PA,NJ,DE,MD → add GA) |
| **Provider Change Form** | PRM_ProviderChangeForm_English – ProviderChangeFormCapitationSite (remove) |
| **Application Review / PSV** | PRM_CredApplicationReviewSubOS_English, PRM_PSVSubOsWSNPDB_English, PRM_PSVSubOsTxnyRole_English, PRM_RecredQC_English – License state GA |
| **Quick Links** | PRM_Quick_Links__mdt, PRMExtractQuickLinks – GA contract grid, GA CDS |
| DataRaptors | State/county filters if present |
| Salesforce | State/County picklists, routing rules |
| PIE | Form source config, guided flow quick links |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | TBD | TBD | Initial implementation plan |

---

*Source: 2.20 Internal Credentialing Scope Read Out.pdf*
