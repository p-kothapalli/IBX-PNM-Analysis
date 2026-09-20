# PAR Case Manager Association via PRM_CaseManagerAssociation__c — User Stories (v3.1)

**Document Version:** 3.1
**Created:** June 7, 2026
**Last updated:** June 10, 2026
**Supersedes:** `PAR_CaseManager_Association_CMA_Redesign_User_Stories.md` (v2.0, Apr 29 2026); v3.0 (Jun 7 2026, this file)
**Vertical:** Provider Network Management (PNM)
**Authoring contract:** User Story Solution Architect (v1.6) — concrete personas, Given/When/Then ACs in business language, Technical Implementation (high-level) section per story.

**Why a v3 rewrite:** A full codebase re-audit on 2026-06-07 found that (a) every IP/DR version number in v2.0 is stale, (b) the CMA Apex layer has expanded far beyond what v2.0 assumed (new builders + two retroactive batches now exist), (c) some v2.0 "net-new" components proposed (a bespoke `createCMAsForPARHCPF` method, `PRM_PARCMABackfillBatch`) are unnecessary because reusable equivalents already exist, and (d) the PAR-form IPs that v2.0 wants to modify are simultaneously being retired by the Apex Service Framework migration (`requirements/Enhancements/PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`), which changes where CMA creation should live.

**Why a v3.1 revision (2026-06-10 — stakeholder direction):** Structural corrections to v3.0:
1. **US7 is retired — there is no standalone "read-side wiring" story.** v3.0 carved out a generic `PRMDREGetPARCaseHCPFViaCMA` DataRaptor + IP-wiring story (US7) as the HCPF slice of the fetch. In practice that abstraction does not work: each review flow loads a different object set through different DataRaptors, so the fetch cannot be wired once in a shared layer and inherited. **The CMA fetch is now baked directly into the acceptance criteria of each review story** — App Review (US8), PSV (US9), QC (US10), PDA Review (US11) and NMQC (US12) — each of which calls the one reusable Apex fetch service (US14). US14 (the service) stays; US7 (the wiring story) is gone.
2. **CMA records are fetched with Apex, not DataRaptors.** The review-flow DataRaptor extracts are the source of the current performance problems. The fetch service (US14) and every review story therefore **retrieve the case's records in Apex (hydrated server-side) and hand the records to the OmniScript**, replacing the per-section DR extracts — rather than returning Ids that DataRaptors then re-query. (This resolves the old CQ-N in favour of Apex hydration.)
3. **Terminated locations HIDE the review-launch button only for App Review, PSV and QC.** A terminated practice location must stop a reviewer from ever *opening* App Review / PSV / QC for that Case Manager (it would otherwise fail at submit). This reuses the already-deployed detection in the `prmTerminatedLocationAlert` LWC (see §0.6.6) and gates those three review-launch buttons on `PRM_CaseManagerRecordPage`. **PDA Review and NMQC are NOT button-gated** — those stages proceed normally (see #5).
4. **Terminated locations are NOT shown on any review step.** The Apex CMA fetch excludes terminated locations from the record set returned to every review step (App Review, PSV, QC, PDA Review, NMQC). v3.0's "show terminated rows read-only with a badge" treatment is removed; terminated locations are filtered out of the displayed data entirely.
5. **For PDA Review and NMQC, the `prmTerminatedLocationAlert` banner is suppressed and the reviewer is not blocked.** When the Case Manager's current stage is "PDA Review and Update" or "Network Management QC", the banner does not render, no button is hidden, and the reviewer works the case normally — terminated locations simply never appear (per #4). Baked into US11 (PDA) and US12 (NMQC).

**Related documents:**
- `requirements/Enhancements/PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` — the Apex-service target state for the PAR form submission flow (the home of CMA creation in the target architecture).
- `requirements/Enhancements/prompt.md` — the migration methodology that governs how PAR-form IPs are being replaced by Apex services.
- `PAR_CaseManager_Association_CMA_Redesign_User_Stories.md` (v2.0 — superseded).

---

## 0. Audit Reconciliation — v2.0 claims vs. verified codebase state (2026-06-07)

Every row below was verified against `force-app/main/default/` and the active OmniProcess `<isActive>` flag.

### 0.1 Version-number corrections (v2.0 was stale on all but one)

| Component | v2.0 said | Verified ACTIVE version | Highest present | Note |
|---|---|---|---|---|
| `PRM_CreatePractitionerAddressRecords` | v41 | **v43 active** | v44 (inactive) | PAR address orchestrator |
| `PRM_PractitionerAddressCreation` | v3 | **v5 active** | v5 | Delegated PAR address path |
| `PRM_ReviewPSVCaseRecordsUpdate` | v23 | **v26 active** | v26 | PSV **and** QC submit (shared) |
| `PRM_FetchFormPDAReview` | _24 | **v24 active** | v24 | Only version v2.0 got right |
| `PRM_FetchFormDetails` | _28 | **v31 active** | v31 | PSV / QC fetch |
| `PRM_FetchCaseRelatedDetails` | _6 | **v8 active** | v8 | CMA-gated reader |

### 0.2 CMA Apex layer — what actually exists today (v2.0 understated this)

| Component | Exists? | What it does |
|---|---|---|
| `PRM_CaseManagerAssociationService` | YES | `createCaseManagerAssociation(inputMap, outMap)` — parses payload, dispatches to builders, single insert, **sets `IndividualApplication.PRM_UseCaseManagerAssociation__c = true`**. |
| `PRM_CaseManagerAssociationDirectBuilder` | YES | Includes **`createCMAForPractitionerPracticeLocation(adpData, caseManagerId)`** → sets `PRM_HealthcarePractitionerFacility__c` + RecordType `Practitioner_Practice_Location`. **Exactly the HCPF link US6 needs — already built.** |
| `PRM_CaseManagerAssociationAddressBuilder` | YES (new since v2.0) | Address-scoped CMA records. |
| `PRM_CaseManagerAssociationNetworkBuilder` | YES (new since v2.0) | HFN / PPLTN / directory CMA records. |
| `PRM_CMARecordTypeHelper` | YES (new since v2.0) | `getCaseManagerAssociationRecordTypeId(devName)` cache for all 14 RTs. |
| `PRM_CaseManagerAssociationBatch` | YES (new since v2.0) | Retroactive backfill for **PDM Manual Change** cases (`PRM_UseCaseManagerAssociation__c = false`). |
| `PRM_CMAProviderChangeBatch` | YES (new since v2.0) | Retroactive backfill for **Provider Change Request** cases. |
| `PRM_CMACreationBatch` | YES (new since v2.0) | HFN-network CMA backfill from a passed-in HFN id list. |
| Remote Action wiring | YES | IPs call `PRM_PDMManualUtility.createCaseManagerAssociation` (which delegates to the service). PDM + PCF flows use this; Ancillary uses DataRaptor `PRMDRPCreateCaseManagerAssociation`. |

### 0.3 The gap v2.0 identified is STILL OPEN, but the build approach changes

- **Confirmed gap:** No version of `PRM_CreatePractitionerAddressRecords` (v43 active, v44 highest) or `PRM_PractitionerAddressCreation` (v5) references CMA in any form. The two retroactive batches key off `RecordType.Name = 'PDM Manual Change'` and `'Provider Change Request'` — **neither covers PAR (`PRM_PractitionerParticipationRequest`) or PNC.** So PAR submissions still create zero CMA records. The production failure mode in v2.0 §2 stands.
- **But v2.0's proposed net-new components are largely unnecessary:**
  - `createCMAsForPARHCPF(List<Id>, Id)` → **not needed as a brand-new method.** The PAR IP can reuse the existing Remote Action `PRM_PDMManualUtility.createCaseManagerAssociation` with an `adpData` payload (list of `{Id: <HCPF Id>}`), which routes to `createCMAForPractitionerPracticeLocation` and already flips the flag. A thin convenience wrapper is optional, not foundational.
  - `PRM_PARCMABackfillBatch` → **do not build from scratch.** Model on / extend `PRM_CaseManagerAssociationBatch` (same shape: query `IndividualApplication WHERE PRM_UseCaseManagerAssociation__c = false`, build via the existing builders, flip the flag). Only the record-type/scope filter changes (PAR + PNC).
  - `PRMDREGetPARCaseHCPFViaCMA` → **still does not exist** (genuinely net-new). Closest existing readers: `PRMDRExtractCaseManagerAssociationDetails` (active=false; filters CMA by `PRM_CaseManager__c`) and `PRMExtractCaseManagerAssociationsPCF` (active=false; filters by `PRM_CaseManager__c` + `PRM_RequestType__c LIKE`). One of these can be activated/extended rather than authored fresh.

### 0.4 Architectural conflict to resolve before coding (prompt.md / PNM_ParForm)

`requirements/Enhancements/PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` retires `PRM_CreatePractitionerAddressRecords` and moves HCPF creation into **`PRM_AddressRecordService.createCoreAddressRecords()`** (Apex, TX1). v2.0 proposed bolting a CMA Remote-Action step onto the legacy IP — that work would be thrown away at migration.

**Decision recorded for this rewrite (see CQ-A):** CMA creation is HCPF-adjacent, so its natural home is the same unit that creates HCPF. Two valid sequencing options:
- **Option 1 (migration-aligned, preferred):** build CMA creation directly inside `PRM_AddressRecordService` (right after the HCPF insert chain), so it ships once and survives. Requires the Apex-service migration of the PAR address leg to be in-flight.
- **Option 2 (interim, if migration not ready):** add the existing `createCaseManagerAssociation` Remote Action as a new step in the active `PRM_CreatePractitionerAddressRecords` (v43→v45) and `PRM_PractitionerAddressCreation` (v5→v6), gated by a feature flag, explicitly flagged as throwaway at migration.

The stories below are written so the **behaviour** (ACs) is identical under either option; only the Technical Implementation note differs.

### 0.5 Verified object facts

- `PRM_CaseManagerAssociation__c`: junction, `ControlledByParent`, history enabled, name `CMA-{00000}`. Fields confirmed: `PRM_HealthcarePractitionerFacility__c` (Lookup→HealthcarePractitionerFacility), `PRM_CaseManager__c` (Master-Detail→IndividualApplication), `PRM_RequestType__c` (Text 255). **14 RecordTypes** including `Practitioner_Practice_Location`.
- `IndividualApplication.PRM_UseCaseManagerAssociation__c` exists in the org (referenced by 6 perm sets + DataMigration CMDT + translation) **but its `.field-meta.xml` is not tracked in this repo** — flagged as a source-control gap (CQ-D).

---

## 0.6 CMA Object Coverage Audit — every lookup, every PAR record, every fetch flow (2026-06-07)

This section answers three questions directly: (1) what lookups exist on the CMA object today, (2) which records PAR submission creates and whether each is captured, and (3) which records each review flow loads by case manager (the fetch side). The principle: **a record needs CMA coverage if and only if a downstream flow loads it by filtering on `PRM_CaseManager__c`** (those are the records the overwrite bug can orphan). Records reached by traversing a parent (e.g., a Contact reached via its Account) do not independently need a CMA.

### 0.6.1 Current CMA lookups (authoritative — from `objects/PRM_CaseManagerAssociation__c/fields/`)

| # | Field | Type | Target SObject | Used by builder |
|---|---|---|---|---|
| 1 | `PRM_CaseManager__c` | **Master-Detail** | IndividualApplication | the case anchor (parent) |
| 2 | `PRM_HealthcarePractitionerFacility__c` | Lookup | HealthcarePractitionerFacility | DirectBuilder |
| 3 | `PRM_HealthcareFacility__c` | Lookup | HealthcareFacility | Direct/Address/Network |
| 4 | `PRM_HealthcareFacilityNetwork__c` | Lookup | HealthcareFacilityNetwork | Direct/Network |
| 5 | `PRM_HealthcareProviderTaxonomy__c` | Lookup | HealthcareProviderTaxonomy | DirectBuilder |
| 6 | `PRM_HealthcareFacilityAssociation__c` | Lookup | PRM_HealthcareFacilityAssociation__c | DirectBuilder |
| 7 | `PRM_Address__c` | Lookup | Address | AddressBuilder |
| 8 | `PRM_Identifier__c` | Lookup | Identifier | DirectBuilder |
| 9 | `PRM_BusinessLicense__c` | Lookup | BusinessLicense | DirectBuilder |
| 10 | `PRM_ProviderFeature__c` | Lookup | PRM_ProviderFeature__c | DirectBuilder |
| 11 | `PRM_ProgramParticipation__c` | Lookup | PRM_ProgramParticipation__c | DirectBuilder |
| 12 | `PRM_Account__c` | Lookup | Account | Direct/Network |
| 13 | `PRM_RequestType__c` | Text(255) | — | request-type tag |

**11 child lookups + 1 master-detail.** RecordTypes (14): `Practitioner_Practice_Location`, `Practitioner_at_Practice_Location_Taxonomy_and_Network`, `Practice_Location_Taxonomy`, `Practice_Location_Association`, `Practice_Location_Address`, `Practice_Location_Network`, `Healthcare_Provider_Taxonomy`, `Business_License`, `Identifier`, `Program_Participation`, `Provider_Feature`, `PRM_PracticeLocation`, `PRM_Practitioner`, `PRM_Vendor`.

### 0.6.2 What PAR submission creates → is it captured by CMA?

Source: `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` §2.1 (PAR IP-chain record inventory). "Needs CMA?" = is the object loaded by `PRM_CaseManager__c` in any review flow (§0.6.3).

| PAR-created SObject | Op | CMA lookup exists? | Needs CMA? | Verdict |
|---|---|---|---|---|
| Account (Person) | INSERT | ✅ `PRM_Account__c` | yes | **Covered** (wire builder) |
| HealthcareFacility (Group + Location) | INSERT | ✅ `PRM_HealthcareFacility__c` | yes | **Covered** |
| HealthcareFacilityNetwork (Group + Location) | INSERT | ✅ `PRM_HealthcareFacilityNetwork__c` | yes | **Covered** |
| HealthcarePractitionerFacility (HCPF) | INSERT | ✅ `PRM_HealthcarePractitionerFacility__c` | yes | **Covered** |
| HealthcareProviderTaxonomy | INSERT | ✅ `PRM_HealthcareProviderTaxonomy__c` | yes | **Covered** (taxonomy is `HealthcareProviderTaxonomy`, NOT `CareProviderFacilitySpecialty` — confirmed: the latter is never used in any DR/IP) |
| Identifier (CAQH) | INSERT | ✅ `PRM_Identifier__c` | yes | **Covered** |
| BusinessLicense | INSERT | ✅ `PRM_BusinessLicense__c` | yes | **Covered** |
| PRM_ProgramParticipation__c | INSERT | ✅ `PRM_ProgramParticipation__c` | yes | **Covered** |
| Address | INSERT | ✅ `PRM_Address__c` | yes | **Covered** |
| ProviderFeature (x3: ACC-linked, assistive aids, base) | INSERT | ✅ `PRM_ProviderFeature__c` | (QC loads `PRM_ProviderFeature__c` by CM) | **Covered** |
| **HealthcareProvider** | INSERT | ❌ none | yes (App/QC/PDA) | **GAP → new lookup** |
| **HealthcareProviderNpi** (individual/group/location) | INSERT | ❌ none | yes (App/QC) | **GAP → new lookup** |
| **PersonEducation** | INSERT | ❌ none | yes (App/QC) | **GAP → new lookup** |
| **PersonLanguage** | INSERT | ❌ none | yes (App/QC) | **GAP → new lookup** |
| **Location** | INSERT | ❌ none | yes (App/QC) | **GAP → new lookup** |
| **ContactProfile** | INSERT | ❌ none | yes (QC) | **GAP → new lookup** |
| **PRM_InfoCodeAssignment__c** (telehealth info codes) | INSERT | ❌ none | yes (QC) | **GAP → new lookup** (confirmed object: `PRMLoadInfoCodeAssigned` → `PRM_InfoCodeAssignment__c`, which has `PRM_CaseManager__c`) |
| PractitionerFacilityAffiliation (PFAA) | INSERT | ❌ none | no (reached via HCPF parent) | No lookup needed |
| AffirmingCareCategory (ACC) | INSERT | ❌ none | no (reached via parent / modeled as ProviderFeature) | No lookup needed |
| Contact (primary/secondary) | INSERT | ❌ none | no (queried, but not by CM) | No lookup needed |
| ContactContactRelation | INSERT | ❌ none | no (via Contact/Account) | No lookup needed |
| ContentVersion (file) | INSERT | ❌ none | no | No lookup needed |
| Case | INSERT | n/a | n/a | the case, not a child |
| IndividualApplication (Case Manager) | INSERT | n/a (this is the parent) | n/a | the CMA parent |

**Net: 7 new lookups to create** for full PAR coverage: HealthcareProvider, HealthcareProviderNpi, PersonEducation, PersonLanguage, Location, ContactProfile, PRM_InfoCodeAssignment__c.

### 0.6.3 Fetch side — what each review flow loads by `PRM_CaseManager__c`

Active fetch IPs and the per-object load matrix (✔ = loaded by a `PRM_CaseManager__c` WHERE filter in that flow):

> **Column note on "QC":** the initial-cred **QC Review (US10) has no separate reader — it runs inside the PSV OmniScript and uses the PSV column**. The `PRM_InitManualUpdatesQC` v9 column below is the **Manual-Updates / "Manual QC" (PDM) "Network Management QC"** flow (`PRM_ManualUpdatesQC_English`), which is a **different flow, out of scope** for these initial-cred stories. It is kept here only because it is the **single most complete CM-scoped reader** and therefore a useful superset reference.

| SObject | App Review `PRM_FetchFormDetails` v31 | Manual QC (PDM)* `PRM_InitManualUpdatesQC` v9 | PDA / NetMgmt-QC `PRM_FetchFormPDAReview` v24 | Committee `PRM_DataRetrievalforHAPACCommitteeReview` v3 | PSV **+ QC Review (US10)** `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33 (wraps `PRM_FetchFormDetails`) |
|---|:--:|:--:|:--:|:--:|:--:|
| HealthcarePractitionerFacility | ✔ | ✔ | ✔ | | ✔ⁱ |
| HealthcareFacility | ✔ | ✔ | ✔ | ✔ | ✔ⁱ |
| HealthcareFacilityNetwork | ✔ | ✔ | ✔ | | ✔ⁱ |
| HealthcareProviderTaxonomy | ✔ | ✔ | | | ✔ⁱ |
| Address | ✔ | ✔ | | | ✔ⁱ |
| Identifier | ✔ | ✔ | ✔ | ✔ | ✔ⁱ |
| BusinessLicense | ✔ | ✔ | | ✔ | ✔ⁱ |
| Account | ✔ | ✔ | | | ✔ⁱ |
| HealthcareProvider | ✔ | ✔ | ✔ | | ✔ⁱ |
| HealthcareProviderNpi | ✔ | ✔ | | | ✔ⁱ |
| PersonEducation | ✔ | ✔ | | | ✔ⁱ |
| PersonLanguage | ✔ | ✔ | | | ✔ⁱ |
| Location | ✔ | ✔ | | | ✔ⁱ |
| ContactProfile | | ✔ | | | |
| BoardCertification | | ✔ | | | |
| PRM_ProviderFeature__c | | ✔ | | | |
| PRM_ProgramParticipation__c | | ✔ | | | |
| PRM_HealthcareFacilityAssociation__c | | ✔ | | | |
| PRM_InfoCodeAssignment__c | | ✔ | | | |
| PRM_CaseDataManager__c | ✔ | | ✔ | | ✔ⁱ |
| PRM_HealthcareFacilityBundle__c / BundleAssociation | | ✔ | | | |
| PRM_ContractHierarchy__c / AccountContractEntity | | ✔ | | | |
| PRM_HealthcareFacilityNPI__c | | ✔ | | | |
| HealthCloudGA__AccountAccountRelation__c | ✔ | | | | ✔ⁱ |
| PRM_AncillaryAssessment__c | | | | ✔ | |
| PRM_AdverseActionReview__c | | | | | ✔ |

Notes: (a) ***Manual QC (PDM)** is the out-of-scope `PRM_ManualUpdatesQC_English` flow (the "Manual QC" button), **not** the initial-cred QC Review (US10). Its `PRM_InitManualUpdatesQC` v9 reader is the most complete case-manager-scoped reader and already extracts `PRM_CaseManagerAssociation__c` (`PRMDRExtractCaseManagerAssociationDetails`) — listed here only as proof the read-via-CMA pattern is viable and as a superset reference. **The initial-cred QC Review reads via the PSV column** (`PRM_FetchParDetails` → `PRM_FetchFormDetails`), since QC is a stage of the PSV OmniScript. (b) **PSV is NOT a read-only/save-only flow.** The PSV Review OmniScript (`PRM_PrimarySourceVerificationReview_English`) loads its screen through `PRM_FetchParDetailsParent` → `PRM_FetchParDetails`, which **internally calls `PRM_FetchFormDetails`** (the App-Review fetch) — so every object App Review loads by `PRM_CaseManager__c` is **inherited by PSV** (marked **✔ⁱ** = inherited via the wrapped App-Review fetch). On top of that, `PRM_FetchParDetails` adds its own case-manager-scoped extracts: `PRM_AdverseActionReview__c` (`DRTurboGetAdverseReviewAction` → `PRMTurboGetAdverseReviewAction`, filtered by `CaseManagerId`, recred QC-Review path only) and a contact-info read (`DRGetContactInformation` → `PRMFetchContactInformation`, which extracts the case manager's primary/secondary contact `Account`s via the IA contact lookups). `PRM_ReviewPSVCaseRecordsUpdate` v26 is the **save** IP, not the fetch. (c) NetMgmt-QC shares the PDA fetch IP.

**✔ⁱ = inherited** by PSV because `PRM_FetchParDetails` wraps App Review's `PRM_FetchFormDetails`. **Consequence for the CMA fix:** converting `PRM_FetchFormDetails` to the US14 Apex fetch (US8) automatically fixes the PSV screen read too — confirming US9's "PSV shares the App-Review fetch" design. US9's PSV-specific read work is limited to the extra `PRM_AdverseActionReview__c` / contact-info extracts.

**Submit side — what's shared and what isn't (verified 2026-06-10).** This table is the **fetch/read** side. On the record-**write** (create-on-submit) side, **App Review is standalone; PSV and QC share one IP** (QC is a stage of the PSV OmniScript); PDA/NMQC share another:

| Flow | Submit / record-update IP |
|---|---|
| App Review | `PRM_ReviewParCaseRecordsUpdateParent` → `PRM_ReviewParCaseRecordsUpdate` v15 (+ CAQH via sub-OS `PRM_AddCAQHRecord`) |
| **PSV + QC Review (US9 + US10)** | `PRM_ReviewPSVCaseRecordsUpdateParent` → `PRM_ReviewPSVCaseRecordsUpdate` **v26** (QC runs the `QCProceedTo` branch of the same IP) |
| PDA / NMQC | `PRM_InitialCredPDAReviewUpdate` v23 → `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7 (+ `PRM_PNCPDAUtility.PNCPDABatch`) |
| _Manual QC (PDM) — out of scope_ | `PRM_SaveManualUpdatesQC` (the `PRM_ManualUpdatesQC_English` flow, not the initial-cred QC Review) |

So CMA create-on-submit upkeep is implemented **once for App Review** (Par v15), **once for PSV/QC together** (v26 — the QC branch inherits US9's hooks), and **once for PDA/NMQC** (the SubIPUpdate chain). Earlier drafts that pointed QC at `PRM_SaveManualUpdatesQC` were **incorrect** — that IP belongs to the separate Manual-QC (PDM) flow.

### 0.6.4 Additional lookups required (consolidated)

**Tier 1 — needed for PAR coverage (created by PAR + loaded by case manager):**
HealthcareProvider, HealthcareProviderNpi, PersonEducation, PersonLanguage, Location, ContactProfile, PRM_InfoCodeAssignment__c.

**Tier 2 — needed for full reuse across off-cycle / ancillary / recred / re-assessment (loaded by case manager in QC/Committee/PSV but not necessarily PAR-created):**
BoardCertification (recred), PRM_HealthcareFacilityBundle__c, PRM_HealthcareFacilityBundleAssociation__c, PRM_ContractHierarchy__c, PRM_AccountContractEntity__c, PRM_HealthcareFacilityNPI__c, PRM_AncillaryAssessment__c (ancillary/HAPAC), PRM_AdverseActionReview__c, HealthCloudGA__AccountAccountRelation__c. (`PRM_CaseDataManager__c` is the case-side record — evaluate whether it warrants a child lookup or is treated as the anchor; CQ-M.)

Each new lookup follows the existing pattern (`deleteConstraint=SetNull`, `relationshipName=Case_Manager_Associations`) and gets a matching RecordType + a builder method + a service routing key, so creation stays in the Apex service and is reused by every flow.

### 0.6.5 The "do not bake CMA logic into OmniScripts" mandate → one reusable Apex fetch service, called per flow

Three principles govern the read side:
- **CMA logic stays out of OmniScripts.** Creation and fetch are flow-agnostic Apex so PAR, off-cycle, ancillary, recred, and re-assessment all reuse them. No OmniScript step ever queries or writes the CMA junction.
- **The fetch is Apex, not DataRaptors.** The existing review-flow DataRaptor extracts (filtered by `PRM_CaseManager__c`) are the cause of the current performance problems. The fetch service therefore **does the SOQL in Apex and returns hydrated records** (the fields each step needs), which the IP/OmniScript consumes directly. The per-section DR extracts are **replaced** by the Apex fetch, not merely re-pointed to `Id IN :<list>`. This decides the old CQ-N in favour of Apex hydration.
- **The fetch *call* is baked into each review story's acceptance criteria.** v3.0's standalone US7 (a generic shared read-side DataRaptor + IP wiring) does not work, because each flow loads a different object set. So each review story (US8–US12) owns its own fetch ACs: it calls the single reusable Apex fetch service and replaces *its own* extracts. The service is shared; the wiring is per-flow.

- **Creation:** already centralized in `PRM_CaseManagerAssociationService.createCaseManagerAssociation(inputMap, outMap)` exposed via the `PRM_PDMManualUtility` Remote Action. Extend it with builders for the Tier-1/Tier-2 objects; every guided flow passes its created-record Id lists in the payload. **No CMA logic in any OmniScript.**
- **Fetch (US14):** add `PRM_CaseManagerAssociationFetchService` (Apex Remote Action via `VlocityOpenInterface2`): given a `caseManagerId`, it queries `PRM_CaseManagerAssociation__c` once, then in **Apex** queries and returns the **active** related records (hydrated, per object type) — **terminated locations excluded** (see §0.6.6) — plus a separate `TerminatedLocations[]` list and a `HasTerminatedLocations` flag (used by the App Review / PSV / QC button-hide gate). Each review IP **replaces its `WHERE PRM_CaseManager__c = :CMID` DataRaptor extracts with this Apex fetch**. One service, called by all flows; **no CMA logic and no per-section DR extract in the read path.**

### 0.6.6 Existing terminated-location detection to REUSE (already deployed — verified 2026-06-10)

The "hide the review button when a location is terminated", "suppress the banner at PDA/NMQC stages", and "do not show terminated locations on review steps" requirements do **not** start from scratch — the detection logic already exists and must be reused, not re-invented:

| Component | What it already does | How v3.1 reuses it |
|---|---|---|
| `prmTerminatedLocationAlert` (LWC, on `PRM_CaseManagerRecordPage`) | Renders a stop-work banner on the Case Manager (IndividualApplication) record when any linked `HealthcareFacility` is terminated. Detection only — today its body text merely *warns* ("Opening any review flow … will result in an error at the submit step"), and it renders at **every** stage. | The **same termination predicate** drives the App Review/PSV/QC button-hide gate and the fetch service's terminated-exclusion. The banner stays as the human-readable explanation **for App Review/PSV/QC stages only** — it is **suppressed when the case stage is "PDA Review and Update" or "Network Management QC"** (US11/US12). |
| Termination predicate (in the LWC) | `PRM_IsErrorRecord__c = true` **OR** (`PRM_EffectiveTo__c != null` AND `PRM_Active__c = false`) **OR** (`PRM_EffectiveTo__c != null` AND `PRM_Active__c = true` AND `PRM_EffectiveTo__c > TODAY`). Linkage: HCPF.PractitionerId = IA practitioner contact **OR** `PRM_CaseManager__c = IA` (direct/indirect). | This is the canonical "is terminated" definition for the whole feature. The Apex CMA fetch service (US14) applies the identical predicate to exclude terminated locations and to compute `HasTerminatedLocations`. |
| `PRM_TerminationAlertReviewStages__mdt.PRM_ReviewStageList__c` | CMDT, keyed by IndividualApplication RecordType; lists the review stages the banner names — e.g. PAR = `"App Review, PSV, QC, Committee, PDA Review, NMQC"`. | Used to drive (a) **which review-launch buttons to hide** (App Review/PSV/QC) and (b) **at which stages to suppress the banner** (PDA Review and Update, NMQC). Config-driven so behaviour stays consistent per RecordType. |
| `PRM_CaseManagerRecordPage` (FlexPage) | Hosts the review-launch buttons (`prmGenericButtonLauncher` + `runtime_omnistudio:flexcard`), gated on CaseType/Status values ("Application Review", "QC Review", "Committee Review", "PDA Review and Update", …). | The hide-the-review-button requirement adds a visibility condition (`NOT HasTerminatedLocations`) to the **App Review, PSV and QC** launchers only. PDA Review and NMQC launchers are left unchanged (no gate). |

**Stage-by-stage behaviour matrix (v3.1):**

| Stage | Terminated locations shown on steps? | Review-launch button | `prmTerminatedLocationAlert` banner |
|---|:--:|---|---|
| App Review (US8) | No (Apex fetch excludes) | **Hidden** when terminated | Shown |
| PSV (US9) | No | **Hidden** when terminated | Shown |
| QC (US10) | No | **Hidden** when terminated | Shown |
| PDA Review and Update (US11) | No | Unchanged (not gated) | **Suppressed** |
| Network Management QC (US12) | No | Unchanged (not gated) | **Suppressed** |

**Design consequence:** terminated-location handling is centralized — one predicate, one CMDT-driven stage list, one detection LWC. US8–US12 do not each re-detect terminations; they consume the shared terminated-excluded record set (all five), the `HasTerminatedLocations` flag (App Review/PSV/QC button-hide), and the stage list (PDA/NMQC banner suppression).

---

## 1. Epic & story map

**Epic:** PAR Case Manager Association via CMA Object — give every PAR case a stable, immutable PAR→HCPF link so review flows survive PDM / Provider-Change overwrites of `HCPF.PRM_CaseManager__c`.

| Story | Title | Persona | Priority | Depends on |
|---|---|---|---|---|
| US6 | Create CMA records during PAR form submission | Credentialing Specialist (dev contract) | P0 | — |
| ~~US7~~ | ~~Resolve review-flow HCPF via CMA (new DR + IP wiring)~~ **RETIRED in v3.1** — the fetch is now baked into each review story's ACs (US8–US12) and backed by the reusable service (US14); there is no standalone read-side wiring story | — | — | — |
| US8 | App Review — CMA fetch (baked, Apex) + hide review button on terminated locations + CMA upkeep at submit | Credentialing Specialist | P0 | US6, US13, US14 |
| US9 | PSV Review — CMA fetch (baked, Apex) + hide review button on terminated locations + CMA upkeep at submit | PSV Reviewer | P0 | US6, US13, US14, US8 |
| US10 | QC Review (stage of the PSV OmniScript) — fetch + submit **inherited from US9** (shared `PRM_FetchParDetails`/`PRM_ReviewPSVCaseRecordsUpdate` v26); net-new = hide review button on terminated locations | QC Reviewer | P0 | US6, US13, US14, US8, **US9** |
| US11 | PDA Review — CMA fetch (baked, Apex) + exclude terminated locations + suppress banner at PDA stage + CMA upkeep at submit (no button-hide) | PDA Specialist | P1 | US6, US13, US14 |
| US12 | Network Management QC — CMA fetch (baked, inherited) + exclude terminated locations + suppress banner at NMQC stage (no button-hide) | Network Management QC Specialist | P1 | US6, US13, US14, US11 |
| US13 | Extend CMA schema + creation service to capture ALL case-scoped records (7 new lookups) | Platform/Dev | P0 | — (precedes US6 coverage) |
| US14 | Reusable CMA fetch service across all guided/review flows (excludes terminated locations; no OmniScript logic) | Platform/Dev | P0 | US13, US6 |

> **Scope note (v3.1):** **US13 centralizes creation** of a CMA for every case-scoped record (per §0.6.2). **US14 centralizes the fetch** into one reusable Apex service (per §0.6.5). US6 is the HCPF *creation* slice of US13. The HCPF *read* slice that v3.0 called "US7" no longer stands alone — **each review story (US8–US12) bakes its own fetch ACs**, all calling the one US14 service. Terminated-location detection is shared (§0.6.6): the same predicate hides the review-launch button and excludes terminated locations from every review step.

---

# USER STORY US6: Create CMA Records During PAR Form Submission

**Persona:** Credentialing Specialist (the story is consumed by developers; the business value accrues to the Credentialing Specialist whose case data must survive later overwrites)
**Priority:** P0 — foundation; blocks US8–US12
**OmniScript:** `PRM_PractitionerParticipationForm_English` (submit)
**Integration Procedures:** `PRM_CreatePractitionerAddressRecords` (v43 active) and `PRM_PractitionerAddressCreation` (v5 active) — OR their Apex-service successor `PRM_AddressRecordService` (see CQ-A)
**Relevant Requirements:** v2.0 US6; `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`

---

## Story

**As a** Credentialing Specialist,
**I want** **every case-scoped record** created on a PAR submission — not just practice locations, but the provider, NPIs, taxonomy, identifiers, licenses, addresses, education, languages, contact profile, info codes, networks, program participation, and account — to be permanently tied to my PAR case through Case Manager Association records,
**So that** when a later PDM or Provider-Change request re-stamps any of those records, my PAR case still knows exactly which records belong to it and every downstream review (App/PSV/QC/Committee/PDA/NMQC) loads correctly.

**Why it matters:** Today PAR submission stamps `PRM_CaseManager__c` directly on each created record and creates no CMA. When PDM/Provider-Change later overwrites that field on **any** of those records, the review flows that load them by case manager return zero rows — producing the "Required Fields Missing" failure (e.g., production case IA-0000096229) and missing data in every section, not just locations. A CMA record is a master-detail child of the PAR case — its parent can never be reassigned — so it is an immutable mirror of every PAR→record link. **This story must cover the full object set, identical to US13; if a dev only wires HCPF, the provider/NPI/education/taxonomy/info-code sections remain broken.**

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| PAR submission | `PRM_PractitionerParticipationForm_English` | Record creation (after each insert branch) | `PRM_CreatePractitionerAddressRecords` v43 / `PRM_PractitionerAddressCreation` v5 / `PRM_PractitionerScreenRecordCreation` / `PRM_CreateGroupScreenRecord` / `PRM_CreateProviderScreenRecords` (or `PRM_AddressRecordService` — see CQ-A) |

## Preconditions

- The submission creates or reuses records across the object set below.
- The PAR `IndividualApplication` (Case Manager) Id is known at the point of record creation.

---

## Objects this submission MUST create CMAs for (full set — mirrors US13)

Every object PAR creates that is case-scoped (per §0.6.2) must get a CMA, using the **exact field mapping in the US13 Master field-mapping matrix** (AC-13.3–AC-13.21). The dev must address all of these, not just HCPF:

| # | Object created by PAR | CMA builder / payload key | Field mapping (see US13) |
|---|---|---|---|
| 1 | HealthcarePractitionerFacility (HCPF) | `adpData` → `createCMAForPractitionerPracticeLocation` | AC-13.3 |
| 2 | HealthcareFacility (group + location) | `lmsPLCOI` → `createCMAForPracticeLocation` | AC-13.4 |
| 3 | HealthcareFacilityNetwork (taxonomy + network) | `addPracLocTaxonomyData`/`practitionerPPLTNData`/… → taxonomy & network builders | AC-13.5, 13.6, 13.7 |
| 4 | HealthcareProviderTaxonomy | `practitionerTaxonomyData` → `createCMAForPractitionerTaxonomy` | AC-13.8 |
| 5 | PRM_HealthcareFacilityAssociation__c | `praclocAssociationData`/`capSite` → association builders | AC-13.9 |
| 6 | Address | `newlyAddedAddressData`/`mailingBillingAddressData`/… → Address builder | AC-13.10 |
| 7 | Identifier (CAQH/Tax/Medicare) | `oldTaxId`+`newTaxId`/`medicareData` → identifier builders | AC-13.11 |
| 8 | BusinessLicense | `practitionerBusinessLicense` → `createCMAForBusinessLicense` | AC-13.12 |
| 9 | PRM_ProviderFeature__c | `pracProviderFeatureCreationData` → `createCMAForProviderFeature` | AC-13.13 |
| 10 | PRM_ProgramParticipation__c | `pracLocProgramParticipation` → `createCMAForProgramParticipation` | AC-13.13 |
| 11 | Account (person/vendor) | `lmsAccountsCOI`/`VendorId` → account builders | AC-13.14 |
| 12 | **HealthcareProvider** | `healthcareProviderData` → `createCMAForHealthcareProvider` 🆕 | AC-13.15 |
| 13 | **HealthcareProviderNpi** | `healthcareProviderNpiData` → `createCMAForHealthcareProviderNpi` 🆕 | AC-13.16 |
| 14 | **PersonEducation** | `personEducationData` → `createCMAForPersonEducation` 🆕 | AC-13.17 |
| 15 | **PersonLanguage** | `personLanguageData` → `createCMAForPersonLanguage` 🆕 | AC-13.18 |
| 16 | **Location** | `locationData` → `createCMAForLocation` 🆕 | AC-13.19 |
| 17 | **ContactProfile** | `contactProfileData` → `createCMAForContactProfile` 🆕 | AC-13.20 |
| 18 | **PRM_InfoCodeAssignment__c** (telehealth) | `infoCodeAssignmentData` → `createCMAForInfoCodeAssignment` 🆕 | AC-13.21 |

> Not captured (per §0.6.2): PFAA, AffirmingCareCategory, Contact, ContactContactRelation, ContentVersion (reached via parent / not case-scoped).

---

## Acceptance Criteria

**AC-6.1 — New PAR submission links every CASE-SCOPED record to the case (full set)**

**Given** a Credentialing Specialist submits a new PAR that creates records across the object set above,
**When** the submission finishes creating those records,
**Then** one Case Manager Association is created per created record across **all** covered object types (HCPF, HCF, HFN, taxonomy, association, address, identifier, license, provider feature, program participation, account, HealthcareProvider, HealthcareProviderNpi, PersonEducation, PersonLanguage, Location, ContactProfile, InfoCodeAssignment),
**And** each association uses the exact field mapping defined in US13 for that object,
**And** the PAR case is marked as using Case Manager Associations,
**And** a section that created no records produces no CMA (no empty rows).

**AC-6.1.1 — Locations specifically (worked sub-case)**

**Given** the submission created two practice-location HCPFs,
**When** it completes,
**Then** two `Practitioner_Practice_Location` CMAs exist (one per HCPF), per AC-6.6.

**AC-6.2 — Reused/existing location on the PAR also gets a fresh association**

**Given** a practitioner re-submits a PAR that reuses an existing practice location (e.g., a previously denied or terminated location),
**When** the submission completes,
**Then** a new Case Manager Association is created linking the new PAR case to that existing location,
**And** any association from the earlier case for the same location is left untouched as history.

**AC-6.3 — Later PDM/Provider-Change overwrite does not disturb the PAR's associations**

**Given** a PAR case has associations from AC-6.1,
**When** a later PDM or Provider-Change request re-stamps the same practice location to a different case,
**Then** the PAR case's associations are unchanged,
**And** the PAR case can still produce the correct list of its locations.

**AC-6.4 — Re-submission does not create duplicate associations**

**Given** a PAR case that already has associations for its locations,
**When** the submission step runs again (retry or resubmit),
**Then** no duplicate associations are created for locations already linked to that case.

**AC-6.5 — Backfill for in-flight PAR cases**

**Given** PAR cases already in flight that have no associations (submitted before this feature),
**When** the backfill job runs,
**Then** associations are created for each in-flight PAR case's locations,
**And** each such case is marked as using Case Manager Associations,
**And** a run summary reports cases processed, associations created, and errors.

**AC-6.6 — Exact HCPF field mapping (the dev contract)**

**Given** each `HealthcarePractitionerFacility` (HCPF) created by the PAR submission,
**When** the CMA record for it is built,
**Then** exactly these fields are set and no others:

| CMA field | Value |
|---|---|
| `PRM_HealthcarePractitionerFacility__c` | the created HCPF's Id |
| `RecordTypeId` | the `Practitioner_Practice_Location` RecordType (via `PRM_CMARecordTypeHelper.getCaseManagerAssociationRecordTypeId('Practitioner_Practice_Location')`) |
| `PRM_CaseManager__c` | the PAR `IndividualApplication` (case manager) Id |
| `PRM_RequestType__c` | not set (HCPF mapping carries no request type) — unless CQ-B decides to stamp `'PAR'` |
| all other lookups (`PRM_HealthcareFacility__c`, `PRM_Account__c`, …) | left null |

**And** an HCPF whose Id is blank/non-string is skipped (no empty CMA row),
**And** this is the same mapping as US13 AC-13.3 (US6 is its HCPF slice).

> Full per-object field mappings for every other record PAR creates are specified in **US13 §"Master field-mapping matrix"** and AC-13.3–AC-13.21.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_AddressRecordService` (target) **or** the active PAR IPs (interim) | Apex service method **or** new IP Remote-Action step(s) | After **each insert branch**, invoke CMA creation passing the created-record Ids for **every** covered object as the matching payload keys (`adpData`, `lmsPLCOI`, taxonomy/network keys, `newlyAddedAddressData`, identifier keys, `practitionerBusinessLicense`, `pracProviderFeatureCreationData`, `pracLocProgramParticipation`, `lmsAccountsCOI`, plus the 🆕 keys `healthcareProviderData`/`healthcareProviderNpiData`/`personEducationData`/`personLanguageData`/`locationData`/`contactProfileData`/`infoCodeAssignmentData`) and `caseManagerId = <PAR IA Id>` | Drives AC-6.1 (full set). Home depends on CQ-A. Depends on US13 builders existing for the 🆕 keys. |
| `PRM_PDMManualUtility.createCaseManagerAssociation` → `PRM_CaseManagerAssociationService` | Reuse (extend in US13) | Existing keys already route to the right builders + flip `PRM_UseCaseManagerAssociation__c`; US13 adds the 7 new keys/builders | Do NOT author a new `createCMAsForPARHCPF` method (v2.0 mistake). |
| `PRM_CaseManagerAssociationService.createCaseManagerAssociation` | Optional Apex enhancement | Add dedup guard: skip record ids already linked to this case manager **per type** (pattern: `PRM_PDMManualCrossRefFinishService.filterExistingCaseManagerAssociations`) | Drives AC-6.4. |
| PAR backfill | Reuse/extend `PRM_CaseManagerAssociationBatch` | Add a PAR/PNC scope (`RecordType.Name IN ('PNM Application'/PAR, PNC)` + `PRM_UseCaseManagerAssociation__c = false`) building CMAs from each case's **full set** of case-scoped records (not just HCPFs) | Drives AC-6.5. Do NOT build `PRM_PARCMABackfillBatch` from scratch. |
| `PRM_RequestType__c = 'PAR'` on PAR CMAs | Optional field value | Tag PAR-created CMAs to distinguish from PDM | Pending CQ-B. |

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ-A | Build CMA creation inside the new `PRM_AddressRecordService` (migration-aligned) or bolt it onto the active legacy IPs now (throwaway at migration)? | Determines where the code lives and whether it survives the Apex-service migration | Technical / Architecture |
| CQ-B | Stamp `PRM_RequestType__c = 'PAR'` on PAR-origin CMAs? | Query/report filtering; consistency with PDM records | BA / Technical |
| CQ-C | Extend the existing `PRM_CaseManagerAssociationBatch` for PAR backfill, or add a sibling batch? | Reuse vs. isolation; test surface | Technical |
| CQ-D | `IndividualApplication.PRM_UseCaseManagerAssociation__c` field-meta is missing from source control — add it? | Deployment integrity | Technical / Ops |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| CMA creation in service/IP (reuse existing builder) | Apex method or IP step | M | AI-estimated — reuses tested builder |
| Dedup guard | Apex | S | AI-estimated |
| PAR backfill (extend existing batch) | Apex batch | M | AI-estimated |
| Unit + regression tests | Apex/manual | M | AI-estimated |

**Total Estimated Effort:** M–L (AI-estimated — validate with team). Lower than v2.0 because no net-new service method or net-new batch.

---

# USER STORY US7: ~~Resolve Review-Flow HCPF Through CMA (New DataRaptor + IP Wiring)~~ — RETIRED in v3.1

> **STATUS: RETIRED. Do not build US7 as a standalone story.** v3.0 carved the read side into a shared "HCPF DataRaptor + IP wiring" story (US7) on the assumption that one generic read-side component could be wired once and inherited by every flow. That does not hold: App Review, PSV, QC, PDA and NMQC each load a **different object set** through **different DataRaptors/IPs** (see §0.6.3), so there is no single place to "wire the fetch." The work US7 described has been redistributed:
>
> - **The reusable fetch *service* → US14.** One Apex service (`PRM_CaseManagerAssociationFetchService`) that, given a `caseManagerId`, queries the CMA junction and then in **Apex** returns the active per-object records (hydrated, terminated locations excluded), plus the terminated set + `HasTerminatedLocations` flag. **Apex, not DataRaptors** — the DR extracts are the current performance problem.
> - **The per-flow fetch *wiring* → baked into each review story's ACs:** App Review (US8), PSV (US9), QC (US10), PDA (US11), NMQC (US12). Each of those stories now contains its own "prepopulate via CMA" acceptance criteria and **replaces its own DR extracts with the US14 Apex fetch**.
> - **The terminated-location handling** moves from "flag in the result" to concrete behaviours owned by US8–US12: **(a) exclude terminated locations** from every review step's displayed data (all five flows); **(b) hide the review-launch button** when the case has a terminated location — **App Review / PSV / QC only**; **(c) suppress the `prmTerminatedLocationAlert` banner** at the **PDA Review and Update** and **NMQC** stages (no button-hide, reviewer proceeds normally).
>
> The reference material below (which objects each flow must resolve, and the universal read behaviours) is retained as a **shared contract** that US8–US12 point back to — it is documentation, not a buildable backlog item.

## Shared read-side contract (referenced by US8–US12)

Each review story below **replaces its own `WHERE PRM_CaseManager__c = :CMID` DataRaptor extracts with the US14 Apex fetch**, which returns the **active** hydrated records (terminated locations excluded). The per-flow object coverage:

| Object (CMA lookup) | App Review `PRM_FetchFormDetails` v31 (US8) | PSV + QC Review `PRM_FetchParDetails` v33 → `PRM_FetchFormDetails` (US9/US10, **inherits App Review**) | PDA/NMQC `PRM_FetchFormPDAReview` v24 (US11/US12) |
|---|:--:|:--:|:--:|
| HealthcarePractitionerFacility | ✔ | ✔ⁱ | ✔ |
| HealthcareFacility | ✔ | ✔ⁱ | ✔ |
| HealthcareFacilityNetwork | ✔ | ✔ⁱ | ✔ |
| HealthcareProviderTaxonomy | ✔ | ✔ⁱ | |
| Address | ✔ | ✔ⁱ | |
| Identifier | ✔ | ✔ⁱ | ✔ |
| BusinessLicense | ✔ | ✔ⁱ | |
| Account | ✔ | ✔ⁱ | |
| HealthcareProvider | ✔ | ✔ⁱ | ✔ |
| HealthcareProviderNpi | ✔ | ✔ⁱ | |
| PersonEducation | ✔ | ✔ⁱ | |
| PersonLanguage | ✔ | ✔ⁱ | |
| Location | ✔ | ✔ⁱ | |
| PRM_AdverseActionReview__c | | ✔ (PSV/QC-only) | |

> **✔ⁱ = inherited.** PSV (US9) **and** the QC Review (US10) run inside the **same OmniScript** (`PRM_PrimarySourceVerificationReview_English`) and prepopulate through `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33, which **wraps** the App-Review fetch (`PRM_FetchFormDetails` v31). So they inherit the entire App Review column automatically — converting `PRM_FetchFormDetails` in US8 fixes the PSV **and** QC read. The only PSV/QC-specific reads are the `PRM_AdverseActionReview__c` extract (`DRTurboGetAdverseReviewAction`) and the contact-`Account` read (`DRGetContactInformation`) in the fetch chain — not in the v26 save IP. (The broader `ContactProfile`/`PRM_ProviderFeature__c`/`PRM_ProgramParticipation__c`/`PRM_InfoCodeAssignment__c` superset in §0.6.3 belongs to the **out-of-scope Manual-QC (PDM)** reader, not to this pipeline.)

**Universal read behaviours every review story (US8–US12) must satisfy** (these were AC-7.1–7.5; they now appear, contextualized, in each review story):
- **Apex fetch (no DR):** records are retrieved by the US14 Apex service and handed to the OmniScript; the legacy per-section DataRaptor extracts are removed.
- **Overwrite-proof load:** for a CMA-enabled case, each section the flow loads returns the correct records resolved through the CMA junction, unaffected by a PDM/Provider-Change overwrite of `PRM_CaseManager__c`.
- **Terminated locations excluded from steps:** terminated locations never appear in the displayed record set (the Apex fetch omits them — §0.6.5/§0.6.6).
- **Graceful fallback:** a case not yet marked `PRM_UseCaseManagerAssociation__c = true` falls back to the legacy `PRM_CaseManager__c` filter, is flagged for backfill, and never errors.
- **No regression:** a never-overwritten case loads exactly as before.

**Submit-side note (App Review standalone; PSV + QC share one IP):** App Review writes via `PRM_ReviewParCaseRecordsUpdate` v15; **PSV and the QC Review share `PRM_ReviewPSVCaseRecordsUpdate` v26** (QC runs the `QCProceedTo` branch of the same IP, because QC is a stage of the PSV OmniScript). So CMA create-on-submit upkeep is implemented **once for App Review (v15)** and **once for PSV/QC together (v26)** — the QC branch inherits US9's v26 hooks rather than getting its own IP. (`PRM_SaveManualUpdatesQC` belongs to the separate, out-of-scope Manual-QC (PDM) flow, not the initial-cred QC Review.) Because the review-launch button is hidden when a terminated location exists (US8–US10), none of these submit IPs needs the v3.0 "don't false-positive on terminated locations at submit" guard as the primary defense — the reviewer never reaches submit with a live termination. The `PRMDREGetPracticeLocation` COUNTQUERY / EligibleForUpdate behaviour is retained as defense-in-depth only (CQ-F). (PDA/NMQC are non-blocking; terminated locations are simply excluded from their steps by the Apex fetch.)

---

# USER STORY US8: App Review — CMA Fetch (Baked) + Hide Review Button on Terminated Locations + CMA Upkeep at Submit

**Persona:** Credentialing Specialist
**Priority:** P0 — direct business requirement; resolves production blocker (IA-0000096229)
**OmniScript:** `PRM_InitialCredentialAppReview_English` (verify active version at build time)
**Review-launch surface:** `PRM_CaseManagerRecordPage` (App Review button via `prmGenericButtonLauncher` / flexcard) + `prmTerminatedLocationAlert` LWC (existing banner) + `PRM_TerminationAlertReviewStages__mdt`
**Integration Procedures:** App Review fetch `PRM_FetchFormDetails` **v31** (prepopulate via `PRM_FetchParDetailsParent` → `PRM_FetchParDetails`, calls the US14 fetch service); **submit `PRM_ReviewParCaseRecordsUpdateParent` → `PRM_ReviewParCaseRecordsUpdate` v15** (App Review's own record-update IP — **not** the PSV IP)
**Relevant Requirements:** v2.0 US8; v3.1 §0.6.5–§0.6.6

> **Dev scope (read this first):** This story has THREE responsibilities, all delivered by the App Review dev: **(1) Prepopulate (fetch baked in)** — load every App Review section through the US14 CMA fetch service (not by `PRM_CaseManager__c`), with terminated locations excluded from the returned set; **(2) Hide the review button** — hide the App Review launch button on the Case Manager record when the case has a terminated location (reuse the existing detection in `prmTerminatedLocationAlert` + the CMDT stage list), so the reviewer can never open the review with a live termination; **(3) Create on submit** — create CMAs for every new record the submit mints. Cover all objects, not just HCPF.

---

## Story

**As a** Credentialing Specialist,
**I want** App Review to prepopulate every section from my case's Case Manager Associations (with terminated locations filtered out), the App Review launch button to be hidden whenever my case has a terminated location, and every new record my submit creates to be tied to my case,
**So that** my data loads correctly after any overwrite, I'm stopped *before* I start a review that would fail, terminated locations never clutter the review, and records created during review never lose their case link.

**Why it matters:** In v3.0 reviewers could still open App Review with a terminated location and only hit a "Required Fields Missing" error at submit. The fix is to **gate at entry**: the Case Manager record already shows a terminated-locations banner (`prmTerminatedLocationAlert`), but the App Review button is still clickable — so reviewers waste a full review then fail. Hiding the launch button when a termination exists stops that wasted work. Separately, after a PDM/Provider-Change overwrite, App Review's prepopulate (`PRM_FetchFormDetails` v31) loses not just locations but provider, NPIs, taxonomy, addresses, identifiers, licenses, education and languages (§0.6.3) — fixed by resolving every section through the CMA. And App Review submit (`PRM_ReviewParCaseRecordsUpdate` v15 — App Review's own IP, reached through the App Review sub-OmniScripts) *creates* new taxonomy, license, education and HFN records (CAQH identifiers are added in the App Review sub-OS via `PRM_AddCAQHRecord`); without a CMA those are exposed to the same overwrite bug.

---

## Preconditions

- US6/US13 (CMA at submission) and US14 (CMA fetch service) are in place.
- The Case Manager (IndividualApplication) page already renders the `prmTerminatedLocationAlert` banner, and `PRM_TerminationAlertReviewStages__mdt` lists "App Review" among the PAR review stages (§0.6.6).

---

## (1) Objects to PREPOPULATE via CMA (App Review fetch `PRM_FetchFormDetails` v31)

**Replace each of these `PRM_CaseManager__c`-filtered DataRaptor extracts with the US14 Apex fetch** (Apex hydrates and returns the records — no DR; the shared read-side contract is documented under the retired US7). The Apex fetch **excludes terminated locations**, so they never reach the App Review steps. Field mapping reference: US13 matrix.

HealthcarePractitionerFacility, HealthcareFacility, HealthcareFacilityNetwork, HealthcareProviderTaxonomy, Address, Identifier, BusinessLicense, Account, **HealthcareProvider, HealthcareProviderNpi, PersonEducation, PersonLanguage, Location**.

## (2) Objects to CREATE CMAs for ON SUBMIT (`PRM_ReviewParCaseRecordsUpdate` v15 write branches)

After each **insert/post** branch (DataRaptor Post of new records / blank-Id upsert), call the creation service with the new Ids. Field mapping: US13 AC for each. **Branch names below were re-derived from `PRM_ReviewParCaseRecordsUpdate` v15** (App Review's actual submit IP); confirm exact element names at build time.

| Object minted at App Review submit | `PRM_ReviewParCaseRecordsUpdate` v15 write branch | Builder / payload key | Mapping |
|---|---|---|---|
| HealthcareProviderTaxonomy | `DRPostTaxonomy` (← `DRPTaxonomy` / `DRTTaxonomy`) | `practitionerTaxonomyData` → `createCMAForPractitionerTaxonomy` | AC-13.8 |
| BusinessLicense | `DRPostLicense` (← `DRPLicense` / `DRTLicenseCreation`; `PRM_OmniUtils.filterListToCreateLicense`) | `practitionerBusinessLicense` → `createCMAForBusinessLicense` | AC-13.12 |
| PersonEducation (ReCred) | `DRPostEducation` (← `DREDegreeRecords` / `DREInstitutionRecords`) | `personEducationData` → `createCMAForPersonEducation` 🆕 | AC-13.17 |
| HealthcareFacilityNetwork | sub-IP `PRM_ReviewHealthcareFacilityNetwork` (`IPReviewHealthCareFacilityNetwork` step) | network keys → network builder | AC-13.6 |
| Identifier (CAQH) | **created in the App Review sub-OS** (`PRM_CredApplicationReviewSubOS` / `…OSTxnyRole`) via `PRM_AddCAQHRecord` — not in this IP; hook the CMA there | identifier keys → identifier builder | AC-13.11 |
| HealthcarePractitionerFacility | ⚠ **not created in `PRM_ReviewParCaseRecordsUpdate`** (no HCPF write found). HCPF practice locations are minted at PAR submission (US6 scope) — confirm whether App Review ever inserts HCPF; if it does, locate the branch at build time | `adpData` → `createCMAForPractitionerPracticeLocation` | AC-13.3 |
| BoardCertification (ReCred, Tier-2) | verify branch in v15 | Tier-2 builder | §0.6.4 |

## Acceptance Criteria

**AC-8.0 — Every App Review section prepopulates via CMA (overwrite-proof)**

**Given** a case whose records were re-stamped by a later PDM/Provider-Change,
**When** the Credentialing Specialist opens App Review,
**Then** every section listed in "(1) Objects to PREPOPULATE" loads the correct records via the US14 CMA fetch service (not by `PRM_CaseManager__c`),
**And** the provider, NPIs, taxonomy, addresses, identifiers, licenses, education and languages sections are all complete — not just locations,
**And** for a non-CMA (un-backfilled) case the flow falls back to the legacy filter with no error.

**AC-8.0.1 — Terminated locations are not shown on any App Review step**

**Given** the case has one or more terminated locations (per the §0.6.6 predicate),
**When** App Review prepopulates,
**Then** no terminated location appears in the location/HCPF/HCF data on any App Review step (the US14 service excludes them from the active lists),
**And** only active locations are displayed and editable.

**AC-8.1 — Happy path: no terminated locations**

**Given** all of the case's locations are active,
**When** the Credentialing Specialist views the Case Manager record,
**Then** the App Review launch button is available and the review behaves exactly as before.

**AC-8.2 — App Review launch button hidden when a location is terminated**

**Given** at least one of the case's locations is terminated (per §0.6.6),
**When** the Credentialing Specialist views the Case Manager record,
**Then** the App Review launch button is hidden for that case (so the review cannot be started),
**And** the existing `prmTerminatedLocationAlert` banner explains which locations are terminated and what to do,
**And** no separate in-review notice screen is shown.

**AC-8.3 — App Review button reappears after the location is fixed**

**Given** the App Review button was hidden because of a terminated location,
**When** that location is reactivated (or removed) so the case has no terminated location,
**Then** the App Review launch button becomes available again,
**And** the banner clears,
**And** the review can be started and completed normally.

**AC-8.4 — Every new record created at submit is linked to the case (full CMA upkeep)**

**Given** an App Review submit that creates new records across the "(2) Objects to CREATE" set (HCPF, HFN, taxonomy, license, CAQH identifier, and ReCred education/board certification),
**When** the submit completes,
**Then** each newly created record — of **every** type in that set, not just HCPF — is tied to the case through a Case Manager Association using the US13 field mapping,
**And** records that were only updated (not newly created) get no additional association,
**And** the case remains marked as using Case Manager Associations.

**AC-8.5 — Records deleted during review do not leave dangling associations**

**Given** an App Review submit that deletes one or more practice-location records,
**When** the submit completes,
**Then** associations that pointed to the deleted records are cleaned up (or are knowingly retained as history per CQ-I),
**And** no association points to a non-existent record in a way that breaks downstream loads.

**AC-8.6 — Production regression resolved (IA-0000096229)**

**Given** the case from production defect IA-0000096229 has associations from backfill (US6) and one terminated location,
**When** the Credentialing Specialist views the Case Manager record,
**Then** the App Review button is hidden while the location is terminated (no failed review attempt),
**And** once the location is resolved, the button reappears and the review completes with no "Required Fields Missing" error.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FetchFormDetails` v31 + its CM-filtered extracts | IP — prepopulate (Apex) | **Replace** the `PRM_CaseManager__c`-filtered DataRaptor extracts (object list in §"(1) Objects to PREPOPULATE") with the US14 **Apex** fetch (Apex returns hydrated records — no DR); gate on `PRM_UseCaseManagerAssociation__c` with fallback | Drives AC-8.0. The big read-side change — do every object. Apex avoids the DR performance problems; active lists already exclude terminated locations (AC-8.0.1). |
| `PRM_CaseManagerRecordPage` (FlexPage) — App Review launch button | FlexPage — visibility | Add a visibility condition on the App Review launcher (`prmGenericButtonLauncher` / flexcard) so it is hidden when the case has a terminated location. Drive the condition from the **same** detection as `prmTerminatedLocationAlert` (§0.6.6 predicate) and the `PRM_TerminationAlertReviewStages__mdt` "App Review" stage entry | Drives AC-8.2–8.3. Reuses existing banner/CMDT; **no in-OmniScript submit block needed**. See CQ-H for the exact wiring (LWC-exposed flag vs. formula field). |
| `prmTerminatedLocationAlert` (LWC) | LWC — optional expose | If the button visibility cannot read the LWC result directly, expose `hasTerminatedLocations` (e.g., a record-level flag the FlexPage can bind) so the button-hide and the banner share one source of truth | Supports AC-8.2; avoids duplicate termination logic. |
| `PRM_ReviewParCaseRecordsUpdate` v15 — write branches | IP — add CMA step(s) | After **each** write branch in §"(2) Objects to CREATE" (taxonomy `DRPostTaxonomy`, license `DRPostLicense`, education `DRPostEducation`, HFN via `PRM_ReviewHealthcareFacilityNetwork`), call `createCaseManagerAssociation` with the new record Ids and the matching payload key. CAQH identifiers are created in the App Review **sub-OS** (`PRM_AddCAQHRecord`) — hook the CMA there | Drives AC-8.4. Hook the **insert/post branch**, not the update step. Reuse US13 builders. ⚠ This is App Review's own IP — **not** shared with PSV/QC (which both use `PRM_ReviewPSVCaseRecordsUpdate` v26); App Review needs its own upkeep here, PSV+QC share theirs in v26. |
| HCPF delete-cleanup path (v15) | IP — cleanup | When an HCPF is deleted during App Review, clean up CMAs whose `PRM_HealthcarePractitionerFacility__c` pointed to the deleted HCPF (lookup nulls on delete) — confirm the delete element name in v15 | Drives AC-8.5; behaviour per CQ-I. |

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ-H | How should the App Review button visibility read the terminated-location state — bind to a flag exposed by `prmTerminatedLocationAlert`, a roll-up/formula field on IndividualApplication, or a FlexPage visibility rule querying the same predicate? | Implementation path for the button-hide; must reuse §0.6.6, not duplicate it | Technical |
| CQ-I | When a record covered by a CMA is deleted during review, delete the orphaned CMA or retain it as history? | Data hygiene + downstream load correctness | Technical / BA |
| CQ-J | Stamp `PRM_RequestType__c` on review-created CMAs (e.g., 'App Review') to distinguish from submission-origin CMAs? | Reporting/filtering | BA |
| CQ-R | Should the button-hide also apply mid-flight if a location is terminated *after* a review starts (edge case), or only gate at launch? | Edge-case scope for AC-8.2 | Product / Technical |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Fetch wiring (all §"(1)" objects, terminated-excluded) | IP/DR | M | calls US14 service |
| Hide App Review launch button on terminated locations | FlexPage (+ optional LWC flag) | S–M | reuses existing banner/CMDT (§0.6.6) |
| CMA upkeep on v26 insert branches | IP steps | M–L | multiple insert branches (HCPF/HFN/taxonomy/license/identifier) |
| Deletion cleanup | IP/Apex | S–M | per CQ-I |
| Regression (ACs 8.0–8.6) | Manual | M | AI-estimated |

**Total Estimated Effort:** L (AI-estimated — validate with team). Lower UI cost than v2.0 (no notice component); button-hide reuses existing detection; added CMA-upkeep cost on submit.

---

# USER STORY US9: PSV Review — CMA Fetch (Baked) + Hide Review Button on Terminated Locations + CMA Upkeep at Submit

**Persona:** PSV Reviewer
**Priority:** P0
**OmniScript:** `PRM_PrimarySourceVerificationReview_English` (verify active version at build)
**Review-launch surface:** `PRM_CaseManagerRecordPage` (PSV button) + `prmTerminatedLocationAlert` + `PRM_TerminationAlertReviewStages__mdt` ("PSV" stage)
**Integration Procedures:** PSV fetch = `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` **v33**, which **wraps `PRM_FetchFormDetails` v31** (App-Review fetch, calls US14) and adds PSV extracts (`DRTurboGetAdverseReviewAction`, `DRGetContactInformation`) + `PRM_ReviewPSVCaseRecordsUpdate` **v26** save IP (**PSV's own** save IP — App Review uses `PRM_ReviewParCaseRecordsUpdate`; branches on `FlowType = 'PSV'`)
**Relevant Requirements:** v2.0 US9; v3.1 §0.6.5–§0.6.6

---

> **Dev scope:** Same three responsibilities as US8 — **prepopulate (fetch baked in)** every PSV section via the US14 service (terminated locations excluded), **hide the PSV review-launch button** when the case has a terminated location, **create** CMAs for every record minted at PSV submit. **What's inherited vs. not:** PSV's **fetch** wraps the App-Review fetch (`PRM_FetchParDetails` → `PRM_FetchFormDetails`), so converting that in US8 fixes the PSV read automatically (inherited). PSV's **submit is its OWN IP — `PRM_ReviewPSVCaseRecordsUpdate` v26 — NOT shared with App Review** (which uses `PRM_ReviewParCaseRecordsUpdate`); so PSV's create-on-submit CMA upkeep is **separate work in v26**, not inherited from US8. Plus the PSV button-visibility condition.

## Story

**As a** PSV Reviewer,
**I want** every PSV section to prepopulate from my case's Case Manager Associations (terminated locations excluded), the PSV launch button hidden when my case has a terminated location, and every record my submit creates linked to the case,
**So that** my verification loads completely after any overwrite, I never start a PSV that would fail at submit, terminated locations don't appear in my verification, and review-created records keep their case link.

**Why it matters:** PSV's screen read runs through `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33, which **internally calls the App-Review fetch `PRM_FetchFormDetails` v31** (see §0.6.3) — so PSV inherits App Review's entire `PRM_CaseManager__c`-scoped load set and the same overwrite bug, and is fixed automatically when US8 converts `PRM_FetchFormDetails` to the US14 Apex fetch. PSV submits through its **own** IP (`PRM_ReviewPSVCaseRecordsUpdate` v26) — **App Review uses a different submit IP (`PRM_ReviewParCaseRecordsUpdate`)**, so PSV does **not** inherit App Review's create-on-submit; PSV's CMA upkeep is its own work on v26 (same pattern as US8, different IP). PSV's own read additions are small: the fetch chain also pulls `PRM_AdverseActionReview__c` (`DRTurboGetAdverseReviewAction`, by `CaseManagerId`, recred QC-Review path) and the case manager's primary/secondary contact `Account`s (`DRGetContactInformation`). The button-hide gate is PSV-specific: the PSV launcher on `PRM_CaseManagerRecordPage` must be hidden on terminated locations using the same §0.6.6 detection ("PSV" is in the CMDT stage list).

## Preconditions

- US6/US13, US14, US8 in place (US8 establishes the prepopulate switch and the button-hide pattern; PSV **inherits the fetch** via the wrapped `PRM_FetchFormDetails`, **replicates** the button-hide for its launcher, and **implements its own** create-on-submit CMA upkeep in `PRM_ReviewPSVCaseRecordsUpdate` v26).

## Objects to PREPOPULATE / CREATE

- **Prepopulate (read):** same set as US8 §"(1)" (inherited via `PRM_FetchParDetails` wrapping the App-Review fetch `PRM_FetchFormDetails`, terminated locations excluded) **plus** PSV-specific fetch-chain extracts: `PRM_AdverseActionReview__c` (`DRTurboGetAdverseReviewAction`, CM-scoped by `CaseManagerId` — switch to CMA when a Tier-2 lookup exists, else leave legacy) and the primary/secondary contact `Account` read (`DRGetContactInformation`, keyed off the IA contact lookups, not `PRM_CaseManager__c` — no CMA change needed).
- **Create on submit:** the records PSV mints in **its own** `PRM_ReviewPSVCaseRecordsUpdate` v26 (HCPF, HFN, taxonomy, license, CAQH identifier, education/board cert) — same object set as App Review conceptually, but the **insert branches live in v26, not in App Review's `PRM_ReviewParCaseRecordsUpdate`**, so the CMA-upkeep hooks must be added to v26 separately. Confirm each branch in v26 at build time.

## Acceptance Criteria

> AC-8.0, AC-8.0.1 apply verbatim with PSV as the context: because PSV's fetch (`PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33) **wraps** the App-Review fetch `PRM_FetchFormDetails`, the full-object prepopulate (AC-8.0) and terminated-exclusion (AC-8.0.1) are **inherited** — verify under `FlowType='PSV'`. AC-8.4 (CMA upkeep) and AC-8.5 (deletion cleanup) are **NOT inherited**: PSV's submit runs in its own `PRM_ReviewPSVCaseRecordsUpdate` v26, so those hooks are implemented separately for v26 (see AC-9.2).

**AC-9.1 — PSV launch button hidden when a location is terminated**

**Given** a PSV case with at least one terminated location (per §0.6.6),
**When** the PSV Reviewer views the Case Manager record,
**Then** the PSV review-launch button is hidden for that case (so PSV cannot be started),
**And** the existing `prmTerminatedLocationAlert` banner identifies the terminated location,
**And** the button reappears once the location is reactivated/removed.

**AC-9.2 — Every new record created by PSV submit is linked to the case (PSV's own v26 IP)**

**Given** a PSV submit (`PRM_ReviewPSVCaseRecordsUpdate` v26) that creates new records (HCPF, HFN, taxonomy, license, CAQH identifier, education/board cert),
**When** the submit completes,
**Then** each new record of **every** type is tied to the case via a Case Manager Association (US13 mapping) — the CMA-upkeep hooks are added to **v26 specifically** (not inherited from App Review's `PRM_ReviewParCaseRecordsUpdate`),
**And** updated-only records get no extra association.

**AC-9.3 — Every PSV section prepopulates via CMA with terminated locations excluded (through the wrapped App-Review fetch)**

**Given** a PSV case whose records were overwritten,
**When** the reviewer opens PSV (for a case with no terminated locations, i.e., the button is available),
**Then** every section listed in §"Objects to PREPOPULATE" loads via the US14 Apex CMA fetch **because `PRM_FetchParDetails` calls `PRM_FetchFormDetails`** — i.e., the US8 conversion flows through to PSV with no separate PSV fetch rewrite,
**And** no terminated location appears on any PSV step (AC-8.0.1).

**AC-9.4 — PSV-specific fetch-chain extracts still load correctly**

**Given** a PSV (recred QC-Review-path) case,
**When** the reviewer opens PSV,
**Then** the `PRM_AdverseActionReview__c` section continues to load via `DRTurboGetAdverseReviewAction` (by `CaseManagerId`) — switched to the CMA only if/when a Tier-2 lookup exists, otherwise legacy filter, with no error,
**And** the primary/secondary contact `Account` read (`DRGetContactInformation`, keyed off the IndividualApplication contact lookups, **not** `PRM_CaseManager__c`) is unaffected and needs no CMA change.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33 (wraps `PRM_FetchFormDetails` v31) | IP — prepopulate (Apex) | Inherited from US8 §1 — `PRM_FetchParDetails` calls `PRM_FetchFormDetails`, so converting that to the US14 Apex fetch fixes PSV automatically; verify all objects load under PSV (no DR) with terminated locations excluded | Drives AC-9.3 |
| `PRM_FetchParDetails` v33 — PSV extracts (`DRTurboGetAdverseReviewAction`, `DRGetContactInformation`) | IP/DR — read | Confirm the `PRM_AdverseActionReview__c` extract (by `CaseManagerId`); switch to CMA if a Tier-2 lookup exists. Contact `Account` read is via IA lookups — no CMA change | Drives AC-9.4 |
| `PRM_CaseManagerRecordPage` (FlexPage) — PSV launch button | FlexPage — visibility | Hide the PSV launcher when the case has a terminated location, using the same §0.6.6 detection as US8 (CMDT "PSV" stage) | Drives AC-9.1. Same wiring choice as CQ-H. |
| `PRM_ReviewPSVCaseRecordsUpdate` v26 — write | IP — add CMA steps (PSV's own IP) | Add `createCaseManagerAssociation` after **each** insert branch in v26 (HCPF, HFN, taxonomy, license, CAQH identifier, education/board cert). Same **pattern** as US8 but a **different IP** — not inherited; confirm branch names in v26 | Drives AC-9.2 |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Prepopulate verification (all objects under PSV, terminated-excluded) | IP/DR | S | inherited via wrapped `PRM_FetchFormDetails` |
| Hide PSV launch button on terminated locations | FlexPage | S | reuses US8 pattern + §0.6.6 |
| CMA upkeep (all objects) on `PRM_ReviewPSVCaseRecordsUpdate` v26 | IP | M | **own IP — NOT inherited**; same pattern as US8, separate insert branches |
| Regression | Manual | M | confirm `FlowType='PSV'` for every object |

**Total Estimated Effort:** M (AI-estimated — validate with team; fetch inherited from US8, but submit-side CMA upkeep is PSV's own work in v26).

---

# USER STORY US10: QC Review — CMA Fetch (Baked, via the PSV OmniScript) + Hide Review Button on Terminated Locations + CMA Upkeep at Submit

**Persona:** QC Reviewer
**Priority:** P0
**OmniScript:** `PRM_PrimarySourceVerificationReview_English` — **QC Review is a stage of the PSV OmniScript, NOT a separate OmniScript.** The QC steps (`SetRecordPSVQC`, `SetQCReadyForCommittee`, `SetQCReadyForMedicalReview`, `SetRecordQCReturnTo`) and the "PSV QC" submit branch live inside this same OmniScript (verified 2026-06-10). ⚠ `PRM_ManualUpdatesQC_English` / `PRM_InitManualUpdatesQC` / `PRM_SaveManualUpdatesQC` are a **different** flow — the "Manual QC" button / Manual-Updates (PDM) "Network Management QC" process — and are **out of scope** for the initial-cred pipeline these stories cover.
**Review-launch surface:** `PRM_CaseManagerRecordPage` (QC Review button) + `prmTerminatedLocationAlert` + `PRM_TerminationAlertReviewStages__mdt` ("QC" stage)
**Integration Procedures:** QC **fetch is SHARED with PSV** — `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` **v33** (which wraps the App-Review fetch `PRM_FetchFormDetails` v31); QC **submit is SHARED with PSV** — `PRM_ReviewPSVCaseRecordsUpdate` **v26** (the `QCProceedTo` / "PSV QC" branch)
**Relevant Requirements:** v2.0 US10; v3.1 §0.6.5–§0.6.6

> **Dev scope:** Because QC runs inside the **same OmniScript, fetch chain, and submit IP as PSV (US9)**, both the **prepopulate** (Apex fetch baked in, terminated locations excluded) and the **create-on-submit** CMA upkeep are **inherited from US9** — converting `PRM_FetchFormDetails`/`PRM_FetchParDetails` to the US14 Apex fetch (US8/US9) fixes the QC read automatically, and the CMA-upkeep hooks added to `PRM_ReviewPSVCaseRecordsUpdate` v26 (US9) also cover the QC submit branch. US10's **net-new** work is the **QC review-button-hide** on terminated locations and verifying every section/branch fires under the QC (`QCProceedTo`) path.

---

## Story

**As a** QC Reviewer,
**I want** every QC section to prepopulate from my case's Case Manager Associations (terminated locations excluded), the QC Review launch button hidden when my case has a terminated location, and every record my submit creates linked to the case,
**So that** QC sees the complete, correct case data after any overwrite, I never start a QC that would fail at submit, terminated locations don't appear in the QC review, and new records keep their case link.

**Why it matters:** QC Review reads and writes through the **same PSV OmniScript** the PSV Reviewer used. Its screen loads via `PRM_FetchParDetailsParent` → `PRM_FetchParDetails` v33 (which internally calls the App-Review fetch `PRM_FetchFormDetails` v31), so QC sees the same `PRM_CaseManager__c`-scoped load set as App Review/PSV and is broken by the same overwrite — and is fixed automatically when US8/US9 convert that fetch to the US14 Apex service. QC submits through the **same** IP as PSV (`PRM_ReviewPSVCaseRecordsUpdate` v26, `QCProceedTo` branch), so the create-on-submit CMA upkeep added in US9 already covers the QC branch. The only QC-specific work is the QC review-button-hide on terminated locations.

## Preconditions

- US6/US13, US14, US8, **US9** in place (US9 establishes the shared PSV fetch + v26 submit upkeep that QC inherits).

## (1) Objects to PREPOPULATE via CMA (QC = the PSV fetch chain, inherited)

QC loads the **same object set as App Review (US8 §"(1)") plus the PSV extras (US9)**, because it runs through the same `PRM_FetchParDetails` v33 → `PRM_FetchFormDetails` v31 chain. There is **no separate QC reader** — converting that chain to the US14 Apex fetch in US8/US9 (terminated locations excluded) fixes the QC read automatically. QC's net-new prepopulate work is therefore **verification under the QC (`QCProceedTo`) path**, not a new set of extracts.

## (2) Objects to CREATE CMAs for ON SUBMIT (PSV's `PRM_ReviewPSVCaseRecordsUpdate` v26 — QC branch)

Same insert branches as US9 §"(2)" (HCPF, HFN, taxonomy, license, CAQH identifier; ReCred education/board cert) — they live in the **shared** `PRM_ReviewPSVCaseRecordsUpdate` v26, so the CMA-upkeep hooks added for PSV (US9) **also cover the QC submit branch**. Confirm the `QCProceedTo` path exercises the same insert branches at build time.

## Acceptance Criteria

> AC-8.0.1 applies verbatim with QC as the context (terminated-exclusion). AC-8.4–AC-8.5 (CMA upkeep + deletion cleanup) are **inherited from US9** — they run in the shared v26 submit IP and are not re-implemented for QC.

**AC-10.0 — Every QC section prepopulates via CMA (the full set, terminated-excluded)**

**Given** a QC case whose records were overwritten by a later PDM/Provider-Change,
**When** the QC Reviewer opens the case (no terminated locations → button available),
**Then** every section listed in §"(1)" loads the correct records via the **shared PSV Apex CMA fetch** (`PRM_FetchParDetails` → `PRM_FetchFormDetails`, converted in US8/US9), exercised under the QC (`QCProceedTo`) path,
**And** all of provider, NPIs, taxonomy, addresses, identifiers, licenses, education, languages, location, contact profile, provider feature, program participation, association and info-code sections are complete,
**And** no terminated location appears on any QC step (AC-8.0.1),
**And** a non-CMA case falls back to legacy filters with no error.

**AC-10.1 — QC Review launch button hidden when a location is terminated**

**Given** a QC case with at least one terminated location (per §0.6.6),
**When** the QC Reviewer views the Case Manager record,
**Then** the QC Review launch button is hidden for that case (so QC cannot be started),
**And** the existing `prmTerminatedLocationAlert` banner identifies the terminated location,
**And** the button reappears once the location is reactivated/removed.

**AC-10.2 — Every new record created by QC submit is linked to the case (inherited from US9's v26 hooks)**

**Given** a QC submit (`PRM_ReviewPSVCaseRecordsUpdate` v26, `QCProceedTo` branch) that creates new records across the §"(2)" set,
**When** the submit completes,
**Then** each new record of **every** type is tied to the case via a CMA (US13 mapping) through the **same v26 CMA-upkeep hooks added in US9** — not re-implemented for QC; verify the QC branch exercises them.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FetchParDetails` v33 → `PRM_FetchFormDetails` v31 (shared with PSV) | IP — prepopulate (Apex) | Inherited from US8/US9 — verify the §"(1)" object set loads via the US14 **Apex** fetch (no DR, terminated-excluded) under the QC (`QCProceedTo`) path | Drives AC-10.0. No separate QC reader exists. |
| `PRM_CaseManagerRecordPage` (FlexPage) — QC Review launch button | FlexPage — visibility | Hide the QC Review launcher when the case has a terminated location, using the same §0.6.6 detection as US8 (CMDT "QC" stage) | Drives AC-10.1. Same wiring choice as CQ-H. **Only QC-specific work.** |
| `PRM_ReviewPSVCaseRecordsUpdate` v26 — write (shared with PSV) | IP — verify CMA steps | The `createCaseManagerAssociation` hooks added in US9 sit on the v26 insert branches and also cover the QC (`QCProceedTo`) submit branch — verify, don't re-add | Drives AC-10.2 (inherited). |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| QC prepopulate | IP | — | inherited from US8/US9 (shared PSV fetch chain) |
| Hide QC Review launch button on terminated locations | FlexPage | S | reuses US8 pattern + §0.6.6 |
| CMA upkeep | IP | — | inherited from US9 (shared v26 submit IP) |
| Regression (QC path) | Manual | M | verify every section/branch under `QCProceedTo` |

**Total Estimated Effort:** S–M (AI-estimated — validate with team; QC inherits PSV's fetch + submit, so the bulk of the work is in US8/US9).

---

# USER STORY US11: PDA Review — CMA Fetch (Baked, Apex) + Exclude Terminated Locations + Suppress Banner at PDA Stage + CMA Upkeep at Submit

**Persona:** PDA Specialist (Provider Data Analyst)
**Priority:** P1
**OmniScript:** `PRM_InitialCredPDAQC_English` (FlowType = "PDA Review and Update")
**Banner surface:** `prmTerminatedLocationAlert` (on `PRM_CaseManagerRecordPage`) — **suppressed** at the PDA stage + `PRM_TerminationAlertReviewStages__mdt` ("PDA Review" stage)
**Integration Procedures:** `PRM_FetchFormPDAReview` v24 (fetch, calls US14 Apex service) + `PRM_InitialCredPDAReviewUpdate` v23 → `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7 + `PRM_PNCPDAUtility.PNCPDABatch` (submit)
**Relevant Requirements:** v2.0 US11; v3.1 §0.6.5–§0.6.6

> **Dev scope:** **(1) Prepopulate (Apex fetch baked in)** every PDA section through the US14 Apex service with terminated locations excluded; **(2) Suppress the `prmTerminatedLocationAlert` banner** when the case's current stage is "PDA Review and Update" — **the PDA Review button is NOT hidden** and the reviewer works the case normally; **(3) Create on submit** CMAs for every record the SubIPUpdate v7 IP and the PNC batch mint.
>
> **Behaviour vs. v3.0:** v3.0 showed terminated locations read-only with a badge on the PDA step. v3.1 instead **excludes terminated locations entirely** from the PDA steps (the Apex fetch omits them). PDA stays **non-blocking** (no button-hide) — consistent with it being the last step before activation — and the warning banner is **hidden** at this stage to avoid confusing a reviewer who has nothing to act on.

---

## Story

**As a** PDA Specialist,
**I want** every PDA section to load (in Apex) through the immutable Case Manager Association link with terminated locations excluded, the terminated-location banner suppressed at my stage, and every record my submit creates linked to the case,
**So that** I always see the complete, correct, active-only case data, I'm not interrupted by a banner about locations I can't act on, and review-created records keep their case link.

**Why it matters:** The PDA fetch (`PRM_FetchFormPDAReview` v24) filters its sections by `PRM_CaseManager__c` via DataRaptors that perform poorly; after a PDM overwrite the PDA also sees empty location, facility, network, provider and identifier sections. Resolving through the CMA **in Apex** fixes both. PDA is the last step before activation, so it must NOT be blocked; terminated locations simply never appear on its steps, and the stop-work banner (meant for App Review/PSV/QC) is suppressed here. PDA submit creates new HCPF/HFN/Address/CAQH-identifier records (via `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7) and, on the PNC path, via `PRM_PNCPDAUtility.PNCPDABatch` — all needing CMA coverage.

## Preconditions

- US6/US13, US14 in place.
- `PRM_TerminationAlertReviewStages__mdt` lists "PDA Review" among the PAR stages (§0.6.6); the banner-suppression config recognizes the "PDA Review and Update" stage.

## (1) Objects to PREPOPULATE via CMA (PDA fetch `PRM_FetchFormPDAReview` v24)

**Replace each `PRM_CaseManager__c`-filtered DataRaptor extract with the US14 Apex fetch** (Apex returns hydrated records — no DR; terminated locations excluded):

HealthcareFacility, HealthcarePractitionerFacility, HealthcareFacilityNetwork, HealthcareProvider, Identifier.

## (2) Objects to CREATE CMAs for ON SUBMIT

| Object minted at PDA submit | Where | Builder / payload key | Mapping |
|---|---|---|---|
| HealthcarePractitionerFacility | `PRMLoadRelatedRecordsForPNC` (new HCPF) | `adpData` → `createCMAForPractitionerPracticeLocation` | AC-13.3 |
| HealthcareFacilityNetwork | `PRMDRLoadNPITaxHCFNPNC` (new HFN) | network keys → network builder | AC-13.6 |
| Address | `PRMDRLoadAddressForPNC` (new) | `newlyAddedAddressData` → Address builder | AC-13.10 |
| Identifier (CAQH) | `PRMLoadOldCaqhRecord` (new) | identifier keys → identifier builder | AC-13.11 |
| HCPF / HFN / taxonomy (PNC path) | `PRM_PNCPDAUtility.PNCPDABatch` (Apex) | call service from batch with new Ids | AC-13.3/13.6/13.8 |

## Acceptance Criteria

**AC-11.0 — Every PDA section prepopulates via Apex CMA fetch (overwrite-proof, terminated-excluded)**

**Given** the case's records were overwritten by PDM and associations exist,
**When** the PDA Specialist opens the PDA Review,
**Then** every section in §"(1)" (facility, locations, networks, provider, identifiers) loads via the US14 **Apex** CMA fetch (no DataRaptor extracts), not just locations,
**And** no terminated location appears on any PDA step (the Apex fetch excludes them),
**And** a non-CMA case falls back to the legacy filter (in Apex) with no error.

**AC-11.1 — PDA loads active HCPF correctly after overwrite**

**Given** the case's locations were overwritten by PDM and associations exist,
**When** the PDA Specialist opens the PDA Review,
**Then** the full correct set of the case's **active** locations is displayed (terminated ones excluded).

**AC-11.2 — PDA is NOT blocked; banner suppressed at the PDA stage**

**Given** at least one location is terminated (per §0.6.6),
**When** the PDA Specialist views the Case Manager record and opens the PDA Review,
**Then** the PDA Review and Update launch button remains available (PDA is never blocked by a termination),
**And** the `prmTerminatedLocationAlert` banner does **not** render while the case's stage is "PDA Review and Update",
**And** no terminated location is shown on any PDA step,
**And** the PDA Specialist completes and submits the review normally.

**AC-11.3 — Submit advances to Network Management QC normally**

**Given** a PDA case (whether or not it has terminated locations, which are excluded from the steps),
**When** the PDA Specialist completes and submits the PDA Review,
**Then** the PDA case closes and a Network Management QC case is created,
**And** active-location records are updated normally,
**And** terminated locations are neither displayed nor activated.

**AC-11.4 — No terminated locations (regression)**

**Given** all locations are active,
**When** the PDA Specialist views the Case Manager record and opens the PDA Review,
**Then** the button is available, no banner is shown, and the review behaves exactly as before.

**AC-11.5 — Mixed locations exclude terminated ones from the PDA steps**

**Given** a case with three locations of which one is terminated,
**When** the PDA Specialist opens the PDA Review,
**Then** only the two active locations are shown and are editable,
**And** the terminated location is never rendered on a PDA step,
**And** the banner is suppressed and the PDA can be completed and submitted.

**AC-11.6 — Every new record created at PDA submit is linked to the case (full CMA upkeep)**

**Given** a PDA submit that creates new records across the §"(2)" set — HCPF, HFN, Address, CAQH identifier (via `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7), and HCPF/HFN/taxonomy (via `PRM_PNCPDAUtility.PNCPDABatch` on the PNC path),
**When** the submit completes,
**Then** each newly created record of **every** type is tied to the case through a Case Manager Association using the US13 mapping,
**And** records that were only updated (not newly created) get no additional association,
**And** the case remains marked as using Case Manager Associations.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FetchFormPDAReview` v24 + CM-filtered extracts | IP — prepopulate (Apex) | **Replace** the §"(1)" section DataRaptor extracts (HCF, HCPF, HFN, HealthcareProvider, Identifier) with the US14 **Apex** fetch (hydrated records, no DR, terminated-excluded); gate on `PRM_UseCaseManagerAssociation__c = true` AND RecordType PAR/PNC | Drives AC-11.0–11.1. Do every object, not just HCPF (seq 5). |
| `prmTerminatedLocationAlert` (LWC) — banner suppression | LWC — visibility | Add a stage check so the banner does **not** render when the IndividualApplication's current stage/status is "PDA Review and Update" (CMDT-driven, §0.6.6). The PDA launch button on `PRM_CaseManagerRecordPage` is **left unchanged** (no hide gate). | Drives AC-11.2, 11.4. **Replaces** v3.0's in-flow read-only-rows approach; terminated exclusion is handled by the Apex fetch (AC-11.0). |
| `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7 — insert branches | IP — add CMA step(s) | After **each** insert branch in §"(2)" (`PRMLoadRelatedRecordsForPNC` new-HCPF, `PRMDRLoadNPITaxHCFNPNC` new-HFN, `PRMDRLoadAddressForPNC` new Address, `PRMLoadOldCaqhRecord` new CAQH), call `createCaseManagerAssociation` with the new Ids + matching payload key | Drives AC-11.6 (non-PNC path). Hook the insert branch (blank-Id upserts). Reuse US13 builders. |
| `PRM_PNCPDAUtility.PNCPDABatch` (Apex) | Apex — add CMA creation | On the PNC path, record creation is in this batch (opaque to the IP); create CMAs there for newly inserted HCPF/HFN/taxonomy | Drives AC-11.6 (PNC path). Requires reading/editing the batch class. |

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ-S | *(resolved in v3.1)* PDA is **non-blocking** — no button-hide; terminated locations are excluded from the steps and the banner is suppressed at the PDA stage. No open question. | — | Product / BA |
| CQ-S1 | How is the case's "current stage" read in `prmTerminatedLocationAlert` for suppression — IndividualApplication `Status`, a CaseType field, or the CMDT stage list? Confirm the exact field/value for "PDA Review and Update". | Drives the banner-suppression condition | Technical / BA |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Apex fetch wiring (all §"(1)" objects, terminated-excluded) | IP | M | HCF/HCPF/HFN/Provider/Identifier — replaces DR extracts |
| Remove per-section DR extracts (PDA fetch) | IP/DR | M | DR→Apex; perf win |
| Suppress `prmTerminatedLocationAlert` banner at PDA stage (no button-hide) | LWC | S | reuses §0.6.6 detection + stage check |
| CMA upkeep on SubIPUpdate v7 insert branches | IP steps | M | new HCPF/HFN/Address/Identifier |
| CMA upkeep in `PRM_PNCPDAUtility.PNCPDABatch` | Apex | M | PNC path only |
| Regression (all ACs) | Manual | L | AI-estimated |

**Total Estimated Effort:** L (AI-estimated — validate with team).

---

# USER STORY US12: Network Management QC — Inherited CMA Fetch (Baked, Apex) + Exclude Terminated Locations + Suppress Banner at NMQC Stage

**Persona:** Network Management QC Specialist
**Priority:** P1
**OmniScript:** `PRM_InitialCredPDAQC_English` (FlowType = "Network Management QC")
**Banner surface:** `prmTerminatedLocationAlert` (on `PRM_CaseManagerRecordPage`) — **suppressed** at the NMQC stage + `PRM_TerminationAlertReviewStages__mdt` ("NMQC" stage)
**Integration Procedures:** `PRM_FetchFormPDAReview` v24 (fetch — SHARED with PDA, calls US14 Apex service) + `PRM_InitialCredPDAReviewUpdate` (submit — SHARED with PDA)
**Relevant Requirements:** v2.0 US12; v3.1 §0.6.5–§0.6.6

---

> **Dev scope:** NMQC shares PDA's Apex fetch (`PRM_FetchFormPDAReview` v24) and submit chain (`PRM_InitialCredPDAReviewUpdate` v23 → SubIPUpdate v7 + PNC batch), so the full-object **prepopulate** (US11 §1, terminated-excluded, Apex) and **create-on-submit** (US11 §2) are inherited automatically. US12's net-new work is **suppressing the `prmTerminatedLocationAlert` banner at the NMQC stage** (NMQC is **NOT** button-gated — the launcher is unchanged) + outcome-path regression — and verifying every inherited object fires under FlowType = "Network Management QC".

## Story

**As a** Network Management QC Specialist,
**I want** the same CMA-stable, Apex-loaded full-section view with terminated locations excluded, the terminated-location banner suppressed at my stage, and the create-on-submit CMA upkeep PDA gets,
**So that** I have full, active-only visibility when deciding QC Completed vs. Errors Found, I'm not interrupted by a banner about locations I can't act on, and records created during my review keep their case link.

**Why it matters:** Investigation confirmed NMQC has no separate IP — it shares `PRM_FetchFormPDAReview` v24 and `PRM_InitialCredPDAReviewUpdate` with PDA and branches on FlowType. So US11's full-object **Apex** CMA load (terminated-excluded) **and** create-on-submit upkeep are inherited automatically; US12's net-new work is the FlowType-/CMDT-gated banner suppression plus outcome-path regression. Like PDA, NMQC is **non-blocking** — terminated locations are simply excluded, not gated.

## Preconditions

- US6/US13, US14, US11 in place.
- `PRM_TerminationAlertReviewStages__mdt` lists "NMQC" among the PAR stages (§0.6.6); the banner-suppression config recognizes the "Network Management QC" stage.

## Objects to PREPOPULATE / CREATE

- **Prepopulate (read):** same set as US11 §"(1)" — HealthcareFacility, HealthcarePractitionerFacility, HealthcareFacilityNetwork, HealthcareProvider, Identifier — inherited via the shared v24 **Apex** fetch (terminated locations excluded).
- **Create on submit:** same set as US11 §"(2)" — HCPF, HFN, Address, CAQH identifier, + PNC-path HCPF/HFN/taxonomy — inherited via the shared submit chain.

## Acceptance Criteria

**AC-12.1 — NMQC loads every section via Apex CMA fetch, terminated-excluded (inherited, regression)**

**Given** the case's records were overwritten by PDM and associations exist,
**When** the NMQC Specialist opens the Network Management QC case,
**Then** every section in US11 §"(1)" (facility, locations, networks, provider, identifiers) displays correctly via the **Apex** CMA fetch (inherited from US11's fetch change, no DR), not just locations,
**And** no terminated location appears on any NMQC step.

**AC-12.2 — NMQC is NOT blocked; banner suppressed at the NMQC stage**

**Given** at least one location is terminated (per §0.6.6),
**When** the NMQC Specialist views the Case Manager record and opens the NMQC case,
**Then** the Network Management QC launch button remains available (NMQC is never blocked by a termination),
**And** the `prmTerminatedLocationAlert` banner does **not** render while the case's stage is "Network Management QC",
**And** no terminated location is shown on any NMQC step,
**And** the NMQC Specialist completes the review normally.

**AC-12.3 — QC Completed unaffected**

**Given** an NMQC case (terminated locations excluded from the steps),
**When** the NMQC Specialist selects "QC Completed" and submits,
**Then** the case is approved and completed normally.

**AC-12.4 — Errors Found with note**

**Given** an NMQC case,
**When** the NMQC Specialist selects "Errors Found", adds a note, and submits,
**Then** the case returns to PDA as a new Returned case with the note visible,
**And** no error occurs.

**AC-12.5 — No terminated locations (regression)**

**Given** all locations are active,
**When** the NMQC Specialist views the Case Manager record,
**Then** the NMQC button is available, no banner is shown, and all outcome paths behave exactly as before.

**AC-12.6 — Every new record created at NMQC submit is linked to the case (inherited, full set)**

**Given** an NMQC submit that creates new records across the US11 §"(2)" set through the shared submit chain,
**When** the submit completes,
**Then** each newly created record of **every** type is tied to the case via a Case Manager Association (inherited from US11's `SubIPUpdate` v7 / PNC-batch CMA steps, US13 mapping),
**And** updated-only records get no extra association.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FetchFormPDAReview` v24 (shared) | IP — prepopulate (Apex) | Inherited from US11 §1 — verify all §"(1)" objects load via the US14 Apex fetch (no DR, terminated-excluded) under FlowType = "Network Management QC" | Drives AC-12.1 (inherited). |
| `prmTerminatedLocationAlert` (LWC) — banner suppression | LWC — visibility | Inherited from US11's stage-check change — add "Network Management QC" to the suppressed stages so the banner does not render at the NMQC stage. The NMQC launcher on `PRM_CaseManagerRecordPage` is **left unchanged** (no hide gate). | Drives AC-12.2, 12.5. **Replaces** v3.0's in-flow informational banner. |
| `PRM_InitialCredPDAReviewUpdate` v23 chain (shared with PDA) | IP — reuse US11 CMA steps | Full-object CMA upkeep on insert branches inherited via the shared submit chain | Drives AC-12.6 (inherited). |
| NMQC outcome paths (QC Completed / Errors Found / Rebuttal) | OmniScript — verify | Confirm outcome Set Values and the submit IP behave normally for active-only cases | Drives AC-12.3–12.5. Verification, not new logic. |

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Suppress `prmTerminatedLocationAlert` banner at NMQC stage (no button-hide) | LWC | S | inherits US11 stage-check; add NMQC stage |
| Outcome-path regression | Manual | M | AI-estimated |

**Total Estimated Effort:** S–M (AI-estimated — validate with team; bulk of work is US11).

---

# USER STORY US13: Extend CMA Schema + Creation Service to Capture Every Case-Scoped Record

**Persona:** Platform / Developer (value accrues to every reviewer downstream)
**Priority:** P0 — without this, PAR-created records other than HCPF are still orphaned by overwrites
**OmniScript:** none (deliberately — all logic is Apex, reused by every flow)
**Apex:** `PRM_CaseManagerAssociationService` + the three builders + `PRM_CMARecordTypeHelper`; new `objects/PRM_CaseManagerAssociation__c/fields/*` + recordTypes
**Relevant Requirements:** §0.6.2, §0.6.4

---

## Story

**As a** developer maintaining the Case Manager Association model,
**I want** the CMA object and the creation service to be able to capture **every** case-scoped record a guided flow creates — not just the practice-location/HCPF link,
**So that** no matter which record a later PDM/Provider-Change request re-stamps, the originating case can still find all of its records, across PAR, off-cycle, ancillary, recred, and re-assessment.

**Why it matters:** §0.6.2 shows PAR creates seven case-scoped record types with **no** CMA lookup (HealthcareProvider, HealthcareProviderNpi, PersonEducation, PersonLanguage, Location, ContactProfile, PRM_InfoCodeAssignment__c). §0.6.3 proves all of them are loaded by `PRM_CaseManager__c` in App Review and/or QC — so the overwrite bug orphans them exactly like HCPF. Covering only HCPF (US6) fixes the location section but leaves provider/NPI/education/language/profile/info-code sections exposed.

## Scope & Preconditions

- In scope: add the **Tier-1** lookups (7) needed for PAR; design the **Tier-2** lookups (per §0.6.4) for the other flows behind the same pattern.
- Each new lookup: `deleteConstraint=SetNull`, `relationshipName=Case_Manager_Associations`, + a matching RecordType + a builder method + a service routing key.
- **The field mappings below for the 13 EXISTING objects are extracted verbatim from the current builders** (`PRM_CaseManagerAssociationDirectBuilder`, `…AddressBuilder`, `…NetworkBuilder`). Devs must preserve them when wiring PAR; they are the contract.

### Field-mapping legend (applies to every CMA record)

Every `PRM_CaseManagerAssociation__c` record, regardless of type, sets these three "universal" fields. Object-specific fields are layered on top.

| CMA field | Meaning | Rule |
|---|---|---|
| `PRM_CaseManager__c` | Master-detail → the case (`IndividualApplication`) | **ALWAYS required.** = the case manager Id passed to the service. A record with no parent cannot be inserted. |
| `RecordTypeId` | The CMA RecordType for this object | Resolved via `PRM_CMARecordTypeHelper.getCaseManagerAssociationRecordTypeId('<DevName>')`. One per object (see table). |
| `<primary lookup>` | The created record being captured | = the created record's Id. Skip the row if the Id is blank/non-string. |
| `PRM_RequestType__c` | Optional text tag | Set only where the table says so. |
| `<secondary lookup(s)>` | Context links (facility/account) | Set only where the table says so; null otherwise. |

### Master field-mapping matrix — every object in scope

> **Source key:** "✅ exists" = builder already implements this exact mapping (verify, don't rebuild). "🆕 new" = lookup + RecordType + builder method to be created in this story.

| # | Object captured | Primary lookup (= record Id) | RecordType (DeveloperName) | Secondary lookup(s) | `PRM_RequestType__c` | Service payload key → builder | Status |
|---|---|---|---|---|---|---|---|
| 1 | HealthcarePractitionerFacility (HCPF) | `PRM_HealthcarePractitionerFacility__c` | `Practitioner_Practice_Location` | — | — | `adpData` → `createCMAForPractitionerPracticeLocation` | ✅ exists |
| 2 | HealthcareFacility (practice location) | `PRM_HealthcareFacility__c` | `PRM_PracticeLocation` | — | `'Terminate Current Office Information'` if payload has `PRM_EffectiveTo__c`, else `'Remove Practitioner'` | `lmsPLCOI` → `createCMAForPracticeLocation` | ✅ exists |
| 3 | HealthcareFacilityNetwork (as Practice-Location Taxonomy) | `PRM_HealthcareFacilityNetwork__c` | `Practice_Location_Taxonomy` | — | from payload `PRM_RequestType__c` | `addPracLocTaxonomyData` / `terminatedPracLocTaxonomyData` → `createCMAForPracticeLocationTaxonomy` | ✅ exists |
| 4 | HealthcareFacilityNetwork (as Practice-Location Network / PPLTN) | `PRM_HealthcareFacilityNetwork__c` | RT by HFN.RecordType.DeveloperName: `PRM_FacilityPractitionerTxNw`→`Practitioner_at_Practice_Location_Taxonomy_and_Network`; `PRM_FacilityNw`→`Practice_Location_Network`; `PRM_FacilityTx`→`Practice_Location_Taxonomy` | `PRM_HealthcareFacility__c` = HFN.HealthcareFacilityId; `PRM_Account__c` = HFN.Practitioner.AccountId | optional (from payload in TxNetwork variant) | `practitionerPPLTNData` / `addRemoveNetworksToUpdate` / `pracLocDirectoryIndicatorData` / `panelUpdateStatusData` → Network builders | ✅ exists |
| 5 | HFN as PPLTN (payload carries PractitionerId) | `PRM_HealthcareFacilityNetwork__c` | `Practitioner_at_Practice_Location_Taxonomy_and_Network` | `PRM_HealthcareFacility__c` = payload `HealthcareFacilityId`; `PRM_Account__c` = Account resolved from `PractitionerId`(PersonContact)→Account | — | `pracLocPPLTNData` / `removedPracLocPPLTNData` → `createCMAForPractitionerAtPracticeLocationTaxonomyAndNetwork` | ✅ exists |
| 6 | HealthcareProviderTaxonomy (practitioner taxonomy) | `PRM_HealthcareProviderTaxonomy__c` | `Healthcare_Provider_Taxonomy` | — | — | `practitionerTaxonomyData` / `updatedPractitionerTaxonomyData` → `createCMAForPractitionerTaxonomy` | ✅ exists |
| 7 | PRM_HealthcareFacilityAssociation__c (practice-location association) | `PRM_HealthcareFacilityAssociation__c` | `Practice_Location_Association` | — | `'Capitation Site'` for the cap-site variant; else none | `praclocAssociationData`/`pracLocContractTo` & `capSite` → `createCMAForPracticeLocationAssociation[CapSite]` | ✅ exists |
| 8 | Address | `PRM_Address__c` | `Practice_Location_Address` | `PRM_HealthcareFacility__c` = resolved via Address.ParentId(Location)→HealthcareFacility.LocationId | from payload `PRM_RequestType__c` | `mailingBillingAddressData`/`newlyAddedAddressData`/`addressAddCOI`/`addressUpdateCOI`/`lmsAddressData` → Address builder | ✅ exists |
| 9 | Identifier (CAQH / Tax / Medicare) | `PRM_Identifier__c` | `Identifier` | — | — | `oldTaxId`+`newTaxId` / `medicareData` → `createCMAForIdentifiers`/`createCMAForMedicare` | ✅ exists |
| 10 | BusinessLicense | `PRM_BusinessLicense__c` | `Business_License` | — | — | `practitionerBusinessLicense` → `createCMAForBusinessLicense` | ✅ exists |
| 11 | PRM_ProviderFeature__c | `PRM_ProviderFeature__c` | `Provider_Feature` | — | — | `pracProviderFeatureCreationData[Update]` → `createCMAForProviderFeature` | ✅ exists |
| 12 | PRM_ProgramParticipation__c | `PRM_ProgramParticipation__c` | `Program_Participation` | — | — | `vendorProgParticipationData`/`pracLocProgramParticipation` → `createCMAForProgramParticipation` | ✅ exists |
| 13 | Account (practitioner / vendor) | `PRM_Account__c` | `PRM_Practitioner` (default) or `PRM_Vendor` (when payload `RecordType == 'Vendor'`) | — | from payload `RequestType` | `lmsAccountsCOI` / `VendorId` / `lmsPLRemovePrac` → `createCMAForTermedAccounts`/`createCMAForLMSRecords` | ✅ exists |
| 14 | **HealthcareProvider** | `PRM_HealthcareProvider__c` 🆕 | `Healthcare_Provider` 🆕 | `PRM_Account__c` = provider's Account (if resolvable) | — | `healthcareProviderData` → `createCMAForHealthcareProvider` 🆕 | 🆕 new |
| 15 | **HealthcareProviderNpi** | `PRM_HealthcareProviderNpi__c` 🆕 | `Healthcare_Provider_NPI` 🆕 | `PRM_HealthcareFacility__c` for group/location NPIs; `PRM_Account__c` for individual NPI (whichever applies) | — | `healthcareProviderNpiData` → `createCMAForHealthcareProviderNpi` 🆕 | 🆕 new |
| 16 | **PersonEducation** | `PRM_PersonEducation__c` 🆕 | `Person_Education` 🆕 | `PRM_Account__c` = practitioner Account | — | `personEducationData` → `createCMAForPersonEducation` 🆕 | 🆕 new |
| 17 | **PersonLanguage** | `PRM_PersonLanguage__c` 🆕 | `Person_Language` 🆕 | `PRM_Account__c` = practitioner Account | — | `personLanguageData` → `createCMAForPersonLanguage` 🆕 | 🆕 new |
| 18 | **Location** | `PRM_Location__c` 🆕 | `Location` 🆕 | `PRM_HealthcareFacility__c` = HCF for that Location | — | `locationData` → `createCMAForLocation` 🆕 | 🆕 new |
| 19 | **ContactProfile** | `PRM_ContactProfile__c` 🆕 | `Contact_Profile` 🆕 | `PRM_Account__c` = practitioner Account | — | `contactProfileData` → `createCMAForContactProfile` 🆕 | 🆕 new |
| 20 | **PRM_InfoCodeAssignment__c** | `PRM_InfoCodeAssignment__c` 🆕 | `Info_Code_Assignment` 🆕 | `PRM_HealthcareFacility__c` = the facility the info code applies to (if present) | — | `infoCodeAssignmentData` → `createCMAForInfoCodeAssignment` 🆕 | 🆕 new |

> Secondary-lookup values for the 🆕 objects (14–20) are **proposed** to match the existing convention (network/address builders already stamp `PRM_HealthcareFacility__c` / `PRM_Account__c` for context). Confirm each against the PAR payload at build time (CQ-P).

## Acceptance Criteria

### Schema & universal rules

> **Data-model story format (standard for any field/object change):** every new field is specified with an explicit **"Create the field"** AC (full field configuration) **and** a **"Field Access, Permission Sets, and Metadata Notification"** AC (FLS mapping + DART notification). See `.cursor/rules/story-completeness-check.md` → "Data Model Change Pattern."

**AC-13.1 — Create the seven new lookup fields on `PRM_CaseManagerAssociation__c`**

**Given** the `PRM_CaseManagerAssociation__c` object exists in the org,
**When** the Admin creates the seven new custom **lookup** fields on `PRM_CaseManagerAssociation__c`,
**Then** each field shall have the following configuration. **Shared settings (identical for all seven):**
- **Type:** Lookup
- **Default Value:** N/A (lookup)
- **Required:** No
- **Delete Constraint:** _Clear the value of this field_ (`deleteConstraint = SetNull`)
- **Child Relationship Name:** `Case_Manager_Associations` (`relationshipName`)
- **Field-Level Security:** per **AC-13.1A**
- **Page Layout:** add to the `PRM_CaseManagerAssociation__c` page layout(s) in a "Captured Record" section

**And** the per-field values shall be:

| # | API Name | Type | Lookup → (Related To) | Label | Description |
|---|---|---|---|---|---|
| 1 | `PRM_HealthcareProvider__c` | Lookup | HealthcareProvider | Healthcare Provider | Captures a HealthcareProvider record created on this case so a later PDM/Provider-Change overwrite of `PRM_CaseManager__c` cannot orphan it. |
| 2 | `PRM_HealthcareProviderNpi__c` | Lookup | HealthcareProviderNpi | Healthcare Provider NPI | Captures an individual/group/location NPI record created on this case for overwrite-proof retrieval. |
| 3 | `PRM_PersonEducation__c` | Lookup | PersonEducation | Person Education | Captures a PersonEducation record created on this case for overwrite-proof retrieval. |
| 4 | `PRM_PersonLanguage__c` | Lookup | PersonLanguage | Person Language | Captures a PersonLanguage record created on this case for overwrite-proof retrieval. |
| 5 | `PRM_Location__c` | Lookup | Location | Location | Captures a Location record created on this case for overwrite-proof retrieval. |
| 6 | `PRM_ContactProfile__c` | Lookup | ContactProfile | Contact Profile | Captures a ContactProfile record created on this case for overwrite-proof retrieval. |
| 7 | `PRM_InfoCodeAssignment__c` | Lookup | PRM_InfoCodeAssignment__c | Info Code Assignment | Captures a telehealth/info-code assignment record created on this case for overwrite-proof retrieval. |

**AC-13.1A — Field Access, Permission Sets, and Metadata Notification**

**Given** the seven new fields have been created in Salesforce,
**When** the Admin configures user access and deployment documentation,
**Then** the access levels shall be explicitly mapped as follows (identically for all seven fields):
- **Read Access:** Credentialing, PDA, Network Management QC Permission Sets
- **Edit Access:** `PRM_CredentialingUser`, `PRM_ProviderDataAdmin`, and `PRM_NetworkManagementQC`
- **View All, Read:** `PRM_DataViewAll`
- **Read, Create, Edit, View All:** `PRM_DataModifyAll`

**And** the Admin shall explicitly **NOTIFY KISHLAY + AKSHAY** to add the fields for SF to **DART Metadata & Data Dictionary**.

**AC-13.1B — Create the seven matching RecordTypes**

**Given** the seven lookup fields exist on `PRM_CaseManagerAssociation__c`,
**When** the Admin creates the matching RecordTypes,
**Then** one RecordType exists per object: `Healthcare_Provider`, `Healthcare_Provider_NPI`, `Person_Education`, `Person_Language`, `Location`, `Contact_Profile`, `Info_Code_Assignment` (CQ-L),
**And** each is activated and assigned to the relevant profiles/permission sets per **AC-13.1A**.

**AC-13.2 — Universal fields set on every CMA record**

**Given** any CMA record created by the service,
**When** it is inserted,
**Then** `PRM_CaseManager__c` = the case Id (never blank), `RecordTypeId` = the object's RecordType, and the object's primary lookup = the created record Id,
**And** rows whose source record Id is blank/non-string are skipped (not inserted as empty),
**And** after a non-empty insert the case is marked `PRM_UseCaseManagerAssociation__c = true`.

### Per-object field mapping — EXISTING objects (verify against builders, do not regress)

**AC-13.3 — HCPF (Practitioner Practice Location)**
**Given** created HCPF records in `adpData`,
**When** the service runs,
**Then** each CMA sets `PRM_HealthcarePractitionerFacility__c` = HCPF Id, `RecordTypeId` = `Practitioner_Practice_Location`, `PRM_CaseManager__c` = case Id,
**And** no secondary lookup or request type is set.

**AC-13.4 — HealthcareFacility (practice location)**
**Given** practice-location facility rows (`lmsPLCOI`),
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareFacility__c` = HCF Id, `RecordTypeId` = `PRM_PracticeLocation`, `PRM_CaseManager__c`,
**And** `PRM_RequestType__c` = `'Terminate Current Office Information'` when the payload row carries `PRM_EffectiveTo__c`, otherwise `'Remove Practitioner'`.

**AC-13.5 — HealthcareFacilityNetwork as Practice-Location Taxonomy**
**Given** `addPracLocTaxonomyData` / `terminatedPracLocTaxonomyData`,
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareFacilityNetwork__c` = HFN Id, `RecordTypeId` = `Practice_Location_Taxonomy`, `PRM_RequestType__c` = the row's `PRM_RequestType__c`, `PRM_CaseManager__c`.

**AC-13.6 — HealthcareFacilityNetwork as Network / PPLTN (record-type-driven)**
**Given** network rows (`practitionerPPLTNData`, `addRemoveNetworksToUpdate`, `pracLocDirectoryIndicatorData`, `panelUpdateStatusData`),
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareFacilityNetwork__c` = HFN Id, `PRM_HealthcareFacility__c` = HFN.HealthcareFacilityId, `PRM_Account__c` = HFN.Practitioner.AccountId, `PRM_CaseManager__c`,
**And** `RecordTypeId` is chosen from the HFN's `RecordType.DeveloperName`: `PRM_FacilityPractitionerTxNw`→`Practitioner_at_Practice_Location_Taxonomy_and_Network`, `PRM_FacilityNw`→`Practice_Location_Network`, `PRM_FacilityTx`→`Practice_Location_Taxonomy`.

**AC-13.7 — PPLTN from payload PractitionerId**
**Given** `pracLocPPLTNData` / `removedPracLocPPLTNData`,
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareFacilityNetwork__c` = Id, `PRM_HealthcareFacility__c` = payload `HealthcareFacilityId`, `PRM_Account__c` = Account resolved from `PractitionerId` (PersonContact→Account), `RecordTypeId` = `Practitioner_at_Practice_Location_Taxonomy_and_Network`, `PRM_CaseManager__c`,
**And** when the PractitionerId cannot be resolved, `PRM_Account__c` is left null (row still created).

**AC-13.8 — HealthcareProviderTaxonomy (practitioner taxonomy)**
**Given** `practitionerTaxonomyData` / `updatedPractitionerTaxonomyData`,
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareProviderTaxonomy__c` = Id, `RecordTypeId` = `Healthcare_Provider_Taxonomy`, `PRM_CaseManager__c`.

**AC-13.9 — Practice-Location Association (+ Capitation Site)**
**Given** `praclocAssociationData`/`pracLocContractTo` and `capSite`,
**When** the service runs,
**Then** each CMA sets `PRM_HealthcareFacilityAssociation__c` = Id, `RecordTypeId` = `Practice_Location_Association`, `PRM_CaseManager__c`,
**And** the cap-site rows additionally set `PRM_RequestType__c` = `'Capitation Site'`.

**AC-13.10 — Address**
**Given** address rows (`mailingBillingAddressData`, `newlyAddedAddressData`, `addressAddCOI`, `addressUpdateCOI`, `lmsAddressData`, updated old/new ids),
**When** the service runs,
**Then** each CMA sets `PRM_Address__c` = Address Id, `RecordTypeId` = `Practice_Location_Address`, `PRM_CaseManager__c`,
**And** `PRM_HealthcareFacility__c` = the HCF resolved by walking Address.ParentId(Location)→HealthcareFacility.LocationId,
**And** `PRM_RequestType__c` = the row's request type when present,
**And** for the LMS variant, only rows with a non-blank `PRM_EffectiveTo__c` produce a CMA.

**AC-13.11 — Identifier (CAQH / Tax / Medicare)**
**Given** `oldTaxId`+`newTaxId` and/or `medicareData`,
**When** the service runs,
**Then** each CMA sets `PRM_Identifier__c` = Id, `RecordTypeId` = `Identifier`, `PRM_CaseManager__c`,
**And** old and new tax identifiers each produce their own row when present.

**AC-13.12 — BusinessLicense**
**Given** `practitionerBusinessLicense`,
**When** the service runs,
**Then** each CMA sets `PRM_BusinessLicense__c` = Id, `RecordTypeId` = `Business_License`, `PRM_CaseManager__c`.

**AC-13.13 — ProviderFeature & ProgramParticipation**
**Given** `pracProviderFeatureCreationData[Update]` and `vendorProgParticipationData`/`pracLocProgramParticipation`,
**When** the service runs,
**Then** provider-feature CMAs set `PRM_ProviderFeature__c` = Id + RT `Provider_Feature`, and program-participation CMAs set `PRM_ProgramParticipation__c` = Id + RT `Program_Participation`, both with `PRM_CaseManager__c`.

**AC-13.14 — Account (practitioner / vendor)**
**Given** `lmsAccountsCOI` / `VendorId` / `lmsPLRemovePrac`,
**When** the service runs,
**Then** each CMA sets `PRM_Account__c` = Account Id, `PRM_CaseManager__c`, `PRM_RequestType__c` from the payload,
**And** `RecordTypeId` = `PRM_Vendor` when the payload row's `RecordType == 'Vendor'`, otherwise `PRM_Practitioner`.

### Per-object field mapping — NEW objects (build in this story)

**AC-13.15 — HealthcareProvider**
**Given** created HealthcareProvider records passed in `healthcareProviderData`,
**When** `createCMAForHealthcareProvider` runs,
**Then** each CMA sets `PRM_HealthcareProvider__c` = HealthcareProvider Id, `RecordTypeId` = `Healthcare_Provider`, `PRM_CaseManager__c`,
**And** `PRM_Account__c` = the provider's Account when resolvable (else null),
**And** blank/non-string Ids are skipped.

**AC-13.16 — HealthcareProviderNpi**
**Given** created HealthcareProviderNpi records (`healthcareProviderNpiData`),
**When** `createCMAForHealthcareProviderNpi` runs,
**Then** each CMA sets `PRM_HealthcareProviderNpi__c` = NPI Id, `RecordTypeId` = `Healthcare_Provider_NPI`, `PRM_CaseManager__c`,
**And** for a group/location NPI `PRM_HealthcareFacility__c` = the related HCF, for an individual NPI `PRM_Account__c` = the practitioner Account (set whichever the payload provides; both null is allowed).

**AC-13.17 — PersonEducation**
**Given** created PersonEducation records (`personEducationData`),
**When** `createCMAForPersonEducation` runs,
**Then** each CMA sets `PRM_PersonEducation__c` = Id, `RecordTypeId` = `Person_Education`, `PRM_Account__c` = practitioner Account (if provided), `PRM_CaseManager__c`.

**AC-13.18 — PersonLanguage**
**Given** created PersonLanguage records (`personLanguageData`),
**When** `createCMAForPersonLanguage` runs,
**Then** each CMA sets `PRM_PersonLanguage__c` = Id, `RecordTypeId` = `Person_Language`, `PRM_Account__c` = practitioner Account (if provided), `PRM_CaseManager__c`.

**AC-13.19 — Location**
**Given** created Location records (`locationData`),
**When** `createCMAForLocation` runs,
**Then** each CMA sets `PRM_Location__c` = Location Id, `RecordTypeId` = `Location`, `PRM_HealthcareFacility__c` = the HCF for that Location (if resolvable), `PRM_CaseManager__c`.

**AC-13.20 — ContactProfile**
**Given** created ContactProfile records (`contactProfileData`),
**When** `createCMAForContactProfile` runs,
**Then** each CMA sets `PRM_ContactProfile__c` = Id, `RecordTypeId` = `Contact_Profile`, `PRM_Account__c` = practitioner Account (if provided), `PRM_CaseManager__c`.

**AC-13.21 — PRM_InfoCodeAssignment__c (telehealth/info codes)**
**Given** created `PRM_InfoCodeAssignment__c` records (`infoCodeAssignmentData`),
**When** `createCMAForInfoCodeAssignment` runs,
**Then** each CMA sets `PRM_InfoCodeAssignment__c` = Id, `RecordTypeId` = `Info_Code_Assignment`, `PRM_HealthcareFacility__c` = the facility the info code applies to (if present), `PRM_CaseManager__c`.

### Service, reuse, and negative paths

**AC-13.22 — No OmniScript contains CMA creation logic**
**Given** the creation path, **When** a developer inspects the OmniScripts, **Then** CMA creation is invoked only via the Apex Remote Action (service), never via per-flow OmniScript steps.

**AC-13.23 — Reused unchanged by every flow**
**Given** PAR, off-cycle, ancillary, recred, and re-assessment, **When** each submits, **Then** each calls the same service with its own created-record Id lists, **And** no flow needs a bespoke CMA builder.

**AC-13.24 — Updated-only and partial payloads**
**Given** a payload where some sections are empty or contain only updated (pre-existing) records,
**When** the service runs,
**Then** empty sections produce zero CMA rows, updated-only records produce no CMA, and present sections still produce their rows (partial payloads never throw).

**AC-13.25 — Single DML + bulk-safe**
**Given** a submission that creates records across many of the 20 types,
**When** the service runs,
**Then** all CMA rows are inserted in a single DML statement (no per-type DML), and account/HFN/contact resolution queries are bulkified (no SOQL/DML in loops).

**AC-13.26 — Tier-2 extensibility**
**Given** the Tier-2 objects (§0.6.4), **When** a future flow needs coverage, **Then** adding it is a new lookup + RecordType + builder method + routing key only — no structural change.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `objects/PRM_CaseManagerAssociation__c/fields/` | Metadata | Add 7 Tier-1 lookups: `PRM_HealthcareProvider__c`, `PRM_HealthcareProviderNpi__c`, `PRM_PersonEducation__c`, `PRM_PersonLanguage__c`, `PRM_Location__c`, `PRM_ContactProfile__c`, `PRM_InfoCodeAssignment__c` | All `SetNull` + `relationshipName=Case_Manager_Associations` (AC-13.1). Set FLS per AC-13.1A; **NOTIFY Kishlay + Akshay for DART Metadata & Data Dictionary**. |
| `permissionsets/*` | Metadata | Grant FLS on the 7 fields: Read → Credentialing/PDA/NetMgmtQC; Edit → `PRM_CredentialingUser`/`PRM_ProviderDataAdmin`/`PRM_NetworkManagementQC`; `PRM_DataViewAll` (read), `PRM_DataModifyAll` (read/create/edit) | Drives AC-13.1A |
| `objects/.../recordTypes/` | Metadata | Add 7 RecordTypes: `Healthcare_Provider`, `Healthcare_Provider_NPI`, `Person_Education`, `Person_Language`, `Location`, `Contact_Profile`, `Info_Code_Assignment` | one per object (CQ-L); drives AC-13.1B |
| `PRM_CaseManagerAssociationDirectBuilder` (+ a new builder if cleaner) | Apex | Add `createCMAForHealthcareProvider`, `…ProviderNpi`, `…PersonEducation`, `…PersonLanguage`, `…Location`, `…ContactProfile`, `…InfoCodeAssignment` | mirror existing builder shape; bulkify Account/HCF resolution (AC-13.25) |
| `PRM_CaseManagerAssociationService` | Apex | Add payload keys (`healthcareProviderData`, `healthcareProviderNpiData`, `personEducationData`, `personLanguageData`, `locationData`, `contactProfileData`, `infoCodeAssignmentData`) + `addIfPresent` routing; preserve single insert | drives AC-13.2, 13.15–13.21, 13.25 |
| `IndividualApplication.PRM_UseCaseManagerAssociation__c` | Metadata | Add missing `.field-meta.xml` to source (CQ-D) | source-control gap |

## Clarification Questions

| # | Question | Owner |
|---|---|---|
| CQ-K | Confirm Tier-1 vs Tier-2 cut for the first release (PAR-only vs all-flows) | Product / Arch |
| CQ-L | One RecordType per object, or reuse generic RTs where lookups disambiguate? | Technical |
| CQ-M | Does `PRM_CaseDataManager__c` need a child lookup, or is it the case anchor? | Technical |
| CQ-P | Confirm the **secondary-lookup** values for the 7 new objects against the PAR payload — specifically: does the PAR payload carry the practitioner Account for Provider/Education/Language/ContactProfile, the HCF for ProviderNpi/Location/InfoCode? If not resolvable inline, leave null or resolve via SOQL? | Technical / BA |
| CQ-Q | For HealthcareProviderNpi, do we need to distinguish individual vs group/location NPI via separate RecordTypes, or is one RT + the populated secondary lookup enough? | Technical |

## Estimated Effort

| Component | Effort |
|---|---|
| 7 Tier-1 lookups + RecordTypes | M |
| 7 builder methods (with secondary-lookup resolution) + service routing | M–L |
| Tier-2 design (not build) | S |
| Tests (per-object mapping assertions, AC-13.3–13.21) | L |

**Total Estimated Effort:** L (AI-estimated — validate with team).

---

# USER STORY US14: Reusable CMA Fetch Service Across All Review/Guided Flows (Terminated-Excluded)

**Persona:** Platform / Developer (value accrues to every reviewer)
**Priority:** P0 — the read side of the fix; without it, captured CMAs are never used. **This is the service the retired US7 referenced; each review story (US8–US12) bakes its own call to it.**
**OmniScript:** none (logic is Apex; flows call one Remote Action)
**Apex:** new `PRM_CaseManagerAssociationFetchService` (`VlocityOpenInterface2`)
**Integration Procedures:** `PRM_FetchFormDetails` v31 (App Review + PSV/QC via wrap), `PRM_FetchParDetails` v33 (PSV + QC Review), `PRM_FetchFormPDAReview` v24 (PDA/NMQC), `PRM_DataRetrievalforHAPACCommitteeReview` v3 (Committee). _(`PRM_InitManualUpdatesQC` v9 = the out-of-scope Manual-QC (PDM) flow — not the initial-cred QC Review.)_
**Relevant Requirements:** §0.6.3, §0.6.5, §0.6.6

---

## Story

**As a** developer maintaining the review/guided flows,
**I want** a single Apex service that, given a case manager Id, returns that case's **active** associated records (grouped by type, terminated locations excluded) plus a separate terminated-location set and a `HasTerminatedLocations` flag,
**So that** every flow — App Review, PSV, QC, Committee, PDA, NMQC, plus off-cycle/ancillary/recred/re-assessment — resolves its records the same overwrite-proof way, never shows terminated locations on a review step, and can gate its review-launch button, all without duplicating logic in OmniScripts.

**Why it matters:** §0.6.3 shows each flow re-implements `WHERE PRM_CaseManager__c = :CMID` extracts across 10–28 DataRaptors. That is both the overwrite vulnerability and massive duplication. One fetch service replaces all of it; the QC flow already extracts CMA details, proving the pattern. Centralizing the terminated-location predicate here (matching `prmTerminatedLocationAlert`, §0.6.6) guarantees every flow filters terminations identically.

## Scope & Preconditions

- US13 (lookups + creation coverage) and US6 (PAR creates CMA) in place so CMAs exist to read.
- The service is **Apex** and returns, per type, the **active hydrated records** (the fields each review step needs) — **terminated locations excluded from those record sets** — plus a `TerminatedLocations[]` list (name, address, termination date) and a `HasTerminatedLocations` flag, gated on `IndividualApplication.PRM_UseCaseManagerAssociation__c = true` (fall back to legacy `PRM_CaseManager__c` filter when false, for un-backfilled cases).
- **No DataRaptors in the read path.** The Apex service does the SOQL and hydration; the per-section DR extracts that cause today's performance problems are removed.
- The termination predicate is the canonical one from §0.6.6 (`PRM_IsErrorRecord__c = true` OR `PRM_EffectiveTo__c != null` with the active/future-dated conditions).

## Acceptance Criteria

**AC-14.1 — Single Apex service returns all ACTIVE associated records by type (hydrated)**

**Given** a case manager Id with CMA records,
**When** a flow calls the Apex fetch service,
**Then** it receives the related **active** records (hydrated with the fields each step needs) grouped by type (HCPF, HCF, HFN, taxonomy, address, identifier, license, provider, NPI, education, language, location, contact profile, info code, …),
**And** terminated locations are NOT included in those record sets,
**And** the result is correct even after `PRM_CaseManager__c` was overwritten on the underlying records.

**AC-14.2 — Flows resolve records via the Apex service (DataRaptor extracts removed)**

**Given** App Review, PSV, QC, Committee, PDA, and NMQC,
**When** each fetch IP runs for a CMA-enabled case,
**Then** it obtains its records from the US14 **Apex** service rather than from `PRM_CaseManager__c`-filtered **DataRaptor** extracts,
**And** the legacy per-section DR extracts are removed from the read path,
**And** the loaded record set matches the case's active records (terminated locations excluded).

**AC-14.2.1 — Performance: Apex replaces the slow DR reads**

**Given** the read path previously ran 10–28 `PRM_CaseManager__c`-filtered DataRaptor extracts per flow,
**When** the Apex fetch replaces them,
**Then** the case loads with a bounded, bulkified set of SOQL queries in Apex (no per-section DR, no SOQL-in-loop),
**And** the load performs at least as well as — and is expected to outperform — the prior DR-based read.

**AC-14.3 — Backward compatible for non-CMA cases**

**Given** a case where `PRM_UseCaseManagerAssociation__c = false` (not yet backfilled),
**When** the Apex fetch service runs,
**Then** it falls back to the legacy `PRM_CaseManager__c` filter **in Apex** (still excluding terminated locations from the record sets),
**And** behaviour is unchanged for those cases.

**AC-14.4 — No CMA fetch logic in any OmniScript (and no DR in the read path)**

**Given** the read path,
**When** a developer inspects the OmniScripts and IPs,
**Then** CMA resolution and record hydration happen only in the Apex service, never in OmniScript steps and never via per-section DataRaptor extracts.

**AC-14.5 — Terminated set + flag surfaced once (drives the button-hide)**

**Given** a case with a terminated location,
**When** any flow calls the service,
**Then** the response includes `HasTerminatedLocations = true` and a `TerminatedLocations[]` list (name, address, termination date) separate from the active display lists,
**And** the same predicate as `prmTerminatedLocationAlert` (§0.6.6) is used, so the banner, the button-hide gate (US8–US12), and the fetch exclusion never disagree.

**AC-14.6 — Reused by off-cycle / ancillary / recred / re-assessment**

**Given** those guided flows,
**When** they load case records,
**Then** they call the same service and need no flow-specific fetch logic.

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CaseManagerAssociationFetchService` | Apex (new) | `VlocityOpenInterface2`; input `caseManagerId`; **queries CMA + hydrates the active records in Apex**; output active hydrated records by type (terminated locations excluded) + `TerminatedLocations[]` + `HasTerminatedLocations` | bulkified SOQL grouped by RecordType/lookup; applies the §0.6.6 termination predicate; **replaces DR reads** |
| `PRM_FetchFormDetails` v31 (App Review, US8) | IP | **Replace** ~20 `PRM_CaseManager__c` DataRaptor extracts with the Apex service call | biggest rewire; removes the slowest DRs |
| `PRM_FetchParDetails` v33 (QC Review, US10) | IP | QC inherits the PSV/App-Review fetch (wraps `PRM_FetchFormDetails`) — no separate QC reader to convert | shared with PSV |
| _`PRM_InitManualUpdatesQC` v9 (Manual QC / PDM — out of scope)_ | IP | Not part of the initial-cred pipeline; its `PRMDRExtractCaseManagerAssociationDetails` is the reference proof for the read-via-CMA pattern | future / out of scope |
| `PRM_FetchFormPDAReview` v24 (PDA/NMQC, US11/US12) | IP | **Replace** HCPF/HCF/HFN/provider/identifier DR extracts with the Apex service | shared by NMQC |
| `PRM_DataRetrievalforHAPACCommitteeReview` v3 (Committee) | IP | **Replace** HCF/identifier/license DR extracts with the Apex service | ancillary-scoped |
| `PRM_FetchParDetails` v33 (PSV fetch, US9) | IP | PSV read inherits App Review via the wrapped `PRM_FetchFormDetails`; only the PSV-specific `DRTurboGetAdverseReviewAction` (AdverseActionReview, by `CaseManagerId`) is PSV-extra — move to CMA if a Tier-2 lookup exists | wraps App-Review fetch; `PRM_ReviewPSVCaseRecordsUpdate` v26 is the **save** IP (not read) |
| `prmTerminatedLocationAlert` / `PRM_CaseManagerRecordPage` | LWC / FlexPage | Optionally expose the service's `HasTerminatedLocations` to the App Review/PSV/QC review-button visibility rules so banner + button-hide share one source of truth; and suppress the banner at PDA/NMQC stages | Supports US8–US10 button-hide + US11/US12 banner suppression (CQ-H) |

## Clarification Questions

| # | Question | Owner |
|---|---|---|
| CQ-N | *(resolved in v3.1)* Return Ids only vs. hydrate full records server-side → **hydrate in Apex** (DRs caused the performance problem) | Technical |
| CQ-O | Roll out flow-by-flow behind a flag, or all flows at once? | Product / Arch |
| CQ-T | Should the service's terminated-exclusion apply to facilities/networks too, or only practice locations (HCPF/HCF)? The §0.6.6 predicate is HealthcareFacility-based; confirm scope of "terminated" beyond locations. | Technical / BA |

## Estimated Effort

| Component | Effort |
|---|---|
| Fetch service + tests | M–L |
| App Review rewire (~20 extracts) | L |
| QC rewire (pattern exists) | M |
| PDA/NMQC + Committee + PSV rewire | M |
| Regression across all flows | L–XL |

**Total Estimated Effort:** XL (AI-estimated — validate with team). Highest-value refactor: removes the overwrite bug for every record type and eliminates per-flow duplication.

---

## 2. Dependency order & sprint sequencing

```
US13 (CMA schema + creation service — ALL case-scoped records, 7 new lookups)
  └─ US6  (PAR creates CMA + backfill)  ── US6 is the HCPF creation slice of US13
US14 (reusable CMA fetch service — APEX, all flows; terminated locations excluded; no OmniScript logic, no DR)
        ├─ US8 (App Review — Apex fetch + hide review button on terminated + CMA upkeep on PRM_ReviewParCaseRecordsUpdate v15)  P0 — unblocks production
        │     ├─ US9  (PSV — inherits App-Review FETCH (wrapped); own SUBMIT IP PRM_ReviewPSVCaseRecordsUpdate v26 → own CMA upkeep; own PSV button-hide)
        │     └─ US10 (QC Review = stage of PSV OmniScript → fetch + v26 submit INHERITED from US9; net-new = QC button-hide)
        └─ US11 (PDA — Apex fetch + exclude terminated + suppress banner at PDA stage [NO button-hide] + CMA upkeep on v23/SubIPUpdate v7 + PNC batch)
              └─ US12 (NMQC — inherits US11 fetch + CMA upkeep; suppress banner at NMQC stage [NO button-hide] + regression)

[US7 RETIRED in v3.1 — the read-side "HCPF DR + IP wiring" is no longer a standalone story;
 each review story above bakes its own fetch call to the US14 service.]
```

| Sprint | Stories | Rationale |
|---|---|---|
| 1 | US13 + US6 | Schema + creation coverage. Build the 7 Tier-1 lookups/builders once; US6 (HCPF) ships inside it. Resolve CQ-A (creation home) + CQ-K (Tier-1 vs Tier-2). |
| 2 | US14 | One reusable **Apex** fetch service (active hydrated records, terminated-excluded, + `HasTerminatedLocations`). No DataRaptors; no separate wiring story — each review story wires itself. Resolve CQ-O (rollout) + CQ-T (terminated scope). |
| 3 | US8, US9, US10 | **Fetch is shared** (PSV+QC wrap App Review's `PRM_FetchFormDetails`). On submit, **App Review is standalone (`PRM_ReviewParCaseRecordsUpdate` v15) while PSV and QC Review share `PRM_ReviewPSVCaseRecordsUpdate` v26** (QC is a stage of the PSV OmniScript, `QCProceedTo` branch) — so CMA create-on-submit upkeep is implemented **twice** (App Review v15; PSV+QC v26), not three times. US10 inherits both fetch and submit from US9; its only net-new work is the **QC review-button-hide** (reusing §0.6.6). Unblocks production bug. Resolve CQ-H (button-hide wiring). |
| 4 | US11, US12 | PDA + NMQC; Apex fetch + **suppress banner at stage (NO button-hide — non-blocking)**; CMA upkeep on `SubIPUpdate` v7 + `PRM_PNCPDAUtility.PNCPDABatch`. US12 mostly inherits US11. Resolve CQ-S1 (how the stage is read for banner suppression). |

**Fetch-is-baked-per-flow insight (v3.1):** there is no shared "wire the fetch once" step. US14 ships the **Apex** *service*; each of US8/US9/US10/US11/US12 contains its own acceptance criteria for calling that service and **replacing its own DataRaptor extracts** (the DR extracts are the performance problem). This is the correction that retired US7.

**Terminated-location handling insight (v3.1):** the US14 Apex fetch excludes terminated locations from **every** review step (all five flows). On top of that exclusion: **App Review / PSV / QC** also **hide their launch button** on `PRM_CaseManagerRecordPage` (one shared §0.6.6 detection) so the reviewer can't start a doomed review; **PDA / NMQC** are **non-blocking** — no button-hide — and instead **suppress the `prmTerminatedLocationAlert` banner** at those stages. No per-flow termination re-detection.

**CMA-upkeep insight (corrected — App Review standalone; PSV+QC share one IP):** CMA records are immutable pointers, so review stages never *update* existing CMAs. They must, however, *create* CMAs for records they newly **insert**. The submit IPs group as follows:
- **App Review** → `PRM_ReviewParCaseRecordsUpdate` v15 (reached via the App Review sub-OmniScripts); CAQH identifiers via the sub-OS `PRM_AddCAQHRecord`.
- **PSV + QC Review** → `PRM_ReviewPSVCaseRecordsUpdate` **v26** (QC is a stage of the PSV OmniScript and runs the `QCProceedTo` branch of the same IP — so the v26 hooks added for PSV cover QC).
- **PDA / NMQC** → `PRM_InitialCredPDAReviewUpdateSubIPUpdate` v7 (+ `PRM_PNCPDAUtility.PNCPDABatch` on the PNC path).

Hook the **insert branch** (blank-Id upserts / DataRaptor-Post of new records), not the update step. So CMA upkeep is built **three times** total (App Review v15; PSV+QC v26; PDA/NMQC SubIPUpdate v7) — not five. **Earlier drafts incorrectly pointed QC at `PRM_SaveManualUpdatesQC`** — verified false on 2026-06-10; that IP is the separate Manual-QC (PDM) flow, and QC actually shares PSV's v26.

## 3. Cross-references

- v2.0 (superseded): `PAR_CaseManager_Association_CMA_Redesign_User_Stories.md`
- Apex-service target for PAR form: `requirements/Enhancements/PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`
- Migration methodology: `requirements/Enhancements/prompt.md`

## 4. Consolidated open decisions

| # | Decision | Default taken in this doc | Owner |
|---|---|---|---|
| CQ-A | CMA creation home: `PRM_AddressRecordService` vs. legacy IP step | Prefer Apex-service (migration-aligned); interim legacy step behind flag | Architecture |
| CQ-B | Tag PAR CMAs with `PRM_RequestType__c='PAR'`? | Recommended yes | BA |
| CQ-C | Extend `PRM_CaseManagerAssociationBatch` for PAR backfill vs. new batch | Extend existing | Technical |
| CQ-D | Add missing `PRM_UseCaseManagerAssociation__c` field-meta to source | Yes | Ops |
| CQ-E | New `PRMDREGetPARCaseHCPFViaCMA` vs. activate/extend `PRMExtractCaseManagerAssociationsPCF` | Either; lean reuse (now subsumed by the US14 service, not a standalone US7 DR) | Technical |
| CQ-F | COUNTQUERY subquery vs. IP-level guard for EligibleForUpdate | Defense-in-depth only now (button-hide gates entry); verify at build | Technical |
| CQ-G | *(retired)* "Update Locations"/"Close Case" actions dropped. **v3.1 supersedes the v3.0 "hide submit button" approach** — App Review/PSV/QC hide the **review-launch button** at entry (§0.6.6); PDA/NMQC stay non-blocking and just suppress the banner. All five exclude terminated locations from the steps | n/a | — |
| CQ-H | Review-button-hide wiring (App Review/PSV/QC only): bind a flag exposed by `prmTerminatedLocationAlert`, a roll-up/formula field on IndividualApplication, or a FlexPage visibility rule re-querying the §0.6.6 predicate? Must reuse one shared detection, not duplicate it. (Same shared detection also drives the PDA/NMQC banner suppression.) | Lean: one shared flag feeding the App Review/PSV/QC launchers + the banner's stage check | Technical |
| CQ-I | When a CMA-covered record is deleted during review (e.g., `RADeleteHCPFRecords` on v26), delete the orphaned CMA or retain as history? | Lean retain-as-history (align v2.0 B1) | Technical / BA |
| CQ-J | Stamp `PRM_RequestType__c` on review-created CMAs (e.g., 'App Review', 'PDA') to distinguish from submission-origin CMAs? | Recommended yes | BA |
| CQ-K | First-release coverage cut — Tier-1 (PAR's 7 case-scoped objects) only, or Tier-1 + Tier-2 (all flows)? | Tier-1 first, Tier-2 fast-follow | Product / Arch |
| CQ-L | One RecordType per new lookup, or reuse generic RTs where the populated lookup disambiguates? | One RT per object (consistency) | Technical |
| CQ-M | Does `PRM_CaseDataManager__c` need its own CMA child lookup, or is it the case anchor? | Treat as anchor unless proven otherwise | Technical |
| CQ-N | *(resolved v3.1)* Fetch service returns resolved Ids only, or hydrates full records server-side? | **Hydrate full records in Apex** — DataRaptors caused the performance problem | Technical |
| CQ-O | Roll the fetch service out flow-by-flow behind a flag, or all flows at once? | Flow-by-flow behind a flag | Product / Arch |
| CQ-R | Should the App Review/PSV/QC button-hide also re-evaluate mid-flight if a location is terminated *after* a review starts, or only gate at launch? | Lean: gate at launch only; mid-flight is an edge case | Product / Technical |
| CQ-S | *(resolved v3.1)* PDA/NMQC button on terminated locations? | **Not blocked** — PDA/NMQC keep their button; terminated locations are excluded from the steps and the banner is suppressed at those stages | Product / BA |
| CQ-S1 | How is the case's current stage read for banner suppression (US11/US12) — IndividualApplication `Status`, a CaseType field, or the CMDT stage list? | Confirm the exact field/values for "PDA Review and Update" and "Network Management QC" | Technical / BA |
| CQ-T | Does terminated-exclusion in the fetch apply to facilities/networks too, or only to practice locations (HCPF/HCF, the §0.6.6 predicate's scope)? | Defines what "terminated" hides beyond locations | Technical / BA |

---

*End of document — v3.1 (2026-06-10). v3.1 retires US7 (fetch baked into each review story); makes the CMA fetch **Apex, not DataRaptors** (US14 hydrates records server-side — DR extracts caused the perf problem); excludes terminated locations from every review step (all five flows); **hides the review-launch button on terminated locations for App Review / PSV / QC only**; and for **PDA / NMQC** keeps the button (non-blocking) while **suppressing the `prmTerminatedLocationAlert` banner** at those stages. Component names/versions verified against the repo on the v3.0 authoring date (2026-06-07); the existing terminated-location infrastructure (`prmTerminatedLocationAlert`, `PRM_TerminationAlertReviewStages__mdt`, `PRM_CaseManagerRecordPage`) verified 2026-06-10.*
