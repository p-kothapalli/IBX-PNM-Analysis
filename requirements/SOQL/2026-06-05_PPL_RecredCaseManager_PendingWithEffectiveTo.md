# PPL (Practitioner Practice Location) — Re-Credentialing Case Manager, Effective To set but still Pending

**Date:** 2026-06-05
**Context:** Identify Practitioner Practice Location (PPL) records that belong to a Re-Credentialing Case Manager and already have an Effective To (termination) date populated, yet the `PRM_Pending__c` flag is still checked. These represent records that should have completed processing but were left in a pending state.

---

## Data model notes

- **PPL** = `HealthcarePractitionerFacility` with `RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'` (the practitioner-at-practice-location affiliation).
- **Case Manager** = `IndividualApplication`, referenced via the `PRM_CaseManager__c` lookup on the PPL. Its record type is read through `PRM_CaseManager__r.RecordType.DeveloperName`.
- **Re-Credentialing record type** DeveloperName on the Case Manager = `PRM_ReCredentialing`.
- **Effective To date** = standard `EffectiveTo` field.
- **Pending flag** = `PRM_Pending__c` (Boolean).

---

## Query 1 — PPL records: Recred Case Manager + EffectiveTo set + still Pending

**Object:** `HealthcarePractitionerFacility`
**Use case:** Find PPL records tied to a Re-Credentialing Case Manager that have an Effective To date but whose Pending flag is still true.

```sql
SELECT Id, Name, PractitionerId, Practitioner.Name, HealthcareFacilityId,
       EffectiveFrom, EffectiveTo, PRM_Pending__c,
       PRM_CaseManager__c, PRM_CaseManager__r.Name,
       PRM_CaseManager__r.RecordType.DeveloperName
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND EffectiveTo != null
  AND PRM_Pending__c = true
ORDER BY EffectiveTo DESC
```

**Sample result / row count (if known):** TBD — run in target org.
**Notes / gotchas:**
- `EffectiveTo` is the standard field on `HealthcarePractitionerFacility` (no `__c`); `PRM_Pending__c` and `PRM_CaseManager__c` are custom.
- The `RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'` filter scopes results to true PPL affiliations and excludes other HPF record types. Remove it if you want all HPF record types tied to a recred case manager.
- If the business definition of "PPL" in your context is broader/narrower, adjust the HPF record-type filter accordingly.

---

## Query 2 — Count only

**Use case:** Quick volume check before remediation.

```sql
SELECT COUNT()
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND PRM_CaseManager__c != null
  AND PRM_CaseManager__r.RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND EffectiveTo != null
  AND PRM_Pending__c = true
```
