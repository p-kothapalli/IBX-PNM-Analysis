# Case Manager Field History — SOQL Archive

**Date:** 2026-05-29
**Context:** Business asked for a Case Manager history report covering Application Review + PSV validation field changes (who edited what, when) for Jan 1 – May 31 2026. Field History Tracking is enabled on `IndividualApplication` (UI label "Case Manager") with ~30 PRM_*Verification__c / PRM_*PSV__c / PRM_PSVOutcome__c fields tracked. Standard `IndividualApplicationHistory` cannot be related as a child in Custom Report Types (Salesforce platform limitation), so SOQL → CSV is the delivery path.

---

## Query 1 — Sanity check: total history-row count in window

**Object:** `IndividualApplicationHistory`
**Use case:** Confirms history data exists for the requested date range before doing the full export. Run this first.

```sql
SELECT COUNT()
FROM IndividualApplicationHistory
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <= 2026-05-31T23:59:59Z
```

**Sample result:** `10,376 records` (Jan 1 – May 31 2026, all tracked fields).
**Notes:** If this returns 0, tracking may not have been enabled for the window — no further queries will help.

---

## Query 2 — Field coverage breakdown (which fields actually have history)

**Object:** `IndividualApplicationHistory`
**Use case:** Shows the per-field row count so we know which of the 30 validation fields actually generated history rows in the window. Catches "tracking is on but no one edited it" cases and surfaces high-volume noise fields (e.g., `PRM_Stage__c`).

```sql
SELECT Field, COUNT(Id) recordCount
FROM IndividualApplicationHistory
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <= 2026-05-31T23:59:59Z
GROUP BY Field
ORDER BY COUNT(Id) DESC
```

**Sample result:** 27 of the 30 target fields had rows. Missing (zero rows): `PRM_NPDBVerified__c`, `PRM_NPDBErrorMessage__c`, `PRM_HospitalAffiliations__c`. High-volume noise fields excluded from scope: `PRM_Stage__c` (2,179), `created` (1,800), `Status` (1,463), `PRM_Decision_Date__c` (1,040).
**Notes:** "Field" column stores the API name; aggregate label `created` denotes record-creation events (no API name).

---

## Query 3 — Full export filtered to the 30 validation fields

**Object:** `IndividualApplicationHistory`
**Use case:** Primary CSV export for the business. Filtered to the App Review + PSV validation fields only; excludes high-noise fields like `PRM_Stage__c`. Run via Workbench → Queries → SOQL Query → "Bulk CSV" for full export (no row cap).

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
    'PRM_CMSPreclusionReview__c','PRM_PSVOutcome__c'
  )
ORDER BY CreatedBy.Name, IndividualApplicationId, CreatedDate DESC
```

**Sample result:** 3,423 rows exported (May 10–29 2026 only — see Query 4 for the date-range investigation).
**Notes:**
- **`ParentId` does NOT exist on `IndividualApplicationHistory`.** Standard-object history tables use a typed FK named after the parent (`IndividualApplicationId`). Custom-object history tables (`<Object>__History`) use `ParentId`. Common gotcha.
- Column meanings:
  - `IndividualApplicationId` → the Case Manager record's Id
  - `IndividualApplication.Name` → human-readable Case Manager # (e.g., `IA-0000151779`)
  - `IndividualApplication.Account.Name` → provider full name
  - `CreatedBy.Name` → the user who edited the field (the "case manager / specialist" in business terms)
- `Field` column is the API name; map to friendly labels downstream (e.g., in the Excel pivot).

---

## Query 4 — Month distribution (diagnoses date-range gaps in exports)

**Object:** `IndividualApplicationHistory`
**Use case:** When an export shows fewer dates than expected, this confirms whether earlier-month data truly exists or whether tracking was enabled mid-window. Critical pre-ship check.

```sql
SELECT CALENDAR_MONTH(CreatedDate) Mth, COUNT(Id) Cnt
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
GROUP BY CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_MONTH(CreatedDate)
```

**Sample result:** *(pending — to be run)*. If only month 5 returns rows → tracking was enabled mid-May; earlier history doesn't exist. If months 1–5 all show rows → original export was tool-row-capped; re-run via Workbench Bulk CSV.
**Notes:**
- `CALENDAR_MONTH()` is a SOQL date function returning 1–12.
- Drop `PRM_NPDBVerified__c`, `PRM_NPDBErrorMessage__c`, `PRM_HospitalAffiliations__c` from the IN clause — they had zero rows in Query 2.

---

## Field reference — UI label ↔ API name

| UI Label (per screenshot) | API Name |
|---|---|
| **Application Review** | |
| Specialty Verification | `PRM_SpecialtyVerification__c` |
| Education Verification | `PRM_EducationVerification__c` |
| License Verification | `PRM_LicenseVerification__c` |
| Work History Verification | `PRM_WorkHistoryVerification__c` |
| DEA Verification | `PRM_DEAVerification__c` |
| Malpractice Coverage Verification | `PRM_MalpracticeCoverageVerification__c` |
| CDS Verification | `PRM_CDSVerification__c` |
| Attestation Verification | `PRM_AttestationVerification__c` |
| NPDB Verified | `PRM_NPDBVerified__c` *(no history rows)* |
| NPDB Verified On | `PRM_NPDBVerifiedOn__c` |
| NPDB Error Message | `PRM_NPDBErrorMessage__c` *(no history rows)* |
| **PSV** | |
| Contract Status | `PRM_ContractStatus__c` |
| CAQH Attestation | `PRM_CAQHAttestation__c` |
| Service Area PSV | `PRM_ServiceAreaPSV__c` |
| License PSV | `PRM_LicensePSV__c` |
| Specialty PSV | `PRM_SpecialtyPSV__c` |
| Admitting Privileges Review | `PRM_AdmittingPrivilegesReview__c` |
| Insurance PSV | `PRM_InsurancePSV__c` |
| Hospital Affiliations | `PRM_HospitalAffiliations__c` *(no history rows)* |
| Education PSV | `PRM_EducationPSV__c` |
| Work History PSV | `PRM_WorkHistoryPSV__c` |
| CDS PSV | `PRM_CDSPSV__c` |
| DEA PSV | `PRM_DEAPSV__c` |
| Board Certification PSV | `PRM_BoardCertificationPSV__c` |
| Disclosure Review | `PRM_DisclosureReview__c` |
| Medicare Opt-Out Review | `PRM_MedicareOptOutReview__c` |
| FSMB PSV | `PRM_FSMBPSV__c` |
| SAM Review | `PRM_SAMReview__c` |
| CMS Preclusion Review | `PRM_CMSPreclusionReview__c` |
| PSV Outcome | `PRM_PSVOutcome__c` |

## Bonus tracked fields surfaced by Query 2 (not in original ask)

These have history rows and may be relevant for future audit reports:

| API Name | Suggested Label | Rows in Jan–May 2026 |
|---|---|---:|
| `PRM_CredentialingQC__c` | Credentialing QC | 236 |
| `PRM_QMReviewOutcome__c` | QM Review Outcome | 62 |
| `PRM_HACACDecisionDate__c` | HACAC Decision Date | 55 |
| `PRM_DenialReason__c` | Denial Reason | 47 |
| `PRM_PendedReason__c` | Pended Reason | 20 |
| `PRM_LicensureReview__c` | Licensure Review | 6 |
| `PRM_AccreditationReview__c` | Accreditation Review | 6 |
| `PRM_NPDBVerification__c` | NPDB Verification (process) | 6 |
