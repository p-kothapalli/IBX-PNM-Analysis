# E03 · `PRM_GroupService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** Self‑contained for component generation (see **§0 Component inventory**): Apex class + `.cls-meta.xml` (**Appendix A**), `PRM_RecordKey__c` field metadata for `Identifier` + `HealthcareProvider` (**Appendix B** — repo‑only today, must deploy to the target org), `PRM_AsyncJob_Access` FLS (**Appendix C**), test class + meta (**Appendix D**), deploy/validation commands (**Appendix E**).
>
> **Source of truth:** `E03_PRM_GroupService.md` (design §1–§9, incl. the IBXDEV01 org‑validation) + the `prm-service-class-boundaries` rule + Part 1 §E0.4. Anything not stated there is **UNKNOWN** and raised as an Open Question (§7) — **not assumed**.
>
> **Scope reminder:** E3 writes **`Account` (Vendor) + `Identifier` (EIN) + `HealthcareProvider` (group)** only. The **group/location `HealthcareProviderNpi` is E13's**, and `locations[]` are E13/E14 — **not** E3.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]** · **Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PRM_GroupService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_GroupService.cls` (+ meta) | **NEW** | Appendix A |
| 2 | `Identifier.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `objects/Identifier/fields/PRM_RecordKey__c.field-meta.xml` | **EXISTS in repo → DEPLOY** (shared w/ E2) | Appendix B |
| 3 | `HealthcareProvider.PRM_RecordKey__c` | Custom Field — same spec | `objects/HealthcareProvider/fields/PRM_RecordKey__c.field-meta.xml` | **EXISTS in repo → DEPLOY** (shared w/ E2) | Appendix B |
| 4 | `PRM_AsyncJob_Access` FLS | Permission Set — `fieldPermissions` (Read+Edit) for the two `PRM_RecordKey__c` + `HealthCloudGA__SourceSystemId__c` (confirm) | `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** | Appendix C |
| 5 | `PRM_GroupServiceTest` | Apex test class | `classes/PRM_GroupServiceTest.cls` (+ meta) | **NEW** | Appendix D |
| 6 | `PRM_TestDataFactory` builders | Apex test factory (reuse / extend) | `classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note (OQ‑E3‑15) |

> **Account needs NO new field** — it reuses the existing Unique External Id **`HealthCloudGA__SourceSystemId__c`** (§1).
> **Conventions:** `PRM_` prefix; `with sharing`; **service does NO SOQL** (batch injects context; upsert‑by‑external‑id handles new‑vs‑existing); one bulk DML per object type; **API 66.0**; test reuses `PRM_TestDataFactory` + the modern `Assert`. Error handling at the batch level (the service throws; Epic C logs + halts).

---

## 1. Confirmed requirements (from `E03…md` + org validation)

- **[CONFIRMED]** `PRM_GroupService extends PRM_ServiceBase`; `execute(Map):Map`. **Runs inside `PracticeLocationAndGroupBatch` (seq 2)**, after E1 + `PractitionerBatch` + E3‑group context. **Writes:** `Account` (Vendor), `Identifier` (EIN), `HealthcareProvider` (group). (Design §1.)
- **[CONFIRMED]** **Branch = BOTH** (IBC + Delegated). (Design §1, OQ‑E3‑3.)
- **[CONFIRMED]** **Bulk:** input `params.groups[]` = the deduped group chunk; build all in memory; **one bulk DML per object type**. (Design §4.)
- **[CONFIRMED — rule]** **Service is SOQL‑free.** Context (`caseManagerId`, `isActive`/effective dates, vendor type, credentialing) is **batch‑injected**; new‑vs‑existing is handled by **external‑id upsert** (no pre‑query). (Design §4.1 + `prm-service-class-boundaries`.)
- **[CONFIRMED]** **Idempotency anchor = `{taxId}-{groupName}`** (the composite), because **`taxId` alone is NOT unique** per vendor in the org. (Design §2, OQ‑E3‑2.)
  - **`Account`** → `upsert … HealthCloudGA__SourceSystemId__c` (value `{taxId}-{groupName}`) — existing Unique External Id, **no new field**.
  - **`Identifier` (EIN)** → `upsert … PRM_RecordKey__c` (`{taxId}_EIN`).
  - **`HealthcareProvider`** → `upsert … PRM_RecordKey__c` (`{taxId}-{groupName}`).
- **[CONFIRMED]** **Existing‑vs‑new = match by `HealthCloudGA__SourceSystemId__c`** (intrinsic to the upsert). (Design §4.1, OQ‑E3‑6.)
- **[CONFIRMED — org]** RT **`PRM_Vendor`** on Account + Identifier; **`Identifier.PRM_Type__c = 'EIN'`**; **`HealthcareProvider.Status` ∈ {Active, Inactive, Pending}** → `'Inactive'` (not "InActive"); **`Account.PRM_ParticipationStatus__c = 'Participating'`** valid; `PRM_CredentialingStatus__c` ∈ {Credentialing In Progress, Credentialed, Denied, Terminated}. (Design §3.1.)
- **[CONFIRMED — org]** **Required booleans never `null`:** `Account.IsActive`/`PRM_Pending__c`, `Identifier.PRM_Active__c`/`PRM_Pending__c` (`nillable=false`). (Design §6, OQ‑E3‑14.)
- **[CONFIRMED]** **Output:** `response.groups[]` (input order): `{ taxId, groupAccountId, groupIdentifierId, groupHealthcareProviderId }`. (Design §4.)
- **[CONFIRMED]** **Effort:** ~1.5 d. (Design header / Part 2.)
- **[CONFIRMED]** **Depends on:** Epic A (base permset), Epic B (`PRM_ServiceBase`, `PRM_FormSubUtility.recordTypeId`), **E3 group context** + the `PracticeLocationAndGroupBatch` wiring, and the `PRM_RecordKey__c` deploy (Identifier + HealthcareProvider).

> **🔎 Org validation (IBXDEV01, 2026‑06‑30):** Account `HealthCloudGA__SourceSystemId__c` Unique+extId, existing values `{taxId}-{groupName}` (taxId not unique per vendor); Identifier `PRM_Type__c='EIN'`, RT `PRM_Vendor`; HealthcareProvider `Status='Inactive'`, Unique `SourceSystemIdentifier` (not extId); **`PRM_RecordKey__c` repo‑only, NOT in IBXDEV01** (deploy gap).

---

## 2. Constraints

- **[CONFIRMED — rule]** **No SOQL / correlation / source‑format branching in the service.** The batch resolves & injects context and dedupes by `{taxId}-{groupName}`; the service reads `params`, builds, upserts.
- **[CONFIRMED]** Runs inside a batch `execute()` chunk; idempotency exists because **retry re‑runs the whole batch**.
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch user via `PRM_AsyncJob_Access`) — `PRM_RecordKey__c` FLS must be present on Identifier + HealthcareProvider.
- **[CONFIRMED]** **Two required fields gate the build:** `taxId` + `groupName` (the composite key). Blank either → fail the group.
- **[CONFIRMED]** Required booleans set explicitly (never null) — §1.
- **[OPEN]** Account vendor type (`Type` vs multipicklist `PRM_VendorType__c`) value (OQ‑E3‑10), group active/effective/credentialing source (OQ‑E3‑7), shared‑group `caseManagerId` (OQ‑E3‑5) — all **batch‑injected**, values **pending clarification**.

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `params.groups[]`; builds `Account` + `Identifier` (EIN) + `HealthcareProvider` per group; **one bulk DML per object type**; **zero SOQL** in the service.
- **[CONFIRMED]** **Idempotent:** Account upsert by `HealthCloudGA__SourceSystemId__c`; Identifier/HealthcareProvider upsert by `PRM_RecordKey__c`; re‑running the same chunk produces **no duplicates**.
- **[CONFIRMED]** Account key = `{taxId}-{groupName}`; Identifier `PRM_Type__c='EIN'`, `PRM_RecordKey__c={taxId}_EIN`; HCP `Status` org‑valid; required booleans never null.
- **[CONFIRMED]** FK order: Account → Identifier (`ParentRecordId`) → HealthcareProvider (`AccountId`).
- **[CONFIRMED]** Returns per‑group `{ taxId, groupAccountId, groupIdentifierId, groupHealthcareProviderId }`.
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (multiple groups, incl. two practitioners sharing a group), (b) a **re‑run/idempotency** test, (c) a **missing‑taxId/groupName negative**.
- **[CONFIRMED]** Field API names/types validated against the org (done; re‑confirm on the target org).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted · Validation · Testing · Risks · Completion. Full class in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E3‑4b/5/7/10/11/12)
- **T0.1 — Confirm target org** (OQ‑E3‑12). Completion: org confirmed.
- **T0.2 — Confirm the batch‑injection contract** (rule): `PracticeLocationAndGroupBatch` dedupes `groups[]` by `{taxId}-{groupName}` and injects `caseManagerId` + group context; service does no SOQL. Completion: contract confirmed (OQ‑E3‑4b).
- **T0.3 — Resolve injected values:** vendor type field+value (OQ‑E3‑10), `isActive`/effective dates/credentialing source (OQ‑E3‑7), shared‑group `caseManagerId` policy (OQ‑E3‑5). Completion: each decided or deferred.
- **T0.4 — Verify dependencies on `main`:** `PRM_ServiceBase`, `PRM_FormSubUtility.recordTypeId`, `PRM_AsyncJob_Access`, `PRM_TestDataFactory`. Completion: present.
- **T0.5 — Confirm group CMA (E19)** (OQ‑E3‑11): are group records CMA‑tracked? Completion: decided.

### Phase 1 — Schema deploy (declarative — **repo‑only field → target org**) *(M1)*
- **T1.1 — Deploy `PRM_RecordKey__c` to `Identifier` + `HealthcareProvider`** (Appendix B) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (Appendix C). **⚠ Field exists in the repo but NOT in IBXDEV01** (design §3 finding).
  - Purpose: enable External‑Id `upsert` (keeps the service SOQL‑free). Outcome: fields + FLS deployed. Dependencies: T0.1. Validation: describe resolves; `upsert … PRM_RecordKey__c` compiles. Testing: trial upsert. Risks: **[RISK]** unique‑constraint vs existing rows (field new/empty → low). Completion: deployed.
- **T1.2 — Confirm `Account.HealthCloudGA__SourceSystemId__c` FLS** on `PRM_AsyncJob_Access` (existing field). Completion: editable by the batch user.

### Phase 2 — `PRM_GroupService` core *(M2)*
- **T2.1 — Class + `execute`; parse + gate (no SOQL).** Purpose: parse `groups[]`; require `taxId`+`groupName`; read injected context. Outcome: Appendix A step 1. Impacted: `classes/PRM_GroupService.cls`. Validation: compiles; **no SOQL**. Testing: parse + negative. Risks: **[RISK]** missing taxId/groupName. Completion: green.
- **T2.2 — Builders (`buildVendorAccount`, `buildEinIdentifier`, `buildGroupHealthcareProvider`).** Purpose: in‑memory records per §6; composite keys; required booleans; org‑valid picklists. Dependencies: T2.1, T0.3. Validation: field‑by‑field assertions. Testing: builder units. Risks: **[RISK]** vendor type value (OQ‑E3‑10), credentialing/effective source (OQ‑E3‑7). Completion: builders unit‑tested.
- **T2.3 — Bulk upserts + FK threading + response.** Purpose: upsert Account by `HealthCloudGA__SourceSystemId__c`; thread `Account.Id` → Identifier `ParentRecordId` + HCP `AccountId`; upsert by `PRM_RecordKey__c`; build response. Dependencies: T2.2, T1.1. Validation: DML counts (3 upserts); SOQL=0; FKs set. Completion: green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** builders (keys, picklists, required booleans), parse/gate; assert **0 SOQL**.
- **T3.2 Bulk/governor:** many groups (incl. shared group across practitioners) → 0 SOQL + 3 DML.
- **T3.3 Idempotency:** execute twice → no duplicates (Account/Identifier/HCP counts stable).
- **T3.4 Negative:** missing `taxId`/`groupName` → exception.
  - Dependencies: Phases 1–2, test data (OQ‑E3‑15). Completion: ≥ 85%.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check incl. a re‑run case) + human sign‑off. Completion: signed off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/group-service`; PR into `main` (green CI + 1 review); squash‑merge; tag. Commit prefix `[E3]`. Schema (T1.1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Reuse `HealthCloudGA__SourceSystemId__c` for the Account upsert.** It's an existing Unique External Id holding `{taxId}-{groupName}` on existing rows — matching it dedupes against real data with **no new Account field**. *(Trade‑off: a group **rename** → new key → possible duplicate, a pre‑existing legacy behaviour. Accept for org consistency unless a rename‑stable key is required — OQ‑E3‑2.)*
- **[RECOMMENDATION] External‑id upsert replaces the legacy new‑vs‑existing gating.** The legacy `…Val = isNew ? x : null` + the `SourceSystemId`(new)/`SourceSystemIdentifier`(existing) inverse can be dropped — upsert handles both paths, and required booleans must be set anyway (§1). *(Confirm we don't need the HCP `SourceSystemIdentifier` legacy value — OQ‑E3‑7.)*
- **[RECOMMENDATION] Deploy `PRM_RecordKey__c` (Identifier + HealthcareProvider) so the service stays SOQL‑free.** The alternative (pre‑checks) adds SOQL and violates the boundary rule. The field is already in the repo — just deploy it (shared with E2). **Re‑verify E2's idempotency works on the target org** (same gap).
- **[RISK] Vendor type (OQ‑E3‑10).** Org has a single `Type` picklist **and** a multipicklist `PRM_VendorType__c`. The value/field is **undocumented** → left as an injected TODO; **do not hardcode**.
- **[RISK] Group active/effective/credentialing source (OQ‑E3‑7).** Not in the group node → batch‑injected; values pending.
- **[RISK] `IndividualApplication` test data (OQ‑E3‑15).** `caseManagerId` → IndividualApplication; required fields undocumented → confirm a `PRM_TestDataFactory` builder.

---

## 6. Gaps & hidden dependencies

- **`PRM_RecordKey__c` deploy gap (OQ‑E3‑13)** — repo‑only; deploy to target org (Phase 1) or the upsert fails to compile/run.
- **Vendor type value (OQ‑E3‑10)**, **active/effective/credentialing source (OQ‑E3‑7)**, **shared‑group `caseManagerId` (OQ‑E3‑5)** — batch‑injected; values pending.
- **Input shape (OQ‑E3‑4b)** — batch dedupes → `params.groups[]` (assumed Option A).
- **Group CMA (OQ‑E3‑11)** — if group records are CMA‑tracked, feed E19 (per §E0.4) — confirm.
- **Batch ownership/order (OQ‑E3‑12)** — E3 before E13 in seq 2.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E3‑4b — Input shape.** Confirm batch dedupes `practitioner.groups[]` by `{taxId}-{groupName}` → `params.groups[]` with injected context (recommended) vs nested nodes.
- **OQ‑E3‑5 — Shared‑group `caseManagerId`.** When one group is referenced by multiple practitioners, which Case Manager stamps `PRM_CaseManager__c`?
- **OQ‑E3‑7 — Group `isActive` / effective dates / `credentialingStatus` source.** Not in the group node — practitioner context, group‑level fields (to be added), or constants?
- **OQ‑E3‑10 — Vendor type.** `Account.Type` (single) vs `PRM_VendorType__c` (multipicklist): which field + which value(s)?
- **OQ‑E3‑11 — Group CMA (E19).** Are group records Case‑Manager‑Association‑tracked?
- **OQ‑E3‑12 — Target org / batch ownership / order** (E3 before E13 in seq 2).
- **OQ‑E3‑13 — `PRM_RecordKey__c` deploy** (repo‑only → target org) — confirm + deploy (shared w/ E2).
- **OQ‑E3‑14 — Required‑boolean existing‑path behaviour** — skip vs explicit boolean on update.
- **OQ‑E3‑15 — `IndividualApplication` test‑data builder** for `caseManagerId`.

*(Resolved: OQ‑E3‑1 group NPI → **moved to E13**; OQ‑E3‑2 anchor=`{taxId}-{groupName}`; OQ‑E3‑3 branch=BOTH; OQ‑E3‑6 match by SourceSystemId; OQ‑E3‑8 no new Account field; OQ‑E3‑9 org‑validated.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | `PRM_RecordKey__c` not deployed to target org → won't compile/upsert | **Medium** | High | Phase 1 (T1.1) deploys it; or pre‑check fallback (adds SOQL) |
| R‑2 | Vendor type value wrong/blank (OQ‑E3‑10) | Medium | Medium | injected TODO; don't hardcode; T0.3 |
| R‑3 | `{taxId}-{groupName}` rename → duplicate | Low–Med | Medium | accepted legacy behaviour; OQ‑E3‑2 |
| R‑4 | Active/effective/credentialing source missing (OQ‑E3‑7) | Medium | Medium | batch‑injected; T0.3 |
| R‑5 | Service does its own SOQL (violates rule) | Low | Medium | external‑id upsert (no pre‑query); assert 0 SOQL in T3.1 |
| R‑6 | `IndividualApplication` test data fails | Medium | Medium | OQ‑E3‑15; factory builder |
| R‑7 | Required boolean written null → DML error | Low | Medium | explicit booleans (§1); T3.1 |
| R‑8 | No target org → can't deploy/test | Medium | High | OQ‑E3‑12 |

---

## 9. Sequencing & effort

- **Order:** Phase 0 → 1 (**deploy `PRM_RecordKey__c` + FLS**) → 2 (service) → 3 → 4 → 5. Runs **in `PracticeLocationAndGroupBatch` (seq 2)**, before E13.
- **Effort:** within the ~1.5 d catalog estimate — class + builders + keys ~0.7 · tests ~0.5 · evidence/VCS folded in.
- **Depends on:** Epic A + Epic B on `main`, the batch wiring, and the field deploy. **Feeds:** E13 (locations reference the group), and E19 if group CMA is in scope (OQ‑E3‑11).

---

## 10. What happens after sign‑off

Resolve OQ‑E3‑4b/5/7/10/11/12/13/15. Then: **deploy `PRM_RecordKey__c` + FLS (Phase 1)** → build the service per **Appendix A** (parse + build → 3 bulk upserts → response) → tests (**Appendix D**) → Test Evidence Report → human sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E3‑12) and the field deploy (OQ‑E3‑13) are confirmed.**

---

## Appendix A — Apex class `PRM_GroupService` (+ meta)

> Full `PRM_GroupService` (expands `E03…md` §4.2). **SOQL‑free** (batch‑injected context; external‑id upsert handles new‑vs‑existing). **Group `HealthcareProviderNpi` is NOT built here (E13).** Org‑valid literals (`'PRM_Vendor'`, `'EIN'`, `'Participating'`, `'Active'/'Inactive'`) — promote to `PRM_Constants` if preferred. **TODO/Pending‑Clarification** comments mark undocumented values (do not hardcode).

```apex
public with sharing class PRM_GroupService extends PRM_ServiceBase {

    public class PRM_GroupServiceException extends Exception {}

    private static final String KEY_DELIMITER = '_';
    private static final String GROUP_KEY_DELIMITER = '-';   // matches existing HealthCloudGA__SourceSystemId__c format

    @TestVisible
    private class GroupUnitOfWork {
        Map<String, Object> node;        // group node + batch-injected context
        String taxId;
        String groupName;
        String groupKey;                 // {taxId}-{groupName} (= Account External Id + HCP key)
        Id caseManagerId;                // batch-injected (OQ-E3-5)
        Account vendor;
        Identifier ein;
        HealthcareProvider hcp;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'groups' => new List<Object>() };
        List<Object> groups = (params == null) ? null : (List<Object>) params.get('groups');
        if (groups == null || groups.isEmpty()) {
            return response;
        }

        Id vendorAccountRecordTypeId = PRM_FormSubUtility.recordTypeId(Account.SObjectType, 'PRM_Vendor');
        Id vendorIdentifierRecordTypeId = PRM_FormSubUtility.recordTypeId(Identifier.SObjectType, 'PRM_Vendor');

        // 1) parse + build (no SOQL/DML in loop)
        List<GroupUnitOfWork> unitsOfWork = new List<GroupUnitOfWork>();
        for (Object groupObject : groups) {
            Map<String, Object> node = (Map<String, Object>) groupObject;
            GroupUnitOfWork uow = new GroupUnitOfWork();
            uow.node = node;
            uow.taxId = (String) node.get('taxId');
            uow.groupName = (String) node.get('groupName');
            if (String.isBlank(uow.taxId) || String.isBlank(uow.groupName)) {
                throw new PRM_GroupServiceException(
                    'Group requires both taxId and groupName (the composite external key)');
            }
            uow.groupKey = uow.taxId + GROUP_KEY_DELIMITER + uow.groupName;
            uow.caseManagerId = (Id) node.get('caseManagerId');
            buildVendorAccount(uow, vendorAccountRecordTypeId);
            buildEinIdentifier(uow, vendorIdentifierRecordTypeId);
            buildGroupHealthcareProvider(uow);
            unitsOfWork.add(uow);
        }

        // 2) bulk DML, FK order, idempotent (§7)
        upsertVendorAccounts(unitsOfWork);          // upsert Account by HealthCloudGA__SourceSystemId__c
        upsertEinIdentifiers(unitsOfWork);          // FK ParentRecordId -> Account; upsert by PRM_RecordKey__c
        upsertGroupHealthcareProviders(unitsOfWork);// FK AccountId -> Account; upsert by PRM_RecordKey__c

        // 3) response (input order)
        return buildResponse(unitsOfWork);
    }

    // ── builders (pure in-memory; required booleans NEVER null) ──

    private void buildVendorAccount(GroupUnitOfWork uow, Id recordTypeId) {
        Account vendor = new Account();
        vendor.RecordTypeId = recordTypeId;
        vendor.Name = uow.groupName;
        vendor.HealthCloudGA__SourceSystemId__c = uow.groupKey;            // upsert KEY (§2)
        vendor.PRM_ParticipationStatus__c = 'Participating';               // org-valid constant
        vendor.PRM_CaseManager__c = uow.caseManagerId;
        vendor.IsActive = asBool(uow.node.get('isActive'));                // REQUIRED (source OQ-E3-7)
        vendor.PRM_Pending__c = false;                                     // REQUIRED
        putDate(vendor, 'PRM_EffectiveFrom__c', uow.node.get('effectiveFrom')); // OQ-E3-7
        putDate(vendor, 'PRM_EffectiveTo__c', uow.node.get('effectiveTo'));
        // TODO Pending Clarification (OQ-E3-10): vendor Type — single picklist Type vs multipicklist PRM_VendorType__c
        //   vendor.Type = (String) uow.node.get('vendorType');
        //   vendor.PRM_VendorType__c = (String) uow.node.get('vendorType');
        // TODO Pending Clarification (OQ-E3-7): credentialing status source
        //   vendor.PRM_CredentialingStatus__c = (String) uow.node.get('credentialingStatus');
        uow.vendor = vendor;
    }

    private void buildEinIdentifier(GroupUnitOfWork uow, Id recordTypeId) {
        Identifier ein = new Identifier();
        ein.RecordTypeId = recordTypeId;
        ein.PRM_Type__c = 'EIN';                                           // org-valid picklist value
        ein.IdValue = uow.taxId;
        ein.Name = uow.taxId;                                              // Name is required
        ein.PRM_Active__c = asBool(uow.node.get('isActive'));             // REQUIRED
        ein.PRM_Pending__c = false;                                        // REQUIRED
        ein.PRM_CaseManager__c = uow.caseManagerId;
        ein.PRM_RecordKey__c = key(new List<String>{ uow.taxId, 'EIN' }); // {taxId}_EIN
        // ParentRecordId set after the Account upsert (FK)
        uow.ein = ein;
    }

    private void buildGroupHealthcareProvider(GroupUnitOfWork uow) {
        HealthcareProvider hcp = new HealthcareProvider();
        hcp.Name = uow.groupName;                                          // required
        hcp.Status = asBool(uow.node.get('isActive')) ? 'Active' : 'Inactive'; // org values
        hcp.PRM_CaseManager__c = uow.caseManagerId;
        hcp.PRM_RecordKey__c = uow.groupKey;                              // {taxId}-{groupName}
        putDate(hcp, 'EffectiveFrom', uow.node.get('effectiveFrom'));
        putDate(hcp, 'EffectiveTo', uow.node.get('effectiveTo'));
        // AccountId set after the Account upsert (FK)
        uow.hcp = hcp;
    }

    // ── DML (idempotent; upsert populates Id on the same instances) ──

    private void upsertVendorAccounts(List<GroupUnitOfWork> unitsOfWork) {
        List<Account> accounts = new List<Account>();
        for (GroupUnitOfWork uow : unitsOfWork) accounts.add(uow.vendor);
        upsert accounts HealthCloudGA__SourceSystemId__c;   // existing Unique External Id (no new field)
    }

    private void upsertEinIdentifiers(List<GroupUnitOfWork> unitsOfWork) {
        List<Identifier> identifiers = new List<Identifier>();
        for (GroupUnitOfWork uow : unitsOfWork) {
            uow.ein.ParentRecordId = uow.vendor.Id;
            identifiers.add(uow.ein);
        }
        upsert identifiers PRM_RecordKey__c;
    }

    private void upsertGroupHealthcareProviders(List<GroupUnitOfWork> unitsOfWork) {
        List<HealthcareProvider> providers = new List<HealthcareProvider>();
        for (GroupUnitOfWork uow : unitsOfWork) {
            uow.hcp.AccountId = uow.vendor.Id;
            providers.add(uow.hcp);
        }
        upsert providers PRM_RecordKey__c;
    }

    private Map<String, Object> buildResponse(List<GroupUnitOfWork> unitsOfWork) {
        List<Object> results = new List<Object>();
        for (GroupUnitOfWork uow : unitsOfWork) {
            results.add(new Map<String, Object>{
                'taxId' => uow.taxId,
                'groupAccountId' => uow.vendor.Id,
                'groupIdentifierId' => uow.ein.Id,
                'groupHealthcareProviderId' => uow.hcp.Id
            });
        }
        response = new Map<String, Object>{ 'groups' => results };
        return response;
    }

    // ── helpers (pure) ──
    private String key(List<String> parts) {
        List<String> safe = new List<String>();
        for (String part : parts) safe.add(part == null ? '' : part);
        return String.join(safe, KEY_DELIMITER);
    }
    private Boolean asBool(Object value) {
        return value == null ? false : (Boolean) value;
    }
    // The batch injects typed values; accept Date or an ISO yyyy-MM-dd string.
    private void putDate(SObject record, String field, Object value) {
        if (value == null) {
            return;
        }
        if (value instanceof Date) {
            record.put(field, (Date) value);
        } else if (String.isNotBlank(String.valueOf(value))) {
            record.put(field, Date.valueOf(String.valueOf(value)));   // expects yyyy-MM-dd (normalize at batch)
        }
    }
}
```

**`PRM_GroupService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E03_PRM_GroupService.md`. Open items (OQ‑E3‑4b/5/7/10/11/12/13/15) still apply — **especially the vendor type (OQ‑E3‑10) and the active/effective/credentialing source (OQ‑E3‑7).**

---

## Appendix B — Field metadata `PRM_RecordKey__c` (Identifier + HealthcareProvider)

> **Already in the repo; the task is to DEPLOY to the target org** (design §3 finding — absent from IBXDEV01). Shared with E2. Same spec on both objects.

`force-app/main/default/objects/Identifier/fields/PRM_RecordKey__c.field-meta.xml` **and** `force-app/main/default/objects/HealthcareProvider/fields/PRM_RecordKey__c.field-meta.xml`:

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
    <description>Durable business key for idempotent upsert during async creation (Epic E). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

> **Account:** no metadata — reuses the existing `HealthCloudGA__SourceSystemId__c` (Unique, External Id).

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set.

```xml
<fieldPermissions>
    <field>Identifier.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
<fieldPermissions>
    <field>HealthcareProvider.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

> Confirm `Account.HealthCloudGA__SourceSystemId__c` is already editable by the batch user (T1.2); add its `fieldPermissions` if not.

---

## Appendix D — Apex test class `PRM_GroupServiceTest` (+ meta)

> Reuses `PRM_TestDataFactory` + the modern `Assert`. The test **plays the batch's role** — it builds `params.groups[]` (deduped) with injected context. **⚠ `IndividualApplication` (Case Manager) test data is undocumented (OQ‑E3‑15)** — confirm/add `PRM_TestDataFactory.createCaseManagers(n)`.

```apex
@isTest
private class PRM_GroupServiceTest {

    private static Map<String, Object> groupNode(String taxId, String name, Id caseManagerId, Boolean isActive) {
        return new Map<String, Object>{
            'taxId' => taxId, 'groupName' => name, 'caseManagerId' => caseManagerId, 'isActive' => isActive
        };
    }
    private static Map<String, Object> params(List<Object> groups) {
        return new Map<String, Object>{ 'flow' => 'Practitioner Creation', 'groups' => groups };
    }

    @isTest
    static void shouldCreateGroupGraph_WhenBulk() {
        // ⚠ OQ-E3-15: confirm/extend PRM_TestDataFactory with a Case Manager (IndividualApplication) builder.
        List<IndividualApplication> cms = PRM_TestDataFactory.createCaseManagers(50);
        List<Object> groups = new List<Object>();
        Integer i = 0;
        for (IndividualApplication cm : cms) {
            groups.add(groupNode('27459103' + i, 'Group ' + i, cm.Id, true));
            i++;
        }

        Test.startTest();
        Integer soqlBefore = Limits.getQueries();
        Map<String, Object> resp = (Map<String, Object>) new PRM_GroupService().execute(params(groups));
        Integer soql = Limits.getQueries() - soqlBefore;
        Test.stopTest();

        Assert.areEqual(0, soql, 'Service must perform ZERO SOQL (batch injects context)');
        Assert.areEqual(cms.size(), [SELECT COUNT() FROM Account WHERE RecordType.DeveloperName = 'PRM_Vendor'], 'One vendor Account per group');
        Assert.areEqual(cms.size(), [SELECT COUNT() FROM Identifier WHERE PRM_Type__c = 'EIN'], 'One EIN Identifier per group');
        Assert.areEqual(cms.size(), [SELECT COUNT() FROM HealthcareProvider], 'One group HealthcareProvider per group');
        Assert.areEqual(cms.size(), ((List<Object>) resp.get('groups')).size(), 'One response row per group');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        IndividualApplication cm = PRM_TestDataFactory.createCaseManagers(1)[0];
        List<Object> groups = new List<Object>{ groupNode('274591038', 'Riverbend Family Health Associates LLC', cm.Id, true) };

        Test.startTest();
        new PRM_GroupService().execute(params(groups));   // first
        new PRM_GroupService().execute(params(groups));   // re-run (idempotent)
        Test.stopTest();

        Assert.areEqual(1, [SELECT COUNT() FROM Account WHERE HealthCloudGA__SourceSystemId__c = '274591038-Riverbend Family Health Associates LLC'], 'Re-run must upsert, not duplicate the vendor Account');
        Assert.areEqual(1, [SELECT COUNT() FROM Identifier WHERE PRM_RecordKey__c = '274591038_EIN'], 'Re-run must upsert, not duplicate the EIN Identifier');
        Assert.areEqual(1, [SELECT COUNT() FROM HealthcareProvider WHERE PRM_RecordKey__c = '274591038-Riverbend Family Health Associates LLC'], 'Re-run must upsert, not duplicate the group HCP');
    }

    @isTest
    static void shouldSetKeysAndPicklists_WhenBuilt() {
        IndividualApplication cm = PRM_TestDataFactory.createCaseManagers(1)[0];
        List<Object> groups = new List<Object>{ groupNode('356720194', 'Summit Specialty Partners PC', cm.Id, false) };

        Test.startTest();
        new PRM_GroupService().execute(params(groups));
        Test.stopTest();

        Account a = [SELECT HealthCloudGA__SourceSystemId__c, PRM_ParticipationStatus__c, IsActive, PRM_Pending__c FROM Account WHERE RecordType.DeveloperName='PRM_Vendor' LIMIT 1];
        Assert.areEqual('356720194-Summit Specialty Partners PC', a.HealthCloudGA__SourceSystemId__c, 'Account external id = {taxId}-{groupName}');
        Assert.areEqual('Participating', a.PRM_ParticipationStatus__c, 'ParticipationStatus constant');
        Assert.isFalse(a.IsActive, 'IsActive from injected value');
        Assert.isFalse(a.PRM_Pending__c, 'PRM_Pending__c never null');

        HealthcareProvider hcp = [SELECT Status, PRM_RecordKey__c FROM HealthcareProvider LIMIT 1];
        Assert.areEqual('Inactive', hcp.Status, 'Status = Inactive when isActive=false (org value, not "InActive")');
    }

    @isTest
    static void shouldThrow_WhenTaxIdOrGroupNameMissing() {
        IndividualApplication cm = PRM_TestDataFactory.createCaseManagers(1)[0];
        List<Object> groups = new List<Object>{ groupNode(null, 'No TaxId Group', cm.Id, true) };

        Test.startTest();
        try {
            new PRM_GroupService().execute(params(groups));
            Assert.fail('Expected an exception for a missing taxId');
        } catch (PRM_GroupService.PRM_GroupServiceException e) {
            Assert.isTrue(e.getMessage().contains('taxId'), 'Clear missing-key error');
        }
        Test.stopTest();
    }

    @isTest
    static void shouldReturnEmpty_WhenNoGroups() {
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_GroupService().execute(params(new List<Object>()));
        Test.stopTest();
        Assert.areEqual(0, ((List<Object>) resp.get('groups')).size(), 'Empty input -> empty response');
    }
}
```

**`PRM_GroupServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (0 SOQL + 3 DML), re‑run idempotency (no dups on all three objects), key/picklist correctness (Account external id, EIN key, HCP Status), missing‑key negative, empty input. Coverage ≥ 85%. *(Confirm `PRM_RecordKey__c` is deployed on the target org first — Appendix B.)*

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E3‑12). **Field + FLS first**, then classes, then tests. **Account needs no new field.**

```bash
# 1) Phase 1 — deploy PRM_RecordKey__c (Identifier + HealthcareProvider) + permission-set FLS
sf project deploy start \
  -d "force-app/main/default/objects/Identifier/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/objects/HealthcareProvider/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_GroupService.cls" \
  -d "force-app/main/default/classes/PRM_GroupServiceTest.cls" \
  -o <alias>

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_GroupServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check
sf data query -o <alias> \
  -q "SELECT Id, Name, HealthCloudGA__SourceSystemId__c FROM Account WHERE RecordType.DeveloperName='PRM_Vendor' ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E3‑10 (vendor type field+value) resolved; OQ‑E3‑7 (active/effective/credentialing source) resolved or injected.
- [ ] OQ‑E3‑4b (batch dedupes → `params.groups[]`) confirmed → service stays SOQL‑free.
- [ ] OQ‑E3‑5 (shared‑group case manager) + OQ‑E3‑11 (group CMA) decided.
- [ ] Target org confirmed (OQ‑E3‑12); `PRM_RecordKey__c` deployed (OQ‑E3‑13).
- [ ] `PRM_TestDataFactory.createCaseManagers` exists or added (OQ‑E3‑15).
- [ ] Field (Appendix B) + FLS (Appendix C) deploy as **External Id, Unique**.
- [ ] `PRM_GroupService` compiles; **0 SOQL**; `upsert … HealthCloudGA__SourceSystemId__c` + `upsert … PRM_RecordKey__c` resolve; runs in seq 2 before E13.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
