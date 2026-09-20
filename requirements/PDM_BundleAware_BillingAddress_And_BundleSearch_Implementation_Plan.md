# PDM Manual Update — Bundle-Aware Billing Address Flow + Practice Location Bundle Search Redesign — Build-Ready Implementation Plan

> ## ✅ Bundle-invariant scope decision RESOLVED 2026-06-22
>
> **Confirmed rule:** A Practice Location is in a capitated bundle if-and-only-if there is a Practice Location Taxonomy (HFN) on that PL that is simultaneously (a) referenced from `PRM_HealthcareFacilityBundleAssociation__c` pointing to an active `'Capitated Bundle'`, AND (b) linked to an active `PRM_ProgramParticipation__c` of program type `CAP`.
>
> `PRM_HealthcareFacilityAssociation__c` (HFA) Designated Specialty Bundle / Network records are **out of scope** — they encode referral relationships without the shared-billing-address invariant.
>
> §0 below predates this decision; the wording remains accurate at the high level but the **gate computation** for any WS-1 work must use the conjunction described above (see the unblocker story for the canonical SOQL and Apex skeleton). Decision brief: [`PDM/PDM_BillingAddress_Bundle_Invariant_Decision_Brief.md`](PDM/PDM_BillingAddress_Bundle_Invariant_Decision_Brief.md). Unblocker story (cleared for pickup): [`PDM/US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md`](PDM/US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md).

**Date:** 2026-05-05
**Companion to:** `requirements/PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md` (the investigation doc)
**Org investigated:** `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, `00DcW000004drQLUAY`)
**Workstreams:**
- **WS-1 (HIGH priority):** Replace the dead-end `PracticeLocationInActiveBundleError` validation in `PRM_PDMManualUpdate_English` with an inline, branching remediation experience.
- **WS-2 (MEDIUM priority):** Replace the typeahead in `PRM_SelectPracticeLocationBundle_English` with a custom LWC + Apex search supporting Tax ID and Billing Address filters and proper server-side pagination.
- **WS-3 (HOUSEKEEPING):** Decommission the legacy DataRaptor `PRMGetPracticeLocationBundles` once WS-2 ships.

---

## 0. Confirmed Business Rule (anchor for every design choice below)

> "The Practice Locations under a capitated bundle are of the same Tax ID account and **must share the same billing address**."

Three consequences flow from this rule:

1. **Bundle membership is the right gate** for the Update-Billing-Address validation, not `PRM_ParticipatesInCapitatedProgram__c`. Bug fix Option A from the investigation doc is the correct interpretation.
2. **A user who wants to change a PL's billing address has two valid intents** the system has never asked them to choose between:
   - *"I want to change billing address for the whole bundle (all member PLs)"* — keeps the bundle intact.
   - *"I want to change billing address for just this one PL"* — requires removing the PL from the bundle first.
3. **Today's flow only supports the second intent, and only as a dead-end error.** It never offers the first intent at all.

---

## 1. Why the Original Tier 3 (search-only) Plan Was Incomplete

The investigation doc proposed a Filter+List bundle search redesign as the single solution. After learning the bundle invariant, that's only half the answer:

| Original assumption | Reality after the bundle invariant is known |
|---|---|
| User blocked by validation needs help finding the bundle | True, but they also probably want to change the address for the WHOLE bundle, not just remove one PL |
| Better search ⇒ user can self-serve the removal | Removal is async (goes through Network Management QC) — even with perfect search the user still has to wait |
| Search is the highest-value fix | Inline remediation in PDM Manual Update is the highest-value fix; search is the next most valuable |

**Net effect on the plan:** the Filter+List bundle search is still useful (1,582 active bundles, broken typeahead, ops users need it), but it's no longer the primary lever for unblocking the reported user. Inline remediation is.

---

## 2. WS-1 — Inline, Bundle-Aware Billing Address Flow (HIGH priority)

### 2.1 Target user experience

```
Step "Update Billing and/or Mailing address"
─────────────────────────────────────────────
  AddressActionType: ( ) Update Mailing Address
                     (•) Update Billing Address       ← user selects this
                     ( ) Update Mailing and Billing Address

  [user enters new address...]

  ┌── Validation runs (replaces today's PracticeLocationInActiveBundleError) ──┐
  │                                                                           │
  │  Q: Is this Practice Location in any active capitated bundle today?       │
  │                                                                           │
  │  ───────────────────────────────────────────────────────────────────────  │
  │  Branch A — No bundles found                                              │
  │     Allow Next. (Includes today's "Lauren Rosen" case where the           │
  │     CAP-program flag is true but bundle membership is empty.)             │
  │  ───────────────────────────────────────────────────────────────────────  │
  │  Branch B — One or more bundles found                                     │
  │                                                                           │
  │     Inline panel renders below the address block:                         │
  │     ┌───────────────────────────────────────────────────────────────────┐ │
  │     │ ⚠  This Practice Location is part of <N> active capitated         │ │
  │     │    bundle(s). All Practice Locations in a capitated bundle must   │ │
  │     │    share the same billing address.                                │ │
  │     │                                                                   │ │
  │     │  • <Bundle Name 1>   Tax ID 232266054   Bundle ID 7000003147      │ │
  │     │       Bundle has <K> other Practice Locations                     │ │
  │     │  • <Bundle Name 2>   Tax ID 223537011   Bundle ID 7000003048      │ │
  │     │       Bundle has <M> other Practice Locations                     │ │
  │     │                                                                   │ │
  │     │  How would you like to proceed?                                   │ │
  │     │   ( ) Update billing address for ALL <Z> Practice Locations       │ │
  │     │       in these bundle(s)  ← preserves bundle, recommended         │ │
  │     │   ( ) Remove this Practice Location from the bundle(s),           │ │
  │     │       then update only this location's billing address            │ │
  │     │       (will create a Network Management QC case for review)       │ │
  │     │   ( ) Cancel                                                      │ │
  │     └───────────────────────────────────────────────────────────────────┘ │
  └───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The three branches translated to behavior

| Branch | User selection | Resulting action |
|---|---|---|
| **A** (no bundles) | n/a — no panel shown | OS proceeds normally; downstream `IPCreatePDMRecords` runs as today |
| **B-1** (in bundle, update for ALL) | "Update billing address for ALL …" | OS adds all member-PL Ids to a `pendingBillingAddressUpdate` collection; downstream Apex (new method on `PRM_OmniUtils` or `PRM_BundleBillingAddressService`) updates billing address on **every active member PL** in one transaction; `PRM_HealthcareFacilityBundle__c.PRM_Active__c` is unchanged |
| **B-2** (in bundle, remove and update only this PL) | "Remove this PL from the bundle(s)" | Calls existing `PRM_ManageHCFBundleAndAssociations` IP path with `RequestType = "Remove from Existing Bundle"` (creates `Case` + `IndividualApplication` + `CaseDataManager`, runs `PRM_HCFBundleAssociationBatch`). After the removal request is queued, OS branches to a confirmation/blocked step (see §2.5 below for the QC vs. fast-path decision) |
| **B-3** (cancel) | "Cancel" | OS goes back to the Address Action Type select; no DML |

### 2.3 Replacing the buggy validation gate

| Element | Today | After fix |
|---|---|---|
| `BundleError` (Formula) | `AND(%Facility:IsCapitated% == true, CONTAINS(%AddressActionType%, "Billing"))` reading from `PRM_ParticipatesInCapitatedProgram__c` | **Delete or deactivate.** Replaced by `Facility:ActiveBundleCount` populated by a new DR / Apex action that counts active `PRM_HealthcareFacilityBundleAssociation__c` rows for this HCF where the related `PRM_HealthcareFacilityBundle__c.PRM_Active__c = true` and `PRM_BundleType__c = 'Capitated Bundle'` |
| `PracticeLocationInActiveBundleError` (Validation) | Hard-blocks Next when `BundleError == true` | **Delete or deactivate.** Replaced by the inline LWC panel below |
| **NEW** Custom LWC element on the same step | n/a | `c-prm-bundle-aware-billing-action` — renders the panel in §2.1; reads `inboundFacilityId`, `inboundAddress`, `inboundActiveBundles`; emits `selection` event back via `omniApplyCallResp` |
| **NEW** DataRaptor / Apex | n/a | `PRMGetActiveBundlesForHCF` — input: `facilityId`; output: list of `{BundleId, BundleName, BundleTaxId, BundleIdentifier, OtherPLCount, EffectiveFrom, EffectiveTo}` filtered to **active capitated bundles only** |
| **NEW** Apex service | n/a | `PRM_BundleBillingAddressService.applyBillingAddressToBundleMembers(...)` for B-1; reuse `PRM_ManageHCFBundleAssParents` for B-2 |

### 2.4 New OmniScript node names (so downstream merge tokens stay clean)

| Node | Type | Source |
|---|---|---|
| `Facility:ActiveBundleCount` | Number | DR `PRMGetActiveBundlesForHCF` (count of records returned) |
| `Facility:ActiveBundles` | List<Object> | DR `PRMGetActiveBundlesForHCF` (full list for inline rendering) |
| `BundleAwareChoice` | String | Set by LWC: `"UpdateAllInBundle"` \| `"RemoveAndUpdate"` \| `"Cancel"` |
| `BundleAwareTargetFacilityIds` | List<Id> | Set by LWC for B-1: every active member PL Id across all bundles the current PL is in (de-duped) |
| `BundleAwareRemovalRequestId` | Id | Set by LWC for B-2: the `Case` Id (or `IndividualApplication` Id) of the QC case created |

### 2.5 The QC-vs-fast-path decision (REQUIRES BUSINESS INPUT)

The existing "Remove from Existing Bundle" path is **asynchronous and routes to QC**:

- `PRM_ManageHCFBundleAssParents` IP → creates `Case` (`Type: "Network Management QC"`, `Status: "New"`), `IndividualApplication` (`Stage: "Network Management QC"`, `Status: "In Progress"`), and `CaseDataManager`
- → calls `PRM_OmniUtils.terminateHCFBundleAssocationsBatch(...)` → executes `PRM_HCFBundleAssociationBatch` (Database.executeBatch with size 200)
- The batch sets `PRM_Active__c = false` on the targeted `PRM_HealthcareFacilityBundleAssociation__c` records and applies effective dates
- A QC reviewer must approve the case before the change is considered complete

**Implication:** B-2 cannot complete the billing-address update *in the same user session*. Two valid product paths exist:

| Path | What B-2 actually does | UX after submit | Risk |
|---|---|---|---|
| **Path Q (queue + wait)** | Creates the QC case as today; locks the billing-address update behind it. User sees: *"Your bundle removal request has been submitted (Case #00012345). Once Network Mgmt QC approves it, you'll be able to retry the billing address update."* OS finishes here; no billing change yet. | User comes back later (maybe days) to redo the address update | Maintains existing controls; long delay; user has to remember to come back |
| **Path F (fast-path)** | Bypasses QC for this specific use case: synchronously deactivates the bundle association(s), then immediately runs the billing address DML. Still creates an audit trail (modified `Case` of a different type, or a new `PRM_BundleBillingAddressAudit__c`) but does not require human approval. | One-shot completion; user's billing address is updated when the OS finishes | Removes a control point — Provider Contracting / Network Mgmt sign-off required |

**Recommendation:** Path Q for v1 (preserves controls, ships faster, no governance asks). Path F as a follow-up if the wait is unacceptable to the business.

> ❓ **Decision required from Provider Contracting / Network Management QC:** Path Q or Path F for B-2? The rest of WS-1 is identical either way; only the post-submit branch differs.

### 2.6 What B-1 ("update for all in bundle") does in detail

| Step | Action | Notes |
|---|---|---|
| 1 | LWC computes the union of all active member PL Ids across the bundle(s) this HCF belongs to | Returned by the same `PRMGetActiveBundlesForHCF` DR (extend it with a `MemberPLIds` array per bundle) |
| 2 | LWC writes the union into `BundleAwareTargetFacilityIds` via `omniApplyCallResp` | De-duped Ids |
| 3 | OS proceeds to the existing address-validation step (Precisely / recommended-address logic) on the new address | Unchanged |
| 4 | At commit time, instead of `IPCreatePDMRecords` running for one PL, a new IP `PRM_BundleBillingAddressBulkUpdate` runs `Address` upsert across all `BundleAwareTargetFacilityIds` | New IP wraps existing per-PL address update logic in a loop |
| 5 | Audit trail row written | One row per PL touched, with reference to the originating bundle and the originating case / OS run |

**Permissions:** B-1 implicitly grants the user authority to update billing addresses for PLs they didn't open. If profile/permset gating is needed (likely for non-PDM-admin users), enforce via `WITH USER_MODE` and a permission set check at the IP boundary.

> ❓ **Decision required:** Who is allowed to run B-1? PDM Admins only, or also PDM Specialists? Drives the permission set assignment.

### 2.7 WS-1 file inventory

| # | File | Type | Purpose |
|---|---|---|---|
| 1 | `force-app/main/default/lwc/prmBundleAwareBillingAction/prmBundleAwareBillingAction.js` (+ `.html`, `.css`, `.js-meta.xml`) | LWC | Renders the inline panel; reads `inboundFacilityId`, `inboundAddress`, list of bundles; emits choice + member-PL-Id collection back to OS via `omniApplyCallResp` |
| 2 | `force-app/main/default/lwc/prmBundleAwareBillingAction/__tests__/prmBundleAwareBillingAction.test.js` | Jest | Unit tests for the three branches and edge cases |
| 3 | `force-app/main/default/omniDataTransforms/PRMGetActiveBundlesForHCF_1.rpt-meta.xml` | DataRaptor | Input `facilityId`; outputs the active capitated bundles the HCF is in plus member-PL Ids and counts |
| 4 | `force-app/main/default/omniIntegrationProcedures/PRM_BundleBillingAddressBulkUpdate_Procedure_1.oip-meta.xml` | Integration Procedure | New IP that loops the existing per-PL address update logic across `BundleAwareTargetFacilityIds` (B-1 path) |
| 5 | `force-app/main/default/classes/PRM_BundleBillingAddressService.cls` (+ `Test`) | Apex | Business logic for B-1; encapsulates the bulk update, audit row creation, and (if Path F is chosen) the synchronous bundle-association deactivation for B-2 |
| 6 | `force-app/main/default/classes/PRM_BundleAwareValidationService.cls` (+ `Test`) | Apex | Server-side counterpart to the LWC; pure function `getActiveBundlesForFacility(Id facilityId, Date asOfDate)` returning the bundle DTO list (called by the new DR if implementation prefers Apex over native DR) |
| 7 | (modify) `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_BundleError.json` | OS element | Set `IsActive: false` |
| 8 | (modify) `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError.json` | OS element | Set `IsActive: false` |
| 9 | (new) `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_DRGetActiveBundles.json` | OS element | DataRaptor Extract Action that calls `PRMGetActiveBundlesForHCF` and writes `Facility:ActiveBundles` and `Facility:ActiveBundleCount` |
| 10 | (new) `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_BundleAwarePanel.json` | OS element | Custom LWC element binding to `prmBundleAwareBillingAction` with the customAttributes wiring described in §2.4 |
| 11 | (modify) `force-app/main/default/omniScripts/PRM_PDMManualUpdate_English_44.os-meta.xml` (or whichever is current) | OS wrapper | Bump active version to next; keep prior version-controlled for rollback |
| 12 | (optional) `force-app/main/default/objects/PRM_BundleBillingAddressAudit__c/...` | Custom object | New audit object if Provider Contracting requires per-PL-touched audit rows beyond standard Field History |

### 2.8 Apex contract — `PRM_BundleAwareValidationService.getActiveBundlesForFacility`

```
@AuraEnabled(cacheable=true)
public static String getActiveBundlesForFacility(Id facilityId, Date asOfDate) {
  // Returns JSON-serialized list of:
  //   {
  //     BundleId, BundleName, BundleTaxId, BundleIdentifier,
  //     BundleType, EffectiveFrom, EffectiveTo,
  //     CurrentMemberPLIds: ["0klUW...", "0klUW..."]   (active members as of asOfDate)
  //   }
  // Filters:
  //   PRM_HealthcareFacilityBundleAssociation__c.PRM_HealthcareFacility__c = :facilityId
  //   AND PRM_Active__c = true
  //   AND PRM_HealthcareFacilityBundle__c.PRM_Active__c = true
  //   AND PRM_HealthcareFacilityBundle__c.PRM_BundleType__c = 'Capitated Bundle'
  //   AND (PRM_EffectiveFrom__c <= :asOfDate OR :asOfDate IS NULL)
  //   AND (PRM_EffectiveTo__c >= :asOfDate OR PRM_EffectiveTo__c IS NULL)
  // For each bundle, sub-query active member PL Ids.
}
```

`cacheable=true` is acceptable because this is a read; the LWC also re-queries on user action.

### 2.9 WS-1 testing strategy

#### Apex (`PRM_BundleAwareValidationServiceTest`)
| Scenario | Expectation |
|---|---|
| Facility with 0 active bundle associations | Returns empty list |
| Facility flagged `PRM_ParticipatesInCapitatedProgram__c=true` but with 0 active bundle associations (Lauren Rosen) | Returns empty list (i.e., Branch A applies) |
| Facility in 1 active capitated bundle with 4 other active members | Returns 1 entry, `CurrentMemberPLIds` length = 5 (includes self) |
| Facility in 2 active bundles | Returns 2 entries; `CurrentMemberPLIds` is a list-of-lists across them |
| Facility in 1 inactive bundle | Returns empty list (only active bundles count) |
| `asOfDate = null` defaults to `Date.today()` | Verified |
| `WITH USER_MODE` enforced | User without read on Bundle gets the appropriate error envelope, not an unhandled exception |

#### LWC (`prmBundleAwareBillingAction.test.js`)
| Scenario | Expectation |
|---|---|
| Empty bundle list | Component renders nothing; OS Next button enabled |
| One bundle, user picks "Update for ALL" | `omniApplyCallResp` called with `BundleAwareChoice="UpdateAllInBundle"` and full `BundleAwareTargetFacilityIds` list |
| Two bundles, user picks "Update for ALL" | Target Ids de-duped across both bundles |
| User picks "Remove and update only this PL" | `omniApplyCallResp` called with `BundleAwareChoice="RemoveAndUpdate"`; subsequent IP call wired to `PRM_ManageHCFBundleAssParents` (or fast-path Apex if Path F) |
| User picks "Cancel" | `BundleAwareChoice="Cancel"` written; OS rolls back to AddressActionType select |

#### Manual / integration QA
1. **Lauren Rosen (`0klUW0000001Nu8YAE`)** — verify Branch A applies (no bundles) and the billing-address update completes.
2. A real bundled HCF (pick any active member of `Advocare Berlin Medical Associ Bundle` from QA) — verify Branch B; pick B-1; confirm all 7 sibling PLs get the new billing address.
3. Same bundled HCF — verify B-2 (Path Q) creates a Network Management QC `Case`; confirm OS finishes with the "you'll be able to retry once approved" message and no billing change is committed.
4. Permission gating (per §2.6 decision) — non-permitted user can see the panel but cannot select B-1.
5. Performance: Bundle with 25+ members on B-1 — confirm `PRM_BundleBillingAddressBulkUpdate` IP completes within IP timeout (30 s default).

### 2.10 WS-1 effort estimate

| Activity | Days |
|---|---|
| Apex: `PRM_BundleAwareValidationService` + `PRM_BundleBillingAddressService` + tests | 2.5 |
| DR: `PRMGetActiveBundlesForHCF` (or Apex equivalent) | 0.5 |
| IP: `PRM_BundleBillingAddressBulkUpdate` | 1.0 |
| LWC: `prmBundleAwareBillingAction` + Jest | 2.0 |
| OS rewiring: deactivate old elements, add new DR + LWC element, version bump | 0.5 |
| (optional) `PRM_BundleBillingAddressAudit__c` object | 0.5 |
| Manual QA + UAT | 1.5 |
| **Total** | **~8.5 dev-days** (8 if audit object skipped, 9 if Path F adds synchronous removal Apex) |

---

## 3. WS-2 — Filter+List Bundle Search Replacement (MEDIUM priority)

This still ships, but its primary user becomes the **ops user proactively managing bundles in `ManagePracticeLocationBundles`**, not the user blocked by the PDM validation (WS-1 handles that case inline).

### 3.1 Filter set (final)

| Filter | Required? | Mapped to |
|---|---|---|
| Tax ID | Optional | `PRM_HealthcareFacilityBundle__c.PRM_TaxID__c` (exact, digits-only normalized) |
| Bundle Identifier | Optional | `PRM_HealthcareFacilityBundle__c.PRM_BundleIdentifierSerial__c` (exact) |
| Bundle Name | Optional | `PRM_HealthcareFacilityBundle__c.Name LIKE '%key%'` (≥3 chars) |
| Bundle Type | Optional | `PRM_HealthcareFacilityBundle__c.PRM_BundleType__c` (multi-pick) |
| Effective on | Optional | `PRM_EffectiveFrom__c <= :date AND (PRM_EffectiveTo__c >= :date OR null)`. Defaults to `TODAY()`. |
| **Billing Address** (NEW) | Optional, but if provided requires Zip OR State+City | Joins via `Address.PRM_AddressType__c INCLUDES 'Billing'` AND `PRM_Active__c = true` → `Address.ParentId = Location.Id` → `HealthcareFacility.LocationId` → `PRM_HealthcareFacilityAssociation__c` (or `PRM_HealthcareFacilityBundleAssociation__c`) → `PRM_HealthcareFacilityBundle__c.Id` |

Filter precision rule (server-side enforced, returns friendly error if violated):
> At least one of: `taxId`, `bundleIdentifier`, `bundleName` (≥3 chars), or `billingAddress` (with Zip OR State+City) must be present.

### 3.2 Removing the limit — pagination strategy

The current DataRaptor's `LIMIT 500` is replaced. The platform ceilings stay (we don't fight them):

| Concern | Approach |
|---|---|
| Tell the user how many matches exist | Apex returns `totalAvailable` (separate `COUNT()` query) before any rows |
| Deep paging | Cursor-based (we serialize `lastRecordId` of the previous page; next-page query = `WHERE Id > :lastRecordId ORDER BY Id`) — sidesteps the 2,000 OFFSET ceiling and uses indexed reads |
| Prevent runaway broad searches | Filter precision rule above; if `totalAvailable > 2000` show a banner asking the user to narrow filters; results past 2000 still paginable but flagged |
| Heap and timeout | Page size 50 (default), cap 200; per-page query touches at most 200+1 rows |
| Bulk export (rare) | **Out of scope for v1.** Listed as a follow-up: "Export results to CSV via Batch Apex → ContentDocument download" |

### 3.3 LWC composition (final)

```
prmBundleSearch                 (parent — extends OmniscriptBaseMixin)
├── prmBundleFilterPanel        (form: Tax ID, Bundle ID, Bundle Name, Bundle Type,
│                                Effective on, Billing Address sub-form)
├── c-prm-enhanced-datatable    (REUSED, server-paged via "Load next 50" button)
├── prmBundleSearchPaginator    (Prev / Next / "Load more" + totalAvailable banner)
└── prmBundleSearchEmptyState   (variants: no-search-yet, zero-results,
                                 over-2000 narrow-down hint)
```

### 3.4 Apex contract — `PRM_PracticeLocationBundleSearch.searchBundles`

Identical to the contract in §5 of the previous plan iteration. Recap:

```
@AuraEnabled(cacheable=false)
public static String searchBundles(String filtersJson)
   // input fields:
   //   taxId, bundleIdentifier, bundleNameLike, bundleTypes[],
   //   billingAddress: { addressLine1Like, city, state, zip },
   //   effectiveOn, pageSize, cursor, sortBy, sortDir
   // output:
   //   { totalAvailable, pageNumber, pageSize, hasMore, cursor,
   //     errorMessage, results: [BundleResultDTO...] }
   // BundleResultDTO:
   //   BundleId, BundleName, BundleIdentifier, BundleTaxId,
   //   BundleType, EffectiveFrom, EffectiveTo, ActiveCapExists,
   //   HCFBundleAssociationsCount,
   //   MatchingBillingAddress: { AddressLine1, City, State, Zip }   (only when address filter used)
```

### 3.5 WS-2 file inventory

| # | File | Type | Purpose |
|---|---|---|---|
| 1 | `force-app/main/default/lwc/prmBundleSearch/*` | LWC | Orchestrator |
| 2 | `force-app/main/default/lwc/prmBundleFilterPanel/*` | LWC | Filter form |
| 3 | `force-app/main/default/lwc/prmBundleSearchPaginator/*` | LWC | Cursor-paged controls + total banner |
| 4 | `force-app/main/default/lwc/prmBundleSearchEmptyState/*` | LWC | Variants |
| 5 | `force-app/main/default/classes/PRM_PracticeLocationBundleSearch.cls` (+ `Test`) | Apex | Controller |
| 6 | `force-app/main/default/classes/PRM_PracticeLocationBundleSearchHelper.cls` | Apex | Query helpers (with sharing, WITH USER_MODE) |
| 7 | (new) `vlocity_export/OmniScript/PRM_SelectPracticeLocationBundle_English/PRM_SelectPracticeLocationBundle_English_Element_BundleSearchLWC.json` | OS element | Custom LWC element on `SelectBundle` step |
| 8 | (modify) `..._Element_PracticeLocationBundle.json`, `..._Element_DRTypeAheadGetPracticeLocationBundles.json` | OS elements | `IsActive: false` |
| 9 | (modify) `force-app/main/default/omniScripts/PRM_SelectPracticeLocationBundle_English_5.os-meta.xml` | OS wrapper | Bump to v6 |

### 3.6 WS-2 helper-method routing

| Filter combination | Helper path | Cap per page | Notes |
|---|---|---|---|
| `bundleIdentifier` | `findByBundleIdentifier` | 5 | Exact match, unique |
| `taxId` | `findByTaxId` | 200 | Worst case 32 hits in QA |
| `bundleNameLike` only | `findByBundleNameLike` | 200/page, no hard cap | Cursor-paged |
| `billingAddress` only | `findByBillingAddress` | 200/page, no hard cap | Address sub-query → distinct bundles |
| Combined | Compose (intersect on Bundle Id) | 200/page | All filters AND-combined |

### 3.7 WS-2 testing strategy

#### Apex (`PRM_PracticeLocationBundleSearchTest`)
- Tax ID returns up to 32 bundles
- Bundle Identifier returns 0 or 1
- Billing Address with Zip `07003` returns the bundles whose member PL is at 194 Broad St, Bloomfield NJ
- Combined Tax ID + Billing Address Zip narrows to 1
- Cursor pagination: page 1 of 50, page 2 of 50 — no overlap, correct ordering
- `totalAvailable` matches `Σ pages.length` for any filter set
- Filter precision rule: empty filters → friendly error, no SOQL run
- `WITH USER_MODE` enforced

#### LWC (`prmBundleSearch.test.js`)
- Mounts with no inbound props → search disabled
- User enters Tax ID → search enabled → Apex called once
- Apex returns 5 results → user selects → `omniApplyCallResp` called with same node names today's typeahead writes (`BundleId`, `BundleName`, `BundleTaxId`, etc.)
- Apex returns 0 results → empty-state component rendered
- Apex returns >2000 → banner shown
- Address filter without Zip / State+City → client-side validation prevents Apex call

#### Manual / integration QA
1. End-to-end ManagePracticeLocationBundles → "Remove from Existing Bundle" → search by Tax ID 232266054 → returns 25 bundles → select → confirm downstream IP receives correct `BundleId`.
2. Same flow, search by Billing Address (Zip 07003) → returns matching bundle.
3. Performance: search with name LIKE "Hospital" → totalAvailable likely 50–100 → pagination returns each page in <1.5 s.
4. Back-navigation: select a bundle → click Previous → click Next → selection still highlighted.

### 3.8 WS-2 effort estimate

Same as the previous plan iteration: **~7 dev-days**.

---

## 4. WS-3 — Decommission `PRMGetPracticeLocationBundles` DataRaptor (HOUSEKEEPING)

After WS-2 is in production for one cycle:
- Set the DataRaptor inactive
- Verify no other OmniScripts / IPs reference it (`PRM_AttestationFlow`, `PRM_PDMManualUpdate`, ad-hoc DRs — `Grep`)
- Delete the `_DataPack.json` and metadata files in a follow-up cleanup PR

Estimated: **~0.5 day** (mostly verification).

---

## 5. Sequencing

```
                     ┌──────────────────────────────────────────────┐
                     │ Provider Contracting / Network Mgmt decisions │
                     │   - Path Q vs Path F for B-2 (§2.5)          │
                     │   - B-1 permission gating (§2.6)             │
                     │   - Audit object Y/N (§2.7 #12)              │
                     └──────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
   WS-1 Apex+DR                  WS-2 Apex+helper                 (parallel)
        ▼                              ▼
   WS-1 LWC                       WS-2 LWCs
        ▼                              ▼
   WS-1 OS rewiring              WS-2 OS rewiring (v6)
        ▼                              ▼
   WS-1 UAT                      WS-2 UAT
        ▼                              ▼
        ▼                              ▼
        └─────────────────► merge to release branch ─► production
                                       │
                                       ▼
                                 WS-3 cleanup
```

WS-1 and WS-2 are independent and can run in parallel after the Provider Contracting decisions land. WS-1 is higher priority and should ship first if a tradeoff is required.

---

## 6. Open questions for stakeholders (decision log)

| # | Question | Owner | Required before |
|---|---|---|---|
| 1 | Path Q (queue + wait for QC) vs Path F (synchronous remove) for the B-2 branch in WS-1 §2.5 | Provider Contracting + Network Mgmt QC | WS-1 dev start |
| 2 | Permission set gating for B-1 (update for all PLs in bundle) — PDM Admins only or also PDM Specialists | Provider Data Management ops lead | WS-1 dev start |
| 3 | Need for a dedicated `PRM_BundleBillingAddressAudit__c` audit object beyond standard Field History tracking | Network Mgmt QC + Compliance | WS-1 dev start, but can default to "no" and add later |
| 4 | Billing-address-match strictness for WS-2: City `=` exact vs `LIKE` contains | Provider Data Management ops lead | WS-2 dev start |
| 5 | Address effective-date semantics for WS-2: match the address active *today* vs *as of bundle effective date* (default: today) | PDM ops lead | WS-2 dev start |
| 6 | CSV export for "all bundles for Tax ID X" — needed for v1 or follow-up | Ops lead | Can defer |
| 7 | If a bundle has 0 *other* members (i.e., the current PL is the only PL in it), does B-2 ("remove this PL") effectively dissolve the bundle? Should the system also deactivate the empty bundle or leave the shell? | Provider Contracting | WS-1 dev start |

---

## 7. Source-of-truth references

### WS-1 / Bug fix
- Validation gate: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError.json`
- Buggy formula: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_BundleError.json`
- Trigger that writes the wrong flag: `force-app/main/default/classes/PRM_ProgramParticipationTriggerHandler.cls`
- Existing remove-from-bundle IP wrapper (creates Case + Application): `vlocity_export/IntegrationProcedure/PRM_ManageHCFBundleAssParents/*`
- Existing inner remove-from-bundle IP: `vlocity_export/IntegrationProcedure/PRM_ManageHCFBundleAndAssociations/*`
- Batch Apex doing the actual termination: `PRM_OmniUtils.terminateHCFBundleAssocationsBatch` → `PRM_HCFBundleAssociationBatch`

### WS-2 / Search redesign
- Bundle typeahead element: `vlocity_export/OmniScript/PRM_SelectPracticeLocationBundle_English/PRM_SelectPracticeLocationBundle_English_Element_PracticeLocationBundle.json`
- DR action wired to typeahead: `..._Element_DRTypeAheadGetPracticeLocationBundles.json`
- Legacy DR (with the 500 cap): `vlocity_export/DataRaptor/PRMGetPracticeLocationBundles/PRMGetPracticeLocationBundles_Items.json`
- Reference LWC pattern: `force-app/main/default/lwc/prmProviderLocationSearch/*`
- Reference Apex service pattern: `force-app/main/default/classes/PRM_PARProviderSearch.cls` + `PRM_ProviderSearchHelper.cls`
- Reusable datatable: `force-app/main/default/lwc/prmEnhancedDatatable/*`
- Reusable utilities: `force-app/main/default/lwc/prmGenericSearchInput/*`, `prmExceptionLoggerUtil/*`, `prmOmniUtils/*`

### Live data anchors (QA, fetched 2026-05-04 / 2026-05-05)
- Reproducible Lauren Rosen HCF: `0klUW0000001Nu8YAE` (NPI 1487320776, Account 001UW00000ejOESYA2)
- Active capitated bundles: 1,577 (of 1,582 active bundles total)
- Distinct Tax IDs across active bundles: 1,209 (max 32 bundles for one Tax ID — `223537011` Advocare)
- Active billing-tagged addresses: 336,317 (`Address.PRM_AddressType__c INCLUDES 'Billing'` + `PRM_Active__c=true`)
- Total active addresses: 577,741
- Address-to-HCF join shape: `Address.ParentId → Location.Id ← HealthcareFacility.LocationId`
