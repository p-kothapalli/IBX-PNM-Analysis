# NPDB Data Validation — Architecture Diagrams

**Companion to:** `00_Overview_NPDB_T180_Validation.md`
**Date:** 2026-06-01
**Updated:** 2026-06-08 — Manual-path design pivot (US-NPDB-02 v4): validation moved into the `PRM_IPCreateAdverseActionLog` IP layer and surfaced via native OmniScript **Message + Validation** elements rendering the validator's link-free `detailText`. Replaces the `prmNpdbValidationBanner` LWC + Fix/Add deep-link approach in §2, §3, and §6.

---

## 1. End-to-end sequence — T-180 batch (automated path)

```mermaid
sequenceDiagram
    autonumber
    participant Sched as PRM_CheckCAQHAccessOnDueAccountsScheduler<br/>(nightly midnight)
    participant T180 as PRM_CheckCAQHAccessOnDueAccountsBatch
    participant Exec as PRM_CheckCAQHExecuteHelper.processAccount
    participant Validator as PRM_NpdbDataValidator (NEW)
    participant Init as PRM_CheckCAQHRecordInitHelper
    participant CM as IndividualApplication
    participant Case as Case
    participant AAL as PRM_AdverseActionLog__c
    participant Trigger as PRM_AdverseActionLogTrigger (NEW gate)
    participant NpdbApi as NPDB Outbound Integration

    Sched->>T180: Schedule.execute()
    T180->>T180: Build SOQL from PRM_CAQHDateRangeSetting__c.PRM_DueDays__c (180)
    T180->>Exec: execute(scope) — Accounts where ReCredDue = T-180
    Exec->>Validator: validateNpdbReady(account, dataWrapper)
    Validator-->>Exec: ValidationResult { isValid, findings[], detailsJson }

    alt isValid == true (clean data)
        Exec->>Init: initializeAdvActionLogRecord(...)
        Init->>AAL: build AAL (Status = Ready To Process)
        Exec->>CM: INSERT CM Status = "Pending NPDB"
        Exec->>Case: INSERT Case Status = "Pending NPDB"
        Exec->>AAL: INSERT AAL
        Note over Trigger: Before-insert gate re-runs validator<br/>(belt + braces). Passes.
        NpdbApi-->>AAL: polls Ready To Process AALs → fires request
    else isValid == false (missing data)
        Exec->>CM: INSERT CM Status = "NPDB Action Needed"<br/>PRM_NPDBValidationDetails__c = detailsJson<br/>PRM_NPDBValidationLastRun__c = now
        Exec->>Case: INSERT Case Status = "NPDB Action Needed"
        Note over Exec,AAL: NO AAL inserted — NPDB request<br/>cannot be fired with bad data.
        Note over CM: Ops sees CM on the<br/>"NPDB Action Needed" report<br/>(US-NPDB-03)
    end
```

---

## 2. End-to-end sequence — Manual `Request NPDB` button

```mermaid
sequenceDiagram
    autonumber
    participant User as Cred Specialist
    participant FP as Case Manager FlexiPage<br/>(PRM_NPDB button)
    participant OS as PRM_CallNPDB_English OmniScript
    participant ParentIP as PRM_IPCreateAdverseActionLogParent IP
    participant IP as PRM_IPCreateAdverseActionLog IP<br/>(loads Addr/NPI/License/Education)
    participant Validator as PRM_NpdbDataValidator (NEW)<br/>Callable validateForOmni
    participant Trigger as PRM_AdverseActionLogTrigger gate (NEW)
    participant AAL as PRM_AdverseActionLog__c

    User->>FP: Click "Request NPDB"
    FP->>OS: Launch CallNPDB OmniScript<br/>ContextId = CM Id
    OS->>ParentIP: Submit -> run wrapper IP
    ParentIP->>IP: Run child IP
    IP->>Validator: validate using already-loaded data
    Validator-->>IP: { npdbValid, npdbDetailText }

    alt npdbValid == true
        IP->>AAL: Build AAL records
        AAL->>Trigger: BEFORE INSERT
        Trigger->>Validator: validateForAal(aal)
        Validator-->>Trigger: isValid = true
        Trigger-->>AAL: allow INSERT
        IP-->>OS: isExists = true
        OS-->>User: Success message ("request submitted")
    else npdbValid == false
        IP-->>OS: npdbValid=false + npdbDetailText (NO AAL created)
        OS-->>User: Detailed text Message element renders npdbDetailText:<br/>"Primary Address - Street Address Line 1 is blank - add it..."<br/>"NPI - No active NPI found - add an NPI record..."<br/>"SBRD License - none found - add license # and state..."
        Note over OS: Submit/Next disabled by Validation (Requirement)<br/>element bound to npdbValid = false (no links)
        User->>User: Read message -> navigate -> fix -> retry
    end
```

> The same pattern — validator IP-action + a detailed text **Message** element + a **Validation** (Requirement) element — is injected into the PSV Review, ReCred QC, Initial Cred App Review, and Cred App Review Complete OmniScripts right before the NPDB Integration Procedure Action, so every manual surface gets the same validation and the same plain-English, link-free message. The Ancillary path additionally renders per-facility findings on the practice-location step via `PRM_GetAncNpdbDetails`.

---

## 3. Component diagram

```mermaid
graph TB
    subgraph Schedulers
        S1[PRM_CheckCAQHAccessOnDueAccountsScheduler]
    end

    subgraph Batches
        B1[PRM_CheckCAQHAccessOnDueAccountsBatch]
        B2[PRM_CreateAdverseActionNpdbBatch]
        B3[PRM_ReinitiateNPDBReport]
    end

    subgraph Apex_Validation_Service [Apex Validation Service NEW]
        V1[PRM_NpdbDataValidator]
        V2[PRM_NpdbDataValidator.FieldRules]
        V3[PRM_NpdbValidationFieldConfig__mdt]
    end

    subgraph Triggers
        T1[PRM_AdverseActionLogTrigger NEW]
        T2[PRM_AdverseActionLogTriggerHandler NEW]
        T3[PRM_IndividualApplicationTrigger<br/>existing — release flip]
    end

    subgraph LWC
        L1[Read-only findings text surface NEW<br/>renders Validation Details, no links]
        L2[pRMPracLocAncNpdb existing]
    end

    subgraph OmniScripts
        O1[PRM_CallNPDB_English]
        O2[PRM_PSVSubOsWSNPDB_English]
        O3[PRM_InitialCredentialAppReview_English]
        O4[PRM_CredentialAppReviewCompleteOS_English]
        O5[PRM_RecredQC_English]
    end

    subgraph IntegrationProcedures
        I1[PRM_IPCreateAdverseActionLogParent]
        I2[PRM_CreateAdverseActionLog_Procedure]
    end

    subgraph Data
        D1[(IndividualApplication<br/>Status + PRM_NPDBValidationDetails__c NEW)]
        D2[(Case<br/>Status)]
        D3[(PRM_AdverseActionLog__c)]
        D4[(Account / Address / NPI / License / Education)]
    end

    S1 --> B1
    B1 --> V1
    B1 --> D1
    B1 --> D2

    O1 --> L1
    O2 --> L1
    O3 --> L1
    O4 --> L1
    O5 --> L1
    L1 -->|@AuraEnabled| V1

    O1 --> I1
    O2 --> I2
    I1 --> B2
    B2 --> T1
    T1 --> T2
    T2 --> V1
    T2 --> D3

    B3 --> T1

    V1 --> V2
    V1 --> V3
    V1 --> D4

    T3 --> D1
```

---

## 4. State diagram — Case Manager Status (with new value)

```mermaid
stateDiagram-v2
    [*] --> Pending_CAQH_Access: T-180 batch — CAQH not active
    [*] --> Pending_NPDB: T-180 batch — CAQH active, data clean
    [*] --> NPDB_Action_Needed: T-180 batch — CAQH active, data missing (NEW)

    Pending_CAQH_Access --> Pending_NPDB: CAQH re-checked OK
    Pending_NPDB --> NPDB_Action_Needed: AAL trigger gate blocks (defense-in-depth)
    NPDB_Action_Needed --> Pending_NPDB: Validation now passes<br/>(field fix → IA trigger flips back)

    Pending_NPDB --> Application_Review: NPDB report received clean
    Application_Review --> PSV: app review done
    PSV --> QC_Review: PSV done
    QC_Review --> Committee_Review: QC done
    Committee_Review --> Approved: committee approves
    Committee_Review --> Denied: committee denies

    note right of NPDB_Action_Needed
      • No AAL inserted
      • PRM_NPDBValidationDetails__c populated
      • Visible on US-NPDB-03 report
      • Round-robin to NPDB queue
      • Letter batch skips this status
    end note
```

---

## 5. Validation flow — single decision used by all surfaces

```mermaid
flowchart TD
    Start([NPDB request about to be created<br/>batch OR manual OR trigger gate]) --> Resolve[Resolve context:<br/>recordType, account, addressMap,<br/>licenseList, npiMap, educationList]
    Resolve --> Slice{Record type?}

    Slice -->|PRM_Practitioner<br/>PRM_ReCredentialing<br/>PRM_PractitionerParticipationRequest| RuleP[Apply Practitioner rule set]
    Slice -->|Ancillary Assessment<br/>Ancillary Re-Assessment| RuleA[Apply Ancillary rule set]
    Slice -->|other| RuleNoop[Skip — no validation needed]

    RuleP --> CheckP{All required fields present?}
    RuleA --> CheckA{All required fields + facility/affiliation present?}

    CheckP -->|yes| Pass([Return isValid = true])
    CheckP -->|no| Findings([Build MissingFieldFinding list:<br/>fieldApiName, friendlyLabel,<br/>sourceObject, sourceRecordId, fixUrl])

    CheckA -->|yes| Pass
    CheckA -->|no| Findings

    Findings --> ResultBad([Return isValid = false<br/>detailsJson serialized to AAL/CM])
    Pass --> ResultGood([Return isValid = true])

    ResultGood --> Done([Caller proceeds — AAL inserted])
    ResultBad --> Done2([Caller: CM → NPDB Action Needed<br/>no AAL inserted<br/>banner renders findings])
```

The `PRM_NpdbValidationFieldConfig__mdt` custom metadata stores **which fields are required per `RecordType.DeveloperName`**. That keeps the validator data-driven — adding a new request type only requires a metadata record, not an Apex deploy.

---

## 6. Where the validator gets plugged in (cheat sheet)

| Caller | Hook point | Lines / file |
|--------|-----------|--------------|
| T-180 batch | `PRM_CheckCAQHExecuteHelper.processAccount` — before `createActiveCAQHRecords` | `force-app/main/default/classes/PRM_CheckCAQHExecuteHelper.cls` |
| Manual button OmniScript | Validator IP-action inside `PRM_IPCreateAdverseActionLog` returns `npdbValid` / `npdbDetailText`; OmniScript renders a detailed text **Message** + **Validation** element in `PRM_CallNPDB_English_*` | `force-app/main/default/omniScripts/PRM_CallNPDB_English_*.os-meta.xml`; `PRM_IPCreateAdverseActionLog_Procedure_*` |
| PSV / ReCred QC / Initial Cred OmniScripts | Same validator IP-action + detailed text Message + Validation injected into `PRM_PSVSubOsWSNPDB_English_*`, `PRM_RecredQC_English_*`, `PRM_InitialCredentialAppReview_English_*`, `PRM_CredentialAppReviewCompleteOS_English_*` | OmniScript metadata |
| Server-side safety gate | New `PRM_AdverseActionLogTrigger` (before-insert) → `PRM_AdverseActionLogTriggerHandler.beforeInsert` calls `validator.validateForAal(aal)` | new files |
| Release flip | `PRM_IndividualApplicationTrigger` → `PRM_IndividualApplicationTriggerHandler` (existing) — on field update, if record was in `NPDB Action Needed` and validator now returns `isValid = true`, flip Status to `Pending NPDB` + clear `PRM_NPDBValidationDetails__c` | existing trigger; new handler branch |
