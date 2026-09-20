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

> **🔄 Revision — async-only execution model (ratified; supersedes the synchronous-orchestrator design below):** the form runs **fully asynchronously**. The IP wrapper **validates (sync), inserts `PRM_AsyncJob__c`, and returns immediately** — **no synchronous orchestrator** and no whole-submission savepoint/rollback. All services run inside **five concrete batch classes** — `PractitionerBatch`, `PracticeLocationAndGroupBatch`, `GroupRelatedBatch`, `PLRelatedBatch`, `Level4RecordCreationBatch` — sequenced by `PRM_AsyncOrchestrator` from `PRM_AsyncJobConfig__mdt` (`PRM_Sequence__c`), each branching **IBC vs Delegated internally** and wrapping its own E-services. The chain **halts on first failure** (later batches don't run; completed records remain; manual retry resumes from the failed batch). New object **`PRM_AsyncJobRecords__c`** tracks the multiple Case Managers per run; `PRM_AsyncJob__c.PRM_CaseManager__c` is **removed**; `PRM_AsyncJobConfig__mdt.PRM_ServiceClassName__c` now holds the **batch class name**. **EPIC F shrinks** to validator + thin insert wrapper; **EPIC E** is reorganized under the five batches (E1–E18 unchanged but now invoked inside batches — **mapping pending, see TDD CL-15**). Authoritative schema: `Epic_A_Environment_Setup.md`. The §2 call sequence and §8/§9 tables below retain the original sync narrative for history — read them through this revision.

---

## 1. Approach & principles

| Principle | What it means in the build *(async-only revision)* |
|---|---|
| **Layered separation** | Async engine (sequences steps) → Batch classes (per-step transaction + branching) → Services (one object family each) → Selectors (all SOQL) → Utilities. |
| **Bulk-first** | Every service method takes a collection and does **one DML per object type**. No per-record loops. |
| **Per-batch transaction control** | Each batch class owns its step's transaction; **no whole-submission savepoint/rollback**. Reliability comes from the **halt-on-failure chain** + durable, resumable retry. |
| **Validate-first** | `PractitionerCreationPayloadValidator.validate()` runs **synchronously, before the job is inserted** (fail-fast; nothing enqueued on invalid payloads). |
| **Branch-aware (inside batches)** | Each batch splits on `PractitionerCreationType` — **IBC Professional Staff** (lean) vs **Delegated Credentialing** (full) — running only the services that branch needs. |
| **Metadata-driven async (everything)** | All record creation is deferred to `PRM_AsyncJob__c` → `PRM_AsyncJobDetails__c` steps, each dispatched as a **named batch class** per Custom Metadata (`PRM_Sequence__c` order). |
| **Fire-and-return transport** | The IP wrapper validates, inserts `PRM_AsyncJob__c` (+ payload file + `PRM_AsyncJobRecords__c` per Case Manager), and returns immediately — **no `Callable` orchestrator**. |

---

## 2. Practitioner Creation call sequence (target)

Grounded to `PRM_PractitionerCreation_Apex_Service_Flow.md`. Intake is synchronous (validate → Case Manager creation → insert job); all other creation is async, sequenced by `PRM_AsyncOrchestrator` across the five batch classes (halt-on-failure). Batch ↔ service mapping: §8.1. All services implement `execute(Map<String,Object>) : Map<String,Object>` (input map = `flow` + `jsonInput` + upstream Ids). E-numbers map to §8.

```
INTAKE (sync, IP wrapper) — form submit OR CSV upload (N practitioners)
  validate → E1 PRM_CaseService (bulk; applications[] array) → Account · Case · IndividualApplication (= Case Manager), one per practitioner
  → insert PRM_AsyncJob__c (ProcessName='Practitioner Creation', JSON as ContentVersion file)
  → insert PRM_AsyncJobRecords__c (one per practitioner) → return {success, AsyncJobId}

ASYNC (PRM_AsyncOrchestrator, PRM_Sequence__c order, halt-on-failure; each batch branches IBC/Delegated)
  1. PractitionerBatch              → E2 Practitioner · E5 License · E6 Education · E7 BoardCert
                                       · E8 InfoCode · E10 Contact · E11 Language · E16 CDM
  2. PracticeLocationAndGroupBatch  → E3 Group · E13 FacilityCreation · E9 File · E12 NPI
  3. GroupRelatedBatch              → TBD (CL-15)
  4. PLRelatedBatch                 → E14 HPF (sub-service PractionerPracticeLocationService) · E15 ProviderFeature · E17 FacilityNetwork
  5. Level4RecordCreationBatch      → E18 Level4
  → all Completed → notifyOnFinish · any Failed → DLQ + chain halts (manual retry resumes)
```

> **Targets:** intake stays light (validation + Case Manager creation only); all heavy work runs in batches on fresh governor budgets. Per-batch governor budgets to validate in the POC (CL-10). Grounded field maps (organized by batch): `Epic_E_Practitioner_Services.md` (Part 1 — PractitionerBatch) / `…_Part2.md` (Part 2 — PracticeLocationAndGroupBatch) / `…_Part3.md` (Part 3 — PLRelatedBatch + Level4).

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
| **A — Environment** | Async objects (`PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c`), Custom Metadata | Deployable scaffolding |
| **B — Foundation** | `PRM_FormSubUtility` (`NameNormalize`) + abstract base `PRM_ServiceBase` *(no `PRM_OrchestratorBase` — async-only)* | Reusable scaffolding (shared by later flows) |
| **C — Async framework** | The three async objects, Custom Metadata, trigger, `PRM_AsyncOrchestrator` (invokes the **named batch classes** directly), LWC progress/retry, cleanup batch | Metadata-driven async execution + monitoring |
| **D — Selectors** | 5 selectors (all SOQL) | Read layer |
| **E — Practitioner Creation services + batch classes** | E1–E18 services **grouped under the five batch classes** (`PractitionerBatch`, `PracticeLocationAndGroupBatch`, `GroupRelatedBatch`, `PLRelatedBatch`, `Level4RecordCreationBatch`); each branches IBC vs Delegated internally | Business logic + async execution units |
| **F — Validation & intake** *(shrunk)* | `PractitionerCreationPayloadValidator` + the thin IP wrapper that validates and **inserts `PRM_AsyncJob__c`** (no sync orchestrator/`Callable`) | Intake wired end-to-end |
| **G — Testing** | Unit, integration, performance, shadow-mode parity | Quality gates |

---

## 4. EPIC A — Environment

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| A1 · Async custom objects + metadata | Create `PRM_AsyncJob__c` (no `PRM_CaseManager__c`), `PRM_AsyncJobDetails__c`, **`PRM_AsyncJobRecords__c`** (per–Case-Manager, M-D to the job), `PRM_AsyncJobConfig__mdt` (`PRM_ServiceClassName__c` = batch class name); reuse existing `PRM_FailedRecordStaging__c`; add a `PRM Async Job` permission set | Objects deployable; one `PRM_AsyncJobConfig__mdt` row **per batch step** for `Practitioner Creation` | 1.0 |

> Object/field API names + DR→object field maps are confirmed from the in-source `objects/` + `omniDataTransforms/` metadata **per service during EPIC E** (definition of done); open object/field questions (PPL=HCPF, no HCPFN, NetworkMember scope) are tracked in the TDD §12 Clarification Log — no separate upfront schema spike.

---

## 5. EPIC B — Foundation

> Build once; reused by all flows. Estimates are engineer-days for design + code + unit tests.

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| B1 · `PRM_FormSubUtility` (High Volume utility) | Common utility class: `NameNormalize()` (replaces `PRM_OmniUtils.titleCase`) + more helpers as services need them *(`toSObjectList` removed for now)* | Unit-tested; `NameNormalize` parity-tested vs legacy `PRM_OmniUtils.titleCase` | 0.5 |
| B2 · `PRM_ServiceBase` | Minimal abstract service **shell** — `public abstract Map<String,Object> execute(Map<String,Object> params)` + `protected response`. **No `FlowContext`** — shared state flows in the `params` map and returns in the response map; response-key contract defined later (C/E/F) | Concrete service implements `execute()` returning a `Map<String,Object>` | 0.5 |
| ~~B3 · `PRM_OrchestratorBase`~~ | **Removed** — async-only pilot has no synchronous orchestrator; the intake wrapper (F3) is a plain class, not a `Callable` orchestrator | — | — |

> The form-specific **typed payload model** has moved to **EPIC F (F1)** — it's consumed by the validator/orchestrator, not shared scaffolding.

---

## 6. EPIC C — Async framework (network offload)

Flow: **IP wrapper inserts parent `PRM_AsyncJob__c` → after-insert trigger (+ helper) invokes `PRM_AsyncOrchestrator` → creates child `PRM_AsyncJobDetails__c` per Custom Metadata (one per batch step) → `InvokeJob` resolves the named batch class (`Type.forName(PRM_ServiceClassName__c)`) and runs `Database.executeBatch(…, PRM_BatchSize__c)` → batch wraps its EPIC E service(s), branches IBC/Delegated, and in `finish()` calls `FindNextJob` (next step in `PRM_Sequence__c` order) → when all Completed: Custom Notification to the Case Manager (LWC) → End. On failure: status `Failed` → log failure (reuse `PRM_ExceptionLogger`) → staging record → chain HALTS; retry is manual (LWC, uncapped, resumes from the failed step). Old job records (+ JSON files) are purged by a monthly scheduled batch.**

> **Implementation-ready guide:** `Epic_C_Async_Framework.md` (full code, SLDS LWC mockup, and C5 build tasks).

> **Decision (CL-1, closed):** **not reusing** the existing `PRM_AsyncProcess__c` pattern — this builds the dedicated `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` framework. The existing pattern remains for its current roster-sync purpose. See the TDD §12 (CL-1) / §13 (G-1).

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| C1 · Objects & config | The three async objects + `PRM_AsyncJobConfig__mdt` (per Epic A). `PRM_AsyncJob__c` (parent, **no `PRM_CaseManager__c`**), `PRM_AsyncJobDetails__c` (per batch step), `PRM_AsyncJobRecords__c` (per practitioner/Case Manager). Config `PRM_ServiceClassName__c` = **batch class** name. **Reuse the existing `PRM_FailedRecordStaging__c`** as the DLQ (+ new `PRM_AsyncJobDetails__c` lookup). Request/result JSON kept as a **ContentVersion file** on the job. **Authoritative object/field schema: `Epic_A_Environment_Setup.md`.** | Objects deployable; config records present (one per batch step) | 1.5 |
| C2 · `PRM_AsyncJobTrigger` + helper (after insert) | After-insert trigger on `PRM_AsyncJob__c` → thin helper class → invokes `PRM_AsyncOrchestrator` (create child details from Custom Metadata, then dispatch). No logic in the trigger body | Trigger delegates to helper → orchestrator; child rows created with correct mode / sequence | 1.0 |
| C3 · `PRM_AsyncOrchestrator` | Central async controller. Methods: **`createDetails`** (one `PRM_AsyncJobDetails__c` per `PRM_AsyncJobConfig__mdt` row) · **`invokeJob`** (`Database.executeBatch(Type.forName(PRM_ServiceClassName__c), PRM_BatchSize__c)` — the **named batch class**) · **`findNextJob`** (next step by `PRM_Sequence__c`; **halts on a `Failed` step**) · **`statusUpdate`** · **`retry`** (**manual**, from the LWC — re-run the failed step, resume chain, **uncapped**) · **`jsonFileParser`** · **`logFailure`** (reuse `PRM_ExceptionLogger` → `PRM_FailedRecordStaging__c`) · **`notifyOnFinish`** (Custom Notification `PRM_AsyncJobNotification`) | chaining verified; halt-on-failure; manual `retry` resumes; finish notification fires; failures staged | 4.0 |
| C4 · The five batch classes (EPIC E) | `PractitionerBatch`, `PracticeLocationAndGroupBatch`, `GroupRelatedBatch`, `PLRelatedBatch`, `Level4RecordCreationBatch` — each `Database.Batchable`, resolves the payload (`jsonFileParser`), branches IBC/Delegated, calls its EPIC E service(s) `execute(params)`, **aggregates Case Manager Association requests and invokes the common `PRM_CMAService` once (same transaction)**, finalizes its `PRM_AsyncJobDetails__c` status, and calls `PRM_AsyncOrchestrator.findNextJob` in `finish()`. *(Replaces the generic `PRM_AsyncQueueable`/`PRM_AsyncBatch` worker pattern.)* Built in EPIC E; C4 defines the contract | Failed step → `PRM_Status__c='Failed'` + DLQ row + chain halts | 2.0 |
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

Every service **extends `PRM_ServiceBase`** and implements **`execute(Map<String,Object>) : Map<String,Object>`** — the input map carries **`flow`** + **`jsonInput`** (business payload as JSON string) plus any upstream record Ids from earlier services. Each service builds records in memory and **does its own DML — one bulk insert/update per object type** (FK/dependency order; back-link updates where needed); reads go through the EPIC D selectors; formula logic (record types via cached describe, dates, gating) is computed in-service. **Grounded field maps + active IP/DR mappings per service (organized by batch for sequential build):** `Epic_E_Practitioner_Services.md` (Part 1 — intake E1 + PractitionerBatch: E2·E5·E6·E7·E8·E10·E11·E16), `Epic_E_Practitioner_Services_Part2.md` (Part 2 — PracticeLocationAndGroupBatch: E3·E13·E9·E12), and `Epic_E_Practitioner_Services_Part3.md` (Part 3 — PLRelatedBatch E14·E15·E17 + Level4RecordCreationBatch E18; GroupRelatedBatch TBD).

> **🔄 Async-only revision — services run inside batch classes (except E1):** the E-services below are unchanged in what they build, but they are no longer sequenced by a synchronous orchestrator. **E1 `PRM_CaseService` runs synchronously at intake** (the "Case Manager Service") — the wrapper calls it (one Case Manager/`IndividualApplication` **per practitioner**) and seeds `PRM_AsyncJobRecords__c` with the returned Ids **before** inserting the job. **E2–E18** are invoked **inside the five concrete batch classes**, which `PRM_AsyncOrchestrator` runs in `PRM_AsyncJobConfig__mdt.PRM_Sequence__c` order with **halt-on-failure**; each branches **IBC vs Delegated internally**. Intake also supports **form submission and CSV upload (multiple practitioners per submission)**.

#### 8.1 Batch ↔ service mapping (CL-15)

Sequence: **`PractitionerBatch` → `PracticeLocationAndGroupBatch` → `GroupRelatedBatch` → `PLRelatedBatch` → `Level4RecordCreationBatch`**.

| Seq | Batch class | Hosted services (E#) |
|---|---|---|
| — | *(sync intake)* | **E1** `PRM_CaseService` (Case Manager Service — one per practitioner) |
| 1 | `PractitionerBatch` | **E2** `PRM_PractitionerService` · **E5** `PRM_LicenseService` · **E6** `PRM_EducationService` · **E7** `PRM_BoardCertificationService` · **E8** `PRM_InfoCodeService` · **E10** `PRM_ContactService` · **E11** `PRM_LanguageService` · **E16** `PRM_CaseDataManagerService` |
| 2 | `PracticeLocationAndGroupBatch` | **E3** `PRM_GroupService` (GroupCreationService) · **E13** `PRM_HealthcareFacilityCreationService` · **E9** `PRM_FileService` (DocumentAssociation) · **E12** `PRM_HealthcareProviderNpiService` |
| 3 | `GroupRelatedBatch` | **TBD** (still a separate batch; services not yet assigned) |
| 4 | `PLRelatedBatch` | **E14** `PRM_HPFService` (invokes `PractionerPracticeLocationService` as a sub-service → `HealthcarePractitionerFacility`) · **E15** `PRM_ProviderFeatureService` · **E17** `PRM_HealthcareFacilityNetworkService` |
| 5 | `Level4RecordCreationBatch` | **E18** `PRM_Level4RecordCreationService` |

> **Residual opens (CL-15):** `GroupRelatedBatch` service list is **TBD**. *(`PractionerPracticeLocationService` resolved: it's a sub-service of E14 `PRM_HPFService`, writing `HealthcarePractitionerFacility` per CL-2.)*

| Task | Service | Branch | Writes | Est |
|---|---|---|---|---|
| E1 | `PRM_CaseService` *(sync intake — Case Manager Service, BULK)* | BOTH | Account · Case · IndividualApplication (= Case Manager) — circular FK: insert + 2 back-link updates; **bulk: one call per submission processing an `applications[]` array (one Case Manager per practitioner), one bulk DML per object type**; runs at intake (not in a batch) | 2.5 |
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
| **E19 (CMA)** | `PRM_CMAService` *(common — invoked by the relevant batches)* | BOTH | `PRM_CaseManagerAssociation__c` *(junction: created/updated records → Case Manager; 14 record types; idempotent **pre‑check**, no new field)* | 1.0 |

⚡ = high-leverage / load-test priority · *(async)* = EPIC C `PRM_ServiceBase` worker · *(batch)* = `Database.Batchable`.

> **CMA (common service — `PRM_CMAService`).** After a batch creates/updates its records, it **aggregates the Case Manager Association requests for its chunk and calls `PRM_CMAService` once, in the same transaction** (a CMA failure fails the step → DLQ/retry). It writes `PRM_CaseManagerAssociation__c` (one row per "primary" record per Case Manager, with contextual lookups) by RecordType, deduped via a **pre‑check** (`PRM_CaseManager__c` + RecordType + primary lookup). The RT→lookup map + a cached `recordTypeId(...)` helper live on **`PRM_FormSubUtility`**. CMA covers a **subset** of objects (those with a CMA record type) — Education/BoardCert/InfoCode/NPI/File/Contact/Language have none. Full spec + grounded mapping: **`epic-e-services/E19_PRM_CMAService.md`**.

> **IBC vs Delegated:** the **IBC** branch uses E1, E2, E5, E8, E16 (links to existing facilities; no async). The **Delegated** branch adds E3, E6, E7, E9–E15 and the async network services **E17 / E18** (locations/facility/network sub-block E13–E15, E17–E18 only when `CaseManagerId` / new-location data is present).
>
> **Removed vs prior plan:** `PRM_TaxonomyService` (E4, merged into E2) and `PRM_ExistingPrimaryPracticeService` (removed). `PRM_AddressService` is no longer a sync service — address/facility creation is the **async `PRM_HealthcareFacilityCreationService` (E13)**.

---

## 9. EPIC F — Validation & intake *(shrunk — async-only revision)*

> **🔄 Revised:** with no synchronous orchestrator, EPIC F is just the **typed payload model + validator + a thin intake wrapper** that: validates synchronously → **calls `PRM_CaseService` (sync)** to create one Case Manager (`IndividualApplication`) per practitioner → **inserts `PRM_AsyncJob__c`** (+ the submission JSON ContentVersion file) **+ one `PRM_AsyncJobRecords__c` per practitioner** (seeded with the returned Case Manager Ids) → returns. Intake accepts a **form submission or CSV upload (multiple practitioners per submission)**. The former **F3 (`PRM_PractitionerCreationOrchestrator` + `Callable`, savepoint/branch/commit) is removed** — branching and execution now live inside the EPIC E batch classes (driven by EPIC C). Effort drops accordingly.

| Task | Deliverables | Acceptance | Est |
|---|---|---|---|
| F1 · Typed payload model (Practitioner Creation) | `BasePayload`, `CaseInfo`, `PractitionerInfo`, `GroupPayload`, `TaxonomyPayload`, `LicensePayload`, `EducationPayload`, `BoardCertPayload`, `InfoCodePayload`, `ContactProfilePayload`, `LanguagePayload`, `FilePayload`, `LocationPayload`, `AddressContext`, `ProviderFeaturePayload` + `PractitionerCreationPayload.fromMap()` / `isIBC()` / `isDelegated()` / `hasCaseManagerId()` / `hasFile()` | OmniScript JSON deserializes losslessly; round-trip test | 3.0 |
| F2 · `PractitionerCreationPayloadValidator` | IBC vs Delegated rules: required fields, NPI format, taxonomy/license cardinality, location cardinality, effective dates; throws `PRM_ValidationException` (replaces `PRM_PractitionerCreationValidator.validate`). **Runs synchronously, pre-enqueue** | Bad payloads fail **before the job is inserted** (nothing enqueued); categorized field errors per branch | 2.0 |
| F3 · Intake wrapper (`PRM_RecordCreationIPWrapper`) | `call('submit', args)` → validate (F2) → on success: **call `PRM_CaseService` (sync)** for each practitioner (→ Case Manager Ids) → build the ContentVersion payload → **insert one `PRM_AsyncJob__c`** (`ProcessName='Practitioner Creation'`) + **one `PRM_AsyncJobRecords__c` per practitioner** (seeded with the Case Manager Ids) → return `{ success, AsyncJobId }`; on validation failure return the error shape (no Case Manager creation, no insert). **No savepoint/branch/commit; the only sync service call is `PRM_CaseService`** | Valid payload creates the Case Manager(s), inserts exactly one job (+ per-practitioner records + payload file), returns the job Id; invalid payload creates/inserts nothing | 1.5 |
| F4 · IP wrapper config | Re-point the Practitioner Creation IP Remote Action to `remoteClass = PRM_RecordCreationIPWrapper`, `remoteMethod = 'submit'` (hard cutover; rollback = re-point to legacy); preserve the request contract; response now returns the async job Id (the heavy work completes asynchronously) | Job created on submit; legacy rollback path verified | 0.5 |

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
A Schema/env ──► B Foundation ──► C Async framework ──► D Selectors ──► E Services + batch classes ──► F Validation & intake ──► G Testing
```

- **Confirm DR field maps per service (EPIC E DoD)** — no `*__c` should remain "inferred" before a service's tests.
- Build foundation (B) + async framework (C) + selectors (D) before services; services + their batch classes (E) before the intake wrapper (F).
- The five batch classes + their hosted services (`PRM_HealthcareFacilityCreationService`, `PRM_HealthcareFacilityNetworkService`, `PRM_Level4RecordCreationService`) are the highest-risk / load-test priorities (Delegated locations + network).
- The flow ends with shadow-mode parity (G4) for **both** branches before cutover (re-pointing the IP wrapper).

---

## 12. Effort summary

| EPIC | Est (engineer-days) |
|---|---|
| A — Environment | 1.0 |
| B — Foundation | 2.0 |
| C — Async framework | 12.5 |
| D — Selectors (selector reuse) | 3.0 |
| E — Practitioner Creation services (E1–E18) + **CMA common service** + 5 batch classes | 23.5 + 1.0 (CMA) + batch wrappers *(re-baseline with the mapping, CL-15)* |
| F — Validation & intake *(shrunk; was Orchestration 8.5)* | ~6.5 |
| G — Testing | 10.5 |
| **Practitioner Creation total** | **~60 engineer-days** *(provisional — re-baseline once the batch↔service mapping lands, CL-15; and the removed base classes' home, TDD CL-13)* |

> Estimates are indicative for planning; refine after a thin POC (`PRM_CaseDataManagerService` invoked inside a single batch via the async chain, proving `PRM_AsyncOrchestrator` → batch → service → `findNextJob` end-to-end). EPICs **B, C, D are shared foundations** — once built here, PAR Form and PDM reuse them (and most E services), so their incremental cost is far lower.

---

## 13. Appendix — Async framework classes (data model)

| Class / Object | Surface |
|---|---|
| `PRM_AsyncJob__c` | parent / process run — `PRM_ProcessName__c`, `PRM_Status__c` (**no `PRM_CaseManager__c`** — removed). Two M-D children (siblings): Records + Details |
| `PRM_AsyncJobRecords__c` *(new)* | per–Case-Manager unit — M-D to `PRM_AsyncJob__c`; **only two custom fields:** `PRM_AsyncJob__c` (M-D) + `PRM_CaseManager__c` (Lookup→IndividualApplication). CM↔Job correlation |
| `PRM_AsyncJobDetails__c` | per–batch-step unit (e.g. 4) — **M-D to `PRM_AsyncJob__c`**, `PRM_ProcessName__c`, `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Sequence__c`, `PRM_Status__c`, `PRM_RetryCount__c` (a step processes all Case Managers; per-CM failures → DLQ) |
| `PRM_FailedRecordStaging__c` *(existing — reused)* | DLQ written by `logFailure` (audit + retry source); fields `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ErrorMessage__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_SourceFlow__c`, `PRM_CaseManager__c` + new `PRM_AsyncJobDetails__c` lookup |
| `PRM_AsyncJobConfig__mdt` | per **batch step** → `PRM_ProcessName__c`, `PRM_ServiceClassName__c` (**batch class name**), `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Sequence__c` |
| `PRM_AsyncJobTrigger` + helper (after insert) | trigger delegates to helper → invokes `PRM_AsyncOrchestrator` |
| `PRM_AsyncOrchestrator` | `createDetails` · `invokeJob` (**`Database.executeBatch` of the named batch class**) · `findNextJob` (sequential; **halt-on-failure**) · `statusUpdate` · `retry` (manual, uncapped; resumes from the failed step) · `jsonFileParser` · `logFailure` (reuse `PRM_ExceptionLogger` → staging) · `notifyOnFinish` (Custom Notification) |
| Batch classes *(EPIC E)* | `PractitionerBatch` · `PracticeLocationAndGroupBatch` · `GroupRelatedBatch` · `PLRelatedBatch` · `Level4RecordCreationBatch` — each `Database.Batchable`, branches IBC/Delegated, wraps its E-service(s), calls back `findNextJob` in `finish()` (mapping pending, CL-15) |
| `prmAsyncJobProgress` (LWC) | on Case Manager — progress, errors, Retry button (queries via `PRM_AsyncJobRecords__c`) |
| `PRM_AsyncJobCleanupBatch` | monthly-scheduled purge of old jobs + details + records + JSON files past threshold |
