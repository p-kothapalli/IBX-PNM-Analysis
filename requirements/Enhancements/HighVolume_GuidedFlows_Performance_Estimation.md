# High-Volume Guided Flow Performance Improvement
## Comprehensive Estimation, Architecture & Business Benefits

**Document Type:** Enhancement Estimation & Architecture Design  
**Vertical:** Provider Network Management (PNM) — Provider Data Management (PDM)  
**Business Ask:** Ability to process transactions in guided flows that require high-volume record creation/processing  
**Document Owner:** Salesforce Architecture  
**Audience:** Business Stakeholders, Project Management, Senior Developers, QA Lead  
**Date:** 2026-04-23  
**Status:** Draft for IBX Review  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Current Limitations](#2-problem-statement--current-limitations)
3. [Scope of Affected Flows](#3-scope-of-affected-flows)
4. [Root Cause Analysis](#4-root-cause-analysis)
5. [Architecture Vision: Modular Reusable Batch Framework](#5-architecture-vision-modular-reusable-batch-framework)
6. [Flow-by-Flow Breakdown & Approach Options](#6-flow-by-flow-breakdown--approach-options)
   - 6A. PDM Manual Change — Practitioner
   - 6B. PDM Manual Change — Practice Location
   - 6C. Mass Updates (Add/Remove Practitioners, Networks, Practice Locations, Taxonomies)
   - 6D. Mass Update Mailing/Billing Addresses (New)
7. [Reuse Strategy: Plug-and-Play Batch Modules](#7-reuse-strategy-plug-and-play-batch-modules)
8. [Removing Limits in Existing OmniScripts](#8-removing-limits-in-existing-omniscripts)
9. [Estimation Summary — All Approaches](#9-estimation-summary--all-approaches)
10. [Business Benefits](#10-business-benefits)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Risk Register](#12-risk-register)
13. [Definition of Done](#13-definition-of-done)

---

## 1. Executive Summary

The IBX Provider Data Management (PDM) platform currently suffers from a class of governor-limit failures that surface as UI freezes, silent partial-data writes, and support escalations whenever a guided flow processes a practitioner or practice location with more than 2–3 associated records. The root cause is consistent across every affected flow: **synchronous Integration Procedure (IP) chains that attempt to create or update 50–500 Salesforce records inside a single Apex transaction that has a fixed governor budget it cannot exceed.**

This document estimates the effort to resolve these failures for every flow identified in the business ask, provides two design approaches per flow (a lower-risk incremental option and a fully future-proof batch-Apex option), and quantifies the infrastructure reuse that makes the second and third flows dramatically cheaper than the first.

**The core insight driving this estimation:**  
The Practitioner Creation performance fix (Wave 1, currently in-flight) is being built as a **reusable framework** — a Platform Event, an orchestrator, three chained Batch Apex classes, a staging/logging infrastructure, and a Data Admin toolset. Every subsequent flow in this estimation (PDM Manual Change — Practitioner, PDM Manual Change — Practice Location, Mass Updates, Mass Address Updates) **extends** that framework rather than rebuilding it. The cost of each successive flow drops sharply because 60–75% of the infrastructure is already delivered.

### High-Level Estimates

| Flow / Enhancement | Approach | Story Points | Calendar Weeks | Confidence |
|---|---|---|---|---|
| **PDM Manual Change — Practitioner** | Approach A (Queueable IP refactor) | 57 SP | 10 weeks | High |
| **PDM Manual Change — Practitioner** | Approach B (Full Batch Apex, recommended) | 38 SP | 6 weeks* | High |
| **PDM Manual Change — Practice Location** | Approach A (Queueable IP refactor) | 45 SP | 8 weeks | High |
| **PDM Manual Change — Practice Location** | Approach B (Full Batch Apex) | 32 SP | 6 weeks* | High |
| **Mass Updates (Add/Remove Pract., Networks, PL, Taxonomy)** | Batch Apex + async dispatch | 65 SP | 10 weeks | Medium |
| **Mass Update Mailing/Billing Addresses (New)** | Batch Apex + async dispatch | 28 SP | 5 weeks* | Medium |
| **OmniScript Limit Removal (all flows)** | Shared async + UI changes | 15 SP | Included above | High |

*Dependent on Wave 1 Practitioner Creation framework being deployed to QA first.

**Total gross effort (no reuse):** ~345 SP  
**Total net effort (with reuse):** ~223 SP  
**Framework reuse savings:** ~122 SP (~35% reduction)

---

## 2. Problem Statement & Current Limitations

### 2.1 Governor Limit Failures in Guided Flows

Every affected PDM and mass-update flow follows the same anti-pattern:

```
OmniScript (user submits)
  └─ Container IP (rollbackOnError = true)
       ├─ Child IP 1: Address / Facility / Location (50-100 ops)
       ├─ Child IP 2: HCPF / Features / Affiliations (50-80 ops)
       └─ Child IP 3: Taxonomy / Payer Network / IFC (180-280 ops)
                                                      ↑
                      TOTAL: 280–494 ops per practitioner
                      SYNCHRONOUS BUDGET: 100 SOQL / 10,000ms CPU / 6MB heap
```

When the budget runs out, the OmniScript UI freezes for 3–8 minutes, and either:
- The transaction hard-fails with a generic "Save failed" error, OR
- The transaction partially completes (IP1 committed, IP2/IP3 rolled back), leaving the data in an inconsistent state with **no error surfaced to the user**

### 2.2 Measured Limits and Thresholds

| Limit Type | Synchronous Budget | Queueable Budget | What PDM Update Needs |
|---|---|---|---|
| SOQL Queries | 100 | 200 | 443–494 total ops (3-location) |
| CPU Time | 10,000 ms | 60,000 ms | ~40,000+ ms at 3+ locations |
| Heap Size | 6 MB | 12 MB | ~8–10 MB (5-location, including delta state) |
| DML Rows | 10,000 | 10,000 | 90–120 DML rows per batch execute at size 5 |

### 2.3 Current Business Impact (Observed)

| Impact Dimension | Current State |
|---|---|
| UI freeze duration | 3–8 minutes for practitioners with 3+ locations |
| Effective hard timeout | 10 minutes (OmniScript session limit) |
| Support ticket volume | 15–20 tickets/week (combined creation + update queue) |
| Data integrity risk | Cross-object partial state: affiliations refreshed, network records stale |
| Operations cost | 1–2 hours per incident for Data Admin manual reconciliation |
| Reputational risk | Network Maintenance teams bypassing PDM for practitioners with many locations |
| Manual workaround cost | 2–3 hours per practitioner (manual record creation) |

### 2.4 Current OmniScript Hard Limits

Several OmniScripts have hard-coded record limits (array size caps, pagination limits) that prevent business from submitting requests above a threshold. Examples identified in the codebase:

- `PRM_PDMManualUpdate_English`: `MergedNetworks` array limited to N entries before the DR times out
- `PRM_PDMManualUpdatePractitioner_English`: `PractitionerPracLocTaxAndNetworks` array loop caps at ~30 records
- Mass update flows: No batch processing; all records must fit in a single IP execution

**The business ask to "remove those limits" requires redesigning these flows to be async — the limits cannot be removed without replacing the synchronous execution model.**

---

## 3. Scope of Affected Flows

### 3.1 Flows In Scope

| Flow | OmniScript Key | Primary IP Chain | Current Failure Threshold |
|---|---|---|---|
| PDM Manual Change — Practitioner | `PRM_PDMManualUpdatePractitioner_English` | `PRM_PDMRecordsCreationParent` → `PRM_PDMRecordsPractitionerCreationHelper` | 3+ practice locations |
| PDM Manual Change — Practice Location | `PRM_PDMManualUpdate_English` | `PRM_PDMRecordsCreationParent` → `PRM_PDMRecordsCreationHelper` (50+ elements) | 30+ networks, 10+ affiliations |
| Mass Add Practitioners | TBD (new or enhancement to existing PL flow) | `PRM_PDMPLRecordsCreationHelper` | No batching exists today |
| Mass Remove Practitioners | TBD | `PRM_PDMUnlinkPracticeLocationHelper` | No batching exists today |
| Mass Add/Remove Networks | `PRM_PDMManualUpdate_English` (CB_AddRemoveNetworks) | `DRLoadManualUpdatePLNetworks` | ~30 networks before timeout |
| Mass Add/Remove Practice Locations | TBD | Multiple IPs | No batching exists today |
| Mass Add/Remove Taxonomies | TBD | `CB_AddorTerminatePLTaxonomy` | ~10 taxonomies before timeout |
| Mass Update Mailing/Billing Addresses | **New flow** | New batch required | No flow exists today |

### 3.2 Existing Batch Classes (Available for Reuse)

The following batch classes already exist in `force-app/main/default/classes/` and can be wired into the new async framework:

| Existing Class | Current Use | Reuse Opportunity |
|---|---|---|
| `PRM_PractitionerActivationBatch` | Activated synchronously from PDM PL flow | Wire into async dispatcher (batch size review needed) |
| `PRM_PracticeLocationAutomationBatch` | Scheduled automation | Extend with PDM-trigger mode |
| `PRM_FullPractitionerTerminationBatch` | Termination flows | Already async — reuse pattern |
| `PRM_AccountCreationCrossRefBatch` | Cross-reference creation | Pattern reuse |
| `PRM_FutureAddressActivateBatch` | Scheduled address activation | Extend for PDM address updates |

---

## 4. Root Cause Analysis

### 4.1 The Three Failure Modes

**Mode 1 — SOQL limit breach (100 synchronous)**  
The container IP executes under the synchronous-Apex limit of 100 SOQL queries. The PDM Manual Update for a 3-location practitioner requires: existing-record delta queries for each of 54 network records + support queries = 100+ SOQL before DML begins. The IP fails at the query phase. Symptom: "Save failed" after 2–3 minutes.

**Mode 2 — CPU limit breach (10,000 ms synchronous / 60,000 ms async)**  
IP2 recomputes affiliations, provider features, and CDM updates synchronously for each location. At 5+ locations, the delta computation alone consumes 8–12 seconds — on top of the other IP's budget. Symptom: UI freeze; eventually fails with `UNEXPECTED_SCRIPT_ERROR`.

**Mode 3 — Heap limit breach (12 MB async)**  
IP3 holds the incoming network payload (desired state) AND the query result (existing state) simultaneously for delta computation. For a 5-location practitioner: ~6 MB desired + ~4 MB existing + OmniStudio stack frames = >12 MB. Symptom: `System.LimitException: Apex heap size too large`.

### 4.2 Why Queueable IP Refactoring (TX1/TX2/TX3) Has Limits

The Wave 2 (Approach A) Queueable refactoring documented in `TDD_PDMManualUpdate_Practitioner_LargeDataOptimization.md` resolves the immediate governor-limit issue for practitioners with up to ~5 locations. However, it has known structural limits:

1. **The TX2→TX3 Queueable chain cannot be integration-tested** in the standard sandbox test harness (1-level chaining limit suppresses TX3 silently)
2. **OmniStudio has no native partial-success DML** — `rollbackOnError = true` is the only mode; a TX3 failure rolls back the entire transaction and may mask stale data
3. **TX1 still blocks the UI** for very large practitioners (5+ locations), because IP1 remains synchronous
4. **Per-transaction operation count for PDM update is 60–75% higher than creation** (443–494 ops vs. 280 ops) due to mandatory delta-query reads before every DML

### 4.3 Why Batch Apex (Approach B) Is the Recommended Architecture

Batch Apex resolves every problem simultaneously:

| Problem | Queueable Approach | Batch Apex Approach |
|---|---|---|
| SOQL limit | Split into 3 transactions (200/ea) | Fresh 200-query budget per `execute()` call |
| CPU limit | Split into 3 transactions (60s/ea) | Fresh 60s per `execute()` call |
| Heap limit | 12 MB per Queueable | Fresh 12 MB per `execute()` call |
| Partial-success DML | Not available in IPs | `Database.upsert(records, extId, false)` |
| Integration testability | TX3 silently skipped in tests | Full chain tested under `Test.startTest()` |
| Scale ceiling | ~5 locations before limits | 50 million rows via `QueryLocator` |
| Idempotency on retry | Insert-mode → duplicate risk | Upsert-mode → safe retry always |

---

## 5. Architecture Vision: Modular Reusable Batch Framework

### 5.1 The "Plug-and-Play" Framework

The central design principle is that **every async processing flow shares one framework and one set of infrastructure**. The framework is being built once (for Practitioner Creation, Wave 1). All subsequent flows extend it with flow-specific Batch Apex modules that snap in as plug-and-play components.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SHARED FRAMEWORK (built once in Wave 1)                   │
│                                                                              │
│  NetworkCreationRequested__e (Platform Event)                                │
│    └─ Mode__c field: 'INSERT' | 'UPSERT' | 'MASS_ADD' | 'MASS_REMOVE' | ... │
│                                                                              │
│  PRM_NetworkCreationEventTrigger                                             │
│    └─ Routes to PRM_NetworkCreationOrchestrator.handleEvent(event)           │
│                                                                              │
│  PRM_NetworkCreationOrchestrator                                             │
│    └─ Reads Mode + FlowType → dispatches to correct Batch chain             │
│                                                                              │
│  PRM_ExceptionLogEvent__e (rollback-safe exception logging)                  │
│  PRM_ExceptionLogEventTrigger → PRM_ExceptionLog__c records                  │
│  PRM_ExceptionLogger.logExceptionViaEvent()                                  │
│                                                                              │
│  PRM_FailedRecordStaging__c (42-field partial-success staging object)        │
│  Data Admin list views, Quick Actions, Permission Set                        │
│  Email notification templates (success/failure)                              │
│  PRM_AsyncProcessingStatus__c + IsNetworkRecordsCreated__c on IA             │
└─────────────────────────────────────────────────────────────────────────────┘
                │                    │                    │
                ▼                    ▼                    ▼
┌───────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────┐
│  PDM MANUAL       │  │  PDM MANUAL         │  │  MASS UPDATE MODULES        │
│  PRACTITIONER     │  │  PRACTICE LOCATION  │  │                             │
│  (UPSERT mode)    │  │  (UPSERT mode)      │  │  PRM_MassAddPractBatch      │
│                   │  │                     │  │  PRM_MassRemovePractBatch   │
│  TaxonomyBatch    │  │  TaxonomyBatch      │  │  PRM_MassNetworkBatch       │
│  (UPSERT)         │  │  (UPSERT)           │  │  PRM_MassTaxonomyBatch      │
│                   │  │                     │  │  PRM_MassAddressBatch       │
│  PayerNwBatch     │  │  PayerNwBatch       │  │  (all reuse shared          │
│  (UPSERT)         │  │  (UPSERT)           │  │   infra + staging object)   │
│                   │  │                     │  │                             │
│  IFCBatch         │  │  IFCBatch           │  │                             │
│  (UPSERT)         │  │  (UPSERT)           │  │                             │
└───────────────────┘  └─────────────────────┘  └─────────────────────────────┘

Each module:
  ✅ Gets fresh governor limits per execute() call
  ✅ Uses Database.upsert(records, externalId, false) — partial success
  ✅ Stages per-row failures to PRM_FailedRecordStaging__c
  ✅ Logs transaction-level failures via PRM_ExceptionLogEvent__e
  ✅ Updates CaseManager status: Not Started → Queued → Processing X → Completed/Failed
  ✅ Sends email notification on chain completion
  ✅ Is fully integration-testable via Test.startTest()/stopTest()
```

### 5.2 Mode Parameter Propagation

A single `Mode__c` field on the Platform Event carries the processing mode through the entire chain. This enables the same three batch classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) to handle both INSERT (creation) and UPSERT (update) modes — plus new modes for mass operations — without code duplication.

```
Platform Event: NetworkCreationRequested__e
  Mode__c values:
    'INSERT'          → Practitioner Creation (Wave 1)
    'UPSERT'          → PDM Manual Change Practitioner (Wave 2)
    'UPSERT_PL'       → PDM Manual Change Practice Location (Wave 3)
    'MASS_ADD_PRACT'  → Mass Add Practitioners (Wave 4)
    'MASS_REM_PRACT'  → Mass Remove Practitioners (Wave 4)
    'MASS_NETWORK'    → Mass Add/Remove Networks (Wave 4)
    'MASS_TAXONOMY'   → Mass Add/Remove Taxonomies (Wave 4)
    'MASS_ADDRESS'    → Mass Update Mailing/Billing Addresses (Wave 5)
```

### 5.3 Reuse Accounting

Every component in the table below marked **Direct (0 effort)** was built in Wave 1 and is consumed by all subsequent waves at zero marginal cost.

| Component | Wave 1 | Wave 2 (PDM Pract.) | Wave 3 (PDM PL) | Wave 4 (Mass) | Wave 5 (Address) |
|---|---|---|---|---|---|
| `NetworkCreationRequested__e` | Built | Reused (add Mode field) | Reused | Reused | Reused |
| Event Trigger + Orchestrator | Built | Mode-extended (S) | Mode-extended (XS) | Mode-extended (S) | Mode-extended (XS) |
| `PRM_TaxonomyNetworkBatch` | Built | Mode-extended (M) | Mode-extended (XS) | New sub-mode (M) | N/A |
| `PRM_PayerNetworkBatch` | Built | Mode-extended (M) | Mode-extended (XS) | New sub-mode (M) | N/A |
| `PRM_IFCRecordBatch` | Built | Mode-extended (M) | Mode-extended (XS) | New sub-mode (S) | N/A |
| `PRM_ExceptionLogEvent__e` + trigger | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| `PRM_ExceptionLogger.logExceptionViaEvent` | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| `PRM_FailedRecordStaging__c` (42 fields) | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| Data Admin list views + Quick Actions | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| Email success/failure templates | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| `PRM_AsyncProcessingStatus__c` field | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| `IsNetworkRecordsCreated__c` field | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| Data Admin permission set | Built | **Direct (0)** | **Direct (0)** | **Direct (0)** | **Direct (0)** |
| `PRM_BatchStagingHelper` utility | Built (Wave 2) | Built here | **Direct (0)** | **Direct (0)** | **Direct (0)** |

---

## 6. Flow-by-Flow Breakdown & Approach Options

---

### 6A. PDM Manual Change — Practitioner

**OmniScript:** `PRM_PDMManualUpdatePractitioner_English`  
**Current failure threshold:** 3+ practice locations  
**Record volume per submission:** 443–494 total operations (180–225 payer networks + 36–54 taxonomy networks + 45–60 IFC records + deactivation DML)

#### What it does today (confirmed from codebase)

Seven distinct Conditional Block sub-actions fire depending on user selection:
- `CB_IBCProfessionalStaff` → Case + IndividualApplication + CaseDataManager
- `CBExecuteNewPractitionerPracLocTaxAndNetworks` → HCPF + Taxonomy + HFN records
- `CB_PractitionerNetworks` → HFN upserts per `PractitionerPracLocTaxAndNetworks` array
- `CB_AdmittingPrivileges` → HCPF admitting type
- `CB_MedicareNumber` → HealthcareProviderNpi (Medicare identifier)
- `CB_DelegatedPractitionerUpdate` → Account + HCPF
- `CB_ExecuteUpdateProfessionalStaff` / `CB_ExecuteRemoveProfessionalStaff` → Multiple objects

The `PractitionerPracLocTaxAndNetworks` array loop in `DRLoadPPLTaxNetworkRecords` runs N DML statements (one per entry) synchronously. For 10 locations × 3 networks = **30 HFN records in one IP action**, hitting limits.

#### Approach A: Queueable IP Refactoring (TX1/TX2/TX3)

**What it involves:**  
- TX1 (Synchronous): `PRM_PDMUpdateLogicContainer` + IP1 (address/facility upserts) → governor ceiling elevated; IP2 invoked as Queueable
- TX2 (Queueable): IP2 (HCPF, provider features, affiliations, CDM) → Queueable governor limits (150 queries / 60s CPU / 12 MB heap)
- TX3 (Queueable chained from IP2): IP3 (taxonomy/payer/IFC upserts) → separate Queueable transaction

**Limitations of this approach:**
- TX3 still cannot be integration-tested (1-level Queueable chaining limit)
- IP still uses all-or-nothing DML (OmniStudio limitation)
- TX1 still blocks UI for 5+ location practitioners

**Effort:** 57 SP (~33 developer days) | **Timeline:** 10 weeks (5 × 2-week sprints)

| Component | SP | Days | Notes |
|---|---|---|---|
| IBX assumption audit (OmniScript, IP key confirmation) | 3 | 2 | Dev + BA |
| Container governor ceiling + IP2 invocation mode change | 5 | 3 | Adapted from Wave 1 |
| IP2 Queueable overrides + Try/Catch + logExceptionViaEvent | 7 | 4 | Adapted from Wave 1 |
| IP3 Try/Catch + partial-success + PRM_FailedRecordStaging | 9 | 5 | Adapted from Wave 1 |
| Update-mode DataRaptor clones (est. 2–4) | 5 | 3 | New |
| Optional Apex helpers (upsert service, delta computer) | 5 | 3 | New |
| OmniUtils sourceFlow annotation | 1 | 0.5 | New |
| List view + page layout changes | 3 | 1.5 | Adapted |
| Unit tests for new Apex classes | 3 | 2 | New |
| Integration tests (1/3/5 location scenarios) | 5 | 3 | QA |
| Forced-failure injection tests (TX1/TX2/TX3) | 3 | 2 | QA |
| UAT with Network Maintenance team | 3 | 2 | QA + PM |
| Deployment runbook + monitoring | 3 | 2 | Dev + Admin |
| **Wave 1 shared infrastructure** (Platform Event, trigger, logger, staging object, fields, Quick Action, permission set) | **0** | **0** | **Reused from Wave 1** |
| **TOTAL** | **57 SP** | **~33 days** | |

#### Approach B: Full Batch Apex Migration (RECOMMENDED)

**What it involves:**  
- Trim the PDM container IP to: IP1 (sync address/facility) + IP2 (sync HCPF/features) + a Remote Action that publishes `NetworkCreationRequested__e` with `Mode__c = 'UPSERT'`
- Mode-extend the three Wave 1 batch classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) to add an UPSERT branch with: delta query in `execute()`, `Database.upsert(records, externalId, false)`, and `Database.update(deactivations, false)`
- UI returns in < 3 seconds; batch chain completes in 8–18 minutes for any practitioner size

**Why this is recommended:**
- Scales to unlimited practice locations (50M rows via QueryLocator)
- Full partial-success DML (per-row failures do not roll back successful updates)
- Full integration testability (batch chains tested end-to-end under `Test.startTest()`)
- Framework-consistent: PDM failures appear in the same Data Admin list views as Creation failures, with zero additional tooling

**Effort:** 38 SP (~17.5 developer days) | **Timeline:** 6 weeks (PDM-only after Wave 1 prerequisite)

| Component | Category | SP | Days |
|---|---|---|---|
| Add `Mode__c` field to `NetworkCreationRequested__e` | Config/Metadata | 1 | 0.5 |
| Mode-extend `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` | Mode-Extended | 1 | 0.5 |
| Mode-extend `PRM_NetworkCreationOrchestrator` (handleEvent, NetworkRequest) | Mode-Extended | 2 | 1 |
| Mode-extend `PRM_TaxonomyNetworkBatch` (UPSERT branch: delta query, upsert DML, deactivation) | Mode-Extended | 3 | 1.5 |
| Mode-extend `PRM_PayerNetworkBatch` | Mode-Extended | 3 | 1.5 |
| Mode-extend `PRM_IFCRecordBatch` | Mode-Extended | 3 | 1.5 |
| `PRM_BatchStagingHelper` shared utility class | New Development | 2 | 1 |
| PDM container IP simplification (deactivate IP3, add Remote Action, `Mode: 'UPSERT'`) | Config/Metadata | 3 | 1.5 |
| Unit tests for all mode-extended batch classes (parameterized) | Testing | 5 | 2.5 |
| Unit tests for Orchestrator + Remote Action mode propagation | Testing | 2 | 1 |
| Integration tests (1-loc, 3-loc, 5+ loc, delta-deactivation, forced-failure) | Testing | 5 | 2.5 |
| Regression test for Practitioner Creation INSERT mode | Testing | 2 | 1 |
| UAT with Network Maintenance team | Testing | 3 | 1.5 |
| Deployment runbook + rollback plan + 48h monitoring | Config/Metadata | 3 | 1.5 |
| **All Wave 1 shared infrastructure** | **Reused (0)** | **0** | **0** |
| **TOTAL** | | **38 SP** | **~17.5 days** |

**Savings vs. standalone (no reuse):** 63 SP (~30 developer days) saved by framework reuse — a 62% reduction from the standalone build cost of 101 SP.

---

### 6B. PDM Manual Change — Practice Location

**OmniScript:** `PRM_PDMManualUpdate_English`  
**Current failure threshold:** ~30 networks, 10+ affiliated practitioners  
**Record volume per submission:** 10–35+ DML operations per sub-action; up to 13 distinct Conditional Block sub-actions

#### What it does today (confirmed from `PRM_PDMRecordsCreationHelper`, 50+ elements)

| Sub-action | CB Element | Records Affected | Failure Risk |
|---|---|---|---|
| Add/Remove Practitioner | `CB_AddRemovePractitioner` | HCPF | Low |
| HCPF + Networks for Add/Remove | `CB_AddRemovePractitionerHCPF` | HCPF + HFN (×N) | HIGH |
| Add Network | `CB_AddPractitionerNetwork` | HFN | Medium |
| Change Networks | `CB_AddRemovePractitionerNetwork` | HFN updates | HIGH |
| Remove Network | `CB_RemovePractitionerNetwork` | HFN deletes | Medium |
| Add/Terminate Taxonomy | `CB_AddorTerminatePLTaxonomy` | HPT + HFN | HIGH |
| Add/Remove Networks (bulk) | `CB_AddRemoveNetworks` | HFN (×bulk, up to 30+) | **CRITICAL** |
| Terminate Practice Location | `CB_TerminatePracticeLocation` | HCPF + HFN + HPT + HCF | **CRITICAL** |
| COI Terminate + Remove | `CB_TerminateCOIAndRemovePractitioner` | Multiple objects | HIGH |
| Program Participation | `CB_ProgramParticipation` / `CB_AddProgramPartcipation` / `CB_RemoveProgramPartcipation` | ProgramParticipation + HFN | HIGH |
| Non-Par Account | `CB_NonParAccount` | Account + HCPF + HFN | Medium |
| Update Office Hours | `CB_UpdateOfficeHours` | OperatingHours (7 days × N slots) | Medium |
| Capitation Site | `CB_CapitationSite` | CapitationSite | Low |
| Directory Indicators | `CB_UpdateDirectoryIndicators` | HFN bulk flag updates | HIGH |

**Critical note:** `CB_AddRemoveNetworks` → `DRLoadManualUpdatePLNetworks` processes a `MergedNetworks` array — each item = one DML. A facility with 30 networks = **30 DML statements in one IP action.** Terminate Practice Location is the most complex: it deactivates HCPF + all HFN (×N) + all HPT (×M) + updates HCF + clones cross-reference records — all synchronously.

#### Approach A: Queueable IP Refactoring

Same pattern as PDM Practitioner Approach A but applied to the Practice Location IP chain.  
**Effort:** 45 SP (~26 developer days) | **Timeline:** 8 weeks

| Component | SP | Days | Notes |
|---|---|---|---|
| IBX assumption audit (IP chain confirmation, sub-action inventory) | 3 | 2 | Dev + BA |
| Container governor ceiling + Queueable invocation changes | 5 | 3 | Adapted |
| Network CB (AddRemoveNetworks) → Queueable wrapper + Try/Catch | 8 | 5 | New (sub-action specific) |
| Terminate PL → Queueable wrapper (deactivation chain) | 8 | 5 | New |
| HFN bulk update sub-actions → Queueable wrappers | 5 | 3 | New |
| DataRaptor upsert mode clones (est. 3–6) | 6 | 4 | New |
| PRM_FailedRecordStaging__c integration for PL-specific objects | 3 | 2 | Adapted |
| Unit tests | 3 | 2 | New |
| Integration tests (all 13 sub-action types, 1/3/5 network scenarios) | 3 | 2 | QA |
| UAT | 3 | 2 | QA + PM |
| Runbook | 1 | 0.5 | Dev |
| **Shared Wave 1 infrastructure** | **0** | **0** | **Reused** |
| **TOTAL** | **45 SP** | **~26 days** | |

#### Approach B: Full Batch Apex Migration (RECOMMENDED)

**What it involves:**  
- Trim the PDM PL container IP: keep synchronous address/facility validation; replace all sub-action DML with a single Remote Action that publishes `NetworkCreationRequested__e` with `Mode__c = 'UPSERT_PL'` and `SubType` identifying the sub-action
- New `PRM_PDMPracticeLocationBatch` class handles sub-action routing in `execute()` based on SubType
- For Terminate PL: separate `PRM_PDMTerminatePLBatch` that deactivates HCPF + HFN + HPT with `Database.update(records, false)` for partial success
- Reuses all framework components; adds only the PL-specific DML logic

**Effort:** 32 SP (~15 developer days) | **Timeline:** 6 weeks (after Wave 1 + Wave 2 prerequisites)

| Component | Category | SP | Days |
|---|---|---|---|
| Add `UPSERT_PL` mode + `SubType` field to Platform Event | Config | 1 | 0.5 |
| Mode-extend Orchestrator to route UPSERT_PL to PL batch | Mode-Extended | 2 | 1 |
| `PRM_PDMPracticeLocationBatch` (handles all non-terminate sub-actions, UPSERT mode) | New Batch | 5 | 2.5 |
| `PRM_PDMTerminatePLBatch` (deactivation chain: HCPF + HFN + HPT) | New Batch | 5 | 2.5 |
| `PRM_PDMOfficeHoursBatch` (OperatingHours upsert) | New Batch | 2 | 1 |
| PDM PL container IP simplification (replace all sub-action DML elements with Remote Action) | Config/Metadata | 3 | 1.5 |
| Unit tests for all PL-specific batch classes | Testing | 4 | 2 |
| Integration tests (all 13 sub-actions, bulk scenarios) | Testing | 4 | 2 |
| Regression test (shared batch class modes) | Testing | 2 | 1 |
| UAT + deployment runbook | Testing/Config | 4 | 2 |
| **All Wave 1 + Wave 2 shared infrastructure** | **Reused (0)** | **0** | **0** |
| **TOTAL** | | **32 SP** | **~15 days** |

---

### 6C. Mass Updates (Add/Remove Practitioners, Networks, Practice Locations, Taxonomies)

**Current state:** No dedicated mass-update flow exists today. Business performs individual guided-flow submissions for each change, which is extremely slow at volume. The UPHS mass load scenario (107 practitioners × multiple locations × networks = potentially thousands of records) demonstrates the need.

**Scope of mass update types:**
1. **Mass Add Practitioners to Practice Location(s)** — create HCPF + HFN per taxonomy × role × network
2. **Mass Remove Practitioners from Practice Location(s)** — deactivate HCPF + associated HFN
3. **Mass Add/Remove Networks** at a Practice Location — bulk upsert/deactivate HFN records
4. **Mass Add/Remove Practice Locations** (new/remove entire locations for practitioners) — full HCPF + HFN + HPT chain
5. **Mass Add/Remove Taxonomies** — HPT upsert + HFN cascade

#### Approach: Batch Apex + Async Dispatch (Only viable approach)

Mass updates cannot be processed synchronously regardless of volume. The only viable architecture is:

1. **New OmniScript or LWC** captures the mass-change request (CSV upload or multi-select UI)
2. **New `PRM_AsyncJobRequest__c` staging object** holds the full payload with `FlowType`, `SubType`, `Status`, `PractitionerId`, `FacilityId`, `Payload` (JSON), `RequestId`
3. **New `PRM_AsyncJobQueued__e` Platform Event** dispatches the batch
4. **Dedicated Batch Apex classes** process the mass change in chunks with partial-success DML and staging

**New batch classes required:**

| Batch Class | Sub-action | Objects Written | Batch Size |
|---|---|---|---|
| `PRM_MassAddPractitionerBatch` | Mass Add Practitioners | HCPF, HFN, HPT | 5 practitioners/exec |
| `PRM_MassRemovePractitionerBatch` | Mass Remove Practitioners | HCPF (deactivate), HFN (deactivate) | 10/exec |
| `PRM_MassAddNetworkBatch` | Mass Add Networks | HFN | 50/exec |
| `PRM_MassRemoveNetworkBatch` | Mass Remove Networks | HFN (deactivate) | 50/exec |
| `PRM_MassAddPracticeLocationBatch` | Mass Add Practice Locations | HCPF + HFN chain | 5/exec |
| `PRM_MassTerminatePracticeLocationBatch` | Mass Terminate Locations | HCPF + HFN + HPT | 5/exec |
| `PRM_MassAddTaxonomyBatch` | Mass Add Taxonomies | HPT + HFN cascade | 10/exec |
| `PRM_MassRemoveTaxonomyBatch` | Mass Remove Taxonomies | HPT deactivate + HFN cascade | 10/exec |

**Shared infrastructure reused:** All Wave 1 components (event, trigger, orchestrator, staging object, exception pipeline, Data Admin toolset, email templates) — at zero additional cost.

**New infrastructure required:**
- `PRM_AsyncJobRequest__c` custom object (18 fields: FlowType, SubType, Status, RequestId, Payload, FacilityId, PractitionerId, BatchJobId, etc.)
- `PRM_AsyncJobQueued__e` Platform Event (3 fields: JobRequestId, FlowType, Priority)
- `PRM_AsyncJobDispatcher` Apex class (routes by FlowType to correct batch)
- `PRM_PDMJobStatusCard` FlexCard (polls job status; shows Queued → Processing → Completed/Failed)
- `PRM_SubmitAsyncJob` Integration Procedure (captures payload, writes to staging object, fires event)
- Generic rollback batch (`PRM_RollbackBatch`): deletes records by `PRM_RequestId__c` per object in chained finish() calls

**Effort:** 65 SP (~37.5 developer days) | **Timeline:** 10 weeks

| Component | SP | Days | Notes |
|---|---|---|---|
| `PRM_AsyncJobRequest__c` object + all fields + permissions + layout | 2 | 1 | New |
| `PRM_AsyncJobQueued__e` Platform Event + trigger + dispatcher | 3 | 1.5 | New |
| Add `PRM_RequestId__c` + `PRM_Status__c` to 7 target objects (AI-assisted) | 2 | 1 | New |
| `PRM_SubmitAsyncJob` IP (captures payload, writes staging, fires event) | 2 | 1 | New |
| `PRM_RollbackBatch` generic (per-object chained delete in finish()) | 3 | 1.5 | New |
| Rewire `PRM_PractitionerActivationBatch` into async dispatcher | 1 | 0.5 | Existing batch, rewire |
| `PRM_PDMJobStatusCard` FlexCard | 3 | 1.5 | New |
| `PRM_MassAddPractitionerBatch` | 5 | 2.5 | New |
| `PRM_MassRemovePractitionerBatch` | 3 | 1.5 | New |
| `PRM_MassAddNetworkBatch` | 3 | 1.5 | New |
| `PRM_MassRemoveNetworkBatch` | 3 | 1.5 | New |
| `PRM_MassAddPracticeLocationBatch` (full HCPF + HFN chain) | 5 | 2.5 | New |
| `PRM_MassTerminatePracticeLocationBatch` (deactivation chain) | 5 | 2.5 | New |
| `PRM_MassAddTaxonomyBatch` (HPT + HFN cascade) | 4 | 2 | New |
| `PRM_MassRemoveTaxonomyBatch` (HPT deactivate + cascade) | 3 | 1.5 | New |
| OmniScript / LWC for mass change initiation (3 flow types) | 5 | 2.5 | New |
| Unit tests for all mass batch classes (AI-assisted) | 6 | 3 | New |
| Integration tests (107-record UPHS scenario + failure injection) | 4 | 2 | QA |
| UAT with business + bug fixes | 3 | 1.5 | QA + PM |
| Deployment runbook | 1 | 0.5 | Dev |
| **All Wave 1 shared infrastructure (exception pipeline, staging, Data Admin toolset)** | **0** | **0** | **Reused** |
| **TOTAL** | **65 SP** | **~37.5 days** | |

---

### 6D. Mass Update Mailing/Billing Addresses (New)

**Current state:** No flow exists to bulk-update mailing or billing addresses across multiple practitioners or practice locations. Business must update each record individually through the PDM Manual Change guided flow.

**Business scenarios:**
- Re-zone a hospital system's billing address for 200+ practitioners simultaneously
- Update a practice group's mailing address after a move
- Bulk-correct address data after a Precisely API re-validation run

#### Approach: Batch Apex + Async Dispatch

**What it involves:**
1. **New OmniScript or LWC** for mass address update: select target type (Practitioner or Practice Location), upload CSV or multi-select records, provide new address values
2. **Address validation step** (Precisely API via `PRM_AddressValidationService.validateAddress()`) runs synchronously on the provided address before the payload is submitted
3. **`PRM_AsyncJobRequest__c`** staging object (reused from Mass Updates, 6C) holds the payload
4. **`PRM_MassAddressUpdateBatch`** processes the address updates in chunks with partial-success DML
5. `PRM_FutureAddressActivateBatch` (already exists) handles future-dated address activations

**New batch classes required:**

| Batch Class | Function | Objects Written | Batch Size |
|---|---|---|---|
| `PRM_MassMailingAddressUpdateBatch` | Update mailing address on Account/Contact | Account, Contact, `PRM_Address__c` | 20/exec |
| `PRM_MassBillingAddressUpdateBatch` | Update billing address | Account, `PRM_Address__c` (billing type) | 20/exec |
| `PRM_MassPLAddressUpdateBatch` | Update practice location address | `Location__c`, `HealthcareFacility`, associated HCPF/HFN | 10/exec |

**Dependency on existing infrastructure:**
- `PRM_AddressValidationService` (already built) — reused for pre-batch validation
- `PRM_FutureAddressActivateBatch` (already exists) — reused for future-dated changes
- `PRM_AsyncJobRequest__c` (built in Wave 4 / 6C) — reused
- All Wave 1 exception pipeline and staging infrastructure — reused

**Effort:** 28 SP (~14 developer days) | **Timeline:** 5 weeks (after Wave 4 infrastructure)

| Component | SP | Days | Notes |
|---|---|---|---|
| `PRM_MassMailingAddressUpdateBatch` (Account/Contact/Address) | 5 | 2.5 | New |
| `PRM_MassBillingAddressUpdateBatch` (Account/Address billing) | 4 | 2 | New |
| `PRM_MassPLAddressUpdateBatch` (Location/HCF/HCPF/HFN) | 5 | 2.5 | New |
| Address validation pre-flight (Precisely API integration, sync before queuing) | 3 | 1.5 | Adapted from existing service |
| New OmniScript / LWC for mass address change initiation | 4 | 2 | New |
| Unit tests for all address batch classes | 3 | 1.5 | New |
| Integration tests (mailing + billing + PL address scenarios) | 2 | 1 | QA |
| UAT | 2 | 1 | QA + PM |
| Deployment runbook | 1 | 0.5 | Dev |
| `PRM_AsyncJobRequest__c` + dispatcher + FlexCard | **0** | **0** | **Reused from Wave 4** |
| All Wave 1 shared infrastructure | **0** | **0** | **Reused** |
| **TOTAL** | **28 SP** | **~14 days** | |

---

## 7. Reuse Strategy: Plug-and-Play Batch Modules

### 7.1 How the Modules Connect

Each batch class is designed to be **self-contained, mode-parameterized, and chainable**. The orchestrator acts as the routing layer — when it receives a Platform Event, it reads `Mode__c` and `SubType__c` and dispatches to the correct first batch in the appropriate chain.

```
PRM_NetworkCreationOrchestrator.handleEvent(event)
  
  switch on event.Mode__c:
    when 'INSERT'         → Database.executeBatch(new PRM_TaxonomyNetworkBatch(params, 'INSERT'), 5)
    when 'UPSERT'         → Database.executeBatch(new PRM_TaxonomyNetworkBatch(params, 'UPSERT'), 5)
    when 'UPSERT_PL'      → Database.executeBatch(new PRM_PDMPracticeLocationBatch(params), 5)
    when 'MASS_ADD_PRACT' → Database.executeBatch(new PRM_MassAddPractitionerBatch(params), 5)
    when 'MASS_REM_PRACT' → Database.executeBatch(new PRM_MassRemovePractitionerBatch(params), 10)
    when 'MASS_NETWORK'   → Database.executeBatch(new PRM_MassAddNetworkBatch(params), 50)
    when 'MASS_TAXONOMY'  → Database.executeBatch(new PRM_MassAddTaxonomyBatch(params), 10)
    when 'MASS_ADDRESS'   → Database.executeBatch(new PRM_MassMailingAddressUpdateBatch(params), 20)
```

### 7.2 Reuse in Existing Guided Flows

The same batch framework can be applied to every existing guided flow that currently processes records synchronously. Below is an inventory of flows where the framework can be wired in with minimal additional work:

| Existing Guided Flow | OmniScript | Current IP | Batch Reuse Opportunity | Est. Additional Effort |
|---|---|---|---|---|
| Delegated Practitioner Creation | `PRM_DelegatedPractitionerReviewScreen` | `PRM_AddressLogicContainer` | Wave 1 — already the driver for the batch framework | 0 (Wave 1 builds this) |
| IBC Professional Staff Creation | `PRM_PractitionerCreation_English` | `PRM_PractitionerCreationContainer` | Reuse `PRM_TaxonomyNetworkBatch` / `PRM_PayerNetworkBatch` via INSERT mode | 5–8 SP (IP simplification only) |
| Initial Credentialing PDA Review | `PRM_InitialCredPDA` | `PRM_InitialCredPDAReviewUpdateParent` (44 steps) | New `PRM_PDANetworkUpdateBatch` — reuses orchestrator + staging | 15–20 SP |
| Re-Credentialing PDA Review | `PRM_ReCredPDA` | Similar to InitialCred | Same as above, parameterized | 5–8 SP (shares PDA batch) |
| PDM Terminate Practitioner | Multiple | `PRM_FullPractitionerTerminationBatch` (already batch) | Reuse rollback-safe exception logging + staging | 3–5 SP |
| PDM Recredentialing Manual Change | `PRM_PDMManualChanges_English` | Multiple IPs | Extend UPSERT mode of PDM Practitioner batches | 8–12 SP |
| Mass UPHS Load (107 practitioners) | N/A (new) | N/A | `PRM_MassAddPractitionerBatch` directly | 0 (covered in 6C) |
| Provider Screen Records (bulk) | Multiple intake flows | `PRM_CreateProviderScreenRecordsContainer` | New `PRM_ProviderScreeningBatch` — reuses staging + orchestrator | 10–15 SP |

**Total additional reuse effort across all existing guided flows:** ~46–68 SP (estimated), primarily IP simplification and new flow-specific batch classes. All share the same exception pipeline, staging object, Data Admin toolset, and monitoring infrastructure.

### 7.3 The "Plug and Play" Contract

For a new flow to plug into the framework, the developer needs to:

1. **Add a `Mode__c` value** to `NetworkCreationRequested__e` (one-line XML change)
2. **Add a routing case** in `PRM_NetworkCreationOrchestrator` (one-line switch)
3. **Build the batch class** implementing `Database.Batchable<SObject>, Database.Stateful` with:
   - `start()` → `Database.getQueryLocator` scoped to the CaseManager/request
   - `execute()` → business-specific DML with `Database.upsert(records, extId, false)`; failures → `PRM_BatchStagingHelper.stageFailure()`
   - `finish()` → update `PRM_NetworkCreationStatus__c` → chain to next batch or complete
4. **Simplify the IP** to replace DML elements with a Remote Action publish

Steps 1–2 take under 1 hour. Steps 3–4 contain all the flow-specific business logic.

---

## 8. Removing Limits in Existing OmniScripts

### 8.1 Current Hard Limits Identified

| OmniScript | Component | Current Limit | Symptom |
|---|---|---|---|
| `PRM_PDMManualUpdate_English` | `CB_AddRemoveNetworks` → `DRLoadManualUpdatePLNetworks` | ~30 network records before timeout | Users cannot add more than ~30 networks in a single PDM PL change |
| `PRM_PDMManualUpdatePractitioner_English` | `PractitionerPracLocTaxAndNetworks` DR loop | ~30 HFN entries before timeout | Users cannot update practitioners at 10+ locations |
| `PRM_PDMManualUpdate_English` | `CB_AddRemovePractitionerHCPF` | 3–5 practitioners at a location before timeout | Bulk add/remove practitioners hits limits |
| `PRM_InitialCredPDA` | `InitialCredPDAReviewHFN` Queueable element | 5 practitioners per batch before timeout | Monthly PDA reviews must be split manually |
| Multiple mass add/remove flows | No batch processing at all | N/A — no flow exists | Business cannot do mass changes without manual scripts |

### 8.2 How Limits Are Removed

**The limits cannot be removed by simply changing a config value.** They exist because the synchronous execution model has a finite governor budget. Removing them requires the async batch architecture:

1. The OmniScript form submission triggers a validation + staging write (< 3 seconds, no DML limit risk)
2. A Platform Event dispatches the unlimited-volume processing to a Batch Apex chain
3. The batch chain processes records in chunks (5–50 per `execute()` call), with each chunk getting a **fresh governor budget**
4. The chain scales to **any volume** — 30 networks, 300 networks, 3,000 networks — with no code change needed

**Once the async architecture is in place:**
- All artificially imposed array size caps in OmniScript elements can be removed (the UI no longer times out)
- Business can submit requests for practitioners with 20+ locations without workarounds
- Mass changes of 100–10,000 records become routine operations with status tracking

### 8.3 OmniScript Changes Required Per Flow

| OmniScript | Change | Effort |
|---|---|---|
| `PRM_PDMManualUpdate_English` | Replace `DRLoadManualUpdatePLNetworks` DML with Remote Action → Platform Event publish; remove array size cap on `MergedNetworks` | 3 SP |
| `PRM_PDMManualUpdatePractitioner_English` | Replace `DRLoadPPLTaxNetworkRecords` DML with Remote Action → Platform Event publish; remove array size cap on `PractitionerPracLocTaxAndNetworks` | 3 SP |
| `PRM_InitialCredPDA` | Replace `InitialCredPDAReviewHFN` Queueable with Platform Event publish; remove practitioner count cap | 4 SP (covered under PDA reuse estimate) |
| New Mass Update OmniScript/LWC | New component capturing bulk change request; no legacy limits to remove | Covered in 6C/6D estimates |

**Total OmniScript limit-removal effort (across all in-scope flows):** ~15 SP (included in per-flow estimates above)

---

## 9. Estimation Summary — All Approaches

### 9.1 Master Estimation Table

| Delivery Wave | Flow | Approach | SP | Developer Days | Calendar Weeks | Dependencies |
|---|---|---|---|---|---|---|
| **Wave 1** (in-flight) | Practitioner Creation Performance | Batch Apex Framework build | ~80 SP | ~40 days | 8 weeks | None |
| **Wave 2** | PDM Manual Change — Practitioner | **Approach B: Batch Apex (Recommended)** | **38 SP** | **~17.5 days** | **6 weeks** | Wave 1 deployed to QA |
| *(Wave 2 alt)* | PDM Manual Change — Practitioner | Approach A: Queueable IP Refactor | 57 SP | ~33 days | 10 weeks | Wave 1 shared infra |
| **Wave 3** | PDM Manual Change — Practice Location | **Approach B: Batch Apex (Recommended)** | **32 SP** | **~15 days** | **6 weeks** | Wave 1 + Wave 2 deployed |
| *(Wave 3 alt)* | PDM Manual Change — Practice Location | Approach A: Queueable IP Refactor | 45 SP | ~26 days | 8 weeks | Wave 1 shared infra |
| **Wave 4** | Mass Updates (Add/Remove Pract., Networks, PL, Taxonomy) | Batch Apex + Async Dispatch | **65 SP** | **~37.5 days** | **10 weeks** | Wave 1 deployed |
| **Wave 5** | Mass Update Mailing/Billing Addresses | Batch Apex + Async Dispatch | **28 SP** | **~14 days** | **5 weeks** | Wave 1 + Wave 4 infra |
| **Cross-cutting** | Remove limits in all OmniScripts | Async UI changes | Included above | Included | Included | Per wave |

### 9.2 Recommended (Approach B) Total Summary

| Phase | Waves | SP | Calendar Weeks | Notes |
|---|---|---|---|---|
| **Pre-requisite** | Wave 1 (in-flight) | ~80 SP | 8 weeks | Practitioner Creation framework |
| **High Priority** | Wave 2 + Wave 3 (parallel where possible) | 38 + 32 = **70 SP** | **8–10 weeks** | Both flows after Wave 1 |
| **Business Priority** | Wave 4 (Mass Updates) | **65 SP** | **10 weeks** | After Wave 1; can start parallel to Wave 3 |
| **New Capability** | Wave 5 (Mass Addresses) | **28 SP** | **5 weeks** | After Wave 4 infrastructure |
| **TOTAL (Waves 2–5)** | | **201 SP** | **~28 weeks total elapsed** | With 2 senior devs, parallel execution possible |

### 9.3 Cost Comparison: With vs. Without Reuse

| Component | Standalone Cost | Framework Reuse Cost | Savings |
|---|---|---|---|
| Wave 2 (PDM Pract.) | 101 SP | 38 SP | **63 SP** |
| Wave 3 (PDM PL) | 85 SP | 32 SP | **53 SP** |
| Wave 4 (Mass Updates) | 115 SP | 65 SP | **50 SP** |
| Wave 5 (Mass Addresses) | 55 SP | 28 SP | **27 SP** |
| **Total** | **356 SP** | **163 SP** | **193 SP (~54% reduction)** |

The Practitioner Creation framework (Wave 1) is an investment that pays forward 193 story points in savings across all subsequent waves — roughly 97 developer days that do not need to be spent rebuilding infrastructure.

---

## 10. Business Benefits

### 10.1 Operational Efficiency Gains

| Metric | Current State | Post-Implementation Target |
|---|---|---|
| UI freeze rate (PDM updates, 3+ locations) | ~60–80% of submissions | < 1% |
| Average UI response time | 3–8 minutes (blocking) | < 3 seconds (async) |
| Support ticket volume (PDM/creation queue) | 15–20 tickets/week | < 3/week (>80% reduction) |
| Manual workaround time per incident | 1–2 hours (Data Admin reconciliation) | < 15 minutes (automated staging + retry) |
| Mass change capacity (practitioners/batch) | ~5–10 per manual session | Unlimited (batch scale) |
| Time to complete UPHS 107-practitioner load | N/A (impossible today) | ~2–4 hours automated |
| Practitioner onboarding time (from submission to active) | 2–8 hours (manual workarounds) | 30–90 minutes (async + email notification) |

### 10.2 Data Integrity Improvements

| Issue | Current Risk | Post-Implementation |
|---|---|---|
| Partial data writes on timeout | High — IP3 rolls back silently; user sees success screen | Eliminated — each batch commits independently; per-row failures staged for review |
| Duplicate records on retry | High for creation flows — retrying a failed submission creates duplicates | Eliminated — UPSERT mode is idempotent; retrying any batch produces the same final state |
| Silent failures (no exception log) | High — direct DML exception logging rolls back with the transaction | Eliminated — `PRM_ExceptionLogEvent__e` with `PublishImmediately` survives rollback |
| Stale network data after update | High — a TX3 failure leaves the prior network graph intact but invisible | Resolved — `PRM_FailedRecordStaging__c` identifies exactly which rows failed; retry is safe |
| Concurrent modification conflicts (dirty-read window) | Medium (new risk for async) | Mitigated — batch `execute()` re-queries inside its own transaction for current state |

### 10.3 Scalability Achievements

| Dimension | Current Ceiling | Post-Implementation Ceiling |
|---|---|---|
| Practice locations per practitioner (PDM update) | 2–3 (reliable), 5 (possible), >5 fails | Unlimited (50M rows via QueryLocator) |
| Networks per practice location (bulk add) | ~30 before timeout | Unlimited |
| Practitioners per mass-add operation | 1 (individual submission only) | Unlimited (processed in batches of 5) |
| Addresses per mass update | 1 (individual submission only) | Unlimited (processed in batches of 20) |
| Concurrent PDM submissions without queue conflict | 1–2 (Queueable limit) | 5 concurrent batch chains (Salesforce concurrent batch limit) |

### 10.4 Developer / Operational Benefits

- **Unified monitoring:** All async PDM flows surface in one `AsyncApexJob` query and one Data Admin list view — regardless of which flow triggered them
- **Self-service retry:** Data Admins can resolve failed records directly from the "Network Creation Errors" list view using the existing "Mark Resolved & Route to QC" Quick Action — no developer involvement needed for most failures
- **Automated audit trail:** Every batch execution creates `PRM_ExceptionLog__c` records and `PRM_FailedRecordStaging__c` records, providing a complete paper trail for compliance and support
- **Email notifications:** Credentialing and Network Maintenance users receive a completion email (success or failure summary) within minutes of a batch chain completing — eliminating the need to refresh the UI or ask Data Admin for status
- **Feature flag safety:** Existing synchronous IPs remain in place (set to `isActive: false`) and can be reactivated via Custom Setting `PRM_UseAsyncProcessing__c` if a rollback is needed — no redeployment required

### 10.5 Financial Impact (Conservative Estimate)

| Savings Category | Estimated Monthly Value |
|---|---|
| Support ticket reduction (~15 → ~3/week × 1h/ticket × $75/hr) | ~$3,600/month |
| Manual Data Admin reconciliation reduction (50h/week → 5h/week × $75/hr) | ~$13,500/month |
| Faster practitioner onboarding (time-to-revenue: 1 week faster × $500/practitioner × 20 practitioners/month) | ~$10,000/month |
| UPHS mass-load automation (107 practitioners × 2h saved each × $75/hr) | ~$16,050/one-time |
| **Estimated Monthly Recurring Savings** | **~$27,100/month** |
| **Estimated Annual Recurring Savings** | **~$325,000/year** |

---

## 11. Implementation Roadmap

### 11.1 Dependency Chain

```
Wave 1 (in-flight)
  Practitioner Creation Framework → QA Deploy
  (Platform Event, Orchestrator, 3 Batch Classes, Staging Object, Exception Pipeline,
   Data Admin Toolset, Email Templates)
  
       │
       ▼ (Wave 1 QA Deploy complete)
       
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ Wave 2 + Wave 4 can start in PARALLEL after Wave 1 QA Deploy              │
  │                                                                            │
  │  Wave 2: PDM Manual Pract.    Wave 4: Mass Updates                        │
  │  (Mode-extend batch classes)  (New async job infrastructure)               │
  │  38 SP / 6 weeks              65 SP / 10 weeks                             │
  └────────────────────────────────────────────────────────────────────────────┘
       │                                │
       ▼ (Wave 2 complete)              ▼ (Wave 4 complete)
       
  Wave 3: PDM Manual PL          Wave 5: Mass Addresses
  (New PL batch + IP simplify)   (New address batches)
  32 SP / 6 weeks                28 SP / 5 weeks
```

### 11.2 Sprint Plan (Recommended Path — 2 Developers)

| Sprint | Weeks | Dev 1 | Dev 2 | Deliverables |
|---|---|---|---|---|
| S0 (prereq) | 1–2 | Wave 1 final hardening | Wave 1 QA integration tests | Wave 1 deployed to QA |
| S1 | 3–4 | Wave 2: Mode-extend Taxonomy + Payer batches (UPSERT) | Wave 4: AsyncJobRequest + AsyncJobQueued infra + dispatcher | Both teams unblocked |
| S2 | 5–6 | Wave 2: Mode-extend IFC batch + PDM IP simplification | Wave 4: MassAddPractitionerBatch + MassRemovePractitionerBatch | Wave 2 core complete |
| S3 | 7–8 | Wave 2: Unit + integration tests + UAT | Wave 4: MassNetworkBatch + MassTaxonomyBatch + MassAddPLBatch | Wave 2 production-ready |
| S4 | 9–10 | Wave 3: PDM PL batch classes + IP simplification | Wave 4: MassTerminatePLBatch + JobStatusCard FlexCard | Wave 4 core complete |
| S5 | 11–12 | Wave 3: Unit + integration tests + UAT | Wave 4: Unit + integration tests + UAT | Waves 3 + 4 production-ready |
| S6 | 13–14 | Wave 5: MassMailingBatch + MassBillingBatch + MassPLAddressBatch | Wave 5: Address validation pre-flight + OmniScript/LWC | Wave 5 core complete |
| S7 | 15–16 | Wave 5: Tests + UAT + deployment | Regression testing all previous waves | All waves production-ready |

**Total calendar duration (2 developers, parallel execution):** ~16 weeks (after Wave 1 QA deploy)

### 11.3 Single-Developer Path

If only one developer is available, waves are sequential. Estimated duration: ~26 weeks after Wave 1 QA deploy.

---

## 12. Risk Register

| # | Risk | Severity | Probability | Mitigation |
|---|---|---|---|---|
| 1 | Wave 1 (Practitioner Creation) delayed — all subsequent waves delayed by the same amount | High | Medium | Hard dependency documented. PDM work cannot begin until Wave 1 shared infra is deployed to QA. |
| 2 | IP3 shared between Creation and Update flows — changes to UPSERT mode risk regressing INSERT mode | High | High (likely) | Sprint 0 confirms whether IP3 is shared. If shared, add a `mode` parameter or fork the IP. Regression pass required in each wave's hardening sprint. |
| 3 | `logException` vs `logExceptionViaEvent` routing bug — developer accidentally uses direct-DML variant in a Catch block, causing silent failure | High | Medium | Wave 1 renamed the direct variant to `logExceptionDirect` with a deprecation comment. Code-review checklist item. |
| 4 | IP3 placement inside IP2's conditional block (not at level 0) — causes IP3 to never fire | High | Medium | Lock placement at `level: 0`, `sequenceNumber: 6.1`, after `ResponseForIp`. Sandbox test: a PDM update that modifies only secondary locations must still trigger IP3. |
| 5 | Platform event duplicate dispatch (at-least-once delivery) — same request processed twice | High | Low | `PRM_AsyncJobDispatcher.dispatch()` checks `PRM_AsyncJobRequest__c.Status != 'Queued'` with `FOR UPDATE` before enqueuing. Idempotency confirmed in integration tests. |
| 6 | BCBSA sync events pick up `Status = 'Pending'` batch-created records before activation | High | Medium | Confirm BCBSA sync triggers filter `PRM_IsActive__c = true`. Add the field to existing filter logic if not already present. |
| 7 | `PRM_FutureDatedProcessingBatchHandler` processes Pending records created by batches | Medium | High | Add `PRM_IsActive__c = true` filter to FDP queries. Confirmed as a known risk in `PRM_HighVolume_Processing_SK_Estimation.md`. |
| 8 | Rollback batch uses `UNION ALL` in `Database.getQueryLocator` — not supported in Salesforce SOQL | High | Confirmed (known bug) | Use chained per-object delete in `finish()`. Pattern documented and fixed in `PRM_HighVolume_Processing_SK_Estimation.md` Section 4C. |
| 9 | UAT scope creep — business discovers additional sub-actions or edge cases during testing | Medium | High | Sprint 0 includes a full sub-action audit. UAT fixtures are defined upfront and signed off before Sprint 1 begins. |
| 10 | Batch job queue limit (5 concurrent) — mass updates from multiple users block each other | Low | Medium | Monitor `AsyncApexJob` queue depth. For high-volume mass operations, schedule during off-peak hours. Add queue depth check to `PRM_AsyncJobDispatcher`. |
| 11 | `allOrNone = false` on upserts leaves a payer-network roster partially refreshed | Medium | Medium | Use `allOrNone = true` for delete DML; `allOrNone = false` only for upsert DML. Stage all failed rows for Data Admin review. |
| 12 | Update-specific dirty-read window between TX1 commit and batch execute | Medium | Low | Batch `execute()` re-queries critical rows inside its own transaction (not trusting the payload passed from the IP). Documented in Section 4 risks. |

---

## 13. Definition of Done

### 13.1 Wave 2 — PDM Manual Change Practitioner (Batch Apex Approach)

- [ ] All PDM Manual Update IP chain elements that previously called network/taxonomy/IFC creation logic have been removed or set to `isActive: false`
- [ ] Trimmed PDM IP chain contains only synchronous address/facility/location upsert work (IP1 + IP2) and the Platform Event publish step
- [ ] Platform Event publish returns to the UI in under 3 seconds for a practitioner with 5+ practice locations
- [ ] All heavy DML (taxonomy, payer network, IFC upsert + stale record deactivation) executes in Batch Apex only
- [ ] `Mode__c = 'UPSERT'` propagates correctly from Remote Action through Orchestrator through all three batch classes
- [ ] Unit test coverage ≥ 90% on all mode-extended batch classes
- [ ] Integration tests pass for 1-location, 3-location, 5+ location PDM updates
- [ ] Delta computation correctly identifies and deactivates stale records
- [ ] `PRM_NetworkCreationStatus__c` progresses correctly: Not Started → Queued → Processing Taxonomies → Processing Payer Networks → Processing IFC → Completed/Failed
- [ ] Email notification sent on completion (success and failure)
- [ ] No regression in Practitioner Creation (INSERT mode) integration tests
- [ ] UAT sign-off from Network Maintenance team

### 13.2 Wave 3 — PDM Manual Change Practice Location (Batch Apex Approach)

- [ ] All 13 sub-action DML elements in the PDM PL container IP replaced with Remote Action → Platform Event publish
- [ ] `PRM_PDMPracticeLocationBatch` handles all non-terminate sub-actions with UPSERT mode
- [ ] `PRM_PDMTerminatePLBatch` correctly deactivates HCPF + HFN + HPT with partial-success DML
- [ ] UI returns in under 3 seconds for any sub-action regardless of network volume
- [ ] All existing OmniScript hard limits (e.g., `MergedNetworks` array cap) removed
- [ ] Unit test coverage ≥ 85% on all PL-specific batch classes
- [ ] Integration tests pass for all 13 sub-action types and bulk scenarios (30+ networks, 10+ practitioners)
- [ ] UAT sign-off from Network Maintenance team

### 13.3 Wave 4 — Mass Updates

- [ ] `PRM_AsyncJobRequest__c` object deployed with all required fields
- [ ] `PRM_AsyncJobQueued__e` Platform Event + trigger + dispatcher deployed
- [ ] `PRM_PDMJobStatusCard` FlexCard shows real-time status (Queued → Processing → Completed/Failed) on Case record
- [ ] All 8 mass batch classes deployed and tested
- [ ] Rollback tested: simulate mid-chain failure → confirm all records with `PRM_RequestId__c` are deleted
- [ ] E2E test: 107-practitioner UPHS load completes without governor exceptions
- [ ] Platform event idempotency verified: duplicate `PRM_AsyncJobQueued__e` delivery does not create duplicate batches
- [ ] UAT sign-off from Business on all mass update types

### 13.4 Wave 5 — Mass Update Addresses

- [ ] All three address batch classes deployed and tested
- [ ] Precisely API pre-validation runs synchronously before queuing (invalid addresses rejected at form submission)
- [ ] `PRM_FutureAddressActivateBatch` correctly activated for future-dated address changes
- [ ] Integration tests pass for mailing, billing, and practice location address bulk updates
- [ ] UAT sign-off from Business

### 13.5 Cross-Cutting (All Waves)

- [ ] 48-hour post-production monitoring completed for each wave: no unexpected `AsyncApexJob` failures, no unexpected exception logs, no unexpected staging rows
- [ ] Post-deployment KPI baseline captured: UI response time P50/P95, batch chain duration P50/P95, exception log rate, staging row rate, support ticket volume at week 1, 2, 4
- [ ] Feature flag (`PRM_UseAsyncProcessing__c`) confirmed to revert each flow to synchronous mode without redeployment
- [ ] BCBSA sync trigger and FDP batch confirmed to exclude `PRM_IsActive__c = false` records

---

*Document References:*
- `TDD_PDMManualUpdate_Practitioner_LargeDataOptimization.md` — Wave 2 Approach A detailed design
- `TDD_PDMManualUpdate_Practitioner_IPToApex.md` — Wave 2 Approach B detailed design
- `PRM_HighVolume_Processing_SK_Estimation.md` — Mass update architecture and estimate
- `PRM_NetworkCreation_Issue_Summary.md` — Root cause and proposed batch architecture
- `PRM_NetworkCreation_BatchImplementation_Guide.md` — Batch class implementation reference
- `PRM_Performance_Issues_Analysis_UserStories.md` — All 5 performance issues with scenarios
- `PRM_Batch_Rollback_Strategies.md` — Rollback strategy options (note: UNION ALL fix applies)
- `UPHS_MASS_LOAD_SOLUTIONS.md` — 107-practitioner mass load scenario analysis
- `requirements/PractitionerCreationPerformance/US_PractitionerCreation_Complete_Implementation.md` — Wave 1 user stories
- `requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md` — Staging object spec
