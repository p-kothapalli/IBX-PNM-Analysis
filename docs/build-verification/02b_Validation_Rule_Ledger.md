# 02b — Validation / Eligibility Rule Ledger (Delegated Practitioner Creation)

> Sibling of [`02_Parity_Ledger.md`](02_Parity_Ledger.md). The Parity Ledger answers *"did the right
> records get **created**?"*. **This ledger answers *"did the delivery **reject the right payloads** —
> the eligibility / "must-have" / "can-only" rules — before any DML?"***
>
> It is the ground truth for the **Contract Conformance** agent ([`01_Agent_Catalog.md`](01_Agent_Catalog.md)
> Agent 3) and the validate-first half of the **Branch-Coverage** agent (Agent 2).

---

## 0. Where these rules live today (the critical finding)

The eligibility rules are spread across **three** layers, and **most of them live only in the OmniScript
UI** — which the redesign replaces. That is the central parity risk this ledger exists to manage.

| Layer | What it owns today | Active source | Survives the redesign? |
|-------|--------------------|---------------|------------------------|
| **OmniScript UI** (`Validation`/`Formula` elements) | NPI-exists, already-created, currently-credentialed, group-NPI valid, practice-location-known, networks-selected, ~25 required fields, "one primary degree", date-order | `omniScripts/PRM_PractitionerCreation_English_25.os-meta.xml` (**active**, `isActive=true` at line 5) | **❌ No** — UI-side validations are lost unless ported server-side |
| **Apex remote actions / helper** | Group resolution (NPI+EIN → group account) and the **delegated** practice-location info-code gate | `classes/PRM_PractitionerCreationUtility.cls` (`getGroupData`) → `PRM_PractitionerCreationHelper.cls` (`getUniqueAccountForNPITaxId`, `getPracticeLocation`, `checkDelegatedPracLoc`) | ◐ Partial — logic exists in Apex but is invoked by the OS at runtime, not as a submit-time guard |
| **Apex precheck validator** | Effective-date rules only (fail-fast, pre-DML) | `classes/PRM_PractitionerCreationValidator.cls` (`RA_ValidateSubmit`) | ◐ Partial — exists, but only covers dates |
| **Object triggers / validation rules** | `PRM_EffectiveDateValidation` on HCPF + HFN (the rule the Apex precheck mirrors) | platform validation (referenced in validator header, `PRM_PractitionerCreationValidator.cls:8-12`) | ✅ Yes (DB-level) |

> **The trap.** Because the new model is **validate-first, fire-and-return async** ([`00_Architecture.md`](00_Architecture.md),
> [`03_Plan_Audit_Findings.md`](03_Plan_Audit_Findings.md)), every rule currently enforced **in the
> OmniScript UI must be reproduced in `PractitionerCreationPayloadValidator` (Epic F)** — otherwise an
> invalid payload that the old UI blocked will now be accepted, enqueued, and fail (or worse, partially
> commit) deep in a batch. The legacy Apex validator (`PRM_PractitionerCreationValidator`) **only does
> dates** today, so R-E1…R-E8 below are **net-new server-side obligations**, not a port of existing Apex.

---

## 1. Branch / type gating rules (which path + which records are even eligible)

Verified by **Branch-Coverage** (Agent 2). Source: [`PRM_PractitionerCreationContainer_Process.md`](../reference/PRM_PractitionerCreationContainer_Process.md)
§4 + [`PRM_PractitionerCreation_Hierarchy.md`](../reference/PRM_PractitionerCreation_Hierarchy.md) branch table.

| Rule ID | Rule | Condition / key | Legacy source | New owner |
|---------|------|-----------------|---------------|-----------|
| R-B1 | Branch is chosen by `PractitionerCreationType` — exactly `IBC Professional Staff` or `Delegated Credentialing` | `PractitionerCreationType` | Container v6 `SV_SourceIPDetails` + branch (Process §4.A); Hierarchy "Branch Summary" | Orchestrator / batch branch |
| R-B2 | Location + facility + network + async sub-tree runs **only when `CaseManagerId` is present** | Delegated **and** `CaseManagerId != null` | Process §4.A line 96 (`ExecuteAddressLogic` runs only when delegated CaseManagerId exists); Hierarchy row "Delegated (with CaseManagerId)" | E13–E15 + async (gated in batch) |
| R-B3 | File pipeline (`Identifier` Document RT + `ContentDocumentLink`) runs **only if `FileData` present** | `FileData` non-empty | Process §4.C line 153 | E9 `PRM_FileService` |
| R-B4 | Info-code assignment runs **only if `InfoCodeIds` non-empty** | `InfoCodeIds` non-empty | Process §4.C line 154 | E8 `PRM_InfoCodeService` |
| R-B5 | IBC gets the default info code `C64 (IBC Professional Staff)`; Delegated info codes come from selection | `PractitionerCreation == "IBC Professional Staff"` | OS `DefaultInfoCode` formula (`...English_25.os-meta.xml:3569`) | E8 (branch-aware default) |
| R-B6 | `PersonLanguage` created **only if** languages provided | languages non-empty | Process §4.G (`PersonLanguageBlock` conditional) | E11 `PRM_LanguageService` |

---

## 2. Eligibility / pre-create gates — the "can only / must already / must not exist" rules

**These are the rules the question was about.** All are **hard `Requirement` validations in the active
OmniScript today** (block submit), and **none are in the legacy Apex validator** — so each is a net-new
server-side obligation for `PractitionerCreationPayloadValidator`. Verified by **Contract Conformance**
(Agent 3). Source column cites the active OmniScript element + line.

| Rule ID | Eligibility rule | Trigger (when it must REJECT) | Expected outcome | Legacy source (OmniScript v25 element : line) | New owner |
|---------|------------------|-------------------------------|------------------|-----------------------------------------------|-----------|
| R-E1 | A practitioner that **already exists cannot be re-created** here — reroute to PDM Manual Updates | `IsExistingPractitioner == true` | Block; message "Practitioner selected is already created, please update Practitioner through PDM Manual Updates guided flow." | `ExistingPractitionerErrMsg` (:3686, show rule :3698) | `PractitionerCreationPayloadValidator` |
| R-E2 | A **delegated** practitioner whose **NPI is already associated with a practitioner** cannot be created | `PractitionerCreation == "Delegated Credentialing"` **and** `ExistingNPIPractitioner == true` | Block (hard `Requirement`); "The NPI entered is already associated with a Practitioner, please update Practitioner through PDM Manual Updates guided flow." | `ExistingNPIAssociatedPractitioner` (:3586, validateExpression :3616) | `PractitionerCreationPayloadValidator` |
| R-E3 | A practitioner **currently being credentialed** cannot be created again | `PractitionerCreation == "Delegated Credentialing"` **and** `ExistingHealthPractionerCredentialed == true` | Block; "The Practitioner is currently being Credentialed. Case Manager %ExistingCaseManagerNumber%" | `ExistingNPICredentialed` (:3636, validateExpression :3666) | `PractitionerCreationPayloadValidator` |
| R-E4 | The **group NPI must exist** in the system | `Group:NPIExist == false` and no Tax Id | Block; "The NPI does not exist in the system." | `Messaging1` (:910, validateExpression :915) | `PractitionerCreationPayloadValidator` / E3 `PRM_GroupService` |
| R-E5 | Group NPI **and** Tax Id both not found | `Group:NPIExist == false` and Tax Id provided | Block; "The NPI and TaxId does not exist in the system." | `Messaging5` (:960, validateExpression :990) | `PractitionerCreationPayloadValidator` / E3 |
| R-E6 | Group NPI must be **valid and associated with the named group** | invalid / mismatched group NPI | Block; "Please input a valid Group NPI Number associated with the Group Name provided." | `SetErrors` map (:8066); "Please input a valid Group NPI Number." (:2266) | `PractitionerCreationPayloadValidator` / E3 |
| R-E7 | A practitioner can **only join a *known* practice location** — a typed-in location with no resolved id is flagged | `PracticeLocationName != NULL` **and** `PracticeLocationId == NULL` | Flag (formula `true`) → must resolve to an existing location before submit | `FormulaGroupSpecialtyValdiation` (:856, expression :863) | `PractitionerCreationPayloadValidator` + E13 `PRM_HealthcareFacilityCreationService` |
| R-E8 | **Networks must be selected** before the practitioner can be assigned to a practice location | `SelectedPLNetworks == null` | Block; "Please select networks to proceed." | `ValidateNetwork` formula (:476); `NtwkErrorMsg` text (:304/:309) | `PractitionerCreationPayloadValidator` / E17–E18 |

> R-E7 is the literal answer to *"a practitioner can only join the delegated practice location"*: the UI
> only lets the practitioner affiliate to a location that **resolves to an existing `FacilityId`** (the
> Apex validator's `collectExistingHfIds` then date-checks exactly those resolved ids —
> `PRM_PractitionerCreationValidator.cls:142-163`). A free-typed location with no id is a validation
> flag, not an affiliation.

### 2.1 Resolved condition logic — the DataRaptor lookups behind each flag

The §2 gates fire on boolean flags (`ExistingNPIPractitioner`, `Group:NPIExist`, `PracticeLocationId`,
…). Those flags are **not** in the OmniScript — they are computed by **DataRaptor Extracts + a
Fetch-IP** that the type-aheads/blocks call. This is the actual query logic the new
`PractitionerCreationPayloadValidator` must re-implement in Apex. **All citations are active-version
metadata.** (Note: the lookup DataRaptors carry `<active>false</active>` in the repo snapshot — they are
invoked **by name** from their IPs/type-aheads, so they execute regardless; the active flag governs only
the standalone REST entry point. Confirm against live org before relying on it.)

| Flag (→ rule) | Where computed | Query / filter | Decision formula | Source (file : line) |
|---------------|----------------|----------------|------------------|----------------------|
| `ExistingNPIPractitioner` (→ R-E2) | `PRMDRExtractExistingNPIInfo` | `HealthcareProviderNpi` WHERE `Npi = <input NPI>` AND `NpiType = 'Individual'`; join `Account` WHERE `RecordType.DeveloperName = 'PRM_Practitioner'` on `Account.Id = HCPNpi.AccountId` | `ExistingNPIPractitioner = IF(ISNOTBLANK(HealthCareProviderNpi.PractitionerId), true, false)` | `PRMDRExtractExistingNPIInfo_1.rpt-meta.xml` — NpiType `:219-224`, Npi `:553-558`, Account RT `:33-36`, formula `:536-538` |
| `IsExistingPractitioner` (→ R-E1) | OS formula over the existing-account lookup | resolves an existing Practitioner `Account` via the name/NPI type-ahead (`PractitionerAccId`) | `IF((firstNameBlock.PractitionerAccId == lastNameBlock.PractitionerAccId) && PractitionerAccId != NULL, true, false)` | OS `...English_25.os-meta.xml:8581`; account fields from `PRMDRExtractExistingNPIInfo` `ExistingAccountId` `:48-63` |
| `ExistingHealthPractionerCredentialed` + `ExistingCaseManagerNumber` (→ R-E3) | `PRM_FetchExistingNPIInfo` IP (v14, **active**) consuming the DR's `CredentialingStatus` + NPI `IsActive` | `CredentialingStatus = Account.PRM_CredentialingStatus__c`; `ExistingHealthCareProviderNPIIsActive = HealthcareProviderNpi.IsActive`; `ExistingCaseManagerNumber = HCPNpi.PRM_CaseManager__r.Name` | `ExistingHealthPractionerCredentialed = IF(CredentialingStatus == 'Credentialing In Progress' && NPIIsActive == false, true, false)`; **also** `IsCredentialedPNCDelegated = IF(CredentialingStatus == 'Credentialed', IF(IsPNC \|\| IsDelegated \|\| IsPDelegatedGroup=='Yes', false, true), false)` | `PRM_FetchExistingNPIInfo_Procedure_14.oip-meta.xml` — credentialed `:470`, PNC/delegated `:493`, DR call `:180`; status field `PRMDRExtractExistingNPIInfo_1:205`, NPI IsActive `:240`, CM name `:354` |
| `Group:NPIExist` (→ R-E4/E5) | `PRMDRCheckExistingGroupNPI` | `HealthcareProviderNpi` WHERE `Npi = <group NPI>` AND `NpiType = 'GroupNPI'` AND `PRM_NPIEffectiveToday__c = true`; also returns EffFrom/EffTo/Pending/AccountId | `GroupNPIExist = IF(HPNPI.Id, true, false)` | `PRMDRCheckExistingGroupNPI_1.rpt-meta.xml` — NpiType `:67-70`, effective-today `:137-140`, formula `:156-157` |
| Group resolution (→ R-E6 — group valid **and** matches the named group) | **Apex remote action** `PRM_PractitionerCreationUtility.getGroupData` → `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId(npi, taxId)` | (1) `Identifier` WHERE `IdValue = <TaxId>` AND `PRM_Active__c = true` AND `PRM_IDEffectiveToday__c = true` AND `PRM_Type__c = 'EIN'` AND `ParentRecordId != null` → group `Account` ids; (2) `HealthcareFacility` WHERE `AccountId IN <those>` AND `PRM_Active__c = true` AND `PRM_NpiId__r.Npi = <NPI>` AND `RecordType.DeveloperName != 'PRM_NCPDP'` | returns `GroupId`/`ExistingGroupNPIId`/`GroupName`/`TINID` per matched group (keyed on **GroupNPI + GroupTaxId/EIN**, not the typed name) | `PRM_PractitionerCreationHelper.cls:53-90`; remote-action binding OS `...English_25.os-meta.xml:2003-2018` |
| `PracticeLocationId` — **IBX** path (→ R-E7) | `PRMDRGetActivePracticeLocationforIBXInfoCode` | `HealthcareFacility` WHERE `PRM_Active__c = true` AND `Name LIKE <Key>` AND `AccountId = <group account>`; **gated by** `PRM_InfoCodeAssignment__c` WHERE `PRM_InfoCode__r.PRM_Code__c = 'IBX'` AND `PRM_Active__c = true`; addresses filtered to `PRM_AddressType__c LIKE 'Primary' \|\| 'Practice'` | `PracticeLocationId = HealthcareFacility.Id` (null ⇒ no match ⇒ R-E7 flag) | `PRMDRGetActivePracticeLocationforIBXInfoCode_1.rpt-meta.xml` — HF active `:67-70`, **IBX info-code** `:236-239`, info-code active `:338-341`, PLId `:204-211`, addr filter `:319` |
| `PracticeLocationId` — **Delegated** path (→ R-E7, the *delegated* guided flow) | **Apex** `PRM_PractitionerCreationHelper.getPracticeLocation` → `checkDelegatedPracLoc()` | `facilityIds` = active `HealthcareFacility` for the group account whose `PRM_NpiId__r.Npi = <NPI>` (or `PRM_Primary__c = true`), excluding `PRM_NCPDP`; then `PRM_InfoCodeAssignment__c` WHERE `PRM_InfoCode__r.PRM_Type__c = 'Delegated'` AND `PRM_HealthcareFacility__c IN <facilityIds>` AND `PRM_Active__c = true` | only locations with an **active Delegated info-code assignment** are returned (`DetailsFound=false` ⇒ none ⇒ blocked) | `PRM_PractitionerCreationHelper.cls` — `getPracticeLocation` `:92-106`, `getlocVsFac` `:108-129`, **`checkDelegatedPracLoc` `:164-174`** |

> **This nails the "delegated practitioner must have a practice location with a delegated info code"
> phrasing — and it lives in Apex, not the OmniScript.** For the **delegated** guided flow a practice
> location is joinable only when it is an **active `HealthcareFacility`** under the resolved group
> (NPI/EIN match) **that carries an active `PRM_InfoCodeAssignment__c` whose
> `PRM_InfoCode__r.PRM_Type__c = 'Delegated'`** (`checkDelegatedPracLoc`, `PRM_PractitionerCreationHelper.cls:164-174`).
> The IBC/IBX flow uses the sibling DataRaptor path keyed on `PRM_Code__c = 'IBX'`. The
> `PractitionerCreationPayloadValidator` must re-implement **both** info-code lookups
> (`HealthcareFacility` × `PRM_InfoCodeAssignment__c` × `PRM_InfoCode__c`, filtered by `PRM_Type__c`/`PRM_Code__c`)
> server-side, plus the group resolution (`Identifier` EIN × `HealthcareFacility` NPI).

**Net-new server-side query surface for the payload validator** (objects/fields it must read to enforce
R-E1–E7, none of which the current date-only validator queries): `HealthcareProviderNpi`
(`Npi`, `NpiType`, `PractitionerId`, `AccountId`, `IsActive`, `PRM_NPIEffectiveToday__c`,
`PRM_CaseManager__r.Name/PRM_Stage__c`), `Account` (`RecordType.DeveloperName='PRM_Practitioner'`,
`PRM_CredentialingStatus__c`, `PRM_DelegatedOnly__c`, `PRM_DelegatedGroup__c`, `PRM_PNC__c`),
`Identifier` (`IdValue`, `PRM_Type__c='EIN'`, `PRM_Active__c`, `PRM_IDEffectiveToday__c`, `ParentRecordId`),
`PRM_InfoCodeAssignment__c` (`PRM_Active__c`, `PRM_InfoCode__r.PRM_Code__c`, **`PRM_InfoCode__r.PRM_Type__c`**,
`PRM_HealthcareFacility__c`), `HealthcareFacility` (`PRM_Active__c`, `Name`, `AccountId`, `LocationId`,
`PRM_NpiId__r.Npi/NpiType`, `PRM_Primary__c`, `RecordType.DeveloperName`).

---

## 3. Effective-date rules (the only eligibility rules already in Apex)

Verified by **Contract Conformance** (Agent 3). These exist in `PRM_PractitionerCreationValidator`
**and** are mirrored in the OmniScript and in the `PRM_EffectiveDateValidation` trigger on HCPF/HFN.

| Rule ID | Rule | Condition (REJECT when) | Legacy source | New owner |
|---------|------|-------------------------|---------------|-----------|
| R-D1 | Practitioner **Effective From is required** | `EffectiveFrom == null` | `PRM_PractitionerCreationValidator.cls:83-84` | `PractitionerCreationPayloadValidator` |
| R-D2 | Effective **To ≥ Effective From** | `EffectiveTo < EffectiveFrom` | Validator `:87-88`; OS formula `:5323`; `SetEffectiveToError` "Effective To Date must be greater than Effective From Date." `:7926` | `PractitionerCreationPayloadValidator` |
| R-D3 | Practitioner **Effective From not earlier than** an existing **active, non-pending** Practice Location's Effective From | `pracEffFrom < HF.PRM_EffectiveFrom__c` (HF active & not pending) | Validator `:102-108` (mirrors `PRM_EffectiveDateValidation`) | `PractitionerCreationPayloadValidator` + trigger |
| R-D4 | Practitioner **Effective To not later than** the existing Practice Location's Effective To | `pracEffTo > HF.PRM_EffectiveTo__c` | Validator `:109-112` | `PractitionerCreationPayloadValidator` + trigger |
| R-D5 | "Active" is derived: `EffFrom <= TODAY` and (`EffTo` null or `> TODAY`) | computed, not rejected | OS `IsRecordActive` formula `:8405` | service compute |

> **Scope of the existing Apex validator (be precise in verdicts):** `PRM_PractitionerCreationValidator`
> only enforces **R-D1…R-D4** and only for **existing** HFs (brand-new HFs with no `FacilityId` are
> intentionally skipped — `collectExistingHfIds`/`addFacilityIdsFromList`, `:165-183`). It does **not**
> enforce R-E1…R-E8 or R-B*. Do not certify the validator as "full parity" just because it exists.

---

## 4. Field-level required rules (≈25 enforced fields)

Verified by **Contract Conformance** (Agent 3, "required keys per branch"). These are `"required": true`
elements + `Requirement` validations in the active OmniScript. Representative (not exhaustive):

| Rule ID | Rule | Legacy source (OmniScript v25) |
|---------|------|--------------------------------|
| R-F1 | Practitioner **Role** is required | `Role` multi-select `"required": true` (:410) |
| R-F2 | **Only 1 Degree can be Primary** | `Requirement` "Only 1 Degree can be Primary." (:5098) |
| R-F3 | **Hispanic Origin** is required | `Requirement` "Hispanic Origin is a required." (:5930) |
| R-F4 | **Personal Pronouns** required (+ "Prefer not to share" mutual-exclusion) | `Requirement` (:6777, :7057) |
| R-F5 | ~20 other `required:true` fields (address line 1, city, state, zip, license fields, etc.) | `"required": true` at :1455, :1928, :1984, :2074, :2182, :3058, :3185, :3420, :3458, :3815, :3957, :4078, :4153, :4188, :4267, :4305, :4352, :4455, :4493, :4558, :4660, :4840, :5068, :5131, :5345, :5400, :5595, :5762, :5896, :6261, :6434, :6582, :6935, :6953 |

> For the redesign, "required" is a **payload-validator** obligation (the server can no longer rely on the
> UI). The agent should treat any required field that has **no server-side check** in
> `PractitionerCreationPayloadValidator` as `NEEDS-FIX`, not `PASS`.

---

## 5. How the agents use this ledger

- **Contract Conformance (Agent 3)** — for a delivered `PractitionerCreationPayloadValidator` (or any
  intake artifact), assert each R-E*/R-D*/R-F* rule has a corresponding **server-side check + a negative
  test** that proves the rejection. A rule present in this ledger but absent in the delivery → `NEEDS-FIX`
  (or `BLOCKED` if it's an eligibility gate like R-E1…R-E3 that prevents duplicate/again-credentialed
  creation).
- **Branch-Coverage (Agent 2)** — assert R-B1…R-B6 gates are honored on the correct branch (e.g. R-B2:
  no location/network work without `CaseManagerId`).
- **Critic (Agent 9)** — cross-check: a rule the validator *claims* to enforce must have a negative test
  asserting the rejection; a "validator PASS" with no negative test for R-E2/R-E3 is a contradiction.
- **Eval harness ([`06`](06_Agent_Eval_Harness.md))** — each R-E* becomes a seeded-defect case (payload
  that *should* be rejected) so we can measure the validator agent's recall.

## 6. Open items / cannot-verify-yet

- ✅ **Resolved — the condition logic for R-E1…R-E7 is drilled out in §2.1** (queries + formulas + line
  citations).
- ✅ **Resolved — runtime activation confirmed against the live `ibx-dev` org** (2026-06-28).
  `SELECT Name, IsActive, VersionNumber FROM OmniDataTransform` returns `IsActive = false` for all three
  lookup DataRaptors (`PRMDRExtractExistingNPIInfo`, `PRMDRCheckExistingGroupNPI`,
  `PRMDRGetActivePracticeLocationforIBXInfoCode`) — i.e. **repo snapshot == org**. They are invoked
  by-name from their parent IPs/type-aheads, so the `active=false` flag does **not** stop them; it only
  governs the standalone REST entry point. §2.1 is therefore byte-exact, not provisional.
- ✅ **Resolved — R-E6 group resolution is Apex, not a DataRaptor.** The `GroupName` type-ahead is a
  **Remote Action** to `PRM_PractitionerCreationUtility.getGroupData` →
  `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId(npi, taxId)`, which resolves the group by
  **GroupNPI + EIN/TaxId** (`Identifier` EIN join → `HealthcareFacility` NPI join), not by typed name.
  Captured in §2.1. The *delegated* practice-location info-code rule is likewise Apex
  (`checkDelegatedPracLoc`, `PRM_InfoCode__r.PRM_Type__c = 'Delegated'`).
- **R-E8 (networks selected)** condition is a pure OS formula (`SelectedPLNetworks == null`), no DR — fully
  captured.
- **`locationsToUpsert` cardinality cap** is *recommended* in the reference (`PRM_PractitionerCreationContainer_Process.md`
  §7 rec. 6) but **not implemented** in the active validator. Flag as a divergence, not a parity miss.

---

*Grounded in: [`PRM_PractitionerCreationContainer_Process.md`](../reference/PRM_PractitionerCreationContainer_Process.md)
§4/§8, [`PRM_PractitionerCreation_Hierarchy.md`](../reference/PRM_PractitionerCreation_Hierarchy.md) branch
table, `classes/PRM_PractitionerCreationValidator.cls` (full read), the **active** OmniScript
`omniScripts/PRM_PractitionerCreation_English_25.os-meta.xml` (`Validation`/`Formula`/required elements,
line-cited above), and the condition DataRaptors / Fetch-IP behind the eligibility flags (§2.1):
`omniDataTransforms/PRMDRExtractExistingNPIInfo_1.rpt-meta.xml`,
`omniDataTransforms/PRMDRCheckExistingGroupNPI_1.rpt-meta.xml`,
`omniDataTransforms/PRMDRGetActivePracticeLocationforIBXInfoCode_1.rpt-meta.xml`, and the **active**
`omniIntegrationProcedures/PRM_FetchExistingNPIInfo_Procedure_14.oip-meta.xml`.*
