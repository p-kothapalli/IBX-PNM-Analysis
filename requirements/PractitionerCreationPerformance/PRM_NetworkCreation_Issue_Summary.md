# PRM Network Creation Performance Issue - Summary

## Subject: Critical: PRM Delegated Practitioner Network Creation Timeout - Proposed Batch Solution

---

## Problem Statement

The `PRM_AddressLogicContainer` Integration Procedure is experiencing indefinite spinning/timeout when creating delegated practitioners with multiple practice locations.

---

## Current Impact

**User Experience:**
- UI spins indefinitely (5+ minutes) with no feedback
- Users uncertain if process is working or failed
- Poor perception of system reliability

**Technical Metrics:**
- **Processing volume:** 3 locations × 3 taxonomies × 15 networks = **54+ records**
- **Estimated operations:** ~280 (queries, DML, transformations)
- **Governor limits:** Approaching/hitting SOQL (100), CPU (60s async), Heap (12MB)
- **Current timeout:** 5+ minutes → No completion

---

## Root Cause

The `PRM_CreateDelegatedHFNRecords` child IP executes **24 sequential steps** synchronously:

1. **Taxonomy Network Creation** (9 records) → ~36 operations
2. **Payer Network Creation** (45 records) → ~180 operations  
3. **IFC Record Creation** (15 records) → ~45 operations
4. Supporting queries, deduplication, merging → ~20 operations

**Total: ~280 operations in a single transaction**

This exceeds synchronous processing capacity and causes the Integration Procedure to hang while waiting for completion.

---

## Proposed Solution

**Event-Driven Batch Architecture:**

```
PRM_AddressLogicContainer
  ↓ (Creates addresses - fast)
  ↓ (Publishes Platform Event)
  ↓ Returns immediately with "Processing..." message
  
[ASYNC] Batch Jobs (chained):
  → Taxonomy Batch (2-5 min)
  → Payer Network Batch (5-10 min)
  → IFC Batch (1-3 min)
  → Email notification on completion
```

**Benefits:**
- ✅ **Instant UI response** (< 3 seconds)
- ✅ **No governor limit issues** (renewable per batch)
- ✅ **Scalable** to any number of locations/networks
- ✅ **User visibility** via status field + email notification
- ✅ **Retry capability** for failed batches

---

## Implementation Overview

1. **Platform Event** → Triggers async processing
2. **3 Batch Classes** → Taxonomy, Payer Networks, IFC (chained)
3. **Status Tracking** → Field on Case Manager with progress updates
4. **Email Notification** → Alerts user on completion/failure
5. **IP Modification** → Replace sync call with event publish

**Estimated Development:** 1-2 weeks (includes testing)
**Risk Level:** Low (isolated to network creation, existing flow unchanged)

---

## Alternative Considered

**Optimizing current IP with chunking/queueable:**
- ❌ Still hits limits with 45+ network records
- ❌ Minimal user experience improvement
- ❌ Doesn't scale beyond current volume

---

## Next Steps

**Discussion Points:**
1. Approve event-driven batch approach?
2. Timeline for implementation (recommend 2-week sprint)
3. User communication strategy (status messages, timeframes)
4. Monitoring/dashboard requirements
5. Rollout plan (sandbox → pilot → production)

**Attachments:**
- Full implementation guide with code samples (available)
- Architecture diagram
- Test strategy

---

## Questions for Team

1. Are there other processes affected by similar scale issues?
2. Should we prioritize optimization of existing `PRM_CreateDelegatedHFNRecords` IP as interim fix?
3. What's acceptable processing time? (Current proposal: 8-18 minutes async)
4. Do we need real-time progress updates (e.g., "15 of 45 networks created")?

---

**Priority:** High  
**Impact:** User Experience, System Reliability  
**Complexity:** Medium  
**Recommendation:** Proceed with batch implementation

---

Please review and advise on preferred approach and timeline.
