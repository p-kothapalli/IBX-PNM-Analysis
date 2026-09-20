# US-PAR Scale Audit — 5 Groups × 10 Locations Maximum

**Audit date:** 2026-05-28
**Audited stories:** US-PAR-01 (Batch Refactor), US-PAR-02 (Platform Event Logging), US-PAR-03 (Pre-Submit Callout Phase), US-PAR-04 (Trigger Idempotency), US-PAR-05 (Failed Record Staging UX)
**Question that triggered the audit:** "We can enter 5 groups in the PAR form with 10 locations for each group. Does the solution still hold at this scale?"

**TL;DR:**
1. The OmniScript caps confirmed by reading the metadata are **5 groups × 10 locations = 50 location rows per submission**.
2. At that ceiling, **one PAR submission creates ~470–500 database rows across ~15 object types**.
3. **US-PAR-01 (Batch)** holds — `chunkSize=1` survives the worst case, but the user story's sizing claim ("30–50 DML rows") was understated and is corrected here.
4. **US-PAR-03 (Pre-Submit Callout)** does **not** hold as originally specified — 50 sequential Precisely callouts at ~500ms each ≈ 25s sync wait. **Five concrete corrections** are required (bulk endpoint, dedup, parallelism, HTTP Continuation, fail-fast budget).
5. **US-PAR-02, US-PAR-04, US-PAR-05** hold structurally but each needs one additional acceptance criterion to make the max-scale behaviour explicit and testable.

---

## 1. Confirmed Repeat-Element Limits (from OmniScript metadata)

Active OmniScript versions in the workspace today:

| OmniScript | Active version | `<isActive>` | Confirmed via |
|---|---|---|---|
| `PRM_PractitionerParticipationForm_English` | **v111** | `true` (line 5) | `rg '<isActive>' ...111.os-meta.xml` |
| `PRM_PractitionerParticipationAddressForm_English` | **v54** | `true` | `rg '<isActive>' ...54.os-meta.xml` |

### Repeatable blocks (only blocks where `"repeat": true`)

| OmniScript | Element name | `repeatLimit` | Interpretation | Max instances per submission |
|---|---|---|---|---|
| Main PAR form v111 (line 2600–2614) | `GroupInformation` | `4` | Initial instance + 4 additional clones | **5 groups** |
| Main PAR form v111 (line 3194–3208) | `AddLicenseBlock` | `3` | Initial + 3 additional licenses | **4 licenses** (per state) |
| Address sub-form v54 (line 1995–2014) | `AdditionalAddress` | `9` | Primary office + 9 additional within each group | **10 locations** per group |

### Non-repeatable blocks that nonetheless multiply

| Block | Cardinality | Notes |
|---|---|---|
| Primary Office Address (`PrimaryOfficeAddressBlock`) | 1 per group | Implicit; user must fill it |
| `PrimaryContact` / `SecondaryContact` | 1 + 1 (boolean toggle) | Two `Contact` rows max |
| `ProviderSpecialty` + `AdditionalSpeciality` (multi-select LWC) | 1 + N | `prmMultiSelect.maxselection` defaults to `optionData.length` → no cap. Typical 1–5; theoretical worst case ≈ 50 |
| Practitioner Person Account itself | 1 | One PAR = one practitioner |

**Definitive maximums per submission:**

```
groups            = 5
locations         = 5 × 10 = 50
licenses          = 4
contacts          = 2
practitioner specialties = ~5 typical, up to all taxonomies (uncapped by UI)
```

---

## 2. Maximum Entity Volume Per Submission

Computed by walking the existing pipeline (`PRM_CreatePractitionerAddressRecords_Procedure_41` has **44 DataRaptor Post Actions** wrapped in two Loop Blocks; `PRM_CreateGroupScreenRecord` writes Account + HCP + HCNPI + HCPT per group; `PRM_PractitionerScreenRecordCreation` writes the practitioner Person Account, HCP, HCNPI, IndividualApplication, Case).

| Object | Per-row formula | Worst case (5 × 10) | Owns DML? |
|---|---|---|---|
| `Account` (Practitioner Person) | 1 | **1** | PAR-01 |
| `Account` (Vendor / Group) | `groups` | **5** | PAR-01 |
| `HealthcareProvider` (HCP) | `1 + groups` | **6** | PAR-01 |
| `HealthcareProviderNpi` (HCNPI) | `1 + groups` | **6** | PAR-01 |
| `HealthcareProviderTaxonomy` (HCPT) | `prac_specialties + groups × group_specialties` ≈ `5 + 5 × 3` | **~20** (typical) / up to **~50** if multi-select unbounded | PAR-01 |
| `HealthcareFacility` (HF) | `groups + locations` | **55** | PAR-01 |
| `Schema.Location` | `locations` | **50** | PAR-01 |
| `Schema.Address` | `locations + few` | **~60** (50 office + 5 billing + 5 mailing) | PAR-01 |
| `HealthcarePractitionerFacility` (PPL / HPF) | `1 prac × locations` | **50** | PAR-01 |
| `ContactPointAddress` (CPA) | `locations × ~3` (phone / fax / email) | **~150** | PAR-01 |
| `Contact` | `1 + (1 if secondary)` | **2** | PAR-01 |
| `HealthcarePractitionerLicense` | `licenses` | **4** | PAR-01 |
| `IndividualApplication` (Case Manager) | 1 | **1** | PAR-01 |
| `Case` (PRM) | 1 | **1** | PAR-01 |
| `ProviderFeatureAssignment` (PFA) | `≈ 2 × (1 + groups)` | **~10** | PAR-01 |
| Custom `PRM_Identifier*__c` (Vendor / Practitioner / HCProvider / HCNPI / HF / PPL) | one per parent | **~70** | Triggers (PAR-04) |

**Worst-case totals per submission**

```
core PAR-01 DML rows         ≈ 420
identifier-trigger DML rows  ≈  70
─────────────────────────────────
TOTAL records per submission ≈ 490
unique object types DML'd    ≈  15
```

**Apex sync-transaction governor budget (one batch `execute(scope=1)` call gets the full budget):**

| Limit | Apex limit | One PAR submission at max | Headroom |
|---|---|---|---|
| DML statements per transaction | 150 | ~15 (one bulked DML per object type) | **OK** (90% headroom) |
| DML rows per transaction | 10,000 | ~490 | **OK** (95% headroom) |
| SOQL queries per transaction | 100 | ~25–40 (lookup queries + memoization warm-up) | **OK** (60–75% headroom) |
| SOQL rows per transaction | 50,000 | a few thousand at most | **OK** |
| CPU time | 10,000 ms sync / 60,000 ms async | ~3–6s in `execute()` | **OK** |
| Heap | 6 MB sync / 12 MB async | Envelope JSON + row buffers ≈ 1–2 MB | **OK** |
| Async (`@future` / `Queueable` / batch) DML rows | 10,000 | 490 | **OK** |
| Callouts per transaction | 100 | 0 in batch (US-PAR-03 invariant) / **50 in pre-callout** (problem — see §4) | **VIOLATION in pre-callout** |

**Conclusion at the entity level:** One submission, even at the absolute maximum (5 groups × 10 locations + every multi-select set), comfortably fits in **one Apex async transaction (batch `execute(scope=1)`)** for DML, SOQL, CPU, and heap. The architecture choice is sound. The risk is concentrated in **(a) callouts in the pre-DML phase**, and **(b) triggers that take O(N) SOQL** instead of O(1) when 50 PPL rows / 150 CPA rows / 60 Address rows arrive at once.

---

## 3. US-PAR-01 (Batch Refactor) — Audit Verdict

### Verdict: **HOLDS WITH SIZING CORRECTIONS**

| Audit item | Original story | Corrected for 5×10 |
|---|---|---|
| Sizing claim (line 178 of `US_PAR01_BatchRefactor.md`) | "~30–50 DML rows" | **~490 DML rows / ~15 object types** at max |
| Chunk size | `chunkSize=1` (one submission per `execute(scope)`) | **Stay at 1** — verified against the new numbers, still inside governor budget |
| Memoization scope | Taxonomy by code, RecordType Ids, FeatureConfigSetting | **Add to memoization set:** `HealthcareFacility` by group `SourceSystemIdentifier`, `Account` by NPI, `Schema.Address` by `(line1, city, zip)` digest — these are *re-queried per location today* and at 50 locations would burn 50 SOQLs each without memoization |
| Per-row Savepoint | `Database.setSavepoint()` per submission, rollback on failure | **Stay** — one submission is one atomic unit; rolling back 490 rows takes <1s |
| Max-scale acceptance criterion | (none) | **NEW AC-MAX:** see §3.2 below |

### 3.1 Required edit to `US_PAR01_BatchRefactor.md` — Line 178 sizing claim

**OLD:**
> A single PAR submission may create up to ~30–50 DML rows (Account, HCNPI, HCP, HCPT, Identifier, vendor Account, vendor HCP, HF, HPF, CPA, ProviderFeatureAssignment, Contact, …).

**NEW:**
> A single PAR submission at maximum scale (5 groups × 10 locations = 50 PPL rows, ~150 CPA rows, ~60 Address rows, ~55 HealthcareFacility rows, plus 6 Accounts, 6 HCP, 6 HCNPI, ~20 HCPT, 4 Licenses, 2 Contacts, ~10 PFA, 1 IA, 1 Case, ~70 trigger-inserted Identifier rows) creates **~490 DML rows across ~15 object types**. Bundling N submissions per chunk multiplies that and risks the SOQL=201 / DML=151 cliff. With `chunkSize=1`, one submission's atomicity per chunk fits comfortably inside Apex async transaction limits (15 of 150 DML statements, 490 of 10,000 DML rows, ~30 of 100 SOQL queries with full memoization). Tune up *only after* the AC-MAX max-scale load test described below.

### 3.2 NEW Acceptance Criterion to add to `US_PAR01_BatchRefactor.md`

**AC-MAX — One submission with 5 groups × 10 locations completes inside one batch chunk.**

> **Given** a PAR submission with the maximum supported payload (5 groups, 10 locations per group = 50 PPL rows, ~150 ContactPointAddress rows, ~60 Address rows, ~55 HealthcareFacility rows, 6 Accounts, 6 HealthcareProvider, 6 HealthcareProviderNpi, ~20 HealthcareProviderTaxonomy, 4 Licenses, 2 Contacts, ~10 ProviderFeatureAssignment, 1 IndividualApplication, 1 Case),
> **When** `PRM_ParFormSubmissionBatch.execute(scope = [thisSubmission])` runs,
> **Then** the transaction completes within **6 seconds CPU**, with `Limits.getDMLStatements() ≤ 20`, `Limits.getDMLRows() ≤ 600`, `Limits.getQueries() ≤ 50`, `Limits.getCallouts() == 0`, and `IA.PRM_ParFormSubmissionStatus__c = 'Success'`.

### 3.3 NEW load test scenario

Add to the test plan section of `US_PAR01_BatchRefactor.md`:

- [ ] **Max-scale load test (manual / scheduled in QA):** Build a TestDataFactory helper `buildMaxScaleEnvelope()` that fills 5 groups × 10 locations with realistic data, runs `Database.executeBatch(new PRM_ParFormSubmissionBatch(env), 1)`, and asserts AC-MAX. Run weekly in QA. If any limit creeps above the threshold, alarm and triage before production deploy.

### 3.4 Memoization expansion

Add to `PRM_ParFormSubmissionBatch` stateful fields:

```apex
// Lookup caches that survive across chunks. Mirrors PRM_NetworkCreationBatch
// memoization pattern, expanded for PAR scale (50 PPL rows per submission means
// any per-row SOQL is fatal).
@TestVisible Map<String, Id>     taxonomyIdByCode      = new Map<String, Id>();
@TestVisible Map<String, Id>     recordTypeIdByDevName = new Map<String, Id>();
@TestVisible Map<String, Id>     featureConfigByName   = new Map<String, Id>();

// NEW for AC-MAX — needed because at 5×10 we look up the same parent records
// repeatedly while building per-location children.
@TestVisible Map<String, Id>     hfIdBySourceSystemId  = new Map<String, Id>();   // HealthcareFacility lookup
@TestVisible Map<String, Id>     accountIdByNpi        = new Map<String, Id>();   // Vendor / Practitioner Account by NPI
@TestVisible Map<String, Id>     addressIdByDigest     = new Map<String, Id>();   // Schema.Address by (line1, city, zip) hash
@TestVisible Map<String, Id>     locationIdByDigest    = new Map<String, Id>();   // Schema.Location by (addressId, npi)
```

---

## 4. US-PAR-03 (Pre-Submit Callout Phase) — Audit Verdict

### Verdict: **DOES NOT HOLD AS WRITTEN — RE-DESIGN REQUIRED**

The original story has the Apex orchestrator do:

```apex
for (Object raw : rawAddresses) {
    standardizeOne(rawMap);       // calls PRM_AddressValidationService.validateAddress() — ONE callout each
}
```

At max scale this is **50 sequential Precisely callouts**:

| Scenario | Latency budget | At 50 addresses |
|---|---|---|
| Precisely healthy (~500 ms each) | 50 × 500 ms = 25 s | UI blocked 25 s — fails the "< 3 s sync turn" goal |
| Precisely cold start (~1.5 s each) | 50 × 1.5 s = 75 s | UI blocked 75 s — approaches Salesforce's **120 s sync transaction ceiling**; one slow call away from a hard error |
| Precisely degraded (~3 s each) | 50 × 3 s = 150 s | **Exceeds the 120 s sync ceiling** → transaction killed by platform; the whole submission fails before any DML even starts |
| Sync transaction `callout` count | 100 max | 50 used → **OK on count, lethal on latency** |

The original story is **functionally correct** (callouts must finish before DML) but **operationally infeasible** at the maximum scale the form supports. Five corrections needed.

### 4.1 Correction A — Add a Bulk Precisely Endpoint Wrapper

**Required new component:** `PRM_AddressValidationService.validateAddressBulk(List<AddressShape> addresses)`.

```apex
/**
 * Bulk-validate up to 50 addresses in a single Precisely callout. Returns one
 * ValidationResult per input address (positional). REQUIRED by US-PAR-03 at
 * 5 groups × 10 locations.
 */
@AuraEnabled
public static List<ValidationResult> validateAddressBulk(List<AddressShape> addresses) { /* ... */ }
```

Implementation routes through a new IP `PRM_IPPreciselyAPICallBulk` that calls Precisely's batch endpoint (Precisely's `verify` API supports batch input of up to 100 addresses per request — confirm with Integrations team; if not, this method falls back to internal parallelism described in Correction C).

**Performance target:** one bulk call < 3 s. Drops the 5×10 latency from 25 s → ~3 s.

**Open question:** Does the `PRM_IPPreciselyAPICall` Integration Procedure support batch payload today, or only single-address? **Clarification #1 of this audit** — must be resolved before US-PAR-03 ships.

### 4.2 Correction B — Dedup Addresses Before Calling Precisely

Empirically, the user often fills the same address into Primary + Billing + Mailing across multiple locations, and group-level billing addresses are commonly copied to the locations under that group. **Deduplicate by `(line1, city, state, zip5)` before calling out.**

```apex
public static Map<String, ValidationResult> validateAddressesDedup(List<AddressShape> addresses) {
    Map<String, AddressShape> uniqueByKey = new Map<String, AddressShape>();
    for (AddressShape a : addresses) uniqueByKey.put(addrKey(a), a);
    Map<String, ValidationResult> resultByKey = ...;  // bulk call on uniqueByKey.values()
    return resultByKey;
}
```

**Effect:** 50 raw addresses typically reduce to **10–20 unique** addresses after dedup → already inside a comfortable single-bulk-call budget.

### 4.3 Correction C — HTTP Continuation for the OmniScript Step

Salesforce supports `Continuation` for long-running callouts up to 120 s in a synchronous OmniScript context (LWC Remote Action). Wrap the bulk call in a Continuation so the UI doesn't hold a real thread for the wait — the user sees a spinner / progress, and the OmniScript resumes when the response lands. This is the standard Salesforce pattern for "the sync turn must finish, but the callout takes a while".

Add to `PRM_PreSubmitCalloutOrchestrator`:

```apex
@AuraEnabled(continuation=true)
public static Continuation validateAddressesAsync(Map<String, Object> input) {
    Continuation con = new Continuation(60);   // 60s continuation budget
    con.continuationMethod = 'processPreciselyResponse';
    HttpRequest req = buildBulkPreciselyRequest(input);
    con.addHttpRequest(req);
    return con;
}

public static Map<String, Object> processPreciselyResponse(List<String> labels, Object state) {
    HttpResponse res = Continuation.getResponse(labels[0]);
    return parseBulkPreciselyResponse(res);
}
```

### 4.4 Correction D — Fail-Fast Latency Budget in the Pre-Callout IP

The pre-callout IP must enforce a **wall-clock budget**: if Precisely doesn't return within e.g. 15 s, abort the submit with a user-visible message ("Address validation is currently slow — please try again, or contact admin to bypass via PRM_SkipPrecisely toggle"). This protects users from staring at a 25–75 s spinner if Precisely is degraded.

```apex
// In PRM_PreSubmitCalloutOrchestrator.validateAddresses
Long startMs = DateTime.now().getTime();
// ... bulk call ...
Long elapsedMs = DateTime.now().getTime() - startMs;
if (elapsedMs > 15000) {
    PRM_ExceptionLogger.logException('PRM_PreSubmitCallout', 'SYNC', 'Warning',
        'Precisely latency ' + elapsedMs + 'ms exceeded 15s budget at 5x10 max scale',
        '', '', 0, '', '', 'Salesforce', 'Precisely', '');
}
```

### 4.5 Correction E — Parallelism via `@future(callout=true)` Fan-Out for Non-Critical Validations

NPI / Tax-Id pre-validation and CAQH lookup are **independent** of address standardization. Fire them in parallel from the IP:

```
PRM_PreSubmitCalloutPhase IP:
  ├─ Step 1 (in parallel via separate Remote Actions chained in IP):
  │    ├─ validateAddressesAsync (Continuation, bulk Precisely)
  │    ├─ validateNpiAsync       (Continuation, MuleSoft)
  │    └─ validateTaxIdAsync     (Continuation, MuleSoft)
  ├─ Step 2: Aggregate results (waits for all three to land via OmniScript Wait pattern)
  └─ Step 3: Pack into PreSubmitCalloutResult
```

OmniStudio doesn't natively fan out parallel IP calls, but it does support multiple "Remote Action" steps inside one IP that the platform executes in serial; the latency savings come from each individual step using Continuation, so the LWC thread isn't pinned. **Net effect: total perceived wall-clock = max(bulkPrecisely, npi, taxId) ≈ 3–4 s** instead of sum.

### 4.6 Updated AC for `US_PAR03_PreSubmitCalloutPhase.md`

**AC-MAX (NEW) — Bulk + dedup at 5 groups × 10 locations stays under 6 seconds.**

> **Given** the user submits a PAR form with the maximum payload (5 groups × 10 locations = up to 50 raw addresses, of which typically 10–20 are unique after dedup, plus 1 practitioner NPI + 1 Tax-Id + 1 CAQH ID),
> **When** the OmniScript invokes `PRM_PreSubmitCalloutPhase_Procedure_1`,
> **Then** the user-perceived wall-clock from "click Submit" → "callout phase complete, batch enqueued" is **≤ 6 seconds at P50** and **≤ 15 seconds at P95**, the IP makes **exactly 1 bulk Precisely callout** (not 50 single-address calls), and `PreSubmitCalloutResult.standardizedAddresses` contains one entry per raw input address (deduped lookups expanded back to the original positions).

**AC-FAIL-FAST (NEW) — Fail-fast when Precisely is degraded.**

> **Given** Precisely is responding slowly (>15 s wall-clock for the bulk call),
> **When** the OmniScript invokes `PRM_PreSubmitCalloutPhase_Procedure_1`,
> **Then** the user sees a toast "Address validation is temporarily slow. Please retry, or ask an admin to enable PRM_SkipPrecisely.", the OmniScript blocks Submit, **no batch is enqueued**, and `PRM_ExceptionLog__c` records a Warning event with category `PRECISELY_SLOW` for monitoring.

### 4.7 Open clarification

> **Clarification audit-1:** Does Precisely's `verify` endpoint (or whatever endpoint `PRM_IPPreciselyAPICall` uses) support a batch payload of up to 50 addresses per HTTP call? **Owner:** Integrations team. **Blocker for US-PAR-03.**
> - If **yes**, Corrections A + B + C + D are sufficient.
> - If **no**, US-PAR-03 must additionally implement **client-side fan-out via N `@future(callout=true)` methods**, each handling a slice of ~10 dedup'd addresses, with the OmniScript polling for completion before navigating to the batch enqueue step (effectively turns the pre-callout into a short async phase).

---

## 5. US-PAR-02 (Platform Event Logging) — Audit Verdict

### Verdict: **HOLDS — ADD ONE AC**

Platform event publishing scales to ~10,000 events / hr / org. A single PAR submission publishes at most one event per failed sub-step (≤ 15 events at max scale). 100 concurrent submissions = ~1,500 events, well under the org limit.

**One concern at max scale:** an `addError()` trigger on `HealthcareFacility` (55 records) or `ContactPointAddress` (150 records) could, in the worst case, publish one PE per failing record → 150 events from one trigger invocation. This is still under any org limit but should be batched at the `Trigger.new` level (one PE per *batch of failing rows*, not per row).

### 5.1 NEW AC for `US_PAR02_ExceptionLogging_PlatformEvent.md`

**AC-MAX (NEW) — One submission publishes ≤ 20 platform events total.**

> **Given** a PAR submission with the maximum payload (5 groups × 10 locations) experiences a failure inside `processSubmission()`,
> **When** the batch's outer `catch` block fires and the trigger handlers' bulk `addError()` paths run,
> **Then** the total number of `PRM_ExceptionLogEvent__e` events published per submission is **≤ 20** (one per failed object type / one per outer-catch / one per trigger), not one-per-failing-record. (At 150 CPA rows or 55 HF rows, publishing one event per row would inflate the noise without adding signal — the structured error message in a single event must carry the list of failed row identifiers.)

### 5.2 Implementation change to `PRM_ExceptionLogger.logExceptionViaEvent`

```apex
// At max scale we expect 50 PPL rows, 150 CPA rows, 60 Address rows. One PE
// per failing record would be ~200 events for a single failure cascade. Use
// one PE per (object type, error class) and pack the row Ids into the event
// payload's PRM_RecordId__c field as a comma-separated list (max 18 × 50 = 900 chars).
public static void logBulkExceptionViaEvent(String process, String sObjectName,
    Set<Id> failedRecordIds, Exception ex, Id individualAppId) { /* ... */ }
```

---

## 6. US-PAR-04 (Trigger Idempotency) — Audit Verdict

### Verdict: **HOLDS STRUCTURALLY — REQUIRES EXPLICIT BULK-SAFETY AC**

The three triggers being refactored — `populateSourceSystemIdentifier` (HealthcareProvider), `setPracFacilityIdentifier` (HealthcarePractitionerFacility), `setAccIdentifier` (Account) — already accept `List<...>` in their signatures (confirmed via inspection). The risk is that the idempotency check the story adds (SOQL for existing identifier-by-computed-key) is naively coded **inside the loop**, which would be **50 SOQLs for the 50 PPL rows** in one trigger invocation — burning half the per-transaction SOQL budget.

### 6.1 NEW AC for `US_PAR04_TriggerIdempotency.md`

**AC-MAX-BULK (NEW) — Idempotency check uses one SOQL per trigger invocation regardless of `Trigger.new.size()`.**

> **Given** a batch inserts up to 50 `HealthcarePractitionerFacility`, 55 `HealthcareFacility`, 6 `HealthcareProvider`, or 6 `Account` records in a single DML statement,
> **When** the corresponding trigger fires with that bulk `Trigger.new`,
> **Then** the trigger's idempotency check executes **at most one SOQL query** (selecting the existing identifier table by the computed-key `IN :keys` set), iterates `Trigger.new` once to compare against the in-memory map, and calls `addError()` only on the duplicates — `Limits.getQueries()` increases by **exactly 1** for any `Trigger.new.size()` ∈ [1, 200].

### 6.2 Implementation pattern (mandatory in `US_PAR04`)

```apex
public static void populateSourceSystemIdentifier(List<HealthcareProvider> newRecords) {
    // 1. Collect computed keys for all records in Trigger.new
    Set<String> computedKeys = new Set<String>();
    Map<String, HealthcareProvider> recordByKey = new Map<String, HealthcareProvider>();
    for (HealthcareProvider r : newRecords) {
        String key = computeSourceSystemKey(r);   // pure function
        computedKeys.add(key);
        recordByKey.put(key, r);
    }

    // 2. ONE SOQL — finds any pre-existing identifier rows for ALL of Trigger.new
    Map<String, Id> existingByKey = new Map<String, Id>();
    for (PRM_IdentifierHCProvider__c idRow : [
        SELECT Id, ComputedKey__c
        FROM PRM_IdentifierHCProvider__c
        WHERE ComputedKey__c IN :computedKeys
    ]) {
        existingByKey.put(idRow.ComputedKey__c, idRow.Id);
    }

    // 3. addError() — purely in-memory, no SOQL
    for (String key : recordByKey.keySet()) {
        if (existingByKey.containsKey(key)) {
            recordByKey.get(key).addError(
                'PRM_HCPROVIDER_EXISTS::' + existingByKey.get(key) + '::HCProvider with computed key '
                + key + ' already exists. Reuse existing record instead of inserting a duplicate.'
            );
        }
    }
}
```

### 6.3 Unit test (mandatory)

```apex
@isTest
static void triggerIdempotency_holdsAt50PPLrows() {
    Test.startTest();
    Integer queriesBefore = Limits.getQueries();
    insert TestDataFactory.buildPPLs(50);  // 50 HealthcarePractitionerFacility in one DML
    Integer queriesAfter = Limits.getQueries();
    Test.stopTest();
    // setPracFacilityIdentifier should use ONE SOQL regardless of size
    // (Allow ±1 for unrelated framework SOQLs introduced by other handlers.)
    System.assert(queriesAfter - queriesBefore <= 3,
        'setPracFacilityIdentifier must be bulk-safe; observed ' + (queriesAfter - queriesBefore) + ' queries for 50 PPL rows');
}
```

---

## 7. US-PAR-05 (Failed Record Staging UX) — Audit Verdict

### Verdict: **HOLDS — ADD TWO AUTO-RETRY CONSTRAINTS**

The analyst-facing manual retry path (Quick Action → re-enqueue envelope from staging row) works identically at 1 group or 5×10 — same JSON envelope, same `PRM_ParFormSubmissionHelper.enqueue()`. **Manual retry: no scale concern.**

The **auto-retry** path (optional scheduled job) DOES have a scale concern: if 200 PAR submissions failed last night and the scheduled job picks them all up, that's 200 separate `Database.executeBatch(...)` calls. The org allows max 5 concurrent batch jobs and 100 holding-state batches; we'd exhaust that immediately.

### 7.1 NEW AC for `US_PAR05_FailedRecordStaging_AnalystRetryUX.md`

**AC-RETRY-THROTTLE (NEW) — Auto-retry caps concurrent batch enqueues.**

> **Given** N `PRM_FailedRecordStaging__c` rows with `Status__c = 'Awaiting Retry'` exist when the scheduled auto-retry job runs,
> **When** the job kicks off,
> **Then** it enqueues at most **3 batches in parallel** (well under the org's 5-batch concurrent limit), monitors via `[SELECT Id, Status FROM AsyncApexJob WHERE JobType='BatchApex' AND Status IN ('Queued','Processing','Preparing')]`, and proceeds to the next staging row only when there's room in the queue. The job runs to completion (drains all `Awaiting Retry` rows) or hands off remaining rows to the next scheduled invocation if the schedule window closes.

**AC-RETRY-IDEMPOTENT (NEW) — Auto-retry won't re-enqueue an in-flight retry.**

> **Given** a staging row was picked up by a previous auto-retry invocation 30 seconds ago and the batch it spawned is still in `Status='Processing'`,
> **When** the scheduled auto-retry job runs again,
> **Then** the staging row is **skipped** (recognized via `PRM_RetryJobId__c` lookup → `AsyncApexJob.Status` check) and not re-enqueued. The "in-flight retry" guard prevents double-write of all 490 records when the second job overlaps with the first.

### 7.2 Implementation patterns

```apex
public class PRM_ParFormAutoRetryScheduled implements Schedulable {
    private static final Integer MAX_PARALLEL_BATCHES = 3;

    public void execute(SchedulableContext sc) {
        Integer inFlightBatches = [
            SELECT COUNT() FROM AsyncApexJob
            WHERE ApexClass.Name = 'PRM_ParFormSubmissionBatch'
              AND Status IN ('Queued', 'Processing', 'Preparing', 'Holding')
        ];
        if (inFlightBatches >= MAX_PARALLEL_BATCHES) {
            // Wait for next schedule window — don't pile on
            return;
        }

        Integer slotsAvailable = MAX_PARALLEL_BATCHES - inFlightBatches;
        List<PRM_FailedRecordStaging__c> awaiting = [
            SELECT Id, PRM_EnvelopePayload__c, PRM_IndividualApplication__c, PRM_RetryJobId__c
            FROM PRM_FailedRecordStaging__c
            WHERE PRM_Status__c = 'Awaiting Retry'
              AND PRM_OriginatingProcess__c = 'PAR_FORM_SUBMIT'
              AND (PRM_RetryJobId__c = NULL OR PRM_RetryJobId__r.Status IN ('Completed','Failed','Aborted'))
            ORDER BY CreatedDate ASC
            LIMIT :slotsAvailable
        ];

        for (PRM_FailedRecordStaging__c row : awaiting) {
            PRM_ParFormSubmissionEnvelope env = (PRM_ParFormSubmissionEnvelope)
                JSON.deserialize(row.PRM_EnvelopePayload__c, PRM_ParFormSubmissionEnvelope.class);
            Id jobId = PRM_ParFormSubmissionHelper.enqueue(env);
            row.PRM_RetryJobId__c = jobId;
            row.PRM_Status__c = 'Retry In Flight';
        }
        update awaiting;
    }
}
```

---

## 8. Summary Table — Required Edits

| User Story | Verdict | Required edits | Effort delta |
|---|---|---|---|
| `US_PAR01_BatchRefactor.md` | **HOLDS** | Update sizing claim (line 178), add AC-MAX + max-scale load test, expand memoization fields | +0.5 day |
| `US_PAR02_ExceptionLogging_PlatformEvent.md` | **HOLDS** | Add AC-MAX (≤20 events), add `logBulkExceptionViaEvent()` method | +0.5 day |
| `US_PAR03_PreSubmitCalloutPhase.md` | **REQUIRES RE-DESIGN** | Add bulk endpoint wrapper, dedup, HTTP Continuation, fail-fast budget, parallel fan-out; add AC-MAX + AC-FAIL-FAST; resolve Clarification audit-1 first | **+3 days + 1 dependency on Integrations team** |
| `US_PAR04_TriggerIdempotency.md` | **HOLDS** | Add AC-MAX-BULK (one SOQL per trigger), add bulk-safety unit test pattern | +0.5 day |
| `US_PAR05_FailedRecordStaging_AnalystRetryUX.md` | **HOLDS** | Add AC-RETRY-THROTTLE, AC-RETRY-IDEMPOTENT, throttling implementation | +1 day |

**Total effort delta:** ~5–6 person-days, concentrated in US-PAR-03.

**New blocker:** Clarification audit-1 (Precisely bulk endpoint support). Must be answered before US-PAR-03 starts development.

---

## 9. Cross-Story Invariants (NEW — to add to the Roadmap)

These are invariants the audit identified that span multiple stories. Add them to `00_Overview_PARForm_BatchRefactor_Roadmap.md`:

1. **Per-submission entity ceiling: 500 rows / 15 object types.** Any future feature that adds a new repeatable to the PAR form (e.g., "10 specialties per location" or "6 groups") must re-run this audit. Document the formula in the roadmap so future PRs explicitly recompute.

2. **`chunkSize = 1` is mandatory for `PRM_ParFormSubmissionBatch`.** Bundling N submissions per chunk multiplies 500 rows by N and breaks the SOQL/DML headroom math.

3. **Zero callouts inside `execute()`.** Unit test `execute_makesNoCallouts` (US-PAR-03 §F) is the permanent guardrail. Any future contributor who breaks it will be caught at CI.

4. **One SOQL per trigger per `Trigger.new` invocation, regardless of size.** AC-MAX-BULK in US-PAR-04 is the contract.

5. **Auto-retry concurrency capped at 3 parallel batches.** Prevents the org's 5-batch slot from being exhausted by a backlog flush.

---

## 10. Evidence Trail

- OmniScript v111 active, line 5: `<isActive>true</isActive>` → confirmed via `rg '<isActive>' force-app/main/default/omniScripts/PRM_PractitionerParticipationForm_English_111.os-meta.xml`
- OmniScript v54 active (address sub-form) — same method
- `GroupInformation.repeatLimit = 4` → line 2608 of v111
- `AdditionalAddress.repeatLimit = 9` → line 2003 of v54
- `AddLicenseBlock.repeatLimit = 3` → line 3202 of v111
- `prmMultiSelect.maxselection` defaults to `optionData.length` → lines 25, 443-444 of `prmMultiSelect.js`
- `PRM_CreatePractitionerAddressRecords_Procedure_41` action tally: 44 DataRaptor Post Action + 19 DataRaptor Transform + 13 List Merge + 13 Set Values + 5 Conditional + 4 DataRaptor Extract + 2 Loop Block + 1 PRM Apex (= 101 actions) — confirms the existing IP iterates per (group, location) pair
- `PRM_AddressValidationService.validateAddress()` is single-address-only → no bulk call exists today (Clarification audit-1 needed)
- `PRM_NetworkCreationHelper.cls` line 42: existing precedent uses `chunkSize = 50` — but that's for *lightweight* network rows, not heavy PAR submissions; PAR must stay at `chunkSize = 1`
