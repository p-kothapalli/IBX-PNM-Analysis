# App Review — "Required fields are missing: [PRM_PrimaryCity/State/StreetAddress/Zip]" — Root Cause & Fix

> ⚠️ **PARTIALLY SUPERSEDED (2026-06-15).** The root-cause analysis below is correct, but the
> **fix sections (§3 config "drop the gate" and §5 Apex `PRM_Active__c=true` stopgap) are WRONG and
> were reverted.** Activating an address is committee-gated and cannot be used; the gate must stay.
> The approved fix is to honor the **facility/location pending** signal inside the IP — see
> **`requirements/PDM Flows/US_AppReview_AAL_HonorPendingPrimaryAddress.md`** and the read-only
> validation script `scripts/apex/validate_AppReview_PendingAddressFix.apex`.

**Date:** 2026-06-15
**Org:** ibx--qa
**Component:** `PRM_CreateAdverseActionLog_Procedure` (Integration Procedure, v8) — App Review / Initial Credentialing submit
**Error surfaced to user:** `Error : Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`

---

## 1. What the user sees

Submitting the App Review OmniScript fails on the "Record Creation Failed" step. The four
`PRM_Primary*` fields on `PRM_AdverseActionLog__c` are `required=true`; when the IP tries to insert
the log with those values blank, Salesforce throws `REQUIRED_FIELD_MISSING`.

## 2. Why the fields are blank — the real root cause

The IP builds the four values from a `FilterPrimaryAddress` (List Merge) step:

```
PrimaryCity  = %FilterPrimaryAddress:City%
PrimaryState = %FilterPrimaryAddress:State%
PrimaryAdd1  = %FilterPrimaryAddress:AddressLine1%
PrimaryZip   = %FilterPrimaryAddress:Zip%
```

`FilterPrimaryAddress` runs against the addresses of the location chosen by the prior
`FilterPrimaryPracticeLocation` step (`PrimaryPracticeLoc == true`), using:

```
(Type LIKE "Primary" || AddressMultiType LIKE "Practice") && (Active==true || Pending==true)
```

**The `locationsToUpsert` address objects the OmniScript passes in do NOT contain a `Pending`
field.** Confirmed from the IP's own saved runtime payload (`customJavaScript`):

```json
"Addresses":[{ "AddressMultiType":"Primary;Mailing;Billing", "Active":false, "Type":"Primary",
               "AddressLine1":"7 Beach Ave", "City":"Rehoboth Beach", "State":"DE", "Zip":"19971" }]
```

`Pending` is only present on `primaryFacility.PRM_Pending__c` and `HCFNetwork[].Pending` — never on
the address node. So `Pending==true` evaluates against `null` and is **always false**. The gate
effectively reduces to **`Active==true`**.

**Consequence:** if the selected primary practice location's Primary/Practice address has
`Active=false` (a brand-new pending location, or an address whose `Active` drifted to false during a
QC/review save), the filter returns nothing → the four fields go blank → the insert fails.

### This explains all reported cases

| Case | Primary practice location address | `Active` | `Pending` (DB) | Outcome |
|------|-----------------------------------|:--:|:--:|---------|
| Brandon / Dana | active | true | – | ✅ passes |
| Rebecca / Tara | desynced new location | false | false | ❌ fails |
| **Katherine** — promoting NEW pending loc `131UW000001f4LdYAI` (401 S 2nd St) | new pending | **false** | **true** | ❌ **fails even though DB Pending=true** |

Katherine is the proof: her new address *is* `Pending=true` in the DB, yet she still fails — because
the filter never reads `Pending`.

### Scale in QA

`Address` records that are `PRM_Active__c=false` and typed Primary/Practice:

- **19,627** total
- 16,421 with `Pending=false`
- **3,206 with `Pending=true`** (would pass *if* the filter honored pending)

Not all are tied to an in-flight App Review, but any practitioner whose **selected primary practice
location** has only inactive Primary/Practice addresses will hit this error.

---

## 3. The fix (config — fixes all current and future cases)

`FilterPrimaryAddress.filterListFormula` in `PRM_CreateAdverseActionLog_Procedure_8.oip-meta.xml`:

```diff
- = (Type LIKE "Primary" || AddressMultiType  LIKE "Practice") && (Active==true || Pending== true)
+ = (Type LIKE "Primary" || AddressMultiType  LIKE "Practice")
```

Rationale: `FilterPrimaryPracticeLocation` has already narrowed the list to the chosen primary
practice location. We just need *that* location's Primary/Practice address — its Active/Pending state
is irrelevant for NPDB/adverse-action reporting, and the address-level flags are unreliable (they
desync from the genuinely-pending facility/HCPF). This also aligns the OmniStudio path with the Apex
`PRM_AdverseActionLogService` behavior.

**Scope check:** only this IP carries the filter. The re-credentialing variant
`PRM_IPCreateAdverseActionLog_Procedure` (v10 active) uses a different mechanism and needs no change.

### Deploy

```bash
sf project deploy start \
  --source-dir "force-app/main/default/omniIntegrationProcedures/PRM_CreateAdverseActionLog_Procedure_8.oip-meta.xml" \
  --target-org qa-sandbox --wait 10
```

> OmniStudio note: after deploy, confirm v8 is still the **active** version of
> `PRM_CreateAdverseActionLog` in the OmniStudio IP designer (Activate if the deploy created a new
> draft). Then re-run an App Review submit for one of the failing cases to verify.

After deploy, every backlog case is cleared by simply **re-opening the case and re-submitting App
Review** — no data change required.

---

## 4. Detector — list the affected backlog

Affected = practitioner's **primary practice location** has no *active* Primary/Practice address.
The screen's `PrimaryPracticeLoc` maps to `HealthcarePractitionerFacility.IsPrimaryFacility`.

**Step 1 — primary practice LocationIds (via primary HCPF → facility):**

```sql
SELECT HealthcareFacility.LocationId, PractitionerId, HealthcareFacilityId
FROM HealthcarePractitionerFacility
WHERE IsPrimaryFacility = true
```

**Step 2 — of those locations, the ones whose Primary/Practice address is all-inactive:**

```sql
SELECT Id, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c,
       PRM_AddressLine1__c, PRM_City__c, PRM_State__c, PRM_Zip__c
FROM Address
WHERE ParentId IN (:locationIdsFromStep1)
  AND (PRM_AddressType__c INCLUDES ('Practice') OR PRM_AddressType__c INCLUDES ('Primary'))
  AND PRM_Active__c = false
```

A practitioner is affected when **all** Primary/Practice addresses on their primary location are
`PRM_Active__c=false`. (The single Apex detector in §5 implements this join directly.)

---

## 5. OPTIONAL pre-deploy data stopgap (only if config can't ship immediately)

> ⚠️ Use only as a bridge. The config fix in §3 is the real solution. This script flips
> `PRM_Active__c=true` on the primary practice location's Primary/Practice address for a **specific,
> reviewed list** of practitioners — this is exactly what ops already do by hand. Do **NOT** run it
> org-wide; activating addresses for genuinely-pending new locations can affect directory/network
> visibility. Scope it to the reported defect accounts.

`scripts/apex/fix_AppReview_PrimaryAddress.apex` (run with `sf apex run --file ... --target-org qa-sandbox`):

```apex
// Scope: practitioner Account Ids from the reported defects ONLY.
Set<Id> practitionerAccountIds = new Set<Id>{
    '001UW000016UFgrYAG'   // Katherine Santa Maria — add the rest of the reported list
};

// 1. Primary practice locations for these practitioners
Map<Id, Id> facilityToLocation = new Map<Id, Id>();
Set<Id> locationIds = new Set<Id>();
for (HealthcarePractitionerFacility hpf : [
        SELECT HealthcareFacilityId, HealthcareFacility.LocationId
        FROM HealthcarePractitionerFacility
        WHERE IsPrimaryFacility = true
          AND PractitionerId IN (
              SELECT PersonContactId FROM Account WHERE Id IN :practitionerAccountIds)
    ]) {
    if (hpf.HealthcareFacility.LocationId != null) {
        locationIds.add(hpf.HealthcareFacility.LocationId);
    }
}

// 2. Inactive Primary/Practice addresses on those locations
List<Address> toFix = [
    SELECT Id, PRM_Active__c, PRM_Pending__c, PRM_AddressType__c, ParentId
    FROM Address
    WHERE ParentId IN :locationIds
      AND PRM_Active__c = false
      AND (PRM_AddressType__c INCLUDES ('Practice') OR PRM_AddressType__c INCLUDES ('Primary'))
];

for (Address a : toFix) {
    a.PRM_Active__c = true;     // unblock the filter (which only honors Active)
}
System.debug('Addresses to reactivate: ' + toFix.size());
// update toFix;   // <-- uncomment to commit after reviewing the debug list
```

Leave the `update` line commented for a dry run first; review the debug count/IDs, then re-run with
it uncommented. After the data fix, the affected users re-submit App Review.

---

## 6. Recommended follow-ups

1. **Ship the config fix (§3)** — single-line, fixes all flows of this error.
2. **Add automated coverage** — a test that submits App Review for a practitioner whose primary
   practice location address is `Active=false / Pending=true` and asserts the AAL is created.
3. **Heal the upstream desync** — the QC/review save path lets `Address.PRM_Pending__c` drift to
   `false` while the facility/HCPF stay `Pending=true`; and `PRMDRUpdatePrimaryPracticeLoc`
   ("Make as primary location") re-types the address without setting Active/Pending. Sync the
   address pending to its location/facility so the data is internally consistent regardless of this
   particular filter.
