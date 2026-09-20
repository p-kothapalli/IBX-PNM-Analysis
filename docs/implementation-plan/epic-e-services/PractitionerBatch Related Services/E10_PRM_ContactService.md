# E10 · `PRM_ContactService` — *1.0 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1). Shared conventions in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1). **Writes:** `ContactProfile`.
> **Legacy:** `PRMDRCreateContactProfileRecords` (Load) + `PRMDRTransformProviderInformationData` — element `CreateContactProfileRecords` in `PRM_DelegatedCreateProviderScreenRecords` v1.

> **⚠ CL‑E2‑1:** the active DR writes the **`ContactProfile`** object (HC data model), **not** `Contact`. The map below is the grounded `ContactProfile` shape; reconcile the plan/flow docs.

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **gated** — only for practitioners with a `providerInformation` node. **Delegated** branch.
- Creates **one `ContactProfile` per practitioner** (demographic profile) — 1:1 with the practitioner.
- Needs the E1 `accountId` (→ `PRM_PersonAccount__c`) + `practitionerId` (PersonContact → `ContactId`) + `caseManagerId`.

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array; each element `{ practitionerInfo (id, npi), providerInformation, providerInformationPersonalPronouns }`. Build all `ContactProfile` rows, then **one bulk DML**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C **retry re-runs the whole batch** → no duplicate ContactProfiles. The legacy DR already upserts by (`PRM_PersonAccount__c`, `ContactId`) — i.e. one per practitioner.

**Anchor = NPI (durable business key)** (**NPI is unique — business‑confirmed; see E02 §8 CL‑E2**). `ContactProfile` is **1:1 with the practitioner**, so the key is simply the NPI:

| Object | `PRM_RecordKey__c` | Mechanism |
|---|---|---|
| `ContactProfile` | `{npi}` | `upsert … PRM_RecordKey__c` |

> **Field — ✅ DECIDED: new `PRM_RecordKey__c` (External Id, Unique)** (consistent with E2/E5/E6/E7/E8).
>
> **🔎 Org validation results (IBXDEV01, 2026‑06‑24):**
> - **Object exists** (572 records). **`ContactId` is UNIQUE** (`nillable=false`) → **confirms 1 ContactProfile per practitioner** (the `{npi}` key is correct; `ContactId` uniqueness is also a natural dup safety net). `PRM_ExternalId__c` (External Id, not unique) → new `PRM_RecordKey__c` stands.
> - **⚠ Multipicklists:** **`Race`, `PRM_Ethnicity__c`, `PRM_HispanicOrigin__c`, `PRM_PersonalPronoun__c` are `multipicklist`** → values must be **`;`‑joined** if multiple (single value is fine). `PRM_HispanicLatino__c` is a single picklist.
> - **Field facts:** the **4 `*IsDirectoryPrint__c` are required booleans** (`nillable=false` → default `false` via `toBool`); `PRM_LastUpdatedByProvider__c` is **`datetime`** (`System.now()`); `PRM_PersonalPronounNotListed__c` is text.

**No‑NPI rule:** NPI-anchored → require NPI (reject‑at‑intake recommended) or fallback. **Key‑collision guard:** `_` delimiter (single‑part here = `{npi}`).

---

## 3. Prerequisite work items — **schema + access**

✅ **DECIDED: add `PRM_RecordKey__c`** (External Id, Unique) on `ContactProfile`:

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `ContactProfile` | `objects/ContactProfile/fields/PRM_RecordKey__c.field-meta.xml` | field deploys as External Id |
| **WI‑2** | Add **FLS (Read + Edit)** for `ContactProfile.PRM_RecordKey__c` to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | running user can edit |

*(Field + FLS XML identical to E02 §3.)* **Do not start the service (§4+) until `PRM_RecordKey__c` is deployed and the grain (§2) confirmed.**

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk; each element `{ practitionerInfo (id, npi), providerInformation, providerInformationPersonalPronouns }`.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.practitioners`** | `List<Object>` — `{ practitionerInfo (id, npi), providerInformation, providerInformationPersonalPronouns }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, contactProfileId }` |

### 4.1 Correlation & Id resolution

Per practitioner: `practitionerInfo.id` = Account Id (E1) → `PRM_PersonAccount__c`; resolve `practitionerId` (`PersonContactId`) via one bulk Account query → `ContactId`. **`caseManagerId`** from the `PRM_AsyncJobRecords__c` row (stable), not the mutable Account back‑link. Gated practitioners (no `providerInformation`) skipped.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_ContactService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) collect Account Ids for practitioners that HAVE providerInformation (gated)
        // 2) bulk resolve Account -> PersonContactId; caseManagerId from job record
        // 3) build ContactProfile[] (demographic defaults); set PRM_RecordKey__c = npi (§2)
        // 4) ONE bulk upsert by PRM_RecordKey__c (idempotent, §7)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** 1 SOQL (Account resolution) + 1 bulk DML (ContactProfile) — constant regardless of chunk size.

---

## 5. Expected input format

```json
{
  "practitioners": [
    {
      "practitionerInfo": { "id": "001XXXXXXXXXXXXXXX", "npi": "1234567893" },
      "providerInformation": {
        "RacialIdentity": "", "CulturalIdentityAPI": "", "IdentifyasHispanic": "", "HispanicOriginAPI": "",
        "RacialIdentityConfirmation": "", "CulturalIdentityConfirmation": "", "HispanicOriginConfirmation": "", "ConfirmationQuestion1": ""
      },
      "providerInformationPersonalPronouns": { "PersonalPronouns": "", "PronounNotListed": "" }
    }
  ]
}
```

> **Service-computed (do NOT send):** `PRM_Ethnicity__c` default `"Prefer not to share"`, the 4 `*IsDirectoryPrint__c` flags (default `false`), `PRM_LastUpdatedByProvider__c` (`System.now()`), `PRM_RecordKey__c`. FK fields (`PRM_PersonAccount__c`, `ContactId`, `PRM_CaseManager__c`) set in-service.

---

## 6. Field map (grounded)

| ContactProfile field                                                                                                                                   | Source                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PRM_PersonAccount__c`                                                                                                                                 | `accountId` (= `practitionerInfo.id`)                                                                                                                     |
| `ContactId` *(unique, required)*                                                                                                                       | `practitionerId` (PersonContact)                                                                                                                          |
| `PRM_CaseManager__c`                                                                                                                                   | `caseManagerId`                                                                                                                                           |
| `Race` *(multipicklist)*                                                                                                                               | `providerInformation.RacialIdentity` (`;`‑join if multiple)                                                                                               |
| `PRM_Ethnicity__c` *(multipicklist)*                                                                                                                   | `providerInformation.CulturalIdentityAPI` (⟲ default `"Prefer not to share"`)                                                                             |
| `PRM_HispanicLatino__c` *(picklist)*                                                                                                                   | `providerInformation.IdentifyasHispanic`                                                                                                                  |
| `PRM_HispanicOrigin__c` *(multipicklist)*                                                                                                              | `providerInformation.HispanicOriginAPI` (`;`‑join if multiple)                                                                                            |
| `PRM_PersonalPronoun__c` *(multipicklist)* / `PRM_PersonalPronounNotListed__c` *(text)*                                                                | `providerInformationPersonalPronouns.PersonalPronouns` / `PronounNotListed`                                                                               |
| `PRM_RaceIsDirectoryPrint__c` / `PRM_EthnicityIsDirectoryPrint__c` / `PRM_HispanicOriginIsDirectoryPrint__c` / `PRM_HispanicLatinoIsDirectoryPrint__c` *(required booleans)* | ⟲ `IF(ISNOTBLANK(x), x, false)` on `RacialIdentityConfirmation` / `CulturalIdentityConfirmation` / `HispanicOriginConfirmation` / `ConfirmationQuestion1` (→ `toBool`) |
| `PRM_LastUpdatedByProvider__c` *(datetime)*                                                                                                            | ⟲ formula `NOW()` → `System.now()`                                                                                                                        |
| `PRM_RecordKey__c`                                                                                                                                     | ⟲ `{npi}` (dedupe — §2)                                                                                                                                   |

### IP grounding (`PRM_DelegatedCreateProviderScreenRecords` → `CreateContactProfileRecords`)

| DR input                              | IP source                                     | E10 mapping                           |
| ------------------------------------- | --------------------------------------------- | ------------------------------------- |
| `PersonAccountId`                     | `PractitionerScreenRecordIds:AccountId`       | `accountId`                           |
| `ContactId`                           | `PractitionerScreenRecordIds:PersonContactId` | `practitionerId`                      |
| `CaseManagerId`                       | `PractitionerScreenRecordIds:CaseManagerId`   | `caseManagerId`                       |
| `ProviderInformation`                 | `ProviderInformation` node                    | `providerInformation`                 |
| `ProviderInformationPersonalPronouns` | `ProviderInformationPersonalPronouns` node    | `providerInformationPersonalPronouns` |

**Formulas → Apex:** confirmation flags default blanks to `false` (`x != null ? x : false`); `CulturalIdentityAPI` defaults to `"Prefer not to share"`; `PRM_LastUpdatedByProvider__c = System.now()`; `PRM_RecordKey__c` per §2.

---

## 7. DML / order (idempotent)

Account + PersonContact + CaseManager exist (E1). Single **bulk `upsert`** of `ContactProfile[]` by `PRM_RecordKey__c` (FK `PRM_PersonAccount__c`, `ContactId`). Gated — skip practitioners with no `providerInformation`. Returns `contactProfileId` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Org validation (§2) — done (IBXDEV01).** `ContactId` unique (1‑per‑practitioner confirmed); `PRM_ExternalId__c` not unique → new `PRM_RecordKey__c`. `Race`/`PRM_Ethnicity__c`/`PRM_HispanicOrigin__c`/`PRM_PersonalPronoun__c` are **multipicklists**; 4 `*IsDirectoryPrint__c` required booleans; `PRM_LastUpdatedByProvider__c` datetime.
- ⚠ **Multipicklist handling** — `;`‑join multi‑value demographics; confirm inbound values are active picklist entries (esp. the `PRM_Ethnicity__c` default `"Prefer not to share"`).
- ⚠ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link.
- ⚠ **No‑NPI policy** — NPI-anchored key; reject‑at‑intake vs fallback.
- **CL‑E2‑1** — confirm the object is `ContactProfile` (not `Contact`) in the flow/plan docs.

---

## 9. Definition of Done

- [ ] **`PRM_RecordKey__c` (§3) deployed + added to `PRM_AsyncJob_Access`** before coding.
- [ ] Org check (§2/§8) done; grain + picklists confirmed.
- [ ] `PRM_ContactService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the chunk; **one bulk DML**; gated on `providerInformation` present.
- [ ] `practitionerId` resolved via one bulk Account query; `caseManagerId` from the job record.
- [ ] Demographic defaults computed (`Prefer not to share`, IsDirectoryPrint flags, `LastUpdatedByProvider`); `PRM_RecordKey__c` set.
- [ ] **Idempotent:** `upsert` by `PRM_RecordKey__c`; re-run produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy.
- [ ] Returns `contactProfileId` per practitioner.
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re-run/idempotency test**.
- [ ] Field API names/types validated against the org.
