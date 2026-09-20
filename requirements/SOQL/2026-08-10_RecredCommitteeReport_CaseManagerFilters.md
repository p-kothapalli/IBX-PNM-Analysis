# Recred Committee Report — Case Manager Filters

**Date:** 2026-08-10
**Context:** Document which Case Manager (`IndividualApplication`) filters determine whether a recred case appears on the Recred / Routine Credentialing Committee Report (LWC `prmCommitteeReview` → `PRM_CommitteeReview.getCommiteeRecordsForLwc` → `PRM_CommitteeReviewHelper.queryCaseManagers`).

**Source:** `PRM_CommitteeReviewHelper.cls` ReCred branch (`caseRecTypeName == 'PRM_ReCredentialing'`). Stage is hard-coded as `Committee Review` by the LWC entry point.

---

## Query 1 — Recred Committee Report eligibility

**Object:** `IndividualApplication` (Case Manager)
**Use case:** Which recred Case Managers show on the Recred Committee Report.

```sql
SELECT Id, Name, Status, PRM_Stage__c, PRM_RoutineCommittee__c,
       PRM_CredentialingQC__c, PRM_Decision_Date__c, PRM_ProcessingStatus__c,
       AccountId, RecordType.DeveloperName
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND PRM_Stage__c = 'Committee Review'
  AND Status != 'Closed'
  AND Status != 'Additional Review Needed'
  AND PRM_CredentialingQC__c = false
  AND PRM_RoutineCommittee__c = true
  AND PRM_Decision_Date__c = null
  AND AccountId != null
  AND PRM_ProcessingStatus__c != 'In Progress'
LIMIT 500
```

**Notes / gotchas:**
- Runtime code uses `RecordTypeId` resolved from `PRM_ReCredentialing`, not `DeveloperName` in the SOQL string.
- Row limit comes from `PRM_CommitteStageLimit__mdt` (`Default.Record_Limit__c`); falls back to 500 if CMDT is missing (default attempt is 400).
- **Initial Cred** committee path is different: it also includes ReCred Case Managers where `PRM_CredentialingQC__c = true` (converted recred → initial cred). Pure Recred report requires `PRM_CredentialingQC__c = false`.
- Related: `requirements/SOQL/2026-08-04_InitialCredCommitteeReportVsGuidedFlow.md`
