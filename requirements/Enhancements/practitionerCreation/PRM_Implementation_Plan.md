# PRM Practitioner Creation Form — Implementation Plan

> Build plan for re-platforming the **Practitioner Creation Form** (`PRM_PractitionerCreationContainer` v6 + sub-IPs) onto a layered, bulk-first Apex service architecture with a metadata-driven async framework.
>
> **Scope:** Practitioner Creation Form **only** — it is the **first/pilot** conversion. PAR Form and PDM Manual Update are out of scope here; they will reuse the shared foundation (EPIC B), async framework (EPIC C), selectors (EPIC D), and most services built here.
>
> **Sources of truth (grounded against):** `PRM_PractitionerCreation_Apex_Service_Flow.md` (call sequence + object impact), `PRM_Apex_Reference_Implementation.md` (foundation classes + orchestrator blueprint), `PRM_Service_JSON_Contracts.md` (payload + async contracts), `PRM_Apex_Migration_Plan_v2.md` (risks), live metadata under `force-app/main/default`.
>
> **Naming convention:** all Apex classes use the `PRM_` prefix (e.g. `PRM_CaseService`, `PRM_HealthcareFacilityCreationService`). Selectors as `PRM_*Selector`.
>
> ⚠️ Custom object / field API names below are grounded to the in-source `objects/` + `omniDataTransforms/` metadata where verified; any still marked *(inferred)* and the open object/field questions are confirmed **per service during EPIC E** (tracked in the TDD §12 Clarification Log).

---

## 1. Approach & principles

| Principle | What it means in the build |
|---|---|
| **Layered separation** | Orchestrator (transaction) → Services (one object family each) → Selectors (all SOQL) → Utilities. |
| **Bulk-first** | Every service method takes a collection and does **one DML per object type**. No per-record loops. |
| **Native transaction control** | `Database.setSavepoint()` + explicit `Database.rollback()` inside the orchestrator's `run()`. |
| **Validate-first** | `PractitionerCreationPayloadValidator.validate()` runs before any DML (fail-fast). |
| **Branch-aware** | The orchestrator splits on `PractitionerCreationType` — **IBC Professional Staff** (lean) vs **Delegated Credentialing** (full) — sequencing only the services each branch needs. |
| **Metadata-driven async** | Heavy network writes (`HealthcareFacilityNetwork`) are deferred to `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c`, dispatched per Custom Metadata (Queueable / Batch). |
| **Transport-agnostic** | The orchestrator implements `Callable` (`call('submit', args)` → `run(Map<String,Object>)`) — reusable from the IP wrapper / REST / tests. |

---

## 2. Practitioner Creation call sequence (target)

Grounded to `PRM_PractitionerCreationOrchestrator.run()` and `PRM_PractitionerCreation_Apex_Service_Flow.md`. The orchestrator owns the savepoint, validates, runs the shared head, branches on `PractitionerCreationType`, commits the CDM once, then (Delegated + `CaseManagerId`) enqueues async.

> All services implement `execute(Map<String,Object>) : Map<String,Object>` (input map = `flow` + `jsonInput` + upstream Ids). E-numbers map to §8.

```
savepoint → validate → parse →
 E1. PRM_CaseService                → Account · Case · IndividualApplication (= Case Manager)        [BOTH]
 E2. PRM_PractitionerService        → HealthcareProvider · HealthcareProviderNpi · Identifier · HealthcareProviderTaxonomy   [BOTH]

 ── IBC Professional Staff branch ──
 E5. PRM_LicenseService             → BusinessLicense
 E8. PRM_InfoCodeService (gated)    → PRM_InfoCodeAssignment__c

 ── Delegated Credentialing branch (adds) ──
 E3. PRM_GroupService               → Account(Vendor) · Identifier · HealthcareProviderNpi · HealthcareProvider
 E5. PRM_LicenseService             → BusinessLicense
 E6. PRM_EducationService           → PersonEducation
 E7. PRM_BoardCertificationService  → BoardCertification
 E8. PRM_InfoCodeService (gated)    → PRM_InfoCodeAssignment__c
 E9. PRM_FileService (gated)        → Identifier (Document) · ContentDocumentLink
 E10. PRM_ContactService            → ContactProfile
 E11. PRM_LanguageService (gated)   → PersonLanguage

 ── both branches converge (sync) ──
 E16. PRM_CaseDataManagerService    → PRM_CaseDataManager__c (single coalesced DML)
→ commit (or Database.rollback(sp) on any exception)

 ── async network offload (Delegated + CaseManagerId / new-location data) via EPIC C ──
 insert PRM_AsyncJob__c (ProcessName='Practitioner Creation', payload as ContentVersion file)
   → after-insert trigger → PRM_AsyncOrchestrator → child PRM_AsyncJobDetails__c → worker:
     E13. PRM_HealthcareFacilityCreationService  → Location · Address · HealthcareFacility · HealthcareProviderNpi (E12) · HealthcarePractitionerFacility
                                                   ↳ invokes E14 PRM_HPFService · E15 PRM_ProviderFeatureService (Assistive Aids)
     E17. PRM_HealthcareFacilityNetworkService   → HealthcareFacilityNetwork (RT PRM_FacilityNw · PRM_FacilityTx)
     E18. PRM_Level4RecordCreationService (batch) → HealthcareFacilityNetwork (RT PRM_FacilityPractitionerTxNw)
```

> **Targets:** worst-case **sync DML** is light (IBC ≈ a handful; Delegated head only) because the **locations / facility / network creation is offloaded to async** (E13–E15, E17–E18) on fresh governor budgets; **SOQL ≤ 40** per sync submission. Exact branch composition + grounded field maps: `Epic_E_Practitioner_Services.md` (E1–E8) / `…_Part2.md` (E9–E18).

### 2.1 Legacy IP/DR → target service map (grounded to metadata)

`PRM_PractitionerCreationContainer` **v6** (active) orchestrates 3 sub-IPs + `TryCatchBlock` + `Response`. Mapping of the real OmniStudio assets to target services:

| Legacy sub-IP (active version) | Legacy DataRaptors / Apex | Target service(s) |
|---|---|---|
| `PRM_PractitionerCreation` v3 (base / IBC) | `PRMDRCreateCaseCaseManager*`, `PRMDRPHCProviderHCProvider*`, `PRMDRPPractionerPracticeLocation`, `PRMDRPCreateInfoCodeAssignment`, `PRMDRCreateCDMForPractitioner`, `PRMDRPCDMCaseManagerLink`, `PRM_OmniUtils.titleCase`/`convertToListSobjects` | `PRM_CaseService`, `PRM_PractitionerService` (incl. Taxonomy), `PRM_InfoCodeService`, `PRM_CaseDataManagerService`, `PRM_FormSubUtility` |
| `PRM_DelegatedPractitionerCreation` v7 (Delegated) | `PRMDRCreateCaseCaseManager`, `PRMDRCreateIdentiferAndDocument`, `PRMDRExtractTaxonomyData`/`PRMDRTransDelegatedTaxonomy`/`PRMDRPHCPHCPTaxonomyAndBu*`, `PRMDRPCreateEducation`/`PRMDRTransformAddEducation`, `PRMDRPHCPNPIBoardCretIden*`, `PRMDRTransformDelegatedBu*`, `PRMPostGroupPractitionerC*`, `PRMDRPCreateInfoCodeAssignment`, CDM DRs, `PRM_PractitionerCreationValidator.validate` | `PRM_PractitionerService` (HCP+Taxonomy), `PRM_LicenseService`, `PRM_EducationService`, `PRM_BoardCertificationService`, `PRM_HealthcareProviderNpiService`, `PRM_GroupService`, `PRM_InfoCodeService`, `PRM_CaseDataManagerService`, `PractitionerCreationPayloadValidator` |
| `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` v2 + async network DRs | `PRMDRTransformPractitionerLocations`/`PRMDRPDelegatedPractionerPracticeLocations`, `PRMDRPFacilityPractitionerTxNw`, `PRMDRPostProviderFeatureAsstAids` (+ transforms), `PRMDRCreatePractitionerFacilityNetwork`/`PRMDRCreateHFNPractitionerNetworkRecords`, address/HCF DRs | `PRM_HealthcareFacilityCreationService` (async), `PRM_HPFService`, `PRM_ProviderFeatureService`, `PRM_HealthcareFacilityNetworkService` (async), `PRM_Level4RecordCreationService` (batch) |
| `PRMGetFeatureConfigSetting` (DR Turbo) | — | response `FeatureConfigSetting` |

> **CDM contention:** `PRMDRCreateCDMForPractitioner` / `PRMDRPCDMCaseManagerLink` run in **both** creation sub-IPs — the single `PRM_CaseDataManagerService.commit()` collapses that to one DML.
> **Case Manager:** there is no `PRM_Case_Manager__c` object — the **`IndividualApplication`** record is the Case Manager (`ctx.caseManagerId = IndividualApplication.Id`); the CDM links via `PRM_CaseDataManager__c.PRM_CaseManager__c → IndividualApplication`.
> **DataRaptor caveat:** DR→object field mappings are confirmed from the retrieved `omniDataTransforms` + `objects` metadata **per service during EPIC E** (tracked in the TDD §12 Clarification Log, CL-11).

---

## 3. Delivery phases (EPICs)

| EPIC | Theme | Output |
|---|---|---|
| **A — Environment** | Async objects, Custom Metadata | Deployable scaffolding |
| **B — Foundation** | `PRM_FormSubUtility` + abstract base classes (`PRM_ServiceBase`, `PRM_OrchestratorBase`) | Reusable scaffolding (shared by later flows) |
| **C — Async framework** | `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c`, Custom Metadata, trigger, `PRM_AsyncOrchestrator`, executors, LWC progress/retry, cleanup batch | Metadata-driven async network offload + monitoring |
| **D — Selectors** | 5 selectors (all SOQL) | Read layer |
| **E — Practitioner Creation services** | Shared + IBC + Delegated services + async processor | Business logic |
| **F — Orchestration** | Validator + branch-aware orchestrator + IP wrapper | Flow wired end-to-end |
| **G — Testing** | Unit, integration, performance, shadow-mode parity | Quality gates |

---

## 4. EPIC A — Environment

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| A1 · Async custom objects + metadata | Create `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobConfig__mdt` (fields per EPIC C); reuse existing `PRM_FailedRecordStaging__c`; add a `PRM Async Job` permission set | Objects deployable; one `PRM_AsyncJobConfig__mdt` row for `Practitioner Creation` | 1.0 |

> Object/field API names + DR→object field maps are confirmed from the in-source `objects/` + `omniDataTransforms/` metadata **per service during EPIC E** (definition of done); open object/field questions (PPL=HCPF, no HCPFN, NetworkMember scope) are tracked in the TDD §12 Clarification Log — no separate upfront schema spike.

---

## 5. EPIC B — Foundation

> Build once; reused by all flows. Estimates are engineer-days for design + code + unit tests.

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| B1 · `PRM_FormSubUtility` (High Volume utility) | Common utility/transformation class: `NameNormalize()` (replaces `PRM_OmniUtils.titleCase`), `toSObjectList()` (replaces `PRM_OmniUtils.convertToListSobjects`), + more as services need them | Unit-tested; methods parity-tested vs legacy `PRM_OmniUtils` | 1.0 |
| B2 · `PRM_ServiceBase` | Minimal abstract service base (mirrors `PRM_OrchestratorBase`) — `public abstract Map<String,Object> execute(Map<String,Object> params)`. **No `FlowContext`** — shared state (record Ids + context) flows in the `params` map and is returned in the response map | Concrete service implements `execute()` returning a `Map<String,Object>` | 0.5 |
| B3 · `PRM_OrchestratorBase` | Minimal abstract base — `public abstract Map<String,Object> run(Map<String,Object> params)` + shared `response`. Each concrete `run()` owns its savepoint, try/catch (validation vs error), and rollback; a thin `Callable.call()` adapter delegates to it | One abstract method; a concrete `run()` proves savepoint/rollback end-to-end | 0.5 |

> The form-specific **typed payload model** has moved to **EPIC F (F1)** — it's consumed by the validator/orchestrator, not shared scaffolding.

---

## 6. EPIC C — Async framework (network offload)

Flow: **Orchestrator inserts parent `PRM_AsyncJob__c` → after-insert trigger (+ helper) invokes `PRM_AsyncOrchestrator` → creates child `PRM_AsyncJobDetails__c` per Custom Metadata → `InvokeJob` (Queueable/Batch + Batch Size) → executor resolves the `PRM_ServiceBase` worker (via `PRM_ServiceClassName__c`) and calls `execute(params)` → on finish: status update + `FindNextJob` (chain next pending) → when all done: Custom Notification to the Case Manager (LWC) → End. On failure: status `Failed` → log failure (reuse `PRM_ExceptionLogger`) → staging record; retry is manual (LWC, uncapped). Old job records (+ JSON files) are purged by a monthly scheduled batch.**

> **Implementation-ready guide:** `Epic_C_Async_Framework.md` (full code, SLDS LWC mockup, and C5 build tasks).

> **Decision (CL-1, closed):** **not reusing** the existing `PRM_AsyncProcess__c` pattern — this builds the dedicated `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` framework. The existing pattern remains for its current roster-sync purpose. See the TDD §12 (CL-1) / §13 (G-1).

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| C1 · Objects & config | `PRM_AsyncJob__c` (parent): `PRM_CaseManager__c` · `PRM_ProcessName__c` · `PRM_Status__c`. `PRM_AsyncJobDetails__c` (child): `PRM_CaseManager__c` · `PRM_AsyncJob__c` (lookup) · `PRM_ProcessName__c` · `PRM_Mode__c` · `PRM_BatchSize__c` · `PRM_Status__c`. `PRM_AsyncJobConfig__mdt`: per `ProcessName` → `PRM_ProcessName__c`, `PRM_ServiceClassName__c`, `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Sequence__c`. **Reuse the existing `PRM_FailedRecordStaging__c`** as the DLQ (fields `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ErrorMessage__c`, `PRM_ExceptionLog__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_SourceFlow__c`, `PRM_CaseManager__c`) — no new staging object. `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` are **new** objects (Master-Detail child; `PRM_ProcessName__c` picklist; **no `PRM_RetryCount__c`** on the child — retry is manual/uncapped). Request/result JSON kept as a **ContentVersion file** on the job. **Authoritative object/field schema: `Epic_A_Environment_Setup.md`.** | Objects deployable; config records present | 1.5 |
| C2 · `PRM_AsyncJobTrigger` + helper (after insert) | After-insert trigger on `PRM_AsyncJob__c` → thin helper class → invokes `PRM_AsyncOrchestrator` (create child details from Custom Metadata, then dispatch). No logic in the trigger body | Trigger delegates to helper → orchestrator; child rows created with correct mode / sequence | 1.0 |
| C3 · `PRM_AsyncOrchestrator` | Central async controller. Methods: **`createDetails`** (create `PRM_AsyncJobDetails__c` based on `PRM_AsyncJobConfig__mdt`) · **`invokeJob`** (`System.enqueueJob()` / `Database.executeBatch(…, PRM_BatchSize__c)` by `PRM_Mode__c`) · **`findNextJob`** (chain the next pending child) · **`statusUpdate`** · **`retry`** (**manual**, from the LWC — re-enqueue `Failed` children, **uncapped**; no `MAX_RETRIES`) · **`jsonFileParser`** (read & parse the JSON file → payload) · **`logFailure`** (**reuse `PRM_ExceptionLogger`** → `PRM_FailedRecordStaging__c`) · **`notifyOnFinish`** (Custom Notification `PRM_AsyncJobNotification`) | `findNextJob`/`invokeJob` chaining verified; manual `retry` re-enqueues failed children; finish Custom Notification fires; failures staged | 4.0 |
| C4 · Async executors (reuse `PRM_ServiceBase`) | **No dedicated `PRM_AsyncProcessor` interface** — the worker is a `PRM_ServiceBase` subclass (EPIC B/E). `PRM_AsyncQueueable` / `PRM_AsyncBatch` resolve it (`Type.forName(PRM_ServiceClassName__c)` → `PRM_ServiceBase`), call `execute(params)` (params = `detailId`/`jobId`/`caseManagerId`/`processName`/`payload`), read `success`/`error` from the response map, finalize status, and call back `PRM_AsyncOrchestrator.findNextJob`; failures → `PRM_ExceptionLogger` + staging | Failed job → `PRM_Status__c = 'Failed'` + detail in staging (`PRM_ErrorMessage__c`) | 2.0 |
| C5 · LWC progress + retry component | `prmAsyncJobProgress` LWC on the **`IndividualApplication`** (Case Manager) record page: summary dashboard + per-child progress, surfaces errors, and a **Retry** button (re-invokes failed children via `PRM_AsyncOrchestrator.retry`); **loads on render + manual Refresh** (no streaming — finish alert via the Custom Notification). SLDS mockup + full build-task breakdown in `Epic_C_Async_Framework.md` §C5.1 | Progress + errors shown; Retry re-runs failed child and reflects new status after refresh | 2.5 |
| C6 · Scheduled cleanup batch | `PRM_AsyncJobCleanupBatch` (monthly-scheduled) deletes old `PRM_AsyncJob__c` + `PRM_AsyncJobDetails__c` + their JSON files once the **configurable threshold** (Apex constant `RETENTION_DAYS`, default 90) is reached | Records + JSON files older than threshold purged; threshold configurable without code change | 1.5 |

---

## 7. EPIC D — Selectors

All SOQL lives here — read-only, typed, bulk-safe.

| Task | Selector | Key methods (inferred) | Est |
|---|---|---|---|
| D1 | `PRM_CaseSelector` | `getCDMByCaseManager(Id)` · `getCaseById(Id)` | 0.5 |
| D2 | `PRM_PractitionerSelector` *(existing `PractitionerDetailsSelector` — reuse/extend)* | `getByNPI(Set<String>)` · `getProviderById(Id)` | 0.5 |
| D3 | `PRM_AddressSelector` *(EXISTS — reuse/extend)* | `getExistingByFacilityIds(Set<Id>)` · `getExistingByNPISet(Set<String>)` · `getByIds(Set<Id>)` | 0.5 |
| D4 | `PRM_FacilitySelector` | `getAffiliationsByFacility(Set<Id>, Id practitionerId)` · `getPrimaryPracFacilities(...)` | 1.0 |
| D5 | `PRM_TaxonomySelector` | `getTaxonomyRefs(Set<String>)` | 0.5 |

**Acceptance (all):** read-only, bulk-safe, typed lists; covered by selector tests.

---

## 8. EPIC E — Practitioner Creation services (build in call order)

Every service **extends `PRM_ServiceBase`** and implements **`execute(Map<String,Object>) : Map<String,Object>`** — the input map carries **`flow`** + **`jsonInput`** (business payload as JSON string) plus any upstream record Ids from earlier services. Each service builds records in memory and **does its own DML — one bulk insert/update per object type** (FK/dependency order; back-link updates where needed); reads go through the EPIC D selectors; formula logic (record types via cached describe, dates, gating) is computed in-service. **Grounded field maps + active IP/DR mappings per service:** `Epic_E_Practitioner_Services.md` (E1–E8) and `Epic_E_Practitioner_Services_Part2.md` (E9–E18).

| Task | Service | Branch | Writes | Est |
|---|---|---|---|---|
| E1 | `PRM_CaseService` | BOTH | Account · Case · IndividualApplication (= Case Manager) — circular FK: insert + 2 back-link updates | 2.0 |
| E2 | `PRM_PractitionerService` | BOTH | HealthcareProvider · HealthcareProviderNpi · Identifier · **HealthcareProviderTaxonomy** *(E4 merged in)* | 2.5 |
| E3 | `PRM_GroupService` | DEL | Account(Vendor) · Identifier · HealthcareProviderNpi · HealthcareProvider *(`PRMPostGroupPractitionerCreation`)* | 1.5 |
| ~~E4~~ | ~~`PRM_TaxonomyService`~~ | — | **merged into E2** (fused HCP+Taxonomy+License DR) | — |
| E5 | `PRM_LicenseService` | BOTH | BusinessLicense *(unified `businessLicenses[]`; DEA/CDS + SBRD)* | 0.5 |
| E6 | `PRM_EducationService` | DEL | PersonEducation | 0.5 |
| E7 | `PRM_BoardCertificationService` | DEL | BoardCertification *(upsert by `BoardName`; runs after E2)* | 0.5 |
| E8 | `PRM_InfoCodeService` | BOTH | `PRM_InfoCodeAssignment__c` | 1.5 |
| E9 | `PRM_FileService` | DEL | Identifier (Document RT) · ContentDocumentLink | 1.0 |
| E10 | `PRM_ContactService` | DEL | **ContactProfile** *(not Contact)* | 1.0 |
| E11 | `PRM_LanguageService` | DEL | PersonLanguage | 0.5 |
| E12 | `PRM_HealthcareProviderNpiService` | reusable | HealthcareProviderNpi *(create/update; reuse `PRM_OmniUtils.updateExistignHCPNPI`)* | 1.0 |
| E13 | `PRM_HealthcareFacilityCreationService` ⚡ *(async)* | DEL | Location · Address · HealthcareFacility · HealthcareProviderNpi (E12) · HealthcarePractitionerFacility — invokes **E14** + **E15** | 3.0 |
| E14 | `PRM_HPFService` | DEL | HealthcarePractitionerFacility *(RT PractitionerLocationAffiliation / PractitionerPracticeAffiliation)* | 1.5 |
| E15 | `PRM_ProviderFeatureService` | DEL | `PRM_ProviderFeature__c` *(Assistive Aids only; RT `PRM_AssistiveAid`; create + update)* | 1.0 |
| E16 | `PRM_CaseDataManagerService` | BOTH | `PRM_CaseDataManager__c` *(single coalesced write; boolean presence flags)* | 1.5 |
| E17 | `PRM_HealthcareFacilityNetworkService` ⚡ *(async)* | DEL | HealthcareFacilityNetwork *(RT `PRM_FacilityNw` + `PRM_FacilityTx`)* | 1.5 |
| E18 | `PRM_Level4RecordCreationService` ⚡ *(batch)* | DEL | HealthcareFacilityNetwork *(RT `PRM_FacilityPractitionerTxNw` — Practitioner × PracticeLocation × Taxonomy × Role × Network)* | 2.0 |

⚡ = high-leverage / load-test priority · *(async)* = EPIC C `PRM_ServiceBase` worker · *(batch)* = `Database.Batchable`.

> **IBC vs Delegated:** the **IBC** branch uses E1, E2, E5, E8, E16 (links to existing facilities; no async). The **Delegated** branch adds E3, E6, E7, E9–E15 and the async network services **E17 / E18** (locations/facility/network sub-block E13–E15, E17–E18 only when `CaseManagerId` / new-location data is present).
>
> **Removed vs prior plan:** `PRM_TaxonomyService` (E4, merged into E2) and `PRM_ExistingPrimaryPracticeService` (removed). `PRM_AddressService` is no longer a sync service — address/facility creation is the **async `PRM_HealthcareFacilityCreationService` (E13)**.

---

## 9. EPIC F — Orchestration

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| F1 · Typed payload model (Practitioner Creation) | `BasePayload`, `CaseInfo`, `PractitionerInfo`, `GroupPayload`, `TaxonomyPayload`, `LicensePayload`, `EducationPayload`, `BoardCertPayload`, `InfoCodePayload`, `ContactProfilePayload`, `LanguagePayload`, `FilePayload`, `LocationPayload`, `AddressContext`, `ProviderFeaturePayload` + `PractitionerCreationPayload.fromMap()` / `isIBC()` / `isDelegated()` / `hasCaseManagerId()` / `hasFile()` | OmniScript JSON deserializes losslessly; round-trip test | 3.0 |
| F2 · `PractitionerCreationPayloadValidator` | IBC vs Delegated rules: required fields, NPI format, taxonomy/license cardinality, location cardinality, effective dates; throws `PRM_ValidationException` (replaces `PRM_PractitionerCreationValidator.validate`) | Bad payloads fail before any DML; categorized field errors per branch | 2.0 |
| F3 · `PRM_PractitionerCreationOrchestrator` (+ Callable adapter) | `call('submit', args)` → `run(Map<String,Object>)`; savepoint → validate → parse → E1/E2 → **branch on `PractitionerCreationType`** (IBC vs Delegated) → E16 commit → insert `PRM_AsyncJob__c` (`Practitioner Creation`) when Delegated + `hasCaseManagerId()` & `hasAddressesForNetwork()`; sets response (`PractitionerScreenRecordIds`, `FeatureConfigSetting`, `AsyncJobId?`); `Database.rollback(sp)` on any exception | E2E create for IBC and Delegated paths; single CDM write; async job inserted on Delegated; rollback on injected failure | 3.0 |
| F4 · IP wrapper config (`PRM_RecordCreationIPWrapper`) | Re-point the Practitioner Creation IP Remote Action to `remoteClass = PRM_PractitionerCreationOrchestrator`, `remoteMethod = 'submit'` (hard cutover; rollback = re-point to legacy); preserve the request/response contract | Byte-for-byte response parity with the legacy contract | 0.5 |

---

## 10. EPIC G — Testing

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| G1 · Unit tests ≥ 85% | All services + foundation (per the §8 definition of done) | ≥ 85% coverage; assertions per template | 4.5 |
| G2 · Integration tests | IBC happy path · Delegated happy path (with & without `CaseManagerId`) · validation failure (both branches) · partial-DML rollback · async completion (`PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` → `Completed`) | All scenarios pass; branch DML within targets | 3.0 |
| G3 · Performance regression | `Test.startTest()/stopTest()` capture per submission | IBC DML ≤ 12 · Delegated DML ≤ 28 · SOQL ≤ 40 · CPU < 5000 ms · heap < 2 MB | 1.0 |
| G4 · Shadow-mode parity harness | Run the new orchestrator beside the legacy IP; compare created records field-by-field into an audit object | Field-by-field parity recorded for 2 weeks (both branches) | 2.0 |

---

## 11. Dependency / sequencing

```
A Schema/env ──► B Foundation ──► C Async framework ──► D Selectors ──► E Services ──► F Orchestration ──► G Testing
```

- **Confirm DR field maps per service (EPIC E DoD)** — no `*__c` should remain "inferred" before a service's tests.
- Build foundation (B) + async framework (C) + selectors (D) before services; services before the orchestrator.
- `PRM_HealthcareFacilityCreationService`, `PRM_HealthcareFacilityNetworkService`, `PRM_Level4RecordCreationService` are the highest-risk / load-test priorities (Delegated async locations + network).
- The flow ends with shadow-mode parity (G4) for **both** branches before cutover (re-pointing the IP wrapper).

---

## 12. Effort summary

| EPIC | Est (engineer-days) |
|---|---|
| A — Environment | 1.0 |
| B — Foundation | 2.0 |
| C — Async framework | 12.5 |
| D — Selectors (selector reuse) | 3.0 |
| E — Practitioner Creation services (E1–E18) | 23.0 |
| F — Orchestration (incl. payload model) | 8.5 |
| G — Testing | 10.5 |
| **Practitioner Creation total** | **~60.5 engineer-days** *(pending where the removed base classes live — see TDD CL-13)* |

> Estimates are indicative for planning; refine after a thin POC (`PRM_CaseDataManagerService` + a minimal branch-aware orchestrator proving savepoint/rollback end-to-end). EPICs **B, C, D are shared foundations** — once built here, PAR Form and PDM reuse them (and most E services), so their incremental cost is far lower.

---

## 13. Appendix — Async framework classes (data model)

| Class / Object | Surface |
|---|---|
| `PRM_AsyncJob__c` | parent job — `PRM_CaseManager__c`, `PRM_ProcessName__c`, `PRM_Status__c` |
| `PRM_AsyncJobDetails__c` | child unit — `PRM_CaseManager__c`, `PRM_AsyncJob__c` (lookup), `PRM_ProcessName__c`, `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Status__c` (no `PRM_RetryCount__c` — retry is manual/uncapped) |
| `PRM_FailedRecordStaging__c` *(existing — reused)* | DLQ written by `logFailure` (audit + retry source); fields `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ErrorMessage__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_SourceFlow__c`, `PRM_CaseManager__c` |
| `PRM_AsyncJobConfig__mdt` | per `ProcessName` → `PRM_ProcessName__c`, `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Sequence__c` |
| `PRM_AsyncJobTrigger` + helper (after insert) | trigger delegates to helper → invokes `PRM_AsyncOrchestrator` |
| `PRM_AsyncOrchestrator` | `createDetails` · `invokeJob` · `findNextJob` · `statusUpdate` · `retry` (manual, uncapped) · `jsonFileParser` · `logFailure` (reuse `PRM_ExceptionLogger` → staging) · `notifyOnFinish` (Custom Notification) |
| Async worker | a `PRM_ServiceBase` subclass resolved via `PRM_ServiceClassName__c` — `execute(params)` (no dedicated `PRM_AsyncProcessor` interface) |
| `PRM_AsyncQueueable` / `PRM_AsyncBatch` | resolve processor from config → delegate → finalize status → `findNextJob` chain |
| `prmAsyncJobProgress` (LWC) | on Case Manager — progress, errors, Retry button |
| `PRM_AsyncJobCleanupBatch` | monthly-scheduled purge of old jobs + details + JSON files past threshold |
