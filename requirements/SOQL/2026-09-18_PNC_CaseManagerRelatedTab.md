# PNC / PAR Case Manager Related Tab (BUG 1467373)

**Date:** 2026-09-18
**Context:** Credentialing Specialists opening a submitted PNC Case Manager (new practitioner on an existing PNC group) see “No related records found” on the Related tab. These queries separate “associations were never written” from “associations exist but the Related-tab LWC will not render them.”

---

## Query 1 — Case Manager header (screenshot Id)

**Object:** `IndividualApplication`
**Use case:** Confirm record type, CMA flag, and whether PDM Manual Update Type is blank (the Related-tab controller’s current gate).

```sql
SELECT Id, Name, RecordType.DeveloperName, RecordType.Name, Status, Category,
       PRM_UseCaseManagerAssociation__c, PRM_PDMManualUpdateType__c,
       PRM_RequestType__c, AccountId, Account.Name, CreatedDate
FROM IndividualApplication
WHERE Name = 'IA-0000157071'
```

**Sample result / row count (if known):** In default org `ibx-qa`, this auto-number is a **different** Case Manager (`PRM_NonParClaimsRequest` / Non-Par Claims Request, Approved, Sanford Healthcare Accessories). The bug screenshot is Record Type **PNC**, Status **Submitted**, Category **Credentialing**, account Katherine Marie Nicodemus — run this in the defect’s QA org, not assumed equal across sandboxes.
**Notes / gotchas:** `IndividualApplication.Name` auto-numbers are org-specific. Prefer Id from the screenshot URL when available.

---

## Query 2 — PNC record types

**Object:** `RecordType`
**Use case:** Confirm the PNC vs PAR vs Non-Par Claims labels so the screenshot “PNC” is not confused with Non-Par Claims Request.

```sql
SELECT Id, Name, DeveloperName
FROM RecordType
WHERE SobjectType = 'IndividualApplication'
  AND (Name LIKE '%PNC%'
    OR DeveloperName LIKE '%PNC%'
    OR Name LIKE '%Non-Par%'
    OR Name LIKE '%Participation%')
```

**Sample result / row count (if known):** 4 rows in `ibx-qa` — `PRM_NonParClaimsRequest` (Non-Par Claims Request), `PRM_NonParticipationRequest`, **`PRM_PNC` (label PNC)**, `PRM_PractitionerParticipationRequest`.
**Notes / gotchas:** Screenshot Record Type **PNC** is `PRM_PNC`, not Non-Par Claims.

---

## Query 3 — Analog PNC Case Managers (Submitted, CMA flag on)

**Object:** `IndividualApplication`
**Use case:** Find PNC cases in this org that already flipped to the CMA Related tab (`PRM_UseCaseManagerAssociation__c = true`) with no PDM Manual Update Type — the same empty-tab condition as the defect.

```sql
SELECT Id, Name, Status, Category,
       PRM_UseCaseManagerAssociation__c, PRM_PDMManualUpdateType__c,
       Account.Name, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PNC'
  AND Status = 'Submitted'
ORDER BY CreatedDate DESC
LIMIT 10
```

**Sample result / row count (if known):** 10 recent PNC Submitted rows in `ibx-qa`. Example analog: `IA-0000192693` (`0iTVB000000KLuj2AG`, Heather C Wargo) — flag **true**, `PRM_PDMManualUpdateType__c` **null**.
**Notes / gotchas:** Newer rows (e.g. IA-0000194525) still have the flag **false** and would still show the **standard** Related lists, not the empty LWC state.

---

## Query 4 — Case Manager Associations by record type

**Object:** `PRM_CaseManagerAssociation__c`
**Use case:** Prove whether the empty Related tab is a missing-data problem or a display-mapping problem.

```sql
SELECT RecordType.DeveloperName, COUNT(Id) cnt
FROM PRM_CaseManagerAssociation__c
WHERE PRM_CaseManager__c = '0iTVB000000KLuj2AG'
GROUP BY RecordType.DeveloperName
```

**Sample result / row count (if known):** 12 associations on analog IA-0000192693: Practitioner (1), Vendor (1), Identifier (3), Healthcare Provider NPI (2), Business License (1), Provider Taxonomy (1), Person Education (1), Person Language (1), Contact Profile (1). **Zero** Practice Location, Practitioner Practice Location, Practice Location Network, or Practice Location Taxonomy associations.
**Notes / gotchas:** `PRM_CaseManagerRelatedListController.fetchCaseManagerAssociatedRecords` returns an empty map when `PRM_PDMManualUpdateType__c` is blank — so these 12 rows never reach the LWC.

---

## Query 5 — Case-scoped practitioner-at-location vs location Case Manager stamp

**Object:** `HealthcarePractitionerFacility` (and parent `HealthcareFacility`)
**Use case:** Show that new practitioner-at-location rows are stamped to this Case Manager while the **existing** practice location keeps its original Case Manager — which is why the PAR CMA batch (querying `PRM_CaseManager__c = this CM` on `HealthcareFacility`) finds zero locations.

```sql
SELECT Id, Name, HealthcareFacilityId, HealthcareFacility.Name,
       HealthcareFacility.PRM_CaseManager__c, PRM_CaseManager__c
FROM HealthcarePractitionerFacility
WHERE PRM_CaseManager__c = '0iTVB000000KLuj2AG'
```

```sql
SELECT COUNT(Id) cnt
FROM HealthcareFacility
WHERE PRM_CaseManager__c = '0iTVB000000KLuj2AG'
```

**Sample result / row count (if known):** 2 practitioner-at-location rows; one points at existing location `Einstein Practice Plan(5501 Old York Rd-7170)` whose Case Manager is a **different** Id (`0iTVB000000Kkxx2AC`). Location count stamped to this CM: **0**.
**Notes / gotchas:** Do **not** restamp the existing location’s Case Manager. Create Case Manager Association rows that point at the existing location (and its networks/taxonomies) while leaving the location’s own Case Manager lookup unchanged.

**Related:** `requirements/BUG1467373_PNC_CaseManager_RelatedTab_Empty_UserStory.md`
