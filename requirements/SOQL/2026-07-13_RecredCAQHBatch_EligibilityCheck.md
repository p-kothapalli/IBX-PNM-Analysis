# Recred CAQH Batch — Case Manager Eligibility Check

**Date:** 2026-07-13
**Context:** Determine whether running `PRM_CheckCAQHAccessOnDueAccountsBatch` (the recred CAQH batch) will create a recredentialing Case Manager (`IndividualApplication`) for a given practitioner. Used to diagnose Account `001VB00000o8OLMYA2` (Sarah Awad).

The batch selects practitioners due for recred, then `PRM_CheckCAQHExecuteHelper.processAccount` decides if a Case Manager is created. Key gates:
- `start` query: `IsActive=true`, RecordType=Practitioner, `PRM_DelegatedOnly__c=false`, `PRM_PNC__c=false`, and `PRM_ReCredDueDate__c` matches the `ReCredCAQHDateRange` custom setting (exact `today + PRM_DueDays__c` when DueDays is set; otherwise Start/End range).
- Skip if an in-flight `PRM_ReCredentialing` IA already exists (status not Approved/Denied/Terminate).
- Skip if no CAQH identifier AND not "Universal" (Universal = `PRM_CredentialingStatus__c = Credentialed` AND no CAQH identifier).
- Otherwise a Case Manager + Case is created (active vs inactive path decided by the live CAQH validator call).

---

## Query 1 — Practitioner eligibility fields

**Object:** `Account`
**Use case:** Pull the fields the batch's `start` query filters on, for one practitioner.

```sql
SELECT Id, Name, IsActive, PRM_DelegatedOnly__c, PRM_PNC__c,
       PRM_ReCredDueDate__c, PRM_IsReCredDue__c, PRM_CredentialingStatus__c
FROM Account
WHERE Id = '001VB00000o8OLMYA2'
```

**Sample result:** IsActive=true, DelegatedOnly=false, PNC=false, ReCredDueDate=**2027-01-08** (raw API value), CredentialingStatus=Credentialed.
**Notes:** RecordType must be `Practitioner`. The recred due date must equal `today + DueDays` on the run date (exact match when DueDays is set).
**⚠️ Gotcha (verified 2026-07-13):** `PRM_ReCredDueDate__c` is a **Date** field, but `sf data query`'s human table output renders it shifted by one day for the running user's timezone (America/New_York) — it displayed `2027-01-09` while the raw value is `2027-01-08`. Always confirm Date fields via `--json` (raw) or Apex, not the CLI table, before doing date arithmetic. Consequence: with DueDays=180 the batch's `PRM_ReCredDueDate__c = today+180` filter matched `2027-01-09` and therefore did NOT pick up this account (true due date 2027-01-08); it would only be selected if the batch ran on 2026-07-12. Bypassing the filter (querying by Id) creates the CM but does not reflect real batch selection.

---

## Query 2 — CAQH identifier presence

**Object:** `Identifier`
**Use case:** The batch's `start` subquery only pulls CAQH identifiers; presence/absence drives the Universal branch.

```sql
SELECT Id, IdValue, PRM_Type__c, PRM_AttestationDate__c
FROM Identifier
WHERE ParentRecordId = '001VB00000o8OLMYA2' AND PRM_Type__c = 'CAQH'
```

**Sample result:** 1 CAQH id (`16174548`, attestation 2026-04-15) → not empty, so Universal=false → non-universal branch (CM still created).

---

## Query 3 — Existing Case Managers (in-flight ReCred check)

**Object:** `IndividualApplication`
**Use case:** Detect an existing non-terminal ReCredentialing IA that would cause the batch to skip the account.

```sql
SELECT Id, Name, RecordType.DeveloperName, Status, PRM_Stage__c, CreatedDate
FROM IndividualApplication
WHERE AccountId = '001VB00000o8OLMYA2'
ORDER BY CreatedDate DESC
```

**Sample result:** 1 IA — `PRM_PractitionerParticipationRequest`, Approved/Complete (not a ReCred IA) → not skipped.
**Notes/gotchas:** `PRM_Category__c` does NOT exist on `IndividualApplication` (query fails). The skip only triggers for a `PRM_ReCredentialing` IA whose Status is not Approved/Denied/Terminate.

---

## Query 4 — Recred date-range custom setting

**Object:** `PRM_CAQHDateRangeSetting__c`
**Use case:** Read the run-date math. When `PRM_DueDays__c` is set, the batch matches `PRM_ReCredDueDate__c = today + DueDays` exactly.

```sql
SELECT Name, PRM_DueDays__c, PRM_StartDate__c, PRM_EndDate__c, PRM_BatchSize__c
FROM PRM_CAQHDateRangeSetting__c
WHERE Name = 'ReCredCAQHDateRange'
```

**Sample result:** DueDays=180, Start/End null, BatchSize=50 → on 2026-07-13, ftrDate = 2027-01-09 (exact match to Sarah Awad).
**Notes:** Exact-date match means the practitioner is only in scope on the single day when `today + 180` equals their recred due date. Use Start/End range (clear DueDays) to widen the window.
