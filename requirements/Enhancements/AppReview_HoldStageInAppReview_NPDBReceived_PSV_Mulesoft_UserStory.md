# USER STORY: Keep Case Manager in "Application Review" Until NPDB Report Is Received — Let MuleSoft Advance the Stage to "PSV"

**Persona:** Credentialing Specialist (Initial Credentialing)
**Priority:** P1
**OmniScript:** `PRM_CredentialAppReviewCompleteOS_English` (v2), `PRM_InitialCredentialAppReview_English` (v29)
**Integration Procedures:** `PRM_ReviewParCaseRecordsUpdateParent` → `PRM_ReviewParCaseRecordsUpdate` (v15)
**Relevant Requirements:** `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md`, `requirements/NPDB_T180/01_Architecture_Diagrams.md` (state diagram §4), `requirements/ReDesignCredFlows/Application_Review_LWC_Redesign_Detailed_Design.md`

---

## Story

**As a** Credentialing Specialist working initial credentialing cases,
**I want** a Case Manager that has finished Application Review but is still waiting on its NPDB report to remain in the **Application Review** stage (not jump to **PSV**),
**So that** the case's stage truthfully reflects where it sits in the lifecycle, and it only moves to **PSV** once the NPDB report is actually back.

**Why it matters:** Today, the moment a reviewer selects "Proceed to PSV", the Case Manager's stage flips to **PSV** even though the Case is set to **Pending NPDB** — so the stage and the real status disagree. Cases appear to be in PSV when no NPDB report exists yet, which corrupts queue counts, SLA reporting, and reviewer worklists, and lets PSV work start on a practitioner whose NPDB data has not returned.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Initial Cred — Application Review (Complete & Submit) | `PRM_CredentialAppReviewCompleteOS_English` | Set Values `SetProceedToPSVRecordUpdate` (the "Proceed to PSV" path) | Writes `RecordsToUpdate` → `PRM_ReviewParCaseRecordsUpdate` IP → `PRMUpdateIDCaseCaseMgr` (Load) |
| NPDB report inbound | N/A (MuleSoft) | NPDB report received → advance stage | MuleSoft inbound updates the Case Manager (`IndividualApplication`) |

---

## Current State (from codebase)

### `PRM_CredentialAppReviewCompleteOS_English` (v2) — Set Values element `SetProceedToPSVRecordUpdate`

- **Trigger condition:** `AppReviewResults = "Proceed to PSV"`.
- **Current behavior:** in one step it sets
  - `IndividualApplication.PRM_Stage__c = "PSV"` and `IndividualApplication.Status = "In Progress"`,
  - `Case.Status = "Pending NPDB"`,
  - a ContentNote titled *"Application Review to PSV"*.
- **Net effect (the defect):** the Case Manager shows stage **PSV** while the Case is **Pending NPDB** — the stage advances before the NPDB report exists.
- **Location:** `force-app/main/default/omniScripts/PRM_CredentialAppReviewCompleteOS_English_2.os-meta.xml` (element `SetProceedToPSVRecordUpdate`, ~lines 1736–1756).

### Other Set Values elements in the same OmniScript that also set `PRM_Stage__c = "PSV"`

- **`SetRecordPSVUpdate`** — fires only on `AppReviewReturnedResultsWithQC/WithoutQC = "Return to PSV"` (a return **from QC**, where NPDB is already complete).
- **`SetRecordQCUpdate`** — fires only on `AppReviewReturnedResultsWithQC = "Return to QC"`.
- These are **return paths from later stages**, not the initial Application-Review-to-PSV transition, so they are out of the primary defect's path (see Clarification Q3).

### Stage field & lifecycle

- The Case Manager stage lives on `IndividualApplication.PRM_Stage__c`. Known values: `Application Review`, `PSV`, `QC Review`, `Committee Review`, `Complete`.
- The persisted write happens via the App Review IP `PRM_ReviewParCaseRecordsUpdate` (v15) using the Load `PRMUpdateIDCaseCaseMgr` (`outputFieldName = PRM_Stage__c` on `IndividualApplication`) — i.e., the IP simply persists whatever stage the OmniScript Set Values put into `RecordsToUpdate`.
- The intended lifecycle is documented in `requirements/NPDB_T180/01_Architecture_Diagrams.md` §4: `Pending NPDB → Application Review → PSV → QC Review → …`. The current OmniScript skips ahead by writing `PSV` while still `Pending NPDB`.
- `Case.Status = "Pending NPDB"` is the marker that the NPDB report has not yet returned (per `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md` §6).

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_CredentialAppReviewCompleteOS_English` → `SetProceedToPSVRecordUpdate` | OmniScript Set Values element | On the "Proceed to PSV" path, **do not** set `IndividualApplication.PRM_Stage__c = "PSV"`. Set/leave it at `"Application Review"`. Keep `Case.Status = "Pending NPDB"` and the existing verification fields. (Activate a new OmniScript version.) |
| MuleSoft NPDB report inbound | Integration | When the NPDB report is received for a Case Manager currently in `Application Review` + `Pending NPDB`, update `IndividualApplication.PRM_Stage__c = "PSV"` (and clear the `Pending NPDB` status onto the PSV path). |
| SF inbound entry point | Apex / API (confirm existing vs new — Clarification Q1) | The endpoint MuleSoft calls to apply the report outcome must own the stage advance to `"PSV"`, idempotently. |

### Implementation Notes

- The IP layer (`PRM_ReviewParCaseRecordsUpdate` / `PRMUpdateIDCaseCaseMgr`) needs **no change** — it persists whatever stage the OmniScript supplies. Fixing the Set Values value is sufficient on the App Review side.
- Keep all other fields the element writes today (verification fields, ContentNote, `PRM_NPDBIssue__c`, `Case.Status = "Pending NPDB"`) unchanged. Only the `PRM_Stage__c` value changes from `"PSV"` to `"Application Review"`.
- OmniStudio versioning: clone `PRM_CredentialAppReviewCompleteOS_English` to a new version, edit the element, activate the new version, deprecate the old. Only one active version runs.
- The MuleSoft-driven update should be **idempotent** and **guarded**: advance to `"PSV"` only from `Application Review` + `Pending NPDB`, so a duplicate/late callback can't regress a case already in QC/Committee.

---

## Acceptance Criteria

**AC-1 — Application Review completion holds the stage when the NPDB report is not yet back**

**Given** a Credentialing Specialist has finished reviewing an initial-credentialing application whose NPDB report has not yet been received,
**When** they complete the review and choose "Proceed to PSV",
**Then** the Case Manager remains in the **Application Review** stage,
**And** the Case is marked **Pending NPDB**,
**And** the Case Manager is **not** shown as being in the **PSV** stage.

**AC-2 — MuleSoft advances the stage to PSV when the report arrives**

**Given** a Case Manager sitting in **Application Review** with status **Pending NPDB** after the reviewer chose "Proceed to PSV",
**When** the NPDB report is received through the MuleSoft integration,
**Then** the Case Manager's stage is updated to **PSV**,
**And** the Case is no longer **Pending NPDB**.

**AC-3 — Verification results and notes are preserved on the held case**

**Given** a Credentialing Specialist completes Application Review and chooses "Proceed to PSV" with the NPDB report still pending,
**When** the case is saved,
**Then** all Application Review verification outcomes (specialty, education, license, DEA, CDS, malpractice, work history, attestation, NPDB) and the review note are saved on the Case Manager exactly as today,
**And** only the stage differs — it stays **Application Review** instead of becoming **PSV**.

**AC-4 — A late or duplicate NPDB callback cannot regress a more advanced case**

**Given** a Case Manager that has already progressed beyond **Application Review** (e.g., it is in **PSV**, **QC Review**, or **Committee Review**),
**When** a duplicate or late NPDB-report message is received from MuleSoft for that Case Manager,
**Then** the Case Manager's stage is left unchanged,
**And** no regression to **PSV** or **Application Review** occurs.

**AC-5 — Return-from-QC and return-from-PSV paths are unaffected**

**Given** a Case Manager being returned to PSV or QC from a later review stage (not the initial Application-Review-to-PSV transition),
**When** the reviewer submits that return,
**Then** the stage behaves exactly as it does today (no change introduced by this story).

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|-----------|------|--------|-------|
| `PRM_CredentialAppReviewCompleteOS_English` (`SetProceedToPSVRecordUpdate`) | Modified OmniScript Set Values (new active version) | Change `IndividualApplication.PRM_Stage__c` from `"PSV"` to `"Application Review"` on the "Proceed to PSV" path; keep `Case.Status = "Pending NPDB"` and all verification fields | Drives AC-1, AC-3 |
| MuleSoft NPDB inbound + SF entry point | Integration + Apex/API | On report received, set `PRM_Stage__c = "PSV"` for cases in `Application Review` + `Pending NPDB`; idempotent + guarded | Drives AC-2, AC-4 |
| `PRM_ReviewParCaseRecordsUpdate` / `PRMUpdateIDCaseCaseMgr` | No change | Persists the stage value supplied by the OmniScript | Confirms AC-1 |

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Does a SF inbound endpoint already exist that MuleSoft calls when the NPDB report returns (e.g., an AAL/`PRM_AdverseActionLog__c` status update path), or must a new entry point be built to own the stage advance to PSV? | Determines whether AC-2 is a config/extend or a net-new integration build | Technical / Integration |
| 2 | When the NPDB report is received, what exact `Case.Status` / `IndividualApplication.Status` should the case land on alongside stage = PSV (today the OmniScript also creates the PSV `NewCase`)? Should MuleSoft create the PSV Case, or should that still happen at App Review submit while only the stage is held? | Defines the precise record shape MuleSoft must produce; affects PSV queue ownership | BA / Product |
| 3 | Do the "Return to PSV" (`SetRecordPSVUpdate`) and "Return to QC" (`SetRecordQCUpdate`) paths also need to honor an NPDB hold, or are they always post-NPDB and therefore out of scope? | Scope of OmniScript changes | BA / Credentialing Ops |
| 4 | Should this hold also apply to the **Provider Outreach** path (`SetRecordOutreachUpdate`), or only "Proceed to PSV"? | Whether additional Set Values elements change | BA / Credentialing Ops |
| 5 | Is this behavior expected in **both** the legacy OmniScript and the planned combined "Initial Credentialing Review" LWC redesign (`Application_Review_LWC_Redesign_Detailed_Design.md`)? | Avoids re-introducing the defect in the redesign | Product / Technical |
| 6 | For an NPDB report that returns with an issue/hit (`PRM_NPDBIssue__c`), does the stage still advance to PSV, or route differently? | Branch logic for AC-2 | Credentialing Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_CredentialAppReviewCompleteOS_English` | OmniScript | HIGH | The "Proceed to PSV" Set Values is the single source of the premature stage flip |
| MuleSoft NPDB inbound integration | Integration | HIGH | Becomes the owner of the App Review → PSV stage advance |
| `IndividualApplication.PRM_Stage__c` | Field (data) | MEDIUM | Stage values for in-flight initial-cred cases change meaning; report/dashboard filters relying on stage = PSV may need review |
| PSV worklists / queue counts | Reporting | MEDIUM | Counts become accurate; downstream PSV reports/automation keyed on stage = PSV will only pick up cases with a returned NPDB report |
| `PRM_ReviewParCaseRecordsUpdate` IP | Integration Procedure | LOW | No change; persists supplied stage |

---

## Definition of Done

- [ ] New active version of `PRM_CredentialAppReviewCompleteOS_English` holds stage at `Application Review` on the "Proceed to PSV" path (NPDB pending).
- [ ] MuleSoft inbound (and its SF entry point) advances stage to `PSV` only from `Application Review` + `Pending NPDB`; idempotent and guarded against regression.
- [ ] All Application Review verification fields and the review note are preserved unchanged.
- [ ] Return-from-QC / return-from-PSV paths verified unaffected.
- [ ] Reporting/queues validated against the corrected stage semantics.
- [ ] Clarification Questions resolved and reflected in final design.
- [ ] Regression: initial-cred happy path App Review → (NPDB received) → PSV → QC validated end-to-end in a sandbox.

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_CredentialAppReviewCompleteOS_English` Set Values | OmniScript element edit + new version + activation | M | Single value change; OmniStudio versioning overhead |
| MuleSoft NPDB inbound → stage advance | Integration + SF entry point | XL (new) / M (extend existing) | Depends on Clarification Q1 |
| Regression + reporting validation | QA / config | L | Lifecycle + queue/report checks |

**Total Estimated Effort:** M–XL — *AI-estimated; validate with team* (driven mainly by whether the MuleSoft inbound entry point already exists).
