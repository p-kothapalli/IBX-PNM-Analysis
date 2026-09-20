# USER STORY: Delegated Practitioner — Move Address Creation IP to Batch (Sub‑3s Submit + Navigate to Case Manager)

**Persona:** Credentialing Specialist (Delegated), Salesforce Developer
**Priority:** P0 — Submit takes ~10s for 1 group / 15 locations even after the recent Network/IFC batch refactor; blocks data‑entry throughput and locks the browser tab.
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_DelegatedPractitionerAddressForm_English` (v9 — submit step) → `PRM_DelegatedPractitionerReviewScreen_English` (v5)
**Integration Procedures (impacted):**
- `PRM_AddressLogicContainer` (container, current v4) — entry point invoked from the OmniScript Submit
- `PRM_PractitionerAddressCreation` (child IP 1, current v5) — **TARGET to move to batch**
- `PRM_ExistingPrimaryPracticeLocationLogicDelg` (child IP 2, current v1) — **TARGET to absorb into batch**
- `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` (current v2, currently `isActive=false` in `PRM_DelegatedPractitionerCreation_Procedure_7`) — **resurrect inside the batch**
- `PRM_CreateDelegatedHFNRecords` (child IP 3, current v3) — already routed to `PRM_NetworkCreationBatch` via `PRM_OmniProcessUtils.enqueueNetworkCreation`; **no change required here** (story builds on top of the same envelope/helper/batch pattern)
**Apex (reference pattern to clone):** `PRM_NetworkCreationBatch.cls`, `PRM_NetworkCreationEnvelope.cls`, `PRM_NetworkCreationRow.cls`, `PRM_NetworkCreationHelper.cls`, `PRM_OmniProcessUtils.cls` (routes `enqueueNetworkCreation`)
**Relevant Requirements:** `PRM_NetworkCreation_Issue_Summary.md`, `PRM_NetworkCreation_BatchImplementation_Guide.md`, `US_PractitionerCreation_QueueableRefactor.md`, `PRM_FailedRecordStaging_Object_Specification.md`, `PRM_Batch_Rollback_Strategies.md`

---

## Story

**As a** Credentialing Specialist working a Delegated Practitioner request,
**I want** the “Submit” button on the Delegated Practitioner Address Form to return in **under 3 seconds** and automatically navigate me to the Case Manager (`IndividualApplication`) record, with address/HCPF/PFA/Practice‑to‑Practitioner creation continuing in the background,
**So that** I can move on to the next case immediately — without staring at a spinner, without risking double‑submits, and without manually re‑opening the Case Manager from the global search.

**Why it matters:** After the recent network/IFC batch refactor (PRM_NetworkCreationBatch, May 2026), the heaviest remaining synchronous work is `PRM_PractitionerAddressCreation` + `PRM_ExistingPrimaryPracticeLocationLogicDelg`. For the canonical sanity case (1 practitioner / 1 group / 15 locations), this still consumes **~10 seconds wall‑clock** because both IPs build Address, HealthcarePractitionerFacility (HCPF), ProviderFeatureAssignment (PFA), AssistiveAids, AffirmingCareCategory, and PracticeToPractitioner records inline under the OmniScript HTTP turn. With the current sample input — `Locations × CareTaxonomies × (PFA + PFAACC + AA + HCPF + PracToPract)` — the user perceives the entire transaction as “the form is broken”, and we routinely see duplicate `IndividualApplication` rows when users hit Submit twice. The fix is to apply the **same envelope → helper → `Database.Batchable<SObject>, Database.Stateful` → bell notification + IA status field** pattern proven by `PRM_NetworkCreationBatch`.

---

## Scope

| Flow | OmniScript | Affected IP / Element | Data Source |
|------|------------|----------------------|-------------|
| Delegated Practitioner Creation — Submit | `PRM_DelegatedPractitionerAddressForm_English_9` (Submit element invokes `PRM_AddressLogicContainer`) | `PRM_AddressLogicContainer_English_4` → `PractitionerAddressCreation` (seq 1.0) | `PRM_PractitionerAddressCreation_Procedure_5` |
| Delegated Practitioner Creation — Submit | Same | `PRM_AddressLogicContainer_English_4` → `ExistingPrimaryAddressLogic` (seq 3.0) | `PRM_ExistingPrimaryPracticeLocationLogicDelg_English_1` |
| Delegated Practitioner Creation — Submit | Same | `PRM_AddressLogicContainer_English_4` → `AddTaxNetworkLogic` (seq 4.0) | `PRM_CreateDelegatedHFNRecords_Procedure_3` (already async via `PRM_NetworkCreationBatch`) — **no change**, just confirm ordering |
| Practice‑Location summary records | `PRM_DelegatedPractitionerAddressForm_English_9` | `PRM_DelegatedPractitionerCreation_Procedure_7` → `IP_CreatePractitionerPracticeLocation` (seq 20.0, currently `isActive=false`) | `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_2` |
| Post‑submit navigation | `PRM_DelegatedPractitionerAddressForm_English_9` (Navigate Action) and/or `pRMPncAndDelegated` LWC | Final response from `PRM_AddressLogicContainer` must include `CaseManagerId` | n/a |

---

## Current State (from codebase)

### `PRM_AddressLogicContainer_English_4` (top‑level orchestrator)

Three child IPs run **inline under the OmniScript Submit**:

- **`PractitionerAddressCreation`** (seq 1.0) — Integration Procedure Action, `chainOnStep=true`, `integrationProcedureKey=PRM_PractitionerAddressCreation1`. Passes `locationsToUpsert`, `PractitionerScreenRecordIds`, `GroupRecordIds`, `PractitionerRole`, `FeatureConfigSetting`, `IsActive`, `IsPending`, `PractitionerEffectiveDate`, `PractitionerEffToDate`.
- **`ExistingPrimaryAddressLogic`** (seq 3.0) — Integration Procedure Action, `chainOnStep=true`, `integrationProcedureKey=PRM_ExistingPrimaryPracticeLocationLogicDelg`.
- **`AddTaxNetworkLogic`** (seq 4.0) — Integration Procedure Action, `disableChainable=true`, `remoteOptions.useQueueable=true`, `integrationProcedureKey=PRM_CreateDelegatedHFNRecords`. **Already async** — the user’s “network creation moved to batch” work. Under the hood `PRM_CreateDelegatedHFNRecords_Procedure_3` is what enqueues `PRM_NetworkCreationBatch` via `PRM_OmniProcessUtils.callMethod('enqueueNetworkCreation', …)` (see `PRM_OmniProcessUtils.cls` line 111–113 and `PRM_NetworkCreationHelper.enqueueNetworkCreation`).

Net effect today: the Container returns to the OmniScript only after IP1 and IP2 are fully complete; IP3 returns immediately because it is already queueable.

### `PRM_PractitionerAddressCreation_Procedure_5` (IP 1 — the heavy one)

Single‑transaction synchronous IP. Element bundles touched (grep of `bundle` keys):

- Address creation: `PRMDRCreatePractitionerAddressRecordswithNPIDelg`, `PRMDRCreatePractitionerAddAddressRecordsDelg`, `PRMDRCreatePractitionerNewAddressRecordsDelg`
- HCPF creation: `PRMDRCreateHealthcarePractitionerFacilityDelg`, `PRMDRCreateHCPFForPractitionerPracAffiliationDelg`
- Provider Feature Assignment (PFA) + transforms: `PRMDRCreatePracProviderFeatureACC`, `PRMDRCreateProviderFeatureACC`, `PRMDRPProviderFeatureACC`, `PRMDRTProviderFeatureACC`, `PRMDRTransformProviderFeatureACC`, `PRMDRTransformPFAA`, `PRMDRTransformPFACC`, `PRMDRTransformHCFacilityData`
- AssistiveAids: `PRMDRCreateProviderFeatureAssitiveAids`
- HFN bridge & InfoCode bridge: `PRMDRCreatePractitionerFacilityNetwork`, `PRMLoadInfoCodeAssigned`, `PRMLoadInfoCodeAssignedPracFacilities`, `PRMDRPracCreateHCFacilityNetworkRecordNewGroup`, `PRMDRCreatePracHealthCareFacilityNetworkForGroup`
- Practice‑to‑Practitioner: `PRMDRCheckIfPracticeToPractitionerExist`, `PRMUpdatePracticeToPractitionerDelg`, `PRMDRCreatePPLForPPADelg`
- Case Data Manager link: `PRMDRPCaseDataManager`
- Remote: `PRM_OmniUtils.updateExistignHCPNPI`

The IP fans out **per location × per taxonomy × per provider feature flavour**. For 15 locations × ~2 taxonomies that is roughly 90–150 child DML rows in a single synchronous turn — close to but not blowing the queueable governor ceiling, hence “slow but not failing” (10s).

### `PRM_ExistingPrimaryPracticeLocationLogicDelg_English_1` (IP 2)

Synchronous IP that handles the **already‑existing primary HCPF** path (when a Group/Address already has an HCPF for this practitioner). Creates: HCPF, PFA‑Affirming Care Category, PFA‑Assistive Aids, AffirmingCareCategory transforms, PracticeToPractitioner merges, and a final `UpdateCaseDataManager` step.

### `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_2`

Builds `HealthcarePractitionerFacility` records under the two `RecordType.DeveloperName` values `PRM_PractitionerPracticeAffiliation` and `PRM_PractitionerLocationAffiliation`, including the `FacilityPractitionerTxNw` rows (later consumed by the network batch). **Currently `isActive=false` in `PRM_DelegatedPractitionerCreation_Procedure_7` → `IP_CreatePractitionerPracticeLocation` (seq 20.0).** Confirm with team whether this was disabled because the work is now done elsewhere or because it is the *next* candidate to be wrapped into the new batch.

### Reference pattern already in production — `PRM_NetworkCreationBatch`

The story builds directly on the envelope/helper/batch trio committed on 2026‑05‑20:

- `PRM_NetworkCreationEnvelope.cls` — POJO carrying `caseManagerId`, `personContactId`, `practitionerAccountId`, `effectiveFrom`, `effectiveTo`, `isActive`, `isPending`, `List<PRM_NetworkCreationRow> rows`.
- `PRM_NetworkCreationRow.cls` — POJO for one HFN row (HCF + taxonomy + role + selected networks).
- `PRM_NetworkCreationHelper.enqueueNetworkCreation(input, outMap)` — deserializes, calls `Database.executeBatch(new PRM_NetworkCreationBatch(envelope), chunkSize)`, also enqueues `PRM_IfcLoader`. Returns `{ jobId, ifcJobId, success, errorMessage? }` synchronously in <100 ms.
- `PRM_NetworkCreationBatch` — `Database.Batchable<SObject>, Database.Stateful`. Memoizes lookups across chunks (line 13–14), writes failed rows to `PRM_FailedRecordStaging__c`, in `finish()` updates `IndividualApplication.PRM_ProcessingStatus__c` to `Success`/`Failed` and posts a bell notification via `PRM_NotificationHelper.sendBellNotification`.
- `PRM_OmniProcessUtils.cls` line 111–113 — `if (methodName == 'enqueueNetworkCreation') { return PRM_NetworkCreationHelper.enqueueNetworkCreation(inputMap, outMap); }` — single integration point for OmniStudio remote actions.

We will mirror this pattern 1:1 for address creation.

---

## Proposed Architecture (After)

```
TX1 — Synchronous (UI turn, target ≤ 3 s):
  PRM_AddressLogicContainer (v5, new)
    └── Remote Action: PRM_OmniProcessUtils.callMethod('enqueueAddressCreation', …)
          → PRM_AddressCreationHelper.enqueueAddressCreation(input, outMap)
              → builds PRM_AddressCreationEnvelope (one PRM_AddressCreationRow per location × taxonomy)
              → Database.executeBatch(new PRM_AddressCreationBatch(envelope), chunkSize=5)
              → returns {jobId, success:true, message:'Processing… You will be notified.'}
    └── (existing async IP3) PRM_CreateDelegatedHFNRecords → PRM_NetworkCreationBatch
    └── Response Action returns CaseManagerId, IndividualApplicationId, jobId, ifcJobId, addressJobId

TX2 — Async, separate transactions, per chunk (5 locations / chunk):
  PRM_AddressCreationBatch.execute()
    → For each PRM_AddressCreationRow:
        - upsert Schema.Address
        - upsert HealthcarePractitionerFacility (PRM_PractitionerPracticeAffiliation + PRM_PractitionerLocationAffiliation)
        - upsert Provider Feature Assignment (Capabilities, AssistiveAids, AffirmingCareCategory)
        - upsert PracticeToPractitioner (PRM_CrossReferencePractice* analog)
        - upsert HealthcareFacility ↔ Address ↔ Group bridge
        - log row‑level failures to PRM_FailedRecordStaging__c with exception log link
  PRM_AddressCreationBatch.finish()
    → Update IndividualApplication.PRM_AddressCreationStatus__c (Success / PartialFailure / Failed)
    → If success and PRM_NetworkCreationStatus__c also Success → IndividualApplication.PRM_ProcessingStatus__c = Success
    → PRM_NotificationHelper.sendBellNotification(owner, 'PRM_CustomNotitficationtoCaseOwner', ...)
```

### Why a batch (not just another queueable)

- Locations × taxonomies × feature flavours has historically pushed CPU and Heap past Queueable limits — the May `PRM_NetworkCreationBatch` change made that explicit (see comment in `PRM_NetworkCreationBatch.cls` line 12: *“IA‑0000150602: SOQL=201 fix, 2026‑05‑20”*). Batches give us per‑chunk SOQL/CPU budgets and `Database.Stateful` memoization across chunks, which Queueables do not.
- We already have the staging + bell + status pattern; reusing it keeps the operational surface uniform for the Network Management QC team.

### Why NOT Platform Event‑driven (the original 2026‑02 proposal in `PRM_NetworkCreation_BatchImplementation_Guide.md`)

The May 2026 implementation chose the simpler `Helper.enqueue → executeBatch` route over `EventBus.publish → Trigger → Orchestrator → Batch`, because:
- One fewer hop, easier to observe in `AsyncApexJob`.
- `Database.Stateful` memoization (see `cachedHfNameToId`, `cachedPayerNetworkNameToId`) cuts SOQL by ~60 % across chunks.
- Same behaviour from the user’s perspective.

We will keep the same opinion for address creation.

---

## Technical Section (For Developers)

### A. New Apex artifacts (mirror `PRM_NetworkCreation*`)

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_AddressCreationEnvelope.cls`** | New Apex POJO | Fields: `Id practitionerAccountId; Id personContactId; Id caseManagerId; Id caseDataManagerId; Id caseId; Date effectiveFrom; Date effectiveTo; Boolean isActive; Boolean isPending; String practitionerName; String practitionerRole; String featureConfigSettingId; List<PRM_AddressCreationRow> rows;` |
| **`PRM_AddressCreationRow.cls`** | New Apex POJO | One row per **location × care taxonomy**. Fields drawn from `PRM_AddressLogicContainer` sample input (`locationsToUpsert.Locations[*]` + `Addresses[*]` + `CareTaxxonomyData[*]`): `String existingGroupNpiId; String existingGroupAccountId; String hcFacilityName; String hcNewFacilityName; String hcPractitionerFacility; String addressType; String addressLine1; String city; String state; String stateCounty; String county; String postalCode; String postalCodeWithZip4; String phone; String fax; String officeEmail; String capabilitiesAtLocationAPI; String selectedAdditionalTaxonomiesAPI; String selectedPrimaryTaxonomy; String careTaxonomyId; String careTaxonomyName; String careTaxonomyCode; Boolean isPrimarySpecialty; Boolean primaryPracticeLoc; Boolean telehealthEnabled; Boolean telehealthOnly; String doingBusinessAsName; String addressIdentifier; Boolean newPracticeLocationForExistingGroup; String affirmingCareCategoryAPI; String assistiveAidsId; ...` |
| **`PRM_AddressCreationHelper.cls`** | New Apex class | `public static Map<String,Object> enqueueAddressCreation(Map<String,Object> input, Map<String,Object> outMap)`. Parses `locationsToUpsert`, `PractitionerScreenRecordIds`, `PractitionerEffectiveDate`, `PractitionerEffToDate`, `IsActive`, `IsPending`, `PractitionerRole`, `FeatureConfigSetting`, `ProviderInformationAffirmingCategory`. Flattens `Locations[].Addresses[].CareTaxxonomyData[]` into a list of `PRM_AddressCreationRow`. Calls `Database.executeBatch(new PRM_AddressCreationBatch(envelope), chunkSize)` (default 5). Returns `{ jobId, success, message, errorMessage? }`. **Must never throw** — wraps everything in try/catch and logs to `PRM_ExceptionLogger`. |
| **`PRM_AddressCreationBatch.cls`** | New Apex class — `implements Database.Batchable<SObject>, Database.Stateful` | See **Section B** for skeleton. Mirrors `PRM_NetworkCreationBatch` for staging, partial‑failure handling, finish‑time IA status + bell notification. |
| **`PRM_AddressCreationHelperTest.cls`** | New Apex test | ≥ 90 % coverage; exercises null caseManagerId, empty rows, single row, 15‑location chunked path, Vlocity single‑object‑instead‑of‑list edge case (see `PRM_NetworkCreationHelper.parseTxNwRows` line 116–121). |
| **`PRM_AddressCreationBatchTest.cls`** | New Apex test | ≥ 90 % coverage; happy path, partial‑failure path (one row force‑fails), full‑failure path (envelope nulled), `finish()` writes IA `PRM_AddressCreationStatus__c` and posts notification. Pattern‑match `PRM_NetworkCreationBatchTest.cls`. |
| **`PRM_OmniProcessUtils.cls`** | Apex (existing class) | **Add new route** alongside line 111: `if (methodName == 'enqueueAddressCreation') { return PRM_AddressCreationHelper.enqueueAddressCreation(inputMap, outMap); }`. **No removal of existing routes.** |
| **`PRM_FailedRecordStaging__c`** | Custom Object (existing) | Add picklist value `'PRM_AddressCreationBatch'` to `PRM_SourceFlow__c` so Network Management QC can filter staged failures by origin. No schema change beyond the picklist. |
| **`IndividualApplication`** | Custom Field (new) | `PRM_AddressCreationStatus__c` — Picklist (restricted): `Not Started` (default), `Queued`, `Processing`, `Success`, `Partial Failure`, `Failed`. **Mirror `PRM_ProcessingStatus__c` already used by the Network batch.** |
| **`IndividualApplication`** | Custom Field (new, optional) | `PRM_AddressCreationError__c` — LongTextArea(32768) for finish()‑time aggregated error summary. Optional — `PRM_FailedRecordStaging__c` already carries per‑row detail. |
| **`PRM_NetworkCreationBatch.finish()`** | Apex (existing) | Update the “overall success” logic in `updateCaseManagerStatusAndNotify` to consider BOTH `PRM_AddressCreationStatus__c` and the network outcome before setting `PRM_ProcessingStatus__c = 'Success'`. (Or simpler: both batches set their own status field, and a small `PRM_PostSubmitStatusEvaluator` queueable rolls them up — see Clarifications.) |

### B. `PRM_AddressCreationBatch` — implementation skeleton

```apex
public with sharing class PRM_AddressCreationBatch
    implements Database.Batchable<SObject>, Database.Stateful {

    @TestVisible private final PRM_AddressCreationEnvelope envelope;
    @TestVisible private Integer successCount = 0;
    @TestVisible private Integer failureCount = 0;
    @TestVisible private Integer inputRowsProcessed = 0;
    @TestVisible private List<String> failureMessages = new List<String>();

    // Stateful memoization — recovered SOQL per chunk after the first.
    // Same pattern as PRM_NetworkCreationBatch.cachedHfNameToId.
    @TestVisible private Map<String, Id> cachedHfNameToId = null;
    @TestVisible private Map<String, Id> cachedAddressKeyToId = null;
    @TestVisible private Map<String, Id> cachedPracticeRtIdByDevName = null;

    public PRM_AddressCreationBatch(PRM_AddressCreationEnvelope envelope) {
        this.envelope = envelope;
    }

    public Iterable<SObject> start(Database.BatchableContext bc) {
        // Placeholder list — one per row — so execute() runs in chunks.
        List<HealthcareFacility> placeholders = new List<HealthcareFacility>();
        if (envelope == null || envelope.rows == null) return placeholders;
        for (Integer i = 0; i < envelope.rows.size(); i++) placeholders.add(new HealthcareFacility());
        return placeholders;
    }

    public void execute(Database.BatchableContext bc, List<SObject> scope) {
        Integer chunkInputRowsAtStart = inputRowsProcessed;
        Integer chunkSizeAtStart = scope == null ? 0 : scope.size();
        try {
            // 1. slice envelope.rows into chunk
            // 2. memoized lookups (HF by name, Address by addressIdentifier, RecordTypeIds)
            // 3. for each row, build:
            //    - Schema.Address     (upsert by external key)
            //    - HealthcareFacility (find-or-create by name + AccountId)
            //    - HealthcarePractitionerFacility (PRM_PractitionerPracticeAffiliation
            //      + PRM_PractitionerLocationAffiliation record types)
            //    - PRM_ProviderFeatureAssignment__c (Capabilities, AssistiveAids,
            //      AffirmingCareCategory) — one parent + per-feature children
            //    - PRM_PracticeToPractitioner__c (with effective dates)
            // 4. Database.insert(..., false) → SaveResult[] → split into
            //    successCount / failureCount + PRM_FailedRecordStaging__c rows
            // 5. PRM_ExceptionLogger.logExceptionReturnId on failures
        } catch (Exception e) {
            // Bump failureCount BEFORE any DML so a governor unwind
            // can't leave the IA marked Success.
            failureCount += chunkSizeAtStart;
            failureMessages.add('execute() threw: ' + e.getTypeName() + ' - ' + e.getMessage());
            // best-effort exception log + staging — same try/try/catch
            // pattern as PRM_NetworkCreationBatch (lines 161–193).
        }
    }

    public void finish(Database.BatchableContext bc) {
        String jobId = bc == null ? '' : String.valueOf(bc.getJobId());
        if (failureCount > 0) {
            // Aggregated exception log
            PRM_ExceptionLogger.logException(...);
        }
        updateIndividualApplicationStatusAndNotify();
    }

    private void updateIndividualApplicationStatusAndNotify() {
        if (envelope == null || envelope.caseManagerId == null) return;
        try {
            String newStatus = failureCount == 0 ? 'Success'
                              : (successCount == 0 ? 'Failed' : 'Partial Failure');
            update new IndividualApplication(
                Id = envelope.caseManagerId,
                PRM_AddressCreationStatus__c = newStatus
            );
            // Bell notification — copy structure verbatim from
            // PRM_NetworkCreationBatch.updateCaseManagerStatusAndNotify().
            // Title: "Practitioner Address Creation Complete" / "...- Action Needed"
        } catch (Exception e) {
            PRM_ExceptionLogger.logException(...);
        }
    }
}
```

**Hard constraints to honour (lessons from `PRM_NetworkCreationBatch`):**

1. `failureCount += chunkSizeAtStart;` **before** any DML in the outer catch — so a SOQL=201 secondary unwind cannot leave `successCount=0, failureCount=0` and a misleading “Success” IA status (the IA‑0000150602 fix).
2. Skip the bell notification when both counters are zero (IA‑0000150329 / IA‑0000150310 noise fix).
3. Use `PRM_FailedRecordStaging__c.PRM_SourceFlow__c = 'PRM_AddressCreationBatch'` (per spec in `PRM_FailedRecordStaging_Object_Specification.md`) and link to `PRM_ExceptionLog__c` via `PRM_ExceptionLog__c` lookup.
4. Memoize all per‑run SOQL in `Database.Stateful` instance vars (recovered SOQL budget — same play as `cachedHfNameToId`).
5. Never read from `envelope.rows` outside `execute()` once `start()` has returned — the start placeholder count is the source of truth for chunking.

### C. OmniStudio (Integration Procedure) changes

#### C.1 `PRM_AddressLogicContainer_English_5` (new version)

Replace the three child IP actions with two elements:

| Seq | Element | Change vs v4 |
|-----|---------|--------------|
| 1.0 | **`EnqueueAddressCreation`** (NEW) | Remote Action — `remoteClass = PRM_OmniProcessUtils`, `remoteMethod = callMethod`, `additionalInput.methodName = enqueueAddressCreation`. Pass: `locationsToUpsert`, `PractitionerScreenRecordIds`, `PractitionerEffectiveDate`, `PractitionerEffToDate`, `IsActive`, `IsPending`, `PractitionerRole`, `PractitionerForm`, `FeatureConfigSetting`, `ProviderInformationAffirmingCategory`, `GroupRecordIds`. Output node `AddressBatch` → captures `jobId`, `success`, `message`. |
| 2.0 | `Response` | Add `additionalOutput.CaseManagerId = %PractitionerScreenRecordIds:CaseManagerId%`, `addressJobId = %AddressBatch:jobId%`, `addressMessage = %AddressBatch:message%`, `addressSuccess = %AddressBatch:success%`. |
| 3.0 | ~~`ExistingPrimaryAddressLogic`~~ | **Set `isActive=false`.** Logic absorbed into `PRM_AddressCreationBatch.execute()`. |
| 4.0 | `AddTaxNetworkLogic` | **No change** — already queueable, already routes to `PRM_NetworkCreationBatch`. Keep `disableChainable=true`, `useQueueable=true`. |

Update `PRM_AddressLogicContainer.propertySetConfig`:
- `rollbackOnError = false` (was `true`). Address work no longer runs inline, so a rollback at this scope cannot affect it.
- `chainableCpuLimit` may be lowered back to the default once we confirm container CPU drops below 1,000 ms (currently provisioned at 2,000 ms).

#### C.2 `PRM_DelegatedPractitionerCreation_Procedure_8` (new version)

| Element | Change |
|---------|--------|
| `IP_CreatePractitionerPracticeLocation` (seq 20.0) | **Decision needed (see Clarifications):** either (a) leave `isActive=false` permanently and let `PRM_AddressCreationBatch` create the HCPF rows itself, or (b) re‑enable and call a NEW IP `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_3` that ALSO routes through `PRM_OmniProcessUtils.callMethod('enqueueAddressCreation', …)`. We strongly prefer (a) — single batch, single envelope, no risk of two writers racing on the same `HealthcarePractitionerFacility` rows. |
| `ResponseAction` (seq 23.0) | Add `addressJobId` / `addressSuccess` / `addressMessage` so the OmniScript Navigate Action has them in `dataJson`. |

#### C.3 OmniScript `PRM_DelegatedPractitionerAddressForm_English_10` (new version)

| Element | Change |
|---------|--------|
| Submit / Final IP Action (calls `PRM_AddressLogicContainer`) | No structural change — but now returns in <3 s. |
| **Navigate Action** (immediately after the Submit IP) | Set `Target Type = SObject`, `Record Id = {{CaseManagerId}}` (from `PRM_AddressLogicContainer:CaseManagerId`), `Action Name = view`. Add a `Show Toast` action before nav with `variant=info`, `message = "Address creation queued. We’ll notify you when it completes (typically <2 min for 15 locations)."` Toast title sourced from `addressMessage`. |
| Error path | If `addressSuccess == false` → show sticky error toast with `addressMessage`, do **not** navigate. |

#### C.4 LWC `pRMPncAndDelegated` and `prmTextElementOverrideForDelegatedCred`

These already render in the address form. **No behaviour change** unless the team wants to surface a live status pill on the Case Manager record itself — out of scope for this story (see Clarifications).

---

## Acceptance Criteria

**AC1 — Sub‑3‑second submit.**
**Given** I am on `PRM_DelegatedPractitionerAddressForm_English` for a Delegated Practitioner request with **1 group and 15 practice locations** (≥1 with multiple care taxonomies),
**When** I click **Submit**,
**Then** the Submit IP returns within **3 seconds (P95)** and within **5 seconds (P99)**, **and** the OmniScript navigates me to the `IndividualApplication` (Case Manager) record page automatically.

**AC2 — Background batch completes.**
**Given** the batch has been enqueued,
**When** I refresh the Case Manager record approximately 60–120 seconds later,
**Then** `PRM_AddressCreationStatus__c` is `Success`, **and** the address / HCPF / PFA / PracticeToPractitioner records appear in the related lists, **and** I receive a bell notification titled “Practitioner Address Creation Complete” with the practitioner and group name in the body.

**AC3 — Partial failure path.**
**Given** one of the 15 locations has invalid data (e.g., missing `CareTaxonomyId`),
**When** the batch executes,
**Then** the other 14 locations are created successfully, `PRM_AddressCreationStatus__c = 'Partial Failure'`, the failed location is written to `PRM_FailedRecordStaging__c` with `PRM_SourceFlow__c = 'PRM_AddressCreationBatch'` linked to a `PRM_ExceptionLog__c` row, **and** the user receives a bell notification titled “Practitioner Address Creation — Action Needed” telling them to review Failed Record Staging.

**AC4 — Full failure does not silently succeed.**
**Given** the executor hits SOQL=201 (or any governor exhaustion) **after** `successCount=0`,
**When** `finish()` runs,
**Then** `PRM_AddressCreationStatus__c = 'Failed'` (NOT `Success`) — i.e., the same defence as `PRM_NetworkCreationBatch` line 162–193.

**AC5 — Idempotent re‑submit guard.**
**Given** I accidentally hit Submit twice within 2 seconds (browser double‑click),
**When** the second invocation reaches `PRM_AddressCreationHelper.enqueueAddressCreation`,
**Then** the helper detects a recently enqueued job for the same `CaseManagerId` (e.g., `AsyncApexJob.CreatedDate > now() - 60s AND ApexClass.Name = 'PRM_AddressCreationBatch'`) and returns `{ success: true, jobId: <existing>, message: 'Already queued' }` without enqueuing a second batch. (Implementation: query `AsyncApexJob` in `enqueueAddressCreation`; cheap because the SOQL is bounded.)

**AC6 — Network + Address agreement on overall status.**
**Given** both `PRM_AddressCreationBatch.finish()` and `PRM_NetworkCreationBatch.finish()` have completed for the same `CaseManagerId`,
**Then** `IndividualApplication.PRM_ProcessingStatus__c` is `Success` only if BOTH `PRM_AddressCreationStatus__c = 'Success'` AND `PRM_NetworkCreationStatus__c = 'Success'`. Otherwise it reflects the worst of the two (Failed > Partial Failure > Success > Queued).

**AC7 — Backwards compatibility.**
**Given** I open an in‑flight OmniScript session that was started against `PRM_AddressLogicContainer_English_4`,
**When** I submit,
**Then** the v5 container handles the old payload shape and produces the same `CaseManagerId` response key (no NPE, no missing field).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` (currently `isActive=false` at seq 20.0 in `PRM_DelegatedPractitionerCreation_Procedure_7`) be **deleted** outright, or kept as a deprecated v3 that just calls the new helper? | Determines whether the legacy IP needs an empty‑shell v3 for any external callers (e.g., other OmniScripts, Apex `PRM_PractitionerCreationHelper`). | Technical Lead |
| 2 | Is the cross‑batch roll‑up of `PRM_ProcessingStatus__c` (AC6) done (a) inside whichever batch finishes second, or (b) by a new `PRM_PostSubmitStatusEvaluator` queueable that always runs last? | (a) is simpler but couples the two batches; (b) is cleaner but adds a new artifact. | Technical Lead |
| 3 | Do we want a live status pill on the Case Manager record page (LWC reading `PRM_AddressCreationStatus__c`) so users don’t have to refresh? | UX polish — adds a small `lightning-record-edit-form` or `getRecordNotifyChange` integration. | Product / UX |
| 4 | Are there any DOWNSTREAM triggers/flows on `Schema.Address`, `HealthcarePractitionerFacility`, or `PRM_ProviderFeatureAssignment__c` that **assume the OmniScript transaction is still open** (e.g., reading session‑scoped context)? | Could break when the work moves to an async batch with a different user context. | Apex Lead |
| 5 | For AC5 (idempotent re‑submit), is 60 seconds the right window, or do we want to make this a Custom Metadata `PRM_AddressCreation__mdt.DuplicateGuardSeconds__c`? | Trade‑off between blocking a legitimate quick‑resubmit after a known transient failure and preventing accidental double‑creates. | Product / Ops |
| 6 | Should the bell notification go to `UserInfo.getUserId()` (the submitter) **and** the Case Manager owner, or just the submitter (as in `PRM_NetworkCreationBatch`)? | Determines whether queue‑routed cases get a queue notification or a personal one. | Network Management QC Lead |
| 7 | Do we need to support **roll‑back on full failure** (Option 1 in `PRM_Batch_Rollback_Strategies.md`) for address creation, or is the staging + manual replay pattern sufficient? | Adds `PRM_AddressCreationRollbackBatch` if yes; +1 week effort. | Operations Lead |
| 8 | What is the production chunk size that proved stable for `PRM_NetworkCreationBatch` (currently default 50)? Address creation does more DML per row, so we should start lower (suggest 5). | Affects throughput, governor head‑room, and total wall time. | Performance / Apex Lead |
| 9 | Should the `Show Toast` after enqueue be `dismissable` or `sticky`? | UX — sticky reduces support tickets but is mildly annoying. | UX |
| 10 | Are there UTAM page objects / QTA scenarios for `PRM_DelegatedPractitionerAddressForm` that need to be updated for the new navigate‑to‑case‑manager behaviour? | QTA regression coverage. | QA Lead |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_AddressLogicContainer_English_5` (new version) | Integration Procedure | **HIGH** | Replaces three sync child IPs with one Remote Action |
| `PRM_DelegatedPractitionerAddressForm_English_10` (new version) | OmniScript | **MEDIUM** | New Navigate Action + Show Toast; success/error branches |
| `PRM_DelegatedPractitionerCreation_Procedure_8` (new version) | Integration Procedure | **LOW** | Decision on `IP_CreatePractitionerPracticeLocation` seq 20.0 + Response Action passes through new fields |
| `PRM_PractitionerAddressCreation_Procedure_5` | Integration Procedure | **LOW** | Becomes orphan / deprecated. Mark `isActive=false`. Keep for 30 days for in‑flight session backstop, then delete. |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg_English_1` | Integration Procedure | **LOW** | Becomes orphan / deprecated. Same disposition. |
| `PRM_AddressCreationBatch.cls` | Apex (NEW) | **HIGH** | Net‑new batch class doing all the address/HCPF/PFA/PracToPract DML |
| `PRM_AddressCreationHelper.cls` | Apex (NEW) | **HIGH** | Net‑new helper; sole entry point from OmniStudio |
| `PRM_AddressCreationEnvelope.cls` / `PRM_AddressCreationRow.cls` | Apex (NEW) | **MEDIUM** | POJOs only |
| `PRM_OmniProcessUtils.cls` | Apex (existing) | **LOW** | One new `if` branch — surgical |
| `IndividualApplication.PRM_AddressCreationStatus__c` | Custom Field (NEW) | **MEDIUM** | New picklist; UI tile / list view filter add |
| `PRM_FailedRecordStaging__c.PRM_SourceFlow__c` | Picklist value add | **LOW** | One new value `PRM_AddressCreationBatch` |
| `PRM_NetworkCreationBatch.finish()` | Apex (existing) | **MEDIUM** | Cross‑batch roll‑up logic (AC6) — see Clarification #2 |
| `PRM_NotificationHelper` / `PRM_CustomNotitficationtoCaseOwner` | Notification Type (existing) | **LOW** | Reuse — no new notification type needed |
| QTA scripts for delegated practitioner flow | Test artifacts | **MEDIUM** | Submit timing assertion + navigate assertion must be updated |
| `pRMPncAndDelegated`, `prmTextElementOverrideForDelegatedCred` LWCs | LWC | **LOW** | No required changes unless UX polish (Clarification #3) approved |
| Any out‑of‑process consumers of `HealthcarePractitionerFacility` created in the OmniScript turn (e.g., realtime DDP / inbound API) | External | **MEDIUM** | These rows now appear 30–120 s **after** Submit returns. See Clarification #4. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_AddressCreationEnvelope.cls` | Apex POJO (NEW) | **S** (< 1 hr) | Direct clone of `PRM_NetworkCreationEnvelope` with two extra fields |
| `PRM_AddressCreationRow.cls` | Apex POJO (NEW) | **M** (2–4 hrs) | ~25 fields; map from `locationsToUpsert.Locations[].Addresses[].CareTaxxonomyData[]` |
| `PRM_AddressCreationHelper.cls` | Apex class (NEW) | **L** (4–8 hrs) | Parse + flatten + idempotency guard (AC5) + executeBatch |
| `PRM_AddressCreationBatch.cls` | Apex class (NEW) | **XXL** (3+ days) | The heavy lift — replicates the logic of `PRM_PractitionerAddressCreation_Procedure_5`'s ~20 bundles in Apex DML form. Includes Stateful memoization, partial‑failure staging, governor‑unwind guard |
| `PRM_AddressCreationBatchTest.cls` + helper test | Apex tests (NEW) | **XL** (1–2 days) | ≥ 90 % coverage; happy, partial, full‑failure, governor‑unwind, idempotency |
| `PRM_OmniProcessUtils.cls` route add | Apex (existing) | **S** (< 1 hr) | One `if` |
| `IndividualApplication.PRM_AddressCreationStatus__c` | Custom field (NEW) | **S** (< 1 hr) | Picklist + permission set updates |
| `PRM_FailedRecordStaging__c.PRM_SourceFlow__c` picklist value | Config (NEW) | **S** (< 1 hr) | Single value add |
| `PRM_AddressLogicContainer_English_5` | IP version (NEW) | **L** (4–8 hrs) | Replace 3 child IPs with 1 Remote Action; update Response Action |
| `PRM_DelegatedPractitionerAddressForm_English_10` | OmniScript version (NEW) | **L** (4–8 hrs) | Navigate Action + Show Toast + error branch |
| `PRM_DelegatedPractitionerCreation_Procedure_8` | IP version (NEW) | **M** (2–4 hrs) | Pass new fields through Response Action |
| Cross‑batch roll‑up `PRM_ProcessingStatus__c` (AC6) | Apex update | **L** (4–8 hrs) | Either small edit to both batches' `finish()` OR new `PRM_PostSubmitStatusEvaluator` queueable |
| QTA / FIT regression updates | Tests | **M** (2–4 hrs) | Submit‑timing assertion + navigate assertion |
| Sandbox + UAT smoke + perf measurement (1, 5, 15, 50 locations) | QA / Perf | **L** (4–8 hrs) | Capture P50/P95/P99 + governor usage |

**Total Estimated Effort:** **~9–12 person‑days** — overall **XL** sprint slice (one developer over ~1.5 sprints, or two developers in parallel for ~1 sprint). Label as **AI‑estimated — validate with team**, especially the `PRM_AddressCreationBatch.cls` XXL line item which is the only true unknown (depends on whether HCPF/PFA upsert keys are already stable).

---

## Reference — Why this story slots in on top of the May 2026 work

The 2026‑05‑20 commit on `PRM_NetworkCreationBatch.cls` (recovered SOQL budget; `cachedHfNameToId`; IA‑0000150602 governor‑unwind fix) established the exact pattern this story uses. By the time this story ships:

- `PRM_AddressLogicContainer` will route **all three** child responsibilities through one of two batches (Address + Network), with IFC already on `PRM_IfcLoader`.
- The OmniScript turn collapses from three serial sync IP invocations to one Remote Action returning in <100 ms after enqueue.
- `IndividualApplication` becomes the single source of truth for “did everything land”: `PRM_AddressCreationStatus__c` × `PRM_NetworkCreationStatus__c` → `PRM_ProcessingStatus__c`.

That gives us the sub‑3‑second submit + immediate navigate‑to‑case‑manager UX the credentialing team has been asking for, without paying a Platform Event tax or rebuilding any of the data‑mapper / record‑creation logic in OmniStudio.
