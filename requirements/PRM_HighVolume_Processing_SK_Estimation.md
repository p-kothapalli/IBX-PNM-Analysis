# PRM High-Volume Transaction Processing — Story K (SK) Estimation

**Story K:** Ability to process transactions in guided flows that require high-volume record creation/processing (performance issues)

**Business Value:**
- Reduces enrollment bottleneck → providers get in-network and start billing faster
- Improved turnaround time and provider experience
- Moves record creation away from OmniScript Integration Procedures (synchronous, UI-blocking) to platform-level processing (Apex Batch / Queueable / Platform Events)

**Scope:** Three workflows identified:
1. **Practitioner Creation** (`PRM_PractitionerCreation_English` OmniScript)
2. **PDM Manual Change – Practitioner** (`PRM_PDMManualUpdatePractitioner_English` OmniScript)
3. **PDM Manual Change – Practice Location** (`PRM_PDMManualUpdate_English` OmniScript)

---

## Executive Summary

| | Baseline | AI + Senior Dev |
|---|---|---|
| **Total effort** | 36 developer-days | **18–22 developer-days** |
| **Calendar time (2 devs)** | ~4 sprints (8 weeks) | **2–3 sprints (4–6 weeks)** |
| **Risk level** | Medium-High | Medium-High (unchanged) |

> **Revision notes (v2):** Added AI productivity re-estimate, fixed SOQL UNION ALL error
> in rollback batch (not supported by `Database.getQueryLocator`), corrected `CaseManager__c`
> object reference (should be `IndividualApplication`), added existing `PRM_PractitionerActivationBatch`
> overlap note, added missing platform event duplicate-dispatch risk, and added FDP interaction gap.

---

## 1. Current Architecture — What the IPs Are Doing (and Why It Breaks)

### Root Cause: Synchronous IP Chains Exceeding Salesforce Limits

All three flows use the same anti-pattern: a **synchronous OmniScript Integration Procedure chain** that tries to create 6–15 Salesforce objects in a single UI transaction. When providers have multiple practice locations, networks, or taxonomies, the volume of DML operations exceeds Salesforce governor limits or causes UI timeouts.

```
OmniScript (User fills out form)
    └─ IP: PRM_PDMRecordsCreationParent (or PRM_PractitionerCreationContainer)
           └─ IP: PRM_PDMRecordsCreation
                  ├─ DR: DRCreateCaseCaseMgr         → INSERT Case + IndividualApplication
                  ├─ DR: DRCreateCaseDatamanager     → INSERT PRM_CaseDataManager__c
                  ├─ DR: DRUpdateAccount             → UPDATE Account
                  ├─ DR: DRUpdatePractitionerPDM     → UPDATE Contact + HealthcareProvider
                  ├─ IP: IPRecordsCreationHelper     → PRM_PDMRecordsCreationHelper
                  │       ├─ CB: CB_AddRemovePractitioner
                  │       │     └─ DR: PRMLoadPPLPDM          → UPSERT HealthcarePractitionerFacility
                  │       ├─ CB: CB_AddRemovePractitionerHCPF
                  │       │     ├─ RA: RAClonePPLTaxForRoles  → INSERT HealthcareFacilityNetwork (×N roles)
                  │       │     └─ RA: RAClonePPLTaxForPayerNetworks → INSERT HFN (×M networks)
                  │       ├─ CB: CB_AddorTerminatePLTaxonomy
                  │       │     └─ DR: PRMDRAddPracticeLocationTaxonomy → INSERT HealthcareProviderTaxonomy
                  │       ├─ CB: CB_AddRemoveNetworks
                  │       │     ├─ DR: DRLoadManualUpdatePLNetworks → UPSERT HFN
                  │       │     └─ DR: LoadAddMUPLNetworks / LoadRemoveMUPLNetworks
                  │       └─ CB: CB_ProgramParticipation
                  │             └─ DR: DRLoadManualUpdatePLNetworks → UPSERT ProgramParticipation
                  ├─ IP: IPPractitionerCreationHelper → PRM_PDMRecordsPractitionerCreationHelper
                  │       ├─ DR: DRLoadPPLPDM           → UPSERT HealthcarePractitionerFacility
                  │       ├─ DR: DRLoadTaxonomyPDM       → UPSERT HealthcareProviderTaxonomy
                  │       ├─ DR: DRLoadPPLTaxNetworkRecords → UPSERT HealthcareFacilityNetwork (×N×M)
                  │       ├─ DR: DRLoadLicenses          → UPSERT BusinessLicense
                  │       └─ DR: DRLoadIdentifierData    → UPSERT HealthcareProviderNpi (Identifiers)
                  └─ IP: IPPLRecordsCreationHelper     → PRM_PDMPLRecordsCreationHelper
                          ├─ CB: CB_UpdateOfficeHours    → INSERT/UPDATE OperatingHours
                          ├─ CB: CB_UpdateDirectoryIndicators → UPDATE HealthcareFacilityNetwork
                          ├─ CB: CB_CapitationSite       → UPSERT CapitationSite
                          └─ CB: CB_HCAssociations       → UPSERT HCF Associations
```

### Scale of the Problem

| Flow | Objects Created per Submission | DML Statements | Apex CPU Risk |
|------|-------------------------------|----------------|---------------|
| Practitioner Creation | Account + Contact + HealthcareProvider + Case + IndividualApplication + CaseDataManager + HCPF + HCProviderTaxonomy (×2) + BusinessLicense + HFN (×roles×networks) + Identifier | 12–25 DML ops | HIGH |
| PDM Manual – Practitioner | Case + IndividualApplication + CaseDataManager + HCPF (×locations) + HFN (×networks×roles) + HCProviderTaxonomy + Identifier updates + License updates | 15–40 DML ops | HIGH |
| PDM Manual – Practice Location | Case + IndividualApplication + CaseDataManager + HCPF + HFN (×networks×roles) + HCProviderTaxonomy + OperatingHours + CapitationSite + ProgramParticipation + DirectoryIndicator updates | 10–35 DML ops | HIGH |

**Current Governor Limit exposure per submission (observed in SampleInput debugLog):**
- Each DataRaptor Post Action = 1–3 SOQL queries + 1 DML statement
- 7 chained IPs × avg 5 DR actions = 35+ DML statements in a **single synchronous Apex transaction**
- Salesforce limit: **150 DML statements per transaction** — already close to the ceiling for complex submissions (multi-location, multi-network practitioners)

---

## 2. Proposed Architecture — Platform-Level Processing

### Core Design Principle

**Decouple the OmniScript form submission from record creation.** The OmniScript does three things:
1. Collects form data (synchronous, fast)
2. Validates input (synchronous, fast)
3. **Kicks off async processing** (fire-and-forget, returns immediately)

All DML creation happens asynchronously via Apex Batch or Queueable chains, with status tracked back to the UI via a status record.

```
OmniScript (User submits)
    │
    ▼
[SYNC] Validate inputs + NPI lookups
    │
    ▼
[SYNC] Write payload → PRM_AsyncJobRequest__c (single INSERT)
    │   Status = "Queued"
    │
    ▼
[SYNC] Return "Submission received" to user (instant response)
    │
    ▼ (Platform Event fires asynchronously)
    │
[ASYNC] PRM_AsyncJobDispatcher.enqueue() → PRM_RecordCreationQueueable
    ├─ [Batch 1] PRM_CoreRecordsBatch     → Case + IndividualApplication + CaseDataManager + Account
    ├─ [Batch 2] PRM_PractitionerBatch    → HealthcareProvider + Contact updates + Identifiers + Licenses
    ├─ [Batch 3] PRM_TaxonomyBatch        → HealthcareProviderTaxonomy (per taxonomy × location)
    ├─ [Batch 4] PRM_NetworkBatch         → HealthcarePractitionerFacility + HealthcareFacilityNetwork (×N)
    └─ [Batch 5] PRM_ActivationBatch      → Activate all Pending records (Status = Pending → Active)

On failure at any batch: PRM_RollbackBatch → delete all records with RequestId = X
    │
    ▼
Status Record updated → FlexCard on UI polls / Platform Event pushes update to user
```

---

## 3. Workflow-by-Workflow Breakdown

---

### **3A. Practitioner Creation** (`PRM_PractitionerCreation_English`)

#### What it creates today (confirmed from `PRM_PractitionerCreation_SampleInput.json`):
1. `Account` (Person Account) — DRPAccountCaseCaseManagerCreation via `PRMDRCreateCaseCaseManagerAndAccount`
2. `Contact` (PersonContact) — from Person Account creation
3. `Case` (Type: "Network Management QC")
4. `IndividualApplication` (ApplicationType: "Individual", Category: "Provider Data Management")
5. `PRM_CaseDataManager__c`
6. `HealthcareProvider`
7. `HealthcareProviderNpi` (NPI identifier)
8. `HealthcareProviderTaxonomy` (CareTaxonomy, per taxonomy)
9. `BusinessLicense` (State license)
10. `HealthcarePractitionerFacility` (HCPF) — at initial practice location
11. `HealthcareFacilityNetwork` (per role × payer network)
12. `InfoCode` assignment records

**DR Bundles Used:**
- `PRMDRCreateCaseCaseManagerAndAccount`
- `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense`
- `PRMDRPPractionerPracticeLocations`
- `PRMDRCreateCDM` / `PRMDRCreateCDMForPractitioner`

**Current Execution Sequence (IP `PRM_PractitionerCreation`):**
```
SV_RecordTypeIds  →  RA_GetInfoCodesList  →  RA_GetRecordTypeList  →  RA_TitleCase
  →  DRPAccountCaseCaseManagerCreation
  →  DRPHCProviderHCProviderTaxonomyAndBusineessLicense
  →  DRPPractionerPracticeLocations
  →  DRPCreateInfoCodeAssignments
  →  PRMDRCreateCDM
  →  PRMDRCreateCDMForPractitioner
  →  ResponseAction
```

**Problem:** All 7 DR actions run synchronously. With 3+ practice locations + 2 taxonomies + 4 networks = 40+ DML operations in one transaction.

#### **Redesign: Practitioner Creation Async**

```
Phase 1 (OmniScript, sync):
  1. Validate NPI format
  2. Check for duplicate Account (SOQL only, no DML)
  3. Write to PRM_AsyncJobRequest__c:
     - FlowType = "PractitionerCreation"
     - Payload = serialized form JSON
     - Status = "Queued"
  4. Fire PRM_AsyncJobQueued__e platform event
  5. Return "Your practitioner creation request has been submitted.
             Case Number will be assigned shortly." to user

Phase 2 (Async, Queueable chain):
  Batch 1 — PRM_PractitionerCoreCreationBatch
    - Create Account (Person Account)
    - Create Case
    - Create IndividualApplication
    - Create PRM_CaseDataManager__c
    - Status → "Core Records Created"

  Batch 2 — PRM_PractitionerProviderBatch
    - Create HealthcareProvider
    - Create HealthcareProviderNpi (NPI Identifier)
    - Create BusinessLicense (State license)
    - Status → "Provider Records Created"

  Batch 3 — PRM_PractitionerTaxonomyBatch
    - Create HealthcareProviderTaxonomy (per taxonomy in payload)
    - Create InfoCode assignments
    - Status → "Taxonomy Records Created"

  Batch 4 — PRM_PractitionerLocationBatch
    - Create HealthcarePractitionerFacility (per practice location)
    - Create HealthcareFacilityNetwork (per taxonomy × role × network)
    - Status → "Location Records Created"

  Batch 5 — PRM_PractitionerActivationBatch
    - Set all Pending records → Active (PRM_Status__c = "Active", PRM_IsActive__c = true)
    - Update PRM_AsyncJobRequest__c Status = "Completed"
    - Send notification email / Platform Event to UI
    - Status → "Completed"

  On failure at any batch:
    PRM_PractitionerRollbackBatch → Delete all records WHERE PRM_RequestId__c = :requestId
    Status → "Failed — Rolled Back"
```

**Objects tracked with `PRM_RequestId__c`:** Account, Case, IndividualApplication, PRM_CaseDataManager__c, HealthcareProvider, HealthcareProviderNpi, HealthcareProviderTaxonomy, BusinessLicense, HealthcarePractitionerFacility, HealthcareFacilityNetwork

---

### **3B. PDM Manual Change – Practitioner** (`PRM_PDMManualUpdatePractitioner_English`)

#### What it changes today (confirmed from `PRM_PDMRecordsPractitionerCreationHelper` elements):
The PDM Practitioner change covers 7 distinct sub-actions, each firing a separate Conditional Block:

| CB Element | Fires When | Records Affected |
|-----------|-----------|-----------------|
| `CB_IBCProfessionalStaff` | IBC Professional Staff update | Case + IndividualApplication + CaseDataManager |
| `CBExecuteNewPractitionerPracLocTaxAndNetworks` | New PPL Taxonomy + Network | HCPF + HealthcareProviderTaxonomy + HealthcareFacilityNetwork |
| `CB_PractitionerNetworks` | Network add/update/remove | HealthcareFacilityNetwork (per PractitionerPracLocTaxAndNetworks array) |
| `CB_AdmittingPrivileges` | Admitting Privileges change | HealthcarePractitionerFacility (admitting type) |
| `CB_MedicareNumber` | Medicare number update | HealthcareProviderNpi (Medicare identifier) |
| `CB_DelegatedPractitionerUpdate` | Delegated flag change | Account + HCPF |
| `CB_ExecuteUpdateProfessionalStaff` / `CB_ExecuteRemoveProfessionalStaff` | Professional Staff update/remove | IndividualApplication + multiple related records |

**Confirmed from SampleInput:** `PractitionerPracLocTaxAndNetworks` array can contain **multiple entries** (one per network × location × taxonomy). Each entry creates/updates a `HealthcareFacilityNetwork` record. For a practitioner at 10 locations × 3 networks = **30 HFN records** in one synchronous IP call.

**DR/RA Actions involved:**
- `DRCaseManagerCaseDataManager` (×5 variants for each sub-action)
- `DRLoadPPLTaxNetworkRecords` → Upsert HFN (×N array entries)
- `RemActionClonePPLTaxNwForNetworks` → Remote Action, clones HFN records
- `RemoteActionToCloneOnNetworks` → Another Remote Action clone
- `DRLoadLicenses` → License upserts
- `DRTIdentifier` → Identifier updates

**Problem:** When a user updates networks for a practitioner at many locations, the `PractitionerPracLocTaxAndNetworks` loop in DR `DRLoadPPLTaxNetworkRecords` runs N DML statements (one per array element) synchronously.

#### **Redesign: PDM Practitioner Change Async**

```
Phase 1 (OmniScript, sync):
  1. Validate change type, practitioner exists
  2. Write to PRM_AsyncJobRequest__c:
     - FlowType = "PDMPractitionerChange"
     - SubType = one of [IBCProfessionalStaff | NetworkUpdate | TaxonomyUpdate |
                         AdmittingPrivileges | MedicareNumber | DelegatedUpdate]
     - Payload = full PractitionerRelatedRecordsToUpdate JSON
     - PractitionerId = Contact.Id
     - CaseManagerId = (created synchronously as Phase 1 always needs a CaseManager)
     - Status = "Queued"
  3. Fire PRM_AsyncJobQueued__e platform event
  4. Return "PDM change submitted. Case #XXXX created." to user

Phase 2 (Async, per SubType):

  [IBCProfessionalStaff] — PRM_PDMPractitionerIBCBatch
    - Create/Update IndividualApplication (professional staff record)
    - Create PRM_CaseDataManager__c
    - Update Account flags
    - Status → "Completed"

  [NetworkUpdate] — PRM_PDMPractitionerNetworkBatch
    - Iterate PractitionerPracLocTaxAndNetworks[]
    - Upsert HealthcareFacilityNetwork per entry (UpdatePN = true → update, false → skip)
    - Clone new HFN records via Apex (replaces RemActionClonePPLTaxNwForNetworks)
    - Status → "Completed"

  [TaxonomyUpdate] — PRM_PDMPractitionerTaxonomyBatch
    - Upsert HealthcareProviderTaxonomy per taxonomy in payload
    - Create HealthcareFacilityNetwork links (taxonomy × network × role)
    - Update HCPF records (new PPL taxonomy)
    - Status → "Completed"

  [AdmittingPrivileges] — PRM_PDMAdmittingPrivilegesBatch
    - Transform ADP records (DRTransformADPrivileges equivalent in Apex)
    - Insert/Update HealthcarePractitionerFacility admitting rows
    - Status → "Completed"

  [MedicareNumber] — PRM_PDMMedicareBatch
    - Update/Insert HealthcareProviderNpi Medicare identifier
    - Status → "Completed"

  On failure: PRM_PDMPractitionerRollbackBatch
    - Delete all records WHERE PRM_RequestId__c = :requestId AND PRM_Status__c = 'Pending'
    - Status → "Failed — Rolled Back"
```

---

### **3C. PDM Manual Change – Practice Location** (`PRM_PDMManualUpdate_English`)

#### What it changes today (confirmed from `PRM_PDMRecordsCreationHelper` 50+ elements):
The Practice Location flow covers 9 distinct change types, each a Conditional Block:

| CB Element | Fires When | Records Affected |
|-----------|-----------|-----------------|
| `CB_AddRemovePractitioner` | Add/Remove practitioner to/from location | HealthcarePractitionerFacility |
| `CB_AddRemovePractitionerHCPF` | HCPF + Networks for Add/Remove Prac | HCPF + HealthcareFacilityNetwork (×N) |
| `CB_AddPractitionerNetwork` | Add network to practitioner-location | HealthcareFacilityNetwork |
| `CB_AddRemovePractitionerNetwork` | Change networks | HealthcareFacilityNetwork updates |
| `CB_RemovePractitionerNetwork` | Remove network records | HealthcareFacilityNetwork deletes |
| `CB_AddorTerminatePLTaxonomy` | Add/terminate practice location taxonomy | HealthcareProviderTaxonomy + HFN |
| `CB_AddRemoveNetworks` | Add/Remove payer networks at facility | HealthcareFacilityNetwork (×bulk) |
| `CB_TerminatePracticeLocation` | Terminate entire practice location | HCPF + HFN + HPT + HCF deactivation |
| `CB_TerminateCOIAndRemovePractitioner` | COI Terminate + Remove | Multiple objects |
| `CB_ProgramParticipation` | Program Participation change | ProgramParticipation records |
| `CB_AddProgramPartcipation` | Add Program Participation | ProgramParticipation + HFN |
| `CB_RemoveProgramPartcipation` | Remove Program Participation | ProgramParticipation + HFN |
| `CB_NonParAccount` | Non-Par Account change | Account + HCPF + HFN |

**Add/Remove Networks specifically** (`CB_AddRemoveNetworks` → `DRLoadManualUpdatePLNetworks`) processes a `MergedNetworks` array (from `LAMergeAddRemoveNetworks`). Each item = one DML. For a facility with 30 networks, this is **30 DML statements in one IP action**.

**Terminate Practice Location** is the most complex: it deactivates HCPF, all HFN records (×N), all HPT records (×M), updates the HCF, and clones cross-reference records — all synchronously.

**Additional complexity confirmed from `PRM_PDMPLRecordsCreationHelper`:**
- `CB_UpdateOfficeHours` → `DRLoadOperatingHours` — can have 7 days × multiple time slots
- `CB_CapitationSite` → `DRLoadCapitationSite` — per capitation agreement
- `CB_HCAssociations` → `DRLoadHCFAssociation` — HCF Association upserts
- `CB_UpdateDirectoryIndicators` → `DRLoadManualUpdateDirIndicators` — bulk HFN flag updates
- `CB_UpdateHCFNames` → `DRLoadPracticeNameChange` — cascades to HCPF Name field

**Remote Actions that are Apex already (but sync):**
- `RAPractitionerActivationBatch` → calls `PRM_PractitionerActivationUtility.PractitionerActivationBatch` (already a batch trigger, but fired synchronously from IP finish)

#### **Redesign: PDM Practice Location Change Async**

```
Phase 1 (OmniScript, sync):
  1. Validate facility selection, change type
  2. Create Case + IndividualApplication + CaseDataManager synchronously
     (These are needed immediately for UI reference / QC routing)
  3. Write remaining payload to PRM_AsyncJobRequest__c:
     - FlowType = "PDMPracticeLocationChange"
     - SubType = PracLocationManualChange value
     - CaseId = <just created>
     - CaseManagerId = <just created IndividualApplication.Id>
     - Payload = full HCFRecordsToUpdate JSON
     - Status = "Queued"
  4. Fire PRM_AsyncJobQueued__e platform event
  5. Return "Change submitted. Case #XXXX assigned to QC team." to user

Phase 2 (Async, per SubType):

  [AddRemovePractitioner] — PRM_PDMAddRemovePractitionerBatch
    - Upsert HealthcarePractitionerFacility (PRMLoadPPLPDM equivalent)
    - Insert HealthcareProviderTaxonomy (PRMDRAddPracticeLocationTaxonomy equivalent)
    - Insert HealthcareFacilityNetwork per taxonomy × role × network
    - Activate records on success
    - Rollback on failure

  [AddRemoveNetworks] — PRM_PDMNetworkBatch
    - Process MergedNetworks[] array in batches of 50
    - Upsert HealthcareFacilityNetwork per entry (Add: IsActive=true, Remove: EffectiveTo=today)
    - Rollback on failure

  [AddorTerminatePLTaxonomy] — PRM_PDMTaxonomyBatch
    - Insert/Update HealthcareProviderTaxonomy
    - Cascade to HealthcareFacilityNetwork (clone or deactivate)

  [TerminatePracticeLocation] — PRM_PDMTerminatePLBatch
    - Deactivate HealthcareFacilityNetwork (bulk update IsActive=false)
    - Deactivate HealthcareProviderTaxonomy
    - Update HealthcarePractitionerFacility (EffectiveTo = termDate)
    - Update HealthcareFacility (if last practitioner)
    - Rollback: Reactivate records (PRM_RequestId__c allows targeted query)

  [UpdateOfficeHours] — PRM_PDMOfficeHoursBatch
    - Upsert OperatingHours + OperatingHoursHoliday
    - Update HealthcareFacility.OperatingHoursId

  [CapitationSite] — PRM_PDMCapitationBatch
    - Upsert CapitationSite records

  [DirectoryIndicators] — PRM_PDMDirectoryBatch
    - Bulk update HealthcareFacilityNetwork flags (ShowInDir, MemberSelectablePCP, etc.)

  On failure (any sub-type): PRM_PDMPLRollbackBatch
    - All newly created records → Delete WHERE PRM_RequestId__c = :requestId AND PRM_Status__c = 'Pending'
    - All updated records → Restore from PRM_AsyncJobRequest__c stored original values
    - Status → "Failed — Rolled Back"
```

---

## 4. Shared Infrastructure (Common to All Three Workflows)

### 4A. `PRM_AsyncJobRequest__c` — New Custom Object

> Single staging/tracking object for all async PDM jobs. Replaces the need for workflow-specific staging objects.

| Field | Type | Purpose |
|-------|------|---------|
| `Name` (auto) | Auto Number | `PDM-{000001}` |
| `PRM_FlowType__c` | Picklist | `PractitionerCreation | PDMPractitionerChange | PDMPracticeLocationChange` |
| `PRM_SubType__c` | Text (100) | Sub-action: `AddRemovePractitioner`, `NetworkUpdate`, etc. |
| `PRM_Status__c` | Picklist | `Queued | Processing | Completed | Failed | RolledBack` |
| `PRM_CaseId__c` | Lookup(Case) | Linked QC Case |
| `PRM_CaseManagerId__c` | Lookup(IndividualApplication) | Linked Case Manager |
| `PRM_FacilityId__c` | Text(18) | HealthcareFacility.Id |
| `PRM_PractitionerId__c` | Text(18) | Contact.Id |
| `PRM_RequestId__c` | Text(36) | UUID — stamped on all created records |
| `PRM_Payload__c` | Long Text Area | Serialized JSON payload from OmniScript |
| `PRM_ErrorMessage__c` | Long Text Area | Error details on failure |
| `PRM_RecordsCreated__c` | Number | Count of records created |
| `PRM_RecordsFailed__c` | Number | Count of failed record creations |
| `PRM_SubmittedBy__c` | Lookup(User) | Who submitted the request |
| `PRM_SubmittedAt__c` | DateTime | Submission timestamp |
| `PRM_CompletedAt__c` | DateTime | Completion timestamp |
| `PRM_BatchJobId__c` | Text(18) | Apex Batch job ID for monitoring |
| `PRM_RetryCount__c` | Number | Number of retry attempts |

### 4B. `PRM_AsyncJobQueued__e` — Platform Event

> Fired by OmniScript on form submission. Triggers batch dispatch.

| Field | Type | Purpose |
|-------|------|---------|
| `JobRequestId__c` | Text(18) | PRM_AsyncJobRequest__c.Id |
| `FlowType__c` | Text(100) | Flow type routing key |
| `Priority__c` | Text(20) | `Standard | High | Critical` |

**Trigger (Platform Event):**
```apex
trigger PRM_AsyncJobQueuedTrigger on PRM_AsyncJobQueued__e (after insert) {
    for (PRM_AsyncJobQueued__e evt : Trigger.new) {
        PRM_AsyncJobDispatcher.dispatch(evt.JobRequestId__c, evt.FlowType__c);
    }
}
```

**Dispatcher:**
```apex
public class PRM_AsyncJobDispatcher {
    public static void dispatch(String jobRequestId, String flowType) {
        switch on flowType {
            when 'PractitionerCreation' {
                System.enqueueJob(new PRM_PractitionerCreationQueueable(jobRequestId));
            }
            when 'PDMPractitionerChange' {
                System.enqueueJob(new PRM_PDMPractitionerChangeQueueable(jobRequestId));
            }
            when 'PDMPracticeLocationChange' {
                System.enqueueJob(new PRM_PDMPLChangeQueueable(jobRequestId));
            }
        }
    }
}
```

### 4C. Rollback Framework (per `PRM_Batch_Rollback_Strategies.md`)

**Recommended: Hybrid Option 1 + 2 (Compensation + Status-Based)**

All created records get:
- `PRM_RequestId__c` (Text 36) — UUID stamped at creation
- `PRM_Status__c` (Picklist: Pending | Active | Failed | Rolled Back) — default "Pending"
- `PRM_IsActive__c` (Checkbox) — default false; set true only on activation batch

> ⚠️ **Fix required from `PRM_Batch_Rollback_Strategies.md`:** The rollback batch's
> `Database.getQueryLocator` uses `UNION ALL` which **Salesforce SOQL does not support**.
> Use separate chained batches per object type, or use `Database.Batchable<String>` with
> the object name list as the iterable (as shown in Option 5 of that document).

**Corrected rollback pattern:**
```apex
// Wrong — SOQL UNION ALL not supported in QueryLocator:
// return Database.getQueryLocator('SELECT Id FROM HFN WHERE ... UNION ALL SELECT Id FROM HPT WHERE ...');

// Correct — chain separate deletes per object in finish():
public void finish(Database.BatchableContext BC) {
    List<String> objectsToDelete = new List<String>{
        'HealthcareFacilityNetwork', 'HealthcareProviderTaxonomy',
        'HealthcarePractitionerFacility', 'BusinessLicense'
    };
    // Delete each in sequence using dynamic SOQL
    for (String objName : objectsToDelete) {
        List<SObject> toDelete = Database.query(
            'SELECT Id FROM ' + objName + ' WHERE PRM_RequestId__c = :requestId'
        );
        if (!toDelete.isEmpty()) Database.delete(toDelete, false);
    }
    // Update IndividualApplication status (not CaseManager__c — that object doesn't exist)
    update new IndividualApplication(
        Id = caseManagerId,
        Status = 'Failed',
        PRM_Stage__c = 'Complete'
    );
}
```

**Objects requiring these 3 new fields:**

| Object | Already Has Status | Already Has IsActive | Action |
|--------|-------------------|---------------------|--------|
| `HealthcarePractitionerFacility` | `PRM_Active__c` exists | `IsActive` (standard) | Add `PRM_RequestId__c`, `PRM_Status__c` |
| `HealthcareFacilityNetwork` | `PRM_Active__c` exists | — | Add `PRM_RequestId__c`, `PRM_Status__c` |
| `HealthcareProviderTaxonomy` | `PRM_Active__c` exists | — | Add `PRM_RequestId__c`, `PRM_Status__c` |
| `HealthcareProvider` | — | — | Add `PRM_RequestId__c` only |
| `BusinessLicense` | — | — | Add `PRM_RequestId__c` only |
| `Case` | `Status` standard | — | Add `PRM_RequestId__c` only |
| `IndividualApplication` | `Status` standard | — | Add `PRM_RequestId__c` only |

### 4D. Status Polling — FlexCard Update

The OmniScript returns immediately. A FlexCard on the Case or Practitioner record polls `PRM_AsyncJobRequest__c.PRM_Status__c` every 10 seconds via a platform event subscriber or simple SOQL refresh:

```
PRM_PDMJobStatusCard (FlexCard)
  ├─ Shows: Job Status, Submitted At, Completed At, Error (if any)
  ├─ "Queued"     → spinner, "Processing your request..."
  ├─ "Processing" → progress bar (RecordsCreated / expected total)
  ├─ "Completed"  → green checkmark, Case # link, records created count
  └─ "Failed"     → red alert, error message, retry button
```

---

## 5. OmniScript Changes Required

### For All Three Flows

**Add a new IP action at the end of the submit flow:**

```json
{
  "Name": "IPSubmitAsyncJob",
  "Type": "Integration Procedure Action",
  "integrationProcedureKey": "PRM_SubmitAsyncJob",
  "executionConditionalFormula": "",
  "additionalInput": {
    "FlowType": "=<flow-specific value>",
    "SubType": "=%PracLocationManualChange%",  // or equivalent
    "Payload": "=<full form data node>"
  },
  "returnOnlyAdditionalOutput": true
}
```

**Replace synchronous record-creation IP calls** with the above submit action.

**Existing elements to DISABLE (not delete — for rollback capability):**
- `IPRecordsCreationHelper` (PRM_PDMRecordsCreationHelper) — disable `isActive`
- `IPPractitionerCreationHelper` (PRM_PDMRecordsPractitionerCreationHelper) — disable `isActive`
- `IPPLRecordsCreationHelper` (PRM_PDMPLRecordsCreationHelper) — disable `isActive`
- `DRPAccountCaseCaseManagerCreation` — disable for PractitionerCreation flow

**New confirmation step in OmniScript:**

```
Current: "Your submission has been processed."
New:     "Your request (PDM-000123) has been submitted. 
          Case #0001234 has been created and assigned to QC.
          Record creation is processing — you'll receive a notification
          when complete (typically within 2 minutes)."
```

---

## 6. Estimation Summary

### Important: What's Already Built (Reduces Scope)

Before estimating, note that `PRM_PractitionerActivationBatch` already exists in the
codebase (`PRM_PractitionerActivationBatch.cls`, `PRM_PractitionerActivationUtility.cls`,
`PRM_PractitionerActivationBatchHelper.cls` — US-1372477, Feb 2026). It is currently
invoked **synchronously** via Remote Action from the PDM Practice Location flow.

This means:
- The activation batch **does not need to be built from scratch** — only wired into the new async dispatcher
- The batch chunk size is already set at `database.executeBatch(praActivation, 1)` — this will need review for high-volume scenarios (chunk of 1 is very safe but slow)
- Save ~1.5 days of build effort; add ~0.5 days to refactor/rewire it

### Story Points / T-Shirt Size by Component

| Component | Baseline Days | AI + Senior Days | Size | Notes |
|-----------|--------------|-----------------|------|-------|
| **`PRM_AsyncJobRequest__c` object** (fields, layout, permissions) | 0.5 | 0.25 | XS | AI generates field XML in minutes |
| **`PRM_AsyncJobQueued__e` platform event** + trigger + dispatcher | 0.5 | 0.25 | XS | Simple pattern |
| **Add `PRM_RequestId__c` + `PRM_Status__c`** to 7 objects | 0.5 | 0.25 | XS | AI generates all 7 field XMLs in one pass |
| **`PRM_SubmitAsyncJob` IP** | 1 | 0.5 | S | Simple write + event fire |
| **`PRM_RollbackBatch`** (generic, per corrected SOQL pattern above) | 1 | 0.5 | S | AI generates from rollback doc; senior fixes SOQL |
| **`PRM_ActivationBatch`** (rewire existing `PRM_PractitionerActivationBatch`) | 0.5 → **0.25** | **0.25** | XS | Already exists — just rewire |
| **`PRM_PDMJobStatusCard` FlexCard** | 1 | 0.5 | S | AI generates from existing FlexCard patterns |
| **Practitioner Creation — Queueable chain** (5 batches, 3A) | 5 | 2.5 | L | AI generates batch scaffolding; senior validates business logic |
| **PDM Practitioner Change — Queueable chain** (5 sub-types, 3B) | 6 | 3 | L | Most complex sub-type logic |
| **PDM Practice Location Change — Queueable chain** (7 sub-types, 3C) | 7 | 3.5 | XL | Largest scope; AI drafts, senior reviews 13 CB equivalents |
| **OmniScript changes** (3 flows — disable old IPs, add submit action) | 2 | 1.5 | M | OmniStudio publishing is manual — not fully compressible |
| **Unit tests** (80%+ coverage) | 4 | **1** | L | **AI biggest win — 4× multiplier on test generation** |
| **Integration/E2E testing** in sandbox | 3 | 2.5 | M | Mostly manual — async flows need real sandbox execution |
| **UAT + bug fixes** | 3 | 3 | M | **Cannot be accelerated — human-only** |
| **Deployment + cutover runbook** | 1 | 0.75 | S | AI drafts runbook |

### **Total Estimate**

| Phase | Baseline Days | AI + Senior Days | SP (1 SP = 0.5 day) |
|-------|--------------|-----------------|---------------------|
| **Phase 1: Shared Infrastructure** | 5 | **2.5** | **5 SP** |
| **Phase 2: Practitioner Creation** | 5 | **2.5** | **5 SP** |
| **Phase 3: PDM Manual – Practitioner** | 6 | **3** | **6 SP** |
| **Phase 4: PDM Manual – Practice Location** | 7 | **3.5** | **7 SP** |
| **Phase 5: OmniScript changes (all 3)** | 2 | **1.5** | **3 SP** |
| **Phase 6: Testing (unit + integration + UAT)** | 10 | **7** | **14 SP** |
| **Phase 7: Deployment** | 1 | **0.75** | **1.5 SP** |
| **Total** | **36 days** | **~21 days** | **~42 SP** |

> **Team assumption:** 2 senior developers with Cursor AI, working in parallel on Phases 2–4
> after Phase 1 infra is complete.
>
> **Calendar estimate:**
> - Standard team: ~4 sprints (8 weeks)
> - **AI + senior team: ~2.5 sprints (5 weeks)**

---

## 7. Sprint Breakdown Recommendation

> **Sequencing note:** Sprint 1 previously had Dev 2 starting Practitioner Creation Batches
> while infra was still being built. This creates a hard dependency conflict. The revised
> plan ensures infra is complete before workflow batches begin. With 2 senior devs + AI,
> Phase 1 infra completes in ~2.5 days, so Dev 2 can start workflow work mid-sprint.

### Sprint 1 (2 weeks) — Foundation + Start Practitioner Creation
| Task | Owner | Days |
|------|-------|------|
| Create `PRM_AsyncJobRequest__c` object + all fields (AI-assisted) | Dev 1 | 0.25 |
| Create `PRM_AsyncJobQueued__e` + trigger + dispatcher | Dev 1 | 0.25 |
| Add `PRM_RequestId__c` / `PRM_Status__c` to 7 objects (AI generates XML) | Dev 1 | 0.25 |
| Create `PRM_SubmitAsyncJob` IP | Dev 1 | 0.5 |
| Create `PRM_RollbackBatch` (generic, corrected pattern) | Dev 1 | 0.5 |
| Rewire `PRM_PractitionerActivationBatch` into new async dispatcher | Dev 1 | 0.25 |
| Unit tests for all infra classes (AI-generated) | Dev 1 | 0.5 |
| Create `PRM_PDMJobStatusCard` FlexCard | Dev 2 | 0.5 |
| *(After infra complete, Day 3+)* Practitioner Creation Batches 1+2+3 | Dev 2 | 2.5 |
| *(After infra complete, Day 3+)* Practitioner Creation Batches 4+5 | Dev 1 | 1.5 |
| **Sprint 1 Total** | | **~7 days** |

### Sprint 2 (2 weeks) — PDM Practitioner (all sub-types) + OmniScript changes
| Task | Owner | Days |
|------|-------|------|
| PDM Practitioner — IBC Professional Staff + Network Update batches | Dev 2 | 1.5 |
| PDM Practitioner — Taxonomy + Admitting Privileges batches | Dev 2 | 1.5 |
| PDM Practitioner — Medicare + Delegated Update batches | Dev 2 | 0.5 |
| PDM Practitioner OmniScript changes (disable IPs, add submit action) | Dev 2 | 0.5 |
| Practitioner Creation OmniScript changes | Dev 1 | 0.5 |
| PDM Practice Location — AddRemovePractitioner + AddRemoveNetworks batches | Dev 1 | 1.5 |
| PDM Practice Location — Terminate PL + Taxonomy batches | Dev 1 | 1.5 |
| Unit tests for all Sprint 2 Apex (AI-generated) | Both | 1 |
| **Sprint 2 Total** | | **~8.5 days** |

### Sprint 3 (2 weeks) — PDM Practice Location (finish) + Testing + Deploy
| Task | Owner | Days |
|------|-------|------|
| PDM Practice Location — OfficeHours + Capitation + Directory batches | Dev 1 | 1.5 |
| PDM Practice Location OmniScript changes | Dev 1 | 0.5 |
| Unit tests remaining (AI-generated, senior reviews edge cases) | Dev 2 | 0.5 |
| Integration testing — Practitioner Creation E2E (real sandbox async) | Dev 2 | 1 |
| Integration testing — PDM Practitioner E2E | Dev 2 | 1 |
| Integration testing — PDM Practice Location E2E | Dev 2 | 1 |
| Verify FDP + BCBSA sync exclusion (new `PRM_IsActive__c` filters) | Dev 1 | 0.5 |
| UAT with business — all 3 flows | Both | 3 |
| Bug fixes from UAT | Both | 1.5 |
| Deployment + cutover runbook | Dev 1 | 0.75 |
| **Sprint 3 Total** | | **~11.25 days** |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **OmniScript IP disable breaks existing integrations** | Medium | High | Feature flag: keep old IPs active; toggle via Custom Setting `PRM_UseAsyncProcessing__c` |
| **Platform event delivery guarantee** (at-least-once) causes **duplicate dispatch** | **High** | High | `PRM_AsyncJobDispatcher.dispatch()` MUST check `PRM_AsyncJobRequest__c.Status != 'Queued'` before enqueuing; add `FOR UPDATE` on the status check |
| **Queueable job limit** (1 Queueable per transaction, max 50 chained) | Low | Medium | Use `Database.executeBatch` in queueable finish instead of `System.enqueueJob` for chain |
| **Heap size in stateful batch** | Low | Medium | Serialize payload into `PRM_AsyncJobRequest__c` (not stateful variable); re-query in execute() |
| **UI experience degradation** (users don't see immediate confirmation) | Medium | Medium | New confirmation step + status FlexCard on Case record |
| **Test coverage for complex batch chains** | Medium | High | Mock payloads from existing SampleInput.json files; existing `PRM_PractitionerActivationBatchBatchTest.cls` is a pattern to follow |
| **Rollback doesn't restore updated (not inserted) records** | Medium | High | For updates: store original values in `PRM_AsyncJobRequest__c.PRM_OriginalValues__c` JSON before updating |
| **Governor limits in rollback batch** | Low | Medium | Process deletes in batches of 200; use dynamic SOQL per object (UNION ALL not supported in QueryLocator) |
| **`PRM_PractitionerActivationBatch` chunk size** (currently batch size = 1) | Medium | Medium | A batch size of 1 is correct for complex nested operations but produces N async jobs for N practitioners; confirm acceptable for high-volume scenarios, or increase with risk assessment |
| **`PRM_FutureDatedProcessing__c` conflict** | Medium | High | The existing FDP system also updates `PRM_Status__c` and effective dates on `HCPF`, `HFN`, `HPT`. New async-created records with `Status = 'Pending'` must be excluded from FDP processing until activated. Add `PRM_IsActive__c = true` filter to `PRM_FutureDatedProcessingBatchHandler` queries |
| **BCBSA sync events** (`PRM_BCBSARecordsSyncEvents__e`) listening on the same objects | Medium | High | BCBSA sync platform event subscribers may pick up newly inserted `Status = Pending` records before activation. Confirm sync triggers filter `PRM_IsActive__c = true` or add the new field to existing filter logic |
| **SOQL UNION ALL in rollback batch** (from `PRM_Batch_Rollback_Strategies.md`) | **Confirmed bug** | High | Replace with chained per-object deletes in finish() (see corrected pattern in Section 4C) |

---

## 9. Definition of Done

- [ ] All 3 OmniScript flows submit asynchronously (no synchronous DR/IP record creation)
- [ ] `PRM_AsyncJobRequest__c` records created for every submission with correct Status progression
- [ ] All Apex batch classes have ≥ 80% unit test coverage
- [ ] Rollback tested: simulate Batch 3 failure → confirm Batch 1+2 records deleted
- [ ] E2E tested: practitioner creation with 3 locations + 2 taxonomies + 4 networks completes under 2 minutes
- [ ] FlexCard shows real-time job status on Case record
- [ ] No regression on existing flows (termination, reinstate, recred still work)
- [ ] Business UAT sign-off on all 3 flows
- [ ] Feature flag controls rollout (can revert to sync IPs without redeployment)
- [ ] **`PRM_IsActive__c` filter confirmed** in `PRM_FutureDatedProcessingBatchHandler` queries — no FDP processing of Pending records
- [ ] **BCBSA sync trigger** confirmed to exclude `PRM_IsActive__c = false` records
- [ ] **Platform event idempotency** verified: duplicate `PRM_AsyncJobQueued__e` delivery does not create duplicate batches
- [ ] **Rollback SOQL** uses per-object delete chains (no UNION ALL)

---

## 10. AI Productivity Model

| Work Category | AI Acceleration | Reason |
|---------------|----------------|--------|
| Custom object XML + field metadata | **4×** | Boilerplate; AI generates all 7 object field XMLs in one prompt |
| Apex batch scaffolding (execute/finish/start methods) | **3×** | Highly repetitive pattern; senior reviews business logic only |
| Unit test generation | **4×** | AI generates 80%+ coverage tests from existing SampleInput.json files |
| Rollback + activation batch logic | **2×** | Pattern is clear; technical edge cases still need senior review |
| OmniScript element changes (disable IPs, add submit action) | **1.5×** | OmniStudio IDE is mostly point-and-click, not accelerated by AI |
| Integration + E2E testing | **1.1×** | Async flows must run in real sandbox; AI cannot replace this |
| UAT | **1×** | Human-only — business must validate the async UX change |

> **Key bottleneck (not compressible):** UAT is 3 days minimum. Business stakeholders need
> to experience the new async confirmation UX ("Your request is processing...") and sign off
> that the status FlexCard is acceptable. This is the most common source of schedule overrun
> for this type of UX-impacting refactor.

---

## 11. Comparison: Current vs. Future State

| Metric | Current (Sync IP Chain) | Future (Async Batch) |
|--------|------------------------|---------------------|
| **User wait time** | 15–60 seconds (UI blocked) | < 2 seconds (instant return) |
| **Timeout risk** | High (15+ chained IPs) | None (form submission = 1 INSERT) |
| **Governor limit risk** | High (35–80 DML in one tx) | None (batch = 10 records per tx) |
| **Partial failure handling** | None (UI shows error, unknown state) | Full rollback via RequestId |
| **Scalability** | ~10 networks max before timeout | Unlimited (batch handles any volume) |
| **Error visibility** | IP error page, no detail | `PRM_AsyncJobRequest__c` error log + email notification |
| **Re-runability** | Manual re-do entire form | Re-queue specific RequestId |
| **Audit trail** | DataRaptor debug logs only | `PRM_AsyncJobRequest__c` + `PRM_BatchExecutionLog__c` |

---

*Document References:*
- *`PRM_Batch_Rollback_Strategies.md` — Rollback architecture options (note: UNION ALL fix applies)*
- *`UPHS_MASS_LOAD_SOLUTIONS.md` — UPHS batch load implementation (sister document)*
- *`PRM_PractitionerCreation_SampleInput.json` — Practitioner creation payload structure*
- *`PRM_PDMRecordsPractitionerCreationHelper_SampleInput.json` — PDM Practitioner change payload*
- *`PRM_PDMPLRecordsCreationHelper_SampleInput.json` — PDM Practice Location change payload*
- *`PRM_PDMRecordsCreationHelper` (50+ elements) — Full CB/DR/RA action inventory*
- *`PRM_PractitionerActivationBatch.cls` / `PRM_PractitionerActivationUtility.cls` — Existing activation batch (rewire, do not rebuild)*
- *`Provider_Data_Versioning_Estimation.md` — Companion versioning SK estimation*
