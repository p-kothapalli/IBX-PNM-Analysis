# USER STORY: PNC Practitioners Carry No Credentialing Status and No Recred Due Date (Override Blanks Both; 30-Day Restore on Revert)

**Persona:** PDM Specialist (data steward); the PNC PDA flow is operated by the Provider Data Admin (PDA) Specialist
**Priority:** P0 (data-integrity rule tied to the PNC field migration + Override/Bypass flag)
**OmniScript:** `PRM_PNCPDA_English` (PNC PDA guided flow) — no OmniScript field change; the write is in the PDA batch
**Apex:** `PRM_PNCPDABatchHelper`
**DataRaptor:** `PRMDRCreateCaseCaseManagerAndAccount` (creation-time status)
**Relevant Requirements:** `PRM_PNCAnyLocation_DataModel_User_Story.md` (`PRM_BypassPNC__c`), `PRM_BypassPNC_UpdateFlow_User_Story.md` (Override flow that performs the blank/restore), `PRM_PNC_Logic_Change_Implementation_Plan.md`, `PRM_PNC_AppReview_Flows_User_Stories.md` (US-AR3 PDA)

> **Vertical:** Provider Network Management (PNM) — Health Cloud + PNM managed package.
> **Business rule (confirmed with business, Jul 2026):** A **PNC (Par Non Cred)** practitioner is *participating but not credentialed*, so their **Credentialing Status must be blank AND their Recred Due Date must be blank**. Turning the **Override / Bypass PNC** flag **ON** forces a practitioner into PNC and therefore **blanks both** the Credentialing Status and the Recred Due Date. If the Override is later **turned OFF (unchecked)** and the practitioner **was Credentialed before** and the change is **within 30 days**, the system **restores** Credentialing Status = "Credentialed" and the **old Recred Due Date**.
> **Revision note:** This supersedes the earlier "bypass keeps Credentialed" model. Override/Bypass = force **into** PNC (blank), not "keep credentialed."
> **Depends on:** `Account.PRM_BypassPNC__c` (bypass data-model story) and field-history tracking on Credentialing Status, Recred Due Date, and the Bypass flag (for the 30-day restore).

---

## Story

**As a** PDM Specialist (acting as data steward),
**I want** a PNC practitioner to carry no Credentialing Status and no Recred Due Date — and turning the Override/Bypass PNC flag on to blank both, while unchecking it within 30 days restores the prior "Credentialed" status and old Recred Due Date,
**So that** PNC (non-credentialed) practitioners are never mislabeled as "Credentialed" or left with a stale recred due date, and an accidental or short-lived override can be cleanly reversed without losing the practitioner's real credentialing state.

**Why it matters:** Credentialing Status = "Credentialed" and a populated Recred Due Date drive real downstream logic — the recred-due report and recred case-manager creation key off `PRM_ReCredDueDate__c` and `PRM_CredentialingStatus__c`. Today the PNC PDA flow stamps every PNC practitioner as "Credentialed" and leaves the recred due date in place, which wrongly pulls non-credentialed PNC providers into credentialed-only and recred processes. Blanking both fixes that automatically; the 30-day restore protects against a mistaken override.

---

## Scope

| Object | Field | Applies To | Trigger point |
|--------|-------|-----------|---------------|
| Account (Practitioner RT) | `PRM_CredentialingStatus__c` | PNC practitioners (`PRM_PNC__c = true`) | PNC PDA processing; practitioner creation; Override on/off |
| Account (Practitioner RT) | `PRM_ReCredDueDate__c` | PNC practitioners (`PRM_PNC__c = true`) | PNC PDA processing; practitioner creation; Override on/off |

---

## Current State (from codebase) — audit of Credentialing Status / Recred Due Date writes

**Field:** `Account.PRM_CredentialingStatus__c` — restricted picklist: `Credentialing In Progress`, `Credentialed`, `Denied`, `Terminated`, and blank. History tracking is on.
**Field:** `Account.PRM_ReCredDueDate__c` — date; drives recred-due reporting and recred case-manager creation. History tracking is **on** (`trackHistory=true`, verified in metadata) — required for the 30-day restore.

### PNC-relevant writes (in scope)

| Where | File : line | Current behavior | Verdict |
|---|---|---|---|
| **PNC PDA flow** (batch) | `PRM_PNCPDABatchHelper.cls:229,233` | Sets `PRM_PNC__c = true` **and** `PRM_CredentialingStatus__c = 'Credentialed'` together; leaves `PRM_ReCredDueDate__c` in place | **Primary fix** — for a PNC practitioner, **blank** both status and recred due date |
| **Practitioner creation** | `PRMDRCreateCaseCaseManagerAndAccount_Items.json` (formula → `CredentialingStatusVal`, output `PRM_CredentialingStatus__c`) | Status derived from `PractitionerCreationType` (IBC Professional Staff → `Credentialed`; Delegated Credentialing → `null`; else → `Credentialing In Progress`); `PRM_PNC__c` set separately from `PNCFlag` | **Secondary** — make PNC-aware so a PNC practitioner is created with blank status **and** no recred due date |
| **Override / Bypass flow** | `PRM_BypassPNC_UpdateFlow_User_Story.md` (`PRM_UpdateBypassPNC`) | Flow toggles `PRM_BypassPNC__c`; today it does not touch status/recred due date | **New** — Override ON → blank both; Override OFF → 30-day restore (that logic is specified in the flow story; this story defines the rule) |

### Standard lifecycle writes (NOT PNC — leave unchanged unless the practitioner is PNC)

| Where | File : line | Value | Note |
|---|---|---|---|
| Standard PDA / initial-cred list assignment | `PRMUpdateCMandAccountPDATrue` DR (DefaultValue "Credentialed") → used by `PRM_ReviewInitialCredAppListAssignment` | `Credentialed` | Credentialed path — not PNC |
| Recred committee approve | `PRM_PARReCredCommitteeReviewBatch.cls:126` | `Credentialed` | Credentialed path |
| Denials | `PRM_PARRequestDenialHelper.cls:164`, `PRM_CaseManagerDenialUtility.cls:211`, `PRM_PARReCredCommitteeReviewDenialBatch.cls:87` | `Denied` | Unaffected |
| Terminations | `PRM_PractitionerTerminationBatchHelper.cls:564/583`, `PRM_RCATTerminationEffectivityHelper.cls:76/90`, `PRM_FullPracTermRecredBatchService.cls:72`, `PRM_FullPractitionerTerminationBatch.cls:117`, `PRM_RCATTerminationBatchHelper.cls:836/850` | `Terminated` / `''` | Unaffected |
| Activation / reinstatement | `PRM_PractitionerActivationBatchHelper.cls:33` (null), `PRM_FutureDatedProcessingBatchHandler.cls:934/974` (`''`) | null/blank | Unaffected |

> **Off Cycle PDA:** `PRM_OffCycleRecordUpdatesPDAReview` only references Credentialing Status in a saved preview blob — no live write step found; it inherits the practitioner's existing status. Confirm during build.

---

## Acceptance Criteria

**AC-1 — PNC practitioner leaves PDA with blank Credentialing Status and blank Recred Due Date**

**Given** a practitioner who is PNC,
**When** the PNC PDA processing completes for that practitioner,
**Then** their Credentialing Status is blank **and** their Recred Due Date is blank,
**And** their participation status and PNC flag are set as they are today (participating, PNC = yes).

**AC-2 — Turning Override/Bypass PNC ON blanks both**

**Given** a practitioner who is not currently PNC,
**When** a specialist turns the "Override/Bypass PNC" flag ON (forcing the practitioner into PNC),
**Then** their Credentialing Status is blanked **and** their Recred Due Date is blanked,
**And** the prior values are recoverable for 30 days (see AC-3).

**AC-3 — Turning Override/Bypass PNC OFF within 30 days restores the prior Credentialed state**

**Given** a practitioner whose Override was turned ON (status + recred due date blanked) and who **was "Credentialed" immediately before** the override,
**When** the specialist turns the Override OFF **within 30 days of the Override-ON date**,
**Then** the system restores Credentialing Status = "Credentialed" **and** the **previous** Recred Due Date,
**And** the 30-day window is measured from the **Override-ON date** (the moment the status was blanked, per field history — *not* the practitioner's last-Credentialed date),
**And** if the Override is turned off **after 30 days**, no automatic restore occurs and the status/recred due date follow the normal (non-PNC) lifecycle / rollup instead.

**AC-3a — Restore applies only to the manual Override, not to rollup-driven PNC exits**

**Given** a practitioner who leaves PNC because the automatic location rollup recomputed them to non-PNC (no manual Override involved),
**When** that rollup change occurs,
**Then** the 30-day "Credentialed" restore does **not** run automatically,
**And** the practitioner's status/recred due date follow the normal lifecycle (the restore is reserved for undoing a manual Override).

**AC-4 — Non-PNC practitioners are unaffected**

**Given** a practitioner who is not PNC,
**When** any credentialing lifecycle step runs (PDA, committee, denial, termination, activation),
**Then** their Credentialing Status and Recred Due Date behave exactly as they do today,
**And** none of this story's changes alter that path.

**AC-5 — PNC practitioners are created without a Credentialing Status or Recred Due Date**

**Given** a new PNC practitioner is created,
**When** the record is created,
**Then** their Credentialing Status is blank (not "Credentialed" or "Credentialing In Progress") **and** their Recred Due Date is blank.

**AC-6 — Credentialing-Status / Recred-Due-Date computation rules** *(Pattern D — rules block)*

**Given** a practitioner record is being written by the PNC PDA flow, the creation flow, or the Override flow,
**When** the Credentialing Status and Recred Due Date are set,
**Then** they are set per the rules below:

- **When `PRM_PNC__c = true` (regular PNC or Override ON):** Credentialing Status → **blank**; Recred Due Date → **blank**.
- **When the manual Override/Bypass flips true → false within 30 days of the Override-ON date AND the practitioner was "Credentialed" immediately before:** Credentialing Status → **"Credentialed"** (restored); Recred Due Date → **previous value** (restored from field history). The 30-day clock starts at the **Override-ON date** (the `AccountHistory.CreatedDate` of the "Credentialed→blank" status change), *not* the last-Credentialed date.
- **When the manual Override/Bypass flips true → false after 30 days, or the practitioner was not previously Credentialed:** no restore — Credentialing Status / Recred Due Date follow the normal non-PNC lifecycle (rollup recompute).
- **When a practitioner exits PNC via the automatic rollup (no manual Override):** no automatic restore — normal non-PNC lifecycle applies (restore is manual-Override-only).
- **When `PRM_PNC__c = false` (non-PNC, no override involved):** **existing lifecycle values** (Credentialed / Credentialing In Progress / Denied / Terminated — unchanged).

**AC-7 — Downstream credentialed-only and recred processes exclude PNC practitioners automatically**

**Given** a PNC practitioner whose status and recred due date are now blank,
**When** credentialed-only or recred processes run (recred-due reporting, recred case-manager creation, practitioner-activation selection),
**Then** that PNC practitioner is not picked up (no "Credentialed" status, no recred due date),
**And** a practitioner whose Credentialed state was restored on revert (AC-3) is included again where appropriate.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PNCPDABatchHelper` | Modified Apex | At the PNC update (~L229/233): for a PNC practitioner set `PRM_CredentialingStatus__c = null` **and** `PRM_ReCredDueDate__c = null` (instead of `'Credentialed'`). Add both fields to the SOQL (~L207/247). | Drives AC-1, AC-6 |
| `PRMDRCreateCaseCaseManagerAndAccount` | Modified DataRaptor | Make the `CredentialingStatusVal` formula PNC-aware: when `PNCFlag = true` → blank status and do not populate recred due date; else keep current `PractitionerCreationType` logic | Drives AC-5, AC-6 |
| Override/Bypass flow (`PRM_UpdateBypassPNC`) | New/Modified Flow (spec'd in the flow story) | On Override **ON** → blank status + recred due date; on Override **OFF** → read field history and, if previously "Credentialed" and within 30 days, restore status + old recred due date | Drives AC-2, AC-3; detailed in `PRM_BypassPNC_UpdateFlow_User_Story.md` |
| 30-day restore source | Field history (no new fields — per decision) | Read `AccountHistory` for the **"Credentialed→blank" `PRM_CredentialingStatus__c` row**: its `CreatedDate` = the Override-ON date (the 30-day basis) and its `OldValue` = the status to restore; read the paired `PRM_ReCredDueDate__c` row's `OldValue` for the old due date. Restore only if `OldValue = 'Credentialed'` and `CreatedDate` within 30 days | History confirmed on status + recred due date; enable on `PRM_BypassPNC__c`; note AccountHistory queryability/row limits (see Risks) |
| Downstream credentialed-only / recred selectors | No change | `PRM_RecredDuePractitionersReportBatch`, `PRM_CheckCAQHAccessOnDueAccountsBatch`, `DFX/PRM_PractitionerActivationExecutor` already filter on `= 'Credentialed'` and/or `PRM_ReCredDueDate__c`; blanking both naturally excludes PNC practitioners | Validates AC-7 |
| Off Cycle PDA (`PRM_OffCycleRecordUpdatesPDAReview`) | Verify | Confirm it has no live Credentialing-Status/recred-due write; if it does, apply the same rule | AC-4 safety |

> **Risk (field-history restore):** the 30-day restore relies on Salesforce field history (`AccountHistory`). History rows are queryable but capped and retained per org policy; a restore beyond the retention window (or before history tracking was enabled) will silently find nothing. History tracking is confirmed on `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c`; enable it on the new `PRM_BypassPNC__c`, confirm retention covers 30+ days, and handle the "no history found" path gracefully (fall back to rollup recompute).

---

## Definition of Done

- [ ] `PRM_PNCPDABatchHelper` blanks **both** Credentialing Status and Recred Due Date for PNC practitioners; SOQL includes both fields.
- [ ] `PRMDRCreateCaseCaseManagerAndAccount` creates PNC practitioners with blank status **and** no recred due date.
- [ ] Override ON blanks both; Override OFF restores "Credentialed" + old recred due date only when previously Credentialed and within 30 days (validated with the flow story).
- [ ] Non-PNC lifecycle paths verified unchanged (committee/denial/termination/activation).
- [ ] Recred-due, recred CM creation, and activation selection verified to exclude PNC practitioners and re-include restored ones.
- [ ] Field-history tracking confirmed on Credentialing Status, Recred Due Date, and Bypass flag; "no history" path handled.
- [ ] Apex ≥85% incl. PNC blank, override-on blank, revert-within-30-days restore, revert-after-30-days no-restore, and non-PNC paths; bulk (200).
- [ ] Off Cycle PDA confirmed to have no conflicting write (or fixed).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | *(Resolved Jul 2026)* Override/Bypass = **force into PNC → blank** status + recred due date (not "keep Credentialed"). Confirmed by business. | Core rule (AC-1/AC-2/AC-6) | ✅ Business |
| 2 | *(Resolved Jul 2026)* The **30-day window is measured from the Override-ON date** (the moment the status was blanked) — read as the `AccountHistory.CreatedDate` of the "Credentialed→blank" `PRM_CredentialingStatus__c` change, *not* the last-Credentialed date. That same history row supplies the prior value to restore. | Restore window definition (AC-3) | ✅ Business |
| 3 | *(Resolved Jul 2026)* The restore applies **only to the manual Override** toggle. A practitioner exiting PNC via the automatic rollup does **not** get an automatic 30-day restore (AC-3a). | Restore scope | ✅ Business |
| 4 | Should existing PNC practitioners already stamped "Credentialed" (and/or carrying a recred due date) be **back-corrected** at go-live, or only corrected going forward? | Data remediation scope | Product / Ops |
| 5 | *(Resolved Jul 2026 — verified in metadata)* History tracking is **already ON** for `PRM_CredentialingStatus__c` and `PRM_ReCredDueDate__c` (`trackHistory=true`). Remaining prerequisite: enable it on the new `PRM_BypassPNC__c` (owned by the data-model story) and confirm org history retention covers 30+ days. | Feasibility of restore | Admin / Technical |
| 6 | Any reports/list views/automation (beyond recred-due, recred CM, activation) that treat blank Credentialing Status **or** blank Recred Due Date as an error for participating practitioners? | Hidden downstream impact | BA / Ops |
| 7 | Does the Off Cycle PDA path ever set Credentialing Status / Recred Due Date for a PNC practitioner? (verify no live write) | Adds Off Cycle to scope | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PNCPDABatchHelper` | Apex | HIGH | Primary write that mislabels PNC practitioners today; now blanks status **and** recred due date |
| Override/Bypass flow (`PRM_UpdateBypassPNC`) | Flow | HIGH | New blank-on-enable + 30-day restore-on-revert behavior |
| `PRMDRCreateCaseCaseManagerAndAccount` | DataRaptor | MEDIUM | Creation-time status/recred due date; make PNC-aware |
| Recred-due / recred CM / activation selection | Apex | MEDIUM | Behavior corrects automatically once both fields are blank; restored practitioners re-enter |
| Field history (`AccountHistory`) | Platform | MEDIUM | Restore source; retention/queryability caveats |
| Off Cycle PDA | IP | LOW | Verify only |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_PNCPDABatchHelper` | Apex (blank both + SOQL fields) | M | Blank status + recred due date |
| `PRMDRCreateCaseCaseManagerAndAccount` | DataRaptor formula | M | PNC-aware status + recred due date; field-map sign-off |
| Override flow blank + 30-day restore | Flow / Apex (field-history read) | L | Restore logic + no-history fallback (detailed in flow story) |
| Off Cycle PDA verification | Analysis | S | Confirm no write |
| Tests | Apex tests | M–L | PNC blank / override-on / revert<30d / revert>30d / non-PNC + bulk |
| Data remediation (if approved) | Data fix | M–L | Optional per clarification #4 |

**Total Estimated Effort:** **L**

---

## Related User Stories

- `PRM_PNCAnyLocation_DataModel_User_Story.md` — defines `Account.PRM_BypassPNC__c` (the Override this rule depends on).
- `PRM_BypassPNC_UpdateFlow_User_Story.md` — the Override flow that performs the blank-on-enable and 30-day restore-on-revert (this story defines the rule; that story implements the toggle behavior).
- `Recred_BypassPNC_CaseManagerCreation_UserStory.md` — **reversed** by this change: bypassed/override practitioners have a blank recred due date and are therefore excluded from recred CM creation (they re-enter only if restored on revert).
- `PRM_PNC_AppReview_Flows_User_Stories.md` — US-AR3 (Sent to PDA): the PDA feed/rollup re-point; this story is the Credentialing-Status / Recred-Due-Date side effect at the same PDA step.
- `PRM_PNC_Logic_Change_Implementation_Plan.md` — US4/US5/US5B rollup + triggers.
