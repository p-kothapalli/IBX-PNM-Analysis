# USER STORY: Mass Upload — Intake: Rules Validation — System Validation (Delegated Practitioner)

**Persona:** PDM Specialist
**Priority:** P1
**GUS Requirement:** #1487028 — *Mass Upload - Intake: Rules Validation - System Validation* (Proposed)
**OmniScript:** N/A for delivery (Mass Upload is an LWC experience). **Parity source:** `PRM_PractitionerCreation_English` v27 — Group step
**Integration Procedures:** N/A for delivery. **Parity source:** `PRM_DuplicateAddCheck` (address duplicate chain)
**Relevant Requirements:** #1486103 (*Initial Validation — Delegated Practitioner — Group*, Active), #1482230 (source of the relocated NPI/credentialing AC), `requirements/SOQL/2026-09-15_GroupMatchingTaxIdNpiAmbiguity.md` (org evidence), `requirements/PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md` (why the external ID must not be used), `requirements/UPHS_MASS_LOAD_SOLUTIONS.md`
**Sibling story boundary:** #1486103 validates a row **against itself** (required fields, formats, specialty resolution). This story validates a row **against the org** (does this NPI, group, or location already exist, and what does it resolve to).

---

## Story

**As a** PDM Specialist,
**I want** each uploaded row resolved against existing practitioner, group, and practice-location records using the same matching the Practitioner Creation flow already uses, with any ambiguous group confirmed by me once,
**So that** I can correct genuine conflicts up front and let the clean rows process, instead of discovering duplicate or mis-linked provider data after the load has run.

**Why it matters:** A delegated-roster file routinely carries hundreds of practitioners across dozens of locations. Without an org-aware gate, a single re-used NPI or a mistyped group name silently creates duplicate groups and orphaned locations that take days of manual data repair — and corrupts the provider directory in the meantime.

---

## Scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Upload — Delegated Practitioner | CSV upload experience | Initial Validation → **System Validation → Group Reconciliation** → JSON generation → async creation | Existing practitioner, group and practice-location records in the org |

**Request type in scope:** Delegated Practitioner (creates or updates Practitioner, Groups and Practice Locations).

**In scope:** org-lookup validation for Practitioner, Group and Practice Location using the guided flow's Tax ID → NPI → address resolution order; the per-group reconciliation step; cross-row duplicate detection; the Error/Warning severity model; partial processing with a correction report.

**Out of scope:** field-level format validation (#1486103); the record-creation recipe once rows are accepted; other request types; external registry (NPPES) verification; remediation of stale practice-location external IDs (tracked separately).

---

## Current State (from codebase and org)

**System Validation does not exist today — this story specifies a net-new layer.** The upload pipeline performs no org lookups for provider data; its only queries are the specialty master and the job list.

### How the Practitioner Creation flow resolves a group today (the parity source)

Group step of `PRM_PractitionerCreation_English` v27 → Remote Action `PRM_PractitionerCreationUtility.getGroupData` → `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId(npi, taxId)`, which runs **two queries in a deliberate order**:

| Step | Method | Logic |
|---|---|---|
| 1. Tax ID scopes first | `getAccountForIdentifier(taxId)` | `Identifier` where `IdValue = taxId`, `PRM_Type__c = 'EIN'`, `PRM_Active__c = true`, `PRM_IDEffectiveToday__c = true`, `ParentRecordId != null` → candidate accounts |
| 2. NPI filters within that scope | `getAccountForNPI(npi, accounts)` | `HealthcareFacility` where `AccountId IN` candidates, `PRM_Active__c = true`, `PRM_NpiId__r.Npi = npi`, `RecordType.DeveloperName != 'PRM_NCPDP'`, and `(Professional AND BillingType != 'UB') OR (Facility AND BillingType = '1500')`. Results collected into a **Map keyed by AccountId** → unique accounts |
| 3. Human disambiguates | `MultipleGroupNPIS` + `GroupTypeAhead` | When more than one account returns, the specialist picks |
| 4. Locations last | `getPracticeLocation(accountId, npi)` → `getlocVsFac` → `checkDelegatedPracLoc` → `getAddressData` | Locations for that account **and** NPI, narrowed to delegated, presented with addresses for selection |

**The ordering is the whole design.** Tax ID narrows, NPI filters, the account-keyed Map dedupes, and only then are locations fetched. The specialist is the tie-breaker.

### How the flow matches an address

Creation-time duplicate detection runs `PRM_DuplicateAddCheck`: `PRMDRTransformAddData` normalizes the input address → `PRMDRGetHcfIdByAcc` scopes to the account's active locations → `PRMDRGetAddressDataForDupCheck` matches `Address` on **Line1 =, City =, Zip =, County LIKE, `PRM_Active__c` = true, `PRM_AddressType__c` INCLUDES Primary/Practice, `ParentId` IN the account's location Ids**. Field-level and scoped — it does **not** match on the external ID.

### Why the practice-location external ID must not be used

`PRM_HCFacilityTriggerHelper.populatePRMExternalId` builds `HealthcareFacility.PRM_ExternalId__c` as:

```
{Account.SourceSystemIdentifier}-{PRM_NpiId__c}-{PRM_PracticeClassification__c}-{AddressLine1}-{AddressLine2}-{Zip}-{Phone}
```

with `SourceSystemIdentifier` itself being `{taxId}-{groupName}` — eight concatenated, individually fat-fingerable components. It is generated once at creation and **never regenerated when the address changes**, which already causes production duplicate-blocks (`PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`). This story never constructs, compares, or keys on it.

### Existing pipeline components

| Component | Current behaviour | Location |
|---|---|---|
| Row validator | Required fields, conditional blocks, Individual/Location NPI = 10 digits, CAQH = 8 digits, email shape, specialty resolvable. **No org lookups.** No Tax ID format check. | `PRM_CSVRowValidator.cls` |
| Standard template | Group & Location = Group Name (opt), Group Tax ID (req), Location Name (opt), Location NPI (req). **No Group NPI.** Primary Address section already carries Address Line 1 (req), Line 2 (opt), City (req), State (req), ZIP (req), Phone (opt). | `PRM_CSVStandardTemplate.cls` |
| Failure handling | Built so intake **blocks the whole file** until every row is valid | `PRM_CSVRowValidator` header |
| Group identity (async path) | Keyed on **Tax ID + Group Name** — batch dedupes `{taxId}-{groupName}`, service upserts `Account.HealthCloudGA__SourceSystemId__c` to the same composite, so a mistyped name silently creates a new group | `PRM_GroupService.cls`, `PRM_PracticeLocationAndGroupBatch.cls` |

### Org evidence (QA org, 2026-09-15 — see the SOQL archive)

| Measure | Result | Consequence |
|---|---|---|
| Vendor accounts under one Tax ID (`361924025`, Walgreens) | 233 | Tax ID alone cannot resolve a group |
| Name variants under that Tax ID | `WALGREEN CO` vs `WALGREEN CO.`; `WALGREENS #02771` vs `#03000` | Typo duplicates and real stores are lexically adjacent |
| Active facilities carrying an NPI | **390,864 across 318,661 accounts** | Group NPI (read off the location) is a viable predicate |
| Facilities / distinct NPIs / accounts under the Walgreens Tax ID | 263 / 263 / 233 | Tax ID + NPI is highly selective |
| Widest single NPI | **966 active locations across 12 accounts**; another spans 138 accounts | **NPI must never be the first predicate** |

> **Correction to an earlier analysis in this story's history:** group-NPI coverage was first measured on `HealthcareProviderNpi.AccountId` and reported as 1.8%, which wrongly ruled Group NPI out. The guided flow reads the NPI off the **practice location** (`HealthcareFacility.PRM_NpiId__r.Npi`), where coverage is effectively universal. The ACs below use the flow's relationship.

**Three gaps this story must close:** no Tax ID format check despite #1486103 AC-2 requiring 9 digits; no Group NPI column; whole-file blocking contradicts partial processing.

---

## Acceptance Criteria

> Pattern A (behavioural, business language) unless marked. AC-8, AC-17, AC-29 and AC-31 are Pattern D (rules); AC-30 is Pattern B (new column). System Validation is a **read-only gate** — it resolves and tags rows but creates and updates no provider records, so no Pattern E record spec applies.

### Practitioner-level system validation

**AC-1 — Individual NPI is new to the org**

**Given** a row whose Individual NPI does not match any existing practitioner,
**When** Practitioner system validation runs,
**Then** the row is marked as a new practitioner and proceeds to processing.

**AC-2 — Individual NPI already belongs to a practitioner (not in credentialing)**

**Given** a row whose Individual NPI matches exactly one existing practitioner who has no credentialing in flight,
**When** Practitioner system validation runs,
**Then** the row resolves to that existing practitioner and is marked as an update,
**And** the new group and location affiliations from the file are added to the existing practitioner rather than creating a second practitioner record.

**AC-3 — Individual NPI belongs to a practitioner who is mid-credentialing** *(relocated from #1482230 AC-5)*

**Given** a row whose Individual NPI matches a practitioner with credentialing already in flight,
**When** Practitioner system validation runs,
**Then** the row is **allowed to proceed** as a Delegated Practitioner update,
**And** a Warning is reported naming the existing Case Manager,
**And** the row is **not** diverted to the PDM Manual Updates path.

> **Change of behaviour:** the individual-record flow errors and redirects to PDM Manual Updates here. Mass Upload deliberately does not, because a delegated roster legitimately re-states practitioners already in credentialing.

**AC-4 — Individual NPI matches more than one practitioner**

**Given** a row whose Individual NPI matches more than one existing practitioner record,
**When** Practitioner system validation runs,
**Then** an Error is reported listing the matched practitioners, and that row does not proceed to processing,
**And** no match is chosen automatically.

**AC-5 — Additional Specialties resolve individually** *(overlaps #1486103 AC-10 — see Clarification Q6)*

**Given** a row with multiple Additional Specialty values and at least one that does not resolve to a known specialty,
**When** Practitioner system validation runs,
**Then** an Error is reported identifying each unresolved value, and that row does not proceed to processing.

**AC-6 — Additional Specialties present without a Primary Specialty**

**Given** a row where Additional Specialties are populated but Primary Specialty is blank,
**When** Practitioner system validation runs,
**Then** an Error is reported stating that Additional Specialties require a Primary Specialty, and that row does not proceed to processing.

### Group resolution — Tax ID scopes, Group NPI filters

**AC-7 — Tax ID and Group NPI resolve exactly one group**

**Given** a row whose Tax ID identifies one or more groups, and whose Group NPI is held by an eligible practice location under exactly one of them,
**When** Group system validation runs,
**Then** the row resolves to that group and proceeds to processing,
**And** the group is taken from the resolved match rather than from the Group Name in the file.

**AC-8 — Which groups and locations qualify as candidates** *(Pattern D — rules)*

Resolution must consider the same population the Practitioner Creation flow considers, in the same order.

- **Order is fixed:** Tax ID narrows the candidate groups first; Group NPI filters within that set; the practice location is matched last. Group NPI is **never** the first predicate — a single NPI can span hundreds of locations across many groups.
- **A Tax ID candidate** is a group whose tax identifier is of type EIN, is active, and is effective today. Expired or inactive tax identifiers are ignored.
- **An eligible practice location** is active, is not a pharmacy-type (NCPDP) location, and satisfies the billing rule: a Professional-classification location whose billing type is not UB, **or** a Facility-classification location whose billing type is 1500.
- **Candidates are deduplicated by group**, so one group holding several matching locations counts once.
- **Ineligible locations never resolve a group**, even when their NPI matches the file.
- **Exact-name tie-break (auto-resolve):** when several groups qualify but **exactly one** of them matches the file's Group Name *exactly after normalization* (AC-31), that group resolves automatically and the row proceeds without reconciliation. When **zero** or **two or more** candidates match exactly, the row goes to reconciliation. This tier is exact-only — similarity scores never auto-resolve.

> Grounded: TIN `23-2743545` with Vendor NPI `1053447151` returns five Penn groups. The file's Group Name `Penn Hospital Medicine Penn Presbyterian` matches exactly one of them byte-for-byte, so the row auto-resolves. Similarity at a 0.5 threshold would have returned three candidates, including `Penn Hospital Medicine HUP` (0.60) — a different hospital.

**AC-9 — Tax ID and Group NPI resolve several groups with no single exact name match**

**Given** a row whose Tax ID and Group NPI resolve to more than one eligible group, and where the exact-name tie-break in AC-8 does not resolve to exactly one candidate,
**When** Group system validation runs,
**Then** the row is held for group reconciliation with every matched group presented as a candidate,
**And** no group is chosen automatically.

**AC-10 — Tax ID resolves groups but none holds the Group NPI**

**Given** a row whose Tax ID identifies one or more groups, but where no eligible practice location under any of them holds the Group NPI,
**When** Group system validation runs,
**Then** an Error is reported showing the Tax ID, the Group NPI, and the groups found for that Tax ID, and that row does not proceed to processing.

**AC-11 — Tax ID resolves no group**

**Given** a row whose Tax ID identifies no group with an active, currently effective tax identifier,
**When** Group system validation runs,
**Then** the row is held for group reconciliation as a proposed new group,
**And** the group is not created until the specialist explicitly confirms it.

**AC-12 — Group Name differs from the resolved group**

**Given** a row whose Tax ID and Group NPI resolved a group, but whose Group Name does not match the resolved group's name after name comparison,
**When** Group system validation runs,
**Then** the row proceeds to processing using the resolved group,
**And** the name difference is reported as a Warning showing both the file value and the resolved group name.

### Practice-location resolution — address within the resolved group

**AC-13 — The address resolves exactly one practice location**

**Given** a row whose group resolved, and whose address matches exactly one eligible practice location under that group,
**When** Location system validation runs,
**Then** the row resolves to that practice location and proceeds to processing.

**AC-14 — The address matches no practice location in the group**

**Given** a row whose group resolved, but whose address matches no eligible practice location under that group,
**When** Location system validation runs,
**Then** the row is marked as a new practice location under the resolved group and proceeds to processing.

**AC-15 — The address matches more than one practice location**

**Given** a row whose group resolved, and whose address matches more than one eligible practice location under that group,
**When** Location system validation runs,
**Then** the row is held for reconciliation with every matched location presented as a candidate,
**And** no location is chosen automatically.

**AC-16 — Location NPI contradicts the address-matched location**

**Given** a row whose address matched exactly one practice location, but whose Location NPI differs from the NPI held by that location,
**When** Location system validation runs,
**Then** an Error is reported showing both NPIs and the matched address, and that row does not proceed to processing.

**AC-17 — How an address is matched** *(Pattern D — rules)*

- **Match on the address components**, normalized: Address Line 1, City, ZIP and State. These columns already exist in the upload template and no new address columns are required.
- **Normalize before comparing** — trim, collapse internal whitespace, and ignore casing and punctuation, consistent with how the guided flow normalizes an address before its duplicate check.
- **Scope to the resolved group** — only that group's eligible practice locations are considered, never an org-wide address search.
- **Only active addresses** of type Primary or Practice participate in the match.
- **The practice-location external identifier is never used** for matching, comparison, or key construction. It embeds the group name, both address lines, ZIP and phone, and is not regenerated when an address changes, so it is stale by design.
- **Address Line 2 and Phone are not match keys** — they may be shown to help a specialist distinguish candidates, but they never decide a match.

### Cross-row validation within the uploaded file

**AC-18 — The same practitioner across multiple rows is one practitioner**

**Given** a file in which the same Individual NPI appears on several rows with consistent practitioner details,
**When** cross-row validation runs,
**Then** the rows are treated as one practitioner practising at multiple locations, and no duplicate-practitioner Error is reported.

**AC-19 — The same Individual NPI carries conflicting practitioner details**

**Given** a file in which the same Individual NPI appears on several rows with conflicting practitioner details,
**When** cross-row validation runs,
**Then** an Error is reported naming the conflicting field and the row numbers involved, and those rows do not proceed to processing.

**AC-20 — The same Tax ID carries conflicting group details**

**Given** a file in which the same Tax ID appears on several rows with a conflicting Group Name or Group NPI,
**When** cross-row validation runs,
**Then** the conflict is raised once in group reconciliation rather than per row,
**And** the specialist's confirmed choice applies to every row carrying that Tax ID.

> Grounded: in *UPHS Provider.June.Changes_2026_Part 1*, Tax ID `23-2743545` with Group NPI `1184012569` appears under two different Group Names — `Penn Outpatient Lab` and `Penn Outpatient Lab Pennsylvania Hospital` — within the same upload.

**AC-21 — The same address carries conflicting location details**

**Given** a file in which the same address under the same group appears on several rows with a conflicting Location NPI or Location Name,
**When** cross-row validation runs,
**Then** an Error is reported naming the conflicting field and the row numbers involved, and those rows do not proceed to processing.

**AC-22 — A fully duplicated row**

**Given** a file containing two rows identical across practitioner, group and location,
**When** cross-row validation runs,
**Then** the duplicate is collapsed to a single row, and a Warning is reported naming the duplicated row numbers.

### Group reconciliation (before processing)

**AC-23 — One reconciliation entry per distinct group, not per row**

**Given** an uploaded file whose rows span several groups,
**When** System Validation completes,
**Then** the specialist is shown one reconciliation entry per distinct Tax ID and Group NPI pair in the file, each showing the file's values and affected row count alongside the group the system resolved,
**And** groups that resolved unambiguously are shown as already confirmed and need no action.

**AC-24 — Ambiguous groups and locations present ranked candidates without a pre-selection**

**Given** a group or location that could not be resolved to a single match,
**When** the specialist opens its reconciliation entry,
**Then** every candidate is listed with the information needed to tell them apart — for a group its name and location count, for a location its full address and NPI — ordered with the closest name match first,
**And** no candidate is pre-selected,
**And** the ordering is presented as a suggestion only.

**AC-25 — A confirmed group applies to all of its rows**

**Given** a specialist has chosen a candidate group, or confirmed a proposed new group,
**When** they confirm the reconciliation entry,
**Then** every row in the file carrying that Tax ID and Group NPI is bound to the confirmed group,
**And** the file cannot proceed to processing while any entry remains unconfirmed.

### File outcome and correction report

**AC-26 — Valid rows process while failed rows fall out**

**Given** an uploaded file in which some rows fail System Validation and others pass, and every reconciliation entry has been confirmed,
**When** processing is submitted,
**Then** the rows that passed continue to processing,
**And** the rows that failed are excluded and captured in the correction report,
**And** the specialist is shown how many rows proceeded and how many fell out.

**AC-27 — Every row fails**

**Given** an uploaded file in which every row fails System Validation,
**When** System Validation completes,
**Then** no rows proceed to processing, and the specialist is shown the correction report with the reason for every row.

**AC-28 — The correction report is downloadable and row-addressable**

**Given** a completed System Validation with at least one Error or Warning,
**When** the specialist downloads the correction report,
**Then** each entry shows the file row number, the field, the severity, the message, and the matched existing record where one was found,
**And** the row numbers match the row numbers in the uploaded file so the specialist can correct the source file directly.

**AC-29 — Severity model** *(Pattern D — rules)*

- **Error** — the row is excluded and must be corrected and re-uploaded. Applies to: AC-4, AC-5, AC-6, AC-10, AC-16, AC-19, AC-21.
- **Warning** — the row proceeds; reported for visibility only. Applies to: AC-3, AC-12, AC-22.
- **Requires reconciliation** — the row is neither passed nor failed until the specialist confirms. Applies to: AC-9, AC-11, AC-15, AC-20.
- **A file with Warnings and no Errors** proceeds in full once every reconciliation entry is confirmed; Warnings still appear in the correction report.
- **A row carrying both an Error and a Warning** is treated as an Error and excluded.
- **A file cannot be submitted** while any reconciliation entry is unconfirmed.
- **Warnings never block** submission and never require acknowledgement.

**AC-30 — New Group NPI column on the upload template** *(Pattern B — field/metadata)*

- **Column:** Group NPI
- **Section:** Group & Location
- **Required:** Yes — it is the second predicate in group resolution (AC-7, AC-8); without it a Tax ID cannot be narrowed to one group
- **Format:** exactly 10 digits
- **Position:** within the Group & Location section, immediately after Group Name
- **Appears in:** the downloadable sample template, the column-mapping experience, and the correction report field list
- **No new address columns** — Address Line 1, City, State and ZIP already exist in the Primary Address section and are reused for location matching (AC-17)
- **Backward compatibility:** previously saved column mappings must continue to load, presenting Group NPI as an unmapped required column

**AC-31 — Name comparison rules** *(Pattern D — rules)*

Group Name selects a group in **exactly one** circumstance — the exact-name tie-break in AC-8, where a single candidate matches exactly after normalization. In every other case it is compared only to decide whether to report a Warning, and to order candidates for the specialist.

- **Normalize before comparing** — lowercase, collapse every run of non-alphanumeric characters to a single space, and trim. This absorbs casing, extra spaces, trailing spaces, punctuation and dashes.
- **Identical after normalization** → no finding. This is what makes `WALGREEN CO` and `WALGREEN CO.` a silent match.
- **Exactly one candidate identical after normalization** → that candidate auto-resolves (AC-8). Two or more identical candidates, or none, → reconciliation.
- **A known alias pair** (curated list) → no finding.
- **Differs after normalization** → Warning (AC-12), proceeding on the resolved group.
- **Any difference in digits** — store, suite or unit numbers — is a **material difference**, never smoothed over by similarity scoring, because `WALGREENS #04029` and `WALGREENS #04348` are different groups despite near-identical text.
- **Similarity scoring may only order candidates** (AC-24). It may never select, auto-confirm, or remove a candidate from the list.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CSVSystemValidator` | **New** Apex class | Bulk Tax ID → NPI → address resolution, mirroring `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId` and `getPracticeLocation` | Drives AC-1 – AC-17 |
| `PRM_CSVGroupReconciliation` | **New** Apex class | One entry per distinct Tax ID + Group NPI, candidate ranking, apply-to-all-rows binding | Drives AC-20, AC-23 – AC-25 |
| `PRM_CSVSystemValidationSelector` | **New** selector class | Bulk equivalents of the flow's queries: EIN `Identifier` (active + effective today), `HealthcareFacility` (active, non-NCPDP, classification/billing rule), `Address` (active, Primary/Practice), practitioner NPI records, in-flight Case Managers | All SOQL here; the flow's per-row queries must become set-based |
| `PRM_CSVAddressMatcher` | **New** Apex class | Normalized Line1 + City + State + ZIP comparison, scoped to the resolved group | Drives AC-13 – AC-17, mirroring `PRMDRTransformAddData` + `PRMDRGetAddressDataForDupCheck` |
| `PRM_CSVNameComparator` | **New** Apex class | Normalization, alias lookup, digit-aware material-difference test, candidate ordering | Drives AC-12, AC-24, AC-31. Reuse `PRM_CSVSpecialtyResolver.normalize()` |
| `PRM_CSVCrossRowValidator` | **New** Apex class | In-file duplicate and conflict detection | Drives AC-18 – AC-22. No SOQL |
| `PRM_GroupAlias__mdt` | **New** Custom Metadata | Curated group name ↔ alias pairs | Drives AC-31, mirroring `PRM_SpecialtyAlias__mdt` |
| `PRM_CSVStandardTemplate` | Modified Apex class | Add a required `groupNpi` field to the Group & Location section | Drives AC-30. **Adding a field shifts 0-based positions — re-sync the `COL_*` constants in `PRM_CSVPractitionerCreationMapper`** |
| `PRM_CSVRowValidator` | Modified Apex class | Add the missing Tax ID 9-digit check and a Group NPI 10-digit check | Closes the #1486103 AC-2 gap |
| `PRM_GroupService` | Modified Apex class | Accept a resolved group Id from reconciliation instead of always keying on `{taxId}-{groupName}`; dual-read the legacy composite during cutover | Removes the silent-duplicate-group failure mode |
| `PRM_PracticeLocationAndGroupBatch` | Modified Apex class | Dedupe on the reconciled group Id rather than `{taxId}-{groupName}` | Same root cause |
| `PRM_CSVConversionBatch` | Modified Apex class | Invoke system + cross-row validation per shard; exclude failed rows rather than blocking the file | Drives AC-26, AC-27 |
| `PRM_CSVPractitionerCreationMapper` | Modified Apex class | Carry resolved group Id, location Id and new-vs-update decision into the generated JSON | Drives AC-2, AC-7, AC-13, AC-25 |
| `PRM_CSVJobUploadController` | Modified Apex class | Return findings, reconciliation entries and proceeded/fell-out counts | Drives AC-23, AC-26, AC-28 |
| `prmCsvGroupReconciliation` | **New** LWC | The per-group confirmation surface — the batch equivalent of `GroupTypeAhead` / `MultipleGroupNPIS` | Drives AC-23 – AC-25 |
| `prmCsvJobUpload` | Modified LWC | Severity-grouped results, reconciliation gate before submit, report download | Drives AC-26, AC-28, AC-29 |
| `prmCsvColumnMapper` | Modified LWC | Surface Group NPI as a mappable required column | Drives AC-30 |

**Grounded notes:**

- Group NPI lives on the **practice location** (`HealthcareFacility.PRM_NpiId__r.Npi`), not the Account. Do not look for it on `HealthcareProviderNpi.AccountId` — coverage there is 1.8%.
- `Identifier` filters must include `PRM_IDEffectiveToday__c = true` alongside `PRM_Active__c = true`, matching `getAccountForIdentifier`.
- `HealthcareFacility.PRM_ExternalId__c` is **out of bounds** for matching (AC-17).
- The guided flow's helper queries run per submission; the bulk equivalents must be set-based and shard-safe, one query per entity per shard.
- `HealthcareProvider.PRM_RecordKey__c` does not exist in the org (undeployed Epic E); do not traverse it at runtime.

---

## Definition of done

- [ ] A row whose Tax ID and Group NPI resolve one eligible group binds to it, ignoring the file's Group Name (AC-7)
- [ ] Resolution is Tax-ID-first — an NPI spanning hundreds of locations never widens the candidate set (AC-8)
- [ ] Ineligible locations (inactive, NCPDP, or failing the classification/billing rule) never resolve a group (AC-8)
- [ ] An expired or inactive EIN identifier is ignored during Tax ID scoping (AC-8)
- [ ] `WALGREEN CO` against a stored `WALGREEN CO.` passes silently; a different store number never auto-matches (AC-31)
- [ ] A row whose address matches one location in the resolved group binds to it; no match creates a new location (AC-13, AC-14)
- [ ] Address matching uses normalized Line 1, City, State and ZIP, scoped to the group, and never the practice-location external identifier (AC-17)
- [ ] A row whose Individual NPI matches an existing practitioner resolves as an update with no duplicate created (AC-2)
- [ ] A practitioner already in credentialing proceeds with a Warning naming the existing Case Manager (AC-3)
- [ ] Ambiguous groups and locations are held for reconciliation with no automatic selection (AC-9, AC-15, AC-24)
- [ ] A confirmed group applies to every row sharing its Tax ID and Group NPI, and the file cannot submit while any entry is unconfirmed (AC-25, AC-29)
- [ ] A new group is never created without explicit confirmation (AC-11)
- [ ] Each Error excludes only its own row, leaving the remaining rows processing (AC-26)
- [ ] The correction report downloads with row number, field, severity, message and matched record, aligned to the uploaded file's row numbers (AC-28)
- [ ] Group NPI appears in the sample template, mapping experience and validator as required, and saved mappings still load (AC-30)
- [ ] Re-synced `COL_*` positions verified — generated JSON maps every field to the correct column after the template change
- [ ] Legacy `{taxId}-{groupName}` accounts still resolve during cutover via dual-read
- [ ] Resolution parity spot-checked against the Practitioner Creation Group step: the same Tax ID + NPI returns the same group set
- [ ] ≥ 85% Apex coverage on the new validator, reconciliation, matcher, comparator, cross-row validator and selector, including bulk (200+ rows), single-row, empty-file and negative paths
- [ ] No regression to Initial Validation behaviour covered by #1486103

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which Case Manager statuses count as "credentialing in flight" for the AC-3 Warning? | Determines the in-flight query and how often the Warning fires | BA / Ops |
| 2 | The guided flow narrows locations to **delegated** ones (`checkDelegatedPracLoc`). Should Mass Upload apply the same narrowing, given the request type is Delegated Practitioner? | Changes the location candidate set in AC-13 – AC-15 | BA / Technical |
| 3 | How should a row be treated when the matched practitioner, group or location is terminated or inactive — proceed, warn, or error? | Adds scenarios across AC-2, AC-7 and AC-13 | BA / Ops |
| 4 | Should reconciliation decisions be remembered across uploads, so the same group isn't re-confirmed every file? | Materially changes repeat-upload effort | Product |
| 5 | Who curates the group alias list, and through what process? | Determines whether AC-31's alias tier is usable | Ops / BA |
| 6 | AC-5 overlaps #1486103 AC-10. Should specialty resolution live entirely in Initial Validation? | Avoids duplicate ACs and duplicate implementation | BA |
| 7 | Tax ID `361924025` has 233 vendor groups including two unrelated names (`University Of Miami`, `MATTHEW MCCULLOUGH DDS`). Is that a data-quality defect needing its own cleanup? | Affects candidate-list noise; may warrant a remediation story | Ops / Data |
| 8 | Should Mass Upload trigger regeneration of a stale practice-location external ID when it resolves a location, or leave that to the separate remediation? | Decides whether this story touches the known stale-external-ID defect | Technical / Product |
| 9 | Is there a maximum row count or distinct-group count per upload? | Sizes the selector queries and the reconciliation UI | Technical |
| 10 | After correcting a fallout file, does the specialist upload a new file or amend the original job? | Determines whether a resubmission journey is needed | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_GroupService` | Apex | **HIGH** | Group key moves off `{taxId}-{groupName}`; needs dual-read for 240k existing accounts |
| `PRM_PracticeLocationAndGroupBatch` | Apex | **HIGH** | Group dedupe key changes |
| `PRM_CSVStandardTemplate` | Apex | **HIGH** | Adding a column shifts positional indexes used by the remapper, validator and mapper |
| `PRM_CSVPractitionerCreationMapper` | Apex | **HIGH** | `COL_*` constants must be re-synced or every field maps one column off |
| `PRM_CSVConversionBatch` | Apex | **HIGH** | Block-the-file → partial processing |
| `prmCsvJobUpload` + new reconciliation LWC | LWC | **MEDIUM** | New gated step between validation and submit |
| `PRM_CSVRowValidator` | Apex | MEDIUM | Gains Tax ID and Group NPI format checks |
| `prmCsvColumnMapper` / `PRM_CSVColumnMapping__c` | LWC / Object | MEDIUM | New required column; saved mappings predate it |
| `PRM_PractitionerCreationHelper` | Apex | LOW | Parity source only — unchanged, but its logic must not drift from the bulk copy |
| Practice-location external ID defect | Data / Apex | LOW | Deliberately avoided rather than fixed here (Clarification Q8) |
| #1486103 Initial Validation | Requirement | LOW | Specialty AC overlap to reconcile |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_CSVSystemValidator` | New Apex | **XL** | Three-stage resolution, 17 scenarios |
| `PRM_CSVGroupReconciliation` | New Apex | **XL** | Aggregation, ranking, apply-to-all-rows binding |
| `prmCsvGroupReconciliation` | New LWC | **XL** | New gated confirmation surface |
| `PRM_CSVSystemValidationSelector` | New Apex | **L** | Set-based rewrites of the flow's per-row queries |
| `PRM_CSVAddressMatcher` | New Apex | **L** | Normalized component matching scoped to a group |
| `PRM_CSVCrossRowValidator` | New Apex | **L** | In-file conflict and duplicate detection |
| `PRM_CSVNameComparator` + `PRM_GroupAlias__mdt` | New Apex + CMDT | **L** | Normalization, alias tier, digit-aware comparison |
| `PRM_GroupService` + batch key change | Modified Apex | **L** | Includes legacy dual-read |
| `PRM_CSVStandardTemplate` + `COL_*` re-sync | Modified Apex | **L** | Low code volume, high regression risk |
| `PRM_CSVConversionBatch` | Modified Apex | **L** | Partial processing |
| `PRM_CSVPractitionerCreationMapper` | Modified Apex | **M** | Carry resolution decisions into JSON |
| `PRM_CSVRowValidator` | Modified Apex | **M** | Tax ID + Group NPI format checks |
| `PRM_CSVJobUploadController` | Modified Apex | **M** | Findings, reconciliation entries, counts |
| `prmCsvJobUpload` | Modified LWC | **M** | Severity grouping and submit gate |
| `prmCsvColumnMapper` | Modified LWC | **M** | New required column |
| Apex + Jest tests (≥ 85%, bulk + negative) | New tests | **XL** | 31 ACs including eligibility, ambiguity and reconciliation paths |
| Resolution-parity verification vs the Group step | Test / analysis | **M** | Same Tax ID + NPI must return the same group set |

**Total Estimated Effort:** ~16–20 engineer-days — **XXL** overall.
