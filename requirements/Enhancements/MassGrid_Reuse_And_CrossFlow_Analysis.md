# Mass Grid Reuse & Cross-Flow Analysis
## Leveraging the Shared Async Batch Framework + Tile-Based LWC Redesign
## to Deliver Mass Grid, POMS Replacement, FHNatic Provider Forms, and Guided-Flow Modernization

**Document Type:** Enhancement Architecture & Reuse Estimation
**Vertical:** Provider Network Management (PNM) — Provider Data Management (PDM)
**Companion To:** `requirements/Enhancements/HighVolume_GuidedFlows_Performance_Estimation.md`
**Business Ask:** Update many records at once — across Group Name, DBA Name, Info Indicator, Phone Number, Office Hours, NPI, Tax ID, Locations, Networks, Cap Sites, Linking Providers, Terming Practitioners, Panel Status — without opening each record individually.
**Document Owner:** Salesforce Architecture
**Audience:** Business Stakeholders, Project Management, Senior Developers, QA Lead, Enterprise Architecture
**Date:** 2026-04-23
**Status:** Draft for IBX Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business-Requested Mass Grid Operations — Detailed Breakdown](#2-business-requested-mass-grid-operations--detailed-breakdown)
3. [Revised Mass Grid Architecture](#3-revised-mass-grid-architecture-replacing-the-old-13-ptsoperation-estimate)
4. [The "Tile Approach" — App Review / PSV / PSV QC / PDA QC / ReCred Redesign](#4-the-tile-approach--app-review--psv--psv-qc--pda-qc--recred-redesign)
5. [THE MASTER REUSE TABLE](#5-the-master-reuse-table)
6. [OmniScript-by-OmniScript Impact Analysis](#6-omniscript-by-omniscript-impact-analysis)
7. [POMS Replacement — Revised Estimate](#7-poms-replacement--revised-estimate)
8. [FHNatic Provider Forms — How Mass Grid & Batch Framework Help](#8-fhnatic-provider-forms--how-mass-grid--batch-framework-help)
9. [Updated Grand Total Comparison](#9-updated-grand-total-comparison)
10. [Implementation Sequencing](#10-implementation-sequencing)

---

## 1. Executive Summary

This document is **complementary to** — not duplicative of — the existing `HighVolume_GuidedFlows_Performance_Estimation.md`. The performance estimation doc establishes the **shared async batch framework** (Platform Event, Orchestrator, three mode-parameterized Batch Apex classes, staging object, exception pipeline, Data Admin tooling) delivered as Wave 1 (Practitioner Creation) and re-used across Waves 2–5 for PDM Practitioner, PDM Practice Location, Mass Updates, and Mass Address Updates.

This companion document does four things that doc does not:

1. **Maps the 13 specific business-requested mass operations** (Group Name, DBA Name, Info Indicator, Phone, Office Hours, NPI, Tax ID, Locations, Networks, Cap Sites, Linking Providers, Terming Practitioners, Panel Status) onto the shared framework — including Salesforce objects, current OmniScripts, and overlap with performance-fix batches.
2. **Revises the October 2025 Mass Grid estimate** (130 SP @ 13 SP/op × 10 operations) downward, because 60–75% of the infrastructure is already being built for Wave 1/4.
3. **Introduces the "Tile Approach"** — the App Review / PSV / PSV QC / PDA QC / ReCred PSV / ReCred PSV QC LWC redesign pattern — and explains how tile primitives (`prm_verificationDashboard`, `prm_verificationTile`, `prm_verificationModal`, `prm_progressHeader`, `prm_fileUpload`) become the **UI layer for the mass grid**. The same tile framework that replaces OmniScripts becomes the bulk-edit experience.
4. **Builds a master reuse table** showing every cross-flow reusable asset (batch class, LWC, IP, DataRaptor, service, custom object, Platform Event, FlexCard) and the flows they plug into.

### Headline Numbers

| Initiative | October 2025 Estimate | Revised Estimate (with reuse) | Savings |
|---|---|---|---|
| Mass Grid Replacement | 130 SP (10 ops × 13 pts) | **58–72 SP** | **58–72 SP (~50% reduction)** |
| POMS Replacement in PIE | 80–120 SP | **42–60 SP** | **38–60 SP (~45% reduction)** |
| FHNatic Provider Forms (external portal) | 32–52 SP | **18–28 SP** | **14–24 SP (~45% reduction)** |
| **TOTAL** | **242–302 SP** | **118–160 SP** | **~47% average reduction** |

The savings are possible only because three investments run **in parallel**:
- Wave 1 (Practitioner Creation) delivers the **shared async batch framework**
- Waves 2–5 (PDM Pract., PDM PL, Mass Updates, Mass Addresses) deliver the **mode-extended batch classes and async dispatcher**
- App Review / PSV / PDA QC / ReCred redesigns deliver the **tile primitives, verification-tile LWCs, session-persistence objects, and auto-save/progress infrastructure**

When all three streams are done, Mass Grid, POMS, and FHNatic become **assembly jobs**, not ground-up builds.

---

## 2. Business-Requested Mass Grid Operations — Detailed Breakdown

### 2.1 Operation-to-Framework Mapping

Each business-requested operation is analyzed against three questions:
- **Which Salesforce object(s) does it write to?**
- **Which OmniScript handles the individual-record case today?**
- **Is the batch class for this operation already being built in the performance-fix waves (Waves 1–5)?**

| # | Operation | SF Object(s) | Current OmniScript | Batch Class Needed | Overlap w/ Perf Fix | SP Low | SP High | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | **Group Name** | `Account.Name` (Group), `HealthcareFacility.Name` cascade | `PRM_PDMManualUpdate_English` → `CB_UpdateHCFNames` → `DRLoadPracticeNameChange` | `PRM_MassGroupNameBatch` (new) | **Low** — new op; reuses orchestrator + staging + event | 3 | 5 | Cascades to HCPF.Name; requires cache refresh on directory |
| 2 | **DBA Name** | `Account.PRM_DBAName__c`, `HealthcareFacility.PRM_DBAName__c` | `PRM_PDMManualUpdate_English` (CB for DBA) | `PRM_MassDBANameBatch` (new) | **Low** — same shape as #1 | 2 | 3 | Trivially similar to Group Name; same batch class with field list param |
| 3 | **Info Indicator** | `HealthcarePractitionerFacility.PRM_InfoCode__c`, `PRM_InfoCodeAssignment__c`, `PractitionerLocationInfoCode`, `PractitionerInfoCode` | `PRM_InitialCredPDAQC_English`, `PRM_PDMManualUpdate_English` → `CB_UpdateDirectoryIndicators` / related | `PRM_MassInfoIndicatorBatch` (new) | **Medium** — overlaps with Wave 4 `PRM_PDMDirectoryBatch` (directory indicators also bulk HCPF flag updates) | 4 | 6 | Bulk flag update pattern; can use same batch shape as Wave 4 directory batch |
| 4 | **Phone Number** | `HealthcareFacility.Phone`, `Location.Phone`, `Address.Phone`, `HealthcarePractitionerFacility.PRM_Phone__c`, `Account.Phone` | `PRM_PDMManualUpdate_English`, `PRM_DelegatedPractitionerAddressForm_English` | `PRM_MassPhoneUpdateBatch` (new) | **Medium** — mirrors Wave 5 `PRM_MassMailingAddressUpdateBatch` (same target objects minus street fields) | 3 | 5 | Reuses `PRM_AddressValidationService` pattern for phone normalization |
| 5 | **Office Hours** | `OperatingHours`, `OperatingHoursHoliday`, `HealthcareFacility.OperatingHoursId` | `PRM_PDMManualUpdate_English` → `CB_UpdateOfficeHours` → `DRLoadOperatingHours` | `PRM_MassOfficeHoursBatch` (new) | **High** — Wave 3 is already building `PRM_PDMOfficeHoursBatch` (non-mass version); we extend with MASS_OFFICE_HOURS mode | 2 | 4 | Mode extension of existing Wave 3 batch; 7 days × N slots per facility |
| 6 | **NPI** | `HealthcareProviderNpi`, `HealthcareFacility.PRM_NPI__c`, `PRM_IdentifierPractitioner__c`, `PRM_IdentifierHealthcareFacility__c` | `PRM_PDMManualUpdatePractitioner_English` → `CB_MedicareNumber` / `DRTIdentifier` | `PRM_MassNPIUpdateBatch` (new) | **Medium** — overlaps with `PRM_FutureHCProviderNPIActivateBatch` (existing activation batch) | 4 | 6 | Strict data-integrity validation (NPI Luhn check + uniqueness); can reuse `DRTIdentifier` validation logic |
| 7 | **Tax ID** | `Account.PRM_TaxId__c`, `HealthcareFacility.PRM_TaxId__c` | `PRM_PDMManualUpdate_English`, `PRM_AccountCreation_English` | `PRM_MassTaxIdUpdateBatch` (new) | **Low** — new op; same shape as Group Name | 3 | 4 | Tax ID changes often require downstream cross-reference record updates (handled via `PRM_CrossRefBatch`) |
| 8 | **Locations** | `HealthcareFacility`, `HealthcarePractitionerFacility`, `HealthcareFacilityNetwork`, `HealthcareProviderTaxonomy`, `Location`, `PRM_HealthcareFacilityAssociation__c` | `PRM_PDMManualUpdate_English` → `CB_TerminatePracticeLocation`; `PRM_CreatePracticeLocationBundle_English`; `PRM_AddToExistingPracticeLocationBundle_English` | **Reuse Wave 4 `PRM_MassAddPracticeLocationBatch` + `PRM_MassTerminatePracticeLocationBatch`** | **Full (100%)** — already in Wave 4 | 0 | 2 | **Zero new batch work** — already planned in Wave 4 |
| 9 | **Networks** | `HealthcareFacilityNetwork`, `PractitionerLocationNetwork`, `PractitionerNetwork` | `PRM_PDMManualUpdate_English` → `CB_AddRemoveNetworks` → `DRLoadManualUpdatePLNetworks` | **Reuse Wave 4 `PRM_MassAddNetworkBatch` + `PRM_MassRemoveNetworkBatch`** | **Full (100%)** — already in Wave 4 | 0 | 2 | **Zero new batch work**; only UI plumbing |
| 10 | **Cap Sites** (Capitation Sites) | `CapitationSite`, `PractitionerLocationCapitation`, `HealthcareFacility.PRM_IsCapitated__c` | `PRM_PDMManualUpdate_English` → `CB_CapitationSite` → `DRLoadCapitationSite`; `PRM_InitialCredPDAQC_English` (cap-site tile logic via `prmCapitationSiteLogic` + `prmInitialCredPDACaptiationLogic`) | `PRM_MassCapSiteBatch` (new) | **Medium** — shares facility-lookup + upsert shape with Wave 4; reuses existing `prmCapitationSiteLogic` LWC | 3 | 5 | The existing `prmCapitationSiteLogic` LWC (from PDA QC) is directly reusable as the grid cell editor |
| 11 | **Linking Providers** (link practitioner → practice location) | `HealthcarePractitionerFacility`, `HealthcareFacilityNetwork` (cloned per taxonomy × role × network), `HealthcareProviderTaxonomy`, `PRM_IdentifierHCPractitionerFacility__c` | `PRM_PDMManualUpdate_English` → `CB_AddRemovePractitionerHCPF`; mirrors the UPHS 107-practitioner scenario | **Reuse Wave 4 `PRM_MassAddPractitionerBatch`** | **Full (100%)** — already in Wave 4 as the UPHS use case | 0 | 2 | **Zero new batch work**; this IS the UPHS scenario |
| 12 | **Terming Practitioners** (bulk terminate practitioner-facility or practitioner-network) | `HealthcarePractitionerFacility` (deactivate), `HealthcareFacilityNetwork` (deactivate), `HealthcareProviderTaxonomy` (optional cascade), `PRM_CrossRef__c` | `PRM_PDMManualUpdate_English` → `CB_TerminateCOIAndRemovePractitioner`, `CB_AddRemovePractitioner`; `PRM_PractitionerTerminationForm_English`; `PRM_PractitionerTerminationRecredForm_English` | **Reuse Wave 4 `PRM_MassRemovePractitionerBatch`**, plus existing `PRM_FullPractitionerTerminationBatch`, `PRM_PractitionerTerminationBatch`, `PRM_ManualUpdatePracLocTerminationBatch` | **Full (100%)** — heavy existing batch inventory | 0 | 2 | **Zero new batch work**; mostly rewiring existing termination batches to accept a mass payload |
| 13 | **Panel Status** (Accepting-New-Patients / Closed Panel flags) | `HealthcarePractitionerFacility.PRM_PanelStatus__c`, `HealthcareFacilityNetwork.PRM_AcceptingNewPatients__c`, `PractitionerLocationNetwork.PRM_PanelStatus__c`, `PRM_InfoCodeAssignment__c` for "Accepting New Patients" | `PRM_PDMManualUpdate_English`, `PRM_InitialCredPDAQC_English` | `PRM_MassPanelStatusBatch` (new) | **Medium** — overlaps with Info Indicator (#3) — both are bulk-flag updates on HCPF/HFN. Can be same batch with `fieldList` parameter | 2 | 4 | Closed network config (`PRM_ClosedNetworkConfig__mdt`, `prmCheckClosedNetworkLogic` LWC) already exists for validation |
| | **TOTALS** | | | | | **26** | **50** | |

### 2.2 Data Validation & Constraint Analysis

| Operation | Key Validations | Existing Service / Rule |
|---|---|---|
| Group Name / DBA Name | Length, uniqueness (soft), printable chars | `PRM_ExistingAccountService` |
| Phone Number | Format normalization (xxx-xxx-xxxx), area code valid | `prmAddressUtils.formatPhone()` |
| NPI | Luhn check, 10-digit, not duplicate on active records | `PRM_PARProviderSearch`, `DRTIdentifier` |
| Tax ID | 9-digit, EIN format, cross-reference across all group accounts | `PRM_CrossRefBatch`, `PRM_AccountCreationCrossRefBatch` |
| Office Hours | 24h clock, no overlap, at least one day open | `DRLoadOperatingHours` logic (port to Apex) |
| Cap Sites | Must be capitated network, PCP/Dual role only | `prmCapitationSiteLogic`, `prmInitialCredPDACaptiationLogic` |
| Networks | Closed-network rule check, service area match | `prmCheckClosedNetworkLogic`, `PRM_ClosedNetworkConfig__mdt` |
| Locations (add) | Facility exists, address validated, not duplicate | `PRM_AddressValidationService`, `PRM_LocationQueryService`, `PRM_SmartAddressSearch` |
| Terming Practitioners | Date ≥ today, not already terminated, no active future-dated records | `PRM_FutureDatedProcessingBatch`, `PRM_FutureDatedProcessingBatchHandler` |
| Panel Status | Network contract allows panel toggle, info code exists | `PRM_InfoCode__c`, `PRM_InfoCodeAssignment__c` |
| Info Indicator | Valid info code, correct level (location vs. network vs. practitioner) | `PRM_InfoCodeAssignment__c` |
| Linking Providers | Practitioner exists, facility exists, not already linked at same taxonomy × role | `PRM_PDMManualUpdate_English` dup check; `PRM_PractitionerActivationBatchHelper` |

### 2.3 Observation: "Locations / Networks / Linking Providers / Terming Practitioners" = Free

Four of the thirteen operations are already fully covered by Wave 4 batch classes documented in the High-Volume estimation (Section 6C):
- `PRM_MassAddPracticeLocationBatch`
- `PRM_MassTerminatePracticeLocationBatch`
- `PRM_MassAddNetworkBatch` / `PRM_MassRemoveNetworkBatch`
- `PRM_MassAddPractitionerBatch` / `PRM_MassRemovePractitionerBatch`

These four operations together account for **52 SP** in the October 2025 estimate (4 × 13 SP). Under the revised model, they add **0–8 SP** incremental — just the grid UI wiring.

---

## 3. Revised Mass Grid Architecture (Replacing the Old 13-pts/Operation Estimate)

### 3.1 Why the Old 130 SP Estimate Was Conservative

The October 2025 estimate assumed each mass operation was built from scratch:

```
Old Assumption:
  10 operations × 13 SP each =  130 SP
  Each operation gets its own:
    - Apex batch class                 (5 SP)
    - OmniScript/LWC UI                (4 SP)
    - Unit tests + integration tests   (2 SP)
    - Deployment + UAT                 (2 SP)
```

Under the shared-framework model, the per-operation cost drops dramatically because the batch framework, staging object, exception pipeline, email templates, Data Admin tooling, and status FlexCard are **delivered once** in Waves 1 and 4.

### 3.2 The New Architecture: Shared Async Infrastructure + Operation-Specific Modules

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       MASS GRID LWC (Tile-Based UI)                        │
│  prm_massGridDashboard   ← reuses prm_verificationDashboard primitives     │
│    │                                                                       │
│    ├─ prm_progressHeader           (reused 100% from App Review redesign)  │
│    ├─ prm_massGridTable            (new, built on lightning-datatable)     │
│    │    ├─ prm_gridCellGroupName   (new, thin)                             │
│    │    ├─ prm_gridCellDBAName     (new, thin)                             │
│    │    ├─ prm_gridCellInfoInd     (reused from prmAddInfoCodes)           │
│    │    ├─ prm_gridCellPhone       (reused from prmAddressUtils)           │
│    │    ├─ prm_gridCellOfficeHrs   (reused from prmAttestationOfficeHourReadOnly + edit mode) │
│    │    ├─ prm_gridCellNPI         (new, thin)                             │
│    │    ├─ prm_gridCellTaxId       (new, thin)                             │
│    │    ├─ prm_gridCellNetworks    (reused from prmAddNetworks)            │
│    │    ├─ prm_gridCellCapSite     (reused from prmCapitationSiteLogic)    │
│    │    └─ prm_gridCellPanelStatus (reused from prmCheckClosedNetworkLogic)│
│    ├─ prm_verificationModal        (reused 100% for bulk-edit dialogs)     │
│    ├─ PRM_PDMJobStatusCard         (FlexCard, reused from Wave 4)          │
│    └─ prm_navigationFooter         (reused 100%)                           │
│                                                                            │
│  [Save All Changes] → submits to PRM_SubmitAsyncJob IP                    │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                 SHARED ASYNC FRAMEWORK (built in Waves 1 & 4)              │
│                                                                            │
│  PRM_SubmitAsyncJob (IP) → PRM_AsyncJobRequest__c (staging)                │
│       → PRM_AsyncJobQueued__e (Platform Event)                             │
│       → PRM_AsyncJobQueuedTrigger                                          │
│       → PRM_AsyncJobDispatcher.dispatch(flowType, subType)                 │
│                                                                            │
│  ExceptionLogEvent__e + PRM_ExceptionLog__c (rollback-safe logging)        │
│  PRM_FailedRecordStaging__c + Data Admin list view + Quick Actions         │
│  Email success/failure templates                                           │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│              OPERATION-SPECIFIC BATCH MODULES                              │
│                                                                            │
│  Reused from Wave 4 (zero marginal cost):                                  │
│    PRM_MassAddPractitionerBatch        (Linking Providers)                 │
│    PRM_MassRemovePractitionerBatch     (Terming Practitioners)             │
│    PRM_MassAddNetworkBatch             (Add Networks)                      │
│    PRM_MassRemoveNetworkBatch          (Remove Networks)                   │
│    PRM_MassAddPracticeLocationBatch    (Add Locations)                     │
│    PRM_MassTerminatePracticeLocationBatch (Terminate Locations)            │
│    PRM_MassAddTaxonomyBatch            (optional for Networks)             │
│                                                                            │
│  Reused from Wave 5 (zero marginal cost):                                  │
│    PRM_MassMailingAddressUpdateBatch   (Phone, Office Hours adjacency)     │
│                                                                            │
│  New thin batches (~2–4 SP each):                                          │
│    PRM_MassGroupNameBatch                                                  │
│    PRM_MassDBANameBatch                                                    │
│    PRM_MassInfoIndicatorBatch                                              │
│    PRM_MassPhoneUpdateBatch                                                │
│    PRM_MassOfficeHoursBatch    (mode-extended from Wave 3's batch)         │
│    PRM_MassNPIUpdateBatch                                                  │
│    PRM_MassTaxIdUpdateBatch                                                │
│    PRM_MassCapSiteBatch                                                    │
│    PRM_MassPanelStatusBatch                                                │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Mass Grid Estimate Summary (New vs. Old)

| Work Component | Old Estimate (Oct 2025) | New Estimate | Why It Changed |
|---|---|---|---|
| Batch Apex — 10 new batch classes @ 5 SP each | 50 SP | 10–20 SP | 4 operations reuse Wave 4 batches (0 SP); 2 reuse/extend Wave 3/5 batches (0–2 SP); remaining 7 are thin (~2–4 SP each) |
| UI — 10 new OmniScripts/LWCs @ 4 SP each | 40 SP | 15–22 SP | Dashboard/tile/modal/progress primitives reused from App Review redesign (0 SP); only the 13 grid cell LWCs are new, and 6 of those are reused from existing LWCs |
| Tests — 10 operations × 2 SP | 20 SP | 10–14 SP | AI-assisted test generation from pattern; shared test harness from Wave 1 |
| Deployment + UAT | 20 SP | 8–10 SP | One deploy, one UAT session covers all 10 ops because they share the framework |
| Async infrastructure (staging object, event, dispatcher, FlexCard, email templates, exception pipeline) | *not separated* | **0 SP** | Delivered by Wave 1 (in-flight) + Wave 4 |
| Data Admin tooling (list views, Quick Actions, permission sets) | *not separated* | **0 SP** | Delivered by Wave 1 |
| Email notification templates | *not separated* | **0 SP** | Delivered by Wave 1 |
| **TOTAL** | **130 SP** | **43–66 SP** | **~50% reduction** |

Rounded range: **Mass Grid Replacement = 58–72 SP** (adding buffer for integration testing, closed-network rule validation, and the mass-grid-specific UX polish not present in the per-operation estimates).

### 3.4 Why the New Approach Is Better (Beyond Cheaper)

| Dimension | Old 130 SP Approach | New 58–72 SP Approach |
|---|---|---|
| **Scalability** | Each op hits governor limits at its own threshold (~30 records typical) | Unlimited — fresh 200 SOQL / 60s CPU / 12 MB heap per execute(); 50M rows via QueryLocator |
| **Testability** | Each op tested in isolation; no shared harness | Full-chain integration testable under Test.startTest(); shared fixtures |
| **Monitoring** | Each op has its own AsyncApexJob pattern | One Data Admin list view covers all ops; one retry Quick Action |
| **Failure handling** | All-or-nothing per op; partial failures lose data silently | Database.upsert(records, extId, false) → per-row failure staged to `PRM_FailedRecordStaging__c` |
| **Retry** | Manual, per op, often requires developer | Idempotent UPSERT + Mark Resolved Quick Action; Data Admin self-service |
| **User experience** | UI freeze 3–8 min, no feedback | < 3 second submit; `PRM_PDMJobStatusCard` FlexCard shows Queued → Processing → Completed |
| **Audit trail** | Inconsistent across ops | `PRM_ExceptionLog__c` + `PRM_FailedRecordStaging__c` for all ops; compliance-ready |
| **Compatibility with tile redesign** | Not considered | Mass Grid is a **first-class tile dashboard variant** — same UX as App Review, PSV, QC |
| **Future extensibility** | Adding operation #11 = +13 SP | Adding op #11 = +2–4 SP (just the cell LWC + thin batch) |

---

## 4. The "Tile Approach" — App Review / PSV / PSV QC / PDA QC / ReCred Redesign

### 4.1 What the Tile Approach Is

The tile approach is the UX pattern being adopted for the **six largest credentialing review OmniScripts** (all of which are blocked by the 4 MB Save-for-Later payload limit and the inability to edit fields inline):

| OmniScript | Design Doc | Redesign Name |
|---|---|---|
| `PRM_InitialCredentialAppReview_English` + `PRM_CredApplicationReviewSubOS_English` + `PRM_CredentialAppReviewCompleteOS_English` | `Application_Review_LWC_Redesign_Detailed_Design.md` | Application Review Dashboard |
| `PRM_PrimarySourceVerificationReview_English` + `PRM_PSVSubOsTxnyRole_English` (186+ elements) | `PSV_Review_LWC_Redesign_Detailed_Design.md` | PSV Review Dashboard |
| `PRM_PrimarySourceVerificationReview_English` (QC mode, `CaseType = "QC Review"`) + `PRM_PSVSubOsSummary_English` | `PSV_QC_Review_LWC_Redesign_Detailed_Design.md` | PSV QC Review Dashboard |
| `PRM_InitialCredPDAQC_English` (Network Management QC) | `PDA_QC_Review_LWC_Redesign_Detailed_Design.md` | PDA QC Review Dashboard |
| `PRM_PrimarySourceVerificationReview_English` (Re-Cred mode, `IsRecredentialing = true`) | `ReCred_PSV_Review_LWC_Redesign_Detailed_Design.md` | Re-Cred PSV Dashboard |
| `PRM_PrimarySourceVerificationReview_English` (Re-Cred + QC mode) | `ReCred_PSV_QC_Review_LWC_Redesign_Detailed_Design.md` | Re-Cred PSV QC Dashboard |

Each redesign replaces a single monolithic OmniScript with:
- A **parent dashboard LWC** (tile grid + progress header + auto-save)
- **10–11 tile LWCs**, each independently editable and saveable
- A **modal wrapper** that dynamically loads the correct tile child component
- **Session persistence** via two new custom objects: `PRM_VerificationSession__c` and `PRM_VerificationTileStatus__c`

### 4.2 Framework Primitives (Built Once, Used Everywhere)

These components are **100% reusable across all six redesigns** and, critically, across the **mass grid**, **POMS replacement**, and **FHNatic Provider Forms**:

| Primitive LWC | Purpose | Reuse Scope |
|---|---|---|
| `prm_verificationDashboard` | Parent container; fetches initial data; manages tile grid; coordinates auto-save | App Review, PSV, PSV QC, PDA QC, ReCred PSV, ReCred PSV QC, **Mass Grid**, **POMS**, **FHNatic** |
| `prm_progressHeader` | Progress bar, auto-save indicator, last-saved timestamp | Same 9 flows |
| `prm_verificationTile` | Individual tile card with status badge (Pending / In-Progress / Completed / Error) | Same 9 flows |
| `prm_verificationModal` | Dynamic modal wrapper that injects the correct child tile LWC | Same 9 flows |
| `prm_navigationFooter` | Resume Later / Save & Exit / Help buttons | Same 9 flows |
| `prm_fileUpload` | Drag-drop multi-file upload with type restrictions | App Review, PSV, PSV QC, ReCred, FHNatic (provider uploads) |
| `prm_practitionerDemographics` | Side-by-side CAQH ↔ Salesforce demographics comparison | App Review, PSV, PSV QC, ReCred PSV, ReCred PSV QC, **FHNatic intake** |
| `prm_taxonomyVerification` | Taxonomy/specialty multi-row editor | App Review, PSV, PDA QC, ReCred, **Mass Grid (Networks cell expansion)**, **POMS** |
| `prm_finalSubmitBase` | Outcome selection + validation + notes | All 6 redesigns + FHNatic submit step |

### 4.3 Session Persistence (Used by Mass Grid Too)

The two new custom objects built for App Review — `PRM_VerificationSession__c` and `PRM_VerificationTileStatus__c` — are the **same object shape** needed for mass-grid drafts:
- User starts a mass update for 200 practitioners
- Uploads CSV, grid populates, user edits 50 rows across multiple tiles
- Auto-save writes to `PRM_VerificationSession__c.Session_Data__c` every 2 minutes
- User can close browser, come back tomorrow, resume exactly where they left off
- Each row's completion status is tracked in `PRM_VerificationTileStatus__c`
- On "Save All Changes", the session is submitted to `PRM_SubmitAsyncJob` IP, which writes to `PRM_AsyncJobRequest__c` and fires the Platform Event

This is **zero additional object design effort** for the mass grid — the objects already exist from the App Review redesign (Phase 1, Weeks 1–2).

### 4.4 Tile-to-Mass-Grid Cross-Over

The following tile LWCs from the redesigns map directly onto mass-grid cell editors:

| Tile LWC (from redesign) | Used In | Mass Grid Operation | Reuse Type |
|---|---|---|---|
| `prm_psvGroupPractice` | PSV, PSV QC, ReCred PSV | Group Name, DBA Name, Tax ID, NPI | Direct — exposes same field set |
| `prm_psvAddressVerification` | PSV, PSV QC, ReCred PSV | Phone, Office Hours (for practice location phone/hours) | Direct |
| `prm_qcPracticeLocationNetworks` | PDA QC, PSV QC | Networks (Add/Remove) | Direct — same multi-select grid |
| `prm_qcCapitationSites` (wraps `prmCapitationSiteLogic`) | PDA QC | Cap Sites | Direct |
| `prm_qcDirectoryIndicators` | PDA QC | Info Indicator, Panel Status | Direct |
| `prm_qcPractitionerNetworks` | PDA QC | Linking Providers (practitioner-level networks) | Direct |
| `prm_reviewTaxonomy` | App Review, PDA QC | Networks (taxonomy linkage) | Indirect — used for validation |
| `prm_qcOutcome` | PDA QC | Mass Grid final submit with outcome selector | Direct |

### 4.5 Backend Services Cross-Over

| Backend Service | Built For | Reused In |
|---|---|---|
| `PRM_AddressValidationService` (Precisely API) | Phase 5 core services | Mass Grid (Phone field normalization), PSV, Wave 5 (Mass Addresses), FHNatic |
| `PRM_AddressPicklistService` | Phase 5 core services | Mass Grid, PSV, FHNatic |
| `PRM_LocationQueryService` | Phase 5 core services | Mass Grid (Locations cell), PSV, PDA QC, FHNatic |
| `PRM_SmartAddressSearch` | Existing | Mass Grid (facility lookup from NPI/Tax ID), FHNatic |
| `PRM_PARProviderSearch` | Existing | Mass Grid (practitioner lookup), FHNatic |
| `PRM_ExistingAccountService` | Existing | Mass Grid (group name/tax id dedup), FHNatic |
| `ApplicationReviewController` / `CAQHIntegrationController` | App Review redesign | PSV, PSV QC, ReCred PSV, FHNatic |
| `PRM_ExceptionLogger.logExceptionViaEvent` | Wave 1 | Every flow in the platform |

---

## 5. THE MASTER REUSE TABLE

> **Legend — Reuse Type:**
> - **Direct** = use as-is, zero effort
> - **Mode-Extend** = add a new mode/subType branch (typically 1–3 SP)
> - **Config** = configure or pass new params (< 1 SP)
> - **Wrap** = wrap existing component in new shell (1–2 SP)
> - **Adapt** = material extension to existing code (2–5 SP)

| # | Component Name | Type | Primary Purpose (where it's built) | Reusable In These Flows | Reuse Type | Effort to Reuse | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `PRM_TaxonomyNetworkBatch` | Batch Apex | Built in Wave 1 (Practitioner Creation INSERT mode) | Wave 2 (PDM Pract. UPSERT), Wave 4 (Mass Grid MASS_TAXONOMY), **Mass Grid (Networks)**, **POMS** | Mode-Extend | 3 SP per new mode | Single class; Mode__c parameter drives INSERT/UPSERT/MASS branches |
| 2 | `PRM_PayerNetworkBatch` | Batch Apex | Built in Wave 1 (Practitioner Creation) | Wave 2, Wave 3, **Mass Grid Networks**, **POMS** | Mode-Extend | 3 SP per new mode | Same pattern as #1 |
| 3 | `PRM_IFCRecordBatch` | Batch Apex | Built in Wave 1 | Wave 2, **Mass Grid Info Indicator**, **POMS** | Mode-Extend | 3 SP per new mode | Info Feature Code records |
| 4 | `PRM_NetworkCreationOrchestrator` | Apex Service | Built in Wave 1 (handleEvent, mode router) | Every async flow (PDM Pract., PDM PL, Mass Grid, POMS, FHNatic) | Mode-Extend | 1 SP per new mode (one switch case) | Tiny change per mode |
| 5 | `PRM_NetworkCreationRemote` (+ `publishNetworkCreationEvent`) | Apex Invocable | Built in Wave 1 | Every async flow's IP-to-event bridge | Mode-Extend | 1 SP per new mode | Remote action invoked from OmniScript |
| 6 | `NetworkCreationRequested__e` (Platform Event) | Platform Event | Built in Wave 1 | Every async flow (shared bus) | Direct | 0 SP | Just publish with correct Mode__c value |
| 7 | `PRM_ExceptionLogEvent__e` | Platform Event | Built in Wave 1 | Every flow in the platform | Direct | 0 SP | Rollback-safe exception logging |
| 8 | `PRM_ExceptionLogger.logExceptionViaEvent()` | Apex Service | Built in Wave 1 | Every catch block, every flow | Direct | 0 SP | Replaces direct-DML `logException` |
| 9 | `PRM_ExceptionLog__c` | Custom Object | Built in Wave 1 | Every flow | Direct | 0 SP | Platform Event subscribes → creates records |
| 10 | `PRM_FailedRecordStaging__c` (42 fields) | Custom Object | Built in Wave 1 (partial-success staging) | Every async batch's per-row failures (Mass Grid, POMS, FHNatic) | Direct | 0 SP | Covers all object types via generic field layout |
| 11 | `PRM_BatchStagingHelper` | Apex Utility | Built in Wave 2 (extracted from Wave 1 patterns) | Every mass batch | Direct | 0 SP | Shared helper for stageFailure(), stageSuccess() |
| 12 | `PRM_AsyncJobRequest__c` | Custom Object | Built in Wave 4 (Mass Updates) | Wave 5, **Mass Grid**, **POMS**, **FHNatic** | Direct | 0 SP | 18-field staging object for async payloads |
| 13 | `PRM_AsyncJobQueued__e` | Platform Event | Built in Wave 4 | Same as #12 | Direct | 0 SP | Dispatch-only event (different from #6 which is record-creation event) |
| 14 | `PRM_AsyncJobDispatcher` | Apex Service | Built in Wave 4 | Every mass flow | Mode-Extend | 1 SP per flow type | Single switch on FlowType__c |
| 15 | `PRM_SubmitAsyncJob` (Integration Procedure) | IP | Built in Wave 4 | Mass Grid, POMS, FHNatic | Direct | 0 SP | Captures payload → writes staging → fires event |
| 16 | `PRM_PDMJobStatusCard` (FlexCard) | FlexCard | Built in Wave 4 | Mass Grid, POMS, FHNatic, PDA QC (post-async poll) | Direct | 0 SP | Real-time Queued→Processing→Completed display |
| 17 | `PRM_PractitionerActivationBatch` + `PRM_PractitionerActivationBatchHelper` | Batch Apex (existing) | Already built; currently invoked synchronously | Wave 4, Mass Grid Linking Providers, POMS | Adapt (rewire to async dispatcher) | 1 SP | Existing 100% — just rewire |
| 18 | `PRM_FutureAddressActivateBatch` | Batch Apex (existing) | Existing scheduled batch | Wave 5, Mass Grid Locations (future-dated), POMS | Direct | 0 SP | Existing; reused for future-dated address activation |
| 19 | `PRM_FullPractitionerTerminationBatch` | Batch Apex (existing) | Existing | Mass Grid Terming Practitioners, POMS | Direct | 0 SP | Existing |
| 20 | `PRM_PracticeLocationTerminationBatch` / `PRM_ManualUpdatePracLocTerminationBatch` | Batch Apex (existing) | Existing | Mass Grid Locations (terminate), POMS | Direct | 0 SP | Existing |
| 21 | `PRM_AccountTerminationBatch` + Helper | Batch Apex (existing) | Existing | Mass Grid Terming (group-level), POMS | Direct | 0 SP | Existing |
| 22 | `PRM_FutureDatedProcessingBatch` + Scheduler + Handler | Batch Apex (existing) | Existing | Mass Grid effective-dated changes, Wave 4/5 | Direct | 0 SP | Requires `PRM_IsActive__c = true` filter fix (tracked in risk register) |
| 23 | `PRM_CrossRefBatch` + `PRM_AccountCreationCrossRefBatch` + `PRM_ManualUpdatesCrossRefBatch` | Batch Apex (existing) | Existing — updates cross-reference records | Mass Grid Tax ID, Group Name, NPI changes (any that cascade to cross-refs) | Direct | 0 SP | Existing |
| 24 | `PRM_HcFacilityNetworkAutomationBatch` | Batch Apex (existing) | Existing | Mass Grid Networks, PDA QC | Direct | 0 SP | Existing |
| 25 | `PRM_PracticeLocationAutomationBatch` | Batch Apex (existing) | Existing scheduled | Mass Grid Locations | Mode-Extend | 1 SP (PDM-trigger mode) | Existing; add trigger mode |
| 26 | `PRM_MassAddPractitionerBatch` | Batch Apex | New in Wave 4 | Mass Grid Linking Providers | Direct | 0 SP | This IS the UPHS 107-practitioner use case |
| 27 | `PRM_MassRemovePractitionerBatch` | Batch Apex | New in Wave 4 | Mass Grid Terming Practitioners | Direct | 0 SP | |
| 28 | `PRM_MassAddNetworkBatch` / `PRM_MassRemoveNetworkBatch` | Batch Apex | New in Wave 4 | Mass Grid Networks | Direct | 0 SP | |
| 29 | `PRM_MassAddPracticeLocationBatch` / `PRM_MassTerminatePracticeLocationBatch` | Batch Apex | New in Wave 4 | Mass Grid Locations | Direct | 0 SP | |
| 30 | `PRM_MassAddTaxonomyBatch` / `PRM_MassRemoveTaxonomyBatch` | Batch Apex | New in Wave 4 | Mass Grid (for network-taxonomy cascade) | Direct | 0 SP | |
| 31 | `PRM_MassMailingAddressUpdateBatch` / `PRM_MassBillingAddressUpdateBatch` / `PRM_MassPLAddressUpdateBatch` | Batch Apex | New in Wave 5 | Mass Grid Phone (same target objects), FHNatic | Mode-Extend or Direct | 0–2 SP | |
| 32 | `PRM_PDMOfficeHoursBatch` | Batch Apex | New in Wave 3 | Mass Grid Office Hours (MASS_OFFICE_HOURS mode) | Mode-Extend | 2 SP | 7 days × N slots; existing Wave 3 work |
| 33 | `PRM_PDMDirectoryBatch` (implied in Wave 3 `PRM_PDMPracticeLocationBatch`) | Batch Apex | New in Wave 3 | Mass Grid Info Indicator, Panel Status | Mode-Extend | 2 SP | Bulk flag updates |
| 34 | `PRM_PDMPracticeLocationBatch` | Batch Apex | New in Wave 3 | Mass Grid DBA Name, Group Name cascade | Mode-Extend | 2 SP | Handles non-terminate sub-actions |
| 35 | `PRM_AddressValidationService` (Precisely API) | Apex Service (existing Phase 5) | Existing | Mass Grid Phone & Locations, PSV, Wave 5, FHNatic | Direct | 0 SP | Existing |
| 36 | `PRM_AddressPicklistService` | Apex Service (existing Phase 5) | Existing | Mass Grid, PSV, FHNatic | Direct | 0 SP | Existing |
| 37 | `PRM_LocationQueryService` | Apex Service (existing Phase 5) | Existing | Mass Grid Locations, PSV, PDA QC, FHNatic | Direct | 0 SP | Existing |
| 38 | `PRM_SmartAddressSearch` | Apex Service (existing) | Existing — NPI/Tax ID based lookup | Mass Grid facility lookup, FHNatic | Direct | 0 SP | Existing |
| 39 | `PRM_PARProviderSearch` | Apex Service (existing) | Existing — PAR provider search | Mass Grid practitioner lookup, FHNatic, PSV | Direct | 0 SP | Existing |
| 40 | `PRM_ExistingAccountService` | Apex Service (existing) | Existing — account validation | Mass Grid Group/DBA dedup, FHNatic | Direct | 0 SP | Existing |
| 41 | `prmAddressUtils` (LWC utility) | LWC (existing Phase 5) | Phone formatting, validation, address normalization | Mass Grid Phone cell, FHNatic, PSV, all tile redesigns | Direct | 0 SP | Existing |
| 42 | `prm_verificationDashboard` | LWC (new in App Review redesign) | Parent tile-grid container | All 6 redesigns, **Mass Grid**, **POMS**, **FHNatic** | Config | < 1 SP | Configure tile list |
| 43 | `prm_progressHeader` | LWC (new in App Review redesign) | Progress bar + autosave indicator | Same as #42 | Direct | 0 SP | |
| 44 | `prm_verificationTile` | LWC (new in App Review redesign) | Tile card with status badge | Same as #42 | Direct | 0 SP | |
| 45 | `prm_verificationModal` | LWC (new in App Review redesign) | Dynamic modal wrapper | Same as #42 | Direct | 0 SP | |
| 46 | `prm_navigationFooter` | LWC (new in App Review redesign) | Footer buttons | Same as #42 | Direct | 0 SP | |
| 47 | `prm_fileUpload` | LWC (new in App Review redesign) | Drag-drop multi-file upload | App Review, PSV, PSV QC, ReCred flows, **FHNatic** | Direct | 0 SP | |
| 48 | `prm_practitionerDemographics` | LWC (new in App Review redesign, shared sub-component) | CAQH↔SF demographics comparison | App Review, PSV, PSV QC, ReCred PSV, ReCred PSV QC, **FHNatic** | Config | < 1 SP | `showFields` + `flowType` props |
| 49 | `prm_taxonomyVerification` | LWC (new in App Review redesign, shared sub-component) | Taxonomy multi-row editor | App Review, PSV, PDA QC, **Mass Grid Networks expansion**, **POMS** | Config | < 1 SP | |
| 50 | `prm_finalSubmitBase` | LWC (new in App Review redesign) | Outcome selector + validation | All 6 redesigns + FHNatic | Wrap | 1 SP per flow | Extend for flow-specific outcomes |
| 51 | `PRM_VerificationSession__c` | Custom Object (new in App Review redesign) | Per-user session / autosave storage | Same as #42 | Direct | 0 SP | |
| 52 | `PRM_VerificationTileStatus__c` | Custom Object (new in App Review redesign) | Per-tile status + verification data | Same as #42 | Direct | 0 SP | |
| 53 | `ApplicationReviewController` | Apex Controller (new in App Review redesign) | `fetchApplicationReviewData`, `saveVerificationSession`, `saveVerificationTileStatus` | PSV, QC, ReCred, **FHNatic intake controller pattern** | Adapt | 2–3 SP per new flow | Pattern is fully replicable |
| 54 | `CAQHIntegrationController` | Apex Controller (new in App Review redesign) | CAQH validation + fetch | PSV, ReCred, **FHNatic** (for provider portal CAQH data pull) | Direct | 0 SP | |
| 55 | `prmAddNetworks` | LWC (existing) | Existing network-add modal | Mass Grid Networks cell editor | Direct | 0 SP | |
| 56 | `prmAddInfoCodes` | LWC (existing) | Existing info-code add modal | Mass Grid Info Indicator cell editor | Direct | 0 SP | |
| 57 | `prmCapitationSiteLogic` + `prmInitialCredPDACaptiationLogic` | LWC (existing, used in PDA QC) | Capitation site picker + rules | Mass Grid Cap Sites cell editor, PDA QC tile, POMS | Direct | 0 SP | |
| 58 | `prmCheckClosedNetworkLogic` + `prmCheckClosedNetworkAdditionalAddress` | LWC (existing) | Closed-network rule check | Mass Grid Networks cell (validation), PSV, PDA QC, **FHNatic** | Direct | 0 SP | |
| 59 | `prmAttestationOfficeHourReadOnly` | LWC (existing) | Office hours display | Mass Grid Office Hours cell (extend to edit mode), PSV | Adapt | 2 SP | Add edit mode |
| 60 | `prmAdditionalAddressValidation` / `prmAdditionalAddressBlockForParForm` | LWC (existing, used in PAR form) | Address validation block | **FHNatic provider forms**, Mass Grid Locations | Direct | 0 SP | |
| 61 | `prmAddressGroupManager` | LWC (existing Phase 5) | Primary/billing/mailing address manager | Mass Grid Locations, FHNatic, PSV | Direct | 0 SP | |
| 62 | `prmDisplayLocationContactDetails` / `prmDisplayInitialLocationPracDetails` / `prmDisplayEditableLocationPracDetails` | LWC (existing) | Location-practitioner display/edit | Mass Grid Linking Providers cell, PDA QC, PSV | Direct or Wrap | 0–1 SP | |
| 63 | `prmBatchRecordException` | LWC (existing) | Displays exception records for a batch | Mass Grid error panel, POMS error review, **Data Admin console for failed rows** | Direct | 0 SP | Existing |
| 64 | `prmEditBlockMultiSelect` / `prmEditBlockSingleSelect` / `prmCheckboxList` | LWC (existing) | Multi/single select grid cells | Mass Grid cell editors (Networks, Info Ind, Cap Sites, Panel Status) | Direct | 0 SP | Existing |
| 65 | `prmAddressFilterGrid` | LWC (existing) | Filterable address grid | Mass Grid Locations cell expansion, FHNatic | Direct | 0 SP | Existing |
| 66 | `prmCustomGenericRelatedList` | LWC (existing) | Generic related-list with filters | Mass Grid generic row selector, POMS | Direct | 0 SP | Existing |
| 67 | `PRM_PDMRecordsCreationHelper` (IP, 50+ elements) | Integration Procedure | Existing — driver for PDM PL change sub-actions | Post-Wave 3: simplified; sub-actions go async | Adapt (simplify) | -5 SP (net reduction) | After Wave 3, IP is trimmed to orchestration only |
| 68 | `PRM_PDMRecordsPractitionerCreationHelper` (IP) | Integration Procedure | Existing — driver for PDM Pract. change | Post-Wave 2: simplified | Adapt (simplify) | -5 SP | Same |
| 69 | `PRM_ReviewPSVCaseRecordsUpdate` (IP, 70–90+ elements) | Integration Procedure | Existing — final save for App Review / PSV | Post-redesign: called from `ApplicationReviewController.submitFinalReview()` | Direct | 0 SP | Reused by LWC redesign |
| 70 | `PRM_NetworkManagementQCUpdate` (IP) | Integration Procedure | Existing — final save for PDA QC | Post-redesign: called from QC final submit | Direct | 0 SP | Reused by QC tile redesign |
| 71 | `PRM_FileUploadOS_English` (OmniScript) | OmniScript | Existing — file upload sub-OS | Can be retired after `prm_fileUpload` LWC replaces it | Deprecate | -3 SP (net reduction) | Retirement after redesigns land |
| 72 | `PRM_CredApplicationReviewSubOS_English` (OmniScript) | OmniScript | Existing — App Review sub-OS | Replaced by tile LWCs | Deprecate | -5 SP | Retirement |
| 73 | `PRM_PSVSubOsTxnyRole_English` + `PRM_PSVSubOsSummary_English` + `PRM_PSVSubOsWSNPDB_English` (OmniScripts) | OmniScripts | Existing — PSV sub-OS | Replaced by tile LWCs | Deprecate | -8 SP | Retirement |
| 74 | `PRM_AsyncProcessingStatus__c` (field on IndividualApplication) | Field | Built in Wave 1 | Every async flow | Direct | 0 SP | |
| 75 | `IsNetworkRecordsCreated__c` (field on IndividualApplication) | Field | Built in Wave 1 | Every async flow | Direct | 0 SP | |
| 76 | Email success/failure templates (`PRM_AsyncJob_Success`, `PRM_AsyncJob_Failure`) | Email Template | Built in Wave 1 | Every async flow | Direct | 0 SP | |
| 77 | Data Admin permission set (`PRM_DataAdmin`) | Permission Set | Built in Wave 1 | Every async flow | Direct | 0 SP | |
| 78 | "Network Creation Errors" List View + "Mark Resolved & Route to QC" Quick Action | List View + Quick Action | Built in Wave 1 | Every async flow's failure triage | Direct | 0 SP | Data Admin self-service |
| 79 | `PRM_UseAsyncProcessing__c` (Custom Setting feature flag) | Custom Setting | Built in Wave 1 | Every async flow | Direct | 0 SP | Safe rollback switch |
| 80 | `PRM_BCBSARecordsSyncEvents__e` + `PRM_BCBSABucketObjectConfig__mdt` | Platform Event + Metadata | Existing BCBSA sync | Must be filtered by `PRM_IsActive__c = true` in every async flow (tracked risk #6) | Direct | 0 SP | Existing — just ensure filter |

**Total reusable components inventoried: 80**
(**40** directly reusable at 0 SP; **18** mode-extendable at 1–3 SP; **6** existing LWCs reusable for the mass grid cells; **10** new in the tile redesigns; **6** are retirements that **save** SP.)

---

## 6. OmniScript-by-OmniScript Impact Analysis

This section looks at the **top 15 most-impacted OmniScripts** in the current codebase and shows how each one benefits from the shared batch framework, the tile redesign primitives, or both.

| # | OmniScript | Current Issue | Batch Modules Applicable | UI Components Applicable | Modernization Effort |
|---|---|---|---|---|---|
| 1 | `PRM_PractitionerCreation_English` | Governor limits at 3+ locations; 40+ DML sync | Wave 1 batches (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch` INSERT mode) | None (intake flow, not review) | **0 SP** (Wave 1 owns this) |
| 2 | `PRM_DelegatedPractitionerReviewScreen` | Same as #1 — actually the primary driver of Wave 1 | Wave 1 batches directly | None | **0 SP** (Wave 1) |
| 3 | `PRM_PDMManualUpdatePractitioner_English` | 30+ HFN DML on multi-location practitioner; array cap at ~30 | Mode-extend Wave 1 batches (UPSERT) + `PRM_BatchStagingHelper` | None | **38 SP** (Wave 2 Approach B, already in existing doc) |
| 4 | `PRM_PDMManualUpdate_English` (Practice Location) | 30-network cap; 13 sub-actions all sync; Terminate PL most complex | `PRM_PDMPracticeLocationBatch` + `PRM_PDMTerminatePLBatch` + `PRM_PDMOfficeHoursBatch` (Wave 3) | None | **32 SP** (Wave 3, already in existing doc) |
| 5 | `PRM_InitialCredentialAppReview_English` + sub-OS | 4 MB Save-for-Later limit; all-or-nothing; no inline edit | `ApplicationReviewController` calls existing `PRM_ReviewPSVCaseRecordsUpdate` IP (can be trimmed + made async as Wave 6) | All tile primitives (`prm_verificationDashboard`, `prm_verificationTile`, etc.) + 10 child tile LWCs | **~80–100 SP** (tile redesign; separate initiative) |
| 6 | `PRM_PrimarySourceVerificationReview_English` (186+ elements — the worst offender) | 4 MB limit; read-only; address payload can be 100+ | `ApplicationReviewController` pattern; optional async for final save; address payload reduction via staged `PRM_VerificationTileStatus__c` | All tile primitives + 10 child tile LWCs (including `prm_psvAddressVerification` for 100+ addresses); reuses `PRM_AddressValidationService`, `prmAddressGroupManager` | **~100–120 SP** (PSV tile redesign) |
| 7 | `PRM_PrimarySourceVerificationReview_English` (QC mode) | Same as #6 plus QC verification fields read-only | Same as #6; QC wrapper pattern | Reuses 8 PSV tiles + QC wrapper (`prm_qcWrapper`) + 3 QC-specific tiles | **~30–40 SP** (80% reuse from #6) |
| 8 | `PRM_PrimarySourceVerificationReview_English` (Re-Cred mode) | Same as #6 plus board cert + CMS preclusion + med dir review | Same as #6 + `PRM_UpdateBoardCertification_English` integration | Reuses 8 PSV tiles + 3 Re-Cred-specific tiles | **~30–40 SP** (80% reuse from #6) |
| 9 | `PRM_PrimarySourceVerificationReview_English` (Re-Cred QC mode) | Same as #7 + #8 combined | Same as #7/#8 | Reuses 8 PSV QC tiles + 3 Re-Cred QC tiles | **~25–35 SP** (80% reuse from #7 and #8) |
| 10 | `PRM_InitialCredPDAQC_English` (Network Management QC) | 100+ network options × 20+ PL; capitation site LWC embedded | Mode-extend Wave 4 `PRM_MassAddNetworkBatch` for PDA QC network assignment if moved async | All tile primitives + 7 QC tiles (Practitioner Summary, Specialties, PL Networks, Pract. Networks, Directory Indicators, Cap Sites, QC Outcome); reuses `prmCapitationSiteLogic` | **~50–70 SP** (PDA QC tile redesign) |
| 11 | `PRM_InitialCredPDA_English` | 5 practitioners/batch cap on `InitialCredPDAReviewHFN` Queueable | New `PRM_PDANetworkUpdateBatch` reusing orchestrator + staging | Optional: same PDA QC tiles if moved to tile pattern | **15–20 SP** |
| 12 | `PRM_RecredQC_English` + `PRM_ReCredQCUpdate_English` | Similar to PDA QC with Re-Cred additions | Same as #10 with Re-Cred routing | Reuses PDA QC tiles + Re-Cred-specific tiles | **~30–40 SP** (shares with #10) |
| 13 | `PRM_AncillaryCredApplicationReview_English` + `PRM_AncillaryPSVForm_English` + `PRM_AncillaryPDA_English` + `PRM_AncillaryQC_English` | Same 4 MB + all-or-nothing issues | `PRM_CheckDueOnAncillaryReAssessmentBatch` (existing); async final save | All tile primitives; most App Review/PSV tiles directly apply to Ancillary | **~40–60 SP** total for all 4 ancillary OmniScripts (massive reuse) |
| 14 | `PRM_ProviderChangeForm_English` + `PRM_ProviderChangePDAUpdate_English` + `PRM_ProviderChangeQC_English` | Multi-step provider-change flow; similar perf pain | Wave 4 batches reusable; `PRM_ProvChangeTerminationBatch` (existing) | Tile primitives + reused tiles | **~25–35 SP** |
| 15 | `PRM_NonParReview_English` + `PRM_NonParQCReview_English` + `PRM_NonParProviderRegistration_English` | Similar patterns; non-par flow | Reuse of Wave 1/4 batches; `PRM_MassAddPractitionerBatch` for non-par creation | Tile primitives + reused demographics/taxonomy tiles | **~20–30 SP** |
| 16 | `PRM_PracticeLocationTermination_English` + `PRM_PracticeLocationReinstate_English` | Sync DML for termination chain | `PRM_PracticeLocationTerminationBatch` (existing), `PRM_ManualUpdatePracLocTerminationBatch` (existing) — rewire to async dispatcher | None | **5–8 SP** |
| 17 | `PRM_PractitionerTerminationForm_English` + `PRM_PractitionerTerminationRecredForm_English` + `PRM_PractitionerReinstateForm_English` | Sync DML termination chain | `PRM_PractitionerTerminationBatch` + `PRM_FullPractitionerTerminationBatch` (existing) — rewire | None | **5–8 SP** |
| 18 | `PRM_ManualUpdatesQC_English` + `PRM_ManualUpdatesQCReview1-5_English` (5 variants) | QC flows for manual updates | `PRM_ManualUpdatesCrossRefBatch` (existing); optional tile redesign | Tile primitives reusable | **~15–25 SP** |

**Summary across top 18 OmniScripts:** If only the existing Wave 1–5 perf fixes plus the tile redesigns are completed, approximately **~450–600 SP of downstream modernization work becomes ~40–60% cheaper** than it would be without the shared framework.

---

## 7. POMS Replacement — Revised Estimate

### 7.1 What POMS Is

POMS (Provider Operations Management System) is the legacy system being replaced in PIE (Provider Information Enterprise). It performs many of the same operations the mass grid performs — bulk practitioner-facility-network management — but is a separate codebase with no reuse of the Salesforce framework.

### 7.2 October 2025 Estimate: 80–120 SP

The original estimate assumed POMS replacement would build:
- A new UI for bulk provider/facility/network management (~30–40 SP)
- New Apex batch classes for bulk ops (~25–35 SP)
- A new staging object and dispatcher (~10–15 SP)
- Integration with existing PNM data (~10–15 SP)
- Tests + UAT + deployment (~15–25 SP)

### 7.3 Revised Estimate With Reuse: 42–60 SP

| POMS Component | Old Estimate | New Estimate | What Changed |
|---|---|---|---|
| Bulk management UI | 30–40 SP | 8–12 SP | Tile framework (`prm_verificationDashboard` + primitives) + reused mass-grid cell editors |
| Bulk ops batch classes | 25–35 SP | 5–10 SP | 90% covered by Wave 4 batches + mass-grid batches (NPI, Tax ID, Group Name, etc.) |
| Staging object + dispatcher | 10–15 SP | 0 SP | `PRM_AsyncJobRequest__c` + `PRM_AsyncJobDispatcher` already built |
| Integration with PNM | 10–15 SP | 8–12 SP | Same — this is POMS-specific data migration logic |
| FlexCard / status UI | *included above* | 0 SP | `PRM_PDMJobStatusCard` already built |
| Exception pipeline / Data Admin tooling | *included above* | 0 SP | Built in Wave 1 |
| POMS-specific business rules (legacy parity) | *included above* | 15–20 SP | POMS has some unique rules not in PNM (e.g., legacy panel calc logic) |
| Tests + UAT + deployment | 15–25 SP | 6–10 SP | AI-assisted + shared harness |
| **TOTAL** | **80–120 SP** | **42–60 SP** | **~45% reduction** |

### 7.4 POMS-Specific Considerations Not Covered By Reuse

The ~15–20 SP of irreducible POMS effort covers:
- Legacy POMS business rules that do not exist in PNM today (panel-status recalculation algorithm, regional contract-specific overrides)
- Data migration and reconciliation between POMS and PNM during cutover
- POMS-specific audit report generation

---

## 8. FHNatic Provider Forms — How Mass Grid & Batch Framework Help

### 8.1 What FHNatic Is

FHNatic is the external-facing provider portal that exposes a subset of PDM flows to providers directly, letting them self-service certain data updates (address changes, practice hours, panel status, etc.) via a web portal.

### 8.2 October 2025 Estimate: 32–52 SP

The original estimate assumed FHNatic would build:
- External portal UI (Experience Cloud site) — 10–15 SP
- Form-to-Salesforce submission pipeline — 8–12 SP
- Validation layer (anti-abuse, rate limiting) — 5–8 SP
- Backend processing — 5–10 SP
- Tests + UAT + deployment — 4–7 SP

### 8.3 Revised Estimate With Reuse: 18–28 SP

| FHNatic Component | Old Estimate | New Estimate | What Changed |
|---|---|---|---|
| External portal UI (Experience Cloud) | 10–15 SP | 6–10 SP | Tile framework + reused demographics/address LWCs (`prm_practitionerDemographics`, `prmAddressGroupManager`, `prmAdditionalAddressValidation`) |
| Form-to-SF submission pipeline | 8–12 SP | 2–4 SP | `PRM_SubmitAsyncJob` IP + `PRM_AsyncJobRequest__c` directly reusable as the intake pipeline |
| Validation layer | 5–8 SP | 3–5 SP | Reuses `PRM_AddressValidationService`, `prmCheckClosedNetworkLogic`, `PRM_ExistingAccountService` |
| Backend processing | 5–10 SP | 0 SP | Mass grid batches handle the actual changes; FHNatic just queues via dispatcher |
| Status / notification to provider | *included above* | 1–2 SP | `PRM_PDMJobStatusCard` FlexCard + email templates directly reusable |
| Tests + UAT + deployment | 4–7 SP | 3–5 SP | AI-assisted; shared harness |
| External portal hardening (auth, CSP, rate limit) | *included above* | 3–4 SP | FHNatic-specific security hardening |
| **TOTAL** | **32–52 SP** | **18–28 SP** | **~45% reduction** |

### 8.4 Net Effect: FHNatic Becomes a Thin Portal

After the framework and tile primitives land, FHNatic is effectively a **thin external skin** on top of the existing internal infrastructure:
- The provider clicks "Update Office Hours" on the portal
- The portal submits to `PRM_SubmitAsyncJob` IP (the same IP internal users submit to)
- The IP writes to `PRM_AsyncJobRequest__c` with `FlowType = 'PDMPracticeLocationChange'`, `SubType = 'UpdateOfficeHours'`, `Source = 'FHNatic'`
- Wave 3's `PRM_PDMOfficeHoursBatch` picks it up and processes it
- The provider gets an email notification from the same Wave 1 template
- The Data Admin sees any failures in the same "Network Creation Errors" list view

FHNatic becomes a **UI layer**, not a parallel system.

---

## 9. Updated Grand Total Comparison

### 9.1 Three-Column Comparison

| Initiative | Old Estimate (Oct 2025) | New Estimate (With Framework + Tile Reuse) | Savings | Notes |
|---|---|---|---|---|
| **Mass Grid Replacement** | 130 SP | **58–72 SP** | **58–72 SP (~50% reduction)** | 4 of 13 operations covered by Wave 4 batches; tile framework provides UI; staging, event, dispatcher, FlexCard delivered by Waves 1/4 |
| **POMS Replacement in PIE** | 80–120 SP | **42–60 SP** | **38–60 SP (~45% reduction)** | Async infra fully reused; mass-grid batches cover most ops; residual effort is POMS-specific legacy rules + data migration |
| **FHNatic Provider Forms** | 32–52 SP | **18–28 SP** | **14–24 SP (~45% reduction)** | Becomes thin external UI on top of shared infrastructure; reuses tile primitives + Precisely + mass-grid batches |
| **Performance Fix Wave 2** (PDM Pract.) | *not in Oct 2025 scope* | **38 SP** (already in existing doc) | — | Carried from existing estimation doc |
| **Performance Fix Wave 3** (PDM PL) | *not in Oct 2025 scope* | **32 SP** | — | Carried from existing estimation doc |
| **Performance Fix Wave 4** (Mass Updates backbone) | *not in Oct 2025 scope* | **65 SP** | — | Carried from existing estimation doc |
| **Performance Fix Wave 5** (Mass Addresses) | *not in Oct 2025 scope* | **28 SP** | — | Carried from existing estimation doc |
| **App Review tile redesign** | *not in scope Oct 2025* | **~80–100 SP** | — | Standalone initiative; delivers tile primitives used everywhere |
| **PSV tile redesign** | *not in scope Oct 2025* | **~100–120 SP** | — | Largest tile redesign; 186-element OmniScript replacement |
| **PSV QC + ReCred PSV + ReCred PSV QC + PDA QC redesigns** | *not in scope Oct 2025* | **~130–175 SP** (total for all four) | — | 80% reuse from App Review + PSV redesigns |
| **Three original initiatives (Mass Grid + POMS + FHNatic) TOTAL** | **242–302 SP** | **118–160 SP** | **124–142 SP (~47% average reduction)** | |

### 9.2 Why the Savings Are Possible

The savings are not magic — they come from **three concrete investments** being made for other reasons, whose outputs happen to be precisely what Mass Grid / POMS / FHNatic need:

1. **Wave 1 Practitioner Creation Framework** (in-flight, ~80 SP)
   - Delivers: Platform Event, Orchestrator, 3 mode-parameterized batch classes, `PRM_ExceptionLogEvent__e` + `PRM_ExceptionLogger`, `PRM_FailedRecordStaging__c`, Data Admin tooling, email templates, feature flag, permission set.
   - This is **already funded** as a production-blocking fix for the 15–20 support-tickets-per-week problem.

2. **Wave 4 Mass Updates Framework** (next quarter, 65 SP)
   - Delivers: `PRM_AsyncJobRequest__c` + `PRM_AsyncJobQueued__e` + `PRM_AsyncJobDispatcher` + `PRM_PDMJobStatusCard` FlexCard + 8 mass batch classes (`PRM_MassAddPractitionerBatch` et al.)
   - This is **already funded** as the solution to the UPHS 107-practitioner mass load problem.

3. **App Review / PSV / QC / ReCred Tile Redesigns** (next 2–3 quarters, ~320–395 SP combined)
   - Delivers: Tile dashboard + tile + modal + progress primitives, `PRM_VerificationSession__c` + `PRM_VerificationTileStatus__c`, `ApplicationReviewController`, `CAQHIntegrationController`, 10+ child tile LWCs, session persistence / autosave / resume-anywhere.
   - This is **already funded** as the solution to the 4 MB Save-for-Later limit + read-only-field complaints.

When all three are done, **Mass Grid is the thinnest possible assembly on top**:
- 9 new thin batch classes (avg 3 SP each) = ~20 SP
- 7 new thin grid-cell LWCs (avg 1.5 SP each) = ~10 SP
- 1 new parent LWC (`prm_massGridDashboard`) = ~4 SP
- CSV import + grid UX polish = ~10 SP
- Tests + UAT + deployment = ~10 SP
- **Total = ~54–72 SP** (matches the 58–72 SP range above)

And POMS and FHNatic become **configurations of the same framework**.

---

## 10. Implementation Sequencing

### 10.1 Dependency Graph

```
┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 0 — FOUNDATION (parallel tracks, already funded)                     │
│                                                                            │
│   Track A: Wave 1 (Practitioner Creation)                                  │
│     ~80 SP | 8 weeks | in-flight                                           │
│     Delivers: Platform Event, Orchestrator, 3 batch classes,               │
│               Exception pipeline, FailedRecordStaging, Data Admin tools    │
│                                                                            │
│   Track B: App Review Tile Redesign (Phase 1 — Foundation)                 │
│     ~30–40 SP | 4 weeks | queued after approval                            │
│     Delivers: prm_verificationDashboard/Tile/Modal/Progress/Footer,        │
│               PRM_VerificationSession__c, PRM_VerificationTileStatus__c,   │
│               prm_fileUpload, prm_practitionerDemographics,                │
│               prm_taxonomyVerification, prm_finalSubmitBase                │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (Layer 0 completed → Layer 1 can start)
┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1 — DOMAIN BUILD-OUT (parallel tracks after Layer 0)                 │
│                                                                            │
│   Track C: Waves 2 + 3 (PDM Pract. + PDM PL)                               │
│     38 + 32 = 70 SP | 8–10 weeks parallel                                  │
│                                                                            │
│   Track D: Wave 4 (Mass Updates backbone)                                  │
│     65 SP | 10 weeks                                                       │
│     Delivers: PRM_AsyncJobRequest__c, PRM_AsyncJobQueued__e,               │
│               PRM_AsyncJobDispatcher, PRM_PDMJobStatusCard FlexCard,       │
│               8 mass batch classes (the "free" 4 mass-grid ops)            │
│                                                                            │
│   Track E: App Review Tile Redesign (Phase 2+3 — Tiles + Testing)          │
│     ~40–60 SP | 6–8 weeks parallel                                         │
│     Delivers: 10 App Review tile child LWCs                                │
│                                                                            │
│   Track F: PSV Tile Redesign (Phase 1)                                     │
│     ~40–60 SP | 6–8 weeks parallel                                         │
│     Delivers: 10 PSV tile child LWCs (80% reuse from App Review)           │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (Layer 1 completed → Layer 2 can start)
┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2 — HIGH-LEVERAGE ASSEMBLY                                           │
│                                                                            │
│   Track G: Wave 5 (Mass Addresses)                                         │
│     28 SP | 5 weeks                                                        │
│                                                                            │
│   Track H: Mass Grid Replacement                                           │
│     58–72 SP | 8–10 weeks                                                  │
│     Delivers: prm_massGridDashboard + 13 grid cell LWCs                    │
│               + 7 new thin batch classes + CSV import                      │
│                                                                            │
│   Track I: PSV QC + ReCred PSV + ReCred PSV QC + PDA QC tile redesigns     │
│     ~130–175 SP (total) | 12–16 weeks (mostly parallel)                    │
│                                                                            │
│   Track J: POMS Replacement                                                │
│     42–60 SP | 8–10 weeks (requires Mass Grid or parallel to it)           │
│                                                                            │
│   Track K: FHNatic Provider Forms                                          │
│     18–28 SP | 4–6 weeks                                                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3 — DOWNSTREAM MODERNIZATION (optional, uses residual primitives)    │
│                                                                            │
│   Ancillary flows (4 OmniScripts) tile redesign: ~40–60 SP                 │
│   Provider Change flow tile redesign: ~25–35 SP                            │
│   Non-Par flow tile redesign: ~20–30 SP                                    │
│   Manual Updates QC 1–5 variants: ~15–25 SP                                │
│   PDA Review (Initial + ReCred) tile redesign: ~30–40 SP                   │
│                                                                            │
│   Total Layer 3: ~130–190 SP — all at heavy discount vs. ground-up cost   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Calendar Timeline (with 2 senior devs + AI-assisted pair)

| Quarter | Layer 0 | Layer 1 | Layer 2 | Layer 3 |
|---|---|---|---|---|
| **Q2 2026** (current) | Wave 1 finishing; App Review Phase 1 starting | — | — | — |
| **Q3 2026** | Complete | Waves 2+3+4 parallel; App Review Phase 2; PSV Phase 1 | — | — |
| **Q4 2026** | — | App Review final; PSV final; Wave 5 starts | Mass Grid starts; PSV QC/PDA QC start | — |
| **Q1 2027** | — | — | Mass Grid complete; POMS starts; ReCred tiles | Ancillary / Provider Change starts |
| **Q2 2027** | — | — | POMS complete; FHNatic launches | Layer 3 continues |

### 10.3 Critical-Path Observations

1. **Wave 1 is the single biggest dependency.** Every subsequent track (except App Review Phase 1) waits on Wave 1 being deployed to QA. Protecting Wave 1's schedule protects every downstream savings.
2. **App Review Phase 1 is on the critical path for the tile approach.** Without the primitives (`prm_verificationDashboard`, `prm_verificationTile`, `PRM_VerificationSession__c`), neither PSV nor Mass Grid nor FHNatic can begin their UI build.
3. **Wave 4 is on the critical path for Mass Grid, POMS, and FHNatic** (all three require `PRM_AsyncJobRequest__c` + dispatcher + FlexCard).
4. **POMS and Mass Grid overlap by design.** POMS can start in parallel with Mass Grid once the async framework is in place, sharing most of the same new batch classes.
5. **FHNatic is the cheapest add-on**, because by the time it starts, literally every piece of infrastructure it needs is already in production.

### 10.4 Risk Call-Outs

| Risk | Mitigation |
|---|---|
| Wave 1 delay cascades to everything | Wave 1 is already on a hard timeline; no speculative extras are added to its scope. Risk tracked in existing doc. |
| App Review Phase 1 stakeholder signoff slippage | Phase 1 (primitives + foundation objects) is decoupled from Phase 2 (tile content); Phase 1 can proceed on a framework-only scope and be validated without waiting for Phase 2 business signoff. |
| Framework primitives over-fit to App Review and don't reuse for Mass Grid cleanly | Primitive API is being designed with tile-list-as-config (not hard-coded tile types). Mass Grid validates the reuse claim early; if gaps emerge, they can be hardened in Phase 2 of App Review. |
| OmniScript retirements (#71–73 in master table) blocked by compliance/audit concerns | Feature flag `PRM_UseAsyncProcessing__c` keeps old OmniScripts deployable with `isActive: false` for rollback-with-no-redeploy. |
| CSV import for Mass Grid becomes a rabbit hole (encoding, validation, progress reporting) | Reuse existing intake patterns; CSV is just another source feeding into `PRM_AsyncJobRequest__c`. |
| Tile framework session-persistence object (`PRM_VerificationSession__c`) concurrency under heavy mass-grid use | Design assumes single-user-per-session; concurrent editing handled via record lock + "In Use by X" indicator (already in App Review redesign spec). |

---

## Appendix A — Cross-References

### A.1 Companion Documents

- `requirements/Enhancements/HighVolume_GuidedFlows_Performance_Estimation.md` — the foundation document this one complements
- `requirements/PRM_HighVolume_Processing_SK_Estimation.md` — original Story K estimation (baseline)
- `requirements/Application_Review_LWC_Redesign_Detailed_Design.md` — tile approach master (Phase 1 source of primitives)
- `requirements/PSV_Review_LWC_Redesign_Detailed_Design.md` — largest redesign (186+ element OmniScript)
- `requirements/PSV_QC_Review_LWC_Redesign_Detailed_Design.md` — QC wrapper pattern
- `requirements/PDA_QC_Review_LWC_Redesign_Detailed_Design.md` — Network Management QC redesign
- `requirements/ReCred_PSV_Review_LWC_Redesign_Detailed_Design.md` — Re-Cred PSV variant
- `requirements/ReCred_PSV_QC_Review_LWC_Redesign_Detailed_Design.md` — Re-Cred PSV QC variant
- `requirements/UPHS_MASS_LOAD_SOLUTIONS.md` — 107-practitioner mass-load reference (validates the Linking Providers op)
- `requirements/TDD_PDMManualUpdate_Practitioner_LargeDataOptimization.md` — Wave 2 Approach A detailed design
- `requirements/TDD_PDMManualUpdate_Practitioner_IPToApex.md` — Wave 2 Approach B detailed design
- `requirements/PRM_Batch_Rollback_Strategies.md` — rollback patterns (UNION ALL fix)
- `requirements/PractitionerCreationPerformance/PRM_NetworkCreation_BatchImplementation_Guide.md` — Wave 1 batch implementation reference
- `requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md` — staging object spec
- `requirements/PractitionerCreationPerformance/US_PractitionerCreation_Complete_Implementation.md` — Wave 1 user stories

### A.2 Calibration

All SP estimates in this document use the same calibration as the companion `HighVolume_GuidedFlows_Performance_Estimation.md`:

- **1 SP ≈ 0.6 developer days** (AI-assisted pair with senior dev)
- **1 SP ≈ 1.0 developer days** (traditional non-AI baseline, for reference)
- **Calendar conversion:** assume 8 productive SP per developer per week (inclusive of code review, testing, meetings)

### A.3 Unverified Assumptions (IBX Review Needed)

1. The exact field list for "Info Indicator" across location / practitioner / network levels — the document assumes `PRM_InfoCodeAssignment__c` + `PractitionerLocationInfoCode` + `PractitionerInfoCode`, needs IBX confirmation.
2. Panel Status field location — the document assumes `HealthcarePractitionerFacility.PRM_PanelStatus__c` + `HealthcareFacilityNetwork.PRM_AcceptingNewPatients__c`; needs IBX confirmation which is source of truth.
3. POMS legacy rules scope — the 15–20 SP residual for POMS-specific logic is a placeholder pending a POMS business-rules audit.
4. FHNatic security hardening requirements — the 3–4 SP for auth/CSP/rate-limit is a placeholder pending a security architecture review.
5. Whether existing LWCs `prmInitialCredPDACaptiationLogic` and `prmCapitationSiteLogic` can be directly embedded as grid cells, or require a wrapper — confirmed by inspection of LWC folder; exact API surface needs a 1-day spike.
6. Office Hours grid-cell UX — whether 7-day schedule is editable in a grid cell or expands to a modal; this document assumes modal expansion (cleaner UX, reuses `prm_verificationModal`).

---

*End of Document*
