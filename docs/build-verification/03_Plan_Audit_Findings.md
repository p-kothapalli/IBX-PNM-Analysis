# 03 — Implementation-Plan Audit (Verifiability)

> A thorough audit of [`PRM_Implementation_Plan.md`](../implementation-plan/PRM_Implementation_Plan.md)
> and the surrounding design through one lens: **can a build-verification agent actually certify a
> delivery against the legacy guided flow?** For each area: what is checkable *today*, what is *blocked*,
> and the divergences a reviewer must not mistake for defects (or miss as real risks).

---

## 1. Verifiability scorecard

| Verification concern | Checkable today? | Gated by | Confidence |
|----------------------|:----------------:|----------|:----------:|
| Object-level parity (right objects per step) | ✅ Yes | — | High |
| Field-level parity (right fields/values) | ⚠ Partial | **CL-11** (DR→object field maps not extracted) | Low until per-service sign-off |
| Branch correctness (IBC vs Delegated + gates) | ✅ Yes | — | High |
| Governor / bulk-safety | ✅ Yes (deterministic) | per-batch budgets to confirm (CL-10) | High |
| Async semantics (halt-on-failure, idempotency, DLQ, retry) | ✅ Yes | — | High |
| Service boundary discipline | ✅ Yes (existing rule) | — | High |
| Test adequacy (coverage + meaningful assertions) | ✅ Yes | — | High |
| Response-contract parity | ⚠ Re-scoped | async-only model (see §2) | Medium |
| Transaction / partial-failure parity | ⚠ Re-scoped | async-only model (see §2) | Medium |
| `GroupRelatedBatch` parity | ❌ No | **CL-15** (batch↔service mapping TBD) | Blocked |
| Network-record scope (HCFN vs NetworkMember) | ⚠ Mostly | **CL-6** (open) for edge scope | Medium |

---

## 2. The two structural divergences (must be encoded, not flagged as bugs)

The redesign deliberately changes two behaviors of the current guided flow. A naive parity check would
flag both as regressions. The agents are explicitly told these are **intended**, and instead verify the
*new* contract.

### 2.1 Synchronous response → async fire-and-return

**Legacy:** `PRM_PractitionerCreationContainer` runs everything in one synchronous transaction (30 s
`remoteTimeout`) and returns the full `PractitionerScreenRecordIds` / `GroupRecordIds` / `CaseManagerId`
payload to the OmniScript.

**New:** the intake wrapper validates, calls `PRM_CaseService` (sync) to create one Case Manager per
practitioner, inserts `PRM_AsyncJob__c`, and **returns `{ success, AsyncJobId }` immediately**; all heavy
creation runs asynchronously in the five batches.

**Audit finding.** "Byte-for-byte response parity" (stated as a goal in [`CLAUDE.md`](../../CLAUDE.md) §3.3)
is **not achievable for the deferred fields** and should not be the parity gate. The Contract Conformance
agent verifies the *new* immediate contract; the Parity Auditor verifies **record parity in shadow mode
(G4)** — the same records, fields, and record types eventually exist. Reviewers must confirm every
downstream consumer of the old synchronous fields has been migrated to read from the async result / LWC.

**Recommendation.** Restate the parity NFR as: *"immediate response = `{success, AsyncJobId}`; full
field-by-field **record** parity validated in shadow mode for both branches before cutover."* Track the
consumer-migration list as an explicit checklist item.

### 2.2 All-or-nothing rollback → halt-on-failure, no compensating rollback

**Legacy:** `TryCatchBlock` with `rollbackOnError=true` — any failure rolls back the entire submission.

**New:** per-batch transactions; on a batch failure the chain **halts**, completed batches' records
**persist**, the failed step goes to the DLQ, and a **manual, uncapped retry resumes from the failed
batch**. There is no whole-submission savepoint.

**Audit finding.** A partial failure produces a **different end-state** than legacy (legacy: nothing;
new: everything up to the failed batch). This is the core trade in CL-14. The Async/Reliability agent
must therefore verify the *new* guarantees (halt, DLQ, resumable retry, idempotent re-run) and must
**not** flag "records remain after a later step failed."

**Recommendation.** Add an explicit **partial-failure parity matrix** to G2/G4: for each batch boundary,
the expected set of persisted records when the *next* batch fails, and proof that a resume produces the
same final state as a clean run (idempotency). Without this, "parity" is undefined at failure points.
This is the single most important missing test artifact.

---

## 3. Blocking gaps (agents return `BLOCKED` until closed)

| Gap | Impact on verification | Owner action |
|-----|------------------------|--------------|
| **CL-11 — DR→object field maps not extracted** | Field-level parity cannot be certified; agents cap at object-level. This is the **biggest** limiter on parity confidence. | Extract + sign off the per-service field map (it is already a hard gate in the Epic E DoD) and fill the field columns in the [Parity Ledger](02_Parity_Ledger.md). |
| **CL-15 — batch↔service mapping** | `GroupRelatedBatch` has **no** assigned services; its parity and the `PRM_AsyncJobConfig__mdt` sequence are provisional. | Assign E-services to `GroupRelatedBatch` (or confirm it is empty) and finalize the seed sequence. |
| **CL-6 — async target scope** | Whether the heavy work is `HealthcareFacilityNetwork` only, or also `NetworkMember`/`NetworkMemberChunk`, changes E17/E18 parity scope. Epic A resolved HCFN as the target; the edge remains flagged open. | Confirm and close CL-6 so the network-scope check is unambiguous. |
| **CL-13 — home of removed foundation helpers** | Affects where `PRM_ExceptionLogger` usage / validation exception / `PRM_RecordTypes` live; the Service-Boundary + Async agents reference them. | Decide reuse-vs-relocate; the agents reference whatever is ratified. |

---

## 4. Parity traps the plan/reference will mislead a reviewer on

Encoded in [Parity Ledger §6](02_Parity_Ledger.md); summarized here as audit risk:

- **PPL = `HealthcarePractitionerFacility`** (CL-2) — legacy DR names imply a `PractitionerPracticeLocation`
  object that does not exist.
- **No `HealthcarePractitionerFacilityNetwork`** (CL-3) — legacy reference tables list HCPFN; async
  creates `HealthcareFacilityNetwork` only.
- **CDM coalescing** — legacy 3–4 writes vs one coalesced write; assert final state, not write count.
- **`ContactProfile` not `Contact`** (E10).
- **Transforms create nothing** — in-memory DRs have no object parity.
- **Misleading legacy element names** — `RA_GetInfoCodesList`/`RA_GetRecordTypeList` are list-shaping,
  not fetches.

A reviewer (human or agent) who matches the legacy reference literally will produce false NEEDS-FIX /
false PASS on every one of these. The ledger neutralizes them.

---

## 5. Strengths the plan already gives verification (leverage these)

- **G4 shadow-mode parity** is already in the plan — the build-verification layer plugs the agents into
  it rather than inventing a parity mechanism. Make the shadow harness emit a field-by-field audit object
  the Parity Auditor reads.
- **Per-service Definition of Done** ([`CLAUDE.md`](../../CLAUDE.md) §7.3) already enumerates most of what
  the DoD Verifier enforces — the agent operationalizes an existing checklist.
- **Existing rule** `prm-service-class-boundaries.mdc` already encodes Agent 6's job.
- **Deterministic baselines exist** — the legacy DML/SOQL counts (`Apex_Service_Flow.md` §"Sync DML count
  audit") give the Governor agent concrete ceilings.
- **Mature skill library** (`running-code-analyzer`, `running-apex-tests`, `analyzing-omnistudio-dependencies`,
  `debugging-apex-logs`) supplies the backbone with no new tooling.

---

## 6. Recommendations (ordered)

1. **Close CL-11 incrementally and feed the Parity Ledger.** Field-level parity is the highest-value,
   currently-blocked check. Each signed-off service map unblocks its row.
2. **Author the partial-failure parity matrix** (§2.2) — the missing artifact that makes failure-point
   parity well-defined. Add it to G2/G4.
3. **Restate the response-parity NFR** (§2.1) as immediate-contract + eventual-record parity, and track
   the downstream-consumer migration list.
4. **Resolve CL-15** so `GroupRelatedBatch` deliveries can be verified rather than blocked.
5. **Make the G4 shadow harness machine-readable** (audit object / JSON) so the Parity Auditor consumes
   evidence instead of re-deriving it.
6. **Scaffold the agents in build order** ([`04_Adoption_Playbook.md`](04_Adoption_Playbook.md) §"Build
   order"): the rules + Parity Ledger first (highest leverage, lowest cost), then the skills, then the
   DoD Verifier subagent.
