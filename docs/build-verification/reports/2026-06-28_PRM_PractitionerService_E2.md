# Verification Report — `PRM_PractitionerService` (E2)

> **Pilot run** of the build-verification agent layer ([`docs/build-verification/`](../README.md)) against
> an existing delivery. Rendered from the Verification State; verdict is deterministic.

| | |
|---|---|
| **Artifact** | `force-app/main/default/classes/PRM_PractitionerService.cls` (+ `PRM_PractitionerServiceTest.cls`) |
| **Resolved step** | E2 `PRM_PractitionerService` · PractitionerBatch (seq 1) · both branches (IBC + Delegated) — Parity Ledger §3 row 1 / §4 |
| **Agents run** | Parity · Branch-Coverage · Governor & Bulk-Safety · Service-Boundary · Test-Adequacy · Clarification-Log Gate · Critic |
| **Verdict** | **BLOCKED** |
| **Risk score** | **80 / 100** |
| **Review tier** | **owner-block** |
| **Run date / org** | 2026-06-28 · tests on `ibx-dev` |

> **One-line read:** the code is well-built — clean object parity, bulk-safe, 94% coverage — but it
> **cannot be certified yet**: field-level parity is gated by the open **CL-11** field-map sign-off, plus
> two code NEEDS-FIX (in-service context SOQL vs the service-boundary rule; missing `WITH USER_MODE`). The
> BLOCK is a **process gate**, not a rewrite.

---

## Findings (by agent)

| Agent | Item | Expected (citation) | Actual | Status |
|-------|------|---------------------|--------|--------|
| **Parity** | Object set | `HealthcareProvider`, `HealthcareProviderNpi`, `Identifier`, `HealthcareProviderTaxonomy` (E4 fused into E2) — Ledger §3 row 1 | All four created; no extras (`cls:295,327,371,382`) | ✅ PASS (object-level) |
| **Parity** | Name normalization | `PRM_FormSubUtility.NameNormalize` (legacy `RA_TitleCase`) — Ledger §3 row 1 | `healthcareProviderName()` uses `NameNormalize` (`cls:419-427`) | ✅ PASS |
| **Parity** | Record type resolution | RTs via cached describe, not SOQL on `RecordType` | `PRM_FormSubUtility.recordTypeId(Identifier…)` (`cls:45-48`) | ✅ PASS |
| **Parity** | No phantom objects (CL-2/CL-3) | No `PractitionerPracticeLocation`, no `HealthcarePractitionerFacilityNetwork` | None present | ✅ PASS |
| **Parity** | **Field-level parity** | Per-service DR→object field map **signed off** before tests — CL-11 (hard gate, `CLAUDE.md:153`) | E2 field map not signed off (CL-11 open) | ⛔ **BLOCKED** |
| **Branch-Coverage** | Branch-agnostic service | Branching is the batch's job; service runs on both branches | No `PractitionerCreationType` branching in service | ✅ PASS |
| **Branch-Coverage** | Existing-NPI delta path | `isExistingNPI=true` → deltas only (Ledger §2) | `existingHcpNpiId` reuses NPI, builds none (`cls:188-192`); marked "deferred for pilot" | ◐ PASS (delta scope partial — see Critic) |
| **Governor** | Bulk-first, no DML/SOQL in loops | one bulk DML per object type; SOQL outside loops (CLAUDE §6) | 4 bulk DML + 4 SOQL, all outside loops; 200-row test green | ✅ PASS |
| **Governor** | FLS / `WITH USER_MODE` | All SOQL/DML user-mode enforced (CLAUDE §6) | Queries (`cls:111,153,311,356`) + DML lack `WITH USER_MODE` / `as user` — **Code Analyzer confirms 10× High `ApexCRUDViolation`** at `cls:112,153,295,311,327,356,371,382` | ❌ NEEDS-FIX |
| **Governor** | Method complexity | Within PMD thresholds (cyclo ≤ class 50 / cognitive ≤ 15) | `writeHealthcareProviderNpis` cognitive **15** + cyclomatic **12**; class cognitive **78** / cyclomatic **77** (Code Analyzer, Moderate) | ◐ advisory |
| **Service-Boundary** | No self-context SOQL / cross-object correlation | Batch injects all context (`prm-service-class-boundaries.mdc`) | `resolveForeignKeys` SOQLs `Account` for `PersonContactId` **and falls back to `PRM_CaseManager__c`** (`cls:111-125`); `resolveTaxonomyIds` SOQLs `CareTaxonomy` (`cls:153-158`) | ❌ NEEDS-FIX |
| **Test-Adequacy** | ≥85% coverage | ≥85% (deploy gate 75%) | **94%** (7/7 pass, live on `ibx-dev`) | ✅ PASS |
| **Test-Adequacy** | Path coverage | bulk(200)/single/empty/negative | All present + idempotent re-run + distinct-NPI | ✅ PASS |
| **Test-Adequacy** | Standards | reuse `PRM_TestDataFactory`; cover existing-NPI path | Inline inserts (not factory); no `existingHcpNpiId` test (uncovered `cls:121,135,173…`) | ◐ advisory |
| **CL Gate** | No `*__c` "inferred" | concrete API names only | Real fields throughout | ✅ PASS |
| **CL Gate** | Reuse over rebuild (CL-8/CL-9) | reuse utilities/constants | Reuses `PRM_FormSubUtility`, `PRM_Constants` | ✅ PASS |
| **CL Gate** | CL-11 field-map sign-off | hard gate before tests | **Open** — not signed off | ⛔ **BLOCKED** |

---

## Critic — cross-agent contradictions

| Between | Description | Resolved? |
|---------|-------------|-----------|
| Service-Boundary ↔ delivery intent | Service header says *"E2 resolves only PersonContactId + taxonomy refs it owns"*, but `prm-service-class-boundaries` forbids self-context SOQL **and** CaseManager→Account correlation (`cls:123-124`). Design-vs-rule conflict needing an **architect decision** (ratify a carve-out, or move resolution to PractitionerBatch). | ❌ unresolved |
| Service-Boundary ↔ Governor | The same in-service `Account`/`CareTaxonomy` SOQL drives both the boundary finding **and** the missing-`USER_MODE` finding — fixing the boundary (inject from batch) relocates/removes the FLS finding. Fix them together. | ❌ coupled |
| Parity ↔ Test-Adequacy | Parity allows an existing-NPI **delta-only** path, but no test exercises `existingHcpNpiId`; the delta behavior is asserted by neither parity evidence nor a test. | ◐ low-confidence |

**Risk score 80/100** = field-map BLOCKED (40) + 2× NEEDS-FIX (30) + low-confidence delta gap (10).
Tier **owner-block** (dominated by the CL-11 gate).

---

## Evidence

| Tool | Command | Output |
|------|---------|--------|
| Apex tests | `sf apex run test --target-org ibx-dev --tests PRM_PractitionerServiceTest --code-coverage` | 7/7 pass; **`PRM_PractitionerService` 94%** |
| Static SObject/DML scan | manual | 4 bulk DML (HCP upsert, NPI insert, Identifier insert, Taxonomy upsert); 4 SOQL (Account, CareTaxonomy, NPI dedupe, Identifier dedupe); none in loops |
| Code Analyzer | `sf code-analyzer run --workspace PRM_PractitionerService.cls --workspace PRM_PractitionerServiceTest.cls` (JDK 17 via Homebrew `openjdk@17`) | **30 violations: 10 High, 4 Moderate, 16 Low.** High = all `ApexCRUDViolation` (FLS/user-mode). Moderate = cyclomatic/cognitive complexity. Low = test-class style (`@isTest` casing, `System.runAs`). Full JSON: [`…_E2_codeanalyzer.json`](./2026-06-28_PRM_PractitionerService_E2_codeanalyzer.json) |
| Git | `git fetch` + `git log HEAD..origin/main` | up to date with `origin/main` (latest: `2d0f853 [E20] PRM_PractitionerBatch`) |

---

## Required actions

**BLOCKED (must clear before certification)**
1. **CL-11 — sign off the E2 DR→object field map.** Object parity is verified; field parity stays
   `BLOCKED` until the per-service map is signed off (hard gate, `CLAUDE.md:153`). Owner: Epic-E lead.

**NEEDS-FIX (code)**
2. **Service-boundary** (`PRM_PractitionerService.cls:106-161`) — the service resolves its own context
   (`Account.PersonContactId`, `Account.PRM_CaseManager__c` fallback, `CareTaxonomy` ids) via SOQL. Either
   move this resolution into `PRM_PractitionerBatch` and inject via `params`, **or** have an architect
   ratify an explicit carve-out and amend `prm-service-class-boundaries.mdc`. (Resolves the coupled
   Governor finding too.)
3. **FLS / user-mode** (`cls:111,153,311,356` + DML) — add `WITH USER_MODE` (or `Security.stripInaccessible`)
   per CLAUDE §6.

**Advisory (not blocking)**
4. Add a test for the `existingHcpNpiId` delta path; prefer `PRM_TestDataFactory` over inline inserts.
5. ✅ **Done** — deterministic backbone completed: `sf code-analyzer run` now runs (JDK 17 installed). Reduce
   class/method complexity (`writeHealthcareProviderNpis`, see Code Analyzer Moderate) and clean up test-class
   style nits (`@IsTest`/`@TestSetup` casing, `System.runAs`).

> **Full developer fix guide:** [`2026-06-28_PRM_PractitionerService_E2_DEV_FIX_SUMMARY.md`](./2026-06-28_PRM_PractitionerService_E2_DEV_FIX_SUMMARY.md)
> — every finding with exact line, why it matters, and a concrete fix pattern.

---

## Sign-off

| Reviewer | Date | Decision |
|----------|------|----------|
| _(pending architect — owner-block tier)_ | | |
