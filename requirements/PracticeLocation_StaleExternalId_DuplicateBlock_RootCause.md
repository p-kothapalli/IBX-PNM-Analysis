# Practice Location Stale External ID — Duplicate Block Root Cause Analysis

**Date:** 2026-04-16
**Reported By:** Business / Operations
**Affected Flow:** PDM Manual Update → Update Address Request Type → New Practice Location Creation

---

## Problem Statement

A practice location exists at **123 Main Street** with External ID:

```
103369626-Self Space Pllc-1033696265-P-123 main street-98121-2067990712
```

Business used the PDM Manual Update (Update Address Request Type) to change the address to
**345 Main Street**. The External ID on the `HealthcareFacility` record was **not updated** —
it still contains "123 main street".

When business later attempts to create a **new** practice location at 123 Main Street, the
DataRaptors block the creation with a duplicate error, even though the original record no longer
physically resides at that address.

---

## Architecture Context

### External ID Structure

Practice location External IDs are composed at creation time from:

```
{NPI}-{PracticeName}-{PIE}-P-{AddressLine1}-{Zip}-{Phone}
```

This key is generated **once** and is never regenerated when address data is subsequently modified
through PDM updates. The address component inside the External ID becomes stale the moment any
address update request is processed.

### Duplicate Detection Chain

When a new practice location is created, the following chain executes:

```
OmniScript (Account Creation / PDM Manual Update)
  └── IP: PRM_DuplicateAddCheck  (PRM_DuplicateAddCheck_Procedure_3)
          ├── DR Transform: PRMDRTransformAddData          — normalizes input address
          ├── SV: SVNewAddress                             — isolates "new" addresses
          ├── DR Extract: PRMDRGetHcfIdByAcc               — fetches all HCF IDs for account
          ├── DR Extract: PRMDRGetAddressDataForDupCheck   — queries Address child records (Primary)
          ├── DR Extract: PRMDRGetAddressDataForDupLine    — queries Address child records (Practice)
          └── RA: RAToShowError
                → ShowValidationMsg = true if either DR returns a record
```

`PRMDRGetAddressDataForDupCheck` queries the `Address` object with these filters:

| Filter | Value |
|---|---|
| `PRM_AddressLine1__c` | = input address line 1 |
| `PRM_City__c` | = input city |
| `PRM_Zip__c` | = input zip |
| `PRM_StateCounty__c` | = input state |
| `PRM_Active__c` | = `true` |
| `PRM_AddressType__c` | INCLUDES `'Primary'` (Query 1) / `'Practice'` (Query 2) |
| `ParentId` | IN all HCF IDs for the account |

---

## Root Causes

There are two independent mechanisms that can cause the block. Either one alone is sufficient to
trigger the duplicate error.

### Root Cause A — External ID Upsert Collision (Primary)

When the creation flow builds the External ID for the new location at 123 Main Street:

```
103369626-Self Space Pllc-1033696265-P-123 main street-98121-2067990712
```

This key **matches the relocated record's External ID exactly**. The creation DataRaptor performs
an upsert using this External ID and finds the existing (address-updated) record. The IP or
OmniScript logic treats this as a duplicate and blocks creation.

### Root Cause B — Active Address Child Record Not Deactivated (Contributing)

The PDM "Update Address" request type updates address fields on the `HealthcareFacility` record
but **does not set `PRM_Active__c = false`** on the old `Address` child record. The old Address
record for "123 Main Street" remains active.

`PRMDRGetAddressDataForDupCheck` queries for active Address records matching "123 Main Street"
under all HCF IDs on the account. It finds the old active Address record and returns a result,
causing `ShowValidationMsg = true` regardless of what the HCF's current address fields say.

---

## Impact

| Area | Effect |
|---|---|
| **New Location Creation** | Hard block prevents creation of a legitimately different location at the original address |
| **Business Operations** | Workaround requires manual data correction or admin intervention |
| **Data Integrity** | Stale External ID causes the system to conflate a relocated record with a new record at the vacated address |
| **Audit Trail** | The relocated record's External ID permanently misrepresents its current address |

---

## Recommended Fixes

### Fix 1 — Deactivate Old Address Child Record on PDM Update (Quick Win)

**Addresses:** Root Cause B

In the Integration Procedure that processes the PDM "Update Address" request type, add a
`DataRaptor Post` step **before** creating or activating the new Address record:

```
DRDeactivateOldAddress:
  UPDATE Address
  SET PRM_Active__c = false
  WHERE ParentId = [HCF Id]
    AND PRM_Active__c = true
    AND PRM_AddressType__c INCLUDES 'Primary'  (or 'Practice')
```

This ensures `PRMDRGetAddressDataForDupCheck`'s `PRM_Active__c = 'true'` filter excludes the old
address, eliminating the false positive from Root Cause B.

---

### Fix 2 — Add Current-Address Reconciliation Step in PRM_DuplicateAddCheck IP (Recommended)

**Addresses:** Root Cause A and Root Cause B

After the duplicate DR returns a matched record, add a reconciliation step that verifies whether
the matched HCF's **current** active address still matches the address being tested. If the matched
record has been relocated, it is not a true duplicate.

**New element to add in `PRM_DuplicateAddCheck` after `DRGetAddressData`:**

```
DRGetCurrentAddressOfMatchedHCF:
  SELECT PRM_AddressLine1__c, PRM_Zip__c
  FROM Address
  WHERE ParentId = [Id of matched HCF from DRGetAddressData]
    AND PRM_Active__c = true
    AND PRM_AddressType__c INCLUDES 'Primary'
  LIMIT 1
```

**Updated `RAToShowError` formula:**

```
ShowValidationMsg =
  IF(
    ISNOTBLANK(%DRGetAddressData%) &&
    %DRGetCurrentAddressOfMatchedHCF:PRM_AddressLine1__c% == %TransformAddress:AddressWO:line1%,
    true,
    IF(
      ISNOTBLANK(%DRGetAddressData2%) &&
      %DRGetCurrentAddressOfMatchedHCF:PRM_AddressLine1__c% == %TransformAddress:Address:line1%,
      true,
      false
    )
  )
```

This ensures the block only fires when the found record's **current** address matches the incoming
address — not just when the External ID address component matches.

---

### Fix 3 — Soft-Block with User Override for Relocated Location Scenario

**Addresses:** Root Cause A and Root Cause B (UX approach)

When a duplicate match is found but the matched HCF's current address differs from the address in
its External ID (indicating a relocation occurred), replace the hard block with a confirmation
prompt:

> "A practice location at this address existed previously but has since been relocated to
> 345 Main Street. Do you want to proceed with creating a new location at 123 Main Street?"

**Implementation:**
- Change `STBDuplicateAddPracErrorSF` / `TBDuplicateAddPracError` from a hard-stop to a
  conditional text block that only appears when `IsRelocatedDuplicate = true`
- Add a separate `STBHardBlockDuplicate` that fires only when `IsRelocatedDuplicate = false`
  (genuine same-address, same-active-record duplicate)
- Requires a `Set Values` in the IP to output `IsRelocatedDuplicate` based on the reconciliation
  check from Fix 2

---

### Fix 4 — Add `PRM_AddressUpdated__c` Flag on HealthcareFacility (Longer-Term)

**Addresses:** Root Cause A and Root Cause B (declarative signal)

Add a custom boolean field `PRM_AddressUpdated__c` on `HealthcareFacility__c`. Set it to `true`
whenever the PDM "Update Address" request type successfully completes.

Update `PRMDRGetAddressDataForDupCheck` and `PRMDRGetAddressDataForDupLine` to add:

```
HealthcareFacility.PRM_AddressUpdated__c != true
```

as an additional filter on the `Address` query (via a linked object join). This explicitly excludes
relocated locations from duplicate detection and is easily auditable via a report.

When a location is intentionally terminated and a brand-new record is created at the same address,
the flag is not carried over to the new record.

---

## Fix Comparison

| Fix | Root Cause A | Root Cause B | Scope | Risk | Effort |
|---|---|---|---|---|---|
| 1 — Deactivate old Address on PDM update | No | Yes | PDM update IP | Low | Small |
| 2 — Reconciliation in duplicate IP | Yes | Yes | `PRM_DuplicateAddCheck` IP + DR | Medium | Medium |
| 3 — Soft-block with override | Yes | Yes | PDM OmniScript + IP | Medium | Medium |
| 4 — `PRM_AddressUpdated__c` flag | Yes | Yes | New field + DRs | Low (additive) | Medium |

**Recommended Path:**
1. Apply **Fix 1** immediately as a targeted quick win to eliminate Root Cause B.
2. Implement **Fix 2** as the permanent guard — handles both root causes and is defensive against
   any future cases where Fix 1 is bypassed or the PDM update fails mid-execution.

---

## Files Referenced

| File | Role |
|---|---|
| `force-app/.../omniDataTransforms/PRMDRGetAddressDataForDupCheck_1.rpt-meta.xml` | DR that queries active Address child records for duplicate detection |
| `force-app/.../omniDataTransforms/PRMDRGetAddressDataForDupLine_1.rpt-meta.xml` | DR that queries Practice-type Address records for duplicate detection |
| `force-app/.../omniIntegrationProcedures/PRM_DuplicateAddCheck_Procedure_3.oip-meta.xml` | IP that orchestrates the full duplicate address check |
| `force-app/.../omniIntegrationProcedures/PRM_DuplicatePracticeLocationCheck_Procedure_2.oip-meta.xml` | IP that checks for duplicate cross-reference practice locations |
| `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/...STBDuplicateAddPracErrorSF.json` | OmniScript element that surfaces the duplicate block to the user |
| `force-app/.../classes/PRM_PDMCheckDuplicateEditBlock.cls` | Apex class used for edit-block-level duplicate checks (composite key comparison) |
