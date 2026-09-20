# USER STORY: PSV Service Area Verification — CAQH Bulk Practice Location DataMapper Failure (Bug Fix)

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScript:** `PRM_PrimarySourceVerificationReview_English` (parent), `PRM_PSVSubOsTxnyRole_English` (sub-OmniScript containing the Service Area Verification step)
**Integration Procedures:** N/A (root cause is a DataRaptor Transform, not an IP)
**Relevant Requirements:** Case Manager Reference `IA-0000047990` (production defect report); reproduction script `scripts/apex/psv_caqh_dr_bulk_perf_test.apex`

---

## Story

**As a** Credentialing Specialist,
**I want** the Service Area Verification step of Primary Source Verification (PSV) to display and process a practitioner's CAQH practice locations without freezing or erroring, no matter how many mailing/billing locations CAQH returns,
**So that** I can complete PSV review and click Continue without the case getting stuck and my verification work being lost.

**Why it matters:** In production, when CAQH returns a large number of mailing/billing locations for a practitioner (documented case: `IA-0000047990`), the Service Area Verification screen becomes progressively slower to load, the screen eventually throws an error, and clicking Continue does not save — the case remains stuck in PSV and never reaches QC. This blocks case throughput and forces manual workarounds by Credentialing Specialists and their leads.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Primary Source Verification (PSV) | `PRM_PSVSubOsTxnyRole_English` (invoked as a sub-OmniScript from `PRM_PrimarySourceVerificationReview_English`) | Service Area Verification (`ServiceAreaVerificationStep` → `CAQHPracticeAddressBlk`) | DataRaptor Transform `DRTransformCAQHPSVResponse`, bundle `PRMTransformCAQHPSVReview` |

**Explicitly out of scope for this story:** the separate, already-documented (but never deployed) proposal in `requirements/primarysourceverification/` (`SOLUTION_SUMMARY.md`, `Integration_Procedure_Modifications.md`, `PracticeLocationBatchProcessor.apex`, dated 2026-04-09). That proposal targets a **different** bottleneck — the **PSV Case Closure** step, where Integration Procedure `PRM_ReviewPSVCaseRecordsUpdate` creates `HealthcarePractitionerFacility` records for every practice location at case-close time. This story addresses the **mid-flow display/transform** bottleneck in the Service Area Verification screen, which fails earlier in the flow and independently of case closure. Both stem from CAQH returning high volumes of practice locations for the same practitioner and should be reconciled by whoever picks up the closure-time proposal, but are not the same code path and are not fixed by the same change.

---

## Current State (from codebase)

### DataRaptor Transform Action `DRTransformCAQHPSVResponse`

- **Element** (DataRaptor Transform Action): Runs synchronously inside the `PRM_PSVSubOsTxnyRole_English` sub-OmniScript. `sendJSONNode`/`sendJSONPath`/`responseJSONNode`/`responseJSONPath` are all empty, meaning the **entire OmniScript JSON context** is sent to the DataRaptor and the entire output is merged back at the root — there is no scoping to a subset of the payload.
- **Location:** `vlocity_export/OmniScript/PRM_PrimarySourceVerificationReview_English/PRM_PrimarySourceVerificationReview_English_Element_DRTransformCAQHPSVResponse.json`

### DataRaptor `PRMTransformCAQHPSVReview`

- **Element** (DataRaptor Transform, ~3,845 lines of mapping metadata): Reads `Provider:Practice:*` paths from the CAQH-shaped payload — `PracticeName`, `NPI`, `PracticeAddress:*`, `Tax:TaxID`, `Limitation:*`, and, critically, `Patient:PatientType:PatientTypeDescription` (nested `Patient[]` array) and additional `Service[]`-array fields — all nested **inside each individual `Practice` element**.
- **Location:** `force-app/main/default/omniDataTransforms/PRMTransformCAQHPSVReview_1.rpt-meta.xml`; sample payload shape in `vlocity_export/DataRaptor/PRMTransformCAQHPSVReview/PRMTransformCAQHPSVReview_SampleInputJson.json` (confirms `Patient[]` and `Service[]` are sibling arrays nested under each `Practice` entry).

### Display block `CAQHPracticeAddressBlk`

- **Element** (Edit Block, Table mode, `maxDisplay: 3`): Displays `Provider:Practice:PracticeAddress` rows. Shown only when `Provider:Practice:PracticeAddress` is not null and `isCAQHIDPresent` is true.
- **Location:** `vlocity_export/OmniScript/PRM_PSVSubOsTxnyRole_English/PRM_PSVSubOsTxnyRole_English_Element_CAQHPracticeAddressBlk.json`
- **Note:** the UI only ever renders 3 rows regardless of how many practice locations exist — the DataRaptor is doing far more transform work than the screen ever displays.

### Confirmed root cause (reproduced 2026-07-24)

Using the live QA CAQH sandbox (test provider id `16174884`, which already carries 78 real `Provider.Practice` entries — each with nested `Patient[]` and `Service[]` sub-arrays, matching production CAQH payload shape), the DataRaptor `PRMTransformCAQHPSVReview` was invoked directly via `omnistudio.DRGlobal.processFromApex` at increasing practice-location counts (inflated by cloning the 78 real entries):

| Practice locations (N) | CPU time | Result |
|---|---|---|
| 78 (real, prod-like volume) | 111ms | OK |
| 90 – 110 | 94–417ms | OK |
| **115** | **15,243ms** | `System.LimitException: Apex CPU time limit exceeded` |
| 118, 120, 130, 150, 250, 400, 600 | ~15,000–15,258ms | Same exception, every run |

This is not a linear slowdown — there is a hard cliff between ~110 and ~115 practice locations where CPU cost jumps roughly 30–150x and the transaction aborts, well past the 10-second synchronous Apex CPU limit. The cause is that the DataRaptor Transform maps the sibling `Patient[]` and `Service[]` arrays (both nested under the same `Practice` element) into the same output row set without a shared list index, producing an **implicit cross-join** (`Patient × Service`) for every practice location. Total transform cost scales as `SUM_over_practices(patientTypes_i × serviceTypes_i)`, not with practice-location count alone — so a modest increase in the number of locations returned by CAQH (well within "hundreds," as reported) is enough to blow the budget once a few "heavy" practices (more patient types / services) are included.

Reproduction script (parameterized, re-runnable): `scripts/apex/psv_caqh_dr_bulk_perf_test.apex`.

---

## Acceptance Criteria

> Every AC uses Pattern A (behavioural, business language). Implementation
> detail (class names, cross-join elimination, thresholds) lives in Technical
> Implementation below.

**AC-1 — Service Area Verification loads normally for a practitioner with a large number of CAQH practice locations**

**Given** a Credentialing Specialist opens the Service Area Verification step for a practitioner whose CAQH profile returns several hundred mailing and billing locations,
**When** the step loads,
**Then** the practice location addresses display within the same time as any other PSV step, with no visible slowdown tied to the number of locations,
**And** no DataMapper or transform error is shown to the Credentialing Specialist.

**AC-2 — Continue reliably saves the Credentialing Specialist's verification work**

**Given** a Credentialing Specialist has completed the Service Area Verification review for a practitioner with a large number of CAQH practice locations,
**When** they click Continue,
**Then** their verification selections are saved and the case advances to the next PSV step,
**And** the case does not remain stuck on the Service Area Verification step.

**AC-3 — Existing low-volume practitioners see no change in behavior**

**Given** a Credentialing Specialist opens the Service Area Verification step for a practitioner with a typical (small) number of CAQH practice locations,
**When** the step loads and they click Continue,
**Then** the displayed practice address information and downstream verification behavior is identical to today,
**And** no regression is introduced for the common case.

**AC-4 — Extreme-volume submissions degrade safely instead of failing**

**Given** CAQH returns an unusually large number of practice locations for a practitioner (beyond the volume validated in AC-1),
**When** the Credentialing Specialist opens Service Area Verification,
**Then** the step still loads and allows the Credentialing Specialist to complete their review,
**And** if the volume is high enough that full synchronous processing is not safe, the system falls back to a mode that still lets the Credentialing Specialist finish the step without an error,
**And** no case is silently left stuck without the Credentialing Specialist knowing.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `DRTransformCAQHPSVResponse` (OmniScript element in `PRM_PSVSubOsTxnyRole_English`) | OmniScript element | Replace the "DataRaptor Transform Action" with a Remote Action (Apex Remote) calling a new Apex class | Drives AC-1, AC-2, AC-3 |
| New Apex class (suggested name: `PRM_CAQHPracticeLocationTransformService`, following the org's `PRM_*Service` convention) | New Apex class | Single-pass (O(N)) transform over `Provider.Practice[]`; for each practice, emit exactly **one** output row (per the "collapse, don't cross-join" decision below) using the first/primary `Patient` type and `Service` entry rather than the full `Patient × Service` cross-join the DataRaptor currently produces | Drives AC-1, AC-2, AC-3; eliminates the root-cause cross-join |
| Same Apex class | New Apex logic | Add a volume-threshold guard: below the threshold, process fully synchronously (parity with today's fields); at/above the threshold, apply a safe fallback (e.g., process only what the `CAQHPracticeAddressBlk` block can display — `maxDisplay: 3` — plus whatever `PRM_ValidatePracticeLocationParent` needs for existing-location matching) so the step never throws `System.LimitException` | Drives AC-4; owner to confirm exact threshold and fallback field set — see Clarification Questions |
| `PRMTransformCAQHPSVReview` (DataRaptor, `force-app/main/default/omniDataTransforms/PRMTransformCAQHPSVReview_1.rpt-meta.xml`) | Existing DataRaptor | Deactivate/retire once the Apex Remote Action replaces its call site; do not delete until parity is confirmed in shadow testing | Drives AC-3 (no regression) |
| `IPValidatePracticeLocation` → `PRM_ValidatePracticeLocationParent` → `PRM_ValidatePracticeLocation` (active version `_3`) | Existing Integration Procedure | No change expected, but must be validated against the new Apex output shape (one row per practice location instead of the cross-joined shape) since it consumes the same `Provider:Practice:*` structure for existing-location matching | Drives AC-3; flagged for regression testing |
| `scripts/apex/psv_caqh_dr_bulk_perf_test.apex` | Existing reproduction/perf script | Reuse as the perf regression check — re-run against the new Apex service (not the DataRaptor) once built, confirming CPU stays flat and low across N=78 through N=600+ | Drives AC-1, AC-4 verification |

---

## Definition of done

- [ ] AC-1 verified: a practitioner with 300+ CAQH practice locations (real or synthetically inflated, per `scripts/apex/psv_caqh_dr_bulk_perf_test.apex`) loads Service Area Verification with no error and CPU time well under the synchronous limit.
- [ ] AC-2 verified: Continue saves and advances the case for the same high-volume practitioner.
- [ ] AC-3 verified: a typical low-volume practitioner shows identical displayed data and downstream behavior before and after the change (shadow/parity comparison).
- [ ] AC-4 verified: the agreed extreme-volume fallback (threshold + degraded-but-non-erroring path) is exercised and does not silently strand a case.
- [ ] `PRM_ValidatePracticeLocationParent` / `PRM_ValidatePracticeLocation` regression-tested against the new single-row-per-practice output shape.
- [ ] >= 85% Apex test coverage on the new service class, including bulk (300+ practice locations), single, empty (`Provider.Practice` absent/null), and the threshold-fallback path.
- [ ] No regression to PSV completion rates or to the QC handoff for cases already in flight.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | For a practice location with multiple `Patient` types and `Service` entries, which one should the collapsed single row surface (first in CAQH's returned order? a specific type/service business rule?) | Determines exact field-selection logic in the new Apex service; affects what the Credentialing Specialist and downstream `PRM_ValidatePracticeLocation` see for that location | BA / Product |
| 2 | What is the exact volume threshold for the AC-4 fallback path (e.g., 500? 1,000? no threshold at all if the cross-join removal alone keeps CPU flat)? | Sizes the fallback logic; if the collapsed single-pass rewrite already stays flat at 600+ (per the reproduction data), a threshold may only be a defensive safety margin, not a functional requirement | Technical / Product |
| 3 | Should the eventual fix in `requirements/primarysourceverification/` (PSV Case Closure async processing) be revisited/reconciled with this fix, since both are triggered by the same root data condition (CAQH returning high practice-location volume) on the same case? | Avoids duplicate or conflicting future work on the same underlying CAQH data-volume problem | Product / Technical lead |
| 4 | Is there a business need to eventually raise `maxDisplay` above 3 on `CAQHPracticeAddressBlk`, now that processing cost is no longer tied to the number of locations returned? | Could change UI scope beyond this bug fix | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PSVSubOsTxnyRole_English` | OmniScript | HIGH | Element type change (DataRaptor Transform Action → Remote Action) on the step that fails today |
| `PRM_PrimarySourceVerificationReview_English` | OmniScript | LOW | Parent OmniScript invokes the sub-OmniScript unchanged; no direct edits expected |
| `PRMTransformCAQHPSVReview` | DataRaptor | HIGH | Retired/deactivated as the transform's call site moves to Apex |
| `PRM_ValidatePracticeLocationParent` / `PRM_ValidatePracticeLocation` | Integration Procedure | MEDIUM | Consumes the same `Provider:Practice:*` structure; must be regression-tested against the new single-row-per-practice shape |
| `CAQHPracticeAddressBlk` | OmniScript Edit Block | LOW | Display source path unchanged; only the volume/shape of upstream data changes (safely) |

---

## Estimated Effort

*(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| New Apex service class (single-pass practice-location transform) | New Apex class | XL | Core rewire; must port every field currently mapped by the ~3,845-line DataRaptor |
| Apex unit tests (bulk 300+, single, empty, threshold-fallback) | Apex test class | L | ≥85% coverage gate |
| OmniScript element swap (DataRaptor Transform Action → Remote Action) | OmniScript element | M | Single element change plus wiring |
| Volume-threshold/fallback logic (AC-4) | Apex logic | M | Pending Clarification Question #2 on exact threshold |
| Regression pass on `PRM_ValidatePracticeLocation` chain | Testing / validation | L | Confirm no behavior change for existing-location matching |
| Deactivate `PRMTransformCAQHPSVReview` DataRaptor | Config | S | After parity confirmed |

**Total Estimated Effort:** ~XL overall (multi-day effort, dominated by the new Apex service and its field-parity testing)
