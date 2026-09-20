# Large-Volume Audit of P2P EffectiveFrom Trigger Fix

> **Companion to** [`P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md`](./P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md). This document stress-tests the proposed `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL` trigger hook against the largest real-world cardinalities found in QA and the chain of batches it has to coexist with.

---

## 1. Real Data Cardinalities (live from QA org)

### 1.1 PPL counts per single Account ("group")

```
sf data query --target-org qa-sandbox \
  --query "SELECT AccountId, COUNT(Id) cnt FROM HealthcarePractitionerFacility
           WHERE RecordType.DeveloperName='PRM_PractitionerLocationAffiliation'
           GROUP BY AccountId ORDER BY COUNT(Id) DESC LIMIT 15"
```

| Account | Active+Inactive PPL count |
|---|---|
| 001UW00000ejey3YAA | **10,964** |
| 001UW00000ek0LrYAI | 7,459 |
| 001UW00000ejwaYYAQ | 6,691 |
| 001UW00000ejX7TYAU | 6,109 |
| 001UW00000ejMArYAM | 5,844 |
| … | … |
| 001UW00000ejzL8YAI | 3,364 |

There are **multiple groups with thousands of PPLs**. Top group ≈ 11K PPLs.

### 1.2 PPL counts per single Practice Location (the worst trigger fire vector)

```
sf data query --target-org qa-sandbox \
  --query "SELECT HealthcareFacilityId, COUNT(Id) cnt FROM HealthcarePractitionerFacility
           WHERE RecordType.DeveloperName='PRM_PractitionerLocationAffiliation'
           GROUP BY HealthcareFacilityId ORDER BY COUNT(Id) DESC LIMIT 5"
```

| HealthcareFacility (one Practice Location) | Practitioners attached (PPLs) |
|---|---|
| 0klUW0000001WhoYAE | **1,579** |
| 0klUW0000001eqjYAA | 1,046 |
| 0klUW0000001WhtYAE | 917 |
| 0klUW0000001WhlYAE | 676 |
| 0klUW0000001ufIYAQ | 497 |

**Top Practice Location has 1,579 practitioners.** When that PL is termed, `PRM_PracticeLocationTerminationBatch.execute` updates **all 1,579 PPLs in a single DML** — and that DML hits our new trigger hook in one fire.

### 1.3 PPLs per (Account, Practitioner)

| Bucket | Max count |
|---|---|
| `(AccountId, PractitionerId)` → PPLs | 104 |

Tightly bounded — one practitioner has at most ~100 PPLs at any single group.

### 1.4 Object-wide volumes

| Record type | Rows |
|---|---|
| PPL  | 563,282 |
| P2P  | 230,207 |
| Admitting Privileges | 268,333 |

---

## 2. Worst-Case Trigger Fire Scenarios

| # | Scenario | Records in `Trigger.new` | impactedAccountIds | impactedPractitionerIds | Distinct (Account,Practitioner) keys |
|---|---|---|---|---|---|
| A | **Terminate the 1,579-PPL Practice Location** via `PRM_PracticeLocationTerminationBatch` (chunk 1) | 1,579 PPLs | **1** | **1,579** | 1,579 |
| B | **Terminate the 10,964-PPL top Account** via `PRM_AccountTerminationBatch` (chunk 3) — `helper.getHcPracFacForPracLoc` builds one bulk DML across 3 facilities | ≈ 3 × avg(200) = 600 PPLs / chunk | 1 | ≤ 600 | ≤ 600 |
| C | **Practitioner Termination** via `PRM_PractitionerTermForFacilityBatch` (chunk 1) — one practitioner across all their PPLs | ≤ 104 × N_accounts | ≤ N_accounts | 1 | ≤ N_accounts |
| D | **Future-Dated Processing Batch** (chunk 9) flips a wave of HCPFs at activation/term date | ≤ 9 | ≤ 9 | ≤ 9 | ≤ 9 |
| E | **Unlink Practice Location from Practitioner** (`PRM_PDMUnlinkPractitioner.terminateNPIAndPracToPrac`) — synchronous from OmniScript | ≤ 100 PPLs (UI bounded) | ≤ 100 | 1 | ≤ 100 |
| F | **Mass Data Migration / Data Loader bulk update** of HCPF rows | Up to **10,000 per DML** | Up to thousands | Up to thousands | Up to thousands |
| G | **PracticeLocationReinstate** via `PRM_ReinstateVendorAccountBatch` re-activating all PPLs of a 1,579-PPL PL | 1,579 PPLs | 1 | 1,579 | 1,579 |

**Scenario A is the worst realistic case from existing flows.** Scenario F is unbounded — only possible if someone runs an unguarded Bulk API operation, but should still be considered for resilience.

---

## 3. Governor-Limit Analysis Against Worst Case (Scenario A: 1,579 PPLs)

| Governor | Limit | Worst-case usage | Verdict |
|---|---|---|---|
| **SOQL queries** (synchronous) | 100 | helper adds 2 (1 aggregate + 1 P2P lookup) | ✅ safe |
| **SOQL queries** (async / batch) | 200 | same +2 | ✅ safe |
| **SOQL aggregate rows** (`GROUP BY` result groups) | **2,000** | 1,579 distinct (A,P) keys | ⚠️ **at 79 % of limit** — exceeded for >2 K-key bulk DML |
| **SOQL rows total per tx** | 50,000 | agg returns 1,579 rows, P2P returns 1,579 rows → 3,158 from helper. Combined with other handlers (~10K) ≈ 13K | ✅ safe |
| **DML statements** | 150 | helper adds 1 | ✅ safe |
| **DML rows per tx** | 10,000 | helper updates up to 1,579 P2Ps | ✅ safe |
| **Apex CPU time** (sync 10s / async 60s) | n/a | helper loop is O(n) memory, ~20 ms for 1,579 records + 2 SOQLs ≈ 200 ms | ✅ safe |
| **Heap** (sync 6 MB / async 12 MB) | n/a | 1,579 rows × ~200 B = ~320 KB | ✅ safe |
| **Query selectivity** | force.com optimizer non-selective threshold (200 K rows / 30 %) | `WHERE AccountId IN (1) AND PractitionerId IN (1579)` against 563 K PPL rows: IN-list of 1,579 ≈ <0.3 % → uses `Account_Practitioner` composite | ⚠️ borderline — needs explicit chunking to keep IN-list ≤ 200 |
| **Trigger recursion** | n/a | helper updates P2P → trigger refires; recordType filter exits early on re-entry | ✅ guarded |

### 3.1 The Real Failure Mode: `2,000-row aggregate result` for very wide DMLs

Salesforce limits a single `SELECT ... GROUP BY ...` to **2,000 result groups**. If the trigger fires with >2,000 distinct `(AccountId, PractitionerId)` keys it will throw:

```
System.LimitException: Too many query rows: 2001
```

For current production flows this is bounded:
- Scenario A: 1,579 → just under the cliff
- Scenarios B, C, D, E, G: well under 2,000

**But** the next-largest PL above the current top could push past 2,000 (the top is **1,579 today**; if any one PL grows to 2,001+, the trigger breaks). Also Scenario F (data migration) can blow past instantly.

**Resolution**: the helper must chunk its inputs into sets of ≤ 500 keys per query, never relying on a single GROUP BY result.

---

## 4. Downstream Side-Effects of the New Trigger Hook

When the helper DML-updates P2P rows, the **HCPF trigger fires again on those P2P rows**. The cascade matters at 1,579-row scale:

| Handler invoked on P2P refire | Behavior on P2P record type | Cost @ 1,579 rows |
|---|---|---|
| `updateActiveLocationsCount` | Filters by `HealthcareFacilityId != null` → P2P has null → no-op | ~0 |
| `updateAccountPNC` | Iterates `Trigger.new`, gathers `PractitionerId` → **runs full PNC recompute even on P2P updates** | **2 SOQL + 1 DML on Account** for 1,579 practitioners. Touches up to 1,579 Practitioner Accounts. **NEEDS GUARD.** |
| `updatePrimaryFlagonExistingPPL` | Filters `hcpf.RecordTypeId != pracAffRecTypeId` → P2P is `pracAffRecTypeId` → skipped | ~0 |
| `futureDatedProcessing` | Upserts `PRM_FutureDatedProcessing__c` rows keyed by `HCPF_Id + '_Activate'`. Idempotent. | 1 upsert with up to 1,579 rows. Acceptable but adds 1,579 rows to FutureDatedProcessing. **Audit item.** |
| `processAffCareCatEffectiveDates` | Filters by `recordTypeId == RECTYPEID_PLAFFILIATION` → P2P skipped | ~0 |
| `handleConciergeRollup` | Has explicit P2P branch (`pracAffRecTypeId`) that adds AccountId to `pplAccountIds` and looks up PLAs → re-runs Concierge logic against those 1,579 P2P accounts. **Real cost.** | ~1 extra SOQL per cascade + work in `PRM_ConciergeRollupHelper.evaluate` |
| `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL` (self) | Re-entered with P2P → `n.RecordTypeId != pplRtId` filter exits early in the loop. | ~0 |

**Critical finding**: even with the self-recursion blocked, the P2P refire triggers **at least three other handlers that do real work**:
1. `updateAccountPNC` — runs Account PNC recompute on up to 1,579 Practitioner Accounts.
2. `futureDatedProcessing` — upserts 1,579 FutureDatedProcessing rows.
3. `handleConciergeRollup` — invokes Concierge evaluation on 1,579 P2P accounts.

These add governor-limit cost and side-effects (Account writes, FutureDatedProcessing rows) that aren't in scope of the requirement. **The fix must short-circuit these on P2P-only refires that are caused solely by the EffectiveFrom recompute.**

---

## 5. Recursion / Re-entry Audit

| Path | Re-entry risk | Mitigation |
|---|---|---|
| Helper updates P2P → `afterUpdate` fires → helper re-enters | Caught by recordType filter at top of helper (n.RecordTypeId != pplRtId → all skipped) | ✅ |
| Helper triggers `updateAccountPNC` on Account → Account trigger → ??? | Account trigger could DML back. Not currently — but a future Account afterUpdate handler could DML HCPF → fires helper again | Need a static guard `isP2PRecomputeInProgress` |
| Bulk processor (`PRM_PracticeLocationTerminationBatch.execute`) does multiple sequential DML on HCPF (PPLs + PLA on lines 254-260): trigger fires twice in one execute | Helper runs twice. Second run: nothing changed → no-op (idempotent). | ✅ but inefficient — recommend a guard |
| Future-Dated Processing batch DML → trigger → helper | Runs in async context (60 s CPU). Helper does its 2 SOQL + 1 DML. Per chunk 9 records. Safe. | ✅ |

**Recommendation**: add `@TestVisible private static Boolean isP2PRecomputeInProgress = false;` and gate the helper. Reset in `finally`.

---

## 6. Interaction Audit With Every Chained Batch

`PRM_PracticeLocationTerminationBatch.finish()` enqueues both `PRM_PractitionerTermForFacilityBatch` AND `PRM_PracticeLocationAutomationBatch` (chunk 1). Same for `PRM_AccountTerminationBatch`. These run in separate transactions, but they will DML-update HCPF records that **had already been updated by the parent batch** — so the helper fires for each.

| Batch chain step | DML on HCPF | Helper fires | Idempotent? |
|---|---|---|---|
| `PRM_PracticeLocationTerminationBatch.execute` updates 1,579 PPLs | ✓ | once at 1,579 rows | first write |
| `PRM_PracticeLocationTerminationBatch.execute` updates 0–N Networks (HFN — different object, no fire) | — | — | — |
| `PRM_PractitionerTermForFacilityBatch.execute` for each practitioner (chunk 1) — DMLs only the HCPF rows IT cares about (line 134) | ✓ per chunk | ~104 rows / fire × 1,579 fires (one per practitioner) | second pass — values are already correct so helper's DML list is empty → no DML done. Aggregate SOQL still runs ~1,579 extra times across batch. **Real CPU cost.** |
| `PRM_PracticeLocationAutomationBatch.execute` (chunk 1) — does NOT directly DML HCPF | — | — | — |

**Practitioner-by-practitioner re-fire** is the silent performance tax. For 1,579 practitioners, the helper runs 1,579 times in `PRM_PractitionerTermForFacilityBatch`. Each fire = 2 SOQL + 0 DML = ~150 ms CPU. Cumulative: 1,579 × 0.15 s = **~4 minutes of extra CPU spread across the batch** (each chunk has its own 60 s CPU budget, so per-chunk we're fine).

Acceptable, but justifies a guard like `if(/* old values already optimal */) skip;` or `PRM_TriggerContextControl.isBulkContext` opt-out for re-fires from chained batches.

---

## 7. Interaction With Existing Static Caches

`PRM_PracFacilityTriggerHandler` has 6 static memoization caches (`hfNameCache`, `accNameCache`, etc.) that live one Apex transaction. At 1,579 rows these can each hold ~1,579 entries. Each entry holds a small SObject (~200 B). Total memory: 6 × 1,579 × 200 B ≈ **2 MB**. Inside a batch execute (heap limit 12 MB) this is acceptable but eats half the budget. Helper's own dictionaries add ~1 MB more. Total heap ≈ 3 MB out of 12 MB. Safe.

`existingPracticeAffiliationAccountIds` from `PRM_AddNewLocationUtilityHelper` is also a static cache. Unrelated.

---

## 8. Query-Selectivity Hardening Details

For the worst case Scenario A:
```sql
SELECT AccountId, PractitionerId, MIN(EffectiveFrom)
FROM   HealthcarePractitionerFacility
WHERE  RecordTypeId      = '012UW000002dbQB...'  -- standard index
  AND  IsActive          = true                  -- not selectively-indexed by default
  AND  PRM_IsErrorRecord__c = false              -- custom checkbox
  AND  AccountId        IN  (1 id)
  AND  PractitionerId   IN  (1,579 ids)
GROUP BY AccountId, PractitionerId
```

- `AccountId` IN-list of size 1 → highly selective.
- `PractitionerId` IN-list of size 1,579 → optimizer chooses `AccountId` index first, then filters in-memory.
- Estimated cost: probe AccountId index → ~10,964 rows for top account → memory-filter to PractitionerId set → ~10,964 rows scanned.
- Salesforce's selectivity threshold for standard index = 200,000 rows. We're well under.
- For an account with 11K PPLs the query is **selective**. No `non-selective query` error expected.

Edge case: if the IN-list balloons past Salesforce's IN-list internal limit (~1,000 for many older orgs; modern orgs handle ~10K)— need to chunk to **≤ 500 IDs per IN clause** for safety.

---

## 9. Hardened Implementation

The original §6.1 implementation needs three reinforcements:

1. Chunk inputs to ≤ 500 keys per SOQL.
2. Hard recursion guard.
3. Skip downstream side-effects on P2P refire (use `PRM_TriggerContextControl` or a dedicated flag).

```apex
public with sharing class PRM_HCPFTriggerHelper {

    /* ─────────────────────────────────────────────────────────────────────
     *  Public re-entry / cross-handler flag — set to true while the helper
     *  is performing its own DML on P2P rows.  Other handlers in
     *  PRM_PracFacilityTriggerHandler should bail out early when this flag
     *  is on AND the new record is a P2P row, because the only change
     *  in that re-fire is an EffectiveFrom recompute we already accounted for.
     * ───────────────────────────────────────────────────────────────────── */
    @TestVisible public static Boolean isP2PRecomputeInProgress = false;

    /* ─────────────────────────────────────────────────────────────────────
     *  Configuration
     * ───────────────────────────────────────────────────────────────────── */
    private static final Integer CHUNK_SIZE = 500;   // safe under IN-list and 2K aggregate limits

    /* ─────────────────────────────────────────────────────────────────────
     *  Main entry point
     * ───────────────────────────────────────────────────────────────────── */
    public static void syncP2PEffectiveFromOldestActivePPL(
            List<HealthcarePractitionerFacility> changedList,
            Map<Id, HealthcarePractitionerFacility> oldMap,
            Boolean isDelete) {

        if (isP2PRecomputeInProgress) return;
        if (changedList == null || changedList.isEmpty()) return;

        Id pplRtId = PRM_GlobalConstant.RECTYPEID_PLAFFILIATION;
        Id p2pRtId = PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL;

        // 1. Collect impacted (AccountId, PractitionerId) pairs.
        //    Skip P2P rows entirely — we only care about PPL changes.
        Set<String> impactedKeys = new Set<String>();
        for (HealthcarePractitionerFacility n : changedList) {
            if (n.RecordTypeId != pplRtId) continue;
            if (n.AccountId == null || n.PractitionerId == null) continue;

            HealthcarePractitionerFacility o =
                (oldMap != null && !isDelete) ? oldMap.get(n.Id) : null;
            Boolean changed = isDelete
                || (o == null)
                || n.IsActive       != o.IsActive
                || n.EffectiveFrom  != o.EffectiveFrom
                || n.EffectiveTo    != o.EffectiveTo
                || n.PRM_IsErrorRecord__c != o.PRM_IsErrorRecord__c;
            if (!changed) continue;

            impactedKeys.add(n.AccountId + '|' + n.PractitionerId);

            if (o != null
                && (o.AccountId != n.AccountId
                    || o.PractitionerId != n.PractitionerId)) {
                impactedKeys.add(o.AccountId + '|' + o.PractitionerId);
            }
        }
        if (impactedKeys.isEmpty()) return;

        // 2. Chunk-by-key and accumulate the oldest active PPL EffectiveFrom per key.
        Map<String, Date> keyToOldestEffFrom = new Map<String, Date>();
        // missingKeys = keys with no remaining active PPL (so P2P EffectiveFrom must NOT be touched)
        List<String> keyList = new List<String>(impactedKeys);
        for (Integer i = 0; i < keyList.size(); i += CHUNK_SIZE) {
            Integer end = Math.min(i + CHUNK_SIZE, keyList.size());
            List<String> chunk = new List<String>();
            Set<Id> chunkAcctIds  = new Set<Id>();
            Set<Id> chunkPracIds  = new Set<Id>();
            for (Integer j = i; j < end; j++) {
                chunk.add(keyList.get(j));
                List<String> parts = keyList.get(j).split('\\|');
                chunkAcctIds.add(parts[0]);
                chunkPracIds.add(parts[1]);
            }
            for (AggregateResult ar : [
                SELECT AccountId acc, PractitionerId prac, MIN(EffectiveFrom) minEFF
                FROM   HealthcarePractitionerFacility
                WHERE  RecordTypeId        = :pplRtId
                  AND  IsActive            = true
                  AND  PRM_IsErrorRecord__c = false
                  AND  AccountId          IN :chunkAcctIds
                  AND  PractitionerId     IN :chunkPracIds
                GROUP BY AccountId, PractitionerId
            ]) {
                String key = ((Id)ar.get('acc')) + '|' + ((Id)ar.get('prac'));
                if (impactedKeys.contains(key)) {
                    keyToOldestEffFrom.put(key, (Date)ar.get('minEFF'));
                }
            }
        }

        // 3. Load matching P2P rows in chunks.
        List<HealthcarePractitionerFacility> p2ps = new List<HealthcarePractitionerFacility>();
        for (Integer i = 0; i < keyList.size(); i += CHUNK_SIZE) {
            Integer end = Math.min(i + CHUNK_SIZE, keyList.size());
            Set<Id> chunkAcctIds  = new Set<Id>();
            Set<Id> chunkPracIds  = new Set<Id>();
            for (Integer j = i; j < end; j++) {
                List<String> parts = keyList.get(j).split('\\|');
                chunkAcctIds.add(parts[0]);
                chunkPracIds.add(parts[1]);
            }
            p2ps.addAll([
                SELECT Id, AccountId, PractitionerId,
                       EffectiveFrom, EffectiveTo, IsActive, PRM_IsErrorRecord__c
                FROM   HealthcarePractitionerFacility
                WHERE  RecordTypeId        = :p2pRtId
                  AND  AccountId          IN :chunkAcctIds
                  AND  PractitionerId     IN :chunkPracIds
            ]);
        }

        // 4. Compute the deltas.
        List<HealthcarePractitionerFacility> toUpdate = new List<HealthcarePractitionerFacility>();
        for (HealthcarePractitionerFacility p2p : p2ps) {
            String key = p2p.AccountId + '|' + p2p.PractitionerId;
            if (!impactedKeys.contains(key)) continue;
            // No remaining active PPL → leave P2P EffectiveFrom alone (EffectiveTo cascade
            // in updatePrimaryFlagonExistingPPL handles termination separately).
            Date newEffFrom = keyToOldestEffFrom.get(key);
            if (newEffFrom == null) continue;
            if (p2p.EffectiveFrom == newEffFrom) continue;
            // Guardrails
            if (p2p.EffectiveTo != null && newEffFrom > p2p.EffectiveTo) continue;
            if (p2p.PRM_IsErrorRecord__c) continue; // already in error state — leave alone

            HealthcarePractitionerFacility u = new HealthcarePractitionerFacility(Id = p2p.Id);
            u.EffectiveFrom = newEffFrom;
            // Recompute IsActive consistent with the new EffectiveFrom
            u.IsActive = (newEffFrom <= Date.today())
                         && (p2p.EffectiveTo == null || p2p.EffectiveTo > Date.today());
            toUpdate.add(u);
        }

        if (toUpdate.isEmpty()) return;

        // 5. DML the deltas with the re-entry guard ON so the cascading
        //    handlers can short-circuit if they choose.
        isP2PRecomputeInProgress = true;
        try {
            // Chunk DML to keep updateActiveLocationsCount / handleConciergeRollup
            // sub-queries from blowing limits when toUpdate is huge.
            for (Integer i = 0; i < toUpdate.size(); i += 200) {
                Integer end = Math.min(i + 200, toUpdate.size());
                List<HealthcarePractitionerFacility> slice =
                    new List<HealthcarePractitionerFacility>();
                for (Integer j = i; j < end; j++) slice.add(toUpdate.get(j));
                update slice;
            }
        } finally {
            isP2PRecomputeInProgress = false;
        }
    }
}
```

### 9.1 Cooperating short-circuits in `PRM_PracFacilityTriggerHandler`

Inside the existing handlers that do real work on P2P refire, short-circuit when our recompute is the cause:

```apex
private void updateAccountPNC() {
    // ── NEW ── skip Account PNC recompute when refire is our P2P EffectiveFrom touch
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && allTriggerRowsAreP2POnly(Trigger.new)) return;
    // … rest unchanged …
}

private static void futureDatedProcessing(...){
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && allTriggerRowsAreP2POnly(newList)) return;
    // … rest unchanged …
}

public static void handleConciergeRollup(Map<Id,SObject> newItems, Map<Id,SObject> oldItems) {
    if (PRM_HCPFTriggerHelper.isP2PRecomputeInProgress
        && allTriggerRowsAreP2POnly((List<HealthcarePractitionerFacility>)
                (newItems != null ? newItems.values() : oldItems.values()))) return;
    // … rest unchanged …
}

private static Boolean allTriggerRowsAreP2POnly(List<HealthcarePractitionerFacility> rows) {
    Id p2pRt = PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL;
    for (HealthcarePractitionerFacility r : rows) {
        if (r.RecordTypeId != p2pRt) return false;
    }
    return true;
}
```

This neutralises the cascade overhead described in §4 — when our helper's DML re-fires the trigger, the other handlers exit on the first line.

### 9.2 Wire-up (revised)

```apex
public override void afterInsert(Map<Id, SObject> newItems) {
    updateAccountPNC();
    updateActiveLocationsCount();
    updatePrimaryFlagonExistingPPL(newItems, null);
    futureDatedProcessing((List<HealthcarePractitionerFacility>)newItems.values(), null);
    PRM_HCPFTriggerHelper.handleConciergeRollup(newItems, null);
    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)newItems.values(), null, false);
}

public override void afterUpdate(Map<Id, SObject> newItems, Map<Id, SObject> oldItems) {
    // … unchanged …
    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)newItems.values(),
        (Map<Id, HealthcarePractitionerFacility>)oldItems,
        false);
}

public override void afterDelete(Map<Id, SObject> oldItems) {
    if(!PRM_GlobalConstant.byPassVal) updateActiveLocationsCount();
    PRM_HCPFTriggerHelper.handleConciergeRollup(null, oldItems);
    PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL(
        (List<HealthcarePractitionerFacility>)oldItems.values(),
        null,    // no oldMap needed when isDelete=true
        true);
}
```

---

## 10. Re-evaluated Worst Case Limits With Hardened Implementation

| Scenario | SOQL Q | SOQL rows | DML statements | DML rows | Aggregate rows | Verdict |
|---|---|---|---|---|---|---|
| **A – 1,579 PPL Practice Location term** | 4 queries (1,579/500 ≈ 4 chunks for agg) + 4 (P2P) = **8** | ~3,500 | ≤ 8 (chunk 200 DML) | ≤ 1,579 | ≤ 500 / chunk | ✅ |
| Same with `PractitionerTermForFacilityBatch` chained refire | +2 SOQL × 1,579 chunks = 3,158 over the lifetime of the batch (spread across chunks; per-execute ≤ 4 SOQL) | per-chunk safe | per-chunk safe | per-chunk safe | per-chunk safe | ✅ |
| **B – Account Term chunk 3 (≈600 PPL)** | 2 + 2 = 4 | ~1,200 | ≤ 3 DML | ≤ 600 | ≤ 500 | ✅ |
| **F – Data Loader 10,000-row HCPF bulk update** | 20 + 20 = 40 SOQL | ~20K | ≤ 50 DML (200 each) | ≤ 10,000 | ≤ 500 / chunk | ✅ |
| **Pathological 2,500 distinct (A,P) keys at once** | 5 + 5 = 10 SOQL | ≤ 5,000 | ≤ 13 DML | ≤ 2,500 | ≤ 500 / chunk | ✅ |

Helper is now safe up to any input size that fits within the Apex DML row limit (10,000 sync / 10,000 async), which is the wall everything else hits anyway.

---

## 11. Failure-Mode Tests to Add to `PRM_PracFacilityTriggerHandlerTest`

Beyond the 8 scenarios in the original report, the audit findings require:

| Test | What it verifies | Setup hint |
|---|---|---|
| `test_largeFacilityTermination_1500PPLs` | Helper succeeds when 1,500 PPLs for one PL are termed in a single DML | Create 1,500 Practitioner Accounts + 1,500 PPLs all pointing at 1 HealthcareFacility + 1,500 P2P records. Term the PL → assert no governor breach, all 1,500 P2Ps get correct EffectiveFrom |
| `test_chunkedAggregate_threeChunks` | Verifies chunk loop with > 500 keys runs multiple SOQL queries | Generate 1,200 keys, count SOQL via `Limits.getQueries()` before/after |
| `test_noActivePPL_doesNotTouchP2P` | When all PPLs are termed, P2P EffectiveFrom is NOT modified by helper | Term all PPLs for (A, P), assert P2P.EffectiveFrom unchanged |
| `test_concurrentP2PRefire_doesNotRecurse` | Helper sets `isP2PRecomputeInProgress` correctly | Add a static counter incremented on each helper call; assert ≤ 1 invocation per PPL DML |
| `test_dataLoader_5000RowBulkInsert` | New PPL inserts in bulk don't break the helper or other handlers | `Test.startTest()` + `insert 5000 PPLs` + assert P2P populated correctly for each (A, P) group |
| `test_chainedBatchRefire_noExtraDML` | `PRM_PractitionerTermForFacilityBatch` running after `PRM_PracticeLocationTerminationBatch` doesn't re-update P2Ps that are already correct | Mock the chain; assert the second pass invokes helper but the toUpdate list is empty |
| `test_handlerShortCircuit_skipsOnP2PRefire` | `updateAccountPNC`, `futureDatedProcessing`, `handleConciergeRollup` short-circuit during `isP2PRecomputeInProgress` and all rows are P2P | Set flag manually, simulate trigger fire on P2P-only rows, assert no Account / FutureDated / Concierge work |
| `test_aggregateAtCliffEdge_1999keys` | Exactly at the 2K aggregate boundary | Generate 1,999 distinct (A,P) keys; ensure chunking prevents `Too many query rows: 2001` |
| `test_p2pInsertWithoutPPL_noop` | Insert P2P standalone → helper's record-type filter skips it cleanly | Insert P2P with no matching PPLs; assert no SOQL beyond the one filter check |
| `test_deletePPL_recomputesP2P` | `afterDelete` path works (the original bug where oldMap == newList) | Delete the oldest active PPL; assert P2P.EffectiveFrom updates to next oldest |

---

## 12. Data-Backfill Batch — Large-Volume Hardening

The 230 K-row backfill (§8 of the original report) needs the same hardening:

```apex
global class PRM_BackfillP2PEffectiveFromBatch
        implements Database.Batchable<SObject>, Database.Stateful {
    global Database.QueryLocator start(Database.BatchableContext bc){
        // Scope = P2P records. Default chunk size 200 is fine.
        return Database.getQueryLocator(
            'SELECT Id, AccountId, PractitionerId, EffectiveFrom, EffectiveTo, IsActive ' +
            'FROM   HealthcarePractitionerFacility ' +
            'WHERE  RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL ' +
            '  AND  PRM_IsErrorRecord__c = false');
    }
    global void execute(Database.BatchableContext bc,
                        List<HealthcarePractitionerFacility> scope){
        Set<Id> acctIds = new Set<Id>();
        Set<Id> pracIds = new Set<Id>();
        for (HealthcarePractitionerFacility p2p : scope) {
            acctIds.add(p2p.AccountId);
            pracIds.add(p2p.PractitionerId);
        }
        Map<String, Date> oldest = new Map<String, Date>();
        for (AggregateResult ar : [
            SELECT AccountId, PractitionerId, MIN(EffectiveFrom) minEFF
            FROM   HealthcarePractitionerFacility
            WHERE  RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PLAFFILIATION
              AND  IsActive = true
              AND  PRM_IsErrorRecord__c = false
              AND  AccountId IN :acctIds
              AND  PractitionerId IN :pracIds
            GROUP BY AccountId, PractitionerId
        ]) {
            oldest.put(((Id)ar.get('AccountId'))+'|'+((Id)ar.get('PractitionerId')),
                       (Date)ar.get('minEFF'));
        }
        List<HealthcarePractitionerFacility> toUpdate =
            new List<HealthcarePractitionerFacility>();
        for (HealthcarePractitionerFacility p2p : scope) {
            String key = p2p.AccountId+'|'+p2p.PractitionerId;
            Date newEffFrom = oldest.get(key);
            if (newEffFrom == null) continue;            // no active PPL left
            if (p2p.EffectiveFrom == newEffFrom) continue;
            if (p2p.EffectiveTo != null && newEffFrom > p2p.EffectiveTo) continue;
            toUpdate.add(new HealthcarePractitionerFacility(
                Id            = p2p.Id,
                EffectiveFrom = newEffFrom,
                IsActive      = (newEffFrom <= Date.today())
                                && (p2p.EffectiveTo == null || p2p.EffectiveTo > Date.today())
            ));
        }
        // Set the re-entry guard so the trigger refire short-circuits.
        PRM_HCPFTriggerHelper.isP2PRecomputeInProgress = true;
        try {
            if (!toUpdate.isEmpty()) update toUpdate;
        } finally {
            PRM_HCPFTriggerHelper.isP2PRecomputeInProgress = false;
        }
    }
    global void finish(Database.BatchableContext bc){}
}
```

Execute with `Database.executeBatch(new PRM_BackfillP2PEffectiveFromBatch(), 200);` — at 230K rows that's **1,150 batch executions** over ~30–60 min. Each execute:
- 200 P2P rows in scope.
- 1 aggregate SOQL (200 group rows max — well under 2K).
- 1 DML on ≤ 200 P2P rows.

Safe.

---

## 13. Summary of Audit Findings

| # | Finding | Severity | Fix |
|---|---|---|---|
| 1 | Top single Practice Location has **1,579 PPLs** (Scenario A) — single trigger fire of that size | High | Helper chunks SOQL to 500 keys; ✅ resolved in §9 |
| 2 | Aggregate `GROUP BY` 2,000-row hard limit could be exceeded by future data growth or Data Loader bulk DML | High | Chunked SOQL per ≤ 500 keys; ✅ §9 |
| 3 | IN-list with 1,579 values borderline-non-selective | Medium | Chunking also fixes IN-list size; ✅ §9 |
| 4 | Helper DML on P2P re-fires trigger → `updateAccountPNC`, `futureDatedProcessing`, `handleConciergeRollup` each do real work on P2P refire | Medium | Cooperating short-circuits keyed off `isP2PRecomputeInProgress`; ✅ §9.1 |
| 5 | `afterDelete` original implementation passed identical `newList`/`oldMap` → `changed=false` → helper never fires on PPL delete | High | New `isDelete` parameter forces all to be impacted; ✅ §9 |
| 6 | `PRM_PractitionerTermForFacilityBatch` (chained, chunk 1) refires helper 1,579 times when terming a 1,579-PPL PL — each fire is a no-op DML but still 2 SOQL each | Low | Acceptable. Could later add `PRM_TriggerContextControl` skip; not blocking. |
| 7 | Future-Dated Processing creates 1 row per P2P updated by the helper | Low / informational | Upsert is idempotent; future-dated activate row is actually desirable so the P2P moves with the PPL when the date arrives. |
| 8 | Concierge Rollup may evaluate against the P2P refire | Medium | Short-circuit in §9.1 |
| 9 | Backfill batch must obey the same chunking and guard rules | High | New §12 implementation |
| 10 | Heap ≈ 3 MB / 12 MB at 1,579 records | Low | Acceptable; chunked DML keeps individual chunk heap low |

**Bottom line**: with the hardened implementation in §9 + the cooperating short-circuits in §9.1, the fix is governor-safe up to the platform DML row ceiling of 10,000 records per transaction — well past the largest real Practice Location in QA today (1,579 PPLs).

If a single transaction were ever to update >10,000 PPLs (e.g., an unguarded Bulk API push), the existing Account/Practitioner termination batches would already break before our helper does, so this is the responsibility of the bulk-load caller to chunk — not our trigger.
