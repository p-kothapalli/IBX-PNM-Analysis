# E13 · `PRM_HealthcareFacilityCreationService` — *3.0 d* · Branch: BOTH · *(PracticeLocationAndGroupBatch)*

> **Parent:** `Epic_E_Practitioner_Services_Part2.md` (Part 2 — PracticeLocationAndGroupBatch). Shared conventions in **Part 1 §E0.1–E0.2 / §E0.4**.
> **Batch:** runs **inside `PracticeLocationAndGroupBatch` (seq 2)** ✅ (OQ‑E13‑2 — *not* a separate async worker), after E3 (group graph) and `PractitionerBatch` (seq 1). **Branch = BOTH** (IBC + Delegated). **Writes (core):** `Location`, `Address`, `HealthcareFacility`, the location's `HealthcareProviderNpi` (via **E12**). ⚠ **The HealthcareFacility trigger (`PRM_HCFacilityTriggerHelper`) auto‑creates `PRM_HealthcareFacilityNPI__c` (Location NPI History) [`createNPIRecords`] and populates `HealthcareFacility.PRM_ExternalId__c` [`populatePRMExternalId`] on insert** — E13 sets `HealthcareFacility.PRM_NpiId__c` but does **not** create the history record or set the external id. **E14 (`HealthcarePractitionerFacility`) + E15 (`ProviderFeature`) are deferred to `PLRelatedBatch` (seq 4)** ✅ (OQ‑E13‑3).
> **Legacy:** field maps reused from `PRMDRCreatePractitionerAddAddressRecords` (fused Address + HealthcareFacility + Location DR). *(That DR is the PAR/shared address path, invoked async here for new‑location creation — CL‑E2‑9.)*
>
> **⚠ Mirrors E02/E03 structure. E13 is the most complex Part‑2 service (async, multi‑object, cross‑service). Nothing is assumed — every gap is an Open Question (§8). Tags: [CONFIRMED] · [OPEN] · [RISK] · [RECOMMENDATION] · Pending Clarification.**

---

## 1. Role & cardinality

- Runs **inside `PracticeLocationAndGroupBatch`** (seq 2). By the time it runs: E1 created the Case Managers; `PractitionerBatch` (seq 1) created the practitioner graph; **E3** created the group/vendor graph.
- E13 builds the **new‑location graph** per location, **gated on the HealthcareFacility not already existing** (§2): `HealthcareProviderNpi` (location NPI, via **E12**) → `Location` → `Address[]` → `HealthcareFacility` (with `PRM_NpiId__c` = the location NPI). ⚠ **On HealthcareFacility insert the trigger auto‑creates `PRM_HealthcareFacilityNPI__c` (Location NPI History) and populates `PRM_ExternalId__c`** — E13 must **not** do those. **E14/E15 run later in `PLRelatedBatch`** (OQ‑E13‑3).
- **[CONFIRMED — scope] New‑location only (CL‑E2‑9).** E13 **creates** `Location`/`Address`/`HealthcareFacility` for locations that don't already exist; **existing** locations are *linked* (affiliations) by later steps, not re‑created. The new‑vs‑existing test is the idempotent upsert/pre‑check in §2.
- **Source grain:** in `PRM_MultiPractitioner_lowvolume.json`, a location lives at `practitioner.groups[].locations[]` — so a location is owned by a **group** (E3) which is owned by a **practitioner**.

> **⚠ [OPEN — OQ‑E13‑4] Cardinality / dedup.** A location (by its composite key — §2) can be referenced by multiple practitioners/groups in one submission. E13 must create each **unique location once** (deduped across the chunk), with practitioner↔location affiliations created separately (E14). Confirm the dedup grain (= the §2 composite key) and that affiliations are out of E13 scope.

> **Bulkification.** Build all `Location`/`Address`/`HealthcareFacility` rows in memory across the chunk, then **one bulk DML per object type**. No DML/SOQL in loops.

---

## 2. Idempotency (re-run safe) — **required**

> **Why:** Epic C retry re‑runs the whole batch; E13 must be safe to re‑run without duplicating the location graph.

> **🔑 The gate = does the `HealthcareFacility` already exist (by its composite `PRM_ExternalId__c`)?** Per the ratified rule: **create `Location`, `Address`, `HealthcareProviderNpi`, and `HealthcareFacility` only when the HealthcareFacility's `PRM_ExternalId__c` does NOT already exist.** If it exists → the location is already set up → **skip the whole graph** (later affiliation steps link it).

> **⚠ The HealthcareFacility trigger owns two things (do NOT do them in the service):**
> - **`PRM_HCFacilityTriggerHelper.populatePRMExternalId`** sets `HealthcareFacility.PRM_ExternalId__c` on insert (formula below). The service must **not** set it.
> - **`PRM_HCFacilityTriggerHelper.createNPIRecords`** **auto‑creates `PRM_HealthcareFacilityNPI__c` (Location NPI History)** when the HCF is inserted with `PRM_NpiId__c` populated. The service must **not** create it — it only sets `HealthcareFacility.PRM_NpiId__c` = the location NPI (from E12).

**HealthcareFacility `PRM_ExternalId__c` — the trigger formula (org‑confirmed, `populatePRMExternalId`):**

```apex
// PRM_HCFacilityTriggerHelper.populatePRMExternalId (from the primary Address of the Location):
facility.PRM_ExternalId__c =
    Account.SourceSystemIdentifier + '-' +
    (facility.PRM_NpiId__c != null ? facility.PRM_NpiId__c : '') + '-' +          // ⚠ the NPI record Id (lookup), not the NPI number
    (facility.PRM_PracticeClassification__c != null ? facility.PRM_PracticeClassification__c : '') + '-' +
    addr.PRM_AddressLine1__c + '-' + addr.PRM_AddressLine2__c + '-' + addr.PRM_Zip__c + '-' + addr.PRM_Phone__c;
```

> **✅ Shared helper (decision).** This composite lives **once** in **`PRM_FormSubUtility.computeHcfExternalId(...)`** — E13 calls it to compute the create/pre‑check gate, and **E22 (`PRM_PLRelatedBatch`, seq 4) calls the same helper** to resolve each location's `HealthcareFacility` Id for E14/E15 (see E22 §3.1). **Do not inline‑replicate the formula** — single source of truth avoids drift. Requires `Account.SourceSystemIdentifier` on the group Account (OQ‑E13‑18/OQ‑E21‑2).

**Approach (org‑grounded — gate on HCF existence):**

| Object | Dedupe / gate | Mechanism | Notes |
|---|---|---|---|
| `HealthcareFacility` | **existence of `PRM_ExternalId__c`** (the trigger composite) | **pre‑check** (batch) → create only the misses | Service must **not** set `PRM_ExternalId__c` (trigger does). Can't `upsert` on it reliably (value = trigger output). |
| `Location` | created **only if the HCF is new** (same gate) | insert (gated) | Location `PRM_ExternalId__c` is also trigger/other‑owned — don't fight it. |
| `Address` | created **only if the HCF is new** | insert (gated) | No unique field; created with the new Location. |
| `HealthcareProviderNpi` (location NPI) | `(Npi + NpiType='Organization')` — **via E12** | pre‑check (E12) | Resolve/create **first** so `PRM_NpiId__c` (Id) is known for the composite. |
| `PRM_HealthcareFacilityNPI__c` (Location NPI History) | **trigger‑created** (`createNPIRecords`) | — | ⛔ **NOT created by E13** — the HCF trigger creates it from `HealthcareFacility.PRM_NpiId__c`. |

- **✅ [OQ‑E13‑1 — RESOLVED] The composite is `PRM_HCFacilityTriggerHelper.populatePRMExternalId`** (formula above). **The batch computes it via the shared `PRM_FormSubUtility.computeHcfExternalId(...)` helper** (same helper E22 uses — single source of truth) to pre‑check HealthcareFacility existence. **Build note:** the formula uses `PRM_NpiId__c` (the HealthcareProviderNpi **record Id**) → resolve the location NPI (E12) **first**, then compute the composite, then run the HCF pre‑check. *(Dedupe is against the current trigger's output; historical rows are not a concern.)*
- **Dependency (E03):** the prefix is **`Account.SourceSystemIdentifier`** — confirm the **group Account** has `SourceSystemIdentifier` populated (E03 currently sets `HealthCloudGA__SourceSystemId__c`; the HCF trigger reads `SourceSystemIdentifier`). **Possible E03 gap (OQ‑E13‑18).**
- **Idempotency flow:** (1) E12 resolves/creates the location NPI (by `Npi`); (2) compute the HCF composite; (3) pre‑check `HealthcareFacility.PRM_ExternalId__c`; (4) **new** → create Location→Address→HCF (trigger then sets the external id + creates the Location NPI History); **existing** → skip. Re‑run safe (a prior‑run HCF is found and skipped).

---

## 3. Prerequisite work items — schema + access

> **✅ Org schema validated — IBXDEV01, 2026‑06‑30 (§3.1).** **No new fields required** for the core graph — `Location`/`HealthcareFacility` already have `PRM_ExternalId__c` (Unique, extId); `Address` dedupes by pre‑check.

| WI | Task | Object | Status |
|---|---|---|---|
| **WI‑1** | **No new field.** Use existing `PRM_ExternalId__c` (Unique, extId) for the Location upsert — value = legacy composite (OQ‑E13‑1) | `Location` | ✅ field exists |
| **WI‑2** | **No new field.** Use existing `PRM_ExternalId__c` for the HealthcareFacility upsert — value = legacy composite | `HealthcareFacility` | ✅ field exists |
| **WI‑3** | `Address` dedupe = pre‑check (no field) | `Address` | ✅ (no field) |
| **WI‑4** | Confirm FLS on `PRM_AsyncJob_Access` for all fields E13 writes (Location/Address/HealthcareFacility) | `PRM_AsyncJob_Access` | ◻ confirm |
| **WI‑5** | Location NPI `HealthcareProviderNpi` via **E12** (pre‑check on `Npi`+`NpiType='Organization'`) | `HealthcareProviderNpi` | depends on E12 |
| **WI‑6** | ~~`PRM_HealthcareFacilityNPI__c`~~ — **trigger‑created** (`createNPIRecords`); E13 only sets `HealthcareFacility.PRM_NpiId__c` | `PRM_HealthcareFacilityNPI__c` | ➡ not built by E13 |
| **WI‑7** | Batch replicates the `populatePRMExternalId` composite to **pre‑check HealthcareFacility existence** (the gate). ⚠ needs `Account.SourceSystemIdentifier` (E03 — OQ‑E13‑18) | `HealthcareFacility` | ◻ formula source confirmed (trigger) |

### 3.1 🔎 Org validation (IBXDEV01, 2026‑06‑30)

- **Location** (49 fields, RT `Master`) — `Name` **required**; **`LocationType` REQUIRED picklist**: `Building, Campus, Floor, Plant, Site, Space, Store, Warehouse, Practice, Corporate/Hospital Affiliation` (source has no locationType → default? OQ‑E13‑6). **`PRM_TelehealthOnly__c`, `PRM_Pending__c` REQUIRED booleans**; **`PRM_EffectiveFrom__c` REQUIRED date** (OQ‑E13‑8). **`PRM_ExternalId__c` Unique+extId** ✓. `PRM_CaseManager__c`→IndividualApplication. *(No NPI field on Location.)*
- **Address** (57 fields, RT `Master`) — `PRM_AddressLine1__c/2`, `PRM_City__c`, **`PRM_State__c` picklist (59, 2‑letter ✓)**, `PRM_Zip__c`. **`PRM_AddressType__c` = multipicklist** (⚠ source sends a single value — OQ‑E13‑9). **`ParentId` → Location, REQUIRED, insert‑only.** **`PRM_EffectiveFrom__c` REQUIRED date**, **`PRM_Pending__c` REQUIRED boolean**. **No External Id / unique field** → pre‑check dedupe.
- **HealthcareFacility** (71 fields) — RTs `PRM_NCPDP, PRM_PracticeLocation, Master`. `Name` **required**; **`AccountId` → Account, REQUIRED** (which account? OQ‑E13‑5). `PRM_PracticeName__c`; **`PRM_Primary__c` REQUIRED boolean**; **`PRM_PracticeClassification__c`** picklist `Professional, Facility` (✅ from source `practiceClassification` §5.1); **`PRM_BillingType__c`** picklist `UB, 1500` (source? OQ‑E13‑7); **`PRM_NpiId__c` → HealthcareProviderNpi** (location NPI, via E12); `LocationId` → Location; **`PRM_ExternalId__c` Unique+extId** ✓; `SourceSystemIdentifier` (string, not unique). `PRM_Pending__c` REQUIRED boolean.
- **PRM_HealthcareFacilityNPI__c** (Location NPI History) — junction: `PRM_HealthcareFacility__c`→HealthcareFacility, `PRM_HealthcareProviderNPI__c`→HealthcareProviderNpi, `PRM_CaseManager__c`→IndividualApplication. **⚡ TRIGGER‑created** (`PRM_HCFacilityTriggerHelper.createNPIRecords`) from `HealthcareFacility.PRM_NpiId__c` — **E13 does not write it.** *(FYI: its `PRM_ExternalId__c` (extId, not unique) existing value = `{HealthcareFacility PRM_ExternalId__c}-{locationNpi}`, e.g. `…-2132131231-1326061284`; 3,139/4,655 populated.)*
- **HealthcarePractitionerFacility** (E14, 53 fields) — RTs incl. `PRM_PractitionerLocationAffiliation`, `PRM_PractitionerPracticeAffiliation`; **`SourceSystemIdentifier` Unique**; `PractitionerId`→Contact, `HealthcareFacilityId`→HealthcareFacility. *(E14 scope — listed for the §1 graph only.)*

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. Per §E0.4 + the `prm-service-class-boundaries` rule, **context is batch‑injected** and the service does **no SOQL/correlation**.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.locations`** | `List<Object>` — **deduped** location nodes (§4.1), each carrying the location fields + batch‑injected context (`accountId` (group), `caseManagerId`, group `taxId`/`groupName` for the composite key, resolved `npiId`/effective dates) |
| **Output `response.locations`** | `List<Map<String,Object>>` (created/new only): `{ locationId, addressIds, healthcareFacilityId, locationNpiId }` *(Location NPI History is trigger‑created; query back if its Id is needed)* |

> **[OPEN — OQ‑E13‑4b] Input shape.** Proposed `params.locations[]` = the batch's **deduped** locations (the batch flattens `practitioner.groups[].locations[]`, dedupes by the composite key, and injects the group `taxId`/`groupName` + `accountId` + `caseManagerId`). Confirm vs passing nested practitioner/group nodes.

### 4.1 Correlation & Id resolution (batch‑injected)

The **batch** (rule): flattens locations, dedupes by the §2 composite key, and injects per location: the **group `accountId`** (✅ OQ‑E13‑5 = the group/vendor Account from E3), **`caseManagerId`** (✅ OQ‑E13‑5b = the **first/owning** practitioner's Case Manager for a shared location), the group **`taxId`/`groupName`** (for the composite `PRM_ExternalId__c`), the **effective date** (✅ OQ‑E13‑8 = the **practitioner `effectiveFromDate`**), and the resolved **location `HealthcareProviderNpi` Id** (via E12, `NpiType='Organization'` — ✅ OQ‑E13‑10). The service does **no lookups**.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_HealthcareFacilityCreationService extends PRM_ServiceBase {

    @TestVisible
    private class LocationUow {
        Map<String, Object> loc;        // location node (+ injected context)
        String externalId;              // composite PRM_ExternalId__c (OQ-E13-1)
        Id accountId;                   // group account (OQ-E13-5)
        Id caseManagerId;               // batch-injected
        Id locationNpiId;               // from E12 (needed for the HCF composite + PRM_NpiId__c)
        String hcfExternalId;           // computed via populatePRMExternalId formula (the gate)
        Boolean isNewFacility;          // batch pre-check on HealthcareFacility.PRM_ExternalId__c
        Location location;
        List<Address> addresses = new List<Address>();
        HealthcareFacility facility;    // trigger creates PRM_HealthcareFacilityNPI__c + sets PRM_ExternalId__c on insert
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> locations = (List<Object>) params.get('locations');   // deduped chunk (OQ-E13-4)

        // 1) build UoWs (no DML/SOQL in loop); read batch-injected context + composite externalId
        // 2) cache RTs (HealthcareFacility 'PRM_PracticeLocation'); compute required defaults (Pending=false, etc.)
        // 3) build Location -> Address[] -> HealthcareFacility (FK LocationId, AccountId, PRM_NpiId__c from E12)
        // 4) GATE + BULK DML (idempotent — §7): batch pre-checks HealthcareFacility by the composite PRM_ExternalId__c
        //    (populatePRMExternalId formula) and processes NEW locations only:
        //      resolve NPI (E12) -> insert Location -> insert Address[] -> insert HealthcareFacility (set PRM_NpiId__c)
        //    ⚡ trigger then auto-populates HCF PRM_ExternalId__c + creates PRM_HealthcareFacilityNPI__c (Location NPI History)
        // 5) E14/E15 -> deferred to PLRelatedBatch (OQ-E13-3), not invoked here

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor:** runs in `PracticeLocationAndGroupBatch` (seq 2). Core cost ≈ 1 SOQL (HealthcareFacility existence pre‑check) + **3 bulk DML** (Location, Address, HealthcareFacility — new only) + E12’s NPI cost — per chunk. **The HCF insert fires the trigger** (`PRM_HCFacilityTriggerHelper`) which itself does additional SOQL/DML (Location NPI History, external id, and other automations — factor into the per‑chunk budget/batch size). E14/E15 run later in PLRelatedBatch.

---

## 5. Expected input format

### 5.1 Source location node (`practitioner.groups[].locations[]`)

```json
{
  "locationNpi": "1801234561",
  "practiceName": "Riverbend Family Health - Cherry Hill",
  "doingBusinessAsName": "Riverbend Family Health",
  "officeEmail": "cherryhill@riverbendhealth.com",
  "primaryPracticeLoc": true,
  "telehealthEnabled": true,
  "telehealthOnly": false,
  "practiceClassification": "Professional",
  "capabilitiesAtLocation": "American Sign Language; Braille Materials",
  "selectedInfoCodes": "Delegated;Par",
  "addresses": [
    { "addressType": "Primary", "addressLine1": "1450 Marlton Pike E", "addressLine2": "Ste 200",
      "city": "Cherry Hill", "state": "NJ", "county": "Camden", "zip": "08034", "zip4": "2143",
      "phone": "8565550199", "phoneExt": "210", "fax": "8565550200" }
  ],
  "networkTaxonomyRoles": [ { "networkName": "AmeriHealth HMO", "careTaxonomyCode": "207Q00000X", "role": "PCP" } ]
}
```

> **🆕 `practiceClassification` added to the source node** (org picklist `Professional` / `Facility`) — needed for `HealthcareFacility.PRM_PracticeClassification__c` **and** as the 3rd segment of the HCF composite `PRM_ExternalId__c` (§5.2). Add it to the intake payload/schema.

### 5.2 Building the HCF composite `PRM_ExternalId__c` from JSON attributes (for the existence gate)

The batch replicates the trigger's `populatePRMExternalId` formula to pre‑check `HealthcareFacility` existence (§2). Mapped to source attributes:

```
PRM_ExternalId__c =
    <group Account.SourceSystemIdentifier>          // = {group.taxId}-{group.groupName}   (from E3; OQ-E13-18)
    + '-' + <location HealthcareProviderNpi Id>      // resolved by E12 from location.locationNpi (⚠ record Id, not the number)
    + '-' + location.practiceClassification          // NEW source attr (Professional/Facility)
    + '-' + primaryAddress.addressLine1
    + '-' + primaryAddress.addressLine2
    + '-' + primaryAddress.zip
    + '-' + primaryAddress.phone
```

- **`primaryAddress`** = the `addresses[]` entry with `addressType='Primary'` (else the first) — matches the trigger reading the Location's primary Address.
- **Blank handling:** the trigger emits `''` for null `PRM_NpiId__c`/`PRM_PracticeClassification__c` and for missing address parts — replicate exactly (empty string between the `-` delimiters) so the computed key matches the trigger output.
- **⚠ Order:** the location NPI (E12) must be resolved **before** computing the key (it contributes the NPI **Id**).

> **Source coverage vs E13 objects:** the source now provides `locationNpi`, `practiceName`, `doingBusinessAsName`, `officeEmail`, `primaryPracticeLoc`, `telehealthEnabled`, `telehealthOnly`, **`practiceClassification`**, `capabilitiesAtLocation`, `selectedInfoCodes`, `addresses[]`, `networkTaxonomyRoles[]`. **Still not in the source:** `LocationType` (OQ‑E13‑6), `PRM_BillingType__c` (OQ‑E13‑7), effective dates (OQ‑E13‑8); the group `taxId`/`groupName` are injected from E3. **Downstream (not E13 core):** `selectedInfoCodes` → **E8** facility‑grain; `networkTaxonomyRoles` → **E14**.

---

## 6. Field maps (grounded — `PRMDRCreatePractitionerAddAddressRecords`, Part 2 §E13 + org §3.1)

> **`[GAP]`** = no source in `PRM_MultiPractitioner_lowvolume.json`. ⚠ = org‑required (must always set; never null).

**Location:**

| Field | Source |
|---|---|
| `Name` | `location.practiceName` (or `doingBusinessAsName`? — OQ‑E13‑6) — **required** |
| `LocationType` | ⚠ **required picklist** — `[GAP]` default e.g. `'Practice'`? (OQ‑E13‑6) |
| `PRM_TelehealthOnly__c` | `location.telehealthOnly` — ⚠ required boolean |
| `PRM_EffectiveFrom__c` | ✅ practitioner `effectiveFromDate` (injected — OQ‑E13‑8) — ⚠ required date |
| `PRM_Pending__c` | `false` — ⚠ required boolean |
| `PRM_CaseManager__c` | injected `caseManagerId` (first/owning practitioner — OQ‑E13‑5b) |
| `PRM_ExternalId__c` | ⭐ legacy composite `{taxId}-{groupName}-{locationNpi}-…` (**upsert key** — OQ‑E13‑1, value TBC) |
| *(telehealthEnabled)* | ✅ **ignored** (OQ‑E13‑11 — only `telehealthOnly` maps) |
| *(officeEmail, doingBusinessAsName, capabilitiesAtLocation)* | `[OPEN — OQ‑E13‑12]` target fields to be specified by user |

**Address (one per `addresses[]`):**

| Field | Source |
|---|---|
| `PRM_AddressLine1__c` / `PRM_AddressLine2__c` | `addresses[].addressLine1` / `addressLine2` |
| `PRM_City__c` / `PRM_State__c` / `PRM_Zip__c` / `PRM_Zip4__c` | `city` / `state` (2‑letter ✓) / `zip` / `zip4` |
| `PRM_County__c` | `county` |
| `PRM_Phone__c` / `PRM_PhoneExtension__c` / `PRM_Fax__c` | `phone` / `phoneExt` / `fax` |
| `PRM_AddressType__c` | `addresses[].addressType` — ⚠ **multipicklist** (source single value — OQ‑E13‑9) |
| `ParentId` | ← Location (**required, insert‑only**) |
| `PRM_EffectiveFrom__c` | ✅ practitioner `effectiveFromDate` (injected — OQ‑E13‑8) — ⚠ required date |
| `PRM_Pending__c` | `false` — ⚠ required boolean |
| `PRM_CaseManager__c` | injected `caseManagerId` |
| **Dedupe** | **pre‑check** `(ParentId + PRM_AddressType__c [+ addressLine1 + zip])` — no extId (§2/OQ‑E13‑9 — confirm tuple in org) |

**HealthcareFacility:**

| Field | Source |
|---|---|
| `Name` | `location.practiceName` — **required** |
| `AccountId` | ✅ **group/vendor Account (E3)** — **required** (OQ‑E13‑5) |
| `PRM_PracticeName__c` | `location.practiceName` |
| `PRM_Primary__c` | `location.primaryPracticeLoc` — ⚠ required boolean |
| `PRM_PracticeClassification__c` | ✅ `location.practiceClassification` (added to source §5.1; also the composite's 3rd segment §5.2) |
| `PRM_BillingType__c` | `[GAP]` picklist `UB/1500` (OQ‑E13‑7 — still deferred) |
| `PRM_NpiId__c` | ← location `HealthcareProviderNpi` (via E12; `Npi=locationNpi`, `NpiType='Organization'`) |
| `LocationId` | ← Location |
| `PRM_Pending__c` | `false` — ⚠ required boolean |
| `PRM_CaseManager__c` | injected `caseManagerId` (first/owning practitioner — OQ‑E13‑5b) |
| `PRM_ExternalId__c` | ⭐ legacy composite (**upsert key** — OQ‑E13‑1, value TBC) |

**Location `HealthcareProviderNpi` (via E12):** `Npi` ← `location.locationNpi`; `NpiType` ← ✅ **`'Organization'`** (OQ‑E13‑10); dedupe **`(Npi + NpiType='Organization')`** pre‑check (E12).

**`PRM_HealthcareFacilityNPI__c` (Location NPI History)** — ⛔ **NOT built by E13.** The **HealthcareFacility trigger** (`PRM_HCFacilityTriggerHelper.createNPIRecords`) creates it automatically from `HealthcareFacility.PRM_NpiId__c` when the facility is inserted. E13's only responsibility is to **set `HealthcareFacility.PRM_NpiId__c`** = the location `HealthcareProviderNpi` (E12). *(The trigger copies effective dates, pending, case manager, and sets `PRM_Active__c`.)*

---

## 7. DML / order (idempotent)

**One bulk DML per object type**, FK order, idempotent per §2:

0. **Gate (batch):** compute the `populatePRMExternalId` composite per location; **pre‑check `HealthcareFacility.PRM_ExternalId__c`** → process **only the new** locations. (Needs the NPI Id from step 1 for the composite — resolve NPI first.)
1. **Location `HealthcareProviderNpi`** (via **E12**) — pre‑check `(Npi + NpiType='Organization')`; insert misses → gives `PRM_NpiId__c` (needed for the composite + the FK).
2. **Insert `Location`** (new only).
3. **Insert `Address[]`** (new only; FK `ParentId` = Location).
4. **Insert `HealthcareFacility`** (new only; FK `LocationId`, `AccountId`, **`PRM_NpiId__c`**). ⚡ **On insert, the trigger auto‑populates `PRM_ExternalId__c` and creates `PRM_HealthcareFacilityNPI__c` (Location NPI History)** — E13 does neither.
5. **E14** `HealthcarePractitionerFacility` + **E15** `ProviderFeature` — ✅ **deferred to `PLRelatedBatch` (seq 4)** (OQ‑E13‑3).

> **⚠ Because a HealthcareFacility can't be `upsert`ed on the trigger‑owned `PRM_ExternalId__c`, E13 uses the batch pre‑check gate (step 0) + plain inserts for the new locations.** Idempotency holds: on re‑run, an already‑created HCF is found by the composite and skipped.

Returns per **new** location `{ locationId, addressIds, healthcareFacilityId, locationNpiId }` (the HCF `PRM_ExternalId__c` + Location NPI History are set/created by the trigger — query back if needed).

> **Required booleans/dates never null:** `Location.PRM_TelehealthOnly__c`/`PRM_Pending__c`/`PRM_EffectiveFrom__c`/`LocationType`, `Address.PRM_EffectiveFrom__c`/`PRM_Pending__c`, `HealthcareFacility.PRM_Primary__c`/`PRM_Pending__c` are all `nillable=false` (§3.1).

---

## 8. Open items / clarifications (must be answered before build)

**Still open (need your input / a check):**
- **🔑 OQ‑E13‑18 (NEW) — `Account.SourceSystemIdentifier` for the prefix.** The trigger reads **`Account.SourceSystemIdentifier`**, but **E03 sets `HealthCloudGA__SourceSystemId__c`**. Confirm the group Account also has `SourceSystemIdentifier` = `{taxId}-{groupName}` (else the HCF external id / gate breaks) — **possible E03 gap.**
- **OQ‑E13‑19 (NEW) — HealthcareFacility trigger cascade.** `PRM_HCFacilityTriggerHelper` on insert also runs `setPLNumberOnCreation`, `assignPrimaryFlags`, `updatePracLocNetworks`, `createAlternateContactOnLocationAdd`, `updateCaseDataManager`, etc. Confirm which of these E13 must **not** duplicate (e.g. networks, alternate contact, CDM update) and factor their SOQL/DML into the batch‑size budget.
- **OQ‑E13‑4/4b — Input shape (assuming Option A).** Batch flattens + dedupes nested `groups[].locations[]` → flat `params.locations[]` with injected context. Confirm Option A.
- **OQ‑E13‑6 — `Location.Name` + `LocationType` (you'll check).** `Name` = `practiceName` vs `doingBusinessAsName`? `LocationType` default (e.g. `Practice`)?
- **OQ‑E13‑7 — `PRM_BillingType__c` (`UB`/`1500`) still not in source** (deferred). *(✅ `PRM_PracticeClassification__c` now added to the source node §5.1 — `Professional`/`Facility`.)*
- **OQ‑E13‑9 — Address dedupe tuple (you'll check in org).** No unique key on Address → which tuple `(ParentId + addressType [+ line1 + zip])`; plus single `addressType` → multipicklist.
- **OQ‑E13‑12 — `officeEmail`, `doingBusinessAsName`, `capabilitiesAtLocation` (you'll specify target fields).**
- **OQ‑E13‑14 — `networkTaxonomyRoles` ownership (you'll confirm).** Assumed E14 (role/network builder, CL‑E2‑10) — not E13.

**Resolved this round:**
- ✅ **OQ‑E13‑1b — Branch = BOTH** (IBC + Delegated).
- ✅ **OQ‑E13‑2 — Runs inside `PracticeLocationAndGroupBatch` (seq 2)** (not a separate async worker).
- ✅ **OQ‑E13‑3 — E14/E15 deferred to `PLRelatedBatch` (seq 4)** ("A for now").
- ✅ **OQ‑E13‑5 — `HealthcareFacility.AccountId` = the group/vendor Account (E3).**
- ✅ **OQ‑E13‑5b — Shared‑location `caseManagerId` = the first/owning practitioner's.**
- ✅ **OQ‑E13‑8 — Effective dates ← the practitioner `effectiveFromDate`.**
- ✅ **OQ‑E13‑10 — Location NPI `NpiType = 'Organization'`.**
- ✅ **OQ‑E13‑11 — `telehealthEnabled` ignored** (only `telehealthOnly` maps).
- ✅ **OQ‑E13‑13 — `selectedInfoCodes` owned by another service** (facility‑grain info codes, not E13).
- ✅ **OQ‑E13‑15 — Use `PRM_ExternalId__c`** (only viable upsert key; `SourceSystemIdentifier` not unique/extId or absent).
- ✅ **OQ‑E13‑16 — Target org IBXDEV01; `PracticeLocationAndGroupBatch` (seq 2); ~3.0 d.**
- ✅ **OQ‑E13‑17 — Location NPI History (`PRM_HealthcareFacilityNPI__c`) is TRIGGER‑created** (`PRM_HCFacilityTriggerHelper.createNPIRecords`), **not** by E13. E13 only sets `HealthcareFacility.PRM_NpiId__c` = the location NPI (E12); the trigger creates the history + sets `PRM_Active__c`/effective/CM. *(Corrected — earlier draft wrongly had E13 create it.)*
- ✅ **OQ‑E13‑1 — Composite = `populatePRMExternalId`** (formula §2/§5.2); batch replicates it for the existence gate (resolve NPI first). Historical Id‑vs‑number mismatch: **out of scope** (dedupe against current trigger output).

---

## 9. Definition of Done

- [ ] Remaining OQs answered — **OQ‑E13‑18 `Account.SourceSystemIdentifier` (E03 gap)**, **OQ‑E13‑19 trigger cascade**, OQ‑E13‑4b, OQ‑E13‑6, OQ‑E13‑7, OQ‑E13‑9, OQ‑E13‑12, OQ‑E13‑14. *(✅ resolved: 1 composite=`populatePRMExternalId` · 1b BOTH · 2 in‑batch seq 2 · 3 E14/E15→PLRelatedBatch · 5 AccountId=group · 5b CM=first · 8 effdate=practitioner · 10 NpiType=Organization · 11 telehealthEnabled ignored · 13 infoCodes→other service · 16 IBXDEV01 · 17 NPI History = trigger‑created.)*
- [ ] Prerequisite: no new fields; FLS confirmed on `PRM_AsyncJob_Access`; `Account.SourceSystemIdentifier` populated for the group Account (OQ‑E13‑18).
- [ ] **Gate on HealthcareFacility existence** (batch replicates `populatePRMExternalId`); create Location/Address/HCF **only for new** locations; **do NOT** set `HCF.PRM_ExternalId__c` or create `PRM_HealthcareFacilityNPI__c` (trigger owns both).
- [ ] `PRM_HealthcareFacilityCreationService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the deduped location chunk; **one bulk DML per object type** (new only); batch‑injected context (no service SOQL); location NPI via **E12** resolved **first** (needed for the composite + `PRM_NpiId__c`).
- [ ] HealthcareFacility inserted with `PRM_NpiId__c` set → trigger creates the Location NPI History + external id.
- [ ] Required booleans/dates never null (`LocationType`, `PRM_TelehealthOnly__c`, `PRM_Primary__c`, `PRM_Pending__c`, effective dates).
- [x] E14/E15 invocation resolved → **deferred to PLRelatedBatch** (OQ‑E13‑3).
- [ ] **Idempotent:** re‑run produces no duplicate Location/Address/HealthcareFacility.
- [ ] Returns per‑location Ids for downstream (E14 affiliations, E15 features, E8 facility info codes).
- [ ] `<Class>Test` ≥ 85% incl. a bulk test (multiple locations/groups) + a re‑run/idempotency test.
- [ ] Field API names/types validated against the org (§3.1 done; re‑confirm target org).
