# USER STORY 1: Record every credentialing artefact against the Case Manager exactly once

**Story Key:** PRM-E19-CMASERVICE
**Persona:** Credentialing Specialist
**Priority:** P1
**OmniScript:** N/A — this is a common back-end service invoked by the Practitioner Creation record-creation chain, not an OmniScript change
**Integration Procedures:** N/A (new Apex service; replaces the legacy DataMapper write path — see Technical Implementation)
**Relevant Requirements:**
- `docs/build-verification/02_Parity_Ledger.md` — step row 20 and §6 rule 9 (CMA subset rule)
- `docs/implementation-plan/PRM_Implementation_Plan.md` §8.1 — CMA as a common service invoked by the batch classes
- `docs/gamechanger/02_IBC_Integration_Plan.md` — this story is the **GameChanger 3.0 pilot instrument** (D9, revised)
- ⚠ **`requirements/PAR_CaseManager_Association_CMA_Redesign_User_Stories.md`** — an existing redesign that writes to the **same object** from the **PAR flow**. Its User Story 6 creates association records during PAR form submission using the Practitioner Practice Location category. **Read before building — see Clarification Question 7.**

**Affected downstream roles:** PDA Specialist, PDM Specialist, Network Management QC Specialist — all read the Case Manager's associated-record list when reviewing a credentialing case.

---

## Story

**As a** Credentialing Specialist,
**I want** every provider record my submission creates to be listed against the credentialing case exactly once, under the right category,
**So that** when I or a reviewer opens the case we see a complete, non-duplicated inventory of what was captured, and re-running a failed submission never doubles it up.

**Why it matters:** the associated-record list is what reviewers use to confirm a submission is complete before it moves to PSV and QC. Today the legacy flow can write the same association twice when a submission is retried, and reviewers cannot tell a genuine second licence from a duplicate. Under the new async model a failed batch is **retried by design**, so duplicate-safety stops being a nice-to-have and becomes a correctness requirement.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Practitioner Creation — IBC Professional Staff | N/A (back-end) | Record creation, after each batch step | Submission payload + records created by that step |
| Practitioner Creation — Delegated Credentialing | N/A (back-end) | Record creation, after each batch step | Submission payload + records created by that step |

**In scope:** creating and updating the Case Manager association rows for provider records that have an association category.
**Out of scope:** creating the provider records themselves (each owning service does that); the association categories that no credentialing artefact maps to; the Case Manager itself.

---

## Current State (from codebase)

- **Object:** `PRM_CaseManagerAssociation__c` exists with **19 record types** and 18 fields (17 lookups plus `PRM_RequestType__c`). Verified from `force-app/main/default/objects/PRM_CaseManagerAssociation__c/`.
- **Legacy write path:** `PRMDRPCreateCaseManagerAssociation` (DataMapper) performs the association write. Related read-side mappers: `PRMDRExtractCaseManagerAssociationDetails`, `PRMDRECaseManagerAssocFacility`, `PRMExtractCaseManagerAssociationsPCF`.
- **Duplicate behaviour:** the legacy mapper has no pre-check, so a re-submission or retry can produce a second association row for the same record.
- **Parity Ledger row 20** classifies the target behaviour as insert-or-update with an **idempotent pre-check dedup**.

> **Note for the GameChanger pilot.** A prior implementation of this service exists in the repo. It is deliberately **not** cited in this story — the story is written from the Parity Ledger and the live object metadata only, so the existing implementation can serve as an independent answer key when grading the pipeline's output.

---

## Acceptance Criteria

**AC-1 — Every eligible record is listed against the case (happy path)**

**Given** a Credentialing Specialist submits a practitioner for credentialing and the submission captures records that have an association category,
**When** the submission is processed,
**Then** the credentialing case lists one association entry for each of those records,
**And** each entry is filed under the category that matches the kind of record it points to,
**And** records with no association category are not listed and are not treated as missing.

**AC-2 — Re-processing the same submission does not duplicate entries (idempotency)**

**Given** a submission has already been processed and its associations are listed against the credentialing case,
**When** the same submission is processed again — for example after a failed step is retried,
**Then** no additional association entry is created for a record that is already listed,
**And** the existing entry is left in place rather than replaced,
**And** the total number of entries on the case is unchanged.

**AC-3 — A high-volume submission is recorded completely**

**Given** a Credentialing Specialist submits a batch of practitioners large enough to be processed in chunks,
**When** the submission is processed,
**Then** every eligible record across every practitioner in the batch is listed against its own credentialing case,
**And** no entry is attributed to the wrong practitioner's case.

**AC-4 — A record with no association category is skipped, not failed (edge case)**

**Given** a submission captures a record whose kind has no association category,
**When** the submission is processed,
**Then** no association entry is created for that record,
**And** the submission continues without error,
**And** the case is not reported as incomplete on account of that record.

**AC-5 — Records created/updated when a submission is processed**

**Given** a Credentialing Specialist's submission has produced provider records that have an association category,
**When** the submission is processed,
**Then** the following records are created or updated exactly as specified:

**Case Manager Association — Create (one per eligible record, when no entry exists yet)**

The object carries **18 fields**: two set on every entry, and sixteen record-pointer fields of which **exactly one** is populated per entry.

*Always set:*

| Field | Value | Notes |
|---|---|---|
| Record Type | {Category matching the record's kind} | one of the 19 categories; see AC-6 |
| Case Manager | {Credentialing case for this practitioner} | the association's parent |
| Request Type | {Submission request type} | see Clarification Question 3 |

*Exactly one of the following, matching the entry's category — every other pointer field is left empty:*

| Field | Value | Populated for category |
|---|---|---|
| Account | {Vendor or practitioner account} | Vendor · Practitioner |
| Address | {Address} | Practice Location Address |
| Business Licence | {Business licence} | Business Licence |
| Contact Profile | {Contact profile} | Contact Profile |
| Healthcare Facility | {Practice location facility} | Practice Location |
| Healthcare Facility Association | {Facility association} | Practice Location Association |
| Healthcare Facility Network | {Facility network} | Practice Location Network |
| Healthcare Practitioner Facility | {Practitioner-to-location link} | Practitioner Practice Location · Practitioner at Practice Location Taxonomy and Network |
| Healthcare Provider NPI | {Provider NPI} | Healthcare Provider NPI |
| Healthcare Provider Taxonomy | {Provider taxonomy} | Healthcare Provider Taxonomy · Practice Location Taxonomy |
| Identifier | {Identifier} | Identifier |
| Info Code Assignment | {Info code assignment} | Info Code Assignment |
| Person Education | {Education record} | Person Education |
| Person Language | {Language record} | Person Language |
| Programme Participation | {Programme participation} | Programme Participation |
| Provider Feature | {Provider feature} | Provider Feature |

> There are **19 categories but only 16 pointer fields**, so some categories share a pointer field (shown above). **The pairings marked with two categories are inferred from the field and category names, not from a signed-off map — see Clarification Question 6.**

**Case Manager Association — No change (when an entry already exists for that record and category)**

| Field | Value | Notes |
|---|---|---|
| *(none)* | — | the existing entry is left exactly as it is; this is the idempotency guarantee in AC-2 |

**AC-6 — Association categories available on the object**

- **Object:** Case Manager Association (`PRM_CaseManagerAssociation__c`)
- **Categories (record types) present in the org — 19:** Business Licence · Healthcare Provider Taxonomy · Identifier · Contact Profile · Healthcare Provider NPI · Info Code Assignment · Person Education · Person Language · Practice Location · Practitioner · Vendor · Practice Location Address · Practice Location Association · Practice Location Network · Practice Location Taxonomy · Practitioner Practice Location · Practitioner at Practice Location Taxonomy and Network · Programme Participation · Provider Feature
- **Resolution:** categories are resolved by their developer name at run time, never by a stored identifier.

> ⚠ **The Parity Ledger says 14 categories and states that Education, Board Certification, Info Code, NPI, File, Contact and Language have none.** The org contains 19, including Person Education, Info Code Assignment, Healthcare Provider NPI, Contact Profile and Person Language. **See Clarification Question 1 — this must be resolved before the category list is treated as final.**

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CMAService` | New Apex service class | Common service extending `PRM_ServiceBase`; accepts the association requests aggregated by a batch chunk and performs **one** bulk insert of `PRM_CaseManagerAssociation__c` | Drives AC-1, AC-3, AC-5 |
| `PRM_CMAService` — pre-check | Apex | Query existing associations for the Case Manager set, key on (Case Manager, record type, target record id), and filter the insert list against it | Drives AC-2; implements Parity Ledger row 20's "idempotent pre-check dedup" |
| Record-type resolution | Apex | `Schema.SObjectType.PRM_CaseManagerAssociation__c.getRecordTypeInfosByDeveloperName()` via cached describe — **no hardcoded ids**, no SOQL on `RecordType` | Drives AC-6; per `CLAUDE.md` §6 |
| Category routing map | Apex | Map each target SObject type to its record type developer name and its pointer field; SObject types absent from the map are skipped silently | Drives AC-4, AC-6 |
| `PRM_CMAServiceTest` | New Apex test class | Bulk (200), single, empty, negative and re-run/idempotency paths, with outcome assertions | Drives the Definition of done coverage gate |
| Callers (future) | Apex | Each batch class aggregates its chunk's association requests and calls the service **once per chunk, in the same transaction** | Per `PRM_Implementation_Plan.md` §8.1; out of scope for this story |
| `PRMDRPCreateCaseManagerAssociation` | Legacy DataMapper | Superseded for the Practitioner Creation path — **not deleted** in this story | Retirement is a separate cutover story |

**Governor posture:** one bulk SOQL for the pre-check and one bulk DML for the insert, per invocation. No SOQL or DML inside a loop. `with sharing`, CRUD/FLS enforced.

---

## Definition of done

- [ ] A submission that captures eligible records produces exactly one association entry per record, filed under the correct category (AC-1).
- [ ] Re-processing the same submission adds no entries and modifies none (AC-2).
- [ ] A 200-record bulk submission is recorded completely, with every entry attributed to the correct credentialing case (AC-3).
- [ ] A record whose kind has no association category is skipped without error and without being reported as missing (AC-4).
- [ ] Exactly one record-pointer field is populated on each entry (AC-5).
- [ ] Record types are resolved by developer name at run time; no hardcoded ids anywhere in the change.
- [ ] One bulk SOQL and one bulk DML per invocation, verified against a 200-record run.
- [ ] ≥ 85% Apex coverage including bulk, empty, negative and re-run paths, with outcome assertions rather than "no exception thrown".
- [ ] Clarification Question 1 (category count) is answered and AC-6 reflects the answer.
- [ ] No regression to the read-side mappers listed in Impact Analysis.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **The Parity Ledger says 14 association categories and that Education, Board Certification, Info Code, NPI, File, Contact and Language have none — but the org has 19, including Person Education, Info Code Assignment, Healthcare Provider NPI, Contact Profile and Person Language.** Is the ledger scoped to Practitioner Creation only (with the extra categories belonging to other flows), or is the ledger stale? | Determines the routing map and whether AC-4's "skip" list is 7 kinds or 2. Also determines whether the Parity Auditor's rule 9 is producing false negatives across every service. | Technical / BA |
| 2 | For the categories that do belong to Practitioner Creation, is the association written for **both** the IBC Professional Staff and Delegated Credentialing branches, or is the set branch-specific? | Changes the routing map and the branch-coverage tests. | Technical |
| 3 | What value should Request Type carry — the submission's request type, or a value specific to the association category? | Affects every created row; the field is on the object but its source is unstated in the ledger. | BA |
| 4 | Is the dedup key (Case Manager + category + target record) correct, or can one record legitimately appear twice under the same category on one case? | If duplicates are legitimate in some case, AC-2 is wrong as written. | Technical / BA |
| 5 | When a record is deleted or superseded later in the credentialing lifecycle, should its association entry be removed, or left as history? | Out of scope for this story, but determines whether a follow-on story is needed. | BA / Ops |
| 6 | **There are 19 categories but only 16 pointer fields.** The AC-5 pairings for the categories that share a field (Vendor/Practitioner → Account; Practitioner Practice Location and Practitioner-at-Location Taxonomy and Network → Healthcare Practitioner Facility; Healthcare Provider Taxonomy and Practice Location Taxonomy → Healthcare Provider Taxonomy) are **inferred from naming, not from a signed-off map.** Confirm each pairing. *Partially corroborated:* the PAR redesign story documents Practitioner Practice Location → Healthcare Practitioner Facility, which matches. | A wrong pairing writes the association against the wrong record and is invisible to object-level parity checking. This is a **CL-11 field-map sign-off** item — field-level parity stays `BLOCKED` until it closes. | Technical |
| 7 | ✅ **ANSWERED 2026-09-09 by the org — reframed.** The question assumed two *prospective* write paths. In fact **PAR already calls this service today**: `sf_deps.py callers PRM_CMAService` returns `PRM_ParFormCmaBatch` (plus `PRM_CMAServiceTest`), so a shared write path onto `PRM_CaseManagerAssociation__c` exists in the deployed org. **Revised question:** is `PRM_ParFormCmaBatch`'s use of the service consistent with the dedup semantics and category routing this story specifies, and does the PAR redesign story (User Story 6) intend to keep, replace or bypass it? | The duplicate-semantics risk is *already live*, not hypothetical. Any change to this service's dedup key or routing map is a change to the PAR flow's behaviour, so PAR regression coverage is in scope for this story. | Technical / Architect |
| 8 | The PAR redesign references an `IndividualApplication` flag that switches consumers over to reading associations. Does the Practitioner Creation path need to set or respect that flag? | Determines whether reviewers see this story's associations at all. | Technical / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CaseManagerAssociation__c` | Object | HIGH | All rows for the Practitioner Creation path are produced by this service |
| `PRMDRPCreateCaseManagerAssociation` | DataMapper | HIGH | Superseded for this path; still live for other flows until a cutover story retires it |
| `PRMDRExtractCaseManagerAssociationDetails` | DataMapper | MEDIUM | Read-side; must continue to return the same shape |
| `PRMDRECaseManagerAssocFacility` | DataMapper | MEDIUM | Read-side; facility-scoped association read |
| `PRMExtractCaseManagerAssociationsPCF` | DataMapper | MEDIUM | Read-side; feeds the Practitioner Creation form |
| `PRM_ParFormCmaBatch` | Apex | **HIGH** | **Existing caller of this service in the deployed org** (measured 2026-09-09). Any change to the dedup key or category routing changes PAR behaviour — PAR regression coverage is in scope |
| PAR CMA redesign (User Story 6) | Requirement | **HIGH** | Writes the same object from the PAR flow; the shared path already exists via `PRM_ParFormCmaBatch` — see Clarification Question 7 |
| `PRM_ServiceBase` | Apex | LOW | Parent class; unchanged. Deployed |
| The batch classes | Apex | LOW | Future callers. `PRM_PractitionerBatch` is committed but not deployed; the other four are not authored |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_CMAService` | New Apex class | XL | Routing map, cached record-type resolution, pre-check dedup, one bulk DML |
| Category routing map | Apex config within the class | M | Size depends on the answer to Clarification Question 1 |
| `PRM_CMAServiceTest` | New Apex test class | L | Bulk 200, single, empty, negative, re-run |
| Parity Ledger correction | Documentation | S | Only if Clarification Question 1 finds the ledger stale |

**Total Estimated Effort:** XL + M + L + S — **XL overall (~1.5–2 days)**
*AI-estimated — validate with the team.*
