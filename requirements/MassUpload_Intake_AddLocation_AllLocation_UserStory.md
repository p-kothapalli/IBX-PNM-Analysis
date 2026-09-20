# USER STORY: Mass Upload — Intake: Add Location / All Location (Practitioner Creation)

**Persona:** PDM Specialist
**Priority:** P1
**GUS Requirement:** #1490648 — *Mass Upload - Intake: Add Location/All Location* (Proposed) · Area: IHG\BTS EIM\Provider Network Management\Mass Updates
**OmniScript:** N/A for delivery (Mass Upload is an LWC experience). **Parity source:** `PRM_PractitionerCreation_English` v27 — Group step
**Integration Procedures:** N/A
**Relevant Requirements:** #1487028 (*System Validation* — resolution rules this story consumes), #1486103 (*Initial Validation*), `requirements/SOQL/2026-09-15_GroupMatchingTaxIdNpiAmbiguity.md`, `requirements/MassUpload_Intake_RulesValidation_SystemValidation_UserStory.md`
**Grounding:** 34 real delegated rosters in `Downloads/08-17-2026` (UPHS, Penn Medicine, Cooper, Virtua, Summit, Nemours, Princeton, Jefferson, Headway) and live queries against the `deploytarget` QA org, 2026-09-15.
**Story boundary:** #1487028 decides *what a row resolves to* and reports conflicts. **This story decides what to create or reuse from that resolution, and writes the records.**

---

## Story

**As a** PDM Specialist,
**I want** each Practitioner Creation row to reuse the practitioner, group and practice location that already exist and create only what genuinely doesn't — and, when the row says All Location, to affiliate the practitioner to every active location of the group instead of touching a single one,
**So that** a hospital roster onboards the right people at the right offices without duplicating practitioners, groups or locations, and without re-keying credentials that already exist.

**Why it matters:** Delegated rosters re-state practitioners and groups the org already holds — in the UPHS June file every row shares one Tax ID and repeats the same practitioners across locations. Without explicit create-vs-reuse rules, each upload multiplies vendor accounts and practice locations, and large systems ask for a practitioner to be added at every office of a group, which is currently a manual row-per-location exercise.

---

## Scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Upload — Practitioner Creation | CSV upload experience | System Validation → **Create-vs-Reuse decision** → JSON generation → async creation | Resolved practitioner / group / location from #1487028 |

**In scope:** the create-vs-reuse decision for practitioner, group and location; the All Location behaviour; conditional address requirements; credential handling for an existing practitioner; ingest value normalization; the new template columns this needs.

**Out of scope:** the resolution and conflict rules themselves (#1487028); per-row `Type of Request` routing (see Clarification Q7); field-level format validation (#1486103); terminations.

---

## Current State (from codebase, files and org)

### Already built

| Component | Relevance |
|---|---|
| `PRM_CSVStandardTemplate` | Already carries an optional **`addToAllLocations` — "Add to all group locations"** field in the Group & Location section. The All Location concept exists in the pipeline; no roster file supplies it yet. |
| `PRM_HPFService` (E14) | Creates the practitioner-to-location affiliation with PPA / PLA record types — the write AC-11 fans out |
| `PRM_HealthcareFacilityCreationService` (E13) | Creates the location NPI, Location and Address records for a new practice location |
| `PRM_GroupService` (E3) | Creates the vendor Account, EIN Identifier and group provider record for a new group |
| `PRM_PractitionerCreationHelper` | Parity source for Tax ID → NPI → location resolution |

### Evidence from the 34 delegated rosters

| Finding | Detail | Consequence |
|---|---|---|
| PIE columns exist but are named inconsistently | 26 of 34 files, **nine spellings**: `Provider PIE ID`, `Practitioner PIE`, `Practitoiner PIE` *(typo in the Virtua file)*, `PIE ID`, `Vendor PIE Location`, `Vendor PIE`, `Location PIE ID`, `Practice Location PIE`, `Location PIE` | The column-mapping experience must absorb the variance; header typos are real |
| 8 of 34 files carry **no** PIE column | Cooper 09/2025, Minute Clinic, Princeton Terminations, Jefferson, Summit 2024 | PIE Id must be optional; NPI/TIN is the fallback path |
| Group-level PIE is rare | Only Penn Medicine (`Vendor PIE Location`) and Virtua (`Vendor PIE`) | Group reuse will usually run on Group NPI + TIN |
| **No file has an All Location column** | Zero of 34 | AC-17 adds it; it is new to the business's files |
| Numeric coercion | `Provider PIE ID = 10000043652.0`, `Provider NPI = 1063972552.0` — and the *same column* also holds `1063972552` | A 10-digit NPI check fails on the `.0` form |
| Tax ID formatting | `Vendor TIN = 23-2743545` | Fails the 9-digit rule in #1486103 AC-2 |
| ZIP+4 | `Address Zip = 19104-4206` | Breaks an exact ZIP match against a 5-digit stored value |
| One practitioner, many locations | Provider PIE `10000043652` appears on consecutive rows with Location PIE `30000139654` and `30000136421` | The normal shape, not a duplicate |

### Live QA org tests (row 1 of *UPHS Provider.June.Changes_2026_Part 1*)

| Test | Input | Result |
|---|---|---|
| Practitioner by NPI | `1063972552` | **Exactly one** — `Lauren Lacey Hughes`. The file says "Lauren Hughes"; the middle name differs, confirming NPI (not name) as the practitioner key |
| Group by TIN + Vendor NPI | `232743545` + `1053447151` | **Five groups**, not one — `Penn Hospital Medicine Penn Presbyterian`, `… Penn Presbyterian - PMG`, `… HUP`, `University of PA Medical Group`, `Penncare IM Science Center` |
| PIE Id storage | Provider PIE `10000043652`, Location PIE `30000139654` | **No match anywhere.** No `PIE` Identifier type exists (types are BSPA, EIN, HRLO, Document, HR, CAQH, MCRE, MAID); no match on `SourceSystemIdentifier` or `PRM_ExternalId__c`. The only PIE fields in the org are feature flags |

**Two consequences drive this story:**

1. **"Group NPI and TIN match exactly one vendor" does not hold.** A real row returns five candidates, one of which (`… Penn Presbyterian - PMG`) is a near-twin of the file's Vendor Name. Group reuse therefore resolves through #1487028's reconciliation rather than assuming a single match.
2. **PIE Id has no storage in Salesforce.** It is the primary key in the AC set below, so PIE-based reuse is specified but **gated on a prerequisite** (AC-16) rather than assumed available.

---

## Acceptance Criteria

> Pattern A (behavioural) unless marked. AC-7, AC-10 and AC-14 are Pattern E (record & field specification); AC-15 and AC-16 are Pattern D (rules); AC-17 is Pattern B (columns). Business labels are used throughout; the API mapping is in Technical Implementation.

### Practitioner — create or reuse

**AC-1 — Existing practitioner is reused**

**Given** a row whose Provider PIE Id, or whose Provider NPI, matches exactly one existing practitioner,
**When** the create-vs-reuse decision runs,
**Then** that practitioner is reused,
**And** no second practitioner record is created,
**And** the practitioner's name in the file does not overwrite the stored name.

**AC-2 — New practitioner is created**

**Given** a row whose Provider PIE Id and Provider NPI match no existing practitioner,
**When** the create-vs-reuse decision runs,
**Then** a new delegated practitioner is prepared from the row's practitioner columns.

**AC-3 — Credentials for an existing practitioner are added, never modified**

**Given** a row that reused an existing practitioner, and whose licence, education, board-certification or training columns are populated,
**When** the create-vs-reuse decision runs,
**Then** only credentials the practitioner does not already hold are added,
**And** credentials the practitioner already holds are left exactly as they are,
**And** no credential is updated or deactivated from the file.

### Group — create or reuse

**AC-4 — Existing group is reused**

**Given** a row whose Group PIE Id matches exactly one existing group, or whose Group NPI and Tax ID together resolve to exactly one eligible group, or whose Group NPI and Tax ID resolve to several groups of which **exactly one** matches the row's Group Name exactly after normalization,
**When** the create-vs-reuse decision runs,
**Then** that group is reused and no second vendor account is created,
**And** the Group Name in the file does not overwrite the stored group name.

> Grounded: TIN `23-2743545` with Vendor NPI `1053447151` returns five Penn groups in the QA org — `Penn Hospital Medicine Penn Presbyterian`, `… Penn Presbyterian - PMG`, `… HUP`, `University of PA Medical Group`, `Penncare IM Science Center`. The row's Group Name `Penn Hospital Medicine Penn Presbyterian` matches exactly one of them byte-for-byte, so the row reuses that group without stopping for reconciliation.

**AC-5 — Group NPI and Tax ID resolve several groups with no single exact name match**

**Given** a row whose Group NPI and Tax ID resolve to more than one eligible group, whose Group PIE Id is blank or unmatched, and where **zero or more than one** candidate matches the row's Group Name exactly after normalization,
**When** the create-vs-reuse decision runs,
**Then** the row is held for group reconciliation with every candidate presented,
**And** no group is created and none is chosen automatically.

> Similarity scoring never resolves a group. On the five Penn candidates above, a 0.5 similarity threshold returns three — including `Penn Hospital Medicine HUP` at 0.60, a different hospital. Only the exact-after-normalization tier may auto-resolve.

**AC-6 — A new group requires Primary, Billing and Mailing addresses**

**Given** a row whose Group PIE Id, Group NPI and Tax ID resolve to no existing group,
**When** the create-vs-reuse decision runs,
**Then** the Primary, Billing and Mailing address columns become required on that row,
**And** if any of them is blank an Error is reported naming the missing address and that row does not proceed,
**And** when all are present a new group is prepared.

**AC-7 — Records created for a new group** *(Pattern E)*

**Given** a row that resolved to no existing group and supplied all three addresses,
**When** the records are built,
**Then** the following records are created exactly as specified:

**Group (Vendor Account) — Create**

| Field | Value | Notes |
|---|---|---|
| Record Type | Vendor | |
| Name | {Group Name} | from the file |
| Vendor Account Type | Medical Service Vendor | default unless the row supplies one |
| Source System Id | {Tax ID}-{Group Name} | external id for idempotent upsert |
| Source System Identifier | {Tax ID}-{Group Name} | same composite; consumed by the location external id |

**Group Tax Identifier — Create**

| Field | Value | Notes |
|---|---|---|
| Record Type | Vendor Identifier | |
| Type | EIN | |
| Id Value | {Tax ID} | digits only, per AC-15 |
| Parent Record | {Group Vendor Account} | |
| Active | TRUE | |

**Group Provider Record — Create**

| Field | Value | Notes |
|---|---|---|
| Record Key | {Tax ID}-{Group Name} | idempotent upsert key |
| Account | {Group Vendor Account} | |

### Practice location — create or reuse

**AC-8 — Existing location is reused and its address is preserved**

**Given** a row that is not All Location, whose Practice Location PIE Id matches exactly one location on the resolved group, or whose Group NPI, Tax ID and standardized address match exactly one location on the resolved group,
**When** the create-vs-reuse decision runs,
**Then** that location is reused and the practitioner is affiliated to it,
**And** the location's stored address is **not** overwritten from the file.

**AC-9 — A new location requires the Address columns**

**Given** a row that is not All Location, and whose location keys match no existing practice location on the resolved group,
**When** the create-vs-reuse decision runs,
**Then** the Address columns become required on that row,
**And** if any required address column is blank an Error is reported and that row does not proceed,
**And** when they are present a new practice location is prepared and the practitioner is affiliated to it.

**AC-10 — Records created for a new practice location** *(Pattern E)*

**Given** a row that resolved to no existing location and supplied the Address columns,
**When** the records are built,
**Then** the following records are created exactly as specified, in this order:

**Location NPI — Create**

| Field | Value | Notes |
|---|---|---|
| Name | {Location NPI} | |
| NPI | {Location NPI} | digits only, per AC-15 |
| NPI Type | Organization | |
| Account | {Resolved Group} | |
| Effective From | {Effective Date} | from the file |
| Effective To | {Effective To} | blank unless supplied |
| Active | TRUE when Effective From is today or earlier and Effective To is blank or future | |
| Case Manager | {Row's Case Manager} | correlation |

**Location — Create**

| Field | Value | Notes |
|---|---|---|
| Name | {Location Name} | falls back to the practice name |
| Location Type | {Location Type} | |
| Telehealth Only | FALSE unless the row says otherwise | |
| Effective From | {Effective Date} | |
| Effective To | {Effective To} | |
| Pending | FALSE | |
| Active | per the same effective-date rule as the Location NPI | |
| Case Manager | {Row's Case Manager} | |

**Address — Create**

| Field | Value | Notes |
|---|---|---|
| Parent | {Location} | |
| Location Type | {Location Type} | |
| Address Line 1 | {Address Line 1} | |
| Address Line 2 | {Address Line 2} | blank when not supplied |
| City | {Address City} | |
| State | {Address State} | |
| ZIP | {Address Zip} | first five digits, per AC-15 |
| County | {County} | blank when not supplied |
| Phone | {Phone} | digits only |
| Phone Extension | {Phone Extension} | digits only, blank when not supplied |

**Practice Location — Create**

| Field | Value | Notes |
|---|---|---|
| Account | {Resolved Group} | |
| Location | {Location} | |
| NPI | {Location NPI} | |
| Practice Classification | {Practice Classification} | drives eligibility on later matches |
| Active | TRUE | |
| Case Manager | {Row's Case Manager} | |

### All Location

**AC-11 — All Location adds the practitioner to every active location**

**Given** a row whose All Location column is TRUE or YES,
**When** the create-vs-reuse decision runs,
**Then** the practitioner is affiliated to every active practice location already on the resolved group,
**And** no location is created or updated from that row's address,
**And** the Address columns are not required on that row.

**AC-12 — All Location requires an existing group with at least one active location**

**Given** a row whose All Location column is TRUE or YES, and whose group either does not exist or has no active practice location,
**When** the create-vs-reuse decision runs,
**Then** an Error is reported stating that All Location requires an existing group with at least one active location, and that row does not proceed.

**AC-13 — All Location and a location reference on the same row**

**Given** a row whose All Location column is TRUE or YES and which also supplies a Practice Location PIE Id or address,
**When** the create-vs-reuse decision runs,
**Then** the practitioner is still affiliated to every active location of the group,
**And** a Warning is reported stating that the row's location details were ignored because All Location was set.

**AC-14 — Records created for each affiliation** *(Pattern E)*

**Given** a practitioner being affiliated to a practice location — whether from a single-location row (AC-8, AC-9) or from each active location under All Location (AC-11),
**When** the records are built,
**Then** one affiliation record is created per practitioner and location exactly as specified:

**Practitioner Location Affiliation — Create (one per practitioner × location)**

| Field | Value | Notes |
|---|---|---|
| Record Type | Practice Location Affiliation | Practitioner Practice Affiliation when there is no location |
| Practitioner | {Resolved or new practitioner} | |
| Group | {Resolved group} | |
| Practice Location | {Resolved or new location} | blank for a practice-level affiliation |
| Group Provider Record | {Group provider record} | blank for a practice-level affiliation |
| Name | {Practitioner name} – {Location or practice name} | composed |
| Primary Location | TRUE only when the row marks it primary; FALSE for every All Location affiliation | |
| Active | TRUE when the effective dates make it current | |
| Pending | FALSE | |
| Effective From | {Effective Date} | |
| Effective To | {Effective To} | blank unless supplied |
| Attestation Date | {TODAY} | |
| Case Manager | {Row's Case Manager} | |

> **All Location never marks a primary location.** A roster that adds a practitioner to every office of a group is not asserting which one is primary.

### Value handling and prerequisites

**AC-15 — Ingest value normalization** *(Pattern D — rules)*

Real rosters arrive from Excel with formatting the org does not store. Normalize on ingest, before any matching or validation.

- **Identifier and NPI columns** — strip a trailing `.0` produced by spreadsheet numeric coercion, so `1063972552.0` and `1063972552` are the same value. The same column may hold both forms in one file.
- **Tax ID** — strip every non-digit before matching and storing, so `23-2743545` becomes `232743545`.
- **NPI columns** — strip every non-digit, then apply the 10-digit rule.
- **ZIP** — match on the first five digits, so `19104-4206` matches a stored `19104`. Store the value as supplied.
- **Phone and extension** — digits only.
- **All text match keys** — trim and collapse internal whitespace.
- **Normalization never rewrites the source file**; the correction report always cites the original value and the file's row number.

**AC-16 — PIE Id matching is gated on a stored PIE identifier** *(Pattern D — prerequisite)*

- PIE Id is the **primary** reuse key for practitioner, group and location wherever it is supplied (AC-1, AC-4, AC-8).
- **There is no PIE identifier stored in the org today** — no PIE identifier type exists, and sample Provider and Location PIE Ids from the UPHS roster match no existing record.
- Until a PIE identifier is stored and backfilled, **PIE-based reuse cannot run**, and reuse falls back to Provider NPI (AC-1), Group NPI + Tax ID (AC-4), and Group NPI + Tax ID + standardized address (AC-8).
- A supplied PIE Id that cannot be looked up **must not** be treated as "no match" — that would silently create duplicates. It is reported as a Warning stating PIE matching is unavailable, and the fallback key decides.
- Storing and backfilling the PIE identifier is a **prerequisite dependency**, not part of this story (Clarification Q1).

**AC-17 — New template columns** *(Pattern B — field/metadata)*

- **All Location** — Group & Location section; optional; accepted values TRUE / YES / FALSE / NO / blank, case-insensitive; blank is treated as FALSE. Maps to the pipeline's existing "Add to all group locations" field.
- **Provider PIE Id** — Practitioner section; optional; free text.
- **Group PIE Id** — Group & Location section; optional; free text.
- **Practice Location PIE Id** — Group & Location section; optional; free text.
- **Mailing address columns** — already present and optional; become conditionally required for a new group (AC-6).
- All four new columns appear in the downloadable sample template, the column-mapping experience and the correction report field list.
- The mapping experience must tolerate the nine observed source spellings and header typos; mapping is per hospital and saved.
- Previously saved column mappings must continue to load with the new columns unmapped.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CSVCreateOrReuseResolver` | **New** Apex class | Turns #1487028's resolution into a per-row create-vs-reuse decision for practitioner, group and location | Drives AC-1 – AC-9 |
| `PRM_CSVAllLocationExpander` | **New** Apex class | Expands an All Location row into one affiliation per active location on the group | Drives AC-11 – AC-13 |
| `PRM_CSVValueNormalizer` | **New** Apex class | Trailing `.0` strip, digits-only for TIN/NPI/phone, ZIP-5 match key, whitespace collapse | Drives AC-15. Applied before validation and matching |
| `PRM_CSVStandardTemplate` | Modified Apex class | Add `allLocation`, `providerPieId`, `groupPieId`, `locationPieId`; `addToAllLocations` already exists and should be reconciled with `allLocation` rather than duplicated | Drives AC-17. **Adding fields shifts 0-based positions — re-sync `COL_*` in `PRM_CSVPractitionerCreationMapper`** |
| `PRM_CSVRowValidator` | Modified Apex class | Conditional requirement sets: three addresses when the group is new (AC-6), address columns when the location is new (AC-9), neither when All Location is set (AC-11) | Conditional-block mechanism already exists in this class |
| `PRM_CSVPractitionerCreationMapper` | Modified Apex class | Emit reuse decisions (existing Ids vs new), the All Location fan-out, and suppress licence/education for a reused practitioner | Drives AC-1 – AC-3, AC-11 |
| `PRM_HPFService` | Existing (E14) | Consumes the affiliation list; `IsPrimaryFacility` false for All Location | Implements AC-14 |
| `PRM_HealthcareFacilityCreationService` | Existing (E13) | Builds Location NPI, Location, Address and Practice Location for a new location | Implements AC-10 |
| `PRM_GroupService` | Existing (E3) | Builds vendor Account, EIN Identifier and group provider record | Implements AC-7 |
| `prmCsvColumnMapper` | Modified LWC | Surface the four new columns; absorb the nine observed source spellings | Drives AC-17 |
| PIE identifier storage | **Prerequisite** | A stored, backfilled PIE identifier on practitioner, group and location | Blocks AC-16's primary path |

**API mapping for the Pattern E blocks:**

| Business label | API |
|---|---|
| Group (Vendor Account) | `Account`, record type `PRM_Vendor`, `HealthCloudGA__SourceSystemId__c`, `SourceSystemIdentifier` |
| Group Tax Identifier | `Identifier` — `PRM_Type__c = 'EIN'`, `IdValue`, `ParentRecordId`, `PRM_Active__c` |
| Group Provider Record | `HealthcareProvider` — `PRM_RecordKey__c` |
| Location NPI | `HealthcareProviderNpi` — `Name`, `Npi`, `NpiType`, `AccountId`, `EffectiveFrom`, `EffectiveTo`, `IsActive`, `PRM_CaseManager__c` |
| Location | `Location` — `Name`, `LocationType`, `PRM_TelehealthOnly__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`, `PRM_Pending__c`, `PRM_Active__c`, `PRM_CaseManager__c` |
| Address | `Schema.Address` — `ParentId`, `LocationType`, `PRM_City__c`, `PRM_State__c`, `PRM_Zip__c`, `PRM_County__c`, `PRM_Phone__c`, `PRM_PhoneExtension__c` |
| Practice Location | `HealthcareFacility` — `AccountId`, `LocationId`, `PRM_NpiId__c`, `PRM_PracticeClassification__c`, `PRM_Active__c` |
| Practitioner Location Affiliation | `HealthcarePractitionerFacility` — `RecordTypeId` (PLA / PPA), `PractitionerId`, `AccountId`, `HealthcareFacilityId`, `HealthcareProviderId`, `Name`, `IsPrimaryFacility`, `IsActive`, `PRM_Pending__c`, `EffectiveFrom`, `EffectiveTo`, `PRM_AttestationDate__c`, `PRM_CaseManager__c` |

> `HealthcareFacility.PRM_ExternalId__c` is populated by an existing trigger helper from the account identifier, NPI, classification and address. This story must not construct or match on it — it goes stale after an address change (`PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`).

---

## Definition of done

- [ ] A row whose Provider NPI matches an existing practitioner reuses that practitioner and creates no second person account (AC-1)
- [ ] `1063972552.0` and `1063972552` resolve to the same practitioner (AC-15)
- [ ] `23-2743545` matches a stored Tax ID of `232743545` (AC-15)
- [ ] `19104-4206` matches a stored ZIP of `19104` (AC-15)
- [ ] A reused practitioner gains only credentials they did not already hold; existing credentials are untouched (AC-3)
- [ ] TIN `232743545` with Vendor NPI `1053447151` is held for reconciliation with all five Penn groups listed, and creates nothing (AC-5)
- [ ] A new group is blocked when any of Primary, Billing or Mailing address is missing, and creates all three records when present (AC-6, AC-7)
- [ ] An existing location is reused and its stored address is unchanged after the upload (AC-8)
- [ ] A new location creates the Location NPI, Location, Address and Practice Location records with every field in AC-10
- [ ] An All Location row affiliates the practitioner to every active location of the group and creates no location (AC-11)
- [ ] No All Location affiliation is marked as the primary location (AC-14)
- [ ] An All Location row for a group with no active location errors and does not proceed (AC-12)
- [ ] An All Location row that also supplies location details proceeds with a Warning (AC-13)
- [ ] A supplied PIE Id that cannot be looked up produces a Warning and falls back, never a silent create (AC-16)
- [ ] The four new columns appear in the sample template and mapping experience, all nine observed source spellings map successfully, and saved mappings still load (AC-17)
- [ ] Re-synced `COL_*` positions verified after the template change
- [ ] A 200-row UPHS-shaped file processes within governor limits with one bulk DML per object type
- [ ] ≥ 85% Apex coverage on the new resolver, expander and normalizer, including bulk, single, empty and negative paths

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Where will PIE Ids be stored and who backfills them?** No PIE identifier type or field exists, and sample PIE Ids match nothing in QA. | Blocks the primary reuse key in AC-1, AC-4 and AC-8; until resolved all reuse runs on NPI/TIN | Technical / Data |
| 2 | Is PIE data present in Production even though it is absent from QA? | Decides whether AC-16's gate is temporary or structural | Technical |
| 3 | No roster carries an All Location column. Will hospitals add it, or should it be set per upload in the UI? | Determines whether AC-17's column is ever populated in practice | Product / BA |
| 4 | The template already has `addToAllLocations`. Should the new All Location column reuse that field or replace it? | Avoids two competing columns meaning the same thing | Technical |
| 5 | For All Location, does "every active location" mean every active location, or only delegated ones (the guided flow narrows to delegated)? | Changes the fan-out size materially for large groups | BA / Ops |
| 6 | Should an All Location row reuse an existing affiliation if the practitioner is already at some of the group's locations? | Decides whether AC-11 is additive-only or reconciling | BA |
| 7 | The UPHS files carry a per-row `Type of Request` (e.g. "Add Provider to a Current Location"). Should it drive behaviour in a later story? | Scope of a follow-on story | Product / BA |
| 8 | What is the effective date for an All Location affiliation when the group's locations have different start dates? | Determines the Effective From in AC-14 | BA |
| 9 | Practitioner name in the file differs from the stored name (`Lauren Hughes` vs `Lauren Lacey Hughes`). Confirm the stored name always wins. | Confirms AC-1's no-overwrite rule | BA |
| 10 | Should a reused group or location whose stored record is inactive be reactivated, or treated as no match? | Adds scenarios to AC-4 and AC-8 | BA / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CSVStandardTemplate` | Apex | **HIGH** | Four new columns shift positional indexes used by the remapper, validator and mapper |
| `PRM_CSVPractitionerCreationMapper` | Apex | **HIGH** | `COL_*` re-sync, plus reuse decisions and All Location fan-out in the generated JSON |
| `PRM_CSVRowValidator` | Apex | **MEDIUM** | New conditional requirement sets driven by the create-vs-reuse outcome |
| `PRM_HPFService` | Apex | **MEDIUM** | Receives many more affiliations per row under All Location |
| `prmCsvColumnMapper` | LWC | MEDIUM | Four new columns and wide source-header variance |
| `PRM_HealthcareFacilityCreationService` / `PRM_GroupService` | Apex | LOW | Consumers of the decision; unchanged logic |
| PIE identifier storage | Data model | **BLOCKING** | Prerequisite for the primary reuse key |
| #1487028 System Validation | Requirement | **HIGH** | This story consumes its resolution output; the two must stay aligned |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_CSVCreateOrReuseResolver` | New Apex | **XL** | Three-entity create-vs-reuse with conditional requirements |
| `PRM_CSVAllLocationExpander` | New Apex | **L** | Fan-out plus the no-primary and error rules |
| `PRM_CSVValueNormalizer` | New Apex | **M** | Small but touches every match key |
| `PRM_CSVStandardTemplate` + `COL_*` re-sync | Modified Apex | **L** | Low code volume, high regression risk |
| `PRM_CSVRowValidator` | Modified Apex | **L** | Conditional requirement sets |
| `PRM_CSVPractitionerCreationMapper` | Modified Apex | **L** | Reuse decisions, fan-out, credential suppression |
| `prmCsvColumnMapper` | Modified LWC | **M** | Four new columns |
| Apex tests (≥ 85%, bulk + negative) | New tests | **XL** | 17 ACs including three Pattern E record specs |
| Verification against the real rosters | Test / analysis | **L** | Replay UPHS, Penn Medicine and Cooper files end to end |

**Total Estimated Effort:** ~9–12 engineer-days — **XXL** overall. **Excludes the PIE identifier prerequisite**, which must be sized separately.
