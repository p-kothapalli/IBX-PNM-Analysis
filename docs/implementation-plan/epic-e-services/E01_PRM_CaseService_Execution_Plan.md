# E01 · `PRM_CaseService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan includes the **complete reference implementation** of `PRM_CaseService` (**Appendix A**, mirroring `E01_PRM_CaseService.md` §2.2 — full `execute` + builders + formula/parse helpers + the §3f CMA invocation). **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered, and the target org (OQ‑6) is confirmed.
>
> **Source of truth:** `E01_PRM_CaseService.md` (design + §8 Validation Log F‑1…F‑11). This plan restates/expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and raised as an Open Question — not assumed.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]**. Tasks blocked by an unresolved [OPEN] item are **⛔ Pending Clarification**.

---

## 1. Confirmed requirements (from `E01_PRM_CaseService.md`)

- **[CONFIRMED]** `PRM_CaseService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`. **Runs at synchronous intake** (the "Case Manager Service"), **not** in a batch.
- **[CONFIRMED]** **Bulk**: input `params.jsonInput` = `{ "applications": [ { caseManagerInfo, practitionerInfo }, … ] }` (+ `params.flow`). Processes **N practitioners per submission** in one call; creates **one Account + Case + IndividualApplication (= Case Manager) per practitioner**.
- **[CONFIRMED]** **Writes** (org‑verified, IBXDEV01): `Account` (RT `PRM_Practitioner`), `Case` (RT `PRM_PRM`), `IndividualApplication` (RT per PNC/flow). `IndividualApplication.AppliedDate` is **Datetime**; `Stage` → **`PRM_Stage__c`**; `Account.PRM_DelegatedOnly__c` is a **Boolean**; required booleans default `false` via `toBool`.
- **[CONFIRMED]** **DML / order** (5 statements, constant regardless of N): Account insert → IA insert (FK Account) → Case insert (FK Account + IA) → IA update (`ApplicationCaseId`) → Account update (`PRM_CaseManager__c`). Per‑application correlation via the **`AppUow` reference wrapper**; back‑links are schema‑nullable (valid order).
- **[CONFIRMED]** **CMA (§3f/§5.1):** after the records, E1 invokes **`PRM_CMAService`** to create the **Practitioner CMA** (`recordType='PRM_Practitioner'`, `PRM_Account__c`=created Account, `caseManagerId`=IA Id), **bulk, in the same intake transaction** (idempotent pre‑check). E1 creates **only** the Practitioner CMA.
- **[CONFIRMED]** **Return:** per practitioner `{ practitionerAccountId, caseId, caseManagerId }` (input order) + flat `caseManagerIds`. The wrapper uses **AccountId + CaseManagerId** to create `PRM_AsyncJob__c` + `PRM_AsyncJobRecords__c` and to **enrich the stored payload** (so batches' `practitionerInfo.id` = the E1 Account Id). **PersonContactId not returned** (E2 resolves it).
- **[CONFIRMED]** **Formulas in‑service:** `caseType`, `CredentialingStatusVal`, gender (`PersonGenderIdentity`/`Pc`), `AppliedDate=System.now()`, IA RT rule; record types via cached **`PRM_FormSubUtility.recordTypeId`**; names via `PRM_FormSubUtility.NameNormalize`.
- **[CONFIRMED]** **Decisions:** `flowType` = `params.flow` authoritative (fallback `caseManagerInfo.flowType`); `Category` always supplied (validator‑guaranteed); intake = **all‑or‑nothing**; **existing‑practitioner path deferred** (always insert new Account).
- **[CONFIRMED]** **Effort:** ~2.5 engineer‑days (Plan §8). **Depends on:** EPIC B (`PRM_ServiceBase`, `PRM_FormSubUtility` incl. `recordTypeId`), **`PRM_CMAService` (E19)**, EPIC A objects/RTs. **Invoked by:** EPIC F intake wrapper.

---

## 2. Constraints

- **[CONFIRMED]** No DML/SOQL/describe in loops; RT Ids cached once; one bulk DML per object type.
- **[CONFIRMED]** Runs in the **synchronous intake transaction** — CMA + records share atomicity (all‑or‑nothing).
- **[CONFIRMED]** Circular FK handled by insert‑then‑back‑link; back‑link fields must be nullable at insert (org‑verified).
- **[CONFIRMED]** `with sharing`; CRUD/FLS respected (intake user / permission set).
- **[CONFIRMED]** No new fields/objects (uses existing Account/Case/IndividualApplication + CMA).

---

## 3. Acceptance criteria

- **[CONFIRMED]** Parses `applications[]`; creates the 3 records per practitioner with correct field maps + formulas; **5 DML** regardless of N.
- **[CONFIRMED]** Invokes `PRM_CMAService` → one Practitioner CMA per practitioner (Account ↔ Case Manager); no duplicate on re‑submit (CMA pre‑check).
- **[CONFIRMED]** Returns per‑practitioner AccountId + CaseManagerId (+ flat list) in input order.
- **[CONFIRMED]** Intake is atomic (any bad row / CMA failure rolls back the whole submission).
- **[CONFIRMED]** Apex ≥ 85% incl. a **bulk** test (e.g. 200 applications) asserting governor‑safe DML counts **and** the Practitioner CMA rows; Test Evidence Report + human sign‑off (Epic A §A7) before promotion.

---

## 4. Phases, milestones & task breakdown

> The full class is in §2.2 (Appendix A points to it). Tasks below are the build/verify breakdown. Each: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑1…OQ‑6)
- **T0.1 — Target org** (OQ‑6) for deploy + tests. Completion: org confirmed.
- **T0.2 — Verify dependencies present:** `PRM_ServiceBase` + `PRM_FormSubUtility` (with `NameNormalize` **and** `recordTypeId`) and **`PRM_CMAService` (E19)** on `main`; Account/Case/IndividualApplication RTs active (verified); permission set/field access for the intake user. Validation: describe/deploy dry‑run. Completion: all present.
- **T0.3 — Resolve open business/data items:** picklist value validity (OQ‑1), gender‑null‑for‑flow (OQ‑2), IA flow→RT rule (OQ‑3 / CL‑E2), date format (OQ‑4 / CL‑E1b), multipicklist `PRM_PDMManualUpdateType__c` shape (OQ‑5). Completion: each decided or explicitly deferred.

### Phase 1 — `PRM_CaseService` core *(M1)*
- **T1.1 — Class + `execute` + `AppUow`**
  - Purpose: parse `applications[]`; build UoWs (no DML in loop); cache RT Ids once.
  - Outcome: per §2.2.
  - Dependencies: T0.2. Prerequisites: Phase 0.
  - Impacted: `classes/PRM_CaseService.cls`.
  - Validation: compiles; parses sample payload; RT Ids cached. Testing: unit (parse + cache). Risks: **[RISK]** payload shape drift vs EPIC F. Completion: parse + UoW build green.
- **T1.2 — Builders (`buildAccount` / `buildIndividualApplication` / `buildCase`) + formula helpers**
  - Purpose: in‑memory record build + in‑service formulas (gender, caseType, credentialing, IA RT, AppliedDate).
  - Outcome: per §4 field map + §2.2 builders.
  - Dependencies: T1.1. Validation: field‑by‑field unit assertions (incl. Datetime `AppliedDate`, `PRM_Stage__c`, Boolean `PRM_DelegatedOnly__c`). Testing: builder unit cases (IBC vs Delegated, PNC vs non‑PNC). Risks: **[RISK]** picklist values (OQ‑1), gender‑null (OQ‑2), IA RT rule (OQ‑3). Completion: builders unit‑tested.
- **T1.3 — Bulk DML order + circular‑FK back‑links**
  - Purpose: 5 bulk statements (insert ×3 + back‑link update ×2), reference correlation.
  - Outcome: per §5 steps 1–5.
  - Dependencies: T1.2. Validation: created records have correct FKs; DML count = 5 regardless of N. Testing: bulk test (200). Risks: **[RISK]** back‑link required‑at‑insert (org‑verified nullable). Completion: bulk DML green.

### Phase 2 — CMA invocation (Practitioner CMA) *(M1)*
- **T2.1 — Build + invoke `PRM_CMAService`** (§5 step 6 / §3f / §5.1)
  - Purpose: one Practitioner CMA per practitioner, bulk, same transaction.
  - Outcome: CMA rows (Account ↔ Case Manager) created; idempotent on re‑submit.
  - Dependencies: T1.3, **E19 `PRM_CMAService`**. Prerequisites: CMA + its `PRM_AsyncJob_Access` FLS deployed.
  - Impacted: `PRM_CaseService.cls` (the CMA call); none in CMA.
  - Validation: after intake, one `PRM_CaseManagerAssociation__c` (RT `PRM_Practitioner`) per practitioner with correct `PRM_Account__c` + `PRM_CaseManager__c`; re‑run → no dup. Testing: integration test (E1 → CMA). Risks: **[RISK]** cross‑class dependency on E19 (must land first); **[RISK]** a CMA failure rolls back the whole intake (intended). Completion: CMA integration test green.

### Phase 3 — Response + wrapper contract *(M1)*
- **T3.1 — Build the response** (per‑practitioner AccountId + CaseManagerId + flat list, input order).
  - Purpose: give the EPIC F wrapper what it needs for `PRM_AsyncJob__c` + `PRM_AsyncJobRecords__c` + payload enrichment.
  - Dependencies: T1.3. Validation: response shape + order. Risks: **[RISK]** wrapper coupling — confirm the wrapper consumes AccountId for payload enrichment (cross‑epic, EPIC F). Completion: response asserted.

### Phase 4 — Testing *(M2)*
- **T4.1 Unit:** builders/formulas (IBC vs Delegated, PNC vs non‑PNC, gender, credentialing, caseType, IA RT).
- **T4.2 Bulk/governor:** 200 applications → 5 DML + the CMA call; assert limits.
- **T4.3 CMA:** Practitioner CMA created per practitioner; re‑submit → no dup (pre‑check).
- **T4.4 Atomicity:** a bad row (or CMA failure) rolls back the whole submission (all‑or‑nothing).
- **T4.5 Negative/edge:** missing required (`Category` — should be validator‑guaranteed), blank dates, multipicklist value.
  - Dependencies: Phases 1–3. Completion: ≥ 85% coverage; suites green.

### Phase 5 — Evidence & governance *(M2)* (Epic A §A7)
- **T5.1 —** Test Evidence Report (coverage + org spot‑check of Account/Case/IA + Practitioner CMA) + human sign‑off. Risks: **[RISK]** no org → can't run (OQ‑6). Completion: evidence + sign‑off.

### Phase 6 — Version control *(M2)* (E01 §9 / Epic A §A8)
- **T6.1 —** Branch `epic-e/case-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility`. **Pairs with EPIC F** intake wrapper. Commit prefix `[E1]`.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Validate picklist values at intake (OQ‑1).** The service writes/forwards picklist values (gender outputs, `caseType`, `Status/Stage/Category/ApplicationType/ProcessingStatus`). Recommend the **EPIC F validator** asserts these are active picklist entries (fail fast) rather than letting the insert throw — keeps the atomic reject clean.
- **[RECOMMENDATION] Explicit date parsing (OQ‑4/CL‑E1b).** `Date.parse`/`Datetime.parse` are locale‑dependent. If the payload format is fixed, add an explicit parser to `PRM_FormSubUtility` (single‑owner) to avoid org‑locale drift.
- **[RISK] E19 dependency.** E1's CMA call requires `PRM_CMAService` (E19) + its permission‑set FLS deployed first; otherwise E1 won't compile/insert. Sequence E19 → E1.
- **[RISK] Cross‑epic wrapper coupling.** E1's value depends on the EPIC F wrapper consuming the return (AccountId for payload enrichment, CaseManagerId for `PRM_AsyncJobRecords__c`). Track as an EPIC F deliverable.
- **[RISK] Same‑transaction blast radius.** CMA runs in the intake transaction (atomic). A CMA mapping/FLS bug blocks the whole intake until fixed — intended, but worth monitoring at go‑live.
- **[RECOMMENDATION] Existing‑practitioner path.** Keep deferred (insert‑only) for the pilot; reintroduce the new‑vs‑existing Account partition when in scope (the `AppUow` correlation already supports it).

---

## 6. Gaps & hidden dependencies

- **Target org** (OQ‑6) — gates deploy/test.
- **E19 `PRM_CMAService`** must land first (compile + runtime dependency).
- **EPIC F wrapper** — assembles `params` (flow + jsonInput), consumes the response (AccountId/CaseManagerId), seeds `PRM_AsyncJob__c`/`PRM_AsyncJobRecords__c`, enriches the payload. Cross‑epic.
- **`PRM_FormSubUtility.recordTypeId`** — shared helper (added with E19); single‑owner coordination.
- **Open business/data:** picklist values (OQ‑1), gender‑null (OQ‑2), IA flow→RT (OQ‑3), date format (OQ‑4), multipicklist (OQ‑5).

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑1 (F‑4) — Picklist value validity.** Are the payload + formula values guaranteed active picklist entries (gender, `caseType`, `Status/PRM_Stage__c/Category/ApplicationType/PRM_ProcessingStatus__c`)? *Recommendation:* validate at intake (EPIC F).
- **OQ‑2 (F‑6) — Gender null for PractitionerCreation flow.** Confirm both gender fields should be `null` for this flow (legacy parity).
- **OQ‑3 (F‑8/CL‑E2) — IA flow→RecordType rule.** Confirm `PRM_PDMManualChange` (PractitionerCreation) vs `PRM_PractitionerParticipationRequest` (else), PNC → `PRM_PNC`.
- **OQ‑4 (F‑9/CL‑E1b) — Date/Datetime format.** Locale‑parse vs a fixed format (e.g. `MM/dd/yyyy`)?
- **OQ‑5 — `PRM_PDMManualUpdateType__c` (multipicklist).** Does the payload send a single value or a `;`‑joined set?
- **OQ‑6 — Target org** for deploy/test.

*(Already resolved in E01 §8: `Category` source, `flowType` source, partial‑failure = all‑or‑nothing, return shape, CL‑E5 recordTypeId, AppliedDate/Stage/DelegatedOnly types, CMA invocation.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | E19 `PRM_CMAService` not landed → E1 won't compile/insert | Medium | High | Sequence E19 → E1; T0.2 check |
| R‑2 | Picklist value mismatch → insert fails | Medium | Medium | OQ‑1 validate at intake; T4.5 |
| R‑3 | Date locale drift | Medium | Medium | OQ‑4 explicit parser |
| R‑4 | IA flow→RT rule wrong | Medium | Medium | OQ‑3 confirm; T4.1 |
| R‑5 | Wrapper (EPIC F) coupling not wired | Medium | High | track EPIC F deliverable; T3.1 |
| R‑6 | Same‑txn CMA failure blocks intake | Low–Med | Medium | accepted (atomic); idempotent re‑submit |
| R‑7 | No target org | Medium | High | OQ‑6 |
| R‑8 | `PRM_FormSubUtility` parallel edits | Low | Medium | single‑owner; land recordTypeId first |

---

## 9. Sequencing & effort

- **Order:** Phase 0 → 1 → 2 → 3 → 4 → 5 → 6. **E19 (CMA) before E1** (dependency). EPIC F wrapper pairs with E1.
- **Effort:** within the ~2.5 d catalog estimate — core class + builders/formulas ~1.5 · CMA integration ~0.25 · response/contract ~0.1 · tests ~0.5 · evidence/VCS folded in. *(Re‑confirm after OQ‑1…OQ‑5.)*
- **Depends on:** EPIC B + E19 + EPIC A on `main`. **Blocks/pairs with:** EPIC F intake wrapper.

---

## 10. What happens after sign‑off

Resolve OQ‑1…OQ‑6 (esp. target org + the picklist/date/RT confirmations). Then build per **§2.2 (complete implementation)**: `execute` + builders/formulas → bulk DML/back‑links → CMA invocation → response → tests (unit/bulk/CMA/atomicity/negative) → Test Evidence Report → human governance sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑6) and the remaining items are confirmed.**

---

## Appendix A — Complete reference implementation

> Full, deployable `PRM_CaseService` (mirrors `E01_PRM_CaseService.md` §2.2): `execute()` (parse → build UoWs → 5 bulk DML + back‑links → §3f CMA invocation → response) + builders + formula/parse helpers. **Depends on** `PRM_FormSubUtility` (`NameNormalize`, `recordTypeId`) and **`PRM_CMAService` (E19)**.

```apex
public with sharing class PRM_CaseService extends PRM_ServiceBase {

    // one per applications[] element, built in input order — holds the 3 record references
    @TestVisible
    private class AppUow {
        Account acc;
        IndividualApplication ia;
        Case cse;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        List<Object> applications = (List<Object>) input.get('applications');

        // 1) cache record-type Ids ONCE (never per row) — via PRM_FormSubUtility.recordTypeId (CL-E5 resolved)
        Id accRt  = PRM_FormSubUtility.recordTypeId(Account.SObjectType, 'PRM_Practitioner');
        Id caseRt = PRM_FormSubUtility.recordTypeId(Case.SObjectType, 'PRM_PRM');   // IA RT resolved per-app (PNC/flow)

        // 2) build one UoW per application, in input order (no DML in this loop)
        List<AppUow> uows = new List<AppUow>();
        for (Object o : applications) {
            Map<String, Object> app = (Map<String, Object>) o;
            Map<String, Object> cm  = (Map<String, Object>) app.get('caseManagerInfo');
            Map<String, Object> p   = (Map<String, Object>) app.get('practitionerInfo');

            AppUow u = new AppUow();
            u.acc = buildAccount(p, cm, accRt, flow);
            u.ia  = buildIndividualApplication(cm, flow);
            u.cse = buildCase(cm, caseRt, flow);
            uows.add(u);
        }

        // 3) BULK DML — wrapper references carry Ids forward, so no re-correlation/re-query

        // 3a Accounts — all insert (existing-practitioner path is out of scope for now; see §6)
        List<Account> accIns = new List<Account>();
        for (AppUow u : uows) accIns.add(u.acc);
        insert accIns;   // populates Id on the SAME instances held by the UoWs

        // 3b IndividualApplications — FK from the now-populated Account reference
        List<IndividualApplication> iaIns = new List<IndividualApplication>();
        for (AppUow u : uows) { u.ia.AccountId = u.acc.Id; iaIns.add(u.ia); }
        insert iaIns;

        // 3c Cases — FK to Account + IA (the Case Manager)
        List<Case> caseIns = new List<Case>();
        for (AppUow u : uows) { u.cse.AccountId = u.acc.Id; u.cse.PRM_CaseManager__c = u.ia.Id; caseIns.add(u.cse); }
        insert caseIns;

        // 3d back-link: IA.ApplicationCaseId = Case.Id
        List<IndividualApplication> iaBack = new List<IndividualApplication>();
        for (AppUow u : uows) { u.ia.ApplicationCaseId = u.cse.Id; iaBack.add(u.ia); }
        update iaBack;

        // 3e back-link: Account.PRM_CaseManager__c = IA.Id
        List<Account> accBack = new List<Account>();
        for (AppUow u : uows) { u.acc.PRM_CaseManager__c = u.ia.Id; accBack.add(u.acc); }
        update accBack;

        // 3f) CMA — one "Practitioner CMA" per practitioner (Account ↔ Case Manager), in the SAME intake transaction (§5.1)
        List<Object> cmaRequests = new List<Object>();
        for (AppUow u : uows) {
            cmaRequests.add(new Map<String, Object>{
                'caseManagerId' => u.ia.Id,                                   // → PRM_CaseManager__c (required)
                'recordType'    => 'PRM_Practitioner',                        // CMA RecordType
                'lookups'       => new Map<String, Object>{ 'PRM_Account__c' => u.acc.Id }
            });
        }
        new PRM_CMAService().execute(new Map<String, Object>{ 'associations' => cmaRequests });
        // CMA = idempotent pre-check + all-or-nothing → a CMA failure rolls back the whole intake (atomic)

        // 4) response — input order preserved
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        List<Id> caseManagerIds = new List<Id>();
        for (AppUow u : uows) {
            results.add(new Map<String, Object>{
                'practitionerAccountId' => u.acc.Id,
                'caseId'                => u.cse.Id,
                'caseManagerId'         => u.ia.Id
            });
            caseManagerIds.add(u.ia.Id);
        }
        response = new Map<String, Object>{ 'applications' => results, 'caseManagerIds' => caseManagerIds };
        return response;
    }

    // ── builders (pure in-memory; formulas computed here — see §4 of the design doc) ──

    private Account buildAccount(Map<String, Object> p, Map<String, Object> cm, Id rt, String flow) {
        Account a = new Account();
        a.RecordTypeId = rt;                                                   // RT 'PRM_Practitioner'
        a.FirstName  = PRM_FormSubUtility.NameNormalize((String) p.get('firstName'));
        a.MiddleName = PRM_FormSubUtility.NameNormalize((String) p.get('middleName'));
        a.LastName   = PRM_FormSubUtility.NameNormalize((String) p.get('lastName'));
        a.Suffix     = PRM_FormSubUtility.NameNormalize((String) p.get('suffix'));
        a.PersonEmail     = (String) p.get('email');
        a.PersonBirthdate = parseDate((String) p.get('dob'));
        String gender = (String) p.get('gender');
        a.PersonGenderIdentity      = genderIdentity(gender, flow);
        a.HealthCloudGA__Gender__pc = genderIdentityPc(gender, flow);
        a.HealthCloudGA__SourceSystemId__c = (String) p.get('npi');
        a.PRM_ProviderRole__c = (String) p.get('providerRole');               // UI label: 'title'
        a.PRM_CredentialingStatus__c = credentialingStatus((String) p.get('practitionerCreationType'));
        a.PRM_PNC__c   = toBool(cm.get('PNCFlag'));
        a.Type         = (String) p.get('accountType');
        a.IsActive     = toBool(p.get('isActive'));
        a.PRM_EffectiveFrom__c = parseDate((String) p.get('effectiveFrom'));
        a.PRM_EffectiveTo__c   = parseDate((String) p.get('effectiveTo'));
        a.PRM_DelegatedOnly__c = toBool(p.get('delegated'));                  // Boolean checkbox (verified IBXDEV01)
        return a;
    }

    private IndividualApplication buildIndividualApplication(Map<String, Object> cm, String flow) {
        String  flowType = String.isNotBlank(flow) ? flow : (String) cm.get('flowType');
        Boolean pnc      = toBool(cm.get('PNCFlag'));

        IndividualApplication ia = new IndividualApplication();
        ia.RecordTypeId = iaRecordTypeId(pnc, flowType);

        Datetime applied = parseDateTime((String) cm.get('AppliedDate'));
        ia.AppliedDate = (applied != null) ? applied : System.now();          // Datetime (verified IBXDEV01)

        ia.Status          = (String) cm.get('Status');
        ia.PRM_Stage__c    = (String) cm.get('Stage');                        // API name PRM_Stage__c (verified)
        ia.Category        = (String) cm.get('Category');                     // REQUIRED — validator-guaranteed (F-3)
        ia.ApplicationType = (String) cm.get('ApplicationType');
        ia.PRM_FormCompletedBy__c = (String) cm.get('FormCompletedBy');
        ia.PRM_FormType__c        = (String) cm.get('FormType');
        ia.PRM_PNC__c             = pnc;
        ia.PRM_CorporateReceiptDate__c = parseDate((String) cm.get('CorporateReceiptDate'));
        ia.PRM_FHNaticCaseNumber__c    = (String) cm.get('FHnaticCaseNumber');
        ia.PRM_DisplayCapSites__c      = toBool(cm.get('HasCapSites'));
        ia.PRM_ProcessingStatus__c     = (String) cm.get('processingStatus');
        ia.PRM_PDMManualUpdateType__c  = (String) cm.get('PDMManualUpdateType'); // multipicklist (OQ-5: ;-join if multiple)
        // AccountId + ApplicationCaseId FKs set in execute() (steps 3b / 3d)
        return ia;
    }

    private Case buildCase(Map<String, Object> cm, Id rt, String flow) {
        String flowType = String.isNotBlank(flow) ? flow : (String) cm.get('flowType');
        Case c = new Case();
        c.RecordTypeId = rt;                                                   // RT 'PRM_PRM'
        c.Type = caseType(flowType, toBool(cm.get('PNCFlag')));
        c.PRM_IsRoundRobinLogic__c = toBool(cm.get('isRoundRobinLogic'));
        // AccountId + PRM_CaseManager__c FKs set in execute() (step 3c)
        return c;
    }

    // ── formula helpers ──

    private Id iaRecordTypeId(Boolean pnc, String flowType) {
        if (pnc) return PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PNC');
        return (flowType == 'PractitionerCreation')
            ? PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PDMManualChange')
            : PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PractitionerParticipationRequest');
    }

    private String caseType(String flowType, Boolean pnc) {
        if (String.isNotBlank(flowType) && flowType == 'PractitionerCreation') return 'Network Management QC';
        return pnc ? 'PNC' : 'Application Review';
    }

    private String credentialingStatus(String type) {
        if (type == 'IBC Professional Staff')   return 'Credentialed';
        if (type == 'Delegated Credentialing')  return null;
        return 'Credentialing In Progress';
    }

    private String genderIdentity(String gender, String flow) {
        if (flow == 'PractitionerCreation') return null;
        if (gender == 'Male')   return 'M';
        if (gender == 'Female') return 'F';
        if (gender == 'Prefer not to share') return 'Prefer not to share';
        return 'U';
    }

    private String genderIdentityPc(String gender, String flow) {
        if (flow == 'PractitionerCreation') return null;
        if (gender == 'Male')   return 'Male';
        if (gender == 'Female') return 'Female';
        if (gender == 'Prefer not to share') return 'Prefer not to share';
        return 'Other';
    }

    // ── small parse utilities ──
    private Boolean toBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date parseDate(String s) { return String.isBlank(s) ? null : Date.parse(s); }            // ⚠ locale (CL-E1b)
    private Datetime parseDateTime(String s) { return String.isBlank(s) ? null : Datetime.parse(s); } // ⚠ locale (CL-E1b)
}
```

> Keep this in sync with `E01_PRM_CaseService.md` §2.2 (the design source). Open items (OQ‑1…OQ‑6) above still apply to this implementation.
