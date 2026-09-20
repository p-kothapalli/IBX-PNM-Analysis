# IBXQA Pre-Development Story Analysis Template
## Provider Network Management (PRM) — Salesforce Health Cloud

---

> **Purpose:** Every developer must complete this template before writing code for any user story. It ensures you've thought through OmniStudio impacts, governor limits, data model changes, and the multi-layered architecture of the PRM credentialing platform.
>
> **Time to complete:** 20-40 minutes for standard stories | 5-10 minutes for trivial config/copy changes (mark sections N/A)

---

# Story Design & Technical Kickoff

| Field | Value |
|-------|-------|
| **Work Item ID** | _[e.g., 1402515]_ |
| **Story Title** | _[Title from sprint backlog]_ |
| **Category** | _[e.g., Ancillary Reassessment / PDM Manual / PNC / Initial Cred / ReCred / PAR Form / Prod Feedback]_ |
| **Sprint** | _[Sprint number, e.g., Sprint 53]_ |
| **Developer** | _[Name]_ |
| **Date Completed** | _[Date]_ |
| **Tech Lead Reviewer** | _[Name]_ |
| **Tags** | _[e.g., BX; Go Live; NFD; Credentialing]_ |
| **Status** | `Draft` / `In Review` / `Approved` |

---

## 1. Impacted Objects & Components

> **Instructions:** List every Salesforce object, OmniStudio component, Apex class, LWC, trigger, flow, and external system affected. This project has 71 custom PRM objects, 314 non-test Apex classes, 166 LWC components, 1417 Integration Procedures, 1359 DataRaptors, and 663 OmniScript versions — you MUST identify what you're touching.

### 1.1 Salesforce Objects (Data Model)

| Object API Name | Nature of Impact | Fields Added/Modified | Record Types Affected |
|----------------|-----------------|----------------------|----------------------|
| _e.g., `PRM_HealthcareFacilityAssociation__c`_ | _New field added_ | _`PRM_DelegatedFlag__c` (Checkbox)_ | _All_ |
| _e.g., `PRM_CaseManagerAssociation__c`_ | _Query pattern change_ | _None_ | _PRM_Practitioner_ |
| _e.g., `IndividualApplication`_ | _Status field update_ | _`Status` picklist value added_ | _N/A_ |

### 1.2 OmniStudio Components

| Component Type | Component Name | Version | Change Description |
|---------------|---------------|---------|-------------------|
| OmniScript | _e.g., `PRM_PractitionerParticipationForm_English` v27_ | _Active_ | _Add QC_EditMode flag propagation_ |
| Integration Procedure | _e.g., `PRM_AccountTermination_Procedure` v17_ | _Active_ | _New action step for delegated check_ |
| DataRaptor (Extract) | _e.g., `DRExtractAccountRelationship`_ | _v1_ | _Add filter condition for active records_ |
| DataRaptor (Load/Transform) | _e.g., `PRMCreateCaseManagerAndCase`_ | _v1_ | _Map new field to output_ |
| FlexCard / OmniUI Card | _e.g., `prmAddressDetailsCard`_ | — | _Add column for delegated status_ |

### 1.3 Apex Classes & Triggers

| Class/Trigger Name | Type | Change Description |
|-------------------|------|-------------------|
| _e.g., `PRM_AddressManagementService.cls`_ | Service | _Add `validateDelegatedAddress()` method_ |
| _e.g., `PRM_AccountTriggerHandler.cls`_ | Trigger Handler | _Add before-update logic for delegated flag_ |
| _e.g., `PRM_AccountTerminationBatch.cls`_ | Batch Apex | _Extend query to include delegated accounts_ |
| _e.g., `PRM_AddressManagementServiceTest.cls`_ | Test Class | _Add test methods for new delegated path_ |

### 1.4 Lightning Web Components (LWC)

| Component Name | Change Description | Parent/Consumer |
|---------------|-------------------|-----------------|
| _e.g., `prmAddressGroupManager`_ | _Add delegated badge to address rows_ | _`prmAddressGroupManagerPage` (Aura wrapper)_ |
| _e.g., `prmAddressUtils`_ | _Add validation for delegated address rules_ | _Headless utility, consumed by multiple LWC_ |

### 1.5 Flows & Automation

| Flow/Automation Name | Type | Change |
|--------------------|------|--------|
| _e.g., `PRM_CaseManagerClosureFlow`_ | Record-Triggered Flow | _Add criteria for delegated case type_ |
| _e.g., `PRM_DailyScheduledFlowToCheckIfCaseHasExpiredOrNot`_ | Scheduled Flow | _No change, but verify not broken_ |

### 1.6 External Integrations

| Integration | Direction | Impact |
|------------|-----------|--------|
| _Precisely Address API_ | Outbound callout | _No change / New field in request payload_ |
| _CAQH Roster API_ | Outbound callout | _N/A_ |
| _BCBSA Sync_ | Bidirectional (Platform Event) | _Verify new field doesn't break sync event schema_ |
| _Mulesoft Connector_ | Inbound | _N/A_ |
| _NPDB_ | Outbound | _N/A_ |
| _SendGrid (Notifications)_ | Outbound | _N/A_ |

### 1.7 Permission Sets & Security

| Permission Set | Change |
|---------------|--------|
| _e.g., `PRM_CredentialingUser`_ | _Add FLS for new field `PRM_DelegatedFlag__c`_ |
| _e.g., `PRM_NetworkManagementQC`_ | _No change needed_ |

---

## 2. Dependencies & Blockers

> **Instructions:** PRM stories frequently depend on other stories being deployed first (especially batch frameworks, data model changes, or IP chains). Identify these explicitly.

| Dependency | Type | Status | Owner | Work Item ID |
|-----------|------|--------|-------|-------------|
| _e.g., Practitioner Creation Batch framework deployed to QA_ | Upstream (code) | `Done` / `In Progress` / `Blocked` | _[name]_ | _1387014_ |
| _e.g., `PRM_DelegatedOnly_to_PRM_Delegated` field migration complete_ | Data model | _[status]_ | _[name]_ | _1167777_ |
| _e.g., Design confirmation on UI for delegated badge_ | Design/Product | _[status]_ | _[BA name]_ | — |
| _e.g., Notify BCBSA sync team of schema change_ | Downstream notification | _[status]_ | _[name]_ | — |

**Hard Blockers (cannot start development):**
- _[List or "None"]_

**Soft Blockers (can start but cannot complete/deploy):**
- _[List or "None"]_

---

## 3. Technical Implementation Plan

### 3.1 Summary of Approach

_[1-3 sentences. What is the high-level strategy? Are you modifying an existing OmniScript, creating new Apex, extending a batch framework, or building an LWC?]_

**Approach Type:** _(check all that apply)_
- [ ] OmniScript modification (republish required)
- [ ] Integration Procedure new/update
- [ ] DataRaptor new/update
- [ ] Apex class — new service
- [ ] Apex class — modify existing
- [ ] Batch Apex (new or extending existing framework)
- [ ] Trigger / Trigger Handler update
- [ ] LWC — new component
- [ ] LWC — modify existing
- [ ] Flow — new or update
- [ ] Data Model — new field/object
- [ ] Data Model — field modification (picklist values, formula, etc.)
- [ ] Permission Set / FLS change
- [ ] Custom Metadata Type (CMT) update
- [ ] Configuration only (no code)
- [ ] Data Fix (DFX framework)

### 3.2 Detailed Implementation Steps

> **Instructions:** Be specific enough that another PRM developer could pick this up. Include file paths, method names, and OmniScript element names.

#### Data Model Changes
- [ ] _e.g., Add field `PRM_DelegatedFlag__c` (Checkbox, default false) to `PRM_HealthcareFacilityAssociation__c`_
- [ ] _e.g., Add picklist value "Delegated" to `PRM_CaseManagerAssociation__c.Status__c`_
- [ ] _e.g., Create Custom Metadata record `PRM_Constant__mdt.Delegated_Threshold` = 90_

#### OmniStudio Changes
- [ ] _e.g., OmniScript `PRM_PractitionerParticipationForm_English` → Step "GroupSelection" → Add conditional visibility: `%DelegatedFlag% == true`_
- [ ] _e.g., Integration Procedure `PRM_AccountTypeRecordCreations_Procedure` → Add new Action step "Check Delegated" after step 3_
- [ ] _e.g., DataRaptor `DRExtractAccountRelationship` → Add filter: `PRM_DelegatedFlag__c = true`_
- [ ] _e.g., **Republish OmniScript version:** X → X+1_

#### Apex Changes
- [ ] _e.g., `PRM_AddressManagementService.cls` → Add method `validateDelegatedAddress(Id facilityId, Boolean isDelegated): AddressValidationResult`_
- [ ] _e.g., `PRM_AccountTriggerHandler.cls` → Add `handleDelegatedFlagChange()` in `beforeUpdate` switch_
- [ ] _e.g., New class: `PRM_DelegatedStatusService.cls` — service for delegated status logic_
- [ ] _e.g., Batch: Extend `PRM_AccountCreationCrossRefBatch.cls` → Add `WHERE PRM_DelegatedFlag__c = true` to query_

#### LWC Changes
- [ ] _e.g., `prmAddressGroupManager` → Add lightning-badge for delegated status in address row template_
- [ ] _e.g., `prmAddressUtils` → Add export function `isDelegatedAddress(address): Boolean`_

#### Flow / Automation Changes
- [ ] _e.g., `PRM_CaseManagerClosureFlow` → Add decision element for delegated case type_

### 3.3 OmniScript / IP Call Chain (if applicable)

> **Instructions:** If your change touches an OmniScript → IP → DR chain, map the full call path so reviewers can trace data flow.

```
OmniScript: PRM_PractitionerParticipationForm_English
  └─ Step: GroupSelection
       └─ IP Action: PRM_AccountTypeRecordCreations_Procedure
            ├─ DR Extract: DRExtractAccountRelationship
            ├─ Action: CheckDelegatedStatus (NEW)
            ├─ DR Load: PRMCreateCaseManagerAndCase
            └─ Response Action: Return to OS
```

### 3.4 Governor Limit Assessment

> **CRITICAL for this project.** PRM regularly hits governor limits (100 SOQL synchronous, 200 async, 6MB heap, CPU timeouts). Assess whether your change adds SOQL/DML/CPU load.

| Limit | Current Usage (estimate) | Your Change Adds | Total | Risk |
|-------|------------------------|-----------------|-------|------|
| SOQL queries (sync: 100) | _e.g., 45_ | _+3_ | _48_ | `Safe` / `Watch` / `Danger` |
| SOQL queries (async: 200) | _e.g., 120_ | _+5_ | _125_ | _[assessment]_ |
| DML statements (150) | _e.g., 30_ | _+2_ | _32_ | _[assessment]_ |
| DML rows (10,000) | _e.g., 200_ | _+50_ | _250_ | _[assessment]_ |
| Heap (6MB sync / 12MB async) | _e.g., 3MB_ | _+0.5MB_ | _3.5MB_ | _[assessment]_ |
| CPU time (10s sync / 60s async) | _e.g., 4s_ | _+0.5s_ | _4.5s_ | _[assessment]_ |
| Callouts (100) | _e.g., 2_ | _+0_ | _2_ | _[assessment]_ |

**Mitigation if limits are at risk:**
- _[e.g., "Move to Batch Apex if > 80 SOQL", "Use Platform Event for async processing", "Bulkify the query"]_

---

## 4. Acceptance Criteria Breakdown & Estimation

> **Instructions:** Copy each AC verbatim from the work item. Break into sub-tasks mapped to specific components (Apex, OmniScript, LWC, DataRaptor, etc.). Estimate in hours.

| # | Acceptance Criteria (from ticket) | Sub-Tasks | Component | Est. (hrs) |
|---|----------------------------------|-----------|-----------|-----------|
| AC-1 | _"[verbatim]"_ | | | |
| | | 1. _[task]_ | _Apex_ | _Xh_ |
| | | 2. _[task]_ | _OmniScript_ | _Xh_ |
| | | 3. _[task]_ | _LWC_ | _Xh_ |
| | | 4. _[task]_ | _Test class_ | _Xh_ |
| AC-2 | _"[verbatim]"_ | | | |
| | | 1. _[task]_ | _IP/DR_ | _Xh_ |
| | | 2. _[task]_ | _Apex_ | _Xh_ |
| | **TOTAL** | | | **_Xh_** |

| Estimation Summary | |
|--------------------|---|
| Total estimated hours | _[X]h_ |
| Story points assigned | _[N]_ |
| Confidence level | `High` / `Medium` / `Low` |
| Biggest risk to estimate | _[describe, e.g., "Unsure if existing IP can handle additional action steps without timeout"]_ |

---

## 5. Testing Strategy

> **Instructions:** PRM requires test coverage for Apex deployment. OmniStudio components require manual sandbox testing. Plan both.

### 5.1 Apex Test Coverage

| Test Class | Methods to Add/Update | What's Tested | Bulk Test? |
|-----------|----------------------|--------------|-----------|
| _e.g., `PRM_AddressManagementServiceTest.cls`_ | _`testValidateDelegatedAddress_positive`, `testValidateDelegatedAddress_negative`_ | _New delegated validation logic_ | _Yes (200 records)_ |
| _e.g., `PRM_AccountTriggerHandlerTest.cls`_ | _`testDelegatedFlagChange_bulkUpdate`_ | _Trigger fires correctly on bulk_ | _Yes_ |

**Minimum coverage target:** _75% (Salesforce deployment minimum) / Team target: ≥85%_

### 5.2 OmniStudio Manual Testing

| OmniScript / IP | Test Scenario | Test Data | Expected Result |
|----------------|---------------|-----------|-----------------|
| _e.g., PRM_PractitionerParticipationForm v28_ | _Select delegated group, verify conditional UI_ | _Account: "HMHMG Specialty Care", NPI: 1215989249_ | _Delegated badge shown, PNC path skipped_ |
| _e.g., PRM_AccountTypeRecordCreations IP_ | _Submit with delegated flag = true_ | _Same account_ | _CaseManager record created with Delegated status_ |

### 5.3 LWC Unit Tests (Jest)

| Component | Test File | Scenarios |
|-----------|----------|-----------|
| _e.g., `prmAddressGroupManager`_ | _`prmAddressGroupManager.test.js`_ | _Delegated badge renders when flag=true; hidden when false_ |

### 5.4 Integration / E2E Testing in QA Sandbox

| Flow | Scenario | Steps | Verify |
|------|----------|-------|--------|
| _e.g., PAR Form → PDA → QC_ | _Delegated practitioner full path_ | _1. Create practitioner 2. Submit PAR 3. Complete PDA 4. QC Review_ | _All records created correctly, delegated field populated_ |

---

## 6. Deployment Plan

> **Instructions:** PRM deployments follow a specific order due to metadata dependencies. Use the project's existing scripts where possible.

### 6.1 Deployment Order

| Step | What | Method | Command / Script |
|------|------|--------|-----------------|
| 1 | _Object/Field metadata_ | _sf project deploy start_ | `sf project deploy start --source-dir force-app/main/default/objects/PRM_HealthcareFacilityAssociation__c --target-org qa-sandbox` |
| 2 | _Permission Sets (FLS)_ | _sf project deploy start_ | `sf project deploy start --source-dir force-app/main/default/permissionsets/PRM_CredentialingUser.permissionset-meta.xml --target-org qa-sandbox` |
| 3 | _Apex Classes + Tests_ | _TEST_DEPLOYMENT_COMMANDS.sh_ | `./TEST_DEPLOYMENT_COMMANDS.sh` |
| 4 | _LWC_ | _sf project deploy start_ | `sf project deploy start --source-dir force-app/main/default/lwc/prmAddressGroupManager --target-org qa-sandbox` |
| 5 | _OmniStudio (OS/IP/DR)_ | _Manual via OmniStudio Designer_ | _Activate version X+1 in UI_ |
| 6 | _Flows_ | _sf project deploy start_ | _[command]_ |
| 7 | _Run Tests_ | _sf apex run test_ | `sf apex run test --class-names PRM_AddressManagementServiceTest --target-org qa-sandbox --wait 10` |

### 6.2 OmniScript Version Management

| Component | Current Active Version | New Version | Activate After Deploy? |
|-----------|----------------------|-------------|----------------------|
| _e.g., PRM_PractitionerParticipationForm_English_ | _v27_ | _v28_ | _Yes — deactivate v27 first_ |

### 6.3 Rollback Plan

| If This Fails... | Rollback Action | Reversible? |
|------------------|----------------|-------------|
| _New field breaks existing triggers_ | _Deactivate trigger via `PRM_TriggerBypass` permission set, then remove field_ | _Yes_ |
| _OmniScript new version has UI bug_ | _Reactivate previous version (v27), deactivate v28_ | _Yes — OmniScript versioning supports this_ |
| _IP timeout on new action step_ | _Remove action step in OmniStudio Designer, reactivate previous IP version_ | _Yes_ |
| _Batch Apex fails with governor limit_ | _Abort batch via Setup → Apex Jobs, reduce batch size, redeploy_ | _Yes_ |
| _Data model field added_ | _Field is additive (nullable) — no rollback needed, just don't populate_ | _Yes (safe)_ |

### 6.4 Feature Toggle (if applicable)

| Toggle Mechanism | Name | Default | How to Disable |
|-----------------|------|---------|---------------|
| Custom Setting | _`PRM_FeatureConfigurationSettings__c.DelegatedEnabled__c`_ | _false_ | _Set to false in Setup → Custom Settings_ |
| Custom Metadata | _`PRM_Constant__mdt.Delegated_Active`_ | _true_ | _Deactivate CMT record_ |
| Permission Set | _Assign `PRM_CredentialingUser` only to pilot users_ | — | _Remove permission set assignment_ |

---

## 7. Security & Data Considerations

| Consideration | Assessment |
|--------------|-----------|
| **New fields contain PHI/PII?** | _[e.g., "No — delegated flag is operational only" / "Yes — practitioner SSN visible in new panel"]_ |
| **HIPAA implications?** | _[e.g., "N/A" / "New field exposes provider credentialing status — restrict via FLS"]_ |
| **Sharing rules affected?** | _[e.g., "No — existing OWD and sharing rules cover this" / "Need new sharing rule for delegated records"]_ |
| **Record-level access?** | _[e.g., "Existing `PRM_CredentialingUser` permission set covers FLS"]_ |
| **Trigger Bypass consideration?** | _[e.g., "PRM_TriggerBypass perm set exists — ensure new trigger logic respects bypass check"]_ |
| **Portal/Community access?** | _[e.g., "N/A" / "Portal users can see this via `PRM_OmniStudioPermissionPortal`"]_ |
| **Audit trail needed?** | _[e.g., "No" / "Yes — log changes to PRM_ExceptionLog__c"]_ |

---

## 8. Observability & Error Handling

> **Instructions:** PRM uses `PRM_ExceptionLog__c` for error logging and `PRM_ExceptionLogEvent__e` platform events for async error capture. Plan how errors surface.

| Scenario | Error Handling Approach |
|----------|----------------------|
| _IP timeout on large practitioner_ | _Log to `PRM_ExceptionLog__c`, show user-friendly error in OmniScript_ |
| _Batch partial failure_ | _Stage to `PRM_FailedRecordStaging__c`, surface in Data Admin list view_ |
| _Precisely API callout failure_ | _Existing fallback: `PRM_AddressValidationService.isPreciselySkipped()` bypass_ |
| _DML failure in trigger_ | _Log via `PRM_ExceptionLogEvent__e` platform event (rollback-safe)_ |

**Post-deploy monitoring (first 30 minutes):**
- [ ] Check `PRM_ExceptionLog__c` for new error entries
- [ ] Verify Apex Jobs (Setup → Apex Jobs) if batch was deployed
- [ ] Test the flow end-to-end once in QA org
- [ ] Review debug logs: `sf apex tail log --target-org qa-sandbox`

---

## 9. Open Questions & Assumptions

### Open Questions

| # | Question | Directed To | Status | Answer |
|---|----------|------------|--------|--------|
| Q1 | _[e.g., "Should delegated practitioners skip PNC check entirely or just get different routing?"]_ | _Product/BA_ | `Open` / `Resolved` | _[answer]_ |
| Q2 | _[e.g., "What's the max number of practice locations for a delegated practitioner?"]_ | _Product_ | _[status]_ | _[answer]_ |
| Q3 | _[e.g., "Is the existing IP version chain stable or is another team modifying it this sprint?"]_ | _[Dev name]_ | _[status]_ | _[answer]_ |

### Assumptions

| # | Assumption | Risk if Wrong | Validated By |
|---|-----------|--------------|-------------|
| A1 | _[e.g., "Existing `PRM_AccountTypeRecordCreations_Procedure` IP can accept one more action step without hitting timeout"]_ | _High — would need batch refactor_ | _[unvalidated / name+date]_ |
| A2 | _[e.g., "Delegated practitioners will never exceed 10 practice locations"]_ | _Medium — governor limit concern beyond 10_ | _[Product confirmed 2026-05-20]_ |
| A3 | _[e.g., "The BCBSA sync will ignore the new field since it's not in their field mapping config"]_ | _Medium — could break sync_ | _[unvalidated]_ |

---

## 10. Out of Scope

> **Instructions:** Explicitly state what this story does NOT cover. This prevents scope creep in sprint.

- _[e.g., "Migrating existing delegated records — separate data fix story using DFX framework"]_
- _[e.g., "Portal-facing UI for delegated status — future sprint"]_
- _[e.g., "BCBSA sync schema update for new field — depends on BCBSA team timeline"]_
- _[e.g., "Performance optimization of the full IP chain — separate tech debt story"]_

---

## 11. Retrieval & Sync Notes

> **Instructions:** After deploying to QA sandbox, other developers need to sync. Note what components to retrieve.

**Retrieval scope for teammates after this deploys:**
```bash
# Use existing script:
./RETRIEVE_COMPONENTS_FROM_QA.sh
# Select option: [1-ALL / 2-Apex / 3-LWC / 5-Phase5 / 6-Custom]

# Or manual retrieval of specific components:
sf project retrieve start \
  --metadata ApexClass:PRM_AddressManagementService \
  --metadata ApexClass:PRM_AddressManagementServiceTest \
  --metadata CustomObject:PRM_HealthcareFacilityAssociation__c \
  --target-org qa-sandbox
```

---

## Sign-Off

| Role | Name | Date | Approved? |
|------|------|------|-----------|
| Developer | _[name]_ | _[date]_ | Yes |
| Tech Lead | _[name]_ | _[date]_ | _[pending]_ |
| BA / Product (optional) | _[name]_ | _[date]_ | _[pending]_ |

---

## Quick Reference: When to Use What

| If your story involves... | You MUST fill out... |
|--------------------------|---------------------|
| Any OmniScript change | Sections 1.2, 3.3, 6.2 (version management) |
| Any Apex change | Sections 1.3, 3.4 (governor limits), 5.1 (test coverage) |
| Data model change | Sections 1.1, 6.1 (deploy order — fields FIRST), 7 (security) |
| Batch Apex | Sections 3.4 (governor limits), 5.4 (integration testing), 6.3 (rollback) |
| IP → DR chain modification | Sections 1.2, 3.3 (call chain diagram), 3.4 (SOQL assessment) |
| External integration (Precisely, CAQH, BCBSA) | Sections 1.6, 8 (error handling), 9 (assumptions about contracts) |
| LWC modification | Sections 1.4, 5.3 (Jest tests), 6.1 (deploy order — Apex before LWC) |
| Config/Permission only | Sections 1.7, 6.1 — mark other sections N/A |
| Data Fix (DFX) | Sections 1.1, 3.2 (CMT config), 6.3 (rollback), 8 (monitoring) |

---

## Changelog

_[Update this section if significant discoveries change the plan during development]_

| Date | Change | Reason |
|------|--------|--------|
| _[date]_ | _[what changed]_ | _[why]_ |
