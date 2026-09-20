# Credentialing LWC Redesign — Demo POC Execution Plan

> **STATUS: PROPOSAL — awaiting review.** No components, objects, or deploys are created until this plan is reviewed and the Open Questions (§7) are answered.
>
> **Source of truth:** `MASTER_Development_Plan_Credentialing_LWC_Redesign.md` (vision) + `POC_Audit_And_Reuse_Map.md` (what already exists). This plan only builds the *missing* shell and reuses the four existing action centers.
>
> **Format mirrors** `docs/implementation-plan/Epic_A_Execution_Plan.md` (CONFIRMED / OPEN / RISK / RECOMMENDATION tags; tasks list Purpose · Outcome · Dependencies · Validation · Risks · Completion).
>
> **Date:** 2026-06-23

> ### ⛔ STRICT RULE — NO EDITS TO EXISTING COMPONENTS
> This is a demo. Every reuse is **by reference only** (launch / import / copy-into-new-file). **No existing component, Apex class, object, field, permission set, flexipage, or layout may be edited, refactored, renamed, or re-versioned.** All changes live in new files. This forces the **console-subtab launch** model (it needs zero edits); modal embedding is deferred because it would require editing the action centers.

---

## 1. POC objective & scope

### 1.1 Objective
- **[CONFIRMED]** Prove the tile-based credentialing redesign on **one flow (Application Review)** by **reusing the four deployed action centers** (`prmLaunchCredentialsAction`, `prmLaunchContactAction`, `prmLaunchProviderAction`, `prmLaunchAddressAction`) as the editable tiles, plus the CAQH compare component, behind a **new thin tile dashboard** with progress + pause/resume.
- **[CONFIRMED]** Demonstrate: visual progress, complete-in-any-order tiles, independent save (no 4 MB limit), resume from any device, CAQH read-only vs SF editable.

### 1.2 In scope
- 2 custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`).
- 1 Apex controller (`PRM_VerificationSessionController`) + test.
- 3 thin LWCs (`prmVerificationDashboard`, `prmProgressHeader`, `prmVerificationTile`).
- Minimal embed tweaks to the 4 action centers (`@api recordId` exposure / target add).
- 1 FlexPage placement on `IndividualApplication` (Case Manager) + 1 permission set.

### 1.3 Out of scope (POC)
- QC flows (4, 5), PDA QC (6), `prm_qcWrapper`, network dual-listbox, directory cascade.
- New editors for App Review tiles that have **no existing component** (Education, Work History, Malpractice, Adverse Action) — these render **read-only or "coming soon"** in the POC.
- Final-submit aggregation into `PRM_ReviewPSVCaseRecordsUpdate` (POC ends at per-tile save + status); wire as fast-follow.
- Dynamic `lwc:component` modal injection — POC launches action centers as **console subtabs** (reuses proven `prmGenericButtonLauncher` logic).

---

## 2. Constraints

- **[CONFIRMED]** Follow `.cursor/skills/salesforce-development/SKILL.md` + LWC best-practices rule (Lightning base components, SLDS, `@wire` error handling, ≥85% Jest/Apex coverage, no SOQL/DML in loops, `with sharing`, CRUD/FLS via `WITH USER_MODE`/`stripInaccessible`).
- **[CONFIRMED]** `PRM_` prefix; LWC folders camelCase (`prmVerificationDashboard`); Apex `PRM_*Controller`; tests `<Class>Test`.
- **[CONFIRMED]** `IndividualApplication` is the Case Manager record (`recordId` = its Id), consistent with the high-volume program.
- **[CONFIRMED]** Reuse existing controllers/selectors — do not rebuild (`PRM_BusinessLicenseController`, `PRM_ContactInformationController`, `PRM_ProviderInformationController`, `PRM_AddNewLocationUtility`, `PRM_AppReviewMatchController`, `PRM_AddressSelector`).

---

## 3. Dependencies & prerequisites

- **[CONFIRMED]** The 4 action centers + their controllers + shared blocks already deployed (verified in repo).
- **[OPEN] OQ-1 — Target org** (alias / scratch vs `ibx--qa`).
- **[CONFIRMED]** `IndividualApplication`, `BusinessLicense`, `PersonEducation`, `Account`, CAQH objects exist in org.

---

## 4. Acceptance criteria

- **[CONFIRMED]** AC1: Dashboard on a Case Manager (`IndividualApplication`) renders a tile grid with live status badges (pending / in-progress / completed / error).
- **[CONFIRMED]** AC2: Clicking a tile opens the corresponding **existing** action center scoped to the same `recordId`.
- **[CONFIRMED]** AC3: Completing a tile (save in the action center) updates `PRM_VerificationTileStatus__c` → reflected in progress header on return.
- **[CONFIRMED]** AC4: Leaving and reopening the dashboard **resumes** with prior tile statuses (pause/resume).
- **[CONFIRMED]** AC5: A CAQH-backed tile shows CAQH data read-only beside editable SF data (reusing `prmAppReviewCaqhMatch`).
- **[CONFIRMED]** AC6: ≥85% Apex + Jest coverage on new code; deploys clean to OQ-1 org.

---

## 5. Phases, milestones & task breakdown

### Phase 0 — Setup *(milestone M0: ready to author)*

**T0.1 — Working branch**
- Purpose: isolate POC work. Outcome: branch `poc/cred-tile-dashboard` from `main`. Validation: branch exists. Risk: none. Completion: created.

**T0.2 — Confirm org & embed decision ⛔ Pending (OQ-1, OQ-2)**
- Purpose: target org + embed-vs-subtab decision. Outcome: both confirmed in writing. Completion: documented.

### Phase 1 — Data model *(milestone M1: objects deployable)*

**T1.1 — `PRM_VerificationSession__c`**
- Purpose: track a reviewer's session per Case Manager + flow.
- Outcome: object (OWD Private), Auto-Number Name `VS-{0000000}`; fields: `PRM_CaseManager__c` (Lookup→IndividualApplication), `PRM_FlowType__c` (restricted picklist: `ApplicationReview`/`PSVReview`/`ReCredPSVReview`/`PSVQCReview`/`ReCredPSVQCReview`/`PDAQCReview`), `PRM_Status__c` (`In Progress`(def)/`Completed`/`Abandoned`), `PRM_LastAccessedBy__c` (Lookup→User), `PRM_LastAccessedDate__c` (DateTime), `PRM_CompletedTileCount__c` / `PRM_TotalTileCount__c` (Number).
- Deps: none. Impacted: `objects/PRM_VerificationSession__c/`. Validation: describe. Risk: **[RISK]** picklist values must match plan §2 `Flow_Type__c`. Completion: deploys.

**T1.2 — `PRM_VerificationTileStatus__c`**
- Purpose: per-tile status within a session.
- Outcome: Master-Detail → `PRM_VerificationSession__c` (reparent=false), Auto-Number `VTS-{0000000}`; fields: `PRM_TileId__c` (Text), `PRM_TileLabel__c` (Text), `PRM_Status__c` (`Pending`(def)/`In Progress`/`Completed`/`Error`), `PRM_CompletedBy__c` (Lookup→User), `PRM_CompletedDate__c` (DateTime), `PRM_Notes__c` (LongText), `PRM_ModifiedAfterCompletion__c` (Checkbox).
- Deps: T1.1. Validation: describe + M-D. Risk: M-D parent first. Completion: deploys.
- **[RECOMMENDATION]** Per audit A5, do **not** store field-level draft JSON — action centers commit their own data; this object tracks **status only**.

### Phase 2 — Apex *(milestone M2: data layer)*

**T2.1 — `PRM_VerificationSessionController`**
- Purpose: get-or-create session, list tile statuses, upsert tile status, compute progress.
- Outcome: `with sharing` controller, methods: `getOrCreateSession(Id caseManagerId, String flowType)`, `getTileStatuses(Id sessionId)`, `upsertTileStatus(...)`, `markTileComplete(...)`; all `@AuraEnabled`, CRUD/FLS via `WITH USER_MODE`; bulk-safe; no DML/SOQL in loops.
- Deps: T1.*. Validation: Apex test ≥85% (bulk + single + negative). Risk: **[RISK]** governor-safe progress recompute — do it in one query/update. Completion: tests pass.

**T2.2 — `PRM_VerificationSessionControllerTest`** — factory data, no `SeeAllData`, assert outcomes.

### Phase 3 — Framework LWCs *(milestone M3: shell)*

**T3.1 — `prmVerificationTile`** (presentational)
- Purpose: one tile card. Outcome: `@api tile` (id,label,icon,status), status badge styling, `onclick` → emits `tileselect`. Deps: none. Validation: Jest (renders badge per status; emits event). Completion: covered.

**T3.2 — `prmProgressHeader`** (presentational)
- Purpose: progress bar + session info. Outcome: `@api completed`, `@api total`, `@api lastSaved`, `@api reviewerName`. Validation: Jest. Completion: covered.

**T3.3 — `prmVerificationdashboard`** (container)
- Purpose: tile grid + orchestration. Outcome: `@api recordId`; on load calls `getOrCreateSession` + `getTileStatuses`; renders `prmPractitionerSummary` + `prmProgressHeader` + tile grid; on `tileselect` opens the mapped action center **as a console subtab** (lift `prmGenericButtonLauncher.openOrFocusSubtab`) passing `c__recordId`; refreshes statuses on focus return; tile→component map is a constant.
- Deps: T2.1, T3.1, T3.2. Impacted: new bundle + reuse `prmPractitionerSummary`, `prmGenericInlineError`. Validation: Jest (mock wires, assert subtab open + grid render). Risk: **[RISK]** subtab focus-return refresh; **[RISK]** non-console fallback (Navigate). Completion: AC1–AC4 demoable.

### Phase 4 — Reuse wiring *(milestone M4: tiles live)*

**T4.1 — Launch action centers (NO EDITS to them)**
- Purpose: open each existing action center scoped to the dashboard `recordId` **without modifying it**.
- Outcome: dashboard opens `c__prmLaunch*Action` as a console subtab passing `c__recordId=recordId` (the existing `lightning__UrlAddressable` target already supports this; the action-center JS already reads `c__recordId` from page state). **No target/`@api`/field edits to any action center.**
- Deps: T3.3. Validation: open each center from a tile, correct practitioner loads. Risk: **[RISK]** R1/R2 from audit. Completion: all 4 launch + load with zero edits to existing bundles.
- **[CONSTRAINT]** Strict no-edit rule (see §0). The subtab path is chosen precisely because it requires **no** change to existing components. Modal embedding (which would need edits) is explicitly deferred.

**T4.2 — CAQH compare tile**
- Purpose: read-only CAQH beside editable SF. Outcome: reuse `prmAppReviewCaqhMatch` (+ `PRM_AppReviewMatchController`) as a tile target. Deps: T3.3. Validation: AC5. Completion: CAQH panel renders.

**T4.3 — Tile inventory config (App Review)**
- Purpose: define POC tiles. Outcome: constant mapping — `Credentials/License`→`prmLaunchCredentialsAction`, `Contact`→`prmLaunchContactAction`, `Provider/Diversity/Languages`→`prmLaunchProviderAction`, `Address`→`prmLaunchAddressAction`, `CAQH Compare`→`prmAppReviewCaqhMatch`, plus **read-only/"coming soon"** placeholders for Education, Work History, Malpractice, Adverse Action, File Upload, Final Submit. Deps: T3.3. Validation: AC2. Completion: tiles render + route.

### Phase 5 — Access & placement *(milestone M5)*

**T5.1 — Permission set `PRM_CredTileDashboard_Access`** — R/C/E on the 2 objects + FLS; assignable. Validation: assigns. 
**T5.2 — FlexPage / tab placement** — place `prmVerificationDashboard` on the Case Manager (`IndividualApplication`) record page (and/or app page). Validation: renders for a test Case Manager.

### Phase 6 — Deploy, test, demo *(milestone M6: signed off)*

**T6.1 — Validate-only deploy** to OQ-1 org. ⛔ Pending OQ-1.
**T6.2 — Deploy + smoke** (objects → permset → Apex → LWC → FlexPage).
**T6.3 — End-to-end demo script** — load Case Manager → dashboard → open each action center → save → see progress update → reload → resume → CAQH compare. Validation: AC1–AC6.
**T6.4 — Lightweight evidence** (deploy result, Jest/Apex coverage, demo recording/screens) + sign-off on PR.

---

## 6. Suggested timeline (POC)

| Day | Work |
|---|---|
| 1 | T0, T1.1–T1.2 (objects), permission set scaffold |
| 2 | T2.1–T2.2 (controller + tests) |
| 3 | T3.1–T3.2 (tile + header) + Jest |
| 4 | T3.3 (dashboard) + subtab launch wiring |
| 5 | T4.1–T4.3 (reuse wiring, CAQH tile, tile config) |
| 6 | T5 (permset + FlexPage), T6.1–T6.2 (deploy + smoke) |
| 7 | T6.3–T6.4 (demo script, evidence, polish) |

**~7 working days for the POC** (vs. the master plan's 8-week Flow-1 build), because ~75–85% of the editing surface is reused.

---

## 7. Open Questions & Decisions Log

- **◻ OQ-1 — Target org** (alias / scratch vs `ibx--qa`) — gates deploy (Phase 6).
- **✅ OQ-2 — Embed model: RESOLVED → console subtab.** Modal injection would require editing the action centers, which the strict no-edit rule forbids. Subtab launch is the only compliant path for the POC.
- **◻ OQ-3 — Persistence depth:** **status-only** (recommended) vs field drafts.
- **◻ OQ-4 — POC flow:** **Application Review** (recommended).
- **◻ OQ-5 — Tile↔component sign-off** incl. which App Review tiles are read-only/stub for POC.
- **◻ OQ-6 — Final submit:** in POC (aggregate to `PRM_ReviewPSVCaseRecordsUpdate`) or fast-follow (recommended: fast-follow).

---

## 8. Re-baselining the full program (post-POC)

- **[RECOMMENDATION]** After the POC validates reuse, re-estimate Flows 1–6. Expect the editing-tile portions of Flow 1 (App Review) and Flow 2 (PSV) to shrink substantially (Contact, Provider/diversity/languages, License, Address already exist). Net-new effort concentrates in: the shell (built once in POC), `prm_qcWrapper` + QC summaries (Flows 4/5), and PDA QC networks/directory (Flow 6).

---

## 9. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| P1 | Action centers console-coupled (`platformWorkspaceApi`) | Med | Med | JS no-ops off-console; dashboard provides close path |
| P2 | `recordId` via page state when embedded | High | Low | set `@api recordId`; wires react |
| P3 | Immediate commit (no dashboard transaction) | Med | Med | per-tile independent save = plan intent |
| P4 | App Review tiles w/o existing editor | Med | Med | read-only/stub in POC; phase-2 backlog |
| P5 | apiVersion drift (64/65) across bundles | Low | Low | normalize on deploy |
| P6 | Subtab focus-return status refresh flakiness | Med | Low | refresh on `connectedCallback` + focus event |
