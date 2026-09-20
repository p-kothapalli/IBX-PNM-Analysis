# USER STORY: Data Model — Add the `PRM_BypassPNC__c` Rollup-Bypass Flag to the Practitioner Account

**Persona:** PDM Specialist (acting as data steward); Admin for the metadata build
**Priority:** P0 (foundational — blocks the bypass-aware rollup in US4/US5/US5B and the participation-flow determination in US3)
**OmniScript:** N/A (data model / metadata story)
**Integration Procedures:** N/A
**Relevant Requirements:** `PRM_PNC_Logic_Change_Implementation_Plan.md` (US1 AC4/AC5, US3, US4, US5, §5.1b), `PRM_PNC_Analysis.md`, `PRM_PNC_US5_OmniScript_Impact_Analysis.md`

> **Vertical:** Provider Network Management (PNM) — Health Cloud + PNM managed package.
> **Note:** This story extracts and expands what was previously captured inline as US1 AC4/AC5 in `PRM_PNC_Logic_Change_Implementation_Plan.md` into a standalone data-model story. It defines **only the field and its access**; the behaviour that consumes the field lives in US3 (participation/creation), US4 (RCAT/batch rollup), US5 (HealthcareFacility trigger), and US5B (PPL trigger).
>
> **Revision (naming + semantics changed):** the field is now **`PRM_BypassPNC__c`** (was `PRM_PNCAnyLocation__c`) and its meaning is a **bypass switch, not an ALL/ANY switch**. When checked, it **bypasses the automatic PNC rollup trigger logic** for that practitioner — the practitioner's PNC is managed manually and is **not** recomputed/overwritten from their practice locations, regardless of whether they sit in PNC or non-PNC locations. The default rollup (unchecked) remains the legacy **"all participating locations must be PNC"** rule. The previously proposed "any location" mode is **removed**.
>
> **Revision 2 (Jul 2026 — Override side effects confirmed by business):** turning this flag **ON = force the practitioner INTO PNC**, which also **blanks `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c`**; turning it **OFF within 30 days of the Override-ON date** (when the practitioner was "Credentialed" immediately before) **restores** those two values from **field history** (no new snapshot fields — decision Jul 2026). The 30-day window is measured from the **Override-ON date** (the `AccountHistory.CreatedDate` of the "Credentialed→blank" status change), and the restore applies **only to this manual Override** — not to rollup-driven PNC exits. Those side-effect behaviours are owned by `PRM_PNC_CredentialingStatus_Blank_User_Story.md` and implemented by `PRM_BypassPNC_UpdateFlow_User_Story.md`. **Prerequisite for the restore:** history tracking is **already ON** for `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c` (verified in metadata); it must additionally be enabled on this flag (`PRM_BypassPNC__c`), with retention ≥ 30 days.

---

## Story

**As a** PDM Specialist (acting as data steward),
**I want** a per-practitioner flag on the Practitioner Account that turns off the automatic PNC rollup for that practitioner,
**So that** exception-case practitioners can have their PNC set and held manually without the location-driven trigger overwriting it, while every other practitioner keeps today's automatic "all locations must be PNC" behavior.

**Why it matters:** PNC is moving from the vendor Account to the practice location (HealthcareFacility), and triggers will recompute each practitioner's PNC from their locations. Some practitioners must not be driven by that rollup — they may sit in a PNC location or in no PNC locations, but their PNC status is set by hand for business reasons. A dedicated bypass flag makes that override explicit, auditable, reportable, and safe to default off (no behavior change for existing practitioners).

---

## Scope

| Object | Field | Applies To | Consumed By |
|--------|-------|-----------|-------------|
| Account (Person Account — Practitioner) | `PRM_BypassPNC__c` | Practitioner record type only | `pncOnlyPractitioner` (US4), `updateAccountPNCHelper` / `getPIdToHCPFList` (US4), HealthcareFacility trigger recompute (US5), PPL trigger recompute (US5B), Account-trigger recompute, `SV_PNCFlag`/`PNCFlag` (US3) |

---

## Current State (from codebase)

- The field `PRM_BypassPNC__c` does **not** exist anywhere in the repo (verified — no metadata, no permission-set entries). Neither does the previously proposed `PRM_PNCAnyLocation__c`.
- The practitioner PNC rollup today is **hard-coded "all"** with **no bypass path**:
  - `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner()` — starts `true`, sets `false` when any `PRM_PractitionerPracticeAffiliation` has `Account.PRM_PNC__c = false`; no affiliations → `false`.
  - `PRM_CommonUtils.updateAccountPNCHelper()` / `getPIdToHCPFList()` — same "all" logic, source `Account.PRM_PNC__c`.
  - There is currently **no way** to stop these from overwriting a practitioner's PNC — the bypass flag introduces that path.
- `Account.PRM_PNC__c` (practitioner rollup) exists today and has FLS in these permission sets: **edit** — `PRM_DataModifyAll`, `PRM_CredentialingUser`, `PRM_ProviderDataAdmin`, `PRM_NetworkManagementQC`, `PRM_AncillaryCredSpecialist`, `PRM_RebtuttalSpecialist`; **read-only** — `PRM_DataViewAll`. The new bypass flag mirrors this audience.

---

## Acceptance Criteria

**AC-1 — Create the `PRM_BypassPNC__c` field on Account** *(Pattern B — Field Creation)*

- **API Name:** `PRM_BypassPNC__c` *(org convention requires the `PRM_` prefix + `__c`; user-requested name "BypassPNC")*
- **Object:** Account (Person Account — used for Practitioner records)
- **Type:** Checkbox
- **Label:** Bypass PNC
- **Default:** Unchecked (false)
- **Help text (customer-facing):** "When checked, this practitioner's PNC is managed manually and is NOT automatically recalculated from their practice locations. When unchecked (default), the practitioner is PNC only when all of their participating practice locations are PNC."
- **Description (admin-facing):** "Per-practitioner bypass switch for the PNC rollup. Unchecked = automatic 'all locations PNC' rollup (default, matches legacy behavior). Checked = the HealthcareFacility trigger, PPL trigger, Account trigger, and RCAT/batch rollup skip this practitioner and never overwrite Account.PRM_PNC__c; PNC is set manually. Introduced with the PNC field migration (PNC moved from vendor Account to HealthcareFacility)."
- **Track History:** true — **required** (the 30-day Override restore reads this flag's change timestamp from field history; `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c` history tracking is already ON, verified in metadata)
- **Required:** false
- **Applicable Record Type:** Practitioner only (not Vendor/Group). Add to the Practitioner Account page layout in the credentialing/participation section; do **not** add to the Vendor/Group layout.

**AC-2 — Field Access & Permission Sets** *(Pattern C — FLS)*

- **PRM_DataModifyAll, PRM_ProviderDataAdmin, PRM_CredentialingUser, PRM_NetworkManagementQC, PRM_AncillaryCredSpecialist, PRM_RebtuttalSpecialist:**
  - Field level: **Read and Edit** on `Account.PRM_BypassPNC__c` (mirrors their existing edit access to `Account.PRM_PNC__c`)
- **PRM_DataViewAll:**
  - Field level: **Read only** on `Account.PRM_BypassPNC__c` (mirrors its read-only access to `Account.PRM_PNC__c`)
- Object-level access is unchanged (the field rides on existing Account access in each permission set).

**AC-3 — Default preserves existing behavior (no backfill)** *(Pattern A — Behavioural)*

**Given** the bypass field is deployed to production,
**When** the deployment completes,
**Then** every existing practitioner has `PRM_BypassPNC__c` unchecked,
**And** no data backfill or mass update is run against the field,
**And** the practitioner PNC rollup continues to behave exactly as before (all participating locations must be PNC) until a practitioner is explicitly flagged.

**AC-4 — When bypass is on, the rollup trigger does not touch the practitioner's PNC** *(Pattern A — Behavioural)*

**Given** a practitioner whose "Bypass PNC" flag is checked,
**When** any event that would normally recompute PNC occurs (a practice location's PNC changes, the practitioner is added to or removed from a location, or the practitioner record is re-evaluated),
**Then** the system does **not** recalculate or overwrite that practitioner's PNC value,
**And** the manually set `Account.PRM_PNC__c` value is preserved,
**And** this holds whether the practitioner is in a PNC location, a mix, or no PNC locations at all.

**AC-5 — Turning bypass off restores automatic rollup** *(Pattern A — Behavioural)*

**Given** a practitioner whose "Bypass PNC" flag is unchecked (or is changed from checked to unchecked),
**When** the next PNC-affecting event occurs (or the flag change itself is saved),
**Then** the practitioner's PNC is recomputed by the default rule (PNC only when all participating locations are PNC),
**And** the automatically computed value replaces any prior manual value.

**AC-6 — Flag is visible/editable to the credentialing/PDM audience** *(Pattern A — Behavioural)*

**Given** a PDM Specialist (or Credentialing Specialist) opens a Practitioner record,
**When** they view the credentialing/participation section of the Practitioner Account,
**Then** they can see the "Bypass PNC" checkbox and its help text,
**And** they can check or uncheck it and save,
**And** a read-only user (PRM_DataViewAll) can see the value but cannot change it.

**AC-7 — Flag is available for reporting and list views** *(Pattern A — Behavioural)*

**Given** the field is created,
**When** an admin builds a report or list view on Practitioner Accounts,
**Then** "Bypass PNC" is available as a filterable and displayable column,
**And** field history shows who changed the flag and when.

**AC-8 — Field is not added to Vendor/Group accounts** *(Pattern A — Edge case)*

**Given** the field is created on the Account object,
**When** a user opens a Vendor/Group Account record,
**Then** the "Bypass PNC" checkbox does **not** appear on the Vendor/Group page layout,
**And** the flag is understood to apply to Practitioner records only.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `Account.PRM_BypassPNC__c` | New custom field (Checkbox) | Create per AC-1; default false; history tracking on | Drives AC-1, AC-3, AC-7 |
| Practitioner Account page layout | Layout | Add field to credentialing/participation section (Practitioner RT only) | Drives AC-6, AC-8 |
| `PRM_DataModifyAll`, `PRM_ProviderDataAdmin`, `PRM_CredentialingUser`, `PRM_NetworkManagementQC`, `PRM_AncillaryCredSpecialist`, `PRM_RebtuttalSpecialist` | Permission set FLS | Add Read+Edit on the new field | Mirrors existing `Account.PRM_PNC__c` grants — Drives AC-2 |
| `PRM_DataViewAll` | Permission set FLS | Add Read-only on the new field | Mirrors existing `Account.PRM_PNC__c` grant — Drives AC-2 |

**Consumers (out of scope for this story — cross-referenced; note the semantics are now "skip when bypass = true", not "ALL vs ANY"):**
- US3 — `PRM_PractitionerScreenRecordCreation` (`SV_PNCFlag`/`PNCFlag`): at creation, if bypass is on, do not auto-derive PNC from the rollup.
- US4 — `pncOnlyPractitioner`, `updateAccountPNCHelper`, `getPIdToHCPFList`: short-circuit and leave `Account.PRM_PNC__c` untouched for practitioners with bypass = true.
- US5 — HealthcareFacility trigger recompute: exclude bypassed practitioners from the recompute set.
- US5B — PPL (HealthcarePractitionerFacility) trigger recompute: on add/remove of a practitioner-location, skip recompute for bypassed practitioners.
- Account trigger — when `PRM_BypassPNC__c` flips true→false, trigger a one-time recompute (AC-5); when false→true, stop managing PNC (AC-4).
- Credentialing-status / recred-due-date side effects — Override ON blanks `PRM_CredentialingStatus__c` + `PRM_ReCredDueDate__c`; Override OFF within 30 days restores them from field history. Owned by `PRM_PNC_CredentialingStatus_Blank_User_Story.md`, implemented in `PRM_BypassPNC_UpdateFlow_User_Story.md`. This story only guarantees the **history-tracking prerequisite**.

---

## Definition of Done

- [ ] `Account.PRM_BypassPNC__c` created (Checkbox, default false, history tracking on) and deployed.
- [ ] Added to the Practitioner Account page layout only; not on Vendor/Group layout.
- [ ] FLS added to the 6 edit permission sets and the 1 read-only permission set, mirroring `Account.PRM_PNC__c`.
- [ ] Verified in the org: unchecked for all existing practitioners; no backfill run.
- [ ] Field available in reports/list views; field history visible.
- [ ] Cross-referenced from `PRM_PNC_Logic_Change_Implementation_Plan.md` US1 (this story supersedes US1 AC4/AC5 for the field spec) and the renamed references updated across the PNC story set.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the field label "Bypass PNC" and API name `PRM_BypassPNC__c` are acceptable to naming standards (org convention forces the `PRM_` prefix). | Field naming; downstream references | Technical / BA |
| 2 | When bypass flips from checked → unchecked, should PNC recompute immediately (on save), or only on the next location event? | Account-trigger design (AC-5) | BA / Technical |
| 3 | While bypass is on, is `Account.PRM_PNC__c` freely editable by the specialist audience (manual control), or locked to Admin/PDM only? | FLS / manual-edit governance | Ops / Security |
| 4 | Should the switch be editable by all six specialist permission sets, or restricted to a narrower set (e.g., only Admin/PDM)? | FLS scope | Ops / Security |
| 5 | Is field history tracking approved (adds to the Account's tracked-field count)? | History tracking limit on Account | Admin |
| 6 | Are there existing practitioners that should be pre-flagged as bypassed at go-live, or is unchecked-for-all the correct starting state? | Data setup at cutover | Product / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| Account (Practitioner) | Object / Field | HIGH | New control field that governs whether the PNC rollup runs for a practitioner |
| 7 permission sets | Metadata (FLS) | LOW | Add one field-permission entry each |
| Practitioner Account layout | Layout | LOW | Add one checkbox to one layout |
| Rollup Apex / triggers / participation flow | Apex / OmniStudio | (Downstream) | Consume the field (skip-when-bypass) — covered by US3/US4/US5/US5B, not this story |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `Account.PRM_BypassPNC__c` | Custom field + history tracking | S | AI-estimated — validate with team |
| Page layout update | Config | S | Practitioner layout only |
| Permission set FLS (7 sets) | Config | S–M | Repetitive but mechanical; 7 files |

**Total Estimated Effort:** **S–M** (config only, no code in this story) — AI-estimated, validate with team.

---

## Related User Stories

- `PRM_BypassPNC_UpdateFlow_User_Story.md` — record-page Flow button for cred/PDM specialists to toggle this flag and set PNC manually while bypassed (consumes AC-4/AC-5).
- `PRM_PNC_Logic_Change_Implementation_Plan.md` — US1 (data model), US3 (participation/creation), US4 (RCAT/batch rollup — bypass-aware), US5 (HealthcareFacility trigger), US5B (PPL trigger), §5.1b (worked example — **update ALL/ANY wording to bypass**).
- `PRM_PNC_Analysis.md` — target-state rollup rule.
- `PRM_PNC_US5_OmniScript_Impact_Analysis.md` — OmniScript/flow impact of the bypass-aware trigger.
- `PRM_PNC_AppReview_Flows_User_Stories.md` — US-AR1/US-AR2/US-AR3 reference the old ANY-override; the "any location" clauses must be re-worded to the bypass model.

> **Rename impact (follow-up):** `PRM_PNCAnyLocation__c` and the "any location" rollup mode are referenced in 6 other requirement files — `PRM_PNC_AppReview_Flows_Update_Analysis.md`, `PRM_PNC_AppReview_Flows_User_Stories.md`, `PRM_PNC_Logic_Change_Implementation_Plan.md`, `PRM_PNC_US5_OmniScript_Impact_Analysis.md`, `Provider_Change_Form_PNC_Deep_Dive_Analysis.md`, `PRM_PNC_Analysis.md`. They should be updated to `PRM_BypassPNC__c` + bypass semantics for consistency.
