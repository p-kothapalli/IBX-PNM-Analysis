# PPR Case Managers Missing Institution

**Date:** 2026-06-23
**Context:** Business asked "how many Case Managers are missing institution in the Practitioner Participation Request (PPR) record type." This is the NPDB "No Institution" root cause (`G1: Set A and set B mandatory fields not complete`). A Case Manager is flagged "missing institution" when the practitioner's `PersonEducation` record has `PRM_Institution__c = null` (see `PRM_NPDBErrorMessageTriggerHelper.evaluateEducation`).

---

## Data model notes (relationship chain)

```
IndividualApplication                 (UI label = "Case Manager")
  • RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  • AccountId  → Account (the practitioner, a Person Account)
        ▲
        │ (same Account)
        ▼
PersonEducation
  • Contact.AccountId  → practitioner Account  (Contact = the Account's PersonContact)
  • PRM_Institution__c → lookup to PRM_Institution__c  ← NULL means "missing institution"
  • PRM_Degree__r.Name, PRM_EndDate__c
```

**"Missing institution" definition:** at least one `PersonEducation` row for the practitioner Account has `PRM_Institution__c = null`. (Distinct from "Education Missing", which is *no* `PersonEducation` rows at all.)

**Why no single SOQL statement works:** a semi-join's left operand can't traverse two levels (`Contact.AccountId` is rejected: *"The left operand cannot have more than one level of relationships"*), and an IN-list of ~15K account Ids blows the SOQL string-length limit. So this is done as **two queries + a client-side (or Apex) intersection**.

---

## Query 1 — All PPR Case Manager → Account (export side A)

**Object:** `IndividualApplication`
**Use case:** One row per PPR Case Manager record, with its practitioner Account.

```sql
SELECT AccountId
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND AccountId != null
```

**Sample result / row count (qa-sandbox, 2026-06-23):** 17,381 PPR Case Manager records across 15,115 distinct practitioner Accounts.

---

## Query 2 — Accounts with an education record that has NO institution (export side B)

**Object:** `PersonEducation`
**Use case:** Every practitioner Account that has at least one education row missing its institution.

```sql
SELECT Contact.AccountId
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND Contact.AccountId != null
```

**Sample result / row count (qa-sandbox, 2026-06-23):** 33,179 education rows → 31,700 distinct Accounts missing institution (org-wide, not just PPR).

---

## Intersection — the answer

Intersect the Account Ids from Query 1 and Query 2:

- **PPR Case Manager RECORDS missing institution: 7,277**
- **Distinct PPR practitioners (Accounts) missing institution: 5,898**

(The gap = practitioners with multiple PPR Case Manager records / re-submissions.)

CLI recipe used:
```bash
sf data query -o qa-sandbox --result-format csv \
  --query "SELECT AccountId FROM IndividualApplication WHERE RecordType.DeveloperName='PRM_PractitionerParticipationRequest' AND AccountId != null" > ppr.csv
sf data query -o qa-sandbox --result-format csv \
  --query "SELECT Contact.AccountId FROM PersonEducation WHERE PRM_Institution__c = null AND Contact.AccountId != null" > miss.csv
# then set-intersect AccountId column of ppr.csv against miss.csv
```

---

## Monthly tracking — this month's PPR case managers with the institution error

**Use case:** Track how many *new* PAR (PPR) case managers raised this month carry the missing-institution error. Only the case-manager side gets a `CreatedDate = THIS_MONTH` filter; the `PersonEducation` side (Query 2) is unchanged.

```sql
-- Side A, scoped to this month
SELECT AccountId
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND AccountId != null
  AND CreatedDate = THIS_MONTH
```

Then intersect the `AccountId` column against Query 2 (accounts missing institution).

**Sample result / row count (qa-sandbox, 2026-06 / "THIS_MONTH"):**
- 203 PPR case managers created this month (196 practitioners)
- **147 records** with the missing-institution error, across **142 practitioners** (~72% of this month's new PAR cases)

**Notes:** swap `THIS_MONTH` for `LAST_MONTH`, `LAST_N_DAYS:30`, or a literal range (`CreatedDate >= 2026-06-01T00:00:00Z`) to track other windows.

---

## ⭐ Single-statement count (Account-anchored)

**Why it works:** anchoring on `Account` keeps both semi-joins **one level deep** (`Account.Id` and `Account.PersonContactId`), which sidesteps the two-level `Contact.AccountId` rejection. Salesforce allows up to two non-nested semi-joins in one `WHERE`. Drop the `CreatedDate` line for the all-time version.

```sql
SELECT COUNT()
FROM Account
WHERE Id IN (
        SELECT AccountId
        FROM IndividualApplication
        WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
          AND CreatedDate = THIS_MONTH
      )
  AND PersonContactId IN (
        SELECT ContactId
        FROM PersonEducation
        WHERE PRM_Institution__c = null
      )
```

**Sample result (qa-sandbox, THIS_MONTH):** 142 — distinct **practitioners**. (Replace `COUNT()` with `Id, Name` to list the accounts.)

> Grain note: this counts **accounts/practitioners (142)**, not case-manager records (147). The record grain lives on `IndividualApplication`, which can't reach `PersonEducation` in a single non-nested semi-join, so the **Case Manager Ids** need the two-step below.

---

## ⭐ Get the Case Manager Ids (two-step — record grain)

A single statement can't return Case Manager Ids filtered by `PersonEducation` (it would be a nested semi-join, which Salesforce rejects). For a bounded window (e.g. `THIS_MONTH`, ~142 accounts) the account-Id `IN` list fits, so run two steps:

**Step 1 — account Ids (single statement above, returning `Id`):**
```sql
SELECT Id
FROM Account
WHERE Id IN (
        SELECT AccountId FROM IndividualApplication
        WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
          AND CreatedDate = THIS_MONTH)
  AND PersonContactId IN (
        SELECT ContactId FROM PersonEducation WHERE PRM_Institution__c = null)
```

**Step 2 — the Case Manager records (feed Step 1's Ids into the `IN`):**
```sql
SELECT Id, Name, PRM_Stage__c, Status, Account.Name
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate = THIS_MONTH
  AND AccountId IN (:accountIdsFromStep1)
ORDER BY CreatedDate
```

**Sample result (qa-sandbox, THIS_MONTH):** **147 Case Manager records** across 142 practitioners. Full list exported to `scripts/CaseManagers_MissingInstitution_ThisMonth.csv`.

CLI recipe:
```bash
IDS=$(sf data query -o qa-sandbox --result-format csv \
  --query "SELECT Id FROM Account WHERE Id IN (SELECT AccountId FROM IndividualApplication WHERE RecordType.DeveloperName='PRM_PractitionerParticipationRequest' AND CreatedDate = THIS_MONTH) AND PersonContactId IN (SELECT ContactId FROM PersonEducation WHERE PRM_Institution__c = null)" \
  | tail -n +2 | tr -d '\r' | grep -v '^$' | paste -sd, | sed "s/[^,]*/'&'/g")
sf data query -o qa-sandbox --result-format csv \
  --query "SELECT Id, Name, PRM_Stage__c, Status, Account.Name FROM IndividualApplication WHERE RecordType.DeveloperName='PRM_PractitionerParticipationRequest' AND CreatedDate = THIS_MONTH AND AccountId IN ($IDS) ORDER BY CreatedDate"
```

---

## Optional — scope to OPEN case managers

Add the open filter to Query 1 to count only in-flight cases (Stage not Complete):

```sql
SELECT AccountId
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c != 'Complete'
  AND AccountId != null
```

**Notes / gotchas:**
- `PRM_Institution__c = null` only flags practitioners who *have* education rows with a blank institution. To also catch practitioners with **no education at all** (the helper's separate "Education Missing" error), query Accounts that have zero `PersonEducation` children.
- Counts are point-in-time against `qa-sandbox`; re-run for current numbers.
- Aggregate `GROUP BY AccountId` in anonymous Apex fails with *"Aggregate query does not support queryMore()"* at this volume (15K+ groups) — use the CLI export + intersect approach (or a Batch Apex) instead.
