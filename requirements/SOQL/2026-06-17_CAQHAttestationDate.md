# CAQH Attestation Date (Identifier record tagged to Practitioner)

**Date:** 2026-06-17
**Context:** Need the CAQH attestation date alongside an `IndividualApplicationHistory` verification-field export. The attestation date is not on the application/history — it lives on the practitioner's child `Identifier` record where `PRM_Type__c = 'CAQH'` (`PRM_AttestationDate__c`). History objects don't allow child subqueries and `Identifier` is a 1-to-many child of the Account, so it must be pulled in a second query and joined on `AccountId`.

---

## Query 1 — IndividualApplicationHistory export (add AccountId join key)

**Object:** `IndividualApplicationHistory`
**Use case:** Verification/PSV field-change history per case. Adds `IndividualApplication.AccountId` so results can be joined to the CAQH Identifier query.

```sql
SELECT
  IndividualApplicationId,
  IndividualApplication.Name,
  IndividualApplication.AccountId,
  IndividualApplication.Account.Name,
  IndividualApplication.PRM_Stage__c,
  Field, OldValue, NewValue,
  CreatedDate, CreatedBy.Name,
  IndividualApplication.RecordType.Name,
  IndividualApplication.PRM_Decision_Date__c
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

**Notes / gotchas:** History objects (`*History`) cannot contain child subqueries and cannot dot-traverse to a parent's child collection — hence the separate Identifier query below.

---

## Query 2 — CAQH attestation date from the practitioner's Identifier

**Object:** `Identifier`
**Use case:** Returns the active CAQH identifier and its attestation date for each practitioner. Join `ParentRecordId` (the practitioner Account) to `IndividualApplication.AccountId` from Query 1.

```sql
SELECT
  ParentRecordId,
  ParentRecord.Name,
  Name,
  PRM_AttestationDate__c,
  PRM_AttestationID__c,
  PRM_Active__c,
  EffectiveDate, EndDate
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND PRM_Active__c = true
  AND ParentRecord.Type = 'Account'
ORDER BY ParentRecordId, PRM_AttestationDate__c DESC
```

Optionally scope to just the practitioners from Query 1:

```sql
... AND ParentRecordId IN ('001UW00000eiavfYAA','001UW00000eiBO8YAM', /* ...AccountIds... */ )
```

**Join key:** `Identifier.ParentRecordId` = `IndividualApplication.AccountId`.

### Single combined output (one run)

A single flat SOQL query that returns both the history rows AND the CAQH date is **not possible**: the base is a History object (no subqueries) and the CAQH date is a *grandchild* of IndividualApplication (IA → Account → Identifier), which SOQL can't subquery, and it isn't exposed as a parent field on Account/IndividualApplication (those only have the `PRM_CAQHAttestation__c` picklist). To get one merged CSV in one run, use the Apex join script:

`scripts/apex/export_IAHistory_with_CAQHAttestation.apex` — runs Query 1, collects AccountIds, runs Query 2, and emits a single CSV (history columns + `CAQH_Identifier` + `CAQH_AttestationDate`) to the debug log and a downloadable `ContentVersion`. **Sandbox/small-volume only** — synchronous anonymous Apex (10s CPU / 6MB heap), so it throws "Apex CPU time limit exceeded" on PROD volume.

### PROD-safe path (no Apex, no 50k cap)

`scripts/export_IAHistory_with_CAQH.sh <org> [fromISO] [toISO] [outDir]` — exports both queries via **Bulk API 2.0** (`sf data export bulk`, no Apex governor and no 50,000-record REST limit) and joins them locally with `scripts/join_iahistory_caqh.py` (streaming join on `AccountId`, constant memory, latest attestation per practitioner wins, `1900-01-01` blanked). Produces one merged CSV. Example:

```bash
./scripts/export_IAHistory_with_CAQH.sh prod 2026-01-01T00:00:00Z 2026-05-31T23:59:59Z ./out
```

Verified on sandbox: handled 103,220 CAQH identifiers + 3,461 history rows with no limit errors.

**Sample result:**

| ParentRecordId | ParentRecord.Name | PRM_AttestationDate__c | Name |
|---|---|---|---|
| 001UW00000eiBO8YAM | Kathleen Boreale | 2026-04-13 | ID-917059 |
| 001UW00000eiavfYAA | Dennis Morgan Burton | 1900-01-01 | ID-917050 |

**Notes / gotchas:**
- A practitioner may have multiple CAQH `Identifier` rows; `PRM_Active__c = true` (or `MAX(PRM_AttestationDate__c)`) selects the current one.
- `1900-01-01` is a "never attested / migrated" sentinel — treat as null, not a real attestation date.
- `Identifier.ParentRecordId` is polymorphic; CAQH-for-practitioner rows point to `Account`. (`Identifier` also has `PRM_CaseManager__c` → `IndividualApplication`, but the practitioner link is `ParentRecordId`.)
- Do **not** confuse `Identifier.PRM_AttestationDate__c` (this CAQH date) with `IndividualApplication.PRM_CAQHAttestation__c` (a picklist status whose change *event* date = `MAX(IndividualApplicationHistory.CreatedDate)` per the Integrity Reporting mapping).
```
