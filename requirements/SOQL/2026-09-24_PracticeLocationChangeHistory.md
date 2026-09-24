# Practice Location Change History

**Date:** 2026-09-24
**Context:** Grounding queries for the Practice Location change-history LWC design prompt (`requirements/PracticeLocation_ChangeHistory_LWC_DesignPrompt.md`). They show which association fields are history-tracked, how large the child tables are, and how to pull the child-association history for one practice location.

---

## Query 1 — Which fields are history-tracked on Practice Location objects

**Object:** `FieldDefinition` (Tooling API — run with `--use-tooling-api`)
**Use case:** Confirms what the LWC can actually show for each category. Anything not listed has no history.

```sql
SELECT EntityDefinition.QualifiedApiName, QualifiedApiName
FROM FieldDefinition
WHERE EntityDefinition.QualifiedApiName IN (
  'HealthcareFacility','HealthcarePractitionerFacility','HealthcareFacilityNetwork',
  'HealthcareProviderTaxonomy','CareProviderFacilitySpecialty',
  'PRM_InfoCodeAssignment__c','PRM_ProviderFeature__c','PRM_HealthcareFacilityNPI__c',
  'PRM_HealthcareFacilityAssociation__c','PRM_HealthcareFacilityBundleAssociation__c')
AND IsFieldHistoryTracked = true
```

**Sample result / row count:** 99 rows for the first five objects plus 64 for the custom ones (IBX QA, 2026-09-24). `CareProviderFacilitySpecialty` returns 0.
**Notes / gotchas:** Local source XML has no `trackHistory` flags on these objects, so the source can't be trusted for this. Ask the org.

---

## Query 2 — HealthcareFacilityNetwork volume by record type

**Object:** `HealthcareFacilityNetwork`
**Use case:** Sizes the network/taxonomy categories to decide pagination and caps.

```sql
SELECT RecordType.DeveloperName rt, COUNT(Id) c
FROM HealthcareFacilityNetwork
GROUP BY RecordType.DeveloperName
```

**Sample result:** `PRM_FacilityPractitionerTxNw` 8,022,468 · `PRM_FacilityNw` 914,111 · `PRM_FacilityTx` 519,469 · `PRM_TaxonomyNetworkException` 9,451 · null 651.
**Notes / gotchas:** Took about 75 seconds. Don't run it routinely.

---

## Query 3 — Practitioner add/remove history for one Practice Location (two-step)

**Object:** `HealthcarePractitionerFacility` → `HealthcarePractitionerFacilityHistory`
**Use case:** Shows who was added to or removed from a location, and when. Step 1 gets the child Ids; step 2 gets their history.

```sql
-- Step 1
SELECT Id, Practitioner.Name, EffectiveFrom, EffectiveTo, IsActive, PRM_CaseManager__r.Name
FROM HealthcarePractitionerFacility
WHERE HealthcareFacilityId = '<PracticeLocationId>'

-- Step 2
SELECT HealthcarePractitionerFacilityId, Field, DataType, OldValue, NewValue,
       CreatedDate, CreatedBy.Name
FROM HealthcarePractitionerFacilityHistory
WHERE HealthcarePractitionerFacilityId IN (<ids from step 1>)
  AND Field IN ('created','EffectiveTo','EffectiveFrom','IsActive','PRM_IsErrorRecord__c')
ORDER BY CreatedDate DESC
```

**Notes / gotchas:** History tables can't be filtered by the grandparent (`HealthcareFacilityId`). `Field = 'created'` means "Added". A blank-to-date `EffectiveTo` means "Removed". Lookup changes return two rows (`DataType = 'EntityId'` and a name row), so de-duplicate them.

---

## Query 4 — Network / taxonomy add/remove history for one Practice Location

**Object:** `HealthcareFacilityNetwork` → `HealthcareFacilityNetworkHistory`
**Use case:** Shows networks and taxonomies added or removed at location level (`PRM_FacilityNw` / `PRM_FacilityTx`), or at practitioner-at-location level (`PRM_FacilityPractitionerTxNw`).

```sql
-- Step 1 (location-level; add 'PRM_FacilityPractitionerTxNw' for Level 4)
SELECT Id, RecordType.DeveloperName, PayerNetwork.Name, PRM_Taxonomy__r.Name,
       Practitioner.Name, EffectiveFrom, EffectiveTo, IsActive
FROM HealthcareFacilityNetwork
WHERE HealthcareFacilityId = '<PracticeLocationId>'
  AND RecordType.DeveloperName IN ('PRM_FacilityNw','PRM_FacilityTx')

-- Step 2
SELECT HealthcareFacilityNetworkId, Field, DataType, OldValue, NewValue, CreatedDate, CreatedBy.Name
FROM HealthcareFacilityNetworkHistory
WHERE HealthcareFacilityNetworkId IN (<ids from step 1>)
ORDER BY CreatedDate DESC
```

**Notes / gotchas:** A large group location can have thousands of Level-4 rows (deferred post-POC), so page the step-1 Ids in chunks and keep the SOQL 50K-row limit in mind. **Corrected 2026-09-24:** IBX has Field Audit Trail, so older rows are in `FieldHistoryArchive` (Query 5), not lost after 18–24 months.

---

## Query 5 — Archived history (Field Audit Trail) for child records of a Practice Location

**Object:** `FieldHistoryArchive` (big object)
**Use case:** Fetches changes that have moved out of the live `<Object>History` table. Run it per object type, reusing the child Ids from step 1 of Query 3 or Query 4.

```sql
SELECT HistoryId, ParentId, Field, OldValue, NewValue, CreatedDate, CreatedById
FROM FieldHistoryArchive
WHERE FieldHistoryType = 'HealthcarePractitionerFacility'
  AND ParentId IN (<ids from Query 3 step 1>)
```

**Sample result:** Returns rows (e.g., `Field = 'created'` on 2025-05-28) in IBX QA.
**Notes / gotchas:**
- Big-object SOQL must filter on the index in order: `FieldHistoryType`, then `ParentId`, then optionally a `CreatedDate` range. Arbitrary filters and `ORDER BY` aren't allowed, so sort in Apex.
- There is no `DataType` column, so tell lookup Id rows from name rows by checking whether the value is a valid record Id.
- De-duplicate against live history on `HistoryId`.
- `CreatedBy.Name` relationship traversal may not be supported here. Resolve `CreatedById` to names in a separate `User` query.

---

## Query 6 — Candidate integration users

**Object:** `User`
**Use case:** Seeds the Custom Metadata list the LWC uses to badge "Integration" changes. Profile can't be used: MuleSoft Integration User is a System Administrator.

```sql
SELECT Id, Name, Username, Profile.Name, UserType
FROM User
WHERE IsActive = true
  AND (Name LIKE '%Integration%' OR UserType = 'CloudIntegrationUser')
```

**Sample result:** 5 users — MuleSoft Integration User (System Administrator), Platform Integration User (CloudIntegrationUser), Integration User, Insights Integration, SalesforceIQ Integration.
**Notes / gotchas:** A name match is only a starting point. Confirm the final list with the business, and check whether any batch/DFX jobs run as a named person.
