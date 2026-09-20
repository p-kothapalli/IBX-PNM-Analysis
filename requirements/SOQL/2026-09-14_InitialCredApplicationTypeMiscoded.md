# Initial Cred — Application Type miscoded as Organization

**Date:** 2026-09-14
**Context:** Business reported that some Initial Credentialing Case Managers carry an Application Type of
"Organizational" (actual picklist value is **`Organization`**) when they should be **`Individual`**. These
queries identify the affected population, size it, and support a data-fix extract.

**Grounding notes:**

- The Case Manager object is **`IndividualApplication`** (there is no `PRM_Case_Manager__c`).
- Initial Cred = RecordType **`PRM_PractitionerParticipationRequest`** (label "Practitioner Participation
  Request", described in metadata as the *Practitioner Participation Intake Form*). Recredentialing is a
  separate record type, `PRM_ReCredentialing`.
- `ApplicationType` is a **standard** picklist on `IndividualApplication` with values `Individual` /
  `Organization`. There is no value literally named "Organizational" — business shorthand.
- Both values are valid on the Initial Cred record type, so no validation rule blocks the bad value.
- Counts below were run against the **`ibx-qa` sandbox** (`00DVB00000AU8Ll2AL`). Re-run in Production for
  the real business numbers.

---

## Query 1 — Size the problem across all Case Manager record types

**Object:** `IndividualApplication`
**Use case:** Show, per record type, how the Application Type values split — this is what proves Initial Cred
is the outlier and gives the "expected vs actual" baseline.

```sql
SELECT RecordType.DeveloperName, ApplicationType, COUNT(Id) recCount
FROM IndividualApplication
GROUP BY RecordType.DeveloperName, ApplicationType
ORDER BY RecordType.DeveloperName
```

**Sample result (ibx-qa, 2026-09-14):**

| Record Type | Individual | Organization | (blank) |
|---|---:|---:|---:|
| PRM_PractitionerParticipationRequest (**Initial Cred**) | 22,964 | **293** | – |
| PRM_ReCredentialing | 37,075 | – | – |
| PRM_PDMManualChange | 61,192 | 29,468 | – |
| PRM_PNC | 1,717 | 166 | – |
| PRM_OffCycleRequest | 3,103 | – | – |
| PRM_ProfessionalStaffVerification | 36 | – | – |
| PRM_AncillaryAssessment | – | 280 | – |
| PRM_AncillaryReAssessment | – | 1,086 | – |
| PRM_NonParClaimsRequest | – | 12,674 | – |
| PRM_NonParticipationRequest | – | 1,335 | – |
| PRM_ProviderChangeRequest | – | 279 | 90 |
| PRM_CMSPreclusionTerm | – | – | 4 |

**Notes / gotchas:** Recred being 100% `Individual` is the control group — it confirms `Individual` is the
correct value for a practitioner-level credentialing application, so the 293 Initial Cred rows are genuinely
wrong rather than a legitimate variant.

---

## Query 2 — The defect population (the report business asked for)

**Object:** `IndividualApplication`
**Use case:** Extract the Initial Cred Case Managers miscoded as Organization, with the fields needed to
triage and correct them.

```sql
SELECT Id,
       Name,
       ApplicationType,
       Category,
       Status,
       PRM_FormType__c,
       PRM_FirstName__c,
       PRM_LastName__c,
       AccountId,
       PRM_HealthcareProviderNPI__c,
       CreatedDate,
       CreatedBy.Name,
       LastModifiedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND ApplicationType = 'Organization'
ORDER BY CreatedDate DESC
```

**Sample result / row count:** 293 rows in `ibx-qa`. All carry `Category = 'Credentialing'`. Sample IDs:
`IA-0000031405`, `IA-0000030283`, `IA-0000030139`.

**Notes / gotchas:** `ApplicationReferenceNumber` is null on every affected row, and `PRM_FirstName__c` /
`PRM_LastName__c` are null on most — consistent with these records being created by the *existing NPI*
branch, which resolves the practitioner from the NPI rather than typing the name onto the Case Manager.

---

## Query 3 — Volume trend by month (is it still happening?)

**Object:** `IndividualApplication`
**Use case:** Determine whether the miscoding is historical or ongoing, so business knows whether a one-time
data fix is enough or a config fix must land first.

```sql
SELECT CALENDAR_YEAR(CreatedDate) yr, CALENDAR_MONTH(CreatedDate) mo, COUNT(Id) recCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND ApplicationType = 'Organization'
GROUP BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
```

**Sample result (ibx-qa):** 2025-06 → 9; 2025-07 → 129; 2025-08 → 143; 2025-09 → 12. Ongoing, not a
one-off historical batch.

**Notes / gotchas:** `CALENDAR_MONTH` ignores the year, so it must be paired with `CALENDAR_YEAR` in both
`GROUP BY` and `ORDER BY` or months collapse across years.

---

## Query 4 — Spread by creator / form type / status

**Object:** `IndividualApplication`
**Use case:** Test whether this is one user's data-entry habit or a systemic creation-path defect.

```sql
SELECT CreatedBy.Name, PRM_FormType__c, Category, Status, COUNT(Id) recCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND ApplicationType = 'Organization'
GROUP BY CreatedBy.Name, PRM_FormType__c, Category, Status
ORDER BY COUNT(Id) DESC
```

**Sample result (ibx-qa):** 40 groups spanning ~15 distinct creators and both `IBC` and
`AmeriHealth - CAQH` form types. No single user dominates — systemic, not user error.

**Notes / gotchas:** The overwhelming majority sit in `Status = 'Denied'`, with a small tail in `Closed`,
`Submitted`, `In Progress`, `Complete`, and `Pending Closure`. Worth confirming with business whether the
wrong Application Type is itself driving the denial routing.

---

## Root cause (for the fix story, not a query)

`PRMDRCreateCaseCaseManagerExistingNPI` (version 1, the only version) writes the
`PRM_PractitionerParticipationRequest` record type and maps `ApplicationType → ApplicationType` with:

```xml
<defaultValue>Organization</defaultValue>
<inputFieldName>ApplicationType</inputFieldName>
<outputFieldName>ApplicationType</outputFieldName>
<outputObjectName>IndividualApplication</outputObjectName>
```

When the intake payload omits `ApplicationType`, the DataRaptor default stamps `Organization`. The sibling
new-NPI path, `PRMDRCreateCaseCaseManagerAndAccount`, hardcodes `"ApplicationType" : "Individual"` and is
therefore unaffected. Caller of the defective mapper:
`PRM_PractitionerScreenExistingNPIRecordUpdation_Procedure` (confirm the `isActive` version before changing).

**Fix options:** change the DataRaptor `defaultValue` to `Individual`, or have the IP always pass
`ApplicationType` explicitly. Either needs a matching backfill of the 293 existing rows.
