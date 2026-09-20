# PRM PNC Logic Change & Field Migration – Implementation Plan

---

> **⚠️ Revision (Jul 2026) — two changes supersede parts of this plan below:**
> 1. **`PRM_PNCAnyLocation__c` (ALL/ANY switch) is replaced by `PRM_BypassPNC__c` (bypass switch).** The "any location" mode is removed; see `PRM_PNCAnyLocation_DataModel_User_Story.md`. The Quick Reference table and ANY/ALL wording throughout this plan are **stale** and pending a rename pass.
> 2. **Override/Bypass = force INTO PNC → blank `PRM_CredentialingStatus__c` AND `PRM_ReCredDueDate__c`; revert within 30 days (if previously "Credentialed") restores both from field history.** This replaces the earlier "bypass keeps Credentialed" assumption. Owned by `PRM_PNC_CredentialingStatus_Blank_User_Story.md`; implemented in `PRM_BypassPNC_UpdateFlow_User_Story.md`; recred-CM creation is correspondingly **reversed** (bypassed practitioners are excluded) in `Recred_BypassPNC_CaseManagerCreation_UserStory.md`.

## Quick Reference for Junior Developers

| Concept | Before | After |
|---------|--------|-------|
| **Where is PNC stored?** | Account (Vendor) | HealthcareFacility (practice location) |
| **Practitioner PNC rollup (default)** | True if **all** practice affiliations PNC | True if **all** participating practice locations PNC |
| **Practitioner PNC rollup (flag ON)** | n/a | True if **any** participating practice location PNC — when `Account.PRM_PNCAnyLocation__c = true` on the practitioner |
| **New per-practitioner flag** | n/a | `Account.PRM_PNCAnyLocation__c` (Checkbox, default false). Unchecked = ALL logic; checked = ANY logic |
| **Which HCPF record type?** | PRM_PractitionerPracticeAffiliation (Account) | PRM_PractitionerLocationAffiliation (HealthcareFacility) |
| **Trigger fires on** | Account (Vendor) update | HealthcareFacility update |
| **DataRaptor path** | `Account.PRM_PNC__c`, `Facility:Account.PRM_PNC__c` | `HealthcareFacility.PRM_PNC__c`, `Facility:PRM_PNC__c` |

> **⚠️ Logic direction (READ THIS FIRST):** The practitioner PNC rollup is **NOT** an unconditional "all → any" change (that would mirror the Delegated change). The **default remains ALL** — a practitioner is PNC only when **all** of their participating practice locations are PNC. A **new checkbox on the practitioner Account, `PRM_PNCAnyLocation__c`**, flips the logic to **ANY** (practitioner is PNC when **any** location is PNC) **only for practitioners where that flag is true**. Every rollup point (batch, triggers, participation/creation) must honor this per-practitioner flag. This corrects the earlier revision of these stories, which had unconditionally switched the rollup to "any".

**PNC + Delegated overlap:** When implementing both PNC and Delegated (PRM_DelegatedOnly → PRM_Delegated) changes, see `PRM_DelegatedOnly_to_PRM_Delegated_User_Stories.md` for the overlap table. Flows 1–5 (PDM, Provider Change, Off-Cycle, Termination, Demographics) touch both; implement together where possible.

**Key files to modify:**
- `PRM_RCATTerminationBatchHelper.cls` – `pncOnlyPractitioner()`
- `PRM_CommonUtils.cls` – `updateAccountPNCHelper()`, `getPIdToHCPFList()`
- `PRM_AccountTriggerHelper.cls` – remove/change `updateAccountPNC` for Vendor
- New: `HealthcareFacility` trigger for PNC rollup
- ~40 DataRaptors in `vlocity_export/DataRaptor/`
- Integration Procedures: `PRM_RecredTerminationLetter`, `PRM_VerifyPractitionerDetails`, `PRM_GetRelatedDataforPNCAndDelegatedRCATReview`
- **New field (US1):** `Account.PRM_PNCAnyLocation__c` (Checkbox, default false) on the Practitioner record type – the per-practitioner switch that flips the rollup from ALL (default) to ANY.
- **Practitioner Participation flow (US3):** `PRM_PractitionerScreenRecordCreation` (SV_PNCFlag, PNCFlag), `PRM_IPExtractGroupNameBasedOnTINNPI`, `PRMDRCreateCaseCaseManagerAndAccount` – PNC from practice locations; default practitioner PNC = true only if **all** joining locations are PNC (existing SV_PNCFlag "all groups PNC" semantics, retargeted to practice locations); when the practitioner's `PRM_PNCAnyLocation__c = true`, practitioner PNC = true if **any** joining location is PNC; case manager Record Type = PNC when practitioner is PNC. Does **not** use getPIdToHCPFList or updateAccountPNCHelper.
- **RCAT / Triggers (US4):** `pncOnlyPractitioner`, `updateAccountPNCHelper`, `getPIdToHCPFList` – used by Account trigger and PracFacility trigger; all must read the practitioner's `PRM_PNCAnyLocation__c` and apply ALL (default) vs ANY (flag on) logic per practitioner

---

## Executive Summary

This document describes the implementation of two related changes to the PNC (Par Non Cred) functionality:

1. **Field Migration:** Move the PNC flag from **Account** (vendor) to **HealthcareFacility** (practice location).
2. **Configurable Rollup Logic:** The practitioner PNC rollup **keeps its current default** — a practitioner is PNC only when **all** of their participating practice locations are PNC. A **new per-practitioner checkbox, `Account.PRM_PNCAnyLocation__c`**, flips the rollup to **ANY** (practitioner is PNC when **any** location is PNC) for practitioners where that flag is true.

> **Important — this differs from the PRM_DelegatedOnly → PRM_Delegated change.** Delegated was an unconditional "all → any" switch. PNC is **not**: the default stays "all", and "any" applies **only** when `PRM_PNCAnyLocation__c` is checked on the practitioner. An earlier revision of these stories incorrectly made PNC an unconditional "any" rollup; this version corrects that.

---

## Part 1: Background & Current State

### 1.1 What is PNC?

**PNC** = **Par Non Cred** (Participating Non-Credentialed). It indicates that a practice or practitioner participates in the network without full individual credentialing—typically through a group/vendor affiliation.

### 1.2 Current Data Model

| Object | Field | Purpose |
|--------|-------|---------|
| **Account** (Vendor/Group) | `PRM_PNC__c` | Indicates the practice/vendor is a PNC group |
| **Account** (Practitioner) | `PRM_PNC__c` | Rollup: true only when **all** practice affiliations have PNC = true |

### 1.3 Current Logic (All = PNC)

- **Practitioner PNC rollup:** Practitioner `PRM_PNC__c = true` only when **all** of their practice affiliations (via `HealthcarePractitionerFacility` RecordType `PRM_PractitionerPracticeAffiliation`) have `Account.PRM_PNC__c = true`.
- **Practitioner PNC rollup:** If **any** affiliation has `Account.PRM_PNC__c = false` → Practitioner `PRM_PNC__c = false`.
- **Source of PNC:** The `Account` (vendor) on `HealthcarePractitionerFacility` when RecordType = `PRM_PractitionerPracticeAffiliation`.

### 1.4 Data Model Context

- **HealthcareFacility** = Physical practice location (address, NPI, etc.). Has `AccountId` lookup to the Vendor/Group Account.
- **HealthcarePractitionerFacility** = Junction linking Practitioner (Contact) to either:
  - **Account** (vendor) when RecordType = `PRM_PractitionerPracticeAffiliation`
  - **HealthcareFacility** (location) when RecordType = `PRM_PractitionerLocationAffiliation`
- **Delegated** is already on `HealthcareFacility.PRM_IsDelegated__c` (practice location level).

---

## Part 2: Target State

### 2.1 New Data Model

| Object | Field | Purpose |
|--------|-------|---------|
| **HealthcareFacility** | `PRM_PNC__c` (new) | Indicates this practice location is PNC |
| **Account** (Practitioner) | `PRM_PNC__c` (keep) | Rollup: computed from participating practice locations. Default: true when **all** locations PNC. If `PRM_PNCAnyLocation__c = true`: true when **any** location PNC |
| **Account** (Practitioner) | `PRM_PNCAnyLocation__c` (new) | Per-practitioner switch. Unchecked (default) = ALL logic; checked = ANY logic |

### 2.2 New Logic (Configurable: ALL default, ANY when flag is on)

- **Source of PNC:** `HealthcareFacility.PRM_PNC__c` (practice location level).
- **Default rollup (flag OFF — `PRM_PNCAnyLocation__c = false`/blank):** Practitioner `PRM_PNC__c = true` **only when all** of their participating practice locations (via `HealthcarePractitionerFacility` with a `HealthcareFacility`, RecordType `PRM_PractitionerLocationAffiliation`, `IsActive = true`) have `HealthcareFacility.PRM_PNC__c = true`. If **any** participating location is non-PNC → practitioner `PRM_PNC__c = false`.
- **Flag rollup (flag ON — `PRM_PNCAnyLocation__c = true`):** Practitioner `PRM_PNC__c = true` when **any** participating practice location has `HealthcareFacility.PRM_PNC__c = true`.
- **No participating locations:** Practitioner `PRM_PNC__c = false` (both modes).
- **Where the flag is read:** every rollup point — RCAT batch (`pncOnlyPractitioner`), triggers (`updateAccountPNCHelper`/`getPIdToHCPFList`), the HealthcareFacility trigger (US5), future-dated processing, and the Participation/Creation flow (US3) — must read `PRM_PNCAnyLocation__c` for each practitioner and branch accordingly.

### 2.3 Migration Path

1. Add `PRM_PNC__c` to HealthcareFacility and `PRM_PNCAnyLocation__c` to Account (Practitioner).
2. Migrate data: For each HealthcareFacility, set `PRM_PNC__c = Account.PRM_PNC__c` (copy from parent vendor). `PRM_PNCAnyLocation__c` defaults to false for all practitioners (existing behavior = ALL logic preserved).
3. Update all Apex, DataRaptors, IPs, and OmniScripts to read/write PNC from HealthcareFacility.
4. Switch the rollup **source** from Account to HealthcareFacility, **keep the default ALL logic**, and make it branch to ANY when `PRM_PNCAnyLocation__c = true`.
5. Deprecate `PRM_PNC__c` on Account (vendor) after migration and validation.

---

## Part 3: Impact Analysis

### 3.1 Objects & Fields

| Area | Impact |
|------|--------|
| **HealthcareFacility** | Add `PRM_PNC__c` (Checkbox) |
| **Account** | Remove `PRM_PNC__c` from Vendor record type; keep `PRM_PNC__c` on Practitioner for rollup; **add `PRM_PNCAnyLocation__c` (Checkbox)** on Practitioner as the ALL/ANY switch |
| **DataRaptors** | ~40 DataRaptors reference Account.PRM_PNC__c; must change to HealthcareFacility.PRM_PNC__c or appropriate path |

### 3.2 Apex Classes

| Class | Change |
|-------|--------|
| PRM_RCATTerminationBatchHelper | `pncOnlyPractitioner()`: Switch source to HealthcareFacility.PRM_PNC__c via PRM_PractitionerLocationAffiliation; **keep ALL as the default**, branch to ANY per practitioner when `PRM_PNCAnyLocation__c = true` |
| PRM_CommonUtils | `updateAccountPNCHelper()`: Trigger when HealthcareFacility.PRM_PNC__c changes; rollup from locations to practitioner; ALL (default) vs ANY (flag) per practitioner |
| PRM_AccountTriggerHelper | `updateAccountPNC()`: Trigger on HealthcareFacility (new) instead of Account |
| PRM_FutureDatedProcessingBatchHandler | Use HealthcareFacility.PRM_PNC__c; update pncOnlyPractitioner logic |
| PRM_CheckCAQHAccessOnDueAccountsBatch | No change to filter (still uses practitioner Account.PRM_PNC__c) |
| PRM_FetchPractTermDataHandler | Practitioner PNC comes from rollup; no change |
| PRM_OffCycleProviderSearch, PRM_PARProviderSearch | Read from practitioner Account (rollup) or facility; update facility PNC source |
| PRM_IPUtilityHelper | Change `hcfRecord.Account.PRM_PNC__c` to `hcfRecord.PRM_PNC__c` (HealthcareFacility) |
| PRM_AncillaryProviderUtilsService | Same |
| PRM_PractitionerTerminationBatchHelper | Update query to use HealthcareFacility.PRM_PNC__c where applicable |

### 3.3 OmniStudio (DataRaptors, IPs, OmniScripts)

- **DataRaptors:** Update `InputFieldName`/`OutputFieldName` from `Account.PRM_PNC__c` to `HealthcareFacility.PRM_PNC__c` (or `Facility.PRM_PNC__c` depending on JSON structure).
- **Integration Procedures:** Update formulas referencing `Account:PRM_PNC__c` to use `HealthcareFacility:PRM_PNC__c` or equivalent.
- **OmniScripts:** Update any direct field references; most flow through DataRaptors.

### 3.4 Trigger Logic

- **Current:** Account trigger on Vendor Account when `PRM_PNC__c` changes → rollup to practitioners (ALL logic). The PPL trigger (`PRM_PracFacilityTriggerHandler.updateAccountPNC`) already rolls up on HCPF insert / IsActive change (ALL logic, vendor source).
- **New (location PNC change):** HealthcareFacility trigger when `PRM_PNC__c` changes → find practitioners linked via HealthcarePractitionerFacility (PRM_PractitionerLocationAffiliation) → for each practitioner, recalculate PNC using ALL (default) or ANY (when that practitioner's `PRM_PNCAnyLocation__c = true`) → update practitioner Account.PRM_PNC__c. See US5 §5.1.
- **Kept & updated (practitioner added/removed):** PPL trigger `PRM_PracFacilityTriggerHandler` recomputes when a practitioner is added (insert), activated/deactivated (IsActive change), or removed (add PNC recompute to `afterDelete`) on a location — now switch-aware and sourced from `HealthcareFacility.PRM_PNC__c`. See US5B §5B.1.
- **Also (switch change):** when `PRM_PNCAnyLocation__c` itself changes on a practitioner Account, the rollup must be recomputed for that practitioner (the switch can flip PNC without any location changing). See US5 §5.1a.

---

## Part 4: User Stories

The following user stories are written in **Given / When / Then** format for a junior OmniStudio/Salesforce developer. They are grouped by persona and dependency order.

---

# USER STORY 1: Data Model – Add PNC Field to Practice Location

**Persona:** Admin  
**Priority:** P0 (Must be done first)

## Story

**As an** Admin,  
**I want to** add the PNC field to the HealthcareFacility (practice location) object,  
**So that** PNC can be tracked at the practice location level instead of the vendor account level.

## Acceptance Criteria (Given / When / Then)

### AC1: Create the field

**Given** the HealthcareFacility object exists in the org,  
**When** the Admin creates a new custom field on HealthcareFacility,  
**Then** the field shall have the following configuration:
- **API Name:** `PRM_PNC__c`
- **Type:** Checkbox
- **Default Value:** Unchecked (false)
- **Label:** PNC (Par Non Cred)
- **Description:** Indicates this practice location participates in the network without full individual credentialing (Par Non Cred). When true, practitioners affiliated with this location may be considered PNC for rollup purposes.
- **Required:** No
- **Field-Level Security:** Same as current Account.PRM_PNC__c (Credentialing Specialist, PDM Specialist, Admin)
- **Page Layout:** Add to relevant HealthcareFacility page layouts where practice location details are edited

### AC2: Add to page layout

**Given** the PRM_PNC__c field exists on HealthcareFacility,  
**When** the Admin edits the HealthcareFacility page layout(s) used for practice location management,  
**Then** the PNC (Par Non Cred) checkbox shall appear in the appropriate section (e.g., Participation or Credentialing section).

### AC3: Add to list views and reports

**Given** the field is created,  
**When** the Admin configures list views or reports that show practice location PNC status,  
**Then** the field shall be available for filtering and display.

### AC4: Create the per-practitioner ALL/ANY switch field

> **Now maintained as a standalone data-model story:** see `requirements/PRM_PNCAnyLocation_DataModel_User_Story.md` for the full field spec, FLS, and layout ACs. AC4/AC5 below are kept as a summary.

**Given** the practitioner is stored as a Person Account,  
**When** the Admin creates a new custom field on Account,  
**Then** the field shall have the following configuration:
- **API Name:** `PRM_PNCAnyLocation__c`
- **Type:** Checkbox
- **Default Value:** Unchecked (false) — preserves the existing ALL behavior for all current practitioners
- **Label:** PNC – Any Location
- **Description:** Controls how the practitioner's PNC rollup is computed. When **unchecked (default)**, the practitioner is PNC only when **all** of their participating practice locations are PNC. When **checked**, the practitioner is PNC when **any** of their participating practice locations is PNC.
- **Applies to:** Practitioner record type only (not Vendor/Group)
- **Field-Level Security:** Same audience that manages practitioner credentialing (Credentialing Specialist, PDM Specialist, Admin) — editable; read-only for others as appropriate
- **Page Layout:** Add to the Practitioner Account layout in the credentialing/participation section

### AC5: Do not backfill the switch

**Given** the migration preserves current behavior,  
**When** `PRM_PNCAnyLocation__c` is deployed,  
**Then** it shall remain **false** for all existing practitioners (no data backfill), so the rollup continues to behave as "all locations PNC" until a practitioner is explicitly flagged for "any" logic.

---

# USER STORY 2: Data Model – Data Migration Script

**Persona:** Admin  
**Priority:** P0  
**Depends on:** User Story 1

## Story

**As an** Admin,  
**I want to** migrate existing PNC data from Account to HealthcareFacility,  
**So that** each practice location has the correct PNC value before we switch the application logic.

## Acceptance Criteria (Given / When / Then)

### AC1: Migration logic

**Given** Account (Vendor) records have PRM_PNC__c populated,  
**And** HealthcareFacility records have AccountId lookup to the Vendor Account,  
**When** the migration script runs,  
**Then** for each HealthcareFacility:
- If the HealthcareFacility has an AccountId (vendor),
- Set `HealthcareFacility.PRM_PNC__c = Account.PRM_PNC__c` (from the parent vendor)
- If the Account has no PNC value (null), set HealthcareFacility.PRM_PNC__c = false

### AC2: Validation

**Given** the migration has run,  
**When** the Admin runs a validation query,  
**Then** the count of HealthcareFacility records with PRM_PNC__c = true shall match (or be a superset of) the count of Vendor Accounts that had PRM_PNC__c = true and have at least one HealthcareFacility.

### AC3: Rollback plan

**Given** a need to rollback,  
**When** the migration is rolled back,  
**Then** the script shall not delete or modify the new HealthcareFacility.PRM_PNC__c field; it may be left as-is. The old Account.PRM_PNC__c remains until User Story 11 (deprecation).

---

# USER STORY 3: Practitioner Participation Form – PNC Determination and Case Manager Creation

**Persona:** Developer (OmniStudio)  
**Priority:** P0  
**Depends on:** User Story 1, 2

## Story

**As an** OmniStudio/Salesforce developer,  
**I want to** update the Practitioner Participation Form flow so that PNC is determined from practice locations (HealthcareFacility) instead of groups (Account), keeping the current **default** where the practitioner is PNC only when **all** joining practice locations are PNC, while honoring the per-practitioner `PRM_PNCAnyLocation__c` switch that flips the rule to **any** location,  
**So that** the case manager created after submission uses Record Type PNC when the practitioner qualifies under the applicable (ALL default / ANY when flag on) rule.

**Creation-time note:** at onboarding the practitioner Account may not exist yet, so the flag defaults to **false → ALL logic** unless the practitioner's `PRM_PNCAnyLocation__c` is already set (e.g., existing practitioner) or provided. The existing `SV_PNCFlag` already implements "all groups PNC" (`PNCFalseFlagList = FILTER(GroupInformation,'pnc = false')` → PNC only when the list is empty); this ALL semantics is **retained** and simply retargeted to practice-location PNC. The HealthcareFacility trigger (US5) keeps the rollup correct after creation if the flag is later changed.

**Note:** This flow does **not** use `getPIdToHCPFList` or `updateAccountPNCHelper`. Those Apex methods are used by triggers (Account, PracFacility) and are covered in User Story 4 (RCAT). The Practitioner Participation flow uses **Apex** (`PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI`) via IP Remote Actions to fetch group data (including the `pnc` property), plus Integration Procedures and DataRaptors to compute PNCFlag and write to Account.PRM_PNC__c at creation time.

## Acceptance Criteria (Given / When / Then)

### AC1: PNC determination – keep "all locations PNC" default; source from practice location; honor the ANY switch

**Given** the Practitioner Participation Form (PRM_PractitionerParticipationForm_English) is used to onboard PNC practitioners,  
**And** the flow currently checks if the practitioner is joining PNC-only accounts (groups) and sets the practitioner's PNC checkbox accordingly; the case manager created after submission uses Record Type "PNC" when the practitioner is PNC,  
**When** the developer updates the flow for the new data model (PNC on practice location),  
**Then** the logic shall change as follows:

**Current behavior:**
- Groups selected in the flow have a `pnc` property from the vendor Account (Account.PRM_PNC__c).
- SV_PNCFlag (PRM_PractitionerScreenRecordCreation) filters GroupInformation for `pnc = false` (`PNCFalseFlagList`).
- PNCFlag is derived: practitioner is PNC only when **all** groups they join have `pnc = true` (i.e., `PNCFalseFlagList` is empty).
- PRMDRCreateCaseCaseManagerAndAccount uses PNCFlag to set Account.PRM_PNC__c on the practitioner and to set the IndividualApplication RecordType to PNC.

**New behavior:**
- PNC is on HealthcareFacility (practice location), not Account (vendor). The `pnc` property on each entry in GroupInformation must be **sourced from practice-location PNC** (`HealthcareFacility.PRM_PNC__c`), not the vendor Account.
- **Default (ALL — practitioner `PRM_PNCAnyLocation__c` is false/blank):** keep the existing "all" rule. The practitioner is PNC (PNCFlag = true) only when **all** joining practice locations are PNC — i.e., `PNCFalseFlagList` (locations with `pnc = false`) is **empty**. This is the current SV_PNCFlag behavior, unchanged except for the data source.
- **Flag ON (ANY — practitioner `PRM_PNCAnyLocation__c` is true):** the practitioner is PNC (PNCFlag = true) when **any** joining practice location is PNC — i.e., there is **at least one** entry with `pnc = true` (equivalently, a `PNCTrueFlagList = FILTER(GroupInformation,'pnc = true')` is non-empty).
- When PNCFlag = true, the case manager created after submission shall use Record Type PNC.
- When PNCFlag = false, the case manager shall use the non-PNC record type (e.g., Application Review).
- **Determining the switch at creation:** if the practitioner already exists (re-participation), read `Account.PRM_PNCAnyLocation__c`. For brand-new practitioners with no existing Account, use the **default ALL** rule unless the flag value is passed into the flow. Persist the flag on the created/updated practitioner Account so US4/US5 rollups stay consistent.

### AC2: PRM_PractitionerScreenRecordCreation – SV_PNCFlag and PNCFlag formula

**Given** SV_PNCFlag filters GroupInformation for `pnc = false` and uses `PNCFalseFlagList` (today: PNCFlag = true when this list is empty → "all groups PNC"),  
**When** the developer updates the Integration Procedure,  
**Then** the logic shall evaluate practice locations (HealthcareFacilities) instead of groups (Accounts) and become **switch-aware**:
- `GroupInformation[].pnc` must be sourced from `HealthcareFacility.PRM_PNC__c` (the GroupInformation structure must carry practice-location PNC, or a separate IP/DataRaptor must fetch practice locations for the selected groups and populate `pnc` per location).
- Read the practitioner's `PRM_PNCAnyLocation__c` (existing Account) or the value passed into the flow; default to **false** for brand-new practitioners.
- **Default (flag false):** keep `PNCFalseFlagList = FILTER(LIST(%...GroupInformation%),'pnc = false')`; `PNCFlag = (SIZE(PNCFalseFlagList) == 0)` — true only when **all** locations are PNC.
- **Flag true:** add `PNCTrueFlagList = FILTER(LIST(%...GroupInformation%),'pnc = true')`; `PNCFlag = (SIZE(PNCTrueFlagList) > 0)` — true when **any** location is PNC.
- Implement as a single formula that picks the branch based on the switch, e.g. `PNCFlag = IF(%PNCAnyLocation% == true, SIZE(PNCTrueFlagList) > 0, SIZE(PNCFalseFlagList) == 0)`. The resulting PNCFlag is passed to PRMDRCreateCaseCaseManagerAndAccount as today.

### AC3: PRM_IPExtractGroupNameBasedOnTINNPI – Apex and DataRaptors

**Given** the IP fetches group data via Remote Actions RAGetUniqueGroupsForPNCTaxIdNPI and RAGetUniqueGroupsForTaxIdNPI (both call `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI`),  
**And** the DataRaptor PRMDRExtractGroupNameBasedOnTINNPIPNC may be used in other contexts and maps Account.PRM_PNC__c → Account:PNC,  
**When** the developer updates the group data source for PNC removal from Account,  
**Then**:
- **Apex:** `PRM_RecordQueryServiceUtils.getAccount` and `getAccountWrapperData` must derive the group-level PNC from HealthcareFacility.PRM_PNC__c (true if any practice location under the group has PNC = true) instead of reading Account.PRM_PNC__c.
- **DataRaptor (if used):** PRMDRExtractGroupNameBasedOnTINNPIPNC must be updated to derive PNC from HealthcareFacility instead of Account.
- The GroupInformation structure used by SV_PNCFlag must support the new evaluation (pnc = true when any practice location under the group is PNC).

### AC4: PRMDRCreateCaseCaseManagerAndAccount – no structural change

**Given** the DataRaptor receives PNCFlag and writes to Account.PRM_PNC__c and sets IndividualApplication RecordType,  
**When** the developer reviews the DataRaptor,  
**Then** no change to the DataRaptor input/output structure is required. The PNCFlag value is computed differently upstream (AC1–AC3). The DataRaptor continues to receive PNCFlag and write Account.PRM_PNC__c (practitioner) and set case type based on PNCFlag.

### AC5: IsPNCGroup (PractitionerParticipationForm) – OmniScript elements and group data source

**Given** IsPNCGroup is set by PractitionerParticipationQuestion5 ("Yes" = joining PNC group),  
**When** the developer reviews the flow,  
**Then** the following applies:

1. **IsPNCGroup (PractitionerParticipationQuestion5)** – No change. This is user intent only; it does not read from Account and does not depend on Account.PRM_PNC__c.

2. **GroupInformation.pnc** – When PNC is removed from Account, the source of the `pnc` property for each group **must** change. Today, `pnc` comes from Account.PRM_PNC__c via:
   - **Apex:** `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI` → `getAccountWrapperData` puts `accountWrap.put('PNC', acc.prm_pnc__c)`. The IP uses Remote Actions (RAGetUniqueGroupsForPNCTaxIdNPI, RAGetUniqueGroupsForTaxIdNPI) that call this Apex, not the DataRaptor.
   - **DataRaptor (if used elsewhere):** `PRMDRExtractGroupNameBasedOnTINNPIPNC` maps `Identifier:Account:PRM_PNC__c` → `Account:PNC`.

3. **Required change when PNC is removed from Account:** The group data source (Apex and/or DataRaptor) must derive the group-level PNC from HealthcareFacility.PRM_PNC__c: for each group (vendor Account), PNC = true if **any** HealthcareFacility under that Account has PRM_PNC__c = true. The OmniScript `pnc` formula element and SV_PNCFlag continue to use GroupInformation.pnc; the formula logic does not change, but the **data source** must be updated.

---

# USER STORY 4: RCAT / Apex – Practitioner PNC Rollup Logic (Any vs All)

**Persona:** Developer (Apex)  
**Priority:** P0  
**Depends on:** User Story 1, 2

## Story

**As an** OmniStudio/Salesforce developer,  
**I want to** switch the practitioner PNC rollup **source** from vendor Account to practice location (HealthcareFacility) in RCAT batch processing, triggers, and related Apex, **keeping the default "all locations PNC" rule** and adding a per-practitioner switch (`PRM_PNCAnyLocation__c`) that flips the rule to "any location PNC",  
**So that** a practitioner is PNC when **all** their practice locations are PNC by default, or when **any** location is PNC if they are explicitly flagged.

**Note:** This story covers: `pncOnlyPractitioner`, `updateAccountPNCHelper`, `getPIdToHCPFList`, and the HealthcareFacility trigger. These are used by **RCAT / batch / triggers**, not by the Practitioner Participation OmniScript.

> **Direction correction:** this is **not** an unconditional "all → any" change. The default remains **all**; "any" applies **only** to practitioners where `PRM_PNCAnyLocation__c = true`. What changes unconditionally is the **source** (Account.PRM_PNC__c → HealthcareFacility.PRM_PNC__c) and the **record type** (PRM_PractitionerPracticeAffiliation → PRM_PractitionerLocationAffiliation).

---

## Business Details (For Business Analysts & Stakeholders)

### What is RCAT?

**RCAT** = **Recredentialing Credentialing Action Tracking**. It is the process for reviewing and processing practitioners due for recredentialing who are flagged for termination (recred term).

### PRM_ReviewRCAT_English OmniScript – Three Steps

The RCAT review flow presents practitioners in three sequential steps. **PNC will be removed from Account (vendor)**; all PNC display and logic must use **HealthcareFacility.PRM_PNC__c** (practice location PNC) instead.

---

#### Step 1: Review PNC & Delegated

**Message:** *"Practitioners will only be termed from their Non-Delegated or Non-PNC Groups."*

| Aspect | Current (Before Change) | After Change |
|--------|-------------------------|--------------|
| **What is shown** | Practitioners in the PNC & Delegated bucket; each row has a **PNC** checkbox (read-only) | Same – practitioners with PNC/Delegated locations |
| **PNC data source** | `Account.PRM_PNC__c` (vendor-level PNC) via DataRaptors (PRMGetRelatedDataforPNCAndDelegatedRCATReview, PRMGetRelatedRecordForRCATReview, PRMGetPLVendorPNCRCAT) | **HealthcareFacility.PRM_PNC__c** (practice location PNC) |
| **Custom LWC** | CustomLWC1 displays the practitioner table; PNC value comes from Account.PRM_PNC__c in the JSON | **Must change:** Custom LWC must consume PNC from HealthcareFacility.PRM_PNC__c. DataRaptors and Apex must supply `HealthcareFacility.PRM_PNC__c` in the payload instead of Account.PRM_PNC__c |
| **Why this matters** | PNC checkbox is being removed from Account; if we continue to read Account.PRM_PNC__c, the PNC column will be empty or incorrect | Each practice location has its own PNC; the displayed PNC must reflect the location(s) the practitioner is affiliated with |

---

#### Step 2: Review Last Man Standing

**Message:** *Last Man Standing – practitioners who are the only active practitioner at a non-PNC, non-delegated location.*

| Aspect | Current (Before Change) | After Change |
|--------|-------------------------|--------------|
| **What is shown** | LMS practitioners; each row has **LMSPNC** checkbox (read-only) | Same – LMS practitioners |
| **PNC data source** | `HealthcareFacility.Account.PRM_PNC__c` via PRM_RCATProcessingHelper.assignLocationDerivedFields → PracLoc.pnc | **HealthcareFacility.PRM_PNC__c** |
| **Custom LWC** | CustomLWC2 displays the LMS table; PNC from PracLoc.pnc (Apex) | **Must change:** PRM_RCATProcessingHelper must set `loc.pnc` from `HealthcareFacility.PRM_PNC__c`; Custom LWC continues to consume PracLoc.pnc |

---

#### Step 3: Review RCAT – Not Last AND PNC Delegated Practitioner Locations

**Message:** *Not Last AND PNC Delegated – practitioners who have at least one other active practitioner at their locations, and whose locations include PNC or Delegated.*

| Aspect | Current (Before Change) | After Change |
|--------|-------------------------|--------------|
| **What is shown** | Practitioners in the Not Last AND PNC/Delegated bucket | Same |
| **PNC data source** | `Account.PRM_PNC__c` via PRMUpdateDataForRCATNLReview, PRMGetRelatedDataforPNCAndDelegatedRCATReview | **HealthcareFacility.PRM_PNC__c** |
| **Custom LWC** | CustomLWC3 displays the table; PNC from DataRaptor output | **Must change:** DataRaptors must supply HealthcareFacility.PRM_PNC__c; Custom LWC consumes updated payload |

---

### Summary: PNC Source Change Across All Steps

| Step | Current PNC Source | New PNC Source |
|------|--------------------|----------------|
| **Step 1: Review PNC & Delegated** | Account.PRM_PNC__c | HealthcareFacility.PRM_PNC__c |
| **Step 2: Review Last Man Standing** | HealthcareFacility.Account.PRM_PNC__c | HealthcareFacility.PRM_PNC__c |
| **Step 3: Not Last AND PNC Delegated** | Account.PRM_PNC__c | HealthcareFacility.PRM_PNC__c |

**Critical:** The Custom LWCs (CustomLWC1, CustomLWC2, CustomLWC3) display practitioners in tables. Today they receive PNC from Account or HealthcareFacility.Account. **We are removing the PNC checkbox from Account.** Therefore, all three steps must supply and display PNC from **HealthcareFacility.PRM_PNC__c** only.

### Other RCAT Components (Batch, Letter, Rollup)

| Component | Current | After Change |
|-----------|---------|--------------|
| **Batch processing** | pncOnlyPractitioner() uses Account.PRM_PNC__c, "all" logic | HealthcareFacility.PRM_PNC__c; **ALL by default, ANY when `PRM_PNCAnyLocation__c = true`** |
| **Practitioner PNC rollup** | Account.PRM_PNC__c = true only when **all** affiliations PNC | Account.PRM_PNC__c = true when **all** locations PNC (default), or when **any** location PNC if `PRM_PNCAnyLocation__c = true` |
| **Recred termination letter** | Excludes locations where Account.PRM_PNC__c = true | Excludes locations where HealthcareFacility.PRM_PNC__c = true (per-location exclusion; unaffected by the practitioner switch) |

---

## Technical Details (For Developers)

### 4.1 Apex Classes to Modify

| Class | Method / Area | Change |
|-------|---------------|--------|
| **PRM_RCATTerminationBatchHelper** | `pncOnlyPractitioner(Set<Id> practitionerIds)` | Switch from PRM_PractitionerPracticeAffiliation + Account.PRM_PNC__c to PRM_PractitionerLocationAffiliation + HealthcareFacility.PRM_PNC__c; **keep ALL as default**, branch to ANY per practitioner when `PRM_PNCAnyLocation__c = true` |
| **PRM_CommonUtils** | `updateAccountPNCHelper()` | Change source from Account.PRM_PNC__c to HealthcareFacility.PRM_PNC__c; ALL (default) vs ANY (flag) per practitioner |
| **PRM_CommonUtils** | `getPIdToHCPFList()` | Query HCPF with RecordType PRM_PractitionerLocationAffiliation; include HealthcareFacility.PRM_PNC__c instead of Account.PRM_PNC__c |
| **PRM_RCATProcessingHelper** | `populateLocationsForScreens()` | Line ~134: `loc.pnc = hcpf.HealthcareFacility.Account.PRM_PNC__c` → `loc.pnc = hcpf.HealthcareFacility.PRM_PNC__c` |
| **PRM_FutureDatedProcessingBatchHandler** | HCPF query and PNC evaluation | Use HealthcarePractitionerFacility with RecordType PRM_PractitionerLocationAffiliation and HealthcareFacility.PRM_PNC__c; align with updated pncOnlyPractitioner logic |

### 4.2 DataRaptors to Modify (RCAT-specific)

| DataRaptor | Item / Location | Current | Change |
|------------|-----------------|---------|--------|
| **PRMGetRelatedDataforPNCAndDelegatedRCATReview** | FormulaExpression (HealthcarePractitionerFacilityFiltered) | `(RecordType == "PRM_PractitionerPracticeAffiliation" && Account.PRM_PNC__c == false ...) \|\| (RecordType == "PRM_PractitionerLocationAffiliation" && Account.PRM_PNC__c == false ...)` | For PRM_PractitionerLocationAffiliation branch: use `HealthcareFacility.PRM_PNC__c == false` (or equivalent path). For PRM_PractitionerPracticeAffiliation: remove or migrate to Location Affiliation only |
| **PRMGetRelatedDataforPNCAndDelegatedRCATReview** | InputFieldName / OutputFieldName | `CaseManager:HealthcarePractitionerFacilityFiltered:Account.PRM_PNC__c` → `CaseManager:HealthcarePractitionerFacility:Account.PRM_PNC__c` | Change to `HealthcareFacility.PRM_PNC__c` or `HealthcareFacility:PRM_PNC__c` for Location Affiliation context |
| **PRMGetPLVendorPNCRCAT** | FormulaExpression (IsVendorPNC) | `IF(%CaseManagers:PractionerPracticeLocation:HCF:Account.PRM_PNC__c% == true, true, false)` | Change to `HCF:PRM_PNC__c` (HealthcareFacility.PRM_PNC__c) |
| **PRMGetPLVendorPNCRCAT** | InputObjectQuerySequence 1 (HealthcareFacility) | Queries HealthcareFacility by Id | Ensure query returns `PRM_PNC__c` from HealthcareFacility (add field to Extract if not present) |
| **PRMGetRelatedRecordForRCATReview** | InputFieldName | `CaseManagers:PractionerPracticeLocation:Account.PRM_PNC__c` → OutputFieldName `PractionerPracticeLocation:PracPNC` | For Location Affiliation: use `HealthcareFacility.PRM_PNC__c` or `PractionerPracticeLocation:HealthcareFacility.PRM_PNC__c` as input; output remains PracPNC |

### 4.3 Integration Procedures to Modify (RCAT-specific)

| Integration Procedure | Element | Change |
|-----------------------|---------|--------|
| **PRM_RecredTerminationLetter** | FilterHCPFRecords | `Account:PRM_PNC__c != true` → `HealthcareFacility:PRM_PNC__c != true` |
| **PRM_UpdateDataForRCATPNCReview** | PRMGetRelatedDataforPNCAndDelegatedRCATReview | Calls DataRaptor; no IP change if DataRaptor is updated |
| **PRM_ReviewRCATLoad** | PRMUpdateDataForRCATPNCReview | Calls PRM_UpdateDataForRCATPNCReview; no change if downstream DataRaptor updated |
| **PRM_ReviewRCAT** (IP – initial load) | PRMGetRelatedRecordForRCATReview | Calls DataRaptor; no IP change if DataRaptor updated. PRMGetRelatedRecordForRCATReview outputs PractionerPracticeLocation with PracPNC from Account.PRM_PNC__c → change to HealthcareFacility.PRM_PNC__c |

### 4.4 PRM_ReviewRCAT_English OmniScript – Component Details

| Element | Type | Step | PNC Impact | Change Required |
|---------|------|------|------------|-----------------|
| **SetInitialVariables** | Set Values | — | None | No change |
| **PRM_ReviewRCAT** | IP Action | — | Loads initial data | No change (data comes from Apex/DataRaptors) |
| **PRM_ReviewRcatRemote** | Remote Action | — | Batch submit | No change (Apex handles PNC) |
| **ReviewPNCAndDelegated** | Step | **Step 1** | Container for "Review PNC & Delegated" | No change |
| **PNCAndDelegated** | Edit Block | Step 1 | Displays practitioners; **PNC** checkbox (read-only) | Data source must be HealthcareFacility.PRM_PNC__c. Update DataRaptors (PRMGetRelatedDataforPNCAndDelegatedRCATReview, PRMGetRelatedRecordForRCATReview, PRMGetPLVendorPNCRCAT) |
| **PNC** | Checkbox | Step 1 | Displays PNC for each row | Binds to Edit Block row; data from DataRaptor – must be HealthcareFacility.PRM_PNC__c |
| **CustomLWC1** | Custom LWC | **Step 1** | Renders practitioner table for PNC & Delegated | **Must verify:** LWC consumes PNC from JSON. Today it may read Account.PRM_PNC__c. After change, payload must contain HealthcareFacility.PRM_PNC__c (or equivalent). LWC may need update if it explicitly references Account.PNC |
| **ReviewLastManStanding** | Step | **Step 2** | Container for "Review Last Man Standing" | No change |
| **LastManStanding** | Edit Block | Step 2 | Displays LMS practitioners; **LMSPNC** checkbox (read-only) | Data source: PRM_RCATProcessingHelper → PracLoc.pnc. Update assignLocationDerivedFields to use HealthcareFacility.PRM_PNC__c |
| **LMSPNC** | Checkbox | Step 2 | Displays PNC for LMS row | Binds to Edit Block row; data from Apex PracLoc.pnc |
| **CustomLWC2** | Custom LWC | **Step 2** | Renders LMS practitioner table | Consumes PracLoc.pnc from Apex; no LWC change if Apex supplies correct value |
| **ReviewNotLastANDPNCDelegated** | Step | **Step 3** | Container for "Not Last AND PNC Delegated Practitioner Locations" | No change |
| **NotLastANDPNCDelegated** | Edit Block | Step 3 | Displays practitioners | Data from PRMUpdateDataForRCATNLReview; PNC must come from HealthcareFacility.PRM_PNC__c |
| **CustomLWC3** | Custom LWC | **Step 3** | Renders Not Last AND PNC/Delegated table | **Must verify:** LWC consumes PNC from JSON. Payload must supply HealthcareFacility.PRM_PNC__c |
| **PRM_ReviewRCATLoadParent** | IP Action | — | Loads data when user navigates | No change |
| **DataMapperTransformAction1, 2, 3** | Transform | All | Maps data for each bucket | Verify transform does not hardcode Account.PRM_PNC__c |

**Data flow summary:**
- **LMS / Last Man Standing:** Data from `PRM_RCATProcessingController.getRCATRecords()` → `PRM_RCATProcessingService.screenRecords()` → `PRM_RCATProcessingHelper.populateLocationsForScreens()` → `PracLoc.pnc` from `HealthcareFacility.Account.PRM_PNC__c` (today). **Change:** `HealthcareFacility.PRM_PNC__c`.
- **PNC & Delegated / Not Last:** Data from `PRM_ReviewRCATLoad` → `PRM_UpdateDataForRCATPNCReview` → `PRMGetRelatedDataforPNCAndDelegatedRCATReview` (DataRaptor) → filters and outputs HCPF with `Account.PRM_PNC__c`. **Change:** DataRaptor filter and output to use `HealthcareFacility.PRM_PNC__c`.
- **PRMGetPLVendorPNCRCAT:** Used in PRM_UpdateDataForRCATPNCReview or PRMGetRelatedRecordForRCATReview flow; formula uses `HCF:Account.PRM_PNC__c`. **Change:** `HCF:PRM_PNC__c`.

### 4.5 pncOnlyPractitioner – Logic Change

| Aspect | Current | New |
|--------|---------|-----|
| **HCPF RecordType** | PRM_PractitionerPracticeAffiliation (Account) | PRM_PractitionerLocationAffiliation (HealthcareFacility) |
| **PNC field** | Account.PRM_PNC__c | HealthcareFacility.PRM_PNC__c |
| **Logic (default, `PRM_PNCAnyLocation__c = false`)** | Start true; set false if any affiliation has PNC = false | **Unchanged rule, new source:** Start true; set false if any **location** has HealthcareFacility.PRM_PNC__c = false |
| **Logic (flag on, `PRM_PNCAnyLocation__c = true`)** | n/a | Start false; set true if any **location** has HealthcareFacility.PRM_PNC__c = true |
| **Practitioner with no affiliations/locations** | Note: today returns false when no affiliations | Remains false (both modes) |

### 4.6 Files to Create/Modify

| File | Action |
|------|--------|
| `PRM_RCATTerminationBatchHelper.cls` | Modify – pncOnlyPractitioner |
| `PRM_CommonUtils.cls` | Modify – updateAccountPNCHelper, getPIdToHCPFList |
| `PRM_RCATProcessingHelper.cls` | Modify – assignLocationDerivedFields (lines 133–135): `loc.pnc = hcpf.HealthcareFacility.PRM_PNC__c`; add HealthcareFacility.PRM_PNC__c to SOQL (line 69) |
| `PRM_FutureDatedProcessingBatchHandler.cls` | Modify – HCPF query, PNC evaluation |
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview` (DataRaptor) | Modify – FormulaExpression, InputFieldName, OutputFieldName for PNC |
| `PRMGetPLVendorPNCRCAT` (DataRaptor) | Modify – FormulaExpression: HCF:PRM_PNC__c; ensure HealthcareFacility query returns PRM_PNC__c |
| `PRMGetRelatedRecordForRCATReview` (DataRaptor) | Modify – InputFieldName: PractionerPracticeLocation:Account.PRM_PNC__c → HealthcareFacility.PRM_PNC__c (or equivalent path for Location Affiliation) |
| `PRM_RecredTerminationLetter` (IP) | Modify – FilterHCPFRecords |
| `PRM_ReviewRCAT_English` (OmniScript) | No direct changes – PNC display elements (PNC, LMSPNC) consume data from Apex/DataRaptors |
| **CustomLWC1, CustomLWC2, CustomLWC3** (LWC) | **Verify:** LWCs display practitioners; ensure they consume PNC from HealthcareFacility.PRM_PNC__c (or PracLoc.pnc for Step 2). If LWCs reference Account.PRM_PNC__c, update to use practice location PNC |
| Test classes | Update for pncOnlyPractitioner, updateAccountPNCHelper, getPIdToHCPFList, PRM_RCATProcessingHelper |

**Note:** The HealthcareFacility trigger for PNC rollup is covered in **User Story 5**. User Story 4 focuses on the RCAT batch and helper logic that runs during RCAT processing and future-dated batch jobs.

---

## Acceptance Criteria (Given / When / Then)

### AC1: pncOnlyPractitioner – switch source to HealthcareFacility; ALL default, ANY when flag on

**Given** the method `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner(Set<Id> practitionerIds)` exists,  
**And** it currently uses HealthcarePractitionerFacility with RecordType `PRM_PractitionerPracticeAffiliation` and Account.PRM_PNC__c with "all" logic,  
**When** the developer updates the method to use HealthcarePractitionerFacility with RecordType `PRM_PractitionerLocationAffiliation` and HealthcareFacility.PRM_PNC__c **and to honor the per-practitioner `PRM_PNCAnyLocation__c` switch**,  
**Then** the logic shall be:
- Load each practitioner's `PRM_PNCAnyLocation__c` (query the practitioner Person Accounts by PersonContactId, or include it via the HCPF `Practitioner.Account.PRM_PNCAnyLocation__c`).
- Query active location affiliations: HCPF where RecordType = `PRM_PractitionerLocationAffiliation`, IsActive = true, with `HealthcareFacility.PRM_PNC__c`.
- **Default (flag false) — ALL:** initialize `true`; set `false` when any location has `PRM_PNC__c = false`; practitioners with no locations → `false`.
- **Flag true — ANY:** initialize `false`; set `true` when any location has `PRM_PNC__c = true`; practitioners with no locations → `false`.

**Pseudocode:**
```apex
// Map of practitionerId -> PRM_PNCAnyLocation__c (default false)
Map<Id, Boolean> anyLocationFlag = getPncAnyLocationFlag(practitionerIds);

Set<Id> practitionersWithLocations = new Set<Id>();

// Seed defaults per the switch: ALL starts true, ANY starts false
for (Id pid : practitionerIds) {
    practitionerPNCMap.put(pid, anyLocationFlag.get(pid) == true ? false : true);
}

for (HealthcarePractitionerFacility hpf : [SELECT PractitionerId, HealthcareFacility.PRM_PNC__c
    FROM HealthcarePractitionerFacility
    WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
    AND PractitionerId IN :practitionerIds
    AND IsActive = true
    WITH SYSTEM_MODE]) {

    practitionersWithLocations.add(hpf.PractitionerId);
    Boolean isAny = anyLocationFlag.get(hpf.PractitionerId) == true;
    Boolean locPnc = hpf.HealthcareFacility.PRM_PNC__c == true;

    if (isAny) {
        if (locPnc) { practitionerPNCMap.put(hpf.PractitionerId, true); }   // ANY: one PNC location is enough
    } else {
        if (!locPnc) { practitionerPNCMap.put(hpf.PractitionerId, false); } // ALL: one non-PNC location disqualifies
    }
}

// No participating locations -> false in both modes
for (Id pid : practitionerIds) {
    if (!practitionersWithLocations.contains(pid)) {
        practitionerPNCMap.put(pid, false);
    }
}
```

### AC2: updateAccountPNCHelper – change source and logic

**Given** the method `PRM_CommonUtils.updateAccountPNCHelper` exists,  
**And** it is called from `PRM_AccountTriggerHelper.updateAccountPNC` (Vendor Account PNC change) and `PRM_PracFacilityTriggerHandler` (HealthcarePractitionerFacility insert/IsActive change),  
**And** it currently receives HCPF records with Account.PRM_PNC__c and uses "all must be PNC" logic,  
**When** the developer updates it to work with HealthcareFacility.PRM_PNC__c **and to branch on each practitioner's `PRM_PNCAnyLocation__c`**,  
**Then** the logic shall be, per practitioner:
- **Default (flag false) — ALL:** Practitioner Account PRM_PNC__c = true only if **all** of their active location affiliations have HealthcareFacility.PRM_PNC__c = true; false if **any** location has PNC = false.
- **Flag true — ANY:** Practitioner Account PRM_PNC__c = true if **any** of their location affiliations has HealthcareFacility.PRM_PNC__c = true; false if **none** are PNC.
- The helper must load `PRM_PNCAnyLocation__c` for the practitioner (e.g., include `Practitioner.Account.PRM_PNCAnyLocation__c` in `getPIdToHCPFList`) and pick the branch accordingly. Only write the Account when the computed value differs from the current `PRM_PNC__c`.

### AC3: getPIdToHCPFList – update query

**Given** the method `PRM_CommonUtils.getPIdToHCPFList` is used by `updateAccountPNCHelper` (called from Account and PracFacility triggers),  
**And** it currently queries HCPF with RecordType `PRM_PractitionerPracticeAffiliation` (via `PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL`) and `Account.PRM_PNC__c`,  
**When** the developer updates it for the new model,  
**Then** it shall query HealthcarePractitionerFacility for the practitioner-location affiliation record type and include `HealthcareFacility.PRM_PNC__c` (and `Practitioner.Account.PRM_PNCAnyLocation__c`) instead of `Account.PRM_PNC__c`. The **branching (ALL default vs ANY when the flag is on) happens in `updateAccountPNCHelper`** (AC2); `getPIdToHCPFList` simply supplies the location PNC and the practitioner's switch value. Ensure active-record filters (`IsActive = true` and, where applicable, the facility/location active) are preserved.

### AC4: PRM_ReviewRCAT_English – PNC display correct (all three steps)

**Given** the Credentialing Specialist uses PRM_ReviewRCAT_English to review recredentialing terminations,  
**When** they view:
- **Step 1: Review PNC & Delegated** – "Practitioners will only be termed from their Non-Delegated or Non-PNC Groups."
- **Step 2: Review Last Man Standing**
- **Step 3: Review RCAT – Not Last AND PNC Delegated Practitioner Locations**  
**Then** the PNC checkbox for each practitioner/location row shall display the value from `HealthcareFacility.PRM_PNC__c` (practice location PNC), **not** from `Account.PRM_PNC__c` (vendor PNC, which is being removed). The Custom LWCs (CustomLWC1, CustomLWC2, CustomLWC3) that render the practitioner tables must consume PNC from the updated payload (HealthcareFacility.PRM_PNC__c or PracLoc.pnc). Data sources: (a) Step 1 & 3 – DataRaptors (PRMGetRelatedDataforPNCAndDelegatedRCATReview, PRMGetRelatedRecordForRCATReview, PRMGetPLVendorPNCRCAT); (b) Step 2 – PRM_RCATProcessingHelper.assignLocationDerivedFields → PracLoc.pnc.

---

# USER STORY 5: Apex – HealthcareFacility Trigger for PNC Rollup

**Persona:** Developer (Apex) + PDM Specialist (Business)  
**Priority:** P0  
**Depends on:** User Story 4

## Story

**As an** OmniStudio/Salesforce developer,  
**I want to** create a trigger on **HealthcareFacility** that rolls up PNC to practitioner accounts when a practice location's `PRM_PNC__c` changes, and recompute a practitioner's PNC when their `PRM_PNCAnyLocation__c` (ALL/ANY) switch changes,  
**So that** a practitioner's PNC stays in sync (ALL default / ANY when flagged) whenever the location's PNC or the practitioner's ALL/ANY switch changes.

### PNC recompute triggers — the full picture (this story owns #1 and #3)

| # | Trigger | Fires when | Recompute action | Story |
|---|---------|-----------|------------------|-------|
| 1 | **HealthcareFacility** (new — §5.1) | `HealthcareFacility.PRM_PNC__c` inserted/changed | Recompute every practitioner affiliated (active PPL) to that location | **US5 (this story)** |
| 2 | **PPL / HealthcarePractitionerFacility** (existing `PRM_PracFacilityTriggerHandler`) | Practitioner **added** (insert), **activated/deactivated** (IsActive change), or **removed** (delete) on a location | Recompute the affected practitioner(s) | **US5B** |
| 3 | **Account (Practitioner)** (§5.1a) | `PRM_PNCAnyLocation__c` changes | Recompute that practitioner (switch can flip PNC with no location change) | **US5 (this story)** |

All three funnel through the same switch-aware rule (`pncOnlyPractitioner` / `updateAccountPNCHelper`) so ALL-default / ANY-when-flagged behavior stays in one place. The **practitioner add/remove** path (#2) is specified in **US5B** below.

---

## Business Details (For Business Analysts & Stakeholders)

### Request Type

| Field | Value |
|-------|-------|
| **Flow Name** | PDM Manual Update (PRM_PDMManualUpdate_English) |
| **Manual Update Option** | **TBD – Business to confirm** (see questions below) |
| **Request Type** | Add/Remove PNC |
| **User Role** | PDM Specialist |

### Current Process (Before Change)

1. PDM Specialist selects **Vendor** as the manual update type.
2. PDM Specialist selects **Add/Remove PNC** as the vendor change type.
3. PDM Specialist searches for a group (by NPI, Tax ID, or name) and selects **one practice location** from the search results (GroupSelectionFlexCard).
4. The selected location's current PNC status is displayed (read-only checkboxes: **CBPNCCkd** if PNC = true, **CBPNCUnCkd** if PNC = false).
5. PDM Specialist runs **ProcessMedicareNumbersAndPncData** (IP) which prepares PNC data.
6. PDM Specialist checks/unchecks the PNC checkbox to indicate the desired value.
7. On submit, the system updates the **Vendor Account's** PRM_PNC__c field.
8. **Result:** All practice locations under that vendor inherit the same PNC value (one PNC per vendor).

### New Process (After Change)

1. PDM Specialist selects **Vendor** or **Practice Location** (business to confirm) → **Add/Remove PNC**.
2. PDM Specialist enters **NPI** to search.
3. The system **displays all practice locations** for that NPI (no selection – all locations are shown).
4. A **table** displays all locations with Location Name, Address, current PNC, and an **editable PNC checkbox** per row.
5. PDM Specialist changes the PNC checkbox for the location(s) they want to update.
6. On submit: **Validation** – if no PNC value was changed for any location, show error and block submit. Otherwise, update **HealthcareFacility.PRM_PNC__c** for each location where PNC was changed.
7. **Result:** Each practice location has its own PNC value. A vendor can have some locations PNC and others non-PNC.

### UI Changes (Confirmed)

| Item | Current | New |
|------|---------|-----|
| **Location display** | User selects **one** practice location from search | **No selection** – system displays **all locations** based on NPI search |
| **Search** | By NPI, Tax ID, or name | **Search by NPI** – user enters NPI; system returns all practice locations for that NPI |
| **PNC checkbox** | Read-only display; user toggles to set new value | **Editable per location** – one checkbox per row; business can change PNC for any displayed location |
| **Add/Remove PNC step** | PncData (Edit Block) – single location | **Table** – one row per location (all locations for NPI) with Location Name, Address, current PNC, and editable PNC checkbox |
| **Confirmation message** | Generic success | "PNC updated for X location(s)" |
| **Validation** | None for Add/Remove PNC | **At least one PNC location must be changed** – if business does not change any PNC value, show error and block submit |

### Validation Rule: At Least One PNC Location Must Be Changed

**Rule:** Before submit, at least one of the displayed practice locations must have its PNC checkbox changed (different from the original value). If business views the locations but does not change any PNC value, display the error and block submit.

**Implementation pattern (existing in OmniScript):** Use **Set Errors** element type (e.g., `SetErrorPLNetworkNotAvailable`, `SetErrorPLTaxNetworkDirError`). Add new element `SetErrorPNCNoChange` with:
- **elementErrorMap:** `"PNCNoChangeError": "At least one PNC location must be changed before submit."`
- **show** condition: When `hasAtLeastOnePNCChange = false` (formula: true if any row has `isPNC != originalPNC`)
- **validationRequired:** `"Step"` – blocks Next/Submit when error is shown

**Alternative:** Extend `PRMTransformValidateRecordSelection` (or create Add/Remove PNC–specific transform) to add formula `hasAtLeastOnePNCChange` and `ShowPNCNoChangeError`; then Set Errors element references `ShowPNCNoChangeError`.

### Business Questions (Must Provide Before Development)

**1. Request type – where should Add/Remove PNC appear?**

- [ ] **Option A: Vendor Account** – Keep Add/Remove PNC under **Vendor** manual update (current placement). User searches by NPI; system displays all locations for that vendor.
- [ ] **Option B: Practice Location** – Move Add/Remove PNC under **Practice Location** manual update. User searches by NPI; system displays all locations.
- [ ] **Option C: Both** – Offer Add/Remove PNC under both Vendor and Practice Location paths.

**2. Search criteria – confirmed**

- [x] **Search by NPI** – User enters NPI; system displays **all practice locations** for that NPI (no selection step).
- [ ] Confirm NPI type: Organization NPI, Location NPI, or both?

**3. Validation rules**

- [x] **At least one PNC location must be changed** – User cannot submit unless they have changed the PNC checkbox for at least one selected location (confirmed).
- [ ] Any additional validation rules? (e.g., must at least one location remain PNC if practitioners are PNC?)

---

## Technical Details (For Developers)

### 5.1 HealthcareFacility Trigger (Apex)

**File to create:** `PRM_HealthcareFacilityTrigger.trigger` (or add to existing HealthcareFacility trigger if one exists)

| Requirement | Specification |
|-------------|---------------|
| **Trigger events** | `after insert`, `after update` |
| **Condition** | Fire when `PRM_PNC__c` is inserted or changed (Trigger.oldMap value != Trigger.newMap value) |
| **Logic** | 1. Collect HealthcareFacilityIds where PRM_PNC__c changed<br>2. Query HealthcarePractitionerFacility WHERE HealthcareFacilityId IN :changedIds AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation' AND IsActive = true<br>3. Collect PractitionerIds (ContactId)<br>4. For each practitioner, recalculate PNC across **all** their active location affiliations using the practitioner's `PRM_PNCAnyLocation__c` switch: **ALL** locations PNC by default, or **ANY** location PNC when the flag is true. Reuse `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` (now switch-aware) so the rule stays in one place.<br>5. Update Practitioner Account (PersonContactId → Account) PRM_PNC__c |
| **Bulk safety** | No SOQL/DML in loops; use Set/Map for practitioner IDs; batch Account updates |

**Pseudocode:**
```apex
trigger PRM_HealthcareFacilityTrigger on HealthcareFacility (after insert, after update) {
    Set<Id> changedHCFIds = new Set<Id>();
    for (HealthcareFacility hcf : Trigger.new) {
        if (Trigger.isInsert || hcf.PRM_PNC__c != Trigger.oldMap.get(hcf.Id).PRM_PNC__c) {
            changedHCFIds.add(hcf.Id);
        }
    }
    if (changedHCFIds.isEmpty()) return;
    // 1) Find affected practitioners via active PRM_PractitionerLocationAffiliation HCPF
    // 2) Recalculate PNC for each via pncOnlyPractitioner (ALL default / ANY when PRM_PNCAnyLocation__c = true)
    // 3) Bulk-update practitioner Accounts where PRM_PNC__c changed
}
```

### 5.1a Recompute When `PRM_PNCAnyLocation__c` Changes (Account Trigger)

**File:** `PRM_AccountTriggerHelper.cls` (Practitioner Account path)

The ALL/ANY switch can flip a practitioner's PNC **without any location changing**. Therefore the Account trigger must recompute the rollup when `PRM_PNCAnyLocation__c` changes.

| Requirement | Specification |
|-------------|---------------|
| **Trigger event** | `after update` on Account (Practitioner record type) |
| **Condition** | `PRM_PNCAnyLocation__c` old value != new value |
| **Logic** | 1. Collect the changed practitioners' PersonContactIds<br>2. Call `pncOnlyPractitioner(contactIds)` (switch-aware) to recompute<br>3. Update `Account.PRM_PNC__c` where the recomputed value differs |
| **Guardrails** | Bulk-safe; avoid recursion (only re-enter when the switch changed, and skip if PRM_PNC__c already equals the computed value) |

### 5.2 Deprecate Account Trigger PNC Logic

**File:** `PRM_AccountTriggerHelper.cls`

- Remove or disable `updateAccountPNC` for **Vendor** Account when `PRM_PNC__c` changes (Vendor PNC is going away in US11).
- **Keep** the Practitioner-side recompute for `PRM_PNCAnyLocation__c` changes (§5.1a) — that is new and stays.

### 5.3 PDM Add/Remove PNC Flow – OmniScript & DataRaptor Changes

**Note:** Search by NPI confirmed. User enters NPI; system displays **all** practice locations for that NPI (no selection). Flow path (Vendor vs Practice Location) depends on business decision.

**OmniScript:** `PRM_PDMManualUpdate_English`

| Element | Current | Change Required |
|---------|---------|-----------------|
| **SV_PNC** | Sets `AccountToUpdate.RecordId = SelectedVendorAccount:Id` | For Add/Remove PNC: Pass **all displayed locations** (from NPI search) with `RecordId`, `originalPNC`, and `isPNC` per row; only locations where `isPNC != originalPNC` need to be updated |
| **AccountToUpdate** | Used by DRUpdateAccount | Add new payload for Add/Remove PNC: `FacilitiesToUpdate` – array of all locations with `{RecordId, originalPNC, isPNC}`; filter to rows where changed before update |
| **PRM_PDMRecordsCreation** | DRUpdateAccount calls PRMDRUpdateAccountPDM (updates Account) | Add new branch for Add/Remove PNC: Call DataRaptor that updates HealthcareFacility for locations where PNC changed |
| **SetErrorPNCNoChange** (new) | N/A | Add **Set Errors** element – blocks submit when no PNC change; see 5.3a below |

**DataRaptor to create or modify:**

| Option | Approach |
|--------|----------|
| **A** | Create new `PRMDRUpdateHealthcareFacilityPNC` – Load type, accepts **array** of `{RecordId, PRM_PNC__c}` for locations where PNC changed; updates multiple HealthcareFacility records in one call |
| **B** | Add HealthcareFacility object to `PRMLoadFacilityLocAddUpdate` with PRM_PNC__c mapping; use when Add/Remove PNC; support batch input (changed locations only) |

**DataRaptor to fetch locations by NPI:** Ensure existing or new DataRaptor returns all practice locations for a given NPI (Organization or Location NPI per business confirmation).

**Integration Procedure:** `PRM_PDMRecordsCreation`

- Add new element (e.g., `DRUpdateHealthcareFacilityPNC`) with execution condition: `%RecordsToUpdate:IndividualApplication:PDMManualUpdateType% == "Add/Remove PNC"`.
- This element calls the HealthcareFacility update DataRaptor instead of PRMDRUpdateAccountPDM.
- Modify or remove `DRUpdateAccount` execution for Add/Remove PNC (no longer update Account for this type).

### 5.3a Validation: At Least One PNC Location Must Be Changed

**Pattern:** Follow existing OmniScript validation – **Set Errors** element (see `SetErrorPLNetworkNotAvailable`, `SetErrorPLTaxNetworkDirError`).

| Component | Specification |
|-----------|---------------|
| **New element** | `SetErrorPNCNoChange` |
| **Type** | Set Errors |
| **elementErrorMap** | `"PNCNoChangeError": "At least one PNC location must be changed before submit."` |
| **show** condition | When `hasAtLeastOnePNCChange = false` |
| **validationRequired** | `"Step"` |
| **Placement** | Inside AddOrRemovePNCRecords step, before IPCreatePDMRecords (or before ProcessMedicareNumbersAndPncData) |

**Formula for `hasAtLeastOnePNCChange`:**
- For each row in `FacilitiesToUpdate` (or `PncData`): compare `isPNC` (new value from checkbox) with `originalPNC` (value when locations were loaded).
- `hasAtLeastOnePNCChange = true` if **any** row has `isPNC != originalPNC`.
- Implement via: (a) Set Values with formula, or (b) DataRaptor Transform (extend `PRMTransformValidateRecordSelection` or create PNC-specific transform), or (c) Integration Procedure that returns `ShowPNCNoChangeError`.

**Reference elements:** `PRM_PDMManualUpdate_English_Element_SetErrorPLNetworkNotAvailable.json`, `PRM_PDMManualUpdate_English_Element_SetErrorPLTaxNetworkDirError.json`

### 5.4 Data Flow for Add/Remove PNC

| Step | Source | Target |
|------|--------|--------|
| User enters NPI | Search input | NPI |
| System fetches locations | DataRaptor/IP by NPI | All practice locations for that NPI (no selection) |
| Table displays all locations | Locations array | One row per location: Location Name, Address, originalPNC, editable PNC checkbox |
| User changes PNC per row | Checkbox per location | isPNC per facility |
| Validation | Compare isPNC vs originalPNC for each row | hasAtLeastOnePNCChange = true if any row changed; else show error, block submit |
| SV_PNC (modified) | All locations with RecordId, originalPNC, isPNC | FacilitiesToUpdate; filter to rows where isPNC != originalPNC for update |
| IP/DataRaptor | FacilitiesToUpdate (changed rows only) | HealthcareFacility.PRM_PNC__c (batch update) |
| Trigger | HealthcareFacility update(s) | Practitioner Account.PRM_PNC__c (rollup) |

### 5.5 Files to Create/Modify

| File | Action |
|------|--------|
| `PRM_HealthcareFacilityTrigger.trigger` | Create |
| `PRM_HealthcareFacilityTriggerHandler.cls` (or equivalent) | Create |
| `PRM_AccountTriggerHelper.cls` | Modify – disable updateAccountPNC for Vendor PNC; **add Practitioner-side recompute when `PRM_PNCAnyLocation__c` changes (§5.1a)** |

> The **PPL / `HealthcarePractitionerFacility` trigger** (`PRM_PracFacilityTriggerHandler`) changes — recompute on practitioner add/remove — are specified separately in **US5B**.
| `PRMDRUpdateHealthcareFacilityPNC` (DataRaptor) or `PRMLoadFacilityLocAddUpdate` | Create or modify |
| `PRM_PDMRecordsCreation` (IP) | Modify – add DRUpdateHealthcareFacilityPNC for Add/Remove PNC |
| `PRM_PDMManualUpdate_English` (OmniScript) | Modify – SV_PNC, payload for Add/Remove PNC; add SetErrorPNCNoChange; add formula for hasAtLeastOnePNCChange |
| Test classes | Create/update for trigger and handler |

---

## Acceptance Criteria (Given / When / Then)

### AC1: Create HealthcareFacility trigger

**Given** the Account trigger currently handles PNC rollup when Vendor Account.PRM_PNC__c changes,  
**When** the developer creates a new trigger on HealthcareFacility,  
**Then** the trigger shall:
- Fire on `after insert`, `after update`
- When `PRM_PNC__c` is inserted or changed (old value != new value)
- Collect all HealthcareFacilityIds that changed
- Find all HealthcarePractitionerFacility records where HealthcareFacilityId IN :changedIds AND RecordType = PRM_PractitionerLocationAffiliation AND IsActive = true
- Collect the PractitionerIds (ContactIds)
- For each practitioner, recalculate PNC using the **switch-aware** rule: **ALL** locations PNC by default, or **ANY** location PNC when that practitioner's `PRM_PNCAnyLocation__c = true` (reuse `pncOnlyPractitioner`)
- Update the Practitioner Account (PersonContactId → Account) with the new PRM_PNC__c value

### AC1a: Recompute when the ALL/ANY switch changes

**Given** the practitioner's `PRM_PNCAnyLocation__c` is changed (with no change to any location),  
**When** the Account `after update` trigger runs,  
**Then** the practitioner's `PRM_PNC__c` shall be recomputed with the new rule (`pncOnlyPractitioner`) and updated if it differs. Example: a practitioner with locations [PNC, non-PNC] flips from `PRM_PNC__c = false` (ALL) to `true` (ANY) when the switch is turned on, and back to `false` when turned off.

### AC2: Deprecate Account trigger PNC logic

**Given** the new HealthcareFacility trigger handles PNC rollup,  
**When** the developer updates PRM_AccountTriggerHelper,  
**Then** the `updateAccountPNC` method shall be removed or disabled for Vendor Account PRM_PNC__c changes (since PNC will no longer exist on Vendor Account after full migration). If Account.PRM_PNC__c is kept on Vendor during transition, the trigger can remain but will eventually be removed.

### AC3: Bulk safety

**Given** multiple HealthcareFacility records are updated in one transaction,  
**When** the trigger runs,  
**Then** it shall use bulk patterns (no SOQL/DML in loops), handle nulls, and respect governor limits.

### AC4: Add/Remove PNC flow updates HealthcareFacility

**Given** the PDM Specialist uses Add/Remove PNC, enters NPI, and the system **displays all practice locations** for that NPI,  
**When** they change the PNC checkbox for one or more locations and submit the form,  
**Then** the system shall update HealthcareFacility.PRM_PNC__c for each location where PNC was changed (not Account.PRM_PNC__c). The HealthcareFacility trigger shall fire for each updated location and roll up to practitioner accounts.

### AC5: Validation – at least one PNC location must be changed

**Given** the PDM Specialist has viewed the Add/Remove PNC step with all locations displayed (based on NPI search),  
**When** they attempt to submit without changing the PNC checkbox for any location (all values match original),  
**Then** the system shall display the error "At least one PNC location must be changed before submit." and block the submit. The user must change at least one location's PNC value to proceed.

---

# USER STORY 5B: Apex – Practitioner-Practice-Location (PPL) Trigger for PNC Rollup

**Persona:** Developer (Apex)  
**Priority:** P0  
**Depends on:** User Story 4  
**Related:** User Story 5 (HealthcareFacility trigger owns the location-PNC-change and ALL/ANY-switch recompute paths)

## Story

**As an** OmniStudio/Salesforce developer,  
**I want to** keep the existing **Practitioner-Practice-Location (PPL) trigger** (`HealthcarePractitionerFacility` → `PRM_PracFacilityTriggerHandler`) recomputing practitioner PNC whenever a practitioner is **added to** or **removed from** a location,  
**So that** a practitioner's PNC (ALL default / ANY when flagged) stays in sync when their set of practice locations changes — not only when a location's PNC value changes (US5).

---

## Technical Details (For Developers)

### 5B.1 PPL / HealthcarePractitionerFacility Trigger (Apex)

**This trigger already exists and already recomputes PNC** — it must be kept working and made switch-aware (via US4). Do **not** build a new one; extend the existing handler.

**Files:** `PRM_HealthcarePractitionerFacilityTrigger.trigger` → `PRM_PracFacilityTriggerHandler.updateAccountPNC()`

**Current behaviour (as-built):**

```apex
// PRM_PracFacilityTriggerHandler.updateAccountPNC()  (afterInsert + afterUpdate)
Set<Id> practitionerIds = new Set<Id>();
for (HealthcarePractitionerFacility f : (List<HealthcarePractitionerFacility>) Trigger.new) {
    if (Trigger.isInsert
        || (Trigger.isUpdate && f.IsActive != Trigger.oldMap.get(f.Id).IsActive)) {
        practitionerIds.add(f.PractitionerId);   // practitioner "added" or activated/deactivated on a location
    }
}
if (!practitionerIds.isEmpty()) {
    Map<Id, List<HealthcarePractitionerFacility>> hcpfMap = PRM_CommonUtils.getPIdToHCPFList(practitionerIds);
    PRM_CommonUtils.updateAccountPNCHelper(practitionerIds, hcpfMap);   // recompute + update Account.PRM_PNC__c
}
```

| Scenario | HCPF event | Handled today? | Required after change |
|----------|-----------|----------------|-----------------------|
| Practitioner **added** to a location | `after insert` | ✅ Yes (`afterInsert → updateAccountPNC`) | Recompute must now source `HealthcareFacility.PRM_PNC__c` + honor `PRM_PNCAnyLocation__c` (via US4 AC2/AC3) |
| Practitioner **removed** (soft) — affiliation deactivated | `after update`, `IsActive` true→false | ✅ Yes (IsActive-change branch) | Same switch-aware recompute |
| Practitioner **re-activated** on a location | `after update`, `IsActive` false→true | ✅ Yes | Same |
| Practitioner **removed (hard delete)** of the affiliation | `after delete` | ❌ **No** — `afterDelete` only runs `updateActiveLocationsCount()` (PNC not recomputed) | **Add** PNC recompute in `afterDelete` (collect `PractitionerId` from `Trigger.old`, recompute). See gap below. |

**Changes required in this story:**

1. **Delete gap (required):** In `PRM_PracFacilityTriggerHandler.afterDelete`, collect `PractitionerId` from the deleted HCPF rows and call the same `getPIdToHCPFList` + `updateAccountPNCHelper` recompute, so removing a practitioner from a PNC location by deletion also updates PNC. (Today only soft-remove via `IsActive` is covered.) If the business only ever ends affiliations via `IsActive = false`, capture that as a decision (see Clarification Questions) and mark the delete branch optional; otherwise implement it.
2. **Switch-aware source (via US4):** the recompute path (`getPIdToHCPFList` + `updateAccountPNCHelper`) is updated in US4 to read `HealthcareFacility.PRM_PNC__c` and branch ALL/ANY on `PRM_PNCAnyLocation__c`. No separate logic lives here — this trigger just triggers the recompute for the affected practitioners.
3. **Bulk-context bypass (call out):** the trigger returns early when `PRM_TriggerContextControl.inBulkContext()` is true and when `PRM_TriggerBypassPermission` is granted. During **bulk/async creation** (e.g., the PRM async batch classes and roster loads that set bulk context), this trigger is skipped, so those paths must set/rollup PNC themselves. Verify the async Practitioner-creation path computes PNC at creation (US3 handles creation-time PNC) and that no PNC-relevant HCPF mutation silently bypasses the rollup.

**Bulk safety:** already bulk-safe (collects a Set of PractitionerIds, one `getPIdToHCPFList` query, one bulk Account update inside the helper). Preserve this — no SOQL/DML in loops when adding the delete branch.

### 5B.2 Files to Create/Modify

| File | Action |
|------|--------|
| `PRM_PracFacilityTriggerHandler.cls` | Modify – **add PNC recompute to `afterDelete`** (practitioner removed by hard delete); confirm `afterInsert`/`afterUpdate` `updateAccountPNC()` continues to fire for add/activate/deactivate (§5B.1). Recompute path itself is switched to HealthcareFacility source in US4. |
| `PRM_PracFacilityTriggerHandlerTest.cls` | Modify – add tests for add (insert), remove (IsActive false + delete), re-activate, and bulk (AC1–AC3 below) |

---

## Acceptance Criteria (Given / When / Then)

### AC1: Practitioner added to a location recomputes PNC

**Given** the existing PPL trigger `PRM_HealthcarePractitionerFacilityTrigger` → `PRM_PracFacilityTriggerHandler.updateAccountPNC()`,  
**When** a practitioner is **added** to a location (HealthcarePractitionerFacility insert of a `PRM_PractitionerLocationAffiliation`) **or re-activated** (`IsActive` false→true),  
**Then** that practitioner's `PRM_PNC__c` shall be recomputed switch-aware (ALL default / ANY when `PRM_PNCAnyLocation__c = true`) from `HealthcareFacility.PRM_PNC__c` across their active location affiliations (via the US4-updated `getPIdToHCPFList` + `updateAccountPNCHelper`), and the Account updated only if the value differs.

### AC2: Practitioner removed from a location recomputes PNC

**Given** the same PPL trigger,  
**When** a practitioner is **removed** from a location — either by **deactivation** (`IsActive` true→false) or by **deletion** of the affiliation,  
**Then** that practitioner's `PRM_PNC__c` shall be recomputed switch-aware from their remaining active location affiliations and updated if it differs.  
**And** because the current `afterDelete` path recomputes `updateActiveLocationsCount` only (not PNC), the developer shall **add the PNC recompute to `afterDelete`** (collect `PractitionerId` from `Trigger.old`, run the same recompute) — unless the business confirms removals are always soft (`IsActive = false`), in which case the delete branch is documented as not required (see Clarification Questions).  
**Example:** a practitioner on [PNC, non-PNC] with the ALL default is `PRM_PNC__c = false`; removing the non-PNC location leaves [PNC] only, so recompute flips them to `true`.

### AC3: Bulk & async coverage

**Given** practitioners are added/removed in bulk, or via the async batch/roster paths that set `PRM_TriggerContextControl.inBulkContext()` (which makes the PPL trigger return early),  
**When** those paths run,  
**Then** the rollup shall still be correct: the PPL recompute is bulk-safe (Set of PractitionerIds, one query, one bulk Account update), **and** any path that bypasses the trigger (bulk context / `PRM_TriggerBypassPermission`) shall compute PNC itself (creation-time PNC is handled by US3). No PNC-relevant HCPF mutation may leave the practitioner's PNC stale.

## Clarification Questions

1. **Removal semantics (drives the `afterDelete` work in §5B.1 / AC2):** When a practitioner is removed from a location, does the system **hard-delete** the `HealthcarePractitionerFacility` record, or only **soft-remove** it (`IsActive = false` / end-date)? If removals are always soft, the `afterDelete` PNC recompute is optional; if hard deletes occur anywhere (UI, roster, data loads), the `afterDelete` recompute is required.
2. **Bulk/async paths (drives AC3):** Which practitioner add/remove paths run under `PRM_TriggerContextControl.inBulkContext()` or `PRM_TriggerBypassPermission` (async batch classes, roster upload, data loads)? For each, confirm PNC is set/rolled up by that path itself (since the PPL trigger is skipped).
3. **Record type name:** Confirm the exact HCPF record-type DeveloperName for practitioner↔location affiliations (used to filter the rollup) — `PRM_PractitionerLocationAffiliation` vs the constant behind `PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL`. (Shared with US5.)

---

# USER STORIES 6, 7, 8: PNC Migration by Guided Flow (OmniScript)

**Persona:** Product Owner, Business Analyst, Developer  
**Priority:** P0  
**Depends on:** User Story 1, 2

## Overview

User Stories 6 (Apex), 7 (DataRaptors), and 8 (Integration Procedures) are consolidated into **flow-centric** user stories. Each guided flow/OmniScript has a **Business Section** (for POs and BAs) and a **Technical Section** (for developers) so stakeholders understand *what* changes and *where* to implement it.

**What changes:** PNC moves from Vendor Account to HealthcareFacility (practice location). Every flow that displays or validates PNC must use the new source.

---

## Flow 1: PDM Manual Update (PRM_PDMManualUpdate_English)

**Who uses it:** PDM Specialist  
**Request types affected:** Add/Remove a Practitioner, Add/Update/Terminate Current Office Information, Add/Remove PNC, and other Practice Location / Vendor paths

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Selected Practice Location** – PNC (Par Non Cred) checkbox | Today: reads from Vendor Account. After: reads from the selected practice location (HealthcareFacility). |
| **Search Results** – PNC column (if shown) | Same change: each row shows that location's PNC, not the vendor's. |
| **Practitioner verification** – validation when adding/removing practitioners | Uses facility PNC: if location is PNC, validation passes; if not PNC, at least one PNC practitioner required. |
| **Add/Remove PNC** – PNC checkbox per location | Writes to HealthcareFacility.PRM_PNC__c (not Account). |

**Why it matters:** PDM Specialists rely on PNC to manage practitioners and locations. Wrong PNC can block valid submissions or allow invalid ones.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRMFetchVendorAndHCFWithNPI** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` (or `Facility:PracLocPNC` from `HealthcareFacility.PRM_PNC__c`) |
| **PRMFetchVendorAndHCFWithTaxID** | DataRaptor | Same; use `Facility:PRM_PNC__c` instead of `Vendor:PRM_PNC__c` for facility PNC |
| **PRMDRExtractVendorPracticeLocations** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` |
| **PRM_VerifyPractitionerDetails** | Integration Procedure | SetDelegatedPNC: `PNC` input from selected facility must come from HealthcareFacility.PRM_PNC__c (via DataRaptor). Practitioner PNC in merged list = rollup (unchanged). |
| **PRM_IPUtilityHelper** | Apex | `hcfRecord.Account.PRM_PNC__c` → `hcfRecord.PRM_PNC__c` for PracLocPNC mapping (if used by PDM IPs) |

### Acceptance Criteria

**Given** the PDM Specialist is in PRM_PDMManualUpdate_English and selects a practice location,  
**When** they view the Selected Practice Location block or run practitioner verification,  
**Then** the PNC value shall come from HealthcareFacility.PRM_PNC__c for the selected location. PNCValid and DelegatedValid formulas in PRM_VerifyPractitionerDetails shall work correctly.

---

## Flow 2: Provider Change Form (PRM_ProviderChangeForm_English)

**Who uses it:** PDM Specialist  
**Request types affected:** Add or Remove a Practitioner, Update/Add/Terminate Current Office Information

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Provider search results** – facility list with PNC | Each facility's PNC comes from that practice location, not the vendor. |
| **Practitioner verification** – validation when adding practitioners or updating COI | Uses selected facility's PNC: PNC location → validation passes; non-PNC location → at least one PNC practitioner required. |

**Why it matters:** Provider Change Form validates practitioners against PNC and Delegated rules. Incorrect facility PNC breaks validation.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRMExtractPracticeLocationsProvChange** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` (output: `Facility:ProviderDetails:PNC`) |
| **PRMDRExtractVendorPracticeLocations** | DataRaptor | Same path change if used by Provider Search |
| **PRM_VerifyPractitionerDetails** | Integration Procedure | `PNC` passed from `%ProviderDetails:PNC%` (OmniScript) must reflect HealthcareFacility.PRM_PNC__c. No IP formula change if DataRaptor is updated. |

### Acceptance Criteria

**Given** the PDM Specialist is in PRM_ProviderChangeForm_English and selects "Add or Remove a Practitioner" or "Update/Add/Terminate Current Office Information",  
**When** PRM_VerifyPractitionerDetails runs,  
**Then** ProviderDetails:PNC shall reflect the selected facility's HealthcareFacility.PRM_PNC__c. PNCValid and DelegatedValid shall work correctly.

---

## Flow 3: Off-Cycle Credentialing (PRM_OffCycleCredentialing_English)

**Who uses it:** Credentialing Specialist  
**Request types affected:** Provider search, group/facility selection

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Provider search results** – PNC for group and each facility | Facility PNC comes from each practice location. Group PNC may aggregate locations (e.g., any location PNC = group PNC). |
| **PNC consistency validation** (SetErrorsWhenPracTrueandAccFalse) | Continues to work; only the data source changes to HealthcareFacility. |

**Why it matters:** Credentialing Specialists need correct PNC to route cases and validate practitioner/location alignment.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_OffCycleProviderSearch** | Apex | Facility PNC: `fac.Account.PRM_PNC__c` → `fac.PRM_PNC__c` (HealthcareFacility). Group PNC: clarify with BA (aggregate from locations or deprecated). |
| **PRMFetchVendorAndHCFWithNPI** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` (if used by Off-Cycle search) |
| **Provider Search DataRaptors** | DataRaptor | Any path `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` |

### Acceptance Criteria

**Given** the Credentialing Specialist searches for a provider in PRM_OffCycleCredentialing_English,  
**When** they view search results,  
**Then** the PNC value for each facility shall come from HealthcareFacility.PRM_PNC__c. PNC consistency validation shall continue to work.

---

## Flow 4: Practitioner Termination / Recred Termination (PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English)

**Who uses it:** Credentialing Specialist  
**Request types affected:** Practitioner termination, recred termination

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Practice location list** – PracLocPNC, PNC checkbox per location | Each location's PNC comes from HealthcareFacility, not the vendor. |
| **Practitioner PNC** | Stays as practitioner Account rollup (unchanged). |

**Why it matters:** Termination flows must show correct PNC per location for accurate processing and letters.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRMExtractLocationsforHCPNPI** | DataRaptor | `HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c` → `HealthcarePractitionerFacility:HealthcareFacility.PRM_PNC__c` |
| **PRMDRGetLocationTerminationData** | DataRaptor | Same path change |
| **PRM_PractitionerTerminationBatchHelper** | Apex | Query `Account.PRM_PNC__c` on HealthcareFacility's Account → use `HealthcareFacility.PRM_PNC__c` instead |

### Acceptance Criteria

**Given** the Credentialing Specialist views practitioner or practice location data in the termination flows,  
**When** PNC is displayed,  
**Then** practice location PNC shall come from HealthcareFacility.PRM_PNC__c. Practitioner PNC shall come from the practitioner Account rollup (unchanged).

---

## Flow 5: RCAT Review & Recred Termination Letter (PRM_ReviewRCAT_English)

**Who uses it:** Credentialing Specialist  
**Request types affected:** RCAT review (3 steps), Recred Termination Letter generation

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **RCAT Review** – PNC & Delegated / Not Last step | PNC locations excluded from certain checks; data comes from HealthcareFacility. |
| **Recred Termination Letter** | PNC practice locations (HealthcareFacility.PRM_PNC__c = true) are excluded from the letter. Behavior unchanged; only data source changes. |

**Why it matters:** PNC locations are excluded from termination letters. Wrong source could include or exclude the wrong locations.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_RecredTerminationLetter** | Integration Procedure | FilterHCPFRecords: `'Account:PRM_PNC__c != true'` → `'HealthcareFacility:PRM_PNC__c != true'` (or correct path per DataRaptor output) |
| **PRMDRExtractHCPFDetails** | DataRaptor | Output HealthcareFacility.PRM_PNC__c for HCPF records; ensure structure supports IP formula |
| **PRM_GetRelatedDataforPNCAndDelegatedRCATReview** | DataRaptor / IP | Filter: `Account.PRM_PNC__c == false` → `HealthcareFacility.PRM_PNC__c == false` |
| **PRMGetPLVendorPNCRCAT** | DataRaptor | `HCF:Account.PRM_PNC__c` → `HCF:PRM_PNC__c` |
| **PRMDRGetFacilityInfoDelegatedPNCReCred** | DataRaptor | Same path change |

### Acceptance Criteria

**Given** the Credentialing Specialist uses PRM_ReviewRCAT_English or generates a recred termination letter,  
**When** PNC locations are filtered or excluded,  
**Then** the filter shall use HealthcareFacility.PRM_PNC__c. PNC locations shall be excluded from the termination letter.

---

## Flow 6: Ancillary & PAR Forms (Ancillary Provider, PAR Provider Search)

**Who uses it:** Users of Ancillary and PAR provider search flows  
**Request types affected:** Provider search in Ancillary/PAR contexts

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Provider search** – PNC per facility | Facility PNC comes from HealthcareFacility, not vendor. |

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_AncillaryProviderUtilsService** | Apex | `fac?.Account?.PRM_PNC__c` → `fac?.PRM_PNC__c` (HealthcareFacility) |
| **PRM_PARProviderSearch** | Apex | Facility PNC: `fac.Account.PRM_PNC__c` → `fac.PRM_PNC__c` |
| **PRMExtractPracticeLocationsAncillaryChange** | DataRaptor | `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` |
| **PRMExtractPracticeLocationsPARChange** | DataRaptor | Same |

### Acceptance Criteria

**Given** the user searches for a provider in Ancillary or PAR flows,  
**When** facility PNC is returned,  
**Then** it shall come from HealthcareFacility.PRM_PNC__c.

---

## Flow 7: Background Jobs (No User-Facing Flow)

**Who uses it:** System (batch/scheduled jobs)  
**Request types affected:** Future-dated processing, RCAT batch, etc.

### Business Section (For POs / BAs)

No direct user impact. These jobs process practitioner PNC rollup and participation status. Correct PNC source ensures practitioner records stay in sync when locations change.

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_FutureDatedProcessingBatchHandler** | Apex | Use HealthcarePractitionerFacility with RecordType `PRM_PractitionerLocationAffiliation` and `HealthcareFacility.PRM_PNC__c`. Compute practitioner PNC via the switch-aware `pncOnlyPractitioner` (ALL locations PNC by default; ANY location PNC when `PRM_PNCAnyLocation__c = true`). Any separate inline PNC query in this handler must adopt the same switch-aware rule. |
| **PRM_RCATTerminationBatchHelper** | Apex | Covered in User Story 4 (pncOnlyPractitioner, getPIdToHCPFList) |

### Acceptance Criteria

**Given** background jobs run (future-dated processing, RCAT),  
**When** they evaluate practitioner PNC,  
**Then** they shall use HealthcareFacility.PRM_PNC__c via PRM_PractitionerLocationAffiliation. Practitioner PNC rollup shall follow the switch-aware rule: ALL locations PNC by default, ANY location PNC when `PRM_PNCAnyLocation__c = true`.

---

## Flow 8: Practitioner Demographics & FlexCards (PRM_FetchPractitionerDemographics)

**Who uses it:** FlexCards, demographics displays  
**Request types affected:** Practitioner demographics display

### Business Section (For POs / BAs)

| What the user sees | What changes |
|--------------------|--------------|
| **Practitioner PNC** in demographics | No change. Practitioner PNC is the rollup on practitioner Account; the HealthcareFacility trigger keeps it in sync. |

### Technical Section (For Developers)

| Component | Type | Change |
|-----------|------|--------|
| **PRM_FetchPractitionerDemographics** | Integration Procedure | PractitionerData:PNC from Account.PRM_PNC__c (practitioner rollup). **No change** – rollup remains on Account. |

### Acceptance Criteria

**Given** practitioner demographics are displayed,  
**When** PNC is shown,  
**Then** it shall come from practitioner Account.PRM_PNC__c (rollup). No change required.

---

## Cross-Cutting Rules (All Flows)

### Practitioner PNC (Rollup)

- **Practitioner Account.PRM_PNC__c** = rollup from practice locations. **Do not change** DataRaptor/IP references that read or write practitioner PNC.
- **Rollup rule is per-practitioner and configurable:** ALL participating locations PNC by default; ANY location PNC when `Account.PRM_PNCAnyLocation__c = true`. The rule lives in Apex (`pncOnlyPractitioner` / `updateAccountPNCHelper`); DataRaptors/IPs just read the already-computed `PRM_PNC__c`.
- The HealthcareFacility trigger (User Story 5) keeps the rollup in sync when `HealthcareFacility.PRM_PNC__c` changes; the Account trigger (§5.1a) keeps it in sync when `PRM_PNCAnyLocation__c` changes.
- **`PRM_PNCAnyLocation__c`** is read-only to display flows; it is set/maintained by admins/specialists and should not be overwritten by rollup logic.

### DataRaptors That Write PNC

- **Practitioner Account** (rollup): Keep as-is.
- **Vendor Account**: Change to write HealthcareFacility.PRM_PNC__c when updating practice locations.
- **PRMDRCreateCaseCaseManagerAndAccount, PRMDRUpdateAccountPDM, PRMDRUpdatePNCCase**: Review each; practitioner writes stay, vendor writes change.

### Export and Validation

**Given** all DataRaptor changes are complete,  
**When** the developer runs `vlocity packExport` for updated DataRaptors,  
**Then** the export shall succeed and JSON shall reflect the new field paths.

### Test Classes

**Given** test classes create or assert on Account.PRM_PNC__c for vendors,  
**When** the developer updates tests,  
**Then** tests shall create HealthcareFacility records with PRM_PNC__c and/or update assertions. All tests shall pass.

---

## Quick Reference: Flow → Components

| Flow | OmniScript | Apex | DataRaptors | Integration Procedures |
|------|------------|------|-------------|------------------------|
| PDM Manual Update | PRM_PDMManualUpdate_English | PRM_IPUtilityHelper | PRMFetchVendorAndHCFWithNPI, PRMFetchVendorAndHCFWithTaxID, PRMDRExtractVendorPracticeLocations | PRM_VerifyPractitionerDetails |
| Provider Change Form | PRM_ProviderChangeForm_English | — | PRMExtractPracticeLocationsProvChange, PRMDRExtractVendorPracticeLocations | PRM_VerifyPractitionerDetails |
| Off-Cycle Credentialing | PRM_OffCycleCredentialing_English | PRM_OffCycleProviderSearch | PRMFetchVendorAndHCFWithNPI, Provider Search DRs | — |
| Practitioner Termination | PRM_PractitionerTerminationForm_English, PRM_PractitionerTerminationRecredForm_English | PRM_PractitionerTerminationBatchHelper | PRMExtractLocationsforHCPNPI, PRMDRGetLocationTerminationData | — |
| RCAT Review & Recred Letter | PRM_ReviewRCAT_English | — | PRMDRExtractHCPFDetails, PRM_GetRelatedDataforPNCAndDelegatedRCATReview, PRMGetPLVendorPNCRCAT, PRMDRGetFacilityInfoDelegatedPNCReCred | PRM_RecredTerminationLetter |
| Ancillary / PAR | Ancillary, PAR flows | PRM_AncillaryProviderUtilsService, PRM_PARProviderSearch | PRMExtractPracticeLocationsAncillaryChange, PRMExtractPracticeLocationsPARChange | — |
| Background Jobs | — | PRM_FutureDatedProcessingBatchHandler | — | — |
| Practitioner Demographics | FlexCards | — | — | PRM_FetchPractitionerDemographics (no change) |

---

# USER STORY 9: Credentialing Flows – PNC Display and Validation

**Persona:** Credentialing Specialist  
**Priority:** P1

## Story

**As a** Credentialing Specialist,  
**I want to** see and use PNC at the practice location level in credentialing flows,  
**So that** I can correctly identify which locations are PNC and ensure practitioners are handled appropriately.

## Acceptance Criteria (Given / When / Then)

### AC1: Off-Cycle Credentialing – PNC display

**Given** the Credentialing Specialist is in the Off-Cycle Credentialing flow (PRM_OffCycleCredentialing_English),  
**When** they search for a provider and view results,  
**Then** the PNC value displayed for the group and for each facility shall come from HealthcareFacility.PRM_PNC__c (for facilities) and the practitioner rollup (for practitioners). The validation that checks PNC consistency (SetErrorsWhenPracTrueandAccFalse, TextBlock14, TextBlock15) shall continue to work with the new data source.

### AC2: Practitioner Termination / Recred Termination – PNC display

**Given** the Credentialing Specialist is in PRM_PractitionerTerminationForm_English or PRM_PractitionerTerminationRecredForm_English,  
**When** they view practitioner or practice location data,  
**Then** the PNC checkbox/label (PracLocPNC, PNC) shall display the value from HealthcareFacility.PRM_PNC__c for each practice location, and the practitioner-level PNC from the practitioner Account rollup.

### AC3: PNC Review / PNC QC / PNC PDA flows

**Given** the Credentialing Specialist uses PRM_PNCReview_English, PRM_PNCQC_English, or PRM_PNCPDA_English,  
**When** they work with PNC cases,  
**Then** the flows shall correctly identify PNC practice locations and practitioners based on HealthcareFacility.PRM_PNC__c and the updated rollup logic. Any DataRaptors or IPs used by these flows shall be updated per User Stories 6, 7, 8 (Flow-Centric PNC Migration).

### AC4: Recred Termination Letter – exclude PNC locations

**Given** the Credentialing Specialist generates a recredentialing termination letter via PRM_RecredTerminationLetter (e.g., from RCAT review),  
**When** the letter is generated,  
**Then** practice locations with HealthcareFacility.PRM_PNC__c = true shall be excluded from the letter (FilterHCPFRecords). This behavior shall remain; only the data source changes from Account to HealthcareFacility.

### AC5: Practitioner Participation Form – PNC determination and case manager creation

**Given** the Credentialing Specialist uses the Practitioner Participation Form (PRM_PractitionerParticipationForm_English) to onboard a practitioner who is joining PNC groups,  
**When** the practitioner selects one or more groups and submits the form,  
**Then** the background logic shall:
1. For each selected group, determine the practice locations (HealthcareFacilities) the practitioner is joining.
2. For each practice location, evaluate `HealthcareFacility.PRM_PNC__c`.
3. Apply the practitioner's ALL/ANY switch:
   - **Default (`PRM_PNCAnyLocation__c` false):** set PNC = true only when **all** joining practice locations are PNC.
   - **Flag on (`PRM_PNCAnyLocation__c` true):** set PNC = true when **any** joining practice location is PNC.
4. When the practitioner is PNC, the case manager (IndividualApplication) created after submission shall use Record Type **PNC**.
5. Otherwise the case manager shall use the non-PNC record type (e.g., Application Review).

**Key components to update:** PRM_PractitionerScreenRecordCreation (SV_PNCFlag, PNCFlag formula — switch-aware), PRM_IPExtractGroupNameBasedOnTINNPI, and any DataRaptors that supply group/location PNC data. The GroupInformation or equivalent structure must include practice location PNC (HealthcareFacility.PRM_PNC__c) so the PNCFlag can be computed with the ALL (default) / ANY (flag) rule. See **User Story 3** for implementation details.

---

# USER STORY 10: PDM Flows – PNC Display and Validation

**Persona:** PDM Specialist  
**Priority:** P1

## Story

**As a** PDM Specialist,  
**I want to** see and use PNC at the practice location level in PDM flows,  
**So that** I can correctly add/remove PNC practitioners and locations and pass validation.

## Acceptance Criteria (Given / When / Then)

### AC1: PDM Manual Update – Add/Remove PNC

**Given** the PDM Specialist is in PRM_PDMManualUpdate_English and selects "Add/Remove PNC" as the manual update type,  
**When** they search for a group and select a practice location,  
**Then** the PNC status (SelectedPLPNC, PracLocPNC) shall display HealthcareFacility.PRM_PNC__c for the selected location. The checkboxes CBPNCCkd and CBPNCUnCkd (PNC Par Non Cred) shall reflect the practice location's PNC value.

### AC2: PDM Manual Update – Practitioner verification

**Given** the PDM Specialist adds or removes practitioners in the PDM flow,  
**When** PRM_VerifyPractitionerDetails runs (SetDelegatedPNC),  
**Then** the PNCValid and DelegatedValid formulas shall work correctly. PNCValid: when the selected facility is PNC (%PNC% = true), validation passes; otherwise at least one PNC practitioner is required. The facility PNC shall come from HealthcareFacility.PRM_PNC__c. DelegatedValid: non-credentialed, non-PNC practitioners cannot be in delegated groups. Practitioner PNC comes from the rollup (practitioner Account).

### AC3: Provider Change Form

**Given** the PDM Specialist is in PRM_ProviderChangeForm_English,  
**When** they verify practitioners (PRM_VerifyPractitionerDetailsParent),  
**Then** the PNC and DelegatedValid logic shall work as in AC2. The ProviderDetails:PNC passed to the IP shall reflect the selected facility's HealthcareFacility.PRM_PNC__c.

### AC4: Practitioner Demographics FlexCard

**Given** the PDM Specialist views practitioner demographics (PRMPractitionerDemographics FlexCard),  
**When** the FlexCard loads data via PRM_FetchPractitionerDemographicsParent,  
**Then** the PNC value displayed shall be the practitioner Account.PRM_PNC__c (rollup). No change needed for the FlexCard if the rollup is correct.

---

# USER STORY 10a: PDM Manual Update – Practitioner verification (Selected Practice Location PNC)

**Persona:** PDM Specialist  
**Priority:** P1  
**OmniScript:** PRM_PDMManualUpdate_English (PDM Manual Updates guided flow)

## Story

**As a** PDM Specialist,  
**I want to** see the correct PNC (Par Non Cred) status for each practice location when I select it in the PDM Manual Update flow,  
**So that** I can accurately add/remove practitioners, update office information, and manage PNC at the practice location level.

---

## Business Section (For Product Owners)

### What Changes

The **PNC (Par Non Cred)** checkbox in the "Selected Practice Location" section currently reads PNC from the **Vendor Account** (group). After this change, it will read PNC from the **Healthcare Facility** (practice location) record. This aligns with the broader PNC migration: PNC is moving from the vendor/group level to the individual practice location level.

### Why This Matters

- **Accuracy:** Each practice location can have its own PNC status. Displaying the vendor-level PNC was incorrect when locations within the same group had different PNC values.
- **User trust:** PDM Specialists rely on the PNC checkbox to verify location status before making changes. Incorrect data could lead to wrong decisions.
- **Validation:** The practitioner verification step (PRM_VerifyPractitionerDetails) uses this PNC value to validate that at least one PNC practitioner is present when the location is not PNC. Using the wrong source breaks validation logic.

### Which Request Types Are Affected

The PNC checkbox appears when the user selects **Practice Location** or **Vendor → Add/Remove PNC** and then selects a practice location from search results. The following request types show the "Selected Practice Location" block with the PNC checkbox:

| Path | Request Type | Shows PNC Checkbox? |
|------|--------------|---------------------|
| **Practice Location** | Add/Remove a Practitioner | Yes |
| **Practice Location** | Add/Update/Terminate Current Office Information | Yes |
| **Practice Location** | Patient Accept Status | Yes |
| **Practice Location** | Capitation Site | Yes |
| **Practice Location** | Update Office Hours | Yes |
| **Practice Location** | Add/Remove Network | Yes |
| **Practice Location** | Update Directory Indicators | Yes |
| **Practice Location** | Update Practice Location Names | Yes |
| **Practice Location** | Add/Remove Program Participation | Yes |
| **Practice Location** | Associate/Disassociate Practice Location | Yes |
| **Practice Location** | Add/Remove Contract To | Yes |
| **Practice Location** | Update Provider Features | Yes |
| **Practice Location** | Add/Terminate Practice Location Taxonomy | Yes |
| **Practice Location** | Update Billing/Mailing Address | Yes |
| **Vendor** | Add/Remove PNC | Yes |

### Step-by-Step UI Flow (How to See the Changes)

#### Path A: Practice Location → Add/Remove a Practitioner (or Add/Update/Terminate Current Office Information)

| Step | Screen/Element | What the User Sees | What Changes |
|------|----------------|--------------------|--------------|
| 1 | **Manual Update Options** | Radio: Practitioner, Vendor, Practice Location | No change |
| 2 | **Practice Location Change Type** (PracLocationManualChange) | Dropdown: Add/Remove a Practitioner, Add/Update/Terminate Current Office Information, etc. | No change |
| 3 | **Search Record** | Fields: NPI, Tax ID, Group Name, etc. | No change |
| 4 | **Search Results** (GroupSelectionFlexCard) | List of practice locations; user selects one | PNC column (if shown) uses HealthcareFacility.PRM_PNC__c |
| 5 | **Selected Practice Location** (BlkSelectedPracticeLocation) | Practice name, DBA, NPI, address, **Delegated**, **Active**, **PNC (Par Non Cred)** checkboxes | **PNC checkbox** now reflects HealthcareFacility.PRM_PNC__c |
| 6 | **Practitioner verification** (PRM_VerifyPractitionerDetails) | Validation of practitioners against PNC/Delegated rules | Uses facility PNC from HealthcareFacility.PRM_PNC__c |

#### Path B: Vendor → Add/Remove PNC

| Step | Screen/Element | What the User Sees | What Changes |
|------|----------------|--------------------|--------------|
| 1 | **Manual Update Options** | Select "Vendor" | No change |
| 2 | **Vendor Change Type** (VendorManualChange) | Select "Add/Remove PNC" | No change |
| 3 | **Search Record** | Enter NPI, Tax ID, or Group Name | No change |
| 4 | **Search Results** (GroupSelectionFlexCard) | List of practice locations; user selects one | PNC column (if shown) uses HealthcareFacility.PRM_PNC__c |
| 5 | **Selected Practice Location** (BlkSelectedPracticeLocation) | Practice details, **PNC (Par Non Cred)** checkbox | **PNC checkbox** now reflects HealthcareFacility.PRM_PNC__c |

#### Summary Flow (Request Type → Steps → Element That Changes)

```
Practice Location → [Request Type] → Search Record → Search Results (GroupSelectionFlexCard) 
  → Select a location → Selected Practice Location block → PNC checkbox (CBPNCCkd / CBPNCUnCkd)
  → Source: Facility:PracLocPNC (must come from HealthcareFacility.PRM_PNC__c)

Vendor → Add/Remove PNC → Search Record → Search Results (GroupSelectionFlexCard)
  → Select a location → Selected Practice Location block → PNC checkbox
  → Source: Facility:PracLocPNC (must come from HealthcareFacility.PRM_PNC__c)
```

---

## Technical Section (For Developers)

### Data Flow Overview

```
PRM_FetchPDMManualUpdateDetails (IP)
  → PRMFetchVendorAndHCFWithNPI (or Tax ID / NPI+Tax ID DataRaptors)
  → Returns Facility[] with PracLocPNC (today: Facility:Account.PRM_PNC__c)
  → GroupSelectionFlexCard displays facilities
  → User selects facility → SelectedFacility:Facility:PracLocPNC
  → SelectedPLPNC formula: %SearchResults:GroupSelectionFlexCard:SelectedFacility:Facility:PracLocPNC%
  → SetSelectedFacility sets PNC = %SearchResults:GroupSelectionFlexCard:SelectedFacility:Facility:PracLocPNC%
  → CBPNCCkd / CBPNCUnCkd checkboxes bound to SelectedPLPNC
  → PRM_VerifyPractitionerDetails receives %PNC% (from SetSelectedFacility)
```

### Components to Update

| Component | Type | Current | Change |
|-----------|------|---------|--------|
| **PRMFetchVendorAndHCFWithNPI** | DataRaptor (OmniDataTransform) | `InputFieldName`: `Facility:Account.PRM_PNC__c` → `Facility:PracLocPNC` | Change to `Facility:PRM_PNC__c` (HealthcareFacility.PRM_PNC__c) |
| **PRMFetchVendorAndHCFWithTaxID** | DataRaptor (OmniDataTransform) | `FormulaExpression`: `IF(ISNOTBLANK(%Facility%),%Vendor:PRM_PNC__c%,\"\")` → PracLocPNC | Change to use `Facility:PRM_PNC__c` instead of `Vendor:PRM_PNC__c` |
| **PRM_IPUtilityHelper** (if used by IP) | Apex | `hcfRecord.Account.PRM_PNC__c` → `PracLocPNC` | Map `hcfRecord` (HealthcareFacility).`PRM_PNC__c` → `PracLocPNC` |
| **NPI+Tax ID path** (PRM_FetchPDMManualUpdateDetails) | Integration Procedure | Merges results from NPI and Tax ID DataRaptors | Ensure both DataRaptors return PracLocPNC from HealthcareFacility |

### OmniScript Elements (No Formula Changes Required)

The OmniScript formulas already reference `PracLocPNC`. Once the DataRaptors and IP return `PracLocPNC` from `HealthcareFacility.PRM_PNC__c`, the UI will display correctly.

| Element | Formula/Binding | Purpose |
|---------|-----------------|---------|
| **SelectedPLPNC** | `%SearchResults:GroupSelectionFlexCard:SelectedFacility:Facility:PracLocPNC%` | Displays PNC for selected location |
| **SetSelectedFacility** | `"PNC": "%SearchResults:GroupSelectionFlexCard:SelectedFacility:Facility:PracLocPNC%"` | Passes PNC to PRM_VerifyPractitionerDetails |
| **CBPNCCkd** / **CBPNCUnCkd** | Bound to SelectedPLPNC | PNC (Par Non Cred) checkboxes in Selected Practice Location block |

### Acceptance Criteria (Given / When / Then)

**AC1: Selected Practice Location – Practice Location path**

**Given** the PDM Specialist is in PRM_PDMManualUpdate_English and selects "Practice Location" and any request type (e.g., Add/Remove a Practitioner, Add/Update/Terminate Current Office Information),  
**When** they search for a group, select a practice location from the GroupSelectionFlexCard, and the "Selected Practice Location" block appears,  
**Then** the PNC (Par Non Cred) checkbox shall display the value from HealthcareFacility.PRM_PNC__c for the selected location. CBPNCCkd and CBPNCUnCkd shall reflect the practice location's PNC status.

**AC2: Selected Practice Location – Vendor Add/Remove PNC path**

**Given** the PDM Specialist selects "Vendor" and "Add/Remove PNC",  
**When** they search and select a practice location from the GroupSelectionFlexCard,  
**Then** the PNC checkbox in the Selected Practice Location block shall display HealthcareFacility.PRM_PNC__c for the selected location.

**AC3: Practitioner verification (PRM_VerifyPractitionerDetails)**

**Given** the PDM Specialist has selected a practice location (Practice Location or Vendor Add/Remove PNC path),  
**When** PRM_VerifyPractitionerDetails runs (e.g., Add/Remove a Practitioner, Add/Update/Terminate Current Office Information),  
**Then** the %PNC% passed to the IP shall be the value from HealthcareFacility.PRM_PNC__c. PNCValid and DelegatedValid formulas shall work correctly: when the facility is PNC, validation passes; when not PNC, at least one PNC practitioner is required.

### Verification Steps for QA

1. **Practice Location path:** Select Practice Location → Add/Remove a Practitioner → Search by NPI → Select a location with PNC = true → Confirm PNC checkbox is checked.
2. **Vendor path:** Select Vendor → Add/Remove PNC → Search → Select a location with PNC = false → Confirm PNC checkbox is unchecked.
3. **PRM_VerifyPractitionerDetails:** When location is PNC, validation should pass even with no PNC practitioners. When location is not PNC, at least one PNC practitioner must be present.

---

# USER STORY 11: Data Model – Deprecate PNC on Vendor Account

**Persona:** Admin  
**Priority:** P2 (After all flows validated)  
**Depends on:** User Stories 3–10 complete and tested

## Story

**As an** Admin,  
**I want to** remove the PRM_PNC__c field from the Vendor/Group Account record type (or deprecate it),  
**So that** PNC is only stored at the practice location level and we avoid data inconsistency.

## Acceptance Criteria (Given / When / Then)

### AC1: Confirm no references

**Given** all Apex, DataRaptors, IPs, and OmniScripts have been updated,  
**When** the Admin runs a global search for `Account.PRM_PNC__c` and `PRM_PNC__c` in the context of Vendor Account,  
**Then** there shall be no remaining references that write to or read from Vendor Account.PRM_PNC__c for practice location PNC. Practitioner Account.PRM_PNC__c (rollup) shall remain.

### AC2: Remove or hide field

**Given** no references remain,  
**When** the Admin removes PRM_PNC__c from the Vendor Account page layout and/or deletes the field (if no longer needed),  
**Then** the field shall no longer be visible or editable for Vendor Accounts. If the field is deleted, ensure no integrations or managed packages depend on it.

### AC3: Documentation

**Given** the change is complete,  
**When** the Admin updates the data dictionary and release notes,  
**Then** it shall document that PNC is now on HealthcareFacility (practice location) and that practitioner Account.PRM_PNC__c is a rollup governed by `PRM_PNCAnyLocation__c` (ALL locations PNC by default; ANY location PNC when the flag is true).

---

## Part 5: Edge Cases & Clarifications

### 5.1 Practitioners with Only Practice Affiliations (No Location Affiliations)

**Current:** PNC uses `PRM_PractitionerPracticeAffiliation` (links to Account/vendor).  
**New:** PNC uses `PRM_PractitionerLocationAffiliation` (links to HealthcareFacility).

**Risk:** If a practitioner has only practice affiliations and no location affiliations, they would have no HealthcareFacility records to evaluate. The new logic would set practitioner PNC = false (in both ALL and ANY modes — the switch does not change the no-locations outcome).

**Recommendation:** Before implementation, run a query to count practitioners who have `PRM_PractitionerPracticeAffiliation` but no `PRM_PractitionerLocationAffiliation`. If the count is significant, consider:
- A transition period with fallback: if no location affiliations, use practice affiliation Account.PRM_PNC__c
- Or a data fix to create/associate location affiliations for those practitioners

### 5.1b The ALL/ANY Switch (`PRM_PNCAnyLocation__c`)

**Default:** false → **ALL** logic (a practitioner is PNC only when all participating locations are PNC). This preserves current behavior for every existing practitioner with no data backfill.

**When true → ANY** logic (a practitioner is PNC when any participating location is PNC). Turning the switch on/off recomputes `PRM_PNC__c` via the Account trigger (§5.1a) even if no location changed.

**Worked example** — practitioner joined to locations [A = PNC, B = non-PNC]:

| `PRM_PNCAnyLocation__c` | Rule | Result `PRM_PNC__c` |
|---|---|---|
| false (default) | ALL locations PNC? (A yes, B no) | **false** |
| true | ANY location PNC? (A yes) | **true** |

**No locations** → `PRM_PNC__c = false` regardless of the switch.

### 5.2 Vendor with Multiple HealthcareFacilities

**Scenario:** One Vendor Account has 5 HealthcareFacilities. Today all inherit Account.PRM_PNC__c. After migration, each HealthcareFacility has its own PRM_PNC__c.

**Migration:** Set each HealthcareFacility.PRM_PNC__c = its parent Account.PRM_PNC__c.  
**Going forward:** Each location can be updated independently (e.g., 3 PNC, 2 non-PNC).

### 5.3 HealthcareFacility with No Account

**Scenario:** HealthcareFacility exists without AccountId (edge case).  
**Migration:** Set PRM_PNC__c = false (default).  
**Rollup:** Such locations would not contribute to practitioner PNC (no vendor context).

---

## Part 6: Implementation Order

| Order | User Story | Owner |
|-------|------------|-------|
| 1 | US1: Add PNC to HealthcareFacility **and `PRM_PNCAnyLocation__c` to Practitioner Account** | Admin |
| 2 | US2: Data migration (facility PNC copy; switch left false) | Admin |
| 3 | US3: Practitioner Participation Form (OmniScript, IPs, DataRaptors) – ALL default / ANY switch | Developer |
| 4 | US4: RCAT / Apex rollup logic (pncOnlyPractitioner, updateAccountPNCHelper, getPIdToHCPFList) – switch-aware | Developer |
| 5 | US5: HealthcareFacility trigger (location PNC change) + ALL/ANY switch recompute | Developer |
| 5B | US5B: PPL trigger (practitioner added/removed from a location) | Developer |
| 6 | US6–8: PNC Migration by Flow (Apex, DataRaptors, IPs per guided flow) | Developer |
| 7 | US9: Credentialing flows validation | Credentialing Specialist + Developer |
| 8 | US10: PDM flows validation | PDM Specialist + Developer |
| 9 | US11: Deprecate Account PNC | Admin |

---

## Part 7: Testing Checklist

- [ ] **Practitioner Participation Form (US3) – default ALL:** Submit form (practitioner `PRM_PNCAnyLocation__c` = false) joining locations that are ALL PNC → PNCFlag = true, case manager Record Type = PNC
- [ ] **Practitioner Participation Form (US3) – default ALL, mixed:** Submit form (flag false) joining a mix of PNC and non-PNC locations → PNCFlag = false, case manager Record Type = Application Review
- [ ] **Practitioner Participation Form (US3) – ANY:** Submit form with `PRM_PNCAnyLocation__c` = true joining at least one PNC location → PNCFlag = true, Record Type = PNC
- [ ] Unit tests for pncOnlyPractitioner – **ALL default** (all PNC → true; one non-PNC → false; no locations → false)
- [ ] Unit tests for pncOnlyPractitioner – **ANY (flag on)** (one PNC → true; all non-PNC → false; no locations → false)
- [ ] Unit tests for updateAccountPNCHelper – ALL and ANY branches, HealthcareFacility source
- [ ] Unit tests for getPIdToHCPFList (HealthcareFacility.PRM_PNC__c + Practitioner.Account.PRM_PNCAnyLocation__c)
- [ ] HealthcareFacility trigger tests (insert, update, bulk) – ALL and ANY practitioners
- [ ] Account trigger test – flipping `PRM_PNCAnyLocation__c` recomputes PRM_PNC__c with no location change (§5.1a)
- [ ] DataRaptor export/import validation
- [ ] Off-Cycle Credentialing flow – PNC display and validation
- [ ] Practitioner Termination / Recred flows – PNC display
- [ ] PDM Manual Update – Add/Remove PNC
- [ ] Provider Change Form – verification
- [ ] Recred Termination Letter – PNC locations excluded
- [ ] CAQH batch – PNC practitioners excluded (unchanged behavior)
- [ ] RCAT / Future-dated processing – PNC rollup correct

---

## Part 8: Rollback Plan

If issues are found post-deployment:
1. Revert Apex (trigger, helper, batch) to previous version.
2. Keep HealthcareFacility.PRM_PNC__c populated (no need to clear).
3. Re-enable Account trigger for Vendor PNC if it was disabled.
4. Revert DataRaptor and IP changes via version control.
5. Communicate to Credentialing and PDM teams to use previous behavior until fix is deployed.
