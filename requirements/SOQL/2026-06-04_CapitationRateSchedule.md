# Capitation Rate Schedule — Inspection Queries

**Date:** 2026-06-04
**Context:** Locate and inspect "capitation rate" data in the org. Note: Salesforce stores only the **Rate Schedule picklist code** (e.g. `PTH710`, `100000`) — not dollar PMPM amounts. Dollar rates live in the downstream IBC claims/payment platform. The rate schedule code maps to that external rate table.

The field `PRM_RateSchedule__c` exists on three objects:
- `PRM_Program__c` (master, ~60 values, filtered by `PRM_ProgramSubType__c`)
- `PRM_ProgramParticipation__c` (practitioner-level, required for CAP/CAPV)
- `PRM_HealthcareFacilityBundle__c` (bundle-level, Lab/Rad/PT subset)

---

## Query 1 — All capitated program participations with rate schedule code + label

**Object:** `PRM_ProgramParticipation__c`
**Use case:** Get every practitioner program participation that is capitated and see which rate schedule applies. `toLabel()` returns the human label (e.g. "TEMPLE PHYSICAL THERAPY") instead of the API code.

```sql
SELECT Id,
       Name,
       PRM_Program__r.Name,
       PRM_Program__r.PRM_ProgramType__c,
       PRM_Program__r.PRM_ProgramSubType__c,
       PRM_AgreementType__c,
       PRM_RateSchedule__c,
       toLabel(PRM_RateSchedule__c) RateScheduleLabel,
       PRM_Account__r.Name,
       PRM_EffectiveFrom__c,
       PRM_EffectiveTo__c
FROM   PRM_ProgramParticipation__c
WHERE  PRM_AgreementType__c IN ('Capitated','Both')
  AND  PRM_RateSchedule__c != null
ORDER BY PRM_Program__r.Name, PRM_Account__r.Name
LIMIT  500
```

**Notes / gotchas:**
- Validation rule `PRM_rateScheduledRequired` blocks save if `PRM_AgreementType__c` ∈ (`Capitated`,`Both`) on a `CAP/CAPV` program with blank rate schedule.
- `toLabel()` is the same lookup `PRM_OmniUtils.fetchProgramParticipationRateScheduleLabels` performs in Apex.

---

## Query 2 — All capitated Practice Location Bundles with their rate schedule

**Object:** `PRM_HealthcareFacilityBundle__c`
**Use case:** Inspect capitated bundles (typically Lab, Radiology, Physical Therapy) and their rate schedule.

```sql
SELECT Id,
       Name,
       PRM_BundleType__c,
       PRM_AgreementType__c,
       PRM_RateSchedule__c,
       toLabel(PRM_RateSchedule__c) RateScheduleLabel,
       PRM_HealthcareFacility__r.Name,
       PRM_ServiceType__c,
       PRM_EffectiveFrom__c,
       PRM_EffectiveTo__c
FROM   PRM_HealthcareFacilityBundle__c
WHERE  PRM_BundleType__c = 'Capitated Bundle'
  AND  PRM_RateSchedule__c != null
ORDER BY PRM_HealthcareFacility__r.Name
LIMIT  500
```

**Notes / gotchas:**
- Bundle-level picklist values are a **subset** of the program-participation set — Lab (`LAB*`), Radiology (`RAD*`), Physical Therapy (`PTH*`, `DPTH01`, `NPTH00`) only.

---

## Query 3 — Programs and their allowed Rate Schedule (master view)

**Object:** `PRM_Program__c`
**Use case:** See which rate schedule each Program record currently carries. Useful for picklist audit + program setup verification.

```sql
SELECT Id,
       Name,
       PRM_ProgramType__c,
       PRM_ProgramSubType__c,
       PRM_RateSchedule__c,
       toLabel(PRM_RateSchedule__c) RateScheduleLabel
FROM   PRM_Program__c
WHERE  PRM_ProgramType__c IN ('CAP','CAPV')
ORDER BY PRM_ProgramSubType__c, Name
LIMIT  500
```

**Notes / gotchas:**
- `PRM_RateSchedule__c` on `PRM_Program__c` is the **controlled picklist** (sub-type filters it). The other two objects pull their valid values from the same value set but apply their own filters in the OmniScripts.

---

## Query 4 — Rate Schedule change history (audit)

**Object:** `PRM_ProgramParticipation__History`
**Use case:** Who changed the rate schedule, when, from what → to what. Field is history-tracked on all three objects.

```sql
SELECT Id,
       ParentId,
       Parent.Name,
       Field,
       OldValue,
       NewValue,
       CreatedDate,
       CreatedBy.Name
FROM   PRM_ProgramParticipation__History
WHERE  Field = 'PRM_RateSchedule__c'
  AND  CreatedDate = LAST_N_DAYS:90
ORDER BY CreatedDate DESC
LIMIT  500
```

**Notes / gotchas:**
- History rows store **API codes**, not labels — re-run `toLabel()` against the field (or use the Rate Schedule Field Analysis doc) to translate.
- Same query works against `PRM_Program__History` and `PRM_HealthcareFacilityBundle__History` by swapping the object name.

---

## Query 5 — Distinct rate schedule codes currently in use (with counts)

**Object:** `PRM_ProgramParticipation__c`
**Use case:** Find unused or rarely-used picklist values before deprecation; sanity-check a recent picklist update.

```sql
SELECT PRM_RateSchedule__c,
       toLabel(PRM_RateSchedule__c) RateScheduleLabel,
       COUNT(Id) ParticipationCount
FROM   PRM_ProgramParticipation__c
WHERE  PRM_RateSchedule__c != null
GROUP BY PRM_RateSchedule__c
ORDER BY COUNT(Id) DESC
LIMIT  100
```

**Notes / gotchas:**
- `GROUP BY` with `toLabel()` requires it in a SELECT alias; some orgs require ordering by the API value column instead. If aggregate fails, drop `toLabel(...)` and translate after.

---

## Cross-references

- Full architectural map: `requirements/RateSchedule/RateSchedule_Field_Analysis.md`
- Recent picklist label changes: `requirements/RateSchedule/RateSchedule_Picklist_Update_UserStories.md`
- Apex code-to-label converter: `PRM_OmniUtils.fetchProgramParticipationRateScheduleLabels`, `PRM_OmniUtils.getProgramMappedData`
- Bundle taxonomy display: `PRM_GetBundleDetailsService`
