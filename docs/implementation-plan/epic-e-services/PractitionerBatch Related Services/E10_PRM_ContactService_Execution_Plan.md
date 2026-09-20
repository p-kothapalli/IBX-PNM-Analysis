# E10 · `PRM_ContactService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** Self‑contained for component generation (see **§0 Component inventory**): Apex class + `.cls-meta.xml` (**Appendix A**), `ContactProfile.PRM_RecordKey__c` field metadata (**Appendix B**), `PRM_AsyncJob_Access` FLS (**Appendix C**), test class + meta (**Appendix D**), deploy/validation (**Appendix E**). *(Metadata appendices included for parity with E05–E08; say the word for code‑only.)* **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered, and the target org (OQ‑E10‑1) is confirmed.
>
> **⚠ Aligns with the `prm-service-class-boundaries` rule (`.cursor/rules`).** A `PRM_*Service` is a **generic transformer**: it reads everything it needs from `params` (batch‑injected), builds in memory, and does one bulk DML — **no SOQL / correlation / source‑format branching in the service**. So, unlike the E10 design's §4.1 (which queries Account→PersonContactId), **the batch injects `practitionerId` (ContactId), `accountId`, and `caseManagerId` per node** and the service does **zero SOQL** (§4.1 / OQ‑E10‑2).
>
> **Source of truth:** `E10_PRM_ContactService.md` (design §1–§9, incl. org‑validation, CL‑E2‑1, NPI‑anchored idempotency) + the service‑boundary rule. Anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `ContactProfile.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/ContactProfile/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E10‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_ContactService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_ContactService.cls` (+ meta) | **NEW** | Appendix A |
| 4 | `PRM_ContactServiceTest` | Apex test class | `force-app/main/default/classes/PRM_ContactServiceTest.cls` (+ meta) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test` / `prm-service-class-boundaries`):** `PRM_` prefix; `with sharing`; **service does NO SOQL** (batch injects context); one bulk DML; **API version 66.0**; test reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class; bulk path tested at **251+**. **Error handling at the batch level** — the service lets exceptions propagate (no inline try/catch); the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain.

---

## 1. Confirmed requirements (from `E10_PRM_ContactService.md` + the service‑boundary rule)

- **[CONFIRMED]** `PRM_ContactService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1).** **Writes:** `ContactProfile`. (Design §1, §4.)
- **[CONFIRMED]** **Gated** — only practitioners with a **`providerInformation`** node. **DELEGATED branch only.** (Design §1.)
- **[CONFIRMED]** **One `ContactProfile` per practitioner** (1:1). (Design §1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk, each `{ practitionerInfo (id, npi), providerInformation, providerInformationPersonalPronouns }` **+ batch‑injected `practitionerId`, `caseManagerId`** (rule); build all rows, then **one bulk DML**. (Design §4, §5 + rule.)
- **[CONFIRMED — per rule] Context is batch‑injected; the service does NO SOQL.** `accountId` = `practitionerInfo.id` → `PRM_PersonAccount__c`; `practitionerId` (PersonContactId, **injected by the batch**) → `ContactId`; `caseManagerId` (from `PRM_AsyncJobRecords__c`, **injected by the batch**) → `PRM_CaseManager__c`. *(Supersedes the design §4.1 Account query — that resolution moves to the batch.)*
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — E02 §8 CL‑E2): `upsert` `ContactProfile` by **`PRM_RecordKey__c = {npi}`** (single‑part key; ContactProfile is 1:1 with the practitioner). (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E10‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`ContactProfile`** + Read+Edit FLS on `PRM_AsyncJob_Access`. **The field does not exist yet — creating it is a required E10 deliverable (Phase 1, T1.1).** *(Org: `PRM_ExternalId__c` is External Id but **not unique** → not reliably upsertable.)* (Design §3.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV01):** `PRM_PersonAccount__c`←accountId, `ContactId`←practitionerId (**required**), `PRM_CaseManager__c`←caseManagerId, `Race`←`RacialIdentity`, `PRM_Ethnicity__c`←`CulturalIdentityAPI` (default `'Prefer not to share'`), `PRM_HispanicLatino__c`←`IdentifyasHispanic`, `PRM_HispanicOrigin__c`←`HispanicOriginAPI`, `PRM_PersonalPronoun__c`/`PRM_PersonalPronounNotListed__c`←pronouns, the 4 `*IsDirectoryPrint__c`←confirmation flags (toBool), `PRM_LastUpdatedByProvider__c`=`System.now()`, `PRM_RecordKey__c`=npi. (Design §6.)
- **[CONFIRMED]** **Service‑computed (pure, in‑memory — allowed by the rule):** `PRM_Ethnicity__c` blank→`'Prefer not to share'`; the 4 `*IsDirectoryPrint__c` (toBool, default false); `PRM_LastUpdatedByProvider__c` (`System.now()`); `PRM_RecordKey__c`. (Design §5.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** by `PRM_RecordKey__c`; gated; returns `contactProfileId` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, contactProfileId }`. (Design §4.)
- **[CONFIRMED]** **Governor:** **0 SOQL** (batch injected context) + **1 bulk DML**; no DML/SOQL in loops. *(Design said 1 SOQL; the rule moves that query to the batch.)*
- **[CONFIRMED]** **Effort:** ~1.0 engineer‑day. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set), Epic B (`PRM_ServiceBase`), **E1** (Account/PersonContact/Case Manager), the **`PractitionerBatch`** wiring (resolves + injects `practitionerId`/`caseManagerId`), and E10's own `PRM_RecordKey__c` field + FLS. **No E2 dependency.**

> **🔎 Org validation (IBXDEV01, 2026‑06‑29):**
> - `PRM_PersonAccount__c`→Account (nullable); **`ContactId`→Contact, REQUIRED** (`nillable=false`; design notes it's also unique — 1:1 safety net); `PRM_CaseManager__c`→IndividualApplication.
> - **Multipicklists:** `Race` (8 vals incl. `Prefer not to share`), `PRM_Ethnicity__c` (273 vals incl. `Prefer not to share`), `PRM_HispanicOrigin__c` (44), `PRM_PersonalPronoun__c` (6). **`PRM_HispanicLatino__c`** is a single **picklist** (`Hispanic/Latino`, `Non-Hispanic/Non-Latino`, `Unknown`). `PRM_PersonalPronounNotListed__c` = text.
> - **4 `*IsDirectoryPrint__c` = required booleans** (`nillable=false`). `PRM_LastUpdatedByProvider__c` = **datetime** (nullable).
> - `PRM_ExternalId__c` = Text, **External Id but NOT unique** → not reliably upsertable → new `PRM_RecordKey__c` (Unique) per design §3.

---

## 2. Constraints

- **[CONFIRMED — rule]** **No SOQL / correlation / source‑format branching in the service.** The batch resolves Ids (`practitionerId`, `caseManagerId`) and normalizes source values; the service reads `params`, builds in memory, one bulk DML.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch**. (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch user via `PRM_AsyncJob_Access`) — `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E10‑4).
- **[CONFIRMED]** **`ContactId` is required** — the batch must inject a non‑null `practitionerId` (PersonContactId) or the insert fails (OQ‑E10‑6).
- **[CONFIRMED]** **Gated:** practitioners with no `providerInformation` are skipped (no row, not in the response).
- **[OPEN]** Multipicklist values (`Race`, `PRM_Ethnicity__c`, `PRM_HispanicOrigin__c`, `PRM_PersonalPronoun__c`) must be **active picklist entries**, `;`‑joined if multiple — **normalized at the batch/intake** per the rule (OQ‑E10‑3).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds one `ContactProfile` each per the §6 map; **one bulk DML** regardless of chunk size; **zero SOQL** in the service.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running on the same chunk produces **no duplicates** (1:1 per practitioner).
- **[CONFIRMED]** Context (`accountId`, `practitionerId`/ContactId, `caseManagerId`) read from `params` (batch‑injected) — not queried.
- **[CONFIRMED]** Demographic defaults computed (`'Prefer not to share'`, the 4 IsDirectoryPrint booleans, `PRM_LastUpdatedByProvider__c`).
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, contactProfileId }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners), (b) a **re‑run/idempotency** test, and (c) a **required‑field negative** (null `practitionerId` → `DmlException` on `ContactId`); Test Evidence Report + human sign‑off (Epic A §A7).
- **[CONFIRMED]** Field API names/types validated against the org (done — re‑confirm on the target org, OQ‑E10‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E10‑1…OQ‑E10‑8)
- **T0.1 — Target org** (OQ‑E10‑1). Completion: org confirmed.
- **T0.2 — Confirm the batch‑injection contract** (OQ‑E10‑2, **rule‑driven**): `PractitionerBatch` injects `practitionerId` (PersonContactId) + `caseManagerId` per node (the service no longer queries). Completion: contract confirmed.
- **T0.3 — Verify dependencies present on `main`:** `PRM_ServiceBase`; E1 (Account/PersonContact/Case Manager + `PRM_AsyncJobRecords__c`); the permission set `PRM_AsyncJob_Access`. *(E10's `PRM_RecordKey__c` is **NOT pre‑existing** — created in Phase 1.)* Completion: all present.
- **T0.4 — Resolve open data items:** multipicklist value/`;`‑join normalization (OQ‑E10‑3, batch/intake), `'Prefer not to share'` Ethnicity default (OQ‑E10‑8, org‑valid), no‑NPI policy (OQ‑E10‑4), CL‑E2‑1 object confirm (OQ‑E10‑7). Completion: each decided or deferred.

### Phase 1 — E10 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `ContactProfile`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (Appendices B–C). **Confirmed: the field does not exist yet** (`PRM_ExternalId__c` is External Id but **not unique**).
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS deployed.
  - Dependencies: T0.1. Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing 572 rows (field new/empty → low). Completion: field + FLS deployed.

### Phase 2 — `PRM_ContactService` core *(M2)*
- **T2.1 — Class + `execute`; parse + gate (no SOQL)**
  - Purpose: parse `practitioners[]`; keep only gated (has `providerInformation`); read batch‑injected `practitionerId`/`caseManagerId` + `practitionerInfo.id`/`npi`.
  - Outcome: Appendix A step 1. Impacted: `classes/PRM_ContactService.cls` (+ test).
  - Validation: compiles; gating correct; **no SOQL in the class** (rule). Testing: unit (parse + gate). Risks: **[RISK]** missing injected `practitionerId` → ContactId null (OQ‑E10‑6). Completion: parse + gate green.
- **T2.2 — `buildContactProfile` + demographic defaults + `PRM_RecordKey__c`**
  - Purpose: in‑memory `ContactProfile` per §6; Ethnicity default; 4 IsDirectoryPrint via toBool; `System.now()`; key = npi.
  - Dependencies: T2.1. Validation: field‑by‑field unit assertions; key = npi. Testing: builder unit (defaults; confirmation flags; pronouns). Risks: **[RISK]** multipicklist values not active (OQ‑E10‑3). Completion: builder unit‑tested.
- **T2.3 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; per‑practitioner response (gated subset, input order).
  - Dependencies: T2.2. Validation: rows have correct FKs + key; DML count = 1; **SOQL count = 0**. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildContactProfile` (Ethnicity default, IsDirectoryPrint booleans, LastUpdated, pronouns, key), gating; assert **0 SOQL** in the service.
- **T3.2 Bulk/governor:** 251+ practitioners → 0 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → `ContactProfile` count unchanged (1:1 upsert by npi).
- **T3.4 Negative/edge:** missing `providerInformation` (skipped), **null `practitionerId` → `DmlException`** (ContactId required, OQ‑E10‑6), invalid multipicklist value (OQ‑E10‑3), no‑NPI (OQ‑E10‑4).
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `ContactProfile` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E10‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/contact-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Commit prefix `[E10]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION — rule] Move context resolution to the batch.** The E10 design §4.1 has the service query `Account → PersonContactId`; the `prm-service-class-boundaries` rule **forbids that**. The `PractitionerBatch` must resolve `practitionerId` (PersonContactId) + `caseManagerId` and **inject them per node**; the service reads them. *(Same correction applies to the already‑written E05/E06/E07/E08 plans — flag to revise those services to read injected Ids rather than query.)*
- **[RISK] `ContactId` required (OQ‑E10‑6).** If the batch doesn't inject a valid `practitionerId`, the insert fails the whole chunk. Confirm the batch always supplies the PersonContactId (E1 stamped it on the Account).
- **[RISK] Multipicklist values (OQ‑E10‑3).** `Race`/`PRM_Ethnicity__c`/`PRM_HispanicOrigin__c`/`PRM_PersonalPronoun__c` are restricted multipicklists — an inactive value throws on `upsert`. Per the rule, **normalize + `;`‑join + validate at the batch/intake**, not the service.
- **[RECOMMENDATION] Ethnicity default (OQ‑E10‑8).** `'Prefer not to share'` is org‑valid for `PRM_Ethnicity__c` (and `Race`) — the blank→default is a pure in‑memory formula (rule‑allowed). Confirm it's the desired default.
- **[RECOMMENDATION] CL‑E2‑1.** Confirm the object is **`ContactProfile`** (not `Contact`) in the flow/plan docs (OQ‑E10‑7).
- **[RECOMMENDATION] `ContactId` uniqueness as a dup safety net.** Even with the `PRM_RecordKey__c=npi` upsert, the unique `ContactId` enforces 1:1 — keep both.

---

## 6. Gaps & hidden dependencies

- **Batch‑injection contract (OQ‑E10‑2, rule)** — `practitionerId` + `caseManagerId` per node; service does no SOQL.
- **`ContactId` required (OQ‑E10‑6)** — batch must inject a valid PersonContactId.
- **Multipicklist normalization (OQ‑E10‑3)** — batch/intake `;`‑join + validate.
- **Target org (OQ‑E10‑1)**; **E10 `PRM_RecordKey__c` + FLS** — not yet created → Phase 1.
- **CL‑E2‑1 (OQ‑E10‑7)**; **no‑NPI (OQ‑E10‑4)**.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E10‑1 — Target org** for deploy/test.
- **OQ‑E10‑2 — Batch‑injection contract (rule).** Confirm `PractitionerBatch` injects `practitionerId` (PersonContactId) + `caseManagerId` per node so the service does **no SOQL**.
- **OQ‑E10‑3 — Multipicklist values + `;`‑join.** Are inbound `Race`/`PRM_Ethnicity__c`/`PRM_HispanicOrigin__c`/`PRM_PersonalPronoun__c` active picklist values, and `;`‑joined for multiples? *(Normalize at batch/intake per the rule.)*
- **OQ‑E10‑4 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key.
- **OQ‑E10‑5 — Removed** *(folded into OQ‑E10‑2; the field is a confirmed Phase 1 deliverable).*
- **OQ‑E10‑6 — `ContactId` (required) always injected?** Confirm the batch always supplies a non‑null `practitionerId`.
- **OQ‑E10‑7 (CL‑E2‑1) — Object is `ContactProfile` (not `Contact`)?** Confirm in the flow/plan docs.
- **OQ‑E10‑8 — Ethnicity default.** Confirm blank `CulturalIdentityAPI` → `'Prefer not to share'` (org‑valid).

*(Already resolved: org validation done — fields/types/multipicklists confirmed; `ContactId` unique/required (1:1); new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E10's `PRM_RecordKey__c` is NOT yet created → built as E10 Phase 1**.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | Batch doesn't inject `practitionerId` → `ContactId` null → chunk fails | Medium | High | OQ‑E10‑2/6; batch injects PersonContactId; T3.4 |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | Multipicklist value not active → chunk insert fails | Medium | Medium | OQ‑E10‑3; normalize/validate at batch/intake; T3.4 |
| R‑4 | Service does its own SOQL (violates rule) | Low | Medium | rule check in review; assert 0 SOQL in T3.1 |
| R‑5 | No target org → can't deploy/test | Medium | High | OQ‑E10‑1 |
| R‑6 | CL‑E2‑1 mis‑modeled as `Contact` in flow docs | Low | Medium | OQ‑E10‑7 |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. OQ‑E10‑2 injection contract) → 1 (**create the field + FLS**) → 2 (service) → 3 → 4 → 5. Runs in `PractitionerBatch` (no E2 dependency).
- **Effort:** within the ~1.0 d catalog estimate — class + builder + defaults ~0.4 · tests ~0.4 · evidence/VCS folded in.
- **Depends on:** Epic A + Epic B + E1 on `main`, plus `PractitionerBatch`. **Feeds:** nothing downstream consumes E10 (ContactProfile is a leaf).

---

## 10. What happens after sign‑off

Resolve OQ‑E10‑1…OQ‑E10‑8 — **the batch‑injection contract (OQ‑E10‑2) is the gate** (it's what keeps the service SOQL‑free per the rule). Then: **create + deploy the E10 `PRM_RecordKey__c` field + FLS (Phase 1)** → build the service per **Appendix A** (parse + gate → build + defaults + key → one bulk `upsert` → response) → tests → Test Evidence Report → human sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E10‑1) and the injection contract (OQ‑E10‑2) are confirmed.**

---

## Appendix A — Apex class `PRM_ContactService` (+ meta)

> Full `PRM_ContactService` (expands `E10…md` §4.2, **rule‑aligned**). **Depends on** `PRM_ServiceBase`. **No SOQL** — `practitionerId` (ContactId) + `caseManagerId` are **batch‑injected** per node (OQ‑E10‑2). Multipicklist values are assumed **normalized/`;`‑joined upstream** (rule — OQ‑E10‑3). `ContactProfile` is 1:1 → key = npi.

```apex
public with sharing class PRM_ContactService extends PRM_ServiceBase {

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');                          // DELEGATED (context)
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) gate + build (NO SOQL — context is batch-injected, per prm-service-class-boundaries)
        List<Map<String, Object>> gated = new List<Map<String, Object>>();   // input order
        List<ContactProfile> rows = new List<ContactProfile>();
        if (practitioners != null) {
            for (Object o : practitioners) {
                Map<String, Object> app = (Map<String, Object>) o;
                Map<String, Object> info = (Map<String, Object>) app.get('providerInformation');
                if (info == null) continue;                                  // GATED: skip
                gated.add(app);
                rows.add(buildContactProfile(app));
            }
        }
        if (rows.isEmpty()) {
            response = new Map<String, Object>{ 'practitioners' => new List<Object>() };
            return response;
        }

        // 2) ONE bulk upsert by the External Id (idempotent — §7)
        upsert rows PRM_RecordKey__c;

        // 3) response (input order; gated subset)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (Integer i = 0; i < gated.size(); i++) {
            Map<String, Object> pInfo = (Map<String, Object>) gated[i].get('practitionerInfo');
            results.add(new Map<String, Object>{
                'accountId'        => pInfo.get('id'),
                'contactProfileId' => rows[i].Id
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── builder (pure in-memory; field map per §6; reads batch-injected Ids) ──
    private ContactProfile buildContactProfile(Map<String, Object> app) {
        Map<String, Object> info = (Map<String, Object>) app.get('practitionerInfo');
        Map<String, Object> pi   = (Map<String, Object>) app.get('providerInformation');
        Map<String, Object> pron = (Map<String, Object>) app.get('providerInformationPersonalPronouns');

        ContactProfile cp = new ContactProfile();
        cp.PRM_PersonAccount__c = (Id) info.get('id');                       // accountId
        cp.ContactId            = (Id) app.get('practitionerId');            // PersonContactId — batch-injected (REQUIRED, OQ-E10-6)
        cp.PRM_CaseManager__c   = (Id) app.get('caseManagerId');            // batch-injected (rule)

        // demographics (multipicklists assumed normalized/;-joined upstream — OQ-E10-3)
        cp.Race                  = (String) pi.get('RacialIdentity');
        cp.PRM_Ethnicity__c      = blankDefault((String) pi.get('CulturalIdentityAPI'), 'Prefer not to share');
        cp.PRM_HispanicLatino__c = (String) pi.get('IdentifyasHispanic');    // single picklist
        cp.PRM_HispanicOrigin__c = (String) pi.get('HispanicOriginAPI');
        if (pron != null) {
            cp.PRM_PersonalPronoun__c          = (String) pron.get('PersonalPronouns');
            cp.PRM_PersonalPronounNotListed__c = (String) pron.get('PronounNotListed');
        }

        // required booleans (default false)
        cp.PRM_RaceIsDirectoryPrint__c           = toBool(pi.get('RacialIdentityConfirmation'));
        cp.PRM_EthnicityIsDirectoryPrint__c      = toBool(pi.get('CulturalIdentityConfirmation'));
        cp.PRM_HispanicOriginIsDirectoryPrint__c = toBool(pi.get('HispanicOriginConfirmation'));
        cp.PRM_HispanicLatinoIsDirectoryPrint__c = toBool(pi.get('ConfirmationQuestion1'));

        cp.PRM_LastUpdatedByProvider__c = System.now();                      // datetime
        cp.PRM_RecordKey__c             = (String) info.get('npi');          // single-part key = npi (§2)
        return cp;
    }

    // ── helpers (pure) ──
    private String blankDefault(String v, String d) { return String.isBlank(v) ? d : v; }
    private Boolean toBool(Object o) { return o == null ? false : (Boolean) o; }
}
```

**`PRM_ContactService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E10_PRM_ContactService.md` + the `prm-service-class-boundaries` rule. Open items (OQ‑E10‑1…OQ‑E10‑8) still apply — **especially OQ‑E10‑2 (batch injection) and OQ‑E10‑3 (multipicklist normalization).**

---

## Appendix B — Field metadata `ContactProfile.PRM_RecordKey__c`

> **NEW (E10‑owned).** Path: `force-app/main/default/objects/ContactProfile/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`.

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
    <required>false</required>
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E10 — ContactProfile). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`.

```xml
<fieldPermissions>
    <field>ContactProfile.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_ContactServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`**, modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, re‑run/idempotency, and asserts the service does **0 SOQL** (via `Limits`). ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`). The test **plays the batch's role** — it injects `practitionerId` (the Account's `PersonContactId`) + `caseManagerId` per node (the service doesn't query).

```apex
@isTest
private class PRM_ContactServiceTest {

    private static final Integer BULK = 251;

    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);   // Person Accounts + a Case Manager each
    }

    // The test injects practitionerId/caseManagerId (the BATCH's job — the service never queries).
    private static Map<String, Object> buildParams(List<Account> accts, Map<Id, Id> contactByAcct,
            Map<Id, Id> cmByAcct, Map<Id, String> npiByAcct, Boolean withProviderInfo) {
        List<Object> practitioners = new List<Object>();
        for (Account a : accts) {
            Map<String, Object> node = new Map<String, Object>{
                'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => npiByAcct.get(a.Id) },
                'practitionerId'   => contactByAcct.get(a.Id),     // batch-injected PersonContactId
                'caseManagerId'    => cmByAcct.get(a.Id)           // batch-injected
            };
            if (withProviderInfo) {
                node.put('providerInformation', new Map<String, Object>{
                    'RacialIdentity' => 'Asian',
                    'CulturalIdentityAPI' => '',                    // -> default 'Prefer not to share'
                    'IdentifyasHispanic' => 'Unknown',
                    'HispanicOriginAPI' => '',
                    'RacialIdentityConfirmation' => true,
                    'CulturalIdentityConfirmation' => false,
                    'HispanicOriginConfirmation' => false,
                    'ConfirmationQuestion1' => false
                });
                node.put('providerInformationPersonalPronouns', new Map<String, Object>{
                    'PersonalPronouns' => 'She / Her', 'PronounNotListed' => ''
                });
            }
            practitioners.add(node);
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    private static Map<Id, Id> contactByAccount(List<Account> accts) {
        Map<Id, Id> m = new Map<Id, Id>();
        for (Account a : [SELECT Id, PersonContactId FROM Account WHERE Id IN :accts]) m.put(a.Id, a.PersonContactId);
        return m;
    }
    private static Map<Id, String> npiMap(List<Account> accts) {
        Map<Id, String> m = new Map<Id, String>(); Integer n = 0;
        for (Account a : accts) m.put(a.Id, '40000000' + n++);
        return m;
    }

    @isTest
    static void shouldCreateOnePerPractitioner_WhenBulk() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<String, Object> params = buildParams(accts, contactByAccount(accts),
            PRM_TestDataFactory.caseManagerByAccount(accts), npiMap(accts), true);

        Test.startTest();
        Integer before = Limits.getQueries();
        Map<String, Object> resp = (Map<String, Object>) new PRM_ContactService().execute(params);
        Integer soql = Limits.getQueries() - before;
        Test.stopTest();

        Assert.areEqual(BULK, [SELECT COUNT() FROM ContactProfile], 'One ContactProfile per practitioner');
        Assert.areEqual(0, soql, 'Service must perform ZERO SOQL (batch injects context)');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(), 'One response entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, Id> cb = contactByAccount(accts);
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<Id, String> npis = npiMap(accts);

        Test.startTest();
        new PRM_ContactService().execute(buildParams(accts, cb, cm, npis, true));   // first
        new PRM_ContactService().execute(buildParams(accts, cb, cm, npis, true));   // re-run (idempotent)
        Test.stopTest();

        Assert.areEqual(BULK, [SELECT COUNT() FROM ContactProfile], 'Re-run must upsert by npi, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoProviderInformation() {
        List<Account> accts = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = buildParams(accts, contactByAccount(accts),
            PRM_TestDataFactory.caseManagerByAccount(accts), npiMap(accts), false);  // no providerInformation

        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_ContactService().execute(params);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM ContactProfile], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(), 'Response excludes gated-out practitioners');
    }

    @isTest
    static void shouldDefaultEthnicityAndSetKey_WhenBuilt() {
        List<Account> accts = [SELECT Id FROM Account LIMIT 1];
        Map<Id, String> npis = npiMap(accts);
        Map<String, Object> params = buildParams(accts, contactByAccount(accts),
            PRM_TestDataFactory.caseManagerByAccount(accts), npis, true);

        Test.startTest();
        new PRM_ContactService().execute(params);
        Test.stopTest();

        ContactProfile cp = [
            SELECT PRM_Ethnicity__c, PRM_RaceIsDirectoryPrint__c, PRM_LastUpdatedByProvider__c, PRM_RecordKey__c
            FROM ContactProfile LIMIT 1
        ];
        Assert.areEqual('Prefer not to share', cp.PRM_Ethnicity__c, 'Blank CulturalIdentityAPI should default');
        Assert.isTrue(cp.PRM_RaceIsDirectoryPrint__c, 'RacialIdentityConfirmation=true should map to the flag');
        Assert.isNotNull(cp.PRM_LastUpdatedByProvider__c, 'LastUpdatedByProvider should be set');
        Assert.isNotNull(cp.PRM_RecordKey__c, 'Record key (npi) should be set');
    }

    // ContactId is required (org) -> a null injected practitionerId must fail the insert (OQ-E10-6).
    @isTest
    static void shouldThrow_WhenContactIdMissing() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> node = new Map<String, Object>{
            'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '4999999999' },
            'practitionerId'   => null,                          // batch failed to inject -> ContactId null
            'caseManagerId'    => PRM_TestDataFactory.caseManagerByAccount(new List<Account>{ a }).get(a.Id),
            'providerInformation' => new Map<String, Object>{ 'CulturalIdentityAPI' => '' }
        };
        Map<String, Object> params = new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => new List<Object>{ node } };

        Test.startTest();
        try {
            new PRM_ContactService().execute(params);
            Assert.fail('Expected a DmlException for the required ContactId');
        } catch (DmlException e) {
            Assert.isTrue(e.getMessage().length() > 0, 'DmlException should be raised for the missing required ContactId');
        }
        Test.stopTest();
    }
}
```

**`PRM_ContactServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ → **0 SOQL** + 1 DML), re‑run idempotency (1:1), gating (no `providerInformation`), defaults/flags/key correctness, required‑`ContactId` negative. Add a multipicklist‑value negative once OQ‑E10‑3 is set. Coverage ≥ 85%.

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E10‑1). **Field + FLS first**, then classes, then tests.

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/ContactProfile/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_ContactService.cls" \
  -d "force-app/main/default/classes/PRM_ContactServiceTest.cls" \
  -o <alias>

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_ContactServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check
sf data query -o <alias> \
  -q "SELECT Id, PRM_PersonAccount__c, ContactId, PRM_Ethnicity__c, PRM_LastUpdatedByProvider__c, PRM_RecordKey__c FROM ContactProfile ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E10‑2 (batch injects `practitionerId`/`caseManagerId`) confirmed → service stays SOQL‑free.
- [ ] OQ‑E10‑3 (multipicklist values/`;`‑join) normalized at batch/intake; OQ‑E10‑8 (Ethnicity default) confirmed.
- [ ] Target org confirmed (OQ‑E10‑1); CL‑E2‑1 object confirmed (OQ‑E10‑7).
- [ ] `PRM_TestDataFactory` builders exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_ContactService` compiles; **0 SOQL** in the service; `upsert … PRM_RecordKey__c` resolves.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
