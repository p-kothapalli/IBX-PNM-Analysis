# Duplicate Primary / Billing / Mailing Address per Location

**Date:** 2026-09-03
**Context:** BUG 1300056 (*More than one primary address per location*) — Julie Nguyen reported two active `Address` rows with `Primary` on the same Healthcare Facility Location (Clear Lake Dialysis Center). Confirm whether the uniqueness invariant is enforced and whether the defect is still in QA / Full Copy.

---

## Query 1 — Locations with more than one currently-effective active Primary

**Object:** `Address` (parent = Location)
**Use case:** Find Location records that currently have two or more **active, non-pending, effective-today** addresses whose multi-select `PRM_AddressType__c` includes `Primary`. This is the live form of BUG 1300056.

```sql
SELECT ParentId, COUNT(Id) cnt
FROM Address
WHERE PRM_Active__c = true
  AND PRM_Pending__c = false
  AND PRM_AddressEffectiveToday__c = true
  AND PRM_AddressType__c INCLUDES ('Primary')
GROUP BY ParentId
HAVING COUNT(Id) > 1
```

**Sample result / row count (if known):** FC2 (`FC2`) = **13 locations**. QA (`salesforce-7y19gr`) = **5 locations**. Run 2026-09-03.
**Notes / gotchas:** `PRM_AddressType__c` is a multi-select — must use `INCLUDES ('Primary')`, not `LIKE`. `PRM_AddressEffectiveToday__c` is a formula on From/To only; it does **not** check `PRM_Active__c`, so always AND Active = true. Parent is Location (`131…`), not HealthcareFacility (`0kl…`).

---

## Query 2 — Same check for Billing

**Object:** `Address`
**Use case:** Julie’s note on the bug (*“there are also situations where there are more than one Practice, Billing, Mailing”*) — currently-effective duplicate Billing per Location.

```sql
SELECT ParentId, COUNT(Id) cnt
FROM Address
WHERE PRM_Active__c = true
  AND PRM_Pending__c = false
  AND PRM_AddressEffectiveToday__c = true
  AND PRM_AddressType__c INCLUDES ('Billing')
GROUP BY ParentId
HAVING COUNT(Id) > 1
```

**Sample result / row count (if known):** FC2 = **99 locations**. Run 2026-09-03.
**Notes / gotchas:** Same INCLUDES / formula caveats as Query 1.

---

## Query 3 — Same check for Mailing

**Object:** `Address`
**Use case:** Currently-effective duplicate Mailing per Location.

```sql
SELECT ParentId, COUNT(Id) cnt
FROM Address
WHERE PRM_Active__c = true
  AND PRM_Pending__c = false
  AND PRM_AddressEffectiveToday__c = true
  AND PRM_AddressType__c INCLUDES ('Mailing')
GROUP BY ParentId
HAVING COUNT(Id) > 1
```

**Sample result / row count (if known):** FC2 = **208 locations**. Run 2026-09-03.
**Notes / gotchas:** Mailing is the most common duplicate type in FC2.

---

## Query 4 — Same check for Practice

**Object:** `Address`
**Use case:** Currently-effective duplicate Practice type per Location.

```sql
SELECT ParentId, COUNT(Id) cnt
FROM Address
WHERE PRM_Active__c = true
  AND PRM_Pending__c = false
  AND PRM_AddressEffectiveToday__c = true
  AND PRM_AddressType__c INCLUDES ('Practice')
GROUP BY ParentId
HAVING COUNT(Id) > 1
```

**Sample result / row count (if known):** FC2 = **2 locations**. Run 2026-09-03.

---

## Query 5 — Address rows for a known duplicate Location

**Object:** `Address`
**Use case:** Inspect the overlapping Primary rows for one ParentId returned by Query 1 (swap the Id). Example: `131UW000001KWUbYAO` (MH TX Options LLC) has two active Primaries both effective 2026-02-01.

```sql
SELECT Id, Name, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_AddressEffectiveToday__c,
       PRM_AddressLine1__c
FROM Address
WHERE ParentId = '131UW000001KWUbYAO'
  AND PRM_AddressType__c INCLUDES ('Primary')
ORDER BY PRM_EffectiveFrom__c, Name
```

**Sample result / row count (if known):** FC2, 2026-09-03 — two currently-effective active Primaries (`A01327179`, `A01327483`), both From = 2026-02-01 / To = null / same street.

---

## Query 6 — Original BUG 1300056 example (Clear Lake Dialysis Center)

**Object:** `HealthcareFacility` + `Address`
**Use case:** Re-check the facility cited in the bug (`0klUW0000001en0YAA`).

```sql
SELECT Id, Name, LocationId
FROM HealthcareFacility
WHERE Id = '0klUW0000001en0YAA'
```

```sql
SELECT Id, Name, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_AddressEffectiveToday__c,
       PRM_AddressLine1__c
FROM Address
WHERE ParentId = '131UW0000015ciXYAQ'
ORDER BY PRM_EffectiveFrom__c, Name
```

**Sample result / row count (if known):** FC2, 2026-09-03 — 4 Address rows. The original duplicate Primary was **partially cleaned**: `A01050679` (Primary;Billing;Mailing, From 2025-01-01) is now **Inactive**. One active Primary remains (`A01050678`). `A01050677` (Billing;Mailing) is still active open-ended. `A01050679.PRM_AddressEffectiveToday__c` is still true because the formula ignores Active.

**Notes / gotchas:** Production URL in the bug used `ibx.lightning.force.com`. FC2 is the closest connected full-copy. LocationId for this facility is `131UW0000015ciXYAQ`.
