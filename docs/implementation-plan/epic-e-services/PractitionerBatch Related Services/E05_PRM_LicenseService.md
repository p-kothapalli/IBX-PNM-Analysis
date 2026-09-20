# E05 · `PRM_LicenseService` — *0.5 d* · Branch: BOTH (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1 — intake + PractitionerBatch). Shared conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2** and apply here unchanged.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), after E1 created the Case Managers at intake. **Writes:** `BusinessLicense`.
> **Legacy:** `PRMDRTransformDelegatedBusinessLicense` (Transform — Delegated DEA/CDS + SBRD merge) + the **BusinessLicense columns** of the fused HCP DR (`PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` IBC / `PRMDRPHCPHCPTaxonomyAndBusineessLicense` Delegated).

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners whose payload has a non-empty `businessLicenses[]`.
- Creates `BusinessLicense` rows for each practitioner (FKs to the E1 Account + PersonContact + Case Manager).
- **Branch:** BOTH. IBC supplies a unified `businessLicenses[]`; Delegated historically split DEA/CDS vs SBRD (collapsed to one array now — see §6 note / CL‑E8).
- Independent of E2's records (it only needs E1's Account/Contact/CaseManager), but runs in the same batch.

> **Bulkification.** Like E1/E2, E5 processes the **whole batch chunk in one pass** — input is a **`practitioners[]`** array; each element carries `practitionerInfo` (incl. `id` = Account Id, `npi`) + its `businessLicenses[]`. Build all `BusinessLicense` rows across the chunk, then **one bulk DML**. `practitionerId` resolved in one bulk query; `caseManagerId` from the job record (see §4.1).

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C manual **retry re-runs the whole batch**, including chunks that already committed. So E5 must be re-run safe (no duplicate licenses). Same principle as E2 §2.

**Anchor = NPI (durable business key)** — consistent with E2 (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). The license dedupe key is **NPI + the license's natural attributes**:

| Object | **Provisional** `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `BusinessLicense` | `{npi}_{licenseType}_{licenseNumber}_{practitionerState}` | `upsert … PRM_RecordKey__c` |

```apex
// '_' delimiter; NPI-anchored, stable inputs only; normalize blanks
// bl.PRM_RecordKey__c = key(new List<String>{ npi, licenseType, licenseNumber, state });
```

> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **Existing fields:** `PRM_ExternalId__c` (External Id, **not unique**) is **essentially unused — 3 / 1,607** rows; `Identifier` is unique (not External Id), ~0% used. → Low‑ownership; reuse is possible, but neither is *unique External Id*.
> - **⚠ Grain is UNRESOLVED (blocking).** The triple `LicenseNumber + LicenseClass + State` **repeats for the same `ContactId`** (4×, 4×, 3×…), and one license number is shared by **39 distinct practitioners** → the org is **test‑polluted**, so the data can't confirm the rule. **Business decision needed:** does a practitioner's license uniquely = `licenseType+licenseNumber+state`, or must `effectiveDate` be part of the key (renewals)? The provisional key above assumes **no renewals** (triple is unique per NPI) — **confirm before building** (§8).
> - **Field facts:** `Name` is **required**; `LicenseClass`/`Status`/`PRM_LicenseState__c` are **picklists** (values incl. SBRD/DEA/CDS/State Pharmacy/CLIA…, `LicenseClass` can be null). All E5 fields exist with the expected types.

> **Field decision (§3) — ✅ DECIDED:** add a new **`PRM_RecordKey__c` (External Id, Unique)** (not reusing `PRM_ExternalId__c`), consistent with E2.

**No‑NPI rule:** as in E2, the key is NPI‑anchored → require NPI (reject‑at‑intake recommended) or define a fallback. *(Confirm — §8.)*

**Key‑collision guard:** fixed `_` delimiter; normalize blank `licenseType`/`licenseNumber`/`state` to empty strings.

---

## 3. Prerequisite work items — **schema + access**

Org check (§2) shows no clean **unique External Id** on `BusinessLicense` (`PRM_ExternalId__c` is External Id but **not unique**, and near‑empty). **✅ DECIDED: add a new `PRM_RecordKey__c`** (unique).

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `BusinessLicense` | `force-app/main/default/objects/BusinessLicense/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `BusinessLicense.PRM_RecordKey__c` to permission set **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit the field |

*(Field + FLS XML shapes identical to E02 §3 — `Text(255)`, `externalId=true`, `unique=true`, `caseSensitive=false`.)* **Do not start the service (§4+) until `PRM_RecordKey__c` is deployed AND the dedupe grain (§2) is confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow**` and `**practitioners**` — the batch chunk; each element `{ practitionerInfo (incl. `id`, `npi`), businessLicenses[] }`. `VerifiedDate` is service-computed.

| | |
|---|---|
| **Input `params.flow`** | `String` — IBC vs Delegated |
| **Input `params.practitioners`** | `List<Object>` — chunk of `{ practitionerInfo (id, npi), businessLicenses[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, businessLicenseIds }` |

### 4.1 Correlation & Id resolution

`practitionerInfo.id` = Account Id (E1) → resolve `practitionerId` (`PersonContactId`) via one bulk Account query. **`caseManagerId` comes from the `PRM_AsyncJobRecords__c` row (stable), not `Account.PRM_CaseManager__c` (mutable)** — same caveat as E2 §4.1. A per-practitioner wrapper holds references; gated practitioners (empty `businessLicenses`) are skipped.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_LicenseService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) collect Account Ids for practitioners that HAVE licenses (gated)
        // 2) ONE bulk query: Account -> PersonContactId  (caseManagerId from job record)
        // 3) build BusinessLicense[] across the chunk; set PRM_RecordKey__c (NPI-anchored, §2); VerifiedDate = Date.today()
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** 1 SOQL (Account resolution) + 1 bulk DML (BusinessLicense) — constant regardless of chunk size. No DML/SOQL in loops.

---

## 5. Expected input format

`params.practitioners` — each element a practitioner node with a **single unified `businessLicenses[]`** array (each element carries its own `licenseType`). The legacy two-array split (`DEACDSBusinessLicense` / `SBRDBusinessLicense`) + normalize/merge transform are **collapsed** (see §6 note / CL‑E8).

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893" },
      "businessLicenses": [
        { "practitionerLicenseNumber": "3232323", "licenseType": "SBRD", "practitionerState": "PA", "licenseIssuedDate": "12/30/2024", "licenseExpirationDate": "02/01/2025" },
        { "practitionerLicenseNumber": "232323",  "licenseType": "DEA",  "practitionerState": "PA" }
      ]
    }
  ]
}
```

> **Service-computed (do NOT send):** `VerifiedDate` (`TODAY()`), `PRM_RecordKey__c` (NPI-anchored). FK fields (`AccountId`, `ContactId`, `PRM_CaseManager__c`) are set in-service from the batch context.

---

## 6. Field map (grounded — fused DR `BusinessLicense` columns → `businessLicenses[]`)

| BusinessLicense field                  | Source                                         |
| -------------------------------------- | ---------------------------------------------- |
| `AccountId`                            | `accountId` (FK, in-service)                   |
| `ContactId`                            | `practitionerId`                               |
| `Name` / `LicenseNumber`               | `businessLicenses[].practitionerLicenseNumber` |
| `LicenseClass`                         | `businessLicenses[].licenseType`               |
| `PRM_LicenseState__c`                  | `businessLicenses[].practitionerState`         |
| `PRM_ProviderLicenseEffectiveDate__c`  | `businessLicenses[].licenseIssuedDate`         |
| `PRM_ProviderLicenseExpirationDate__c` | `businessLicenses[].licenseExpirationDate`     |
| `VerifiedDate`                         | ⟲ formula `TODAY()` → `Date.today()`           |
| `PRM_CaseManager__c`                   | `caseManagerId`                                |
| `Status`                               | payload (optional)                             |
| `PRM_RecordKey__c`                     | ⟲ `{npi}_{licenseType}_{licenseNumber}_{state}` (dedupe — §2) |

> **Coverage check:** every fused-DR `BusinessLicense.*` column maps to a `businessLicenses[]` attribute or a batch-context Id. `licenseType` distinguishes DEA / CDS / SBRD (replacing the legacy two-block + transform).

> **Org‑validated field facts (IBXDEV01):** `Name` is **required** (satisfied by `practitionerLicenseNumber` — confirm it's always present, else supply a fallback). `LicenseClass` (← `licenseType`), `Status`, and `PRM_LicenseState__c` are **picklists** — the payload values must be **active picklist entries** (seen: SBRD, DEA, CDS, State Pharmacy, CLIA, Business Registration, …; `LicenseClass` may be null). Validate inbound values at intake.

### IP grounding (BusinessLicense input to the fused HCP DR)

| Branch | IP source of `BusinessLicense` | New design |
| --- | --- | --- |
| IBC (`PRM_PractitionerCreation` v3) | `RecordsToUpdate:BusinessLicense` (already unified) | `businessLicenses[]` directly |
| Delegated (`PRM_DelegatedPractitionerCreation` v7) | `LA_MergeBusinessLicense` = `PRMDRTransformDelegatedBusinessLicense` (normalized DEA/CDS) **+** SBRD | `businessLicenses[]` (single array; normalize only if the OmniScript still sends two blocks) |

> **Why one node now (not two):** legacy DEA/CDS and SBRD came from two blocks with different field names, so `PRMDRTransformDelegatedBusinessLicense` renamed DEA/CDS → SBRD shape (stamping `licenseType="SBRD"`), then `LA_MergeBusinessLicense` merged them. In Apex the payload supplies **one `businessLicenses[]`** already unified (with `licenseType` per element), so the transform + merge are unnecessary. Confirm the OmniScript emits a single array vs. two blocks (then normalize in `PRM_FormSubUtility`) — **CL‑E8**.

**Formulas → Apex:** `VerifiedDate = Date.today()`; `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account/Practitioner/CaseManager exist (E1). Single **bulk `upsert`** of `BusinessLicense[]` by `PRM_RecordKey__c` (FK `AccountId`, `ContactId`). Gated — skip practitioners with no `businessLicenses`. Returns `businessLicenseIds` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** `PRM_ExternalId__c` (External Id, not unique) ~0% used; `Identifier` unique but not External Id. All E5 fields exist; `Name` required; `LicenseClass`/`Status`/`PRM_LicenseState__c` picklists. **✅ Decided: new unique `PRM_RecordKey__c` (§3).**
- 🚧 **BLOCKING — license dedupe grain (§2).** Data is test‑polluted (same `ContactId`+triple repeats 4×; one license number across 39 practitioners), so it can't confirm the rule. **Business decision:** is a license unique per practitioner by `licenseType+licenseNumber+state`, or must `effectiveDate` be in the key (renewals)? Provisional key assumes the triple. **Confirm before building.**
- ⚠ **Picklist values** — `licenseType`/`Status`/`state` must be active picklist entries on the org (validate at intake).
- ⚠ **`Name` required** — set from `practitionerLicenseNumber`; confirm always present.
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not `Account.PRM_CaseManager__c` (mutable). Same as E2.
- ⚠ **No‑NPI policy** — NPI-anchored key; reject-at-intake (recommended) vs fallback.
- **CL‑E8** — license payload shape: confirm the OmniScript emits a single unified `businessLicenses[]` (else normalize the legacy two blocks in `PRM_FormSubUtility`).
- **`Status` default** — confirm whether `Status` is set by payload or defaulted.

---

## 9. Definition of Done

- [ ] **Org check (§2/§8) done**; idempotency field decided (reuse vs new `PRM_RecordKey__c`) and, if new, **deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] `PRM_LicenseService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML** (no DML/SOQL in loops); gated on non-empty `businessLicenses`.
- [ ] `practitionerId` resolved via one bulk Account query; `caseManagerId` from the job record.
- [ ] `VerifiedDate = Date.today()`; `PRM_RecordKey__c` set (NPI-anchored).
- [ ] **Idempotent:** `upsert` by the chosen key; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `businessLicenseIds` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
