# PAR Address Screen — Designate a New Primary Practice Location When Practitioner Already Has an Active Primary

**Document Version:** 1.0
**Created Date:** April 30, 2026
**Vertical:** Provider Network Management (PNM)
**Source Requirement:** Screenshot — `Practitioner Participation Request → Address Screen` Primary Practice Location handoff (April 30, 2026)
**OmniScript:** `PRM_PractitionerParticipationAddressForm_English` (currently v55), `PRM_PractitionerParticipationForm_English` (currently v112)
**Object Impacted:** `HealthcarePractitionerFacility` (HCPF / Practice Location to Practitioner)
**Related Documents:**
- `PAR_DeniedTerminated_RecordReuse_User_Stories.md`
- `PAR_Form_PNC_Path_User_Stories.md`
- `Initial_Cred_Add_Practice_Location_User_Stories.md`
- `AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md`

---

## Source Requirement (Verbatim from Screenshot)

> **1. On Practitioner Participation Request → Address Screen, if Practitioner has existing Active Practice Location to Practitioner where Primary = TRUE:**
>
> - **"Is this the Practitioner's Primary Practice Location?"**
>   - **No** can be selected if Practitioner has existing Primary Practice Location
>   - **If Yes is selected:**
>     - **Practice Location to Practitioner (HealthcarePractitionerFacility) — New Primary**
>       - `Primary = TRUE`
>   - Upon **PDA Review & Update** completion → Upon **Activation of New Primary Practice Location to Practitioner** → **Existing Primary Practice Location to Practitioner** is updated with:
>     - `Primary = FALSE`

---

## Executive Summary

When a credentialed Practitioner already has an **Active** `HealthcarePractitionerFacility` (HCPF) record with `PRM_Primary__c = TRUE` and a new Practitioner Participation Request (PAR) is submitted that adds another practice location, the Address screen asks **"Is this your Practitioner's Primary Practice Location?"**. Today the screen always permits Yes/No, but the back-end "downgrade" of the prior primary on activation is not enforced as a discrete, deterministic step gated to PDA Review & Update activation.

This requirement defines the explicit business rule:

1. **Capture intent on the form** — Selecting **No** is always valid when an existing Primary HCPF exists; selecting **Yes** designates the new HCPF as the incoming Primary and queues a demotion of the prior primary.
2. **Defer the side-effect to activation** — The prior Primary HCPF must remain `PRM_Primary__c = TRUE` and `IsActive = TRUE` until the PDA Review & Update step **activates** the new Primary HCPF. Only then is the prior record updated to `PRM_Primary__c = FALSE`.
3. **Atomicity** — A Practitioner must end the activation transaction with **exactly one** Active HCPF where `PRM_Primary__c = TRUE`. No window in which there are zero, two, or more is permitted.

---

## Use Case Matrix

| # | Existing State (Practitioner) | User Action on Address Screen | Expected Behavior at Address Save | Expected Behavior at PDA Activation |
|---|-------------------------------|-------------------------------|-----------------------------------|-------------------------------------|
| UC-1 | No existing HCPF where `IsActive=TRUE` AND `PRM_Primary__c=TRUE` | "Is this Primary?" = **Yes** (must be Yes for first PL) | New HCPF queued with `PRM_Primary__c=TRUE` | New HCPF activated with `Primary=TRUE`. No demotion needed. |
| UC-2 | **Existing Active Primary HCPF** | "Is this Primary?" = **No** | New HCPF queued with `PRM_Primary__c=FALSE` | New HCPF activated with `Primary=FALSE`. Existing Primary unchanged. |
| UC-3 | **Existing Active Primary HCPF** | "Is this Primary?" = **Yes** (new Primary intent) | New HCPF queued with `PRM_Primary__c=TRUE`. Existing Primary HCPF marked for demotion (`PRM_PendingPrimaryDemotion__c = TRUE` or equivalent staging flag) but not yet flipped. | On Activation: New HCPF activated with `Primary=TRUE`. **In the same transaction**, prior Active Primary HCPF updated with `Primary=FALSE`. |
| UC-4 | Multiple Active HCPFs but none with `Primary=TRUE` (data anomaly) | "Is this Primary?" = **Yes** | Block save; surface remediation message; require admin cleanup. | N/A |
| UC-5 | Existing Active Primary HCPF, but PAR is **denied** mid-flow | "Is this Primary?" = **Yes** had been selected | Demotion never executes (case did not reach PDA Activation). Prior primary stays `Primary=TRUE`. | N/A |

---

# USER STORY 1: PAR Address Screen — Capture "New Primary" Intent When Practitioner Has an Existing Active Primary HCPF

**Persona:** Sr. Data Reporting Analyst / Credentialing Specialist, Developer
**Priority:** P0
**OmniScript:** `PRM_PractitionerParticipationAddressForm_English` (v55) — `PractitionerAddress` step → `GroupAddressBlock` → `PrimaryOfficeAddressBlock.PrimaryPrimaryPractice` Radio AND `AdditionalAddressesBlock.AdditionalAddress.AdditionalPrimaryPractice` Radio
**LWC Override:** `prmPrimaryPracticeLogic` (`force-app/main/default/lwc/prmPrimaryPracticeLogic/`)
**Integration Procedures:** `PRM_ExistingPrimaryPracticeLocationLogic_English` (v4), `PRM_PractitionerAddressCreation`, `PRM_CreateParFormRecords`
**DataRaptors:** `PRMDRCheckIfPracticeToPractitionerExist`, `PRMDRTPractitionerPracticeLoc`, `PRMUpdatePracticeToPractitioner`
**Relevant Requirements:** Screenshot UC-1, UC-2, UC-3, UC-4 above

---

## Story

**As a** Sr. Data Reporting Analyst submitting a Practitioner Participation Request,
**I want** the Address screen to surface the existing Active Primary practice location to me, allow me to designate the new practice location as the practitioner's Primary by answering **Yes**, and persist that intent without immediately mutating the prior primary,
**So that** I can correctly reflect a practitioner's change in primary practice location during the PAR intake without prematurely flipping the prior primary or violating the "exactly one Active Primary" constraint.

**Why it matters:** Practitioners frequently change primary practice locations during a participation event (relocation, group change, hospital affiliation switch). Without explicit intent capture and deferred activation, today's flow can either (a) leave two Active Primary HCPF records (data integrity break — downstream rosters, directory, and provider directory feeds break), or (b) prematurely demote the prior primary while the new request is still in PSV/QC/Committee, which mis-states the practitioner's primary location to downstream consumers (CAQH, SendGrid letters, member-facing directory) for the duration of the case.

---

## Scope

| Flow | OmniScript | Affected Step / Element | Data Source |
|------|------------|-------------------------|-------------|
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationAddressForm_English` v55 | `PractitionerAddress` → `GroupAddressBlock` → `PrimaryOfficeAddressBlock.PrimaryPrimaryPractice` (Radio) | `prmPrimaryPracticeLogic` LWC override |
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationAddressForm_English` v55 | `PractitionerAddress` → `GroupAddressBlock` → `AdditionalAddressesBlock.AdditionalAddress.AdditionalPrimaryPractice` (Radio) | `prmPrimaryPracticeLogic` LWC override |
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationForm_English` v112 | Hidden context: `ExistingPrimaryHCPFId`, `ExistingPrimaryFlag` | `PRMDRTPractitionerPracticeLoc` (DR Extract) — to be extended |

---

## Current State (from codebase)

### `PRM_PractitionerParticipationAddressForm_English_55.os-meta.xml`

- **Element `PrimaryPrimaryPractice`** (Radio, level 4, sequence 0.0): label *"Is this your Practitioner's Primary Practice Location?"*; options Yes/No; `required: true`; `lwcComponentOverride: prmPrimaryPracticeLogic`. Located inside `PrimaryOfficeAddressBlock`.
- **Element `AdditionalPrimaryPractice`** (Radio, level 4, sequence 2.0): same label; `required: true` on `GroupAddressBlock` index 0 and `required: false` on subsequent indexes. Located inside repeatable `AdditionalAddressesBlock.AdditionalAddress`.
- **Validation `text`:** *"One Primary or Additional Address must be selected as your Primary Practice Location."* — fires when no element across all blocks resolves to `Yes`.

### `prmPrimaryPracticeLogic.js` (LWC override)

- **File:** `force-app/main/default/lwc/prmPrimaryPracticeLogic/prmPrimaryPracticeLogic.js`
- **Behavior:** When the user picks **Yes** on any `PrimaryPrimaryPractice` or `AdditionalPrimaryPractice` radio, the override walks `GroupAddressBlock[*]` and forces every other Primary/Additional Practice radio to **No**, then `omniApplyCallResp`s the patched JSON. Cached previous selection (`cachedVal.cachedPrimaryAddd`) prevents thrash.
- **Gap:** The override does not **read** existing HCPF state for the practitioner; it only enforces single-select within the form. Nothing today flags "an Active Primary HCPF already exists for this practitioner outside of the case."

### `PRMDRCheckIfPracticeToPractitionerExist` (DR Extract)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDRCheckIfPracticeToPractitionerExist_1.rpt-meta.xml`
- **Returns:** existing HCPF rows for `(AccountId, PractitionerId, RecordType=PRM_PractitionerPracticeAffiliation)`.
- **Gap:** Filter is by Account (group); does not return cross-group existing Active Primary HCPFs for the practitioner. Need a sibling extract that returns *all* `IsActive=TRUE AND PRM_Primary__c=TRUE` HCPFs for the practitioner regardless of account.

### `PRM_ExistingPrimaryPracticeLocationLogic_English` (IP, v4)

- **Location:** `force-app/main/default/omniIntegrationProcedures/PRM_ExistingPrimaryPracticeLocationLogic_English_4.oip-meta.xml`
- **Behavior:** Branches between create-new vs. update-existing on Practice-to-Practitioner records based on `PRMDRCheckIfPracticeToPractitionerExist` output.
- **Gap:** Does not stage the "demote prior primary" instruction; no field today carries the deferred demotion intent into PDA activation.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **HealthcarePractitionerFacility** | Custom Field | New checkbox `PRM_PendingPrimaryDemotion__c` (Default = FALSE). Marks an existing Active Primary HCPF that is to be demoted on activation of a new Primary HCPF in the same case. (Or use a Lookup `PRM_SupersedingPrimaryHCPF__c` to the new HCPF — see Clarification Q1.) |
| **HealthcarePractitionerFacility** | Custom Field | New checkbox `PRM_StagedAsNewPrimary__c` (Default = FALSE). Marks the new HCPF that is to become Primary upon activation. Cleared when activation completes. |
| **PRMDRGetExistingActivePrimaryHCPF** *(new)* | DataRaptor Extract | Input: `PractitionerId`. Output: `ExistingPrimaryHCPF { Id, AccountId, PRM_Primary__c, IsActive, EffectiveFrom, AccountName }`. Filter: `PractitionerId = :PractitionerId AND IsActive = TRUE AND PRM_Primary__c = TRUE AND RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'`. Sort: `LastModifiedDate DESC`. Returns 0 or 1; >1 indicates anomaly (UC-4). |
| **PRM_PractitionerParticipationForm_English** v113 | OmniScript Element (DataRaptor Extract Action) | Add step to PAR Form pre-load that calls `PRMDRGetExistingActivePrimaryHCPF` and stores result on `Practitioner.ExistingPrimaryHCPF`. |
| **PRM_PractitionerParticipationAddressForm_English** v56 | OmniScript Element (Text Block) | Add a conditional `existingPrimaryAlertTB` Text Block on `PractitionerAddress` step shown when `Practitioner.ExistingPrimaryHCPF.Id != null`: *"This Practitioner currently has an Active Primary Practice Location at \{AccountName\} (effective \{EffectiveFrom\}). Selecting **Yes** below will designate this new location as the Primary upon PDA activation, and the existing primary will be set to non-primary."* |
| **PRM_PractitionerParticipationAddressForm_English** v56 | OmniScript Validation | Block save with error `OnlyOneActivePrimaryAllowedErr` when `Practitioner.ExistingPrimaryHCPF` returns more than 1 row (UC-4 anomaly). |
| **prmPrimaryPracticeLogic** (LWC) | Enhancement | When `selectedPrimaryPractice == "Yes"`, in addition to forcing siblings to `No`, write `Practitioner.NewPrimaryIntent = TRUE` (or equivalent flag at the OS root) so the IP downstream knows a demotion needs to be staged. When `No`, write `Practitioner.NewPrimaryIntent = FALSE`. |
| **PRM_ExistingPrimaryPracticeLocationLogic_English** v5 | Integration Procedure | New branch: when `Practitioner.NewPrimaryIntent = TRUE` AND `Practitioner.ExistingPrimaryHCPF.Id != null`: (a) on the new HCPF, set `PRM_StagedAsNewPrimary__c = TRUE` and `PRM_Primary__c = TRUE`; (b) on the existing Primary HCPF, set `PRM_PendingPrimaryDemotion__c = TRUE` (do not flip `PRM_Primary__c` yet — that happens at activation). |
| **PRMUpdatePracticeToPractitioner** | DataRaptor Load | Add output mappings for `PRM_StagedAsNewPrimary__c` and `PRM_PendingPrimaryDemotion__c`. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRGetExistingActivePrimaryHCPF` *(new)* | DR Extract | `PractitionerId` | `ExistingPrimaryHCPF[ Id, AccountId, AccountName, PRM_Primary__c, IsActive, EffectiveFrom ]` | New DR — filter to `IsActive=TRUE AND PRM_Primary__c=TRUE AND RecordType='PRM_PractitionerPracticeAffiliation'`. |
| `PRM_ExistingPrimaryPracticeLocationLogic_English` v5 | IP | New HCPF JSON, `Practitioner.NewPrimaryIntent`, `Practitioner.ExistingPrimaryHCPF.Id` | HCPF Upsert payload | Add staging branch — set `PRM_StagedAsNewPrimary__c` on new HCPF; set `PRM_PendingPrimaryDemotion__c` on existing primary. Do NOT mutate `PRM_Primary__c` on existing primary in this IP. |
| `PRMUpdatePracticeToPractitioner` | DR Load | HCPF JSON | HCPF record upserts | Map new staging fields to output. |

### Example — IP Output Patch (US1 path)

```json
{
  "HCPF_NEW": {
    "PractitionerId": "0HD...",
    "AccountId": "001...new...",
    "PRM_Primary__c": true,
    "IsActive": false,
    "PRM_Pending__c": true,
    "PRM_StagedAsNewPrimary__c": true,
    "RecordType.DeveloperName": "PRM_PractitionerPracticeAffiliation"
  },
  "HCPF_EXISTING_PRIMARY": {
    "Id": "0Hp...existing...",
    "PRM_Primary__c": true,
    "IsActive": true,
    "PRM_PendingPrimaryDemotion__c": true
  }
}
```

---

## Acceptance Criteria

**AC-1 (UC-3 happy path — capture intent):**
**Given** Practitioner P has exactly one Active HCPF where `IsActive=TRUE AND PRM_Primary__c=TRUE` (call it HCPF_A),
**And** a new PAR case is opened for P at a different group/practice location (HCPF_B is being added),
**When** the user reaches the Address screen and selects **Yes** on `PrimaryPrimaryPractice` for HCPF_B,
**Then** the conditional alert text shall reference HCPF_A's Account name and effective-from date,
**And** on Save/Next, HCPF_B is upserted with `PRM_Primary__c=TRUE`, `PRM_StagedAsNewPrimary__c=TRUE`, `IsActive=FALSE`, `PRM_Pending__c=TRUE`,
**And** HCPF_A is updated with `PRM_PendingPrimaryDemotion__c=TRUE`,
**And** HCPF_A retains `PRM_Primary__c=TRUE` and `IsActive=TRUE` (no premature flip).

**AC-2 (UC-2 — explicit "No"):**
**Given** Practitioner P has an existing Active Primary HCPF_A,
**When** the user selects **No** on the new HCPF_B `PrimaryPrimaryPractice` radio,
**Then** HCPF_B is upserted with `PRM_Primary__c=FALSE`, `PRM_StagedAsNewPrimary__c=FALSE`,
**And** HCPF_A is unchanged (`PRM_PendingPrimaryDemotion__c` stays FALSE).

**AC-3 (UC-1 — first-time primary, no existing primary):**
**Given** Practitioner P has zero HCPFs where `IsActive=TRUE AND PRM_Primary__c=TRUE`,
**When** the user reaches the Address screen,
**Then** the existing-primary alert text is **not** displayed,
**And** at least one block must be selected as Primary = Yes (existing validation `OneAddressMustBePrimaryErr` continues to fire),
**And** on Save, the chosen HCPF is upserted with `PRM_Primary__c=TRUE`, `PRM_StagedAsNewPrimary__c=FALSE` (no demotion to stage).

**AC-4 (UC-4 — anomaly: 2+ Active Primary):**
**Given** Practitioner P has 2 or more HCPFs where `IsActive=TRUE AND PRM_Primary__c=TRUE` (data anomaly),
**When** the Address screen pre-load fires `PRMDRGetExistingActivePrimaryHCPF`,
**Then** the OmniScript shall display a non-dismissable error block: *"Data anomaly detected — practitioner has more than one active primary practice location. Contact a Salesforce Admin before continuing this PAR request. (Reference: \{listOfHCPFIds\})"*,
**And** the **Next** button on the Address step is disabled,
**And** no upsert is attempted.

**AC-5 (UC-3 — only one Yes within the case):**
**Given** the user selected **Yes** on HCPF_B Primary radio,
**When** the user toggles **Yes** on a second block (HCPF_C) within the same PAR case,
**Then** the existing `prmPrimaryPracticeLogic` LWC behavior shall fire and force HCPF_B Primary radio back to **No**,
**And** only HCPF_C carries `PRM_StagedAsNewPrimary__c=TRUE` on Save.

**AC-6 (Data integrity — single staged primary per case):**
**Given** any valid Save state,
**Then** at most one HCPF per case (per Practitioner) shall have `PRM_StagedAsNewPrimary__c=TRUE`,
**And** at most one existing HCPF per Practitioner shall have `PRM_PendingPrimaryDemotion__c=TRUE`.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the demotion intent be modeled as two boolean checkboxes (`PRM_PendingPrimaryDemotion__c`, `PRM_StagedAsNewPrimary__c`) or as a single self-referential lookup (`PRM_SupersedingPrimaryHCPF__c` on the prior primary, pointing to the new HCPF)? Lookup is auditable but adds a constraint that the new HCPF must exist before the lookup can be set. | Object Model | Technical / BA |
| 2 | If a PAR case is **denied** at Committee/PSV/QC after intent was captured, do we clear the staging flags on case closure, or leave them in place for audit? | Lifecycle | BA / Ops |
| 3 | Is the existing primary always at the **same** Vendor/Account, or can the new primary be at a **different** Vendor (group change)? The DR filter must accommodate both. | Scope | Product |
| 4 | If the practitioner has multiple Active Primary HCPFs today (anomaly UC-4), do we need a one-time data fix script before deploying this enhancement? Roughly how many records are in this state? | Data Quality | Ops / Technical |
| 5 | Should the conditional alert text on the Address screen be a hard-styled warning banner (yellow) or an inline help text? UI wireframe needed. | UX | Product / Design |
| 6 | When the user picks **Yes** for a new primary, does the prior primary's HCFN (Healthcare Facility Network) records need any change (effective-end on prior, effective-start on new) at activation, or is `PRM_Primary__c` flip sufficient? | Downstream Impact | Network Operations |
| 7 | How should this interact with the **Off Cycle** flow's `PRMTransformPrimaryAddressForOffCycle` (which has a similar Primary toggle)? Should both flows write the same staging fields and share the activation IP, or do they remain separate? | Cross-Flow | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `HealthcarePractitionerFacility` object | Custom Fields | HIGH | Two new fields (`PRM_PendingPrimaryDemotion__c`, `PRM_StagedAsNewPrimary__c`); permission set + page layout updates required for Admin and Credentialing Specialist profiles. |
| `PRM_PractitionerParticipationAddressForm_English` | OmniScript | HIGH | New conditional alert TB + new validation + new pre-load DR call. Must be re-cloned to v56. |
| `PRM_PractitionerParticipationForm_English` | OmniScript | MEDIUM | Pre-load DR call to populate `Practitioner.ExistingPrimaryHCPF`; v113. |
| `prmPrimaryPracticeLogic` (LWC) | LWC | MEDIUM | Adds writes to `Practitioner.NewPrimaryIntent` based on selection. Existing single-select enforcement preserved. |
| `PRM_ExistingPrimaryPracticeLocationLogic_English` | IP | HIGH | New branch + staging-field writes; v5. |
| `PRMUpdatePracticeToPractitioner` | DataRaptor Load | LOW | Two new field mappings. |
| `PRMDRGetExistingActivePrimaryHCPF` | DataRaptor Extract | LOW | New, additive. |
| Reporting / Provider Directory feeds | Downstream | MEDIUM | No change in steady state, but consumers must understand `PRM_Primary__c` only flips at activation, not at form save. Document in data dictionary. |
| Off Cycle (`PRMTransformPrimaryAddressForOffCycle`) | Cross-Flow | MEDIUM | Pending alignment decision (Q7); may need same staging fields applied. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_PendingPrimaryDemotion__c` field | Custom Field | S | Checkbox + permission set + layout. |
| `PRM_StagedAsNewPrimary__c` field | Custom Field | S | Checkbox + permission set + layout. |
| `PRMDRGetExistingActivePrimaryHCPF` | New DataRaptor Extract | M | Single-table query, simple sort + filter. |
| `PRM_PractitionerParticipationForm_English` v113 | OmniScript pre-load step | M | Add DR Action + assign result to `Practitioner.ExistingPrimaryHCPF`. |
| `PRM_PractitionerParticipationAddressForm_English` v56 | OS Text Block + validation + clone | L | New conditional alert + new validation + version clone + regression on existing Yes/No flow. |
| `prmPrimaryPracticeLogic` LWC enhancement | LWC | M | Write `NewPrimaryIntent` to OS root JSON; add unit tests for new write path. |
| `PRM_ExistingPrimaryPracticeLocationLogic_English` v5 | IP staging branch | XL | New branch + staging writes + integration tests; ensure `IsActive` and `PRM_Primary__c` of existing primary are NOT mutated. |
| `PRMUpdatePracticeToPractitioner` | DR Load mapping | S | Add 2 output fields. |
| Apex test class updates | Test | M | Cover UC-1..UC-5; one-time data anomaly path. |
| Documentation — data dictionary update for Provider Directory consumers | Docs | S | Note the deferred-flip semantics. |

**Total Estimated Effort:** ~5–7 dev days (1.0–1.5 sprint week) — **L/XL overall** — *AI-estimated, validate with team*

---

# USER STORY 2: PDA Review & Update Activation — Demote Existing Primary HCPF When New Primary Is Activated

**Persona:** PDM Specialist / PDA Reviewer, Developer
**Priority:** P0
**OmniScript:** N/A — server-side activation triggered at PDA Review & Update completion
**Integration Procedures:** `PRM_ManualChangePDAUpdateParent_Procedure` (or PAR equivalent — see Q1 below), `PRM_RecredPDAUpdateRecordsParent_Procedure`
**Apex / Triggers:** `PRM_HCFacilityTriggerHelper`, `PRM_HCPractitionerFacilityTrigger` (HCPF before-update / after-update)
**DataRaptors:** `PRMUpdatePracticeToPractitioner`
**Relevant Requirements:** Screenshot UC-3 activation clause; depends on US1 staging flags

---

## Story

**As a** PDM Specialist completing PDA Review & Update on a PAR case,
**I want** the system to atomically activate the staged new Primary HCPF and demote the prior Active Primary HCPF (`PRM_Primary__c → FALSE`) in the same transaction,
**So that** the Practitioner ends each PAR activation with **exactly one** Active HCPF where `PRM_Primary__c = TRUE`, with no temporal window in which the Practitioner has zero or two Active Primary practice locations visible to downstream consumers.

**Why it matters:** The demotion must be deterministic and atomic. Any drift (e.g., the new primary activates but the prior primary is not demoted, or vice versa) corrupts the practitioner's record in member-facing directory feeds, in CAQH Roster Submissions, and in welcome-letter generation. This is the activation half of the contract started in US1.

---

## Scope

| Flow | Trigger | Affected Records | Outcome |
|------|---------|------------------|---------|
| PAR | PDA Review & Update completion → HCPF activation step | New HCPF (`PRM_StagedAsNewPrimary__c=TRUE`) and prior Primary HCPF (`PRM_PendingPrimaryDemotion__c=TRUE`) for the same Practitioner | New HCPF: `IsActive=TRUE`, `PRM_Primary__c=TRUE`, `PRM_StagedAsNewPrimary__c=FALSE`, `PRM_Pending__c=FALSE`. Prior HCPF: `PRM_Primary__c=FALSE`, `PRM_PendingPrimaryDemotion__c=FALSE`. |

---

## Current State (from codebase)

### `PRM_HCFacilityTriggerHelper` / HCPF triggers

- HCPF is updated in many flows (PAR, Off Cycle, Recred, PDM Manual Update, Provider Change). Today there is no centralized "activate new primary + demote prior primary" routine.

### PDA Update IPs

- `PRM_ManualChangePDAUpdateParent_Procedure` and the corresponding flow-specific PDA update IPs perform record activation. They do not currently look for `PRM_StagedAsNewPrimary__c` or `PRM_PendingPrimaryDemotion__c` (these fields don't exist yet — see US1).

### Gap

- There is no atomic operation that, on activation of a staged-as-new primary HCPF, finds the prior `PRM_PendingPrimaryDemotion__c=TRUE` HCPF for the same Practitioner and flips its `PRM_Primary__c` to FALSE in the same DML transaction.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **PRM_HCPractitionerFacilityActivationService** *(new)* | Apex Service | New service class with method `activateStagedPrimary(Set<Id> stagedHCPFIds)` that, for each staged HCPF: (1) sets `IsActive=TRUE`, `PRM_Primary__c=TRUE`, `PRM_StagedAsNewPrimary__c=FALSE`, `PRM_Pending__c=FALSE`; (2) finds the prior primary HCPF for the same `PractitionerId` where `PRM_PendingPrimaryDemotion__c=TRUE AND IsActive=TRUE AND PRM_Primary__c=TRUE`; (3) updates that prior HCPF with `PRM_Primary__c=FALSE`, `PRM_PendingPrimaryDemotion__c=FALSE` in the same DML transaction. |
| **PRM_HCFacilityTriggerHelper** | Apex Trigger Handler | On HCPF after-update, when `PRM_StagedAsNewPrimary__c` flips from TRUE → FALSE AND `IsActive` flipped from FALSE → TRUE, invoke `PRM_HCPractitionerFacilityActivationService.activateStagedPrimary` if not already invoked from the PDA IP. (Defensive — covers paths that bypass the IP.) |
| **PDA Update IPs** (PAR-specific, e.g., `PRM_ManualChangePDAUpdateParent_Procedure` v3 — confirm exact IP in Q1) | IP | Add a step that, after the new HCPF is activated, calls `PRM_HCPractitionerFacilityActivationService.activateStagedPrimary` (Remote Action) with the activated HCPF Id(s). |
| **PRMUpdatePracticeToPractitioner** | DR Load | Ensure mapping for `PRM_Primary__c=FALSE` and `PRM_PendingPrimaryDemotion__c=FALSE` exists for the demoted record path. |
| **HCPF Validation Rule** *(new)* | Validation Rule | `PRM_OnlyOneActivePrimaryPerPractitioner` — Salesforce duplicate matching is not feasible cross-account; instead, in `PRM_HCFacilityTriggerHandler` before-insert/before-update, throw `addError` if the operation would result in `>1` HCPFs for the same Practitioner where `IsActive=TRUE AND PRM_Primary__c=TRUE`. |
| **Audit / Field History Tracking** | Config | Enable Field History Tracking on `HCPF.PRM_Primary__c` and `HCPF.IsActive` if not already enabled. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRM_ManualChangePDAUpdateParent_Procedure` (or PAR equivalent — see Q1) | IP | `CaseId`, activated HCPF Ids | n/a | Add Remote Action step calling `PRM_HCPractitionerFacilityActivationService.activateStagedPrimary` after HCPF activation step. |
| `PRMUpdatePracticeToPractitioner` | DR Load | HCPF JSON for demoted record | HCPF update | Confirm `PRM_Primary__c=FALSE` and `PRM_PendingPrimaryDemotion__c=FALSE` are mapped. |

### Example — Apex Service Skeleton

```apex
public with sharing class PRM_HCPractitionerFacilityActivationService {

    public static void activateStagedPrimary(Set<Id> stagedHcpfIds) {
        if (stagedHcpfIds == null || stagedHcpfIds.isEmpty()) return;

        List<HealthcarePractitionerFacility> staged = [
            SELECT Id, PractitionerId, PRM_StagedAsNewPrimary__c, IsActive, PRM_Primary__c
            FROM HealthcarePractitionerFacility
            WHERE Id IN :stagedHcpfIds
              AND PRM_StagedAsNewPrimary__c = TRUE
        ];
        if (staged.isEmpty()) return;

        Set<Id> practitionerIds = new Set<Id>();
        for (HealthcarePractitionerFacility h : staged) practitionerIds.add(h.PractitionerId);

        Map<Id, HealthcarePractitionerFacility> priorPrimaryByPractitioner = new Map<Id, HealthcarePractitionerFacility>();
        for (HealthcarePractitionerFacility prior : [
            SELECT Id, PractitionerId, PRM_Primary__c, PRM_PendingPrimaryDemotion__c, IsActive
            FROM HealthcarePractitionerFacility
            WHERE PractitionerId IN :practitionerIds
              AND PRM_PendingPrimaryDemotion__c = TRUE
              AND IsActive = TRUE
              AND PRM_Primary__c = TRUE
              AND Id NOT IN :stagedHcpfIds
        ]) {
            priorPrimaryByPractitioner.put(prior.PractitionerId, prior);
        }

        List<HealthcarePractitionerFacility> toUpdate = new List<HealthcarePractitionerFacility>();
        for (HealthcarePractitionerFacility newPrimary : staged) {
            newPrimary.IsActive = true;
            newPrimary.PRM_Primary__c = true;
            newPrimary.PRM_StagedAsNewPrimary__c = false;
            newPrimary.PRM_Pending__c = false;
            toUpdate.add(newPrimary);

            HealthcarePractitionerFacility prior = priorPrimaryByPractitioner.get(newPrimary.PractitionerId);
            if (prior != null) {
                prior.PRM_Primary__c = false;
                prior.PRM_PendingPrimaryDemotion__c = false;
                toUpdate.add(prior);
            }
        }
        update toUpdate;
    }
}
```

---

## Acceptance Criteria

**AC-1 (UC-3 happy path — atomic flip):**
**Given** HCPF_B (new) was staged with `PRM_StagedAsNewPrimary__c=TRUE` and `PRM_Primary__c=TRUE` and `IsActive=FALSE`,
**And** HCPF_A (existing) is `IsActive=TRUE, PRM_Primary__c=TRUE, PRM_PendingPrimaryDemotion__c=TRUE`,
**When** PDA Review & Update completion activates HCPF_B,
**Then** in a single DML transaction, HCPF_B becomes `IsActive=TRUE, PRM_Primary__c=TRUE, PRM_StagedAsNewPrimary__c=FALSE, PRM_Pending__c=FALSE`,
**And** HCPF_A becomes `IsActive=TRUE, PRM_Primary__c=FALSE, PRM_PendingPrimaryDemotion__c=FALSE`,
**And** Field History on both records reflects the changes,
**And** the Practitioner has exactly one HCPF where `IsActive=TRUE AND PRM_Primary__c=TRUE`.

**AC-2 (UC-2 — no demotion needed):**
**Given** HCPF_B was staged with `PRM_StagedAsNewPrimary__c=FALSE` (user picked No on the form),
**When** activation occurs,
**Then** HCPF_B becomes `IsActive=TRUE, PRM_Primary__c=FALSE`,
**And** HCPF_A is unchanged,
**And** no demotion DML is issued.

**AC-3 (Validation rule prevents drift):**
**Given** any DML operation on HCPF that would result in a Practitioner having `>1` rows with `IsActive=TRUE AND PRM_Primary__c=TRUE`,
**When** the operation is attempted,
**Then** the trigger handler throws `addError("A Practitioner can have at most one Active Primary Practice Location at a time.")`,
**And** no records are committed.

**AC-4 (Idempotency):**
**Given** `activateStagedPrimary` is invoked twice with the same staged HCPF Id (e.g., retry, batch reprocess),
**Then** the second invocation is a no-op (no records match `PRM_StagedAsNewPrimary__c=TRUE` after the first run),
**And** no duplicate DML occurs.

**AC-5 (Cross-flow tolerance):**
**Given** the same staging-and-activation pattern is invoked from the Off Cycle flow's PDA update IP,
**Then** the service behaves identically (same demotion semantics).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which PDA Update IP is the canonical one for PAR activation — `PRM_ManualChangePDAUpdateParent_Procedure`, `PRM_RecredPDAUpdateRecordsParent_Procedure`, or a PAR-specific variant? Need exact IP name to wire the activation hook. | Integration | Technical |
| 2 | If the prior primary HCPF was somehow already deactivated (`IsActive=FALSE`) between form save and PDA activation, do we still need the demotion update (no-op)? Confirm safe behavior. | Edge Case | BA / Technical |
| 3 | Is there a notification/email expected to the Network Operations team when a primary is demoted (audit trail beyond Field History)? | Notifications | Ops |
| 4 | For the validation rule (AC-3), can the trigger handler do a `SELECT COUNT()` per practitioner per transaction efficiently, or do we need a flag-based approach (e.g., `PRM_HasActivePrimary__c` rollup)? | Performance | Technical |
| 5 | Should activation update the EffectiveFrom/EffectiveTo on prior primary HCPF (set EffectiveTo = today) when demoted, or leave dates untouched? | Data Model | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `HealthcarePractitionerFacility` triggers | Trigger Handler | HIGH | New activation hook + new validation. Regression risk on all flows that touch HCPF (PAR, Off Cycle, Recred, PDM Manual Update, Provider Change). |
| `PRM_HCPractitionerFacilityActivationService` | Apex (new) | MEDIUM | New service; isolated; covered by unit + integration tests. |
| PAR PDA Update IP (TBD per Q1) | IP | MEDIUM | Single Remote Action step addition. |
| Field History Tracking | Config | LOW | Enable on `PRM_Primary__c`, `IsActive`, `PRM_PendingPrimaryDemotion__c`, `PRM_StagedAsNewPrimary__c`. |
| Provider Directory feeds | Downstream | MEDIUM | No schema change; consumers see atomic flip. Data dictionary update needed. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_HCPractitionerFacilityActivationService` | New Apex class | L | Include unit tests for AC-1..AC-4. |
| `PRM_HCFacilityTriggerHelper` | Apex Trigger Handler edit | L | Add validation rule logic for AC-3 + activation hook. |
| PAR PDA Update IP | IP edit | M | Add Remote Action step (after exact IP confirmed in Q1). |
| `PRMUpdatePracticeToPractitioner` mapping confirmation | DR Load | S | Mostly verification. |
| Validation Rule design + perf check | Apex/Config | M | Confirm SOQL governor safety per Q4. |
| Field History Tracking config | Config | S | Setup, no code. |
| Apex test class updates (PAR + Off Cycle + Recred regression) | Test | XL | Multi-flow integration tests; idempotency; cross-account scenarios. |
| Data dictionary / runbook update | Docs | S | One-pager for Provider Directory consumers. |

**Total Estimated Effort:** ~6–8 dev days (1 sprint week + buffer) — **XL overall** — *AI-estimated, validate with team*

---

# Cross-Story Dependency Graph

```
US1 (Address Screen — capture intent)
   │  produces: PRM_StagedAsNewPrimary__c=TRUE on new HCPF
   │            PRM_PendingPrimaryDemotion__c=TRUE on prior HCPF
   ▼
US2 (PDA Activation — atomic flip)
   │  consumes the staging flags
   │  produces: exactly one Active Primary HCPF per Practitioner
   ▼
Downstream consumers (CAQH Roster, Provider Directory, SendGrid)
   │  see atomic transition; no temporal anomaly
```

**Sequencing:** US1 must merge **before** US2 because US2's service depends on the two new fields and the staging contract. Both must ship in the same release to avoid intermediate states. Field History Tracking config can ship independently, ahead of either.

---

# Open Items / Pre-Implementation Questions Roll-Up

(De-duplicated across both stories for the BA review meeting.)

| # | Question | Story | Owner |
|---|----------|-------|-------|
| 1 | Two booleans vs. self-referential lookup for staging? | US1 Q1 | Technical / BA |
| 2 | Behavior on PAR denial mid-flow? | US1 Q2 | BA / Ops |
| 3 | Cross-vendor primary change in scope? | US1 Q3 | Product |
| 4 | Anomaly remediation script needed? | US1 Q4 | Ops / Technical |
| 5 | Alert UI styling? | US1 Q5 | Product / Design |
| 6 | HCFN effective-date adjustments at demotion? | US1 Q6 | Network Ops |
| 7 | Off Cycle flow alignment? | US1 Q7 | Technical |
| 8 | Canonical PAR PDA Update IP name? | US2 Q1 | Technical |
| 9 | Behavior if prior primary already inactive at activation? | US2 Q2 | BA / Technical |
| 10 | Notification to Network Ops on demotion? | US2 Q3 | Ops |
| 11 | Validation rule SOQL strategy? | US2 Q4 | Technical |
| 12 | EffectiveFrom/To date update on demotion? | US2 Q5 | Product / BA |

---

## QTA Test Bridge — Optional Next Step

The two stories above contain **6 + 5 = 11 acceptance criteria**. If desired, the QTA Quality Test Agent can convert them into browser-automation test prompts (one prompt per AC, navigation + interaction + assertion mapped from Given/When/Then). Reply *"generate QTA prompts"* to produce `qta_test_prompts.md` alongside this document.
