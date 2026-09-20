# Role Change — Entry-Point Analysis & "Role Effective Date" UI Requirement

**Date:** 2026-08-03
**Scope:** Every place a business user can **update / change the Practitioner Role**, and where a new **Role Effective Date** UI field must be captured.
**Companion doc:** [`PatientAcceptStatus_Level4_EffectiveDate_Calculation_Analysis.md`](PatientAcceptStatus_Level4_EffectiveDate_Calculation_Analysis.md) (the calculation pattern we are mirroring).

---

## 1. Where the Role is stored (three objects)

The "Practitioner Role" is **not** a single field on one object — it is duplicated across the hierarchy and kept in sync by the L4 trigger:

| Level | Object | Role field | Effective-date fields available |
|---|---|---|---|
| **L4** Practitioner @ Practice Location Taxonomy & Network | `HealthcareFacilityNetwork` (RT `PRM_FacilityPractitionerTxNw`) | `PRM_PractitionerRole__c` | `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c` (+ `...Calculated__c` formulas) **and** `EffectiveFrom` / `EffectiveTo` (network) |
| **PPL** Practitioner–Practice-Location affiliation | `HealthcarePractitionerFacility` (RT `PRM_PractitionerLocationAffiliation`) | `PRM_PractitionerRole__c` | `EffectiveFrom` / `EffectiveTo` (affiliation) — **no** dedicated Role effective fields |
| **PL** Practice Location | `HealthcareFacility` | practitioner role (rolled up) | — |

**Sync path (not a UI):** `PRM_HCFacilityNetworkTriggerHandler` → `PRM_HCFacilityNetworkTriggerHelper.setPracRoleOnPLAndPPL(...)` propagates the role from an L4 HCFN row down to the PL and PPL records whenever the L4 role or active flag changes.

> **Key finding #1 — the dedicated Role effective fields (`PRM_RoleEffectiveFrom__c` / `...To__c` + `...Calculated__c`) exist only on L4 `HealthcareFacilityNetwork`.** The PPL affiliation and every legacy role-change flow use the record's generic `EffectiveFrom` / `EffectiveTo` instead. The `PRM_RoleEffectiveFromCalculated__c` / `...ToCalculated__c` formulas already fall back to the L4 network `EffectiveFrom` / `EffectiveTo` when the stamped value is blank.

---

## 2. All business entry points that can change the Role

| # | Business UI / process | Persona | Component chain | Role written to | **Role effective date captured on the UI today?** |
|---|---|---|---|---|---|
| **E1** | **Manage Roles tab** (Provider Action Center → *Manage Taxonomy & Roles*) | PDA / PDM Specialist | LWC `prmManageRolesTab` (parent `prmLaunchTaxonomyRolesAction`) → `PRM_ManageRolesController` → `PRM_ManageRolesControllerHelper` | **L4 HCFN** `PRM_PractitionerRole__c` | ✅ **Yes** — the Edit/New modal has **"Role Effective From"** and **"Role Effective To"** date pickers writing `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c`. *Only pending rows are editable; active rows are read-only.* |
| **E2** | **Off-Cycle Credentialing** flow | Credentialing / Network QC | OmniScript `PRM_OffCycleCredentialing_English_*` → IP `PRM_CheckRoleChangeDataParent` → `PRM_CheckRoleChangeData` → DRs `PRMTransNewPracFacOffCycle`, `PRMTransOldPracFacOffCycle`, `PRMTransformOffCycleLocations` → load DR `PRMLoadPractitionerFacRoleChange` | **PPL** `HealthcarePractitionerFacility.PRM_PractitionerRole__c` (+ trigger cascade) | ❌ **No** — the new/old role records inherit the affiliation `EffectiveFrom` / `EffectiveTo`; there is no separate Role-effective input. Uses **terminate-old + create-new**. |
| **E3** | **Off-Cycle QC / PDA Review** | Network Management QC / PDA | OmniScripts `PRM_OffCycleQCReview_English_*` → IPs `PRM_OffCycleRecordUpdatesQCReview`, `PRM_OffCycleRecordUpdatesPDAReview`, `PRM_OffCycleRecordsUpdate(Helper)` | PPL + L4 HCFN | ❌ **No** |
| **E4** | **Role change during Intake** (initial cred / provider screen) | Credentialing Specialist | DR `PRMTransRoleChangeDuringIntake` (builds `NewRole` + `OldRole` JSON) → practitioner-screen creation IPs | L4 (Facility-Practitioner-TxNw) + PPL | ❌ **No** — `NewRole:EffectiveFromDate` / `OldRole:EffectiveToDate` are taken from existing record dates, not a Role-specific UI field. Uses **terminate-old + create-new**. |
| **E5** | **PDM Manual Update / Manual Changes** | PDM Specialist / PDA | OmniScripts `PRM_PDMManualChanges_English_*`, `PRM_PDMManualUpdate_English_*` (steps `PractitionerRole`, `PLPPractitionerRole`, `TaxonomyPractitionerRole`) → IP `PRM_ManualChangePDAUpdates` → DRs `PRMTransRoleChangeTables`, `PRMTransPracFacRoleChange`, `PRMLoadPractitionerFacRoleChange` | PPL + L4 HCFN | ❌ **No** — `NewRoleTable` / `PrevRoleTable` reuse `EffectiveFrom` / `EffectiveTo` (and `Current_EffectiveFrom/To`); no dedicated Role effective date. Uses **terminate-old + create-new**. |
| **E6** | **ReCred QC review** (role adjusted during recredentialing) | Credentialing / QC | DRs `PRMTransformRecredQCSetValues*`, `PRMFetchRecredUpdateData` | L4 HCFN + PPL | ❌ **No** |

> **Key finding #2 — E1 (Manage Roles tab) is the *only* channel that already captures a Role Effective Date and writes it to the dedicated `PRM_RoleEffectiveFrom__c` / `...To__c` fields.** Every other role-change channel (E2–E6) silently reuses the record's network/affiliation `EffectiveFrom` / `EffectiveTo` and writes role to the **PPL** object, never touching the L4 Role effective fields.
>
> **Key finding #3 — the common persistence pattern for E2/E4/E5 is "terminate old role row + create new role row"** (a `PrevRole`/`OldRole` + `NewRole` pair), which is exactly the insert-new/terminate-old model the Patient Accept Status flows use. A captured Role Effective Date would stamp the **new** row's start and the **old** row's end.

---

## 3. The gap & the "Role Effective Date" requirement

**Goal:** give business a UI field to explicitly capture *when a role change takes effect* (and, where relevant, when it ends), instead of implicitly inheriting the network/affiliation dates.

**What already exists (reuse, don't rebuild):**
- L4 fields `PRM_RoleEffectiveFrom__c` / `PRM_RoleEffectiveTo__c` (writable) and `PRM_RoleEffectiveFromCalculated__c` / `PRM_RoleEffectiveToCalculated__c` (formula fallback to network dates).
- The Manage Roles tab modal already renders the two date pickers and persists them via `PRM_ManageRolesControllerHelper.buildEditRow` / `buildCreateRow`.

**Where the new UI field must be added (E2–E6):**
- **Off-Cycle Credentialing (E2)** and **QC/PDA Review (E3)** — add a **Role Effective From** (and optionally To) input on the role-change step; stamp it onto the new role record and the old row's end date.
- **Intake role change (E4)** — surface a Role Effective From on the role-change UI so `NewRole:EffectiveFromDate` comes from user input rather than the record default.
- **PDM Manual Update (E5)** — add the field to the `PractitionerRole` / `PLPPractitionerRole` steps; feed `PRMTransRoleChangeTables` / `PRMLoadPractitionerFacRoleChange`.

**Backing fields — decision required (see §4):** either (a) write the captured date to the L4 `PRM_RoleEffectiveFrom__c` / `...To__c` (consistent with E1, gives the `...Calculated__c` formulas meaning), or (b) continue writing the PPL affiliation `EffectiveFrom` / `EffectiveTo`, or (c) both. Today E1 diverges from E2–E6 on this exact point.

---

## 4. Open questions to lock before building

1. **Source-of-truth object.** Role sits on both L4 HCFN and PPL. Should the new Role Effective Date write the **L4** `PRM_RoleEffectiveFrom__c` / `...To__c` (like Manage Roles) or the **PPL** `EffectiveFrom` / `EffectiveTo` (like Off-Cycle/Intake/Manual)? Recommend standardizing on the L4 dedicated fields and letting the trigger cascade, so `...Calculated__c` reporting is consistent.
2. **From only, or From + To?** Manage Roles exposes both. E2/E4/E5 model role change as terminate-old + create-new — is the "To" the old row's end (system-derived) or also user-entered?
3. **Future-dating.** Should a future Role Effective From defer activation (via Future Dated Processing, like Patient Accept Status), or take effect immediately? Patient Accept Status has a documented single-window future-dating gap — the same constraint applies here.
4. **Validation.** Overlap/gap rules across successive role windows (mirror `PRMTransformNewPanelStatus` / `PRMTransformOldPanelStatus`)? Must Role Effective From be ≥ network Effective From?
5. **Active-row edits.** Manage Roles only allows editing *pending* rows. Do the other channels allow dating a role change on an already-active row?
6. **Backfill / parity.** Existing rows have blank `PRM_RoleEffectiveFrom__c` (so `...Calculated__c` = network date). Any need to backfill?

---

## 5. Component inventory (role-change specific)

**LWC / UI:** `prmManageRolesTab`, `prmLaunchTaxonomyRolesAction`, `prmManageAdmittingPrivilegesTab` (adjacent), `prmGenericButtonLauncher`.
**Apex:** `PRM_ManageRolesController`, `PRM_ManageRolesControllerHelper`, `PRM_HCFacilityNetworkTriggerHelper` (`setPracRoleOnPLAndPPL`, cascade).
**OmniScripts:** `PRM_OffCycleCredentialing_English_*`, `PRM_OffCycleQCReview_English_*`, `PRM_PDMManualChanges_English_*`, `PRM_PDMManualUpdate_English_*`.
**Integration Procedures:** `PRM_CheckRoleChangeDataParent`, `PRM_CheckRoleChangeData`, `PRM_OffCycleRecordUpdatesQCReview`, `PRM_OffCycleRecordUpdatesPDAReview`, `PRM_OffCycleRecordsUpdate(Helper)`, `PRM_ManualChangePDAUpdates`, `PRM_FetchOffCycleDetails`.
**DataRaptors:** `PRMTransRoleChangeDuringIntake`, `PRMTransNewPracFacOffCycle`, `PRMTransOldPracFacOffCycle`, `PRMTransformOffCycleLocations`, `PRMTransRoleChangeTables`, `PRMTransPracFacRoleChange`, `PRMLoadPractitionerFacRoleChange`.

> Ground each against the **active** OmniStudio version (`<isActive>true</isActive>`) before build; many versions exist per asset.
