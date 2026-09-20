# PNM Mass Billing / Mailing Address Update — Full-Stack Architecture
## Front-End (LWC) + Apex Service & Batch Framework · IP/DR/Apex Reuse Matrix · New-Component Blueprint

> **Feature.** Business receives a request with a **Tax ID + Group NPI** and a **new Billing address and/or new Mailing address**. That Tax ID + Group NPI resolves to **hundreds to thousands** of `HealthcareFacility` practice locations. The tool must mass-update the Billing/Mailing `Address` records across all (selected) locations, create **one** QC work item that tracks **every** changed address as a child record, and route it to the QC team for after-the-fact verification.

---

> **Companion docs**
> - Reference architecture (structure mirrored here) — `PNM_PractitionerCreation_Apex_Service_Architecture.md`
> - Framework intent — `PNM_Apex_Service_Architecture.md`
> - QC routing model (decision log) — `../../.agents/artifacts/MassAddressUpdate_QC_Routing_Design.md`
> - UI mockup (IBX/AmeriHealth themed) — `../../.agents/artifacts/MassUpdate_BillingMailingAddress_Mockup.html`
> - Brand tokens for the LWC — `../Mockup_Brand_Style_Guide.md`, `../assets/brand-tokens.css`
> - Bundle invariant + inline remediation — `../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md`
> - High-volume async pattern — `../PRM_HighVolume_Processing_SK_Estimation.md`
> - Mass-load batch precedent — `../UPHS_MASS_LOAD_SOLUTIONS.md`

---

## 0. TL;DR

| | PDM Manual Update (single PL today) | Bundle-Aware Billing (planned) | **THIS FLOW — Mass Address Update** |
|---|---|---|---|
| Trigger | OS submit, one Practice Location at a time | Inline panel inside PDM Manual Update | **Standalone ops LWC app page** — one submit fans out to 100s–1000s of PLs |
| Entry surface | `PRM_PDMManualUpdate_English` OmniScript | LWC element in the same OS | New LWC `prmMassAddressUpdate` (no OmniScript) |
| Resolution key | user picks one HCF | one HCF in context | **Tax ID + Group NPI → all `HealthcareFacility` under the group** |
| Records changed | 1–2 `Address` rows | 1 PL or N bundle members | **N `Address` rows** (Billing and/or Mailing), one per selected PL |
| QC routing | 1 Case + 1 IndividualApplication + `PRM_CaseDataManager__c` per change | 1 Case per bundle removal | **1 Case + 1 IndividualApplication + 1 `PRM_CaseDataManager__c` + N `PRM_CaseManagerAssociation__c`** (one per address) — verified after the fact |
| Execution | synchronous DR Post chain | inline IP loop | **async Batch** (`Database.Batchable`, scope 200), records set Active on completion |
| Front end | OmniScript screens | OS + LWC | **5-step LWC**: Identify → Review grid → Confirm → Async progress → QC verification grid |
| Reusable backend | DR/IP heavy | DR/IP heavy | **~55% reuse** of existing Apex/DR/LWC; the "service framework" in the reference doc does **not** exist yet, so this design uses a **pragmatic orchestrator + existing CMA/address/batch primitives** |
| Net-new Apex | n/a | ~6 | **9 classes** (1 controller, 1 orchestrator, 1 resolver/selector, 1 batch, 1 batch-finish notifier, 1 CMA mass helper, 1 rollback batch, 1 wrapper DTO set, 1 test factory) |
| Net-new LWC | n/a | 4 | **6 bundles** (1 container + 5 children), heavy reuse of `prmEnhancedDatatable`, `prmGenericConfirmModal`, `prmNotesCapture`, `addressValidationModal`, `prmAddressUtils`, `prmExceptionLoggerUtil` |

**Bottom line.** This is a **net-new, full-stack** feature, not an IP-to-Apex migration. The single most important reuse discovery: the org already has the **`PRM_CaseManagerAssociation__c`** object and **`PRM_CaseManagerAssociationAddressBuilder.createCMAForUpdatedAddressIds(newAddrId, oldAddrId, facilityId, caseManagerId)`** — the exact primitive for the business's chosen model of *one QC case tracking each address change as a child record*. We compose that with the existing address-load DataRaptor (`PRMDRLoadMailingAndBillingAdd`), the Tax ID + NPI extractor (`PRMDREAccountNpiTaxId`), the QC-case DataRaptors (`PRMDRCreateCaseCaseManagerBundleExist` / `PRMCreateCaseDatamanager`), the proven **stateful-batch** pattern (`PRM_CaseManagerAssociationBatch`, `PRM_HCFBundleAssociationBatch`), `PRM_ExceptionLogger`, and the `prmEnhancedDatatable` LWC. The **service framework** referenced by `PNM_PractitionerCreation_Apex_Service_Architecture.md` (`PRM_BaseService`, `PRM_ServiceDispatcher`, `PRM_DMLUtil`, …) is **aspirational — it is not in the codebase** — so this design is written against what actually exists, with a thin orchestrator instead.

---

## 0.1 Reality check — what the reference doc assumes vs. what exists

The reference architecture (`PNM_PractitionerCreation_Apex_Service_Architecture.md`) is written against a **target** service framework. A direct verification of `force-app/main/default/classes/` shows these classes **do not exist**:

| Class referenced by the reference doc | In the codebase? |
|---|---|
| `PRM_BaseService`, `PRM_ServiceDispatcher`, `PRM_ServiceRequest`, `PRM_ServiceResponse`, `PRM_ServiceInvoker`, `PRM_TransactionContext` | ❌ none |
| `PRM_DMLUtil`, `PRM_CollectionUtil`, `PRM_GovernorUtil`, `PRM_RecordTypeUtil`, `PRM_BulkOperation` | ❌ none |
| `PRM_AsyncJobBase`, `PRM_AsyncEnqueueGuard`, `PRM_FeatureConfig` | ❌ none |

The real codebase is **OmniStudio-first** (1,483 IPs, 1,409 DataRaptors) with **621 focused Apex classes** (services, builders, selectors, batches). This design therefore does **not** depend on the imaginary framework. It uses a single pragmatic orchestrator (`PRM_MassAddressUpdateService`) plus a Batchable, and reuses the concrete classes that actually ship. Where the reference doc says "REUSE `PRM_DMLUtil`", we say "use `Database.insert(list, false)` + `PRM_ExceptionLogger`" — the established pattern in `PRM_CaseManagerAssociationBatch`.

> **Decision needed (D-0):** Do we (a) keep this feature self-contained on existing primitives [recommended — ships fastest, lowest risk], or (b) seed the `PRM_BaseService`/dispatcher framework here so future flows inherit it? This doc assumes (a) and notes the (b) seams in §3.6.

---

## 1. Current State: there is no mass path today

### 1.1 What exists for *single*-PL address change

The only production way to change a Billing/Mailing address today is the **PDM Manual Update** OmniScript, one Practice Location at a time:

```
PRM_PDMManualUpdate_English (OmniScript)
   └── Step "Update Billing and/or Mailing address"
         ├── AddressActionType  (Select: "Update Mailing Address" |
         │                               "Update Billing Address" |
         │                               "Update Mailing and Billing Address")
         ├── BillingAddressBlock / MailingAddressBlock   (entry fields)
         ├── AddressValidation                            (Precisely standardize)
         ├── IP_CheckAddressUpdated → PRM_CheckAddressUpdated (IP)
         └── submit → PRM_PDMRecordsCreationParent (IP)
                        └── PRM_PDMRecordsCreationHelper (IP, 76 elt)
                              ├── DR: PRMDRLoadMailingAndBillingAdd     → upsert Address (Billing/Mailing)
                              ├── DR: PRMDRCreateCaseCaseManagerBundleExist → Case + IndividualApplication
                              ├── DR: PRMCreateCaseDatamanager          → PRM_CaseDataManager__c
                              └── (bundle branch) PRM_ManageHCFBundleAndAssociations
```

**Why it doesn't scale to 1000s.** The OmniScript re-serializes its data JSON on every keystroke and the IP chain runs **synchronously** — the same failure mode catalogued in `PRM_HighVolume_Processing_SK_Estimation.md` (governor-limit and UI-timeout exposure above ~15–25 repeating rows). There is **no** Tax ID + Group NPI fan-out anywhere in the flow.

### 1.2 The capitated-bundle invariant (carried forward)

`PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md` establishes the rule: **Practice Locations in a capitated bundle must share the same billing address.** In QA there are 1,577 active capitated bundles, max 32 bundles for one Tax ID. Per the business decision for this feature, bundle members are **flagged "warn only"** (see §7) — updated as selected, with their CMA records split to a Provider Contracting child case.

### 1.3 Object model (verified)

```
Account (Vendor / Group)
   ├── PRM_TaxId__c                         ← Tax ID (also as Identifier, Type = EIN)
   └── HealthcareFacility (Practice Location)         AccountId → Account
         ├── PRM_NPI__c                     ← Group NPI  (primary resolution key)
         ├── LocationId → Location
         │                  └── Address (1..N)
         │                        ├── PRM_AddressType__c   ('Billing' | 'Mailing' | 'Primary' | multi)
         │                        ├── PRM_AddressLine1__c / 2 / City / State / Zip / Zip4 / County
         │                        ├── PRM_Phone__c / PRM_Fax__c
         │                        ├── PRM_Active__c / PRM_IsErrorRecord__c / PRM_Pending__c
         │                        └── PRM_EffectiveFrom__c / PRM_EffectiveTo__c
         └── PRM_HealthcareFacilityBundleAssociation__c → PRM_HealthcareFacilityBundle__c
                                                            (PRM_BundleType__c = 'Capitated Bundle')

QC tracking objects (all exist):
   Case (Type "Network Management QC", RT PRM_PRM, PRM_IsRoundRobinLogic__c)
     └── IndividualApplication ("Case Manager", RT PRM_PDMManualChange, Category "Provider Data Management",
                                 Stage "Network Management QC")
           ├── PRM_CaseDataManager__c (PRM_Address__c = true ← "this case changed an address")
           └── PRM_CaseManagerAssociation__c (1 per changed address) ← the per-address QC worklist
                 ├── PRM_CaseManager__c        → IndividualApplication
                 ├── PRM_Address__c            → Address
                 ├── PRM_HealthcareFacility__c → HealthcareFacility
                 └── PRM_RequestType__c        (text — stamp "Mass Billing Address Update" etc.)
```

---

## 2. Records Created / Updated by this feature

### 2.1 The fan-out, per submitted job

For a job resolving **N** practice locations (e.g. 1,284), updating Billing only:

| SObject | Operation | Volume | Source |
|---|---|---|---|
| `Address` (Billing) | UPDATE (or INSERT if none) | **N** (minus already-matching) | `PRMDRLoadMailingAndBillingAdd` (reused) or `PRM_MassAddressUpdateBatch` DML |
| `Case` | INSERT | **1** | `PRMDRCreateCaseCaseManagerBundleExist` (reused) |
| `IndividualApplication` (Case Manager) | INSERT | **1** | same DR |
| `PRM_CaseDataManager__c` | INSERT | **1** (`PRM_Address__c=true`) | `PRMCreateCaseDatamanager` (reused) |
| `PRM_CaseManagerAssociation__c` | INSERT | **N** (one per address; 2N if old+new tracked) | `PRM_CaseManagerAssociationAddressBuilder.createCMAForUpdatedAddressIds(...)` (reused) |
| `Case` (bundle child) | INSERT | **0–B** (one per affected bundle) | new orchestrator path |

"Billing & Mailing" doubles the `Address` and CMA counts. **No** HealthcareFacility / HFN / taxonomy rows are touched — this flow only writes Address + the QC tracking chain. That keeps each batch execute() well under DML limits at scope 200.

### 2.2 State transitions

Per business decision, **records are set Active when the PDA's update completes** (activate-then-verify), mirroring today's PDM behavior — QC is a downstream quality check, not a gate:

| Phase | Address state | CMA `PRM_QCVerdict__c` (new field) |
|---|---|---|
| Batch execute | `PRM_Active__c = true` immediately on successful upsert | `Pending Verification` |
| Batch error on a row | row left unchanged; logged to `PRM_ExceptionLog__c` | `Error` |
| QC verifies | unchanged (already Active) | `Verified` |
| QC flags a row | unchanged | `Flagged` → correction re-run by `PRM_RequestId__c` |

### 2.3 Volume profile (worst case)

| Quantity | Value |
|---|---|
| Practice locations resolved | up to ~3,000 for the largest Tax ID + NPI |
| Address rows updated (Billing+Mailing) | up to ~6,000 |
| CMA rows | up to ~6,000 (or 12,000 if old+new snapshot) |
| Batches @ scope 200 | ~30–60 |
| QC cases | **1** parent + (0–B bundle children) |

This is the case the synchronous IP chain **cannot** handle and why the design is batch-first.

---

## 3. Target Architecture (Front-End + Apex Back-End)

### 3.1 Full-stack layered diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FRONT END — Lightning App Page  "Mass Address Update"  (Network Mgmt / PDM ops)  │
│                                                                                   │
│  prmMassAddressUpdate (container, OmniscriptBaseMixin NOT needed — standalone)    │
│    ├── prmMauIdentifyStep      Step 1: Tax ID + Group NPI + new Billing/Mailing   │
│    │      └── (reuse) prmGenericSearchInput, addressValidationModal,              │
│    │                  prmAddressUtils (phone/zip/normalize)                        │
│    ├── prmMauReviewGrid        Step 2: resolved PLs, pre-selected, bundle-flagged  │
│    │      └── (reuse) prmEnhancedDatatable (selection, pagination, search, sort)   │
│    ├── prmMauConfirmStep       Step 3: summary + reason                            │
│    │      └── (reuse) prmGenericConfirmModal, prmNotesCapture                      │
│    ├── prmMauProgress          Step 4: async job progress (poll/subscribe)         │
│    └── prmMauQcReview          Step QC: verify CMA records, bulk verify / flag     │
│           └── (reuse) prmEnhancedDatatable, prmGenericConfirmModal                 │
│    (cross-cutting) prmExceptionLoggerUtil mixin · brand-tokens.css theming         │
│           │  @wire / imperative Apex                                               │
├───────────┼───────────────────────────────────────────────────────────────────────┤
│  APEX CONTROLLER (NEW)                                                             │
│   PRM_MassAddressUpdateController   (@AuraEnabled façade for the LWC)              │
│     resolveLocations(taxId, groupNpi, statusFilter, page) ─┐                       │
│     previewImpact(criteria)                                │ read                  │
│     submitMassUpdate(jobRequestJson)  ─────────────────────┼─ write (kick async)   │
│     getJobStatus(jobId) / getQcWorklist(caseManagerId)     │ poll / QC             │
│     verifyAssociations(ids) / flagAssociation(id, note)    │ QC verbs              │
├───────────────────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION (NEW — pragmatic, NOT the imaginary PRM_BaseService framework)      │
│   PRM_MassAddressUpdateService                                                    │
│     ├─ validateRequest(req)           (Precisely standardize new address once)     │
│     ├─ resolveFacilities(taxId, npi)  → PRM_MassAddressLocationResolver            │
│     ├─ createQcWorkItem(req)          → Case + IndividualApplication + CDM         │
│     └─ enqueue(PRM_MassAddressUpdateBatch)                                         │
│   PRM_MassAddressUpdateBatch  (Database.Batchable<HealthcareFacility>, Stateful)   │
│     start()   → resolver.queryLocator(taxId, npi, statusFilter, selectedIds)       │
│     execute() → upsert Address (Active) + build CMA rows + per-row error log       │
│     finish()  → publish PRM_ExceptionLogEvent / notify; close-out counts on job    │
│   PRM_MassAddressRollbackBatch (Database.Batchable<sObject>)  — revert by RequestId│
├───────────────────────────────────────────────────────────────────────────────────┤
│  DOMAIN PRIMITIVES (REUSE — concrete classes that exist)                          │
│   PRM_CaseManagerAssociationAddressBuilder.createCMAForUpdatedAddressIds(...)      │  ← per-address QC row
│   PRM_CaseManagerAssociationService.insertCaseManagerAssociations(list, iaId)     │  ← bulk insert CMA
│   PRM_AddressValidationService.validateAddress(input) / isPreciselySkipped()      │  ← Precisely standardize
│   PRM_AddressManagementService.markAddressAsError(...) (soft-delete on rollback)  │
│   PRM_LocationQueryService (facility/address query façade)                        │
│   PRM_ExistingAccountService (Tax ID / NPI account validation)                    │
│   PRM_GlobalConstant (RecordType Ids, Status, Category, Stage constants)          │
│   PRM_ExceptionLogger.logException(...) (per-row + job-level error log)           │
├───────────────────────────────────────────────────────────────────────────────────┤
│  OMNISTUDIO PRIMITIVES (REUSE — optional, callable from Apex via Callable)        │
│   DR PRMDREAccountNpiTaxId          (Account by Group NPI + Tax ID)               │
│   DR PRMDRLoadMailingAndBillingAdd  (Address upsert, Billing/Mailing)            │
│   DR PRMDRCreateCaseCaseManagerBundleExist (Case + IndividualApplication)         │
│   DR PRMCreateCaseDatamanager       (PRM_CaseDataManager__c)                       │
│   IP PRM_ManageHCFBundleAndAssociations (bundle child-case path, if needed)        │
├───────────────────────────────────────────────────────────────────────────────────┤
│  DATA + PLATFORM                                                                   │
│   Address · HealthcareFacility · Account · Case · IndividualApplication           │
│   PRM_CaseDataManager__c · PRM_CaseManagerAssociation__c (+ new fields §3.4)       │
│   PRM_MassAddressJob__c (NEW — parent job/progress record)                         │
│   PRM_ExceptionLog__c · PRM_ExceptionLogEvent__e (existing)                        │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why batch (not OmniScript IP, not synchronous)

| Concern | Synchronous IP | **Async Batch (chosen)** |
|---|---|---|
| 1,000s of Address upserts | governor-limit / timeout (see SK doc) | scope 200 → ≤ ~600 DML/exec, comfortably under limits |
| User wait | minutes / browser freeze | submit returns in < 2 s with a job id |
| Partial failure | unknown state, no recovery | per-row error log + re-run by `PRM_RequestId__c` |
| Re-runability | redo whole form | re-queue failed rows only |
| Precedent | — | `PRM_CaseManagerAssociationBatch`, `PRM_HCFBundleAssociationBatch`, `PRM_UPHSPractitionerLocationBatch` |

### 3.3 Transaction boundaries

| Phase | TX | Scope | Rationale |
|---|---|---|---|
| 1 | Sync (controller request) | Precisely-standardize the **one** new Billing/Mailing address; validate Tax ID + NPI resolve to a real group | One callout, fast; reject bad input before any DML |
| 2 | Sync | INSERT Case + IndividualApplication + `PRM_CaseDataManager__c`; INSERT `PRM_MassAddressJob__c` (Status=Queued, RequestId=UUID) | The LWC needs the Case/Job id immediately to show progress |
| 3 | Sync | `Database.executeBatch(new PRM_MassAddressUpdateBatch(jobId), 200)` | Fire-and-forget; controller returns `{ jobId, caseId, caseManagerId }` |
| 4 | **Async batch execute()** | per scope of 200 HCF: upsert Address (Active), build + insert CMA rows, stamp `PRM_RequestId__c`, per-row error capture | The heavy fan-out; idempotent per row |
| 5 | Async batch finish() | update `PRM_MassAddressJob__c` (Processed/Error counts, Status=Completed), publish event, split bundle children | Close-out + QC notification |
| 6 | Later, QC LWC | UPDATE `PRM_CaseManagerAssociation__c.PRM_QCVerdict__c` (Verified/Flagged) | After-the-fact verification |

### 3.4 New custom fields & object

| Object | Field / Object | Type | Purpose |
|---|---|---|---|
| `PRM_CaseManagerAssociation__c` | `PRM_QCVerdict__c` | Picklist (`Pending Verification`/`Verified`/`Flagged`/`Corrected`) | per-address QC state |
| `PRM_CaseManagerAssociation__c` | `PRM_OldAddressSnapshot__c` | Long Text (JSON) | pre-change values (QC diff + rollback) |
| `PRM_CaseManagerAssociation__c` | `PRM_NewAddressSnapshot__c` | Long Text (JSON) | post-change values |
| `PRM_CaseManagerAssociation__c` | `PRM_RequestId__c` | Text(36) | rollback / re-run key |
| `PRM_CaseManagerAssociation__c` | `PRM_BundleFlag__c` | Checkbox | in an active capitated bundle |
| `Address` (or reuse existing) | `PRM_RequestId__c` | Text(36) | stamp the originating job (rollback) |
| **NEW** `PRM_MassAddressJob__c` | object | — | parent job/progress (see below) |

**`PRM_MassAddressJob__c`** (mirrors the staging pattern in `UPHS_MASS_LOAD_SOLUTIONS.md` and `PRM_AsyncJobRequest__c` proposal):

| Field | Type | Purpose |
|---|---|---|
| `Name` | Auto `MAU-{00000}` | — |
| `PRM_Status__c` | Picklist `Queued/Processing/Completed/Failed/RolledBack` | progress |
| `PRM_TaxId__c`, `PRM_GroupNPI__c` | Text | resolution keys |
| `PRM_AddressActionType__c` | Picklist `Billing/Mailing/Both` | what changed |
| `PRM_NewAddressJSON__c` | Long Text | standardized new address payload |
| `PRM_CaseId__c` / `PRM_CaseManagerId__c` | Lookup | the QC work item |
| `PRM_RequestId__c` | Text(36) | UUID stamped on all touched records |
| `PRM_TotalResolved__c` / `PRM_Selected__c` / `PRM_Processed__c` / `PRM_Errors__c` / `PRM_BundleCount__c` | Number | counts for the progress UI |
| `PRM_SubmittedBy__c` | Lookup(User) | audit |
| `PRM_Reason__c` | Long Text | mandatory change reason |

### 3.5 Front-end ↔ Apex contract

```
Step 1 → controller.resolveLocations({taxId, groupNpi, statusFilter})
            → { groupName, totalResolved, bundleCount, alreadyMatchCount, page[] }
Step 1 → controller.validateAddress(addressInput)   // reuse PRM_AddressValidationService
            → { standardized, suggestions[], skipped }
Step 2 → controller.resolveLocations(..., page, pageSize)   // server-side paging for 1000s
Step 3 → controller.submitMassUpdate({taxId, groupNpi, actionType, billing, mailing,
                                       selectedFacilityIds | deselectedFacilityIds, reason})
            → { jobId, caseId, caseManagerId }    // returns in <2s, batch enqueued
Step 4 → controller.getJobStatus(jobId)   // poll every 5s OR subscribe to platform event
            → { status, processed, total, errors, bundleCount }
Step QC→ controller.getQcWorklist(caseManagerId, filter, page)
            → CMA rows [{id, facility, plNumber, oldAddr, newAddr, recordStatus, bundleFlag, verdict}]
Step QC→ controller.verifyAssociations(cmaIds[]) | flagAssociation(cmaId, note)
```

> **Selection at scale.** For 1000s of rows the LWC sends **`deselectedFacilityIds`** (the exceptions the user unchecked) rather than the full selected set; the batch resolves "all minus deselected" server-side. Pre-selected-with-deselect was the chosen UX.

### 3.6 Optional framework seam (Decision D-0 = b)

If the team wants to seed the reference-doc framework here: introduce `PRM_BaseService` + `PRM_ServiceDispatcher` + `PRM_ServiceResponse`, register `PRM_MassAddressUpdateService` under key `"MassAddressUpdate"`, and have the controller call `PRM_ServiceDispatcher.invoke(...)`. The orchestration logic is identical; only the entry shape changes. **Not recommended for v1** — it adds 4 net-new framework classes with no existing tests and no other consumers yet.

---

## 4. Reusability Matrix

### 4.1 Apex — Framework / Cross-cutting

| Class | Exists? | Disposition | Why this flow needs it |
|---|---|---|---|
| `PRM_BaseService` / `PRM_ServiceDispatcher` / `PRM_ServiceRequest` / `PRM_ServiceResponse` / `PRM_TransactionContext` | ❌ no | **N/A (aspirational)** | Reference doc only; not used in v1 |
| `PRM_DMLUtil` / `PRM_CollectionUtil` / `PRM_GovernorUtil` / `PRM_RecordTypeUtil` / `PRM_BulkOperation` | ❌ no | **pattern-only** | Use `Database.insert(list,false)` + `Schema describe` inline, as `PRM_CaseManagerAssociationBatch` does |
| `PRM_ExceptionLogger` | ✅ yes | **REUSE** | `logException(class, method, level, stack, msg, type, line, …)` — per-row + job error log |
| `PRM_GlobalConstant` | ✅ yes | **REUSE** | `RECTYPEID_PRM_PRM` (Case RT), IndividualApplication RT, `CATEGORY_PDM='Provider Data Management'`, `STS_NEW` |
| `PRM_ExceptionLogEvent__e` | ✅ yes | **REUSE** | publish from `finish()` for the progress UI / monitoring |

### 4.2 Apex — Address / Location

| Class | Exists? | Disposition | Notes |
|---|---|---|---|
| `PRM_AddressValidationService` | ✅ yes | **REUSE** | `validateAddress(input)`, `isPreciselySkipped()` — standardize the one new address in Step 1 |
| `PRM_AddressManagementService` | ✅ yes | **EXTEND** | reuse `markAddressAsError(...)` for rollback; add `bulkUpsertAddress(List<Address>, requestId)` |
| `PRM_LocationQueryService` | ✅ yes | **EXTEND** | facility/address query façade; add `queryLocatorByTaxIdAndNpi(...)` for the batch start() |
| `PRM_AddressPicklistService` | ✅ yes | **REUSE** | state/county picklists for the Step 1 form |
| `PRM_AddressSelector` | ✅ yes | **REUSE** | Address SOQL |
| `PRM_ExistingAccountService` | ✅ yes | **EXTEND** | validate Tax ID + Group NPI → group Account; add `resolveGroupByTaxIdAndNpi(taxId, npi)` |
| `PRM_SmartAddressSearch` | ⚠️ stub | **pattern-only** | not production-grade; do not depend on it |

### 4.3 Apex — Case Manager Association (the core reuse win)

| Class | Exists? | Disposition | Notes |
|---|---|---|---|
| `PRM_CaseManagerAssociation__c` (object) | ✅ yes | **REUSE** | fields incl. `PRM_Address__c`, `PRM_CaseManager__c`, `PRM_HealthcareFacility__c`, `PRM_RequestType__c` |
| `PRM_CaseManagerAssociationAddressBuilder` | ✅ yes | **REUSE** | `createCMAForUpdatedAddressIds(newAddrId, oldAddrId, facilityId, caseManagerId)` — **exact** per-address QC primitive |
| `PRM_CaseManagerAssociationService` | ✅ yes | **REUSE / EXTEND** | `insertCaseManagerAssociations(list, iaId)` bulk insert; extend with a mass-friendly entry that skips the OS-payload router |
| `PRM_CaseManagerAssociationBatch` | ✅ yes | **pattern** | the canonical `Database.Batchable + Stateful` over `IndividualApplication`, `Database.insert(list,false)`, error capture, `finish()` |
| `PRM_CaseManagerAssociationDirectBuilder` / `…NetworkBuilder` | ✅ yes | **not needed** | network/identifier builders — out of scope (address only) |
| `PRM_CMARecordTypeHelper` | ✅ yes | **REUSE** | `getCaseManagerAssociationRecordTypeId('Practice_Location_Address')` |

### 4.4 Apex — Case / Case Manager creation

| Component | Exists? | Disposition | Notes |
|---|---|---|---|
| `PRMDRCreateCaseCaseManagerBundleExist` (DR) | ✅ yes | **REUSE** | Case + IndividualApplication (RT PRM_PRM / PRM_PDMManualChange) |
| `PRMCreateCaseDatamanager` (DR) | ✅ yes | **REUSE** | `PRM_CaseDataManager__c` (set `PRM_Address__c=true`) |
| `PRMCaseMgrCaseDataMgrPDM` (DR) | ✅ yes | **REUSE** | links Case + CDM |
| `PRM_CaseService` (unified Apex) | ❌ no | **build** | thin `createQcWorkItem(jobReq)` that calls the DRs (or does direct DML) — there is no unified Case service today |

### 4.5 Apex — Async / Batch

| Class | Exists? | Disposition | Notes |
|---|---|---|---|
| `PRM_CaseManagerAssociationBatch` | ✅ yes | **pattern** | copy structure for `PRM_MassAddressUpdateBatch` |
| `PRM_HCFBundleAssociationBatch` | ✅ yes | **pattern** | stateful ctor-injection + `Iterable start()` + `PRM_ExceptionLogger` in `execute()`/`finish()` |
| `PRM_PractitionerActivationBatch` | ✅ yes | **pattern** | activate-records-on-completion idiom |
| `PRM_UPHSPractitionerLocationBatch` | ✅ yes (doc'd) | **pattern** | staging-object + `finish()` email summary |
| `PRM_AsyncJobBase` / `PRM_AsyncEnqueueGuard` | ❌ no | **pattern-only** | plain `Database.executeBatch(...)`; no guard wrapper exists |

### 4.6 Apex — Tax ID + Group NPI resolution

| Component | Exists? | Disposition | Notes |
|---|---|---|---|
| `PRMDREAccountNpiTaxId` (DR) | ✅ yes | **REUSE** | Account by Group NPI (`PRM_NPI__c`) + Tax ID (EIN Identifier) |
| `PRMDRExtractGroupNameBasedOnTINNPI` (DR) | ✅ yes | **REUSE** | group display name for the Step 1 readback |
| `PRM_MassAddressLocationResolver` | ❌ no | **build** | the one genuinely new selector: `SELECT … FROM HealthcareFacility WHERE PRM_NPI__c = :npi AND Account.PRM_TaxId__c = :taxId AND PRM_IsErrorRecord__c=false [status filter]` → QueryLocator for the batch + paged list for the grid |

### 4.7 Front-End — LWC

| Component | Exists? | Disposition | What it gives the tool |
|---|---|---|---|
| `prmEnhancedDatatable` | ✅ yes | **REUSE** | Step 2 review grid + Step QC grid: selection (`maxrowselection`), pagination, search (`customFieldsSearch`), sort; `getselectedrows` event, `resetSelection()` |
| `prmGenericSearchInput` | ✅ yes | **REUSE** | Step 1 Tax ID / NPI inputs; emits `valuechange` |
| `addressValidationModal` | ✅ yes | **REUSE** | Step 1 "did you mean?" Precisely result (`addressselected` event, original vs standardized tiles) |
| `prmAddressUtils` (module) | ✅ yes | **REUSE** | `formatPhone()`, `stripNonNumeric()`, `validateLocationFields()`, `normalizeAddressShape()` |
| `prmGenericPagination` | ✅ yes | **REUSE** | server-side paging controls (alt to datatable paging for 1000s) |
| `prmGenericConfirmModal` | ✅ yes | **REUSE** | Step 3 confirm + Step QC approve/reject (`confirm`/`cancel`, optional notes) |
| `prmNotesCapture` | ✅ yes | **REUSE** | mandatory change reason (Step 3); QC flag note |
| `prmExceptionLoggerUtil` (mixin) | ✅ yes | **REUSE** | error logging + toast in the container |
| `prmAddressGroupManager` | ✅ yes | **pattern / partial** | gold-standard address workflow; reuse its Precisely + picklist patterns, not wholesale |
| `prmAddressComparisonParForm` | ✅ yes | **pattern** | side-by-side old/new address — reference for the QC diff cell |
| `prmOmniUtils` (LWC) | ✅ yes | **optional** | only if any step calls a DR/IP from the LWC |
| step/wizard/progress-path | ❌ no | **build** | small SLDS path component (see mockup) |
| async job progress card | ❌ no | **build** | Step 4 progress (poll `getJobStatus` or subscribe to `PRM_ExceptionLogEvent__e`) |

### 4.8 Reuse Score

| Bucket | Reuse | Extend | New | Pattern-only / N-A | Total considered |
|---|---|---|---|---|---|
| Apex framework/cross-cutting | 3 | 0 | 1 (`PRM_CaseService` helper) | 8 | 12 |
| Apex address/location | 4 | 3 | 1 (resolver) | 1 | 9 |
| Apex CMA | 4 | 1 | 0 | 2 | 7 |
| Apex case/async | 3 (DRs) | 0 | 2 (batch, rollback batch) | 5 | 10 |
| Front-end LWC | 9 | 0 | 6 (container + 5 children) | 3 | 18 |
| **Totals** | **23** | **4** | **10** | **19** | **56** |

**Reuse % = (Reuse + Extend) / (Reuse + Extend + New) = (23 + 4) / (23 + 4 + 10) = 73%** of the components that must be *built or wired* are existing-or-extended; **10 net-new** classes/bundles. (Pattern-only items aren't counted as build cost — they inform the new code but aren't wired in.)

---

## 5. Front-End Build Map (LWC)

### 5.1 Component tree & responsibilities

```
prmMassAddressUpdate                       (container — owns wizard state, Apex calls)
│   state: { step, criteria, newBilling, newMailing, resolved{}, selection, jobId, caseManagerId }
│   extends prmExceptionLoggerUtil(LightningElement)
│   theming: imports brand-tokens (data-brand attribute, default IBX)
│
├── prmMauPath                             (NEW — SLDS progress path: 1·2·3·4·QC)
│
├── prmMauIdentifyStep                     (NEW — Step 1)
│     ├── c-prm-generic-search-input  ×2   (Tax ID, Group NPI)             [REUSE]
│     ├── group readback (name)            (← controller.resolveGroup)
│     ├── action-type segmented control    (Billing | Mailing | Both)
│     ├── address sub-form (line1/2,city,state,zip,zip4,county,phone,fax)
│     │     uses prmAddressUtils.formatPhone / validateLocationFields        [REUSE]
│     └── c-address-validation-modal       (Precisely "did you mean?")       [REUSE]
│
├── prmMauReviewGrid                       (NEW — Step 2)
│     └── c-prm-enhanced-datatable                                           [REUSE]
│           columns: select | PL name | PL# | current addr | → | new addr | status
│           maxrowselection = (resolved count), all rows pre-checked
│           bundle rows: warning row-class + badge
│           server-side paging via controller.resolveLocations(page,pageSize)
│           filter chips: All / In bundle / Already matches / No billing yet
│           emits getselectedrows → container tracks DESELECTED ids
│
├── prmMauConfirmStep                      (NEW — Step 3)
│     ├── summary recap (counts, new address, bundle note)
│     ├── c-prm-notes-capture (required reason)                              [REUSE]
│     └── c-prm-generic-confirm-modal (authorize + submit)                   [REUSE]
│
├── prmMauProgress                         (NEW — Step 4)
│     ├── progress bar + stat tiles (Updated / Bundle→Contracting / Errors / Pending)
│     ├── poll controller.getJobStatus(jobId) every 5s  OR
│     └── subscribe empApi → PRM_ExceptionLogEvent__e (job channel)
│
└── prmMauQcReview                         (NEW — Step QC, QC persona)
      └── c-prm-enhanced-datatable                                          [REUSE]
            rows = PRM_CaseManagerAssociation__c (old→new, verdict, bundle flag)
            toolbar: Verify selected / Flag selected / filter (Pending/Verified/Bundle/Errors)
            footer: Approve & Close Case / Send flagged to PDA
            actions → controller.verifyAssociations / flagAssociation
```

### 5.2 Why each new bundle (not just reuse)

- **`prmMassAddressUpdate`** — owns the 5-step state machine and the single point of Apex contact; no existing container matches a Tax-ID-fanout wizard.
- **`prmMauReviewGrid`** — wraps `prmEnhancedDatatable` with the *old→new address diff cell*, bundle row styling, and the **deselect-at-scale** semantics; the datatable itself is reused untouched.
- **`prmMauQcReview`** — same datatable, but bound to `PRM_CaseManagerAssociation__c` with verify/flag verbs; this is the QC persona surface, distinct from the PDA wizard.
- **`prmMauProgress`** / **`prmMauPath`** — no async-progress or wizard-path component exists today (confirmed by inventory); both are small.
- **`prmMauIdentifyStep` / `prmMauConfirmStep`** — thin layout shells that compose reused inputs/modals; they keep the container lean.

### 5.3 Reused LWC API touch-points (verified)

| Reused bundle | Property / event used | In step |
|---|---|---|
| `prmEnhancedDatatable` | `columns`, `source`, `keyField`, `maxrowselection`, `pagination`, `apppagesize`, `enableSearch`, `customFieldsSearch`, `selectedrows`; event `getselectedrows`; method `resetSelection()` | 2, QC |
| `prmGenericSearchInput` | `label`, `placeholder`, `value`; event `valuechange` | 1 |
| `addressValidationModal` | `originalAddress`, `validatedAddress`, `confidence`, `hasMatch`; event `addressselected` | 1 |
| `prmAddressUtils` | `formatPhone()`, `stripNonNumeric()`, `validateLocationFields()`, `normalizeAddressShape()` | 1 |
| `prmGenericConfirmModal` | `title`, `message`, `warningMessage`, `confirmLabel`, `showNotes`; events `confirm`/`cancel` | 3, QC |
| `prmNotesCapture` | `label`, `required`, `maxLength`; method `getNoteText()`, `reportValidity()` | 3 |
| `prmExceptionLoggerUtil` | mixin: `logApexError(err, ctx)`, `logError(title,msg,err)` | container |
| `prmGenericPagination` | `perPage`, `setSize`, `tabledata`; event `change` | 2, QC (optional) |

---

## 6. Back-End Build Map (Apex) — class by class

### 6.1 `PRM_MassAddressUpdateController` (NEW — LWC façade)

> **Why we need it** — The standalone LWC has no OmniScript to call IPs/DRs through; it needs a cacheable read API (resolve/preview) and a transactional write API (submit/verify) with FLS enforced. No existing controller resolves a HealthcareFacility set by Tax ID + Group NPI or exposes a CMA QC worklist.
>
> **How it helps** — One `with sharing` controller, `@AuraEnabled(cacheable=true)` for reads (`resolveLocations`, `getJobStatus`, `getQcWorklist`) and non-cacheable for writes (`submitMassUpdate`, `verifyAssociations`, `flagAssociation`). Delegates all logic to `PRM_MassAddressUpdateService`; the controller only marshals DTOs and enforces sharing.
>
> **Outcome** — Single tested entry point; the LWC is decoupled from the batch and the DRs. Reads are paged (1000s of rows never hit the wire at once).
>
> **Replaces** — n/a (net-new; there is no mass path today).

```apex
public with sharing class PRM_MassAddressUpdateController {

    @AuraEnabled(cacheable=true)
    public static PRM_MassAddressDTO.ResolveResult resolveLocations(String criteriaJson) {
        return PRM_MassAddressUpdateService.resolve(
            (PRM_MassAddressDTO.Criteria) JSON.deserialize(criteriaJson, PRM_MassAddressDTO.Criteria.class));
    }

    @AuraEnabled
    public static PRM_MassAddressDTO.AddressValidation validateAddress(String addressJson) {
        // reuse existing Precisely service
        return PRM_MassAddressUpdateService.standardize(
            (PRM_MassAddressDTO.AddressInput) JSON.deserialize(addressJson, PRM_MassAddressDTO.AddressInput.class));
    }

    @AuraEnabled
    public static PRM_MassAddressDTO.SubmitResult submitMassUpdate(String jobRequestJson) {
        return PRM_MassAddressUpdateService.submit(
            (PRM_MassAddressDTO.JobRequest) JSON.deserialize(jobRequestJson, PRM_MassAddressDTO.JobRequest.class));
    }

    @AuraEnabled(cacheable=true)
    public static PRM_MassAddressDTO.JobStatus getJobStatus(Id jobId) {
        return PRM_MassAddressUpdateService.status(jobId);
    }

    @AuraEnabled(cacheable=true)
    public static List<PRM_MassAddressDTO.QcRow> getQcWorklist(Id caseManagerId, String filter, Integer page, Integer pageSize) {
        return PRM_MassAddressUpdateService.qcWorklist(caseManagerId, filter, page, pageSize);
    }

    @AuraEnabled
    public static void verifyAssociations(List<Id> cmaIds) {
        PRM_MassAddressUpdateService.verify(cmaIds);
    }

    @AuraEnabled
    public static void flagAssociation(Id cmaId, String note) {
        PRM_MassAddressUpdateService.flag(cmaId, note);
    }
}
```

### 6.2 `PRM_MassAddressUpdateService` (NEW — orchestrator)

> **Why we need it** — Submit must do four things atomically in the sync request: standardize the new address (Precisely), validate the group, create the **one** QC work item (Case + IndividualApplication + `PRM_CaseDataManager__c` with `PRM_Address__c=true`), and enqueue the batch — then return ids in < 2 s. No existing class composes these.
>
> **How it helps** — A plain `with sharing` orchestrator (no imaginary `PRM_BaseService`). It reuses `PRM_AddressValidationService` (standardize), `PRM_ExistingAccountService` (group resolve), the Case/CDM DataRaptors via a thin `createQcWorkItem`, then `Database.executeBatch(new PRM_MassAddressUpdateBatch(jobId), 200)`. QC verbs (`verify`/`flag`) are simple `PRM_CaseManagerAssociation__c` updates.
>
> **Outcome** — Submit returns `{jobId, caseId, caseManagerId}` synchronously; the 1000s-row fan-out happens in the batch. One place to test the orchestration with mocked collaborators.
>
> **Replaces** — the synchronous `PRM_PDMRecordsCreationHelper` address branch *for the mass case* (single-PL PDM path is untouched).

```apex
public with sharing class PRM_MassAddressUpdateService {

    public static PRM_MassAddressDTO.SubmitResult submit(PRM_MassAddressDTO.JobRequest req) {
        // 1. standardize the ONE new address (reuse Precisely service)
        if (!PRM_AddressValidationService.isPreciselySkipped()) {
            req.billing = standardizeIfPresent(req.billing);
            req.mailing = standardizeIfPresent(req.mailing);
        }
        // 2. resolve & validate the group (reuse/extend existing account service)
        PRM_MassAddressDTO.Group grp = PRM_ExistingAccountService.resolveGroupByTaxIdAndNpi(req.taxId, req.groupNpi);
        if (grp == null) throw new AuraHandledException('No active group found for Tax ID ' + req.taxId + ' / NPI ' + req.groupNpi);

        String requestId = newRequestId();   // UUID — stamped on every touched record

        // 3. ONE QC work item (Case + IndividualApplication + PRM_CaseDataManager__c)
        PRM_MassAddressDTO.QcWorkItem qc = createQcWorkItem(req, grp, requestId);

        // 4. parent job/progress record
        PRM_MassAddressJob__c job = insertJob(req, grp, qc, requestId);

        // 5. enqueue async fan-out (scope 200)
        Database.executeBatch(new PRM_MassAddressUpdateBatch(job.Id), 200);

        return new PRM_MassAddressDTO.SubmitResult(job.Id, qc.caseId, qc.caseManagerId);
    }

    // QC after-the-fact verbs
    public static void verify(List<Id> cmaIds) {
        List<PRM_CaseManagerAssociation__c> rows = new List<PRM_CaseManagerAssociation__c>();
        for (Id id : cmaIds) rows.add(new PRM_CaseManagerAssociation__c(Id = id, PRM_QCVerdict__c = 'Verified'));
        Database.update(rows, false);
    }

    public static void flag(Id cmaId, String note) {
        Database.update(new PRM_CaseManagerAssociation__c(
            Id = cmaId, PRM_QCVerdict__c = 'Flagged', PRM_QCNote__c = note), false);
    }

    // createQcWorkItem(...) → calls Case/IndividualApplication/CDM DRs (PRMDRCreateCaseCaseManagerBundleExist,
    //   PRMCreateCaseDatamanager) via Callable, OR direct DML using PRM_GlobalConstant record types;
    //   sets Case.PRM_IsRoundRobinLogic__c=true, CDM.PRM_Address__c=true.
    // resolve(...) / standardize(...) / status(...) / qcWorklist(...) — see contract §3.5
}
```

### 6.3 `PRM_MassAddressUpdateBatch` (NEW — the fan-out engine)

> **Why we need it** — Upserting Billing/Mailing `Address` across 100s–1000s of locations and creating a CMA row per address is exactly the workload that breaks the synchronous IP chain (`PRM_HighVolume_Processing_SK_Estimation.md`). It must be chunked, idempotent per row, error-isolated, and re-runnable.
>
> **How it helps** — A `Database.Batchable<SObject>, Database.Stateful` modeled on `PRM_CaseManagerAssociationBatch` and `PRM_HCFBundleAssociationBatch`. `start()` returns the resolver's QueryLocator (all HCF for Tax ID + NPI, minus deselected). `execute()` upserts the Address (set `PRM_Active__c=true`), stamps `PRM_RequestId__c`, builds CMA rows via `PRM_CaseManagerAssociationAddressBuilder.createCMAForUpdatedAddressIds(...)`, and captures per-row `Database.SaveResult` errors into `PRM_ExceptionLogger`. `finish()` updates `PRM_MassAddressJob__c` counts, splits bundle CMA rows to a Provider Contracting child case, and publishes the completion event.
>
> **Outcome** — Linear, governor-safe scaling; one bad row never fails the batch; failed rows re-runnable by `PRM_RequestId__c`. Records are Active on completion (activate-then-verify, per business decision).
>
> **Replaces** — there is no current mass equivalent; this is the engine the feature is built on.

```apex
public class PRM_MassAddressUpdateBatch implements Database.Batchable<SObject>, Database.Stateful {

    private final Id jobId;
    private PRM_MassAddressJob__c job;
    private Integer processed = 0, errors = 0, bundleHits = 0;

    public PRM_MassAddressUpdateBatch(Id jobId) { this.jobId = jobId; }

    public Database.QueryLocator start(Database.BatchableContext bc) {
        this.job = PRM_MassAddressUpdateService.loadJob(jobId);   // status → Processing
        return PRM_MassAddressLocationResolver.queryLocator(job);  // all HCF for TaxId+NPI minus deselected
    }

    public void execute(Database.BatchableContext bc, List<HealthcareFacility> scope) {
        List<Address> addrToUpsert = new List<Address>();
        Map<Id, Address> oldByFacility = PRM_MassAddressLocationResolver.currentAddresses(scope, job.PRM_AddressActionType__c);
        // 1. shape new Address rows from job payload (Billing and/or Mailing) per facility
        for (HealthcareFacility hcf : scope) {
            addrToUpsert.addAll(PRM_MassAddressUpdateService.buildAddressRows(hcf, job, oldByFacility.get(hcf.Id)));
        }
        // 2. upsert addresses (Active) — partial success
        Database.UpsertResult[] ur = Database.upsert(addrToUpsert, Address.Id, false);
        // 3. build + insert CMA rows for the successful ones (reuse existing builder)
        List<PRM_CaseManagerAssociation__c> cma = new List<PRM_CaseManagerAssociation__c>();
        for (Integer i = 0; i < ur.size(); i++) {
            if (ur[i].isSuccess()) {
                Address a = addrToUpsert[i];
                cma.addAll(PRM_CaseManagerAssociationAddressBuilder.createCMAForUpdatedAddressIds(
                    a.Id, (oldByFacility.containsKey(a.ParentId) ? oldByFacility.get(a.ParentId).Id : null),
                    a.ParentId /*facilityId*/, job.PRM_CaseManagerId__c));
                processed++;
            } else {
                errors++;
                PRM_ExceptionLogger.logException('PRM_MassAddressUpdateBatch', 'execute', 'Error',
                    '', ur[i].getErrors()[0].getMessage(), 'DmlException', 0, '', '', 'Salesforce', '', jobId);
            }
        }
        // stamp request id + verdict + snapshots on CMA, then insert (partial success)
        PRM_MassAddressUpdateService.stampAndInsertCma(cma, job, oldByFacility);
    }

    public void finish(Database.BatchableContext bc) {
        PRM_MassAddressUpdateService.closeOutJob(jobId, processed, errors, bundleHits);  // status Completed + counts
        PRM_MassAddressUpdateService.splitBundleChildCases(jobId);                        // §7
        // publish PRM_ExceptionLogEvent__e (job channel) → progress UI / QC notify
    }
}
```

### 6.4 `PRM_MassAddressLocationResolver` (NEW — the only new selector)

> **Why we need it** — No existing class resolves "all `HealthcareFacility` under a Tax ID + Group NPI" as a `QueryLocator` (for the batch) *and* a paged list (for the grid). `PRM_LocationQueryService` takes an Account Id, not Tax ID + NPI.
>
> **How it helps** — One selector with two entry points sharing the same `WHERE`: `queryLocator(job)` for the batch and `page(criteria, page, size)` for the grid. The predicate is `PRM_NPI__c = :npi AND Account.PRM_TaxId__c = :taxId AND PRM_IsErrorRecord__c = false [+ status]`, minus `Id IN :deselected`.
>
> **Outcome** — Single source of truth for the resolution query; the grid and the batch can never drift. Bundle membership flagged via a sub-select on `PRM_HealthcareFacilityBundleAssociation__c`.
>
> **Replaces** — the would-be `PRMDREAccountNpiTaxId` round-trip from the LWC (we keep that DR available but resolve in Apex for paging control).

```apex
public with sharing class PRM_MassAddressLocationResolver {

    public static Database.QueryLocator queryLocator(PRM_MassAddressJob__c job) {
        Set<Id> deselected = parseIds(job.PRM_DeselectedIds__c);
        String soql =
            'SELECT Id, Name, PRM_NPI__c, AccountId, LocationId, ' +
            ' (SELECT Id, PRM_HealthcareFacilityBundle__c FROM PRM_HealthcareFacilityBundleAssociations__r ' +
            '   WHERE PRM_Active__c = true) ' +
            'FROM HealthcareFacility ' +
            'WHERE PRM_NPI__c = :npi AND Account.PRM_TaxId__c = :taxId AND PRM_IsErrorRecord__c = false';
        if (job.PRM_StatusFilter__c == 'Active') soql += ' AND PRM_Active__c = true';
        if (!deselected.isEmpty()) soql += ' AND Id NOT IN :deselected';
        String npi = job.PRM_GroupNPI__c, taxId = job.PRM_TaxId__c;
        return Database.getQueryLocator(soql);
    }

    public static List<PRM_MassAddressDTO.LocationRow> page(PRM_MassAddressDTO.Criteria c, Integer page, Integer size) { /* OFFSET/cursor paging for the grid */ }
    public static Map<Id, Address> currentAddresses(List<HealthcareFacility> hcf, String actionType) { /* existing Billing/Mailing per facility */ }
}
```

### 6.5 `PRM_MassAddressRollbackBatch` (NEW)

> **Why** — A flagged/rejected job (or a bad address discovered post-update) must be revertible. **How** — `Database.Batchable<sObject>` that queries every record stamped with the job's `PRM_RequestId__c` and reverts Address values from `PRM_OldAddressSnapshot__c` (or `markAddressAsError` for inserts), then sets CMA `PRM_QCVerdict__c='Corrected'`. Per-object delete/revert chains — **no SOQL `UNION ALL`** (the documented pitfall in `PRM_Batch_Rollback_Strategies.md`). **Outcome** — targeted, audited reversal. **Replaces** — n/a.

### 6.6 Existing classes EXTENDED

| Class | New method | Body summary |
|---|---|---|
| `PRM_ExistingAccountService` | `resolveGroupByTaxIdAndNpi(taxId, npi)` | SOQL Account by `PRM_TaxId__c` + verify a HealthcareFacility with `PRM_NPI__c` exists; returns `{accountId, name}` or null |
| `PRM_AddressManagementService` | `bulkUpsertAddress(List<Address>, requestId)` | thin wrapper: stamp `PRM_RequestId__c`, `Database.upsert(list,false)`, log failures |
| `PRM_LocationQueryService` | (delegates to resolver) | keep façade; resolver owns the new query |
| `PRM_CaseManagerAssociationService` | `insertMassAddressCma(List<CMA>, iaId)` | bypasses the OS-payload router; reuses `insertCaseManagerAssociations(list, iaId)` |

### 6.7 Retired / not-needed OmniStudio (for the mass path only)

| Today (single-PL PDM) | Mass path |
|---|---|
| `PRM_PDMManualUpdate_English` address step | **not used** — standalone LWC instead |
| synchronous `PRM_PDMRecordsCreationHelper` address branch | replaced by the batch for mass; **single-PL path untouched** |
| per-keystroke OmniScript JSON re-serialization | eliminated (no OmniScript) |

---

## 7. Capitated-bundle handling (warn-only + child case)

Per the business decision (warn only), the batch does **not** auto-include bundle siblings:

1. `PRM_MassAddressLocationResolver` flags each HCF that has an active `PRM_HealthcareFacilityBundleAssociation__c` (sub-select) → `PRM_CaseManagerAssociation__c.PRM_BundleFlag__c = true`.
2. The grid shows these rows with a warning style; the user may deselect them.
3. `finish()` → `splitBundleChildCases(jobId)`: bundle-flagged CMA rows are re-parented (or cross-linked) to a **child Case per bundle** routed to **Provider Contracting** (reusing the `PRM_ManageHCFBundleAndAssParents` Case pattern), because the shared-billing-address invariant needs contracting sign-off.
4. A 1,284-location job touching 3 bundles = **1 parent QC case + 3 bundle child cases**, not 1,284 cases.

> **Decision D-3:** flag-only vs. hard-block bundle members. This design implements **flag-only** (matches the chosen UX). Switching to hard-block is a one-line predicate change in the resolver + a disabled checkbox in `prmMauReviewGrid`.

---

## 8. Routing to QC (mechanics)

All exist in-org; recommend **round-robin + a notification**:

| Mechanism | How | Note |
|---|---|---|
| Round-robin | `Case.PRM_IsRoundRobinLogic__c = true` (set in `createQcWorkItem`) | what PDM uses today |
| Queue + Owner | assign Case to the QC queue | shows in QC list views |
| Notification | publish `PRM_ExceptionLogEvent__e` on job channel / CustomNotification to QC group on `finish()` | heads-up that a large batch landed |

---

## 9. Sequencing & Phasing

```
Phase 0 — Data model (0.5–1 day)
  • PRM_MassAddressJob__c object + fields
  • PRM_CaseManagerAssociation__c new fields (QCVerdict, snapshots, RequestId, BundleFlag)
  • Address.PRM_RequestId__c
Phase 1 — Backend resolve + submit (3–4 days)
  • PRM_MassAddressLocationResolver, PRM_MassAddressUpdateService (resolve/standardize/submit/createQcWorkItem)
  • PRM_MassAddressUpdateController (read + submit)
  • extend PRM_ExistingAccountService, PRM_AddressManagementService
Phase 2 — Batch fan-out (3–4 days)
  • PRM_MassAddressUpdateBatch (+ reuse CMA builder), closeOutJob, splitBundleChildCases
  • PRM_MassAddressRollbackBatch
Phase 3 — Front end (5–6 days)
  • prmMassAddressUpdate container + 5 child bundles
  • wire reused datatable/modals/inputs/utils; brand-tokens theming
Phase 4 — QC review (2 days)
  • prmMauQcReview + controller QC verbs
Phase 5 — Test + UAT (4–5 days)
  • Apex tests (resolver, service, batch partial-success, rollback) ≥ 85%
  • Jest for the new LWC bundles; reused bundles already covered
  • UAT: 5-loc smoke → 1,284-loc real Tax ID → bundle case → error re-run
```

Total ≈ **18–23 dev-days** (1–2 senior devs, ~3 sprints), consistent with the SK estimation doc's async-refactor profile.

---

## 10. Testing Strategy

### 10.1 Apex
| Scenario | Expectation |
|---|---|
| Resolver: Tax ID + NPI returns N HCF; status filter excludes inactive/error | exact count, bundle flag set where assoc active |
| Resolver: `deselected` honored | excluded rows absent from QueryLocator |
| Service.submit: creates 1 Case + 1 IA + 1 CDM (`PRM_Address__c=true`) + 1 job; enqueues batch | ids returned; `Test.startTest/stopTest` runs batch |
| Batch.execute: 250 HCF over 2 chunks → Address Active + CMA per address | counts correct; `PRM_RequestId__c` stamped |
| Batch.execute: 1 row DML error | other rows succeed; 1 `PRM_ExceptionLog__c`; job error count = 1 |
| Bundle split: 3 bundles → 3 child cases | parent + 3 children; bundle CMA re-parented |
| Rollback: revert by RequestId | addresses restored from snapshot; CMA `Corrected` |
| QC verify/flag | verdict transitions; flag stores note |
| FLS / `with sharing` | non-privileged user blocked appropriately |

### 10.2 LWC (Jest)
- container step machine: 1→2→3→4→QC transitions; deselect tracking sends `deselectedFacilityIds`.
- `prmMauIdentifyStep`: address-validation modal accept → standardized values populate.
- `prmMauReviewGrid`: pre-selected all; uncheck → recap count decrements; bundle rows styled.
- `prmMauQcReview`: verify-selected → verdict chip flips; flag → note required.

### 10.3 Integration / manual
1. 5-location smoke (sandbox).
2. Largest QA Tax ID + NPI (~1,000+ PLs) → confirm batch completes, addresses Active, 1 QC case, N CMA rows.
3. Bundle Tax ID (e.g. Advocare `223537011`) → confirm child case to Provider Contracting.
4. Force a row error (lock an Address) → confirm error log + re-run by RequestId.
5. Performance: 200-scope chunks finish under batch limits; submit returns < 2 s.

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Service framework assumed by reference doc doesn't exist | **confirmed** | High if blindly followed | This design uses concrete existing classes; framework is optional seam (§3.6) |
| 1000s of CMA rows per job | Medium | Medium | batch scope 200; CMA insert partial-success; consider 1-row-per-address (not old+new) if volume doubles |
| Bundle invariant broken by partial update | Medium | High | flag + child case to Provider Contracting; D-3 toggle to hard-block |
| Address lock contention with concurrent PDM cases | Medium | Medium | per-row error capture + re-run by RequestId; don't fail batch |
| Precisely rate limits on bulk | Low | Medium | standardize the **one** new address once (not per-PL); per-PL addresses inherit it |
| Records Active before QC sees them | by design | Low | matches today's PDM activate-then-verify; rollback batch available |
| Already-matching rows re-written needlessly | Low | Low | resolver excludes addresses already equal to the new value |

---

## 12. Open Decisions (log)

| # | Question | Owner | Needed before |
|---|---|---|---|
| D-0 | Self-contained primitives (a, recommended) vs. seed `PRM_BaseService` framework (b) | Tech lead / Arch | Phase 1 |
| D-1 | Object name: reuse `PRM_CaseManagerAssociation__c` (yes — exists) — confirm `PRM_RequestType__c` stamp value e.g. `"Mass Billing Address Update"` | PDM ops | Phase 0 |
| D-2 | Track **old+new** CMA (2 rows/address) or **new only** (1 row) | QC + Compliance | Phase 0 |
| D-3 | Bundle members: flag-only (chosen) vs hard-block | Provider Contracting | Phase 1 |
| D-4 | QC notification: round-robin only, or + CustomNotification to QC group | PDM ops | Phase 4 |
| D-5 | Flagged-row workflow: whole case back to PDA, or targeted re-run by RequestId | QC | Phase 4 |
| D-6 | Bundle child-case owner queue (Provider Contracting API name) | Network Mgmt | Phase 2 |
| D-7 | Dedicated audit object beyond CMA + Field History? | Compliance | Phase 0 (default: no) |

---

## 13. Source-of-truth references (verified in repo)

**Reused Apex** (`force-app/main/default/classes/`):
`PRM_CaseManagerAssociationAddressBuilder.cls` (`createCMAForUpdatedAddressIds`), `PRM_CaseManagerAssociationService.cls` (`insertCaseManagerAssociations`), `PRM_CaseManagerAssociationBatch.cls` (batch pattern), `PRM_CMARecordTypeHelper.cls`, `PRM_AddressValidationService.cls`, `PRM_AddressManagementService.cls`, `PRM_LocationQueryService.cls`, `PRM_AddressPicklistService.cls`, `PRM_AddressSelector.cls`, `PRM_ExistingAccountService.cls`, `PRM_ExceptionLogger.cls`, `PRM_GlobalConstant.cls`, `PRM_HCFBundleAssociationBatch.cls` (pattern), `PRM_PractitionerActivationBatch.cls` (pattern).

**Reused object/fields**: `objects/PRM_CaseManagerAssociation__c/` (`PRM_Address__c`, `PRM_CaseManager__c`, `PRM_HealthcareFacility__c`, `PRM_RequestType__c`), `PRM_ExceptionLogEvent__e`.

**Reused DataRaptors** (`vlocity_export/DataRaptor/`):
`PRMDREAccountNpiTaxId`, `PRMDRExtractGroupNameBasedOnTINNPI`, `PRMDRLoadMailingAndBillingAdd`, `PRMDRLoadMailingBillingAddresses`, `PRMDREMailingBillingAddress`, `PRMDRCreateCaseCaseManagerBundleExist`, `PRMCreateCaseDatamanager`, `PRMCaseMgrCaseDataMgrPDM`.

**Reused IPs** (`vlocity_export/IntegrationProcedure/`):
`PRM_ManageHCFBundleAndAssociations`, `PRM_ManageHCFBundleAssParents` (bundle child-case pattern), `PRM_CheckAddressUpdated`.

**Reused LWC** (`force-app/main/default/lwc/`):
`prmEnhancedDatatable`, `prmGenericSearchInput`, `addressValidationModal`, `prmAddressUtils`, `prmGenericConfirmModal`, `prmNotesCapture`, `prmExceptionLoggerUtil`, `prmGenericPagination`; pattern refs `prmAddressGroupManager`, `prmAddressComparisonParForm`.

**Patterns referenced**: `PRM_HighVolume_Processing_SK_Estimation.md` (async), `UPHS_MASS_LOAD_SOLUTIONS.md` (staging + finish summary), `PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md` (bundle invariant), `PRM_Batch_Rollback_Strategies.md` (no SOQL UNION ALL).

---

## 14. Net-new component inventory (build list)

| # | Component | Type | Layer |
|---|---|---|---|
| 1 | `PRM_MassAddressJob__c` (+ fields) | Custom Object | data |
| 2 | `PRM_CaseManagerAssociation__c` new fields | Fields | data |
| 3 | `Address.PRM_RequestId__c` | Field | data |
| 4 | `PRM_MassAddressUpdateController` | Apex | controller |
| 5 | `PRM_MassAddressUpdateService` | Apex | orchestration |
| 6 | `PRM_MassAddressLocationResolver` | Apex | selector |
| 7 | `PRM_MassAddressUpdateBatch` | Apex Batch | async |
| 8 | `PRM_MassAddressRollbackBatch` | Apex Batch | async |
| 9 | `PRM_MassAddressDTO` | Apex (DTO bundle) | shared |
| 10 | `PRM_MassAddressUpdateServiceTest` / `…BatchTest` / `…ResolverTest` | Apex tests | test |
| 11 | `prmMassAddressUpdate` | LWC | container |
| 12 | `prmMauPath` | LWC | UI |
| 13 | `prmMauIdentifyStep` | LWC | UI |
| 14 | `prmMauReviewGrid` | LWC | UI |
| 15 | `prmMauConfirmStep` | LWC | UI |
| 16 | `prmMauProgress` | LWC | UI |
| 17 | `prmMauQcReview` | LWC | UI |
| 18 | EXTEND: `PRM_ExistingAccountService`, `PRM_AddressManagementService`, `PRM_LocationQueryService`, `PRM_CaseManagerAssociationService` | Apex | reuse-extend |

**End of document.**
