# Recred PSV — "Effective Dates must be within Account's Effective Dates"

**Date:** 2026-08-25
**Context:** Recredentialing PSV (and Recred PSV QC) submit shows OmniScript step **Update Failed** with `Error : Effective Dates must be within Account's Effective Dates`. The banner is `%result:error%` from `PRM_ReviewPSVCaseRecordsUpdateParent` (PSV) or the same DML emitters if a child record is re-saved. Replace `:caseManagerId` / `:accountId` with the failing case.

---

## Query 1 — Case Manager → practitioner Account date window

**Object:** `IndividualApplication`, `Account`
**Use case:** Confirm the Recred Case Manager's practitioner Account `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` that child records must sit inside.

```sql
SELECT Id, Name, Status, PRM_Stage__c, RecordType.DeveloperName,
       AccountId, Account.Name, Account.IsActive, Account.PRM_Pending__c,
       Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c,
       Account.PRM_NPI__c, Account.PRM_CredentialingStatus__c
FROM IndividualApplication
WHERE Id = :caseManagerId
```

**Sample result / row count (if known):** 1 row.
**Notes / gotchas:** Recred Case Managers use record type `PRM_Recredentialing`. The VRs only fire when `Account.IsActive = true` and `Account.PRM_Pending__c = false`.

---

## Query 2 — HealthcareProviderTaxonomy rows outside the Account window

**Object:** `HealthcareProviderTaxonomy`
**Use case:** Find taxonomies Recred PSV will re-save via `PRMDRCreateTaxonomy` (DRPTaxonomy) whose existing `EffectiveFrom` is earlier than the Account window. This is the most common Recred PSV emitter (`0bP` prefix).

```sql
SELECT Id, Name, IsActive, IsPrimaryTaxonomy, EffectiveFrom, EffectiveTo,
       AccountId, Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c,
       PractitionerId, Practitioner.Account.PRM_EffectiveFrom__c,
       Practitioner.Account.PRM_EffectiveTo__c, PRM_CaseManager__c
FROM HealthcareProviderTaxonomy
WHERE (AccountId = :accountId OR Practitioner.AccountId = :accountId)
  AND IsActive = true
  AND (
    EffectiveFrom < Account.PRM_EffectiveFrom__c
    OR EffectiveFrom < Practitioner.Account.PRM_EffectiveFrom__c
    OR (Account.PRM_EffectiveTo__c != null AND EffectiveTo > Account.PRM_EffectiveTo__c)
    OR (Practitioner.Account.PRM_EffectiveTo__c != null
        AND EffectiveTo > Practitioner.Account.PRM_EffectiveTo__c)
  )
```

**Sample result / row count (if known):** typically 1+ historical NPPES/CAQH specialties on Recred.
**Notes / gotchas:** `PRMDRCreateTaxonomy` does **not** map `EffectiveFrom` — it updates Id / IsPrimary / Case Manager / Provider Type. The VR has **no `ISCHANGED()`**, so a no-op date rewrite still fails. Cross-link: `2026-07-09_PARForm_EffectiveDatesWithinAccount.md`.

---

## Query 3 — HealthcareProvider rows outside the Account window

**Object:** `HealthcareProvider`
**Use case:** Same exact error string; prefix `0cm`. Less common on Recred PSV submit than taxonomy, but the VR is active.

```sql
SELECT Id, Name, EffectiveFrom, EffectiveTo, AccountId, PractitionerId,
       Account.IsActive, Account.PRM_Pending__c,
       Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c,
       Practitioner.Account.PRM_EffectiveFrom__c,
       Practitioner.Account.PRM_EffectiveTo__c
FROM HealthcareProvider
WHERE (AccountId = :accountId OR Practitioner.AccountId = :accountId)
  AND (
    EffectiveFrom < Account.PRM_EffectiveFrom__c
    OR EffectiveFrom < Practitioner.Account.PRM_EffectiveFrom__c
    OR (Account.PRM_EffectiveTo__c != null AND EffectiveTo > Account.PRM_EffectiveTo__c)
    OR (Practitioner.Account.PRM_EffectiveTo__c != null
        AND EffectiveTo > Practitioner.Account.PRM_EffectiveTo__c)
  )
```

**Sample result / row count (if known):** 0–few.
**Notes / gotchas:** VR `HealthcareProvider.PRM_EffectiveDateValidation` is **active**. `HealthcareProviderNpi.PRM_EffectiveDateValidation` is **inactive**.

---

## Query 4 — Identifier rows outside the Account window

**Object:** `Identifier`
**Use case:** Recred PSV updates CAQH attestation via `PRMLoadPSVIdentifierRecords` (`DRLoadIdentifierRecords`). Prefix `0hk`. Emitter is Apex `PRM_IdentifierTriggerHandler.resUsrsToUpdateInvalidEffDates`, not a VR.

```sql
SELECT Id, Name, IdType, PRM_Active__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       ParentRecordId, ParentRecord.PRM_EffectiveFrom__c, ParentRecord.PRM_EffectiveTo__c,
       ParentRecord.IsActive
FROM Identifier
WHERE ParentRecordId = :accountId
  AND PRM_Active__c = true
  AND (
    PRM_EffectiveFrom__c < ParentRecord.PRM_EffectiveFrom__c
    OR (ParentRecord.PRM_EffectiveTo__c != null
        AND PRM_EffectiveTo__c > ParentRecord.PRM_EffectiveTo__c)
  )
```

**Sample result / row count (if known):** often the CAQH / NPI identifier on existing-NPI Recred.
**Notes / gotchas:** Trigger runs on **every** insert/update of an active Identifier whose parent Account is active — it does not check whether dates changed. `PRMLoadPSVIdentifierRecords` maps attestation fields, not effective dates, so a date-unchanged update still fails.

---

## Query 5 — Recent exception logs for this exact message

**Object:** `PRM_ExceptionLog__c`
**Use case:** If the IP logged the DML, the stack / process name names the emitter. Recred PSV DML failures often stay in the OmniScript `%result:error%` and never hit this object.

```sql
SELECT Id, CreatedDate, PRM_ProcessName__c, PRM_ExceptionType__c,
       PRM_ErrorMessage__c, PRM_LineNumber__c
FROM PRM_ExceptionLog__c
WHERE CreatedDate = LAST_N_DAYS:14
  AND PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'
ORDER BY CreatedDate DESC
```

**Sample result / row count (if known):** may be 0 for Recred PSV UI failures (same pattern as PAR form).
**Notes / gotchas:** Decode any Id in the message: `0bP` = HealthcareProviderTaxonomy VR, `0cm` = HealthcareProvider VR, `0hk` = Identifier Apex trigger.
