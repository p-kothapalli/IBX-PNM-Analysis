# Patient Accept Status Effective Dates at Level 4 — Calculation Analysis

**Date:** 2026-08-03
**Object (Level 4):** `HealthcareFacilityNetwork` — record type `PRM_FacilityPractitionerTxNw` ("Practitioner at Practice Location Taxonomy and Network with Role")
**Reference example:** [HealthcareFacilityNetwork 0bYUW000000YYl02AG](https://ibx--qa.sandbox.lightning.force.com/lightning/r/HealthcareFacilityNetwork/0bYUW000000YYl02AG/view)
**Source of truth for target behavior:** [Data Details: Analysis of Production Issue 08202025 (Patient Accept Status, Lv4) — "Solution Option Reviewed" tab](https://docs.google.com/spreadsheets/d/1K25mOVrsoS5mcWH4WAsnImD9TLgZz2SKXM4x6ez1mus/edit?gid=1024379097)

> **Purpose:** map out *every* flow / OmniScript / Integration Procedure / DataRaptor / Apex path that calculates the **Patient Accept Status Effective From / Effective To** dates at Level 4, so the same pattern can be authored as build stories for **Role Effective From / To (+ Calculated)** and **Taxonomy Effective From / To (+ Calculated)**.

---

## 1. Field model (grounded in org metadata)

The three "date pairs" on `HealthcareFacilityNetwork` all follow the **same three-part shape**: a *stamped* (writable) field, a *derived* formula field that falls back to the record's Network effective dates, and the standard **Network** effective dates as the fallback base.

| Business term (sheet) | API name | Type | Notes |
|---|---|---|---|
| Network Effective From (stamped) | `EffectiveFrom` | Date (standard) | Base fallback for every "Calculated"/derived field |
| Network Effective To (stamped) | `EffectiveTo` | Date (standard) | Base fallback |
| Patient Accept Status Effective From (**stamped**) | `PRM_PanelStatusEffFromSet__c` | Date, **history-tracked**, writable | What the flows actually *write* |
| Patient Accept Status Effective To (**stamped**) | `PRM_PanelStatusEffToSet__c` | Date, **history-tracked**, writable | What the flows actually *write* |
| Patient Accept Status Effective From (**derived**) | `PRM_PanelStatusEffFrom__c` | Date, **formula** | `IF(ISBLANK(PRM_PanelStatusEffFromSet__c), EffectiveFrom, PRM_PanelStatusEffFromSet__c)` |
| Patient Accept Status Effective To (**derived**) | `PRM_PanelStatusEffTo__c` | Date, **formula** | `IF(ISBLANK(PRM_PanelStatusEffToSet__c), EffectiveTo, PRM_PanelStatusEffToSet__c)` |
| Patient Accept Status value | `PanelStatus` | Picklist | Open to New / Open to Existing / Closed to All |
| "Effective Today" flag | `PRM_FacilityNetworkEffectiveToday__c` | Checkbox, formula | `TODAY()` between `EffectiveFrom`/`EffectiveTo` |
| Active | `IsActive` | Checkbox | TRUE when eff-from set & eff-to empty; FALSE once eff-to populated |

**Role date pair (already exists, mostly un-populated):**

| Business term | API name | Type | Formula |
|---|---|---|---|
| Role Effective From (stamped) | `PRM_RoleEffectiveFrom__c` | Date, writable | — |
| Role Effective To (stamped) | `PRM_RoleEffectiveTo__c` | Date, writable | — |
| Role Effective From Calculated | `PRM_RoleEffectiveFromCalculated__c` | Date, formula | `IF(ISBLANK(PRM_RoleEffectiveFrom__c), EffectiveFrom, PRM_RoleEffectiveFrom__c)` |
| Role Effective To Calculated | `PRM_RoleEffectiveToCalculated__c` | Date, formula | `IF(ISBLANK(PRM_RoleEffectiveTo__c), EffectiveTo, PRM_RoleEffectiveTo__c)` |

**Taxonomy date pair (already exists, un-populated):**

| Business term | API name | Type | Formula |
|---|---|---|---|
| Taxonomy Effective From (stamped) | `PRM_TaxonomyEffectiveFrom__c` | Date, writable | — |
| Taxonomy Effective To (stamped) | `PRM_TaxonomyEffectiveTo__c` | Date, writable | — |
| Taxonomy Effective From Calculated | `PRM_TaxonomyEffectiveFromCalculated__c` | Date, formula | `IF(ISBLANK(PRM_TaxonomyEffectiveFrom__c), EffectiveFrom, PRM_TaxonomyEffectiveFrom__c)` |
| Taxonomy Effective To Calculated | `PRM_TaxonomyEffectiveToCalculated__c` | Date, formula | `IF(ISBLANK(PRM_TaxonomyEffectiveTo__c), EffectiveTo, PRM_TaxonomyEffectiveTo__c)` |

> **Key finding #1 — the "Calculated"/derived layer is already built and identical across all three pairs.** The `*Calculated__c` formula fields for Role and Taxonomy already mirror the Patient Accept Status `PRM_PanelStatusEffFrom__c` / `PRM_PanelStatusEffTo__c` formulas exactly. No new formula work is required; the derived value automatically falls back to the Network `EffectiveFrom`/`EffectiveTo` when the stamped field is blank.
>
> **Key finding #2 — the real work is the *stamping* layer.** The behavior the sheet documents (insert-new + terminate-old, Active flip, future-dating) is about *who writes the stamped `*Set` / `*Effective` fields, and when*. That logic exists richly for Patient Accept Status and is almost entirely **absent** for Role and Taxonomy (see §4).

---

## 2. Target behavior per the "Solution Option Reviewed" tab

The reviewed option models each panel-status change as a **new effective window** rather than an in-place edit:

1. **Original record (Insert):** stamp Effective From; leave Effective To blank → `Active = TRUE`.
2. **Panel status change (Insert new + Update old):** the *old* row is terminated (`...EffToSet` = change date − 1 / the boundary) → `Active = FALSE`; a *new* row is inserted for the new status with `...EffFromSet` = change date → `Active = TRUE`.
3. **Termination (Update):** stamp `...EffToSet` on the active row → `Active = FALSE`.
4. **Active flag rule:** `Active = TRUE` when the effective-from (Network + Accept Status) is set and effective-to (Network + Accept Status) is empty; `Active = FALSE` when effective-to is populated.
5. **Documented limitation:** future-dating panel-status changes needs both the current and next records future-dated; because a record holds a *single* effective window and supports only one event set per object, there is a **gap** for stacked future changes.

The **derived formula** (`...EffFrom__c` / `...EffTo__c`) is what queries/reporting read, so a row that never had a specific Accept-Status date still reports the Network window. This is exactly the semantics the Role/Taxonomy `*Calculated__c` fields already provide.

---

## 3. How Patient Accept Status Effective dates get calculated today — the full map

The stamped `PRM_PanelStatusEffFromSet__c` / `PRM_PanelStatusEffToSet__c` fields are written through **six channels**. This is the "flows / OmniScripts mapped out" deliverable.

### Channel A — Manual Update (PDM Manual Changes) — *interactive*
- **OmniScripts:** `PRM_PDMManualChanges_English_*`, `PRM_PDMManualUpdate_English_*`, `PRM_PDMManualUpdatePracticeLocation_English_*`
- **Integration Procedure:** `PRM_ManualChangePDAUpdates_Procedure_*` → element `LoadPatientAcceptStatus`
- **DataRaptor (Load):** `PRMLoadManualUpdatePAS` — writes `PanelStatus`, `PRM_PanelStatusEffFromSet__c`, `PRM_PanelStatusEffToSet__c` onto `HealthcareFacilityNetwork`
- **Apex:** `PRM_PDMManualUtility`, and the async `PRM_PASUpdateBatch` (see Channel F)

### Channel B — Provider Change Form / PDA review (PCF/PDA)
- **Integration Procedures:** `PRM_FetchPCFDetails_Procedure_*` (element `DRTransPCFPatientStatus`), `PRM_ProviderChangePDAUpdatesHelper_Procedure_*` (element `DRLoadHCFacNwPCFPDA`), `PRM_ProviderChangePDAUpdates_Procedure_*`
- **DataRaptors:** `PRMTransPCFPatientStatus` (transform), `PRMLoadHCFacNwPCFPDA` (load), `PRMLoadPASDataPDMPDA` (load), `PRMExtractFacilityNetworkPCF` / `PRMExtractHFNNwPCF` (extract)

### Channel C — Panel-status validation (overlap / gap enforcement)
- **Integration Procedure:** `PRM_ValidatePanelStatus_Procedure_*` (also `PRM_ValidatePanelStatusPCFPDA*`)
- **DataRaptors:** `PRMTransformNewPanelStatus`, `PRMTransformOldPanelStatus` — build the "old window terminated + new window opened" pair described in §2

### Channel D — Trigger-driven roll-up & future-dating (`HealthcareFacilityNetwork` trigger)
- **Apex:** `PRM_HCFacilityNetworkTriggerHandler` → `PRM_HCFacilityNetworkTriggerHelper`
  - `futureDatedProcessing(...)` — on insert/update, when `PRM_PanelStatusEffFromSet__c` / `...EffToSet__c` (or Network `EffectiveFrom`/`EffectiveTo`, or `PRM_Pending__c`) change, clones the row and **maps the stamped Accept-Status dates onto the Network dates** for the record-type `PRACFACNWTX`, feeding Future Dated Processing.
  - `updatePanelStatus(...)` — rolls the practitioner-level (`PRACFACNWTX`) panel status up to the facility-network (`FACNW`) record.
  - `hfnRecordsEffectiveRangeRollup(...)` — recomputes `EffectiveFrom` (MIN) / `EffectiveTo` (MAX) on the parent PL-Taxonomy (`PRACLOCTAX`) and PL-Network (`FACNW`) rows from their active children.

### Channel E — Scheduled Future Dated Processing (FDP)
- **Apex:** `PRM_FutureDatedProcessingBatchHandler.processRecords(...)`
  - For `HealthcareFacilityNetwork` rows of record type `PRACFACNWTX`, on `Activate` it writes `PRM_PanelStatusEffFromSet__c = PRM_EffectiveDate__c`; on `Terminate` it writes `PRM_PanelStatusEffToSet__c = PRM_EffectiveDate__c` (constants `panelEffectiveFromStr` / `panelEffectiveToStr`). Other object types use `EffectiveFrom`/`EffectiveTo` or `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c`.

### Channel F — Async Patient-Accept-Status batch (bulk apply from UI)
- **Apex:** `PRM_PASUpdateBatch` — for each selected L4 row: **clones** the record with the new `PanelStatus` + `PRM_PanelStatusEffFromSet__c = effDate` (new active window), and **terminates the original** with `PRM_PanelStatusEffToSet__c = effDate`; chains to `PRM_CMACreationBatch`. This is the code-level realization of the §2 "insert new + terminate old" model.

### Channel G — Data conversion & data-fix (DART→SF and corrections)
- **DataRaptors (Load):** `PRMLoadHCFacilityNetwork`, `PRMLoadHCFacNwPCFPDA`, `PRMDRUpdateHCPracFacHCFNProviderNpi`
- **Apex data-fix executors:** `PRM_PatientAcceptStatusDateShiftExecutor`, `DFX_PatientAcceptStatusDateShiftExecutor` (+ tests) driven by Custom Metadata `DFX_DataFixConfiguration.PatientAcceptStatusShift`

---

## 4. Current state of Role & Taxonomy effective dates (the gap)

| Layer | Patient Accept Status | Role | Taxonomy |
|---|---|---|---|
| Derived / "Calculated" formula field | ✅ `PRM_PanelStatusEffFrom__c` / `...EffTo__c` | ✅ `PRM_RoleEffectiveFromCalculated__c` / `...ToCalculated__c` | ✅ `PRM_TaxonomyEffectiveFromCalculated__c` / `...ToCalculated__c` |
| Stamped field written by **Manual Update** (Channel A) | ✅ `PRMLoadManualUpdatePAS` | ❌ | ❌ |
| Stamped field written by **PCF/PDA** (Channel B) | ✅ | ❌ | ❌ |
| **Validation** new/old window (Channel C) | ✅ | ❌ | ❌ |
| **Trigger** roll-up / future-date map (Channel D) | ✅ | ❌ | ❌ |
| **FDP** scheduled activate/terminate (Channel E) | ✅ | ❌ | ❌ |
| **Async bulk** insert-new/terminate-old (Channel F) | ✅ (`PRM_PASUpdateBatch`) | ❌ | ❌ |
| **Conversion / data-fix** (Channel G) | ✅ | ❌ | ❌ |
| Interactive **Manage** tab | (n/a — panel status editable everywhere) | ⚠️ **only** writer today: `PRM_ManageRolesControllerHelper` (`buildEditRow` / `buildCreateRow` write `PRM_RoleEffectiveFrom__c` / `...To__c` from a modal payload) | ❌ no writer |

> **Key finding #3 — Role effective dates are written in exactly one place** (`PRM_ManageRolesControllerHelper`, the Provider Action Center *Manage Roles* tab), and only for pending, manually-added rows. **Taxonomy effective dates have no writer at all.** None of the mature Patient-Accept-Status channels (Manual Update DR, PCF/PDA, validation, trigger roll-up, FDP batch, async bulk, conversion) currently stamp Role or Taxonomy dates.

---

## 5. Candidate story backlog (to be authored via the User Story Solution Architect)

The end goal is to replicate the Patient Accept Status pattern for the Role and Taxonomy date pairs. Each candidate below maps to one of the channels in §3. These are **skeletons/scope notes**, not finished stories — each should be written up through the `user-story-architect` skill (concrete PDM/PDA/Network-QC persona, Given/When/Then in business language, `## Technical Implementation (high-level)`, effort table) and grounded against the active OmniStudio versions before build.

**Role Effective From / To (+ Calculated):**
1. **R-A** Manual Update (PDM Manual Changes) stamps `PRM_RoleEffectiveFrom__c` / `...To__c` — mirror `PRMLoadManualUpdatePAS` in the `PRM_ManualChangePDAUpdates` IP.
2. **R-B** PCF / PDA review stamps Role dates — mirror `PRMTransPCFPatientStatus` / `PRMLoadHCFacNwPCFPDA`.
3. **R-C** Role-change validation (terminate old role window + open new) — mirror `PRMTransformNewPanelStatus` / `...Old` in `PRM_ValidatePanelStatus`.
4. **R-D** Trigger roll-up + future-date mapping for Role dates — extend `PRM_HCFacilityNetworkTriggerHelper` (`futureDatedProcessing`, effective-range roll-up).
5. **R-E** FDP scheduled Activate/Terminate writes Role dates — extend `PRM_FutureDatedProcessingBatchHandler` (add `PRM_RoleEffectiveFrom__c` / `...To__c` alongside the panel constants).
6. **R-F** Async bulk role-change (insert-new / terminate-old) — mirror `PRM_PASUpdateBatch`.
7. **R-G** Conversion / data-fix backfill of Role dates — mirror the PAS shift executors.

**Taxonomy Effective From / To (+ Calculated):** the identical **T-A … T-G** set for `PRM_TaxonomyEffectiveFrom__c` / `...To__c`.

**Cross-cutting decisions to confirm before writing stories:**
- **Grain:** Role dates key on Facility + Taxonomy + **Role**; Taxonomy dates key on Facility + **Taxonomy**. Confirm whether the "insert-new / terminate-old" window model (§2) applies per-role and per-taxonomy, or whether these are simple in-place stamps (given Role/Taxonomy change less often than panel status).
- **Active-flag interaction:** confirm whether Role/Taxonomy effective-to should influence `IsActive` (today only Network + Accept Status do).
- **Future-dating gap:** the documented single-window limitation (§2) applies equally to Role/Taxonomy — decide whether to accept the gap or design stacked windows.
- **Naming inconsistency:** Patient Accept Status uses `...Set__c` for the stamped field; Role/Taxonomy use the bare `...Effective(From|To)__c` for the stamped field and `...Calculated__c` for the formula. Stories should reference the exact API names above to avoid confusion.

---

## 6. Components inventory (quick reference)

**Apex:** `PRM_HCFacilityNetworkTriggerHandler`, `PRM_HCFacilityNetworkTriggerHelper`, `PRM_FutureDatedProcessingBatchHandler`, `PRM_PASUpdateBatch`, `PRM_PDMManualUtility`, `PRM_PDMDataHelper`, `PRM_ManageRolesControllerHelper` (Role writer), `PRM_PatientAcceptStatusDateShiftExecutor`, `DFX_PatientAcceptStatusDateShiftExecutor`, `PRM_HFNCascadeBatch`, `PRM_LinkPLPPLTNBatch`, `PRM_AddPracPPLTNBatch`.

**Integration Procedures:** `PRM_ManualChangePDAUpdates`, `PRM_FetchPCFDetails`, `PRM_ProviderChangePDAUpdates(Helper)`, `PRM_ValidatePanelStatus`, `PRM_ValidatePanelStatusPCFPDA`, `PRM_PDMPLRecordsCreationHelper`, `PRM_PDMRecordsCreationHelper`.

**DataRaptors:** `PRMLoadManualUpdatePAS`, `PRMTransPCFPatientStatus`, `PRMLoadHCFacNwPCFPDA`, `PRMLoadPASDataPDMPDA`, `PRMTransformNewPanelStatus`, `PRMTransformOldPanelStatus`, `PRMExtractFacilityNetworkPCF`, `PRMExtractHFNNwPCF`, `PRMExtractFacilityNetwork`, `PRMLoadHCFacilityNetwork`, `PRMDRUpdateHCPracFacHCFNProviderNpi`, `PRMDRExtractAddressLocAddressPracLocNetwork`, `PRMProvdrChngExtractFacilityNetwork`, `PRMExtractSpecialtiesForFacility`, `PRMDRExtractPPLTNAddRemovePractitioner`.

**OmniScripts:** `PRM_PDMManualChanges`, `PRM_PDMManualUpdate`, `PRM_PDMManualUpdatePracticeLocation` (+ the QC/review scripts that read these values).

**LWC:** `prmManageRolesTab` (+ `prmLaunchTaxonomyRolesAction`) — the interactive Role editor.

> OmniStudio has many versions per asset; only the version with `<isActive>true</isActive>` is live. Ground every story against the **active** version before build.
