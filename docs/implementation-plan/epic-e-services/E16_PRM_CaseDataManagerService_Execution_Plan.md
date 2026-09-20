# E16 · `PRM_CaseDataManagerService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** Self‑contained for **code** generation (see **§0 Component inventory**): Apex class + `.cls-meta.xml` (**Appendix A**), test class + meta (**Appendix B**), deploy/validation commands (**Appendix C**). **No component metadata is generated** here per the request — E16 needs **no new fields** (idempotency uses the existing `PRM_CaseManager__c`), and **[CONFIRMED] FLS for `PRM_CaseDataManager__c` is already granted via an existing permission set** (OQ‑E16‑7) → **no permission‑set change** is required. **Nothing is deployed now** — per direction, **no org/test‑data work this iteration** (OQ‑E16‑4/5 deferred); this remains a code‑level plan for review.
>
> **Source of truth:** `E16_PRM_CaseDataManagerService.md` (design §0–§9, incl. org‑validation on **IBXDEV01** and the complete reference implementation §4.2) + the wired **E20** (`E20_PRM_PractitionerBatch.md`, which supplies E16's outcomes). Anything not stated there is **UNKNOWN** and raised as an Open Question — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]** · **Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PRM_CaseDataManagerService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `force-app/main/default/classes/PRM_CaseDataManagerService.cls` (+ meta) | **NEW** | Appendix A |
| 2 | `PRM_CaseDataManagerServiceTest` | Apex test class | `force-app/main/default/classes/PRM_CaseDataManagerServiceTest.cls` (+ meta) | **NEW** | Appendix B |
| 3 | `PRM_TestDataFactory` builders | Apex test factory (reuse / extend) | `force-app/main/default/classes/PRM_TestDataFactory.cls` | **EDIT if needed (deferred)** | Appendix B note (OQ‑E16‑5) |

> **No new fields, no permission‑set change.** Unlike E02/E05–E11 (which add `PRM_RecordKey__c`), E16's idempotency is **existence‑based on `PRM_CaseManager__c`** — so there is **no field metadata**. **[CONFIRMED] FLS for `PRM_CaseDataManager__c` (identity + flags) is already granted via an existing permission set** (OQ‑E16‑7) → **no `PRM_AsyncJob_Access` edit**. (Design §2, §3.)

> **Conventions (org‑grounded — `salesforce-development` / `generating-apex-test`):** `PRM_` prefix; `with sharing`; one bulk SOQL + one bulk INSERT + one bulk UPDATE; **FLS‑safe** via `Security.stripInaccessible`; **API version 66.0**; test reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class; bulk path tested at scale. **Error handling at the batch level** — the service throws `PRM_CaseDataManagerException` / lets DML exceptions propagate; the Epic C framework (via E20) logs through `PRM_ExceptionLogger` and halts the chain.

---

## 1. Confirmed requirements (from `E16…md` + `E20…md`)

- **[CONFIRMED]** `PRM_CaseDataManagerService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs inside `PractitionerBatch` (seq 1), LAST** (after E2 → E5 → E6 → E19). **Writes:** `PRM_CaseDataManager__c`. (Design §1; E20 §9.)
- **[CONFIRMED]** **Input contract = batch‑supplied outcomes** (not payload presence): `params.practitioners[]` where each element is `{ caseManagerId: Id, created: List<String>, failed: List<String> }`. `created`/`failed` are **record‑type tokens** (§6 vocabulary). (Design §4/§5; E20 `writeCdm`.)
- **[CONFIRMED]** **Output:** `response.practitioners` (input order): `{ caseManagerId, caseDataManagerId }`. (Design §4.)
- **[CONFIRMED]** **Identity = `PRM_CaseManager__c`** (a lookup → **`IndividualApplication`**, **required**, **createable‑only / NOT updateable**). **Exactly one CDM per Case Manager**; under the confirmed **1:1 CM↔practitioner**, that is **one CDM per practitioner**. (Design §1/§2; org‑validated.)
- **[CONFIRMED]** **Idempotency (no `PRM_RecordKey__c`):** one bulk query of existing CDMs by `PRM_CaseManager__c` → reuse (update) or new (insert). (Design §2.)
- **[CONFIRMED]** **64 custom booleans, ALL non‑nillable** (34 record‑type + 30 `*Exception__c`). **INSERT** must set **every** boolean (default `false`, then this batch's flags `true`); **UPDATE** must touch **only** this batch's flags (later batches own the rest). (Design §2/§4.2/§7; org‑validated.)
- **[CONFIRMED]** **Token semantics:** a token in `created[]` → its **flag** `= true`; a token in `failed[]` → its **`*Exception__c`** `= true`. **4 record flags have no exception counterpart** (`PRM_RacialIdentity__c`, `PRM_CultureIdentity__c`, `PRM_HispanicOrigin__c`, `PRM_PersonalPronoun__c`) → a failed token there is a **no‑op**. (Design §2/§6.)
- **[CONFIRMED — OQ‑E16‑2, per‑record granularity]** `created[]`/`failed[]` are **per practitioner** (= per Case Manager, 1:1), so E16 already records **per‑record** exception detail. **⚠ This imposes a dependency on E20 + E2/E5/E6:** they must report **per‑record** outcomes (which specific practitioner's record type failed) — a whole‑call throw that fails the entire chunk is **insufficient** for the required granularity. (See §5 / CL‑E16‑A.)
- **[CONFIRMED]** **FLS already provisioned** — Read+Edit on `PRM_CaseDataManager__c` (identity + flags) is granted via an existing permission set (OQ‑E16‑7); E16 stays FLS‑safe (`stripInaccessible` + identity assert) defensively, but **no permission‑set deliverable**.
- **[CONFIRMED]** **Token→field map is explicit** (`FIELDS_BY_TOKEN`) because record‑flag→exception names are **not** a uniform transform (e.g. `PRM_HealthCareProvider__c`→`PRM_HealthcareProviderException__c`; `PRM_PracticeLocationBundleAssociation__c`→`PRM_BundleAssociationException__c`). Org‑grounded. (Design §6.)
- **[CONFIRMED]** **DML split (not `upsert`):** `PRM_CaseManager__c` is createable‑only, so a single `upsert`/`UPSERTABLE` strip would drop it → **one bulk INSERT (new) + one bulk UPDATE (existing)**. (Design §7.)
- **[CONFIRMED]** **FLS‑safe:** `Security.stripInaccessible` (CREATABLE for inserts, UPDATABLE for updates); identity asserted via `assertIdentityAccessible`. (Design §4.2.)
- **[CONFIRMED — E20‑owned, resolved]** **OQ‑E16‑1 concurrency** — 1:1 model → each CM is a single work‑item; **no grouping / unique constraint** needed; chunk size up to ~10 → up to 10 distinct Case Managers per chunk. (E20 §1/§9/§10.)
- **[CONFIRMED — E20‑owned, resolved]** **OQ‑E16‑3 `PersonAccount`** — E20 `writeCdm()` **always emits the `PersonAccount` token** (Person Account created by E1 at intake) → `PRM_PersonAccount__c` set `true`. (E20 §7/§9.)
- **[CONFIRMED]** **Governor:** 1 bulk SOQL (existing CDMs) + 1 bulk INSERT + 1 bulk UPDATE per chunk — constant regardless of chunk size; `getDescribe()` is cached (no limit cost). (Design §4.2.)
- **[CONFIRMED]** **Effort:** ~1.5 engineer‑days. (Design header.)
- **[CONFIRMED]** **Depends on:** Epic A (base permission set), Epic B (`PRM_ServiceBase`), **E20** (`PractitionerBatch` supplies the `{caseManagerId, created[], failed[]}` outcomes), and the org's existing `PRM_CaseDataManager__c` object + flags.

> **🔎 Org validation (IBXDEV01, re‑verified 2026‑06‑29 — design §2):**
> - `PRM_CaseDataManager__c` exists (~9.9k rows). `Name` = auto‑number (not createable). `PRM_CaseManager__c` = required lookup → `IndividualApplication`, **createable but NOT updateable**.
> - **64 custom booleans, all non‑nillable** (34 record‑type + 30 `*Exception__c`); 4 record flags have no exception counterpart.
> - Record‑flag → exception names are **not** a uniform transform → explicit map required.

---

## 2. Constraints

- **[CONFIRMED]** Runs **inside a batch `execute()` chunk** (E20), **last**; idempotency exists because **manual retry re‑runs the whole batch**. (Design §1/§2; E20 §6.)
- **[CONFIRMED]** **No rollback** on failure (supersedes any savepoint idea): the CDM must persist its `*Exception__c` flags, so E16 always writes. (E20 §6; design §7.)
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected. **FLS is already provisioned via an existing permission set** (OQ‑E16‑7) — no permission‑set change. (Because every flag is non‑nillable, an FLS‑stripped flag on INSERT would `REQUIRED_FIELD_MISSING`; the existing PS prevents this.)
- **[CONFIRMED]** **INSERT sets all 64 booleans; UPDATE touches only this batch's flags** (must not reset later batches' flags). (Design §2/§4.2.)
- **[CONFIRMED]** **Unknown token throws** (`PRM_CaseDataManagerException`) — the batch's vocabulary must match `FIELDS_BY_TOKEN`. (Design §4.2.)
- **[CONFIRMED]** No SOQL/DML in loops — one bulk query + one INSERT + one UPDATE. (Design §4.2/§7.)
- **[CONFIRMED — OQ‑E16‑2]** **Per‑record exception granularity is required.** E16's `failed[]` is per practitioner, so E16 itself is already per‑record. **Dependency (CL‑E16‑A):** E20 + E2/E5/E6 must capture **per‑record** failures (partial‑success DML, e.g. `Database.insert(rows, false)`, mapping each failed record to its practitioner) instead of a whole‑call throw — otherwise the manifest over‑reports. *(This is an E20/service change, outside E16's own code.)*

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `practitioners[]` outcomes; collects `caseManagerId`s; **one bulk query** of existing CDMs; builds **one CDM per Case Manager**; **one INSERT + one UPDATE**.
- **[CONFIRMED]** **INSERT** path: all 64 booleans defaulted `false`, then `created`→flag `true`, `failed`→`*Exception__c` `true`. **UPDATE** path: only this batch's flags changed; other batches' flags untouched.
- **[CONFIRMED]** **Idempotent:** re‑running the same chunk produces **no duplicate CDM** (one per Case Manager); flags are monotonic (a `true` stays `true`).
- **[CONFIRMED]** **`PersonAccount`** flag set `true` (E20 always emits it — OQ‑E16‑3).
- **[CONFIRMED]** **Unknown token** → `PRM_CaseDataManagerException`.
- **[CONFIRMED]** **FLS‑safe**; identity (`PRM_CaseManager__c`) asserted; FLS gap surfaces as a clear error.
- **[CONFIRMED]** Returns per‑practitioner `{ caseManagerId, caseDataManagerId }` (input order; shared `caseDataManagerId` if two outcomes share a CM — defensive).
- **[CONFIRMED]** Apex ≥ 85% incl.: bulk (many distinct CMs); re‑run/idempotency (one CDM after two runs); created→flag + failed→exception; defensive same‑CM token merge; unknown‑token error. Test Evidence Report + human sign‑off (Epic A §A7).
- **[CONFIRMED]** Field API names/types validated against the org (done; re‑confirm on the target org — OQ‑E16‑4).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion. The full class is in **Appendix A**; the full test in **Appendix B**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (CL‑E16‑A, OQ‑E16‑6)
- **T0.1 — Target org / deployment — DEFERRED** (OQ‑E16‑4). Per direction, **no org work this iteration**; plan stays code‑level. Completion: deferred (revisit at build time).
- **T0.2 — Confirm the E20 input contract** (CL).
  - Purpose: E20 supplies `{ caseManagerId, created[], failed[] }` per practitioner with tokens matching `FIELDS_BY_TOKEN`. Outcome: contract confirmed. Dependencies: E20 design (done). Prerequisites: E20 §7/§9. Validation: token list reconciled (§6). Testing: covered by Appendix B. Risks: **[RISK]** token drift between E20 emit and E16 map. Completion: token vocabulary agreed.
- **T0.3 — ✅ Per‑record grain confirmed** (OQ‑E16‑2). Decision: **per‑record** exception detail required. E16 already supports it (per‑practitioner `failed[]`). **Hand‑off (CL‑E16‑A):** E20 + E2/E5/E6 must capture per‑record failures (partial‑success DML) — tracked as an E20/service dependency, **not** an E16 code task. Completion: decision recorded; dependency raised against E20.
- **T0.4 — Test‑data approach for `IndividualApplication` — DEFERRED** (OQ‑E16‑5). Per direction, **nothing created in the org now**; the Appendix B builder (`createCaseManagers`) is specified but not built this iteration. Completion: deferred.
- **T0.5 — Verify dependencies present on `main`:** `PRM_ServiceBase`; `PRM_CaseDataManager__c` object + flags; `PRM_TestDataFactory`. Completion: all present.
- **T0.6 — Confirm later‑batch token ownership is out of scope** (OQ‑E16‑6): this iteration emits only practitioner‑grain tokens (E1/E2/E5/E6 + `PersonAccount`); the rest default `false`. Completion: scope confirmed.

### Phase 1 — Access prerequisite — **NOT REQUIRED** *(M1)*
- **T1.1 — ✅ FLS already provisioned (no action).** Read+Edit on `PRM_CaseDataManager__c` (identity + flags) is granted via an **existing permission set** (OQ‑E16‑7) → **no `PRM_AsyncJob_Access` edit, no metadata to generate**. The service keeps its defensive `stripInaccessible` + identity assert. Completion: confirmed (no deliverable).

### Phase 2 — `PRM_CaseDataManagerService` core *(M2)*
- **T2.1 — Class skeleton + `execute`; parse outcomes**
  - Purpose: parse `practitioners[]` → `Outcome{ caseManagerId, created, failed }`; collect `caseManagerId`s; validate `caseManagerId` present (throw if null). Outcome: Appendix A step 1. Dependencies: T0.2. Impacted: `classes/PRM_CaseDataManagerService.cls`. Validation: compiles; empty input returns empty response. Testing: parse + empty‑input unit. Risks: **[RISK]** missing `caseManagerId`. Completion: parse green.
- **T2.2 — Bulk existence query (idempotency)**
  - Purpose: one SOQL of existing CDMs by `PRM_CaseManager__c` → `Map<Id,PRM_CaseDataManager__c>`. Outcome: Appendix A step 2. Dependencies: T2.1. Validation: 1 SOQL; map keyed by CM. Testing: re‑run test (existing found). Risks: **[RISK]** `WITH SECURITY_ENFORCED` hides rows if read FLS missing (covered by the existing PS — OQ‑E16‑7). Completion: query green.
- **T2.3 — Build/merge one CDM per Case Manager + token application**
  - Purpose: per CM, reuse existing (UPDATE) or new with all‑false init (INSERT); merge tokens of all outcomes under that CM; `applyTokens(created,true)` / `applyTokens(failed,false)`; `initAllFlagsFalse` via cached describe. Outcome: Appendix A step 3 + helpers. Dependencies: T2.2, T0.2 (tokens). Validation: insert record has all 64 set, created→true, failed→exception; update touches only set flags. Testing: insert/update unit; unknown‑token throws; demographics‑no‑exception no‑op. Risks: **[RISK]** token map drift (OQ‑E16‑6); **[RISK]** update accidentally resets flags. Completion: build/merge unit‑tested.
- **T2.4 — Split INSERT/UPDATE (FLS‑safe) + Id mapping + response**
  - Purpose: split by `Id==null`; `stripInaccessible(CREATABLE)`+assert identity+`insert`; `stripInaccessible(UPDATABLE)`+`update`; map new Ids back by `PRM_CaseManager__c`; build per‑practitioner response. Outcome: Appendix A steps 4–5. Dependencies: T2.3. Validation: DML = 1 insert (+1 update on re‑run); response Ids populated. Testing: bulk + re‑run. Risks: **[RISK]** clone‑Id mapping after `stripInaccessible`; **[RISK]** identity stripped (assert catches; FLS pre‑provisioned). Completion: DML + response green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** parse, empty input, build (created→flag, failed→exception), unknown‑token throws, demographics no‑op.
- **T3.2 Bulk/governor:** many distinct Case Managers in one call → 1 SOQL + 1 INSERT; assert limits.
- **T3.3 Idempotency (re‑run):** execute twice → CDM count unchanged (one per CM); flags monotonic.
- **T3.4 Update path:** pre‑existing CDM with some flags true → E16 sets its own flags, leaves others untouched.
- **T3.5 Defensive merge:** two outcomes for the same CM in one call → one CDM, union of tokens.
- **T3.6 PersonAccount:** `created` includes `PersonAccount` → `PRM_PersonAccount__c=true`.
  - Dependencies: Phase 2; test data (OQ‑E16‑5, **deferred** — builds when the org/test‑data step is scheduled). Completion: ≥ 85% coverage; suites green.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7) — *(deferred with deploy)*
- **T4.1 —** Test Evidence Report (coverage + org spot‑check of `PRM_CaseDataManager__c` incl. a re‑run case) + human sign‑off. Risks: **[RISK]** org work deferred (OQ‑E16‑4). Completion: evidence + sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/case-data-manager-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Commit prefix `[E16]`. **No schema and no permission‑set change** lands (no new fields; FLS already provisioned).

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Keep `FIELDS_BY_TOKEN` the single source of the token vocabulary.** E20 emits tokens; E16 maps them. Drift = an unknown‑token exception (fail‑fast, good) but a build‑time annoyance — keep the token list reviewed against E20 `writeCdm`/`collectE2`/`collectE5` (§6, OQ‑E16‑6).
- **[RECOMMENDATION] Initialise‑all‑false via cached describe, not a hardcoded list.** Resilient to org flag additions; cached statically (no limit cost). Trade‑off: it defaults **every** createable custom boolean — confirm none must default `true` (none known). (Design §4.2.)
- **[CONFIRMED] FLS already provisioned (OQ‑E16‑7).** Read+Edit on `PRM_CaseDataManager__c` (identity + flags) is granted via an existing permission set → **no `PRM_AsyncJob_Access` change**. The service keeps `stripInaccessible` + identity assert defensively.
- **[RECOMMENDATION] Don't `upsert`.** Confirmed split INSERT/UPDATE because `PRM_CaseManager__c` is createable‑only. (Design §7.)
- **[CONFIRMED → DEPENDENCY] Per‑record exception grain (OQ‑E16‑2 = CL‑E16‑A).** Business requires per‑record exception detail. E16 already records it (per‑practitioner `failed[]`); the **hard dependency is on E20 + E2/E5/E6** to capture **per‑record** failures (partial‑success DML, `Database.insert(rows, false)` + map each failed row to its practitioner) instead of a whole‑call throw. **This conflicts with a naive halt‑on‑first‑error** in the services — they must collect per‑record results, then E20 builds per‑practitioner `failed[]`, then (per the no‑rollback policy) the step still ends `Failed` to halt the chain. **Raise against E20/E2/E5/E6 design.**
- **[RISK] `IndividualApplication` test data (OQ‑E16‑5) — deferred.** Required fields/record types/validation rules on `IndividualApplication` are **undocumented** → test setup may fail when built. Needs a confirmed `PRM_TestDataFactory` builder (no org work this iteration).

---

## 6. Token → field mapping (org‑grounded) & gaps

**This iteration (E20‑emitted practitioner‑grain tokens):**

| Token | Flag field (`created`→true) | `*Exception__c` (`failed`→true) | Source |
|---|---|---|---|
| `PersonAccount` | `PRM_PersonAccount__c` | `PRM_PersonAccountException__c` | E1 (always emitted — OQ‑E16‑3) |
| `HealthcareProvider` | `PRM_HealthCareProvider__c` | `PRM_HealthcareProviderException__c` | E2 |
| `HealthcareProviderNpi` | `PRM_HealthCareProviderNPI__c` | `PRM_HealthcareProviderNPIException__c` | E2 |
| `Identifier` | `PRM_Identifier__c` | `PRM_IdentifierException__c` | E2 |
| `Taxonomy` | `PRM_HealthCareProviderTaxonomy__c` | `PRM_HealthcareProviderTaxonomyException__c` | E2 |
| `BusinessLicense` | `PRM_BusinessLicense__c` | `PRM_BusinessLicenseException__c` | E5 |
| `PersonEducation` | `PRM_PersonEducation__c` | `PRM_PersonEducationException__c` | E6 |

> Full vocabulary (incl. deferred E7/E8/E10/E11 + later‑batch tokens, and the 4 demographics flags with **no** exception) is in design §6 / Appendix A `FIELDS_BY_TOKEN`.

**Gaps & hidden dependencies**
- **[DEPENDENCY — CL‑E16‑A] Per‑record failure capture (OQ‑E16‑2, confirmed).** E20 + E2/E5/E6 must report per‑record failures so E16's per‑practitioner `failed[]` is accurate. **Not an E16 code task** — raised against E20/services.
- **[OPEN] OQ‑E16‑6** later‑batch token ownership (out of scope this iteration; vocabulary present, emit lives in each batch).
- **[DEFERRED] OQ‑E16‑4** target org / deploy — no org work this iteration.
- **[DEFERRED] OQ‑E16‑5** `IndividualApplication` test‑data builder — not built this iteration.
- **[DEPENDENCY]** E20 must supply the outcomes contract with matching tokens (T0.2) and **always emit `PersonAccount`** (resolved, E20 §7).
- **[RESOLVED] OQ‑E16‑7** FLS — already provisioned via an existing permission set.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑E16‑6 — Later‑batch token ownership.** Confirm this iteration emits only practitioner‑grain tokens (+`PersonAccount`); the rest default `false` and are owned by later batches.
- **CL‑E16‑A (dependency, not E16 code) — Per‑record failure capture.** Confirmed per‑record grain (OQ‑E16‑2) requires **E20 + E2/E5/E6** to report per‑record failures (partial‑success DML) so each practitioner's `failed[]` is accurate. Raise/track against the E20 + service designs.

*(Resolved/decided: **OQ‑E16‑1** concurrency — 1:1 model, no grouping (E20); **OQ‑E16‑2** — **per‑record grain required** → E16 already supports it; dependency CL‑E16‑A on E20/services; **OQ‑E16‑3** `PersonAccount` always emitted (E20); **OQ‑E16‑7** FLS already provisioned via an existing PS (no change); org validation done — object/identity/64 booleans; idempotency = existence on `PRM_CaseManager__c`; **no `PRM_RecordKey__c`/no new field**; split INSERT/UPDATE; input contract = batch outcomes. **Deferred (no org work now):** **OQ‑E16‑4** target org, **OQ‑E16‑5** `IndividualApplication` test‑data builder.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | FLS strips a non‑nillable boolean on INSERT → `REQUIRED_FIELD_MISSING` | **Low** | High | **FLS pre‑provisioned via existing PS (OQ‑E16‑7)**; defensive `assertIdentityAccessible` |
| R‑2 | Token drift between E20 emit and E16 `FIELDS_BY_TOKEN` → unknown‑token exception | Medium | Medium | T0.2 reconcile; fail‑fast exception; T3.1 unknown‑token test |
| R‑3 | UPDATE path accidentally resets other batches' flags | Low | High | UPDATE touches only this batch's flags; T3.4 update test |
| R‑4 | **Per‑record failures not captured by E20/services** → manifest over‑reports exceptions | **Medium** | **High** | **CL‑E16‑A** — E20+E2/E5/E6 partial‑success DML + per‑practitioner mapping (per‑record grain required) |
| R‑5 | Clone‑Id mapping after `stripInaccessible(CREATABLE)` wrong | Low | Medium | Map by `PRM_CaseManager__c` (createable, retained); T3.2 asserts response Ids |
| R‑6 | `IndividualApplication` test data fails (undocumented required fields) | Medium | Medium | OQ‑E16‑5 (deferred); confirmed factory builder when scheduled |
| R‑7 | Identity `PRM_CaseManager__c` stripped (createable‑only / FLS) | Low | High | `assertIdentityAccessible` throws; FLS pre‑provisioned |
| R‑8 | Concurrency duplicate CDM | **Low** | Medium | **Resolved** by 1:1 (E20, OQ‑E16‑1); unique constraint optional |

---

## 9. Sequencing & effort

- **Order:** Phase 0 (confirm CL‑E16‑A + OQ‑E16‑6) → 1 (**no‑op — FLS already provisioned**) → 2 (service) → 3 → 4/5 *(deploy/evidence deferred — no org work now)*. Runs **last** in `PractitionerBatch` `execute()` (after E2/E5/E6/E19).
- **Effort:** within the ~1.5 d catalog estimate — class + token map + insert/update ~0.7 · tests ~0.5 · evidence/VCS folded in. *(Excludes the E20/service per‑record‑failure change, CL‑E16‑A, which is separate.)*
- **Depends on:** Epic A + Epic B + **E20** (supplies outcomes, incl. per‑record `failed[]` — CL‑E16‑A) on `main`. **Feeds:** the CDM manifest is consumed downstream by reporting/ops (not by other services this iteration).

---

## 10. What happens after sign‑off

Confirm **OQ‑E16‑6** and raise **CL‑E16‑A** (per‑record failure capture) against E20/E2/E5/E6. Then build the service per **Appendix A** (parse outcomes → existence query → build/merge one CDM per CM with all‑false init + token application → split INSERT/UPDATE FLS‑safe → response). **FLS is already provisioned (OQ‑E16‑7) — no permission‑set step.** Tests (**Appendix B**), Test Evidence Report, and human sign‑off (A7) follow when the org/test‑data step is scheduled — **deferred this iteration (OQ‑E16‑4/5); no org work now.**

---

## Appendix A — Apex class `PRM_CaseDataManagerService` (+ meta)

> Full class (mirrors `E16…md` §4.2). **Depends on** `PRM_ServiceBase`. Idempotent by existence on `PRM_CaseManager__c`; INSERT defaults all 64 booleans `false`; UPDATE touches only this batch's flags; FLS‑safe; split INSERT/UPDATE. `FIELDS_BY_TOKEN` is org‑grounded — keep in sync with E20's emitted tokens (OQ‑E16‑6).

```apex
public with sharing class PRM_CaseDataManagerService extends PRM_ServiceBase {
    private static final String CDM_OBJECT = 'PRM_CaseDataManager__c';
    private static final String FIELD_CASE_MANAGER = 'PRM_CaseManager__c';

    public class PRM_CaseDataManagerException extends Exception {}

    private class FlagFields {
        String flag;
        String exception;
        FlagFields(String flag, String exception) {
            this.flag = flag;
            this.exception = exception;
        }
    }

    // Token -> (flag field, *Exception__c field|null). Org-grounded (IBXDEV01). Keep in sync with E20 emitted tokens.
    private static final Map<String, FlagFields> FIELDS_BY_TOKEN = new Map<String, FlagFields>{
        // ── PractitionerBatch (seq 1) — practitioner-grain (E1/E2/E5/E6/E7/E8/E10/E11) ──
        'PersonAccount'          => new FlagFields('PRM_PersonAccount__c',                  'PRM_PersonAccountException__c'),
        'Account'                => new FlagFields('PRM_Account__c',                        'PRM_AccountException__c'),
        'HealthcareProvider'     => new FlagFields('PRM_HealthCareProvider__c',            'PRM_HealthcareProviderException__c'),
        'HealthcareProviderNpi'  => new FlagFields('PRM_HealthCareProviderNPI__c',         'PRM_HealthcareProviderNPIException__c'),
        'Identifier'             => new FlagFields('PRM_Identifier__c',                     'PRM_IdentifierException__c'),
        'Taxonomy'               => new FlagFields('PRM_HealthCareProviderTaxonomy__c',     'PRM_HealthcareProviderTaxonomyException__c'),
        'BusinessLicense'        => new FlagFields('PRM_BusinessLicense__c',                'PRM_BusinessLicenseException__c'),
        'PersonEducation'        => new FlagFields('PRM_PersonEducation__c',                'PRM_PersonEducationException__c'),
        'BoardCertification'     => new FlagFields('PRM_BoardCertification__c',             'PRM_BoardCertificationException__c'),
        'InfoCodeAssignment'     => new FlagFields('PRM_InfoCodeAssignment__c',             'PRM_InfoCodeAssignmentException__c'),
        'ContactProfile'         => new FlagFields('PRM_ContactProfile__c',                 'PRM_ContactProfileException__c'),
        'PersonLanguage'         => new FlagFields('PRM_PersonLanguage__c',                 'PRM_PersonLanguageException__c'),
        // demographics sub-flags (E10) — no exception counterpart in the org
        'RacialIdentity'         => new FlagFields('PRM_RacialIdentity__c',                 null),
        'CultureIdentity'        => new FlagFields('PRM_CultureIdentity__c',                null),
        'HispanicOrigin'         => new FlagFields('PRM_HispanicOrigin__c',                 null),
        'PersonalPronoun'        => new FlagFields('PRM_PersonalPronoun__c',                null),
        // ── later batches (PracticeLocationAndGroupBatch / PLRelated / Level4) — vocabulary for reuse ──
        'ProviderFeature'                   => new FlagFields('PRM_ProviderFeature__c',                  'PRM_ProviderFeatureException__c'),
        'HealthcareFacilityNetwork'         => new FlagFields('PRM_HealthcareFacilityNetwork__c',        'PRM_HealthcareFacilityNetworkException__c'),
        'HealthCarePractitionerFacility'    => new FlagFields('PRM_HealthCarePractitionerFacility__c',   'PRM_HCPractitionerFacilityException__c'),
        'HealthCareFacility'                => new FlagFields('PRM_HealthCareFacility__c',               'PRM_HealthcareFacilityException__c'),
        'Location'                          => new FlagFields('PRM_Location__c',                         'PRM_LocationException__c'),
        'LocationNPIHistory'                => new FlagFields('PRM_LocationNPIHistory__c',               'PRM_LocationNPIHistoryException__c'),
        'Address'                           => new FlagFields('PRM_Address__c',                          'PRM_AddressException__c'),
        'AlternativeContactMethod'          => new FlagFields('PRM_AlternativeContactMethod__c',         'PRM_AlternativeContactMethodException__c'),
        'OperatingHours'                    => new FlagFields('PRM_OperatingHours__c',                   'PRM_OperatingHoursException__c'),
        'TimeSlot'                          => new FlagFields('PRM_TimeSlot__c',                         'PRM_TimeSlotException__c'),
        'ContentVersion'                    => new FlagFields('PRM_ContentVersion__c',                   'PRM_ContentVersionException__c'),
        'ProgramParticipation'              => new FlagFields('PRM_ProgramParticipation__c',             'PRM_ProgramParticipationException__c'),
        'PracticeLocationAssociation'       => new FlagFields('PRM_PracticeLocationAssociation__c',      'PRM_PracticeLocationAssociationException__c'),
        'PracticeLocationBundle'            => new FlagFields('PRM_PracticeLocationBundle__c',           'PRM_PracticeLocationBundleException__c'),
        'PracticeLocationBundleAssociation' => new FlagFields('PRM_PracticeLocationBundleAssociation__c','PRM_BundleAssociationException__c'),
        'AccountContractEntity'             => new FlagFields('PRM_AccountContractEntity__c',            'PRM_AccountContractEntityException__c'),
        'AccountToAccountRelationship'      => new FlagFields('PRM_AccountToAccountRelationship__c',     'PRM_AccountAccountRelationshipException__c'),
        'ContractHierarchy'                 => new FlagFields('PRM_ContractHierarchy__c',                'PRM_ContractHierarchyException__c')
    };

    private static List<String> allBooleanFlagFieldsCache;

    private class Outcome {
        Id caseManagerId;
        Set<String> created;
        Set<String> failed;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'practitioners' => new List<Map<String, Object>>() };
        List<Object> practitioners = (params == null) ? null : (List<Object>) params.get('practitioners');
        if (practitioners == null || practitioners.isEmpty()) {
            return response;
        }

        // 1) parse outcomes; collect caseManagerIds (no SOQL/DML in loop)
        List<Outcome> outcomes = new List<Outcome>();
        Set<Id> caseManagerIds = new Set<Id>();
        for (Object practitionerObject : practitioners) {
            Map<String, Object> node = (Map<String, Object>) practitionerObject;
            Id caseManagerId = (Id) node.get('caseManagerId');
            if (caseManagerId == null) {
                throw new PRM_CaseDataManagerException('CDM: caseManagerId is required for every practitioner');
            }
            Outcome outcome = new Outcome();
            outcome.caseManagerId = caseManagerId;
            outcome.created = toStringSet(node.get('created'));
            outcome.failed = toStringSet(node.get('failed'));
            outcomes.add(outcome);
            caseManagerIds.add(caseManagerId);
        }

        // 2) ONE bulk query: existing CDMs by Case Manager
        Map<Id, PRM_CaseDataManager__c> existingByCaseManager = new Map<Id, PRM_CaseDataManager__c>();
        for (PRM_CaseDataManager__c existing : [
            SELECT Id, PRM_CaseManager__c
            FROM PRM_CaseDataManager__c
            WHERE PRM_CaseManager__c IN :caseManagerIds
            WITH SECURITY_ENFORCED
        ]) {
            existingByCaseManager.put(existing.PRM_CaseManager__c, existing);
        }

        // 3) build/merge ONE CDM per Case Manager (tokens of all practitioners of that CM merge in)
        Map<Id, PRM_CaseDataManager__c> workingByCaseManager = new Map<Id, PRM_CaseDataManager__c>();
        for (Outcome outcome : outcomes) {
            PRM_CaseDataManager__c cdm = workingByCaseManager.get(outcome.caseManagerId);
            if (cdm == null) {
                PRM_CaseDataManager__c existing = existingByCaseManager.get(outcome.caseManagerId);
                if (existing != null) {
                    cdm = existing;                                  // UPDATE — do NOT touch other batches' flags
                } else {
                    cdm = new PRM_CaseDataManager__c(PRM_CaseManager__c = outcome.caseManagerId);
                    initAllFlagsFalse(cdm);                         // INSERT — every non-nillable boolean must be set
                }
                workingByCaseManager.put(outcome.caseManagerId, cdm);
            }
            applyTokens(cdm, outcome.created, true);                // created -> flag = true
            applyTokens(cdm, outcome.failed, false);               // failed  -> *Exception__c = true
        }

        // 4) split + FLS-safe DML (PRM_CaseManager__c is createable-only -> cannot go through an UPDATABLE strip)
        List<PRM_CaseDataManager__c> toInsert = new List<PRM_CaseDataManager__c>();
        List<PRM_CaseDataManager__c> toUpdate = new List<PRM_CaseDataManager__c>();
        for (PRM_CaseDataManager__c cdm : workingByCaseManager.values()) {
            if (cdm.Id == null) {
                toInsert.add(cdm);
            } else {
                toUpdate.add(cdm);
            }
        }
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            assertIdentityAccessible(decision);
            List<SObject> safeRows = decision.getRecords();
            insert safeRows;
            for (SObject safeRow : safeRows) {                      // map new Ids back onto the working records
                PRM_CaseDataManager__c saved = (PRM_CaseDataManager__c) safeRow;
                workingByCaseManager.get(saved.PRM_CaseManager__c).Id = saved.Id;
            }
        }
        if (!toUpdate.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.UPDATABLE, toUpdate);
            update decision.getRecords();
        }

        // 5) response in input order
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (Outcome outcome : outcomes) {
            results.add(new Map<String, Object>{
                'caseManagerId' => outcome.caseManagerId,
                'caseDataManagerId' => workingByCaseManager.get(outcome.caseManagerId).Id
            });
        }
        response.put('practitioners', results);
        return response;
    }

    /** created -> flag true; failed -> *Exception__c true (no-op when the token has no exception field). */
    private void applyTokens(PRM_CaseDataManager__c cdm, Set<String> tokens, Boolean isCreated) {
        for (String token : tokens) {
            FlagFields flagFields = FIELDS_BY_TOKEN.get(token);
            if (flagFields == null) {
                throw new PRM_CaseDataManagerException('CDM: unknown record-type token "' + token + '"');
            }
            if (isCreated) {
                cdm.put(flagFields.flag, true);
            } else if (flagFields.exception != null) {
                cdm.put(flagFields.exception, true);
            }
        }
    }

    /** INSERT only: every non-nillable custom boolean must carry a value. */
    private void initAllFlagsFalse(PRM_CaseDataManager__c cdm) {
        for (String apiName : allBooleanFlagFields()) {
            cdm.put(apiName, false);
        }
    }

    /** Cached describe of every createable custom boolean on the object. */
    private static List<String> allBooleanFlagFields() {
        if (allBooleanFlagFieldsCache == null) {
            allBooleanFlagFieldsCache = new List<String>();
            Map<String, Schema.SObjectField> fieldMap = PRM_CaseDataManager__c.SObjectType.getDescribe().fields.getMap();
            for (Schema.SObjectField field : fieldMap.values()) {
                Schema.DescribeFieldResult fieldDescribe = field.getDescribe();
                if (fieldDescribe.getType() == Schema.DisplayType.BOOLEAN
                    && fieldDescribe.isCustom()
                    && fieldDescribe.isCreateable()) {
                    allBooleanFlagFieldsCache.add(fieldDescribe.getName());
                }
            }
        }
        return allBooleanFlagFieldsCache;
    }

    /** Fail loudly if FLS stripped the identity lookup rather than silently inserting an orphan manifest. */
    private void assertIdentityAccessible(SObjectAccessDecision decision) {
        Set<String> removedFields = decision.getRemovedFields().get(CDM_OBJECT);
        if (removedFields != null && removedFields.contains(FIELD_CASE_MANAGER)) {
            throw new PRM_CaseDataManagerException(
                'CDM: insufficient field access (FLS) for "' + FIELD_CASE_MANAGER + '" - grant it via PRM_AsyncJob_Access'
            );
        }
    }

    private Set<String> toStringSet(Object listObject) {
        Set<String> values = new Set<String>();
        if (listObject == null) {
            return values;
        }
        for (Object item : (List<Object>) listObject) {
            if (item != null) {
                values.add(String.valueOf(item));
            }
        }
        return values;
    }
}
```

**`PRM_CaseDataManagerService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E16_PRM_CaseDataManagerService.md`. Open items (OQ‑E16‑2/4/5/6/7) still apply.

---

## Appendix B — Apex test class `PRM_CaseDataManagerServiceTest` (+ meta)

> Reuses **`PRM_TestDataFactory`** + the modern **`Assert`** class. The test **plays E20's role** — it builds `{ caseManagerId, created[], failed[] }` outcomes. **⚠ `IndividualApplication` (Case Manager) test data is undocumented (OQ‑E16‑5)** — the flagged builder **`PRM_TestDataFactory.createCaseManagers(n)`** must exist or be added (returns `List<IndividualApplication>`). Assertions use the org‑grounded flag/exception field names (§6).

```apex
@isTest
private class PRM_CaseDataManagerServiceTest {

    private static final Integer BULK = 200;   // distinct Case Managers per chunk (1:1) — tune to factory limits

    @TestSetup
    static void setup() {
        // ⚠ OQ-E16-5: confirm/extend PRM_TestDataFactory with a Case Manager (IndividualApplication) builder.
        PRM_TestDataFactory.createCaseManagers(BULK);
    }

    private static Map<String, Object> outcome(Id caseManagerId, List<String> created, List<String> failed) {
        return new Map<String, Object>{
            'caseManagerId' => caseManagerId,
            'created' => created,
            'failed'  => failed
        };
    }

    private static Map<String, Object> params(List<Object> practitioners) {
        return new Map<String, Object>{ 'flow' => 'Practitioner Creation', 'practitioners' => practitioners };
    }

    @isTest
    static void shouldInsertOneCdmPerCaseManager_WhenBulk() {
        List<IndividualApplication> cms = [SELECT Id FROM IndividualApplication];
        List<Object> outcomes = new List<Object>();
        for (IndividualApplication cm : cms) {
            outcomes.add(outcome(cm.Id,
                new List<String>{ 'PersonAccount', 'HealthcareProvider', 'HealthcareProviderNpi', 'Identifier', 'Taxonomy' },
                new List<String>()));
        }

        Test.startTest();
        Integer soqlBefore = Limits.getQueries();
        Map<String, Object> resp = (Map<String, Object>) new PRM_CaseDataManagerService().execute(params(outcomes));
        Integer soql = Limits.getQueries() - soqlBefore;
        Test.stopTest();

        Assert.areEqual(cms.size(), [SELECT COUNT() FROM PRM_CaseDataManager__c], 'One CDM per Case Manager');
        Assert.areEqual(1, soql, 'Exactly one existence query');
        Assert.areEqual(cms.size(), ((List<Object>) resp.get('practitioners')).size(), 'One response entry per outcome');
    }

    @isTest
    static void shouldSetCreatedFlagsAndExceptionFlags_WhenBuilt() {
        IndividualApplication cm = [SELECT Id FROM IndividualApplication LIMIT 1];
        List<Object> outcomes = new List<Object>{
            outcome(cm.Id,
                new List<String>{ 'PersonAccount', 'HealthcareProvider', 'Identifier' },
                new List<String>{ 'BusinessLicense' })
        };

        Test.startTest();
        new PRM_CaseDataManagerService().execute(params(outcomes));
        Test.stopTest();

        PRM_CaseDataManager__c cdm = [
            SELECT PRM_PersonAccount__c, PRM_HealthCareProvider__c, PRM_Identifier__c,
                   PRM_BusinessLicense__c, PRM_BusinessLicenseException__c, PRM_Taxonomy__c
            FROM PRM_CaseDataManager__c WHERE PRM_CaseManager__c = :cm.Id
        ];
        Assert.isTrue(cdm.PRM_PersonAccount__c, 'PersonAccount created -> true');
        Assert.isTrue(cdm.PRM_HealthCareProvider__c, 'HealthcareProvider created -> true');
        Assert.isTrue(cdm.PRM_Identifier__c, 'Identifier created -> true');
        Assert.isFalse(cdm.PRM_BusinessLicense__c, 'BusinessLicense not created -> false');
        Assert.isTrue(cdm.PRM_BusinessLicenseException__c, 'BusinessLicense failed -> exception true');
    }

    @isTest
    static void shouldNotDuplicate_WhenReRun() {
        IndividualApplication cm = [SELECT Id FROM IndividualApplication LIMIT 1];
        List<Object> outcomes = new List<Object>{
            outcome(cm.Id, new List<String>{ 'PersonAccount', 'HealthcareProvider' }, new List<String>())
        };

        Test.startTest();
        new PRM_CaseDataManagerService().execute(params(outcomes));   // first  -> insert
        new PRM_CaseDataManagerService().execute(params(outcomes));   // re-run -> update
        Test.stopTest();

        Assert.areEqual(1, [SELECT COUNT() FROM PRM_CaseDataManager__c WHERE PRM_CaseManager__c = :cm.Id],
            'Re-run must update the same CDM, not duplicate');
    }

    @isTest
    static void shouldPreserveOtherFlags_WhenUpdating() {
        IndividualApplication cm = [SELECT Id FROM IndividualApplication LIMIT 1];
        // first run sets HealthcareProvider; second run (a "later batch" token) must not reset it
        new PRM_CaseDataManagerService().execute(params(new List<Object>{
            outcome(cm.Id, new List<String>{ 'HealthcareProvider' }, new List<String>()) }));

        Test.startTest();
        new PRM_CaseDataManagerService().execute(params(new List<Object>{
            outcome(cm.Id, new List<String>{ 'Location' }, new List<String>()) }));
        Test.stopTest();

        PRM_CaseDataManager__c cdm = [
            SELECT PRM_HealthCareProvider__c, PRM_Location__c
            FROM PRM_CaseDataManager__c WHERE PRM_CaseManager__c = :cm.Id
        ];
        Assert.isTrue(cdm.PRM_HealthCareProvider__c, 'Existing flag preserved on update');
        Assert.isTrue(cdm.PRM_Location__c, 'New flag set on update');
    }

    @isTest
    static void shouldThrow_WhenUnknownToken() {
        IndividualApplication cm = [SELECT Id FROM IndividualApplication LIMIT 1];
        List<Object> outcomes = new List<Object>{
            outcome(cm.Id, new List<String>{ 'NotARealToken' }, new List<String>())
        };

        Test.startTest();
        try {
            new PRM_CaseDataManagerService().execute(params(outcomes));
            Assert.fail('Expected an exception for an unknown token');
        } catch (PRM_CaseDataManagerService.PRM_CaseDataManagerException e) {
            Assert.isTrue(e.getMessage().contains('unknown record-type token'), 'Clear unknown-token error');
        }
        Test.stopTest();
    }

    @isTest
    static void shouldThrow_WhenCaseManagerMissing() {
        List<Object> outcomes = new List<Object>{
            new Map<String, Object>{ 'created' => new List<String>{ 'PersonAccount' }, 'failed' => new List<String>() }
        };

        Test.startTest();
        try {
            new PRM_CaseDataManagerService().execute(params(outcomes));
            Assert.fail('Expected an exception for a missing caseManagerId');
        } catch (PRM_CaseDataManagerService.PRM_CaseDataManagerException e) {
            Assert.isTrue(e.getMessage().contains('caseManagerId is required'), 'Clear missing-identity error');
        }
        Test.stopTest();
    }

    @isTest
    static void shouldReturnEmpty_WhenNoPractitioners() {
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_CaseDataManagerService()
            .execute(params(new List<Object>()));
        Test.stopTest();
        Assert.areEqual(0, ((List<Object>) resp.get('practitioners')).size(), 'Empty input -> empty response');
    }
}
```

**`PRM_CaseDataManagerServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **⚠ Test‑data caveats (Pending Clarification):**
> - **OQ‑E16‑5 (deferred — no org work this iteration):** `PRM_TestDataFactory.createCaseManagers(n)` (returns `IndividualApplication[]`) is **assumed** — confirm/add it (required fields/record type unknown) when the build/test step is scheduled.
> - The `PRM_Taxonomy__c` field in the first assertion query is illustrative — **replace with the actual taxonomy flag** `PRM_HealthCareProviderTaxonomy__c` when finalising (kept here only to flag the field‑name check).
> - **FLS‑strip negative test** is intentionally omitted (hard to simulate without a second running user/permission context) — covered operationally by T1.1 + `assertIdentityAccessible`.

---

## Appendix C — Deployment & validation (commands)

> **Deploy is deferred this iteration (no org work — OQ‑E16‑4/5).** When scheduled: run against the confirmed org. **No field metadata and no permission‑set step** — E16 adds no fields and **FLS is already provisioned via an existing PS (OQ‑E16‑7)**. Deploy classes, then tests.

```bash
# 1) Phase 2 — deploy the service + test class (FLS from T1.1 must already be in place)
sf project deploy start \
  -d "force-app/main/default/classes/PRM_CaseDataManagerService.cls" \
  -d "force-app/main/default/classes/PRM_CaseDataManagerServiceTest.cls" \
  -o <alias>

# 2) Phase 3 — run tests with coverage
sf apex run test --class-names PRM_CaseDataManagerServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 3) Spot-check a CDM (existence-based idempotency)
sf data query -o <alias> \
  -q "SELECT Id, PRM_CaseManager__c, PRM_PersonAccount__c, PRM_HealthCareProvider__c, PRM_Identifier__c, PRM_BusinessLicense__c, PRM_BusinessLicenseException__c FROM PRM_CaseDataManager__c ORDER BY LastModifiedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist (when deploy is scheduled):**

- [x] OQ‑E16‑2 — **per‑record grain decided**; CL‑E16‑A raised against E20/E2/E5/E6 (their deliverable).
- [x] OQ‑E16‑7 — **FLS already provisioned** via an existing PS (no permission‑set step).
- [ ] OQ‑E16‑6 (later‑batch token ownership out of scope) confirmed.
- [ ] CL‑E16‑A — E20 + E2/E5/E6 capture **per‑record** failures so each practitioner's `failed[]` is accurate.
- [ ] E20 supplies the `{ caseManagerId, created[], failed[] }` contract with tokens matching `FIELDS_BY_TOKEN` (incl. always `PersonAccount`).
- [ ] `PRM_CaseDataManagerService` compiles; 1 SOQL + 1 INSERT + 1 UPDATE per chunk; INSERT sets all 64 booleans; UPDATE preserves other flags.
- [ ] *(Deferred)* Target org (OQ‑E16‑4) + `IndividualApplication` test‑data builder (OQ‑E16‑5).
- [ ] Tests green, coverage ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
