# Future-Dated Termination Push-Out — Detailed Unit Test Scenarios

**Story:** Future-Dated Termination — Push-Out & Post-Termination Edits (see `requirements/FutureDated_Termination_PushOut_AddressUpdate_UserStory.md`)
**Targeted ACs:**

- **AC1** — Termination Date "Push-Out" Support: parent + cascaded children + FDP staging records all move to the new date.
- **AC2** — Independent Child Record Date Protection: a child with its own (independently-set) earlier termination date must NOT be extended when the parent is pushed out.

**Audience:** Apex devs writing `@isTest` methods, LWC devs writing Jest tests, and OmniStudio devs writing IP-level tests.

---

## 1. Code Surface Under Test

This is the minimum set of classes / methods that MUST have new push-out test coverage. Each method's "monotonic pull-in only" guard is the buggy line to assert against.

| Class | Method(s) | Pattern Variant | Test Class |
|---|---|---|---|
| `PRM_AccountTerminationBatchHelper` | `getVendorAccount`, `transformFacilityData`, `transformLocationData`, `transformAccountData`, `getIdentifier`, `getHcProvider`, `getAddressData`, `getIFCForVendor`, `getIFCForPracLoc`, `getProgPartForVendor`, `getProgPartForFacility`, `getHCFAssocData`, `getHCFBundleAssocData`, `getHcPracFacForPracLoc`, `getHcProviderNPI`, `getProviderTaxonomy`, `getHcProvider(Set<Id>)`, `getPractitonerNPI`, `getBoardCertifications`, `getPractitionerIFC`, `getHCPractitionerFacility`, `getNetworkDataForPractitioner`, `getAdmittingPrivileges`, `getPracProviderTaxonomy`, `getPractitionerIdentifier` | Form A (parent `>=`) + Form B (child `<`) | `PRM_AccountTerminationBatchTest` |
| `PRM_PractitionerTerminationBatchHelper` | `setTermDataPractitioner`, `getPractitionerNetwork`, `getPractitonerNPI`, `getBoardCertifications`, `getPractitionerIdentifier`, `getPractitionerIFC`, `getHCPractitionerFacility`, `getAdmittingPrivileges`, `getPracProviderTaxonomy`, `getPractitionerPracticeToPractitioner` | Form A (parent `>=`) + Form B (child `<`) | `PRM_FullPractitionerTerminationBatchTest` |
| `PRM_CrossRefBatchHelper` | `terminateFacilityAndRelations`, `terminateAssociations`, `terminateFacNetworks`, `terminatePPL`, `termContactMethod`, `termInfoCodeAssign`, `termProgPart`, `termHCProvider`, `termIdentifier`, `termPracAccNPI` | SOQL `OR PRM_EffectiveTo__c > :effDate` filter (push-out candidates filtered out) + Form B guard | `PRM_CrossRefBatchTest` |
| `PRM_PracLocTermHelper` | All `getXxx` methods (lines 183, 201, 218, 235, 255, 309, 328, 373, 425, 442, 458, 476, 494) | Form B | `PRM_PracLocTerminationUtilityPDMTest` |
| `PRM_ManualUpdatePracLocTerminationBatch` | `execute()` HCF & Location update expressions | Form A | (new test class) |
| `PRM_RCATTerminationBatchHelper`, `PRM_RCATTerminationEffectivityHelper`, `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch` | RCAT termination cascade | Form A + Form B | `PRM_RCATTerminationBatchHelperTest` |
| `PRM_FullPracTerminationRecredBatch`, `PRM_FullPracTermForFacilityBatch`, `PRM_FullPracTermForFacilityRecredBatch`, `PRM_AccountTerminationInitialCredUtility`, `PRM_AccountTermInitalCredService`, `PRM_PractitionerTermInitalCredService`, `PRM_ProvChangeTerminationBatch` | Per-flow batch | Form A + Form B | corresponding `*Test` classes |
| `PRM_FutureDatedProcessingUtil` | `createRecords` (External-Id upsert) | n/a — this is the convergence point | `PRM_FutureDatedProcessingUtilTest` |
| `PRM_FutureDatedProcessingBatchHandler` | `deleteRedundentRecords` | n/a — must not delete needed future FDP rows | `PRM_FutureDatedProcessingBatchHandlerTest` |

> **Test Constant Convention** — every scenario below uses the same symbolic dates so reviewers can correlate scenarios fast:
> - `TODAY` = `System.today()`
> - `OLD_TERM_DATE` = `TODAY.addDays(60)` (e.g., 2026-02-01)
> - `NEW_TERM_DATE` = `TODAY.addDays(90)` (e.g., 2026-03-01) — push-out case
> - `EARLIER_TERM_DATE` = `TODAY.addDays(30)` — pull-in case
> - `INDEP_CHILD_TERM` = `TODAY.addDays(45)` — independent child date (earlier than OLD parent)
> - `LATE_CHILD_TERM` = `TODAY.addDays(120)` — independent child date (later than OLD parent)
> - `EFF_FROM` = `TODAY.addDays(-30)`

---

## 2. Test Suite A — Account (Vendor) Termination Push-Out

**Flow under test:** `PRM_AccountTerminationForm_English_*` OmniScript → `PRM_AccountTerminationUtility.AccountTerminationBatch` → `PRM_AccountTerminationBatch` → `PRM_AccountTerminationBatchHelper`.

**Cascade target objects** (every one of these MUST be re-asserted in each test that pushes a Vendor Account):

1. `Account` (Vendor) — `PRM_EffectiveTo__c`
2. `HealthcareProvider` (Account-level) — `EffectiveTo`
3. `Identifier` (TaxID, etc.) — `PRM_EffectiveTo__c`
4. `HealthcareFacility` (every PL on this Vendor) — `PRM_EffectiveTo__c`
5. `Schema.Location` (1-to-1 with each HCF) — `PRM_EffectiveTo__c`
6. `Schema.Address` (Primary / Billing / Mailing on each Location) — `PRM_EffectiveTo__c`
7. `HealthcareFacilityNetwork` (Networks on each PL — recordType `PRM_FacilityNw`, `PRM_FacilityPractitionerTxNw`, `PRM_FacilityTx`) — `EffectiveTo`
8. `PRM_HealthcareFacilityAssociation__c` — `PRM_EffectiveTo__c`
9. `PRM_HealthcareFacilityBundleAssociation__c` — `PRM_EffectiveTo__c`
10. `PRM_InfoCodeAssignment__c` (Vendor-level + per-PL) — `PRM_EffectiveTo__c`
11. `PRM_ProgramParticipation__c` (Vendor-level + per-PL) — `PRM_EffectiveTo__c`
12. `HealthcarePractitionerFacility` (PPL on each PL) — `EffectiveTo`
13. `HealthcareProviderNpi` (NPI on the Vendor or shared) — `EffectiveTo`
14. `HealthcareProviderTaxonomy` — `EffectiveTo`
15. `PRM_ContactMethod__c` (Phone on PL) — `PRM_EffectiveTo__c`
16. `PRM_FutureDatedProcessing__c` (one Terminate row per record above; External Id `{recordId}_Terminate`)

### A1 — AC1 Happy Path: Vendor push-out, all-aligned children

**Setup**

| Record | `PRM_EffectiveTo` / `EffectiveTo` |
|---|---|
| Vendor Account | `OLD_TERM_DATE` |
| HealthcareProvider | `OLD_TERM_DATE` |
| Identifier (TaxID) | `OLD_TERM_DATE` |
| HealthcareFacility (PL) | `OLD_TERM_DATE` |
| Location | `OLD_TERM_DATE` |
| Address (Primary) | `OLD_TERM_DATE` |
| HCFN (PRM_FacilityNw) | `OLD_TERM_DATE` |
| HCFAssoc | `OLD_TERM_DATE` |
| HCFBundleAssoc | `OLD_TERM_DATE` |
| IFC (PRM_InfoCodeAssignment) | `OLD_TERM_DATE` |
| ProgramParticipation | `OLD_TERM_DATE` |
| HPF (PPL) | `OLD_TERM_DATE` |
| NPI | `OLD_TERM_DATE` |
| FDP row (Terminate) per record above | `OLD_TERM_DATE` |

**Action**: Invoke `PRM_AccountTerminationBatch` with `accountTerminationDate = NEW_TERM_DATE` and `typeOfTermination = 'Full-Termination'`.

**Expected**

1. Every one of the 13 sObjects above has `PRM_EffectiveTo__c` / `EffectiveTo` = `NEW_TERM_DATE`.
2. `PRM_FutureDatedProcessing__c` query: `PRM_Status__c = 'Terminate' AND PRM_SObjectRecordId__c IN :allRecordIds` — every row has `PRM_EffectiveDate__c = NEW_TERM_DATE`. ZERO rows still on `OLD_TERM_DATE`.
3. `Account.IsActive = true` (since `NEW_TERM_DATE > TODAY`).
4. `Account.PRM_IsErrorRecord__c = false`.
5. Bell notification sent to Case Owner with old → new dates.

**Assertion (Apex)**:

```apex
Account a = [SELECT PRM_EffectiveTo__c, PRM_IsErrorRecord__c, IsActive FROM Account WHERE Id = :vendorAccount.Id];
System.assertEquals(NEW_TERM_DATE, a.PRM_EffectiveTo__c, 'Vendor must be pushed out');
System.assertEquals(false, a.PRM_IsErrorRecord__c);
System.assertEquals(true, a.IsActive);

Integer staleFdp = [SELECT COUNT() FROM PRM_FutureDatedProcessing__c WHERE PRM_Status__c = 'Terminate' AND PRM_EffectiveDate__c = :OLD_TERM_DATE AND PRM_Processed__c = false];
System.assertEquals(0, staleFdp, 'No FDP row may remain on the original termination date');

Integer freshFdp = [SELECT COUNT() FROM PRM_FutureDatedProcessing__c WHERE PRM_Status__c = 'Terminate' AND PRM_EffectiveDate__c = :NEW_TERM_DATE AND PRM_Processed__c = false];
System.assertEquals(expectedRecordCount, freshFdp, 'Every cascaded record must have its FDP rewritten');
```

**Why this matters:** This single test catches the entire defect family on the Vendor path.

---

### A2 — AC1 Pull-in regression: Vendor pull-in (existing date 5/1, new date 3/1)

**Action**: Same as A1, but `accountTerminationDate = EARLIER_TERM_DATE` (where `OLD_TERM_DATE > EARLIER_TERM_DATE`).

**Expected** (must still pass — this is the legacy behavior):

1. Every record's `EffectiveTo` = `EARLIER_TERM_DATE`.
2. FDP rows all updated to `EARLIER_TERM_DATE`.

---

### A3 — AC2 Independent earlier child: Network removed 10/1, push PL/Vendor

**This is exactly the user's example.**

**Setup**

| Record | `EffectiveTo` |
|---|---|
| Vendor Account | `TODAY.addDays(180)` (1/1/2027) |
| HealthcareFacility (PL) | `TODAY.addDays(180)` (1/1/2027) |
| Location | `TODAY.addDays(180)` |
| **`HealthcareFacilityNetwork` (HCFN)** | **`TODAY.addDays(120)`** (10/1/2026 — INDEPENDENTLY SET EARLIER by a prior Network-removal flow) |
| FDP rows | one Terminate row per record at its own date |

**Action**: Re-run Account Termination flow with `accountTerminationDate = TODAY.addDays(540)` (1/1/2028 — push out PL effective to 1/1/2028).

**Expected** (CRITICAL):

1. `Account.PRM_EffectiveTo__c = 1/1/2028`
2. `HealthcareFacility.PRM_EffectiveTo__c = 1/1/2028`
3. `Location.PRM_EffectiveTo__c = 1/1/2028`
4. **`HealthcareFacilityNetwork.EffectiveTo = 10/1/2026` (UNCHANGED)** — the network was terminated independently EARLIER than both the OLD and the NEW parent date; the parent push-out must NOT touch it.
5. `PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :hcfn.Id` → still has `PRM_EffectiveDate__c = 10/1/2026` (unchanged; no DML on HCFN means no trigger fire means no FDP upsert).
6. Audit warning surfaced on the Case: "1 child record kept its independently-set termination date: HealthcareFacilityNetwork ['Test Nw'] = 10/1/2026."

**Assertion**:

```apex
HealthcareFacilityNetwork hcfnAfter = [SELECT EffectiveTo FROM HealthcareFacilityNetwork WHERE Id = :hcfn.Id];
System.assertEquals(Date.newInstance(2026, 10, 1), hcfnAfter.EffectiveTo, 'Network independently terminated EARLIER must be preserved');

PRM_FutureDatedProcessing__c hcfnFdp = [SELECT PRM_EffectiveDate__c FROM PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :hcfn.Id AND PRM_Status__c = 'Terminate'];
System.assertEquals(Date.newInstance(2026, 10, 1), hcfnFdp.PRM_EffectiveDate__c, 'HCFN FDP staging row must remain at original date');
```

---

### A4 — AC2 Independent later child: Identifier termination 4/1, push Vendor 5/1

**Setup**

| Record | `EffectiveTo` |
|---|---|
| Vendor Account | `OLD_TERM_DATE` (2/1/2026) |
| Identifier (TaxID) | **`TODAY.addDays(120)`** (4/1/2026 — independently set LATER than parent) |
| All other children | `OLD_TERM_DATE` |

**Action**: `accountTerminationDate = TODAY.addDays(150)` (5/1/2026).

**Expected:**

1. `Account.PRM_EffectiveTo__c = 5/1/2026`
2. All "aligned-to-old-date" children = `5/1/2026`.
3. **`Identifier.PRM_EffectiveTo__c = 4/1/2026` (UNCHANGED)** — child terminates earlier independently; do not extend it.
4. Identifier FDP row: `PRM_EffectiveDate__c = 4/1/2026` (unchanged).
5. UI warning: "Identifier ['TaxID 12345'] kept its independent termination date 4/1/2026."

**Boundary note:** This is the same code path as A3 but exercises the `(existing != null && existing < newTermDate ? existing : newTermDate)` branch where `existing < newTermDate` — must hit the "keep existing" branch.

---

### A5 — AC2 Mixed independent-earlier + aligned + independent-later in one cascade

**Setup**

| Record | `EffectiveTo` |
|---|---|
| Vendor Account | `OLD_TERM_DATE` |
| HealthcareFacility | `OLD_TERM_DATE` (aligned) |
| Location | `OLD_TERM_DATE` (aligned) |
| Address (Primary) | `OLD_TERM_DATE` (aligned) |
| HCFN (FacilityNw) | `INDEP_CHILD_TERM` (45 days — independent earlier) |
| HCFAssoc | `LATE_CHILD_TERM` (120 days — independent later) |
| IFC | `OLD_TERM_DATE` (aligned) |
| ProgramParticipation | `LATE_CHILD_TERM` (independent later) |
| Identifier | `INDEP_CHILD_TERM` (independent earlier) |
| HPF | `OLD_TERM_DATE` (aligned) |

**Action**: Push to `NEW_TERM_DATE` (90 days).

**Expected (one assert per child — be explicit):**

| Record | Expected `EffectiveTo` | Reason |
|---|---|---|
| Vendor Account | `NEW_TERM_DATE` | Parent pushed |
| HCF | `NEW_TERM_DATE` | Aligned — re-stamp |
| Location | `NEW_TERM_DATE` | Aligned — re-stamp |
| Address | `NEW_TERM_DATE` | Aligned — re-stamp |
| HCFN | **`INDEP_CHILD_TERM`** | Independent earlier — protect |
| HCFAssoc | **`LATE_CHILD_TERM`** | Independent later — protect (do NOT extend) |
| IFC | `NEW_TERM_DATE` | Aligned — re-stamp |
| ProgramParticipation | **`LATE_CHILD_TERM`** | Independent later — protect |
| Identifier | **`INDEP_CHILD_TERM`** | Independent earlier — protect |
| HPF | `NEW_TERM_DATE` | Aligned — re-stamp |

**FDP-level assertion:** Query `PRM_FutureDatedProcessing__c` grouped by `PRM_SObjectRecordId__c`, assert each `PRM_EffectiveDate__c` matches the table.

---

### A6 — Convert-to-Non-Par push-out (Vendor)

**Setup**: `Account.PRM_NonParticipatingStartDate__c = OLD_TERM_DATE`, `Account.PRM_ParticipationStatus__c = 'Non-Par'`, all children with their non-par-aligned `EffectiveTo`.

**Action**: Re-run with `typeOfTermination = 'Convert to Non-Participating'`, `accountTerminationDate = NEW_TERM_DATE`.

**Expected**:

1. `Account.PRM_NonParticipatingStartDate__c = NEW_TERM_DATE`.
2. `Account.PRM_ParticipationStatus__c = 'Non-Par'`.
3. `Account.PRM_EffectiveTo__c` unchanged (Non-Par does not set EffectiveTo on the Vendor).
4. Practitioner cascade (`PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner(false)`) pivots `PRM_NonParticipatingStartDate__c` not `PRM_EffectiveTo__c` — confirm.
5. FDP rows realigned where applicable.

---

### A7 — Switch termination type during push-out

**Setup**: Same as A6 (Vendor in Non-Par with date 2/1).

**Action**: Re-run with `typeOfTermination = 'Full-Termination'`, `accountTerminationDate = NEW_TERM_DATE`.

**Expected**:

1. `Account.PRM_EffectiveTo__c = NEW_TERM_DATE` (Full-Term now applies).
2. `Account.PRM_NonParticipatingStartDate__c = null` (cleared per `setTermDataPractitioner(isFull=true)`).
3. `Account.PRM_ParticipationStatus__c = null` (per `getVendorAccount` L20).
4. FDP rows: Terminate rows on NEW_TERM_DATE created for every record that didn't have one before (previously Non-Par didn't populate `PRM_EffectiveTo__c`).

---

### A8 — Same date no-op

**Setup**: Vendor + children all on `OLD_TERM_DATE`.
**Action**: `accountTerminationDate = OLD_TERM_DATE`.
**Expected**: No DML errors. No FDP rows change `Id` (upsert is idempotent — assert `LastModifiedDate` of FDP rows did NOT change). Use `Limits.getDmlStatements()` to confirm minimal DML.

---

### A9 — Past date (terminate immediately)

**Action**: `accountTerminationDate = TODAY` (or `TODAY.addDays(-1)`).

**Expected**:

1. Vendor + children get `EffectiveTo = TODAY`.
2. `IsActive = false` everywhere (because `EffectiveTo > TODAY` is FALSE).
3. FDP rows: All Terminate rows for these records are DELETED by `PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords` when the FDP batch next runs (or, if the trigger inserts an FDP row with `PRM_EffectiveDate__c = TODAY`, the batch picks it up immediately).
4. `Account.PRM_IsErrorRecord__c = false` only if `EffectiveFrom < TODAY`.

---

### A10 — Termination date < EffectiveFrom (validation)

**Setup**: Vendor `EffectiveFrom = TODAY.addDays(-5)`.
**Action**: `accountTerminationDate = TODAY.addDays(-10)`.
**Expected**:

1. `Account.PRM_IsErrorRecord__c = true`.
2. `Account.PRM_EffectiveTo__c = null`.
3. `Account.IsActive = false`.
4. (After fix) OmniScript-level validation error: "Termination date cannot be earlier than EffectiveFrom".

---

### A11 — Last-Man-Standing branch

**Setup**: Vendor + 1 active PL + 1 active practitioner on that PL.
**Action**: Push the Vendor; verify `PRM_FutureDatedProcessingUtil.createRecords` uses `PRM_Status__c = 'Terminate - Last Man Standing'` for the Vendor's Account FDP row (per line 99–108 of the util).

**Expected**:

1. `PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :vendor.Id AND PRM_Status__c = 'Terminate - Last Man Standing' AND PRM_EffectiveDate__c = NEW_TERM_DATE` — exactly 1 row.

---

## 3. Test Suite B — Practitioner Termination Push-Out

**Flows under test:**

- `PRM_PDMManualUpdatePractitioner_*` → `PRM_ManualUpdatePracLocTerminationBatch` → `PRM_PracLocTermHelper`
- `PRM_FullPractitionerTerminationBatch` → `PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner`
- RCAT post-recred: `PRM_RCATTerminationBatchHelper`

**Cascade target objects on a Practitioner (Person Account):**

1. `Account` (Practitioner Person Account) — `PRM_EffectiveTo__c` (Full-Term) OR `PRM_NonParticipatingStartDate__c` (Non-Par)
2. `HealthcareProvider` (linked by PractitionerId) — `EffectiveTo`
3. `HealthcareProviderNpi` (individual NPI) — `EffectiveTo`
4. `HealthcareProviderTaxonomy` — `EffectiveTo`
5. `BoardCertification` — `PRM_EffectiveTo__c`
6. `Identifier` (per practitioner — DEA, LicenseNumber, etc.) — `PRM_EffectiveTo__c`
7. `PRM_InfoCodeAssignment__c` (PRM_Account = practitioner) — `PRM_EffectiveTo__c`
8. `HealthcarePractitionerFacility` records:
   - `PRM_PractitionerLocationAffiliation` (PPL) — `EffectiveTo`
   - `PRM_AdmittingPrivileges` — `EffectiveTo`
   - `PRM_PractitionerPracticeAffiliation` — `EffectiveTo`
9. `HealthcareFacilityNetwork` (record type `PRM_FacilityPractitionerTxNw`) — `EffectiveTo`
10. `PRM_FutureDatedProcessing__c` rows for every above record.

### B1 — AC1 Full Practitioner push-out (happy path)

**Setup**: Practitioner Account + every cascade record above on `OLD_TERM_DATE`.

**Action**: `PRM_FullPractitionerTerminationBatch` with `termDate = NEW_TERM_DATE`, `isFull = true`.

**Expected**:

1. `Account.PRM_EffectiveTo__c = NEW_TERM_DATE`, `PRM_NonParticipatingStartDate__c = null`, `PRM_CredentialingStatus__c = 'Terminated'`, `PRM_ReCredDueDate__c = null`.
2. Every child sObject's `EffectiveTo` = `NEW_TERM_DATE`.
3. All FDP Terminate rows have `PRM_EffectiveDate__c = NEW_TERM_DATE`. **Zero** rows on `OLD_TERM_DATE`.
4. `BoardCertification.PRM_EffectiveTo__c = NEW_TERM_DATE` (note: BCert uses `PRM_EffectiveFrom__c` not `EffectiveFrom` per `PRM_FutureDatedProcessingUtil.getFieldApiName` BCert override).

### B2 — AC1 Practitioner Convert-to-Non-Par push-out

**Action**: Same as B1, but `isFull = false` (`PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner(acc, false, ...)`).
**Expected**:

1. `Account.PRM_NonParticipatingStartDate__c = NEW_TERM_DATE`.
2. `Account.PRM_ParticipationStatus__c = 'Non-Par'`.
3. `Account.PRM_EffectiveTo__c` UNCHANGED (Non-Par doesn't touch EffectiveTo).
4. Children that pivot on the Non-Par date (admitting privileges, PPL) — `EffectiveTo = NEW_TERM_DATE`.
5. Children that pivot on EffectiveTo (BoardCert, NPI) — UNCHANGED.

### B3 — AC2 Practitioner push-out with independent earlier license expiration

**Setup**: Practitioner + Identifier (LicenseNumber, type = License) with `PRM_EffectiveTo__c = TODAY.addDays(30)` (independent earlier — license expires before parent term).

**Action**: Push Practitioner Account from `OLD_TERM_DATE` to `NEW_TERM_DATE`.

**Expected**:

1. `Account.PRM_EffectiveTo__c = NEW_TERM_DATE`.
2. **`Identifier.PRM_EffectiveTo__c = TODAY.addDays(30)` (UNCHANGED)**.
3. Identifier FDP row: `PRM_EffectiveDate__c = TODAY.addDays(30)` (unchanged).

### B4 — AC2 Practitioner push-out with independent earlier BoardCertification

**Setup**: Practitioner + 1 BoardCert with `PRM_EffectiveTo__c = INDEP_CHILD_TERM` (board cert expired earlier than parent — independent).

**Action**: Push Practitioner `OLD_TERM_DATE` → `NEW_TERM_DATE`.

**Expected**:

1. Practitioner moves to `NEW_TERM_DATE`.
2. **BoardCert stays on `INDEP_CHILD_TERM`**.
3. FDP row for BoardCert stays on `INDEP_CHILD_TERM`.

### B5 — AC2 Practitioner push-out with independent earlier NPI (individual NPI expired)

**Setup**: Practitioner + HealthcareProviderNpi (NpiType = 'PRM_Individual') with `EffectiveTo = INDEP_CHILD_TERM`.

**Action**: Push Practitioner.

**Expected**: NPI `EffectiveTo` UNCHANGED (independent earlier).

### B6 — AC2 Practitioner push-out where one PL of three has an independent earlier termination on the PPL link

**Setup**: Practitioner with 3 PPL (HealthcarePractitionerFacility, record type `PRM_PractitionerLocationAffiliation`) records — PPL-1 and PPL-2 aligned to `OLD_TERM_DATE`; PPL-3 independently set to `INDEP_CHILD_TERM`.

**Action**: Push Practitioner from `OLD_TERM_DATE` to `NEW_TERM_DATE`.

**Expected**:

1. PPL-1, PPL-2: `EffectiveTo = NEW_TERM_DATE`.
2. **PPL-3: `EffectiveTo = INDEP_CHILD_TERM` (unchanged).**
3. The HCF, Vendor Account, NPI parents reachable through PPL-3 must NOT be cascaded.

### B7 — AC2 Practitioner — Admitting Privilege earlier than Practitioner term

**Setup**: Admitting Privilege (HPF record type `PRM_AdmittingPrivileges`) with `EffectiveTo = INDEP_CHILD_TERM`. Practitioner on `OLD_TERM_DATE`.

**Action**: Push Practitioner.

**Expected**: Admitting Privilege UNCHANGED on `INDEP_CHILD_TERM`. FDP row UNCHANGED.

### B8 — Full Practitioner Term where practitioner has 0 PPLs (edge — LMS)

**Setup**: Practitioner with no active PPLs.
**Expected**: Cascade still runs on Practitioner-direct child records (NPI, BoardCert, Taxonomy, Identifier, IFC). Skip PPL/HPF cascade gracefully. Method `setTermDataPractitioner` still called.

---

## 4. Test Suite C — Practice Location Termination Push-Out

**Flow under test:** `PRM_PracticeLocationTermination_English_*` OmniScript → `PRM_PracticeLocationTermination_Procedure_*` IP → `PRM_TerminatePracticeLocationNRelations` (batch) → `PRM_CrossRefBatchHelper.terminateFacilityAndRelations`.

**Cascade target objects (per PL):**

1. `HealthcareFacility` — `PRM_EffectiveTo__c`
2. `Schema.Location` — `PRM_EffectiveTo__c`
3. `Schema.Address` (Primary, Billing, Mailing) — `PRM_EffectiveTo__c`
4. `HealthcareFacilityNetwork` (record types `PRM_FacilityNw`, `PRM_FacilityPractitionerTxNw`, `PRM_FacilityTx`) — `EffectiveTo`
5. `PRM_HealthcareFacilityAssociation__c` — `PRM_EffectiveTo__c`
6. `PRM_HealthcareFacilityBundleAssociation__c` — `PRM_EffectiveTo__c`
7. `PRM_InfoCodeAssignment__c` — `PRM_EffectiveTo__c`
8. `PRM_ProgramParticipation__c` (direct + via `PRM_HealthcareFacilityNetwork`) — `PRM_EffectiveTo__c`
9. `PRM_ContactMethod__c` — `PRM_EffectiveTo__c`
10. `HealthcarePractitionerFacility` (PPL records) — `EffectiveTo`
11. `HealthcareProviderNpi` (if PL is the last active PL for this NPI) — `EffectiveTo`
12. `Account` (Vendor) — `PRM_EffectiveTo__c` (only if this PL is the last active PL on the Vendor)
13. Practitioner Account (if this PL is the last PL for the practitioner — via `terminatePPL` + `setTermDataPractitioner(false)`)
14. `PRM_FutureDatedProcessing__c` for every record above.

> **CRITICAL CODE-LEVEL ISSUE TO TEST:** Every SOQL in `PRM_CrossRefBatchHelper` (lines 68, 133, 158, 189, 219, 249, 313, 368, 405, 432, 495) has:
> ```
> AND (PRM_EffectiveTo__c = NULL OR PRM_EffectiveTo__c > :effectiveToDate)
> ```
> During push-out, records with `EffectiveTo` between `OLD_TERM_DATE` and `NEW_TERM_DATE` (i.e., `< effectiveToDate=NEW_TERM_DATE`) are FILTERED OUT and never updated. The fix needs to also pull `EffectiveTo = OLD_TERM_DATE` records. **Every C-suite test below must assert that records on the old date are picked up post-fix.**

### C1 — AC1 Happy path: PL push-out, all-aligned cascade

**Setup**: One PL with every child on `OLD_TERM_DATE`, including:

- 1 Address (Primary, Billing)
- 2 HCFN (1× FacilityNw, 1× FacilityPractitionerTxNw, 1× FacilityTx)
- 1 HCFAssoc, 1 HCFBundleAssoc
- 1 IFC, 1 ProgramParticipation
- 1 ContactMethod
- 1 HPF (PPL)

**Action**: Push PL termination to `NEW_TERM_DATE` via PracticeLocationTermination flow.

**Expected**:

1. All 12+ records have `EffectiveTo = NEW_TERM_DATE`.
2. **`PRM_CrossRefBatchHelper.terminateFacNetworks` updates the FacilityTx and its `PRM_ProgramParticipation__c` (via line 215) — assert both got the new date.**
3. **`PRM_CrossRefBatchHelper.terminatePPL` recomputes practnrVendorDate map correctly** — assert practitioner is non-par'd to `NEW_TERM_DATE` if this is the last PPL for the practitioner.
4. FDP staging: every record has a `Terminate` row at `NEW_TERM_DATE`. Zero on `OLD_TERM_DATE`.

### C2 — AC2 USER'S EXAMPLE (must pass): Network removed earlier, push PL out

**Setup** — matches user's exact scenario from the query:

| Record | `EffectiveTo` |
|---|---|
| PL (HCF) | `2027-01-01` (`OLD_TERM_DATE`) |
| Location | `2027-01-01` |
| Address (Primary) | `2027-01-01` |
| HCFAssoc | `2027-01-01` |
| **HCFN (Network)** | **`2026-10-01`** (independently removed via Network-Termination flow 3 months ago) |
| HPF (PPL) | `2027-01-01` |
| IFC | `2027-01-01` |

**Action**: Run Practice Location Termination flow with `effectiveToDate = 2028-01-01` (push PL out by 1 year).

**Expected**:

1. `HCF.PRM_EffectiveTo__c = 2028-01-01`.
2. `Location.PRM_EffectiveTo__c = 2028-01-01`.
3. `Address.PRM_EffectiveTo__c = 2028-01-01`.
4. `HCFAssoc.PRM_EffectiveTo__c = 2028-01-01`.
5. **`HealthcareFacilityNetwork.EffectiveTo = 2026-10-01` (UNCHANGED)** ← THIS IS THE KEY ASSERT.
6. `HPF.EffectiveTo = 2028-01-01`.
7. `IFC.PRM_EffectiveTo__c = 2028-01-01`.
8. `PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :hcfn.Id` → still `PRM_EffectiveDate__c = 2026-10-01`. Other rows = `2028-01-01`.

**Apex assertion (verbatim — devs can copy):**

```apex
@isTest
static void pushPLTermPreservesIndependentlyRemovedNetwork() {
    // --- Setup ---
    Account vendor = createVendor();
    Schema.Location loc = createLocation(System.today().addDays(-30), Date.newInstance(2027, 1, 1));
    HealthcareFacility hcf = createHCF(vendor, loc, Date.newInstance(2027, 1, 1));
    HealthcareFacilityNetwork hcfn = createHCFN(hcf, Date.newInstance(2026, 10, 1)); // independent earlier
    // ... other children all on 2027-01-01

    // --- Action ---
    Test.startTest();
    Date pushTo = Date.newInstance(2028, 1, 1);
    PRM_CaseDataManager__c cdm = new PRM_CaseDataManager__c();
    PRM_CrossRefBatchHelper.terminateFacilityAndRelations(
        new List<HealthcareFacility>{ new HealthcareFacility(Id = hcf.Id, PRM_EffectiveTo__c = pushTo, PRM_Active__c = true, AccountId = vendor.Id, LocationId = loc.Id, PRM_NpiId__c = null) },
        UserInfo.getUserId(), new List<Id>(), new List<Id>(), cdm, new Set<Id>{ hcf.Id }, pushTo
    );
    Test.stopTest();

    // --- Assertions ---
    HealthcareFacility hcfAfter = [SELECT PRM_EffectiveTo__c FROM HealthcareFacility WHERE Id = :hcf.Id];
    System.assertEquals(Date.newInstance(2028, 1, 1), hcfAfter.PRM_EffectiveTo__c, 'PL must be pushed out');

    HealthcareFacilityNetwork hcfnAfter = [SELECT EffectiveTo FROM HealthcareFacilityNetwork WHERE Id = :hcfn.Id];
    System.assertEquals(Date.newInstance(2026, 10, 1), hcfnAfter.EffectiveTo,
        'AC2: Network independently removed EARLIER than parent must remain on its original date');

    Schema.Location locAfter = [SELECT PRM_EffectiveTo__c FROM Schema.Location WHERE Id = :loc.Id];
    System.assertEquals(Date.newInstance(2028, 1, 1), locAfter.PRM_EffectiveTo__c, 'Location must cascade with PL');

    PRM_FutureDatedProcessing__c fdpHcfn = [SELECT PRM_EffectiveDate__c FROM PRM_FutureDatedProcessing__c
        WHERE PRM_SObjectRecordId__c = :hcfn.Id AND PRM_Status__c = 'Terminate' LIMIT 1];
    System.assertEquals(Date.newInstance(2026, 10, 1), fdpHcfn.PRM_EffectiveDate__c,
        'HCFN FDP staging row must remain at original date');
}
```

### C3 — AC2 PL push-out with billing Address independently terminated earlier (remittance change)

**Setup**: PL on `OLD_TERM_DATE`. Billing Address terminated 30 days ago via a remittance change (`PRM_EffectiveTo = INDEP_CHILD_TERM`, `PRM_Active = false`, `PRM_IsErrorRecord = false`).

**Action**: Push PL.

**Expected**:

1. PL cascades to `NEW_TERM_DATE`.
2. Billing Address `PRM_EffectiveTo__c` UNCHANGED.
3. Per `PRM_CrossRefBatchHelper` L73 — the `add.PRM_Active__c == false` branch flips `PRM_IsErrorRecord__c = true` but does NOT change `PRM_EffectiveTo__c`. **Confirm this branch fires AND no date change.**

### C4 — AC2 PL push-out where 1 of 4 HCFAssoc rows is independently terminated earlier

**Setup**: PL + 4 HCFAssoc. HCFAssoc-1 = `INDEP_CHILD_TERM`. HCFAssoc-2, 3, 4 = `OLD_TERM_DATE`.

**Action**: Push PL to `NEW_TERM_DATE`.

**Expected**:

1. HCFAssoc-1 UNCHANGED at `INDEP_CHILD_TERM`.
2. HCFAssoc-2, 3, 4 = `NEW_TERM_DATE`.
3. FDP rows match.

### C5 — AC2 PL push-out where PPL (HPF) was independently terminated earlier

**Setup**: 3 PPL records on the PL. PPL-1 = `INDEP_CHILD_TERM` (practitioner left this PL earlier). PPL-2, PPL-3 = `OLD_TERM_DATE`.

**Action**: Push PL.

**Expected**:

1. PPL-2, PPL-3 = `NEW_TERM_DATE`.
2. **PPL-1 UNCHANGED**.
3. `PRM_CrossRefBatchHelper.terminatePPL` `pracToPractitionerMap` does NOT include the practitioner from PPL-1 (or if it does, it does NOT push that practitioner's other PPLs to `NEW_TERM_DATE` based on PPL-1).

### C6 — Last-Man-Standing PL push-out cascades to Vendor and NPI

**Setup**: Vendor with ONE active PL. NPI shared with this PL only. Push the PL.
**Expected**:

1. PL `EffectiveTo = NEW_TERM_DATE`.
2. **Vendor Account `PRM_EffectiveTo__c = NEW_TERM_DATE`** (because `vendorTermMap` populated via line 38).
3. **NPI `EffectiveTo = NEW_TERM_DATE`** (since this is the last facility for the NPI per the AggregateResult HAVING Count = 1 query).
4. Vendor FDP row uses `PRM_Status__c = 'Terminate - Last Man Standing'`.

### C7 — PL push-out where Vendor has 2 PLs (cascade must NOT touch Vendor)

**Setup**: Vendor with 2 active PLs. Push PL-A.
**Expected**:

1. PL-A cascade as normal.
2. Vendor Account UNCHANGED.
3. NPI (if shared with PL-B too) UNCHANGED.
4. `vendorTermMap.remove(hcf.AccountId)` fires at line 108–109.

### C8 — PL push-out via PDM Manual Update (`PRM_ManualUpdatePracLocTerminationBatch`)

**Flow under test:** `PRM_PDMManualUpdatePractitioner_*` → `PRM_ManualUpdatePracLocTerminationBatch.execute()` (L212, L219, L298, L305).
**Setup**: Same as C1.
**Action**: Run the PDM Manual Update batch with new term date.
**Expected**: Same as C1 (PL + children + FDP all aligned).

### C9 — RCAT PL push-out (`PRM_RCATLocationTerminationBatch`)

**Flow under test:** RCAT post-recred PL termination.
**Setup**: PL terminated by RCAT batch on `OLD_TERM_DATE`. Re-run RCAT with `NEW_TERM_DATE`.
**Expected**: PL + cascade all on `NEW_TERM_DATE`. Verify `PRM_RCATTerminationEffectivityHelper` does NOT block the push-out.

### C10 — RCAT Network-only push-out (`PRM_RCATNetworkTerminationBatch`)

**Setup**: HCFN on `OLD_TERM_DATE`. Push standalone via RCATNetwork batch.
**Expected**:

1. HCFN moves to `NEW_TERM_DATE`.
2. `PRM_ProgramParticipation__c` linked to this HCFN ALSO moves.
3. Parent HCF / Vendor UNCHANGED (network-only push must NOT cascade up).

---

## 5. Test Suite D — FDP Staging Record Integrity (AC1 second clause)

These tests target `PRM_FutureDatedProcessingUtil.createRecords` and the FDP batch.

### D1 — External-Id upsert correctness

**Setup**: Record with `PRM_EffectiveTo = OLD_TERM_DATE`. FDP row inserted via trigger.
**Action**: Update record to `PRM_EffectiveTo = NEW_TERM_DATE` (after the helper-class fix).
**Expected**:

1. ONE FDP row exists with `PRM_ExternalId__c = '{recordId}_Terminate'`.
2. `PRM_EffectiveDate__c = NEW_TERM_DATE`.
3. The row's `Id` is the SAME as before (upsert by external id, not insert).

```apex
PRM_FutureDatedProcessing__c before = [SELECT Id, PRM_EffectiveDate__c FROM PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :rec.Id LIMIT 1];
// trigger push-out
PRM_FutureDatedProcessing__c after = [SELECT Id, PRM_EffectiveDate__c FROM PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :rec.Id LIMIT 1];
System.assertEquals(before.Id, after.Id, 'Same FDP row — must upsert by external id');
System.assertEquals(NEW_TERM_DATE, after.PRM_EffectiveDate__c);
```

### D2 — No duplicate FDP rows on rapid re-submission

**Action**: Submit termination, then immediately re-submit with a different date.
**Expected**: Exactly 1 `Terminate` FDP row per `PRM_SObjectRecordId__c`. No duplicates.

### D3 — `deleteRedundentRecords` does NOT delete future FDP rows

**Setup**: Two FDP rows for same record (different IDs, both future-dated). Run `PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords`.
**Expected**: NEITHER future-dated row is deleted (function only de-dupes rows with `EffectiveDate ≤ TODAY`). Add assertion guarding this so the eventual fix in §5.6 of the story is tested.

### D4 — FDP batch on OLD date doesn't pick up pushed-out records

**Setup**: Record pushed out from `OLD_TERM_DATE` to `NEW_TERM_DATE`. FDP row now at `NEW_TERM_DATE`. Set `System.today() = OLD_TERM_DATE` (use `Test.setFixedDate` or test seam).
**Action**: Run `PRM_FutureDatedProcessingBatch` for `OLD_TERM_DATE`.
**Expected**: Record NOT terminated. FDP row not processed (it's on `NEW_TERM_DATE`).

### D5 — FDP batch on NEW date picks up pushed-out records

**Setup**: Same as D4.
**Action**: Run FDP batch for `NEW_TERM_DATE`.
**Expected**: Record's `PRM_Active__c = false`, `IsActive = false`, FDP `PRM_Processed__c = true`.

### D6 — Last-Man-Standing FDP status

**Setup**: Vendor on `OLD_TERM_DATE` + one active PL (LMS condition true).
**Action**: Push Vendor.
**Expected**: Vendor's FDP row has `PRM_Status__c = 'Terminate - Last Man Standing'` (per `PRM_FutureDatedProcessingUtil` L99-108) with `PRM_EffectiveDate__c = NEW_TERM_DATE`.

### D7 — BoardCertification field-name override

**Setup**: BoardCertification with `PRM_EffectiveTo__c = OLD_TERM_DATE` (BCert uses custom field, not standard `EffectiveTo` per `PRM_FutureDatedProcessingUtil.getFieldApiName`).
**Action**: Push BoardCert.
**Expected**: FDP row created using `PRM_EffectiveTo__c` value. Don't regress the BCert special-case.

---

## 6. Test Suite E — `PRM_TerminationDateUtility` (new class per § 5.1 of the story)

Once `PRM_TerminationDateUtility.computeEffectiveTo(...)` exists, here are the parametric unit tests for the utility itself (fast, no DML required).

| # | `existing` | `requested` | `effectiveFrom` | `isErrorRecord` | `mode` | Expected |
|---|---|---|---|---|---|---|
| E1 | null | `NEW_TERM_DATE` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `NEW_TERM_DATE` |
| E2 | `OLD_TERM_DATE` | `NEW_TERM_DATE` (later) | `EFF_FROM` | false | `USER_RE_TERMINATION` | `NEW_TERM_DATE` (push-out!) |
| E3 | `OLD_TERM_DATE` | `EARLIER_TERM_DATE` (earlier) | `EFF_FROM` | false | `USER_RE_TERMINATION` | `EARLIER_TERM_DATE` (pull-in) |
| E4 | `OLD_TERM_DATE` | `OLD_TERM_DATE` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `OLD_TERM_DATE` |
| E5 | `INDEP_CHILD_TERM` (earlier than `NEW_TERM_DATE`) | `NEW_TERM_DATE` | `EFF_FROM` | false | `PARENT_CASCADE` | `INDEP_CHILD_TERM` (child kept) |
| E6 | `INDEP_CHILD_TERM` (earlier) | `NEW_TERM_DATE` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `NEW_TERM_DATE` (user overrides) |
| E7 | `LATE_CHILD_TERM` (later than `NEW_TERM_DATE`) | `NEW_TERM_DATE` | `EFF_FROM` | false | `PARENT_CASCADE` | `NEW_TERM_DATE` (pull child in) |
| E8 | `LATE_CHILD_TERM` (later) | `NEW_TERM_DATE` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `LATE_CHILD_TERM` (user push but child later — per AC1.7 of story, keep child later — confirm intent) |
| E9 | `OLD_TERM_DATE` | `NEW_TERM_DATE` | `EFF_FROM` | true | `USER_RE_TERMINATION` | null (error record → clear EffectiveTo) |
| E10 | null | `EFF_FROM.addDays(-1)` | `EFF_FROM` | false | `USER_RE_TERMINATION` | null (requested < EffectiveFrom → error) |
| E11 | `OLD_TERM_DATE` | `TODAY` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `TODAY` (terminate immediately) |
| E12 | `OLD_TERM_DATE` | `TODAY.addDays(-1)` | `EFF_FROM` | false | `USER_RE_TERMINATION` | `TODAY.addDays(-1)` (back-date allowed since `>= EFF_FROM`) |

> **Decision point for E8:** The story §4.1 AC1.7 says "Account moves to 5/1/2026 but Identifier stays at 4/1/2026" — i.e., the user's later date does NOT extend a child that's already terminating earlier. Confirm with Product before encoding this; if "USER_RE_TERMINATION = user owns ALL dates" then E8 returns `NEW_TERM_DATE`. Today's defect would say `LATE_CHILD_TERM` (child kept). Pick one and test it.

---

## 7. Test Suite F — Concurrency / Idempotency

### F1 — Two parallel pushes (last-write-wins via External-Id upsert)

**Setup**: One Vendor.
**Action**: Use `Test.startTest`/`stopTest` with `Database.executeBatch` invoking 2 batches at once (`AsyncMode` differs in test but simulate ordering).
**Expected**: One FDP row per record. `PRM_EffectiveDate__c` = whichever batch's date won (last-write). No `DUPLICATE_VALUE` exceptions.

### F2 — Re-run same flow twice with same date

**Action**: Submit, then submit again with the same date.
**Expected**: No DML errors. FDP row count unchanged. `LastModifiedDate` may bump but `PRM_EffectiveDate__c` unchanged.

### F3 — Push out then immediately reinstate (out of scope per story §6, but trap regressions)

**Setup**: Pushed-out Vendor.
**Action**: Set Vendor `PRM_EffectiveTo__c = null` via direct DML (no flow).
**Expected**: After the next trigger fire, the Vendor's FDP `Terminate` row should be processed/cancelled by a future cleanup job — for now, just assert the DML doesn't error and the FDP row still exists with the OLD date (cleanup is out of scope for this story but document the gap).

---

## 8. Test Suite G — OmniScript-Level Validation (UI / IP)

These run against the OmniScript / Integration Procedure layer; use `OmniScriptTestHelper` patterns.

### G1 — `PRM_AccountTerminationForm` prefills existing EffectiveTo

**Setup**: Vendor with `PRM_EffectiveTo__c = OLD_TERM_DATE`.
**Action**: Launch OmniScript on this Vendor.
**Expected**: `EndDate` step pre-populates with `OLD_TERM_DATE`. Banner shows "Account is scheduled to terminate on 2/1/2026."

### G2 — `PRM_PracticeLocationTermination` prefills existing EffectiveTo

Same as G1 but for `HealthcareFacility.PRM_EffectiveTo__c` and the PL OmniScript's `PLInfo:TerminateEffectiveTo` setvalue.

### G3 — OmniScript blocks submit when push-out goes earlier than EffectiveFrom

**Action**: Enter `endDate = TODAY.addDays(-365)` when `EffectiveFrom = TODAY.addDays(-10)`.
**Expected**: Inline validation error; submit disabled.

### G4 — IP `PRM_PracticeLocationTermination_Procedure_*` passes new date through to batch

**Setup**: Mock IP input `{ "PLInfo": { "TerminateEffectiveTo": "03/10/2028" } }`.
**Action**: Invoke IP.
**Expected**: `PRM_TerminatePracticeLocationNRelations` constructor is called with `effectiveToDate = 2028-03-10`. (Use the `vlocity_omniout` test harness or `Test.callRemoteAction` + mock.)

### G5 — IP cascades the new date to `terminateFacilityAndRelations`

Assert the value passed at line 46 of `PRM_TerminatePracticeLocationNRelations.execute()` is the post-push date, not the stale prior date from HCF (defensive — if HCF wasn't updated in step 1, the cascade would use stale data).

---

## 9. Test Suite H — Audit Trail & Notifications

### H1 — `PRM_AsyncProcess__c` row written

**Action**: Push Vendor.
**Expected**: 1 row with `PRM_SubType__c = 'FDTermination'` and references to old + new dates.

### H2 — `PRM_CaseDataManager__c` boolean flags

**Action**: Run CrossRef cascade.
**Expected** (per `terminateFacilityAndRelations` body):

- `cdm.PRM_HealthCareFacility__c = true`
- `cdm.PRM_Location__c = true`
- `cdm.PRM_Address__c = true` (if any addresses cascaded)
- `cdm.PRM_HealthcareFacilityNetwork__c = true` (if any HCFN cascaded — NOT true in C2 where HCFN was independent)
- `cdm.PRM_PracticeLocationAssociation__c = true` (if HCFAssoc cascaded)
- ...and so on per cascade scope.

### H3 — Bell notification copy

**Setup**: Push Vendor.
**Expected**: `PRM_NotificationHelper.sendBellNotification` called with title containing "Termination Date Updated" (per story §4.4 AC4.4). For this story, assert the call happens via mocked invocation count.

### H4 — Old date and new date both recorded on Case

**Expected**: One Case-level log entry per push-out, with both `OldTerminationDate` and `NewTerminationDate`.

---

## 10. Per-Flow Coverage Matrix (devs: each flow = at least 1 push-out + 1 AC2 test)

| Flow / Entry Point | AC1 Push-out Test | AC2 Independent-Child Test |
|---|---|---|
| `PRM_AccountTerminationBatch` (Full) | A1 | A3, A4, A5 |
| `PRM_AccountTerminationBatch` (Non-Par) | A6 | (extend A3 — set Non-Par instead of Full) |
| `PRM_AccountTerminationInitialCredBatch` | new test | new test |
| `PRM_AccountTermInitalCredService` | new test | new test |
| `PRM_FullPractitionerTerminationBatch` | B1 | B3, B4, B5, B6, B7 |
| `PRM_PractitionerTermInitalCredService` | new test | new test |
| `PRM_ManualUpdatePracLocTerminationBatch` (PDM) | C8 | (extend C8 with independent HCFN) |
| `PRM_TerminatePracticeLocationNRelations` → `PRM_CrossRefBatchHelper` | C1 | **C2 (user's example)**, C3, C4, C5, C6, C7 |
| `PRM_RCATTerminationBatchHelper` (post-recred Account) | new test | new test |
| `PRM_RCATLocationTerminationBatch` | C9 | (extend C9) |
| `PRM_RCATNetworkTerminationBatch` | C10 | n/a (network-only) |
| `PRM_FullPracTerminationRecredBatch` | new test | new test |
| `PRM_FullPracTermForFacilityBatch` | new test | new test |
| `PRM_FullPracTermForFacilityRecredBatch` | new test | new test |
| `PRM_ProvChangeTerminationBatch` | new test | new test |
| LMS auto-cascade `PRM_PPLLMSTermService` | (regression — must NOT enter USER_RE_TERMINATION mode) | confirm `PARENT_CASCADE` mode |

---

## 10A. Test Suite L — Last-Man-Standing (LMS) Push-Out Scenarios

LMS has **three distinct code paths** in this codebase. Push-out interacts with each one differently. Every scenario below must be a discrete `@isTest` method.

### Code paths summary

| Path | Class / Method | LMS Trigger | Date Source |
|---|---|---|---|
| LMS-A | `PRM_FutureDatedProcessingUtil.createRecords` (L54-58, L99-108) | Account FDP staging when `PRM_CountOfActivePractitioners__c == 1` on the related PL | `PRM_EffectiveTo__c` of Account |
| LMS-B | `PRM_PPLLMSTermService.processFacilities` (called from `PRM_TerminatePracticeLocationNRelations.finish` L86) | Primary PL terminating + other active PLs on same Account | `fac.PRM_EffectiveTo__c` (line 277 — strict equality vs Address `PRM_EffectiveTo__c`) |
| LMS-C | `PRM_CrossRefBatchHelper.terminateFacilityAndRelations` (L104-111) + `PRM_AccountTerminationBatchHelper.getHcProviderNPI` (L284-296) | Vendor / NPI cascades only if no other active siblings; uses `HAVING Count(Id) = 1` for shared NPI | `effectiveToDate` parameter |
| LMS-D | `PRM_LMSService.evaluateImpact` + `collectLmsLastManStandingUpdates` | Practitioner removed from facility making `PRM_CountOfActivePractitioners__c = 0` | `Date.today()` (immediate) |

---

### L1 — LMS-A: Vendor LMS FDP status preserved on push-out

**Setup**: Vendor with exactly 1 active PL, PL has 1 active practitioner (`PRM_CountOfActivePractitioners__c = 1`). Vendor `PRM_EffectiveTo__c = OLD_TERM_DATE`. Vendor FDP row exists with `PRM_Status__c = 'Terminate - Last Man Standing'`, `PRM_EffectiveDate__c = OLD_TERM_DATE`.

**Action**: Re-run Account Termination flow with `accountTerminationDate = NEW_TERM_DATE`.

**Expected**:

1. Vendor `PRM_EffectiveTo__c = NEW_TERM_DATE`.
2. Vendor FDP row (same `Id`, upserted by external id `{vendorId}_Terminate`):
   - `PRM_Status__c = 'Terminate - Last Man Standing'` (UNCHANGED — still LMS condition true).
   - `PRM_EffectiveDate__c = NEW_TERM_DATE`.
3. Zero rows on `OLD_TERM_DATE`.

**Why this is critical**: `PRM_FutureDatedProcessingUtil.createRecords` re-evaluates `PRM_CountOfActivePractitioners__c` at trigger time. If push-out triggers the util but the practice-count query returns the same value, the upsert correctly preserves LMS. Test that.

---

### L2 — LMS-A: LMS status downgrade when condition no longer holds

**Setup**: Vendor LMS-terminated at `OLD_TERM_DATE` (PL had 1 practitioner). Between OLD and TODAY, a NEW practitioner is added to that PL (`PRM_CountOfActivePractitioners__c = 2` now).

**Action**: Push Vendor termination from `OLD_TERM_DATE` to `NEW_TERM_DATE`.

**Expected**:

1. Vendor FDP row's `PRM_Status__c` MUST flip from `'Terminate - Last Man Standing'` to `'Terminate'` (LMS condition no longer holds at trigger time).
2. `PRM_EffectiveDate__c = NEW_TERM_DATE`.
3. The downstream batch on `NEW_TERM_DATE` will now process this as a regular Terminate, NOT LMS.

**LANDMINE**: `PRM_FutureDatedProcessingUtil` line 99 condition `(objApiName == ACCOUNTST && lstManStanding)` flips at trigger time. **Verify the upsert correctly downgrades the status** — if the upsert path fails to overwrite `PRM_Status__c`, you'll have a stale LMS row.

---

### L3 — LMS-A: LMS status upgrade when push-out causes new LMS condition

**Setup**: Vendor with 2 active PLs, neither LMS (status = `'Terminate'`). PL-A terminating `OLD_TERM_DATE`. PL-B independently terminating earlier `INDEP_CHILD_TERM`.

**Action**: Push Vendor + PL-A from `OLD_TERM_DATE` to `NEW_TERM_DATE`. PL-B left untouched.

**Expected**:

1. PL-A → `NEW_TERM_DATE`; PL-B → `INDEP_CHILD_TERM` (preserved).
2. After PL-B's date passes, `PRM_CountOfActivePractitioners__c` on the Vendor will eventually become 1 — but at the time of push-out, evaluate at trigger time.
3. If LMS condition holds AT trigger time → `'Terminate - Last Man Standing'`.
4. If not → `'Terminate'`.

**Document** the time-of-evaluation policy so QA can pin the assertion deterministically.

---

### L4 — LMS-B: Primary PL push-out, address cloning to new primary (the L277 brittle equality)

**Setup**:

- Vendor with 2 PLs: PL-A (Primary) and PL-B (Practice).
- PL-A `PRM_EffectiveTo__c = OLD_TERM_DATE`.
- PL-A's Location has Mailing + Billing addresses with `PRM_EffectiveTo__c = OLD_TERM_DATE` (aligned to PL-A).
- PL-B is active, no Mailing/Billing addresses yet.

**Action**: Push PL-A from `OLD_TERM_DATE` to `NEW_TERM_DATE` via PL Termination flow. After cascade, `PRM_TerminatePracticeLocationNRelations.finish()` calls `PRM_PPLLMSTermService.processFacilities`.

**Expected (after fix)**:

1. PL-A `PRM_EffectiveTo__c = NEW_TERM_DATE`.
2. PL-A's Mailing/Billing addresses `PRM_EffectiveTo__c = NEW_TERM_DATE` (cascade re-stamped).
3. `PRM_PPLLMSTermService` correctly identifies PL-B as new primary (earliest active facility on Account).
4. **PL-A's Mailing + Billing addresses ARE cloned to PL-B's location** (`PRM_PPLLMSTermService.getAddressForTermedPracLoc` L277 equality `fac.PRM_EffectiveTo__c == addr.PRM_EffectiveTo__c` HOLDS because both moved to `NEW_TERM_DATE`).

**LANDMINE TEST L4b**: Same setup, BUT PL-A's Billing address has `PRM_EffectiveTo__c = INDEP_CHILD_TERM` (independently set earlier — independent of PL-A). After push-out, PL-A is on `NEW_TERM_DATE`, Billing address still on `INDEP_CHILD_TERM`. Line 277 equality FAILS. Billing **never gets cloned** to PL-B.

**Required behavior**: Either:
- (a) Loosen the L277 equality to `addr.PRM_EffectiveTo__c >= fac.PRM_EffectiveTo__c OR addr.PRM_EffectiveTo__c was the OLD parent date`, OR
- (b) Use the address's actual EffectiveTo regardless and clone all Mailing/Billing.

Either way, **the test must fail under the current code** so devs know to fix the L277 condition.

---

### L5 — LMS-B: Push-out when ZERO other PLs exist on the Account (no new primary)

**Setup**: Vendor with 1 PL only (PL-A, Primary). PL-A `PRM_EffectiveTo = OLD_TERM_DATE`.

**Action**: Push PL-A to `NEW_TERM_DATE`.

**Expected**:

1. `PRM_PPLLMSTermService.processFacilities` runs, finds termed primary, but `accountToFacilities` map has 0 active facilities for the Account → no new primary picked.
2. **Vendor cascades to `NEW_TERM_DATE`** (via `PRM_CrossRefBatchHelper.vendorTermMap` at L38-44), with FDP `PRM_Status__c = 'Terminate - Last Man Standing'` at `NEW_TERM_DATE`.
3. No `PRM_PPLLMSTermService.unmarkPrimaryOnTermedWithOtherFacilities` mutation.
4. No address cloning (no target).
5. No errors logged in `PRM_ExceptionLogger`.

---

### L6 — LMS-B: Pull-in scenario, primary re-assignment

**Setup**: Same as L4 (2 PLs). Pull PL-A's term IN from `OLD_TERM_DATE` to `EARLIER_TERM_DATE`.

**Expected**:

1. PL-A → `EARLIER_TERM_DATE`.
2. Addresses → `EARLIER_TERM_DATE`.
3. `PRM_PPLLMSTermService` runs again; PL-B already promoted from prior cascade — must NOT mark PL-B again or duplicate primary.
4. `unmarkPrimaryOnTermedWithOtherFacilities` is idempotent.

---

### L7 — LMS-C: NPI shared by 2 PLs, push one PL out, NPI keeps OLD date

**Setup**:

- NPI shared between PL-A (Vendor V1) and PL-B (Vendor V1).
- Both PLs `PRM_EffectiveTo__c = OLD_TERM_DATE`.
- NPI `EffectiveTo = OLD_TERM_DATE`.

**Action**: Push PL-A only to `NEW_TERM_DATE` (PL-B stays on `OLD_TERM_DATE`).

**Expected**:

1. PL-A → `NEW_TERM_DATE`.
2. **NPI stays on `OLD_TERM_DATE`** because PL-B will still terminate on the OLD date and the NPI's "last man standing" condition (`HAVING Count(Id) = 1`) does NOT yet apply for PL-A's push-out (PL-B is the LMS holder for the NPI).
3. Vendor V1 `PRM_EffectiveTo__c` UNCHANGED (PL-B still keeps Vendor active until OLD date).

---

### L8 — LMS-C: Shared NPI, push BOTH PLs out (NPI cascades)

**Setup**: Same as L7.
**Action**: Push PL-A AND PL-B both to `NEW_TERM_DATE`.

**Expected**:

1. PL-A, PL-B → `NEW_TERM_DATE`.
2. **NPI → `NEW_TERM_DATE`** (now LMS — both sharing PLs aligned).
3. Vendor V1 → `NEW_TERM_DATE`.
4. NPI FDP row at `NEW_TERM_DATE`.

---

### L9 — LMS-C: Shared NPI, mixed push-out and pull-in

**Setup**: NPI shared by PL-A (`OLD_TERM_DATE`) and PL-B (`OLD_TERM_DATE`).
**Action**: Push PL-A to `NEW_TERM_DATE`; pull PL-B in to `EARLIER_TERM_DATE`.

**Expected**:

1. PL-A → `NEW_TERM_DATE`.
2. PL-B → `EARLIER_TERM_DATE`.
3. NPI: take the LATER of the two PL termination dates because that's when the NPI is no longer used anywhere → NPI = `NEW_TERM_DATE` (per `PRM_CrossRefBatchHelper` L59-61: `npiTermMap.get(...).EffectiveTo < hcf.PRM_EffectiveTo__c`).
4. Vendor V1: takes LATER → `NEW_TERM_DATE` (per L45-46 same logic on `vendorTermMap`).

**Verification**: Inspect `npiTermMap` and `vendorTermMap` resolution logic in `PRM_CrossRefBatchHelper.terminateFacilityAndRelations` — the existing `< hcf.PRM_EffectiveTo__c` check correctly picks the later date when entries exist for both PLs.

---

### L10 — LMS-C: Vendor LMS removal when push-out makes another sibling active

**Setup**: Vendor with PL-A (Primary, `OLD_TERM_DATE`) and PL-B (active, no term date — "open-ended"). Push PL-A.

**Expected**:

1. PL-A → `NEW_TERM_DATE`.
2. **Vendor UNCHANGED** (PL-B is open-ended, so Vendor must remain active).
3. `PRM_CrossRefBatchHelper` lines 104-111 fire `vendorTermMap.remove(hcf.AccountId)` because PL-B has `PRM_Active__c = TRUE` and is not in `hcfIdList`.

---

### L11 — LMS-A: LMS Vendor + LMS NPI both pushed in same flow

**Setup**: Vendor V1 with single PL-A (`PRM_CountOfActivePractitioners = 1`). NPI on PL-A is unique. Both Vendor and NPI on `OLD_TERM_DATE`.

**Action**: Push Vendor to `NEW_TERM_DATE` via Account Termination flow.

**Expected**:

1. Vendor → `NEW_TERM_DATE`, FDP `'Terminate - Last Man Standing'`.
2. PL-A → `NEW_TERM_DATE`.
3. NPI → `NEW_TERM_DATE`.
4. **All 3 LMS-relevant FDP rows on `NEW_TERM_DATE`. None on OLD.**
5. `PRM_FutureDatedProcessingUtil.createRecords` LMS branch fires once for the Account (per L99 condition).

---

### L12 — LMS-D: Practitioner removal LMS does NOT trigger USER_RE_TERMINATION mode (regression)

**Setup**: PL with `PRM_CountOfActivePractitioners__c = 1`. The remaining practitioner is being removed via the Active Location Removal flow (which calls `PRM_LMSService.evaluateImpact` → `collectLmsInactivationUpdates` or `collectLmsLastManStandingUpdates`).

**Action**: The LMS service runs with `Date.today()`.

**Expected**:

1. Facility, Location, Address, Networks, Associations all inactivated **today**.
2. **`PRM_TerminationDateUtility` (the new utility from § 5.1) is NOT invoked here** — `PRM_LMSService` is a separate code path that does immediate inactivation, NOT a guided-flow re-termination. The `Mode` enum is irrelevant here.
3. **If a refactor accidentally routes `PRM_LMSService` through the new utility, this test must fail.** This is a guardrail.

---

### L13 — LMS-D: Practitioner removal with AccountId == null (no Vendor)

**Setup**: Standalone practitioner with no Vendor, on a PL whose `AccountId == null`.
**Action**: Run `PRM_LMSService.evaluateImpact(facility)`.
**Expected** (per L49-53):

1. `impact.isLmsCandidate = true`.
2. `impact.isLastManStanding = true`.
3. `impact.shouldInactivateLocationAndAddress = false`.

This is unchanged by the push-out fix — pure regression test.

---

### L14 — LMS-A: Concurrent re-evaluation across multiple termed records

**Setup**: 50 Vendors each with their own LMS condition (all 1-PL, 1-practitioner). All `OLD_TERM_DATE`. Bulk push all 50 to `NEW_TERM_DATE`.

**Expected**:

1. `PRM_FutureDatedProcessingUtil.createRecords` issues ONE SOQL for `PRM_CountOfActivePractitioners__c` (line 55) — bulk-safe.
2. All 50 FDP rows upserted with `'Terminate - Last Man Standing'` at `NEW_TERM_DATE`.
3. No CPU/SOQL governor exceptions.

**Why**: The `for (Schema.HealthcareFacility... WHERE AccountId IN :records)` query at line 55 must be bulk-safe — verify with 50 records.

---

### L15 — LMS-B: Push-out with new primary that ALSO has `PRM_EffectiveTo__c` set (rare)

**Setup**: PL-A (Primary, terminating). PL-B (active, but has `PRM_EffectiveTo__c = LATE_CHILD_TERM` — terminating in the future, but later than PL-A).

**Action**: Push PL-A from `OLD_TERM_DATE` to `NEW_TERM_DATE`.

**Expected**:

1. PL-A → `NEW_TERM_DATE`.
2. PL-B is selected as new primary (`determineFacilitiesToMarkPrimary` picks earliest active).
3. PL-B's `PRM_EffectiveTo__c` UNCHANGED at `LATE_CHILD_TERM`.
4. PL-B's `PRM_Primary__c` flips from `false` → `true`.
5. PL-A's Mailing/Billing addresses cloned to PL-B's Location — but **only those whose `PRM_EffectiveTo__c == PL-A.PRM_EffectiveTo__c`** (i.e., `NEW_TERM_DATE` after the cascade); see L4b for the brittle case.

---

### L16 — LMS-A: LMS Vendor pushed PAST a child's independent earlier date

**Setup**: Vendor LMS, all children (PL, Address, HCFAssoc, etc.) on `OLD_TERM_DATE`, EXCEPT `PRM_HealthcareFacilityNetwork` independently terminated on `INDEP_CHILD_TERM` (earlier than NEW).

**Action**: Push Vendor from `OLD_TERM_DATE` to `NEW_TERM_DATE`.

**Expected**:

1. Vendor → `NEW_TERM_DATE` (LMS still — count of active practitioners is still 1 at trigger time).
2. Vendor FDP `'Terminate - Last Man Standing'` at `NEW_TERM_DATE`.
3. **HCFN UNCHANGED at `INDEP_CHILD_TERM`** (AC2).
4. **HCFN FDP UNCHANGED at `INDEP_CHILD_TERM`** with `PRM_Status__c = 'Terminate'` (NOT LMS — HCFN doesn't get LMS status; LMS is Account-only per `PRM_FutureDatedProcessingUtil` L99).

---

### L17 — LMS Audit Trail

**Setup**: Vendor LMS push-out (L1).

**Expected**:

1. `PRM_AsyncProcess__c` row written with `PRM_SubType__c = 'FDTermination'`.
2. Audit captures the LMS-status change (if any — see L2/L3).
3. Bell notification copy mentions LMS where applicable.

---

### LMS Coverage Matrix — what to assert in every LMS test

| Assertion | Why |
|---|---|
| `Account.PRM_EffectiveTo__c` correctly updated | Parent push-out works |
| `PRM_FutureDatedProcessing__c` count for parent = exactly 1 | External-Id upsert idempotent |
| `PRM_FutureDatedProcessing__c.PRM_Status__c` = `'Terminate'` OR `'Terminate - Last Man Standing'` per condition | LMS evaluation correct at trigger time |
| Vendor `PRM_CountOfActivePractitioners__c` re-queried (not cached) | LMS condition is dynamic |
| `PRM_PPLLMSTermService.processFacilities` runs for each terminated facility | Primary re-assignment fires |
| Mailing/Billing cloning to new primary uses correct `PRM_EffectiveTo__c` (no `==` brittleness) | L4b covers this |
| `PRM_LMSService` is NOT invoked with `USER_RE_TERMINATION` mode | L12 regression guard |
| Shared-NPI logic uses LATER of sibling dates | L9 covers this |

---

## 11. Negative / Regression Tests (must NOT regress with the fix)

| # | Scenario | Expected |
|---|---|---|
| N1 | LMS auto-cascade (`PRM_PPLLMSTermService`) terminating practitioner because last PL closed | Practitioner's existing earlier EffectiveTo (from another flow) is KEPT — i.e., `PARENT_CASCADE` mode must continue to honor "keep earlier of the two". |
| N2 | First-time termination on a record with `EffectiveTo = null` | Works exactly as today — `EffectiveTo = newTermDate`, FDP row created. |
| N3 | Termination Reason change with same date | No date or FDP changes. |
| N4 | Already-processed FDP row (`PRM_Processed__c = true`) | Push-out flow must INSERT a new FDP row (since the upsert key is `{id}_Terminate` — the prior row exists but is processed — the upsert will overwrite it). Devs: verify business semantics with PDM team; the processed flag will get reset by the upsert, which might re-fire processing. **This is a subtle landmine — test it.** |
| N5 | Push-out across a record that's already terminated (`PRM_Active = false`, `EffectiveTo < TODAY`) | Should error or be a no-op — user can't push-out an already-terminated record. Validate. |
| N6 | Trigger recursion guard | `PRM_FutureDatedProcessingUtil.createRecords` is called from triggers; pushing a Vendor must not blow Apex CPU limits. Use a 100-PL Vendor + 1000-child cascade in bulk test. |

---

## 12. Bulk / Governor Tests

### BULK1 — 200 PLs on one Vendor, push the Vendor

**Setup**: 200 active PLs, each with 5 child records (Address, HCFN, HCFAssoc, HPF, IFC).
**Action**: Push Vendor.
**Expected**:

1. Cascade completes within governor limits (≤ 50 SOQL, ≤ 150 DML chunks, ≤ 10k DML rows).
2. All 200 PLs + all 1000 children + ~1200 FDP rows on `NEW_TERM_DATE`.
3. No `LimitException`.

### BULK2 — 50 push-outs in one batch (multiple Vendors)

**Setup**: 50 Vendors, each terminated on different dates.
**Action**: Bulk re-terminate all 50 with `NEW_TERM_DATE`.
**Expected**: All 50 + cascades aligned. FDP upserts succeed (no DUPLICATE_EXTERNAL_ID).

---

## 13. Implementation Order for Devs (test-first checklist)

1. **Write Test Suite E (utility)** — fastest feedback. Create `PRM_TerminationDateUtilityTest` BEFORE the utility class. TDD.
2. **Write Test C2 (user's example)** — pin the AC2 contract before refactoring `PRM_CrossRefBatchHelper`.
3. **Write Tests A1, A3, A4** — pin the AC1 + AC2 contract for `PRM_AccountTerminationBatchHelper`.
4. **Write Tests B1, B3** — pin AC1 + AC2 for Practitioner flow.
5. **Write Tests D1, D4, D5** — pin FDP staging behavior.
6. Refactor each helper (per § 3.2 of the user story) and run the tests above.
7. **Write Tests in Suite C (C1–C10), B5–B8, A5–A11, BULK1–BULK2** — full coverage.
8. **Write Tests G1–G5** — OmniScript-level UAT seam.
9. Add `PRM_AccountTerminationBatchTest.@TestSetup` extension methods to seed:
   - "All-aligned" cascade
   - "Mixed independent dates" cascade
   - "Single PL on Vendor (LMS)" cascade
   - Factory methods preferred — reuse across all helper-class tests.

---

## 14. Test-Data Builder Pattern (recommended)

To keep tests readable and avoid copy-paste in 30+ test methods, add this builder to a new `PRM_TerminationTestFactory`:

```apex
@isTest
public class PRM_TerminationTestFactory {

    public static Account createVendor(Date effFrom, Date effTo) { /* ... */ }
    public static Account createPractitioner(Date effFrom, Date effTo) { /* ... */ }
    public static HealthcareFacility createPL(Account vendor, Date effFrom, Date effTo) { /* ... */ }
    public static HealthcareFacilityNetwork createNetwork(HealthcareFacility pl, String recordTypeDevName, Date effFrom, Date effTo) { /* ... */ }
    public static Schema.Address createAddress(Schema.Location loc, String addressType, Date effFrom, Date effTo) { /* ... */ }
    public static Identifier createIdentifier(Id parentId, String type, Date effFrom, Date effTo) { /* ... */ }
    public static BoardCertification createBoardCert(Id practitionerContactId, Date effFrom, Date effTo) { /* ... */ }
    public static HealthcareProviderNpi createNPI(Account acct, String npiType, Date effFrom, Date effTo) { /* ... */ }
    public static HealthcarePractitionerFacility createPPL(Id practContactId, HealthcareFacility pl, Date effFrom, Date effTo) { /* ... */ }
    // ... one factory per cascade target

    /**
     * Returns the COUNT of Terminate FDP rows whose EffectiveDate matches the input.
     * Use after any termination flow to assert FDP alignment.
     */
    public static Integer countTerminateFdpOnDate(Set<Id> recordIds, Date effDate) {
        return [SELECT COUNT() FROM PRM_FutureDatedProcessing__c
                WHERE PRM_SObjectRecordId__c IN :recordIds
                AND PRM_Status__c IN ('Terminate', 'Terminate - Last Man Standing')
                AND PRM_EffectiveDate__c = :effDate
                AND PRM_Processed__c = false];
    }

    /**
     * Assert that pushing a parent did NOT change a child's EffectiveTo.
     * Use for AC2 (independent child) assertions.
     */
    public static void assertChildUnchanged(SObject recBefore, SObject recAfter, String fieldName) {
        System.assertEquals(recBefore.get(fieldName), recAfter.get(fieldName),
            'AC2 violation: child ' + recBefore.getSObjectType() + '.' + fieldName + ' was modified during parent push-out');
    }
}
```

---

## 15. Quick-Reference: One-Liner Asserts to Add to EVERY Termination Test

For every existing termination test in the codebase, add these two assertions at the end to retroactively guard against the defect:

```apex
// AC1: After ANY termination flow, FDP rows must align with sObject EffectiveTo
for (Id recId : cascadedRecordIds) {
    Date sObjEffectiveTo = /* query the record's EffectiveTo */;
    Date fdpDate = [SELECT PRM_EffectiveDate__c FROM PRM_FutureDatedProcessing__c WHERE PRM_SObjectRecordId__c = :recId AND PRM_Status__c LIKE 'Terminate%' LIMIT 1].PRM_EffectiveDate__c;
    System.assertEquals(sObjEffectiveTo, fdpDate, 'FDP-vs-sObject date drift detected on ' + recId);
}

// AC2: Independent child dates must be preserved (assert via fixture snapshot diff)
for (Id independentChildId : preflightIndependentChildIds) {
    Date beforePush = preflightDateSnapshot.get(independentChildId);
    Date afterPush = /* re-query */;
    System.assertEquals(beforePush, afterPush, 'AC2 violation on ' + independentChildId);
}
```

---

## 16. Definition of "Done" for QA Sign-Off

A push-out PR may merge only after:

- [ ] Test Suite A (Account) passes for `PRM_AccountTerminationBatch` + `PRM_AccountTerminationInitialCredBatch`.
- [ ] Test Suite B (Practitioner) passes for `PRM_FullPractitionerTerminationBatch` + RCAT + Initial Cred.
- [ ] Test Suite C (Practice Location) passes for `PRM_TerminatePracticeLocationNRelations` + PDM Manual + RCAT Location + RCAT Network.
- [ ] **C2 passes** (user's explicit scenario — Network 10/1, PL 1/1/2027 → 1/1/2028, Network UNCHANGED).
- [ ] Test Suite D (FDP integrity) passes — Zero stale `Terminate` FDP rows on old date after any push-out.
- [ ] Test Suite E (`PRM_TerminationDateUtility`) passes — all 12 parametric cases.
- [ ] Test Suite F (Concurrency) passes — no duplicate FDP rows.
- [ ] Test Suite G (OmniScript) passes — pre-fill, banner, validation.
- [ ] Test Suite H (Audit) passes — bell notification + Case + AsyncProcess written.
- [ ] BULK1 + BULK2 pass within governor limits.
- [ ] N1 (LMS regression) passes — `PARENT_CASCADE` mode preserved.
- [ ] Code coverage ≥ 85% on every modified class.

---

## 17. Appendix — Field-Name Map (for cross-object cascade asserts)

| sObject | EffectiveFrom Field | EffectiveTo Field | Active Field |
|---|---|---|---|
| Account | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `IsActive` |
| HealthcareFacility | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| HealthcareFacilityNetwork | `EffectiveFrom` | `EffectiveTo` | `IsActive` |
| HealthcareProvider | `EffectiveFrom` | `EffectiveTo` | `PRM_Active__c` |
| HealthcareProviderNpi | `EffectiveFrom` | `EffectiveTo` | `IsActive` |
| HealthcareProviderTaxonomy | `EffectiveFrom` | `EffectiveTo` | `IsActive` |
| HealthcarePractitionerFacility | `EffectiveFrom` | `EffectiveTo` | `IsActive` |
| Schema.Location | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| Schema.Address | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| Identifier | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| BoardCertification | `PRM_EffectiveFrom__c` (override) | `PRM_EffectiveTo__c` (override) | `PRM_Active__c` |
| PRM_InfoCodeAssignment__c | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| PRM_ProgramParticipation__c | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| PRM_HealthcareFacilityAssociation__c | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| PRM_HealthcareFacilityBundleAssociation__c | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| PRM_ContactMethod__c | `PRM_EffectiveFrom__c` | `PRM_EffectiveTo__c` | `PRM_Active__c` |
| PRM_FutureDatedProcessing__c | — | `PRM_EffectiveDate__c` | `PRM_Processed__c` (inverse) |

Use this when writing factory helpers — saves 30 minutes per dev.
