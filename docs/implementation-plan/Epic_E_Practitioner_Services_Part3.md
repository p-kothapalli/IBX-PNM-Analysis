# Epic E — Practitioner Creation Services (Implementation Guide) · Part 3 · PLRelatedBatch + Level4RecordCreationBatch (+ GroupRelatedBatch TBD)

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.6) · `PRM_Implementation_Plan.md` (§8) · **Part 1:** `Epic_E_Practitioner_Services.md` (intake + PractitionerBatch — shared conventions §E0–E0.3) · **Part 2:** `Epic_E_Practitioner_Services_Part2.md` (PracticeLocationAndGroupBatch).
> **Goal:** the **tail batches** of the pipeline: **`PLRelatedBatch`** (seq 4, batch design **`E22_PRM_PLRelatedBatch.md`**) — **E14** `PRM_HPFService` (+ `PractionerPracticeLocationService` sub-service) · **E15** `PRM_ProviderFeatureService`; and **`Level4RecordCreationBatch`** (seq 5) — **E18** `PRM_Level4RecordCreationService`. **`GroupRelatedBatch`** (seq 3) services are still **TBD** (CL-15).
>
> **🔄 Recent decisions (2026-07, org-verified — folder docs are authoritative):**
> - **E14 is a single service owning BOTH record types** — **PLA** (`PRM_PractitionerLocationAffiliation`, facility-linked) **+ PPA** (`PRM_PractitionerPracticeAffiliation`, **Account-linked**, `HealthcareFacilityId` blank). PPA is org-confirmed created by DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]`.
> - **E15 owns TWO record types** — **AssistiveAid** (`capabilitiesAtLocation`) **+ AffirmingCareCategory / ACC** (`affirmingCareCategory`), both **per-location**, Id-based idempotency (no end-dating).
> - **✅ E17 DROPPED** — the facility-grain `HealthcareFacilityNetwork` (`PRM_FacilityNw` network + `PRM_FacilityTx` taxonomy) rows are a **trigger side-effect** of E18's insert of the **Level-4 `HealthcareFacilityNetwork` RT `PRM_FacilityPractitionerTxNw`** (via `PRM_HealthcareFacilityNetworkTrigger`), **not** a standalone service.
> - **CL-E2-13 resolved** — E14/E15 run in **`PLRelatedBatch` (seq 4)**, not in-process in E13. **CL-E2-11 superseded** — ACC **is** in scope (E15).
>
> **Estimate (Part 3):** ~5.5 engineer-days · **Depends on:** EPIC A/B/D + Part 1 (intake/conventions) + Part 2 (facility/location Ids from E13/E12). · **Blocks:** EPIC F (intake wrapper).

> **🔄 Reorganized by batch (sequential build).** Epic E is split **by the batch a service runs in** so each batch can be built end-to-end before the next. **This is Part 3 = the tail batches** (`GroupRelatedBatch` TBD → `PLRelatedBatch` → `Level4RecordCreationBatch`). Conventions and the batch↔service mapping live in **Part 1**. E‑numbers and CL ref IDs are preserved from the pre-reorg layout.

> **🔄 Async-only model:** these services run **inside `PLRelatedBatch` (seq 4)** and **`Level4RecordCreationBatch` (seq 5)**, sequenced by `PRM_AsyncOrchestrator` with halt-on-failure; no synchronous orchestrator. **Batch ↔ service mapping: see Part 1 + Plan §8.1.**

> **Grounding:** all field maps/formulas extracted from the in-repo **active** OmniStudio DataRaptors (single-version `_1` unless noted). Conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2** and apply here unchanged.

---

## E3.0 Record types referenced by Part 3 services (from DR `QUERY` formulas)


| SObject                        | DeveloperName                         | Used by                        |
| ------------------------------ | ------------------------------------- | ------------------------------ |
| HealthcarePractitionerFacility | `PRM_PractitionerLocationAffiliation` | E14 (PLA — facility-linked)     |
| HealthcarePractitionerFacility | `PRM_PractitionerPracticeAffiliation` | E14 (PPA — Account-linked)      |
| PRM_ProviderFeature__c         | `PRM_AssistiveAid`                    | E15 (Assistive Aids)           |
| PRM_ProviderFeature__c         | `PRM_AffirmingCareCategory`          | E15 (Affirming Care / ACC)      |
| HealthcareFacilityNetwork      | `PRM_FacilityPractitionerTxNw`        | E18 (Level-4 network)          |
| HealthcareFacilityNetwork      | `PRM_FacilityNw` / `PRM_FacilityTx`   | **trigger side-effect** of E18 (was E17 — dropped) |


> Resolve all of these via the shared cached helper **`PRM_FormSubUtility.recordTypeId(SObjectType, devName)`** (CL-E5 resolved; **not** a separate `PRM_RecordTypeUtil`) — never the legacy `QUERY(...)`.

---

## GroupRelatedBatch (seq 3) — services TBD (CL-15)

> **Open (CL-15).** `GroupRelatedBatch` sits at sequence 3 between `PracticeLocationAndGroupBatch` (Part 2) and `PLRelatedBatch`, but **no services have been assigned to it yet**. It may carry group-related follow-on records (e.g. additional group identifiers/affiliations) or be dropped. **Pending clarification** — document its services here once confirmed; until then `PRM_AsyncJobConfig__mdt` omits sequence 3 (the orchestrator tolerates the gap).

---

## E14 · `PRM_HPFService` — *1.5 d* · HealthcarePractitionerFacility · *(PLRelatedBatch · seq 4)*

> **🔄 Build spec (authoritative):** `PLRelatedBatch Related Services/E14_PRM_HPFService.md`. **✅ CL‑E2‑13 resolved:** E14 runs in **`PLRelatedBatch` (seq 4)** — **not** in-process in E13. Orchestrated by **E22** (`PRM_PLRelatedBatch`). The `PractionerPracticeLocationService` is an **internal builder** inside E14 (not a separate class).

**Single service, two record types** (org-verified). **Writes:** `HealthcarePractitionerFacility` — one mixed-RT bulk DML:

| RT | Grain | Key links | Notes |
|---|---|---|---|
| **`PRM_PractitionerLocationAffiliation`** (PLA) | one per (practitioner × location) | `HealthcareFacilityId` set, `AccountId` blank | legacy `PRMDRPDelegatedPractionerPracticeLocations` |
| **`PRM_PractitionerPracticeAffiliation`** (PPA) | one per (practitioner × practice/group) | **`AccountId` set (group), `HealthcareFacilityId` blank** | ✅ DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]` (org-confirmed) |

**Common fields (both RTs):** `PractitionerId` (PersonContact), `PRM_CaseManager__c` (IndividualApplication), `IsActive`, `EffectiveFrom`/`EffectiveTo`, `PRM_Pending__c=true`. **New PPA inserts** also set `Name` = `CONCAT(practitionerName,' @ ',practiceName)` + `IsPrimaryFacility=false` (org-required; the DR omits them). **`HealthcareProviderId`** = null for PPA (DR doesn't map it).

**Idempotency (pre-check → matched-Id update, mirrors the DR `HPFId` upsert):** PLA on `(PractitionerId + HealthcareFacilityId + RT)`; PPA on `(PractitionerId + AccountId + RT)`.

**CMA/CDM (via E22):** CMA RT **`Practitioner_Practice_Location`** (primary `PRM_HealthcarePractitionerFacility__c`); CDM token **`HealthCarePractitionerFacility`**. Neither is trigger-set → E22 emits both.

**DML:** one bulk DML (mixed RT). Returns `hcpfId` per affiliation. Full field maps + open items: the E14 folder doc.

---

## E15 · `PRM_ProviderFeatureService` — *1.5 d* · Assistive Aids + Affirming Care (ACC) · *(PLRelatedBatch · seq 4)*

> **🔄 Build spec (authoritative):** `PLRelatedBatch Related Services/E15_PRM_ProviderFeatureService.md`. **✅ CL‑E2‑13 resolved:** runs in **`PLRelatedBatch` (seq 4)**, orchestrated by **E22**. **✅ CL‑E2‑11 superseded:** ACC **is** in scope (org-verified the active IP `PRMPractitionerAddressCreation` v5 creates both).

**Single service, two record types** (org-verified, both **per-location** — sets only `PRM_HealthcareFacility__c`, never practitioner/HPF):

| RT | Source node | Target multipicklist | Gate | DR (active) |
|---|---|---|---|---|
| **`PRM_AssistiveAid`** | `location.capabilitiesAtLocation` (**display labels** → map to codes) | `PRM_AssistiveAids__c` (codes `TD,DE,…`) | `!= "Does Not Apply"` | `PRMDRCreateProviderFeatureAssitiveAids` |
| **`PRM_AffirmingCareCategory`** (ACC) | `location.affirmingCareCategory` (**labels**, added to intake) | `PRM_AffirmingCareCategory__c` (labels) | non-blank | `PRMDRCreateProviderFeatureACC` |

**Field map (org-verified):** `PRM_HealthcareFacility__c` (E13), `PRM_CaseManager__c` (IndividualApplication), `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c`, `Name` (`'Assistive Aid'` / `'Affirming Care Categories'`). **⚠ REQUIRED booleans:** `PRM_Active__c` (← `isActive`, **no default → must set**), `PRM_Pending__c` (default false); `PRM_IsDirectoryPrint__c` set for **ACC** (← `shareInDirectory`), default false for AsstAid; `PRM_IsErrorRecord__c` default false. **`PRM_ExternalId__c` is unused** by the active DRs.

**Idempotency = Id-based update-in-place** (pre-check on `(PRM_HealthcareFacility__c + RecordTypeId)`; supply matched Id → update the multipicklist, else insert). **No end-dating / `OldCapabilities`** logic (the earlier assumption is superseded by the active DR).

> **⚠ Label→code mapping (OQ-E15-4):** the intake `capabilitiesAtLocation` holds **display labels** (`American Sign Language`, `Braille Materials`) — the **batch maps them to `PRM_AssistiveAids__c` codes** (`AS`, `BM`, …) before invoking E15 (like E11's ISO codes). `Wheelchair Accessible` has no exact picklist label — finalize that one mapping row. ACC labels arrive matching the picklist (no code mapping).

**CMA/CDM (via E22):** CMA RT **`Provider_Feature`** (primary `PRM_ProviderFeature__c`; context `PRM_Account__c` group + `PRM_HealthcareFacility__c`); CDM token **`ProviderFeature`**. Not trigger-set → E22 emits both.

**DML:** one bulk DML across both RTs. Returns `providerFeatureId` per (location × type). Full detail: the E15 folder doc.

---

## E17 · `PRM_HealthcareFacilityNetworkService` — ~~*service*~~ **DROPPED** · *(trigger side-effect of E18/Level-4)*

> **✅ RESOLVED — E17 is NOT a service/batch step.** The facility-grain `HealthcareFacilityNetwork` rows (RT `PRM_FacilityNw` "Practice Location Network" + `PRM_FacilityTx` "Practice Location Taxonomy") are **auto-created by the HealthcareFacilityNetwork trigger** (`PRM_HealthcareFacilityNetworkTrigger` → `PRM_HCFacilityNetworkTriggerHelper`) when **E18** inserts the **Level-4 `HealthcareFacilityNetwork` rows (RT `PRM_FacilityPractitionerTxNw`, "Practitioner at Practice Location Taxonomy and Network")** in `Level4RecordCreationBatch` (seq 5). *(Note: this is the **HealthcareFacilityNetwork** object — `HealthcarePractitionerFacility` has no such RT.)* So the network/taxonomy records — and their CMA (`Practice_Location_Network`/`Taxonomy`) + CDM (`HealthcareFacilityNetwork`) — belong to the **Level-4 flow (E18)**, not a standalone service. **No E17 code is built.** *(The `location.networkTaxonomyRoles[]` source is consumed by E18.)*

---

## E18 · `PRM_Level4RecordCreationService` ⚡ — *2.0 d* · Branch: DELEGATED (batch) · *(Level4RecordCreationBatch)*

**Batch** class (`Database.Batchable`, dispatched via EPIC C `Batch` mode). **Writes:** `HealthcareFacilityNetwork` at the **full Level-4 grain** — RT **`PRM_FacilityPractitionerTxNw`** ("Practitioner at Practice Location Taxonomy and Network"): the **Practitioner × PracticeLocation × Taxonomy × Role × Network** combination (the highest-cardinality records — hence a batch).

**Legacy:** `PRMDRCreatePractitionerFacilityNetwork`, `PRMDRCreateHFNPractitionerNetworkRecords`, `PRMDRPFacilityPractitionerTxNw` (+ `PRMDRPracCreateHCFacilityNetworkRecordNewGroup`).

`**HealthcareFacilityNetwork` field map (RT `PRM_FacilityPractitionerTxNw`):**


| Field                                     | Source                                                           |
| ----------------------------------------- | ---------------------------------------------------------------- |
| `RecordTypeId`                            | RT `PRM_FacilityPractitionerTxNw`                                |
| `Name`                                    | formula `SUBSTRING(PracFacilityName, 0, 254)` → `name.left(254)` |
| `HealthcareFacilityId`                    | `FacilityNetworkData:PracticeLocationId` **[KEY]**               |
| `AccountId`                               | `…GroupId` / `VendorAccountId` **[KEY]**                         |
| `PractitionerId`                          | `PractitionerId` **[KEY]**                                       |
| `PRM_Taxonomy__c` / `PRM_TaxonomyCode__c` | `…CareTaxonomyId` / `…CareTaxonomyCode` **[KEY]**                |
| `PRM_ProviderType__c`                     | `…VendorTypeId`                                                  |
| `PRM_Primary__c`                          | `…isPrimarySpecialty`                                            |
| `IsActive`                                | `IsActive`                                                       |
| `PRM_Pending__c`                          | `IsPending` / formula                                            |
| `EffectiveFrom` / `EffectiveTo`           | `EffectiveDate` / `EffectiveTo`                                  |
| `PRM_CaseManager__c`                      | `IndividualAppId`                                                |


> **⚠ CL‑E2‑4:** both active network DRs target `**HealthcareFacilityNetwork`**. The plan/flow doc also mention `**HealthcarePractitionerFacilityNetwork` (HCPFN)** — no active DR for that object was found. Confirm whether HCPFN is created (and by which DR) or whether HCFN is the sole network object.

**Design:** async worker reads the parent job's ContentVersion payload (Epic C `jsonFileParser`), builds `HealthcareFacilityNetwork` in bulk (chunked by `PRM_BatchSize__c`), `Name` truncated to 254, RT via describe; idempotent on the composite key set above. **DoD:** runs under async governor budget; bulk insert; status/finish via Epic C; tests with a `PRM_ServiceBase` stub.

---

## E22 · `PRM_PLRelatedBatch` — Batch orchestrator *(PLRelatedBatch · seq 4)*

> **Batch design (authoritative):** `PLRelatedBatch Related Services/E22_PRM_PLRelatedBatch.md`. Mirrors E20/E21: `(Id jobId, Id stepDetailId)` constructor, `Database.Batchable<Object>, Database.Stateful`, NPI correlation, halt-on-failure. **Wires E14 → E15 → E19 (CMA) → E16 (CDM)** per practitioner; aggregates one CMA call; updates the CDM (UPDATE path). **`BatchSize=1`** recommended (shared-location races). Resolves each location's **HealthcareFacility Id** by recomputing the composite `HealthcareFacility.PRM_ExternalId__c` via the **shared `PRM_FormSubUtility.computeHcfExternalId(...)` helper** (also used by E13) + a bulk query — keeps E14/E15 SOQL-free.

---

## E3.Effort (Part 3 — PLRelatedBatch + Level4RecordCreationBatch)


| Service                                           | Est (d) |
| ------------------------------------------------- | ------- |
| E14 `PRM_HPFService` (PLA + PPA, single service)  | 1.5 |
| E15 `PRM_ProviderFeatureService` (AssistiveAid + ACC) | 1.5 |
| ~~E17 `PRM_HealthcareFacilityNetworkService`~~     | — (DROPPED — trigger side-effect of E18) |
| E18 `PRM_Level4RecordCreationService` ⚡ (batch; incl. trigger-made HFN) | 2.0 |
| E22 `PRM_PLRelatedBatch` (batch orchestrator)     | (with E14/E15) |
| `GroupRelatedBatch` (seq 3)                        | — (TBD, CL-15) |
| **Total (Part 3)**                                | **5.5** |


> **EPIC E grand total (Part 1 + Part 2 + Part 3): ~23.0 d** — Part 1 11.0 · Part 2 6.5 · Part 3 5.5.

---

## E3.CL — Clarification Log (Part 3 services)

> CL ref IDs are preserved from the pre-reorg layout so existing cross-references resolve.


| Ref      | Item                                                                                                                                                                                                                                                                                                              | Evidence                                                                             | Action                                                                                                                                             |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL‑E2‑4  | **HCPFN object.** Active network DRs only write `HealthcareFacilityNetwork`; plan also references `HealthcarePractitionerFacilityNetwork`.                                                                                                                                                                        | `PRMDRCreatePractitionerFacilityNetwork`, `PRMDRCreateHFNPractitionerNetworkRecords` | Confirm if HCPFN is created (which DR) or HCFN is sole — Tech Lead                                                                                 |
| CL‑E2‑5  | **PPL has no own object.** "PractitionerPracticeLocation" = `HealthcarePractitionerFacility` with RT `PRM_PractitionerPracticeAffiliation`.                                                                                                                                                                       | `PRMDRCreatePPLForPPA`                                                               | Confirmed; flow doc rows that list `PractitionerPracticeLocation` should map to HCPF/RT — Eng                                                      |
| CL‑E2‑11 | **✅ SUPERSEDED — E15 owns ACC too.** Org check of the **active** IP `PRMPractitionerAddressCreation` v5 shows it creates **both** AssistiveAid (`PRMDRCreateProviderFeatureAssitiveAids`) **and** AffirmingCareCategory (`PRMDRCreateProviderFeatureACC`). E15 now covers **both RTs** (per-location). | active IP `PRMPractitionerAddressCreation` v5 (org) | ✅ Resolved — ACC in scope (E15 folder doc §6.2) |
| CL‑E2‑13 | **✅ RESOLVED — E14/E15 run in `PLRelatedBatch` (seq 4).** E13 does **not** invoke E14/E15 in-process; the batch mapping is authoritative (orchestrated by **E22**). | E22/E13/E14/E15 folder docs | ✅ Resolved — ratified model |
| CL‑E2‑17 | **✅ E17 DROPPED.** The facility-grain `HealthcareFacilityNetwork` (`PRM_FacilityNw`+`PRM_FacilityTx`) is a **trigger side-effect** of E18's insert of the **Level-4 `HealthcareFacilityNetwork` RT `PRM_FacilityPractitionerTxNw`**, not a standalone service. Its CMA/CDM belong to E18. | `PRM_HealthcareFacilityNetworkTrigger`/`PRM_HCFacilityNetworkTriggerHelper` (org); E18/E23 docs | ✅ Resolved — no E17 service |
| CL‑15    | **GroupRelatedBatch services.** Sequence 3 batch has no services assigned. Confirm its scope (group follow-on records) or drop it.                                                                                                                                                                                 | Plan §8.1; batch↔service mapping                                                     | Assign services or drop seq 3 — BA/Tech Lead                                                                                                       |


---

> **Part 1 (intake + PractitionerBatch — E1 · E2 · E5 · E6 · E7 · E8 · E10 · E11 · E16 · E19):** see `**Epic_E_Practitioner_Services.md`** (shared conventions §E0–E0.3).
> **Part 2 (PracticeLocationAndGroupBatch — E3 · E13 · E9 · E12):** see `**Epic_E_Practitioner_Services_Part2.md`**.
> **Batch designs:** E20 `PRM_PractitionerBatch` (seq 1) · E21 `PRM_PracticeLocationAndGroupBatch` (seq 2) · **E22 `PRM_PLRelatedBatch` (seq 4)** — under `epic-e-services/**/`.
>
> EPIC E (E1–E18) is organized **by batch** across Part 1 + Part 2 + Part 3, grounded in the active OmniStudio metadata + org schema, to support **sequential build** (one batch shipped end-to-end before the next). **Recent:** E14 single-service both RTs; E15 both RTs (AssistiveAid + ACC); **E17 dropped** (trigger side-effect of E18); E14/E15 in `PLRelatedBatch` (seq 4, E22).
