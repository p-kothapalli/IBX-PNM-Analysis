# Vendor "Provider Intelligence" Dataset — Cred & PDM Coverage Analysis

**Date:** 2026-05-05
**Vendor sample file:** `IBX_Sample_PI_Dataset_04_29_2026.xlsx` (150 NPI sample, sourced from Thomas Jefferson Hospital, Hospital of the University of Pennsylvania, Temple University Hospital — Main Campus)
**Audience:** IBX Cred + PDM business owners, vendor evaluation meeting
**Author:** Engineering analysis (Cursor agent, code-review-graph + omniscript inspection)
**Decision needed:** Whether the vendor feed can replace, supplement, or only marginally augment our existing CAQH + NPDB primary-source verification workflow.

---

## TL;DR — One-Paragraph Recommendation

**This vendor is a strong supplement to CAQH and a partial NPDB substitute. It cannot replace either.** The dataset can fully retire 4 of our 13 PSV verification steps (state-board click-throughs, OIG/SAM/CMS exclusions, NPI Registry click-through, Medicare opt-out). It can accelerate 5 more (license expiration monitoring, demographic refresh, hospital affiliation pre-fill, NPI deactivation alerts, sanctions surveillance). It adds 3 net-new signals we don't capture today (MIPS, CMS Star, Open Payments). However, it does **not** carry **malpractice claim history (the core of NPDB), DEA, CDS, board certifications, education, work history, malpractice insurance coverage, Tax ID/EIN, or CAQH attestation artifacts** — so cred and PDM continue to need both CAQH and NPDB. The missing **Tax ID** column is the single biggest blocker for PDM use; if the vendor cannot supply it in the full feed, this becomes a pure cred-supplement purchase, not a PDM solution.

---

## Document Map

1. [Vendor dataset inventory (all 11 tabs, every column)](#1-vendor-dataset-inventory)
2. [What our cred + PDM flows verify today](#2-what-our-cred--pdm-flows-verify-today)
3. [Tab-by-tab mapping to verification steps](#3-tab-by-tab-mapping-to-verification-steps)
4. [**Cannot-Replace summary — verification steps the vendor cannot retire**](#4-cannot-replace-summary)
5. [**NPDB-specific gap analysis — what is missing**](#5-npdb-specific-gap-analysis)
6. [Net-new signals the vendor adds](#6-net-new-signals-the-vendor-adds)
7. [Questions to ask the vendor](#7-questions-to-ask-the-vendor)
8. [Decision framework](#8-decision-framework)

---

## 1. Vendor Dataset Inventory

The workbook contains **11 tabs** with a 150-NPI sample.

### 1.1 SUMMARY tab — risk dashboard / scorecard

| Metric | Sample value | What it tells you |
|---|---|---|
| NPI (verified sample set) | 150 | Sample size |
| FEDERAL integrity flags | 0 (0%) | Federal exclusion hits |
| STATE integrity flags | 1 (0.7%) | State sanction hits |
| SUSPICIOUS OWNERSHIP | 4 (2.7%) | Open Payments / Sunshine flags |
| MAJOR RISK FLAGS | 1 (0.7%) | Vendor-internal severity bucket |
| MINOR RISK FLAGS | 0 | Vendor-internal severity bucket |
| DEACTIVATIONS | 0 | NPI deactivations |
| MEDICARE EXCLUSIONS | 0 | OIG-style exclusions |
| MIPS SCORES <2 | 0 | CMS quality outliers |
| CMS STAR RATINGS <2 | 17 (11.3%) | CMS quality outliers |

**Use case:** Triage / queue prioritization. Not a primary-source verification artifact.

### 1.2 Demographic tab (1,794 rows × 21 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1003025461 | Primary key |
| 2 | FULLNAME | GARFIELD,JAMIE | |
| 3 | FIRSTNAME | JAMIE | |
| 4 | MIDDLENAME | L | |
| 5 | LASTNAME | GARFIELD | |
| 6 | TITLE | MD | |
| 7 | ORGANIZATIONNAME | (null for individual) | |
| 8 | OTHERBUSINESSNAME | (null for individual) | |
| 9 | ENTITYTYPE | Individual | |
| 10 | ENTITYTYPECODE | 1 | NPPES code (1=Individual, 2=Org) |
| 11 | AUTHORIZEDOFFICIALCONTACTNAME | (null for individual) | |
| 12 | AUTHORIZEDOFFICIALCONTACTTITLE | (null for individual) | |
| 13 | AUTHORIZED_OFFICIAL_PHONE_NUM | (null for individual) | |
| 14 | **SSN** | XXX-XX-4505 | **MASKED in sample — confirm production behavior** |
| 15 | **DOB** | XX-XX-1953 | **MASKED in sample — confirm production behavior** |
| 16 | NPI_ENUMERATIONDATE | 2007-05-22 | Sourced from NPPES |
| 17 | NPIDEACTIVATIONDATE | (null) | NPPES |
| 18 | NPIREACTIVATIONDATE | (null) | NPPES |
| 19 | PRIMARYSPECIALITY | Physician-Internal Medicine | |
| 20 | CCN | (null for individual) | CMS Certification Number |
| 21 | MEDICARE_OPT_OUT | No | |

### 1.3 Addresses tab (5,093 rows × 12 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1003025461 | |
| 2 | ADDRESSTYPE | PRACTICE / BILLING | **MAILING type not seen in sample — confirm** |
| 3 | ADDR1 | 3401 N BRD ST | |
| 4 | ADDR2 | (often null) | |
| 5 | CITY | Philadelphia | |
| 6 | STATE | PA | |
| 7 | COUNTY | Philadelphia | |
| 8 | ZIP | 19140 | 5-digit |
| 9 | PHONE | 215-707-5864 | |
| 10 | UPDATEDATETIME | 2026-04-22 | Refresh timestamp |
| 11 | LATITUDE | 40.0000172 | |
| 12 | LONGITUDE | -75.1340379 | |

**Missing for PDM:** Fax, ZIP+4, addresses-of-mailing-type, and **Tax ID/EIN attached to address**.

### 1.4 Taxonomy tab (236 rows × 7 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1003234196 | |
| 2 | TAXONOMYGROUPING | Allopathic & Osteopathic Physicians | |
| 3 | SPECIALITY | Anesthesiology | |
| 4 | TAXONOMYCODE | 207L00000X | NUCC X12 code |
| 5 | LICENSENUMBER | MD465813 | |
| 6 | STATE | PA | |
| 7 | PRIMARYTAXONOMYFLAG | Y / N | |

### 1.5 Affiliations tab (267 rows × 7 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1003234196 | |
| 2 | FACILITYTYPE | HOSPITAL | Practitioner-to-facility relationship |
| 3 | FACILITYNAME | TEMPLE UNIVERSITY HOSPITAL | |
| 4 | ADDRESS | 3401 NORTH BRD ST | |
| 5 | CITY | PHILADELPHIA | |
| 6 | STATE | PA | |
| 7 | ZIPCODE | 19140 | |

**Missing for cred:** Affiliation start/end date, staff category, admitting status, temporary vs. unrestricted privileges flag, "who admits for you" delegation field, hospital record type.

### 1.6 Licenses tab (262 rows × 9 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1740724343 | |
| 2 | FIRSTNAME | MEGHANN | |
| 3 | MIDDLENAME | (null sometimes) | |
| 4 | LASTNAME | LEITNER | |
| 5 | LICENSENUMBER | OA004021 | |
| 6 | LICENSESTATE | PA | |
| 7 | LICENSEEFFECTIVEDATE | 2016-12-13 | |
| 8 | LICENSEEXPIRATIONDATE | 2026-10-31 | |
| 9 | ACTIVEFLAG | Active | |

**Missing for cred:** License class (MD/DO/CRNP/PA-C/etc.), disciplinary action detail at the license level, primary-source attribution (which state board did this come from?).

### 1.7 MIPS Score tab (313 rows × 8 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1700085214 | |
| 2 | REPORTEDYEAR | 2023 | |
| 3 | ORGPACID | 6204730955 | CMS PECOS PAC ID |
| 4 | FINALMIPSSCORE | 79.2781 | Composite |
| 5 | QUALITYSCORE | 79.2781 | |
| 6 | INTEROPERABILITYSCORE | 73.5769 | |
| 7 | IMPROVMENTSCORE | 100 | |
| 8 | COSTCATEGORYSCORE | 40 | |

**Use case:** Cred committee triage / quality oversight. Not currently captured in IBX cred flow — net-new.

### 1.8 CMS STAR tab (246 rows × 8 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1568558922 | |
| 2 | FIVESTARBENCHMARK | 100 | |
| 3 | INDPACID | 8820088644 | Individual PECOS PAC ID |
| 4 | MEASURETITLE | Diabetic Retinopathy: Communication With The Physician Managing Ongoing Diabetes Care | Measure-level |
| 5 | PATIENTCOUNT | 39 | |
| 6 | PERFORMANCERATING | 90 | |
| 7 | REPORTEDYEAR | 2023 | |
| 8 | STARVALUE | 4 | 1–5 |

**Use case:** Quality oversight, member-directory star indicator. Net-new.

### 1.9 Sanctions tab (2 rows × 5 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1467472175 | |
| 2 | SANCTIONAUTHORITY | Pennsylvania State Health Licensing Boards | |
| 3 | SANCTIONTYPECODE | 203 | Vendor-coded type |
| 4 | ACTIONDETAIL | Joseph R. Spiegel, License No. Md-033351-E … was ordered to pay a civil penalty of $250 (6-22-04) | Free-text narrative |
| 5 | EFFECTIVEDATE_MOD | 2004-07-15 | |

**Use case:** Replaces the OIG/SAM/CMS Preclusion click-through *for state and federal disciplinary sanctions only*. **Does not contain malpractice claims.**

### 1.10 Offenses tab (5 rows × 13 columns)

| # | Column | Sample value | Notes |
|--:|---|---|---|
| 1 | NPI | 1255505962 | |
| 2 | CRIMINALOFFENSE | Burglary Or Attempt; No Assault; Unarmed; Unoccupied Structure | |
| 3 | CRIMESEVERITY | 3 Felony | |
| 4 | CRIMINALCATEGORY | False | (vendor's own classification flag) |
| 5 | CONVICTDATE | (null sometimes) | |
| 6 | COURTCOUNTY | Desoto | |
| 7 | OFFENSELOCATION | Desoto | |
| 8 | CASEINFOCASENUMBER | 100445 | |
| 9 | CRIMEDATE | 2001-09-28 | |
| 10 | CRIMINALDESCRIPTION | (often null) | |
| 11 | COURTNAME | (often null) | |
| 12 | ARRESTDATE | (often null) | |
| 13 | CATEGORY_4L | Major | Severity bucket |

**Use case:** Background-check supplement. Useful for disclosure-question objective verification.

### 1.11 SuspiciousOwnership tab (82 rows × 18 columns)

CMS Open Payments / Sunshine Act payments to physicians:

| # | Column | Notes |
|--:|---|---|
| 1 | NPI | |
| 2-4 | RECIPIENTCITY / RECIPIENTSTATE / RECIPIENTZIPCODE | |
| 5-6 | PHYSICIANSPECIALTY / PHYSICIANLICENSESTATE | |
| 7-8 | APPLICABLEMANUFACTURERMAKINGPAYMENTNAME / STATE | |
| 9-11 | INDICATEDRUGORBIOLOGICALORDEVICEMEDICALSUPPLY / PRODUCTCATEGORYTHERAPEUTICAREA / NAMEOFDRUGBIOLOGICALDEVICEMEDICALSUPPLY | |
| 12 | INTERESTHELD | e.g. "Physician Covered Recipient" |
| 13-14 | INVESTMENTAMT / TOTALAMOUNTOFPMT | |
| 15 | DATEOFPAYMENT | |
| 16 | PROGRAMYEAR | |
| 17 | PAYMENTPUBLICATIONDATE | |
| 18 | CONTEXTOFRESEARCH | |

**Use case:** FWA/integrity flagging. Net-new — not captured in IBX today.

---

## 2. What Our Cred + PDM Flows Verify Today

There are **three flows** in scope.

### 2.A Practitioner PSV — `PRM_PrimarySourceVerificationReview` v50 (active)

The CAQH-driven flow for individual practitioners. The actual verification happens in three embedded Sub-OmniScripts:

| Sub-OS | Step | What is verified | Source today |
|---|---|---|---|
| `PRM_PSVSubOsTxnyRole` v5 | `CAQHSignatureAttestionStep` | Provider attested in CAQH (`AttestationDate`, `ProviderAttestID`) | **CAQH ProView** |
| | `ServiceAreaVerificationStep` | Practice address, city/state/zip/county, **Tax ID**, NPI, age min/max accepted | **CAQH ProView** |
| | `VerifyLicense` | License #, state, class, effective, expiration, status; duplicate-license check | **CAQH** + state medical boards (PA PALS, NJ DCA, DE DELPROS) |
| | `VerifySpecialty` | Specialty name, type, taxonomy primary flag | CAQH + internal taxonomy |
| | `VerifyPractitionerRole` | Care taxonomy + role | Internal |
| | `AdmittingPrivileges` | Hospital affiliation, type, dates, temporary/unrestricted flags | **CAQH** + hospital staff offices |
| | `CertificateofInsuranceVerification` | Malpractice carrier, type, policy #, occurrence/aggregate, dates | **CAQH** (insurance carrier docs) |
| `PRM_PSVSubOsWSNPDB` v6 | `WorkHistoryVerification` | Employer name, address, dates, current-employer flag | **CAQH** (provider self-reported) |
| | `EducationVerification` | Degree, institution, level, dates, status, completion | **CAQH** + institution verification |
| | `PatientStatus` | Patient type description | CAQH |
| | `DEAVerification` | DEA #, state, issue/expiration | **DEA database** (via CAQH) |
| | `CDSVerification` | State Controlled Dangerous Substances license | State CDS boards (via CAQH) |
| | `DisclosureQuestionsStep` | Yes/No malpractice/sanction disclosures + explanations | **CAQH attestation** |
| | `NPDBResults` | NPDB report attached/verified | **NPDB report (uploaded PDF)** |
| `PRM_PSVSubOsSummary` v6 | `BoardCertificationsStep` | Board name, original cert, recert, expiration | **AMA / AOA / specialty boards** (via CAQH) |
| | `VerifyMedicareOptOut` | Medicare opt-out yes/no | **CMS Medicare provider files** |
| | `VerifyLinks` | CMS Preclusion / FSMB / SAM | sam.gov, oig.hhs.gov, FSMB |
| | `PSVSummary` / `ReCredPSVSummary` | Aggregate Pass/Pend/Deny + MDR | Aggregator |
| | `MDRFormStep` | Medical Director Review (NPDB action, dates, amounts settled) | NPDB + manual |

### 2.B Ancillary PSV — `PRM_AncillaryPSVForm` v10 (active)

For ancillary facilities (no CAQH profile):

| Step | Source today |
|---|---|
| `VerifyAttestationSignature` | Provider attestation document |
| `ReviewPracticeLocation` | Internal |
| `NPDBScreen` | NPDB uploaded report |
| `VerifyInsurance` | Carrier docs |
| `VerifyCMSOIGSAM` | sam.gov, oig.hhs.gov, CMS Preclusion |
| `VerifyLicensure` | State agency portals (PALS / NJ DCA / DELPROS) + business-license LWC |
| `VerifyAccreditation` | JCAHO, ACHC, AAAHC, ABCOP, CAP, DNV, etc. |
| `VerifyCMS` | qcor.cms.gov, medicare.gov |
| `VerifyServices` | Internal SDS files |
| `VerifyTaxId` | NPI Registry click-through (npiregistry.cms.hhs.gov) |
| `ReviewScreen` | Aggregator |

### 2.C PDM — `PRM_PDMManualUpdate` and downstream consumers

Practice-location maintenance. Heavy reliance on the NPI ↔ Tax ID ↔ HFN bundle linkage. See `requirements/PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md`.

---

## 3. Tab-by-Tab Mapping to Verification Steps

Coverage rating: 🟢 fully covers · 🟡 partially covers · 🔴 doesn't cover · ⚪ not applicable.

### 3.1 Practitioner cred (CAQH-driven flow)

| PSV Sub-OS step | Field(s) needed | Vendor tab → column | Coverage | Notes |
|---|---|---|---|---|
| Demographics on Review screen | First/Middle/Last/Full, Title, NPI, DOB, Specialty | **Demographic**: FIRSTNAME / MIDDLENAME / LASTNAME / FULLNAME / TITLE / NPI / DOB / PRIMARYSPECIALITY | 🟡 | DOB and SSN are **masked** in sample; confirm unmasked in production under BAA. |
| `ServiceAreaVerificationStep` | Practice address line1/2, city, state, zip, county, **Tax ID**, NPI, age min/max | **Addresses**: ADDR1 / ADDR2 / CITY / STATE / COUNTY / ZIP + **Demographic**: NPI | 🟡 | **No Tax ID column anywhere.** Age-min/max is a CAQH-specific concept; not shipped. |
| `VerifyLicense` | License #, state, class, effective, expiration, status | **Licenses**: LICENSENUMBER / LICENSESTATE / LICENSEEFFECTIVEDATE / LICENSEEXPIRATIONDATE / ACTIVEFLAG | 🟢 | Strong replacement for the state-board click-throughs. **Missing**: license class (MD/DO/CRNP) and disciplinary detail. |
| `VerifySpecialty` / Taxonomy | Specialty, taxonomy code, primary flag | **Taxonomy**: SPECIALITY / TAXONOMYCODE / PRIMARYTAXONOMYFLAG / TAXONOMYGROUPING + **Demographic**: PRIMARYSPECIALITY | 🟢 | Direct hit — they ship the X12 taxonomy code. |
| `AdmittingPrivileges` | Hospital affiliation: name, address, type, dates, staff category, privileges status | **Affiliations**: FACILITYTYPE / FACILITYNAME / ADDRESS / CITY / STATE / ZIPCODE | 🟡 | Has the **affiliation** but missing: start/end dates, staff category, temporary/unrestricted flags, "who admits for you", admitting privileges status. |
| `CertificateofInsuranceVerification` | Carrier, policy #, type, coverage amounts, effective/end | — | 🔴 | **Not in this dataset.** |
| `WorkHistoryVerification` | Employer name, address, start/end, current-employer flag | — | 🔴 | **Not in this dataset.** |
| `EducationVerification` | Institution, degree, level, start/end, completion, status | — | 🔴 | **Not in this dataset.** |
| `DEAVerification` | DEA #, state, issue, expiration, status | — | 🔴 | **Not in this dataset.** |
| `CDSVerification` | State CDS #, state, effective, expiration | — | 🔴 | **Not in this dataset.** |
| `BoardCertificationsStep` | Board name, certification name, cert #, original, recert, expiration, type | — | 🔴 | **Not in this dataset.** No ABMS / AOA feed. |
| `DisclosureQuestionsStep` | Yes/No malpractice / loss-of-privileges / criminal disclosures + explanations | **Offenses** + **Sanctions** + **SuspiciousOwnership** | 🟡 | Provides **objective public-record facts**, not the provider's *answers*. Useful as a corroboration check. |
| `NPDBResults` | NPDB report (PDF), verified-on date, verified flag | **Sanctions** + **Offenses** + **SuspiciousOwnership** | 🟡 | Vendor data **overlaps but does not include malpractice claims** (the core NPDB content). See §5. |
| `VerifyLinks` → CMS Preclusion / OIG / SAM | Hit lists from those sites | **Sanctions** + SUMMARY → MEDICARE EXCLUSIONS, FEDERAL flags | 🟢 | Replaces three click-throughs with one API. |
| `VerifyMedicareOptOut` | Provider opt-out yes/no | **Demographic**: MEDICARE_OPT_OUT, CCN | 🟢 | Direct field. |
| Tax ID step → NPI Registry click-through | NPI valid + active | **Demographic**: NPI / NPI_ENUMERATIONDATE / NPIDEACTIVATIONDATE / NPIREACTIVATIONDATE | 🟢 | Replaces NPPES click-through and gives historical deactivation. |
| MDR / quality signals (not currently structured) | — | **MIPS Score** + **CMS STAR** | 🟢 (new) | Net-new value — not captured today. |
| CAQH attestation date / signature | `AttestationDate`, `ProviderAttestID` | — | 🔴 | CAQH-internal artifact — not replaceable. |
| ProviderEmail / languages spoken / pronouns / cultural identity / accepting new patients | (Review submit screen) | — | 🔴 | CAQH attestation-only fields. |

### 3.2 Ancillary cred (facility flow)

| Step | Vendor coverage | Notes |
|---|---|---|
| `VerifyTaxId` + NPI Verification | 🟡 | NPI ✓, **Tax ID ✗** |
| `VerifyLicensure` | 🟢 | If Licenses tab covers facility licenses too — confirm with vendor (sample is practitioners) |
| `VerifyAccreditation` (JCAHO/ACHC/etc.) | 🔴 | Not in dataset |
| `VerifyCMSOIGSAM` | 🟢 | SUMMARY + Sanctions covers this |
| `VerifyCMS` (QCOR / Medicare.gov) | 🟡 | MIPS + CMS STAR is provider-level, not facility-level QCOR |
| `VerifyInsurance` | 🔴 | Not in dataset |
| `VerifyServices` | 🔴 | Not in dataset |
| `NPDBScreen` | 🟡 | Vendor sanctions ≠ NPDB malpractice (see §5) |
| `VerifyAccreditation` site survey | 🔴 | Not in dataset |

### 3.3 PDM (Provider Data Management)

| PDM data point | Vendor coverage | Notes |
|---|---|---|
| Provider primary specialty / taxonomy | 🟢 Demographic + Taxonomy | |
| Practice / billing / mailing addresses | 🟡 Addresses tab | PRACTICE and BILLING types observed; **MAILING type not seen — confirm** |
| Phone / fax | 🟡 | Phone ✓, **fax ✗** |
| Group practice (Tax ID linkage) | 🔴 | **No Tax ID** — critical blocker for PDM. |
| Hospital affiliations for HFN setup | 🟢 Affiliations | Could pre-populate facility relationships |
| License renewal monitoring (re-cred trigger) | 🟢 Licenses (with expiration) | Could replace `PRM_ReCheckActiveCAQHValidtnScheduler` for license-only checks |
| NPI deactivation / reactivation | 🟢 Demographic | Proactive de-activation alerts |
| Capitated bundle / program participation | ⚪ Internal-only | Vendor does not / cannot help here |
| Lat/lng for service-area mapping | 🟢 Addresses | Net-new useful for member search radius |

---

## 4. Cannot-Replace Summary

> **The verification steps and data points the vendor cannot replace.**

This is the table the business needs to see most clearly. Every row here is a step or a data element that **must continue to be sourced from CAQH, NPDB, or the existing primary source** even if we adopt this vendor.

### 4.1 Verification steps that CANNOT be retired

| # | Verification step (where it lives) | Why vendor cannot replace it | Continued primary source |
|--:|---|---|---|
| 1 | `CAQHSignatureAttestionStep` (Practitioner PSV → `PRM_PSVSubOsTxnyRole`) | Vendor data is *factual*, not *attested*. NCQA cred standards require a provider attestation that the data is current, signed within 365 days. | **CAQH ProView attestation** |
| 2 | `WorkHistoryVerification` (`PRM_PSVSubOsWSNPDB`) | Vendor ships affiliations but **not employment history** with start/end dates and gaps. | **CAQH** (self-reported) + manual gap follow-up |
| 3 | `EducationVerification` (`PRM_PSVSubOsWSNPDB`) | No education / degree / institution / training data in the dataset. | **CAQH** + AMA Profiles + institution verification |
| 4 | `DEAVerification` (`PRM_PSVSubOsWSNPDB`) | No DEA registration data shipped (number, state, schedules, expiration). | **DEA database** (via CAQH or direct) |
| 5 | `CDSVerification` (`PRM_PSVSubOsWSNPDB`) | No state-CDS license data shipped. | **State CDS boards** |
| 6 | `DisclosureQuestionsStep` (`PRM_PSVSubOsWSNPDB`) | Vendor gives objective public records (criminal, sanctions, payments) but not the provider's *answers* to the ~23 yes/no NCQA disclosure questions. We still need the attested answers and explanations. | **CAQH attestation** (vendor data is corroboration only) |
| 7 | `NPDBResults` / `MDRFormStep` (`PRM_PSVSubOsWSNPDB` / `PRM_PSVSubOsSummary`) | Vendor data **does not include malpractice claims, payouts, hospital privilege denials, surrenders, or DEA voluntary surrenders** — these are NPDB's core. | **NPDB report** (uploaded) |
| 8 | `BoardCertificationsStep` (`PRM_PSVSubOsSummary`) | No ABMS / AOA / specialty board feed. No certification name, dates, type, recert, expiration. | **AMA Profiles / ABMS / AOA / specialty boards** |
| 9 | `CertificateofInsuranceVerification` (`PRM_PSVSubOsTxnyRole`) | No malpractice insurance carrier, policy, occurrence/aggregate amounts, or effective dates. | **CAQH** (insurance carrier COI documents) |
| 10 | `AdmittingPrivileges` lifecycle detail (`PRM_PSVSubOsTxnyRole`) | Vendor ships the affiliation, not the privileges. Missing start/end dates, staff category, temporary vs. unrestricted, status. | **CAQH** + hospital staff offices |
| 11 | `VerifyAccreditation` (Ancillary PSV — `PRM_AncillaryPSVForm`) | No accreditation status (JCAHO, ACHC, AAAHC, ABCOP, CAP, DNV, etc.). | **Accrediting bodies** directly |
| 12 | `VerifyInsurance` (Ancillary PSV) | Same as #9 but for facilities. | **Carrier COI** |
| 13 | `VerifyServices` (Ancillary PSV) | Internal SDS files; vendor cannot replace. | **Internal SDS** |
| 14 | `VerifyAttestationSignature` (Ancillary PSV) | Provider attestation document — same NCQA reasoning as #1. | **Uploaded attestation** |

### 4.2 Data fields that the vendor does NOT ship

These fields are required somewhere in cred or PDM and are missing from the sample. **If these exist in the vendor's full feed, they need to be confirmed in writing with a richer sample.**

| Field | Required by | Currently sourced from |
|---|---|---|
| **Tax ID / EIN (provider and group level)** | PDM bundles, billing/mailing flow, `ServiceAreaVerificationStep` | CAQH, internal HFN config |
| **DEA registration** (number, state, schedules, expiration, status) | `DEAVerification` step | DEA database via CAQH |
| **State CDS license** (number, state, effective, expiration) | `CDSVerification` step | State CDS boards via CAQH |
| **Board certifications** (board, cert #, type, original, recert, expiration, board-certified flag) | `BoardCertificationsStep` | AMA / ABMS / AOA via CAQH |
| **Education** (institution, degree, level, dates, status, completion) | `EducationVerification` | CAQH + institution |
| **Work history** (employer, address, start/end, current flag) | `WorkHistoryVerification` | CAQH |
| **Malpractice insurance** (carrier, policy, occurrence/aggregate, dates) | `CertificateofInsuranceVerification` | CAQH (carrier COI docs) |
| **Malpractice claims / NPDB content** | `NPDBResults`, `MDRFormStep` | NPDB report |
| **License class** (MD/DO/CRNP/PA-C, etc.) | `VerifyLicense` | State boards |
| **License disciplinary detail** | `VerifyLicense`, `VerifyLinks` | State boards, NPDB |
| **Hospital affiliation lifecycle** (start/end, staff category, privilege status, temp/unrestricted) | `AdmittingPrivileges` | Hospital staff offices |
| **Accreditation** (body, type, status, dates) | `VerifyAccreditation` | JCAHO/ACHC/etc. |
| **CAQH attestation artifact** (`AttestationDate`, `ProviderAttestID`) | `CAQHSignatureAttestionStep` | CAQH |
| **Disclosure question answers** (the 23 yes/no items) | `DisclosureQuestionsStep` | CAQH |
| **Languages spoken / pronouns / cultural identity / accepting new patients** | Review submit screen, provider directory | CAQH |
| **Provider email** | Review submit screen | CAQH |
| **Mailing addresses (vs. practice/billing)** | PDM mailing-address flow | CAQH, internal |
| **Fax numbers** | PDM, provider directory | CAQH, internal |
| **ZIP+4** | Address standardization, claims | Precisely API, CAQH |

### 4.3 Verification steps that CAN be retired or accelerated

| Step | Outcome with vendor adopted | Notes |
|---|---|---|
| `VerifyMedicareOptOut` (Practitioner PSV) | **Retire** | `Demographic.MEDICARE_OPT_OUT` is a direct replacement |
| `VerifyLinks` → CMS Preclusion / OIG / SAM (Practitioner PSV) | **Retire 3 click-throughs** | `Sanctions` + SUMMARY exclusion counts cover it |
| State-board click-throughs in `VerifyLicense` (PA PALS, NJ DCA, DE DELPROS) | **Retire click-through, keep manual review of class** | `Licenses` tab covers expiration, status, dates |
| NPI Registry click-through in `VerifyTaxId` (Ancillary) and elsewhere | **Retire** | `Demographic.NPI/NPI_ENUMERATIONDATE/NPIDEACTIVATIONDATE` covers |
| `VerifyCMSOIGSAM` (Ancillary PSV) | **Retire 3 click-throughs** | Same as above for ancillary |
| Re-cred license expiration sweep (`PRM_ReCheckActiveCAQHValidtnScheduler` license slice) | **Accelerate** | Vendor ships expiration date with active flag |
| Demographic refresh (PDM) | **Accelerate** | `Demographic` + `Addresses` tabs feed PDM |
| Hospital affiliation pre-fill (Practitioner PSV) | **Accelerate (pre-populate)** | Still need CAQH for privilege-status detail |
| NPI deactivation alerts (PDM) | **Accelerate (proactive)** | `NPIDEACTIVATIONDATE` |
| Sanctions surveillance (PDM / re-cred trigger) | **Accelerate (proactive)** | `Sanctions` continuous feed |

---

## 5. NPDB-Specific Gap Analysis

> **The single most important slide for the meeting.** NPDB is the federally-mandated source of truth for adverse actions against practitioners. This vendor does **not** replace it.

### 5.1 What NPDB contains

The National Practitioner Data Bank (HRSA / 42 CFR Part 60) publishes reports across these categories:

| NPDB report category | What it covers |
|---|---|
| **Medical malpractice payments** | Any payment for the benefit of a practitioner in settlement of, or in satisfaction in whole or in part of, a written claim or judgment |
| **State licensure actions** | License revocation, suspension, surrender, censure, reprimand, probation, voluntary surrender while under investigation |
| **Clinical privilege actions** | Hospital adverse actions: denial, revocation, restriction, suspension, surrender of clinical privileges (>30 days) |
| **Professional society actions** | Adverse membership actions by professional societies |
| **DEA / Federal licensure actions** | DEA registration revocation, suspension, restriction, surrender |
| **Federal exclusions (HHS-OIG, GSA/SAM)** | Exclusions from federal healthcare programs |
| **Federal/state criminal convictions** | Healthcare-related criminal convictions |
| **Civil judgments** | Healthcare-related civil judgments |
| **Government administrative actions** | Federal/state agency actions for healthcare-related civil/administrative offenses |
| **CMS/state Medicaid exclusions** | Termination from Medicare/Medicaid programs |
| **Peer review / accreditation actions** | Adverse actions reported by peer review organizations (PROs) and private accreditation entities |

### 5.2 What this vendor's dataset covers vs. NPDB

| NPDB report category | Vendor coverage | Vendor source | Verdict |
|---|---|---|---|
| Medical malpractice payments | 🔴 None | — | **Cannot replace NPDB** |
| State licensure actions (full disciplinary detail) | 🟡 Partial | `Sanctions` (free-text narrative, sanction type code) | Sample row 1 covers a PA Health Licensing Board civil penalty — vendor catches sanction-style actions but not all license disciplinary nuances |
| Clinical privilege actions (hospital privilege denial/revocation/restriction) | 🔴 None | — | **Cannot replace NPDB** |
| Professional society actions | 🔴 None | — | **Cannot replace NPDB** |
| DEA / federal licensure actions | 🔴 None | — | **Cannot replace NPDB** (vendor doesn't even ship DEA itself) |
| Federal exclusions (HHS-OIG, SAM, CMS Preclusion) | 🟢 Full | `Sanctions` + SUMMARY → FEDERAL/MEDICARE EXCLUSIONS | Vendor covers this — can replace OIG/SAM/CMS click-throughs |
| Federal / state criminal convictions | 🟡 Partial | `Offenses` (criminal records by court county) | Vendor sample is sparse (5 rows / 150 NPI). Not all healthcare-related criminal convictions may be captured. Confirm scope. |
| Civil judgments | 🔴 None | — | **Cannot replace NPDB** |
| Government administrative actions | 🟡 Partial | `Sanctions` | Some included; depth unclear |
| CMS / state Medicaid exclusions | 🟢 | SUMMARY → MEDICARE EXCLUSIONS | |
| Peer review / accreditation adverse actions | 🔴 None | — | **Cannot replace NPDB** |
| Open Payments / Sunshine Act | 🟢 (not part of NPDB) | `SuspiciousOwnership` | Net-new — NPDB doesn't carry this |

### 5.3 NPDB content the vendor is silent on

Even with the vendor adopted, **every cred case still needs an NPDB query** because the vendor does **not** ship:

1. **Medical malpractice claim and payment records** — the most-cited NPDB content. Required for `MDRFormStep` (MDR amounts, dates settled, NPDB action).
2. **Clinical privileges adverse actions** — denial, revocation, restriction, surrender of hospital privileges >30 days. NCQA-required.
3. **DEA / federal controlled-substance registration actions** — DEA surrenders, suspensions.
4. **Civil judgments** in healthcare matters.
5. **Peer review and accreditation organization actions** — adverse actions reported by hospitals' QA/PI/peer-review processes.
6. **Voluntary surrender of license while under investigation** — NPDB-specific reportable event.
7. **Practitioner identification verification** — the NPDB query result includes a "self-query" verification artifact that NCQA accepts as primary-source.
8. **Continuous Query subscription artifact** — IBX may use NPDB Continuous Query for ongoing monitoring; the audit trail of received reports is NPDB-specific.

### 5.4 Required action

- **Continue NPDB integration as-is.** No reduction in NPDB usage.
- The vendor `Sanctions` and `Offenses` tabs can act as **early-warning signals** between NPDB queries (e.g., flag a re-cred case for early review if a new sanction appears), but **cannot replace** the NPDB self-query at initial cred or re-cred.
- Update `NPDBResults` and `MDRFormStep` workflows to **also ingest** vendor sanctions/offenses as supplementary evidence, not as primary source.

---

## 6. Net-New Signals the Vendor Adds

These are capabilities IBX **does not have today** that the vendor brings:

| Signal | Vendor source | Use case |
|---|---|---|
| MIPS scores (Final, Quality, Interoperability, Improvement, Cost) | `MIPS Score` tab | Cred-committee triage; quality oversight |
| CMS Star measure-level rating | `CMS STAR` tab | Member-directory star indicator; quality oversight |
| Open Payments / Sunshine Act | `SuspiciousOwnership` tab | FWA/integrity flagging; conflict-of-interest review |
| NPI deactivation / reactivation lifecycle | `Demographic.NPIDEACTIVATIONDATE` / `NPIREACTIVATIONDATE` | Proactive directory cleanup; auto-suspend HFNs |
| Geocoded addresses (lat/lng) | `Addresses.LATITUDE` / `LONGITUDE` | Member-search radius; service-area accuracy |
| Aggregate per-NPI risk scorecard | `SUMMARY` tab pattern | Per-case triage flag for cred queue |
| Refresh timestamp on addresses | `Addresses.UPDATEDATETIME` | PDM data-currency auditability |

---

## 7. Questions to Ask the Vendor

| # | Question | Why it matters |
|--:|---|---|
| 1 | Will you ship **unmasked DOB and last-4 SSN** under a BAA, or only masked values? | NCQA cred requires identity verification against DOB |
| 2 | Do you carry **Tax ID / EIN at the individual provider and group level**? | Single biggest blocker for PDM use; sample shows none |
| 3 | Do you have **DEA, CDS, board certification, malpractice insurance, education, work history** in your full feed even though this sample omits them? Please send a richer sample. | Determines whether this is a CAQH replacement or supplement |
| 4 | What **source attribution and "verified on" timestamp at the field level** do you provide for NCQA primary-source verification audit? | NCQA primary-source standards require source identification |
| 5 | **Refresh frequency** for sanctions, license status, NPI status — daily, weekly, monthly? | Cred re-cycles every 36 months; we sweep continuously for adverse actions |
| 6 | Coverage in PA / NJ / DE for IBX's full participating-provider population (~40k+) — what's the match rate? | Sample is 150 from 3 hospitals only |
| 7 | Is the **Affiliations** tab limited to facility/address, or does the full feed include **start/end dates, staff category, privilege status**? | Determines whether `AdmittingPrivileges` step can be accelerated |
| 8 | Do you carry **mailing addresses** (not just practice/billing) and **fax**? | PDM directory data |
| 9 | NPDB-equivalent **malpractice claims** data — do you have it, and if so, from what source? | Determines whether this can ever supplement NPDB beyond sanctions |
| 10 | API contract: **delta payloads**, **per-NPI on-demand**, **bulk** — which is the intended consumption model? | Drives integration design relative to existing `PRM_CAQH_API` named credential pattern |
| 11 | What's your stance on **NCQA / URAC certification**? Are you a delegated credentialing source any health plan uses today? | Determines whether your data can stand alone for cred |
| 12 | Do you provide a **Continuous Query** style subscription where new sanctions/exclusions are pushed within X hours? | Real-time alerting for cred surveillance |
| 13 | **License class** (MD / DO / CRNP / PA-C / etc.) — is it in the full feed? | Required for `VerifyLicense` |
| 14 | **License disciplinary detail at the license-record level** — beyond the Sanctions tab, do you flag a license as "disciplinary action present"? | Drives auto-pend behavior |

---

## 8. Decision Framework

Use this matrix to set the buying decision based on vendor responses:

| Vendor answer profile | What it means | Recommended action |
|---|---|---|
| **No Tax ID, no DEA/CDS/board cert/education/work history/insurance, no malpractice claims** (i.e., the sample is the full feed) | Pure cred-supplement and PDM partial | **Modest investment.** Use for sanctions surveillance, license expiration monitoring, demographic refresh, MIPS/Star/Sunshine net-new. Do not retire CAQH or NPDB. PDM use limited (no Tax ID = no bundle work). |
| **Has DEA/CDS/board cert/education/work history/insurance, but no malpractice claims** | Could replace much of CAQH but never NPDB | **Moderate investment.** Possible CAQH alternative for re-cred maintenance flow. Initial cred still needs full CAQH + NPDB + provider attestation. |
| **Has all of the above + malpractice claim records (NPDB-equivalent)** | True dual-replacement candidate | **Strategic evaluation.** Requires legal review of NPDB compliance equivalence (HRSA does not certify alternatives). Even then, NPDB self-query is statutorily preferred for hospital privileging — health plans may have more flexibility. |
| **Has Tax ID at provider and group level** | Unlocks PDM use | **Add PDM use case to scope.** Vendor can drive billing-address freshness, bundle automation, and replace some CAQH-based PDM lookups. |
| **NCQA/URAC delegated cred recognition** | Can stand alone for cred sources | **Strategic.** Worth a deeper RFP. Few vendors meet this bar. |

### 8.1 Most likely outcome

Based on the sample shape, the most likely vendor profile is **Profile 1 (cred-supplement + partial PDM)**. In that case:

**Buy if:**
- Annual cost is justified by the value of (a) eliminating ~7 click-through verifications per cred case × volume, (b) proactive license/sanctions surveillance reducing manual re-cred prep time, (c) MIPS/Star/Sunshine signals for quality oversight.
- The vendor commits to an SLA for refresh frequency and field-level verified-on timestamps (NCQA primary-source compliance).

**Don't buy if:**
- The vendor cannot supply Tax ID and the business case depended on PDM use.
- The vendor cannot provide field-level source attribution for NCQA audit defensibility.
- Refresh frequency is monthly or worse for sanctions/exclusions (NCQA expects quarterly minimum, ideally weekly or continuous).

---

## Appendix A — Source artifacts inspected

- **Vendor file:** `/Users/pkothapalli/Downloads/IBX_Sample_PI_Dataset_04_29_2026.xlsx`
- **OmniScripts:**
  - `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_50.os-meta.xml` (Practitioner PSV — active)
  - `force-app/main/default/omniScripts/PRM_PSVSubOsTxnyRole_English_5.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_PSVSubOsWSNPDB_English_6.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_PSVSubOsSummary_English_6.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_AncillaryPSVForm_English_10.os-meta.xml` (Ancillary PSV — active)
  - `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml`
- **Apex:** `force-app/main/default/classes/PRM_CAQHValidationService.cls`, `PRM_CheckCAQHRecordInitHelper.cls`, `PRM_CheckCAQHDataHelper.cls`, `PRM_ReCheckActiveCAQHValidtnScheduler.cls`, `PRM_CaqhAuthController.cls`
- **Named credentials:** `force-app/main/default/namedCredentials/PRM_CAQH_API.namedCredential-meta.xml`
- **Related requirements:** `requirements/PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md`
