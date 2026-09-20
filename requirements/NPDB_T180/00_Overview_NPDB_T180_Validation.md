# NPDB Data Validation — T-180 Batch + Manual Paths

**Date:** 2026-06-01
**Owner:** Credentialing / PRM Engineering
**Replaces:** prior T-240 pre-flight design (removed per business decision — pre-flight is NOT needed)

---

## 1. Problem statement

NPDB report requests are silently failing because the source data on the practitioner (address, NPI, license, demographics, etc.) is missing or malformed at the moment the request is built. Today two paths fire NPDB requests:

1. **Automated path — T-180 recredentialing kickoff:** `PRM_CheckCAQHAccessOnDueAccountsBatch` runs nightly, identifies Accounts whose `PRM_ReCredDueDate__c` is `T-180` days out, calls `PRM_CheckCAQHExecuteHelper.processAccount` → `createActiveCAQHRecords` → which inserts an `IndividualApplication` (Case Manager) in `Status = 'Pending NPDB'`, the matching `Case`, and a child `PRM_AdverseActionLog__c` (AAL) in `Status = 'Ready To Process'`. The downstream NPDB outbound integration polls AALs in `Ready To Process` and fires the request.
2. **Manual path — `Request NPDB` button on the Case Manager record:** Credentialing users click `CustomButton.IndividualApplication.PRM_NPDB` which launches the `PRM_CallNPDB_English` OmniScript. The OmniScript inserts/edits AALs through `PRM_CreateAdverseActionNpdbBatch` and/or the `PRM_IPCreateAdverseActionLogParent` IP.

Both paths today insert an AAL **regardless of whether the source data is complete.** The only existing guard is a null check on the practitioner's primary `Schema.Address` inside `PRM_CheckCAQHRecordInitHelper.initializeAdvActionLogRecord` (lines 86–99), and when that null check trips the AAL is silently skipped but the Case Manager is still created in `Pending NPDB` — leaving the case stuck and invisible.

Business users today only discover these failures **after** the NPDB outbound service returns an `Error` and the AAL flips to `PRM_Status__c = 'Error'`. By that point the practitioner is already inside the recredentialing window and SLA pressure starts.

> **Business decision (2026-06-01):** A separate T-240 pre-flight batch is NOT wanted. Validation must happen inside the existing T-180 batch and the manual paths.

---

## 2. Solution at a glance

Three coordinated changes, all firing at the moment an NPDB request would be created:

| # | Change | Where | Outcome |
|---|--------|-------|---------|
| **A** | T-180 batch validates NPDB-required fields **before** inserting the AAL. If any field is missing, the Case Manager + Case are created in **`NPDB Action Needed`** (new status) instead of `Pending NPDB`, and **no AAL is inserted**. | `PRM_CheckCAQHExecuteHelper.processAccount` / new `PRM_NpdbDataValidator` | Catches failures before the integration ever sees them. Surfaces every missing-data case on day one of the recred window (T-180) instead of T-150 / T-120 when the error comes back. |
| **B** | Manual `Request NPDB` button + every embedded NPDB step in OmniScripts validates the same required fields before submission. Validation runs in the **Integration Procedure layer** (where the practitioner data is already loaded) and renders a **detailed, link-free text message** listing exactly which fields are missing on which record (Account, Address, NPI, License, Education, Facility) with a plain-English fix instruction for each — shown natively via OmniScript Message / Validation elements. A matching server-side Apex gate covers programmatic inserts. | New `PRM_NpdbDataValidator` Apex (returns `detailText`) + modified `PRM_IPCreateAdverseActionLog` / `PRM_GetAncNpdbDetails` IPs + OmniScript Message / Validation elements (no deep-link banner LWC) | User sees the actual blocker, in plain English, the first time they try to request — instead of submitting and waiting 24 hours to find out it failed. |
| **C** | New Salesforce Report (+ optional dashboard component) listing all Case Managers currently in `NPDB Action Needed`, grouped by the practitioner's `PRM_ReCredDueDate__c` so leadership can see "how many recreds are blocked, how many days of runway each one has". | Reports folder | Single source of truth for the queue; replaces ad-hoc SOQL the Ops team runs today. |

---

## 3. Why this works (and why no pre-flight is OK)

| Concern from the original pre-flight design | How T-180 validation answers it |
|---------------------------------------------|---------------------------------|
| "We want to see failures earlier than T-180" | Business confirmed T-180 IS early enough — the recred *due date* is T-0; T-180 is six months of runway. The pre-flight (T-240) would only add ~60 days to that window and adds a whole new batch + finding object + dashboard to maintain. |
| "We need a queue of 'records that will fail NPDB'" | The `NPDB Action Needed` status IS that queue — built right into the Case Manager record where Ops already work. No new object. |
| "We need to know which fields are missing" | The validator output is stored on the Case Manager (`PRM_NPDBValidationDetails__c` long-text JSON) at batch time AND rendered live in the manual button banner. |
| "We don't want to fire the NPDB request blindly" | T-180 gate skips AAL insert when validation fails. Manual paths block submission client-side. Both paths converge on the same validator. |

---

## 4. Inventory: every NPDB launch surface

This is what we have to harden. Each row is a place where an `PRM_AdverseActionLog__c` can be created today.

### 4.1 Automated (batch) surfaces

| Surface | Batch / class | Inserts AAL via | Status set on CM |
|---------|---------------|-----------------|------------------|
| T-180 recred kickoff | `PRM_CheckCAQHAccessOnDueAccountsBatch` → `PRM_CheckCAQHExecuteHelper.createActiveCAQHRecords` | `PRM_CheckCAQHRecordInitHelper.initializeAdvActionLogRecord` | `Pending NPDB` |
| Nightly re-initiate (stale NPDB report) | `PRM_ReinitiateNPDBReport` (scheduled by `PRM_ReinitiateNPDBReportScheduler`) | Clones existing AAL via `cloneAdverseActionLogsForReinitiation` | unchanged (CM already in a stage) |
| Org NPDB processor | `PRM_OrgNPDBProcessorBatch` / `PRM_OrgNPDBProcessorService` | (Org-side, not in this scope) | n/a |

### 4.2 Manual (user-initiated) surfaces

| Surface | Where it appears | OmniScript / IP launched | CM record types where button shows |
|---------|------------------|--------------------------|------------------------------------|
| **`Request NPDB` button** | `CustomButton.IndividualApplication.PRM_NPDB` on `PRM_CaseManagerRecordPage` and `PRM_NonParCaseMangerRecordPage` flexipages | `PRM_CallNPDB_English_2` OmniScript → `PRM_IPCreateAdverseActionLogParent` IP → `PRM_CreateAdverseActionNpdbBatch` Apex | `PRM_ReCredentialing`, `PRM_PractitionerParticipationRequest`, Ancillary Assessment / Re-Assessment (`RecordType.Name CONTAINS Assessment`) |
| **PSV Review NPDB step** | Embedded in `PRM_PSVSubOsWSNPDB_English_*` (versions 1–6) called by `PRM_PrimarySourceVerificationReview_English_*` | `PRM_CreateAdverseActionLog_Procedure_*` IP | Initial Credentialing (`PRM_Practitioner`) and ReCred PSV review |
| **Initial Cred App Review NPDB step** | Embedded in `PRM_InitialCredentialAppReview_English_*` and `PRM_CredentialAppReviewCompleteOS_English_*` | `PRM_CreateAdverseActionLog_Procedure_*` IP | `PRM_Practitioner` (initial cred only) |
| **Recred QC Review NPDB step** | Embedded in `PRM_RecredQC_English_*` | `PRM_CreateAdverseActionLog_Procedure_*` IP | `PRM_ReCredentialing` |

> **Note on the visibility rule for the manual button** (`PRM_CaseManagerRecordPage.flexipage-meta.xml` lines 49–102): the button shows only when **(1)** the user holds `PRM_CredentialingPermission` or `PRM_AncillaryCredSpecialistPermission`, **AND (2)** `PRM_Stage__c IN ('Committee Review','PSV','QC Review')` OR (`Application Review` AND `Status = 'Pending NPDB'`), **AND (3)** record type is `PRM_ReCredentialing`, `PRM_PractitionerParticipationRequest`, or anything whose name contains `Assessment`. Initial Cred (`PRM_Practitioner`) does **not** see this button — NPDB for initial cred fires only through the embedded OmniScript step.

### 4.3 The single Apex chokepoint

All five surfaces above eventually write to `PRM_AdverseActionLog__c` with `PRM_Status__c = 'Ready To Process'`. The downstream outbound NPDB integration polls that picklist. **That makes `PRM_AdverseActionLog__c` insert the right place to enforce a final server-side validation gate** — see US-NPDB-02 §3.4.

---

## 5. NPDB-required fields (the validation contract)

Below is the minimum field set that must be non-null/non-blank for a clean NPDB request, derived from `PRM_CheckCAQHRecordInitHelper.populate*` methods (lines 108–165) and `PRM_CreateAdverseActionNpdbBatch.execute` (lines 60–98). Variation per record type is captured in the right-most column.

| Group | Field on AAL | Source | Required for |
|-------|--------------|--------|--------------|
| **Identity** | `PRM_ProviderId__c` (Account Id) | Account.Id | All record types |
| | `PRM_Birthdate__c` | Account.PersonBirthdate | Practitioner record types (Cred, ReCred, PAR, Assessment) |
| | `PRM_IndividualNpi__c` + `PRM_IndividualNpiId__c` | `HealthcareProviderNpi.Npi` for the Account | All practitioner record types |
| **Org context** | `PRM_OrganizationName__c` | Account.Name (or orgAccount.Name for facility-bound) | All |
| | `PRM_OrganizationType__c` | `PRM_GlobalConstant.ORGTYPE_INDIVIDUAL` (for practitioner) / `OrgType` input (for facility) | All |
| **Address** (Primary) | `PRM_PrimaryStreetAddress__c`, `PRM_PrimaryCity__c`, `PRM_PrimaryState__c`, `PRM_PrimaryZip__c` | `Schema.Address` on Account / PracLoc | All |
| | `PRM_PrimaryAddressId__c` | Address.Id | All |
| | `PRM_PrimaryCounty__c` | Address.PRM_County__c | All (warning only — NPDB allows blank county) |
| **Licensure** | `PRM_Licensure__c` (JSON, first BusinessLicense) | `BusinessLicense WHERE LicenseClass = 'SBRD'` | Practitioner record types |
| **Education** | `PRM_ProfessionalSchool__c` (JSON) | `PersonEducation` | Practitioner record types |
| **Affiliation** (Ancillary only) | `PRM_AffiliationName__c`, `PRM_AffiliationStreetAddress__c`, `PRM_AffiliationCity__c`, `PRM_AffiliationState__c`, `PRM_AffiliationZip__c` | Practice Location selection | Ancillary Assessment / Re-Assessment |
| **Facility / NPI per location** | `PRM_HealthcareFacility__c`, per-facility NPI | Selected `HealthcareFacility` | Ancillary Assessment / Re-Assessment, Ancillary PAR |
| **Tax / Medicare** | `PRM_TaxID__c`, `PRM_MedicareNumber__c` | Account / OmniScript input | Ancillary Re-Assessment, PAR (Organization NPDB) |

The validator's responsibility is to compute, per Case Manager record type, **the right slice of this table** and return a structured `List<MissingFieldFinding>` describing every gap, the friendly name, and a navigable URL to the source object so the user can jump straight to the fix.

---

## 6. Status model

We add **one** new picklist value to `IndividualApplication.Status` AND `Case.Status`:

| Value | When set | Cleared by |
|-------|----------|------------|
| `NPDB Action Needed` | T-180 batch validation OR server-side AAL trigger gate finds missing data. **No AAL inserted.** | Auto-flip back to `Pending NPDB` once `PRM_NPDBValidationDetails__c` is empty after data fix (handled by `PRM_NPDBActionNeededReleaseAction` — small async/scheduled action) OR a manual user action |

Adjacent picklist values that already exist and we will **NOT** change:

- `Pending NPDB` — CM is sitting waiting for the NPDB report to come back (clean path)
- `Pending NPDB Action Needed` — **deprecated name** — we explicitly chose the shorter `NPDB Action Needed` because the previous value was never wired up and the UI label is cleaner

---

## 7. Deliverables (this design package)

| File | Purpose |
|------|---------|
| `00_Overview_NPDB_T180_Validation.md` | This document — context, inventory, contract |
| `01_Architecture_Diagrams.md` | Sequence, component, state, and validation-flow diagrams |
| `US_NPDB01_T180_BatchValidation_Routing.md` | Modify the T-180 batch to validate + route to `NPDB Action Needed` |
| `US_NPDB02_ManualNPDB_DataValidation.md` | Validate every manual surface (button, OmniScript steps) + show field-level error banner |
| `US_NPDB03_NPDBActionNeeded_Report.md` | Salesforce Report grouped by ReCred Due Date |

## 8. Out of scope

- Changes to the downstream NPDB outbound integration / NPDB API contract — these are upstream-only fixes.
- Org NPDB processor (`PRM_OrgNPDBProcessorBatch`) — separate story.
- Letter generation logic in `PRM_LetterRecredBatch` — does not need to change because we only add a new status value; letters continue to fire on existing values. (Will be revisited in US-NPDB-03 §5 if Ops wants the new status excluded from letters.)
- Initial Credentialing path is in scope for the **server-side AAL trigger gate** (US-NPDB-02 §3.4) but the manual `PRM_NPDB` button is not exposed to Initial Cred today.

## 9. Open questions for the user

| # | Question | Default if no answer |
|---|----------|----------------------|
| 1 | Should the `NPDB Action Needed` status be assigned to round-robin queues like `Pending NPDB` is today (`PRM_CaseTriggerHandler.caseStatuses` line 12)? | **Yes, same routing.** Otherwise the case sits unowned. |
| 2 | Should `PRM_LetterRecredBatch` send the standard recred letter when CM is in `NPDB Action Needed`? | **No** — wait until the data is fixed and CM flips back to `Pending NPDB`. |
| 3 | Should the auto-flip (`NPDB Action Needed → Pending NPDB`) happen on field save (trigger) or via nightly batch? | **Trigger** is faster; nightly batch is cheaper. Recommend **trigger** because Ops fixes are interactive. |
| 4 | Required-field contract for **PAR (`PRM_PractitionerParticipationRequest`)** — does it match Practitioner ReCred, or different? | Assume **same as ReCred** until business confirms; document the assumption in US-NPDB-02. |
