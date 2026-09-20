# Off-Cycle HFN with null Practice Location (HealthcareFacilityId)

**Date:** 2026-09-14  
**Context:** Investigate Off Cycle “New Region” creates of `HealthcareFacilityNetwork` (RT `PRM_FacilityPractitionerTxNw`) where `HealthcareFacilityId` is null, which blanks PRACTICE LOCATION in PDA Review and blocks the specialist.

---

## Query 1 — Bad Practitioner-at-Practice-Location rows (null facility)

**Object:** `HealthcareFacilityNetwork`  
**Use case:** Find all Practitioner-at-Practice-Location / Facility Practitioner Tx Nw rows with no Practice Location lookup.

```sql
SELECT Id, Name, CreatedDate, CreatedBy.Name,
       HealthcareFacilityId, AccountId, Account.Name,
       PractitionerId, Practitioner.Name,
       PRM_CaseManager__c, PRM_Pending__c, IsActive,
       PRM_Taxonomy__c, PRM_PractitionerRole__c, PRM_ChangeReason__c,
       RecordType.DeveloperName
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND HealthcareFacilityId = NULL
ORDER BY CreatedDate DESC
LIMIT 200
```

**Notes / gotchas:** Confirm RT developer name in the org (`PRM_FacilityPractitionerTxNw`). Name often contains the literal substring `- null -` when Apex `cloneHCFNRecords` built the name with a null Taxonomy.

---

## Query 2 — Recent creates only (are we still creating bad rows?)

**Object:** `HealthcareFacilityNetwork`  
**Use case:** Confirm whether NEW null-facility HFN rows are still being inserted (post any supposed fix).

```sql
SELECT Id, Name, CreatedDate, CreatedBy.Name,
       HealthcareFacilityId, Account.Name, Practitioner.Name,
       PRM_CaseManager__c, PRM_Pending__c, PRM_ChangeReason__c
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND HealthcareFacilityId = NULL
  AND CreatedDate = LAST_N_DAYS:30
ORDER BY CreatedDate DESC
```

**Sample result / row count (if known):** run in org after reproducing New Region + new group + new practice location.

---

## Query 3 — Tie bad HFN rows to Off-Cycle Case Manager / Case

**Object:** `HealthcareFacilityNetwork` (+ Case Manager)  
**Use case:** Scope null-facility rows to Off-Cycle New Region / New State requests.

```sql
SELECT Id, Name, CreatedDate, HealthcareFacilityId,
       PRM_CaseManager__c,
       PRM_CaseManager__r.Name,
       PRM_CaseManager__r.PRM_OffCycleRequestType__c,
       PRM_CaseManager__r.Status,
       PRM_CaseManager__r.AccountId,
       Account.Name, Practitioner.Name
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND HealthcareFacilityId = NULL
  AND PRM_CaseManager__r.PRM_OffCycleRequestType__c IN ('New Region', 'New State')
ORDER BY CreatedDate DESC
LIMIT 200
```

**Notes / gotchas:** Adjust the Off-Cycle request-type field API name if the org uses a different API (`PRM_OffCycleRequestType__c` vs label “Off Cycle Request Type”).

---

## Query 4 — Name pattern from cloneHCFNRecords (`- null -`)

**Object:** `HealthcareFacilityNetwork`  
**Use case:** Rows whose Name was built when Taxonomy (and often PracticeLocationId) was null in JSON.

```sql
SELECT Id, Name, CreatedDate, HealthcareFacilityId,
       Account.Name, Practitioner.Name, PRM_CaseManager__c
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND Name LIKE '%- null -%'
ORDER BY CreatedDate DESC
LIMIT 200
```

---

## Query 5 — Count by day (trend / still-shipping check)

**Object:** `HealthcareFacilityNetwork`  
**Use case:** Daily volume of null-facility Practitioner Tx Nw creates.

```sql
SELECT DAY_ONLY(CreatedDate) dayCreated, COUNT(Id) cnt
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND HealthcareFacilityId = NULL
  AND CreatedDate = LAST_N_DAYS:90
GROUP BY DAY_ONLY(CreatedDate)
ORDER BY DAY_ONLY(CreatedDate) DESC
```
