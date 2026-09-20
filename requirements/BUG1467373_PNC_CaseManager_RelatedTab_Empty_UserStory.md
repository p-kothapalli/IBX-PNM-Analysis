# USER STORY: PNC / PAR Case Manager Related tab shows no records after new-practitioner submit (BUG 1467373)

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScript:** PAR form (Practitioner Participation / PNC group path) — display fix is on the Case Manager record page, not an OmniScript element
**Integration Procedures:** `PRM_CreateParFormRecords` (Remote Action that starts Case Manager Association creation after PAR submit)
**Relevant Requirements:** BUG 1467373; `PAR_CaseManager_Association_CMA_User_Stories_v3.md` (stories 1429783 / 1461944 — CMA write path); `requirements/SOQL/2026-09-18_PNC_CaseManagerRelatedTab.md`

---

## Story

**As a** Credentialing Specialist,
**I want** the Case Manager Related tab to show the practitioner, group, practice locations, practitioner-at-location links, networks, taxonomies, licenses, and identifiers that belong to a submitted PNC or PAR case,
**So that** I can review a new practitioner added to an existing PNC group without an empty Related tab.

**Why it matters:** This is a Sprint 65 regression. After Case Manager Associations were turned on for PAR, the Related tab switched from standard related lists to a custom list. That custom list only knows how to render PDM Manual Change and Provider Change. PNC and PAR cases now look empty even when associations already exist, so Application Review cannot see the records on the case.

---

## Scope

| Flow | OmniScript / Page | Affected Step | Data Source |
|------|-------------------|---------------|-------------|
| PAR — PNC group (new practitioner, existing group) | Case Manager record page Related tab | Related | `prmCaseManagerRelatedList` → related-list controller |
| PAR — Practitioner Participation | Same Related tab | Related | Same controller + PAR CMA batch |
| PAR submit (record creation) | `PRM_CreateParFormRecords` Remote Action | After records commit | `PRM_ParFormCmaCreation` → queueable → `PRM_ParFormCmaBatch` |

**In scope**

- PNC (`PRM_PNC`) and Practitioner Participation Request Case Managers.
- Related-tab display of Case Manager Associations when the case has no PDM Manual Update Type.
- Associating the **existing** group, practice locations, and networks used on the form (without overwriting those records’ own Case Manager lookup).
- Filling missing practitioner-at-location / location / network / taxonomy associations that the current PAR CMA batch does not write when the location still points at an older Case Manager.

**Out of scope**

- PDM Manual Change and Provider Change Related-tab mapping (already implemented).
- Changing the Case Manager lookup on an existing group or practice location.
- Recreating the standard (non-CMA) Related-tab facet as the long-term UI.

---

## Current State (from codebase)

### How the Related tab is chosen

`PRM_CaseManagerRecordPage` has **two** Related tabs:

- **Standard related lists** (Accounts, Practitioner Practice Locations, …) when **Use Case Manager Association** is false.
- **Custom LWC** `prmCaseManagerRelatedList` when **Use Case Manager Association** is true.

The screenshot text **“No related records found.”** is the LWC empty state in `prmCaseManagerRelatedList.html`, not a standard related list. That means the CMA flag is **true** on the defect Case Manager.

### How the custom tab loads data

1. LWC wires `PRM_CaseManagerRelatedListController.fetchCaseManagerAssociatedRecords`.
2. Controller loads every Case Manager Association for the Case Manager.
3. **Provider Change** record type is delegated to `PRM_CMRelatedListPCFHelper` (maps by Provider Change request type).
4. Every other record type is treated as **PDM Manual Change**: it splits **PDM Manual Update Type** and matches `PRM_Relatedlistconfiguration__mdt`.
5. If PDM Manual Update Type is blank, the controller **returns an empty map** (comment: “Par Form … return empty rather than throw”). The unit test `testFetchCMARecordsForParCaseManagerNoPdmType` **asserts that empty map**. That test locked in this defect.

### What PAR already writes

`PRM_ParFormCmaCreation` (feature flag **Use Case Manager Association for PAR**) enqueues `PRM_ParFormCmaBatch`. The batch:

- Finds records with **Case Manager = this case**.
- Inserts one association per record (only that record’s own lookup).
- Always sets **Use Case Manager Association = true** in `finish()`, which **hides** the standard Related lists.

Analog in `ibx-qa` (IA-0000192693, PNC, Submitted, Heather C Wargo): **12 associations already exist** (practitioner, vendor/group Einstein Practice Plan, licenses, identifiers, NPIs, taxonomy, education, language, contact). The Related tab would still be empty because PDM Manual Update Type is blank.

### What the batch misses on “existing PNC group”

On the same analog case:

- Two **Practitioner Practice Location** rows are stamped to this Case Manager.
- The practice location they point at still has a **different** Case Manager.
- **Zero** practice locations are stamped to this Case Manager.
- **Zero** associations exist for Practice Location, Practitioner Practice Location, Practice Location Network, or Practice Location Taxonomy.

The batch never walks from the new practitioner-at-location row to the existing location and its networks. Existing locations must **not** have their Case Manager lookup overwritten; they need association rows only.

---

## Acceptance Criteria

> Pattern A in business language. Pattern B for metadata. Pattern E for association rows the batch must write. No Apex class names, IP versions, or API field names inside Pattern A.

**AC-1 — Related tab shows records on a submitted PNC Case Manager**

**Given** a Credentialing Specialist submitted the PAR form for a **new practitioner** on an **existing PNC group**, and the resulting Case Manager is PNC / Submitted,
**When** they open the Case Manager and click Related,
**Then** the tab does not show “No related records found”,
**And** they see lists for the practitioner, the existing group, the practice locations used on the form, the practitioner-at-location links, practice location networks, practice location taxonomies, business licenses, and identifiers / NPIs that belong to the case.

**AC-2 — Same Related tab behaviour on Practitioner Participation**

**Given** a Credentialing Specialist submitted the PAR form as Practitioner Participation (not PNC) and Case Manager Associations were created for that case,
**When** they open that Case Manager and click Related,
**Then** the same related lists as AC-1 appear from those associations,
**And** the tab is not empty solely because the case has no PDM Manual Update Type.

**AC-3 — Existing group and locations appear without stealing their Case Manager**

**Given** the practitioner was added to an existing PNC group whose practice locations already belong to an older Case Manager,
**When** the Credentialing Specialist opens Related on the **new** Case Manager,
**Then** the existing group, those practice locations, and those locations’ networks and taxonomies appear on this case,
**And** each existing group and practice location still shows its **original** Case Manager on its own record.

**AC-4 — Empty only when there is truly nothing to show**

**Given** a PNC or PAR Case Manager that has no Case Manager Associations (feature flag off, or submit failed before associations were written),
**When** the Credentialing Specialist opens Related,
**Then** they either still see the standard related lists (when Use Case Manager Association is false) or a true empty state,
**And** a PDM Manual Change or Provider Change Case Manager Related tab is unchanged.

**AC-5 — Create related-list configuration for PNC and PAR**

- **API Name:** `PRM_CaseManager_Record_Type__c`
- **Object:** `PRM_Relatedlistconfiguration__mdt` (Related List Configuration)
- **Type:** Text(255)
- **Label:** Case Manager Record Type
- **Required:** false
- **Help text:** Developer names of Case Manager record types this row applies to (comma-separated), e.g. PNC and Practitioner Participation Request.
- **Description:** Lets the Related-tab LWC map association rows for PAR/PNC the same way PDM Manual Update Type and Provider Change request type already do.
- **Track History:** false
- **Seed rows:** one configuration row per related list in AC-1 (Practitioners, Accounts, Practice Locations, Practitioner Practice Locations, Practice Location Networks, Practice Location Taxonomies, Business Licenses, Identifiers, Healthcare Provider NPIs). Reuse the column strings already used on the matching PDM/Provider Change rows. Set Case Manager Record Type to `PRM_PNC,PRM_PractitionerParticipationRequest`.

**AC-6 — Records created for existing-group location coverage (Pattern E)**

**Given** a PAR/PNC submit that created practitioner-at-location rows on this Case Manager pointing at **existing** practice locations,
**When** Case Manager Association creation runs (or is re-run for an already-submitted case),
**Then** the following records are created exactly as specified (skip a row if an association of that record type already exists for the same Case Manager + target record):

**Case Manager Association — Practitioner — Create** (already written today; keep)

| Field | Value | Notes |
|---|---|---|
| Record Type | Practitioner | CMA record type for the person account |
| Case Manager | {this Case Manager} | |
| Account | {new practitioner} | only lookup set on this row |

**Case Manager Association — Vendor — Create** (already written today when the group account is case-scoped; keep)

| Field | Value | Notes |
|---|---|---|
| Record Type | Vendor | |
| Case Manager | {this Case Manager} | |
| Account | {existing PNC group} | do not change the group account’s Case Manager |

**Case Manager Association — Practitioner Practice Location — Create** (missing today)

| Field | Value | Notes |
|---|---|---|
| Record Type | Practitioner Practice Location | |
| Case Manager | {this Case Manager} | |
| Healthcare Practitioner Facility | {each practitioner-at-location row stamped to this Case Manager} | only lookup set |

**Case Manager Association — Practice Location — Create** (missing today)

| Field | Value | Notes |
|---|---|---|
| Record Type | Practice Location | |
| Case Manager | {this Case Manager} | |
| Healthcare Facility | {the existing practice location on that practitioner-at-location row} | do **not** update the location’s Case Manager |

**Case Manager Association — Practice Location Network — Create** (missing today)

| Field | Value | Notes |
|---|---|---|
| Record Type | Practice Location Network | |
| Case Manager | {this Case Manager} | |
| Healthcare Facility Network | {each facility-network row on that existing location} | facility-network record type only |

**Case Manager Association — Practice Location Taxonomy — Create** (missing today)

| Field | Value | Notes |
|---|---|---|
| Record Type | Practice Location Taxonomy | |
| Case Manager | {this Case Manager} | |
| Healthcare Facility Network | {each facility-taxonomy row on that existing location} | facility-taxonomy record type only |

**Case Manager Association — Identifier — Create** (already written today; keep)

| Field | Value | Notes |
|---|---|---|
| Record Type | Identifier | |
| Case Manager | {this Case Manager} | |
| Identifier | {each identifier stamped to this Case Manager} | |

**Case Manager Association — Healthcare Provider NPI — Create** (already written today; keep)

| Field | Value | Notes |
|---|---|---|
| Record Type | Healthcare Provider NPI | |
| Case Manager | {this Case Manager} | |
| Healthcare Provider NPI | {each NPI stamped to this Case Manager} | |

**Case Manager Association — Business License — Create** (already written today; keep)

| Field | Value | Notes |
|---|---|---|
| Record Type | Business License | |
| Case Manager | {this Case Manager} | |
| Business License | {each license stamped to this Case Manager} | |

**Practice Location (Healthcare Facility) — not updated**

| Field | Value | Notes |
|---|---|---|
| Case Manager | unchanged | existing location keeps its original Case Manager |

**Group Account — not updated**

| Field | Value | Notes |
|---|---|---|
| Case Manager | unchanged | existing PNC group keeps its original Case Manager |

**AC-7 — Regression: PDM and Provider Change Related tabs still work**

**Given** a PDM Manual Change Case Manager with a PDM Manual Update Type, and a Provider Change Case Manager with a request type,
**When** a Credentialing Specialist or PDM Specialist opens Related,
**Then** those cases still show the related lists they show today,
**And** the PNC/PAR mapping is not applied to them.

---

## Technical Implementation (high-level)

> Display bug is sufficient to explain the screenshot. Location lists also need the batch to walk existing locations. Invert the PAR “empty map” unit test — it currently certifies the defect.

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CaseManagerRelatedListController` | Modified Apex | After the Provider Change branch, if Case Manager record type is `PRM_PNC` or `PRM_PractitionerParticipationRequest`, delegate to a PAR/PNC helper instead of requiring `PRM_PDMManualUpdateType__c` | Drives AC-1, AC-2, AC-4. Keep the blank-PDM early return **only** for remaining non-PAR types that are not Provider Change. |
| `PRM_CMRelatedListParHelper` (new) | New Apex | Map CMA record types → related-list names the same way `PRM_CMRelatedListPCFHelper` maps Provider Change. Load `PRM_Relatedlistconfiguration__mdt` filtered by `PRM_CaseManager_Record_Type__c` | Drives AC-1. Mapping: `PRM_Practitioner` → Practitioners; `PRM_Vendor` → Accounts; `PRM_PracticeLocation` → Practice Locations; `Practitioner_Practice_Location` → Practitioner Practice Locations; `Practice_Location_Network` → Practice Location Networks; `Practice_Location_Taxonomy` → Practice Location Taxonomies; `Business_License` → Business Licenses; `Identifier` → Identifiers; `PRM_Healthcare_Provider_NPI` → Healthcare Provider NPIs. Reuse `createMapOfRelatedList`. |
| `PRM_Relatedlistconfiguration__mdt.PRM_CaseManager_Record_Type__c` | New custom metadata field + seed rows | Pattern B / AC-5 | Do not overload `PRM_PDM_Manual_Request_Type__c` with PAR. |
| `PRM_ParFormCmaBatch` | Modified Apex | After collecting case-scoped HCPFs, also associate (1) the HCPF itself if missing, (2) `HealthcareFacilityId` even when that location’s Case Manager is another case, (3) facility-network and facility-taxonomy rows for those locations | Drives AC-3, AC-6. Still one primary lookup per CMA row (story 1429783 AC5). Do not update `HealthcareFacility.PRM_CaseManager__c` or the vendor Account Case Manager. |
| `PRM_CaseManagerRelatedListControllerTest` | Modified Apex test | Replace `testFetchCMARecordsForParCaseManagerNoPdmType` so a PAR/PNC Case Manager **with** CMA rows returns a **non-empty** map (Practitioners / Accounts at minimum) | Today this test asserts `result.isEmpty()` and locks the regression. |
| `PRM_ParFormCmaCreationTest` / new helper test | Modified / new Apex test | Cover existing-location walk: HCPF stamped to this CM, facility stamped to another CM → CMA rows for HCPF + facility + networks; facility Case Manager unchanged | Drives AC-3, AC-6. ≥85% on new helper. |
| `PRM_CaseManagerRecordPage.flexipage-meta.xml` | No change | Visibility already switches on `PRM_UseCaseManagerAssociation__c` | Do not add a third Related tab. |
| `prmCaseManagerRelatedList` LWC | No functional change expected | Empty state stays for a true empty map | If QA wants a spinner until associations finish, that is a follow-up (CQ-1). |
| Backfill | One-time / ops | Re-run PAR CMA creation for existing PNC/PAR cases with the flag true that are missing location associations (e.g. analog IA-0000192693 and defect IA-0000157071 in the bug org) | Idempotent via `PRM_CMAService`. |

**CMA record type → related list (PAR/PNC)**

| CMA Record Type (DeveloperName) | Related list title |
|---|---|
| `PRM_Practitioner` | Practitioners |
| `PRM_Vendor` | Accounts |
| `PRM_PracticeLocation` | Practice Locations |
| `Practitioner_Practice_Location` | Practitioner Practice Locations |
| `Practice_Location_Network` | Practice Location Networks |
| `Practice_Location_Taxonomy` | Practice Location Taxonomies |
| `Business_License` | Business Licenses |
| `Identifier` | Identifiers |
| `PRM_Healthcare_Provider_NPI` | Healthcare Provider NPIs |

---

## Definition of done

- [ ] On a PNC Case Manager created by “new practitioner + existing PNC group”, Related shows practitioner, group, locations, practitioner-at-location, networks, taxonomies, licenses, and identifiers/NPIs (AC-1, AC-3).
- [ ] Same lists appear on a Practitioner Participation Case Manager that has Case Manager Associations (AC-2).
- [ ] Existing practice location and group Account still point at their original Case Manager (AC-3, AC-6).
- [ ] PDM Manual Change and Provider Change Related tabs are unchanged (AC-7).
- [ ] `testFetchCMARecordsForParCaseManagerNoPdmType` no longer asserts an empty map for PAR with associations.
- [ ] New Apex ≥ 85% coverage including the existing-location walk and the blank-PDM PAR path.
- [ ] Defect Case Manager in the bug’s QA org (screenshot IA-0000157071 / PNC / Katherine Marie Nicodemus) shows related records after deploy + association backfill.
- [ ] No regression to the standard Related tab when Use Case Manager Association is false (AC-4).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | If associations are still running when the specialist opens Related, should the tab show a loading state / “associations in progress”, or is a refresh after the batch finishes acceptable? | UX only; does not change mapping | Product |
| 2 | Should education, language, and contact-profile associations also get their own related lists, or is the AC-1 inventory enough? Analog PNC cases already have those CMA rows. | Extra MDT rows + mapping | Product |
| 3 | Confirm defect IA-0000157071 in the **bug’s** QA org (screenshot account Katherine Marie Nicodemus). Default `ibx-qa` auto-number IA-0000157071 is a different Non-Par Claims case. | QA evidence pack | QA |
| 4 | Backfill: all historical PNC/PAR cases with the CMA flag true, or only cases still in Application Review / Submitted? | Batch volume | Ops / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CaseManagerRelatedListController` | Apex | HIGH | New record-type branch; current blank-PDM return is the screenshot root cause |
| `PRM_CMRelatedListParHelper` | Apex (new) | HIGH | PAR/PNC mapping, modelled on Provider Change helper |
| `PRM_Relatedlistconfiguration__mdt` | Custom Metadata | MEDIUM | New field + PAR/PNC seed rows |
| `PRM_ParFormCmaBatch` | Apex | HIGH | Existing-location walk; without this, location lists stay empty |
| `prmCaseManagerRelatedList` | LWC | LOW | Consumes whatever map the controller returns |
| `PRM_CaseManagerRecordPage` | FlexiPage | LOW | No layout change |
| PDM / Provider Change Related tab | Apex | LOW | Must keep existing branches first |
| `PRM_CMAService` | Apex | LOW | Reused for idempotent insert; no contract change expected |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Related-list controller branch | Apex | M | Follows existing Provider Change `if` |
| `PRM_CMRelatedListParHelper` | New Apex + tests | L | Same shape as `PRM_CMRelatedListPCFHelper` |
| Related-list configuration field + seeds | Custom Metadata | M | 9 list rows, reuse column strings |
| `PRM_ParFormCmaBatch` existing-location walk | Apex + tests | L | Walk HCPF → facility → facility Nw/Tx; do not restamp |
| Invert PAR empty-map test | Apex test | S | Currently certifies the bug |
| Backfill run in QA | Ops / anonymous Apex | M | Re-enqueue PAR CMA for affected Submitted PNC/PAR cases |

**Total Estimated Effort:** ~2 days — **XL** (AI-estimated — validate with team)

**Story points (optional):** 5
