# USER STORY: Off-Cycle Name Change — Regression (No Role/Taxonomy Effective Dating)

**Persona:** Credentialing Specialist (primary); Provider Data Admin (PDA) Specialist and Network Management QC Specialist (downstream review personas)
**Priority:** P1
**OmniScript:** `PRM_OffCycleCredentialing_English`, `PRM_OffCyclePDAReview_English`, `PRM_OffCycleQCReview_English`
**Integration Procedures:** N/A (no new logic — regression coverage only)
**Relevant Requirements:**
- `requirements/OffCycle_RoleChange_RoleEffectiveDate_UserStory.md`
- `requirements/OffCycle_SpecialtyChange_TaxonomyEffectiveDate_UserStory.md`
- `requirements/OffCycle_NewRegionState_EffectiveDate_UserStory.md`

> **This is a regression story, not a build story.** Name Change is a demographic update to the practitioner Account. It does **not** create or modify any Level 4 role, taxonomy, or network record, so **no Role or Taxonomy Effective Date applies**. This story exists to guarantee the effective-dating work in the three sibling stories does not leak into or break the Name Change path.

---

## Story

**As a** Credentialing Specialist processing an off-cycle **Name Change**,
**I want** the Name Change path to keep working exactly as it does today — updating the practitioner's legal name with no effective-date prompts and no changes to Level 4 records,
**So that** the new Role/Taxonomy/New-Region effective-dating capabilities do not accidentally surface an effective-date field on, or alter the records produced by, a pure demographic name change.

**Why it matters:** The three sibling stories add effective-date inputs, validation, and Level 4 stamping that are **gated on their own request types** (Role Change, Specialty Change, New Region/State). Because the off-cycle validator (`PRM_EffectiveDateValidationForOffcycle`) and the shared `CollectAndVerifyNewInformation` step are touched by that work, Name Change must be explicitly regression-tested so an unrelated demographic change is never blocked by an effective-date validation or given an effective-date field it should not have.

---

## Scope

| Flow | OmniScript | Affected Step(s) | This story does |
|---|---|---|---|
| Off-Cycle Credentialing | `PRM_OffCycleCredentialing_English` | `NameChangeBlock` (Collect And Verify New Information) | Regression — no new field, no L4 write |
| Off-Cycle PDA Review | `PRM_OffCyclePDAReview_English` | Name Change review | Regression — completes unchanged |
| Off-Cycle QC Review | `PRM_OffCycleQCReview_English` | Name Change review | Regression — completes unchanged |

**In scope:** Regression verification only.
**Out of scope:** Any effective-date capture, validation, or Level 4 stamping (Name Change has none).

---

## Current State (verified in active build)

| Item | Current behavior | Location |
|---|---|---|
| Request type | **Name Change** (formula `NameChange`) | `SelectOffCycleChanges` step |
| Capture UI | `NameChangeBlock` (label "Name Change") with `FirstNameInput`, `MiddleNameInput`, `LastNameInput`, Suffix; gated on `NameChange <> ""` | `CollectAndVerifyNewInformation` step |
| Records affected | Practitioner **Account** legal name fields only | Account (Practitioner record type) |
| Level 4 impact | **None** — no role, taxonomy, or network record is created or modified | — |
| Effective date | **None** (correctly) | — |

---

## Acceptance Criteria

### AC1 — Name Change shows no effective-date field (Pattern A — happy path)
- **Given** a Credentialing Specialist has selected **Name Change** only,
- **When** they reach the Collect And Verify New Information step and edit the practitioner's name,
- **Then** the flow must present the name fields with **no Role, Taxonomy, or New Region effective-date input**,
- **And** the specialist can proceed without entering or being blocked by any effective-date validation.

### AC2 — Name Change writes only the Account name (Pattern E)
When the Name Change flow completes, only the practitioner Account is updated:

**Object: `Account` (Practitioner) — name updated**
| Field | Value |
|---|---|
| `FirstName` | the entered first name |
| `MiddleName` | the entered middle name |
| `LastName` | the entered last name |
| Suffix | the entered suffix |
| (all Level 4 role/taxonomy/network records) | **unchanged** — none created, none terminated |
| `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c` / `PRM_TaxonomyEffectiveFrom__c` / `PRM_TaxonomyEffectiveTo__c` on any HealthcareFacilityNetwork | **not written** |

### AC3 — Effective-date validation does not fire for Name Change (Pattern A — negative)
- **Given** a Name Change submission with no Role Change, Specialty Change, or New Region/State,
- **When** the specialist advances through the flow,
- **Then** the off-cycle effective-date validation must **not** run for the submission and must **not** block progression.

### AC4 — Combined Name Change + a dated request type still validates the dated type (Pattern A — edge case)
- **Given** a submission that selects **Name Change together with** Role Change (or Specialty Change, or New Region/State),
- **When** the specialist completes the flow,
- **Then** the name is updated **and** the dated request type's effective date is still captured, validated, and stamped per its sibling story — the two paths do not interfere.

### AC5 — PDA & QC complete for a Name Change (Pattern A — regression)
- **Given** a PDA Specialist or QC Specialist reviewing a Name Change,
- **When** they open the review step,
- **Then** no effective-date field is shown for the name change and the review flow completes end to end.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes (implements) |
|---|---|---|---|
| `PRM_OffCycleCredentialing_English` — `NameChangeBlock` | OmniScript | **No change** — verify the new effective-date elements remain gated on their own request types and never render for Name Change | AC1 |
| `PRM_EffectiveDateValidationForOffcycle` | Apex | **No change** — the request-type dispatcher must route a Name-Change-only submission past all effective-date branches (no validation). Add a regression test asserting this | AC3 |
| `PRM_OffCyclePDAReview_English`, `PRM_OffCycleQCReview_English` | OmniScript | **No change** — verify Name Change review completes | AC5 |
| Account name write path | (existing) | **No change** — Name Change continues to update the practitioner Account only | AC2 |

---

## Definition of done

- [ ] Name Change (only) shows no effective-date input on any step (AC1).
- [ ] Name Change updates only the Account name; no L4 record is created, terminated, or date-stamped (AC2).
- [ ] The off-cycle effective-date validator does not fire and does not block a Name-Change-only submission (AC3).
- [ ] Name Change combined with a dated request type still validates and stamps the dated type correctly (AC4).
- [ ] Name Change completes end-to-end through Credentialing, PDA, and QC (AC5).
- [ ] Regression test added asserting the validator skips a Name-Change-only submission.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| CQ1 | Confirm Name Change is never expected to carry an effective date at Level 4 (name lives on the Account, not on HCFN). | Scope confirmation | Product/BA |
| CQ2 | For a combined Name Change + dated request type, is a single shared effective date acceptable, or must each dated type keep its own? | Combined-submission UX | Product/BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` | Apex | Low | Must correctly skip Name-Change-only submissions after the sibling changes land |
| `PRM_OffCycleCredentialing_English` | OmniScript | Low | Shared step — verify gating isolates Name Change |
| `PRM_OffCyclePDAReview_English` / `PRM_OffCycleQCReview_English` | OmniScript | Low | Review completes unchanged |
| Practitioner Account | Object | Low | Name-only update (unchanged behavior) |

---

## Estimated Effort *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_EffectiveDateValidationForOffcycle` regression test | Apex test | S | Assert validator skips Name-Change-only |
| Regression pass (Credentialing / PDA / QC) | QA | S | Name-only + Name + dated-type combinations |
| **Total** | | **S** | Regression story — no new build logic |
