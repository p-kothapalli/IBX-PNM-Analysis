# E15 · `PRM_ProviderFeatureService` — *1.5 d* · Branch: BOTH · *(PLRelatedBatch · seq 4)*

> **Parent:** `Epic_E_Practitioner_Services_Part3.md` (Part 3). Shared conventions in **Part 1 §E0.1–E0.2 / §E0.4**.
> **Batch:** runs inside **`PLRelatedBatch`** (seq 4), after the HealthcareFacility graph (E13/E21). **Writes:** `PRM_ProviderFeature__c` — **TWO record types: `PRM_AssistiveAid` + `PRM_AffirmingCareCategory` (ACC)** (both org‑verified created by the active IP). One service, mixed‑RT bulk DML.
> **Legacy (active — ✅ org‑verified):** the active orchestrator is the IP **`PRMPractitionerAddressCreation` v5** (`0jNOv000000ICkIMAW`), which runs **`PRMDRTransformPFAA`** (Transform, `0jIOv0000000UPVMA2`) → **`PRMDRCreateProviderFeatureAssitiveAids`** (Load, `0jIOv0000000UNtMAM`) for assistive aids. *(The doc's earlier `PRMDRPostProviderFeatureAsstAids`/`PRMDRTransformAsstAids` exist but are **not** used by the active address‑creation IP — stale chain.)*
>
> **✅ OQ‑E15‑10 RESOLVED — E15 owns BOTH AssistiveAid + ACC.** The active IP creates ACC via `PRMDRCreateProviderFeatureACC` (Load, `0jIOv0000000R6fMAE`) + `PRMDRTransformProviderFeatureACC`. The ACC map is **near‑identical** to AsstAids (same object, same links) — only the RT, `Name` default, target multipicklist, and `PRM_IsDirectoryPrint__c` differ (§6.2). So E15 builds a **mixed‑RT list** in **one bulk DML**. *(This IP also creates Facility Networks, Info Codes, and Case Data Manager — see §1.1, owned elsewhere.)*
> **⚠ Nothing is assumed — every gap is an Open Question (§8). Tags: [CONFIRMED] · [OPEN] · [RISK] · [RECOMMENDATION] · Pending Clarification.**

---

## 1. Role & cardinality

- Runs inside **`PLRelatedBatch`** (seq 4). Creates `PRM_ProviderFeature__c` for each location, in **two record types**:
  - **`PRM_AssistiveAid`** ← location's **`capabilitiesAtLocation`** — ✅ verified: holds **display labels** (`"American Sign Language; Braille Materials"`, `"Wheelchair Accessible"`), **not** codes. Batch **maps label → `PRM_AssistiveAids__c` code** (`American Sign Language`→`AS`, `Braille Materials`→`BM`, …) — see OQ‑E15‑4. ⚠ `"Wheelchair Accessible"` has **no exact picklist label** (closest `Handicapped Accessible`=`HA`) → needs a mapping‑table entry.
  - **`PRM_AffirmingCareCategory`** ← location's **`affirmingCareCategory`** — ✅ **added to the intake JSON** (`;`‑separated labels, mostly label==value on `PRM_AffirmingCareCategory__c`). See OQ‑E15‑11.
- **✅ Grain = per location (RESOLVED — OQ‑E15‑1).** Both DRs set **only `PRM_HealthcareFacility__c`** — never `PRM_Practitioner__c` / `PRM_HealthcarePractitionerFacility__c`. → **one row per (location × record type)**; **drop** the practitioner/HPF links.
- **✅ Gate (RESOLVED — org):** AssistiveAids filters `CapabilitiesAtLocation != "Does Not Apply"` (`FILTER(LIST(%Locations%), …)`). ACC has **no such filter** in `PRMDRTransformProviderFeatureACC` → created whenever `affirmingCareCategory` is present (batch gates on non‑blank). **[OPEN — OQ‑E15‑11]** confirm ACC gating (any "Does Not Apply" equivalent?).

> **Bulkification.** Build all feature rows in memory across the chunk, one bulk DML. No DML/SOQL in loops.

### 1.1 What the active IP `PRMPractitionerAddressCreation` v5 actually creates (✅ org‑verified, 88 elements)

The IP is a **master orchestrator** for the practice‑location graph. Its Load/Post actions create (grouped by our service):

| Records created (DR bundle) | Object | Our owner |
|---|---|---|
| `PRMDRCreatePractitioner*AddressRecords*Delg` (new / add‑address / diff‑NPI / same‑NPI) | Address/Location | **E13** |
| `PRMDRCreateHealthcarePractitionerFacilityDelg` | HealthcareFacility | **E13** |
| `PRMDRCreatePPLForPPADelg` (`CreatePractitionerPracticeLocation`) | HPF · RT PLA | **E14** |
| `PRMDRCreateHCPFForPractitionerPracAffiliationDelg` + `PRMUpdatePracticeToPractitionerDelg` (update) | HPF · RT PPA | **E14** |
| `PRMDRCheckIfPracticeToPractitionerExist` (Extract) | — (idempotency pre‑check) | **E14** |
| `PRMDRCreateProviderFeatureAssitiveAids` (+ `PRMDRTransformPFAA`) | ProviderFeature · RT AssistiveAid | **E15** |
| `PRMDRCreateProviderFeatureACC` / `PRMDRPProviderFeatureACC` / `PRMDRCreatePracProviderFeatureACC` (+ ACC transforms) | ProviderFeature · RT ACC | **⚠ OQ‑E15‑10** (unowned) |
| `PRMDRCreatePractitionerFacilityNetwork`, `PRMDRPracCreateHCFacilityNetworkRecordNewGroup`, `PRMDRCreatePracHealthCareFacilityNetworkForGroup` | Practitioner/Facility Network | **E17/E18** |
| `PRMLoadInfoCodeAssigned`, `PRMLoadInfoCodeAssignedPracFacilities` | Info Code Assigned | **separate service** (OQ‑E13‑13) |
| `PRMDRPCaseDataManager` (`UpdateCaseManager*` / `UpdateCaseDataManager`) | CaseManager / CDM | **E16** |
| `PRM_OmniUtils.updateExistignHCPNPI` (Remote) | HealthcareProvider NPI | **E3/E13** |

> **Branching:** the IP forks on **new group / existing group‑same‑NPI / existing group‑diff‑NPI / new practice location for existing group** (conditional blocks + list merges). E15's per‑location output is the same across these; the branches differ only in how the location/address is created (E13's concern).

---

## 2. Idempotency (re-run safe) — **required**

> **🔎 Org:** `PRM_ProviderFeature__c` has `PRM_ExternalId__c` (String, External Id, **NOT unique**) but the **active DR does NOT use it**. `PRM_AssistiveAids__c` is a **multipicklist**.

**✅ Legacy mechanism (org‑verified):** the active Load `PRMDRCreateProviderFeatureAssitiveAids` maps **`Id` (update path) — no `PRM_ExternalId__c`**. So idempotency is **Id‑based update, not extId upsert**: caller supplies the existing feature `Id` (present ⇒ update, absent ⇒ insert), same pattern as the PPA DR's `HPFId`.

**Recommended approach (matches legacy):**
- **Pre‑check on `(PRM_HealthcareFacility__c + RecordTypeId)`** — one feature per (location × RT), i.e. one `PRM_AssistiveAid` **and** one `PRM_AffirmingCareCategory` per location; supply the matched `Id` to update the multipicklist in place, else insert. *(Batch or service does the pre‑check — OQ‑E15‑1b, per the `prm-service-class-boundaries` rule.)*
- **Alternative:** populate `PRM_ExternalId__c` = `{facilityExternalId}-AssistiveAid` + `upsert`; but since the field is **not unique** and legacy doesn't use it, the pre‑check is preferred.
- **✅ OQ‑E15‑3 (create‑vs‑update / end‑dating):** the active DR has a **single Id‑based upsert path** — it **replaces the multipicklist in place** (`PRM_AssistiveAids__c` = full current set), **no end‑date‑then‑create** in this chain. The earlier "end‑date old + create new" assumption is **not** what the active DR does.

---

## 3. Prerequisite work items — schema + access

| WI | Task | Object | Status |
|---|---|---|---|
| WI‑1 | **No new field** — reuse existing `PRM_ExternalId__c` (extId) for the upsert, or pre‑check | `PRM_ProviderFeature__c` | ✅ (field exists) |
| WI‑2 | Confirm FLS on `PRM_AsyncJob_Access` for the fields E15 writes | `PRM_AsyncJob_Access` | ◻ confirm |

### 3.1 🔎 Org validation (IBXDEV01)

- RTs used by E15: **`PRM_AssistiveAid`** + **`PRM_AffirmingCareCategory`** (both created by the active IP). Also on object (unused by E15): `PRM_ConsumerDistinction`, `PRM_OnsiteServices`, `PRM_OnsiteStaffType`, `Master`. RT formula: `SELECT Id FROM RecordType WHERE DeveloperName='<PRM_AssistiveAid|PRM_AffirmingCareCategory>' AND SobjectType='PRM_ProviderFeature__c'`.
- `Name` **nullable** — DR defaults: `'Assistive Aid'` (AsstAid) / `'Affirming Care Categories'` (ACC). **`PRM_AssistiveAids__c`** (codes) + **`PRM_AffirmingCareCategory__c`** (labels) = multipicklists. `PRM_HealthcareFacility__c` → HealthcareFacility (**the only link either DR sets**). `PRM_Practitioner__c` / `PRM_HealthcarePractitionerFacility__c` — **present but NOT set** (drop from E15). `PRM_CaseManager__c` → IndividualApplication.
- **`PRM_ExternalId__c` = External Id, NOT unique** (unused by active DR). `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c` = date (nullable).
- **⚠ REQUIRED booleans (`nillable=false`) — CORRECTED:** `PRM_Active__c` (**no default → MUST be set explicitly**, DR maps ← `IsActive`), `PRM_Pending__c` (default `false`), `PRM_IsDirectoryPrint__c` (default `false`, **NOT set by the DR** → relies on default), `PRM_IsErrorRecord__c` (default `false`). *(Prior doc wrongly flagged `PRM_IsDirectoryPrint__c` as the key required one — the real must‑set is **`PRM_Active__c`**.)*

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. Per §E0.4 + the rule, **context is batch‑injected**.

| | |
|---|---|
| **Input `params.flow`** | `String` |
| **Input `params.features`** | `List<Object>` — each `{ featureType: 'AssistiveAid'\|'AffirmingCareCategory', healthcareFacilityId, caseManagerId, values[] (picklist values for the type), isActive, effectiveFrom, effectiveTo, shareInDirectory?, existingFeatureId? }` (batch‑injected) |
| **Output `response.features`** | `List<Map<String,Object>>`: `{ healthcareFacilityId, featureType, providerFeatureId }` |

### 4.1 Correlation & Id resolution (batch‑injected)

The **batch** injects, **per (location × featureType)**: `healthcareFacilityId` (E13), `caseManagerId`, `isActive`, effective dates, and the **already‑mapped picklist values** for that type. **⚠ OQ‑E15‑4 (corrected):** the intake JSON `capabilitiesAtLocation` holds **display labels** (`"American Sign Language; …"`), **not** codes — the legacy transform's `CapabilitiesAtLocationAPI` is a **derived** field. So the **batch maps label → `PRM_AssistiveAids__c` code** (`AS`,`BM`,…) before calling E15 (like E11's ISO codes). **ACC** values are full labels (mostly label==value), sourced from the new `affirmingCareCategory` node (OQ‑E15‑11). For ACC the batch also injects `shareInDirectory` → `PRM_IsDirectoryPrint__c` (default `false`). Also injects `existingFeatureId` when the pre‑check (§2) found a row. **No `practitionerId`/`hcpfId`** (per‑location grain — OQ‑E15‑1).

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_ProviderFeatureService extends PRM_ServiceBase {
    public class PRM_ProviderFeatureException extends Exception {}

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'features' => new List<Object>() };
        List<Object> features = (params == null) ? null : (List<Object>) params.get('features');
        if (features == null || features.isEmpty()) { return response; }

        // 1) build PRM_ProviderFeature__c per featureType:
        //    AssistiveAid  -> RT PRM_AssistiveAid,          Name='Assistive Aid',            PRM_AssistiveAids__c = ';'-joined codes
        //    ACC           -> RT PRM_AffirmingCareCategory, Name='Affirming Care Categories', PRM_AffirmingCareCategory__c = ';'-joined labels, PRM_IsDirectoryPrint__c<-shareInDirectory
        //    REQUIRED booleans: PRM_Active__c (<- isActive, NO default so MUST set), PRM_Pending__c (default false); IsErrorRecord default false
        // 2) idempotency: pre-check (PRM_HealthcareFacility__c + RecordTypeId) -> set Id to update in place, else insert (Id-based, matches legacy)
        // 3) ONE bulk DML over the mixed-RT list; response
        return response;
    }
}
```

---

## 5. Expected input format

E15 consumes **batch‑injected features** derived from `location.capabilitiesAtLocation` (gated non‑blank).

```json
{
  "features": [
    { "featureType": "AssistiveAid", "healthcareFacilityId": "0Gx...", "caseManagerId": "0P8...",
      "values": ["TD", "DE"], "isActive": true, "effectiveFrom": "2026-03-10", "effectiveTo": null, "existingFeatureId": null },
    { "featureType": "AffirmingCareCategory", "healthcareFacilityId": "0Gx...", "caseManagerId": "0P8...",
      "values": ["Anxiety Disorder Treatment", "LGBTQ+ Counseling/Support"], "shareInDirectory": false,
      "isActive": true, "effectiveFrom": "2026-03-10", "effectiveTo": null, "existingFeatureId": null }
  ]
}
```

> **Source:** AsstAid ← `location.capabilitiesAtLocation` (**display labels**; split `;` → trim → **map label→code** for `PRM_AssistiveAids__c`, e.g. `American Sign Language`→`AS`) gated on label `!= "Does Not Apply"`; ACC ← `location.affirmingCareCategory` (**✅ added to intake JSON**; label values) gated non‑blank (OQ‑E15‑11). The `values[]` in the contract above are the **post‑mapped** codes/labels the batch supplies. **Service‑computed:** RT, `Name` (`'Assistive Aid'` / `'Affirming Care Categories'`), `PRM_Active__c` (← isActive), `PRM_Pending__c`/`PRM_IsErrorRecord__c` (defaults); ACC also sets `PRM_IsDirectoryPrint__c` ← `shareInDirectory`. Required booleans always set.

---

## 6. Field map

### 6.1 AssistiveAid (✅ grounded — active `PRMDRCreateProviderFeatureAssitiveAids` Load, `0jIOv0000000UNtMAM`)

| `PRM_ProviderFeature__c` field | Source (DR mapping) | Notes |
|---|---|---|
| `RecordTypeId` | formula → `PRM_AssistiveAid` | `DeveloperName='PRM_AssistiveAid' AND SobjectType='PRM_ProviderFeature__c'` |
| `Id` | existing feature Id | present ⇒ **update in place**; absent ⇒ insert (idempotency §2) |
| `Name` | DEFAULT `'Assistive Aid'` | constant (not practitioner‑derived) |
| `PRM_AssistiveAids__c` | `ProviderFeature:AssistiveAids` ← transform `FilteredLocations:CapabilitiesAtLocationAPI` | multipicklist (`;`‑joined **API** values) |
| `PRM_HealthcareFacility__c` | `ProviderFeature:PracticeLocationId` ← transform `FilteredLocations:FacilityId` (E13) | **only link set** |
| `PRM_Active__c` | `IsActive` | ⚠ REQUIRED, **no default → MUST set** |
| `PRM_EffectiveFrom__c` | `EffectiveDate` | IP `SV_EffectiveDate` |
| `PRM_EffectiveTo__c` | `EffectiveTo` | IP `SV_EffectiveToDate` |
| `PRM_Pending__c` | `ProviderFeature:PRM_Pending__c` | ⚠ REQUIRED (default `false`) |
| `PRM_CaseManager__c` | `IndividualAppId` | IndividualApplication |

> **Not set by the active DR** (⇒ E15 omits or defaults): `PRM_Practitioner__c`, `PRM_HealthcarePractitionerFacility__c` (per‑location grain), `PRM_ExternalId__c` (Id‑based idempotency instead), `PRM_IsDirectoryPrint__c`/`PRM_IsErrorRecord__c` (default `false`).

**Transform `PRMDRTransformPFAA` (✅ org):**
- Gate: `FILTER(LIST(%Locations%), 'CapabilitiesAtLocation != "Does Not Apply"')` → `FilteredLocations`.
- `AssistiveAids ← CapabilitiesAtLocationAPI`, `PracticeLocationId ← FacilityId`, `PRM_Pending__c ← PRM_Pending__c`. No end‑date/OldCapabilities logic — single upsert path (§2, OQ‑E15‑3 resolved).
- ⚠ **`CapabilitiesAtLocationAPI` is a *derived* field** (label→code) produced upstream by the legacy OmniScript; the intake JSON only carries `capabilitiesAtLocation` = **labels**. In the async model the **batch** performs the label→code mapping (OQ‑E15‑4).

### 6.2 AffirmingCareCategory / ACC (✅ grounded — active `PRMDRCreateProviderFeatureACC` Load, `0jIOv0000000R6fMAE`)

Near‑identical to §6.1 — **differences highlighted**:

| `PRM_ProviderFeature__c` field | Source (DR mapping) | Notes |
|---|---|---|
| `RecordTypeId` | formula → **`PRM_AffirmingCareCategory`** | `DeveloperName='PRM_AffirmingCareCategory' AND SobjectType='PRM_ProviderFeature__c'` |
| `Id` | existing feature Id | update‑in‑place / insert (idempotency §2) |
| `Name` | DEFAULT **`'Affirming Care Categories'`** | constant |
| **`PRM_AffirmingCareCategory__c`** | `ProviderFeature:AffirmingCareCategory` ← transform `FacilityData:AffirmingCareCategory` | multipicklist (**label** values) |
| `PRM_HealthcareFacility__c` | `ProviderFeature:PracticeLocationId` ← `FacilityData:PracticeLocationId` (E13) | only link set |
| `PRM_Active__c` | `IsActive` | ⚠ REQUIRED, no default → MUST set |
| **`PRM_IsDirectoryPrint__c`** | `ProviderFeature:ShareInDir` (transform DEFAULT `false`) | ⚠ **ACC sets this** (AsstAid does not) |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | `EffectiveDate` / `EffectiveTo` | IP set‑values |
| `PRM_Pending__c` | `ProviderFeature:PRM_Pending__c` | ⚠ REQUIRED (default `false`) |
| `PRM_CaseManager__c` | `IndividualAppId` | IndividualApplication |

**Transform `PRMDRTransformProviderFeatureACC` (✅ org):** `AffirmingCareCategory ← FacilityData:AffirmingCareCategory`, `PracticeLocationId ← FacilityData:PracticeLocationId`, `ShareInDir ← FacilityData:ShareInDir` (DEFAULT `false`), `PRM_Pending__c ← FacilityData:PRM_Pending__c`. **No `"Does Not Apply"` filter** (OQ‑E15‑11).

---

## 7. DML / order (idempotent)

Gated per type (AsstAid: `!= "Does Not Apply"`; ACC: non‑blank). **One bulk DML** of `PRM_ProviderFeature__c` across **both RTs** (`PRM_AssistiveAid` + `PRM_AffirmingCareCategory`): pre‑check on `(PRM_HealthcareFacility__c + RecordTypeId)` → set `Id` to update the multipicklist in place, else insert (Id‑based, matches legacy — no end‑dating). Returns `providerFeatureId` per (location × type).

> **CMA:** `PRM_ProviderFeature__c` maps to the CMA record type **`Provider_Feature`** (primary `PRM_ProviderFeature__c` + context `PRM_Account__c`, `PRM_HealthcareFacility__c`) — created by **E19** in `PLRelatedBatch`. **[OPEN — OQ‑E15‑5]** confirm both RTs' features are CMA‑tracked here.

---

## 8. Open items / clarifications

- **✅ OQ‑E15‑1 — Grain — RESOLVED (org):** per **location** (DR sets only `PRM_HealthcareFacility__c`); drop `PRM_Practitioner__c`/`PRM_HealthcarePractitionerFacility__c`. **OQ‑E15‑1b** — batch vs service does the pre‑check (rule).
- **✅ OQ‑E15‑2 — Idempotency — RESOLVED (org):** legacy is **Id‑based update** (no extId). Pre‑check `(PRM_HealthcareFacility__c + RT)` → update in place, else insert.
- **✅ OQ‑E15‑3 — create‑vs‑update / end‑dating — RESOLVED (org):** single upsert path, **replace multipicklist in place**, **no** end‑dating / `OldCapabilities`.
- **✅ OQ‑E15‑4 — label → picklist — DECIDED:** intake `capabilitiesAtLocation` holds **display labels**; the **batch maps label → `PRM_AssistiveAids__c` code** (`American Sign Language`→`AS`, `Braille Materials`→`BM`, …) before invoking E15. *(Remaining data item: `Wheelchair Accessible` has no exact picklist label — closest `Handicapped Accessible`=`HA`; finalize this one row in the mapping table.)*
- **OQ‑E15‑5 — CMA (`Provider_Feature`).** Confirm both RTs' features feed E19 CMA (context lookups source).
- **✅ OQ‑E15‑6 — `showInDirectory` — RESOLVED (org):** DR does **not** set `PRM_IsDirectoryPrint__c` → defaults `false`; no intake field needed.
- **OQ‑E15‑7 — Effective dates.** DR maps `EffectiveDate`/`EffectiveTo` from IP set‑values; confirm the batch injects the practitioner `effectiveFromDate` (like E13).
- **OQ‑E15‑8 — CL‑E2‑13.** E15 runs in `PLRelatedBatch` (seq 4), not in‑process in E13 — confirm.
- **OQ‑E15‑9 — Target org / batch / effort (1.0 d).**
- **✅ OQ‑E15‑10 — ACC scope — RESOLVED:** **E15 owns ACC too** (2nd RT `PRM_AffirmingCareCategory`, §6.2), one service / mixed‑RT bulk DML.
- **✅ OQ‑E15‑11 — ACC source node — DECIDED:** `affirmingCareCategory` **added to the location node** in the intake JSON (see `PRM_MultiPractitioner_lowvolume.json`), `;`‑separated. Gate: **non‑blank** (no "Does Not Apply" equivalent). Values arrive as **exact `PRM_AffirmingCareCategory__c` picklist values** (most label==value; a few differ, e.g. `Cultural Competency`→`Cultural Competency Training`, `Home Visit/House Call Only`→`HVHC`).

*(Org‑validated against **active** IP `PRMPractitionerAddressCreation` v5 + DRs `PRMDRCreateProviderFeatureAssitiveAids`/`PRMDRTransformPFAA` and `PRMDRCreateProviderFeatureACC`/`PRMDRTransformProviderFeatureACC`: RTs `PRM_AssistiveAid`+`PRM_AffirmingCareCategory`; multipicklists (codes vs labels); per‑location grain; Id‑based idempotency; required booleans corrected (`PRM_Active__c` must‑set); ACC sets `PRM_IsDirectoryPrint__c`.)*

---

## 9. Definition of Done

- [ ] OQ‑E15‑1…11 answered *(✅ 1 grain=location, 2 Id‑based idempotency, 3 no end‑dating, 4 batch maps AsstAid label→code, 6 no showInDirectory, 10 ACC in scope, 11 `affirmingCareCategory` added to intake; remaining: `Wheelchair Accessible` mapping row)*.
- [ ] `PRM_ProviderFeatureService extends PRM_ServiceBase`; `execute(...)` — **single service, two RTs** (AssistiveAid + ACC), mixed‑RT **one bulk DML**.
- [ ] Gated per type (AsstAid `!= "Does Not Apply"`; ACC non‑blank); batch‑injected context.
- [ ] Per type: RT + `Name` (`'Assistive Aid'`/`'Affirming Care Categories'`) + target multipicklist (`PRM_AssistiveAids__c` codes / `PRM_AffirmingCareCategory__c` labels); `PRM_HealthcareFacility__c` set (no practitioner/HPF); ACC sets `PRM_IsDirectoryPrint__c` ← `shareInDirectory`.
- [ ] REQUIRED booleans: **`PRM_Active__c` (← isActive, no default → set)**, `PRM_Pending__c`; `PRM_IsErrorRecord__c` default false.
- [ ] Idempotent: pre‑check `(PRM_HealthcareFacility__c + RecordTypeId)` → update in place / insert (Id‑based); re‑run creates no duplicate.
- [ ] Returns `providerFeatureId` per (location × type) (feeds E19 `Provider_Feature` CMA).
- [ ] `<Class>Test` ≥ 85% incl. bulk, both RTs, gating, re‑run/idempotency (update‑in‑place).
- [ ] Field API names/types validated against the org.
