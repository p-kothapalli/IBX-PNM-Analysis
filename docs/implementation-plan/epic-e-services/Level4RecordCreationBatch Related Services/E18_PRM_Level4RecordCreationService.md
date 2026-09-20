# E18 · `PRM_Level4RecordCreationService` — *2.0 d* · Branch: BOTH · *(Level4RecordCreationBatch · seq 5)*

> **Parent:** `Epic_E_Practitioner_Services_Part3.md` (Part 3). Shared conventions in **Part 1 §E0.1–E0.2 / §E0.4**. **Batch:** runs inside **`PRM_Level4Batch`** (seq 5, `E23_PRM_Level4Batch.md`), after `PLRelatedBatch` (seq 4) built the affiliations/features.
> **Writes:** **`HealthcareFacilityNetwork`** — **RT `PRM_FacilityPractitionerTxNw`** ("Practitioner at Practice Location Taxonomy and Network") — the **Level‑4** record: one per **(practitioner × location × network × taxonomy × role)**.
>
> **✅ Org‑grounded (IBXDEV01).** Legacy: the active Load DR **`PRMDRPFacilityPractitionerTxNw`** (`0jIOv0000002bl3MAA`); an existing batch **`PRM_NetworkCreationBatch`** (+ `PRM_NetworkCreationHelper`/`Envelope`/`Row`) implements the same creation from Vlocity. **We build a NEW async service+batch** (per decision) rather than reuse it.
>
> **⚡ Trigger cascade (decisive):** on insert of a **TxNw** row, the active **`PRM_HealthcareFacilityNetworkTrigger` → `PRM_HCFacilityNetworkTriggerHelper`** auto‑creates the downstream **`PRM_FacilityNw` (Practice Location Network)** *and* **`PRM_FacilityTx` (Practice Location Taxonomy)** rows (deduped) **and populates *their* `SourceSystemIdentifier`**. So **E18 creates ONLY the TxNw row**; the network + taxonomy (the former "E17") are a **trigger side‑effect**. The trigger does **not** set the TxNw's own `SourceSystemIdentifier` → **E18 owns it** (idempotency, §2).
>
> **⚠ Tags: [CONFIRMED] · [OPEN] · [RISK] · [RECOMMENDATION].**

---

## 1. Role & cardinality

- Runs inside **`Level4RecordCreationBatch`** (seq 5). By seq 5: practitioner core (seq 1), group + HealthcareFacility graph (seq 2), affiliations + features (seq 4) all exist.
- **✅ Writes ONLY `HealthcareFacilityNetwork` RT `PRM_FacilityPractitionerTxNw`** (Level‑4). The HFN trigger cascades `PRM_FacilityNw` + `PRM_FacilityTx` — **E18 must NOT create those** (would duplicate the trigger's output).
- **✅ Grain (decided): one TxNw per (network × taxonomy × role) combination per practitioner.** A `networkTaxonomyRoles[]` entry's **`networkName`, `careTaxonomyCode`, and `role`** may each be **`;`‑separated** (e.g. `role = "PCP"` **or** `"PCP;Specialist"`) → the batch (**E23**) **splits all three on `;`, trims, and builds the full cross‑product** (`networkName × careTaxonomyCode × role`), emitting one **atomic** E18 `networks[]` row per combination. *(Mirrors the legacy `PRM_NetworkCreationBatch` role×network fan‑out, extended to taxonomy.)* **E18 itself receives atomic rows** (one network, one taxonomy, one role) — the split/cross‑product is an E23 responsibility.
- **Branch:** BOTH.
- **⚡ The trigger MUST fire.** The trigger early‑returns when `PRM_TriggerContextControl.inBulkContext()` is true. E18/E23 must run with **bulk context OFF** so the cascade (FacilityNw + FacilityTx) happens. Factor the trigger's dedupe SOQL + inserts into the governor budget → **`BatchSize = 1`** (E23).

> **Bulkification.** Build all TxNw rows for the chunk in memory, one bulk DML. No DML/SOQL in loops (the trigger's own SOQL is separate + budgeted).

---

## 2. Idempotency (re-run safe) — **required**

> **Why:** Epic C retry re‑runs the whole batch; E18 must not duplicate Level‑4 rows.

> **🔎 Org:** `HealthcareFacilityNetwork.SourceSystemIdentifier` = **`Unique`, `externalId=False`, `idLookup=True`, length 255**. Unique but **not** an External Id → **cannot `upsert` on it**; **pre‑check + insert**, with the Unique constraint as a race backstop.

**✅ Decided approach — set a deterministic Unique `SourceSystemIdentifier` + pre‑check:**
- **`SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}`** (record Ids + code + role; `_` delimiter). *(Replaces `{npi}` with the practitioner **record Id** — the TxNw is per‑practitioner, so a practitioner discriminator is required for Unique‑ness across practitioners at the same location/network/taxonomy/role. Confirmed.)*
- **Pre‑check** existing TxNw by `SourceSystemIdentifier IN :keys AND RecordTypeId = PRM_FacilityPractitionerTxNw` → **insert only the misses**.
- Insert with **`Database.insert(rows, false)`**; treat a `DUPLICATE_VALUE` error as "already exists" (idempotent no‑op) — covers the parallel‑race edge even though `BatchSize=1` avoids it.

> **⚠ [OPEN — OQ‑E18‑1b]** Pre‑check owner — **service** (recommended, like E14/E15/E16/E19) or **batch**. The service self‑pre‑checks by `SourceSystemIdentifier`.

---

## 3. Prerequisite work items — schema + access

| WI | Task | Object | Status |
|---|---|---|---|
| WI‑1 | **No new field** — reuse the existing Unique `SourceSystemIdentifier` (set by E18, pre‑checked) | `HealthcareFacilityNetwork` | ✅ (field exists) |
| WI‑2 | Confirm FLS on `PRM_AsyncJob_Access` for the fields E18 writes | `PRM_AsyncJob_Access` | ◻ confirm |

### 3.1 🔎 Org validation (IBXDEV01)

- **RTs on `HealthcareFacilityNetwork`:** `PRM_FacilityPractitionerTxNw` (**E18**, "Practitioner at Practice Location Taxonomy and Network"), `PRM_FacilityNw` ("Practice Location Network" — trigger), `PRM_FacilityTx` ("Practice Location Taxonomy" — trigger), `PRM_TaxonomyNetworkException`.
- **Fields (E18 writes):** `Name` **required** (string, ≤80 used by legacy). `HealthcareFacilityId` → HealthcareFacility. `AccountId` → Account. `PractitionerId` → **Contact**. `PayerNetworkId` → **HealthcarePayerNetwork**. `PRM_Taxonomy__c` → **CareTaxonomy**. `PRM_PractitionerRole__c` = **picklist `PCP` / `Specialist`**. `PRM_CaseManager__c` → IndividualApplication. `EffectiveFrom`/`EffectiveTo` = date.
- **REQUIRED booleans (`nillable=false`):** `IsActive` (default false), `PRM_Pending__c` (default false), `PRM_Primary__c` (default false).
- **`SourceSystemIdentifier`** = Unique, **not** extId (idempotency handle, §2).

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. Per §E0.4 + the `prm-service-class-boundaries` rule, **context is batch‑injected**; the service builds + bulk‑DMLs (existence pre‑check per OQ‑E18‑1b).

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.networks`** | `List<Object>` — each `{ practitionerId, practitionerName, healthcareFacilityId, facilityName, accountId, payerNetworkId, careTaxonomyId, careTaxonomyCode, careTaxonomyName, role, isPrimarySpecialty, isActive, effectiveFrom, effectiveTo, caseManagerId }` (all Ids **batch‑resolved**) |
| **Output `response.networks`** | `List<Map<String,Object>>` (input order): `{ healthcareFacilityId, payerNetworkId, careTaxonomyCode, role, healthcareFacilityNetworkId }` |

### 4.1 Correlation & Id resolution (batch‑injected — §E23)

The **batch** (`E23`) resolves and injects per network row: `practitionerId` (PersonContact) + `practitionerName` (Account), `healthcareFacilityId` (via shared `PRM_FormSubUtility.computeHcfExternalId` + bulk query) + `facilityName`, `accountId` (= `HealthcareFacility.AccountId`, group), `payerNetworkId` (`networkName` → `HealthcarePayerNetwork.Name`, exact match), `careTaxonomyId` (`careTaxonomyCode` → `CareTaxonomy`), `careTaxonomyName`, `role`, `isPrimarySpecialty` (correlated `careTaxonomyCode` → `practitioner.taxonomies[].isPrimarySpecialty`), `isActive`/effective dates/`caseManagerId`. The service does **no SOQL** except the idempotency pre‑check (OQ‑E18‑1b).

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_Level4RecordCreationService extends PRM_ServiceBase {
    public class PRM_Level4Exception extends Exception {}
    private static final String RT_TXNW = 'PRM_FacilityPractitionerTxNw';

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'networks' => new List<Map<String,Object>>() };
        List<Object> networks = (params == null) ? null : (List<Object>) params.get('networks');
        if (networks == null || networks.isEmpty()) { return response; }

        // 1) parse + validate; compute SourceSystemIdentifier per row (no SOQL/DML in loop)
        //    ssid = practitionerId _ healthcareFacilityId _ payerNetworkId _ careTaxonomyCode _ role
        // 2) pre-check existing TxNw by SourceSystemIdentifier IN :keys AND RecordTypeId = RT_TXNW (OQ-E18-1b)
        // 3) build HealthcareFacilityNetwork (RT_TXNW) for the MISSES:
        //    RecordTypeId (PRM_FormSubUtility.recordTypeId), Name (concat, <=80), SourceSystemIdentifier,
        //    HealthcareFacilityId, AccountId, PractitionerId, PayerNetworkId, PRM_Taxonomy__c,
        //    PRM_PractitionerRole__c, PRM_Primary__c(=isPrimarySpecialty), IsActive, EffectiveFrom/To,
        //    PRM_CaseManager__c, PRM_Pending__c(=false). Required booleans never null.
        // 4) Database.insert(rows, false) — tolerate DUPLICATE_VALUE as already-exists (idempotent)
        //    ⚡ trigger fires here -> creates PRM_FacilityNw + PRM_FacilityTx (do NOT create them in E18)
        // 5) response (input order) with healthcareFacilityNetworkId
        return response;
    }
}
```

---

## 5. Expected input format

E18 consumes **batch‑injected `networks[]`** derived from `practitioner.groups[].locations[].networkTaxonomyRoles[]` (one row per entry).

```json
{
  "networks": [
    { "practitionerId": "003...", "practitionerName": "Jane Smith",
      "healthcareFacilityId": "0Gx...", "facilityName": "Riverbend Family Health - Cherry Hill",
      "accountId": "001...", "payerNetworkId": "0Pn...",
      "careTaxonomyId": "0Ct...", "careTaxonomyCode": "207Q00000X", "careTaxonomyName": "Family Medicine",
      "role": "PCP", "isPrimarySpecialty": true,
      "isActive": true, "effectiveFrom": "2026-03-10", "effectiveTo": null, "caseManagerId": "0P8..." }
  ]
}
```

> **Source (E23 maps):** `networkTaxonomyRoles[]` `{ networkName, careTaxonomyCode, role }` per location — **all three may be `;`‑separated** (`role` = `"PCP"` or `"PCP;Specialist"`); E23 **splits each + cross‑products** into one row per `(network × taxonomy × role)` combination, then resolves `networkName`→`payerNetworkId`, `careTaxonomyCode`→`careTaxonomyId`(+name), HCF via `computeHcfExternalId`, `isPrimarySpecialty` from the practitioner's taxonomy (per split code). **Service‑computed:** RT, `Name`, `SourceSystemIdentifier`, `PRM_Pending__c=false`. Required booleans always set.

---

## 6. Field map (✅ grounded — `PRMDRPFacilityPractitionerTxNw` `0jIOv0000002bl3MAA` + legacy `PRM_NetworkCreationBatch.buildHfnRecord`)

| `HealthcareFacilityNetwork` field | Source | Notes |
|---|---|---|
| `RecordTypeId` | ⟲ `PRM_FacilityPractitionerTxNw` | `PRM_FormSubUtility.recordTypeId(HealthcareFacilityNetwork.SObjectType, 'PRM_FacilityPractitionerTxNw')` |
| `Name` | ⟲ `CONCAT(practitionerName, ' - ', networkName, ' - ', careTaxonomyName, ' - ', role, ' at ', facilityName)` (**≤80**) | required |
| `SourceSystemIdentifier` | ⟲ `{practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` | **Unique — idempotency (§2)** |
| `HealthcareFacilityId` | injected `healthcareFacilityId` (E13/E21) | |
| `AccountId` | injected `accountId` (= `HealthcareFacility.AccountId`, group) | |
| `PractitionerId` | injected `practitionerId` (PersonContact) | |
| `PayerNetworkId` | injected `payerNetworkId` (`networkName`→`HealthcarePayerNetwork`) | exact match |
| `PRM_Taxonomy__c` | injected `careTaxonomyId` (`careTaxonomyCode`→`CareTaxonomy`) | |
| `PRM_PractitionerRole__c` | injected `role` | picklist `PCP`/`Specialist` |
| `PRM_Primary__c` | injected `isPrimarySpecialty` | ⚠ REQUIRED (never null) |
| `IsActive` | injected `isActive` | ⚠ REQUIRED |
| `EffectiveFrom` / `EffectiveTo` | injected `effectiveFrom` / `effectiveTo` | |
| `PRM_CaseManager__c` | injected `caseManagerId` | IndividualApplication |
| `PRM_Pending__c` | ⟲ `false` | ⚠ REQUIRED (default) |

> **Not created by E18 (trigger‑owned):** `PRM_FacilityNw` + `PRM_FacilityTx` rows and *their* `SourceSystemIdentifier` (`PRM_HCFacilityNetworkTriggerHelper.populateSourceSystemIdentifierNw/Tx`, formula `facility.PRM_ExternalId__c + '-' + …`). E18 must not build them.

---

## 7. DML / order (idempotent)

Practitioner/HealthcareFacility/PayerNetwork/CareTaxonomy resolved (E23). **One bulk insert** of `HealthcareFacilityNetwork[]` (RT `PRM_FacilityPractitionerTxNw`), gated by the `SourceSystemIdentifier` pre‑check (§2). ⚡ **The HFN trigger fires on insert** → creates `PRM_FacilityNw` + `PRM_FacilityTx` (deduped) — budget its SOQL/DML (E23 runs `BatchSize=1`). Returns `healthcareFacilityNetworkId` per network row.

> **No CMA / CDM (decided).** E18/E23 do **not** create `PRM_CaseManagerAssociation__c` or update `PRM_CaseDataManager__c` for these records (per decision). *(If needed later: CMA RT `Practitioner_at_Practice_Location_Taxonomy_and_Network` + CDM token `HealthcareFacilityNetwork`.)*

---

## 8. Open items / clarifications

- **✅ OQ‑E18‑1 — Idempotency — DECIDED:** Unique `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` + pre‑check + insert‑misses (not `upsert`; field is Unique but not extId). **OQ‑E18‑1b** — pre‑check owner (service, recommended).
- **✅ OQ‑E18‑2 — Scope — DECIDED:** E18 creates **only** the TxNw; the trigger cascades `FacilityNw` + `FacilityTx`. E18 must let the trigger fire (bulk‑context OFF).
- **✅ OQ‑E18‑3 — `isPrimarySpecialty` — DECIDED:** from `practitioner.taxonomies[].isPrimarySpecialty`, correlated by `careTaxonomyCode` (E23).
- **OQ‑E18‑4 — `CareTaxonomy` code field.** Confirm the `CareTaxonomy` field that holds `careTaxonomyCode` (e.g. `Code`) for the E23 lookup — **validate API name in‑org**.
- **OQ‑E18‑5 — `PRM_PractitionerRole__c` values.** Source `role` must be exactly `PCP`/`Specialist` (picklist). Confirm intake always sends these (else map).
- **OQ‑E18‑6 — Effective dates + `PRM_Pending__c`/`IsActive` source.** Confirm batch injects the practitioner `effectiveFromDate`/`effectiveTo`, `isActive`, and `PRM_Pending__c=false` (legacy default).
- **✅ OQ‑E18‑8 — Multi‑value `networkTaxonomyRoles` — DECIDED:** `networkName`, `careTaxonomyCode`, **and `role`** may each be **`;`‑separated** (`role` = `"PCP"`/`"Specialist"`/`"PCP;Specialist"`); **E23 splits all three + builds the cross‑product** (`network × taxonomy × role`) → one **atomic** E18 row per combination (E18 sees single values). `SourceSystemIdentifier` per atomic combination stays Unique.
- **OQ‑E18‑7 — Target org / batch / effort (2.0 d).**

*(Org‑validated: RTs, required booleans, `SourceSystemIdentifier` Unique/not‑extId, field targets/types; trigger cascade + SSID population from `PRM_HCFacilityNetworkTriggerHelper`; field map from DR `0jIOv0000002bl3MAA` + `PRM_NetworkCreationBatch`.)*

---

## 9. Definition of Done

- [ ] OQ‑E18‑1…8 resolved *(✅ 1 idempotency SSID composite, ✅ 2 TxNw‑only + trigger cascade, ✅ 3 isPrimarySpecialty, ✅ 8 E23 splits `;` + cross‑products; confirm 4 CareTaxonomy code field, 5 role picklist, 6 date/active source, 7 org)*.
- [ ] E18 rows are **atomic** (single network/taxonomy/role); E23 owns the `;`‑split + cross‑product (OQ‑E18‑8).
- [ ] `PRM_Level4RecordCreationService extends PRM_ServiceBase`; `execute(...)` — writes **only** TxNw; lets the HFN trigger cascade `FacilityNw`+`FacilityTx`.
- [ ] Bulk over the chunk; **one bulk insert**; batch‑injected context; required booleans never null.
- [ ] Idempotent: `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}`; pre‑check + insert‑misses; `DUPLICATE_VALUE` tolerated; re‑run creates no duplicate.
- [ ] Field map per §6 (DR‑grounded); `Name` ≤80; `PRM_Primary__c`←`isPrimarySpecialty`; `PRM_PractitionerRole__c`∈{PCP,Specialist}.
- [ ] Bulk‑context OFF so the trigger fires; governor budget validated with `BatchSize=1` (trigger cascade SOQL/DML).
- [ ] Returns `healthcareFacilityNetworkId` per network row.
- [ ] `PRM_Level4RecordCreationServiceTest` ≥ 85% incl. bulk, re‑run/idempotency, required‑boolean, DUPLICATE_VALUE tolerance, trigger‑cascade smoke (FacilityNw+FacilityTx created).
- [ ] Field API names/types validated against the org (esp. OQ‑E18‑4 CareTaxonomy code).
