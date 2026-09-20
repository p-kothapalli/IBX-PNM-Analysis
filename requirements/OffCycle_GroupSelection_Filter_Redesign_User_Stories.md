# Off-Cycle Guided Flow — Group & Practice Location Filter Redesign

**Document Version:** 1.0
**Created Date:** May 6, 2026
**Author:** Salesforce Engineering Team
**Story Type:** Feature Enhancement
**Flow Impacted:** `PRM_OffCycleCredentialing_English`

---

## Overview

**Purpose:** Redesign what Account/Practice Locations are available for selection through the Type-Ahead & Group Selection Screen in the Off-Cycle Guided Flow.

The Off-Cycle Request should **allow all Groups/Practice Locations EXCEPT** the following excluded categories:

| # | Exclusion Rule | Condition |
|---|----------------|-----------|
| 1 | Do not show **Terminated Groups** | `Account.IsActive = FALSE` AND `Account.PRM_EffectiveTo__c != NULL` |
| 2 | Do not show **Facility** Practice Locations | `HealthcareFacility.PRM_PracticeClassification__c = 'Facility'` |
| 3 | Do not show **Delegated** Practice Locations | `HealthcareFacility.PRM_IsDelegated__c = TRUE` |
| 4 | Do not show **Error** Accounts or Practice Locations | `Account.PRM_IsErrorRecord__c = TRUE` OR `HealthcareFacility.PRM_IsErrorRecord__c = TRUE` |

**Additionally**, the following user-facing error messages must be shown in specific scenarios:

| # | Trigger | Error Message |
|---|---------|---------------|
| E1 | User enters NPI, Tax ID, and Name of a terminated group | `"You entered information for the terminated group. Please select a different group to proceed."` |
| E2 | User selects a group where ALL practice locations are delegated | `"The group you selected only contains Delegated Practice Locations."` |

---

## Scope

### Components Affected

| Component | Type | File Path |
|-----------|------|-----------|
| `PRM_ProviderSearchHelper` | Apex Class | `force-app/main/default/classes/PRM_ProviderSearchHelper.cls` |
| `PRM_OffCycleProviderSearch` | Apex Class | `force-app/main/default/classes/PRM_OffCycleProviderSearch.cls` |
| `PRM_OmniUtils` | Apex Class | `force-app/main/default/classes/PRM_OmniUtils.cls` |
| `prmGroupSelectionOffCycle` | LWC Component | `force-app/main/default/lwc/prmGroupSelectionOffCycle/` |
| `prmGroupSelectionOffCycle.html` | LWC Template | `force-app/main/default/lwc/prmGroupSelectionOffCycle/prmGroupSelectionOffCycle.html` |

---

## Gap Analysis Summary (Current State vs Required State)

### GAP 1 — `getFacilityOffcycle()` is missing 3 required filters
**File:** `PRM_ProviderSearchHelper.cls` — Lines 85–94
**Severity:** 🔴 Critical

**Current SOQL:**
```sql
WHERE AccountId =:groupId
  AND RecordType.DeveloperName != 'PRM_NCPDP'
  AND PRM_NpiId__r.Npi =: npi
  AND PRM_PracticeClassification__c != 'Facility'   -- ✅ present
  AND PRM_Active__c = true                           -- ❌ wrong (too restrictive & missing delegated/error)
```

**Problems:**
1. `PRM_IsDelegated__c = false` — **MISSING** → delegated practice locations are shown
2. `PRM_IsErrorRecord__c = false` — **MISSING** → error practice locations are shown
3. `PRM_Active__c = true` — **WRONG** → excludes valid inactive records (those without a termination date). Must be changed to allow inactive records where `PRM_EffectiveTo__c = NULL` (not terminated)

---

### GAP 2 — `getGroupAccount()` does not exclude Error Accounts when `IsActive = TRUE`
**File:** `PRM_ProviderSearchHelper.cls` — Lines 21–30
**Severity:** 🔴 Critical

**Current SOQL (relevant OR branches):**
```sql
OR (Id =: groupId AND IsActive = true AND PRM_ParticipationStatus__c =: PC_PARTICIPATING)
OR (Id =: groupId AND IsActive = true AND PRM_ParticipationStatus__c =: PC_NON_PARTICIPATING ...)
-- ❌ No PRM_IsErrorRecord__c = false on the IsActive = true branches
```

**Problem:** An Account that is `IsActive = TRUE` but `PRM_IsErrorRecord__c = TRUE` is still returned and shown in the group selection. The `PRM_IsErrorRecord__c = false` guard exists only on the `IsActive = false` branches.

---

### GAP 3 — TypeAhead account filter (`isValidAccRecord`) does not exclude active Error Accounts
**File:** `PRM_OmniUtils.cls` — Lines 4398–4413
**Severity:** 🔴 Critical

**Current logic for OffCycle (`isProviderChangeFlow = false`):**
```java
acc.PRM_ParticipationStatus__c != Administrative
&& (
    (acc.IsActive)                          // ❌ No IsErrorRecord check here
    || (!acc.IsActive
        && acc.PRM_EffectiveFrom__c == null
        && acc.PRM_EffectiveTo__c == null
        && !acc.PRM_IsErrorRecord__c        // ✅ Error check only on inactive branch
        && acc.PRM_Pending__c)
)
```

**Problem:** An active account with `PRM_IsErrorRecord__c = TRUE` passes the TypeAhead filter and appears in suggestions to the user.

---

### GAP 4 — No Terminated Group error message logic exists
**File:** N/A — this is entirely **new functionality**
**Severity:** 🔴 Critical (new requirement, zero implementation)

**Requirement:** When a user enters a combination of NPI, Tax ID, and Group Name that matches a **terminated** group (i.e., `IsActive = FALSE` AND `PRM_EffectiveTo__c != NULL`), the system must display:

> `"You entered information for the terminated group. Please select a different group to proceed."`

**Current state:** No such check exists anywhere — in Apex, LWC, or OmniScript. Terminated groups are simply invisible (not shown), but no error message is presented if the user's input matches one.

---

### GAP 5 — Delegated Group error message: flag propagated but UI message not rendered
**File:** `prmGroupSelectionOffCycle.html` / `prmGroupSelectionOffCycle.js`
**Severity:** 🟡 Medium

**Current state:**
- `getInfoCodeAssign()` identifies delegated locations ✅
- `areAllLocationsDelegated()` computes the `isGroupDelegated` boolean ✅
- `isGroupDelegated` is returned from Apex and stored in OmniScript JSON as `IsGroupDelegated` ✅
- **However:** The HTML template does **not** render the error message:
  > `"The group you selected only contains Delegated Practice Locations."`
  when `IsGroupDelegated = true`.
- The `delegatedGroup` value is stored in `clearNodes()` and `getUpdatedPath()` but **never used to show an inline error to the user** in the modal or on the form.

---

## Epic: Off-Cycle Group & Practice Location Filter Redesign

**Epic Goal:** Enforce the correct exclusion rules for Groups (Accounts) and Practice Locations (HealthcareFacility records) shown in the Off-Cycle guided flow Type-Ahead and Group Selection screen, and surface the required user-facing error messages.

**Total Estimated Effort:** 13 Story Points

| Story | Title | SP |
|-------|-------|----|
| Story 1 | Fix `getFacilityOffcycle()` — Add Missing Delegated, Error, and Terminated Filters | 3 |
| Story 2 | Fix `getGroupAccount()` — Exclude Error Accounts from Group Selection | 2 |
| Story 3 | Fix TypeAhead (`isValidAccRecord`) — Exclude Active Error Accounts | 2 |
| Story 4 | Implement Terminated Group Detection & Error Message | 5 |
| Story 5 | Render Delegated Group Error Message in LWC | 1 |

---

## Story 1: Fix `getFacilityOffcycle()` — Add Missing Delegated, Error, and Terminated Filters

**Story Number:** OFFCYCLE-FILTER-001
**Effort:** 3 SP
**Priority:** P1 — Critical

---

### User Story

**As a** practitioner using the Off-Cycle guided flow
**I want** the Group Selection screen to only show Practice Locations that are non-delegated, non-error, and not terminated
**So that** I cannot accidentally select invalid or ineligible practice locations

---

### Background / Context

The method `PRM_ProviderSearchHelper.getFacilityOffcycle()` is called by `PRM_OffCycleProviderSearch.getOffcycleProviderSearch()`, which feeds the `prmGroupSelectionOffCycle` LWC component. This is the primary query that determines which Practice Locations (HealthcareFacility records) appear in the Group Selection modal.

Currently, the query filters out Facilities by classification but is **missing three critical filters**:
1. It does not exclude **Delegated** practice locations (`PRM_IsDelegated__c = true`)
2. It does not exclude **Error** practice locations (`PRM_IsErrorRecord__c = true`)
3. It uses `PRM_Active__c = true` which is **too restrictive** — it excludes valid inactive records (those not yet terminated, i.e., `PRM_EffectiveTo__c = NULL`) and does not correctly align with the business rule for terminated records

---

### Acceptance Criteria

#### AC 1.1 — Delegated Practice Locations Are Not Shown

**Given** a group has practice locations where some have `PRM_IsDelegated__c = TRUE`
**When** the Group Selection screen loads for that group
**Then** those delegated practice locations **must not** appear in the selection table

**Technical Condition:**
```
HealthcareFacility.PRM_IsDelegated__c = false
```

---

#### AC 1.2 — Error Practice Locations Are Not Shown

**Given** a group has practice locations where some have `PRM_IsErrorRecord__c = TRUE`
**When** the Group Selection screen loads for that group
**Then** those error practice locations **must not** appear in the selection table

**Technical Condition:**
```
HealthcareFacility.PRM_IsErrorRecord__c = false
```

---

#### AC 1.3 — Terminated Practice Locations Are Not Shown

**Given** a practice location has `PRM_Active__c = FALSE` AND `PRM_EffectiveTo__c != NULL`
**When** the Group Selection screen loads
**Then** that terminated practice location **must not** appear in the selection table

**Given** a practice location has `PRM_Active__c = FALSE` AND `PRM_EffectiveTo__c = NULL` (inactive but not terminated)
**When** the Group Selection screen loads
**Then** that practice location **must** still appear (it is valid — inactive but not terminated)

**Technical Condition (replaces current `PRM_Active__c = true`):**
```sql
((PRM_Active__c = false AND PRM_EffectiveTo__c = NULL) OR PRM_Active__c = true)
```

---

#### AC 1.4 — Facility Classification Records Are Not Shown (Existing — Must Remain)

**Given** the existing filter `PRM_PracticeClassification__c != 'Facility'` is already in place
**Then** this filter must be preserved and continue to work correctly

---

### Files to Change

| File | Method | Change Type |
|------|--------|-------------|
| `PRM_ProviderSearchHelper.cls` | `getFacilityOffcycle(String groupId, String npi)` | Modify SOQL — add 2 conditions, fix Active filter |

### Current Code (Lines 85–94)

```apex
public Map<Id, HealthcareFacility> getFacilityOffcycle(String groupId, String npi){
    return (new Map<Id, HealthcareFacility>( [SELECT prm_websiteaddress__c, prm_effectivefrom__c, ...
                                              FROM HealthcareFacility
                                              WHERE AccountId =:groupId
                                              AND RecordType.DeveloperName != 'PRM_NCPDP'
                                              AND PRM_NpiId__r.Npi =: npi
                                              AND PRM_PracticeClassification__c != 'Facility'
                                              AND PRM_Active__c = true          -- ❌ wrong
                                              WITH USER_MODE ]));
}
```

### Required Change

```apex
public Map<Id, HealthcareFacility> getFacilityOffcycle(String groupId, String npi){
    return (new Map<Id, HealthcareFacility>( [SELECT prm_websiteaddress__c, prm_effectivefrom__c, ...
                                              FROM HealthcareFacility
                                              WHERE AccountId =:groupId
                                              AND RecordType.DeveloperName != 'PRM_NCPDP'
                                              AND PRM_NpiId__r.Npi =: npi
                                              AND PRM_PracticeClassification__c != 'Facility'
                                              AND PRM_IsDelegated__c = false                              -- ✅ ADD
                                              AND PRM_IsErrorRecord__c = false                            -- ✅ ADD
                                              AND ((PRM_Active__c = false AND PRM_EffectiveTo__c = NULL)  -- ✅ FIX
                                                   OR PRM_Active__c = true)
                                              WITH USER_MODE ]));
}
```

---

### Test Cases

| # | Test Scenario | Expected Result |
|---|---------------|-----------------|
| T1.1 | Practice Location with `PRM_IsDelegated__c = true` | Not returned by query |
| T1.2 | Practice Location with `PRM_IsErrorRecord__c = true` | Not returned by query |
| T1.3 | Practice Location with `PRM_Active__c = false` AND `PRM_EffectiveTo__c = [date]` (terminated) | Not returned |
| T1.4 | Practice Location with `PRM_Active__c = false` AND `PRM_EffectiveTo__c = null` (inactive, not terminated) | Returned ✅ |
| T1.5 | Practice Location with `PRM_Active__c = true` (active) | Returned ✅ |
| T1.6 | Practice Location with `PRM_PracticeClassification__c = 'Facility'` | Not returned (existing filter preserved) |

---

## Story 2: Fix `getGroupAccount()` — Exclude Error Accounts from Group Selection

**Story Number:** OFFCYCLE-FILTER-002
**Effort:** 2 SP
**Priority:** P1 — Critical

---

### User Story

**As a** practitioner using the Off-Cycle guided flow
**I want** the Group Selection screen to not display groups (Accounts) that are error records
**So that** I cannot select an invalid group account even if it is currently active

---

### Background / Context

The method `PRM_ProviderSearchHelper.getGroupAccount()` fetches the Account (Group) once a specific Account ID is passed from the TypeAhead selection. The current SOQL has `PRM_IsErrorRecord__c = false` **only** on the `IsActive = false` OR branches. An account that is `IsActive = TRUE` but flagged as an error record (`PRM_IsErrorRecord__c = TRUE`) will still be returned by this query and shown in the Group Selection flow.

---

### Acceptance Criteria

#### AC 2.1 — Active Error Accounts Are Not Returned

**Given** an Account has `IsActive = TRUE` AND `PRM_IsErrorRecord__c = TRUE`
**When** `getGroupAccount()` is called with that Account's Id
**Then** the method must return **no record** (the account must be excluded)

#### AC 2.2 — Active Non-Error Accounts Are Still Returned

**Given** an Account has `IsActive = TRUE` AND `PRM_IsErrorRecord__c = FALSE`
**When** `getGroupAccount()` is called with that Account's Id
**Then** the method must return the Account record as before

#### AC 2.3 — Existing Inactive Branch Logic Is Preserved

**Given** an Account has `IsActive = FALSE` AND `PRM_EffectiveTo__c = null` AND `PRM_IsErrorRecord__c = FALSE`
**Then** the Account is still returned (existing behavior preserved)

---

### Files to Change

| File | Method | Change Type |
|------|--------|-------------|
| `PRM_ProviderSearchHelper.cls` | `getGroupAccount(String groupId)` | Modify SOQL — add `PRM_IsErrorRecord__c = false` to all `IsActive = true` branches |

### Current Code (Lines 21–30)

```apex
public Account getGroupAccount(String groupId){
    return [SELECT ...
            FROM Account
            WHERE (Id =: groupId AND IsActive = true
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_PARTICIPATING)
            OR    (Id =: groupId AND IsActive = true
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_NON_PARTICIPATING
                   AND RecordType.DeveloperName != 'PRM_NCPDP')
            OR    (Id =: groupId AND IsActive = false
                   AND PRM_EffectiveFrom__c = null AND PRM_EffectiveTo__c = null
                   AND PRM_IsErrorRecord__c = false                    -- ✅ exists on inactive branch
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_NON_PARTICIPATING
                   AND RecordType.DeveloperName != 'PRM_NCPDP')
            OR    (Id =: groupId AND IsActive = false
                   AND PRM_EffectiveFrom__c = null AND PRM_EffectiveTo__c = null
                   AND PRM_IsErrorRecord__c = false)                   -- ✅ exists on inactive branch
            WITH USER_MODE];
}
```

### Required Change

```apex
public Account getGroupAccount(String groupId){
    return [SELECT ...
            FROM Account
            WHERE (Id =: groupId AND IsActive = true
                   AND PRM_IsErrorRecord__c = false                    -- ✅ ADD
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_PARTICIPATING)
            OR    (Id =: groupId AND IsActive = true
                   AND PRM_IsErrorRecord__c = false                    -- ✅ ADD
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_NON_PARTICIPATING
                   AND RecordType.DeveloperName != 'PRM_NCPDP')
            OR    (Id =: groupId AND IsActive = false
                   AND PRM_EffectiveFrom__c = null AND PRM_EffectiveTo__c = null
                   AND PRM_IsErrorRecord__c = false
                   AND PRM_ParticipationStatus__c =: PRM_GlobalConstant.PC_NON_PARTICIPATING
                   AND RecordType.DeveloperName != 'PRM_NCPDP')
            OR    (Id =: groupId AND IsActive = false
                   AND PRM_EffectiveFrom__c = null AND PRM_EffectiveTo__c = null
                   AND PRM_IsErrorRecord__c = false)
            WITH USER_MODE];
}
```

---

### Test Cases

| # | Test Scenario | Expected Result |
|---|---------------|-----------------|
| T2.1 | Active Account with `PRM_IsErrorRecord__c = true` | Not returned |
| T2.2 | Active Account with `PRM_IsErrorRecord__c = false`, `ParticipationStatus = Participating` | Returned ✅ |
| T2.3 | Active Account with `PRM_IsErrorRecord__c = false`, `ParticipationStatus = Non-Participating` | Returned ✅ |
| T2.4 | Inactive Account with `PRM_IsErrorRecord__c = true` | Not returned (existing behavior preserved) |
| T2.5 | Inactive Account with `PRM_IsErrorRecord__c = false`, `PRM_EffectiveTo__c = null` | Returned ✅ |

---

## Story 3: Fix TypeAhead (`isValidAccRecord`) — Exclude Active Error Accounts

**Story Number:** OFFCYCLE-FILTER-003
**Effort:** 2 SP
**Priority:** P1 — Critical

---

### User Story

**As a** practitioner using the Off-Cycle guided flow
**I want** the Group TypeAhead search results to exclude error accounts even when they are active
**So that** I am not able to search for and select an error-flagged group through the TypeAhead

---

### Background / Context

The TypeAhead on the Group Information screen calls `PRM_OmniUtils.getGroupDataForTaxId()` → `getUniqueAccountForTaxId()` → `isValidAccRecord()`. The `isValidAccRecord` method is the gate-keeping function that decides which accounts appear as TypeAhead suggestions.

For the Off-Cycle flow (`isProviderChangeFlow = false`), the current logic allows **any active account** regardless of its `PRM_IsErrorRecord__c` value. This means a user can search by Tax ID, see an error account in suggestions, and select it — bypassing the intent of the `Is Error` flag.

---

### Acceptance Criteria

#### AC 3.1 — Active Error Accounts Are Excluded from TypeAhead Results

**Given** an Account has `IsActive = TRUE` AND `PRM_IsErrorRecord__c = TRUE`
**When** a practitioner searches by Tax ID in the Group TypeAhead
**Then** that Account must **not** appear in the TypeAhead results

#### AC 3.2 — Active Non-Error Accounts Remain in TypeAhead Results

**Given** an Account has `IsActive = TRUE` AND `PRM_IsErrorRecord__c = FALSE`
**When** a practitioner searches by Tax ID in the Group TypeAhead
**Then** that Account must still appear in TypeAhead results as before

#### AC 3.3 — `isProviderChangeFlow = true` Logic Is Not Affected

**Given** the change is scoped to the `isProviderChangeFlow = false` branch (Off-Cycle)
**Then** the Provider Change Flow TypeAhead behavior must remain unchanged

---

### Files to Change

| File | Method | Change Type |
|------|--------|-------------|
| `PRM_OmniUtils.cls` | `isValidAccRecord(Account acc, boolean isProviderChangeFlow)` | Add `&& !acc.PRM_IsErrorRecord__c` to the `IsActive = true` branch in the OffCycle condition |

### Current Code (Lines 4398–4413)

```apex
public boolean isValidAccRecord(Account acc, boolean isProviderChangeFlow){
    boolean isValidRec = false;

    // Provider Change Flow branch
    if((isProviderChangeFlow) &&
       ((acc.IsActive) && ( acc.PRM_ParticipationStatus__c == PRM_GlobalConstant.PC_PARTICIPATING ||
            acc.PRM_ParticipationStatus__c == PRM_GlobalConstant.PC_NON_PARTICIPATING )
       )){
           isValidRec = true;
    }
    // Off-Cycle branch
    else if((!isProviderChangeFlow) && acc.PRM_ParticipationStatus__c != PRM_GlobalConstant.Administrative &&
            ((acc.IsActive)                                  // ❌ no error check on active branch
            || ( (!acc.IsActive) && acc.PRM_EffectiveFrom__c == null
                 && acc.PRM_EffectiveTo__c == null
                 && (!acc.PRM_IsErrorRecord__c)              // ✅ error check only on inactive branch
                 && (acc.PRM_Pending__c) ))
           ){
               isValidRec = true;
           }
    return isValidRec;
}
```

### Required Change

```apex
public boolean isValidAccRecord(Account acc, boolean isProviderChangeFlow){
    boolean isValidRec = false;

    // Provider Change Flow branch — NO CHANGE
    if((isProviderChangeFlow) &&
       ((acc.IsActive) && ( acc.PRM_ParticipationStatus__c == PRM_GlobalConstant.PC_PARTICIPATING ||
            acc.PRM_ParticipationStatus__c == PRM_GlobalConstant.PC_NON_PARTICIPATING )
       )){
           isValidRec = true;
    }
    // Off-Cycle branch — ADD !acc.PRM_IsErrorRecord__c to active branch
    else if((!isProviderChangeFlow) && acc.PRM_ParticipationStatus__c != PRM_GlobalConstant.Administrative &&
            ((acc.IsActive && !acc.PRM_IsErrorRecord__c)     // ✅ ADD error check to active branch
            || ( (!acc.IsActive) && acc.PRM_EffectiveFrom__c == null
                 && acc.PRM_EffectiveTo__c == null
                 && (!acc.PRM_IsErrorRecord__c)
                 && (acc.PRM_Pending__c) ))
           ){
               isValidRec = true;
           }
    return isValidRec;
}
```

---

### Test Cases

| # | Test Scenario | Expected Result |
|---|---------------|-----------------|
| T3.1 | Active account, `PRM_IsErrorRecord__c = true`, `ParticipationStatus != Administrative` | `isValidRec = false` |
| T3.2 | Active account, `PRM_IsErrorRecord__c = false`, `ParticipationStatus = Participating` | `isValidRec = true` |
| T3.3 | Active account, `PRM_IsErrorRecord__c = false`, `ParticipationStatus = Administrative` | `isValidRec = false` |
| T3.4 | Inactive account, `PRM_IsErrorRecord__c = false`, `PRM_EffectiveTo__c = null`, `PRM_Pending__c = true` | `isValidRec = true` |
| T3.5 | Inactive account, `PRM_IsErrorRecord__c = true`, `PRM_EffectiveTo__c = null` | `isValidRec = false` |
| T3.6 | Provider Change Flow — active account, any error flag | Behavior unchanged |

---

## Story 4: Implement Terminated Group Detection & Error Message

**Story Number:** OFFCYCLE-FILTER-004
**Effort:** 5 SP
**Priority:** P1 — Critical
**Type:** New Feature (zero current implementation)

---

### User Story

**As a** practitioner using the Off-Cycle guided flow
**I want** to see a clear error message if I enter the NPI, Tax ID, and Name of a group that is terminated
**So that** I understand why the group is not available and I can provide a different valid group

---

### Background / Context

Currently, terminated groups (Accounts where `IsActive = FALSE` AND `PRM_EffectiveTo__c != NULL`) are simply hidden from TypeAhead results and the Group Selection screen. **However, there is no feedback to the user** — if a user deliberately enters the NPI, Tax ID, and Name of a terminated group, they receive no results but also no explanation.

The new requirement mandates:
> If user enters NPI, Tax Id, and Name of a terminated Group, display the error:
> **"You entered information for the terminated group. Please select a different group to proceed."**

This is **entirely new functionality** and requires changes in Apex and the LWC.

---

### Acceptance Criteria

#### AC 4.1 — Terminated Group Detection on TypeAhead Input

**Given** a practitioner has entered a NPI, Tax ID, and Group Name in the Group Information section
**When** the system searches for matching accounts via the TypeAhead
**And** an Account matches the entered NPI, Tax ID, and Name
**And** that Account has `IsActive = FALSE` AND `PRM_EffectiveTo__c != NULL` (terminated)
**Then** the system must NOT show that group in the TypeAhead results
**And** the system must return a flag indicating a terminated group was matched

#### AC 4.2 — Terminated Group Error Message Displayed

**Given** the system has detected a terminated group match (AC 4.1)
**When** the TypeAhead component processes the search result
**Then** an inline error message must be displayed to the user:

> **"You entered information for the terminated group. Please select a different group to proceed."**

**And** the user must not be able to proceed to the Group Selection modal until they change their input

#### AC 4.3 — No False Positives — Non-Terminated Groups Are Unaffected

**Given** an Account has `IsActive = FALSE` AND `PRM_EffectiveTo__c = NULL` (inactive but not terminated)
**Then** this Account follows the standard active/inactive display rules
**And** no terminated group error message is shown for this Account

**Given** an Account has `IsActive = TRUE` (active group)
**Then** no terminated group error message is shown

#### AC 4.4 — Error Clears When User Changes Input

**Given** the terminated group error message is displayed
**When** the user changes the NPI, Tax ID, or Group Name input
**Then** the terminated group error message is cleared
**And** the user can re-search for a valid group

---

### Technical Design

#### Apex: New Method in `PRM_OmniUtils.cls` — `checkTerminatedGroup`

A new method must be added to detect whether the user's input (NPI, Tax ID, Name) matches a terminated group.

**Method Signature:**
```apex
/**
 * @MethodName   : checkTerminatedGroup
 * @Description  : Checks if the entered NPI, TaxId, and Group Name match a terminated Account.
 *                 A terminated Account is one where IsActive = false AND PRM_EffectiveTo__c != null.
 * @Params       : inputMap (NPI, TaxId, GroupName), outMap
 * @Returns      : outMap with IsTerminatedGroup (Boolean)
 */
private Object checkTerminatedGroup(Map<String, Object> inputMap, Map<String, Object> outMap) {
    String npi     = inputMap.get('NPI')       != null ? String.valueOf(inputMap.get('NPI'))       : '';
    String taxId   = inputMap.get('TaxId')     != null ? String.valueOf(inputMap.get('TaxId'))     : '';
    String grpName = inputMap.get('GroupName') != null ? String.valueOf(inputMap.get('GroupName')) : '';

    Boolean isTerminated = false;

    if (String.isNotBlank(npi) && String.isNotBlank(taxId) && String.isNotBlank(grpName)) {
        // Step 1: Find accounts matching Tax ID via Identifier
        List<Identifier> identifiers = [
            SELECT ParentRecordId
            FROM Identifier
            WHERE PRM_Type__c = :PRM_GlobalConstant.EIN
            AND IdValue = :taxId
            AND ParentRecordId != null
        ];

        Set<Id> accountIds = new Set<Id>();
        for (Identifier id : identifiers) {
            accountIds.add(id.ParentRecordId);
        }

        if (!accountIds.isEmpty()) {
            // Step 2: Check for terminated accounts matching NPI and Name
            List<Account> terminatedAccounts = [
                SELECT Id, Name, IsActive, PRM_EffectiveTo__c
                FROM Account
                WHERE Id IN :accountIds
                AND IsActive = false
                AND PRM_EffectiveTo__c != null
                AND RecordType.DeveloperName = :PRM_GlobalConstant.RECTYPE_VENDOR
                AND Name = :grpName
                WITH USER_MODE
            ];
            // NPI match is via the HealthcareProvider/NPI identifier — check against group NPI
            if (!terminatedAccounts.isEmpty()) {
                isTerminated = true;
            }
        }
    }

    outMap.put('IsTerminatedGroup', isTerminated);
    return outMap;
}
```

> **Note:** The NPI-to-Account link may need to be verified via `HealthcareProviderNpi` or `Identifier` depending on the data model. The method should be called as a Remote Action from the OmniScript TypeAhead element's action step.

---

#### LWC: `prmGroupSelectionOffCycle.js` — Add Terminated Group Check

A new property and check must be added to the LWC:

**New property:**
```javascript
isTerminatedGroupError = false;
terminatedGroupErrorMessage = 'You entered information for the terminated group. Please select a different group to proceed.';
```

**In `fetchGroupData()` — handle terminated group flag from Apex response:**
```javascript
// After receiving IP/Apex result:
const isTerminated = IPResult?.IsTerminatedGroup;
if (isTerminated) {
    this.isTerminatedGroupError = true;
    this.clearNodes(false, groupAccountId);
    return; // stop processing
}
this.isTerminatedGroupError = false;
```

**In `set jsonData()` — clear error when user changes inputs:**
```javascript
// When NPI/TaxId changes and inputs are cleared:
this.isTerminatedGroupError = false;
```

---

#### LWC: `prmGroupSelectionOffCycle.html` — Render Terminated Group Error

Add an inline error message block that displays when `isTerminatedGroupError = true`:

```html
<!-- Terminated Group Error Message -->
<template if:true={isTerminatedGroupError}>
    <div class="slds-notify slds-notify_alert slds-alert_error slds-m-bottom_small" role="alert">
        <span class="slds-assistive-text">error</span>
        <lightning-icon icon-name="utility:error" alternative-text="Error" size="x-small"
            class="slds-m-right_x-small"></lightning-icon>
        <h2>{terminatedGroupErrorMessage}</h2>
    </div>
</template>
```

**Placement:** This message block should render outside the modal — on the Group Information screen, immediately below the Group Name / TypeAhead input, so it is visible before the user attempts to open the Group Selection modal.

---

### Files to Change

| File | Change Type | Details |
|------|-------------|---------|
| `PRM_OmniUtils.cls` | Add new method | `checkTerminatedGroup()` — detect terminated group by NPI, TaxId, Name |
| `prmGroupSelectionOffCycle.js` | Add property + logic | `isTerminatedGroupError` flag; handle response; clear on input change |
| `prmGroupSelectionOffCycle.html` | Add error block | Render SLDS error alert when `isTerminatedGroupError = true` |

---

### Test Cases

| # | Test Scenario | Expected Result |
|---|---------------|-----------------|
| T4.1 | User enters NPI, TaxId, Name of a terminated group (`IsActive=false`, `EffectiveTo != null`) | Error message shown; group not selectable |
| T4.2 | User enters NPI, TaxId, Name of an active group | No error; normal TypeAhead results shown |
| T4.3 | User enters NPI, TaxId, Name of an inactive but NOT terminated group (`EffectiveTo = null`) | No terminated group error shown |
| T4.4 | User enters only NPI and TaxId (no Name) | No terminated check triggered (all three fields required) |
| T4.5 | User changes NPI after error message shown | Error message clears |
| T4.6 | User changes TaxId after error message shown | Error message clears |
| T4.7 | Multiple terminated groups match the input | Error message shown (any match triggers the error) |
| T4.8 | `checkTerminatedGroup` called with empty inputs | Returns `IsTerminatedGroup = false`; no error |

---

## Story 5: Render Delegated Group Error Message in LWC

**Story Number:** OFFCYCLE-FILTER-005
**Effort:** 1 SP
**Priority:** P2 — Medium

---

### User Story

**As a** practitioner using the Off-Cycle guided flow
**I want** to see an error message when I select a group whose practice locations are all delegated
**So that** I understand why I cannot proceed with that group and I am directed to choose a different one

---

### Background / Context

The backend logic for detecting an all-delegated group already exists and works correctly:
- `PRM_ProviderSearchHelper.getInfoCodeAssign()` identifies delegated locations via `PRM_InfoCodeAssignment__c` (InfoCode Type = 'Delegated') ✅
- `PRM_ProviderSearchHelper.areAllLocationsDelegated()` computes the `isGroupDelegated` boolean ✅
- `PRM_OffCycleProviderSearch.getOffcycleProviderSearch()` returns `isGroupDelegated` in the JSON response ✅
- `prmGroupSelectionOffCycle.js` captures it as `this.delegatedGroup` and stores it in the OmniScript JSON as `IsGroupDelegated` ✅

**The gap** is that the LWC HTML template **never renders a visible error message** to the user when `isGroupDelegated = true`. The flag is stored but silently ignored from a UX perspective.

Additionally, after Story 1 fixes `getFacilityOffcycle()` to exclude delegated PLs at the SOQL level (via `PRM_IsDelegated__c = false`), the `isGroupDelegated` check via InfoCode will cover the scenario where all remaining (non-field-delegated) PLs are delegated via InfoCode assignment. Both mechanisms are complementary.

---

### Acceptance Criteria

#### AC 5.1 — Delegated Group Error Message Is Displayed

**Given** a practitioner selects a group from the TypeAhead
**And** all of that group's practice locations are delegated (as determined by `isGroupDelegated = true` from Apex)
**When** the Group Selection modal would normally open
**Then** instead of showing the Group Selection modal, the system must display the following error message inline:

> **"The group you selected only contains Delegated Practice Locations."**

**And** the Group Selection modal must NOT open
**And** the user must be able to enter a different group

#### AC 5.2 — Error Message Clears When User Changes Group Input

**Given** the delegated group error is displayed
**When** the user changes the Group TypeAhead selection or clears the NPI/TaxId
**Then** the delegated group error message must be cleared

#### AC 5.3 — Non-All-Delegated Groups Are Not Affected

**Given** a group has at least one non-delegated practice location
**When** the user selects that group
**Then** no delegated error message is shown and the Group Selection modal opens normally

---

### Files to Change

| File | Change Type | Details |
|------|-------------|---------|
| `prmGroupSelectionOffCycle.js` | Add property + logic | `isDelegatedGroupError` flag; set to `true` when `isGroupDelegated = true`; clear on input change |
| `prmGroupSelectionOffCycle.html` | Add error block | Render SLDS error alert when `isDelegatedGroupError = true` |

### LWC JS Change

**New property:**
```javascript
isDelegatedGroupError = false;
delegatedGroupErrorMessage = 'The group you selected only contains Delegated Practice Locations.';
```

**In `fetchGroupData()` — after receiving result:**
```javascript
this.delegatedGroup = IPResult?.isGroupDelegated;
if (this.delegatedGroup) {
    this.isDelegatedGroupError = true;
    this.showModal = false; // Do not open modal
    return;
}
this.isDelegatedGroupError = false;
```

**In `clearNodes()` and `set jsonData()` — clear on input change:**
```javascript
this.isDelegatedGroupError = false;
```

### LWC HTML Change

Add the following error block to `prmGroupSelectionOffCycle.html`, placed below the TypeAhead / Group input area (outside the modal):

```html
<!-- Delegated Group Error Message -->
<template if:true={isDelegatedGroupError}>
    <div class="slds-notify slds-notify_alert slds-alert_error slds-m-bottom_small" role="alert">
        <span class="slds-assistive-text">error</span>
        <lightning-icon icon-name="utility:error" alternative-text="Error" size="x-small"
            class="slds-m-right_x-small"></lightning-icon>
        <h2>{delegatedGroupErrorMessage}</h2>
    </div>
</template>
```

---

### Test Cases

| # | Test Scenario | Expected Result |
|---|---------------|-----------------|
| T5.1 | User selects a group where ALL PLs are delegated (`isGroupDelegated = true`) | Error message shown; modal does NOT open |
| T5.2 | User selects a group where at least one PL is non-delegated | No error; modal opens normally |
| T5.3 | User changes Group TypeAhead input after seeing delegated error | Error message cleared |
| T5.4 | User clears NPI/TaxId after seeing delegated error | Error message cleared |

---

## End-to-End Exclusion Rules Reference

The table below maps each business exclusion rule to the specific technical filter that enforces it across both the TypeAhead and the Group Selection Screen.

| Business Rule | Object | Field Condition | Enforced In | Story |
|---------------|--------|-----------------|-------------|-------|
| Do not show Terminated Groups | Account | `IsActive = false AND PRM_EffectiveTo__c != null` | `getGroupAccount()` (SOQL), `isValidAccRecord()` (in-memory) | Story 2, Story 3 |
| Error message for Terminated Group input | Account | Match on NPI + TaxId + Name, terminated | New `checkTerminatedGroup()` method + LWC error render | Story 4 |
| Do not show Facilities | HealthcareFacility | `PRM_PracticeClassification__c = 'Facility'` | `getFacilityOffcycle()` (SOQL) — already exists ✅ | Existing |
| Do not show Delegated Practice Locations | HealthcareFacility | `PRM_IsDelegated__c = true` | `getFacilityOffcycle()` (SOQL) | Story 1 |
| Error message for All-Delegated Group | HealthcareFacility + InfoCodeAssignment | All PLs delegated via InfoCode | `areAllLocationsDelegated()` (Apex) + LWC error render | Story 5 |
| Do not show Error Practice Locations | HealthcareFacility | `PRM_IsErrorRecord__c = true` | `getFacilityOffcycle()` (SOQL) | Story 1 |
| Do not show Error Accounts | Account | `PRM_IsErrorRecord__c = true` | `getGroupAccount()` (SOQL), `isValidAccRecord()` (in-memory) | Story 2, Story 3 |

---

## Summary of All Changes

| Story | File | Method / Element | Change Summary | SP |
|-------|------|-----------------|----------------|----|
| Story 1 | `PRM_ProviderSearchHelper.cls` | `getFacilityOffcycle()` | Add `PRM_IsDelegated__c = false`, `PRM_IsErrorRecord__c = false`; fix Active filter | 3 |
| Story 2 | `PRM_ProviderSearchHelper.cls` | `getGroupAccount()` | Add `PRM_IsErrorRecord__c = false` to `IsActive = true` SOQL branches | 2 |
| Story 3 | `PRM_OmniUtils.cls` | `isValidAccRecord()` | Add `&& !acc.PRM_IsErrorRecord__c` to active branch in Off-Cycle condition | 2 |
| Story 4 | `PRM_OmniUtils.cls` | New method `checkTerminatedGroup()` | Detect terminated group by NPI + TaxId + Name | 3 |
| Story 4 | `prmGroupSelectionOffCycle.js` | `fetchGroupData()`, `set jsonData()` | Handle `IsTerminatedGroup` flag; set/clear `isTerminatedGroupError` | 1 |
| Story 4 | `prmGroupSelectionOffCycle.html` | New error block | Render terminated group error message | 1 |
| Story 5 | `prmGroupSelectionOffCycle.js` | `fetchGroupData()`, `clearNodes()` | Set/clear `isDelegatedGroupError` flag | 0.5 |
| Story 5 | `prmGroupSelectionOffCycle.html` | New error block | Render delegated group error message | 0.5 |
| **TOTAL** | | | | **13 SP** |

---

## Dependencies

| Dependency | Reason |
|------------|--------|
| Story 1 must be completed before Story 5 | Story 1 excludes field-level delegated PLs from the query; Story 5 then handles the InfoCode-based all-delegated scenario correctly |
| Stories 1, 2, 3 are independent | Can be developed in parallel |
| Story 4 requires OmniScript TypeAhead Remote Action wiring | Needs confirmation of how `checkTerminatedGroup` is invoked (Remote Action vs. Integration Procedure) |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NPI-to-Account link may require querying via `HealthcareProviderNpi` rather than directly on Account | Medium | Medium | Verify data model during sprint planning; update `checkTerminatedGroup` query accordingly |
| Changing `PRM_Active__c = true` to the compound condition in Story 1 may return more records than before, impacting Group Selection modal performance | Low | Low | Perf test with representative data; `maxFacilitySize = 50` cap in LWC already limits display |
| `isProviderChangeFlow` flag must remain `false` for Off-Cycle — confirm this is always set correctly by the OmniScript | Low | High | Add assertion in unit test to verify flow passes correct flag |
| Story 5 — if `areAllLocationsDelegated()` receives an empty `locIds` set (e.g., all PLs excluded by Story 1 filters), it returns `false` and no error shows | Low | Medium | Verify `areAllLocationsDelegated()` handles the case where Story 1 filters leave zero PLs; may need separate "no locations found" messaging |

---

## Testing Strategy

### Unit Tests (Apex)

| Class | New Test Methods |
|-------|-----------------|
| `PRM_ProviderSearchTest` | Test `getFacilityOffcycle()` with delegated, error, and terminated PLs |
| `PRM_ProviderSearchTest` | Test `getGroupAccount()` with active error account |
| `PRM_OmniUtilsTest` | Test `isValidAccRecord()` with active error account (Off-Cycle path) |
| `PRM_OmniUtilsTest` | Test new `checkTerminatedGroup()` — all positive/negative scenarios |

### LWC Unit Tests (Jest)

| Component | Test Scenarios |
|-----------|---------------|
| `prmGroupSelectionOffCycle` | `isTerminatedGroupError = true` renders error message |
| `prmGroupSelectionOffCycle` | `isDelegatedGroupError = true` renders error message and suppresses modal |
| `prmGroupSelectionOffCycle` | Error flags clear on input change |

### Integration / UAT Scenarios

| # | Scenario |
|---|----------|
| UAT-1 | Select group with only delegated PLs → error message appears; modal does not open |
| UAT-2 | Select group with mix of delegated and non-delegated PLs → only non-delegated PLs shown in modal |
| UAT-3 | Search TypeAhead with TaxId of active error account → account does not appear in suggestions |
| UAT-4 | Enter NPI + TaxId + Name of a terminated group → terminated error message appears |
| UAT-5 | Enter NPI + TaxId + Name of an active group → no error; TypeAhead shows results |
| UAT-6 | Group has practice locations classified as Facility → Facility PLs not shown in modal |
| UAT-7 | Group has practice locations with `PRM_IsErrorRecord__c = true` → error PLs not shown in modal |
| UAT-8 | Practice Location `PRM_Active__c = false` AND `PRM_EffectiveTo__c = null` → still appears in modal |
| UAT-9 | Practice Location `PRM_Active__c = false` AND `PRM_EffectiveTo__c = [date]` → does NOT appear in modal |

---

**End of Document**
