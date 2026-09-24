# USER STORY 08: Table View

**Persona:** Network Management QC Specialist (secondary: PDM Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-06](US-06_SummaryTilesCategoryChipsAndFilters_UserStory.md) · Business feedback 0.4 items 1–3 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) 0.3 (Export CSV removed)
**Build status:** ✅ Built in POC (QA) v0.4

---

## Story

**As a** Network Management QC Specialist,
**I want** a sortable table of a practice location's changes with who, when, what, effective dates, Case Manager and FHNatic case in their own columns,
**So that** I can scan and sort many changes quickly, e.g. by FHNatic case or by effective-from date, during a QC review.

**Why it matters:** Auditors often need a dense, sortable list rather than cards. Export was removed at the business's request, so the table is the list view.

---

## Acceptance Criteria

**AC-1 — The table shows who, when, what and references in columns**

**Given** the Network Management QC Specialist selects "Table",
**When** the table is shown,
**Then** its columns are: Changed on, Changed by, Category, Change, What happened, Old value, New value, Effective from, End date, Case Manager, FHNatic Case #,
**And** it respects every filter and search from US-06.

**AC-2 — Newest first by default, sortable by column**

**Given** the table is shown,
**When** the Network Management QC Specialist clicks the Effective from column header,
**Then** the rows sort by effective-from date,
**And** by default the table is sorted by Changed on, newest first,
**And** Changed on, Changed by, Category, Change, Effective from and FHNatic Case # are sortable.

**AC-3 — Links open the record and the Case Manager**

**Given** a row for "Network Amerihealth PPO removed" under Case Manager IA-0000033655,
**When** the Network Management QC Specialist clicks the "What happened" link or the Case Manager link,
**Then** the network record or the Case Manager opens in a new tab.

**AC-4 — Integration changes are labelled**

**Given** a row was changed by the MuleSoft Integration User,
**When** the table is shown,
**Then** Changed by reads "MuleSoft Integration User (Integration)".

**AC-5 — Dates are shown on the correct day**

**Given** a record's effective-from date is Feb 14, 2021 and its end date Sep 18, 2026,
**When** the table is shown in a US time zone,
**Then** Effective from shows Feb 14, 2021 and End date shows Sep 18, 2026.

**AC-6 — No export option**

**Given** the table is shown,
**When** the Network Management QC Specialist looks for an export,
**Then** no Export CSV button is offered.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `TABLE_COLUMNS` | LWC | `lightning-datatable`; `date` (Changed on), `date-local` (Effective from, End date), `url` (What happened → record; Case Manager → IA) | AC-1, AC-3, AC-5 |
| `tableRows` + `handleSort` | LWC | Client-side sort; Changed on sorts on the numeric `eventTime` | AC-2 |
| `actorLabel` | LWC | "{name} (Integration)" | AC-4 |
| Export CSV | Removed | `handleExportCsv`, `csvEscape`, `downloadCsv` deleted in 0.3 | AC-6 |

---

## Definition of done

- [ ] All 11 columns present and filled on the reference location (AC-1).
- [ ] Sorting on every sortable column works (AC-2).
- [ ] Dates correct in Central time (AC-5).
- [ ] Jest: columns and data (FHNatic, End date, integration label) pass.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the business get a report type for bulk extraction instead of export? Retire the orphaned "Practice Location History" report type. | New report type story | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Table columns and sort | LWC | M | |
| Jest | Test | S | |

**Total Estimated Effort:** M–L (about 0.5 day)
