# USER STORY: Add "Behavioral Health" Column to Case Manager Report Type (PIE Report Builder)

**Persona:** Credentialing Specialist / Ancillary Cred Specialist / Reporting Analyst, Developer
**Priority:** P2
**OmniScript:** N/A (report type metadata change)
**Integration Procedures:** N/A
**Relevant Requirements:** Business request — expose the `Behavioral Health` flag as a selectable column in the PIE report builder for Case Manager–based reports (organizational and individual provider scenarios), in both **Case Manager** and **Case Manager with Cases** report types.
**Vertical:** Provider Network Management (PNM) — Behavioral Health reporting
**Glossary note:** **PIE** = *Provider Information Exchange* (IBX's Salesforce platform), per `requirements/vendor/IBX_Vendor_DataDictionary_Request_v1.md` line 618. "PIE report builder" therefore refers to the standard Salesforce report builder column-picker scoped to a given Case Manager–based custom Report Type.

---

## Story

**As a** Credentialing Specialist / Ancillary Cred Specialist / Reporting Analyst building reports off of the **Case Manager** and **Case Manager with Cases** report types,
**I want** the **`Behavioral Health` (`PRM_BehavioralHealth__c`)** field on `IndividualApplication` (Case Manager) exposed as a selectable column in the PIE report builder,
**So that** I can identify and segment Case Managers tied to **Behavioral Health Provider Type & Service** (applicable to both organizational and individual provider scenarios) without resorting to a different report type, a different system, or a hand-built workaround.

**Why it matters:** Behavioral Health provider tracking is a recurring reporting ask from Cred / QC / Ancillary teams (volumes, due-on-recred lists, NPDB exception lists, etc.). The flag `PRM_BehavioralHealth__c` is already populated automatically by `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` based on the Provider Type & Service in `PRM_AncillaryAssessment__c`, but only **3 of the 4** Case Manager–based Report Types currently expose it as a selectable column. The canonical **"Case Manager Report Type"** (`PRM_CaseManagerReportType`) is missing it, blocking BH-segmented reporting for users who default to that report type.

---

## Scope

| Flow | Report Type | Affected Section | Data Source | Action |
|------|------------|------------------|-------------|--------|
| Reporting | `PRM_CaseManagerReportType` (label: **"Case Manager Report Type"**) | `Individual Applications` section | `IndividualApplication.PRM_BehavioralHealth__c` | **Add column** (currently missing) |
| Reporting | `PRM_CaseManagerwithCases` (label: **"Case Manager with Cases"**) | `Case Managers` section | `IndividualApplication.PRM_BehavioralHealth__c` | **Verify only — already present** at `PRM_CaseManagerwithCases.reportType-meta.xml` line 779 |

The two business-named report types are: **Case Manager** (missing) and **Case Manager with Cases** (already present). The story therefore only changes one file.

> Note on "organizational and individual": there are no separate `Organizational Case Manager` / `Individual Case Manager` report types in the codebase — every Case Manager is an `IndividualApplication` regardless of whether the linked Account is an organizational or individual provider. The `PRM_BehavioralHealth__c` field lives on `IndividualApplication` itself, so once it is exposed as a column it is available for both organizational and individual provider records (users segment by Account record type as they do today).

---

## Current State (from codebase)

### `PRM_CaseManagerReportType.reportType-meta.xml` — TARGET (missing the column)

- **Base object:** `IndividualApplication`
- **Label:** `Case Manager Report Type`
- **Description:** "This report is for Case Manager Object"
- **Sections:**
  - `Individual Applications` — contains ~50+ `IndividualApplication` columns (Id, Name, RecordType, CreatedDate, Account, ApplicationCase, PRM_Stage__c, PRM_NPDBVerification__c, PRM_OIGReviewOutcome__c, PRM_AncillaryAssessment__c neighborhood absent, PRM_CaseManagerAge__c, etc.)
  - `Case Managers` — contains a single column `PRM_DenialReason__c`
- **`PRM_BehavioralHealth__c` is NOT currently listed in either section.**
- **Location:** `force-app/main/default/reportTypes/PRM_CaseManagerReportType.reportType-meta.xml`

### `PRM_CaseManagerwithCases.reportType-meta.xml` — ALREADY OK

- **Base object:** `IndividualApplication`, joined with `Cases__r`
- **Label:** `Case Manager with Cases`
- `PRM_BehavioralHealth__c` already present in the `Case Managers` section at line 779–782, alongside `PRM_ProviderTypeService__c` and `PRM_AncillaryAssessment__c`.

### Sibling report types (not in business request, but already aligned — included as evidence)

| Report Type file | Label | Behavioral Health column? |
|---|---|---|
| `Case_Manager_with_Accounts.reportType-meta.xml` | "Case Manager with Accounts" | ✅ Present at line 779 |
| `Case_Manager_w_Cases.reportType-meta.xml` | "Case Manager w/ Cases" | ✅ Present at line 779 |

### Field — already exists on `IndividualApplication`

- **`PRM_BehavioralHealth__c`** — label "Behavioral Health" (custom checkbox on `IndividualApplication`).
- Help text: *"Determines if Ancillary Assessment is Behavioral Health Provider Type & Service."*
- Translation present at `force-app/main/default/objectTranslations/IndividualApplication-en_US/PRM_BehavioralHealth__c.fieldTranslation-meta.xml`.
- Set programmatically by `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` (line ~139): `PRM_BehavioralHealth__c = String.isNotBlank(ancillaryRecord.PRM_ProviderTypeService__c) && !ancillaryMDTRecords.isEmpty() && ancillaryMDTRecords.contains(ancillaryRecord.PRM_ProviderTypeService__c)` — driven by `PRM_GlobalConstant.BEHAVIORAL_HEALTH_PROVIDER_TYPE_SERVICE_NAMES` custom-metadata-backed values.
- Field-level access already granted on the following permission sets — **no FLS work needed**:
  - `PRM_CredentialingUser` (read+edit)
  - `PRM_AncillaryCredSpecialist` (read+edit)
  - `PRM_DataModifyAll` (read+edit)
  - `PRM_DataViewAll` (read-only)
  - `PRM_NetworkManagementQC` (read-only)
  - `PRM_ProviderDataAdmin` (read-only)

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_CaseManagerReportType.reportType-meta.xml`** | Custom Report Type (metadata) | Add a single `<columns>` entry exposing `PRM_BehavioralHealth__c` from the `IndividualApplication` table. Place it in the existing `Individual Applications` section adjacent to `PRM_AncillaryAssessment__c`-style fields (or in the `Case Managers` section next to `PRM_DenialReason__c` to mirror the other three sibling report types — see Clarification Q1). `<checkedByDefault>false</checkedByDefault>`. |
| **`PRM_CaseManagerwithCases.reportType-meta.xml`** | Custom Report Type (metadata) | **No change required** — already exposes the field at line 779. Include in the deploy validation step only. |

### Exact metadata snippet to add

Add the following `<columns>` block inside `PRM_CaseManagerReportType.reportType-meta.xml`:

```xml
<columns>
    <checkedByDefault>false</checkedByDefault>
    <field>PRM_BehavioralHealth__c</field>
    <table>IndividualApplication</table>
</columns>
```

### Reference — placement in existing Case Manager report types

In `PRM_CaseManagerwithCases.reportType-meta.xml`, the field appears in the `Case Managers` section between `PRM_SiteVisitStateSurveyDate__c` and `PRM_ProviderTypeService__c`:

```778:782:force-app/main/default/reportTypes/PRM_CaseManagerwithCases.reportType-meta.xml
        <columns>
            <checkedByDefault>false</checkedByDefault>
            <field>PRM_BehavioralHealth__c</field>
            <table>IndividualApplication</table>
        </columns>
```

The same placement pattern is used in `Case_Manager_with_Accounts.reportType-meta.xml` and `Case_Manager_w_Cases.reportType-meta.xml`.

### Deployment

- Deploy via SFDX:
  ```bash
  sf project deploy start \
      -m "ReportType:PRM_CaseManagerReportType" \
      --target-org qa-sandbox \
      --wait 10
  ```
- No data migration, Apex, OmniScript, IP, DataRaptor, or LWC change required.
- No `--test-level` flag needed (report type metadata only — no Apex test impact).

---

## Acceptance Criteria

**AC-1 — Field is selectable in the Case Manager Report Type**

**Given** a user with `PRM_CredentialingUser` (or any of the listed permission sets that grant FLS read on `PRM_BehavioralHealth__c`) navigates to **Reports → New Report**,
**When** they select the **"Case Manager Report Type"** report type and enter the report builder,
**Then** the **"Behavioral Health"** field SHALL appear in the Fields panel under the Case Manager (`IndividualApplication`) section,
**And** dragging it into the report SHALL render the checkbox value (`true` / `false`) for each row.

---

**AC-2 — Field continues to be selectable in the Case Manager with Cases Report Type (regression)**

**Given** a user opens the **"Case Manager with Cases"** report type in the report builder,
**Then** the **"Behavioral Health"** field SHALL continue to appear in the Fields panel under the Case Manager section (no regression from current state),
**And** any saved reports built on `PRM_CaseManagerwithCases` that already include the column SHALL continue to render unchanged.

---

**AC-3 — Field is unchecked by default**

**Given** the metadata change is deployed,
**When** a user opens the report builder for the Case Manager Report Type,
**Then** **"Behavioral Health"** SHALL NOT be pre-added to the default report layout (`checkedByDefault = false`),
**And** existing reports built on this report type SHALL continue to render unchanged (no auto-injected column).

---

**AC-4 — Filterable and groupable for Behavioral Health segmentation**

**Given** the field is added to a Case Manager Report Type report,
**When** a user adds a **filter** `Behavioral Health = True` (or groups by Behavioral Health),
**Then** the report SHALL execute successfully and return only Case Manager records with `PRM_BehavioralHealth__c = TRUE` (matching the Behavioral Health Provider Type & Service set in `PRM_AncillaryAssessment__c`).

---

**AC-5 — Coverage for both organizational and individual provider scenarios**

**Given** a user runs the **Case Manager Report Type** with the new Behavioral Health column added,
**When** the underlying Case Manager records span both organizational and individual provider Accounts,
**Then** the Behavioral Health value SHALL render correctly for **both** record sets (no record-type-specific gap), since `PRM_BehavioralHealth__c` is on the `IndividualApplication` itself and is record-type-agnostic.

---

**AC-6 — No regression to existing reports built on this report type**

**Given** any existing saved Lightning report or dashboard component built on `PRM_CaseManagerReportType`,
**When** the metadata change is deployed,
**Then** the report SHALL continue to load and run with the same columns, filters, and groupings as before deployment,
**And** no schema/metadata error SHALL be raised in the report builder.

---

**AC-7 — FLS respected**

**Given** a user without read access to `PRM_BehavioralHealth__c`,
**When** they open the Case Manager Report Type in the report builder,
**Then** the **"Behavioral Health"** field SHALL NOT be visible in the Fields panel (Salesforce default FLS behavior),
**And** any prior report containing the column SHALL render the column as blank for that user.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should `PRM_BehavioralHealth__c` be added to the `Individual Applications` section (next to other ancillary/review fields) or to the `Case Managers` section (next to `PRM_DenialReason__c`, mirroring the other three sibling Case Manager report types)? | Section placement determines where users find the field in the report builder; mirroring sibling report types favors the `Case Managers` section. Recommend **`Case Managers` section** for consistency. | BA / Reporting Lead |
| 2 | Confirm the two report types named by the business are `PRM_CaseManagerReportType` ("Case Manager Report Type") and `PRM_CaseManagerwithCases` ("Case Manager with Cases"). The latter already exposes Behavioral Health, so the actual delta is in only one file. Should we also bring `Case_Manager_with_Accounts` and `Case_Manager_w_Cases` to parity (already present — no change) and proactively confirm dashboards built on those still pick up the field? | Determines whether QA validation extends to all four report types or only two. | BA / Reporting Lead |
| 3 | Does the business want **`Behavioral Health`** as the displayed column header, or a different alias (e.g., "BH Provider", "Behavioral Health Provider Flag")? Salesforce uses the field's translated label (currently "Behavioral Health"). | Column header label on reports. | BA |
| 4 | Should `checkedByDefault` be `true` (auto-shown when a new report is created) or `false` (user opt-in)? Existing report types use `false`. Recommend **`false`** for consistency. | UX behavior in report builder default state. | BA |
| 5 | Are there any related Behavioral Health fields the business also wants surfaced in the same change (e.g., `PRM_ProviderTypeService__c` already in the with-Cases report; `PRM_AncillaryAssessment__c` reference)? Bundling avoids a future second change. | Could expand scope to a small "BH reporting parity" bundle for `PRM_CaseManagerReportType`. | BA / Reporting Lead |
| 6 | Should this be reflected in any analytics/CRMA dataset, list view, or downstream BI feed that consumes report metadata (especially BH-cohort dashboards)? | If yes, add downstream artifacts to the change set. | Analytics / Data Eng |
| 7 | Is there an existing W-number/GUS work item for this enhancement, or should one be created and linked to this story? | Tracking and PR reference. | Product / Scrum Master |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **`PRM_CaseManagerReportType`** | Custom Report Type | **LOW** | Single `<columns>` element added; no schema, FLS, OmniScript, IP, DataRaptor, Apex, or LWC change required. |
| **`PRM_CaseManagerwithCases`** | Custom Report Type | **NONE** | Field already exposed; no change. |
| Existing reports built on `PRM_CaseManagerReportType` | Saved Reports / Dashboards | **LOW** | Backward-compatible; new field is opt-in (`checkedByDefault=false`). No re-save required. |
| Profiles & Permission Sets | FLS | **NONE** | Field already permissioned across Cred/QC/Ancillary/Data permission sets. |
| `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` and other Apex consumers | Apex | **NONE** | No code path changes; the field continues to be populated as today. |
| `Case_Manager_with_Accounts`, `Case_Manager_w_Cases` | Sibling Report Types | **NONE** | Already expose the field; no change. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|------------|--------|-------|
| `PRM_CaseManagerReportType.reportType-meta.xml` | Add one `<columns>` element | **S** | Single-file metadata add. |
| Deployment + smoke test in QA sandbox | Config validation | **S** | Validate via report builder in target org; create a test report and confirm Behavioral Health column appears, filters, and groups. |
| Regression — confirm no existing Case Manager report breaks | Manual QA | **S** | Open 1–2 existing saved reports built on this report type. |
| Smoke test of `Case Manager with Cases` parity | Manual QA | **S** | Confirm column still selectable (no regression). |

**Total Estimated Effort:** **S** (≤ 1 hour) — *AI-estimated; validate with team.*

---

## Cross-References / Existing Stories

- **`requirements/PRM_CaseManagerReportType_AddMedicalDirectorReview_UserStory.md`** — Direct precedent: identical pattern, different field (`PRM_MedicalDirectorReview__c`). Same target report type, same single-file delta, same deployment shape.
- **`requirements/ReAssessment_Reports_Dashboard_UserStory.md`** — Other Case Manager / Ancillary Re-Assessment reporting work; no direct dependency.
- **`requirements/AncillaryAssessment_GroupModalFilter_BillingTypeOptional_UserStory.md`** — Touches the same Ancillary domain that drives `PRM_BehavioralHealth__c` upstream; no direct dependency.
