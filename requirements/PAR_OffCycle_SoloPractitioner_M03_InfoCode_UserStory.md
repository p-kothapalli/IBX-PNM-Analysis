# USER STORY: Stamp the M03 – Sole Proprietor Info Code on a Solo Practitioner's Practice Location (PAR / Off-Cycle)

**Persona:** Credentialing Specialist
**Priority:** P1
**OmniScript:** `PRM_PractitionerParticipationForm_English_117` (PAR), `PRM_OffCycleCredentialing_English_63` (Off-Cycle) — Add Additional Groups / Recred scope pending CQ-6
**Integration Procedures:** `PRM_CreateRecordsForPCF_Procedure_35` (record-creation chain, extend)
**Apex:** `PRM_CreateHCFRelatedRecordsHelper` (extend), `PRM_IfcLoader` (duplicate-skip precedent), `PRM_InfoCodeAssTriggerHelper` (existing overlap guard), `PRM_PractitionerActivationExecutor` (PDA activation)
**Relevant Requirements:** New business ask (2026-08-19). **Companion to** `requirements/PAR_OffCycle_SoloPractitioner_GroupJoin_Restriction_UserStory.md` — that story *blocks* the invalid solo-to-solo join; this story *stamps* the info code on the valid one. Detection SOQL: `requirements/SOQL/2026-08-19_M03SoleProprietorInfoCode.md`

---



## Story

**As a** Credentialing Specialist,
**I want** the M03 – Sole Proprietor info code to be created automatically on a practice location when a solo practitioner is credentialed into their own solo group,
**So that** downstream directory, claims, and reporting consumers can identify sole-proprietor locations without anyone remembering to add the code by hand.

**Why it matters:** Sole-proprietor status drives directory display and claims handling, and today the M03 code only exists on locations that came across in the legacy LMS conversion. Measured in FC2 on 2026-08-19: of **98,048 active practice locations whose group NPI is an individual (Type 1) NPI, only 10,212 — 10.4% — carry M03**; the other **87,836 have no code at all**, and not a single M03 in the org was created by a guided flow. Every new solo PAR widens that gap, so the population consumers rely on is both stale and incomplete.

---



## Scope


| Flow                             | OmniScript (active version)                     | Affected Step                              | Data Source                                                                             |
| -------------------------------- | ----------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------- |
| PAR — Practitioner Participation | `PRM_PractitionerParticipationForm_English_117` | Post-PDA record creation (not form submit) | `PRM_CreateRecordsForPCF` → `PRM_CreateHCFRelatedRecordsHelper.handleHCFRelatedRecords` |
| Off-Cycle Credentialing          | `PRM_OffCycleCredentialing_English_63`          | Post-PDA record creation                   | Same chain                                                                              |
| Add Additional Groups / Recred   | **TBD — CQ-6**                                  | TBD                                        | TBD                                                                                     |


**Out of scope:** creating M03 at the group (Account) level (CQ-1); terminating M03 when a solo practitioner leaves the location (CQ-5); back-filling M03 onto solo practice locations that already exist without it (CQ-4 — sizing SOQL is provided in the companion SOQL file); PDM Manual Update and Provider Change flows, where a specialist can already add the code manually.

---



## Current State (from codebase and FC2 org)



### The info code already exists — no new metadata needed

Verified in FC2 (`00DcW000005NtYnUAK`):


| Attribute                                       | Value                                          |
| ----------------------------------------------- | ---------------------------------------------- |
| Info Code record name                           | `M03-Sole Proprietor`                          |
| Code                                            | `M03`                                          |
| Info Code (description)                         | `Sole Proprietor`                              |
| Enabled at Practice Location level              | **Yes** (`PRM_IsHealthcareFacility__c = true`) |
| Enabled at Group / Account level                | Yes (`PRM_IsAccount__c = true`) — see CQ-1     |
| Enabled at Practitioner Practice Location level | No                                             |
| Taxonomy-only                                   | No                                             |


The exact string `M03-Sole Proprietor` matters: the creation helper resolves info codes **by** `Name`, not by code, so any other spelling silently produces no record.

### Existing M03 population is legacy-only

- All M03 assignments in FC2 sit at the **practice location** level (`PRM_HealthcareFacility__c` populated; group, practitioner-practice-location, and taxonomy parents all blank) — confirming practice location is the correct level.
- Every one of them was created by the LMS conversion loads (bulk-created 2025-05-28 / 2025-06-02, effective dates back-dated to 2019–2024), carries a legacy `PRM_ExternalId__c` of the form `{TIN}-{Provider Name}-{NPI}-P-{Address}-{Zip}-{Phone}-M03`, and has no Case Manager. **No M03 has ever been created by a guided flow.**
- **No practice location currently holds more than one M03** (verified: zero locations with a duplicate assignment). The duplicate rule in AC-3 is therefore preventative — it protects a clean population rather than remediating a known defect.



### The creation path already exists and is generic

- `PRM_CreateHCFRelatedRecordsHelper.getInfoCodeAssignments()` builds practice-location info code assignments from a semicolon-delimited `SelectedInfoCodes` string of info code **Names**, setting Practice Location, Info Code, Effective From, Effective To, Pending, and Case Manager.
- `validateIFCAssignment()` already refuses any code not flagged `PRM_IsHealthcareFacility__c` — M03 passes that gate.
- **It does not check the database for an existing assignment.** It de-duplicates only within the incoming payload, so a repeat submission would attempt a second insert.



### Duplicate protection is split across two mechanisms

- `PRM_InfoCodeAssTriggerHelper.restrictUsersToEnterOverLapDates` blocks an insert when the same info code on the same parent has an **overlapping** effective-date range, raising `System.Label.PRM_ICAOverlapsDatesErrorMsg`. This is a hard error — if the chain hits it, the record write fails rather than skipping.
- `PRM_IfcLoader.loadIfc` shows the safe precedent: query existing `Practice Location + Info Code` pairs first, **silently skip** matches (counting them as `skippedCount`), insert the rest with partial-success `Database.insert(..., false)`, and route failures to `PRM_FailedRecordStaging__c` via `PRM_ExceptionLogger`.



### "Activated after PDA" is already automatic

`PRM_Active__c` on the assignment is a **formula field**, not a writable checkbox:

```
AND( PRM_EffectiveFrom__c <= TODAY(),
     NOT(PRM_Pending__c),
     NOT(PRM_IsErrorRecord__c),
     OR( ISBLANK(PRM_EffectiveTo__c), PRM_EffectiveTo__c > TODAY() ) )
```

So nothing can or should write to Active. `PRM_PractitionerActivationExecutor` (and `DFX_PractitionerActivationExecutor`) walk the `Info_Codes_Assignment__r` children at PDA, stamp Effective From with the Case Manager's approved date when it is blank, and flip Pending to false — at which point the formula resolves to Active on its own.

---



## Acceptance Criteria

> Patterns per `.cursor/skills/user-story-architect/references/ac-pattern-library.md`.
> AC-2 is the mandatory Pattern E record specification paired with AC-1.

**AC-1 — A solo practitioner credentialed into their own solo location gets the M03 code**

**Given** a Credentialing Specialist has taken a PAR request through PDA approval for a practitioner whose own individual NPI is the group NPI on the selected practice location,
**When** the request's records are created,
**Then** the practice location carries an info code assignment for **M03 – Sole Proprietor**,
**And** the assignment is visible on the practice location's Info Codes related list with the same effective date as the practitioner's link to that location.

**AC-2 — Records created when a solo practitioner joins their own solo location**

**Given** the conditions in AC-1 are met and no unexpired M03 assignment already exists on that practice location,
**When** the request's records are created,
**Then** the following record is created exactly as specified:

**Practice Location Info Code Assignment — Create**


| Field             | Value                                                                                           | Notes                                                                                                                                       |
| ----------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Info Code         | M03 – Sole Proprietor                                                                           | resolved by the exact record name `M03-Sole Proprietor`                                                                                     |
| Practice Location | {Selected Practice Location}                                                                    | the only parent populated                                                                                                                   |
| Effective From    | {Effective From of the practitioner's link to that location}                                    | if still blank at PDA, the Case Manager's approved date is stamped by the existing activation step                                          |
| Effective To      | *(blank)*                                                                                       | open-ended                                                                                                                                  |
| Pending           | {the same Pending flag the surrounding record-creation chain applies to its sibling info codes} | observed as `false` in the post-PDA PAR and Off-Cycle path                                                                                  |
| Case Manager      | {the PAR / Off-Cycle request}                                                                   |                                                                                                                                             |
| Is Error Record   | No                                                                                              |                                                                                                                                             |
| Active            | *(never written — formula)*                                                                     | resolves to Yes once Effective From is on or before today, Pending is No, Is Error Record is No, and Effective To is blank or in the future |


**Explicitly not populated:** Group, Practitioner Practice Location, Practice Location Taxonomy (M03 is not enabled at the Practitioner Practice Location level), Request Type, and External Id (the legacy LMS key format is not reproduced for guided-flow records — see CQ-7).

1. **AC-3 — An existing M03 assignment is never duplicated**
2. **Given** a practice location that already carries an M03 – Sole Proprietor assignment covering the new effective date,
**When** another solo practitioner request for that same location is approved through PDA,
**Then** no second M03 assignment is created,
**And** the record creation completes successfully with no error surfaced to the Credentialing Specialist,
**And** all other records for the request are created as normal.

**AC-4 — Rules that determine whether M03 is created**

M03 – Sole Proprietor is created on a practice location when **all** of the following hold; if any fails, no M03 is created and no error is raised:


| #   | Condition                                                                                                  | Create M03?                                                                |
| --- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1   | The practice location's group NPI is an **Individual** (Type 1) NPI                                        | Required                                                                   |
| 2   | That individual NPI belongs to the practitioner being credentialed into the location                       | Required                                                                   |
| 3   | The practice location has **no** M03 assignment whose effective date range overlaps the new effective date | Required                                                                   |
| 4   | The practice location's group NPI is an **Organization** (Type 2) NPI                                      | No — skip                                                                  |
| 5   | The practice location's group NPI is Individual but belongs to a *different* practitioner                  | Not reachable — blocked at intake by the companion story; skip defensively |
| 6   | The practice location has no group NPI on file                                                             | No — skip, and treat as a data gap (CQ-2)                                  |


**AC-5 — Group practice locations are untouched**

**Given** a Credentialing Specialist has taken a PAR request through PDA for a practitioner joining an organization (Type 2) group's practice location,
**When** the request's records are created,
**Then** no M03 – Sole Proprietor assignment is created,
**And** every other info code, program, network, and taxonomy record for that location is created exactly as it is today.

**AC-6 — The code activates after PDA, not before**

**Given** a solo practitioner's PAR request is still in flight and its records were created as pending,
**When** the Credentialing Specialist views the practice location before PDA approval,
**Then** the M03 assignment shows as not Active,
**And** once PDA approval completes and the effective date is on or before today, the same assignment shows as Active without anyone editing it.

**AC-7 — Multi-practitioner and multi-location submissions stay correctly attributed**

**Given** a submission covering several practitioners and several practice locations, only some of which are solo locations,
**When** the request's records are created,
**Then** exactly one M03 assignment is created per qualifying solo practice location,
**And** no M03 assignment is created on any non-qualifying location in the same submission.

**AC-8 — A failure to create M03 does not fail the credentialing request**

**Given** the M03 assignment cannot be saved for any reason,
**When** the request's records are created,
**Then** the practitioner, location link, and all other records for the request are still created,
**And** the failure is captured for follow-up in the failed-record staging queue with the practice location identified,
**And** the Credentialing Specialist is not blocked from completing the request.

---



## Technical Implementation (high-level)


| Component                                                  | Type           | Change                                                                                                                                                       | Notes                                                                                                           |
| ---------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `PRM_CreateHCFRelatedRecordsHelper.getInfoCodeAssignments` | Modified Apex  | Add a bulk pre-insert existence check on `PRM_HealthcareFacility__c` + `PRM_InfoCode__c` (with effective-date overlap) and skip matches instead of inserting | Drives AC-3; mirrors `PRM_IfcLoader.loadIfc`; prevents tripping `restrictUsersToEnterOverLapDates`              |
| `PRM_CreateHCFRelatedRecordsHelper`                        | Modified Apex  | Append `M03-Sole Proprietor` to the location's `SelectedInfoCodes` when the solo test in AC-4 passes                                                         | Drives AC-1, AC-4, AC-7; reuses the existing `validateIFCAssignment` gate                                       |
| Solo-location resolution                                   | Reuse          | Resolve `HealthcareFacility.PRM_NpiId__r.NpiType` and the NPI's owning practitioner in bulk                                                                  | Drives AC-4; **reuses** `PRMDRExtractSoloPracticeLocationOwner` **from the companion story** — build that first |
| `PRM_CreateRecordsForPCF`                                  | New IP version | Pass the resolved solo flag / owning practitioner through to the helper                                                                                      | Drives AC-1; version up, do not edit v35 in place                                                               |
| `PRM_CreateHCFRelatedRecordsHelper`                        | Modified Apex  | Wrap the info code insert in partial-success `Database.insert(..., false)` with `PRM_ExceptionLogger` + `PRM_FailedRecordStaging__c` routing                 | Drives AC-8                                                                                                     |
| `PRM_Active__c`                                            | **No change**  | Formula field — must not be written to                                                                                                                       | Drives AC-6; activation is the existing `PRM_PractitionerActivationExecutor` Pending flip                       |
| `PRM_OmniUtilsTest` / new test class                       | Apex tests     | Bulk (200), duplicate-skip, organization-NPI, missing-NPI, and insert-failure paths                                                                          | ≥ 85% coverage gate                                                                                             |


No new objects, fields, picklist values, or permission sets are required.

---



## Definition of done

- [ ] A solo practitioner credentialed into their own solo practice location produces exactly one `M03-Sole Proprietor` assignment at the practice location level, with the field values in AC-2 verified in the target org
- [ ] Re-running an approved solo request against the same practice location creates no second M03 and raises no error to the specialist (AC-3)
- [ ] A practitioner joining an organization-NPI group practice location produces no M03, and that location's existing info code / program / network / taxonomy records are unchanged (AC-5)
- [ ] The assignment reports not Active while pending and Active after PDA approval, with no manual edit and no write to the Active formula field (AC-6)
- [ ] A submission containing a mix of solo and group locations creates M03 only on the solo ones (AC-7)
- [ ] A forced M03 insert failure leaves the rest of the request's records intact and lands a row in `PRM_FailedRecordStaging__c` naming the practice location (AC-8)
- [ ] ≥ 85% Apex coverage on the modified helper, including a 200-record bulk case and the duplicate-skip and negative paths
- [ ] No regression to PAR, Off-Cycle, or PDM Manual Update info code creation, or to the Concierge rollup and BCBSA sync consumers listed in Impact Analysis

---



## Clarification Questions (Before Implementation)


| #   | Question                                                                                                                                                                                                                                                                                                                                                                                                                             | Impact                                                                                                       | Owner                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ----------------------- |
| 1   | The M03 info code is enabled at the **group (Account)** level as well as the practice location level, but every existing M03 record sits only at the practice location. Should a solo group's Account also receive M03?                                                                                                                                                                                                              | Adds a second record per submission and a second dedupe path; changes what directory/reporting consumers see | BA / Product            |
| 2   | What should happen when a practice location has **no group NPI** on file? AC-4 currently skips silently. **682 active locations** are in this state today.                                                                                                                                                                                                                                                                           | Silent skip could mask a data-quality gap that nobody ever sees                                              | BA / Ops                |
| 3   | If a practice location has an M03 assignment that is already **terminated** (Effective To in the past), should a new one be created for the new term, or should the location be treated as already coded? The existing trigger guard only blocks *overlapping* ranges, while the `PRM_IfcLoader` precedent skips on any prior pair — these disagree.                                                                                 | Determines whether re-credentialing a returning sole proprietor creates a new assignment or nothing          | BA / Technical          |
| 4   | Should M03 be **back-filled** onto the **87,836 active solo practice locations** currently missing it?                                                                                                                                                                                                                                                                                                                               | A remediation batch of substantial volume plus a data-fix approval, sized separately from this story         | Ops / BA                |
| 5   | When a solo practitioner **leaves** their solo practice location, should the M03 assignment be terminated (Effective To stamped)?                                                                                                                                                                                                                                                                                                    | A termination-side change in the practitioner-termination batches, likely its own story                      | BA                      |
| 6   | Does this apply to **Add Additional Groups** and **Recred** as well as PAR and Off-Cycle? (Mirrors CQ-1 on the companion story.)                                                                                                                                                                                                                                                                                                     | Scope: additional IP versions and regression surface                                                         | BA                      |
| 7   | Legacy M03 rows carry a populated External Id (`{TIN}-{Name}-{NPI}-P-{Address}-{Zip}-{Phone}-M03`) that guided-flow info codes leave blank. Do any downstream consumers (LMS / BCBSA sync) require that key on new records?                                                                                                                                                                                                          | If yes, the key must be composed at creation, adding address and phone lookups                               | Technical / Integration |
| 8   | Is "solo" defined purely by the location's group NPI being Type 1 (the definition used here and in the companion story), or does an organization-NPI group with exactly one practitioner also count as a sole proprietor? **31.8% of all active practice locations (98,048 of 308,567) have a Type 1 group NPI** — high enough that it should be confirmed as genuine sole-proprietor volume rather than partly mis-linked NPI data. | Materially changes the qualifying population and the CQ-4 back-fill size                                     | BA / Product            |


---



## Impact Analysis


| Component                                                                   | Type                  | Impact Level | Description                                                                                                                                  |
| --------------------------------------------------------------------------- | --------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `PRM_CreateHCFRelatedRecordsHelper`                                         | Apex                  | **HIGH**     | Shared by every flow that creates practice-location child records; the new dedupe check changes behaviour for *all* info codes, not just M03 |
| `PRM_CreateRecordsForPCF`                                                   | Integration Procedure | **HIGH**     | New version required; central to PAR and Off-Cycle record creation                                                                           |
| `PRM_InfoCodeAssTriggerHandler` / `PRM_InfoCodeAssTriggerHelper`            | Apex                  | MEDIUM       | Overlap guard and future-dated processing fire on every new assignment; the pre-check must keep the chain from ever reaching `addError`      |
| `PRM_ConciergeProviderRollupQueueable`                                      | Apex                  | MEDIUM       | Enqueued from the info code assignment trigger — additional inserts add async work per submission                                            |
| `PRM_UpdateEffectiveDateBatch`                                              | Apex                  | MEDIUM       | Realigns practice-location `Info_Codes_Assignment__r` effective dates; will now see M03 rows                                                 |
| `PRM_BCBSARecordSyncSubServiceHandler`                                      | Apex                  | MEDIUM       | Syncs non-pending info code assignments outbound — new M03 rows will flow to BCBSA                                                           |
| `PRM_PractitionerActivationExecutor` / `DFX_PractitionerActivationExecutor` | Apex                  | LOW          | No change expected; existing Pending flip activates the new rows                                                                             |
| `PRM_FutureDatedProcessingUtil`                                             | Apex                  | LOW          | Receives a future-dated processing row per new assignment                                                                                    |
| Companion story's `PRMDRExtractSoloPracticeLocationOwner`                   | DataRaptor            | **BLOCKING** | This story reuses it; sequence the companion story first                                                                                     |


---



## Estimated Effort


| Component                                                                       | Change Type                | Effort | Notes                                                                    |
| ------------------------------------------------------------------------------- | -------------------------- | ------ | ------------------------------------------------------------------------ |
| Solo-location + owner resolution                                                | Reuse from companion story | S (1)  | Blocked on the companion story's DataRaptor                              |
| `PRM_CreateHCFRelatedRecordsHelper` — database-level duplicate pre-check        | Apex                       | L (3)  | Bulk-safe; must cover the effective-date overlap semantics in CQ-3       |
| `PRM_CreateHCFRelatedRecordsHelper` — conditional M03 injection                 | Apex                       | XL (5) | Branching per location within a multi-practitioner submission            |
| `PRM_CreateRecordsForPCF` new version                                           | IP                         | L (3)  | Pass-through of the solo flag; regression surface is large               |
| Partial-success insert + failed-record staging                                  | Apex                       | M (2)  | Follows the `PRM_IfcLoader` pattern                                      |
| Apex tests (bulk 200, duplicate, organization NPI, missing NPI, insert failure) | Apex tests                 | L (3)  | ≥ 85% gate                                                               |
| Detection / sizing SOQL for the back-fill question                              | SOQL analysis              | M (2)  | Delivered in `requirements/SOQL/2026-08-19_M03SoleProprietorInfoCode.md` |


**Total Estimated Effort:** 19 story points — **XL** (AI-estimated — validate with team)

> **Sequencing note:** this story shares its solo-practitioner detection with `requirements/PAR_OffCycle_SoloPractitioner_GroupJoin_Restriction_UserStory.md`. Building them in the same sprint avoids implementing the same NPI-type resolution twice; if they are split, the restriction story must land first.

