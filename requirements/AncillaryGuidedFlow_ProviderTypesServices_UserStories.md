# Ancillary Guided Flow — Provider Types & Services Enhancement (User Stories)

**Feature:** Ancillary Application Guided Flow — Provider Type & Service updates
**Date:** 2026-04-30
**Requested By:** Business (PDA / Credentialing)
**Primary OmniScripts:** `PRM_AncillaryProviderForm_English` (parent, v38), `PRM_AncillaryTypesAndServices_English` (embedded, v23), `PRM_AncillaryproviderFormDocumentation_English` (embedded, v4)
**Primary Object:** `PRM_AncillaryAssessment__c`
**Related WI Reference:** W-1113370 *Ancillary Guided Flow - New Account - Record Creation (2.2)* (Closed)

---

## 1. Background & Current Architecture

The Ancillary Application is delivered through a parent OmniScript (`PRM_AncillaryProviderForm_English`) that embeds three child OmniScripts:

| Embedded Script | Purpose |
|---|---|
| `PRM_AncillaryTypesAndServices_English` (v23) | Captures Provider Types & Services and the conditional per-type sub-screens (Skilled Nursing, Sleep Study, HHA, etc.) |
| `PRM_AncillaryproviderFormDocumentation_English` (v4) | Documentation upload screen |
| `PRM_AncillarySubcontractorQMInfoScreen_English` | Subcontractor / QM info |

### How Provider Types & Services render today

1. The first screen of `PRM_AncillaryTypesAndServices` renders a parent / sub-option checkbox tree using a custom LWC: **`prmAncillaryFormTypeOptions`**.
2. The LWC pulls option metadata from the `PRM_AncillaryFormType__mdt` custom metadata via Apex `PRM_CheckboxListController.getTypeOptions(category)` (category = `AncillaryTypes`).
3. Each option is keyed by `PRM_APIName__c` (e.g., `PTSSkilledNursing`, `PTSSleepStudy`, `PTSHomeHealthAgencyAdultPediatric`). Sub-options have `PRM_ParentOption__c` set to their parent's API name (e.g., `PTSHomeHealthAgencyAdultPediatric_ChildHomePerinatal`).
4. Selections are written back to OmniScript `omniJsonData` under `AncillaryTypesAndServices` block as boolean flags (e.g., `"PTSSkilledNursing": true`).
5. Each Provider Type/Service has a **Step** (e.g., `SkilledNursingStep`, `SleepStudyStep`, `HomeHealthAgencyStep`) that is shown when its API-name flag is true.
6. The Steps display additional questions, typed inputs, radios, and reusable checkbox lists rendered by **`prmCheckboxList`** LWC. Those checkbox lists use `PRM_AncillaryFormService__mdt` records (e.g., `SkilledNursingCredentialingRequests`, `SleepStudyServices`) and write a single `SelectedValues` (`;`-delimited) string into the block.

### How data is persisted to `PRM_AncillaryAssessment__c`

1. On guided-flow submit, the parent script invokes IP `PRM_AncillaryFormRecordsCreationParent`, which calls Apex `PRM_AncillaryProviderFormDataUpdates.insertAARecords()`.
2. The class iterates every `true` key in the `AncillaryTypesAndServices` block. For each key, it loads the field-mapping JSON from custom metadata `PRM_TypesandServices__mdt.PRM_TypeandServiceMapping__c` (looked up by `PRM_TypeAndServiceName__c`).
3. The JSON map flattens screen-element paths (e.g., `"SkilledNursingStep_SkilledNursing_Facilitytype"`) to target fields (e.g., `"PRM_TypeofFacility__c"`), and one `PRM_AncillaryAssessment__c` record is created per selected Type/Service. RecordType is resolved by label (e.g., "Skilled Nursing", "Sleep Study", "Home Health Agency-Adult/Pediatric").
4. Each sub-option (e.g., `PTSHomeHealthAgencyAdultPediatric_ChildHomePerinatal`) also has its own row in `PRM_AncillaryFormType__mdt`, in `API_METHOD_MAP` (`PRM_GlobalConstant.cls`), and in `PRM_TypesandServices__mdt`, so it independently produces its own Ancillary Assessment record at submission.

### Existing fields involved in this story

| Section | OmniScript Element | Element Type | Existing AA Field | Field Type |
|---|---|---|---|---|
| Skilled Nursing | `CredentialingRequestOptions` | LWC `prmCheckboxList` (4 cols) | `PRM_CredentialingRequestFor__c` | Multi-Select Picklist |
| Skilled Nursing | `SkilledNursing_Facilitytype` | Radio | `PRM_TypeofFacility__c` | Picklist |
| Skilled Nursing | `SkilledNursing_SkilledCare`, `SkilledNursing_SubacuteMedical`, `SkilledNursing_SubacuteRehab`, `SkilledNursing_Ventilator` | Text inputs (numeric `^\d{1,4}$`, "Number of Beds" group) | `PRM_SkilledCare__c`, `PRM_SubacuteMedical__c`, `PRM_SubacuteRehabilitation__c`, `PRM_VentilatorChronicCareandorWeaning__c` | Number(10,0) |
| Sleep Study | `SleepStudy_Type` | Radio (single select, 3 options) | `PRM_TypeofFacility__c` | Picklist (shared with Skilled Nursing — 9 values total) |
| Sleep Study | `SleepStudyServiceOptions` | LWC `prmCheckboxList` | `PRM_SleepStudyServices__c` | Multi-Select Picklist |
| HHA — Provider Type screen | LWC `prmAncillaryFormTypeOptions` (parent + children) | Custom checkbox tree | (writes booleans into block; used to drive record creation) | n/a |
| Documentation | `MSG_FileSizeUpto15MB` (validation) | Validation (currently `<isActive>false</isActive>`) | n/a | n/a |
| Documentation | `ErrorMsgBlock` Text Block + `SetErrorFileValidation` Set Errors | "File must be in PDF or Excel format only and file size must not exceed 15MB." | n/a | n/a |
| Documentation | `UploadDocuments` Text Block | "Upload Attachments (Max 5 files, 15 MB Each)" | n/a | n/a |

### Verified behavior of `prmAncillaryFormTypeOptions` LWC (Provider Type checkbox tree)

- **`handleChange` (parent click)**: when a parent is unchecked, all of its sub-options are auto-unchecked (lines 76–84).
- **`handleChildChange` (child click — current bug per business)**: when a child is checked, the **parent is auto-checked** (lines 99–114). This forces a "main option" selection that the business does not want.

This is the gap that Story 3 below resolves.

### Verified behavior of file-upload validation in Documentation step (v4)

- Validation element `MSG_FileSizeUpto15MB` is already `<isActive>false</isActive>`, so the inline validator is dormant.
- However, the file-size message is **still displayed** through:
  - Text Block `ErrorMsgBlock` (active=true) showing "File must be in PDF or Excel format only and file size must not exceed 15MB." when `FileValidSuccess=false`.
  - Text Block `UploadDocuments` (active=true) showing "Upload Attachments (Max 5 files, 15 MB Each) ...".
  - Set Errors element `SetErrorFileValidation` injecting "File must be in PDF format only and file size must not exceed 15MB." into `ErrorMsgBlock`.
  - IP Action `FileValidation` calling `PRM_FileValidation` IP for server-side validation.
- File-Upload Size enhancement work (`requirements/File_Upload_Size_Increase_15MB_to_100MB.md`) is in flight; this story removes the explicit 15 MB messaging on the *Ancillary* documentation step only.

---

## 2. Scope Summary

| # | Provider Type / Screen | Change |
|---|---|---|
| US-1 | **Skilled Nursing** | Add new "Sub-Specialty Options" checkbox group below "Credentialing Request For"; persist to a new MSP field `PRM_SubSpecialtyOptions__c` |
| US-2 | **Sleep Study** | Convert "Type of Sleep Center" from single-select Radio to multi-select checkboxes; persist to a new MSP field `PRM_TypeOfSleepCenter__c`; existing `PRM_TypeofFacility__c` remains read-only on layout |
| US-3 | **Home Health Agency (Provider Type screen)** | Allow user to select Sub-Options without auto-selecting the Main Option (`prmAncillaryFormTypeOptions` LWC change) |
| US-4 | **Documentation step** | Remove file-limit text and warning message from the Ancillary documentation upload screen |

All changes are confined to:
- New OmniScript versions: `PRM_AncillaryTypesAndServices_English_24`, `PRM_AncillaryproviderFormDocumentation_English_5` (and a re-pointed parent `PRM_AncillaryProviderForm_English_39`).
- New `PRM_AncillaryAssessment__c` fields (2 net-new MSP fields).
- New / updated `PRM_AncillaryFormService__mdt` and `PRM_TypesandServices__mdt` custom-metadata records.
- One `prmAncillaryFormTypeOptions.js` behavior change.
- Two layout updates (`Skilled Nursing.layout`, `Sleep Study.layout`).
- Permission-set updates on 5 permission sets.

---

## 3. User Stories

---

### US-1 — Skilled Nursing: Add "Sub-Specialty Options" multi-select to Provider Type & Service screen

#### Story
> **As a** Provider Data Admin (PDA) or Credentialing Specialist completing the Ancillary Application for a Skilled Nursing facility,
> **I want** a new "Sub-Specialty Options" checkbox list (multi-select) directly below the existing "Credentialing Request For" checkboxes on the Skilled Nursing step,
> **so that** I can capture which sub-specialties the facility provides (Skilled Care, Subacute Medical, Subacute Rehabilitation, Ventilator – Chronic Care and/or Weaning) on the resulting Ancillary Assessment record.

#### Background
Today, the Skilled Nursing step renders the existing "Credentialing Request For" checkbox group via the `CredentialingRequestOptions` element (LWC `prmCheckboxList`, `ckbCategory = SkilledNursingCredentialingRequests`, persisted to `PRM_CredentialingRequestFor__c`). The Ancillary Assessment object also has four standalone Number fields (`PRM_SkilledCare__c`, `PRM_SubacuteMedical__c`, `PRM_SubacuteRehabilitation__c`, `PRM_VentilatorChronicCareandorWeaning__c`) that capture **bed-counts** in the "Number of Beds" section — these are intentionally **not** reused, because the new requirement is to capture **whether** each sub-specialty applies, not how many beds.

#### Acceptance Criteria

**A. New custom field on `PRM_AncillaryAssessment__c`**
1. Field Label: `Sub-Specialty Options`
2. API Name: `PRM_SubSpecialtyOptions__c`
3. Description: `Stores Sub-Specialty Options related to Ancillary Assessment`
4. Type: **Multi-Select Picklist** (restricted), `visibleLines = 4`
5. Picklist values (in this order, none default):
   - `Skilled Care`
   - `Subacute Medical`
   - `Subacute Rehabilitation`
   - `Ventilator - Chronic Care and/or Weaning`
6. Field-level security:

| Permission Set | Read | Edit |
|---|:---:|:---:|
| `PRM_ProviderDataAdmin` | ✓ | ✓ |
| `PRM_AncillaryCredSpecialist` | ✓ | ✓ |
| `PRM_CredentialingUser` | ✓ | ✓ |
| `PRM_DataViewAll` | ✓ | — |
| `PRM_DataModifyAll` | ✓ | ✓ |

> *Implementation note:* Existing `PRM_CredentialingRequestFor__c` is `readable=true` only on these permission sets (because it's populated via OmniScript and read-only on layout). The new field follows the screenshot spec verbatim ("Read/Edit" for PDA & Credentialing, "View All / Read" for `PRM_DataViewAll`, "Read/Create/Edit/View All" for `PRM_DataModifyAll`).

**B. New custom-metadata record `PRM_AncillaryFormService.SkilledNursingSubSpecialtyOptions.md-meta.xml`**

| Field | Value |
|---|---|
| `Label` | `SkilledNursing SubSpecialty Options` |
| `PRM_Category__c` | `SkilledNursingSubSpecialtyOptions` |
| `PRM_SubCategory__c` | `Sub-Specialty Options` *(used as the H2 heading rendered by `prmCheckboxList`)* |
| `PRM_CheckboxOptions__c` | `Skilled Care\|Subacute Medical\|Subacute Rehabilitation\|Ventilator - Chronic Care and/or Weaning` |
| `PRM_DisplayOrder__c` | `1.0` |

**C. OmniScript changes — `PRM_AncillaryTypesAndServices_English_24` (clone of v23)**

1. Inside `SkilledNursingStep`, add a new **Block** named `SkilledNursing_SubSpecialty` placed **immediately after** the existing `CredentialingRequestOptions` element (sequence number = 4.5 or any value strictly between current `CredentialingRequestOptions=4.0` and the next sibling).
2. Inside the new block, add a Custom Lightning Web Component element:
   - `name`: `SubSpecialtyOptions`
   - `lwcName`: `prmCheckboxList`
   - `customAttributes`:

```
numberOfColumns: "1"
ckbCategory:     "SkilledNursingSubSpecialtyOptions"
stepName:        "SkilledNursingStep"
blockName:       "SkilledNursing_SubSpecialty"
```

3. The block label (rendered above the checkboxes) MUST be `Sub-Specialty Options`. The existing "Credentialing Request For" heading (Text Block `SkilledNursingTextBlock2`, sequence ≈ 11) is unchanged.
4. The block's `show` rule is the same as the existing CredentialingRequestOptions show rule: visible only when `AncillaryTypesAndServices:PTSSkilledNursing = true` and `SkilledNursing_Facilitytype` is selected (mirror the existing CredentialingRequestOptions' conditional behavior).

> *Why a new block is required:* `prmCheckboxList` writes its result to `<blockName>.SelectedValues`. The existing `CredentialingRequestOptions` already uses `blockName = SkilledNursingStep`, so the new checkbox group must live in its own block to avoid clobbering `PRM_CredentialingRequestFor__c`.

**D. Update `PRM_TypesandServices.Skilled_Nursing.md-meta.xml` mapping JSON**

Add the following entry to `PRM_TypeandServiceMapping__c`:

```
"SkilledNursingStep_SkilledNursing_SubSpecialty_SelectedValues": "PRM_SubSpecialtyOptions__c"
```

(Path mirrors how `flattenJSON` in `PRM_AncillaryProviderFormDataUpdates.insertAARecords` walks nested blocks: Step → Block → SelectedValues.)

**E. Page-Layout update — `PRM_AncillaryAssessment__c-Skilled Nursing.layout-meta.xml`**

In the **"Skilled Nursing"** section, after the row containing `PRM_CredentialingRequestFor__c`, add a new row:

```xml
<layoutColumns>
    <layoutItems>
        <behavior>Readonly</behavior>
        <field>PRM_SubSpecialtyOptions__c</field>
    </layoutItems>
</layoutColumns>
```

Per business request, the field is **Read-Only** on layout (population is via guided flow only), placed below `PRM_TypeofFacility__c` per screenshot.

**F. Apex / Test class updates**
- `PRM_AncillaryProviderFormDataUpdatesTest.cls` — extend the Skilled Nursing test fixture JSON to include `SkilledNursing_SubSpecialty.SelectedValues = "Skilled Care;Subacute Medical"` and assert that the inserted record has `PRM_SubSpecialtyOptions__c` set to the same MSP-encoded value (`Skilled Care;Subacute Medical`). The runtime class itself needs **no Apex changes** — it is metadata-driven.

#### Definition of Done
- [ ] Field metadata, FLS, layout, custom-metadata records, OmniScript v24, type/service mapping CMD updated and deployed.
- [ ] Existing values for `PRM_CredentialingRequestFor__c` are unaffected (regression).
- [ ] On submit, when the user checks "Skilled Care" + "Ventilator – Chronic Care and/or Weaning", the resulting Ancillary Assessment has `PRM_SubSpecialtyOptions__c = Skilled Care;Ventilator - Chronic Care and/or Weaning`.
- [ ] Test class coverage ≥ 75% on touched code.
- [ ] Both new and existing Skilled Nursing apps validated end-to-end.

#### Out of Scope
- Renaming or removing the existing four bed-count Number fields (`PRM_SkilledCare__c`, `PRM_SubacuteMedical__c`, `PRM_SubacuteRehabilitation__c`, `PRM_VentilatorChronicCareandorWeaning__c`). They continue to capture bed counts in the "Number of Beds" section.
- The existing "Credentialing Request For" picklist values (`Pediatric Ventilator | Subacute Medical | Subacute Rehab | Subacute Ventilator`) remain unchanged.

---

### US-2 — Sleep Study: Convert "Type of Sleep Center" from single-select Radio to multi-select checkboxes

#### Story
> **As a** PDA / Credentialing Specialist completing the Sleep Study section of the Ancillary Application,
> **I want** to be able to select multiple "Type of Sleep Center" values (instead of being forced to pick exactly one),
> **so that** the application accurately reflects facilities that operate as more than one type (e.g., both Hospital-Based **and** Home-Based).

#### Background
The current `SleepStudy_Type` element is an OmniScript Radio with three values:

```
Freestanding Sleep Disorder Center
Hospital-Based Sleep Study Center
Home-Based Sleep Study Services
```

It maps to `PRM_TypeofFacility__c` (a restricted Picklist that today contains those three values plus six others used by Skilled Nursing / Renal / IDTF / etc.). Because `PRM_TypeofFacility__c` is shared across record types, it cannot be converted to multi-select without breaking other flows. Instead, this story introduces a **new dedicated** field for Sleep Study and converts the OmniScript control to multi-select.

#### Acceptance Criteria

**A. New custom field on `PRM_AncillaryAssessment__c`**
1. Field Label: `Type of Sleep Center`
2. API Name: `PRM_TypeOfSleepCenter__c`
3. Description: `Stores Type of Sleep Center`
4. Type: **Multi-Select Picklist** (restricted), `visibleLines = 3`
5. Picklist values (none default):
   - `Freestanding Sleep Disorder Center`
   - `Hospital-Based Sleep Study Center`
   - `Home-Based Sleep Study Services`
6. Field-level security: same matrix as US-1 §A.6 (Read/Edit on PDA & Credentialing PSets, Read on `PRM_DataViewAll`, Create/Read/Edit on `PRM_DataModifyAll`).

**B. New custom-metadata record `PRM_AncillaryFormService.SleepStudyTypeOfCenter.md-meta.xml`**

| Field | Value |
|---|---|
| `Label` | `SleepStudy Type Of Sleep Center` |
| `PRM_Category__c` | `SleepStudyTypeOfCenter` |
| `PRM_SubCategory__c` | `Type of Sleep Center` |
| `PRM_CheckboxOptions__c` | `Freestanding Sleep Disorder Center\|Hospital-Based Sleep Study Center\|Home-Based Sleep Study Services` |
| `PRM_DisplayOrder__c` | `1.0` |

**C. OmniScript changes — `PRM_AncillaryTypesAndServices_English_24`**
1. Replace the existing `SleepStudy_Type` Radio element with a new **Block** named `SleepStudy_TypeOfCenter`, parented to `SleepStudyStep`, sequence number = current `SleepStudy_Type` sequence (`0.0`).
2. Inside the block, add a Custom Lightning Web Component element using `prmCheckboxList`:

```
name:            "TypeOfSleepCenterOptions"
lwcName:         "prmCheckboxList"
numberOfColumns: "1"
ckbCategory:     "SleepStudyTypeOfCenter"
stepName:        "SleepStudyStep"
blockName:       "SleepStudy_TypeOfCenter"
```

3. The block label rendered above the checkboxes MUST be `Type of Sleep Center`.
4. Mark the original Radio element `SleepStudy_Type` as `<isActive>false</isActive>` (do **not** delete) so historical version comparisons remain readable.

> *Implementation alternative:* If product prefers, replace `SleepStudy_Type` directly with an OmniScript "Multi-select" element of type `MultiSelect` and inline the three options. The team should pick the LWC-driven option for **consistency with `SleepStudyServiceOptions`** already on the same step (both reuse `prmCheckboxList` and write `SelectedValues`).

**D. Update `PRM_TypesandServices.Sleep_Study.md-meta.xml` mapping JSON**

1. **Remove** the existing entry:
   ```
   "SleepStudyStep_SleepStudy_Type": "PRM_TypeofFacility__c"
   ```
2. **Add** the new entry:
   ```
   "SleepStudyStep_SleepStudy_TypeOfCenter_SelectedValues": "PRM_TypeOfSleepCenter__c"
   ```

`PRM_TypeofFacility__c` will no longer be written by the Sleep Study guided flow; it remains valid (read-only on layout) for legacy records and other record types.

**E. Page-Layout update — `PRM_AncillaryAssessment__c-Sleep Study.layout-meta.xml`**

1. Existing field `PRM_TypeofFacility__c` (currently `Readonly` in the "Type of Facility" section) must remain on the layout but stay `Readonly` (per screenshot: "Replaces 'Type of Facility' on Sleep Study Page Layout as Read-Only" — interpreted as "the *new* multi-select field replaces the legacy field on the layout for *write* purposes; the legacy field stays visible Read-Only").
2. Add `PRM_TypeOfSleepCenter__c` directly above `PRM_TypeofFacility__c` (or in the same section) with `Readonly`:

```xml
<layoutItems>
    <behavior>Readonly</behavior>
    <field>PRM_TypeOfSleepCenter__c</field>
</layoutItems>
```

**F. Apex / Test class updates**
- `PRM_AncillaryProviderFormDataUpdatesTest.cls` — extend the Sleep Study fixture JSON to include `SleepStudy_TypeOfCenter.SelectedValues = "Freestanding Sleep Disorder Center;Home-Based Sleep Study Services"`; assert the inserted Ancillary Assessment record has the same MSP-encoded value on `PRM_TypeOfSleepCenter__c` and that **`PRM_TypeofFacility__c` is left null** for new submissions.

#### Definition of Done
- [ ] User can select multiple values; selection persists on revisit; submit-flow writes correctly to `PRM_TypeOfSleepCenter__c`.
- [ ] Existing Sleep Study Ancillary Assessment records still display correctly (legacy `PRM_TypeofFacility__c` values intact, read-only).
- [ ] Reports and dashboards using `PRM_TypeofFacility__c` are reviewed; if any pivot Sleep Study by facility type, they are repointed to `PRM_TypeOfSleepCenter__c` with proper MSP filter (`includes`).
- [ ] Test coverage maintained.

#### Open Questions for Business
- **Q1:** Should historical Sleep Study records have `PRM_TypeOfSleepCenter__c` back-filled from `PRM_TypeofFacility__c`? (Recommend: yes — one-time `apex script` or DataRaptor-based migration covering all `PRM_AncillaryAssessment__c` records where `RecordType.DeveloperName = 'Sleep_Study'` and `PRM_TypeofFacility__c` is in the 3 sleep values.)
- **Q2:** Should reassessment / PSV / QC flows that read `PRM_TypeofFacility__c` for Sleep Study also be updated? See US-2a below.

#### US-2a (sub-task, deferred unless Q2 = yes) — Reassessment / PSV / QC flows
Update read-side OmniScripts (`PRM_AncillaryReassessmentPSV_English_8`, `PRM_AncillaryPSVForm_English_10`, `PRM_AncillaryQC_English_2`) to display `PRM_TypeOfSleepCenter__c` instead of `PRM_TypeofFacility__c` for the Sleep Study record type. Estimated additional effort if scoped: ½ day.

---

### US-3 — Home Health Agency: Allow Sub-Option selection without Main Option auto-check

#### Story
> **As a** PDA / Credentialing Specialist completing the Ancillary Application,
> **I want** to be able to select an HHA Sub-Option (Home Perinatal, Mother's Option, or Private Duty Nursing) **without** the parent "Home Health Agency-Adult/Pediatric" checkbox being auto-selected,
> **so that** I can credential a facility that only provides one sub-service (e.g., Mother's Option) without forcing the parent record-type to be created when it does not apply.

#### Background
Provider Types & Services on the first screen of `PRM_AncillaryTypesAndServices` are rendered by **`prmAncillaryFormTypeOptions`** LWC. The Home Health Agency-Adult/Pediatric option (`PTSHomeHealthAgencyAdultPediatric`) is the parent of three child checkboxes (Home Perinatal, Mother's Option, Private Duty Nursing). Inspection of `prmAncillaryFormTypeOptions.js` `handleChildChange()` (lines 93–124) confirms that **when a child is checked, the parent is force-checked** by:

```js
let parentCheckbox = this.template.querySelector('[data-id="' + parentId + '"]');
if (parentCheckbox) {
    parentCheckbox.checked = true;
    if (!this.selectedValues.includes(parentId)) {
        this.selectedValues = [...this.selectedValues, parentId];
    }
    ...
}
```

The same pattern is also applied to the Ambulatory-Surgery-Center → Lithotripsy and DME → Orthotics & Prosthetics sub-option pairs. Confirm with business whether this story applies to **all** parent / sub-option pairs or **HHA-only**.

The downstream Apex (`PRM_AncillaryProviderFormDataUpdates.insertAARecords`, `PRM_GlobalConstant.API_METHOD_MAP` & `SUBTYPESSET`) **already supports** sub-options being selected without their parent — each sub-option (`PTSHomeHealthAgencyAdultPediatric_ChildHomePerinatal`, `…_ChildMothersOption`, `…_ChildPrivateDutyNursing`) is independently keyed in `API_METHOD_MAP` and produces its own `PRM_AncillaryAssessment__c` record (`SUBTYPESSET` includes 'Home Perinatal', 'Mother's Option', 'Private Duty Nursing'). This is the persistence behavior delivered under **W-1113370 (Closed)**, which the screenshot references. **Therefore Story 3 is purely a UI/LWC change.**

#### Acceptance Criteria

**A. LWC change — `prmAncillaryFormTypeOptions.js`**

1. Modify `handleChildChange(event)` so that when a child checkbox is checked, the parent checkbox is **NOT** automatically checked, and the parent's API name is **NOT** added to `selectedValues`.
2. Updated method body (illustrative):

```javascript
handleChildChange(event) {
    try {
        const checkedValue = event.target.value;
        const checkedLabel = event.target.label;
        if (event.target.checked) {
            if (!this.selectedValues.includes(checkedValue)) {
                this.selectedValues = [...this.selectedValues, checkedValue];
            }
            if (checkedValue.startsWith('PTS') && !this.selectedOptionLabels.includes(checkedLabel)) {
                this.selectedOptionLabels = [...this.selectedOptionLabels, checkedLabel];
            }
        } else {
            this.selectedValues = this.selectedValues.filter(v => v !== checkedValue);
            this.selectedOptionLabels = this.selectedOptionLabels.filter(v => v !== checkedLabel);
        }
        this.sendDataToOmniscript();
    } catch (e) {
        this.logError('Error', 'Something went wrong!', { errorMessage: e?.message, stackTrace: e?.stack, exceptionType: e?.name, processName: 'prmAncillaryFormTypeOptions.js' });
    }
}
```

3. **Retain** the existing parent → child cascade in `handleChange()`: when a parent is **un**checked, all its children are unchecked. (This prevents "orphan" selected children when the user explicitly removes the parent. Confirm with business.)
4. **Retain** the existing rule that re-checking a parent does **not** auto-check children (no change to `handleChange`).

**B. OmniScript change — none required.** Existing element `PTSHomeHealthAgencyAdultPediatric` and its children remain wired the same way; the cascading behavior is purely client-side LWC logic.

**C. Apex change — none required.** Validate existing behavior in `PRM_AncillaryProviderFormDataUpdates.insertAARecords` for `Home Perinatal -only`, `Mother's Option -only`, and `Private Duty Nursing -only` submissions.

**D. Visual / UX**
- Children render with the existing left-padding/indent under the parent (`padding-left: 12px`, see `prmAncillaryFormTypeOptions.html` line 12).
- No change to the parent's appearance.

**E. Cross-flow reuse confirmation (per W-1113370 architecture)**
- Confirm that `PRM_AncillaryFormType__mdt` rows (`Home Perinatal`, `Mothers_Option`, `Private Duty Nursing`) are still active.
- Confirm `PRM_TypesandServices__mdt` rows for those three sub-options exist with full mapping JSON (`Home_Perinatal`, `Mother_s_Option`, `Private_Duty_Nursing`) — already verified during analysis.
- Confirm record-types `Home Perinatal`, `Mother's Option`, `Private Duty Nursing` exist on `PRM_AncillaryAssessment__c` — they each have a corresponding page layout (`PRM_AncillaryAssessment__c-Home Perinatal.layout-meta.xml`, etc.).

**F. Jest test additions**
- Add Jest tests for `prmAncillaryFormTypeOptions` covering:
  - Checking `Home Perinatal` does NOT add `PTSHomeHealthAgencyAdultPediatric` to `selectedValues` and does NOT toggle the parent checkbox in the DOM.
  - The OmniScript payload sent via `omniApplyCallResp` contains exactly `{"<blockName>": {"PTSHomeHealthAgencyAdultPediatric_ChildHomePerinatal": true, "SelectedOptions": "Home Perinatal"}}`.
  - Unchecking the parent (with one child checked) cascades to uncheck the child (regression).

#### Definition of Done
- [ ] LWC update deployed; Jest unit tests pass.
- [ ] Manual end-to-end on three scenarios:
  - "Mother's Option" only → parent record NOT created; one Ancillary Assessment record created with `RecordType = Mother's Option`.
  - "Home Perinatal" + "Private Duty Nursing" → no parent; two AA records created.
  - "Home Health Agency-Adult/Pediatric" + "Home Perinatal" → both selections produce records (regression — backward compatible).
- [ ] Cross-flow regression: same LWC is reused for ASC → Lithotripsy and DME → Orthotics. Verify those flows still work for both "child-only" and "parent + child" scenarios per business decision.

#### Open Question for Business
- **Q1:** Does this change apply **HHA-only** or to **all** parent/sub-option groups (HHA, ASC → Lithotripsy, DME → Orthotics & Prosthetics)? Recommend applying globally for consistency, since the LWC is shared. Default assumption in this story: **all groups** (HHA-only would require LWC config to scope behavior by parent API name).

---

### US-4 — Documentation step: Remove file-limit text and warning message

#### Story
> **As an** Ancillary applicant uploading documents on the Documentation step,
> **I want** the file-limit text ("Max 5 files, 15 MB Each") and the file-size error message ("File must be in PDF or Excel format only and file size must not exceed 15MB.") to be removed from the screen,
> **so that** the UI matches the upcoming new file-size limits and is no longer cluttered with stale guidance text.

#### Background
The Documentation step (`PRM_AncillaryproviderFormDocumentation_English_4`) currently exposes the 15 MB limit in three places:
1. Text Block `UploadDocuments` (sequence 39, active=true) — `<p><strong>Upload Attachments (Max 5 files, 15 MB Each)</strong></p>...`
2. Text Block `ErrorMsgBlock` (sequence 41, active=true, conditional `FileValidSuccess = false`) — the red banner saying *"File must be in PDF or Excel format only and file size must not exceed 15MB."*
3. Set Errors element `SetErrorFileValidation` (sequence 3, active=true) — injects *"File must be in PDF format only and file size must not exceed 15MB."* into `ErrorMsgBlock`.

The validation element `MSG_FileSizeUpto15MB` is already inactive (`<isActive>false</isActive>`), so no inline form-level validator fires today.

#### Acceptance Criteria

**A. OmniScript changes — `PRM_AncillaryproviderFormDocumentation_English_5` (clone of v4)**

1. Edit `UploadDocuments` Text Block `text` to remove "Max 5 files, 15 MB Each":
   - From: `<p><strong>Upload Attachments (Max 5 files, 15 MB Each)</strong></p>...`
   - To: `<p><strong>Upload Attachments</strong></p>...` *(retain bullet list for "compile into 1 PDF/Excel" and "attach all required documentation").*
2. **Remove the file-size warning** by either:
   - **Option A (recommended, minimal-risk):** Set `ErrorMsgBlock` `<isActive>false</isActive>` and `SetErrorFileValidation` `<isActive>false</isActive>`. This preserves the elements for audit history without rendering them.
   - **Option B:** Edit `SetErrorFileValidation.elementErrorMap.ErrorMsgBlock` to a generic message like `Please upload a valid file.` and edit `ErrorMsgBlock.text` to `<div>...</div>` with the same generic message.
   - Choose Option A unless the business wants a different replacement message; document the choice in the work item.
3. Confirm that the upstream IP `PRM_FileValidation` is not relied on for actual size enforcement on this screen. If size enforcement is still required server-side under different limits, that work belongs to `requirements/File_Upload_Size_Increase_15MB_to_100MB.md` and is **out of scope here**.

**B. Parent script update**
- Activate `PRM_AncillaryProviderForm_English_39` (clone of v38) repointing the embedded `AncillaryproviderFormDocumentation` element to `PRM|AncillaryproviderFormDocumentation|English` v5 (Vlocity manages this via active version automatically; no JSON change is typically needed if the existing version is bumped — confirm with the OmniStudio admin).

**C. Visual QA**
- Documentation step renders without "Max 5 files, 15 MB Each" anywhere.
- Upload still works for currently-supported file types and sizes (the actual server-side limit is governed elsewhere).
- No red banner appears when valid files are uploaded.
- Negative test: when an invalid file is uploaded, the user receives an appropriate error path (either a blank/generic banner if Option A — `ErrorMsgBlock` not rendered — or a generic message if Option B).

#### Definition of Done
- [ ] OmniScript v5 active; v4 deactivated.
- [ ] Manual smoke test for happy path (PDF ≤ supported size).
- [ ] Manual smoke test for invalid file (oversized / wrong format) — verify behavior matches chosen option.
- [ ] Coordinated with the file-size-increase initiative (see Cross-Story Dependencies).

#### Open Question for Business
- **Q1:** Confirm whether Option A (banner removed entirely) or Option B (generic banner) is preferred.
- **Q2:** Should we coordinate the activation of v5 with `File_Upload_Size_Increase_15MB_to_100MB.md` so that messaging never lags actual limits?

---

## 4. Cross-Story Dependencies & Sequencing

| Dependency | From → To | Note |
|---|---|---|
| US-1 → Skilled Nursing layout | New field must exist in object before layout can reference it | Deploy field/CMD → layout in same package |
| US-2 → Sleep Study layout | New field must exist before layout can reference it | Same as above |
| US-2 → Reporting | If reports filter on `PRM_TypeofFacility__c`, retag MSP filter | Owners: Reporting team |
| US-3 → US-1, US-2 | None — independent | LWC change is isolated |
| US-4 → File_Upload_Size_Increase_15MB_to_100MB | Sequence: deploy US-4 only **after** the new size limits are live (or simultaneously) so the UI never shows guidance that contradicts enforcement | Coordinate with that work item |
| All four | OmniScript versioning | Activate new versions atomically post-deploy; deactivate predecessors only after smoke tests |

---

## 5. Test Strategy

### Functional Tests (per story)
- **US-1, US-2:** OmniScript end-to-end submit; assert resulting `PRM_AncillaryAssessment__c` field values via `Database.query` in test class fixtures.
- **US-3:** Three submit-paths (parent-only, child-only, parent+child) for HHA. Repeat for ASC/DME if applicable.
- **US-4:** Smoke test happy + invalid uploads.

### Regression Tests (whole flow)
- Submit a complete Ancillary Application end-to-end with **each** record type at least once: Skilled Nursing, Sleep Study, HHA + sub-options, Hospital, Hospice, Ambulance, IDTF, Renal Dialysis Center, DME + Orthotics, Birth Center, Cardiac Monitoring, Clinical Lab. Confirm the `PRM_AncillaryAssessment__c` records created have the expected RecordType, and required fields are populated.
- Reassessment & PSV flows still load Skilled Nursing and Sleep Study records correctly.

### QTA / Automation
- If QTA suites exist for "Ancillary New Account" guided flow, extend with one new test case per story (4 total).
- Add Jest tests for `prmAncillaryFormTypeOptions` per US-3 §F.

### Permissions / FLS Tests
- Each persona (PDA, Credentialing Specialist, ReCredentialing User, Compliance) sees the new fields with the correct CRUD per US-1 §A.6 and US-2 §A.6.

---

## 6. Effort Estimate (rough order of magnitude)

| Story | Build (dev-days) | QA (days) | Total |
|---|---:|---:|---:|
| US-1 — Skilled Nursing Sub-Specialty Options | 1.5 | 1.0 | **2.5** |
| US-2 — Sleep Study Multi-Select | 1.5 | 1.0 | **2.5** |
| US-3 — HHA decouple parent/child (LWC) | 1.0 | 1.0 | **2.0** |
| US-4 — Doc step text/warning removal | 0.5 | 0.5 | **1.0** |
| Cross-cutting regression / deployment | — | 1.0 | **1.0** |
| **Grand Total** | **4.5** | **4.5** | **9.0 person-days** |

(Assumes one Salesforce engineer + one QA. Excludes US-2a back-fill migration if pursued.)

---

## 7. Open Questions Consolidated (please confirm with business)

1. **US-1:** Confirm field-level security spec (Read/Edit on PDA & Credentialing PSets, etc.) matches latest enterprise security review — the current matrix is per the screenshot.
2. **US-2 / Q1:** Back-fill `PRM_TypeOfSleepCenter__c` from legacy `PRM_TypeofFacility__c`? (One-time data migration.)
3. **US-2 / Q2:** Update Reassessment, PSV, QC flows to consume the new field? (US-2a sub-task scope.)
4. **US-3 / Q1:** Apply HHA-only or globally to all parent/sub-option pairs?
5. **US-4 / Q1, Q2:** Banner removal strategy (Option A vs. Option B) and coordination with file-size increase work item.

---

## 8. Component Inventory (for impact assessment / code review)

| Layer | Component | Change Type |
|---|---|---|
| Object/Field | `PRM_AncillaryAssessment__c.PRM_SubSpecialtyOptions__c` | **NEW** (US-1) |
| Object/Field | `PRM_AncillaryAssessment__c.PRM_TypeOfSleepCenter__c` | **NEW** (US-2) |
| Custom Metadata | `PRM_AncillaryFormService.SkilledNursingSubSpecialtyOptions` | **NEW** (US-1) |
| Custom Metadata | `PRM_AncillaryFormService.SleepStudyTypeOfCenter` | **NEW** (US-2) |
| Custom Metadata | `PRM_TypesandServices.Skilled_Nursing` | **EDIT** (US-1) — extend mapping JSON |
| Custom Metadata | `PRM_TypesandServices.Sleep_Study` | **EDIT** (US-2) — swap mapping JSON entry |
| OmniScript | `PRM_AncillaryTypesAndServices_English_24` | **NEW** (US-1, US-2) |
| OmniScript | `PRM_AncillaryproviderFormDocumentation_English_5` | **NEW** (US-4) |
| OmniScript | `PRM_AncillaryProviderForm_English_39` | **NEW** (parent re-pointer) |
| LWC | `prmAncillaryFormTypeOptions.js` | **EDIT** (US-3) — modify `handleChildChange` |
| Apex | `PRM_AncillaryProviderFormDataUpdatesTest` | **EDIT** — add fixtures (US-1, US-2) |
| Layout | `PRM_AncillaryAssessment__c-Skilled Nursing.layout` | **EDIT** (US-1) |
| Layout | `PRM_AncillaryAssessment__c-Sleep Study.layout` | **EDIT** (US-2) |
| Permission Set | `PRM_ProviderDataAdmin`, `PRM_AncillaryCredSpecialist`, `PRM_CredentialingUser`, `PRM_DataViewAll`, `PRM_DataModifyAll` | **EDIT** — add FLS for two new fields |

---

*Prepared by: Cursor analysis of `force-app/main/default/omniScripts/PRM_AncillaryTypesAndServices_English_23.os-meta.xml`, `PRM_AncillaryproviderFormDocumentation_English_4.os-meta.xml`, `PRM_AncillaryProviderForm_English_38.os-meta.xml`, `PRM_AncillaryProviderFormDataUpdates.cls`, `PRM_GlobalConstant.cls`, `prmAncillaryFormTypeOptions.js`, `prmCheckboxList.js`, and the related `PRM_AncillaryAssessment__c` field metadata, layouts, custom-metadata records, and permission sets. Cross-references to W-1113370 confirmed against `SUBTYPESSET` comment in `PRM_GlobalConstant.cls` (line 116).*
