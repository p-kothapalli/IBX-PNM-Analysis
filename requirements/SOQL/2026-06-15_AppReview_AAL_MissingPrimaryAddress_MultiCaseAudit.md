# App Review – "Record Creation Failed / Required fields are missing" — Multi-Case Audit

**Date:** 2026-06-15
**Context:** Business reported multiple defects where submitting the App Review (Initial Credentialing)
OmniScript fails on the "Record Creation Failed" step with
`Error : Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`.
This is the standard `REQUIRED_FIELD_MISSING` DML error when the `PRM_CreateAdverseActionLog_Procedure`
IP (v8) inserts a `PRM_AdverseActionLog__c` with blank primary-address fields. Those 4 fields are
`required=true` on the object. Root cause: the practitioner's primary practice location has **no
Active (or Pending) Primary/Practice address**, so the IP's `FilterPrimaryAddress` step drops the
only address and the fields go blank.

Related single-case file: `2026-06-08_AppReview_AdverseActionLog_MissingPrimaryAddress.md`.

Cases audited: IA-0000088944, IA-0000092468, IA-0000094048, IA-0000120583, IA-0000124514.

---

## Query 1 — Resolve reported cases to practitioner accounts

**Object:** `IndividualApplication`

```sql
SELECT Id, Name, AccountId, Account.Name
FROM IndividualApplication
WHERE Name IN ('IA-0000088944','IA-0000092468','IA-0000094048','IA-0000120583','IA-0000124514')
ORDER BY Name
```

## Query 2 — Primary facility + location + facility active status

**Object:** `HealthcarePractitionerFacility`
**Use case:** Find the `IsPrimaryFacility=true` row and whether the facility/location is active.

```sql
SELECT Practitioner.AccountId, Practitioner.Account.Name, Id, IsPrimaryFacility,
       HealthcareFacility.LocationId, HealthcareFacility.PRM_Active__c, HealthcareFacility.Account.Name
FROM HealthcarePractitionerFacility
WHERE Practitioner.AccountId IN ('001UW00000lXetJYAS','001UW0000105zwuYAA','001UW00000zqw9gYAA','001UW000014WJJFYA4','001UW000011XMjpYAG')
  AND IsPrimaryFacility = true
ORDER BY Practitioner.Account.Name
```

## Query 3 — Addresses on each primary location (the filter input)

**Object:** `Address`
**Use case:** THE diagnostic. The IP keeps an address only if
`(Type LIKE "Primary" || AddressMultiType LIKE "Practice") && (Active==true || Pending==true)`.
Check `PRM_Active__c` / `PRM_Pending__c` on the Primary/Practice address.

```sql
SELECT ParentId, Id, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c, PRM_IsErrorRecord__c,
       PRM_AddressLine1__c, PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_County__c
FROM Address
WHERE ParentId IN ('131UW0000015Si3YAE','131UW0000015mcNYAQ','131UW0000015iiuYAA','131UW000001ZE7ZYAW','131UW000001WdSHYA0')
ORDER BY ParentId
```

## Query 4 — Existing AALs (resolution check)

**Object:** `PRM_AdverseActionLog__c`

```sql
SELECT PRM_CaseManager__r.Name, Id, PRM_Status__c, PRM_PrimaryCity__c, PRM_PrimaryState__c,
       PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c, CreatedDate
FROM PRM_AdverseActionLog__c
WHERE PRM_CaseManager__c IN ('0iTUW000000Qd5l2AC','0iTUW000000RrQ12AK','0iTUW000000SVGz2AO','0iTUW000000bwTF2AY','0iTUW000000dLZF2A2')
ORDER BY PRM_CaseManager__r.Name
```

**Result:** 0 rows for all (no successful submit yet).

## Query 5 — Generic detector: find practitioners whose primary location has NO active primary/practice address

**Use case:** Proactively find ALL cases that will hit this error (not just reported ones).
Run in two steps (primary locations, then addresses), or as an ops report.

```sql
-- Step A: primary-facility locations
SELECT Practitioner.AccountId, HealthcareFacility.LocationId
FROM HealthcarePractitionerFacility
WHERE IsPrimaryFacility = true

-- Step B: for those LocationIds, an address is "good" only if:
--   (PRM_AddressType__c INCLUDES ('Primary') OR PRM_AddressType__c INCLUDES ('Practice'))
--   AND (PRM_Active__c = true OR PRM_Pending__c = true)
-- Locations with zero "good" rows are the ones that will fail App Review submit.
SELECT ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c
FROM Address
WHERE ParentId IN (:locationIds)
```

---

## Audit results

| Case | Practitioner | Primary Acct | Primary Loc | Facility Active | Primary/Practice addr | Active | Pending | Verdict |
|------|-------------|--------------|-------------|-----------------|----------------------|--------|---------|---------|
| IA-0000088944 | Katherine Santa Maria | 001UW00000lXetJYAS | 131UW0000015iiuYAA | true | 2566 Frankford Ave (Practice) `130UW00000MNM4dYAH` | true | false | Reactivated 04/29 → now passes; resubmit clears |
| IA-0000092468 | Brandon Roda | 001UW0000105zwuYAA | 131UW0000015Si3YAE | true | 2901 Jolly Rd (Primary;Billing;Mailing) `130UW00000MNVznYAH` | true | false | Reactivated 04/29 → now passes; resubmit clears |
| IA-0000094048 | Dana Vogel | 001UW00000zqw9gYAA | 131UW0000015mcNYAQ | true | 1119 Raritan Ave (Primary;Billing) `130UW00000MNa8bYAD` | true | false | Reactivated 05/06 → now passes; resubmit clears |
| IA-0000120583 | Rebecca Harvey | 001UW000014WJJFYA4 | 131UW000001ZE7ZYAW | **false** | 168 Franklin Corner Rd (Practice) `130UW00000cCwC1YAK` | **false** | false | **STILL FAILS** — no active/pending primary/practice address |
| IA-0000124514 | Tara Lowe | 001UW000011XMjpYAG | 131UW000001WdSHYA0 | **false** | 3450 High Point Blvd (Primary) `130UW00000b11ZRYAY` | **false** | false | **STILL FAILS** — whole location/facility deactivated |

## Root cause (single, consistent)

The App Review submit chain (OmniScript `PRM_InitialCredentialAppReview` → IP
`PRM_CreateAdverseActionLog_Procedure` v8):

1. `PRMDRExtractAdverseActionLog` — skip if an AAL already exists.
2. `FilterPrimaryPracticeLocation` — keep `Locations` where `PrimaryPracticeLoc == true`.
3. `FilterPrimaryAddress` — keep that location's addresses where
   `(Type LIKE "Primary" || AddressMultiType LIKE "Practice") && (Active==true || Pending==true)`.
4. `PRMDRCreateAdverseActionLog` — inserts `PRM_AdverseActionLog__c` using
   `FilterPrimaryAddress` City/State/AddressLine1/Zip.

When the primary practice location's Primary/Practice address is **inactive**
(`PRM_Active__c=false`) and **not pending** (`PRM_Pending__c=false`), step 3 returns nothing →
City/State/StreetAddress/Zip are blank → step 4 fails REQUIRED_FIELD_MISSING.

**Upstream driver:** the practitioner's `IsPrimaryFacility=true` facility points to a
deactivated/terminated location whose address is inactive. Ops "fixes" each ticket by reactivating
the address (`PRM_Active__c=true`), which is why some tickets clear and new ones keep coming.

## Fix options

**Data fix (clears the 2 still-failing cases now):**
```bash
# Rebecca Harvey
sf data update record --target-org qa-sandbox --sobject Address \
  --record-id 130UW00000cCwC1YAK --values "PRM_Active__c=true"
# Tara Lowe
sf data update record --target-org qa-sandbox --sobject Address \
  --record-id 130UW00000b11ZRYAY --values "PRM_Active__c=true"
```

**Config fix (permanent, stops the recurring defects):** relax the `FilterPrimaryAddress`
filter in `PRM_CreateAdverseActionLog_Procedure` so it falls back to the primary/practice
address even when inactive (the AAL only needs the address-of-record for NPDB). This mirrors the
Apex screen-edit path `PRM_AdverseActionLogService.loadPrimaryFacilityAndAddress`, which deliberately
does NOT filter on `PRM_Active__c` and just prefers active via `ORDER BY`.

---

## DEEPER ROOT CAUSE (2026-06-15 follow-up) — Address pending desync

Business model: new PAR practice location → address `Active=false, Pending=true`; existing
location → `Active=true` (type can be `Practice` for the primary). The create DR
`PRMDRCreatePractitionerNewAddressRecords` confirms this — Address `PRM_Pending__c` has
`defaultValue=true` at creation (so does the Facility/Location/HCPF).

But the two failing cases show the **address pending desynced from its own location**:

| Record | Active | Pending |
|--------|--------|---------|
| Rebecca Facility/Loc (Ivy Rehab, `0klUW000000AXQvYAO`) | false | **true** |
| Rebecca primary HCPF (`0bSUW000000RxDh2AK`) | false (IsActive) | **true** |
| Rebecca Address (Practice, `130UW00000cCwC1YAK`) | false | **false** ❌ |
| Tara Facility/Loc (Nat'l Mentor, `0klUW0000009TCTYA2`) | false | **true** |
| Tara primary HCPF (`0bSUW000000SvUn2AK`) | false (IsActive) | **true** |
| Tara Address (Primary/Mailing/Billing, `130UW00000b11Z*`) | false | **false** ❌ |

The facility/HCPF correctly say "new & pending," but the **Address** is `Active=false AND
Pending=false` — an invalid third state. The addresses were last modified post-creation by QC
users (Jennyfer Licopit 03/17; Jobelle Dalida 04/19) while the facility was never re-touched,
so a review/QC save desynced the address pending. `PRMDRUpdatePrimaryPracticeLoc` ("Make as
primary location") re-types the address but does NOT set Active/Pending, so it never heals it.
Ops "fixes" each ticket by manually flipping `PRM_Active__c=true` (that is exactly what cleared
the 3 resolved cases).

**Net root cause:** `FilterPrimaryAddress` keys off the **address-level** `Active`/`Pending`,
which is unreliable and can drift out of sync with the genuinely-pending facility/HCPF. For new
pending locations the address ends up `Active=false / Pending=false` → dropped → required fields
blank → error.

### Provenance query

```sql
SELECT Id, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c, PRM_IsErrorRecord__c,
       PRM_CaseManager__c, PRM_CaseManager__r.Name, CreatedDate, CreatedBy.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM Address
WHERE Id IN ('130UW00000cCwC1YAK','130UW00000b11ZRYAY','130UW00000b11ZSYAY','130UW00000b11ZTYAY')

SELECT Id, Name, PRM_Active__c, PRM_Pending__c, LocationId, CreatedDate, CreatedBy.Name
FROM HealthcareFacility
WHERE LocationId IN ('131UW000001ZE7ZYAW','131UW000001WdSHYA0')
```

### Recommended fix (revised)

Prefer making the AAL IP trust the **location/facility/HCPF** pending state (reliably `true`
for new locations) rather than the address-level flag — e.g., change `FilterPrimaryAddress` so an
address qualifies when its parent location/HCPF is pending, OR drop the `&& (Active==true ||
Pending==true)` gate entirely and just take the primary/practice address (aligns with the Apex
`PRM_AdverseActionLogService` path). Secondarily, fix the QC/review save so the Address
`PRM_Pending__c` is kept in sync with the facility while the location is pending.

---

## DEFINITIVE ROOT CAUSE (confirmed from IP runtime payload) — 2026-06-15

Reading `PRM_CreateAdverseActionLog_Procedure_8.oip-meta.xml` `customJavaScript` (the IP's own
saved runtime sample of `locationsToUpsert` / `primaryFacility`) settles it. The address objects
fed to `FilterPrimaryAddress` look like this:

```json
"Addresses":[{
  "AddressMultiType":"Primary;Mailing;Billing",
  "Active":false,
  "Type":"Primary",
  "AddressLine1":"7 Beach Ave", "City":"Rehoboth Beach", "State":"DE", "Zip":"19971", ...
}]
```

There is **no `Pending` key on the address node** (it only exists on `primaryFacility.PRM_Pending__c`
and on `HCFNetwork[].Pending`). Therefore in the filter

```
(Type LIKE "Primary" || AddressMultiType LIKE "Practice") && (Active==true || Pending==true)
```

`Pending` resolves to null, `Pending==true` is **always false**, and the gate collapses to
**`Active==true`**. The `Pending` branch is dead code.

**This unifies every case:**

| Case | Primary practice loc address | Active | Pending(DB) | Result |
|------|------------------------------|:--:|:--:|--------|
| Brandon / Dana | active | ✅ true | – | passes |
| Rebecca / Tara | desynced | ❌ false | false | fails |
| **Katherine** (new pending primary `131UW000001f4LdYAI`, 401 S 2nd St) | new pending | ❌ false | **true** | **fails anyway** — proves `Pending==true` is never read |

Org-wide scale of the latent condition (QA, Address with `PRM_Active__c=false` and type
Primary/Practice): **19,627** total — 16,421 with `Pending=false`, **3,206 with `Pending=true`**
(the Katherine pattern that *should* pass but cannot).

### CORRECTED FIX DIRECTION (supersedes earlier drafts)

⚠️ An earlier draft of this doc proposed dropping the `&& (Active==true || Pending==true)` gate, and
a data stopgap that set `Address.PRM_Active__c = true`. **Both were rejected** and reverted:

- Activating an address (`PRM_Active__c=true`) is **committee-gated** — it cannot be faked as a fix.
- The pending guard is meaningful and must stay; the bug is that `Pending` never reaches the filter.

**Correct fix:** make the IP honor the **facility/location pending** signal
(`HealthcareFacility.PRM_Pending__c = true`), which is the reliable indicator of a new pending
location, by resolving the primary address from the DB inside
`PRM_CreateAdverseActionLog_Procedure` (Option 1). This recovers all backlog — including the **745**
desynced addresses whose own `PRM_Pending__c` is false — with **no address activation and no data
migration**.

Full requirements: `requirements/PDM Flows/US_AppReview_AAL_HonorPendingPrimaryAddress.md`.
Read-only validation/sizing: `scripts/apex/validate_AppReview_PendingAddressFix.apex`
(QA: 3,195 inactive Primary/Practice addresses on pending locations fail today, all recover under the
fix; 745 are desynced and only recoverable via the facility/location pending signal).
