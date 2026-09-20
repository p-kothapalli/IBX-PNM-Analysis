# PAR Form — `HealthCloudGA__SourceSystemId__c` Duplicate Errors

**Date:** 2026-08-19
**Context:** PAR form (`PRM_PractitionerParticipationForm` v117) submissions failed with `DUPLICATE_VALUE: HealthCloudGA__SourceSystemId__c` for Alan Heideman (NPI 1114971827) and Debra Palmer (NPI 1669235743). These queries diagnose why the form's existing-practitioner detection missed Accounts that already exist, and size the affected population.

**Org used:** `salesforce-7y19gr` (`prashanth.kothapalli@ibx.com.pie.qa`)

---

## Query 1 — Identify the Account behind a duplicate-value error

**Object:** `Account`
**Use case:** Given the record Id quoted in the DUPLICATE_VALUE message, confirm what it is (practitioner vs vendor) and whether it is active.

```sql
SELECT Id, Name, RecordType.DeveloperName, HealthCloudGA__SourceSystemId__c,
       IsPersonAccount, IsActive, PRM_CredentialingStatus__c, CreatedDate, LastModifiedDate
FROM Account
WHERE Id IN ('001UW00000eiMVPYA2','001UW000014BjjmYAC')
```

**Sample result:** `Alan Heideman` / NPI `1114971827` / `PRM_Practitioner` / `IsActive=false`; `Debra Palmer` / NPI `1669235743` / `IsActive=false` / `PRM_CredentialingStatus__c='Denied'`.
**Notes / gotchas:** Ids copied from a screenshot are case-sensitive — `001UW000014BJjmYAC` returns nothing, the real Id is `001UW000014BjjmYAC`. Query by NPI (Query 2) instead of transcribing Ids.

---

## Query 2 — Find the practitioner Account by NPI (the fallback lookup the form is missing)

**Object:** `Account`
**Use case:** The single query that would have prevented all of these failures. `HealthCloudGA__SourceSystemId__c` on a practitioner Account holds the NPI.

```sql
SELECT Id, Name, HealthCloudGA__SourceSystemId__c, IsActive, PRM_CredentialingStatus__c
FROM Account
WHERE HealthCloudGA__SourceSystemId__c IN ('1114971827','1669235743','1932179090')
  AND RecordType.DeveloperName = 'PRM_Practitioner'
```

**Sample result:** 3 of 3 rows found, all `IsActive=false`.
**Notes / gotchas:** This is the counterfactual proof — the records the form claimed were new are findable in one query.

---

## Query 3 — Inspect the NPI linkage the form actually relies on

**Object:** `HealthcareProviderNpi`
**Use case:** `PRMDRExtractExistingNPIInfo` finds the Account only via `HealthcareProviderNpi` → `AccountId`, filtered to `NpiType = 'Individual'`. This query shows why the join fails.

```sql
SELECT Id, Npi, NpiType, AccountId, PractitionerId, IsActive,
       EffectiveFrom, EffectiveTo, CreatedDate
FROM HealthcareProviderNpi
WHERE Npi IN ('1114971827','1669235743','1932179090')
```

**Sample result:**

| Npi | NpiType | AccountId | Why detection fails |
|---|---|---|---|
| 1114971827 | Individual | *(null)* | Account join returns nothing |
| 1669235743 | Organization | 001UW000014BjjmYAC | filtered out by `NpiType='Individual'` |
| 1932179090 | Individual | *(null)* | Account join returns nothing |

**Notes / gotchas:** Two independent break modes — a null `AccountId`, or a practitioner NPI mistyped as `Organization`. Either one silently routes the form to the create path.

---

## Query 4 — Confirm the live DataRaptor filters (no repo guessing)

**Object:** `OmniDataTransformItem`
**Use case:** The repo export can be stale. This reads the filters actually running in the org.

```sql
SELECT InputObjectQuerySequence, InputObjectName, InputFieldName,
       FilterOperator, FilterValue, OutputFieldName, OutputObjectName, IsDisabled
FROM OmniDataTransformItem
WHERE OmniDataTransformation.Name = 'PRMDRExtractExistingNPIInfo'
  AND (InputObjectName != null OR OutputFieldName LIKE '%ExistingAccountId%')
ORDER BY InputObjectQuerySequence
```

**Notes / gotchas:** `PropertySetConfig` on `OmniProcessElement` **cannot** be filtered in SOQL (`field 'PropertySetConfig' can not be filtered in a query call`) — select it and filter in the client instead.

---

## Query 5 — Confirm active OmniScript / Integration Procedure versions

**Object:** `OmniProcess`
**Use case:** Many versions exist per asset; only `IsActive=true` runs.

```sql
SELECT Name, VersionNumber, IsActive, Type, SubType
FROM OmniProcess
WHERE (Name LIKE '%PractitionerParticipation%'
    OR Name LIKE '%FetchExistingNPIInfo%'
    OR Name LIKE '%CreateParFormRecords%'
    OR Name LIKE '%PractitionerScreen%')
  AND IsActive = true
ORDER BY Name
```

**Sample result:** `PractitionerParticipationForm` v117, `PRMFetchExistingNPIInfo` v14, `CreateParFormRecords` v31, `PractitionerScreenRecordCreation` v18, `PractitionerScreenExistingNPIRecordUpdation` v13.
**Notes / gotchas:** Repo docs referencing v111 / v8 / v29 are stale.

---

## Query 6 — Blast radius: NPI records invisible to the form's detection

**Object:** `HealthcareProviderNpi`
**Use case:** Size how many practitioners will hit this error on their next submission.

```sql
-- Pattern A: Individual NPI with no Account link
SELECT COUNT(Id) c FROM HealthcareProviderNpi
WHERE NpiType = 'Individual' AND AccountId = null

-- Pattern B: practitioner Account linked, but NPI mistyped as Organization
SELECT COUNT(Id) c FROM HealthcareProviderNpi
WHERE NpiType = 'Organization'
  AND Account.RecordType.DeveloperName = 'PRM_Practitioner'

-- Sanity: blank NpiType, and total
SELECT COUNT(Id) c FROM HealthcareProviderNpi WHERE NpiType = null
SELECT COUNT(Id) c FROM HealthcareProviderNpi
```

**Sample result (2026-08-19):** Pattern A = **50,410**; Pattern B = **2,554**; blank = 3; total = 555,827.
**Notes / gotchas:** `--result-format csv` renders `COUNT()` as an empty line — use `COUNT(Id) c` with `--result-format json`, or `-r human`.

---

## Query 7 — Narrow Pattern B to the guaranteed-collision set

**Object:** `HealthcareProviderNpi`
**Use case:** A Pattern-B row only causes a duplicate error if its linked Account's external Id equals the NPI. Check the overlap.

```sql
SELECT Id, Npi, NpiType, AccountId,
       Account.Name, Account.HealthCloudGA__SourceSystemId__c,
       IsActive, CreatedDate
FROM HealthcareProviderNpi
WHERE NpiType = 'Organization'
  AND Account.RecordType.DeveloperName = 'PRM_Practitioner'
ORDER BY CreatedDate DESC
```

**Sample result:** in a 200-row sample, **200 of 200** had `Account.HealthCloudGA__SourceSystemId__c == Npi` — i.e. effectively all 2,554 Pattern-B practitioners are pre-loaded duplicate failures. By contrast, only ~1% of the Pattern-A sample had a matching Account (most are NPPES reference rows), implying roughly 500 live Pattern-A risks.

---

## Query 8 — Verify whether the May 2026 remediation was ever applied

**Object:** `HealthcareProviderNpi`
**Use case:** `scripts/apex/fix_george_henry_hcnpi_link.apex` was supposed to set `AccountId = 001UW00000eiR46YAE`.

```sql
SELECT Id, Npi, AccountId, IsActive
FROM HealthcareProviderNpi
WHERE Id = '0bNUW000001N8ck2AC'
```

**Sample result:** `AccountId` still **null** — the fix script was never run in this org.

---

## Query 9 — Provenance of a mistyped NPI record

**Object:** `HealthcareProviderNpi`
**Use case:** Establish who/what created a Pattern-B row.

```sql
SELECT Id, Npi, NpiType, CreatedDate, CreatedBy.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM HealthcareProviderNpi
WHERE Id = '0bNUW0000037LfV2AU'
```

**Sample result:** created 2026-03-10 by Prathamesh Shivare, last modified 2026-04-13 by Erwin Giron.

---

## Related

- `requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` — May 2026 root cause & fix story (Category A is the same defect class)
- `requirements/PAR_Form_DuplicateErrors_DataFix_Runbook.md` — data-fix runbook
- `scripts/apex/mimic_par_duplicate_2026_08_19.apex` — reproduction harness for these three NPIs
