# E11 · `PRM_LanguageService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1). Shared conventions in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), **after E2** (needs E2's `HealthcareProvider` Id). **Writes:** `PersonLanguage`.
> **Legacy:** `PRMDRCreatePersonLanguage` (Load) — element `DRCreatePersonlanguage` in `PRM_DelegatedCreateProviderScreenRecords` v1.

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners with a non-empty `languages[]`. **Delegated** branch.
- Creates `PersonLanguage` rows per practitioner (FKs: Individual = Account, HealthcareProvider, Case Manager).
- **Depends on E2** for `healthcareProviderId`.

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array; each element `{ practitionerInfo (id, npi), languages[] }`. Build all rows, then **one bulk DML**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C **retry re-runs the whole batch** → no duplicate language rows. Same principle as E2 §2.

**Anchor = NPI (durable business key)** (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). One row per practitioner per language:

| Object | `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `PersonLanguage` | `{npi}_{language}` | `upsert … PRM_RecordKey__c` |

> **Field — ✅ DECIDED: new `PRM_RecordKey__c` (External Id, Unique)** (consistent with E2/E5/E6/E7/E8/E10).
>
> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **Object exists** (880 records). `PRM_ExternalId__c` (External Id, not unique) → new `PRM_RecordKey__c` stands.
> - **Field facts:** **`IndividualId`** is **polymorphic (Account/Contact/Individual), required** → the Account Id works (legacy mapped `AccountId`) ✓. **`Language` is a required picklist**, **`Name` required**, **`Rank` is a required `int`**. **`PRM_ShareInPublicDirectory__c` is a picklist (`Yes`/`No`)** — *not* a boolean → map `shareInDir` → `Yes`/`No`. `PRM_LastUpdatedByProvider__c` is `datetime`.
> - **⚠ Language value mismatch risk:** picklist values look like **ISO codes** (`eng`, `abk`) and some names — so payload `"English"` may not match. Confirm the payload sends valid `Language` picklist values (or map name→code).
> - **⚠ Grain (confirm).** Same `Individual + Language` repeats (39×, 32×…) → test‑polluted; `npi_language` likely correct (old dup bug).

**No‑NPI rule:** NPI-anchored → require NPI (reject‑at‑intake recommended) or fallback. **Key‑collision guard:** `_` delimiter; normalize language value (casing/code).

---

## 3. Prerequisite work items — **schema + access**

✅ **DECIDED: add `PRM_RecordKey__c`** (External Id, Unique) on `PersonLanguage`:

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `PersonLanguage` | `objects/PersonLanguage/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `PersonLanguage.PRM_RecordKey__c` to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit |

*(Field + FLS XML identical to E02 §3.)* **Do not start the service (§4+) until `PRM_RecordKey__c` is deployed and the grain (§2) confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk; each element `{ practitionerInfo (id, npi), languages[] }`.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.practitioners`** | `List<Object>` — `{ practitionerInfo (id, npi), languages[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, personLanguageIds }` |

### 4.1 Correlation & Id resolution

Per practitioner: `practitionerInfo.id` = Account Id (E1) → `IndividualId`. **`healthcareProviderId`** (from E2, same batch) → resolve in bulk by querying `HealthcareProvider` (`WHERE PRM_RecordKey__c IN :npis`) or receive E2's per-practitioner output (same wiring decision as E6/E7). **`caseManagerId`** from the `PRM_AsyncJobRecords__c` row (stable), not the mutable Account back‑link. `Rank` = sequence within each practitioner's `languages[]`. Gated practitioners (empty `languages`) skipped.

> **Note:** E11 does not need `PersonContactId` — `IndividualId` is the Account Id (legacy `Languages:AccountId`). Confirm `IndividualId`'s referenced object during org validation.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_LanguageService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) collect Account Ids + NPIs for practitioners that HAVE languages (gated)
        // 2) bulk resolve: HealthcareProvider by PRM_RecordKey__c(npi) -> hcpId; caseManagerId from job record
        // 3) build PersonLanguage[] across the chunk (Rank = per-practitioner sequence); set PRM_RecordKey__c (§2)
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** ~1 SOQL (HealthcareProvider resolution) + 1 bulk DML (PersonLanguage) — constant regardless of chunk size.

---

## 5. Expected input format

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893" },
      "languages": [
        { "value": "English", "shareInDir": true, "lastUpdatedOn": "" }
      ]
    }
  ]
}
```

> **Service-computed (do NOT send):** `Rank` (per-practitioner sequence), `PRM_RecordKey__c`. FK fields (`IndividualId`, `PRM_HealthcareProvider__c`, `PRM_CaseManager__c`) set in-service.

---

## 6. Field map (grounded)

| PersonLanguage field            | Source                                                                  |
| ------------------------------- | ----------------------------------------------------------------------- |
| `IndividualId` *(polymorphic Account/Contact/Individual, required)* | `accountId` (legacy `Languages:AccountId` — Account)                    |
| `PRM_HealthcareProvider__c` (→ HealthcareProvider) | `healthcareProviderId` (from E2; legacy `Languages:HealthCareProviderId`) |
| `Language` *(required picklist)* / `Name` *(required)* | `languages[].value` (⚠ must be a valid `Language` picklist value — codes like `eng`) |
| `Rank` *(required int)*         | ⟲ formula (per-practitioner sequence)                                   |
| `PRM_ShareInPublicDirectory__c` *(picklist `Yes`/`No`)* | ⟲ `languages[].shareInDir ? 'Yes' : 'No'`                              |
| `PRM_LastUpdatedByProvider__c` *(datetime)* | `languages[].lastUpdatedOn`                                             |
| `PRM_CaseManager__c` (→ IndividualApplication) | `caseManagerId` (legacy `Languages:CaseManagerId`)                      |
| `PRM_RecordKey__c`              | ⟲ `{npi}_{language}` (dedupe — §2)                                     |

### IP grounding (`PRM_DelegatedCreateProviderScreenRecords` v1 → `DRCreatePersonlanguage`)

`Languages` ← the `Languages` node (each row pre-enriched in the legacy with `AccountId` / `HealthCareProviderId` / `CaseManagerId`). In the new design those FK Ids come from the batch context (not the row).

**Formulas → Apex:** `Rank` = per-practitioner sequence index; `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account/Individual + CaseManager exist (E1); HealthcareProvider exists (E2). Single **bulk `upsert`** of `PersonLanguage[]` by `PRM_RecordKey__c` (FK `IndividualId`, `PRM_HealthcareProvider__c`). Gated — skip practitioners with no `languages`. Returns `personLanguageIds` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** `PRM_ExternalId__c` not unique → new `PRM_RecordKey__c`. `IndividualId` polymorphic (Account ✓) required; `Language` required picklist; `Rank` required int; `PRM_ShareInPublicDirectory__c` picklist `Yes`/`No`; `PRM_LastUpdatedByProvider__c` datetime.
- ⚠ **`Language` picklist values** — appear to be ISO codes (`eng`, `abk`); payload `"English"` may not match. Confirm the payload value (or map name→code) at intake.
- ⚠ **`PRM_ShareInPublicDirectory__c`** — picklist `Yes`/`No`; map `shareInDir` boolean → `'Yes'`/`'No'`.
- ⚠ **`Rank` required** — must compute a per-practitioner sequence (confirm ordering: input order vs primary-first).
- ⚠ **Language dedupe grain** — `npi_language` unique per practitioner? (normalize language value).
- ⚠ **E2 dependency / `healthcareProviderId` resolution** — in‑memory from E2 vs query `HealthcareProvider` (by `PRM_RecordKey__c=npi`). Same wiring decision as E6/E7.
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link.
- ⚠ **No‑NPI policy** — NPI-anchored key; reject‑at‑intake vs fallback.
- **`Rank`** — confirm whether Rank is required and how it's sequenced (input order vs primary‑first).

---

## 9. Definition of Done

- [ ] **`PRM_RecordKey__c` (§3) deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] Org check (§2/§8) done; grain + `IndividualId` target confirmed.
- [ ] `PRM_LanguageService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML**; gated on non-empty `languages`.
- [ ] `healthcareProviderId` (E2) resolved in bulk; `caseManagerId` from the job record; `Rank` sequenced.
- [ ] `PRM_RecordKey__c` set (NPI-anchored).
- [ ] **Idempotent:** `upsert` by `PRM_RecordKey__c`; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `personLanguageIds` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
