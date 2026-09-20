# CAQH ID Length (find 7-digit CAQH identifiers)

**Date:** 2026-07-31
**Context:** Need to find CAQH IDs that are exactly 7 digits long. CAQH IDs are stored on the practitioner's child `Identifier` record (`PRM_Type__c = 'CAQH'`) in the standard `IdValue` field. SOQL has no length/regex function, so length is matched with the `LIKE` single-character wildcard `_`.

---

## Query 1 — CAQH IDs that are exactly 7 characters

**Object:** `Identifier`
**Use case:** Returns every CAQH identifier whose `IdValue` is exactly 7 characters long (i.e., 7-digit CAQH IDs, since CAQH IDs are numeric).

```sql
SELECT ParentRecordId,
       ParentRecord.Name,
       IdValue,
       PRM_Active__c,
       PRM_AttestationDate__c
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND IdValue LIKE '_______'
ORDER BY IdValue
```

**Notes / gotchas:**
- `LIKE '_______'` = exactly 7 underscores → matches any value of **exactly** 7 characters. Add/remove underscores to change the length.
- `_` matches ANY single character, not only digits — SOQL has no digit character class. If 7-char values could contain letters/spaces, post-filter in Apex (`String.isNumeric(v) && v.length()==7`) or export and grep `^[0-9]{7}$`.
- Add `AND PRM_Active__c = true` to restrict to active identifiers.
- The CAQH ID lives in the standard `IdValue` field on the CAQH `Identifier` row; `Name` is the auto-number (`ID-######`), not the CAQH number. (`PRM_AttestationID__c` also holds a CAQH id on some rows — confirm which your data uses.)
- `Identifier.ParentRecordId` is polymorphic; CAQH-for-practitioner rows point to `Account`.

---

## Query 2 — 7-digit CAQH ID + practitioner NPI + ReCred Due Date

**Correction:** the practitioner NPI is **NOT** on the `Identifier` record. It lives on the standard **`HealthcareProviderNpi`** object (field `Npi`), linked to the practitioner Account via `AccountId` (and `PractitionerId`). Existing code confirms the pattern: `PRM_NPDBErrorMessageTriggerHelper.fetchProviderNpi()` queries `SELECT Id, Npi, AccountId FROM HealthcareProviderNpi WHERE AccountId IN :accounts`. Because NPI is a **sibling child** of the Account (not a child of `Identifier`), it can't be pulled in a flat query on `Identifier` — use a 2-query join or an Account-rooted query with subqueries.

### Option A — two queries, joined on the practitioner Account Id (most reliable)

**Query 2a — CAQH (7-digit) + ReCred Due Date** (`Object: Identifier`):

```sql
SELECT ParentRecordId,
       ParentRecord.Name,
       IdValue,
       PRM_Active__c,
       PRM_AttestationDate__c,
       TYPEOF ParentRecord
         WHEN Account THEN PRM_ReCredDueDate__c
       END
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND IdValue LIKE '_______'
  AND ParentRecord.Type = 'Account'
ORDER BY IdValue
```

**Query 2b — NPI for those practitioners** (`Object: HealthcareProviderNpi`; paste the `ParentRecordId` Account Ids from 2a):

```sql
SELECT AccountId, PractitionerId, Npi, NpiType, EffectiveFrom, EffectiveTo
FROM HealthcareProviderNpi
WHERE NpiType = 'Individual'
  AND AccountId IN ('001...','001...')
```

**Join key:** `HealthcareProviderNpi.AccountId` = `Identifier.ParentRecordId`.

### Option B — single Account-rooted query with subqueries

```sql
SELECT Id, Name,
       PRM_ReCredDueDate__c,
       (SELECT IdValue, PRM_AttestationDate__c
          FROM Identifiers
         WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'),
       (SELECT Npi, NpiType, EffectiveFrom, EffectiveTo
          FROM HealthcareProviderNpis
         WHERE NpiType = 'Individual')
FROM Account
WHERE Id IN (
    SELECT ParentRecordId FROM Identifier
    WHERE PRM_Type__c = 'CAQH' AND IdValue LIKE '_______'
)
```

**Notes / gotchas:**
- **NPI source is `HealthcareProviderNpi.Npi`** — there is no NPI field on `Identifier` (an earlier `PRM_NPI__c` guess was wrong). `NpiType = 'Individual'` picks the practitioner (vs `Organization`) NPI. Consider filtering active rows via `EffectiveTo`/`PRM_NPIEffectiveToday__c`.
- **ReCred Due Date** = `Account.PRM_ReCredDueDate__c` (also on `IndividualApplication` and `Case`). Via `Identifier` it needs `TYPEOF ParentRecord WHEN Account THEN ... END` because `ParentRecordId` is polymorphic.
- **Option B relationship names** (`Identifiers`, `HealthcareProviderNpis`) are the standard child-relationship names but may be customized. If SOQL errors with `Didn't understand relationship`, confirm via describe or fall back to Option A (guaranteed to work).
```
