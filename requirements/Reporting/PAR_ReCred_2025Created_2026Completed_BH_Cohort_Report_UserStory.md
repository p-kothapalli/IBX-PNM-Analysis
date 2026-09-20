# USER STORY: PAR & Re-Cred Cohort Report — "Created in Year N, Completed in Year N+1" — Behavioral Health vs Non-BH Split

**Persona:** Senior Data and Reporting Specialist (primary) / Credentialing Specialist / Business Admin
**Priority:** P1
**OmniScripts (highest version in repo, taxonomy-capture steps confirmed):**
- **PAR** — `PRM_PractitionerParticipationForm_English_117` (`TaxonomySection`, `TaxonomyCode`, `IPFetchCareTaxonomyProviderTypes`)
- **Off Cycle** — `PRM_OffCycleCredentialing_English_63` (`AddAddressTaxonomy`, `AddPrimaryAddressTaxonomy`, `PRTaxonomy`, `NewStateRegionTaxonomy`, `IsPrimaryTaxonomy`)
- **Re-Cred** — `PRM_ReCredUpdate_English_7` and `PRM_ReCredQCUpdate_English_3` (`TaxonomyNew`, `RemovePPLTaxonomy`); `PRM_RecredQC_English_13` (`PSVPractitonerTaxonomy`, `HFNCareTaxonomy`, `HFNPracticeLocationTaxonomy`, `IPToCountPrimaryTaxonomy`, `SetErrorsMultiplePrimaryTaxonomy`, `VerifyCareTaxonomyRD`)

**Apex (primary change surface):** `PRM_HCProviderTaxonomyTriggerHandler` (existing), `PRM_HealthcareProviderTaxonomyTrigger` (existing)
**DataRaptors:** `PRMDRCreateTaxonomy_1` (PAR/PSV/App-Review), `PRMLoadOffCycleTaxonomy_1` (Off Cycle), `PRMDRPPersonAccHCProviderNPITaxonomy_1` (Account-type/Non-PAR), `PRMUpdateTaxonomyPDAReview_1` (PDA-Review **activation** path — does *not* stamp Case Manager), `PRMDRLoadRCATHCPTax_1` (RCAT termination), `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1` (existing BH-flag precedent — unchanged)
**Relevant Requirements:**
- `requirements/PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md` — **HARD DEPENDENCY** (exposes `PRM_BehavioralHealth__c` as a selectable column on `PRM_CaseManagerReportType`)
- `requirements/SOQL/2026-08-13_CreatedIn2025_CompletedIn2026_ParRecred.md` — source SOQL for all outcome buckets and BH/Non-BH split
- `.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md` — cross-check of business's BH practitioner list against `CareTaxonomy` groupings (business elected to filter by grouping)
- `requirements/PRM_CaseManagerReportType_AddMedicalDirectorReview_UserStory.md` — precedent for the report-type expansion pattern
**Vertical:** Provider Network Management (PNM)

---

## Story

**As a** Senior Data and Reporting Specialist,
**I want** a repeatable Salesforce report that shows how many **PAR (Practitioner Participation Request)** and **Re-Credentialing** Case Managers were **created in a chosen calendar year** and **completed in the following calendar year**, broken down by outcome (**Approved / Denied / Withdrew / In-Flight**) and split into two cohorts — practitioners with an active **Behavioral Health** taxonomy grouping vs everyone else (**Non-BH**),
**So that** Cred leadership, Network Management QC, and Compliance can measure year-over-year cred throughput, identify BH-network-specific bottlenecks, and answer regulatory / accreditation questions without a developer running ad-hoc SOQL each time.

**Why it matters:** The business currently asks a developer to run SOQL against `IndividualApplication` and `HealthcareProviderTaxonomy` every time this question comes up (last run: 6 queries × BH/Non-BH × 4 buckets = 8 SOQL statements per refresh — see `requirements/SOQL/2026-08-13_CreatedIn2025_CompletedIn2026_ParRecred.md`). The BH cohort split is a recurring reporting ask driven by BH network parity commitments; a self-service Salesforce report on the existing **Case Manager Report Type** eliminates the developer round-trip, works for any pair of years (2025→2026, 2026→2027, …), and lets Reporting build downstream dashboards on top of it.

The critical design pivot: instead of building a cross-object custom report type that joins `IndividualApplication → Account → HealthcareProviderTaxonomy → CareTaxonomy` (which returns one row per taxonomy and requires row-collapsing group-bys), we **push the BH determination down onto the Case Manager as taxonomies are written** by populating the existing `IndividualApplication.PRM_BehavioralHealth__c` checkbox. The report then filters/groups on a single flat boolean on the Case Manager, which the standard `PRM_CaseManagerReportType` already targets.

---

## Scope

| Area | Component | Change |
|---|---|---|
| **BH flag write (primary)** | `PRM_HCProviderTaxonomyTriggerHandler` (existing Apex) | **New method** `syncBehavioralHealthFlagToCaseManager()` on `afterInsert` + `afterUpdate`. Covers **every** practitioner-taxonomy write path in one place — including Re-Cred's `TaxonomyNew` add and the Re-Cred/Off-Cycle PDA-Review activation. |
| BH flag write (reconciliation **and Re-Cred carry-forward**) | New Apex batch `PRM_SyncBehavioralHealthFlagBatch` | Covers the trigger's bypass gaps (bulk context, `PRM_TriggerBypassPermission`, future-dated activations), the **new-Re-Cred-cycle carry-forward case** where an already-BH practitioner gets a fresh Re-Cred CM with no taxonomy DML (AC-4), **and** serves as the one-time 2025-cohort backfill. Schedulable nightly. |
| Field write — Ancillary flow | `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1`, `PRM_CheckDueOnAncillaryReAssessmentBatch` | **No change** — already set `PRM_BehavioralHealth__c` from Ancillary Provider Type & Service. |
| Rule union | All write paths | If **either** the Ancillary Provider-Type-&-Service rule **or** the taxonomy-grouping rule is TRUE, the flag is TRUE. Both writers target the same field; the new logic **only ever sets TRUE** (never clears), so it cannot regress the Ancillary value. Clearing is a separate business decision (Clarification Q5). |
| Report Type | `PRM_CaseManagerReportType` | Add `Behavioral Health` as a selectable column — **already covered by** `requirements/PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md` (hard dependency, must ship first) |
| Report 1 | New saved report | **"PAR & Re-Cred — Created in <YearN>, Completed in <YearN+1> — BH vs Non-BH"** — on `PRM_CaseManagerReportType`, grouped RecordType → BH flag → outcome bucket |
| Report 2 | New saved report | **"PAR & Re-Cred — In-Flight (Created in <YearN>, not yet Complete) — BH vs Non-BH"** — on `PRM_CaseManagerReportType`, grouped RecordType → BH flag → PRM_Stage__c |
| Dashboard (optional) | New Lightning dashboard | Side-by-side visualization of Report 1 + Report 2 with a Year filter |

**In scope:** PAR (`PRM_PractitionerParticipationRequest`) and Re-Cred (`PRM_ReCredentialing`) record types on `IndividualApplication` for the *report*. The *BH-flag write* is deliberately **flow-agnostic** — because it hangs off the taxonomy trigger, PAR, Off Cycle, Re-Cred, PSV, App Review, PDM, and Provider Change all get correct flags with zero per-flow work.

**Re-Cred is covered by three distinct mechanisms**, because Re-Cred can become Behavioral Health in three different ways:

| Re-Cred scenario | Mechanism | AC |
|---|---|---|
| Specialist **adds** a BH taxonomy during the cycle (`TaxonomyNew` in `PRM_ReCredUpdate` / `PRM_ReCredQCUpdate`) | Trigger `afterInsert` (D3) | AC-3 |
| A pending BH taxonomy is **activated at PDA Review** (`PRMUpdateTaxonomyPDAReview_1`, which does not stamp the Case Manager) | Trigger `afterUpdate` (D4) + `AccountId` fallback | AC-8 |
| Practitioner is **already BH from a prior cycle** and a new Re-Cred CM is opened — **no taxonomy DML occurs, so no trigger fires** | Nightly batch (D5) | AC-4 |

The third row is the one that is easy to miss and covers the largest population: most Re-Cred Case Managers inherit an existing BH taxonomy rather than adding a new one, so **without the batch, most Re-Cred CMs would never be flagged.**

**Out of scope:**
- **Clearing** the flag back to FALSE when the last BH taxonomy is deactivated (Clarification Q5) — v1 is set-only. Note Re-Cred's `RemovePPLTaxonomy` element and the RCAT full-termination path make this a live question.
- **Practice-location-level BH taxonomy** on `HealthcareFacilityNetwork` (Re-Cred's `HFNCareTaxonomy` / `HFNPracticeLocationTaxonomy` elements) — different object, trigger does not fire. Documented boundary; see AC-7 and Clarification Q14.
- BH-cohort dashboards for Off-Cycle, PSV, PNC, or Provider Change flows (the flag will be correct; the *reports* aren't built for them).
- CRMA / Data Cloud syndication of the BH flag.

---

## Current State — how `PRM_BehavioralHealth__c` gets written today (graph + metadata verified)

### The gap

`PRM_BehavioralHealth__c` on `IndividualApplication` is populated by **exactly two writers today, both Ancillary-only**:

| Writer | Trigger point | Rule |
|---|---|---|
| `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1` (line 345) | Ancillary CM creation | mapped from IP input `IsBehaviourTypeAndService` |
| `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` (line ~139) | Ancillary re-assessment | `PRM_ProviderTypeService__c` ∈ `PRM_AncillaryFormType__mdt` rows where `PRM_APIName__c LIKE 'BTS%'` |

**Neither considers practitioner taxonomies.** So a PAR, Off Cycle, or **Re-Cred** practitioner with a Behavioral Health taxonomy gets `PRM_BehavioralHealth__c = FALSE` — which is precisely the reporting gap this story closes. Re-Cred is the worst-affected of the three: since Re-Cred Case Managers are opened for *existing* practitioners who typically already carry their BH taxonomy from a prior cycle, **effectively the entire Re-Cred BH population is currently unflagged**, and no taxonomy-write event ever occurs to correct it.

### The enabling discovery — `HealthcareProviderTaxonomy` already knows its Case Manager

`HealthcareProviderTaxonomy` carries a direct lookup to the Case Manager:

```7:9:force-app/main/default/objects/HealthcareProviderTaxonomy/fields/PRM_CaseManager__c.field-meta.xml
    <referenceTo>IndividualApplication</referenceTo>
    <relationshipLabel>Healthcare Provider Taxonomies</relationshipLabel>
    <relationshipName>HealthcareProviderTaxonomies</relationshipName>
```

Field description: *"This field will be used to identify which records need to picked when working on flows like application Review, OIG, etc."*

This means **no Account round-trip is needed** — a taxonomy row knows which Case Manager it was created under. That is what makes a trigger-based write viable.

### Verified taxonomy write paths for the three flows in scope

| Flow | OmniScript | Taxonomy capture elements | Integration Procedure | DataRaptor Load | Stamps `PRM_CaseManager__c`? |
|---|---|---|---|---|---|
| **PAR** | `PRM_PractitionerParticipationForm_English_117` | `TaxonomySection`, `TaxonomyCode`, `IPFetchCareTaxonomyProviderTypes` | `PRM_ReviewParCaseRecordsUpdate_Procedure`, `PRM_ReviewPSVCaseRecordsUpdate_Procedure`, `PRM_PractitionerScreenExistingNPIRecordUpdation_Procedure` | `PRMDRCreateTaxonomy_1` | ✅ **YES** |
| **Off Cycle** | `PRM_OffCycleCredentialing_English_63` | `AddAddressTaxonomy`, `AddPrimaryAddressTaxonomy`, `PRTaxonomy`, `NewStateRegionTaxonomy`, `IsPrimaryTaxonomy` | `PRM_OffCycleRecordCreation_Procedure` | `PRMLoadOffCycleTaxonomy_1` | ✅ **YES** |
| **Re-Cred — add** | `PRM_ReCredUpdate_English_7`, `PRM_ReCredQCUpdate_English_3` | **`TaxonomyNew`** (the add case), `RemovePPLTaxonomy` (remove case) | `PRM_RecredPDAHelper_Procedure`, `PRM_ReCredHelper_Procedure` | **To confirm at build time — Clarification Q13** | ⚠️ unconfirmed |
| **Re-Cred — PSV verify** | `PRM_RecredQC_English_13` | `PSVPractitonerTaxonomy`, `VerifyCareTaxonomyRD`, `IPToCountPrimaryTaxonomy`, `SetErrorsMultiplePrimaryTaxonomy` | `PRM_ReCredHelper_Procedure` (carries `VerifyCareTaxonomy`, `VerifyIsPrimaryTaxonomy`, `TaxonomyTypeAhead` blocks) | read/verify — may activate existing rows | n/a (read) |
| **Re-Cred / Off Cycle — PDA activation** | `PRM_ReCredUpdate_English_7`, Off Cycle PDA Review | — | `PRM_OffCycleRecordUpdatesPDAReview_Procedure` | `PRMUpdateTaxonomyPDAReview_1` — writes `IsActive`, `PRM_Pending__c`, `EffectiveFrom`, `EffectiveTo` | ❌ **NO** → needs `AccountId` fallback |
| **RCAT termination** | `PRM_ReviewRCAT_English_10` | (none — no taxonomy elements) | `PRM_RCATFullTermination_Procedure_1` | `PRMDRLoadRCATHCPTax_1` | ✅ **YES** |
| Account-type / Non-PAR | — | — | `PRM_AccountTypeRecordCreations`, `PRM_NonParRecordCreations` | `PRMDRPPersonAccHCProviderNPITaxonomy_1` | ✅ **YES** |

Off Cycle has the richest **add** surface; Re-Cred's add case is the single **`TaxonomyNew`** element (present in both `PRM_ReCredUpdate` and `PRM_ReCredQCUpdate`). Together these three cover the business's description of a practitioner "joining / adding a taxonomy".

> **Why the unconfirmed Re-Cred DataRaptor doesn't block the build:** because the flag write hangs off the `HealthcareProviderTaxonomy` trigger, it fires for **any** insert or activation of a practitioner taxonomy regardless of which IP or DataRaptor performed it. The Re-Cred DR name is needed for *test-data setup and QA scripting*, not for the implementation. This is the core resilience argument for the trigger-based design.

### ⚠️ Scope boundary — practice-location taxonomy is a *different object*

Re-Cred's taxonomy surface is **split across two objects**, and only one of them fires the trigger:

| Element(s) | Target object | Trigger fires? | In scope for the BH flag? |
|---|---|---|---|
| `PSVPractitonerTaxonomy`, `TaxonomyNew` | `HealthcareProviderTaxonomy` (practitioner-level) | ✅ Yes | ✅ **Yes** |
| `HFNCareTaxonomy`, `HFNPracticeLocationTaxonomy`, `RemovePPLTaxonomy` | **`HealthcareFacilityNetwork`** (practice-location-level) | ❌ **No** | ❌ **No** — see Clarification Q14 |

Verified: `PRMDRCreatePracticeLocationTaxonomy_1`, `PRMDRPracticeLocationTaxonomyNetworkUpdate_1`, and `PRMDRCreateHFNTaxonomyRecords_1` all write `HealthcareFacilityNetwork`, **not** `HealthcareProviderTaxonomy`.

The BH cohort definition agreed with the business (and every query in the SOQL reference) is based on **practitioner-level** `HealthcareProviderTaxonomy`, so this boundary matches the intended definition. But it must be stated explicitly: **a practitioner whose only Behavioral Health taxonomy exists at the practice-location level will not be flagged.** Clarification Q14 asks the business to confirm that is acceptable.

The existence of `RemovePPLTaxonomy` is also further evidence that taxonomy **removal** is a real business action in Re-Cred, which sharpens Clarification Q3 (set-only vs clear-on-deactivate).

### Why per-IP DataRaptor steps were rejected

A full inventory of every DataRaptor that writes `HealthcareProviderTaxonomy` found **31 DataRaptors**, of which **22 stamp `PRM_CaseManager__c` and 9 do not**:

| Stamps `PRM_CaseManager__c` (22 — trigger resolves CM directly) | Does NOT stamp (9 — trigger must fall back to `AccountId`) |
|---|---|
| `PRMDRCreateTaxonomy_1`, `PRMLoadOffCycleTaxonomy_1`, `PRMDRPPersonAccHCProviderNPITaxonomy_1`, `PRMDRPPersonAccHCProviderNPITaxonomyExAcc_1`, `PRMDRCreateAncillaryProviderNPIIdentifier_1`, `PRMDRCreateEducationTaxanomyAndLicense_1`, `PRMDRLoadNPITaxHCFNPNC_1`, `PRMDRLoadPractitionerHealthcareProviderHPTaxonomy_1`, `PRMDRLoadRCATHCPTax_1`, `PRMDRPBoardCertHCProvTaxonomy_1`, `PRMDRPHCPHCPTaxonomyAndBusineessLicense_1`, `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense_1`, `PRMDRPHCProviderHCTxnHCNPI_1`, `PRMDRUpdateHCPTaxonomyPDM_1`, `PRMDRUpdateRelateddataForNonRoutineTable1_1`, `PRMDRUpdateTaxonomy_1`, `PRMLoadOffCycleCaseCaseMgr_1`, `PRMLoadPracProviderTxnyPDM_1`, `PRMLoadTaxonomyPDM_1`, `PRMReinstateHealthcareProviderTaxonomyRecordUpdate_1`, `PRMUpdateHPTxnmFcltyPracFclty_1` | `PRMDRLoadSaveInactiveHCPTaxonomy_1`, `PRMDRPHealthCareNPIHealthCareTaxonomyUpdate_1`, `PRMDRPIdentifierAccountTaxonomy_1`, `PRMDRToUpdateTaxonomiesReInstate_1`, `PRMDRUpdateBusLicIdentifierInfoCode_1`, `PRMDRUpdatePrimaryTaxonomy_1`, `PRMLoadAccTaxIdBasedOnId_1`, `PRMLoadIDTaxnmyCertUpdate_1`, `PRMUpdateTaxonomyPDAReview_1` |

Adding a BH-flag step to 31 DataRaptors across dozens of IP versions is unmaintainable and guarantees drift. **One trigger method covers all 31.**

### The existing trigger — and its two bypasses (why a batch is mandatory, not optional)

```10:14:force-app/main/default/triggers/PRM_HealthcareProviderTaxonomyTrigger.trigger
trigger PRM_HealthcareProviderTaxonomyTrigger on HealthcareProviderTaxonomy(before insert, after insert, before update, after update) {
    
    if (PRM_TriggerContextControl.inBulkContext()) return;
    
    if (FeatureManagement.checkPermission('PRM_TriggerBypassPermission') == false) {
```

`PRM_HCProviderTaxonomyTriggerHandler` already overrides `beforeInsert`, `beforeUpdate`, `afterInsert`, `afterUpdate` (currently doing primary-taxonomy demotion + future-dated processing). Adding one method is low-risk.

**But the trigger is skipped in two situations**, so it cannot be the only writer:

1. **`PRM_TriggerContextControl.inBulkContext()`** — batch and bulk-load contexts return early. The ReCred→PAR conversion batch, data migrations, and Data Loader runs all bypass it.
2. **`PRM_TriggerBypassPermission`** — users/integrations holding this custom permission bypass it.

**Plus a lifecycle gap:** `PRMDRCreateTaxonomy_1` and `PRMLoadOffCycleTaxonomy_1` set `PRM_Pending__c` but **do not set `IsActive`**. Taxonomies can be created **future-dated / pending** and activated later by `PRM_FutureDatedProcessingUtil` / `DFX_PractitionerActivationExecutor`. A taxonomy inserted today as pending will not satisfy the `IsActive = TRUE` rule at insert time — it only qualifies when it is later activated.

The `afterUpdate` hook catches the in-session `IsActive` false→true flip, but **future-dated activation happens in batch context** (bypassed). Hence `PRM_SyncBehavioralHealthFlagBatch` runs nightly as the safety net, and doubles as the one-time 2025 backfill.

---

## Current State (from codebase — graph-verified)

### Field — already exists

- **`IndividualApplication.PRM_BehavioralHealth__c`** — custom checkbox, label "Behavioral Health".
- Currently populated **only** on Ancillary CMs by two writers:
  1. `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1.rpt-meta.xml` line 345 — mapped from IP input `IsBehaviourTypeAndService` at CM creation.
  2. `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` line ~139 — `String.isNotBlank(ancillaryRecord.PRM_ProviderTypeService__c) && ancillaryMDTRecords.contains(ancillaryRecord.PRM_ProviderTypeService__c)` at re-assessment.
- **NOT currently populated on PAR, Off Cycle, or Re-Cred CMs** — those records have `PRM_BehavioralHealth__c = FALSE` today regardless of practitioner taxonomies.
- FLS already granted on `PRM_CredentialingUser`, `PRM_AncillaryCredSpecialist`, `PRM_DataModifyAll`, `PRM_DataViewAll`, `PRM_NetworkManagementQC`, `PRM_ProviderDataAdmin`. **`PRM_SeniorDataReportingSpecialist` FLS needs verification (see Clarification Q6).**

### Existing SOQL — the shape the report must reproduce

From `requirements/SOQL/2026-08-13_CreatedIn2025_CompletedIn2026_ParRecred.md`, the target row structure per cohort is:

| RecordType | Outcome | BH cohort | Non-BH cohort |
|---|---|---|---|
| PractitionerParticipationRequest | Approved | count | count |
| PractitionerParticipationRequest | Denied | count | count |
| PractitionerParticipationRequest | Withdrew | count | count |
| PractitionerParticipationRequest | In-Flight (not yet Complete) | count | count |
| Recredentialing | Approved | count | count |
| Recredentialing | Denied | count | count |
| Recredentialing | Withdrew | count | count |
| Recredentialing | In-Flight (not yet Complete) | count | count |

Today: 8 separate SOQL queries, run by a developer, spreadsheet-assembled. Target: 2 saved Salesforce reports, filterable by year, runnable by the persona.

### BH-cohort definition (business-signed-off)

A Case Manager is BH iff the linked `Account` (practitioner) has **at least one** `HealthcareProviderTaxonomy` where:
- `HealthcareProviderTaxonomy.IsActive = TRUE`, **AND**
- `HealthcareProviderTaxonomy.Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'`

Non-BH = the anti-set (no active BH taxonomy). Business acknowledged this grouping-only filter excludes some BH-adjacent physicians / APPs whose taxonomies fall in `Allopathic & Osteopathic Physicians` or `Physician Assistants & Advanced Practice Nursing Providers` groupings (see `.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md`); this is the intended definition.

---

## Acceptance Criteria

### Behavioural ACs (Pattern A)

**AC-1 — Adding a Behavioral Health taxonomy on the PAR form flags the Case Manager**

**Given** a Credentialing Specialist is working a Practitioner Participation Request (PAR) for a practitioner,
**When** they add a taxonomy that belongs to the **"Behavioral Health & Social Service Providers"** grouping and save the form,
**Then** the **"Behavioral Health"** flag on that practitioner's Case Manager SHALL be set to **Yes**,
**And** the flag SHALL be visible on the Case Manager record page and available as a report column.

---

**AC-2 — Adding a Behavioral Health taxonomy on the Off Cycle form flags the Case Manager**

**Given** a Credentialing Specialist is working an Off Cycle Credentialing request for an already-credentialed practitioner,
**When** they add a taxonomy that belongs to the **"Behavioral Health & Social Service Providers"** grouping and save the form,
**Then** the **"Behavioral Health"** flag on that practitioner's Case Manager SHALL be set to **Yes**.

---

**AC-3 — Adding a Behavioral Health taxonomy during Re-Credentialing flags the Case Manager**

**Given** a Credentialing Specialist is working a Re-Credentialing cycle for an existing practitioner,
**When** they add a taxonomy that belongs to the **"Behavioral Health & Social Service Providers"** grouping and save,
**Then** the **"Behavioral Health"** flag on that practitioner's Re-Credentialing Case Manager SHALL be set to **Yes**,
**And** the flag SHALL be set on the **Re-Credentialing** Case Manager for the current cycle, not on a prior closed cycle's Case Manager.

---

**AC-4 — A practitioner already flagged Behavioral Health stays flagged through a new Re-Cred cycle**

**Given** a practitioner who has an active Behavioral Health taxonomy carried forward from a prior credentialing cycle,
**When** a new Re-Credentialing Case Manager is opened for that practitioner and the Behavioral Health sync runs,
**Then** the new Re-Credentialing Case Manager SHALL have its **"Behavioral Health"** flag set to **Yes**,
**And** the Credentialing Specialist SHALL NOT have to re-enter the taxonomy for the flag to be correct.

---

**AC-5 — A non-Behavioral-Health taxonomy does not flag the Case Manager**

**Given** a Credentialing Specialist is working a PAR, Off Cycle, or Re-Credentialing request for a practitioner,
**When** the only taxonomies they add belong to a grouping **other than** "Behavioral Health & Social Service Providers" (for example a family-medicine physician taxonomy),
**Then** the **"Behavioral Health"** flag on the Case Manager SHALL remain **No**.

---

**AC-6 — A practitioner with a mix of taxonomies is flagged if any one is Behavioral Health**

**Given** a practitioner whose Case Manager already has taxonomies from a non-Behavioral-Health grouping,
**When** a Credentialing Specialist adds one additional taxonomy from the **"Behavioral Health & Social Service Providers"** grouping,
**Then** the **"Behavioral Health"** flag on the Case Manager SHALL be set to **Yes**,
**And** the previously added non-Behavioral-Health taxonomies SHALL remain unchanged.

---

**AC-7 — A practice-location-only Behavioral Health taxonomy does not flag the Case Manager (documented boundary)**

**Given** a practitioner whose **only** Behavioral Health taxonomy is recorded at the **practice-location** level rather than against the practitioner,
**When** the Behavioral Health sync runs,
**Then** the **"Behavioral Health"** flag on the Case Manager SHALL remain **No**,
**And** this SHALL be treated as expected behaviour consistent with the agreed Behavioral Health cohort definition (pending business confirmation — Clarification Q14).

---

**AC-8 — A Behavioral Health taxonomy activated at PDA Review flags the Case Manager**

**Given** a Behavioral Health taxonomy was captured earlier in a Re-Credentialing or Off Cycle case and is still pending activation,
**When** the Provider Data Admin (PDA) Specialist completes PDA Review and the taxonomy becomes active,
**Then** the **"Behavioral Health"** flag on that Case Manager SHALL be set to **Yes**,
**And** this SHALL hold even though the activation step does not itself record which Case Manager the taxonomy belongs to.

---

**AC-9 — A future-dated Behavioral Health taxonomy flags the Case Manager only once it becomes effective**

**Given** a Credentialing Specialist adds a **Behavioral Health** taxonomy with an effective date in the future, so it is saved as pending rather than active,
**When** the taxonomy's effective date arrives and it becomes active,
**Then** the **"Behavioral Health"** flag on the Case Manager SHALL be set to **Yes** no later than the next overnight sync,
**And** the flag SHALL remain **No** for as long as the taxonomy is still pending.

---

**AC-10 — Bulk and back-office taxonomy loads still reach the Case Manager**

**Given** Behavioral Health taxonomies are added to practitioners through a bulk load, a batch conversion, or by an integration user that bypasses interactive record automation,
**When** the overnight Behavioral Health sync runs,
**Then** every affected Case Manager SHALL have its **"Behavioral Health"** flag set to **Yes**,
**And** Case Managers with no Behavioral Health taxonomy SHALL be left unchanged.

---

**AC-11 — Ancillary Behavioral Health determination is not regressed**

**Given** an Ancillary Cred Specialist creates an Ancillary Case Manager for a Provider Type & Service that already qualifies as Behavioral Health,
**When** the Ancillary Case Manager is created,
**Then** the **"Behavioral Health"** flag SHALL continue to be **Yes** exactly as it is today,
**And** the new taxonomy-driven logic SHALL never change an existing **Yes** to **No**.

---

**AC-12 — One-time backfill flags the historical cohort**

**Given** Case Managers created in 2025 and earlier whose practitioners have a Behavioral Health taxonomy but whose **"Behavioral Health"** flag is currently **No**,
**When** the Senior Data and Reporting Specialist runs the one-time Behavioral Health sync in the target org,
**Then** every such Case Manager SHALL be updated to **"Behavioral Health" = Yes**,
**And** Case Managers without a Behavioral Health taxonomy SHALL remain **No**,
**And** a summary of records scanned, updated, and unchanged SHALL be recorded for audit.

---

**AC-13 — Re-running the sync produces no further changes (idempotency)**

**Given** the Behavioral Health sync has already completed successfully,
**When** it is run a second time with no taxonomy data having changed in between,
**Then** zero Case Manager records SHALL be updated,
**And** the audit summary SHALL report zero updates.

---

**AC-14 — Cohort report runs natively on the Case Manager Report Type**

**Given** the Senior Data and Reporting Specialist opens the saved report **"PAR & Re-Cred — Created in <YearN>, Completed in <YearN+1> — BH vs Non-BH"**,
**When** they set the year filters to (Year Created = 2025, Year Completed = 2026) at report-run time,
**Then** the report SHALL render 8 rows (2 record types × 4 outcome buckets), each showing a Behavioral Health count and a Non-Behavioral-Health count,
**And** the totals per bucket SHALL reconcile to the reference query set within ±0 records.

---

**AC-15 — In-Flight report shows what's still open from the prior year**

**Given** the Senior Data and Reporting Specialist opens the saved report **"PAR & Re-Cred — In-Flight (Created in <YearN>, not yet Complete) — BH vs Non-BH"**,
**When** they set the "Year Created" filter to 2025,
**Then** the report SHALL show only Case Managers created in calendar 2025 whose Stage is not "Complete",
**And** the rows SHALL be grouped by record type and by the Behavioral Health flag,
**And** the count SHALL reconcile to the In-Flight bucket in the reference query set within ±0 records.

---

**AC-16 — Year filters are parameterized (works for future years)**

**Given** the report is deployed,
**When** the Senior Data and Reporting Specialist changes the created-date and decision-date range filters on the saved report to any pair of consecutive years,
**Then** the report SHALL execute successfully and return the corresponding cohort counts without any developer intervention.

---

**AC-17 — Withdrew bucket is counted separately from Denied (edge case)**

**Given** the cohort contains Case Managers that were withdrawn by the applicant rather than denied by IBX,
**When** the report is run,
**Then** the **Withdrew** column SHALL be populated distinctly from **Denied**,
**And** the sum of Approved + Denied + Withdrew + In-Flight SHALL equal the total cohort count for that record type (no double-count, no drop-through).

---

**AC-18 — Only permitted roles see the flag and the reports**

**Given** a user whose role does not grant access to the Behavioral Health flag,
**When** they open the Case Manager report type or one of the saved reports from this story,
**Then** the Behavioral Health column SHALL NOT appear in the field picker,
**And** the saved report SHALL render that column as blank for that user.

---

### Field / metadata AC (Pattern B)

**AC-19 — No new fields on IndividualApplication**

The story reuses `IndividualApplication.PRM_BehavioralHealth__c`. No new custom field is created. Metadata scope:

| Object | Field | Change |
|---|---|---|
| `IndividualApplication` | `PRM_BehavioralHealth__c` | **No change** — reused as-is; write-sources expanded |
| `HealthcareProviderTaxonomy` | `PRM_CaseManager__c`, `TaxonomyId`, `AccountId`, `IsActive`, `PRM_Pending__c`, `EffectiveFrom`, `EffectiveTo` | **No change** — all read-only inputs to the rule; already populated by the 22 CM-stamping DataRaptors |
| `CareTaxonomy` | `PRM_TaxonomyGrouping__c` | **No change** — read-only reference for the rule |

---

### Permission set AC (Pattern C)

**AC-20 — Permission grants**

| Permission Set | Access needed | Current state | Action |
|---|---|---|---|
| `PRM_SeniorDataReportingSpecialist` | Read on `IndividualApplication.PRM_BehavioralHealth__c` | **Verify — likely missing** (see Clarification Q6) | Add if missing |
| `PRM_SeniorDataReportingSpecialist` | Read on the two new saved reports (folder-level share) | New folder needs sharing | Grant folder read |
| `PRM_CredentialingUser` | Read on the two new saved reports | Existing FLS OK | Grant folder read |
| `PRM_ProviderDataAdmin` | Read on the two new saved reports | Existing FLS OK | Grant folder read |
| `PRM_DataModifyAll` | Execute rights on `PRM_SyncBehavioralHealthFlagBatch` | Standard admin | Confirm |
| `PRM_TriggerBypassPermission` holders | Awareness only — their taxonomy writes skip the trigger and rely on the nightly batch | Existing custom permission | Document; no change |

---

### Field-update-rules AC (Pattern D)

**AC-21 — `PRM_BehavioralHealth__c` write rules, by source**

Let **`BH_RULE`** = `IsActive = TRUE` **AND** `PRM_Pending__c = FALSE` **AND** the row's `TaxonomyId` resolves to a `CareTaxonomy` with `PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'`.

| # | Source | Trigger point | Rule | Existing / new |
|---|---|---|---|---|
| D1 | Ancillary CM creation | `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1` load step (line 345) | `IsBehaviourTypeAndService = TRUE` (computed upstream from `PRM_AncillaryFormType__mdt` rows where `PRM_APIName__c LIKE 'BTS%'`) | **Existing — no change** |
| D2 | Ancillary re-assessment | `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` line ~139 | `String.isNotBlank(ancillaryRecord.PRM_ProviderTypeService__c) && ancillaryMDTRecords.contains(ancillaryRecord.PRM_ProviderTypeService__c)` | **Existing — no change** |
| D3 | **Any practitioner-taxonomy insert** — PAR (`TaxonomySection`), Off Cycle (`AddAddressTaxonomy`/`PRTaxonomy`), **Re-Cred (`TaxonomyNew`)**, PSV, App Review, PDM, Provider Change | `PRM_HCProviderTaxonomyTriggerHandler.afterInsert` | For each inserted `HealthcareProviderTaxonomy` satisfying **`BH_RULE`** → set `PRM_BehavioralHealth__c = TRUE` on the resolved Case Manager | **New** |
| D4 | **Taxonomy activation** (pending → active) — incl. **Re-Cred / Off Cycle PDA Review** via `PRMUpdateTaxonomyPDAReview_1`, and future-dated activation | `PRM_HCProviderTaxonomyTriggerHandler.afterUpdate` | **`BH_RULE`**, fired when `IsActive` changes `FALSE → TRUE` **or** `PRM_Pending__c` changes `TRUE → FALSE` **or** `TaxonomyId` changes | **New** |
| D5 | **New Re-Cred cycle opened for an already-BH practitioner** (carry-forward — AC-4) | `PRM_SyncBehavioralHealthFlagBatch` | For each open Case Manager with `PRM_BehavioralHealth__c = FALSE` whose `AccountId` has **any** `HealthcareProviderTaxonomy` satisfying **`BH_RULE`** → set `TRUE`. No taxonomy DML occurs when a Re-Cred CM is opened, so the trigger cannot fire — **the batch is the only mechanism that covers this case** | **New** |
| D6 | **Reconciliation / bypass coverage / backfill** | `PRM_SyncBehavioralHealthFlagBatch` (schedulable nightly + on-demand) | **`BH_RULE`**, evaluated set-wise across all in-scope Case Managers where the flag is currently `FALSE` | **New** |

**Explicitly NOT a write source (AC-7 boundary):** taxonomy recorded on **`HealthcareFacilityNetwork`** (practice-location level) via `PRMDRCreatePracticeLocationTaxonomy_1`, `PRMDRPracticeLocationTaxonomyNetworkUpdate_1`, `PRMDRCreateHFNTaxonomyRecords_1`, or the Re-Cred QC elements `HFNCareTaxonomy` / `HFNPracticeLocationTaxonomy` / `RemovePPLTaxonomy`. These write a **different object**, so neither the trigger nor the batch evaluates them. See Clarification Q14.

> **D5 is the row that makes Re-Cred work end-to-end.** Re-Cred has two distinct BH paths: (a) the specialist *adds* a new BH taxonomy during the cycle → D3/D4 handle it; (b) the practitioner was *already* BH from a prior cycle and the new Re-Cred CM must inherit the flag → only D5 handles it, because opening a Re-Cred CM performs no taxonomy DML. Omitting D5 would leave the majority of Re-Cred Case Managers unflagged.

**Case Manager resolution order** (used by D3–D6):

1. **Primary:** `HealthcareProviderTaxonomy.PRM_CaseManager__c` — populated by 22 of the 31 taxonomy-writing DataRaptors (including `PRMDRCreateTaxonomy_1` for PAR, `PRMLoadOffCycleTaxonomy_1` for Off Cycle, and `PRMDRLoadRCATHCPTax_1` for RCAT).
2. **Fallback:** if `PRM_CaseManager__c` is null, resolve via `AccountId` → the practitioner's open PAR/Re-Cred Case Managers (`PRM_Stage__c != 'Complete'`). If more than one is open, flag **all** of them. **This fallback is load-bearing for Re-Cred**, because `PRMUpdateTaxonomyPDAReview_1` — the PDA-Review activation path used by Re-Cred and Off Cycle — writes `IsActive` / `PRM_Pending__c` **without** stamping `PRM_CaseManager__c` (verified). Without the fallback, AC-8 fails.
3. If neither resolves, skip the row and record it for the nightly batch to retry (no exception thrown — a taxonomy write must never fail because of BH-flag logic).

**Union semantics:** the new logic is **set-only** — it writes `TRUE` and never writes `FALSE`. This guarantees it cannot regress the Ancillary determination (D1/D2) and makes every path idempotent. Clearing the flag when the last BH taxonomy is deactivated is deliberately deferred to Clarification Q5 — noting that Re-Cred's `RemovePPLTaxonomy` element makes removal a real business action worth deciding on.

---

### Record & field specification (Pattern E)

**AC-22 — Every field written, by component**

**D3 / D4 — `PRM_HCProviderTaxonomyTriggerHandler.syncBehavioralHealthFlagToCaseManager()`**

| Object | Field | Value written | Rule / formula |
|---|---|---|---|
| `IndividualApplication` | `PRM_BehavioralHealth__c` | `TRUE` | Set only. Written when a qualifying BH taxonomy is inserted or activated for this Case Manager. Never written `FALSE`. Skipped if already `TRUE` (no-op DML avoidance). |

No other field on `IndividualApplication` is touched. No field on `HealthcareProviderTaxonomy`, `CareTaxonomy`, or `Account` is written.

**D5 / D6 — `PRM_SyncBehavioralHealthFlagBatch`**

| Object | Field | Value written | Rule / formula |
|---|---|---|---|
| `IndividualApplication` | `PRM_BehavioralHealth__c` | `TRUE` | Set only, same rule as D3. Only records whose current value is `FALSE` **and** whose `AccountId` has ≥1 qualifying active BH taxonomy are included in the update. Covers the Re-Cred carry-forward case (D5) and bypass/backfill (D6). |
| `PRM_ExceptionLog__c` | `PRM_ClassName__c` | `'PRM_SyncBehavioralHealthFlagBatch'` | Literal |
| `PRM_ExceptionLog__c` | `PRM_MethodName__c` | `'finish'` | Literal |
| `PRM_ExceptionLog__c` | `PRM_Message__c` | Summary text | `'Scanned=' + scanned + ', Updated=' + updated + ', Unchanged=' + unchanged + ', Skipped(no CM)=' + skipped + ', RunId=' + runId` |
| `PRM_ExceptionLog__c` | `PRM_LogLevel__c` | `'INFO'`, or `'ERROR'` if any chunk failed | Conditional |

> Exact `PRM_ExceptionLog__c` field API names to be confirmed against `PRM_ExceptionLogger`'s existing signature at build time (Clarification Q11) — reuse `PRM_ExceptionLogger.logException(...)` rather than writing the object directly (org convention).

---

## Technical Implementation (high-level)

**Cross-refs the AC numbers each row implements.**

| Component | Type | Change | Implements |
|---|---|---|---|
| `PRM_HCProviderTaxonomyTriggerHandler.cls` | Apex (existing) | **Add** `syncBehavioralHealthFlagToCaseManager(newList, oldMap)`, called from the existing `afterInsert` and `afterUpdate` overrides alongside `futureDatedProcessing`. Bulk-safe: one SOQL on `CareTaxonomy` to resolve BH `TaxonomyId`s (cache in a static `Set<Id>`), one optional SOQL for the `AccountId` fallback, one bulk `update` on `IndividualApplication`. Guard with a static re-entrancy flag. Wrap in try/catch → `PRM_ExceptionLogger` so a BH-flag failure never blocks a taxonomy save. | AC-1, AC-2, AC-3, AC-5, AC-6, AC-8, AC-11, AC-21 |
| `PRM_HealthcareProviderTaxonomyTrigger.trigger` | Apex Trigger (existing) | **No change** — already routes `after insert` + `after update` to the handler. | AC-1, AC-2, AC-3 |
| `PRM_SyncBehavioralHealthFlagBatch.cls` (new) | Apex Batch, `Database.Stateful`, `Schedulable` | `start()`: `QueryLocator` over `IndividualApplication` where `PRM_BehavioralHealth__c = FALSE` and record type in the in-scope set (optional `CreatedDate` floor for the one-time backfill run). `execute()`: for the chunk's `Id`s + `AccountId`s, one aggregate SOQL against `HealthcareProviderTaxonomy` joined to BH `CareTaxonomy` (matching on `PRM_CaseManager__c` **or** `AccountId`), then one bulk update. `finish()`: log summary via `PRM_ExceptionLogger`, chain nothing. Scope 200. `with sharing`; DML `as system` for the flag write (consistent with the existing handler's `update as system`). | AC-4, AC-9, AC-10, AC-12, AC-13, AC-21, AC-22 |
| `PRM_SyncBehavioralHealthFlagBatchTest.cls` (new) | Apex Test | Bulk 200+; single; BH-only; non-BH-only; mixed groupings; active vs pending vs future-dated; taxonomy with `PRM_CaseManager__c` populated; taxonomy with it **null** (AccountId fallback); **new Re-Cred CM for an already-BH practitioner (AC-4 carry-forward)**; practitioner with 2 open CMs; practice-location-only BH taxonomy → not flagged (AC-7); already-`TRUE` no-op (assert zero DML); re-run idempotency. ≥85% coverage. | AC-4, AC-7, AC-9, AC-10, AC-12, AC-13 |
| `PRM_HCProviderTaxonomyTriggerHandlerTest.cls` | Apex Test (existing) | **Extend** with BH-flag cases: insert BH taxonomy → CM flagged (PAR, Off Cycle **and Re-Cred** record types); insert non-BH → not flagged; activate pending BH with `PRM_CaseManager__c` **null** → flagged via AccountId fallback (AC-8); regression on existing primary-demotion + future-dated tests. | AC-1, AC-2, AC-3, AC-5, AC-6, AC-8 |
| `PRM_TriggerContextControl` / `PRM_TriggerBypassPermission` | Apex (existing) | **No change** — but their bypass behaviour is the documented reason `PRM_SyncBehavioralHealthFlagBatch` is mandatory. | AC-10 |
| `PRMDRCreateTaxonomy_1`, `PRMLoadOffCycleTaxonomy_1`, `PRMUpdateTaxonomyPDAReview_1`, `PRMDRLoadRCATHCPTax_1`, and the other taxonomy DataRaptors | DataRaptor | **No change** — deliberately. The trigger covers all write paths regardless of which DR performed the write; per-DR edits were rejected as unmaintainable. | AC-1, AC-2, AC-3, AC-8 |
| Re-Cred `TaxonomyNew` write path (`PRM_ReCredUpdate` / `PRM_ReCredQCUpdate` → `PRM_RecredPDAHelper_Procedure`) | OmniStudio | **No change** — but **trace at build time** to name the DataRaptor for QA test-data setup (Clarification Q13). Implementation does not depend on it. | AC-3 |
| `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1`, `PRM_CheckDueOnAncillaryReAssessmentBatch` | DataRaptor / Apex | **No change** — Ancillary determination preserved; new logic is set-only. | AC-11 |
| `PRMDRCreatePracticeLocationTaxonomy_1`, `PRMDRPracticeLocationTaxonomyNetworkUpdate_1`, `PRMDRCreateHFNTaxonomyRecords_1` | DataRaptor | **No change and out of scope** — these write `HealthcareFacilityNetwork`, not `HealthcareProviderTaxonomy`, so the trigger does not fire. Documented boundary. | AC-7 |
| `PRM_CaseManagerReportType.reportType-meta.xml` | Custom Report Type | Add `Behavioral Health` column — **covered by** `requirements/PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md` (hard dependency). | AC-14, AC-15 |
| New saved report — `PAR_ReCred_YoY_BHvsNonBH` (folder `PRM Reporting / Cohort`) | Lightning Report | On `PRM_CaseManagerReportType`. Filters: `RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')`, `CreatedDate = 2025 CALENDAR_YEAR`, `PRM_Stage__c = 'Complete'`, `PRM_Decision_Date__c = 2026 CALENDAR_YEAR`. Groupings: record type → `PRM_BehavioralHealth__c` → outcome bucket (row-level formula over `Status`; see Clarification Q4). | AC-14, AC-17 |
| New saved report — `PAR_ReCred_InFlight_BHvsNonBH` | Lightning Report | Same report type. Filters: same record types, `CreatedDate = 2025 CALENDAR_YEAR`, `PRM_Stage__c != 'Complete'`. Groupings: record type → `PRM_BehavioralHealth__c`. | AC-15 |
| New Lightning dashboard — `PAR_ReCred_Cohort_BH_Dashboard` (optional — Clarification Q7) | Dashboard | Side-by-side of the two reports with a global cohort-year filter. | AC-16 |
| Permission set — `PRM_SeniorDataReportingSpecialist` (existing) | Permission Set | Add FLS-read on `IndividualApplication.PRM_BehavioralHealth__c` if not already granted (Clarification Q6). | AC-18, AC-20 |
| Report folder — new `PRM Reporting / Cohort` | Analytics Folder | Share with `PRM_SeniorDataReportingSpecialist`, `PRM_CredentialingUser`, `PRM_ProviderDataAdmin`. | AC-20 |

### Reference — the BH-taxonomy predicate (`BH_RULE`, single source of truth for write paths D3–D6)

```sql
SELECT Id FROM CareTaxonomy
WHERE PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
```

A taxonomy row qualifies (**`BH_RULE`**) when `IsActive = TRUE` **and** `PRM_Pending__c = FALSE` **and** `TaxonomyId` is in that set. The trigger handler (D3/D4) and the batch (D5/D6) MUST evaluate the identical predicate — if they diverge, the nightly batch will silently flip flags the trigger didn't set (or vice versa) and the report will drift between runs.

Recommended: expose the grouping literal as a Custom Label or `PRM_GlobalConstant` member referenced by both the handler and the batch, rather than hardcoding it (org convention — no hardcoded config).

---

## Definition of done

**BH flag write path**

- [ ] `PRM_HCProviderTaxonomyTriggerHandler.syncBehavioralHealthFlagToCaseManager()` implemented and wired into `afterInsert` + `afterUpdate`.
- [ ] Verified in QA: adding a BH taxonomy on **PAR** (`PRM_PractitionerParticipationForm`) flags the Case Manager (AC-1).
- [ ] Verified in QA: adding a BH taxonomy on **Off Cycle** (`PRM_OffCycleCredentialing`) flags the Case Manager (AC-2).
- [ ] Verified in QA: adding a BH taxonomy on **Re-Cred** via `TaxonomyNew` (`PRM_ReCredUpdate` / `PRM_ReCredQCUpdate`) flags the **Re-Cred** Case Manager for the current cycle (AC-3).
- [ ] Verified in QA: opening a **new Re-Cred Case Manager** for a practitioner who is already BH from a prior cycle results in the new CM being flagged after the sync runs (AC-4 carry-forward — batch path, no taxonomy DML involved).
- [ ] Verified in QA: a BH taxonomy activated at **PDA Review** (`PRMUpdateTaxonomyPDAReview_1`, which does **not** stamp `PRM_CaseManager__c`) flags the CM via the `AccountId` fallback (AC-8).
- [ ] Verified in QA: a non-BH taxonomy does **not** flag the Case Manager (AC-5).
- [ ] Verified in QA: `PRM_CaseManager__c`-null taxonomy resolves via the `AccountId` fallback (AC-21 resolution step 2).
- [ ] Verified in QA: future-dated / pending BH taxonomy does not flag until activated, then does (AC-9).
- [ ] Verified in QA: a bulk-context taxonomy load bypasses the trigger, and the nightly batch picks it up (AC-10).
- [ ] Verified in QA: a **practice-location-only** BH taxonomy (`HealthcareFacilityNetwork`) does **not** flag the CM, and the business has signed off on that boundary (AC-7, Clarification Q14).
- [ ] Verified in QA: a taxonomy-save failure is impossible from BH-flag logic — exception is caught and logged, taxonomy still saves.
- [ ] Re-Cred `TaxonomyNew` DataRaptor traced and named in this story (Clarification Q13) so QA test-data setup is reproducible.
- [ ] Regression: existing primary-taxonomy demotion (`demoteExistingPrimaryTaxonomy`) and future-dated processing (`futureDatedProcessing`) behave unchanged; `PRM_HCProviderTaxonomyTriggerHandlerTest` still green.
- [ ] Regression: Ancillary BH determination unchanged; new logic never writes `FALSE` (AC-11).
- [ ] Regression: Re-Cred QC (`PRM_RecredQC_English_13`) primary-taxonomy count/validation elements (`IPToCountPrimaryTaxonomy`, `SetErrorsMultiplePrimaryTaxonomy`) behave unchanged — they share the same trigger.
- [ ] Grouping literal externalised to a Custom Label / `PRM_GlobalConstant` (not hardcoded in three places).

**Batch / backfill**

- [ ] `PRM_SyncBehavioralHealthFlagBatch` deployed with ≥85% Apex coverage, incl. bulk-200 and the AccountId-fallback cases.
- [ ] Dry-run in QA sandbox; results reconciled to Query 8b in `requirements/SOQL/2026-08-13_CreatedIn2025_CompletedIn2026_ParRecred.md` within ±0 records.
- [ ] Re-run immediately after a successful run updates **zero** records (AC-13 idempotency).
- [ ] One-time historical backfill executed in production during a low-traffic window, with summary logged via `PRM_ExceptionLogger`.
- [ ] Nightly schedule registered and confirmed running.

**Reports**

- [ ] Dependency shipped: `Behavioral Health` column exposed on `PRM_CaseManagerReportType` (per `PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md`).
- [ ] Two saved reports created in the `PRM Reporting / Cohort` folder; folder shared with the three permission sets.
- [ ] Reports reconciled to Queries 1–8 in the SOQL reference within ±0 records for the 2025→2026 window.
- [ ] Reports run cleanly for the 2026→2027 window (parameterization proven).
- [ ] FLS verified: `PRM_ProviderDataAdmin` (read-only) sees the field; a user in no listed permission set does not.
- [ ] Optional dashboard demoed to the business (if in scope).
- [ ] Story cross-referenced in `.cursor/AGENTS.md` "Recent Activity Log".

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the BH determination be based **strictly** on `Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'`, or should IBX also include the curated list of ~30 physician / APP taxonomy codes from `.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md` that belong to other groupings but are BH-adjacent? Current design: grouping-only (business-confirmed 2026-08-13). | Determines whether the `BH_RULE` `CareTaxonomy` predicate is a single-value grouping equality or a hybrid grouping-OR-code set. Affects write paths D3–D6 and the report equally, so it must be answered once and applied in one place. | BA / Reporting Lead |
| 2 | Should the BH flag consider **primary taxonomy only** (`HealthcareProviderTaxonomy.IsPrimaryTaxonomy`) or **any active taxonomy**? Current design: any active. | Governs which practitioners qualify. Any-active is broader and simpler. | BA |
| 3 | **Should the flag be cleared** when a practitioner's last active BH taxonomy is deactivated or end-dated? Current design: **set-only, never cleared** — chosen so the new logic can't regress the Ancillary determination (D1/D2), which is driven by Provider Type & Service rather than taxonomy. Clearing would require deciding precedence between the two rules. **Note:** Re-Cred exposes an explicit `RemovePPLTaxonomy` element and RCAT has a full-termination path (`PRM_RCATFullTermination_Procedure_1` → `PRMDRLoadRCATHCPTax_1`), so taxonomy removal is a real, routine business action — not a rare edge case. | **Highest-impact open item.** If clearing is required, the trigger needs a "recompute both rules" path and the batch needs a two-way sweep, adding ~M effort. It also changes the report's meaning from "was ever BH" to "is currently BH". | BA / Compliance |
| 4 | What is the canonical "outcome" field on `IndividualApplication` for the report grouping? The SOQL reference uses `Status` (`'Approved'` / `'Denied'` / `'Withdrew'`) combined with `PRM_Stage__c = 'Complete'` + `PRM_Decision_Date__c`. Confirm `Status` is the right field to build the row-level bucket formula over. | Determines whether a formula field is added to `IndividualApplication` or a report row-level formula suffices. | BA / Developer |
| 5 | For a taxonomy whose `PRM_CaseManager__c` is null (the non-stamping DataRaptors — notably `PRMUpdateTaxonomyPDAReview_1`) and whose practitioner has **more than one open** PAR/Re-Cred Case Manager — should the flag be set on **all** open CMs, only the **most recent**, or should the row be skipped and reported? Current design: **all open CMs**. **This is more likely than it first appears in Re-Cred**, where a practitioner can have an open Re-Cred cycle *and* a concurrent Off Cycle or PAR request for a new location. | Affects fallback correctness and could over-flag. Directly determines AC-8 behaviour. | BA / Developer |
| 6 | Does `PRM_SeniorDataReportingSpecialist` currently have FLS-read on `IndividualApplication.PRM_BehavioralHealth__c`? Its permission set XML declares `customPermissions` and `classAccesses` but no `<fieldPermissions>` — verify in-org. | Determines whether AC-20 needs a permset update. | Admin |
| 7 | Is the Lightning **dashboard** in scope, or ship just the two saved reports? | Effort (~S). | Product / Reporting Lead |
| 8 | What **cadence** should `PRM_SyncBehavioralHealthFlagBatch` run on? Recommended: nightly, to cover the trigger bypasses and future-dated activations. Alternative: weekly, or on-demand only. | Data freshness vs org async capacity. Nightly is the safe default given `PRM_FutureDatedProcessingUtil` activates taxonomies in batch context. | Ops / Release Manager |
| 9 | Should the report include a **fifth outcome bucket "Other / Data Quality"** for records where `PRM_Stage__c = 'Complete'` but `PRM_Decision_Date__c` is NULL, or force those into In-Flight? Current design: force into In-Flight. | Bucket definition tightness. | BA |
| 10 | Historical scope of the one-time backfill: **2025-onwards only** (matches the report window) or **all time**? Current design: parameterised `CreatedDate` floor, defaulting to 2025-01-01. | Batch runtime and blast radius of the production run. | BA / Release Manager |
| 11 | Confirm the `PRM_ExceptionLogger` method signature and the `PRM_ExceptionLog__c` field API names for the batch summary log (the Pattern E table lists inferred names). Org convention is to reuse the logger, not write the object directly. | Prevents an invalid-field deploy error. | Developer |
| 12 | Is there an existing GUS/ADO work item for this reporting request, or should one be created and linked? | Tracking. | Product / Scrum Master |
| 13 | **Which DataRaptor does the Re-Cred `TaxonomyNew` element ultimately write through?** `PRM_ReCredUpdate_English_7` and `PRM_ReCredQCUpdate_English_3` both expose `TaxonomyNew`, and `PRM_RecredPDAHelper_Procedure` is described as *"Update the ReCred data related to the Taxonomy and Networks of Practice Location"* — but the DR name is embedded in the IP's runtime payload and could not be resolved by static inspection. Needs a runtime trace or developer confirmation. | **Does not block implementation** (the trigger fires regardless of which DR writes the row) — but it **does** block reproducible QA test-data setup for AC-3, and it's the only way to confirm whether Re-Cred's add path writes practitioner-level `HealthcareProviderTaxonomy` or only practice-location `HealthcareFacilityNetwork`. | Developer / OmniStudio SME |
| 14 | **Should practice-location-level BH taxonomy count toward the flag?** Re-Cred's `HFNCareTaxonomy`, `HFNPracticeLocationTaxonomy`, and `RemovePPLTaxonomy` elements write **`HealthcareFacilityNetwork`**, a different object that the `HealthcareProviderTaxonomy` trigger does not see. Current design: **practitioner-level only**, matching the agreed BH cohort definition and every query in the SOQL reference. | If the business wants practice-location taxonomy included, this is **not a small change**: it needs a second trigger on `HealthcareFacilityNetwork`, a second batch sweep, and a redefinition of the BH cohort in all Section-2 queries — the report and the flag would no longer agree with the SOQL baseline. Adds ~M–L. | BA / Reporting Lead |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| **`PRM_HCProviderTaxonomyTriggerHandler`** | Apex Trigger Handler | **HIGH** | Adds logic to a handler that fires on **every** `HealthcareProviderTaxonomy` insert and update across the whole org — PAR, Off Cycle, Re-Cred, PSV, App Review, PDM, Provider Change, Ancillary, RCAT, reinstatement. Must be strictly bulk-safe (no SOQL/DML in loops), re-entrancy-guarded, and fully exception-isolated so a BH-flag failure can never block a taxonomy save. This is the single highest-risk item in the story and the reason regression coverage on the two existing handler methods is mandatory. |
| `PRM_HealthcareProviderTaxonomyTrigger` | Apex Trigger | **NONE** | Already routes `after insert` / `after update` to the handler — no change. |
| **31 taxonomy-writing DataRaptors** (incl. `PRMDRCreateTaxonomy_1`, `PRMLoadOffCycleTaxonomy_1`, `PRMUpdateTaxonomyPDAReview_1`, `PRMDRLoadRCATHCPTax_1`) | OmniStudio DR | **NONE** | Deliberately untouched — the whole point of the trigger-based design. Zero IP version bumps, zero OmniScript changes, zero re-activation risk. This is also why the unresolved Re-Cred DR (Q13) doesn't block the build. |
| PAR / Off Cycle / **Re-Cred** OmniScripts | OmniStudio OS | **NONE** | No change. Taxonomy capture elements (`TaxonomySection`, `AddAddressTaxonomy`, `TaxonomyNew`, `PSVPractitonerTaxonomy`) are read-only inputs to the existing DR chain. |
| **Re-Cred QC validation elements** (`IPToCountPrimaryTaxonomy`, `SetErrorsMultiplePrimaryTaxonomy`, `VerifyCareTaxonomyRD`) | OmniStudio OS / IP | **LOW — regression risk** | No change, but these run against the same `HealthcareProviderTaxonomy` records the modified trigger now touches. Because the new logic writes only `IndividualApplication` (never the taxonomy row) it should be inert to them — must still be smoke-tested. |
| Ancillary CM-creation DR + re-assessment batch | OmniStudio DR / Apex | **NONE** | Explicitly untouched; set-only semantics guarantee no regression (AC-11). |
| `IndividualApplication.PRM_BehavioralHealth__c` | Custom Field | **LOW** | No schema change; write-sources expanded from 2 to 6. |
| `HealthcareProviderTaxonomy`, `CareTaxonomy` | Standard Objects | **NONE** | Read-only inputs. |
| **`HealthcareFacilityNetwork`** (practice-location taxonomy) | Standard Object | **NONE — out of scope** | Not read and not written. Documented boundary (AC-7, Q14): a practitioner whose only BH taxonomy is at practice-location level will not be flagged. |
| `PRM_SyncBehavioralHealthFlagBatch` | Apex Batch | **MEDIUM** | New nightly job + one-time historical run against O(10k) records. Consumes one scheduled-job slot and adds nightly async load. Must be idempotent (AC-13). **Load-bearing for Re-Cred:** it is the only mechanism that flags a new Re-Cred CM opened for an already-BH practitioner (AC-4), since that event involves no taxonomy DML. |
| `PRM_CaseManagerReportType` | Custom Report Type | **LOW** | Column exposure — handled by the dependent story. |
| Saved reports + folder | Analytics | **LOW** | New artifacts; no existing report affected. |
| `PRM_SeniorDataReportingSpecialist` | Permission Set | **LOW** | Possible FLS addition (Clarification Q6). |
| **Downstream consumers of `PRM_BehavioralHealth__c`** | Existing Reports / Dashboards | **MEDIUM — BREAKING SEMANTIC CHANGE** | Today the flag effectively means *"this is an Ancillary BH provider type & service"*. After this story it means *"this Case Manager is Behavioral Health by Ancillary type **or** practitioner taxonomy"*. Any existing report, dashboard, list view, or automation that treats `BH = TRUE` as a proxy for "Ancillary" will start including PAR / Off Cycle / **Re-Cred** records. Re-Cred materially enlarges this blast radius, because the AC-4 carry-forward rule flags **every** Re-Cred CM belonging to an already-BH practitioner — a much larger population than newly-added BH taxonomies alone. **Must be communicated to report owners before deploy**, and existing Ancillary reports should add an explicit record-type filter. |
| `PRM_CheckDueOnAncillaryReAssessmentBatch` | Apex Batch | **LOW** | No code change, but it now shares the field with the new writers. Because both only ever set `TRUE`, there is no write-ordering conflict. |

---

## Estimated Effort — AI-estimated; validate with team

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Dependency: `PRM_CaseManagerReportType` column exposure | Metadata add | **S** | Already estimated in the dependent story. |
| `PRM_HCProviderTaxonomyTriggerHandler` — new `syncBehavioralHealthFlagToCaseManager()` | Apex (existing class) | **M** | One bulk-safe method + CM resolution with `AccountId` fallback + re-entrancy guard + exception isolation. |
| `PRM_HCProviderTaxonomyTriggerHandlerTest` — extend | Apex Test | **M** | New BH cases **plus** regression protection for the two existing methods on a high-traffic handler. |
| `PRM_SyncBehavioralHealthFlagBatch` + Schedulable | Apex Batch | **M** | Stateful, bulk-safe, dual-match (`PRM_CaseManager__c` **or** `AccountId`), idempotent. Also carries the Re-Cred carry-forward rule (AC-4). |
| `PRM_SyncBehavioralHealthFlagBatchTest` | Apex Test | **M** | Bulk-200, fallback path, pending/future-dated, idempotency, multi-open-CM, Re-Cred carry-forward, practice-location-only exclusion. ≥85% coverage. |
| Trace the Re-Cred `TaxonomyNew` write path (Q13) | Investigation | **S** | Runtime trace or SME confirmation; needed for QA test-data setup, not for implementation. |
| Grouping literal → Custom Label / `PRM_GlobalConstant` | Config | **S** | Avoids hardcoding in three places. |
| Outcome-bucket row-level formula (Q4) | Report formula | **S** | Row-level formula preferred over a new formula field. |
| Two saved reports + folder + folder sharing | Analytics | **M** | Groupings, bucket formula, parameter-friendly year filters. |
| Optional dashboard | Analytics | **S** | If Clarification Q7 = yes. |
| Regression QA — PAR, Off Cycle, **Re-Cred (Update, QC Update, QC)**, PSV, App Review, PDM, RCAT, Ancillary taxonomy saves | Manual QA | **L** | **Largest QA item.** The trigger fires org-wide, so every flow that writes a taxonomy needs a smoke test — not just the ones the report covers. Re-Cred alone adds three OmniScripts plus the PDA-Review activation path and the Re-Cred QC primary-taxonomy validation elements. |
| Reconciliation vs SOQL reference | Manual QA | **S** | Cross-check report totals against Queries 1–8. |
| Downstream-consumer impact comms (semantic change) | Coordination | **S** | Notify owners of existing `PRM_BehavioralHealth__c` reports before deploy. |
| Deployment + backfill orchestration | Release | **M** | Deploy → dry-run batch in staging → reconcile → prod backfill → register nightly schedule. |

**Total Estimated Effort:** **L** (~7–10 engineer-days) — *AI-estimated; re-baseline after Clarification Q1–Q5, Q8, and Q13–Q14 are answered.* Adding explicit Re-Cred coverage raised the range by ~1 day: the implementation is unchanged (the trigger already fires for Re-Cred), but the Re-Cred carry-forward rule (D5/AC-4) needs its own batch logic and tests, and three more OmniScripts plus the PDA-Review activation path enter regression QA. **If Q14 returns "include practice-location taxonomy", add M–L** — that would require a second trigger on `HealthcareFacilityNetwork` and a redefinition of the BH cohort across the SOQL baseline.

> **Effort note vs. the earlier draft of this story:** the original plan (add DR-Extract + DR-Load steps to three Integration Procedures) looked cheaper per-component but was **wrong** — it would have missed 28 of the 31 taxonomy write paths and required a version bump on every affected IP. The trigger-based design shifts effort from OmniStudio changes into Apex + regression QA, and is the reason the QA line item is now the largest.

---

## Cross-References / Existing Stories

- **`requirements/PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md`** — Hard dependency: exposes `PRM_BehavioralHealth__c` as a selectable column on the target report type. Must ship first.
- **`requirements/PRM_CaseManagerReportType_AddMedicalDirectorReview_UserStory.md`** — Same-shape precedent for report-type column exposure.
- **`requirements/SOQL/2026-08-13_CreatedIn2025_CompletedIn2026_ParRecred.md`** — Source-of-truth SOQL. Report totals reconcile to this.
- **`.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md`** — Cross-check of the business's BH practitioner list against `CareTaxonomy` groupings. Documents why the grouping-only filter is intended and what it excludes.
- **`requirements/Reporting/IntegrityReporting_InitialCredReview_BusinessOverview.md`** — Adjacent Cred-Review reporting work; no direct dependency.
- **`requirements/BH_Medical_Dual_Credentialing_User_Stories.md`** — Related BH cohort work at the story level.
