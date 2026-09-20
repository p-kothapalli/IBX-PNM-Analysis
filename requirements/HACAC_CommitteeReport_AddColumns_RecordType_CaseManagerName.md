# USER STORY: HACAC Committee Report – Add Record Type and Case Manager Name Columns

**Persona:** HACAC Committee Member / Credentialing Specialist
**Priority:** P1
**OmniScript:** `PRM_ReviewHACAC_English` (active version: `PRM_ReviewHACAC_English_3`)
**Relevant Requirements:** Sprint 53 – HACAC Committee Report Enhancement
**Vertical:** Provider Network Management (PNM)

---

## Story

**As a** HACAC Committee Member or Credentialing Specialist reviewing the HACAC Committee Report in PIE,
**I want** to see a **Record Type** column (indicating whether each facility is an Assessment or Reassessment) and a **Case Manager Name** column (showing the application ID / case name) directly in the `HACACCommitteeTable` Edit Block,
**So that** I can immediately identify the credentialing stage and application reference for each facility without opening the "View More" detail panel, improving review efficiency during HACAC Committee meetings.

**Why it matters:** Currently, the HACAC Committee table does not surface the Record Type (Assessment vs. Reassessment) or the application name/ID as visible columns. Committee members must click "View More" on each row to determine which credentialing process a facility is in and what the corresponding case identifier is. This friction slows down committee review sessions and increases the risk of misidentification. Adding these two fields as visible table columns directly addresses the committee's standing request: *"Can the HACAC Committee report in PIE identify whether the facilities are assessments or reassessments and application ID number?"*

---

## Technical Section (For Developers)

### Current State (from codebase)

- **`HACACCommitteeTable`** (Edit Block, Table mode): Defined in `PRM_ReviewHACAC_English_3.os-meta.xml`, inside the `HACACStep` step. The Edit Block has `allowEdit: true`, `editLabel: "View More"`, `mode: "Table"`, `selectMode: "Multi"`. Child elements with `disOnTplt: false` are rendered as columns in the table view; those with `disOnTplt: true` are hidden in the table but visible in the detail/edit panel.

- **`Decision`** (Formula child element, seq 2): Already uses `%HACACCommitteeTable|n:CaseManagerDeveloperName%` to branch logic between Assessment and Reassessment — confirming the `CaseManagerDeveloperName` field is available in each row's JSON.

- **`PRMDRHACACExtractCaseManagerAndRelatedData`** (DataRaptor Extract): Already extracts:
  - `CaseManager:RecordType.DeveloperName` → output `CaseManager:CaseManagerDeveloperName` (e.g., `PRM_AncillaryAssessment`, `PRM_AncillaryReAssessment`)
  - `CaseManager:RecordType.Name` → output `CaseManager:CaseManagerRecordTypeName` (e.g., `PRM Ancillary Assessment`, `PRM Ancillary ReAssessment`)
  - These fields are already flowing through `PRM_DataRetrievalforHAPACCommitteeReview` IP → `PRMDRHACACTransformData` → response mapped to OmniScript

- **`CaseManager:Name`** (IndividualApplication.Name): The `Name` field on the CaseManager (`IndividualApplication`) object is the application ID / case name (e.g., `APP-XXXXXX`). It is **not currently extracted** by `PRMDRHACACExtractCaseManagerAndRelatedData` into the OmniScript data payload.

- **`prmHACACCommitteeReviewExport`** (LWC, Custom Lightning Web Component): Receives `%HACACStep:HACACCommitteeTable%` as the `cmdata` attribute. If new columns are added to the Edit Block, the LWC export logic may also need to include the new fields in the CSV/Excel export output.

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **`PRMDRHACACExtractCaseManagerAndRelatedData`** | DataRaptor Extract | Add a new output mapping: `InputFieldName: CaseManager:Name` → `OutputFieldName: CaseManager:CaseManagerName` (OutputObjectName: `json`, OutputCreationSequence: 1). This exposes the IndividualApplication record `Name` (application ID) to the OmniScript table data. |
| **`PRMDRHACACTransformData`** | DataRaptor Transform | Verify that `CaseManagerName` flows through the transform output into the final response. If the transform uses an explicit field allowlist, add `CaseManagerName` to the passthrough mappings. |
| **`HACACCommitteeTable`** (Edit Block) – new child element | OmniScript Text element | Add a new **Text** child element named `HACACRecordType` inside `HACACCommitteeTable` with: `label: "Record Type"`, `readOnly: true`, `disOnTplt: false` (visible in table), `controlWidth: 6`. The `defaultValue` should bind to the already-available `CaseManagerRecordTypeName` field value in the row JSON. Recommended label: **"Record Type"**. |
| **`HACACCommitteeTable`** (Edit Block) – new child element | OmniScript Text element | Add a new **Text** child element named `HACACCaseManagerName` inside `HACACCommitteeTable` with: `label: "Case Manager Name"`, `readOnly: true`, `disOnTplt: false` (visible in table), `controlWidth: 6`. The value binds to the newly extracted `CaseManagerName` field. Recommended label: **"Case Manager Name"**. |
| **`prmHACACCommitteeReviewExport`** | LWC (Custom Lightning Web Component) | Review the export logic to include the two new fields (`CaseManagerRecordTypeName` / `CaseManagerName`) in the exported report columns so the CSV/Excel output matches the on-screen table. |
| **`PRM_ReviewHACAC_English_3`** | OmniScript (version bump) | After changes are validated in dev/scratch org, activate version 4 (or update version 3 if editing in place) to deploy. |

### Example – New DataRaptor Extract Item (JSON)

```json
{
    "FilterGroup": 0,
    "GlobalKey": "PRMDRHACACExtractCaseManagerAndRelatedDataCaseManagerName",
    "InputFieldName": "CaseManager:Name",
    "InputObjectQuerySequence": 0,
    "IsDisabled": false,
    "IsRequiredForUpsert": false,
    "IsUpsertKey": false,
    "LinkedObjectSequence": 0,
    "Name": "PRMDRHACACExtractCaseManagerAndRelatedData",
    "OutputCreationSequence": 1,
    "OutputFieldName": "CaseManager:CaseManagerName",
    "OutputObjectName": "json"
}
```

### Example – New OmniScript Edit Block Child Elements (JSON property configs)

```json
// HACACRecordType – Text element (Record Type column)
{
  "controlWidth": 6,
  "label": "Record Type",
  "showInputWidth": false,
  "inputWidth": 12,
  "required": false,
  "repeat": false,
  "repeatClone": false,
  "repeatLimit": null,
  "readOnly": true,
  "defaultValue": null,
  "help": false,
  "helpText": "",
  "helpTextPos": "",
  "mask": "",
  "pattern": "",
  "ptrnErrText": "",
  "minLength": 0,
  "maxLength": 255,
  "placeholder": "",
  "show": null,
  "conditionType": "Hide if False",
  "accessibleInFutureSteps": false,
  "debounceValue": 0,
  "HTMLTemplateId": "",
  "hide": false,
  "disOnTplt": false,
  "autocomplete": null
}

// HACACCaseManagerName – Text element (Case Manager Name / Application ID column)
{
  "controlWidth": 6,
  "label": "Case Manager Name",
  "showInputWidth": false,
  "inputWidth": 12,
  "required": false,
  "repeat": false,
  "repeatClone": false,
  "repeatLimit": null,
  "readOnly": true,
  "defaultValue": null,
  "help": false,
  "helpText": "",
  "helpTextPos": "",
  "mask": "",
  "pattern": "",
  "ptrnErrText": "",
  "minLength": 0,
  "maxLength": 255,
  "placeholder": "",
  "show": null,
  "conditionType": "Hide if False",
  "accessibleInFutureSteps": false,
  "debounceValue": 0,
  "HTMLTemplateId": "",
  "hide": false,
  "disOnTplt": false,
  "autocomplete": null
}
```

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| **PRMDRHACACExtractCaseManagerAndRelatedData** | DataRaptor Extract | `CaseManager:Name` (IndividualApplication.Name) | `CaseManager:CaseManagerName` (JSON output) | **Add new item** – maps the application name/ID to the OmniScript row data |
| **PRMDRHACACTransformData** | DataRaptor Transform | `CaseManagerName` (from MergedData) | Passthrough in final response | **Verify passthrough** – confirm `CaseManagerName` is not filtered out; add mapping if needed |
| **PRM_DataRetrievalforHAPACCommitteeReview** | Integration Procedure | No change to IP structure needed | `CaseManagerName` flows through as part of `DR1Output` list | **No structural change** – data flows automatically once DataRaptor is updated |

---

## Acceptance Criteria

**AC-1 – Record Type Column Visible in Table**

**Given** a HACAC Committee member opens the HACAC Committee Report OmniScript (`PRM_ReviewHACAC_English`) in PIE,
**When** the report loads and the `HACACCommitteeTable` Edit Block is displayed,
**Then** a **"Record Type"** column SHALL be visible in the table view for every row,
**And** the value SHALL display `PRM Ancillary Assessment` for Assessment records and `PRM Ancillary ReAssessment` for Reassessment records (sourced from `IndividualApplication.RecordType.Name`).

---

**AC-2 – Case Manager Name Column Visible in Table**

**Given** a HACAC Committee member opens the HACAC Committee Report OmniScript in PIE,
**When** the report loads and the `HACACCommitteeTable` Edit Block is displayed,
**Then** a **"Case Manager Name"** column SHALL be visible in the table view for every row,
**And** the value SHALL display the `IndividualApplication.Name` value (the application ID, e.g., `APP-XXXXXX`) for that case.

---

**AC-3 – Columns Are Read-Only**

**Given** the two new columns are visible in the `HACACCommitteeTable`,
**When** a user clicks "View More" on any row,
**Then** both the **"Record Type"** and **"Case Manager Name"** fields SHALL be read-only (non-editable) in the detail panel,
**And** they SHALL NOT be submittable or writable back to Salesforce.

---

**AC-4 – Export Includes New Columns**

**Given** the HACAC Committee Report table is populated with facilities,
**When** a user clicks the **Export** button (via `prmHACACCommitteeReviewExport` LWC),
**Then** the exported file (CSV/Excel) SHALL include the **"Record Type"** and **"Case Manager Name"** columns,
**And** the values SHALL match those displayed in the on-screen table.

---

**AC-5 – Both Assessment and Reassessment Record Types Are Correctly Identified**

**Given** the table contains a mix of Assessment and Reassessment cases,
**When** the "Record Type" column is rendered,
**Then** rows where `CaseManagerDeveloperName = "PRM_AncillaryAssessment"` SHALL show **"Assessment"** (or the RecordType.Name label),
**And** rows where `CaseManagerDeveloperName = "PRM_AncillaryReAssessment"` SHALL show **"Reassessment"** (or the RecordType.Name label),
**And** no row SHALL display a blank or null value in the Record Type column if the IndividualApplication has a valid RecordType.

---

**AC-6 – No Regression on Existing Columns**

**Given** the two new elements are added to the `HACACCommitteeTable` Edit Block,
**When** the OmniScript is loaded and the table renders,
**Then** all existing columns (Decision, Decision Due Date, Accrediting Body, CMS, NPI, Behavioral Health, Tax ID, etc.) SHALL continue to function as before,
**And** the Decision radio and ReAssessment Decision radio conditional show/hide logic SHALL be unaffected.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the "Record Type" column display the raw RecordType **Name** (e.g., `PRM Ancillary Assessment`) or a more user-friendly label (e.g., `Assessment` / `Reassessment`)? | Affects whether a Formula element is needed to transform the value, or if the raw `CaseManagerRecordTypeName` is sufficient | BA / Product |
| 2 | Should the "Case Manager Name" label remain as-is, or should it be renamed to **"Application ID"** or **"Application Name"** to match the business terminology? | Label only – no technical impact | BA / Business |
| 3 | Does the `PRMDRHACACTransformData` DataRaptor Transform use an explicit field allowlist, or does it pass through all fields from `MergeContentNoteswithCaseManagerData`? | If it allowlists fields, `CaseManagerName` must be explicitly added to the transform mappings | Technical / Developer |
| 4 | Should these two columns appear in the Export LWC (`prmHACACCommitteeReviewExport`)? If yes, in what column order/position? | LWC code change required | Technical / Business |
| 5 | Should the existing `CaseManagerDeveloperName` field (currently used internally for show/hide logic in the `Decision` Formula) also become a visible column, or remain hidden (`disOnTplt: true`)? | Minimal impact – `CaseManagerDeveloperName` is an internal API name and likely not user-friendly | BA |
| 6 | Are there version-specific considerations? The active OmniScript version in production is version 3; should the fix go into version 3 (in-place edit) or create a new version 4? | Deployment and testing approach | Technical / Release |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_ReviewHACAC_English_3`** (HACACCommitteeTable) | OmniScript Edit Block | **HIGH** | Two new child Text elements added; table column order may shift |
| **`PRMDRHACACExtractCaseManagerAndRelatedData`** | DataRaptor Extract | **MEDIUM** | One new extract item added for `CaseManager:Name` → `CaseManager:CaseManagerName` |
| **`PRMDRHACACTransformData`** | DataRaptor Transform | **LOW** | Verify `CaseManagerName` passes through; add mapping only if transform uses an allowlist |
| **`PRM_DataRetrievalforHAPACCommitteeReview`** | Integration Procedure | **LOW** | No structural change; data flows automatically once DataRaptor item is added |
| **`prmHACACCommitteeReviewExport`** | LWC | **MEDIUM** | Export column list may need to include the two new fields; requires LWC code review |
| **`PRM_ReviewHACAC_English_4` / `_5`** | OmniScript (other active versions) | **MEDIUM** | Versions 4 and 5 (`PRM_ReviewHACAC_English_4.os-meta.xml`, `_5`) also contain a `HACACCommitteeTable` at line 1832 — same changes should be evaluated/applied for consistency |

---

## Background / Business Context

> *"I know that we discussed this before, but can the HACAC Committee report in PIE identify whether the facilities are assessments or reassessments and application ID number? There are other items that we need on the report, but this would be very helpful for now."*
> — Business Stakeholder Request

The HACAC (Health & Ancillary Credentialing Advisory Committee) Committee Report is launched via the `PRM_ReviewHACAC_English` OmniScript. It displays a list of Ancillary provider facilities pending HACAC committee review, sourced from `IndividualApplication` (Case Manager) records via the `PRM_DataRetrievalforHAPACCommitteeReview` Integration Procedure. The committee uses this report to record Approve/Deny/Pended decisions for each facility during their meeting sessions.

Currently, the `CaseManagerDeveloperName` field (`RecordType.DeveloperName`, e.g., `PRM_AncillaryAssessment`) is **already extracted** by the DataRaptor and flows through to the OmniScript JSON — it is used internally by the `Decision` Formula element to branch between Assessment and Reassessment decision radios. However, neither `CaseManagerRecordTypeName` nor `CaseManager:Name` (the application name/ID) is currently rendered as a visible column in the table, requiring committee members to open each row individually to identify these attributes.
