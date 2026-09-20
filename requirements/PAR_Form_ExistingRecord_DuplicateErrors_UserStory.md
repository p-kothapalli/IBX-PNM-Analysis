# PAR Form — Existing Practitioner / Vendor Record Duplicate Errors: Root Cause & Fix

**Document Version:** 1.0
**Created Date:** May 11, 2026
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_PractitionerParticipationForm_English` (Active QA version **v111**; v112 is a dev draft)
**Source Data:** `Copy of Duplicate account and tax id errors.xlsx` (19 failed PAR submissions, May 2026)
**Related Documents:**
- `PAR_DeniedTerminated_RecordReuse_User_Stories.md` (UC-3 / UC-4 — similar reuse problem for denied/terminated records)
- `PAR_Form_PNC_Path_User_Stories.md`
- `Practitioner_Participation_Form_Complete_Record_Creation_Analysis.md`
- `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`

---

## Executive Summary

Sr. Data Reporting Analysts and Reps are unable to submit the **Practitioner Participation (PAR) Form** for **19 distinct provider/vendor combinations** because the form attempts to insert new Account / HealthcareProvider / HealthcareProviderTaxonomy records when the practitioner or vendor (group) already exists in the org. All failures resolve to **one of three duplicate-record errors** thrown by Salesforce DML or the OmniStudio DataRaptor Load engine.

The form's "Existing NPI" detection (`PractitionerForm:IsExistingNPI`) is computed solely from a `HealthCareProviderNpi → Account` join inside `PRMDRExtractExistingNPIInfo`. **When the practitioner's `HealthCareProviderNpi` record is absent or its `AccountId` link is broken**, the IP routes to the **create-new-Account** path even though the practitioner Account already exists. The create path then collides with the unique External Id on `Account.HealthCloudGA__SourceSystemId__c`, the unique constraint on `HealthcareProvider.SourceSystemIdentifier` (auto-populated by `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier`), or the (AccountId, TaxonomyId) composite key on `HealthcareProviderTaxonomy`.

This story consolidates all three failure modes into a single fix covering: (a) broader existing-record detection, (b) safe upsert semantics on Account/HealthcareProvider creation DRs, (c) data-cleanup and prevention for duplicate HCPT junction rows, and (d) UI surfacing so the analyst is never silently routed to a duplicate-block path.

---

## Failure Inventory (from `Copy of Duplicate account and tax id errors.xlsx`)

### Error Category A — Account Insert Blocked (`HealthCloudGA__SourceSystemId__c`)

`duplicate value found: HealthCloudGA__SourceSystemId__c duplicates value on record with id: 001UW...`

| Row | Fhnatic Case | Provider | NPI | Group Tax ID | Existing Account Id | Notes (state of system) |
|-----|--------------|----------|-----|--------------|---------------------|-------------------------|
| 3 | 663776 | George Henry | 1932179090 | 222763588 | `001UW00000eiR46YAE` | Non-par : provider; Active : Account & Tax ID |
| 6 | 677637 | Melanie Weaver | 1801188388 | 844050618 | `001UW00000ejxCcYAI` | Provider not in PIE; Active : Account & Tax ID |

**Cause:** Practitioner Account already exists (with `HealthCloudGA__SourceSystemId__c` = NPI), but `HealthCareProviderNpi` linkage is missing/broken → `PRMDRExtractExistingNPIInfo` returns `ExistingAccountId = NULL` → `IsExistingNPI = false` → create path taken → unique External Id constraint trips.

### Error Category B — HealthcareProvider Insert Blocked (`SourceSystemIdentifier`)

`duplicate value found: SourceSystemIdentifier duplicates value on record with id: 0bSUW...`

| Row | Fhnatic Case | Provider | NPI | Group | Existing HC Provider Id | Notes |
|-----|--------------|----------|-----|-------|--------------------------|-------|
| 10 | 698724 | Ovsev Uzuner | 1437203346 | Rittenhouse Imaging Center LLC | `0bSUW000000Buy92AC` | Provider cred in progress, non-par; Active Vendor & Tax ID |
| 16 | 708088 | Sandi McKay | 1972200632 | AtlantiCare Physician Group | `0bSUW000000FTJS2A4` | Provider cred in progress, participating; Active Account & Tax ID |
| 20 | 674985 | Igor Povshitkov | 1700924669 | Advanced Ambulatory Anesthesia LLC | `0bSUW000000GoaM2AS` | Provider cred in progress, participating; Active Account & Tax ID |

**Cause:** A `HealthcareProvider` (object `0bS...`) already exists for this provider+group combination. The form re-creates it. The before-insert trigger `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` computes `SourceSystemIdentifier = identifier.IdValue + '-' + acc.Name` (EIN Tax-Id + Account Name); the resulting value is identical to the existing record's, and the unique constraint on `SourceSystemIdentifier` blocks the insert.

### Error Category C — HealthcareProviderTaxonomy Upsert Match Conflict

`Duplicated results found for HealthcareProviderTaxonomy AccountId=001UW... AND TaxonomyId=0bKUW... - Related Ids: 0bPUW...,0bPUW.... Delete or fix duplicate records before importing.`

| Row | Fhnatic Case | Provider | NPI | Account Id (Practitioner) | Taxonomy Id | Duplicate HCPT Ids |
|-----|--------------|----------|-----|---------------------------|-------------|---------------------|
| 5 | 673515 | Hyesun Lee | 1053793505 | `001UW00000eiED1YAM` | `0bKUW00000000qI2AQ` | `0bPUW00000073lx2AA`, `0bPUW0000007jid2AA` |
| 7 | 695317 | Charles E Digby | 1629208095 | `001UW00000ej33JYAQ` | `0bKUW00000000hC2AQ` | `0bPUW0000006rXt2AI`, `0bPUW0000007jzT2AQ` |
| 8 | 695435 | Bryan Romero | 1487244414 | `001UW00000vCYhvYAG` | `0bKUW00000000qI2AQ` | `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` |
| 9 | 697360 | Amir Hedayati | 1770534869 | `001UW00000i9PM1YAM` | `0bKUW00000000jg2AA` | `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` |
| 11 | 699856 | Amir Hedayati | 1770534869 | `001UW00000i9PM1YAM` | `0bKUW00000000jg2AA` | `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` |
| 12 | 701509 | Bryan Romero | 1487244414 | `001UW00000vCYhvYAG` | `0bKUW00000000qI2AQ` | `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` |
| 13 | 701737 | Erin McNeilly | 1174744783 | `001UW00000eivAwYAI` | `0bKUW00000000qI2AQ` | `0bPUW0000003rJp2AI`, `0bPUW0000008cJR2AY` |
| 14 | 703594 | Bryan Romero | 1487244414 | `001UW00000vCYhvYAG` | `0bKUW00000000qI2AQ` | `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` |
| 17 | 711166 | Amir Hedayati | 1770534869 | `001UW00000i9PM1YAM` | `0bKUW00000000jg2AA` | `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` |
| 19 | 712069 | Hyesun Lee | 1053793505 | `001UW00000eiED1YAM` | `0bKUW00000000qI2AQ` | `0bPUW00000073lx2AA`, `0bPUW0000007jid2AA` |

**Cause:** Two `HealthcareProviderTaxonomy` rows already exist in the DB for the same `(AccountId, TaxonomyId)` composite. The OmniStudio DataRaptor Load engine's upsert match returns 2+ records → it cannot decide which to update → throws the standard "Duplicated results found ... Delete or fix duplicate records before importing" error. The duplicates are pre-existing data — only 5 distinct (Account, Taxonomy) pairs underlie the 10 failures.

### Error Category D — Generic / Catch-All

| Row | Provider | Error |
|-----|----------|-------|
| 21 | (no provider info; Igor Povshitkov context) | "Please contact your administration" |

**Cause:** Final fallback message presented to the user when one of A/B/C fires inside a sub-procedure where the original SOQL/DML error is swallowed. Same root cause as one of the above; the lack of error specificity is itself a defect because it prevents analysts from self-diagnosing.

---

## Per-Row Issue → Fix Mapping

This table maps every failure row from `Copy of Duplicate account and tax id errors.xlsx` to its specific root cause, the exact code change(s) that resolve it (numbered per the Technical Section → *Changes Required* table below), and the acceptance criteria that verify the fix. Rows 4, 15, and 18 in the original spreadsheet are address-spillover continuations of the row above and not separate failures.

**Legend — Category:** A = Account dup (`HealthCloudGA__SourceSystemId__c`) · B = HealthcareProvider dup (`SourceSystemIdentifier`) · C = HealthcareProviderTaxonomy duplicated upsert match · D = Generic catch-all.
**Legend — Fix #:** see *Technical Section → Changes Required* table (Items 1–12).

| Excel Row | Fhnatic Case | Analyst | Provider | NPI | Group / Vendor | Cat | Specific Issue | Conflicting Record Id | Fix # | Verifies (AC) |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 663776 | Chhaya Ghadge | George Henry | 1932179090 | (TaxId 222763588) | **A** | Practitioner Account exists; `HealthCareProviderNpi → Account` link is missing/broken → `PRMDRExtractExistingNPIInfo` returns `ExistingAccountId=NULL` → `IsExistingNPI=false` → create path → `PRMDRCreateCaseCaseManagerAndAccount` inserts Account; unique External Id on `HealthCloudGA__SourceSystemId__c` (= NPI 1932179090) trips. | Account `001UW00000eiR46YAE` | #1, #2, #3, #4 | AC-1, AC-5, AC-9 |
| 5 | 673515 | Pratik Kambli | Hyesun Lee | 1053793505 | PM Pediatrics of Livingston (TaxId 454846207) | **C** | Two active HCPT rows already exist in QA for `(AccountId=001UW00000eiED1YAM, TaxonomyId=0bKUW00000000qI2AQ)`; DR Load upsert by composite key returns 2 matches → ambiguous → error. | HCPT siblings `0bPUW00000073lx2AA`, `0bPUW0000007jid2AA` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 6 | 677637 | Pratik Kambli | Melanie Weaver | 1801188388 | Acclaim Autism (TaxId 844050618) | **A** | Practitioner Account exists; note says "provider not in PIE" so no `IndividualApplication` history → `HealthCareProviderNpi` linkage absent → `IsExistingNPI=false` → create-Account path → unique External Id on NPI 1801188388 trips. | Account `001UW00000ejxCcYAI` | #1, #2, #3, #4 | AC-1, AC-5, AC-9 |
| 7 | 695317 | Chhaya Ghadge | Charles E Digby | 1629208095 | St Lukes Internal Medicine (TaxId 232380812) | **C** | Two active HCPT rows for `(AccountId=001UW00000ej33JYAQ, TaxonomyId=0bKUW00000000hC2AQ)`. | HCPT siblings `0bPUW0000006rXt2AI`, `0bPUW0000007jzT2AQ` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 8 | 695435 | Akshata Narale | Bryan Romero | 1487244414 | Central Jersey Urgent Care LLC (TaxId 460793976) | **C** | Two active HCPT rows for `(AccountId=001UW00000vCYhvYAG, TaxonomyId=0bKUW00000000qI2AQ)`. **Same (Account, Taxonomy) pair as rows 12, 14** — single underlying duplicate. | HCPT siblings `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 9 | 697360 | Akshata Narale | Amir Hedayati | 1770534869 | Contemporary Diagnostic Imaging LLC (TaxId 455241476) | **C** | Two active HCPT rows for `(AccountId=001UW00000i9PM1YAM, TaxonomyId=0bKUW00000000jg2AA)`. **Same (Account, Taxonomy) pair as rows 11, 17** — single underlying duplicate, 3 retry attempts. | HCPT siblings `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 10 | 698724 | Chhaya Ghadge | Ovsev Uzuner | 1437203346 | Rittenhouse Imaging Center LLC (TaxId 233067073) | **B** | HealthcareProvider exists; `PRMDRPPersonAccHCProviderNPITaxonomy` inserts a new row → `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` auto-computes `SourceSystemIdentifier = '233067073-Rittenhouse Imaging Center LLC'` which matches existing record's value → unique constraint trips. | HealthcareProvider `0bSUW000000Buy92AC` | #1, #5, #6 | AC-2, AC-5, AC-9 |
| 11 | 699856 | Khan Suleman | Amir Hedayati | 1770534869 | Temple Faculty Radiology Associates (TaxId 831002191) | **C** | Same root duplicate as row 9 — `(AccountId=001UW00000i9PM1YAM, TaxonomyId=0bKUW00000000jg2AA)`. Different group but same practitioner Account; the duplicate junction blocks the unrelated new group submission. | HCPT siblings `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 12 | 701509 | Chhaya Ghadge | Bryan Romero | 1487244414 | Central Jersey Urgent Care LLC (TaxId 460793976) | **C** | Same as row 8 (re-submission attempt) — `(AccountId=001UW00000vCYhvYAG, TaxonomyId=0bKUW00000000qI2AQ)`. | HCPT siblings `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 13 | 701737 | Akshata Narale | Erin McNeilly | 1174744783 | Central Jersey Urgent Care LLC (TaxId 460793976) | **C** | Two active HCPT rows for `(AccountId=001UW00000eivAwYAI, TaxonomyId=0bKUW00000000qI2AQ)`. | HCPT siblings `0bPUW0000003rJp2AI`, `0bPUW0000008cJR2AY` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 14 | 703594 | Chhaya Ghadge | Bryan Romero | 1487244414 | Central Jersey Urgent Care LLC (TaxId 460793976) | **C** | Same as rows 8, 12 (third re-submission attempt) — `(AccountId=001UW00000vCYhvYAG, TaxonomyId=0bKUW00000000qI2AQ)`. | HCPT siblings `0bPUW0000009a972AA`, `0bPUW0000009pzL2AQ` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 16 | 708088 | Pratik Kambli | Sandi McKay | 1972200632 | AtlantiCare Physician Group (TaxId 20701782) | **B** | HealthcareProvider exists for this practitioner+group; trigger-computed `SourceSystemIdentifier = '020701782-AtlantiCare Physician Group'` collides. Note also: TaxId 20701782 is 8 digits — the trigger does `.substring(0,9)` and may also be vulnerable to a leading-zero formatting mismatch (see clarification Q5). | HealthcareProvider `0bSUW000000FTJS2A4` | #1, #5, #6 | AC-2, AC-5, AC-9 |
| 17 | 711166 | Khan Suleman | Amir Hedayati | 1770534869 | Valley Physician Services (TaxId 465285330) | **C** | Same root duplicate as rows 9, 11 — `(AccountId=001UW00000i9PM1YAM, TaxonomyId=0bKUW00000000jg2AA)`. Third group submission for same practitioner, same blocking duplicate. | HCPT siblings `0bPUW0000004t7Z2AQ`, `0bPUW0000005Nwi2AE` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 19 | 712069 | Chhaya Ghadge | Hyesun Lee | 1053793505 | PM Pediatrics of Livingston (TaxId 454846207) | **C** | Same as row 5 (re-submission attempt) — `(AccountId=001UW00000eiED1YAM, TaxonomyId=0bKUW00000000qI2AQ)`. | HCPT siblings `0bPUW00000073lx2AA`, `0bPUW0000007jid2AA` | #7, #8, #9, #10 | AC-3, AC-4, AC-7 |
| 20 | 674985 | Nicole | Igor Povshitkov | 1700924669 | Advanced Ambulatory Anesthesia LLC (TaxId 223683554) | **B** | HealthcareProvider exists; trigger-computed `SourceSystemIdentifier = '223683554-Advanced Ambulatory Anesthesia LLC'` collides. | HealthcareProvider `0bSUW000000GoaM2AS` | #1, #5, #6 | AC-2, AC-5, AC-9 |
| 21 | (n/a) | (n/a) | (no provider info captured) | — | — | **D** | OmniScript SetErrors element rendered the generic catch-all `"Please contact your administration"` instead of surfacing the underlying DML error. Cannot diagnose without re-running with verbose logging; root cause is one of A/B/C. | (unknown — masked by catch-all) | #12 | AC-6 |

### Unique Underlying Defects (de-duplicated view)

The 16 failure rows reduce to **9 unique underlying defects** once retries on the same `(Provider, Group, Account, Taxonomy)` tuple are collapsed:

| Defect | Rows | Category | Single Remediation |
|---|---|---|---|
| D1 | 3 | A | George Henry Account `001UW00000eiR46YAE` reuse |
| D2 | 6 | A | Melanie Weaver Account `001UW00000ejxCcYAI` reuse |
| D3 | 10 | B | Ovsev Uzuner HealthcareProvider `0bSUW000000Buy92AC` reuse |
| D4 | 16 | B | Sandi McKay HealthcareProvider `0bSUW000000FTJS2A4` reuse |
| D5 | 20 | B | Igor Povshitkov HealthcareProvider `0bSUW000000GoaM2AS` reuse |
| D6 | 5, 19 | C | HCPT duplicate `(001UW00000eiED1YAM, 0bKUW00000000qI2AQ)` — Hyesun Lee × 2 attempts |
| D7 | 7 | C | HCPT duplicate `(001UW00000ej33JYAQ, 0bKUW00000000hC2AQ)` — Charles E Digby |
| D8 | 8, 12, 14 | C | HCPT duplicate `(001UW00000vCYhvYAG, 0bKUW00000000qI2AQ)` — Bryan Romero × 3 attempts |
| D9 | 9, 11, 17 | C | HCPT duplicate `(001UW00000i9PM1YAM, 0bKUW00000000jg2AA)` — Amir Hedayati × 3 attempts |
| D10 | 13 | C | HCPT duplicate `(001UW00000eivAwYAI, 0bKUW00000000qI2AQ)` — Erin McNeilly |

**5 distinct duplicate HCPT pairs** drive 10 of the 16 failures — `scripts/apex/cleanup_duplicate_hcpt.apex` (Technical Section Change #10) targets exactly these 5 pairs.

---

# USER STORY 1: PAR Form — Detect & Reuse Existing Practitioner / Vendor Records Before Inserting Account, HealthcareProvider, and HealthcareProviderTaxonomy

**Persona:** Sr. Data Reporting Analyst, Rep, Developer
**Priority:** P0
**OmniScript:** `PRM_PractitionerParticipationForm_English` v111 (active in QA)
**Integration Procedures:** `PRM_FetchExistingNPIInfo` v8, `PRM_CreateParFormRecords` v29, `PRM_PractitionerScreenRecordCreation`, `PRM_PractitionerScreenExistingNPIRecordUpdation`, `PRM_PractitionerAddressCreation` v5, `PRM_CreatePractitionerAddressRecords` v41
**DataRaptors:** `PRMDRExtractExistingNPIInfo`, `PRMDRCreateCaseCaseManagerAndAccount`, `PRMDRPPersonAccHCProviderNPITaxonomy`, `PRMDRPPersonAccHCProviderNPITaxonomyExAcc`, `PRMDRCreateTaxonomy`, `PRMDREIdentiferAccountTaxonomy`, `PRMDRPHealthCareNPIHealthCareTaxonomyUpdate`
**Apex:** `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier`, `PRM_AccountTriggerHelper.setAccIdentifier`, `PRM_HCProviderTrigger`
**Relevant Requirements:** Failure Inventory above (19 rows from `Copy of Duplicate account and tax id errors.xlsx`, May 2026)

---

## Story

**As a** Sr. Data Reporting Analyst (or PAR Rep) submitting a Practitioner Participation request,
**I want** the form to correctly detect and reuse any existing Practitioner Account, Vendor (Group) Account, HealthcareProvider record, or HealthcareProviderTaxonomy junction — regardless of whether the practitioner's `HealthCareProviderNpi` link is missing or stale, and regardless of whether duplicate junction rows are already present in the database,
**So that** I can submit re-participation, change-group, and add-location requests for existing providers without hitting a duplicate-value or "duplicated results found" DML error and without escalating to a Salesforce admin to manually delete records.

**Why it matters:** Out of a single day's PAR submissions, **19 requests across 14 distinct providers** failed with one of three duplicate-record errors. Every failure currently requires (a) a developer to read the trace, (b) an admin to delete or merge the colliding record, and (c) the analyst to re-enter the entire 7-step form. The economic and SLA cost is significant: an estimated **45–60 minutes of manual remediation per failure**, plus a 1–2 day delay in the credentialing case.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationForm_English` v111 | `PractitionerForm` (Step 1) — `FetchExistingNPIInfo` LWC remote action | `PRM_FetchExistingNPIInfo` IP → `PRMDRExtractExistingNPIInfo` DR |
| PAR | `PRM_PractitionerParticipationForm_English` v111 | Final Submit — `CreateParFormRecords` action | `PRM_CreateParFormRecordsContainer` → `PRM_CreateParFormRecords` v29 → `PRM_PractitionerScreenRecordCreation` (create path) **or** `PRM_PractitionerScreenExistingNPIRecordUpdation` (update path) |
| Cross-cutting | N/A | HealthcareProvider before-insert trigger | `PRM_HCProviderTrigger` → `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` |

---

## Current State (from codebase)

### `PRMDRExtractExistingNPIInfo` — Existing-Record Detection (the root miss)

**Location:** `force-app/main/default/omniDataTransforms/PRMDRExtractExistingNPIInfo_1.rpt-meta.xml`

The DR has three query sources used to populate `PractitionerForm:ExistingAccountId`:

1. Primary: `HealthCareProviderNpi` query by `NPI` input value.
2. Linked: `Account WHERE Id = HealthCareProviderNpi:AccountId` (line 64–79, `inputObjectQuerySequence=2.0`).
3. Linked: `Identifier WHERE ... = HealthCareProviderNpi:Id` and similar.

`PractitionerForm:ExistingAccountId` is set **only when an active `HealthCareProviderNpi` row is found and its `AccountId` is non-null**. There is **no fallback query** that searches `Account` directly by `HealthCloudGA__SourceSystemId__c = NPI` or by `(SourceSystemIdentifier = TaxId + '-' + Name)`.

### `PRM_FetchExistingNPIInfo` v8 — IsExistingNPI Flag

**Location:** `force-app/main/default/omniIntegrationProcedures/PRM_FetchExistingNPIInfo_Procedure_8.oip-meta.xml` (line 403)

```
PractitionerForm:IsExistingNPI =
  IF(%IsCredentialedPNCDelegated%, NULL,
     IF(%PractitionerForm:ExistingAccountId% != NULL, true, false))
```

Because `ExistingAccountId` is null whenever the `HealthCareProviderNpi → Account` join fails, `IsExistingNPI` is set to **`false`** and the form is routed down the create-new-Account path.

### `PRM_CreateParFormRecords` v29 — Routing Switch

**Location:** `force-app/main/default/omniIntegrationProcedures/PRM_CreateParFormRecords_Procedure_29.oip-meta.xml` (lines 227–270)

```
IF %PractitionerForm:IsExistingNPI% == false → PRM_PractitionerScreenRecordCreation (CREATE)
IF %PractitionerForm:IsExistingNPI% == true  → PRM_PractitionerScreenExistingNPIRecordUpdation (UPDATE)
```

Routing is binary on this single flag. There is no secondary safety check against `Account.HealthCloudGA__SourceSystemId__c` or `Account.SourceSystemIdentifier` before the create DR runs.

### `PRMDRCreateCaseCaseManagerAndAccount` — Pure Insert (no upsert key)

**Location:** `force-app/main/default/omniDataTransforms/PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` (lines 202–217)

```xml
<inputFieldName>Npi</inputFieldName>
<outputCreationSequence>1.0</outputCreationSequence>
<outputFieldName>HealthCloudGA__SourceSystemId__c</outputFieldName>
<outputObjectName>Account</outputObjectName>
<requiredForUpsert>false</requiredForUpsert>
<upsertKey>false</upsertKey>
```

Every Account field is `upsertKey=false`. The DR therefore always **inserts**. When an Account already exists with `HealthCloudGA__SourceSystemId__c = Npi` (and the create path was wrongly chosen), the platform unique constraint fires Error Category A.

### `PRMDRPPersonAccHCProviderNPITaxonomy` — Inserts HealthcareProvider

**Location:** `force-app/main/default/omniDataTransforms/PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml`

- Writes to `HealthcareProvider` (lines 139, 187, etc.) — **all fields `upsertKey=false`** → insert only.
- Upserts on `HealthcareProviderNpi` use composite key `(Name, Npi)`.
- A parallel DR `PRMDRPPersonAccHCProviderNPITaxonomyExAcc` (Existing Account variant) **omits HealthcareProvider entirely** — confirming the design intent that HealthcareProvider only be created when the practitioner is truly new. But the routing flag (`IsExistingNPI`) is false-negative in the broken-NPI-link cases, so the wrong DR runs.

### `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier`

**Location:** `force-app/main/default/classes/PRM_HCProviderTriggerHandler.cls` (lines 35–75)

```apex
hp.SourceSystemIdentifier = identifier.IdValue + '-' + acc.Name;
```

Computed in before-insert from the related Account's EIN Tax-Id identifier and the Account Name. The field is unique at the schema level. Two practitioners affiliating with the same group share the same Tax-Id and Account-Name, so their auto-computed `SourceSystemIdentifier` values collide when the practitioner Account is recreated rather than reused (Error Category B).

### `PRMDRCreateTaxonomy` — HealthcareProviderTaxonomy Junction Create/Update

**Location:** `force-app/main/default/omniDataTransforms/PRMDRCreateTaxonomy_1.rpt-meta.xml`

- Output object `HealthcareProviderTaxonomy`.
- `Id` field is mapped from `TaxonomyData:ExistingId` (the IP's upstream attempt to set the record Id if known).
- All fields `upsertKey=false`. The DR is essentially "if `Id` populated → update; else → insert."
- The IP relies on `TaxonomyData:ExistingId` being correctly populated by an upstream extract. **No de-duplication logic exists** if multiple existing HCPTs match the same `(AccountId, TaxonomyId)`.

### `PRMDRPIdentifierAccountTaxonomy` — Load DR with Mis-Mapped Upsert Key

**Location:** `force-app/main/default/omniDataTransforms/PRMDRPIdentifierAccountTaxonomy_1.rpt-meta.xml` (lines 150–166)

```xml
<inputFieldName>Taxonomy:Id</inputFieldName>
<outputFieldName>Id</outputFieldName>
<outputObjectName>HealthcareProviderTaxonomy</outputObjectName>
<requiredForUpsert>true</requiredForUpsert>
<upsertKey>true</upsertKey>
```

The taxonomy code Id (key prefix `0bK...`) is mapped into HealthcareProviderTaxonomy's own `Id` field (key prefix `0bP...`) and used as the upsert key. This will never match an existing junction record. Combined with pre-existing duplicate rows, this is the proximate trigger of Error Category C.

### Pre-existing HCPT Duplicates in QA

The 10 Category C failures involve only **5 unique `(Account, Taxonomy)` pairs**. For each, two HealthcareProviderTaxonomy junction rows already exist in QA. There is **no validation rule, schema uniqueness constraint, or trigger** on `HealthcareProviderTaxonomy` that prevents duplicate junctions on `(AccountId, TaxonomyId)`.

---

## Technical Section (For Developers)

### Changes Required

| # | Component | Type | Change |
|---|-----------|------|--------|
| 1 | `PRMDRExtractExistingNPIInfo` | DataRaptor Extract | Add a second top-level `inputObject` query: `Account WHERE HealthCloudGA__SourceSystemId__c = %NPI% AND RecordType.DeveloperName = 'PRM_Practitioner'`. Map `Account:Id` into `PractitionerForm:ExistingAccountId` (fallback path) when the `HealthCareProviderNpi → Account` join returns no row. Also expose `PractitionerForm:ExistingHealthcareProviderId` from the same Account-keyed query so downstream DRs can route to the update path. |
| 2 | `PRM_FetchExistingNPIInfo` v8 → v9 | Integration Procedure | Update the SetValues element (line 403) that computes `PractitionerForm:IsExistingNPI` to also evaluate `PractitionerForm:ExistingHealthcareProviderId` and `PractitionerForm:ExistingHCProviderTaxonomyId` so the routing flag is `true` whenever ANY of `(ExistingAccountId, ExistingHealthcareProviderId, ExistingHCProviderTaxonomyId)` is non-null. |
| 3 | `PRM_CreateParFormRecords` v29 → v30 | Integration Procedure | Insert an "Account safety check" branch immediately before the `IsExistingNPI == false` route fires. Use a new lightweight Extract DR (`PRMDREAccountByNpi`) to look up `Account WHERE HealthCloudGA__SourceSystemId__c = %Npi% LIMIT 1`. If any row is returned, **redirect** to `PRM_PractitionerScreenExistingNPIRecordUpdation` and surface a TextBlock-level note to the analyst ("Existing practitioner record detected — reusing"). |
| 4 | `PRMDRCreateCaseCaseManagerAndAccount` | DataRaptor Load | Convert Account inserts to upserts. Set `<requiredForUpsert>true</requiredForUpsert>` and `<upsertKey>true</upsertKey>` on the `HealthCloudGA__SourceSystemId__c` field item (currently lines 202–217). This makes the DR idempotent — re-runs with the same NPI update instead of throwing. |
| 5 | `PRMDRPPersonAccHCProviderNPITaxonomy` | DataRaptor Load | Convert HealthcareProvider inserts to upserts. Mark `SourceSystemIdentifier` as upsert key (mirroring the pattern in `PRMPostGroupPractitionerCreation_1` lines 410–416). Additionally, before invoking this DR, the calling IP must call the `ExAcc` variant whenever `ExistingAccountId` is non-null (closing the loop opened by change #1). |
| 6 | `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` | Apex | Add idempotency: query existing `HealthcareProvider` by the computed `SourceSystemIdentifier` value and short-circuit (do not assign on insert) if a match exists — instead, throw a clean `AddError` on the trigger record with message `"Existing HealthcareProvider record found; reuse via PAR form update path"`. This converts the platform DUPLICATE_VALUE error into a recoverable validation error the OmniScript can render. |
| 7 | `PRMDRPIdentifierAccountTaxonomy` | DataRaptor Load | Remove the `<upsertKey>true</upsertKey>` from the `Taxonomy:Id → HealthcareProviderTaxonomy.Id` mapping (line 165). The Id field of the junction is auto-generated and cannot match a foreign-key value. Replace with a proper composite upsert on `(AccountId, TaxonomyId)` once duplicate prevention (change #9) is live, OR remove this DR from the create chain entirely if `PRMDRCreateTaxonomy`'s `ExistingId`-driven update pattern is sufficient. |
| 8 | `PRMDRCreateTaxonomy` | DataRaptor Load | Enhance the input transform to **de-duplicate** when multiple HCPTs match the same `(AccountId, TaxonomyId)`. Use a pre-step Extract DR or a formula that picks the row with `IsActive=true`, then `PRM_Pending__c=false`, then most-recent `LastModifiedDate` — and inactivates the others by setting `EffectiveTo=TODAY()`. |
| 9 | `HealthcareProviderTaxonomy` | Schema / Trigger | Add a before-insert/before-update trigger (`PRM_HCProviderTaxonomyTrigger` + `PRM_HCPTriggerHandler`) that prevents creation of a second active row for the same `(AccountId, TaxonomyId)` tuple. If a duplicate is detected, the trigger should `addError` with message `"A HealthcareProviderTaxonomy row already exists for this Account+Taxonomy pair (Id: <existingId>). Re-activate or update the existing row instead."` |
| 10 | Anonymous Apex / Data Cleanup | Script | Provide a one-time `scripts/apex/cleanup_duplicate_hcpt.apex` script that deletes (or sets `EffectiveTo=TODAY()` on) the older/inactive of each pair in the failure inventory (5 distinct duplicate pairs identified). Save run output to `scripts/apex/cleanup_duplicate_hcpt.log`. |
| 11 | `PRM_PractitionerParticipationForm_English` v111 → v113 | OmniScript | Add a hidden DataRaptor Action (`OS_DRCheckExistingPractitioner`) on the `PractitionerForm` step that re-validates `ExistingAccountId` immediately before navigation away from Step 1. If found, show an info banner: *"This practitioner already exists in IBX (Account: ____). The form will update the existing record."* This gives the analyst visibility before the Final Submit. |
| 12 | OmniScript Error Display | OmniScript | Replace the generic catch-all "Please contact your administration" SetErrors element (root cause of Category D) with a switch that renders the actual platform error: SOQL message + (when applicable) the conflicting record Id. The analyst should always know which record collided so they can verify whether it is the same provider. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRExtractExistingNPIInfo` | DR Extract | `NPI` (string) | `PractitionerForm:ExistingAccountId`, `PractitionerForm:ExistingHealthcareProviderId` (NEW), `PractitionerForm:ExistingHCProviderTaxonomyId` (NEW), `PractitionerForm:PractitionerIdentifierId`, `PractitionerForm:ExistingPersonContactId`, `PractitionerForm:ExistingCaseManagerId` | Add fallback Account query (HealthCloudGA__SourceSystemId__c lookup); add HealthcareProvider lookup by `AccountId`; add HealthcareProviderTaxonomy lookup by `AccountId+PrimaryTaxonomyId` |
| `PRMDREAccountByNpi` (NEW) | DR Extract | `Npi` | `Account:Id`, `Account:HealthCloudGA__TaxId__c`, `Account:RecordType.DeveloperName` | New DR; single-row lookup `WHERE HealthCloudGA__SourceSystemId__c = %Npi%` for the IP-level safety check |
| `PRM_FetchExistingNPIInfo` v9 | IP | `NPI`, `TaxId`, `PNCFlag` | Same as v8 + new `ExistingHealthcareProviderId`, `ExistingHCProviderTaxonomyId` | Update `IsExistingNPI` formula; pass through new output fields |
| `PRM_CreateParFormRecords` v30 | IP | Form data | Record creation results | Insert safety branch using `PRMDREAccountByNpi`; redirect to update path when an Account row is found regardless of `IsExistingNPI` |
| `PRMDRCreateCaseCaseManagerAndAccount` | DR Load | Form JSON | Account, IndividualApplication, Case | Change `HealthCloudGA__SourceSystemId__c` field to `upsertKey=true, requiredForUpsert=true` |
| `PRMDRPPersonAccHCProviderNPITaxonomy` | DR Load | Form JSON | HealthcareProvider, HealthcareProviderNpi, HealthcareProviderTaxonomy | Mark `SourceSystemIdentifier` on HealthcareProvider as `upsertKey=true` |
| `PRMDRCreateTaxonomy` | DR Load | `TaxonomyData[]` | HealthcareProviderTaxonomy | Add pre-step de-dup logic; do NOT insert when an active HCPT already exists for the (AccountId, TaxonomyId) |
| `PRMDRPIdentifierAccountTaxonomy` | DR Load | Form JSON | Account, Identifier, HealthcareProviderTaxonomy | Remove the broken `Taxonomy:Id → HCPT.Id` upsertKey mapping |
| `PRM_HCProviderTaxonomyTrigger` (NEW) | Apex Trigger | HCPT before-insert/update | n/a | Block duplicate active rows on (AccountId, TaxonomyId) |

### Example: Fixed Account Upsert Mapping in `PRMDRCreateCaseCaseManagerAndAccount`

```xml
<omniDataTransformItem>
    <disabled>false</disabled>
    <inputFieldName>Npi</inputFieldName>
    <outputCreationSequence>1.0</outputCreationSequence>
    <outputFieldName>HealthCloudGA__SourceSystemId__c</outputFieldName>
    <outputObjectName>Account</outputObjectName>
    <requiredForUpsert>true</requiredForUpsert>
    <upsertKey>true</upsertKey>
</omniDataTransformItem>
```

### Example: New `PRMDREAccountByNpi` (skeleton)

```xml
<OmniDataTransform>
    <name>PRMDREAccountByNpi</name>
    <inputType>JSON</inputType>
    <outputType>JSON</outputType>
    <type>Extract</type>
    <omniDataTransformItem>
        <inputFieldName>Id</inputFieldName>
        <inputObjectName>Account</inputObjectName>
        <inputObjectQuerySequence>0.0</inputObjectQuerySequence>
        <filterGroup>0.0</filterGroup>
        <filterOperator>=</filterOperator>
        <filterValue>%Npi%</filterValue>
        <!-- second filter row -->
        <filterField>HealthCloudGA__SourceSystemId__c</filterField>
        <outputFieldName>Account:Id</outputFieldName>
        <outputObjectName>json</outputObjectName>
    </omniDataTransformItem>
</OmniDataTransform>
```

### Example: Trigger Skeleton (`PRM_HCProviderTaxonomyTrigger`)

```apex
trigger PRM_HCProviderTaxonomyTrigger on HealthcareProviderTaxonomy (before insert, before update) {
    PRM_HCPTriggerHandler.preventDuplicateActiveJunctions(Trigger.new, Trigger.oldMap);
}
```

```apex
public without sharing class PRM_HCPTriggerHandler {
    public static void preventDuplicateActiveJunctions(
        List<HealthcareProviderTaxonomy> newList,
        Map<Id, HealthcareProviderTaxonomy> oldMap
    ) {
        Set<String> keys = new Set<String>();
        for (HealthcareProviderTaxonomy r : newList) {
            if (r.AccountId != null && r.TaxonomyId != null && r.IsActive) {
                keys.add(r.AccountId + '|' + r.TaxonomyId);
            }
        }
        if (keys.isEmpty()) return;

        Map<String, HealthcareProviderTaxonomy> existing = new Map<String, HealthcareProviderTaxonomy>();
        for (HealthcareProviderTaxonomy e : [
            SELECT Id, AccountId, TaxonomyId, IsActive
            FROM HealthcareProviderTaxonomy
            WHERE IsActive = true
              AND AccountId != null
              AND TaxonomyId != null
        ]) {
            existing.put(e.AccountId + '|' + e.TaxonomyId, e);
        }

        for (HealthcareProviderTaxonomy r : newList) {
            if (r.AccountId == null || r.TaxonomyId == null || !r.IsActive) continue;
            String key = r.AccountId + '|' + r.TaxonomyId;
            HealthcareProviderTaxonomy match = existing.get(key);
            if (match != null && (oldMap == null || match.Id != r.Id)) {
                r.addError('A HealthcareProviderTaxonomy row already exists for this Account+Taxonomy pair (Id: '
                    + match.Id + '). Re-activate or update the existing row instead.');
            }
        }
    }
}
```

---

## Acceptance Criteria

### AC-1 — Existing Account detected via NPI external Id (covers rows 3, 6)

**Given** a practitioner whose Account exists in IBX (`Account.HealthCloudGA__SourceSystemId__c = NPI`) but whose `HealthCareProviderNpi` linkage is missing or has a stale `AccountId`,
**When** the analyst enters this NPI on the PAR form's PractitionerForm step,
**Then** `PRMDRExtractExistingNPIInfo` returns `PractitionerForm:ExistingAccountId = <existing Account Id>` via the fallback Account query,
**AND** `PRM_FetchExistingNPIInfo` sets `IsExistingNPI = true`,
**AND** the form prefills practitioner fields read-only,
**AND** Final Submit routes through `PRM_PractitionerScreenExistingNPIRecordUpdation` — no duplicate-value error on Account.

### AC-2 — Existing HealthcareProvider detected via SourceSystemIdentifier (covers rows 10, 16, 20)

**Given** a practitioner with an existing `HealthcareProvider` record (`SourceSystemIdentifier = TaxId-AccountName`),
**When** the analyst submits a new PAR request for the same provider + group,
**Then** the form does not attempt to insert a duplicate `HealthcareProvider`,
**AND** `PRMDRPPersonAccHCProviderNPITaxonomyExAcc` (existing-account variant) is invoked instead of `PRMDRPPersonAccHCProviderNPITaxonomy`,
**AND** no `duplicate value found: SourceSystemIdentifier` error is thrown,
**AND** the existing HealthcareProvider record is updated with the new effective dates and case manager.

### AC-3 — HCPT Upsert handles pre-existing duplicate junctions (covers rows 5, 7, 8, 9, 11, 12, 13, 14, 17, 19)

**Given** two (or more) `HealthcareProviderTaxonomy` rows already exist in the org for the same `(AccountId, TaxonomyId)` pair,
**When** the PAR form submits and the create/update flow reaches `PRMDRCreateTaxonomy`,
**Then** the DR's pre-step de-dup logic identifies the active row (or the most-recently-modified if none is active),
**AND** updates the chosen active row's effective dates,
**AND** sets `EffectiveTo = TODAY()` on the duplicate sibling(s),
**AND** no "Duplicated results found for HealthcareProviderTaxonomy" error is surfaced.

### AC-4 — New HCPT duplicate prevention

**Given** an existing active `HealthcareProviderTaxonomy` for `(Account A, Taxonomy T)`,
**When** any DR or Apex attempts to insert a SECOND active row for the same `(A, T)`,
**Then** `PRM_HCProviderTaxonomyTrigger` blocks the insert,
**AND** the error message is `"A HealthcareProviderTaxonomy row already exists for this Account+Taxonomy pair (Id: <existingId>). Re-activate or update the existing row instead."`,
**AND** the existing row's Id is included in the error so the calling IP can chain into the update path.

### AC-5 — Idempotent Account / HealthcareProvider DRs

**Given** the user clicks Final Submit on the PAR form twice (e.g., due to network retry),
**When** `PRMDRCreateCaseCaseManagerAndAccount` and `PRMDRPPersonAccHCProviderNPITaxonomy` both re-execute,
**Then** the second execution upserts (matches on `HealthCloudGA__SourceSystemId__c` and `SourceSystemIdentifier` respectively) instead of inserting,
**AND** no duplicate-value error occurs,
**AND** the same case manager + case + IA + account records are returned.

### AC-6 — Generic error replaced with actionable message (covers row 21)

**Given** any DML failure occurs in the create or update chain,
**When** the OmniScript renders the resulting error,
**Then** the error message includes the actual platform message AND the conflicting record Id (if available) AND a remediation hint ("Reuse this record via the Existing Practitioner search"), rather than the generic "Please contact your administration".

### AC-7 — Data cleanup verified

**Given** the 5 distinct duplicate `(Account, Taxonomy)` pairs in the failure inventory (Category C),
**When** `scripts/apex/cleanup_duplicate_hcpt.apex` is executed in QA,
**Then** for each pair, exactly one row remains `IsActive = true`,
**AND** the inactivated rows have `EffectiveTo = TODAY()` and `PRM_Pending__c = false`,
**AND** re-submission of the 10 originally-failing PAR cases (rows 5, 7, 8, 9, 11, 12, 13, 14, 17, 19) succeeds end-to-end.

### AC-8 — Banner shown when existing practitioner detected (UX)

**Given** the analyst enters an NPI that matches an existing Account (via either path),
**When** the form navigates from Step 1 to Step 2,
**Then** a non-blocking info banner is shown: *"Existing practitioner detected — fields prefilled; the existing record will be updated."*
**AND** the banner includes the existing Account Name and Id,
**AND** an analyst can click "Cancel" to abort the submission if the match is incorrect.

### AC-9 — No regression on the "truly new" path

**Given** an NPI that has no Account, no HealthcareProvider, and no HealthcareProviderTaxonomy in the org,
**When** the analyst submits a new PAR request,
**Then** all create-new records are inserted exactly as before (Account, HealthcareProvider, HealthcareProviderTaxonomy, HealthcareProviderNpi, IndividualApplication, Case, Location, Address, etc.),
**AND** no functional regression in record counts or field values compared to v111 baseline.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | For Category C, do we have business approval to **automatically inactivate** the duplicate HCPT sibling, or must the analyst be prompted to choose which to keep? | Determines if AC-3 auto-resolves or escalates to a manual UX prompt | BA / Ops |
| 2 | When `ExistingAccountId` is detected via the NEW fallback path, but the existing Account has a different Tax Id from the one entered on the form, should the form (a) block with a Tax-Id mismatch error, (b) update the Account's Tax Id, or (c) prompt the analyst? | Determines the safety behavior in row-6-style "provider not in PIE" cases | BA |
| 3 | Should the `PRM_HCProviderTaxonomyTrigger` block ALL duplicate active junctions, or only those created via OmniStudio (so legacy data-loader bulk inserts can still bypass)? | Determines trigger context-check (e.g., `System.isBatch()`, `Trigger.context`) | Technical / Architecture |
| 4 | Is `HealthCloudGA__SourceSystemId__c` an External Id field with the `unique` flag at the schema level today, or is the uniqueness enforced only by trigger? | Confirms whether the AC-5 upsert pattern will work natively or needs a custom matcher | Technical |
| 5 | The current `populateSourceSystemIdentifier` Apex includes a substring of `acc.Name`. For practitioner Accounts whose name contains special characters or differs by a single space across re-applications, the generated SourceSystemIdentifier can differ from the existing record's. Should we **normalize** the name (trim, lowercase, remove punctuation) before computing the identifier? | Determines whether some Category B failures are spurious-mismatches that the trigger fix needs to absorb | Technical / BA |
| 6 | Are there any in-flight PAR submissions currently using v112 of the OmniScript (dev draft) that would be affected if we cut a v113 from v111? | Determines the release/activation order in QA | Technical / Product |
| 7 | For the `PRMDREAccountByNpi` fallback, do we limit the lookup to `Account.IsActive = true` or include inactive Accounts? Some of the 19 failed cases note "Non-par" status which may be modeled as `IsActive=false`. | Determines whether inactive-Account reuse is permitted or requires reactivation step | BA |
| 8 | If Tax-Id changes between the previous and current submission (e.g., provider moved groups), should the form (a) reuse the existing practitioner Account but link to a NEW Vendor Account, or (b) treat this as a fully new submission? | Edge case for vendor switch scenario | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMDRExtractExistingNPIInfo` | DataRaptor Extract | HIGH | Core detection gap; adds fallback query path |
| `PRM_FetchExistingNPIInfo` v8→v9 | Integration Procedure | HIGH | Updates routing flag formula |
| `PRM_CreateParFormRecords` v29→v30 | Integration Procedure | HIGH | Adds safety branch; changes record-creation routing |
| `PRMDRCreateCaseCaseManagerAndAccount` | DataRaptor Load | HIGH | Change from insert to upsert on Account |
| `PRMDRPPersonAccHCProviderNPITaxonomy` | DataRaptor Load | HIGH | Change from insert to upsert on HealthcareProvider |
| `PRMDRCreateTaxonomy` | DataRaptor Load | HIGH | Add de-dup logic for HCPT |
| `PRMDRPIdentifierAccountTaxonomy` | DataRaptor Load | MEDIUM | Remove broken upsertKey mapping |
| `PRMDREAccountByNpi` (NEW) | DataRaptor Extract | MEDIUM | New lightweight extract DR for safety check |
| `PRM_HCProviderTaxonomyTrigger` (NEW) + `PRM_HCPTriggerHandler` (NEW) | Apex Trigger + Handler | HIGH | New duplicate prevention; needs test class with 75%+ coverage |
| `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` | Apex | MEDIUM | Add idempotency check |
| `PRM_PractitionerParticipationForm_English` v111→v113 | OmniScript | MEDIUM | Add hidden DR Action + info banner + error display |
| `scripts/apex/cleanup_duplicate_hcpt.apex` (NEW) | Anonymous Apex | LOW | One-time data cleanup for the 5 duplicate pairs |
| HealthcareProviderTaxonomy data (QA & Prod) | Data | MEDIUM | One-time cleanup of duplicates; ongoing monitoring needed |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRMDRExtractExistingNPIInfo` — fallback Account query | DR mapping additions | M | Add second `inputObject` query block + 2 new output mappings |
| `PRMDREAccountByNpi` (NEW) | New DR Extract | M | Simple single-table extract |
| `PRM_FetchExistingNPIInfo` v9 | IP formula change | S | Single SetValues element edit |
| `PRM_CreateParFormRecords` v30 | IP conditional branch | L | New If/Else block + new IP-action step + regression testing of all 4 routing paths |
| `PRMDRCreateCaseCaseManagerAndAccount` upsertKey | DR config | S | Two XML attribute flips |
| `PRMDRPPersonAccHCProviderNPITaxonomy` upsertKey | DR config | S | Two XML attribute flips |
| `PRMDRCreateTaxonomy` de-dup | DR transform logic | L | New formula items + sort/pick logic for active row |
| `PRMDRPIdentifierAccountTaxonomy` upsertKey removal | DR config | S | Single XML attribute flip |
| `PRM_HCProviderTaxonomyTrigger` + handler + test | New Apex | L | ~50 lines of Apex + 75%+ coverage test class |
| `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` idempotency | Apex enhancement | M | Add SOQL lookup + addError; update existing test class |
| OmniScript v113 — banner + DR action | OmniScript element additions | M | New DR action element + new TextBlock with show condition |
| OmniScript v113 — generic error replacement | OmniScript SetErrors update | M | Replace static text with token-based error message |
| `scripts/apex/cleanup_duplicate_hcpt.apex` | Data fix script | S | ~30 lines, deletes/inactivates 5 known duplicates |
| Regression testing (full AC matrix × 19 failing rows + clean baseline) | QA | XL | 19 rerun cases + 9 ACs × 2 environments (QA, UAT); ~2 days |

**Total Estimated Effort:** AI-estimated — validate with team — **XL** (~5–7 dev days + 2 QA days). Effort dominated by IP routing redesign (#3), DR de-dup logic (#8), and full regression matrix.

---

## Rollout Plan

1. **Phase 1 — Apex & Trigger Prevention (lowest risk):** Deploy #6 (`populateSourceSystemIdentifier` idempotency) + #9 (`PRM_HCProviderTaxonomyTrigger`). Run #10 cleanup script in QA. Smoke-test the 19 failure cases.
2. **Phase 2 — DR Upsert Conversion:** Deploy #4, #5, #7. Re-run the 19 failure cases in QA.
3. **Phase 3 — IP & DR Detection Logic:** Deploy #1, #2, #3, new `PRMDREAccountByNpi`, #8. Re-run full AC matrix.
4. **Phase 4 — OmniScript v113:** Deploy #11, #12. Final UAT.
5. **Phase 5 — Prod:** Run #10 in Prod (after Prod-data audit), then deploy Phase 1–4 metadata.

---

## QTA Test Bridge

Each AC above can be converted into a QTA browser automation prompt. Suggested first 3:

1. **AC-1 QTA prompt:** *"Open PRM_PractitionerParticipationForm_English in QA. In the PractitionerForm step, enter NPI `1932179090` (George Henry — Case 663776 from failure inventory). Verify the form auto-prefills the practitioner fields read-only and that an info banner reads 'Existing practitioner detected.' Navigate to Step 2; complete the flow; click Final Submit. Verify no error toast appears and that the IndividualApplication record is created with `AccountId = 001UW00000eiR46YAE`."*

2. **AC-3 QTA prompt:** *"Open PRM_PractitionerParticipationForm_English in QA. Enter NPI `1053793505` (Hyesun Lee — Case 673515). Select Vendor 'PM Pediatrics of Livingston' (NPI 1639430515, TaxId 454846207). Complete the flow; click Final Submit. Verify no 'Duplicated results found' error. Query HealthcareProviderTaxonomy in QA: confirm only one active row remains for AccountId=001UW00000eiED1YAM AND TaxonomyId=0bKUW00000000qI2AQ; sibling rows must have EffectiveTo set."*

3. **AC-4 QTA prompt:** *"In QA Developer Console, run Anonymous Apex that inserts a HealthcareProviderTaxonomy with `AccountId=001UW00000eiED1YAM, TaxonomyId=0bKUW00000000qI2AQ, IsActive=true, EffectiveFrom=TODAY()`. Verify the insert is rejected with error containing 'A HealthcareProviderTaxonomy row already exists for this Account+Taxonomy pair (Id: 0bP...)' and the existing record Id."*
