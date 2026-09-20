# User Story — App Review AAL must honor PENDING primary practice locations

**ID:** US-APPREVIEW-AAL-PENDING
**Date:** 2026-06-15
**Component:** OmniStudio IP `PRM_CreateAdverseActionLog_Procedure` (App Review / Initial Credentialing)
**Type:** Bug fix (config / OmniStudio)
**Priority:** High — blocks App Review submission for new pending practice locations (3,195 addresses org-wide in QA)

---

## Story

**As** a Credentialing case manager submitting the App Review (Initial Credentialing) OmniScript,
**I want** the Adverse Action Log to be created when the practitioner's primary practice location is a
**new, pending** location (awaiting committee approval),
**so that** I can complete submission without hitting
`Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`,
**without** anyone having to (improperly) activate an address that has not been approved.

---

## Background / Current behavior

On App Review submit, `PRM_CreateAdverseActionLog_Procedure` inserts a `PRM_AdverseActionLog__c`.
The four `PRM_Primary*` fields are `required=true` and are populated from the primary practice
location's Primary/Practice address via the `FilterPrimaryAddress` List Merge step:

```
filterListFormula = (Type LIKE "Primary" || AddressMultiType LIKE "Practice") && (Active==true || Pending==true)
```

`FilterPrimaryAddress` runs on `FilterPrimaryPracticeLocation|1:Addresses`, i.e. the addresses of the
location flagged `PrimaryPracticeLoc == true` inside the `locationsToUpsert` screen structure.

## Root cause (confirmed)

The `locationsToUpsert` **address node does not contain a `Pending` key** (verified from the IP's own
runtime payload — the address object has `Active`, `Type`, `AddressMultiType`, etc., but no
`Pending`). Therefore `Pending==true` always evaluates against null/false and the gate collapses to
**`Active==true`**.

Consequence: when the chosen primary practice location is a **new pending location**, its
Primary/Practice address is `Active=false` (correct — it is awaiting committee approval), so the
filter returns nothing → the four required fields are blank → `REQUIRED_FIELD_MISSING`.

The reliable "this is a new pending location" signal is **`HealthcareFacility.PRM_Pending__c = true`**
(and the matching HCPF `PRM_Pending__c`), NOT the address-level flag — the address `Pending` is
frequently drifted to `false` by downstream QC/review saves.

### Evidence (QA, read-only validation `scripts/apex/validate_AppReview_PendingAddressFix.apex`)

| Metric | Count |
|---|---|
| Pending `HealthcareFacility` records | 3,302 |
| Inactive Primary/Practice addresses on pending locations (fail today, recover under fix) | **3,195** |
| ...of which `address.PRM_Pending__c` is **also false** (desynced — only recoverable via facility/location pending) | **745** |

Reported defects validated (primary practice location):

| Practitioner | Case | Facility `Pending` | Addr `Active` | Addr `Pending` | Today | Under fix |
|---|---|:--:|:--:|:--:|:--:|:--:|
| Katherine Santa Maria | IA-0000088944 | true | false | true | FAIL | PASS |
| Lindsey Schaffel | IA-0000148183 | true | false | true | FAIL | PASS |
| Rebecca Harvey | IA-0000120583 | true | false | **false** | FAIL | PASS |
| Tara Lowe | IA-0000124514 | true | false | **false** | FAIL | PASS |
| Brandon Roda | IA-0000092468 | false | true | false | PASS | PASS |
| Dana Vogel | IA-0000094048 | false | true | false | PASS | PASS |

---

## Scope of fix

Single OmniStudio IP: `PRM_CreateAdverseActionLog_Procedure` (active version **8**).
The re-credentialing IP `PRM_IPCreateAdverseActionLog_Procedure` uses a different mechanism and is
**out of scope** (no `FilterPrimaryAddress` filter present).

### Explicitly NOT in scope / NOT acceptable

- ❌ Setting `Address.PRM_Active__c = true` to make the filter pass. Activation is **committee-gated**;
  it must never be used as a workaround or fix.
- ❌ Dropping the `(Active==true || Pending==true)` guard entirely (would let removed/invalid
  addresses through).

---

## Proposed technical design (recommended: Option 1)

**Option 1 — Resolve the primary address from the DB inside the IP, honoring location/facility pending.**

Add a DataRaptor (Extract/Turbo) step to `PRM_CreateAdverseActionLog_Procedure`, keyed on the primary
practice `LocationId` (already available as `%FilterPrimaryPracticeLocation|1:LocationId%`), that
returns the Primary/Practice address joined to its parent location/facility pending+active state, and
selects the address where:

```
(PRM_AddressType__c INCLUDES Primary OR PRM_AddressType__c INCLUDES Practice)
AND ( Address.PRM_Active__c = true
      OR Address.PRM_Pending__c = true
      OR HealthcareFacility.PRM_Active__c = true
      OR HealthcareFacility.PRM_Pending__c = true )
```

Then map the four AAL fields from this DataRaptor instead of `FilterPrimaryAddress`:

```
PrimaryCity  ← <NewDR>:City
PrimaryState ← <NewDR>:State
PrimaryAdd1  ← <NewDR>:AddressLine1
PrimaryAdd2  ← <NewDR>:AddressLine2
PrimaryZip   ← <NewDR>:Zip
PrimaryCounty← <NewDR>:County
```

Rationale: reads DB truth, honors the reliable facility/location pending signal (covers the 745
desynced cases too), needs no address activation and no data surgery, and is contained to one IP
(low blast radius).

**Option 2 (alternative) — Carry address `Pending` into `locationsToUpsert`.**
Fix the upstream PAR/practitioner-form builder so the address node includes
`Pending = Address.PRM_Pending__c`, allowing the existing filter to work. Rejected as primary
approach: (a) higher blast radius (shared form flow), and (b) it would still miss the 745 desynced
addresses whose `address.PRM_Pending__c` is false — those need the facility/location signal.

---

## Acceptance criteria

1. Submitting App Review for a practitioner whose primary practice location is a **new pending**
   location (`HealthcareFacility.PRM_Pending__c = true`) with `Address.PRM_Active__c = false`
   **creates** the `PRM_AdverseActionLog__c` with the four `PRM_Primary*` fields populated from that
   location's Primary/Practice address.
2. Works whether the address `PRM_Pending__c` is `true` (Katherine, Lindsey) or `false`/desynced
   (Rebecca, Tara) — i.e., the location/facility pending signal is honored.
3. Existing passing cases (active primary address — Brandon, Dana) continue to succeed unchanged.
4. **No** `Address` record is activated (`PRM_Active__c` unchanged) by the flow.
5. When the primary practice location genuinely has no Primary/Practice address at all, behavior is a
   clear, handled error (not a raw `REQUIRED_FIELD_MISSING`) — log/short-circuit gracefully.
6. The re-cred flow (`PRM_IPCreateAdverseActionLog_Procedure`) is unaffected.

## Test cases

| # | Setup | Expected |
|---|---|---|
| T1 | Primary loc pending, addr Active=false, Pending=true (Katherine/Lindsey) | AAL created, fields populated |
| T2 | Primary loc pending, addr Active=false, Pending=false desync (Rebecca/Tara) | AAL created, fields populated |
| T3 | Primary loc active, addr Active=true (Brandon/Dana) | AAL created (regression) |
| T4 | Primary loc with no Primary/Practice address | Graceful handled error, no AAL, no DML exception surfaced raw |
| T5 | Verify no `Address.PRM_Active__c` changed after submit in T1/T2 | All address active flags unchanged |

## Validation / rollout

- **Pre-deploy sizing & post-deploy verification:** run
  `scripts/apex/validate_AppReview_PendingAddressFix.apex` (read-only) — Section A confirms the
  reported cases flip FAIL→PASS under the fix; Section B sizes the org-wide backlog (3,195 / 745).
- **Backlog clearance:** after deploy, affected cases are cleared by re-opening and re-submitting App
  Review — **no data migration required**.
- **Deploy:**
  ```bash
  sf project deploy start \
    --source-dir "force-app/main/default/omniIntegrationProcedures/PRM_CreateAdverseActionLog_Procedure_8.oip-meta.xml" \
    --source-dir "force-app/main/default/omniDataTransforms/<NewDataRaptor>.rpt-meta.xml" \
    --target-org qa-sandbox --wait 10
  ```
  Confirm the IP version remains **active** in the OmniStudio designer after deploy.

## Related

- Root-cause analysis: `requirements/PDM Flows/US_AppReview_AAL_MissingPrimaryAddress_RootCause_Fix.md`
- Multi-case audit + SOQL: `requirements/SOQL/2026-06-15_AppReview_AAL_MissingPrimaryAddress_MultiCaseAudit.md`
- Validation script: `scripts/apex/validate_AppReview_PendingAddressFix.apex`
- Diagnostic script: `scripts/apex/diagnose_AppReview_PrimaryAddress.apex`
