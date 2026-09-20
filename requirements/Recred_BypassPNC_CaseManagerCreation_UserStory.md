# USER STORY: Recred Cycle — Bypass/Override-PNC Practitioners Are Excluded from Recred Case-Manager Creation

> Authored with the **User Story Solution Architect** (v1.10). Vertical: **Provider Network Management (PNM)**.
> Part of the PNC migration set. **Depends on:** the `PRM_BypassPNC__c` field (`PRM_PNCAnyLocation_DataModel_User_Story.md`), US4 (switch-aware practitioner PNC rollup), and `PRM_PNC_CredentialingStatus_Blank_User_Story.md`.

> **⚠️ REVERSED (Jul 2026) by the confirmed business rule.** This story originally proposed *including* bypass-PNC practitioners in the recred cycle (`... OR PRM_BypassPNC__c = true`). Business has since confirmed that **Override/Bypass PNC forces a practitioner INTO PNC and blanks their Credentialing Status AND Recred Due Date** (see `PRM_PNC_CredentialingStatus_Blank_User_Story.md`). Consequently a bypassed/override practitioner has **no recred due date** and is a **PNC** practitioner, so they are **already excluded** by the existing recred filter. **The originally proposed filter change is dropped.** This story is now a **verification/regression** story confirming the correct exclusion — and confirming that a practitioner **restored on revert (within 30 days)** re-enters the recred cycle through their restored Recred Due Date.

**Persona:** Credentialing Specialist
**Priority:** P2 (verification/regression — no functional Apex change expected)
**OmniScript:** N/A
**Integration Procedures:** N/A
**Apex (the change surface):** `PRM_CheckCAQHAccessOnDueAccountsBatch` (recred case-manager creation), `PRM_CheckCAQHExecuteHelper` (record builder), `PRM_UpdateCaseManagerBatch` (sibling — regression only)
**Relevant Requirements:** `PRM_PNC_Logic_Change_Implementation_Plan.md`; `PRM_PNC_CredentialingStatus_Blank_User_Story.md`; `PRM_BypassPNC_UpdateFlow_User_Story.md`

---

## Story

**As a** Credentialing Specialist,
**I want** the monthly recredentialing cycle to **exclude** practitioners who are PNC — including those forced into PNC via the Override/Bypass flag (who have no recred due date) — while a practitioner whose Credentialed state was **restored on revert within 30 days** re-enters the cycle through their restored recred due date,
**So that** non-credentialed PNC practitioners never generate recred case managers, and genuinely credentialed practitioners who briefly (mistakenly) had an override are picked back up on their original schedule.

**Why it matters:** PNC (Par Non Cred) practitioners are intentionally excluded from recredentialing. Under the confirmed rule, Override/Bypass = force into PNC → blank Credentialing Status **and** blank Recred Due Date. Because the recred batch keys off `PRM_PNC__c = false` and a populated `PRM_ReCredDueDate__c`, an override practitioner is excluded automatically — no special inclusion is needed (and adding one would wrongly recredentialize non-credentialed providers). The only thing to guarantee is that a **restored** practitioner (revert within 30 days) has their old recred due date back and therefore returns to the cycle.

---

## Scope

| Flow | Component | Affected Step | Data Source |
|------|-----------|---------------|-------------|
| Recred cycle (scheduled) | `PRM_CheckCAQHAccessOnDueAccountsBatch` | `start()` → `generateQueryString()` due-account filter | `Account` (practitioner) PNC + recred due date |
| Recred cycle (scheduled) | `PRM_CheckCAQHExecuteHelper` | `processAccount` → build/insert recred case manager + case | Batch scope |
| Recred cycle (month-end) | `PRM_UpdateCaseManagerBatch` | Existing-CM update (chained from `finish()`) | Existing recred case managers — **regression only** |

---

## Current State (from codebase)

- **`PRM_CheckCAQHAccessOnDueAccountsBatch.generateQueryString()`** `WHERE` clause today: active + `RecordTypeID = pracRecTypeId` + `PRM_DelegatedOnly__c = false` + **`PRM_PNC__c = false`** + `PRM_ReCredDueDate__c` in the due window.
- Under the confirmed rule, an Override/Bypass practitioner has `PRM_PNC__c = true` **and** a blank `PRM_ReCredDueDate__c` → **excluded twice over** by the existing filter. **No filter change is required.**
- A practitioner **restored on revert** (within 30 days, previously Credentialed) has `PRM_PNC__c = false` (or non-PNC) and their **old recred due date restored** → naturally re-included when due.
- `PRM_CheckCAQHExecuteHelper.processAccount` has no separate PNC gate. `PRM_UpdateCaseManagerBatch` operates only on existing CMs.

**Mapping the confirmed rule to today:**

| Rule | Today | Change? |
|---|---|---|
| PNC (regular) → no recred | Excluded by `PRM_PNC__c = false` | None |
| Override/Bypass ON (forced PNC, blank recred due date) → no recred | Excluded by `PRM_PNC__c = false` **and** blank due date | **None (was: add bypass — now dropped)** |
| Reverted within 30 days (restored Credentialed + old due date) → recred when due | Included once PNC=false and due date restored | None (relies on restore) |
| Non-PNC → unchanged | Included by `PRM_PNC__c = false` | None |

---

## Acceptance Criteria

**AC-1 — Regular PNC practitioners are skipped**

**Given** a practitioner is PNC (not via override),
**When** the monthly recredentialing cycle runs,
**Then** no recred case manager is created for them (unchanged from today).

**AC-2 — Override/Bypass practitioners are skipped**

**Given** a practitioner forced into PNC via the Override/Bypass flag (PNC = yes, recred due date blank),
**When** the recredentialing cycle runs,
**Then** no recred case manager is created for them,
**And** no special inclusion logic re-adds them.

**AC-3 — Restored practitioners re-enter the cycle**

**Given** a practitioner whose Override was reverted within 30 days and whose Credentialed status + old recred due date were restored,
**When** the recredentialing cycle runs and they are due,
**Then** a recred case manager is created for them exactly like any credentialed practitioner.

**AC-4 — Non-PNC and existing exclusions unchanged**

**Given** non-PNC, delegated-only, or inactive practitioners,
**When** the cycle runs,
**Then** non-PNC due practitioners get a recred case manager as today, and delegated-only/inactive remain excluded.

**AC-5 — No duplicate or missed case managers at month boundaries**

**Given** a mixed due population,
**When** the cycle runs and the month-end update chains afterward,
**Then** each eligible practitioner gets exactly one recred case manager, PNC/override practitioners get none, and the chained update/notification batches operate without error.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CheckCAQHAccessOnDueAccountsBatch.generateQueryString()` | **Verify (no change)** | Confirm the existing `PRM_PNC__c = false` + recred-due-date filter correctly excludes override/PNC practitioners; **do not** add `OR PRM_BypassPNC__c = true` | Drives AC-1, AC-2 |
| Restore dependency | Cross-story | Re-inclusion of reverted practitioners depends on the 30-day restore setting `PRM_PNC__c = false` + old `PRM_ReCredDueDate__c` (see CredentialingStatus + Flow stories) | Drives AC-3 |
| `PRM_CheckCAQHExecuteHelper.processAccount` | Verify Apex | Confirm no path re-adds PNC/override accounts | Drives AC-2 |
| `PRM_UpdateCaseManagerBatch` | Verify Apex (regression) | No change expected | Drives AC-5 |
| `PRM_CheckCAQHAccessOnDueAccountsTest` | Modified test | Add: regular-PNC excluded, override-PNC (blank due date) excluded, restored (PNC=false + due date) included, non-PNC included, delegated-only/inactive excluded | ≥85% gate |

---

## Definition of done

- [ ] Confirmed **no filter change** is made (the earlier `OR PRM_BypassPNC__c = true` is not implemented).
- [ ] Regular-PNC and override-PNC practitioners get no recred case manager (AC-1, AC-2) — verified in QA.
- [ ] Restored practitioners (revert < 30 days) receive a recred case manager when due (AC-3) — verified in QA.
- [ ] Non-PNC unchanged (AC-4); delegated-only/inactive still excluded.
- [ ] Exactly one recred case manager per eligible practitioner across a month boundary; chained batches error-free (AC-5).
- [ ] ≥85% Apex coverage incl. the exclusion/inclusion branches; real assertions on which accounts produced a case manager.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | *(Resolved Jul 2026)* Override/Bypass = force into PNC → blank recred due date → **excluded** from recred (the earlier "include bypass" proposal is dropped). | Core direction | ✅ Business |
| 2 | Should a practitioner **restored** mid-cycle (revert after their due date already passed) be back-filled into the current cycle or picked up next window? | One-time catch-up vs forward-only | BA |
| 3 | Confirm the 30-day restore reliably re-populates `PRM_ReCredDueDate__c` before the recred window opens, so restored practitioners aren't missed. | Timing dependency on the restore | Technical / BA |
| 4 | Any recred reporting/list views (e.g. `PRM_OpenRecredCasesbyDueDate_Case`, `PRM_RecredDuePractitionersReportBatch`) that need alignment with the override-exclusion behavior? | Downstream report accuracy | BA / Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CheckCAQHAccessOnDueAccountsBatch` | Apex | LOW (verify) | Existing filter already excludes override/PNC; no functional change |
| `PRM_CheckCAQHExecuteHelper` | Apex | LOW | Verify no secondary re-inclusion |
| `PRM_UpdateCaseManagerBatch` | Apex | LOW | Chained month-end update; regression only |
| Restore behavior (CredentialingStatus + Flow stories) | Apex/Flow | (Dependency) | Re-inclusion of reverted practitioners depends on the restore populating due date |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Filter verification (no change) | Apex review | S | Confirm exclusion holds |
| `PRM_CheckCAQHExecuteHelper` verification | Apex | S | Confirm no secondary gate |
| Test coverage (exclusion/inclusion + negatives) | Apex test | M | ≥85% gate |
| Regression (chained batches + reports) | QA | M | Month-boundary run |

**Total Estimated Effort:** **S–M** (verification/regression; the functional behavior comes from the CredentialingStatus + Override-flow stories)
