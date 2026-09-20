# USER STORY: Off-Cycle New Region / New State — Capture, Validate & Stamp Role + Taxonomy Effective Dates on Newly Created Level 4 Records

**Persona:** Credentialing Specialist (primary); Provider Data Admin (PDA) Specialist and Network Management QC Specialist (downstream review personas)
**Priority:** P1
**OmniScript:** `PRM_OffCycleCredentialing_English` (capture), `PRM_OffCyclePDAReview_English` (PDA update), `PRM_OffCycleQCReview_English` (QC review)
**Integration Procedures:** `PRM_NewStateRegionTaxonomy` (New Region/State save)
**Relevant Requirements:**
- `requirements/OffCycle_RoleChange_RoleEffectiveDate_UserStory.md` (sibling — Role Effective Date)
- `requirements/OffCycle_SpecialtyChange_TaxonomyEffectiveDate_UserStory.md` (sibling — Taxonomy Effective Date)
- `requirements/RoleChange_EntryPoints_Analysis_RoleEffectiveDate.md`
- `requirements/PatientAcceptStatus_Level4_EffectiveDate_Calculation_Analysis.md` (pattern being mirrored)

> **New State = legacy alias of New Region.** Both request types are routed to the same validation branch (`validateNewRegionRequest`) and the same save IP; this story covers both. Where the picklist offers both, the flow shows a combined "New Region & State" context.

---

## Story

**As a** Credentialing Specialist processing an off-cycle **New Region** or **New State** request,
**I want** to capture an **Effective Date** for the newly added practitioner-at-practice-location taxonomy, role, and networks, validate it, and have it stamped as the **Role Effective From** and **Taxonomy Effective From** on the Level 4 records that get created,
**So that** the new region/state participation records carry an accurate start date instead of silently defaulting to the network's generic effective date — and downstream PDA/QC reviewers, network loads, and reporting all reflect when the practitioner began participating in the new region.

**Why it matters:** New Region / New State **creates brand-new** Level 4 records (taxonomy + role + networks) for a geography the practitioner didn't previously serve. Unlike Role Change and Specialty Change (which terminate an old record and create a new one), this path is **create-only** — but it still leaves `PRM_RoleEffectiveFrom__c` and `PRM_TaxonomyEffectiveFrom__c` empty today, so the already-built *Calculated* fields fall back to the network dates and the true role/taxonomy start date is lost. This story closes that gap for the create-only New Region / New State path.

---

## Scope

| Flow | OmniScript | Affected Step(s) | Persona | This story does |
|---|---|---|---|---|
| Off-Cycle Credentialing | `PRM_OffCycleCredentialing_English` | New Region/State step (`NewStateRegionTaxonomyRole`) | Credentialing Specialist | Capture Effective Date; validate; stamp Role + Taxonomy Effective From on the created L4 records |
| Off-Cycle PDA Review | `PRM_OffCyclePDAReview_English` | New Region/State review step | PDA Specialist | Show read-only Role/Taxonomy Effective From/To; allow network add/remove with correct network dating |
| Off-Cycle QC Review | `PRM_OffCycleQCReview_English` | New Region/State review step | QC Specialist | Show read-only Role/Taxonomy Effective From/To; complete the QC flow |
| Off-Cycle — other request types | all three | all | all | **Regression only** — Role Change, Specialty Change, Name Change must continue to work unchanged |

**In scope:** Off-Cycle **New Region** and **New State** request types, immediate (non-future-dated) effect, **create-only** Level 4 stamping (Effective From set, Effective To open).
**Out of scope (this story):** future-dated processing (FDP), terminate-old logic (there is no prior record to terminate for a new region), Name Change (separate regression story), and entry points outside off-cycle.

---

## Current State (verified in active build)

| Item | Current behavior | Location |
|---|---|---|
| Request types | Role Change, Specialty Change, Name Change, **New Region**, **New State** | `PRM_OffCycleCredentialing_English` v62, `SelectOffCycleChanges` step |
| New Region/State capture UI | Step `NewStateRegionTaxonomyRole` (label "Add Practitioner Role") with Edit Block `NewStateRegionTaxonomy` ("Practitioner at Practice Location Taxonomy"), `CareTaxonomyName`, `IsPrimaryTaxonomy`, `Role`; gated on `NewRegionOrStateRT` (`New Region` OR `New State`) | `CollectAndVerifyNewInformation` / `NewStateRegionTaxonomyRole` steps |
| Effective Date field | **None dedicated** for New Region/State | — |
| Validation | `validateNewRegionRequest` → `runCascadeValidationForNewRegion` **exists** (validates Effective Date on/after Practitioner Account + HealthcareProvider only; output key `EffectiveDateCheckForNewRegion`) but is **not wired** to a New Region-specific effective-date input | `PRM_EffectiveDateValidationForOffcycle.cls` |
| Save path | `PRM_NewStateRegionTaxonomy` (element `IP_NewStateRegionTaxonomy`); transform via `PRMTransNewRegionSpecialties` (`DRTransNewRegionSpecialties`) | `IP_NewStateRegionTaxonomy` element |
| **Gap** | No Effective Date input; New Region validation not wired; `PRM_RoleEffectiveFrom__c` / `PRM_TaxonomyEffectiveFrom__c` **never written** on the created records; dates not shown read-only downstream | — |

---

## Acceptance Criteria

### AC1 — Credentialing: capture the New Region Effective Date (Pattern A)
- **Given** a Credentialing Specialist has started the off-cycle guided flow and selected **New Region** or **New State**,
- **When** they reach the New Region/State step and add the practitioner's taxonomy, role, and networks for the new geography,
- **Then** the step must present a required **"Effective Date"** input, defaulted to today and editable,
- **And** the specialist cannot proceed until at least one new region/state row is added and the Effective Date passes validation.

### AC2 — Credentialing: validate the Effective Date (Pattern A + Pattern D)
- **Given** the specialist has entered an Effective Date for the new region/state,
- **When** they attempt to move to the next step,
- **Then** the flow must block progression and show a clear message when the date is invalid.

**Validation rules (Pattern D — field: New Region Effective Date):**
| # | Rule | Message shown |
|---|---|---|
| V1 | Effective Date must be **on or after** the Practitioner Account and HealthcareProvider effective-from dates (existing New Region cascade — wire it) | "Effective Date must be on or after the Practitioner's effective date" |
| V2 | Effective Date must be **on or before** the target network / practice-location **Effective To** window, where applicable (upper-bound check) | "Effective Date must fall within the network effective window" |

> V3 (Effective To > Effective From) does **not** apply — create-only records leave Effective To open. Future-dating is **not** blocked in this story.

### AC3 — Records written on completion: create-only Level 4 records (Pattern E)

When the New Region / New State flow completes, the Level 4 records are **created** (no termination). This path is exempt from the clone-and-terminate rule that the Role and Taxonomy sibling stories follow: there is **no prior record** for a brand-new geography, so nothing is cloned or terminated. (If a New Region submission ever edits an *existing* record's effective window, the same clone-new + terminate-old rule as `PRM_PASUpdateBatch` applies — preserve the old network Effective From, copy the other effective-from dates, stamp only the changed dimension.) Enumerate every field written:

**Object: `HealthcareFacilityNetwork` — NEW region/state taxonomy + role + network record (created)**
| Field | Value |
|---|---|
| `PRM_Taxonomy__c` / `PRM_TaxonomyCode__c` (care taxonomy) | the selected new-region care taxonomy |
| Role field (`PRM_PractitionerRole__c` grain) | the selected role (PCP / Specialist) |
| `PRM_RoleEffectiveFrom__c` | the captured **Effective Date** (or today when not selected) |
| `PRM_RoleEffectiveTo__c` | null (open-ended) |
| `PRM_TaxonomyEffectiveFrom__c` | the captured **Effective Date** (or today) |
| `PRM_TaxonomyEffectiveTo__c` | null (open-ended) |
| `PRM_Primary__c` (Is Primary Taxonomy flag) | carried from the UI selection |
| `EffectiveFrom` (network date) | the captured Effective Date (or today) |
| `EffectiveTo` (network date) | null (open) |
| `PanelStatus` | initial status per existing New Region logic (unchanged) |
| `RecordType` | resolved by DeveloperName to the correct L4 record type (`FacilityPractitionerTxNw` / `PractitionerTx`) — no hardcoded Id |

> `PRM_RoleEffectiveFromCalculated__c` / `PRM_TaxonomyEffectiveFromCalculated__c` (and the `…To…` formulas) are **formula fields** — not written; they now reflect the stamped Effective From instead of falling back to the network date.

### AC4 — PDA: read-only dates + network changes drive network effective dating (Pattern A)
- **Given** a PDA Specialist has initiated the off-cycle PDA guided flow for a New Region/State request,
- **When** they reach the review step, select a new-region taxonomy, and update its networks,
- **Then** the step must show **read-only "Role Effective From/To"** and **"Taxonomy Effective From/To"** for the selected location,
- **And** network changes must be date-stamped: added network → Effective From = today; removed network → Effective To = today.

### AC5 — QC: read-only dates, flow completes (Pattern A — regression)
- **Given** a QC Specialist has initiated the off-cycle QC guided flow for a New Region/State request,
- **When** they reach the review step and open a new-region taxonomy,
- **Then** the step must show **read-only** Role/Taxonomy Effective From/To,
- **And** the specialist must be able to complete the QC flow end to end.

### AC6 — Other off-cycle request types unaffected (Pattern A — negative/regression)
- **Given** an off-cycle guided flow for **Role Change, Specialty Change, or Name Change** (no new region/state),
- **When** the user completes the flow across Credentialing, PDA, and QC,
- **Then** no New Region Effective Date input is required or shown, no records are created for a new geography, and the flow completes exactly as it does today.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes (implements) |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` — `NewStateRegionTaxonomyRole` | OmniScript | Add a required **"Effective Date"** Date element gated on `NewRegionOrStateRT`, defaulted to today | AC1 |
| `CheckEffDateValForRoleChange` (or new sibling remote action) | OmniScript | Pass the New Region Effective Date + `RequestType='New Region'`/`'New State'` into `checkDateValidation` so `validateNewRegionRequest` is actually wired | AC2 |
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Add **upper-bound** (V2) to `runCascadeValidationForNewRegion`; keep the practitioner+HCP lower-bound (V1) | AC2 |
| `PRM_NewStateRegionTaxonomy` | Integration Procedure | Stamp `PRM_RoleEffectiveFrom__c` + `PRM_TaxonomyEffectiveFrom__c` (= captured Effective Date) and network `EffectiveFrom` on the created L4 records | AC3 |
| `PRMTransNewRegionSpecialties`, `PRMDRTNewRegionStateTaxonomy`, `PRMDRTRoleSpecialtyNewRegionState` | DataRaptor | Extend transform/create maps to carry the Effective Date onto Role + Taxonomy Effective From (today set network `EffectiveFrom` only) | AC3 |
| `PRM_OffCyclePDAReview_English` — New Region step | OmniScript | Read-only Role/Taxonomy Effective From/To; wire network add/remove → network Effective From/To = today | AC4 |
| `PRM_OffCycleQCReview_English` — New Region step | OmniScript | Read-only Role/Taxonomy Effective From/To display | AC5 |
| `HealthcareFacilityNetwork` fields | Metadata (exists) | `PRM_RoleEffectiveFrom__c`, `PRM_TaxonomyEffectiveFrom__c` (+ `…To__c` + `…Calculated__c`) already deployed — **reuse, do not recreate** | AC3 |
| `PRM_EffectiveDateValForOffcycleTest` | Apex test | Extend for the New Region V1/V2 branches (≥85%) | AC2 |

---

## Definition of done

- [ ] Effective Date is required, defaults to today, editable on the New Region/State step (AC1).
- [ ] New Region date validation is wired and V1 (lower) + V2 (upper) block with clear messages (AC2).
- [ ] On complete, created L4 records carry `PRM_RoleEffectiveFrom__c` + `PRM_TaxonomyEffectiveFrom__c` = captured date, Effective To open, `Is Primary` carried (AC3).
- [ ] Role/Taxonomy Effective From/To display **read-only** on PDA and QC steps (AC4–AC5).
- [ ] `…Calculated__c` fields reflect the stamped Effective From (spot-check a created record).
- [ ] Role Change, Specialty Change, Name Change regress cleanly (AC6).
- [ ] Record types resolved by DeveloperName (no hardcoded Ids); writes bulk-safe (one DML per object type); FLS/CRUD enforced.
- [ ] Apex coverage ≥ 85% incl. the new New Region V2 branch; happy path + negative (invalid date) paths asserted.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ1 | One shared "Effective Date" across all selected request types in a combined submission, or a dedicated New Region date? | UI + payload | Product/BA |
| CQ2 | V2 upper-bound — should a brand-new region even have an upper bound, or is lower-bound (V1) sufficient? | Validation scope | Product/BA |
| CQ3 | For a combined "New Region **&** State" submission, is one effective date applied to all created records? | Data consistency | Product/BA |
| CQ4 | Confirm the created record's network `EffectiveFrom` should equal the captured Effective Date (vs. always today). | Network dating | Product/BA |
| CQ5 | Stamp both the taxonomy `PractitionerTx` rows and the network `FacilityPractitionerTxNw` rows? | Write grain | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Medium | New Region wiring + V2; shared across request types — regress others |
| `PRM_NewStateRegionTaxonomy` chain | Integration Procedure | High | Now stamps Role + Taxonomy Effective From on create |
| `PRMTransNewRegionSpecialties` / `PRMDRTNewRegionStateTaxonomy` / `PRMDRTRoleSpecialtyNewRegionState` | DataRaptor | Medium | Carry Effective Date onto Role + Taxonomy Effective From |
| `PRM_OffCycleCredentialing_English` | OmniScript | Low | New date input on New Region step |
| `PRM_OffCyclePDAReview_English` | OmniScript | Medium | Network add/remove effective dating |
| `PRM_OffCycleQCReview_English` | OmniScript | Low | Read-only display only |
| `HealthcareFacilityNetwork` role/taxonomy fields | Metadata | Low | Reused (already deployed) |

---

## Estimated Effort *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` (date input + validation wiring) | OmniScript | M | New Date element gated on New Region/State |
| `PRM_EffectiveDateValidationForOffcycle` (+ test) | Apex enhancement | S–M | Wire New Region + add V2 |
| `PRM_NewStateRegionTaxonomy` | IP enhancement | M | Stamp Role + Taxonomy Effective From on create |
| `PRMTransNewRegionSpecialties` / `PRMDRTNewRegionStateTaxonomy` / `PRMDRTRoleSpecialtyNewRegionState` | DataRaptor edits | M | Carry Effective Date through transforms/creates |
| `PRM_OffCyclePDAReview_English` (New Region step) | OmniScript | M | Read-only + network add/remove dating |
| `PRM_OffCycleQCReview_English` (New Region step) | OmniScript | S | Read-only display |
| Regression (other request types) | QA | S | Role / Specialty / Name |
| **Total** | | **~L** | Simpler than Role/Taxonomy (create-only, no terminate); sequence Credentialing → PDA → QC |
