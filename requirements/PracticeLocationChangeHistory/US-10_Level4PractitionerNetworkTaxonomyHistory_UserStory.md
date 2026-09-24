# USER STORY 10 (post-POC): Practitioner-Level Network and Taxonomy Changes at a Location (Level 4)

**Persona:** Network Management QC Specialist (secondary: PDM Specialist)
**Priority:** P2 (post-POC per Decision D1)
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-01](US-01_HistoryConfigurationMetadata_UserStory.md) AC-3 (inactive Level 4 row) · [US-02](US-02_HistoryServiceAndChangeRules_UserStory.md) · [Design prompt](../PracticeLocation_ChangeHistory_LWC_DesignPrompt.md) Decision D1 · change log follow-up F4
**Build status:** ⏸ **Deferred.** The configuration row exists but is inactive.

---

## Story

**As a** Network Management QC Specialist,
**I want** a practice location's history to show when a network or taxonomy is added to or removed from a specific practitioner at that location,
**So that** I can confirm which practitioners are in which networks at the location, the level at which claims and directory decisions are actually made.

**Why it matters:** Location-level network and taxonomy changes are shown today. The practitioner × taxonomy × network rows at a location ("Level 4") are the most detailed and highest-volume level (about 8.0 million records in QA; 1,795 at Hospitalists Pottstown alone).

---

## Acceptance Criteria

**AC-1 — A practitioner-level network change is shown in plain English**

**Given** network Amerihealth PPO was added for Dr. Jane Doe at a practice location under taxonomy Family Medicine,
**When** a Network Management QC Specialist opens the location's history,
**Then** they see "Network Amerihealth PPO added (Jane Doe · Family Medicine)" under the "Practitioner Networks" category,
**And** it shows who made the change, when, the effective-from date, the Case Manager and the FHNatic case.

**AC-2 — Removals and scheduled removals follow the same rules**

**Given** that network is end-dated for Dr. Jane Doe with a future date,
**When** the history is loaded,
**Then** it reads "Network Amerihealth PPO scheduled for removal, effective {date} (Jane Doe · Family Medicine)",
**And** the change-type rules match US-02 AC-2.

**AC-3 — Large group locations stay responsive**

**Given** a practice location with about 1,800 practitioner-level network records,
**When** a Network Management QC Specialist opens the history,
**Then** the history is shown within 5 seconds,
**And** if the category is capped, the "showing the most recent records only" warning names "Practitioner Networks".

**AC-4 — The category can be turned on and off by configuration**

**Given** the Level 4 category is inactive,
**When** an administrator activates it,
**Then** practitioner-level changes appear with no code deployment,
**And** deactivating it hides them again.

**AC-5 — The category appears in the summary and chips**

**Given** the Level 4 category is active,
**When** the history is shown,
**Then** a "Practitioner Networks" chip with its count is offered,
**And** its changes appear in the By category view as their own section.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PracticeLocationHistoryConfig.PractitionerTaxonomyNetwork` | CMDT record | Set `PRM_IsActive__c = true`; set `PRM_MaxRecords__c` after the volume test | AC-4 |
| `PRM_PracticeLocationHistoryConfig__mdt` | CMDT field | **New** `PRM_SecondaryContextFieldPath__c` (Text 255) so the context can show practitioner **and** taxonomy (`Practitioner.Name` + `PRM_Taxonomy__r.Name`) | AC-1 (US-01 Clarification Question 3) |
| `PRM_PracticeLocationHistoryService.toChildRecord` / `PRM_PracticeLocationHistoryDeriver.composeSentence` | Apex | Join two context values with " · " | AC-1, AC-2 |
| History query | Apex | Uses the existing one-query-per-object read (shared with the network and taxonomy rows); child IN list up to the cap; measure query rows and CPU at 1,800 and at the largest group location | AC-3 |
| KPI tiles | LWC | Decide whether to add a "Practitioner Networks" tile | Clarification Question 2 |

---

## Definition of done

- [ ] Volume test on the largest group locations (1,800+ Level 4 rows) within 5 s and under 50,000 query rows.
- [ ] Sentences show practitioner and taxonomy context (AC-1).
- [ ] Activation and deactivation by config verified (AC-4).
- [ ] Apex coverage stays ≥ 85%.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What cap (Max Records) is acceptable for Level 4 per location? | Completeness vs speed | Product / Technical |
| 2 | Add a "Practitioner Networks" summary tile? | Tile row | UX |
| 3 | Should Level 4 changes be grouped under the practitioner in the By category view? | View design | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Secondary context field + sentence | CMDT field + Apex | M | |
| Activate row + cap | Config | S | |
| Volume and performance test | Testing | L | |
| LWC chip/tile decisions | LWC | S | |

**Total Estimated Effort:** L–XL (about 1.5 days)
