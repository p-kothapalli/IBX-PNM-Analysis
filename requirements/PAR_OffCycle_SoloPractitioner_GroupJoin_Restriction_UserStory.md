# USER STORY: Block a Practitioner from Joining Another Solo Practitioner's Practice Location (PAR / Off-Cycle / Add Additional Groups)

**Persona:** Credentialing Specialist
**Priority:** P1
**OmniScript:** `PRM_PractitionerParticipationForm_English_117` (PAR), `PRM_OffCycleCredentialing_English_63` (Off-Cycle), `PRM_AddAdditionalGroups_English_7` (Add Additional Groups) — Recred entry point TBD (see CQ-1)
**Integration Procedures:** `PRM_ValidateTermedGroupAndPL` (extend), `PRM_IPExtractGroupNameBasedOnTINNPI_English_4` (group search, read-only reference)
**Apex (reference only):** `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI`, `PRM_OmniUtils.getGroupDataForTaxId`
**Relevant Requirements:** New business ask (2026-08-19). **Companion story:** `requirements/PAR_OffCycle_SoloPractitioner_M03_InfoCode_UserStory.md` — stamps the M03 – Sole Proprietor info code on the *valid* solo-to-own-solo-location join that this story permits; it reuses the solo-location detection built here, so build this story first. Related: `requirements/PAR_AppReview_TerminatedLocation_InFlight_BugFix.md`, `requirements/Initial_Cred_Add_Practice_Location_User_Stories.md`, `requirements/SOQL/2026-07-16_FC2_EffectiveDates_Repro.md` (documents individual-vs-organization group NPI data anomalies)

---

## Story

**As a** Credentialing Specialist,
**I want** the PAR, Off-Cycle, and Add Additional Groups forms to stop me from attaching a practitioner to a practice location that belongs to a *different* solo practitioner,
**So that** a practitioner is never credentialed under someone else's individual NPI, and our directory, claims routing, and network rosters stay attributable to the correct provider.

**Why it matters:** A solo practitioner's practice location carries that practitioner's own individual (Type 1) NPI as its group NPI. Today nothing stops a specialist from picking such a location for a different practitioner, which silently credentials Practitioner B under Practitioner A's individual NPI. That produces mis-directed claims, incorrect directory listings, and roster/network records that have to be unwound manually — a data-integrity defect that is far cheaper to prevent at intake than to remediate downstream.

---

## Scope

| Flow | OmniScript (active version) | Affected Step | Data Source |
|------|-----------------------------|---------------|-------------|
| PAR — Practitioner Participation | `PRM_PractitionerParticipationForm_English_117` | Group / Practice Location step (`PractionerGroup` block), on Next | `PRM_IPExtractGroupNameBasedOnTINNPI` search → `PRM_ValidateTermedGroupAndPL` validation |
| Off-Cycle Credentialing | `PRM_OffCycleCredentialing_English_63` | Group / Practice Location step (`PractitionerGroup` block), on Next | `PRM_OmniUtils.getGroupDataForTaxId` search → `PRM_ValidateTermedGroupAndPL` validation |
| Add Additional Groups | `PRM_AddAdditionalGroups_English_7` | Group selection step, on Next | `PRM_IPExtractGroupNameBasedOnTINNPI` search (no validation IP wired today) |
| Recred (adding a location during re-credentialing) | **TBD — CQ-1** | TBD | TBD |

**Out of scope:** Provider Change Form, PDM Manual Update, Ancillary flows, and remediation of practitioner-to-location links that already exist in the org (see AC-9 and CQ-7).

---

## Current State (from codebase)

### Solo-practitioner signal already exists in the data model
- A practice location's group NPI is held on `HealthcareFacility.PRM_NpiId__c` → `HealthcareProviderNpi`.
- `HealthcareProviderNpi.NpiType` distinguishes `Individual` (Type 1, a person) from `Organization` (Type 2, a group). No new field is required to detect a solo practice location.
- `HealthcareProviderNpi` carries `PractitionerId` / `AccountId`, so the owning practitioner of an individual NPI is resolvable.

### Group search does not consider NPI type
- `PRM_RecordQueryServiceUtils.getAccountForNPI` matches groups via `HealthcareFacility.PRM_NpiId__r.Npi` with **no `NpiType` filter**; group Accounts are restricted to `RecordType.DeveloperName = PRM_Vendor` only.
- A solo practitioner's practice location is therefore returned by the search exactly like a multi-provider group, with nothing to distinguish it in the results.

### An existing block pattern is available to reuse
- `PRM_ValidateTermedGroupAndPL_English_1` already validates the selected group and practice location and returns boolean flags (`TerminatedAccError`, `TerminatedPLError`) plus detail lists (`TermedAccountInfo`, `TermedPLInfo`).
- Both PAR and Off-Cycle consume those flags through a **Set Errors** element with `validationRequired: Step` bound to the group block (e.g. `SetErrorsTermedGroup` in the PAR form, gated on `TerminatedAccError`), with the message text held in a Set Values variable (`TermedGenericMessage`).
- `PRM_AddAdditionalGroups_English_7` performs the group search but does **not** call the validation IP, so it needs the validation call added, not just the error element.

---

## Acceptance Criteria

> Patterns per `.cursor/skills/user-story-architect/references/ac-pattern-library.md`.
> **Pattern E is intentionally not used:** this story creates and updates no records — its entire outcome is to *prevent* a submission from proceeding. AC-9 asserts the absence of record writes.

**AC-1 — A solo practitioner may join their own solo practice location**

**Given** a Credentialing Specialist is completing a PAR request for a practitioner whose individual NPI is 1234567890,
**When** they select a practice location whose group NPI is that same individual NPI 1234567890 and click Next,
**Then** the form advances to the next step with no error,
**And** the practice location remains selected exactly as chosen.

**AC-2 — Another solo practitioner's practice location is blocked**

**Given** a Credentialing Specialist is completing a PAR request for a practitioner whose individual NPI is 1234567890,
**When** they select a practice location whose group NPI is a *different* practitioner's individual NPI (for example 7890123456) and click Next,
**Then** the form does not advance,
**And** an error is shown against the group / practice location section reading: "This practice location belongs to another solo practitioner and cannot be joined. Please select a group practice location or enter your own solo practice location.",
**And** the blocked practice location is named in the error so the specialist knows which selection to change.

**AC-3 — Group (organization) practice locations are unaffected**

**Given** a Credentialing Specialist is completing a PAR request for any practitioner,
**When** they select a practice location whose group NPI is an organization NPI and click Next,
**Then** the form advances with no solo-practitioner error,
**And** existing terminated-group and terminated-location validations continue to behave exactly as they do today.

**AC-4 — Rules that determine whether a practice location is blocked**

**Given** a Credentialing Specialist has selected one or more practice locations on the PAR, Off-Cycle, or Add Additional Groups form,
**When** they click Next from the group / practice location step,
**Then** each selected practice location is evaluated against the rules below:

- **Practice location's group NPI type =**
  - **Organization (Type 2)** → **Allowed** — not a solo practice location
  - **Blank / no group NPI on the location** → **Allowed** — no solo signal to evaluate (see CQ-3)
  - **Individual (Type 1)** → continue to the ownership rules below
- **Ownership rules (individual/Type 1 group NPI only) =**
  - Individual NPI on the location **equals** the applicant practitioner's own individual NPI → **Allowed** (their own solo practice)
  - Individual NPI on the location **differs** from the applicant's individual NPI **and** that NPI is on record for another practitioner → **Blocked**
  - Individual NPI on the location **differs** from the applicant's individual NPI **and** that NPI is not on record for any practitioner → **Blocked** (fail-safe default, pending CQ-2)
- **Applicant's individual NPI source =**
  - PAR → the individual NPI captured on the form
  - Off-Cycle / Add Additional Groups / Recred → the individual NPI on record for the practitioner the request is being raised for
- **Outcome when any one selected location is Blocked =** the whole step is blocked; every blocked location is listed in the error

**AC-5 — One bad location among several blocks the whole step**

**Given** a Credentialing Specialist has selected three practice locations for a practitioner, two valid group locations and one that belongs to another solo practitioner,
**When** they click Next from the group / practice location step,
**Then** the form does not advance,
**And** the error names only the one location that belongs to another solo practitioner,
**And** the two valid selections stay selected so the specialist does not have to re-enter them.

**AC-6 — The error clears once the selection is corrected**

**Given** a Credentialing Specialist is being blocked because they selected another solo practitioner's practice location,
**When** they remove or replace that location with a valid one and click Next,
**Then** the error disappears and the form advances,
**And** no residual error remains if they later navigate back to the group / practice location step.

**AC-7 — Off-Cycle enforces the same rule**

**Given** a Credentialing Specialist is raising an Off-Cycle request to add a practice location for an existing practitioner,
**When** they select a practice location that belongs to another solo practitioner and click Next,
**Then** the form does not advance and the same error is shown against the group / practice location section.

**AC-8 — Add Additional Groups enforces the same rule**

**Given** a Credentialing Specialist is adding an additional group for an existing practitioner,
**When** they select a group whose practice location belongs to another solo practitioner and click Next,
**Then** the form does not advance and the same error is shown against the group selection section.

**AC-9 — Nothing is created or changed when the submission is blocked**

**Given** a Credentialing Specialist is blocked at the group / practice location step by the solo-practitioner rule,
**When** they abandon the form without correcting the selection,
**Then** no Case Manager, practitioner-to-location link, group, practice location, or network record is created or updated as a result of that attempt,
**And** the practitioner's existing practice locations are left exactly as they were.

**AC-10 — Manually entered practice location with someone else's individual NPI is also blocked**

**Given** a Credentialing Specialist is completing a PAR request and chooses to key in a new practice location rather than pick an existing one,
**When** they enter a group NPI that is a different practitioner's individual NPI and click Next,
**Then** the form does not advance and the same error is shown,
**And** no new group or practice location is created for that entry.

**AC-11 — No override is available**

**Given** a Credentialing Specialist of any permission level is blocked by the solo-practitioner rule,
**When** they attempt to proceed,
**Then** there is no acknowledge-and-continue option and no permission that bypasses the block,
**And** the only path forward is to change the practice location selection.

---

## Technical Implementation (high-level)

> All API names, class names, and IP wiring live here — not in the ACs above.

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRMDRExtractSoloPracticeLocationOwner` | **New** DataRaptor Extract | For the selected `HealthcareFacility` / group Account ids, return `PRM_NpiId__r.Npi`, `PRM_NpiId__r.NpiType`, and the owning `PRM_NpiId__r.PractitionerId` / `AccountId` | Feeds the rules in AC-4. Follow `PRMDR[Action][Object]` convention |
| `PRM_ValidateTermedGroupAndPL` | **New IP version (v2)** | Add a conditional block after the existing termed-group / termed-PL checks that calls the new DR, applies the AC-4 rules, and returns `SoloGroupConflictError` (boolean) + `SoloConflictInfo` (list of offending location names) via a Response Action, mirroring `RATermedGroup` / `RATermedPL` | Single shared enforcement point for PAR and Off-Cycle. Drives AC-2, AC-4, AC-5, AC-7 |
| New input on `PRM_ValidateTermedGroupAndPL` | Modified IP contract | Accept the applicant's individual NPI and practitioner Account id as inputs (`ApplicantIndividualNPI`, `ApplicantAccountId`) so the IP does not have to infer the applicant | Drives AC-4 "Applicant's individual NPI source" |
| `PRM_PractitionerParticipationForm_English_117` → **v118** | New OmniScript version | Pass `PractitionerForm:PractitionerIndividualNPI` into the validation IP; add a `Set Values` entry for the message text and a `Set Errors` element (`validationRequired: Step`, bound to the `PractionerGroup` block) gated on `SoloGroupConflictError`; add the flag to `SV_ResetValues` so it clears on re-entry | Mirrors the existing `SetErrorsTermedGroup` pattern. Drives AC-1, AC-2, AC-5, AC-6, AC-10 |
| `PRM_OffCycleCredentialing_English_63` → **v64** | New OmniScript version | Same wiring on the `PractitionerGroup` block; resolve the applicant's individual NPI from the practitioner record (`HealthcareProviderNpi` where `NpiType = 'Individual'`) rather than a form field | Drives AC-7 |
| `PRM_AddAdditionalGroups_English_7` → **v8** | New OmniScript version | **Add** the `PRM_ValidateTermedGroupAndPL` (v2) call — this OmniScript currently only runs `PRM_IPExtractGroupNameBasedOnTINNPI` — plus the `Set Errors` element | Drives AC-8. Larger change than PAR/Off-Cycle because the validation call does not exist yet |
| Custom Label `PRM_SoloPracticeLocationJoinBlocked` | **New** Custom Label | Holds the AC-2 error text so wording changes do not require an OmniScript redeploy | Drives AC-2 |
| `PRM_RecordQueryServiceUtils.getAccountForNPI` / `getAccountMap` | Modified Apex (optional optimisation) | Return `NpiType` and the owning practitioner alongside each group-search result so the validation IP can reuse it instead of re-querying | Supports AC-4; if taken, unit tests must cover Individual, Organization, and null-NPI locations. Keep `WITH SYSTEM_MODE`/FLS handling consistent with the existing methods |

**Design notes**
- Enforcement belongs in `PRM_ValidateTermedGroupAndPL` rather than in each OmniScript so PAR, Off-Cycle, and Add Additional Groups share one rule implementation and one message.
- Evaluate all selected locations in a single pass over the selection list (the IP already handles primary plus additional addresses via its List Merge steps) — no per-location query loops.
- Because this is a validation-only change, there is no DML and no record recipe; deployment risk is confined to the three OmniScript versions and the IP version.

---

## Definition of done

- [ ] A practitioner can still be attached to their own solo practice location on PAR (AC-1 verified in the target org).
- [ ] Selecting another solo practitioner's practice location blocks Next on PAR with the agreed message naming the offending location (AC-2).
- [ ] Organization-NPI group locations are unaffected, and the existing terminated-group / terminated-location errors still fire as before (AC-3, regression).
- [ ] The rules table in AC-4 is verified for every branch: organization NPI, blank NPI, own individual NPI, another practitioner's individual NPI, and an individual NPI with no owning practitioner.
- [ ] A mixed selection of valid and invalid locations blocks the step and preserves the valid selections (AC-5).
- [ ] The error clears after correction and does not reappear on step re-entry (AC-6).
- [ ] Off-Cycle and Add Additional Groups block identically (AC-7, AC-8).
- [ ] A blocked attempt creates and updates no records — confirmed by querying Case Manager, practitioner-to-location, group, practice location, and network objects after the attempt (AC-9).
- [ ] A manually keyed practice location using another practitioner's individual NPI is blocked and creates nothing (AC-10).
- [ ] No permission set or profile can bypass the block (AC-11).
- [ ] ≥ 85% Apex coverage including bulk (200) and negative paths, if `PRM_RecordQueryServiceUtils` is modified.
- [ ] Only the newly created OmniScript / IP versions are active in the target org; superseded versions are deactivated.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which Recred component actually lets a specialist add a practice location? No Recred OmniScript in the repo performs a group search — `PRM_ReCredUpdate_English_7` and `PRM_RecredQC_English_8` have none. If Recred reuses Add Additional Groups, AC-8 already covers it; if there is a separate entry point, it needs its own OmniScript version. | Determines whether Recred needs a fourth OmniScript change (adds ~M effort) | BA / Technical |
| 2 | An individual (Type 1) group NPI that is not on record for any practitioner — block (fail-safe, assumed in AC-4) or allow? | Changes AC-4's third ownership branch; blocking may surface legitimate data-quality gaps as user-facing errors | Product / Ops |
| 3 | A practice location with no group NPI at all is currently treated as Allowed. Is that acceptable, or should a missing group NPI be blocked for a different reason? | Could widen the story's scope into a general data-completeness rule | Product |
| 4 | If a practitioner has more than one active individual NPI on record, must the location's NPI match **any** of them, or only the one entered on the form? | Affects the comparison logic in AC-4 for Off-Cycle and Add Additional Groups | Technical / Ops |
| 5 | If the location's individual NPI matches the applicant but the group TIN belongs to a different entity, should that still be allowed? (Ownership was confirmed as NPI-match only.) | May require adding a TIN condition to AC-4 | Product / Ops |
| 6 | Does the rule apply on the PNC (Par Non Cred) path through the PAR form, which uses the same group type-ahead but a different downstream flow? | Determines whether the PNC branch needs separate test coverage | BA |
| 7 | Should a one-time report of practitioners already linked to another solo practitioner's location be produced for business review? (Scope today is new submissions only.) | Adds a reporting deliverable outside this story | Product / Ops |
| 8 | Should downstream review steps (Application Review, PDA Review) also block if a specialist adds such a location after intake? | Would extend scope beyond the three intake forms | Product |
| 9 | Confirm the exact final wording of the error message before the Custom Label is created. | Wording change after deployment is a label-only edit, so low risk — but confirm before QA writes tests | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_ValidateTermedGroupAndPL` | Integration Procedure | **HIGH** | Shared by PAR and Off-Cycle. A regression here breaks the existing terminated-group and terminated-location blocks on both flows |
| `PRM_PractitionerParticipationForm_English_117` | OmniScript | **HIGH** | New version required; highest-volume credentialing intake form |
| `PRM_OffCycleCredentialing_English_63` | OmniScript | **HIGH** | New version required |
| `PRM_AddAdditionalGroups_English_7` | OmniScript | **MEDIUM** | New version required, and gains a validation IP call it does not have today |
| `PRMDRExtractSoloPracticeLocationOwner` | DataRaptor | **LOW** | New, read-only extract; no existing consumers |
| `PRM_RecordQueryServiceUtils` | Apex | **MEDIUM** | Only if the optional optimisation is taken; `getAccountForNPI` / `getAccountMap` feed the group type-ahead on PAR |
| `PRM_OmniUtils.getGroupDataForTaxId` | Apex | **LOW** | Off-Cycle's search path; unchanged unless the same optimisation is applied there |
| `HealthcareProviderNpi` / `HealthcareFacility` | Objects | **LOW** | Read-only use of `NpiType`, `Npi`, `PractitionerId`, `PRM_NpiId__c` — no schema change |

---

## Estimated Effort

**AI-estimated — validate with team.**

| Component | Change Type | Effort | Story Points | Notes |
|-----------|-------------|--------|--------------|-------|
| `PRMDRExtractSoloPracticeLocationOwner` | New DataRaptor Extract | **L** | 3 | New DR with NPI-type and owning-practitioner fields |
| `PRM_ValidateTermedGroupAndPL` v2 | New IP version | **XL** | 5 | New conditional block, rules logic, new inputs, new response flags; must not regress the termed checks |
| `PRM_PractitionerParticipationForm_English_117` → v118 | New OmniScript version | **L** | 3 | Set Values + Set Errors + reset wiring, following the existing termed-group pattern |
| `PRM_OffCycleCredentialing_English_63` → v64 | New OmniScript version | **L** | 3 | Same wiring, plus resolving the applicant's individual NPI from the practitioner record |
| `PRM_AddAdditionalGroups_English_7` → v8 | New OmniScript version | **XL** | 5 | Validation IP call does not exist here yet, so more than an error-element addition |
| Custom Label | New Custom Label | **S** | 1 | Error message text |
| `PRM_RecordQueryServiceUtils` | Modified Apex (optional) | **L** | 3 | Only if the search-result optimisation is taken; requires ≥85% coverage incl. bulk |
| Testing — functional + regression | QA | **XL** | 5 | Three flows × the five AC-4 branches, plus terminated-group/location regression |

**Total Estimated Effort:** 25–28 story points — **XXL** overall (~6–7 engineer-days build + ~2 days QA). Drops by ~3 points if the optional Apex optimisation is deferred, and rises by ~M–L if CQ-1 uncovers a separate Recred entry point.
