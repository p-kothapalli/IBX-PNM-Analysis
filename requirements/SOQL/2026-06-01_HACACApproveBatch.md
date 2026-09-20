# HACAC Committee – Approve Batch Workaround

**Date:** 2026-06-01
**Context:** The HACAC Committee Report (`PRM_ReviewHACAC_English` OmniScript →
`PRM_DataRetrievalforHAPACCommitteeReview` IP) is hitting SOQL 101 when 28+
case managers are eligible. Until the IP / DataRaptor Extracts are made
bulk-safe, we apply committee Approve decisions in batch via anonymous Apex
(`scripts/HACACApproveCaseManagers.apex`). These are the queries that script
runs (and the ad-hoc SOQL the committee can use to pull the 28 IDs).

---

## Query 1 — Pull the eligible HACAC case managers (for the script input)

**Object:** `IndividualApplication`
**Use case:** Identify the 28 case managers currently sitting in the HACAC
committee review bucket so we can paste their IDs into
`scripts/HACACApproveCaseManagers.apex`.

```sql
SELECT Id, Name, Account.Name, Status, PRM_Stage__c,
       RecordType.DeveloperName, PRM_HACACDecisionDate__c,
       PRM_DecisionDueDate__c, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_AncillaryAssessment', 'PRM_AncillaryReAssessment')
  AND Status != 'Approved'
  AND PRM_Stage__c = 'HACAC Review'
ORDER BY PRM_DecisionDueDate__c ASC
```

**Sample result / row count:** ~28 rows as of 2026-06-01 (the batch
triggering the SOQL 101 failure).
**Notes / gotchas:**
- Validate the `PRM_Stage__c` value against the actual HACAC eligibility
  picklist value in your org — adjust if the bucket is named differently
  (e.g. `'HACAC Committee Review'`).
- If the script's pre-filter `Status != 'Approved'` is too narrow, drop it.

---

## Query 2 — Load the case managers being processed (inside the script)

**Object:** `IndividualApplication`
**Use case:** Inside `HACACApproveCaseManagers.apex`, hydrate the Account
and current state for the input Ids. Skips anything already Approved.

```sql
SELECT Id, Name, AccountId, Status, PRM_Stage__c,
       PRM_HACACDecisionDate__c, ApplicationCaseId,
       RecordType.DeveloperName
FROM IndividualApplication
WHERE Id IN :caseManagerIds
  AND Status != 'Approved'
```

**Notes / gotchas:** This is 1 SOQL regardless of N case managers.

---

## Query 3 — Load related Ancillary Assessment records (inside the script)

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** Mirrors the IP's `PRMDRHACACExtractAncillaryAssessmentForReAssessment`
DataRaptor — fetch every assessment belonging to the affected Accounts so we
can stamp `PRM_ReAssessmentDueDate__c = approvedDate + 3 years` on them in
one DML.

```sql
SELECT Id, PRM_Account__c, PRM_CaseManager__c, PRM_ReAssessmentDueDate__c
FROM PRM_AncillaryAssessment__c
WHERE PRM_Account__c IN :accountIds
```

**Notes / gotchas:**
- Linkage is by `PRM_Account__c`, not `PRM_CaseManager__c`, matching the IP's
  `PRMDRHACACUpdateAccountAndAncillaryAssessment` behavior. If two case
  managers share an account, all of the account's assessments get the same
  new due date — same as the OmniScript path.
- 1 SOQL regardless of N accounts.

---

## Total footprint

| Step | SOQL | DML |
|------|------|-----|
| Load case managers | 1 | 0 |
| Load assessments | 1 | 0 |
| Insert `Case` per CM | 0 | 1 |
| Update `IndividualApplication` | 0 | 1 |
| Update `PRM_AncillaryAssessment__c` | 0 | 1 |
| Update `Account` to Participating | 0 | 1 |
| Insert `ContentNote` (`'HACAC - Approved'`) per CM | 0 | 1 |
| Insert `ContentDocumentLink` per CM (links note → IndApp) | 0 | 1 |
| **Total per chunk** | **2** | **6** |

So even with one chunk holding all 28 cases, we sit at ~2 SOQL + 6 DML —
well under the 100 SOQL / 150 DML limits — versus the IP path that detonates
at 28 records.

The two ContentNote-related DMLs mirror `PRM_OmniUtils.createNoteMulti`
(invoked by the IP's `RACreateNote` Remote Action) so the committee's audit
trail on the IndividualApplication record matches what the OmniScript would
have produced. The script uses a boilerplate note body — if you have per-CM
notes from the committee, paste them into the script and replace the
`noteContent` builder.
