# Ancillary Assessment — Add Provider Type / Sub-Service After Initial Submission

**Status:** Investigation + Initial Design Proposal — **superseded in part by `requirements/AncillaryAssessment_AddSubService_DetailedUserStories.md` (v3, 2026-06-02)**
**Created:** 2026-06-02
**Author:** AI agent (with QA-sandbox evidence)
**Target account used as evidence:** `001UW00000ejn1SYAQ` — *Complete Care At Lakeview Llc* (PRM_Vendor)
**Sandbox:** `qa-sandbox`

> **Routing-rule correction (2026-06-02).** The original investigation below assumed *any* in-flight Case Manager on the Account triggers reuse (`contextType = REUSE_IN_FLIGHT_CM`). That has been **corrected** in the Detailed User Stories doc to: **reuse the in-flight Case Manager ONLY when its Provider Type matches the submission's Provider Type**. A submission for a different Provider Type always creates a new Case Manager — even if another Provider Type is in flight on the same Account. Refer to `AncillaryAssessment_AddSubService_DetailedUserStories.md` §0 (decision matrix) and US-001 AC-1.2 / AC-1.6 for the authoritative routing rule. The schema sections, gap analysis, and live evidence in this investigation doc remain valid.

---

## 1. Business Requirements

**Primary persona:** Ancillary Cred Specialist.

An Ancillary Cred Specialist submits the **Ancillary Assessment** OmniScript guided flow for a vendor. After the first submission, the provider phones in and asks the Ancillary Cred Specialist to add **another Provider Type and/or sub-service** (example: original was *Skilled Nursing*; provider now wants to add *Subacute Ventilator* as a sub-service). Today there is no way to "amend" — every form submission spawns a brand-new Case Manager and a brand-new `PRM_AncillaryAssessment__c`, which contaminates Committee Review, reassessment scheduling, and downstream PDA/QC.

Two distinct scenarios must be supported, with very different routing logic.

### Scenario 1 — In-flight Case Manager (PSV-stage, pre-Committee)

- Ancillary Cred Specialist submits the Ancillary form for **Skilled Nursing**. CM = `IA-####` in **PSV / In Progress**.
- ~1 week later (before Committee Review), provider requests to add **Subacute Ventilator** as a sub-service.
- The Ancillary Cred Specialist must be able to submit a new Ancillary form that:
  - **Reuses the existing in-flight Case Manager** (no second CM, no second Case).
  - **Reuses the existing `PRM_AncillaryAssessment__c`** for any provider-types already submitted (do not create duplicates of *Skilled Nursing*).
  - **Adds new `PRM_AncillaryAssessment__c` records** only for newly-selected types/services (e.g., *Subacute Ventilator*).
  - Updates all downstream child data (addresses, licenses, identifiers, NPDB queue, adverse action logs, IPFiles, case-manager-association records, etc.) so that nothing is lost when Committee Review opens the CM.

### Scenario 2 — Approved Case Manager from prior cycle (reassessment behaviour)

- Provider was credentialed for **Skilled Nursing** in 2024; that CM completed Committee, HACAC = *Approve*, `PRM_ReAssessmentDueDate__c` was set to *HACACDecisionDate + 3 years*.
- A year (or more) later, provider asks the Ancillary Cred Specialist to add **Subacute Ventilator**.
- The Ancillary Cred Specialist submits a new Ancillary form. The system should:
  - **Create a brand new Case Manager + Case** (the prior cycle is closed; we are starting a new credentialing review for the added service).
  - **Reuse the same `PRM_AncillaryAssessment__c` "master" record where applicable**; only create new `PRM_AncillaryAssessment__c` rows for newly-added Provider Types/services.
  - When the new CM completes Committee Review with HACAC = *Approve*, set the reassessment due date conditionally:
    - **(2a)** If existing `PRM_ReAssessmentDueDate__c` is **≤ 1 year from today** → update to `HACACDecisionDate + 3 years` (preserve current behaviour).
    - **(2b)** If existing `PRM_ReAssessmentDueDate__c` is **> 1 year from today** → **do not override**; keep the existing reassessment date intact.

---

## 2. Live-data confirmation (account `001UW00000ejn1SYAQ`)

```sql
SELECT Id, Name, RecordType.DeveloperName, PRM_ProviderTypeService__c,
       PRM_CaseManager__c, PRM_CaseManager__r.Name, PRM_CaseManager__r.PRM_Stage__c,
       PRM_CaseManager__r.Status, PRM_AuthorizedSignatureForProvider__c,
       PRM_ReAssessmentDueDate__c, CreatedDate
FROM PRM_AncillaryAssessment__c
WHERE PRM_Account__c='001UW00000ejn1SYAQ'
ORDER BY CreatedDate DESC
```

| AA Id | Provider Type | Case Manager | Stage / Status | ReAssessmentDueDate | AuthorizedSignature | Created |
|---|---|---|---|---|---|---|
| `a1VVB000009BuwB2AS` | Skilled Nursing | `IA-0000152008` | PSV / In Progress | *null* | `"Test"` | 2026-05-28 |
| `a1VUW00000HHxMs2AL` | Skilled Nursing | *null* | n/a | **2027-07-08** (≈ 13 months out) | `"N/A - FROM HC3 MIGRATION"` | 2025-12-19 |

Open Cases on the account:

| Case # | Type | Status | CM |
|---|---|---|---|
| `00205898` | PSV | In Progress | `IA-0000152008` |
| `00064989` | Network Management QC | New | `IA-0000051037` |
| `00054768` | Network Management QC | New | `IA-0000043303` |

**This account already materialises both scenarios as a "live bug":**

- The 2025-12-19 row was migrated from HC3 with a future reassessment date of 2027-07-08 (> 1 yr from today, 2026-06-02). The 2026-05-28 row is a brand-new PSV created for the **same Skilled Nursing** provider-type — i.e. a duplicate. If the Ancillary Cred Specialist now adds Subacute Ventilator we will create a *third* `PRM_AncillaryAssessment__c` for Skilled Nursing and a *second* in-flight CM. **All three are wrong** under the new requirements.

---

## 3. Current Architecture — relevant active components

### 3.1 Form submission path

```
PRM_AncillaryWelcomeScreen_English_3 (active)
  └─→ PRM_AncillaryProviderForm_English_38 (active)        ← provider type/service selection
        └─→ PRM_AncillaryFormRecordsCreationParent_Procedure_2 (active)
              └─→ PRM_AncillaryFormRecordsCreation_Procedure_18 (active)
                    ├─ step 2  DRCaseCaseMgrAccountCreation  → bundle PRMDRCreateAncillaryCaseCaseMgrAndAccount
                    │            • Upserts Account (key: ExistingAccId)
                    │            • ALWAYS inserts new IndividualApplication (CM)  ← Gap #1
                    │            • ALWAYS inserts new Case (Type=PSV)              ← Gap #1
                    ├─ step 11 DRCreateLocationAddressPracLocationRecords
                    ├─ step 13 DRCreateCaseDataManagerRecord
                    ├─ step 17 PRMDRPCreateCaseManagerAssociation
                    ├─ step 26 DRCreatePracLocationSummaryRecords
                    ├─ step 27 IPFileCreation (form PDF on Case)
                    ├─ step 28 + 35 DRCreateAdverseActionLog
                    ├─ step 29 InsertAncillaryRecords  → Apex PRM_AncillaryProviderFormDataUpdates.insertAARecords
                    │            • Loops jsonData (AncillaryTypesAndServices)
                    │            • Lines 99 & 432–436:  `PRM_AncillaryAssessment__c record = new …();` + `insert aaRecords;`
                    │            • NO existing-record lookup, NO upsert, NO dedup ← Gap #2
                    └─ step 36 PRMDRCreateAdditionalAdverseActionLog
```

Duplicate-account check at form entry (`PRM_DuplicateAccountCheck_English_4`, active) only **detects** an existing Account; it does **not** detect or react to an existing in-flight Case Manager or Ancillary Assessment.

### 3.2 PSV stage

- OmniScripts: `PRM_AncillaryPSV…` series (LWC + IPs `PRM_AncillaryPSVFormCreationParent_Procedure_1`, `PRM_AncillaryPSVFormCreation_Procedure_2`, retrieval `PRM_AncillaryPSVFormDataRetrievalIP_Procedure_4` — all active).
- Reassessment-PSV: `PRM_AncillaryReassessmentPSVFormCreationParent_Procedure_1` / `_Creation_Procedure_1` (active).
- Address activation logic: `PRM_AncillaryReAssessmentPSVService.cls`.
- PSV completion → `PRM_AncillaryCompletePSVReviewParent_Procedure_1` + `_Procedure_1` (active).
- PSV reads the CM by Id only; **if step 1 reuses an in-flight CM, PSV "just works"** because it always operates on the CM record passed in. No PSV change should be required, only data correctness on the parent AA.

### 3.3 Committee Review (HACAC) & the +3-year date logic

- OmniScript: `PRM_ReviewHACAC_English_6` (active).
- Parent IP: `PRM_DataUpdationforHAPACCommitteeReviewParent_Procedure_1` (active).
- Child IP: `PRM_DataUpdationforHAPACCommitteeReview_Procedure_8` (active).
- The IP_8 calls these DataRaptors (referenced by `bundle` even though the retrieved `.rpt-meta.xml` shows `<active>false</active>` — that flag is from the export, not the org-side state; the IP references them so the deployed version is active):
  - `PRMDRTransformAncillaryReAssessmentApproveCase`
  - `PRMDRHACACUpdateAccountAndAncillaryAssessment`
  - `PRMDRHACACUpdateAncillaryAssessmentRecords`
  - `PRMDRHACACUpdateAncillaryAssessmentRecordsTerminateReAssess` (terminate path)

**The +3 year formula lives in `PRMDRHACACUpdateAncillaryAssessmentRecords_1.rpt-meta.xml`, lines 16–18:**

```text
formulaExpression : IF(%SelectedDecision% == "Approve",
                       ADDYEAR(TOSTRING(%DataList:HACACDecisionDate%), 3),
                       NULL)
formulaResultPath : DataList:HACACAncillaryAssessmentRecords:ReAssessmentDueDate
```

It is then written to `PRM_AncillaryAssessment__c.PRM_ReAssessmentDueDate__c` (line 69). **The formula is unconditional** — it always overrides whatever was previously set on the record. This is the root cause of the Scenario-2 violation.

### 3.4 PDA Review & Update

- Active IPs: `PRM_AncillaryPDAParent_Procedure_1` + `PRM_AncillaryPDA_Procedure_10`.
- Service: `PRM_AncillaryProviderUtilsPDAService.cls` (extracts location/address data for PDA).
- PDA reads from whatever AA records exist; **no change needed** if step 3.1 stops duplicating AAs.

### 3.5 Network Management QC

- Active IPs: `PRM_AncillaryQCUpdateParent_Procedure_1` + `PRM_AncillaryQCUpdate_Procedure_2`.
- Reads CM, AA, address data; reuses the same address-activation pipeline. **No change required** beyond fixing upstream duplicates.

### 3.6 Background batches that touch the reassessment date

- `PRM_NotifyReAssessmentDueDateBatch.cls` — sends 30/60/180-day notifications (only reads `PRM_ReAssessmentDueDate__c`).
- `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` — when an AA's `PRM_ReAssessmentDueDate__c` hits the window, creates a *new* Case Manager + Case for the reassessment (this is how the reassessment cycle normally starts). **This is independent of our changes** — but the Scenario-2 fix must not break it. Both should still trigger correctly off `PRM_ReAssessmentDueDate__c`.

---

## 4. Gap Analysis & Risks

### Gap #1 — No "existing in-flight CM" detection on form entry

`DRCaseCaseMgrAccountCreation` inserts a new `IndividualApplication` and new `Case` every time, regardless of whether a CM with `Status='In Progress'` and `RecordType.DeveloperName='PRM_AncillaryAssessment'` already exists for the same Account.

**Effects today:**
- Duplicate CMs and Cases on the same account, all "in flight" simultaneously.
- Committee Review opens whichever CM the user picks; data from the other CM is lost.
- The two AAs in the live evidence (`a1VVB…` and `a1VUW…`) prove this is a real production-data problem.

### Gap #2 — `insertAARecords` always inserts, never reuses

`PRM_AncillaryProviderFormDataUpdates.insertAARecords` instantiates `new PRM_AncillaryAssessment__c()` per selected type/service and does a flat `insert aaRecords` (lines 99, 432–436). There is no upsert key, no SOQL to find an existing AA for the same Account + Provider-Type-Service, no merging logic.

**Effects today:**
- Same Provider-Type-Service on the same account is duplicated across submissions.
- Reassessment due date is split across multiple records — `PRM_NotifyReAssessmentDueDateBatch` may fire twice, and Committee approvals on one AA do not affect the other.

### Gap #3 — Reassessment date is unconditionally overwritten

`PRMDRHACACUpdateAncillaryAssessmentRecords` always sets `PRM_ReAssessmentDueDate__c = HACACDecisionDate + 3 yrs` whenever `SelectedDecision == "Approve"`. There is no comparison against the existing value, so Scenario 2b is impossible to satisfy with the current logic.

### Risk #4 — Downstream child records (addresses, licenses, identifiers, adverse-action log, IPFile)

The records-creation IP creates many child records keyed to the freshly-created Case/CM. If we reuse an in-flight CM (Scenario 1) we must:
- Skip re-creating IPFile rows for forms that were already filed.
- Append-only behaviour for `PRM_CaseManagerAssociation__c`, `PRM_AdverseActionLog__c`, addresses, identifiers, licenses (no duplicate inserts, no overwrites of `PRM_EffectiveFrom__c` that the PSV stage may have already set).
- Decide whether to merge or to attach as "additional" the new Provider Type's storey: ownership / licensure / insurance / Medicare data is captured per-type on the AA record itself, so the new AA naturally carries the second submission's answers. Cross-type fields (e.g., contact person on the Account) should not regress to whatever was typed on form 2 — i.e., **the form should pre-populate those from the in-flight CM and disable editing them**, otherwise we get silent overrides.

### Risk #5 — Concurrency / idempotency

Two Ancillary Cred Specialists could submit two forms within seconds. We must use either a transactional "find or create CM" SOQL+upsert, or a `WITH SECURITY_ENFORCED` query inside a try/catch with a unique-criteria index on (`AccountId`, `RecordType.DeveloperName`, `Status`). Currently no such guard exists.

### Risk #6 — Audit & traceability

If the second submission "merges into" the first CM, we need an audit trail of which types/services were added when, otherwise Committee Review cannot see the chronology. Suggest adding history-tracking on `PRM_AncillaryAssessment__c.PRM_ProviderTypeService__c` and an explicit `PRM_AddedDate__c` field, plus appending a Chatter post to the CM each time a "delta" submission is made.

---

## 5. Proposed Design

### 5.1 Branching at form submission

Add a new pre-creation step in `PRM_AncillaryFormRecordsCreation_Procedure_18` (or a wrapper called by the parent IP_2 *before* IP_18) called `DetectExistingAncillaryContext`:

```text
Inputs : ExistingAccId, ProviderTypesSelected[]
Outputs:
  contextType : 'NEW' | 'REUSE_IN_FLIGHT_CM' | 'REASSESS_APPROVED_CM'
  existingCaseManagerId           (if REUSE_IN_FLIGHT_CM)
  existingCaseId                  (if REUSE_IN_FLIGHT_CM)
  existingAncillaryAssessmentMap  Map<ProviderType, AssessmentId>
  priorApprovedAA[]               (if REASSESS_APPROVED_CM)
```

SOQL inside the Apex helper:

```sql
SELECT Id, AccountId, PRM_Stage__c, Status
FROM IndividualApplication
WHERE AccountId = :existingAccId
  AND RecordType.DeveloperName = 'PRM_AncillaryAssessment'
  AND Status = 'In Progress'
ORDER BY CreatedDate DESC LIMIT 1
```

- If found → `contextType = REUSE_IN_FLIGHT_CM`.
- Else find the most-recently-approved AA(s) without an in-flight CM → `contextType = REASSESS_APPROVED_CM`.
- Else → `contextType = NEW` (current behaviour).

Then the orchestration IP makes step 2 (`DRCaseCaseMgrAccountCreation`) **conditional on `contextType == 'NEW'` or `contextType == 'REASSESS_APPROVED_CM'`**. Under `REUSE_IN_FLIGHT_CM` we skip CM/Case creation entirely and stuff `existingCaseManagerId` / `existingCaseId` into the IP context so all downstream steps wire correctly.

### 5.2 Apex change — `insertAARecords` becomes upsert + delta

In `PRM_AncillaryProviderFormDataUpdates.cls` modify `insertAARecords` to:

1. Accept the new `existingAncillaryAssessmentMap` input.
2. For each Provider Type the user selected:
   - If `existingAncillaryAssessmentMap.containsKey(providerType)` → fetch the existing AA, **merge** the form fields into it (update only fields that were blank or that the user explicitly changed), keep the same Id, no insert.
   - Else → instantiate a new AA (current behaviour), but ensure `PRM_CaseManager__c = contextCaseManagerId` (whether reused or freshly created).
3. Replace the unconditional `insert aaRecords;` with a partitioned operation:
   ```apex
   if (!aaRecordsToInsert.isEmpty()) insert aaRecordsToInsert;
   if (!aaRecordsToUpdate.isEmpty()) update aaRecordsToUpdate;
   ```
4. Add unit tests in `PRM_AncillaryProviderFormDataUpdatesTest` covering all three contexts plus the delta scenarios.

### 5.3 Reassessment-date conditional formula

Modify `PRMDRHACACUpdateAncillaryAssessmentRecords_1.rpt-meta.xml`. Replace the single ADDYEAR formula with a two-step computed value, OR (preferred) move the logic to Apex for clarity and add a fixed input `Today`.

**Preferred — invoke a small Apex method from IP_8** before the DR load step:

```apex
public class PRM_AncillaryHACACReassessmentDateCalculator implements Callable {
    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> input = (Map<String, Object>) args.get('input');
        Map<String, Object> output = (Map<String, Object>) args.get('output');
        Date hacacDecisionDate = Date.valueOf((String) input.get('HACACDecisionDate'));
        Id ancillaryAssessmentId = (Id) input.get('AncillaryAssessmentId');
        String decision = (String) input.get('SelectedDecision');

        if (decision != 'Approve') {
            output.put('ReAssessmentDueDate', null);
            return output;
        }

        PRM_AncillaryAssessment__c aa = [
            SELECT Id, PRM_ReAssessmentDueDate__c
            FROM PRM_AncillaryAssessment__c
            WHERE Id = :ancillaryAssessmentId WITH SECURITY_ENFORCED];

        Date oneYearOut = Date.today().addYears(1);
        Date proposedNew = hacacDecisionDate.addYears(3);

        // Scenario 2b: keep existing date if it is already more than 1 year out
        if (aa.PRM_ReAssessmentDueDate__c != null
            && aa.PRM_ReAssessmentDueDate__c > oneYearOut) {
            output.put('ReAssessmentDueDate', aa.PRM_ReAssessmentDueDate__c);
        } else {
            // Scenario 2a + initial approval: set to HACACDecisionDate + 3yrs
            output.put('ReAssessmentDueDate', proposedNew);
        }
        return output;
    }
}
```

Then in IP_8 the DR step that loads `PRM_ReAssessmentDueDate__c` reads from the Apex output rather than from the DR formula. The DR keeps its other field mappings; only the formula is replaced.

**Alternative (pure DR) — keep IP/DR-only by using OmniStudio formulas:**

```text
IF(
  %SelectedDecision% == "Approve",
  IF(
    AND(
      ISNOTBLANK(%DataList:HACACAncillaryAssessmentRecords:CurrentReAssessmentDueDate%),
      DATEDIFF(%DataList:HACACAncillaryAssessmentRecords:CurrentReAssessmentDueDate%, TODAY(), "d") > 365
    ),
    %DataList:HACACAncillaryAssessmentRecords:CurrentReAssessmentDueDate%,
    ADDYEAR(TOSTRING(%DataList:HACACDecisionDate%), 3)
  ),
  NULL
)
```

This requires `PRMDRHACACExtractCaseManagerAndRelatedData` to also return the **current** `PRM_ReAssessmentDueDate__c` as `CurrentReAssessmentDueDate` for each AA row, so the formula can reference it. Slightly cleaner deploy but harder to test; the Apex approach is recommended.

### 5.4 Welcome screen / Provider Form UX

Add an early "Add to existing review?" choice on the Welcome Screen when the account already has either:

- a CM in PSV or Committee Review (not yet approved/terminated), **or**
- an approved AA whose reassessment date is not yet hit.

Three options (drives `contextType` upstream so the user is aware):

- **(A)** Start a brand-new credentialing cycle (rare; today's default).
- **(B)** Add to the in-flight review (only types/services they don't already have).
- **(C)** Add a sub-service to an approved provider (creates a new CM but preserves the AA where applicable).

The "Provider Type & Service" picker on `PRM_AncillaryProviderForm` should grey out and pre-tick the types that already exist on the account, with a tooltip "Already credentialed / already in flight — additions only".

---

## 6. Implementation Plan

| # | Component | Change | Owner | Risk |
|---|---|---|---|---|
| 1 | `PRM_AncillaryProviderFormDataUpdates.cls` | New context resolution; upsert+delta logic in `insertAARecords` | Apex | M |
| 2 | New Apex `PRM_AncillaryFormContextResolver.cls` (Callable) | Returns `contextType`, ids, existing AA map | Apex | L |
| 3 | New Apex `PRM_AncillaryHACACReassessmentDateCalculator.cls` (Callable) | Conditional +3 yr vs preserve | Apex | L |
| 4 | `PRM_AncillaryFormRecordsCreation_Procedure_19` (new active version) | Inject context-resolver step at top; make CM/Case/AA steps conditional on `contextType` | OmniStudio | H – orchestration risk |
| 5 | `PRM_AncillaryFormRecordsCreationParent_Procedure_3` (new active version) | Wire to IP_19 | OmniStudio | L |
| 6 | `PRMDRHACACUpdateAncillaryAssessmentRecords_2` (new active version) | Replace formula with Apex-output binding | OmniStudio | M |
| 7 | `PRM_DataUpdationforHAPACCommitteeReview_Procedure_9` (new active version) | Insert Apex date calculator step before load DR | OmniStudio | M |
| 8 | `PRM_AncillaryWelcomeScreen_English_4` (new active version) | Add "Add to existing review?" pre-step | OmniStudio | M |
| 9 | `PRM_AncillaryProviderForm_English_39` (new active version) | Grey-out / pre-tick already-credentialed types | OmniStudio | M |
| 10 | New test classes | 90 %+ coverage for all new Apex; assertions for scenario 2a vs 2b | Apex | L |
| 11 | Data migration script | Walk all accounts, find duplicate `(AccountId, PRM_ProviderTypeService__c)` AAs, merge them with audit trail | Apex + script | H – touches live data |

### Test data plan (to use on `001UW00000ejn1SYAQ`)

After deploying changes:

**Scenario-1 test:**
1. Verify the existing in-flight CM `IA-0000152008` is still in PSV.
2. Submit a new Ancillary form for the account, select *Subacute Ventilator*.
3. Assert: no new IA created (still only `IA-0000152008` in-flight), no new Case, **one new `PRM_AncillaryAssessment__c`** for Subacute Ventilator linked to `IA-0000152008`, no duplicate Skilled Nursing AA.

**Scenario-2 test (2b path):**
1. Manually approve the in-flight CM (run committee). Note the new `PRM_ReAssessmentDueDate__c` on the just-approved AAs.
2. Submit another Ancillary form for the same account, select a new sub-service (e.g., Cardiac Monitoring).
3. Assert: new CM and Case created; new AA created for Cardiac Monitoring (CM linked); pre-existing Skilled Nursing / Subacute Ventilator AAs unchanged.
4. Run Committee Review on the new CM → Approve.
5. Assert: existing AAs whose `PRM_ReAssessmentDueDate__c > today+365` are **unchanged**; new Cardiac Monitoring AA gets `HACACDecisionDate + 3 yrs`.

**Scenario-2 test (2a path):**
1. Backdate a test AA's `PRM_ReAssessmentDueDate__c` to today+200d.
2. Submit + approve as above.
3. Assert: backdated AA's date is **updated** to `HACACDecisionDate + 3 yrs`.

---

## 7. Open Questions for Business

1. When a second submission happens for the **same** provider type already on the in-flight CM (e.g., user picks Skilled Nursing again with different ownership data), do we **merge** the new answers into the existing AA, **reject** the form, or treat the second answer set as the source of truth? *Recommend: pre-populate and lock those types, force the user to deselect them.*
2. Should the "add sub-service" flow be allowed once the CM has moved past PSV (e.g., during Committee Review)? *Recommend: no — once HACAC is open, lock the CM.*
3. For Scenario 2, if the existing approved AA was for *Skilled Nursing* and the new submission adds *Subacute Ventilator*, do we want one consolidated reassessment date across all AAs of that account (preserving the earliest date), or per-AA dates as today? *Current code is per-AA; the requirement reads per-AA. Confirm.*
4. Does the 1-year threshold compare to `TODAY()` or to the **HACAC decision date** of the new committee approval? Spec says "1 year from today"; recommend using `TODAY()` at the time of approval to keep the rule intuitive for Ancillary Cred Specialists.

---

## 8. Evidence Index

- Active IPs / OmniScripts confirmed by `<isActive>true</isActive>` grep.
- +3 year formula proved in `force-app/main/default/omniDataTransforms/PRMDRHACACUpdateAncillaryAssessmentRecords_1.rpt-meta.xml`, lines 16–18, target field `PRM_ReAssessmentDueDate__c` (line 69).
- `insertAARecords` always-insert proved in `force-app/main/default/classes/PRM_AncillaryProviderFormDataUpdates.cls`, lines 99, 432–436.
- `DRCaseCaseMgrAccountCreation` always-insert proved by IP_18 step 2 (additionalOutput maps `Account_1`, `Case_3`, `IndividualApplication_2` from the DR with no upsert key on the latter two).
- Live state of `001UW00000ejn1SYAQ` queried 2026-06-02 in `qa-sandbox`.
