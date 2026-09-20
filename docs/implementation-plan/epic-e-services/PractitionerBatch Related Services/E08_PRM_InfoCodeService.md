# E08 · `PRM_InfoCodeService` — *1.5 d* · Branch: BOTH (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1). Shared conventions in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1). **Writes:** `PRM_InfoCodeAssignment__c` (custom object).
> **Legacy:** `PRMDRPCreateInfoCodeAssignments` (Load — straight map, no formulas).

> **Scope note:** E8 has two methods per the plan — `createIfPresent(infoCodes)` (**practitioner‑grain — this doc**) and `prepareBulkForLocations(addresses)` (**facility‑grain — detailed with §E14 in Part 3**).

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners with a non-empty `infoCodes[]`. **BOTH** branches.
- Creates `PRM_InfoCodeAssignment__c` rows linking the practitioner **Account** to each **InfoCode**.
- **No E2 dependency** — needs only the E1 `accountId` (+ `caseManagerId`); simplest of the PractitionerBatch services.

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array; each element `{ practitionerInfo (id, npi, isActive, effectiveFrom/To), infoCodes[] }`. Build all assignments across the chunk, then **one bulk DML**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C **retry re-runs the whole batch** → no duplicate InfoCode assignments. Same principle as E2 §2.

**Anchor = NPI (durable business key)** (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). One assignment per practitioner per InfoCode:

| Object | `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `PRM_InfoCodeAssignment__c` | `{npi}_{code}` | `upsert … PRM_RecordKey__c` |

> **Key uses the inbound `code` (not the resolved Id).** ✅ **DECIDED (CL‑E9, §4.1):** the payload carries the InfoCode **`code`** (`PRM_InfoCode__c.PRM_Code__c` — unique External Id), not a record Id. The `code` is the stable business key, so the dedupe key is `{npi}_{code}` (independent of how the master Id resolves).

> **Field — ✅ DECIDED: new `PRM_RecordKey__c` (External Id, Unique)** (consistent with E2/E5/E6/E7).
>
> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **Object exists** (1,317 records). `PRM_ExternalId__c` (External Id, not unique) is **2 / 1,317 populated** → near‑empty; new `PRM_RecordKey__c` stands.
> - **Field facts:** `PRM_Account__c` → Account, `PRM_CaseManager__c` → IndividualApplication, **`PRM_InfoCode__c` → `PRM_InfoCode__c`** object (resolved from `code` — CL‑E9). **`PRM_EffectiveFrom__c` is REQUIRED** (`nillable=false`) — must supply (← `practitionerInfo.effectiveFrom`) or insert fails. **⚠ `PRM_Active__c` is a read‑only FORMULA** (`calculated=true`, `createable=false`/`updateable=false`) — **must NOT be set** (the original "required boolean" note was wrong; re‑validated 2026‑06‑30 on IBXDEV). `PRM_InfoCodeAssignedEffectiveToday__c` is likewise a read‑only formula.
> - **⚠ Grain (confirm).** Same `Account + InfoCode` repeats (10×, 2×…) → test‑polluted; almost certainly the old dup bug, so `npi_infoCodeId` is likely right — **confirm** the same InfoCode can't legitimately repeat with different effective periods.

**No‑NPI rule:** NPI-anchored → require NPI (reject‑at‑intake recommended) or fallback. **Key‑collision guard:** `_` delimiter; normalize blanks.

---

## 3. Prerequisite work items — **schema + access**

✅ **DECIDED: add `PRM_RecordKey__c`** (External Id, Unique) on `PRM_InfoCodeAssignment__c`:

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `PRM_InfoCodeAssignment__c` | `objects/PRM_InfoCodeAssignment__c/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `PRM_InfoCodeAssignment__c.PRM_RecordKey__c` to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit |

*(Field + FLS XML identical to E02 §3.)* **Do not start the service (§4+) until `PRM_RecordKey__c` is deployed and the grain (§2) confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk; each element `{ practitionerInfo (id, npi, isActive, effectiveFrom/To), infoCodes[] }`.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.practitioners`** | `List<Object>` — `{ practitionerInfo (id, npi, isActive, effectiveFrom/To), infoCodes[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, infoCodeAssignmentIds }` |

### 4.1 Correlation & Id resolution

Per practitioner: `practitionerInfo.id` = Account Id (E1) → used **directly** as `PRM_Account__c` (no extra query needed — E8 doesn't need PersonContact or HealthcareProvider). **`caseManagerId`** from the `PRM_AsyncJobRecords__c` row (stable), not the mutable Account back‑link. `isActive`/`effectiveFrom`/`effectiveTo` from `practitionerInfo`. Gated practitioners (empty `infoCodes`) skipped.

> **CL‑E9 — ✅ RESOLVED: the payload sends `code` (not an Id).** Each `infoCodes[]` element is `{ infoCode, code }`, where **`code` = `PRM_InfoCode__c.PRM_Code__c`** (the unique External Id on the master — **Text(3)**, org‑validated). The service **bulk‑resolves** the master record Id from `code` via **one SOQL** (`SELECT Id, PRM_Code__c FROM PRM_InfoCode__c WHERE PRM_Code__c IN :codes`) → `Map<code, Id>` before building, then sets `PRM_InfoCodeAssignment__c.PRM_InfoCode__c` = the resolved Id. A code with **no matching master is skipped** (no assignment row). The `infoCode` value is the human‑readable label (informational); resolution keys off `code`. *(Mirrors the E6 master‑data resolution pattern — degree/institution.)*

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_InfoCodeService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) for each practitioner with infoCodes (gated): accountId = practitionerInfo.id; caseManagerId from job record
        // 2) (CL-E9) collect codes -> ONE bulk query PRM_InfoCode__c by PRM_Code__c -> Map<code, Id>
        // 3) build PRM_InfoCodeAssignment__c[] across the chunk (skip unresolved codes); set PRM_RecordKey__c = {npi}_{code} (§2)
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** 1 SOQL (InfoCode `code`→Id resolution) + 1 bulk DML — constant regardless of chunk size.

---

## 5. Expected input format

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893", "isActive": true, "effectiveFrom": "03/01/2026", "effectiveTo": "" },
      "infoCodes": [ { "infoCode": "Wheelchair Accessible", "code": "101" } ]
    }
  ]
}
```

> `infoCodes[]` = `{ infoCode, code }` (**no Id** — CL‑E9). `code` = `PRM_InfoCode__c.PRM_Code__c` (unique) → the service resolves the master Id in‑bulk. `infoCode` is the human‑readable label. **Service-resolved (do NOT send):** `PRM_InfoCode__c` (master Id). **Service-computed (do NOT send):** `PRM_RecordKey__c` (= `{npi}_{code}`). FK fields (`PRM_Account__c`, `PRM_CaseManager__c`) set in-service.

---

## 6. Field map (grounded — practitioner-grain)

| PRM_InfoCodeAssignment__c field               | Source                                 |
| --------------------------------------------- | -------------------------------------- |
| `PRM_Account__c` (→ Account)                  | `accountId` (= `practitionerInfo.id`)  |
| `PRM_InfoCode__c` (→ `PRM_InfoCode__c`)       | resolved master Id from `infoCodes[].code` via `PRM_Code__c` (CL‑E9) |
| ~~`PRM_Active__c`~~ *(read‑only formula — **do NOT set**)* | n/a — org‑validated `calculated=true` (derived from the effective dates) |
| `PRM_EffectiveFrom__c` *(**required** Date)* / `PRM_EffectiveTo__c` | `practitionerInfo.effectiveFrom` / `effectiveTo` |
| `PRM_CaseManager__c` (→ IndividualApplication) | `caseManagerId`                        |
| `PRM_RecordKey__c`                            | ⟲ `{npi}_{code}` (dedupe — §2)  |

### IP grounding (element `DRPCreateInfoCodeAssignments` — IBC v3 & Delegated v7)

| DR input                        | IP source                                         | E8 mapping                             |
| ------------------------------- | ------------------------------------------------- | -------------------------------------- |
| `Account`                       | `DRPAccountCaseCaseManagerCreation:AccountId`     | `accountId`                            |
| `CaseManager`                   | `DRPAccountCaseCaseManagerCreation:CaseManagerId` | `caseManagerId`                        |
| `InfoCodeIds`                   | `%InfoCodeIds%` (resolved list)                   | `infoCodes[].code` → resolved in‑service to the master Id (CL‑E9) |
| `EffectiveFrom` / `EffectiveTo` | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`   | `practitionerInfo.effectiveFrom` / `effectiveTo` |
| `IsActive`                      | `%IsActive%` (Delegated only)                     | `practitionerInfo.isActive`            |

**Formulas → Apex:** none (straight map). `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account + CaseManager exist (E1). Single **bulk `upsert`** of `PRM_InfoCodeAssignment__c[]` by `PRM_RecordKey__c` (FK `PRM_Account__c`). Gated — skip practitioners with no `infoCodes`. Returns `infoCodeAssignmentIds` (per practitioner). *(Facility‑grain `prepareBulkForLocations(addresses)` is detailed with §E14 in Part 3.)*

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** Object exists; `PRM_ExternalId__c` not unique, ~0% used → new `PRM_RecordKey__c`. `PRM_InfoCode__c` → `PRM_InfoCode__c`; `PRM_EffectiveFrom__c` required; `PRM_Active__c` required boolean.
- ⚠ **`PRM_EffectiveFrom__c` required** — `practitionerInfo.effectiveFrom` must be present or insert fails; confirm intake guarantees it (or default).
- ✅ **CL‑E9 — RESOLVED: payload sends `code`, not Id.** Each `infoCodes[]` element is `{ infoCode, code }`; `code` = `PRM_InfoCode__c.PRM_Code__c` (unique). The service bulk‑resolves the master Id from `code` (one SOQL) and sets `PRM_InfoCode__c`. Unresolved codes are skipped. *(Mirrors E6's master‑data resolution.)*
- ⚠ **InfoCode dedupe grain** — `npi_code` (data: same Account+InfoCode repeats 10× = likely old dup bug); confirm it can't legitimately repeat with different effective periods.
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link.
- ⚠ **No‑NPI policy** — NPI-anchored key; reject‑at‑intake vs fallback.
- **`isActive`/`effectiveFrom`/`effectiveTo` source** — confirm practitioner-level (`practitionerInfo`).

---

## 9. Definition of Done

- [ ] **`PRM_RecordKey__c` (§3) deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] Org check (§2/§8) done; grain confirmed; CL‑E9 resolved.
- [ ] `PRM_InfoCodeService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML**; gated on non-empty `infoCodes`.
- [ ] `accountId` used directly; `caseManagerId` from the job record.
- [ ] `PRM_RecordKey__c` set (NPI-anchored).
- [ ] **Idempotent:** `upsert` by `PRM_RecordKey__c`; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `infoCodeAssignmentIds` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
