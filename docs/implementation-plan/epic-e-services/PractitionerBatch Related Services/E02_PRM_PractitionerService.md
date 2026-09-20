# E02 · `PRM_PractitionerService` — *2.5 d* · Branch: BOTH · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1 — intake + PractitionerBatch). Shared conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2** and apply here unchanged.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), after E1 has created the Case Managers at intake. **Writes:** `HealthcareProvider`, `HealthcareProviderNpi`, `Identifier`, `HealthcareProviderTaxonomy`.
> **Legacy:** `PRMDRPHCPHCPTaxonomyAndBusineessLicense` / IBC `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (HealthcareProvider + HealthcareProviderTaxonomy columns) + `PRMDRPHCPNPIBoardCretIdentifier` (HealthcareProviderNpi + Identifier columns) + `PRMDRCreateIdentiferAndDocument`.

> **Scope note:** E2 owns `HealthcareProviderTaxonomy` (matching the fused legacy DR). For Practitioner Creation this **supersedes the standalone E4 `PRM_TaxonomyService`** — keep E4 only if a taxonomy-only reuse is needed elsewhere; otherwise treat E4 as covered here.
> **⚠ CL‑E1 (IBC gap):** the active IBC IP (`PRM_PractitionerCreation` v3) creates HealthcareProvider/Taxonomy (fused DR) but has **no DR creating HealthcareProviderNpi / Identifier**. Per the ratified decision, E2 still creates NPI + Identifier for **both** branches; the IBC source DR is a **gap** — confirm IBC NPI/Identifier field values during build (default: reuse the maps below).

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1) — *not* at intake. By the time it runs, E1 has already created, per practitioner: the Person `Account`, the `Case`, and the `IndividualApplication` (= Case Manager), and seeded one `PRM_AsyncJobRecords__c` per Case Manager.
- For each practitioner it creates the **practitioner core graph**: `HealthcareProvider` → `HealthcareProviderNpi` → `Identifier[]` → `HealthcareProviderTaxonomy[]`.
- **Branching:** IBC vs Delegated handled internally (the batch passes `flow`); IBC and Delegated differ in taxonomy/license source (see §6 IP grounding) but E2 builds NPI + Identifier for both (CL‑E1).

> **Bulkification (resolved — §4.1).** Like `PRM_CaseService` (E1), **E2 processes the whole batch chunk of practitioners in one pass** — input is a **`practitioners[]`** array; each `practitionerInfo` carries an **`id` = the Practitioner Account Id** created by E1 (the correlation key). E2 resolves each practitioner's `practitionerId` (PersonContact) and `caseManagerId` in **one bulk query**, builds all records, then does **one bulk DML per object type**.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C manual **retry re-runs the whole batch**, including `execute()` chunks that already committed in the prior run. So E2 must be safe to run again without creating duplicates. (Within one `execute()`, an unhandled exception rolls back that chunk; the duplicate risk is the *already-committed* chunks on re-run.)

**Anchor = NPI (durable business key).** The key is anchored on the practitioner's **`npi`** (`practitionerInfo.npi`) — immutable, **globally unique (business‑confirmed: no duplicate NPIs — see §8 CL‑E2)**, present in the payload, and **reusable by other processes**. It is **not** anchored on internal/mutable values (`accountId` is per‑submission & internal; `PRM_CaseManager__c` is a mutable lookup; `PRM_AsyncJobRecords__c.Id` is ephemeral) — see the decision trail in §8.

**Approach (hybrid):**

- **HCP / Identifier / Taxonomy — External‑Id `upsert` on `PRM_RecordKey__c`** (the field created in §3; built from stable inputs only — never generated child Ids):

  | Object | `PRM_RecordKey__c` value | Mechanism |
  |---|---|---|
  | `HealthcareProvider` | `{npi}` *(one HCP per provider NPI)* | `upsert … PRM_RecordKey__c` |
  | `HealthcareProviderNpi` | *(uses existing `Npi` field)* | **pre‑check on `Npi`** — no new field |
  | `Identifier` | `{npi}_{type}_{idValue}` | `upsert … PRM_RecordKey__c` |
  | `HealthcareProviderTaxonomy` | `{npi}_{taxonomyCode}` | `upsert … PRM_RecordKey__c` |

  ```apex
  // built in the per-UoW builder; '_' delimiter; NPI-anchored, stable inputs only
  private String key(List<String> parts) { return String.join(parts, '_'); }
  // e.g. hcp.PRM_RecordKey__c = key(new List<String>{ npi });
  //      idn.PRM_RecordKey__c = key(new List<String>{ npi, type, idValue });
  //      tax.PRM_RecordKey__c = key(new List<String>{ npi, taxonomyCode });
  ```

- **HealthcareProviderNpi — existence pre‑check (no new field).** The NPI value already lives in the standard **`Npi`** field, so don't add a redundant key field: one **bulk SOQL** (`SELECT Npi FROM HealthcareProviderNpi WHERE Npi IN :chunkNpis`) → skip NPIs already present → `insert` the rest. *(Standard `Npi` is not unique‑constrained, so the pre‑check is what prevents duplicates — WI‑5.)*

**No‑NPI rule (required):** NPI is the anchor, so a practitioner **must** have an NPI for the key to be valid. **Recommended: require NPI at intake (reject if blank)** so the key is always a clean business key. *(Confirm the no‑NPI policy — see §8.)*

**Key‑collision guard:** fixed delimiter `_`; normalize blank `type`/`idValue` to empty strings; confirm the natural keys are unique per practitioner (a practitioner won't have two identifiers with the same `type`+`idValue`, nor two rows for the same `taxonomyCode`).

**Dependency:** `PRM_RecordKey__c` (External Id, Unique) on **HealthcareProvider / Identifier / HealthcareProviderTaxonomy** + permission‑set FLS — see the **§3 work items**. These are **E02's own** declarative work items (the base permission set `PRM_AsyncJob_Access` is Epic A's; the fields + FLS are E02's) and are **already deployed ✅**. *(Scoped to E2's objects for now — not yet standardized across E2–E18.)*

---

## 3. Prerequisite work items — **schema + access (E02‑owned) — ✅ already deployed**

Idempotency (§2) is via External‑Id `upsert`, so the External‑Id field must exist **and be on the permission set** before the service is built. These are **E02's own declarative work items** — the `PRM_RecordKey__c` fields + their FLS belong to **E02, not Epic A** (only the base permission set `PRM_AsyncJob_Access` is Epic A's). They are **already deployed ✅**; re‑confirm present before coding.

> **Field:** `PRM_RecordKey__c` — `Text(255)`, **External Id = true**, **Unique = true**, **Case Sensitive = false**. A **durable business key** (anchored on NPI — §2), reusable by other processes; **not** the org's existing `PRM_ExternalId__c`/`SourceSystemIdentifier` (those are owned by other integrations — see §2 / §8). Added only on the 3 objects that need an upsert key; **HealthcareProviderNpi reuses its existing `Npi` field via pre‑check** (no new field).

| WI | Task | Object | Metadata path | Done when |
|---|---|---|---|---|
| **WI‑1** | Create `PRM_RecordKey__c` (Text 255, ExternalId, Unique, case‑insensitive) | `HealthcareProvider` | `force-app/main/default/objects/HealthcareProvider/fields/PRM_RecordKey__c.field-meta.xml` | field deploys; visible as External Id |
| **WI‑2** | Create `PRM_RecordKey__c` (same spec) | `Identifier` | `objects/Identifier/fields/PRM_RecordKey__c.field-meta.xml` | field deploys |
| **WI‑3** | Create `PRM_RecordKey__c` (same spec) | `HealthcareProviderTaxonomy` | `objects/HealthcareProviderTaxonomy/fields/PRM_RecordKey__c.field-meta.xml` | field deploys |
| **WI‑4** | Add **field‑level security (Read + Edit)** for the 3 new fields to the permission set **`PRM_AsyncJob_Access`** (E02 adds this FLS; the base permset is Epic A §A5) | `PRM_AsyncJob_Access` | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | permset deploys; running user can edit `PRM_RecordKey__c` on all 3 objects |
| **WI‑5** | HealthcareProviderNpi — **no new field**; confirm pre‑check on `Npi` is the dedupe mechanism (note: standard `Npi` is *not* unique‑constrained, so the pre‑check enforces no‑dup) | `HealthcareProviderNpi` | — | approach confirmed; (optional) decide whether to add a unique constraint on `Npi` |

**Field metadata (WI‑1/2/3) — same shape per object:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_RecordKey__c</fullName>
    <label>Record Key</label>
    <type>Text</type>
    <length>255</length>
    <externalId>true</externalId>
    <unique>true</unique>
    <caseSensitive>false</caseSensitive>
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E02). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

**Permission set FLS (WI‑4) — add to `PRM_AsyncJob_Access`:**

```xml
<fieldPermissions>
    <field>HealthcareProvider.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
<fieldPermissions>
    <field>Identifier.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
<fieldPermissions>
    <field>HealthcareProviderTaxonomy.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

> **Validation:** `Schema.SObjectType.HealthcareProvider.fields.getMap().get('PRM_RecordKey__c')` resolves and `isUpdateable()` is true for the running user; a test `upsert … PRM_RecordKey__c` compiles. WI‑1…WI‑4 are **already deployed ✅** — re‑confirm present before starting the service (§4+).

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow**` and `**practitioners**` — the batch chunk's practitioner nodes (a `List`, each element `{ practitionerInfo, taxonomies[], identifiers[] }`). **`practitionerInfo.id` = the Practitioner Account Id** created by E1. All formula fields are computed in the service.

| | |
|---|---|
| **Input `params.flow`** | `String` — IBC vs Delegated routing/context |
| **Input `params.practitioners`** | `List<Object>` — chunk of `{ practitionerInfo (incl. `id` = Account Id, `npi`), taxonomies[], identifiers[] }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ accountId, healthcareProviderId, healthcareProviderNpiId, identifierIds, taxonomyIds }` |

### 4.1 Correlation & Id resolution

Each `practitionerInfo.id` is the **Account Id** from E1 — the correlation key for **FK resolution** (distinct from the **dedupe** anchor, which is NPI — §2). E1 stamped on that Account `PersonContactId` (→ `practitionerId`). E2 resolves the FK Ids with **one bulk SOQL** over the Account Ids; a per-practitioner **`PractUow`** wrapper holds the record references so Ids carry forward across the inserts (same pattern as E1's `AppUow`).

> **⚠ `caseManagerId` source (see §8):** `Account.PRM_CaseManager__c` is a **mutable** "latest" pointer — the `PRM_CaseManager__c` FK on E2's records should come from the **`PRM_AsyncJobRecords__c`** row (stable, the batch scope), not re‑derived from the Account. The skeleton below still shows the Account‑based read; reconcile to the job‑record source when wiring the batch.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_PractitionerService extends PRM_ServiceBase {

    // one per practitioners[] element (input order) — holds inputs + resolved Ids + built records
    @TestVisible
    private class PractUow {
        Map<String, Object> p;          // practitionerInfo (incl. id = Account Id, npi)
        List<Object> taxonomies;
        List<Object> identifiers;
        Id accountId;                   // = practitionerInfo.id (E1)
        Id practitionerId;              // PersonContactId (resolved)
        Id caseManagerId;               // Case Manager (from PRM_AsyncJobRecords__c — see §4.1 note)
        HealthcareProvider hcp;
        HealthcareProviderNpi npi;
        List<Identifier> idRecs = new List<Identifier>();
        List<HealthcareProviderTaxonomy> taxRecs = new List<HealthcareProviderTaxonomy>();
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) build UoWs + collect Account Ids (no DML/SOQL in loop)
        List<PractUow> uows = new List<PractUow>();
        Set<Id> accountIds = new Set<Id>();
        for (Object o : practitioners) {
            Map<String, Object> app = (Map<String, Object>) o;
            PractUow u = new PractUow();
            u.p          = (Map<String, Object>) app.get('practitionerInfo');
            u.taxonomies = (List<Object>) app.get('taxonomies');
            u.identifiers= (List<Object>) app.get('identifiers');
            u.accountId  = (Id) u.p.get('id');          // Account Id from E1
            accountIds.add(u.accountId);
            uows.add(u);
        }

        // 2) ONE bulk query resolves practitionerId (PersonContactId). caseManagerId comes from
        //    PRM_AsyncJobRecords__c (batch scope) — NOT Account.PRM_CaseManager__c (mutable; §4.1/§8)
        Map<Id, Account> accById = new Map<Id, Account>(
            [SELECT Id, PersonContactId FROM Account WHERE Id IN :accountIds]);
        for (PractUow u : uows) { u.practitionerId = accById.get(u.accountId).PersonContactId; /* u.caseManagerId set from job record */ }

        // 3) cache RTs once (Identifier 'PRM_Practitioner'); bulk-resolve taxonomy refs by code (PRM_TaxonomySelector)
        // 4) build HCP / NPI / Identifier[] / Taxonomy[] per UoW (formulas in builders — see §6),
        //    set PRM_RecordKey__c (NPI-anchored — §2)
        // 5) BULK DML per object type (idempotent — §7): upsert HCP/Identifier/Taxonomy by PRM_RecordKey__c;
        //    pre-check + insert HealthcareProviderNpi by Npi

        // 6) response (input order)
        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost:** ~**2 SOQL** (Account resolution + NPI pre‑check; +1 taxonomy‑ref selector) + **4 bulk DML** (HCP, NPI, Identifier, Taxonomy) — constant regardless of chunk size. No DML/SOQL/describe in loops.

---

## 5. Expected input format

`params.practitioners` is the batch chunk — a list of practitioner nodes, each `{ practitionerInfo, taxonomies[], identifiers[] }`. **`practitionerInfo.id` = the Account Id created by E1** (FK correlation key) and **`practitionerInfo.npi`** is the dedupe anchor (§2); `practitionerId`/`caseManagerId` are resolved in-service (§4.1), not sent. Formula fields are service-computed.

```json
{
  "practitioners": [
    {
      "practitionerInfo": {
        "id": "001XXXXXXXXXXXXXXX",
        "firstName": "Jane",
        "lastName": "Smith",
        "npi": "1234567893",
        "npiType": "",
        "existingHcpNpiId": "",
        "isActive": false,
        "effectiveFrom": "",
        "effectiveTo": "",
        "hcpEffectiveFrom": "",
        "hcpEffectiveTo": ""
      },
      "taxonomies": [
        { "careTaxonomyId": "", "taxonomyCode": "207R00000X", "name": "", "isPrimary": true, "providerType": "" }
      ],
      "identifiers": [
        { "name": "", "type": "" }
      ]
    }
  ]
}
```

> **`practitionerInfo.id`** = Account Id from E1 (FK resolution). **`practitionerInfo.npi`** = dedupe anchor (§2). E2 resolves `practitionerId` (PersonContact) via the §4.1 bulk query and `caseManagerId` from the job record.

> **Service-computed (do NOT send):** `HealthcareProvider.Status` (`HCPStatus`), `HealthcareProviderNpi.IsActive`/`EffectiveFrom`/`EffectiveTo` (new-NPI gating), `Identifier.RecordTypeId` (RT `PRM_Practitioner`), `Identifier.PRM_Pending__c`, `HealthcareProviderTaxonomy.ProviderType` (primary-only) and the `FinalName` taxonomy name, plus `PRM_RecordKey__c` (NPI‑anchored). FK fields (`AccountId`, `PractitionerId`, `ParentRecordId`, `PRM_CaseManager__c`) are set **in-service** from the batch-provided Ids.

> **Field coverage check:** `practitionerInfo.*` → HealthcareProvider + HealthcareProviderNpi; `taxonomies[].*` → HealthcareProviderTaxonomy; `identifiers[].*` → Identifier; the E1 Ids `{accountId, practitionerId, caseManagerId}` → the FK columns. `existingHcpNpiId` drives the new-vs-existing NPI gating.

---

## 6. Field maps (grounded — per practitioner)

**HealthcareProvider** (from fused DR):

| Field                           | Source                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------ |
| `AccountId`                     | `accountId` (FK, in-service)                                                          |
| `PractitionerId`                | `practitionerId`                                                                      |
| `Name`                          | ⟲ `CONCAT(NameNormalize(firstName), ' ', NameNormalize(lastName))` (not a raw input) |
| `Status`                        | ⟲ formula `HCPStatus = IF(IsActive,"Active","InActive")`                             |
| `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.effectiveFrom` / `effectiveTo`                                     |
| `PRM_CaseManager__c`            | `caseManagerId`                                                                       |
| `PRM_RecordKey__c`              | ⟲ `{npi}` (dedupe — §2)                                                               |

**HealthcareProviderNpi** (from `PRMDRPHCPNPIBoardCretIdentifier`):

| Field                           | Source                                                               |
| ------------------------------- | -------------------------------------------------------------------- |
| `AccountId`                     | `accountId`                                                          |
| `PractitionerId`                | `practitionerId`                                                     |
| `Npi` / `Name`                  | `practitionerInfo.npi` (`Npi` = dedupe pre‑check key — §2)           |
| `NpiType`                       | `practitionerInfo.npiType`                                           |
| `IsActive`                      | ⟲ formula `IF(ISBLANK(existingHcpNpiId), isActive, null)`            |
| `EffectiveFrom` / `EffectiveTo` | ⟲ formula `IF(ISBLANK(existingHcpNpiId), hcpEffectiveFrom/To, null)` |
| `PRM_CaseManager__c`            | `caseManagerId`                                                      |

> New-vs-existing NPI: when `existingHcpNpiId` is supplied the DR sets `Id = existingHcpNpiId` and **nulls** active/effective → `npi.IsActive = String.isBlank(existingHcpNpiId) ? isActive : null;` etc.

**Identifier** (from `PRMDRPHCPNPIBoardCretIdentifier` + `PRMDRCreateIdentiferAndDocument`):

| Field                                         | Source                                                 |
| --------------------------------------------- | ------------------------------------------------------ |
| `RecordTypeId`                                | ⟲ formula RT `PRM_Practitioner` (Identifier)           |
| `IdValue`                                     | `identifiers[].name`                                   |
| `PRM_Type__c`                                 | `identifiers[].type`                                   |
| `ParentRecordId`                              | `accountId`                                            |
| `PRM_Active__c`                               | `practitionerInfo.isActive`                            |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | `practitionerInfo.hcpEffectiveFrom` / `hcpEffectiveTo` |
| `PRM_CaseManager__c`                          | `caseManagerId`                                        |
| `PRM_Pending__c`                              | ⟲ formula `IF(type!="Document", true, false)`          |
| `PRM_RecordKey__c`                            | ⟲ `{npi}_{type}_{idValue}` (dedupe — §2)             |

**HealthcareProviderTaxonomy** (from fused DR + `PRMDRTransDelegatedTaxonomyData`):

| Field                           | Source                                                                                 |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `AccountId`                     | `accountId`                                                                            |
| `PractitionerId`                | `practitionerId`                                                                       |
| `TaxonomyId`                    | `taxonomies[].careTaxonomyId` (resolve from `taxonomyCode` via `PRM_TaxonomySelector`) |
| `Name`                          | `taxonomies[].name` ⟲ or `FinalName = name + " - " + taxonomyCode`                     |
| `IsPrimaryTaxonomy`             | `taxonomies[].isPrimary` (⟲ `isPrimary = FinalName == primaryTaxonomy`)                |
| `IsActive`                      | `practitionerInfo.isActive`                                                            |
| `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.effectiveFrom` / `effectiveTo`                                       |
| `PRM_CaseManager__c`            | `caseManagerId`                                                                        |
| `PRM_RecordKey__c`              | ⟲ `{npi}_{taxonomyCode}` (dedupe — §2)                                                |

### IP grounding (active IP → DR input mappings)

Verified from the active IPs. Upstream Ids (both branches) come from the **E1 element `DRPAccountCaseCaseManagerCreation`** → the batch context Ids; business data comes from the `**RecordsToUpdate**` payload node; names are normalized via `RA_TitleCase` → `PRM_FormSubUtility.NameNormalize`.

**IBC — `PRM_PractitionerCreation` v3 → `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense`:**

| DR input                                     | IP source                                                          | E2 mapping                                       |
| -------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------ |
| `Account`                                    | `DRPAccountCaseCaseManagerCreation:AccountId`                      | `accountId`                                      |
| `Practitioner`                               | `DRPAccountCaseCaseManagerCreation:PersonContactId`                | `practitionerId`                                 |
| `CaseManager`                                | `DRPAccountCaseCaseManagerCreation:CaseManagerId`                  | `caseManagerId`                                  |
| `HCPName`                                    | `CONCAT(RA_TitleCase:firstName,' ',RA_TitleCase:lastName)`         | ⟲ `NameNormalize(first)+' '+NameNormalize(last)` |
| `HCPTaxonomyName` / `CareTaxonomy`           | `RecordsToUpdate:HCPTaxonomy:Name` / `:CareTaxonomy`               | `taxonomies[].name` / `careTaxonomyId`           |
| `BusinessLicense`                            | `RecordsToUpdate:BusinessLicense` (direct)                         | E5                                               |
| `IsActive` / `EffectiveFrom` / `EffectiveTo` | `RecordsToUpdate:IsRecordActive` / `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.*`                             |

**Delegated — `PRM_DelegatedPractitionerCreation` v7:**

`PRMDRPHCPHCPTaxonomyAndBusineessLicense` — same as IBC **except**: `BusinessLicense` ← `LA_MergeBusinessLicense` (DEA/CDS + SBRD merge — E5), `TaxonomyData` ← `DRTTaxonomyData` (transform `PRMDRTransDelegatedTaxonomyData` output — E4), plus `ProviderType` ← `RecordsToUpdate:ProviderType`.

`PRMDRPHCPNPIBoardCretIdentifier`:

| DR input                                           | IP source                                                                                 | E2 mapping                                             |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `HCPNPI`                                           | `RecordsToUpdate:HCPNPI`                                                                  | `practitionerInfo.npi`                                 |
| `HCPNPIId`                                         | `RecordsToUpdate:HCPNPIId`                                                                | `practitionerInfo.existingHcpNpiId` (gating)           |
| `HCPEffectiveFrom` / `HCPEffectiveTo`              | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`                                           | `practitionerInfo.hcpEffectiveFrom` / `hcpEffectiveTo` |
| `IsActive`                                         | `RecordsToUpdate:IsRecordActive`                                                          | `practitionerInfo.isActive`                            |
| `AccountId` / `PractitionerId` / `IndividualAppId` | `DRPAccountCaseCaseManagerCreation:AccountId` / `PersonContactId` / `CaseManagerId`       | batch context Ids                                      |
| `HealthcareProviderId`                             | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId` (HCP DR output) | ← created HCP Id (feeds E7 BoardCert)                  |
| `Identifiers`                                      | `IF(ISNOTBLANK(Identifiers\|1:Name), RecordsToUpdate:Identifiers, '')`                    | `identifiers[]` gated on first element `name`          |
| `BoardCertifications`                              | `LIST(RecordsToUpdate:BoardCertifications)`                                               | E7                                                     |

> **Branch differences:** IBC feeds taxonomy/license **directly** from the payload (no transform); Delegated routes taxonomy through the **`DRTTaxonomyData` transform** and license through the **`LA_MergeBusinessLicense`** merge, and adds `ProviderType`, `Identifiers`, `BoardCertifications`. **Ordering:** the NPI/Identifier/BoardCert DR consumes `HealthCareProviderId` from the HCP DR output → **HCP must be inserted before NPI/Identifier**.

**Formulas → Apex:**

- `HCPName` = `PRM_FormSubUtility.NameNormalize(firstName) + ' ' + PRM_FormSubUtility.NameNormalize(lastName)`.
- `HCPStatus` = `isActive ? 'Active' : 'InActive'`.
- NPI gating = `String.isBlank(existingHcpNpiId) ? value : null` (IsActive / EffectiveFrom / EffectiveTo).
- Identifier `RecordTypeId` via cached describe (`PRM_Practitioner`); `PRM_Pending__c = !'Document'.equals(type)`; Identifiers gated on first element having a `name`.
- Taxonomy: IBC direct; Delegated via transform — `FinalName = name + ' - ' + taxonomyCode`; `IsPrimaryTaxonomy = (FinalName == primaryTaxonomy)`; `ProviderType = isPrimary ? providerType : null`.
- `PRM_RecordKey__c` (dedupe — §2): `{npi}` (HCP) / `{npi}_{type}_{idValue}` (Identifier) / `{npi}_{taxonomyCode}` (Taxonomy).

---

## 7. DML / order (idempotent)

Account/Practitioner/CaseManager exist (E1). Process in dependency order, **one bulk DML per object type** across the whole chunk; idempotency per §2 — **`upsert` by `PRM_RecordKey__c`** for HCP/Identifier/Taxonomy, **pre‑check on `Npi`** for the NPI object:

1. **Upsert `HealthcareProvider`** (FK `AccountId`, `PractitionerId`) by `PRM_RecordKey__c`.
2. **Insert `HealthcareProviderNpi`** for NPIs **not already present** (pre‑check on `Npi` over the chunk's NPIs; skip existing).
3. **Upsert `Identifier[]`** (FK `ParentRecordId` = Account) by `PRM_RecordKey__c`.
4. **Upsert `HealthcareProviderTaxonomy[]`** (FK `AccountId`, `PractitionerId`) by `PRM_RecordKey__c`.

No circular FKs here (all reference E1 records), so no back-link updates are needed. `upsert` populates `Id` on the passed instances, so `PractUow` correlation still holds and the `HealthcareProvider` Id feeds E7 (BoardCertification). Returns `healthcareProviderId`, `healthcareProviderNpiId`, `identifierIds`, `taxonomyIds` (per practitioner).

---

## 8. Open items / clarifications

- ✅ **Bulkification contract (§4.1) — resolved.** Input is `params.practitioners[]`; `practitionerInfo.id` = Account Id (FK resolution); `practitionerId` resolved via one bulk Account query; `PractUow` reference correlation.
- ⚠ **`caseManagerId` FK source must be stable, not `Account.PRM_CaseManager__c`.** That Account lookup is **mutable** (a "latest" pointer), so the `PRM_CaseManager__c` FK on E2's records should be taken from the **`PRM_AsyncJobRecords__c`** row (the batch scope, stable per submission), not re‑derived from the Account. `practitionerId` (`PersonContactId`) is fine from the Account. Reconcile §4.1/§4.2 when wiring the batch.
- **How the batch builds `practitioners`** — `PractitionerBatch` reads the job payload (`jsonFileParser`) and must pass each practitioner node **with `practitionerInfo.id` = the E1 Account Id** (FK resolution) and **`practitionerInfo.npi`** (the dedupe anchor). Confirm the batch enriches the payload with the E1 Account Id (or that intake wrote it back into the stored payload).
- ✅ **CL‑E2 (NPI uniqueness) — resolved: NPI is unique (business‑confirmed), anchor kept on NPI.** A concern was raised that duplicate practitioner Accounts could share one NPI (a terminated‑then‑recreated practitioner re‑entered with a slightly different name — comma/special chars). **Business confirmed there are no duplicate NPIs**, so the dedupe key stays **NPI‑anchored** (durable, reusable). *(Contingency: if duplicate NPIs ever surface, switch the anchor to `accountId` — `{accountId[_natural]}` + an `AccountId`+`Npi` pre‑check — to keep distinct practitioners from collapsing.)*
- ✅ **Idempotency (§2) — decided: hybrid, NPI‑anchored.** `PRM_RecordKey__c` (External Id, Unique) on **HealthcareProvider / Identifier / HealthcareProviderTaxonomy** (`upsert`); **pre‑check on `Npi`** for HealthcareProviderNpi (no new field). **Epic A schema + permission‑set dependency — see §3 work items.** Decision trail: not reusable `accountId`/`caseManagerId`/`PRM_AsyncJobRecords__c.Id` (internal/mutable/ephemeral) nor existing `PRM_ExternalId__c`/`SourceSystemIdentifier` (owned by other integrations; Identifier's is ~31% populated on IBXDEV01).
- ⚠ **No‑NPI policy** — NPI is the dedupe anchor; decide reject‑at‑intake (recommended) vs a fallback key for practitioners without an NPI.
- **CL‑E1** — IBC NPI/Identifier source gap: confirm IBC field values (default: reuse the Delegated maps).
- **Taxonomy resolution** — `taxonomies[].careTaxonomyId` from `taxonomyCode` via `PRM_TaxonomySelector` (EPIC D); confirm selector availability.
- **Identifier RT via `PRM_FormSubUtility.recordTypeId` / `PRM_TaxonomySelector`** — cached describe + selectors (CL‑E5 resolved).
- **Existing-NPI path** — `existingHcpNpiId` gating (insert vs reuse) — confirm whether in pilot scope (parallels E1's deferred existing-account path).
- **Org schema validation** — *not yet run for E2.* Validate `HealthcareProvider` / `HealthcareProviderNpi` / `Identifier` / `HealthcareProviderTaxonomy` field API names, types, and required flags against IBXDEV01 (as done for E1).

---

## 9. Definition of Done

- [x] **Prerequisite work items (§3) — E02's own — deployed ✅:** `PRM_RecordKey__c` (External Id, Unique) on HealthcareProvider/Identifier/HealthcareProviderTaxonomy + FLS added to `PRM_AsyncJob_Access`.
- [ ] `PRM_PractitionerService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the batch chunk: build all records first, **one bulk DML per object type** (no DML/SOQL/describe in loops).
- [ ] Per-practitioner correlation via wrapper references (E1 pattern).
- [ ] Formulas computed in-service (HCPName, HCPStatus, NPI gating, Identifier RT/Pending, taxonomy primary/providerType, `PRM_RecordKey__c`).
- [ ] HCP upserted before NPI/Identifier/Taxonomy (feeds E7).
- [ ] **Idempotent (§2), NPI‑anchored:** `upsert` by `PRM_RecordKey__c` (HCP/Identifier/Taxonomy) + pre‑check on `Npi` (NPI object); re-running the service produces **no duplicates**.
- [ ] No‑NPI handled per the chosen policy (reject/fallback).
- [ ] `caseManagerId` FK sourced from `PRM_AsyncJobRecords__c` (not the mutable Account back‑link).
- [ ] Returns per-practitioner Ids for downstream services (E5/E6/E7/E8).
- [ ] `<Class>Test` ≥ 85% incl. (a) a bulk test (251+ practitioners) asserting governor-safe DML counts and (b) a **re-run/idempotency test** (execute twice → record counts unchanged).
- [ ] Field API names/types validated against the org.
