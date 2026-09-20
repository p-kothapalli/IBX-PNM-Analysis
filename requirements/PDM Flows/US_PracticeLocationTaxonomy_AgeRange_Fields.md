# USER STORY: Capture Patient Age Range at the Practice Location Taxonomy Level (with Pediatric Default)

**Persona:** PDM Specialist
**Priority:** P1
**Type:** Enhancement (reuse standard fields + defaulting)
**Object:** `HealthcareFacilityNetwork` — Record Type **`PRM_FacilityTx`** (label *"Practice Location Taxonomy"*; note `PRM_RecordTypeName__c` stores the developer name `PRM_FacilityTx`, not the label)
**OmniScript(s):** `PRM_PDMManualUpdatePracticeLocation_English`, `PRM_PDMManualUpdate_English`, `PRM_AttestationFlow_English` (age today lives at the location level)
**Integration Procedures:** `PRM_ProcessPracticeLocationTaxonomyData` (PL-Tax create), `PRM_PdmHfnHelper`
**DataRaptors:** `PRMDRCreatePracticeLocationTaxonomy`, `PRMDRTransformPracticeLocationTaxonomyData`, `PRMTransPDMPPLTaxNw`, `PRMTransAccountCreationPPLTaxNw`
**Apex:** `PRM_HCFacilityNetworkTriggerHelper` (before-insert defaulting), `PRM_BCBSARecordSyncSubServiceHandler` (roster sync)
**Relevant Requirements:** Sibling requirement — *Member-Selectable PCP on two taxonomies at the same practice location* (the two changes are coupled; see Clarification Q1)

---

## Story

**As a** PDM Specialist,
**I want** each practice location **taxonomy** record to carry its own **Lowest Valid Age** and **Highest Valid Age**, defaulted to **0–18** when the taxonomy is a **pediatric physician** taxonomy and **0–125** for every other taxonomy,
**So that** the age range a provider accepts is accurate **per specialty at a location** — instead of one blunt range shared across all taxonomies — and directory/PCP-selection consumers show the correct accepted ages for each taxonomy.

**Why it matters:** Today the accepted patient age range lives only on the practice **location** (`HealthcareFacility`) as a single manually-attested value, so a location with both a pediatric and an adult taxonomy can only publish one age band. With member-selectable PCP now allowed on two taxonomies at the same location, each taxonomy needs its own age band (e.g., a pediatric PCP taxonomy 0–18 alongside an adult PCP taxonomy 0–125) so members are matched to the right provider by age.

---

## Data Synchronization Between Age Levels (Critical — No Existing Sync)

> **Reviewers commonly assume a roll-up already exists. It does not.** Verified live on 2026-07-06 across every trigger, Apex class, and DataRaptor.

Age (`PRM_AgeMin__c` / `PRM_AgeMax__c`) is **not** automatically kept in sync between **practitioner-at-location** (`HealthcarePractitionerFacility`, HCPF) and the **practice location** (`HealthcareFacility`). There is **no roll-up, no roll-down trigger, and no aggregation**. Each level's age is written **independently** at OmniScript/IP save time, from **different nodes of the same submission payload**:

| Source payload node | DataRaptor(s) | Writes age to | Direction |
|---|---|---|---|
| `Locations` | `PRMLoadFacLocAddAccountCreation`, `PRMUpdateHPTxnmFcltyPracFclty` | `HealthcareFacility` (location) | payload → location |
| `PPLRecords` / `HCPF` | `PRMCreateHCPFForAdmittingPriviliges`, `PRMLoadHCPFRecordswithConcierge`, `PRMLoadRecordsHCPFRecords` | `HealthcarePractitionerFacility` (HCPF) | payload → HCPF |

Supporting evidence:
- **No trigger touches age** — a search of every `*Trigger*` class/trigger for `AgeMin`/`AgeMax` returns nothing.
- **Only one Apex class assigns age** — `PRM_AttestationProviderServiceHelper` writes `HealthcareFacility.PRM_AgeMin__c/PRM_AgeMax__c` from the attestation input (location level only); it never derives location age from HCPF or vice-versa.
- **Cross-ref batch helpers copy HCPF → HCPF only** (`PRM_ManualUpdatesCrossRefBatchHelper`, `PRM_CrossRefBatchHelper`) when cloning practitioner-facility records; no location aggregation.
- **`PRM_IPUtility` reads the location's age** (`HealthcareFacility.PRM_AgeMin__c/PRM_AgeMax__c`) — not HCPF — to build the cross-reference / NPPES payload, so the **location is the outbound source of truth** for directory/NPPES.

**Implication for this story:** introducing age on the **taxonomy** (`HealthcareFacilityNetwork` / `PRM_FacilityTx`) adds a **third, independent age holder** with **no existing propagation** to or from the location or HCPF. Any reconciliation is **net-new** and must be explicitly decided — source of truth, propagation direction, and conflict rules when two member-selectable taxonomies coexist at one location (see Clarification Q4 and Q7).

---

## Org Verification (QA sandbox — `prashanth.kothapalli@ibx.com.pie.qa`)

Verified live via CLI `describe` / SOQL (2026-07-06):

- **Reusable standard fields already exist on `HealthcareFacilityNetwork`** — no need to create custom age fields:
  - `LowestValidAge` (int, createable, updateable, nillable, no default) — help text: *"Indicates the lowest age of patient that this facility network is applicable for."*
  - `HighestValidAge` (int, createable, updateable, nillable, no default) — help text: *"Indicates the highest age of patient that this facility network is applicable for."*
- These fields are **empty across all 8,871,450 HFN records** (`COUNT(LowestValidAge)=0`, `COUNT(HighestValidAge)=0`), so adopting them has no data-collision risk. `GenderRestriction` is likewise unused (0).
- The **Practice Location Taxonomy** record type is `PRM_FacilityTx` (**482,109** records); member-selectable PCP records are `PRM_FacilityTx` + `PRM_PractitionerRole__c = 'PCP'`, and their `LowestValidAge`/`HighestValidAge` are currently `null`. Records with `PRM_MemberSelectablePCP__c = true`: **9,034**. (`PRM_FacilityPractitionerTxNw` = 7,510,061.)
- **Decision:** **reuse `LowestValidAge` / `HighestValidAge`** (Years, whole numbers) instead of creating `PRM_AgeMin__c` / `PRM_AgeMax__c` on HFN. This keeps the platform-standard fields and avoids new custom metadata. (Trade-off: standard fields **cannot carry a declarative default value**, so all defaulting must be done in Apex/DR/OmniScript — see Technical Section.)

---

## Scope

| Flow | Component | Affected Step / Path | Data Target |
|------|-----------|----------------------|-------------|
| PDM Manual Update – Practice Location | `PRM_PDMManualUpdatePracticeLocation_English` | Add/Update PL Taxonomy (`AddPLT` block) | `HealthcareFacilityNetwork` (`PRM_FacilityTx`) |
| PDM Manual Update | `PRM_PDMManualUpdate_English` | `AddPLT` block | `HealthcareFacilityNetwork` (`PRM_FacilityTx`) |
| PL-Taxonomy creation (all paths) | `PRM_ProcessPracticeLocationTaxonomyData` → `PRMDRCreatePracticeLocationTaxonomy` | Record insert | `HealthcareFacilityNetwork` (`PRM_FacilityTx`) |
| Roster / BCBSA sync | `PRM_BCBSARecordSyncSubServiceHandler` | PL-Tax record creation | `HealthcareFacilityNetwork` (`PRM_FacilityTx`) |

**In scope:** Adopt the standard age fields on the PL-Taxonomy (`PRM_FacilityTx`) record type, taxonomy-driven defaulting, validation, UI capture in the PDM PL-Taxonomy flow, and populating the fields on every PL-Tax create path.
**Out of scope:** The existing `HealthcareFacility.PRM_AgeMin__c/PRM_AgeMax__c` location-level fields (they remain as-is; see Clarification Q4). Member-selectable-PCP uniqueness change is a sibling story. Any roll-up/roll-down propagation between taxonomy, location, and HCPF age (net-new; deferred pending Q7).

---

## Current State (from codebase + QA org)

### `HealthcareFacility` (Practice Location) — where age lives today
- `PRM_AgeMin__c` (Number, default **0**) and `PRM_AgeMax__c` (Number, default **125**), plus `PRM_AgeMinUnit__c` / `PRM_AgeMaxUnit__c` (restricted picklist, only `Years`, default `Years`); all history-tracked.
- Values are **manually attested**, not computed — captured via OmniScript inputs `PatientAgeMinimum` / `PatientAgeMaximum` (`PRM_AttestationFlow`, `PRM_PDMManualChanges`, `PRM_AccountCreation`) and written to `HealthcareFacility` by DataRaptors (`PRMDRUpdatePracLocData`, `PRMDRPLocationAddressFacility`) and `PRM_AttestationProviderServiceHelper`.
- Validation: `PRM_PatientMinAge` (0–125), `PRM_PatientMaxAge` (1–125). Attestation formula `AgeRangeValid = INTEGER(min) < INTEGER(max)`.
- All 382,893 location records have the fields populated (field-level default makes them non-null). **No taxonomy-driven defaulting exists anywhere** — the pediatric 0–18 rule is net-new.

### `HealthcarePractitionerFacility` (Practitioner-at-location, HCPF) — where age is copied today
- Carries its own `PRM_AgeMin__c` / `PRM_AgeMax__c` / `PRM_AgeMinUnit__c` / `PRM_AgeMaxUnit__c`, populated independently from the `PPLRecords`/`HCPF` payload node (see Data Synchronization section). ~47% of HCPF records have age populated in QA.
- **Not** derived from, and does not feed, the location age — the two are parallel copies written by the same flow.

### `HealthcareFacilityNetwork` (Practice Location Taxonomy = `PRM_FacilityTx`) — target
- Standard age fields `LowestValidAge` / `HighestValidAge` exist but are **unused/empty** (see Org Verification). No custom age fields present. Comparable restriction fields: `GenderRestriction`, `PanelStatus`, `PanelLimit`. Member-selectable is `PRM_MemberSelectablePCP__c`; specialty is `PRM_Taxonomy__c` (Lookup → `CareTaxonomy`); role is `PRM_PractitionerRole__c` (PCP/Specialist).
- Trigger (`PRM_HCFacilityNetworkTriggerHelper`) already queries `CareTaxonomy` for PL-Tax records on insert/update (identifier build) — the natural home for age defaulting.

### `CareTaxonomy` — pediatric classification source
- Carries `PRM_TaxonomyClassification__c`, `PRM_TaxonomyGrouping__c`, `PRM_TaxonomySection__c`, `TaxonomyCode`, `Name`. **There is no existing "is pediatric" flag** — a reliable pediatric-taxonomy definition must be agreed (see Clarification Q2).

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `HealthcareFacilityNetwork.LowestValidAge` / `HighestValidAge` | **Reuse standard fields** | Adopt for min/max age on the PL-Taxonomy record type. Enable field history tracking if required (Clarification Q3). No custom field creation |
| `PRM_PediatricTaxonomy__mdt` (or reuse a `CareTaxonomy` flag) | New Custom Metadata (proposed) | Config-driven list of pediatric taxonomy codes/classifications that drive the 0–18 default (avoids hardcoding "Pediatrics") |
| `PRM_HCFacilityNetworkTriggerHelper` | Modified Apex | On **before insert** of `PRM_FacilityTx` records, when age fields are blank, default them from the taxonomy (0–18 pediatric, else 0–125). Insert-only, blank-only — never overwrite a supplied value. **Required because standard fields have no declarative default** |
| Validation rule (new, on HFN) | New Validation Rule | `LowestValidAge` in 0–125, `HighestValidAge` in 1–125, and `LowestValidAge < HighestValidAge` (scoped to `PRM_FacilityTx` record type) |
| `PRMDRCreatePracticeLocationTaxonomy`, `PRMTransPDMPPLTaxNw`, `PRMTransAccountCreationPPLTaxNw` | Modified DataRaptor | Add `LowestValidAge` / `HighestValidAge` to the output mapping so UI/roster-supplied values persist |
| `PRM_PDMManualUpdatePracticeLocation_English` (+ `PRM_PDMManualUpdate_English`) | Modified OmniScript | Add Lowest/Highest Valid Age inputs inside the PL-Taxonomy (`AddPLT`) block; prefill from the defaulted values |
| Permission sets | FLS | Grant field access matching existing `PRM_MemberSelectablePCP__c` on HFN |

### Defaulting logic (proposed)
- Fire in the HFN **before-insert** trigger path for the `PRM_FacilityTx` record type only.
- For each new PL-Tax record with `LowestValidAge`/`HighestValidAge` blank: resolve its `PRM_Taxonomy__c` → `CareTaxonomy`; if the taxonomy matches the pediatric config → `Lowest=0, Highest=18`; else `Lowest=0, Highest=125`.
- If a value is supplied (UI/roster/migration), do **not** override it.

### Synchronization note
- Because no sync exists between taxonomy, location, and HCPF age (see Data Synchronization section), this story writes **only** the taxonomy fields. Do **not** assume the location or HCPF age will update. If business needs the taxonomy age to drive the location/HCPF/NPPES output, that propagation is a separate, net-new work item gated by Q7.

---

## Acceptance Criteria

**AC-1 — Adopt standard age fields on Practice Location Taxonomy**  *(Pattern B — reuse, not create)*

- **Field (reuse):** `LowestValidAge` — standard int, label *"Lowest Valid Age"*, on `HealthcareFacilityNetwork`; used for the minimum accepted patient age on `PRM_FacilityTx` records.
- **Field (reuse):** `HighestValidAge` — standard int, label *"Highest Valid Age"*; used for the maximum accepted patient age.
- **Track History:** enable if parity with the location fields is required (Q3).
- **No new custom fields** are created; `PRM_AgeMin__c` / `PRM_AgeMax__c` are NOT added to HFN.

**AC-2 — Age defaults by taxonomy on creation**  *(Pattern D)*

**Given** a new Practice Location Taxonomy (`PRM_FacilityTx`) record is being created (via the PDM flow, the PL-Taxonomy creation IP, or roster sync) with no age values supplied,
**When** the record is saved,
**Then** the age fields are set per the rules below:

- **Lowest Valid Age =** 0 (all taxonomies)
- **Highest Valid Age =**
  - When the taxonomy is a **pediatric physician** taxonomy → **18**
  - Else → **125**
- **And** a taxonomy classified as pediatric never defaults to 125, and a non-pediatric taxonomy never defaults to 18.

**AC-3 — Supplied age values are never overwritten by the default**

**Given** a Practice Location Taxonomy record is created with an explicit age range provided (entered by the PDM Specialist or delivered by a roster feed),
**When** the record is saved,
**Then** the supplied lowest and highest values are persisted unchanged,
**And** the taxonomy-based default does not replace them.

**AC-4 — PDM Specialist can view and edit the age range per taxonomy**

**Given** a PDM Specialist is adding or updating a taxonomy for a practice location in the PDM Manual Update Practice Location flow,
**When** they open the taxonomy row,
**Then** they see a Lowest Valid Age and Highest Valid Age for that taxonomy, prefilled with the defaulted values,
**And** they can change either value before submitting.

**AC-5 — Invalid age range is rejected**  *(edge case)*

**Given** a PDM Specialist enters an age range where the lowest is not less than the highest, or a value outside 0–125,
**When** they submit,
**Then** the save is blocked with a clear "Please enter a valid age" message on the offending field,
**And** no taxonomy record is created or updated until the range is corrected.

**AC-6 — Two member-selectable taxonomies keep independent age ranges**

**Given** a practice location has two member-selectable PCP taxonomies (e.g., a pediatric taxonomy and an adult taxonomy),
**When** both are created,
**Then** the pediatric taxonomy carries 0–18 and the adult taxonomy carries 0–125 independently,
**And** editing one taxonomy's age range does not change the other's.

**AC-7 — Taxonomy age does not silently alter location or practitioner age**  *(guardrail — reflects no-sync finding)*

**Given** the taxonomy-level `LowestValidAge`/`HighestValidAge` are set or edited,
**When** the record is saved,
**Then** the location (`HealthcareFacility`) and practitioner-at-location (`HealthcarePractitionerFacility`) age values are left unchanged,
**And** no implicit roll-up/roll-down occurs unless a propagation rule is explicitly delivered (Q7).

**AC-8 — Field Access & Permission Sets**  *(Pattern C)*

- **PRM_DataModifyAll:** Object level Read/Create/Edit/View All; Field level Read + Edit on `LowestValidAge`, `HighestValidAge`
- **PRM_ProviderDataAdmin, PRM_CredentialingUser, PRM_NetworkManagementQC, PRM_AncillaryCredSpecialist:** Field level Read + Edit (match current `PRM_MemberSelectablePCP__c` access on HFN)
- **PRM_DataViewAll:** Field level Read only

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `HealthcareFacilityNetwork.LowestValidAge` / `HighestValidAge` | Reuse standard fields | Adopt for PL-Tax age; enable history tracking (optional) | Drives AC-1; verified empty in QA |
| `PRM_PediatricTaxonomy__mdt` (proposed) | New CMDT | Seed one row per pediatric taxonomy code/classification | Drives AC-2; avoids hardcoding |
| `PRM_HCFacilityNetworkTriggerHelper` | Modified Apex | Before-insert, blank-only taxonomy-based defaulting for `PRM_FacilityTx` | Drives AC-2, AC-3, AC-7; required (no field default on standard fields) |
| New HFN validation rule | New validation rule | 0–125 bounds + lowest < highest, `PRM_FacilityTx` only | Drives AC-5 |
| `PRMDRCreatePracticeLocationTaxonomy`, `PRMTransPDMPPLTaxNw`, `PRMTransAccountCreationPPLTaxNw` | Modified DR | Add age fields to output mapping | Drives AC-3, AC-4 |
| `PRM_PDMManualUpdatePracticeLocation_English` (+ `PRM_PDMManualUpdate_English`) | Modified OmniScript | Age inputs in `AddPLT` block, prefilled | Drives AC-4 |
| Permission sets | FLS update | Mirror `PRM_MemberSelectablePCP__c` access | Drives AC-8 |

---

## Definition of Done

- [ ] `LowestValidAge` / `HighestValidAge` adopted on the `PRM_FacilityTx` layout; history tracking decision applied.
- [ ] Pediatric-taxonomy definition agreed and configured (CMDT or `CareTaxonomy` flag), not hardcoded.
- [ ] Before-insert defaulting sets 0–18 (pediatric) / 0–125 (other) only when blank; never overwrites supplied values; bulk-safe (200+ records, no SOQL/DML in loops).
- [ ] Validation rule enforces 0–125 and lowest < highest on `PRM_FacilityTx` records.
- [ ] Age fields captured/editable in the PDM PL-Taxonomy flow and persisted by the PL-Tax DataRaptors.
- [ ] Roster/BCBSA sync and PL-Tax creation IP populate/preserve the fields.
- [ ] Taxonomy age writes do not mutate location/HCPF age (no implicit sync); propagation, if any, is a separate deliverable per Q7.
- [ ] FLS granted on the relevant permission sets.
- [ ] Apex test coverage ≥ 85% incl. bulk + pediatric/non-pediatric + supplied-value paths.
- [ ] Backfill decision for existing `PRM_FacilityTx` records agreed (see Clarification Q5).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Is this story dependent on the *Member-Selectable PCP on two taxonomies* change shipping together? | Sequencing; AC-6 assumes two member-selectable taxonomies are allowed | Product / Technical |
| 2 | What is the authoritative definition of a "pediatric physician taxonomy" (taxonomy code list, `PRM_TaxonomyClassification__c` value, or a new flag)? | Correctness of the 0–18 default | Business / Data |
| 3 | Enable field history tracking on `LowestValidAge` / `HighestValidAge` (the location fields are tracked)? | Audit parity | BA / Technical |
| 4 | Should the location-level `HealthcareFacility` age range now be derived from its taxonomies, or continue to be maintained independently? | Scope; possible follow-up rollup | Product |
| 5 | Do existing `PRM_FacilityTx` records (currently null) need a one-time backfill (0–18 pediatric / 0–125 other)? | Data migration effort | Ops / Technical |
| 6 | Should the two age fields flow to the provider directory / vendor extract, and under which columns? | Downstream extract changes | Product / Integration |
| 7 | Given there is **no existing sync** between taxonomy, location, and practitioner-at-location age, is any propagation required — and if so, which level is the source of truth and what are the conflict rules when two member-selectable taxonomies exist at one location? | Net-new sync logic; NPPES/directory correctness (location is today's outbound source of truth) | Product / Integration / Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `HealthcareFacilityNetwork` (`PRM_FacilityTx`) | Fields (reuse) + defaulting | HIGH | Adopting age + defaulting on a high-volume object (8.87M records) |
| `PRM_HCFacilityNetworkTriggerHelper` | Apex | HIGH | Adds before-insert defaulting to an already-heavy trigger |
| Age synchronization (taxonomy ↔ location ↔ HCPF) | Design gap | HIGH | No sync exists today; a third age holder is introduced. Reconciliation is net-new and unspecified (Q7) |
| PL-Tax DataRaptors / IP | OmniStudio | MEDIUM | Output mapping additions on multiple create paths |
| `PRM_PDMManualUpdatePracticeLocation_English` | OmniScript | MEDIUM | New inputs in the PL-Taxonomy block |
| Roster / BCBSA sync | Apex | MEDIUM | Must preserve/populate new fields |
| Directory / vendor extract | Integration | LOW–MEDIUM | Only if Q6/Q7 requires publishing age per taxonomy |

---

## Estimated Effort  *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Adopt standard age fields (layout, history) | Config | S | No field creation — reuse `LowestValidAge`/`HighestValidAge` |
| Pediatric taxonomy config (CMDT/flag) | Custom Metadata / field | S–M | Depends on Q2 |
| Trigger defaulting + tests | Apex | L | Bulk-safe, insert-only, blank-only; carries the default (no field-level default) |
| HFN validation rule | Validation rule | S | 0–125 + lowest < highest |
| PL-Tax DataRaptor mapping updates | DataRaptor | M | 2–3 DRs |
| OmniScript age inputs | OmniScript | M | PL-Taxonomy block |
| Permission set FLS | Config | S | Mirror member-selectable access |
| Existing-record backfill | Data / batch | M–L | Depends on Q5 |
| Age propagation/sync (if required) | Apex / batch | M–L | Only if Q7 mandates taxonomy→location/HCPF propagation; net-new |

**Total Estimated Effort:** ~**L** overall (reuse of standard fields removes field-creation work; larger if backfill, directory extract, or Q7 propagation are in scope).

---

## Revision History

| Version | Date | Summary |
|---------|------|---------|
| ce5ade38c184 | 2026-07-06 | Authored via User Story Architect (PNM); added Data Synchronization section documenting no existing age sync across taxonomy/location/practitioner-at-location, plus Q7 propagation clarification and impact row. |
