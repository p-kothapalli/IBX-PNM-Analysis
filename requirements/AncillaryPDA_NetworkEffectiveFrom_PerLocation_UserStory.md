# USER STORY: Ancillary PDA — Editable Network Effective From Date per Practice Location

**Persona:** PDA Specialist (Ancillary)
**Priority:** P1
**OmniScript:** `PRM_AncillaryPDA_English` (active version 5 — API name `AncillaryPDA`)
**Integration Procedures:** `PRM_AncillaryPDAParent` → `PRM_AncillaryPDA` (active version 10); `PRM_PrepareAncillaryPLNetworkParent` → `PRM_PrepareAncillaryPLNetwork`
**DataRaptors:** `PRMLoadPLNetworkInfoCode`, `PRMTransformAncillaryPDAUpdate`, `PRMUpdateNetworkInfoCodeAncillary`
**Affected Step:** `PracticeLocationsAttributes` ("Assign Practice Locations Attributes") → Edit Block `PracticeLocations`
**Relevant Requirements:** `requirements/SOQL/2026-06-03_AncillaryNPIHistoryEffectiveFrom.md`, `requirements/P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md`

---

## Story

**As a** PDA Specialist (Ancillary),
**I want** to edit the network effective-from date for each practice location on the "Assign Practice Locations Attributes" step — once for all locations when they share a date, or individually when they differ —
**So that** a practice location's network participation can start on a date that differs from the HACAC decision date, without changing the effective dates on any other record in the case.

**Why it matters:** Today the network (HealthcareFacilityNetwork) effective-from date is hard-set to the HACAC decision date for every location. Business needs network participation to be back- or forward-dated per location (e.g., contract effective dates that pre/post-date the committee decision) while the account, taxonomy, provider/NPI, and info-code records continue to use the HACAC date. Without this, PDA has to raise data-fix tickets after the case closes.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Ancillary PDA | `PRM_AncillaryPDA_English_5` | `PracticeLocationsAttributes` (Edit Block `PracticeLocations`) | Edit-block input → `DRTransformAncillaryPDAUpdate` / list-merge → `DRLoadPLNetworkInfoCode` (`PRMLoadPLNetworkInfoCode`) |

**In scope:** the effective-from date written to `HealthcareFacilityNetwork` (PLNetwork) records created/updated by the PDA flow.
**Out of scope:** effective-from / effective-date on `Account`, `HealthcareProviderTaxonomy`, `HealthcareProviderNpi`, `HealthcareProvider`, and `PRM_InfoCodeAssignment__c` — these continue to use the HACAC decision date.

---

## Current State (from codebase)

### 1. OmniScript step `PracticeLocationsAttributes` ("Assign Practice Locations Attributes")

- **Type:** Step (sequence 5), `validationRequired: true`, `allowSaveForLater: true`.
- **File:** `force-app/main/default/omniScripts/PRM_AncillaryPDA_English_5.os-meta.xml` (lines ~2051–2102).
- Contains a single **Edit Block `PracticeLocations`** (`type: Edit Block`, `selectMode: Multi`, `allowEdit: true`, `allowNew: false`, `allowDelete: false`, `editLabel: "View More"`, `maxDisplay: 6`). This is the "Practice Locations" grid + the per-location detail popup shown to the user.

### 2. Edit Block `PracticeLocations` — detail (popup) fields (level 2 children)

| Element | Type | Behavior today | Notes |
|---|---|---|---|
| `PracticeLocationName` | Text | Read-only | Display only (grid + popup) |
| `PracticeLocationType` | Text | Read-only | Primary;Billing;Mailing etc. |
| `PracticeLocationCity` | Text | Read-only | |
| `PracticeLocationState` | Text | Read-only | |
| `PracticeLocationCounty` | Text | Read-only | |
| `PracticeLocationDirectory` | Radio (Yes/No) | Editable, required | "Practice Location Show in Directory" |
| `AncillaryAddNetwork` | Text Block w/ `lwcComponentOverride: prmMultiSelectEditBlock` | Networks multi-select, required | Stores `SelectedNetworks` |
| `AncillaryAddInfoCodes` | Text Block w/ `lwcComponentOverride: prmMultiSelectEditBlock` | Info Codes multi-select | Stores `SelectedInfoCodes` |
| `Billing_Type` | Multi-select (`HealthcareFacility.PRM_BillingType__c`) | Editable, required | UB / 1500 |
| `PLAAddressId` / `PLALocationId` / `PLAPracticeLocationId` | Text | Hidden | Keys for save (`AddressId`, `LocationId`, `PracticeLocationId`) |
| `SelectedNetworksHidden` | Text | Hidden | Validation guard ("ensure Networks selected") |

**There is no effective-from date field in this edit block today.** This is the gap.

### 3. Custom LWC `prmMultiSelectEditBlock`

- File: `force-app/main/default/lwc/prmMultiSelectEditBlock/prmMultiSelectEditBlock.js`.
- For node `AncillaryAddNetwork` → `stepname='PracticeLocationsAttributes'`, `blockName='PracticeLocations'`, `label='SelectedNetworks'`, `requiredastrik=true`; for `AncillaryAddInfoCodes` → `label='SelectedInfoCodes'`.
- Both branches set `disabled = (flowType === 'Network Management QC')`. The PDA case is created as Type **"Network Management QC"**, so the network/info-code pickers render **read-only** in the PDA step today. (A new date field must therefore manage its own enable/disable independently — see Clarification Q4.)

### 4. How effective dates are set today (active IP `PRM_AncillaryPDA_Procedure_10`)

- DataRaptor Post Action **`DRLoadPLNetworkInfoCode`** (bundle `PRMLoadPLNetworkInfoCode`, sequence 17) `additionalInput`:
  - `"PLNetwork:EffectiveFrom" : "=%HACACDecisionDate%"`  ← **hard-set to HACAC for every location/network**
  - `"PLNetwork:Active" : "=%HACACDecisionDate% <= TODAY()"`
  - `"InfoCodeAssign:EffectiveFrom" : "=%HACACDecisionDate%"`
  - `"InfoCodeAssign:Active" : "=%HACACDecisionDate% <= TODAY()"`
- The PLNetwork list fed into this load comes from `=%LAPLNetworkFinal%`, built by the list-merge chain (`LAFacilityNetwork` merges `PLNetworkDirectoryIndicators:PLNetwork` + `SVFacilityNetworks:PLTaxonomy`; keyed by `PLNetworkPracLocId` / `PracticeLocationId`).
- DataRaptor **`PRMLoadPLNetworkInfoCode_1`** maps `HealthcareFacilityNetwork.EffectiveFrom` from the formula `PLNetwork:EffectiveFromFormula = IF(ExistingRecord==true && ExistingActive==true, NULL, %PLNetwork:EffectiveFrom%)`.
- The same IP sets every **other** record's date to HACAC: `Account` EffectiveFrom, `HPTaxonomy:EffectiveDate`, `NPI:EffectiveDate`, `HealthcareProvider:EffectiveDate`, `InfoCodeAssign:EffectiveFrom` all `=%HACACDecisionDate%`.

### 5. Existing date validation / date logic in the flow (grounding for AC-6)

- **OmniScript — `HacacDateCheck`** (Step `PDAOutcomeStep`): `IF(%Account:PRM_EffectiveFrom__c% == null, false, IF(%Account:PRM_EffectiveFrom__c% > %CaseManager:HACACDecisionDate%, true, false))` → error *"The Hacac Decision Date cannot be earlier than the Account Effective From Date."* Establishes: **Account effective-from ≤ HACAC decision date**.
- **DataRaptor — `PRMUpdateNetworkInfoCodeAncillary`** (term/removed-network loader): computes `1DayPriorHACACDate = ADDDAY(%HACACDecisionDate%, -1)` and flags `Error = IF(ISBLANK(ExistingEffectiveFrom) || ExistingEffectiveFrom >= 1DayPriorHACACDate, true, false)`, with `Active = IF(Error, false, IF(ExistingEffectiveFrom <= TODAY() && EffectiveToFormula > TODAY(), true, false))`. Establishes the precedent that **a network's effective-from is validated against the HACAC date** before its active/term state is computed.
- **NPI History defer logic** (`PRMUptLocationHistoryNPIForAncillary_1`, `Ancillary_NPIHistory_EffectiveFrom_Fix_DevStory.md`): for new ancillary records the practice-location / network effective-from is stamped to the **HACAC decision date** (`IF(ISBLANK(EffectiveFrom), HACACDecisionDate, EffectiveFrom)`). Confirms **HACAC decision date = practice location effective-from** for these new records.

**Resulting date hierarchy the new field must honor:**

```
Account Effective From  ≤  HACAC Decision Date ( = Practice Location Effective From )  ≤  Network Effective From (PDA-entered)
```

The new per-location "Network Effective From" sits at the **right end** of this chain: it defaults to the HACAC date and may move forward (later) but never earlier than the HACAC date / practice location effective-from. See AC-6.

---

## Acceptance Criteria

**AC-1 — A network effective-from date is shown for every practice location, defaulted to the HACAC date**

**Given** a PDA Specialist opens the "Assign Practice Locations Attributes" step for an Ancillary case that has one or more practice locations,
**When** the step loads,
**Then** each practice location shows an editable "Network Effective From" date,
**And** each date defaults to the case's HACAC decision date,
**And** if the specialist makes no change, every network record is saved with the HACAC decision date exactly as it is today.

**AC-2 — Apply one effective-from date to all locations at once**

**Given** a PDA Specialist is on the step with multiple practice locations that should all share the same network effective-from date,
**When** they enter a date in the "Apply to all locations" date control and choose Apply,
**Then** the "Network Effective From" date on every location is set to that date,
**And** the specialist can still override any individual location afterward.

**AC-3 — Set a different effective-from date per location**

**Given** a PDA Specialist is on the step with multiple practice locations that need different network effective-from dates,
**When** they edit the "Network Effective From" date on an individual location,
**Then** only that location's date changes,
**And** the other locations keep their existing (defaulted or applied) dates.

**AC-4 — Only network records use the edited date; all other records keep the HACAC date**

**Given** a PDA Specialist has changed the network effective-from date for one or more locations and completes the step,
**When** the case is saved,
**Then** the network (Healthcare Facility Network) records for each location are saved with that location's entered date,
**And** the account, taxonomy, provider/NPI, and info-code records for the same case are still saved with the HACAC decision date,
**And** a network record's Active status reflects its own effective-from date (Active when the entered date is today or earlier).

**AC-5 — Edited date defaults are not lost on revisit / save-for-later**

**Given** a PDA Specialist entered per-location dates and used "Save for later" (or navigated Previous/Next),
**When** they return to the "Assign Practice Locations Attributes" step,
**Then** each location still shows the date they entered (not reset to the HACAC date).

**AC-6 — Reject a network effective-from date that is earlier than the HACAC decision date**

> **The rule:** the network effective-from date a PDA Specialist enters for a location **cannot be earlier than the HACAC decision date** for the case. The HACAC decision date is the credentialing window start and equals the practice location's effective-from date for these records, so this is the same as saying *the network effective-from cannot be before the practice location effective-from*. The date may equal the HACAC date (the default) or be later; it may never be earlier. This mirrors the existing guardrail already in the flow — `HacacDateCheck` blocks a HACAC date earlier than the Account effective-from — extending the same "no record may start before the credentialing date" principle to the network date the PDA team now controls.

**Given** a PDA Specialist enters a network effective-from date for a practice location that is **earlier than the HACAC decision date** (i.e., earlier than the practice location effective-from),
**When** they try to advance past the "Assign Practice Locations Attributes" step (or save for later),
**Then** the step is blocked with a clear inline message that names the offending location and both dates:
> *"Network Effective From for {Practice Location Name} ({MM-DD-YYYY}) cannot be earlier than the HACAC Decision Date ({MM-DD-YYYY}). Enter a date on or after the HACAC Decision Date."*
**And** no network or other records are saved until every location's date is on or after the HACAC decision date.

**AC-6 date-validation scenarios** (HACAC Decision Date = practice location effective-from = **06-25-2026** in the examples):

| # | Entered "Network Effective From" | Result | Message shown |
|---|---|---|---|
| 6a | (left blank / untouched) | **Accept** — defaults to HACAC date 06-25-2026; saved as today's behavior | none |
| 6b | 06-25-2026 (equals HACAC date) | **Accept** — network effective-from = 06-25-2026; Active if ≤ today | none |
| 6c | 07-15-2026 (after HACAC date) | **Accept** — forward-dated; network effective-from = 07-15-2026; network is Pending/Inactive until that date | none |
| 6d | 06-24-2026 (one day before HACAC date) | **Reject** — block step | "Network Effective From for {Location} (06-24-2026) cannot be earlier than the HACAC Decision Date (06-25-2026)…" |
| 6e | 01-01-2026 (well before HACAC date) | **Reject** — block step | same message as 6d with the entered date |
| 6f | Multi-location "Apply to all" of 06-20-2026 where HACAC = 06-25-2026 | **Reject** — block step; every location flagged | message lists each violating location (or a step-level summary) |
| 6g | Multi-location: Loc A = 06-25-2026 (valid), Loc B = 06-10-2026 (invalid) | **Reject** — block step; only Loc B flagged | message names Loc B only; Loc A is unaffected |
| 6h | A non-date / malformed value | **Reject** — standard required/format validation on the date field | OmniStudio field-level "Enter a valid date" |

**AC-6.1 — HACAC date itself still cannot precede the Account effective-from (existing rule preserved)**

**Given** the case's HACAC decision date is earlier than the Account effective-from date,
**When** the PDA Specialist reaches the outcome/validation point,
**Then** the existing `HacacDateCheck` block fires ("The Hacac Decision Date cannot be earlier than the Account Effective From Date.") exactly as today,
**And** the new per-location network date validation does not replace or suppress it.

**AC-7 — Field-level access (Pattern C)**

- **`PRM_DataModifyAll`, `PRM_ProviderDataAdmin` (and the PDA/Network-Mgmt-QC permission set used by the PDA team):**
  - Field level: Read and Edit on any new field introduced to capture the per-location network effective-from date.
- **`PRM_DataViewAll`, `PRM_NetworkManagementQC`:**
  - Field level: Read on the new field.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_AncillaryPDA_English` (Edit Block `PracticeLocations`) | New OmniScript Date element | Add editable `NetworkEffectiveFrom` (Date) to the edit-block detail; default = `%CaseManager:HACACDecisionDate%`. Carry value on each row alongside `PLAPracticeLocationId`. | Drives AC-1, AC-3, AC-5 |
| `PRM_AncillaryPDA_English` (step `PracticeLocationsAttributes`) | New OmniScript elements | Add an "Apply to all locations" Date + action (Set Values / small LWC) that writes the date into each `PracticeLocations` row. | Drives AC-2 |
| `PRM_AncillaryPDA_English` (validation) | New Formula(s) + error block | Per-location rule **`NetworkEffectiveFrom >= HACACDecisionDate`**, mirroring the existing `HacacDateCheck` pattern. Formula e.g. `IF(ISBLANK(%NetworkEffectiveFrom%), false, %NetworkEffectiveFrom% < %CaseManager:HACACDecisionDate%)`; show the AC-6 error block when true and gate Next. Must name the violating location(s). | Drives AC-6, AC-6.1 |
| `PRMTransformAncillaryPDAUpdate` / list-merge (`LAFacilityNetwork`, `LANewPLNetworks`) | Modified DR/merge | Propagate each location's `NetworkEffectiveFrom` onto its matching PLNetwork rows by `PracticeLocationId`. | Drives AC-4 |
| `PRM_AncillaryPDA_Procedure_10` → `DRLoadPLNetworkInfoCode` | Modified IP step | Stop hard-coding `PLNetwork:EffectiveFrom = %HACACDecisionDate%`; pass per-row date through and fall back to HACAC when blank. Recompute `PLNetwork:Active` from the row's effective-from. Leave `InfoCodeAssign:*` and all other records on `%HACACDecisionDate%`. | Drives AC-4 |
| `PRMLoadPLNetworkInfoCode` (DataRaptor) | Modified DR formula | Compute `HealthcareFacilityNetwork.EffectiveFrom` from row date with HACAC fallback: `IF(ISBLANK(rowDate), HACACDecisionDate, rowDate)`; recompute Active accordingly. (DR already receives `HACACDecisionDate`.) | Per-row logic belongs in DR, not the list-level action input |
| Permission sets | FLS update | Read/Edit on the new field per AC-7. | Drives AC-7 |

> Design note: because the IP DataRaptor Post Action `additionalInput` applies one formula to the whole PLNetwork list, the per-row date must travel **on each PLNetwork row** (set during transform/merge) and the HACAC-fallback must be evaluated **inside `PRMLoadPLNetworkInfoCode`**, not in the action input. A deeper design doc can live in `requirements/Enhancements/` if needed.

---

## Recommended UX (single vs. per-location dates)

- **Top of step — "Apply to all locations":** one date picker + Apply button. Fastest path when every location shares one date (AC-2).
- **Per-location override:** a "Network Effective From" date inside each location's "View More" detail popup (next to Networks / Billing Type), pre-filled with the HACAC date and overridable (AC-1, AC-3).
- **Optional grid column:** surface the chosen date as a read-only column in the `PracticeLocations` grid so the specialist can confirm all locations at a glance before Next.
- **Safe default:** every location starts at the HACAC date, so doing nothing reproduces today's behavior exactly (AC-1).

---

## Definition of Done

- [ ] New per-location "Network Effective From" date appears in the `PracticeLocations` edit block, defaulted to the HACAC date.
- [ ] "Apply to all locations" sets every location's date; individual overrides work and persist across Previous/Next and Save-for-later.
- [ ] On save, `HealthcareFacilityNetwork` records use the per-location date; `Account`, taxonomy, NPI/provider, and `PRM_InfoCodeAssignment__c` records still use the HACAC date.
- [ ] Network Active flag derives from the per-location date.
- [ ] Invalid dates are blocked with a clear, location-specific message; nothing saves until corrected.
- [ ] FLS updated on the relevant permission sets.
- [ ] Regression: a case where the specialist changes nothing produces byte-for-byte the same records as today.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the persona/role label — "PDA team" vs. an existing role (Ancillary Cred Specialist / PDM Specialist / Network Management QC Specialist). | Permission-set targeting, story header | Product / Ops |
| 2 | **Lower bound RESOLVED** — network effective-from cannot be earlier than the HACAC decision date (= practice location effective-from); see AC-6. **Still open:** is there an **upper bound** on forward-dating (e.g., cannot exceed the network/account `EffectiveTo`, or a max N days/months past HACAC)? | AC-6 validation logic (max-date rule) | BA / Ops |
| 3 | Should the per-location date also affect `EffectiveTo`/term recalculation for existing active network records, or only `EffectiveFrom` on new/updated networks? | Scope of DR change (`PRMLoadPLNetworkInfoCode` EffectiveTo logic) | BA / Technical |
| 4 | Networks/Info-code pickers are disabled when `flowType = 'Network Management QC'` (the PDA case type). Should the new date field be editable for the PDA team in this state? | Field enable/disable + permission gating | Technical / Product |
| 5 | Does the editable date apply to **all** network rows of a location, or only to networks added/changed during this PDA cycle (not pre-existing active ones)? | Merge/transform row-targeting | BA / Technical |
| 6 | Should info-code assignment effective-from ever follow the network date, or always stay on HACAC? (Story currently assumes info-codes stay on HACAC.) | AC-4 boundary | BA |
| 7 | Is "Apply to all" expected to also re-apply to locations the user already overrode (overwrite) or skip them? | AC-2/AC-3 interaction | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_AncillaryPDA_English` | OmniScript | HIGH | New element(s) in `PracticeLocations` edit block + step-level apply-all control + validation |
| `PRM_AncillaryPDA_Procedure` | Integration Procedure | HIGH | `DRLoadPLNetworkInfoCode` effective-from/Active logic change (new version) |
| `PRMLoadPLNetworkInfoCode` | DataRaptor (Load) | HIGH | Per-row EffectiveFrom + Active with HACAC fallback |
| `PRMTransformAncillaryPDAUpdate` / list-merges | DataRaptor / IP merge | MEDIUM | Propagate per-location date onto PLNetwork rows |
| `prmMultiSelectEditBlock` | LWC | LOW–MEDIUM | Only if the apply-all/date interaction is built as/near this custom edit block |
| Permission sets | Metadata | LOW | FLS for the new field |
| `HealthcareFacilityNetwork` | Object | MEDIUM | Effective-from values diverge from HACAC for ancillary networks (reporting/QC awareness) |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PracticeLocations` edit-block date field + default | OmniScript element | M | Date element + default formula |
| "Apply to all locations" control + write-to-rows | OmniScript + small LWC/Set Values | L | UX convenience; per-row write |
| Per-location date validation | OmniScript Formula + error block | M | Mirror `HacacDateCheck` |
| Propagate date onto PLNetwork rows | DR Transform / list-merge | M | Key by `PracticeLocationId` |
| `DRLoadPLNetworkInfoCode` / `PRMLoadPLNetworkInfoCode` change | IP step + DataRaptor | L | New IP + DR versions, fallback + Active recompute |
| Permission-set FLS | Config | S | New field access |
| Regression + QA across single/multi-location, save-for-later | Test | L | Includes "no change = HACAC" regression |

**Total Estimated Effort:** ~L–XL (roughly 2–3 days) — *AI-estimated, validate with team.*
