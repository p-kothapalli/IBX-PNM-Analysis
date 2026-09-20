# 06 — Agent Eval Harness (verifying the verifiers)

> The build-verification agents check delivered code. **This file defines how we check the agents
> themselves** — before any check is allowed to *block* a delivery. It is the analog of the Senior
> Mortgage Underwriting system's `mortgage_test_cases.json` → `Automated_Test_Report.md` (labeled
> cases → expected-vs-actual matrix), and the doc-based equivalent of the IBXQA `AiEvaluationDefinition`
> + `sf agent test run` gate.
>
> **Rule of the layer:** an agent's check stays **advisory** until it is calibrated on this corpus.
> No false-positive-prone check is promoted to `BLOCKED`/blocking without a passing eval run.

---

## 1. Why an eval harness (not optional)

Every reference agent ships a labeled test set and a pass/fail report. Without one we cannot state the
agents' false-positive / false-negative rate, so we cannot know whether a `PASS` is trustworthy or a
`NEEDS-FIX` is noise. Two lessons are baked in from the mortgage reference:

- **Deterministic tools are not automatically correct.** The mortgage DTI tool produced obviously wrong
  numbers and the Critic did not catch them. Our deterministic backbone (the SObject/DML extractor, the
  Parity-Ledger lookup, the governor-budget probe) must itself be unit-tested and **bounded** — the
  harness treats those tools as units under test, not as ground truth.
- **Label synonyms must be canonicalized.** The mortgage report flagged a `DENIED` vs. expected
  `REJECTED` mismatch as a miss. Our verdict vocabulary is fixed (§4) so a synonym is never scored as a
  failure.

---

## 2. The labeled corpus

The corpus lives at `docs/build-verification/eval/` and is git-tracked. Each case is a small, real
delivery (or a seeded copy of one) plus an **expected outcome** the agents must reproduce.

```
docs/build-verification/eval/
  corpus.md                 # the case index (this table, machine-readable)
  cases/
    P01_practitioner_pass/  # known-good delivery  -> expected PASS
    D01_missing_object/     # seeded defect        -> expected NEEDS-FIX (Parity)
    D02_soql_in_loop/       # seeded defect        -> expected NEEDS-FIX (Governor)
    ...
  reports/
    eval_<date>.md          # the expected-vs-actual matrix (generated)
```

### 2.1 Known-good cases (expected `PASS`)

Pick already-built, already-reviewed `PRM_*` classes that the team agrees are correct. Each is a
**positive control**: the agents must NOT raise a blocking finding. A false positive here is the most
damaging failure mode (it erodes trust), so positive controls are weighted heavily in the gate (§5).

| Case | Source artifact | Resolved step | Expected verdict |
|------|-----------------|---------------|:---------------:|
| `P01` | a merged `PRM_*Service` for a Delegated step | E# · Delegated | `PASS` |
| `P02` | a merged `PRM_*Batch` (bulk, one DML/object) | batch · both | `PASS` |
| `P03` | a merged `PRM_*Selector` (Epic D) | read layer | `PASS` |

### 2.2 Seeded-defect cases (expected `NEEDS-FIX` / `BLOCKED`)

Take a known-good class and inject **exactly one** defect each. The expected verdict **and the agent that
must catch it** are both asserted — a case "passes" only if the *right* agent fires for the *right* reason.

| Case | Seeded defect | Expected verdict | Must be caught by |
|------|---------------|:---------------:|-------------------|
| `D01` | Drop one object the legacy DR created for that step | `NEEDS-FIX` | Parity Auditor |
| `D02` | SOQL/DML inside a `for` loop | `NEEDS-FIX` | Governor & Bulk-Safety |
| `D03` | Write a Delegated-only object on the IBC path (ungated branch) | `NEEDS-FIX` | Branch-Coverage |
| `D04` | Duplicate-prone CMA write (no coalescing/upsert key) | `NEEDS-FIX` | Parity Auditor / Governor |
| `D05` | Leave a `*__c` field map "inferred" (CL-11 not signed off) | `BLOCKED` | Clarification-Log Gate |
| `D06` | `GroupRelatedBatch` delivery with no batch↔service mapping (CL-15) | `BLOCKED` | Clarification-Log Gate |
| `D07` | Service that bypasses `PRM_ServiceBase` / talks to another domain directly | `NEEDS-FIX` | Service-Boundary |
| `D08` | Tests with no assertion on a created record (coverage without proof) | `NEEDS-FIX` | Test-Adequacy + **Critic** |
| `D09` | Output contract claims a field for a record the service never writes | `NEEDS-FIX` | Contract + **Critic** |
| `D10` | Async job targeting `NetworkMember` (out of CL-6 pilot scope) | `BLOCKED` | Clarification-Log Gate |

> **Cross-agent cases (D08, D09) are the Critic's calibration set.** A worst-of combiner reports
> "PASS + PASS"; only the [Critic](01_Agent_Catalog.md#agent-9--critic--cross-validator) catches the
> contradiction. These cases exist specifically to prove the Critic works.

### 2.3 Tool-trust cases (the backbone is under test too)

| Case | Target | Expected |
|------|--------|----------|
| `T01` | SObject/DML extractor on a class with mixed DML | extracts the exact object+operation set |
| `T02` | Parity-Ledger lookup for a known step | returns the exact expected object/field rows |
| `T03` | Governor-budget probe on a 200-record bulk path | reports DML/SOQL counts within budget |

If a tool case fails, every agent verdict that depends on that tool is **`INCONCLUSIVE`**, never `PASS`
(the degraded-mode rule — see [`05_Reference_Agent_Audit.md`](05_Reference_Agent_Audit.md) G7).

---

## 3. Running the harness

For each case the DoD Verifier runs the full roster (verifiers → Critic → aggregate) against the case
artifact and records the resulting [Verification State](00_Architecture.md#45-verification-state-the-shared-append-only-object).
The harness then compares the State's `verdict`, the firing agent(s), and the `risk_score` against the
case's expected values, and writes one report (§4). Determinism is required: reasoning agents run at
`temperature=0` so a case's outcome is reproducible run-to-run.

---

## 4. The expected-vs-actual report

Mirrors the mortgage `Automated_Test_Report.md`: one row per case, a per-case **Match** column, and a
roll-up. Verdict labels are canonicalized to exactly `PASS | NEEDS-FIX | BLOCKED | INCONCLUSIVE` before
comparison (a synonym is normalized, never scored as a miss).

```
| Case | Expected verdict | Actual verdict | Expected catcher | Actual catcher | Risk | Match |
|------|------------------|----------------|------------------|----------------|------|:----:|
| P01  | PASS             | PASS           | —                | —              | 8    | ✅    |
| D01  | NEEDS-FIX        | NEEDS-FIX      | Parity           | Parity         | 55   | ✅    |
| D08  | NEEDS-FIX        | PASS           | Test+Critic      | (none)         | 12   | ❌    |
| ...  |                  |                |                  |                |      |      |

Agreement: 9/10 (90%)   False positives: 0   False negatives: 1   Critic contradiction recall: 1/2
```

A case is a **match** only when the verdict matches **and** the expected agent caught it for the right
reason. A correct verdict reached by the wrong agent is a partial miss (flagged, not counted as a pass).

---

## 5. The calibration gate (when a check may block)

A verification check progresses through three trust tiers, gated by its corpus metrics:

| Tier | Behavior | Promotion criterion (on the corpus) |
|------|----------|-------------------------------------|
| **Advisory** | Reports findings; never blocks | default for any new/changed check |
| **Soft-gate** | Demotes verdict to `NEEDS-FIX` | **0 false positives** on the known-good cases (§2.1) |
| **Hard-gate** | Can demote to `BLOCKED` | soft-gate criterion **and** ≥ the target recall on its seeded-defect cases |

Targets (tunable, pinned here so changes are reviewed):
- **False-positive rate on positive controls: 0** — a check that flags good code cannot block.
- **Seeded-defect recall ≥ 0.9** for the agent that owns the defect class.
- **Critic contradiction recall ≥ 0.9** on D08/D09-style cross-agent cases before the Critic's
  contradictions are allowed to demote a verdict.
- **Risk-score thresholds** (`auto ≤ 20`, `architect 21–60`, `owner-block 61–100`) are accepted only if
  every positive control scores `auto` and every `BLOCKED` case scores `owner-block` on the corpus.

A check that regresses below its tier's criterion on a later run is automatically **demoted** until fixed.

---

## 6. Maintenance

- **Grow the corpus from real misses.** Every time the agents miss a real defect (false negative) or flag
  good code (false positive) in practice, add that artifact as a new case with the correct expected label.
- **Re-run on agent changes.** Any edit to a skill/rule/Critic weight re-runs the harness; the
  `eval_<date>.md` report is committed alongside the change so the trust tier is auditable.
- **Keep it small and fast.** ~10–15 cases is enough to calibrate; the corpus is a regression net, not an
  exhaustive test suite. Cases must contain **no real PHI/Ids** (see [`05`](05_Reference_Agent_Audit.md) G9).

---

*Grounded in the reference harness at `~/Documents/AgenticAI/Senior Mortgage Underwriting System/`
(`mortgage_test_cases.json`, `Automated_Test_Report.md`) and the IBXQA `AiEvaluationDefinition` /
`sf agent test run` mapping. This closes gap **G2** from [`05_Reference_Agent_Audit.md`](05_Reference_Agent_Audit.md).*
