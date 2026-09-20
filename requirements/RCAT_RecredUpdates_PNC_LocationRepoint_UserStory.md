# USER STORY: RCAT "Recred Updates" Termination — Source Location PNC from the Practice Location, Not the Group

> Authored with the **User Story Solution Architect** (v1.10). Vertical: **Provider Network Management (PNM)**.
> Companion to the RCAT **review** re-point (`US-AR2` in `PRM_PNC_AppReview_Flows_User_Stories.md`). This story covers the **downstream PDM "Recred Updates" termination** the review hands off to.
> **Depends on:** US1 (`HealthcareFacility.PRM_PNC__c` field exists — confirmed on disk), US4 (rollup helpers). **Related:** `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md`.

**Persona:** Provider Data Management (PDM) Specialist
**Priority:** P0
**OmniScript:** `PRM_ReCredUpdate_English` (no change — verified PNC-clean)
**Integration Procedures:** `PRM_FetchFormRecredUpdate_Procedure`, `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (no change — verified PNC-clean)
**Apex (the actual change surface):** `PRM_FullPracTermRecredBatchService`, `PRM_PractitionerTerminationBatchHelper` (invoked via `PRM_PractitionerTerminationUtility.FullPractitionerTerminationBatchRecred` → `PRM_FullPracTerminationRecredBatch`)
**Relevant Requirements:** `PRM_PNC_AppReview_Flows_Update_Analysis.md`; `PRM_PNC_Logic_Change_Implementation_Plan.md`; `PRM_PNC_AppReview_Flows_User_Stories.md` (US-AR2)

---

## Story

**As a** Provider Data Management (PDM) Specialist working a recredentialing "Recred Updates" case,
**I want** the termination to decide which of a practitioner's practice locations are protected as PNC (Par Non Cred) based on **each practice location's own PNC status**, not the group/vendor's single PNC flag,
**So that** a non-PNC location under a group that used to be flagged PNC is correctly terminated, and a genuinely PNC location is correctly preserved.

**Why it matters:** PNC is moving from the group/vendor to the practice location. Today the recred termination protects a location from termination based on the **group's** PNC flag, so every location under a "PNC group" is shielded — even locations that are not actually PNC. After the migration, protection must follow the location's own PNC, or recred terminations will leave stale, still-active locations behind (a directory-accuracy and claims-integrity risk).

---

## Scope

| Flow | Component | Affected Step | Data Source (where PNC is read) |
|------|-----------|---------------|-------------|
| Recred Updates (PDM) | `PRM_ReCredUpdate_English` | Practitioner/PL termination submit | OmniScript — **no PNC reference (verified)** |
| Recred Updates (PDM) | `PRM_FetchFormRecredUpdate_Procedure` | Load PL + networks (`DRGetPLNetworks` → `PRMFetchExistingHCFNPNC`) | DataRaptor named "…HCFNPNC" but reads **no** PNC field (verified) |
| Recred Updates (PDM) | `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` | `CallPractitionerTerminationBatch` | `PracLocPNC` only in SampleInput; calls `PRM_PractitionerTerminationUtility.FullPractitionerTerminationBatchRecred` |
| Recred Updates (PDM) | `PRM_FullPracTermRecredBatchService` | `executeTermination` builds the PNC exclusion map | **`HealthcareFacility.Account.PRM_PNC__c`** ← the vendor read to re-point |

---

## Current State (from codebase)

### OmniStudio layer — no change needed (verified)
- **`PRM_ReCredUpdate_English`** — full-folder scan for `pnc` returns nothing. No PNC element, message, or binding.
- **`PRM_FetchFormRecredUpdate_Procedure`** — its only "PNC" reference is the DataRaptor `PRMFetchExistingHCFNPNC`, which (despite the name) reads only `HealthcareFacility`, `HealthcareFacilityNetwork` (PracticeLocationNetwork), and `PRM_InfoCodeAssignment__c` fields — **no `PRM_PNC__c`**. Legacy naming; no re-point.
- **`PRM_PractitionerTerminationRecordsRecredUpdate_Procedure`** — `PracLocPNC` / `PracLocPNCPL` appear only in `SampleInput.json`, never in a logic/filter element. It calls Apex `PRM_PractitionerTerminationUtility.FullPractitionerTerminationBatchRecred`.

### Apex layer — the actual vendor read
- **`PRM_FullPracTermRecredBatchService.executeTermination`** (~lines 366–376): builds `hcfAccPNCMap` from `if(hcf.Account.PRM_PNC__c)` — i.e. from the **vendor** account, keyed by facility Id.
- That map drives **termination exclusion**: skip the practitioner↔location link (~lines 33–38), skip the practice-location network record (~lines 49–54), skip practice-to-practice affiliations for PNC accounts (line 40 via `AccPNCIds`), and select the Full-Termination vs. Recred branch (`hasPNCOrDelegated`, ~lines 393–400).
- **`PRM_PractitionerTerminationBatchHelper.getHealthcareFacility`** (~line 608) is the SOQL that sources it: `SELECT id, accountid, …, Account.PRM_PNC__c FROM HealthcareFacility WHERE Id IN :hcfIds`.
- **Credentialing status** is set to `'Terminated'` on the practitioner account (`…Service` ~line 72; `PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner` ~lines 564/583). This is correct for a termination and is **not** PNC-dependent — no change.
- This flow does **not** recompute or write the practitioner rollup `Account.PRM_PNC__c`, so there is no BypassPNC interaction here.

---

## Acceptance Criteria

**AC-1 — A genuinely PNC practice location is preserved during recred termination**

**Given** a PDM Specialist completes a Recred Updates termination for a practitioner who has a practice location marked as PNC at the practice-location level,
**When** the termination runs,
**Then** that PNC practice location and its related records (the practitioner's link to it and its network participation) are left active,
**And** the location's PNC status is determined by the practice location itself, not by the group it belongs to.

**AC-2 — A non-PNC location under a formerly-PNC group is now terminated**

**Given** a practitioner has a practice location that is **not** PNC, but that location belongs to a group that was historically flagged PNC,
**When** the recred termination runs,
**Then** that non-PNC practice location and its related records are terminated (effective-dated closed) as normal,
**And** the old group-level PNC flag no longer shields it from termination.

**AC-3 — Locations under the same group are evaluated independently**

**Given** a practitioner has two practice locations under the same group, one PNC and one not PNC,
**When** the recred termination runs,
**Then** the PNC location is preserved and the non-PNC location is terminated,
**And** the two locations are not forced to the same PNC outcome by a shared group value.

**AC-4 — Full-Termination vs. Recred branch honours location PNC**

**Given** a recred termination is submitted with no practice location that is PNC or delegated,
**When** the termination runs,
**Then** it follows the full-termination path,
**And** when at least one in-scope location is PNC at the practice-location level, it follows the recred path that preserves the PNC location(s).

**AC-5 — No regression to practitioner and network termination**

**Given** a recred termination that ends a practitioner's participation,
**When** the termination runs,
**Then** the practitioner-side records (person account, affiliations, providers, taxonomy, NPI, identifiers, boards) and non-PNC network records are terminated exactly as they are today,
**And** the practitioner's credentialing status is set to Terminated exactly as today,
**And** the run stays within platform limits for a bulk recred case.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PractitionerTerminationBatchHelper.getHealthcareFacility` | Modified Apex (SOQL) | Add `PRM_PNC__c` to the `HealthcareFacility` select; stop relying on `Account.PRM_PNC__c` for the location's PNC | Drives AC-1–AC-4 |
| `PRM_FullPracTermRecredBatchService.executeTermination` | Modified Apex | `if(hcf.Account.PRM_PNC__c)` → `if(hcf.PRM_PNC__c)`; `hcfAccPNCMap.put(hcf.Id, hcf.PRM_PNC__c)` | Core re-point; drives AC-1–AC-4 |
| `AccPNCIds` derivation (same method) | Verify/Adjust Apex | Confirm the practice-to-practice (account-level) exclusion still behaves correctly once the map is location-sourced | See Clarification #2 |
| `PRM_ReCredUpdate_English`, `PRM_FetchFormRecredUpdate_Procedure`, `PRMFetchExistingHCFNPNC`, `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` | No change | Verified PNC-clean | AC-1 (regression) |
| Credentialing-status writes (`…Service` term, `setTermDataPractitioner`) | No change | `'Terminated'` on termination is not PNC-dependent | AC-5 |
| `PRM_FullPracTerminationRecredBatchTest` | Modified test | Re-point setup from vendor `Account.PRM_PNC__c` to `HealthcareFacility.PRM_PNC__c`; add mixed-PNC-under-one-group case | ≥85% gate; AC-1–AC-4 |

---

## Definition of done

- [ ] Recred termination preserves a location that is PNC at the practice-location level (AC-1) — verified in QA.
- [ ] A non-PNC location under a formerly-PNC group is terminated (AC-2) — verified in QA.
- [ ] Mixed PNC / non-PNC locations under one group resolve independently (AC-3).
- [ ] Full-Term vs. Recred branch selection is driven by location PNC (AC-4).
- [ ] No `hcf.Account.PRM_PNC__c` (vendor) read remains in the recred termination path (grep clean).
- [ ] Practitioner-side + network termination and `Terminated` credentialing status show no regression (AC-5).
- [ ] ≥85% Apex coverage incl. bulk, single, PNC-preserved, and non-PNC-terminated paths; real assertions on which records were left active vs. termed.
- [ ] Shadow-mode parity for a recred case spanning PNC and non-PNC locations under one group.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the companion **non-LMS auto-batch** path (`PRM_RCATLocationTerminationBatch` → `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner`, which reads `HealthcarePractitionerFacility.Account.PRM_PNC__c` and also writes the practitioner rollup + blanks credentialing status) be a **separate story**, or folded here so the whole RCAT termination side re-points together? | Scope — one story vs. two | Technical / BA |
| 2 | After the map is location-sourced, is the account-level `AccPNCIds` (practice-to-practice) exclusion still meaningful, or should it be dropped/redefined? | Whether the P2P branch changes | Technical |
| 3 | During the transition, do we need a fallback to the group PNC for locations whose `HealthcareFacility.PRM_PNC__c` has not yet been backfilled, or is the migration a hard cutover? | Backfill dependency / interim behaviour | BA / Data |
| 4 | Confirm `PRM_PractitionerTerminationBatchHelper.queryRecords` (line 20, also selects `Account.PRM_PNC__c`) is used only by `PRM_ReinstateVendorAccountBatch` and is **out of scope** here. | Prevents an unnecessary edit | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_FullPracTermRecredBatchService` | Apex | HIGH | Builds the PNC exclusion map that governs what recred termination preserves |
| `PRM_PractitionerTerminationBatchHelper` | Apex | HIGH | SOQL that sources the facility PNC value |
| `PRM_FullPracTerminationRecredBatch` / `PRM_PractitionerTerminationUtility` | Apex | LOW | Orchestration only — no PNC logic |
| `PRM_ReCredUpdate_English` / `PRM_FetchFormRecredUpdate_Procedure` / `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` | OmniScript / IP | LOW | No change — verified PNC-clean; regression only |
| `PRM_RCATTerminationBatchHelper` (auto-batch sibling) | Apex | MEDIUM | Same vendor-PNC pattern; re-point via this story or a companion (Clarification #1) |
| `HealthcareFacility`, `HealthcarePractitionerFacility`, `HealthcareFacilityNetwork`, `Account` | Objects | HIGH | Records preserved/terminated by the cascade |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_PractitionerTerminationBatchHelper.getHealthcareFacility` SOQL | Apex | M | Add location field to select |
| `PRM_FullPracTermRecredBatchService.executeTermination` map build | Apex | M | Re-point read + verify `AccPNCIds` |
| `PRM_FullPracTerminationRecredBatchTest` | Apex test | L | Re-point setup to location PNC + mixed-group case |
| Shadow parity / regression | QA | M | PNC + non-PNC under one group |

**Total Estimated Effort:** **L** — nearer XL if the auto-batch sibling (Clarification #1) is folded in.
