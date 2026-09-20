# USER STORY: PDM Manual Update — Look Up Account / Practitioner / Practice Location by PIE ID Instead of NPI or Tax ID

**Persona:** PDM Specialist (Provider Data Management)
**Priority:** P1
**OmniScript:** `PRM_PDMManualUpdate_English_44` (parent), `PRM_PDMManualUpdateVendorAccount_English_6`, `PRM_PDMManualUpdatePractitioner_English_24`, `PRM_PDMManualUpdatePracticeLocation_English_15`
**Integration Procedures:** `PRM_FetchPDMManualUpdateDetails_Procedure_7`, `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_1`
**Data Raptors (record lookups today):** `PRMFetchVendorAndHCFWithNPI_1`, `PRMFetchVendorAndHCFWithTaxIDOptimised_1`, `PRMFetchVendorAccWithTaxIdAndBillingZip_1`, `PRMDRExtractPDMAccountDetails_1`
**Relevant Requirements:** `requirements/TDD_PDMManualUpdate_Practitioner_IPToApex.md`, `requirements/TDD_PDMManualUpdate_Practitioner_LargeDataOptimization.md`, `requirements/PDM Flows/US_PDM_WebsiteEmail_OverlappingAddressError.md`, `requirements/PDM/US_PDM_BillingAddress_Bundle_Invariant_Decision_Brief.md`

---

## Story

**As a** PDM Specialist,
**I want** to open the PDM Manual Update flow for an Account, Practitioner, or Practice Location by entering the record's PIE-side identifier (Vendor Number, Practitioner Number, or Practice Location Number) — so that when I already know the PIE identifier I am not forced to also enter the NPI or Tax ID,
**So that** I can start an update case in a single step for records I have already identified upstream, and I stop hitting false "record not found" errors that today occur when the NPI or Tax ID stored on the record is stale, blank, or shared across multiple entities.

**Why it matters:** Every PDM Manual Update case today requires NPI (for Practitioner) or Tax ID (for Vendor Account / Practice Location) to enter the flow. When the PDM Specialist works from an upstream PIE extract (roster load, Concierge, network re-cred file), the PIE ID (Vendor / Practitioner / Practice Location Number) is the primary key they already have — re-keying an NPI or Tax ID that they may not have on hand adds manual effort, and stale or shared NPIs/Tax IDs produce ambiguous or empty search results that force the Specialist to abandon the flow and start again. Because these lookup identifiers (`PRM_IdentifierVendor__c`, `PRM_IdentifierPractitioner__c`, `PRM_IdentifierHealthcareFacility__c`) already exist on every record, the change is entry-point-only — no schema and no downstream flow logic changes.

---

## Scope

| Flow | OmniScript (active version) | Affected Step | Data Source Today |
|------|----------------------------|--------------|-------------------|
| PDM Manual Update — Vendor Account | `PRM_PDMManualUpdateVendorAccount_English_6` | Vendor identification step (Tax ID + billing zip entry) | `PRMFetchVendorAccWithTaxIdAndBillingZip_1` (DR) → `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_1` |
| PDM Manual Update — Practitioner | `PRM_PDMManualUpdatePractitioner_English_24` | Practitioner identification step (NPI entry) | `PRMFetchVendorAndHCFWithNPI_1` (DR) → `PRM_FetchPDMManualUpdateDetails_Procedure_7` |
| PDM Manual Update — Practice Location | `PRM_PDMManualUpdatePracticeLocation_English_15` | Practice Location identification step (Tax ID + billing zip entry) | `PRMFetchVendorAndHCFWithTaxIDOptimised_1` (DR) → `PRM_FetchPDMManualUpdateDetails_Procedure_7` |

**Out of scope:** Provider Change, Account Creation, PAR, and any other manual-entry flow. Feature flag gating (`PRM_FeatureConfigurationSettings__c.PRM_EnablePIE__c`) is intentionally NOT applied — this behavior ships always-on for PDM Manual Update. No changes to any post-selection PDM Manual Update step (address edit, taxonomy edit, group edit, submit, QC).

---

## Current State (from codebase)

### Parent OmniScript — `PRM_PDMManualUpdate_English_44`

- **Active version:** confirmed `<isActive>true</isActive>` in `force-app/main/default/omniScripts/PRM_PDMManualUpdate_English_44.os-meta.xml`.
- **Entry-point elements today (grounded via `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/`):**
  - `Element_NPI.json`, `Element_PracNPI.json`, `Element_VendorNPI.json`, `Element_PLNPI.json` — NPI capture inputs across the three sub-flows.
  - `Element_TaxIdPN.json` — Tax ID capture input (Practice Location / Vendor Account paths).
  - `Element_InvalidNPIErrorMsg.json` — hard-block message when NPI fails validation.
  - `Element_PractitionerNumber.json`, `Element_PracPractitionerNumber.json`, `Element_PLNumber.json`, `Element_VendorNumber.json` — read-only display fields that ALREADY render the PIE-side numbers after lookup, but are not editable and are not accepted as entry-point inputs today.

### PIE ID fields (already on the target objects — no schema work required)

| Business term | Object | Field API name | Field type | Verified in |
|---|---|---|---|---|
| Vendor Number | `Account` (record type `PRM_Vendor`, `PRM_SupplementalBenefitVendor`, `PRM_NCPDP`) | `PRM_IdentifierVendor__c` (Lookup to `PRM_IdentifierVendor__c`) | Lookup, `trackHistory=true`, label "Vendor Number" | `force-app/main/default/objects/Account/fields/PRM_IdentifierVendor__c.field-meta.xml` |
| Practitioner Number | `Account` (record type `PRM_Practitioner`) | `PRM_IdentifierPractitioner__c` (Lookup to `PRM_IdentifierPractitioner__c`) | Lookup, `trackHistory=true`, label "Practitioner Number" | `force-app/main/default/objects/Account/fields/PRM_IdentifierPractitioner__c.field-meta.xml` |
| Practice Location Number | `HealthcareFacility` | `PRM_IdentifierHealthcareFacility__c` (Lookup to `PRM_IdentifierHealthcareFacility__c`) | Lookup, `trackHistory=true`, label "Practice Location Number" | `force-app/main/default/objects/HealthcareFacility/fields/PRM_IdentifierHealthcareFacility__c.field-meta.xml` |

### Fetch IP chain today

- **Practitioner:** `PRM_FetchPDMManualUpdateDetails_Procedure_7` (v7 is latest active) runs `PRMFetchVendorAndHCFWithNPI_1` on the entered NPI → returns the matching `Account` and its HCF/HCPF graph.
- **Practice Location:** same IP invokes `PRMFetchVendorAndHCFWithTaxIDOptimised_1` on the entered Tax ID + Billing Zip pair.
- **Vendor Account:** `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_1` invokes `PRMFetchVendorAccWithTaxIdAndBillingZip_1`.

### Precedent PIE-based DataRaptors already in the org (reuse candidates)

`PRMExtractPracticeLocationByPIE_1`, `PRMDRExtractPracticeLocationWithPIENumbers_1`, `PRMExtractCrossRefPIEAccCreation_1`, `PRMExtractCrossRefPracticeByPIE_1` — these already query the identifier objects on the PIE side and demonstrate the pattern for by-PIE lookup. The story adds a peer DR/IP path for PDM Manual Update, modelled on these.

---

## Acceptance Criteria

> All ACs are Pattern A (behavioural, business language). No records are created or updated by this story — the entry-point behaves as a search filter only — so Pattern E is not applicable. Field API names, IP versions, and DR names appear only in the Technical Implementation section below.

**AC-1 — PDM Specialist opens a Practitioner update case using only the Practitioner Number**

**Given** I am a PDM Specialist on the PDM Manual Update — Practitioner entry step,
**When** I enter a valid Practitioner Number that exists on a Practitioner Account and leave the NPI field blank, then click Search,
**Then** the flow proceeds to the Practitioner record's edit step with all details loaded (Practitioner Account, Practice Locations, taxonomies)
**And** no "NPI required" validation error is shown
**And** the read-only Practitioner Number and NPI fields on the loaded record display the correct values from Salesforce.

**AC-2 — PDM Specialist opens a Vendor Account update case using only the Vendor Number**

**Given** I am a PDM Specialist on the PDM Manual Update — Vendor Account entry step,
**When** I enter a valid Vendor Number that exists on a Vendor Account and leave both the Tax ID and Billing Zip fields blank, then click Search,
**Then** the flow proceeds to the Vendor Account's edit step with all details loaded (Vendor Account, contract hierarchy, billing address bundle)
**And** no "Tax ID required" or "Billing Zip required" validation error is shown.

**AC-3 — PDM Specialist opens a Practice Location update case using only the Practice Location Number**

**Given** I am a PDM Specialist on the PDM Manual Update — Practice Location entry step,
**When** I enter a valid Practice Location Number that exists on a Practice Location and leave both the Tax ID and Billing Zip fields blank, then click Search,
**Then** the flow proceeds to the Practice Location's edit step with all details loaded (Practice Location, its owning Vendor Account, taxonomies)
**And** no "Tax ID required" or "Billing Zip required" validation error is shown.

**AC-4 — Existing NPI-based Practitioner search continues to work unchanged**

**Given** I am a PDM Specialist on the PDM Manual Update — Practitioner entry step,
**When** I enter a valid NPI and leave the Practitioner Number field blank, then click Search,
**Then** the flow proceeds exactly as it does today
**And** the resolved practitioner and all downstream steps behave identically to the pre-change flow (no regression).

**AC-5 — Existing Tax-ID-based Vendor Account / Practice Location search continues to work unchanged**

**Given** I am a PDM Specialist on the PDM Manual Update — Vendor Account entry step (or the Practice Location entry step),
**When** I enter a valid Tax ID and Billing Zip and leave the corresponding PIE Number field blank, then click Search,
**Then** the flow proceeds exactly as it does today (no regression to Tax ID + Billing Zip search).

**AC-6 — Invalid PIE Number blocks progression with a clear error**

**Given** I am a PDM Specialist on any of the three PDM Manual Update entry steps,
**When** I enter a PIE Number (Vendor / Practitioner / Practice Location Number) that does NOT match any record in Salesforce, leave the NPI / Tax ID fields blank, then click Search,
**Then** I see a validation error stating "No record found for the entered [Vendor / Practitioner / Practice Location] Number"
**And** the flow does NOT advance to the edit step
**And** no case, no Case Manager, and no PDM Manual Update record is created.

**AC-7 — Empty entry blocks progression (both search paths required to be blank fails)**

**Given** I am a PDM Specialist on any of the three PDM Manual Update entry steps,
**When** I click Search with the PIE Number, the NPI, and the Tax ID / Billing Zip fields ALL blank,
**Then** I see a validation error stating "Enter either the [Vendor / Practitioner / Practice Location] Number, or the [NPI / Tax ID + Billing Zip], to continue"
**And** the flow does NOT advance.

**AC-8 — Conflicting inputs (PIE Number + NPI/Tax ID that resolve to different records) block progression**

**Given** I am a PDM Specialist on the PDM Manual Update — Practitioner entry step,
**When** I enter a Practitioner Number and an NPI that resolve to two different Practitioner Accounts, then click Search,
**Then** I see a validation error stating "The Practitioner Number and NPI entered belong to different practitioners — clear one field and try again"
**And** the flow does NOT advance
**And** the same rule applies to the Vendor Account and Practice Location entry steps for conflicting Vendor Number vs. Tax ID and Practice Location Number vs. Tax ID pairs.

**AC-9 — PIE Number belonging to the wrong record type does not resolve on the wrong sub-flow**

**Given** I am a PDM Specialist on the PDM Manual Update — Practitioner entry step,
**When** I enter a Vendor Number (which is a valid PIE identifier but not for a Practitioner) into the Practitioner Number field, then click Search,
**Then** I see the same "No record found for the entered Practitioner Number" error as AC-6
**And** the flow does NOT advance (i.e., the search is scoped to the sub-flow's expected record type — Vendor Numbers never resolve to a Practitioner and vice versa).

**AC-10 — Inactive / terminated record with a valid PIE Number follows existing "record status" rules**

**Given** I am a PDM Specialist on any of the three PDM Manual Update entry steps,
**When** I enter a valid PIE Number that resolves to a record whose status (Active / Terminated / Denied) would today block the NPI/Tax-ID path from proceeding,
**Then** the flow shows the same status-based validation message that the NPI/Tax-ID path shows today
**And** the flow does NOT advance (i.e., PIE-ID search is NOT a bypass for record-status gating — the only thing being replaced is the identifier, not any downstream eligibility check).

---

## Technical Implementation (high-level)

| # | Component | Type | Change | Notes |
|---|---|---|---|---|
| 1 | `PRM_PDMManualUpdate_English_44` → new version `PRM_PDMManualUpdate_English_45` | OmniScript version bump | Add three peer input elements next to the existing NPI / Tax ID / Billing Zip inputs on each sub-flow's entry step: `PracIdentifierInput` (Practitioner Number), `VendorIdentifierInput` (Vendor Number), `PLIdentifierInput` (Practice Location Number). Add a Set Values / Formula element that computes `searchMode = "PIE"` when any PIE input has a value, else `"LEGACY"`. Deactivate v44 after v45 passes shadow-mode testing. | Drives AC-1 · AC-2 · AC-3 · AC-4 · AC-5. |
| 2 | Entry-step validation rules (OmniScript-level `errorMessage` formulas on the Search / Next action) | OmniScript element edit | (a) Blank-blank check → AC-7 error; (b) Conflicting resolution check → AC-8 error; (c) Wrong-type PIE input → AC-9 error (surfaced through the fetch IP's empty response, then rendered as AC-6 error). No error messages are new record types — reuse existing `Element_InvalidNPIErrorMsg` pattern. | Drives AC-6 · AC-7 · AC-8 · AC-9. |
| 3 | `PRM_FetchPDMManualUpdateDetails_Procedure_7` → new version `_Procedure_8` | Integration Procedure version bump | Add a top-level branch on the incoming `searchMode`: (a) `PIE` → run new DR `PRMFetchAccountAndHCFByPIE_1` on the entered PIE Number; (b) `LEGACY` → unchanged existing branch (NPI or Tax ID + Billing Zip). Response contract unchanged so downstream steps require no change. | Drives AC-1 · AC-3 · AC-4 · AC-5 · AC-6. |
| 4 | `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_1` → new version `_Procedure_2` | Integration Procedure version bump | Same branching pattern as (3), scoped to Vendor Account. | Drives AC-2 · AC-5 · AC-6. |
| 5 | `PRMFetchAccountAndHCFByPIE_1` | **New** DataRaptor Extract (Standard) | Given one of {Vendor Number, Practitioner Number, Practice Location Number}, query the corresponding `Account` or `HealthcareFacility` record using the appropriate PIE-side field (`PRM_IdentifierVendor__c` / `PRM_IdentifierPractitioner__c` / `PRM_IdentifierHealthcareFacility__c`) and return the same shape the legacy NPI/Tax-ID DataRaptors return, so the downstream IP steps and OmniScript UI need no format change. Model after `PRMExtractPracticeLocationByPIE_1`. | Drives AC-1 · AC-2 · AC-3 · AC-9 · AC-10. |
| 6 | Conflict-detection helper in the IP branch of (3) and (4) | IP formula/decision step | When BOTH a PIE Number AND an NPI (or Tax ID) are supplied, resolve both separately and compare record IDs; if IDs differ, return the AC-8 error payload. | Drives AC-8. |
| 7 | `PRM_PDMManualCrossRefFinishService` | Apex class | Review to confirm no code assumes NPI/Tax ID is always populated on the finish path (it should not — the finish service already runs off the resolved record IDs). If any assumption exists, either remove it or gate it behind a null-check. | Regression protection for AC-1 · AC-2 · AC-3. |

**Guiding constraints:**
- No schema changes (all three PIE-side fields already exist and are `trackHistory=true`).
- No feature-flag gating (`PRM_FeatureConfigurationSettings__c.PRM_EnablePIE__c` explicitly NOT used; behavior ships always-on).
- Downstream steps (address edit, taxonomy edit, submit, QC path) receive the same resolved record IDs regardless of entry mode — zero contract change to any step past the entry step.

---

## Definition of done

- [ ] PDM Specialist can complete AC-1 (Practitioner Number only), AC-2 (Vendor Number only), and AC-3 (Practice Location Number only) in QA sandbox end-to-end (entry → edit step loaded correctly).
- [ ] Legacy NPI-only (AC-4) and Tax-ID+Billing-Zip-only (AC-5) flows still work with zero step or field-value regression against a captured shadow-mode baseline of 20 recent Manual Update cases (10 Practitioner, 5 Vendor Account, 5 Practice Location).
- [ ] AC-6 (invalid PIE Number), AC-7 (all-blank), AC-8 (conflicting inputs), AC-9 (wrong-type PIE Number), and AC-10 (status-gated record) each produce the specified error and do not advance the flow.
- [ ] `PRMFetchAccountAndHCFByPIE_1` unit-testable via a Callable-invoke Apex test that seeds one Vendor Account, one Practitioner Account, and one HealthcareFacility, calls the DataRaptor for each PIE Number, and asserts the returned graph shape matches the legacy DR shape.
- [ ] Any Apex touched (e.g., `PRM_PDMManualCrossRefFinishService` if changed) has ≥85% test coverage including one bulk (200-record) test and one negative-path test.
- [ ] `PRM_PDMManualUpdate_English_45` deployed as active, `_44` deactivated; corresponding new IP versions deployed as active. Rollback = re-activate v44 and the two prior IP versions.
- [ ] No FLS or permission-set change required (all three PIE-side fields already granted to the PDM Manual Update permission set — verify against `permissionsets/PRM_PDMManualUpdate*` or equivalent before closing).
- [ ] No regression to `PRM_PDMManualCrossRefFinishService`, `PRM_PDMDataHelper`, `PRM_PDMManualUtility`, `PRM_PDMCheckDuplicateEditBlock`, or `PRM_PDMUnlinkPractitioner` (spot-check via one full submit/QC on each sub-flow in QA).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | For the Practice Location sub-flow, today's search uses **Tax ID + Billing Zip** (two fields). Under the PIE-ID path we treat the Practice Location Number alone as sufficient — confirm the business is comfortable dropping the Billing Zip disambiguation for the PIE-ID path (a Practice Location Number is unique on its own, so this should be safe). | Determines whether Billing Zip becomes conditionally required when PIE Number is blank, or is unconditionally dropped from the PIE path. | Product / PDM BA |
| 2 | AC-8 (conflicting PIE + NPI/Tax ID inputs) — should the flow **prefer PIE ID silently** (ignore the NPI/Tax ID) or **hard-block** as the AC currently specifies? Hard-block is safer but slightly more clicks; prefer-PIE is faster but hides a data-quality signal. | Determines whether conflicting inputs error or auto-resolve. | Product / PDM Lead |
| 3 | AC-6 wording — should the "No record found" error include the entered value verbatim (helpful for the Specialist to spot a typo, but risks logging PHI-adjacent identifiers in captured screenshots)? | Copy of the error message and any masking. | Product / Compliance |
| 4 | Are there PDM Manual Update sub-flows other than the three named (Vendor Account, Practitioner, Practice Location) — e.g., `PRM_PDMManualUpdateHCFAssociations_English_2` or `PRM_PDMManualUpdateFHNaticPractitioner_English_3` — that also need a PIE-ID entry option, or are these already downstream of the entry step and therefore out of scope? | Scope creep vs. scope completeness. | PDM BA |
| 5 | Should the new DataRaptor `PRMFetchAccountAndHCFByPIE_1` be built from scratch or should we extend one of the existing PIE-based DRs (`PRMExtractPracticeLocationByPIE_1`, `PRMExtractCrossRefPracticeByPIE_1`) to cover the Vendor and Practitioner cases too? Extension reduces the DR count; a new dedicated DR keeps the PDM contract independent from Account Creation. | Delivery effort and future maintenance surface. | Technical / OmniStudio lead |
| 6 | For AC-10 (status-gated records), please confirm the exhaustive list of statuses that today block the NPI/Tax-ID path (Active-only? Include Pending? Exclude Terminated? Exclude Denied?) — the PIE-ID path must mirror this exactly. | Determines the exact status filter on the new DR. | PDM BA |
| 7 | Confirm the field-level security for the three PIE-side fields on the **PDM Manual Update runtime user profile / permission set** — the story assumes Read is already granted (fields are on the read-only display today), but if the entry step is a public-facing OmniScript variant, we may need to explicitly grant Read on the permission set the OmniScript runtime uses. | Determines whether a permission-set change (Pattern C) needs to be added to this story. | Salesforce Admin |
| 8 | Analytics — do any reports, dashboards, or `PRM_ExceptionLog__c` searches key off the entered NPI or Tax ID at the PDM Manual Update entry point (e.g., "cases entered by NPI vs. by Tax ID")? If so, we may need to record the entry-mode (`PIE` / `LEGACY`) on the `IndividualApplication` record for traceability. | Determines whether a small metadata field (`PRM_PDMManualUpdate_EntryMode__c`) needs to be added. | Reporting BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PDMManualUpdate_English_44` → `_45` | OmniScript | HIGH | Entry-step redesign on all three sub-flows; three new inputs + branching validation. |
| `PRM_FetchPDMManualUpdateDetails_Procedure_7` → `_8` | Integration Procedure | MEDIUM | Add search-mode branch at the top of the IP; existing branch retained unchanged. |
| `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_1` → `_2` | Integration Procedure | MEDIUM | Same as above, scoped to Vendor Account. |
| `PRMFetchAccountAndHCFByPIE_1` (new) | DataRaptor Extract | MEDIUM | New DR modelled after `PRMExtractPracticeLocationByPIE_1`; three PIE-side lookup branches. |
| `PRM_PDMManualCrossRefFinishService`, `PRM_PDMDataHelper`, `PRM_PDMManualUtility` | Apex | LOW | Read-only review to confirm no assumption that NPI/Tax ID is always populated at entry. |
| `PRM_PDMManualUpdateVendorAccount_English_6`, `PRM_PDMManualUpdatePractitioner_English_24`, `PRM_PDMManualUpdatePracticeLocation_English_15` | OmniScript (child) | LOW | No structural change expected — child scripts receive the same resolved record IDs the parent hands them today. Verify no child element assumes the parent's NPI/Tax ID context is populated. |
| `Account.PRM_IdentifierVendor__c`, `Account.PRM_IdentifierPractitioner__c`, `HealthcareFacility.PRM_IdentifierHealthcareFacility__c` | Field | NONE | Read-only usage — no schema change. All three are `trackHistory=true` already. |
| Feature flag `PRM_FeatureConfigurationSettings__c.PRM_EnablePIE__c` | Setting | NONE | Explicitly NOT used for this story per business direction (always-on). |
| Concierge, PAR, Provider Change, Account Creation flows | OmniScript / IP | NONE | Out of scope — no changes. |

---

## Estimated Effort

_AI-estimated — validate with team._

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_PDMManualUpdate_English_45` (v45) | OmniScript version + element edits + validation formulas on 3 entry steps | **L** | 6–8 hrs — three input elements, three validation blocks (blank, conflict, wrong-type), search-mode formula. |
| `PRM_FetchPDMManualUpdateDetails_Procedure_8` | IP version + top-level branch + conflict-detection helper | **L** | 4–6 hrs. |
| `PRM_FetchPDMManualUpdateDetailsVendorAccount_Procedure_2` | IP version + top-level branch | **M** | 3–4 hrs. |
| `PRMFetchAccountAndHCFByPIE_1` | New DataRaptor Extract | **M** | 3–4 hrs — three lookup branches, response shaping to match legacy contract. |
| Apex review (`PRM_PDMManualCrossRefFinishService`, `PRM_PDMDataHelper`, `PRM_PDMManualUtility`) | Read-only review + null-safety patch if needed | **M** | 2–4 hrs (patch only if the review finds an assumption). |
| Apex unit tests (Callable-invoke test for new DR contract) | New test class | **M** | 3–4 hrs. |
| Shadow-mode parity harness (20-case NPI/Tax-ID regression) | QA scripting | **M** | 4 hrs. |
| Deployment + rollback playbook (activate v45 IPs, keep v44 as fallback) | Config | **S** | 1 hr. |

**Total Estimated Effort:** ~26–35 hrs — **L / early XL** overall (roughly 4–5 engineer-days including QA).

---

## Post-Generation Notes

- **Graph-tools verification:** `code-review-graph` semantic search for "PDM Manual Update" returned zero hits (graph coverage gap on this flow) — fell back to `Glob` + `Read` per the SKILL's allowed exception. All named OmniScripts, IPs, DataRaptors, Apex classes, and custom fields cited in this story were verified against real source files under `force-app/main/default/` (paths in the Current State section).
- **Related requirements found in `requirements/`:** `TDD_PDMManualUpdate_Practitioner_IPToApex.md` and `TDD_PDMManualUpdate_Practitioner_LargeDataOptimization.md` design an IP-to-Apex migration for the same flow. If the migration is delivered before this story, the OmniScript-side entry-step changes still apply exactly as specified; only the fetch layer (item 3 & 4 in Technical Implementation) becomes an Apex-batch signature change instead of an IP version bump. Coordinate delivery order with the Practitioner Creation framework lead.
- **No overlap** with `US_PDM_WebsiteEmail_OverlappingAddressError.md`, `US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md`, or `US_PracticeLocationTaxonomy_AgeRange_Fields.md` — those are downstream-step edits, not entry-step.
