# Location NPI History Wrongly Termed on PDA Review (BUG 1491213)

**Date:** 2026-09-08
**Context:** BUG 1491213 — when PDA Review is submitted for PAR / Off-Cycle requests, the Location
NPI History (`PRM_HealthcareFacilityNPI__c`) for the Practice Location is being termed/deactivated.
These queries were run against the QA sandbox (`prashanth.kothapalli@ibx.com.pie.qa`) to size the
blast radius and identify which request types produce the bad state.

---

## Query 1 — Records with no Effective From

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** The Off-Cycle PDA load DataMapper derives Active from `PRM_EffectiveFrom__c`; any row
with a blank Effective From is forced inactive. This sizes that population.

```sql
SELECT COUNT(Id) total
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_EffectiveFrom__c = null
```

**Sample result / row count:** 3,305 rows in QA (only 6 of them still Active).
**Notes / gotchas:** Most blank-Effective-From rows are `PRM_Pending__c = true` newly-created rows
that are inactive by design — filter on `PRM_Pending__c = false` to exclude those.

---

## Query 2 — The bug fingerprint: rows that should be Active but are not

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** A record that started on or before today, has no term date, and is not pending, must be
Active. Anything matching this filter has been wrongly termed.

```sql
SELECT COUNT(Id) total
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_Active__c = false
  AND PRM_Pending__c = false
  AND PRM_EffectiveFrom__c != null
  AND PRM_EffectiveFrom__c <= TODAY
  AND PRM_EffectiveTo__c = null
```

**Sample result / row count:** 261 rows in QA.
**Notes / gotchas:** This is the cleanest reproduction signal — use it as the before/after check when
validating a fix, and as the source list for any data-fix executor.

---

## Query 3 — Bug fingerprint grouped by originating request type

**Object:** `PRM_HealthcareFacilityNPI__c` (via `PRM_CaseManager__r` → `IndividualApplication`)
**Use case:** Confirms which PDA flows produce the wrongly-termed rows.

```sql
SELECT PRM_CaseManager__r.RecordType.DeveloperName rt, COUNT(Id) c
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_Active__c = false
  AND PRM_Pending__c = false
  AND PRM_EffectiveFrom__c != null
  AND PRM_EffectiveFrom__c <= TODAY
  AND PRM_EffectiveTo__c = null
GROUP BY PRM_CaseManager__r.RecordType.DeveloperName
ORDER BY COUNT(Id) DESC
```

**Sample result / row count (QA):**

| Case Manager Record Type | Count |
|---|---|
| `PRM_PDMManualChange` | 93 |
| (null — no Case Manager) | 69 |
| `PRM_PractitionerParticipationRequest` (PAR) | 44 |
| `PRM_OffCycleRequest` | 30 |
| `PRM_NonParClaimsRequest` | 19 |
| `PRM_NonParticipationRequest` | 3 |
| `PRM_AncillaryAssessment` | 3 |

**Notes / gotchas:** PAR + Off-Cycle = 74 rows, which is the population called out in the bug. The
`PRM_PDMManualChange` rows come through a different DataMapper (`PRMDRUpdateNPIHistory`) and should
be triaged separately.

---

## Query 4 — Field history: who/what flipped the flag

**Object:** `PRM_HealthcareFacilityNPI__History`
**Use case:** Distinguishes a legitimate term (Active and Effective To written in the same
transaction) from the bug (Active flipped on its own, with no term date written).

```sql
SELECT ParentId, Field, OldValue, NewValue, CreatedDate, CreatedBy.Name
FROM PRM_HealthcareFacilityNPI__History
WHERE Field = 'PRM_Active__c'
  AND CreatedDate = LAST_N_DAYS:30
ORDER BY CreatedDate DESC
```

```sql
SELECT ParentId, OldValue, NewValue, CreatedDate, CreatedBy.Name
FROM PRM_HealthcareFacilityNPI__History
WHERE Field = 'PRM_EffectiveTo__c'
  AND CreatedDate = LAST_N_DAYS:30
ORDER BY CreatedDate DESC
```

**Sample result / row count:** Last 30 days in QA — `PRM_CaseManager__c` 4,632 changes,
`PRM_Active__c` 608, `PRM_EffectiveTo__c` 534, `PRM_Pending__c` 193, `PRM_EffectiveFrom__c` 49.
**Notes / gotchas:** Field history is tracked on this object (477,145 rows total), so it is the best
forensic source. Compare timestamps to the second — a legitimate PDM Manual Change term writes both
`PRM_Active__c` and `PRM_EffectiveTo__c` at the identical timestamp; the Off-Cycle bug writes
`PRM_Active__c` alone.
