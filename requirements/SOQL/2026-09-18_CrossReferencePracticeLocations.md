# Cross-Reference Practice Locations — Case Manager IA-0000067363

**Date:** 2026-09-18
**Context:** Case Manager `0iTUW000000J6WL2A0` (IA-0000067363) is a PDM Manual Change of type Cross-Reference Practice Locations, but no From/To Practice Locations appear on the record. These queries reconstruct where those locations are stored and why this Case Manager has none.

---

## Query 1 — Case Manager header

**Object:** `IndividualApplication`
**Use case:** Confirm request type, status, and vendor for this Case Manager.

```sql
SELECT Id, Name, RecordType.DeveloperName, RecordType.Name, Status,
       PRM_PDMManualUpdateType__c, PRM_RequestType__c,
       AccountId, Account.Name, CreatedDate, LastModifiedDate
FROM IndividualApplication
WHERE Id = '0iTUW000000J6WL2A0'
```

**Sample result / row count (if known):** 1 row. IA-0000067363, PDM Manual Change, Status In Progress, `PRM_PDMManualUpdateType__c` = Cross-Reference Practice Locations, vendor Montville Primary Care Physicians (`001UW00000ejtTnYAI`), created 2025-12-15 20:33:05Z.
**Notes / gotchas:** Request type lives on `PRM_PDMManualUpdateType__c`, not `PRM_RequestType__c` (that field is null here).

---

## Query 2 — Case Manager Associations (what the related-list LWC uses)

**Object:** `PRM_CaseManagerAssociation__c`
**Use case:** The Case Manager related-list LWC (`prmCaseManagerRelatedList`) only shows Practice Locations that are associated through this object. Empty means the UI will show none.

```sql
SELECT Id, Name, RecordType.DeveloperName, PRM_RequestType__c,
       PRM_HealthcareFacility__c, PRM_HealthcareFacility__r.Name,
       PRM_Account__c, PRM_Account__r.Name,
       PRM_HealthcareFacilityNetwork__c, PRM_Address__c,
       PRM_HealthcarePractitionerFacility__c,
       PRM_HealthcareFacilityAssociation__c, CreatedDate
FROM PRM_CaseManagerAssociation__c
WHERE PRM_CaseManager__c = '0iTUW000000J6WL2A0'
ORDER BY RecordType.DeveloperName, CreatedDate
```

**Sample result / row count (if known):** 0 rows.
**Notes / gotchas:** For Cross-Reference, Practice Locations are collected from CMA rows with record type `Practitioner_at_Practice_Location_Taxonomy_and_Network` (`PRM_CaseManagerRelatedListController`). CMA is written later by `PRM_CaseManagerAssociationBatch` after facilities are stamped with the Case Manager.

---

## Query 3 — Practice Locations stamped to this Case Manager

**Object:** `HealthcareFacility`
**Use case:** The standard Practice Locations related list on the Case Manager (`HealthCarefacilities__r`) is the reverse of `HealthcareFacility.PRM_CaseManager__c`.

```sql
SELECT Id, Name, PRM_PracticeName__c, PRM_Active__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_CaseManager__c,
       PRM_CrossReferenceFrom__c, PRM_CrossReferenceFrom__r.Name,
       PRM_CrossReferenceTo__c, PRM_CrossReferenceTo__r.Name,
       PRM_CrossReference__c, PRM_CrossReference__r.Name,
       AccountId, Account.Name, LocationId, PRM_NpiId__c
FROM HealthcareFacility
WHERE PRM_CaseManager__c = '0iTUW000000J6WL2A0'
```

**Sample result / row count (if known):** 0 rows.
**Notes / gotchas:** `PRM_CaseManager__c` is overwritten by later requests, so even a successful Cross-Reference Case Manager can later lose the To location from this related list.

---

## Query 4 — Exception that blocked record creation

**Object:** `PRM_ExceptionLog__c`
**Use case:** Find why no Practice Locations were linked to this Case Manager.

```sql
SELECT Id, Name, PRM_ProcessName__c, PRM_ErrorMessage__c, PRM_StackTrace__c,
       PRM_ExceptionType__c, PRM_RecordId__c, PRM_RequestPayload__c, CreatedDate
FROM PRM_ExceptionLog__c
WHERE CreatedDate >= 2025-12-15T20:00:00Z
  AND CreatedDate <= 2025-12-15T21:00:00Z
  AND PRM_ProcessName__c LIKE '%CrossRef%'
ORDER BY CreatedDate DESC
```

**Sample result / row count (if known):** 1 row, `a1eUW000007CRWfYAO`. Error: `Update failed. First exception on row 0 with id 0klUW0000001eyeYAA; first error: CIRCULAR_DEPENDENCY, Hierarchy Constraint Violation: [PRM_CrossReference__c]`. Process: `PRM_ManualUpdatesCrossRefProcessor processManualUpdates()`. Stack: `crossRefExistingProcess` (LocationExists = Yes path). Payload field is null — the From location Id is not in the log.
**Notes / gotchas:** Filter by process name, not Case Manager Id. `PRM_RecordId__c` is also null on this row; the failing HealthcareFacility Id is inside `PRM_ErrorMessage__c`.

---

## Query 5 — All Practice Locations for the vendor, with From/To

**Object:** `HealthcareFacility`
**Use case:** Find Cross-Reference From and Cross-Reference To on the vendor's Practice Locations, independent of Case Manager stamp.

```sql
SELECT Id, Name, PRM_PracticeName__c, PRM_Active__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       PRM_CaseManager__c, PRM_CaseManager__r.Name,
       PRM_CrossReferenceFrom__c, PRM_CrossReferenceFrom__r.Name,
       PRM_CrossReferenceTo__c, PRM_CrossReferenceTo__r.Name,
       PRM_CrossReference__c, PRM_CrossReference__r.Name,
       LocationId, PRM_NpiId__c, PRM_NpiId__r.Npi, CreatedDate
FROM HealthcareFacility
WHERE AccountId = '001UW00000ejtTnYAI'
ORDER BY CreatedDate DESC
```

**Sample result / row count (if known):** 3 rows (see investigation notes). All share NPI `1841347523`.
**Notes / gotchas:** Addresses are nearly identical (`137 MAIN RD RTE 202` vs `137 MAIN RD ROUTE 202`). Do not identify locations by name/NPI alone.

---

## Query 6 — Addresses for those Practice Locations

**Object:** `Address`
**Use case:** Distinguish the three Montville locations by street line. Address parent is `Location` (`ParentId`), not HealthcareFacility.

```sql
SELECT Id, ParentId, PRM_AddressLine1__c, PRM_City__c, PRM_State__c,
       PRM_Zip__c, PRM_Active__c, PRM_CaseManager__c
FROM Address
WHERE ParentId IN ('131UW0000015WG3YAM','131UW0000016BxbYAE','131UW000001HeQHYA0')
```

**Sample result / row count (if known):** 4 address rows.
**Notes / gotchas:** `Address` has `ParentId` (Location), not `LocationId`. Join to HealthcareFacility through `HealthcareFacility.LocationId`.

---

## Query 7 — Generic pattern: find From/To for any Cross-Reference Case Manager

**Object:** `HealthcareFacility`
**Use case:** Reusable lookup when a Cross-Reference Case Manager's related list is empty or incomplete.

```sql
SELECT Id, Name, PRM_Active__c, PRM_CaseManager__c, PRM_CaseManager__r.Name,
       PRM_CrossReferenceFrom__c, PRM_CrossReferenceFrom__r.Name,
       PRM_CrossReferenceTo__c, PRM_CrossReferenceTo__r.Name,
       PRM_CrossReference__c, PRM_CrossReference__r.Name, AccountId
FROM HealthcareFacility
WHERE AccountId IN (
        SELECT AccountId FROM IndividualApplication WHERE Id = '0iTUW000000J6WL2A0'
      )
  AND (
        PRM_CrossReferenceFrom__c != null
     OR PRM_CrossReferenceTo__c != null
     OR PRM_CrossReference__c != null
     OR PRM_CaseManager__c = '0iTUW000000J6WL2A0'
  )
```

**Sample result / row count (if known):** 2 rows for this vendor (the prior completed Cross-Reference pair). This Case Manager itself still returns 0 stamped rows.
**Notes / gotchas:** Cross-Reference From is stored on the **new/To** location. Cross-Reference To is stored on the **old/From** location. `PRM_CrossReference__c` is the merger/acquisition sibling of From and is also stored on the To location.

---

## Query 8 — Related Case

**Object:** `Case`
**Use case:** Confirm the parent Case is still waiting on processing.

```sql
SELECT Id, CaseNumber, Status, AccountId, Account.Name, CreatedDate
FROM Case
WHERE Id IN (
    SELECT ApplicationCaseId FROM IndividualApplication WHERE Id = '0iTUW000000J6WL2A0'
)
```

**Sample result / row count (if known):** Case `00085340` (`500UW00000tivvsYAA`), Status `Pended - Processing`.
**Notes / gotchas:** IndividualApplication → Case is `ApplicationCaseId`, not a `CaseId` field on IA.
