# Katherine Santa Maria — App Review "Missing Primary Address" diagnosis

**Date:** 2026-06-15
**Context:** App Review (`PRM_InitialCredentialAppReview`) fails on submit with
`Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`.
Root cause: `PRM_CreateAdverseActionLog_Procedure` filters `locationsToUpsert.Locations` on
`PrimaryPracticeLoc == true`; none of Katherine's facilities qualify, so the primary
address fields resolve to null. Practitioner Contact = `003UW00000icjajYAA`, Account =
`001UW00000lXetJYAS`, case = `500UW00000wJ9cV`, case facility = `0klUW000000CXufYAG`,
address = `130UW00000f3ZUfYAM`.

---

## Query 1 — Facility flags for the case practice location

**Object:** `HealthcareFacility`
**Use case:** Confirm whether the case's practice location is flagged primary/active/pending.

```sql
SELECT Id, Name, PRM_Primary__c, PRM_Active__c, PRM_Pending__c, LocationId
FROM HealthcareFacility
WHERE Id = '0klUW000000CXufYAG'
```

**Result:** `PRM_Primary__c=false, PRM_Active__c=false, PRM_Pending__c=true` (new/pending, not primary).

---

## Query 2 — All practitioner-facility links for the practitioner

**Object:** `HealthcarePractitionerFacility`
**Use case:** Enumerate every practice location for the practitioner and find which (if any) is primary.

```sql
SELECT Id, HealthcareFacilityId, HealthcareFacility.Name,
       HealthcareFacility.PRM_Primary__c, HealthcareFacility.PRM_Active__c,
       HealthcareFacility.PRM_Pending__c, IsPrimaryFacility, IsActive, PRM_Pending__c
FROM HealthcarePractitionerFacility
WHERE PractitionerId = '003UW00000icjajYAA'
```

**Result:** 6 links / ~4 duplicate "River Wards Wellness Collective" facilities.
**No HealthcareFacility has `PRM_Primary__c = true`.** One HCPF (2566 Frankford Ave) has
`IsPrimaryFacility = true` but its HCF `PRM_Primary__c` is still false.

---

## Query 3 — Address record for the case location

**Object:** `Address`
**Use case:** Confirm the address has full data and inspect its type/active/pending.

```sql
SELECT Id, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c,
       PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_AddressLine1__c, ParentId
FROM Address
WHERE Id = '130UW00000f3ZUfYAM'
```

**Result:** type `Practice` (later changed to `Primary` by data fix), `PRM_Active__c=false`,
`PRM_Pending__c=true`, full City/State/Zip/Line1.
**Notes / gotchas:** `Address` has no `HealthcareFacilityId` column (use `ParentId` / location).
`PRM_AddressType__c` is a multi-select picklist — `LIKE` is invalid; use `INCLUDES('Primary')`.

---

## Query 4 — Org-wide usage of the primary-practice-location flag

**Object:** `HealthcareFacility`
**Use case:** Confirm `PRM_Primary__c` is the standard "primary practice location" marker.

```sql
SELECT COUNT() FROM HealthcareFacility WHERE PRM_Primary__c = true
```

**Result:** 315,069 facilities flagged primary org-wide → field is the real marker; Katherine is an anomaly with none set.

---

## Query 5 — Is the flag a formula? (Tooling API)

**Object:** `FieldDefinition` (Tooling)
**Use case:** Determine whether `PRM_Primary__c` is directly writable.

```sql
SELECT QualifiedApiName, DataType, IsCalculated
FROM FieldDefinition
WHERE EntityDefinition.QualifiedApiName = 'HealthcareFacility'
  AND QualifiedApiName = 'PRM_Primary__c'
```

**Result:** `Checkbox`, `IsCalculated=false` — writable, BUT a `before` trigger
(`PRM_HCFacilityTriggerHelper.assignPrimaryFlags`) / governance keeps it false for a
**pending/inactive** facility. Setting it true on a pending location does not persist.
**Notes / gotchas:** Run with `--use-tooling-api`.
