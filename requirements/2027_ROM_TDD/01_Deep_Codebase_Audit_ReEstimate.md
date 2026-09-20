# 2027 Priorities — Deep Codebase Audit & Re-Estimation

**Date:** August 25, 2026
**Supersedes the sizing in:** `00_ROM_TDD_Summary.md` (July 29, 2026)
**Method:** every number below is **measured** from `force-app/main/default/` in this repo. Where a figure could not be measured, it is labelled *unverified* rather than estimated.

> **Headline:** the portfolio is materially larger than the current ROM assumes. Re-grounded, the twelve priorities total **~2,130–3,020 baseline dev-days (~9.3–13.1 developer-years)**, against a stated team of 5–7 engineers (~1,150–1,610 dev-days/year). **The portfolio is ~1.8–2.1× the stated 2027 capacity.** Three items moved: F2 and F4 grew, F11 moved up a size band.

---

## 1. Measured inventory (the baseline everything else rests on)

| Layer | Measured | Note |
|---|---:|---|
| Apex classes | **714** | 439 non-test + 275 test |
| — performing DML | 236 | the Apex write path |
| — performing SOQL | 260 | |
| — `Database.Batchable` | **71** | substantial existing async precedent |
| — `Queueable` | 6 | |
| — `Schedulable` | 20 | |
| — `Callable` | 52 | the OmniStudio→Apex remote-action boundary |
| Triggers | 32 | |
| LWC bundles | **192** | 144 `isExposed`; **only 15 community-targeted** |
| Aura components | 3 | |
| OmniScripts | **100 distinct** | 759 version files — avg **7.6 versions each** |
| Integration Procedures | **437 distinct** | 1,542 version files — avg 3.5 each |
| DataMappers | **1,432** | 508 Extract · **478 Load** · 337 Transform · 109 Turbo Extract |
| FlexCards | 10 distinct | 39 version files |
| Objects | 914 | 254 custom `__c` (incl. managed packages) |
| Field definitions | ~11,000 | 3,744 on custom objects |
| **Objects written by Load DRs** | **42** | the true provider-data write surface |
| Field History enabled | 128 objects | |
| Fields with `trackHistory` | **596** across 53 objects | partial versioning foundation |
| Queues | 14 | |
| **Assignment rules** | **0** | all routing is code-driven today |
| Reports / dashboards / report types | **5 / 1 / 45** | reporting is effectively greenfield |
| Named credentials | 5 | NPPES, CAQH, Precisely, SDS, SendGrid |
| Flows / permission sets | 22 / 41 | |

**Limitation:** git history in this repo is a **101-commit, single-month snapshot**, so it yields no delivery-velocity signal. Estimates are structure-based, not velocity-calibrated. Calibrating against the team's real sprint history would be the single highest-value refinement.

---

## 2. What the current ROM got wrong

| # | ROM claim | Measured reality | Direction |
|---|---|---|---|
| F4 | "~501 Apex classes / 1,338 DataRaptors / ~30 objects" | **439 non-test Apex (236 doing DML)**, **1,432 DataMappers of which 478 are write-path Load**, and **42 objects** written by Load DRs | **Scope up** |
| F2 | "5 flows, **~55 tiles**" | credentialing family = **45 active OmniScripts / 304 steps / 205 IP actions / 106 LWC refs**; the **core 5 flows alone ≈ 108 steps** | **Scope up ~2×** |
| F11 | "update and expose existing internal flow", 8–13 pts/form | portal **exists** (`ProviderIE`), but **only 15 of 192 LWCs are community-targeted**; the 4 forms carry **~17 custom LWCs** at extreme churn (v117 / v87 / v53 / v44) | **Scope up** |
| F7 | "engine designed-not-built" | **Confirmed** — no `PRM_AsyncJob__c`. But `PRM_ServiceBase` + `PRM_FormSubUtility` **are built**, `PRM_Constants` already carries the async constants, and **71 Batchable classes** exist as precedent | Small head start |
| F2 | "CAQH document API entitlement unverified" | **44 CAQH Apex classes + `PRM_CAQH_API` named credential already exist** — connectivity is *not* the risk; the **document** entitlement still is | Risk narrowed |
| F8 | LexisNexis treated as fully net-new | **`PRM_EnableLexisNexis__c` toggle already wired into 10 IPs / 55 references** in the address + PAR pipeline (alongside Precisely) — but **no LexisNexis named credential**, so the API call itself is still net-new (likely via Mulesoft) | Partially offset |
| F3 | "smart + configurable routing" | **14 queues but 0 assignment rules** — routing is entirely code-driven, so declarative routing is genuinely net-new | Slight up |
| F6 | "OOTB reports + dashboards" | **5 reports / 1 dashboard** exist; 45 report types help | Slight up |
| F4 | (no credit taken) | **596 fields already history-tracked across 53 objects** — a real point-in-time head start (FHT ≠ effective-dated versioning, but it is not zero) | Partial offset |

**Flag:** `IndividualApplication` shows **61 `trackHistory` fields**, above the standard 20-field-per-object limit. Confirm whether an increased limit is in effect before F4 assumes FHT headroom.

---

## 3. F4 tiering — the most actionable finding

The 478 Load DataMappers concentrate heavily. **14 objects carry 723 of ~890 Load-DR object references (~80% of the write path):**

| Object | Load DRs | | Object | Load DRs |
|---|---:|---|---|---:|
| HealthcarePractitionerFacility | 79 | | Address | 55 |
| IndividualApplication | 78 | | PRM_InfoCodeAssignment__c | 47 |
| HealthcareFacilityNetwork | 72 | | Identifier | 45 |
| Account | 67 | | HealthcareProviderNpi | 41 |
| HealthcareFacility | 63 | | Location | 40 |
| Case | 60 | | HealthcareProviderTaxonomy | 30 |
| | | | HealthcareProvider | 24 |
| | | | PRM_CaseDataManager__c | 22 |

**Recommendation:** define **F4 Tier 1 = these 14 objects**. It buys ~80% of versioning value for roughly half the cost, and makes F4 fundable as a phase instead of an open-ended program.

---

## 4. Re-run estimates

Baseline developer-days. Sizes use the ROM key (L 35–75 · XL 75–150 · XXL 150–300+).

| # | Feature | Old base | **New base** | Old size | **New size** | Primary driver of the change |
|---|---|---:|---:|:--:|:--:|---|
| 1 | PDM + PEAR self-service | 84–107 | **100–130** | XL | XL | community LWC enablement + FLS |
| 2 | Credentialing (tiles/CAQH/Agentic) | 322–421 | **430–560** | XXL | **XXL ⚠** | 108 core steps vs 55 assumed tiles |
| 3 | Enhanced Case Management | 68–100 | **80–115** | L–XL | L–XL | 0 assignment rules — routing all net-new |
| 4 | Full Data Versioning | 475–490 | **560–700** | XXL | **XXL ⚠** | 42 objects / 478 Load DRs (vs ~30) |
| 5 | Cred + PDM Integration | 50–75 | **55–80** | L | L | RCAT reuse confirmed |
| 6 | Inventory & Reporting | 61–110 | **70–120** | L–XL | L–XL | reporting near-greenfield |
| 7 | Mass Data Loads | 187–263 | **185–270** | XXL | XXL | head start offsets extra ops |
| 8 | LexisNexis + Compliance | 117–185 | **115–185** | XL | XL | existing toggle offsets net-new API |
| 9 | Stabilization & Tech Debt | 230–400 | **260–430** | L–XL | L–XL | envelope scales with 12 priorities |
| 10 | Re-Cred PSV → PDM routing | 95–150 | **95–150** | XL | XL | unchanged — evidence consistent |
| 11 | FHNatic external forms | 48–78 | **90–140** | L–XL | **XL** | ~17 LWCs need community enablement |
| 12 | POMS multi-request | 80–120 | **90–140** | XL | XL | PDM Manual Update family ≈ 99 steps |
| | **Total** | 1,817–2,449 | **2,130–3,020** | | | |

**⚠** F2 and F4 each exceed **2× the floor of the XXL band**. They are not single priorities — they are multi-year programs and should be funded as phases.

---

## 5. Capacity reality check

- Portfolio: **2,130–3,020 dev-days** = **9.3–13.1 developer-years** at ~230 productive days/year.
- Stated team: **5–7 senior engineers** = **1,150–1,610 dev-days** in 2027.
- **The portfolio is ~1.8–2.1× what the stated team can deliver.**

Three ways out: **staff to ~9–13 engineers**, **phase the portfolio**, or **cut scope**. A phased slice that genuinely fits 5–7 engineers:

| Slice | Dev-days |
|---|---:|
| F7 async engine + first 4 mass operations | 130–190 |
| **F4 Tier 1** (14 objects ≈ 80% of write path) | 300–380 |
| F3 Case Management (routing + duplicate-QC defect) | 80–115 |
| F1 PDM + PEAR self-service | 100–130 |
| F10 Re-Cred PSV → PDM routing | 95–150 |
| **F2 Phase 1** (tile framework + 2 of 5 flows) | 180–240 |
| F9 reserved stabilization envelope (~15–20%) | 130–220 |
| **Total** | **1,015–1,425** |

Deferred to 2028: **F5, F6, F8, F11, F12**, plus **F2 Phases 2–3** and **F4 Tiers 2–3**.

---

## 6. Risks revised on evidence

1. **F4 blast radius (High)** — 478 write-path Load DRs + 236 DML Apex classes across 42 objects. Mitigate by tiering (§3) and building the regression harness before the first object.
2. **F2 is two programs (High)** — 304 steps / 45 OmniScripts in the credentialing family. "5 flows" needs a named step list before funding.
3. **Community LWC gap (Medium, new)** — only 15 of 192 LWCs are community-ready. Blocks F1 and F11; discover the exact per-form LWC list early.
4. **OmniStudio churn (Medium, new)** — avg 7.6 versions per OmniScript, peaking at **v117** (`PRM_PractitionerParticipationForm`), v87 (`PRM_ProviderChangeForm`), v63, v53. High churn on exactly the assets F11 wants to expose externally. Supports the F9 envelope.
5. **No velocity calibration (Medium)** — repo git history is a one-month snapshot. Re-baseline against real sprint throughput before committing dates.
6. **CAQH document entitlement (Medium)** — narrowed, not closed: connectivity exists, document access is unproven.
7. **F10 remains gated** — paused in production pending the async location processor and the P0 defects (Bug 1216121 / 1216120).

---

## 7. Open questions

| # | Question |
|---|---|
| F2 | Name the exact step/tile list for the "5 flows" — 55 or 108? |
| F4 | Approve Tier 1 = the 14 objects in §3; confirm the `IndividualApplication` 61-tracked-field limit. |
| F6 | Integrity-feed count still unknown — run the discovery inventory. |
| F7 | Confirm the exact mass-operation list (7+ vs the 10 in the Oct 2025 estimate). |
| F8 | What does `PRM_EnableLexisNexis__c` toggle today, and does the LexisNexis call route through Mulesoft? |
| F11 | Which of the ~17 form LWCs are already community-safe? |
| All | Provide real sprint velocity so these structure-based numbers can be calibrated. |
