# USER STORY: Default & Typeahead for Primary Taxonomy on Vendor Termination "Select Practice Location Taxonomies" Step

**Persona:** PDM Specialist (Provider Data Management, running the Vendor/Group Account Termination guided flow)
**Priority:** P1
**OmniScript:** `PRM_AccountTerminationForm_English` (v9 — active)
**Integration Procedures:** `PRM_AccountTerminationContainer` (submit), `PRM_AccountTermination` (`PRM_AccountTermination_Procedure_17`)
**LWC:** `prmPracticeLocationForAccountTerm`
**Apex:** `PRM_GetFacilityDataForVendor`
**Relevant Requirements:** Vendor account termination — last-man-standing / non-par conversion behavior

---

## Story

**As a** PDM Specialist,
**I want** the Primary Taxonomy picker on the "Select Practice Location Taxonomies" step to be a searchable typeahead that is pre-defaulted to **Internal Medicine** for every practice location,
**So that** I can convert a terminating group to non-par in seconds — only changing the exceptions — instead of scrolling a list of hundreds of taxonomies and picking one for every location by hand.

**Why it matters:** Today, converting a group to Non-Par stalls on this step. The taxonomy field is a static dropdown of every active taxonomy with no search and no default, so each practice location must be opened and set manually. Groups with many locations make this slow and error-prone, and the step is a hard gate that blocks the termination from completing.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Vendor / Group Account Termination | `PRM_AccountTerminationForm_English` v9 | `Select Practice Location Taxonomies` | `prmPracticeLocationForAccountTerm` LWC → `PRM_GetFacilityDataForVendor.getPracticeLocationData` |

---

## Preconditions — when this step is reached

The step renders **only** when the account-level **Termination Type = "Convert to Non-Par"** on a currently-**participating** vendor account.

| Condition | Step appears? |
|---|---|
| Participating account + "Convert to Non-Par" | **Yes** — this story applies |
| Participating account + "Full-Termination" | No |
| Account already Non-Par (Full-Termination only path) | No |

All **active** practice locations under the vendor are listed (no last-man-standing filter); the data set can be empty, single-page, or paginated (10 rows/page).

---

## Current State (from codebase)

### `prmPracticeLocationForAccountTerm` (LWC)
- **Primary Taxonomy input** is a `lightning-combobox` with `placeholder="Select Primary Taxonomy"` and no default — `prmPracticeLocationForAccountTerm.html` (combobox block).
- **Options** = full taxonomy list mapped from `parsed.Taxonomies` — `prmPracticeLocationForAccountTerm.js` `loadData()`.
- **No pre-selection:** `primaryTaxonomyId: row.primaryTaxonomy || null`, but the Apex payload never returns `primaryTaxonomy`, so every row starts blank.
- **Validation signal:** emits `AllPrimaryTaxonomySelected` (true only when every row has a taxonomy) and `PracticeLocationTaxonomyData` via `omniApplyCallResp`.

### `PRM_GetFacilityDataForVendor` (Apex)
- `getTaxonomies()` returns **all** `CareTaxonomy WHERE IsActive = true AND PRM_DirectoryDisplayException__c = false` — no default flag, no ordering.
- `getHcFacility()` returns all active, non-pending, non-error `HealthcareFacility` for the account; `PracticeLocationData` has **no** taxonomy field.

### `PRM_AccountTerminationForm_English` v9 (OmniScript)
- Step `Select Practice Location Taxonomies` — show rule: `TerminationType = "Convert to Non-Par"`.
- `ErrorForPrimaryTaxonomy` (Set Errors) — blocks Next when `TerminationType = "Convert to Non-Par"` **and** `AllPrimaryTaxonomySelected = false`.
- Submit action `IPAccountTermination` → `PRM_AccountTerminationContainer`, `sendOnlyExtraPayload: true`; the `extraPayload` does **not** include `PracticeLocationTaxonomyData`.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `prmPracticeLocationForAccountTerm.html` | LWC markup | Replace `lightning-combobox` with a searchable typeahead (custom search/autocomplete; reuse the project's taxonomy typeahead pattern if one exists, otherwise filter `taxonomyOptions` client-side as the user types). |
| `prmPracticeLocationForAccountTerm.js` | LWC controller | On `loadData()`, default each row's `primaryTaxonomyId`/`primaryTaxonomyName` to the Internal Medicine taxonomy when the row has no existing taxonomy; pre-set `selectedTaxonomyId` in `openEditModal`; recompute `AllPrimaryTaxonomySelected`/`PracticeLocationTaxonomyData` so the defaulted rows count as selected. |
| `PRM_GetFacilityDataForVendor.cls` | Apex | Identify the Internal Medicine taxonomy server-side and return it (e.g., a `defaultTaxonomyId` in the payload, or stamp each `PracticeLocationData.primaryTaxonomy`). Avoids hardcoding the Id in JS. |
| `PRM_AccountTerminationForm_English` (new version) | OmniScript | Add `PracticeLocationTaxonomyData` to the `IPAccountTermination` `extraPayload` so the selections persist (see Clarification #1 — confirm the backend should apply them). |
| `PRM_GetFacilityDataForVendorTest` | Apex test | Cover default-taxonomy resolution and the empty/no-Internal-Medicine fallback. |

### Internal Medicine resolution (proposed)
Resolve a single `CareTaxonomy` to use as the default (exact record TBD — see Clarification #2), e.g. `SELECT Id, Name FROM CareTaxonomy WHERE Name = 'Internal Medicine' AND IsActive = true AND PRM_DirectoryDisplayException__c = false LIMIT 1`. If not found, fall back to blank (current behavior) rather than erroring.

---

## Acceptance Criteria

**AC-1 — Primary Taxonomy defaults to Internal Medicine for every practice location**

**Given** a PDM Specialist is terminating a participating group and has chosen "Convert to Non-Par",
**When** the "Select Practice Location Taxonomies" step loads the group's active practice locations,
**Then** every practice location row shows **Internal Medicine** pre-selected as its Primary Taxonomy,
**And** the step's Next button is enabled without the specialist editing any row,
**And** no taxonomy-required error is shown.

**AC-2 — Specialist can change the taxonomy via a searchable typeahead**

**Given** a practice location row is defaulted to Internal Medicine,
**When** the specialist opens that row and types part of a taxonomy name in the Primary Taxonomy field,
**Then** the field filters to matching taxonomies as they type and lets them pick one,
**And** the chosen taxonomy replaces Internal Medicine for that location only,
**And** other rows remain defaulted to Internal Medicine.

**AC-3 — Changed selections and defaults are carried into the termination submission**

**Given** the specialist has accepted Internal Medicine for some locations and changed others,
**When** they complete the termination,
**Then** each practice location is converted to non-par with the Primary Taxonomy shown on its row (defaulted or changed),
**And** no location is submitted without a Primary Taxonomy.

**AC-4 — No practice locations to taxonomy-map**

**Given** the terminating group has no active practice locations,
**When** the "Select Practice Location Taxonomies" step loads,
**Then** the specialist sees an empty-state message and can proceed without selecting anything.

**AC-5 — Internal Medicine taxonomy is unavailable**

**Given** an Internal Medicine taxonomy cannot be resolved as an active, directory-displayable taxonomy,
**When** the step loads the practice locations,
**Then** rows load with a blank Primary Taxonomy (no error),
**And** the specialist must select a taxonomy per location before Next is allowed (current safeguard preserved).

**AC-6 — Step still appears only for Convert to Non-Par**

**Given** a vendor termination,
**When** the account-level Termination Type is "Full-Termination" (or the account is already Non-Par),
**Then** the "Select Practice Location Taxonomies" step does not appear and no taxonomy selection is required.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `prmPracticeLocationForAccountTerm.html` | Modified LWC | Combobox → typeahead/autocomplete | Drives AC-2 |
| `prmPracticeLocationForAccountTerm.js` | Modified LWC | Default rows to Internal Medicine; recompute `AllPrimaryTaxonomySelected` & `PracticeLocationTaxonomyData` | Drives AC-1, AC-3, AC-5 |
| `PRM_GetFacilityDataForVendor.cls` | Modified Apex | Return Internal Medicine default (id/name) with payload | Drives AC-1, AC-5 |
| `PRM_AccountTerminationForm_English` | New OS version | Add `PracticeLocationTaxonomyData` to submit payload | Drives AC-3 — pending Clarification #1 |
| `PRM_GetFacilityDataForVendorTest` | Modified test | Default + fallback coverage | — |

---

## Definition of Done

- [ ] Primary Taxonomy renders as a searchable typeahead on the step.
- [ ] Every active practice location defaults to Internal Medicine on load.
- [ ] Defaulted rows satisfy the "all taxonomy selected" gate without manual edits.
- [ ] Changing one row does not affect other rows; changes persist on Save.
- [ ] Selected/defaulted taxonomies reach the backend and are applied on conversion (per Clarification #1).
- [ ] Empty-location and missing-Internal-Medicine fallbacks behave per AC-4/AC-5.
- [ ] Step still hidden for Full-Termination and already-Non-Par accounts.
- [ ] Apex test coverage for default resolution + fallback; LWC Jest updated.
- [ ] Deployed and validated in QA on a group with >10 practice locations.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Today `PracticeLocationTaxonomyData` is collected by the LWC but **not** sent to `PRM_AccountTerminationContainer` (the submit payload omits it). Is the taxonomy supposed to be persisted to the practice location on non-par conversion, or is this step purely a data-quality gate? | Determines whether we must wire the payload + backend update, or only fix UX | Technical / BA |
| 2 | Which exact `CareTaxonomy` record is "Internal Medicine" (Name and/or code)? Several taxonomies can contain "Internal Medicine". | Default correctness | BA / Ops |
| 3 | Should the Internal Medicine default apply to **all** locations, or only locations that don't already have a taxonomy on file? (Note: the Apex currently returns no existing taxonomy at all.) | Default scope | BA |
| 4 | Should the typeahead show the same option set as today (active, directory-displayable taxonomies), or is additional filtering/sorting expected? | Option list scope | BA |
| 5 | Is a single typeahead acceptable, or do they want default Internal Medicine shown inline in the table (no modal) so most locations need zero clicks? | UX scope / effort | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `prmPracticeLocationForAccountTerm` | LWC | HIGH | Core of the change (typeahead + default) |
| `PRM_GetFacilityDataForVendor` | Apex | MEDIUM | Supplies default taxonomy; new query/field |
| `PRM_AccountTerminationForm_English` | OmniScript | MEDIUM | New version if payload wiring needed |
| `PRM_AccountTerminationContainer` / `PRM_AccountTermination_Procedure` | IP | MEDIUM | Only if taxonomy must be persisted (Clarification #1) |
| `CareTaxonomy` | Object | LOW | Read-only reference |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `prmPracticeLocationForAccountTerm` (typeahead) | LWC | L | Replace combobox with searchable input; client-side filter |
| `prmPracticeLocationForAccountTerm` (default + validation recompute) | LWC | M | Pre-select + emit updated state |
| `PRM_GetFacilityDataForVendor` (default resolution) | Apex | M | Query + payload field + test |
| OmniScript payload wiring | OmniScript | M | New version; only if Clarification #1 = persist |
| Backend persistence of taxonomy | IP/Apex | L–XL | Only if not already handled downstream |

**Total Estimated Effort:** ~L–XL (AI-estimated — validate with team). Lands at **L** if this is UX-only; **XL** if taxonomy must also be persisted end-to-end.
