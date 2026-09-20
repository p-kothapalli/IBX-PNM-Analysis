# USER STORY 1: Do not round-robin a Case to a different owner when only its status changes

**Persona:** Credentialing Specialist (applies to every Case owner: PDM Specialist, Network Management QC Specialist, Provider Data Admin (PDA) Specialist, Ancillary Cred Specialist)
**Priority:** P0
**OmniScript:** N/A (Apex Case trigger; status changes arrive from Path, record page, guided flows, and NPDB processing)
**Integration Procedures:** N/A (no IP change; IPs that save Case status must keep working without a side-effect reassignment)
**Relevant Requirements:** `Case_Management_Enhancement_User_Stories.md` (US1 — restore previous owner on a *new* Case at a returned stage — complementary, not this defect); `NPDB_T180/US_NPDB01_T180_BatchValidation_Routing.md` (round-robin still applies when a *new* NPDB Case is created); `Duplicate_QC_Cases_RootCause_Analysis.md` (related round-robin defects)

---

## Story

**As a** Credentialing Specialist,
**I want** the Case I already own to stay assigned to me when I (or the system) only change that Case’s status — New to In Progress, On Hold, Pending NPDB, NPDB Action Required, or any other status on the same Case,
**So that** work is not silently handed to a different specialist in the round-robin pool while I am still working the same Case.

**Why it matters:** Specialists lose Cases they just opened. A status click (or an NPDB data-quality flag) currently re-runs round-robin on that same Case and can assign it to someone else. The Case Manager (the parent application) already keeps its owner; only the child Case is stolen. This is a production continuity defect across every Case type.

---

## Scope

| Flow / Case type | What changes | Round-robin after this story |
|------------------|--------------|------------------------------|
| Application Review | Status on the **existing** Case | **Must not** reassign |
| PSV | Status on the **existing** Case | **Must not** reassign |
| QC Review | Status on the **existing** Case (including Returned) | **Must not** reassign |
| PDA Review and Update / PDA Update / PDA Termination | Status on the **existing** Case | **Must not** reassign |
| Network Management QC / Network Management QC Review | Status on the **existing** Case | **Must not** reassign |
| Recred Updates / QM Review / Non-Par QC Review / Prof Staff Verification | Status on the **existing** Case | **Must not** reassign |
| Ancillary, Off-Cycle, PNC, PDM Manual, CMS Preclusion, Provider Change, Non-Par | Status on the **existing** Case | **Must not** reassign |
| **Any** Case type | **New Case created** (intake, stage hop, return-to-stage that inserts a new Case) | **Still round-robins** (or restores previous stage owner per the existing enhancement story) |
| Case Manager (parent application) | Status / stage on the Case Manager | **Out of scope** — owner already stays put (verified) |

**In scope:** same Case record, any status change, all Case types, honor a manual owner change on the same save.

**Out of scope:** Case Manager owner logic; out-of-office redistribution; creating a *new* Case for a new stage; skill/workload assignment engine (2027 ROM Feature 3).

---

## Current State (from codebase)

Verified after the code-review graph returned empty (2 files, 0 edges). Findings below are from `PRM_CaseTriggerHandler.cls`, `PRM_CaseTrigger.trigger`, `PRM_IATriggerHandler.cls`, `PRM_NPDBErrorMessageTriggerHelper.cls`, `PRM_OutOfOfficeLogTriggerHandler.cls`, `PRM_RoundRobinCaseAssignment__mdt`, and `PRM_CaseTriggerHandlerTest.cls`.

### Case Manager (parent) — already correct

- **Location:** `force-app/main/default/classes/PRM_IATriggerHandler.cls`
- The Case Manager trigger only stamps age dates and kicks BCBSA sync. It **never** assigns owner. A Case Manager status change does **not** round-robin. This story does not change Case Manager.

### Case (child work item) — defect

- **Trigger:** `force-app/main/default/triggers/PRM_CaseTrigger.trigger` (before insert + before update; bypass unless the specialist has the round-robin run permission used by the integration user).
- **Handler:** `force-app/main/default/classes/PRM_CaseTriggerHandler.cls`

**`beforeInsert`** always calls round-robin. That is the intended “new Case” path. **Keep it.**

**`beforeUpdate` (the defect — lines 42–52)** re-enters round-robin whenever **Status** or the Case-to-Case-Manager lookup changes:

- Changing New → In Progress, On Hold, Pending NPDB, NPDB Action Required, Returned, Closed, etc. all qualify as a Status change.
- The handler then filters by Case type + status (lines 101–117). The filter is **not** “new Cases only”:

| Case type | Status gate today | Same-Case status change leaks into round-robin? |
|-----------|-------------------|------------------------------------------------|
| Application Review | Status is **not** On Hold | **Yes** — New → In Progress, Pending NPDB, NPDB Action Required, Returned all re-enter. On Hold is accidentally excluded. |
| PSV | **None** (every status) | **Yes** — any PSV status change re-enters. |
| QC Review | New **or** Returned | **Yes** for those two statuses. Compound condition is also mis-parenthesized: **Returned on any Case type** can be treated as QC Review. |
| PDA Update, QM Review, Network Management QC Review, PDA Termination, Prof Staff Verification | Status = New | Only while Status remains (or is set back to) New. |
| Network Management QC, PDA Review and Update, Recred Updates, Non-Par QC Review | Status = New **and** round-robin flag is checked | Same as above, plus the flag must be true. |

**Partial keep-owner attempt (lines 185–193)** already tries to keep the current owner on update if they are active, not out of office, **and** a member of the public group configured for that Case type. That is **not enough**:

1. A Queue owner, a supervisor, or anyone outside that public group falls through to previous-owner lookup, then round-robin.
2. An out-of-office owner on a status-only save is stolen even though out-of-office redistribution has its own handler.
3. A **manual** owner change on the same save can be overwritten if the new owner is not in the group.
4. **No test** asserts that Owner stays the same after New → In Progress (or any other same-Case status change). Existing tests only insert Cases or update Status without checking Owner.

### Smoking-gun callers (same Case, Status-only update)

| Caller | What it writes on the existing Case | Side effect today |
|--------|-------------------------------------|-------------------|
| Specialist Path / record page | Status only | Round-robin may assign a different person |
| NPDB error processing (`PRM_NPDBErrorMessageTriggerHelper`) | Status = NPDB Action Required, Pending NPDB, or In Progress — **Owner is not in the write** | Round-robin may steal the Case from the specialist who was gathering NPDB data |
| NPDB clear / retry | Status = In Progress | Same |

### What must still round-robin after the fix

- **Insert** of a new Case (intake, stage hop that creates a new Case, return-to-stage that inserts a new Case). Previous-stage owner restore (`Case_Management_Enhancement_User_Stories.md` US1) stays on that insert path.
- **Out of office** (`PRM_OutOfOfficeLogTriggerHandler`) — redistributes that person’s open Cases; it already sets Owner (or calls assignment) **before** the update, and does not rely on a Status change.

### Round-robin configuration (unchanged)

Twenty-three `PRM_RoundRobinCaseAssignment` custom metadata rows map Case Manager record type + Case type → public group or queue (PAR App Review, PAR PSV, PAR QC, Recred PSV/QC/Updates/NMQC, Ancillary PSV/PDA/NMQC, Off-Cycle, PNC, PDM Manual, CMS Preclusion, Non-Par, Provider Change, etc.). This story does **not** add or remove rows; it stops using that map on a **status-only update** of an existing Case.

---

## Acceptance Criteria

> Pattern A = business-language Given / When / Then. Pattern E = exact record recipe after the save. No Apex class names, IP steps, or API field names in Pattern A.

**AC-1 — New → In Progress on the same Case keeps the owner**

**Given** a Credentialing Specialist owns an open Case whose status is New (any Case type that uses round-robin on create),
**When** they change that Case’s status to In Progress and save,
**Then** the Case remains assigned to the same Credentialing Specialist,
**And** no other specialist in the round-robin pool receives that Case,
**And** the parent Case Manager’s owner is unchanged.

**AC-2 — On Hold on the same Case keeps the owner**

**Given** a Credentialing Specialist owns an open Case (including Application Review and PSV),
**When** they change that Case’s status to On Hold and save,
**Then** the Case remains assigned to the same Credentialing Specialist,
**And** putting the Case on hold does not start a new round-robin.

**AC-3 — Pending NPDB / NPDB Action Required on the same Case keeps the owner**

**Given** a Credentialing Specialist owns an open Case (Application Review, PSV, or QC Review),
**When** they or the NPDB process change that Case’s status to Pending NPDB or NPDB Action Required,
**Then** the Case remains assigned to the same Credentialing Specialist,
**And** the parent Case Manager may also move to the matching NPDB status but its owner does not change,
**And** fixing NPDB data and moving the Case back to In Progress also keeps the same Case owner.

**AC-4 — Any other status change on the same Case keeps the owner**

**Given** a Credentialing Specialist (or PDM Specialist, Network Management QC Specialist, PDA Specialist, or Ancillary Cred Specialist) owns an open Case of any type,
**When** they change only that Case’s status to any other value (Returned, Pending Application, Closed, or any status offered on the Case),
**Then** the Case remains assigned to the person who already owned it,
**And** round-robin does not run for that save.

**AC-5 — A newly created Case still round-robins**

**Given** a new Case is being created for a Case Manager (intake, first visit to a stage, or a stage hop that inserts a new Case),
**When** the Case is saved for the first time with status New,
**Then** the Case is assigned through the existing round-robin (or previous-stage owner restore when that enhancement applies),
**And** this story does not change first-time assignment of a brand-new Case.

**AC-6 — A manual owner change on the same save is honored**

**Given** a Credentialing Specialist (or a supervisor) is saving a Case and they also pick a different owner,
**When** they save Status and Owner together,
**Then** the Case is owned by the person they picked,
**And** round-robin does not overwrite that choice.

**AC-7 — Case Manager owner is not touched (regression)**

**Given** a Case Manager has an owner,
**When** a related Case’s status changes,
**Then** the Case Manager remains assigned to the same owner,
**And** no round-robin runs against the Case Manager.

**AC-8 — Out-of-office redistribution still runs**

**Given** a Credentialing Specialist is marked out of office,
**When** the out-of-office process redistributes that person’s open Cases,
**Then** those Cases are still reassigned per today’s out-of-office rules,
**And** a later status-only save on a redistributed Case does not round-robin it away from the new owner.

**AC-9 — Records after a same-Case status save (Pattern E)**

**Given** a Credentialing Specialist owns Case C linked to Case Manager M, and they are only changing Case status,
**When** they save the new status,
**Then** the following records are updated exactly as specified:

**Case — Update**

| Field | Value | Notes |
|-------|-------|-------|
| Status | {the status the specialist or NPDB process saved} | the only field this save is meant to change |
| Owner | {the owner who already owned this Case} | must not be rewritten by round-robin |
| Type | {unchanged} | still the same Case type / stage |
| Case Manager | {Case Manager M} | lookup unchanged |
| Record Type | {unchanged} | PRM Case |

**Case Manager — no owner write**

| Field | Value | Notes |
|-------|-------|-------|
| Owner | {existing Case Manager owner} | not rewritten |
| Status | {unchanged, unless NPDB processing also updates the Case Manager} | NPDB may set NPDB Action Required / Pending NPDB / In Progress on the Case Manager; owner still stays |

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|-----------|------|--------|-------|
| `PRM_CaseTriggerHandler.cls` `beforeUpdate` | Modify Apex | Stop calling `handleRoundRobinAssignment` when the only relevant change is `Status`. Keep calling it on **insert**. Do not overwrite `OwnerId` when the incoming save already changed Owner. | Drives AC-1–AC-6, AC-9 |
| `PRM_CaseTriggerHandler.cls` type/status filter (lines 101–117) | Modify Apex (defensive) | After the gate change, status-only updates should never reach this filter. Optionally tighten the QC Review `Returned` compound condition so Returned on a non-QC Case cannot enter the QC bucket (see Clarification #3). | Hardening; AC-4 |
| `PRM_CaseTriggerHandler.cls` `caseOwnerAssignment` keep-owner block (lines 185–193) | Modify or simplify Apex | Once status-only updates never enter assignment, this block is no longer the primary control. Keep it as a safety net for any remaining update path (Case Manager lookup change) so an already-owned Case is not stolen. | Defense in depth |
| `PRM_CaseTriggerHandlerTest.cls` | Modify Apex tests | Add tests that assert **Owner is unchanged** after New → In Progress, On Hold, Pending NPDB, NPDB Action Required, Returned; insert still assigns; manual Owner + Status save keeps the chosen Owner; bulk 200 status updates; Case Manager Owner unchanged. | DoD / ≥85% |
| `PRM_NPDBErrorMessageTriggerHelper.cls` | No functional change | Status-only Case updates (NPDB Action Required / Pending NPDB / In Progress) must stop being reassigned as a side effect of the Case trigger. Add a regression assertion in the NPDB tests if those tests already create a Case with a known Owner. | Drives AC-3 |
| `PRM_OutOfOfficeLogTriggerHandler.cls` | No change | Continues to set Owner or call `caseOwnerAssignment` then update. Confirm a status-only gate does not block this path (Owner changes without a Status change; today’s `beforeUpdate` already ignores Owner-only saves). | Drives AC-8 |
| `PRM_IATriggerHandler.cls` | No change | Confirmed: Case Manager has no round-robin. | Drives AC-7 |
| `PRM_RoundRobinCaseAssignment__mdt` | No change | Leave the 23 routing rows as-is. | AC-5 |

**Recommended gate (developer contract):** in `beforeUpdate`, compare old vs new Case. Enqueue round-robin only when this is **not** a status-only (or status + unrelated field) update of an already-owned Case. Never replace `OwnerId` when old Owner ≠ new Owner on the incoming save (honor manual / out-of-office / integration writes). `beforeInsert` remains the sole first-assignment path.

---

## Definition of done

- [ ] New → In Progress on an existing Case of each major type (Application Review, PSV, QC Review, PDA, Network Management QC, Recred Updates) keeps the same Case owner in the target org.
- [ ] On Hold, Pending NPDB, NPDB Action Required, and Returned on the same Case keep the same owner (PSV included — today PSV re-enters on every status).
- [ ] NPDB processing that sets Case status to NPDB Action Required / Pending NPDB / In Progress does not change Case owner.
- [ ] A brand-new Case still receives round-robin (or previous-stage owner) on insert.
- [ ] Manual owner change on the same save is kept.
- [ ] Case Manager owner is unchanged after a related Case status save.
- [ ] Out-of-office redistribution still reassigns that person’s open Cases.
- [ ] Apex tests cover bulk (200) same-Case status updates, insert assignment, manual owner, and NPDB status-only update; handler coverage ≥ 85% including the new update path.
- [ ] No regression to stage-hop inserts that create a **new** Case.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Business said “Pending NPDB Action Needed.” Org values on Case/Case Manager are **Pending NPDB** and **NPDB Action Required**. Confirm both (and every other Case status) are in the “do not reassign” set. | AC-3 wording and QA scripts | Product / Ops |
| 2 | If a save changes **Case type** (stage conversion on the *same* Case, no new Case insert) *and* status, should that still keep the owner, or is that treated as a new stage that should round-robin? Default in this story: **keep owner** — only **insert** round-robins. | Whether `beforeUpdate` must also ignore Type changes | Product |
| 3 | Today `Returned` is OR’d without parentheses, so Returned on a **non-QC** Case can enter the QC Review assignment bucket. Fix that operator-precedence leak in this P0, or a follow-up? Default: **fix here** — it is the same class and the same symptom (unexpected reassignment). | Extra test + one-line boolean grouping | Technical |
| 4 | If the Case is owned by a **Queue** (not a person) and someone only changes status, keep the Queue (this story’s default) or assign to the person who saved? | Queue-owned Path updates | Ops |
| 5 | Should populating the Case Manager lookup on an **already inserted** Case (today’s second `beforeUpdate` trigger) still round-robin? This story leaves that path as-is unless Ops wants it stopped too. | Rare “insert Case then stamp Case Manager” integrations | Technical |
| 6 | US-NPDB-01 still wants **new** NPDB Cases to round-robin. Confirm no conflict: this story only stops reassignment on **update** of an existing Case. | Cross-story QA | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CaseTriggerHandler` | Apex | HIGH | Primary fix — stop round-robin on same-Case status update |
| `PRM_CaseTrigger` | Trigger | LOW | No signature change; still before insert/update |
| `PRM_CaseTriggerHandlerTest` | Apex test | HIGH | Missing owner-unchanged assertions must be added |
| `PRM_NPDBErrorMessageTriggerHelper` | Apex | MEDIUM | Status-only Case DML must no longer steal owner; regression test |
| `PRM_OutOfOfficeLogTriggerHandler` | Apex | LOW | Must keep working; Owner-only updates already skip the status gate |
| `PRM_IATriggerHandler` | Apex | NONE | Case Manager owner already stable |
| `PRM_RoundRobinCaseAssignment__mdt` | Custom Metadata | NONE | Routing rows unchanged |
| Review / NPDB / Path UI | OmniScript / standard UI | LOW | Specialists keep seeing their Case after a status click |
| `Case_Management_Enhancement` US1 | Requirement | LOW | Complementary: that story is **new Case** at a returned stage; this one is **same Case** status |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `beforeUpdate` gate + do-not-overwrite Owner | Apex | M | Small code change; high regression risk if gated wrong |
| Type/status filter + Returned parentheses (if included) | Apex | S | Defensive |
| Handler + NPDB + OOO tests (single, bulk 200, negative, all major types) | Apex test | L | This is the bulk of the work |
| QA / UAT across Case types + NPDB path | Test | M | Path + NPDB flag + stage-hop insert regression |

**Total Estimated Effort:** L–XL (about 1–2 days engineering + UAT) — AI-estimated, validate with the team.

**Story points (optional):** 5
