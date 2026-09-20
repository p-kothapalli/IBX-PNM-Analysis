# Epic E — Practitioner Creation Services (Implementation Guide) · Part 2 · PracticeLocationAndGroupBatch

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.6) · `PRM_Implementation_Plan.md` (§8) · **Part 1:** `Epic_E_Practitioner_Services.md` (intake + PractitionerBatch — shared conventions §E0–E0.3 & the legacy entry path).
> **Goal:** the **`PracticeLocationAndGroupBatch`** services (seq 2): **E3** `PRM_GroupService` · **E13** `PRM_HealthcareFacilityCreationService` · **E9** `PRM_FileService` · **E12** `PRM_HealthcareProviderNpiService`. These build the group/vendor graph, the new-location facility graph, document associations, and the reusable NPI create/update.
> **Estimate (Part 2):** ~6.5 engineer-days · **Depends on:** EPIC A/B/D + Part 1 (intake E1; conventions). · **Blocks:** EPIC F (intake wrapper), Part 3 (PLRelatedBatch consumes facility/location Ids).

> **🔄 Reorganized by batch (sequential build).** Epic E is split **by the batch a service runs in** so each batch can be built end-to-end before the next. **This is Part 2 = `PracticeLocationAndGroupBatch`.** Conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) and the batch↔service mapping are in **Part 1 §E0.1–E0.2** and apply here unchanged. E‑numbers and CL ref IDs are preserved from the pre-reorg layout.

> **🔄 Async-only model:** these services run **inside the `PracticeLocationAndGroupBatch`** class, sequenced by `PRM_AsyncOrchestrator` (seq 2) with halt-on-failure; no synchronous orchestrator. Within the batch: **E3** (group/vendor) → **E13** (new-location facility graph) → **E9** (documents) → **E12** (NPI create/update, reusable). **Batch ↔ service mapping: see Part 1 + Plan §8.1.**

> **Grounding:** all field maps/formulas extracted from the in-repo **active** OmniStudio DataRaptors (single-version `_1` unless noted). Where `isActive` is unreliable on an IP family or the metadata diverges from the plan, it's flagged in **§E2.CL**.

---

## E2.0 Record types referenced by Part 2 services (from DR `QUERY` formulas)


| SObject                        | DeveloperName                         | Used by                        |
| ------------------------------ | ------------------------------------- | ------------------------------ |
| Account                        | `PRM_Vendor`                          | E3 (group/vendor)              |
| Identifier                     | `PRM_Vendor`                          | E3 (group/vendor)              |
| Identifier                     | `PRM_Document`                        | E9 (file)                      |
| HealthcarePractitionerFacility | `PRM_PractitionerLocationAffiliation` | E13 (location affiliation)     |
| HealthcarePractitionerFacility | `PRM_PractitionerPracticeAffiliation` | E13 (PPL/“PPA”)                |


> Resolve all of these via the shared cached helper **`PRM_FormSubUtility.recordTypeId(SObjectType, devName)`** (CL-E5 resolved; **not** a separate `PRM_RecordTypeUtil`) — never the legacy `QUERY(...)`.

---

## E3 · `PRM_GroupService` — *1.5 d* · Branch: DELEGATED · *(PracticeLocationAndGroupBatch)*

**Legacy:** `PRMPostGroupPractitionerCreation` (Load) — invoked by element `**DRCreateGroupRecords*`* in IP `PRM_DelegatedPractitionerCreation` v7. **Writes:** `Account` (Vendor/Group), `Identifier` (Vendor), `HealthcareProviderNpi` (group), `HealthcareProvider` (group).

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, and the `**caseManagerId**` from E1. Constants set by the service: `npiType = "Organization"`, `ParticipationStatus = "Participating"`. All `…Val` fields are formula-derived (new-vs-existing gating).

```apex
public with sharing class PRM_GroupService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Id caseManagerId = (Id) params.get('caseManagerId');     // from E1
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        Map<String, Object> groupInfo = (Map<String, Object>) input.get('groupInfo');

        // resolve new-vs-existing (groupInfo.existingGroupId), compute *Val formulas,
        // build Account(Vendor) + Identifier + HealthcareProviderNpi + HealthcareProvider, then DML.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format** — a `groupInfo` node + shared effective/active context (constants & `…Val` fields are service-computed):

```json
{
  "groupInfo": {
    "groupTypeAhead": "Acme Medical Group",
    "groupTaxId": "12-3456789",
    "groupNPI": "9876543210",
    "credentialingStatus": "",
    "existingGroupId": "",
    "existingGroupNPIId": "",
    "tinId": ""
  },
  "isActive": false,
  "effectiveFrom": "",
  "effectiveTo": ""
}
```

> **Service-set constants (do NOT send):** `HealthcareProviderNpi.NpiType = "Organization"`, `Account.PRM_ParticipationStatus__c = "Participating"`, `PRM_Pending__c` default per gating. **Formula-derived (do NOT send):** `…Val` fields (`EffectiveFromVal`, `EffectiveToVal`, `IsActiveVal`, `CaseManagerIdVal`, `PendingVal`, `CredentialingStatusVal`, `HPStatus`), `SourceSystemId` / `SourceSystemIdentifier`, vendor record types.

### IP grounding (`PRM_DelegatedPractitionerCreation` v7 → element `DRCreateGroupRecords` → `PRMPostGroupPractitionerCreation`)


| DR input                               | IP source                                         | E3 mapping                      |
| -------------------------------------- | ------------------------------------------------- | ------------------------------- |
| `GroupInformation`                     | `PractionerGroup:GroupInformation`                | `groupInfo` node                |
| `CaseManagerId`                        | `DRPAccountCaseCaseManagerCreation:CaseManagerId` | `params.caseManagerId`          |
| `IsActive`                             | `RecordsToUpdate:IsRecordActive`                  | `isActive`                      |
| `EffectiveDate` / `EffectiveTo`        | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`   | `effectiveFrom` / `effectiveTo` |
| `npiType`                              | `"Organization"` (constant)                       | service constant                |
| `GroupInformation:ParticipationStatus` | `"Participating"` (constant)                      | service constant                |
| `PRM_Pending__c`                       | `False` (constant)                                | service constant                |


**Field map (grounded):**


| Target                | Field                                         | Source                                               |
| --------------------- | --------------------------------------------- | ---------------------------------------------------- |
| Account               | `RecordTypeId`                                | ⟲ RT `PRM_Vendor` (Account)                          |
| Account               | `Name` / `accName`                            | `groupInfo.groupTypeAhead`                           |
| Account               | `Id`                                          | `groupInfo.existingGroupId` (existing)               |
| Account               | `Type` / `PRM_VendorType__c`                  | ⟲ formula (vendor)                                   |
| Account               | `HealthCloudGA__SourceSystemId__c`            | ⟲ `SourceSystemId` (new only)                        |
| Account               | `PRM_ParticipationStatus__c`                  | `"Participating"` (constant)                         |
| Account               | `PRM_CredentialingStatus__c`                  | ⟲ `CredentialingStatusVal`                           |
| Account               | `IsActive`                                    | ⟲ `IsActiveVal`                                      |
| Account               | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| Account               | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| Account               | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| Identifier            | `RecordTypeId`                                | ⟲ RT `PRM_Vendor` (Identifier)                       |
| Identifier            | `IdValue`                                     | `groupInfo.groupTaxId`                               |
| Identifier            | `Id`                                          | `groupInfo.tinId` (existing)                         |
| Identifier            | `ParentRecordId` / `PRM_Type__c`              | ⟲ formula (← Account)                                |
| Identifier            | `PRM_Active__c`                               | ⟲ `IsActiveVal`                                      |
| Identifier            | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| Identifier            | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| Identifier            | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| HealthcareProviderNpi | `Npi` / `Name`                                | `groupInfo.groupNPI` (`Npi` **[KEY]**)               |
| HealthcareProviderNpi | `Id`                                          | `groupInfo.existingGroupNPIId` (existing)            |
| HealthcareProviderNpi | `NpiType`                                     | `"Organization"` (constant)                          |
| HealthcareProviderNpi | `EffectiveFrom` / `EffectiveTo`               | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| HealthcareProviderNpi | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| HealthcareProviderNpi | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| HealthcareProvider    | `Name`                                        | `groupInfo.groupTypeAhead`                           |
| HealthcareProvider    | `AccountId`                                   | ⟲ formula (← Account)                                |
| HealthcareProvider    | `Status`                                      | ⟲ `HPStatus`                                         |
| HealthcareProvider    | `SourceSystemIdentifier`                      | ⟲ `SourceSystemIdentifier` (existing only) **[KEY]** |
| HealthcareProvider    | `EffectiveFrom` / `EffectiveTo`               | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| HealthcareProvider    | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |


**Formulas → Apex** (all gate on `String.isBlank(groupInfo.existingGroupId)` = **new group**):

- `EffectiveFromVal` / `EffectiveToVal` / `IsActiveVal` / `CaseManagerIdVal` = `isNew ? <value> : null` (suppressed for existing groups).
- `CredentialingStatusVal` = `isNew ? groupInfo.credentialingStatus : null`.
- `PendingVal` = `isNew ? false : null`.
- `HPStatus` = `isNew ? (isActive ? 'Active' : 'Inactive') : null`.
- `SourceSystemId` (Account) = `isNew ? groupTaxId + '-' + groupTypeAhead : null` (**new** only).
- `SourceSystemIdentifier` (HealthcareProvider) = `!isNew ? groupTaxId + '-' + groupTypeAhead : null` (**existing** only — the inverse).
- Vendor RTs (Account + Identifier) via cached describe (`PRM_Vendor`).

> **New-vs-existing:** when `existingGroupId`/`tinId`/`existingGroupNPIId` are supplied the service **reuses** them (sets `Id`) and the `…Val` fields go null; `SourceSystemIdentifier` (HCP) is set only for the existing path, `SourceSystemId` (Account) only for the new path.

**DML / order:** insert **Account (Vendor)** → then **Identifier** (FK `ParentRecordId` = Account), **HealthcareProviderNpi**, **HealthcareProvider** (FK `AccountId` = Account) — one bulk DML per type. Returns `groupAccountId`, `groupIdentifierId`, `groupNpiId`, `groupHealthcareProviderId`.

---

## E13 · `PRM_HealthcareFacilityCreationService` — *3.0 d* · Branch: BOTH (new location) · *(PracticeLocationAndGroupBatch · seq 2)*

> **🔄 Build spec (authoritative):** `PracticeLocationAndGroupBatch Related Services/E13_PRM_HealthcareFacilityCreationService.md` (+ `_Execution_Plan.md`). **✅ Runs in-batch (seq 2)** — not a separate async worker (OQ-E13-2). **✅ CL‑E2‑13 resolved:** E13 does **NOT** invoke E14/E15 in-process — they run in **`PLRelatedBatch` (seq 4, E22)**. **E12 folded into E13** (E13 owns the location NPI).

Creates the **new-location graph** (gated on the `HealthcareFacility` not already existing): `HealthcareProviderNpi` (location NPI) → `Location` → `Address[]` → `HealthcareFacility`. ⚠ **On HealthcareFacility insert the trigger (`PRM_HCFacilityTriggerHelper`) auto-creates `PRM_HealthcareFacilityNPI__c` (Location NPI History) and populates `HealthcareFacility.PRM_ExternalId__c`** — E13 must **not** do those.

> **✅ Shared idempotency helper.** The create/pre-check gate = the composite `HealthcareFacility.PRM_ExternalId__c` (the trigger's `populatePRMExternalId` formula). E13 computes it via the **shared `PRM_FormSubUtility.computeHcfExternalId(...)` helper** — the **same helper E22 uses** to resolve HCF Ids for E14/E15 (single source of truth; no drift). Requires `Account.SourceSystemIdentifier` on the group Account (OQ-E13-18/OQ-E21-2).

> **Grounding:** field maps reused from `PRMDRCreatePractitionerAddAddressRecords` (the fused Address + HealthcareFacility + Location DR) for the create columns.

**`Location` field map:** `Name` ← `location.name`; `LocationType` ← `locationType`; `PRM_TelehealthOnly__c` ← `telehealthOnly`; `PRM_EffectiveFrom__c` ← `effectiveDate`; `PRM_Pending__c` ⟲; `PRM_CaseManager__c` ← `caseManagerId`.

**`Address` field map (grounded):** `PRM_AddressLine1__c`/`2`, `PRM_City__c`/`State__c`/`Zip__c`/`Zip4__c`, `PRM_County__c`/`StateCounty__c`, `PRM_Phone__c`/`PhoneExtension__c`/`Fax__c`, `PRM_Geolocation__Latitude__s`/`Longitude__s`, `PRM_AddressType__c`/`LocationType`, `PRM_Standardized__c`, `PRM_EffectiveFrom__c` ← `effectiveDate`, `ParentId` ⟲ (Location/Account), `PRM_Pending__c` ⟲, `PRM_CaseManager__c`.

**`HealthcareFacility` field map (grounded):** `Name` ← `hcFacilityName`; `AccountId` ← `account`; `PRM_PracticeName__c` ← `hcFacilityPracticeName`; `PRM_Primary__c` ← `primaryPracticeLoc`; `PRM_PracticeClassification__c` ← `practiceClassification`; `PRM_NpiId__c` ← `existingGroupNPI`; `LocationId` ⟲ (← Location); `PRM_BillingType__c` ⟲; `PRM_Pending__c` ⟲; `PRM_CaseManager__c`.

**Invoked services:** **none in-process.** E14 (`PRM_HPFService`) and E15 (`PRM_ProviderFeatureService`) run later in **`PLRelatedBatch` (seq 4, E22)** — they consume E13's HealthcareFacility Ids (resolved by E22 via the shared composite helper). *(CL‑E2‑13 resolved.)*

**DML / order (one bulk DML per type, FK order, gated on new HCF):** `HealthcareProviderNpi` (location NPI, E12-folded) → `Location` → `Address[]` (ParentId) → `HealthcareFacility` (LocationId, `PRM_NpiId__c`). ⚡ The HCF trigger then creates the Location NPI History + populates `PRM_ExternalId__c`. Returns the created Ids (`locationId`, `addressIds`, `healthcareFacilityId`, `locationNpiId`).

---

## E9 · `PRM_FileService` — *1.0 d* · Branch: DELEGATED (gated on file present) · *(PracticeLocationAndGroupBatch)*

**Legacy:** `PRMDRCreateIdentiferAndDocument` (Load) — element `DRCreateIdentiferAndDocument` in `PRM_DelegatedPractitionerCreation` v7 (`sendJSONPath = SV_AdditionalNodesToFileData`). **Writes:** `Identifier` (Document RT), `ContentDocumentLink`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput`**, and `caseManagerId`.

```apex
public with sharing class PRM_FileService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        List<Object> files = (List<Object>) input.get('files');     // SV_AdditionalNodesToFileData rows
        if (files == null || files.isEmpty()) { response = new Map<String,Object>(); return response; }
        Id caseManagerId = (Id) params.get('caseManagerId');
        // build Identifier[] (Document RT) + ContentDocumentLink[]; insert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format** (one row per uploaded file — the legacy `SV_AdditionalNodesToFileData` node):

```json
{
  "files": [
    { "contentDocumentId": "", "linkedEntityId": "", "parentRecordId": "", "filename": "credentialing_packet.pdf",
      "type": "", "documentType": "", "documentNotes": "", "targetLocation": "", "formProcess": "", "npi": "", "taxId": "" }
  ]
}
```

`DRCreateIdentiferAndDocument` is fed via `sendJSONPath = SV_AdditionalNodesToFileData` (the file-data node) → `files[]`; `CaseManagerId` from the orchestrator context → `params.caseManagerId`.

**Field map (grounded):**


| Target              | Field                                          | Source                                                       |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------------ |
| Identifier          | `RecordTypeId`                                 | ⟲ RT `PRM_Document` (Identifier) **[KEY]**                   |
| Identifier          | `ParentRecordId`                               | `files[].parentRecordId` **[KEY]**                           |
| Identifier          | `PRM_Type__c` / `PRM_DocumentType__c`          | `files[].type` / `documentType`                              |
| Identifier          | `PRM_DocumentName__c` / `PRM_DocumentNotes__c` | `files[].filename` / `documentNotes`                         |
| Identifier          | `PRM_TargetLocation__c` / `PRM_FormProcess__c` | `files[].targetLocation` / `formProcess`                     |
| Identifier          | `PRM_NPI__c` / `PRM_TaxId__c`                  | `files[].npi` / `taxId`                                      |
| Identifier          | `PRM_Pending__c`                               | ⟲ formula `IF(type!="Document", true, false)`                |
| Identifier          | `PRM_CaseManager__c`                           | `params.caseManagerId`                                       |
| ContentDocumentLink | `ContentDocumentId`                            | `files[].contentDocumentId` **[KEY]**                        |
| ContentDocumentLink | `LinkedEntityId`                               | ⟲ formula → `files[].linkedEntityId` (Case/parent) **[KEY]** |


**Gating / DML:** only when `files` non-empty; insert Identifier[] → ContentDocumentLink[]. Returns `fileIdentifierIds`, `contentDocumentLinkIds`.

---

## E12 · `PRM_HealthcareProviderNpiService` — *1.0 d* · reusable (sync/async) · *(PracticeLocationAndGroupBatch)*

**Purpose:** create **or update** `HealthcareProviderNpi`. **Reuses `PRM_OmniUtils.updateExistignHCPNPI(inputMap, outMap)`** (verified — `PRM_OmniUtils.cls`) for the existing-NPI update path; new NPIs are built directly. Used by **E2** (practitioner NPI), **E3** (group NPI), and **E13** (facility group NPI) — so it is a shared sub-service, not a per-flow service.

**Method signature** — `extends PRM_ServiceBase`; `params` = `flow`, `jsonInput`, `caseManagerId` (+ FK `accountId`/`practitionerId` when creating).

```apex
public with sharing class PRM_HealthcareProviderNpiService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        // existingHcpNpiId present → PRM_OmniUtils.updateExistignHCPNPI(...) ; else build new HealthcareProviderNpi
        response = new Map<String, Object>();
        return response;
    }
}
```

**Field map (grounded — NPI columns of `PRMDRPHCPNPIBoardCretIdentifier` / `PRMPostGroupPractitionerCreation`):** `Npi`/`Name` ← `npi`; `NpiType` ← `npiType`; `AccountId`/`PractitionerId` ← `params`; `IsActive`/`EffectiveFrom`/`EffectiveTo` ← gated `IF(ISBLANK(existingHcpNpiId), …, null)`; `PRM_CaseManager__c` ← `params.caseManagerId`. **Update path:** delegate to `PRM_OmniUtils.updateExistignHCPNPI`.

**DML:** insert new NPIs (bulk) + update existing (via the reused method). Returns `healthcareProviderNpiIds`.

---

## E2.Effort (Part 2 — PracticeLocationAndGroupBatch)


| Service                                           | Est (d) |
| ------------------------------------------------- | ------- |
| E3 `PRM_GroupService`                             | 1.5     |
| E13 `PRM_HealthcareFacilityCreationService` (in-batch seq 2; E12 folded) | 3.0 |
| E9 `PRM_FileService`                              | 1.0     |
| E12 `PRM_HealthcareProviderNpiService` (reusable) | 1.0     |
| **Total (Part 2)**                                | **6.5** |


> **EPIC E grand total (Part 1 + Part 2 + Part 3): ~23.5 d** — Part 1 11.0 · Part 2 6.5 · Part 3 6.0.

---

## E2.CL — Clarification Log (Part 2 services)

> CL ref IDs are preserved from the pre-reorg layout so existing cross-references resolve.


| Ref      | Item                                                                                                                                                                                                                                                                                                              | Evidence                                                                             | Action                                                                                                                                             |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL‑E6 | **Group DR source (resolved).** E3 is grounded to `PRMPostGroupPractitionerCreation` via the Delegated IP element `DRCreateGroupRecords` (not the standalone `PRM_CreateGroupScreenRecord` lineage).                                                                                                                     | `PRM_DelegatedPractitionerCreation` v7                                                                                                                    | Resolved — use `PRMPostGroupPractitionerCreation`                                                                                                                                                           |
| CL‑E7 | **Group typeahead inputs.** `groupInfo` maps the `GroupInformation:GroupTypeAhead-Block:*` keys (`groupTypeAhead`, `tinId`, `existingGroupId`, `existingGroupNPIId`); confirm the OmniScript `PractionerGroup:GroupInformation` payload contract.                                                                        | `PRMPostGroupPractitionerCreation`                                                                                                                        | Map to `GroupPayload` in EPIC F — Eng                                                                                                                                                                       |
| CL‑E2‑2  | **Address IP not in pilot (superseded by CL‑E2‑9).** `PRM_CreatePractitionerAddressRecords` is the **PAR**/shared address IP (called by `PRM_CreateParFormRecords`), not the Practitioner Creation chain.                                                                                                         | IP call graph                                                                        | See CL‑E2‑9; address creation is out of pilot scope                                                                                                |
| CL‑E2‑6  | **Address DR fusion (PAR only).** `PRMDRCreatePractitionerAddAddressRecords` (Address+HCF+HCPF+Location fusion) is a **PAR** address-IP DR — not in the Practitioner Creation chain (see CL‑E2‑9).                                                                                                                | DR objs; IP call graph                                                               | N/A for the pilot; relevant if E12 is re-introduced for PAR                                                                                        |
| CL‑E2‑7  | **ContentDocumentLink defaults.** `ShareType`/`Visibility` not in the map.                                                                                                                                                                                                                                        | `PRMDRCreateIdentiferAndDocument`                                                    | Confirm CDL defaults during E9 build — Eng                                                                                                         |
| CL‑E2‑8  | **Existing-NPI / existing-group gating** reuses the same `ISBLANK(existingId)` pattern as E2/E3.                                                                                                                                                                                                                  | HCPF DRs                                                                             | Centralize the new-vs-existing branch in the payload model — Eng                                                                                   |
| CL‑E2‑9  | **Address/HCF creation is async (new-location path).** The **sync** chain only links existing facilities; new `Location`/`Address`/`HealthcareFacility` are created by the **async `PRM_HealthcareFacilityCreationService` (E13)**, reusing the `PRMDRCreatePractitionerAddAddressRecords` field maps (a PAR/shared DR invoked async here). | PPL sub-IP v2; address DR                                                         | Confirm the async new-location trigger condition + payload node — BA/Tech Lead |
| CL‑E2‑10 | **Role/Network builder is Apex.** `PRMDRPFacilityPractitionerTxNw` is fed by the Apex remote `RA_GetFacilityPractitionerRoleNTxNw` (fans out networks × taxonomies per location).                                                                                                                                 | PPL sub-IP v2 element `DRPFacilityPractitionerTxNw`                                  | Port `RA_GetFacilityPractitionerRoleNTxNw` to a selector/builder for E13 — Eng                                                                     |
| CL‑E2‑13 | **✅ RESOLVED — E14/E15 run in `PLRelatedBatch` (seq 4, E22).** E13 does **not** invoke E14/E15 in-process; it creates the location/facility graph only, and E22 later resolves the HCF Ids (shared `computeHcfExternalId` helper) to feed E14/E15. | E13/E22 folder docs; batch mapping | ✅ Resolved — ratified model |


---

> **Part 1 (intake + PractitionerBatch — E1 · E2 · E5 · E6 · E7 · E8 · E10 · E11 · E16):** see `**Epic_E_Practitioner_Services.md`** (shared conventions §E0–E0.3).
> **Part 3 (PLRelatedBatch + Level4RecordCreationBatch + GroupRelatedBatch TBD — E14 · E15 · E18; ~~E17~~ dropped):** see `**Epic_E_Practitioner_Services_Part3.md`**.
