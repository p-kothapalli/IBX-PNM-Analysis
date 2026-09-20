# User Story: Practitioner Role Rollup from PPL to Person Account

## Story

**As a** Provider Network Operations Administrator,  
**I want** the Practitioner's Provider Role (`PRM_ProviderRole__c`) on the Person Account to automatically reflect the aggregated role across all active Practitioner Practice Location (PPL) records,  
**So that** downstream processes (provider search, network adequacy reporting, Concierge eligibility, directory feeds) always reflect the current state of the practitioner's roles across their practice locations.

---

## Background / Current State

### What EXISTS today:
- **HFN → PPL rollup** is implemented in `PRM_PracLocNetworkAutomationService.updatePracitionerRoleForPPL()`
- When HealthcareFacilityNetwork records change, the PPL's `PRM_PractitionerRole__c` is recalculated (PCP, Specialist, Dual, or blank)
- This fires from `PRM_HCFacilityNetworkTriggerHelper`

### What's MISSING:
- **PPL → Account rollup** does NOT exist as automated logic
- When a PPL's role changes or a PPL is terminated, `Account.PRM_ProviderRole__c` is NOT recalculated
- IBC Automated Fields doc notes this is "Handled By DART" (migration tool only, not runtime)

### Object Relationships:
```
Account (Person Account - Practitioner)
  └── PRM_ProviderRole__c  ← THIS NEEDS TO BE AUTO-CALCULATED
      │
      ├── HealthcarePractitionerFacility (PPL) [PractitionerId → Account]
      │     └── PRM_PractitionerRole__c = PCP | Specialist | Dual | blank
      │
      ├── HealthcarePractitionerFacility (PPL) [at another location]
      │     └── PRM_PractitionerRole__c = PCP | Specialist | Dual | blank
      │
      └── ... (N PPL records per practitioner)
```

---

## Acceptance Criteria

### AC-1: Single Active PPL – PCP
**Given** a Practitioner has one active PPL with `PRM_PractitionerRole__c` = 'PCP'  
**When** the system recalculates the Account role  
**Then** `Account.PRM_ProviderRole__c` = 'PCP'

### AC-2: Single Active PPL – Specialist
**Given** a Practitioner has one active PPL with `PRM_PractitionerRole__c` = 'Specialist'  
**When** the system recalculates the Account role  
**Then** `Account.PRM_ProviderRole__c` = 'Specialist'

### AC-3: Multiple PPLs with Mixed Roles → Dual
**Given** a Practitioner has PPL at Location A with role = 'PCP' AND PPL at Location B with role = 'Specialist'  
**When** the system recalculates the Account role  
**Then** `Account.PRM_ProviderRole__c` = 'Dual'

### AC-4: Multiple PPLs with Same Role
**Given** a Practitioner has PPL at Location A with role = 'PCP' AND PPL at Location B with role = 'PCP'  
**When** the system recalculates the Account role  
**Then** `Account.PRM_ProviderRole__c` = 'PCP'

### AC-5: PPL with Dual + Another PPL
**Given** a Practitioner has PPL at Location A with role = 'Dual' AND PPL at Location B with role = 'PCP'  
**When** the system recalculates the Account role  
**Then** `Account.PRM_ProviderRole__c` = 'Dual' (Dual already covers both)

### AC-6: PPL Termination – Dual Reduces to PCP
**Given** a Practitioner is 'Dual' (PCP at Location A + Specialist at Location B)  
**When** Location B's PPL is terminated (status changed to Inactive/Terminated)  
**Then** `Account.PRM_ProviderRole__c` = 'PCP' (recalculated from remaining active PPLs)

### AC-7: PPL Termination – Dual Reduces to Specialist
**Given** a Practitioner is 'Dual' (PCP at Location A + Specialist at Location B)  
**When** Location A's PPL is terminated  
**Then** `Account.PRM_ProviderRole__c` = 'Specialist'

### AC-8: All PPLs Terminated → Blank
**Given** a Practitioner has all PPLs terminated/inactive  
**When** the last active PPL is terminated  
**Then** `Account.PRM_ProviderRole__c` = '' (blank/null)

### AC-9: New PPL Activated
**Given** a Practitioner currently has `PRM_ProviderRole__c` = 'PCP'  
**When** a new PPL is created/activated with role = 'Specialist'  
**Then** `Account.PRM_ProviderRole__c` = 'Dual'

### AC-10: PPL Role Updated (Downstream from HFN Change)
**Given** a Practitioner has PPL at Location A with role = 'PCP' (Account = 'PCP')  
**When** PPL's `PRM_PractitionerRole__c` is updated to 'Dual' (due to new HFN record)  
**Then** `Account.PRM_ProviderRole__c` = 'Dual'

### AC-11: Bulk Operations
**Given** 200+ PPL records are updated in a single transaction (mass termination)  
**When** the trigger processes all records  
**Then** all affected Account records are correctly recalculated without hitting governor limits

### AC-12: Concierge Rollup Coordination
**Given** a PPL change triggers both practitioner role rollup AND Concierge Provider rollup  
**When** both processes execute  
**Then** the Account `PRM_ProviderRole__c` is updated BEFORE the Concierge rollup evaluates it (to ensure Concierge validation uses the correct role)

---

## Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E1 | PPL has `PRM_PractitionerRole__c` = blank/null | Exclude from aggregation (treat as no role) |
| E2 | PPL with role but status is null (not explicitly Active) | Only include PPLs with explicitly Active status |
| E3 | Practitioner has PPLs but none have roles assigned yet | Account role = blank |
| E4 | Same-day: PPL created and terminated in same transaction | Final state should reflect termination (blank if last) |
| E5 | PPL record deleted (not terminated) | Trigger on delete should also recalculate Account role |
| E6 | PPL moved to different Practitioner (reparented) | Both old and new Practitioner Accounts should be recalculated |
| E7 | Recursion: PPL update → Account update → (should NOT re-fire PPL trigger) | Implement recursion guard with static Set<Id> of processed Account IDs |
| E8 | PPL with RecordType other than PRM affiliation | Only consider PPLs with `RecordTypeId = PRM_GlobalConstant.RECTYPEID_PLAFFILIATION` |

---

## Technical Implementation Design

### Architecture

```
PPL Trigger (PRM_HCPFTrigger)
  → PRM_HCPFTriggerHelper.handlePractitionerRoleRollup()
    → PRM_PracLocNetworkAutomationService.updatePractitionerRoleForAccounts(Set<Id> practitionerAccountIds)
      → Query all active PPLs for those Accounts
      → Aggregate roles (PCP + Specialist = Dual)
      → Update Account.PRM_ProviderRole__c
      → [Then] Concierge rollup can proceed with correct data
```

### New Service Method

**Class:** `PRM_PracLocNetworkAutomationService`  
**Method:** `updatePractitionerRoleForAccounts(Set<Id> practitionerAccountIds)`

```apex
public List<Account> updatePractitionerRoleForAccounts(Set<Id> practitionerAccountIds) {
    // 1. Query active PPLs for the given practitioner Account IDs
    List<HealthcarePractitionerFacility> activePPLs = [
        SELECT Id, PractitionerId, PRM_PractitionerRole__c
        FROM HealthcarePractitionerFacility
        WHERE PractitionerId IN :practitionerAccountIds
          AND IsActive = true  // or Status = 'Active' - verify field
          AND RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PLAFFILIATION
          AND PRM_PractitionerRole__c != null
          AND PRM_PractitionerRole__c != ''
    ];

    // 2. Aggregate roles per Account
    Map<Id, Set<String>> accountRolesMap = new Map<Id, Set<String>>();
    for (Id accId : practitionerAccountIds) {
        accountRolesMap.put(accId, new Set<String>());
    }
    for (HealthcarePractitionerFacility ppl : activePPLs) {
        Set<String> roles = accountRolesMap.get(ppl.PractitionerId);
        String pplRole = ppl.PRM_PractitionerRole__c;
        if (pplRole == 'Dual') {
            roles.add('PCP');
            roles.add('Specialist');
        } else {
            roles.add(pplRole);
        }
    }

    // 3. Determine Account-level role
    List<Account> accountsToUpdate = new List<Account>();
    for (Id accId : practitionerAccountIds) {
        Set<String> roles = accountRolesMap.get(accId);
        String accountRole;
        if (roles.contains('PCP') && roles.contains('Specialist')) {
            accountRole = 'Dual';
        } else if (roles.contains('PCP')) {
            accountRole = 'PCP';
        } else if (roles.contains('Specialist')) {
            accountRole = 'Specialist';
        } else {
            accountRole = '';
        }
        accountsToUpdate.add(new Account(Id = accId, PRM_ProviderRole__c = accountRole));
    }

    // 4. DML update
    if (!accountsToUpdate.isEmpty()) {
        update accountsToUpdate;
    }
    return accountsToUpdate;
}
```

### Trigger Helper Integration

**Class:** `PRM_HCPFTriggerHelper`  
**New Method:** `handlePractitionerRoleRollup()`

```apex
// Static recursion guard
private static Set<Id> processedPractitionerIds = new Set<Id>();

public void handlePractitionerRoleRollup(
    List<HealthcarePractitionerFacility> newList,
    Map<Id, HealthcarePractitionerFacility> oldMap,
    System.TriggerOperation operationType
) {
    Set<Id> practitionerIdsToRecalculate = new Set<Id>();

    for (HealthcarePractitionerFacility ppl : newList) {
        HealthcarePractitionerFacility oldPPL = oldMap != null ? oldMap.get(ppl.Id) : null;

        Boolean shouldRecalculate = false;

        switch on operationType {
            when AFTER_INSERT {
                shouldRecalculate = (ppl.IsActive == true && ppl.PRM_PractitionerRole__c != null);
            }
            when AFTER_UPDATE {
                shouldRecalculate = (
                    ppl.PRM_PractitionerRole__c != oldPPL.PRM_PractitionerRole__c ||
                    ppl.IsActive != oldPPL.IsActive ||
                    ppl.PractitionerId != oldPPL.PractitionerId
                );
            }
            when AFTER_DELETE {
                shouldRecalculate = true;
            }
        }

        if (shouldRecalculate) {
            Id practId = (operationType == System.TriggerOperation.AFTER_DELETE)
                ? oldPPL.PractitionerId : ppl.PractitionerId;

            if (!processedPractitionerIds.contains(practId)) {
                practitionerIdsToRecalculate.add(practId);
            }

            // Handle reparenting: recalculate old practitioner too
            if (operationType == System.TriggerOperation.AFTER_UPDATE
                && ppl.PractitionerId != oldPPL.PractitionerId) {
                practitionerIdsToRecalculate.add(oldPPL.PractitionerId);
            }
        }
    }

    if (!practitionerIdsToRecalculate.isEmpty()) {
        processedPractitionerIds.addAll(practitionerIdsToRecalculate);
        new PRM_PracLocNetworkAutomationService()
            .updatePractitionerRoleForAccounts(practitionerIdsToRecalculate);
    }
}
```

### Execution Order in Trigger

```
PRM_HCPFTrigger (AFTER INSERT/UPDATE/DELETE):
  1. handlePractitionerRoleRollup()     ← NEW (synchronous, updates Account)
  2. handleConciergeRollup()            ← EXISTING (enqueues Queueable, reads Account role)
```

This ordering ensures the Concierge rollup always sees the latest `PRM_ProviderRole__c` value.

---

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| `PRM_PracLocNetworkAutomationService` | Existing class | Add new method alongside existing `updatePracitionerRoleForPPL()` |
| `PRM_HCPFTriggerHelper` | Existing class | Add new handler method, adjust execution order |
| `PRM_HCPFTrigger` | Existing trigger | May need to pass additional context (old map for delete) |
| `PRM_GlobalConstant` | Existing class | RecordType IDs for filtering |
| `PRM_ConciergeProviderRollupQueueable` | Downstream dependency | Must execute AFTER this rollup |
| Termination Cascade Logic | Integration point | Must be called during PPL termination cascade |
| Data Migration (separate story) | Prerequisite | One-time batch to backfill existing Account roles |

---

## Effort Estimation

| Component | Estimate |
|-----------|----------|
| Service method (`updatePractitionerRoleForAccounts`) | 3 hours |
| Trigger helper integration (`handlePractitionerRoleRollup`) | 3 hours |
| Recursion guard + execution order coordination | 2 hours |
| Unit tests (all ACs + edge cases) | 4 hours |
| Integration testing with Concierge rollup | 2 hours |
| Code review + refinement | 2 hours |
| **Total** | **~16 hours (8 story points)** |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Governor limits on bulk PPL updates | DML/SOQL limits exceeded | Single query per transaction, map-based aggregation, single DML |
| Race condition with Concierge rollup | Concierge validates wrong role | Synchronous execution order (role first, then Concierge queueable) |
| Infinite recursion (Account update triggers something that updates PPL) | Stack overflow | Static Set<Id> recursion guard |
| Trigger order of execution conflicts | Unpredictable behavior | Explicit method ordering in trigger helper |
| Existing data out of sync | Incorrect roles on existing Accounts | Separate data migration story (batch job) |

---

## Test Scenarios

### Unit Tests

| # | Test | Assertion |
|---|------|-----------|
| T1 | Insert 1 active PPL (PCP) | Account role = 'PCP' |
| T2 | Insert 1 active PPL (Specialist) | Account role = 'Specialist' |
| T3 | Insert 2 active PPLs (PCP + Specialist) | Account role = 'Dual' |
| T4 | Insert 2 active PPLs (PCP + PCP) | Account role = 'PCP' |
| T5 | Insert PPL with role 'Dual' | Account role = 'Dual' |
| T6 | Terminate 1 of 2 PPLs (PCP remains) | Account role = 'PCP' |
| T7 | Terminate 1 of 2 PPLs (Specialist remains) | Account role = 'Specialist' |
| T8 | Terminate all PPLs | Account role = '' |
| T9 | Activate new PPL (Specialist) on PCP practitioner | Account role = 'Dual' |
| T10 | Update PPL role from PCP to Specialist | Account role updated accordingly |
| T11 | Delete PPL record | Account role recalculated |
| T12 | Bulk: 200 PPLs across 50 Accounts | All Accounts correctly updated, no governor limit errors |
| T13 | PPL with blank role | Excluded from aggregation |
| T14 | Non-PRM RecordType PPL | Excluded from aggregation |
| T15 | Reparent PPL to different Practitioner | Both old and new Accounts recalculated |

### Integration Tests

| # | Test | Assertion |
|---|------|-----------|
| IT1 | HFN change → PPL role update → Account role update | Full cascade works end-to-end |
| IT2 | PPL termination → Account role updated → Concierge rollup uses new role | Concierge validation passes/fails based on correct Account role |
| IT3 | Mass termination via termination cascade | All affected Accounts recalculated |

---

## QTA Test Bridge Prompt

```
Test the Practitioner Role Rollup from PPL to Person Account:

SCENARIO 1: Dual Role Assignment
1. Navigate to a Practitioner Person Account
2. Verify the practitioner has 2 active PPLs (one PCP, one Specialist)
3. Validate Account.PRM_ProviderRole__c = 'Dual'

SCENARIO 2: PPL Termination Reduces to Single Role
1. Navigate to a Practitioner with Dual role
2. Terminate the Specialist PPL (change status to Terminated)
3. Return to the Practitioner Account record
4. Validate Account.PRM_ProviderRole__c = 'PCP'

SCENARIO 3: New PPL Activation Creates Dual
1. Navigate to a Practitioner with PCP role
2. Create a new PPL at a different Practice Location
3. Assign Specialist network role to the new PPL
4. Return to the Practitioner Account record
5. Validate Account.PRM_ProviderRole__c = 'Dual'

SCENARIO 4: All PPLs Terminated
1. Navigate to a Practitioner with one active PPL
2. Terminate the last remaining PPL
3. Return to the Practitioner Account record
4. Validate Account.PRM_ProviderRole__c = '' (blank)

Test Data Requirements:
- Person Account with RecordType = Practitioner
- HealthcareFacility (Practice Location) records
- HealthcarePractitionerFacility records with RecordType = PRM affiliation
- HealthcareFacilityNetwork records with PRM_PractitionerRole__c values
```

---

## Definition of Done

- [ ] `updatePractitionerRoleForAccounts()` method implemented and passing all unit tests
- [ ] `handlePractitionerRoleRollup()` integrated into `PRM_HCPFTriggerHelper`
- [ ] Execution order verified (role rollup before Concierge rollup)
- [ ] Recursion guard tested
- [ ] Bulk test with 200+ records passing
- [ ] Integration test with HFN → PPL → Account cascade passing
- [ ] Code review approved
- [ ] Deployed to QA environment
- [ ] QTA automated tests passing
- [ ] Data migration story created for backfill (separate story)
