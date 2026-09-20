# CAQH (7-digit) + NPI Lookup

**Date:** 2026-07-07
**Context:** Find CAQH IDs that are 7 characters long (stored on the `Identifier` object as `PRM_Type__c = 'CAQH'`) and pair each with the provider's NPI. The NPI is **not** an `Identifier` type in this org — it lives on the standard `HealthcareProviderNpi` object (`Npi` field). Both records share the same parent **`Account`** (`Identifier.ParentRecordId` and `HealthcareProviderNpi.AccountId`), so the Account is the join key.

---

## Key schema facts (verified against `ibx-dev`)

- `Identifier` types present: `EIN`, `Document`, `CAQH`, `HRLO`, `MCRE`, `BSPA`, `Medicare Number`, `HR`, `NABP`, `Other` — **no `NPI` type**.
- CAQH `Identifier.ParentRecord.Type` is almost always `Account` (828) with 1 `Contact`.
- NPI value = `HealthcareProviderNpi.Npi`; links via `AccountId` (child rel `HealthcareProviderNpis`) or `PractitionerId`→Contact (child rel `PersonHealthcareProviderNpis`).
- Account child relationships: `Identifiers` (→ `Identifier.ParentRecordId`), `HealthcareProviderNpis` (→ `HealthcareProviderNpi.AccountId`).
- `IdValue LIKE '_______'` (7 underscores) matches **exactly 7 characters** — `_` = any single char, so it is not strictly numeric. SOQL has no regex; enforce "digits only" in code if needed.

---

## Query 1 — Account-anchored, CAQH + NPI in one row (recommended)

**Object:** `Account` (with subqueries into `Identifiers` and `HealthcareProviderNpis`)
**Use case:** For every Account that has a 7-char CAQH identifier, return the CAQH value(s) alongside the NPI value(s).

```sql
SELECT Id, Name,
       (SELECT Id, IdValue, PRM_Type__c, CreatedDate
        FROM Identifiers
        WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'),
       (SELECT Id, Npi, NpiType, IsActive
        FROM HealthcareProviderNpis)
FROM Account
WHERE Id IN (
    SELECT ParentRecordId
    FROM Identifier
    WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'
)
```

**Sample result:** 2 rows in `LIMIT 5` test — e.g. Account "Siham Abdelqader" → CAQH `1336859`, NPI `1639949365` (Individual).
**Notes / gotchas:**
- The semi-join `Id IN (SELECT ParentRecordId FROM Identifier ...)` works even though `ParentRecordId` is polymorphic — non-Account IDs simply don't match `Account.Id`.
- Returns parent/child structure (an Account can have multiple CAQH ids and/or multiple NPI rows). Flatten in code for a strict one-pair-per-row output.
- Add `AND HealthcareProviderNpis` filter (`IsActive = true` / `NpiType = 'Individual'`) inside the subquery if you only want active/individual NPIs.

---

## Query 2 — Flat pair via HealthcareProviderNpi (NPI-anchored)

**Object:** `HealthcareProviderNpi` (with subquery into the Account's `Identifiers`)
**Use case:** Start from NPI records; pull the matching 7-char CAQH from the same Account. Good when you want one row per NPI.

```sql
SELECT Id, Npi, NpiType, AccountId, Account.Name,
       (SELECT IdValue, CreatedDate
        FROM Account.Identifiers
        WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______')
FROM HealthcareProviderNpi
WHERE AccountId IN (
    SELECT ParentRecordId
    FROM Identifier
    WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'
)
```

**Notes / gotchas:** Nested child subquery through a parent relationship (`Account.Identifiers`) is not allowed in SOQL — if this errors, use Query 1 or Query 3 instead.

---

## Query 3 — Two simple queries, join in memory (most portable)

**Use case:** Simplest/most reliable; run both and join on Account Id in Apex/script.

```sql
-- (a) 7-char CAQH ids
SELECT Id, IdValue, ParentRecordId, ParentRecord.Name, CreatedDate
FROM Identifier
WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'
```

```sql
-- (b) NPIs for those Accounts (paste the ParentRecordId set from (a))
SELECT Id, Npi, NpiType, AccountId, Account.Name
FROM HealthcareProviderNpi
WHERE AccountId IN (:accountIds)
```

**Notes / gotchas:** Original query used `PRM_Type_c`/`Idvalue` — correct API names are `PRM_Type__c` (double underscore) and `IdValue`.
