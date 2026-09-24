# USER STORY 05: Timeline View: Who, When and What Changed

**Persona:** PDM Specialist (secondary: Network Management QC Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-02](US-02_HistoryServiceAndChangeRules_UserStory.md) · [US-04](US-04_RecordPageComponentAndIBXHeader_UserStory.md) · Business feedback 0.4 items 1 (by who / at what time), 2 (effective from), 3 (FHNatic case number) · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) §1.1
**Build status:** ✅ Built in POC (QA) v0.4 · Remaining gap: business visual review

---

## Story

**As a** PDM Specialist,
**I want** a timeline of changes where each change leads with who made it and exactly when, and shows each affected record's effective dates, Case Manager and FHNatic case,
**So that** I can confirm my own updates landed correctly and explain any change to a colleague or provider without digging through records.

**Why it matters:** The business said the first timeline was "clumsy" and didn't clearly show who changed what and when. This is the default view.

---

## Acceptance Criteria

**AC-1 — Changes are grouped by day, newest first**

**Given** a practice location has changes on several days,
**When** a PDM Specialist opens the Timeline,
**Then** changes are shown newest first under day headings such as "Thursday, September 17, 2026",
**And** each day heading shows how many changes it contains.

**AC-2 — Each change leads with who made it and when**

**Given** Anshaj Sinha made a change on Sep 17, 2026 at 10:59 AM,
**When** the Timeline is shown on Sep 24,
**Then** the change card starts with Anshaj Sinha's initials and name,
**And** it shows "Thu, Sep 17, 2026, 10:59 AM · 7 days ago".

**AC-3 — Integration changes are clearly marked**

**Given** a change was made by the MuleSoft Integration User,
**When** the Timeline is shown,
**Then** the card shows an integration icon instead of initials,
**And** an "Integration" tag appears next to the name.

**AC-4 — The Case Manager and FHNatic case are shown on the card**

**Given** a change was made under Case Manager IA-0000129625, whose FHNatic case number is 711316,
**When** the Timeline is shown,
**Then** the card shows "Case Manager IA-0000129625" as a link that opens the Case Manager,
**And** it shows "FHNatic Case # 711316".

**AC-5 — A multi-record change is summarised, then itemised**

**Given** a PDM Specialist end-dated 14 records in one submission,
**When** the Timeline is shown,
**Then** one card reads "14 changes · 3 added · 11 removed",
**And** the categories involved are tagged (e.g. "Practitioners", "Networks"),
**And** the first 3 changes are listed with "Show all 14 changes" to expand.

**AC-6 — Each line shows the change type, what happened and the record's dates**

**Given** a card lists "Practitioner Archana Machavarapu scheduled for removal, effective 9/18/2026",
**When** the PDM Specialist reads that line,
**Then** a coloured label reads "Scheduled removal",
**And** the sentence links to the practitioner-at-location record,
**And** it shows "Effective from Feb 14, 2021" and "End date Sep 18, 2026".

**AC-7 — Field updates show old and new values**

**Given** a practitioner's role changed from Specialist to PCP,
**When** the Timeline is shown,
**Then** the line reads "Practitioner …: Practitioner Role changed",
**And** it shows "Specialist" struck through, then an arrow, then "PCP",
**And** a missing value is shown as "—".

**AC-8 — The card edge reflects the most significant change**

**Given** a card contains both an addition and a removal,
**When** the Timeline is shown,
**Then** the card's left edge is red (removal),
**And** cards with only additions are green, only scheduled removals orange, only reinstatements teal, and only updates blue.

**AC-9 — Long histories load in pages**

**Given** a location has more than 25 changes (cards) matching the filters,
**When** the Timeline is shown,
**Then** the first 25 cards appear with "Show more changes" and a count of how many remain,
**And** each click shows 25 more.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `prmPracticeLocationHistory.js`: `timelineDays`, `changeGroups`, `toGroupView` | LWC | Group by `groupKey`, then by day; `GROUP_PAGE_SIZE = 25`; `COLLAPSED_EVENT_COUNT = 3` | AC-1, AC-5, AC-9 |
| `toViewEvent`, `relativeTime`, `initials` | LWC | Tone per change type (`TYPE_TONES`), relative time ("min / hr ago", "Yesterday", "N days / mo / yr ago"), initials | AC-2, AC-6, AC-8 |
| Card priority for edge colour | LWC | `TONE_PRIORITY = remove > schedule > add > restore > warn > update` | AC-8 |
| Card template | LWC HTML | Avatar, name + tags, `lightning-formatted-date-time` (weekday, date, time), Case Manager link chip, FHNatic chip, headline, category tags, change list with pill, sentence link, old → new, `<dl>` Effective from / End date | AC-2–AC-7 |
| Date-only values | LWC | `lightning-formatted-date-time time-zone="UTC"` so dates don't shift | AC-6 |
| Data | Apex (US-02) | `actorName`, `isIntegration`, `caseManagerName`, `fhnaticCaseNumber`, `recordEffectiveFrom`, `effectiveDate` | — |

---

## Definition of done

- [ ] Who and when lead every card, with exact date/time and relative time (AC-2).
- [ ] Case Manager link and FHNatic number visible where they exist (AC-4); verified on the reference location (206 changes carry FHNatic).
- [ ] Effective from and End date show the correct day (AC-6).
- [ ] Expand and paging work (AC-5, AC-9).
- [ ] Jest: who/when, dates, references, grouping, expand pass.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Show 3 changes per card before "Show all", or more? | Card height | UX |
| 2 | Should the relative time switch to an absolute date only after N days? | Readability | UX |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Timeline grouping and paging | LWC JS | L | |
| Card template and styling | LWC HTML/CSS | XL | |
| Jest | Test | M | |

**Total Estimated Effort:** XL (about 2 days)
