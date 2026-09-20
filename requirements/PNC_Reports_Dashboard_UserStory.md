# US-RPT1: PNC Reporting & Dashboard — Case volume, outcomes, and Bypass-vs-Regular split (OOTB / PIE Report Builder)

**Story Type:** Reporting / Observability Enhancement (OOTB configuration — no Apex, no OmniStudio)
**Workstream:** PNC Location Migration & Bypass — Monitoring & Operations
**Persona:** Credentialing Manager (consumed also by PDM Manager, Reporting Analyst, and Credentialing Operations leadership)
**Priority:** P2 / Medium
**OmniScript / IP / DataRaptor:** N/A
**Depends on:** `requirements/PRM_PNCAnyLocation_DataModel_User_Story.md` (the `PRM_BypassPNC__c` field must be deployed before the Bypass-vs-Regular report R5 and the dashboard's bypass split can be built)
**Glossary note:** **PIE** = *Provider Information Exchange* (IBX's Salesforce platform). "PIE report builder" = the standard Lightning report builder scoped to a Case Manager–based Report Type.

---

## Story

**As a** Credentialing Manager,
**I want** a set of standard Salesforce (PIE) reports — and one dashboard that surfaces them — showing how many PNC cases are opened, closed, and denied, and splitting PNC practitioners into **Bypass-PNC** versus **regular PNC**,
**So that** my team can monitor PNC intake volume and outcomes, spot backlogs and denial trends, and report the mix of bypassed versus rule-driven PNC practitioners to leadership — without running ad-hoc SOQL or asking Engineering.

---

## Background

- A **"PNC case"** is a **Case Manager** (`IndividualApplication`) created from the PNC Intake Form, Record Type **`PRM_PNC`**.
- Its lifecycle is tracked on `IndividualApplication.PRM_Stage__c` (values incl. *Application Received → Application Review → QC Review → Sent To PDA → Case Complete → Complete*) and standard `Status` (incl. a *Denied* outcome). A denial reason is captured on `PRM_DenialReason__c`.
- **"Bypass-PNC vs regular PNC"** is a **practitioner (Account)** question: of all practitioners flagged `Account.PRM_PNC__c = true`, how many carry `Account.PRM_BypassPNC__c = true` (**manually forced into PNC via the Override** — Credentialing Status + Recred Due Date blanked, restorable within 30 days on revert) versus `= false` (regular, location-rollup-driven PNC). *(Revision Jul 2026: Override = force into PNC/blank, not "keep credentialed" — see `PRM_PNC_CredentialingStatus_Blank_User_Story.md`.)*

There is no consolidated PNC view today. With the PNC flag moving to the practice location and the new Bypass flag, leadership specifically needs the Bypass-vs-Regular breakdown. All of this is achievable with OOTB Lightning reports and dashboards — no code.

---

## Scope — report & dashboard inventory

| # | Report (business name) | Answers | Report Type (API) | Format | Group by |
|---|---|---|---|---|---|
| R1 | **PNC Cases by Stage** | Open cases and where they sit in the pipeline | `PRM_CaseManagerReportType` | Summary | `PRM_Stage__c` |
| R2 | **PNC Cases — Opened vs Closed vs Denied (by month)** | Monthly intake vs outcome trend | `PRM_CaseManagerReportType` | Matrix | Rows: `CreatedDate` (Calendar Month) · Cols: **Outcome** bucket |
| R3 | **PNC Denials** | How many denied, and why | `PRM_CaseManagerReportType` | Summary | `PRM_DenialReason__c` |
| R4 | **Open PNC Case Aging** | How long open cases have been sitting | `PRM_CaseManagerReportType` | Summary | `PRM_CaseManagerAge__c` bucket |
| R5 | **PNC Practitioners — Bypass vs Regular** | Of PNC practitioners, how many bypass vs regular | `Case_Manager_with_Accounts` *(or standard **Accounts**)* | Summary | `Account.PRM_BypassPNC__c` |
| R6 | **PNC Cases by Owner / Queue** *(optional)* | Team workload distribution | `PRM_CaseManagerReportType` | Summary | Case Owner |
| DB | **PNC Operations Dashboard** | One-glance operational + leadership view of R1–R6 | — | — | — |

---

## Current State (from codebase)

### Report types — reuse, mostly no change needed

**`PRM_CaseManagerReportType`** (label "Case Manager Report Type") — base object `IndividualApplication`. Already exposes every field R1–R4/R6 need, so **no report-type change is required** for them:

| Field | API name | Report-type line |
|---|---|---|
| Record Type (→ filter to PNC) | `RecordType` | `PRM_CaseManagerReportType.reportType-meta.xml:26` |
| Created Date | `CreatedDate` | line 31 |
| Status (→ Denied outcome) | `Status` | line 111 |
| Stage | `PRM_Stage__c` | line 151 |
| Denial Reason | `PRM_DenialReason__c` | line 156 |
| Case Manager Age (days) | `PRM_CaseManagerAge__c` | line 246 |
| Recred Due Date | `PRM_ReCredDueDate__c` | line 21 |

**`Case_Manager_with_Accounts`** (label "Case Manager with Accounts") — base `IndividualApplication` **outer-joined** to `Accounts__r` (`Case_Manager_with_Accounts.reportType-meta.xml:9`). Already exposes:
- IA-level PNC — `PRM_PNC__c` on `IndividualApplication` (line 350)
- **Account-level (practitioner rollup) PNC** — `PRM_PNC__c` on `IndividualApplication.Accounts__r` (line 1153) ✅
- `PRM_CaseManagerAge__c` (240), `PRM_DenialReason__c` (245)
- **Does NOT yet expose `Account.PRM_BypassPNC__c`** — that column must be added once the field is deployed (see Technical Section).

Sibling report types available if a Case-object metric is ever needed: `PRM_CaseManagerwithCases`, `Case_Manager_w_Cases` (both `IndividualApplication` → `Cases__r`).

### Gaps / dependencies
- **`Account.PRM_BypassPNC__c` is not deployed yet** (only `Account.PRM_PNC__c` exists). R5 and the dashboard's Bypass split are **blocked** on the data-model story. R1–R4/R6 and the rest of the dashboard are **independent** and can be built now.
- No PNC-specific reports, dashboard, folders, or dashboard running-user exist today.

---

## Acceptance Criteria

**AC-1 — Open PNC case pipeline (R1)**
- **Given** PNC cases exist across various pipeline stages,
- **When** the Credentialing Manager opens the *PNC Cases by Stage* report,
- **Then** it shows only PNC cases, counts open cases grouped by stage with a grand total, and can be filtered to a chosen date range.

**AC-2 — Opened / Closed / Denied over time (R2)**
- **Given** PNC cases have been created and resolved across several months,
- **When** the manager opens the *Opened vs Closed vs Denied* report,
- **Then** each month shows counts of cases opened, closed, and denied, so the intake-versus-outcome trend is visible at a glance.

**AC-3 — Denials with reason (R3)**
- **Given** some PNC cases have been denied,
- **When** the manager opens the *PNC Denials* report,
- **Then** it shows the total number of denied PNC cases broken down by denial reason, filterable by date range.

**AC-4 — Aging of open cases (R4)**
- **Given** open PNC cases of varying age,
- **When** the manager opens the *Open PNC Case Aging* report,
- **Then** open cases are grouped into age bands (0–7, 8–30, 31–60, 60+ days) with counts, so backlog and SLA risk are obvious.

**AC-5 — Bypass vs regular PNC (R5)** *(requires the Bypass field)*
- **Given** practitioners flagged as PNC, some with Bypass on and some with Bypass off,
- **When** the manager opens the *PNC Practitioners — Bypass vs Regular* report,
- **Then** it shows the count of PNC practitioners split into **Bypass-PNC** and **regular PNC**, with a total and each group's share of the total.

**AC-6 — One dashboard (DB)**
- **Given** the reports above exist,
- **When** the manager opens the *PNC Operations Dashboard*,
- **Then** it presents on one page: headline numbers for PNC cases **opened / closed / denied** in the selected period, the open-case pipeline, the opened-vs-closed trend, the aging breakdown, and the **Bypass-vs-Regular** split — and a dashboard filter lets the viewer change the time period (and optionally owner/team) without editing anything.

**AC-7 — Right people, right numbers**
- **Given** different roles view the dashboard,
- **When** a manager opens it,
- **Then** the figures reflect the data they are permitted to see (FLS respected), and the reports/dashboard live in a shared folder available to the credentialing/PDM teams (view) and their managers (edit).

**AC-8 — No regression**
- **Given** this is additive OOTB configuration,
- **When** the reports and dashboard are deployed,
- **Then** no existing report, report type, dashboard, object, field, FLS, or automation is modified or degraded (the one report-type column add for R5 is `checkedByDefault=false` and backward-compatible).

---

## Technical Section (For Developers)

All items are **OOTB Lightning report/dashboard configuration** — no Apex, triggers, OmniStudio, or LWC.

### Report types
- **R1–R4, R6:** reuse **`PRM_CaseManagerReportType`** as-is — **no metadata change** (all required fields already exposed; see Current State).
- **R5:** use **`Case_Manager_with_Accounts`** (Account PNC already exposed) — but it must expose the Bypass flag. Add **one** column once `Account.PRM_BypassPNC__c` is deployed:

```xml
<columns>
    <checkedByDefault>false</checkedByDefault>
    <field>PRM_BypassPNC__c</field>
    <table>IndividualApplication.Accounts__r</table>
</columns>
```

  in `force-app/main/default/reportTypes/Case_Manager_with_Accounts.reportType-meta.xml` (place next to the Account-level `PRM_PNC__c` at line 1153). Deploy:

```bash
sf project deploy start \
    -m "ReportType:Case_Manager_with_Accounts" \
    --target-org qa-sandbox --wait 10
```

- **Alternative for R5 (recommended for the population view):** a **standard `Accounts` report type** filtered to the practitioner record type + `PRM_PNC__c = true`, grouped by `PRM_BypassPNC__c`. This counts *all* PNC practitioners (not only those with a Case Manager), which is the more accurate leadership figure. No custom report type needed. See Clarification Q3.

### Per-report build notes
| Report | Report type | Filters | Grouping / summaries | OOTB feature |
|---|---|---|---|---|
| R1 | `PRM_CaseManagerReportType` | `RecordType.DeveloperName = PRM_PNC`; open stages (`PRM_Stage__c` not in Complete/Case Complete); `CreatedDate` in range | Group rows by `PRM_Stage__c`; Row Count | Summary |
| R2 | `PRM_CaseManagerReportType` | `RecordType.DeveloperName = PRM_PNC` | Matrix: rows = `CreatedDate` (Calendar Month); cols = **Outcome bucket** | **Bucket column** mapping stage/status → Open / Closed / Denied |
| R3 | `PRM_CaseManagerReportType` | `RecordType.DeveloperName = PRM_PNC`; outcome = Denied | Group by `PRM_DenialReason__c`; Row Count | Summary |
| R4 | `PRM_CaseManagerReportType` | `RecordType.DeveloperName = PRM_PNC`; open only | **Bucket column** on `PRM_CaseManagerAge__c` (0–7/8–30/31–60/60+) | Summary (no custom field needed — age already computed) |
| R5 | `Case_Manager_with_Accounts` (or standard **Accounts**) | Account `PRM_PNC__c = true` | Group by `PRM_BypassPNC__c` (Yes/No); Row Count | **Summary formula** `RowCount / PARENTGROUPVAL(RowCount, GRAND_SUMMARY)` for % share |
| R6 | `PRM_CaseManagerReportType` | `RecordType.DeveloperName = PRM_PNC`; open | Group by Case Owner | Summary |

- **Outcome bucket (R2/dashboard):** a report **Bucket column** mapping closed stages (*Case Complete*, *Complete*) → **Closed**, `Status = Denied` → **Denied**, everything else → **Open**. Confirm exact stage/status → outcome mapping with BA (Clarification Q1).
- **Age bands (R4):** bucket on the existing `PRM_CaseManagerAge__c` (already an integer days value) — no `TODAY() - DATEVALUE(CreatedDate)` row-level formula required. (If age semantics differ from "days open", fall back to a summary formula as in `ReAssessment_Reports_Dashboard_UserStory.md`.)
- **% of total (R5):** custom summary formula `RowCount / PARENTGROUPVAL(RowCount, GRAND_SUMMARY)`, formatted as percent (summary reports allow ≤5 summary formulas, ≤20 bucket fields, 1 row-level formula per report).

### Dashboard — `PNC Operations Dashboard`
Folder: **`PNC Operations`** (new). Components (dashboards support ≤25 components; each visualizes one report):

| # | Component | Type | Source report | Value / axis | Color |
|---|---|---|---|---|---|
| 1 | PNC Cases Opened (period) | Metric | R2 | Count opened | Neutral |
| 2 | PNC Cases Closed (period) | Metric | R2 | Count closed | Green |
| 3 | PNC Cases Denied (period) | Metric | R3 | Count denied | Red when > 0 |
| 4 | Open PNC Pipeline | Donut/Bar | R1 | Count by stage | — |
| 5 | Opened vs Closed vs Denied trend | Line/Column | R2 | By month | — |
| 6 | Open Case Aging | Bar | R4 | Count by age band | Green→Red by band |
| 7 | Bypass vs Regular PNC | Donut | R5 | Count by bypass flag | — |
| 8 | Aging / owner detail | Lightning Table | R4 / R6 | rows | highlight 60+ |

- **Dashboard filter** on date (and optionally owner/team) — ≤3 dashboard filters, 50 filter values each — lets viewers re-slice without editing source reports.
- **Running user / dynamic:** default to a fixed running user + folder sharing; use a **dynamic dashboard** ("view as logged-in user") only if each manager must see just their team's data (org limit 5 Enterprise / 10 Unlimited). See Clarification Q5.
- Optional **report/dashboard subscription** (scheduled email) for weekly leadership delivery — OOTB, no build.

### Storage & access
- New **Reports** folder and **Dashboards** folder, both "PNC Operations".
- Share **view** to credentialing/PDM teams (`PRM_CredentialingUser`, `PRM_ProviderDataAdmin`, `PRM_NetworkManagementQC`, `PRM_DataViewAll`) and **manage/edit** to their managers.
- FLS: `Account.PRM_PNC__c` already permissioned; `Account.PRM_BypassPNC__c` FLS is delivered by the data-model story — no FLS work here.

*(OOTB mechanics & limits grounded from Salesforce report/dashboard docs: formats Tabular/Summary/Matrix; bucket fields ≤20/report; summary formulas ≤5/report; 1 row-level formula/report; `PARENTGROUPVAL(field, GRAND_SUMMARY)` for % of grand total; ≤25 dashboard components; ≤3 dashboard filters; dynamic dashboards 5/10 per org.)*

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | **Outcome definitions.** Exact mapping to **Opened / Closed / Denied**: is "Closed" the stage *Case Complete*/*Complete*, a closed `Status`, or `IsClosed`? Is "Denied" `Status = Denied` or a denial stage? "Opened" = created in period, or currently in an open stage? | Drives the R2 bucket + R1/R3 filters | BA / Reporting Lead |
| 2 | **Denial reason source.** Confirm `PRM_DenialReason__c` is the field business wants R3 grouped by (it is already in the report type). Any secondary reason field? | R3 grouping | BA |
| 3 | **Bypass reporting level.** Report Bypass-vs-Regular over **all PNC practitioners** (standard **Accounts** report on `Account`) or only PNC practitioners **who have a Case Manager** (`Case_Manager_with_Accounts`)? Recommend the **Accounts** report for the true population count. | R5 report type; whether the `Case_Manager_with_Accounts` column add is even needed | BA / Reporting Lead |
| 4 | **Case object vs Case Manager.** Should any metric come from the standard `Case` object (Case Type = PNC), or is the Case Manager (`IndividualApplication`, RecordType `PRM_PNC`) the single source of truth for "PNC case" counts? Recommend Case Manager. | Report type choice | BA |
| 5 | **Static vs dynamic dashboard** + running user; folder-sharing model; whether scheduled email subscriptions are wanted. | Dashboard config | Reporting Lead |
| 6 | **Time basis & window** for trend/aging (Created date vs stage-change date) and default reporting window (rolling 12 months?). | R2/R4 filters | BA |
| 7 | Existing **W-number/GUS** work item to link, or create one? | Tracking / PR | Product / Scrum Master |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_CaseManagerReportType` | Custom Report Type | **NONE** | Reused as-is; all R1–R4/R6 fields already exposed. |
| `Case_Manager_with_Accounts` | Custom Report Type | **LOW** | One `<columns>` add for `PRM_BypassPNC__c` (`checkedByDefault=false`) — only if R5 uses this type (Clarification Q3). Backward-compatible. |
| New reports R1–R6 | Saved Reports | **LOW (additive)** | New reports in the PNC Operations folder. |
| PNC Operations Dashboard | Dashboard | **LOW (additive)** | New dashboard + folder + running user. |
| Objects / Fields / Apex / OmniStudio / LWC | — | **NONE** | No schema or code change. |
| FLS / Permission Sets | FLS | **NONE here** | `PRM_PNC__c` already permissioned; `PRM_BypassPNC__c` FLS handled by the data-model story. |
| **Data-model dependency** | Field | **BLOCKER for R5** | `Account.PRM_BypassPNC__c` must be deployed first. R1–R4/R6 independent. |
| Data accuracy | Data | **INFO** | Numbers reflect the PNC-location migration + Bypass rollup once those stories land. |

---

## Definition of Done

- [ ] R1 *PNC Cases by Stage* built on `PRM_CaseManagerReportType`, filtered to `PRM_PNC`, grouped by stage
- [ ] R2 *Opened vs Closed vs Denied* matrix with Outcome bucket, by month
- [ ] R3 *PNC Denials* grouped by `PRM_DenialReason__c`
- [ ] R4 *Open PNC Case Aging* bucketed on `PRM_CaseManagerAge__c`
- [ ] R5 *Bypass vs Regular PNC* with % summary formula — **after `PRM_BypassPNC__c` deployed** (+ report-type column add if using `Case_Manager_with_Accounts`)
- [ ] R6 *By Owner/Queue* (optional)
- [ ] PNC Operations Dashboard with components 1–8 and a date/owner filter; running user confirmed
- [ ] Reports/Dashboards folders created and shared to credentialing/PDM teams (view) + managers (edit)
- [ ] Regression: existing Case Manager reports/dashboards unaffected; sign-off received

---

## Story Points Estimate

| Item | Description | Points |
|---|---|---|
| R1 | PNC Cases by Stage (summary) | 1 |
| R2 | Opened/Closed/Denied matrix + Outcome bucket | 1 |
| R3 | PNC Denials by reason | 0.5 |
| R4 | Open PNC Case Aging bucket | 0.5 |
| R5 | Bypass vs Regular (+ % formula, + report-type column add) — *after Bypass field* | 1 |
| R6 | By Owner/Queue (optional) | 0.5 |
| Dashboard | 8 components + filter + folder/sharing/running user | 2 |
| **Total** | | **≈6.5** (Phase 1 = R1–R4/R6 + dashboard skeleton, no code dep; R5/Bypass split = Phase 2) |

> *AI-estimated; validate with team.*

---

## Cross-References / Reconciliation with Backlog

- **`requirements/ReAssessment_Reports_Dashboard_UserStory.md`** — sibling reports+dashboard story (same OOTB pattern). This story reuses its conventions: single-report-type reuse, cross-filters (WITH/WITHOUT), report **summary formula** for age/%, folder + running-user + component specs, DoD/Points tables. Key difference: PNC needs **no new CRT** (unlike the Re-Assessment CRT), because `PRM_CaseManagerReportType` already exposes stage/status/denial-reason/age — only R5 needs a one-line column add.
- **`requirements/PRM_CaseManagerReportType_AddBehavioralHealth_UserStory.md`** & **`..._AddMedicalDirectorReview_UserStory.md`** — precedent for the exact single-`<columns>` report-type add pattern and deploy shape used here for R5's `PRM_BypassPNC__c` column.
- **`requirements/PRM_PNCAnyLocation_DataModel_User_Story.md`** — **hard dependency** for R5 (delivers `Account.PRM_BypassPNC__c` + FLS).
- **`requirements/PRM_PNC_CredentialingStatus_Blank_User_Story.md`** — explains why Bypass-PNC keeps "Credentialed" while regular PNC blanks status; the Bypass-vs-Regular report makes that population visible.
- **`requirements/Recred_BypassPNC_CaseManagerCreation_UserStory.md`** — Bypass-PNC practitioners re-enter the recred cycle; R1/R6 volumes should reflect that once it ships.
- **`requirements/HACAC_CommitteeReport_AddColumns_RecordType_CaseManagerName.md`** & **`requirements/ReCredQCReviewClosedReport_README.md`** — other Case Manager report work; no direct dependency, same report-type family.
