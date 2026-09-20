# PNC Migration — PAR & Application-Review Flows: User Stories

> Authored with the **User Story Solution Architect** (v1.6). Vertical: **Provider Network Management (PNM)**.
> **Source of truth:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` (verified component/line inventory).
> **Parent plan:** `PRM_PNC_Logic_Change_Implementation_Plan.md`. These are the **flow-specific consumer changes** for the App-Review chain; they **depend on** the shared work: **US1** (`HealthcareFacility.PRM_PNC__c` + `Account.PRM_PNCAnyLocation__c`), **US4** (switch-aware rollup helpers), **US5 / US5B** (HealthcareFacility trigger, PPL trigger, switch recompute).

**Business rule being delivered:** PNC (Par Non Cred) moves from the **vendor** (`Account.PRM_PNC__c`) to the **practice location** (`HealthcareFacility.PRM_PNC__c`); a practitioner is PNC only when **all** their active practice locations are PNC (default), or when **any** are, if the practitioner's ALL/ANY switch is on.

**Verified guardrails (do not re-litigate):** OmniScript steps hold **no literal** `Account.PRM_PNC__c` — they bind transformed nodes (`pnc` / `PracLocPNC` / `PractitionerPNC` / `PracPNC`). The **PDA/NMQC `PractitionerPNC` checkbox is the practitioner rollup** (its fetch IP `PRM_FetchFormPDAReviewParent` has zero PNC references). Review/PDA/QC **routing is never PNC-driven**.

**Active versions to build against:** PAR `PRM_PractitionerParticipationForm_English` v98 · `PRM_ReviewRCAT_English` (this is where review-side PNC actually displays — the separate `PRM_PNCReview_English` v8 has **zero** PNC references) · `PRM_PNCPDA_English` v9 · `PRM_PNCQC_English` v6. Line numbers are indicative — confirm against the active version.

---

# USER STORY US-AR1: Source PAR-intake group PNC from the practice location

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScript:** `PRM_PractitionerParticipationForm_English` (v98)
**Integration Procedures:** `PRM_IPExtractGroupNameBasedOnTINNPI`
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` §Flow A; parent US1, US3, US4; `PAR_Form_PNC_Path_User_Stories.md`

---

## Story

**As a** Credentialing Specialist,
**I want** the PNC status shown for a group's practice locations during the Practitioner Participation form to reflect each **practice location's** PNC (not the vendor's single PNC),
**So that** a practitioner I onboard is marked PNC only when their joined locations qualify, and the Case Manager is created with the correct PNC record type.

**Why it matters:** Under the vendor-level flag, every location under a group inherited one PNC value. Location-level PNC lets a group have some PNC and some non-PNC locations, so onboarding decisions and downstream credentialing routing are correct.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| PAR intake | `PRM_PractitionerParticipationForm_English` | `GroupTypeAhead / IPExtractGroupName` → `GroupInformation.pnc` | `PRM_IPExtractGroupNameBasedOnTINNPI` → `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI`; `PRMDRExtractGroupNameBasedOnTINNPIPNC` |
| PAR intake | `PRM_PractitionerParticipationForm_English` | `PractitionerParticipationQuestion5` → `IsPNCGroup` | User intent (no data source) |

---

## Current State (from codebase)

### `PRM_PractitionerParticipationForm_English`
- **`pnc`** (Formula): `IF(%GroupInformation|n:ExistingGroupSelected% == false, false, %GroupInformation|n:pnc%)` — consumes the group PNC returned by the IP. Location: `..._Element_pnc.json`.
- **`IPExtractGroupName`** (Integration Procedure Action): calls `PRM_IPExtractGroupNameBasedOnTINNPI` with `{IsPNC, NPI, TaxId}`, maps response node `Account` into `GroupInformation`. Location: `..._Element_IPExtractGroupName.json`.
- **`IsPNCGroup`** (Formula): `IF(Q5=="Yes",true,false)` — user intent only. Location: `..._Element_IsPNCGroup.json`.

### Data feeds (where vendor PNC is actually read)
- `PRMDRExtractGroupNameBasedOnTINNPIPNC_Items.json:144` → `InputFieldName: Identifier:Account:PRM_PNC__c` (vendor via identifier).
- `PRMDRExtractGroupNameBasedOnTINNPI_Items.json:144`, `PRMExtractGroupNameByTIN_Items.json:144` → same.
- `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI` / `getAccountWrapperData` — puts `PNC` from the group Account.
- `PRM_PARProviderSearch.cls:125,309`; `PRM_ValidateNPIs.cls:132–133,280–281`.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRMDRExtractGroupNameBasedOnTINNPIPNC` | DataRaptor | `Identifier:Account:PRM_PNC__c` (line 144) → practice-location `HealthcareFacility.PRM_PNC__c` |
| `PRMDRExtractGroupNameBasedOnTINNPI` | DataRaptor | Line 144 → location PNC |
| `PRMExtractGroupNameByTIN` | DataRaptor | Line 144 → location PNC |
| `PRM_RecordQueryServiceUtils` | Apex | `getGroupDataForTaxIdNPI`/`getAccountWrapperData` set `PNC` from `HealthcareFacility.PRM_PNC__c` per location |
| `PRM_PARProviderSearch` | Apex | Lines 125, 309 → location PNC |
| `PRM_ValidateNPIs` | Apex | Lines 132–133, 280–281 → `isPNCGroup` reflects location/intent |
| `pnc` / `MSG_PNCGroup` / `SetErrorNonPNCGroup` | OmniScript | Retarget to location PNC; retain ALL default; honor ANY when `PRM_PNCAnyLocation__c = true` (existing practitioner); fix known validation gaps |
| `PRMDRCreateCaseCaseManagerAndAccount` / `…ExistingNPI` | DataRaptor | Keep practitioner-Account write target; value = switch-aware rollup (US4) |

---

## Acceptance Criteria

**AC-1 — Location PNC drives the group search results**

**Given** a Credentialing Specialist searches for a group by NPI or Tax ID on the Practitioner Participation form,
**When** the group's practice locations are returned,
**Then** the PNC status shown for each location reflects that specific practice location,
**And** two locations under the same group can show different PNC values.

**AC-2 — Default rule: all locations must be PNC**

**Given** a new practitioner (whose ALL/ANY switch is off) is being onboarded,
**When** the Credentialing Specialist selects only locations that are all PNC,
**Then** the practitioner is marked PNC and the Case Manager is created with the PNC record type,
**And** if any selected location is not PNC, the practitioner is not marked PNC.

**AC-3 — Override rule: any location makes the practitioner PNC**

**Given** an existing practitioner whose ALL/ANY switch is on,
**When** the Credentialing Specialist selects a mix of PNC and non-PNC locations,
**Then** the practitioner is marked PNC because at least one selected location is PNC.

**AC-4 — No vendor PNC is displayed or used**

**Given** any group whose vendor-level PNC differs from its locations' PNC,
**When** the form displays or evaluates PNC anywhere in intake,
**Then** the value shown and used comes from the practice location, never the vendor.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRMDRExtractGroupNameBasedOnTINNPIPNC` / `…TINNPI` / `PRMExtractGroupNameByTIN` | Modified DataRaptor | `Identifier:Account:PRM_PNC__c` → `HealthcareFacility.PRM_PNC__c` | Drives AC-1, AC-4 |
| `PRM_RecordQueryServiceUtils`, `PRM_PARProviderSearch`, `PRM_ValidateNPIs` | Modified Apex | Source location PNC; apply switch | Drives AC-1–AC-4 |
| `pnc` / `MSG_PNCGroup` / `SetErrorNonPNCGroup` (OmniScript) | Modified elements | Retarget to location PNC | Drives AC-2, AC-3 |
| `PRMDRCreateCaseCaseManagerAndAccount` / `…ExistingNPI` | Modified DataRaptor | Value from US4 rollup; target unchanged | Drives AC-2, AC-3 |

---

## Definition of Done

- [ ] No PAR-path component reads group/vendor `Account.PRM_PNC__c` for a location's PNC (grep clean).
- [ ] ALL default and ANY override both verified on the form.
- [ ] Case Manager PNC record type correct for both branches.
- [ ] Apex ≥85% incl. ALL, ANY, and bulk paths; DR field-maps signed off.
- [ ] Shadow parity vs legacy for IBC and Delegated.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | For a brand-new practitioner (no Account yet), is the ALL/ANY switch ever supplied at intake, or always default (ALL)? | Determines whether intake reads or ignores the switch | BA / Product |
| 2 | Should the group type-ahead still return a group-level PNC summary anywhere, or is PNC strictly per-location now? | UI + DR shape | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMDRExtractGroupNameBasedOnTINNPIPNC` | DataRaptor | HIGH | Primary group PNC source |
| `PRM_RecordQueryServiceUtils` | Apex | HIGH | Feeds type-ahead PNC |
| `PRM_PractitionerParticipationForm_English` | OmniScript | MEDIUM | `pnc` retarget + validation |
| `PRMDRCreateCaseCaseManagerAndAccount` | DataRaptor | MEDIUM | CM record-type value |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| 3 group DataRaptors | DataRaptor field re-point | M each | Field-map sign-off each |
| `PRM_RecordQueryServiceUtils` + 2 Apex | Apex | L | Switch-aware source |
| OmniScript `pnc`/validation | OmniScript elements | M | Retarget + gap fix |
| Write DRs | DataRaptor | M | Value from US4 |

**Total Estimated Effort:** L–XL

---

# USER STORY US-AR2: Re-point RCAT review data feeds to practice-location PNC

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScript:** `PRM_ReviewRCAT_English` (where review PNC displays). **`PRM_PNCReview_English` (v8) has zero PNC references** — regression only, no field edit.
**Integration Procedures:** `PRM_ReviewRCAT` & `PRM_UpdateDataForRCATPNCReview` (invoke the review DataRaptors), `PRM_RecredTerminationLetter` (termination-letter filter)
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` §Flow B; parent US1, US4; gate US-AR5

---

## Story

**As a** Credentialing Specialist reviewing recredentialing terminations (RCAT / PNC Review),
**I want** each practitioner-location row to show PNC from the practice location, and the termination letter to exclude PNC locations by that same source,
**So that** I make review decisions on accurate per-location PNC and PNC locations are never wrongly termed.

**Why it matters:** RCAT decisions and termination letters hinge on PNC. Reading it from the vendor produced one value for all a group's locations; reading it per location makes the review and the letter correct.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source (where PNC is actually read) |
|------|------------|---------------|-------------|
| RCAT review Step 1 & 3 | `PRM_ReviewRCAT_English` | RCAT tables (`CustomLWC1`/`CustomLWC3`); read-only `PNC`/`PNCAndDelegated` display nodes | `PRMGetRelatedDataforPNCAndDelegatedRCATReview` (via IP `PRM_UpdateDataForRCATPNCReview`), `PRMGetRelatedRecordForRCATReview` (via IP `PRM_ReviewRCAT`) |
| RCAT review Step 2 (LMS) | `PRM_ReviewRCAT_English` | Last-Man-Standing table (`CustomLWC2`); `LMSPNC` display node | `PRMGetPLVendorPNCRCAT` ⚠️, `PRM_RCATProcessingHelper` |
| Recred termination letter | — | `FilterHCPFRecords` | `PRM_RecredTerminationLetter` IP |
| _(PNC display container)_ | `PRM_PNCReview_English` | — | **No PNC anywhere — regression only** |

> ⚠️ `PRMGetPLVendorPNCRCAT` and `PRMDRGetFacilityInfoDelegatedPNCReCred` read vendor PNC but have **no confirmed live caller** in the export — classify as active/orphaned in the **US-AR5 gate** before editing.

---

## Current State (from codebase)

**OmniScript layer — no field edit needed (verified):**
- `PRM_PNCReview_English` — a full scan of the folder for `PRM_PNC__c` / `pnc` / `PracLocPNC` / `PractitionerPNC` returns **nothing**. Its elements only run review/routing IPs (`PRM_TransformParDataParent`, `PRM_ValidateCAQHAppReviewParent`, `PRM_PNCRecordsUpdateParent`, `PRM_AddCAQHRecord`, …). **Regression only.**
- `PRM_ReviewRCAT_English` surfaces PNC via **read-only display checkboxes** — `PNC` (`..._Element_PNC.json`, `readOnly:true`, `Type:Checkbox`), `LMSPNC`, `PNCAndDelegated`, `NotLastANDPNCDelegated` — bound to transformed JSON nodes, **not** to `Account.PRM_PNC__c`. Those nodes are produced by the DataRaptors below (via IPs `PRM_ReviewRCAT` and `PRM_UpdateDataForRCATPNCReview`), so the OmniScript needs no re-point.

**DataRaptor / IP layer — the actual `Account.PRM_PNC__c` reads (the re-point target):**
- `PRMGetRelatedDataforPNCAndDelegatedRCATReview_Items.json:28` FILTER `... Account.PRM_PNC__c == false ...` for both affiliation record types; `:113` output `CaseManager:HealthcarePractitionerFacility:Account.PRM_PNC__c`. Invoked by IP `PRM_UpdateDataForRCATPNCReview`.
- `PRMGetRelatedRecordForRCATReview_Items.json:725` `CaseManagers:PractionerPracticeLocation:Account.PRM_PNC__c → PracPNC`. Invoked by IP `PRM_ReviewRCAT`.
- `PRM_RecredTerminationLetter` → `..._Element_FilterHCPFRecords.json:16` filter `'Account:PRM_PNC__c != true'`.
- **Stays:** `PRMGetRelatedRecordForPractitioner_Items.json:761` `CaseManagers:Account.PRM_PNC__c` (practitioner rollup).
- Routing (no change): `SVRecordsToUpdatePDA`, `SVRecordsToUpdatePORNeeded`, `IPPNCRecordsUpdate`.

**Verify caller before editing (defer to US-AR5 gate):**
- `PRMGetPLVendorPNCRCAT_Items.json:4` `IF(%...IsVendorPNC%, ..., IF(%...HCF:Account.PRM_PNC__c% == true,...))` and `PRMDRGetFacilityInfoDelegatedPNCReCred_Items.json:4` `%HCF:Account.PRM_PNC__c%` both read vendor PNC but have **no confirmed live caller** in the export (found only in their own DataPacks — not referenced by any exported OmniScript, IP, or Apex class). Classify as active or orphaned before committing the re-point.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_PNCReview_English` | OmniScript | **No change** — verified zero PNC references (regression only) |
| `PRM_ReviewRCAT_English` (`PNC`/`LMSPNC`/`PNCAndDelegated` elements) | OmniScript | **No change** — read-only display nodes fed by the DRs below; no field reference to re-point |
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview` | DataRaptor | Line 28 FILTER + line 113 output: location branch (`PRM_PractitionerLocationAffiliation`) uses `HealthcareFacility.PRM_PNC__c`; retire/gate the vendor `PRM_PractitionerPracticeAffiliation` branch |
| `PRMGetRelatedRecordForRCATReview` | DataRaptor | Line 725: `PractionerPracticeLocation:Account.PRM_PNC__c` → `…HealthcareFacility.PRM_PNC__c` |
| `PRM_RecredTerminationLetter / FilterHCPFRecords` | IP | Line 16: `'Account:PRM_PNC__c != true'` → `'HealthcareFacility:PRM_PNC__c != true'` |
| `PRMGetPLVendorPNCRCAT` | DataRaptor | Line 4: `HCF:Account.PRM_PNC__c` → `HCF:PRM_PNC__c` — **only if confirmed active (US-AR5 gate)** |
| `PRMDRGetFacilityInfoDelegatedPNCReCred` | DataRaptor | Line 4: `%HCF:Account.PRM_PNC__c%` → `%HCF:PRM_PNC__c%` — **only if confirmed active (US-AR5 gate)** |
| `PRMGetRelatedRecordForPractitioner` (761) | DataRaptor | **No change** — practitioner rollup |

---

## Acceptance Criteria

**AC-1 — RCAT tables show per-location PNC**

**Given** a Credentialing Specialist opens the RCAT review (Steps 1–3),
**When** the practitioner-location rows are displayed,
**Then** each row's PNC reflects that practice location,
**And** locations under the same group can show different PNC values.

**AC-2 — Termination letter excludes PNC locations**

**Given** a recredentialing termination is generated for a practitioner,
**When** the termination letter is produced,
**Then** locations that are PNC at the practice-location level are excluded from the letter,
**And** only non-PNC locations appear.

**AC-3 — Practitioner-level PNC still shown from the rollup**

**Given** the review shows the practitioner's overall PNC,
**When** the row is rendered,
**Then** that value is the practitioner's rolled-up PNC (unchanged behavior),
**And** it is not re-derived from a vendor record.

**AC-4 — Routing to PDA is unchanged**

**Given** the Credentialing Specialist selects "Proceed to PDA",
**When** they submit,
**Then** the case routes to the PDA queue at the "PDA Review and Update" stage exactly as before.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PNCReview_English`, `PRM_ReviewRCAT_English` | Unchanged OmniScript | Display nodes only; no field re-point | AC-1 (regression), AC-3 |
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview` | Modified DataRaptor | Location branch → HCF PNC; retire vendor branch | Drives AC-1 |
| `PRMGetRelatedRecordForRCATReview` | Modified DataRaptor | `PractionerPracticeLocation:Account.PRM_PNC__c` → HCF PNC | Drives AC-1 |
| `PRM_RecredTerminationLetter / FilterHCPFRecords` | Modified IP filter | `Account:PRM_PNC__c` → `HealthcareFacility:PRM_PNC__c` | Drives AC-2 |
| `PRMGetPLVendorPNCRCAT`, `PRMDRGetFacilityInfoDelegatedPNCReCred` | Conditional DataRaptor | `HCF:Account.PRM_PNC__c` → `HCF:PRM_PNC__c` **iff active** | Gated by US-AR5 |
| `PRMGetRelatedRecordForPractitioner` | Unchanged | Practitioner rollup | AC-3 |

---

## Definition of Done

- [ ] Per-DR field-map sign-off (no `HCF:Account.PRM_PNC__c` left in review DRs).
- [ ] Confirmed **zero** OmniScript edits: `PRM_PNCReview_English` (no PNC) and `PRM_ReviewRCAT_English` (display nodes only) unchanged.
- [ ] `PRMGetPLVendorPNCRCAT` / `PRMDRGetFacilityInfoDelegatedPNCReCred` caller-status resolved via US-AR5 (edited only if active).
- [ ] Termination letter excludes PNC locations by the location field.
- [ ] RCAT Steps 1–3 render correct per-location PNC in shadow parity.
- [ ] "Proceed to PDA" routing regression passes.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Is the vendor `PRM_PractitionerPracticeAffiliation` PNC branch retired entirely, or gated during the transition? | Determines filter logic in `PRMGetRelatedDataforPNCAndDelegatedRCATReview` | Technical / BA |
| 2 | Does `IsVendorPNC` remain a meaningful concept after migration, or is it removed from `PRMGetPLVendorPNCRCAT`? | Formula simplification | BA |
| 3 | Are `PRMGetPLVendorPNCRCAT` and `PRMDRGetFacilityInfoDelegatedPNCReCred` still active (they have no exported caller)? If orphaned, they are dropped from scope. | Removes two DRs from the change set | Technical (US-AR5 gate) |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview` | DataRaptor | HIGH | Core RCAT PNC filter/output |
| `PRM_RecredTerminationLetter` | IP | HIGH | Termination letter correctness |
| `PRMGetRelatedRecordForRCATReview` | DataRaptor | MEDIUM | Table display feed |
| `PRMGetPLVendorPNCRCAT` / `PRMDRGetFacilityInfoDelegatedPNCReCred` | DataRaptor | LOW–MEDIUM | Conditional — only if active (US-AR5) |
| `PRM_PNCReview_English` / `PRM_ReviewRCAT_English` | OmniScript | LOW | No change — regression/display nodes only |
| `PRM_ReviewRCAT_English` CustomLWC1/2/3 | LWC | LOW | No code change if payload keys unchanged |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| 2 confirmed review DataRaptors | Field/formula re-point | M each | Sign-off each |
| 2 conditional DataRaptors | Field re-point | M each | Only if active (US-AR5) |
| `FilterHCPFRecords` IP filter | IP element | M | Letter regression |
| OmniScripts (`PRM_PNCReview`, `PRM_ReviewRCAT`) | No change | — | Regression only |
| RCAT display validation | QA | M | Shadow parity |

**Total Estimated Effort:** L

---

# USER STORY US-AR3: Re-point PDA location-PNC feed and rollup write

**Persona:** Provider Data Admin (PDA) Specialist
**Priority:** P0
**OmniScript:** `PRM_PNCPDA_English` (v9)
**Integration Procedures:** `PRM_FetchFormPDAReviewParent` (no change), `PRM_PNCPDAReviewUpdateParent`
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` §Flow C; parent US1, US4

---

## Story

**As a** Provider Data Admin (PDA) Specialist,
**I want** the practice-location PNC shown on the PDA network/practice-location table to come from the practice location, and PDA processing to set the practitioner PNC by the correct rollup rule,
**So that** I review accurate location PNC and PDA never stamps an incorrect practitioner PNC.

**Why it matters:** PDA is the data-authoritative review step. If its location table shows a vendor value, or the batch forces PNC true, the practitioner record leaves PDA wrong and propagates downstream.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Sent to PDA | `PRM_PNCPDA_English` | PPL / network table (`NetworkInfoCodeTableBlock`, `PracLocPNC`) | `PRM_IPUtilityHelper` |
| Sent to PDA | `PRM_PNCPDA_English` | `PractitionerPNC` checkbox (read-only) | practitioner rollup — **no change** |
| Sent to PDA (submit) | `PRM_PNCPDA_English` | PDA processing batch | `PRM_PNCPDABatchHelper` |

---

## Current State (from codebase)

- **Verified:** `IPFetchFormFormPDA` → `PRM_FetchFormPDAReviewParent` and transform `DRTransformPDAReview` contain **no** PNC reference. The `PractitionerPNC` checkbox is `readOnly:true` and practitioner-level.
- `PRM_IPUtilityHelper.cls:153` `facWrapper.PracLocPNC = hcfRecord.Account.PRM_PNC__c;`; `:262` SOQL selects `account.PRM_PNC__c` on `HealthcareFacility`.
- `PRM_PNCPDABatchHelper.cls:229` `acc.PRM_PNC__c = true;` (with SOQL at 209/249).
- Routing (no change): `SetRecordsNtwlMgntQC`, `SetRecordsRebuttal`, `SetRecordsPended`, `SetRecordsErrorsResolved`, `QCReturnToPDA`.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_IPUtilityHelper` | Apex | Line 153 `hcfRecord.Account.PRM_PNC__c` → `hcfRecord.PRM_PNC__c`; line 262 SOQL select `HealthcareFacility.PRM_PNC__c` directly |
| `PRM_PNCPDABatchHelper` | Apex | Line 229: replace unconditional `acc.PRM_PNC__c = true` with switch-aware rollup value (US4); adjust SOQL 209/249 for location-scoped reads |
| `PRM_PNCPDAService` / `PRM_PNCPDABatch` / `PRM_PNCPDAUtility` | Apex | Audit; keep practitioner-rollup writes, re-point any vendor-via-facility read |
| `PractitionerPNC` (checkbox) | OmniScript | **No change** — practitioner rollup display |
| `IPFetchFormFormPDA` / `PRM_FetchFormPDAReviewParent` / `DRTransformPDAReview` | IP/DR | **No change** — verified no PNC reference |

---

## Acceptance Criteria

**AC-1 — PDA location table shows practice-location PNC**

**Given** a Provider Data Admin Specialist opens a case in PDA review,
**When** the practice-location / network table is displayed,
**Then** each location's PNC reflects that practice location,
**And** it does not reflect a single vendor value.

**AC-2 — PDA sets practitioner PNC by the rollup rule**

**Given** the PDA Specialist submits a PDA review that processes the practitioner,
**When** PDA processing runs,
**Then** the practitioner's PNC is set to the rolled-up value from their locations (all-PNC by default, any-PNC when the switch is on),
**And** the practitioner is never blanket-marked PNC regardless of their locations.

**AC-3 — Read-only practitioner PNC checkbox stays correct**

**Given** the practitioner rollup has been computed,
**When** the PDA screen loads,
**Then** the read-only PNC checkbox shows the practitioner's rolled-up PNC with no additional configuration.

**AC-4 — PDA outcomes route unchanged**

**Given** the PDA Specialist selects "Proceed to Network Management QC" (or Rebuttal / Pended / Errors Resolved / Return to PDA),
**When** they submit,
**Then** the case routes exactly as before (no PNC influence on routing).

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_IPUtilityHelper` | Modified Apex | `PracLocPNC` from `HealthcareFacility.PRM_PNC__c` (assignment + SOQL) | Drives AC-1 |
| `PRM_PNCPDABatchHelper` | Modified Apex | Rollup value instead of blanket `true` | Drives AC-2 |
| `PractitionerPNC`, PDA fetch IP/DR | Unchanged | Practitioner rollup; verified no PNC ref | AC-3 |

---

## Definition of Done

- [ ] `PRM_IPUtilityHelper` sources `PracLocPNC` from the location field (assignment + SOQL).
- [ ] `PRM_PNCPDABatchHelper` writes the switch-aware rollup value, never blanket true.
- [ ] PDA location table parity in shadow; read-only checkbox correct after US4.
- [ ] PDA routing regression passes.
- [ ] Apex ≥85% incl. bulk + ALL/ANY.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should PDA ever be able to **override** the computed practitioner PNC, or always defer to the rollup? | Determines whether `:229` keeps any manual-set path | BA / Ops |
| 2 | Do `PRM_PNCPDAService`/`Batch`/`Utility` contain vendor-via-facility reads beyond `:229`? (audit) | Scope of Apex change | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_IPUtilityHelper` | Apex | HIGH | Feeds PDA/QC location PNC table |
| `PRM_PNCPDABatchHelper` | Apex | HIGH | Writes practitioner PNC at PDA |
| `PRM_PNCPDA_English` | OmniScript | LOW | No re-point (verified) |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_IPUtilityHelper` | Apex (assignment + SOQL) | M | Shared with PDM/QC table |
| `PRM_PNCPDABatchHelper` | Apex (rollup value) | L | Uses US4 helpers |
| PDA service/batch audit | Apex | M | Confirm no other vendor reads |

**Total Estimated Effort:** L

---

# USER STORY US-AR4: Validate NMQC PNC after upstream re-points (regression)

**Persona:** Network Management QC Specialist
**Priority:** P1
**OmniScript:** `PRM_PNCQC_English` (v6)
**Integration Procedures:** `PRM_FetchFormPDAReviewParent` (no change)
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` §Flow D; depends on US-AR2, US-AR3, US4, US5, US5B

---

## Story

**As a** Network Management QC Specialist,
**I want** the QC screens and worklist to show correct PNC after the review and PDA feeds are re-pointed,
**So that** QC inherits accurate PNC with no NMQC-specific configuration change.

**Why it matters:** NMQC is the last review gate. It has no PNC field logic of its own, so it must be verified to inherit correct PNC once upstream is fixed — a silent regression here would ship wrong PNC.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| NMQC | `PRM_PNCQC_English` | `PractitionerPNC` checkbox | practitioner rollup (no change) |
| NMQC | `PRM_PNCQC_English` | PPL / network table (`PracLocPNC`) | `PRM_IPUtilityHelper` (fixed in US-AR3) |
| NMQC worklist | — | Case list by stage | `PRM_FetchRecordsForNMQC` (no PNC field) |

---

## Current State (from codebase)

- `PRM_PNCQC_English` uses the same `PractitionerPNC` read-only checkbox and loads via `IPFetchFormFormPDA → PRM_FetchFormPDAReviewParent` (no PNC reference — verified).
- `PRM_FetchRecordsForNMQC` / `PRM_FetchRecordsForNMQCProviderSearch` filter by Case Type/Stage "Network Management QC" — no `PRM_PNC__c`.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_PNCQC_English` | OmniScript | **No change** — inherits corrected feeds |
| `PRM_FetchRecordsForNMQC*` | Apex | **No change** — Type/Stage filter only |

This story is **validation-only**; no metadata changes are expected.

---

## Acceptance Criteria

**AC-1 — QC worklist populates independently of PNC**

**Given** cases have been routed to Network Management QC,
**When** the QC Specialist opens the worklist,
**Then** the worklist populates by case stage/type exactly as before,
**And** it is unaffected by the PNC migration.

**AC-2 — QC practitioner PNC matches the rollup**

**Given** the practitioner rollup has been computed,
**When** the QC Specialist opens a case,
**Then** the read-only PNC checkbox matches the practitioner's rolled-up PNC.

**AC-3 — QC location table matches practice-location PNC**

**Given** a case with locations of differing PNC,
**When** the QC location/network table is displayed,
**Then** each location's PNC matches the practice location value (as fixed in US-AR3).

**AC-4 — QC↔PDA routing unchanged**

**Given** the QC Specialist completes QC or returns the case to PDA,
**When** they submit,
**Then** the case routes exactly as before.

---

## Technical Implementation (high-level)

- No NMQC metadata change. Verification depends on US-AR2 (review DRs), US-AR3 (`PRM_IPUtilityHelper`), and US4/US5/US5B (rollup + triggers).
- Regression suite: worklist population, `PractitionerPNC` value, location-table PNC, routing.

---

## Definition of Done

- [ ] NMQC regression suite green (worklist, PNC display, routing).
- [ ] Shadow parity of QC PNC display vs legacy for IBC and Delegated.
- [ ] Confirmed: zero NMQC metadata changes required.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Are there QC-only reports or list views that display PNC and read a vendor field directly? | Could add a hidden change to this story | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PNCQC_English` | OmniScript | LOW | Inherits corrected feeds |
| `PRM_FetchRecordsForNMQC*` | Apex | LOW | No PNC dependency |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| NMQC regression | QA validation | M | Depends on AR2/AR3 |

**Total Estimated Effort:** M

---

# USER STORY US-AR5: Classify ambiguous `Account` PNC reads before re-pointing

**Persona:** Credentialing Specialist (with BA/Developer, acting as data steward)
**Priority:** P1 (gate for US-AR2)
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md` §0.1 "Confirm-scope"; parent US1

---

## Story

**As a** Credentialing Specialist,
**I want** the project to correctly classify each remaining PNC read whose account could be a vendor or a practitioner,
**So that** I never see a wrong PNC because a vendor read was missed or a practitioner (rollup) read was changed by mistake.

**Why it matters:** A handful of `Account.PRM_PNC__c` reads are ambiguous. Re-pointing a practitioner-rollup read, or missing a vendor read, both produce visibly wrong PNC in review screens.

---

## Preconditions

Applies only to reads where the `Account` relationship could resolve to either a vendor/group account or a practitioner person account.

---

## Current State (from codebase)

- `PRMExtractCaseDetails_Items.json:1424` `Case:Account.PRM_PNC__c`.
- `PRMDRSearchBasedOnAccount_Items.json:77,188` `Account:PRM_PNC__c`.
- `PRMDRSearchBasedOnNPITINAccount_Items.json:101,234` `Account:PRM_PNC__c`.

---

## Technical Section (For Developers)

Classify each read as **vendor → change to `HealthcareFacility.PRM_PNC__c`** or **practitioner rollup → keep**. Fold vendor items into US-AR2 (or the relevant flow story) with a field-map entry; document practitioner items as intentionally unchanged.

---

## Acceptance Criteria

**AC-1 — Every ambiguous read is classified**

**Given** the three ambiguous PNC reads,
**When** the team reviews each one's account relationship,
**Then** each is labeled either "vendor — re-point" or "practitioner — keep",
**And** the rationale is recorded.

**AC-2 — Vendor items are scheduled; practitioner items are documented**

**Given** the classification is complete,
**When** the results are recorded,
**Then** vendor-classified reads have a field-map entry in the owning flow story,
**And** practitioner-classified reads are documented as intentionally unchanged (no accidental re-point).

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRMExtractCaseDetails` (1424) | Classification | Vendor→change / practitioner→keep | Depends on case type |
| `PRMDRSearchBasedOnAccount` (77,188) | Classification | Per usage | Search DR |
| `PRMDRSearchBasedOnNPITINAccount` (101,234) | Classification | Per usage | Search DR |

---

## Definition of Done

- [ ] All three reads classified with rationale.
- [ ] Vendor items added to the owning flow story's field-map; practitioner items documented as no-change.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | For `PRMExtractCaseDetails`, can the case's Account ever be a group/vendor, or only a practitioner? | Decides change vs keep | BA |
| 2 | In the search DRs, is `Account` the searched group or the practitioner result? | Decides change vs keep | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMExtractCaseDetails` | DataRaptor | MEDIUM | Case-detail PNC display |
| `PRMDRSearchBasedOnAccount` / `…NPITINAccount` | DataRaptor | LOW–MEDIUM | Search results PNC |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Classification spike | Analysis | S–M | 3 reads |
| Any resulting re-points | DataRaptor | M | Folded into owning story |

**Total Estimated Effort:** M

---

## Epic Summary & Dependency Order

| Story | Persona | Scope | Change type | Depends on |
|-------|---------|-------|-------------|------------|
| **US-AR5** | Credentialing Specialist (data steward) | Classify ambiguous `Account` reads | Analysis gate | US1 |
| **US-AR1** | Credentialing Specialist | PAR intake group PNC source | DR + Apex + OmniScript | US1, US4 |
| **US-AR2** | Credentialing Specialist | RCAT review feeds (`PRM_ReviewRCAT_English`; `PRM_PNCReview_English` = no PNC) | DR + IP filter (no OmniScript edit) | US1, US4, US-AR5 |
| **US-AR3** | Provider Data Admin (PDA) Specialist | Sent to PDA feed + rollup write | Apex | US1, US4 |
| **US-AR4** | Network Management QC Specialist | NMQC | Regression only | US-AR2, US-AR3, US4/5/5B |

**Owned elsewhere (not in these stories):** rollup engine (US4), triggers (US5/US5B), field + switch creation (US1), vendor-PNC deprecation (US11), PDM "Add/Remove PNC" write flow (implementation plan US5 §5.3).

---

## Post-Generation Offers

- **QTA test bridge:** each story's Pattern-A ACs can be converted to QTA browser-automation prompts (PAR form, RCAT review, PDA, QC). Say the word and I'll generate `qta_test_prompts.md`.
- **GUS work items:** I can draft GUS work items (Story → Description, ACs → Acceptance_Criteria__c, Priority, persona → team context) if you have GUS CLI access.
- **Diagram:** I can produce an end-to-end epic dependency diagram (AR5 → AR1/AR2/AR3 → AR4) if a diagram tool is configured.
