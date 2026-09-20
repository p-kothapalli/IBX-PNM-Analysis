# USER STORY: Record-Page Flow Button — Update the PNC Bypass Flag (and PNC when bypassed) for Practitioners

**Persona:** PDM Specialist (primary) and Credentialing Specialist
**Priority:** P1 (enables manual PNC control introduced by the bypass flag; depends on the data-model story)
**OmniScript:** N/A (Screen Flow + Quick Action)
**Flow:** `PRM_UpdateBypassPNC` (new Screen Flow)
**Quick Action:** `Account.PRM_UpdateBypassPNC` (type = Flow)
**Interactive mockup:** `docs/implementation-plan/prmOverridePNCFlow_Mockup.html` (SLDS-style — the record-page button, the two conditional checkboxes, the top disclaimer, the live On-Save impact preview, the destructive-change acknowledgment, and the three practitioner scenarios this story specifies)
**Relevant Requirements:** `PRM_PNCAnyLocation_DataModel_User_Story.md` (defines `PRM_BypassPNC__c`), `PRM_PNC_Logic_Change_Implementation_Plan.md` (US4/US5/US5B rollup + trigger skip), `PRM_PNC_US5_OmniScript_Impact_Analysis.md`

> **Vertical:** Provider Network Management (PNM) — Health Cloud + PNM managed package.
> **Depends on:** `Account.PRM_BypassPNC__c` (data-model story) and the bypass-aware rollup/trigger changes (US4/US5/US5B). The trigger must already skip PNC recompute for practitioners with `PRM_BypassPNC__c = true` (data-model AC-4) and recompute when it flips back to false (data-model AC-5).
>
> **Business rule (confirmed Jul 2026) — Override blanks credentialing state, revert restores it:** Turning **Override/Bypass PNC ON forces the practitioner into PNC**, so the flow must also **blank `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c`**. Turning it **OFF** must, when the practitioner **was "Credentialed" immediately before** and the change is **within 30 days**, **restore** Credentialing Status = "Credentialed" and the **old Recred Due Date** (read from field history — no new fields). The rule itself lives in `PRM_PNC_CredentialingStatus_Blank_User_Story.md`; this flow implements the on/off behavior.

---

## Story

**As a** PDM Specialist (or Credentialing Specialist),
**I want** a button on the Practitioner record page that lets me turn the PNC bypass on or off, and — only while bypass is on — set the practitioner's PNC value myself,
**So that** I can manually control PNC for exception-case practitioners without editing raw fields, and the automatic location-driven rollup takes back over the moment I turn bypass off.

**Why it matters:** The bypass flag lets a practitioner's PNC be managed by hand instead of by the location rollup. Specialists need a safe, guided, permission-gated way to set both the bypass and the manual PNC value together — free-typing two related fields on the record detail is error-prone (e.g., setting PNC manually while bypass is still off, where the trigger would immediately overwrite it).

---

## Scope

| Object | Trigger point | Who sees it | Action |
|--------|---------------|-------------|--------|
| Account (Practitioner RT) | Record-page button / Quick Action | Credentialing + PDM specialists only | Launch `PRM_UpdateBypassPNC` Screen Flow to set `PRM_BypassPNC__c` and (conditionally) `PRM_PNC__c` |

---

## Current State (from codebase)

- The org already uses the **Quick Action → Screen Flow** pattern on Account, gated by a custom permission via Dynamic Actions:
  - `Account.PRM_UpdateNPI` (`type = Flow`, `flowDefinition = PRM_PractitionerNPIUpdate`), gated by `PRM_UpdateNPIPermission`.
  - `Account.UpdatePrimaryTaxonomy` → `PRM_UpdatePrimaryTaxonomy` flow, gated by `PRM_UpdatePrimaryTaxonomy` custom permission.
  - `PRM_CaseManagerFinalDecisionButton` — precedent for a button-launched decision flow.
- Relevant existing **custom permissions**: `PRM_CredentialingPermission`, `PRM_PDMPermission` (usable for the cred + PDM visibility filter), plus per-button permissions like `PRM_UpdateNPIPermission` (precedent for a dedicated button permission).
- `Account.PRM_BypassPNC__c` and `Account.PRM_PNC__c` FLS for the cred/PDM audience are established in the data-model story (`PRM_DataModifyAll`, `PRM_ProviderDataAdmin`, `PRM_CredentialingUser`, `PRM_NetworkManagementQC`, `PRM_AncillaryCredSpecialist`, `PRM_RebtuttalSpecialist` = edit).

---

## Acceptance Criteria

**AC-1 — Button appears only for cred/PDM specialists on Practitioner records**

**Given** a Credentialing Specialist or PDM Specialist opens a Practitioner Account record,
**When** the record page loads,
**Then** an "Update PNC Bypass" button is available,
**And** a user without the credentialing/PDM permission does not see the button,
**And** the button does not appear on Vendor/Group Account records.

**AC-2 — Flow shows the current bypass and PNC state**

**Given** a specialist clicks "Update PNC Bypass",
**When** the flow opens,
**Then** it displays the practitioner's current "Bypass PNC" state and current PNC value,
**And** it clearly indicates whether PNC is currently system-managed (bypass off) or manually managed (bypass on).

**AC-3 — With bypass ON, the specialist can set PNC manually**

**Given** the specialist sets "Bypass PNC" to on in the flow,
**When** they proceed,
**Then** the PNC field becomes editable within the flow,
**And** they can set PNC to Yes or No and save,
**And** on completion the practitioner shows bypass = on with the PNC value they chose,
**And** that value is not overwritten by the location rollup.

**AC-4 — With bypass OFF, PNC is not manually editable in the flow**

**Given** the specialist leaves or sets "Bypass PNC" to off,
**When** they proceed,
**Then** the PNC field is not editable in the flow (it is shown read-only with a note that it is system-calculated from the practice locations),
**And** the flow does not let them submit a manual PNC value.

**AC-5 — Turning bypass OFF returns PNC to the automatic rollup**

**Given** a practitioner currently bypassed (bypass on) with a manually set PNC,
**When** the specialist turns "Bypass PNC" off in the flow and saves,
**Then** the practitioner's PNC is handed back to the automatic rule (PNC only when all participating locations are PNC),
**And** the recomputed value replaces the prior manual value.

**AC-6 — Save respects field security and is audited**

**Given** a specialist completes the flow,
**When** the record is saved,
**Then** the changes are written only if the running user has edit access to the fields (a read-only user cannot commit changes),
**And** the "Bypass PNC" and PNC changes appear in field history with the user and timestamp.

**AC-7 — Cancel makes no change**

**Given** a specialist opens the flow,
**When** they cancel or close it without finishing,
**Then** no change is made to the bypass flag, PNC, credentialing status, or recred due date.

**AC-8 — Turning Override ON with PNC = Yes blanks credentialing status and recred due date**

**Given** a specialist turns "Bypass PNC" ON and sets PNC = Yes (forcing the practitioner into PNC),
**When** they save,
**Then** the practitioner's Credentialing Status is blanked **and** their Recred Due Date is blanked,
**And** the prior Credentialing Status and Recred Due Date remain recoverable for 30 days (AC-9).

**AC-8a — Override ON with PNC = No keeps the existing credentialing state**

**Given** a specialist turns "Bypass PNC" ON but sets PNC = No,
**When** they save,
**Then** the practitioner is held as non-PNC manually (bypass on, PNC = No),
**And** the existing Credentialing Status and Recred Due Date are **kept, not blanked**,
**And** the blank/restore behavior (AC-8, AC-9) does not apply because the practitioner is not being forced into PNC.

**AC-9 — Turning Override OFF within 30 days restores the prior Credentialed state**

**Given** a practitioner whose Override was turned ON (status + recred due date blanked) and who **was "Credentialed" immediately before**,
**When** the specialist turns "Bypass PNC" OFF **within 30 days of the Override-ON date** and saves,
**Then** the flow restores Credentialing Status = "Credentialed" **and** the **previous** Recred Due Date (from field history),
**And** the 30-day window is measured from the **Override-ON date** — the `AccountHistory.CreatedDate` of the "Credentialed→blank" status change (not the last-Credentialed date),
**And** the restore runs **only** for this manual Override path — a practitioner who exits PNC via the automatic location rollup is not auto-restored,
**And** if the Override is turned off **after 30 days** (or the practitioner was not previously Credentialed, or no history is found), no restore occurs and PNC/status is handed back to the normal rollup instead (AC-5).

**AC-10 — A disclaimer explains the consequences before any change is made**

**Given** a specialist opens the flow,
**When** the screen renders,
**Then** a prominent disclaimer is shown at the top explaining that turning Override ON forces the practitioner into PNC and will blank Credentialing Status and Re-Cred Due Date,
**And** it states that unchecking Override within 30 days restores the prior Credentialed state,
**And** it states that leaving Override off keeps PNC system-calculated from the practice locations.

**AC-11 — PNC is read-only and cannot be edited while Override is off (negative)**

**Given** Override / Bypass PNC is off in the flow,
**When** the specialist attempts to change the PNC value,
**Then** the PNC field remains read-only and labelled as system-calculated,
**And** an inline validation message tells them to turn Override on first,
**And** no manual PNC value can be submitted (reinforces AC-4).

**AC-12 — Destructive blank requires an explicit acknowledgment before finishing**

**Given** the practitioner is currently Credentialed (a populated status that the change will blank) and the specialist has set Override ON with PNC = Yes,
**When** they try to finish the flow,
**Then** they must first confirm an acknowledgment that the Credentialing Status and Re-Cred Due Date will be blanked,
**And** finishing is blocked until the acknowledgment is confirmed,
**And** when the current status is already blank (no destructive change), no acknowledgment is required.

**AC-13 — The flow confirms the resulting record state on completion**

**Given** a specialist finishes the flow,
**When** the completion screen renders,
**Then** it shows the resulting PNC, Override, Credentialing Status, and Re-Cred Due Date values,
**And** the practitioner record reflects the same values after the flow closes.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_UpdateBypassPNC` | New Screen Flow | Input `recordId`; Get Account (`PRM_BypassPNC__c`, `PRM_PNC__c`, RecordType); one screen with a Bypass toggle and a PNC input whose visibility/editability is conditioned on the toggle (`bypass = true`); Update Account. Run in **user context** so FLS applies. | Drives AC-2–AC-6 |
| `Account.PRM_UpdateBypassPNC` | New Quick Action | `type = Flow`, `flowDefinition = PRM_UpdateBypassPNC`, label "Update PNC Bypass" | Drives AC-1 |
| Practitioner Lightning record page | Dynamic Actions | Add the quick action with a visibility filter: (user has `PRM_CredentialingPermission` **OR** `PRM_PDMPermission`) **AND** RecordType = Practitioner | Drives AC-1 (cred/PDM only, Practitioner only) |
| Bypass→PNC coupling | Flow logic | When `bypass = false`, do **not** write a manual `PRM_PNC__c` (only set `PRM_BypassPNC__c = false`); the US5/US5B/Account trigger recompute takes over (data-model AC-5). When `bypass = true`, write both. | Drives AC-3, AC-4, AC-5 |
| Override ON → blank credentialing state | Flow logic (or invoked Apex) | When `bypass` is set **true** **and** PNC = Yes (forced into PNC), also set `PRM_CredentialingStatus__c = null` and `PRM_ReCredDueDate__c = null` in the same save. When PNC = No, keep both (AC-8a). | Drives AC-8/AC-8a; rule owned by `PRM_PNC_CredentialingStatus_Blank_User_Story.md` |
| Override OFF → 30-day restore | Invoked Apex (field-history read) | When `bypass` is set **false**, query `AccountHistory` for the **"Credentialed→blank" `PRM_CredentialingStatus__c` row** — its `CreatedDate` is the Override-ON date (the 30-day basis) and its `OldValue` is the status to restore; read the paired `PRM_ReCredDueDate__c` row's `OldValue` for the old due date. If `OldValue = 'Credentialed'` and `CreatedDate` is within 30 days, restore both; else skip and let the rollup recompute. Restore runs only on this manual-Override path (not rollup-driven exits). Handle "no history found" gracefully. | Drives AC-9; history confirmed on Credentialing Status + Recred Due Date; enable on Bypass flag |
| Disclaimer banner | Flow screen (Display Text) | Static warning at the top of the screen describing the force-into-PNC + blank consequences and the 30-day undo. | Drives AC-10 |
| PNC = No branch | Flow logic | When `bypass = true` **and** PNC set to No, write `PRM_BypassPNC__c = true`, `PRM_PNC__c = false`, and **do not** blank `PRM_CredentialingStatus__c` / `PRM_ReCredDueDate__c`. | Drives AC-8a |
| Read-only PNC lock + inline error | Flow (component visibility / validation) | PNC input is display-only when `bypass = false`; a Validation/error message fires if the user tries to set it. | Drives AC-11 |
| Destructive-change acknowledgment | Flow (conditional required checkbox) | When current `PRM_CredentialingStatus__c` is populated (e.g., Credentialed) and the save will blank it (Override ON + PNC = Yes), show a **required** confirmation checkbox and block Finish until checked. Skip when status is already blank. | Drives AC-12 |
| On-Save impact preview | Flow screen (Display Text, computed) | **UX guidance (not a hard AC):** show a computed before→after summary of PNC / Credentialing Status / Re-Cred Due Date so the specialist sees the effect prior to committing. Values come from the same logic that performs the update. | Supports AC-8/AC-8a/AC-9 (advisory) |
| Completion screen | Flow screen (Display Text) | Confirmation screen echoing the resulting PNC, Override, Credentialing Status, and Re-Cred Due Date. | Drives AC-13 |

> **Gating decision (see clarifications):** reuse existing `PRM_CredentialingPermission` + `PRM_PDMPermission` in the Dynamic Action filter, OR mint a dedicated `PRM_UpdateBypassPNCPermission` (mirrors `PRM_UpdateNPIPermission`) and assign it to `PRM_CredentialingUser` + `PRM_ProviderDataAdmin`.

> **Reference scenarios (from the mockup — use as the test matrix):** (1) **Credentialed practitioner** → Override ON + PNC = Yes triggers the destructive-blank path + acknowledgment (AC-8, AC-12); (2) **Actual PNC practitioner** (rollup-driven, bypass off) → PNC read-only, Override ON needed to change (AC-4, AC-11); (3) **Overridden into PNC** (bypass on, blanked N days ago) → uncheck Override within 30 days restores prior Credentialed state (AC-9).

---

## Definition of Done

- [ ] `PRM_UpdateBypassPNC` Screen Flow created, runs in user context, and enforces the bypass→PNC coupling (PNC editable only when bypass on).
- [ ] `Account.PRM_UpdateBypassPNC` Quick Action created and added to the Practitioner Lightning record page via Dynamic Actions.
- [ ] Visibility filter restricts the button to cred + PDM specialists and to the Practitioner record type (hidden on Vendor/Group).
- [ ] Turning bypass off writes only the flag and lets the rollup recompute PNC (validated against US5/US5B).
- [ ] Turning bypass on with a manual PNC value persists and is not overwritten by the rollup (validated against data-model AC-4).
- [ ] Read-only user cannot commit; field history captures both changes.
- [ ] Override ON with PNC = Yes blanks Credentialing Status + Recred Due Date (AC-8); Override ON with PNC = No keeps them (AC-8a).
- [ ] Override OFF within 30 days (previously Credentialed) restores "Credentialed" + old Recred Due Date from field history; after 30 days / no history → no restore (AC-9).
- [ ] Top-of-screen disclaimer describes the force-into-PNC + blank consequences and the 30-day undo (AC-10).
- [ ] PNC is read-only while Override is off, with an inline error on edit attempts (AC-11).
- [ ] Destructive blank (currently Credentialed) requires a confirmation acknowledgment and blocks Finish until confirmed; skipped when status already blank (AC-12).
- [ ] Completion screen echoes the resulting field values and the record reflects them after close (AC-13).
- [ ] Cancel path makes no change.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Gate the button with the existing `PRM_CredentialingPermission` + `PRM_PDMPermission`, or a new dedicated `PRM_UpdateBypassPNCPermission`? | Metadata + assignment approach | Technical / Ops |
| 2 | When bypass is turned off in the flow, should PNC recompute immediately on save, or on the next location event? (Aligns with data-model AC-5.) | Flow vs Account-trigger responsibility | Technical / BA |
| 3 | Should the flow require a reason/comment when enabling bypass (for audit), or is field history sufficient? | Extra screen field + storage | Ops / Compliance |
| 4 | While bypass is on, should raw inline edit of `Account.PRM_PNC__c` on the record detail be blocked so PNC changes only go through this flow? | FLS / page-layout governance | Ops / Security |
| 5 | Confirm the button label ("Update PNC Bypass") and placement on the Practitioner page. | UX | BA / Product |
| 6 | *(Resolved Jul 2026)* The **30-day** window is measured from the **Override-ON date** — the `AccountHistory.CreatedDate` of the "Credentialed→blank" status change (not the last-Credentialed date). Same row supplies the value to restore. Restore is **manual-Override-only** (not rollup-driven PNC exits). | Restore logic (AC-9) | ✅ Business |
| 7 | *(Resolved Jul 2026 — verified in metadata)* History tracking is **already ON** for `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c` (`trackHistory=true`). Remaining: enable on `PRM_BypassPNC__c` and confirm org retention covers 30+ days. | Feasibility of AC-9 | Admin / Technical |
| 8 | *(Resolved Jul 2026)* Blank Credentialing Status / Recred Due Date **only when PNC = Yes** (forced into PNC). If `bypass = true` **and** PNC = No, the practitioner is held non-PNC by hand and the existing status/recred due date are **kept** (AC-8a). | Blank trigger precision (AC-8/AC-8a) | ✅ Business |
| 9 | *(Resolved Jul 2026)* The destructive-blank **acknowledgment is required only when the practitioner is currently Credentialed** (populated status the save will blank); skipped when status is already blank (AC-12). | Validation gate scope | ✅ Business |
| 10 | The live On-Save impact preview is **UX guidance**, not a hard AC — implement as a computed Display Text if flow effort allows. | Screen scope | BA / Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_UpdateBypassPNC` | Flow | MEDIUM | New guided update path for bypass + manual PNC |
| `Account.PRM_UpdateBypassPNC` | Quick Action | LOW | New record-page button |
| Practitioner Lightning record page | Dynamic Actions | LOW | One visibility-filtered action added |
| Custom permission(s) | Metadata | LOW | Reuse or add one permission for gating |
| Rollup triggers (US5/US5B) | Apex | (Dependency) | Must already honor bypass skip/recompute — not built here |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_UpdateBypassPNC` Screen Flow | Flow (conditional screen + DML, user context) | L | AI-estimated — validate with team |
| `Account.PRM_UpdateBypassPNC` Quick Action | Config | S | Mirrors `PRM_UpdateNPI` |
| Dynamic Action visibility (cred/PDM + Practitioner RT) | Config | S | Reuses existing custom permissions |
| Custom permission (if dedicated) | Config | S | Optional per clarification #1 |
| Override ON blank + OFF 30-day restore | Invoked Apex (field-history read) + tests | L | Restore + no-history fallback; ≥85% coverage |

**Total Estimated Effort:** **L** — AI-estimated, validate with team.

---

## Related User Stories

- `PRM_PNCAnyLocation_DataModel_User_Story.md` — defines `Account.PRM_BypassPNC__c` (this flow's prerequisite; AC-4/AC-5 there define the trigger skip/recompute this flow relies on).
- `PRM_PNC_Logic_Change_Implementation_Plan.md` — US4 (rollup helpers), US5 (HealthcareFacility trigger), US5B (PPL trigger): must skip bypassed practitioners and recompute on un-bypass.
- `PRM_PNC_US5_OmniScript_Impact_Analysis.md` — trigger/flow impact of the bypass model.
- `PRM_PNC_CredentialingStatus_Blank_User_Story.md` — **owns the rule** this flow implements: Override ON → blank Credentialing Status + Recred Due Date; Override OFF within 30 days (if previously Credentialed) → restore both from field history.
