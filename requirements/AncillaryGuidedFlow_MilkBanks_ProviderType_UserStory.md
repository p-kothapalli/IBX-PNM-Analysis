# USER STORY: Add "Milk Banks" as a New Ancillary Provider Type & Service

**Persona:** Ancillary Cred Specialist (completing the Ancillary Application)
**Priority:** P1 (should-have)
**Vertical:** Provider Network Management (PNM) — Health Cloud + PNM managed package
**Primary OmniScripts:** `PRM_AncillaryProviderForm_English` (parent, latest active **v43**), `PRM_AncillaryTypesAndServices_English` (embedded, latest active **v24**)
**Downstream OmniScripts (full lifecycle in scope):** `PRM_AncillaryPSVForm_English` (v13), `PRM_AncillaryQC_English` (v2), `PRM_AncillaryPDA_English` (v5), `PRM_AncillaryReassessmentPSV_English` (v8), `PRM_AncillaryCredApplicationReview_English` (v1)
**Integration Procedures:** `PRM_AncillaryFormRecordsCreationParent` (+ child records-creation IP)
**Primary Object:** `PRM_AncillaryAssessment__c` (new Record Type + fields)
**Apex:** `PRM_GlobalConstant`, `PRM_AncillaryProviderFormDataUpdates` (+ `PRM_AncillaryProviderFormDataUpdatesTest`)
**Relevant Requirements:** `AncillaryGuidedFlow_ProviderTypesServices_UserStories.md` (the architecture this story extends), `AncillaryAssessment_BillingType_UserStories.md`, `BugFix_AncillaryAssessment_PracticeClassification_Override.md`

---

## Story

**As an** Ancillary Cred Specialist completing an Ancillary Application,
**I want** to select **"Milk Bank"** as a Provider Type & Service, answer the Milk-Bank-specific questions (and its sub-services), and have the application create a dedicated Milk Bank assessment record,
**So that** IBX can credential human-milk-bank facilities through the same guided flow used for every other ancillary provider type, and the resulting record flows through PSV, QC, PDA, and Reassessment like any other ancillary provider.

**Why it matters:** Milk banks are a provider type the business must now credential, but the guided Ancillary Application has no way to capture them. Because the flow is metadata-driven, a new type is normally low-cost — but the record-creation routing map is hard-coded in Apex, so "just adding a checkbox" silently produces **no** assessment record. This story delivers the type end-to-end so intake, record creation, and the downstream credentialing lifecycle all recognize Milk Banks.

---

## Scope


| Flow                    | OmniScript                                                    | Affected Step / Screen                    | Change                                               |
| ----------------------- | ------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------- |
| Intake — type selection | `PRM_AncillaryTypesAndServices_English` (new version)         | "Provider Types & Services" checkbox tree | Add "Milk Bank" option (+ its sub-services)          |
| Intake — data capture   | `PRM_AncillaryTypesAndServices_English` (new version)         | New `MilkBankStep`                        | Milk-Bank-specific questions + sub-service list      |
| Intake — parent         | `PRM_AncillaryProviderForm_English` (new version)             | Embedded child re-point                   | Point to new Types & Services version                |
| Record creation         | `PRM_AncillaryProviderFormDataUpdates` + `PRM_GlobalConstant` | `insertAARecords()` / `API_METHOD_MAP`    | Route `PTSMilkBank` to a Milk Bank assessment record |
| Object                  | `PRM_AncillaryAssessment__c`                                  | Record Type + layout + fields             | New `PRM_MilkBank` RT, layout, Milk-Bank fields      |
| Lifecycle               | PSV / QC / PDA / Reassessment / App Review scripts            | Milk Bank record-type display             | Display/verify Milk Bank record type                 |
| Security                | 5 permission sets                                             | FLS                                       | Grant access to new fields                           |


---

## Current State (from codebase — verified)

Provider types are driven by three metadata layers plus one hard-coded Apex map:

1. `**PRM_AncillaryFormType__mdt**` (`PRM_Category__c = AncillaryTypes`) — one row per selectable option, keyed by `PRM_APIName__c` (e.g. `PTSSkilledNursing`). Rendered as the checkbox tree by LWC `**prmAncillaryFormTypeOptions**` via `PRM_CheckboxListController.getTypeOptions()`. Sub-options set `PRM_ParentOption__c` to the parent's API name.
2. **Per-type OmniScript Step** (e.g. `SkilledNursingStep`) shown when `AncillaryTypesAndServices:PTS<Type> = true`. Service checkbox lists inside a Step use LWC `**prmCheckboxList`** fed by `**PRM_AncillaryFormService__mdt**`.
3. `**PRM_TypesandServices__mdt.PRM_TypeandServiceMapping__c**` — JSON mapping of screen-element path → `PRM_AncillaryAssessment__c` field, consumed by `PRM_AncillaryProviderFormDataUpdates.insertAARecords()` (`flattenJSON`).
4. `**PRM_GlobalConstant.API_METHOD_MAP**` (hard-coded Apex) — `insertAARecords()` **skips any selected flag not present in this map**, so a type absent here creates no record. `recordType` is resolved by **Name** (falling back to `General`); `SUBTYPESSET` marks types that skip the shared Medicare/Ownership/QM/Warranty sections; `ANCILLARY_STAFF_TYPES` adds staff rows; a `NumberOfSelections` formula in the Types & Services script sums every `PTS<Type>` flag for the "select at least one" validation.

`PRM_AncillaryAssessment__c` currently has 21 record types, each with a page layout, plus a `General` fallback. **No "Milk" anything exists in the codebase today** (verified).

**Downstream display is data-driven (verified).** The "Provider Type & Service(s)" read-only field on PSV/QC/PDA is fed from the label field `PRM_ProviderTypeService__c` (present on both `PRM_AncillaryAssessment__c` and `IndividualApplication`), which `insertAARecordsHelper` already stamps with the provider-type label:

- **PSV** (`PRM_AncillaryPSVForm_English_13`): step `VerifyAttestationSignature` ("Verify Attestation/Signature"), Text element `ProviderTypeAndService`, sourced by DataRaptor `PRMDRExtractCaseRelatedDataforAncillaryPSVForm` (`AncillaryAssessment:PRM_ProviderTypeService__c` → `VerifyAttestationSignature:ProviderTypeAndService`).
- **QC** (`PRM_AncillaryQC_English_2`) and **PDA** (`PRM_AncillaryPDA_English_5`): step `ReviewAncillary` ("Review Ancillary") → block `AccountBlock` ("Account"), Text-Area `ProviderTypeServices`, sourced by DataRaptor `PRMTransformAncillaryDetails` (comma-joined `ProviderTypeService` → `AccountBlock:ProviderTypeServices`).

Because these read the label generically, **"Milk Bank" displays automatically** once record creation writes `PRM_ProviderTypeService__c = "Milk Bank"` — no per-type OmniScript config is needed for the display. Downstream edits are required **only** if Milk-Bank-specific verification/QC/PDA content is requested (the sole precedent for per-type conditional content is PSV's `IsAmbulatoryPresent = CONTAINS(ProviderTypeAndService, "Ambulatory Surgery Center")`).

---

## Acceptance Criteria

### AC-1 — "Milk Bank" is selectable on the Provider Types & Services screen (Pattern A)

**Given** an Ancillary Cred Specialist is on the "Provider Types & Services" screen of a new Ancillary Application,
**When** the screen loads,
**Then** "Milk Bank" appears in the provider-type checkbox list in the agreed alphabetical position,
**And** it can be checked and unchecked like any other top-level provider type,
**And** its selection persists when navigating away and back.

### AC-2 — Selecting Milk Bank reveals its dedicated questions step (Pattern A)

**Given** the specialist has checked "Milk Bank",
**When** they advance through the application,
**Then** a Milk-Bank questions step is shown that is hidden when Milk Bank is not selected,
**And** the step presents the Milk-Bank-specific questions defined by business (see Clarification Q1).

### AC-3 — Milk Bank sub-services can be captured (Pattern A)

**Given** the specialist is on the Milk Bank step,
**When** they select one or more Milk Bank sub-services from the sub-service list,
**Then** the chosen sub-services are retained on the application,
**And** the specialist can select multiple sub-services in a single submission.

### AC-4 — Submitting creates one Milk Bank assessment record with the dedicated record type (Pattern A)

**Given** a specialist completes and submits an application with only "Milk Bank" selected,
**When** the submission is processed,
**Then** exactly one Milk Bank Ancillary Assessment record is created for the vendor,
**And** the record carries the dedicated "Milk Bank" record type (not the General fallback),
**And** its name follows the existing convention (vendor name + " - Milk Bank"),
**And** the Milk-Bank answers and selected sub-services are saved on that record.

### AC-5 — Shared application sections are captured on the Milk Bank record (Pattern A)

**Given** the specialist has completed the shared Ownership/Licensure/Insurance, Quality-Management, and Warranty sections,
**When** the Milk Bank record is created,
**Then** those shared answers are stamped onto the Milk Bank Ancillary Assessment record the same way they are for other full provider types,
**And** CMS (Medicare/Medicaid) certification is **not** required for Milk Bank (see AC-8c) — a missing Medicare/Medicaid number must not block submission for this type.

### AC-6 — Milk Bank counts toward the "select at least one type" validation (Pattern A, edge)

**Given** a specialist has selected **only** "Milk Bank" and no other provider type,
**When** they attempt to proceed past the selection screen,
**Then** the form treats the selection as valid and does not block them with the "select at least one provider type" error.

### AC-7 — Milk Bank alongside another type creates independent records (Pattern A, edge)

**Given** a specialist selects "Milk Bank" **and** an existing type (e.g. Clinical Laboratory) in one submission,
**When** they submit,
**Then** two Ancillary Assessment records are created — one Milk Bank and one Clinical Laboratory — each with its own record type,
**And** neither record's data bleeds into the other.

### AC-8 — Milk Bank is recognized across the credentialing lifecycle (Pattern A)

**Given** a Milk Bank Ancillary Assessment record exists on a case (its "Provider Type & Service" reads "Milk Bank"),
**When** the case is opened in PSV ("Verify Attestation/Signature" step), QC and PDA ("Review Ancillary" step → Account block), Reassessment, and Application Review,
**Then** each screen displays "Milk Bank" in the read-only "Provider Type & Service(s)" field automatically (the display reads the provider-type label, so no per-type screen config is needed),
**And** no screen errors, hides the record, or mislabels it.

### AC-8a — Milk-Bank-specific verification content (Pattern A, conditional on Q9)

**Given** business requires Milk-Bank-specific questions to be **verified** (not just displayed) during PSV/QC/PDA,
**When** a Milk Bank case is worked in those flows,
**Then** the Milk-Bank-specific content is shown only for Milk Bank cases (mirroring how Ambulatory-specific content is shown today),
**And** it is hidden for non-Milk-Bank cases.
*(If Q9 = "display only", this AC is out of scope and only AC-8 applies.)*

### AC-8b — CLIA certification is verified only when the Milk Bank performs lab testing (Pattern A) — **business-confirmed**

**Given** a Milk Bank organization that **performs CLIA-regulated laboratory testing**,
**When** the case is verified in PSV/QC,
**Then** the specialist verifies the organization's CLIA certification,
**And given** a Milk Bank organization that does **not** perform CLIA-regulated laboratory testing,
**When** the case is verified,
**Then** CLIA verification is **not** required and its absence does not block case completion.

### AC-8c — CMS (Medicare/Medicaid) certification is not applicable to Milk Banks (Pattern A) — **business-confirmed**

**Given** a Milk Bank case,
**When** it moves through intake and PSV/QC verification,
**Then** CMS (Medicare/Medicaid) certification is **not** required and the CMS/Medicare verification step is not enforced for Milk Bank,
**And** the case can be completed without a Medicare/Medicaid identifier,
**Because** human milk banks are not a recognized CMS-certified provider/supplier type under the Medicare Conditions of Participation.

### AC-9 — New Record Type & page layout (Pattern B)

**AC-9 — Create Record Type on `PRM_AncillaryAssessment__c`**

- **Record Type API Name:** `PRM_MilkBank`
- **Record Type Label / Name:** `Milk Bank`  *(the Name must exactly equal the `API_METHOD_MAP` label, because record types are resolved by Name at runtime)*
- **Active:** true
- **Page Layout:** new `PRM_AncillaryAssessment__c-Milk Bank.layout` assigned to the record type, exposing the shared sections + the new Milk-Bank fields
- **Assigned on profiles/permission sets** per AC-12

### AC-10 — New custom fields on `PRM_AncillaryAssessment__c` (Pattern B)

**AC-10 — Create the Milk-Bank fields (final list pending Clarification Q1)**

- **Object:** `PRM_AncillaryAssessment__c`
- **Sub-services field (confirmed by hierarchy decision):**
  - **API Name:** `PRM_MilkBankSubServices__c`
  - **Type:** Multi-Select Picklist (restricted)
  - **Label:** `Milk Bank Sub-Services`
  - **Values:** per Clarification Q2
  - **Track History:** true
- **Additional Milk-Bank question fields:** one field per business question from Clarification Q1 (types/labels TBD). Each follows the naming convention `PRM_<Question>__c` and is Read-Only on the layout (populated via guided flow only), mirroring existing types.

### AC-11 — New Custom Metadata records (Pattern B)

**AC-11 — Create the metadata that wires Milk Bank into the flow**

- `**PRM_AncillaryFormType.Milk_Bank**` (new): `PRM_APIName__c = PTSMilkBank`, `PRM_Category__c = AncillaryTypes`, `PRM_OptionLabel__c = Milk Bank`, `PRM_SubCategory__c = Provider Types & Services`, `PRM_ParentOption__c = (null)`, `PRM_DisplayOrder__c = <agreed order>`.
- `**PRM_TypesandServices.Milk_Bank**` (new): `PRM_TypeAndServiceName__c = PTSMilkBank`, `PRM_TypeandServiceMapping__c = { "<MilkBankStep element path>": "<PRM_...__c>", … , "MilkBankStep_<subservice block>_SelectedValues": "PRM_MilkBankSubServices__c" }`.
- `**PRM_AncillaryFormService.MilkBank***` (new, one per sub-service checkbox list): `PRM_Category__c`, `PRM_SubCategory__c` (heading), `PRM_CheckboxOptions__c` (`|`-delimited values), `PRM_DisplayOrder__c`.

### AC-12 — Field Access & Permission Sets (Pattern C)

**AC-12 — Grant FLS on the new Milk-Bank fields**

- `**PRM_DataModifyAll`:** Object Read/Create/Edit/View All; Field Read + Edit on all new fields.
- `**PRM_ProviderDataAdmin`, `PRM_AncillaryCredSpecialist`, `PRM_CredentialingUser`:** Object Read/Create/Edit; Field Read + Edit on all new fields.
- `**PRM_DataViewAll`:** Object Read/View All; Field Read on all new fields.
- New Record Type `PRM_MilkBank` assigned to the same permission sets/profiles that hold the other Ancillary Assessment record types.

### AC-13 — Record creation is resilient if routing is incomplete (Pattern A, negative)

**Given** the "Milk Bank" type is selectable but not yet fully wired into record creation,
**When** a specialist submits an application with Milk Bank selected,
**Then** the submission does not fail silently with zero records and no signal,
**And** the failure is logged so QA/ops can detect a mis-wired type rather than discovering missing records later.

> *Note:* AC-13 is a guardrail against the framework's known trap — a selected type absent from `API_METHOD_MAP` is skipped with no record and no error. The developer must confirm the map entry AND the record-type Name match before sign-off.

---

## Technical Implementation (high-level)


| Component                                                                                                               | Type            | Change                                                                                                                                                                                                                                                            | Notes / AC                                     |
| ----------------------------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `PRM_AncillaryFormType.Milk_Bank`                                                                                       | Custom Metadata | **NEW** — `PTSMilkBank`, category `AncillaryTypes`, `DisplayOrder` per business                                                                                                                                                                                   | Renders the checkbox (AC-1)                    |
| `PRM_GlobalConstant.API_METHOD_MAP`                                                                                     | Apex            | **EDIT** — add `'PTSMilkBank' => 'Milk Bank -- MilkBankStep'`                                                                                                                                                                                                     | Required or no record is created (AC-4, AC-13) |
| `PRM_GlobalConstant.SUBTYPESSET` / `ANCILLARY_STAFF_TYPES`                                                              | Apex            | **EDIT (conditional)** — only if Milk Bank skips shared sections or needs staff rows                                                                                                                                                                              | Per Clarification Q3/Q4                        |
| `PRM_TypesandServices.Milk_Bank`                                                                                        | Custom Metadata | **NEW** — element-path → field mapping JSON incl. `PRM_MilkBankSubServices__c`                                                                                                                                                                                    | Persists step data (AC-3, AC-4)                |
| `PRM_AncillaryFormService.MilkBank*`                                                                                    | Custom Metadata | **NEW** — sub-service checkbox options                                                                                                                                                                                                                            | Feeds `prmCheckboxList` (AC-3)                 |
| `PRM_AncillaryTypesAndServices_English` (clone latest → v25)                                                            | OmniScript      | **NEW version** — add `MilkBankStep` (show on `PTSMilkBank`), sub-service `prmCheckboxList` block, and add `PTSMilkBank` to the `NumberOfSelections` formula                                                                                                      | AC-1, AC-2, AC-3, AC-6                         |
| `PRM_AncillaryProviderForm_English` (clone latest → v44)                                                                | OmniScript      | **NEW version** — re-point embedded Types & Services child                                                                                                                                                                                                        | Activates the new intake                       |
| `PRM_AncillaryAssessment__c` RT `PRM_MilkBank` + layout                                                                 | Object/Layout   | **NEW** — Name = `Milk Bank`; new page layout                                                                                                                                                                                                                     | AC-9 (Name must match label)                   |
| `PRM_AncillaryAssessment__c` fields                                                                                     | Object          | **NEW** — `PRM_MilkBankSubServices__c` + question fields                                                                                                                                                                                                          | AC-10                                          |
| PSV v13 / QC v2 / PDA v5 (+ Reassessment v8, App Review v1)                                                             | OmniScript      | **NO CHANGE for display** — "Provider Type & Service(s)" is data-driven from `PRM_ProviderTypeService__c` via DRs `PRMDRExtractCaseRelatedDataforAncillaryPSVForm` (PSV) and `PRMTransformAncillaryDetails` (QC/PDA); Milk Bank appears once the label is written | AC-8                                           |
| PSV / QC verification content (Milk Bank)                                                                               | OmniScript      | **EDIT (confirmed in scope)** — (a) conditionally require **CLIA** verification only when the org performs CLIA-regulated lab testing; (b) do **not** enforce the CMS/Medicare (`VerifyCMS`) step for Milk Bank; gate via the existing `CONTAINS(ProviderTypeAndService, …)` pattern | AC-8b, AC-8c                                   |
| PSV/QC/PDA other type-specific content                                                                                  | OmniScript      | **EDIT (conditional on remaining Q9)** — any additional Milk-Bank-specific verification beyond CLIA/CMS                                                                                                                                                          | AC-8a                                          |
| `PRM_ProviderDataAdmin`, `PRM_AncillaryCredSpecialist`, `PRM_CredentialingUser`, `PRM_DataViewAll`, `PRM_DataModifyAll` | Permission Set  | **EDIT** — FLS + record-type visibility                                                                                                                                                                                                                           | AC-12                                          |
| `PRM_AncillaryProviderFormDataUpdatesTest`                                                                              | Apex Test       | **EDIT** — Milk Bank fixture (single + alongside another type) asserting record type, name, fields                                                                                                                                                                | AC-4, AC-7; ≥85% coverage on touched code      |


> **Framework trap to call out in build:** the flow is metadata-driven **except** `API_METHOD_MAP` (and `SUBTYPESSET`/`ANCILLARY_STAFF_TYPES`), which are hard-coded in `PRM_GlobalConstant`. The record-type is resolved by **Name**, so the RT Name and the map label must be byte-identical ("Milk Bank"). Missing either yields a silently skipped or `General`-typed record.

---

## Definition of Done

- [ ] "Milk Bank" is selectable in the guided flow, reveals its step, and captures its questions + sub-services.
- [ ] Submitting Milk Bank (alone and alongside another type) creates the correct `PRM_MilkBank`-record-type assessment record(s) with the expected name and field values.
- [ ] Shared Medicare/Ownership/QM/Warranty sections stamp onto the Milk Bank record (unless business designates it a sub-type).
- [ ] `NumberOfSelections` validation accepts a Milk-Bank-only selection.
- [ ] New Record Type, page layout, and fields deployed; FLS granted on all 5 permission sets.
- [ ] PSV ("Verify Attestation/Signature"), QC/PDA ("Review Ancillary" → Account block), Reassessment, and Application Review display "Milk Bank" in the read-only "Provider Type & Service(s)" field without error (data-driven — verify only; no build unless Q9 requires type-specific verification content).
- [ ] CLIA verification is required **only** when the Milk Bank performs CLIA-regulated lab testing, and is not enforced otherwise (AC-8b).
- [ ] CMS/Medicare verification (`VerifyCMS`) is not enforced for Milk Bank, and a case completes without a Medicare/Medicaid identifier (AC-8c).
- [ ] `API_METHOD_MAP` entry and RT Name verified to match; negative path (mis-wired type) logs rather than silently no-ops.
- [ ] `PRM_AncillaryProviderFormDataUpdatesTest` extended; ≥85% coverage on touched Apex.
- [ ] End-to-end regression: at least one other existing provider type still creates its record correctly.

---

## Clarification Questions (Before Implementation)


| #   | Question                                                                                                                                                                                                                     | Impact                                                                | Owner                        |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------- |
| Q1  | What **specific questions/fields** must the Milk Bank step capture (e.g. HMBANA accreditation, donor screening, pasteurization/processing method, storage capacity, dispensing vs. processing)? Provide labels + data types. | Defines `MilkBankStep` elements + new AA fields + mapping JSON        | Business / Credentialing SME |
| Q2  | What are the **Milk Bank sub-services** and their exact picklist values (e.g. Donor Human Milk Dispensary, Milk Processing/Pasteurization, Donor Screening)?                                                                 | `PRM_MilkBankSubServices__c` values + `PRM_AncillaryFormService` rows | Business                     |
| Q3  | Does Milk Bank complete the **shared Medicare / Ownership / Licensure / Quality-Management / Warranty** sections (a "full" type), or is it a lightweight sub-type that skips them (`SUBTYPESSET`)?                           | Whether shared sections are stamped (AC-5)                            | Business / Credentialing     |
| Q4  | Does Milk Bank require **staff/practitioner records** (like Admitting Physician / Medical Director on other types)?                                                                                                          | `ANCILLARY_STAFF_TYPES` + staff capture UI                            | Business                     |
| Q5  | ✅ **ANSWERED** — Verification rules: **CLIA** certification is verified **only if** the org performs CLIA-regulated laboratory testing (otherwise not required, does not block). **CMS (Medicare/Medicaid)** certification is **not applicable** — human milk banks are not a recognized CMS-certified provider/supplier type under the Medicare Conditions of Participation. *(Still confirm: any HMBANA / state-license verification?)*                                                                                          | Drives AC-8b (CLIA conditional) + AC-8c (no CMS) + AC-5              | Credentialing / Compliance   |
| Q6  | What **display-order position** should "Milk Bank" occupy in the provider-type list?                                                                                                                                         | `PRM_DisplayOrder__c` value                                           | Business                     |
| Q7  | Which **states / plans** does Milk Bank credentialing apply to, and are there network/taxonomy implications?                                                                                                                 | Scope boundaries + downstream network records                         | Network Mgmt / Business      |
| Q8  | Is Milk Bank a **medical** ancillary type (`PTS…`) or a **behavioral-health** type (`BTS…`)? (Assumed medical `PTSMilkBank`.)                                                                                                | API key prefix + which screen section it lives in                     | Business                     |
| Q9  | Basic display of "Milk Bank" in PSV/QC/PDA is automatic (data-driven). **Partially answered:** at minimum PSV/QC must conditionally **verify CLIA** (AC-8b) and **skip CMS** (AC-8c) — so some verification content is in scope. Confirm whether any **other** Milk-Bank-specific data must be actively verified.                        | Whether AC-8a is in scope; depth of downstream OmniScript edits       | Credentialing / QA           |


---

## Impact Analysis


| Component                                                                                  | Type            | Impact Level | Description                                                                                             |
| ------------------------------------------------------------------------------------------ | --------------- | ------------ | ------------------------------------------------------------------------------------------------------- |
| `PRM_GlobalConstant`                                                                       | Apex            | MEDIUM       | Hard-coded routing map edit; shared by all ancillary record creation                                    |
| `PRM_AncillaryProviderFormDataUpdates(+Test)`                                              | Apex            | MEDIUM       | New fixture; metadata-driven so runtime likely unchanged                                                |
| `PRM_AncillaryTypesAndServices_English`                                                    | OmniScript      | HIGH         | New version with new step + formula change; core intake                                                 |
| `PRM_AncillaryProviderForm_English`                                                        | OmniScript      | MEDIUM       | New parent version re-pointing child                                                                    |
| PSV / QC / PDA / Reassessment / App Review                                                 | OmniScript      | LOW–MEDIUM   | Display is data-driven (no change); new versions only if Q9 requires type-specific verification content |
| `PRM_AncillaryAssessment__c` (RT + fields + layout)                                        | Object/Metadata | MEDIUM       | New record type, layout, fields                                                                         |
| `PRM_AncillaryFormType__mdt`, `PRM_TypesandServices__mdt`, `PRM_AncillaryFormService__mdt` | Custom Metadata | LOW          | Additive rows                                                                                           |
| 5 permission sets                                                                          | Metadata        | LOW          | FLS + RT visibility                                                                                     |
| Reporting / dashboards                                                                     | Config          | LOW          | New record type available for ancillary reports                                                         |


---

## Estimated Effort


| Component                                                                   | Change Type     | Effort | Notes                                                               |
| --------------------------------------------------------------------------- | --------------- | ------ | ------------------------------------------------------------------- |
| Custom Metadata (FormType, TypesandServices, FormService)                   | Config          | S      | Additive rows                                                       |
| `PRM_GlobalConstant` `API_METHOD_MAP` (+ conditional sets)                  | Apex            | S      | One-line map + test                                                 |
| New RT + page layout + Milk-Bank fields                                     | Object/Metadata | M      | Depends on Q1 field count                                           |
| `PRM_AncillaryTypesAndServices` new version (step + sub-services + formula) | OmniScript      | L      | New step build + validation formula                                 |
| Parent `PRM_AncillaryProviderForm` new version                              | OmniScript      | S      | Re-point child                                                      |
| PSV / QC / PDA / Reassessment / App Review — display                        | OmniScript      | **XS** | Data-driven; verify "Milk Bank" renders, no build for basic display |
| PSV / QC — CLIA conditional + CMS-skip verification (confirmed)             | OmniScript      | S–M    | Gate CLIA on lab-testing; suppress `VerifyCMS` for Milk Bank (AC-8b/8c) |
| PSV / QC / PDA — any other type-specific verification (remaining Q9)        | OmniScript      | S–L    | Only if business names more beyond CLIA/CMS                          |
| Permission sets FLS                                                         | Config          | S      | 5 psets                                                             |
| Apex test fixtures                                                          | Apex Test       | M      | Single + multi-type submissions                                     |
| Regression + deployment                                                     | QA              | M      | Full flow smoke of one existing type + Milk Bank                    |


**Total Estimated Effort:** **L–XL** (AI-estimated — validate with team; downstream-lifecycle depth per Q9 is the main swing factor).

---

## Related User Stories

- `AncillaryGuidedFlow_ProviderTypesServices_UserStories.md` — establishes the `prmAncillaryFormTypeOptions` / `prmCheckboxList` / `PRM_TypesandServices__mdt` / `API_METHOD_MAP` architecture this story extends.
- `AncillaryAssessment_BillingType_UserStories.md` and `BugFix_AncillaryAssessment_PracticeClassification_Override.md` — related `PRM_AncillaryAssessment__c` behavior to regression-check.

---

*Prepared by Cursor analysis (graph-first + verified) of `PRM_AncillaryTypesAndServices_English_23`, `PRM_AncillaryProviderForm_English_43`, `PRM_AncillaryProviderFormDataUpdates.cls`, `PRM_GlobalConstant.cls` (`API_METHOD_MAP`, `SUBTYPESSET`, `ANCILLARY_STAFF_TYPES`), `PRM_AncillaryFormType__mdt` (56 rows), `PRM_TypesandServices__mdt` (20 rows), and `PRM_AncillaryAssessment__c` record types (21). Confirmed no "Milk Bank" component exists today.*