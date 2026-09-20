# Practice-to-Practitioner `EffectiveFrom` ← Oldest Active PPL — Deep-Dive Impact Analysis

> **Requirement**: Whenever a *Practitioner Practice Location (PPL)* is Termed or Reinstated, recompute and update `EffectiveFrom` on the *Practice-to-Practitioner (P2P)* record (same Group + Practitioner) to the **oldest `EffectiveFrom` of the remaining active PPLs** for that Group + Practitioner combination.

---

## 1. Data Model Verification (live QA query)

| Concept | Salesforce Object | Record Type Developer Name | Constant in `PRM_GlobalConstant` |
|---|---|---|---|
| Practice Location | `HealthcareFacility` | — | `SOBJECT_HCFacility` |
| **Practitioner Practice Location (PPL)** | `HealthcarePractitionerFacility` | `PRM_PractitionerLocationAffiliation` | `RECTYPEID_PLAFFILIATION` |
| **Practice to Practitioner (P2P)** | `HealthcarePractitionerFacility` | `PRM_PractitionerPracticeAffiliation` | `RECTYPEID_PRACTITIONERPL` / `HCPFPracticeToPracRec` |
| Admitting Privileges | `HealthcarePractitionerFacility` | `PRM_AdmittingPrivileges` | `RECTYPEID_ADMITTINGPRIVILEGES` |

**QA volumes (live)**:

| Record Type | Count |
|---|---|
| `PRM_PractitionerLocationAffiliation` (PPL) | 563,282 |
| `PRM_PractitionerPracticeAffiliation` (P2P) | 230,207 |
| `PRM_AdmittingPrivileges` | 268,333 |

**Confirmed model in QA** for a real Group + Practitioner (Delaware Family Eye Ctr LLC / Erwin Suh):

| Rec Type | HealthcareFacilityId | `EffectiveFrom` | `IsActive` |
|---|---|---|---|
| PPL | Omega Dr | **2002-11-15** ← oldest | ✓ |
| PPL | Centurian Dr 8060 | 2024-10-15 | ✓ |
| PPL | Centurian Dr 9000 | 2024-10-22 | ✓ |
| **P2P** | *(null)* | **2002-11-15** ← matches oldest PPL today | ✓ |

So today the P2P `EffectiveFrom` happens to equal the oldest PPL `EffectiveFrom` because that was the date it was first inserted. But **nothing in the code keeps these in sync after Termination or Reinstatement**, which is exactly the requirement gap.

**P2P record key facts**:
- `HealthcareFacilityId` is **null** on P2P (the unique key is `AccountId` + `PractitionerId`).
- Existing trigger logic already knows about this PPL-vs-P2P distinction (`PRM_HCPFTriggerHelper.handleConciergeRollup` lines 153-164 has explicit “PPL path: no HealthcareFacilityId — resolve via Account” branch).

---

## 2. Existing EffectiveFrom Behavior on P2P (Today)

I traced every place in the codebase that writes to `HealthcarePractitionerFacility.EffectiveFrom` for the P2P record type. Findings:

| Component | What it does today with P2P `EffectiveFrom` |
|---|---|
| `PRM_PracFacilityTriggerHandler.updatePrimaryFlagonExistingPPL` | Only writes **`EffectiveTo`** on P2P when last PPL on the Account is termed. **Never recomputes EffectiveFrom.** |
| `PRM_PDMUnlinkPractitioner.terminateNPIAndPracToPrac` | Writes `EffectiveTo`, `IsActive` on P2P. **Never writes EffectiveFrom.** |
| `PRM_CrossReferencePracticeLocation.terminatePracticeToPractitioner` | Writes `EffectiveTo` and only updates P2P if **all** PPLs are terminating (`existingFacilityIds.size() == terminatedfacilityIds.size()`). Keeps `EffectiveFrom` as-is. |
| `PRM_PracLocTermHelper.getPracticeToPractitionerProvChange` / `getVendorPracticeToPractitioner` | Writes `EffectiveTo`. Sets `EffectiveFrom = System.today()` only in the `PRM_IsErrorRecord__c == true` (rollback) branch. |
| `PRM_PractitionerTerminationBatchHelper.getVendorPracticeToPractitioner` / `getHCPFForPract` | Same — only `EffectiveTo`, never `EffectiveFrom`. |
| `PRM_ReinstateVendorAccountBatchHelper.getFacilityAndEntityId (cls_PracticeToPractitioner)` | Writes whatever `obj.EffectiveFrom` was passed in by the OmniScript / wrapper (a single user-entered date — not computed). |
| `PRM_AddNewLocationUtilityHelper.buildAffiliationForExistingFacility` + `insertPracticeAffiliationIfMissing` | Creates P2P **without setting `EffectiveFrom`** (relies on default/null). Cap=1 per Practitioner+Account. |
| `PRM_ManualUpdatesCrossRefBatchHelper` (Account Creation Cross-Reference batch) | Inserts P2P with `EffectiveFrom = effectiveDate` (the same date used for the whole new account). |
| `PRM_HCPFTriggerHelper.processAffCareCatEffectiveDates` | Cascades the *changed PPL’s* `EffectiveFrom` to its own `PRM_ProviderFeature__c` rows — does NOT touch the sibling P2P record. |

**Conclusion**: There is **no flow today that recomputes the P2P `EffectiveFrom` to the oldest active PPL**. Every termination/reinstate flow listed in your requirement has the same gap.

---

## 3. Trigger Reality Check (why a trigger-only fix is the cleanest single point of enforcement)

Every Term / Reinstate path ultimately writes to `HealthcarePractitionerFacility` (PPL rows) — via:

- `PRM_PracticeLocationTerminationBatch` → `update this.hcPractitionerFacility.values()` (line 259)
- `PRM_PractitionerTerminationBatchHelper` → `update` of PPL records
- `PRM_PDMUnlinkPractitioner` → `update as system uniqueHCPFRecsToUpdate;` (line 291)
- `PRM_ReinstateVendorAccountBatchHelper.updateFacilityAndItsRelatedData` → `update hcPracFacUpdate;`
- `PRM_CrossReferencePracticeLocation` → returns records to OmniScript that the IP DML-updates
- All OmniScripts that DML upsert HCPF rows via DataRaptors

The `PRM_PracFacility` trigger fires on **all** of these, calling `PRM_PracFacilityTriggerHandler.afterUpdate(...)` / `afterInsert(...)` / `afterDelete(...)`. That is the single seam where the new rule can be enforced uniformly without modifying 30+ OmniScripts / IPs / batches.

**Recommended primary fix**: add a new helper method (e.g., `PRM_HCPFTriggerHelper.recomputeP2PEffectiveFromForChangedPPLs(newItems, oldItems)`) and call it from `PRM_PracFacilityTriggerHandler.afterInsert` / `afterUpdate` / `afterDelete`.

---

## 4. Flow-by-Flow Impact Matrix

> **Legend**: ❌ = currently does not satisfy the requirement (writes only EffectiveTo, or skips P2P entirely). ⚠️ = partially does it (e.g. sets EffectiveFrom from a single passed value, not the oldest-active rule). ✓ = will get the fix for free if we put it in the trigger.

| # | Guided Flow | Final SObject DML | Today’s P2P EffectiveFrom Behavior | Impact | Fix Path |
|---|---|---|---|---|---|
| 1 | **Account Creation Cross-Reference** | `PRM_ManualUpdatesCrossRefBatchHelper.upsertRecords` inserts PPL + P2P together with same `effectiveDate` | P2P `EffectiveFrom = effectiveDate` (same as PPL). OK at creation, but no recompute on later edits. | ⚠️ Pass at creation; fails on later term/reinstate | Trigger fix covers later DML; no change needed here. |
| 2 | **PDM Manual Updates** (`PRM_PDMManualChanges_English_*`) | Multiple — UI lets users term/reinstate PPLs; calls `PRM_PracLocTermPDMService` / `PRM_PDMUnlinkPractitioner` | PPL `EffectiveFrom` / `EffectiveTo` updated; P2P `EffectiveFrom` not recomputed | ❌ | Trigger fix |
| 3 | **Unlink Practice Location from Practitioner** (`PRM_PDMUnlinkPracticeLocationHelper_Procedure_*` → `PRM_PDMUnlinkPractitioner.terminateNPIAndPracToPrac`) | Updates PPL.IsActive=false + EffectiveTo; updates P2P.EffectiveTo only | P2P `EffectiveFrom` unchanged | ❌ — this is the canonical bug | Trigger fix |
| 4 | **Link Practice Location from Practitioner** (`PRM_PDMLinkPracticeLocationHelper_Procedure_*`) | Inserts new active PPL; may also re-activate P2P | New PPL has fresh `EffectiveFrom`; existing P2P `EffectiveFrom` untouched. If new PPL has earlier date than current P2P EffectiveFrom, P2P stays wrong | ❌ on retro-link | Trigger fix (afterInsert path) |
| 5 | **Terminate COI** (Conflict of Interest) | Triggers Practitioner Term flow downstream → `PRM_PractitionerTerminationBatchHelper` | Same gap as #6/#9 | ❌ | Trigger fix |
| 6 | **Remove Practitioner from Practice Location** (`PRM_PDMUnlinkPractitioner.terminateNPIAndPracToPrac`) | Updates one PPL.IsActive=false + EffectiveTo | Same as #3 — P2P EffectiveFrom unchanged | ❌ | Trigger fix |
| 7 | **Cross-Reference** (during Initial Cred — `PRM_CrossReferencePracticeLocation.recordsEligibleForTermination`) | Only touches P2P if **all** PPLs are termed (returns to OmniScript). EffectiveFrom not recomputed; EffectiveTo set | ⚠️ — full-term path only; partial term silently skips P2P | ❌ on partial term | Trigger fix (covers both paths) |
| 8 | **Add Practitioner to Practice Location** (`PRM_AddNewLocationUtilityHelper`) | Inserts new PPL + may insert P2P; P2P inserted with no `EffectiveFrom` (defaulted) | If group already has P2P, no change. If new P2P created, `EffectiveFrom` is left null | ⚠️ | Trigger fix (afterInsert PPL recompute) + small Apex fix to set P2P `EffectiveFrom` to inserted PPL `EffectiveFrom` at create time |
| 9 | **Practitioner Termination – PPL is Termed** (`PRM_PractitionerTerminationBatchHelper.getVendorPracticeToPractitioner`) | Sets P2P EffectiveTo only | ❌ | Trigger fix |
| 10 | **Practice Location Termination** (`PRM_PracticeLocationTerminationBatch.execute`) | Bulk updates PPLs for the Facility; does not touch P2P EffectiveFrom (the trigger handler currently tries when only 1 PPL remains, but only EffectiveTo, not EffectiveFrom) | ❌ | Trigger fix |
| 11 | **Provider Change Request** (`PRM_ProviderChangePDATerminate_*`, `PRM_ProviderChangePDAUpdates_*`, `PRM_PracLocTermHelper.getPracticeToPractitionerProvChange`) | Sets EffectiveTo on P2P; never EffectiveFrom | ❌ | Trigger fix |
| 12 | **Remove Practitioner** (in PDA / vendor term context) | Routes via `PRM_PDMUnlinkPractitioner` | Same as #3/#6 | ❌ | Trigger fix |
| 13 | **Add Practitioner** (via OmniScripts that call `PRM_AddPractitionerPCFPDA_Procedure_1`) | Inserts PPL; may insert P2P if first PPL on the Group | Inserted P2P has no `EffectiveFrom` set; subsequent retro-adds break invariant | ⚠️ | Trigger fix + ensure new P2P creation seeds `EffectiveFrom` to inserted PPL `EffectiveFrom` |
| 14 | **Practice Location Reinstate** (`PRM_ReinstateVendorAccountBatchHelper.updateFacilityAndItsRelatedData` + `cls_PracticeToPractitioner`) | Sets P2P EffectiveFrom = `obj.EffectiveFrom` (a single user-entered date passed in the wrapper) | ⚠️ — uses whatever the OmniScript sent, not the oldest-active rule. Per Scenario 2 step 5, the reinstate IP must set EffectiveFrom = retro PPL EffectiveFrom (11/20/2025). The trigger fix gives correct value regardless of what OS passes. | ❌ on retro reinstate where the reinstated PPL’s date precedes the prior P2P EffectiveFrom | Trigger fix (computes it correctly) — and remove the manual override in `cls_PracticeToPractitioner` so the trigger is the single source of truth |
| 15 | **Practitioner Reinstate** (`PRM_PractitionerReinstateVendorUpdate_Procedure_*` → `PRM_PractitionerActivationBatchHelper`) | Re-activates PPL and P2P; passes a single EffectiveFrom value to P2P | ⚠️ | Trigger fix |
| 16 | **Account Reinstate (after changes on #1369999)** | After Account reinstate, all PPLs become active again; P2P also reinstated by the batch helper | ⚠️ | Trigger fix |

---

## 5. Concrete Validation Against Your Two Scenarios

### Scenario 1 (single P2P with one PPL having the same date)

Initial state (after Step 1):

| Record | EffectiveFrom | IsActive |
|---|---|---|
| PPL #1 | 1/1/2026 | ✓ |
| PPL #2 | 12/1/2025 | ✓ |
| PPL #3 | 11/1/2025 (oldest) | ✓ |
| P2P    | 11/1/2025 | ✓ |

After action 2a / 2b / 2c (terminate PPL #3):
- Current code path → P2P `EffectiveTo` untouched (or set per the action), `EffectiveFrom` stays at 11/1/2025. ❌
- Required → `EffectiveFrom` should now equal `MIN(EffectiveFrom WHERE IsActive=true)` of remaining PPLs = **12/1/2025**. ✓

### Scenario 2 (Reinstate path with retroactive new date)

After Step 4a/4b (PPL #3 reinstated with EffectiveFrom 11/20/2025), the oldest active PPL `EffectiveFrom` is now **11/20/2025**, which is earlier than the current P2P `EffectiveFrom` of 12/1/2025. So the trigger fix must also handle the case where the oldest moves **earlier** (insert/reactivate flow), not just later (term flow).

The implementation in §6 below handles both directions.

---

## 6. Recommended Fix — Centralized Trigger-Level Recompute (Large-Volume Hardened)

> Sized for the actual QA worst-case: a single Practice Location with **1,579 active PPLs** (`HealthcareFacilityId = 0klUW0000001WhoYAE`) being termed in one DML, plus future growth headroom. See the companion document [`P2P_EffectiveFrom_Fix_LargeVolume_Audit.md`](./P2P_EffectiveFrom_Fix_LargeVolume_Audit.md) for the full audit and the data behind every limit cited below.

### 6.1 Volume Targets (governor budget at the worst case)

| Trigger fire payload | What invokes it | Frequency |
|---|---|---|
| **1,579 PPLs in one DML** | `PRM_PracticeLocationTerminationBatch.execute` for the 1,579-practitioner Practice Location | Possible today |
| 600 PPLs in one DML | `PRM_AccountTerminationBatch.execute` chunk=3 across an avg-sized account | Common |
| ≤ 100 PPLs in one DML | OmniScript paths (`PRM_PDMUnlinkPractitioner`, manual updates) | Frequent |
| **Pathological**: 10,000 PPLs in one DML | Data Loader / Bulk API push | Rare but must not crash |

Governor wall the helper is designed against:

| Limit | Budget consumed by helper in worst case (1,579 PPLs) |
|---|---|
| SOQL queries (async) | 8 of 200 — 96 % headroom |
| Aggregate `GROUP BY` rows per query | ≤ 500 (chunked) — never hits the 2,000-group cliff |
| SOQL rows / tx | ~3,500 of 50,000 |
| DML statements | ≤ 8 of 150 |
| DML rows / tx | 1,579 of 10,000 |
| Heap | ~3 MB of 12 MB (async) |
| Apex CPU | ~250 ms of 60,000 ms (async) |
| Trigger recursion | Self-recursion blocked by recordType filter; cross-handler cascade short-circuited by guard flag (see §6.4) |

### 6.2 Design Principles

1. **Chunk every SOQL to ≤ 500 keys** — keeps `GROUP BY` under the 2,000-row hard cap and keeps IN-lists below Salesforce selectivity heuristics.
2. **Chunk every DML to ≤ 200 rows** — small enough that even if the resulting trigger re-fire spawned other handler work, that work fits within per-trigger limits.
3. **Idempotent** — re-running with the same inputs produces no DML (the helper is fired multiple times across chained batches like `PRM_PracticeLocationTerminationBatch` → `PRM_PractitionerTermForFacilityBatch`; second pass must be cheap).
4. **Single re-entry guard for the whole trigger** — when our helper's DML re-fires the trigger and every row is a P2P, the trigger short-circuits at the top so no other handler does cascade work.
5. **Feature-flagged** — a `PRM_FeatureConfiguration__mdt` toggle (`P2PEffectiveFromAutoSync`) lets ops disable the helper instantly in production if needed, without a deploy.
6. **Safe by default** — never push P2P EffectiveFrom past EffectiveTo; never touch a P2P when no remaining PPL is active (the existing `EffectiveTo` cascade handles termination separately); skip P2Ps in `PRM_IsErrorRecord__c = true` state.
7. **Synchronous, not async** — the largest realistic case (1,579 records) fits comfortably in sync trigger limits with chunking. Async (Queueable/PE) was rejected because OmniScripts read the P2P EffectiveFrom in the same transaction; staleness is unacceptable.

### 6.3 Helper Implementation — `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL`

```apex
public with sharing class PRM_HCPFTriggerHelper {

    /* ─────────────────────────────────────────────────────────────────────
     *  Public re-entry / cross-handler flag.  TRUE while our helper is
     *  performing its own DML on P2P rows.  PRM_PracFacilityTriggerHandler
     *  inspects this flag at the very top of afterInsert/Update/Delete and
     *  exits early when every Trigger.new row is a P2P — neutralising the
     *  full re-fire cascade (updateAccountPNC, futureDatedProcessing,
     *  handleConciergeRollup) for our own DML.
     * ───────────────────────────────────────────────────────────────────── */
    @TestVisible public static Boolean isP2PRecomputeInProgress = false;

    /* Chunk sizes derived from §6.1 governor analysis. Adjust only with care. */
    @TestVisible static Integer SOQL_CHUNK = 500;   // ≤2K aggregate-group cap, IN-list safe
    @TestVisible static Integer DML_CHUNK  = 200;   // standard Salesforce DML chunk

    /* ─────────────────────────────────────────────────────────────────────
     *  syncP2PEffectiveFromOldestActivePPL
     *  Single entry point. Wired from PRM_PracFacilityTriggerHandler
     *  afterInsert (oldMap=null, isDelete=false),
     *  afterUpdate (oldMap=trigger.oldMap, isDelete=false),
     *  afterDelete (oldMap=null, isDelete=true).
     * ───────────────────────────────────────────────────────────────────── */
    public static void syncP2PEffectiveFromOldestActivePPL(
            List<HealthcarePractitionerFacility> changedList,
            Map<Id, HealthcarePractitionerFacility> oldMap,
            Boolean isDelete) {

        // Re-entry / feature-flag short-circuits
        if (isP2PRecomputeInProgress) return;
        if (changedList == null || changedList.isEmpty()) return;
        if (!isFeatureEnabled()) return;

        try {
            Id pplRtId = PRM_GlobalConstant.RECTYPEID_PLAFFILIATION;
            Id p2pRtId = PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL;

            // ── Step 1. Collect impacted (AccountId, PractitionerId) keys.
            //    We only react to PPL changes; P2P rows in the trigger payload
            //    (e.g., the same DML that updated both) never cause recompute.
            Set<String> impactedKeys = collectImpactedKeys(changedList, oldMap, isDelete, pplRtId);
            if (impactedKeys.isEmpty()) return;

            // ── Step 2. For each impacted key, get MIN(EffectiveFrom) of
            //    remaining active PPLs (chunked SOQL).
            Map<String, Date> keyToOldestEffFrom = queryOldestActivePPLEffectiveFrom(
                impactedKeys, pplRtId);

            // ── Step 3. Load matching P2P rows (chunked SOQL).
            List<HealthcarePractitionerFacility> p2ps = queryP2PRows(impactedKeys, p2pRtId);
            if (p2ps.isEmpty()) return;

            // ── Step 4. Compute deltas; only update P2Ps whose EffectiveFrom is wrong.
            List<HealthcarePractitionerFacility> toUpdate = buildP2PUpdateList(
                p2ps, keyToOldestEffFrom);
            if (toUpdate.isEmpty()) return;

            // ── Step 5. DML in 200-row chunks, with re-entry guard set so the
            //    cascading handlers can short-circuit (see §6.4).
            isP2PRecomputeInProgress = true;
            try {
                for (Integer i = 0; i < toUpdate.size(); i += DML_CHUNK) {
                    Integer end = Math.min(i + DML_CHUNK, toUpdate.size());
                    List<HealthcarePractitionerFacility> slice =
                        new List<HealthcarePractitionerFacility>();
                    for (Integer j = i; j < end; j++) slice.add(toUpdate.get(j));
                    update slice;
                }
            } finally {
                isP2PRecomputeInProgress = false;
            }
        } catch (Exception ex) {
            // Belt-and-suspenders: never let this helper take down the
            // parent termination flow.  Log and continue.
            PRM_ExceptionLogger.logException(
                'PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL',
                '', 'Error', ex.getStackTraceString(), ex.getMessage(),
                ex.getTypeName(), ex.getLineNumber(), '',
                ex.getMessage(), 'Salesforce', '', '');
            // Ensure guard is cleared on uncaught exception in DML inside try.
            isP2PRecomputeInProgress = false;
        }
    }

    /* ───────────── Step 1: change detection (PPL rows only) ───────────── */
    private static Set<String> collectImpactedKeys(
            List<HealthcarePractitionerFacility> changedList,
            Map<Id, HealthcarePractitionerFacility> oldMap,
            Boolean isDelete,
            Id pplRtId) {
        Set<String> keys = new Set<String>();
        for (HealthcarePractitionerFacility n : changedList) {
            if (n.RecordTypeId != pplRtId) continue;
            if (n.AccountId == null || n.PractitionerId == null) continue;

            HealthcarePractitionerFacility o =
                (oldMap != null && !isDelete) ? oldMap.get(n.Id) : null;
            Boolean changed = isDelete
                || (o == null)
                || n.IsActive             != o.IsActive
                || n.EffectiveFrom        != o.EffectiveFrom
                || n.EffectiveTo          != o.EffectiveTo
                || n.PRM_IsErrorRecord__c != o.PRM_IsErrorRecord__c;
            if (!changed) continue;

            keys.add(n.AccountId + '|' + n.PractitionerId);
            // If the PPL was moved (rare but possible via PDM Manual Update),
            // recompute both the old and new groupings.
            if (o != null
                && (o.AccountId != n.AccountId || o.PractitionerId != n.PractitionerId)) {
                keys.add(o.AccountId + '|' + o.PractitionerId);
            }
        }
        return keys;
    }

    /* ───────────── Step 2: aggregate MIN(EffectiveFrom) — chunked ─────── */
    private static Map<String, Date> queryOldestActivePPLEffectiveFrom(
            Set<String> impactedKeys, Id pplRtId) {
        Map<String, Date> result = new Map<String, Date>();
        List<String> keyList = new List<String>(impactedKeys);

        for (Integer i = 0; i < keyList.size(); i += SOQL_CHUNK) {
            Integer end = Math.min(i + SOQL_CHUNK, keyList.size());
            Set<Id> acctIds = new Set<Id>();
            Set<Id> pracIds = new Set<Id>();
            for (Integer j = i; j < end; j++) {
                List<String> parts = keyList.get(j).split('\\|');
                acctIds.add(parts[0]);
                pracIds.add(parts[1]);
            }
            for (AggregateResult ar : [
                SELECT AccountId acc, PractitionerId prac, MIN(EffectiveFrom) minEFF
                FROM   HealthcarePractitionerFacility
                WHERE  RecordTypeId        = :pplRtId
                  AND  IsActive            = true
                  AND  PRM_IsErrorRecord__c = false
                  AND  AccountId          IN :acctIds
                  AND  PractitionerId     IN :pracIds
                GROUP BY AccountId, PractitionerId
            ]) {
                String key = ((Id)ar.get('acc')) + '|' + ((Id)ar.get('prac'));
                // We over-fetch (we filter by Account-set AND Practitioner-set,
                // not the exact pairs), so post-filter by impactedKeys.
                if (impactedKeys.contains(key)) {
                    result.put(key, (Date)ar.get('minEFF'));
                }
            }
        }
        return result;
    }

    /* ───────────── Step 3: load matching P2P rows — chunked ───────────── */
    private static List<HealthcarePractitionerFacility> queryP2PRows(
            Set<String> impactedKeys, Id p2pRtId) {
        List<HealthcarePractitionerFacility> result =
            new List<HealthcarePractitionerFacility>();
        List<String> keyList = new List<String>(impactedKeys);

        for (Integer i = 0; i < keyList.size(); i += SOQL_CHUNK) {
            Integer end = Math.min(i + SOQL_CHUNK, keyList.size());
            Set<Id> acctIds = new Set<Id>();
            Set<Id> pracIds = new Set<Id>();
            for (Integer j = i; j < end; j++) {
                List<String> parts = keyList.get(j).split('\\|');
                acctIds.add(parts[0]);
                pracIds.add(parts[1]);
            }
            // Post-filter handled in buildP2PUpdateList using impactedKeys.
            result.addAll([
                SELECT Id, AccountId, PractitionerId,
                       EffectiveFrom, EffectiveTo, IsActive, PRM_IsErrorRecord__c
                FROM   HealthcarePractitionerFacility
                WHERE  RecordTypeId    = :p2pRtId
                  AND  AccountId      IN :acctIds
                  AND  PractitionerId IN :pracIds
            ]);
        }
        return result;
    }

    /* ───────────── Step 4: delta computation with guardrails ──────────── */
    private static List<HealthcarePractitionerFacility> buildP2PUpdateList(
            List<HealthcarePractitionerFacility> p2ps,
            Map<String, Date> keyToOldestEffFrom) {

        List<HealthcarePractitionerFacility> toUpdate =
            new List<HealthcarePractitionerFacility>();
        Date today = Date.today();
        for (HealthcarePractitionerFacility p2p : p2ps) {
            String key = p2p.AccountId + '|' + p2p.PractitionerId;
            // No remaining active PPL → leave P2P EffectiveFrom alone (the
            // EffectiveTo cascade in updatePrimaryFlagonExistingPPL handles
            // last-PPL termination separately).
            Date newEffFrom = keyToOldestEffFrom.get(key);
            if (newEffFrom == null)                       continue;
            if (p2p.EffectiveFrom == newEffFrom)          continue;
            // Never push EffectiveFrom past EffectiveTo.
            if (p2p.EffectiveTo != null
                && newEffFrom > p2p.EffectiveTo)          continue;
            // Don't touch a P2P that's already in error state.
            if (p2p.PRM_IsErrorRecord__c == true)         continue;

            HealthcarePractitionerFacility u =
                new HealthcarePractitionerFacility(Id = p2p.Id);
            u.EffectiveFrom = newEffFrom;
            u.IsActive      = (newEffFrom <= today)
                              && (p2p.EffectiveTo == null || p2p.EffectiveTo > today);
            toUpdate.add(u);
        }
        return toUpdate;
    }

    /* ───────────── Feature flag ─────────────────────────────────────────
     *  Backed by a new Checkbox field on the existing custom setting
     *  PRM_FeatureConfigurationSettings__c:
     *      PRM_EnableP2PEffectiveFromAutoSync__c
     *  Reuses the existing PRM_Utility.fetchFeatureConfigSettings('Default', ...)
     *  pattern (already used by other PRM_* helpers).
     *  Default false during initial rollout → flip true after backfill
     *  completes successfully.
     * ───────────────────────────────────────────────────────────────────── */
    @TestVisible static Boolean featureEnabledOverride = null;  // tests can set
    private static Boolean isFeatureEnabled() {
        if (featureEnabledOverride != null) return featureEnabledOverride;
        try {
            return PRM_Utility.fetchFeatureConfigSettings(
                'Default', 'PRM_EnableP2PEffectiveFromAutoSync__c');
        } catch (Exception ignored) {
            // No custom-setting row in this org → off by default.
            return false;
        }
    }

    /* Used by PRM_PracFacilityTriggerHandler's top-of-trigger short-circuit. */
    public static Boolean allRowsAreP2P(List<HealthcarePractitionerFacility> rows) {
        if (rows == null || rows.isEmpty()) return false;
        Id p2pRt = PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL;
        for (HealthcarePractitionerFacility r : rows) {
            if (r.RecordTypeId != p2pRt) return false;
        }
        return true;
    }
}
```

### 6.4 Wire-up in `PRM_PracFacilityTriggerHandler` (single top-of-trigger short-circuit)

The cleanest cascade-suppression strategy is a **single guard at the top of each trigger method** rather than per-handler short-circuits. When our helper's DML re-fires the trigger and every row is a P2P, no other handler needs to run (P2P rows are filtered out by every existing handler downstream anyway — this just saves the wasted iterations and the unnecessary `updateAccountPNC` / `futureDatedProcessing` / `handleConciergeRollup` work that DOES run on P2P refire today).

```apex
public override void afterInsert(Map<Id, SObject> newItems) {
    // ── NEW ──  short-circuit when our own DML is re-firing the trigger
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && PRM_HCPFTriggerHelper.allRowsAreP2P(
            (List<HealthcarePractitionerFacility>)newItems.values())) {
        return;
    }

    updateAccountPNC();
    updateActiveLocationsCount();
    updatePrimaryFlagonExistingPPL(newItems, null);
    futureDatedProcessing((List<HealthcarePractitionerFacility>)newItems.values(), null);
    PRM_HCPFTriggerHelper.handleConciergeRollup(newItems, null);

    // ── NEW ──  S-XXXXXXX  P2P EffectiveFrom auto-sync
    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)newItems.values(), null, false);
}

public override void afterUpdate(Map<Id, SObject> newItems, Map<Id, SObject> oldItems) {
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && PRM_HCPFTriggerHelper.allRowsAreP2P(
            (List<HealthcarePractitionerFacility>)newItems.values())) {
        return;
    }

    updateAccountPNC();
    updateActiveLocationsCount();
    PRM_GlobalConstant.byPassVal = PRM_GlobalConstant.BOOL_FALSE;
    updatePrimaryFlagonExistingPPL(newItems, oldItems);
    futureDatedProcessing((List<HealthcarePractitionerFacility>)newItems.values(),
                          (Map<Id, HealthcarePractitionerFacility>)oldItems);
    PRM_HCPFTriggerHelper.processAffCareCatEffectiveDates(
        (List<HealthcarePractitionerFacility>)newItems.values(),
        (Map<Id, HealthcarePractitionerFacility>)oldItems);
    PRM_HCPFTriggerHelper.handleConciergeRollup(newItems, oldItems);

    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)newItems.values(),
        (Map<Id, HealthcarePractitionerFacility>)oldItems,
        false);
}

public override void afterDelete(Map<Id, SObject> oldItems) {
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && PRM_HCPFTriggerHelper.allRowsAreP2P(
            (List<HealthcarePractitionerFacility>)oldItems.values())) {
        return;
    }

    if (!PRM_GlobalConstant.byPassVal) updateActiveLocationsCount();
    PRM_HCPFTriggerHelper.handleConciergeRollup(null, oldItems);

    // Pass oldMap=null + isDelete=true. The helper marks every PPL in oldItems
    // as "impacted" (this fixes the original bug where passing the same list
    // as both new and old made `changed` evaluate to false and skipped the
    // recompute entirely).
    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)oldItems.values(), null, true);
}
```

### 6.5 Per-Scenario Volume Trace (worst-case walkthroughs)

| Real-world flow | Trigger.new size | impactedKeys (`A\|P`) | Aggregate SOQL chunks (≤500) | P2P SOQL chunks (≤500) | DML chunks (≤200) | Total SOQL/DML | Verdict |
|---|---|---|---|---|---|---|---|
| **PL Term, 1,579-practitioner PL** (`PRM_PracticeLocationTerminationBatch`) | 1,579 PPLs (all same Account) | 1,579 | 4 | 4 | 0–8 (depending on actual deltas) | 8 SOQL + ≤ 8 DML | ✅ |
| Account Term chunk=3 (~600 PPLs) | 600 | 600 | 2 | 2 | 0–3 DML | 4 SOQL + ≤ 3 DML | ✅ |
| OS unlink (≤ 100 PPLs) | ≤ 100 | ≤ 100 | 1 | 1 | 1 | 2 SOQL + 1 DML | ✅ |
| Future-Dated chunk=9 (date arrives) | ≤ 9 | ≤ 9 | 1 | 1 | 1 | 2 SOQL + 1 DML | ✅ |
| Data Loader bulk 10K PPL update | 10,000 | up to 10,000 | 20 | 20 | 50 | 40 SOQL + 50 DML | ✅ within DML row ceiling |
| **PL Term termed-all path** (all 1,579 PPLs IsActive=false simultaneously) | 1,579 PPLs | 1,579 | 4 (returns 0 active groups) | 4 | **0 DML** — `keyToOldestEffFrom.get(key) == null` → skip every P2P | 8 SOQL + 0 DML | ✅ correct: no active PPL means P2P EffectiveFrom is untouched (existing EffectiveTo cascade handles termination) |
| Chained `PRM_PractitionerTermForFacilityBatch` re-fire on already-correct P2Ps | ≤ 104 PPLs per chunk | ≤ 104 | 1 | 1 | **0 DML** (idempotent) | 2 SOQL, 0 DML per chunk | ✅ cheap re-fire |

Across the helper's lifetime in a single 1,579-PPL PL termination workflow (parent batch + 1,579 chained practitioner-term chunks), cumulative cost ≈ **8 SOQL + 8 DML in the parent execute**, then **2 SOQL + 0 DML in each of 1,579 chained chunks** = ~3,166 SOQL total across **separate transactions** (each transaction stays well under limits).

### 6.6 Why Synchronous (not Queueable / Platform Event)

Async dispatch was considered. Rejected because:

1. **Sync fits**: the worst case (1,579 records) uses ≤ 10 % of every async governor and ≤ 50 % of sync governors with chunking.
2. **OmniScripts read P2P EffectiveFrom in the same transaction** (e.g., Reinstate review screens). A Queueable would leave them seeing stale data until the next session refresh.
3. **Queueable per trigger = chain hell**. `PRM_PracticeLocationTerminationBatch` → 1,579 chained Practitioner term chunks would each enqueue a Queueable, and Salesforce caps chained Queueables at 50.
4. **Async testing is harder**. `Test.startTest()/stopTest()` works, but multi-step chained tests (with 8 listed flows to cover) get painful.

Async remains a fallback option ONLY if a future Bulk API operation needs to update > 10 K HCPFs in one DML — at which point the bulk caller is responsible for either chunking the load or switching the helper to async. Both options can be added later without API change.

### 6.7 Feature Flag & Rollout

Add a new Checkbox field on the existing custom setting `PRM_FeatureConfigurationSettings__c`:

| Field API name | Type | Default |
|---|---|---|
| `PRM_EnableP2PEffectiveFromAutoSync__c` | Checkbox | `false` |

The existing `Default` setting record (used by `PRM_Utility.fetchFeatureConfigSettings('Default', …)`) gets the flag flipped via `Setup → Custom Settings → PRM Feature Configuration Settings`. No code change required to flip — ops can disable instantly in production.

Roll-out steps:
1. Deploy code (helper + trigger wire-up + new custom-setting field). Field initial value is `false` everywhere.
2. Run backfill batch (§8). The backfill explicitly **does not** call the trigger helper — it inlines its own recompute logic and suppresses the trigger via `isP2PRecomputeInProgress = true` around DML. So backfill works regardless of the flag.
3. Spot-check backfill results in QA / sandbox using the `PRM_AsyncProcess__c` finish-log row.
4. In QA: set `PRM_EnableP2PEffectiveFromAutoSync__c = true` on the `Default` setting record. Smoke-test the §9.1 scenarios live.
5. Monitor `PRM_ExceptionLogger` for any failures over the next 48 hours.
6. Promote to production: deploy field + code, run backfill, flip the toggle.
7. After 1 week of clean ops in production, proceed with §7 secondary cleanup (retiring redundant manual `EffectiveFrom` writes).

---

## 7. Secondary Cleanup (Phase 2, after trigger is verified)

The following helpers currently write `EffectiveFrom` on P2P themselves. Once the trigger is shipped and `PRM_Enabled__c=true`, these manual writes become redundant — the trigger will overwrite them with the correct value anyway. They can be retired to remove confusion:

| File | Lines | What to do | Risk if delayed |
|---|---|---|---|
| `PRM_ReinstateVendorAccountBatchHelper.cls` lines 327-335 (`cls_PracticeToPractitioner`) | Sets P2P `EffectiveFrom = obj.EffectiveFrom` from a single user-entered value | Remove the assignment — let the trigger compute it from active PPLs | None — trigger will overwrite |
| `PRM_AddNewLocationUtilityHelper.buildAffiliationForExistingFacility` | Inserts P2P with no explicit `EffectiveFrom` (defaults to null) | Set `EffectiveFrom` explicitly to the staged PPL's `EffectiveFrom` at insert time | None — trigger fires on the PPL afterInsert and recomputes |
| `PRM_ManualUpdatesCrossRefBatchHelper.cls` line 175 | Inserts P2P with `EffectiveFrom = effectiveDate` at creation | Leave as-is — at creation this IS the oldest active PPL date | N/A |

---

## 8. Data-Fix Backfill (one-time, hardened for 230 K rows)

```apex
/**
 * @description One-time backfill that walks every existing P2P row and
 *              corrects its EffectiveFrom to MIN(EffectiveFrom) of remaining
 *              active PPLs for the same (Account, Practitioner).
 *
 * Runtime expectations on QA (230,207 rows, chunk=200):
 *   - 1,150 batch executions
 *   - ≈ 500 ms / chunk → ~10 minutes total
 *   - 2 SOQL + 1 DML / chunk
 *
 * Use Database.executeBatch(new PRM_BackfillP2PEffectiveFromBatch(true), 200)
 * to run in DRY-RUN mode first.  The finish() method writes a row to
 * PRM_AsyncProcess__c with the would-have-updated count (ItemsProcessed)
 * and any failures (ItemsFailed) — see finish() below.
 */
global class PRM_BackfillP2PEffectiveFromBatch
        implements Database.Batchable<SObject>, Database.Stateful {

    private Boolean dryRun;
    private Integer recordsScanned  = 0;
    private Integer recordsToUpdate = 0;
    private Integer recordsUpdated  = 0;
    private Integer recordsFailed   = 0;

    global PRM_BackfillP2PEffectiveFromBatch(Boolean dryRun) {
        this.dryRun = dryRun != null && dryRun;
    }

    global Database.QueryLocator start(Database.BatchableContext bc){
        // We scan ALL P2P rows (including inactive) so backfill is complete.
        // The helper itself skips IsActive=true/false based on per-row state.
        return Database.getQueryLocator(
            'SELECT Id, AccountId, PractitionerId, EffectiveFrom, EffectiveTo, ' +
            '       IsActive, PRM_IsErrorRecord__c '                            +
            'FROM   HealthcarePractitionerFacility '                            +
            'WHERE  RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL '+
            '  AND  PRM_IsErrorRecord__c = false');
    }

    global void execute(Database.BatchableContext bc,
                        List<HealthcarePractitionerFacility> scope){
        recordsScanned += scope.size();

        // Build the (Account, Practitioner) key set from the scope.
        Set<Id> acctIds = new Set<Id>();
        Set<Id> pracIds = new Set<Id>();
        Set<String> keys = new Set<String>();
        for (HealthcarePractitionerFacility p2p : scope) {
            if (p2p.AccountId == null || p2p.PractitionerId == null) continue;
            acctIds.add(p2p.AccountId);
            pracIds.add(p2p.PractitionerId);
            keys.add(p2p.AccountId + '|' + p2p.PractitionerId);
        }

        // Aggregate MIN(EffectiveFrom) of active PPLs.  Scope is 200 → keys
        // ≤ 200 → guaranteed under the 2,000-group cap with no chunking needed.
        Map<String, Date> oldest = new Map<String, Date>();
        for (AggregateResult ar : [
            SELECT AccountId acc, PractitionerId prac, MIN(EffectiveFrom) minEFF
            FROM   HealthcarePractitionerFacility
            WHERE  RecordTypeId        = :PRM_GlobalConstant.RECTYPEID_PLAFFILIATION
              AND  IsActive            = true
              AND  PRM_IsErrorRecord__c = false
              AND  AccountId          IN :acctIds
              AND  PractitionerId     IN :pracIds
            GROUP BY AccountId, PractitionerId
        ]) {
            String key = ((Id)ar.get('acc')) + '|' + ((Id)ar.get('prac'));
            if (keys.contains(key)) oldest.put(key, (Date)ar.get('minEFF'));
        }

        // Compute deltas using the exact same logic as the trigger helper.
        Date today = Date.today();
        List<HealthcarePractitionerFacility> toUpdate =
            new List<HealthcarePractitionerFacility>();
        for (HealthcarePractitionerFacility p2p : scope) {
            String key = p2p.AccountId + '|' + p2p.PractitionerId;
            Date newEffFrom = oldest.get(key);
            if (newEffFrom == null) continue;
            if (p2p.EffectiveFrom == newEffFrom) continue;
            if (p2p.EffectiveTo != null && newEffFrom > p2p.EffectiveTo) continue;
            if (p2p.PRM_IsErrorRecord__c == true) continue;

            HealthcarePractitionerFacility u =
                new HealthcarePractitionerFacility(Id = p2p.Id);
            u.EffectiveFrom = newEffFrom;
            u.IsActive      = (newEffFrom <= today)
                              && (p2p.EffectiveTo == null || p2p.EffectiveTo > today);
            toUpdate.add(u);
        }
        recordsToUpdate += toUpdate.size();

        if (dryRun || toUpdate.isEmpty()) return;

        // Suppress trigger cascade — backfill is its own pass; we don't want
        // the helper to fire from inside our own update.
        PRM_HCPFTriggerHelper.isP2PRecomputeInProgress = true;
        try {
            Database.SaveResult[] results = Database.update(toUpdate, false);
            for (Database.SaveResult sr : results) {
                if (sr.isSuccess()) recordsUpdated++;
                else                recordsFailed++;
            }
        } finally {
            PRM_HCPFTriggerHelper.isP2PRecomputeInProgress = false;
        }
    }

    global void finish(Database.BatchableContext bc){
        // PRM_AsyncProcess__c already exposes ItemsProcessed / ItemsFailed.
        // ItemsProcessed = total rows we touched (DML succeeded);
        // ItemsFailed    = rows whose DML failed during the run.
        // In dry-run mode we record the would-have-updated count under
        // ItemsProcessed and tag the SubType so it's distinguishable.
        PRM_AsyncProcess__c log = new PRM_AsyncProcess__c(
            PRM_Type__c           = 'Backfill',
            PRM_SubType__c        = dryRun ? 'P2PEffectiveFromBackfill_DryRun'
                                           : 'P2PEffectiveFromBackfill',
            PRM_StartTime__c      = DateTime.now(),
            PRM_EndTime__c        = DateTime.now(),
            PRM_Status__c         = PRM_GlobalConstant.PROCESS_FINISHED,
            PRM_ItemsProcessed__c = dryRun ? recordsToUpdate : recordsUpdated,
            PRM_ItemsFailed__c    = recordsFailed
        );
        insert log;
    }
}
```

**Order of operations**:

1. Deploy code with feature flag `Enabled=false`.
2. `Database.executeBatch(new PRM_BackfillP2PEffectiveFromBatch(true), 200);` — DRY RUN. Inspect `PRM_AsyncProcess__c.PRM_RecordsUpdated__c` to gauge data drift.
3. Optional: pull a sample of the proposed updates (anonymous Apex query against the dry-run scope) and review with business.
4. `Database.executeBatch(new PRM_BackfillP2PEffectiveFromBatch(false), 200);` — real run.
5. Flip the feature flag to `Enabled=true` to turn on the live trigger logic going forward.

---

## 9. Test Plan (expanded for large-volume coverage)

Augment `PRM_PracFacilityTriggerHandlerTest` (and create `PRM_HCPFTriggerHelperTest` if it doesn't exist):

### 9.1 Functional correctness tests

1. **Scenario 1**: 3 PPLs (11/1, 12/1, 1/1) + 1 P2P (11/1). Term the 11/1 PPL → assert P2P.EffectiveFrom = 12/1.
2. **Scenario 2 retro re-add**: Same setup, then re-add 11/20 PPL → assert P2P.EffectiveFrom = 11/20.
3. **Scenario 2 reinstate**: Term the 11/1 PPL, then reinstate with EffectiveFrom=11/20 → assert P2P.EffectiveFrom = 11/20.
4. **No remaining active PPLs**: term the only PPL → assert P2P.EffectiveFrom NOT changed.
5. **Account Reinstate (#1369999)**: end-to-end through `PRM_ReinstateVendorAccountBatch` → assert P2P.EffectiveFrom = MIN(active PPLs post-reinstate).

### 9.2 Guardrail tests

6. **EffectiveFrom > EffectiveTo blocked**: try a recompute that would push past P2P.EffectiveTo → assert no DML.
7. **PRM_IsErrorRecord__c=true P2P untouched**: try a recompute on an error-state P2P → assert no DML.
8. **Feature flag off**: `featureEnabledOverride = false` → helper returns immediately; no SOQL / DML consumed.
9. **Recursion guard**: set `isP2PRecomputeInProgress = true`, fire trigger → helper returns immediately.
10. **afterDelete recompute**: delete the oldest active PPL → assert P2P.EffectiveFrom = next oldest. **(Regression for the original-design bug.)**
11. **Insert with isActive=false (Pending)**: insert pending P2P + PPL → assert P2P.EffectiveFrom = inserted PPL.EffectiveFrom once PPL becomes IsActive=true.

### 9.3 Large-volume tests

12. **`test_largeFacility_1500PPLs_term`**: synthetic 1,500-practitioner PL + 1,500 PPL + 1,500 P2P, then term the PL. Assert: all 1,500 P2Ps get correct EffectiveFrom (or untouched if no active PPLs remain); `Limits.getQueries() ≤ 12` (8 helper + 4 other handlers); `Limits.getDmlRows() ≤ 1,500 + existing handler DML`.
13. **`test_chunkedAggregate_threeChunks`**: generate 1,200 distinct (A, P) keys; assert helper makes 3 aggregate SOQLs (`Math.ceil(1200/500)`).
14. **`test_aggregateAtCliffEdge_1999keys`**: exactly 1,999 keys; assert chunking prevents `Too many query rows: 2001`.
15. **`test_dataLoader_5000RowBulkInsert`**: 5,000 PPLs inserted across 100 accounts × 50 practitioners; assert P2P populated correctly; assert no governor breach.
16. **`test_chainedBatch_idempotent`**: simulate `PRM_PracticeLocationTerminationBatch` → `PRM_PractitionerTermForFacilityBatch` chain. Assert helper's second-pass DML list is empty (no redundant P2P writes).

### 9.4 Cascade-suppression tests

17. **`test_triggerShortCircuit_p2pOnlyRefire`**: manually set `isP2PRecomputeInProgress=true` and DML 10 P2P rows; assert `updateAccountPNC` / `futureDatedProcessing` / `handleConciergeRollup` do NOT execute (e.g., assert no Account DML, no `PRM_FutureDatedProcessing__c` rows created).
18. **`test_mixedPPLAndP2P_doesNotShortCircuit`**: DML 5 PPL + 5 P2P rows with `isP2PRecomputeInProgress=true` — assert trigger does NOT short-circuit (because not all rows are P2P), so PPL-side handlers still run.

### 9.5 Backfill batch tests

19. **`test_backfill_dryRun_noUpdates`**: assert `PRM_AsyncProcess__c.PRM_RecordsUpdated__c > 0` but no actual P2P DML happened.
20. **`test_backfill_realRun_correctsKnownDrift`**: seed 10 P2P rows with deliberately wrong EffectiveFrom; run backfill; assert all corrected.

---

## 10. Risk & Side-Effects

| Risk | Severity | Mitigation |
|---|---|---|
| Aggregate `GROUP BY` exceeds 2,000-row platform cap | High | SOQL chunked to ≤ 500 keys (§6.3) |
| Non-selective query on 1,579-item IN-list | Medium | Same chunking keeps IN-list ≤ 500 |
| `afterDelete` no-op bug (newList == oldMap) | High | Explicit `isDelete=true` parameter forces all PPLs in scope to count as impacted (§6.3 Step 1) |
| Re-fire cascade (`updateAccountPNC`, `futureDatedProcessing`, `handleConciergeRollup` doing real work on P2P refire) | Medium | Top-of-trigger short-circuit gated by `isP2PRecomputeInProgress + allRowsAreP2P` (§6.4) |
| Chained batch (`PRM_PractitionerTermForFacilityBatch`) re-fires helper 1,579× per workflow | Low | Helper is idempotent — second pass does 2 SOQL + 0 DML. Cumulative ~4 min CPU spread across 1,579 separate async transactions. |
| Hand-rolled `EffectiveFrom` writes in `PRM_ReinstateVendorAccountBatchHelper` cause confusion vs. trigger | Low | Phase-2 cleanup (§7) once trigger is verified in QA |
| Production rollout breaks something unforeseen | Medium | Feature flag `P2PEffectiveFromAutoSync` (default OFF) → flip ON after backfill verification (§6.7) |
| `PRM_FutureDatedProcessing__c` rows created when helper updates P2P | Informational | This is desired behavior — when a future-dated PPL becomes active, the P2P should also move with it. The upsert is idempotent on external Id. |
| Heap pressure at 1,579 records combined with 6 existing static caches in `PRM_PracFacilityTriggerHandler` | Low | ~3 MB of 12 MB async budget — verified in audit doc §3 |
| Exception in helper takes down parent termination batch | High | Try / catch wraps entire helper body; logs to `PRM_ExceptionLogger`; clears `isP2PRecomputeInProgress` in catch (§6.3) |

---

## 11. Summary

**Root cause**: 16 listed guided flows all rely on per-flow logic in 8+ Apex helpers/batches/IPs to maintain HCPF dates. None of them implement "oldest active PPL EffectiveFrom" → P2P EffectiveFrom propagation.

**Fix**: One new method `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL` wired into `PRM_PracFacilityTriggerHandler.afterInsert/Update/Delete`. Centralizes the rule at the only common chokepoint (the HCPF trigger), so every existing and future flow inherits it automatically.

**Large-volume safety**: chunked SOQL (≤ 500 keys), chunked DML (≤ 200 rows), top-of-trigger cascade suppression keyed off `isP2PRecomputeInProgress + allRowsAreP2P`, feature flag for instant production disable, explicit `isDelete` parameter to fix the afterDelete edge case. Verified governor-safe up to the platform DML row ceiling of 10,000 records — well past the realistic worst case of 1,579 PPLs found in QA.

**Backfill**: `PRM_BackfillP2PEffectiveFromBatch` with dry-run mode, chunk size 200, completes the 230 K-row backfill in ~10 minutes. Suppresses its own trigger re-fire via the same guard.

**Total code touch**:

| File | Lines | Notes |
|---|---|---|
| `PRM_HCPFTriggerHelper.cls` | +220 | New `syncP2PEffectiveFromOldestActivePPL` + helpers |
| `PRM_PracFacilityTriggerHandler.cls` | +15 | Top-of-trigger short-circuit + 3 new wire-up calls |
| `PRM_BackfillP2PEffectiveFromBatch.cls` | +100 | New backfill batch |
| `PRM_FeatureConfigurationSettings__c` | +1 field | New checkbox `PRM_EnableP2PEffectiveFromAutoSync__c` |
| `PRM_HCPFTriggerHelperTest.cls` (new) | +600 | 20 test methods covering §9 |
| `PRM_PracFacilityTriggerHandlerTest.cls` | +50 | Cascade-suppression assertions |

**No OmniScript / IP / DataRaptor / Flow changes required.** The single-trigger chokepoint covers all 16 guided flows.
