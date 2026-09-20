# PAR Form — "Effective Dates must be within Account's Effective Dates" (HMHMG examples)

**Date:** 2026-07-15
**Context:** 3 practitioners reported hitting "Effective Dates must be within Account's Effective Dates" on PAR submission when joining HMHMG Specialty Care (NPI 1215989249 / TIN 223376459) and Bayhealth (NPI 1023006434 / TIN 510064318). Root cause is `PRM_IdentifierTriggerHandler` (lines 120-133): an `Identifier` whose `PRM_EffectiveFrom__c` is earlier than its ACTIVE parent Account's `PRM_EffectiveFrom__c` (or `PRM_EffectiveTo__c` later) is rejected. Cross-link: `2026-07-09_PARForm_EffectiveDatesWithinAccount.md`.

**Reported examples:**
| Practitioner | Prac NPI | Group | Group NPI | TIN |
|---|---|---|---|---|
| Lucy Tan | 1083240014 | HMHMG Specialty Care | 1215989249 | 223376459 |
| Jonathan Philip Knowles | 1699437897 | HMHMG Specialty Care | 1215989249 | 223376459 |
| RYAN SMOLIN | 1184327462 | BAYHEALTH URGENT CARE, TOTAL CARE | 1023006434 | 510064318 |

---

## Query 1 — Resolve NPIs to provider/account + effective windows

**Object:** `HealthcareProviderNpi`
**Use case:** Map each practitioner/group NPI to its Account and compare the NPI record's EffectiveFrom to the Account's PRM_EffectiveFrom__c.

```sql
SELECT Id, Npi, NpiType, AccountId, Account.Name, Account.IsActive,
       Account.PRM_Pending__c, Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c,
       EffectiveFrom, EffectiveTo
FROM HealthcareProviderNpi
WHERE Npi IN ('1083240014','1699437897','1184327462','1215989249','1023006434')
ORDER BY Npi
```

**Sample result:** Only 3 of 5 NPIs exist in QA. Group NPI 1023006434 → Bayhealth Medical Center (acct from 2025-01-01, NPI from 2004-11-25); NPI 1215989249 → "GRACE CHANG" `PRM_Practitioner` (acct from 2021-06-21, NPI from 2015-08-01); 1699437897 → Jonathan Philip Knowles (acct from 2023-12-04, Pending=true). Practitioner NPIs 1083240014 (Lucy) and 1184327462 (Ryan) are NOT present → their PAR submission failed before records were created.

---

## Query 2 — All Identifiers under a parent Account vs the account window

**Object:** `Identifier`
**Use case:** For a given account, list identifiers and eyeball any whose `PRM_EffectiveFrom__c` < account's `PRM_EffectiveFrom__c` (the violation the trigger rejects).

```sql
SELECT Id, PRM_Type__c, IdValue, PRM_Active__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       ParentRecordId,
       TYPEOF ParentRecord
         WHEN Account THEN Name, IsActive, PRM_EffectiveFrom__c, PRM_EffectiveTo__c
       END
FROM Identifier
WHERE ParentRecordId = '001UW00000eiqynYAA'
ORDER BY PRM_EffectiveFrom__c
```

**Notes / gotchas:** The `TYPEOF ... END` parent fields don't always render in `sf data query` table output — pull the Account window with a separate query if needed. Trigger only evaluates identifiers with `PRM_Active__c = true` whose parent Account `IsActive = true`.

---

## Query 3 — Who carries the HMHMG TIN (shared TIN across locations)

**Object:** `Identifier`
**Use case:** Show TIN 223376459 is shared across many HMHMG accounts (different locations), which is why "the majority" of failing practitioners share this NPI/TIN.

```sql
SELECT Id, PRM_Type__c, IdValue, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, ParentRecordId
FROM Identifier
WHERE IdValue = '223376459'
ORDER BY PRM_EffectiveFrom__c
```

**Sample result:** ~40+ EIN rows across distinct HMHMG accounts, EffectiveFrom ranging 1995-05-01 → 2026-04-04.

---

## Query 4 — Find violating Identifiers by explicit account window (bulk sweep)

**Object:** `Identifier` (compare client-side)
**Use case:** Pull active identifiers for a set of accounts + those accounts' windows, then flag `ident.from < acct.from` locally. SOQL can't compare parent vs child fields in WHERE, so filter by account list and compare in a script.

```sql
SELECT Id, PRM_Type__c, IdValue, PRM_Active__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, ParentRecordId
FROM Identifier
WHERE PRM_Active__c = true AND ParentRecordId IN ('<accountId1>','<accountId2>')
```

**Notes / gotchas:** In Apex, `null < someDate` is `false`, so a NULL identifier EffectiveFrom does NOT trip the trigger — only a POPULATED date earlier than the account's does.

---

## Query 5 — Runtime evidence: real logged failures (source of truth)

**Object:** `PRM_ExceptionLog__c`
**Use case:** Find the ACTUAL logged occurrences of the effective-date family of errors and their originating class (via stack trace). This is what proves origin, vs. hypothesizing from metadata.

```sql
SELECT Id, CreatedDate, PRM_RecordId__c, PRM_RecordObjectName__c, PRM_ExceptionType__c,
       PRM_SourceSystem__c, PRM_ErrorMessage__c, PRM_StackTrace__c
FROM PRM_ExceptionLog__c
WHERE PRM_ErrorMessage__c LIKE '%Effective Dates must be within%'
  AND CreatedDate = LAST_N_DAYS:180
ORDER BY CreatedDate DESC
LIMIT 25
```

**KEY FINDINGS (QA, last 180 days):**
- The error is a FAMILY, not one rule: "...within **Account's** Effective Dates" (Identifier), "...within **Practice Location** Effective Dates", "...within **Location Address** Effective Dates", "...within **Practice Location & Practitioner's**", "...within **Practice Location and Healthcare Provider NPI's**".
- Every occurrence is a `System.DmlException` **"Update failed"** with `PRM_SourceSystem__c = Salesforce`.
- **Originating classes (from stack traces) are TERMINATION / cross-reference BATCHES — NOT the PAR form:**
  - "Account's Effective Dates" (Identifier) → `PRM_PracticeLocationTerminationBatch.execute` line 350.
  - "Practice Location Effective Dates" → `PRM_TerminatePracticeLocationNRelations.execute` → `PRM_CrossRefBatchHelper.terminateFacilityAndRelations` → `termContactMethod` line 529.

**Concrete failing Identifier records (pre-existing out-of-window data):**
| Identifier | Type/Value | Ident EffFrom | Parent Account | Acct EffFrom | Gap |
|---|---|---|---|---|---|
| `0hkUW00000058AcYAI` | BSPA 004186045 | 2019-02-13 | Andrea T Difiore (Practitioner, active) | 2022-02-17 | ident ~3 yrs before acct |
| `0hkUW0000005zTUYAY` | BSPA 003134433 | 2015-01-29 | Pedi Care Corp (Vendor) | 2015-02-01 | ident 3 days before acct |

**Conclusion:** the logged errors are termination batches bulk-updating **pre-existing** identifiers whose real (historical) effective date predates when the account was set up in PRM. The `beforeUpdate` trigger re-validates and blocks the chunk. This is NOT the PAR form stamping an NPI date at submission.

---

## Query 6 — LIVE RUNTIME CAPTURE: new-practitioner PAR submit does NOT throw (definitive)

**Context:** On 2026-07-16 16:45 UTC a controlled PAR submission was run under an active trace flag — **Lucy Tan (NPI 1083240014, `IsExistingNPI: false`) joining HMHMG Specialty Care (group acct `001UW00000ejvzDYAQ`, NPI 1215989249, TIN 223376459)**. Case Manager **IA-156760** was created; submission **succeeded**.

**Debug-log + record evidence (all confirm NO error fired):**
- Exception logs in the submission window (`CreatedDate >= 2026-07-16T16:40:00Z`) → **0 rows**.
- 15 MB record-creation Queueable log → **no `addError`, no `FIELD_CUSTOM_VALIDATION`, no `FATAL_ERROR`**; only benign SOQL referencing `PRM_EffectiveFrom__c`.
- Two `FutureHandler` logs → `PRM_IdentifierTriggerHandler` **executed** (constant `ERR_MSG_INVALIDIDENDATES` loaded into scope at lines 66/71) but **did not throw**.
- Created Account `001VB00000qyOHjYAM` (Lucy Tan): `PRM_EffectiveFrom__c = null`, `PRM_EffectiveTo__c = null`, `IsActive = false`, `PRM_Pending__c = true`.
- Created Identifier `0hkVB000001qCxNYAU` (CAQH 16174844, parent = Lucy's acct): `PRM_EffectiveFrom__c = null`, `PRM_EffectiveTo__c = null`.

**Verification query used:**
```sql
SELECT Id, PRM_Type__c, IdValue, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, ParentRecordId, CreatedDate
FROM Identifier
WHERE CreatedDate >= 2026-07-16T16:40:00Z
ORDER BY CreatedDate DESC
```

**Definitive conclusion:** For a **brand-new** practitioner, the PAR flow creates identifiers with **null** effective dates, so `null < acct.from` is `false` and the `PRM_IdentifierTriggerHandler` guard passes. The "Effective Dates must be within Account's Effective Dates" error therefore **cannot originate from the new-practitioner PAR submit path**. It only fires on (a) the **existing-NPI / reinstate-termination** DataRaptors (`PRMDRPHcProviderNpiIdentifier` / `PRMDRPHCProvProvNPIIdentifier`) which copy the NPI's own (backdated) effective date onto the identifier, or (b) later backend activation/termination/CAQH batches that stamp a backdated date onto an identifier. Business users blocked at submit time are on an **existing NPI** (`IsExistingNPI: true`), not a new one.
