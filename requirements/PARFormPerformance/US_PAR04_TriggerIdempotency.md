# USER STORY US-PAR-04: PAR Form — Trigger Idempotency for HealthcareProvider + PracFacility Identifiers

**Persona:** Salesforce Developer, Sr. Data Reporting Analyst, Operations Lead
**Priority:** P0 — smallest, lowest-risk story; hard pre-req for US-PAR-01 (batch must be safe to retry); immediate win against documented Cat B / Cat C duplicate-error failures (16 production cases in `Copy of Duplicate account and tax id errors.xlsx`, May 2026)
**Vertical:** Provider Network Management (PNM)
**Apex (impacted):**
- `PRM_HCProviderTriggerHandler.cls` — `populateSourceSystemIdentifier()` (lines 35–75); make idempotent
- `PRM_PracFacilityTriggerHandler.cls` — `setPracFacilityIdentifier()`; make idempotent (root cause of the 48 NPEs / 30 d on this method)
- `PRM_AccountTriggerHelper.cls` — `setAccIdentifier()`; review for the same idempotency gap on the practitioner-Account path (Category A)
- `PRM_OmniUtils.cls` — `validateExistsAcc()` (referenced from `PRM_FetchExistingNPIInfo`) — review whether it should ALSO query by composite identifier for the upstream existing-record-detection
- (NEW) `PRM_HCProviderTriggerHandlerTest.cls`, `PRM_PracFacilityTriggerHandlerTest.cls` — additional test scenarios for idempotent behavior

**Triggers (impacted):**
- `PRM_HCProviderTrigger.trigger` — no body change, just relies on the refactored handler
- `PRM_PracFacilityTrigger.trigger` (or wherever `setPracFacilityIdentifier` is wired) — same
- `PRM_AccountTrigger.trigger` — same (if Category A is in scope)

**DataRaptors (impacted — already discussed in `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md`):**
- `PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml` — add `<requiredForUpsert>true</requiredForUpsert>` + `<upsertKey>true</upsertKey>` on `SourceSystemIdentifier` to align with the trigger's new idempotency
- `PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` — same on Account's `HealthCloudGA__SourceSystemId__c`

**Relevant requirements:** `00_Overview_PARForm_BatchRefactor_Roadmap.md`, `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` (Item #6 — this story implements it for HCProvider AND extends it to PracFacility + Account), `PAR_Form_DuplicateErrors_DataFix_Runbook.md`

---

## Story

**As a** Salesforce Developer responsible for the PAR Form pipeline (and the eventual `PRM_ParFormSubmissionBatch` from US-PAR-01),
**I want** the before-insert / before-update triggers that compute external-style unique identifiers (`HealthcareProvider.SourceSystemIdentifier`, `HealthcarePractitionerFacility.PRM_PracFacilityIdentifier__c`, `Account.HealthCloudGA__SourceSystemId__c`) to be **idempotent** — i.e., detect when the computed identifier already exists in the database and convert the operation from an insert into an in-trigger update (or `addError` with a clean recoverable message) rather than letting the platform throw a generic `DUPLICATE_VALUE` exception,
**So that** (a) the existing 16 production failures in `Copy of Duplicate account and tax id errors.xlsx` stop recurring; (b) the 48 monthly NPEs from `setPracFacilityIdentifier` drop to zero; (c) `PRM_ParFormSubmissionBatch` can safely retry a failed submission (via `PRM_FailedRecordStaging__c` re-enqueue) without the retry itself colliding on the records partially created during the original failed attempt; and (d) the OmniScript catch-all `"Please contact your administration"` is replaced with an actionable recoverable error message.

**Why it matters:** The 16 production-blocked PAR submissions in `Copy of Duplicate account and tax id errors.xlsx` are **all** caused by these three triggers throwing `DUPLICATE_VALUE`. The runbook (`PAR_Form_DuplicateErrors_DataFix_Runbook.md`) documents a manual data-fix for each case, but the fix is one-off — the architectural defect is still there, and every new PAR submission with the same conditions (existing practitioner, existing vendor, broken HCNPI linkage) recreates the failure. Worse: once `PRM_ParFormSubmissionBatch` ships (US-PAR-01), it MUST be able to retry failed submissions safely. If the triggers are not idempotent, every retry trips the same `DUPLICATE_VALUE` cliff and the batch's `PRM_FailedRecordStaging__c` rows pile up forever in `Pending` status. **US-PAR-04 is the smallest, cheapest, and most immediately impactful piece of the roadmap.**

---

## Scope

| Layer | Component | Change |
|---|---|---|
| Apex | `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` | Query existing `HealthcareProvider` by computed identifier; if found, set `Id` on the incoming row OR `addError` with a clean recoverable message |
| Apex | `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` | Same pattern: query existing by computed identifier; idempotent path |
| Apex | `PRM_AccountTriggerHelper.setAccIdentifier` (and any other identifier-computing path on Account) | Review and make idempotent — root cause of Category A failures in the duplicate-errors story |
| Apex | `PRM_OmniUtils.cls` | Add `validateExistsForIdentifier(...)` helper used by all three triggers (shared utility — DRY) |
| Tests | New / extended trigger-handler tests | Three new scenarios: insert-when-already-exists, retry-after-partial-failure, bulk-insert-with-mixed-existing-and-new |
| DataRaptor | `PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml` | Mark `SourceSystemIdentifier` as `<upsertKey>true</upsertKey>` so DR-driven inserts hit the upsert path before the trigger fires |
| DataRaptor | `PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` | Mark `HealthCloudGA__SourceSystemId__c` as `<upsertKey>true</upsertKey>` |
| (Optional) Data hygiene | `PRM_FacilityPractitionerTriggerHandler` (or similar) on `HealthcareProviderTaxonomy` | Add the same idempotency pattern for HCPT — currently no unique constraint, but the 277 cumulative duplicate `(AccountId, TaxonomyId)` pairs prove the gap; see `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Item #7 for full HCPT story |

---

## Current State (verified from codebase)

### `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` (lines 35–75)

From `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` §Item #6 and the code:

```apex
// CURRENT (simplified):
for (HealthcareProvider hp : trigger.new) {
    if (String.isBlank(hp.SourceSystemIdentifier) && hp.AccountId != null) {
        Account acc = accountsById.get(hp.AccountId);
        Identifier id = identifiersByAccountId.get(hp.AccountId);  // EIN Tax-Id identifier
        if (acc != null && id != null) {
            // Auto-compute the unique identifier
            hp.SourceSystemIdentifier = id.IdValue + '-' + acc.Name;
        }
    }
}
```

`SourceSystemIdentifier` is unique at the schema level (`<unique>true</unique>` in the field metadata). When the practitioner Account already exists in the org and the PAR form's "existing NPI" detection misroutes to the create path (the root cause for Categories A and B), this trigger computes the SAME value that already exists on a `HealthcareProvider` row → `DUPLICATE_VALUE`. The trigger has no idempotency check; it relies entirely on the platform's unique constraint to enforce uniqueness, and the platform's error is opaque to the OmniScript layer.

### `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` (referenced in `PAR_Form_PartialDataRollback_Investigation_FixPlan.md`)

Throws **48 NPEs / 30 days** in production. Inspection shows the method depends on an upstream sub-IP populating certain fields on the HPF record; when the upstream sub-IP fails (one of the partial-data sources we're solving), this trigger tries to dereference a null pointer. Two fixes are needed: (a) null-guards in the trigger so it fails gracefully with a clean `addError` instead of an NPE, AND (b) idempotency so the trigger detects an existing HPF with the same computed identifier and short-circuits.

### `PRM_AccountTriggerHelper.setAccIdentifier` (referenced for Category A)

Category A failures (`Account.HealthCloudGA__SourceSystemId__c` collision) happen when the PAR form attempts to insert a new practitioner Account whose NPI is already on an existing Account but the HCNPI linkage is broken. Same root cause — no idempotency on the helper. `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Item #4 (DataRaptor upsert) is one half of the fix; the trigger-side idempotency is the other half.

### Why "DR upsert" alone is not enough

`PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` proposes (Items #4 and #5) converting the DR inserts to upserts on `HealthCloudGA__SourceSystemId__c` and `SourceSystemIdentifier`. That fixes the DR-call path. BUT:
1. The trigger fires before the DR's upsert reach the unique-constraint check, and if the trigger has computed a duplicate `SourceSystemIdentifier` for an Apex-driven insert (not a DR), the platform still throws.
2. `PRM_ParFormSubmissionBatch` (US-PAR-01) does its DML directly via Apex `Database.insert(...)`, not via DataRaptors. The DR-upsert fix does NOT help the batch. We need the trigger itself to be idempotent.

So US-PAR-04 is the **trigger-level idempotency** that complements US-PAR-01 Items #4 / #5 (DR-upsert level idempotency). Both are required to fully close the gap.

---

## Proposed Architecture (Trigger Pattern)

```apex
// IDEMPOTENT TRIGGER PATTERN — applied uniformly across all three handlers
//
// Before-insert / before-update: detect duplicate by computed identifier,
// convert into update (preferred) or addError (fallback for invalid bulk ops).

private void populateSourceSystemIdentifier(List<HealthcareProvider> incoming) {
    // 1. Compute the identifier for each incoming row.
    Map<HealthcareProvider, String> computedKeyByRow = computeIdentifiers(incoming);

    // 2. Bulk-query existing HCProvider rows with matching identifiers.
    Set<String> keys = new Set<String>(computedKeyByRow.values());
    keys.remove(null);
    if (keys.isEmpty()) return;

    Map<String, HealthcareProvider> existingByKey = new Map<String, HealthcareProvider>();
    for (HealthcareProvider hp : [
        SELECT Id, SourceSystemIdentifier, AccountId
        FROM HealthcareProvider
        WHERE SourceSystemIdentifier IN :keys
    ]) {
        existingByKey.put(hp.SourceSystemIdentifier, hp);
    }
    if (existingByKey.isEmpty()) {
        // Nothing to dedup — assign computed identifier as before.
        for (HealthcareProvider hp : incoming) {
            String key = computedKeyByRow.get(hp);
            if (key != null) hp.SourceSystemIdentifier = key;
        }
        return;
    }

    // 3. For each incoming row that collides, choose recovery path.
    for (HealthcareProvider hp : incoming) {
        String key = computedKeyByRow.get(hp);
        if (key == null) continue;
        HealthcareProvider existing = existingByKey.get(key);
        if (existing == null) {
            hp.SourceSystemIdentifier = key;
            continue;
        }
        // PATH A — In-trigger upsert: if this is a new row (no Id),
        //          set the Id to the existing row's Id so the platform
        //          converts the insert into an update. ONLY allowed when
        //          Trigger.operationType is BEFORE_INSERT and the user
        //          context permits update on the existing row.
        if (Trigger.isBefore && Trigger.isInsert && hp.Id == null) {
            // hp.Id = existing.Id;  ← this is the "in-trigger upsert" trick
            // CAUTION: this trick works for some Salesforce objects but not all,
            // and Health Cloud objects in particular may behave unexpectedly.
            // We instead prefer PATH B as the safer default. Activate PATH A
            // only after sandbox validation that the platform accepts it.

            // PATH B — Clean recoverable error: addError with a structured
            //          message the OmniScript can catch and route to the
            //          "existing practitioner detected — reuse" UX.
            hp.addError('PRM_HCPROVIDER_EXISTS::' + existing.Id
                + '::Existing HealthcareProvider record found for '
                + key + '. Reuse via PAR form update path.');
        }
    }
}
```

The same pattern (with object-specific tweaks) goes into `setPracFacilityIdentifier` and `setAccIdentifier`.

### Why "PATH B" (addError) over "PATH A" (in-trigger Id assignment)

| Path | Pro | Con |
|---|---|---|
| **A (Id assignment)** | Truly silent idempotency; insert becomes update; the calling code doesn't even know a duplicate was averted | Salesforce Apex documentation explicitly warns this is undefined behaviour on some standard objects; the `Trigger.new[i].Id` assignment in before-insert is **not officially supported** as a way to convert insert→update; behavior on Health Cloud objects has not been validated |
| **B (addError)** | Officially supported; structured error message the OmniScript / batch catch block can parse (`PRM_HCPROVIDER_EXISTS::<id>::<msg>`); easy to surface to the user; safe to retry via the staging mechanism | Caller must handle the error explicitly; doesn't silently merge — the caller has to take the existing Id and use the update path itself |

**Recommendation:** Default to **PATH B**. The batch and the DR-upsert path (Items #4 / #5 of the duplicate-errors story) can both parse the structured error string and recover. PATH A is too risky for production today.

### Why the bulk query is safe

The pattern requires one SOQL per trigger invocation regardless of row count — the `IN :keys` query is a single SOQL. This costs 1 SOQL per before-insert / before-update event on each of three triggers. The PAR submission batch (US-PAR-01) creates at most ~5 HealthcareProvider rows per submission. Trigger SOQL impact: 3 extra SOQL per submission. Well within budget.

For `Database.Stateful` batch behavior (if the trigger fires inside `PRM_ParFormSubmissionBatch.execute`), the cached lookup will be re-queried per chunk — that's acceptable because the chunk size is 1 submission anyway (US-PAR-01).

---

## Technical Section (For Developers)

### A. `PRM_HCProviderTriggerHandler` — refactor

Apply the **PATH B** pattern from above. Three changes:

1. Refactor `populateSourceSystemIdentifier` to do the bulk query first and `addError` when collision detected.
2. Extract the identifier-computation logic into a private method `computeIdentifierForRow(HealthcareProvider hp, Account acc, Identifier id)` so the test class can call it directly.
3. Add a defensive null-guard at the top: if `hp.AccountId == null` OR the Account has no EIN Tax-Id identifier, do NOT throw — `addError('PRM_HCPROVIDER_MISSING_INPUTS::...')`. This is partly the existing `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Item #6 scope.

### B. `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` — refactor

Same pattern. Additional fix for the 48-NPE-per-month issue:

```apex
// Before any field-dereference, validate the row has the inputs it needs:
if (hpf.HealthcareFacilityId == null || hpf.PractitionerId == null) {
    hpf.addError('PRM_PRACFACILITY_MISSING_INPUTS::HealthcareFacilityId='
        + hpf.HealthcareFacilityId + ', PractitionerId=' + hpf.PractitionerId
        + '::Upstream record creation must complete before this insert.');
    continue;
}
// ... then proceed with identifier computation and the bulk-existing query.
```

This converts the 48 NPEs / month into 48 clean `addError` rejections — far better triage signal, AND the calling Apex (the batch from US-PAR-01) can parse the structured message and decide whether to retry-with-fixed-input or fail-permanently.

### C. `PRM_AccountTriggerHelper.setAccIdentifier` — refactor

Same pattern. Critical: the existing logic computes Account's `SourceSystemIdentifier` (different from `HealthCloudGA__SourceSystemId__c`); both fields can collide. The bulk-existing query needs to check **both** identifier fields if both are computed in the trigger.

### D. Shared utility `PRM_OmniUtils.validateExistsForIdentifier`

To keep the three trigger handlers DRY, add a static utility:

```apex
/**
 * Bulk-detect existing records by a computed identifier field.
 * Returns a map from identifier value → existing record Id.
 */
public static Map<String, Id> findExistingByIdentifier(
    String objectApiName,    // e.g., 'HealthcareProvider'
    String identifierField,   // e.g., 'SourceSystemIdentifier'
    Set<String> identifiers   // computed values to check
) {
    if (identifiers == null || identifiers.isEmpty()) return new Map<String, Id>();
    String soql = 'SELECT Id, ' + identifierField + ' FROM ' + objectApiName
        + ' WHERE ' + identifierField + ' IN :identifiers';
    Map<String, Id> result = new Map<String, Id>();
    for (SObject so : Database.query(soql)) {
        String key = (String) so.get(identifierField);
        if (String.isNotBlank(key) && so.Id != null) result.put(key, so.Id);
    }
    return result;
}
```

Reused by all three trigger handlers; one place to test the SOQL injection guards.

### E. DataRaptor metadata changes (overlap with `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md`)

`PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml` — find the HealthcareProvider section, locate the `SourceSystemIdentifier` field, set:
```xml
<requiredForUpsert>true</requiredForUpsert>
<upsertKey>true</upsertKey>
```

`PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` — find the Account section, locate `HealthCloudGA__SourceSystemId__c`, set the same flags.

These are explicitly called out in the duplicate-errors story (Items #4 and #5). US-PAR-04 inherits and verifies them.

### F. Test scenarios

For each of the three trigger handlers, add three new test scenarios:

1. **Insert-when-already-exists.** Pre-insert an HCProvider with `SourceSystemIdentifier='12345-Acme'`. Trigger another HCProvider insert via Apex `insert` that would compute the same identifier. Assert: clean `addError` with structured message `PRM_HCPROVIDER_EXISTS::<id>::...`. Assert: no platform `DUPLICATE_VALUE` exception escapes.
2. **Retry-after-partial-failure.** Insert HCProvider via Apex, force a downstream NPE so the transaction rolls back the HCP but the partial state (HCNPI or Account) survives. Re-insert HCProvider. Assert: clean `addError` (not collision; not NPE).
3. **Bulk-insert-with-mixed-existing-and-new.** Insert 5 HCProviders in one DML; 2 collide with existing, 3 do not. Assert: 2 rows have `addError`, 3 rows commit. Verify SOQL count is 1 (bulk).

### G. Migration order (deployment safety)

The trigger refactors are deployable independently of US-PAR-01 / US-PAR-05 — they only ADD safety, they never break a happy path. **Deploy this story FIRST** in Sprint 1, then verify in production for 7 days, then start US-PAR-01.

---

## Acceptance Criteria

**AC1 — HCProvider trigger idempotency.**
**Given** a `HealthcareProvider` row exists in QA with `SourceSystemIdentifier='223683554-Advanced Ambulatory Anesthesia LLC'` (per row 20 of `Copy of Duplicate account and tax id errors.xlsx`),
**When** an Apex test (or live PAR submission) attempts to insert a new HCProvider whose computed `SourceSystemIdentifier` equals the existing value,
**Then** the trigger's `addError` fires with message `PRM_HCPROVIDER_EXISTS::0bSUW000000GoaM2AS::Existing HealthcareProvider record found for 223683554-Advanced Ambulatory Anesthesia LLC. Reuse via PAR form update path.`, the platform `DUPLICATE_VALUE` exception does NOT escape, and the calling code can parse the structured message to retrieve the existing record's Id.

**AC2 — PracFacility trigger NPE elimination.**
**Given** the upstream IP failed to populate `HealthcarePractitionerFacility.HealthcareFacilityId` (causing the historical 48 NPEs / 30 d),
**When** the row reaches the before-insert trigger,
**Then** `setPracFacilityIdentifier` fires `addError('PRM_PRACFACILITY_MISSING_INPUTS::...')` instead of throwing an NPE, and the post-deployment monitoring query `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_ProcessName__c='PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier' AND PRM_ExceptionType__c='NullPointerException' AND CreatedDate=LAST_N_DAYS:14` returns **0**.

**AC3 — PracFacility idempotency.**
**Given** an existing `HealthcarePractitionerFacility` row with a computed `PRM_PracFacilityIdentifier__c` value,
**When** an Apex insert attempts to create a duplicate row with the same identifier,
**Then** the trigger fires `addError('PRM_PRACFACILITY_EXISTS::<id>::...')` and the platform unique-constraint exception does NOT escape.

**AC4 — Account trigger idempotency (Category A).**
**Given** an existing Account with `HealthCloudGA__SourceSystemId__c='1700924669'` (row 20 NPI from the duplicate-errors spreadsheet),
**When** the PAR form attempts to insert a new practitioner Account with the same NPI,
**Then** `setAccIdentifier` fires `addError('PRM_ACCOUNT_EXISTS::<existing-id>::...')` and the calling DataRaptor / IP / batch can parse the message and route to the update path.

**AC5 — Batch retry safety (the most important AC for US-PAR-01).**
**Given** `PRM_ParFormSubmissionBatch` (from US-PAR-01) has rolled back submission #42 because of a `DUPLICATE_VALUE` collision, AND the staging row for submission #42 was marked `Status='Fixed'` after analyst intervention,
**When** the staging row's retry mechanism re-enqueues submission #42 with the SAME envelope (including the same NPI / TaxId / addresses),
**Then** the second attempt:
- Does NOT throw `DUPLICATE_VALUE` on `HealthcareProvider.SourceSystemIdentifier`
- Does NOT throw `DUPLICATE_VALUE` on `Account.HealthCloudGA__SourceSystemId__c`
- Either succeeds (records are created / updated cleanly) OR fails with a clean structured `addError` the staging row can mark `Failed - Terminal`

**AC6 — No regression on bulk operations.**
**Given** a bulk insert of 200 HealthcareProvider rows via the Data Import Wizard or a data-loading script,
**When** the trigger fires,
**Then** SOQL count attributable to the new idempotency query is exactly **1** (bulk `IN :keys` query), the trigger does not enter loops or excessive memory usage, and any pre-existing duplicates are `addError`-blocked individually with no impact on the other 199 rows.

**AC7 — Structured error message parseability.**
**Given** a calling Apex method receives a `DmlException` from a failed insert where the trigger fired `addError('PRM_HCPROVIDER_EXISTS::0bSUW000000GoaM2AS::Existing HealthcareProvider record found...')`,
**When** the catch block calls `parseStructuredError(DmlException dmlEx)`,
**Then** the method returns `{ errorCode: 'PRM_HCPROVIDER_EXISTS', existingId: '0bSUW000000GoaM2AS', message: 'Existing HealthcareProvider record found...' }` and the calling code can route to the update path with `existingId`.

**AC8 — Pre-existing 16 cases unblocked.**
**Given** the 16 documented production cases in `Copy of Duplicate account and tax id errors.xlsx`,
**When** the cleanup steps in `PAR_Form_DuplicateErrors_DataFix_Runbook.md` are completed AND the analyst re-submits each one via the PAR form,
**Then** all 16 submissions complete successfully (either through the create or the update path, depending on which records pre-exist), with no `DUPLICATE_VALUE`-driven blocks.

**AC-MAX-BULK — Idempotency check uses one SOQL per trigger invocation at max PAR scale.**
**Given** the `PRM_ParFormSubmissionBatch` (US-PAR-01) inserts at peak load — `Trigger.new.size()` reaches 50 (`HealthcarePractitionerFacility`), 55 (`HealthcareFacility`), 6 (`HealthcareProvider`), 6 (`Account`), or ~150 (`ContactPointAddress` from indirect inserts) in a single DML statement (see `US_PAR_ScaleAudit_5Groups_10Locations.md`),
**When** the corresponding trigger fires for that bulk `Trigger.new`,
**Then** the trigger's idempotency check executes **exactly one SOQL query** — selecting the existing identifier table by the computed-key `IN :keys` set — iterates `Trigger.new` once to compare against the in-memory map, and calls `addError()` only on the duplicates. `Limits.getQueries()` attributable to the new idempotency logic must increase by **exactly 1** for any `Trigger.new.size()` ∈ [1, 200]. A unit test enforces this:
> ```apex
> @isTest static void triggerIdempotency_oneSOQL_at50PPLrows() {
>     Test.startTest();
>     Integer queriesBefore = Limits.getQueries();
>     insert TestDataFactory.buildPPLs(50);  // 50 HealthcarePractitionerFacility in one DML
>     Integer added = Limits.getQueries() - queriesBefore;
>     Test.stopTest();
>     // setPracFacilityIdentifier idempotency check MUST be bulk-safe.
>     // Allow ±2 for unrelated framework SOQLs from other handlers in the chain.
>     System.assert(added <= 3, 'setPracFacilityIdentifier must use bulk SOQL; observed ' + added + ' queries for 50 PPL rows');
> }
> @isTest static void triggerIdempotency_oneSOQL_at55HFrows() { /* same shape for HealthcareFacility */ }
> @isTest static void triggerIdempotency_oneSOQL_at150CPArows() { /* same shape for ContactPointAddress */ }
> ```

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Has anyone validated PATH A (assigning `hp.Id = existing.Id` in before-insert to convert insert→update) against Health Cloud objects in this org? If yes and it works, the trigger becomes silently idempotent rather than `addError`-based. | Architectural choice; affects all of §A / §B / §C. | Architecture Lead |
| 2 | Are there any existing callers (Apex, Flow, Process Builder) that currently catch the platform's `DUPLICATE_VALUE` exception and have specific recovery logic? They will need to be updated to also handle the new `addError` messages with `PRM_*_EXISTS::` prefix. | Caller migration scope. | Apex Lead |
| 3 | Should the structured `addError` message be machine-readable (current proposal: `PRM_<OBJ>_EXISTS::<existingId>::<humanMsg>`), or should we use a custom exception class with extra fields? Custom exception is cleaner but Salesforce trigger `addError` is a String only. | API design. | Architecture Lead |
| 4 | Is there a third identifier-computing trigger we missed? `PRM_HCNPITrigger`? `PRM_IdentifierTrigger`? | Completeness. | Apex Lead |
| 5 | For `HealthcareProviderTaxonomy` — there is no unique constraint, yet 277 duplicate `(AccountId, TaxonomyId)` pairs accumulated. Should US-PAR-04 add a trigger-level idempotency check on HCPT (preventing duplicate creation), even though the underlying unique constraint doesn't exist? Or is that scope of `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Item #7 only? | Scope. | Operations Lead |
| 6 | Do the existing trigger-handler test classes (`PRM_HCProviderTriggerHandlerTest`, etc.) have ≥ 90% coverage today? Will adding the new scenarios still keep them within the coverage requirement? | QA. | QA Lead |
| 7 | Should the trigger ALSO publish a `PRM_ExceptionLogEvent__e` (US-PAR-02) when it fires `addError`, so we have observability into how often the idempotency path is hit? Or is that too noisy? | Observability vs noise. | Operations Lead |
| 8 | What is the production deployment plan — is a rolling deploy possible (deploy the Apex first, then the trigger), or does the platform require atomic deployment? | Deployment safety. | Release Manager |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_HCProviderTriggerHandler.cls` | Apex (existing) | **HIGH** | Body refactor of `populateSourceSystemIdentifier` |
| `PRM_PracFacilityTriggerHandler.cls` | Apex (existing) | **HIGH** | Body refactor of `setPracFacilityIdentifier` + NPE guards |
| `PRM_AccountTriggerHelper.cls` | Apex (existing) | **MEDIUM** | Body refactor of `setAccIdentifier` |
| `PRM_OmniUtils.cls` | Apex (existing) | **LOW** | One new utility method `findExistingByIdentifier` |
| Three `*TriggerHandlerTest.cls` files | Apex tests (existing) | **MEDIUM** | Three new scenarios per handler |
| `PRMDRPPersonAccHCProviderNPITaxonomy_1` | DataRaptor (existing) | **LOW** | Two XML attribute additions |
| `PRMDRCreateCaseCaseManagerAndAccount_1` | DataRaptor (existing) | **LOW** | Two XML attribute additions |
| Calling Apex / DR catch blocks across PAR pipeline | Apex / IP (existing) | **MEDIUM** | Update catch blocks to parse the new structured error messages |
| `PRM_ParFormSubmissionBatch.cls` (from US-PAR-01) | Apex (NEW, not yet shipped) | **MEDIUM** | The batch's per-row catch block must parse structured errors and route to the update path |

---

## Estimated Effort

| Component | Type | Effort | Notes |
|---|---|---|---|
| `PRM_HCProviderTriggerHandler` refactor | Apex | **M** (2–4 hrs) | Apply pattern. |
| `PRM_PracFacilityTriggerHandler` refactor + NPE guards | Apex | **M** (2–4 hrs) | Pattern + null-guards. |
| `PRM_AccountTriggerHelper` refactor | Apex | **M** (2–4 hrs) | Pattern. |
| `PRM_OmniUtils.findExistingByIdentifier` utility | Apex | **S** (< 1 hr) | One method. |
| Trigger-handler tests (× 3) | Apex tests | **L** (4–8 hrs) | 3 scenarios × 3 handlers = 9 new tests. |
| DataRaptor metadata edits (× 2) | XML | **S** (< 1 hr) | Two upsertKey flags each. |
| Audit + update calling catch blocks | Apex | **M** (2–4 hrs) | ~5 catch blocks to update. |
| Sandbox verification (8 ACs) | QA | **M** (2–4 hrs) | Per AC. |

**Total Estimated Effort:** **~2–3 person-days** — overall **M** sprint slice. This is the cheapest story in the roadmap and the highest leverage per day.

---

## Deployment Checklist

**Pre-requisites:**
- [ ] Resolve Clarification #1 (PATH A vs PATH B). Production deployment uses PATH B unless validated.

**Metadata (deploy in order):**
- [ ] `PRM_OmniUtils.cls` (add new utility) + regression test pass
- [ ] `PRM_HCProviderTriggerHandler.cls` + test
- [ ] `PRM_PracFacilityTriggerHandler.cls` + test
- [ ] `PRM_AccountTriggerHelper.cls` + test
- [ ] `PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml` upsertKey additions
- [ ] `PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` upsertKey additions
- [ ] Catch-block updates in any existing Apex / IP callers

**Verification in Sandbox:**
- [ ] AC1: insert duplicate HCProvider via Apex test → assert structured `addError`
- [ ] AC2: query 30-day NPE count from `PRM_PracFacilityTriggerHandler` → assert 0 within 14 days post-deploy
- [ ] AC3: insert duplicate HPF via Apex test → assert structured `addError`
- [ ] AC4: insert duplicate Account via Apex test → assert structured `addError`
- [ ] AC5: simulate batch retry against existing partial state — assert no platform exceptions escape
- [ ] AC6: bulk insert 200 HCProviders, mixed with pre-existing → assert SOQL ≤ 4 (1 new + existing), failures isolated
- [ ] AC7: parse structured error from a forced collision in a calling Apex test
- [ ] AC8: re-submit each of the 16 production cases in `Copy of Duplicate account and tax id errors.xlsx` after the data-fix runbook is applied → assert all 16 succeed

**Post-Deployment Monitoring (first 30 days):**
- [ ] Daily: `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_ExceptionType__c='NullPointerException' AND PRM_ProcessName__c='PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier' AND CreatedDate=LAST_N_DAYS:1` — target 0
- [ ] Daily: `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_ErrorMessage__c LIKE '%duplicate value found: SourceSystemIdentifier%' AND CreatedDate=LAST_N_DAYS:1` — target 0
- [ ] Weekly: new HCPT duplicate `(AccountId, TaxonomyId)` pairs (depends on Clarification #5 — if HCPT idempotency is in scope, target 0)
- [ ] Weekly: count of structured `addError` rejections via `PRM_HCPROVIDER_EXISTS::` / `PRM_ACCOUNT_EXISTS::` etc. — non-zero is expected and good (it means the safety net is working)

---

## Related Stories

| Story | Priority | Relationship |
|---|---|---|
| `US-PAR-01` (Batch Refactor) | P0 | **Hard consumer** — batch retry safety depends on this story |
| `US-PAR-02` (Exception Logging via Platform Event) | P0 | **Optional consumer** — Clarification #7: do we publish events on idempotency hits? |
| `US-PAR-05` (Failed Record Staging + Retry UX) | P1 | **Consumer** — staging-row retry logic parses the structured `addError` messages |
| `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Items #4–#6 | P0 (in flight) | **Sibling** — Items #4 and #5 (DR-upsert) are the DR-layer half of this story's fix; Item #6 IS this story's HCProvider work |
| `PAR_Form_DuplicateErrors_DataFix_Runbook.md` | (data-fix runbook) | **One-off** — cleans the existing 16 cases; this story prevents recurrence |
| `PAR_Form_PartialDataRollback_Investigation_FixPlan.md` | (investigation) | **Reference** — documents the 48 NPEs / 30 d this story eliminates |
