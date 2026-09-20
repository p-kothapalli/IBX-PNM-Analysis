# 04 — Adoption Playbook

> How architects and developers actually use the build-verification agents day-to-day, the deterministic
> commands that back every verdict, the Definition-of-Done checklist, the report template, and the specs
> for the `.cursor/skills/` + `.cursor/rules/` to scaffold next.

---

## 1. The two ways to invoke

### 1.1 In-IDE (single delivery — primary path)

A developer finishes a class/component; an architect (or the dev) opens the file(s) in Cursor and asks
in natural language. The **DoD Verifier** picks it up (via the skill description) and routes.

Trigger phrases that should invoke the layer:

- *"Verify this Practitioner Creation delivery."*
- *"Check `PRM_PractitionerService` for Delegated parity against the legacy flow."*
- *"Run build verification on the changed files."*
- *"Does `PRM_HealthcareFacilityNetworkService` match the legacy network DataRaptors?"*
- *"Is this batch bulk-safe and within the governor budget?"*

Explicit nudge if it doesn't auto-trigger: *"Use the `verifying-practitioner-build` skill on this file."*

### 1.2 On a PR (diff-scoped)

A `code-review` subagent (Cursor Task) runs the same roster against `git diff <base>...HEAD` scoped to
changed `force-app` files, and posts the consolidated report as a PR comment + advisory status. Launch
it from the PR or as a scheduled review on the feature branch.

> The org's deploy gate already runs Code Analyzer + Apex tests; the agents add the parity / branch /
> contract / async **reasoning** the gate can't express.

---

## 2. Deterministic backbone (the commands every verdict rests on)

These are the existing org commands (default alias `qa-sandbox`); the agents run them and interpret the
output. They are CI-ready as-is.

```bash
# Governor & Bulk-Safety — static analysis over changed files (running-code-analyzer skill)
sf code-analyzer run --workspace "force-app/main/default" --severity-threshold 2

# Test-Adequacy — run the delivery's tests with coverage (running-apex-tests skill); target >= 85%
sf apex run test -n PRM_PractitionerServiceTest --target-org qa-sandbox --code-coverage --result-format human -w 10

# Parity (object-level) — confirm the legacy reference is the ACTIVE OmniStudio version
#   (analyzing-omnistudio-dependencies skill; reconcile reference tables to active *.oip-meta.xml / *.rpt-meta.xml)

# Async / partial-failure — exercise the chain + DLQ in an integration test, then inspect
sf apex run test -n PRM_AsyncOrchestratorTest --target-org qa-sandbox --code-coverage -w 10

# Shadow-mode parity (G4) — run new beside legacy and diff created records field-by-field
#   (consume the harness's audit object/JSON; do not re-derive parity by hand)
```

Pre-commit hooks (`.husky` + `lint-staged`) already run Prettier/ESLint/Jest on staged files — the
agents assume these pass and do not duplicate them. **Do not bypass hooks** (`--no-verify`).

---

## 3. Definition-of-Done checklist (what a PASS means)

The DoD Verifier asserts all of these for a service/batch delivery (from [`CLAUDE.md`](../../CLAUDE.md)
§6 + §7.3, plus the parity layer):

- [ ] **Parity:** every object the legacy step created is produced; no unexplained extras; record types
      correct (cached describe, not SOQL). Field-level parity if CL-11 closed for this service.
- [ ] **Branch:** IBC vs Delegated split + Delegated sub-gates (`CaseManagerId` / file / languages /
      existing-primary / `isExistingNPI`) match the legacy decision tree.
- [ ] **Bulk-first:** one bulk DML per object type; no SOQL/DML in loops; parents before children.
- [ ] **Governor:** within per-batch budgets (IBC DML ≤ 12 · Delegated ≤ 28 · SOQL ≤ 40 · CPU < 5 s ·
      heap < 2 MB), proven by the perf harness.
- [ ] **Security:** `with sharing`; `WITH USER_MODE` / `stripInaccessible`; no hardcoded Ids.
- [ ] **Service boundary:** `extends PRM_ServiceBase`; reads context from `params`; no self-context SOQL;
      returns a generic response map.
- [ ] **Async (batch/orchestrator):** halt-on-failure; idempotent (External-Id upsert / status guard /
      CMA pre-check); DLQ to `PRM_FailedRecordStaging__c`; resumable manual retry; **no** whole-submission
      savepoint; `findNextJob` called in `finish()`.
- [ ] **Tests:** ≥ 85%; bulk (200) + single + empty + negative/halt-on-failure; real outcome assertions;
      no `SeeAllData`; `Test.startTest/stopTest` for async; `PRM_TestDataFactory`.
- [ ] **Clarification Log:** no open-CL contradiction; no `*__c` left "inferred"; real log object names
      (`PRM_ExceptionLog__c`); reuses existing selectors/validator.

Any unchecked item → `NEEDS-FIX`. Any open-CL contradiction or unsigned field map → `BLOCKED`.

---

## 4. Verification Report template

Each run writes one report to `docs/build-verification/reports/<artifact>_<YYYY-MM-DD>.md`. The report
is a **deterministic render of the Verification State** ([`00_Architecture.md`](00_Architecture.md) §4.5)
— nothing below is re-narrated by the LLM:

```markdown
# Verification Report — <PRM_ClassName> (<YYYY-MM-DD>)

- Artifact(s):        <files>
- Resolved step:      <E# · batch · IBC/Delegated> (Parity Ledger §<n>)
- Agents run:         <list>
- Deterministic runs: code-analyzer <pass/fail> · tests <coverage%> · shadow-parity <ref>

## Verdict: PASS | NEEDS-FIX | BLOCKED      Risk: <0-100>      Review tier: auto | architect | owner-block

| Agent | Verdict | Evidence (tool output / Ledger citation) | Finding |
|-------|:------:|------------------------------------------|---------|
| Parity Auditor      | … | Ledger §3 row <n>; DR table … | … |
| Branch-Coverage     | … | decision tree §… | … |
| Contract Conformance| … | sample fixture … | … |
| Governor & Bulk     | … | code-analyzer rule … ; perf harness DML=… | … |
| Async / Reliability | … | test … ; DLQ row … | … |
| Service-Boundary    | … | rule … | … |
| Test-Adequacy       | … | coverage …% | … |
| Clarification Gate  | … | CL-… | … |

## Critic — cross-agent contradictions
| Between | Contradiction | Resolved? |
|---------|---------------|:---------:|
| Parity ↔ Test-Adequacy | parity PASS on <object> but no test asserts it | no |
(none → "No contradictions detected.")

## Open blockers
- <CL-id> — <owner> — <what must happen>

## Reviewer sign-off
- Architect: __________  Date: ______  (overrides require written justification)
```

This is the doc-based analog of the IBXQA `PRM_AgentDecision__c` audit trail — append-only, git-tracked,
and the artifact an architect signs. The verdict + risk + review tier are computed deterministically from
the state (the LLM only writes the per-agent **Finding** prose).

---

## 5. Build order (how to scaffold the agents — doc → rules → skills → subagent)

Highest leverage / lowest cost first. None of this is built yet; this deliverable is the spec.

1. **Parity Ledger field columns** — close CL-11 per service and fill [`02_Parity_Ledger.md`](02_Parity_Ledger.md)
   §3 field detail. (Unblocks field-level parity; pure docs.)
2. **Rules** (`.cursor/rules/`) — fast, always-on invariants:
   - `prm-parity-objects.mdc` (glob `**/classes/PRM_*Service.cls`, `**/classes/PRM_*Batch.cls`) — the
     §6 parity traps as hard rules (PPL=HCPF, no HCPFN, one CDM write, `ContactProfile`).
   - `prm-bulk-governor.mdc` — one DML per object type, no SOQL/DML in loops, RT-by-describe, `WITH USER_MODE`.
   - `prm-async-reliability.mdc` (glob `**/classes/PRM_*Batch.cls`, `PRM_AsyncOrchestrator.cls`) —
     halt-on-failure, idempotency, DLQ, no whole-submission savepoint.
   - (reuse the existing `prm-service-class-boundaries.mdc` for Agent 6.)
3. **Skills** (`.cursor/skills/`) — reasoning + which commands to run (descriptions drive auto-invoke):
   - `verifying-practitioner-build` — the umbrella DoD-Verifier skill: classify artifact → route →
     aggregate → emit report. Description triggers on the §1.1 phrases.
   - `verifying-practitioner-parity` — the Parity Auditor: read the Ledger, static-scan SObjects,
     reconcile active OmniStudio version, classify deltas.
   - Reuse existing: `running-code-analyzer`, `running-apex-tests`, `analyzing-omnistudio-dependencies`,
     `debugging-apex-logs` (no new tooling).
   - Each new skill follows the org pattern: upstream best-practice body + an `## IBX Overrides &
     Additions` section; lives once under `.cursor/skills/<name>/SKILL.md`, git-tracked, synced to
     `IBXEnhancements`.
4. **Subagent prompts** — the DoD Verifier (in-IDE) and the PR `code-review` runner, both emitting the
   §4 report. Pin a model, run reasoning agents at `temperature=0`, and keep the prompt
   deterministic-first. Include the **Critic** pass (Agent 9) after the verifiers.
5. **Wire the shadow-parity harness** to emit a machine-readable parity audit the Parity Auditor consumes.
6. **Stand up the eval harness** ([`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md)) — the labeled
   good + seeded-defect corpus and the expected-vs-actual report. This is the gate that decides when a
   check is allowed to block (§6 below), so build it alongside the first skills, not after.

---

## 6. Rollout sequencing

1. **Pilot on one already-built service** (e.g. `PRM_PractitionerService` / `PRM_CaseService`) — prove
   the Parity Auditor + Governor + Test agents against code that exists, calibrate false-positive rate.
2. **Add the async agents** once a batch + `PRM_AsyncOrchestrator` are stable (they already exist).
3. **Turn on the PR subagent** as advisory (non-blocking) for two weeks; measure reviewer-accept rate.
4. **Make selected checks blocking** (governor, test coverage, service boundary — the deterministic ones)
   only after each check passes the **calibration gate** in [`06_Agent_Eval_Harness.md`](06_Agent_Eval_Harness.md)
   §5 (0 false positives on the known-good corpus); keep parity/contract advisory until CL-11 closes.
5. **Expand to LWC + metadata** deliveries last (lower parity surface).

---

## 7. What this layer is *not*

- **Not** a replacement for the architect's sign-off — verdicts are advisory and grounded; a human signs.
- **Not** a business-process agent — provider/policy decisions stay in the IBXQA `AgenticAI` Agentforce
  stack.
- **Not** a new runtime — it is skills + rules + subagent prompts + existing CLI, in the IDE/PR loop.
- **Not** authorized to resolve open Clarification-Log items — it blocks and names the owner.
- **Not** a substitute for G4 shadow parity — it *consumes* the shadow harness; it does not replace the
  field-by-field record diff before cutover.
