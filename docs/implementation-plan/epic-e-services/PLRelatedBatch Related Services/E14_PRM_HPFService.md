# E14 · `PRM_HPFService` — *1.5 d* · Branch: BOTH · *(PLRelatedBatch · seq 4)*

> **Parent:** `Epic_E_Practitioner_Services_Part3.md` (Part 3). Shared conventions in **Part 1 §E0.1–E0.2 / §E0.4**.
> **Batch:** runs inside **`PLRelatedBatch`** (seq 4), after `PracticeLocationAndGroupBatch` (seq 2, E21) created the Location/HealthcareFacility graph. **Writes:** `HealthcarePractitionerFacility` (the **practitioner ↔ practice‑location affiliation**), RT `PRM_PractitionerLocationAffiliation` / `PRM_PractitionerPracticeAffiliation`.
> **Legacy (active):** **PLA** ← `PRMDRTransformPractitionerLocations` (Transform) → `PRMDRPDelegatedPractionerPracticeLocations` (Load). **PPA** ← ✅ **org‑confirmed** created by the Load DR **`PRMDRCreateHCPFForPractitionerPracAffiliation`** and its variants **`…Delg`** (Delegated, Id `0jIOv000000EMyLMAW`) / **`…DelgZ2`** — each writes `HealthcarePractitionerFacility` with RT `PRM_PractitionerPracticeAffiliation` (field map §6.1). The **`PractionerPracticeLocationService`** (PPL) is a **sub‑service of E14** (builds the practitioner↔practice‑location rows).
>
> **⚠ Nothing is assumed — every gap is an Open Question (§8). Tags: [CONFIRMED] · [OPEN] · [RISK] · [RECOMMENDATION] · Pending Clarification.**

---

## 1. Role & cardinality

- Runs inside **`PLRelatedBatch`** (seq 4). By the time it runs: E1 created the Case Managers; `PractitionerBatch` (seq 1) the practitioner core; `PracticeLocationAndGroupBatch` (seq 2) the group + **HealthcareFacility** graph.
- **✅ Cardinality (decided): one `HealthcarePractitionerFacility` (HPF) per (practitioner × location)** — the `PRM_PractitionerLocationAffiliation` (PLA) row linking a practitioner (`PractitionerId` = PersonContact) to a `HealthcareFacility` (from E13), + the group `Account` (and optionally the group `HealthcareProvider`).
- **✅ Single service (decided): E14 owns both record types** — do **not** split. The `PractionerPracticeLocationService` is an **internal builder** inside E14 (not a separate class): one service builds a mixed‑RT list and does **one bulk DML** on `HealthcarePractitionerFacility` (same object, same legacy DR `PRMDRPDelegatedPractionerPracticeLocations`, RT‑aware dedupe).
- **Record types:**
  - **`PRM_PractitionerLocationAffiliation`** (PLA) — practitioner **at a specific location** (has `HealthcareFacilityId`); **one per (practitioner × location)**.
  - **`PRM_PractitionerPracticeAffiliation`** (PPA) — practitioner **at the practice/group** (Account‑linked). **✅ Org‑confirmed created by DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]`** (2,233 rows ≈ PLA's 2,310). The DR is a **Load** (JSON→SObject) writing `HealthcarePractitionerFacility` RT `PRM_PractitionerPracticeAffiliation`, resolved by the formula `QUERY(SELECT Id FROM RecordType WHERE DeveloperName='PRM_PractitionerPracticeAffiliation')`. **✅ DR sets `AccountId` (practice/group) and does NOT map `HealthcareFacilityId`** → PPA is **Account‑linked, facility blank** by design (grain = **one per practitioner × practice/group Account**). The 32% of org rows with a facility are legacy/other‑flow artifacts — **E14 leaves `HealthcareFacilityId` null for PPA** (matches the DR).
- **Branch:** BOTH (source carries locations under IBC + Delegated — cf. E13 OQ‑E13‑1b).

> **Bulkification.** Process the whole batch chunk in one pass — build all HPF rows in memory, one bulk DML. No DML/SOQL in loops.

---

## 2. Idempotency (re-run safe) — **required**

> **Why:** Epic C retry re‑runs the whole batch; E14 must not duplicate affiliations.

> **🔎 Org:** `HealthcarePractitionerFacility` has **no `PRM_RecordKey__c` / `PRM_ExternalId__c`**; it has a **Unique `SourceSystemIdentifier`** (string, **not** an External Id → can't `upsert` on it, only pre‑check).

**Proposed approach (existence pre‑check — no new field):**
- **PLA dedupe key = `(PractitionerId + HealthcareFacilityId + RecordTypeId)`** — one row per practitioner × location (decided grain).
- **PPA dedupe key = `(PractitionerId + AccountId + RecordTypeId)`** — one row per practitioner × practice/group (facility is blank for PPA). ✅ **Mirrors the DR's upsert pattern:** the PPA DR maps `Id ← AddressToUpdate:HPFId` — **present ⇒ update**, **absent ⇒ insert**. The caller (Apex batch/service) supplies the matched HPF Id when a row already exists; E14 reproduces this by pre‑checking the natural key and passing the found Id.
- Batch pre‑checks existing HPF for the chunk's practitioners → insert the misses / update the hits. *(Per the `prm-service-class-boundaries` rule, the **batch** does the pre‑check + injects `hcpfId`/`isNew`, or the service does the bulk pre‑check — confirm ownership OQ‑E14‑1b.)*
- **Alternative:** set the Unique **`SourceSystemIdentifier`** to a composite (`{npi}-{facilityExternalId}-{RT}`) + pre‑check on it — mirrors the location objects. **[OPEN — OQ‑E14‑1]**.

> **✅ [RESOLVED — OQ‑E14‑2] Single service, both RTs.** PPA rows are built by the same E14 pass (mixed‑RT list, one bulk DML). New‑vs‑existing gating follows the DR's `HPFId` upsert pattern (above), not a `PracticeToPractitionerRecTypeId` toggle.

---

## 3. Prerequisite work items — schema + access

| WI | Task | Object | Status |
|---|---|---|---|
| WI‑1 | **No new field** (idempotency via pre‑check on the natural key, or the existing Unique `SourceSystemIdentifier`) | `HealthcarePractitionerFacility` | ✅ (no field) |
| WI‑2 | Confirm FLS on `PRM_AsyncJob_Access` for the fields E14 writes | `PRM_AsyncJob_Access` | ◻ confirm |

### 3.1 🔎 Org validation (IBXDEV01)

- RTs (available): **`PRM_PractitionerLocationAffiliation`**, **`PRM_PractitionerPracticeAffiliation`**, `PRM_AdmittingPrivileges`, `Master`. **Usage (org counts):** PLA **2,310** (facility set 93%), PPA **2,233** (Account set 84%, facility set 32%), AdmittingPrivileges 54, no‑RT 243. → **both PLA + PPA are created**; PLA is location‑grain, PPA is practice/group‑grain (Account).
- `Name` **required**. `PractitionerId` → Contact (nullable). `HealthcareFacilityId` → HealthcareFacility (nullable). `AccountId` → Account. `HealthcareProviderId` → HealthcareProvider. `PRM_CaseManager__c` → IndividualApplication. `OperatingHoursId` → OperatingHours.
- **REQUIRED booleans:** `IsPrimaryFacility`, `IsActive`, `PRM_Pending__c` (never null). `EffectiveFrom`/`EffectiveTo`/`PRM_AttestationDate__c` = date (nullable).
- **`SourceSystemIdentifier` = Unique** (string, not extId). **No `PRM_RecordKey__c`/`PRM_ExternalId__c`.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. Per §E0.4 + the `prm-service-class-boundaries` rule, **context is batch‑injected**; the service builds + bulk‑DMLs (existence pre‑check per OQ‑E14‑1b).

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.affiliations`** | `List<Object>` — each `{ practitionerId, healthcareFacilityId, accountId?, healthcareProviderId?, caseManagerId, isPrimary, isActive, effectiveFrom, effectiveTo, recordType }` (batch‑injected) |
| **Output `response.affiliations`** | `List<Map<String,Object>>` (input order): `{ practitionerId, healthcareFacilityId, hcpfId }` |

### 4.1 Correlation & Id resolution (batch‑injected)

The **batch** (`PLRelatedBatch`) resolves and injects per affiliation: `practitionerId` (PersonContact, from the practitioner's Account), `healthcareFacilityId` (from E13/E21 output — the location's HCF), `accountId` (group Account), `caseManagerId`, `isActive`/`effectiveFrom`/`effectiveTo`, `isPrimary` (`location.primaryPracticeLoc`), and the **`recordType`** (PLA vs PPA — OQ‑E14‑2). The service does **no SOQL** (except the idempotency pre‑check if that ownership is confirmed to E14 — OQ‑E14‑1b).

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_HPFService extends PRM_ServiceBase {
    public class PRM_HPFException extends Exception {}

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'affiliations' => new List<Object>() };
        List<Object> affiliations = (params == null) ? null : (List<Object>) params.get('affiliations');
        if (affiliations == null || affiliations.isEmpty()) { return response; }

        // 1) build HealthcarePractitionerFacility rows — PLA (one per practitioner x location) + PPA (internal builder, if in scope OQ-E14-2b)
        //    (no DML/SOQL in loop; required booleans never null)
        // 2) dedupe via pre-check: PLA on (PractitionerId + HealthcareFacilityId); PPA on (PractitionerId + AccountId + RT) — OQ-E14-1
        // 3) ONE bulk insert of the new rows (mixed RT)
        // 4) response (input order)
        return response;
    }
}
```

---

## 5. Expected input format

E14 consumes **batch‑injected affiliations** — the practitioner's practice locations (HCF Ids resolved by E21/E13), not raw JSON. The **source driver** is `practitioner.groups[].locations[]` (each location the practitioner is affiliated with) + `location.primaryPracticeLoc`.

```json
{
  "affiliations": [
    { "practitionerId": "003...", "healthcareFacilityId": "0Gx...", "accountId": "001...",
      "caseManagerId": "0P8...", "isPrimary": true, "isActive": true,
      "effectiveFrom": "2026-03-10", "effectiveTo": null, "recordType": "PRM_PractitionerLocationAffiliation" }
  ]
}
```

> **Service‑computed:** `Name` (⟲ `CONCAT(practitionerName, ' @ ', facilityPracticeName)` — legacy), `PRM_AttestationDate__c` (⟲ `Date.today()`), `PRM_Pending__c` (default), the PLA/PPA gating (§6). Required booleans always set.

---

## 6. Field map (grounded — `PRMDRPDelegatedPractionerPracticeLocations`)

| Field | Source |
|---|---|
| `RecordTypeId` | ⟲ `PRM_PractitionerLocationAffiliation` / `PRM_PractitionerPracticeAffiliation` (OQ‑E14‑2) |
| `Name` | ⟲ `CONCAT(practitionerName, ' @ ', facilityPracticeName)` — **required** |
| `PractitionerId` | injected `practitionerId` (PersonContact) |
| `HealthcareFacilityId` | injected `healthcareFacilityId` (E13) — **blanked for PPA RT** (formula below) |
| `AccountId` | injected `accountId` (group) |
| `HealthcareProviderId` | injected `healthcareProviderId` (group HCP, optional) |
| `IsPrimaryFacility` | ⚠ REQUIRED — ⟲ formula (below) from `isPrimary` |
| `IsActive` | injected `isActive` — ⚠ REQUIRED |
| `EffectiveFrom` / `EffectiveTo` | injected `effectiveFrom` / `effectiveTo` |
| `PRM_AttestationDate__c` | ⟲ `Date.today()` |
| `PRM_Pending__c` | ⚠ REQUIRED → `false` (never null) |
| `PRM_CaseManager__c` | injected `caseManagerId` |

**Formulas → Apex (from `PRMDRPDelegatedPractionerPracticeLocations`):**
- `IsPrimaryFacility = (practiceToPractitionerRecTypeId != recordTypeId) && isPrimary` — i.e. primary applies to the **location** RT, not the practice RT.
- `HealthcareFacilityId = (practiceToPractitionerRecTypeId == recordTypeId) ? null : healthcareFacilityId` — the PPA RT has **no** facility.

### 6.1 PPA field map (✅ grounded — `PRMDRCreateHCPFForPractitionerPracAffiliationDelg`, Id `0jIOv000000EMyLMAW`)

Load DR (JSON→SObject) — all inputs from the `AddressToUpdate` node:

| Field | Source (DR mapping) | Notes |
|---|---|---|
| `Id` | `AddressToUpdate:HPFId` | present ⇒ **update**; absent ⇒ **insert** (idempotency §2) |
| `RecordTypeId` | formula → `PRM_PractitionerPracticeAffiliation` | `QUERY(SELECT Id FROM RecordType WHERE DeveloperName='PRM_PractitionerPracticeAffiliation')` (result path `PracLocToPractitionerRecTypeId` — misnamed) |
| `PractitionerId` | `AddressToUpdate:PractitionerId` | PersonContact |
| `AccountId` | `AddressToUpdate:CreationList:Id` / `AddressToUpdate:Id` | **practice/group Account** |
| `HealthcareFacilityId` | *(not mapped)* | ✅ **blank for PPA** |
| `EffectiveFrom` | `AddressToUpdate:EffectiveDate` | |
| `EffectiveTo` | `AddressToUpdate:EffectiveTo` | |
| `IsActive` | `AddressToUpdate:IsActive` | |
| `PRM_CaseManager__c` | `AddressToUpdate:IndividualAppId` | IndividualApplication |
| `PRM_Pending__c` | `AddressToUpdate:IsPending` (DEFAULT `true`) | ⚠ REQUIRED |

> ✅ **[RESOLVED — OQ‑E14‑8] Name / IsPrimaryFacility not mapped by the PPA DR** — both are org‑`required`. **DECIDED:** for **new** PPA inserts E14 populates `Name` = ⟲ `CONCAT(practitionerName,' @ ',practiceName)` and `IsPrimaryFacility = false` to satisfy required‑field validation (the DR's update path relies on the pre‑existing row for these).
> ⚠ **[RESOLVED — OQ‑E14‑3] `HealthcareProviderId`** — **not mapped by the PPA DR** → E14 leaves it **null** for PPA (revisit only if PLA needs the group HCP).

---

## 7. DML / order (idempotent)

Practitioner/HealthcareFacility exist (E2/E13). **One bulk insert** of `HealthcarePractitionerFacility[]` (both RTs), gated by the existence pre‑check (§2). Returns `hcpfId` per affiliation.

> **CMA:** E14's HPF feeds the CMA record type **`Practitioner_Practice_Location`** (primary `PRM_HealthcarePractitionerFacility__c` + context `PRM_HealthcareFacility__c`, `PRM_HealthcareFacilityNetwork__c`) — created by **E19** in `PLRelatedBatch` (§ per the batch). **[OPEN — OQ‑E14‑4]** confirm the CMA network context lookup source (E17 output).

---

## 8. Open items / clarifications

- **OQ‑E14‑1 — Idempotency key.** Pre‑check on PLA `(PractitionerId + HealthcareFacilityId + RecordTypeId)` / PPA `(PractitionerId + AccountId + RecordTypeId)` (recommended, mirrors the DR's `HPFId` upsert) vs a composite Unique `SourceSystemIdentifier`. And **OQ‑E14‑1b** — does the **batch** or the **service** do the pre‑check (rule)?
- **✅ OQ‑E14‑2a — Single service + PLA grain — DECIDED.** One service (E14) owns both RTs (PPA builder is internal, not a separate class); **one HPF (PLA) per (practitioner × location)**.
- **✅ OQ‑E14‑2b — PPA — RESOLVED (org DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]`).** PPA **is** created, grain = **one per (practitioner × practice/group Account)**, **`HealthcareFacilityId` blank** (DR does not map it). New‑vs‑existing via the `HPFId` upsert path. Field map = §6.1. *(Remaining minor: exact count of PPA per practitioner — one per group Account referenced.)*
- **✅ OQ‑E14‑3 — `HealthcareProviderId` — RESOLVED.** Not mapped by the PPA DR → **null** for PPA.
- **OQ‑E14‑4 — CMA context.** `Practitioner_Practice_Location` CMA context lookups (`PRM_HealthcareFacilityNetwork__c` from E17) — source/order.
- **OQ‑E14‑5 — `Name` source.** `practitionerName` + `facilityPracticeName` (PLA) / `practiceName` (PPA) — from the practitioner Account + HealthcareFacility/Account (batch‑injected) — confirm.
- **OQ‑E14‑6 — CL‑E2‑13.** E14 runs in `PLRelatedBatch` (seq 4), **not** in‑process in E13 — confirm (ratified model).
- **OQ‑E14‑7 — Target org / batch / effort (1.5 d).**
- **✅ OQ‑E14‑8 — PPA required‑field fill — RESOLVED.** The PPA DR omits `Name`/`IsPrimaryFacility` (both org‑required); E14 sets them for new inserts: `Name` = `CONCAT(practitionerName,' @ ',practiceName)`, `IsPrimaryFacility = false`.

*(Org‑validated: RTs, required booleans, Unique `SourceSystemIdentifier`, no `PRM_RecordKey__c`; PPA field map from DR `0jIOv000000EMyLMAW`.)*

---

## 9. Definition of Done

- [ ] OQ‑E14‑1…8 answered *(✅ OQ‑E14‑2a: one service, PLA = one per practitioner×location; ✅ OQ‑E14‑2b: PPA **is** created by DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]`, Account‑grain, facility blank; ✅ OQ‑E14‑3: `HealthcareProviderId` null for PPA; ✅ OQ‑E14‑8: new PPA inserts set `Name`=`CONCAT(practitionerName,' @ ',practiceName)`, `IsPrimaryFacility=false`)*.
- [ ] `PRM_HPFService extends PRM_ServiceBase`; `execute(...)` — **single service**, PPA as an internal builder (not split).
- [ ] Bulk over the chunk; **one bulk DML** (mixed RT); batch‑injected context; required booleans never null.
- [ ] Idempotent: **PLA** pre‑check on `(PractitionerId + HealthcareFacilityId + RT)`; **PPA** on `(PractitionerId + AccountId + RT)`; matched Id supplied for update (DR `HPFId` pattern); re‑run creates no duplicate.
- [ ] PPA field map per §6.1 (DR‑grounded): `AccountId` set, `HealthcareFacilityId` blank, `PRM_CaseManager__c` ← IndividualApplication, `PRM_Pending__c=true`; new inserts also set `Name`/`IsPrimaryFacility` (OQ‑E14‑8). `IsPrimaryFacility`/`HealthcareFacilityId` formulas applied for PLA.
- [ ] Returns `hcpfId` per affiliation (feeds E19 CMA + E15's `PRM_HealthcarePractitionerFacility__c`).
- [ ] `<Class>Test` ≥ 85% incl. bulk, re‑run/idempotency, PLA+PPA rows, primary‑flag formula.
- [ ] Field API names/types validated against the org.
