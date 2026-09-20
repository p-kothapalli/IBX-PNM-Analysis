# User Story — Re-Assessment Letter: Default Fallback Logic + Monitoring Dashboard

**Story Type:** Enhancement + Observability
**Workstream:** Ancillary / Re-Assessment
**Epic:** Provider Relations Letter Generation
**Priority:** P1 — Blocking 68 stuck assessments in production
**Approved:** 2026-05-06

---

## Story Title

**As a** Provider Relations Operations Manager,
**I want** the Re-Assessment batch to automatically generate IBX and AmeriHealth letters for all providers (regardless of state), with real-time monitoring when default letterhead logic is used,
**So that** no provider assessment silently fails letter generation, operations can monitor out-of-territory activity, and all providers receive timely Re-Assessment letters regardless of their geographic location.

---

## Background / Problem Statement

### Current State

The `PRM_CheckDueOnAncillaryReAssessmentBatch` runs daily and creates `PRM_Letter__c` records for Re-Assessment due providers. Letter creation depends on a `PRM_LetterheadIndicator__c` lookup:

```apex
String letterKey = addrPrimary.PRM_State__c + '-' + addrPrimary.PRM_County__c;  // e.g. "CA-San Mateo"

if (stateCountyVsIndicator.containsKey(letterKey)) {
    // Create letter(s) using configured letterhead key
} 
// ← NO ELSE BRANCH — silent failure if key not found
```

**`PRM_LetterheadIndicator__c` only covers DE, MD, NJ, PA counties** (IBX's traditional service territory). Any provider outside these 4 states silently fails letter generation:
- An `IndividualApplication` is created (Stage=PSV, Status=Pending Application)
- A `Case` is created
- **No letter is created** — completely silent, batch reports "Completed (0 errors)"
- The IA blocks future batch re-processing (`filterAncillaryAssessments()` removes records with existing incomplete IAs)
- The record is **permanently stuck** — letter never generated

**Confirmed impact (QA Sandbox audit):**
- **69 stuck IAs** with no letter created
- **68 of 69 (98%)** caused by missing `PRM_LetterheadIndicator__c` entries
- **7 PA counties** (Allegheny, Carbon, Cumberland, Dauphin, Lackawanna, Luzerne, Monroe) inside IBX territory but not configured
- **61 out-of-territory locations** across 21 states (CA, FL, NY, NC, TN, CO, OH, MN, GA, AZ, OK, IL, AL, MI, NH, MA, WI, TX, WV, VA, OR)

**Business Decision (2026-05-06):**
All providers should receive **BOTH IBX (IBC letterhead) and AmeriHealth (AHPA letterhead)** Re-Assessment letters, regardless of state.

---

### Proposed Future State

1. **Default Fallback Logic:** If no `PRM_LetterheadIndicator__c` exists for a provider's state-county, automatically create 2 letters with `IBC` and `AHPA` letterhead keys
2. **Preserve Existing Behavior:** DE/MD/NJ/PA providers continue using their configured letterhead indicators
3. **Observability:** Log an `Info`-level message when default logic is used (not a Warning — this is expected behavior for out-of-territory providers)
4. **Monitoring Dashboard:** Real-time visibility into:
   - How many letters are being generated via fallback vs configured indicators
   - Which states/counties are triggering fallback logic
   - Daily/weekly trends in out-of-territory letter generation
5. **Operational Reports:** Standard and custom report types to support audit and compliance

---

## Scope

This story covers **five workstreams**:

| Workstream | Deliverable | Owner |
|---|---|---|
| **WS-1** | Code Fix — Default fallback logic in `PRM_ReassessmentLetter.cls` | Engineering |
| **WS-2** | Observability — Logging + null guards | Engineering |
| **WS-3** | Reporting — Custom Report Type for Re-Assessment Letters | Engineering + Ops |
| **WS-4** | Dashboard — Real-time monitoring dashboard | Engineering + Ops |
| **WS-5** | Test Coverage — Update test class + add fallback test scenario | Engineering |

---

## Acceptance Criteria

---

### WS-1: Code Fix — Default Fallback Logic

**File:** `PRM_ReassessmentLetter.cls` — `createLetter()` method (lines 88–141)

**AC-1.1 — Add `else` branch with IBC + AHPA default letterhead creation**

```apex
// CURRENT CODE (lines 96-139):
if (stateCountyVsIndicator.containsKey(letterKey)) {
    for (PRM_LetterheadIndicator__c indicator : stateCountyVsIndicator.get(letterKey)) {
        PRM_Letter__c ltr = new PRM_Letter__c();
        ltr.RecordTypeId = PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT;
        // ... (populate all fields — lines 100-136)
        ltr.PRM_LetterheadKey__c = indicator.PRM_LetterheadKey__c;
        toInsertLetter.add(ltr);
    }
}
// ← NO ELSE — silent failure

// FIXED CODE:
if (stateCountyVsIndicator.containsKey(letterKey)) {
    // EXISTING BEHAVIOR: Use configured PRM_LetterheadIndicator__c records
    for (PRM_LetterheadIndicator__c indicator : stateCountyVsIndicator.get(letterKey)) {
        PRM_Letter__c ltr = new PRM_Letter__c();
        ltr.RecordTypeId = PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT;
        // Header
        ltr.PRM_GroupName__c       = accLocObj.hcFacility.Account.Name;
        ltr.PRM_MailingAddressld__c = accLocObj.addrMailing?.Id;
        ltr.PRM_MailingStreetAddress__c  = accLocObj.addrMailing?.PRM_AddressLine1__c;
        ltr.PRM_MailingStreetAddress2__c = accLocObj.addrMailing?.PRM_AddressLine2__c;
        ltr.PRM_MailingCity__c  = accLocObj.addrMailing?.PRM_City__c;
        ltr.PRM_MailingState__c = accLocObj.addrMailing?.PRM_State__c;
        ltr.PRM_MailingZip__c   = accLocObj.addrMailing?.PRM_Zip__c;
        ltr.PRM_EffectiveDate__c = System.now().date();
        // Body
        ltr.PRM_GroupNpi__c    = accLocObj.hcFacility.PRM_NpiId__r?.Npi;  // ← safe nav added (AC-2.4)
        ltr.PRM_GroupNpiId__c  = accLocObj.hcFacility.PRM_NpiId__c;
        ltr.PRM_PrimaryAddress__c = String.isNotBlank(accLocObj.addrPrimary.PRM_AddressLine1__c)
            ? accLocObj.addrPrimary.PRM_AddressLine1__c : '';
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_AddressLine2__c)
            ? ', ' + accLocObj.addrPrimary.PRM_AddressLine2__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_City__c)
            ? ', ' + accLocObj.addrPrimary.PRM_City__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_State__c)
            ? ', ' + accLocObj.addrPrimary.PRM_State__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_Zip__c)
            ? ' ' + accLocObj.addrPrimary.PRM_Zip__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_Zip4__c)
            ? ' - ' + accLocObj.addrPrimary.PRM_Zip4__c : '');
        ltr.PRM_MedicareNumber__c = accLocObj.identifierValues;
        // Letter Head Logic
        ltr.PRM_PrimaryAddressCountyName__c = accLocObj.addrPrimary?.PRM_StateCounty__c;
        ltr.PRM_PrimaryAddressStateCode__c  = accLocObj.addrPrimary?.PRM_State__c;
        ltr.PRM_PrimaryAddressId__c = accLocObj.addrPrimary?.Id;
        ltr.PRM_CaseManager__c   = accLocObj.caseManagerId;
        ltr.PRM_CaseNumber__c    = accLocObj.csManager.ApplicationCase.CaseNumber;
        ltr.PRM_ApplicationId__c = accLocObj.csManager.Name;
        ltr.PRM_LetterheadKey__c = indicator.PRM_LetterheadKey__c;  // ← from configured indicator
        if (accountTaxIdMap.containsKey(accLocObj.hcFacility.AccountId)) {
            ltr.PRM_TaxId__c      = accountTaxIdMap.get(accLocObj.hcFacility.AccountId).Id;
            ltr.PRM_TaxIdValue__c = accountTaxIdMap.get(accLocObj.hcFacility.AccountId).IdValue;
        }
        toInsertLetter.add(ltr);
    }
} else {
    // ✅ NEW BEHAVIOR: Default fallback — create BOTH IBC and AHPA letters
    for (String defaultKey : new String[]{'IBC', 'AHPA'}) {
        PRM_Letter__c ltr = new PRM_Letter__c();
        ltr.RecordTypeId = PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT;
        // Header (same as above)
        ltr.PRM_GroupName__c       = accLocObj.hcFacility.Account.Name;
        ltr.PRM_MailingAddressld__c = accLocObj.addrMailing?.Id;
        ltr.PRM_MailingStreetAddress__c  = accLocObj.addrMailing?.PRM_AddressLine1__c;
        ltr.PRM_MailingStreetAddress2__c = accLocObj.addrMailing?.PRM_AddressLine2__c;
        ltr.PRM_MailingCity__c  = accLocObj.addrMailing?.PRM_City__c;
        ltr.PRM_MailingState__c = accLocObj.addrMailing?.PRM_State__c;
        ltr.PRM_MailingZip__c   = accLocObj.addrMailing?.PRM_Zip__c;
        ltr.PRM_EffectiveDate__c = System.now().date();
        // Body (same as above)
        ltr.PRM_GroupNpi__c    = accLocObj.hcFacility.PRM_NpiId__r?.Npi;
        ltr.PRM_GroupNpiId__c  = accLocObj.hcFacility.PRM_NpiId__c;
        ltr.PRM_PrimaryAddress__c = String.isNotBlank(accLocObj.addrPrimary.PRM_AddressLine1__c)
            ? accLocObj.addrPrimary.PRM_AddressLine1__c : '';
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_AddressLine2__c)
            ? ', ' + accLocObj.addrPrimary.PRM_AddressLine2__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_City__c)
            ? ', ' + accLocObj.addrPrimary.PRM_City__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_State__c)
            ? ', ' + accLocObj.addrPrimary.PRM_State__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_Zip__c)
            ? ' ' + accLocObj.addrPrimary.PRM_Zip__c : '');
        ltr.PRM_PrimaryAddress__c += (String.isNotBlank(accLocObj.addrPrimary.PRM_Zip4__c)
            ? ' - ' + accLocObj.addrPrimary.PRM_Zip4__c : '');
        ltr.PRM_MedicareNumber__c = accLocObj.identifierValues;
        // Letter Head Logic
        ltr.PRM_PrimaryAddressCountyName__c = accLocObj.addrPrimary?.PRM_StateCounty__c;
        ltr.PRM_PrimaryAddressStateCode__c  = accLocObj.addrPrimary?.PRM_State__c;
        ltr.PRM_PrimaryAddressId__c = accLocObj.addrPrimary?.Id;
        ltr.PRM_CaseManager__c   = accLocObj.caseManagerId;
        ltr.PRM_CaseNumber__c    = accLocObj.csManager.ApplicationCase.CaseNumber;
        ltr.PRM_ApplicationId__c = accLocObj.csManager.Name;
        ltr.PRM_LetterheadKey__c = defaultKey;  // ← 'IBC' or 'AHPA' default
        if (accountTaxIdMap.containsKey(accLocObj.hcFacility.AccountId)) {
            ltr.PRM_TaxId__c      = accountTaxIdMap.get(accLocObj.hcFacility.AccountId).Id;
            ltr.PRM_TaxIdValue__c = accountTaxIdMap.get(accLocObj.hcFacility.AccountId).IdValue;
        }
        toInsertLetter.add(ltr);
    }
    
    // ✅ Log Info message (not Warning — fallback is expected behavior)
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter createLetter', '', 'Info', '',
        'Default letterhead fallback used — no PRM_LetterheadIndicator__c found for ' + letterKey,
        'LetterheadFallback', 0, '',
        'Generated IBC + AHPA letters for Account: ' + accId 
            + ' | State: ' + accLocObj.addrPrimary.PRM_State__c 
            + ' | County: ' + accLocObj.addrPrimary.PRM_County__c
            + ' | AccountName: ' + accLocObj.hcFacility.Account.Name,
        'Salesforce', '', 
        JSON.serialize(new Map<String, String>{
            'AccountId' => String.valueOf(accId),
            'State' => accLocObj.addrPrimary.PRM_State__c,
            'County' => accLocObj.addrPrimary.PRM_County__c,
            'LetterKey' => letterKey
        })
    );
}
```

**AC-1.2 — Existing DE/MD/NJ/PA behavior unchanged**

- Providers whose primary address state-county has a matching `PRM_LetterheadIndicator__c` continue to use the configured indicator(s)
- No behavior change for the existing 50+ configured state-county combos
- If multiple indicators exist for the same state-county (e.g., `NJ-Camden` has both `IBC` and `AHNJ`), multiple letters are still created (by design)

**AC-1.3 — Dual letters created for fallback cases**

- Any provider **not** in DE/MD/NJ/PA (or in PA but in an unconfigured county) gets exactly **2 letters**
- One letter with `PRM_LetterheadKey__c = 'IBC'`
- One letter with `PRM_LetterheadKey__c = 'AHPA'`
- Both letters linked to the same `PRM_CaseManager__c` (IndividualApplication Id)

---

### WS-2: Observability — Logging + Additional Guards

**File:** `PRM_ReassessmentLetter.cls` — `generateLetter()` and `createLetter()` methods

**AC-2.1 — Log when no active primary HealthcareFacility exists**

Insert after the HCF query loop in `generateLetter()` (after line ~43):

```apex
// ✅ NEW: Detect accounts with no primary active HCF before calling createLetter()
List<String> missingHCF = new List<String>();
for (Id accId : accLocMap.keySet()) {
    if (accLocMap.get(accId).hcFacility == null) {
        missingHCF.add(accId);
    }
}
if (!missingHCF.isEmpty()) {
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter generateLetter', '', 'Warning', '',
        'No active primary HealthcareFacility found for ' + missingHCF.size() + ' account(s)',
        'DataQualityWarning', 0, '',
        'Accounts missing HCF: ' + String.join(missingHCF, ', '),
        'Salesforce', '', JSON.serialize(missingHCF)
    );
}
```

**AC-2.2 — Guard against null `addrPrimary` in `createLetter()`**

Insert at the top of the `for(Id accId: accLocMap.keySet())` loop in `createLetter()` (before line 94):

```apex
// ✅ NEW: Skip accounts with no primary address (prevents 'null-null' key)
if (accLocObj.addrPrimary == null) {
    PRM_ExceptionLogger.logException(
        'ReassessmentLetter createLetter', '', 'Warning', '',
        'No active primary Address for account — cannot generate letter',
        'DataQualityWarning', 0, '',
        'AccountId: ' + accId + ' | HealthcareFacility found: ' + (accLocObj.hcFacility != null),
        'Salesforce', '', ''
    );
    continue;  // ← skip this account, move to next
}
```

**AC-2.3 — Guard against null ApplicationCase reference**

The field `accLocObj.csManager.ApplicationCase.CaseNumber` (line 130) can throw a NullPointerException if `ApplicationCaseId` was not successfully populated during the IA/Case cross-link update. Add a guard:

```apex
// Line 130 — current:
ltr.PRM_CaseNumber__c = accLocObj.csManager.ApplicationCase.CaseNumber;

// Fixed:
ltr.PRM_CaseNumber__c = accLocObj.csManager.ApplicationCase?.CaseNumber;
```

**AC-2.4 — Use safe navigation on NPI relationship (already in AC-1.1)**

Line 110: change `accLocObj.hcFacility.PRM_NpiId__r.Npi` to `accLocObj.hcFacility.PRM_NpiId__r?.Npi`

**AC-2.5 — All new logs are queryable in `PRM_ExceptionLog__c`**

- Severity: `Info` for fallback usage (expected behavior), `Warning` for data quality issues (missing HCF, missing address)
- Exception Type: Use distinct values (`LetterheadFallback`, `DataQualityWarning`) to enable filtering in reports
- Message body must include: AccountId, State, County, and any other context needed for ops investigation

---

### WS-3: Reporting — Custom Report Type for Re-Assessment Letter Monitoring

**Deliverable:** Custom Report Type `PRM_ReAssessment_Letters_with_Fallback_Info`

**AC-3.1 — Create Custom Report Type**

- **Primary Object:** `PRM_Letter__c`
- **Related Object A:** `IndividualApplication` (via `PRM_CaseManager__c` lookup)
- **Related Object B:** `Account` (via `IndividualApplication.AccountId`)
- **Filter:** RecordType = `PRM_ReAssessment`

**Fields available in report:**

| Field | Source | Purpose |
|---|---|---|
| Letter Name | `PRM_Letter__c.Name` | Letter identifier |
| Letter Created Date | `PRM_Letter__c.CreatedDate` | When letter was generated |
| Letterhead Key | `PRM_Letter__c.PRM_LetterheadKey__c` | IBC, AHPA, or other |
| Effective Date | `PRM_Letter__c.PRM_EffectiveDate__c` | Letter effective date |
| Group Name | `PRM_Letter__c.PRM_GroupName__c` | Provider name |
| Primary Address State | `PRM_Letter__c.PRM_PrimaryAddressStateCode__c` | State code (PA, CA, etc.) |
| Primary Address County | `PRM_Letter__c.PRM_PrimaryAddressCountyName__c` | County name |
| Case Number | `PRM_Letter__c.PRM_CaseNumber__c` | Linked case |
| IA Id | `PRM_Letter__c.PRM_CaseManager__c` | IndividualApplication Id |
| IA Stage | `IndividualApplication.PRM_Stage__c` | IA stage (PSV, etc.) |
| IA Status | `IndividualApplication.Status` | IA status |
| Account Name | `Account.Name` | Provider account name |
| Account Billing State | `Account.BillingState` | Account billing state |

**AC-3.2 — Create Standard Report: "Re-Assessment Letters with Fallback Usage"**

| Report Attribute | Value |
|---|---|
| Report Type | `PRM_ReAssessment_Letters_with_Fallback_Info` |
| Report Format | Summary (grouped by State) |
| Time Frame | Current Month |
| Columns | Letter Name, Created Date, Letterhead Key, State, County, Group Name |
| Filter 1 | `RecordType = PRM_ReAssessment` |
| Filter 2 | `CreatedDate >= LAST_N_DAYS:30` |
| Grouping | Primary Address State (ascending) |
| Summary | COUNT of Letter Id by State, COUNT of Letter Id by Letterhead Key |

**Expected output:**
```
STATE: CA
  Letterhead Key: AHPA — 15 letters
  Letterhead Key: IBC  — 15 letters
  Subtotal: 30 letters

STATE: FL
  Letterhead Key: AHPA — 8 letters
  Letterhead Key: IBC  — 8 letters
  Subtotal: 16 letters

STATE: PA
  Letterhead Key: IBC  — 12 letters
  Letterhead Key: AHPA — 5 letters
  Subtotal: 17 letters

GRAND TOTAL: 63 letters
```

**AC-3.3 — Create Standard Report: "Letterhead Fallback Log (Info Messages)"**

| Report Attribute | Value |
|---|---|
| Report Type | `PRM_ExceptionLog__c` (standard) |
| Report Format | Tabular |
| Time Frame | Current Month |
| Columns | Created Date, Exception Type, Message, Details (JSON field with AccountId/State/County) |
| Filter 1 | `PRM_Severity__c = Info` |
| Filter 2 | `PRM_ExceptionType__c = LetterheadFallback` |
| Sort | Created Date DESC |

**AC-3.4 — Create Standard Report: "Missing HealthcareFacility or Address Warnings"**

| Report Attribute | Value |
|---|---|
| Report Type | `PRM_ExceptionLog__c` (standard) |
| Report Format | Tabular |
| Time Frame | Current Month |
| Columns | Created Date, Method Name, Message, Details |
| Filter 1 | `PRM_Severity__c = Warning` |
| Filter 2 | `PRM_ExceptionType__c = DataQualityWarning` |
| Filter 3 | `PRM_MethodName__c CONTAINS ReassessmentLetter` |
| Sort | Created Date DESC |

---

### WS-4: Dashboard — Real-Time Monitoring

**Deliverable:** Lightning Dashboard `PRM_ReAssessment_Letter_Monitoring_Dashboard`

**AC-4.1 — Create Lightning Dashboard with 6 components**

Dashboard layout (2-column, 3 rows):

```
┌────────────────────────────────────────────────────────┐
│  Re-Assessment Letter Monitoring Dashboard (Last 30d)  │
├───────────────────────────┬────────────────────────────┤
│ 📊 Total Letters Generated│ 📊 Letterhead Key Breakdown│
│    (Count by Date)        │    (IBC vs AHPA vs Others) │
├───────────────────────────┼────────────────────────────┤
│ 🗺️  Letters by State       │ ⚠️  Fallback Usage Trend   │
│    (Top 10 States)        │    (Fallback vs Configured)│
├───────────────────────────┼────────────────────────────┤
│ 🔔 Recent Data Quality    │ 📋 Stuck IAs (No Letter)   │
│    Warnings (Last 7 days) │    (Real-time count)       │
└───────────────────────────┴────────────────────────────┘
```

**Component 1 — Total Letters Generated (Line Chart)**
- **Report:** "Re-Assessment Letters Created (Last 30 Days)" — grouped by Created Date
- **Chart Type:** Line Chart
- **X-Axis:** Created Date (daily)
- **Y-Axis:** Count of Letter Id
- **Purpose:** Monitor daily letter generation volume

**Component 2 — Letterhead Key Breakdown (Donut Chart)**
- **Report:** "Re-Assessment Letters by Letterhead Key (Last 30 Days)" — grouped by Letterhead Key
- **Chart Type:** Donut Chart
- **Grouping:** Letterhead Key (IBC, AHPA, others)
- **Purpose:** Visualize distribution of IBX vs AmeriHealth letters

**Component 3 — Letters by State (Horizontal Bar Chart)**
- **Report:** "Re-Assessment Letters by State (Top 10)" — grouped by Primary Address State, sorted by count DESC, limit 10
- **Chart Type:** Horizontal Bar Chart
- **X-Axis:** Count of Letter Id
- **Y-Axis:** Primary Address State
- **Purpose:** Identify which states generate the most letters

**Component 4 — Fallback Usage Trend (Stacked Bar Chart)**
- **Report:** "Fallback vs Configured Letterhead Usage" — requires a **cross-object report** joining `PRM_Letter__c` and `PRM_ExceptionLog__c`
  - **Alternative approach if cross-object not supported:** Use a gauge/metric component showing count of `PRM_ExceptionLog__c` records with `ExceptionType = LetterheadFallback` in last 30 days
- **Chart Type:** Metric (count)
- **Metric Label:** "Fallback Letters (Last 30d)"
- **Purpose:** Track how many letters are using default vs configured indicators

**Component 5 — Recent Data Quality Warnings (Table)**
- **Report:** "Missing HealthcareFacility or Address Warnings" (from AC-3.4)
- **Rows to Display:** 10
- **Purpose:** Alert ops to data quality issues requiring immediate attention

**Component 6 — Stuck IAs (No Letter) — Real-time Count (Metric)**
- **Report:** Custom report on `IndividualApplication`
  - Filter: `RecordType = PRM_AncillaryReAssessment` AND `Stage != Complete` AND `Id NOT IN (SELECT PRM_CaseManager__c FROM PRM_Letter__c WHERE RecordType = PRM_ReAssessment)`
  - **Note:** This requires a **cross-object filter** which is not natively supported in Salesforce reports. **Alternative:** Use a **scheduled flow** that populates a custom field `PRM_HasLetter__c` (checkbox) on `IndividualApplication` nightly, then report filters on `PRM_HasLetter__c = false`
- **Chart Type:** Metric (count)
- **Threshold:** Red if count > 0, Green if count = 0
- **Purpose:** Real-time alert if any IAs are stuck without letters

**AC-4.2 — Dashboard visibility and permissions**

- Dashboard visibility: Public (folder: `Provider Relations Reports`)
- View access: All users with `PRM_CredentialingUser` permission set
- Edit access: System Administrator, `PRM_ReportsAdmin` permission set

**AC-4.3 — Dashboard refresh schedule**

- Auto-refresh: Enabled, every 3 hours
- Manual refresh: Users can click "Refresh" anytime

---

### WS-5: Test Coverage — Update Test Class

**File:** `PRM_CheckDueOnAncillaryReAssessBatchTest.cls`

**AC-5.1 — Fix broken `@testSetup`: set `PRM_DueDays__c`**

Current setup inserts `PRM_CAQHDateRangeSetting__c` with all null date fields, causing the batch to query 0 records. Fix:

```apex
// CURRENT (line 60-63):
PRM_CAQHDateRangeSetting__c reAssessmentDateRange = new PRM_CAQHDateRangeSetting__c(
    Name = 'ReAssessmentCAQHDateRange'
);

// FIXED:
PRM_CAQHDateRangeSetting__c reAssessmentDateRange = new PRM_CAQHDateRangeSetting__c(
    Name = 'ReAssessmentCAQHDateRange',
    PRM_DueDays__c = '180'  // ← batch will query for records with due date = today + 180
);

// Also fix the assessment due date to match (line 45):
PRM_ReAssessmentDueDate__c = System.today().addDays(180),  // ← was hardcoded, now matches DueDays
```

**AC-5.2 — Fix `@testSetup`: align LetterheadIndicator with test address**

Current setup creates `PRM_LetterheadIndicator__c` for `DE-New Castle` but the test account address is not set to DE. Either:
- Set test address to DE, OR
- **Remove the LetterheadIndicator insert entirely** (fallback logic should be tested instead)

**Recommendation:** Remove the `PRM_LetterheadIndicator__c` insert to test the **fallback path**.

**AC-5.3 — Update positive test: assert 2 letters created (IBC + AHPA)**

```apex
@isTest
static void testBatchExecution_fallbackLetters() {
    // Setup: assessment with no matching LetterheadIndicator → fallback logic triggers
    
    Test.startTest();
    PRM_CheckDueOnAncillaryReAssessmentBatch batch = new PRM_CheckDueOnAncillaryReAssessmentBatch();
    Database.executeBatch(batch);
    Test.stopTest();

    // Assert IA created
    List<IndividualApplication> iaList = [
        SELECT Id FROM IndividualApplication
        WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPE_ANCILLARYREASSESSMENT
    ];
    System.assertEquals(1, iaList.size(), 'Expected 1 IA to be created');

    // Assert 2 letters created (IBC + AHPA fallback)
    List<PRM_Letter__c> letters = [
        SELECT Id, PRM_LetterheadKey__c FROM PRM_Letter__c
        WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT
        ORDER BY PRM_LetterheadKey__c ASC
    ];
    System.assertEquals(2, letters.size(), 'Expected 2 letters (IBC + AHPA) via fallback logic');
    System.assertEquals('AHPA', letters[0].PRM_LetterheadKey__c, 'First letter should be AHPA');
    System.assertEquals('IBC', letters[1].PRM_LetterheadKey__c, 'Second letter should be IBC');

    // Assert Info log created for fallback usage
    List<PRM_ExceptionLog__c> logs = [
        SELECT Id, PRM_ExceptionType__c, PRM_Severity__c FROM PRM_ExceptionLog__c
        WHERE PRM_ExceptionType__c = 'LetterheadFallback'
    ];
    System.assertEquals(1, logs.size(), 'Expected 1 Info log for fallback usage');
    System.assertEquals('Info', logs[0].PRM_Severity__c, 'Fallback log should be Info severity');
}
```

**AC-5.4 — Add test: configured LetterheadIndicator still works (existing behavior preserved)**

```apex
@isTest
static void testBatchExecution_configuredIndicator() {
    // Setup: Insert a LetterheadIndicator matching the test address state-county
    delete [SELECT Id FROM PRM_LetterheadIndicator__c];  // clear any from setup
    
    // Get test account address
    Account vendorAcc = [SELECT Id FROM Account WHERE RecordType.DeveloperName = :PRM_GlobalConstant.RECTYPE_VENDOR LIMIT 1];
    HealthcareFacility hcf = [SELECT LocationId FROM HealthcareFacility WHERE AccountId = :vendorAcc.Id AND PRM_Primary__c = true LIMIT 1];
    Address addr = [SELECT PRM_State__c, PRM_County__c FROM Address WHERE ParentId = :hcf.LocationId AND PRM_AddressType__c INCLUDES ('Primary') LIMIT 1];
    
    // Insert matching indicator
    insert new PRM_LetterheadIndicator__c(
        PRM_StateCode__c = addr.PRM_State__c,
        PRM_CountyName__c = addr.PRM_County__c,
        PRM_LetterheadKey__c = 'TEST_KEY',
        PRM_Category__c = 'Test Category'
    );

    Test.startTest();
    Database.executeBatch(new PRM_CheckDueOnAncillaryReAssessmentBatch());
    Test.stopTest();

    // Assert 1 letter created with configured key (not fallback)
    List<PRM_Letter__c> letters = [
        SELECT Id, PRM_LetterheadKey__c FROM PRM_Letter__c
        WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT
    ];
    System.assertEquals(1, letters.size(), 'Expected 1 letter using configured indicator');
    System.assertEquals('TEST_KEY', letters[0].PRM_LetterheadKey__c, 'Letter should use configured key, not fallback');

    // Assert NO fallback log
    List<PRM_ExceptionLog__c> logs = [
        SELECT Id FROM PRM_ExceptionLog__c WHERE PRM_ExceptionType__c = 'LetterheadFallback'
    ];
    System.assertEquals(0, logs.size(), 'No fallback log should be created when indicator is configured');
}
```

**AC-5.5 — Add test: multiple configured indicators create multiple letters (by design)**

```apex
@isTest
static void testBatchExecution_multipleIndicators() {
    // Setup: Insert TWO LetterheadIndicators for the same state-county
    delete [SELECT Id FROM PRM_LetterheadIndicator__c];
    
    Account vendorAcc = [SELECT Id FROM Account WHERE RecordType.DeveloperName = :PRM_GlobalConstant.RECTYPE_VENDOR LIMIT 1];
    HealthcareFacility hcf = [SELECT LocationId FROM HealthcareFacility WHERE AccountId = :vendorAcc.Id AND PRM_Primary__c = true LIMIT 1];
    Address addr = [SELECT PRM_State__c, PRM_County__c FROM Address WHERE ParentId = :hcf.LocationId AND PRM_AddressType__c INCLUDES ('Primary') LIMIT 1];
    
    insert new List<PRM_LetterheadIndicator__c>{
        new PRM_LetterheadIndicator__c(
            PRM_StateCode__c = addr.PRM_State__c, PRM_CountyName__c = addr.PRM_County__c,
            PRM_LetterheadKey__c = 'IBC', PRM_Category__c = 'Test'
        ),
        new PRM_LetterheadIndicator__c(
            PRM_StateCode__c = addr.PRM_State__c, PRM_CountyName__c = addr.PRM_County__c,
            PRM_LetterheadKey__c = 'AHPA', PRM_Category__c = 'Test'
        )
    };

    Test.startTest();
    Database.executeBatch(new PRM_CheckDueOnAncillaryReAssessmentBatch());
    Test.stopTest();

    // Assert 2 letters created (one per indicator, NOT fallback)
    List<PRM_Letter__c> letters = [
        SELECT Id, PRM_LetterheadKey__c FROM PRM_Letter__c
        WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT
        ORDER BY PRM_LetterheadKey__c ASC
    ];
    System.assertEquals(2, letters.size(), 'Expected 2 letters from 2 configured indicators');
    System.assertEquals('AHPA', letters[0].PRM_LetterheadKey__c);
    System.assertEquals('IBC', letters[1].PRM_LetterheadKey__c);

    // Assert NO fallback log (configured indicators were used)
    List<PRM_ExceptionLog__c> logs = [
        SELECT Id FROM PRM_ExceptionLog__c WHERE PRM_ExceptionType__c = 'LetterheadFallback'
    ];
    System.assertEquals(0, logs.size(), 'No fallback log when indicators are configured');
}
```

**AC-5.6 — Add negative test: null address triggers warning, no letter**

```apex
@isTest
static void testBatchExecution_nullAddress_logsWarning() {
    // Setup: Create assessment but delete the primary address to force null addrPrimary
    Account vendorAcc = [SELECT Id FROM Account WHERE RecordType.DeveloperName = :PRM_GlobalConstant.RECTYPE_VENDOR LIMIT 1];
    HealthcareFacility hcf = [SELECT LocationId FROM HealthcareFacility WHERE AccountId = :vendorAcc.Id LIMIT 1];
    delete [SELECT Id FROM Address WHERE ParentId = :hcf.LocationId AND PRM_AddressType__c INCLUDES ('Primary')];

    Test.startTest();
    Database.executeBatch(new PRM_CheckDueOnAncillaryReAssessmentBatch());
    Test.stopTest();

    // Assert no letter created
    List<PRM_Letter__c> letters = [
        SELECT Id FROM PRM_Letter__c WHERE RecordTypeId = :PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT
    ];
    System.assertEquals(0, letters.size(), 'No letter should be created when primary address is missing');

    // Assert warning log created
    List<PRM_ExceptionLog__c> logs = [
        SELECT Id, PRM_Severity__c FROM PRM_ExceptionLog__c
        WHERE PRM_ExceptionType__c = 'DataQualityWarning'
          AND PRM_MethodName__c = 'ReassessmentLetter createLetter'
    ];
    System.assertEquals(1, logs.size(), 'Expected 1 warning log for missing address');
    System.assertEquals('Warning', logs[0].PRM_Severity__c);
}
```

---

## Technical Implementation Notes

### Code Refactoring Opportunity

The letter field population logic (lines 98-136) is **duplicated** in both the `if` and `else` branches. Consider extracting to a helper method:

```apex
private static PRM_Letter__c buildLetterRecord(AccLocDetails accLocObj, String letterheadKey) {
    PRM_Letter__c ltr = new PRM_Letter__c();
    ltr.RecordTypeId = PRM_GlobalConstant.RECTYPEID_PRM_REASSESSMENT;
    // ... all field population logic
    ltr.PRM_LetterheadKey__c = letterheadKey;
    return ltr;
}

// Then in createLetter():
if (stateCountyVsIndicator.containsKey(letterKey)) {
    for (PRM_LetterheadIndicator__c indicator : stateCountyVsIndicator.get(letterKey)) {
        toInsertLetter.add(buildLetterRecord(accLocObj, indicator.PRM_LetterheadKey__c));
    }
} else {
    for (String defaultKey : new String[]{'IBC', 'AHPA'}) {
        toInsertLetter.add(buildLetterRecord(accLocObj, defaultKey));
    }
    // ... log Info message
}
```

This reduces code duplication and makes future maintenance easier.

---

### Dashboard Implementation Note (AC-4.1, Component 6)

Salesforce standard reports **cannot natively filter on records that do NOT exist in a related object** (i.e., "IAs with no letters" requires a NOT IN subquery, which is not supported in report builder).

**Workaround options:**

**Option A — Scheduled Flow (Recommended):**
1. Create a custom checkbox field: `IndividualApplication.PRM_HasReAssessmentLetter__c`
2. Create a scheduled flow (runs nightly at 2 AM):
   - Query all IAs with `RecordType = PRM_AncillaryReAssessment` AND `Stage != Complete`
   - For each IA, query `PRM_Letter__c` WHERE `PRM_CaseManager__c = :ia.Id` AND `RecordType = PRM_ReAssessment`
   - Set `PRM_HasReAssessmentLetter__c = true` if letter found, `false` if not
3. Report filters on `PRM_HasReAssessmentLetter__c = false`

**Option B — Custom Lightning Web Component:**
Build a custom LWC that runs the SOQL query directly (with NOT IN subquery) and displays the count as a dashboard metric component.

**Option C — Exclude from Dashboard:**
Remove Component 6 from the dashboard and rely on the remediation script (run on-demand) to identify stuck IAs.

**Recommendation:** Use **Option A** (scheduled flow) — most maintainable, no code deployment needed, non-technical admins can troubleshoot.

---

## Definition of Done

- [ ] **WS-1 complete:** Code fix deployed to QA, fallback logic tested, 2 letters created for out-of-territory provider
- [ ] **WS-2 complete:** All 4 logging guards implemented, tested, logs queryable in `PRM_ExceptionLog__c`
- [ ] **WS-3 complete:** Custom Report Type created, 3 standard reports created and tested
- [ ] **WS-4 complete:** Dashboard created with 6 components (or 5 if Component 6 excluded per implementation note)
- [ ] **WS-5 complete:** Test class updated, 5 new test methods added, all tests pass with >75% coverage
- [ ] Code review completed, approved by Lead Engineer
- [ ] Deployment to QA: zero errors, batch runs successfully
- [ ] Manual QA testing: out-of-territory provider gets 2 letters (IBC + AHPA), dashboard displays data
- [ ] User acceptance testing: Ops team reviews dashboard, confirms reports meet their needs
- [ ] Remediation script run: 68 stuck IAs remediated (136 letters created)
- [ ] Production deployment approved, change control ticket closed
- [ ] Post-deployment monitoring: dashboard reviewed for 3 consecutive batch runs, no silent failures

---

## Story Points Estimate

| Workstream | Effort | Notes |
|---|---|---|
| WS-1: Code fix (fallback logic) | 3 pts | Straightforward else branch + refactor helper method |
| WS-2: Observability (logging + guards) | 2 pts | 4 guards, straightforward |
| WS-3: Custom Report Type + 3 reports | 3 pts | Report type config, 3 reports with groupings |
| WS-4: Dashboard (6 components) | 5 pts | Dashboard + flow for Component 6 if using Option A |
| WS-5: Test class updates (5 new tests) | 3 pts | Test scenarios are well-defined |
| **Total** | **16 pts** | ~2 sprints (assuming 8-10 pts/sprint) |

> If Component 6 is excluded (Option C), WS-4 = 3 pts → **Total 14 pts**

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Fallback logic creates too many letters for configured states (regression) | High | WS-5 AC-5.4/5.5 explicitly test that configured indicators are still used (no fallback) |
| Dashboard Component 6 (stuck IAs) requires custom code | Medium | Use Option A (scheduled flow) — no code, admin-configurable |
| Ops team unfamiliar with new dashboard | Low | Provide training session + quick reference guide |
| Production data has edge cases not covered by tests (e.g., null Tax ID) | Medium | WS-2 logging catches all edge cases; monitor `PRM_ExceptionLog__c` for 1 week post-deployment |
| Remediation script run before code fix deployed | High | **Strict deployment order:** 1) Code fix to prod, 2) Verify batch runs successfully with fallback, 3) Run remediation script |

---

## Related Artifacts

| Artifact | Location |
|---|---|
| Affected Assessment | `a1VUW00000HHx9r2AD` (Genomic Health Inc) |
| Affected IA | `0iTUW000000L2LA2A0` |
| Batch Class | `PRM_CheckDueOnAncillaryReAssessmentBatch.cls` |
| Letter Class | `PRM_ReassessmentLetter.cls` |
| Test Class | `PRM_CheckDueOnAncillaryReAssessBatchTest.cls` |
| Remediation Script | `.agents/artifacts/stuck-ia-remediation-script.apex` |
| Original Bug Analysis | `requirements/ReAssessment_Letter_Silent_Failure_UserStory.md` |
| Audit Results | 68 out of 69 stuck IAs caused by missing letterhead indicators |

---

## Open Questions (Resolved 2026-05-06)

All questions resolved — see Business Decisions section at top of story.

**Pending confirmation:**
- **OQ-7:** Remediation SLA — is there a compliance deadline for late letters? ⏳ Awaiting business response
