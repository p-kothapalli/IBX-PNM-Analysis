# USER STORY: PDM — Billing Address Update Must Only Block When Practice Location Is Actually In An Active Capitated Bundle

> ## ✅ CLEARED FOR PICKUP — Decision resolved 2026-06-22
>
> **Confirmed business rule (from PDM business owner):**
>
> > A Practice Location is in a capitated bundle if-and-only-if there is a **Practice Location Taxonomy (HFN — sObject `HealthcareFacilityNetwork`, label "Practice Location Summary")** on that PL that is **simultaneously**:
> > 1. Referenced from a `PRM_HealthcareFacilityBundleAssociation__c` row (HFBA) where the parent `PRM_HealthcareFacilityBundle__c` is active and `PRM_BundleType__c = 'Capitated Bundle'`, **AND**
> > 2. Linked to an active `PRM_ProgramParticipation__c` whose `PRM_Program__r.PRM_ProgramType__c = 'CAP'`.
>
> Designated Specialty Bundle / Designated Specialty Bundle Network records on `PRM_HealthcareFacilityAssociation__c` (HFA) are **explicitly out of scope** — they encode referral relationships, not co-tenancy bundles, and do not carry the shared-billing-address invariant.
>
> **Verified controls (QA, 2026-06-22):**
> - Negative: HCF `0klUW0000001Nu8YAE` (Lauren Rosen) → conjunction count `0` → unblocked.
> - Positive: HCF `0klUW0000001E0SYAU` (LABORATORY CORPORATION OF AMERICA HOLDINGS, HFN `0bYUW000000XTDD2A4`) → conjunction count `1` → remains blocked.
>
> **Population impact:** 8,358 of today's 9,368 currently-blocked HCFs are released by the new rule; 1,010 remain correctly blocked.
>
> Decision brief: [`./PDM_BillingAddress_Bundle_Invariant_Decision_Brief.md`](./PDM_BillingAddress_Bundle_Invariant_Decision_Brief.md).

**Persona:** PDM Specialist
**Priority:** P0 (Business Unblocker)
**Type:** Bug Fix
**OmniScript:** `PRM_PDMManualUpdate_English` (current active version: v44 → bump to v45)
**Integration Procedures:** N/A (no IP changes in this story)
**DataRaptors (existing — read):** `PRMDRExtractVendorPracticeLocations` (populates the stale `Facility:IsCapitated` field — kept untouched, see Notes)
**Apex (new):** `PRM_PDMBundleMembershipService` — `@AuraEnabled` method `getActiveCapitatedBundleCount(Id facilityId)` returning `Integer` (count of HFNs on the HCF that satisfy the conjunction). Apex is preferred over a DataRaptor here because the rule requires a semi-join across two child sObjects (HFBA + PP) keyed off the same HFN; that pattern is awkward in Vlocity DR builders and trivially expressible (and unit-testable) in Apex.
**Apex (existing — context only, no change):** `PRM_ProgramParticipationTriggerHandler.isParticipatingInCapitatedProgram()` (this trigger writes `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c` based on CAP `PRM_ProgramParticipation__c` rows; it is NOT touched by this story)
**Relevant Requirements:**
- Investigation → [`../PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md`](../PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md)
- Larger build-ready plan → [`../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md`](../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md) (this story is the minimum unblock; WS-1 inline-panel and WS-2 bundle-search redesigns ship separately)
- Reproducing record (QA): `HealthcareFacility` Id `0klUW0000001Nu8YAE` — "Lauren Rosen Wellness LLC", NPI `1487320776`, Account `001UW00000ejOESYA2`

---

## Story

**As a** PDM Specialist,
**I want** to update the billing address of a Practice Location that is **not actually part of any active capitated bundle**, even if the location is flagged as participating in a capitated program,
**So that** I can complete routine billing-address maintenance without being blocked by a misleading error that points me to a bundle that does not exist.

**Why it matters:** Today the PDM Manual Update flow blocks **every** billing-address update for a Practice Location whose `PRM_ParticipatesInCapitatedProgram__c` flag is `true`, and tells the user to "remove the Practice Location from the Bundle." For PLs that are flagged as capitated *because of a CAP program participation* but are **not members of any Practice Location Bundle** (the reproducing Lauren Rosen case has 0 rows in both `PRM_HealthcareFacilityAssociation__c` and `PRM_HealthcareFacilityBundleAssociation__c` despite the flag being `true`), the user cannot satisfy the error — there is no bundle to remove from. The user is stuck, and the only workaround today is to ask Provider Contracting to end-date a CAP Program Participation record, which has unrelated downstream consequences. The fix gates the validation on actual bundle membership while preserving the business invariant ("PLs in a capitated bundle share the same billing address") for PLs that really are in a bundle.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| PDM Manual Update | `PRM_PDMManualUpdate_English` | "Update Billing and/or Mailing address" | New Apex `PRM_PDMBundleMembershipService.getActiveCapitatedBundleCount(facilityId)` invoked from a Remote Action element; result populates `Facility:ActiveCapitatedBundleCount` consumed by the `BundleError` formula. |

**In scope:**
- Replace the data field the `BundleError` formula reads from (today: `Facility:IsCapitated` from `PRM_ParticipatesInCapitatedProgram__c`; new: `Facility:ActiveCapitatedBundleCount` from the **HFBA + CAP-PP-per-HFN conjunction** described in the Cleared-for-Pickup banner).
- Add a new Apex class `PRM_PDMBundleMembershipService` and a new OmniScript Remote Action element that calls it.
- Rewrite the `PracticeLocationInActiveBundleError` validation message to be honest about the actual user action (it remains a block when the PL really is in a bundle).
- Bump the OmniScript active version.

**Out of scope (covered by separate stories in the larger plan):**
- The inline "Update for all PLs in the bundle vs. Remove and update only this PL" choice panel (planned as a follow-up enhancement story under WS-1 of the implementation plan).
- The Filter+List bundle search redesign for `PRM_SelectPracticeLocationBundle_English` (WS-2 of the implementation plan).
- Any changes to `PRM_ProgramParticipationTriggerHandler` or the `PRM_ParticipatesInCapitatedProgram__c` field itself.
- Any data backfill or cleanup of HCFs that today have stale `PRM_ParticipatesInCapitatedProgram__c=true` but no bundle membership.

---

## Current State (from codebase)

### OmniScript element — `PRM_PDMManualUpdate_English_Element_BundleError.json`
- Type: Formula
- Current expression: `AND(%Facility:IsCapitated% == true, CONTAINS(%AddressActionType%, "Billing"))`
- `Facility:IsCapitated` is sourced upstream from DataRaptor `PRMDRExtractVendorPracticeLocations` which maps `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c → Facility:IsCapitated` (see `force-app/main/default/omniDataTransforms/PRMDRExtractVendorPracticeLocations_1.rpt-meta.xml` lines 914–925).
- That field is **not** a measure of bundle membership; it is a CAP-program-participation flag written by `PRM_ProgramParticipationTriggerHandler.isParticipatingInCapitatedProgram()` whenever the HCF has any active `PRM_ProgramParticipation__c` row with `PRM_Program__r.PRM_ProgramType__c = 'CAP'`.

### OmniScript element — `PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError.json`
- Type: Validation
- `show.group.rules`: `field=BundleError, condition="=", data="true"` (renders the error when the formula above is true).
- `validateExpression.group.rules`: `field=BundleError, condition="=", data="false"` (blocks the Next button).
- Message text today: *"The Practice Location selected is a part of a Capitated Practice Location Bundle, remove Practice Location from the Bundle before proceeding."*

### Live data — reproducing record `0klUW0000001Nu8YAE` (Lauren Rosen Wellness LLC, QA, last verified 2026-06-22)

| Source | Filter / Value | Result |
|---|---|---|
| `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c` | flag value | **true** ← drives today's stale error |
| `HealthcareFacilityNetwork` (HFNs on this HCF) | `WHERE HealthcareFacilityId='0klUW0000001Nu8YAE' AND IsActive=true` | 59 active HFNs |
| HFNs satisfying **HFBA condition** (referenced from active capitated HFBA row) | the HFBA semi-join below | **0** |
| HFNs satisfying **CAP-PP condition** (have active CAP `PRM_ProgramParticipation__c`) | only one — `0bYUW000000VWwj2AG` (PPA-44783, Capitation-PRIMARY CARE PHYSICIAN) | 1 |
| **HFNs satisfying BOTH** (the conjunction = the rule) | per the rule | **0** |
| Conjunction count returned by `PRM_PDMBundleMembershipService.getActiveCapitatedBundleCount` | new service | **0** |

The PL is **not in any Practice Location Bundle**, yet the legacy validation tells the user to remove it from one. The new conjunction correctly returns 0 → the new rule unblocks her.

### Live data — positive-control record `0klUW0000001E0SYAU` (LABORATORY CORPORATION OF AMERICA HOLDINGS — Pine Hollow Rd, QA, 2026-06-22)

Used as the AC-2 / regression positive case.

| Source | Filter / Value | Result |
|---|---|---|
| HFN under inspection | `0bYUW000000XTDD2A4` (RT `PRM_FacilityTx`, IsActive=true, Effective 2022-10-11) | active |
| **HFBA condition** | `a1iUW00000EezLUYAZ` → "LabCorp of America Bundle" (`PRM_BundleType__c='Capitated Bundle'`, `PRM_Active__c=true`, HFBA `PRM_Active__c=true`, eff. 2024-05-01) | satisfied |
| **CAP-PP condition** | `a26UW000000leYuYAI` → PPA-46355 "Capitation-LAB FUND" (`PRM_Program__r.PRM_ProgramType__c='CAP'`, `PRM_Active__c=true`, eff. 2022-10-11) | satisfied |
| Conjunction count returned by `PRM_PDMBundleMembershipService.getActiveCapitatedBundleCount` | new service | **1** → blocks correctly |

### Org-wide volumes (QA, 2026-06-22)

| Metric | Value |
|---|---|
| Active capitated bundles | 131 |
| Active capitated HFBA rows with non-null HFN-resolved HCF | 3,010 |
| Distinct HCFs satisfying the **confirmed conjunction** rule | **1,051** |
| Of today's 9,368 flagged-and-blocked HCFs: still blocked under the new rule | **1,010** |
| Of today's 9,368 flagged-and-blocked HCFs: **released** by the new rule | **8,358** |

### Reference SOQL (Apex semi-join shape used by the new service)

```sql
SELECT COUNT()
FROM   PRM_HealthcareFacilityBundleAssociation__c
WHERE  PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId = :facilityId
  AND  PRM_Active__c = true
  AND  PRM_HealthcareFacilityBundle__r.PRM_Active__c = true
  AND  PRM_HealthcareFacilityBundle__r.PRM_BundleType__c = 'Capitated Bundle'
  AND  PRM_PracticeLocationTaxonomy__c IN (
        SELECT PRM_HealthcareFacilityNetwork__c
        FROM   PRM_ProgramParticipation__c
        WHERE  PRM_Active__c = true
          AND  PRM_Program__r.PRM_ProgramType__c = 'CAP'
       )
```

---

## Technical Section (For Developers)

> **Selected approach: gate the existing validation on the confirmed HFBA + CAP-PP-per-HFN conjunction, computed by a new Apex service.** The validation stays in place (so genuine bundle-member PLs are still protected by the "same billing address" invariant); the gate now reads from accurate, conjunction-derived data. A new OmniScript Remote Action element runs on entry to the step and writes the count into an OmniScript node the formula consumes.

### Why Apex (not a DataRaptor)

The rule expressed in the Cleared-for-Pickup banner is a semi-join across two sibling child sObjects (`PRM_HealthcareFacilityBundleAssociation__c` and `PRM_ProgramParticipation__c`) keyed off the same parent `HealthcareFacilityNetwork`. Vlocity DataRaptor Extract supports parent/child traversal but not arbitrary `IN (subquery)` semi-joins; expressing the rule in a DR would require a multi-extract chain plus a Formula step to do the set intersection, which is fragile and hard to unit-test. A 25-line Apex method is dramatically simpler, fully unit-testable, and exposes a single integer result the OmniScript can consume directly.

### ⚠️ Schema gotcha — `PRM_HealthcareFacility__c` is null on HFBA / HFA in this org

`PRM_HealthcareFacilityBundleAssociation__c` has both:

- a direct lookup `PRM_HealthcareFacility__c → HealthcareFacility`, and
- an indirect path `PRM_PracticeLocationTaxonomy__c → HealthcareFacilityNetwork.HealthcareFacilityId → HealthcareFacility`.

In the QA org **the direct lookup field `PRM_HealthcareFacility__c` is null on every row**, including all 3,010 active rows in active capitated bundles. The HCF reference lives **only** through the `PRM_PracticeLocationTaxonomy__c` (HFN) traversal. A filter of the form `WHERE PRM_HealthcareFacility__c = :facilityId` will return zero for every PL — including PLs that genuinely are in a bundle — silently breaking the bundle-invariant guard. The Apex method below traverses via HFN. If a future schema cleanup populates the direct lookup, revisit this story before changing the query.

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `force-app/main/default/classes/PRM_PDMBundleMembershipService.cls` (and `.cls-meta.xml`) | **NEW** Apex class | Public class with one `@AuraEnabled(cacheable=false)` method `Integer getActiveCapitatedBundleCount(Id facilityId)`. Implementation runs the SOQL shown in the Live data section above. Returns the row count (an integer ≥ 0). Decorate with `with sharing` and short-circuit return `0` when `facilityId` is null. |
| `force-app/main/default/classes/PRM_PDMBundleMembershipServiceTest.cls` | **NEW** Apex test | Unit tests covering: (a) HCF with HFN that has both HFBA + CAP PP → returns 1+; (b) HCF with HFN in HFBA but no CAP PP → returns 0; (c) HCF with HFN with CAP PP but no HFBA → returns 0; (d) HCF with neither → returns 0; (e) HCF with multiple HFNs where conjunction holds on a subset → returns the correct count; (f) bundle exists but `PRM_BundleType__c != 'Capitated Bundle'` → returns 0; (g) inactive bundle / inactive HFBA / inactive PP → returns 0; (h) null `facilityId` → returns 0. ≥90% coverage. |
| `PRM_PDMManualUpdate_English` → step **"Update Billing and/or Mailing address"** → **new element** `RAGetActiveCapitatedBundleCount` | **NEW** OmniScript element (Remote Action) | Calls `PRM_PDMBundleMembershipService.getActiveCapitatedBundleCount` with `{facilityId: %Facility:FacilityId%}`. Writes the integer return into `Facility:ActiveCapitatedBundleCount`. Placed **before** the `BundleError` formula evaluates and before the `PracticeLocationInActiveBundleError` validation renders. `validationRequired: "Step"`. Hidden / persistent. The Remote Action element type matches the pattern already used elsewhere in the OmniScript (e.g., `RATerminateHCFBundleAssocationsBatch` calling `PRM_OmniUtils.TerminateHCFBundleAssocationsBatch`). |
| `PRM_PDMManualUpdate_English_Element_BundleError.json` (Formula) | **MODIFY** | Change `expression` from `AND(%Facility:IsCapitated% == true, CONTAINS(%AddressActionType%, "Billing"))` to `AND(%Facility:ActiveCapitatedBundleCount% > 0, CONTAINS(%AddressActionType%, "Billing"))`. No other property changes. |
| `PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError.json` (Validation) | **MODIFY** | Rewrite the active message under `messages` to: *"This Practice Location is a member of an active Capitated Practice Location Bundle. Every Practice Location in a capitated bundle must share the same billing address. Before changing this location's billing address, use **Manage Practice Location Bundles → Remove from Existing Bundle** to remove this Practice Location from the bundle, or contact Provider Contracting if the address should change for all locations in the bundle."* No other property changes. |
| `force-app/main/default/omniScripts/PRM_PDMManualUpdate_English_44.os-meta.xml` | **VERSION BUMP** | Activate a new `_45` version with the modifications above. Keep v44 inactive but version-controlled for rollback. |

### Apex skeleton (for reviewer reference, not final code)

```apex
public with sharing class PRM_PDMBundleMembershipService {

    @AuraEnabled(cacheable=false)
    public static Integer getActiveCapitatedBundleCount(Id facilityId) {
        if (facilityId == null) {
            return 0;
        }
        Integer count = [
            SELECT COUNT()
            FROM   PRM_HealthcareFacilityBundleAssociation__c
            WHERE  PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId = :facilityId
              AND  PRM_Active__c = true
              AND  PRM_HealthcareFacilityBundle__r.PRM_Active__c = true
              AND  PRM_HealthcareFacilityBundle__r.PRM_BundleType__c = 'Capitated Bundle'
              AND  PRM_PracticeLocationTaxonomy__c IN (
                    SELECT PRM_HealthcareFacilityNetwork__c
                    FROM   PRM_ProgramParticipation__c
                    WHERE  PRM_Active__c = true
                      AND  PRM_Program__r.PRM_ProgramType__c = 'CAP'
                  )
        ];
        return count;
    }
}
```

Effective-date filtering on HFBA (`PRM_EffectiveFrom__c <= TODAY` etc.) is intentionally **not** included in the v1 query because the rule statement received from the business owner only requires `PRM_Active__c = true`. If post-deploy review reveals a need for the date guard, it's a one-line addition. (See Clarification Question 3.)

### Notes
- The `Facility:IsCapitated` node is **not** removed from the OmniScript — it may be consumed by other elements (e.g. effective-date error blocks `EffectiveFromBundleError`, `EffectiveToBundleError`, the `SECapitatedEffectiveErrors` Set Errors element). Removing it is explicitly out of scope; see Clarification Question 1.
- `PRM_ProgramParticipationTriggerHandler` is **unchanged**. The CAP-program flag continues to drive other logic.
- The query's selectivity comes from `PRM_PracticeLocationTaxonomy__c` (indexed) and the bounded HFN cardinality per HCF (Lauren is the upper end at 59 HFNs; typical PCPs have 1–10). The semi-join `IN (SELECT ...)` is on `PRM_HealthcareFacilityNetwork__c` of `PRM_ProgramParticipation__c`, also indexed. No pagination or governor-limit concerns expected.
- The validation **remains a hard block** when a PL really is in a capitated bundle — the bundle invariant is preserved. Only the previously-blocked-but-not-actually-bundled population (Lauren-class, 8,358 HCFs in QA) is released.
- `PRM_BundleType__c` distribution check (QA, 2026-06-22): all 131 active bundles are `'Capitated Bundle'`. The literal is hard-coded in the Apex for forward-compatibility with future bundle types. If a new bundle type is introduced that should also share-billing-address, the filter must be updated — flagged in the Clarification Questions below.

---

## Acceptance Criteria

**AC-1 — Billing-address update proceeds when the Practice Location is in zero active capitated bundles**

**Given** a PDM Specialist opens the "Update Billing and/or Mailing address" step in the PDM Manual Update flow for a Practice Location that is **not** a member of any active capitated Practice Location Bundle (including locations that are flagged as participating in a capitated program but have no actual bundle membership, such as the reproducing record `0klUW0000001Nu8YAE`),
**When** the specialist selects "Update Billing Address" and clicks Next after entering a valid new billing address,
**Then** the step advances to the next step of the flow without showing the capitated-bundle error,
**And** no validation message about removing the location from a bundle is rendered.

**AC-2 — Billing-address update is still blocked when the Practice Location satisfies the confirmed conjunction (HFBA + CAP-PP-per-HFN)**

**Given** a PDM Specialist opens the "Update Billing and/or Mailing address" step for a Practice Location that has at least one active HFN that is **simultaneously** referenced from an active `PRM_HealthcareFacilityBundleAssociation__c` row pointing to an active `'Capitated Bundle'` AND linked to an active CAP `PRM_ProgramParticipation__c` row (verified positive control: HCF `0klUW0000001E0SYAU` "LABORATORY CORPORATION OF AMERICA HOLDINGS"),
**When** the specialist selects "Update Billing Address" and clicks Next,
**Then** the step displays a validation message explaining that the location is in a capitated bundle and that the billing address cannot be changed without first removing the location from the bundle (or contacting Provider Contracting to change the address for the whole bundle),
**And** the Next button does not advance the flow,
**And** the message names the screen the specialist should use to perform the removal ("Manage Practice Location Bundles → Remove from Existing Bundle").

**AC-3 — Mailing-only updates are never blocked by this validation**

**Given** a PDM Specialist opens the "Update Billing and/or Mailing address" step for **any** Practice Location (regardless of whether it is in a capitated bundle),
**When** the specialist selects "Update Mailing Address" (with no Billing change) and clicks Next,
**Then** the capitated-bundle validation does not fire,
**And** the flow advances normally.

**AC-4 — Combined mailing + billing update obeys the same rule as billing-only**

**Given** a PDM Specialist opens the "Update Billing and/or Mailing address" step,
**When** the specialist selects "Update Mailing and Billing Address",
**Then** the capitated-bundle validation behaves identically to selecting "Update Billing Address" alone (blocks if-and-only-if the location is in one or more active capitated bundles).

**AC-5 — The new validation message tells the user exactly where to go and what to do**

**Given** the validation fires (per AC-2 or AC-4),
**When** the message is shown,
**Then** the message identifies the screen the specialist should open ("Manage Practice Location Bundles") and the action to choose ("Remove from Existing Bundle"),
**And** the message also names an alternate path for the case where the billing address should change for every location in the bundle ("contact Provider Contracting"),
**And** the message does not reference the legacy phrasing "remove Practice Location from the Bundle before proceeding".

**AC-6 — Reproducing case ends-to-end**

**Given** a PDM Specialist opens the PDM Manual Update flow for the QA reproducing record HCF `0klUW0000001Nu8YAE` ("Lauren Rosen Wellness LLC"),
**When** the specialist selects "Update Billing Address", enters a new valid billing address, and clicks Next,
**Then** the flow advances past the "Update Billing and/or Mailing address" step without firing the capitated-bundle validation,
**And** the user can complete the manual-update submission.

**AC-7 — Effective-date validations on the same step are unchanged**

**Given** a PDM Specialist is on the "Update Billing and/or Mailing address" step for a Practice Location that participates in a CAP program (regardless of bundle membership),
**When** the specialist enters an Effective From or Effective To date that would fail the existing capitated-program effective-date rules,
**Then** the existing effective-date validation messages still fire as they do today (this story does not change the effective-date logic),
**And** the user is blocked from advancing until the dates are corrected, consistent with the current behaviour driven by `SECapitatedEffectiveErrors`.

---

## Definition of Done

- [ ] New Apex class `PRM_PDMBundleMembershipService` deployed to QA, with `getActiveCapitatedBundleCount(Id)` returning **0** for HCF `0klUW0000001Nu8YAE` (Lauren Rosen — negative control) and **≥1** for HCF `0klUW0000001E0SYAU` (LABORATORY CORPORATION OF AMERICA HOLDINGS — positive control with HFN `0bYUW000000XTDD2A4` satisfying the conjunction via "LabCorp of America Bundle" + "Capitation-LAB FUND").
- [ ] `PRM_PDMBundleMembershipServiceTest` covers the eight test cases listed in the Technical Section with ≥90% coverage and all assertions green.
- [ ] Code review checklist confirms: (a) the SOQL traverses `PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId`; (b) it does **not** filter on `PRM_HealthcareFacility__c`; (c) the semi-join `IN (SELECT PRM_HealthcareFacilityNetwork__c FROM PRM_ProgramParticipation__c …)` is preserved; (d) `with sharing` is declared; (e) null-input short-circuit returns 0.
- [ ] OmniScript `PRM_PDMManualUpdate_English` v45 active in QA with the modifications above; v44 inactive and version-controlled for rollback.
- [ ] AC-1 through AC-7 manually verified in QA against both the reproducing HCF and the LabCorp positive-control HCF.
- [ ] Existing PDM Manual Update regression suite passes (Mailing-only update, Billing-only update for a non-capitated PL, combined update, effective-date validations).
- [ ] Release notes entry calling out the message wording change for PDM Specialists.
- [ ] Rollback plan documented: reactivate v44 OmniScript if a defect is discovered post-deploy; the new Apex class can remain (it is read-only, additive, and unused by other components).
- [ ] Pre-deploy data audit re-run on release day confirms: ~8,358 HCFs released and ~1,010 still blocked, matching the 2026-06-22 baseline within ±5%; any larger drift halts the release.

---

## Clarification Questions (Before Implementation)

> The core rule question (HFBA-only vs. HFBA+HFA) was resolved 2026-06-22 — see the Cleared-for-Pickup banner. Remaining questions are scoped to wording, edge cases, and rollout mechanics.

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the `Facility:IsCapitated` node remain in the OmniScript (consumed by `EffectiveFromBundleError`, `EffectiveToBundleError`, `SECapitatedEffectiveErrors`, and possibly other effective-date validations) or is it acceptable to leave it as a vestigial CAP-program-participation indicator? | Determines whether this story is purely additive to the formula gate or also touches downstream effective-date validation elements. **Recommendation: leave `Facility:IsCapitated` unchanged in v1**; revisit when WS-1 (inline panel) story is built. | Technical / BA |
| 2 | Final wording of the AC-5 validation message — does Provider Contracting prefer "Manage Practice Location Bundles → Remove from Existing Bundle" or a different action name? Should the message link to a specific case template / form for the "contact Provider Contracting" path? | Affects the exact text used in the modified validation element; cosmetic but customer-facing. | Product / Provider Contracting |
| 3 | Does the conjunction need to add an effective-date guard (`PRM_EffectiveFrom__c <= TODAY` / `PRM_EffectiveTo__c >= TODAY OR null`) on the HFBA row and/or the `PRM_ProgramParticipation__c` row? The confirmed rule statement only mentions `PRM_Active__c = true`. **Recommendation: ship without the date guard for v1**; if post-deploy review surfaces stale-but-active rows that should not block, the date guard is a one-line addition. | Affects edge-case behaviour for future-effective and recently-end-dated bundles/CAP-PPs. | BA / Provider Contracting |
| 4 | Are there ~41 HCFs in QA (1,051 conjunction-positive minus 1,010 flagged-and-blocked) that satisfy the new conjunction but have `PRM_ParticipatesInCapitatedProgram__c=false`? If yes, the new validation will newly-block these PLs that the old validation let through. **Recommendation: list them in a pre-deploy audit and notify PDM Ops** so any in-flight tickets aren't surprised. | Possible regression on a small population (~0.4% of newly-blocked vs. 8,358 newly-released). | Technical / PDM Ops |
| 5 | Should the v45 OmniScript change be feature-flagged (e.g., gated on a custom permission) to allow a phased rollout, or is a hard cut-over acceptable? | Affects deployment plan. Given this is a P0 unblocker and the change is metadata-only with a simple rollback, **recommendation: hard cut-over with the version-bump rollback path**. | Technical / Release Mgmt |
| 6 | Today all 131 active bundles in QA have `PRM_BundleType__c = 'Capitated Bundle'`. If Provider Contracting plans to introduce additional bundle types (e.g. value-based, FFS), should the same "shared billing address" invariant apply to those types? The new Apex hard-codes `'Capitated Bundle'` and would not block billing-address changes for PLs in a non-capitated bundle. **Recommendation: keep equality for v1**; if a new type is introduced, raise a follow-up story to broaden the filter (and re-confirm the conjunction with CAP PP still applies). | Determines whether the filter should be `IN (...)` or stay equality. | BA / Provider Contracting |
| 7 | The `PRM_HealthcareFacility__c` lookup on `PRM_HealthcareFacilityBundleAssociation__c` is null on every row in QA — is this intentional (the field exists but the schema relies on the HFN traversal), the result of a historical data migration, or a data-loader bug to be fixed separately? **Recommendation: treat as permanent for this story**; raise a separate data-quality story if the platform team confirms the lookup should be populated. | Drives whether the Schema gotcha is permanent or temporary. | Technical / Platform |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PDMManualUpdate_English` v45 | OmniScript | **HIGH** | Active version bump; behaviour change on a frequently-used step |
| `PRM_PDMBundleMembershipService` | Apex | **LOW** | New, additive; one read-only `@AuraEnabled` method; nothing else depends on it |
| `PRM_PDMBundleMembershipServiceTest` | Apex test | **LOW** | New; covers the new class only |
| `PRM_PDMManualUpdate_English_Element_BundleError` | OmniScript Formula | **MEDIUM** | Expression rewrite; the node it depends on changes |
| `PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError` | OmniScript Validation | **MEDIUM** | Customer-facing message text change |
| `PRMDRExtractVendorPracticeLocations` / `Facility:IsCapitated` | DataRaptor / OS node | **NONE** | Unchanged; still populated for other consumers |
| `PRM_ProgramParticipationTriggerHandler` / `PRM_ParticipatesInCapitatedProgram__c` | Apex / Custom Field | **NONE** | Unchanged |
| `SECapitatedEffectiveErrors`, `EffectiveFromBundleError`, `EffectiveToBundleError` | OmniScript elements | **NONE** | Unchanged (continue reading `Facility:IsCapitated`) |
| `PRM_SelectPracticeLocationBundle_English` (bundle removal flow) | OmniScript | **LOW** | Indirect: more users will reach this flow under AC-2/AC-5 — usability gap in its typeahead becomes more visible. Mitigated by WS-2 (separate story). |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_PDMBundleMembershipService` | New Apex class | **S** | ~25 lines; one method; one SOQL with semi-join |
| `PRM_PDMBundleMembershipServiceTest` | New Apex test | **M** | 8 test cases per the Technical Section; data-builder helpers for HFN/HFBA/PP |
| New OS element `RAGetActiveCapitatedBundleCount` (Remote Action) | New OmniScript element | **S** | Hidden persistent element with one input mapping; matches the existing `RATerminateHCFBundleAssocationsBatch` pattern in the same OmniScript family |
| `BundleError` formula expression | OmniScript element modify | **S** | One-line expression change |
| `PracticeLocationInActiveBundleError` message wording | OmniScript element modify | **S** | Text-only |
| OmniScript v45 activate / v44 inactivate | Version bump | **S** | Standard activation cycle |
| QA / regression / UAT for AC-1 through AC-7 | Testing | **L** | Includes positive (LabCorp HCF) and negative (Lauren) cases plus the regression on effective-date rules |
| Pre-deploy data audit | Ops/Engineering | **S** | Re-run the population-sizing SOQL on release day; halt on >5% drift |

**Total Estimated Effort:** ~1–1.5 dev-days build + ~0.5 day QA = **~2 dev-days total** (**M overall** — AI-estimated; validate with team)

---

> **Cross-story note:** This is the **minimum unblocker**. The follow-up enhancement story for the inline "Update for all PLs in the bundle vs. Remove and update only this PL" panel (WS-1 in [`../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md`](../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md) §2) and the bundle-search redesign (WS-2 of the same plan) are separate stories and are not blocked by this one. This story can ship independently.
