# IBX Vendor "Provider Intelligence" Feed — Data Dictionary Request (v1)

**Date:** 2026-05-13
**Audience:** Vendor delivery / data engineering team (with IBX Cred + PDM business co-pilots)
**Purpose:** Catalog **every source-of-truth field IBX needs from the vendor to retire (or replace) the CAQH-driven Primary Source Verification (PSV) workflow.** This is the consolidated ask after reviewing (a) the vendor's `IBX_Sample_PI_Dataset_04_29_2026.xlsx` (11 tabs / ~150 NPI sample) and (b) the IBC PNM Data Dictionary V5.6 WIP (72 tabs covering the full PIE data model).
**Companion docs:**
- `requirements/vendor/Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md` (gap analysis, decision framework)
- `requirements/vendor/Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md` (NPDB test-set methodology)

---

## 0. Scope & Filtering Rules (read this first)

This document **only lists source-of-truth fields**, i.e. data that IBX today **verifies from an external primary source** (CAQH, state medical boards, NPDB, DEA, ABMS/AOA, AMA Profiles, NPPES, OIG/SAM/CMS, hospital staff offices, insurance carriers, accrediting bodies).

We deliberately **EXCLUDE** every field that IBX itself creates, sets, or maintains. These are workflow / state-tracking artifacts and are **not** something the vendor should attempt to populate. Examples of excluded fields (present on most PIE objects but **not** requested from the vendor):

| Excluded category | IBX field examples |
|---|---|
| IBX activation window on a PIE record (NOT the source date) | `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c` |
| IBX activation flags | `PRM_Active__c`, `IsActive` (on PIE custom records), `PRM_Pending__c` |
| Error / exception tracking | `PRM_IsErrorRecord__c`, `PRM_IsError__c`, `PRM_ErrorMessage__c` |
| Case workflow linkage | `PRM_CaseManager__c`, `PRM_Case__c`, `PRM_RequestType__c`, `PRM_ChangeReason__c` |
| Salesforce system fields | `Id`, `CreatedById`, `CreatedDate`, `LastModifiedById`, `LastModifiedDate`, `OwnerId`, `RecordTypeId`, `SystemModstamp`, `LastViewedDate`, `LastReferencedDate` |
| IBX external/business keys | `PRM_ExternalId__c`, `SourceSystem`, `SourceSystemIdentifier`, `HealthCloudGA__SourceSystemId__c`, `PRM_LatestVersionId__c`, `PRM_MergeKey__c`, `PRM_ParentGUID__c` |
| IBX-derived formulas | `PRM_NPIEffectiveToday__c`, `PRM_AddressEffectiveToday__c`, `PRM_PracticeLocationEffectiveToday__c`, `PRM_CountOfActivePractitioners__c`, anything `Formula (...)` |
| IBX directory print toggles | `PRM_IsDirectoryPrint__c`, `PRM_HispanicLatinoIsDirectoryPrint__c`, `PRM_RaceIsDirectoryPrint__c`, `PRM_EthnicityIsDirectoryPrint__c` |
| IBX-internal status pickers | `PRM_Status__c` (when populated by IBX MDR), `VerificationStatus`, `Status` (on internal review), `PRM_CredentialingStatus__c`, `PRM_NetworkParticipationType__c` |
| IBX directory display & member-facing presentation toggles | `PRM_MemberSelectablePCP__c`, `PRM_DirectoryExceptionType__c`, `PRM_DirectoryDisplayException__c` |
| IBX-only MDR review fields | `PRM_NPDBAction__c`, `PRM_MalpracticeSanctionReview__c`, `PRM_Amounts__c`, `PRM_DatesSettled__c`, `PRM_OtherConcerns__c`, `PRM_PreviouslyReviewedBy__c` (the MDR's record of their own review) |
| IBX-only PDM/Network linkage | `ProviderNetworkContractId`, `ProviderNetworkTierId`, `PRM_AgreementType__c`, `PRM_ClaimType__c`, `PRM_ClaimClass__c`, `PRM_LegacyIdentifier__c` (BSPA), `PRM_HC3CaseNumber__c` |
| IBX termination booking | `PRM_TerminationReason__c`, `TerminationDate`, `TerminationReason` (when set by IBX in response to vendor data) |

> ⚠️ **Critical distinction — "Effective Date" fields:**
> - Fields like `IssueDate`, `Provider License Effective Date`, `License Expiration Date`, `Period Start / Period End`, `Current Certification Date`, `Board Original`, `Board Re-Cert`, `Expiration Date` (on board cert), `Completion Date` (education), `NPI Enumeration Date`, `Accreditation Effective Date / Expiration Date`, `DEA Issue / Expiration Date`, etc. ARE **source dates from the issuing authority**. We **DO** need these from the vendor.
> - Fields like `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` on objects like `Address`, `Identifier`, `BoardCertification`, `BusinessLicense`, `PersonEducation`, `HealthcareProviderTaxonomy` are **IBX's internal record-active-window dates** — IBX itself fills them when activating/terminating a record in PIE. We **DO NOT** need these from the vendor.

---

## 1. Vendor Coverage — Snapshot

The vendor sample currently includes 11 tabs. Coverage by domain:

| Domain | Vendor tab(s) | Vendor coverage | Action needed from vendor |
|---|---|---|---|
| Practitioner demographics | Demographic | 🟢 Good (DOB/SSN masked) | Confirm unmasked under BAA; add 5 minor fields |
| NPI registration / lifecycle | Demographic | 🟢 Good | None |
| Addresses (practice/billing) | Addresses | 🟡 Partial | Add Mailing type, Fax, Zip+4 |
| Taxonomy / Specialty | Taxonomy | 🟢 Good | Confirm taxonomy type/group/section consistency |
| Hospital Affiliations | Affiliations | 🟡 Partial | Add lifecycle (dates, privilege status, staff category) |
| State Licenses | Licenses | 🟡 Partial | Add license class, disciplinary detail |
| Federal exclusions / sanctions | Sanctions + SUMMARY | 🟢 Good (state/fed) | Confirm refresh cadence |
| Criminal background | Offenses | 🟡 Confirm scope | Verify completeness, healthcare-relevance filter |
| Open Payments | SuspiciousOwnership | 🟢 Net-new | None (net-new value-add) |
| Quality scoring | MIPS, CMS STAR | 🟢 Net-new | None (net-new value-add) |
| **Tax ID / EIN** | — | 🔴 **MISSING** | **Add — single biggest gap** |
| **DEA Registration** | — | 🔴 **MISSING** | **Add — full DEA record** |
| **CDS (state controlled-substance license)** | — | 🔴 **MISSING** | **Add — full CDS record** |
| **Board Certifications (ABMS / AOA)** | — | 🔴 **MISSING** | **Add — full cert record** |
| **Education / training** | — | 🔴 **MISSING** | **Add — full education record** |
| **Work history** | — | 🔴 **MISSING** | **Add — full work history record** |
| **Malpractice Insurance (COI)** | — | 🔴 **MISSING** | **Add — full COI record** |
| **NPDB-equivalent malpractice claims** | — | 🔴 **MISSING** | **Add or confirm cannot supply** |
| **Hospital privileges lifecycle** | Affiliations (name only) | 🔴 **MISSING** | **Add admitting privileges fields** |
| Facility accreditation (JCAHO/ACHC/etc.) | — | 🔴 **MISSING** | **Add for ancillary cred** |
| Languages spoken / pronouns | — | 🔴 **MISSING** | **Add (directory)** |
| Provider email / phone | Addresses.PHONE only | 🟡 Partial | Add provider email, mobile, fax |

The rest of this document is the **field-by-field shopping list** organized by PSV verification step.

---

## 2. SECTION A — Fields the Vendor ALREADY Provides

These fields are in the current sample (`IBX_Sample_PI_Dataset_04_29_2026.xlsx`). **Listed here for completeness/contract clarity, not as a new ask.** Vendor must agree to ship these consistently for the full IBX population (PA/NJ/DE participating practitioners and facilities) on the agreed refresh cadence.

### 2.1 Demographic tab ✓

| Vendor column | Maps to IBX object.field | PSV step |
|---|---|---|
| `NPI` | `HealthcareProviderNpi.Npi` | All steps |
| `FULLNAME` | `Contact.Name` / `Account.Name` | All steps |
| `FIRSTNAME` / `MIDDLENAME` / `LASTNAME` | `Contact.FirstName/MiddleName/LastName` | All steps |
| `TITLE` | `Account.PersonTitle` / `Contact.Title` | All steps |
| `ORGANIZATIONNAME` | `Account.Name` (for org NPIs) | Ancillary cred |
| `OTHERBUSINESSNAME` | `Account.PRM_DoingBusinessAsName__c` | PDM |
| `ENTITYTYPE` / `ENTITYTYPECODE` | NPPES code (1=Individual, 2=Org) | All steps |
| `AUTHORIZEDOFFICIALCONTACTNAME` / `…TITLE` / `…PHONE_NUM` | Org-NPI authorized rep | Ancillary cred |
| `SSN` (masked in sample) | `Contact.PRM_SSN__c` (where stored) | Identity verification |
| `DOB` (masked in sample) | `Contact.Birthdate` / `Account.PersonBirthdate` | Identity verification |
| `NPI_ENUMERATIONDATE` | `HealthcareProviderNpi.EffectiveFrom` (source date — NPPES) | NPI verify |
| `NPIDEACTIVATIONDATE` | (source date — NPPES) — net new for IBX | NPI verify / surveillance |
| `NPIREACTIVATIONDATE` | (source date — NPPES) — net new for IBX | NPI verify / surveillance |
| `PRIMARYSPECIALITY` | `Account.PRM_ProviderSpecialties__c` / `CareTaxonomy.Name` | Specialty verify |
| `CCN` | `Identifier` (CMS Certification Number) | CMS verify |
| `MEDICARE_OPT_OUT` | Replaces `VerifyMedicareOptOut` step | Medicare opt-out |

### 2.2 Addresses tab ✓

| Vendor column | Maps to IBX object.field | PSV step |
|---|---|---|
| `ADDRESSTYPE` | `Address.PRM_AddressType__c` (Practice/Billing — confirm Mailing) | Service-area verify |
| `ADDR1` / `ADDR2` | `Address.PRM_AddressLine1__c` / `PRM_AddressLine2__c` | Service-area verify |
| `CITY` | `Address.PRM_City__c` | Service-area verify |
| `STATE` | `Address.PRM_State__c` | Service-area verify |
| `COUNTY` | `Address.PRM_County__c` | Service-area verify |
| `ZIP` | `Address.PRM_Zip__c` | Service-area verify |
| `PHONE` | `Address.PRM_Phone__c` / `Account.Phone` | Directory |
| `UPDATEDATETIME` | (vendor refresh timestamp — net new for IBX) | Data currency |
| `LATITUDE` / `LONGITUDE` | `Address.PRM_Geolocation__c` (net new — vendor-computed) | Member search radius |

### 2.3 Taxonomy tab ✓

| Vendor column | Maps to IBX object.field | PSV step |
|---|---|---|
| `TAXONOMYGROUPING` | `CareTaxonomy.PRM_TaxonomyGrouping__c` | Specialty verify |
| `SPECIALITY` | `CareTaxonomy.Name` / `PRM_TaxonomySpecialization__c` | Specialty verify |
| `TAXONOMYCODE` | `CareTaxonomy.TaxonomyCode` (NUCC X12) | Specialty verify |
| `LICENSENUMBER` | `BusinessLicense.LicenseNumber` (taxonomy↔license link) | Specialty / license |
| `STATE` | `BusinessLicense.PRM_LicenseState__c` | Specialty / license |
| `PRIMARYTAXONOMYFLAG` | `HealthcareProviderTaxonomy.IsPrimaryTaxonomy` | Specialty verify |

### 2.4 Affiliations tab ✓ (partial — see §3.9 for gaps)

| Vendor column | Maps to IBX object.field | PSV step |
|---|---|---|
| `FACILITYTYPE` | `HealthcareFacility.PRM_VendorType__c` | Admitting privileges |
| `FACILITYNAME` | `HealthcareFacility.Name` | Admitting privileges |
| `ADDRESS` / `CITY` / `STATE` / `ZIPCODE` | `Address` linked to facility | Admitting privileges |

### 2.5 Licenses tab ✓ (partial — see §3.4 for gaps)

| Vendor column | Maps to IBX object.field | PSV step |
|---|---|---|
| `LICENSENUMBER` | `BusinessLicense.LicenseNumber` | License verify |
| `LICENSESTATE` | `BusinessLicense.PRM_LicenseState__c` | License verify |
| `LICENSEEFFECTIVEDATE` | `BusinessLicense.PRM_ProviderLicenseEffectiveDate__c` (source date) | License verify |
| `LICENSEEXPIRATIONDATE` | `BusinessLicense.PRM_ProviderLicenseExpirationDate__c` (source date) | License verify |
| `ACTIVEFLAG` | (Source state-board "Active"/"Inactive" — distinct from IBX's `IsActive`) | License verify |

### 2.6 Sanctions, Offenses, SuspiciousOwnership, MIPS, CMS STAR, SUMMARY ✓ (net-new value)

Already inventoried in §1.6–§1.10 of `Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md`. No new fields requested — but we **do** need formal SLA on refresh cadence and source attribution (see §5 Open Questions).

---

## 3. SECTION B — Fields IBX NEEDS the Vendor to ADD

This is the priority list. Each subsection corresponds to one PSV verification step that the vendor's current sample **cannot** support. The vendor has claimed they can supply the full CAQH-replacement dataset — these are the fields they must commit to delivering in writing before the next vendor evaluation gate.

### 3.1 ⛔ CRITICAL — Tax ID / EIN (Group + Individual)

**Why it matters:** The single biggest blocker for using the vendor in PDM. Without Tax ID we cannot link practitioners to billing/capitated bundles, drive group-practice association, run NPI↔Tax ID validation for CMS, or replace the `VerifyTaxId` step in Ancillary PSV.

**Fields required:**

| Field name | Type | Source attribution required | IBX maps to |
|---|---|---|---|
| Tax ID (EIN) | Text(9) | IRS-issued; tie to NPI + Address | `Identifier.IdValue` where `PRM_Type__c = 'EIN - Tax Id'` |
| Tax ID Type | Picklist (EIN, SSN-based) | | `Identifier.PRM_Type__c` |
| Tax ID Effective Date | Date | Source — IRS issue date | (new field) |
| Tax ID Termination Date | Date | If applicable | (new field) |
| Tax ID Group Practice Name | Text(255) | Name registered to the EIN | `Account.Name` (group) |
| Tax ID ↔ NPI link | Relationship | Many-to-many at provider level | `HealthcareProviderNpi` ↔ `Identifier` join |
| Tax ID ↔ Practice Address link | Relationship | Service-address binding | `Address` ↔ `Identifier` join |
| Authorized Official for Tax ID | Text(255) | If org-level | `Account.PRM_PayeeName__c` |

### 3.2 ⛔ CRITICAL — DEA Registration

**Why it matters:** Required for `DEAVerification` step (`PRM_PSVSubOsWSNPDB`). Cannot retire the CAQH-driven DEA verification without these fields. NCQA requires DEA verification for prescribers.

**Fields required:**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| DEA Number | Text(9) | DEA registration ID | `Identifier.IdValue` where `PRM_Type__c = 'DEA'` (extension needed) |
| DEA Issue Date | Date | DEA-issued | (new field) |
| DEA Expiration Date | Date | DEA-issued | (new field) |
| DEA State | Picklist (US state codes) | State of registration | `Identifier.PRM_LicenseState__c` |
| DEA Schedules | Multi-Picklist (II, IIN, III, IIIN, IV, V) | DEA-issued | (new field) |
| DEA Status | Picklist (Active, Surrendered, Suspended, Revoked, Restricted) | DEA-issued | (new field) |
| DEA Address (registered location) | Address fields | DEA-issued | (new field) |
| DEA Business Activity Code | Text | DEA classification (e.g. Practitioner, MLP, Pharmacy) | (new field) |

### 3.3 ⛔ CRITICAL — CDS / State Controlled Dangerous Substances License

**Why it matters:** Required for `CDSVerification` step. Each state has its own controlled-substance authority (PA, NJ, DE in IBX's footprint). Cannot retire CAQH-driven CDS verification without these fields.

**Fields required:**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| CDS Number | Text(50) | State CDS authority | `Identifier.IdValue` where `PRM_Type__c = 'CDS'` (extension needed) |
| CDS State | Picklist | State that issued it | `Identifier.PRM_LicenseState__c` |
| CDS Effective Date | Date | State-issued | (new field) |
| CDS Expiration Date | Date | State-issued | (new field) |
| CDS Status | Picklist (Active, Expired, Surrendered, Suspended) | State-issued | (new field) |
| CDS Schedules | Multi-Picklist | If state distinguishes | (new field) |

### 3.4 ⛔ CRITICAL — Enhanced License Detail (in addition to existing Licenses tab)

**Why it matters:** The current Licenses tab covers number / state / effective / expiration / active flag. We also need **license class** (MD vs. DO vs. CRNP vs. PA-C, etc.) and **disciplinary detail at the license-record level** to fully retire the state-board click-through in `VerifyLicense`.

**Fields to ADD to existing Licenses tab:**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| License Class | Picklist (MD, DO, CRNP, PA-C, APN, RN, LPN, PT, OT, ST, RD, Pharmacist, Dentist, Chiropractor, Optometrist, Podiatrist, etc.) | State board | `BusinessLicense.LicenseClass` |
| License Issue Date | Date | State board original-issue date | `BusinessLicense.IssueDate` |
| License Status Detail | Picklist (Active in Good Standing, Active with Conditions, Active under Probation, Disciplinary Action Pending, Suspended, Revoked, Surrendered, Inactive, Lapsed) | State board | `BusinessLicense.Status` |
| Disciplinary Action Indicator | Boolean | State board / NPDB | (new field) |
| Disciplinary Action Effective Date | Date | If status has condition/probation/suspension | (new field) |
| License Restrictions Free-text | Text Area(2000) | If conditions exist | (new field) |
| Issuing Authority Name | Text(255) | e.g. "Pennsylvania State Board of Medicine" | `BusinessLicense.Issuer` |
| License Jurisdiction Type | Picklist (State, Country, Province) | | `BusinessLicense.JurisdictionType` |
| Primary License Indicator | Boolean | The practitioner's primary license | `BusinessLicense.IsPrimaryLicense` |
| Source Verified On | Datetime | Vendor-side verification date for NCQA audit | `BusinessLicense.VerifiedDate` |
| Verification Source | Text(64) | "PA PALS" / "NJ DCA" / "DELPROS" / "FSMB" | (new field — NCQA needs source attribution) |

### 3.5 ⛔ CRITICAL — Board Certifications (ABMS / AOA / Other Specialty Boards)

**Why it matters:** Required for `BoardCertificationsStep` (`PRM_PSVSubOsSummary`). Cannot retire CAQH-driven board-cert verification without these. IBX's `BoardCertification` standard object has 30+ fields populated today via CAQH.

**Fields required (one record per practitioner-board-certification):**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Board Name | Text(255) | e.g. "American Board of Internal Medicine" | `BoardCertification.BoardName` |
| Board Issuing Organization | Picklist (ABMS, AOA, ABOMS, Specialty board direct) | | (new field) |
| Certification Name / Type | Picklist (matches `BoardCertification.CertificationType` — 23 values) | Board-issued | `BoardCertification.CertificationType` |
| Certificate Identifier / Cert # | Text(255) | Board-issued | (new field) |
| Original Certification Date | Date | First board-cert date | `BoardCertification.PRM_BoardOriginal__c` |
| Most Recent Re-Certification Date | Date | Latest recert | `BoardCertification.PRM_BoardReCert__c` |
| Current Certification Date | Date | Currently-valid cert start | `BoardCertification.CurrentCertificationDate` |
| Certification Expiration Date | Date | When cert expires | `BoardCertification.ExpirationDate` |
| Board Certification Status | Picklist (Certified, Not Certified, MOC In Progress, Lapsed, Suspended, Revoked) | Board-issued | `BoardCertification.Status` |
| Sub-Specialty | Text(255) | Sub-cert if any | (new field) |
| Maintenance of Certification (MOC) Status | Picklist (In Compliance, Not in Compliance, N/A) | Board-issued | (new field) |
| Source Verified On | Datetime | Vendor-side verification date | (new field) |
| Verification Source | Text(64) | "ABMS" / "AOA" / direct board | (new field) |

### 3.6 ⛔ CRITICAL — Education / Training

**Why it matters:** Required for `EducationVerification` step (`PRM_PSVSubOsWSNPDB`). IBX's `PersonEducation` standard object has 30+ fields populated today via CAQH and direct institution verification.

**Fields required (one record per practitioner-degree):**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Education Level | Picklist (matches IBX's 17-value list: Medical School, Dental School, Residency, Fellowship, etc.) | Institution-issued | `PersonEducation.EducationLevel` |
| Degree Name | Text(255) | "MD", "DO", "DDS", "PharmD", "PhD", etc. | `PersonEducation.Name` |
| Institution Name | Text(255) | Granting institution | `PersonEducation.PRM_Institution__c` (via `PRM_Institution__c` reference object) |
| Institution Address | Address fields | City/State/Country of institution | (new field) |
| Education Specialty | Text(255) | If applicable (e.g. for residency/fellowship) | `PersonEducation.PRM_EducationSpecialty__c` |
| Start Date | Date | Enrollment start | `PersonEducation.PRM_StartDate__c` |
| End Date | Date | Enrollment end (or expected end) | `PersonEducation.PRM_EndDate__c` |
| Graduation / Completion Date | Date | Actual graduation | `PersonEducation.CompletionDate` / `PRM_GraduationDate__c` |
| Completion Status | Picklist (Completed, In Progress, Withdrew, Dismissed) | Institution-issued | `PersonEducation.PRM_Completed__c` |
| Certificate Identifier | Text(255) | Diploma / cert number | `PersonEducation.CertificateIdentifier` |
| Program Name | Text(255) | Specific program if not the degree itself | `PersonEducation.ProgramName` |
| Primary Indicator | Boolean | Is this the practitioner's primary degree for credentialing? | `PersonEducation.PRM_Primary__c` |
| Source Verified On | Datetime | NCQA audit trail | `PersonEducation.VerifiedDate` |
| Verification Source | Text(64) | "AMA Profiles" / "Direct Institution Verification" / "CAQH" | (new field) |

### 3.7 ⛔ CRITICAL — Work History / Employment

**Why it matters:** Required for `WorkHistoryVerification` step (`PRM_PSVSubOsWSNPDB`). NCQA requires 5-year employment history with gap explanations for initial cred.

**Fields required (one record per employment period):**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Employer Name | Text(255) | Self-reported then verified | (new — IBX uses `WorkHistory` derived from CAQH) |
| Employer Address Line 1 / 2 | Text(60) | | |
| Employer City / State / Zip | | | |
| Employer Phone | Phone | For verification call-out | |
| Employer Type | Picklist (Hospital, Group Practice, Solo, Academic, Locum Tenens, Government, Military) | | |
| Position / Title | Text(255) | | |
| Start Date | Date | | |
| End Date | Date (null if current) | | |
| Is Current Employer | Boolean | | |
| Reason for Leaving | Text(255) | If end date populated | |
| Gap Indicator | Boolean (vendor-computed if gap >30 days) | | |
| Gap Explanation | Text Area(2000) | Provider-supplied; vendor relays | |
| Source Verified On | Datetime | NCQA audit | |
| Verification Source | Text(64) | "Employer Verification Letter" / "CAQH attestation" | |

### 3.8 ⛔ CRITICAL — Malpractice Insurance (Certificate of Insurance)

**Why it matters:** Required for `CertificateofInsuranceVerification` step (`PRM_PSVSubOsTxnyRole`) and `VerifyInsurance` in `PRM_AncillaryPSVForm`. Cannot retire CAQH-driven COI verification without these.

**Fields required (one record per active policy):**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Carrier Name | Text(255) | Insurance carrier | (new) |
| Policy Number | Text(100) | Carrier-issued | (new) |
| Policy Type | Picklist (Occurrence, Claims-Made, Tail Coverage) | Carrier-issued | (new) |
| Per-Occurrence Limit | Currency | Carrier — typically $1M minimum for credentialing | (new) |
| Per-Aggregate Limit | Currency | Carrier — typically $3M minimum | (new) |
| Policy Effective Date | Date | Carrier-issued | (new) |
| Policy Expiration Date | Date | Carrier-issued | (new) |
| Insured Name | Text(255) | Practitioner (or group) named insured | (new) |
| Coverage Type | Picklist (Individual, Group, Hospital Self-Insured, Government Self-Insured) | | (new) |
| Tail / Prior Acts Coverage | Boolean | If switching policies | (new) |
| Continuous Coverage Indicator | Boolean | Has there been any lapse in last 5 years? | (new) |
| Lapse Periods | Text Area(2000) | If continuous = false | (new) |
| Source Verified On | Datetime | NCQA audit | (new) |
| Verification Source | Text(64) | "Carrier COI Document" / "Carrier Direct Verification" | (new) |

### 3.9 ⛔ CRITICAL — Hospital Affiliations & Admitting Privileges (lifecycle detail)

**Why it matters:** The current Affiliations tab only ships name + address. The `AdmittingPrivileges` step needs the **lifecycle**: when did they get privileges, what staff category, are the privileges restricted or temporary, what's the current status.

**Fields to ADD to existing Affiliations tab:**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Affiliation Start Date | Date | Hospital staff office | `HealthcarePractitionerFacility.InitialStartDate` |
| Affiliation End Date | Date (null if active) | Hospital staff office | `HealthcarePractitionerFacility.TerminationDate` |
| Staff Category | Picklist (Active, Courtesy, Consulting, Honorary, Provisional, Affiliate, Telemedicine, Allied Health) | Hospital staff office | (new field) |
| Privilege Status | Picklist (Unrestricted, Temporary, Provisional, Restricted, Suspended, Surrendered, Revoked, Denied) | Hospital staff office | (new field) |
| Admitting Rights Indicator | Boolean | Does this practitioner admit at this facility | `HealthcarePractitionerFacility.RecordType = "Admitting Rights"` |
| Restrictions Free-text | Text Area(2000) | If status has restrictions | (new field) |
| Department / Service | Text(255) | e.g. "Internal Medicine", "Cardiology" | (new field) |
| Who Admits For You | Text(255) | If the practitioner doesn't have admitting privileges, name the colleague who admits on their behalf (NCQA-required) | (new field) |
| Termination Reason | Picklist (Voluntary Resignation, Facility Closed, Loss of Privileges, Other) | Hospital staff office | `HealthcarePractitionerFacility.TerminationReason` |
| Source Verified On | Datetime | NCQA audit | (new field) |
| Verification Source | Text(64) | "Hospital Staff Office" / "CAQH attestation" | (new field) |
| Hospital NPI | Text(10) | NPPES org NPI | `HealthcarePractitionerFacility.HealthcareFacilityId → HealthcareFacility → HealthcareProviderNpi` |
| Hospital Tax ID | Text(9) | IRS | (see §3.1) |

### 3.10 ⛔ CRITICAL (NPDB-equivalent) — Malpractice Claims & Adverse Actions

**Why it matters:** This is the single most contested gap. The vendor's `Sanctions` tab catches state/federal **disciplinary** actions, but NPDB's primary content is **medical malpractice claims and payments**, plus **clinical privilege actions**, **DEA actions**, **civil judgments**, and **peer review actions**.

> 🟥 **Per §5 of `Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md`, the vendor sample does NOT cover NPDB's core malpractice content.** If the vendor claims they can replace NPDB, they must commit to providing these fields. Otherwise IBX **continues NPDB integration as-is**, and the vendor remains a corroboration-only supplement.

**Fields required (one record per adverse-action / claim):**

| Field name | Type | Source attribution | NPDB report category mapped |
|---|---|---|---|
| Event Type | Picklist (Medical Malpractice Payment, State Licensure Action, Clinical Privileges Action, Professional Society Action, DEA/Federal Action, Federal Exclusion, Criminal Conviction, Civil Judgment, Government Admin Action, CMS/Medicaid Exclusion, Peer Review Action, Voluntary License Surrender While Under Investigation) | NPDB / source | All NPDB categories |
| Event Date | Date | Date the underlying act occurred | All |
| Action / Settlement Date | Date | Date of payment / action taken | All |
| Reporting Entity | Text(255) | Hospital / state board / federal agency / insurance carrier | All |
| Reporting Entity Type | Picklist (Hospital, State Board, Federal Agency, Insurance Carrier, Court, PRO) | | All |
| Action Type Code | Picklist (Vendor codification of NPDB action codes) | NPDB Code Lists 1–4 | All |
| Action Type Description | Text(255) | Free-text from source | All |
| Payment Amount | Currency | Settlement / judgment amount | Malpractice payment |
| Payment Type | Picklist (Settlement, Judgment, Arbitration Award, Other) | | Malpractice payment |
| Allegations | Text Area(4000) | Narrative of allegations | Malpractice payment |
| Severity Code | Picklist (NPDB severity 1–9) | | Malpractice payment |
| Outcome Code | Picklist (NPDB outcome codes) | | Malpractice payment |
| Practitioner Role in Action | Picklist (Sole Defendant, Co-Defendant, Released, Dismissed) | | Malpractice payment |
| State of Action | Picklist (state code) | | All |
| DCN / NPDB Report ID | Text(40) | If sourced from NPDB | All |
| Source Verified On | Datetime | NCQA audit | All |
| Verification Source | Text(64) | "NPDB Continuous Query" / "Court Records" / "State Board" / etc. | All |

### 3.11 Disclosure Questions (Provider-Attested Yes/No Answers)

**Why it matters:** The `DisclosureQuestionsStep` (`PRM_PSVSubOsWSNPDB`) captures the practitioner's **own attested answers** to ~23 NCQA yes/no disclosure questions. The vendor's objective public-record data (Offenses, Sanctions) provides **corroboration** but **cannot replace** the attested answers.

> **Vendor cannot fully provide these.** They are by definition attestation artifacts. We list them here only so the vendor understands the gap.

| Disclosure question (NCQA standard) | Vendor corroboration available? |
|---|---|
| Have you ever been denied/restricted hospital privileges? | ~ (Affiliations lifecycle could indirectly signal) |
| Have you ever had hospital privileges suspended/surrendered? | ~ |
| Have you ever been convicted of a felony? | ✓ (`Offenses` tab) |
| Have you ever been the subject of a federal/state license action? | ✓ (`Sanctions` tab) |
| Have you ever surrendered a DEA registration? | 🔴 (vendor doesn't ship DEA today) |
| Have you ever been denied/cancelled malpractice insurance? | 🔴 (vendor doesn't ship insurance today) |
| Have you ever been excluded from Medicare/Medicaid? | ✓ (SUMMARY → MEDICARE EXCLUSIONS) |
| Have you ever been the subject of an NPDB report? | 🔴 (vendor doesn't ship malpractice claims) |
| Have you ever been the subject of a peer review action? | 🔴 |
| Have you ever been the subject of a sanction by a professional society? | 🔴 |
| Pending malpractice actions? | 🔴 |
| Physical / mental impairment affecting ability to practice? | — Provider-only |
| Substance use affecting practice? | — Provider-only |
| Loss of professional liability coverage in past 5 years? | 🔴 |
| (~10 more standard NCQA disclosures) | varied |

**Action for the vendor:** No new fields, but please confirm in writing that these are out of scope so IBX retains CAQH for the attestation artifact.

### 3.12 Mailing Address, Fax, ZIP+4 (PDM directory needs)

**Why it matters:** PDM (`PRM_PDMManualUpdate`) and the provider directory need mailing addresses and fax numbers. The vendor's `Addresses` tab only ships PRACTICE and BILLING types in the sample.

**Fields to ADD to existing Addresses tab:**

| Field name | Type | Source attribution | IBX maps to |
|---|---|---|---|
| Address Type — Mailing | Picklist value | Vendor must include MAILING in the `ADDRESSTYPE` enum | `Address.PRM_AddressType__c = 'Mailing'` |
| Fax | Phone(40) | Source: provider attestation / directory | `Address.PRM_Fax__c` / `Account.Fax` |
| ZIP+4 | Text(4) | USPS standardization | `Address.PRM_Zip4__c` |
| Phone Extension | Text(5) | If applicable | `Address.PRM_PhoneExtension__c` |
| Provider Email (primary work email) | Email | Source: provider attestation | `Contact.Email` / `Account.PersonEmail` |
| Provider Mobile Phone | Phone(40) | Source: provider attestation | `Account.PersonMobilePhone` |
| Office Email | Email | Practice-level email | `HealthcareFacility.PRM_OfficeEmail__c` |
| Website URL | URL | Practice website | `HealthcareFacility.PRM_WebsiteAddress__c` |

### 3.13 Languages Spoken + Cultural / Demographic Identity (Directory)

**Why it matters:** Member-facing directory shows languages spoken, ethnicity, pronouns, accepting-new-patients status. Today this comes from CAQH attestation only.

**Fields required (vendor may or may not have these — confirm):**

| Field name | Type | IBX maps to |
|---|---|---|
| Languages Spoken | Multi-Picklist (ISO language codes — IBX has ~1000-value picklist) | `PersonLanguage.Language` |
| Speaking Proficiency | Picklist (Fluent, Intermediate, Beginner) | `PersonLanguage.SpeakingProficiencyLevel` |
| Writing Proficiency | Picklist (Distinguished, Superior, Advanced, Intermediate, Novice) | `PersonLanguage.WritingProficiencyLevel` |
| Personal Pronoun | Picklist (He/Him, She/Her, They/Them, Ze/Zim, Ey/Em, Not Listed) | `ContactProfile.PRM_PersonalPronoun__c` |
| Hispanic / Latino | Picklist (Hispanic/Latino, Non-Hispanic/Non-Latino, Unknown) | `ContactProfile.PRM_HispanicLatino__c` |
| Hispanic Origin | Picklist (40+ values) | `ContactProfile.PRM_HispanicOrigin__c` |
| Race | Multi-Picklist (7 categories) | `ContactProfile.Race` |
| Ethnicity | Picklist (multi-select from IBX ethnicity dictionary) | `ContactProfile.PRM_Ethnicity__c` |
| Gender Identity | Picklist (M, F, U, Non-Binary, Prefer Not to Share) | `Contact.GenderIdentity` |

### 3.14 Patient Acceptance / Service-Area Constraints

**Why it matters:** `ServiceAreaVerificationStep` captures patient age min/max and accepting-new-patients status. CAQH-only today.

| Field name | Type | IBX maps to |
|---|---|---|
| Accepting New Patients | Picklist (Open to New, Open to Existing Only, Closed to All) | `HealthcareFacilityNetwork.PanelStatus` |
| Patient Age Minimum | Number | `HealthcareFacility.PRM_AgeMin__c` |
| Patient Age Min Unit | Picklist (Months, Years) | `HealthcareFacility.PRM_AgeMinUnit__c` |
| Patient Age Maximum | Number | `HealthcareFacility.PRM_AgeMax__c` |
| Patient Age Max Unit | Picklist (Months, Years) | `HealthcareFacility.PRM_AgeMaxUnit__c` |
| Gender Restriction | Picklist (Male, Female, None) | `HealthcarePractitionerFacility.GenderRestriction` |
| Provider Role at Location | Picklist (PCP, Specialist, Dual) | `HealthcarePractitionerFacility.PRM_PractitionerRole__c` |
| E-Prescribe Enabled | Boolean | `HealthcarePractitionerFacility.PRM_ERX__c` |

### 3.15 Identity Verification — Unmasked DOB and SSN (Last-4)

**Why it matters:** Vendor's sample masks DOB and SSN. NCQA cred requires identity verification against DOB; PDM needs SSN-last-4 for downstream matching.

| Field name | Type | Sample value (masked) | Required production value |
|---|---|---|---|
| DOB | Date | "XX-XX-1953" | Full date (under BAA) |
| SSN (last 4) | Text(4) | "XXX-XX-4505" | Last-4 only (under BAA) |
| SSN (full) | Text(9) | — | NOT required (avoid PHI scope creep) |

### 3.16 Facility-Specific Cred Fields (Ancillary)

**Why it matters:** `PRM_AncillaryPSVForm` verifies accreditation, services, staff. The vendor sample is practitioner-focused; we need facility-level fields for ancillary cred.

#### 3.16.1 Accreditation (per facility)

| Field name | Type | Source | IBX maps to |
|---|---|---|---|
| Accrediting Organization | Picklist (JCAHO, ACHC, AAAHC, ABCOP, CAP, DNV, ACR, NCQA, CARF, COA, AAASF, ADA, AABB, CHAP, NHPCO, AOA, IAC, etc.) | Accrediting body | `PRM_AncillaryAssessment__c.PRM_NameoftheAccreditingOrganization__c` |
| Accreditation Status | Picklist (Accredited, Provisional, Denied, Withdrawn, Revoked) | Accrediting body | (new) |
| Accreditation Effective Date | Date | Accrediting body | `PRM_AncillaryAssessment__c.PRM_AccreditationEffectiveDate__c` |
| Accreditation Expiration Date | Date | Accrediting body | `PRM_AncillaryAssessment__c.PRM_AccreditationExpirationDate__c` |
| Accreditation Scope / Service Type | Multi-Picklist (e.g. acute care, home health, hospice, etc.) | Accrediting body | (new) |
| Last Survey Date | Date | Accrediting body / CMS | `PRM_AncillaryAssessment__c.PRM_DateoflastCMSorStateSurvey__c` |
| Source Verified On | Datetime | NCQA audit | (new) |

#### 3.16.2 Facility CMS Certification (for hospitals / SNFs / etc.)

| Field name | Type | Source | IBX maps to |
|---|---|---|---|
| CMS Certification Number (CCN) | Text(10) | CMS (already in `Demographic.CCN`) | `Identifier` |
| CMS Quality Star Rating | Number | Medicare.gov | (net-new) |
| QCOR Inspection Findings | Text Area | qcor.cms.gov | (net-new) |
| Survey Deficiencies | Text Area | CMS / state survey | (net-new) |
| Licensed Bed Count | Number | State licensing | `HealthcareFacility.LicensedBedCount` |
| Medicare-Certified Bed Count | Number | CMS | `PRM_AncillaryAssessment__c.PRM_MedicareCertifiedBeds__c` |

#### 3.16.3 Facility Services Offered

The vendor likely cannot provide these — IBX collects them via the Ancillary Assessment OmniScript. Listed here for completeness; **vendor should explicitly confirm out-of-scope.**

### 3.17 CAQH Attestation Artifact (vendor cannot replace — flag for completeness)

`CAQHSignatureAttestionStep` requires:
- CAQH Provider Attestation ID
- CAQH Attestation Date (within 365 days)

These are CAQH-internal artifacts. **Vendor must confirm they are out of scope and IBX retains the CAQH attestation step regardless of vendor adoption.**

---

## 4. Required Metadata on EVERY Vendor Record (NCQA Compliance)

Independent of any single tab, NCQA Primary-Source Verification standards require source attribution and timestamps. **The vendor must commit to including these metadata fields on every record across every tab.**

| Field name | Type | Why required |
|---|---|---|
| Source Authority Name | Text(255) | NCQA primary-source identification (e.g. "PA State Board of Medicine", "DEA", "ABMS", "AMA Profiles", "NPPES", "NPDB", "OIG", "SAM.gov", "FSMB") |
| Source Authority URL | URL | If applicable (auditable click-through reference) |
| Source Verified On Timestamp | Datetime | Date/time vendor pulled / verified this field |
| Vendor Internal Confidence Score | Number 0–100 | If vendor uses one |
| Field-Level Refresh Cadence | Picklist (Real-time, Daily, Weekly, Monthly, Quarterly, Annual, On-Demand) | NCQA expects ≤ quarterly for sanctions/exclusions; weekly for licensure ideal |
| Data Provenance Chain | Text | If vendor sources from another aggregator (e.g. CAQH licensee), document the chain |
| Last Successful Refresh | Datetime | Most recent successful pull from source |
| Last Failed Refresh + Reason | Datetime + Text | If a source was unreachable |

---

## 5. Open Questions / Contractual Asks for the Vendor

Below the data-field asks, IBX needs the vendor to commit on the following operational items before integration design begins:

| # | Question / Ask | Why it matters |
|---|---|---|
| 1 | Will you ship **unmasked DOB and last-4 SSN** under a BAA? | NCQA identity verification |
| 2 | Confirm **Tax ID / EIN at provider AND group level** is in scope (the single biggest blocker for PDM) | PDM bundle / billing linkage |
| 3 | Confirm whether DEA, CDS, board certification, education, work history, malpractice insurance are in the full feed even though absent from this sample. **Request a richer sample (or an extended schema) for evaluation.** | Determines whether this is a CAQH replacement or supplement |
| 4 | **Field-level source attribution + "verified on" timestamp** per row (per §4 above). Is the vendor able to ship these as metadata columns? | NCQA primary-source compliance |
| 5 | **Refresh frequency** SLAs by field category — sanctions, exclusions, license status, NPI status, demographics, board cert, DEA. Daily for sanctions ideal; quarterly minimum NCQA. | Cred surveillance + re-cred cycle |
| 6 | Coverage match rate against IBX's full PA/NJ/DE participating-provider population (target ~40k+ practitioners + 5k+ facilities) | Sample is 150 from 3 hospitals — confirm production coverage |
| 7 | API / delivery contract: **delta payloads**, **per-NPI on-demand**, **bulk batch** — which consumption modes are supported, and at what limits? | Drives integration architecture vs. existing `PRM_CAQH_API` pattern |
| 8 | NCQA / URAC delegated credentialing recognition — is the vendor a delegated source for any health plan today? | Determines whether vendor data can stand alone for NCQA audit |
| 9 | **Continuous Query** subscription model — push notifications for new sanctions/exclusions within X hours? | Real-time cred surveillance |
| 10 | **NPDB-equivalent malpractice claim records** — yes/no, and if yes, what data source? | Determines whether vendor supplements NPDB beyond sanctions |
| 11 | Mailing address type, Fax, ZIP+4 in full feed? | PDM directory |
| 12 | **License class** (MD/DO/CRNP/PA-C/etc.) in full feed? | `VerifyLicense` step |
| 13 | **License disciplinary detail** at license-record level (beyond Sanctions tab)? | Drives auto-pend behavior |
| 14 | **Hospital affiliations lifecycle** (start/end dates, staff category, privilege status) in full feed? | `AdmittingPrivileges` step |
| 15 | **Languages spoken / pronouns / ethnicity / gender identity** — are these in the full feed or vendor-out-of-scope? | Provider directory |
| 16 | **Accreditation** (JCAHO/ACHC/AAAHC/etc.) — facility-level coverage in full feed? | Ancillary PSV `VerifyAccreditation` step |

---

## 6. How to Read the Companion CSV

Alongside this Markdown, IBX is providing `IBX_Vendor_DataDictionary_Request_v1.csv` — a flat file the vendor can fill in inline. Columns:

| CSV column | Description |
|---|---|
| `Section` | §3.1 through §3.16 (which gap area) |
| `PSV Step` | Which IBX verification step needs this field |
| `Field Name` | Human-readable field label |
| `Type` | Salesforce type or equivalent |
| `Required for NCQA?` | Yes / No / Recommended |
| `Vendor — In Sample?` | Yes / No / Partial — pre-filled by IBX |
| `Vendor — In Full Feed?` | **Vendor fills in: Yes / No / Future / Won't Support** |
| `Vendor — Source Authority` | **Vendor fills in: where they source it from** |
| `Vendor — Refresh Cadence` | **Vendor fills in: Daily / Weekly / Monthly / Quarterly / Real-time** |
| `Vendor — Comments` | **Vendor fills in any caveats** |
| `IBX Maps To` | Target IBX object.field |

---

## 7. Summary Scoreboard (one-pager for executive review)

| Domain | # required fields | # vendor has today | # net-new asks | Action |
|---|---|---|---|---|
| Tax ID / EIN | 8 | 0 | 8 | ⛔ Add — blocking |
| DEA | 8 | 0 | 8 | ⛔ Add — blocking |
| CDS | 6 | 0 | 6 | ⛔ Add — blocking |
| Enhanced License | 11 | 5 | 6 | ⛔ Add |
| Board Certifications | 13 | 0 | 13 | ⛔ Add |
| Education | 14 | 0 | 14 | ⛔ Add |
| Work History | 14 | 0 | 14 | ⛔ Add |
| Malpractice Insurance | 14 | 0 | 14 | ⛔ Add |
| Hospital Affiliations | 13 | 5 | 8 | ⛔ Add |
| NPDB Malpractice Claims | 16 | 0 | 16 | ⛔ Add or accept gap |
| Mailing/Fax/Email/ZIP+4 | 8 | 1 | 7 | ⚠️ Add |
| Languages/Pronouns/Ethnicity | 9 | 0 | 9 | ⚠️ Add |
| Patient Acceptance | 8 | 0 | 8 | ⚠️ Add |
| Identity (DOB/SSN unmasked) | 3 | 0 (masked) | 3 | ⚠️ Unmask under BAA |
| Facility Accreditation | 7 | 0 | 7 | ⚠️ Add for ancillary cred |
| NCQA metadata (per record) | 8 | 0 | 8 | ⛔ Add — compliance |
| **TOTAL net-new fields requested** | — | — | **~149** | — |

If the vendor can commit to **at least Tax ID, DEA, CDS, Board Cert, Education, Work History, Malpractice Insurance, Hospital-Affiliations-lifecycle, and NCQA per-record metadata**, this becomes a real CAQH-replacement candidate. Without those, it remains a high-value supplement (sanctions / license surveillance / MIPS / Star / Sunshine) — but **not** a CAQH replacement.

---

## Appendix A — Source artifacts inspected

- **Vendor sample:** `/Users/pkothapalli/Downloads/IBX_Sample_PI_Dataset_04_29_2026.xlsx` (11 tabs)
- **IBC Data Dictionary:** `/Users/pkothapalli/Downloads/IBC PNM Data Dictionary V5.6 WIP.xlsx` (72 tabs)
- **Salesforce objects referenced (IBX PIE data model):** Account, Address, BoardCertification, BusinessLicense, CareTaxonomy, Contact, ContactProfile, HealthcareFacility, HealthcareFacilityNetwork, HealthcarePractitionerFacility, HealthcareProvider, HealthcareProviderNpi, HealthcareProviderTaxonomy, Identifier, PersonEducation, PersonLanguage, PRM_AncillaryAssessment__c, PRM_AdverseActionLog__c, PRM_AdverseActionReview__c, PRM_ContactMethod__c, PRM_ProviderFeature__c.
- **OmniScripts (PSV flows):**
  - `PRM_PrimarySourceVerificationReview_English_50.os-meta.xml`
  - `PRM_PSVSubOsTxnyRole_English_5.os-meta.xml`
  - `PRM_PSVSubOsWSNPDB_English_6.os-meta.xml`
  - `PRM_PSVSubOsSummary_English_6.os-meta.xml`
  - `PRM_AncillaryPSVForm_English_10.os-meta.xml`
  - `PRM_AncillaryReassessmentPSV_English_8.os-meta.xml`
- **Companion analyses:**
  - `requirements/vendor/Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md`
  - `requirements/vendor/Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md`

## Appendix B — Glossary of acronyms

| Acronym | Meaning |
|---|---|
| ABMS | American Board of Medical Specialties |
| AOA | American Osteopathic Association |
| BAA | Business Associate Agreement (HIPAA) |
| BSPA | Blue Shield Provider Account (IBX legacy) |
| CAQH | Council for Affordable Quality Healthcare |
| CCN | CMS Certification Number |
| CDS | Controlled Dangerous Substances license (state-level controlled-substance license) |
| COI | Certificate of Insurance |
| DEA | Drug Enforcement Administration |
| EIN | Employer Identification Number (= Tax ID) |
| FSMB | Federation of State Medical Boards |
| HFN | HealthcareFacilityNetwork (IBX object) |
| MDR | Medical Director Review |
| MIPS | Merit-based Incentive Payment System (CMS) |
| MOC | Maintenance of Certification |
| NCQA | National Committee for Quality Assurance |
| NPDB | National Practitioner Data Bank |
| NPI | National Provider Identifier |
| NPPES | National Plan & Provider Enumeration System |
| OIG | Office of Inspector General (HHS) |
| PAR | Provider Application Request (IBX) |
| PDM | Provider Data Management |
| PIE | Provider Information Exchange (IBX's Salesforce platform) |
| PSV | Primary Source Verification |
| SAM | System for Award Management (gsa.gov) |
| URAC | Utilization Review Accreditation Commission |
