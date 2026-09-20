# Integrity Reporting Practitioner — Closed Cases

## *Initial Cred Review — Field Mapping Overview*

**Audience:** Business stakeholders, Integrity Reporting team, Credentialing Operations
**Prepared:** June 2026
**Purpose:** Confirm the source-of-truth for every column in the Initial Cred Review export before the report is regenerated directly from Salesforce.

---

## 1. What this report shows

Every Approved **Initial Credentialing** case for an individual physician, with one row per *tracked field change* (App Review, PSV, and key administrative events). The same header information about the case and practitioner is repeated on every row of that case so the data can be filtered, pivoted, or audited any way the business needs.

### Cohort included

A case appears in this export only when **all** of the following are true:

| Filter | Plain-language meaning |
| --- | --- |
| Case is **Approved** | The credentialing decision has been made and closed |
| Record Type = **Practitioner Participation Request** | This is an *initial* credentialing case (not Re-Cred, Ancillary, etc.) |
| Practitioner is a **Person Account** | The case is about an individual physician, not a facility or group |
| Decision Date falls in the requested window | The reporting window — typically a calendar quarter or year-to-date |

### Why this cohort

These four filters together produce the "Individual Physician — Full/Initial — Approved" group that the legacy Excel feed already shows in columns 2, 3, and 4. The new report keeps the same scope so existing dashboards and historical comparisons remain valid.

---

## 2. Column-by-column source mapping

The table below shows where each of the 18 columns comes from. **"Source"** is the Salesforce object and field that holds the value. **"Notes"** explains anything non-obvious.

| # | Column | Source | Notes |
| --- | --- | --- | --- |
| 1 | **Case ID** | Individual Application — Name | The IA-NNNNNNN case number. |
| 2 | **Cred Body** | *Constant:* `Individual Physician` | Derived from the cohort filter (Person Account + Practitioner Participation record type). |
| 3 | **Status** | Individual Application — Status | Always `Approved` for this tab — the closed-case filter. |
| 4 | **Credentialing Type** | *Constant:* `Full/Initial` | Derived from the record type (`Practitioner Participation Request` ⇒ Full/Initial; `Re-Credentialing` ⇒ Re-Cred). |
| 5 | **Practitioner ID** | Account → Practitioner Number → Name | The 11-digit IBX practitioner identifier. |
| 6 | **Practitioner NPI** | Healthcare Provider NPI — NPI<br/>*(Individual NPI tagged to the practitioner's Account; active row preferred when more than one exists)* | Standard Health Cloud NPI record on the Account. We deliberately do not filter on the *Active* flag — a small share of practitioners have only an inactive Individual NPI row tagged to their Account, and the legacy Excel feed never filtered on Active either. |
| 7 | **First Name** | Account — First Name | Person Account demographics. |
| 8 | **Middle Name** | Account — Middle Name | May be blank if not on file. |
| 9 | **Last Name** | Account — Last Name | Person Account demographics. |
| 10 | **Current Attestation Date** | Most recent **CAQH Attestation** field-change date for the practitioner across all their cases | Pulled from history, not a single field. Blank if the practitioner has never had an attestation event tracked. |
| 11 | **Review Name** | Individual Application History — Field | Friendly name (we strip the `PRM_` prefix and `__c` suffix). See §3 for the full list of 38 tracked fields. |
| 12 | **Review Previous Value** | Individual Application History — Old Value | What the field was before the change. Blank when this is the first time the field was set. Boolean fields show as `~` (legacy convention). |
| 13 | **Review Current Value** | Individual Application History — New Value | What the field changed to. The full list of values matches what users see in the Salesforce UI (e.g. `Data Looks Good`, `Not Applicable`, `PSV QC`, etc.). |
| 14 | **Review Date** | Individual Application History — Created Date<br/>*(date portion, GMT)* | When that specific field changed — the calendar date in GMT. |
| 15 | **Review Time** | Individual Application History — Created Date<br/>*(time portion `HH:mm:ss`, GMT)* | The time-of-day the field changed, in the same GMT timezone as Review Date so the two columns describe a single consistent moment. Together columns 14+15 give the full audit timestamp. |
| 16 | **Applied Date** | Individual Application — Applied Date | When the practitioner submitted their application. |
| 17 | **Decision Date** | Individual Application — Decision Date | Custom field on the case. The official decision date used for SLA reporting. |
| 18 | **Processing Time** | Individual Application — Case Manager Age | The case age in days, sourced directly from the Salesforce-managed *Case Manager Age* field (`PRM_CaseManagerAge__c`). The leading number is shown without the trailing `" days"` text so the column matches the legacy integer format. |
| 19 | **Applied After Decision Flag** | *Computed:* `Yes` if the field changed after the case was decided, else `No` | Audit signal — flags any review activity that happened after the case was closed. |

---

## 3. The 38 tracked fields (column 11 detail)

These are the only Individual Application fields whose changes appear in the **Review Name** column. Anything outside this list is filtered out so the export stays focused on credentialing-relevant activity.

### Application Review (10)

| Review Name in export | Field on Individual Application |
| --- | --- |
| Attestation Verification | `PRM_AttestationVerification__c` |
| License Verification | `PRM_LicenseVerification__c` |
| Education Verification | `PRM_EducationVerification__c` |
| Specialty Verification | `PRM_SpecialtyVerification__c` |
| Malpractice Coverage Verification | `PRM_MalpracticeCoverageVerification__c` |
| DEA Verification | `PRM_DEAVerification__c` |
| CDS Verification | `PRM_CDSVerification__c` |
| Work History Verification | `PRM_WorkHistoryVerification__c` |
| NPDB Verified On | `PRM_NPDBVerifiedOn__c` |
| NPDB Error Message | `PRM_NPDBErrorMessage__c` |

### PSV / Reviews (17)

| Review Name in export | Field on Individual Application |
| --- | --- |
| PSV Outcome | `PRM_PSVOutcome__c` |
| Contract Status | `PRM_ContractStatus__c` |
| CAQH Attestation | `PRM_CAQHAttestation__c` |
| Service Area PSV | `PRM_ServiceAreaPSV__c` |
| License PSV | `PRM_LicensePSV__c` |
| Specialty PSV | `PRM_SpecialtyPSV__c` |
| Admitting Privileges Review | `PRM_AdmittingPrivilegesReview__c` |
| Insurance PSV | `PRM_InsurancePSV__c` |
| Education PSV | `PRM_EducationPSV__c` |
| Work History PSV | `PRM_WorkHistoryPSV__c` |
| CDS PSV | `PRM_CDSPSV__c` |
| DEA PSV | `PRM_DEAPSV__c` |
| Board Certification PSV | `PRM_BoardCertificationPSV__c` |
| Disclosure Review | `PRM_DisclosureReview__c` |
| Medicare Opt-Out Review | `PRM_MedicareOptOutReview__c` |
| FSMB PSV | `PRM_FSMBPSV__c` |
| SAM Review | `PRM_SAMReview__c` |
| CMS Preclusion Review | `PRM_CMSPreclusionReview__c` |

### Operational / Administrative (11)

| Review Name in export | Field on Individual Application |
| --- | --- |
| Approved Date | `ApprovedDate` *(standard)* |
| Approved Date (custom) | `PRM_ApprovedDate__c` |
| Re-Cred Due Date | `PRM_ReCredDueDate__c` |
| Created By Id | `CreatedById` *(standard)* |
| Case Data Manager | `PRM_CaseDataManager__c` |
| Display Cap Sites | `PRM_DisplayCapSites__c` |
| NPDB Received | `PRM_NPDBReceived__c` |
| NPDB Verified | `PRM_NPDBVerified__c` |
| Role Change Request | `PRM_RoleChangeRequest__c` |
| First Name | `PRM_FirstName__c` |
| Last Name | `PRM_LastName__c` |

---

## 4. Sample row (illustrative)

> | Column | Value |
> | --- | --- |
> | Case ID | `IA-0000021599` |
> | Cred Body | `Individual Physician` |
> | Status | `Approved` |
> | Credentialing Type | `Full/Initial` |
> | Practitioner ID | `10000237353` |
> | Practitioner NPI | `1083292528` |
> | First Name | `Aleksandr` |
> | Last Name | `Abakulov` |
> | Current Attestation Date | `2025-12-29` |
> | Review Name | `License Verification` |
> | Previous Value | *(blank — first time set)* |
> | Current Value | `Data Looks Good` |
> | Review Date | `2026-02-17` |
> | Review Time | `15:16:14` *(GMT)* |
> | Applied Date | `2025-07-31` |
> | Decision Date | `2026-03-26` |
> | Processing Time *(Case Age)* | `306` |
> | Applied After Decision | `No` |
