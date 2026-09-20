# Ancillary NPI History — EffectiveFrom Stamping at Submission vs HACAC

**Date:** 2026-06-03
**Context:** Investigating whether `PRM_HealthcareFacilityNPI__c` (Location NPI History) `PRM_EffectiveFrom__c` is being stamped at Ancillary form submission. The concern is that for a brand‑new location the date should not be set until **after PDA Review/Update + HACAC approval**.

**Finding (code reference):** YES — at submission the trigger eagerly stamps `PRM_EffectiveFrom__c` from the parent `HealthCareFacility.PRM_EffectiveFrom__c`. See `PRM_HCFacilityTriggerHelper.createNPIRecords` (force-app/main/default/classes/PRM_HCFacilityTriggerHelper.cls, lines 182‑206), wired into `PRM_HCFacilityTriggerHandler.afterInsert` (line 51).

The `PRMUptLocationHistoryNPIForAncillary_1` DR called by `PRM_AncillaryPDA_Procedure_10` at HACAC approval uses formula `IF(ISBLANK(EffectiveFrom), HACACDecisionDate, EffectiveFrom)` — meaning HACAC only fills the date when blank, so it **never** overrides the submission‑time stamp.

---

## Query 1 — How many Ancillary submissions have eagerly stamped NPI History EffectiveFrom while still Pending

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** Find NPI history rows that were stamped with an EffectiveFrom at submission but are still Pending (i.e., HACAC has not yet approved).

```sql
SELECT Id,
       PRM_HealthcareFacility__r.Name,
       PRM_HealthcareFacility__r.AccountId,
       PRM_HealthcareProviderNPI__r.Npi,
       PRM_EffectiveFrom__c,
       PRM_Pending__c,
       PRM_Active__c,
       PRM_CaseManager__c,
       PRM_CaseManager__r.Stage__c,
       CreatedDate
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_Pending__c = true
  AND PRM_EffectiveFrom__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_AncillaryCaseManager'
  AND CreatedDate = LAST_N_DAYS:90
ORDER BY CreatedDate DESC
LIMIT 200
```

**Notes / gotchas:** Adjust `RecordType.DeveloperName` to whatever the org uses for ancillary case managers. Any non‑zero rowcount is evidence that submission is stamping the date before HACAC approval has run.

---

## Query 2 — Did HACAC keep the submission date or overwrite it? (sanity check on the formula gap)

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** For approved Ancillary NPI history rows, compare `PRM_EffectiveFrom__c` against the parent Case Manager's HACAC decision date. If they don't match, HACAC kept the submission‑time stamp instead of using the HACAC decision date.

> **SOQL limitation:** you cannot put `field1 != field2` in a `WHERE` clause — it returns `MALFORMED_QUERY: unexpected token`. Both sides of every comparison must include a literal, bind variable, or `null`. So this check has to be done in **anonymous Apex** (preferred) or with a 2‑step pure‑SOQL pattern that pins the HACAC date as a literal in step 2.

### 2a) Recommended — anonymous Apex with post‑filter

```apex
List<PRM_HealthcareFacilityNPI__c> rows = [
    SELECT Id,
           PRM_HealthcareFacility__r.Name,
           PRM_HealthcareProviderNPI__r.Npi,
           PRM_EffectiveFrom__c,
           PRM_CaseManager__c,
           PRM_CaseManager__r.PRM_HACACDecisionDate__c,
           PRM_CaseManager__r.Stage__c,
           CreatedDate
    FROM PRM_HealthcareFacilityNPI__c
    WHERE PRM_Pending__c = false
      AND PRM_Active__c  = true
      AND PRM_CaseManager__r.PRM_HACACDecisionDate__c != null
      AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_AncillaryCaseManager'
    ORDER BY CreatedDate DESC
    LIMIT 2000
];

Integer mismatch = 0;
for (PRM_HealthcareFacilityNPI__c r : rows) {
    if (r.PRM_EffectiveFrom__c != r.PRM_CaseManager__r.PRM_HACACDecisionDate__c) {
        mismatch++;
        System.debug(
            'MISMATCH | NPI=' + r.PRM_HealthcareProviderNPI__r.Npi +
            ' | Loc=' + r.PRM_HealthcareFacility__r.Name +
            ' | EffFrom=' + r.PRM_EffectiveFrom__c +
            ' | HACAC=' + r.PRM_CaseManager__r.PRM_HACACDecisionDate__c +
            ' | CM=' + r.PRM_CaseManager__c
        );
    }
}
System.debug('TOTAL approved ancillary NPI history rows scanned: ' + rows.size());
System.debug('TOTAL with EffFrom != HACAC decision date: ' + mismatch);
```

### 2b) Pure SOQL alternative — two queries

Step 1: pick a sample CM and note its HACAC date.

```sql
SELECT Id, PRM_HACACDecisionDate__c
FROM Case_Manager__c
WHERE PRM_HACACDecisionDate__c != null
  AND RecordType.DeveloperName = 'PRM_AncillaryCaseManager'
ORDER BY PRM_HACACDecisionDate__c DESC
LIMIT 5
```

Step 2: feed that pair (Id + date literal) back in:

```sql
SELECT Id, PRM_EffectiveFrom__c
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_CaseManager__c = '<CM_Id_from_step_1>'
  AND PRM_Pending__c = false
  AND PRM_Active__c  = true
  AND PRM_EffectiveFrom__c != <HACAC_date_from_step_1>   -- e.g. 2026-05-15
```

**Notes / gotchas:**
- Field name on Case Manager is `PRM_HACACDecisionDate__c` (verified by the user's `MALFORMED_QUERY` error — earlier draft of this file incorrectly omitted the `PRM_` prefix; that has been corrected).
- A non‑zero result from either approach proves the `IF(ISBLANK(EffectiveFrom), HACACDecisionDate, EffectiveFrom)` formula in `PRMUptLocationHistoryNPIForAncillary` never overwrote the eagerly‑stamped submission date for those rows.
- SOQL does not allow `field1 != field2`; cross‑field comparison requires Apex post‑filter or a literal pinned at query time.

---

## Query 3 — Find NPI history rows where EffectiveFrom is older than the parent Case Manager submission

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** Detect rows where `PRM_EffectiveFrom__c` was stamped before the Case Manager itself was created — a strong signal of "submission‑form date" rather than "HACAC date".

```sql
SELECT Id,
       PRM_HealthcareFacility__r.Name,
       PRM_HealthcareFacility__r.AccountId,
       PRM_EffectiveFrom__c,
       PRM_Pending__c,
       PRM_Active__c,
       PRM_CaseManager__c,
       PRM_CaseManager__r.CreatedDate,
       CreatedDate
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_CaseManager__c != null
  AND PRM_EffectiveFrom__c != null
  AND PRM_EffectiveFrom__c < DAY_ONLY(CreatedDate)
ORDER BY CreatedDate DESC
LIMIT 200
```

**Notes / gotchas:** Comparing a Date field to a DateTime requires `DAY_ONLY()`. This is a fast smoke test — if rows return, you have submission‑date stamping confirmed.

---

## Query 4 — Post‑fix verification: Ancillary NPI history rows that survived submission with `EffectiveFrom = null`

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** After the dev story `Ancillary_NPIHistory_EffectiveFrom_Fix_DevStory.md` ships and the feature flag `PRM_DeferAncillaryNPIHistEffFrom__c` is flipped on, this query proves the new behaviour: pending Ancillary NPI history rows should be created with `PRM_EffectiveFrom__c = null` and only get a date when HACAC approves.

```sql
SELECT Id,
       PRM_HealthcareFacility__r.Name,
       PRM_HealthcareProviderNPI__r.Npi,
       PRM_EffectiveFrom__c,
       PRM_Pending__c,
       PRM_Active__c,
       PRM_CaseManager__c,
       PRM_CaseManager__r.RecordType.DeveloperName,
       PRM_CaseManager__r.Stage__c,
       PRM_CaseManager__r.PRM_HACACDecisionDate__c,
       CreatedDate
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_Pending__c = true
  AND PRM_EffectiveFrom__c = null
  AND PRM_CaseManager__r.RecordType.DeveloperName IN ('PRM_AncillaryAssessment','PRM_AncillaryReAssessment')
  AND CreatedDate = LAST_N_DAYS:7
ORDER BY CreatedDate DESC
LIMIT 200
```

**Expected post‑fix result:** every newly created in‑flight Ancillary NPI history row appears here with `EffectiveFrom = null`. After HACAC runs, the same row should disappear from this query (because EffFrom is no longer null) and appear in Query 5 below.

---

## Query 5 — Post‑fix verification: Ancillary NPI history rows whose date matches HACAC decision date

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** After HACAC approval, every row should have `PRM_EffectiveFrom__c` exactly equal to the parent CM's `PRM_HACACDecisionDate__c`. This confirms the HACAC update DR (`PRMUptLocationHistoryNPIForAncillary_1`) is now the authoritative writer for new locations.

> **SOQL caveat (same as Query 2):** field‑to‑field comparison is not allowed in SOQL. Use the anonymous Apex below.

### Anonymous Apex

```apex
List<PRM_HealthcareFacilityNPI__c> rows = [
    SELECT Id,
           PRM_EffectiveFrom__c,
           PRM_Pending__c,
           PRM_Active__c,
           PRM_CaseManager__r.PRM_HACACDecisionDate__c,
           PRM_CaseManager__r.Stage__c,
           CreatedDate
    FROM PRM_HealthcareFacilityNPI__c
    WHERE PRM_Pending__c = false
      AND PRM_Active__c  = true
      AND PRM_CaseManager__r.PRM_HACACDecisionDate__c != null
      AND PRM_CaseManager__r.RecordType.DeveloperName IN ('PRM_AncillaryAssessment','PRM_AncillaryReAssessment')
      AND CreatedDate = LAST_N_DAYS:30
    ORDER BY CreatedDate DESC
    LIMIT 2000
];

Integer match = 0;
Integer drift = 0;
for (PRM_HealthcareFacilityNPI__c r : rows) {
    if (r.PRM_EffectiveFrom__c == r.PRM_CaseManager__r.PRM_HACACDecisionDate__c) match++;
    else                                                                          drift++;
}
System.debug('Total scanned: ' + rows.size() + ' | EffFrom == HACAC: ' + match + ' | drift: ' + drift);
```

**Expected post‑fix result:** `drift == 0` for any rows created after the flag flipped on. Pre‑fix legacy rows with drift are expected and are not touched by the new code (the backfill in §4.4 of the dev story handles still‑pending pre‑fix rows).
