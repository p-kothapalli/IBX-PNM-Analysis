# USER STORY 6: ReCred Termination Services — Establish Apex Test Coverage Before Changing Them

**Persona:** Provider Data Admin (PDA) Specialist
**Priority:** P1
**OmniScript:** N/A (Apex service layer behind `PRM_ReCredUpdate_English`)
**Integration Procedures:** `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v11, active) — invokes the termination path under test
**Relevant Requirements:** `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §5 H1; prerequisite for US-1, US-2, and `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md`

---

## Story

**As a** Provider Data Admin (PDA) Specialist,
**I want** the code that terminates practitioners, locations and networks on my re-cred cases to be covered by automated tests,
**So that** fixes to the removal logic cannot silently introduce a new mass-termination defect that I only discover after provider data is already damaged.

**Why it matters:** The three Apex classes that execute re-cred terminations have **no test coverage at all** — including the 628-line service that already carries a partially completed change. Every open story in this area (practitioner-scope fix, termination-date fix, PNC re-point) modifies this code. Changing untested termination logic is how Bug 1216121 reached production in the first place. This story creates the safety net **before** those changes land.

**Persona note:** the consumer of this story is a developer, but the risk being managed is the PDA Specialist's — a regression here corrupts the provider data they are accountable for. The developer-facing contract is in Technical Implementation.

---

## Scope

| Component | Size | Current test references |
|---|---|---|
| `PRM_FullPracTermRecredBatchService` | 628 lines | **none** |
| `PRM_RCATTerminationEffectivityHelper` | 219 lines | **none** |
| `PRM_PracticeLocationTerminationBatch` | 466 lines | **none** |

**In scope:** new test classes for the three uncovered classes above, covering the termination behaviours the business depends on.

**Out of scope:** changing the behaviour of these classes (that is US-1, US-2, and the PNC re-point story); classes that already have some coverage, such as the practitioner-termination and RCAT termination helpers.

---

## Current State (from codebase)

Grepping every `*Test.cls` in `force-app/main/default/classes/` for each class name returns **zero** references for all three. The org's deploy gate is 75% and the workspace standard is ≥85%; these classes contribute their full uncovered line count against both.

`PRM_FullPracTermRecredBatchService` is the class that already contains the completed half of the PNC re-point (it reads the practice-location-level PNC flag at line 372), so it is being actively modified with no regression protection.

---

## Acceptance Criteria

> Pattern A ACs describe the business behaviours the tests must prove. The class-level testing contract is in Technical Implementation.

**AC-1 — A single-practitioner termination is proven correct**

**Given** a re-credentialing case terminating one practitioner at one practice location,
**When** the termination runs,
**Then** an automated test proves that practitioner's affiliation, taxonomy and network rows are end-dated,
**And** the test asserts the resulting field values rather than only asserting that no error occurred.

**AC-2 — A bulk termination is proven to stay within platform limits**

**Given** a re-credentialing termination covering 200 practitioner-location combinations,
**When** the termination runs,
**Then** an automated test proves all records are processed,
**And** the test proves the run completes without exceeding platform processing limits.

**AC-3 — Other practitioners at a shared location are proven untouched**

**Given** a practice location with several active practitioners where only one is being terminated,
**When** the termination runs,
**Then** an automated test asserts the other practitioners' rows are unchanged,
**And** this test fails if the over-broad scope defect is reintroduced.

**AC-4 — The location cascade is proven for the last active practitioner**

**Given** the practitioner being terminated is the only active practitioner at the practice location,
**When** the termination runs,
**Then** an automated test proves the practice location is also terminated,
**And** a companion test proves the location is **not** terminated when other active practitioners remain.

**AC-5 — Protected (PNC) locations are proven to be handled correctly**

**Given** a practice location flagged as protected from termination,
**When** the termination runs,
**Then** an automated test proves that location is excluded from termination,
**And** the test proves a non-protected location under the same group **is** terminated.

**AC-6 — Failure paths are proven not to leave partial data silently**

**Given** a termination run encounters a record it cannot process,
**When** the termination runs,
**Then** an automated test proves the failure is recorded rather than silently swallowed,
**And** the test proves the outcome is the documented behaviour for a partial failure.

**AC-7 — Empty and no-op inputs are handled**

**Given** a termination is invoked with no qualifying records,
**When** it runs,
**Then** an automated test proves it completes without error and writes nothing.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FullPracTermRecredBatchServiceTest` | New Apex test class | Cover the re-cred full-termination service: single, bulk (200), PNC-protected, last-active-practitioner cascade, empty, and failure paths | Drives AC-1 – AC-7 |
| `PRM_RCATTerminationEffectivityHelperTest` | New Apex test class | Cover effective-date derivation branches (past, future, empty effective-to) and the Active flag outcomes | Drives AC-1, AC-4 |
| `PRM_PracticeLocationTerminationBatchTest` | New Apex test class | Cover the practice-location termination batch: single, bulk, cascade-vs-no-cascade, and non-par / full-term reasons | Drives AC-2, AC-4 |
| Shared test-data factory | New or extended Apex test utility | Build a multi-practitioner facility fixture (one group, several practitioners, PNC and non-PNC locations) reusable by all three test classes and by US-1's regression | Supports all ACs |

Testing standards to follow (per the workspace Apex conventions):

- Wrap the code under test in `Test.startTest()` / `Test.stopTest()`; assert async completion after `stopTest()`
- **Never** use `@isTest(SeeAllData=true)` — build data through the factory
- Assert **outcomes** (field values, record counts), not merely absence of exceptions
- Cover bulk (200), single, empty, and negative paths for each class

---

## Definition of done

- [ ] All three classes have a dedicated test class deployed
- [ ] Each of the three classes is at **≥ 85%** coverage individually, not just in aggregate
- [ ] The multi-practitioner facility fixture exists in a shared test factory and is reused by US-1's regression
- [ ] AC-3's test is demonstrated to **fail** when the over-broad removal scope is deliberately reintroduced (proves it is a real guard, not a passing no-op)
- [ ] AC-5's test covers both a protected and a non-protected location under the same group
- [ ] The full test suite passes with no new failures in existing termination-related tests
- [ ] Coverage is verified in the target org, not only locally

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Should this story be completed **before** US-1 and US-2 merge, or in parallel? | Sequencing it first is safer but delays the P0 defect fixes; in parallel risks writing tests against changing behaviour | Technical / Product |
| 2 | What is the documented expected behaviour on a partial termination failure — halt, continue, or roll back? | AC-6 cannot assert an outcome that has never been specified | BA / Technical |
| 3 | Is there an existing test-data factory to extend, or should a new one be created for this area? | Avoids a duplicate fixture and keeps setup consistent with the rest of the suite | Technical |
| 4 | Should the PNC assertion in AC-5 use the practice-location-level flag or the group-level flag? | The PNC re-point story is changing this mid-flight; the test must target the intended end state | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_FullPracTermRecredBatchService` | Apex | **HIGH** | Largest uncovered class; actively being modified |
| `PRM_PracticeLocationTerminationBatch` | Apex | **HIGH** | Executes location terminations |
| `PRM_RCATTerminationEffectivityHelper` | Apex | MEDIUM | Effective-date derivation feeding the above |
| Org-wide test coverage percentage | Deployment | MEDIUM | Improves the deploy gate margin |
| US-1 / US-2 / PNC re-point | Stories | **HIGH** | All three become materially safer to implement |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Shared multi-practitioner test fixture | Apex test utility | **L** | Reused by three test classes and US-1 |
| `PRM_FullPracTermRecredBatchServiceTest` | New Apex test | **XL** | 628 lines, many branches |
| `PRM_PracticeLocationTerminationBatchTest` | New Apex test | **XL** | 466 lines incl. cascade paths |
| `PRM_RCATTerminationEffectivityHelperTest` | New Apex test | **L** | 219 lines, date branches |
| Coverage verification + suite run | QA / Technical | **M** | Per-class coverage confirmation |

**Total Estimated Effort:** **XXL** (roughly 3–4 days) — AI-estimated, validate with team.
