# Re-Assessment Cases Past Due (Re-Cred Due Jan–Jul 2026)

**Date:** 2026-06-26
**Context:** Report of Ancillary re-assessment "cases" that are **past due**, where the Re-Assessment Due Date (the "recred due date" the business refers to) falls between **Jan 2026 and Jul 2026**. The due date lives on the `PRM_AncillaryAssessment__c` record (`PRM_ReAssessmentDueDate__c`). The case/provider is reached via `PRM_Account__c` (and optionally the `IndividualApplication` Case Manager via `PRM_CaseManager__c`).

---

## Query 1 — Past-due re-assessments with due date Jan–Jul 2026

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** Pull every ancillary re-assessment whose Re-Assessment Due Date is in the Jan 1 – Jul 31, 2026 window and is already past due (due date earlier than today).

```sql
SELECT Id, Name,
       PRM_ProviderTypeService__c,
       PRM_ReAssessmentDueDate__c,
       RecordType.DeveloperName,
       PRM_Account__c, PRM_Account__r.Name,
       PRM_CaseManager__c, PRM_CaseManager__r.Name, PRM_CaseManager__r.Status
FROM PRM_AncillaryAssessment__c
WHERE PRM_ReAssessmentDueDate__c >= 2026-01-01
  AND PRM_ReAssessmentDueDate__c <= 2026-07-31
  AND PRM_ReAssessmentDueDate__c < TODAY
ORDER BY PRM_ReAssessmentDueDate__c ASC, PRM_Account__r.Name ASC
```

**Sample result / row count (if known):** 283 rows in `qa-sandbox` as of 2026-06-26.
**Notes / gotchas:**
- "Recred due date" in the request = `PRM_ReAssessmentDueDate__c` (Date) on the assessment, NOT `IndividualApplication.PRM_ReCredDueDate__c` (a separate field that was null on the sampled records).
- `PRM_ReAssessmentDueDate__c < TODAY` enforces "past due"; because today (2026-06-26) is before Jul 31, the `<= 2026-07-31` bound is effectively redundant but kept to honor the stated Jan–Jul window. Drop the `< TODAY` line if you want the full window including not-yet-due dates through July.
- On the sampled data the assessments are linked to the provider via `PRM_Account__c`; `PRM_CaseManager__c` (→ `IndividualApplication`) was null, so Case Manager columns may be blank.

---

## Query 2 — Count only

**Object:** `PRM_AncillaryAssessment__c`
**Use case:** Quick total for the same filter.

```sql
SELECT COUNT()
FROM PRM_AncillaryAssessment__c
WHERE PRM_ReAssessmentDueDate__c >= 2026-01-01
  AND PRM_ReAssessmentDueDate__c <= 2026-07-31
  AND PRM_ReAssessmentDueDate__c < TODAY
```

**Sample result / row count (if known):** 283 (qa-sandbox, 2026-06-26).
