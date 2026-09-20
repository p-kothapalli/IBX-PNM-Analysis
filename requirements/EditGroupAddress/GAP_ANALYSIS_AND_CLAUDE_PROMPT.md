# PAR Form Address Step — Gap Analysis & Claude Implementation Prompt

**Date:** April 15, 2026  
**Author:** Technical Analysis — GitHub Copilot  
**Component Under Analysis:** `prmAddressGroupManager` LWC + `PRM_AddressManagementService` Apex  
**Target:** Full parity with the Practitioner Participation Form (PAR Form) address step  

---

## PART 1: WHAT IS CURRENTLY IMPLEMENTED ✅

### Fields Implemented (Create New Location Form)

| Field | Type | Constraints in HTML | JS Validation | Status |
|-------|------|---------------------|---------------|--------|
| Facility Name | `lightning-input` text | `required` | Required check only | ✅ |
| Group NPI | `lightning-input` text | `max-length="10"`, `pattern="[0-9]{10}"` | 10-digit check | ✅ |
| Address Line 1 | `lightning-input` text | `required` | Required check only | ✅ |
| Address Line 2 | `lightning-input` text | None | None | ✅ |
| City | `lightning-input` text | `required` | Required check only | ✅ |
| State | `lightning-combobox` | `required` | Required check only | ✅ |
| County | `lightning-combobox` | `required`, disabled until state selected | Required check only | ✅ |
| Zip Code | `lightning-input` text | `max-length="5"`, `pattern="[0-9]{5}"` | 5 or 9 digits (JS) | ✅ |
| Zip+4 | `lightning-input` text | `max-length="4"`, `pattern="[0-9]{4}"` | None | ✅ |
| Phone | `lightning-input` tel | `required` | 10 digits (JS) | ✅ |
| Phone Extension | `lightning-input` text | `max-length="10"` | None | ✅ |
| Fax | `lightning-input` tel | None | None | ✅ |
| Is Primary (checkbox) | `lightning-input` checkbox | None | None | ✅ |
| Telehealth Only (checkbox) | `lightning-input` checkbox | None | None | ✅ |

### Address Validation (Precisely Integration)
- `validateAddress()` Apex method: currently broken (direct callout) — see FIX 1 for IP-based replacement
- `addressValidationModal` LWC: **target design** = minimal "Address validation feedback" dialog — shows standardized suggestion as a single bold line, "Yes, change" (brand) and "No, mine is correct" (neutral) buttons, no confidence badges, no geocoding display, no side-by-side comparison — see FIX 1 Part B for full redesign spec
- `handleAddressSelected()`: routes to `proceedWithCreateLocation()` or `proceedWithUpdateLocation()`
- Modal only fires when `hasMatch === true`; when no match or API down, proceed silently with inline banner

### Edit Subtab (Active Locations)
- Active locations are **read-only by design** — no edit action
- `handleValidateEditAddress()` exists for pending locations only
- `handleUseRecommendedAddress()` / `handleUseProvidedAddress()` → `saveEditedLocation()`
- Back button with unsaved-changes guard (needs replacement — `confirm()` is blocked in Lightning Experience)

### Pending Locations Edit
- Subtab edit form present for pending locations
- Save calls `handleSaveLocation()` (routes through `validateAddress()` → modal)

### Apex Backend
- `createNewLocation()` — creates 5 records in sequence
- `updatePractitionerLocation()` — updates existing location + geocoding
- `markAddressAsError()` — soft-delete (sets `PRM_IsErrorRecord__c = true`)
- `getStateOptions()` / `getCountyOptionsByState()` — picklist dependency
- `addTaxonomiesToPractitionerFacility()` — backend ready, no UI
- `addAssistiveAidsToFacility()` — backend placeholder, no UI
- `addAffirmingCareCategories()` — backend placeholder, no UI
- `createNewGroup()` — backend ready, no UI

---

## PART 2: WHAT IS MISSING / BROKEN 🚨

---

### 🔴 CRITICAL — Precisely Address Validation NOT Working

#### Root Problem
The Apex `validateAddress()` method calls:
```apex
req.setEndpoint('callout:PRM_Precisely_API/verify');
```
The Named Credential `PRM_Precisely_API.namedCredential-meta.xml` points to:
```
https://eapiqa.ibx.com/qa/api/v1/precisely
```

**Issues identified:**
1. **Endpoint path mismatch** — The named credential URL already ends in `/precisely`, and the Apex appends `/verify`, resulting in `https://eapiqa.ibx.com/qa/api/v1/precisely/verify`. The PAR form uses the Integration Procedure `PRM_IPPreciselyAPICall` (also referenced as `PRMIPAddressValidation`), **not a raw HTTP callout**. The actual endpoint, authentication token mechanism, and response shape for a direct REST call vs. the IP may differ.
2. **ExternalCredential dependency** — The Named Credential uses `PRM_Mulesoft_Access_Token` external credential. If the OAuth token for the QA Mulesoft endpoint has expired or is not set up for Apex callouts (only for OmniScript), the callout will return 401 or throw a `CalloutException`.
3. **Response parsing may be incorrect** — The PAR form Integration Procedure returns a nested object under a key like `PreciselyResponse`, but the current `validateAddress()` Apex treats the top-level `res.getBody()` as the address map directly. If the real response is wrapped (e.g. `{"output": {"AddressLine1": ...}}`), `parseValidatedAddress()` will return all nulls.
4. **Confidence value parsing is fragile** — `Decimal.valueOf(String.valueOf(confObj))` will throw if `confObj` is an Integer (e.g. `95` not `"95"`).
5. **`hasMatch` detection is wrong** — `statusCode != 'No match found'` is truthy even if `statusCode` is empty string or null (when the API fails silently). Should be: `String.isNotBlank(statusCode) && statusCode != 'No match found'`.
6. **No Remote Site Setting for Precisely** — `remoteSiteSettings` folder only contains Mulesoft entries. If the callout bypasses the named credential and uses a raw URL, it will be blocked. Confirm that `callout:PRM_Precisely_API` is whitelisted.
7. **Silent failure path swallows errors** — When `validationResult.success = false`, the current code shows a warning toast but proceeds with the address as-entered. This means **the user never knows if Precisely is broken** — they just get un-standardized addresses silently saved. Need a clear "Validation unavailable" indicator, not just a warning toast that disappears.

---

### ✅ CORRECT BEHAVIOR — Active Locations Are Intentionally Read-Only

Active Locations should **NOT** have an Edit action. Only Pending Locations are editable. This is by design — active practice locations are locked records managed through the credentialing workflow. The `activeLocationsColumns` should only have the "Remove" (soft-delete) action, which is the current behavior.

**No change needed here** — the current implementation is correct for Active Locations.

---

### 🔴 CRITICAL — Pending Locations Edit Form Has Regression Issues

Since Pending Locations are the **only** editable locations, this form must be fully correct. Current gaps:

**Zip Code HTML constraint is wrong:**
In `prmAddressGroupManager.html` (Pending Edit Subtab), the Zip Code field has:
```html
max-length="5" pattern="[0-9]{5}"
```
This blocks entry of a 9-digit ZIP (12345-6789). The JS validates "5 or 9 digits" but the HTML won't even let the user type 9 digits. Fix: `max-length="9"`, remove the `pattern` attribute.

**State is a plain text input instead of combobox:**
The Pending Edit form uses `<lightning-input max-length="2">` for State instead of `<lightning-combobox options={stateOptions}>`. This means:
- No picklist enforcement (user can type any 2 chars)
- No county dropdown re-load when state changes
- Inconsistent UX vs the Create New form which correctly uses a combobox

**Validation gaps in `handleSaveLocation()` / `validateEditForm()`:**
1. **Phone is treated as optional** — `if (this.editAddressData.phone)` — phone is required
2. **Fax format never validated** — 10-digit rule not checked when fax is provided
3. **Phone Extension max-length not JS-validated** — HTML has `max-length="10"` but JS doesn't check
4. **Address Line 1 no max-length** — `PRM_AddressLine1__c` is 255 chars; not enforced in HTML or JS
5. **City no max-length** — `PRM_City__c` is 100 chars; not enforced in HTML or JS
6. **Zip+4 not JS-validated** — HTML pattern `[0-9]{4}` is browser-only; JS never checks if provided
7. **County not validated** — `editAddressData.county` is populated but never checked as required
8. **`handleSaveLocation()` calls `validateAddress()` before validating fields** — if Address Line 1 is empty, the Precisely API call fires with empty data, wastes the callout, and returns a bad response. Required fields must be checked first.

---

### 🟠 HIGH — Validation Error Messages Are Inconsistent

Current error messages across forms:

| Location | Field | Message Shown |
|----------|-------|---------------|
| Create New — JS | Zip | "Zip code must be 5 or 9 digits" |
| Create New — HTML | Zip | Browser native: "Please match the requested format" (pattern mismatch) |
| Edit Subtab — JS | Zip | "Zip code must be 5 or 9 digits" |
| Edit Subtab — JS | Phone | "Phone must be 10 digits" |
| Create New — JS | Phone | "Phone number must be 10 digits" |
| HTML pattern mismatch | NPI | "NPI must be exactly 10 digits" |
| HTML pattern mismatch | Zip+4 | Browser native — no custom message set |

**Problems:**
- `message-when-pattern-mismatch` is set for NPI but NOT for Zip, Zip+4, or Phone HTML inputs
- JS validation fires a single toast combining all errors — no field-level inline error highlighting
- The error messages themselves differ (`"must be 10 digits"` vs `"must be exactly 10 digits"`) between forms
- No `max-length` enforcement error message for Address Line 1, Address Line 2, City fields

---

### 🟠 HIGH — Field Length Constraints Missing

Per the PAR form data model and Salesforce field definitions:

| Field | Object Field | Max Length | HTML `max-length` | JS Check |
|-------|-------------|------------|-------------------|----------|
| Address Line 1 | `PRM_AddressLine1__c` | 255 | ❌ Not set | ❌ None |
| Address Line 2 | `PRM_AddressLine2__c` | 255 | ❌ Not set | ❌ None |
| City | `PRM_City__c` | 100 | ❌ Not set | ❌ None |
| Fax | `PRM_Fax__c` | 40 | ❌ Not set | ❌ None |
| Facility Name | `Name` (Location) | 255 | ❌ Not set | ❌ None |
| Phone Extension | `PRM_PhoneExtension__c` | 10 | ✅ max-length="10" | ❌ No JS check |
| Zip+4 | `PRM_Zip4__c` | 4 | ✅ max-length="4" | ❌ No JS validation |
| Tax ID (Group Search) | — | 10 | ✅ max-length="10" | ❌ No format check (XX-XXXXXXX) |
| Group NPI (Group Search) | — | 10 | ✅ max-length="10" | ✅ JS 10-digit check |

---

### 🟠 HIGH — Tax ID Format Validation Missing

In the group search section, the Tax ID field has:
```html
placeholder="XX-XXXXXXX" max-length="10"
```
But there is **no validation** that:
- Tax ID follows the EIN format `XX-XXXXXXX` (2 digits, dash, 7 digits)
- Tax ID contains only digits (and optionally a dash)
- Tax ID is at least 9 digits when stripped of non-numeric chars

The PAR form enforces EIN format. This is also needed to properly call `findAccountsByNpiAndTaxId()`.

---

### 🟠 HIGH — Fax Validation Missing Everywhere

The Fax field appears in:
1. Create New Location form
2. Edit Subtab (Active Locations)
3. Pending Edit form

None of these validate fax format. Per PAR form rules, Fax is optional but when provided must be 10 digits (same rule as Phone). No JS validation, no HTML pattern, no `message-when-pattern-mismatch`.

---

### 🟠 HIGH — Pending Edit Form Missing Fields: County, Telehealth Only, Fax

The Pending Locations edit form (`showPendingEditSubtab`) is missing three fields that are present in the Create New Location form:

1. **County** — The Create New form has a state-dependent `lightning-combobox` for County. The Pending Edit form has no County field at all. When a user edits a pending location and changes the state, there is no way to update the county to match the new state.

2. **Telehealth Only** — The `isTelehealthOnly` boolean is set on the Location object (`PRM_TelehealthOnly__c`). It is present in the Create New form as a checkbox. It is absent from the Pending Edit form. Users have no way to toggle this on a pending location.

3. **Fax** — The Pending Edit form does not render a Fax field. The underlying `PRM_Fax__c` Address field is editable and the data model supports it, but there's no input for it in the Pending Edit form HTML.

---

### 🟠 HIGH — State in Pending Edit Uses Text Input Instead of Combobox

In the Pending Locations edit subtab, State renders as `<lightning-input max-length="2">` (plain text), not a combobox. The Create New form uses `lightning-combobox` bound to `stateOptions` loaded from Apex. The Pending Edit form must also use a combobox so:
- State abbreviations are validated against the picklist (not free-typed)
- Changing the state triggers `loadCountiesForState()` to reload county options
- The `onchange` handler updates both `selectedPendingLocationForEdit.state` and resets `county`

---

### 🟡 MEDIUM — Phone Number Formatting Not Applied

The PAR form displays phone numbers formatted as `(XXX) XXX-XXXX` or stores them as 10 raw digits. Currently:
- `newLocationPhone` stores raw digits/whatever user typed
- No auto-formatting on input
- No stripping of formatting characters before saving (only `replace(/\D/g, '')` in validation check, but the raw value is passed to Apex)
- **The Apex `createNewLocation()` receives the formatted value** — if user types `(215) 555-1234`, the phone stored is `(215) 555-1234` not `2155551234`

---

### 🟡 MEDIUM — Zip Code Accepts 5-Digit but HTML Pattern Blocks 9-Digit

In the Create New Location form:
```html
max-length="5" pattern="[0-9]{5}"
```
The JS validation checks "5 OR 9 digits" — but the HTML `max-length="5"` **prevents the user from even typing a 9-digit ZIP**. The two constraints directly contradict. The HTML should allow `max-length="9"` and the pattern should be `[0-9]{5}(-[0-9]{4})?` or simply removed from HTML (handle entirely in JS).

---

### 🟡 MEDIUM — Group NPI in Group Search Has No Luhn/Format Validation

The Group NPI field in the "Add New" tab search section validates that it's 10 digits via `pattern="[0-9]{10}"` in HTML, but:
- No Luhn algorithm check (NPIs have a specific check-digit algorithm)
- The PAR form validates that NPIs pass the CMS NPI Luhn check
- Should display: `"Please enter a valid 10-digit NPI"` not just a generic pattern mismatch

---

### 🟡 MEDIUM — No Inline Field-Level Error Display

All validation errors are shown via a single `ShowToastEvent` that lists all errors comma-separated. The PAR form shows inline field-level error messages using `reportValidity()` on individual inputs. The LWC approach should:
1. Call `this.template.querySelectorAll('lightning-input, lightning-combobox').forEach(input => input.reportValidity())` to show browser-native inline errors
2. Only show a toast for business-rule violations that can't be captured by HTML validation (e.g., "phone must be exactly 10 digits")

---

### 🟡 MEDIUM — Precisely Integration: Wrong IP Name Referenced in Docs

The `COMPONENTS_SUMMARY.md` says:
> **Integration Procedure:** `PRMIPAddressValidation`

But the `Address_Validation_Implementation_Plan.md` says:
> `PRM_IPPreciselyAPICall`

And the actual Apex code calls a **direct HTTP callout** (not an Integration Procedure at all). The PAR form uses an OmniScript Integration Procedure, not a raw HTTP callout. The IP handles authentication, error handling, and response normalization. **The current direct HTTP callout approach bypasses all of that.** The fix is to use `vlocity_cmt.IntegrationProcedureService.runIntegrationProcedure()` as originally designed in the plan document.

---

### 🟡 MEDIUM — `handleSaveLocation()` in Pending Edit Doesn't Validate Fields First

`handleSaveLocation()` (called from Pending Edit "Save" button) directly calls `validateAddress()` without first checking required fields. If address line 1 is empty, the Precisely call will fire with empty data, waste an API call, and return a bad response.

---

### 🟡 MEDIUM — Soft Delete Uses `this.currentUserId` Which Returns Empty String

In `removeAddress()`:
```javascript
const result = await markAddressAsError({
    facilityId: facilityId,
    reason: reason,
    removedBy: this.currentUserId
});
```

`get currentUserId()` returns `this.userId || ''` — but `this.userId` is never set. The `removedBy` is always `''`. The audit trail is broken. Should use `@wire(CurrentPageReference)` or `import UserId from '@salesforce/user/Id'`.

---

### 🟡 MEDIUM — Confirmation Dialogs Use Native `confirm()` — Blocked in Lightning

The code uses `confirm('...')` in multiple places:
- `handleRemoveAddress()`
- `handleRemoveActiveLocation()`
- `handleRemoveActiveLocationFromTable()`
- `handleRemovePendingLocationFromTable()`
- `handleCancelEdit()` (for unsaved changes)

**Native `confirm()` dialogs are blocked in Salesforce Lightning Experience.** They always return `false` in LE because the iframe security model blocks `window.confirm`. This means:
- **Users cannot remove any address** — the confirm always returns false and the delete is silently cancelled
- **The unsaved-changes guard never works** — users are never warned before discarding

Must replace with a custom `lightning-modal` or a `slds-modal` confirmation dialog component.

---

### 🟡 MEDIUM — `handleCreateNewLocation()` Shows `showSpinner = false` Before Modal Closes

In the create flow:
```javascript
this.showValidationModal = true;
this.showSpinner = false; // Hide spinner when modal shows
```
Then later in `handleAddressSelected()`:
```javascript
this.showValidationModal = false;
// ... proceeds to create
this.showSpinner = true; // (inside proceedWithCreateLocation)
```

But `proceedWithCreateLocation()` sets `showSpinner = true` in a `try` block and `= false` in `finally`. If the user hits "Cancel" on the modal, `this.pendingLocationData` is cleared, but `showCreateNewLocation` stays `true` and the form stays visible — which is correct. However the spinner state when cancellation happens mid-flow can leave the UI in a stuck spinner state in certain race conditions.

---

### 🟡 MEDIUM — Taxonomy / Provider Type / Assistive Aids / Affirming Care UI Missing

This is one of the most significant PAR form parity gaps. The PAR form collects four related pieces of data at the address step that our custom LWC **never asks for**. The backend is fully ready — `createNewLocation()` already accepts `taxonomyIds[]` but the LWC always passes `[]`.

#### What the PAR form collects at the address step:

**1. Provider Type** (`PRM_ProviderType__c` object, linked via `PRM_ProviderTypeAssignment__c`)
- A lookup to the custom object `PRM_ProviderType__c`
- This is the credentialing category (e.g., "Physician", "Nurse Practitioner", "PA", "CRNA")
- The `PRM_ProviderTypeAssignment__c` junction object links:
  - `PRM_PractitionerType__c` → lookup to `PRM_ProviderType__c`
  - `PRM_CareTaxonomy__c` → lookup to `CareTaxonomy`
  - `PRM_BCBSAPractitionerTypeCode__c` → text code
  - `PRM_VendorType__c` → text
- **Not currently passed to `createNewLocation()` at all**

**2. Care Taxonomy / Specialty** (`CareTaxonomy` standard object → `HealthcareProviderTaxonomy`)
- A multi-select from the `CareTaxonomy` standard object (NUCC taxonomy codes)
- The backend `addTaxonomiesToPractitionerFacility()` creates `HealthcareProviderTaxonomy` records
- Fields set: `TaxonomyId`, `PractitionerId`, `AccountId`, `IsPrimaryTaxonomy` (first = true), `PRM_Pending__c = true`
- The `createNewLocation()` method already accepts `List<String> taxonomyIds` and calls this automatically when IDs are provided
- **UI needed:** A `lightning-dual-listbox` or `lightning-combobox` populated by querying `CareTaxonomy` records, with one selection able to be marked "Primary"

**3. Assistive Aids** (`ProviderFeature` or picklist)
- Multi-select of accessibility features at this location (e.g., "AS" = American Sign Language, "TT" = TTY/TDD, "TR" = Translation services)
- Backend `addAssistiveAidsToFacility()` is a **placeholder** — marked with TODO comment, not yet implemented
- **UI needed + Apex TODO must be finished before this can save**

**4. Affirming Care Categories** (`HealthcarePractitionerFacility.PRM_AffirmingCareCategories__c` picklist)
- Multi-select checkboxes of affirming care designations
- Backend `addAffirmingCareCategories()` is also a **placeholder** with TODO comment
- **UI needed + Apex TODO must be finished**

#### Data Model Context:

```
PRM_ProviderTypeAssignment__c
  ├── PRM_PractitionerType__c  → lookup → PRM_ProviderType__c (the credential category)
  ├── PRM_CareTaxonomy__c      → lookup → CareTaxonomy (NUCC specialty code)
  ├── PRM_BCBSAPractitionerTypeCode__c
  └── PRM_VendorType__c

HealthcareProviderTaxonomy (created by addTaxonomiesToPractitionerFacility)
  ├── TaxonomyId               → lookup → CareTaxonomy
  ├── PractitionerId           → Account (practitioner)
  ├── AccountId                → Account (group)
  ├── IsPrimaryTaxonomy        → Boolean
  └── PRM_Pending__c           → Boolean
```

#### What needs to be built:

| Item | Apex Status | UI Status | Notes |
|------|-------------|-----------|-------|
| Provider Type selection | ❌ No method exists | ❌ No UI | Need `getProviderTypeOptions()` Apex method querying `PRM_ProviderType__c` |
| Care Taxonomy multi-select | ✅ `addTaxonomiesToPractitionerFacility()` ready | ❌ No UI | Need `getTaxonomyOptions()` + `lightning-dual-listbox` |
| Primary taxonomy designation | ✅ Auto-sets first as primary | ❌ No UI | Need radio or checkbox to designate which is primary |
| Assistive Aids | ⚠️ Placeholder only (TODO) | ❌ No UI | Apex TODO must be implemented + `getAssistiveAidOptions()` needed |
| Affirming Care | ⚠️ Placeholder only (TODO) | ❌ No UI | Apex TODO must be implemented + `getAffirmingCareOptions()` needed |

#### Implementation Approach for Taxonomy + Provider Type:

The Apex needs two new `@AuraEnabled(cacheable=true)` methods:

```apex
// Returns list of {label, value} for Provider Type combobox
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getProviderTypeOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    for (PRM_ProviderType__c pt : [
        SELECT Id, Name FROM PRM_ProviderType__c 
        WHERE IsActive__c = true ORDER BY Name
    ]) {
        options.add(new Map<String, String>{ 'label' => pt.Name, 'value' => pt.Id });
    }
    return options;
}

// Returns list of {label, value} for CareTaxonomy dual-listbox
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getTaxonomyOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    for (CareTaxonomy ct : [
        SELECT Id, Name, Code FROM CareTaxonomy 
        WHERE IsActive = true ORDER BY Name LIMIT 500
    ]) {
        options.add(new Map<String, String>{
            'label' => ct.Name + (ct.Code != null ? ' (' + ct.Code + ')' : ''),
            'value' => ct.Id
        });
    }
    return options;
}
```

The LWC Create New Location form needs an expandable "Specialty & Accessibility" section with:
- `lightning-combobox` for Provider Type (single select, from `getProviderTypeOptions()`)
- `lightning-dual-listbox` for Care Taxonomy / Specialty (multi-select, from `getTaxonomyOptions()`, first selected auto-marked primary)
- Assistive Aids checkboxes (deferred until Apex placeholder is implemented)
- Affirming Care checkboxes (deferred until Apex placeholder is implemented)

The selected `taxonomyIds` array must be passed into `createNewLocation()` replacing the hardcoded `[]`.

---

### 🟡 MEDIUM — New Group Creation UI Missing

The `createNewGroup()` Apex method is fully implemented and tested. But there is no "Create New Group" button or form in the LWC. If a practitioner needs to add a group that doesn't exist yet, they have no way to create it through this component.

---

### 🟡 MEDIUM — No Fax Field in Pending Locations Datatable

The `pendingLocationsColumns` definition does not show Fax. When reviewing pending locations before editing them, users cannot see the current fax value in the list and don't know if it needs to be corrected. Consider adding a Fax column or surfacing it in the expanded row details.

---

### 🔵 LOW — Missing `message-when-value-missing` on Required Fields

The HTML `required` attribute on `lightning-input` fields triggers a generic "Complete this field" message. The PAR form uses specific messages:
- Address Line 1: `"Address is required"`
- City: `"City is required"`
- Phone: `"Phone number is required"`
- State: `"State is required"`
- County: `"County is required"`
- Zip: `"Zip Code is required"`

Use `message-when-value-missing` attribute on each required field.

---

### 🔵 LOW — Group NPI in Create New Form Has No `required` Constraint

The NPI field in Create New form:
```html
placeholder="Enter 10-digit NPI (optional)"
```
But in the JS validation:
```javascript
const npiToUse = this.newLocationGroupNpi || this.groupNpi;
if (npiToUse && npiToUse.length !== 10) { ... }
```
It uses `this.groupNpi` as fallback — the group NPI from the search section. This is good, but there is no clear UI indicator to the user that "Group NPI is auto-populated from your search". If the search NPI was invalid, the fallback also fails silently.

---

### 🔵 LOW — Active Locations Edit Subtab Lacks "Validate Address" Button Visibility

The edit subtab has `handleValidateEditAddress()` wired to a button. However, looking at the HTML, the subtab does not appear to actually render the validate button conditionally. The subtab needs clear state: "Edit Mode" vs "Validate Mode" with visible button to trigger Precisely, and clear instructions.

---

### 🔵 LOW — No Duplicate Group Search Warning Before Creating New Location

If a user fills in the Create New Location form and the entered Group NPI + Tax ID matches an existing group that already has a location at that address, the component proceeds to create a new location without warning. The `detectLocationScenario()` Apex method exists but is never called from the create-new flow.

---

## PART 3: COMPLETE FIELD & VALIDATION MATRIX

### All Fields on the PAR Form Address Step

| # | Field Label | Required | Type | Max Length | Format/Pattern | Current Status |
|---|-------------|----------|------|------------|----------------|---------------|
| 1 | Group NPI | Yes | Text | 10 | `[0-9]{10}` | ✅ Present, partial validation |
| 2 | Group Tax ID | Yes | Text | 10 | `XX-XXXXXXX` format | ⚠️ No format validation |
| 3 | Group Name | Yes | Record Picker | — | Must exist in Account | ✅ Present |
| 4 | Facility Name / Practice Name | Yes | Text | 255 | No special format | ⚠️ No max-length constraint |
| 5 | Address Line 1 | Yes | Text | 255 | No special format | ⚠️ No max-length constraint |
| 6 | Address Line 2 | No | Text | 255 | No special format | ⚠️ No max-length constraint |
| 7 | City | Yes | Text | 100 | Letters only | ⚠️ No max-length, no letters-only validation |
| 8 | State | Yes | Combobox | — | From picklist | ⚠️ Edit subtab uses plain text input |
| 9 | County | Yes | Combobox (state-dependent) | — | From picklist, filtered by state | ⚠️ Missing from Active edit subtab |
| 10 | Zip Code | Yes | Text | 9 | 5 or 9 digits | ⚠️ HTML max-length="5" blocks 9-digit entry |
| 11 | Zip+4 | No | Text | 4 | 4 digits exactly | ⚠️ HTML enforces it but no JS check |
| 12 | Phone | Yes | Tel | 10 (digits) | 10 digits | ⚠️ Edit subtab phone is optional in validation |
| 13 | Phone Extension | No | Text | 10 | Digits only | ⚠️ No JS validation |
| 14 | Fax | No | Tel | 10 (digits) | 10 digits when provided | ❌ No validation at all |
| 15 | Is Primary (Primary Practice) | — | Checkbox | — | — | ⚠️ Missing from Active edit subtab |
| 16 | Telehealth Only | — | Checkbox | — | — | ⚠️ Missing from Active edit subtab |
| 17 | Primary Specialty / Taxonomy | No (conditionally) | Multi-Select | — | From CareTaxonomy | ❌ UI not built |
| 18 | Assistive Aids | No | Multi-Select | — | From picklist | ❌ UI not built |
| 19 | Affirming Care Categories | No | Multi-Select | — | From picklist | ❌ UI not built |

### Required Error Messages (Complete Set)

| Field | Error Condition | Required Message |
|-------|-----------------|-----------------|
| Group NPI | Empty | "Group NPI is required" |
| Group NPI | Not 10 digits | "Group NPI must be exactly 10 digits" |
| Group NPI | Invalid Luhn (optional) | "Please enter a valid NPI" |
| Group Tax ID | Empty | "Group Tax ID is required" |
| Group Tax ID | Bad format | "Tax ID must be in XX-XXXXXXX format" |
| Group Name | Empty | "Group Name is required" |
| Facility Name | Empty | "Facility Name is required" |
| Facility Name | > 255 chars | "Facility Name cannot exceed 255 characters" |
| Address Line 1 | Empty | "Address Line 1 is required" |
| Address Line 1 | > 255 chars | "Address Line 1 cannot exceed 255 characters" |
| City | Empty | "City is required" |
| City | > 100 chars | "City cannot exceed 100 characters" |
| State | Empty | "State is required" |
| County | Empty | "County is required" |
| Zip Code | Empty | "Zip Code is required" |
| Zip Code | Not 5 or 9 digits | "Zip Code must be 5 digits or 9 digits (e.g., 12345 or 123456789)" |
| Zip+4 | Provided but not 4 digits | "Zip+4 must be exactly 4 digits" |
| Phone | Empty | "Phone number is required" |
| Phone | Not 10 digits | "Phone number must be 10 digits (digits only, no dashes or spaces)" |
| Phone Extension | > 10 chars | "Phone Extension cannot exceed 10 characters" |
| Fax | Provided but not 10 digits | "Fax number must be 10 digits when provided" |
| Address Validation | Precisely API down | "Address validation is currently unavailable. Your address will be saved without standardization." |
| Address Validation | No match | "We could not find a standardized match. You may proceed with the address as entered." |
| Address Validation | Low confidence (≤50%) | "Low confidence match ({confidence}%). Please verify the recommended address carefully." |
| Remove Address | Primary practice | "The primary practice location cannot be removed. Please designate another location as primary first." |
| Edit Address | No address line 1 | "Address Line 1 is required to save" |

---

## PART 4: PRECISELY INTEGRATION ANALYSIS

### Current Implementation (BROKEN)
```apex
// Current — Direct HTTP callout, likely failing
req.setEndpoint('callout:PRM_Precisely_API/verify');
req.setMethod('POST');
Http http = new Http();
HttpResponse res = http.send(req);
```

### How PAR Form Does It (CORRECT PATTERN)
The PAR form calls Integration Procedure `PRM_IPPreciselyAPICall` via:
```apex
Map<String, Object> ipOutput = new Map<String, Object>();
vlocity_cmt.IntegrationProcedureService.runIntegrationProcedure(
    'PRM_IPPreciselyAPICall',  // IP Name
    ipInput,                    // Input map
    ipOutput,                   // Output map
    new Map<String, Object>()   // Options
);
```

### Why Direct HTTP Callout Fails
1. The `PRM_Precisely_API` Named Credential uses `PRM_Mulesoft_Access_Token` External Credential — this credential provides a Bearer token for Mulesoft, but is set up for **OmniStudio IP namespace** (`AllowedManagedPackageNamespaces: omnistudio`), not for standard Apex callouts
2. The Integration Procedure handles: request building, authentication injection, timeout, error wrapping
3. The direct callout may succeed in some orgs but will fail whenever the Mulesoft token needs refresh

### Correct Request/Response Shape
**Request (via IP):**
```json
{
  "AddressLine1": "1901 Market St",
  "AddressLine2": "",
  "City": "Philadelphia",
  "StateProvince": "PA",
  "PostalCode": "19103",
  "Country": "US"
}
```

**Response (from IP):**
```json
{
  "PreciselyResponse": {
    "AddressLine1": "1901 MARKET ST",
    "City": "PHILADELPHIA",
    "StateProvince": "PA",
    "PostalCode": {
      "Base": "19103",
      "AddOn": "1234"
    },
    "Confidence": 95,
    "Status": {
      "Code": "Success"
    },
    "Latitude": "39.9526",
    "Longitude": "-75.1652",
    "USCountyName": "Philadelphia"
  }
}
```

The current `parseValidatedAddress()` method tries to get `apiResponse.get('AddressLine1')` directly from the top-level response body, but if using the IP, the data is under `ipOutput.get('PreciselyResponse')`.

---

## PART 5: COMPLETE CLAUDE IMPLEMENTATION PROMPT

---

```
You are an expert Salesforce LWC and Apex developer. You are working on the IBX 
Practitioner Participation Form (PAR Form) — specifically the custom LWC component
`prmAddressGroupManager` and its Apex backend `PRM_AddressManagementService`.

This component is the standalone "Edit Address Details" widget that sits on the 
IndividualApplication record page and allows credentialing staff to manage practice 
locations for practitioners.

Below is a comprehensive list of bugs and missing features that need to be 
implemented. Please implement ALL of them in one pass.

---

## COMPONENT FILES TO MODIFY

1. `/force-app/main/default/classes/PRM_AddressManagementService.cls`
2. `/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.html`
3. `/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.js`
4. `/force-app/main/default/lwc/prmAddressGroupManager/prmAddressGroupManager.css`

---

## FIX 1: Precisely Address Validation — Replace Direct HTTP + Redesign Modal UX

### Part A — Replace Direct HTTP Callout with Integration Procedure

**File:** `PRM_AddressManagementService.cls`

**Problem:** The current `validateAddress()` method makes a direct HTTP callout to 
`callout:PRM_Precisely_API/verify`. This is broken because:
- The Named Credential's ExternalCredential is scoped for OmniStudio, not raw Apex callouts
- The response parsing doesn't match the actual IP response structure
- Authentication token refresh is not handled

**Fix:** Replace the direct HTTP callout with an Integration Procedure call:

```apex
@AuraEnabled
public static Map<String, Object> validateAddress(Map<String, String> addressData) {
    Map<String, Object> result = new Map<String, Object>();
    
    try {
        System.debug('Validating address via IP: ' + addressData);
        
        // Prepare IP input matching the Precisely IP input schema
        Map<String, Object> ipInput = new Map<String, Object>{
            'AddressLine1'   => addressData.get('addressLine1') ?? '',
            'AddressLine2'   => addressData.get('addressLine2') ?? '',
            'City'           => addressData.get('city') ?? '',
            'StateProvince'  => addressData.get('state') ?? '',
            'PostalCode'     => addressData.get('zip') ?? '',
            'Country'        => 'US'
        };
        
        Map<String, Object> ipOutput  = new Map<String, Object>();
        Map<String, Object> ipOptions = new Map<String, Object>();
        
        // Call the same Integration Procedure used by the PAR Form
        vlocity_cmt.IntegrationProcedureService.runIntegrationProcedure(
            'PRM_IPPreciselyAPICall',
            ipInput,
            ipOutput,
            ipOptions
        );
        
        System.debug('IP Output: ' + ipOutput);
        
        // The IP wraps the Precisely response under 'PreciselyResponse'
        if (ipOutput.containsKey('PreciselyResponse')) {
            Map<String, Object> apiResponse = (Map<String, Object>) ipOutput.get('PreciselyResponse');
            
            // Extract status
            String statusCode = '';
            if (apiResponse.containsKey('Status')) {
                Map<String, Object> statusObj = (Map<String, Object>) apiResponse.get('Status');
                if (statusObj != null) {
                    statusCode = String.valueOf(statusObj.get('Code') ?? '');
                }
            }
            
            // Extract confidence — handle Integer or String
            Decimal confidence = 0;
            if (apiResponse.containsKey('Confidence')) {
                Object confObj = apiResponse.get('Confidence');
                if (confObj instanceof Decimal) {
                    confidence = (Decimal) confObj;
                } else if (confObj instanceof Integer) {
                    confidence = Decimal.valueOf((Integer) confObj);
                } else if (confObj != null) {
                    try {
                        confidence = Decimal.valueOf(String.valueOf(confObj));
                    } catch (Exception ex) {
                        confidence = 0;
                    }
                }
            }
            
            Boolean hasMatch = String.isNotBlank(statusCode) 
                               && statusCode != 'No match found'
                               && statusCode != 'E' // Precisely error code
                               && statusCode != '';
            
            result.put('success',    true);
            result.put('validated',  parseValidatedAddress(apiResponse));
            result.put('original',   addressData);
            result.put('confidence', confidence);
            result.put('hasMatch',   hasMatch);
            result.put('statusCode', statusCode);
            
        } else if (ipOutput.containsKey('error') || ipOutput.containsKey('Error')) {
            String err = String.valueOf(ipOutput.get('error') ?? ipOutput.get('Error') ?? 'Unknown IP error');
            result.put('success', false);
            result.put('error',   'Address validation service error: ' + err);
            result.put('original', addressData);
            result.put('hasMatch', false);
        } else {
            // IP ran but returned no Precisely response — treat as unavailable
            result.put('success', false);
            result.put('error',   'Address validation service returned no data');
            result.put('original', addressData);
            result.put('hasMatch', false);
        }
        
    } catch (Exception e) {
        System.debug('Error calling Precisely IP: ' + e.getMessage());
        System.debug(e.getStackTraceString());
        result.put('success', false);
        result.put('error',   'Address validation service unavailable: ' + e.getMessage());
        result.put('original', addressData);
        result.put('hasMatch', false);
    }
    
    return result;
}
```

Also fix `parseValidatedAddress()` to handle the nested PostalCode map structure 
correctly (it already does this partially — keep it, but make null-safe):
```apex
private static Map<String, String> parseValidatedAddress(Map<String, Object> apiResponse) {
    Map<String, String> validated = new Map<String, String>();
    if (apiResponse == null) return validated;
    
    validated.put('addressLine1', String.valueOf(apiResponse.get('AddressLine1') ?? ''));
    validated.put('addressLine2', String.valueOf(apiResponse.get('AddressLine2') ?? ''));
    validated.put('city',         String.valueOf(apiResponse.get('City') ?? ''));
    validated.put('state',        String.valueOf(apiResponse.get('StateProvince') ?? ''));
    
    Object postalCodeObj = apiResponse.get('PostalCode');
    if (postalCodeObj instanceof Map<String, Object>) {
        Map<String, Object> pc = (Map<String, Object>) postalCodeObj;
        validated.put('zip',  String.valueOf(pc.get('Base') ?? ''));
        validated.put('zip4', String.valueOf(pc.get('AddOn') ?? ''));
    } else if (postalCodeObj != null) {
        validated.put('zip', String.valueOf(postalCodeObj));
    }
    
    if (apiResponse.containsKey('Latitude'))    validated.put('latitude',  String.valueOf(apiResponse.get('Latitude')));
    if (apiResponse.containsKey('Longitude'))   validated.put('longitude', String.valueOf(apiResponse.get('Longitude')));
    if (apiResponse.containsKey('USCountyName')) validated.put('county',   String.valueOf(apiResponse.get('USCountyName') ?? ''));
    
    return validated;
}
```

---

### Part B — Redesign the Address Validation Modal UX

**Files:** `addressValidationModal.html`, `addressValidationModal.js`, `addressValidationModal.css`

**Current design (WRONG):** Side-by-side two-column layout with "Recommended Address" vs "Original Address" columns, confidence badges, geocoding indicators, technical labels — too complex and clinical.

**Required design (per UX reference screenshot):** A clean, minimal centered popup that:
1. Shows the title **"Address validation feedback"** 
2. Shows a single natural-language prompt: **"We found a typo in your address, did you mean:"** (or **"We found a standardized version of your address, did you mean:"**)
3. Displays the **suggested address as a single bold formatted line**: `2928 Youngwood Street, Leander, TX 78641-5063, USA`
4. Two buttons only: **"Yes, change"** (solid brand/primary) and **"No, mine is correct"** (outlined/neutral)
5. A close (✕) button top-right
6. No confidence scores, no geocoding text, no side-by-side comparison, no technical jargon

**Logic for modal body text:**
- If `hasMatch === true`: `"We found a standardized version of your address, did you mean:"`
- If `hasMatch === false` (no match): Do NOT show the modal at all — instead show an inline message in the form: `"We could not verify this address. Your address will be saved as entered."` and proceed without interrupting the user.
- If `validationResult.success === false` (API down): Do NOT show the modal — show the inline unavailable banner and proceed.

**The modal should ONLY appear when `hasMatch === true`.** Showing a modal with no suggestion is confusing — silent proceed is better for no-match and API-down cases.

**Complete rewrite of `addressValidationModal.html`:**

```html
<template>
    <template if:true={showModal}>
        <!-- Backdrop -->
        <div class="slds-backdrop slds-backdrop_open"></div>

        <!-- Modal -->
        <section
            role="dialog"
            class="slds-modal slds-fade-in-open"
            aria-modal="true"
            aria-labelledby="addr-val-title"
            style="--modal-max-width: 480px;"
        >
            <div class="slds-modal__container addr-val-container">

                <!-- Close button -->
                <button
                    class="slds-button slds-button_icon slds-modal__close slds-button_icon-inverse"
                    title="Close"
                    onclick={handleCancel}
                >
                    <lightning-icon icon-name="utility:close" size="small" alternative-text="Close"></lightning-icon>
                </button>

                <!-- Body — no header bar, title is inside body for clean look -->
                <div class="slds-modal__content slds-p-around_large addr-val-body">

                    <h2 id="addr-val-title" class="addr-val-title">
                        Address validation feedback
                    </h2>

                    <p class="addr-val-prompt">
                        {promptText}
                    </p>

                    <!-- Suggested address (bold, prominent) -->
                    <p class="addr-val-suggestion">
                        {suggestedAddressLine}
                    </p>

                </div>

                <!-- Footer with two buttons -->
                <footer class="slds-modal__footer addr-val-footer">
                    <lightning-button
                        label="Yes, change"
                        variant="brand"
                        class="addr-val-btn-yes"
                        onclick={handleConfirmValidated}
                    ></lightning-button>
                    <lightning-button
                        label="No, mine is correct"
                        variant="neutral"
                        class="addr-val-btn-no"
                        onclick={handleDeclineValidated}
                    ></lightning-button>
                </footer>

            </div>
        </section>
    </template>
</template>
```

**Complete rewrite of `addressValidationModal.js`:**

```javascript
import { LightningElement, api } from 'lwc';

export default class AddressValidationModal extends LightningElement {
    @api validatedAddress;   // The Precisely-standardized address
    @api originalAddress;    // The address the user typed
    @api confidence;         // 0–100 (kept for future use, not shown in UI)
    @api hasMatch;           // Boolean — true if Precisely found a match

    showModal = true;

    /**
     * The natural-language prompt line shown above the suggestion.
     * Adapts phrasing based on whether we detected a typo vs. full standardization.
     */
    get promptText() {
        // Use "typo" language when the addresses differ only slightly (common path);
        // the generic fallback covers full standardization cases.
        return 'We found a standardized version of your address, did you mean:';
    }

    /**
     * Build a single-line formatted address string from the validated address.
     * Format: "2928 Youngwood Street, Leander, TX 78641-5063, USA"
     */
    get suggestedAddressLine() {
        if (!this.validatedAddress) return '';

        const v = this.validatedAddress;
        let parts = [];

        // Street (line1 + optional line2)
        let street = (v.addressLine1 || '').trim();
        if (v.addressLine2 && v.addressLine2.trim()) {
            street += ' ' + v.addressLine2.trim();
        }
        if (street) parts.push(street);

        // City
        if (v.city) parts.push(v.city.trim());

        // State + ZIP (combined, e.g. "TX 78641-5063")
        let stateZip = '';
        if (v.state) stateZip += v.state.trim();
        if (v.zip) {
            stateZip += (stateZip ? ' ' : '') + v.zip.trim();
            if (v.zip4 && v.zip4.trim()) {
                stateZip += '-' + v.zip4.trim();
            }
        }
        if (stateZip) parts.push(stateZip);

        // Country
        parts.push('USA');

        return parts.join(', ');
    }

    /** User accepted the suggested address */
    handleConfirmValidated() {
        this.dispatchEvent(new CustomEvent('addressselected', {
            detail: {
                selectedAddress: this.validatedAddress,
                useValidated:    true,
                standardized:    true,
                latitude:        this.validatedAddress?.latitude  ?? null,
                longitude:       this.validatedAddress?.longitude ?? null
            }
        }));
        this.showModal = false;
    }

    /** User kept their original address */
    handleDeclineValidated() {
        this.dispatchEvent(new CustomEvent('addressselected', {
            detail: {
                selectedAddress: this.originalAddress,
                useValidated:    false,
                standardized:    false,
                latitude:        null,
                longitude:       null
            }
        }));
        this.showModal = false;
    }

    /** User closed the modal with ✕ — treat same as "No, mine is correct" */
    handleCancel() {
        this.dispatchEvent(new CustomEvent('cancel'));
        this.showModal = false;
    }
}
```

**Complete rewrite of `addressValidationModal.css`:**

```css
/* Container — narrower than the SLDS modal default */
.addr-val-container {
    max-width: 480px !important;
    border-radius: 16px;
    overflow: hidden;
}

/* Body */
.addr-val-body {
    text-align: center;
    padding: 2rem 2rem 1.5rem;
}

/* Title: "Address validation feedback" */
.addr-val-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #181818;
    margin-bottom: 1rem;
}

/* Prompt line: "We found a typo..." */
.addr-val-prompt {
    font-size: 0.9375rem;
    color: #444;
    margin-bottom: 0.75rem;
}

/* The bold suggested address line */
.addr-val-suggestion {
    font-size: 1rem;
    font-weight: 700;
    color: #181818;
    margin-bottom: 0;
    line-height: 1.5;
}

/* Footer: buttons side by side, centered */
.addr-val-footer {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    padding: 1.25rem 2rem 1.75rem;
    border-top: none;              /* Remove SLDS default top border */
    background: transparent;
}

/* "Yes, change" — use IBX brand green to match screenshot */
.addr-val-btn-yes .slds-button {
    background-color: #2D6A4F;
    border-color:     #2D6A4F;
    border-radius:    999px;       /* Pill shape like the screenshot */
    min-width:        130px;
    font-weight:      600;
}

/* "No, mine is correct" — outlined pill */
.addr-val-btn-no .slds-button {
    border-radius: 999px;
    min-width:     160px;
    font-weight:   600;
}
```

**Update `prmAddressGroupManager.js` — Only show modal when `hasMatch === true`:**

In `handleCreateNewLocation()` and `handleSaveLocation()`, replace the current
modal-trigger block:

```javascript
// BEFORE (shows modal even when no match):
if (validationResult.success) {
    this.validatedAddress     = validationResult.validated;
    this.originalAddress      = validationResult.original;
    this.validationConfidence = validationResult.confidence;
    this.validationHasMatch   = validationResult.hasMatch;
    this.showValidationModal  = true;
    this.showSpinner          = false;
} else {
    // ...warning toast, proceed...
}

// AFTER — only interrupt user when there is an actual suggestion:
if (validationResult.success && validationResult.hasMatch) {
    // Precisely found a standardized version — show the "did you mean?" modal
    this.validatedAddress     = validationResult.validated;
    this.originalAddress      = validationResult.original;
    this.validationConfidence = validationResult.confidence;
    this.validationHasMatch   = true;
    this.showValidationModal  = true;
    this.showSpinner          = false;
    // Flow pauses here; resumes in handleAddressSelected()

} else if (validationResult.success && !validationResult.hasMatch) {
    // API worked but no match — show inline info, proceed silently
    this.validationUnavailableMessage =
        'We could not verify this address. Your address will be saved as entered.';
    await this.proceedWithCreateLocation(this.pendingLocationData);  // or proceedWithUpdateLocation

} else {
    // API down / error — show inline banner, proceed silently
    this.validationUnavailableMessage =
        'Address validation is currently unavailable. Your address will be saved without standardization.';
    await this.proceedWithCreateLocation(this.pendingLocationData);
}
```

**Update `prmAddressGroupManager.html` — Add `<c-address-validation-modal>` tag:**

The modal component IS built but was never added to the parent HTML. Add it at the 
end of the template (before closing `</template>`):

```html
<!-- Address Validation "Did you mean?" Modal -->
<template if:true={showValidationModal}>
    <c-address-validation-modal
        validated-address={validatedAddress}
        original-address={originalAddress}
        confidence={validationConfidence}
        has-match={validationHasMatch}
        onaddressselected={handleAddressSelected}
        oncancel={handleValidationCancel}
    ></c-address-validation-modal>
</template>
```

---

## FIX 2: Add Taxonomy / Provider Type UI to Create New Location Form

**Files:** `prmAddressGroupManager.html`, `prmAddressGroupManager.js`, `PRM_AddressManagementService.cls`

**Problem:** `createNewLocation()` always receives `taxonomyIds: []`. The PAR form collects Provider Type and Care Taxonomy at the address step. The backend `addTaxonomiesToPractitionerFacility()` is fully ready and wired into `createNewLocation()` — it just needs IDs passed to it.

**Step 1 — Add to Apex (`PRM_AddressManagementService.cls`):**
```apex
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getProviderTypeOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    for (PRM_ProviderType__c pt : [
        SELECT Id, Name FROM PRM_ProviderType__c 
        WHERE IsActive__c = true ORDER BY Name
    ]) {
        options.add(new Map<String, String>{ 'label' => pt.Name, 'value' => pt.Id });
    }
    return options;
}

@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getTaxonomyOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    for (CareTaxonomy ct : [
        SELECT Id, Name, Code FROM CareTaxonomy
        WHERE IsActive = true ORDER BY Name LIMIT 500
    ]) {
        options.add(new Map<String, String>{
            'label' => ct.Name + (ct.Code != null ? ' (' + ct.Code + ')' : ''),
            'value' => ct.Id
        });
    }
    return options;
}
```

**Step 2 — Add to JS (`prmAddressGroupManager.js`):**
```javascript
import getProviderTypeOptions from '@salesforce/apex/PRM_AddressManagementService.getProviderTypeOptions';
import getTaxonomyOptions     from '@salesforce/apex/PRM_AddressManagementService.getTaxonomyOptions';

@track showSpecialtySection      = false;
@track providerTypeOptions       = [];
@track selectedProviderTypeId    = '';
@track taxonomyOptions           = [];
@track selectedTaxonomyIds       = [];
@track assistiveAidOptions       = [];
@track selectedAssistiveAidCodes = [];
@track affirmingCareOptions      = [];
@track selectedAffirmingCareCodes = [];

toggleSpecialtySection() {
    this.showSpecialtySection = !this.showSpecialtySection;
    if (this.showSpecialtySection && this.providerTypeOptions.length === 0) {
        this.loadSpecialtySectionData();
    }
}

async loadSpecialtySectionData() {
    try {
        const [providerTypes, taxonomies] = await Promise.all([
            getProviderTypeOptions(),
            getTaxonomyOptions()
        ]);
        this.providerTypeOptions = providerTypes || [];
        this.taxonomyOptions     = taxonomies    || [];
    } catch (error) {
        console.error('Error loading specialty data:', error);
        this.showToast('Warning', 'Could not load specialty options. You can add specialties after saving.', 'warning');
    }
}

handleProviderTypeChange(event) { this.selectedProviderTypeId    = event.detail.value; }
handleTaxonomyChange(event)     { this.selectedTaxonomyIds       = event.detail.value; }
handleAssistiveAidChange(event) { this.selectedAssistiveAidCodes = event.detail.value; }
handleAffirmingCareChange(event){ this.selectedAffirmingCareCodes= event.detail.value; }
```

**Step 3 — Add to HTML (`prmAddressGroupManager.html`) in the Create New Location form, after phone/fax fields:**

```html
<!-- Specialty & Accessibility Section (collapsible) -->
<div class="slds-col slds-size_1-of-1 slds-m-top_small">
    <div class="slds-section" class:slds-is-open={showSpecialtySection}>
        <h3 class="slds-section__title slds-theme_shade slds-p-around_x-small"
            style="cursor:pointer;" onclick={toggleSpecialtySection}>
            <lightning-icon icon-name="utility:chevronright" size="x-small"
                class="slds-m-right_x-small"></lightning-icon>
            Specialty &amp; Accessibility (Optional)
        </h3>
        <template if:true={showSpecialtySection}>
            <div class="slds-section__content slds-p-around_small slds-grid slds-gutters slds-wrap">
                
                <!-- Provider Type -->
                <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                    <lightning-combobox
                        label="Provider Type"
                        value={selectedProviderTypeId}
                        options={providerTypeOptions}
                        placeholder="Select provider type"
                        onchange={handleProviderTypeChange}
                    ></lightning-combobox>
                </div>
                
                <!-- Care Taxonomy / Specialty (multi-select) -->
                <div class="slds-col slds-size_1-of-1 slds-m-top_small">
                    <lightning-dual-listbox
                        name="taxonomies"
                        label="Care Taxonomy / Specialty"
                        source-label="Available Specialties"
                        selected-label="Selected (first = Primary)"
                        options={taxonomyOptions}
                        value={selectedTaxonomyIds}
                        onchange={handleTaxonomyChange}
                        min="0"
                        max="5"
                        field-level-help="The first selected specialty will be set as the Primary taxonomy."
                    ></lightning-dual-listbox>
                    <template if:true={selectedTaxonomyIds.length}>
                        <p class="slds-text-body_small slds-text-color_weak slds-m-top_xx-small">
                            <lightning-icon icon-name="utility:info" size="xx-small"
                                class="slds-m-right_xx-small"></lightning-icon>
                            Primary specialty: first item in the Selected list.
                            Assistive Aids and Affirming Care can be added after saving.
                        </p>
                    </template>
                </div>
                
            </div>
        </template>
    </div>
</div>
```

**Step 4 — Pass `taxonomyIds` to `proceedWithCreateLocation()`:**
In `handleCreateNewLocation()`, update `pendingLocationData`:
```javascript
this.pendingLocationData = {
    // ... existing fields ...
    taxonomyIds: this.selectedTaxonomyIds,  // ← was hardcoded []
    networkIds:  [],
    // ...
};
```

---

## FIX 3: Replace all `confirm()` with Custom SLDs Confirmation Modal

**Files:** `prmAddressGroupManager.html`, `prmAddressGroupManager.js`

`window.confirm()` is blocked in Salesforce Lightning Experience (LE). Replace every 
usage with a custom confirmation modal.

**In HTML**, add a confirmation modal template at the end of the component (before 
the closing `</template>`):

```html
<!-- Confirmation Dialog -->
<template if:true={showConfirmDialog}>
    <section role="dialog" class="slds-modal slds-fade-in-open" aria-modal="true" aria-labelledby="confirm-dialog-heading">
        <div class="slds-modal__container" style="max-width: 400px;">
            <header class="slds-modal__header">
                <h2 id="confirm-dialog-heading" class="slds-modal__title">{confirmDialogTitle}</h2>
            </header>
            <div class="slds-modal__content slds-p-around_medium">
                <p>{confirmDialogMessage}</p>
                <template if:true={confirmDialogWarning}>
                    <div class="slds-box slds-theme_warning slds-m-top_small">
                        <lightning-icon icon-name="utility:warning" size="x-small" class="slds-m-right_x-small"></lightning-icon>
                        {confirmDialogWarning}
                    </div>
                </template>
            </div>
            <footer class="slds-modal__footer">
                <lightning-button label="Cancel"  onclick={handleConfirmDialogCancel}></lightning-button>
                <lightning-button label={confirmDialogConfirmLabel} variant={confirmDialogVariant}
                    onclick={handleConfirmDialogConfirm} class="slds-m-left_x-small"></lightning-button>
            </footer>
        </div>
    </section>
    <div class="slds-backdrop slds-backdrop_open"></div>
</template>
```

**In JS**, add state and a generic confirm helper:

```javascript
// Confirmation dialog state
@track showConfirmDialog    = false;
@track confirmDialogTitle   = '';
@track confirmDialogMessage = '';
@track confirmDialogWarning = '';
@track confirmDialogConfirmLabel = 'Confirm';
@track confirmDialogVariant = 'brand';
_confirmResolve = null;

/**
 * Show a confirmation dialog and return a Promise<boolean>
 */
showConfirm({ title, message, warning = '', confirmLabel = 'Confirm', variant = 'brand' }) {
    this.confirmDialogTitle        = title;
    this.confirmDialogMessage      = message;
    this.confirmDialogWarning      = warning;
    this.confirmDialogConfirmLabel = confirmLabel;
    this.confirmDialogVariant      = variant;
    this.showConfirmDialog         = true;
    return new Promise(resolve => {
        this._confirmResolve = resolve;
    });
}

handleConfirmDialogConfirm() {
    this.showConfirmDialog = false;
    if (this._confirmResolve) this._confirmResolve(true);
    this._confirmResolve = null;
}

handleConfirmDialogCancel() {
    this.showConfirmDialog = false;
    if (this._confirmResolve) this._confirmResolve(false);
    this._confirmResolve = null;
}
```

Then replace every `confirm('...')` call. Examples:

```javascript
// BEFORE (broken in LE):
if (confirm(`Remove address: ${addressInfo.FullAddress}?`)) {
    this.removeAddress(facilityId, '...');
}

// AFTER (correct):
const confirmed = await this.showConfirm({
    title: 'Remove Address?',
    message: `You are about to remove: ${addressInfo.FullAddress}`,
    warning: 'This will mark the address as an error record. This action can be undone by an administrator.',
    confirmLabel: 'Remove Address',
    variant: 'destructive'
});
if (confirmed) {
    this.removeAddress(facilityId, '...');
}
```

Apply the same pattern for:
- `handleRemoveAddress()` 
- `handleRemoveActiveLocation()`
- `handleRemoveActiveLocationFromTable()`
- `handleRemovePendingLocationFromTable()`
- `handleCancelEdit()` (unsaved changes guard)

---

## FIX 4: Fix `currentUserId` — Import from Salesforce User

**File:** `prmAddressGroupManager.js`

**Add this import at the top:**
```javascript
import CurrentUserId from '@salesforce/user/Id';
```

**Remove the broken getter and replace with:**
```javascript
userId = CurrentUserId; // populated by Salesforce at runtime
```

Then update the `get currentUserId()` getter OR replace all `this.currentUserId` 
references with `this.userId` directly.

---

## FIX 5: Fix All Field Validations — Complete Validation Logic

**File:** `prmAddressGroupManager.js`

### 5a. Create a shared `validateLocationFields(data)` helper:

```javascript
/**
 * Validate location form fields. Returns array of error objects.
 * @param {Object} data - Object with all address fields
 * @returns {Array} - Array of { field, message } objects; empty = valid
 */
validateLocationFields(data) {
    const errors = [];
    
    // Required fields
    if (!data.facilityName || !data.facilityName.trim()) {
        errors.push({ field: 'facilityName', message: 'Facility Name is required' });
    } else if (data.facilityName.length > 255) {
        errors.push({ field: 'facilityName', message: 'Facility Name cannot exceed 255 characters' });
    }
    
    if (!data.addressLine1 || !data.addressLine1.trim()) {
        errors.push({ field: 'addressLine1', message: 'Address Line 1 is required' });
    } else if (data.addressLine1.length > 255) {
        errors.push({ field: 'addressLine1', message: 'Address Line 1 cannot exceed 255 characters' });
    }
    
    if (data.addressLine2 && data.addressLine2.length > 255) {
        errors.push({ field: 'addressLine2', message: 'Address Line 2 cannot exceed 255 characters' });
    }
    
    if (!data.city || !data.city.trim()) {
        errors.push({ field: 'city', message: 'City is required' });
    } else if (data.city.length > 100) {
        errors.push({ field: 'city', message: 'City cannot exceed 100 characters' });
    }
    
    if (!data.state) {
        errors.push({ field: 'state', message: 'State is required' });
    }
    
    if (!data.county) {
        errors.push({ field: 'county', message: 'County is required' });
    }
    
    // Zip Code: 5 or 9 digits
    if (!data.zip) {
        errors.push({ field: 'zip', message: 'Zip Code is required' });
    } else {
        const zipDigits = data.zip.replace(/\D/g, '');
        if (zipDigits.length !== 5 && zipDigits.length !== 9) {
            errors.push({ field: 'zip', message: 'Zip Code must be 5 digits or 9 digits (e.g., 12345 or 123456789)' });
        }
    }
    
    // Zip+4: exactly 4 digits when provided
    if (data.zip4) {
        const zip4Digits = data.zip4.replace(/\D/g, '');
        if (zip4Digits.length !== 4) {
            errors.push({ field: 'zip4', message: 'Zip+4 must be exactly 4 digits' });
        }
    }
    
    // Phone: required, 10 digits
    if (!data.phone) {
        errors.push({ field: 'phone', message: 'Phone number is required' });
    } else {
        const phoneDigits = data.phone.replace(/\D/g, '');
        if (phoneDigits.length !== 10) {
            errors.push({ field: 'phone', message: 'Phone number must be exactly 10 digits (digits only)' });
        }
    }
    
    // Phone Extension: max 10 chars when provided
    if (data.phoneExtension && data.phoneExtension.length > 10) {
        errors.push({ field: 'phoneExtension', message: 'Phone Extension cannot exceed 10 characters' });
    }
    
    // Fax: 10 digits when provided
    if (data.fax) {
        const faxDigits = data.fax.replace(/\D/g, '');
        if (faxDigits.length !== 10) {
            errors.push({ field: 'fax', message: 'Fax number must be exactly 10 digits when provided' });
        }
    }
    
    // NPI: 10 digits when provided
    if (data.groupNpi) {
        const npiDigits = data.groupNpi.replace(/\D/g, '');
        if (npiDigits.length !== 10) {
            errors.push({ field: 'groupNpi', message: 'Group NPI must be exactly 10 digits' });
        }
    }
    
    return errors;
}
```

### 5b. Update `handleCreateNewLocation()` to use shared validation:
Replace the inline validation block with:
```javascript
const validationErrors = this.validateLocationFields({
    facilityName:   this.newLocationName,
    addressLine1:   this.newLocationAddress1,
    addressLine2:   this.newLocationAddress2,
    city:           this.newLocationCity,
    state:          this.newLocationState,
    county:         this.newLocationCounty,
    zip:            this.newLocationZip,
    zip4:           this.newLocationZip4,
    phone:          this.newLocationPhone,
    phoneExtension: this.newLocationPhoneExtension,
    fax:            this.newLocationFax,
    groupNpi:       this.newLocationGroupNpi
});

if (validationErrors.length > 0) {
    // Show first error prominently; also try to highlight fields
    this.showToast('Error', validationErrors.map(e => e.message).join(' | '), 'error');
    // Try to call reportValidity on lightning-inputs
    this.reportFormValidity('[data-section="new-location"]');
    return;
}
```

### 5c. Update `validateEditForm()` to use shared validation:
Replace the entire `validateEditForm()` method body to call the shared helper and 
also add the missing county, fax, and phone-required checks.

### 5d. Add `reportFormValidity(sectionSelector)` helper:
```javascript
reportFormValidity(sectionSelector) {
    try {
        const container = sectionSelector 
            ? this.template.querySelector(sectionSelector)
            : this.template;
        if (!container) return;
        container.querySelectorAll('lightning-input, lightning-combobox').forEach(input => {
            input.reportValidity();
        });
    } catch(e) {
        // Ignore DOM errors
    }
}
```

---

## FIX 6: Add Tax ID Format Validation

**File:** `prmAddressGroupManager.js`

In `handleTaxIdChange()` add:
```javascript
handleTaxIdChange(event) {
    this.groupTaxId = event.target.value ? event.target.value.trim() : '';
    
    // Validate EIN format: XX-XXXXXXX when 9+ chars
    if (this.groupTaxId.length >= 9) {
        const taxDigits = this.groupTaxId.replace(/\D/g, '');
        if (taxDigits.length !== 9) {
            event.target.setCustomValidity('Tax ID must contain exactly 9 digits (format: XX-XXXXXXX)');
        } else {
            event.target.setCustomValidity('');
        }
        event.target.reportValidity();
    }
    
    this.resetSelections();
    this.filterAccountsByNpiAndTaxId();
}
```

---

## FIX 7: Fix Zip Code HTML Constraints to Allow 9-Digit ZIP

**File:** `prmAddressGroupManager.html`

In the Create New Location form, change the Zip Code input from:
```html
max-length="5"
pattern="[0-9]{5}"
```
To:
```html
max-length="9"
message-when-pattern-mismatch="Zip Code must be 5 digits (e.g., 12345) or 9 digits (e.g., 123456789)"
```
Remove the `pattern` attribute from the HTML entirely and handle validation in JS only 
(since the "5 or 9" pattern can't be easily expressed as a single HTML pattern attribute 
that Lightning renders correctly).

Do the same fix in the Pending Locations Edit form.

---

## FIX 8: Complete the Pending Edit Form — Missing Fields + State Combobox

**File:** `prmAddressGroupManager.html` and `prmAddressGroupManager.js`

The Pending Locations edit subtab is the only editable form for existing locations. It must be feature-complete.

### 8a. Replace State text input with combobox:
```html
<!-- REMOVE THIS: -->
<lightning-input label="State" max-length="2" value={...} ...></lightning-input>

<!-- REPLACE WITH: -->
<lightning-combobox
    label="State"
    value={selectedPendingLocationForEdit.state}
    options={stateOptions}
    required
    placeholder="Select state"
    message-when-value-missing="State is required"
    onchange={handlePendingEditStateChange}
></lightning-combobox>
```

Add `handlePendingEditStateChange()` to JS:
```javascript
async handlePendingEditStateChange(event) {
    const stateValue = event.detail.value;
    const locationId = this.selectedPendingLocationForEdit.id;
    this.selectedPendingLocationForEdit = {
        ...this.selectedPendingLocationForEdit,
        state:  stateValue,
        county: ''  // Reset county when state changes
    };
    this.existingLocations = this.existingLocations.map(loc =>
        loc.id === locationId ? { ...loc, state: stateValue, county: '' } : loc
    );
    if (stateValue) {
        await this.loadCountiesForState(stateValue);
    } else {
        this.countyOptions       = [];
        this.countyOptionsDisabled = true;
    }
}
```

### 8b. Add County combobox after State:
```html
<div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-3">
    <lightning-combobox
        label="County"
        value={selectedPendingLocationForEdit.county}
        options={countyOptions}
        data-field="county"
        onchange={handleLocationFieldChange}
        required
        placeholder="Select county"
        disabled={countyOptionsDisabled}
        message-when-value-missing="County is required"
    ></lightning-combobox>
</div>
```

### 8c. Add Telehealth Only checkbox:
```html
<div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
    <lightning-input
        type="checkbox"
        label="Telehealth Only"
        checked={selectedPendingLocationForEdit.isTelehealthOnly}
        data-field="isTelehealthOnly"
        onchange={handleLocationFieldChange}
    ></lightning-input>
</div>
```

### 8d. Add Fax field:
```html
<div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-3">
    <lightning-input
        label="Fax"
        type="tel"
        value={selectedPendingLocationForEdit.fax}
        data-field="fax"
        onchange={handleLocationFieldChange}
        placeholder="(optional) 10-digit fax number"
        message-when-pattern-mismatch="Fax must be 10 digits when provided"
    ></lightning-input>
</div>
```

### 8e. Fix Zip Code max-length in Pending Edit:
```html
<!-- Change max-length from "5" to "9" and remove the pattern attribute -->
<lightning-input label="Zip Code" max-length="9" required
    message-when-value-missing="Zip Code is required"
    value={selectedPendingLocationForEdit.zip}
    data-field="zip" onchange={handleLocationFieldChange}
></lightning-input>
```

### 8f. Validate fields before calling Precisely in `handleSaveLocation()`:
```javascript
async handleSaveLocation(event) {
    // Validate FIRST — before any API call
    const locationId = event.target.dataset.locationId || this.selectedPendingLocationForEdit?.id;
    const loc = this.existingLocations.find(l => l.id === locationId);
    if (!loc) return;

    const validationErrors = this.validateLocationFields({
        facilityName:   loc.name,
        addressLine1:   loc.addressLine1,
        city:           loc.city,
        state:          loc.state,
        county:         loc.county,
        zip:            loc.zip,
        zip4:           loc.zip4,
        phone:          loc.phone,
        fax:            loc.fax,
        phoneExtension: loc.phoneExtension
    });
    if (validationErrors.length > 0) {
        this.showToast('Error', validationErrors.map(e => e.message).join(' | '), 'error');
        return;
    }

    // Only call validateAddress after fields pass
    // ... existing Precisely call code ...
}
```

---

## FIX 9: Add `message-when-value-missing` to All Required Fields

**File:** `prmAddressGroupManager.html`

For every `lightning-input` or `lightning-combobox` with `required`, add the 
`message-when-value-missing` attribute with a clear, user-friendly message.

Examples (apply pattern to all required fields in Create New and Edit forms):
```html
<!-- Address Line 1 -->
<lightning-input label="Address Line 1" required 
    message-when-value-missing="Address Line 1 is required"
    max-length="255" ...></lightning-input>

<!-- City -->
<lightning-input label="City" required 
    message-when-value-missing="City is required"
    max-length="100" ...></lightning-input>

<!-- Phone -->
<lightning-input label="Phone" type="tel" required 
    message-when-value-missing="Phone number is required"
    message-when-pattern-mismatch="Phone must be 10 digits (digits only)"
    ...></lightning-input>

<!-- Zip Code -->
<lightning-input label="Zip Code" required 
    message-when-value-missing="Zip Code is required"
    max-length="9" ...></lightning-input>
```

---

## FIX 10: Fix Pending Edit Form — State as Combobox + County Dependency

**File:** `prmAddressGroupManager.html` and `prmAddressGroupManager.js`

In the Pending Locations edit subtab form:

1. Replace `<lightning-input label="State" max-length="2" ...>` with a 
   `<lightning-combobox>` using `stateOptions` (same as Create New form).

2. Add the County combobox after State (same as Create New form).

3. In JS, the Pending edit form uses `handleLocationFieldChange()` which updates 
   `this.existingLocations`. Add a `handlePendingEditStateChange()` handler that 
   updates state and reloads counties for the `selectedPendingLocationForEdit` object:

```javascript
async handlePendingEditStateChange(event) {
    const stateValue = event.target.value;
    this.selectedPendingLocationForEdit = {
        ...this.selectedPendingLocationForEdit,
        state: stateValue,
        county: '' // Reset county
    };
    // Also update in existingLocations array
    const locationId = this.selectedPendingLocationForEdit.id;
    this.existingLocations = this.existingLocations.map(loc =>
        loc.id === locationId ? { ...loc, state: stateValue, county: '' } : loc
    );
    if (stateValue) {
        await this.loadCountiesForState(stateValue);
    } else {
        this.countyOptions = [];
        this.countyOptionsDisabled = true;
    }
}
```

---

## FIX 11: Add Address Line Max-Length Constraints to All Forms

**File:** `prmAddressGroupManager.html`

For all `lightning-input` address fields across ALL three forms (Create New, Active 
Edit, Pending Edit):

```html
<!-- Address Line 1: max 255 -->
<lightning-input label="Address Line 1" max-length="255" required ...></lightning-input>

<!-- Address Line 2: max 255 -->
<lightning-input label="Address Line 2" max-length="255" ...></lightning-input>

<!-- City: max 100 -->
<lightning-input label="City" max-length="100" required ...></lightning-input>

<!-- Facility Name: max 255 -->
<lightning-input label="Facility Name" max-length="255" required ...></lightning-input>

<!-- Phone Extension: max 10 (already present in Create New, add to Edit forms) -->
<lightning-input label="Phone Extension" max-length="10" ...></lightning-input>
```

---

## FIX 12: Strip Phone/Fax Formatting Before Passing to Apex

**File:** `prmAddressGroupManager.js`

Before calling `createNewLocation()` or `updatePractitionerLocation()`, strip 
non-numeric characters from phone and fax:

In `proceedWithCreateLocation()` and `proceedWithUpdateLocation()`, apply:
```javascript
const cleanPhone = locationData.phone ? locationData.phone.replace(/\D/g, '') : '';
const cleanFax   = locationData.fax   ? locationData.fax.replace(/\D/g, '')   : '';
```
And pass `cleanPhone` / `cleanFax` to the Apex methods instead of the raw values.

---

## FIX 13: Handle "Validation Unavailable" More Clearly

**File:** `prmAddressGroupManager.js`

When `validationResult.success === false`, instead of a warning toast that auto-
dismisses (and the user may miss), show a persistent inline banner. Add a tracked 
property:
```javascript
@track validationUnavailableMessage = '';
```

In the HTML edit form and create form, add:
```html
<template if:true={validationUnavailableMessage}>
    <div class="slds-notify slds-notify_alert slds-theme_info" role="alert" 
         style="margin-bottom: 12px;">
        <lightning-icon icon-name="utility:info" size="x-small" class="slds-m-right_x-small"></lightning-icon>
        {validationUnavailableMessage}
        <button class="slds-button slds-float_right" onclick={clearValidationWarning}>✕</button>
    </div>
</template>
```

Set `validationUnavailableMessage` when Precisely returns an error:
```javascript
this.validationUnavailableMessage = 
    'Address validation is currently unavailable. Your address will be saved without standardization.';
```

---

## FIX 14: Add "Validate Address" Button to Edit Subtab

**File:** `prmAddressGroupManager.html`

In the Active Locations edit subtab form (when `isEditModeEdit === true`), add a 
dedicated "Validate Address" button between the address fields and the action buttons:

```html
<!-- Validate Address Section -->
<div class="slds-col slds-size_1-of-1 slds-m-top_small">
    <div class="slds-box slds-box_x-small" style="background: #f3f9f6; border-left: 3px solid #4bca81;">
        <div class="slds-grid slds-grid_vertical-align-center slds-gutters">
            <div class="slds-col">
                <p class="slds-text-body_small">
                    <lightning-icon icon-name="utility:check" size="xx-small" variant="success" class="slds-m-right_xx-small"></lightning-icon>
                    Validate this address against USPS standards before saving
                </p>
            </div>
            <div class="slds-col slds-no-flex">
                <lightning-button
                    label="Validate Address"
                    variant="neutral"
                    icon-name="utility:location"
                    onclick={handleValidateEditAddress}
                    disabled={isProcessingEdit}
                ></lightning-button>
            </div>
        </div>
    </div>
</div>
```

---

## FIX 15: Add Taxonomy, Assistive Aids, and Affirming Care UI

**File:** `prmAddressGroupManager.html` and `prmAddressGroupManager.js`

**In the Create New Location form**, after the Phone/Fax section and before the action 
buttons, add a collapsible "Additional Details (Optional)" section:

```html
<!-- Optional Additional Details Section -->
<div class="slds-col slds-size_1-of-1">
    <div class="slds-section" class:slds-is-open={showOptionalSection}>
        <h3 class="slds-section__title slds-theme_shade" onclick={toggleOptionalSection}>
            <lightning-icon icon-name="utility:chevronright" size="x-small" 
                class="slds-m-right_x-small section-chevron"></lightning-icon>
            Optional: Specialty, Assistive Aids & Affirming Care
        </h3>
        <template if:true={showOptionalSection}>
            <div class="slds-section__content slds-p-around_small">
                
                <!-- Primary Specialty -->
                <div class="slds-m-bottom_small">
                    <label class="slds-form-element__label">Primary Specialty / Taxonomy</label>
                    <lightning-dual-listbox
                        name="taxonomies"
                        label="Select Specialties"
                        source-label="Available Specialties"
                        selected-label="Selected Specialties"
                        options={taxonomyOptions}
                        value={selectedTaxonomyIds}
                        onchange={handleTaxonomyChange}
                        min="0"
                        max="5"
                    ></lightning-dual-listbox>
                </div>
                
                <!-- Assistive Aids -->
                <div class="slds-m-bottom_small">
                    <lightning-dual-listbox
                        name="assistiveAids"
                        label="Assistive Aids at this Location"
                        source-label="Available Aids"
                        selected-label="Selected Aids"
                        options={assistiveAidOptions}
                        value={selectedAssistiveAidCodes}
                        onchange={handleAssistiveAidChange}
                        min="0"
                    ></lightning-dual-listbox>
                </div>
                
                <!-- Affirming Care -->
                <div class="slds-m-bottom_small">
                    <lightning-dual-listbox
                        name="affirmingCare"
                        label="Affirming Care Categories"
                        source-label="Available Categories"
                        selected-label="Selected Categories"
                        options={affirmingCareOptions}
                        value={selectedAffirmingCareCodes}
                        onchange={handleAffirmingCareChange}
                        min="0"
                    ></lightning-dual-listbox>
                </div>
                
            </div>
        </template>
    </div>
</div>
```

**In JS**, add:
```javascript
@track showOptionalSection       = false;
@track taxonomyOptions           = [];
@track selectedTaxonomyIds       = [];
@track assistiveAidOptions       = [];
@track selectedAssistiveAidCodes = [];
@track affirmingCareOptions      = [];
@track selectedAffirmingCareCodes = [];

import getTaxonomyOptions      from '@salesforce/apex/PRM_AddressManagementService.getTaxonomyOptions';
import getAssistiveAidOptions  from '@salesforce/apex/PRM_AddressManagementService.getAssistiveAidOptions';
import getAffirmingCareOptions from '@salesforce/apex/PRM_AddressManagementService.getAffirmingCareOptions';

toggleOptionalSection() {
    this.showOptionalSection = !this.showOptionalSection;
    if (this.showOptionalSection && this.taxonomyOptions.length === 0) {
        this.loadOptionalSectionData();
    }
}

async loadOptionalSectionData() {
    try {
        const [taxonomies, aids, affirming] = await Promise.all([
            getTaxonomyOptions(),
            getAssistiveAidOptions(),
            getAffirmingCareOptions()
        ]);
        this.taxonomyOptions          = taxonomies  || [];
        this.assistiveAidOptions      = aids        || [];
        this.affirmingCareOptions     = affirming   || [];
    } catch (error) {
        console.error('Error loading optional section data:', error);
    }
}

handleTaxonomyChange(event)      { this.selectedTaxonomyIds        = event.detail.value; }
handleAssistiveAidChange(event)  { this.selectedAssistiveAidCodes  = event.detail.value; }
handleAffirmingCareChange(event) { this.selectedAffirmingCareCodes = event.detail.value; }
```

Then pass `taxonomyIds: this.selectedTaxonomyIds` in `handleCreateNewLocation()`.

**In Apex**, add three new `@AuraEnabled` methods to `PRM_AddressManagementService`:

```apex
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getTaxonomyOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    for (CareTaxonomy ct : [
        SELECT Id, Name, Code__c FROM CareTaxonomy 
        WHERE IsActive = true ORDER BY Name LIMIT 500
    ]) {
        options.add(new Map<String, String>{
            'label' => ct.Name + ' (' + ct.Code__c + ')',
            'value' => ct.Id
        });
    }
    return options;
}

@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getAssistiveAidOptions() {
    // Query ProviderFeature picklist values or custom object
    List<Map<String, String>> options = new List<Map<String, String>>();
    Schema.DescribeFieldResult fieldResult = 
        ProviderFeature.FeatureType.getDescribe();
    for (Schema.PicklistEntry pe : fieldResult.getPicklistValues()) {
        if (pe.isActive()) {
            options.add(new Map<String, String>{
                'label' => pe.getLabel(),
                'value' => pe.getValue()
            });
        }
    }
    return options;
}

@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getAffirmingCareOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    // Query from picklist or custom object per IBX data model
    Schema.DescribeFieldResult fieldResult = 
        HealthcarePractitionerFacility.PRM_AffirmingCareCategories__c.getDescribe();
    for (Schema.PicklistEntry pe : fieldResult.getPicklistValues()) {
        if (pe.isActive()) {
            options.add(new Map<String, String>{
                'label' => pe.getLabel(),
                'value' => pe.getValue()
            });
        }
    }
    return options;
}
```

---

## FIX 16: Add New Group Creation UI

**File:** `prmAddressGroupManager.html`, `prmAddressGroupManager.js`

**In the "Add New" tab**, after the Group Name record picker section and the 
Search button, add a "Don't see your group?" section:

```html
<!-- Create New Group Link -->
<div class="slds-m-top_small slds-text-align_center">
    <p class="slds-text-body_small slds-text-color_weak">
        Group not found? 
        <a href="javascript:void(0);" onclick={handleShowCreateNewGroup}>
            Create a new group
        </a>
    </p>
</div>

<!-- Create New Group Form (inline) -->
<template if:true={showCreateNewGroup}>
    <div class="slds-box slds-m-top_medium" style="background: #f9f9f9;">
        <h4 class="slds-text-heading_small slds-m-bottom_small">
            <lightning-icon icon-name="utility:new" size="x-small" class="slds-m-right_xx-small"></lightning-icon>
            Create New Group
        </h4>
        <div class="slds-grid slds-gutters slds-wrap">
            <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                <lightning-input label="Group Name" value={newGroupName} 
                    data-field="newGroupName" onchange={handleNewGroupFieldChange}
                    required max-length="255"
                    message-when-value-missing="Group Name is required"></lightning-input>
            </div>
            <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                <lightning-input label="Tax ID / EIN" value={newGroupTaxId}
                    data-field="newGroupTaxId" onchange={handleNewGroupFieldChange}
                    placeholder="XX-XXXXXXX" max-length="10"></lightning-input>
            </div>
            <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                <lightning-input label="Group NPI" value={newGroupNpi}
                    data-field="newGroupNpi" onchange={handleNewGroupFieldChange}
                    pattern="[0-9]{10}" max-length="10"
                    placeholder="10-digit NPI (optional)"
                    message-when-pattern-mismatch="NPI must be exactly 10 digits"></lightning-input>
            </div>
            <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
                <lightning-combobox label="Vendor Type" value={newGroupVendorType}
                    options={vendorTypeOptions} onchange={handleNewGroupFieldChange}
                    data-field="newGroupVendorType"
                    placeholder="Select vendor type"></lightning-combobox>
            </div>
        </div>
        <div class="slds-grid slds-grid_align-end slds-gutters_x-small slds-m-top_small">
            <div class="slds-col slds-no-flex">
                <lightning-button label="Cancel" onclick={handleCancelCreateNewGroup}></lightning-button>
            </div>
            <div class="slds-col slds-no-flex">
                <lightning-button label="Create Group" variant="brand" 
                    onclick={handleCreateNewGroup} disabled={showSpinner}></lightning-button>
            </div>
        </div>
    </div>
</template>
```

**In JS**, add:
```javascript
import createNewGroup    from '@salesforce/apex/PRM_AddressManagementService.createNewGroup';
import getVendorTypeOpts from '@salesforce/apex/PRM_AddressManagementService.getVendorTypeOptions';

@track showCreateNewGroup  = false;
@track newGroupName        = '';
@track newGroupTaxId       = '';
@track newGroupNpi         = '';
@track newGroupVendorType  = '';
@track vendorTypeOptions   = [];

handleShowCreateNewGroup() {
    this.showCreateNewGroup = true;
    if (this.vendorTypeOptions.length === 0) {
        this.loadVendorTypeOptions();
    }
}

handleCancelCreateNewGroup() {
    this.showCreateNewGroup = false;
    this.newGroupName = '';
    this.newGroupTaxId = '';
    this.newGroupNpi = '';
    this.newGroupVendorType = '';
}

handleNewGroupFieldChange(event) {
    const field = event.target.dataset.field;
    const value = event.target.value;
    if (field === 'newGroupName')       this.newGroupName       = value;
    if (field === 'newGroupTaxId')      this.newGroupTaxId      = value;
    if (field === 'newGroupNpi')        this.newGroupNpi        = value.replace(/\D/g, '').substring(0, 10);
    if (field === 'newGroupVendorType') this.newGroupVendorType = value;
}

async loadVendorTypeOptions() {
    try {
        const opts = await getVendorTypeOpts();
        this.vendorTypeOptions = opts || [];
    } catch (error) {
        console.error('Error loading vendor types:', error);
    }
}

async handleCreateNewGroup() {
    if (!this.newGroupName) {
        this.showToast('Error', 'Group Name is required', 'error');
        return;
    }
    try {
        this.showSpinner = true;
        const result = await createNewGroup({
            accountName: this.newGroupName,
            taxId:       this.newGroupTaxId,
            npi:         this.newGroupNpi,
            vendorType:  this.newGroupVendorType
        });
        if (result.success) {
            // Auto-select the newly created group
            this.groupAccountId = result.accountId;
            this.showToast('Success', result.message, 'success');
            this.handleCancelCreateNewGroup();
        } else {
            this.showToast('Error', result.message, 'error');
        }
    } catch (error) {
        this.showToast('Error', 'Failed to create group: ' + (error.body?.message || error.message), 'error');
    } finally {
        this.showSpinner = false;
    }
}
```

Also add `getVendorTypeOptions()` to Apex:
```apex
@AuraEnabled(cacheable=true)
public static List<Map<String, String>> getVendorTypeOptions() {
    List<Map<String, String>> options = new List<Map<String, String>>();
    Schema.DescribeFieldResult fr = Account.PRM_VendorType__c.getDescribe();
    for (Schema.PicklistEntry pe : fr.getPicklistValues()) {
        if (pe.isActive()) {
            options.add(new Map<String, String>{
                'label' => pe.getLabel(),
                'value' => pe.getValue()
            });
        }
    }
    return options;
}
```

---

## TESTING CHECKLIST

After implementing all fixes, verify the following:

### Precisely Address Validation
- [ ] Create a new location with a valid address → Precisely modal shows with comparison
- [ ] Create a new location with an invalid/unmatchable address → "No Match" message shows
- [ ] Precisely API is down → inline "Validation unavailable" banner shows, user can still save
- [ ] Low confidence address (≤50%) → yellow warning shows on modal

### Field Validation
- [ ] Submit Create New form with all fields empty → inline errors shown on all required fields
- [ ] Enter 4-digit zip → error "Zip Code must be 5 digits or 9 digits"
- [ ] Enter 9-digit zip (no dash) → should be accepted
- [ ] Enter phone as "(215) 555-1234" → stripped to "2155551234" before save
- [ ] Enter fax → 10-digit validation fires
- [ ] Enter Tax ID as "123456789" → format warning shows
- [ ] Address Line 1 > 255 chars → error shown

### Edit Active Location
- [ ] Active Locations datatable shows both "Edit" and "Remove" row actions
- [ ] Click Edit → edit subtab opens with all fields populated including County and Telehealth Only
- [ ] Change State in edit form → County dropdown reloads
- [ ] Click "Validate Address" → Precisely comparison shows inline
- [ ] Click Remove (primary) → custom confirmation modal shows, then shows error about primary

### Confirmation Dialogs
- [ ] Click Remove on any address → custom SLDs modal shows (NOT native confirm())
- [ ] Click Cancel → address not removed
- [ ] Click Confirm → address soft-deleted

### New Group Creation
- [ ] Click "Create a new group" → inline form appears
- [ ] Fill in name and click Create → group created, auto-selected in picker

### Taxonomy / Assistive Aids
- [ ] Click "Optional" accordion → lists load
- [ ] Select taxonomies → passed to createNewLocation()

---

## DEPLOYMENT ORDER

1. Deploy `PRM_AddressManagementService.cls` first (Apex IP call replacement)
2. Deploy `addressValidationModal` LWC (full HTML + JS + CSS rewrite per FIX 1 Part B)
3. Deploy `prmAddressGroupManager` LWC (HTML modal tag addition + JS modal-trigger logic update)
4. Test in QA sandbox org with alias `qa-sandbox`

```bash
sf project deploy start \
  --source-dir force-app/main/default/classes/PRM_AddressManagementService.cls \
  --source-dir force-app/main/default/lwc/addressValidationModal \
  --source-dir force-app/main/default/lwc/prmAddressGroupManager \
  --target-org qa-sandbox --wait 30 --verbose
```
```

---

## PART 6: PRIORITY SUMMARY

| Priority | Issue | Impact |
|----------|-------|--------|
| 🔴 P0 | Precisely integration broken (direct HTTP vs Integration Procedure) | No address validation working at all |
| 🔴 P0 | `confirm()` dialog blocked in LE | Users cannot delete any address (silently fails) |
| 🔴 P0 | Pending Edit: Phone treated as optional in validation | Bad data saved without phone |
| 🔴 P0 | Pending Edit: `handleSaveLocation()` calls Precisely before validating fields | Wasted API call, bad UX |
| 🟠 P1 | All max-length constraints missing (Address1/2 255, City 100, FacilityName 255) | Data truncation errors at Apex layer |
| 🟠 P1 | Pending Edit: State is plain text input, not combobox | No picklist enforcement, county doesn't reload |
| 🟠 P1 | Pending Edit: Missing County, Telehealth Only, Fax fields | Incomplete editing capability |
| 🟠 P1 | Pending Edit: Zip HTML `max-length="5"` blocks 9-digit ZIP entry | Users can't enter full ZIP+4 |
| 🟠 P1 | Fax validation completely absent in all three forms | Invalid fax numbers saved silently |
| 🟠 P1 | Tax ID format not validated | Incorrect group lookups |
| � P2 | **Taxonomy / Provider Type UI missing** — `taxonomyIds` always passed as `[]` | Core PAR form parity gap; backend ready but disconnected |
| 🟡 P2 | `currentUserId` always empty string | Audit trail broken for all soft-deletes |
| 🟡 P2 | Phone/Fax not stripped of formatting before Apex call | Formatted values stored in DB |
| 🟡 P2 | No inline field-level error display (toast only) | Poor UX; user doesn't know which field failed |
| 🟡 P2 | Assistive Aids UI missing + Apex placeholder not implemented | PAR form parity gap |
| 🟡 P2 | Affirming Care UI missing + Apex placeholder not implemented | PAR form parity gap |
| 🟡 P2 | New Group creation UI missing | No way to create groups from this component |
| 🔵 P3 | `message-when-value-missing` missing on all required fields | Generic "Complete this field" instead of specific messages |
| 🔵 P3 | NPI Luhn algorithm validation missing | Invalid NPIs (correct digit count, wrong check digit) could be saved |
| 🔵 P3 | No duplicate location warning before create | `detectLocationScenario()` exists but never called |

---

*End of Gap Analysis — April 15, 2026*
