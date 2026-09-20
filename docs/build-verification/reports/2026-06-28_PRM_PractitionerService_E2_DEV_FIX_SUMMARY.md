# Developer Fix Summary — `PRM_PractitionerService` (E2)

> Companion to the [Verification Report](./2026-06-28_PRM_PractitionerService_E2.md). This is the
> **developer-facing punch list**: every finding, why it matters, the exact location, and a concrete fix
> pattern. **No code was changed** producing this document — it is read-only analysis.
>
> Backbone now complete: `sf code-analyzer run` executes (JDK 17 installed via Homebrew `openjdk@17`) and
> Apex tests pass 7/7 at 94 % on `ibx-dev`. Raw scanner output:
> [`…_E2_codeanalyzer.json`](./2026-06-28_PRM_PractitionerService_E2_codeanalyzer.json).

| | |
|---|---|
| **Artifact** | `force-app/main/default/classes/PRM_PractitionerService.cls` (+ `…ServiceTest.cls`) |
| **Verdict** | **BLOCKED** (process gate, not a rewrite) · risk **80/100** · tier **owner-block** |
| **Code Analyzer** | 30 violations — **10 High** (all FLS/CRUD), **4 Moderate** (complexity), **16 Low** (test style) |
| **Tests** | 7/7 pass, `PRM_PractitionerService` **94 %** on `ibx-dev` |

The class is fundamentally well-built — clean object parity, bulk-first (4 bulk DML, no SOQL/DML in loops),
idempotent, 94 % coverage. Nothing here is a redesign. The fixes are: **1 process sign-off**, **2 code
NEEDS-FIX**, plus mechanical scanner clean-up.

---

## Priority 0 — BLOCKER (process, owner: Epic-E lead)

### B1. CL-11 — sign off the E2 DR→object field map
- **What:** Object-level parity is verified (the four objects, record types, name normalization all match
  legacy). **Field-level** parity is gated by **CL-11**, a hard gate in [`CLAUDE.md:153`](../../../CLAUDE.md) —
  the per-service DataRaptor→object field map must be signed off *before* the build is certified.
- **Why it blocks:** without the signed map there is no ground truth to assert that every legacy DataRaptor
  field landed on the right SObject field. The build cannot be promoted on "looks right".
- **Action:** produce/sign the E2 field map (legacy DataRaptor field → target SObject field) and attach it.
  This flips the BLOCK; it is not a code change.

---

## Priority 1 — NEEDS-FIX (code)

### F1. FLS / user-mode missing on every SOQL + DML — *Code Analyzer: 10× High `ApexCRUDViolation`*
The class declares `with sharing` (good for record visibility) but performs **no field-/object-level
enforcement**. Per [`CLAUDE.md` §6](../../../CLAUDE.md) every query/DML must run in user mode (or strip
inaccessible fields). Code Analyzer flags all 10 access points:

| # | Line | Operation | Object | Fix |
|---|------|-----------|--------|-----|
| 1 | `cls:112` | SOQL | `Account` (PersonContactId, PRM_CaseManager__c) | add `WITH USER_MODE` — but see **F2** (this query should move out of the service) |
| 2 | `cls:153` | SOQL | `CareTaxonomy` | add `WITH USER_MODE` — see **F2** |
| 3 | `cls:295` | `upsert` | `HealthcareProvider` | DML `as user` |
| 4 | `cls:311` | SOQL | `HealthcareProviderNpi` (dedupe) | `WITH USER_MODE` |
| 5 | `cls:327` | `insert` | `HealthcareProviderNpi` | DML `as user` |
| 6 | `cls:356` | SOQL | `Identifier` (dedupe) | `WITH USER_MODE` |
| 7 | `cls:371` | `insert` | `Identifier` | DML `as user` |
| 8 | `cls:382` | `upsert` | `HealthcareProviderTaxonomy` | DML `as user` |

**Fix pattern (SOQL):**
```apex
// before
for (HealthcareProviderNpi existing : [
    SELECT Id, Npi FROM HealthcareProviderNpi WHERE Npi IN :npis
]) { ... }

// after
for (HealthcareProviderNpi existing : [
    SELECT Id, Npi FROM HealthcareProviderNpi WHERE Npi IN :npis WITH USER_MODE
]) { ... }
```

**Fix pattern (DML):**
```apex
upsert as user healthcareProviders HealthcareProvider.PRM_RecordKey__c;
insert as user npisToInsert;
```
If user-mode DML would reject legitimately system-owned writes, use
`Security.stripInaccessible(AccessType.CREATABLE, records)` and DML the `getRecords()` result instead, and
document why. Either way the scanner finding must be cleared or baseline-suppressed **with justification**.

> **Decision required:** confirm the async batch runs as a user with FLS on these objects (the expected model)
> vs. a system context. That choice picks `USER_MODE` vs. `stripInaccessible`. Do not silently leave system
> mode.

### F2. Service-boundary violation — service resolves its own context via SOQL
- **Where:** `resolveForeignKeys` (`cls:106-127`) SOQLs `Account` for `PersonContactId` **and** falls back to
  `Account.PRM_CaseManager__c` (`cls:123-124`); `resolveTaxonomyIds` (`cls:129-161`) SOQLs `CareTaxonomy`.
- **Rule:** [`.cursor/rules/prm-service-class-boundaries.mdc`](../../../.cursor/rules/prm-service-class-boundaries.mdc)
  — services must not run self-context SOQL or cross-object correlation; **`PRM_PractitionerBatch` injects all
  context** via `params`. The class header itself (`cls:8`) says *"The batch supplies all context… E2 resolves
  only PersonContactId + taxonomy refs it owns"* — but the code resolves them with its own queries, and the
  `PRM_CaseManager__c` fallback is correlation the header doesn't even claim.
- **Why it matters:** it breaks the bulk-context contract (the batch is supposed to be the single place that
  reads context), and it is the root of half the F1 FLS findings (queries 1 & 2). **Fix F2 first and two F1
  rows disappear.**
- **Two acceptable resolutions (architect picks one):**
  1. **Move resolution into `PRM_PractitionerBatch`** and pass `practitionerId` (PersonContactId),
     `caseManagerId`, and resolved taxonomy Ids in `params.practitioners[]`. Service becomes pure build+DML.
  2. **Ratify an explicit carve-out** for these specific reference lookups and amend
     `prm-service-class-boundaries.mdc` to document the exception (with rationale). Only with sign-off.
- This is flagged as a **Critic unresolved contradiction** (design intent vs. rule) — it needs an architect
  decision, not a unilateral code tweak.

---

## Priority 2 — Moderate (Code Analyzer: complexity)

| Finding | Location | Detail | Suggested fix |
|---------|----------|--------|---------------|
| `CognitiveComplexity` | `writeHealthcareProviderNpis` `cls:298-339` | cognitive **15** (threshold 15) | extract the dedupe-query + resolved-Id back-fill into helpers; the nested null/contains checks are the cost |
| `CyclomaticComplexity` | `writeHealthcareProviderNpis` `cls:298-339` | cyclomatic **12** | same extraction reduces branch count |
| `CognitiveComplexity` | class `cls:10-454` | total **78** (threshold 50) | naturally drops once F2 moves resolution out and the method above is split |
| `CyclomaticComplexity` | class `cls:10-454` | total **77** | same |

Not blocking, but worth doing while touching the file for F1/F2 — much of the class total is the existing-NPI
branching that F2's refactor will simplify.

---

## Priority 3 — Low (test class hygiene, `PRM_PractitionerServiceTest.cls`)

Mechanical, safe, no behavior change. Clears 16 Low findings:

- **`@isTest` / `@testSetup` casing → `@IsTest` / `@TestSetup`** (PascalCase): lines
  `10, 14, 85, 142, 161, 186, 211, 227` (`AnnotationsNamingConventions`).
- **`System.runAs()` missing** in each `@IsTest` method (`ApexUnitTestClassShouldHaveRunAs`): methods at
  `86, 143, 162, 187, 212, 228`. Wrap the act/assert in `System.runAs(testUser)` with a least-privilege user —
  this also makes the F1 user-mode fixes meaningfully *tested* (FLS only bites under a real user).

---

## Advisory (not scanner-driven)

- **A1. Existing-NPI delta path is untested.** `existingHcpNpiId` (`cls:22`, used at `cls:329-337`) reuses an
  existing NPI and builds no new NPI record. Parity allows this delta-only path, but **no test exercises it**
  (Critic low-confidence gap). Add a test that seeds an existing `HealthcareProviderNpi`, passes its Id, and
  asserts no duplicate insert + correct `resolvedHealthcareProviderNpiId`.
- **A2. Use `PRM_TestDataFactory`.** The test uses inline `insert`s; standardize on the factory per repo
  convention so FLS/required-field drift is caught centrally.

---

## Suggested fix order

1. **B1** (CL-11 sign-off) — unblocks certification; parallelizable, owned by Epic-E lead.
2. **F2** (architect decision on boundary) — do this *before* F1, because moving the `Account`/`CareTaxonomy`
   queries into the batch deletes F1 rows 1 & 2 outright.
3. **F1** (user-mode on the remaining DML + dedupe SOQL).
4. **P3** test casing + `System.runAs` (lets F1 be verified under a real user).
5. **A1/A2** existing-NPI test + factory.
6. **P2** complexity — falls out naturally from F2.
7. Re-run the backbone (below); confirm 0 High violations and ≥85 % coverage; resubmit for verification.

---

## How to reproduce the backbone locally

Java is now installed (Homebrew `openjdk@17`, keg-only). To run Code Analyzer in a fresh shell:

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version   # expect openjdk 17.x

cd ibx-dev-project
sf code-analyzer run \
  --workspace force-app/main/default/classes/PRM_PractitionerService.cls \
  --workspace force-app/main/default/classes/PRM_PractitionerServiceTest.cls \
  --view detail

sf apex run test --target-org ibx-dev \
  --tests PRM_PractitionerServiceTest --code-coverage --result-format human
```

> To make `JAVA_HOME` permanent: `echo 'export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"' >> ~/.zshrc`.
> CI should pin the same (or any Zulu/OpenJDK 11+) so the SFGE/PMD pass is deterministic.

---

## Definition of Done (re-verify after fixes)

- [ ] CL-11 field map signed off (B1)
- [ ] `sf code-analyzer run` → **0 High** `ApexCRUDViolation`
- [ ] Boundary resolved per architect decision (F2) and rule doc updated if a carve-out was ratified
- [ ] Existing-NPI delta path covered by a test (A1)
- [ ] Tests green, `PRM_PractitionerService` ≥ 85 %
- [ ] Re-run `verifying-practitioner-build` → verdict **PASS**
