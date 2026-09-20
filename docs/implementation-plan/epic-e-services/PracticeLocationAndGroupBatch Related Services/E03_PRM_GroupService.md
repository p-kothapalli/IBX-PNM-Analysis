# E03 · `PRM_GroupService` — *1.5 d* · Branch: BOTH · *(PracticeLocationAndGroupBatch)*

> **Parent:** `Epic_E_Practitioner_Services_Part2.md` (Part 2 — PracticeLocationAndGroupBatch). Shared conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2 / §E0.4** and apply here unchanged.
> **Batch:** runs inside **`PracticeLocationAndGroupBatch`** (seq 2), after `PractitionerBatch` (seq 1). **Writes:** `Account` (Vendor/Group), `Identifier` (Vendor TIN/EIN), `HealthcareProvider` (group). *(Group-grain only — the **group/location `HealthcareProviderNpi` is owned by E13**, and the nested `locations[]` by E13/E14 — **not** E3 — see §1.)*
> **Legacy:** `PRMPostGroupPractitionerCreation` (Load) — invoked by element `DRCreateGroupRecords` in IP `PRM_DelegatedPractitionerCreation` v7.
>
> **⚠ This doc mirrors E02's structure, but E3 has material source-data gaps (the group node in `PRM_MultiPractitioner_lowvolume.json` lacks existing-Ids and credentialing status). The group `HealthcareProviderNpi` is **out of E3 scope** (owned by E13). Nothing is assumed — every gap is raised as an Open Question (§8). Tags: [CONFIRMED] · [OPEN] · [RISK] · [RECOMMENDATION] · Pending Clarification.**

---

## 1. Role & cardinality

- Runs **inside `PracticeLocationAndGroupBatch`** (seq 2). By the time it runs, **E1** has created the Person `Account` / `Case` / `IndividualApplication` (Case Manager) per practitioner, and **`PractitionerBatch`** (seq 1) has created the practitioner core graph.
- E3 builds the **group/vendor graph** per group: `Account` (Vendor) → `Identifier` (Vendor TIN/EIN) → `HealthcareProvider` (group). *(Per the legacy `PRMPostGroupPractitionerCreation` field map — Part 2 §E3.)*
- **The group/location `HealthcareProviderNpi` is NOT E3's** — it is created by **E13 `PRM_HealthcareFacilityCreationService`** (keyed `(Npi + NpiType='Organization')`). E3 does not create or reference it.
- **[CONFIRMED — scope] Group-grain only.** The source nests `groups[].locations[]`, but **location/address/facility/affiliation records are NOT E3's** — they belong to **E13** (`PRM_HealthcareFacilityCreationService`) and **E14** (`PRM_HPFService`). E3 creates only the **group** records.

> **⚠ [OPEN — OQ‑E3‑4] Cardinality / dedup.** In the source, a **practitioner owns `groups[]`** (one practitioner → many groups), and the **same group can be referenced by multiple practitioners** in one submission. E3 must create each **unique group once** (deduped across the chunk by the **`{taxId}-{groupName}`** key — §2; **not** bare `taxId`, which is not unique per the org), with the **practitioner↔group/location affiliations created separately** (E13/E14). Confirm: dedup the group graph by `{taxId}-{groupName}`, and that the practitioner-to-group link is out of E3 scope.

> **✅ [RESOLVED — OQ‑E3‑3] Branch = BOTH.** E3 processes `groups[]` for **both** IBC and Delegated practitioners (source-driven), superseding the legacy Delegated-only IP scope. *(Analogous to E2's CL‑E1 "build for both branches" decision.)*

> **Bulkification.** Like E2, E3 processes the **whole batch chunk** in one pass — input is a **deduped `groups[]`** list (§4); build all records in memory, then **one bulk DML per object type**. No DML/SOQL in loops.

---

## 2. Idempotency (re-run safe) — **required** *(define before the service)*

> **Why:** Epic C manual **retry re-runs the whole batch**, including `execute()` chunks that already committed. So E3 must be safe to re-run without creating duplicate group graphs.

> **⚠ [REVISED — OQ‑E3‑2] Anchor = `{taxId}-{groupName}` (the `HealthCloudGA__SourceSystemId__c` value), NOT bare `taxId`.** Org evidence (§3.1) shows the **same `taxId` on multiple vendor Accounts** (e.g. `142748468-Another Practice` **and** `142748468-Sisham Ingnam`), so **`taxId` is not unique per vendor group**. The durable key that *is* unique (and already populated on existing data + written by the legacy DR) is the composite **`{taxId}-{groupName}`** = `HealthCloudGA__SourceSystemId__c`. **⚠ Trade-off:** this key includes `groupName`, so a group **rename** yields a new key → a possible duplicate (a pre-existing legacy behaviour — see the org sample `166996419-Birth Family Wellness` vs `…-Birth And Family Wellness`). **Confirm the intended grain (taxId+name composite, per org/legacy — recommended for consistency — vs a name-independent key).**

**Approach (org-grounded — keyed on `HealthCloudGA__SourceSystemId__c = {taxId}-{groupName}`):**

| Object | Dedupe key | Mechanism | Notes (org-validated, IBXDEV01) |
|---|---|---|---|
| `Account` (Vendor/Group) | **`HealthCloudGA__SourceSystemId__c` = `{taxId}-{groupName}`** | **`upsert … HealthCloudGA__SourceSystemId__c`** | ⭐ **Account already has this Unique External Id** (no new field). Value matches existing data + the legacy DR. *(OQ‑E3‑8 resolved.)* |
| `Identifier` (Vendor TIN) | **`PRM_RecordKey__c = {taxId}_EIN`** | `upsert … PRM_RecordKey__c` | ⚠ `PRM_RecordKey__c` **repo-only, NOT in IBXDEV01** (§3) → deploy. *(Note: keys one EIN Identifier per `taxId`; if a `taxId` is legitimately shared across vendor accounts, confirm whether each needs its own EIN row — else add `ParentRecordId` to the key.)* |
| `HealthcareProvider` (group) | `PRM_RecordKey__c = {taxId}-{groupName}` **or `SourceSystemIdentifier`** | `upsert … PRM_RecordKey__c` **or pre‑check** | HCP has a **Unique `SourceSystemIdentifier`** (not an External Id → pre‑check only). `PRM_RecordKey__c` **repo-only** — §3. |

> **Group `HealthcareProviderNpi` is out of scope** — created by **E13** (keyed `(Npi + NpiType='Organization')`), not E3.

```apex
// Account key = the composite SourceSystemId (matches existing data + legacy DR)
String groupKey = taxId + '-' + groupName;                 // e.g. '168923170-Sishira Bridges'
// acct.HealthCloudGA__SourceSystemId__c = groupKey;        // existing Unique External Id (no new field)
// idn.PRM_RecordKey__c  = taxId + '_EIN';                  // EIN identifier key (per decision)
// ghcp.PRM_RecordKey__c = groupKey;                        // or pre-check on Unique SourceSystemIdentifier
```

> **⭐ Key improvement (org-driven): anchor the Account on the existing `HealthCloudGA__SourceSystemId__c`** (Unique + External Id, already on `Account`) instead of adding a new field — and use the **org/legacy value `{taxId}-{groupName}`** so the upsert matches the **existing** vendor rows (not a new key format). *(OQ‑E3‑8 resolved; OQ‑E3‑2 corrected from bare taxId to the composite.)*

- **HealthcareProviderNpi (group) — NOT E3.** Moved to **E13 `PRM_HealthcareFacilityCreationService`** (the location/org NPI graph, keyed `(Npi + NpiType='Organization')`). E3 builds only Account + Identifier (EIN) + HealthcareProvider.
- **Key-collision guard:** Account key = `{taxId}-{groupName}` on `HealthCloudGA__SourceSystemId__c` (won't collide with E1's NPI-based person-account key — different format); `_` delimiter on `PRM_RecordKey__c`; confirm a group has at most one EIN `Identifier`.
- **⚠ Dependency / deployment gap (§3):** the `PRM_RecordKey__c` fields E3 wants to reuse on **Identifier** and **HealthcareProvider** exist in the **repo** but are **absent from IBXDEV01** — they must be deployed (they're shared with E2), **or** E3 uses **pre‑checks** instead.

---

## 3. Prerequisite work items — schema + access

> **✅ Org schema validated — IBXDEV01, 2026‑06‑30 (see §3.1).** The improved plan **adds no new field to `Account`** (reuses its existing Unique External Id). The only schema dependency is the **shared `PRM_RecordKey__c`** on `Identifier`/`HealthcareProvider` — which is **in the repo but NOT deployed to IBXDEV01** (or use pre‑checks).

| WI | Task | Object | Status |
|---|---|---|---|
| **WI‑1** | **No new field.** Use existing **`HealthCloudGA__SourceSystemId__c`** (Unique, ExternalId) for the Account upsert (value `{taxId}-{groupName}`) | `Account` | ✅ field exists in IBXDEV01 |
| **WI‑2** | Reuse `PRM_RecordKey__c` for the group `HealthcareProvider` upsert (`{taxId}`) **— OR** pre‑check on Unique `SourceSystemIdentifier` | `HealthcareProvider` | ⚠ `PRM_RecordKey__c` **in repo, NOT in IBXDEV01** → deploy or pre‑check |
| **WI‑3** | Reuse `PRM_RecordKey__c` for the EIN `Identifier` upsert (`{taxId}_EIN`) **— OR** pre‑check on `(ParentRecordId+PRM_Type__c+IdValue)` | `Identifier` | ⚠ `PRM_RecordKey__c` **in repo, NOT in IBXDEV01** → deploy or pre‑check |
| **WI‑4** | Confirm FLS on `PRM_AsyncJob_Access` for the fields E3 writes (incl. `HealthCloudGA__SourceSystemId__c`, and `PRM_RecordKey__c` if used) | `PRM_AsyncJob_Access` | ◻ confirm |
| **WI‑5** | ~~HealthcareProviderNpi (group)~~ — **moved to E13** | `HealthcareProviderNpi` | ➡ out of E3 scope |

> **⚠ [FINDING — deployment gap] `PRM_RecordKey__c` is repo‑only.** The repo has `PRM_RecordKey__c.field-meta.xml` on `HealthcareProvider`, `Identifier`, `HealthcareProviderTaxonomy`, `BusinessLicense`, `BoardCertification`, `ContactProfile`, `PersonEducation`, `PersonLanguage` — but **IBXDEV01's describe shows none of them present**. So **E02's "already deployed ✅" is not true for IBXDEV01** (likely deployed to a different build/test org). Re‑confirm the target org and deploy these fields before any E2/E3 upsert that relies on them — **or** use pre‑checks (E3 can run pre‑check‑only with zero new fields).

### 3.1 🔎 Org validation (IBXDEV01, 2026‑06‑30)

- **Account** — RT **`PRM_Vendor` ("Vendor")** ✓ (also `PRM_SupplementalBenefitVendor`). **`HealthCloudGA__SourceSystemId__c` = Unique + External Id** ✓ (⭐ use for the Account upsert — no new field). **Existing value format (confirmed by sampling Vendor accounts): `{taxId}-{groupName}`** — e.g. `168923170-Sishira Bridges`, `161979194-4145 BRIARGATE PARKWAY OPS, LLC`. **⚠ `taxId` is NOT unique per vendor:** the same EIN appears on multiple accounts (`142748468-Another Practice` **&** `142748468-Sisham Ingnam`; `166996419-Birth Family Wellness` **&** `…-Birth And Family Wellness`) → the unique key is the **composite** `{taxId}-{groupName}` (OQ‑E3‑2 revised). **`Type`** = single picklist (7): `Other, Medical Service Vendor, Supplemental Benefit Vendor, Supplemental Capitated Vendor, Pharma, Medicaid Reclamation, Facility`. **`PRM_VendorType__c`** = **multipicklist** (⚠ different from `Type` — OQ‑E3‑10). **`PRM_ParticipationStatus__c`** picklist: `Participating, Non-Par, Administrative` → `"Participating"` ✓. **`PRM_CredentialingStatus__c`** picklist: `Credentialing In Progress, Credentialed, Denied, Terminated`. **`PRM_Pending__c` and `IsActive` are REQUIRED booleans** (`nillable=false`) — ⚠ cannot be `null` (see §6 correction). `PRM_CaseManager__c` → `IndividualApplication`.
- **Identifier** — RT **`PRM_Vendor` ("Vendor Identifier")** ✓. **`PRM_Type__c` REQUIRED picklist** incl. **`EIN`** → the group TIN uses **`PRM_Type__c='EIN'`** ✓ (OQ‑E3‑10 for Identifier resolved). `ParentRecordId` → polymorphic incl. **Account** ✓, **required**, **insert‑only**. `PRM_Active__c`, `PRM_Pending__c` REQUIRED booleans. **No `PRM_RecordKey__c` in IBXDEV01.**
- **HealthcareProvider** — `Name` **required**; **`SourceSystemIdentifier` = Unique** (string, **not** an External Id → pre‑check only, no upsert). **`Status`** picklist: `Active, Inactive, Pending` → use **`'Inactive'`** (⚠ legacy formula said `"InActive"` — wrong). `AccountId` → Account. **No `PRM_RecordKey__c` in IBXDEV01.**
- **HealthcareProviderNpi** — *(out of E3 scope — owned by E13; see `E13_PRM_HealthcareFacilityCreationService.md`).*

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `Map<String,Object>` in/out. Per the §E0.4 batch contract and the `prm-service-class-boundaries` rule, **context is batch-injected** and the service does **no SOQL/correlation**.

| | |
|---|---|
| **Input `params.flow`** | `String` — process/application name (Part 1 §4.1) |
| **Input `params.groups`** | `List<Object>` — **deduped** group nodes (§4.1), each `{ taxId, groupName, …, caseManagerId, isActive?, effectiveFrom?, effectiveTo? }` (batch-injected context per OQ‑E3‑5/OQ‑E3‑7) |
| **Output `response.groups`** | `List<Map<String,Object>>` (input order): `{ taxId, groupAccountId, groupIdentifierId, groupHealthcareProviderId }` |

> **[OPEN — OQ‑E3‑4b] Input shape.** Proposed `params.groups[]` = the **deduped** set of groups for the chunk (the batch dedupes `practitioner.groups[]` by **`{taxId}-{groupName}`** and injects context). Alternative: pass `params.practitioners[]` with nested `groups[]` and let E3 dedupe. **Recommendation: batch dedupes → `groups[]`** (keeps E3 a thin builder). Confirm.

### 4.1 Correlation & Id resolution (batch-injected)

The **batch** (`PracticeLocationAndGroupBatch`) is responsible (rule):
- **Dedupe** `practitioner.groups[]` across the chunk by the group key **`{taxId}-{groupName}`** (= `HealthCloudGA__SourceSystemId__c`; not bare `taxId` — OQ‑E3‑2).
- **Inject** per group: `caseManagerId` (**[OPEN — OQ‑E3‑5]** which Case Manager stamps a group shared by multiple practitioners?), and the group-level `isActive`/`effectiveFrom`/`effectiveTo` (**[OPEN — OQ‑E3‑7]** the group node has none — source from the practitioner context or a group-level field?).
- **✅ Existing-vs-new (OQ‑E3‑6 — RESOLVED): match by `HealthCloudGA__SourceSystemId__c = {taxId}-{groupName}`.** The source has no `existingGroupId`/`existingGroupNPIId`/`tinId`, so the match is **intrinsic to the External‑Id `upsert`** on `HealthCloudGA__SourceSystemId__c` (existing key → update, new → insert) — no separate pre‑query needed for the Account. The `…Val` new-vs-existing gating keys off **"did the `{taxId}-{groupName}` already exist?"** rather than a payload `existingGroupId`.

### 4.2 Reference implementation (skeleton)

```apex
public with sharing class PRM_GroupService extends PRM_ServiceBase {

    // one per groups[] element (input order) — holds inputs + built records
    @TestVisible
    private class GroupUow {
        Map<String, Object> g;          // group node (taxId, groupName, injected context)
        String taxId;                   // dedupe anchor (proposed — OQ-E3-2)
        Id caseManagerId;               // batch-injected (OQ-E3-5)
        Account vendor;
        Identifier vendorTin;
        HealthcareProvider groupHcp;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        List<Object> groups = (List<Object>) params.get('groups');   // deduped chunk (OQ-E3-4)

        // 1) build UoWs (no DML/SOQL in loop); read batch-injected context
        // 2) cache RTs once (Account 'PRM_Vendor', Identifier 'PRM_Vendor'); compute *Val formulas (§6)
        // 3) build Account(Vendor) -> Identifier(TIN/EIN) -> HealthcareProvider(group)
        //    set keys (§2): Account.HealthCloudGA__SourceSystemId__c={taxId}-{groupName}; Identifier/HCP PRM_RecordKey__c
        // 4) BULK DML per object type (idempotent — §7):
        //    upsert Account by HealthCloudGA__SourceSystemId__c; Identifier/HealthcareProvider by PRM_RecordKey__c (or pre-check)
        //    (group HealthcareProviderNpi is E13's — not built here)

        response = new Map<String, Object>();
        return response;
    }
}
```

> **Governor cost (estimate):** ~1 SOQL (existing-group resolution, **if** OQ‑E3‑6 = match-by-taxId) + up to 4 bulk DML (Account, Identifier, [NPI], HealthcareProvider) — constant regardless of chunk size.

---

## 5. Expected input format

### 5.1 Source group node (from `PRM_MultiPractitioner_lowvolume.json`, `practitioner.groups[]`)

```json
{
  "taxId": "274591038",
  "groupName": "Riverbend Family Health Associates LLC",
  "locations": [ { "locationNpi": "1801234561", "practiceName": "…", "addresses": [ … ], "networkTaxonomyRoles": [ … ] } ]
}
```

> **Source coverage vs legacy E3 inputs:** the **current sample** provides **`taxId`** + **`groupName`** only (+ `locations[]`, owned by E13). Not yet in the sample: `existingGroupId`/`tinId` (handled by SourceSystemId match — OQ‑E3‑6), `credentialingStatus` + group-level `isActive`/`effectiveFrom`/`effectiveTo` (OQ‑E3‑7). *(The legacy `groupNPI` is **not** an E3 input — the group/location NPI is owned by E13.)*

### 5.2 What the batch injects (proposed — pending OQs)

`caseManagerId` (OQ‑E3‑5), `isActive`/`effectiveFrom`/`effectiveTo` (OQ‑E3‑7), and any resolved existing-Ids (OQ‑E3‑6). **Service-computed (do NOT send):** record types (`PRM_Vendor`), `PRM_ParticipationStatus__c="Participating"`, the `…Val` new-vs-existing gating formulas, `HealthCloudGA__SourceSystemId__c`/`SourceSystemIdentifier`, `PRM_RecordKey__c`.

---

## 6. Field maps (grounded — legacy `PRMPostGroupPractitionerCreation`, Part 2 §E3)

> Sources reconciled to the **new source node** where possible; **`[GAP]`** marks fields with no source in `PRM_MultiPractitioner_lowvolume.json` (raised in §8).

**Account (Vendor/Group)** — RT `PRM_Vendor`:

| Field | Source |
|---|---|
| `RecordTypeId` | ⟲ RT `PRM_Vendor` ✓ (org) |
| `Name` | `group.groupName` |
| `Type` (single picklist) and/or `PRM_VendorType__c` (**multipicklist**) | **[OPEN — OQ‑E3‑10]** which field + value (e.g. `Type='Medical Service Vendor'`?); org has distinct `Type` (7 vals) vs multipicklist `PRM_VendorType__c` |
| `HealthCloudGA__SourceSystemId__c` | ⭐ **`taxId + '-' + groupName`** — the **Account upsert key** (Unique External Id; matches existing data + legacy DR; always set) |
| `PRM_ParticipationStatus__c` | `"Participating"` (constant) ✓ valid picklist |
| `PRM_CredentialingStatus__c` | `[GAP]` `credentialingStatus` (OQ‑E3‑7); valid values: `Credentialing In Progress / Credentialed / Denied / Terminated` |
| `IsActive` | ⚠ **REQUIRED boolean** → `isNew ? isActive : <keep>`; **never null** (§6 correction). `isActive` source `[GAP]` (OQ‑E3‑7) |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | injected `[GAP]` (OQ‑E3‑7); dates nullable ✓ |
| `PRM_Pending__c` | ⚠ **REQUIRED boolean** → set `false` (never null) (§6 correction) |
| `PRM_CaseManager__c` | injected `caseManagerId` → `IndividualApplication` (OQ‑E3‑5) |
| `Id` | resolved by existing‑match on `HealthCloudGA__SourceSystemId__c` (OQ‑E3‑6) — not a payload `existingGroupId` |

**Identifier (Vendor TIN)** — RT `PRM_Vendor`:

| Field | Source |
|---|---|
| `RecordTypeId` | ⟲ RT `PRM_Vendor` (Identifier) ✓ (org) |
| `IdValue` | `group.taxId` |
| `PRM_Type__c` | **`'EIN'`** ✓ (org picklist value; **required**) |
| `ParentRecordId` | ← group Account (**required, insert‑only**) |
| `PRM_Active__c` | ⚠ **REQUIRED boolean** → never null |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | injected `[GAP]` (OQ‑E3‑7) |
| `PRM_Pending__c` | ⚠ **REQUIRED boolean** → set `false` (never null) |
| `PRM_CaseManager__c` | injected `caseManagerId` |
| `Id` | resolved by existing‑match (OQ‑E3‑6) |
| `PRM_RecordKey__c` *(if deployed)* | ⟲ `{taxId}_EIN` — **or pre‑check** on `(ParentRecordId+PRM_Type__c+IdValue)` (§2/§3) |

**HealthcareProviderNpi (group)** — *(out of E3 scope — created by **E13**; see `E13_PRM_HealthcareFacilityCreationService.md`.)*

**HealthcareProvider (group)**:

| Field | Source |
|---|---|
| `Name` | `group.groupName` (**required** ✓) |
| `AccountId` | ← group Account (in-service) |
| `Status` | ⟲ `HPStatus = isActive ? 'Active' : 'Inactive'` ✓ (org values — ⚠ **'Inactive'**, not legacy "InActive") |
| `SourceSystemIdentifier` | Unique (not extId) — legacy set `taxId-groupName` on the **existing** path; usable as a **pre‑check** dedupe key |
| `EffectiveFrom` / `EffectiveTo` | injected `[GAP]` (OQ‑E3‑7) |
| `PRM_CaseManager__c` | injected `caseManagerId` |
| `PRM_RecordKey__c` *(if deployed)* | ⟲ `{taxId}` — **or pre‑check** on Unique `SourceSystemIdentifier` (§2/§3) |

**Formulas → Apex** (gate on new-vs-existing — OQ‑E3‑6):

> **⚠ Correction (org-driven): required booleans cannot be `null`.** The legacy `…Val = isNew ? value : null` pattern **breaks** for `Account.IsActive`, `Account.PRM_Pending__c`, `Identifier.PRM_Active__c`/`PRM_Pending__c` — all **`nillable=false`**. On the **existing** path, either **don't touch** those fields (update only the deltas) or set an explicit boolean — **never `null`**.

- Date/lookup `…Val` (`EffectiveFromVal`/`ToVal`/`CaseManagerIdVal`) = `isNew ? <value> : null` (nullable → OK).
- **Required booleans:** `IsActive`/`PRM_Active__c` = the injected `isActive` (default `false` if absent — OQ‑E3‑7); `PRM_Pending__c` = `false` (constant). **Never null.**
- `CredentialingStatusVal` = `credentialingStatus` `[GAP]` (OQ‑E3‑7); valid org values only.
- `HPStatus` = `isActive ? 'Active' : 'Inactive'` ✓ (org picklist; not "InActive").
- **Account key** = `HealthCloudGA__SourceSystemId__c = taxId + '-' + groupName` (always; the upsert key — matches existing data + legacy DR). HCP `SourceSystemIdentifier` (same `taxId-groupName`) optional as a pre‑check key.
- Vendor RTs via cached describe (`PRM_Vendor`) ✓.

### 6.1 IP grounding (`PRM_DelegatedPractitionerCreation` v7 → `DRCreateGroupRecords` → `PRMPostGroupPractitionerCreation`)

| DR input | IP source | E3 mapping |
|---|---|---|
| `GroupInformation` | `PractionerGroup:GroupInformation` | `group` node (`taxId`, `groupName`) |
| `CaseManagerId` | `DRPAccountCaseCaseManagerCreation:CaseManagerId` | injected `caseManagerId` (OQ‑E3‑5) |
| `IsActive` | `RecordsToUpdate:IsRecordActive` | injected `isActive` `[GAP]` |
| `EffectiveDate` / `EffectiveTo` | `RecordsToUpdate:EffectiveFrom`/`EffectiveTo` | injected `[GAP]` |
| `GroupInformation:ParticipationStatus` | `"Participating"` (constant) | service constant |
| `PRM_Pending__c` | `False` (constant) | service constant |

> **Legacy vs source mismatch:** the legacy `groupInfo` carried `existingGroupId` / `tinId` / `credentialingStatus` (+ `groupNPI`, now **E13's**); the **source group node does not** — so the legacy new-vs-existing gating is driven by the SourceSystemId match instead (OQ‑E3‑6/7).

---

## 7. DML / order (idempotent)

Process in dependency order, **one bulk DML per object type** across the deduped chunk; idempotency per §2:

1. **Upsert `Account` (Vendor)** by **`HealthCloudGA__SourceSystemId__c`** (`{taxId}-{groupName}`) — existing Unique External Id (no new field; matches existing rows).
2. **`Identifier` (Vendor TIN, `PRM_Type__c='EIN'`)** (FK `ParentRecordId` = Account): **`upsert … PRM_RecordKey__c`** *(if deployed)* **or pre‑check** on `(ParentRecordId+PRM_Type__c+IdValue)` then insert misses.
3. **`HealthcareProvider` (group)** (FK `AccountId` = Account): **`upsert … PRM_RecordKey__c`** *(if deployed)* **or pre‑check** on Unique `SourceSystemIdentifier`.

> **Group `HealthcareProviderNpi` is NOT created here** — it belongs to **E13** (location/org NPI graph).

> **DML alternative (zero new schema):** E3 can run **today on IBXDEV01** with **no field deployment** — Account upsert by `HealthCloudGA__SourceSystemId__c` (exists) + Identifier/HCP via **pre‑checks**. Reuse `PRM_RecordKey__c` only once it's deployed to the target org (shared with E2).

`upsert` populates `Id` on the passed instances, so `GroupUow` correlation holds. Returns `groupAccountId`, `groupIdentifierId`, `groupHealthcareProviderId` per group.

> **[OPEN — OQ‑E3‑11] CMA (E19).** Does the group graph need Case Manager Association rows (like Identifier/Taxonomy in E2)? If a Vendor/Group record type exists for CMA, E3's created Ids would feed E19 (per §E0.4). Confirm whether group records are CMA-tracked.

---

## 8. Open items / clarifications (must be answered before build)

- **✅ OQ‑E3‑1 — Group NPI — MOVED OUT OF E3.** The group/location `HealthcareProviderNpi` is owned by **E13 `PRM_HealthcareFacilityCreationService`** (not E3). E3 builds only Account + Identifier (EIN) + HealthcareProvider.
- **⚠ OQ‑E3‑2 — Idempotency anchor — REVISED: `{taxId}-{groupName}` (the `HealthCloudGA__SourceSystemId__c` composite), not bare `taxId`.** Org evidence shows **`taxId` is not unique per vendor** (same EIN on multiple accounts), so the unique key is the composite (matches existing data + legacy DR). **Confirm the grain** (taxId+name composite — recommended for org consistency — vs a name-independent key, which would re-key on rename). *(You selected "taxId"; flagging this correction since the org data contradicts bare-taxId uniqueness.)*
- **✅ OQ‑E3‑3 — Branch — RESOLVED: BOTH.** E3 processes groups for IBC **and** Delegated practitioners (source-driven).
- **OQ‑E3‑4 — Cardinality / dedup.** Confirm E3 creates each **unique group once** (dedup by **`{taxId}-{groupName}`**), with practitioner↔group/location links owned by E13/E14; and **OQ‑E3‑4b** the input shape (`params.groups[]` deduped by the batch — recommended — vs `practitioners[]`).
- **OQ‑E3‑5 — `caseManagerId` for a shared group.** When one group (same `{taxId}-{groupName}`) is referenced by multiple practitioners (different Case Managers), which `caseManagerId` stamps the group's `PRM_CaseManager__c`? *(Now more pressing given dedup + both branches.)*
- **✅ OQ‑E3‑6 — Existing-vs-new — RESOLVED: match by `HealthCloudGA__SourceSystemId__c = {taxId}-{groupName}`** (intrinsic to the External‑Id `upsert`). `…Val` gating keys off whether the key already existed.
- **OQ‑E3‑7 — Group active/effective/credentialing source.** The group node lacks `isActive`/`effectiveFrom`/`effectiveTo`/`credentialingStatus`. Source these from the **practitioner context**, a **group-level field** (to be added), or constants? (Legacy `groupInfo` shape vs the new source — reconcile.)
- **✅ OQ‑E3‑8 — Account schema — RESOLVED: no new field.** Use the existing **`HealthCloudGA__SourceSystemId__c`** (Unique + External Id, on `Account` in IBXDEV01) for the upsert, value **`{taxId}-{groupName}`** (matches existing rows + legacy DR). No `PRM_RecordKey__c` added to `Account`.
- **🟡 OQ‑E3‑9 — Org validation — DONE (IBXDEV01, §3.1).** Remaining: confirm the **target org** for deploy (and that `PRM_RecordKey__c` is deployed there if used — see the §3 deployment finding).
- **🟡 OQ‑E3‑10 — Vendor type picklists.** **Identifier `PRM_Type__c='EIN'` — RESOLVED** ✓ (org). **Still open:** the group **Account** vendor type — `Type` (single picklist, 7 values) vs `PRM_VendorType__c` (multipicklist): which field and which value(s)?
- **OQ‑E3‑11 — Group CMA (E19).** Are group records Case-Manager-Association-tracked (feed E19), or not?
- **OQ‑E3‑12 — Batch/effort.** Confirm `PracticeLocationAndGroupBatch` ownership, batch size, and that E3 runs before E13 (locations) in seq 2.
- **⚠ OQ‑E3‑13 (FINDING) — `PRM_RecordKey__c` deployment gap.** Repo has the field (Identifier/HealthcareProvider/…); **IBXDEV01 does not**. Confirm the target org + deploy (shared with E2) **or** build E3 pre‑check‑only (zero new schema). Re‑verify E2's idempotency actually works on the target org.
- **⚠ OQ‑E3‑14 (FINDING) — required-boolean correction.** `Account.IsActive`/`PRM_Pending__c`, `Identifier.PRM_Active__c`/`PRM_Pending__c` are **`nillable=false`** — the legacy `…Val = isNew ? x : null` must not write `null` (§6). Confirm the existing-path behaviour (skip vs explicit boolean).

*(Assumptions explicitly NOT made: the group active/effective/credentialing source (OQ‑E3‑7), the Account vendor-type field/value (OQ‑E3‑10), shared-group case manager (OQ‑E3‑5), and group CMA (OQ‑E3‑11) are left OPEN rather than guessed. **Scope:** the group/location `HealthcareProviderNpi` is **E13's**, not E3's. **Org-validated & improved:** anchor=`{taxId}-{groupName}`, Account upsert via existing `HealthCloudGA__SourceSystemId__c` (no new field), Identifier `PRM_Type__c='EIN'`, HCP `Status='Inactive'`, required-boolean handling, and the `PRM_RecordKey__c` deployment gap.)*

---

## 9. Definition of Done

- [ ] Remaining OQs answered — OQ‑E3‑4/4b, OQ‑E3‑5, OQ‑E3‑7, OQ‑E3‑10 (Account vendor type), OQ‑E3‑11, OQ‑E3‑12, OQ‑E3‑13/14 (findings). *(✅ resolved: OQ‑E3‑1 group NPI **moved to E13** · OQ‑E3‑2 anchor=`{taxId}-{groupName}` · OQ‑E3‑3 branch=BOTH · OQ‑E3‑6 match by SourceSystemId · OQ‑E3‑8 no new Account field · OQ‑E3‑9 org-validated · OQ‑E3‑10 Identifier='EIN'.)*
- [ ] Prerequisite schema (§3): **Account uses existing `HealthCloudGA__SourceSystemId__c`** (no new field); **Identifier/HealthcareProvider** use `PRM_RecordKey__c` (**deploy to target org** — repo-only today) **or pre‑checks**; FLS confirmed on `PRM_AsyncJob_Access`.
- [ ] Required booleans never written `null` (OQ‑E3‑14): `Account.IsActive`/`PRM_Pending__c`, `Identifier.PRM_Active__c`/`PRM_Pending__c`.
- [ ] `PRM_GroupService extends PRM_ServiceBase`; `execute(...)`.
- [ ] Bulk over the deduped group chunk; **one bulk DML per object type** (no DML/SOQL in loops); batch-injected context (no service SOQL).
- [ ] Group dedup by the confirmed anchor; each unique group created once.
- [ ] Formulas computed in-service (`…Val` gating, `SourceSystemId`/`Identifier`, `HPStatus`, RTs, `PRM_RecordKey__c`).
- [ ] **Idempotent:** `upsert` by `PRM_RecordKey__c`; re-run produces **no duplicate** group graph.
- [ ] Returns per-group Ids for downstream services (E13/E14 location/affiliation).
- [ ] `<Class>Test` ≥ 85% incl. a bulk test (multiple practitioners sharing a group) + a re-run/idempotency test.
- [ ] Field API names/types validated against the org (OQ‑E3‑9).
