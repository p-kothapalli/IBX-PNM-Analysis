# Master Development Plan: Credentialing Flows LWC Redesign
## OmniScript → Tile-Based LWC Architecture

---

> **🔄 Architecture revision — Application Review + Initial Cred PSV are now ONE combined flow (ratified by business).** Business confirmed that the **Application Review** process and the **Initial Cred PSV Review** process are performed together for initial credentialing, so they are merged into a single unified **"Initial Credentialing Review"** dashboard with one de-duplicated tile set. The four overlapping tiles — **Practitioner Info** (Review Application ⟷ PSV Practitioner Info), **Taxonomy & Specialty**, **File Upload**, and **Final Submit** (Final Confirmation) — are merged into one tile each. Net: **17 tiles in one dashboard** (down from 20 across the two former flows). The downstream flows (**Re-Cred PSV, Initial Cred QC, Re-Cred PSV QC, PDA QC**) **remain separate**; the QC flow now **wraps the combined flow's components**. This banner + §1–§5 reflect the revision.

---

## 1. Program Overview

### Business Problem

Business users performing credentialing verification (Application Review, PSV, QC Reviews) struggle with the current OmniScript-based flows because:

1. **4MB Payload Limit** — "Save for Later" fails with large datasets, forcing users to restart hours of work
2. **All-or-Nothing Sessions** — 2-4 hour verification sessions with zero pause/resume capability
3. **No Visual Progress** — Users cannot see which sections are complete vs. pending
4. **Read-Only Fields** — Users cannot edit Salesforce fields inline, forcing them to exit and manually update records externally
5. **Linear Flow** — Must follow sequential steps even when sections are independent
6. **No Collaboration** — A single reviewer must handle the entire flow alone

### Solution

Break each OmniScript into **independent, clickable tiles** within a reusable LWC dashboard framework. Each tile:
- Opens in a modal for focused review
- Saves independently to Salesforce on submit (no 4MB limit)
- Can be completed in any order
- Supports resume from any device (session state persisted in custom objects)
- Shows visual progress (pending / in-progress / completed / error)

> **Note on CAQH Data:** CAQH data is always **display-only** (read-only reference). Users review CAQH data side-by-side with Salesforce data and edit only the Salesforce fields. CAQH data cannot be modified from within these flows.

### Development Acceleration: Cursor AI-Assisted Building

All LWC components, Apex controllers, and boilerplate will be built with **Cursor AI assistance**, significantly accelerating:
- Component scaffolding and standard LWC patterns (~50% faster)
- Repetitive tile patterns (form fields, datatables, modals) (~50% faster)
- Apex controller SOQL/DML patterns (~40% faster)
- Unit test generation (~40% faster)

**Testing and UAT timelines remain unchanged** — these require manual validation with real business data.

### Flows Being Redesigned

| # | Flow | Current OmniScript(s) | Tiles | Est. Timeline |
|---|------|-------------------|-------|---------------|
| 1 | **Initial Credentialing Review (Combined)** — *merges Application Review + Initial Cred PSV* | `PRM_InitialCredentialAppReview_English` **+** `PRM_PrimarySourceVerificationReview_English` | 17 | 10.5 weeks |
| 2 | **Re-Cred PSV Review** | `PRM_PrimarySourceVerificationReview_English` (`IsRecredentialing = true`) | 11 | 3 weeks |
| 3 | **Initial Cred QC Review** *(wraps the combined flow)* | `PRM_PrimarySourceVerificationReview_English` (`CaseType = "QC Review"`) | 15 | 2.5 weeks |
| 4 | **Re-Cred PSV QC Review** | `PRM_PrimarySourceVerificationReview_English` (`IsRecredentialing = true` + `CaseType = "QC Review"`) | 11 | 1.5 weeks |
| 5 | **PDA QC Review (Network Mgmt QC)** | `PRM_InitialCredPDAQC_English` | 7 | 5 weeks |

**Total Sequential:** ~22.5 weeks | **Total Parallel (recommended):** ~12 weeks

> **What changed:** former Flow 1 (Application Review, 10 tiles / 8 wks) and Flow 2 (Initial Cred PSV, 10 tiles / 5 wks) are now **one combined Flow 1** (17 tiles / 10.5 wks) — saving ~2.5 weeks by eliminating the duplicate framework-extend phase, the four duplicated overlapping tiles, and a redundant test/UAT cycle. Downstream flows are renumbered 2–5.

---

## 2. Architecture Overview

### Shared Framework Components (Built Once, Reused 100% Across All 5 Flows)

| Component | Purpose | Reuse % |
|-----------|---------|---------|
| `prm_verificationDashboard` | Parent container — tile grid, progress tracking, session orchestration | 100% |
| `prm_progressHeader` | Progress bar, session info (last saved timestamp, reviewer name) | 100% |
| `prm_verificationTile` | Individual tile card — status badge, icon, click handler | 100% |
| `prm_verificationModal` | Modal wrapper — dynamic child component injection, Save/Submit/Cancel actions | 100% |
| `prm_navigationFooter` | Resume Later / Save & Exit / Help buttons | 100% |
| `prm_qcWrapper` | Generic QC wrapper — displays PSV data (read-only) + QC verification (editable) | 100% (QC flows) |

### Shared Sub-Components (Built Once, Configured Per Flow)

| Sub-Component | Used By | Reuse % |
|---------------|---------|---------|
| `prm_practitionerDemographics` | Initial Cred Review, Cred QC, PDA QC | 80% |
| `prm_taxonomyVerification` | Initial Cred Review, Cred QC | 100% |
| `prm_fileUpload` | Initial Cred Review, Cred QC, Re-Cred PSV | 100% |
| `prm_finalSubmitBase` | Initial Cred Review, Cred QC, PDA QC (extended per flow) | 80% |

### Custom Objects (Built Once, Shared Across All Flows)

| Object | Purpose |
|--------|---------|
| `PRM_VerificationSession__c` | Tracks session state (Case Manager, Flow Type, Progress, Draft JSON) |
| `PRM_VerificationTileStatus__c` | Tracks each tile's status (Tile ID, Completed By, Verification Data JSON, Notes) |

`Flow_Type__c` picklist values: `InitialCredReview` *(combined App Review + PSV)*, `ReCredPSVReview`, `InitialCredQCReview`, `ReCredPSVQCReview`, `PDAQCReview`

> **Migration note:** the former `ApplicationReview` and `PSVReview` picklist values are replaced by the single `InitialCredReview` value (former `PSVQCReview` → `InitialCredQCReview`). Any seed/config or in-flight session records referencing the old values must be re-mapped on cutover.

### Apex Controllers (One Per Flow, Shared Patterns)

| Controller | Flow | Key Methods |
|------------|------|-------------|
| `CredentialingReviewController` *(merges `ApplicationReviewController` + `PSVReviewController`)* | Initial Credentialing Review (Combined) | `fetchCredentialingReviewData` (one fetch for all 17 tiles), `saveVerificationTileStatus`, `submitCredentialingReview`, `checkAsyncAddressProcessing` |
| `ReCredPSVReviewController` | Re-Cred PSV | `fetchReCredPSVReviewData` + Re-Cred routing logic (Medical Director, Final Development) |
| `CredQCReviewController` | Initial Cred QC | `fetchCredQCReviewData`, `saveQCVerificationTileStatus`, `submitCredQCReview` (wraps the combined flow's tiles read-only) |
| `ReCredPSVQCReviewController` | Re-Cred PSV QC | Extends Cred QC + Board Cert QC, CMS Preclusion QC |
| `QCReviewController` | PDA QC | `fetchQCReviewData`, `fetchAvailableNetworks`, `fetchAvailableInfoCodes`, `fetchCapitationSites`, `submitQCReview` |
| `CAQHIntegrationController` | Combined flow, Re-Cred (shared) | `validateCAQHProvider`, `fetchCAQHData` |

### Integration Procedures (Existing — Reused)

| IP | Used By | Elements |
|----|---------|----------|
| `PRM_ReviewPSVCaseRecordsUpdate` | Initial Cred Review (Combined), Cred QC, Re-Cred PSV, Re-Cred PSV QC | 70-90+ elements |
| `PRM_NetworkManagementQCUpdate` | PDA QC | Custom for network/info code/directory updates |

> **Single IP for the combined flow:** both former flows already submitted through the **same** `PRM_ReviewPSVCaseRecordsUpdate` IP, so the combined Final Submit calls it **once** with the aggregated payload from all 17 tiles — no IP changes required.

### CAQH Data Handling (All Flows)

**CAQH data is always read-only.** In every tile that displays CAQH information:
- **Left panel / top section:** CAQH data displayed as read-only reference (no edit controls)
- **Right panel / bottom section:** Salesforce data displayed with editable fields
- Users compare CAQH against Salesforce and update Salesforce fields as needed
- Verification status (Verified / Needs Review / Rejected) is set by the reviewer after comparison

---

## 3. Detailed Flow-by-Flow Development Plan

---

### FLOW 1: Initial Credentialing Review (Combined — Builds Shared Framework)

**Current OmniScripts (both replaced by this one flow):** `PRM_InitialCredentialAppReview_English` **+** `PRM_PrimarySourceVerificationReview_English` (186+ elements)
**Tiles:** 17 (merged, de-duplicated union of the former App Review + PSV tile sets)
**Timeline:** 10.5 weeks (accelerated with Cursor AI)
**Priority:** FIRST (all other flows depend on this — it builds the shared framework + every reusable tile)

> **Why combined:** business performs Application Review and PSV together for initial credentialing. One dashboard, one session, one Final Submit (→ same `PRM_ReviewPSVCaseRecordsUpdate` IP both flows already used). The reviewer verifies all 17 tiles in any order and submits once.

#### Combined Tile Inventory (17 tiles)

| # | Tile | Component | Origin | Data Sources | Complexity | Est. Days |
|---|------|-----------|--------|-------------|------------|-----------|
| 1 | Practitioner Info | `prm_practitionerInfo` | **Merged** (Review Application + PSV Practitioner Info) | Account, IndividualApplication, CAQH (read-only) — incl. Gender, Email, Degree, Telehealth | Medium | 1.5 |
| 2 | Taxonomy & Specialty | `prm_taxonomyVerification` | **Merged** (App Review tile + PSV embedded) | HealthcareProviderTaxonomy, CAQH (read-only); PCP/Specialist/Dual role | Medium | 2 |
| 3 | Verify Education | `prm_reviewEducation` | App Review | PersonEducation, CAQH (read-only) | Medium | 2 |
| 4 | Verify License (SBRD) | `prm_reviewLicense` | App Review | BusinessLicense, CAQH (read-only) | High | 3 |
| 5 | Verify DEA | `prm_reviewDEA` | App Review | BusinessLicense (DEA), CAQH (read-only) | Medium | 1.5 |
| 6 | Verify CDS | `prm_reviewCDS` | App Review | BusinessLicense (CDS), CAQH (read-only) | Medium | 1.5 |
| 7 | Verify Work History | `prm_reviewWorkHistory` | App Review | CAQH (display only) | Low | 1 |
| 8 | Verify Malpractice | `prm_reviewMalpractice` | App Review | CAQH (display only) | Medium | 2 |
| 9 | Group/Practice | `prm_psvGroupPractice` | PSV | CareProviderFacilityGroup, Facility, CAQH (read-only) | Medium | 1 |
| 10 | Address Verification | `prm_psvAddressVerification` | PSV | Address, HealthcarePractitionerFacility, CAQH | **HIGH** — 100+ addresses, pagination, async | 3 |
| 11 | Demographics & Diversity | `prm_psvDemographicsDiversity` | PSV | Account, IndividualApplication, CAQH (read-only) | Low | 1 |
| 12 | Languages Spoken | `prm_psvLanguagesSpoken` | PSV | LanguageSkill, CAQH (read-only) | Low | 1 |
| 13 | Contact Information | `prm_psvContactInformation` | PSV | Account, IndividualApplication, CAQH (read-only) | Low | 1 |
| 14 | Board Certification | `prm_psvBoardCertification` | PSV | BoardCertification, CAQH (read-only); `showWhen` Re-Cred or applicable | Low | 1 |
| 15 | Contract Status | `prm_psvContractStatus` | PSV | Contract, PractitionerRole | Medium | 1 |
| 16 | Upload Attachments | `prm_fileUpload` | Shared | ContentDocumentLink | Low | 0.5 |
| 17 | Final Submit | `prm_finalSubmit` | **Merged** (Final Submit + Final Confirmation) | Aggregated tile data, Case, Case Manager | High | 3 |

**Sum of tile build effort:** ~27 days. (The four merged tiles — Practitioner Info, Taxonomy, File Upload, Final Submit — are built **once** instead of twice.)

#### Phase Breakdown

**Phase 1: Foundation & Shared Components (Weeks 1-3)**

| Week | Deliverables | Details | Days |
|------|-------------|---------|------|
| **Week 1** | Custom Objects + Dashboard + Framework | Deploy `PRM_VerificationSession__c` and `PRM_VerificationTileStatus__c`. Build `prm_verificationDashboard` parent container with tile grid layout, `@api recordId` binding to Case Manager. Build `prm_progressHeader` (progress bar, session info). Build `prm_verificationTile` (tile card with status badges: pending/in-progress/completed/error, click handler, warning badges). Build `prm_verificationModal` (dynamic child component injection via `lwc:component`, Save Draft / Submit & Close / Submit & Next actions, unsaved changes warning). Build `prm_navigationFooter` (Resume Later, Save & Exit, Help). Cursor AI accelerates all scaffolding. | 5 |
| **Week 2** | Shared Sub-Components | Build `prm_practitionerDemographics` (Name, NPI, DOB, CAQH ID + Gender, Email, Degree, Telehealth — configurable via `showFields`; CAQH section read-only, SF section editable). Build `prm_taxonomyVerification` (specialty lookup, taxonomy code validation, PCP/Specialist/Dual role, Lightning Datatable with row actions). Build `prm_fileUpload` (drag-and-drop, multi-file, type restrictions, preview, ContentDocumentLink creation). | 5 |
| **Week 3** | Combined Apex + Final Submit Base | Build `CredentialingReviewController` Apex (`fetchCredentialingReviewData` — one fetch covering all 17 tiles' CAQH + SF data; `saveVerificationTileStatus`; `submitCredentialingReview`; `checkAsyncAddressProcessing`). Build `CAQHIntegrationController` (`validateCAQHProvider`, `fetchCAQHData`). Build `prm_finalSubmitBase` (tile summary table, validation — all required tiles completed, outcome selection, notes). Unit tests for Apex (75%+ coverage). Cursor AI generates test stubs. | 5 |

**Phase 2: Combined Tiles (Weeks 4-8)**

| Week | Deliverables | Details | Days |
|------|-------------|---------|------|
| **Week 4** | Tiles 1-2 (merged) + Tile 3 | Tile 1: `prm_practitionerInfo` — uses `prm_practitionerDemographics` (full field set), CAQH (read-only) vs SF (editable) side-by-side, verification status + notes. Tile 2: `prm_taxonomyVerification` as a tile — CAQH specialty display (read-only), add/remove/update SF taxonomy records, Practitioner Role radio. Tile 3: `prm_reviewEducation` — PersonEducation CRUD (SF), CAQH education read-only, institution lookup, degree picklist, date validation. | 5 |
| **Week 5** | Tiles 4-8 (App Review credentials) | Tile 4: `prm_reviewLicense` — BusinessLicense CRUD (SF), CAQH read-only, state board quick links, duplicate detection, service area validation (PA/NJ/DE). Tile 5: `prm_reviewDEA`. Tile 6: `prm_reviewCDS`. Tile 7: `prm_reviewWorkHistory` (CAQH display-only, employer timeline). Tile 8: `prm_reviewMalpractice` (CAQH carrier display read-only; policy #, coverage, self-insured flag editable). | 5 |
| **Week 6** | Tiles 9-13 (PSV core) | Tile 9: `prm_psvGroupPractice` (group lookup, Group NPI, Tax ID, Practice Type). Tile 10: `prm_psvAddressVerification` Part 1 (layout, pagination, mini-modal per address). Tile 11: `prm_psvDemographicsDiversity` (privacy banner; Hispanic/Latino, Racial/Cultural Identity, Pronouns, Affirming Care). Tile 12: `prm_psvLanguagesSpoken`. Tile 13: `prm_psvContactInformation`. | 5 |
| **Week 7** | Tiles 10 (cont), 14-17 | Tile 10 Part 2: `prm_psvAddressVerification` async processing + duplicate detection (1.5d). Tile 14: `prm_psvBoardCertification` (0.5d). Tile 15: `prm_psvContractStatus` (1d — NPI auto-validation, network assignment). Tile 16: wire `prm_fileUpload` (0.5d). Tile 17: `prm_finalSubmit` extends `prm_finalSubmitBase` — combined outcomes (Approved, Returned for QC, Returned to Outreach), CAQH validation checkbox, single `PRM_ReviewPSVCaseRecordsUpdate` IP call (1.5d). | 5 |
| **Week 8** | Integration Testing | Wire all 17 tiles end-to-end. Test full flow: Load → Verify → Save per tile → Resume → Final Submit. Realistic data (50+ licenses, 100+ addresses, CAQH payloads). Fix integration bugs. | 5 |

**Phase 3: Testing & Refinement (Weeks 9-10.5)**

| Week | Deliverables | Details | Days |
|------|-------------|---------|------|
| **Week 9** | Performance + Async | Jest unit tests for each LWC tile (Cursor AI generates stubs). Async address processing with 100+ addresses. Performance testing: page load < 3s, tile save < 2s, resume < 3s. Network-failure recovery. | 5 |
| **Week 10** | UAT | UAT with both App Review **and** PSV business reviewers (one combined flow). Bug fixes. Final regression. | 5 |
| **Week 10.5** | Stabilization | Buffer for UAT fixes + deployment prep. | 2.5 |

**Combined Flow Deliverables Summary:**
- 6 framework components (reused by all flows)
- 4 shared sub-components (reused by 3+ flows)
- 2 custom objects (reused by all flows)
- 15 tile components (2 merged + 6 App-Review-origin + 7 PSV-origin; File Upload reuses a sub-component)
- 1 combined Apex controller (`CredentialingReviewController`) + `CAQHIntegrationController`
- ~52 total working days (vs 65 for the two former flows = ~13 days / 2.5 weeks saved)

---

### FLOW 2: Re-Cred PSV Review

**Current OmniScript:** Same as PSV but with `IsRecredentialing = true`
**Tiles:** 11 (8 reused from Initial Cred PSV + 3 new)
**Timeline:** 3 weeks (accelerated with Cursor AI)
**Dependency:** Initial Cred PSV must be complete

#### What's New vs Initial Cred PSV

| New Tile | Component | Purpose | Est. Days |
|----------|-----------|---------|-----------|
| Board Certification | `prm_reCredBoardCertification` | CAQH board cert displayed read-only, SF board cert editable, add/remove certs, expiration warnings, verification radio (Data Looks Good / Not Applicable / Missing Info) | 2 |
| CMS Preclusion Review | `prm_reCredCMSPreclusionReview` | Checkbox + reason picklist + notes, routes to CMS screening | 0.5 |
| Re-Cred Final Confirmation | `prm_reCredFinalConfirmation` | Extends `prm_finalSubmitBase` with Re-Cred routing: Medical Director Review / PSV QC / Provider Outreach / Final Development | 1 |

#### Phase Breakdown

| Week | Deliverables | Days |
|------|-------------|------|
| **Week 1** | Configure 11 Re-Cred tiles, wire Re-Cred DataRaptor transforms (`DRTransformReCredData`, `DRTransformRecredFiles`). Build `ReCredPSVReviewController` Apex + unit tests. Build `prm_reCredBoardCertification` (2d) — CAQH display (read-only) + SF edit + verification status + add/remove + expiration warnings. | 5 |
| **Week 2** | Build `prm_reCredCMSPreclusionReview` (0.5d). Build `prm_reCredFinalConfirmation` (1d) — Medical Director / QC / Outreach / Final Dev routing. Re-Cred file upload integration (configure `showFileNotes` for Re-Cred). Integration testing: all 11 tiles, routing logic, resume, 100+ addresses + board certs. Bug fixes. | 5 |
| **Week 3** | UAT with Re-Cred specialists (2d), bug fixes (2d), deployment prep (1d). | 5 |

**Re-Cred PSV Deliverables:**
- 3 new Re-Cred-specific tile components
- 8 tiles reused 100% from Initial Cred PSV
- 1 Apex controller
- 15 total working days

---

### FLOW 3: Initial Cred QC Review (wraps the combined flow)

**Current OmniScript:** Same combined OmniScripts with `CaseType = "QC Review"`
**Tiles:** 15 (14 QC-wrapped verification tiles + 1 QC Summary)
**Timeline:** 2.5 weeks (accelerated with Cursor AI)
**Dependency:** **Combined Initial Cred Review (Flow 1) must be complete** — QC wraps its verification components read-only

#### Key Architecture: QC Wrapper Pattern

Instead of building unique QC components, build **1 reusable QC wrapper** (`prm_qcWrapper`) that:
- Displays the combined flow's verified data in a read-only section (top) — includes CAQH data the reviewer saw
- Adds QC verification radio + notes in an editable section (bottom)
- Accepts **any combined-flow verification component** as a child for the display section
- QC verification options: `Data Looks Good` / `Not Applicable` / `Missing Information`

**Result:** Each QC tile = combined-flow component (read-only) + QC Wrapper (editable) = ~0.25 days per tile instead of 2-3 days

#### Tile Inventory

QC wraps the **14 verification tiles** of the combined flow (tiles 1-15 minus File Upload, which is reused as-is) plus a QC Summary. Each wrapped tile is a thin config over `prm_qcWrapper` (`prm_qc<TileName>` ≈ 0.25d each):

| # | QC Tile | Wraps Combined-Flow Component | Est. Days |
|---|---------|-------------------------------|-----------|
| 1 | Practitioner Info QC | `prm_practitionerInfo` (read-only) | 0.25 |
| 2 | Taxonomy QC | `prm_taxonomyVerification` (read-only) | 0.25 |
| 3 | Education QC | `prm_reviewEducation` (read-only) | 0.25 |
| 4 | License QC | `prm_reviewLicense` (read-only) | 0.25 |
| 5 | DEA QC | `prm_reviewDEA` (read-only) | 0.25 |
| 6 | CDS QC | `prm_reviewCDS` (read-only) | 0.25 |
| 7 | Work History QC | `prm_reviewWorkHistory` (read-only) | 0.25 |
| 8 | Malpractice QC | `prm_reviewMalpractice` (read-only) | 0.25 |
| 9 | Group/Practice QC | `prm_psvGroupPractice` (read-only) | 0.25 |
| 10 | Address QC | `prm_psvAddressVerification` (read-only) | 0.25 |
| 11 | Demographics QC | `prm_psvDemographicsDiversity` (read-only) | 0.25 |
| 12 | Languages QC | `prm_psvLanguagesSpoken` (read-only) | 0.25 |
| 13 | Contact QC | `prm_psvContactInformation` (read-only) | 0.25 |
| 14 | Contract/Board QC | `prm_psvContractStatus` + `prm_psvBoardCertification` (read-only) | 0.25 |
| 15 | Cred QC Summary | `prm_credQCSummary` — QC outcome (Approved / Returned to Review / Needs More Info), error reasons multi-select, tile status summary | 1.5 |

#### Phase Breakdown

| Week | Deliverables | Days |
|------|-------------|------|
| **Week 1** | Build `prm_qcWrapper` reusable component (2d): two-section layout (verified display + QC verification), radio buttons, conditional notes requirement, auto-populate reviewer/date. Configure the 15 Cred QC tiles. Build `CredQCReviewController` Apex (1d). Apply QC wrapper to the 14 combined-flow tiles (2d, Cursor AI handles boilerplate). | 5 |
| **Week 2** | Build `prm_credQCSummary` (1.5d) — tile status summary table, QC outcome radio, error reasons multi-select, validation rules. Integration testing (2d) — full QC flow with realistic combined-flow data, resume. Bug fixes + polish (1.5d). | 5 |
| **Week 2.5** | Buffer for the larger wrapped tile set (14 vs 8). | 2.5 |

**Cred QC Deliverables:**
- 1 reusable QC wrapper component (used by all QC flows)
- 14 QC tile configurations (wrap the combined flow's components)
- 1 new QC Summary component
- 1 Apex controller
- 12.5 total working days

---

### FLOW 4: Re-Cred PSV QC Review

**Current OmniScript:** Same PSV OmniScript with `IsRecredentialing = true` AND `CaseType = "QC Review"`
**Tiles:** 11 (8 reused from Initial Cred QC + 3 new)
**Timeline:** 1.5 weeks (accelerated with Cursor AI)
**Dependency:** Initial Cred QC + Re-Cred PSV must be complete

#### What's New vs Initial Cred QC

| New Tile | Component | Wraps | Purpose | Est. Days |
|----------|-----------|-------|---------|-----------|
| Board Cert QC | `prm_reCredQCBoardCertification` | `prm_reCredBoardCertification` (read-only) | QC verifies Re-Cred board cert decisions | 0.5 |
| CMS Preclusion QC | `prm_reCredQCCMSPreclusionReview` | `prm_reCredCMSPreclusionReview` (read-only) | QC verifies CMS preclusion flag | 0.25 |
| Re-Cred QC Summary | `prm_reCredPsvQCSummary` | Extends `prm_credQCSummary` | Re-Cred routing + 2 additional error reasons (Board Cert Issues, CMS Preclusion Incomplete) | 0.5 |

#### Phase Breakdown

| Week | Deliverables | Days |
|------|-------------|------|
| **Week 1** | Configure 11 Re-Cred PSV QC tiles. Build 3 Re-Cred QC tiles (1.25d total — Cursor AI handles repetitive wrapper pattern). Build `ReCredPSVQCReviewController` Apex (1d). Integration testing (1.75d) — all 11 tiles, routing, resume. Bug fixes + deployment prep (1d). | 5 |
| **Week 2 (partial)** | Performance testing (1d). Final UAT validation (1.5d). | 2.5 |

**Re-Cred PSV QC Deliverables:**
- 3 new Re-Cred QC-specific components
- 8 tiles reused 100% from Initial Cred QC
- 1 Apex controller
- 7.5 total working days

---

### FLOW 5: PDA QC Review (Network Management QC)

**Current OmniScript:** `PRM_InitialCredPDAQC_English`
**Tiles:** 7
**Timeline:** 5 weeks (accelerated with Cursor AI)
**Dependency:** Framework from the combined flow (Flow 1) must be complete (can run in parallel with the combined flow's tile build)

#### Tile Inventory

| # | Tile | Component | Reuse | Complexity | Est. Days |
|---|------|-----------|-------|------------|-----------|
| 1 | Practitioner Summary | `prm_qcPractitionerSummary` | `prm_practitionerDemographics` (60%) | Low | 1 |
| 2 | Specialties & Privileges | `prm_qcSpecialtiesPrivileges` | None (new) | Medium | 2 |
| 3 | Practice Location Networks | `prm_qcPracticeLocationNetworks` | None (new) | **HIGHEST** | 5 |
| 4 | Practitioner Networks | `prm_qcPractitionerNetworks` | None (new) | High | 2 |
| 5 | Directory Indicators | `prm_qcDirectoryIndicators` | None (new) | High | 3 |
| 6 | Capitation Sites | `prm_qcCapitationSites` | `prmInitialCredPDACaptiationLogic` (50%) | Medium | 2 |
| 7 | QC Outcome | `prm_qcOutcome` | None (new) | Medium | 2 |

#### Tile 3 Deep Dive: Practice Location Networks (Most Complex Tile in Entire Program)

This tile manages network assignments across 20+ practice locations with 100+ available networks each:

- **Master-detail view:** Left panel = location list, right panel = network assignment for selected location
- **Dual list box** for networks (Available ↔ Assigned) with search/filter and bulk select
- **Dual list box** for info codes (Available ↔ Assigned)
- **Show in Directory** toggle per location
- **Bulk actions:** "Apply to All Locations", "Copy from Location"
- **Pagination** for >10 locations
- **Network categories:** Commercial, Medicare, Medicaid grouping

**Est. effort:** 5 days (1 week) — Cursor AI accelerates dual list box scaffolding

#### Phase Breakdown

| Week | Deliverables | Days |
|------|-------------|------|
| **Week 1** | Configure 7 PDA QC tiles. Build `QCReviewController` Apex: `fetchQCReviewData`, `fetchAvailableNetworks` (cacheable, 100+), `fetchAvailableInfoCodes` (cacheable, 50+), `fetchCapitationSites`, `saveQCVerificationTileStatus`, `submitQCReview`. Wire `PRM_NetworkManagementQCUpdate` IP. Unit tests. Build `prm_qcPractitionerSummary` (1d). | 5 |
| **Week 2** | Build `prm_qcSpecialtiesPrivileges` (2d) — 3 data tables (specialties, board certs, hospital privileges), read-only, expiration warnings. Build `prm_qcPracticeLocationNetworks` Part 1 (3d) — master-detail layout, location list cards, dual list box for networks with search/filter/categories, info code dual list box, show in directory toggle. | 5 |
| **Week 3** | Build `prm_qcPracticeLocationNetworks` Part 2 (2d) — bulk actions (Apply to All, Copy from Location), pagination, validation. Build `prm_qcPractitionerNetworks` (2d). Build `prm_qcDirectoryIndicators` (1d — hierarchical tree view start). | 5 |
| **Week 4** | Complete `prm_qcDirectoryIndicators` (2d — cascade logic, bulk actions, warning messages). Build `prm_qcCapitationSites` (1d — wrap existing `prmInitialCredPDACaptiationLogic` LWC in modal, PCP/Dual only). Build `prm_qcOutcome` (2d) — tile summary table, QC outcome radio, error reasons multi-select, rebuttal section, confirmation dialog. | 5 |
| **Week 5** | Integration testing (2d) — full flow, 100+ networks x 20+ locations, directory cascade, capitation. Performance testing (1d) — dual list box with 100+ options, page load, tile save. UAT with QC specialists (1d). Bug fixes + deployment prep (1d). | 5 |

**PDA QC Deliverables:**
- 6 new PDA QC-specific tile components
- 1 component partially reused (capitation LWC wrap)
- 1 Apex controller
- 25 total working days

---

## 4. Complete LWC Component Inventory

### Framework Components (6)

| # | Component | Type | Built In | Used By |
|---|-----------|------|----------|---------|
| 1 | `prm_verificationDashboard` | Parent Container | Flow 1, Week 1 | All 5 flows |
| 2 | `prm_progressHeader` | UI | Flow 1, Week 1 | All 5 flows |
| 3 | `prm_verificationTile` | UI | Flow 1, Week 1 | All 5 flows |
| 4 | `prm_verificationModal` | UI | Flow 1, Week 1 | All 5 flows |
| 5 | `prm_navigationFooter` | UI | Flow 1, Week 1 | All 5 flows |
| 6 | `prm_qcWrapper` | QC Pattern | Flow 3, Week 1 | Flows 3, 4 |

### Shared Sub-Components (4)

| # | Component | Built In | Used By |
|---|-----------|----------|---------|
| 7 | `prm_practitionerDemographics` | Flow 1, Week 2 | Flows 1, 3, 5 |
| 8 | `prm_taxonomyVerification` | Flow 1, Week 2 | Flows 1, 3 |
| 9 | `prm_fileUpload` | Flow 1, Week 2 | Flows 1, 2, 3, 4 |
| 10 | `prm_finalSubmitBase` | Flow 1, Week 3 | Flows 1, 2, 3, 5 |

### Combined Initial Cred Review Tiles (15 — Flow 1)

> 2 merged (Practitioner Info, Taxonomy) + 6 App-Review-origin + 7 PSV-origin. (File Upload reuses the `prm_fileUpload` sub-component; Final Submit reuses `prm_finalSubmitBase`.)

| # | Component | Built In | Origin |
|---|-----------|----------|--------|
| 11 | `prm_practitionerInfo` *(merged)* | Flow 1, Week 4 | Review Application + PSV Practitioner Info |
| 12 | `prm_taxonomyVerification` (as tile) | Flow 1, Week 4 | App Review tile + PSV embedded |
| 13 | `prm_reviewEducation` | Flow 1, Week 4 | App Review |
| 14 | `prm_reviewLicense` | Flow 1, Week 5 | App Review |
| 15 | `prm_reviewDEA` | Flow 1, Week 5 | App Review |
| 16 | `prm_reviewCDS` | Flow 1, Week 5 | App Review |
| 17 | `prm_reviewWorkHistory` | Flow 1, Week 5 | App Review |
| 18 | `prm_reviewMalpractice` | Flow 1, Week 5 | App Review |
| 19 | `prm_psvGroupPractice` | Flow 1, Week 6 | PSV |
| 20 | `prm_psvAddressVerification` | Flow 1, Week 6-7 | PSV |
| 21 | `prm_psvDemographicsDiversity` | Flow 1, Week 6 | PSV |
| 22 | `prm_psvLanguagesSpoken` | Flow 1, Week 6 | PSV |
| 23 | `prm_psvContactInformation` | Flow 1, Week 6 | PSV |
| 24 | `prm_psvBoardCertification` | Flow 1, Week 7 | PSV (conditional / Re-Cred) |
| 25 | `prm_psvContractStatus` | Flow 1, Week 7 | PSV |
| 26 | `prm_finalSubmit` *(merged)* | Flow 1, Week 7 | Final Submit + Final Confirmation |

### Re-Cred PSV Tiles (3 unique — Flow 2)

| # | Component | Built In | Flow |
|---|-----------|----------|------|
| 27 | `prm_reCredBoardCertification` | Flow 2, Week 1 | Re-Cred PSV |
| 28 | `prm_reCredCMSPreclusionReview` | Flow 2, Week 2 | Re-Cred PSV |
| 29 | `prm_reCredFinalConfirmation` | Flow 2, Week 2 | Re-Cred PSV |

### Initial Cred QC Tiles (14 QC wrappers + 1 summary — Flow 3)

> Each `prm_qc<Tile>` is a thin config over `prm_qcWrapper` wrapping a combined-flow component read-only.

| # | Component | Built In | Flow |
|---|-----------|----------|------|
| 30 | `prm_qcPractitionerInfo` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 31 | `prm_qcTaxonomy` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 32 | `prm_qcEducation` | Flow 3, Week 1 | Cred QC |
| 33 | `prm_qcLicense` | Flow 3, Week 1 | Cred QC |
| 34 | `prm_qcDEA` | Flow 3, Week 1 | Cred QC |
| 35 | `prm_qcCDS` | Flow 3, Week 1 | Cred QC |
| 36 | `prm_qcWorkHistory` | Flow 3, Week 1 | Cred QC |
| 37 | `prm_qcMalpractice` | Flow 3, Week 1 | Cred QC |
| 38 | `prm_qcGroupPractice` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 39 | `prm_qcAddressVerification` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 40 | `prm_qcDemographicsDiversity` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 41 | `prm_qcLanguagesSpoken` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 42 | `prm_qcContactInformation` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 43 | `prm_qcContractBoard` | Flow 3, Week 1 | Cred QC, Re-Cred PSV QC |
| 44 | `prm_credQCSummary` | Flow 3, Week 2 | Cred QC |

### Re-Cred PSV QC Tiles (3 unique — Flow 4)

| # | Component | Built In | Flow |
|---|-----------|----------|------|
| 45 | `prm_reCredQCBoardCertification` | Flow 4, Week 1 | Re-Cred PSV QC |
| 46 | `prm_reCredQCCMSPreclusionReview` | Flow 4, Week 1 | Re-Cred PSV QC |
| 47 | `prm_reCredPsvQCSummary` | Flow 4, Week 1 | Re-Cred PSV QC |

### PDA QC Tiles (7 unique — Flow 5)

| # | Component | Built In | Flow |
|---|-----------|----------|------|
| 48 | `prm_qcPractitionerSummary` | Flow 5, Week 1 | PDA QC |
| 49 | `prm_qcSpecialtiesPrivileges` | Flow 5, Week 2 | PDA QC |
| 50 | `prm_qcPracticeLocationNetworks` | Flow 5, Week 2-3 | PDA QC |
| 51 | `prm_qcPractitionerNetworks` | Flow 5, Week 3 | PDA QC |
| 52 | `prm_qcDirectoryIndicators` | Flow 5, Week 3-4 | PDA QC |
| 53 | `prm_qcCapitationSites` | Flow 5, Week 4 | PDA QC |
| 54 | `prm_qcOutcome` | Flow 5, Week 4 | PDA QC |

### Apex Controllers (6)

| # | Controller | Flow |
|---|-----------|------|
| 55 | `CredentialingReviewController` *(merges ApplicationReview + PSVReview)* | Initial Cred Review (Combined) |
| 56 | `CAQHIntegrationController` | Combined flow, Re-Cred (shared) |
| 57 | `ReCredPSVReviewController` | Re-Cred PSV |
| 58 | `CredQCReviewController` | Initial Cred QC |
| 59 | `ReCredPSVQCReviewController` | Re-Cred PSV QC |
| 60 | `QCReviewController` | PDA QC |

**GRAND TOTAL: ~48 LWC Components + 6 Apex Controllers + 2 Custom Objects** *(down from 49 LWC + 7 Apex: the merge removes the duplicate Practitioner Info / Final Confirmation tiles and folds two controllers into one, offset by the larger Cred QC wrapper set.)*

---

## 5. Recommended Execution Timeline (Parallel Strategy)

### Gantt Chart (12 Weeks)

```
Week:  1  2  3  4  5  6  7  8  9  10  11  12
       ├──┼──┼──┼──┼──┼──┼──┼──┼──┼───┼───┤

FLOW 1: INITIAL CRED REVIEW — COMBINED (10.5 weeks)
       [===FOUNDATION===][======COMBINED TILES (17)======][TEST/UAT]
       W1   W2   W3      W4  W5  W6  W7  W8   W9   W10  W10.5

FLOW 5: PDA QC (5 weeks) — starts Week 4 (parallel with combined-flow tiles)
                      [APEX][===PDA QC TILES===][TEST]
                      W4  W5  W6   W7   W8

FLOW 2: RE-CRED PSV (3 weeks) — starts Week 9 (after combined tiles stable)
                                          [CONFIG][TILES][UAT]
                                          W9   W10   W11

FLOW 3: INITIAL CRED QC (2.5 weeks) — starts Week 9 (wraps combined flow)
                                          [WRAP+APPLY][TEST]
                                          W9    W10   W11

FLOW 4: RE-CRED PSV QC (1.5 weeks) — starts Week 11
                                                    [BUILD][TEST]
                                                    W11  W12

MIGRATION & ROLLOUT (1 week)
                                                          [CUTOVER]
                                                          W12
```

### Critical Path

```
Combined Framework (W1-3) → Combined Tiles (W4-8) → Re-Cred PSV (W9-11) → Re-Cred PSV QC (W11-12)
                          → PDA QC (W4-8) [parallel with combined tiles]
                          → Initial Cred QC (W9-11) [parallel with Re-Cred PSV; wraps combined flow]
```

### Resource Requirements

| Role | Count | Assignment |
|------|-------|-----------|
| **Senior LWC Developer + Cursor AI** | 2 | Developer A: Combined Initial Cred Review + Re-Cred PSV + QC flows. Developer B: PDA QC (parallel). Both leveraging Cursor AI for component generation. |
| **Apex Developer** | 1 | Controllers, IP integration, unit tests |
| **Salesforce Admin** | 1 | Custom objects, permission sets, field-level security |
| **QA Engineer** | 1 | Test plans, integration testing, UAT coordination |
| **Business Analyst** | 1 | UAT coordination, acceptance criteria, training materials |

---

## 6. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| 1 | **4MB limit workaround doesn't fully resolve with tile save** | Low | High | Each tile saves independently; max tile payload ~200KB. Verified by design. |
| 2 | **Address tile performance (100+ addresses)** | Medium | High | Pagination (10/page), lazy loading, async batch processing for >20 addresses (existing `PracticeLocationBatchProcessor`). |
| 3 | **Network dual list box performance (100+ networks)** | Medium | Medium | Cacheable Apex (`@AuraEnabled(cacheable=true)`), network category grouping, search/filter, debounced input. |
| 4 | **Directory flag cascade logic errors** | Low | High | Confirmation dialogs before cascade, unit tests for all cascade scenarios, rollback capability. |
| 5 | **User adoption resistance** | Medium | High | Parallel run with OmniScript fallback, "Try New Experience" opt-in, champion users, training sessions. |
| 6 | **CAQH API timeout during review** | Medium | Medium | Cache CAQH data on first load, retry logic (3 attempts), async CAQH fetch. |
| 7 | **Integration Procedure compatibility** | Low | High | Test tile-based saves against existing IPs early (Week 3 technical spike). Keep IP signatures unchanged. |
| 8 | **Concurrent session conflicts** | Low | Medium | Session locking with "In Use by X" indicator. Unlock on Save & Exit or after 30-min idle. |

---

## 7. Migration Strategy (All Flows)

### Phase 1: Parallel Run (Week 13)
- Deploy all LWC flows alongside existing OmniScripts
- Add "Try New Experience" button on each Case Manager record
- Opt-in for business users
- Collect feedback

### Phase 2: Full Cutover (Post Week 13)
- Make LWC the default experience after 2 sprints of parallel run
- Keep OmniScript as fallback for 2 additional sprints
- Monitor error rates and user satisfaction
- Archive OmniScript code after stability confirmed

---

## 8. Success Criteria

### Performance Targets

| Metric | Target | Current State |
|--------|--------|--------------|
| Save failures | 0 | Multiple (4MB limit) |
| Page load time | < 3 seconds | 8-15 seconds (large OmniScripts) |
| Tile save time | < 2 seconds | N/A (single save at end) |
| Resume session | < 3 seconds | N/A (no resume) |
| Max addresses handled | 200+ (async) | ~50 (timeout) |
| Max networks handled | 100+ per location | ~30 (UI freezes) |

### Business Outcomes

| Outcome | Measurement |
|---------|-------------|
| Eliminate "Save for Later" failures | 0 failures in production |
| Reduce session time per review | 30-50% reduction (tiles allow focused work) |
| Enable collaboration | Multiple reviewers can work on same case (different tiles) |
| Improve progress visibility | 100% of users report knowing their review status |
| Support pause/resume | Users can resume from any device at any time |

---

## 9. Open Decisions

| # | Decision | Options | Recommendation | Status |
|---|----------|---------|---------------|--------|
| 1 | Data persistence strategy | Custom Objects / localStorage / Hybrid | **Custom Objects** (persistent, auditable, cross-device) | Pending stakeholder review |
| 2 | Navigation model | Sequential-only / Free-form / Hybrid | **Free-form** (any tile, any order) | Recommended |
| 3 | CAQH validation timing | Upfront on load / On-demand per tile | **Upfront** (cache on first load) | Recommended |
| 4 | Concurrent access | Block / Allow with locking | **Allow with session locking** | Pending |
| 5 | Edit completed tiles | Lock once done / Allow re-open | **Allow re-open** (with "Modified After Completion" badge) | Recommended |
| 6 | File upload placement | Separate tile / Embedded per tile | **Separate tile** (consistent across flows) | Decided |
| 7 | Integration Procedure approach | Reuse as-is / Modify for tile-based | **Reuse as-is** (aggregate on final submit) | Recommended |

---

**Document Version:** 2.0
**Created:** 2026-04-10
**Last Updated:** 2026-06-27
**Author:** Development Team
**Status:** DRAFT — Ready for Stakeholder Review

### Summary of Changes (v2.0 — Combined Flow)
- **Merged Application Review + Initial Cred PSV into one "Initial Credentialing Review" flow** (business-ratified) — single dashboard, single session, single Final Submit (same `PRM_ReviewPSVCaseRecordsUpdate` IP).
- Merged the 4 overlapping tiles (Practitioner Info, Taxonomy, File Upload, Final Submit) → **17 combined tiles** (was 20 across two flows).
- Folded `ApplicationReviewController` + `PSVReviewController` → one `CredentialingReviewController`.
- `Flow_Type__c`: `ApplicationReview` + `PSVReview` → single `InitialCredReview`; `PSVQCReview` → `InitialCredQCReview`.
- Renumbered downstream flows (Re-Cred PSV → Flow 2, Initial Cred QC → Flow 3 [now wraps the combined flow's 14 verification tiles], Re-Cred PSV QC → Flow 4, PDA QC → Flow 5).
- Downstream flows otherwise unchanged in scope.

### Summary of Changes (v1.1)
- Removed auto-save feature (not in scope)
- Clarified CAQH data is always read-only/display-only across all flows (no edit on CAQH data)
- Adjusted all timelines for Cursor AI-assisted development (~40-50% faster for component building)
- Testing and UAT timelines remain unchanged

### Updated Totals
| Metric | v1.0 | v1.1 (Cursor AI) | v2.0 (Combined) | Notes |
|--------|------|-------------------|-----------------|-------|
| **Total Effort** | 175 working days | ~122 working days | ~111 working days | combine saves ~11 days |
| **Sequential Timeline** | 35 weeks | ~24.5 weeks | ~22.5 weeks | one fewer flow |
| **Parallel Timeline** | 20 weeks | ~13 weeks | ~12 weeks | shorter critical path |
| **Flows** | 6 | 6 | **5** | App Review + PSV merged |
| **LWC Components** | 49 | 49 | ~48 | net of merge + larger QC set |
| **Apex Controllers** | 7 | 7 | **6** | 2 controllers → 1 |
| **Custom Objects** | 2 | 2 | 2 | Same scope |
