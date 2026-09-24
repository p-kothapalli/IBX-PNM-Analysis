# USER STORY 07: By Category View

**Persona:** Network Management QC Specialist (secondary: PDM Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-06](US-06_SummaryTilesCategoryChipsAndFilters_UserStory.md) · Business feedback 0.4 item 4 ("Can we show these by category?")
**Build status:** ✅ Built in POC (QA) v0.4 · Remaining gap: business visual review

---

## Story

**As a** Network Management QC Specialist,
**I want** a practice location's changes organised by category (Practitioners, Networks, Taxonomies, NPI, Info Codes, Provider Features, Associations, and the location itself), each with its own add, remove and update counts,
**So that** I can review one kind of change at a time, e.g. all network changes, and confirm nothing was missed.

**Why it matters:** This was an explicit business request. The timeline answers "what happened when"; this view answers "what happened to the networks".

---

## Acceptance Criteria

**AC-1 — One section per category, in the configured order**

**Given** a location's filtered history includes Practice Location, Practitioners and Networks changes,
**When** the Network Management QC Specialist selects "By category",
**Then** there is one section for each of those three categories, in the configured category order,
**And** categories with no matching changes aren't shown.

**AC-2 — Each section header summarises the category**

**Given** the Networks section contains 1 removal and no other changes,
**When** the view is shown,
**Then** its header reads "Networks · 1 change" with "+0 added", "−1 removed" and "0 updates".

**AC-3 — Each row shows when, who, what and the related references**

**Given** a practitioner was added by Pat Specialist under Case Manager IA-0001 (FHNatic FHN-7788),
**When** the Practitioners section is shown,
**Then** the row shows the date and time, the relative time and "by Pat Specialist",
**And** an "Added" label and the sentence linking to the record,
**And** "Effective from", "End date" (for removals), "Case Manager IA-0001" and "FHNatic Case # FHN-7788".

**AC-4 — Sections can be collapsed and expanded**

**Given** the Practice Location section is open,
**When** the Network Management QC Specialist clicks its header,
**Then** its rows are hidden and the header is announced as collapsed,
**And** clicking again shows the rows.

**AC-5 — Large sections preview 10 rows**

**Given** the Practitioners section has 603 changes,
**When** the view is shown,
**Then** the 10 most recent are listed with "Show all 603",
**And** clicking it lists every change in that section, with "Show fewer" to return.

**AC-6 — Filters apply to this view**

**Given** "Only adds and removes" is on and the date range is Last 30 days,
**When** the Network Management QC Specialist switches to "By category",
**Then** each section and its counts reflect only matching changes.

**AC-7 — Integration changes are marked in rows**

**Given** a row's change was made by an integration account,
**When** the section is shown,
**Then** the row shows "by {integration name}" with an "Integration" tag.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `categorySections` getter | LWC | Groups `filteredEvents` by category; order = response `categories` (config Sort Order), then any extras; counts via `countByCategory` | AC-1, AC-2, AC-6 |
| `handleToggleSection` / `collapsedCategories` | LWC | Section header is a `<button>` with `aria-expanded` and a chevron icon | AC-4 |
| `handleToggleSectionRows` / `expandedCategories` | LWC | `CATEGORY_PREVIEW_COUNT = 10` | AC-5 |
| Row template | LWC HTML | Grid: when/who column, pill, sentence + old → new, `<dl>` with Effective from, End date, Case Manager link, FHNatic | AC-3, AC-7 |
| View option | LWC | `viewOptions` adds "By category" (`category`); page property `defaultView` accepts `category` | — |

---

## Definition of done

- [ ] Sections, counts and order verified on the reference location (AC-1, AC-2).
- [ ] Row detail matches the Timeline for the same change (AC-3).
- [ ] Collapse and "Show all" work by mouse and keyboard (AC-4, AC-5).
- [ ] Jest: sections, counts, row detail and collapse pass.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should sections start collapsed when a category has more than N changes? | First-view length | UX |
| 2 | Within Practitioners, should rows be sub-grouped by practitioner? | Adds a second grouping level | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Section model and toggles | LWC JS | M | |
| Section and row template + CSS | LWC HTML/CSS | L | |
| Jest | Test | M | |

**Total Estimated Effort:** L–XL (about 1 day)
