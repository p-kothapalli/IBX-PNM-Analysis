# IBX — App Review / PSV / QC Review Field Inventory

**Companion to:** `IBX_AppReview_PSV_QC_FieldInventory_v1.xlsx`
**Date:** 2026-05-13 (revised — added Data Source attribution)
**Owner:** Provider Credentialing / Data Strategy

---

## Why this workbook exists

The vendor has offered to replace IBX's CAQH-based primary-source-verification feed. To validate that claim we have to be very precise about **exactly which data values the credentialing/PDM business sees and acts on** during the three review steps that touch every initial-cred application:

1. **App Review** — first reviewer pass against CAQH-loaded application data.
2. **PSV** (Primary Source Verification) — formal source verification (License board, DEA, NPDB, education institution, etc.) with optional ancillary-facility step.
3. **QC Review** — quality-control second-set-of-eyes prior to network committee / approval.

This workbook lists **every input or display element on every screen** of those three flows, classifies each as either *source-of-truth* (vendor must provide) or *IBX-internal* (reviewer decision/note — vendor should NOT touch), and crosswalks the source list against the vendor's existing sample so we can hand them a clean delta.

---

## What's new in this revision

Added **Data Source Today** attribution to every source-of-truth field so the vendor knows whether each value comes from:

| Source | Today's flow |
|---|---|
| **CAQH** | Fetched via the CAQH ProView SOAP/REST API (`PRMDRTransformCAQHData`, `PRMCAQHReviewTransform`, `PRMTransformCAQHPSVReview`, `PRM_ValidateCAQHAppReview_Procedure`). |
| **PAR Form** | Captured directly from the practitioner on `PRM_PractitionerParticipationForm_English_112`. |
| **Salesforce (Internal)** | Read back from Salesforce records (`BoardCertification`, `BusinessLicense`, `Identifier`, `HCPFacility`, `AdmittingPrivileges`, `Taxonomy`) that were originally populated by CAQH, the PAR form, or manual cred-team entry. The NoCAQH DataRaptors (`PRMTransAppReviewNoCAQHDetails`, `PRMTransPSVNOCAQHData`, `PRMTransQCDataNoCAQH`) cover this path. |
| **External** | CMS state-survey data or accreditation-body lookups (JCAHO / AAAHC / ACHC) — outside CAQH. |

A new **Vendor Action** column converts source + domain into a directive (`VENDOR MUST PROVIDE` / `VENDOR PROVIDES` / `PAR FORM CONTINUES` / `MIXED`). Even where "Salesforce (Internal)" is the immediate source, the underlying data still originated from CAQH for all cred domains (License, DEA, CDS, Board Cert, Education, Work History, Hospital Privileges, Disclosure) — so the vendor must replicate.

### Source attribution at a glance

| Primary Data Source Today | Raw Rows | Unique Field Labels |
|---|---:|---:|
| CAQH | 59 | 15 |
| PAR Form | 34 | 8 |
| Salesforce (Internal) | 113 | 20 |
| External (CMS / State Survey) | 1 | 1 |
| External (JCAHO / AAAHC / ACHC) | 1 | 1 |
| **Total source-of-truth rows** | **208** | **46 unique labels** |

### Vendor Action breakdown (deduped per label)

| Vendor Action | # Unique Labels |
|---|---:|
| **VENDOR MUST PROVIDE** (License, DEA, CDS, Board Cert, Education, Work History, Hospital Privileges, Insurance, Facility Accreditation, Disclosure responses) | **32** |
| VENDOR PROVIDES primary taxonomy; additional specialties stay on PAR form | 4 |
| VENDOR PROVIDES practice address + phone; PAR form captures group contact email | 3 |
| **PAR FORM CONTINUES** (Hispanic origin, pronouns, languages spoken) | **3** |
| VENDOR PROVIDES DOB/SSN under BAA (unmasked); age range stays on PAR form | 2 |
| VENDOR PROVIDES (institution names etc.); name from NPI/PAR also acceptable | 2 |

**Bottom line:** of the 46 unique source-of-truth field labels the business validates across App Review/PSV/QC, **41 require the vendor to provide the data** (either replacing CAQH directly or via the SF read-back path that was originally loaded from CAQH). The remaining **5** stay on the PAR form (cultural identity self-attestation + age-range unit pickers).

---

## What was parsed

The workbook is derived directly from the active OmniScript metadata in this repo (no scraping, no manual notes):

| Bucket | OmniScript (active version) | Role |
|--------|------------------------------|------|
| App Review | `PRM_InitialCredentialAppReview_English_29` | Wrapper |
| App Review | `PRM_CredApplicationReviewSubOS_English_4` | Main verification screens |
| App Review | `PRM_CredApplicationReviewOSTxnyRole_English_3` | Taxonomy/role tab |
| App Review | `PRM_CredentialAppReviewCompleteOS_English_2` | Complete / submit |
| App Review | `PRM_CredentialAppReviewFileLoad_English_2` | File-load step |
| PSV | `PRM_PrimarySourceVerificationReview_English_50` | Wrapper |
| PSV | `PRM_PSVSubOsTxnyRole_English_5` | License / Taxonomy verification |
| PSV | `PRM_PSVSubOsWSNPDB_English_6` | Work history + NPDB verification |
| PSV | `PRM_PSVSubOsSummary_English_6` | MDR summary / sign-off |
| PSV | `PRM_AncillaryPSVForm_English_10` | Ancillary facility PSV |
| QC Review | `PRM_InitialCredPDAQC_English_15` | Initial-cred QC |
| QC Review | `PRM_RecredQC_English_12` | Re-cred QC |
| QC Review | `PRM_AncillaryQC_English_2` | Ancillary QC |

Total elements parsed: **666** across the 13 OmniScripts.

---

## How the workbook is laid out

| Sheet | Purpose |
|-------|---------|
| **Cover** | Quick orientation + file list |
| **Summary** | Per-bucket counts (Source / Internal / UI) + per-domain coverage matrix |
| **App Review** | Every component shown in any App-Review screen, with classification |
| **PSV** | Every component shown in any PSV screen (incl. all sub-OS), with classification |
| **QC Review** | Every component shown in any QC-Review screen, with classification |
| **Source Fields (Vendor Ask)** | DEDUPED unique source-of-truth field labels grouped by domain, with `Data Source Today (Primary)`, `Data Source Today (Full)`, and `Vendor Action`. **This is the list to send to the vendor.** |
| **IBX Internal (Skip)** | DEDUPED reviewer/decision/note fields the vendor should NOT populate |
| **All Fields Raw** | Every row from every flow (~666) with source attribution per row |

Colour key:
- 🟩 Green rows = Source-of-Truth (must come from vendor)
- 🟧 Orange rows = IBX-Internal (reviewer decision / note — do NOT ask vendor)
- ⬜ Grey rows = UI controls / static text (out of scope)

---

## Headline numbers

| Bucket | Source-of-Truth | IBX-Internal | UI / Other | Total |
|--------|----------------:|-------------:|-----------:|------:|
| App Review | 32 | 54 | 31 | 117 |
| PSV | 126 | 133 | 125 | 384 |
| QC Review | 50 | 57 | 58 | 165 |
| **TOTAL** | **208** | **244** | **214** | **666** |

After deduping on field label across all three flows:
- **46 unique source-of-truth field labels** the business actually sees and validates — these are the data values the vendor MUST be able to provide.
- **112 unique IBX-internal labels** — verification radios (Pass/Pend/Deny), reviewer notes, QC sign-offs, decision dates — these stay internal.

---

## Source-of-Truth fields, grouped by domain (with vendor coverage)

| Domain | # Unique Labels | Vendor Coverage Today | Action |
|--------|---------------:|-----------------------|--------|
| License (state board) | 7 | ⚠ Partial — class + disciplinary detail missing | **Expand** |
| Education | 7 | ✗ MISSING — full record needed | **Net-new ask** |
| Board Certifications | 8 | ✗ MISSING — full record needed | **Net-new ask** |
| Specialty / Taxonomy | 4 | ✓ Vendor has | Validate |
| Identity / Name | 2 | ✓ Vendor has | Validate |
| Disclosure Questions (CAQH attestation) | 2 | ✗ CAQH-only | **Re-collect via attestation flow** if CAQH retired |
| CDS / State Controlled-Substance | 1 | ✗ MISSING — full record needed | **Net-new ask** |
| DEA Registration | 1 | ✗ MISSING — full record needed | **Net-new ask** |
| Identity / Demographics | 2 | ⚠ DOB/SSN masked | **Unmask under BAA** |
| Work History | 3 | ✗ MISSING — full record needed | **Net-new ask** |
| Hospital Affiliations / Admitting Privileges | 2 | ⚠ Partial — lifecycle missing | **Expand** |
| Addresses / Contact / Directory | 3 | ⚠ Partial — Mailing/Fax/Email missing | **Expand** |
| Languages / Cultural / Directory | 3 | ✗ MISSING | **Net-new ask** |
| Facility Accreditation | 1 | ✗ MISSING — ancillary | **Net-new ask** |

> **Bottom line for the vendor:** of the 14 business domains the reviewer touches across App Review / PSV / QC Review:
> - ✓ 2 are already fully covered (Specialty/Taxonomy, Identity/Name)
> - ⚠ 4 are partially covered (License, Identity/Demographics, Hospital Affiliations, Addresses)
> - ✗ 8 are missing entirely (DEA, CDS, Board Cert, Education, Work History, Languages, Facility Accreditation, Disclosure attestations)

The **Source Fields (Vendor Ask)** sheet has the field-level detail the vendor needs to confirm for each.

---

## How this complements the earlier vendor data-dictionary request

| Deliverable | Angle |
|-------------|-------|
| `IBX_Vendor_DataDictionary_Request_v1.md` + `.csv` | Bottom-up — every Salesforce field the IBX schema persists, classified by PSV step and NCQA requirement. ~209 rows. Comprehensive technical contract. |
| **This workbook** (`IBX_AppReview_PSV_QC_FieldInventory_v1.xlsx`) | Top-down — every value the reviewer **sees and updates on screen** during the three review flows. ~46 unique source-of-truth labels. Business-validated. |

Send BOTH to the vendor. The CSV is the technical contract; the workbook is the screen-by-screen receipt that proves the contract reflects how reviewers actually use the data.

---

## Classification rules used (for transparency)

A field is classified **IBX-Internal** (do NOT ask vendor) if any of the following are true:

- Label or element name ends with `Verification`, `Review`, `Note`, `Notes`, `Verified On`, `Comment`, `Comments`, `Sign-Off`, or `Signature` (also catches misspellings `Verifcation`, `Verfication`).
- Element name begins with `Verify`, `MDR`, `QC`, `Correct`, `Override`, `Acknowledge`, `Is`, `Has`, `Recheck`, `Reload`, `Expedite`, `Suspect`, `PdaCheck`, `PsvCheck`.
- Label contains `Denial Reason`, `Pend Reason`, `Discrepancy`, `Decision`, `Disposition`, `Recommendation`, `Override`, `Acknowledge`, `Review Status`, `Approver`, `Approved Date`, `Outcome`, `Show in Directory`, `Covered Practice Locations`, `Site Visit Compliant?`, `Hospital Affiliations (Yes/No)`.
- File-upload components (NPDB report, signed attestation doc).

A field is classified **Source-of-Truth** (request from vendor) if it matches:
- Element name patterns for `License*`, `DEA*`, `CDS*`, `Board*`, `Education*`, `Taxonomy*`, `Address*`, `Phone*`, `Fax*`, `Email*`, `TaxId*`, `EIN*`, `SSN*`, `DOB*`, `Hospital*`, `Facility*`, `Carrier*`, `Insurance*`, `Specialty*`, `Work History*`, `Employer*`, `Accreditation*`, `Medicare Opt-Out*`, etc.
- Or label-keyword fallback (license, expiration, effective, issue date, education, degree, specialty, work history, etc.).
- Or step-context fallback (a generic `Status`/`Start Date`/`End Date` field inside a step named `Verify License` is classified to the License domain).

A field is **UI/Other** if it's a Text Block, an auto-named radio/checkbox with no useful label, or a UI action like `Add Record` / `Search Accounts` / `Do you want to add new Practice Location?`.

---

## Open questions for the vendor (asked alongside this workbook)

1. **Education:** can you provide degree, institution, start/end dates, completed flag, and primary degree indicator at the same recency NCQA requires (≤180 days for the verification, source ≤30 days old)?
2. **DEA / CDS:** can you provide the full registration record (number, state, schedule/class, effective/expiration, status) — not just an existence flag?
3. **Board Certifications:** can you provide ABMS/AOA cert type, original cert date, re-cert date, expiration, lifetime flag, board status text?
4. **Work History:** can you provide employer name, role, start/end dates, current-employer flag, with 5-year continuity?
5. **NPDB / Sanctions / Malpractice:** are you returning all NPDB report types (Adverse Action, Medical Malpractice, Exclusion, Judgment)? At what cadence?
6. **CAQH Disclosure Questions:** can you carry forward CAQH's 32+ self-attested disclosure responses and explanations, or do we re-collect at attestation?
7. **Demographics:** can DOB/SSN be unmasked under our BAA for entitled cred staff?
8. **Service Area:** can you provide Age Min/Max (with unit), Panel Status, Practitioner Role per practice location?
9. **Hospital Privileges:** can you provide privilege start/end, staff category (Active/Courtesy/etc.), and current vs. terminated status?
10. **Site Visit / State Survey:** can you supply state-survey date and compliance status for ancillary facilities?
