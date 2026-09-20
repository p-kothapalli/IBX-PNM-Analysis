# Ancillary Assessment "Add Sub-Service" Investigation Queries

**Date:** 2026-06-02
**Context:** Confirming live state of account `001UW00000ejn1SYAQ` (Complete Care At Lakeview Llc) for the two-scenario "add sub-service after initial submission" requirement. Both scenarios (in-flight PSV CM, and approved-from-2024 CM with reassessment date > 1 yr out) are materialised on this single account, making it ideal for regression testing the design proposed in `requirements/AncillaryAssessment_AddSubService_TwoScenarios_UserStory.md`.

---

## Query 1 — All Ancillary Assessments on the account

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** List every AA for the account along with its case manager state and reassessment date, to identify duplicates and to evaluate Scenario-2 (date > 1 yr from today).

```sql
SELECT Id, Name, RecordType.DeveloperName, PRM_ProviderTypeService__c,
       PRM_Account__c, PRM_CaseManager__c, PRM_CaseManager__r.Name,
       PRM_CaseManager__r.PRM_Stage__c, PRM_CaseManager__r.Status,
       PRM_AuthorizedSignatureForProvider__c, PRM_ReAssessmentDueDate__c, CreatedDate
FROM PRM_AncillaryAssessment__c
WHERE PRM_Account__c = '001UW00000ejn1SYAQ'
ORDER BY CreatedDate DESC
```

**Sample result (2026-06-02):** 2 rows — same `PRM_ProviderTypeService__c='Skilled Nursing'`, one in-flight PSV (no reassessment date), one with `PRM_ReAssessmentDueDate__c=2027-07-08` (≈13 months out, no CM).

**Notes / gotchas:** The duplicate `PRM_ProviderTypeService__c` on the same account is itself the live-data evidence of Gap #2 in the user story.

---

## Query 2 — Active Ancillary Case Managers on the account

**Object:** `IndividualApplication`
**Use case:** Confirm there is exactly one in-flight Ancillary CM (used to validate "REUSE_IN_FLIGHT_CM" context detection).

```sql
SELECT Id, Name, RecordType.DeveloperName, PRM_Stage__c, Status,
       PRM_ProviderTypeService__c, AccountId, ApplicationCaseId,
       PRM_AncillaryAssessment__c, CreatedDate, AppliedDate
FROM IndividualApplication
WHERE AccountId = '001UW00000ejn1SYAQ'
  AND RecordType.DeveloperName IN ('PRM_AncillaryAssessment','PRM_AncillaryReAssessment')
ORDER BY CreatedDate DESC
```

**Sample result:** 1 row — `IA-0000152008`, `PRM_Stage__c='PSV'`, `Status='In Progress'`, `PRM_AncillaryAssessment__c=null` (interesting — the CM does not back-link to its AA; the link is only AA→CM).

**Notes / gotchas:** The CM's `PRM_AncillaryAssessment__c` lookup is `null` here. The relationship is one-directional in practice (AA→CM via `PRM_CaseManager__c`).

---

## Query 3 — Recent Cases on the account

**Object:** `Case`
**Use case:** Map open Cases to their CMs to confirm no duplicate PSV cases are open.

```sql
SELECT Id, CaseNumber, Type, Status, AccountId, PRM_CaseManager__c,
       PRM_CaseManager__r.Name, CreatedDate
FROM Case
WHERE AccountId = '001UW00000ejn1SYAQ'
ORDER BY CreatedDate DESC LIMIT 10
```

**Sample result:** 3 rows — one PSV / In Progress (`00205898`, CM `IA-0000152008`), two Network Management QC / New (older).

---

## Query 4 — Account snapshot

**Object:** `Account`
**Use case:** Confirm Account `PRM_ParticipationStatus__c` and `PRM_CredentialingStatus__c` are consistent with an active credentialing review (so the "in-flight" scenario is valid).

```sql
SELECT Id, Name, RecordTypeId, PRM_ParticipationStatus__c,
       PRM_CredentialingStatus__c, CreatedDate
FROM Account
WHERE Id = '001UW00000ejn1SYAQ'
```

**Sample result:** *Complete Care At Lakeview Llc* — `RecordTypeId=PRM_Vendor`, `PRM_ParticipationStatus__c='Participating'`, `PRM_CredentialingStatus__c='Credentialing In Progress'`.

---

## Query 5 — Find every account that already has duplicate Ancillary Assessments

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** Quantify how widespread the "duplicate AA per Provider Type" problem is across the org — drives prioritisation of the data-migration plan.

```sql
SELECT PRM_Account__c, PRM_ProviderTypeService__c, COUNT(Id) total
FROM PRM_AncillaryAssessment__c
WHERE PRM_Account__c != null
GROUP BY PRM_Account__c, PRM_ProviderTypeService__c
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
LIMIT 200
```

**Sample result:** *(run in sandbox once approved — to be filled in)*
**Notes / gotchas:** This is the population that will need merging once the design is approved. Migration plan must preserve the earliest `PRM_ReAssessmentDueDate__c` and concat audit notes.

---

## Query 6 — Reassessment due date distribution (for the 1-year threshold sanity check)

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** How many records would be touched by the **Scenario 2a** (update to +3 yrs) vs **Scenario 2b** (preserve) branches in production today.

```sql
SELECT
  CASE WHEN PRM_ReAssessmentDueDate__c <= NEXT_N_DAYS:365 THEN 'within_1yr'
       WHEN PRM_ReAssessmentDueDate__c > NEXT_N_DAYS:365 THEN 'beyond_1yr'
       ELSE 'null_or_past' END bucket,
  COUNT(Id) total
FROM PRM_AncillaryAssessment__c
WHERE PRM_ReAssessmentDueDate__c != null
GROUP BY CASE WHEN PRM_ReAssessmentDueDate__c <= NEXT_N_DAYS:365 THEN 'within_1yr'
              WHEN PRM_ReAssessmentDueDate__c > NEXT_N_DAYS:365 THEN 'beyond_1yr'
              ELSE 'null_or_past' END
```

**Notes / gotchas:** SOQL doesn't support CASE in SELECT directly — split into two count queries instead:

```sql
SELECT COUNT(Id) FROM PRM_AncillaryAssessment__c
WHERE PRM_ReAssessmentDueDate__c != null AND PRM_ReAssessmentDueDate__c <= NEXT_N_DAYS:365

SELECT COUNT(Id) FROM PRM_AncillaryAssessment__c
WHERE PRM_ReAssessmentDueDate__c > NEXT_N_DAYS:365
```
