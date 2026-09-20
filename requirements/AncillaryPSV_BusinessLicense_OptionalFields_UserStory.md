# USER STORY: Make License Class and Provider License Effective Date Optional on the Ancillary PSV & Reassessment PSV Add/Edit Business License Modal

**Persona:** Ancillary Cred Specialist
**Priority:** P1
**OmniScript:** `PRM_AncillaryPSVForm_English` (active v13, v14), `PRM_AncillaryReassessmentPSV_English` (active v8, v9)
**Integration Procedures:** N/A — no IP change required
**Primary Component:** LWC `pRMBusinessLicenseAncNpdb` (renders the Business License table and the Add/Edit License modal on the Verify Licensure step of **both** flows)
**Relevant Requirements:**
- Business feedback (Verify Licensure step) — Angela and Frank do not collect License Class for ancillary licenses and are not familiar with the `SBRD` value
- `requirements/Ancillary_PSV_Business_Licenses_User_Story.md` — parent story; specifies **both** License Class (line 93) and Provider License Effective Date (line 89) as **Required = No**. This story corrects the shipped deviation on both.
- `requirements/AncillaryPSV_BusinessLicense_DateValidation_Relax_UserStory.md` — sibling story. Two of its statements are **superseded** by this story: its "Out of scope" note that the License-Class-inclusive duplicate check stays (line 131), and its position that Effective Date remains required (Desired Behavior item 5, AC-2, AC-4, and the final row of its behaviour matrix).
- `requirements/AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` — AC4 duplicate-check definition (line 127) to be amended
- `requirements/Ancillary_NPDB_AdverseActionLog_ProfessionalPracLoc_BugFix.md` — related ancillary NPDB adverse action context

---

## Story

**As an** Ancillary Cred Specialist working an Ancillary PSV or Ancillary Reassessment PSV case,
**I want** to add or edit a business license on the Verify Licensure step without being forced to pick a License Class or enter a Provider License Effective Date,
**So that** I can record exactly the licensure I verified from the primary source, instead of inventing a classification my team does not collect or a date the primary source does not publish.

**Why it matters:** Neither field is part of the ancillary licensure verification process, and neither plays any role in the ancillary NPDB adverse action request. Forcing them means specialists must guess — most often landing on `SBRD` for the class, which is a practitioner state-board concept the ancillary team has no basis to assert, and back-filling an effective date that the licensing body never published. Those guesses are then persisted as if they were verified data, which is the opposite of what primary source verification is for. The parent story already specified both fields as optional; the shipped component enforces both, so this is a build deviation being corrected rather than a new business relaxation.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|-----------|---------------|-------------|
| Ancillary PSV (Initial) | `PRM_AncillaryPSVForm_English` (v13, v14 active) | Verify Licensure → `AncillaryAssessmentBusinessLicense` (Custom LWC element) | `PRM_BusinessLicenseAncNpdbController` (read + duplicate check); `PRMDRAncillaryPSVCreateBusinessLicense` (write) |
| Ancillary Reassessment PSV | `PRM_AncillaryReassessmentPSV_English` (v8, v9 active) | Verify Licensure → same LWC element | `PRM_BusinessLicenseAncNpdbController` (read + duplicate check); `PRMDRCreateAncReassessPSVBL` (write) |

Both flows render through the same LWC, so a single change delivers both. No form-type gating is in scope.

---

## Current State (from codebase)

### LWC `pRMBusinessLicenseAncNpdb` — the only place either field is enforced

- **`isLicenseClassValid` getter** (`pRMBusinessLicenseAncNpdb.js`, lines 339–341): returns `false` for a new/editable row whenever License Class is blank.
- **`isEffectiveDateValid` getter** (lines 321–323): returns `false` for a new/editable row whenever Provider License Effective Date is blank.
- **`areRequiredFieldsValid` getter** (lines 343–356): includes both getters, and feeds `isSaveDisabled` (line 358) — so either field left blank disables **Save** on a new row.
- **Required asterisks:** License Class (`pRMBusinessLicenseAncNpdb.html` line 255) and Provider License Effective Date (line 177) both render `*` whenever the modal is editable.
- **License Class picklist options** are hard-coded in the component (lines 17–24): `SBRD`, `DEA`, `State Pharmacy`, `Business Registration License`, `CLIA`, `DME Registration`.

### Three places couple Expiration Date to Effective Date

Making Effective Date optional without addressing these would leave the Expiration Date field unusable or silently destructive:

- **`isExpirationDateDisabled`** (lines 299–303): returns `true` whenever Effective Date is blank. A specialist who skips Effective Date would find Expiration Date **permanently locked**.
- **`handleModalFieldChange`** (lines 632–634): clearing Effective Date also nulls Expiration Date. With Effective Date optional, clearing it would **silently discard** an expiration the specialist had already entered.
- **`modalExpirationDateMin`** (lines 219–226): when Effective Date is blank it falls back to `modalEffectiveDateMin`, the selected practice location's Effective From — imposing an unrelated floor on the Expiration Date picker.

The date-order check itself is already null-safe: `isDateOrderValid` (lines 239–246) and `modalDateValidationError` (lines 248–258) only compare the two dates when both are present, so no change is needed there.

### Duplicate detection currently keys on License Class

- **In-memory check** (lines 658–670): compares Practice Location + License Number + License State + License Class.
- **Database check** (`PRM_BusinessLicenseAncNpdbController.checkDuplicateBusinessLicense`, lines 296–323): the same four-part key — **and it short-circuits to `false` when License Class is blank** (line 304), so simply dropping the required flag would silently disable database-level duplicate protection for every row saved without a class.
- **Error copy** (lines 667–668 and 688–689) names License Class in the message shown to the specialist. The second message also contains the typo *"for the selected PRMion"*.

### Neither field is used by the ancillary NPDB adverse action request

- **`PRM_CreateAdverseActionNpdbBatch.fetchLicensesByFacility`** (lines 217–247): selects licences filtered only on the practice location — neither `LicenseClass` nor the effective date is filtered or selected.
- **`PRM_CreateAdverseActionNpdbBatch.stampLicensureFields`** (lines 254–289): the licensure payload carries only license number, state, and a `noLicense` flag. Primary vs. other licensure is decided by created-date order, not by class or effective date.
- **`PRMDRCreateOrgAdverseActionLog`** maps only the two licensure payload fields onto the adverse action log.
- **Contrast — the practitioner path does depend on License Class:** `PRM_AdverseActionLogService.loadLicenses` (lines 227–249) filters practitioner licences on `LicenseClass = 'SBRD'`. That is the Individual record-type path keyed on the person Contact, and it is **out of scope** here — but it explains why `SBRD` exists in the shared picklist and why the ancillary team does not recognise it.

### Nothing below the UI requires either value

- `BusinessLicense.LicenseClass` is a **standard picklist** with no required attribute (`objects/BusinessLicense/fields/LicenseClass.field-meta.xml`).
- `BusinessLicense.PRM_ProviderLicenseEffectiveDate__c` is explicitly `<required>false</required>` (`objects/BusinessLicense/fields/PRM_ProviderLicenseEffectiveDate__c.field-meta.xml`).
- Both write DataRaptors map both fields with `requiredForUpsert = false`, so blank values persist without error.
- There is **no `validationRules/` folder** on `BusinessLicense` in this repo — the target org still needs checking (see Clarification Question 5).
- `PRM_AncillaryProviderUtilsService` (lines 343–351, 685–693) only reads both fields into a display map — null-safe.
- The Ancillary Provider (Assessment) form (`PRM_AncillaryProviderForm_English` v43, v44 active) has **no** License Class or Effective Date input element of its own — only an error text block — so it is unaffected.

---

## Acceptance Criteria

**AC-1 — A business license saves without a License Class**

**Given** an Ancillary Cred Specialist is on the Verify Licensure step of an Ancillary PSV or Ancillary Reassessment PSV case,
**And** they have opened the Add License modal and filled in Practice Location, License Number, License State and Status (plus Verified On when Status is Verified),
**When** they leave License Class unselected and click Save,
**Then** the license is accepted and appears in the Business License table for the case,
**And** no required-field indication is shown against License Class,
**And** the Save button is enabled throughout.

---

**AC-2 — A business license saves without a Provider License Effective Date**

**Given** the Add License modal is open with Practice Location, License Number, License State and Status filled in (plus Verified On when Status is Verified),
**When** the specialist leaves Provider License Effective Date empty and clicks Save,
**Then** the license is accepted and appears in the Business License table for the case,
**And** no required-field indication is shown against Provider License Effective Date,
**And** the Save button is enabled throughout.

---

**AC-3 — A business license saves with both optional fields left blank**

**Given** the Add License modal is open with only Practice Location, License Number, License State and Status filled in,
**When** the specialist leaves both License Class and Provider License Effective Date empty and clicks Save,
**Then** the license is accepted and appears in the Business License table for the case,
**And** the Save button is enabled throughout.

---

**AC-4 — Both fields remain available and are honoured when the specialist does provide them**

**Given** the Add License modal is open with all other required details filled in,
**When** the specialist selects a License Class and enters a Provider License Effective Date, then clicks Save,
**Then** the license is accepted with both values recorded against it,
**And** the same six License Classes remain selectable as they are today, in the same order, with no change to their labels.

---

**AC-5 — Provider License Expiration Date stays usable when Effective Date is blank**

**Given** the Add License modal is open and the specialist has selected a Practice Location,
**When** they leave Provider License Effective Date empty,
**Then** the Provider License Expiration Date field is still editable and accepts a date,
**And** the Expiration Date picker imposes no earliest-date restriction carried over from the practice location,
**And** the license saves with an expiration date recorded and no effective date.

---

**AC-6 — Clearing Effective Date does not discard an Expiration Date already entered**

**Given** the specialist has entered both a Provider License Effective Date and a Provider License Expiration Date in the Add License modal,
**When** they clear the Provider License Effective Date,
**Then** the Provider License Expiration Date they entered is retained and still shown,
**And** the license saves with the expiration date recorded and no effective date.

---

**AC-7 — The date-order check applies only when both dates are entered**

**Given** the specialist has entered a Provider License Effective Date of `1/1/2020`,
**When** they enter a Provider License Expiration Date on or before that date,
**Then** the existing message *"Provider License Expiration Date must be after Provider License Effective Date."* is shown and Save is blocked,
**And** when either date is left blank, no date-order message is shown and Save is not blocked on that basis.

---

**AC-8 — Records created on Save (Ancillary PSV, Initial)**

**Given** an Ancillary Cred Specialist has added a license through the Add License modal on an Ancillary PSV case, with or without a License Class and with or without an Effective Date,
**When** they submit the form,
**Then** the following record is created exactly as specified:

**Business License — Create**

| Field | Value | Notes |
|---|---|---|
| Record Id | *(blank for a new license)* | populated only when an existing license is being updated |
| Name | {License Number} | same source as License Number |
| License Number | {License Number} | required in the modal |
| License Class | {License Class} — **blank when not selected** | no longer required; blank is a valid persisted value |
| License State | {License State} | required in the modal |
| Provider License Effective Date | {Provider License Effective Date} — **blank when not entered** | no longer required; blank is a valid persisted value |
| Provider License Expiration Date | {Provider License Expiration Date} — blank when not entered | already optional, per the sibling date-validation story |
| Status | {Status} | required in the modal |
| Verified Date | {Verified On} | set only when Status is Verified, otherwise blank |
| Account | {Facility Account} | the ancillary facility account on the case |
| Practice Location | {Practice Location} | required in the modal |
| Case Manager | {Case Manager} | the case being worked |

---

**AC-9 — Records created on Save (Ancillary Reassessment PSV)**

**Given** an Ancillary Cred Specialist has added a license through the Add License modal on an Ancillary Reassessment PSV case, with or without a License Class and with or without an Effective Date,
**When** they submit the form,
**Then** the following record is created exactly as specified:

**Business License — Create**

| Field | Value | Notes |
|---|---|---|
| Record Id | *(blank for a new license)* | populated only when an existing license is being updated |
| Name | {License Number} | mandatory on this flow's write |
| License Number | {License Number} | mandatory on this flow's write |
| License Class | {License Class} — **blank when not selected** | no longer required; blank is a valid persisted value |
| License State | {License State} | required in the modal |
| Provider License Effective Date | {Provider License Effective Date} — **blank when not entered** | no longer required; blank is a valid persisted value |
| Provider License Expiration Date | {Provider License Expiration Date} — blank when not entered | already optional, per the sibling date-validation story |
| Status | {Status} | required in the modal |
| Verified Date | {Verified On} | set only when Status is Verified, otherwise blank |
| Account | {Account} | the ancillary account on the case |
| Contact | {Person Contact} | populated on the reassessment write only |
| Healthcare Provider | {Provider} | populated on the reassessment write only |
| Practice Location | {Practice Location} | required in the modal |
| Case Manager | {Case Manager} | the case being worked |

---

**AC-10 — Duplicate licenses are still blocked, now on location, number and state**

**Given** the ancillary facility already has a license recorded for a given Practice Location with License Number `12345` and License State `PA`,
**When** the specialist tries to save another license for that same Practice Location with License Number `12345` and License State `PA` — whether or not either license carries a License Class or an Effective Date,
**Then** the save is blocked,
**And** the message reads *"A license with this License Number and License State already exists for the selected Practice Location."*,
**And** the specialist can correct the number, change the state, or pick a different Practice Location and proceed.

---

**AC-11 — Two licenses that differ only by License Class are now treated as duplicates**

**Given** the ancillary facility already has a license for a Practice Location with License Number `12345`, License State `PA` and License Class `CLIA`,
**When** the specialist tries to save a license for the same Practice Location with License Number `12345`, License State `PA` and License Class `DME Registration`,
**Then** the save is blocked with the duplicate message from AC-10,
**And** the blocking behaviour is identical whether the second license carries a class or none at all.

---

**AC-12 — The remaining required fields on the modal are still enforced**

**Given** the Add License modal is open,
**When** the specialist leaves Practice Location, License Number, License State or Status blank — or leaves Verified On blank while Status is Verified —
**Then** the Save button remains disabled,
**And** the existing required-field indication is shown against each of those fields.

---

**AC-13 — Existing licenses on the table are unchanged**

**Given** the Business License table on the Verify Licensure step lists licenses already recorded for the facility,
**When** the specialist opens one of those existing licenses,
**Then** it opens read-only exactly as it does today, with License Class and Provider License Effective Date displayed as stored (including blank),
**And** Status and Verified On remain the only editable fields on an existing license,
**And** no validation banner or required indication appears on historical licenses that have no class or no effective date.

---

**AC-14 — The ancillary NPDB adverse action request is unaffected by the blank values**

**Given** an ancillary case whose selected practice location has licenses recorded without a License Class and without a Provider License Effective Date,
**When** the Ancillary Cred Specialist submits the manual NPDB request for that case,
**Then** the adverse action request is created and carries the same licensure details it carries today — license number and state for the earliest license, and the remaining licenses as other licensure,
**And** no license is dropped from the request because it has no class or no effective date.

---

**AC-15 — The practitioner NPDB path is untouched (regression guard)**

**Given** a practitioner case where the adverse action request is built from the practitioner's own state-board licensure,
**When** that request is created,
**Then** it continues to select only state-board licenses exactly as it does today,
**And** nothing in this change alters which practitioner licenses qualify.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | Modified LWC | Remove `isLicenseClassValid` and `isEffectiveDateValid` from the `areRequiredFieldsValid` composition (lines 349, 352). Delete both now-unused getters (lines 321–323, 339–341) rather than leaving them orphaned. | Drives AC-1, AC-2, AC-3, AC-4, AC-12 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.html` | Modified LWC | Remove the `<abbr class="slds-required">` asterisk from the Provider License Effective Date label (line 177) and the License Class label (line 255). Keep both inputs and the `licenseClassOptionsWithNone` binding as-is. | Drives AC-1, AC-2, AC-4 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | Modified LWC | Relax `isExpirationDateDisabled` (lines 299–303) to return `this.isModalReadOnly` only, so Expiration Date no longer depends on Effective Date being populated. | Drives AC-5 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | Modified LWC | Remove the `ProviderLicenseExpirationDate` reset from the Effective-Date-cleared branch of `handleModalFieldChange` (lines 632–634) so clearing Effective Date no longer discards an entered expiration. | Drives AC-6 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | Modified LWC | Make `modalExpirationDateMin` (lines 219–226) return `""` when Effective Date is blank instead of falling back to `modalEffectiveDateMin`, so no practice-location floor leaks onto the Expiration picker. | Drives AC-5 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | No change | `isDateOrderValid` (lines 239–246) and `modalDateValidationError` (lines 248–258) are already null-safe — they compare only when both dates are present. Verify only. | Verifies AC-7 |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | Modified LWC | Drop `BusinessLicenseLicenseClass` from the in-memory duplicate key (lines 656–665) so the comparison is Practice Location + License Number + License State. Stop passing `licenseClass` to the server duplicate check (lines 676–691). Update both duplicate messages (lines 667–668, 688–689) to the AC-10 copy — the second currently also contains the typo *"for the selected PRMion"*. | Drives AC-10, AC-11 |
| `force-app/main/default/classes/PRM_BusinessLicenseAncNpdbController.cls` | Modified Apex | Remove the `licenseClass` parameter and its `String.isBlank` short-circuit from `checkDuplicateBusinessLicense` (lines 296–323), and drop the `classField` resolution and its SOQL predicate. The blank short-circuit is the reason a blank class silently bypasses duplicate detection today. | Drives AC-10, AC-11 |
| `force-app/main/default/classes/PRM_BusinessLicenseAncNpdbControllerTest.cls` | Modified Apex test | Update existing duplicate-check coverage for the new signature; add cases for blank-class duplicate and differing-class duplicate. | Drives AC-10, AC-11 |
| `PRMDRAncillaryPSVCreateBusinessLicense`, `PRMDRCreateAncReassessPSVBL` | DataRaptor — **no change** | Both already map License Class and the effective date with `requiredForUpsert = false`; blank values persist cleanly. Verify only. | Supports AC-8, AC-9 |
| `objects/BusinessLicense/fields/LicenseClass.field-meta.xml`, `objects/BusinessLicense/fields/PRM_ProviderLicenseEffectiveDate__c.field-meta.xml` | Object — **no change** | Standard picklist with no required attribute, and a date field explicitly `required=false`. Confirm no validation rule in the target org requires either. | Supports AC-8, AC-9 |
| `PRM_CreateAdverseActionNpdbBatch` | Apex — **no change** | Confirmed to reference neither field. Regression verification only. | Verifies AC-14 |
| `PRM_AdverseActionLogService` | Apex — **no change** | Retains its state-board filter for the practitioner path. Must not be touched. | Verifies AC-15 |
| `requirements/Ancillary_PSV_Business_Licenses_User_Story.md` | Doc amendment | Amend the duplicate-prevention section (lines 99–110) and its AC (lines 168–172) to the three-part key. Correct the field API names: `PRM_LicenseClass__c` → standard `LicenseClass` (lines 78, 93); `PRM_Status__c` → `Status`; `PRM_VerifiedOn__c` → `VerifiedDate` (lines 91–92). | Keeps the parent story truthful |
| `requirements/AncillaryPSV_BusinessLicense_DateValidation_Relax_UserStory.md` | Doc amendment | Amend the "Out of scope" note (line 131) and mark Desired Behavior item 5, AC-2, AC-4 and the final behaviour-matrix row as superseded — Effective Date is no longer required. | Resolves a direct contradiction |
| `requirements/AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` | Doc amendment | Amend AC4 (line 127) to the three-part duplicate key and cross-reference this story. | — |

---

## Definition of done

- [ ] On both Ancillary PSV and Ancillary Reassessment PSV, a business license saves with License Class unselected, with Effective Date empty, and with both blank together (AC-1, AC-2, AC-3, AC-8, AC-9)
- [ ] Neither the License Class nor the Provider License Effective Date label renders a required asterisk, and both values are still persisted when provided (AC-4)
- [ ] Provider License Expiration Date is editable and unrestricted while Effective Date is blank, and a license saves with an expiration but no effective date (AC-5)
- [ ] Clearing Effective Date leaves an already-entered Expiration Date intact (AC-6)
- [ ] The date-order message still fires when both dates are entered out of order, and never fires when either is blank (AC-7)
- [ ] Duplicate detection blocks a same-location / same-number / same-state license regardless of class, including when both are blank (AC-10, AC-11)
- [ ] Practice Location, License Number, License State, Status, and conditional Verified On all still block Save when blank (AC-12)
- [ ] Existing licenses still open read-only with only Status and Verified On editable, and no validation appears on historical licenses lacking a class or an effective date (AC-13)
- [ ] A manual ancillary NPDB request built from licenses with no class and no effective date carries the same licensure details as before, with no license dropped (AC-14)
- [ ] The practitioner adverse action path still selects only state-board licenses — verified by its existing test class passing unchanged (AC-15)
- [ ] `PRM_BusinessLicenseAncNpdbController` retains ≥ 85% coverage with the new duplicate-check cases included
- [ ] No regression on the flows listed in Impact Analysis

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Dropping License Class from the duplicate key means a facility can no longer hold two licenses that share a number and state but differ by class (e.g. a `CLIA` and a `DME Registration` issued under one number). Does that ever occur in ancillary data? If it does, the key should keep class and treat blank as a matchable value instead. | Whether AC-11 is correct behaviour or a data-entry blocker | BA / Ops |
| 2 | The BCBSA record sync maps Provider License Effective Date onto its outbound payload (`PRM_BCBSARecordSyncSubServiceHandler`, line 74). Does the downstream consumer tolerate a blank effective date, or will a class-less / date-less license fail the sync? | Could turn an accepted save into a downstream sync failure | Technical / Integration |
| 3 | Should the Provider License Effective Date input stay gated on Practice Location selection now that the date itself is optional? Current behaviour disables the input until a location is chosen; Practice Location is required regardless, so keeping the gate is harmless but it is a visible behaviour choice. | Minor UX behaviour on the modal | BA / UX |
| 4 | This story and the sibling date-validation story both edit `isExpirationDateDisabled` and `modalExpirationDateMin`. Which deploys first, or should they be merged into one change set? | Merge-conflict and double-work risk between two in-flight stories | Technical |
| 5 | Are there Salesforce validation rules or duplicate rules on `BusinessLicense` in the target org (none exist in this repo) that require License Class or Provider License Effective Date, or enforce the four-part key server-side? | Could block AC-1 / AC-2 after deployment despite the code change | Technical / Admin |
| 6 | Should existing ancillary licenses already carrying a guessed `SBRD` class or a back-filled effective date be cleaned up, or left as-is as historical record? | Whether a one-off data remediation is needed alongside this change | BA / Ops |
| 7 | Angela and Frank don't recognise `SBRD`. Now that selection is optional, is the six-value list still the right list for ancillary, or should a follow-up story trim or relabel it? | Scope of a possible follow-up; out of scope here per decision | BA / Product |
| 8 | Does any report, list view, or downstream extract for ancillary filter or group on License Class or Provider License Effective Date in a way that a blank value would break? | Reporting regression risk | BA / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `pRMBusinessLicenseAncNpdb` | LWC | HIGH | Primary change — hosts both required-field getters, both asterisks, the three Expiration/Effective couplings, and both duplicate checks; shared by both ancillary PSV flows |
| `PRM_BusinessLicenseAncNpdbController` | Apex | HIGH | Method signature change on `checkDuplicateBusinessLicense`; the LWC is its only caller |
| `PRM_BusinessLicenseAncNpdbControllerTest` | Apex test | MEDIUM | Must be updated for the new signature before deployment will pass |
| `PRM_AncillaryPSVForm_English` (v13, v14) | OmniScript | MEDIUM | Hosts the LWC element; no element change, but both active versions need regression testing |
| `PRM_AncillaryReassessmentPSV_English` (v8, v9) | OmniScript | MEDIUM | Same LWC element; both active versions need regression testing |
| `PRM_BCBSARecordSyncSubServiceHandler` | Apex | MEDIUM | Maps Provider License Effective Date outbound; blank values will now reach it — see Clarification Question 2 |
| `AncillaryPSV_BusinessLicense_DateValidation_Relax_UserStory` | In-flight story | MEDIUM | Directly contradicts this story on Effective Date, and overlaps on two getters — needs sequencing (Clarification Question 4) |
| `PRMDRAncillaryPSVCreateBusinessLicense` | DataRaptor | LOW | No change — already tolerates blank class and blank date; verify the write only |
| `PRMDRCreateAncReassessPSVBL` | DataRaptor | LOW | No change — same; note License Number is mandatory on this write and stays so |
| `PRM_AncillaryProviderUtilsService` | Apex | LOW | Reads both fields into a display map only; null-safe, no change |
| `PRM_CreateAdverseActionNpdbBatch` | Apex Batch | LOW | No change — confirmed independent of both fields; regression check only |
| `PRM_AdverseActionLogService` | Apex | LOW | No change — practitioner state-board filter must be left intact |
| `PRM_AncillaryProviderForm_English` (v43, v44) | OmniScript | NONE | No License Class or Effective Date input element; unaffected |
| `requirements/` docs (3 files) | Documentation | LOW | Duplicate-key definition, the superseded Effective Date position, and several field API names need correcting to match the build |

---

## Estimated Effort

| Component | Change Type | Effort | Story Points | Notes |
|-----------|-----------|--------|--------------|-------|
| `pRMBusinessLicenseAncNpdb.js` — required getters | LWC logic — drop two required getters from the Save gate | M | 2 | Two small, well-isolated edits |
| `pRMBusinessLicenseAncNpdb.js` — date couplings | LWC logic — relax the disable, the reset, and the min fallback | M | 2 | Three separate couplings; the reset is the one that silently loses data |
| `pRMBusinessLicenseAncNpdb.js` — duplicate key | LWC logic — rework key, fix message copy and typo | M | 2 | — |
| `pRMBusinessLicenseAncNpdb.html` | LWC template — remove two required asterisks | S | 1 | Two one-line changes |
| `PRM_BusinessLicenseAncNpdbController.cls` | Apex — signature and SOQL predicate change | M | 2 | Removes the blank-class short-circuit that hides duplicates today |
| `PRM_BusinessLicenseAncNpdbControllerTest.cls` | Apex test — update plus two new duplicate cases | M | 2 | Needed to keep the ≥ 85% gate |
| Regression testing | QA — 4 active OmniScript versions across 2 flows, one ancillary NPDB submission, one BCBSA sync check | L | 3 | Both flows share the component, so both must be walked; blank-date sync needs confirming |
| `requirements/` doc amendments (3 files) | Documentation | S | 1 | Duplicate key, superseded Effective Date position, field API-name corrections |

**Total Estimated Effort:** ~1.5–2 days — **L** overall (15 story points)
*(AI-estimated — validate with team)*

---

*Source: business feedback on the Verify Licensure step (Angela, Frank); source audit of `pRMBusinessLicenseAncNpdb`, `PRM_BusinessLicenseAncNpdbController`, `PRM_CreateAdverseActionNpdbBatch`, `PRM_AdverseActionLogService`, `PRM_AncillaryProviderUtilsService`, `PRM_BCBSARecordSyncSubServiceHandler`, `PRMDRAncillaryPSVCreateBusinessLicense`, `PRMDRCreateAncReassessPSVBL`, and the `LicenseClass` / `PRM_ProviderLicenseEffectiveDate__c` field metadata; active OmniScript versions confirmed via `isActive` on `PRM_AncillaryPSVForm_English` and `PRM_AncillaryReassessmentPSV_English`.*
