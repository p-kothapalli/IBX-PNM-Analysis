# Vendor verification — Anonymous Apex scripts

These scripts identify practitioner NPIs where the Medical Director has confirmed **NPDB trouble data**, so we can hand a labeled test set to the vendor and verify whether their "Provider Intelligence" API returns the same actions/sanctions for those same NPIs.

**Current scope (2026-05-11):** Signal **S1 only** — `PRM_AdverseActionReview__c.PRM_NPDBAction__c = 'Yes'`. QA org has **175** such records, which gives us a solid test set without needing to add the lower-confidence signals.

Companion strategy doc: [`../Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md`](../Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md)

## Files

| File | Purpose |
|---|---|
| `01_count_trouble_signals.apex` | Diagnostic counts for **all six** signals. Run optionally if you want to see whether any of the other signals are worth adding back. |
| `02_extract_vendor_test_set.apex` | Full annotated version of the extract script. **Use this to read and understand the logic.** |
| `02_extract_vendor_test_set.min.apex` | Minified version (~2.4KB, no comments/whitespace). **Use this in the Developer Console** — the annotated version triggers an `HTTP 431 Request Header Fields Too Large` error in the Execute Anonymous endpoint. |

## How to run (Developer Console — Anonymous Apex)

1. Authenticate: `sf org login web --alias qa-sandbox --instance-url https://test.salesforce.com`
2. Open the org in browser → **Setup → Developer Console**.
3. **Debug → Open Execute Anonymous Window** (or `Ctrl+E` / `Cmd+E`).
4. Open `02_extract_vendor_test_set.min.apex`, copy its **entire contents**, paste into the window, click **Execute**.
   - If you paste the annotated `.apex` version instead, Developer Console returns `HTTP ERROR 431 Request Header Fields Too Large` — use the minified version.
5. The script writes the CSV directly to Salesforce as a **File (ContentVersion)** owned by the running user. **No copy-paste needed.**
6. Download the file using either:
   - **App Launcher → Files → Owned by Me** — click `VendorVerificationTestSet_NPDBAction_<timestamp>.csv` → Download.
   - **Direct URL** — the script prints a `Direct download URL` line in the debug log (`/sfc/servlet.shepherd/version/download/<ContentVersionId>`). Paste into the browser while logged into the org.
7. (Optional) Run `01_count_trouble_signals.apex` only if you want to see whether the other 5 signals would catch additional practitioners not already in the S1 set.

## Org targeting

Run on **qa-sandbox first** to confirm field names & volumes (expected: ~175 rows), then on a production-mirror sandbox (or production via a read-only user) to get the real test set.

## Output (script 2)

CSV columns:

```
NPI, ContactId, PractitionerName, MDR_Summary,
Amounts, DatesSettled, OtherConcerns, LastReviewDate
```

Every row in the CSV represents a practitioner where the Medical Director marked `PRM_NPDBAction__c = 'Yes'` on a `PRM_AdverseActionReview__c` record. Rows are sorted by `LastReviewDate DESC` (most recent first). The `MDR_Summary` / `Amounts` / `DatesSettled` / `OtherConcerns` columns are **informational context only** — they may be populated or blank depending on what the reviewer captured.

## Sending to the vendor

Pick a sample from the CSV:

| Slice | Target rows | Selection |
|---|---|---|
| Recent confirmed NPDB actions | 40 | Top 40 rows by `LastReviewDate DESC` |
| Older confirmed NPDB actions | 20 | Random sample from rows >12 months old |
| Clean controls (negative test) | 20 | NPIs **not** in this list — sample from random recent CAQH-validated practitioners with no AAR record |
| **Total** | **~80** | |

Strip everything except `NPI` (and optionally a blinded `Internal_Id`) before sending. Keep the labeled file internal to grade vendor responses.
