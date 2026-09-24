# USER STORY 06: Summary Tiles, Category Chips and Filters

**Persona:** Network Management QC Specialist (secondary: PDM Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-05](US-05_TimelineView_UserStory.md) · [US-07](US-07_ByCategoryView_UserStory.md) · [US-08](US-08_TableView_UserStory.md) · Business feedback 0.4 item 4 (by category) · Decision D4 (show integration users)
**Build status:** ✅ Built in POC (QA) v0.4

---

## Story

**As a** Network Management QC Specialist,
**I want** a summary of what was added and removed at a practice location, plus quick filters by category, change type, date, who changed it and free-text search,
**So that** I can audit a location's changes quickly, e.g. "every network removed in the last 30 days by a person, not an integration".

**Why it matters:** A group location can have 700+ changes. Without counts and filters, the timeline is too long to audit.

---

## Acceptance Criteria

**AC-1 — Summary tiles count adds and removes for the current filters**

**Given** the filtered changes include 1 practitioner added, 1 network removed and 1 field update,
**When** the summary tiles are shown,
**Then** they read "Practitioners +1 added −0 removed", "Networks +0 added −1 removed", "Taxonomies +0 added −0 removed" and "Field updates 1",
**And** the counts update whenever a filter changes.

**AC-2 — Clicking a category tile filters to that category**

**Given** the Networks tile is shown,
**When** the Network Management QC Specialist clicks it,
**Then** only network changes are shown and the tile is highlighted,
**And** clicking it again returns to all categories.

**AC-3 — Category chips show a count for each category**

**Given** a location's history covers the location itself, practitioners and networks,
**When** the chips are shown,
**Then** there is an "All" chip plus one chip per configured category, each with its number of changes,
**And** the counts respect every filter except the category itself.

**AC-4 — Clicking a chip filters to that category**

**Given** the chips are shown,
**When** the Network Management QC Specialist clicks "Practice Location",
**Then** only changes to the location's own details are shown,
**And** that chip is highlighted and announced as selected.

**AC-5 — Search matches names, people and case numbers**

**Given** a change was made under FHNatic case 711316,
**When** the Network Management QC Specialist searches "711316",
**Then** only changes under that FHNatic case are shown,
**And** search also matches practitioner, network and taxonomy names, field names, values, the person who made the change, and the Case Manager number.

**AC-6 — Filter by change type**

**Given** the history contains Added, Removed and Updated changes,
**When** the Network Management QC Specialist picks "Removed" from the Change filter,
**Then** only removals are shown,
**And** the Change filter lists only change types present in this location's history.

**AC-7 — Filter by date range (default last 90 days)**

**Given** a location has changes from 7 days ago and 200 days ago,
**When** the history first opens,
**Then** only the change from 7 days ago is shown,
**And** "When" offers Last 30 days, Last 90 days, Last 12 months and All time.

**AC-8 — Filter by who made the change**

**Given** changes were made by both people and integration accounts,
**When** the Network Management QC Specialist selects "People" under "Changed by",
**Then** integration changes are hidden,
**And** "Integration" shows only integration changes, and "Everyone" shows both.

**AC-9 — Show only adds and removes**

**Given** the history mixes adds, removes and field updates,
**When** the Network Management QC Specialist turns on "Only adds and removes",
**Then** field updates are hidden,
**And** added, removed, scheduled-removal, reinstated, deactivated and reactivated changes stay visible.

**AC-10 — The result count reflects the filters**

**Given** 3 of 772 changes match the filters,
**When** the filters are applied,
**Then** the toolbar reads "3 of 772 changes",
**And** with no filters it reads "772 changes".

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `kpiTiles` getter + `handleKpiClick` | LWC | Tiles for `KPI_CATEGORIES` (Practitioners, Networks, Taxonomies) + Field updates; toggle `categoryFilter`; `aria-pressed` | AC-1, AC-2 |
| `categoryChips` getter + `handleCategoryChip` | LWC | `filterEvents(false)` counts ignore the category filter; one chip per response `categories`; icons per category | AC-3, AC-4 |
| `filterEvents(applyCategory)` | LWC | Date cutoff, category, change type, adds/removes, actor, search haystack (sentence, subject, context, field, values, actor, Case Manager, FHNatic) | AC-5–AC-9 |
| `lightning-combobox` ×2, `lightning-radio-group` (Changed by), `lightning-input` search + toggle | LWC | Filter controls; paging resets on change | AC-5–AC-9 |
| `resultSummary` | LWC | "x of y changes" | AC-10 |

---

## Definition of done

- [ ] Tile and chip counts match the filtered list on the reference location (AC-1, AC-3).
- [ ] Every filter narrows all three views consistently (Timeline, By category, Table).
- [ ] Search by FHNatic number verified (AC-5).
- [ ] Jest: tiles, chips, search, change type, date range, actor and toggle pass.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should filters be remembered between visits (per user)? | Adds local persistence | Product |
| 2 | Add NPI and Info Codes tiles, or keep three? | Tile row width | UX |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Tiles and chips | LWC | L | |
| Filter logic and controls | LWC | L | |
| Jest | Test | M | |

**Total Estimated Effort:** XL (about 1.5 days)
