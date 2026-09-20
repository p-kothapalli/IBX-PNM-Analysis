# Per-Step Verification Dates — SOQL Archive

**Date:** 2026-06-01
**Context:** Business asked: "do we have License Verified On / Specialty Verified On / etc. dates like we have NPDB Verified On?"

> **⚠️ MAJOR CORRECTION (added 2026-06-01 PM):** This file's original conclusion that "only `PRM_NPDBVerifiedOn__c` and `PRM_AccreditationVerifiedOn__c` exist" was **incomplete**. It only looked on the `IndividualApplication` parent. The per-credential verification dates DO exist — on the **child credential objects** (`BusinessLicense`, `PersonEducation`, `License`, `BoardCertification`, `PractitionerDegree`) as the standard Health Cloud field **`VerifiedDate`** (UI label "Verified On"). See "Per-Credential VerifiedDate Queries" section below — this is the **recommended path** for the business.

**Related:** [`2026-05-29_CaseManagerFieldHistory.md`](./2026-05-29_CaseManagerFieldHistory.md) — base history audit queries.

---

## Query 1 — Latest verification timestamp per field per Case Manager (long format)

**Object:** `IndividualApplicationHistory`
**Use case:** Returns one row per `(Case Manager × Field)` with the most recent timestamp when that field was edited to a non-blank value. Treat `MAX(CreatedDate)` as the per-step "Verified On" date. Long format = good for pivoting in Excel.

```sql
SELECT 
  IndividualApplicationId,
  IndividualApplication.Name,
  IndividualApplication.Account.Name,
  Field,
  MAX(CreatedDate) LatestVerifiedOn,
  COUNT(Id) ChangeCount
FROM IndividualApplicationHistory
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <= 2026-05-31T23:59:59Z
  AND Field IN (
    'PRM_SpecialtyVerification__c','PRM_EducationVerification__c',
    'PRM_LicenseVerification__c','PRM_WorkHistoryVerification__c',
    'PRM_DEAVerification__c','PRM_MalpracticeCoverageVerification__c',
    'PRM_CDSVerification__c','PRM_AttestationVerification__c',
    'PRM_NPDBVerifiedOn__c','PRM_ContractStatus__c','PRM_CAQHAttestation__c',
    'PRM_ServiceAreaPSV__c','PRM_LicensePSV__c','PRM_SpecialtyPSV__c',
    'PRM_AdmittingPrivilegesReview__c','PRM_InsurancePSV__c',
    'PRM_EducationPSV__c','PRM_WorkHistoryPSV__c','PRM_CDSPSV__c',
    'PRM_DEAPSV__c','PRM_BoardCertificationPSV__c','PRM_DisclosureReview__c',
    'PRM_MedicareOptOutReview__c','PRM_FSMBPSV__c','PRM_SAMReview__c',
    'PRM_CMSPreclusionReview__c','PRM_PSVOutcome__c'
  )
GROUP BY IndividualApplicationId, IndividualApplication.Name, IndividualApplication.Account.Name, Field
ORDER BY IndividualApplication.Name, Field
```

**Notes:**
- `MAX(CreatedDate)` returns the **last time** that field changed. If a field was set on 5/10 then changed again on 5/18, this returns 5/18 — the "current" verified-on date.
- Drop fields with zero history rows: `PRM_NPDBVerified__c`, `PRM_NPDBErrorMessage__c`, `PRM_HospitalAffiliations__c` (already excluded above).
- For Apex GROUP BY relationship fields up to 2 levels (`IndividualApplication.Account.Name`) — supported.
- Output volume: ~198 unique Case Managers × 27 fields = up to ~5,346 rows worst case (typically far fewer since not every field is set on every record).

---

## Query 2 — Latest "Data Looks Good" timestamp only (filter to true completions)

**Object:** `IndividualApplicationHistory`
**Use case:** Same as Query 1 but only counts edits where the NewValue was set to "Data Looks Good" — filtering out cases where the field was set to "Issue", "Pended", or cleared. This is the **strictest** definition of "Verified On."

```sql
SELECT 
  IndividualApplicationId,
  IndividualApplication.Name,
  IndividualApplication.Account.Name,
  Field,
  MAX(CreatedDate) VerifiedOn
FROM IndividualApplicationHistory
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <= 2026-05-31T23:59:59Z
  AND NewValue = 'Data Looks Good'
  AND Field IN (
    'PRM_SpecialtyVerification__c','PRM_EducationVerification__c',
    'PRM_LicenseVerification__c','PRM_WorkHistoryVerification__c',
    'PRM_DEAVerification__c','PRM_MalpracticeCoverageVerification__c',
    'PRM_CDSVerification__c','PRM_AttestationVerification__c',
    'PRM_ContractStatus__c','PRM_CAQHAttestation__c',
    'PRM_ServiceAreaPSV__c','PRM_LicensePSV__c','PRM_SpecialtyPSV__c',
    'PRM_AdmittingPrivilegesReview__c','PRM_InsurancePSV__c',
    'PRM_EducationPSV__c','PRM_WorkHistoryPSV__c','PRM_CDSPSV__c',
    'PRM_DEAPSV__c','PRM_BoardCertificationPSV__c','PRM_DisclosureReview__c',
    'PRM_MedicareOptOutReview__c','PRM_FSMBPSV__c','PRM_SAMReview__c',
    'PRM_CMSPreclusionReview__c'
  )
GROUP BY IndividualApplicationId, IndividualApplication.Name, IndividualApplication.Account.Name, Field
ORDER BY IndividualApplication.Name, Field
```

**Notes:**
- `OldValue` and `NewValue` are typed as `string` on the History table. Equality comparisons (`= 'Data Looks Good'`) work for picklist string values.
- Excluded `PRM_PSVOutcome__c` and `PRM_NPDBVerifiedOn__c` because their valid values are NOT "Data Looks Good" (PSV Outcome = "Route to Final Development" / "PSV QC"; NPDBVerifiedOn = a date string).
- For the strict business semantic: only rows where the verifier said "verified" — exactly what business wants for "Verified On."

---

## Query 3 — One row per Case Manager with NPDB & Accreditation Verified-On (already explicit fields)

**Object:** `IndividualApplication`
**Use case:** For the two fields that DO have dedicated `VerifiedOn` columns, you don't need history at all — they're directly queryable on the parent.

```sql
SELECT 
  Id,
  Name,
  Account.Name,
  PRM_Stage__c,
  PRM_NPDBVerifiedOn__c,
  PRM_NPDBPulledDate__c,
  PRM_AccreditationVerifiedOn__c,
  PRM_HACACDecisionDate__c,
  PRM_ApprovedDate__c,
  PRM_Decision_Date__c
FROM IndividualApplication
WHERE PRM_NPDBVerifiedOn__c >= 2026-01-01
   OR PRM_AccreditationVerifiedOn__c >= 2026-01-01
   OR PRM_ApprovedDate__c >= 2026-01-01
ORDER BY Name
```

**Notes:**
- Date fields use `YYYY-MM-DD` (no quotes, no time component) in SOQL WHERE.
- This is the *current* state of each Case Manager — not a history audit. Combine with Query 2 for full picture.

---

## Query 4 — Wide-format pivot via Apex (only viable option for true wide CSV)

**Object:** `IndividualApplicationHistory` + Apex
**Use case:** Business probably wants ONE row per Case Manager with columns: `License Verified On | Specialty Verified On | DEA Verified On | …`. **SOQL cannot pivot** — it returns long format only. Wide-format requires Apex post-processing or Excel pivot. Below is the Apex pseudo-pattern; full implementation belongs in the export tool we're scoping.

```sql
-- Step 1: pull long format via Query 2 above
-- Step 2: in Apex (or Excel), reshape to wide:

Map<Id, Map<String, Datetime>> ia2FieldDate = new Map<Id, Map<String, Datetime>>();
for (AggregateResult ar : [SELECT IndividualApplicationId, Field, MAX(CreatedDate) verifiedOn FROM IndividualApplicationHistory WHERE NewValue = 'Data Looks Good' GROUP BY IndividualApplicationId, Field]) {
    Id iaId = (Id) ar.get('IndividualApplicationId');
    String fld = (String) ar.get('Field');
    Datetime dt = (Datetime) ar.get('verifiedOn');
    if (!ia2FieldDate.containsKey(iaId)) ia2FieldDate.put(iaId, new Map<String, Datetime>());
    ia2FieldDate.get(iaId).put(fld, dt);
}
// Then build CSV with columns = the 27 fields, rows = Case Managers, cells = dates
```

**Notes:**
- This is the algorithm that will live inside `PRM_CaseManagerHistoryExportController` if you go forward with the export tool.
- Excel alternative: take Query 2 output → Insert PivotTable → Rows = Case Manager #, Columns = Field, Values = MAX of VerifiedOn → format cells as date. Same result without Apex.

---

## Field reference — date fields on IndividualApplication

| API Name | Label | Type | Purpose |
|---|---|---|---|
| `PRM_NPDBVerifiedOn__c` | NPDB Verified On | Date | ✅ NPDB verification timestamp |
| `PRM_AccreditationVerifiedOn__c` | Accreditation Verified On | Date | ✅ Accreditation verification timestamp (Ancillary) |
| `PRM_NPDBPulledDate__c` | NPDB Pulled Date | Date | When NPDB report was pulled (≠ verified) |
| `PRM_HACACDecisionDate__c` | HACAC Decision Date | Date | Committee decision |
| `PRM_Decision_Date__c` | Decision Date | Date | General decision |
| `PRM_ApprovedDate__c` | Approved Date | Date | Final approval |
| `PRM_CorporateReceiptDate__c` | Corporate Receipt Date | Date | Application receipt |
| `PRM_SiteVisitStateSurveyDate__c` | Site Visit / State Survey Date | Date | Site visit |
| `PRM_ReCredDueDate__c` | Re-cred Due Date | Date | Future-dated re-cred trigger |
| `PRM_OnHoldExpirationDate__c` | On Hold Expiration Date | Date | Hold expiry |
| `PRM_NonParticipatingStartDate__c` | Non-Participating Start Date | Date | Status change |
| `PRM_DataValidationDate__c` | Data Validation Date | Date | Data QC completion |
| `PRM_ConciergeOfferedPriorToDate__c` | Concierge Offered Prior To Date | Date | Concierge offer |
| `PRM_PhysicalTherapyEffectiveDate__c` | PT Effective Date | Date | Service-line effective |
| `PRM_RadiologyEffectiveDate__c` | Radiology Effective Date | Date | Service-line effective |
| `PRM_LaboratoryEffectiveDate__c` | Lab Effective Date | Date | Service-line effective |
| `AppliedDate` (standard) | Applied Date | Date | App submission |
| `RequirementsCompleteDate` (standard) | Requirements Complete Date | Date | Requirements milestone |
| `PaymentDate` (standard) | Payment Date | Date | Payment received |
| `ApprovedDate` (standard) | Approved Date (std) | Date | Standard approval |

**Conclusion (about IndividualApplication-level dates):** No `*VerifiedOn__c` field exists *on `IndividualApplication`* for the per-step App Review or PSV validations except NPDB and Accreditation. **However** — see the next section: per-credential `VerifiedDate` fields DO exist on the child credential objects (BusinessLicense, PersonEducation, etc.) and are the recommended path.

---

# Per-Credential VerifiedDate Queries (RECOMMENDED PATH)

**Discovered:** 2026-06-01 PM — user pointed out the "Verified On" date field on a Business License record (5/25/2026 in screenshot). Codebase scan confirms `VerifiedDate` is a Salesforce Health Cloud **standard field** present on multiple credential objects, all with `PRM_CaseManager__c` FK back to IndividualApplication and FLS already granted in `PRM_CredentialingUser`, `PRM_DataViewAll`, `PRM_DataModifyAll`, `PRM_NetworkManagementQC`, `PRM_ProviderDataAdmin`, `PRM_RebtuttalSpecialist`, `PRM_AncillaryCredSpecialist`.

**Why this is better than the IndividualApplicationHistory approach (Queries 1-4 above):**
- Direct queryable date — no MAX/GROUP BY inference
- Reportable in standard Salesforce Reports (no Custom Report Type limitation)
- Per-credential granularity (each license, each degree gets its own date)
- NCQA audit-friendly (vendor data dictionary already maps these fields)
- Works today against existing data

---

## Query 5 — BusinessLicense VerifiedDate by Case Manager

**Object:** `BusinessLicense` (Health Cloud standard)
**Use case:** "When was each license on each Case Manager verified?" The exact question the business asked, answered cleanly per-license.

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name CaseManagerNum,
  PRM_CaseManager__r.Account.Name ProviderName,
  PRM_CaseManager__r.PRM_Stage__c Stage,
  Id,
  LicenseNumber,
  LicenseClass,
  PRM_LicenseState__c,
  Status,
  VerifiedDate,
  PRM_ProviderLicenseEffectiveDate__c,
  PRM_ProviderLicenseExpirationDate__c,
  PRM_IsError__c,
  PRM_Pending__c,
  LastModifiedDate,
  LastModifiedBy.Name
FROM BusinessLicense
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY PRM_CaseManager__r.Name, VerifiedDate DESC
```

**Notes:**
- `VerifiedDate` is the **standard Salesforce Industries field** (not a `PRM_*__c` custom field).
- UI label is "Verified On" (per the Business License record screenshot 2026-06-01).
- `Status` enum includes `'Verified'`, `'Pending'`, `'Error'`, etc.
- Filter `Status = 'Verified'` if business wants only completed verifications.

---

## Query 6 — PersonEducation VerifiedDate by Case Manager

**Object:** `PersonEducation` (Health Cloud standard)
**Use case:** "When was each education record on each Case Manager verified?" Education-level granularity (one row per degree).

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name CaseManagerNum,
  PRM_CaseManager__r.Account.Name ProviderName,
  Id,
  PRM_Degree__r.Name Degree,
  PRM_Institution__c Institution,
  PRM_GraduationDate__c GraduationDate,
  PRM_Status__c Status,
  PRM_Primary__c IsPrimaryDegree,
  VerifiedDate,
  PRM_EffectiveFrom__c,
  PRM_EffectiveTo__c,
  PRM_IsErrorRecord__c,
  PRM_Pending__c,
  LastModifiedDate,
  LastModifiedBy.Name
FROM PersonEducation
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY PRM_CaseManager__r.Name, VerifiedDate DESC
```

**Notes:**
- Per vendor data dictionary, this is the NCQA audit-trail field.
- `PRM_Primary__c = true` flags the practitioner's primary degree if the business needs to filter to that.

---

## Query 7 — BoardCertification by Case Manager (with VerifiedDate test)

**Object:** `BoardCertification` (Health Cloud standard)
**Use case:** Board certification verification dates. **VerifiedDate not yet confirmed in code** — run query first to confirm field is present in your org.

```sql
-- Run FIRST in Developer Console / Anonymous Apex to verify VerifiedDate is queryable:
-- System.debug(Schema.SObjectType.BoardCertification.fields.getMap().keySet());

SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name CaseManagerNum,
  PRM_CaseManager__r.Account.Name ProviderName,
  Id,
  PRM_Taxonomy__r.Name Specialty,
  PRM_BoardOriginal__c OriginalCertDate,
  PRM_BoardReCert__c LastRecertDate,
  PRM_Status__c Status,
  PRM_Active__c IsActive,
  VerifiedDate,
  PRM_EffectiveFrom__c,
  PRM_EffectiveTo__c,
  PRM_IsErrorRecord__c,
  PRM_Pending__c,
  LastModifiedDate,
  LastModifiedBy.Name
FROM BoardCertification
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY PRM_CaseManager__r.Name, VerifiedDate DESC
```

**Notes:**
- If query returns `INVALID_FIELD: No such column 'VerifiedDate' on entity 'BoardCertification'`, the field doesn't exist on this object in your edition — fall back to `LastModifiedDate` as the verification proxy, or check `PRM_BoardCertificationVerification__c` on the parent IndividualApplication via Query 2.
- `BoardCertification` is the standard Health Cloud object — verify field availability in QA org before relying on it.

---

## Query 8 — License VerifiedDate (separate from BusinessLicense — verify object exists in org)

**Object:** `License` (Health Cloud / Public Sector Solutions standard — may or may not be in this org)
**Use case:** Some Salesforce Industries orgs have BOTH `BusinessLicense` and a separate `License` object. Codebase has DataRaptor references to `License:VerifiedDate` (`PRMTransQCDataNoCAQH`, `PRMTransAppReviewNoCAQHDetails`).

```sql
-- Run FIRST to confirm object exists:
-- SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = 'License'

SELECT 
  Id,
  Name,
  Status,
  VerifiedDate,
  LastModifiedDate,
  LastModifiedBy.Name
FROM License
WHERE VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY VerifiedDate DESC
LIMIT 100
```

**Notes:**
- If the org doesn't have the `License` standard object, query fails with `sObject type 'License' is not supported`. Then BusinessLicense (Query 5) is the only license object in use.
- The DataRaptor references could be using `License` as a generic input alias even when the actual SObject is BusinessLicense — confirm via `Schema.getGlobalDescribe().keySet()`.

---

## Query 9 — Combined per-Case-Manager verification dashboard (multi-object Apex pattern)

**Use case:** "For each Case Manager record, list ALL verified credentials and their dates in one row/output." SOQL alone can't UNION across different SObjects — requires Apex post-processing.

```apex
// Pattern: aggregate per Case Manager → Map<credentialType, MAX(VerifiedDate)>
Map<Id, Map<String, Date>> caseMgrCredDates = new Map<Id, Map<String, Date>>();

// Business Licenses
for (BusinessLicense bl : [
    SELECT PRM_CaseManager__c, VerifiedDate 
    FROM BusinessLicense 
    WHERE PRM_CaseManager__c != null 
      AND VerifiedDate >= 2026-01-01
      AND VerifiedDate <= 2026-05-31
]) {
    if (!caseMgrCredDates.containsKey(bl.PRM_CaseManager__c)) {
        caseMgrCredDates.put(bl.PRM_CaseManager__c, new Map<String, Date>());
    }
    Date current = caseMgrCredDates.get(bl.PRM_CaseManager__c).get('LicenseVerifiedOn');
    if (current == null || bl.VerifiedDate > current) {
        caseMgrCredDates.get(bl.PRM_CaseManager__c).put('LicenseVerifiedOn', bl.VerifiedDate);
    }
}

// Person Education
for (PersonEducation pe : [
    SELECT PRM_CaseManager__c, VerifiedDate 
    FROM PersonEducation 
    WHERE PRM_CaseManager__c != null 
      AND VerifiedDate >= 2026-01-01
      AND VerifiedDate <= 2026-05-31
]) {
    if (!caseMgrCredDates.containsKey(pe.PRM_CaseManager__c)) {
        caseMgrCredDates.put(pe.PRM_CaseManager__c, new Map<String, Date>());
    }
    Date current = caseMgrCredDates.get(pe.PRM_CaseManager__c).get('EducationVerifiedOn');
    if (current == null || pe.VerifiedDate > current) {
        caseMgrCredDates.get(pe.PRM_CaseManager__c).put('EducationVerifiedOn', pe.VerifiedDate);
    }
}

// Repeat for BoardCertification, License (if it exists), PractitionerDegree
// Then build CSV: rows = Case Manager Ids, columns = LicenseVerifiedOn, EducationVerifiedOn, BoardCertVerifiedOn, ...
```

**Notes:**
- This is the algorithm that should live inside `PRM_CaseManagerHistoryExportController.getVerifiedOnDates()` if you go forward with the export tool. ~80 lines of Apex.
- Excel alternative: Run Queries 5, 6, 7 separately → 3 CSVs → join in Excel using `PRM_CaseManager__r.Name` as the key (VLOOKUP / Power Query). Same result without Apex.

---

## Field reference — Per-credential VerifiedDate fields

| Object | Field | Type | UI Label | API Status |
|---|---|---|---|---|
| `BusinessLicense` | `VerifiedDate` | Date | Verified On | ✅ Confirmed (used in PRM_BusinessLicenseControllerHelper) |
| `PersonEducation` | `VerifiedDate` | Date | Verified On / Source Verified On | ✅ Confirmed (NCQA audit field per vendor dictionary) |
| `License` | `VerifiedDate` | Date | Verified On | ⚠️ Referenced in DataRaptors — verify object exists in this org |
| `BoardCertification` | `VerifiedDate` | Date | Verified On | ⚠️ Standard Health Cloud field — verify availability in QA org |
| `PractitionerDegree` | `VerifiedDate` | Date | Verified On | ✅ Used in DataRaptors (PRMCAQHReviewTransform formula) |

## Linkage back to Case Manager

All confirmed credential objects have `PRM_CaseManager__c` (Lookup → IndividualApplication) — see permission set evidence:

| Object | FK to IndividualApplication | Source of confirmation |
|---|---|---|
| `BusinessLicense` | `PRM_CaseManager__c` | `PRM_CredentialingUser.permissionset` line 731, `PRM_AncillaryCredSpecialist` line 673 |
| `PersonEducation` | `PRM_CaseManager__c` | `PRM_CredentialingUser.permissionset` line 6506 |
| `BoardCertification` | `PRM_CaseManager__c` | `PRM_CredentialingUser.permissionset` line 596, `PRM_Base.permissionset` line 181 |

---

## Final recommendation (supersedes prior recommendation)

| Path | Effort | Result |
|---|---|---|
| ~~Path A — derive from `IndividualApplicationHistory`~~ | 0 dev days | Works but complex (MAX(CreatedDate), Custom Report Type limitations) |
| **Path C — query per-credential `VerifiedDate` directly (Queries 5-9)** | **0 dev days** | **Best path. Cleaner data, reportable today, NCQA audit-aligned.** |
| Path B — add 27 new `*VerifiedOn__c` fields on IndividualApplication | ~10–15 dev days | Not needed — per-credential dates already exist |

**Strong recommendation: Path C.** Update the `PRM_CaseManagerHistoryExport` tool spec to add a third output mode — "Per-Credential Verification Dates" — that runs Queries 5/6/7/8 in parallel and joins by Case Manager. ~1 extra dev day vs. the IndividualApplicationHistory path.

For an immediate one-time export to deliver to the business this week:
1. Run Query 5 → `BusinessLicense_VerifiedOn_JanMay.csv`
2. Run Query 6 → `PersonEducation_VerifiedOn_JanMay.csv`
3. Run Query 7 (after confirming VerifiedDate field) → `BoardCertification_VerifiedOn_JanMay.csv`
4. Open all three in Excel, key on Case Manager #, build a master sheet with one row per Case Manager, columns for each credential type's most-recent VerifiedDate.

---

# Combined Multi-Source Export Set — Normalized Queries (RECOMMENDED FOR ONE-TIME PULL)

**Added:** 2026-06-01 PM
**Use case:** Business asked for the IndividualApplicationHistory query AND the per-credential VerifiedDate data **in one consolidated extract** for Jan 1 – May 31 2026.

**SOQL constraint:** SOQL cannot UNION across SObjects. Solution = run all 5 queries below (each in Workbench → Queries → SOQL Query → "Bulk CSV"), then stack the CSVs in Excel. **All 5 queries return the same logical column shape**, so concatenation is trivial.

> **The LWC `prmCaseManagerHistory` (see `requirements/Enhancements/PRM_CaseManagerUnifiedHistoryLWC_UserStory.md`) merges these same 5 sources server-side and renders them in a unified record-page table — this query set is the manual one-time equivalent.**

## Normalized output columns (all 5 queries)

Every query returns these columns in this order. Column **labels** differ slightly because SOQL aliases can't include spaces or string literals — but the **positions** are identical, so a CSV stack works:

| Position | Logical column | Notes |
|---|---|---|
| 1 | Case Manager Id | `IndividualApplicationId` or `PRM_CaseManager__c` |
| 2 | Case Manager # | `IndividualApplication.Name` (e.g. `IA-0000151779`) |
| 3 | Provider Name | `Account.Name` of the Case Manager |
| 4 | Stage | `PRM_Stage__c` of the Case Manager |
| 5 | Source | **Add manually in Excel** — set per-CSV before concat: `'FieldHistory'`, `'BusinessLicense'`, `'PersonEducation'`, `'BoardCertification'`, `'License'` |
| 6 | What Changed | `Field` name (history) OR credential identifier (license #, degree, etc.) |
| 7 | Old Value | `OldValue` (history); blank for credentials |
| 8 | New Value | `NewValue` (history); `Status` (credentials) |
| 9 | Event Date | `CreatedDate` (history) or `VerifiedDate` (credentials) |
| 10 | By User | `CreatedBy.Name` (history) or `LastModifiedBy.Name` (credentials) |
| 11 | By Profile | `CreatedBy.Profile.Name` or `LastModifiedBy.Profile.Name` |

---

## Query A — IndividualApplicationHistory (the original, normalized)

```sql
SELECT 
  IndividualApplicationId,
  IndividualApplication.Name,
  IndividualApplication.Account.Name,
  IndividualApplication.PRM_Stage__c,
  Field,
  OldValue,
  NewValue,
  CreatedDate,
  CreatedBy.Name,
  CreatedBy.Profile.Name
FROM IndividualApplicationHistory
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <= 2026-05-31T23:59:59Z
  AND Field IN (
    'PRM_SpecialtyVerification__c','PRM_EducationVerification__c',
    'PRM_LicenseVerification__c','PRM_WorkHistoryVerification__c',
    'PRM_DEAVerification__c','PRM_MalpracticeCoverageVerification__c',
    'PRM_CDSVerification__c','PRM_AttestationVerification__c',
    'PRM_NPDBVerified__c','PRM_NPDBVerifiedOn__c','PRM_NPDBErrorMessage__c',
    'PRM_ContractStatus__c','PRM_CAQHAttestation__c',
    'PRM_ServiceAreaPSV__c','PRM_LicensePSV__c','PRM_SpecialtyPSV__c',
    'PRM_AdmittingPrivilegesReview__c','PRM_InsurancePSV__c',
    'PRM_HospitalAffiliations__c','PRM_EducationPSV__c',
    'PRM_WorkHistoryPSV__c','PRM_CDSPSV__c','PRM_DEAPSV__c',
    'PRM_BoardCertificationPSV__c','PRM_DisclosureReview__c',
    'PRM_MedicareOptOutReview__c','PRM_FSMBPSV__c','PRM_SAMReview__c',
    'PRM_CMSPreclusionReview__c','PRM_PSVOutcome__c',
    'PRM_AccreditationVerifiedOn__c','PRM_AccreditationReview__c',
    'PRM_NPDBPulledDate__c','PRM_NPDBReceived__c','PRM_NPDBIssue__c'
  )
ORDER BY CreatedBy.Name, IndividualApplicationId, CreatedDate DESC
```

**In Excel after export:** Add a new column `Source` and fill all rows with `FieldHistory`.

**Field expansion log (added 2026-06-01 PM):**

| Field | Type | Why included |
|---|---|---|
| `PRM_AccreditationVerifiedOn__c` | Date | The second `*VerifiedOn__c` field on IndividualApplication (sister to `PRM_NPDBVerifiedOn__c`). Captures when accreditation status was verified. Was missing from the original IN list. |
| `PRM_AccreditationReview__c` | Picklist | Outcome of accreditation review (e.g. `Data Looks Good`). Same shape as the existing `PRM_*Review__c` and `PRM_*PSV__c` outcome fields. |
| `PRM_NPDBPulledDate__c` | Date | When the NPDB report was pulled — closes the audit loop for the NPDB workflow alongside the existing `PRM_NPDBVerifiedOn__c` and `PRM_NPDBVerified__c`. |
| `PRM_NPDBReceived__c` | Boolean | Confirms NPDB report was received (precursor to verified). |
| `PRM_NPDBIssue__c` | Picklist | Captures NPDB report issue/error — pairs with `PRM_NPDBErrorMessage__c`. |

> **Field history tracking note:** These 5 expansion fields will only return rows if FHT is enabled on each. Run this diagnostic query once after deployment to confirm which fields are actually being tracked:
> ```sql
> SELECT Field, COUNT(Id) cnt FROM IndividualApplicationHistory
> WHERE Field IN ('PRM_AccreditationVerifiedOn__c','PRM_AccreditationReview__c',
>                 'PRM_NPDBPulledDate__c','PRM_NPDBReceived__c','PRM_NPDBIssue__c')
> GROUP BY Field
> ```
> If a field returns 0 rows but FHT IS enabled, the field simply hasn't changed in the date window. If FHT is NOT enabled (verify via Object Manager → IndividualApplication → Set History Tracking), no historical rows exist before today — same situation as the May 10-29 boundary you saw with the original 30 fields.

---

## Query B — BusinessLicense (per-license VerifiedDate)

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name,
  PRM_CaseManager__r.Account.Name,
  PRM_CaseManager__r.PRM_Stage__c,
  LicenseClass,
  LicenseNumber,
  PRM_LicenseState__c,
  Status,
  VerifiedDate,
  LastModifiedBy.Name,
  LastModifiedBy.Profile.Name
FROM BusinessLicense
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY LastModifiedBy.Name, PRM_CaseManager__c, VerifiedDate DESC
```

**In Excel after export:**
- Add `Source` column = `BusinessLicense`
- Build a `What Changed` column = `="License: " & LicenseClass & " / " & PRM_LicenseState__c & " #" & LicenseNumber`
- Drop the raw `LicenseClass`, `LicenseNumber`, `PRM_LicenseState__c` columns
- Move columns to match the 11-column normalized shape (Old Value will be blank)

---

## Query C — PersonEducation (per-degree VerifiedDate)

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name,
  PRM_CaseManager__r.Account.Name,
  PRM_CaseManager__r.PRM_Stage__c,
  PRM_Degree__r.Name,
  PRM_Institution__c,
  PRM_GraduationDate__c,
  PRM_Status__c,
  VerifiedDate,
  LastModifiedBy.Name,
  LastModifiedBy.Profile.Name
FROM PersonEducation
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY LastModifiedBy.Name, PRM_CaseManager__c, VerifiedDate DESC
```

**In Excel after export:**
- Add `Source` column = `PersonEducation`
- Build a `What Changed` column = `="Education: " & [Degree] & " / " & [Institution]`
- Use `PRM_Status__c` as the `New Value` column
- Drop the raw degree/institution columns

---

## Query D — BoardCertification (per-cert VerifiedDate, with field guard)

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name,
  PRM_CaseManager__r.Account.Name,
  PRM_CaseManager__r.PRM_Stage__c,
  PRM_Taxonomy__r.Name,
  PRM_Status__c,
  VerifiedDate,
  LastModifiedBy.Name,
  LastModifiedBy.Profile.Name
FROM BoardCertification
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY LastModifiedBy.Name, PRM_CaseManager__c, VerifiedDate DESC
```

**Important — run this anonymous Apex FIRST to confirm the field exists in your org:**
```apex
System.debug(Schema.SObjectType.BoardCertification.fields.getMap().keySet().contains('verifieddate'));
```
- If `true` → run the query above as-is.
- If `false` → BoardCertification doesn't have `VerifiedDate` in this org. Use `LastModifiedDate` as a proxy (replace `VerifiedDate` with `LastModifiedDate` in the SELECT and WHERE) and label the Source as `BoardCertification (LMD proxy)` in Excel.

**In Excel after export:**
- Add `Source` column = `BoardCertification`
- `What Changed` column = `="BoardCert: " & [Taxonomy.Name]`
- `New Value` = `PRM_Status__c`

---

## Query E — License (state license object, with object guard)

```sql
SELECT 
  PRM_CaseManager__c,
  PRM_CaseManager__r.Name,
  PRM_CaseManager__r.Account.Name,
  PRM_CaseManager__r.PRM_Stage__c,
  Name,
  Status,
  VerifiedDate,
  LastModifiedBy.Name,
  LastModifiedBy.Profile.Name
FROM License
WHERE PRM_CaseManager__c != null
  AND VerifiedDate >= 2026-01-01
  AND VerifiedDate <= 2026-05-31
ORDER BY LastModifiedBy.Name, PRM_CaseManager__c, VerifiedDate DESC
```

**Important — run this query first to confirm the SObject exists in your org:**
```sql
SELECT QualifiedApiName 
FROM EntityDefinition 
WHERE QualifiedApiName = 'License'
```
- If a row returns → run the query above.
- If empty / errors → this org only uses `BusinessLicense` (Query B); skip License entirely. Most IBX orgs are this configuration.

**In Excel after export (if applicable):**
- Add `Source` column = `License`
- `What Changed` column = `="License (state): " & Name`
- `New Value` = `Status`

---

## Excel concat recipe (5 min, after running all queries)

1. Run Query A → save as `1_FieldHistory.csv`
2. Run Query B → save as `2_BusinessLicense.csv`
3. Run Query C → save as `3_PersonEducation.csv`
4. Run Query D → save as `4_BoardCertification.csv` (or skip)
5. Run Query E → save as `5_License.csv` (or skip)
6. Open `1_FieldHistory.csv` in Excel → add `Source` column, fill all with `FieldHistory`
7. For each other CSV: open in Excel, normalize columns to the 11-column shape, paste below the prior data
8. Save the master file as `CaseManager_AllSources_Audit_2026-01-01_to_2026-05-31.xlsx`
9. Sort by `Event Date DESC` → ready to ship to business
10. (Optional) Build a PivotTable: Rows = `By User`, Columns = `Source`, Values = Count → exact view business asked for

**Power Query alternative:** If you have Microsoft 365, use Data → Get Data → From Folder → point at the folder containing the 5 CSVs → Append Queries As New. One click stacks them all, refreshable later when you re-run the SOQL.

---

## Edge cases and caveats

| Caveat | Why | Mitigation |
|---|---|---|
| Credential queries filter on `VerifiedDate` between Jan-May. Records with NULL `VerifiedDate` (never verified) are excluded. | NULL doesn't satisfy `>= 2026-01-01`. | If business wants ALL credentials regardless of verification status, change WHERE to `LastModifiedDate >= 2026-01-01 AND VerifiedDate = null OR (VerifiedDate >= 2026-01-01 AND VerifiedDate <= 2026-05-31)`. |
| Time semantics differ — `IndividualApplicationHistory.CreatedDate` is the moment of edit; credential `VerifiedDate` is a Date (no time). | History is Datetime; VerifiedDate is Date. | Normalize in Excel — convert VerifiedDate to Datetime (`= [@VerifiedDate] + TIMEVALUE("00:00:00")`) before sorting. |
| `PRM_CaseManager__c` may be NULL on some credential records (legacy data, pre-Case Manager linkage). | Older credential records weren't tagged with the Case Manager. | Already filtered out via `WHERE PRM_CaseManager__c != null`. |
| `Status='Pending'` and `Status='Error'` rows ARE included if `VerifiedDate` is set. | Per UserStory decision 2026-06-01: include all statuses. | Filter visually in Excel via the New Value column or pivot. |
| Workbench Bulk CSV can timeout if a single query exceeds ~50K rows. | Default Workbench limit. | The Jan-May window typically yields well under that. If exceeded, narrow date range and run in two halves. |

