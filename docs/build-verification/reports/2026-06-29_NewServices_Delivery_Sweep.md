# Verification Report — New Epic-E Delivery Sweep (origin/main `52eb50c`)

> Agent run over the **22 commits** pulled into `origin/main` since the last local HEAD (`6bf4a8f`). Run
> **read-only** from a detached `git worktree` at `origin/main` — the user's uncommitted working tree was not
> touched. Rendered from the Verification State; each verdict is deterministic.

| | |
|---|---|
| **Scope** | 5 new services (E16, E7, E10, E6, E11) + 2 modified (E2 `PRM_PractitionerService`, `PRM_PractitionerBatch`) |
| **Source** | `origin/main` @ `52eb50c` "Merge epic-e/cdm-service into main (E16 Case Data Manager)" |
| **Agents run** | Parity · Branch-Coverage · Governor & Bulk-Safety · Service-Boundary · Test-Adequacy · CL Gate · Critic |
| **Backbone** | `sf code-analyzer run` (JDK 17) + `sf apex run test` on `ibx-dev` — **41/41 pass, 100%** |
| **Overall** | **BLOCKED** (all services gated by the open **CL-11** field-map sign-off) + a **systemic FLS NEEDS-FIX** across every service except E16 |

> **One-line read:** this is a strong, consistent delivery — every service is gated/bulk-first/idempotent,
> all tests pass ≥93%, and **E16 (CDM) is exemplary** (does FLS the right way and coalesces to one write).
> But two things repeat across the batch: (1) the **same FLS/user-mode gap** the E2 pilot found, now in E6/E7/E10/E11
> too, and (2) field-level parity is **BLOCKED** on the open **CL-11** sign-off. The blocks are a process gate
> + one systemic code fix, not rewrites.

---

## Per-service verdict

| Service (story) | Object (Ledger row) | Coverage | Code Analyzer (High) | Verdict | Risk / tier |
|-----------------|---------------------|----------|----------------------|---------|-------------|
| **E16 `PRM_CaseDataManagerService`** | `PRM_CaseDataManager__c` (§3 row 19) | 96% | 2 — **near-false-positive** (PMD can't trace `stripInaccessible`) + eager-describe | **BLOCKED** (CL-11 only) | 40 · owner-block |
| **E6 `PRM_EducationService`** | `PersonEducation` (§3 row 5) | 95% | 5 — real FLS | **BLOCKED** + NEEDS-FIX | 70 · owner-block |
| **E7 `PRM_BoardCertificationService`** | `BoardCertification` (§3 row 6) | 98% | 3 — real FLS | **BLOCKED** + NEEDS-FIX | 70 · owner-block |
| **E10 `PRM_ContactService`** | `ContactProfile` (§3 row 9) | 97% | 3 — real FLS | **BLOCKED** + NEEDS-FIX | 70 · owner-block |
| **E11 `PRM_LanguageService`** | `PersonLanguage` (§3 row 10) | 99% | 2 — real FLS | **BLOCKED** + NEEDS-FIX | 55 · owner-block |
| **E2 `PRM_PractitionerService`** (modified) | HCP/NPI/Identifier/Taxonomy (§3 row 1) | 94% | 10 — real FLS | **BLOCKED** + NEEDS-FIX | 80 · owner-block |
| **`PRM_PractitionerBatch`** (modified) | orchestration (E16/E19 wired) | 93% | 0 High (9 Mod complexity) | ◐ advisory | 10 · auto |

CL-15 does **not** block any of these — all six services run inside `PractitionerBatch` (assigned); only
`GroupRelatedBatch` remains unmapped, and nothing here targets it.

---

## Backbone evidence

| Tool | Command | Result |
|------|---------|--------|
| Apex tests | `sf apex run test --target-org ibx-dev --tests <7 classes> --code-coverage` | **41/41 pass, 100%.** Coverage: CDM 96 · BoardCert 98 · Education 95 · Contact 97 · Language 99 · PractitionerService 94 · PractitionerBatch 93 |
| Code Analyzer | `sf code-analyzer run` (JDK 17, worktree) over the 7 classes | **70 violations: 25 High, 21 Moderate, 20 Low, 4 Info.** High = `ApexCRUDViolation` everywhere **except** it's a near-false-positive on E16. Full JSON: [`2026-06-29_NewServices_codeanalyzer.json`](./2026-06-29_NewServices_codeanalyzer.json) |
| Git | `git worktree add --detach origin/main` | Verified `52eb50c`; working tree untouched |

---

## Findings by agent (cross-service)

### Parity Auditor — ✅ object-level PASS, ⛔ field-level BLOCKED (CL-11)
Every new service writes exactly the object its Ledger row requires, and **the well-known traps are handled
correctly**:
- **E10 writes `ContactProfile`, not `Contact`** — trap #4 ✅.
- **E16 coalesces to one INSERT + one UPDATE** per Case Manager (merging all practitioners' tokens), asserting
  final field state — trap #3 ✅ (legacy wrote CDM 3–4×; this is the intended single coalesced write).
- No phantom objects (no `PractitionerPracticeLocation`, no `HealthcarePractitionerFacilityNetwork`).
- Idempotent re-run anchors: NPI-keyed `PRM_RecordKey__c` upsert (E2/E6/E7/E10/E11) and one-CDM-per-CM (E16).

Field-level parity is **BLOCKED** for all — CL-11 (per-service DR→object field-map sign-off) is still open
(`CLAUDE.md:153`). The maps are *documented* in `Epic_E_Practitioner_Services.md` §E6/E7/E10/E11/E16, so this
is a sign-off formality, not missing work.

### Branch-Coverage — ✅ PASS
All four new specialist services are correctly **gated** and Delegated-appropriate: E6 on `education[]`, E7 on
`boardCertifications[]`, E10 on `providerInformation`, E11 on `languages[]`. Empty/absent → no records. Matches
Ledger §2 (Delegated-only, gated).

### Governor & Bulk-Safety — ❌ systemic NEEDS-FIX (FLS), else ✅
- **Bulk-first ✅** everywhere: one bulk SOQL + one bulk DML per object type; no SOQL/DML in loops (E16 has a
  for-loop only over in-memory maps).
- **FLS / user-mode ❌ (real, systemic):** E2, E6, E7, E10, E11 issue raw SOQL + `upsert`/`insert` with **no**
  `WITH USER_MODE` / `stripInaccessible`. 23 of the 25 High violations. **E16 is the exception — it does it
  right** (`WITH SECURITY_ENFORCED` + `Security.stripInaccessible(CREATABLE/UPDATABLE)` + an explicit
  identity-field FLS guard). The fix pattern already exists in the codebase — it's E16.

### Service-Boundary — ❌ systemic NEEDS-FIX (one architect decision)
E2, E6, E7, E10 each run a self-context `Account` SOQL in `resolvePractitionerContacts()` to resolve
`PersonContactId` (E6/E7: `cls` ~`182`/`116`; E10: `107`; E2: `112`). This is the **same** boundary question
raised in the E2 pilot, now confirmed **systemic**. **E11 shows the clean alternative** — it needs no Account
query (`IndividualId = accountId`). E6 additionally SOQLs `PRM_Degree__c` / `PRM_Institution__c` master data
(reference resolution — lower concern). This needs **one** ruling, not five fixes (see Critic).

### Test-Adequacy — ✅ PASS
All 7 classes ≥93% on `ibx-dev`; 41/41 green. (Advisory carried from pilot: prefer `PRM_TestDataFactory` and
add `System.runAs` — the Low CA findings — so FLS fixes are actually exercised under a real user.)

### CL Gate — ⛔ BLOCKED (CL-11), else ✅
CL-11 field-map sign-off open → field parity blocked for every service. CL-15 OK (all in `PractitionerBatch`).
Real object/field API names throughout; reuses `PRM_Constants` / `PRM_FormSubUtility` / `PRM_ServiceBase`.

---

## Critic — cross-agent contradictions & systemic signals

| Between | Description | Resolved? |
|---------|-------------|-----------|
| Governor ↔ delivery (all but E16) | FLS gap is **systemic** and E16 already demonstrates the sanctioned fix (`stripInaccessible` + `SECURITY_ENFORCED`). Apply E16's pattern to E2/E6/E7/E10/E11. | ❌ unresolved (1 pattern, 5 sites) |
| Service-Boundary ↔ rule (E2/E6/E7/E10) | Services resolve their own `PersonContactId` via `Account` SOQL; the boundary rule says the batch injects context. **E11 proves it's avoidable.** Needs **one** architect decision: ratify a carve-out for PersonContactId resolution **or** move it into `PRM_PractitionerBatch`. | ❌ unresolved (systemic) |
| Code Analyzer ↔ E16 reality | E16's 2 High `ApexCRUDViolation` are **PMD failing to trace `Security.stripInaccessible`** — the code *is* FLS-safe. Treat as near-false-positive; suppress with justification, don't "fix". | ✅ explained |
| Parity ↔ CL-11 (all) | Object parity proven; field parity unprovable until the per-service map is signed off. Process gate, not a defect. | ◐ process |

**Systemic risk = 75/100.** Dominated by the open CL-11 gate (process) + one repeated, low-effort FLS pattern
fix. No architectural defects found; nothing needs a rewrite.

---

## Required actions

**BLOCKED (process — clears the whole sweep)**
1. **CL-11 — sign off the per-service field maps** for E2, E6, E7, E10, E11, E16. Maps are already documented
   in `Epic_E_Practitioner_Services.md`; this is a sign-off, owned by the Epic-E lead (`CLAUDE.md:153`).

**NEEDS-FIX (code — systemic, low effort)**
2. **FLS / user-mode — apply E16's pattern to E2, E6, E7, E10, E11.** Add `WITH USER_MODE` (or
   `WITH SECURITY_ENFORCED`) to every SOQL and `Security.stripInaccessible` (or `as user`) to every
   `insert`/`upsert`. E16 (`PRM_CaseDataManagerService.cls:117-180`) is the reference implementation. Clears
   23 of 25 High violations.
3. **Service-boundary — one architect decision** on `PersonContactId` resolution: either move
   `resolvePractitionerContacts()` into `PRM_PractitionerBatch` and inject `practitionerId` via `params`
   (E11-style), **or** ratify an explicit carve-out and amend
   [`prm-service-class-boundaries.mdc`](../../../.cursor/rules/prm-service-class-boundaries.mdc). Apply the
   ruling uniformly to E2/E6/E7/E10.

**Advisory (not blocking)**
4. **E16** — `EagerlyLoadedDescribeSObjectResult` (`cls:231`): the `getMap()` describe is cached statically, so
   impact is low; consider the lazy `fields.<name>` form or suppress with a note. Its CRUD flags are PMD
   false-positives — suppress with justification.
5. Prefer `PRM_TestDataFactory` over inline inserts; add `System.runAs` so FLS fixes are exercised (the Low CA
   findings, all services).
6. `PRM_PractitionerBatch` — 9 Moderate complexity findings; optional cleanup as services are extracted.

---

## Sign-off

| Reviewer | Date | Decision |
|----------|------|----------|
| _(pending architect — owner-block tier; CL-11 + systemic FLS)_ | | |

> **Note on method:** verified read-only from `origin/main` via a detached worktree; the local uncommitted
> working tree was deliberately left untouched per the user's instruction. To re-run after fixes, pull into a
> clean tree (or re-create the worktree) and invoke the `verifying-practitioner-build` skill.
