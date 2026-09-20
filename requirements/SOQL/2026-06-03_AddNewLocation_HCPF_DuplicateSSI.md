# Add-New-Location HCPF Duplicate `SourceSystemIdentifier` Investigation

**Date:** 2026-06-03
**Context:** The Add-New-Location LWC save fails with
`DUPLICATE_VALUE, duplicate value found: SourceSystemIdentifier duplicates value on record with id: 0bSUW000000RQ4r2AG`.
The `0bS` key prefix is `HealthcarePractitionerFacility` (HCPF). Use these
queries to identify which existing HCPF is colliding and on which save path
(Location-Affiliation vs Practice-Affiliation).

---

## Query 1 — Identify the conflicting HCPF

**Object:** `HealthcarePractitionerFacility`
**Use case:** Pull every field needed to tell whether the colliding record is a
Location-Affiliation or Practice-Affiliation HCPF, who the practitioner is,
which facility / vendor account it points to, and whether it's still active.

```sql
SELECT Id,
       Name,
       RecordType.DeveloperName,
       SourceSystemIdentifier,
       PractitionerId,
       Practitioner.Name,
       Practitioner.Account.HealthCloudGA__SourceSystemId__c,
       HealthcareFacilityId,
       HealthcareFacility.Name,
       HealthcareFacility.PRM_ExternalId__c,
       AccountId,
       Account.Name,
       Account.HealthCloudGA__SourceSystemId__c,
       IsActive,
       PRM_Pending__c,
       EffectiveFrom,
       EffectiveTo,
       PRM_CaseManager__c,
       CreatedDate,
       CreatedById,
       LastModifiedDate
FROM HealthcarePractitionerFacility
WHERE Id = '0bSUW000000RQ4r2AG'
```

**Notes / gotchas:**
- `RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'` → the
  collision came from `bulkInsertLocationAffiliations` (line 995 of
  `PRM_AddNewLocationUtilityHelper.cls`). The unique key is
  `<HealthcareFacility.PRM_ExternalId__c>-<Practitioner NPI>`.
- `RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'` → the
  collision came from `insertPracticeAffiliationFromStages` (line 1038). The
  unique key is `<Vendor Account.HealthCloudGA__SourceSystemId__c>-<Practitioner NPI>`.
- The existing HCPF being inactive (`IsActive=false`) does NOT relax the
  uniqueness constraint — `SourceSystemIdentifier` is unique on ALL rows.

---

## Query 2 — Find every HCPF sharing the same SourceSystemIdentifier

**Object:** `HealthcarePractitionerFacility`
**Use case:** Confirm that the conflicting key really is a duplicate (and
inspect any siblings) — useful when remediating with a data fix.

```sql
SELECT Id,
       Name,
       RecordType.DeveloperName,
       SourceSystemIdentifier,
       PractitionerId,
       HealthcareFacilityId,
       AccountId,
       IsActive,
       PRM_Pending__c,
       EffectiveFrom,
       EffectiveTo,
       CreatedDate
FROM HealthcarePractitionerFacility
WHERE SourceSystemIdentifier = (
    SELECT SourceSystemIdentifier
    FROM HealthcarePractitionerFacility
    WHERE Id = '0bSUW000000RQ4r2AG'
)
ORDER BY CreatedDate ASC
```

**Notes / gotchas:** SOQL doesn't allow scalar sub-queries on standard fields
this way — if it errors, run Query 1 first, copy the
`SourceSystemIdentifier` value, then run:

```sql
SELECT Id, Name, RecordType.DeveloperName, SourceSystemIdentifier,
       PractitionerId, HealthcareFacilityId, AccountId, IsActive,
       PRM_Pending__c, EffectiveFrom, EffectiveTo, CreatedDate
FROM HealthcarePractitionerFacility
WHERE SourceSystemIdentifier = '<paste-value-from-query1>'
ORDER BY CreatedDate ASC
```

---

## Query 3 — All HCPFs for the practitioner (cross-check what already exists)

**Object:** `HealthcarePractitionerFacility`
**Use case:** Show every HCPF the practitioner already has so the analyst can
see why the new save tried to re-create one that exists. Replace
`:practitionerAccountId` with the practitioner's Account Id (e.g.
`001UW00000...` — found via Query 1's `PractitionerId`).

```sql
SELECT Id,
       Name,
       RecordType.DeveloperName,
       SourceSystemIdentifier,
       HealthcareFacilityId,
       HealthcareFacility.Name,
       AccountId,
       Account.Name,
       IsActive,
       PRM_Pending__c,
       EffectiveFrom,
       EffectiveTo
FROM HealthcarePractitionerFacility
WHERE PractitionerId = :practitionerAccountId
ORDER BY RecordType.DeveloperName, CreatedDate DESC
```

**Notes / gotchas:** Run inside an Anonymous Apex block with
`Id practitionerAccountId = '001UW00000xxxxxYAA';` bound at the top, or
substitute the literal Id directly in the WHERE clause.

---

## Query 4 — Trigger-time inputs that built the colliding SSI

**Object:** `HealthcareFacility` + `Account`
**Use case:** Verify the two components that the HCPF trigger concatenates so
you can predict the SSI the next save attempt will compute. Replace
`:hcfId` and `:practitionerAccountId` with the ones returned by Query 1.

```sql
SELECT Id, Name, PRM_ExternalId__c
FROM HealthcareFacility
WHERE Id = :hcfId
```

```sql
SELECT Id, Name, HealthCloudGA__SourceSystemId__c
FROM Account
WHERE Id = :practitionerAccountId
```

**Notes / gotchas:** Per `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier`
(lines 498–510 of the trigger handler), the trigger builds
`uniqueKey = HealthcareFacility.PRM_ExternalId__c + '-' + Practitioner Account.HealthCloudGA__SourceSystemId__c`
for the Practitioner-Location record type. Confirm both source fields are
non-null and match what the existing HCPF's `SourceSystemIdentifier` shows.
