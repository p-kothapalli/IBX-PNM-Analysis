# E13 · `PRM_HealthcareFacilityCreationService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** Self‑contained for **code** generation (see **§0**): Apex class + `.cls-meta.xml` (**Appendix A**), test class + meta (**Appendix B**), deploy/validation commands (**Appendix C**). **No component metadata is generated** (per request) — E13 adds **no new fields**; `Location`/`HealthcareFacility`/`PRM_HealthcareFacilityNPI__c` reuse existing `PRM_ExternalId__c`, and the **HealthcareFacility trigger owns** `PRM_ExternalId__c` (populate) + the Location NPI History (create).
>
> **Source of truth:** `E13_PRM_HealthcareFacilityCreationService.md` (design §1–§9, org‑validation, trigger findings) + `PRM_HCFacilityTriggerHelper` (org) + Part 1 §E0.4. Anything not stated there is **UNKNOWN** and raised as an Open Question (§7) — **not assumed**.
>
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RISK]** · **[RECOMMENDATION]** · **Pending Clarification**.

---

## 0. Component inventory — everything to generate

| # | Component | Type | Path | New/Edit | Spec |
|---|---|---|---|---|---|
| 1 | `PRM_HealthcareFacilityCreationService` | Apex class (`with sharing`, extends `PRM_ServiceBase`) | `classes/PRM_HealthcareFacilityCreationService.cls` (+ meta) | **NEW** | Appendix A |
| 2 | `PRM_HealthcareFacilityCreationServiceTest` | Apex test class | `classes/PRM_HealthcareFacilityCreationServiceTest.cls` (+ meta) | **NEW** | Appendix B |
| 3 | `PRM_TestDataFactory` builders | Apex test factory (reuse / extend) | `classes/PRM_TestDataFactory.cls` | **EDIT if needed** | Appendix B note (OQ‑E13‑15) |

> **No metadata:** no field/object/permission‑set XML. E13 uses existing fields. **FLS prerequisite** (Read+Edit on the fields E13 writes) is assumed present on `PRM_AsyncJob_Access` — confirm (WI‑2), but **not generated here**.
> **⚠ Depends on the HealthcareFacility trigger** (`PRM_HCFacilityTriggerHelper`) being active in the target org — it populates `HealthcareFacility.PRM_ExternalId__c` and creates `PRM_HealthcareFacilityNPI__c` (Location NPI History) on insert.
> **Conventions:** `PRM_` prefix; `with sharing`; **service does NO SOQL** (the batch does the existence gate + injects context — §1); one bulk DML per object type; **API 66.0**; test reuses `PRM_TestDataFactory` + modern `Assert`.

---

## 1. Confirmed requirements (from `E13…md` + org validation + trigger)

- **[CONFIRMED]** `PRM_HealthcareFacilityCreationService extends PRM_ServiceBase`; `execute(Map):Map`. **Runs inside `PracticeLocationAndGroupBatch` (seq 2)** (not a separate async worker — OQ‑E13‑2). **Branch = BOTH** (OQ‑E13‑1b). **Writes:** `Location`, `Address`, `HealthcareFacility` (+ sets `HealthcareFacility.PRM_NpiId__c`). (Design §1.)
- **[CONFIRMED]** **New‑location gate:** create `Location`/`Address`/`HealthcareFacility` **only when the HealthcareFacility doesn't already exist** (by the composite `PRM_ExternalId__c`). Existing → skip. (Design §2; your directive.)
- **[CONFIRMED]** **The HealthcareFacility trigger owns two things — E13 must NOT do them:** `populatePRMExternalId` (sets `PRM_ExternalId__c`) and `createNPIRecords` (creates `PRM_HealthcareFacilityNPI__c` Location NPI History from `PRM_NpiId__c`). E13 only sets `HealthcareFacility.PRM_NpiId__c`. (Design §1/§2, org.)
- **[CONFIRMED]** **Composite formula (`populatePRMExternalId`)** = `Account.SourceSystemIdentifier-{PRM_NpiId__c}-{PRM_PracticeClassification__c}-{addr.line1}-{addr.line2}-{addr.zip}-{addr.phone}` (primary Address). The **batch replicates it** to compute the gate key (§5.2 design). (OQ‑E13‑1 resolved.)
- **[CONFIRMED — rule]** **Service is SOQL‑free.** The **batch** dedupes locations, resolves the location NPI (E12), computes the composite, **pre‑checks HealthcareFacility existence**, and passes E13 **only the new locations** with injected `accountId` (group), `caseManagerId`, `locationNpiId`, effective date, and the location fields. (Design §4.1; `prm-service-class-boundaries`.)
- **[CONFIRMED — decisions]** `HealthcareFacility.AccountId` = **group/vendor Account (E3)** (OQ‑E13‑5); shared‑location `caseManagerId` = **first/owning practitioner** (OQ‑E13‑5b); effective dates ← **practitioner `effectiveFromDate`** (OQ‑E13‑8); location NPI `NpiType='Organization'` (OQ‑E13‑10); `telehealthEnabled` ignored (OQ‑E13‑11); `selectedInfoCodes` → another service (OQ‑E13‑13); `networkTaxonomyRoles` → E14 (OQ‑E13‑14); `practiceClassification` **added to source** (§5.1). (Design §8.)
- **[CONFIRMED — org, required (never null)]** `Location`: `Name`, **`LocationType`** (picklist), `PRM_TelehealthOnly__c`, `PRM_EffectiveFrom__c`, `PRM_Pending__c`. `Address`: `ParentId` (Location, insert‑only), `PRM_EffectiveFrom__c`, `PRM_Pending__c`. `HealthcareFacility`: `Name`, `AccountId`, `PRM_Primary__c`, `PRM_Pending__c`. (Design §3.1.)
- **[CONFIRMED]** **DML order:** resolve NPI (E12) → insert `Location` → insert `Address[]` (FK `ParentId`) → insert `HealthcareFacility` (FK `LocationId`,`AccountId`,`PRM_NpiId__c`). ⚠ Address **before** HealthcareFacility so the trigger's `populatePRMExternalId` can read the primary Address. (Design §7.)
- **[CONFIRMED]** **Output:** `response.locations[]` (new only): `{ locationId, addressIds, healthcareFacilityId, locationNpiId }`. (Design §4.)
- **[CONFIRMED]** **Effort:** ~3.0 d. Target org **IBXDEV01** (OQ‑E13‑16).
- **[CONFIRMED]** **Depends on:** Epic A/B, **E3** (group Account, `AccountId`), **E12** (location NPI), the `PracticeLocationAndGroupBatch` wiring (gate + injection), and the **HealthcareFacility trigger**.

> **🔎 Org validation (IBXDEV01):** Location (RT `Master`, `LocationType` required picklist, `PRM_ExternalId__c` Unique+extId); Address (RT `Master`, `PRM_AddressType__c` multipicklist, `ParentId`→Location required/insert‑only, no unique key); HealthcareFacility (`PRM_ExternalId__c` Unique+extId trigger‑owned, `PRM_NpiId__c`→HealthcareProviderNpi, `PRM_PracticeClassification__c` `Professional/Facility`, `PRM_BillingType__c` `UB/1500`); `PRM_HealthcareFacilityNPI__c` (trigger‑created).

---

## 2. Constraints

- **[CONFIRMED — rule]** No SOQL/correlation in the service — the **batch** does the existence gate + injection.
- **[CONFIRMED]** E13 must **not** set `HealthcareFacility.PRM_ExternalId__c` nor create `PRM_HealthcareFacilityNPI__c` (trigger owns both).
- **[CONFIRMED]** **Address inserted before HealthcareFacility** (trigger reads the primary Address for the external id).
- **[CONFIRMED]** Required fields never null (§1); `PRM_AddressType__c` is a multipicklist (set the single source value).
- **[CONFIRMED]** Idempotency is at the **batch gate** (HCF existence) — E13 receives only new locations, so its inserts don't duplicate on retry (a prior‑run HCF is filtered out by the gate).
- **[OPEN]** `LocationType` value/default (OQ‑E13‑6), `PRM_BillingType__c` (OQ‑E13‑7), `officeEmail`/`doingBusinessAsName`/`capabilitiesAtLocation` targets (OQ‑E13‑12), Address dedupe within edge cases (OQ‑E13‑9), `Account.SourceSystemIdentifier` (OQ‑E13‑18), trigger cascade (OQ‑E13‑19) — **batch‑injected or pending**, not hardcoded.

---

## 3. Acceptance criteria

- **[CONFIRMED]** For each **new** location: builds `Location` → `Address[]` → `HealthcareFacility` (with `PRM_NpiId__c`), **one bulk DML per object type**, **zero SOQL** in the service.
- **[CONFIRMED]** Sets `HealthcareFacility.PRM_NpiId__c` so the trigger auto‑creates the Location NPI History + external id; E13 sets **neither** directly.
- **[CONFIRMED]** Required fields never null; `AccountId` = group Account; effective dates from the practitioner; `PRM_PracticeClassification__c` from source.
- **[CONFIRMED]** **Idempotent** at the batch gate — re‑run creates no duplicate Location/Address/HealthcareFacility.
- **[CONFIRMED]** `buildFacilityExternalId(...)` (the gate helper) reproduces the trigger's `populatePRMExternalId` output exactly (blank handling + primary‑address selection).
- **[CONFIRMED]** Returns per‑new‑location `{ locationId, addressIds, healthcareFacilityId, locationNpiId }`.
- **[CONFIRMED]** Apex ≥ 85% incl. bulk, the gate helper, required‑field, and the trigger side‑effects (NPI History + external id populated).
- **[CONFIRMED]** Field API names/types validated against the org (done; re‑confirm target org).

---

## 4. Phases, milestones & task breakdown

> Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted · Validation · Testing · Risks · Completion. Full class in **Appendix A**.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑E13‑6/7/9/12/18/19, 4b)
- **T0.1 — Confirm target org + trigger active** (OQ‑E13‑16). The HealthcareFacility trigger (`PRM_HCFacilityTriggerHelper`) must be active. Completion: confirmed.
- **T0.2 — Confirm the batch gate contract** (rule): `PracticeLocationAndGroupBatch` dedupes locations, resolves NPI (E12), computes the composite (`buildFacilityExternalId`), pre‑checks HealthcareFacility, and passes E13 **only new** locations + injected context. Completion: contract confirmed (OQ‑E13‑4b).
- **T0.3 — Resolve injected/undocumented values:** `LocationType` (OQ‑E13‑6), `Location.Name` source (OQ‑E13‑6), `PRM_BillingType__c` (OQ‑E13‑7), `officeEmail`/`doingBusinessAsName`/`capabilitiesAtLocation` targets (OQ‑E13‑12). Completion: decided or deferred.
- **T0.4 — Confirm `Account.SourceSystemIdentifier`** on the group Account = `{taxId}-{groupName}` (OQ‑E13‑18 — likely an E3 fix). Completion: confirmed/fixed.
- **T0.5 — Map the trigger cascade** (OQ‑E13‑19): which downstream records the trigger auto‑creates (NPI History, alternate contact, PL number, networks, CDM update) so E13 doesn't duplicate them; factor SOQL/DML into the batch size. Completion: documented.
- **T0.6 — Verify dependencies on `main`:** `PRM_ServiceBase`, `PRM_FormSubUtility`, E12, `PRM_AsyncJob_Access`, `PRM_TestDataFactory`. Completion: present.

### Phase 1 — Access prerequisite *(M1)*
- **T1.1 — Confirm FLS** on `PRM_AsyncJob_Access` for the fields E13 writes (`Location.*`, `Address.*`, `HealthcareFacility.*` incl. `PRM_NpiId__c`). **No new fields; metadata not generated here.** Completion: FLS present.

### Phase 2 — `PRM_HealthcareFacilityCreationService` core *(M2)*
- **T2.1 — Class + `buildFacilityExternalId` helper (pure).** Purpose: reproduce `populatePRMExternalId` for the batch gate. Outcome: Appendix A helper. Validation: unit vs the trigger output (blanks, primary address). Testing: helper unit. Risks: **[RISK]** formula drift vs the trigger. Completion: helper matches.
- **T2.2 — `execute` + builders (`buildLocation`, `buildAddresses`, `buildFacility`), no SOQL.** Purpose: build the new‑location graph from injected context; required fields never null. Outcome: Appendix A. Dependencies: T2.1, T0.3. Validation: field‑by‑field; no SOQL. Testing: builder units. Risks: **[RISK]** `LocationType` (OQ‑E13‑6). Completion: builders green.
- **T2.3 — Bulk DML in FK order + response.** Purpose: insert Location → Address → HealthcareFacility (set `PRM_NpiId__c`); return Ids. Dependencies: T2.2. Validation: DML counts (3); SOQL=0; trigger side‑effects present (NPI History + external id). Completion: green.

### Phase 3 — Testing *(M3)*
- **T3.1 Unit:** `buildFacilityExternalId` (blank handling, primary‑address pick), builders, required fields.
- **T3.2 Bulk/governor:** multiple new locations → 0 service SOQL + 3 DML; assert limits (account for the **trigger's** SOQL/DML — OQ‑E13‑19).
- **T3.3 Trigger side‑effects:** after HCF insert, assert `PRM_HealthcareFacilityNPI__c` exists (linked HCF↔NPI) and `HealthcareFacility.PRM_ExternalId__c` populated.
- **T3.4 Idempotency (batch gate):** simulate a pre‑existing HCF → the batch gate excludes it → E13 receives only new → no duplicate.
  - Dependencies: Phases 1–2, test data (OQ‑E13‑15). Completion: ≥ 85%.

### Phase 4 — Evidence & governance *(M3)* (Epic A §A7)
- **T4.1 —** Test Evidence Report (coverage + org spot‑check incl. trigger side‑effects + a re‑run case) + human sign‑off.

### Phase 5 — Version control *(M3)* (Epic A §A8)
- **T5.1 —** Branch `epic-e/healthcare-facility-service`; PR into `main`; squash‑merge; tag. Commit prefix `[E13]`. **No schema** lands.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Let the trigger do its job; E13 stays a thin builder.** E13 sets `HealthcareFacility.PRM_NpiId__c` and inserts — the trigger creates the NPI History + external id. Re‑implementing those in the service would double‑create. *(Confirm the full trigger cascade — OQ‑E13‑19.)*
- **[RECOMMENDATION] Gate in the batch (SOQL), build in the service (no SOQL).** Keeps the boundary rule; `buildFacilityExternalId` is a pure helper the batch calls for the pre‑check.
- **[RECOMMENDATION] Insert Address before HealthcareFacility.** The trigger's `populatePRMExternalId` reads the Location's primary Address — if the address isn't committed first, the external id loses the address segments.
- **[RISK] `Account.SourceSystemIdentifier` (OQ‑E13‑18).** The external id prefix reads `Account.SourceSystemIdentifier`; E3 sets `HealthCloudGA__SourceSystemId__c`. If they diverge, the gate + external id break. **Likely an E3 fix.**
- **[RISK] Trigger cascade governor cost (OQ‑E13‑19).** The HCF insert fires several automations (NPI History, networks, alternate contact, CDM update) → real SOQL/DML per row; **tune batch size** accordingly.
- **[RISK] `LocationType` required, not in source (OQ‑E13‑6).** Must inject/default; don't hardcode.
- **[RISK] `IndividualApplication` + trigger test data (OQ‑E13‑15).** Tests need a group Account (with `SourceSystemIdentifier`), a Case Manager, and a location NPI; the trigger runs in tests → its dependencies must be satisfiable.

---

## 6. Gaps & hidden dependencies

- **`Account.SourceSystemIdentifier` (OQ‑E13‑18)** — E3 dependency for the external id prefix.
- **Trigger cascade (OQ‑E13‑19)** — what the HCF trigger auto‑creates; don't duplicate; governor budget.
- **`LocationType` (OQ‑E13‑6)**, **`PRM_BillingType__c` (OQ‑E13‑7)**, **email/DBA/capabilities targets (OQ‑E13‑12)** — pending.
- **Batch gate + E12 ordering (OQ‑E13‑4b)** — NPI resolved before the composite.
- **`networkTaxonomyRoles` → E14 (OQ‑E13‑14)**, **`selectedInfoCodes` → another service (OQ‑E13‑13)** — out of E13.

---

## 7. Open Questions (must be answered before/along build)

- **🔑 OQ‑E13‑18 — `Account.SourceSystemIdentifier`** on the group Account (external id prefix) — confirm/fix in E3.
- **OQ‑E13‑19 — HealthcareFacility trigger cascade** — enumerate what it auto‑creates so E13 doesn't duplicate + governor budget.
- **OQ‑E13‑4b — Batch gate contract** — batch resolves NPI (E12) → computes composite → pre‑checks HCF → passes only new locations + injected context.
- **OQ‑E13‑6 — `Location.Name` (practiceName vs DBA) + `LocationType`** (required; not in source).
- **OQ‑E13‑7 — `PRM_BillingType__c`** (`UB`/`1500`; not in source).
- **OQ‑E13‑9 — Address handling** — single `addressType` → multipicklist; any dedupe beyond the HCF gate?
- **OQ‑E13‑12 — `officeEmail`, `doingBusinessAsName`, `capabilitiesAtLocation`** target fields.
- **OQ‑E13‑15 — Test data** (group Account + `SourceSystemIdentifier`, Case Manager, location NPI; trigger‑compatible).

*(Resolved: OQ‑E13‑1 composite=`populatePRMExternalId`; 1b BOTH; 2 in‑batch seq 2; 3 E14/E15→PLRelatedBatch; 5 AccountId=group; 5b CM=first; 8 effdate=practitioner; 10 NpiType=Organization; 11 telehealthEnabled ignored; 13 infoCodes→other service; 14 networks→E14; 16 IBXDEV01; 17 NPI History = trigger‑created.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | `Account.SourceSystemIdentifier` missing/diverges → external id + gate break | **Medium** | High | OQ‑E13‑18; fix in E3; T0.4 |
| R‑2 | Trigger cascade governor cost under LDV | Medium | High | OQ‑E13‑19; tune batch size; T3.2 |
| R‑3 | `buildFacilityExternalId` drifts from the trigger formula | Medium | High | mirror `populatePRMExternalId` exactly; T3.1 vs trigger output |
| R‑4 | Address inserted after HCF → external id loses address segments | Low | Med | enforce Address‑before‑HCF order; T3.3 |
| R‑5 | `LocationType` required, undocumented | Medium | Med | OQ‑E13‑6; injected/default; T2.2 |
| R‑6 | Test data / trigger deps unsatisfiable | Medium | Med | OQ‑E13‑15; factory builders |
| R‑7 | Service does SOQL (violates rule) | Low | Med | gate in batch; assert 0 SOQL T3.2 |
| R‑8 | No target org / trigger inactive | Medium | High | OQ‑E13‑16; T0.1 |

---

## 9. Sequencing & effort

- **Order:** Phase 0 → 1 → 2 → 3 → 4 → 5. Runs in `PracticeLocationAndGroupBatch` (seq 2), after E3; before PLRelatedBatch (E14/E15).
- **Effort:** ~3.0 d — helper + builders ~1.2 · gate wiring w/ batch ~0.6 · tests ~0.8 · evidence/VCS folded in.
- **Depends on:** Epic A/B + E3 + E12 + the HealthcareFacility trigger on the target org. **Feeds:** E14 (affiliations), E15 (features), E8 (facility info codes) consume the created Location/Facility Ids.

---

## 10. What happens after sign‑off

Resolve OQ‑E13‑18/19/4b/6/7/9/12/15. Then build per **Appendix A** (batch gate + E13 builder), tests (**Appendix B**), Test Evidence Report, human sign‑off (A7). **Nothing deployed until the org + trigger (OQ‑E13‑16) and `Account.SourceSystemIdentifier` (OQ‑E13‑18) are confirmed.**

---

## Appendix A — Apex class `PRM_HealthcareFacilityCreationService` (+ meta)

> **SOQL‑free builder.** The **batch** does the existence gate (using `buildFacilityExternalId`) + injects context, and passes E13 **only new** locations. E13 inserts Location → Address → HealthcareFacility (sets `PRM_NpiId__c`); the **trigger** then populates `PRM_ExternalId__c` and creates the Location NPI History. **TODO/Pending‑Clarification** comments mark undocumented values (do not hardcode).

```apex
public with sharing class PRM_HealthcareFacilityCreationService extends PRM_ServiceBase {

    public class PRM_HCFException extends Exception {}

    @TestVisible
    private class LocationUnitOfWork {
        Map<String, Object> node;       // location node + batch-injected context
        Id accountId;                   // group/vendor Account (E3) -> HealthcareFacility.AccountId
        Id caseManagerId;               // batch-injected (first/owning practitioner)
        Id locationNpiId;               // HealthcareProviderNpi (E12) -> PRM_NpiId__c
        Location location;
        List<Address> addresses = new List<Address>();
        HealthcareFacility facility;
    }

    /**
     * Pure helper — mirrors PRM_HCFacilityTriggerHelper.populatePRMExternalId EXACTLY.
     * The BATCH calls this to compute the gate key, then pre-checks HealthcareFacility.PRM_ExternalId__c.
     * primaryAddress = the location's addresses[] entry with addressType='Primary' (else the first).
     */
    public static String buildFacilityExternalId(String accountSourceSystemIdentifier, Id npiId,
                                                 String practiceClassification, Map<String, Object> primaryAddress) {
        String line1 = strOf(primaryAddress, 'addressLine1');
        String line2 = strOf(primaryAddress, 'addressLine2');
        String zip   = strOf(primaryAddress, 'zip');
        String phone = strOf(primaryAddress, 'phone');
        return (accountSourceSystemIdentifier == null ? '' : accountSourceSystemIdentifier) + '-' +
               (npiId == null ? '' : String.valueOf(npiId)) + '-' +
               (practiceClassification == null ? '' : practiceClassification) + '-' +
               line1 + '-' + line2 + '-' + zip + '-' + phone;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'locations' => new List<Object>() };
        List<Object> locations = (params == null) ? null : (List<Object>) params.get('locations'); // NEW (gated) only
        if (locations == null || locations.isEmpty()) {
            return response;
        }

        // 1) parse + build UoWs (no SOQL/DML in loop)
        List<LocationUnitOfWork> unitsOfWork = new List<LocationUnitOfWork>();
        for (Object locationObject : locations) {
            Map<String, Object> node = (Map<String, Object>) locationObject;
            LocationUnitOfWork uow = new LocationUnitOfWork();
            uow.node = node;
            uow.accountId = (Id) node.get('accountId');
            uow.caseManagerId = (Id) node.get('caseManagerId');
            uow.locationNpiId = (Id) node.get('locationNpiId');
            if (uow.accountId == null || uow.locationNpiId == null) {
                throw new PRM_HCFException('Location requires injected accountId (group) and locationNpiId (E12)');
            }
            buildLocation(uow);
            unitsOfWork.add(uow);
        }

        // 2) insert Locations
        List<Location> locs = new List<Location>();
        for (LocationUnitOfWork uow : unitsOfWork) {
            locs.add(uow.location);
        }
        insert locs;

        // 3) build + insert Addresses (FK ParentId = Location) — BEFORE HealthcareFacility (trigger reads the primary address)
        List<Address> addresses = new List<Address>();
        for (LocationUnitOfWork uow : unitsOfWork) {
            buildAddresses(uow);
            addresses.addAll(uow.addresses);
        }
        if (!addresses.isEmpty()) {
            insert addresses;
        }

        // 4) build + insert HealthcareFacility (FK LocationId, AccountId, PRM_NpiId__c)
        //    -> trigger populates PRM_ExternalId__c + creates PRM_HealthcareFacilityNPI__c (Location NPI History)
        List<HealthcareFacility> facilities = new List<HealthcareFacility>();
        for (LocationUnitOfWork uow : unitsOfWork) {
            buildFacility(uow);
            facilities.add(uow.facility);
        }
        insert facilities;

        return buildResponse(unitsOfWork);
    }

    // ── builders (pure in-memory; required fields NEVER null) ──

    private void buildLocation(LocationUnitOfWork uow) {
        Map<String, Object> n = uow.node;
        Location loc = new Location();
        loc.Name = (String) n.get('practiceName');                 // required (OQ-E13-6: practiceName vs doingBusinessAsName)
        // TODO Pending Clarification (OQ-E13-6): LocationType is REQUIRED and not in source -> injected/default value:
        loc.LocationType = (String) n.get('locationType');         // e.g. 'Practice' — confirm (OQ-E13-6)
        loc.PRM_TelehealthOnly__c = asBool(n.get('telehealthOnly'));
        loc.PRM_EffectiveFrom__c = asDate(n.get('effectiveFrom')); // practitioner effectiveFromDate (OQ-E13-8)
        loc.PRM_Pending__c = false;                                // REQUIRED
        loc.PRM_CaseManager__c = uow.caseManagerId;
        uow.location = loc;
    }

    private void buildAddresses(LocationUnitOfWork uow) {
        List<Object> addressNodes = (List<Object>) uow.node.get('addresses');
        if (addressNodes == null) {
            return;
        }
        for (Object addressObject : addressNodes) {
            Map<String, Object> a = (Map<String, Object>) addressObject;
            Address addr = new Address();
            addr.ParentId = uow.location.Id;                        // REQUIRED, insert-only (Location inserted in step 2)
            addr.PRM_AddressLine1__c = (String) a.get('addressLine1');
            addr.PRM_AddressLine2__c = (String) a.get('addressLine2');
            addr.PRM_City__c = (String) a.get('city');
            addr.PRM_State__c = (String) a.get('state');            // 2-letter picklist (org)
            addr.PRM_Zip__c = (String) a.get('zip');
            addr.PRM_AddressType__c = (String) a.get('addressType');// multipicklist accepts a single value (OQ-E13-9)
            addr.PRM_EffectiveFrom__c = asDate(uow.node.get('effectiveFrom')); // REQUIRED
            addr.PRM_Pending__c = false;                            // REQUIRED
            addr.PRM_CaseManager__c = uow.caseManagerId;
            // Optional org fields if present: PRM_Zip4__c, PRM_County__c, PRM_Phone__c, PRM_PhoneExtension__c, PRM_Fax__c
            putIfField(addr, 'PRM_Zip4__c', a.get('zip4'));
            putIfField(addr, 'PRM_County__c', a.get('county'));
            putIfField(addr, 'PRM_Phone__c', a.get('phone'));
            putIfField(addr, 'PRM_PhoneExtension__c', a.get('phoneExt'));
            putIfField(addr, 'PRM_Fax__c', a.get('fax'));
            uow.addresses.add(addr);
        }
    }

    private void buildFacility(LocationUnitOfWork uow) {
        Map<String, Object> n = uow.node;
        HealthcareFacility hcf = new HealthcareFacility();
        hcf.Name = (String) n.get('practiceName');                 // required
        hcf.AccountId = uow.accountId;                             // group/vendor Account (E3) — required
        hcf.LocationId = uow.location.Id;
        hcf.PRM_NpiId__c = uow.locationNpiId;                      // -> trigger creates the Location NPI History
        hcf.PRM_PracticeName__c = (String) n.get('practiceName');
        hcf.PRM_Primary__c = asBool(n.get('primaryPracticeLoc'));  // REQUIRED
        hcf.PRM_PracticeClassification__c = (String) n.get('practiceClassification'); // source §5.1 (Professional/Facility)
        hcf.PRM_Pending__c = false;                                // REQUIRED
        hcf.PRM_CaseManager__c = uow.caseManagerId;
        // ⚠ Do NOT set PRM_ExternalId__c — the trigger (populatePRMExternalId) owns it.
        // TODO Pending Clarification (OQ-E13-7): PRM_BillingType__c ('UB'/'1500') — not in source.
        uow.facility = hcf;
    }

    private Map<String, Object> buildResponse(List<LocationUnitOfWork> unitsOfWork) {
        List<Object> results = new List<Object>();
        for (LocationUnitOfWork uow : unitsOfWork) {
            List<Id> addressIds = new List<Id>();
            for (Address addr : uow.addresses) {
                addressIds.add(addr.Id);
            }
            results.add(new Map<String, Object>{
                'locationId' => uow.location.Id,
                'addressIds' => addressIds,
                'healthcareFacilityId' => uow.facility.Id,
                'locationNpiId' => uow.locationNpiId
            });
        }
        response = new Map<String, Object>{ 'locations' => results };
        return response;
    }

    // ── helpers (pure) ──
    private static String strOf(Map<String, Object> m, String key) {
        Object v = (m == null) ? null : m.get(key);
        return (v == null) ? '' : String.valueOf(v);
    }
    private Boolean asBool(Object value) { return value == null ? false : (Boolean) value; }
    private Date asDate(Object value) {
        if (value == null) { return null; }
        if (value instanceof Date) { return (Date) value; }
        return String.isBlank(String.valueOf(value)) ? null : Date.valueOf(String.valueOf(value)); // expects yyyy-MM-dd
    }
    private void putIfField(SObject rec, String field, Object value) {
        if (value != null && String.isNotBlank(String.valueOf(value))) {
            rec.put(field, String.valueOf(value));
        }
    }
}
```

**`PRM_HealthcareFacilityCreationService.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> Keep in sync with `E13…md`. Open items (OQ‑E13‑6/7/9/12/18/19) still apply — **especially `LocationType` (OQ‑E13‑6) and `Account.SourceSystemIdentifier` (OQ‑E13‑18).**

---

## Appendix B — Apex test class `PRM_HealthcareFacilityCreationServiceTest` (+ meta)

> Reuses `PRM_TestDataFactory` + modern `Assert`. The test **plays the batch's role** (passes only new locations + injected `accountId`/`caseManagerId`/`locationNpiId`). **⚠ Test data (OQ‑E13‑15):** a group `Account` with `SourceSystemIdentifier`, a Case Manager (`IndividualApplication`), and a location `HealthcareProviderNpi`. The **HealthcareFacility trigger runs in tests** → its dependencies must be satisfiable.

```apex
@isTest
private class PRM_HealthcareFacilityCreationServiceTest {

    private static Map<String, Object> primaryAddress() {
        return new Map<String, Object>{
            'addressType' => 'Primary', 'addressLine1' => '1450 Marlton Pike E', 'addressLine2' => 'Ste 200',
            'city' => 'Cherry Hill', 'state' => 'NJ', 'zip' => '08034', 'zip4' => '2143',
            'phone' => '8565550199', 'phoneExt' => '210', 'fax' => '8565550200'
        };
    }

    private static Map<String, Object> locationNode(Id accountId, Id caseManagerId, Id npiId) {
        return new Map<String, Object>{
            'accountId' => accountId, 'caseManagerId' => caseManagerId, 'locationNpiId' => npiId,
            'practiceName' => 'Riverbend Family Health - Cherry Hill',
            'locationType' => 'Practice',                         // OQ-E13-6 (test value)
            'telehealthOnly' => false,
            'primaryPracticeLoc' => true,
            'practiceClassification' => 'Professional',
            'effectiveFrom' => Date.today(),
            'addresses' => new List<Object>{ primaryAddress() }
        };
    }

    @isTest
    static void shouldBuildExternalId_MatchingTriggerFormula() {
        Map<String, Object> addr = primaryAddress();
        Id npiId = '0Ex000000000001AAA';   // shape only
        String key = PRM_HealthcareFacilityCreationService.buildFacilityExternalId('274591038-Riverbend', npiId, 'Professional', addr);
        Assert.areEqual('274591038-Riverbend-' + npiId + '-Professional-1450 Marlton Pike E-Ste 200-08034-8565550199', key,
            'buildFacilityExternalId must reproduce populatePRMExternalId exactly');
    }

    @isTest
    static void shouldCreateLocationGraph_AndTriggerSideEffects() {
        // ⚠ OQ-E13-15: builders for group Account (+ SourceSystemIdentifier), Case Manager, and location NPI.
        Account grp = PRM_TestDataFactory.createVendorAccount('274591038-Riverbend');       // sets SourceSystemIdentifier
        IndividualApplication cm = PRM_TestDataFactory.createCaseManagers(1)[0];
        HealthcareProviderNpi npi = PRM_TestDataFactory.createOrgNpi('1801234561');          // NpiType='Organization'

        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'Practitioner Creation',
            'locations' => new List<Object>{ locationNode(grp.Id, cm.Id, npi.Id) }
        };

        Test.startTest();
        Integer soqlBefore = Limits.getQueries();
        Map<String, Object> resp = (Map<String, Object>) new PRM_HealthcareFacilityCreationService().execute(params);
        Integer serviceSoql = Limits.getQueries() - soqlBefore;   // includes the trigger's SOQL
        Test.stopTest();

        Assert.areEqual(1, [SELECT COUNT() FROM Location], 'One Location');
        Assert.areEqual(1, [SELECT COUNT() FROM Address], 'One Address');
        HealthcareFacility hcf = [SELECT Id, PRM_NpiId__c, PRM_ExternalId__c FROM HealthcareFacility LIMIT 1];
        Assert.areEqual(npi.Id, hcf.PRM_NpiId__c, 'HCF.PRM_NpiId__c set by E13');
        Assert.isNotNull(hcf.PRM_ExternalId__c, 'HCF.PRM_ExternalId__c populated by the trigger');
        Assert.areEqual(1, [SELECT COUNT() FROM PRM_HealthcareFacilityNPI__c WHERE PRM_HealthcareFacility__c = :hcf.Id],
            'Location NPI History created by the trigger (createNPIRecords)');
        Assert.areEqual(1, ((List<Object>) resp.get('locations')).size(), 'One response row');
    }

    @isTest
    static void shouldReturnEmpty_WhenNoLocations() {
        Test.startTest();
        Map<String, Object> resp = (Map<String, Object>) new PRM_HealthcareFacilityCreationService()
            .execute(new Map<String, Object>{ 'flow' => 'x', 'locations' => new List<Object>() });
        Test.stopTest();
        Assert.areEqual(0, ((List<Object>) resp.get('locations')).size(), 'Empty input -> empty response');
    }

    @isTest
    static void shouldThrow_WhenInjectedContextMissing() {
        Map<String, Object> params = new Map<String, Object>{
            'flow' => 'x',
            'locations' => new List<Object>{ new Map<String, Object>{ 'practiceName' => 'No context' } }
        };
        Test.startTest();
        try {
            new PRM_HealthcareFacilityCreationService().execute(params);
            Assert.fail('Expected an exception for missing injected accountId/locationNpiId');
        } catch (PRM_HealthcareFacilityCreationService.PRM_HCFException e) {
            Assert.isTrue(e.getMessage().contains('accountId'), 'Clear missing-context error');
        }
        Test.stopTest();
    }
}
```

**`PRM_HealthcareFacilityCreationServiceTest.cls-meta.xml`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

> **Test matrix:** `buildFacilityExternalId` exactness, location‑graph create + **trigger side‑effects** (NPI History + external id), empty input, missing‑context negative. Coverage ≥ 85%. ⚠ Confirm/add the flagged `PRM_TestDataFactory` builders (OQ‑E13‑15) and that the HealthcareFacility trigger + its deps run cleanly in tests.

---

## Appendix C — Deployment & validation (commands)

> Run against the confirmed target org (OQ‑E13‑16) **with the HealthcareFacility trigger active**. **No metadata/field deploys** — E13 uses existing fields.

```bash
# 1) Deploy the service + test class
sf project deploy start \
  -d "force-app/main/default/classes/PRM_HealthcareFacilityCreationService.cls" \
  -d "force-app/main/default/classes/PRM_HealthcareFacilityCreationServiceTest.cls" \
  -o <alias>

# 2) Run tests with coverage
sf apex run test --class-names PRM_HealthcareFacilityCreationServiceTest \
  --result-format human --code-coverage --target-org <alias>

# 3) Spot-check the graph + trigger side-effects
sf data query -o <alias> -q "SELECT Id, Name, PRM_ExternalId__c, PRM_NpiId__c, LocationId, AccountId FROM HealthcareFacility ORDER BY CreatedDate DESC LIMIT 5"
sf data query -o <alias> -q "SELECT Id, PRM_HealthcareFacility__c, PRM_HealthcareProviderNPI__c, PRM_ExternalId__c FROM PRM_HealthcareFacilityNPI__c ORDER BY CreatedDate DESC LIMIT 5"
```

**Pre‑deploy validation checklist:**

- [ ] OQ‑E13‑18 (`Account.SourceSystemIdentifier` on the group Account) confirmed/fixed in E3.
- [ ] OQ‑E13‑19 (trigger cascade) documented; batch size tuned for the trigger's SOQL/DML.
- [ ] OQ‑E13‑4b (batch gate: NPI→composite→pre‑check→new only) confirmed → service stays SOQL‑free.
- [ ] OQ‑E13‑6 (`LocationType` + `Location.Name`) + OQ‑E13‑7 (`PRM_BillingType__c`) + OQ‑E13‑12 (email/DBA/capabilities) resolved or injected.
- [ ] Target org confirmed **with the HealthcareFacility trigger active** (OQ‑E13‑16).
- [ ] `PRM_TestDataFactory` builders exist (group Account + `SourceSystemIdentifier`, Case Manager, location NPI) (OQ‑E13‑15).
- [ ] `buildFacilityExternalId` matches the trigger output; **0 service SOQL**; Address inserted before HealthcareFacility.
- [ ] Trigger side‑effects verified (NPI History + external id); Tests green ≥ 85%; Test Evidence Report + human sign‑off (Epic A §A7).
