# E11 · `PRM_LanguageService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** Self‑contained for component generation (see **§0 Component inventory**): Apex class + `.cls-meta.xml` (**Appendix A**), `PersonLanguage.PRM_RecordKey__c` field metadata (**Appendix B**), `PRM_AsyncJob_Access` FLS (**Appendix C**), test class + meta (**Appendix D**), deploy/validation (**Appendix E**). *(Metadata appendices included for parity with E05–E10; say the word for code‑only.)* **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered — **especially the `Language` ISO‑code mapping (OQ‑E11‑3)** — and the target org (OQ‑E11‑1) is confirmed.
>
> **⚠ Aligns with the `prm-service-class-boundaries` rule.** The service reads everything from `params` (batch‑injected), builds in memory, one bulk DML — **no SOQL / correlation / source‑format branching in the service**. So the design's §4.1 HCP query moves to the **batch**: it injects `healthcareProviderId` + `caseManagerId` per node and the service does **zero SOQL** (§4.1 / OQ‑E11‑2). *(E05–E08 service‑side queries will be reconciled to this rule when `PRM_PractitionerBatch` (E20) is implemented.)*
>
> **Source of truth:** `E11_PRM_LanguageService.md` (design §1–§9, incl. org‑validation, NPI‑anchored idempotency) + the service‑boundary rule. Anything not stated is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PersonLanguage.PRM_RecordKey__c` | Custom Field — Text(255), External Id, **Unique**, case‑insensitive | `force-app/main/default/objects/PersonLanguage/fields/PRM_RecordKey__c.field-meta.xml` | **NEW** (E11‑owned) | Appendix B |
| 2 | `PRM_AsyncJob_Access` FLS for the field | Permission Set — `fieldPermissions` (Read+Edit) | `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml` | **EDIT** (base permset = Epic A) | Appendix C |
| 3 | `PRM_LanguageService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_LanguageService.cls` (+ meta) | **NEW** | Appendix A |
| 4 | `PRM_LanguageServiceTest` | Apex test class | `force-app/main/default/classes/PRM_LanguageServiceTest.cls` (+ meta) | **NEW** | Appendix D |
| 5 | `PRM_TestDataFactory` builders | Apex test factory (reuse) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix D note |

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test` / `prm-service-class-boundaries`):** `PRM_` prefix; `with sharing`; **service does NO SOQL** (batch injects context); one bulk DML; **API version 66.0**; test reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class; bulk path tested at **251+**. **Error handling at the batch level** — the service lets exceptions propagate (no inline try/catch); the Epic C framework logs via `PRM_ExceptionLogger` and halts the chain.

---

## 1. Confirmed requirements (from `E11_PRM_LanguageService.md` + the service‑boundary rule)

- **[CONFIRMED]** `PRM_LanguageService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1), after E2.** **Writes:** `PersonLanguage`. (Design §1, §4.)
- **[CONFIRMED]** **Gated** — only practitioners with a **non‑empty `languages[]`**. **DELEGATED branch only.** (Design §1.)
- **[CONFIRMED]** **Depends on E2** (same batch) for `healthcareProviderId`; needs E1's Account + Case Manager. (Design §1, §4.1.)
- **[CONFIRMED]** **Bulk:** input `params.practitioners` = the batch chunk, each `{ practitionerInfo (id, npi), languages[] }` **+ batch‑injected `healthcareProviderId`, `caseManagerId`** (rule); build all rows, then **one bulk DML**. (Design §4, §5 + rule.)
- **[CONFIRMED — per rule] Context is batch‑injected; the service does NO SOQL.** `accountId` = `practitionerInfo.id` → `IndividualId`; `healthcareProviderId` (**injected**) → `PRM_HealthcareProvider__c`; `caseManagerId` (**injected**) → `PRM_CaseManager__c`. *(Supersedes the design §4.1 HCP query — that resolution moves to the batch.)*
- **[CONFIRMED]** **Idempotency — NPI‑anchored** (NPI unique — E02 §8 CL‑E2): `upsert` `PersonLanguage` by **`PRM_RecordKey__c = {npi}_{language}`** (one row per practitioner per language). **Grain provisional — OQ‑E11‑5.** (Design §2.)
- **[CONFIRMED]** **Prerequisite schema (E11‑owned, declarative) — NOT yet created:** `PRM_RecordKey__c` (Text 255, External Id, **Unique**, case‑insensitive) on **`PersonLanguage`** + Read+Edit FLS on `PRM_AsyncJob_Access`. **The field does not exist yet — creating it is a required E11 deliverable (Phase 1, T1.1).** *(Org: `PRM_ExternalId__c` is External Id but **not unique** → not reliably upsertable.)* (Design §3.)
- **[CONFIRMED]** **Field map (org‑validated, IBXDEV01):** `IndividualId`←accountId, `PRM_HealthcareProvider__c`←healthcareProviderId, `Language`←`languages[].value` (picklist — ISO code), `Name`←`languages[].value`, `Rank`←per‑practitioner sequence, `PRM_ShareInPublicDirectory__c`←`shareInDir ? 'Yes' : 'No'`, `PRM_LastUpdatedByProvider__c`←`lastUpdatedOn`, `PRM_CaseManager__c`←caseManagerId, `PRM_RecordKey__c` (computed). (Design §6.)
- **[CONFIRMED]** **Org‑validated field facts:** **`IndividualId`** polymorphic (Account/Contact/Individual), **required** — Account works; **`Language` REQUIRED picklist (337 ISO codes)**; **`Name` required**; **`Rank` required int**; `PRM_ShareInPublicDirectory__c` picklist `Yes`/`No`; `PRM_LastUpdatedByProvider__c` datetime. (Design §2, §6 + this plan's org check.)
- **[CONFIRMED]** **Service‑computed (pure, in‑memory — rule‑allowed):** `Rank` (per‑practitioner sequence), `PRM_ShareInPublicDirectory__c` (Yes/No from `shareInDir`), `PRM_RecordKey__c`. (Design §5.)
- **[CONFIRMED]** **DML / order:** a single **bulk `upsert`** by `PRM_RecordKey__c`; gated; returns `personLanguageIds` per practitioner. (Design §7.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order) per practitioner `{ accountId, personLanguageIds }`. (Design §4.)
- **[CONFIRMED]** **Governor:** **0 SOQL** (batch injected context) + **1 bulk DML**; no DML/SOQL in loops. *(Design said ~1 SOQL; the rule moves the HCP query to the batch.)*
- **[CONFIRMED]** **Effort:** ~0.5 engineer‑day. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set), Epic B (`PRM_ServiceBase`), **E1**, **E2** (HealthcareProvider), the **`PractitionerBatch`** wiring (resolves + injects `healthcareProviderId`/`caseManagerId`), and E11's own `PRM_RecordKey__c` field + FLS.

> **🔎 Org validation (IBXDEV01, 2026‑06‑29):**
> - **`IndividualId`** → polymorphic [Account, Contact, Individual], **REQUIRED** (`nillable=false`) — Account Id works. `PRM_HealthcareProvider__c` → HealthcareProvider (nullable). `PRM_CaseManager__c` → IndividualApplication.
> - **`Language` REQUIRED picklist — 337 values that are ISO codes** (`abk`, `orm`, `aar`, `afr`, `sqi`, `amh`, `ase`, … — English ≈ `eng`). **`Name` required** (Text). **`Rank` required `int`**.
> - `PRM_ShareInPublicDirectory__c` picklist `Yes`/`No` (nullable). `PRM_LastUpdatedByProvider__c` = datetime (nullable).
> - `PRM_ExternalId__c` = Text, **External Id but NOT unique** → not reliably upsertable → new `PRM_RecordKey__c` (Unique) per design §3.

---

## 2. Constraints

- **[CONFIRMED — rule]** **No SOQL / correlation / source‑format branching in the service.** The batch resolves Ids (`healthcareProviderId`, `caseManagerId`) and normalizes source values (esp. `Language`); the service reads `params`, builds in memory, one bulk DML.
- **[CONFIRMED]** Runs **inside a batch `execute()` chunk**; idempotency exists because **manual retry re‑runs the whole batch**. (Design §2 "Why".)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (batch user via `PRM_AsyncJob_Access`) — `PRM_RecordKey__c` FLS must be present.
- **[CONFIRMED]** Idempotency is **NPI‑anchored**; a practitioner must have an NPI for the key (no‑NPI policy — OQ‑E11‑6).
- **[CONFIRMED]** **Three required fields gate the insert:** `IndividualId` (← accountId), `Language` (valid picklist code), `Name`, and `Rank` (int). A blank/invalid any of these fails the chunk.
- **[CONFIRMED]** **Gated:** practitioners with empty `languages[]` are skipped (no rows, not in the response).
- **[OPEN]** `Language` must be a valid **ISO‑code picklist** value — the payload's `"English"` won't match; **map name→code at the batch/intake** (OQ‑E11‑3).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]`; for **gated** practitioners builds `PersonLanguage[]` per the §6 map (one row per language); **one bulk DML** regardless of chunk size; **zero SOQL** in the service.
- **[CONFIRMED]** **Idempotent (NPI‑anchored):** `upsert` by `PRM_RecordKey__c`; re‑running on the same chunk produces **no duplicates** (contingent on the grain — OQ‑E11‑5).
- **[CONFIRMED]** Context (`accountId`/IndividualId, `healthcareProviderId`, `caseManagerId`) read from `params` (batch‑injected) — not queried.
- **[CONFIRMED]** `Rank` sequenced per practitioner; `PRM_ShareInPublicDirectory__c` = Yes/No; `Language`/`Name` set from a valid value.
- **[CONFIRMED]** Returns per‑practitioner `{ accountId, personLanguageIds }` (input order, gated subset).
- **[CONFIRMED]** Apex ≥ 85% incl. (a) a **bulk** test (251+ practitioners × multiple languages), (b) a **re‑run/idempotency** test, and (c) a **required‑field negative** (invalid/blank `Language` → exception); Test Evidence Report + human sign‑off (Epic A §A7).
- **[CONFIRMED]** Field API names/types validated against the org (done — re‑confirm on the target org, OQ‑E11‑1).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E11‑1…OQ‑E11‑8)
- **T0.1 — Target org** (OQ‑E11‑1). Completion: org confirmed.
- **T0.2 — Confirm the batch‑injection contract** (OQ‑E11‑2, rule): `PractitionerBatch` injects `healthcareProviderId` + `caseManagerId` per node (service no SOQL). Completion: contract confirmed.
- **T0.3 — Resolve `Language` value mapping** (OQ‑E11‑3): does the payload send a valid **`Language` ISO code**, or a name (`"English"`) needing **name→code** mapping at batch/intake? Completion: mapping decided.
- **T0.4 — Verify dependencies present on `main`:** `PRM_ServiceBase`; E1; E2 (HealthcareProvider); the permission set `PRM_AsyncJob_Access`. *(E11's `PRM_RecordKey__c` is **NOT pre‑existing** — created in Phase 1.)* Completion: all present.
- **T0.5 — Resolve open data items:** dedupe grain (OQ‑E11‑5), `Rank` sequencing (OQ‑E11‑4), `Name` source (OQ‑E11‑9), `lastUpdatedOn` parse vs default (OQ‑E11‑8), no‑NPI policy (OQ‑E11‑6). Completion: each decided or deferred.

### Phase 1 — E11 schema prerequisite (declarative — **NEW field, must be created**) *(M1)*
- **T1.1 — Create `PRM_RecordKey__c` on `PersonLanguage`** (Text 255, External Id, Unique, case‑insensitive) + **Read+Edit FLS** on `PRM_AsyncJob_Access` (Appendices B–C). **Confirmed: the field does not exist yet** (`PRM_ExternalId__c` is External Id but **not unique**).
  - Purpose: enable External‑Id `upsert` idempotency. Outcome: field + FLS deployed.
  - Dependencies: T0.1. Validation: field deploys as External Id; describe resolves; running user can edit. Testing: trial `upsert … PRM_RecordKey__c` compiles. Risks: **[RISK]** unique‑constraint vs existing 880 rows (field new/empty → low). Completion: field + FLS deployed.

### Phase 2 — `PRM_LanguageService` core *(M2)*
- **T2.1 — Class + `execute`; parse + gate (no SOQL)**
  - Purpose: parse `practitioners[]`; keep only gated (non‑empty `languages`); read batch‑injected `healthcareProviderId`/`caseManagerId` + `practitionerInfo.id`/`npi`.
  - Outcome: Appendix A step 1. Impacted: `classes/PRM_LanguageService.cls` (+ test).
  - Validation: compiles; gating correct; **no SOQL** (rule). Testing: unit (parse + gate). Risks: **[RISK]** missing injected Ids. Completion: parse + gate green.
- **T2.2 — `buildLanguage` + `Rank` + `PRM_ShareInPublicDirectory__c` + `PRM_RecordKey__c`**
  - Purpose: in‑memory `PersonLanguage` per §6; `Rank` per‑practitioner sequence; Yes/No share flag; NPI‑anchored key; `Language`/`Name` from value.
  - Dependencies: T2.1, T0.3 (Language mapping), T0.4. Validation: field‑by‑field unit assertions; Rank order; key string. Testing: builder unit (rank order; share Yes/No; key). Risks: **[RISK]** `Language` value not a valid code (OQ‑E11‑3); `Rank` order (OQ‑E11‑4). Completion: builder unit‑tested.
- **T2.3 — Bulk `upsert` + response**
  - Purpose: one bulk `upsert … PRM_RecordKey__c`; per‑practitioner response (gated subset, input order).
  - Dependencies: T2.2. Validation: rows have correct FKs + key; DML count = 1; **SOQL count = 0**. Completion: bulk upsert + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildLanguage` (Rank sequence, share Yes/No, key, Language/Name), gating; assert **0 SOQL**.
- **T3.2 Bulk/governor:** 251+ practitioners × multiple languages → 0 SOQL + 1 DML; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → row count unchanged.
- **T3.4 Negative/edge:** empty `languages` (skipped), **invalid `Language` value → exception** (required picklist, OQ‑E11‑3), no‑NPI (OQ‑E11‑6).
  - Dependencies: Phases 1–2. Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `PersonLanguage` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** no org (OQ‑E11‑1). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/language-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Commit prefix `[E11]`. Schema (Phase 1) lands with/before the service.

---

## 5. Challenge / review of the proposed approach

- **[RISK] `Language` ISO‑code picklist (OQ‑E11‑3).** `Language` is a **required** picklist whose values are **ISO codes** (`eng`, `abk`, …), but the sample payload sends `"value": "English"`. A name won't match → the `upsert` throws, **and** the dedupe key (`{npi}_{language}`) would key on the wrong token. Per the rule, **map name→ISO code at the batch/intake** (or require the OmniScript to send codes) — not in the service.
- **[RECOMMENDATION] `Rank` sequencing (OQ‑E11‑4).** `Rank` is a required int — confirm the order (input order, 1‑based, vs primary‑language‑first) and whether it must be globally unique per practitioner.
- **[RECOMMENDATION] `Name` source (OQ‑E11‑9).** `Name` is required and the design maps it from `value` (the code). Confirm `Name` should be the code vs a display name.
- **[RECOMMENDATION] Move HCP resolution to the batch (rule).** The design §4.1 has the service query `HealthcareProvider` by NPI; the rule forbids it — the batch resolves + injects `healthcareProviderId`. (Reconciled with E05–E08 at E20 implementation.)
- **[RECOMMENDATION] `lastUpdatedOn` (OQ‑E11‑8).** Map `languages[].lastUpdatedOn` to `PRM_LastUpdatedByProvider__c` (datetime) — confirm format/parse, or default to `System.now()` when blank.
- **[RECOMMENDATION] Dedupe grain (OQ‑E11‑5).** `{npi}_{language}` assumes one row per practitioner per language; org data is test‑polluted (same Individual+Language repeats) — confirm with business.

---

## 6. Gaps & hidden dependencies

- **`Language` value mapping (OQ‑E11‑3)** — name→ISO code at batch/intake; gates insert + key.
- **Batch‑injection contract (OQ‑E11‑2, rule)** — `healthcareProviderId` + `caseManagerId` per node.
- **Target org (OQ‑E11‑1)**; **E11 `PRM_RecordKey__c` + FLS** — not yet created → Phase 1.
- **E2 dependency** — HealthcareProvider (injected `healthcareProviderId`).
- **`Rank` (OQ‑E11‑4)**, **`Name` (OQ‑E11‑9)**, **`lastUpdatedOn` (OQ‑E11‑8)**, **no‑NPI (OQ‑E11‑6)**.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E11‑1 — Target org** for deploy/test.
- **OQ‑E11‑2 — Batch‑injection contract (rule).** Confirm `PractitionerBatch` injects `healthcareProviderId` + `caseManagerId` per node so the service does **no SOQL**.
- **OQ‑E11‑3 — `Language` ISO‑code mapping.** Does the payload send a valid `Language` picklist code, or a name (`"English"`) needing **name→code** mapping at batch/intake? *(Required picklist of ISO codes; gates insert + key.)*
- **OQ‑E11‑4 — `Rank` sequencing.** Input order (1‑based) vs primary‑first; must it be unique per practitioner?
- **OQ‑E11‑5 — Dedupe grain.** `{npi}_{language}` one row per practitioner per language — confirm (data test‑polluted).
- **OQ‑E11‑6 — No‑NPI policy.** NPI anchors the key → reject‑at‑intake (recommended) vs a fallback key.
- **OQ‑E11‑8 — `lastUpdatedOn` → `PRM_LastUpdatedByProvider__c`.** Parse format, or default `System.now()` when blank?
- **OQ‑E11‑9 — `Name` source.** `Name` (required) = the `Language` code (per design) vs a display name?

*(Already resolved: org validation done — `IndividualId` polymorphic/Account works, `Language`/`Name`/`Rank` required, `PRM_ShareInPublicDirectory__c` Yes/No, datetime; new unique `PRM_RecordKey__c` decided; NPI‑anchored idempotency; **E11's `PRM_RecordKey__c` is NOT yet created → built as E11 Phase 1**.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | `Language` sent as name, not ISO code → insert fails / wrong key | **High** | High | OQ‑E11‑3; map name→code at batch/intake; T3.4 |
| R‑2 | `PRM_RecordKey__c` field/FLS not present → won't compile/upsert | Medium | High | **field not yet created — Phase 1 (T1.1) creates it before the service** |
| R‑3 | Batch doesn't inject `healthcareProviderId`/`caseManagerId` | Medium | Medium | OQ‑E11‑2; batch injects; service reads params |
| R‑4 | `Rank` order/uniqueness wrong | Low–Med | Medium | OQ‑E11‑4; per‑practitioner sequence; T3.1 |
| R‑5 | Dedupe grain wrong | Low–Med | Medium | OQ‑E11‑5; only `key(...)` changes |
| R‑6 | Service does its own SOQL (violates rule) | Low | Medium | rule check in review; assert 0 SOQL in T3.1 |
| R‑7 | No target org → can't deploy/test | Medium | High | OQ‑E11‑1 |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (esp. OQ‑E11‑3 Language mapping) → 1 (**create the field + FLS**) → 2 (service) → 3 → 4 → 5. Runs **after E2** in `PractitionerBatch`.
- **Effort:** within the ~0.5 d catalog estimate — class + builder + key ~0.25 · tests ~0.2 · evidence/VCS folded in.
- **Depends on:** Epic A + Epic B + E1 + **E2** on `main`, plus `PractitionerBatch`. **Feeds:** nothing downstream consumes E11 (PersonLanguage is a leaf).

---

## 10. What happens after sign‑off

Resolve OQ‑E11‑1…OQ‑E11‑9 — **the `Language` ISO‑code mapping (OQ‑E11‑3) is the gate**. Then: **create + deploy the E11 `PRM_RecordKey__c` field + FLS (Phase 1)** → build the service per **Appendix A** (parse + gate → build + Rank + key → one bulk `upsert` → response) → tests → Test Evidence Report → human sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑E11‑1) and the Language mapping (OQ‑E11‑3) are confirmed.**

---

## Appendix A — Apex class `PRM_LanguageService` (+ meta)

> Full `PRM_LanguageService` (expands `E11…md` §4.2, **rule‑aligned**). **Depends on** `PRM_ServiceBase`. **No SOQL** — `healthcareProviderId` + `caseManagerId` are **batch‑injected** per node (OQ‑E11‑2). `Language` value is assumed a **valid ISO code** (mapped upstream — OQ‑E11‑3). `IndividualId` = the Account Id (polymorphic). Key = `{npi}_{language}`.

```apex
public with sharing class PRM_LanguageService extends PRM_ServiceBase {

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');                          // DELEGATED (context)
        List<Object> practitioners = (List<Object>) params.get('practitioners');   // batch chunk

        // 1) gate + build (NO SOQL — context is batch-injected, per prm-service-class-boundaries)
        List<Map<String, Object>> gated = new List<Map<String, Object>>();   // input order
        List<List<PersonLanguage>> rowsPer = new List<List<PersonLanguage>>();
        List<PersonLanguage> allRows = new List<PersonLanguage>();

        if (practitioners != null) {
            for (Object o : practitioners) {
                Map<String, Object> app = (Map<String, Object>) o;
                List<Object> langs = (List<Object>) app.get('languages');
                if (langs == null || langs.isEmpty()) continue;             // GATED: skip

                Map<String, Object> info = (Map<String, Object>) app.get('practitionerInfo');
                Id accountId = (Id) info.get('id');
                String npi   = (String) info.get('npi');
                Id hcpId     = (Id) app.get('healthcareProviderId');        // batch-injected (rule)
                Id cmId      = (Id) app.get('caseManagerId');               // batch-injected (rule)

                List<PersonLanguage> myRows = new List<PersonLanguage>();
                Integer rank = 1;                                           // per-practitioner sequence (OQ-E11-4)
                for (Object lo : langs) {
                    PersonLanguage pl = buildLanguage((Map<String, Object>) lo, accountId, npi, hcpId, cmId, rank);
                    myRows.add(pl);
                    allRows.add(pl);
                    rank++;
                }
                gated.add(app);
                rowsPer.add(myRows);
            }
        }
        if (allRows.isEmpty()) {
            response = new Map<String, Object>{ 'practitioners' => new List<Object>() };
            return response;
        }

        // 2) ONE bulk upsert by the External Id (idempotent — §7)
        upsert allRows PRM_RecordKey__c;     // populates Id on the same instances held in rowsPer

        // 3) response (input order; gated subset)
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (Integer i = 0; i < gated.size(); i++) {
            List<Id> ids = new List<Id>();
            for (PersonLanguage pl : rowsPer[i]) ids.add(pl.Id);
            Map<String, Object> info = (Map<String, Object>) gated[i].get('practitionerInfo');
            results.add(new Map<String, Object>{
                'accountId'        => info.get('id'),
                'personLanguageIds'=> ids
            });
        }
        response = new Map<String, Object>{ 'practitioners' => results };
        return response;
    }

    // ── builder (pure in-memory; field map per §6; reads batch-injected Ids) ──
    private PersonLanguage buildLanguage(Map<String, Object> l, Id accountId, String npi,
                                         Id hcpId, Id cmId, Integer rank) {
        String lang = (String) l.get('value');         // valid Language ISO code (mapped upstream — OQ-E11-3)

        PersonLanguage pl = new PersonLanguage();
        pl.IndividualId                = accountId;     // polymorphic; Account works (REQUIRED)
        pl.PRM_HealthcareProvider__c   = hcpId;         // batch-injected
        pl.Language                    = lang;          // REQUIRED picklist (ISO code)
        pl.Name                        = lang;          // REQUIRED (Name source — OQ-E11-9)
        pl.Rank                        = rank;          // REQUIRED int (sequence — OQ-E11-4)
        pl.PRM_ShareInPublicDirectory__c = toBool(l.get('shareInDir')) ? 'Yes' : 'No';   // picklist Yes/No
        pl.PRM_LastUpdatedByProvider__c  = parseDateTime((String) l.get('lastUpdatedOn'));  // datetime (OQ-E11-8)
        pl.PRM_CaseManager__c          = cmId;
        pl.PRM_RecordKey__c            = key(new List<String>{ npi, lang });
        return pl;
    }

    // ── helpers (pure) ──
    private String key(List<String> parts) {
        List<String> safe = new List<String>();
        for (String s : parts) safe.add(s == null ? '' : s);   // normalize blanks
        return String.join(safe, '_');                          // '_' delimiter (§2)
    }
    private Boolean toBool(Object o) { return o == null ? false : (Boolean) o; }
    private Datetime parseDateTime(String s) { return String.isBlank(s) ? null : Datetime.parse(s); }   // ⚠ locale — confirm (OQ-E11-8)
}
```

**`PRM_LanguageService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E11_PRM_LanguageService.md` + the `prm-service-class-boundaries` rule. Open items (OQ‑E11‑1…OQ‑E11‑9) still apply — **especially OQ‑E11‑3 (Language ISO‑code mapping).**

---

## Appendix B — Field metadata `PersonLanguage.PRM_RecordKey__c`

> **NEW (E11‑owned).** Path: `force-app/main/default/objects/PersonLanguage/fields/PRM_RecordKey__c.field-meta.xml`. Spec identical to E02's `PRM_RecordKey__c`.

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
    <description>Durable business key (NPI-anchored) for idempotent upsert during async creation (Epic E / E11 — PersonLanguage). Not for other integrations' source keys.</description>
    <inlineHelpText>System-managed dedupe key; do not edit.</inlineHelpText>
</CustomField>
```

---

## Appendix C — Permission‑set FLS (add to `PRM_AsyncJob_Access`)

> **EDIT** the existing Epic A permission set. Path: `force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`.

```xml
<fieldPermissions>
    <field>PersonLanguage.PRM_RecordKey__c</field>
    <readable>true</readable>
    <editable>true</editable>
</fieldPermissions>
```

---

## Appendix D — Apex test class `PRM_LanguageServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`**, modern **`Assert`**, bulk **251+**, `Test.startTest/stopTest`, re‑run/idempotency, and asserts the service does **0 SOQL**. ⚠ **Confirm/add the flagged `PRM_TestDataFactory` builders** (`createPractitionersWithCaseManagers`, `caseManagerByAccount`, `createHealthcareProvidersByNpi`). The test **plays the batch's role** — it injects `healthcareProviderId` + `caseManagerId` per node. `Language` uses a valid **ISO code** (`eng`).

```apex
@isTest
private class PRM_LanguageServiceTest {

    private static final Integer BULK = 251;
    private static final String LANG = 'eng';   // valid Language ISO-code picklist value (OQ-E11-3)

    @TestSetup
    static void setup() {
        PRM_TestDataFactory.createPractitionersWithCaseManagers(BULK, true);
    }

    private static Map<Id, String> npiMap(List<Account> accts) {
        Map<Id, String> m = new Map<Id, String>(); Integer n = 0;
        for (Account a : accts) m.put(a.Id, '50000000' + n++);
        return m;
    }

    // The test injects healthcareProviderId/caseManagerId (the BATCH's job — the service never queries).
    private static Map<String, Object> buildParams(List<Account> accts, Map<Id, Id> cm,
            Map<Id, Id> hcpByAcct, Map<Id, String> npis, Integer langsPer) {
        List<Object> practitioners = new List<Object>();
        for (Account a : accts) {
            List<Object> langs = new List<Object>();
            for (Integer i = 0; i < langsPer; i++) {
                langs.add(new Map<String, Object>{
                    'value' => (i == 0 ? 'eng' : 'spa'),   // distinct ISO codes for multi-language
                    'shareInDir' => true, 'lastUpdatedOn' => ''
                });
            }
            practitioners.add(new Map<String, Object>{
                'practitionerInfo'    => new Map<String, Object>{ 'id' => a.Id, 'npi' => npis.get(a.Id) },
                'healthcareProviderId'=> hcpByAcct.get(a.Id),     // batch-injected
                'caseManagerId'       => cm.get(a.Id),            // batch-injected
                'languages'           => langs
            });
        }
        return new Map<String, Object>{ 'flow' => 'Delegated', 'practitioners' => practitioners };
    }

    @isTest
    static void shouldCreateOneRowPerLanguage_WhenBulk() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, String> npis = npiMap(accts);
        Map<Id, Id> hcp = PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);   // returns AccountId -> hcpId
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = buildParams(accts, cm, hcp, npis, 2);

        Test.startTest();
        Integer before = Limits.getQueries();
        Map<String, Object> resp = (Map<String, Object>) new PRM_LanguageService().execute(params);
        Integer soql = Limits.getQueries() - before;
        Test.stopTest();

        Assert.areEqual(BULK * 2, [SELECT COUNT() FROM PersonLanguage], 'Two languages per practitioner');
        Assert.areEqual(0, soql, 'Service must perform ZERO SOQL (batch injects context)');
        Assert.areEqual(BULK, ((List<Object>) resp.get('practitioners')).size(), 'One response entry per gated practitioner');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        List<Account> accts = [SELECT Id FROM Account];
        Map<Id, String> npis = npiMap(accts);
        Map<Id, Id> hcp = PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = buildParams(accts, cm, hcp, npis, 1);

        Test.startTest();
        new PRM_LanguageService().execute(params);   // first
        new PRM_LanguageService().execute(params);   // re-run (idempotent)
        Test.stopTest();

        Assert.areEqual(BULK, [SELECT COUNT() FROM PersonLanguage], 'Re-run must upsert, not duplicate');
    }

    @isTest
    static void shouldSkip_WhenNoLanguages() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Delegated',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo' => new Map<String, Object>{ 'id' => a.Id, 'npi' => '5999999999' },
                    'languages' => new List<Object>()      // empty -> gated out
                }
            }
        };

        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_LanguageService().execute(params);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM PersonLanguage], 'No rows for a gated-out practitioner');
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(), 'Response excludes gated-out practitioners');
    }

    @isTest
    static void shouldSetRankShareAndKey_WhenBuilt() {
        List<Account> accts = [SELECT Id FROM Account LIMIT 1];
        Map<Id, String> npis = npiMap(accts);
        Map<Id, Id> hcp = PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = buildParams(accts, cm, hcp, npis, 2);

        Test.startTest();
        new PRM_LanguageService().execute(params);
        Test.stopTest();

        List<PersonLanguage> rows = [
            SELECT Language, Name, Rank, PRM_ShareInPublicDirectory__c, PRM_RecordKey__c
            FROM PersonLanguage ORDER BY Rank ASC
        ];
        Assert.areEqual(2, rows.size(), 'Two language rows');
        Assert.areEqual(1, rows[0].Rank, 'First language Rank = 1');
        Assert.areEqual(2, rows[1].Rank, 'Second language Rank = 2');
        Assert.areEqual('Yes', rows[0].PRM_ShareInPublicDirectory__c, 'shareInDir=true -> Yes');
        Assert.isTrue(rows[0].PRM_RecordKey__c.contains('_'), 'Key should be underscore-joined');
    }

    // Language is a required picklist -> an invalid value must fail the insert (OQ-E11-3).
    @isTest
    static void shouldThrow_WhenLanguageInvalid() {
        List<Account> accts = [SELECT Id FROM Account LIMIT 1];
        Map<Id, String> npis = npiMap(accts);
        Map<Id, Id> hcp = PRM_TestDataFactory.createHealthcareProvidersByNpi(npis, true);
        Map<Id, Id> cm = PRM_TestDataFactory.caseManagerByAccount(accts);
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Delegated',
            'practitioners' => new List<Object>{
                new Map<String, Object>{
                    'practitionerInfo'     => new Map<String, Object>{ 'id' => accts[0].Id, 'npi' => npis.get(accts[0].Id) },
                    'healthcareProviderId' => hcp.get(accts[0].Id),
                    'caseManagerId'        => cm.get(accts[0].Id),
                    'languages'            => new List<Object>{ new Map<String, Object>{ 'value' => 'English', 'shareInDir' => true } }  // name, not code
                }
            }
        };

        Test.startTest();
        try {
            new PRM_LanguageService().execute(params);
            Assert.fail('Expected an exception for an invalid Language picklist value');
        } catch (Exception e) {
            Assert.isTrue(e.getMessage().length() > 0, 'Exception should be raised for the invalid Language value');
        }
        Test.stopTest();
    }
}
```

**`PRM_LanguageServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** bulk (251+ × 2 languages → **0 SOQL** + 1 DML), re‑run idempotency, gating (empty `languages`), Rank/share/key correctness, invalid‑`Language` negative. Coverage ≥ 85%. *(Confirm `eng`/`spa` are active `Language` values on the target org.)*

---

## Appendix E — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E11‑1). **Field + FLS first**, then classes, then tests.

```bash
# 1) Phase 1 — deploy the NEW field + permission-set FLS first
sf project deploy start \
  -d "force-app/main/default/objects/PersonLanguage/fields/PRM_RecordKey__c.field-meta.xml" \
  -d "force-app/main/default/permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml" \
  -o <alias>

# 2) Phase 2 — deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_LanguageService.cls" \
  -d "force-app/main/default/classes/PRM_LanguageServiceTest.cls" \
  -o <alias>

# 3) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_LanguageServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 4) Spot-check
sf data query -o <alias> \
  -q "SELECT Id, IndividualId, Language, Rank, PRM_ShareInPublicDirectory__c, PRM_RecordKey__c FROM PersonLanguage ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E11‑3 (`Language` name→ISO code) resolved at batch/intake; valid codes confirmed.
- [ ] OQ‑E11‑2 (batch injects `healthcareProviderId`/`caseManagerId`) confirmed → service stays SOQL‑free.
- [ ] OQ‑E11‑4 (`Rank`) + OQ‑E11‑5 (grain) + OQ‑E11‑8/9 confirmed.
- [ ] Target org confirmed (OQ‑E11‑1).
- [ ] `PRM_TestDataFactory` builders exist or added.
- [ ] Field (Appendix B) + FLS (Appendix C) deploy cleanly as **External Id, Unique**.
- [ ] `PRM_LanguageService` compiles; **0 SOQL** in the service; `upsert … PRM_RecordKey__c` resolves; runs after E2.
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
