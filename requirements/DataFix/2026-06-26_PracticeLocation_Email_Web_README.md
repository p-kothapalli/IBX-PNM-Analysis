# Practice Location (HealthcareFacility) — Email & Web Data Fix

**Date:** 2026-06-26
**Object:** `HealthcareFacility`
**Purpose:** Collect corrected Office Email / Website so we can bulk-update via Data Loader.

## Template

File: `2026-06-26_PracticeLocation_Email_Web_Template.csv` — one row per facility.

| Column | Field | Who fills | Notes |
|---|---|---|---|
| `Id` | record Id | IT | 15/18-char `HealthcareFacility` Id (required for update). |
| `Name` | `Name` | reference | For human readability — ignored on load. |
| `PRM_OfficeEmail__c` | Office Email | Business | New email. Leave blank to skip. |
| `PRM_WebsiteAddress__c` | Website Address | Business | New URL (full `https://...`). Leave blank to skip. |

## Load

```bash
sf data update bulk --sobject HealthcareFacility \
  --file 2026-06-26_PracticeLocation_Email_Web_Template.csv
```

Notes: don't change headers; keep as CSV (UTF-8); blank value = no change to that field.
