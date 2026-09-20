# User Story — Re-Assessment Letter Generation: Operational Reports & Dashboard

**Story Type:** Reporting / Observability Enhancement
**Workstream:** Ancillary / Re-Assessment — Monitoring & Operations
**Depends On:** WS-1 Code Fix (AC-1.1 fallback logging), WS-2 Data Fix (Letterhead Indicator config)
**Related Story:** Re-Assessment Letter Generation: Silent Failure on Missing Letterhead Indicator

---

## Story Title

**As a** Provider Relations Operations user,
**I want** a set of Salesforce reports and a dashboard that show the real-time status of Re-Assessment letter generation for every active case manager,
**So that** my team can instantly identify which assessments succeeded, which are stuck with no letter, and which out-of-territory accounts have received the correct dual-letterhead (IBX + AmeriHealth) letters — without needing to run ad-hoc SOQL or ask Engineering.

---

## Background

The `PRM_CheckDueOnAncillaryReAssessmentBatch` runs daily. For each due `PRM_AncillaryAssessment__c`, it creates:
1. An `IndividualApplication` (IA) with `RecordType = PRM_AncillaryReAssessment` — referred to as the **Re-Assessment Case Manager**
2. A `Case` linked to that IA
3. One or more `PRM_Letter__c` records linked to the IA via the `PRM_CaseManager__c` lookup (`relationshipName = Letters`)

**The three operational questions that require reports:**

| Question | Report |
|---|---|
| Which Case Managers have a letter? → Batch ran successfully | Report 1 — Success |
| Which Case Managers have NO letter? → Batch failed silently | Report 2 — Failure / Error |
| Which out-of-territory accounts got both IBX + AHPA letters? → Fallback fix worked | Report 3 — Out-of-Territory Confirmation |

---

## Report Type Setup — One CRT for All Three Reports

> ⚠️ **Critical platform limitation:** When `PRM_Letter__c` is the primary object in a Custom Report Type, `IndividualApplication` does **not** appear as a selectable related object — even though `PRM_CaseManager__c` is a Lookup to `IndividualApplication`. This is a Salesforce platform restriction.

**Design decision:** Use a **single Custom Report Type** with `IndividualApplication` as primary and `PRM_Letter__c` as the optional related object. All three reports are built from this one type — the difference between success, failure, and out-of-territory is controlled entirely by filters within each report.

### CRT — "Re-Assessment Case Managers with or without Letters"

| Setting | Value |
|---|---|
| **Primary object** | `IndividualApplication` |
| **Related object** | `PRM_Letter__c` via `Letters` relationship |
| **Relationship type** | **"Each 'A' record may or may not have related 'B' records"** (A with or without B) |
| **Report type label** | `PRM Re-Assessment Case Managers with or without Letters` |
| **Category** | `Provider Relations` |
| **Status** | Deployed / Active |

**How to create in Setup:**
1. **Setup → Report Types → New Custom Report Type**
2. **Primary Object:** `Individual Application`
3. Click **Next** → **"Click to relate another object"**
4. Search for and select `PRM_Letter__c`; the platform will show the `Letters` relationship (derived from `PRM_CaseManager__c.relationshipName = 'Letters'`)
5. Select **"Each 'A' record may or may not have related 'B' records"**
6. On the field layout, add the following fields from each object:

**From `IndividualApplication`:**
- `Name` (IA auto-number)
- `RecordType.Name`
- `PRM_Stage__c`
- `Status`
- `Account.Name`
- `Account.BillingState`
- `PRM_AncillaryAssessment__c`
- `CreatedDate`

**From `PRM_Letter__c` (via Letters):**
- `Id`
- `Name` (Letter auto-number)
- `PRM_LetterheadKey__c`
- `PRM_GroupName__c`
- `PRM_GroupNpi__c`
- `PRM_PrimaryAddressStateCode__c`
- `PRM_PrimaryAddressCountyName__c`
- `PRM_CaseNumber__c`
- `PRM_ApplicationId__c`
- `PRM_EffectiveDate__c`
- `CreatedDate` (Letter created date)

7. Save and set status to **Deployed**

---

## Report 1 — Re-Assessment Letter Success Report

### Purpose
Show every Re-Assessment Case Manager (`IndividualApplication`) that has at least one linked `PRM_Letter__c`. Presence of a letter = the batch ran successfully for that provider.

### Report Type
**CRT — `PRM Re-Assessment Case Managers with or without Letters`**

### Filters
| Filter | Operator | Value |
|---|---|---|
| `RecordType.DeveloperName` (on IA) | equals | `PRM_AncillaryReAssessment` |
| `PRM_Letter__c: Id` (cross-filter) | **not equal to** | _(blank)_ — i.e., **IA WITH Letters** |
| `PRM_Letter__c: RecordType.DeveloperName` | equals | `PRM_ReAssessment` |
| `IA: CreatedDate` | equals | _(dynamic — rolling 365 days or current fiscal year)_ |

> The key filter is the cross-filter: **"IA WITH Letters"** — only rows where at least one `PRM_Letter__c` record exists under the IA are returned.

### Columns to Include
| Column | Source | Field API Name | Notes |
|---|---|---|---|
| IA Name | IndividualApplication | `Name` | Auto-number — unique per IA |
| Account Name | IndividualApplication | `Account.Name` | Provider name |
| Account State | IndividualApplication | `Account.BillingState` | Provider's billing state |
| Stage | IndividualApplication | `PRM_Stage__c` | e.g., `PSV`, `Complete` |
| Letter Name | PRM_Letter__c | `Name` | Auto-number — unique per letter |
| Letterhead Key | PRM_Letter__c | `PRM_LetterheadKey__c` | `IBC`, `AHPA`, `AHNJ`, etc. |
| State (Letter) | PRM_Letter__c | `PRM_PrimaryAddressStateCode__c` | Address state on the letter |
| County | PRM_Letter__c | `PRM_PrimaryAddressCountyName__c` | Address county on the letter |
| Case Number | PRM_Letter__c | `PRM_CaseNumber__c` | Linked case |
| Effective Date | PRM_Letter__c | `PRM_EffectiveDate__c` | Letter effective date |
| Letter Created Date | PRM_Letter__c | `CreatedDate` | When letter was generated |

> **Note:** One IA with two letters (IBC + AHPA for out-of-territory providers) will produce **two rows** in this report — one row per letter. This is expected.

### Grouping / Sorting
- **Group rows by:** `PRM_PrimaryAddressStateCode__c` (Letter field) — shows distribution by state
- **Sort within group:** `Letter CreatedDate` descending
- **Record count:** Show count of letters per state group

### Report Format
`Summary` — grouped by State

### Acceptance Criteria
- AC-R1.1 — Report returns only IAs with `RecordType = PRM_AncillaryReAssessment` that have at least one linked `PRM_Letter__c` with `RecordType = PRM_ReAssessment`
- AC-R1.2 — Each row represents one letter; a provider with IBC + AHPA letters appears as two rows, both under the same IA
- AC-R1.3 — `PRM_LetterheadKey__c` is populated on every row
- AC-R1.4 — Report refreshes on demand; scheduled subscription available for daily email delivery
- AC-R1.5 — Genomic Health Inc IA `0iTUW000000L2LA2A0` does **not** appear in this report until its letter is generated; it appears with 2 rows (IBC + AHPA) after remediation

---

## Report 2 — Re-Assessment Letter Failure / Error Report

### Purpose
Show every Re-Assessment Case Manager (`IndividualApplication`) that has **no** linked `PRM_Letter__c`. Absence of a letter = the batch ran but letter generation failed silently.

> This is the operational alert / work queue. Every record in this report requires investigation or remediation.

### Report Type
**CRT — `PRM Re-Assessment Case Managers with or without Letters`** (same CRT, opposite cross-filter)

### Filters
| Filter | Operator | Value |
|---|---|---|
| `RecordType.DeveloperName` (on IA) | equals | `PRM_AncillaryReAssessment` |
| `PRM_Stage__c` (on IA) | not equal to | `Complete` |
| `PRM_Letter__c: Id` (cross-filter) | **equals** | _(blank)_ — i.e., **IA WITHOUT Letters** |
| `IA: CreatedDate` | greater or equal | _(rolling — last 18 months to catch all historical batch runs)_ |

> The cross-filter **"IA WITHOUT Letters"** is the key condition. In the report builder: Add Cross Filter → `Individual Application` **without** `Letters`.

### Columns to Include
| Column | Source | Field API Name | Notes |
|---|---|---|---|
| IA Name | IndividualApplication | `Name` | Auto-number |
| Account Name | IndividualApplication | `Account.Name` | Provider name |
| Account State | IndividualApplication | `Account.BillingState` | Quick triage — out-of-territory? |
| Stage | IndividualApplication | `PRM_Stage__c` | e.g., `PSV`, `Pending Application` |
| Status | IndividualApplication | `Status` | e.g., `Pending Application` |
| Assessment | IndividualApplication | `PRM_AncillaryAssessment__c` | Link to source assessment |
| IA Created Date | IndividualApplication | `CreatedDate` | When batch created this IA |
| Days Stuck | _(Report Summary Formula)_ | `TODAY() - DATEVALUE(CreatedDate)` | How long it's been stuck |

### Grouping / Sorting
- **No grouping** — flat list, sorted by `IA CreatedDate` ascending (oldest = highest urgency)
- **Conditional highlight:** Rows where `Days Stuck > 30` in red; `> 60` in bold red

### Report Format
`Tabular` — each row = one stuck IA

### Acceptance Criteria
- AC-R2.1 — Report returns only IAs with `RecordType = PRM_AncillaryReAssessment`, `Stage != Complete`, and zero related `PRM_Letter__c` records
- AC-R2.2 — IA `0iTUW000000L2LA2A0` (Genomic Health Inc) appears in this report immediately and disappears once its letter is created
- AC-R2.3 — Once a letter is created for a stuck IA, that IA drops off the report on the next refresh automatically
- AC-R2.4 — Report is accessible to Provider Relations Operations users
- AC-R2.5 — Report count = 0 after all 68 stuck IAs from the WS-3 audit are remediated

### Supplementary: Exception Log Sub-Report
After WS-1 code fix is deployed, a companion report on `PRM_ExceptionLog__c` surfaces the Warning messages logged when no LetterheadIndicator was found, giving Engineering the exact AccountId/State/County for each gap:

| Filter | Value |
|---|---|
| Context / Object | contains `ReassessmentLetter` |
| Severity | equals `Warning` |
| Message | contains `No LetterheadIndicator match` |
| Created Date | rolling 30 days |

---

## Report 3 — Out-of-Territory Dual-Letter Confirmation Report

### Purpose
Show all Re-Assessment providers whose primary address state is **outside** IBX's core territory (DE, MD, NJ, PA) and confirm that **both** an IBC letter and an AHPA letter were generated for each. This is the post-deployment validation report for the code-only fallback fix.

> This report answers: "For every out-of-territory provider, did we generate exactly 2 letters — one IBC and one AHPA?"

### Report Type
**CRT — `PRM Re-Assessment Case Managers with or without Letters`** (same CRT, filtered to out-of-territory letters)

### Filters
| Filter | Operator | Value |
|---|---|---|
| `RecordType.DeveloperName` (on IA) | equals | `PRM_AncillaryReAssessment` |
| `PRM_Letter__c: RecordType.DeveloperName` | equals | `PRM_ReAssessment` |
| `PRM_Letter__c: PRM_PrimaryAddressStateCode__c` | **not equal to** | `DE` |
| `PRM_Letter__c: PRM_PrimaryAddressStateCode__c` | **not equal to** | `MD` |
| `PRM_Letter__c: PRM_PrimaryAddressStateCode__c` | **not equal to** | `NJ` |
| `PRM_Letter__c: PRM_PrimaryAddressStateCode__c` | **not equal to** | `PA` |
| `PRM_Letter__c: PRM_LetterheadKey__c` | not equal to | _(blank)_ |

> Because the CRT uses IA as primary with Letters as the optional related, each letter row appears under the IA. Filtering on the Letter's `PRM_PrimaryAddressStateCode__c` scopes the report to out-of-territory letters only.

### Columns to Include
| Column | Source | Field API Name | Notes |
|---|---|---|---|
| IA Name | IndividualApplication | `Name` | Groups all letters per case manager |
| Account Name | IndividualApplication | `Account.Name` | Provider name |
| Account State | IndividualApplication | `Account.BillingState` | Confirms out-of-territory |
| Letter Name | PRM_Letter__c | `Name` | One row per letter |
| Letterhead Key | PRM_Letter__c | `PRM_LetterheadKey__c` | Expect `IBC` on one row, `AHPA` on the other |
| State (Letter) | PRM_Letter__c | `PRM_PrimaryAddressStateCode__c` | Should be outside DE/MD/NJ/PA |
| County | PRM_Letter__c | `PRM_PrimaryAddressCountyName__c` | Full county name |
| Case Number | PRM_Letter__c | `PRM_CaseNumber__c` | Linked case |
| Effective Date | PRM_Letter__c | `PRM_EffectiveDate__c` | Letter effective date |
| Letter Created Date | PRM_Letter__c | `CreatedDate` | When the letter was generated |

### Grouping / Sorting
- **Group rows by:** `IA Name` (or `Account.Name`) — both letters for a given provider appear under the same group
- **Secondary sort:** `PRM_LetterheadKey__c` ascending — IBC appears before AHPA within each group
- **Summary row per group:** Row count — every group should show exactly **2** (one IBC + one AHPA)
- **Highlight rule:** Flag any group where row count ≠ 2 — this indicates an incomplete or partial letter set

### Report Format
`Summary` — grouped by IA / Account

### Validation Logic (for Operations)
After WS-1 fallback fix is deployed and WS-3 remediation runs, verify:

1. Every out-of-territory provider group shows **exactly 2 letter rows**
2. One row: `PRM_LetterheadKey__c = 'IBC'`
3. Other row: `PRM_LetterheadKey__c = 'AHPA'`
4. Both rows share the same `IA Name` (same case manager)

Any group with row count = 1 → partial failure; row count = 0 → should not appear (those would show in Report 2 instead).

### Acceptance Criteria
- AC-R3.1 — Report returns only letters where `PRM_PrimaryAddressStateCode__c` is NOT IN (DE, MD, NJ, PA)
- AC-R3.2 — Every IA group shows exactly 2 rows: `IBC` + `AHPA`
- AC-R3.3 — Genomic Health Inc (CA / San Mateo) appears here after remediation with exactly 2 rows
- AC-R3.4 — Any IA group with only 1 letter is visually distinguishable (row count ≠ 2)
- AC-R3.5 — Report can be filtered to a single state (e.g., `CA` only) for targeted validation
- AC-R3.6 — An IA that has no letters at all does **not** appear in this report (those belong in Report 2)

---

## Dashboard — Re-Assessment Letter Generation Health

### Dashboard Name
`PRM Re-Assessment Letter Generation Health`

### Dashboard Folder
`Provider Relations Operations`

### Description
Real-time operational view of Re-Assessment letter generation status across all active batch runs. Daily refresh. Accessible to Provider Relations Operations users.

---

### Component 1 — Letters Generated Today (Metric)
- **Type:** Metric
- **Source:** Report 1 filtered to `Letter CreatedDate = TODAY`
- **Value:** Count of letters created today
- **Label:** `Letters Generated Today`
- **Color:** Green

---

### Component 2 — Case Managers Without Letters (Metric — Alert)
- **Type:** Metric
- **Source:** Report 2 (Failure)
- **Value:** Row count — number of stuck IAs with no letter
- **Label:** `Case Managers Without Letters`
- **Color:** Red when > 0, Green when = 0
- **Purpose:** Primary health indicator. Zero = all assessments processing correctly.

---

### Component 3 — Letters by State (Bar Chart)
- **Type:** Horizontal Bar Chart
- **Source:** Report 1, grouped by `PRM_PrimaryAddressStateCode__c`
- **X-axis:** Count of letters | **Y-axis:** State code
- **Label:** `Letters Generated by State`

---

### Component 4 — Out-of-Territory Provider Letter Status (Table)
- **Type:** Summary Table
- **Source:** Report 3, grouped by Account Name
- **Columns:** Account Name, State, Letter Count (expect 2)
- **Label:** `Out-of-Territory Provider Letter Status`
- **Highlight:** rows where Letter Count ≠ 2

---

### Component 5 — Stuck Records by Age (Bar Chart)
- **Type:** Bar Chart
- **Source:** Report 2, grouped by `Days Stuck` bucket (0–30, 31–60, 61–90, 90+)
- **Label:** `Stuck Case Managers by Age`
- **Color:** Green → Yellow → Orange → Red by bucket

---

### Component 6 — Exception Log Warnings (Metric)
- **Type:** Metric
- **Source:** Exception Log sub-report (Warning severity, `ReassessmentLetter` context, last 7 days)
- **Value:** Count of Warning log entries
- **Label:** `Letterhead Config Warnings (7 days)`
- **Color:** Red when > 0
- **Note:** Visible after WS-1 code fix deployed

---

## Implementation Notes

### Cross-Filters in the Report Builder

All three reports use **cross-filters** — these are set in the **Report Builder** (not the Report Type builder):

| Report | Cross-Filter Setting |
|---|---|
| Report 1 (Success) | `Individual Application` **WITH** `Letters` |
| Report 2 (Failure) | `Individual Application` **WITHOUT** `Letters` |
| Report 3 (Out-of-territory) | `Individual Application` **WITH** `Letters` + Letter state filter |

In the report builder: **Add Filter → Cross Filter → select relationship → choose WITH or WITHOUT**

### Why One CRT Works for All Three

Since the CRT is "IA with or without Letters":
- **Report 1:** Filter "WITH Letters" → returns only IAs that have letters; each letter = one row
- **Report 2:** Filter "WITHOUT Letters" → returns only IAs with no letters; no letter fields populate (they're blank/null)
- **Report 3:** Filter "WITH Letters" + out-of-territory state condition on the Letter side → returns out-of-territory letter rows under their parent IAs

No second report type needed. No duplicated maintenance.

### Formula Field: Days Stuck (Report 2)

Add a **Report Summary Formula** directly in Report 2 (no custom field required):
- **Column Name:** `Days Stuck`
- **Formula:** `TODAY() - DATEVALUE(CreatedDate)` where `CreatedDate` = IA created date
- **Output:** Integer — number of days the IA has existed without a letter

---

## Sharing & Access

| Component | Access |
|---|---|
| CRT — IA with/without Letters | Deployed (platform-wide) |
| Report 1 (Success) | `Provider Relations Operations` folder — View for all Ops users |
| Report 2 (Failure) | `Provider Relations Operations` folder — Edit access for Ops leads |
| Report 3 (Out-of-Territory) | `Provider Relations Operations` folder — View for all Ops users |
| Dashboard | `Provider Relations Operations` folder — View for all; running user = dedicated ops user |

---

## Sequencing / Dependency

| Phase | Prerequisite | Action |
|---|---|---|
| **Phase 1 — Immediate** | None | Build CRT; build Report 1 (Success); build Report 2 (Failure); build dashboard with Components 1–2 |
| **Phase 2 — After WS-1 deployed** | Code fix (fallback IBC+AHPA) deployed | Build Report 3 (Out-of-Territory); add Components 3–4 to dashboard |
| **Phase 3 — After WS-1 deployed** | Exception logger emitting Warnings | Add Component 6 (Exception Log Warnings) |
| **Phase 4 — After WS-3 remediation** | All 68 stuck IAs remediated | Validate: Report 2 = 0 rows; Report 3 = all out-of-territory providers show 2 rows |

---

## Definition of Done

- [ ] **CRT** (`PRM Re-Assessment Case Managers with or without Letters`) deployed and active
- [ ] **Report 1** (Success) created; returns letters for all IAs that have them; Genomic Health Inc appears after remediation
- [ ] **Report 2** (Failure) created; IA `0iTUW000000L2LA2A0` appears before remediation; 0 rows after WS-3 complete
- [ ] **Report 3** (Out-of-Territory) created; every group shows exactly 2 rows (IBC + AHPA) after WS-1 + WS-3
- [ ] **Dashboard** created with Components 1–6; Component 2 (Stuck Count) = 0 after full remediation
- [ ] Dashboard refresh schedule set (daily); running user confirmed
- [ ] Reports shared with Provider Relations Operations team; sign-off received

---

## Story Points Estimate

| Item | Description | Points |
|---|---|---|
| CRT | Build and deploy single Custom Report Type | 1 |
| Report 1 | Success report — IA with Letters, grouped by state | 1 |
| Report 2 | Failure report — IA without Letters, aging formula | 1 |
| Report 3 | Out-of-territory dual-letter confirmation | 1 |
| Dashboard | 6-component dashboard with sharing setup | 2 |
| **Total** | | **6** |

> Phase 1 (CRT + Reports 1 & 2 + basic dashboard) can be completed immediately — no code dependencies.
> Phase 2 onward requires WS-1 code fix deployment.

---

## Related Records & Artifacts

| Item | Reference |
|---|---|
| Silent Failure User Story | `requirements/ReAssessment_Letter_Silent_Failure_UserStory.md` |
| Confirmed Stuck IA | `0iTUW000000L2LA2A0` — Genomic Health Inc, CA/San Mateo |
| Letter lookup field | `PRM_Letter__c.PRM_CaseManager__c` → `IndividualApplication`, `relationshipName = Letters` |
| Batch class | `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` |
| Letter generation class | `PRM_ReassessmentLetter.cls` |
| In-territory states | DE, MD, NJ, PA |
| Fallback letterhead keys | `IBC`, `AHPA` (for out-of-territory providers) |
