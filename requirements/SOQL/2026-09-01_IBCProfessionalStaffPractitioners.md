# IBC Professional Staff Practitioners (C64 Info Code)

**Date:** 2026-09-01
**Context:** Retrieve all practitioners flagged as **IBC Professional Staff** via their info code assignment. "IBC Professional Staff" is not a field on the practitioner — it is an **info code assignment** (`C64`) held against the practitioner `Account`. These queries identify that population, size it, and separate active from terminated professional staff.

All results below were taken from **FC2** (`prashanth.kothapalli@ibx.com.pie.fullcopy2`, `00DcW000005NtYnUAK`) on 2026-09-01.

> **Org note (2026-09-08):** FC2 is no longer reachable — `sf` reports *"Unable to refresh session due to: ... inactive organization"*. The Practitioner Number addition was therefore re-validated against **PIE QA** (`prashanth.kothapalli@ibx.com.pie.qa`, `00DVB00000AU8Ll2AL`), where the same queries return **440** professional staff practitioners (517 C64 assignments total), **440 with a Practitioner Number (100%)**, and **438 with at least one licence** across 552 licence rows. The FC2 counts quoted per-query below are from 2026-09-01 and are retained for history; re-run in a live org before relying on the absolute numbers.

---

## Data model notes

- **Practitioner** = `Account` with `RecordType.DeveloperName = 'PRM_Practitioner'`.
- **Info code definition** = `PRM_InfoCode__c`, one row per code. The professional staff code is `PRM_Code__c = 'C64'`, `Name = 'C64-IBC Professional Staff'`.
- **Info code assignment** = `PRM_InfoCodeAssignment__c`. The parent level is chosen by which lookup is populated: `PRM_Account__c` (practitioner/account), `PRM_HealthcareFacility__c` (practice location), `PRM_HealthcarePractitionerFacility__c` (practitioner-practice-location), `PRM_PracticeLocationTaxonomy__c`.
- **C64 is account-level only** — the definition carries `PRM_IsAccount__c = true` with `PRM_IsHealthcareFacility__c = false` and `PRM_IsHealthcarePractitionerFacility__c = false`. So a C64 assignment is **always** parented on `PRM_Account__c`; never join through the facility lookups for this code.
- `PRM_Active__c` is a **formula** (not writable):
  `AND(PRM_EffectiveFrom__c <= TODAY(), NOT(PRM_Pending__c), NOT(PRM_IsErrorRecord__c), OR(ISBLANK(PRM_EffectiveTo__c), PRM_EffectiveTo__c > TODAY()))`.
- The guided flows resolve info codes **by `Name`** (`PRM_CreateHCFRelatedRecordsHelper`), but for querying prefer `PRM_InfoCode__r.PRM_Code__c = 'C64'` — it is exact and immune to name-string drift.
- **`PractitionerCreationType = 'IBC Professional Staff'`** on the guided form is a *different* thing: it is the intake branch selector (see `PRM_PractitionerCreationContainer_Procedure_6`), not a stored practitioner attribute. It is not queryable on the Account. Use the C64 assignment.
- **Practitioner Number** is *not* a text field on the Account. It is `Account.PRM_IdentifierPractitioner__c` — a **Lookup** whose field label is literally "Practitioner Number" — and the number itself is the **`Name`** of the related record, so the SOQL path is **`PRM_IdentifierPractitioner__r.Name`** (relationship name `PRM_IdentifierPractitioner`). The lookup targets a **custom object, `PRM_IdentifierPractitioner__c`** — *not* the standard `Identifier` object, and not `Account.PRM_IdentifierVendor__c` (the vendor equivalent). Grounded in `PRMDRExtractPDMPractitioner_1` and `PRMDRExtractTerminatedPARCredential_1`, which both map `PRM_IdentifierPractitioner__r.Name` → `PractitionerNumber`. Values are 11-digit strings (e.g. `10000265078`), unique per practitioner, and populated on **100%** of the professional-staff population.

### BusinessLicense linkage (verified in FC2, 2026-09-01)

`BusinessLicense` is a **standard** object with four possible parent paths. Population org-wide (319,096 rows total):

| Parent field | Populated | Child relationship from `Account` | Use for practitioners? |
|---|---|---|---|
| `ContactId` → `Contact` | 318,704 (99.9%) | **`PersonBusinessLicenses`** | ✅ **yes — this is the practitioner path** |
| `HealthcareProviderId` → `HealthcareProvider` | 316,314 (99.1%) | *n/a* | alternative traversal |
| `AccountId` → `Account` | 60,232 (18.9%) | `BusinessLicenses` | ❌ only 41 of the 423 prof staff |
| `PRM_HealthcareFacility__c` → `HealthcareFacility` | 114 (0.04%) | *n/a* | facility/ancillary only |

Practitioners are **Person Accounts**, so their licences hang off `PersonContactId` and are reached via the **`PersonBusinessLicenses`** child relationship. For the 423 professional staff: `PersonBusinessLicenses` returns **421 practitioners / 542 rows**, whereas `BusinessLicenses` (AccountId) returns only **41** — and those 41 are a strict subset. **Do not include both subqueries** or those 41 double-count.

**Real field names (the `pnm-object-model.md` reference is stale here):** `PRM_Status__c`, `PRM_VerifiedOn__c` and `PRM_LicenseClass__c` **do not exist** on `BusinessLicense`. The actual fields are standard `Status`, `VerifiedDate`, and `LicenseClass`.

**Which "effective dates" to use** — three candidate pairs exist; only one is populated:

| Pair | Populated on the 542 prof-staff licence rows | Verdict |
|---|---|---|
| `PRM_ProviderLicenseEffectiveDate__c` / `PRM_ProviderLicenseExpirationDate__c` | 99.4% / 99.6% | ✅ **use these** |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | **0% / 0%** | ❌ always null — a trap, since this is the PRM naming convention used on every other object |
| `PeriodStart` / `PeriodEnd` (standard) | **0% / 0%** | ❌ always null |

Also empty on this population: `Issuer` (0%), `JurisdictionState` (0%) — use `PRM_LicenseState__c` instead (PA 498, NJ 39, DE 4, FL 1).

---

## Query 1 — Confirm the C64 info code definition

**Object:** `PRM_InfoCode__c`
**Use case:** Establish the exact code/name before filtering, and confirm which parent level C64 is allowed at.

```sql
SELECT Id, Name, PRM_Code__c, PRM_InfoCode__c, PRM_Type__c,
       PRM_IsAccount__c,
       PRM_IsHealthcareFacility__c,
       PRM_IsHealthcarePractitionerFacility__c,
       PRM_IsTaxonomyOnly__c
FROM PRM_InfoCode__c
WHERE PRM_Code__c = 'C64'
```

**Result (1 row):**

| Field | Value |
|---|---|
| Id (FC2) | `a1sUW0000028lfMYAQ` |
| **Name** | **`C64-IBC Professional Staff`** |
| Code | `C64` |
| Info Code | `IBC Professional Staff` |
| Type | *(null)* |
| **Is Account** | **`true`** — practitioner/account level |
| Is Healthcare Facility | `false` |
| Is Healthcare Practitioner Facility | `false` |
| Is Taxonomy Only | `false` |

**Notes / gotchas:** `Name` is `C64-IBC Professional Staff` with **no space around the hyphen**. Because `PRM_IsHealthcarePractitionerFacility__c = false`, `validateIFCAssignment()` rejects any attempt to assign C64 at the practitioner-practice-location level.

---

## Query 2 — All IBC Professional Staff practitioners (primary — Account based)

**Object:** `Account`
**Use case:** The main answer — the practitioner records that currently hold an active C64 assignment. Returns one row per practitioner.

```sql
SELECT Id, Name, FirstName, LastName, PersonContactId,
       PRM_IdentifierPractitioner__r.Name,   -- Practitioner Number
       PRM_CredentialingStatus__c, PRM_PNC__c,
       PRM_ReCredDueDate__c, IsActive,
       PRM_CaseManager__c, PRM_CaseManager__r.Name
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND Id IN (
      SELECT PRM_Account__c
      FROM PRM_InfoCodeAssignment__c
      WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
        AND PRM_Active__c = true
        AND PRM_IsErrorRecord__c = false
        AND PRM_Account__c != NULL
  )
ORDER BY LastName, FirstName
```

**Sample result / row count:** **423 practitioners** (FC2, 2026-09-01). All 423 are also `IsActive = true`, so adding `AND IsActive = true` changes nothing in this org today — keep it if you want the filter to be explicit and future-proof.

**Notes / gotchas:**
- The inner `PRM_Account__c != NULL` guard is **required**; without it, null rows in the subquery make the outer `Id IN` filter behave unexpectedly.
- Use this form when you want **practitioners** (deduped). Use Query 3 when you want the **assignment** rows with their effective dates.

---

## Query 2a — Primary query **+ business license details with effective dates**

**Object:** `Account` with a `PersonBusinessLicenses` child subquery
**Use case:** The primary population plus each practitioner's licence(s), licence class/state, verification, and licence effective/expiration dates.

```sql
SELECT Id, Name, FirstName, LastName, PersonContactId,
       PRM_IdentifierPractitioner__r.Name,   -- Practitioner Number
       PRM_CredentialingStatus__c, PRM_PNC__c,
       PRM_ReCredDueDate__c, IsActive,
       PRM_CaseManager__c, PRM_CaseManager__r.Name,
       (SELECT Id, LicenseNumber, LicenseClass,
               PRM_LicenseState__c, Status, VerificationStatus,
               IsPrimaryLicense, IsActive,
               IssueDate, VerifiedDate,
               PRM_ProviderLicenseEffectiveDate__c,
               PRM_ProviderLicenseExpirationDate__c
        FROM PersonBusinessLicenses
        WHERE PRM_IsError__c = false
          AND PRM_Pending__c = false
        ORDER BY PRM_ProviderLicenseEffectiveDate__c DESC)
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND Id IN (
      SELECT PRM_Account__c
      FROM PRM_InfoCodeAssignment__c
      WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
        AND PRM_Active__c = true
        AND PRM_IsErrorRecord__c = false
        AND PRM_Account__c != NULL
  )
ORDER BY LastName, FirstName
```

**Sample result / row count:** 423 practitioners; **421 have at least one licence** (542 licence rows), 2 have none. All 542 rows are `PRM_Pending__c = false` and `PRM_IsError__c = false`, so those two guards are currently no-ops but are kept for safety.

**Sample output:**

```
Maria D Adameck  [Credentialed]
    RN582494  SBRD  PA  primary=False  status=Verified  eff=2007-03-13 -> exp=2026-04-30
Jessica Aitken  [Credentialed]
    RN666255  SBRD  PA  primary=False  status=Verified  eff=2023-02-01 -> exp=2027-10-31
    RN666255  SBRD  PA  primary=False  status=None      eff=2023-02-01 -> exp=2025-10-31
Catherine A Algeo  [Credentialed]
    RN667740  SBRD  PA  primary=False  status=None      eff=2023-07-01 -> exp=2026-04-30
```

**Notes / gotchas:**
- **Practitioner Number requires the `__r.Name` hop** — `PRM_IdentifierPractitioner__c` on its own returns the lookup's record Id (e.g. `a1oVB00000HlfU9YAJ`), not the number. Select `PRM_IdentifierPractitioner__r.Name` for the value (`10000265078`). Populated on 100% of the population in PIE QA, and unique per practitioner, so it is safe to use as the report key.
- **`PersonBusinessLicenses`, not `BusinessLicenses`** — see the linkage table above. Using the `AccountId` relationship silently returns licences for only 41 of the 423.
- **Renewal history inflates the row count.** 542 rows for 421 practitioners, and **100 `(practitioner, LicenseNumber)` pairs appear more than once** — the same licence number recurs with a later `PRM_ProviderLicenseExpirationDate__c` on each renewal (see `RN666255` above: identical effective date, expirations 2025-10-31 and 2027-10-31). This is *not* duplicate data; if you want one row per licence take the max expiration per `LicenseNumber`, or use Query 2b.
- **`IsActive` does not track expiry — do not use it as a currency filter.** Cross-tab of the 540 rows with an expiration date: `IsActive = true` **and expired** = 209; `IsActive = false` **and unexpired** = 131. Filter on `PRM_ProviderLicenseExpirationDate__c` instead.
- **`Status` is only 26% populated** (`Verified` on 141 rows, null on 401), so never filter on it — you would drop three quarters of the population. `VerificationStatus` is `Authorized` on 100% of rows, making it useless as a discriminator.
- `LicenseClass` is `SBRD` on 540 rows and `DEA` on 2 — add `AND LicenseClass = 'SBRD'` if you want to exclude DEA registrations.
- A child subquery cannot be filtered from the outer `WHERE`; a practitioner with no matching licence still returns with an empty/`null` subquery rather than being excluded.

---

## Query 2b — Current (unexpired) licences only

**Use case:** Same as 2a but limited to licences still in force as of today — the usual question for professional-staff verification.

```sql
       (SELECT Id, LicenseNumber, LicenseClass, PRM_LicenseState__c,
               IsPrimaryLicense,
               PRM_ProviderLicenseEffectiveDate__c,
               PRM_ProviderLicenseExpirationDate__c
        FROM PersonBusinessLicenses
        WHERE PRM_IsError__c = false
          AND PRM_Pending__c = false
          AND PRM_ProviderLicenseExpirationDate__c >= TODAY
        ORDER BY PRM_ProviderLicenseExpirationDate__c DESC)
```

(Drop this subquery into Query 2a in place of the existing one.)

**Sample result / row count:** 322 unexpired licence rows, covering **317 of the 423** practitioners — i.e. **106 professional staff have no unexpired licence on file**, which is the number worth escalating.

**Notes / gotchas:** `TODAY` is an unquoted SOQL date literal. Because the subquery filter cannot exclude parent rows, all 423 practitioners still return; count the ones with a non-empty subquery to get 317.

---

## Query 2c — Flat, one-row-per-licence export (two steps)

**Use case:** CSV export where nested subqueries are awkward.

SOQL rejects `WHERE Contact.AccountId IN (SELECT ...)` (*"ERROR at Row:1:Column:72"*) and rejects nesting a semi-join inside a semi-join (*"Nesting of semi join sub-selects is not supported"*), so this cannot be done in one statement. Two steps:

```sql
-- Step 1: collect the person contact Ids
SELECT PersonContactId
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND Id IN (
      SELECT PRM_Account__c
      FROM PRM_InfoCodeAssignment__c
      WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
        AND PRM_Active__c = true
        AND PRM_IsErrorRecord__c = false
        AND PRM_Account__c != NULL
  )
```

```sql
-- Step 2: paste the Ids into an explicit IN list
SELECT Id, ContactId, Contact.Account.Name,
       LicenseNumber, LicenseClass, PRM_LicenseState__c,
       Status, IsPrimaryLicense, IsActive,
       IssueDate, VerifiedDate,
       PRM_ProviderLicenseEffectiveDate__c,
       PRM_ProviderLicenseExpirationDate__c
FROM BusinessLicense
WHERE ContactId IN ('003...','003...')
  AND PRM_IsError__c = false
ORDER BY Contact.Account.Name, PRM_ProviderLicenseExpirationDate__c DESC
```

**Notes / gotchas:** `Contact.Account.Name` traversal works fine in the SELECT and ORDER BY — it is only the **semi-join left-hand side** that rejects a traversed field. With 423 practitioners the `IN` list is well within SOQL's limits.

---

## Query 3 — Assignment-level detail (effective dates and provenance)

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Same population, but returns the assignment rows — needed when you care about *when* the practitioner became professional staff, or which flow created the code.

```sql
SELECT Id, Name,
       PRM_Account__c, PRM_Account__r.Name,
       PRM_Account__r.PRM_CredentialingStatus__c,
       PRM_Account__r.PRM_PNC__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       PRM_Active__c, PRM_Pending__c, PRM_IsErrorRecord__c,
       PRM_CaseManager__c,
       PRM_CaseManager__r.RecordType.DeveloperName,
       PRM_RequestType__c, PRM_ExternalId__c,
       CreatedDate, LastModifiedDate
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
  AND PRM_Active__c = true
  AND PRM_IsErrorRecord__c = false
  AND PRM_Account__r.RecordType.DeveloperName = 'PRM_Practitioner'
ORDER BY PRM_EffectiveFrom__c DESC
```

**Sample result / row count:** **423 rows** — identical to Query 2's 423 practitioners, i.e. **no practitioner holds more than one active C64**. Sampled rows are all `PRM_Pending__c = false`, `PRM_EffectiveTo__c = null`, and created from `PRM_PDMManualChange` case managers.

**Notes / gotchas:** `PRM_Account__r.RecordType.DeveloperName = 'PRM_Practitioner'` is redundant given C64 is account-only, but it is the filter the existing DataRaptors use (`PRMDRExtractActivePractitionerByLastName`, `PRMDRExtractActivePractitionerByFirstName`) and it guards against a mis-parented row.

---

## Query 4 — Population sizing / reconciliation

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Understand the whole C64 population and why rows drop out of the active set.

```sql
SELECT PRM_Active__c a, PRM_Pending__c p, PRM_IsErrorRecord__c e, COUNT(Id) c
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
GROUP BY PRM_Active__c, PRM_Pending__c, PRM_IsErrorRecord__c
```

**Result (FC2, 2026-09-01) — 461 C64 assignments total:**

| Active | Pending | Error | Count | Meaning |
|---|---|---|---|---|
| `true` | `false` | `false` | **423** | current IBC Professional Staff |
| `false` | `false` | `false` | 37 | **terminated** professional staff |
| `false` | `false` | `true` | 1 | error record — exclude |

**Notes / gotchas:** all 37 inactive non-error rows have `PRM_EffectiveTo__c` populated (33 in 2025, 4 in 2026) — they are **terminations**, not future-dated assignments. There are **no pending C64 rows** in this org.

---

## Query 5 — Credentialing status breakdown of the active population

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Sanity-check the population — professional staff are expected to be credentialed.

```sql
SELECT PRM_Account__r.PRM_CredentialingStatus__c s, COUNT(Id) c
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
  AND PRM_Active__c = true
  AND PRM_IsErrorRecord__c = false
  AND PRM_Account__r.RecordType.DeveloperName = 'PRM_Practitioner'
GROUP BY PRM_Account__r.PRM_CredentialingStatus__c
ORDER BY COUNT(Id) DESC
```

**Result (FC2, 2026-09-01):**

| Credentialing status | Count | Share |
|---|---|---|
| `Credentialed` | 383 | 90.5% |
| *(null)* | 29 | 6.9% |
| `Credentialing In Progress` | 11 | 2.6% |

**Notes / gotchas:** the intake DataRaptor `PRMDRCreateCaseCaseManagerAndAccount` sets `CredentialingStatus = 'Credentialed'` when `PractitionerCreationType == "IBC Professional Staff"`, so the 29 null + 11 in-progress rows are worth a look — they suggest C64 was applied via PDM manual change outside the professional-staff intake path. Related known defect: `requirements/PRM_PNC_CredentialingStatus_Blank_User_Story.md`.

---

## Query 6 — Terminated professional staff

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** The 37 practitioners whose professional staff designation has ended — needed for the termination/verification flows.

```sql
SELECT PRM_Account__c, PRM_Account__r.Name,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       PRM_CaseManager__r.PRM_ProfessionalStaffTerminationDate__c,
       PRM_CaseManager__r.RecordType.DeveloperName
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'C64'
  AND PRM_IsErrorRecord__c = false
  AND PRM_EffectiveTo__c != NULL
  AND PRM_EffectiveTo__c <= TODAY
ORDER BY PRM_EffectiveTo__c DESC
```

**Sample result / row count:** 37 rows (FC2, 2026-09-01).

**Notes / gotchas:**
- `PRM_ProfessionalStaffTerminationDate__c` and `PRM_ProfessionalStaffVerificationNotes__c` live on **`IndividualApplication`**, **not** on `Account` — reaching them from the assignment requires `PRM_CaseManager__r.` (the assignment's `PRM_CaseManager__c` lookup points at `IndividualApplication`). Querying `PRM_Account__r.PRM_ProfessionalStaffTerminationDate__c` fails with *"No such column ... on entity 'Account'"*.
- The assignment's `PRM_EffectiveTo__c` is the authoritative end date for the *code*. In the sampled terminated rows `PRM_CaseManager__r.PRM_ProfessionalStaffTerminationDate__c` is `null` (those codes were ended via `PRM_PDMManualChange`, not the professional-staff verification flow) — so do not rely on the verification date to find terminations; filter on `PRM_EffectiveTo__c`.

---

## Variations

**Count only** — swap the field list for `SELECT COUNT()`.

**Filter by name** (mirrors the existing DataRaptors, which search professional staff by first/last name):

```sql
AND PRM_Account__r.LastName LIKE '%Smith%'
```

**Include terminated as well as active** — drop `AND PRM_Active__c = true` and keep only `AND PRM_IsErrorRecord__c = false`, then read `PRM_EffectiveTo__c` per row.

**Filter by the `Name` string instead of the code** (what the DataRaptors do):

```sql
AND PRM_InfoCode__r.Name = 'C64-IBC Professional Staff'
```

---

## Cross-links

- Grounding DataRaptors: `PRMDRExtractActivePractitionerByLastName_1`, `PRMDRExtractActivePractitionerByFirstName_1` (both filter `PRM_InfoCode__r.Name = 'C64-IBC Professional Staff'` + `PRM_Active__c = true` + `PRM_Account__r.RecordType.DeveloperName = 'PRM_Practitioner'`), `PRMFetchAccountAndPracticeLocations_1` and `PRMDrExtractPractForProfStaff_1` (both derive an `InfoC64` flag from `PRM_InfoCode__r.PRM_Code__c == "C64"`).
- Intake branch: `PRM_PractitionerCreationContainer_Procedure_6` (`PractitionerCreationType == "IBC Professional Staff"` → `PRM_PractitionerCreation` IP).
- Related stories: `requirements/IBC_ProfStaffVerification_Batch_UserStory.md`, `requirements/IBC_ProfStaffVerification_Flow_UserStory.md`, `requirements/IBC_ProfStaffVerification_Termination_UserStory.md`, `requirements/IBC_ProfStaffVerification_Config_UserStory.md`.
- Sibling info-code SOQL (practice-location level): `requirements/SOQL/2026-08-19_M03SoleProprietorInfoCode.md`.
