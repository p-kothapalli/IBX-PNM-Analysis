# Feature 9 — System Stabilization & Technical Debt: High-Level TDD & Estimation

**Date:** July 29, 2026
**Priority:** 2027 #9 — *System Stabilization & Technical Debt Reduction*
**Scope (proposed — business was unsure):**
- **Itemized burn-down** of the documented defect/analysis backlog (the grounded floor) **+** a recommended **reserved ~15–20% capacity envelope** (continuous, across the whole team) to absorb newly-discovered defects and small hardening.
- **Estimate unit:** developer-days (baseline + AI-assisted), story-point range secondary.

> Estimation method per the shared note in `Feature1_PDM_PEAR_TDD_Estimation.md` §method. Tech debt is inherently a *capacity* model, not a fixed feature — the itemized backlog below is the **known floor**; the envelope covers the unknown.

---

## 1. Current State (audited, grounded)

`requirements/` contains **~40 root-cause / bug-fix / analysis documents** — a real, catalogued backlog. Representative open/structural items:

| Theme | Grounding docs | Nature |
|---|---|---|
| Duplicate QC cases (71 IAs) | `Duplicate_QC_Cases_RootCause_Analysis.md` | Idempotency defect (also in F3) |
| PDM address overlap false-positive | `PDM Flows/PDM_Address_Error_Analysis.md`, `US_PDM_WebsiteEmail_OverlappingAddressError.md` | Trigger logic |
| Stale external-id duplicate block | `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md` | Data/logic |
| PEAR read-only website bug | `PEAR/PEAR_WebsiteReadOnly_BugFix.md` | OmniScript config |
| PAR partial-data rollback | `PAR_Form_PartialDataRollback_Investigation_FixPlan.md`, `PRM_Batch_Rollback_Strategies.md` | Transactional integrity |
| Terminated-location in-flight | `PAR_AppReview_TerminatedLocation_InFlight_BugFix.md`, daily-script analysis | Flow logic + scripts |
| Sync governor/perf | `PractitionerCreationPerformance/*`, `PRM_FetchPDMSelectedFacilityDetailsParent_Performance_Analysis.md` | Performance (also F7) |
| FDP refactor pre-condition | `Provider_Data_Versioning_Estimation.md` | Structural (also F4) |
| Misc data/field bugs | Ancillary/PersonEducation/HCPF/InfoCode analyses | Various |

Note: several documented items may already be fixed/shipped; treat the list as an **upper-bound inventory** to triage.

---

## 2. High-Level Approach (TDD-lite)

- **Triage + register:** convert the ~40 documents into a triaged register (open / fixed / won't-fix), severity-ranked.
- **Fix in buckets** by type: config/metadata, Apex/IP/DR logic, structural/performance.
- **Guardrails:** each fix gets a regression test (prevent recurrence); recurring classes (idempotency, address overlap, external-id) get a **root-cause fix**, not a patch.
- **Continuous envelope:** reserve team capacity for incoming defects + small hardening rather than a one-time push.

### 2.1 Cross-feature note
Some items are **also** in other features (duplicate QC → F3; perf/governor → F7; FDP refactor → F4). To avoid double-counting, those are **booked in their feature**; Feature 9 covers the **remainder + unknowns**.

---

## 3. Estimation (developer-days)

### 3.1 Itemized backlog burn-down (known floor; excludes items booked in F3/F4/F7)

| Bucket | Count (est.) | Per item (baseline) | Baseline | AI-assisted |
|---|---:|---:|---:|---:|
| Triage + register the ~40 docs | — | — | 4–6 | 4–5 |
| Small (config/metadata/validation) | ~12–15 | 1–2 | 15–30 | 10–18 |
| Medium (Apex/IP/DR logic) | ~8–10 | 3–6 | 30–55 | 18–35 |
| Large/structural (rollback strategy, root-cause classes, non-F7 perf) | ~3–5 | 8–14 | 35–65 | 22–42 |
| Regression tests + hardening | — | — | 10–15 | 5–8 |
| **Backlog floor sub-total** | | | **94–171** | **59–108** |

### 3.2 Reserved capacity envelope (recommended operating model)

- Reserve **~15–20% of annual delivery capacity**, continuous, across the team, for incoming defects + small hardening.
- Illustrative: if the 2027 build program (Features 1–8) is on the order of **~1,150–1,600 AI-assisted dev-days**, 15–20% ≈ **~170–320 AI-assisted dev-days/year**.
- The **backlog floor (§3.1) is funded from within this envelope** — it is not additive; the envelope simply guarantees the capacity exists and covers the unknown.

### 3.3 Feature 9 total (recommended booking)

| View | Baseline dev-days | AI-assisted dev-days |
|---|---:|---:|
| **Known backlog floor** (grounded) | **94–171** | **59–108** |
| **Recommended reserved envelope** (operating model) | ~230–400 | **~170–320** |

- **Recommendation:** book the **reserved envelope** as the planning number (**~170–320 AI-assisted dev-days/yr**), with the known backlog floor (**~59–108**) as the committed starter set inside it.
- **Story-point secondary:** envelope ≈ **170–320 pts/yr**; backlog floor ≈ **90–170 pts**.
- **T-shirt: L–XL** (as an envelope).
- **Confidence: Medium** on the floor; the envelope is a policy choice.
- **Cadence:** continuous (every sprint carries a stabilization slice), not a single milestone.

---

## 4. Assumptions, Dependencies, Open Questions

**Assumptions**
- Continuous reserved % across the team (not a dedicated squad, not fully absorbed) — proposed default.
- Items overlapping F3/F4/F7 are booked there, not double-counted here.
- ~40 docs are an upper-bound inventory needing triage (some already fixed).

**Dependencies**
- Root-cause fixes (idempotency, address overlap, external-id) should land before/with the features that reuse those write paths.

**Open questions (for grooming)**
- Confirm the reserved **%** (15–20% proposed) and whether it's a reserved slice vs a dedicated squad.
- Run the triage pass to confirm how many of the ~40 documented items are still open.
- Decide the double-count boundary with F3/F4/F7 explicitly.

---

*Grounding references:* the ~40 analysis/bug-fix docs under `requirements/` (see §1 table); `PRM_Batch_Rollback_Strategies.md`; `PractitionerCreationPerformance/*`.
