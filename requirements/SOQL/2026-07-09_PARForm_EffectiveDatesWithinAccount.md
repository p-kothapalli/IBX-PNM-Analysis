# PAR Form — "Effective Dates must be within Account's Effective Dates"

**Date:** 2026-07-09
**Context:** After PAR (Practitioner Participation) form submission, business users hit `Effective Dates must be within Account's Effective Dates`. The rule/trigger compares the child record's `EffectiveFrom`/`EffectiveTo` against the parent practitioner **Account's** `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` window (only when the Account `IsActive = true` and `PRM_Pending__c = false`). These queries help pinpoint the offending Account + child records.

> **✅ ROOT CAUSE CONFIRMED IN QA (2026-07-09):** The failing records are **`Identifier`** rows (key prefix `0hk`), and the error is thrown by the **Apex handler `PRM_IdentifierTriggerHandler.resUsrsToUpdateInvalidEffDates`** (runs on `beforeInsert` AND `beforeUpdate`) — **NOT** the VRs and **NOT** the blank-date case. The failing Identifiers have **populated, historical** `PRM_EffectiveFrom__c` that is **earlier than the parent Account's `PRM_EffectiveFrom__c`**:
> | Identifier | Ident.EffectiveFrom | Account | Acct Active/Pending | Acct.EffectiveFrom | Acct.EffectiveTo |
> |---|---|---|---|---|---|
> | 0hkUW00000058AcYAI | 2019-02-13 | Andrea T Difiore (PRM_Practitioner) | true/false | 2022-02-17 | — |
> | 0hkUW0000006KE4YAM | 2023-04-07 | Angela Hubert (PRM_Practitioner) | true/false | 2023-04-18 | — |
> | 0hkUW0000005zTUYAY | 2015-01-29 | Pedi Care Corp (PRM_Vendor) | (now termed) | 2015-02-01 | 2026-07-08 |
>
> **Trigger points seen in `PRM_ExceptionLog__c` (who re-touches the Identifier and re-fires the beforeUpdate validation):** `PRM_CheckCAQHAccessOnDueAccountsBatch` (most frequent), `PRM_CAQHValidationService`, `PRM_PractitionerActivationBatch` (recred/reinstate), `PRM_PracticeLocationTerminationBatch`, `PRM_AccountTerminationBatch`, `Practitioner NPI Update` (Flow), and the interactive PAR OmniScript when it updates an existing Identifier. **Use case = any insert/update of an Identifier whose NPI/CAQH effective-from predates the Account's `PRM_EffectiveFrom__c` (or whose EffectiveTo exceeds the Account's `PRM_EffectiveTo__c`).**

### Remediation script

SOQL can't fix this (no field-to-field `WHERE`, no `UPDATE`). Use **`scripts/apex/fix_identifier_effdates.apex`** — it queries the Identifiers + parent Accounts, and **clamps** the identifier dates into the account window (`EffectiveFrom` up to `Account.PRM_EffectiveFrom__c`, `EffectiveTo` down to `Account.PRM_EffectiveTo__c`). `COMMIT_CHANGES=false` = dry run. `SCOPE_IDS` limits to specific Ids; empty it to sweep all active-account identifiers.

**QA dry-run (2026-07-09):** scanned 4 known failing Ids → 3 fixable (Andrea Difiore 2019-02-13→2022-02-17; 0hkUW000000678kYAA 2020-07-30→2020-09-08; Angela Hubert 2023-04-07→2023-04-18). The 4th (Pedi Care Corp, `0hkUW0000005zTUYAY`) is skipped — its account is now inactive so the trigger no longer validates it.

**Full-org blast radius (QA, 2026-07-09 — bulk export + local join in `scripts/tmp/analyze_blast_radius.py`):** **4,668 violating identifiers** across **2,905 accounts** — **100% are `EffectiveFrom < Account.PRM_EffectiveFrom__c`; 0 `EffectiveTo` violations.** By type: PRM_Vendor 4,014 / PRM_Practitioner 654. Gap distribution: ≤30d 810 · 31–365d 1,088 · 1–5y 1,564 · >5y 1,206 (i.e. 59% are off by >1 year, so clamping rewrites genuinely historical dates — prefer account-side or logic fix for those; clamp is safest for the 810 ≤30-day near-misses).

**Caveats:** (1) Clamping identifier dates forward **discards the true historical NPI/CAQH start** — confirm with business vs. the alternative of moving the *Account's* `PRM_EffectiveFrom__c` back. (2) Updating an Identifier fires `afterUpdate` → `futureDatedProcessing` (creates `PRM_FutureDatedProcessing__c` for Practitioner/Vendor RTs when effective dates change); run under a user with `PRM_TriggerBypassPermission` to suppress if undesired. (3) >45k active identifiers → convert to Batch Apex.

### Confirmed working queries (used in QA)

```sql
-- 1. Find the actual captured failures + which process/record
SELECT Id, PRM_ProcessName__c, PRM_ExceptionType__c, PRM_ErrorMessage__c, CreatedDate
FROM PRM_ExceptionLog__c
WHERE PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'
ORDER BY CreatedDate DESC LIMIT 50
-- (constrain with AND CreatedDate = LAST_N_DAYS:30 — LIKE on the long-text field is non-selective and can time out)

-- 2. The failing Identifier's own dates + its parent (ParentRecordId = Account)
SELECT Id, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_Active__c, ParentRecordId
FROM Identifier WHERE Id IN ('0hkUW00000058AcYAI', ...)

-- 3. The parent Account window
SELECT Id, Name, RecordType.DeveloperName, IsActive, PRM_Pending__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c
FROM Account WHERE Id IN ('001UW00000ei92rYAA', ...)
```

---

> **CONFIRMED 2026-07-09:** The PAR create-DataRaptors (`PRMDRCreateProviderIdentifierNPI`, `PRMDRCreateTaxonomy`, `PRMDrCreateIdentifierRecords`, `PRMDRCreateIdentifierExistingNPI`) do **NOT** map `EffectiveFrom`/`EffectiveTo` onto `HealthcareProvider` / `HealthcareProviderTaxonomy` / `Identifier` — those dates are created **blank**. So the key diagnostic is: on a failing record, **is `EffectiveFrom` actually blank?** If blank → the VR is firing on an un-guarded blank date (it lacks a `NOT(ISBLANK(EffectiveFrom))` guard). If populated → some other flow/trigger stamped an out-of-window date. The `Identifier` Apex path (`PRM_IdentifierTriggerHandler`) is **safe on blank** (Apex: `null < date` = `false`).

> **SOQL limitation:** SOQL cannot compare two fields to each other in a `WHERE` clause (e.g. `EffectiveFrom < Account.PRM_EffectiveFrom__c` is invalid). So the pattern is: (1) read the Account window, (2) read the child effective dates, (3) compare client-side / by eye.

---

## Query 1 — Account effective-date window (the boundary)

**Object:** `Account`
**Use case:** Get the acceptable effective-date window the children must fall inside, plus the Active/Pending gate that turns the rule on.

```sql
SELECT Id, Name, RecordType.DeveloperName,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       IsActive, PRM_Pending__c
FROM Account
WHERE Id = :practitionerAccountId
```

**Notes / gotchas:** The rule only fires when `IsActive = true AND PRM_Pending__c = false`. A blank `PRM_EffectiveTo__c` means "no upper bound" (only the lower `PRM_EffectiveFrom__c` bound is enforced).

---

## Query 2 — HealthcareProvider children outside the window (VR source, active)

**Object:** `HealthcareProvider`
**Use case:** List the provider participation rows for a practitioner so you can compare their dates to the Account window from Query 1.

```sql
SELECT Id, EffectiveFrom, EffectiveTo, IsActive,
       PractitionerId, Practitioner.AccountId,
       Practitioner.Account.PRM_EffectiveFrom__c,
       Practitioner.Account.PRM_EffectiveTo__c,
       Practitioner.Account.IsActive,
       Practitioner.Account.PRM_Pending__c,
       AccountId,
       Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c
FROM HealthcareProvider
WHERE Practitioner.AccountId = :practitionerAccountId
ORDER BY EffectiveFrom
```

**Offending row =** `EffectiveFrom < Account.PRM_EffectiveFrom__c` **OR** (`Account.PRM_EffectiveTo__c != null` AND `EffectiveTo > Account.PRM_EffectiveTo__c`).

---

## Query 3 — HealthcareProviderTaxonomy children outside the window (VR source, active)

**Object:** `HealthcareProviderTaxonomy`
**Use case:** Same comparison for taxonomy/specialty rows created by PAR.

```sql
SELECT Id, EffectiveFrom, EffectiveTo, IsActive,
       PractitionerId, Practitioner.AccountId,
       Practitioner.Account.PRM_EffectiveFrom__c,
       Practitioner.Account.PRM_EffectiveTo__c,
       AccountId,
       Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c
FROM HealthcareProviderTaxonomy
WHERE Practitioner.AccountId = :practitionerAccountId
ORDER BY EffectiveFrom
```

---

## Query 4 — Identifier children outside the window (Apex trigger source, active)

**Object:** `Identifier`
**Use case:** The Apex handler `PRM_IdentifierTriggerHandler.resUsrsToUpdateInvalidEffDates` throws the same message on `Identifier` insert/update, comparing `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c` to the parent Account (`ParentRecordId`).

```sql
SELECT Id, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_Active__c,
       ParentRecordId, PRM_Type__c, IdValue
FROM Identifier
WHERE ParentRecordId = :practitionerAccountId
  AND PRM_Active__c = true
ORDER BY PRM_EffectiveFrom__c
```

**Offending row =** `PRM_EffectiveFrom__c < Account.PRM_EffectiveFrom__c` **OR** `PRM_EffectiveTo__c > Account.PRM_EffectiveTo__c` (see Query 1 for the Account values).

---

## Query 5 — (Optional) HealthcareProviderNpi rows — VR is INACTIVE

**Object:** `HealthcareProviderNpi`
**Use case:** The `PRM_EffectiveDateValidation` VR on `HealthcareProviderNpi` is currently `active=false`, so it is **not** the source of the live error. Kept here for completeness / if it gets re-activated.

```sql
SELECT Id, EffectiveDate, EffectiveTo, IsActive, Account.PRM_EffectiveFrom__c, Account.PRM_EffectiveTo__c
FROM HealthcareProviderNpi
WHERE AccountId = :practitionerAccountId
```

**Notes:** Rule inactive as of 2026-07-09 — ignore unless re-enabled.

---

## Query 6 — Segment the failing cohort (which use case?)

**Object:** `Account` (practitioner) — run over the accounts touched by recent failing PAR submissions.
**Use case:** Only *some* PAR submissions fail. This query classifies the practitioner Accounts by the two firing conditions so you can see which use case dominates: (a) account Active & not Pending, (b) account effective window populated/restrictive. Feed the resulting Account Ids into Queries 2–4 to inspect the child dates.

```sql
SELECT Id, Name, RecordType.DeveloperName,
       IsActive, PRM_Pending__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       (PRM_EffectiveTo__c != null)  // terminated / future-termed?
FROM Account
WHERE Id IN :accountIdsFromFailingPARs
ORDER BY PRM_EffectiveTo__c NULLS LAST, PRM_EffectiveFrom__c DESC
```

**How to read it:**
- Rows with `IsActive = true AND PRM_Pending__c = false` → the *only* rows that can fire (Condition 1). Pending/new accounts here mean the failure is NOT this rule.
- Rows with `PRM_EffectiveTo__c` populated → **Use case 3** (terminated / future-termed practitioner).
- Rows with a recent/late `PRM_EffectiveFrom__c` → candidate for **Use case 2** (retro/back-dated) or **Use case 4** (blank child date vs populated account start) — confirm by checking the child `EffectiveFrom` via Queries 2–4.
- Rows with blank `PRM_EffectiveFrom__c` AND blank `PRM_EffectiveTo__c` → should NOT fail; if they show up as failing, the date is being stamped elsewhere (investigate that source).

**Notes / gotchas:** SOQL cannot compare `child.EffectiveFrom` to `Account.PRM_EffectiveFrom__c` in one query (no field-to-field comparison) — segment on the Account here, then compare child dates in Queries 2–4 client-side.

---

## Query 7 — Find the exception logs for THIS error (tested in QA, 2026-07-09)

**Object:** `PRM_ExceptionLog__c`
**Use case:** Locate every captured occurrence of `Effective Dates must be within Account's Effective Dates`, grouped by the process that triggered it, then drill into the individual rows.

### 7a — Count by process (which jobs fire it most)

```sql
SELECT PRM_ProcessName__c, COUNT(Id)
FROM PRM_ExceptionLog__c
WHERE CreatedDate = LAST_N_DAYS:365
  AND PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'
GROUP BY PRM_ProcessName__c
ORDER BY COUNT(Id) DESC
```

**Sample result (QA, trailing 365 days):**
| Process | Failures |
|---|---|
| `PRM_CheckCAQHAccessOnDueAccountsBatch` | 6 |
| `PRM_PractitionerActivationBatch` | 5 |
| `Practitioner NPI Update` (Flow) | 2 |
| `PRM_CAQHValidationService` | 1 |
| `PRM_PracticeLocationTerminationBatch` | 1 |
| `PRM_AccountTerminationBatch` | 1 |

### 7b — Detail rows (which record / class line failed)

```sql
SELECT CreatedDate, PRM_ProcessName__c, PRM_RecordObjectName__c,
       PRM_RecordId__c, PRM_LineNumber__c, PRM_ExceptionType__c,
       PRM_ErrorMessage__c
FROM PRM_ExceptionLog__c
WHERE CreatedDate = LAST_N_DAYS:365
  AND PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'
ORDER BY CreatedDate DESC
LIMIT 50
```

**Notes / gotchas:**
- **MUST bound with `CreatedDate = LAST_N_DAYS:n`** — `CreatedDate` is indexed; the bare `LIKE` on the long-text `PRM_ErrorMessage__c` is non-selective and **times out / hangs** on this high-volume log object without it.
- **Correct field names on `PRM_ExceptionLog__c`:** `PRM_RecordId__c` (the failing record), `PRM_RecordObjectName__c`, `PRM_LineNumber__c`, `PRM_StackTrace__c`, `PRM_ExceptionType__c`, `PRM_ProcessName__c`, `PRM_ErrorMessage__c`. There is **no** `PRM_ClassName__c` / `PRM_MethodName__c`.
- `sf data query --result-format csv` **drops aggregate (`COUNT`) values** (renders a blank column) — use `--result-format json` (or `human`) to read the counts.
- `PRM_RecordId__c` / `PRM_RecordObjectName__c` are often **blank** for these batch-caught failures (the batch swallows the `DmlException` without capturing the offending Identifier Id), so use `PRM_LineNumber__c` + `PRM_ProcessName__c` to correlate back to the code path.

---

## Query 8 — Is this from the PAR form? (caller attribution, confirmed 2026-07-09)

**Context:** `PRM_ExceptionLog__c.PRM_ProcessName__c` is set by **whoever caught the `DmlException`** (passed into `PRM_ExceptionLogger.logException(processName, …)`). The trigger handler `PRM_IdentifierTriggerHandler` only calls `addError` — it never logs — so the process name identifies the **DML initiator**, not the trigger.

**Finding (prod + QA):** every logged occurrence is a **backend batch/service/Flow** — `PRM_CheckCAQHAccessOnDueAccountsBatch`, `PRM_PractitionerActivationBatch`, `PRM_CAQHValidationService`, `PRM_PracticeLocationTerminationBatch`, `PRM_AccountTerminationBatch`, `Practitioner NPI Update` (Flow). **None are the PAR OmniScript.**

**Why the PAR form doesn't appear here:** the PAR form is the OmniScript `PRM_PractitionerParticipationForm` → IP `PRM_CreateParFormRecords` (active v29) → sub-IPs/DataRaptors. Its create-DataRaptors insert Identifiers with **blank** effective dates (Apex `null < date` = `false`, so insert is safe), and the interactive IP has **no ExceptionLog step** — any trigger error on a PAR *update* of an existing Identifier bubbles to the **browser/OmniScript UI**, not to `PRM_ExceptionLog__c`. So absence from this log ≠ PAR is unaffected; the batch rows and the PAR-UI error are the **same trigger, different callers**.

### 8a — Confirm PAR is/isn't among the callers

```sql
SELECT PRM_ProcessName__c, COUNT(Id)
FROM PRM_ExceptionLog__c
WHERE CreatedDate = LAST_N_DAYS:365
  AND PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'
GROUP BY PRM_ProcessName__c
```

### 8b — Extract the failing Identifier from the message → its practitioner & date gap

The prod messages embed the id: `…first exception on row N with id 0hkUW0000004…`. Paste those ids:

```sql
SELECT Id, PRM_Type__c, IdValue, PRM_Active__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       ParentRecordId, Parent.Name,
       Parent.PRM_EffectiveFrom__c, Parent.PRM_EffectiveTo__c
FROM Identifier
WHERE Id IN ('0hkUW0000004...', '0hkUW000000KK6...')
```

**Offending row =** `PRM_EffectiveFrom__c < Parent.PRM_EffectiveFrom__c` **OR** `PRM_EffectiveTo__c > Parent.PRM_EffectiveTo__c`.

### 8c — Tie that practitioner to an actual PAR submission

PAR submissions are tracked as **`IndividualApplication`** with RecordType **`PRM_PractitionerParticipationRequest`** (NOT a Case). Feed the `ParentRecordId` (Account) from 8b:

```sql
SELECT Id, Name, RecordType.DeveloperName, Status, CreatedDate, LastModifiedDate
FROM IndividualApplication
WHERE AccountId = :parentAccountIdFromStep8b
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
ORDER BY CreatedDate DESC
```

**How to read it:** if an `IndividualApplication` (PAR request) exists with `CreatedDate`/`LastModifiedDate` near the exception log's `CreatedDate`, that failure is plausibly PAR-driven; if the only nearby activity is the batch's scheduled run, it's a backend data-hygiene failure, not the form.

**Notes / gotchas:** there is **no PAR record type on `Case`** — PAR requests live on `IndividualApplication`. To positively attribute PAR-form errors you'd have to add an ExceptionLog step to `PRM_CreateParFormRecords`; today they're only visible as the end-user UI error.

---

## Query 9 — Exception logs created BY the PAR form (Apex touchpoints, confirmed 2026-07-09)

**Object:** `PRM_ExceptionLog__c`
**Use case:** Isolate rows that originated from the **PAR form** submission itself.

**Logging model:** the PAR OmniScript `PRM_PractitionerParticipationForm` creates records via **DataRaptors** — DataRaptor failures go to the **OmniScript UI, not** `PRM_ExceptionLog__c` (the logger is Apex-only). The form's **Apex steps** (invoked through the shared `PRM_OmniUtils` Callable dispatcher) DO log, stamping a method-label `PRM_ProcessName__c`. The only **unambiguously PAR-form** process names present in the data:

| `PRM_ProcessName__c` | PAR-form step | QA volume (365d) |
|---|---|---|
| `PRM_OmniUtils.updatePPLAddresesForPAR()` | PAR address / practice-location update | 39 |
| `PRM_PARProviderSearchHandler` | PAR provider-search | 35 |

```sql
SELECT Id, CreatedDate, PRM_ProcessName__c, PRM_ExceptionType__c,
       PRM_ErrorMessage__c, PRM_LineNumber__c, PRM_StackTrace__c
FROM PRM_ExceptionLog__c
WHERE CreatedDate = LAST_N_DAYS:365
  AND PRM_ProcessName__c IN ('PRM_OmniUtils.updatePPLAddresesForPAR()',
                             'PRM_PARProviderSearchHandler')
ORDER BY CreatedDate DESC
```

**Cross-check — did the effective-dates error ever come from the PAR form?** Add `AND PRM_ErrorMessage__c LIKE '%Effective Dates must be within Account%'` → **0 rows (QA)**. The PAR-form logs are unrelated errors (missing inputs, `Invalid conversion from runtime type List<String> to String`). **Confirms the effective-dates error is 100% backend-batch-driven, never PAR-form.**

**Notes / gotchas:**
- **Cannot perfectly isolate all PAR-form errors by process name.** `PRM_OmniUtils` is shared across PNC/PDM/Ancillary/etc. and stamps generic method labels (e.g. `PRMOmiUtils createHCPFNRecords()`) that are indistinguishable from other forms. Only the two names above carry "PAR" in the label.
- **Watch out for false positives** when searching `PRM_ProcessName__c LIKE '%Par%'`: it also matches data-load CSVs (`27-PRM_ProgramParticipation__c_*.csv`, `02a-PRM_ContractHierarchy-Parent_*.csv`) and Non-Par flows (`PRM_FetchNonParDetails`) — none of which are the PAR form.
- To capture **all** PAR-form failures reliably going forward, add a PAR-specific `processName` (e.g. `'Practitioner Participation Form'`) to a logging step in `PRM_CreateParFormRecords`.

---

## Attribution method — proving the Identifier trigger is the cause WITHOUT a PAR-form exception log (2026-07-09)

**Question:** the PAR form doesn't log this error (DataRaptor failures go to the browser, not `PRM_ExceptionLog__c`) — so how do we prove it's the Identifier Apex trigger and not one of the effective-date Validation Rules?

**Core principle:** causation is a property of the **object + its trigger**, not of the caller. Once you prove "updating an out-of-window Identifier throws this message from `PRM_IdentifierTriggerHandler`," it holds for *every* DML initiator (CAQH batch, activation batch, AND the PAR form). The batches merely make it visible; the form hits the identical code path but returns the error to the UI.

### Key-prefix → object → emitter map (verified via EntityDefinition, QA)

The exact string `Effective Dates must be within Account's Effective Dates` has only **4 active emitters** org-wide. Decode the record Id embedded in any occurrence of the error (`…first exception on row N with id XXXXXXXXX…`) — the 3-char key prefix names the object, and the object names the emitter:

| Key prefix | Object | Emits the message via |
|---|---|---|
| **`0hk`** | **Identifier** | **Apex ONLY — `PRM_IdentifierTriggerHandler` (Identifier has NO EffectiveDate VR)** |
| `0cm` | HealthcareProvider | VR `PRM_EffectiveDateValidation` (active) |
| `0bP` | HealthcareProviderTaxonomy | VR (active) |
| `a26` | PRM_ProgramParticipation__c | VR (active) |
| `0bN` | HealthcareProviderNpi | VR (**inactive** — ruled out) |

So an `0hk` Id in the error ⇒ unambiguously the Apex trigger. The Identifier object's only VRs (`PRM_EndDateValidation`, `PRM_IDValueValidation`, `PRM_Restrict_RecordType_Change`) do not emit this message.

### Query — key-prefix decoder (Tooling API)

```sql
SELECT QualifiedApiName, KeyPrefix
FROM EntityDefinition
WHERE QualifiedApiName IN ('Identifier','HealthcareProvider','HealthcareProviderTaxonomy',
                           'PRM_ProgramParticipation__c','HealthcareProviderNpi')
```
Run with `sf data query --use-tooling-api`. Results (QA): `0hk`=Identifier, `0cm`=HealthcareProvider, `0bP`=HealthcareProviderTaxonomy, `a26`=PRM_ProgramParticipation__c, `0bN`=HealthcareProviderNpi.

### Four ways to pinpoint (none need a PAR log)

1. **Decode the id** in any error occurrence (batch log OR the OmniScript's browser Network response for `PRM_CreateParFormRecords`). `0hk…` ⇒ Identifier ⇒ trigger.
2. **Static ownership map** (table above) — deterministic object→emitter lookup.
3. **Deterministic repro with debug logs** — take a known failing `0hk` id from the batch logs, enable Apex logs, `update` it via anonymous Apex. An Apex `addError` shows the exception inside `PRM_IdentifierTriggerHandler` with **NO `VALIDATION_RULE`/`VALIDATION_FORMULA` log event** (a VR failure always emits one — that's the clean discriminator).
4. **Caller-independence** — the PAR form updates the same out-of-window Identifiers, so the same trigger fires regardless of the missing log.

```apex
// Anonymous Apex — deterministic reproduction (run with debug logs ON)
Identifier idn = [SELECT Id, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, ParentRecordId
                  FROM Identifier WHERE Id = '0hkUW...'];
try { update idn; }
catch (DmlException e) { System.debug(e.getDmlMessage(0)); }  // → the effective-dates message
```
