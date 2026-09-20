# User Story — Re-Assessment Letter Generation: Silent Failure on Missing Letterhead Indicator

**Story Type:** Bug Fix + Enhancement
**Workstream:** Ancillary / Re-Assessment
**Related Batch:** `PRM_CheckDueOnAncillaryReAssessmentBatch`
**Confirmed Affected Record:** Assessment `a1VUW00000HHx9r2AD` — Genomic Health Inc

---

## Story Title

**As a** Provider Relations Operations user,
**I want** the Re-Assessment batch to detect and alert when a letter cannot be generated due to a missing or unmatched Letterhead Indicator configuration,
**So that** no assessment record silently falls through without a letter, the operations team is notified in real time, and stuck records can be remediated before SLA breach.

---

## Background / Problem Statement

The `PRM_CheckDueOnAncillaryReAssessmentBatch` runs daily. For each `PRM_AncillaryAssessment__c` record whose `PRM_ReAssessmentDueDate__c` equals today + 180 days, the batch:
1. Creates an `IndividualApplication` (IA) and a `Case`
2. Calls `PRM_ReassessmentLetter.generateLetter()` to create a `PRM_Letter__c`

**Confirmed failure — Assessment `a1VUW00000HHx9r2AD` (Genomic Health Inc, Redwood City CA):**

| Field | Value |
|---|---|
| Account | `001UW00000ek0hdYAA` — Genomic Health Inc |
| Account IsActive | `true` |
| Account RecordType | `PRM_Vendor` |
| Primary Address | 301 Penobscot Dr, Redwood City, **CA 94063**, County = **San Mateo** |
| HealthcareFacility | `0klUW0000002EkTYAU` — Primary=true, Active=true, NPI=1215003603 |
| Mailing Address | PO Box 735265, Chicago, IL 60673 |
| Assessment Due Date | `2026-04-24` |
| Batch config (`PRM_DueDays__c`) | `180` — batch ran ~2025-10-26 |

**What the batch did:**
- ✅ Created IA `0iTUW000000L2LA2A0` (RecordType=`PRM_AncillaryReAssessment`, Stage=`PSV`, Status=`Pending Application`)
- ✅ Created a Case
- ❌ **Did NOT create a `PRM_Letter__c`**
- ❌ **Batch reported: "Completed (0 errors)"** — completely silent

**Why the letter was not created — confirmed via SOQL:**

The letter key built in `PRM_ReassessmentLetter.createLetter()` (line 94) is:
```
letterKey = addrPrimary.PRM_State__c + '-' + addrPrimary.PRM_County__c
          = 'CA' + '-' + 'San Mateo'
          = 'CA-San Mateo'
```

The entire `PRM_LetterheadIndicator__c` table contains **only DE, MD, NJ, and PA** counties:
- **DE**: New Castle, Kent, Sussex
- **MD**: Cecil, Anne Arundel, Baltimore, Baltimore City, Caroline, Dorchester, Harford, Howard, Montgomery, Washington, Wicomico, Worchester
- **NJ**: Burlington, Camden, Gloucester, Hunterdon, Mercer, Salem, Warren, Atlantic, Bergen, Cape May, Cumberland, Essex, Hudson, Middlesex, Monmouth, Morris, Ocean, Passaic, Somerset, Sussex, Union
- **PA**: Bucks, Chester, Delaware, Montgomery, Philadelphia

`stateCountyVsIndicator.containsKey('CA-San Mateo')` → **`FALSE`** → `toInsertLetter = []` → no insert → **no letter, no exception, no log entry.**

The record is now permanently stuck:
- The existing IA (`Stage=PSV`) blocks all future batch runs via `filterAncillaryAssessments()`
- The due date window (`today+180 = 2026-04-24`) has passed — the record will never re-enter batch scope

---

## Scope

This story covers **four workstreams**. **All workstreams are now UNBLOCKED** — business decisions received 2026-05-06.

| Workstream | Type | Status |
|---|---|---|
| **WS-1** | Code Fix — observability + null guards | ✅ Ready to implement |
| **WS-2** | Data Fix — Letterhead Indicator configuration | ✅ **APPROVED** — insert 136 indicators (68 state-county × 2 keys) |
| **WS-3** | Remediation — stuck records audit + manual fix | ✅ **APPROVED** — manual script, 68 IAs to remediate |
| **WS-4** | Test Fix — assert letter creation end-to-end | ✅ Ready to implement |

---

## Business Decisions (2026-05-06)

| Question | Decision |
|---|---|
| **OQ-1** — Out-of-territory letters? | ✅ **YES** — All providers receive letters regardless of state |
| **OQ-2** — Letterhead keys for out-of-territory? | ✅ **BOTH IBC + AHPA** — Each provider gets 2 letters (dual letterhead) |
| **OQ-3** — Run full audit? | ✅ **YES** — Audit completed: **68 out of 69 stuck IAs** caused by missing indicators |
| **OQ-4** — HC3-migrated records? | ✅ Ignore — not a factor in remediation decision |
| **OQ-5** — CA/other states in picklist? | ✅ **YES** — All required states present in `PRM_States` picklist |
| **OQ-6** — Remediation approach? | ✅ **Manual script** — Anonymous Apex invocation for 68 stuck IAs |
| **OQ-7** — Remediation SLA? | ⏳ Pending confirmation from business |
| **OQ-8** — Gate IA/Case on letter eligibility? | ✅ **NO CHANGE NEEDED** — Existing code already supports multiple letters per assessment |

**Critical finding from audit:**
- **7 PA counties** (Allegheny, Carbon, Cumberland, Dauphin, Lackawanna, Luzerne, Monroe) are **inside IBX territory** but missing from `PRM_LetterheadIndicator__c` — urgent data gap
- **21 out-of-territory states** (CA, FL, NY, NC, TN, CO, etc.) — 61 unique state-county combos

**Total data fix:** 136 `PRM_LetterheadIndicator__c` records to insert (68 state-county combos × 2 keys: IBC + AHPA)

---

## Acceptance Criteria

---

### WS-1: Code Observability Fix (`PRM_ReassessmentLetter.cls`)

**AC-1.1 — Log when no Letterhead Indicator key match is found**

In `createLetter()`, the current code has no `else` branch when `stateCountyVsIndicator.containsKey(letterKey)` returns `false`. A Warning log must be added:

```apex
// CURRENT — silent, no else:
if (stateCountyVsIndicator.containsKey(letterKey)) {
    // ... create letter
}

// FIXED — add else with logging:
if (stateCountyVsIndicator.containsKey(letterKey)) {
    // ... create letter (unchanged)
} else {
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter createLetter', '', 'Warning', '',
        'No LetterheadIndicator match for key: ' + letterKey,
        'DataQualityWarning', 0, '',
        'AccountId: ' + accId
            + ' | Key attempted: ' + letterKey
            + ' | State: ' + accLocObj.addrPrimary.PRM_State__c
            + ' | County: ' + accLocObj.addrPrimary.PRM_County__c,
        'Salesforce', '', '');
}
```

**AC-1.2 — Log when no active primary HealthcareFacility exists for an account**

After the HCF query loop in `generateLetter()`, before calling `createLetter()`, add:

```apex
List<String> missingHCF = new List<String>();
for (Id accId : accLocMap.keySet()) {
    if (accLocMap.get(accId).hcFacility == null) {
        missingHCF.add(accId);
    }
}
if (!missingHCF.isEmpty()) {
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter generateLetter', '', 'Warning', '',
        'No active primary HealthcareFacility found for accounts: ' + missingHCF,
        'DataQualityWarning', 0, '',
        JSON.serialize(missingHCF), 'Salesforce', '', '');
}
```

**AC-1.3 — Guard against null `addrPrimary` in `createLetter()`**

Replace the current silent `null-null` key path with an explicit guard:

```apex
// CURRENT (produces key 'null-null' silently):
String letterKey = accLocObj.addrPrimary?.PRM_State__c
                 + '-' + accLocObj.addrPrimary?.PRM_County__c;

// FIXED:
if (accLocObj.addrPrimary == null) {
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter createLetter', '', 'Warning', '',
        'No active primary Address for account: ' + accId,
        'DataQualityWarning', 0, '',
        'addrPrimary is null — cannot build letterKey for account: ' + accId,
        'Salesforce', '', '');
    continue;
}
String letterKey = accLocObj.addrPrimary.PRM_State__c
                 + '-' + accLocObj.addrPrimary.PRM_County__c;
```

**AC-1.4 — Use safe navigation on NPI field to prevent silent NPE**

In `createLetter()` line 110:

```apex
// CURRENT — throws NullPointerException if PRM_NpiId__c is null:
ltr.PRM_GroupNpi__c = accLocObj.hcFacility.PRM_NpiId__r.Npi;

// FIXED:
ltr.PRM_GroupNpi__c = accLocObj.hcFacility.PRM_NpiId__r?.Npi;
```

**AC-1.5 — All new Warning log entries are queryable**

Every new `PRM_ExceptionLogger.logException()` call must include enough detail (AccountId, key attempted, State, County) that an ops user can investigate the failure from the `PRM_ExceptionLog__c` object without reading code.

---

### WS-2: Data Configuration Fix (`PRM_LetterheadIndicator__c`)
> **Blocked on: OQ-1, OQ-2, OQ-3, OQ-4, OQ-5**

**AC-2.1** — Business confirms whether out-of-territory providers (states outside DE/MD/NJ/PA) should receive a Re-Assessment letter. Decision documented and signed off.

**AC-2.2** — If yes: the appropriate `PRM_LetterheadIndicator__c` records are created for all missing state/county combinations identified in the WS-3 audit. Each record must have:
- `PRM_StateCode__c` — valid picklist value from `PRM_States` global value set
- `PRM_CountyName__c` — exact match to `PRM_County__c` on the account's primary `Address` record
- `PRM_LetterheadKey__c` — approved key string (max 15 chars)
- `PRM_Category__c` — descriptive label

**AC-2.3** — If no: the batch scope or `filterAncillaryAssessments()` is updated to exclude accounts whose primary address state is not covered by any `PRM_LetterheadIndicator__c`, and those accounts generate an operational alert rather than silently processing.

**AC-2.4** — If `CA` (or other required states) are not present in the `PRM_States` restricted picklist, a metadata deployment to add them is completed and validated in sandbox before any `PRM_LetterheadIndicator__c` records are inserted.

---

### WS-3: Stuck Record Remediation
> **Blocked on: OQ-6, OQ-7**

**AC-3.1 — Full audit of stuck records**

A SOQL audit is run to identify all `IndividualApplication` records where:
- `RecordType.DeveloperName = 'PRM_AncillaryReAssessment'`
- `PRM_Stage__c != 'Complete'`
- No linked `PRM_Letter__c` with `RecordType.DeveloperName = 'PRM_ReAssessment'` exists

Suggested audit query:
```sql
SELECT ia.Id, ia.PRM_AncillaryAssessment__c, ia.PRM_Stage__c, ia.Status,
       ia.AccountId, ia.Account.Name, ia.Account.BillingState,
       ia.CreatedDate
FROM IndividualApplication ia
WHERE ia.RecordType.DeveloperName = 'PRM_AncillaryReAssessment'
  AND ia.PRM_Stage__c != 'Complete'
  AND ia.Id NOT IN (
      SELECT PRM_CaseManager__c FROM PRM_Letter__c
      WHERE RecordType.DeveloperName = 'PRM_ReAssessment'
        AND PRM_CaseManager__c != null
  )
ORDER BY ia.CreatedDate ASC
```

Results reviewed and approved by Provider Relations Operations lead.

**AC-3.2 — Specific record remediation**

Once WS-2 is complete (Letterhead Indicator configured for CA/San Mateo):
- Manually invoke `PRM_ReassessmentLetter.generateLetter()` via Anonymous Apex for IA `0iTUW000000L2LA2A0`
- Confirm that `PRM_Letter__c` record is created and linked to IA `0iTUW000000L2LA2A0`
- Confirm `PRM_LetterheadKey__c` is populated on the letter

**AC-3.3** — Approved remediation approach for all other stuck records identified in AC-3.1 is documented and executed within the agreed SLA.

---

### WS-4: Test Class Fix (`PRM_CheckDueOnAncillaryReAssessBatchTest.cls`)

**AC-4.1 — Fix broken `@testSetup`: set `PRM_DueDays__c`**

The current test setup inserts `PRM_CAQHDateRangeSetting__c` with all date fields null, causing the batch to query 0 records (the date filter has no value). Fix:

```apex
// CURRENT — null dates, batch processes nothing:
PRM_CAQHDateRangeSetting__c reAssessmentDateRange = new PRM_CAQHDateRangeSetting__c(
    Name = 'ReAssessmentCAQHDateRange'
);

// FIXED:
PRM_CAQHDateRangeSetting__c reAssessmentDateRange = new PRM_CAQHDateRangeSetting__c(
    Name = 'ReAssessmentCAQHDateRange',
    PRM_DueDays__c = '180'  // must match assessment's PRM_ReAssessmentDueDate__c = today+180
);
```

**AC-4.2 — Fix `@testSetup`: align LetterheadIndicator with test account address**

The test creates a `PRM_LetterheadIndicator__c` with `PRM_StateCode__c='DE'`, `PRM_CountyName__c='New Castle'` — but the test vendor account's primary address is not set to DE/New Castle. Either:
- Set the test address to `PRM_State__c='DE'`, `PRM_County__c='New Castle'`, OR
- Change the `PRM_LetterheadIndicator__c` to match the address state/county used in the test

**AC-4.3 — Assert letter creation in the positive test**

After `Test.stopTest()` in `testBatchExecution()`, add assertions:

```apex
List<IndividualApplication> iaList = [
    SELECT Id FROM IndividualApplication
    WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPE_ANCILLARYREASSESSMENT
];
System.assertEquals(1, iaList.size(), 'Expected 1 IA to be created');

List<PRM_Letter__c> letters = [
    SELECT Id, PRM_CaseManager__c, PRM_LetterheadKey__c FROM PRM_Letter__c
    WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT
];
System.assertEquals(1, letters.size(), 'Expected 1 ReAssessment Letter to be created');
System.assertNotEquals(null, letters[0].PRM_CaseManager__c, 'Letter must be linked to the IA');
System.assertNotEquals(null, letters[0].PRM_LetterheadKey__c, 'Letter must have a LetterheadKey');
```

**AC-4.4 — Add a negative test: no Letterhead Indicator → Warning log created**

```apex
@isTest
static void testBatchExecution_noLetterheadIndicator_logsWarning() {
    // Delete all LetterheadIndicator records
    delete [SELECT Id FROM PRM_LetterheadIndicator__c];

    Test.startTest();
    Database.executeBatch(new PRM_CheckDueOnAncillaryReAssessmentBatch());
    Test.stopTest();

    // No letter should be created
    List<PRM_Letter__c> letters = [SELECT Id FROM PRM_Letter__c
        WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT];
    System.assertEquals(0, letters.size(), 'No letter should be created without LetterheadIndicator');

    // A warning log should be created
    List<PRM_ExceptionLog__c> logs = [SELECT Id, PRM_Message__c FROM PRM_ExceptionLog__c
        WHERE PRM_Severity__c = 'Warning'];
    System.assertEquals(1, logs.size(), 'Expected 1 warning log for missing LetterheadIndicator');
    System.assert(logs[0].PRM_Message__c.contains('No LetterheadIndicator match'),
        'Warning message should reference the missing key');
}
```

> Note: Field API names on `PRM_ExceptionLog__c` for message and severity must be confirmed.

---

## Open Questions to Business

> ⚠️ **Items OQ-1 through OQ-7 are blockers for WS-2 and WS-3. WS-1 and WS-4 can be built and deployed independently while these are resolved.**

---

### OQ-1 — Should out-of-territory providers (outside DE/MD/NJ/PA) receive Re-Assessment letters?

**Context:**
Genomic Health Inc (`001UW00000ek0hdYAA`) is located in Redwood City, **CA**. The `PRM_LetterheadIndicator__c` configuration covers only IBX's traditional service territory: DE, MD, NJ, and PA. There is currently no CA entry.

The Re-Assessment batch picks up this provider because:
- Account `IsActive = true`, `RecordType = PRM_Vendor` ✅
- `PRM_AuthorizedSignatureForProvider__c` is populated (`"N/A - FROM HC3 MIGRATION"`) ✅
- `PRM_ReAssessmentDueDate__c` matched the batch window ✅

However, no letterhead is configured for CA, so no letter can be produced.

**Question:** Is it intentional that IBX sends Re-Assessment letters to providers located in California? Or is this provider outside the intended scope of this process?

**Options to choose from:**
- **A** — Yes, CA providers should receive letters → configure CA letterhead keys (triggers OQ-2)
- **B** — No, only DE/MD/NJ/PA providers should receive letters → exclude out-of-territory from batch scope
- **C** — It depends on a provider-level attribute (e.g., a specific plan network, a flag on the account) → define the rule

**Decision needed from:** Provider Relations / Credentialing Operations lead
**By:** ___________

---

### OQ-2 — What `PRM_LetterheadKey__c` value should be used for CA providers (and any other out-of-territory states)?

**Context:**
The `PRM_LetterheadKey__c` field (max 15 characters, required) drives which letterhead template is rendered on the generated letter. Current values in use:
- `IBC` — used for DE/New Castle, MD/Cecil, NJ/Burlington, NJ/Camden, NJ/Gloucester, NJ/Hunterdon, NJ/Mercer, NJ/Salem, NJ/Warren, PA/Bucks, PA/Chester, PA/Delaware, PA/Montgomery, PA/Philadelphia
- `AHPA` — used for DE/New Castle, DE/Kent, DE/Sussex, MD/Cecil, MD/Anne Arundel, and all other MD counties
- `AHNJ` — used for all NJ counties

A new key or re-use of an existing generic/national key would be needed for CA (if OQ-1 answer is A).

**Question:** What letterhead key should be used for California providers? Is there an existing national/generic IBX template that can be applied, or does a new template need to be created?

**Decision needed from:** Compliance / Brand / Provider Communications team
**By:** ___________

---

### OQ-3 — How many other out-of-territory providers are in the active assessment population?

**Context:**
Genomic Health Inc may not be the only out-of-territory provider with a `PRM_AncillaryAssessment__c` record. There could be providers in NY, TX, FL, OH, or other states that will silently fail letter generation on their due date — creating the same stuck-IA/no-letter situation.

**Question:** Should engineering run a full audit of all active `PRM_AncillaryAssessment__c` records, cross-reference each account's primary address state against the `PRM_LetterheadIndicator__c` table, and report back with a list of states/counties that are missing configuration? If so, who reviews and approves the findings, and what is the turnaround expectation?

**Decision needed from:** Provider Relations Operations / Data Steward
**By:** ___________

---

### OQ-4 — Is the Genomic Health Inc assessment a legitimate active case or a data migration artifact that should be excluded?

**Context:**
The `PRM_AuthorizedSignatureForProvider__c` field on assessment `a1VUW00000HHx9r2AD` reads `"N/A - FROM HC3 MIGRATION"` — a clear indicator that this record was migrated from the legacy HC3 system, not created natively in Salesforce. The field is currently non-null, which is why the batch picks it up. It is possible that:
- The batch was never designed to handle HC3-migrated out-of-territory records
- These records should have been flagged during migration and excluded from automation

**Question:** Should HC3-migrated assessments (identifiable by `PRM_AuthorizedSignatureForProvider__c = 'N/A - FROM HC3 MIGRATION'`) be excluded from the Re-Assessment batch? Or are they legitimate candidates that need full Letterhead Indicator coverage?

**Decision needed from:** Data Migration team / Provider Data Management lead
**By:** ___________

---

### OQ-5 — Is `CA` (and any other out-of-territory states) present in the `PRM_States` global picklist value set?

**Context:**
`PRM_StateCode__c` on `PRM_LetterheadIndicator__c` is a **restricted picklist** tied to the `PRM_States` global value set. Before any new `PRM_LetterheadIndicator__c` record can be inserted for CA (or any other new state), `CA` must exist as an active value in the `PRM_States` global value set — otherwise the DML will fail with a restricted picklist validation error.

This requires a metadata deployment (change to `globalValueSets/PRM_States.globalValueSet-meta.xml`) that must go through the standard release process.

**Question:** Please confirm which state codes are currently active in the `PRM_States` global value set. Is CA included? If not, can it be added in the next release cycle?

**Decision needed from:** Release / Platform Admin team
**By:** ___________

---

### OQ-6 — What is the approved remediation approach for all stuck IA records with no letter?

**Context:**
The `filterAncillaryAssessments()` method permanently removes any assessment from batch scope if an `IndividualApplication` with `RecordType = PRM_AncillaryReAssessment` and `PRM_Stage__c != 'Complete'` already exists. This means:
- Every assessment that had a silent letter failure in the past is stuck forever
- The batch will never automatically retry them
- Manual intervention is required for every stuck record

The known stuck record is:
- Assessment `a1VUW00000HHx9r2AD` / IA `0iTUW000000L2LA2A0` (Genomic Health Inc, Stage=PSV)

There may be additional stuck records (see OQ-3 audit).

**Question:** Which remediation approach is approved for stuck records?

**Options:**
- **A — Manual invocation:** Engineering runs Anonymous Apex to call `PRM_ReassessmentLetter.generateLetter()` for each stuck IA individually. Low risk, targeted.
- **B — One-time remediation batch:** Build a one-time Apex batch that queries all IAs with `RecordType = PRM_AncillaryReAssessment`, `Stage != Complete`, and no linked `PRM_Letter__c`, and attempts letter generation for each. More scalable if many records are stuck.
- **C — Self-healing retry logic:** Modify `filterAncillaryAssessments()` to allow re-processing when a matching IA exists but has no letter yet — i.e., retry if letter is absent regardless of stage. This permanently prevents the stuck state for future runs.

**Decision needed from:** Operations + Engineering leads
**By:** ___________

---

### OQ-7 — What is the remediation SLA for letters that were not generated on the original batch run?

**Context:**
The batch ran for this specific record approximately **2025-10-26**. Today is 2026-05-04. The Re-Assessment letter for Genomic Health Inc has been missing for approximately **6 months**. A late letter may raise compliance, regulatory, or contractual questions.

**Questions:**
1. Is there a regulatory or contractual deadline within which the Re-Assessment letter must be delivered to the provider? If so, has that deadline been breached for this record?
2. Should a late letter carry a different effective date (e.g., today's date) or the original batch run date (`2025-10-26`)?
3. Does a late letter require any special handling — a cover note, supervisor approval, or communication to the provider explaining the delay?
4. Who owns the remediation sign-off — Provider Relations, Compliance, or Credentialing Operations?

**Decision needed from:** Compliance / Provider Relations / Credentialing Operations
**By:** ___________

---

### OQ-8 — Should the batch be restricted to only process accounts covered by an existing Letterhead Indicator?

**Context:**
Currently the batch picks up **any** active `PRM_Vendor` account with a matching due assessment — regardless of whether the account's state has a `PRM_LetterheadIndicator__c` entry. This means:
- An IA and Case are always created (even for unconfigured states)
- But a letter is never produced for unconfigured states
- The IA then blocks all future retries

This is arguably a design flaw: IAs and Cases are created for work that can never proceed to letter generation.

**Question:** Should IA and Case creation be **gated** on letter eligibility (i.e., a matching `PRM_LetterheadIndicator__c` must exist for the account's state/county before an IA is created)? Or should IA/Case creation proceed independently of letter eligibility?

**Trade-off:**
- Gating prevents stuck IAs and wasted records, but may block legitimate processing if a Letterhead Indicator is temporarily missing due to a data issue
- Not gating keeps IA/Case creation clean but requires the observability fixes (WS-1) to surface misconfiguration before it causes downstream failures

**Decision needed from:** Credentialing Operations / Product Owner
**By:** ___________

---

## Definition of Done

- [ ] **WS-1 complete:** AC-1.1 through AC-1.5 implemented, reviewed, and deployed to sandbox
- [ ] **WS-2 complete:** Business answers to OQ-1 through OQ-5 received; `PRM_LetterheadIndicator__c` records created or exclusion logic deployed
- [ ] **WS-3 complete:**
  - [ ] Audit query (AC-3.1) run; results reviewed and signed off by business
  - [ ] Genomic Health Inc letter created for IA `0iTUW000000L2LA2A0` (AC-3.2)
  - [ ] All other stuck records remediated within agreed SLA (AC-3.3)
- [ ] **WS-4 complete:** AC-4.1 through AC-4.4 implemented; all new test assertions pass in sandbox; code coverage maintained
- [ ] After deployment: no new `PRM_ExceptionLog__c` Warning records for letterhead key misses on the next 3 batch runs
- [ ] Ops team confirms letter generation for all previously stuck records
- [ ] Story signed off by Provider Relations Operations lead

---

## Story Points Estimate (Preliminary)

| Workstream | Description | Points |
|---|---|---|
| WS-1 | Code observability fix (logging + null guards + safe nav) | 3 |
| WS-2 | Data configuration (pending business answers) | 2 |
| WS-3 | Stuck record audit + remediation | 3 |
| WS-4 | Test class fix + new negative test scenario | 2 |
| **Total** | | **10** |

> WS-1 and WS-4 can be picked up immediately in the current sprint.
> WS-2 and WS-3 should be tracked as a follow-on spike/story once Open Questions are resolved.

---

## Related Records & Artifacts

| Item | ID / Reference |
|---|---|
| Affected Assessment | `a1VUW00000HHx9r2AD` |
| Affected Account | `001UW00000ek0hdYAA` — Genomic Health Inc |
| Blocking IA (no letter) | `0iTUW000000L2LA2A0` |
| HealthcareFacility | `0klUW0000002EkTYAU` |
| Primary Address | `130UW00000MNOQTYA5` — CA, San Mateo |
| Batch Class | `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` |
| Letter Class | `PRM_ReassessmentLetter.cls` — `createLetter()` line 94–139 |
| Test Class | `PRM_CheckDueOnAncillaryReAssessBatchTest.cls` |
| Letterhead Config Object | `PRM_LetterheadIndicator__c` |
| CAQH Date Setting | `PRM_CAQHDateRangeSetting__c` — `ReAssessmentCAQHDateRange`, `PRM_DueDays__c = '180'` |
