# Practitioners Past Their Re-Cred Due Date — Aug 2025 to Jun 2026

**Date:** 2026-07-10
**Context:** Report of credentialed practitioners whose **Re-Credentialing Due Date** (`Account.PRM_ReCredDueDate__c`) falls between **Aug 2025 and Jun 2026**. Because today is 2026-07-10, every date in that window is already in the past, so the window itself is the "past due" filter. Mirrors the canonical org batch `PRM_RecredDuePractitionersReportBatch.cls`.

---

## Data model notes

- **Practitioner** = `Account` with `RecordType.DeveloperName = 'PRM_Practitioner'`.
- **Re-Cred Due Date** = `Account.PRM_ReCredDueDate__c` (Date, custom, history-tracked). Same-named field also exists on `Case` and `IndividualApplication`, but the practitioner-of-record value is on the Account.
- **`Account.PRM_IsReCredDue__c`** is a formula = `AND(PRM_ReCredDueDate__c > TODAY(), PRM_ReCredDueDate__c - TODAY() <= 180)` — i.e. "due within the next 180 days" (upcoming), NOT past due. Do **not** use it for a past-due report.
- **Case Manager** = `IndividualApplication`, linked from the Account via `PRM_CaseManager__c`; the re-cred case manager record type is `PRM_ReCredentialing`.
- Canonical batch filters also exclude PNC (`PRM_PNC__c = false`) and restrict to `PRM_CredentialingStatus__c = 'Credentialed'`.

---

## Query 1 — Practitioner Account based (primary)

**Object:** `Account`
**Use case:** List credentialed practitioners whose Re-Cred Due Date is in Aug 2025–Jun 2026 (all past due as of today).

```sql
SELECT Id, Name, FirstName, LastName, PersonContactId,
       PRM_ReCredDueDate__c, PRM_CredentialingStatus__c,
       PRM_CaseManager__c, PRM_CaseManager__r.Name
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_CredentialingStatus__c = 'Credentialed'
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c >= 2025-08-01
  AND PRM_ReCredDueDate__c <= 2026-06-30
ORDER BY PRM_ReCredDueDate__c ASC, Name
```

**Sample result / row count (if known):** TBD — run in target org.
**Notes / gotchas:**
- SOQL date literals are **unquoted** (`2025-08-01`), not string-quoted.
- For a strict "past due as of today" (ignoring the upper window), replace the last bound with `AND PRM_ReCredDueDate__c < TODAY`.
- Drop `PRM_PNC__c = false` / `IsActive = true` / status filter if you want a broader population.

---

## Query 2 — Count only

**Use case:** Quick volume check.

```sql
SELECT COUNT()
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_CredentialingStatus__c = 'Credentialed'
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c >= 2025-08-01
  AND PRM_ReCredDueDate__c <= 2026-06-30
```

---

## Query 3 — Case Manager (IndividualApplication) based, matches the org batch

**Object:** `IndividualApplication`
**Use case:** Same population, reached from the Re-Cred Case Manager down to its practitioner Accounts — mirrors `PRM_RecredDuePractitionersReportBatch.start()`.

```sql
SELECT Id, Name,
       (SELECT Id, Name, FirstName, LastName, PersonContactId, PRM_ReCredDueDate__c
        FROM Accounts__r
        WHERE IsActive = true
          AND RecordType.DeveloperName = 'PRM_Practitioner'
          AND PRM_CredentialingStatus__c = 'Credentialed'
          AND PRM_ReCredDueDate__c >= 2025-08-01
          AND PRM_ReCredDueDate__c <= 2026-06-30
          AND PRM_PNC__c = false
        ORDER BY PRM_ReCredDueDate__c, Name)
FROM IndividualApplication
WHERE Id IN (
    SELECT PRM_CaseManager__c
    FROM Account
    WHERE IsActive = true
      AND RecordType.DeveloperName = 'PRM_Practitioner'
      AND PRM_CredentialingStatus__c = 'Credentialed'
      AND PRM_ReCredDueDate__c >= 2025-08-01
      AND PRM_ReCredDueDate__c <= 2026-06-30
      AND PRM_PNC__c = false
)
AND RecordType.DeveloperName = 'PRM_ReCredentialing'
ORDER BY Name
```

**Notes / gotchas:**
- Use this variant when you also need the Case Manager number/context per practitioner. The batch also joins `HealthcareProviderTaxonomy` (by `PersonContactId`) to append taxonomies to each row.

---

## Query 4 — Re-Cred Case Managers in active review stages, filtered by Account recred due date

**Object:** `IndividualApplication`
**Use case:** Start from the Re-Cred Case Manager, filter to those currently sitting in **Application Review / PSV / QC Review / Committee Review**, and only keep the ones whose practitioner Account has a Re-Cred Due Date in the window. Returns each CM with its practitioner Account(s).

```sql
SELECT Id, Name, PRM_Stage__c, PRM_ReCredDueDate__c,
       (SELECT Id, Name, FirstName, LastName,
               PRM_ReCredDueDate__c, PRM_CredentialingStatus__c
        FROM Accounts__r
        WHERE RecordType.DeveloperName = 'PRM_Practitioner'
          AND IsActive = true
          AND PRM_ReCredDueDate__c >= 2025-08-01
          AND PRM_ReCredDueDate__c <= 2026-06-30)
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND PRM_Stage__c IN ('Application Review','PSV','QC Review','Committee Review')
  AND Id IN (
      SELECT PRM_CaseManager__c
      FROM Account
      WHERE RecordType.DeveloperName = 'PRM_Practitioner'
        AND IsActive = true
        AND PRM_ReCredDueDate__c >= 2025-08-01
        AND PRM_ReCredDueDate__c <= 2026-06-30
  )
ORDER BY PRM_Stage__c, Name
```

**Sample result / row count (if known):** TBD — run in target org.
**Notes / gotchas:**
- **Stage field** = `IndividualApplication.PRM_Stage__c` (restricted picklist, history-tracked). Exact values required: `Application Review` (not "App Review"), `PSV`, `QC Review` (not "QC"), `Committee Review`.
- SOQL can't filter a parent by a child field directly — the `Id IN (SELECT PRM_CaseManager__c FROM Account WHERE ...)` **semi-join** scopes the CMs; the `Accounts__r` subquery returns the practitioner rows. Keep the date window identical in both, or CMs come back with an empty `Accounts__r`.
- `Accounts__r` = child relationship `IndividualApplication` → `Account` via the Account's `PRM_CaseManager__c` lookup (same path as `PRM_RecredDuePractitionersReportBatch`).
- `PRM_CredentialingStatus__c = 'Credentialed'` / `PRM_PNC__c = false` were intentionally omitted (a CM mid-review may not be `Credentialed` yet); add back to match the batch exactly.
