# Duplicate QC Cases — Root Cause Analysis

**Date:** 2026-04-16
**Org Investigated:** Production & QA Sandbox (`qa-sandbox`)
**Example Application:** `IA-0000007040` (Kevin A Gall — Re-Credentialing)
**Reported By:** QA Investigation

---

## Summary

Duplicate `QC Review` cases are being created under Individual Applications with the
**Re-Credentialing** record type. Two cases with identical configuration (same
`PRM_CaseManager__c`, same `Type`, same owner queue) are inserted within seconds of
each other, causing both the round-robin assignment and the IA's `ApplicationCaseId`
to be set twice — resulting in one orphaned QC case that never gets properly resolved.

---

## Evidence

### Duplicate Cases on IA-0000007040 (QA)

| CaseNumber | Type | Status | CreatedDate (UTC) | Owner |
|---|---|---|---|---|
| 00043686 | QC Review | Closed | 2025-09-30T12:04:48 | Tomica Gordon |
| 00043687 | QC Review | Closed | 2025-09-30T12:04:52 | Stephanie P. Williams |

### Case History Pattern

Both cases show the same three history events fired within the same second:

1. `created` — by **Tiffany Carsello**
2. `Owner` reassigned from Tiffany Carsello → unique user (round-robin)
3. `Owner` Id updated (second round-robin event)

The round-robin assigning to **different owners** on each case proves two entirely
separate Case INSERT operations hit the database — this is not a sync/display artifact.

### Scale of the Problem (QA Sandbox)

Running `FindDuplicateQCCases.sh` against qa-sandbox identified **71 Individual
Applications** with duplicate QC cases created within the same minute window. In
production the two cases on the reported application were created **6 seconds apart**
(17:28:19 and 17:28:25).

---

## Case Creation Chain

The QC case creation is triggered by the **PSV Review OmniScript** when the reviewer
selects a `ReCredProceedTo` value (e.g. `PSV QC`) and clicks **Next/Submit**:

```
OmniScript: PRM_PrimarySourceVerificationReview (English v45)
    └── Element: IPUpdatePSVReviewUpdate  (Integration Procedure Action)
            ↓  calls (sendJSONPath: RecordsToUpdate)
    IP: PRM_ReviewRecredCaseRecordsUpdateParent  (Parent / exception wrapper)
            ↓  calls child IP
    IP: PRM_ReviewRecredCaseRecordsUpdate  (Procedure 1)
            ↓  element: DRCreateNewCase  (DataRaptor Post Action)
            ↓  bundle:  PRMRecredQCNewCase
                → INSERT Case { Type: "QC Review", Status: "New", ... }
```

---

## Root Causes

### Root Cause 1 — No double-submit guard on the OmniScript element (Primary)

The `IPUpdatePSVReviewUpdate` element in
`PRM_PrimarySourceVerificationReview_English_45` has its `show` condition configured
with a broad `OR` group:

```json
"show": {
  "group": {
    "operator": "OR",
    "rules": [
      { "field": "ProceedTo",      "condition": "=",  "data": "PSV QC" },
      { "field": "ProceedTo",      "condition": "=",  "data": "Medical Director Review" },
      { "field": "ProceedTo",      "condition": "=",  "data": "Return to App Review" },
      { "field": "QCProceedTo",    "condition": "<>", "data": null },
      { "field": "ReCredProceedTo","condition": "<>", "data": null }
    ]
  }
}
```

If the user clicks **Next or Submit twice** before the first IP call returns (e.g. slow
network, page lag), the OmniScript dispatches two separate calls to
`PRM_ReviewRecredCaseRecordsUpdateParent` in rapid succession. There is no in-flight
lock or disabled-state on the button while the IP executes.

### Root Cause 2 — No idempotency check in the Integration Procedure (Contributing)

`DRCreateNewCase` in `PRM_ReviewRecredCaseRecordsUpdate` fires whenever:

```
executionConditionalFormula:
  %RecordsToUpdate:ReCredProceedTo% = 'Medical Director Review'
  && ISNOTBLANK(%RecordsToUpdate:NewCase%)
```

There is **no pre-check** that queries for an already-open QC case on the same
`PRM_CaseManager__c` before inserting. If the IP is called twice with identical
input, two cases are created unconditionally.

### Root Cause 3 — DataRaptor PRMRecredQCNewCase is a pure INSERT (Contributing)

The `PRMRecredQCNewCase` DataRaptor bundle has no `upsertKey` configured — every
execution results in a brand-new `Case` record regardless of whether one already
exists for the IA in `New` or `In Progress` status.

---

## Impact

| Area | Effect |
|---|---|
| **QC Queue** | Two cases assigned to different reviewers for the same IA — wasted effort, duplicate work |
| **Round-Robin Logic** | The round-robin counter advances twice per IA instead of once |
| **IA Latest Case** | `ApplicationCaseId` on the IndividualApplication gets set to the last-created duplicate, leaving the earlier case orphaned |
| **Reporting** | Case volume metrics are inflated; duplicate closed cases skew SLA reports |

---

## Recommended Fixes

### Fix 1 — Disable the submit button while the IP executes (OmniScript — Quick Win)

In `PRM_PrimarySourceVerificationReview`, set a Set Values element immediately before
`IPUpdatePSVReviewUpdate` to write a `SubmitInProgress = true` flag, then add that
flag to the element's `executionConditionalFormula`:

```
executionConditionalFormula: NOT(%SubmitInProgress%)
```

Reset the flag in the post-action or on navigation. This prevents the second click
from firing a second IP call.

### Fix 2 — Add an idempotency check in the IP (Integration Procedure — Recommended)

Add a new `DRQueryExistingQCCase` DataRaptor Extract element **before** `DRCreateNewCase`
in `PRM_ReviewRecredCaseRecordsUpdate`:

```
DRQueryExistingQCCase:
  SELECT Id FROM Case
  WHERE PRM_CaseManager__c = %RecordsToUpdate:CaseManagerID%
    AND Type = 'QC Review'
    AND Status != 'Closed'
  LIMIT 1
```

Then update the `executionConditionalFormula` on `DRCreateNewCase`:

```
%RecordsToUpdate:ReCredProceedTo% = 'Medical Director Review'
&& ISNOTBLANK(%RecordsToUpdate:NewCase%)
&& ISBLANK(%DRQueryExistingQCCase:Id%)
```

This ensures a new QC case is only inserted when no active QC case exists on the IA.

### Fix 3 — Change PRMRecredQCNewCase to Upsert (DataRaptor — Longer Term)

Configure the `PRMRecredQCNewCase` DataRaptor to use an Upsert operation with
`PRM_CaseManager__c + Type` as a composite external key (requires a custom External ID
field or a junction-based approach). This makes the DataRaptor itself idempotent
regardless of how many times it is called.

---

## Detection Script

A shell script has been created to identify duplicate QC cases across any org and
upload the results to Salesforce Files:

```
scripts/FindDuplicateQCCases.sh <org-alias>
```

Output: `scripts/output/duplicate_qc_cases_<org>_<timestamp>.csv`
Salesforce File: uploaded automatically to the org's Files section with a direct URL.

The script flags cases where two or more QC cases (`QC Review` or
`Network Management QC`) share the same `PRM_CaseManager__c`, same `Type`, and were
created within the **same minute window**.

---

## Files Referenced

| File | Role |
|---|---|
| `force-app/.../omniScripts/PRM_PrimarySourceVerificationReview_English_45.os-meta.xml` | OmniScript — triggers the IP via `IPUpdatePSVReviewUpdate` element |
| `force-app/.../omniIntegrationProcedures/PRM_ReviewRecredCaseRecordsUpdateParent_Procedure_1.oip-meta.xml` | Parent IP — wraps child IP in a try-catch |
| `force-app/.../omniIntegrationProcedures/PRM_ReviewRecredCaseRecordsUpdate_Procedure_1.oip-meta.xml` | Child IP — contains `DRCreateNewCase` (the actual insert) |
| `force-app/.../omniDataTransforms/PRMRecredQCNewCase_1.rpt-meta.xml` | DataRaptor Post — performs the Case INSERT with no duplicate guard |
| `scripts/FindDuplicateQCCases.sh` | Detection script |
