# USER STORY US-PAR-03: PAR Form — Pre-Submit Callout Phase (Address Standardization Before Any DML)

**Persona:** Salesforce Developer, Credentialing Intake Specialist
**Priority:** P0 — hard prerequisite for US-PAR-01; explains the historical `chainOnStep=false` design choice we are about to overturn
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_PractitionerParticipationForm_English` v111 → v112 — Final Submit step (re-ordered)
**Integration Procedures (impacted):**
- NEW `PRM_PreSubmitCalloutPhase_Procedure_1` — gathers all callout-bearing work into one IP that runs **before** any DML happens
- `PRM_CreatePractitionerAddressRecords` v41 — split: callout half moves to the new IP, DML half stays in `PRM_ParFormSubmissionBatch` (US-PAR-01)
- `PRM_ValidateCAQH` (or whatever calls it from PAR) — confirm where it runs in the pipeline; ensure it is in the pre-callout phase, not the batch
- (deactivated by US-PAR-01) `PRM_CreatePractitionerAddressRecords` — kept active during US-PAR-01's 30-day backstop, then deleted

**Apex (impacted):**
- `PRM_AddressValidationService.cls` — used today by `validateAddress()` Precisely wrapper; no body change, just ensure it remains callable from an IP step that has NO prior DML in the transaction
- `PRM_CallOutController` / `PRM_BulkCalloutController` (per `PRM_NetworkCreation_BatchImplementation_Guide.md` line 200+) — confirm reuse here
- NEW `PRM_PreSubmitCalloutResult.cls` — POJO that the new IP packs and the next step (the enqueue helper from US-PAR-01) reads
- `PRM_OmniProcessUtils.cls` — add route `runPreSubmitCallouts`

**Relevant requirements:** `00_Overview_PARForm_BatchRefactor_Roadmap.md`, `US-PAR-01`, `PRM_NetworkCreation_BatchImplementation_Guide.md` §"Callout Handling", Salesforce platform guidance: "You have uncommitted work pending" exception (1,007 occurrences in `PRM_ValidateCAQH` / 30 d as of 2026-05-27)

---

## Story

**As a** Salesforce Developer designing the new `PRM_ParFormSubmissionBatch`,
**I want** every external callout that the PAR form depends on (Precisely address standardization, MuleSoft NPI / Tax-Id pre-validation, CAQH lookup, USPS verify) to complete **before** the batch enqueues — i.e., during the synchronous OmniScript turn, before any DML happens in the transaction,
**So that** the batch is **pure DML** (no callouts) and cannot ever hit the Salesforce platform's "You have uncommitted work pending" error that the seven sub-IPs were structurally designed to avoid via the (now-problematic) `chainOnStep=false` pattern.

**Why it matters:** When we investigated why the seven PAR sub-IPs were configured with `chainOnStep=false` (which is what causes the partial-data accumulation), we found the rationale was **structural, not accidental** — sub-IP 5 (`PRM_CreatePractitionerAddressRecords`) calls Precisely. If we simply flipped `chainOnStep=true`, the sub-IP chain would do DML in step 2, then a callout in step 5 → trip the "uncommitted work pending" error on every submission. The org-wide evidence: 1,007 occurrences of this error in `PRM_ValidateCAQH` over 30 days. **Naive fix would re-introduce this in a worse form.** This story is the corrective: pull callouts forward into a pre-DML phase, so the batch can do all its DML in one transaction without ever needing to call out.

---

## Scope

| Layer | Component | Change |
|---|---|---|
| OmniScript | `PRM_PractitionerParticipationForm_English` v111 → v112 | Re-order Final Submit step: (a) call new `PRM_PreSubmitCalloutPhase`, (b) merge results into form data, (c) call `PRM_CreateParFormRecordsContainer` v2 |
| New IP | `PRM_PreSubmitCalloutPhase_Procedure_1` | NEW. Wraps Precisely + MuleSoft + any other callout consumers. All callouts run here. No DML. |
| New Apex POJO | `PRM_PreSubmitCalloutResult.cls` | Output of the pre-callout phase: standardized addresses, validated NPI metadata, validated TaxId metadata, CAQH cache hits, success/error per category |
| Existing Apex | `PRM_AddressValidationService.cls` | No change — already exposes `validateAddress()`. Reuse from the new IP. |
| Existing IPs | `PRM_CreatePractitionerAddressRecords` | After US-PAR-01 ships, deactivated. **During US-PAR-03 (which ships first)**, the Precisely call inside it is moved to the pre-callout phase; the DML half stays. |
| Routes | `PRM_OmniProcessUtils.cls` | Add `if (methodName == 'runPreSubmitCallouts') { return PRM_PreSubmitCalloutOrchestrator.runPreSubmitCallouts(inputMap, outMap); }` if we choose Apex orchestration over IP orchestration (see Clarification #2) |

---

## Current State (verified)

### `PRM_CreatePractitionerAddressRecords_Procedure_41` (the address sub-IP)

Per `PAR_Form_PartialDataRollback_Investigation_FixPlan.md` §3.2 — this IP calls Precisely via `PRM_AddressValidationService.validateAddress()` and **also** does DML to create `Schema.Address` + `ContactPointAddress` + bridges. It is the only sub-IP that mixes callouts with DML. The seven sub-IPs are all `chainOnStep=false` because of this one.

### `PRM_ValidateCAQH` (the CAQH lookup)

Per the runbook (1,007 "uncommitted work pending" exceptions in 30 days), this IP today calls CAQH for credentialing data. It is invoked from the credentialing-flow side, not directly from the PAR form, but it shares the same platform constraint and is a useful reference for what "callout before DML" discipline looks like in this codebase.

### `PRM_AddressValidationService.cls`

Exposes `validateAddress(Address address)` returning a standardized address payload. Honors a `isPreciselySkipped()` toggle so testing environments can bypass the real callout. **No DML inside this method** — it is callout-only. Safe to invoke from a pre-DML phase.

### `PRM_OmniProcessUtils.cls`

The single integration point for OmniStudio remote actions. Already routes `enqueueNetworkCreation`. Will route `runPreSubmitCallouts` (this story) and `enqueueParFormSubmission` (US-PAR-01).

### Salesforce platform constraint we are working around

> Documented Salesforce platform behaviour: "You have uncommitted work pending. Please commit or rollback before calling out." Any Apex DML statement before an HTTP callout in the same transaction triggers this exception. The platform allows callouts THEN DML, never DML THEN callouts.

Source: Salesforce Apex Developer Guide; mirrored in `PRM_NetworkCreation_BatchImplementation_Guide.md` §"Callout Handling".

---

## Proposed Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ OmniScript: PRM_PractitionerParticipationForm_English v112                   │
│                                                                              │
│ Step "ReviewBeforeSubmit"                                                    │
│   ↓                                                                          │
│ Step "PreSubmitCallouts"  (NEW)                                              │
│   └── IP Action: PRM_PreSubmitCalloutPhase_Procedure_1                       │
│         (rollbackOnError=false, chainOnStep=true)                            │
│         •  No DML, callouts only                                             │
│         •  Output: { standardizedAddresses: [...],                           │
│                       validatedNpiInfo: {...},                               │
│                       validatedTaxIdInfo: {...},                             │
│                       caqhCacheHits: [...],                                  │
│                       success: true/false,                                   │
│                       errorsByCategory: {...} }                              │
│   ↓ (the OmniScript merges this back into the form context as               │
│      PreSubmitCalloutResult)                                                 │
│                                                                              │
│ Step "ShowCalloutResult"                                                     │
│   • If PreSubmitCalloutResult.success == false:                              │
│       Surface error to user, BLOCK Submit (no enqueue), let them correct     │
│         the address / NPI / TaxId in the form and retry                      │
│   • Else continue.                                                           │
│                                                                              │
│ Step "Submit"                                                                │
│   └── IP Action: PRM_CreateParFormRecordsContainer v2 (from US-PAR-01)       │
│         additionalInput merges the original form data AND                    │
│         PreSubmitCalloutResult.standardizedAddresses (replacing the         │
│         user's raw addresses with USPS-canonicalized ones)                   │
│   ↓                                                                          │
│   PRM_OmniProcessUtils.callMethod('enqueueParFormSubmission', ...)           │
│         → PRM_ParFormSubmissionHelper.enqueue(...)                           │
│         → Database.executeBatch(new PRM_ParFormSubmissionBatch(envelope))    │
│         → returns {jobId, success: true, caseManagerId}                      │
│                                                                              │
│ Step "ShowToast + Navigate" (from US-PAR-01)                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       ↓
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PRM_ParFormSubmissionBatch.execute() — PURE DML                              │
│                                                                              │
│ Per submission row:                                                          │
│   row.standardizedAddresses is already populated (from pre-callout phase)    │
│   row.validatedNpiInfo is already populated                                  │
│   row.validatedTaxIdInfo is already populated                                │
│   ...                                                                        │
│                                                                              │
│ The batch never makes an HTTP callout. Never. Tested by:                     │
│   - Unit tests: mock HttpCalloutMock that throws if called                   │
│   - Apex check: assert Limits.getCallouts() == 0 at the end of execute()    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why a NEW IP and not a step inside the OmniScript directly

OmniScript steps that call external services do support `Type=HTTP Action`, but the org's convention is to wrap every external system call in an IP for testability, mocking, and centralized error handling. Using `PRM_PreSubmitCalloutPhase_Procedure_1` lets us reuse `PRM_AddressValidationService.validateAddress()` and any future Apex orchestrator without changing the OmniScript.

### Why "BLOCK Submit on callout failure" instead of "let the batch handle it"

If Precisely is down, we **don't want** to enqueue a batch with un-standardized addresses — the batch would either fail later (wasting an enqueue cycle and confusing the user) or create non-canonical data that fails downstream USPS verification. Better to fail-fast in the UI turn so the user sees the error, retries, or contacts admin. Matches the "let the user act on the error" UX principle.

---

## Technical Section (For Developers)

### A. `PRM_PreSubmitCalloutPhase_Procedure_1` — IP design

| Seq | Element | Type | Notes |
|---:|---|---|---|
| 1.0 | `ExtractInputs` | SetValues | Pull `npi`, `taxId`, `practitionerName`, `rawAddresses[]`, `vendorRawAddresses[]` from `inputMap`. |
| 2.0 | `ValidateAddresses` | Remote Action | `remoteClass=PRM_OmniProcessUtils`, `methodName=runPreSubmitCallouts.addresses`. Calls Apex orchestrator that loops over rawAddresses and calls `PRM_AddressValidationService.validateAddress()` for each. Returns standardized list or per-address failure. |
| 3.0 | `ValidateNPI` (conditional) | Remote Action | Only if NPI not already verified via earlier OmniScript step. Calls MuleSoft / PAR. |
| 4.0 | `ValidateTaxId` (conditional) | Remote Action | Only if Tax-Id not already verified. |
| 5.0 | `WarmCAQHCache` (optional) | Remote Action | Pre-fetches CAQH data so the batch's per-row downstream steps can read from cache. |
| 6.0 | `AggregateResult` | SetValues | Packs all of the above into `PreSubmitCalloutResult` with `success` boolean and `errorsByCategory` map. |
| 7.0 | `Response` | Response Action | Returns `PreSubmitCalloutResult` to the OmniScript. |

`propertySetConfig`:
- `rollbackOnError = false` (no DML in this IP, so no rollback to do)
- `chainOnStep = true`
- No queueable
- Governor budget: standard chainable limits (50 SOQL / 2000 CPU is plenty; the IP is dominated by HTTP latency)

### B. `PRM_PreSubmitCalloutResult.cls` (NEW Apex POJO)

```apex
public class PRM_PreSubmitCalloutResult {
    public Boolean success;
    public List<StandardizedAddress> standardizedAddresses;
    public NpiInfo validatedNpiInfo;
    public TaxIdInfo validatedTaxIdInfo;
    public List<CaqhCacheEntry> caqhCacheHits;
    public Map<String, String> errorsByCategory;   // 'address' / 'npi' / 'taxId' / 'caqh' → message

    public class StandardizedAddress {
        public String inputKey;     // matches a key in the original form payload
        public String line1;
        public String line2;
        public String city;
        public String state;
        public String stateCounty;
        public String postalCode;
        public String postalCodeWithZip4;
        public String country;
        public Boolean uspsVerified;
        public String addressType;  // residential / business
    }
    public class NpiInfo {
        public String npi;
        public Boolean exists;
        public Id existingHcNpiId;
        public Id existingAccountId;
        public String practitionerType;  // person / vendor
    }
    public class TaxIdInfo {
        public String taxId;
        public Boolean exists;
        public Id existingVendorAccountId;
    }
    public class CaqhCacheEntry {
        public String npi;
        public String credentialingStatusFromCaqh;
        public Datetime lastUpdated;
    }
}
```

### C. `PRM_OmniProcessUtils.cls` route addition

```apex
if (methodName == 'runPreSubmitCallouts') {
    return PRM_PreSubmitCalloutOrchestrator.runPreSubmitCallouts(inputMap, outMap);
}
```

### D. `PRM_PreSubmitCalloutOrchestrator.cls` (NEW)

The Apex side of the pre-callout phase. Doesn't have to be one method — can be `runPreSubmitCallouts`, `validateAddresses`, `validateNpi`, etc. each invoked separately by the IP steps for finer-grained error handling. Recommendation: one entry per IP step (matches the `PRM_OmniProcessUtils.callMethod` pattern).

```apex
public with sharing class PRM_PreSubmitCalloutOrchestrator {

    public static Map<String, Object> validateAddresses(Map<String, Object> input, Map<String, Object> outMap) {
        Map<String, Object> result = new Map<String, Object>{
            'success' => true, 'standardizedAddresses' => new List<Object>(),
            'errors' => new Map<String, String>()
        };
        try {
            List<Object> rawAddresses = (List<Object>) input.get('rawAddresses');
            if (rawAddresses == null || rawAddresses.isEmpty()) {
                if (outMap != null) outMap.putAll(result);
                return result;
            }
            List<PRM_PreSubmitCalloutResult.StandardizedAddress> out = new List<PRM_PreSubmitCalloutResult.StandardizedAddress>();
            for (Object raw : rawAddresses) {
                Map<String, Object> rawMap = (Map<String, Object>) raw;
                String key = (String) rawMap.get('inputKey');
                try {
                    PRM_PreSubmitCalloutResult.StandardizedAddress sa = standardizeOne(rawMap);
                    out.add(sa);
                } catch (Exception addrEx) {
                    ((Map<String, String>) result.get('errors')).put(key, addrEx.getMessage());
                    result.put('success', false);
                }
            }
            result.put('standardizedAddresses', out);
        } catch (Exception e) {
            result.put('success', false);
            result.put('errors', new Map<String, String>{ 'global' => e.getMessage() });
            PRM_ExceptionLogger.logException(
                'PRM_PreSubmitCalloutOrchestrator.validateAddresses',
                'SYNC', 'Error', e.getStackTraceString(), e.getMessage(),
                e.getTypeName(), e.getLineNumber(), '', '',
                'Salesforce', 'Precisely', JSON.serialize(input).abbreviate(30000));
        }
        if (outMap != null) outMap.putAll(result);
        return result;
    }

    private static PRM_PreSubmitCalloutResult.StandardizedAddress standardizeOne(Map<String, Object> raw) {
        // Build a Schema.Address from the input map
        // Call PRM_AddressValidationService.validateAddress(addr)
        // Translate the result back into StandardizedAddress POJO
        // Throw if Precisely returns an unrecoverable error
        // ...
        return new PRM_PreSubmitCalloutResult.StandardizedAddress();
    }

    // Similar methods for validateNpi, validateTaxId, warmCaqhCache.
}
```

### E. OmniScript `PRM_PractitionerParticipationForm_English` v112 changes

| New element | Type | Where |
|---|---|---|
| `PreSubmitCallouts` | IP Action invoking `PRM_PreSubmitCalloutPhase_Procedure_1` | Immediately before the existing "Final Submit" step. |
| `ShowCalloutResult` | Show Toast (conditional) + Block Navigation | Shows error toast and blocks Submit if `PreSubmitCalloutResult.success==false`. |
| Existing "Final Submit" | (no structural change in this story — US-PAR-01 changes it) | Reads `PreSubmitCalloutResult.standardizedAddresses` from form context and passes them in `additionalInput.locationsToUpsert` (replacing the raw user input). |

### F. Apex unit-test mandate — assert no callouts in the batch

In `PRM_ParFormSubmissionBatchTest.cls` (defined by US-PAR-01), add an assertion:

```apex
@isTest
static void execute_makesNoCallouts() {
    Test.setMock(HttpCalloutMock.class, new ThrowOnAnyCallout());
    // Setup envelope with standardizedAddresses already populated
    PRM_ParFormSubmissionEnvelope env = TestDataFactory.buildEnvelopeWithStandardizedAddresses();
    Integer calloutsBefore = Limits.getCallouts();
    Test.startTest();
        Database.executeBatch(new PRM_ParFormSubmissionBatch(env), 1);
    Test.stopTest();
    System.assertEquals(calloutsBefore, Limits.getCallouts(),
        'PRM_ParFormSubmissionBatch must NOT make HTTP callouts (US-PAR-03 invariant)');
}

private class ThrowOnAnyCallout implements HttpCalloutMock {
    public HttpResponse respond(HttpRequest req) {
        throw new AssertionException('Batch made an unexpected HTTP callout: ' + req.getEndpoint());
    }
}
```

This assertion is a permanent guardrail — any future developer who tries to add a callout to the batch will get a CI failure.

### G. Bulk Precisely callout (REQUIRED for the maximum-scale form)

The OmniScript supports up to **5 groups × 10 locations = 50 raw addresses per submission** (see `US_PAR_ScaleAudit_5Groups_10Locations.md` for the metadata evidence). The original story used a naive `for (raw : rawAddresses) { validateAddress(raw); }` loop. At 50 addresses × ~500 ms typical Precisely latency, that's **~25 s of UI block** — failing AC7's < 2 s budget at P95 and AC-MAX's < 6 s P50 budget, and at P99 (Precisely cold-start ~1.5 s each) it can hit **~75 s**, approaching the 120 s sync transaction ceiling. The serial approach **is not viable at max scale**.

#### G.1 New bulk wrapper on `PRM_AddressValidationService`

```apex
/**
 * Bulk-validate up to N addresses in one or more Precisely calls. Returns one
 * ValidationResult per input address (positional, same order as input).
 *
 * Implementation:
 *   1. Dedupe by digest(line1, city, state, zip5) — typically reduces 50 raw → 10-20 unique.
 *   2. Call PRM_IPPreciselyAPICallBulk (NEW IP, see §G.2) once per ≤25 unique addresses.
 *      If Precisely's batch endpoint cap is 25, two calls cover the 50-address max.
 *   3. Expand the per-digest result back to the per-input-position result map.
 *
 * REQUIRED by AC-MAX. Replaces the per-address loop that would burn 25-75 s.
 */
@AuraEnabled
public static List<ValidationResult> validateAddressesBulk(List<AddressShape> addresses) {
    if (addresses == null || addresses.isEmpty()) return new List<ValidationResult>();

    // Step 1: dedupe
    Map<String, Integer> firstIndexByDigest = new Map<String, Integer>();
    Map<String, AddressShape> uniqueByDigest = new Map<String, AddressShape>();
    for (Integer i = 0; i < addresses.size(); i++) {
        String d = digest(addresses[i]);
        if (!uniqueByDigest.containsKey(d)) {
            uniqueByDigest.put(d, addresses[i]);
            firstIndexByDigest.put(d, i);
        }
    }

    // Step 2: bulk callout in slices (one or two HTTP calls for the 50-address max)
    Map<String, ValidationResult> resultByDigest = new Map<String, ValidationResult>();
    List<AddressShape> uniqueAddrs = new List<AddressShape>(uniqueByDigest.values());
    Integer sliceSize = 25;   // tune per Precisely contract
    for (Integer start = 0; start < uniqueAddrs.size(); start += sliceSize) {
        Integer endIdx = Math.min(start + sliceSize, uniqueAddrs.size());
        List<AddressShape> slice = new List<AddressShape>();
        for (Integer i = start; i < endIdx; i++) slice.add(uniqueAddrs[i]);
        Map<String, ValidationResult> sliceResults = callPreciselyBulkIP(slice);
        resultByDigest.putAll(sliceResults);
    }

    // Step 3: expand to positional output
    List<ValidationResult> out = new List<ValidationResult>();
    for (AddressShape a : addresses) {
        ValidationResult vr = resultByDigest.get(digest(a));
        out.add(vr != null ? vr : buildPassthrough(a));
    }
    return out;
}

private static String digest(AddressShape a) {
    return String.join(new List<String>{
        (a.addressLine1 ?? '').toUpperCase().trim(),
        (a.city ?? '').toUpperCase().trim(),
        (a.state ?? '').toUpperCase().trim(),
        (a.zip ?? '').substring(0, Math.min(5, (a.zip ?? '').length()))
    }, '|');
}
```

#### G.2 New Integration Procedure: `PRM_IPPreciselyAPICallBulk`

A copy of `PRM_IPPreciselyAPICall` whose HTTP Action sends the batch payload format that Precisely's `verify` endpoint accepts. Owner of the IP design: same team that maintains `PRM_IPPreciselyAPICall`. **Blocked by Clarification audit-1 (does Precisely's API support batch input?).**

#### G.3 Wall-clock fail-fast guard

Inside `PRM_PreSubmitCalloutOrchestrator.validateAddresses()`:

```apex
Long startMs = DateTime.now().getTime();
List<ValidationResult> results = PRM_AddressValidationService.validateAddressesBulk(addresses);
Long elapsedMs = DateTime.now().getTime() - startMs;

if (elapsedMs > 15000) {
    // AC-FAIL-FAST: budget exceeded — block submit, log warning, surface toast.
    result.put('success', false);
    result.put('errors', new Map<String, String>{
        'global' => 'Address validation is temporarily slow. Please retry in a moment, '
                  + 'or contact your administrator to enable the PRM_SkipPrecisely toggle.'
    });
    PRM_ExceptionLogger.logException(
        'PRM_PreSubmitCalloutOrchestrator.validateAddresses', 'SYNC', 'Warning',
        'Precisely bulk callout took ' + elapsedMs + 'ms (exceeds 15s budget at max scale)',
        '', '', 0, 'PRECISELY_SLOW', '', 'Salesforce', 'Precisely', '');
}
```

#### G.4 Fallback if Precisely batch endpoint is unavailable

If Clarification audit-1 reveals that Precisely's API does **not** support a batch endpoint, fall back to parallel single-address callouts via `@future(callout=true)` fan-out:

```apex
public static Id validateAddressesAsync(List<AddressShape> addresses) {
    // Slice into 5 groups of ~10 unique addresses each, fire each slice in a separate @future.
    // Persist correlation key on PRM_ParFormSubmissionEnvelope. OmniScript polls a Remote Action
    // (every 1.5s) for completion. ~10 callouts x 500ms in 5 parallel future contexts = ~2.5s wall clock.
    // ...
}
```

This is a back-up; do **not** implement unless Clarification audit-1 forces it.

---

## Acceptance Criteria

**AC1 — Callouts run before any DML.**
**Given** an analyst clicks Submit on the PAR form,
**When** the OmniScript invokes `PRM_PreSubmitCalloutPhase_Procedure_1` (the new pre-DML IP),
**Then** the IP completes all required HTTP callouts (Precisely for each raw address, MuleSoft for NPI / Tax-Id pre-validation, CAQH if applicable) and returns the standardized payload to the OmniScript **before** any record is inserted, updated, or deleted in the database.

**AC2 — Submit is blocked when callouts fail.**
**Given** Precisely returns an unrecoverable error for one of the form's addresses,
**When** the OmniScript receives `PreSubmitCalloutResult.success = false`,
**Then** the OmniScript displays a sticky error toast with the per-address error messages, does **NOT** invoke the Submit IP, and lets the user correct the address and retry.

**AC3 — Standardized addresses replace raw addresses in the batch payload.**
**Given** the pre-callout phase returns `standardizedAddresses[0] = { line1: "123 MAIN ST", city: "PHILADELPHIA", state: "PA", postalCodeWithZip4: "19103-1234", uspsVerified: true }` for the user's raw input "123 Main Street, Phila PA",
**When** the Submit IP enqueues the batch,
**Then** `PRM_ParFormSubmissionRow.addressScreen.addresses[0]` carries the standardized values (not the raw input), so the batch DML inserts USPS-canonical address records.

**AC4 — Batch makes zero HTTP callouts.**
**Given** the apex test `PRM_ParFormSubmissionBatchTest.execute_makesNoCallouts` (from §F),
**When** the batch executes,
**Then** `Limits.getCallouts() == 0` at the end of `execute()`, and the `ThrowOnAnyCallout` mock never fires.

**AC5 — Precisely-skipped sandboxes work.**
**Given** the org is configured with `PRM_AddressValidationService.isPreciselySkipped() == true` (typical for QA / UAT),
**When** the pre-callout phase runs,
**Then** Precisely is bypassed, addresses pass through with `uspsVerified=false` but otherwise canonicalized server-side (trim, case-normalize), and the batch proceeds normally.

**AC6 — Idempotent on re-submit.**
**Given** a user fixes a Precisely error and clicks Submit again within the same OmniScript session,
**When** the pre-callout phase runs a second time,
**Then** all callouts run again (no stale cache from the failed first attempt), and the second submission's batch receives fresh standardized addresses.

**AC7 — Performance budget for the pre-callout phase.**
**Given** a typical submission with 1 practitioner + 1 vendor + 3 practice locations + 3 addresses to standardize,
**When** the pre-callout phase runs,
**Then** it completes within **2 seconds (P95)** so the overall Submit→Navigate target of 3 seconds (from US-PAR-01 AC1) is still achievable when added to the enqueue helper's <100 ms.

**AC-MAX — Maximum-scale pre-callout phase stays under 6 seconds via bulk + dedup.**
**Given** a PAR submission with the maximum payload supported by the OmniScript today (5 groups × 10 locations = up to 50 raw addresses, plus 1 practitioner NPI + ≤5 group NPIs + 1 Tax-Id + 1 CAQH ID — see `US_PAR_ScaleAudit_5Groups_10Locations.md`),
**When** the OmniScript invokes `PRM_PreSubmitCalloutPhase_Procedure_1`,
**Then** the user-perceived wall-clock from "click Submit" → "callout phase complete, batch enqueued" is **≤ 6 seconds at P50** and **≤ 15 seconds at P95**. The IP makes **exactly one bulk Precisely callout** (NOT 50 single-address calls) — implemented via `PRM_AddressValidationService.validateAddressesBulk()` (see §G below) which deduplicates raw addresses by `(line1, city, state, zip5)` before the callout, typically reducing 50 → 10-20 unique addresses, then expands the response back to 50 positional results. `PreSubmitCalloutResult.standardizedAddresses` returns exactly one entry per raw input address.

**AC-FAIL-FAST — Fail-fast when Precisely is degraded at max scale.**
**Given** the Precisely bulk callout exceeds a 15-second wall-clock budget (e.g., during a Precisely incident or peak-traffic latency spike),
**When** the IP's wall-clock guard trips,
**Then** the OmniScript displays a sticky toast "Address validation is temporarily slow. Please retry in a moment, or contact your administrator to enable the PRM_SkipPrecisely toggle." The OmniScript blocks Submit, **no batch is enqueued**, no records are created, and `PRM_ExceptionLog__c` records a `Warning`-severity event with `PRM_ErrorCategory__c = 'PRECISELY_SLOW'` and the observed wall-clock for monitoring/alerting.

**AC8 — Pre-callout failures are logged via Platform Event.**
**Given** a callout failure inside the pre-callout phase,
**When** the orchestrator's catch block fires,
**Then** an exception log is published via `PRM_ExceptionLogger.logExceptionViaEvent` (from US-PAR-02) with `PRM_ProcessName__c = "PRM_PreSubmitCalloutOrchestrator.<methodName>"`, `PRM_TargetSystem__c = "Precisely"` (or whichever external), and the IA-link populated.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Today, which IPs / Apex classes make HTTP callouts during the PAR submission path? (We need to enumerate them all so the pre-callout phase covers them.) Known: Precisely (via `PRM_AddressValidationService`). Suspected: MuleSoft NPI lookup, CAQH cache warm, USPS verify. | Determines the steps inside `PRM_PreSubmitCalloutPhase_Procedure_1`. | Apex Lead + PNM SME |
| 2 | Should the pre-callout phase be (a) one IP with multiple Remote Action steps, or (b) one Remote Action invoking an Apex orchestrator that internally calls all the services? (a) gives finer-grained error handling in the OmniScript; (b) is simpler. | Affects §A and §D. | Architecture Lead |
| 3 | The seven sub-IPs include one (sub-IP 3: `PRM_PractitionerScreenExistingNPIRecordUpdation`) that explicitly handles "existing NPI" — does it make a callout, or only DML? If callout, that callout also moves to the pre-callout phase. | Determines sub-IP 3 disposition under US-PAR-01. | Apex Lead |
| 4 | Are there UTAM / QTA scenarios that mock Precisely today? They will need to update to mock at the new pre-callout phase boundary. | QA regression coverage. | QA Lead |
| 5 | **BLOCKER FOR AC-MAX.** Does Precisely's `verify` API (called via `PRM_IPPreciselyAPICall`) support a batch payload of up to 50 addresses per HTTP request? — If yes: §G.1 + §G.2 bulk wrapper is sufficient. — If no: must implement §G.4 `@future(callout=true)` fan-out fallback, which adds an async hop and ~3 days of effort. **Owner:** Integrations team + Precisely contact. **Cannot ship US-PAR-03 without this answer.** Current `PRM_AddressValidationService.validateAddress()` is single-address only — confirmed via code inspection on 2026-05-28. | AC-MAX feasibility + path choice between §G.1-3 and §G.4. | Apex Lead + Integrations Lead |
| 6 | Should the pre-callout phase warm a CAQH cache that the batch later reads? Or is CAQH only relevant during credentialing (post-submit), not at PAR-intake time? | Determines whether step 5 of §A is in scope or out. | PNM SME |
| 7 | If Precisely is down (HTTP 500, timeout), does Operations want (a) hard fail Submit with sticky error toast, or (b) soft fail — let the submission proceed with `uspsVerified=false`? Today the form does a soft fail because the bypass toggle exists. | AC2 wording. | Operations Lead |
| 8 | Are there any analytics / monitoring tools that today read "how long did the Submit take" — they may show a regression as the work that used to be inside the Submit IP becomes split across pre-callout + batch enqueue? | Stakeholder communication. | Analytics Lead |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_PreSubmitCalloutPhase_Procedure_1` | Integration Procedure (NEW) | **HIGH** | New IP; encapsulates all callouts. |
| `PRM_PreSubmitCalloutOrchestrator.cls` | Apex (NEW) | **HIGH** | New orchestrator. |
| `PRM_PreSubmitCalloutResult.cls` | Apex POJO (NEW) | **MEDIUM** | New POJO consumed by US-PAR-01. |
| `PRM_OmniProcessUtils.cls` | Apex (existing) | **LOW** | One new route. |
| `PRM_PractitionerParticipationForm_English` v112 | OmniScript (NEW version) | **HIGH** | Inserts the new "PreSubmitCallouts" step and the error-block branch. |
| `PRM_AddressValidationService.cls` | Apex (existing) | **MEDIUM** | **NEW method `validateAddressesBulk(List<AddressShape>)`** added to support the 5×10 max scale (see §G.1). Existing `validateAddress(...)` unchanged. |
| `PRM_IPPreciselyAPICallBulk` | Integration Procedure (NEW) | **HIGH** | New bulk variant of the existing Precisely IP. Required by AC-MAX. **Blocker:** Clarification #5 (does Precisely API support batch input?). |
| Existing seven sub-IPs of `PRM_CreateParFormRecords` | IP (existing) | **LOW** | Out-of-scope for this story (US-PAR-01 deactivates them). |
| QTA / UTAM scenarios mocking Precisely | Tests | **MEDIUM** | Move mock boundary to the new IP step. |
| Apex unit test mandate (no callouts in batch) | Tests | **MEDIUM** | New invariant test in US-PAR-01's batch test class. |

---

## Estimated Effort

| Component | Type | Effort | Notes |
|---|---|---|---|
| `PRM_PreSubmitCalloutResult.cls` | POJO (NEW) | **S** (< 1 hr) | Plain Apex POJO. |
| `PRM_PreSubmitCalloutOrchestrator.cls` | Apex (NEW) | **L** (1 day) | 3–4 methods; each wraps an existing service call. |
| `PRM_PreSubmitCalloutOrchestratorTest.cls` | Apex test (NEW) | **L** (4–8 hrs) | Mock each external system; happy + failure paths. |
| `PRM_PreSubmitCalloutPhase_Procedure_1` | IP (NEW) | **L** (4–8 hrs) | 7-step IP wired to Apex orchestrator. |
| `PRM_AddressValidationService.validateAddressesBulk()` + dedupe + positional expand | Apex (existing class, NEW method) | **L** (1 day) | Required for AC-MAX. Implementation per §G.1. Replaces the naive serial loop. |
| `PRM_IPPreciselyAPICallBulk` IP | IP (NEW) | **L** (1 day) | Bulk variant of `PRM_IPPreciselyAPICall`. **Blocked** by Clarification #5. |
| Wall-clock fail-fast guard | Apex (in orchestrator) | **S** (1 hr) | Per §G.3. |
| Fallback `@future` fan-out (only if Precisely batch unavailable) | Apex (NEW) | **L** (2-3 days) | Per §G.4. Only if Clarification #5 forces it. |
| `PRM_OmniProcessUtils.cls` route add | Apex | **S** (< 1 hr) | One `if`. |
| `PRM_PractitionerParticipationForm_English` v112 | OmniScript | **L** (4–8 hrs) | New step + conditional block + error toast. |
| Audit + enumerate all PAR-pipeline callouts | Discovery | **M** (2–4 hrs) | Clarification #1 resolution. |
| QTA / UTAM mock-boundary updates | Tests | **M** (2–4 hrs) | Mock at new IP boundary. |
| Sandbox UAT + perf measurement | QA | **M** (2–4 hrs) | AC7 verification. |

**Total Estimated Effort:** **~4–6 person-days** — overall **L** sprint slice. Most of the cost is enumeration (Clarification #1) and orchestrator unit tests.

---

## Deployment Checklist

**Pre-requisites:**
- [ ] Resolve Clarification #1 (full callout inventory)
- [ ] Resolve Clarification #2 (IP-orchestration vs Apex-orchestration choice)

**Metadata (deploy in order):**
- [ ] `PRM_PreSubmitCalloutResult.cls`
- [ ] `PRM_PreSubmitCalloutOrchestrator.cls` + test
- [ ] `PRM_OmniProcessUtils.cls` route update + regression test pass
- [ ] `PRM_PreSubmitCalloutPhase_Procedure_1`
- [ ] `PRM_PractitionerParticipationForm_English` v112

**Verification in Sandbox:**
- [ ] AC1: open OmniScript, click Submit on a happy-path submission, watch the IP debug log — confirm Precisely runs in `PRM_PreSubmitCalloutPhase_Procedure_1` step, NOT inside the seven sub-IPs (which are still active at this point pre-US-PAR-01).
- [ ] AC2: force Precisely to return an error (use a known-bad ZIP), confirm Submit is blocked.
- [ ] AC3: log the `additionalInput.locationsToUpsert` payload at the Submit step, confirm it contains USPS-canonical addresses.
- [ ] AC7: time the pre-callout phase across 5 typical submissions, confirm P95 < 2 s.
- [ ] AC8: force a callout failure, confirm exception log appears (depends on US-PAR-02 being live).

**Post-Deployment Monitoring (first 14 days):**
- [ ] Query: `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_TargetSystem__c='Precisely' AND CreatedDate=LAST_N_DAYS:1` — confirm logs appear when Precisely has issues
- [ ] Query: `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_ErrorMessage__c LIKE '%uncommitted work%' AND CreatedDate=LAST_N_DAYS:7` — target 0 from PAR-related processes (pre-existing CAQH errors may remain)
- [ ] Performance dashboard: PAR Submit P95 stays within target after the new step is added

---

## Related Stories

| Story | Priority | Relationship |
|---|---|---|
| `US-PAR-01` (Batch Refactor) | P0 | **Hard consumer** — batch invariant (no callouts) depends on this story; this story must ship first |
| `US-PAR-02` (Exception Logging via Platform Event) | P0 | **Consumer** — pre-callout failures use the event-based logging |
| `PRM_NetworkCreation_BatchImplementation_Guide.md` §"Callout Handling" | Reference | **Pattern source** — explains the platform constraint we are designing around |
| `PRM_ValidateCAQH` "uncommitted work pending" exceptions (1,007 / 30 d) | Investigation | **Cross-cutting** — same architectural anti-pattern; a follow-on story should apply the same pre-callout pattern to the cred flow |
