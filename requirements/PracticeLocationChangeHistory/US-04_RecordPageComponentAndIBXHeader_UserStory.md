# USER STORY 04: Change History Component on the Practice Location Page (IBX-branded shell)

**Persona:** PDM Specialist (secondary: Network Management QC Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-02](US-02_HistoryServiceAndChangeRules_UserStory.md) · [Design prompt](../PracticeLocation_ChangeHistory_LWC_DesignPrompt.md) §6 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) 0.3–0.4 · Business feedback 0.4 ("more lively… use IBX styles") · `requirements/assets/brand-tokens.css`
**Build status:** ✅ Built in POC (QA) v0.4 · Remaining gap: not yet placed on the page or visually reviewed by the business (Clarification Questions 1–2)

---

## Story

**As a** PDM Specialist,
**I want** a Change History panel on the Practice Location record page, in IBX's look and feel, that tells me at a glance when the location last changed and who changed it,
**So that** I can go straight to the history I need, in a view that looks and behaves like the rest of IBX's tools.

**Why it matters:** The business called the first version clumsy. This story is the frame every view sits in: header, states, footnotes and brand styling. Views, filters and data are covered in US-05 to US-08.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Practice Location record page, History tab | N/A | N/A | US-02 service |

---

## Acceptance Criteria

**AC-1 — The panel is available on the Practice Location page**

**Given** an administrator edits the Practice Location record page,
**When** they add "PRM Practice Location Change History" to the History tab,
**Then** the panel appears on every practice location record,
**And** it isn't offered on other kinds of record.

**AC-2 — The header shows the location and its last change**

**Given** a practice location's last change was made by Anshaj Sinha on Sep 17, 2026 at 10:59 AM,
**When** a PDM Specialist opens the History tab,
**Then** the header reads "Change History" with the location's name,
**And** it shows "Last change Sep 17, 2026, 10:59 AM · Anshaj Sinha".

**AC-3 — Refresh reloads the history**

**Given** a colleague has just changed the location in another tab,
**When** the PDM Specialist clicks Refresh in the header,
**Then** the history reloads and shows the new change,
**And** any loaded archive and expanded cards are reset.

**AC-4 — Loading is visible**

**Given** the history is being retrieved,
**When** the History tab opens,
**Then** a loading indicator labelled "Loading change history" is shown until the history arrives.

**AC-5 — A location with no tracked changes points to the archive**

**Given** a practice location has no changes in recent history,
**When** the History tab opens,
**Then** it says "No tracked changes in recent history",
**And** it suggests "Load older changes" (US-03).

**AC-6 — Filters that hide everything offer a way back**

**Given** the PDM Specialist's filters match no changes,
**When** the view refreshes,
**Then** it says "No changes match the current filters",
**And** a "Show all time" link widens the date range.

**AC-7 — Errors are explained**

**Given** the history can't be loaded,
**When** the History tab opens,
**Then** a red alert reads "Unable to load change history" followed by the reason.

**AC-8 — Standing footnotes explain the limits**

**Given** any practice location history is shown,
**When** the PDM Specialist scrolls to the bottom,
**Then** footnotes state that records deleted outright may not appear,
**And** that practitioner specialty at a location is not history-tracked,
**And** that practitioner-level network and taxonomy changes are planned after the POC.

**AC-9 — IBX look and feel (UI specification)**

- **Header:** gradient from IBX Navy `#024D76` to IBX Process Blue `#008CCC`, white text, clock icon, heading font Alright Sans (fallback Arial).
- **Primary / links:** IBX Process Blue, accessible variant `#007DB6`; tints `#E6F4FB`.
- **Accent:** IBX Teal `#00AEC7`.
- **Status colours:** add = IBX green `#4D8B3F`, remove = IBX red `#EA1D2C` (text `#B0121F`), scheduled / warning = IBX orange `#F16935` (text `#9C3D18`), integration = IBX purple `#924799`.
- **Surfaces:** cards on `#F7F9FB` with 8 px radius and a soft shadow; neutrals from the IBX token file.
- **Rule:** colour is never the only signal; every coloured element also carries text.

**AC-10 — Usable by keyboard and screen reader**

**Given** a PDM Specialist navigates with the keyboard only,
**When** they tab through the panel,
**Then** every tile, chip, section header and "show more" control is reachable and shows a visible focus ring,
**And** controls announce whether they're pressed or expanded.

**AC-11 — Page settings**

- **Default View:** Timeline (options: Timeline, By category, Table)
- **Default Date Range:** 90 days (options: 30, 90, 365, all)
- **Component Height:** 720px (scrolls within the panel)

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `lwc/prmPracticeLocationHistory` | New LWC | `lightning__RecordPage`, object `HealthcareFacility`; imperative calls to `getHistory` on connect | AC-1, AC-4 |
| `prmPracticeLocationHistory.html` | LWC template | Custom `<article class="plh">` with branded header, `lastChange` getter, refresh `lightning-button-icon` (bare-inverse), states, footnotes | AC-2–AC-8 |
| `prmPracticeLocationHistory.css` | LWC CSS | IBX tokens on `:host` (`--plh-brand`, `--plh-brand-dark`, …) copied from `requirements/assets/brand-tokens.css`; `:focus-visible` outlines; icon colour via `--slds-c-icon-color-foreground-default` | AC-9, AC-10 |
| `prmPracticeLocationHistory.js-meta.xml` | LWC meta | Properties `defaultView`, `defaultDateRange`, `pageHeight` | AC-11 |
| Export CSV | Removed (0.3) | Business request | — |

---

## Definition of done

- [ ] Panel placed on the History tab of the Practice Location page (App Builder) and visible on any location (AC-1).
- [ ] Header, loading, empty, no-match and error states verified (AC-2–AC-7).
- [ ] Business sign-off on the IBX look at desktop and narrow widths (AC-9).
- [ ] Keyboard-only walkthrough passes (AC-10).
- [ ] Jest tests for header, empty and error states pass (17 total for the bundle).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the panel **replace** the standard History related list and the NPI FlexCard on the History tab, or sit beside them? | Page layout and training | Product |
| 2 | Is Alright Sans available in Lightning for IBX users, or should headings stay on the Arial fallback? | Typography only | Brand / UX |
| 3 | Is an AmeriHealth-themed variant needed (the token file supports it)? | Adds a brand switch property | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Shell, header and states | LWC | L | |
| IBX token stylesheet | LWC CSS | L | |
| Page placement | Config | S | App Builder |
| Jest (shell states) | Test | M | |

**Total Estimated Effort:** XL (about 1.5–2 days)
