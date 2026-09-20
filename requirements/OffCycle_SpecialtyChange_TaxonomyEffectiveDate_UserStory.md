# USER STORY: Off-Cycle Specialty (Taxonomy) Change — Capture, Validate & Stamp "Taxonomy Effective Date" (Level 4)

**Persona:** Credentialing Specialist (primary); Provider Data Admin (PDA) Specialist and Network Management QC Specialist (downstream review personas)
**Priority:** P1
**OmniScript:** `PRM_OffCycleCredentialing_English` (capture), `PRM_OffCyclePDAReview_English` (PDA update), `PRM_OffCycleQCReview_English` (QC review)
**Integration Procedures:** `PRM_SpecialtyPractitionerPracticeLocation` (specialty-change save), `PRM_FetchCareTaxonomyProviderTypes`, `PRM_ProcessPracticeLocationTaxonomyData`
**Relevant Requirements:**
- `requirements/OffCycle_RoleChange_RoleEffectiveDate_UserStory.md` (sibling story — Role Effective Date; same pattern)
- `requirements/RoleChange_EntryPoints_Analysis_RoleEffectiveDate.md`
- `requirements/PatientAcceptStatus_Level4_EffectiveDate_Calculation_Analysis.md` (pattern being mirrored)
- `requirements/Concierge_Off_Cycle_End_to_End_User_Stories.md` (off-cycle flow parity)
- `requirements/Enhancements/PNM_OffCycle_Process_Apex_Service_Architecture.md`

---

## Story

**As a** Credentialing Specialist processing an off-cycle **Specialty Change** (taxonomy add / change / remove),
**I want** to capture a **Taxonomy Effective Date** for the specialty update, have it validated against the practitioner's and practice location's effective dates, and have it stamped onto the affected Level 4 taxonomy records so a removed specialty is terminated and an added specialty begins on the correct date,
**So that** downstream PDA and QC reviewers, network loads, and reporting reflect *when* a practitioner's taxonomy started and stopped at each practice location — instead of the Level 4 Taxonomy Effective From/To fields sitting empty and silently defaulting to the network's generic effective dates.

**Why it matters:** The dedicated Level 4 fields `PRM_TaxonomyEffectiveFrom__c` / `PRM_TaxonomyEffectiveTo__c` (and their already-built *Calculated* formula fields) exist but have **no writer today** — no off-cycle path stamps them. The Specialty Change flow currently reuses the single "Effective Date" field (`RoleChangeDate`) that was built for Role Change, and its date validation is only partially wired (the validation remote action does not pass the specialty data). This story gives Specialty Change its own effective-date capture, validation, and Level 4 stamping, exactly parallel to the Role Effective Date story.

---

## Scope

| Flow | OmniScript | Affected Step(s) | Persona | This story does |
|---|---|---|---|---|
| Off-Cycle Credentialing | `PRM_OffCycleCredentialing_English` | Collect And Verify New Information (Specialty Change block); Correspondence | Credentialing Specialist | Capture Taxonomy Effective Date; validate; show read-only per-location Taxonomy Effective From/To; stamp L4 taxonomy records on complete |
| Off-Cycle PDA Review | `PRM_OffCyclePDAReview_English` | Specialty / Taxonomy review step | PDA Specialist | Show read-only Taxonomy Effective From/To; allow network add/remove with correct network Effective From/To dating |
| Off-Cycle QC Review | `PRM_OffCycleQCReview_English` | Specialty / Taxonomy review step | QC Specialist | Show read-only Taxonomy Effective From/To; complete the QC flow |
| Off-Cycle — other request types | all three | all | all | **Regression only** — Role Change, Name Change, New Region, New State must continue to work unchanged |

**In scope:** Off-Cycle **Specialty Change** request type only, immediate (non-future-dated) effect, Level 4 taxonomy record stamping via the **clone-new + terminate-old** pattern (mirroring Patient Accept Status / `PRM_PASUpdateBatch` — the clone preserves the old network Effective From and copies the other effective-from dates; add net-new specialty = create directly; remove specialty = terminate record).
**Out of scope (this story):** future-dated taxonomy processing (FDP), Role Effective From/To (sibling story), the "Is Primary Taxonomy" reassignment rules beyond carrying the flag, and specialty changes originating from Intake / PDM Manual Update / ReCred.

---

## Current State (verified in active build)

| Item | Current behavior | Location |
|---|---|---|
| Off-Cycle request types | Role Change, **Specialty Change**, Name Change, New Region, New State | `PRM_OffCycleCredentialing_English` v62, `SelectOffCycleChanges` step |
| Specialty capture UI | `SpecialityChangeBlock` (label "Specialty Change"), `PractitionerWithSpecialty` ("Practitioner at Practice Location Taxonomy"), `AddSpecialty` / `SpecialityAddBlock`, `IsPrimaryTaxonomy` flag — shown only when *Specialty Change* is selected | `CollectAndVerifyNewInformation` step |
| Taxonomy Effective Date field | **None dedicated.** The single Date element `RoleChangeDate` (label "Effective Date") is the only captured effective date, and it is gated on *Role Change*, not *Specialty Change* | `CollectAndVerifyNewInformation` step |
| Validation | `PRM_EffectiveDateValidationForOffcycle.validateSpecialityChangeRequest` **exists** (reads `SpecialityData` → `FacilityId`, runs the lower-bound cascade) but the only `checkDateValidation` remote action (`CheckEffDateValForRoleChange`) passes `RoleChangeData` + `EffectiveDate = RoleChangeDate`, **not** `SpecialityData` — so specialty validation is not fully wired | `PRM_EffectiveDateValidationForOffcycle.cls`, `CheckEffDateValForRoleChange` element |
| Save path | `PRM_SpecialtyPractitionerPracticeLocation` (element `IPSpecialtyPractitionerPracticeLocation`, sends the `CollectAndVerifyNewInformation` node) → off-cycle taxonomy DataRaptors | `IPSpecialtyPractitionerPracticeLocation` element |
| **Gap** | No Taxonomy Effective Date input; specialty validation not fully wired (no `SpecialityData`, lower-bound only); `PRM_TaxonomyEffectiveFrom__c` / `PRM_TaxonomyEffectiveTo__c` **never written**; dates not shown read-only downstream | — |

---

## Acceptance Criteria

### AC1 — Credentialing: capture the Taxonomy Effective Date (Pattern A)
- **Given** a Credentialing Specialist has started the off-cycle guided flow and selected **Specialty Change** as a request type,
- **When** they reach the **Collect And Verify New Information** step and add, change, or remove one or more practice-location specialties,
- **Then** the step must present a required **"Taxonomy Effective Date"** input, defaulted to today and editable,
- **And** the specialist cannot proceed until at least one specialty row has actually changed and the Taxonomy Effective Date passes validation.

### AC2 — Credentialing: validate the Taxonomy Effective Date (Pattern A + Pattern D)
- **Given** the specialist has entered a Taxonomy Effective Date on the Specialty Change block,
- **When** they attempt to move to the next step,
- **Then** the flow must block progression and show a clear message when the date is invalid.

**Validation rules (Pattern D — field: Taxonomy Effective Date):**
| # | Rule | Message shown |
|---|---|---|
| V1 | Taxonomy Effective Date must be **on or after** the Practitioner, Practice Location, NPI, Location, and active Address effective-from dates (lower-bound cascade — reuse the existing cascade for the specialty branch) | "Effective From dates must be within Practice Location and Practitioner's Effective Dates" |
| V2 | Taxonomy Effective Date must be **on or before** the network / practice-location **Effective To** window (new upper-bound check) | "Taxonomy Effective Date must fall within the Practice Location and network effective window" |
| V3 | When a Taxonomy Effective To is derived/entered, it must be **after** the Taxonomy Effective From | "Taxonomy Effective To must be after Taxonomy Effective From" |

> Future-dating is *not* blocked in this story (immediate effect; FDP handled separately).

### AC3 — Credentialing: read-only dates on the Correspondence step (Pattern A)
- **Given** the specialist has captured valid specialty changes with a Taxonomy Effective Date,
- **When** they reach the Correspondence step and view a selected practice-location taxonomy,
- **Then** the step must display **read-only "Taxonomy Effective From"** and **"Taxonomy Effective To"** for each affected taxonomy record,
- **And** on completing the step, the system must persist the Taxonomy Effective From/To onto the related Level 4 records (see AC6 Pattern E).

### AC4 — PDA: read-only dates + network changes drive network effective dating (Pattern A)
- **Given** a PDA Specialist has initiated the off-cycle PDA guided flow for a Specialty Change,
- **When** they reach the taxonomy review step, select a practice-location taxonomy, and update its networks,
- **Then** the step must show **read-only "Taxonomy Effective From"** and **"Taxonomy Effective To"** for the selected location,
- **And** when the PDA update completes, network changes must be date-stamped as follows (mirroring Patient Accept Status):
  - a **newly added** network (no prior record) → its record's network Effective From = today;
  - a **removed** network → that network record's network Effective To = today;
  - a **retained** network on a changed taxonomy → **no network-date change**; the taxonomy change is handled by clone-and-terminate (see AC6): the old record's Taxonomy Effective To is stamped and the cloned new record **preserves the old network Effective From** and carries the other effective-from dates over.

### AC5 — QC: read-only dates, flow completes (Pattern A — regression)
- **Given** a QC Specialist has initiated the off-cycle QC guided flow for a Specialty Change,
- **When** they reach the taxonomy review step and open a practice-location taxonomy,
- **Then** the step must show **read-only "Taxonomy Effective From"** and **"Taxonomy Effective To"**,
- **And** the specialist must be able to complete the QC flow end to end.

### AC6 — Records written on completion: clone-new + terminate-old (Pattern E)

The Level 4 write **mirrors Patient Accept Status (`PRM_PASUpdateBatch`)**: on a taxonomy change the current record is **cloned** (so every unrelated field — the old network `EffectiveFrom` / `EffectiveTo`, `PanelStatus`, and the **other** effective-from dates such as `PRM_RoleEffectiveFrom__c` — carries over untouched), the **old** record is terminated by stamping its Taxonomy Effective To, and only the taxonomy dimension is overridden on the clone. `effDate` = the captured **Taxonomy Effective Date** (defaults to today). Enumerate every field written:

**Object: `HealthcareFacilityNetwork` — REMOVED / superseded taxonomy record (terminated, updated in place)**
| Field | Value |
|---|---|
| `PRM_TaxonomyEffectiveTo__c` | `effDate` |
| (`PRM_Taxonomy__c`, `PanelStatus`, `EffectiveFrom`/`EffectiveTo`, `PRM_RoleEffectiveFrom__c`/`…To__c`, all others) | unchanged |

**Object: `HealthcareFacilityNetwork` — ADDED / changed taxonomy record (cloned from the current record, then inserted)**
| Field | Value |
|---|---|
| `PRM_Taxonomy__c` / `PRM_TaxonomyCode__c` (care taxonomy) | the new / changed specialty — the only overridden dimension |
| `PRM_TaxonomyEffectiveFrom__c` | `effDate` |
| `PRM_TaxonomyEffectiveTo__c` | null (open-ended) |
| `PRM_Primary__c` (Is Primary Taxonomy flag) | carried from the UI selection |
| `EffectiveFrom` / `EffectiveTo` (network dates) | **copied from the source record** — the old network Effective From is preserved, not reset to today |
| `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c` | **copied from the source record** — the other effective-from dates carry over |
| `PanelStatus` | copied from the source record |
| `RecordType` | copied from the source (same L4 record type: `FacilityPractitionerTxNw` / `PractitionerTx`) — no hardcoded Id |

> **Add specialty (net-new taxonomy, no prior record):** create a new record directly (no clone) with `PRM_TaxonomyEffectiveFrom__c` = `effDate`.
> **Remove specialty:** only terminate — stamp `PRM_TaxonomyEffectiveTo__c` = `effDate` on the current record; **no clone**.

**Object: `HealthcareProvider` / practice-location taxonomy sync (if applicable)**
| Field | Value |
|---|---|
| Provider taxonomy record | kept in sync with the added/removed care taxonomy per existing off-cycle taxonomy load |

> `PRM_TaxonomyEffectiveFromCalculated__c` / `PRM_TaxonomyEffectiveToCalculated__c` are **formula fields** — not written. They fall back to `EffectiveFrom` / `EffectiveTo` when the stamped fields are blank, so populating the stamped fields makes the Calculated fields reflect the true taxonomy window.

### AC7 — Other off-cycle request types unaffected (Pattern A — negative/regression)
- **Given** an off-cycle guided flow for **Role Change, Name Change, New Region, or New State** (specialty not changed),
- **When** the user completes the flow across Credentialing, PDA, and QC,
- **Then** no Taxonomy Effective Date input is required or shown, no L4 Taxonomy Effective From/To fields are altered, and the flow completes exactly as it does today.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes (implements) |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` — `SpecialityChangeBlock` | OmniScript | Add a required **"Taxonomy Effective Date"** Date element (parallel to `RoleChangeDate`), defaulted to today, gated on *Specialty Change*; keep the "at least one specialty changed" guard | AC1 |
| `CheckEffDateValForRoleChange` (or a new sibling remote action) | OmniScript | Pass `SpecialityData` + the Taxonomy Effective Date + `RequestType='Specialty Change'` into `checkDateValidation` so the specialty branch is actually wired | AC2 |
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Add **upper-bound** (V2) and **To > From** (V3) checks to `validateSpecialityChangeRequest` / `runCascadeValidation`; return specialty-specific output keys/messages | AC2 |
| `PRM_OmniUtils.checkDateValidation` | Apex | Pass-through of new validation outputs (no signature change) | AC2 |
| `PRM_OffCycleCredentialing_English` — Correspondence step | OmniScript | Add **read-only** Taxonomy Effective From / Taxonomy Effective To display per taxonomy row | AC3 |
| `PRM_SpecialtyPractitionerPracticeLocation` | Integration Procedure | **Clone-and-terminate mirroring `PRM_PASUpdateBatch`**: clone the source record (preserving old network `EffectiveFrom`/`EffectiveTo`, `PanelStatus`, and `PRM_RoleEffectiveFrom__c`/`…To__c`), stamp `PRM_TaxonomyEffectiveTo__c = effDate` on the old record, set `PRM_TaxonomyEffectiveFrom__c = effDate` on the clone (or create directly for a net-new specialty); only added/removed networks touch network dates | AC3, AC4, AC6 |
| `PRMOffCycleTransformSpecialityData`, `PRMLoadOffCycleTaxonomy`, `PRMDRCreateHFNTaxonomyRecords`, `PRMDRCreatePracticeLocationTaxonomy` | DataRaptor | Extend transform/create/load maps to carry Taxonomy Effective From/To onto the L4 records (today they set generic `EffectiveFrom`/`EffectiveTo` only) | AC6 |
| `PRM_OffCyclePDAReview_English` — taxonomy step | OmniScript | Read-only Taxonomy Effective From/To; wire network add/remove → network Effective From/To = today | AC4 |
| `PRM_OffCycleQCReview_English` — taxonomy step | OmniScript | Read-only Taxonomy Effective From/To display | AC5 |
| `HealthcareFacilityNetwork` fields | Metadata (exists) | `PRM_TaxonomyEffectiveFrom__c`, `PRM_TaxonomyEffectiveTo__c` (+ `…Calculated__c` formulas) already deployed — **reuse, do not recreate** | AC6 |
| `PRM_EffectiveDateValForOffcycleTest` | Apex test | Extend for V2/V3 specialty-change validation branches (≥85%) | AC2 |

---

## Definition of done

- [ ] Taxonomy Effective Date is required, defaults to today, and is editable on the Specialty Change block (AC1).
- [ ] Specialty-change date validation is fully wired (`SpecialityData` passed) and V1 (lower), V2 (upper), V3 (To > From) all block with clear messages (AC2).
- [ ] Taxonomy Effective From/To display **read-only** on Correspondence, PDA, and QC steps (AC3–AC5).
- [ ] On complete, superseded taxonomy records are terminated (`PRM_TaxonomyEffectiveTo__c` = effDate) and the changed taxonomy is a **clone** with `PRM_TaxonomyEffectiveFrom__c` = effDate, **preserving the old network `EffectiveFrom` and copying the Role effective-from dates**, `Is Primary Taxonomy` carried (AC6).
- [ ] Only genuinely added networks (Effective From = today) and removed networks (Effective To = today) change network dates; retained networks preserve the old network Effective From (AC4).
- [ ] `PRM_TaxonomyEffectiveFromCalculated__c` / `…ToCalculated__c` reflect the true window after stamping (spot-check a record).
- [ ] Role Change, Name Change, New Region, New State regress cleanly — no Taxonomy Effective Date shown, no L4 taxonomy fields touched (AC7).
- [ ] Record types resolved by DeveloperName (no hardcoded Ids); writes bulk-safe (one DML per object type); FLS/CRUD enforced.
- [ ] Apex coverage ≥ 85% incl. the new V2/V3 specialty branches; happy path + negative (invalid date) paths asserted.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ1 | Dedicated **"Taxonomy Effective Date"** input vs. reusing the single "Effective Date" field when both Role Change **and** Specialty Change are selected in one submission? (Recommended: dedicated field to decouple.) | UI + payload design | Product/BA |
| CQ2 | **(Resolved — mirrors PAS)** Terminate always stamps `PRM_TaxonomyEffectiveTo__c` = `effDate` (captured date, default today); the clone/create copies the old network Effective From and the Role effective-from dates. Confirm Remove should not force literal today. | Remove-path stamp | Product/BA |
| CQ3 | V2 upper-bound — network `EffectiveTo`, practice-location `EffectiveTo`, or the earlier of the two? | Validation precision | Product/BA |
| CQ4 | The "Is Primary Taxonomy" flag maps to `PRM_Primary__c` on HealthcareFacilityNetwork — does re-designating primary during a change need its own effective-dating, or just carry the flag? | Field mapping / scope | Technical |
| CQ5 | Stamp both the taxonomy `PractitionerTx` rows and the network `FacilityPractitionerTxNw` rows, or L4-with-network only? | Write grain | Technical |
| CQ6 | Does the removed specialty also require terminating the linked License/Board-Cert taxonomy records, or L4 taxonomy only for this story? | Scope boundary | Product/BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Medium | New V2/V3 branches + specialty wiring; shared by all off-cycle request types — regress Role/New Region |
| `PRM_SpecialtyPractitionerPracticeLocation` chain | Integration Procedure | High | Now stamps dedicated taxonomy fields + drives network dating |
| `PRMOffCycleTransformSpecialityData` / `PRMLoadOffCycleTaxonomy` / `PRMDRCreateHFNTaxonomyRecords` | DataRaptor | Medium | Carry Taxonomy Effective From/To through transform/create/load |
| `PRM_OffCycleCredentialing_English` | OmniScript | Medium | New date input on Specialty block; read-only fields on Correspondence |
| `PRM_OffCyclePDAReview_English` | OmniScript | Medium | Network add/remove effective dating |
| `PRM_OffCycleQCReview_English` | OmniScript | Low | Read-only display only |
| `HealthcareFacilityNetwork` taxonomy fields | Metadata | Low | Reused (already deployed) |
| Reporting / Calculated formula fields | Downstream | Low (positive) | Calculated fields become accurate once stamped fields populated |

---

## Estimated Effort *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` (Taxonomy date input + validation wiring) | OmniScript | M | New Date element gated on Specialty Change; pass `SpecialityData` to validation |
| `PRM_EffectiveDateValidationForOffcycle` (+ test) | Apex enhancement | M | Add V2 upper-bound + V3 To>From to specialty branch |
| `PRM_SpecialtyPractitionerPracticeLocation` | IP enhancement | L | Stamp taxonomy fields + network dating on terminate/create |
| `PRMOffCycleTransformSpecialityData` / `PRMLoadOffCycleTaxonomy` / `PRMDRCreateHFNTaxonomyRecords` / `PRMDRCreatePracticeLocationTaxonomy` | DataRaptor edits | M | Carry Taxonomy Effective From/To through transforms/loads |
| `PRM_OffCycleCredentialing_English` (Correspondence read-only) | OmniScript | S | Read-only display fields |
| `PRM_OffCyclePDAReview_English` (taxonomy step) | OmniScript | M | Read-only + network add/remove dating |
| `PRM_OffCycleQCReview_English` (taxonomy step) | OmniScript | S | Read-only display |
| Regression (other request types) | QA | S | Role / Name / New Region / New State |
| **Total** | | **~L–XL** | Bigger than the Role story (no existing writer/date field); sequence Credentialing → PDA → QC |
