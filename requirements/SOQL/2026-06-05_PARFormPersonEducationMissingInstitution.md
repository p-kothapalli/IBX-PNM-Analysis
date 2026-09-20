# PAR Form PersonEducation — Records Created Without PRM_Institution__c

**Date:** 2026-06-05
**Context:** Business asked how many PersonEducation records were created through the PAR form (App Review process) without `PRM_Institution__c` populated. This is the validation gap called out in AC1 of the PAR App Review PersonEducation user story — the system should block save when `PRM_Institution__c`, `PRM_StartDate__c`, or `PRM_EndDate__c` is missing, and the count below shows how many rows have slipped through historically in QA.

**Identification rule for "created through the PAR form":**
- `PRM_CaseManager__c != null`
- `PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'`

This is the PAR App Review CaseManager record type (confirmed via `customMetadata/PRM_RoundRobinCaseAssignment.ParAppReview.md-meta.xml`).

**Org tested:** `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, 00DVB000009WnBh2AK)

---

## Query 1 — TOTAL PAR PersonEducation rows with NULL PRM_Institution__c

**Object:** `PersonEducation`
**Use case:** Headline number for the business — total all-time count of PAR-created PersonEducation rows that bypassed the Institution requirement.

```sql
SELECT COUNT()
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
```

**Result (QA, 2026-06-05):** **6,929 rows**
**Notes / gotchas:** `PersonEducation` is a standard SF object; `PRM_Institution__c` is a custom lookup to `PRM_Institution__c` custom object. `PRM_CaseManager__c` is the PNM-specific lookup from `PersonEducation` back to the case (see `PersonEducation-Person Education Layout.layout-meta.xml` line 102).

---

## Query 2 — Denominator: all PAR-created PersonEducation (regardless of Institution)

**Object:** `PersonEducation`
**Use case:** Compute the gap percentage (Query 1 / Query 2).

```sql
SELECT COUNT()
FROM PersonEducation
WHERE PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
```

**Result (QA, 2026-06-05):** **28,298 rows** → **24.5% of PAR PersonEducation rows are missing Institution**

---

## Query 3 — Recency: last 12 months and last 90 days

**Object:** `PersonEducation`
**Use case:** Show that the issue is still occurring (not just a one-time historical data load).

```sql
-- last 12 months
SELECT COUNT()
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate = LAST_N_DAYS:365

-- last 90 days
SELECT COUNT()
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate = LAST_N_DAYS:90
```

**Results (QA, 2026-06-05):**
- Last 365 days: **6,794 rows** (≈98% of the total — overwhelmingly a recent / ongoing problem)
- Last 90 days: **2,209 rows** (~24 rows/day average)

---

## Query 4 — Yearly trend

**Object:** `PersonEducation`
**Use case:** Confirm trajectory year-over-year.

```sql
SELECT CALENDAR_YEAR(CreatedDate) yr, COUNT(Id) cnt
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
GROUP BY CALENDAR_YEAR(CreatedDate)
ORDER BY CALENDAR_YEAR(CreatedDate)
```

**Result (QA, 2026-06-05):**

| Year | Rows |
|------|------|
| 2025 | 3,202 |
| 2026 | 3,727 (through Jun 5) |

---

## Query 5 — Breakdown by Case Manager Stage

**Object:** `PersonEducation`
**Use case:** Show where in the workflow these bad rows are sitting. Anything in `Complete` is a real downstream data-quality issue (record finalized without Institution).

```sql
SELECT PRM_CaseManager__r.PRM_Stage__c stg, COUNT(Id) cnt
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
GROUP BY PRM_CaseManager__r.PRM_Stage__c
ORDER BY COUNT(Id) DESC
```

**Result (QA, 2026-06-05):**

| Stage | Rows |
|-------|------|
| Complete | 3,003 |
| Application Review | 1,468 |
| Network Management QC | 1,269 |
| PSV | 746 |
| QC Review | 342 |
| PDA Review and Update | 94 |
| Committee Review | 7 |

**Notes / gotchas:** ~43% (3,003 / 6,929) finalized at "Complete" — i.e. they made it through every downstream gate with no Institution. Strong evidence the AC1 validation needs to be enforced server-side.

---

## Query 6 — Sample 5 most recent offending rows (verification)

**Object:** `PersonEducation`
**Use case:** Pull a handful so business can spot-check.

```sql
SELECT Id, Name, ContactId, PRM_CaseManager__c, PRM_CaseManager__r.Name,
       PRM_CaseManager__r.PRM_Stage__c, PRM_Degree__c, PRM_Status__c, CreatedDate
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
ORDER BY CreatedDate DESC
LIMIT 5
```

**Result (QA, 2026-06-05 — latest):**

| PersonEducation Id | Name | Case Manager | Stage | CreatedDate |
|---|---|---|---|---|
| 0SrVB000000Mq1e0AC | Doctor of Divinity (DD) | IA-0000152339 | PSV | 2026-06-04 20:57 UTC |
| 0SrVB000000Mq1c0AC | Master of Science (MS) | IA-0000152339 | PSV | 2026-06-04 20:57 UTC |
| 0SrVB000000Mq020AC | Doctor of Divinity (DD) | IA-0000152337 | PSV | 2026-06-04 20:54 UTC |
| 0SrVB000000Mq000AC | Master of Science (MS) | IA-0000152337 | PSV | 2026-06-04 20:54 UTC |
| 0SrVB000000Mpv70AC | Advanced Practice Registered Nurse | IA-0000152338 | Application Review | 2026-06-04 20:35 UTC |

**Notes / gotchas:** New rows still being created without Institution as of yesterday. `Name` shows the Degree fallback that's getting stamped when Institution is blank.

---

## TL;DR for the business

- **6,929** PAR PersonEducation records in QA were created without `PRM_Institution__c`.
- That's **~24.5%** of all PAR-created PersonEducation rows (6,929 / 28,298).
- **~98% of them are from the last 12 months** and **~32% from the last 90 days** — this is an active, recurring issue, not legacy data.
- **~43% finalized at "Complete" stage** with no Institution — confirms there is no downstream gate stopping it.
- The AC1 validation in the user story (block save when `PRM_Institution__c`, `PRM_StartDate__c`, or `PRM_EndDate__c` is missing or invalid) is justified by these numbers.
