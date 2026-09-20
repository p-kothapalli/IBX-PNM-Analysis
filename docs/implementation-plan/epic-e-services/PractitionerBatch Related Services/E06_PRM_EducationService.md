# E06 · `PRM_EducationService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1 — intake + PractitionerBatch). Shared conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), **after E2** (needs E2's `HealthcareProvider` Id). **Writes:** `PersonEducation`.
> **Legacy:** `PRMDRTransformAddEducation` (Transform — enriches each row with FK Ids) + `PRMDRPCreateEducation` (Load).

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners whose payload has a non-empty `education[]`. **Delegated** branch only.
- Creates `PersonEducation` rows per practitioner (FKs: PersonContact, HealthcareProvider, Case Manager).
- **Depends on E2** within the same batch: needs the `HealthcareProvider` Id created by E2 for the practitioner (see §4.1 resolution).

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array; each element `{ practitionerInfo (id, npi), education[] }`. Build all `PersonEducation` rows across the chunk, then **one bulk DML**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C **retry re-runs the whole batch** → E6 must be re-run safe (no duplicate education rows). Same principle as E2 §2 / E5 §2.

**Anchor = NPI (durable business key)** (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). Provisional key (NPI + the education's natural attributes):

| Object | **Provisional** `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `PersonEducation` | `{npi}_{degreeId}_{institutionId}_{educationLevel}` | `upsert … PRM_RecordKey__c` |

> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **Existing fields:** `PRM_ExternalId__c` (External Id, **not unique**) is **0 / 1,609 populated** (completely unused); `Identifier` is unique (not External Id). → Reuse is very low‑risk, but neither is *unique External Id*.
> - **⚠ Grain (confirm).** Same `ContactId + Degree + Institution + Level` repeats heavily (15×, 14×…) → **test‑polluted**; almost certainly the old duplication bug (a practitioner doesn't earn the same degree 15×), so the triple is likely the correct grain — but **confirm** whether renewals/dates ever make it repeat legitimately.
> - **Field facts:** `Name` **required** (← `practitionerDegree`); `PRM_Degree__c`/`PRM_Institution__c` are **lookups** (✓ Ids); `PRM_Primary__c` **required** boolean (default `false`); **`PRM_Completed__c` is a picklist with values `Yes`/`No`** (+ null) — **CL‑E3 resolved**: there is a single `PRM_Completed__c` picklist (no separate `PRM_Completed_picklist`).

> **Field decision (§3) — ✅ DECIDED:** add a new **`PRM_RecordKey__c` (External Id, Unique)** (not reusing `PRM_ExternalId__c`), consistent with E2.

**No‑NPI rule:** NPI-anchored → require NPI (reject‑at‑intake recommended) or fallback. **Key‑collision guard:** `_` delimiter; normalize blanks.

---

## 3. Prerequisite work items — **schema + access**

✅ **DECIDED: add a new `PRM_RecordKey__c`** (unique) on `PersonEducation` (org check found no clean unique External Id):

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `PersonEducation` | `objects/PersonEducation/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `PersonEducation.PRM_RecordKey__c` to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit |

*(Field + FLS XML identical to E02 §3.)* **Do not start the service (§4+) until the idempotency field is deployed and the grain (§2) confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk; each element `{ practitionerInfo (id, npi), education[] }`.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.practitioners`** | `List<Object>` — `{ practitionerInfo (id, npi), education[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, personEducationIds }` |

### 4.1 Correlation & Id resolution

Per practitioner: `practitionerInfo.id` = Account Id (E1) → resolve `practitionerId` (`PersonContactId`) via one bulk Account query. **`healthcareProviderId`** (from E2, same batch) → resolve in bulk by querying `HealthcareProvider` (e.g. `WHERE PRM_RecordKey__c IN :npis` — E2 stamps `PRM_RecordKey__c = npi`; or by `AccountId`), **or** receive E2's per-practitioner output from the batch (preferred if the batch chains outputs — confirm wiring). **`caseManagerId`** from the `PRM_AsyncJobRecords__c` row (stable), not `Account.PRM_CaseManager__c` (mutable). Gated practitioners (empty `education`) skipped.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_EducationService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) collect Account Ids + NPIs for practitioners that HAVE education (gated)
        // 2) bulk resolve: Account -> PersonContactId; HealthcareProvider by PRM_RecordKey__c(npi) -> hcpId
        //    caseManagerId from job record
        // 3) build PersonEducation[] across the chunk; set PRM_RecordKey__c (NPI-anchored, §2)
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** ~2 SOQL (Account + HealthcareProvider resolution) + 1 bulk DML (PersonEducation) — constant regardless of chunk size.

---

## 5. Expected input format

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893" },
      "education": [
        { "practitionerDegree": "", "degreeId": "", "institutionId": "", "educationLevel": "", "educationStartDate": "", "educationEndDate": "", "educationCompleted": false, "primaryPersonEdu": false }
      ]
    }
  ]
}
```

> **Service-computed (do NOT send):** `PRM_Completed__c` (picklist `Yes`/`No`, from `educationCompleted`), `PRM_RecordKey__c`. FK fields (`ContactId`, `HealthcareProviderId`, `PRM_CaseManager__c`) set in-service.

---

## 6. Field map (grounded — `AddEducationDRInput:*`)

| PersonEducation field                            | Source                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `ContactId`                                      | `practitionerId`                                                   |
| `HealthcareProviderId`                           | `healthcareProviderId` (from E2)                                  |
| `Name`                                           | `education[].practitionerDegree` (`PractitionerDegree-Block:Name`) |
| `PRM_Degree__c`                                  | `education[].degreeId` (`PractitionerDegree-Block:Id`)             |
| `PRM_Institution__c`                             | `education[].institutionId` (`InstitutionName-Block:Id`)           |
| `EducationLevel`                                 | `education[].educationLevel`                                       |
| `PRM_StartDate__c` / `PRM_EndDate__c`            | `education[].educationStartDate` / `educationEndDate`              |
| `PRM_Completed__c` *(picklist: `Yes`/`No`)*      | ⟲ formula `educationCompleted ? "Yes" : "No"` (verified IBXDEV01)  |
| `PRM_Primary__c` *(required boolean)*            | `education[].primaryPersonEdu` (→ `toBool`, default `false`)        |
| `PRM_CaseManager__c`                             | `caseManagerId`                                                    |
| `PRM_RecordKey__c`                               | ⟲ `{npi}_{degreeId}_{institutionId}_{educationLevel}` (dedupe — §2) |

> **CL‑E3 resolved (IBXDEV01):** the "Completed" field is a single **`PRM_Completed__c` picklist** (values `Yes`/`No`) — there is **no** separate `PRM_Completed_picklist`. `Name` is **required** (← `practitionerDegree`); `PRM_Degree__c`/`PRM_Institution__c` are **lookups** (degree/institution Ids).

### IP grounding (`PRM_DelegatedPractitionerCreation` v7)

The transform element `TransformAddEducation` injects the FK Ids into each row, then `DRPCreateEducation` loads it:

| DR input                         | IP source                                                                 | E6 mapping                    |
| -------------------------------- | ------------------------------------------------------------------------- | ----------------------------- |
| `AddEducationTransformed` (rows) | `RecordsToUpdate:AddEducation`                                            | `education[]`                 |
| `PersonContactId`                | `DRPAccountCaseCaseManagerCreation:PersonContactId`                       | `practitionerId`              |
| `HealthcareProviderId`           | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId` | `healthcareProviderId` (E2)   |
| `PRM_CaseManager__c`             | `DRPAccountCaseCaseManagerCreation:CaseManagerId`                         | `caseManagerId`               |
| (Load) `AddEducationDRInput`     | `TransformAddEducation:AddEducationTransformed`                           | the enriched rows             |

**Formulas → Apex:** `PRM_Completed__c = educationCompleted ? 'Yes' : 'No'` (picklist); `PRM_Primary__c = toBool(primaryPersonEdu)`; `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account/Practitioner/CaseManager exist (E1); HealthcareProvider exists (E2). Single **bulk `upsert`** of `PersonEducation[]` by `PRM_RecordKey__c` (FK `ContactId`, `HealthcareProviderId`). Gated — skip practitioners with no `education`. Returns `personEducationIds` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** `PRM_ExternalId__c` (External Id, not unique) **0% used**; `Identifier` unique not External Id. All E6 fields exist; `Name` required; `PRM_Degree__c`/`PRM_Institution__c` lookups; `PRM_Primary__c` required boolean; `PRM_Completed__c` picklist `Yes`/`No`. **✅ Decided: new unique `PRM_RecordKey__c` (§3).**
- ✅ **CL‑E3 — resolved.** Single `PRM_Completed__c` picklist (`Yes`/`No`); no separate `PRM_Completed_picklist`.
- ⚠ **Education dedupe grain (confirm).** `npi_degreeId_institutionId_educationLevel` — data is test‑polluted (same triple repeats 15×); almost certainly the old dup bug, so the triple is likely right, but **confirm** renewals/dates don't legitimately repeat it.
- ⚠ **E2 dependency / `healthcareProviderId` resolution** — confirm whether the batch passes E2's per-practitioner `healthcareProviderId` in‑memory, or E6 queries `HealthcareProvider` (by `PRM_RecordKey__c=npi` / `AccountId`). Either is bulk‑safe; pick one when wiring `PractitionerBatch`.
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link (as E2/E5).
- ⚠ **No‑NPI policy** — NPI-anchored key; reject‑at‑intake vs fallback.

---

## 9. Definition of Done

- [ ] **Org check (§2/§8) done**; idempotency field decided (reuse vs new `PRM_RecordKey__c`) and, if new, **deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] `PRM_EducationService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML**; gated on non-empty `education`.
- [ ] `practitionerId` + `healthcareProviderId` (E2) resolved in bulk; `caseManagerId` from the job record.
- [ ] `PRM_Completed__c` computed; `PRM_RecordKey__c` set (NPI-anchored).
- [ ] **Idempotent:** `upsert` by the chosen key; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `personEducationIds` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
