# USER STORY: Mass Upload — Intake: API Validation (NPPES, Precisely)

**Persona:** PDM Specialist
**Priority:** P1
**GUS Requirement:** #1487020 — *Mass Upload - Intake: API Validation (NPPES, Precisely)* (Active, Dev) · Development Size 8 · Area: IHG\BTS EIM\Provider Network Management\Mass Updates
**OmniScript:** N/A for delivery. **Parity source:** `PRM_PractitionerCreation_English` v27 (Delegated Practitioner) and its address-validation chain
**Integration Procedures:** `PRM_ValidateNPIContainer` (individual NPI + name), `PRM_GetNPIDetails` (organization NPI), `PRM_IPPreciselyAPICall` (address standardization)
**Relevant Requirements:** #1486103 (*Initial Validation* — runs before this), #1487028 (*System Validation* — runs after this), #1490648 (*Add Location / All Location* — consumes the standardized address), `requirements/Address_Validation_Implementation_Plan.md`
**Story boundary:** #1486103 checks a row's **format**. This story checks a row against **external registries** — NPPES for NPI/name truth and Precisely for address truth — and substitutes standardized address values. #1487028 then resolves the row against **org records**.

---

## Story

**As a** PDM Specialist,
**I want** every NPI on an uploaded roster verified against the national registry and every new practice-location address standardized by Precisely before any record is built,
**So that** bulk-created providers and directory addresses meet the same standard as ones entered through the guided flow, instead of publishing unverified NPIs and non-standard addresses to the provider directory.

**Why it matters:** The guided flow validates one practitioner at a time with a specialist watching the result. A delegated roster creates hundreds of providers and locations with no one checking each one, so an unverified NPI or a non-standard address goes straight into the directory and surfaces later as a claims or directory-accuracy defect.

---

## Scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Upload — Delegated Practitioner | CSV upload experience | Initial Validation → **API Validation (NPPES, Precisely)** → System Validation → create-vs-reuse → async creation | NPPES national registry; Precisely address standardization |

**In scope:** individual NPI verification and registry-name comparison; group / practice-location NPI verification and organization-name comparison; registry-outage handling; Precisely standardization of new practice-location addresses with a confidence gate; de-duplication of identical address sets; the existing Precisely bypass.

**Out of scope:** org-record resolution (#1487028); create-vs-reuse and record writes (#1490648); format validation (#1486103); CAQH; re-validating addresses on locations that already exist.

---

## Current State (from codebase)

Every integration piece this story needs already exists — built for the guided flow, one record at a time.

| Component | What it does today | Location |
|---|---|---|
| `NPPES_API` | Named credential for the national registry | `namedCredentials/` |
| `PRM_Precisely_API` | Named credential for address standardization | `namedCredentials/` |
| `PRM_NpiValidationService` | `validatePractitionerNpi(npi, firstName, lastName)` → IP `PRM_ValidateNPIContainer`. Returns `isValid`, `providerName`, `message`. Uses NPI type `NPI-1` | `classes/` |
| `PRM_GroupNpiValidationService` | `validateGroupNpi(groupNpi, groupName)` → IP `PRM_GetNPIDetails`. Returns `npiValid`, `npiType`, `errorMessage` | `classes/` |
| `PRM_PreciselyAddressService` | Direct HTTP POST to `callout:PRM_Precisely_API/address-standardize`, 60s timeout. **Already accepts a List and posts a JSON array** | `classes/` |
| `PRM_AddressValidationService` | Parses the Precisely response including a 0–100 `Confidence` | `classes/` |
| `PRM_SkipPrecisely` | Bypass flag held as a `PRM_Constant__mdt` record | Custom Metadata |

### Three constraints that shape this story

**1. The individual NPI call validates NPI *and* name together.** `PRM_NpiValidationService` returns valid "only when NPPES finds exactly one match for that NPI + name combination", so as built it cannot say whether the NPI was absent or the name disagreed. This story requires two distinct messages, so the lookup must return the registry record (AC-2, AC-3, Clarification Q1).

**2. The guided flow does not block on Precisely, and has no confidence threshold.** Its documented behaviour matrix:

| Condition | Guided flow result |
|---|---|
| `PRM_SkipPrecisely = 'true'` | bypass — no standardization |
| Match returned (confidence > 0) | **modal shown; the specialist accepts or rejects** |
| No match | success, **address saved as entered** |
| Precisely errors / unavailable | error returned |

Mass upload has no specialist at the modal, so **auto-substitution above a confidence threshold, and treating no-match as an error, are deliberate departures** from the flow — justified because a bulk-created directory address gets no human review. Both are called out in the ACs.

**3. Bulk shape differs between the two APIs.** Precisely already takes a list. Both NPPES services issue one Integration Procedure callout per record, against a hard limit of **100 callouts per transaction** — a several-hundred-row roster cannot validate in one transaction. There is also a known trap recorded in `PRM_PreciselyAddressService`: calling the Precisely IP from a transaction holding a savepoint fails with *"All active Savepoints must be released before making callouts."*

> The Precisely request currently sends only `AddressLine1`, `FirmName`, `StateProvince`, `Country`, `PostalCode` and `City` — **Address Line 2 is not sent**, although it is parsed from the response (Clarification Q5).

---

## Acceptance Criteria

> Pattern A (behavioural) unless marked. AC-11 is Pattern E (the substitution field spec); AC-17 and AC-18 are Pattern D (rules). This story creates **no records** — it verifies values and substitutes standardized address components into the payload that #1490648 later writes.

### Individual NPI — national registry

**AC-1 — NPI and name resolve in the registry**

**Given** a practitioner row whose Individual NPI passed the format check,
**When** the registry lookup runs and returns exactly one record whose registered name matches the row's name,
**Then** the NPI is marked verified for that practitioner and the practitioner remains eligible for creation.

**AC-2 — NPI not found blocks the practitioner**

**Given** an Individual NPI for which the registry returns no record,
**When** API validation completes,
**Then** an Error is reported as the row number, Individual NPI, and the message "Please input a valid Individual NPI Number associated with the First & Last Name provided.",
**And** no records are created for that practitioner.

**AC-3 — Registry name mismatch blocks the practitioner**

**Given** an Individual NPI that resolved in the registry, but whose registered name differs from the name in the row,
**When** the name comparison runs on first, middle and last name, case-insensitively,
**Then** an Error is reported showing both the row's name and the registered name, and that practitioner is captured in the fallout,
**And** no records are created for that practitioner.

**AC-4 — No name supplied**

**Given** a practitioner row whose name fields are empty,
**When** the name comparison runs,
**Then** the practitioner is reported as an Error by the required-field rules and captured in the fallout.

**AC-5 — Every row for a blocked practitioner is held together**

**Given** a practitioner whose NPI or name check failed, and who appears on more than one row of the file,
**When** API validation completes,
**Then** every row belonging to that practitioner is held and captured in the fallout,
**And** no row for that practitioner proceeds, even if the other rows are otherwise valid.

### Group and practice-location NPI — national registry

**AC-6 — Group NPI resolves**

**Given** rows carrying a Group or practice-location NPI,
**When** the organization lookup runs for each distinct NPI and returns exactly one record,
**Then** the NPI is marked verified and the group, its locations and addresses remain eligible for creation.

**AC-7 — Group NPI not found blocks the group**

**Given** a Group NPI for which the organization lookup returns no record,
**When** API validation completes,
**Then** an Error is reported as the row number, Group NPI, and the message "Please input a valid Group NPI Number associated with the Group Name provided.", and the affected rows are captured in the fallout.

**AC-8 — Registered organization name mismatch blocks a new group**

**Given** a Group NPI that resolved in the registry but whose registered organization name differs from the Group Name in the row, **and** the row would create a new group,
**When** API validation completes,
**Then** an Error is reported showing both names and the group is held.

**AC-9 — An existing group is not re-blocked by its own registry data**

**Given** a Group NPI and Tax ID that match a vendor account already created by an earlier upload or a guided submission,
**When** API validation runs,
**Then** the group is matched and reused on its existing key,
**And** a registry mismatch against that existing account's stored name does **not** block the new practitioner,
**And** the mismatch is reported as a Warning only.

### Registry availability

**AC-10 — An unreachable registry holds the affected records rather than skipping validation**

**Given** the registry is unreachable for one or more NPIs after the configured retries,
**When** API validation completes,
**Then** those NPIs are marked "not verified",
**And** the practitioners and groups depending on them are held rather than created,
**And** the outage is recorded against the job so the specialist can see validation did not silently pass.

### Address standardization — Precisely

**AC-11 — A confident match replaces the address components** *(Pattern E — values substituted)*

**Given** a row that passed Initial Validation and introduces a **new** practice location whose primary address Precisely matches at or above the confidence threshold,
**When** standardization runs,
**Then** the following components on that address are replaced with the standardized values and the row proceeds to location creation with them:

**Practice-location address — Substitute**

| Component | Value | Notes |
|---|---|---|
| Address Line 1 | {Precisely Address Line 1} | |
| Address Line 2 | {Precisely Address Line 2} | see Clarification Q5 — not currently sent in the request |
| City | {Precisely City} | |
| State | {Precisely State} | |
| ZIP | {Precisely Postal Code} | |
| ZIP+4 | {Precisely Postal Code Extension} | |
| County | {Precisely County} | |
| Confidence | {Precisely Confidence} | retained against the row for audit |

**And** the original file values are retained unchanged in the correction report so the specialist can see what was substituted.

**AC-12 — A low-confidence match blocks the row**

**Given** a row whose address Precisely matches below the confidence threshold,
**When** standardization runs,
**Then** an Error is reported — "Confidence level is less than {threshold}%." — showing the returned confidence,
**And** that row does not proceed to location creation,
**And** no address components are substituted.

**AC-13 — No match blocks the row**

**Given** a row introducing a new practice location whose address Precisely cannot match,
**When** standardization runs,
**Then** an Error is reported stating the address could not be standardized, and that row does not proceed to location creation.

> **Deliberate departure from the guided flow**, which saves an unmatched address as entered. A bulk-created directory address gets no human review, so it must be standardized or held.

**AC-14 — Identical addresses are standardized once**

**Given** a validated set in which mailing or billing is marked same-as-primary, or in which two or more address blocks carry the same Address Line 1, Line 2, City, State, ZIP and ZIP+4,
**When** standardization runs,
**Then** the address is sent for standardization once for that component set,
**And** the returned result is applied to every block that shares it,
**And** the correction report attributes the result to every row that used it.

**AC-15 — Precisely unavailable holds the affected rows**

**Given** Precisely is unreachable or returns a non-success response after the configured retries,
**When** standardization runs,
**Then** an Error is reported — "Address Validation is currently unavailable." — for every row awaiting standardization,
**And** those rows are held rather than created,
**And** the outage is recorded against the job.

**AC-16 — The existing bypass is honoured**

**Given** the Precisely bypass flag is enabled in the environment,
**When** API validation runs,
**Then** address standardization is skipped for every row,
**And** rows proceed with their file-supplied address values,
**And** the job records that standardization was bypassed.

> The bypass exists so lower environments can run without the external service. It does not skip NPI verification.

### Execution rules

**AC-17 — Callout budget and de-duplication** *(Pattern D — rules)*

- **Validate distinct values, not rows.** Registry lookups run once per distinct Individual NPI and once per distinct Group NPI in the file; standardization runs once per distinct address component set (AC-14). A roster that repeats one practitioner across eight locations costs one registry lookup.
- **Stay within the callout ceiling.** No transaction may exceed the platform limit of 100 callouts. Work is chunked so each transaction validates at most a configured number of distinct values, well inside that ceiling.
- **Never hold a savepoint across a callout** — a transaction holding one fails with "All active Savepoints must be released before making callouts."
- **A verified result is reused for the whole file** — the same NPI appearing later in the file is not looked up again.
- **Retries are bounded and configurable**; exhausting them is an outage (AC-10, AC-15), never a silent pass.
- **A held row is never partially created** — verification precedes every record write.

**AC-18 — Confidence threshold configuration** *(Pattern D — rules)*

- The confidence threshold is held in **configuration, not code**, and defaults to **50**.
- A match **at or above** the threshold substitutes (AC-11); **below** it blocks (AC-12).
- The threshold applies to practice-location addresses introduced by the file. It does not apply to addresses on locations that already exist and are being reused.
- The returned confidence is recorded against the row whatever the outcome, so the business can tune the threshold from real results.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CSVApiValidationBatch` | **New** Apex class | Callout-bearing batch over the distinct NPI and address sets; chunked to stay under the callout ceiling | Drives AC-17. Must not hold a savepoint across callouts |
| `PRM_CSVNpiVerificationService` | **New** Apex class | Bulk wrapper over the registry lookups; caches verified NPIs for the file | Drives AC-1 – AC-10 |
| `PRM_CSVAddressStandardizationService` | **New** Apex class | Distinct-address-set standardization with the confidence gate and result fan-out | Drives AC-11 – AC-16 |
| `PRM_NpiValidationService` | Modified Apex class | Return the registry record (registered first / middle / last name) alongside the valid flag, so "not found" and "name mismatch" are distinguishable | Drives AC-2, AC-3 — today it returns only a combined valid flag |
| `PRM_GroupNpiValidationService` | Existing | Organization lookup; reused as-is | Implements AC-6 – AC-8 |
| `PRM_PreciselyAddressService` | Existing | Already list-based and array-posting; reused for the distinct-set call | Implements AC-11, AC-14 |
| `PRM_AddressValidationService` | Existing | Confidence parsing reused | Implements AC-12, AC-18 |
| `PRM_Constant__mdt` | Config | Reuse `PRM_SkipPrecisely`; add a confidence-threshold record and a retry-count record | Drives AC-16, AC-18 |
| `PRM_CSVConversionBatch` | Modified Apex class | Sequence API validation between Initial Validation and System Validation; exclude held rows | Drives AC-5, AC-10, AC-15 |
| `PRM_CSVJobUploadController` / `prmCsvJobUpload` | Modified Apex + LWC | Surface verification findings, substituted-value detail and outage state | Drives AC-11, AC-16, AC-17 |

**Integration Procedures consumed:** `PRM_ValidateNPIContainer` (individual, NPI type `NPI-1`), `PRM_GetNPIDetails` (organization), `PRM_IPPreciselyAPICall` (address). Named credentials `NPPES_API` and `PRM_Precisely_API` already exist.

---

## Definition of done

- [ ] A practitioner whose NPI and name both match the registry is verified and proceeds (AC-1)
- [ ] An unknown NPI and a name mismatch produce **different** error messages (AC-2, AC-3)
- [ ] A practitioner appearing on eight rows costs one registry lookup, not eight (AC-17)
- [ ] When a practitioner is blocked, every row for that practitioner is held, including otherwise-valid ones (AC-5)
- [ ] A registry mismatch against an already-existing group produces a Warning and does not block the new practitioner (AC-9)
- [ ] A registry outage marks NPIs "not verified", holds dependent records, and is visible on the job — never a silent pass (AC-10)
- [ ] A match at or above the threshold substitutes all seven address components, and the original values remain visible in the correction report (AC-11)
- [ ] A match below the threshold blocks the row and substitutes nothing (AC-12)
- [ ] An unmatched address blocks the row rather than saving as entered (AC-13)
- [ ] Same-as-primary and identical address blocks consume one standardization call (AC-14)
- [ ] A Precisely outage holds the affected rows and is recorded on the job (AC-15)
- [ ] With the bypass enabled, standardization is skipped, rows proceed on file values, and NPI verification still runs (AC-16)
- [ ] A 300-row roster completes validation without exceeding the callout limit in any transaction (AC-17)
- [ ] No transaction holds a savepoint across a callout (AC-17)
- [ ] The confidence threshold is changeable in configuration without a deployment (AC-18)
- [ ] ≥ 85% Apex coverage on the new batch and services, with mocked registry and Precisely responses covering success, not-found, mismatch, low-confidence, outage and bypass

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | The individual lookup returns only a combined valid flag. Can `PRM_ValidateNPIContainer` return the registered name, or is a second lookup needed to separate "not found" from "name mismatch"? | Determines whether AC-2 and AC-3 can carry distinct messages | Technical |
| 2 | How should the registry name comparison treat suffixes, credentials and middle-initial-only values (`Lauren Hughes` vs `Lauren Lacey Hughes` occurs in the UPHS roster)? | Decides how often AC-3 fires on legitimate rows | BA / Ops |
| 3 | How many retries, and over what interval, before declaring an outage? | Drives AC-10 and AC-15 | Technical |
| 4 | Should a verified NPI be cached across uploads, or re-verified every file? | Materially changes callout volume for repeat rosters | Product / Technical |
| 5 | Address Line 2 is not sent to Precisely today but is expected to be replaced. Should the request start sending it? | Affects AC-11's Line 2 substitution and the request contract | Technical |
| 6 | Is 50 the right confidence default, and who owns tuning it? | Drives AC-18 | BA / Ops |
| 7 | Should billing and mailing addresses for a **new group** also be standardized, or only the practice-location address? | Expands AC-11's scope to the addresses #1490648 requires for a new group | BA |
| 8 | AC-13 blocks an unmatched address while the guided flow saves it as entered. Confirm the business accepts the stricter bulk rule. | Confirms a deliberate parity departure | Product / BA |
| 9 | Does the registry distinguish an inactive or deactivated NPI from an unknown one, and should they be treated differently? | May add a scenario to AC-2 | BA / Technical |
| 10 | Should NPI verification also run for rows that reuse an **existing** practitioner, or only for new ones? | Changes callout volume and the meaning of AC-5 | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_NpiValidationService` | Apex | **HIGH** | Response contract changes to expose the registered name; the guided flow consumes this service |
| `PRM_CSVConversionBatch` | Apex | **HIGH** | A new callout-bearing stage between Initial and System Validation |
| Callout governor budget | Platform | **HIGH** | 100 per transaction; chunking is the core design constraint |
| `PRM_PreciselyAddressService` | Apex | MEDIUM | Reused unchanged, but now driven from batch rather than LWC context |
| `PRM_Constant__mdt` | Config | MEDIUM | New threshold and retry records alongside `PRM_SkipPrecisely` |
| `prmCsvJobUpload` | LWC | MEDIUM | Must show substituted values and outage state |
| Guided flow NPI validation | OmniStudio / Apex | MEDIUM | Shares `PRM_NpiValidationService`; must not regress |
| #1487028 / #1490648 | Requirements | **HIGH** | Consume this story's verified NPIs and standardized addresses |

---

## Estimated Effort

> AI-estimated — validate with team. GUS records a Development Size of 8.

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_CSVApiValidationBatch` | New Apex | **XL** | Callout chunking, retries, outage handling, savepoint discipline |
| `PRM_CSVNpiVerificationService` | New Apex | **L** | Distinct-value verification with per-file caching |
| `PRM_CSVAddressStandardizationService` | New Apex | **L** | Distinct-set standardization, confidence gate, result fan-out |
| `PRM_NpiValidationService` | Modified Apex | **M** | Expose the registered name without breaking the guided flow |
| `PRM_CSVConversionBatch` | Modified Apex | **M** | Sequence the new stage and exclude held rows |
| `PRM_Constant__mdt` records | Config | **S** | Threshold and retry configuration |
| `PRM_CSVJobUploadController` / `prmCsvJobUpload` | Modified Apex + LWC | **M** | Findings, substituted values, outage state |
| Apex tests with mocked endpoints | New tests | **XL** | Success, not-found, mismatch, low-confidence, outage, bypass, bulk |

**Total Estimated Effort:** ~7–9 engineer-days — **XL** overall, consistent with the recorded size of 8.
