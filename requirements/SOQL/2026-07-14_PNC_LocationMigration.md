# PNC Location Migration — Existing-Data Review Queries

**Date:** 2026-07-14
**Context:** Before we migrate the PNC flag from the group/vendor `Account` down to the practice location (`HealthcareFacility`), the business wants to review the existing data. These queries produce the two review lists: (1) single-location groups (copy the group's PNC to its one location) and (2) multi-location groups where the group PNC = Yes today (decide whether ALL their locations get PNC checked).

**Data model:**
- Group / vendor = `Account` with `RecordType.DeveloperName = 'PRM_Vendor'`; group PNC = `Account.PRM_PNC__c`.
- Practice location = `HealthcareFacility`; `HealthcareFacility.AccountId` → the group/vendor Account.
- Target field `HealthcareFacility.PRM_PNC__c` already exists (destination of the migration). These queries read the **source** (`Account.PRM_PNC__c`) only.

> Adjust `PRM_Vendor` if some groups use `PRM_SupplementalBenefitVendor` / `PRM_NCPDP`. To count only live locations, add `AND PRM_Active__c = true` (noted per query).

---

## Query 1 — Single-location groups (copy group PNC → that one location)

**Object:** `HealthcareFacility` (aggregate, grouped by vendor Account)
**Use case:** Every group that has exactly ONE practice location, with the group's current PNC value. Business already agreed: copy the group PNC to that single location (whether Yes or No).

```sql
SELECT AccountId,
       Account.Name grpName,
       Account.PRM_PNC__c grpPNC,
       COUNT(Id) locCount
FROM HealthcareFacility
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
GROUP BY AccountId, Account.Name, Account.PRM_PNC__c
HAVING COUNT(Id) = 1
ORDER BY Account.Name
```

**Active-only variant:** add `AND PRM_Active__c = true` to the `WHERE` clause (counts only live locations toward the "single location" test).

**Notes / gotchas:** Aggregate `GROUP BY` on parent (`Account.*`) fields is allowed. This returns one row per group. Groups with zero locations don't appear (nothing to migrate).

---

## Query 2 — Multi-location groups with group PNC = Yes (the decision list)

**Object:** `HealthcareFacility` (aggregate, grouped by vendor Account)
**Use case:** Groups that have MORE THAN ONE location AND whose group PNC = Yes today. This is the population where the business must decide "do we check PNC on ALL locations?" Shows group name + location count.

```sql
SELECT AccountId,
       Account.Name grpName,
       Account.PRM_PNC__c grpPNC,
       COUNT(Id) locCount
FROM HealthcareFacility
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
  AND Account.PRM_PNC__c = true
GROUP BY AccountId, Account.Name, Account.PRM_PNC__c
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
```

**Active-only variant:** add `AND PRM_Active__c = true`.

**Notes / gotchas:** `ORDER BY COUNT(Id) DESC` surfaces the biggest groups first (largest blast radius if we check PNC on all locations).

---

## Query 3 — Location-level detail for the multi-location PNC groups (eyeball review)

**Object:** `HealthcareFacility` (detail)
**Use case:** The actual list of locations that WOULD get PNC = Yes if we apply "check ALL locations" to PNC groups. Reviewer scans by group; any group with more than one row is a multi-location group. Use this to spot locations that clearly should NOT be PNC.

```sql
SELECT Account.Name grpName,
       AccountId,
       Account.PRM_PNC__c grpPNC,
       Id,
       Name,
       PRM_PracticeName__c,
       PRM_DoingBusinessAsName__c,
       LocationId,
       PRM_Active__c,
       PRM_NonParLocation__c
FROM HealthcareFacility
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
  AND Account.PRM_PNC__c = true
ORDER BY Account.Name, Name
```

**Active-only variant:** add `AND PRM_Active__c = true`.

**Notes / gotchas:** Detail query can't nest the aggregate from Query 2, so it returns locations for ALL PNC groups (single + multi). Filter/pivot the export by `grpName` — groups appearing once are single-location (Query 1 population), groups appearing 2+ times are the multi-location review set (Query 2 population).

---

## Query 4 — Summary counts (sizing)

**Object:** `HealthcareFacility` (aggregate)
**Use case:** Quick totals to size the effort / determination.

```sql
-- Total groups and total locations in scope
SELECT COUNT_DISTINCT(AccountId) groups, COUNT(Id) locations
FROM HealthcareFacility
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
```

```sql
-- Groups + locations under PNC = Yes groups only
SELECT COUNT_DISTINCT(AccountId) pncGroups, COUNT(Id) pncGroupLocations
FROM HealthcareFacility
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
  AND Account.PRM_PNC__c = true
```

**Notes / gotchas:** `COUNT_DISTINCT(AccountId)` gives distinct group count; `COUNT(Id)` gives raw location count. Compare Query 1 row count (single-location groups) against these totals to see how much of the population is the "easy" single-location copy vs the multi-location decision.
