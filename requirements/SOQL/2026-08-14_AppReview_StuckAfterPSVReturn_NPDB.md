# App Review Stuck After PSV Return — NPDB / Pending NPDB Diagnostic

**Date:** 2026-08-14
**Context:** Cases that PSV returned to Application Review can’t be moved back to PSV. Investigating whether a second NPDB report is (or should be) created on the re-run, and whether `Case.Status = 'Pending NPDB'` is being set on the returned App Review case (which strands it because no new NPDB report will ever arrive from MuleSoft).

Findings from the codebase (see chat context 2026-08-14):

- `PRM_CredentialAppReviewCompleteOS_English_5` (active OS) — `SetProceedToPSVRecordUpdate` writes `Case.Status = 'Pending NPDB'` and `IndividualApplication.PRM_Stage__c = 'PSV'` unconditionally on the “Proceed to PSV” path.
- `IPCreateAdverseActionLogs` → `PRM_CreateAdverseActionLog_Procedure_9` is idempotent: every `PRMDRCreateAdverseActionLog*` step has `executionConditionalFormula = ISBLANK(%PRMDRExtractAdverseActionLog:AdverseActionLog|1:Id%)`. `PRMDRExtractAdverseActionLog_1` looks up any AAL on the Case Manager (LIMIT 1, no status filter) — so a second pass through App Review does **not** insert a new AAL and does **not** fire a new NPDB request.
- The return-path picklist (`AppReviewReturnedResultsWithoutQC` with the “Return to PSV” option) is only visible when `CaseDetails.Status = 'Returned'`. But `PRM_CaseManagerReturnToController.submitReturnRequest` creates the new App Review case with `newCase.Status = 'New'` — so the reviewer sees the first-time `AppReviewResults` (“Proceed to PSV”) instead, and `SetProceedToPSVRecordUpdate` fires (writing `Case.Status = 'Pending NPDB'` again). No new NPDB report is created, and MuleSoft therefore never clears `Pending NPDB` / never advances the stage → stuck.

---

## Query 1 — Find CMs stuck in App Review with an already-completed NPDB report

**Object:** `IndividualApplication` (joined to `PRM_AdverseActionLog__c` and `Case`)
**Use case:** Identify the exact population the business is describing — Case Managers currently sitting in `Application Review` whose most recent App Review `Case.Status = 'Pending NPDB'`, but for which an NPDB `PRM_AdverseActionLog__c` has already completed (i.e., MuleSoft is not going to send another callback).

```sql
SELECT Id,
       Name,
       PRM_Stage__c,
       Status,
       ApplicationCaseId,
       ApplicationCase.Type,
       ApplicationCase.Status,
       ApplicationCase.CreatedDate,
       (SELECT Id, PRM_Status__c, PRM_ResponseCode__c, CreatedDate, LastModifiedDate
        FROM PRM_AdverseActionLogs__r
        ORDER BY LastModifiedDate DESC),
       (SELECT Id, Type, Status, CreatedDate
        FROM Cases
        WHERE Type = 'Application Review'
        ORDER BY CreatedDate DESC LIMIT 3)
FROM IndividualApplication
WHERE PRM_Stage__c = 'Application Review'
  AND ApplicationCase.Type = 'Application Review'
  AND ApplicationCase.Status = 'Pending NPDB'
  AND Id IN (
      SELECT PRM_CaseManager__c FROM PRM_AdverseActionLog__c
      WHERE PRM_Status__c IN ('Success', 'Completed', 'Successful', 'Complete')
  )
ORDER BY LastModifiedDate DESC
LIMIT 500
```

**Notes / gotchas:**
- Confirm the AAL success picklist values in the target org (`PRM_Status__c` uses picklist values like `Ready To Process`, `In Progress`, `Success`/`Completed`, `Error`). Widen or narrow `IN` accordingly.
- Child relationship name `PRM_AdverseActionLogs__r` is the standard convention — verify against `PRM_AdverseActionLog__c.PRM_CaseManager__c`'s `relationshipName`.
- `ApplicationCase` is the lookup from IA to Case (`ApplicationCaseId`).

---

## Query 2 — Confirm no duplicate AAL is being created on the re-run

**Object:** `PRM_AdverseActionLog__c`
**Use case:** Prove the idempotency guard is actually holding — expect ONE AAL per Case Manager for the stuck population; if any CM has >1 AAL, the guard broke and a second NPDB request went out.

```sql
SELECT PRM_CaseManager__c,
       COUNT(Id) totalAALs,
       MAX(CreatedDate) latestAAL,
       MIN(CreatedDate) firstAAL
FROM PRM_AdverseActionLog__c
WHERE PRM_CaseManager__c IN (
    SELECT Id FROM IndividualApplication
    WHERE PRM_Stage__c = 'Application Review'
      AND ApplicationCase.Type = 'Application Review'
      AND ApplicationCase.Status = 'Pending NPDB'
)
GROUP BY PRM_CaseManager__c
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
LIMIT 200
```

**Expected result:** 0 rows. If rows come back, the DR guard has been bypassed on some code path and duplicate NPDB requests DID go out.

---

## Query 3 — Confirm the Case created by `PRM_CaseManagerReturnToController` is `Status = 'New'` (not `'Returned'`)

**Object:** `Case`
**Use case:** Verify the OmniScript visibility hypothesis — the return-from-PSV new App Review case has `Status = 'New'`, so the OmniScript shows `AppReviewResults` (first-time picklist) instead of `AppReviewReturnedResultsWithoutQC` (return-path picklist).

```sql
SELECT Id,
       CaseNumber,
       Type,
       Status,
       PRM_CaseManager__c,
       PRM_CaseManager__r.PRM_Stage__c,
       CreatedDate,
       CreatedBy.Name
FROM Case
WHERE Type = 'Application Review'
  AND PRM_CaseManager__c IN (
      SELECT PRM_CaseManager__c FROM ContentDocumentLink
      WHERE ContentDocument.Title IN ('QC Return to App Review', 'PSV Return to App Review')
  )
ORDER BY CreatedDate DESC
LIMIT 200
```

**Notes:** The `ContentNote` titles `QC Return to App Review` / `PSV Return to App Review` are inserted by `PRM_CaseManagerReturnToController.createNoteMulti` — they’re a reliable fingerprint for CMs that came back through the LWC return path. **Expected:** every row has `Status = 'New'`. If any row has `Status = 'Returned'`, there’s a second/alternate return path we need to find.

---

## Query 4 — Check if any of these stuck CMs are actually blocked by NPDB T-180 validation (missing data)

**Object:** `IndividualApplication`
**Use case:** Distinguish the two failure modes — (a) `SetProceedToPSVRecordUpdate` never fired because NPDB validators returned Error (missing address/NPI/license), vs (b) it fired but `Case.Status = 'Pending NPDB'` is now stuck with no MuleSoft callback coming.

```sql
SELECT Id, Name, PRM_Stage__c, Status,
       ApplicationCase.Status,
       PRM_NPDBValidationDetails__c
FROM IndividualApplication
WHERE PRM_Stage__c = 'Application Review'
  AND ApplicationCase.Type = 'Application Review'
  AND ApplicationCase.Status IN ('Pending NPDB', 'NPDB Action Needed', 'New', 'In Progress')
  AND Id IN (
      SELECT PRM_CaseManager__c FROM PRM_AdverseActionLog__c
      WHERE PRM_Status__c IN ('Success', 'Completed', 'Successful', 'Complete')
  )
ORDER BY LastModifiedDate DESC
LIMIT 300
```

**Notes:** `PRM_NPDBValidationDetails__c` (long text) is written by the T-180 validator; empty means data is clean. If populated, the reviewer is being blocked pre-submit by NPDB Action Needed logic. `PRM_NPDBValidationDetails__c` only exists on orgs where NPDB T-180 (`requirements/NPDB_T180/`) is deployed.
