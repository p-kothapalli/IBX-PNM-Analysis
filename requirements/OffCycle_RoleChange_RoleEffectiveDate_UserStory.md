# USER STORY: Off-Cycle Role Change — Capture, Validate & Stamp "Role Effective Date" (Level 4)

**Persona:** Credentialing Specialist (primary); Provider Data Admin (PDA) Specialist and Network Management QC Specialist (downstream review personas)
**Priority:** P1
**OmniScript:** `PRM_OffCycleCredentialing_English` (capture), `PRM_OffCyclePDAReview_English` (PDA update), `PRM_OffCycleQCReview_English` (QC review)
**Integration Procedures:** `PRM_CheckRoleChangeDataParent` → `PRM_CheckRoleChangeData` (role-change save chain)
**Relevant Requirements:**
- `requirements/RoleChange_EntryPoints_Analysis_RoleEffectiveDate.md` (entry-point analysis)
- `requirements/PatientAcceptStatus_Level4_EffectiveDate_Calculation_Analysis.md` (pattern being mirrored)
- `requirements/Concierge_Off_Cycle_End_to_End_User_Stories.md` (off-cycle flow parity)
- `requirements/Enhancements/PNM_OffCycle_Process_Apex_Service_Architecture.md`, `requirements/Enhancements/PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`

---

## Story

**As a** Credentialing Specialist processing an off-cycle **Role Change**,
**I want** to capture a **Role Effective Date** for the role update, have it validated against the practitioner's and practice location's effective dates, and have it stamped onto the affected Level 4 records so the old role is terminated and the new role begins on the correct date,
**So that** downstream PDA and QC reviewers, network loads, and reporting all reflect *when* a practitioner's role actually started and stopped at each practice location — instead of defaulting silently to the network's generic effective dates.

**Why it matters:** Today the off-cycle Role Change path captures a single required "Effective Date" (`RoleChangeDate`) and runs a lower-bound validation, but it does **not** stamp the dedicated Level 4 Role Effective From/To fields the way Patient Accept Status stamps its own effective dates. As a result, the `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c` fields (and their already-built *Calculated* formula fields) remain unpopulated for off-cycle role changes, the "terminate old role / start new role" history is not date-accurate, and reviewers cannot see when a role change takes effect. This story closes that gap for the off-cycle Role Change request type across the Credentialing, PDA, and QC flows.

---

## Scope

| Flow | OmniScript | Affected Step(s) | Persona | This story does |
|---|---|---|---|---|
| Off-Cycle Credentialing | `PRM_OffCycleCredentialing_English` | Collect And Verify New Information; Role Change Correspondence | Credentialing Specialist | Capture Role Effective Date; validate; show read-only per-location Role Effective From/To; stamp L4 records on complete |
| Off-Cycle PDA Review | `PRM_OffCyclePDAReview_English` | Role Change step | PDA Specialist | Show read-only Role Effective From/To; allow network add/remove with correct network Effective From/To dating |
| Off-Cycle QC Review | `PRM_OffCycleQCReview_English` | Role Change review step | QC Specialist | Show read-only Role Effective From/To; complete the QC flow |
| Off-Cycle — other request types | all three | all | all | **Regression only** — Specialty Change, Name Change, New Region, New State must continue to work unchanged |

**In scope:** Off-Cycle **Role Change** request type only, immediate (non-future-dated) effect, Level 4 record stamping via the **clone-new + terminate-old** pattern (mirroring Patient Accept Status / `PRM_PASUpdateBatch` — the clone preserves the old network Effective From and copies the other effective-from dates).
**Out of scope (this story):** future-dated role processing (FDP), Taxonomy Effective From/To (separate story), the Manage Roles tab entry point (`prmManageRolesTab`, already writes these fields), and role changes originating from Intake/PDM Manual Update/ReCred.

---

## Current State (verified in active build)

| Item | Current behavior | Location |
|---|---|---|
| Off-Cycle request types | Role Change, Specialty Change, Name Change, New Region, New State | `PRM_OffCycleCredentialing_English` v62, `SelectOffCycleChanges` step |
| Role Effective Date field | Required Date element `RoleChangeDate` (label **"Effective Date"**), shown only when *Role Change* is selected | `CollectAndVerifyNewInformation` step |
| Editable role table | `RoleChangeEditBlock` (per practice-location taxonomy rows) | `CollectAndVerifyNewInformation` step |
| Validation | `CheckEffDateValForRoleChange` → `PRM_OmniUtils.checkDateValidation` → `PRM_EffectiveDateValidationForOffcycle` runs a **lower-bound cascade only** (date on/after Practitioner Account, HealthcareProvider, Practice Location, NPI, Location, Address effective-from). Message: *"Effective From dates must be within Practice Location and Practitioner's Effective Dates."* | `PRM_EffectiveDateValidationForOffcycle.cls` |
| Save path | Role-change data + `RoleChangeEffDate = %RoleChangeDate%` passed to IP `PRM_CheckRoleChangeDataParent`; `TerminateAssignedNetworks` element already handles network termination | `IPCheckRoleChangeData` element |
| **Gap** | The captured date is **not** stamped to L4 `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c`; validation checks lower bound only (no upper bound, no To > From); dates are not shown read-only in Correspondence / PDA / QC | — |

---

## Acceptance Criteria

### AC1 — Credentialing: capture the Role Effective Date (Pattern A)
- **Given** a Credentialing Specialist has started the off-cycle guided flow and selected **Role Change** as a request type,
- **When** they reach the **Collect And Verify New Information** step and edit one or more practice-location roles,
- **Then** the step must present a required **"Role Effective Date"** input, defaulted to today and editable,
- **And** the specialist cannot proceed until at least one role row has actually changed and the Role Effective Date passes validation.

### AC2 — Credentialing: validate the Role Effective Date (Pattern A + Pattern D)
- **Given** the specialist has entered a Role Effective Date on the Role Change step,
- **When** they attempt to move to the next step,
- **Then** the flow must block progression and show a clear message when the date is invalid.

**Validation rules (Pattern D — field: Role Effective Date):**
| # | Rule | Message shown |
|---|---|---|
| V1 | Role Effective Date must be **on or after** the Practitioner, Practice Location, NPI, Location, and active Address effective-from dates (existing lower-bound cascade — retained) | "Effective From dates must be within Practice Location and Practitioner's Effective Dates" |
| V2 | Role Effective Date must be **on or before** the network / practice-location **Effective To** window (new upper-bound check) | "Role Effective Date must fall within the Practice Location and network effective window" |
| V3 | When a Role Effective To is derived/entered, it must be **after** the Role Effective From | "Role Effective To must be after Role Effective From" |

> Future-dating is *not* blocked in this story (per scoping decision — immediate effect; FDP handled separately).

### AC3 — Credentialing: read-only dates on Role Change Correspondence (Pattern A)
- **Given** the specialist has captured valid role changes with a Role Effective Date,
- **When** they reach the **Role Change Correspondence** step and view a selected practice-location taxonomy,
- **Then** the step must display **read-only "Role Effective From"** and **"Role Effective To"** for each affected role record,
- **And** on completing the step, the system must persist the Role Effective From/To onto the related Level 4 records (see AC6 Pattern E).

### AC4 — PDA: read-only dates + network changes drive network effective dating (Pattern A)
- **Given** a PDA Specialist has initiated the off-cycle PDA guided flow for a Role Change,
- **When** they reach the **Role Change** step, select a practice-location taxonomy, and update its networks,
- **Then** the step must show **read-only "Role Effective From"** and **"Role Effective To"** for the selected location,
- **And** when the PDA update completes, network changes must be date-stamped as follows (mirroring Patient Accept Status):
  - a **newly added** network (no prior record) → its record's network Effective From = today;
  - a **removed** network → that network record's network Effective To = today;
  - a **retained** network on a changed role → **no network-date change**; the role change is handled by clone-and-terminate (see AC6): the old record's Role Effective To is stamped and the cloned new record **preserves the old network Effective From** and carries the other effective-from dates over.

### AC5 — QC: read-only dates, flow completes (Pattern A — regression)
- **Given** a QC Specialist has initiated the off-cycle QC guided flow for a Role Change,
- **When** they reach the Role Change review step and open a practice-location taxonomy,
- **Then** the step must show **read-only "Role Effective From"** and **"Role Effective To"**,
- **And** the specialist must be able to complete the QC flow end to end.

### AC6 — Records written on completion: clone-new + terminate-old (Pattern E)

The Level 4 write **mirrors Patient Accept Status (`PRM_PASUpdateBatch`)**: on a role change the current record is **cloned** (so every unrelated field — the old network `EffectiveFrom` / `EffectiveTo`, `PanelStatus`, and the **other** effective-from dates such as `PRM_TaxonomyEffectiveFrom__c` — carries over untouched), the **old** record is terminated by stamping its Role Effective To, and only the role dimension is overridden on the clone. `effDate` = the captured **Role Effective Date** (defaults to today). Enumerate every field written:

**Object: `HealthcareFacilityNetwork` — CURRENT role record (terminated, updated in place)**
| Field | Value |
|---|---|
| `PRM_RoleEffectiveTo__c` | `effDate` |
| (Role, `PanelStatus`, `EffectiveFrom`/`EffectiveTo`, `PRM_TaxonomyEffectiveFrom__c`/`…To__c`, all others) | unchanged |

**Object: `HealthcareFacilityNetwork` — NEW role record (cloned from the current record, then inserted)**
| Field | Value |
|---|---|
| Role field (`PRM_PractitionerRole__c` grain) | the new role (PCP / Specialist) — the only overridden dimension |
| `PRM_RoleEffectiveFrom__c` | `effDate` |
| `PRM_RoleEffectiveTo__c` | null (open-ended) |
| `EffectiveFrom` / `EffectiveTo` (network dates) | **copied from the source record** — the old network Effective From is preserved, not reset to today |
| `PRM_TaxonomyEffectiveFrom__c` / `PRM_TaxonomyEffectiveTo__c` | **copied from the source record** — the other effective-from dates carry over |
| `PanelStatus` | copied from the source record |
| `RecordType` | copied from the source (same L4 record type: `FacilityPractitionerTxNw` / `PractitionerTx`) — no hardcoded Id |

> **Remove role:** only terminate — stamp `PRM_RoleEffectiveTo__c` = `effDate` on the current record; **no clone** (nothing new begins).

**Object: `HealthcarePractitionerFacility` (PPL affiliation) — role sync**
| Field | Value |
|---|---|
| `PRM_PractitionerRole__c` | kept in sync with the new L4 role (via existing trigger sync) |

> `PRM_RoleEffectiveFromCalculated__c` / `PRM_RoleEffectiveToCalculated__c` are **formula fields** — not written. They fall back to `EffectiveFrom` / `EffectiveTo` when the stamped fields are blank, so populating the stamped fields makes the Calculated fields reflect the true role window.

### AC7 — Other off-cycle request types unaffected (Pattern A — negative/regression)
- **Given** an off-cycle guided flow for **Specialty Change, Name Change, New Region, or New State** (role not changed),
- **When** the user completes the flow across Credentialing, PDA, and QC,
- **Then** no Role Effective Date input is required or shown, no L4 Role Effective From/To fields are altered, and the flow completes exactly as it does today.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes (implements) |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` — `CollectAndVerifyNewInformation` | OmniScript step | Keep `RoleChangeDate` required + default today; ensure "Role Effective Date" label; keep `RoleChangeEditBlock` guard | AC1 |
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Add **upper-bound** check (V2) and **To > From** check (V3) to the Role Change branch (`validateRoleChangeRequest` / `runCascadeValidation`); return new output keys/messages | AC2 |
| `PRM_OmniUtils.checkDateValidation` | Apex | Pass-through of new validation outputs (no signature change) | AC2 |
| `PRM_OffCycleCredentialing_English` — Role Change Correspondence step | OmniScript | Add **read-only** Role Effective From / Role Effective To display fields per taxonomy row | AC3 |
| `PRM_CheckRoleChangeDataParent` → `PRM_CheckRoleChangeData` | Integration Procedure | **Clone-and-terminate mirroring `PRM_PASUpdateBatch`**: clone the source record (preserving old network `EffectiveFrom`/`EffectiveTo`, `PanelStatus`, and `PRM_TaxonomyEffectiveFrom__c`/`…To__c`), stamp `PRM_RoleEffectiveTo__c = effDate` on the old record, set `PRM_RoleEffectiveFrom__c = effDate` (= `RoleChangeEffDate`) on the clone; only added/removed networks touch network dates | AC3, AC4, AC6 |
| `PRMLoadPractitionerFacRoleChange`, `PRMTransPracFacRoleChange`, `PRMTransRoleChangeTables` | DataRaptor | Extend transform/load maps to carry Role Effective From/To onto the L4 records (currently map generic `EffectiveFrom`/`EffectiveTo` only) | AC6 |
| `PRM_OffCyclePDAReview_English` — Role Change step | OmniScript | Read-only Role Effective From/To; wire network add/remove → network Effective From/To = today | AC4 |
| `PRM_OffCycleQCReview_English` — Role Change step | OmniScript | Read-only Role Effective From/To display | AC5 |
| `HealthcareFacilityNetwork` fields | Metadata (exists) | `PRM_RoleEffectiveFrom__c`, `PRM_RoleEffectiveTo__c` (+ `…Calculated__c` formulas) already deployed — **reuse, do not recreate** | AC6 |
| `PRM_EffectiveDateValForOffcycleTest` | Apex test | Extend for V2/V3 role-change validation branches (≥85%) | AC2 |

---

## Definition of done

- [ ] Role Effective Date is required, defaults to today, and is editable on the Credentialing Role Change step (AC1).
- [ ] V1 (retained), V2 (upper bound), V3 (To > From) all block progression with clear business messages (AC2).
- [ ] Role Effective From/To display **read-only** on Role Change Correspondence, PDA, and QC steps (AC3–AC5).
- [ ] On complete, the current role record is terminated (`PRM_RoleEffectiveTo__c` = effDate) and a **clone** is inserted with `PRM_RoleEffectiveFrom__c` = effDate, **preserving the old network `EffectiveFrom` and copying the Taxonomy effective-from dates**, with the PPL role kept in sync (AC6).
- [ ] Only genuinely added networks (Effective From = today) and removed networks (Effective To = today) change network dates; retained networks preserve the old network Effective From (AC4).
- [ ] `PRM_RoleEffectiveFromCalculated__c` / `…ToCalculated__c` reflect the true window after stamping (spot-check a record).
- [ ] Specialty Change, Name Change, New Region, New State regress cleanly — no Role Effective Date shown, no L4 role fields touched (AC7).
- [ ] Record types resolved by DeveloperName (no hardcoded Ids); writes bulk-safe (one DML per object type); FLS/CRUD enforced.
- [ ] Apex coverage ≥ 85% incl. the new V2/V3 branches; happy path + negative (invalid date) paths asserted.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ1 | **(Resolved — mirrors PAS)** Terminate always stamps `PRM_RoleEffectiveTo__c` = `effDate` (the captured Role Effective Date, default today), matching `PRM_PASUpdateBatch`. Confirm Remove should not instead force literal today. | Remove-path stamp | Product/BA |
| CQ2 | V2 upper-bound — should the ceiling be the **network `EffectiveTo`**, the **practice-location `EffectiveTo`**, or the **earlier of the two**? | Validation precision | Product/BA |
| CQ3 | **(Resolved — mirrors PAS)** The clone copies the old network `EffectiveFrom`/`EffectiveTo` and the Taxonomy effective-from dates; only the role dimension + its Role Effective From/To change. No reset to today for retained networks. | Record parity | Product/BA |
| CQ4 | Should Role Effective To ever be captured on the UI, or is it always system-derived (today on terminate / open on new)? | UI scope | Product/BA |
| CQ5 | Are Taxonomy (PractitionerTx) role rows *and* Network (FacilityPractitionerTxNw) rows both stamped, or L4-with-network only? | Write grain | Technical |
| CQ6 | Confirm the PPL (`HealthcarePractitionerFacility`) role/date sync is trigger-driven (no explicit write needed in this flow). | Avoid double-write | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Medium | New V2/V3 branches; shared by all off-cycle request types — regress Specialty/New Region |
| `PRM_CheckRoleChangeDataParent` chain | Integration Procedure | High | Now stamps dedicated role fields + drives network dating |
| `PRM_OffCycleCredentialing_English` | OmniScript | Medium | Correspondence step read-only fields; capture step unchanged logic |
| `PRM_OffCyclePDAReview_English` | OmniScript | Medium | Network add/remove effective dating |
| `PRM_OffCycleQCReview_English` | OmniScript | Low | Read-only display only |
| `HealthcareFacilityNetwork` role fields | Metadata | Low | Reused (already deployed) |
| Reporting / Calculated formula fields | Downstream | Low (positive) | Calculated fields become accurate once stamped fields populated |

---

## Estimated Effort *(AI-estimated)*

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` (+ test) | Apex enhancement | M | Add V2 upper-bound + V3 To>From to Role Change branch |
| `PRM_CheckRoleChangeDataParent` / `PRM_CheckRoleChangeData` | IP enhancement | L | Stamp role fields + network dating on terminate/create |
| `PRMLoadPractitionerFacRoleChange` / `PRMTransPracFacRoleChange` / `PRMTransRoleChangeTables` | DataRaptor edits | M | Carry Role Effective From/To through transforms/loads |
| `PRM_OffCycleCredentialing_English` (Correspondence read-only) | OmniScript | S | Read-only display fields |
| `PRM_OffCyclePDAReview_English` (Role Change) | OmniScript | M | Read-only + network add/remove dating |
| `PRM_OffCycleQCReview_English` (Role Change) | OmniScript | S | Read-only display |
| Regression (other request types) | QA | S | Specialty / Name / New Region / New State |
| **Total** | | **~L–XL** | Cross-flow story; sequence Credentialing → PDA → QC |
