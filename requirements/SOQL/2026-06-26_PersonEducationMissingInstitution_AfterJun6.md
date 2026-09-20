# PersonEducation Missing Institution — App Review Defect (cases after Jun 6)

**Date:** 2026-06-26
**Context:** Defect investigation — after the App Review (PAR) process, `PersonEducation` records are saved with `PRM_Institution__c = null`, which breaks NPDB (the NPDB "No Institution" / `G1` error). Business asked to quantify **this month's cases created after June 6, 2026**. Org: `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, 00DVB000009WnBh2AK).

**"Created through PAR / App Review" identification rule:**
- `PRM_CaseManager__c != null`
- `PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'`

---

## Query 1 — Offending PersonEducation rows (missing institution) after Jun 6

```sql
SELECT COUNT()
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate >= 2026-06-06T00:00:00Z
```

**Result (qa-sandbox, 2026-06-26):** **220 rows**

---

## Query 2 — Denominator: all PAR PersonEducation after Jun 6

```sql
SELECT COUNT()
FROM PersonEducation
WHERE PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate >= 2026-06-06T00:00:00Z
```

**Result:** **690 rows** → **220 / 690 = ~31.9% missing institution**

---

## Query 3 — Distinct PAR Case Managers affected after Jun 6

```sql
SELECT COUNT_DISTINCT(PRM_CaseManager__c) cms
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate >= 2026-06-06T00:00:00Z
```

**Result:** **125 distinct Case Managers**

---

## Query 4 — Stage breakdown after Jun 6

```sql
SELECT PRM_CaseManager__r.PRM_Stage__c stg, COUNT(Id) cnt
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate >= 2026-06-06T00:00:00Z
GROUP BY PRM_CaseManager__r.PRM_Stage__c
ORDER BY COUNT(Id) DESC
```

**Result:**

| Stage | Rows |
|-------|------|
| PSV | 125 |
| Application Review | 44 |
| Complete | 26 |
| Network Management QC | 19 |
| PDA Review and Update | 4 |
| Committee Review | 2 |

**Note:** 26 already finalized at "Complete" with no Institution → the NPDB-impacting rows.

---

## Query 5 — Sample most recent offending rows

```sql
SELECT PRM_CaseManager__r.Name, PRM_CaseManager__r.PRM_Stage__c, Name, PRM_Degree__c, CreatedDate
FROM PersonEducation
WHERE PRM_Institution__c = null
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND CreatedDate >= 2026-06-06T00:00:00Z
ORDER BY CreatedDate DESC
LIMIT 15
```

**Notes / gotchas:** Fresh rows still being created on 2026-06-26 (e.g. IA-0000154642, IA-0000154638, IA-0000154633) — confirms the defect is active, not legacy. `Name` shows the Degree label fallback that is stamped when Institution is blank.
