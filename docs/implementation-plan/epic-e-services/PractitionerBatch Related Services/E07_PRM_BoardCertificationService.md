# E07 · `PRM_BoardCertificationService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1). Shared conventions in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), **after E2** (needs E2's `HealthcareProvider` Id). **Writes:** `BoardCertification`.
> **Legacy:** BoardCertification columns of `PRMDRPHCPNPIBoardCretIdentifier` (Load — shared with E2's NPI/Identifier DR).

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners with a non-empty `boardCertifications[]`. **Delegated** branch only.
- Creates `BoardCertification` rows per practitioner (FKs: Account, PersonContact, HealthcareProvider, Case Manager).
- **Depends on E2** within the same batch for `healthcareProviderId`.

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array; each element `{ practitionerInfo (id, npi, effectiveFrom/To), boardCertifications[] }`. Build all rows across the chunk, then **one bulk DML**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C **retry re-runs the whole batch** → no duplicate certifications. Same principle as E2 §2.

**Anchor = NPI (durable business key)** (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). Key (NPI + board + certification type):

| Object | `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `BoardCertification` | `{npi}_{boardName}_{certificationType}` | `upsert … PRM_RecordKey__c` |

> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **No existing External Id** on `BoardCertification` (only `SourceSystemIdentifier`, unique not External Id) → **new `PRM_RecordKey__c` (External Id, Unique) confirmed** (no reuse option). ✅
> - **⚠ Grain — `BoardName` alone is NOT sufficient.** The data shows a practitioner with the **same `BoardName` under 2 distinct `CertificationType`s** → the key must include `certificationType`: **`{npi}_{boardName}_{certificationType}`**. *(The legacy DR upserted by `BoardName` only — which could collapse different certification types; our key is safer. Confirm with business.)* The triple still repeats (test‑pollution) but that's the old dup bug.
> - **Field facts:** `Name` **required** (← `boardCertificationName`); **`PRM_EffectiveFrom__c` is REQUIRED** (`nillable=false`) — must supply (← `practitionerInfo.effectiveFrom`) or insert fails; **`PRM_BoardOriginal__c` and `PRM_BoardReCert__c` are `Date` fields** (← `boardOriginal`/`boardRecret` as dates); `CertificationType` is a **picklist** (values are specialties — Internal Medicine, Addiction Medicine, … — validate inbound).

> **Field — ✅ DECIDED: new `PRM_RecordKey__c` (External Id, Unique)** (consistent with E2/E5/E6).

**No‑NPI rule:** NPI-anchored → require NPI (reject‑at‑intake recommended) or fallback. **Key‑collision guard:** `_` delimiter; normalize blanks (esp. null `certificationType`).

---

## 3. Prerequisite work items — **schema + access**

✅ **DECIDED: add `PRM_RecordKey__c`** (External Id, Unique) on `BoardCertification`:

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `BoardCertification` | `objects/BoardCertification/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `BoardCertification.PRM_RecordKey__c` to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit |

*(Field + FLS XML identical to E02 §3.)* **Do not start the service (§4+) until `PRM_RecordKey__c` is deployed and the grain (§2) confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk; each element `{ practitionerInfo (id, npi, effectiveFrom/To), boardCertifications[] }`.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.practitioners`** | `List<Object>` — `{ practitionerInfo (id, npi, effectiveFrom/To), boardCertifications[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, boardCertificationIds }` |

### 4.1 Correlation & Id resolution

Per practitioner: `practitionerInfo.id` = Account Id (E1) → resolve `practitionerId` (`PersonContactId`) via one bulk Account query. **`healthcareProviderId`** (from E2, same batch) → resolve in bulk by querying `HealthcareProvider` (`WHERE PRM_RecordKey__c IN :npis`) or receive E2's per-practitioner output from the batch (confirm wiring — same as E6 §4.1). **`caseManagerId`** from the `PRM_AsyncJobRecords__c` row (stable), not the mutable Account back‑link. `effectiveFrom`/`effectiveTo` from `practitionerInfo`. Gated practitioners (empty `boardCertifications`) skipped.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_BoardCertificationService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) collect Account Ids + NPIs for practitioners that HAVE boardCertifications (gated)
        // 2) bulk resolve: Account -> PersonContactId; HealthcareProvider by PRM_RecordKey__c(npi) -> hcpId
        //    caseManagerId from job record
        // 3) build BoardCertification[] across the chunk; set PRM_RecordKey__c (NPI-anchored, §2)
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** ~2 SOQL (Account + HealthcareProvider) + 1 bulk DML (BoardCertification) — constant regardless of chunk size.

---

## 5. Expected input format

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893", "effectiveFrom": "", "effectiveTo": "" },
      "boardCertifications": [
        { "boardName": "ABIM", "boardCertificationName": "Internal Medicine", "certificationType": "", "boardExpires": "", "boardOriginal": "", "boardRecret": "" }
      ]
    }
  ]
}
```

> **Service-computed (do NOT send):** `PRM_RecordKey__c`. FK fields (`AccountId`, `PractitionerId`, `HealthcareProviderId`, `PRM_CaseManager__c`) set in-service.

---

## 6. Field map (grounded)

| BoardCertification field                      | Source                                             |
| --------------------------------------------- | -------------------------------------------------- |
| `AccountId`                                   | `accountId`                                         |
| `HealthcareProviderId`                        | `healthcareProviderId` (from E2)                  |
| `PractitionerId`                              | `practitionerId`                                   |
| `Name` *(required)*                           | `boardCertifications[].boardCertificationName`     |
| `BoardName`                                   | `boardCertifications[].boardName` **[natural key]** |
| `CertificationType` *(picklist)*              | `boardCertifications[].certificationType`          |
| `ExpirationDate` *(Date)*                     | `boardCertifications[].boardExpires`               |
| `PRM_BoardOriginal__c` *(Date)*               | `boardCertifications[].boardOriginal`              |
| `PRM_BoardReCert__c` *(Date)*                 | `boardCertifications[].boardRecret`                |
| `PRM_EffectiveFrom__c` *(**required** Date)* / `PRM_EffectiveTo__c` | `practitionerInfo.effectiveFrom` / `effectiveTo`   |
| `PRM_CaseManager__c`                          | `caseManagerId`                                    |
| `PRM_RecordKey__c`                            | ⟲ `{npi}_{boardName}_{certificationType}` (dedupe — §2) |

### IP grounding (`PRM_DelegatedPractitionerCreation` v7 → element `DRPHCPNPIBoardCretIdentifier`)

| DR input                                           | IP source                                                                           | E7 mapping                              |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------- |
| `BoardCertifications`                              | `LIST(RecordsToUpdate:BoardCertifications)`                                         | `boardCertifications[]`                 |
| `AccountId` / `PractitionerId` / `IndividualAppId` | `DRPAccountCaseCaseManagerCreation:AccountId` / `PersonContactId` / `CaseManagerId` | batch context Ids                       |
| `HealthcareProviderId`                             | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId`           | `healthcareProviderId` (from E2)        |
| `HCPEffectiveFrom` / `HCPEffectiveTo`              | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`                                     | `practitionerInfo.effectiveFrom` / `effectiveTo` |

> Legacy upserts by **`BoardName`** (per practitioner) → reflected in the NPI-anchored key (§2). E7 runs **after E2** (needs `healthcareProviderId`).

**Formulas → Apex:** `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account/Practitioner/CaseManager exist (E1); HealthcareProvider exists (E2). Single **bulk `upsert`** of `BoardCertification[]` by `PRM_RecordKey__c` (FK `AccountId`, `PractitionerId`, `HealthcareProviderId`). Gated — skip practitioners with no `boardCertifications`. Returns `boardCertificationIds` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** No existing External Id (only `SourceSystemIdentifier`) → new `PRM_RecordKey__c` confirmed. `Name` required; **`PRM_EffectiveFrom__c` required**; `PRM_BoardOriginal__c`/`PRM_BoardReCert__c` are Dates; `CertificationType` picklist.
- ✅/⚠ **Board cert dedupe grain — data shows `BoardName` alone insufficient** (same practitioner+board, 2 certification types) → key = `{npi}_{boardName}_{certificationType}` (legacy upserted by `BoardName` only — confirm with business this is acceptable).
- ⚠ **`PRM_EffectiveFrom__c` required** — `practitionerInfo.effectiveFrom` must be present or insert fails; confirm intake guarantees it (or define a default).
- ⚠ **`boardOriginal`/`boardRecret` are Dates** — payload must send parseable dates; validate.
- ⚠ **E2 dependency / `healthcareProviderId` resolution** — in‑memory from E2 vs query `HealthcareProvider` (by `PRM_RecordKey__c=npi`). Same wiring decision as E6.
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link.
- ⚠ **No‑NPI policy** — NPI-anchored key; reject‑at‑intake vs fallback.
- **`effectiveFrom`/`effectiveTo` source** — confirm practitioner-level (`practitionerInfo`) vs per-cert.

---

## 9. Definition of Done

- [ ] **`PRM_RecordKey__c` (§3) deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] Org check (§2/§8) done; grain confirmed.
- [ ] `PRM_BoardCertificationService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML**; gated on non-empty `boardCertifications`.
- [ ] `practitionerId` + `healthcareProviderId` (E2) resolved in bulk; `caseManagerId` from the job record.
- [ ] `PRM_RecordKey__c` set (NPI-anchored).
- [ ] **Idempotent:** `upsert` by `PRM_RecordKey__c`; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `boardCertificationIds` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
