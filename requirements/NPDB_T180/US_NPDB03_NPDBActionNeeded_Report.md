# US-NPDB-03 — Operational Report: Practitioners in "NPDB Action Needed" by Recredentialing-Due Date

**Status:** Draft for business sign-off
**Created:** 2026-06-01
**Updated:**
- *2026-06-01 (v1)* — Initial draft (pre-template format).
- *2026-06-03 (v2)* — Rewrite to IBXQA 11-section template + linter-conformant appendix.
- *2026-06-03 (v3)* — Rewrite to **User Story Solution Architect v1.6** skill: business-language ACs (Pattern A/B/C), separate **Technical Implementation (high-level)** section, canonical workspace persona.
- *2026-06-08 (v4)* — Consistency update with the US-NPDB-02 v4 pivot: the drill-down target on the Case Manager record page is now a **read-only findings text** surface (no Fix/Add links). AC-3.5 reworded accordingly.
**Author:** AI agent (with QA-sandbox evidence)
**Background investigation:** `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md`
**Primary persona:** **Credentialing Specialist (acting as Credentialing-Ops lead)** — the credentialing operations role responsible for triaging the queue of blocked practitioners each morning. Network Management QC Specialists are a secondary read-only audience.
**Sibling stories:** **US-NPDB-01** (delivers the `NPDB Action Needed` status, the `Validation Details` field, and the `Validation Last Run` field that this report sorts and surfaces); **US-NPDB-02** (delivers the record-page banner the user lands on after clicking a row in this report).

> **How to read this story.**
>
> - **Business sign-off audience** — read Story, Why it matters, Preconditions, Acceptance Criteria. Stop at the Technical Implementation header.
> - **Developer audience** — same sections + Technical Implementation block + Definition of done.
> - **QA audience** — the Acceptance Criteria are the test scripts. Each Pattern-A AC has a Given/When/Then you can execute against the Reports UI; each Pattern-B/C AC is a config or permission spec you can validate via Setup.

---

## Header

**Persona:** Credentialing Specialist (acting as Credentialing-Ops lead) — primary; Network Management QC Specialist — read-only secondary
**Priority:** P1
**OmniScript:** N/A — reporting-only story
**Integration Procedures:** N/A
**Relevant Requirements:** **US-NPDB-01** (hard dependency — new picklist value + new fields must be deployed first), **US-NPDB-02** (the record-page banner the user opens from any report row)

---

## Story

**As a** Credentialing Specialist acting as the Credentialing-Ops lead each morning,
**I want** a single Salesforce report that lists every Case Manager currently in **NPDB Action Needed**, grouped by the practitioner's recredentialing-due date so the most-urgent practitioners surface first, with the days remaining colour-coded for at-a-glance triage,
**So that** I can see in one screen exactly how many practitioners are blocked, sort my team's day by SLA urgency (not by creation date), and avoid writing one-off SOQL every morning to identify stuck cases.

**Why it matters:** Today, Ops opens the Developer Console every morning and runs an ad-hoc SOQL query to figure out which practitioners are stuck waiting for NPDB. The query has to be re-discovered every time, every analyst writes a slightly different version, and the result is a flat list that does not order practitioners by how close they are to their recredentialing-due date. With **US-NPDB-01** introducing a clearly-named status and a "what is missing" field on the Case Manager, the data is finally shaped to drive a structured report — and putting that report into the right folder with the right grouping is the difference between Ops chasing fires and Ops actually triaging the queue.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Operations daily triage | N/A (Salesforce Reports UI) | `PRM_NPDBActionNeeded_ByReCredDueDate` report inside the `PRM Credentialing Operations` folder | `IndividualApplication` filtered to `Status = 'NPDB Action Needed'` joined to `Account.PRM_ReCredDueDate__c` via Custom Report Type `PRM_IndividualApplicationWithAccount` |
| Operations dashboard (optional) | N/A | `PRM_NPDBActionNeeded_Dashboard` | Same report; daily refresh |
| Drill-down to Case Manager record | N/A | Case Manager record page → US-NPDB-02 right-rail findings text | Read-only findings surface rendering `Validation Details` (delivered by US-NPDB-02) |

---

## Preconditions

- **US-NPDB-01 is deployed.** The picklist value `NPDB Action Needed`, the two new Case Manager fields (`Validation Details`, `Validation Last Run`), and the metadata-driven validator are all live in the target org.
- The Salesforce report folder `PRM Credentialing Operations` exists, or an Administrator can create it as part of this deploy.
- The Salesforce public group `PRM Credentialing Ops` exists, or an Administrator can create it as part of this deploy.
- A Custom Report Type joining Case Manager (`IndividualApplication`) to Account exists, or an Administrator can deploy the new one bundled with this story.

---

## Acceptance Criteria

> **Format reminder.** Pattern A (Given/When/Then) for behaviour the persona observes in the Reports UI. Pattern B for the report's structural spec (filters / groupings / columns / formula / highlighting). Pattern C for permission sets / folder sharing.

### Report exists, is in the right folder, and renders correctly

**AC-3.1 — Report exists in the Credentialing Operations folder**

**Given** the report has been deployed,
**When** a Credentialing Specialist navigates from the App Launcher to **Reports**,
**Then** the folder **PRM Credentialing Operations** appears in their folder list,
**And** inside that folder a report titled **NPDB Action Needed by ReCred Due Date** is visible,
**And** the Specialist can open the report without any sharing-error message.

---

**AC-3.2 — Report renders one row per blocked Case Manager, grouped by due-date month**

**Given** one or more Case Managers currently sit in **NPDB Action Needed**,
**When** the Credentialing-Ops lead opens the report,
**Then** the report renders with one row per Case Manager,
**And** rows are grouped first by the practitioner's recredentialing-due month (calendar month, ascending), and within each month grouped by Record Type (e.g., ReCred, Initial Cred, PAR, Ancillary),
**And** the row order within each group is ascending by recredentialing-due date.

---

### Columns and Days-to-Due-Date formula

**AC-3.3 — Each row shows the operational columns the team needs** (Pattern B — report column spec)

The report displays the following columns in this order:

1. **Case Manager** — clickable link to the Case Manager record page
2. **Account / Practitioner** — clickable link to the Account record page
3. **Record Type** — the Case Manager's record type (e.g., `PRM_ReCredentialing`, `PRM_Practitioner`, `PRM_AncillaryAssessment`)
4. **Stage** — the Case Manager's stage (`PSV`, `QC`, `Committee`, etc.)
5. **Recredentialing-Due Date** — the practitioner's recredentialing-due date
6. **Days to Due Date** — a custom report formula (see AC-3.4)
7. **Created Date** — when the Case Manager was created
8. **Owner** — the current Case Manager owner
9. **Missing Data (preview)** — first ~250 chars of `Validation Details`, so the lead can see the gist without opening the record
10. **Last Validated** — `Validation Last Run` timestamp

---

**AC-3.4 — Days-to-Due-Date formula colours rows by urgency** (Pattern B — formula spec)

- **Custom report formula API name:** `FORMULA_DAYS_TO_DUE`
- **Display label:** Days to Due Date
- **Format:** Number, 0 decimals
- **Formula:** `Account.PRM_ReCredDueDate__c - TODAY()` (returns a count of days; negative when overdue)
- **Conditional highlighting on the column:**
  - Value ≤ 0 → **Red** background — practitioner is past due
  - Value 1 → 60 → **Yellow** background — inside the urgent window
  - Value > 60 → **Green** background — outside the urgent window
- **Summary metric shown in the header band:** row count, average Days to Due Date, earliest recredentialing-due date in scope
- **Chart at the top of the report:** horizontal bar of row count by month bucket

---

### Drill-down

**AC-3.5 — Clicking the Case Manager opens the record page with the US-NPDB-02 banner**

**Given** the report is open and at least one row is visible,
**When** the Credentialing Specialist clicks the Case Manager link on any row,
**Then** they land on that Case Manager's record page,
**And** the read-only findings text delivered in **US-NPDB-02** is visible in the right-rail with the exact same missing-data findings the report row's *Missing Data (preview)* column suggested,
**And** the Specialist can read exactly which records and fields to fix and navigate to those records to complete the report-to-fix loop.

---

### Filtering

**AC-3.6 — Built-in filter by record type works**

**Given** the report is showing rows across all practitioner record types,
**When** the Specialist applies the standard Salesforce report filter *Record Type = `PRM_ReCredentialing`* (or any other record type),
**Then** the report immediately re-renders showing only Case Managers of that record type,
**And** the groupings and column highlighting still apply.

---

### Live data behavior

**AC-3.7 — New failures appear on refresh**

**Given** the report is open and the nightly recredentialing batch (US-NPDB-01) routes a new practitioner to `NPDB Action Needed` overnight,
**When** the Specialist refreshes the report the next morning,
**Then** the new Case Manager appears in the correct due-date month group,
**And** the row count in the header band increases by one,
**And** the Specialist does not need to re-apply any filter.

---

**AC-3.8 — Resolved practitioners drop off automatically**

**Given** a Case Manager was in **NPDB Action Needed** yesterday and has since been auto-flipped to **Pending NPDB** by the US-NPDB-01 release flow (because the missing data was fixed),
**When** the Specialist refreshes the report,
**Then** that Case Manager no longer appears in the report,
**And** the row count is decreased accordingly,
**And** no manual archival or "mark resolved" step is needed.

---

### Folder permissions

**AC-3.9 — Permission set / folder sharing — read-only for Credentialing roles** (Pattern C)

- **System Administrator:**
  - Folder access: Manage
  - Report access: full edit
- **Public Group `PRM Credentialing Ops`** (members: `PRM_CredentialingUser`, `PRM_AncillaryCredSpecialist`, `PRM_NetworkManagementQC`):
  - Folder access: View
  - Report access: run + clone + save as personal copy; cannot edit the master
- **All other permission sets / profiles:** No folder access (the report is not surfaced to them).
- **Note:** Folder sharing is the only access mechanism — there is no `Modify All` requirement on the underlying objects, since the report reads existing fields with their existing FLS.

---

### Optional dashboard

**AC-3.10 — Optional Credentialing Ops dashboard surfaces the same view**

**Given** the optional dashboard `PRM_NPDBActionNeeded_Dashboard` is published,
**When** a Credentialing Specialist views the dashboard,
**Then** a single component shows the row count and the same horizontal-bar chart of NPDB Action Needed by recredentialing-due month that appears in the report header,
**And** the dashboard's daily-refresh schedule keeps it within ≤24 hours of the underlying data.

> _The dashboard is a nice-to-have. If the team prefers, ship the report only in Sprint A and follow up with the dashboard in Sprint B (see Estimated Effort)._

---

### Non-functional

**AC-3.11 — Report runs in well under five seconds at expected data volume**

**Given** the report contains ≤ 1,000 rows (the expected size based on historical NPDB error rates of 3–8 % of the active recredentialing population),
**When** the Specialist clicks Run,
**Then** the report renders in well under five seconds,
**And** the Salesforce row-limit warning does not appear at the bottom of the report.

---

## Technical Section — Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| Report `PRM_NPDBActionNeeded_ByReCredDueDate` | New Salesforce Summary Report | Path: `force-app/main/default/reports/PRM_CredentialingOps/PRM_NPDBActionNeeded_ByReCredDueDate.report-meta.xml`. Filters: `IndividualApplication.Status = 'NPDB Action Needed'` AND `Account.PRM_ReCredDueDate__c != null`. Groupings: first by `Account.PRM_ReCredDueDate__c` (Calendar Month, ascending), then by `IndividualApplication.RecordType.Name`. Columns: per §AC-3.3. Custom report formula `FORMULA_DAYS_TO_DUE` per §AC-3.4. Conditional highlighting on the formula column. Horizontal-bar chart of row count by month. | AC-3.1, 3.2, 3.3, 3.4, 3.6 |
| Custom Report Type `PRM_IndividualApplicationWithAccount` | New (only if not already present in the org) | Primary: `IndividualApplication`. Related: `Account` via `AccountId` lookup (Object A with related Object B, "with or without related records"). Available fields: standard IA fields + Account `PRM_ReCredDueDate__c`, `Name`, `OwnerId`. Path: `force-app/main/default/reportTypes/PRM_IndividualApplicationWithAccount.reportType-meta.xml`. | AC-3.1, 3.3 |
| Report folder `PRM Credentialing Operations` | New (only if not already present) | Path: `force-app/main/default/reports/PRM_CredentialingOps-meta.xml`. Shared at *View* level with the public group `PRM Credentialing Ops`. | AC-3.1, 3.9 |
| Public group `PRM Credentialing Ops` | New (only if not already present) | Members: `PRM_CredentialingUser`, `PRM_AncillaryCredSpecialist`, `PRM_NetworkManagementQC`. Deployed via standard `Group` metadata. | AC-3.9 |
| Optional Dashboard `PRM_NPDBActionNeeded_Dashboard` | New Dashboard | Path: `force-app/main/default/dashboards/PRM_CredentialingOps/PRM_NPDBActionNeeded_Dashboard.dashboard-meta.xml`. Single component sourcing the new report. Refresh: daily at 6 AM ET. | AC-3.10 |
| Permission set verifications | Modify `PRM_CredentialingUser`, `PRM_NetworkManagementQC` | Verify *View Reports in Public Folders* user permission is enabled. No FLS changes required (all consumed fields already accessible via US-NPDB-01). | AC-3.9 |
| Apex / Trigger / OmniStudio / LWC / Data Model changes | **None** | This story is pure config and metadata. All behavioural data is delivered by US-NPDB-01 and US-NPDB-02. | — |

---

## Definition of done

- [ ] Custom Report Type `PRM_IndividualApplicationWithAccount` deployed (or verified pre-existing).
- [ ] Report folder `PRM Credentialing Operations` deployed and shared at *View* with the public group `PRM Credentialing Ops`.
- [ ] Public group `PRM Credentialing Ops` deployed (or verified pre-existing) with the correct members.
- [ ] Report `PRM_NPDBActionNeeded_ByReCredDueDate` deployed with filters, groupings, columns, formula, and conditional highlighting per §AC-3.3 / §AC-3.4.
- [ ] Optional Dashboard `PRM_NPDBActionNeeded_Dashboard` deployed (if Sprint A includes it).
- [ ] Permission verification: a test Credentialing Specialist user can open the report and a test non-credentialing user cannot.
- [ ] QA-sandbox smoke test against eight scenarios: empty state, yellow band, red band (overdue), green band, exclusion of Pending NPDB CMs, removal after auto-flip, denied access for non-credentialing user, bulk render with 200 rows under five seconds.

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_NPDBActionNeeded_ByReCredDueDate` report | Report metadata | LOW | New report only — no existing report changes. |
| `PRM_IndividualApplicationWithAccount` Custom Report Type | Report Type | LOW | Additive — verify-or-create. |
| `PRM Credentialing Operations` report folder | Folder metadata | LOW | Additive — verify-or-create with read-only sharing. |
| `PRM Credentialing Ops` public group | Public Group | LOW | Additive — membership maps to existing perm sets. |
| `PRM_NPDBActionNeeded_Dashboard` | Dashboard metadata | LOW (optional) | Optional component; can ship in follow-up sprint. |
| Permission sets (`PRM_CredentialingUser`, `PRM_NetworkManagementQC`) | Config (verification only) | NONE | Verification of existing "View Reports in Public Folders" right; no schema change. |
| Underlying objects (`IndividualApplication`, `Account`) | Data model | NONE | Story consumes existing fields delivered by US-NPDB-01. |

---

## Clarification Questions (before implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| Q1 | Does a Custom Report Type joining `IndividualApplication` to `Account` already exist in the target org? | If yes, saves the report-type deploy step. If no, deploy `PRM_IndividualApplicationWithAccount` as part of this story. Default: assume NO. | Administrator |
| Q2 | Build a second report grouped by Owner (queue-management view) alongside the by-due-date report, or follow up with that later? | If yes, builds the Owner-grouped view in the same sprint. Default: not in this story; clone the report after launch if Ops requests it. | Ops Lead |
| Q3 | Exclude Case Managers whose Status flipped to `NPDB Action Needed` < 24 hours ago (debounce fresh failures so they don't surface until the next morning)? | If yes, add a date filter on the status-change timestamp. Default: no — Ops wants new failures visible immediately. | Ops Lead |
| Q4 | Parse the `Validation Details` JSON into structured columns (one column per field group) instead of the truncated preview? | Splits the JSON into per-group columns (Address Missing, NPI Missing, License Missing, etc.). Default: no for v1; the JSON preview is OK; revisit if Ops asks. | Ops Lead |
| Q5 | Configure email or Slack subscription at deploy time, or let admins subscribe manually via standard Salesforce report subscription? | Subscription at deploy time pushes the report to every Specialist's inbox each morning. Default: no — admins subscribe manually so Ops can opt in / opt out per role. | Ops Lead |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Verify or create Custom Report Type `PRM_IndividualApplicationWithAccount` | Config / metadata | **S–M** | S if already exists; M if creating from scratch. |
| Verify or create folder `PRM Credentialing Operations` + share with public group | Config / metadata | **S** | Standard folder + sharing. |
| Verify or create public group `PRM Credentialing Ops` | Config / metadata | **S** | Standard group. |
| Build the report metadata (filters, groupings, columns, formula, conditional highlighting, chart) | Metadata authoring | **L** | See report skeleton in §Technical Implementation. |
| Optional Dashboard `PRM_NPDBActionNeeded_Dashboard` + daily refresh schedule | Config | **M** | Optional — bundle in Sprint A or follow up. |
| Permission verification (View Reports in Public Folders) on 2 perm sets | Config | **S** | Verify only — no schema change. |
| Deployment + QA (eight manual scenarios per §Definition of done) | Deploy + QA | **M** | All config-only verification. |
| **Total** | | **~L (combined ≈ 1.5–2 dev-days incl. testing)** | **3 story points** (Fibonacci) — confidence High. Biggest risk: Custom Report Type creation may require Administrator coordination if the org does not allow self-service report-type creation. |

---

## Revision History

| Version | Date | Summary |
|---------|------|---------|
| v1 | 2026-06-01 | Initial draft (pre-template format). |
| v2 | 2026-06-03 | Rewrite to IBXQA Pre-Development Story Analysis Template (11 sections) + Linter-Conformant Summary appendix. Session `20260603_080758_51d1e394`. |
| v3 | 2026-06-03 | Rewrite to **User Story Solution Architect v1.6** skill. ACs converted to Pattern A (business-language Given/When/Then) and Pattern B/C (report column / formula / perm-set structured bullets). Report metadata names, field API names, SOQL, and Custom Report Type developer names removed from Given/When/Then lines and consolidated into the single **Technical Implementation (high-level)** table. Persona switched from "Credentialing Operations leader" to canonical **Credentialing Specialist (acting as Credentialing-Ops lead)** per the v1.6 Workspace Persona Cheatsheet pattern. |
| v4 | 2026-06-08 | Consistency update with US-NPDB-02 v4: drill-down target reworded from "validation banner with Fix/Add links" to a **read-only findings text** surface (no links). Scope table and AC-3.5 updated. No change to the report spec itself. |
