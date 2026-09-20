# USER STORY 1: Add "Medical Director Review" Column to Case Manager Report Type

**Persona:** Credentialing Specialist / Medical Director / Reporting Analyst, Developer
**Priority:** P2
**OmniScript:** N/A (report type metadata change)
**Integration Procedures:** N/A
**Relevant Requirements:** Sprint enhancement — reporting parity for Medical Director Review outcomes across Case Manager report types
**Vertical:** Provider Network Management (PNM)

---

## Story

**As a** Credentialing Specialist (and Medical Director / Reporting Analyst) building reports off of the **Case Manager Report Type**,
**I want** the **`Medical Director Review` (`PRM_MedicalDirectorReview__c`)** field on `IndividualApplication` (Case Manager) exposed as a selectable column,
**So that** I can include the Medical Director Review outcome on Case Manager reports without resorting to a different report type or building a custom one.

**Why it matters:** The Medical Director Review outcome is captured on every credentialing case manager record and is required for committee/escalation reporting. Today, three of the four Case Manager-based report types (`Case Manager with Cases`, `Case Manager with Accounts`, `Case Manager w/ Cases`) already expose this field, but the canonical **Case Manager Report Type** (`PRM_CaseManagerReportType`) does not. Users running off the canonical report type cannot pull the Medical Director Review value, forcing workarounds and inconsistent reporting across teams.

---

## Scope

| Flow | Report Type | Affected Section | Data Source |
|------|------------|------------------|-------------|
| Reporting | `PRM_CaseManagerReportType` (label: "Case Manager Report Type") | `Individual Applications` section | `IndividualApplication.PRM_MedicalDirectorReview__c` |

---

## Current State (from codebase)

### `PRM_CaseManagerReportType.reportType-meta.xml`

- **Base object:** `IndividualApplication`
- **Label:** `Case Manager Report Type`
- **Description:** "This report is for Case Manager Object"
- **Sections:**
  - `Individual Applications` — contains ~50+ `IndividualApplication` columns (Id, Name, RecordType, CreatedDate, Account, ApplicationCase, PRM_Stage__c, PRM_NPDBVerification__c, PRM_OIGReviewOutcome__c, PRM_CaseManagerAge__c, etc.)
  - `Case Managers` — contains a single column `PRM_DenialReason__c`
- **`PRM_MedicalDirectorReview__c` is NOT currently listed in either section.**
- **Location:** `force-app/main/default/reportTypes/PRM_CaseManagerReportType.reportType-meta.xml`

### Field — already exists on `IndividualApplication`

- **`PRM_MedicalDirectorReview__c`** — "Medical Director Review" (custom field on `IndividualApplication`).
- Translation present at `force-app/main/default/objectTranslations/IndividualApplication-en_US/PRM_MedicalDirectorReview__c.fieldTranslation-meta.xml`.
- Already exposed in the following report types (precedent for adding it here):
  - `PRM_CaseManagerwithCases.reportType-meta.xml` (line 640) — section "Case Managers"
  - `Case_Manager_with_Accounts.reportType-meta.xml` (line 640) — section "Case Managers"
  - `Case_Manager_w_Cases.reportType-meta.xml` (line 640) — section "Case Managers"
- Already exposed on layouts: `IndividualApplication-Re-credentialing Layout`, `IndividualApplication-Practitioner Participation Request Layout`.
- Field-level security: confirm the field is granted on `PRM_CredentialingUser`, `PRM_NetworkManagementQC`, `PRM_DataViewAll`, `PRM_DataModifyAll`, `PRM_AncillaryCredSpecialist`, `PRM_RebtuttalSpecialist`, `PRM_ProviderDataAdmin`, `PRM Credentialing`, `PRM Business Admin`, and `PRM PDM` (these already reference the field — see Grep results).

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_CaseManagerReportType`** | Custom Report Type (metadata) | Add a new `<columns>` entry exposing `PRM_MedicalDirectorReview__c` from the `IndividualApplication` table. Place it in the existing `Individual Applications` section (or in the `Case Managers` section — see Clarification Q1) with `<checkedByDefault>false</checkedByDefault>`. |
| **`PRM_CaseManagerReportType`** (post-deploy validation) | Reporting / FLS | Verify all profiles/permission sets that reference `PRM_MedicalDirectorReview__c` still have read access; no new FLS work expected since the field is already widely permissioned. |

### Exact metadata snippet to add

Add the following `<columns>` block inside `PRM_CaseManagerReportType.reportType-meta.xml`. Place it adjacent to the other `IndividualApplication` review-outcome fields (e.g., directly after `PRM_OIGReviewOutcome__c` near line ~228) within the `<masterLabel>Individual Applications</masterLabel>` section, **OR** add it inside the `<masterLabel>Case Managers</masterLabel>` section next to `PRM_DenialReason__c` to mirror placement in the other three Case Manager report types — confirm preferred placement in Clarification Q1.

```xml
<columns>
    <checkedByDefault>false</checkedByDefault>
    <field>PRM_MedicalDirectorReview__c</field>
    <table>IndividualApplication</table>
</columns>
```

### Reference — placement in existing Case Manager report types

In `PRM_CaseManagerwithCases.reportType-meta.xml`, `Case_Manager_with_Accounts.reportType-meta.xml`, and `Case_Manager_w_Cases.reportType-meta.xml`, the field appears in the `Case Managers` section in this neighborhood:

```638:642:force-app/main/default/reportTypes/PRM_CaseManagerwithCases.reportType-meta.xml
        <columns>
            <checkedByDefault>false</checkedByDefault>
            <field>PRM_MedicalDirectorReview__c</field>
            <table>IndividualApplication</table>
        </columns>
```

### Deployment

- Deploy via SFDX: `sf project deploy start -m "ReportType:PRM_CaseManagerReportType"`.
- No data migration, Apex, OmniScript, IP, DataRaptor, or LWC change required.

---

## Acceptance Criteria

**AC-1 – Field is selectable in the Case Manager Report Type**

**Given** a user with the `PRM Credentialing` profile (or any profile/permission set that already has read access to `PRM_MedicalDirectorReview__c`) navigates to **Reports → New Report**,
**When** they select the **"Case Manager Report Type"** report type and enter the report builder,
**Then** the **"Medical Director Review"** field SHALL appear in the Fields panel under the Case Manager (`IndividualApplication`) section,
**And** dragging it into the report SHALL render the picklist value (or blank, if unset) for each row.

---

**AC-2 – Field is unchecked by default**

**Given** the metadata change is deployed,
**When** a user opens the report builder for the Case Manager Report Type,
**Then** **"Medical Director Review"** SHALL NOT be pre-added to the default report layout (`checkedByDefault = false`),
**And** existing reports built on this report type SHALL continue to render unchanged (no auto-injected column).

---

**AC-3 – Filterable and groupable**

**Given** the field is added to a Case Manager Report Type report,
**When** a user adds a **filter** (e.g., `Medical Director Review = "Approved"`) or a **grouping** by Medical Director Review,
**Then** the report SHALL execute successfully and return rows whose `PRM_MedicalDirectorReview__c` matches the criterion.

---

**AC-4 – No regression to existing reports built on this report type**

**Given** any existing saved report (Lightning report or dashboard component) built on `PRM_CaseManagerReportType`,
**When** the metadata change is deployed,
**Then** the report SHALL continue to load and run with the same columns, filters, and groupings as before deployment,
**And** no schema/metadata error SHALL be raised in the report builder.

---

**AC-5 – FLS respected**

**Given** a user without read access to `PRM_MedicalDirectorReview__c` (e.g., a profile not in the access list),
**When** they open the Case Manager Report Type in the report builder,
**Then** the **"Medical Director Review"** field SHALL NOT be visible in the Fields panel (Salesforce default FLS behavior),
**And** any prior report containing the column SHALL render the column as blank for that user.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should `PRM_MedicalDirectorReview__c` be added to the `Individual Applications` section (next to other review fields like `PRM_OIGReviewOutcome__c`) or to the `Case Managers` section (next to `PRM_DenialReason__c`, mirroring the other three Case Manager report types)? | Section placement determines where users find the field in the report builder; mirroring existing report types favors the `Case Managers` section. | BA / Reporting Lead |
| 2 | Is the target report type really **`PRM_CaseManagerReportType`** (label "Case Manager Report Type"), or did you mean **`PRM_CaseManagerwithCases`**, **`Case_Manager_with_Accounts`**, or **`Case_Manager_w_Cases`**? Note: those three already expose `PRM_MedicalDirectorReview__c`; only `PRM_CaseManagerReportType` is missing it. | If a different report type is intended, the change is a no-op; story scope shifts. | Product / BA |
| 3 | Are there other commonly-requested review fields (e.g., `PRM_RebuttalOutcome__c`, `PRM_QMReviewOutcome__c`, `PRM_PSVOutcome__c`, `PRM_PDAUpdateOutcome__c`, `PRM_NonParFormQCOutcome__c`) that should also be added to `PRM_CaseManagerReportType` in the same change to bring it to parity with the other three Case Manager report types? | Could expand scope to a single "report type field-parity" story instead of one-field-at-a-time. | BA / Reporting Lead |
| 4 | Does the `checkedByDefault` value need to be `true` (auto-shown when a new report is created) or `false` (user opt-in)? Existing report types use `false`. | UX behavior in report builder default state. | BA |
| 5 | Should this also be reflected in any analytics/CRMA dataset, list view, or downstream BI feed that consumes report metadata? | If yes, add downstream artifacts to the change set. | Analytics / Data Eng |
| 6 | Is there an existing W-number/GUS work item for this enhancement, or should one be created and linked to this story? | Tracking and PR reference. | Product / Scrum Master |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_CaseManagerReportType`** | Custom Report Type | **LOW** | Single `<columns>` element added; no schema, FLS, OmniScript, IP, DataRaptor, Apex, or LWC change required. |
| Existing reports built on this report type | Saved Reports / Dashboards | **LOW** | Backward-compatible; new field is opt-in. No re-save required. |
| Profiles & Permission Sets | FLS | **NONE** | Field already permissioned; no changes needed. |
| `PRM_CaseManagerwithCases`, `Case_Manager_with_Accounts`, `Case_Manager_w_Cases` | Other Case Manager Report Types | **NONE** | Already expose the field; no change. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|------------|--------|-------|
| `PRM_CaseManagerReportType.reportType-meta.xml` | Add one `<columns>` element | **S** | Single-file metadata add. |
| Deployment + smoke test in scratch/sandbox | Config validation | **S** | Validate via report builder in target org. |
| Regression — confirm no existing Case Manager report breaks | Manual QA | **S** | Open 1–2 existing saved reports built on this report type. |

**Total Estimated Effort:** **S** (≤ 1 hour) — *AI-estimated; validate with team.*

---

## Cross-References / Existing Stories

- **`requirements/HACAC_CommitteeReport_AddColumns_RecordType_CaseManagerName.md`** — Pattern precedent for adding columns to Case Manager-based reporting artifacts (although that story targets an OmniScript Edit Block, not a Report Type, the data-source pattern is similar).
- **`requirements/PAR_TerminatedLocation_CaseManagerAlert_UserStory.md`**, **`requirements/PAR_CaseManager_Association_CMA_Redesign_User_Stories.md`** — Other Case Manager-related changes; no direct dependency.
