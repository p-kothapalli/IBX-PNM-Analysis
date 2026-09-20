# App Review – Adverse Action Log "Required fields are missing" Diagnostics

**Date:** 2026-06-08
**Context:** App Review OmniScript (`PRM_InitialCredentialAppReview`) submit fails with
`Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`
when creating a `PRM_AdverseActionLog__c` via the `PRM_CreateAdverseActionLog_Procedure` IP →
`PRMDRCreateAdverseActionLog` DataRaptor. Root cause: the practitioner's primary practice
address is **inactive**, and the IP's `FilterPrimaryAddress` step only keeps addresses where
`Active==true || Pending==true`, so the address fields arrive blank. Those four fields are
field-level `required=true` on `PRM_AdverseActionLog__c`, so the insert throws REQUIRED_FIELD_MISSING.

Case used for repro: Case Manager `0iTUW000000l6d32AA` (IA-0000148183),
Practitioner Account `001UW000016UFgrYAG` (Lindsey Schaffel).

---

## Query 1 — Case Manager → Practitioner

**Object:** `IndividualApplication`
**Use case:** Resolve the practitioner Account behind a Case Manager.

```sql
SELECT Id, Name, AccountId, Account.Name
FROM IndividualApplication
WHERE Id = '0iTUW000000l6d32AA'
```

## Query 2 — Practitioner's primary facility + location

**Object:** `HealthcarePractitionerFacility`
**Use case:** Find the primary facility (`IsPrimaryFacility = true`) and its `LocationId`,
which is the parent of the primary address.

```sql
SELECT Id, IsPrimaryFacility, Practitioner.AccountId, HealthcareFacilityId,
       HealthcareFacility.LocationId, HealthcareFacility.Account.Name
FROM HealthcarePractitionerFacility
WHERE Practitioner.AccountId = '001UW000016UFgrYAG'
```

**Notes:** Primary facility = `0bSUW000000XlD32AK`, LocationId = `131UW000001cvcbYAA`.

## Query 3 — Addresses on the primary location (THE root cause)

**Object:** `Address`
**Use case:** Inspect the address feeding the AAL. Check `PRM_Active__c` — if `false`
the IP's `FilterPrimaryAddress` (`Active==true || Pending==true`) drops it and the AAL
gets blank required address fields.

```sql
SELECT Id, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_AddressLine1__c,
       PRM_AddressLine2__c, PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_County__c, LastModifiedDate
FROM Address
WHERE ParentId = '131UW000001cvcbYAA'
ORDER BY LastModifiedDate DESC
```

**Sample result:** 1 row — `15 Hawthorne Dr, Livingston, NJ 07039` (Essex),
AddressType `Primary;Billing;Mailing`, but **`PRM_Active__c = false`**.

## Query 4 — Existing AALs for the Case Manager

**Object:** `PRM_AdverseActionLog__c`
**Use case:** The IP skips creation when an AAL already exists (`ISBLANK(...Extract...Id)`).
0 rows means the create branch runs.

```sql
SELECT Id, PRM_Status__c, PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_AdHoc__c, CreatedDate
FROM PRM_AdverseActionLog__c
WHERE PRM_CaseManager__c = '0iTUW000000l6d32AA'
```

**Sample result:** 0 rows.

## Query 5 — Primary HealthcareFacility active status

**Object:** `HealthcareFacility`
**Use case:** Confirms the facility itself is inactive (`PRM_Active__c = false`), consistent
with its address being inactive.

```sql
SELECT Id, Name, PRM_Active__c, LocationId
FROM HealthcareFacility
WHERE Id = '0klUW000000Bo37YAC'
```

**Sample result:** `One of a Kind Therapy (15 Hawthorne Dr-9071)`, `PRM_Active__c = false`.

---

### Fix options
1. **Data fix (unblocks this case now):** set `PRM_Active__c = true` on Address `130UW00000e0rwXYAQ`
   (and/or facility `0klUW000000Bo37YAC`) so the filter keeps it.
2. **Config fix (prevents recurrence):** relax the `FilterPrimaryAddress` filter in
   `PRM_CreateAdverseActionLog_Procedure` so it falls back to the primary address even when
   inactive (mirrors `PRM_AdverseActionLogService.loadPrimaryFacilityAndAddress`, which
   deliberately does NOT filter on `PRM_Active__c`).
