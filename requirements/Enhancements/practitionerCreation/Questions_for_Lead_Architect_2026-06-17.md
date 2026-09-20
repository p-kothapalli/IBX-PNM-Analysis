# Questions for the Lead Architect — Practitioner Creation Rebuild

**Date:** 2026-06-17
**Context:** Re-audit after `PRM_Implementation_Plan.md` was added. The plan resolves the earlier "missing master plan" gap, but it also re-numbers the service map and introduces async location/facility/network services whose design doc is absent. These are the open questions a builder cannot answer from the docs alone — grouped by theme, blocking items first.

**Grounding done for this pass (verified in repo):** `PRM_OmniUtils.titleCase`/`convertToListSobjects`/`updateExistignHCPNPI` exist (exact spelling, incl. the `Existign` typo); sub-IP `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` v2 exists; `PRM_ProviderFeature__c` exists; all Epic E Part-1 DataRaptors/IP versions exist. Could **not** confirm in repo: `ContactProfile` object, `NetworkMember(Chunk)`, `PractitionerDetailsSelector`/`PRM_*Selector` (only `PRM_AddressSelector`), `PRM_DeleteExceptionLogBatch` — likely partial retrieval, but they need org confirmation.

---

## A. Source-of-truth integrity (BLOCKING)

The plan's header cites these as "sources of truth (grounded against)," but none exist in the repo:

- `PRM_PractitionerCreation_Apex_Service_Flow.md` (call sequence + object impact + DML counts)
- `PRM_Apex_Reference_Implementation.md` (foundation/orchestrator blueprint)
- `PRM_Service_JSON_Contracts.md` (payload + async contracts)
- `PRM_Apex_Migration_Plan_v2.md` (risks)
- `Epic_E_Practitioner_Services_Part2.md` (E9–E18 — the async location/facility/network services)

**Q-A1.** Where do these five documents live, and can they be committed to the repo? Without the Service_Flow and JSON_Contracts docs, the field maps, DML counts, and payload keys cited throughout are unverifiable.

**Q-A2.** `Epic_E_..._Part2.md` defines E13–E18 — the async, high-volume, load-test-priority (⚡) services that are the entire justification for this rebuild. They currently have **no design doc in the repo**. Is Part 2 written? If not, the highest-risk half of EPIC E is undesigned.

---

## B. Service map / E-numbering reconciliation (BLOCKING)

Three documents now describe three **different** E-numberings, and the async worker name they point at disagrees:

| E# | TDD §11.6 | Implementation_Plan §8 | Epic_E Part 1 |
|----|-----------|------------------------|---------------|
| E12 | `PRM_AddressService` | `PRM_HealthcareProviderNpiService` | (n/a) |
| E13 | `PRM_FacilityNetworkService` | `PRM_HealthcareFacilityCreationService` | `PRM_FacilityNetworkService` |
| E14 | `PRM_ProviderFeatureService` | `PRM_HPFService` | (n/a) |
| E15 | `PRM_ExistingPrimaryPracticeService` | `PRM_ProviderFeatureService` | (n/a) |
| E16 | `PRM_CaseDataManagerService` | `PRM_CaseDataManagerService` | (n/a) |
| E17 | `PRM_Level4RecordCreationService` | `PRM_HealthcareFacilityNetworkService` | `PRM_Level4RecordCreationService` |
| E18 | (none) | `PRM_Level4RecordCreationService` (batch) | (none) |

**Q-B1.** Which document is authoritative for the E-numbering and service list? The plan also **removed** `PRM_AddressService` (sync) and `PRM_ExistingPrimaryPracticeService` that the TDD still lists. Are those removals ratified?

**Q-B2.** Epic C's seed `PRM_AsyncJobConfig__mdt` row sets `PRM_ServiceClassName__c = PRM_Level4RecordCreationService` with `PRM_Mode__c = Queueable`. But in this plan `PRM_Level4RecordCreationService` is **E18, a Batch** service. Is the pilot async worker Queueable or Batch — and is it `PRM_Level4RecordCreationService`, `PRM_HealthcareFacilityCreationService` (E13), or `PRM_HealthcareFacilityNetworkService` (E17)?

---

## C. The async high-volume model — the core gap (BLOCKING)

This is the most important set. The framework is sold as "metadata-driven async for high volume," but the fan-out model doesn't obviously scale with **data** volume.

**Q-C1 (fan-out by config vs by data).** `PRM_AsyncOrchestrator.createDetails()` creates **one child `PRM_AsyncJobDetails__c` per `PRM_AsyncJobConfig__mdt` row** (ordered by Sequence). It does **not** chunk by record count. So for a submission with, say, 5,000 locations/networks, where is the data split into chunks? In Batch mode the single child's `Database.Batchable` handles scope, but in **Queueable** mode there is no chunking at all. How does the engine chunk a large payload into multiple work units?

**Q-C2 (multiple async services per submission).** The Delegated async path needs E13 (facility, which itself invokes E14+E15), E17 (network), and E18 (batch Level-4). Are these **three CMDT rows** (Sequence 1/2/3) under one `PRM_AsyncJob__c`, dispatched by `findNextJob` chaining? If so, the seed config (one row) is incomplete. If E13 invokes E14/E15 **directly in code**, then the fan-out is a hardcoded chain, not metadata-driven — which is it, and why mix the two models?

**Q-C3 (sequential throughput).** `findNextJob` runs children **strictly sequentially** (one at a time, by Sequence). For a high-volume submission, is sequential processing of chunks fast enough to meet the "≥99% complete < 15 min" SLO, or do we need parallel fan-out (multiple Queueables enqueued at once)? What's the expected per-submission location/network count at peak?

**Q-C4 (CL-6 — the unresolved target object).** The TDD's CL-6/G-5 flagged that the real "high volume" may center on `NetworkMember`/`NetworkMemberChunk` (a proven chunking pattern already in the org), not `HealthcareFacilityNetwork`. This plan assumes HCFN (E17/E18) and **does not mention NetworkMember at all**. Has CL-6 been resolved? If the heavy object is actually NetworkMember(Chunk), the async sizing, mode, and even the service list change materially. This must be answered before EPIC C/E.

---

## D. Reuse vs. rebuild (HIGH)

**Q-D1 (existing address subsystem).** E13 (`PRM_HealthcareFacilityCreationService`) creates `Location` + `Address` + `HealthcareFacility` from scratch as async. But the org already has a substantial address subsystem — `PRM_AddressValidationService` (Precisely), `PRM_AddressManagementService`, `PRM_LocationQueryService`, `PRM_SmartAddressSearch`, `PRM_AddressSelector`. Does E13 reuse these, and is address **validation/standardization** still applied on the async path? Rebuilding address creation without the existing validation services risks bypassing USPS/Precisely standardization.

**Q-D2 (NPI service ownership).** `HealthcareProviderNpi` is created by E2 (practitioner), E3 (group), the "reusable" E12 (`PRM_HealthcareProviderNpiService`), and again listed under E13. Who owns NPI creation? Is E12 called by E2/E3/E13, or is NPI created in four places? The "reuse `PRM_OmniUtils.updateExistignHCPNPI`" note suggests update-vs-create logic that needs a single home.

**Q-D3 (validator — port vs rewrite).** F2 says `PractitionerCreationPayloadValidator` **"replaces"** the existing `PRM_PractitionerCreationValidator.validate` (which exists). The TDD (CL-9/G-7) said **port/refactor**, don't rewrite. Will F2 preserve every existing validation rule (so we don't regress branch-specific validation), and is there a rule-by-rule parity checklist?

**Q-D4 (selectors actually exist?).** EPIC D effort is reduced to 3.0 d assuming `PractitionerDetailsSelector` etc. exist. In the repo only `PRM_AddressSelector` is present. Can you confirm against the org which of `PractitionerDetailsSelector`, `PRM_UpdateDirectorySelector`, `PRM_NCPDP_Selector` exist? If they don't, EPIC D is under-estimated.

---

## E. Data integrity: idempotency & transaction boundary (HIGH)

**Q-E1 (idempotency on retry).** The async objects define **no External Id**, and the E-services do blind `insert`. Manual retry of a partially-succeeded child could therefore **duplicate** facility/network records. The TDD claims "idempotency via External-Id upserts," but none are defined. What is the actual idempotency mechanism for retried async work? Which fields are the upsert keys?

**Q-E2 (split-brain sync vs async).** The sync core commits (E1–E16) and then async creates the network records. If the async permanently fails (lands in DLQ and is never retried), the result is a **committed practitioner with no network membership**. Is that a valid interim state? What reconciles or alerts on practitioners whose async network creation never completed? (The finish notification fires, but nothing forces remediation.)

**Q-E3 (E1 must return PersonContactId).** E2/E5/E6/E7 all consume `params.practitionerId` (the PersonContact Id), but E1's documented response returns only `practitionerAccountId`/`caseId`/`caseManagerId`. For a Person Account, PersonContactId is only knowable after the Account insert (re-query). Will E1 explicitly return it? (Confirmed gap in Epic E Part 1.)

---

## F. Performance targets — are they grounded? (MEDIUM)

**Q-F1.** G3 sets IBC DML ≤ 12, Delegated DML ≤ 28, **SOQL ≤ 40**, CPU < 5000 ms, heap < 2 MB. The TDD's CL-10 says the legacy flow doc gives DML figures but **no SOQL baseline**, and calls "≤ 40" provisional. Are these thresholds derived from a measured legacy baseline, or are they aspirational? If un-baselined, G3 could pass/fail arbitrarily.

**Q-F2.** With address/facility/network offloaded to async, the sync DML drops — but how much SOQL do the in-service RecordType describes + EPIC D selector reads actually consume per submission? Has a thin POC measured this?

---

## G. Cutover & operations (MEDIUM)

**Q-G1 (hard cutover risk).** Rollout is a **hard cutover with no feature flag** (rollback = re-point the IP Remote Action). For a core provider-onboarding flow, is the business comfortable with no per-record/per-user gradual rollout? What's the rollback RTO if a defect surfaces post-cutover?

**Q-G2 (response parity).** F4 promises "byte-for-byte response parity" with the legacy IP (`FeatureConfigSetting`, `PractitionerScreenRecordIds`, etc.). Has the exact legacy response contract been captured as a fixture for the shadow-mode harness (G4)?

**Q-G3 (back-pressure & sweeper — promised but unbuilt).** TDD §6.3/§8 promise a Flex-Queue depth guard, per-chunk savepoint, auto-retry, and a stuck-job sweeper. Epic C builds **none** of these (manual-only retry, no sweeper, no back-pressure check in `invokeJob`). At peak the engine can exceed the 100 flex-queue cap and throw. Are these resiliency features in scope for v1 or explicitly deferred? (If deferred, the TDD should say so.)

**Q-G4 (CMDT vs Apex-constant config).** Retention, max-retries, and the per-process active flag were moved from `PRM_AsyncJobConfig__mdt` to Apex constants. That makes "disable a ProcessName during an incident" a redeploy. Should at least `PRM_Active__c` (kill-switch) stay on the CMDT?

---

## H. Schema / record-type confirmations (MEDIUM)

**Q-H1 (record-type DeveloperNames).** Confirm these exist with the exact dev names used: `PRM_FacilityNw`, `PRM_FacilityTx`, `PRM_FacilityPractitionerTxNw` (HealthcareFacilityNetwork); `PRM_AssistiveAid` (PRM_ProviderFeature__c); `PractitionerLocationAffiliation` / `PractitionerPracticeAffiliation` (HealthcarePractitionerFacility); and the IA flow record type (`PRM_PDMManualChange` vs `PRM_PractitionerParticipationRequest`) — the latter is Epic E's open CL-E2.

**Q-H2 (`ContactProfile`).** E10 writes `ContactProfile` (explicitly "not Contact"). Confirm `ContactProfile` is the correct API name and that the legacy DR writes it (could not verify in repo).

**Q-H3 (`PRM_AsyncJobConfig__mdt` field list).** The plan's Appendix §13 lists the CMDT fields without `PRM_ServiceClassName__c` — the very field the dispatcher does `Type.forName()` on (CL-12). Confirm the CMDT field set is `ProcessName / ServiceClassName / Mode / BatchSize / Sequence`.

---

## I. Estimate consistency (LOW)

**Q-I1.** EPIC E totals disagree across docs: TDD = 24.0 d, this plan = 23.0 d, Epic E (Part1 9.0 + Part2 13.5) = 22.5 d. EPIC C: this plan/TDD = 12.5 d, Epic C doc = 12.0 d. Which rollup is authoritative, and can the others be regenerated from it?

---

## Suggested triage order for the architect

1. **C4 (NetworkMember/HCFN target)** and **A2/B2 (Part 2 + async worker identity)** — these determine whether the async design as drawn is even the right one.
2. **C1–C3 (fan-out/chunking/throughput)** — the high-volume claim hinges on these.
3. **D1 (address subsystem reuse)** and **E1/E2 (idempotency, split-brain)** — data-integrity blockers.
4. Everything else can be resolved during the relevant EPIC.
