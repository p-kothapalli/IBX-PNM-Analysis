# CAQH Provider Roster Submission Guide

**Last Updated:** April 28, 2026 (v2 — updated after second exception batch)  
**Author:** IBX QA Team  
**Reference Spec:** CAQH Credentialing Roster Data Exchange Specification v3.2

---

## Overview

This guide documents the correct process for preparing and submitting a provider roster file to the CAQH Provider Data Portal. It was built iteratively from two exception batches received on April 28, 2026, and captures every known issue with the current Salesforce export format.

### Exception History

| Submission | File | Error | Records Failed | Status |
|---|---|---|---|---|
| 1st attempt | `6223_ProviderRoster_2026_04_28_09_43.txt` | File rejected — missing header row + state name format | All 93 | Layout failure |
| 2nd attempt | `6223_ProviderRoster_2026_04_28_09_43.txt` | `Add Failed: CAQH Provider ID not found/invalid` | All 93 | Wrong ID in CAQH_Provider_ID field |
| 3rd attempt | `6223_ProviderRoster_2026_04_28_10_05.txt` | `Required Field missing/invalid` — Practice State, Birthdate, Provider Type | All 93 | Missing required fields not in Salesforce export |

---

## Step 1 — Export the Roster from Salesforce

Export the provider roster report as a **CSV file**. The exported file will not have a header row and will contain raw data columns.

### Required Fields That Must Be in the Salesforce Report

> **The current Salesforce export is missing three required CAQH fields.** These must be added to the report before the roster can be submitted without exceptions.

| CAQH Field | Col # | Status in Current Export | Action Required |
|---|---|---|---|
| `Provider_Practice_State` | 16 | **Missing** | Add to Salesforce report — or derive from `Provider_License_State` (col 25) if the same state |
| `Provider_Birthdate` | 17 | **Missing** | Add practitioner date of birth to the Salesforce report (format: `YYYYMMDD`) |
| `Provider_Type` | 22 | **Missing** | Add CAQH provider type code to the Salesforce report (e.g., `MD`, `NP`, `PA`) — see reference table below |

Until these are included in the Salesforce report, every Add record will fail with:
```
Required Field missing/invalid: Provider Practice State
Required Field missing/invalid: Provider Birthdate
Required Field missing/invalid: Provider Type
```

---

## Step 2 — Convert to Pipe-Delimited TXT

CAQH requires a **pipe (`|`) delimited `.txt` file**, not a CSV. Use the following approach to convert:

```python
import csv

input_file  = 'YourRoster.csv'
output_file = 'YourRoster_piped.txt'

with open(input_file, 'r', newline='', encoding='utf-8-sig') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile, delimiter='|', quoting=csv.QUOTE_MINIMAL)
    for row in reader:
        writer.writerow(row)
```

> **Note:** The `utf-8-sig` encoding handles the BOM character (`\ufeff`) that Salesforce sometimes prepends to CSV exports.

---

## Step 3 — Add the Required Header Row

> **This is the #1 cause of the "incorrect layout" rejection error.**

CAQH requires the **first row** of every submission file to contain the exact column names listed below, in this exact order. The file will be rejected entirely if this row is missing.

The required header (35 columns, pipe-delimited):

```
Action_Flag|Provider_First_Name|Provider_Middle_Name|Provider_Last_Name|Provider_Name_Suffix|Provider_Gender|Provider_Address1|Provider_Address2|Provider_Address_City|Provider_Address_State|Provider_Address_Zip|Provider_Address_Zip_Extn|Provider_Phone|Provider_Fax|Provider_Email|Provider_Practice_State|Provider_Birthdate|Provider_SSN|Short_SSN|Provider_DEA|Provider_UPIN|Provider_Type|Provider_Tax_ID|Provider_NPI|Provider_License_State|Provider_License_Number|CAQH_Provider_ID|PO_Provider_ID|Last_Recredential_Date|Next_Recredential_Date|Delegation_Flag|Application_Type|Affiliation_flag|Organization_ID|Region_ID
```

---

## Step 4 — Fix `Provider_Address_State` (Field 10)

> **This is the #2 data issue found in the April 2026 submission.**

The Salesforce export populates `Provider_Address_State` (column 10) with the **full state name** (e.g., `New Jersey`, `Delaware`, `Pennsylvania`). CAQH requires the **2-character ANSI state code** (`NJ`, `DE`, `PA`).

Apply this mapping when preparing the file:

| Full State Name  | Required Code |
|-----------------|---------------|
| New Jersey      | NJ            |
| Delaware        | DE            |
| Pennsylvania    | PA            |
| *(all others)*  | *(standard 2-char ANSI code)* |

---

## Step 5 — Populate Missing Required Fields

> **This is the #4 issue — causes `Required Field missing/invalid` for all Add records.**

Three fields required for Initial Add (`A`) are not included in the current Salesforce report export. Until the report is fixed, these must be handled during file preparation.

### `Provider_Practice_State` (Field 16)

The primary practice state of the provider — **must be a 2-character ANSI state code**. In most cases this is the same state as `Provider_License_State` (field 25), which is already populated in the export.

**Short-term workaround:** Copy the value from `Provider_License_State` (col 25) into `Provider_Practice_State` (col 16).

**Long-term fix:** Add the practice state field to the Salesforce report.

### `Provider_Birthdate` (Field 17)

The provider's date of birth. **Format must be `YYYYMMDD`** (e.g., `19681204` for December 4, 1968).

**Action required:** This field cannot be derived from other data. The Salesforce report must be updated to include the practitioner's date of birth. There is no valid workaround.

### `Provider_Type` (Field 22)

The CAQH provider type abbreviation. **Must be a value from the CAQH standard list** (see reference table at the bottom of this document).

**Action required:** The Salesforce report must be updated to include the provider type mapped to the appropriate CAQH code. See the reference table below for valid values.

---

## Step 6 — Correct the `CAQH_Provider_ID` vs `PO_Provider_ID` Mapping

> **This is the #3 issue — it caused all 93 records to fail with `Add Failed: CAQH Provider ID not found/invalid`.**

### The Problem

The Salesforce export places the **internal IBX Provider ID** (e.g., `24500001`) in **field 27 (`CAQH_Provider_ID`)** and leaves **field 28 (`PO_Provider_ID`) empty**.

When a record has Action Flag = `A` (Add) and a value is present in `CAQH_Provider_ID`, CAQH treats it as a **Quick Add** — meaning it tries to look up that ID in their system. Since these are internal IBX IDs (not CAQH-assigned IDs), every lookup fails.

### The Fix

For **Action Flag = A (Initial Add)** records where we do not have a CAQH Provider ID:

- **Clear** `CAQH_Provider_ID` (field 27) — leave it empty
- **Move** the internal IBX ID to `PO_Provider_ID` (field 28)

CAQH will then process these as proper **Initial Adds**, using NPI and License Number to match providers in their system.

### Field Reference

| Field # | Column Name       | What to put here for Initial Add (A) |
|---------|-------------------|--------------------------------------|
| 27      | `CAQH_Provider_ID` | **Empty** (unless you have a valid CAQH-assigned ID) |
| 28      | `PO_Provider_ID`   | Your internal IBX Provider ID (e.g., `24500001`) |

> **Only populate `CAQH_Provider_ID` if you have a CAQH-assigned ID** (a 10-digit number issued by CAQH). This is required for Updates (`U`) and Deletes (`D`).

---

## Step 7 — Name the File Correctly

CAQH requires a specific file naming convention. The file name **must start with an underscore**:

```
_<POID>_ProviderRoster_YYYY_MM_DD_HH_MM.txt
```

**Example:** `_6223_ProviderRoster_2026_04_28_09_43.txt`

- `6223` is IBX's Organization ID (POID) assigned by CAQH
- Date/time should reflect when the file was generated
- File must be a `.txt` extension

> **Common mistake:** Omitting the leading underscore (`_`) will cause the file name to fail CAQH's naming validation.

---

## Step 8 — Final Validation Checklist

Before uploading, verify each item:

| # | Check | Expected | Issue Found In |
|---|-------|----------|----------------|
| 1 | File has a header row as the first line | Yes — 35 exact column names | 1st submission |
| 2 | File uses pipe (`\|`) delimiter | Yes | — |
| 3 | File extension | `.txt` | — |
| 4 | File name starts with `_<POID>_ProviderRoster_` | Yes | — |
| 5 | `Provider_Address_State` (col 10) uses 2-char code | `NJ`, `DE`, `PA` — not full names | 1st submission |
| 6 | `CAQH_Provider_ID` (col 27) is empty for Initial Adds | Yes — unless a real CAQH ID is known | 2nd submission |
| 7 | `PO_Provider_ID` (col 28) has the internal IBX ID | Yes | 2nd submission |
| 8 | `Provider_Practice_State` (col 16) is populated | 2-char state code (e.g., `NJ`) | 3rd submission |
| 9 | `Provider_Birthdate` (col 17) is populated | Format: `YYYYMMDD` | 3rd submission |
| 10 | `Provider_Type` (col 22) is populated | Valid CAQH code (e.g., `MD`, `NP`) | 3rd submission |
| 11 | `Action_Flag` (col 1) is `A`, `U`, or `D` only | Yes | — |
| 12 | `Organization_ID` (col 34) = `6223` | Yes | — |

---

## Required Fields by Action Flag

| Field | Initial Add (`A`) | Update (`U`) | Delete (`D`) |
|-------|--------------------|--------------|--------------|
| `Action_Flag` | R | R | R |
| `Provider_First_Name` | R | R | R |
| `Provider_Last_Name` | R | R | R |
| `CAQH_Provider_ID` | Leave empty | **R** | **R** |
| `PO_Provider_ID` | Recommended | O | O |
| `Provider_Practice_State` | R | — | — |
| `Provider_Birthdate` | R | — | — |
| `Provider_Type` | R | — | — |
| `Provider_NPI` | Recommended* | — | — |
| `Provider_License_State` + `Provider_License_Number` | Recommended* | — | — |
| `Organization_ID` | R | R | R |

> `*` At least one identifier (NPI, DEA, UPIN, License State + Number, or SSN) should be populated to improve provider matching for Initial Adds.

---

## Common Errors and Resolutions

| CAQH Error Message | Root Cause | Resolution | Confirmed In |
|--------------------|------------|------------|---|
| *"Your file contains the incorrect layout"* | Missing header row | Add the 35-column header as row 1 | 1st submission |
| *"Your file contains the incorrect layout"* | File name missing leading `_` | Rename file to `_6223_ProviderRoster_...txt` | — |
| `Provider_Address_State is invalid` | Full state name instead of 2-char code | Replace `New Jersey` → `NJ`, `Delaware` → `DE`, `Pennsylvania` → `PA` | 1st submission |
| `Add Failed: CAQH Provider ID not found/invalid` | Internal IBX ID placed in `CAQH_Provider_ID` column | Move value to `PO_Provider_ID`; clear `CAQH_Provider_ID` | 2nd submission |
| `Required Field missing/invalid: Provider Practice State` | `Provider_Practice_State` (col 16) is empty | Add to Salesforce report; short-term: copy from `Provider_License_State` | 3rd submission |
| `Required Field missing/invalid: Provider Birthdate` | `Provider_Birthdate` (col 17) is empty | Add practitioner DOB to Salesforce report in `YYYYMMDD` format | 3rd submission |
| `Required Field missing/invalid: Provider Type` | `Provider_Type` (col 22) is empty | Add CAQH provider type code to Salesforce report | 3rd submission |

---

## Reference: CAQH Provider Type Codes (Common)

| Code | Description |
|------|-------------|
| `MD` | Medical Doctor |
| `DO` | Osteopathic Doctor |
| `NP` | Nurse Practitioner |
| `PA` | Physician Assistant |
| `DC` | Doctor of Chiropractic |
| `DDS` | Doctor of Dental Surgery |
| `DPM` | Doctor of Podiatric Medicine |
| `CSW` | Clinical Social Worker |
| `PT` | Physical Therapist |
| `OT` | Occupational Therapist |
| `SLP` | Speech Pathologist |
| `APN` | Advanced Practice Nurse |
| `CRNA` | Certified Registered Nurse Anesthetist |

Full list available in Appendix B of the CAQH Credentialing Roster Data Exchange Specification v3.2.

---

## Salesforce Report Fix — What Needs to Change

The root cause of the 3rd exception batch is that the Salesforce roster report does not include three fields that CAQH requires for every Initial Add. These must be added to the report so future exports are submission-ready without manual patching.

| Field to Add | CAQH Column # | Salesforce Field to Map | Format |
|---|---|---|---|
| `Provider_Practice_State` | 16 | Primary Practice State (or License State) | 2-char ANSI code (`NJ`, `DE`, `PA`) |
| `Provider_Birthdate` | 17 | Practitioner Date of Birth | `YYYYMMDD` — no slashes or dashes |
| `Provider_Type` | 22 | Provider Type / Specialty | CAQH abbreviation (`MD`, `NP`, `DO`, etc.) |

> **Note on `Provider_Birthdate` format:** CAQH requires `YYYYMMDD` with no separators. If Salesforce exports it as `MM/DD/YYYY` or `YYYY-MM-DD`, it must be reformatted during file preparation.

### Column Position in the Final Submission File

These three fields must appear in the correct positions within the 35-column layout. The columns immediately surrounding them for reference:

```
...col 15: Provider_Email | col 16: Provider_Practice_State | col 17: Provider_Birthdate | col 18: Provider_SSN | col 19: Short_SSN | col 20: Provider_DEA | col 21: Provider_UPIN | col 22: Provider_Type...
```

---

## Contact

For CAQH submission issues, contact the CAQH Solutions Center:  
**Phone:** 888-600-9802  
**Hours:** Monday–Friday, 8:00 AM – 5:00 PM ET  
**Portal:** https://proview.caqh.org/PO
