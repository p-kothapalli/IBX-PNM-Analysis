# USER STORY US-AR6: Suppress the Display-in-Directory indicator on any record that is flagged PNC

> Authored with the **User Story Solution Architect** (v1.10). Vertical: **Provider Network Management (PNM)**.
> **Builds on the PNC migration epic** (`PRM_PNC_AppReview_Flows_User_Stories.md`): PNC (Par Non Cred) now lives on the **practice location** (`HealthcareFacility.PRM_PNC__c`) and rolls up to the **practitioner** (`Account.PRM_PNC__c`). This story adds the **directory-visibility consequence** of that flag on each record that carries it.
> **Components verified** against org metadata (`code-review-graph` returned no nodes for these Apex classes; verified via direct metadata search — see Current State for exact paths).

**Persona:** PDM Specialist
**Priority:** P0
**Objects:** `Account` (Practitioner record type), `HealthcareFacility` (practice location)
**Triggers/Handlers:** `PRM_AccountTrigger` → `PRM_AccountTriggerHandler` → `PRM_AccountTriggerHelper`; `PRM_HealthcareFacilityTrigger` → `PRM_HCFacilityTriggerHandler` → `PRM_HCFacilityTriggerHelper`
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_User_Stories.md` (US1 location PNC field, US4 rollup, US5/US5B triggers), `PRM_PNC_Logic_Change_Implementation_Plan.md`, `PRM_PNCAnyLocation_DataModel_User_Story.md` (`PRM_BypassPNC__c`)

---

## Revision History

| Rev | Date | Change |
|---|---|---|
| **Rev 2** | 2026-08-18 | **Rule rewritten to same-record only.** Suppression is now driven by **each record's own PNC flag** — a practitioner's indicator follows the *practitioner* PNC flag, and a practice location's indicator follows the *practice location* PNC flag. The previous cross-object rule (location PNC → practitioner-practice-location indicator) is **removed**, and the practitioner-practice-location (PPL) indicator is **out of scope**. Suppression is **one-way** (clearing PNC does not restore the indicator), a manual attempt to re-enable on a PNC record is **blocked with an error**, the practitioner rule applies to the **Practitioner record type only**, a **one-time backfill** is in scope, and `PRM_DirectoryIndicatorAccountExecutor` is **updated to skip PNC practitioners**. Consequence: no cross-object fan-out and no async chaining batch are required. |
| Rev 1 | 2026-07-13 | Original — suppressed `HealthcarePractitionerFacility.IsDirectoryPrint` from the parent location's PNC, with a retroactive fan-out batch on location PNC flips. |

---

## Story

**As a** PDM Specialist,
**I want** the Display-in-Directory indicator on a record to be turned off automatically as soon as that record is flagged PNC (Par Non Cred) — the practitioner's own indicator when the practitioner is PNC, and the practice location's own indicator when the location is PNC,
**So that** PNC providers and PNC locations are never published to the member/provider directory, without anyone having to remember to clear the indicator by hand.

**Why it matters:** PNC means the provider or location participates without full individual credentialing, so it must not surface in the member-facing directory. PNC is set from several paths — manually, by the location-driven rollup, by the bypass override, and by RCAT/batch recalculation — and today none of them touch the directory indicator. Every path that can set PNC is therefore a way to leak a non-credentialed provider into published directory data, which is a member-facing accuracy and compliance exposure. Keying the indicator to the **same record's** PNC flag makes the rule simple, auditable, and independent of affiliation structure.

---

## Scope

Two independent, same-record rules. Neither reads the other object.

| # | Rule | Source flag | Suppressed indicator |
|---|---|---|---|
| **R1** | A **practitioner** flagged PNC is suppressed from the directory | Practitioner PNC flag on the practitioner record | Display-in-Directory on that **same practitioner record** |
| **R2** | A **practice location** flagged PNC is suppressed from the directory | PNC flag on the practice location record | Display-in-Directory on that **same practice location record** |

**Behavioural decisions (ratified 2026-08-18):**

| Decision | Ruling |
|---|---|
| Direction | **One-way.** Clearing PNC does **not** restore the indicator — re-enabling directory display is a deliberate business action. |
| Manual override | **Blocked with an error.** A save that tries to turn the indicator on while the record is still PNC is rejected with an explanatory message. |
| Practitioner account scope | **Practitioner record type only.** Vendor/Group accounts are excluded. |
| Existing data | **One-time backfill in scope** for records already PNC with the indicator still on. |
| Source of the PNC value | **Irrelevant** — the rule reacts to the flag's resulting value, whether set manually, by the rollup, by the bypass override, or by batch recalculation. |

**In scope:** the practitioner record's own directory indicator; the practice location record's own directory indicator; a one-time backfill; excluding PNC practitioners from the existing Active + Participating directory-indicator data fix.

**Out of scope:** the **practitioner-practice-location (PPL) affiliation** directory indicator (`HealthcarePractitionerFacility.IsDirectoryPrint`) — deliberately untouched by this story after Rev 2; network-level indicators (`HealthcareFacilityNetwork`); contact-method indicators (`PRM_ContactMethod__c.PRM_IsDirectoryPrint__c`); Vendor/Group account indicators; the PNC rollup logic itself (owned by US4 + `PRM_PractitionerPNCBatch`); restoring the indicator when PNC is cleared.

---

## Current State (from codebase)

**Both indicator fields already exist and both default to ON — nothing clears them from PNC today.**

| Field | Type / default | Description in metadata |
|---|---|---|
| `Account.PRM_IsDirectoryPrint__c` | Checkbox, default **true**, history tracked | "Determines if Practitioner should display in Directory." Label: *Display in Directory* |
| `HealthcareFacility.PRM_IsDirectoryPrint__c` | Checkbox, default **true**, history tracked | "Indicates if the record should be displayed in Provider Directory." Label: *Display in Directory* |
| `Account.PRM_PNC__c` | Checkbox, default false, history tracked | "For Vendor Determines the Group is PNC and for Practitioner, Determines if Practitioner is PNC Only." |
| `HealthcareFacility.PRM_PNC__c` | Checkbox, default false | "Indicates this practice location participates in the network without full individual credentialing (Par Non Cred)." |

**PNC is already maintained by live Apex — this story consumes its result, it does not change it:**

- `PRM_PracFacilityTriggerHandler.updateAccountPNC()` (Story# 1089847) → `PRM_CommonUtils.updateAccountPNCHelper()` (Story# 1089847, 1462313) filters to `Account.PRM_BypassPNC__c = false` + RecordType `PRM_Practitioner`, then hands off to `PRM_PractitionerPNCBatch`.
- `PRM_PractitionerPNCBatchHelper` computes `Account.PRM_PNC__c` = true only when the practitioner has at least one active facility and **every** active facility is PNC.
- `PRM_AccountTriggerHelper.updateAccountPNC()` (Story# 1462313) recalculates on the `PRM_BypassPNC__c` true→false transition, from `PRM_AccountTriggerHandler.afterUpdate`.
- Other writers: `PRM_RecalculatePNCFlowAction`, `PRM_PractitionerPNCDailyBatchHelper`, `PRM_PNCPDABatchHelper`, `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner()`.

**Available insertion points (both already have before-context methods delegating to a helper):**

- `PRM_AccountTriggerHandler.beforeInsert` / `beforeUpdate` → `PRM_AccountTriggerHelper` (currently `setAccIdentifier`, `assignPartCodeBasedOnAccType`).
- `PRM_HCFacilityTriggerHandler.beforeInsert` / `beforeUpdate` → `PRM_HCFacilityTriggerHelper` (currently `assignPracLocNameAndAddress`, `setPLNumberOnCreation`, `populatePRMExternalId`, `restrictUserToModifyHCFName`).

**Two live constraints the developer must respect:**

1. **`PRM_HealthcareFacilityTrigger` exits early** when `PRM_TriggerContextControl.inBulkContext()` or `PRM_TriggerContextControl.suppressHCFTrigger` is set, and `PRM_HCFacilityTriggerHandler.beforeUpdate` is additionally gated on `!PRM_GlobalConstant.byPassVal`. Any bulk/integration path that sets location PNC under those guards will **not** fire R2 — the backfill must cover it.
2. **Conflict — existing data fix reverses the rule.** `PRM_DirectoryIndicatorAccountExecutor` (Bug 1271361) queries Practitioner Accounts where `IsActive = true AND PRM_ParticipationStatus__c = 'Participating' AND PRM_IsDirectoryPrint__c = false` and **forces the indicator back to `true`**. A PNC practitioner who is active and participating would be un-suppressed by that job. It must exclude PNC practitioners (AC-10). `DFX_DirectoryIndicatorAccountExecutor` is a sibling copy of the same fix and needs the same review.

---

## Acceptance Criteria

**AC-1 — A practitioner flagged PNC is suppressed from the directory (happy path)**

**Given** a practitioner whose Display-in-Directory indicator is on,
**When** that practitioner is flagged PNC,
**Then** the Display-in-Directory indicator on that practitioner is turned off in the same save,
**And** the practitioner is no longer published to the provider directory.

**AC-2 — A practice location flagged PNC is suppressed from the directory (happy path)**

**Given** a practice location whose Display-in-Directory indicator is on,
**When** that practice location is flagged PNC,
**Then** the Display-in-Directory indicator on that practice location is turned off in the same save,
**And** the practice location is no longer published to the provider directory.

**AC-3 — The rule reacts to the flag regardless of who set it**

**Given** a practitioner who is not currently PNC,
**When** the practitioner becomes PNC by any means — set by hand, derived from their practice locations, forced on by the manual PNC override, or recalculated by a scheduled job,
**Then** the Display-in-Directory indicator on that practitioner is turned off,
**And** the outcome is identical for every one of those paths.

**AC-4 — Records that are not PNC are left alone**

**Given** a practitioner and a practice location that are both not PNC,
**When** either record is created or updated,
**Then** the Display-in-Directory indicator on each remains as the business set it,
**And** no automatic change is made to either indicator.

**AC-5 — Suppression is one-way; clearing PNC does not republish (edge case)**

**Given** a practitioner or practice location that was suppressed because it was PNC,
**When** the PNC flag is later cleared,
**Then** the Display-in-Directory indicator stays off,
**And** republishing to the directory requires a deliberate action by the PDM Specialist.

**AC-6 — A PNC practitioner cannot be manually republished (negative)**

**Given** a practitioner that is currently flagged PNC and suppressed from the directory,
**When** someone attempts to turn the Display-in-Directory indicator back on while the practitioner is still PNC,
**Then** the save is rejected with a message explaining that a PNC practitioner cannot be displayed in the directory,
**And** the indicator remains off.

**AC-7 — A PNC practice location cannot be manually republished (negative)**

**Given** a practice location that is currently flagged PNC and suppressed from the directory,
**When** someone attempts to turn the Display-in-Directory indicator back on while the location is still PNC,
**Then** the save is rejected with a message explaining that a PNC practice location cannot be displayed in the directory,
**And** the indicator remains off.

**AC-8 — The two rules are independent; no cross-object suppression (edge case)**

**Given** a practitioner who is not PNC but is affiliated to a practice location that is PNC,
**When** the location's PNC flag is applied,
**Then** only the practice location's own Display-in-Directory indicator is turned off,
**And** the practitioner's Display-in-Directory indicator is unchanged,
**And** the practitioner's affiliation-level directory indicator is unchanged.

**AC-9 — Vendor and group accounts are not affected (edge case)**

**Given** a vendor or group account that is flagged PNC,
**When** the account is saved,
**Then** its Display-in-Directory indicator is unchanged,
**And** only practitioner records are subject to this rule.

**AC-10 — The Active-and-Participating directory correction no longer republishes PNC practitioners (negative)**

**Given** a practitioner that is PNC, active, and participating, suppressed from the directory by this rule,
**When** the routine correction job that restores the Display-in-Directory indicator for active participating practitioners runs,
**Then** that practitioner is skipped and stays suppressed,
**And** non-PNC active participating practitioners are still corrected as they are today.

**AC-11 — Records already PNC are corrected by a one-time backfill**

**Given** practitioners and practice locations that were already flagged PNC before this rule existed and still have the Display-in-Directory indicator on,
**When** the one-time correction is run,
**Then** the Display-in-Directory indicator is turned off on every one of those records,
**And** a record of what changed is produced for review,
**And** records that are not PNC are not modified.

**AC-12 — Bulk PNC changes complete without failure (scale)**

**Given** a large volume of practitioners and practice locations being flagged PNC in a single operation, such as a scheduled rollup run,
**When** the operation completes,
**Then** the Display-in-Directory indicator is off on every newly-PNC record,
**And** no records fail because of processing limits.

---

### Pattern E — Record & Field Specification

Every field written by this story. No other field is modified.

**Object 1 — `Account` (Practitioner record type only)**

| Field | API Name | Value written | Condition | AC |
|---|---|---|---|---|
| Display in Directory | `PRM_IsDirectoryPrint__c` | `false` | `PRM_PNC__c = true` AND `RecordTypeId = PRM_GlobalConstant.RECTYPEID_PRACTITIONER` AND `PRM_IsDirectoryPrint__c = true` (on insert, or on update where PNC is true) | AC-1, AC-3, AC-11, AC-12 |
| Display in Directory | `PRM_IsDirectoryPrint__c` | *no write* — save rejected via `addError` | `PRM_PNC__c = true` (unchanged) AND `PRM_IsDirectoryPrint__c` changed `false → true` | AC-6 |
| Display in Directory | `PRM_IsDirectoryPrint__c` | *no write* | `PRM_PNC__c = false`, including the `true → false` transition | AC-4, AC-5 |
| Display in Directory | `PRM_IsDirectoryPrint__c` | *no write* | `RecordTypeId != PRM_GlobalConstant.RECTYPEID_PRACTITIONER` | AC-9 |

**Object 2 — `HealthcareFacility` (practice location)**

| Field | API Name | Value written | Condition | AC |
|---|---|---|---|---|
| Display in Directory | `PRM_IsDirectoryPrint__c` | `false` | `PRM_PNC__c = true` AND `PRM_IsDirectoryPrint__c = true` (on insert, or on update where PNC is true) | AC-2, AC-11, AC-12 |
| Display in Directory | `PRM_IsDirectoryPrint__c` | *no write* — save rejected via `addError` | `PRM_PNC__c = true` (unchanged) AND `PRM_IsDirectoryPrint__c` changed `false → true` | AC-7 |
| Display in Directory | `PRM_IsDirectoryPrint__c` | *no write* | `PRM_PNC__c = false`, including the `true → false` transition | AC-4, AC-5 |

**Objects explicitly NOT written**

| Object | Field | Reason |
|---|---|---|
| `HealthcarePractitionerFacility` | `IsDirectoryPrint` | Out of scope from Rev 2 — no cross-object rule (AC-8) |
| `HealthcareFacilityNetwork` | any directory field | Out of scope |
| `PRM_ContactMethod__c` | `PRM_IsDirectoryPrint__c` | Out of scope — owned by existing contact-method termination logic in `PRM_CommonUtils` |
| `Account` (Vendor / Group) | `PRM_IsDirectoryPrint__c` | Practitioner record type only (AC-9) |

---

## Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AccountTriggerHelper` | Modified Apex (helper) | New method, e.g. `suppressDirectoryPrintForPNC(newItems, oldItems)`. On before-insert/before-update, for `RECTYPEID_PRACTITIONER` records only: if `PRM_PNC__c = true` and `PRM_IsDirectoryPrint__c = true`, set it to `false`; if `PRM_PNC__c` was already `true` and `PRM_IsDirectoryPrint__c` changed `false → true`, `addError` on the field with a business message. Pure in-memory field assignment — no SOQL, no DML. | AC-1, AC-3, AC-4, AC-6, AC-9 |
| `PRM_AccountTriggerHandler` | Modified Apex (trigger handler) | Wire the new helper method into `beforeInsert` and `beforeUpdate` alongside `assignPartCodeBasedOnAccType`. | AC-1, AC-6 |
| `PRM_HCFacilityTriggerHelper` | Modified Apex (helper) | Mirror method, e.g. `suppressDirectoryPrintForPNC(newItems, oldItems)`, with the same set/`addError` semantics against `HealthcareFacility.PRM_PNC__c` / `PRM_IsDirectoryPrint__c`. No record-type filter. | AC-2, AC-4, AC-5, AC-7 |
| `PRM_HCFacilityTriggerHandler` | Modified Apex (trigger handler) | Wire into `beforeInsert` and `beforeUpdate`. **Do not** place it behind the `PRM_GlobalConstant.byPassVal` guard that wraps `restrictUserToModifyHCFName`, so the rule still applies on bypassed name-edit paths. Note the trigger-level `PRM_TriggerContextControl.inBulkContext()` / `suppressHCFTrigger` early return — bulk paths are covered by the backfill instead. | AC-2, AC-7, AC-12 |
| `PRM_DirectoryIndicatorAccountExecutor` | Modified Apex (data-fix executor) | Add `AND PRM_PNC__c = false` to the default query so PNC practitioners are never restored to `true`; apply the same guard in `buildUpdateList` so a custom `PRM_StartQuery__c` cannot bypass it. | AC-10 |
| `DFX_DirectoryIndicatorAccountExecutor` | Modified Apex (data-fix executor) | Sibling copy of the same fix — review and apply the identical PNC exclusion, or retire it if superseded. | AC-10 |
| `PRM_PNCDirectoryIndicatorExecutor` (new) | New Apex (`PRM_IDataFixExecutor`) | One-time backfill over both objects: Practitioner Accounts and practice locations where `PRM_PNC__c = true AND PRM_IsDirectoryPrint__c = true` → set `false`. Registered as a `PRM_DataFix` custom metadata record and run via `PRM_DataFixScheduler.runNow()`; emits the framework's CSV of old/new values. Honours `PRM_DataFixConfig.isDebug` for a dry run and `recordThreshold`. | AC-11 |
| Field-level security | Permission set | Confirm the PDM/Credentialing profiles' edit access on both `PRM_IsDirectoryPrint__c` fields is unchanged — the rule must fail closed, not silently skip, if the field is not writable. | AC-6, AC-7 |

**Notes for the developer:**

- **Same-record only.** Neither rule queries the other object. R1 reads `Account.PRM_PNC__c` on the Account being saved; R2 reads `HealthcareFacility.PRM_PNC__c` on the location being saved. This is what removes the Rev 1 fan-out batch and the Queueable-from-trigger problem entirely.
- **The rollup already produces the Account DML we need.** `PRM_PractitionerPNCBatch` updates `Account.PRM_PNC__c`, and `PRM_AccountTrigger` has no bulk-context suppression, so R1 fires on rollup-driven PNC changes without any extra wiring (AC-3, AC-12).
- **Distinguish auto-suppression from manual override** by comparing against `Trigger.oldMap`: a `PRM_PNC__c` false→true transition (or an insert) auto-suppresses silently; a `PRM_IsDirectoryPrint__c` false→true change while `PRM_PNC__c` is already true is the case that errors. Without that distinction the error path is unreachable, because the auto-set would always win.
- **`addError` vs. a Validation Rule.** `addError` in the before-context handler is recommended: it inherits the existing `PRM_TriggerBypassPermission` escape hatch and the batch/bulk guards, whereas a declarative Validation Rule would also block integration and data-fix updates that legitimately need to write these fields. Flagged as CQ #2 if the business wants the declarative version.
- Reuse `PRM_ExceptionLogger.logException(...)` for any failure path, consistent with `updateAccountPNC`.
- Record types via `PRM_GlobalConstant.RECTYPEID_PRACTITIONER` (cached describe) — do not query `RecordType`.

---

## Definition of Done

- [ ] Flagging a practitioner PNC turns its Display-in-Directory indicator off in the same save, for manual, rollup, override, and batch paths (AC-1, AC-3).
- [ ] Flagging a practice location PNC turns its own Display-in-Directory indicator off in the same save (AC-2).
- [ ] Non-PNC practitioners and locations are never auto-modified (AC-4).
- [ ] Clearing PNC leaves the indicator off — no automatic restore anywhere in the codebase (AC-5).
- [ ] Attempting to re-enable the indicator on a PNC practitioner or PNC location is rejected with a business-readable message (AC-6, AC-7).
- [ ] No cross-object writes: `HealthcarePractitionerFacility.IsDirectoryPrint` is untouched by this story (AC-8) — verified by grep.
- [ ] Vendor/Group accounts are unaffected (AC-9).
- [ ] `PRM_DirectoryIndicatorAccountExecutor` (and its `DFX_` sibling) no longer restore PNC practitioners, including via a custom `PRM_StartQuery__c` (AC-10).
- [ ] Backfill executor run in debug mode first, CSV reviewed and signed off by PDM, then run for real (AC-11).
- [ ] Bulk run of 200+ records per object flags no failures; before-context logic adds zero SOQL and zero DML (AC-12).
- [ ] Apex ≥ 85% coverage incl. bulk (200), single, insert, update, override-error, non-PNC, and wrong-record-type paths; real assertions on both indicator fields.
- [ ] Field history on both `PRM_IsDirectoryPrint__c` fields shows the automated change (both are already history-tracked).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Does R2 apply to **all** `HealthcareFacility` records, or only those that are practice locations (if a record-type or `PRM_Active__c` filter is expected)? Written today as all `HealthcareFacility` records. | Scope of the location rule + backfill query | BA / Technical |
| 2 | Should the manual-override block be Apex `addError` (recommended — respects the existing trigger-bypass permission and batch guards) or a declarative Validation Rule (blocks everyone, including integrations)? | Whether data fixes and integrations can still write the field | Technical / Ops |
| 3 | Exact customer-facing wording for the two error messages, and should it be a Custom Label for reuse? | Error message content | BA / Product |
| 4 | `PRM_HealthcareFacilityTrigger` exits early in bulk context (`inBulkContext` / `suppressHCFTrigger`). Are there known bulk/integration paths that set location PNC, and should they get an explicit suppression call rather than relying on the backfill? | Whether R2 needs a second enforcement point | Technical |
| 5 | Should the backfill also produce a **report of records it would change** for PDM sign-off before the real run, or is the framework's debug-mode CSV sufficient? | Backfill rollout process | Ops / PDM |
| 6 | Since suppression is one-way, is there a required **notification or audit entry** when the indicator is auto-flipped, beyond field history? | Observability scope | Ops |
| 7 | Does any downstream directory extract or outbound feed cache the indicator, such that a re-publish is needed after the backfill? | Cutover/refresh step | Technical / Integration |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_AccountTriggerHelper` | Apex (helper) | HIGH | New before-context suppression + override-block rule for Practitioner accounts |
| `PRM_HCFacilityTriggerHelper` | Apex (helper) | HIGH | New before-context suppression + override-block rule for practice locations |
| `PRM_AccountTriggerHandler` | Apex (trigger handler) | MEDIUM | Wire the new helper into `beforeInsert` / `beforeUpdate` |
| `PRM_HCFacilityTriggerHandler` | Apex (trigger handler) | MEDIUM | Wire the new helper into `beforeInsert` / `beforeUpdate`, outside the `byPassVal` guard |
| `PRM_DirectoryIndicatorAccountExecutor` | Apex (data fix) | HIGH | **Conflicting behavior** — currently restores the indicator for active participating practitioners; must exclude PNC |
| `DFX_DirectoryIndicatorAccountExecutor` | Apex (data fix) | MEDIUM | Sibling copy of the same conflicting fix |
| `PRM_PNCDirectoryIndicatorExecutor` | Apex (data fix, new) | MEDIUM | One-time backfill across both objects |
| `Account.PRM_IsDirectoryPrint__c` | Field | MEDIUM | Now trigger-maintained and no longer freely editable while PNC |
| `HealthcareFacility.PRM_IsDirectoryPrint__c` | Field | MEDIUM | Now trigger-maintained and no longer freely editable while PNC |
| `PRM_PractitionerPNCBatch` / `PRM_RecalculatePNCFlowAction` / `PRM_PNCPDABatchHelper` | Apex (PNC writers) | LOW | Unchanged, but their Account updates now also trigger suppression |
| `HealthcarePractitionerFacility.IsDirectoryPrint` | Field | NONE | Explicitly out of scope from Rev 2 |
| Directory extract DataRaptors (e.g. `PRMDRExtractAffirmingCareCategoriesForPrac`) | DataRaptor | LOW | Consume the corrected values; no change expected |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_AccountTriggerHelper` + handler wiring | Apex (before-context rule + override block) | M | In-memory only; record-type filter |
| `PRM_HCFacilityTriggerHelper` + handler wiring | Apex (before-context rule + override block) | M | Mirror of the Account rule; mind the trigger guards |
| `PRM_DirectoryIndicatorAccountExecutor` + `DFX_` sibling | Apex (query + guard change) | S | Add PNC exclusion in query and in `buildUpdateList` |
| `PRM_PNCDirectoryIndicatorExecutor` (backfill) | Apex (new data-fix executor) | M | Two objects, debug mode, CSV output |
| Custom metadata record + FLS verification | Config | S | `PRM_DataFix` row, permission-set check |
| Unit tests (bulk 200, insert, update, override-error, non-PNC, vendor RT, backfill) | Apex tests | L | ≥85%, real assertions on both fields |

**Total Estimated Effort:** M–L

> **Down from L–XL in Rev 1.** Making both rules same-record removed the cross-object fan-out, the location-flip `Queueable` → `Batch` chain, and all restore logic. What remains is two before-context field rules plus a one-time backfill.

---

## Related User Stories

- `PRM_PNC_AppReview_Flows_User_Stories.md` — US1 (`HealthcareFacility.PRM_PNC__c`), US4 (rollup), US5/US5B (HealthcareFacility + PPL triggers). **This story depends on US1** for the location flag and on US4 for the practitioner flag, but no longer extends the PPL trigger.
- `PRM_PNCAnyLocation_DataModel_User_Story.md` — `PRM_BypassPNC__c`. When set, PNC is managed manually; this story's rule still applies to the resulting value.
- `PRM_PNC_CredentialingStatus_Blank_User_Story.md` / `PRM_BypassPNC_UpdateFlow_User_Story.md` — other side effects of the PNC flag. **Directory suppression is a sibling side effect** and should be regression-tested with them.
- `PRM_PNC_Logic_Change_Implementation_Plan.md` — parent PNC migration plan.

---

## Post-Generation Offers

- **QTA test bridge:** AC-1…AC-12 convert cleanly to QTA browser-automation prompts (flag practitioner PNC, flag location PNC, attempt manual re-enable, clear PNC, vendor account). Say the word and I'll generate `qta_test_prompts.md`.
- **GUS work item:** I can draft a GUS Story (Description ← Story, Acceptance_Criteria__c ← ACs, Priority P0, persona context).
- **Diagram:** I can produce a before-context decision-flow diagram for the two rules (suppress vs. error vs. no-op).
