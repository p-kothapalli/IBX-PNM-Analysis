# Integrity Reporting Practitioner — Closed Cases (Initial Cred Review) — Source Mapping & Runbook

**Purpose:** Replicate the legacy Excel export
"Integrity Reporting Practitioner – Closed Cases" → tab **Initial Cred Review**
directly from Salesforce, eliminating dependence on whatever external feed
produced the original spreadsheet.

**Deliverable:** Apex anonymous script
[`scripts/apex/integrity_reporting_initial_cred_review.apex`](../../scripts/apex/integrity_reporting_initial_cred_review.apex)
that emits a CSV ContentVersion (Salesforce Files) matching the legacy column
layout. Open in Excel, save as `.xlsx` if needed.

---

## 1. Cohort definition (which cases get included)

A case lands in this tab when **all** of these are true on `IndividualApplication`:

| Filter | Value | Why |
|---|---|---|
| `Status` | `Approved` | "Closed Cases" = approved decisions |
| `RecordType.DeveloperName` | `PRM_PractitionerParticipationRequest` | Distinguishes Initial Cred from Re-Cred / Ancillary / etc. |
| `Account.IsPersonAccount` | `true` | Filters to physician/practitioner records (not facilities/vendors) |
| `PRM_Decision_Date__c` | `>= DECISION_FROM AND <= DECISION_TO` | The reporting window (configurable in script) |

### Why these defaults

- **"Initial"** in the legacy "Credentialing Type" column = `RecordType.DeveloperName != 'PRM_ReCredentialing'`. Of the 12 record types on `IndividualApplication`, `PRM_PractitionerParticipationRequest` is the one driving full/initial credentialing for individual physicians.
- **"Individual Physician"** in the legacy "Cred Body" column = `Account.IsPersonAccount = true` on a Practitioner Participation IA.

If the business adds new initial-cred record types in the future, expand the filter on line 132 of the script.

---

## 2. Column-by-column source mapping

| # | Excel Column | Source | Type | Notes |
|---|---|---|---|---|
| 1 | Case ID | `IndividualApplication.Name` | String | e.g. `IA-0000021599` |
| 2 | Cred Body | *Literal* `Individual Physician` | Constant | Derived from cohort filter, not a field |
| 3 | Status | `IndividualApplication.Status` | Picklist | Always `Approved` for this tab |
| 4 | Credentialing Type | *Literal* `Full/Initial` | Constant | Derived from RecordType cohort filter |
| 5 | Practitioner ID | `Account.PRM_IdentifierPractitioner__r.Name` | String | 11-digit IBX practitioner number |
| 6 | Practitioner NPI | `HealthcareProviderNpi.Npi` where `AccountId = IA.AccountId AND NpiType = 'Individual'` (preferring `IsActive = true` when both exist; falls back to inactive when that's the only row) | String | Standard Health Cloud child object. The `IsActive = true` filter was removed in v2 because ~2.4% of practitioners have only an inactive Individual NPI row tagged to their Account, which previously came back blank. The legacy Excel feed never filtered on `IsActive`. |
| 7 | First Name | `Account.FirstName` | String | Person Account |
| 8 | Middle Name | `Account.MiddleName` | String | Person Account |
| 9 | Last Name | `Account.LastName` | String | Person Account |
| 10 | Current Attestation Date | `MAX(IndividualApplicationHistory.CreatedDate)` where `Field = 'PRM_CAQHAttestation__c'` and `IndividualApplication.AccountId = IA.AccountId` | Date | Most recent CAQH attestation event for the practitioner across **all** cases (cross-case lookup). Empty if practitioner has never had an attestation tracked. |
| 11 | Review Name | `friendlyName(IndividualApplicationHistory.Field)` — strips `PRM_` prefix and `__c` suffix | String | See the 38-field map below |
| 12 | Review Previous Value | `IndividualApplicationHistory.OldValue.toString()` | Polymorphic | Booleans render as `~` (legacy convention) |
| 13 | Review Current Value | `IndividualApplicationHistory.NewValue.toString()` | Polymorphic | Booleans render as `~`. For `CaseDataManager` you get the FK Id; for `CreatedById` you get the user Id; otherwise the picklist label / formatted date |
| 14 | Review Date | `IndividualApplicationHistory.CreatedDate` (date portion, GMT) | Date | When the field changed (calendar date in GMT) |
| 15 | Review Time | `IndividualApplicationHistory.CreatedDate` formatted as `HH:mm:ss` (GMT) | String | Time-of-day in GMT/UTC, kept in the same timezone as `Review Date` so the two columns describe a consistent moment. Concatenate cols 14+15 in Excel for a full timestamp |
| 16 | Applied Date | `IndividualApplication.AppliedDate` (date portion) | Date | Standard Salesforce datetime field |
| 17 | Decision Date | `IndividualApplication.PRM_Decision_Date__c` | Date | Custom date field; the official "decision" date used for SLA |
| 18 | Processing Time | `IndividualApplication.PRM_CaseManagerAge__c` | Integer (string from SF) | This is the **Case Age** — Salesforce-computed field that returns a string like `"306 days"`. The script strips the `" days"` suffix so the CSV value is a plain integer matching the legacy export format. Note: case age keeps growing for the life of the record; a closed-case run today shows the age as of run-time, not the time it took to decide. If you need true (Decision − Applied) processing time, derive it from columns 16 and 17. |
| 19 | Applied After Decision Flag | *Computed:* `Yes` if `Review Date > Decision Date`, else `No` | Yes/No | Audit signal — flags any field changes that happened after case closure |

### The 38 tracked fields (column 11 reverse-map)

These are the only `IndividualApplicationHistory.Field` values the script
consumes. Anything outside this set is ignored. Any of these that aren't yet
tracked in production must be enabled via **Setup → Object Manager →
Individual Application → Set History Tracking**.

| Review Name | Field API Name | Type |
|---|---|---|
| **Application Review (10)** | | |
| AttestationVerification | `PRM_AttestationVerification__c` | Picklist |
| LicenseVerification | `PRM_LicenseVerification__c` | Picklist |
| EducationVerification | `PRM_EducationVerification__c` | Picklist |
| SpecialtyVerification | `PRM_SpecialtyVerification__c` | Picklist |
| MalpracticeCoverageVerification | `PRM_MalpracticeCoverageVerification__c` | Picklist |
| DEAVerification | `PRM_DEAVerification__c` | Picklist |
| CDSVerification | `PRM_CDSVerification__c` | Picklist |
| WorkHistoryVerification | `PRM_WorkHistoryVerification__c` | Picklist |
| NPDBVerifiedOn | `PRM_NPDBVerifiedOn__c` | Date |
| NPDBErrorMessage | `PRM_NPDBErrorMessage__c` | TextArea |
| **PSV / Reviews (16)** | | |
| PSVOutcome | `PRM_PSVOutcome__c` | Picklist |
| ContractStatus | `PRM_ContractStatus__c` | Picklist |
| CAQHAttestation | `PRM_CAQHAttestation__c` | Picklist |
| ServiceAreaPSV | `PRM_ServiceAreaPSV__c` | Picklist |
| LicensePSV | `PRM_LicensePSV__c` | Picklist |
| SpecialtyPSV | `PRM_SpecialtyPSV__c` | Picklist |
| AdmittingPrivilegesReview | `PRM_AdmittingPrivilegesReview__c` | Picklist |
| InsurancePSV | `PRM_InsurancePSV__c` | Picklist |
| EducationPSV | `PRM_EducationPSV__c` | Picklist |
| WorkHistoryPSV | `PRM_WorkHistoryPSV__c` | Picklist |
| CDSPSV | `PRM_CDSPSV__c` | Picklist |
| DEAPSV | `PRM_DEAPSV__c` | Picklist |
| BoardCertificationPSV | `PRM_BoardCertificationPSV__c` | Picklist |
| DisclosureReview | `PRM_DisclosureReview__c` | Picklist |
| MedicareOptOutReview | `PRM_MedicareOptOutReview__c` | Picklist |
| FSMBPSV | `PRM_FSMBPSV__c` | Picklist |
| SAMReview | `PRM_SAMReview__c` | Picklist |
| CMSPreclusionReview | `PRM_CMSPreclusionReview__c` | Picklist |
| **Operational (10)** | | |
| ApprovedDate | `ApprovedDate` (standard) | Datetime |
| CreatedById | `CreatedById` (standard) | Reference |
| CaseDataManager | `PRM_CaseDataManager__c` | Reference |
| DisplayCapSites | `PRM_DisplayCapSites__c` | Boolean → `~` |
| NPDBReceived | `PRM_NPDBReceived__c` | Boolean → `~` |
| NPDBVerified | `PRM_NPDBVerified__c` | Boolean → `~` |
| RoleChangeRequest | `PRM_RoleChangeRequest__c` | Picklist |
| FirstName | `PRM_FirstName__c` | String |
| LastName | `PRM_LastName__c` | String |
| ApprovedDate (custom) | `PRM_ApprovedDate__c` | Date |
| ReCredDueDate | `PRM_ReCredDueDate__c` | Date |

### Why some values render as `~`

The legacy export shows `~` for boolean-tracked fields (`PRM_DisplayCapSites__c`,
`PRM_NPDBReceived__c`, `PRM_NPDBVerified__c`). Salesforce's
`IndividualApplicationHistory.OldValue/NewValue` returns these as `Boolean`
objects; the legacy export tool stringified them as `~`. The script preserves
that convention.

---

## 3. Runbook

### One-time setup

Confirm history tracking is enabled in production for **all 38 fields** above.
If any are missing, the corresponding `Review Name` rows simply won't appear in
the export.

```bash
# Quick coverage check (run from sf CLI):
sf data query --target-org production --query "SELECT Field, COUNT(Id) FROM IndividualApplicationHistory WHERE CreatedDate = LAST_N_MONTHS:3 GROUP BY Field ORDER BY COUNT(Id) DESC"
```

Compare the output against the 38-field list above.

### Run the export

1. Edit lines 86–87 of [`integrity_reporting_initial_cred_review.apex`](../../scripts/apex/integrity_reporting_initial_cred_review.apex):
   ```apex
   Date DECISION_FROM = Date.newInstance(2026, 1, 1);
   Date DECISION_TO   = Date.newInstance(2026, 5, 31);
   ```

2. Execute against the target org:
   ```bash
   sf apex run \
     --file scripts/apex/integrity_reporting_initial_cred_review.apex \
     --target-org production
   ```

3. The debug log prints these summary lines (capture them for the run-log):
   ```
   Cohort size: <N> cases
   NPI rows fetched: <N>
   Practitioners with prior CAQH attestation history: <N>
   History rows fetched: <N>
   Cases emitted: <N>   skipped (no tracked history): <N>
   Data rows: <N>
   Title:           IntegrityReporting_InitialCredReview_<YYYYMMDD>
   ContentVersion:  068...
   ```

4. Open the file in Salesforce: **App Launcher → Files → Owned by Me →
   `IntegrityReporting_InitialCredReview_<YYYYMMDD>`** → **Download**.

5. The downloaded `.csv` opens directly in Excel. Save as `.xlsx` if business
   wants the formatted workbook. The CSV layout already matches the legacy
   tab's column order, so no rearrangement is needed.

### Sharing the file

The ContentVersion is owned by the running user. To share with the business:

- **One-off:** open Files → right-click → Share → add user/group.
- **Recurring:** modify the script to insert a `ContentDocumentLink` against a
  Library or User Group after the `insert cv;` line.

### Run characteristics (QA, May 2026 window)

| Metric | Value | Limit | Headroom |
|---|---|---|---|
| SOQL queries | 7 | 100 | 93% |
| Query rows | 8,889 | 50,000 | 82% |
| CPU time | 1,178 ms | 10,000 ms | 88% |
| DML rows | 1 (the ContentVersion) | 10,000 | 99.99% |
| Heap | 0 (under 6MB) | 6,000,000 | 100% |

The cohort query is the highest-volume one. With ~35 history rows per emitted
case, the 50K SOQL row cap supports up to ~1,400 emitted cases per run. For
larger windows, run multiple smaller windows back-to-back (e.g. quarter-by-
quarter) and concatenate the CSVs.

---

## 4. Open items / known limitations

| Item | Status |
|---|---|
| **xlsx generation** | Apex cannot natively produce `.xlsx`. The CSV opens directly in Excel; the user re-saves as `.xlsx` if the business wants a formatted workbook. If true `.xlsx` automation is needed later, wrap the script with a Python post-processor (openpyxl) or move to a Schedulable Apex class that emails the file as an Excel attachment. |
| **Re-Cred / Ancillary tabs** | Same script structure works — change the `RecordType.DeveloperName` filter to `PRM_ReCredentialing` (Partial Recred Review) or `PRM_AncillaryAssessment` (Ancillary Assessment Review). Worth refactoring into a parameterized helper if multiple tabs become regular asks. |
| **Current Attestation Date for new practitioners** | If a practitioner has never had a CAQH attestation event tracked (`PRM_CAQHAttestation__c` field history empty for all their cases), this column will be blank. That's the same behavior as the legacy export. |
| **`CreatedById` legacy values** | Some history rows store user IDs as numeric values (e.g. `'74'`) — leftovers from a data migration. The script passes them through verbatim; the legacy export did the same. If you want friendly names, post-process the CSV. |

---

## 5. Change history

| Date | Change | Author |
|---|---|---|
| 2026-06-02 | Initial script + mapping doc. Verified in QA against 49-case cohort (Jan–May 2026 window). | (this session) |
