# PEAR Attestation — Read-Only Website Field Blocks "Modify Location" / "Submit" — Bug Fix

**Date:** 2026-04-30
**Org affected:** `qa-sandbox` (PEAR Provider Portal — `ProviderIE` Experience Cloud site)
**OmniScript:** `PRM_AttestationFlow_English` (active version: **v19**)
**Severity:** High — blocks portal users from completing attestation when their stored Website value isn't a strict URL
**Type:** Bug fix (metadata-only; no Apex / DataRaptor / IP changes)
**Scope:** Two read-only Website elements — `WebsiteReadOnly` (General Location Information step) **and** `ReviewWebsite` (Review Location Information step)

---

## 1. Symptom (User-Reported)

> "The user cannot proceed to the **Modify Location** screen. The website-address-format edit is incorrectly firing on the General Location Information screen, and because the existing Website value isn't in the required format, it's preventing access to the Modify screen."

Reproduces consistently for any Practice Location whose `HealthcareFacility.PRM_WebsiteAddress__c` does not match the OOTB OmniScript URL regex (e.g., `www.providergroup.com` with no scheme, values containing spaces, trailing punctuation, internal hostnames, etc.).

---

## 2. Root Cause

The "General Location Information" step of the Attestation OmniScript is read-only by design — it's the **summary of current data** that the user attests to before being asked *"Is this information correct?"* (`IsOfficeInformationCorrect`). If the user picks **"No, I need to make changes"**, they're routed to the editable **Modify General Location Information** step where the field is corrected. The "Review Location Information" step at the end of the flow likewise re-displays the same data read-only before submit.

On both of those read-only steps, the **Website** field is configured as an OmniScript element of `Type: URL`. The OOTB URL element on Vlocity/OmniStudio enforces a URL pattern check **on Step Validation regardless of `readOnly: true`**. When the underlying record contains legacy/malformed website data, the URL pattern validation fails, the step is marked invalid, and the OmniScript blocks the **Next**/**Submit** button — preventing the user from ever reaching the Modify step where the data could be corrected, **and** preventing users on the "Yes, info is correct" branch from completing their attestation on Review.

### 2a. Affected Elements (current state — pre-fix)

| OmniScript | Parent step | Element name | `Type` (pre-fix) | `readOnly` | `defaultValue` | Notes |
|---|---|---|---|---|---|---|
| `AttestationFlow` v19 | `GeneralOfficeInformationReadOnly` (label: **General Location Information**, `validationRequired: true`) | `WebsiteReadOnly` | **`URL`** | `true` | `%Website%` (sourced from `HealthcareFacility.PRM_WebsiteAddress__c` via `GetOfficeInformationData` IP) | Blocks **Next** → blocks entry into Modify Location |
| `AttestationFlow` v19 | `ReviewLocationInformation` (label: **Review Location Information**, `validationRequired: true`) | `ReviewWebsite` | **`URL`** | `true` | `null` (resolved at runtime from the merge state populated by `TransformAttestationData` / Modify branch — value flows in unchanged when user picks "Yes, info is correct") | Blocks **Submit** on bad data for the "no changes" branch |

### 2b. Step Flow (visual)

```
ProviderLocation → GeneralInformation
   └─ IsAddressCorrect = "Yes"
        ↓
   GeneralOfficeInformationReadOnly   ← READ-ONLY summary; contains WebsiteReadOnly (URL)  ❌ blocks Next on bad data
        ↓ (Next)                                                                              
   IsOfficeInformationCorrect
        ├─ "Yes, info is correct"  ─┐
        └─ "No, I need to make changes" →
                GeneralOfficeInformation       ← EDITABLE "Modify General Location Information"
                                                  contains Website (URL, editable) — user fixes here
                                          │
                                          ↓
                                    ReviewLocationInformation  ← READ-ONLY review; contains ReviewWebsite (URL)  ❌ blocks Submit on bad data
                                          ↓ (Submit / UpdatePracticeLocation)
                                       Done
```

### 2c. Why the read-only fields don't need format validation

- The user cannot type into `readOnly: true` fields, so they cannot remediate any pattern failure on either step.
- Pattern validation belongs on the editable element on the **Modify** step (`Website` under `GeneralOfficeInformation`), where the user can actually correct the input. That element is left untouched.
- If the user accepts the data as-is (`IsOfficeInformationCorrect = "Yes"`), no change is written to `PRM_WebsiteAddress__c` — the legacy bad value stays as-is, identical to today's behavior. The Apex write path (`PRM_AttestationProviderServiceUtility.updateGeneralOfficeInformation`) is **only invoked from the Modify branch**, so dropping the read-only validation does not introduce a new write of bad data.

---

## 3. Fix

Change both read-only Website element types from **`URL`** → **`Text`**:
1. `WebsiteReadOnly` on the General Location Information step
2. `ReviewWebsite` on the Review Location Information step

All other properties (`readOnly: true`, `defaultValue` bindings, `label`, `controlWidth`, etc.) remain unchanged. A Text element renders the same way visually for read-only display but does not run URL pattern validation.

### 3a. Files Changed

| # | File | Change |
|---|---|---|
| 1 | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` | `WebsiteReadOnly` `<childElements>` block (under parent `GeneralOfficeInformationReadOnly`): `<type>URL</type>` → `<type>Text</type>` |
| 2 | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` | `ReviewWebsite` `<childElements>` block (under parent `ReviewLocationInformation`): `<type>URL</type>` → `<type>Text</type>` |
| 3 | `vlocity_export/OmniScript/PRM_AttestationFlow_English/PRM_AttestationFlow_English_Element_WebsiteReadOnly.json` | `"Type": "URL"` → `"Type": "Text"` |
| 4 | `vlocity_export/OmniScript/PRM_AttestationFlow_English/PRM_AttestationFlow_English_Element_ReviewWebsite.json` | `"Type": "URL"` → `"Type": "Text"` |

### 3b. Diff — `PRM_AttestationFlow_English_19.os-meta.xml` (`WebsiteReadOnly`)

```diff
             <name>WebsiteReadOnly</name>
             <omniProcessVersionNumber>0.0</omniProcessVersionNumber>
             <propertySetConfig>{
   &quot;disOnTplt&quot; : false,
   ...
   &quot;defaultValue&quot; : &quot;%Website%&quot;,
   &quot;readOnly&quot; : true,
   ...
   &quot;label&quot; : &quot;Website&quot;,
   &quot;controlWidth&quot; : 6
 }</propertySetConfig>
             <sequenceNumber>2.0</sequenceNumber>
-            <type>URL</type>
+            <type>Text</type>
         </childElements>
```

### 3c. Diff — `PRM_AttestationFlow_English_19.os-meta.xml` (`ReviewWebsite`)

```diff
             <name>ReviewWebsite</name>
             <omniProcessVersionNumber>0.0</omniProcessVersionNumber>
             <propertySetConfig>{
   &quot;disOnTplt&quot; : false,
   ...
   &quot;defaultValue&quot; : null,
   &quot;readOnly&quot; : true,
   ...
   &quot;label&quot; : &quot;Website&quot;,
   &quot;controlWidth&quot; : 6
 }</propertySetConfig>
             <sequenceNumber>8.0</sequenceNumber>
-            <type>URL</type>
+            <type>Text</type>
         </childElements>
```

### 3d. Diff — DataPack JSONs

```diff
# PRM_AttestationFlow_English_Element_WebsiteReadOnly.json
-    "Type": "URL",
+    "Type": "Text",
     "VlocityDataPackType": "SObject",
     "VlocityRecordSObjectType": "OmniProcessElement",
     "VlocityRecordSourceKey": "OmniProcessElement/OmniProcess/PRM/AttestationFlow/English/WebsiteReadOnly"
```

```diff
# PRM_AttestationFlow_English_Element_ReviewWebsite.json
-    "Type": "URL",
+    "Type": "Text",
     "VlocityDataPackType": "SObject",
     "VlocityRecordSObjectType": "OmniProcessElement",
     "VlocityRecordSourceKey": "OmniProcessElement/OmniProcess/PRM/AttestationFlow/English/ReviewWebsite"
```

### 3e. What is **NOT** changed (intentional)

| Element | Parent step | Why not changed |
|---|---|---|
| `Website` (editable) | `GeneralOfficeInformation` (Modify) | Validation is correct here — the user can type and fix the value. |
| `defaultValue: "%Website%"` merge binding on `WebsiteReadOnly`; `defaultValue: null` on `ReviewWebsite` | both read-only elements | Data binding is unaffected by element type; merge-value resolution still works for `Text` elements. |
| `PRM_AttestationProviderServiceUtility.updateGeneralOfficeInformation` | Apex | No code change — the Apex path is only invoked when `IsOfficeInformationCorrect = "No, I need to make changes"`, i.e., the user explicitly enters an edited value through the URL-validated editable field. |

---

## 4. Deployment Plan

This is a **metadata-only** change to a single OmniScript element on the active v19 version.

### Option A — Patch the active v19 in place (recommended for a hotfix)

```bash
sf project deploy start \
  --target-org qa-sandbox \
  --metadata "OmniProcess:PRM_AttestationFlow_English_19" \
  --test-level RunLocalTests
```

Vlocity caches OmniScript metadata. After deploy, **clear the platform cache** to ensure the running OmniScript picks up the change:

```bash
sf apex run --target-org qa-sandbox --file scripts/clearOmniCache.apex
```

(Or `Setup → Vlocity → Tools → Clear Platform Cache` in the UI.)

### Option B — Bump to a new version (if release process requires it)

1. Activate a clone as v20 in OmniScript Designer (or via Vlocity DataPack export).
2. Apply the same `Type: URL → Text` change on `WebsiteReadOnly`.
3. Activate v20, deactivate v19.
4. Repoint any FlexCard / Site `vlocity_omniscript-uniqueName` references if they're version-pinned (the current `ProviderIE` site uses the active version, not version-pinned, so no extra step is needed).

### Validation post-deploy

Confirm via Tooling API that both elements changed:

```bash
sf data query --target-org qa-sandbox --use-tooling-api -q "
  SELECT Name, Type, PropertySetConfig
  FROM OmniProcessElement
  WHERE Name IN ('WebsiteReadOnly','ReviewWebsite')
    AND OmniProcess.Name = 'AttestationFlow'
    AND OmniProcess.IsActive = true"
```

Expected `Type` in both result rows: `Text`.

---

## 5. Test Plan

### 5a. Reproduction setup (before deploying the fix)

Pick a `HealthcareFacility` whose `PRM_WebsiteAddress__c` is intentionally malformed:

```sql
-- one-off in the dev/QA org, NOT prod
UPDATE HealthcareFacility
SET    PRM_WebsiteAddress__c = 'www.example-bad-format.com no-scheme'
WHERE  Id = '<test HCF Id>';
```

Or pull a real example from the audit log:

```bash
sf data query --target-org qa-sandbox -q "
  SELECT Id, PRM_PracticeName__c, PRM_WebsiteAddress__c
  FROM HealthcareFacility
  WHERE PRM_WebsiteAddress__c != null
    AND NOT PRM_WebsiteAddress__c LIKE 'http%'
  LIMIT 20"
```

### 5b. Test scenarios

| # | Scenario | Pre-fix (expected: BUG) | Post-fix (expected: PASS) |
|---|---|---|---|
| 1 | HCF Website = `www.example.com` (no scheme) | Click **Next** on General Location Information → URL validation error, Next is blocked. | Click **Next** → step proceeds. User reaches `IsOfficeInformationCorrect`. Choosing "No, I need to make changes" routes to **Modify General Location Information**. |
| 2 | HCF Website = `https://valid-site.com` | Next works (URL is valid). | Next works (Text accepts everything). |
| 3 | HCF Website = `null` / blank | Next works (`required: false`). | Next works (unchanged). |
| 4 | HCF Website = `https://valid.com extra junk` (whitespace + tail) | Next blocked. | Next proceeds. |
| 5 | On **Modify General Location Information** step, user enters `not-a-url` into the editable **Website** field | (Same — Modify step blocks save, as it should.) | **Modify step still validates** — user is forced to enter a valid URL before saving. (Editable URL element kept intact.) |
| 6 | "Yes, info is correct" branch with bad data — user reaches **Review Location Information** step and clicks Submit | Submit blocked by `ReviewWebsite` URL pattern check. | Submit proceeds; `UpdatePracticeLocation` runs successfully. |
| 7 | "No, I need to make changes" branch — user fixes Website on Modify, reaches Review, clicks Submit | (Pre-fix: works because Modify wrote a valid URL; in practice users on the bad-data 'Yes' branch were the ones blocked.) | Submit proceeds; new value appears in `HealthcareFacilityHistory` for `PRM_WebsiteAddress__c` with `CreatedBy.Profile = 'PDM Portal User'`. |
| 8 | After fix, end-to-end happy path: open AttestationFlow → through to Submit | Cannot complete on bad data. | Completes; on submit, `PRM_AttestationDate__c` and `PRM_AttestationBy__c` stamped on the HCF, with `HealthcareFacilityHistory.CreatedBy.Profile = 'PDM Portal User'` (per audit-report §6). |
| 9 | Read-only display rendering on both General Location Info and Review Location Info steps | (URL renders as link.) | Text renders as plain text. **Verify visually** that the Website value is still readable (it will not be a clickable link). See §6 caveat. |

### 5c. Regression scope

- No DataRaptor or IP changes → no impact on writes (`PRM_UpdateAttestationData` chain), reads (`GetContactDetailsForAttestation`, `GetPractitionerDetailsForAttestation`), or Apex remote actions (`UpdatePracticeLocation`, `UpdateGeneralOfficeInformationData`, `UpdateAlternateContactMethod`, `UpsertPractitionerData`).
- No Field History Tracking impact (changes are UI-only; `PRM_WebsiteAddress__c` still tracked per `PEAR_Portal_Field_Audit_Report.md` §4).
- No CSP / Network / Profile / Permission Set change.
- No object-schema change.

---

## 6. Known Caveat & Recommended Follow-ups

### 6a. Read-only display loses the auto-link rendering

OOTB URL elements render the value as a clickable `<a href>`; Text elements render plain text. Acceptable for read-only attestation-summary / review screens (the user's task is to verify, not to click out), but flagging here for awareness. If linking is desired, the long-term fix is to **scrub legacy data** (one-time DML to fix all `PRM_WebsiteAddress__c` values to `https://...`) and revert both elements to `Type: URL`. The Text-element fix is a defensive change that protects the flow from any future bad data as well.

### 6b. Long-term data quality

- Add an Apex/Flow validation when `PRM_WebsiteAddress__c` is set in any path other than this attestation flow (e.g., admin record edits, data loads), so future data conforms to URL format.
- Optional one-time DML to normalize existing values:
  ```sql
  UPDATE HealthcareFacility
  SET    PRM_WebsiteAddress__c = 'https://' || PRM_WebsiteAddress__c
  WHERE  PRM_WebsiteAddress__c != null
    AND  NOT PRM_WebsiteAddress__c LIKE 'http%';
  ```
  (Run as a backfill script with a backup, not blanket DML.)

---

## 7. Rollback Plan

Revert is symmetric to apply — change `Text` back to `URL` in both files and redeploy the OmniProcess metadata. No data migration required.

---

## 8. Appendix — Files Touched in This Patch

| Kind | Path | Change |
|---|---|---|
| OmniScript metadata (active v19) | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` | `WebsiteReadOnly` `<type>URL</type>` → `<type>Text</type>` |
| OmniScript metadata (active v19) | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` | `ReviewWebsite` `<type>URL</type>` → `<type>Text</type>` |
| Vlocity DataPack (export) | `vlocity_export/OmniScript/PRM_AttestationFlow_English/PRM_AttestationFlow_English_Element_WebsiteReadOnly.json` | `"Type": "URL"` → `"Type": "Text"` |
| Vlocity DataPack (export) | `vlocity_export/OmniScript/PRM_AttestationFlow_English/PRM_AttestationFlow_English_Element_ReviewWebsite.json` | `"Type": "URL"` → `"Type": "Text"` |
| Documentation (this file) | `requirements/PEAR/PEAR_WebsiteReadOnly_BugFix.md` | New |

Older inactive versions (`PRM_AttestationFlow_English_14`–`18`) reference the same element names but are not active — they are intentionally left untouched. If a rollback to a prior version is ever required, the same fix should be applied there at that time.
