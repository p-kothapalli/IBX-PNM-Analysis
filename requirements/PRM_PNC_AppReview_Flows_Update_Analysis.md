# PNC Migration — PAR Form & Application-Review Guided Flows: What to Update

**Date:** 2026-07-10
**Scope:** End-to-end **PAR (Practitioner Add Request) form** PNC guided flow + the **application-review / approval** guided flows: **PNC Review → Sent to PDA (Provider Data Admin) → NMQC (Network Management QC)**.
**Companion docs:** `PRM_PNC_Logic_Change_Implementation_Plan.md` (US3 = PAR intake, US4 = RCAT/rollup helpers, US5 = HealthcareFacility trigger, US5B = PPL trigger), `PAR_Form_PNC_Path_User_Stories.md`, `PRM_PNC_Analysis.md`.
**User stories for these changes:** `PRM_PNC_AppReview_Flows_User_Stories.md` (US-AR1 PAR intake · US-AR2 PNC Review/RCAT · US-AR3 Sent to PDA · US-AR4 NMQC regression · US-AR5 ambiguous-`Account` scope).

---

## 0. TL;DR — the two things that actually change

The migration is: **PNC moves from `Account.PRM_PNC__c` (vendor) → `HealthcareFacility.PRM_PNC__c` (practice location)**, and the **practitioner rollup becomes switch-aware** (`Account.PRM_PNCAnyLocation__c`: ALL by default, ANY when checked).

So across every flow below, there are only **two kinds of edits**:

1. **Re-point the PNC read** — anything that reads `Account.PRM_PNC__c` / `Account:PRM_PNC__c` / `HCF:Account.PRM_PNC__c` to describe a **practice location's** PNC must read `HealthcareFacility.PRM_PNC__c` (`HealthcareFacility:PRM_PNC__c` / `hcfRecord.PRM_PNC__c`). Vendor-level PNC reads go away with US11.
2. **Re-point the PNC write + rollup** — anything that writes the **practitioner** `Account.PRM_PNC__c` must compute it from the practitioner's locations using the **switch-aware** rule (reuse `pncOnlyPractitioner` / `updateAccountPNCHelper`, per US4).

### Key finding: routing is NOT PNC-driven

PDA and NMQC routing is controlled by **Set Values** on Case `Type`/`Status` and `IndividualApplication.PRM_Stage__c` (queue `PRM_PDAQueue`, Stage/Type `"PDA Review and Update"` → `"Network Management QC"`), **not** by the PNC field. PNC travels through the review flows as **read-only display / rollup data**. ✅ Verified in `PRM_PNCPDA_English_Element_SetRecordsNtwlMgntQC.json` (sets `PRM_Stage__c`/`Type = "Network Management QC"`, `IsRoundRobinLogic = true`; no PNC field) and `PractitionerPNC.json` (`Type: Checkbox`, `readOnly: true`).

**Implication:** none of these flows need routing/approval-logic changes. The work is entirely **data-source re-pointing + rollup**. NMQC in particular needs **no field change** — only regression.

### Active OmniScript versions (confirm before editing)

| Flow | Active OmniScript |
|------|-------------------|
| PAR intake | `PRM_PractitionerParticipationForm_English` v98 |
| RCAT Review (PNC displays here) | `PRM_ReviewRCAT_English` — note `PRM_PNCReview_English` v8 has **no** PNC |
| Sent to PDA | `PRM_PNCPDA_English` v9 |
| NMQC | `PRM_PNCQC_English` v6 |

> Line numbers below are **indicative** (captured from the design-time export). Always confirm against the active version before editing — OmniStudio keeps every version and only `<isActive>true</isActive>` is live.

---

## 0.1 VERIFIED — where the literal vendor `Account.PRM_PNC__c` actually lives

**Critical mechanic (verified by reading the elements):** the OmniScript **steps do NOT contain a literal `Account.PRM_PNC__c`**. Each step displays a **transformed node** (`pnc`, `PracLocPNC`, `PracLocPNCPL`, `PractitionerPNC`, `PracPNC`) that a **DataRaptor/IP/Apex** populates. So "which step refers to vendor PNC" = *the step is the display; the vendor read is in its DataRaptor/Apex feed*. Fix the feed, and the step is correct.

**How to tell vendor vs practitioner:** in the data model `HealthcareFacility.AccountId` → the **vendor/group** Account. So any read that hops **through a facility/identifier** to `Account.PRM_PNC__c` is the **vendor** value → **change to `HealthcareFacility.PRM_PNC__c`** (drop the `.Account` hop). A read of the **person/practitioner** Account's own `PRM_PNC__c` is the **rollup** → **stays** (only the computed value changes, per US4/US5/US5B).

### CHANGE these — vendor PNC read via facility/identifier → `HealthcareFacility.PRM_PNC__c`

| DataRaptor | Line | Current `InputFieldName` / formula | Change to | Flow |
|---|---|---|---|---|
| `PRMDRExtractGroupNameBasedOnTINNPIPNC` | 144 | `Identifier:Account:PRM_PNC__c` | location `PRM_PNC__c` | **A · PAR** |
| `PRMDRExtractGroupNameBasedOnTINNPI` | 144 | `Identifier:Account:PRM_PNC__c` | location `PRM_PNC__c` | **A · PAR** |
| `PRMExtractGroupNameByTIN` | 144 | `Identifier:Account:PRM_PNC__c` | location `PRM_PNC__c` | **A · PAR** |
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview` | 28, 113 | FILTER `... Account.PRM_PNC__c == false ...` (both affiliation RTs) + output `...HealthcarePractitionerFacility:Account.PRM_PNC__c` | Location branch → `HealthcareFacility.PRM_PNC__c`; retire the `PRM_PractitionerPracticeAffiliation` (vendor) branch | **B · PNC Review** |
| `PRMGetPLVendorPNCRCAT` | 4 | `IF(%...IsVendorPNC%, ..., IF(%...HCF:Account.PRM_PNC__c% == true,...))` | `HCF:PRM_PNC__c` | **B · PNC Review (Step 2 LMS)** |
| `PRMGetRelatedRecordForRCATReview` | 725 | `CaseManagers:PractionerPracticeLocation:Account.PRM_PNC__c` → `PracPNC` | `...PractionerPracticeLocation:HealthcareFacility.PRM_PNC__c` (or the location's own PNC) | **B · PNC Review** |
| `PRMDRGetFacilityInfoDelegatedPNCReCred` | 4 | `%HCF:Account.PRM_PNC__c%` | `%HCF:PRM_PNC__c%` | **B · Recred/review** |
| `PRMExtractCaseDetails` | 1424 | `Case:Account.PRM_PNC__c` | Confirm scope (see below) | **B · review** |
| `PRMDRExtractVendorPracticeLocations` | 1086 | `Facility:Account.PRM_PNC__c` → `Facility:PracLocPNC` | `Facility:PRM_PNC__c` | PDM/Provider |
| `PRMFetchVendorAndHCFWithNPI` | 1160 | `Facility:Account.PRM_PNC__c` → `Facility:PracLocPNC` | `Facility:PRM_PNC__c` | PDM/search |
| `PRMExtractLocationsforHCPNPI` | 1283 | `HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c` → `Location:PracLocPNC` | `HealthcarePractitionerFacility:HealthcareFacility.PRM_PNC__c` | search/loc |
| `PRMDRGetLocationTerminationData` | 877 | `HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c` | `...HealthcareFacility.PRM_PNC__c` | termination |
| `PRMExtractPracticeLocationsPARChange` | 926 | `Facility:Account.PRM_PNC__c` | `Facility:PRM_PNC__c` | PAR change |
| `PRMExtractPracticeLocationsProvChange` | 972 | `Facility:Account.PRM_PNC__c` | `Facility:PRM_PNC__c` | Provider change |
| `PRMExtractPracticeLocationsAncillaryChange` | 949 | `Facility:Account.PRM_PNC__c` | `Facility:PRM_PNC__c` | Ancillary |
| `PRMFetchVendorAccWithTaxId` / `...WithTaxIdAndBillingZip` / `PRMFetchVendorAndHCFWithTaxID` | ~77/101/149 | `FormulaResultPath: PracLocPNC` (built from vendor) | Base `PracLocPNC` on `HealthcareFacility.PRM_PNC__c` | PDM/search |

### DO NOT change — practitioner rollup reads/writes (`Account` = person account) → value comes from the new rollup

| DataRaptor / IP | Line | Reference | Why it stays |
|---|---|---|---|
| `PRMGetRelatedRecordForPractitioner` | 761 | `CaseManagers:Account.PRM_PNC__c` | Practitioner's own rollup PNC (display) |
| `PRM_FetchPractitionerDemographics` → `DRGetAccountFromCaseAccountId` (`PRMGetAccountFromCaseAccountId`) | Response `PractitionerData:PNC = Account\|1:PRM_PNC__c` | Person account (same node yields `FirstName`/`PersonBirthdate`/`PersonEmail`) — the practitioner rollup |
| `PRMDRCreateCaseCaseManagerAndAccount` (528, 992), `PRMDRCreateCaseCaseManagerExistingNPI` (389) | write `PRM_PNC__c` | Writes the **practitioner** Account rollup + CM record type; keep target, compute value switch-aware (US3/US4) |
| `PRMDRUpdateAccountPDM` / `PRMDRUpdateAccountReviewPDM` / `PRMDRUpdatePNCCase` | write `PRM_PNC__c` | Practitioner rollup write; value from US4 |
| `PRMDRSearchBasedOnAccount` (77, 188), `PRMDRSearchBasedOnNPITINAccount` (101, 234) | `Account:PRM_PNC__c` | **Confirm** — search DRs; if the Account is the group/vendor, change; if practitioner, stays |

### Confirm-scope (ambiguous `Account`)
- `PRMExtractCaseDetails:1424 Case:Account.PRM_PNC__c` — for a **practitioner** case this is the practitioner rollup (stays); if ever used for a group/vendor case, change. Confirm the case type.
- `PRMDRSearchBasedOnAccount` / `PRMDRSearchBasedOnNPITINAccount` — confirm whether `Account` is vendor or practitioner in each usage.

---

## Flow A — PAR Form Intake (`PRM_PractitionerParticipationForm_English`)

**What PNC means here:** at intake the practitioner's PNC is derived from the **group(s)/location(s)** they are joining, then written to the practitioner Account + drives the Case Manager (`IndividualApplication`) record type. This is **US3** in the implementation plan — this section is the flow-level view.

### A.0 Verified OmniScript step chain (where PNC flows through the form)

| Step / element | Type | What it does | Vendor read? |
|---|---|---|---|
| `PractionerGroup` step → `PractitionerParticipationQuestion5` | Radio | "Is the Practitioner joining a PNC Group?" (user intent) | No (intent only) |
| `IsPNCGroup` | Formula | `IF(Q5=="Yes",true,false)` → `IsPNC` | No |
| `GroupTypeAhead` → `IPExtractGroupName` | IP Action | Calls `PRM_IPExtractGroupNameBasedOnTINNPI` with `{IsPNC, NPI, TaxId}`; response node `Account` → `GroupInformation` | **Indirect** — the IP/Apex/DR behind it reads vendor `Account.PRM_PNC__c` |
| `GroupInformation` block → **`pnc`** | Formula | `IF(GroupInformation.ExistingGroupSelected==false, false, %GroupInformation.pnc%)` — **this is the step that consumes the group PNC value** | **Indirect** — `GroupInformation.pnc` is populated from the vendor group's `Account.PRM_PNC__c` (via the IP → `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI` / `PRMDRExtractGroupNameBasedOnTINNPIPNC`) |
| `MSG_PNCGroup` / `SetErrorNonPNCGroup` / `CredentialingStatus` / `SetErrorsCredentialingStatus` | Msg / Set Errors | PNC-intent gating & credentialed-path warnings | No literal field; keyed off `pnc`/intent |

**So in PAR, the "step referring to vendor PNC" is the `GroupInformation.pnc` formula — but the literal `Account.PRM_PNC__c` read is in `PRM_IPExtractGroupNameBasedOnTINNPI` (Apex `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI`) and the group DataRaptors (`PRMDRExtractGroupNameBasedOnTINNPIPNC:144`, `PRMDRExtractGroupNameBasedOnTINNPI:144`, `PRMExtractGroupNameByTIN:144`).** Re-point those to the practice location's `HealthcareFacility.PRM_PNC__c` and apply the ALL/ANY switch (US3/US4).

### A.1 What to update

| Component | Type | Current | Change |
|-----------|------|---------|--------|
| `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI` / `getAccountWrapperData` | Apex | Puts `PNC` from group `Account.PRM_PNC__c` for the type-ahead | Source PNC from the **practice location** (`HealthcareFacility.PRM_PNC__c`) for the selected location(s); this is the primary PAR Apex change |
| `PRM_PARProviderSearch.cls` (125, 309) | Apex | `outMap.put('PNC', groupAccount.PRM_PNC__c)`; `provDetails.PNC = grpAccount.PRM_PNC__c` | Re-point to location PNC |
| `PRM_ValidateNPIs.cls` (132–133, 280–281) | Apex | `isPNCGroup` payload flag | Confirm the flag reflects location PNC / intent, not vendor PNC |
| `PRMDRExtractGroupNameBasedOnTINNPIPNC_Items.json` (144, 464, 664) | DataRaptor | `Identifier:Account:PRM_PNC__c` | Re-point to `HealthcareFacility.PRM_PNC__c` for the location |
| `PRMDRExtractGroupNameBasedOnTINNPI_Items.json` (144), `PRMExtractGroupNameByTIN_Items.json` (144) | DataRaptor | `Identifier:Account:PRM_PNC__c` | Same |
| `PRMDRCreateCaseCaseManagerAndAccount_Items.json` (528, 992), `PRMDRCreateCaseCaseManagerExistingNPI_Items.json` (389) | DataRaptor | `OutputFieldName: PRM_PNC__c` (writes practitioner PNC + CM record type) | **Keep writing practitioner `Account.PRM_PNC__c`**, but the value must be the **switch-aware rollup** computed from the joined locations (US3/US4). No structural change to the write target (practitioner Account) — only the computed value. |
| `PRMDRExtractExistingNPIInfo_Items.json` (341), `PRMDRExtractHealthCareProviderNPIWith*_Items.json`, `PRMDRExtractHealthCareProviderNpiRecords_Items.json` (539) | DataRaptor | `Account:PRM_PNC__c` (existing-NPI / credentialed path) | Re-point to location PNC where the value describes a location |
| `IsPNCGroup` / `pnc` formula / `Q5` / `MSG_PNCGroup` / `SetErrorNonPNCGroup` / `CredentialingStatus` elements | OmniScript | User intent + group PNC gating | Retarget the `pnc` source to practice-location PNC; retain ALL-default semantics; honor `PRM_PNCAnyLocation__c` when the practitioner exists (US3 AC1/AC5). Fix the known `MSG_PNCGroup`/`SetErrorNonPNCGroup` gaps noted in `PAR_Form_PNC_Path_User_Stories.md`. |
| `PRM_IPExtractGroupNameBasedOnTINNPI` (IP), `PRM_PractitionerScreenRecordCreation` (`SV_PNCFlag`/`PNCFlag`) | IP | Group-based `IsPNC`/PNCFlag derivation | Retarget the underlying data to location PNC; PNCFlag stays "true only if all joined locations PNC" unless switch = ANY |

**Net for PAR intake:** the practitioner PNC *write* stays on the practitioner Account (correct), but every *source* that today reads group/vendor `Account.PRM_PNC__c` to decide it must read location PNC and apply the ALL/ANY switch. Covered by **US3 + US4**.

---

## Flow B — RCAT Review (`PRM_ReviewRCAT_English`; `PRM_PNCReview_English` v8 = no PNC)

**What PNC means here:** the reviewer sees each practitioner/location's PNC status (read-only) to decide the RCAT/termination outcome, then routes to **PDA** (or "Provider Outreach Needed"). PNC here is **display + rollup** data. Core logic is **US4** (RCAT helpers) with display feeds via DataRaptors.

> **OmniScript layer — verified, no field edit:** `PRM_PNCReview_English` contains **zero** PNC references (no `PRM_PNC__c`, no `pnc`/`PracLocPNC`/`PractitionerPNC` node) — it only runs review/routing IPs. The PNC display lives in the **separate** `PRM_ReviewRCAT_English` OmniScript, whose `PNC` / `LMSPNC` / `PNCAndDelegated` elements are **read-only display checkboxes bound to transformed JSON nodes**, not to `Account.PRM_PNC__c`. Those nodes are produced by the DataRaptors below, invoked by IPs `PRM_ReviewRCAT` (via `PRMGetRelatedRecordForRCATReview`) and `PRM_UpdateDataForRCATPNCReview` (via `PRMGetRelatedDataforPNCAndDelegatedRCATReview`). **All re-point work is in the DataRaptors/IPs — neither OmniScript changes.**
>
> **Verify caller first:** `PRMGetPLVendorPNCRCAT` and `PRMDRGetFacilityInfoDelegatedPNCReCred` read vendor PNC but have **no confirmed live caller** in the export (found only in their own DataPacks). Classify as active/orphaned (US-AR5 gate) before editing.

### B.1 Routing (no change)

- `PRM_PNCReview_English_Element_SVRecordsToUpdatePDA.json` → sets `PRM_Stage__c = "PDA Review and Update"`, `OwnerName = "PRM_PDAQueue"`, `Type = "PDA Review and Update"` when `ProceedTo == "PDA"`. **No PNC field — leave as is.**
- `..._Element_SVRecordsToUpdatePORNeeded.json` → "Provider Outreach Needed" path. **No PNC field — leave as is.**
- `..._Element_IPPNCRecordsUpdate.json` → `PRM_PNCRecordsUpdateParent`. Persists outcome; verify it does not write vendor PNC.

### B.2 What to update (display + rollup source)

| Component | Type | Line(s) | Current → Change |
|-----------|------|---------|------------------|
| `PRMGetRelatedDataforPNCAndDelegatedRCATReview_Items.json` | DataRaptor | 28, 99, 113 | Filter `Account.PRM_PNC__c == false` for both `PRM_PractitionerPracticeAffiliation` **and** `PRM_PractitionerLocationAffiliation`; In/Out `...Filtered:Account.PRM_PNC__c`. **→** Location branch uses `HealthcareFacility.PRM_PNC__c`; migrate/retire the Practice-Affiliation (vendor) branch. (Also covered in US4 AC4.) |
| `PRMGetPLVendorPNCRCAT_Items.json` ⚠️ | DataRaptor | 4 | `IF(...HCF:Account.PRM_PNC__c == true...)` **→** `HCF:PRM_PNC__c` — **only if active (US-AR5 gate; no exported caller found)** |
| `PRMGetRelatedRecordForRCATReview_Items.json` | DataRaptor | 725 | `CaseManagers:PractionerPracticeLocation:Account.PRM_PNC__c → PracPNC` **→** location PNC |
| `PRMGetRelatedRecordForPractitioner_Items.json` | DataRaptor | 761 | `CaseManagers:Account.PRM_PNC__c` **→** re-point |
| `PRMDRGetFacilityInfoDelegatedPNCReCred_Items.json` ⚠️ | DataRaptor | 4 | `%HCF:Account.PRM_PNC__c%` **→** `%HCF:PRM_PNC__c%` — **only if active (US-AR5 gate; no exported caller found)** |
| `PRMExtractCaseDetails_Items.json` | DataRaptor | 1424 | `Case:Account.PRM_PNC__c` **→** re-point if location-scoped |
| `PRMDRLoadNPITaxHCFNPNC_Items.json` | DataRaptor | 828 | `OutputFieldName: PRM_PNC__c` **→** confirm write target |
| `PRM_RecredTerminationLetter` → `..._Element_FilterHCPFRecords.json` | IP | 16 | Filter `'Account:PRM_PNC__c != true'` **→** `'HealthcareFacility:PRM_PNC__c != true'` (exclude PNC locations from termination letter) |
| `PRM_ReviewRCAT_English` CustomLWC1/2/3 (Steps 1–3) | LWC | — | Consume PNC from the updated DataRaptor/Apex payload (`pnc`/`PracLoc.pnc`); no hardcoded field path — driven by the DRs/Apex above (US4 AC4) |
| `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` | Apex | 718/726/728/735 vs 764 | ALL-logic on `PRM_PractitionerPracticeAffiliation` + `Account.PRM_PNC__c`; already has a `PRM_PractitionerLocationAffiliation` branch. **→** switch to location source + make switch-aware (US4 AC1) |
| `PRM_RCATProcessingHelper.cls` | Apex | ~133–135 (`loc.pnc`), SOQL ~69 | `loc.pnc` from `HealthcareFacility.Account.PRM_PNC__c` **→** `HealthcareFacility.PRM_PNC__c` (Step-2 LMS PNC) |
| `PRM_RCATProcessingController.cls` | Apex | 51, 61, 71 | `isPNCDelegated` filters — verify source |
| `PRM_FetchPractTermDataHandler.cls` | Apex | 145, 214 | `PNC = npiData.Account.PRM_PNC__c` **→** location PNC |

---

## Flow C — Sent to PDA (`PRM_PNCPDA_English` v9)

**What PNC means here:** the PDA reviewer sees a **read-only PNC checkbox** per practitioner (verified: `PractitionerPNC.json` `Checkbox`, `readOnly: true`), reviews, and routes to **NMQC** / Rebuttal / Pended / Return-to-PDA. On processing, the PDA batch can **set the practitioner PNC**. Launched from Case button `PRM_PNCPDA.webLink`.

### ✅ Verified correction — the PDA `PractitionerPNC` checkbox is the PRACTITIONER ROLLUP, not a vendor read

- The PDA screen loads via `IPFetchFormFormPDA` → **`PRM_FetchFormPDAReviewParent`**, which — grep-verified — contains **no PNC reference at all**. Its transform `DRTransformPDAReview` (`PRMTransInitialPDAReview`) also has none.
- `PractitionerPNC` is a **practitioner-level** display (under the `PractitionerInfoCodes` block, keyed by practitioner). Where a PNC value is sourced elsewhere in PDA/demographics it comes from the **person Account** (`DRGetAccountFromCaseAccountId:Account|1:PRM_PNC__c` — the same node that yields `FirstName`/`PersonBirthdate`/`PersonEmail`), i.e., the **rollup**, not a vendor account.
- **Conclusion:** there is **no vendor `Account.PRM_PNC__c` to re-point inside the PDA OmniScript/fetch.** The checkbox is correct automatically once the practitioner rollup is fixed upstream (US4/US5/US5B). The only PDA **Apex** changes are (a) the PPL wrapper feed `PRM_IPUtilityHelper` (vendor-via-facility, verified) and (b) the PDA write helper computing the rollup value.

### C.1 Routing (no change)

`PDAReviewOutcome` drives Set Values elements: `SetRecordsNtwlMgntQC` (→ NMQC), `SetRecordsRebuttal`, `SetRecordsErrorsResolved`, `SetRecordsPended`, `QCReturnToPDA`. **None set a PNC field — leave as is.**

### C.2 What to update

| Component | Type | Line(s) | Current → Change |
|-----------|------|---------|------------------|
| `PractitionerPNC.json` (read-only checkbox) | OmniScript | 4/28/38 | **No change.** Practitioner-rollup display; correct once rollup fixed upstream |
| `PRM_FetchFormPDAReviewParent` / `PRM_FetchFormPDAReview_Procedure` / `DRTransformPDAReview` | IP/DR | — | **No PNC reference (verified). No change.** |
| `PRM_IPUtilityHelper.cls` | Apex | **153** `facWrapper.PracLocPNC = hcfRecord.Account.PRM_PNC__c;`; **262** SOQL `account.PRM_PNC__c` on `HealthcareFacility` | ✅ Verified vendor-via-facility. **→** `hcfRecord.PRM_PNC__c`; SOQL selects `HealthcareFacility.PRM_PNC__c` directly. Feeds the PPL/network table (`PracLocPNC`) shown in PDA/QC — high value. |
| `PRM_PNCPDABatchHelper.cls` | Apex | 209 (SOQL), **229** `acc.PRM_PNC__c = true;`, 249 (SOQL) | Sets **practitioner** PNC on PDA processing. **→** compute the value via the switch-aware rollup (US4) rather than unconditionally |
| `PRM_PNCPDAService.cls` / `PRM_PNCPDABatch.cls` / `PRM_PNCPDAUtility.cls` | Apex | — | Audit for `Account.PRM_PNC__c`; keep practitioner-rollup writes, re-point any vendor-via-facility read |
| `PRMDRUpdateAccountReviewPDM_Items.json` (341), `PRMDRUpdateAccountPDM_Items.json` (152), `PRMDRUpdatePNCCase_Items.json` (88, 155) | DataRaptor | write `PRM_PNC__c` | Practitioner rollup **write** — keep target, value from US4 |
| `PRMDRExtractPDMAccountDetails_Items.json` (269, 283), `PRMDRExtractAccountDetails_Items.json` (74) | DataRaptor | read `Account:PRM_PNC__c` | Confirm scope (practitioner vs vendor) — re-point only vendor-via-facility reads |

**Net for PDA:** no OmniScript step re-point; the only substantive changes are the two Apex items (`PRM_IPUtilityHelper` verified, `PRM_PNCPDABatchHelper`) and re-pointing any vendor-via-facility DR reads used to build the PPL/network table.

---

## Flow D — NMQC / Network Management QC (`PRM_PNCQC_English` v6)

**What PNC means here:** QC reviews the same practitioner/location data (carried through as display) and routes onward. Reached when PDA outcome = **"Proceed to Network Management QC"**.

### D.1 What to update

- **Routing:** `PRM_PNCQC_English_Element_SetRecordsNtwlMgntQC.json` and the InitialCred analog — Stage/Type-based, **no PNC field. No change.**
- **NMQC worklist Apex** `PRM_FetchRecordsForNMQC.cls` / `PRM_FetchRecordsForNMQCProviderSearch.cls` — filter by Case Type/Stage `"Network Management QC"`, **no direct `PRM_PNC__c` reference.** **No field change.**
- **Display carry-through:** `PRM_PNCQC_English` has the same `PractitionerPNC` read-only checkbox and loads via the same `IPFetchFormFormPDA` → `PRM_FetchFormPDAReviewParent` (no PNC reference — verified). So the QC `PractitionerPNC` is the **practitioner rollup**, identical to PDA — **no vendor `Account.PRM_PNC__c` to re-point.** The PPL/network table PNC (`PracLocPNC`) is fed by `PRM_IPUtilityHelper` (fixed in Flow C).

**Net for NMQC: regression-test only.** No OmniScript/field-migration change; the QC screens inherit corrected PNC once the Flow B (review DRs) and Flow C (`PRM_IPUtilityHelper`) feeds are re-pointed and the rollup (US4/US5/US5B) is correct.

---

## 1. Consolidated change checklist (by artifact type)

### DataRaptors — re-point `Account.PRM_PNC__c` → `HealthcareFacility.PRM_PNC__c` (location-scoped reads)
- PAR: `PRMDRExtractGroupNameBasedOnTINNPIPNC`, `PRMDRExtractGroupNameBasedOnTINNPI`, `PRMExtractGroupNameByTIN`, `PRMDRExtractExistingNPIInfo`, `PRMDRExtractHealthCareProviderNPIWith*`, `PRMDRExtractHealthCareProviderNpiRecords`
- Review: `PRMGetRelatedDataforPNCAndDelegatedRCATReview`, `PRMGetPLVendorPNCRCAT`, `PRMGetRelatedRecordForRCATReview`, `PRMGetRelatedRecordForPractitioner`, `PRMDRGetFacilityInfoDelegatedPNCReCred`, `PRMExtractCaseDetails`
- PDA: `PRMGetAccountFromCaseAccountId`, `PRMDRExtractPDMAccountDetails`, `PRMDRExtractAccountDetails`, `PRMDRExtractFetchCaseManagerDetails`
- Write DRs (keep practitioner-Account target; value = switch-aware rollup): `PRMDRCreateCaseCaseManagerAndAccount`, `PRMDRCreateCaseCaseManagerExistingNPI`, `PRMDRUpdateAccountReviewPDM`, `PRMDRUpdateAccountPDM`, `PRMDRUpdatePNCCase`, `PRMDRLoadNPITaxHCFNPNC`

### Integration Procedures
- `PRM_RecredTerminationLetter / FilterHCPFRecords` (16): `Account:PRM_PNC__c` → `HealthcareFacility:PRM_PNC__c`
- `PRM_FetchPractitionerDemographics` ResponseAction (24): feed PNC from location/rollup
- `PRM_FetchFormPDAReview_Procedure` / `PRM_InitialCredPDAReviewUpdateSubIPInsert`: audit + re-point
- `PRM_IPExtractGroupNameBasedOnTINNPI`, `PRM_PractitionerScreenRecordCreation` (`SV_PNCFlag`/`PNCFlag`): retarget source (US3)

### OmniScripts (element-level)
- PAR: `IsPNCGroup`, `pnc` formula, `Q5`, `MSG_PNCGroup`, `SetErrorNonPNCGroup`, `CredentialingStatus` (retarget to location PNC; fix known validation gaps)
- Review/PDA/QC: **no routing changes**; read-only PNC displays inherit corrected feeds

### Apex (rollup + feeds) — reuse switch-aware helpers, re-point location reads
- `PRM_RecordQueryServiceUtils` (PAR group→location source)
- `PRM_PARProviderSearch` (125, 309), `PRM_ValidateNPIs` (132–133, 280–281)
- `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` (US4), `PRM_RCATProcessingHelper` (loc.pnc), `PRM_RCATProcessingController`
- `PRM_FutureDatedProcessingBatchHandler` (816/821 + rollup), `PRM_CommonUtils.updateAccountPNCHelper`/`getPIdToHCPFList` (US4)
- `PRM_IPUtilityHelper` (153, 262 — verified), `PRM_PNCPDABatchHelper` (229), `PRM_PNCPDAService`/`Batch`/`Utility`, `PRM_PDMDataHelper` (350, 361), `PRM_FetchPractTermDataHandler` (145, 214)
- Triggers: `PRM_AccountTriggerHelper` (US5 §5.1a + deprecate vendor), `PRM_PracFacilityTriggerHandler` (US5B)

### LWC
- `PRM_ReviewRCAT_English` CustomLWC1/2/3 — verify they render PNC from the re-pointed payload (no code change expected if payload keys unchanged)

### No change (regression only)
- All PDA/QC/Review **routing** Set Values (`PRM_PDAQueue`, Stage/Type, round-robin)
- `PRM_FetchRecordsForNMQC*` (Type/Stage-based worklist)

---

## 2. Open questions / clarifications

1. **Vendor-PNC reads during transition:** several DRs read `Identifier:Account:PRM_PNC__c` where "Account" is the **group/vendor**. Confirm each is truly a *location* concept (re-point) vs a *vendor* concept (retire with US11). A per-DR sign-off is needed (ties to CL-11-style field-map gate).
2. **PDA `PractitionerPNC` semantics:** is the read-only checkbox meant to show the **practitioner rollup** or **the specific reviewed location's** PNC? This decides whether `PRM_FetchPractitionerDemographics` feeds it from the practitioner rollup or from `HealthcareFacility.PRM_PNC__c` of the location under review.
3. **PDA write (`PRM_PNCPDABatchHelper:229` `acc.PRM_PNC__c = true`):** should PDA processing ever *force* practitioner PNC true, or must it always be the computed switch-aware rollup? Recommend the latter for consistency.
4. **RCAT Practice-Affiliation branch:** `PRMGetRelatedDataforPNCAndDelegatedRCATReview` and `pncOnlyPractitioner` still branch on `PRM_PractitionerPracticeAffiliation` (vendor). Confirm this branch is retired (locations only) or retained during transition.

---

## 3. Testing checklist

- [ ] **PAR intake (ALL default):** join locations all PNC → practitioner PNC true, CM record type = PNC; join with one non-PNC location → practitioner PNC false.
- [ ] **PAR intake (ANY switch):** `PRM_PNCAnyLocation__c = true`, join [PNC, non-PNC] → practitioner PNC true.
- [ ] **PNC Review:** RCAT Steps 1–3 display each location's PNC from `HealthcareFacility.PRM_PNC__c`; termination letter excludes PNC locations (`HealthcareFacility:PRM_PNC__c != true`).
- [ ] **Review → PDA routing:** `ProceedTo = PDA` still routes to `PRM_PDAQueue` / Stage "PDA Review and Update".
- [ ] **PDA screen:** read-only PNC checkbox shows the correct (location-sourced) value; PDA processing sets practitioner PNC = switch-aware rollup.
- [ ] **PDA → NMQC routing:** `PDAReviewOutcome = "Proceed to Network Management QC"` sets Stage/Type "Network Management QC", round-robin.
- [ ] **NMQC:** worklist populates by Type/Stage; PNC displayed matches upstream (regression).
- [ ] **Rollup triggers:** location PNC change (US5), practitioner add/remove (US5B), switch change (US5 §5.1a) all recompute practitioner PNC through these flows' data.
