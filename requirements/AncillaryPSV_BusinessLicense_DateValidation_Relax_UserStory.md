# User Story: Relax Provider License Effective/Expiration Date Validations on Ancillary PSV & Reassessment PSV — New Business License

**Persona:** Credentialing Specialist
**Priority:** P1
**Flows in scope:** Ancillary PSV (Initial) **and** Ancillary Reassessment PSV
**OmniScripts:** `PRM_AncillaryPSVForm_English`, `PRM_AncillaryReassessmentPSV_English`
**Primary Component:** LWC `pRMBusinessLicenseAncNpdb` (renders the "New Business License" modal on the Verify Licensure step for **both** flows)
**Related existing docs:**
- `requirements/Ancillary_PSV_Business_Licenses_User_Story.md` (parent story — display + Add New)
- `requirements/AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` (AC5 currently mandates `Effective ≥ PL Effective From` — to be amended by this story)

---

## Story

**As a** Credentialing Specialist working an Ancillary PSV or Ancillary Reassessment PSV case,
**I want** to enter a Provider License **Effective Date** that is *earlier than* the selected Practice Location's *Effective From* date, **and** to save a Business License *without* providing a Provider License **Expiration Date**,
**So that** I can accurately capture licenses that were issued **before** IBX added the practice location to the system (common during reassessment when historical licenses are re-verified) and licenses that have no formal expiration on file, without being blocked by overly strict UI validations.

**Why it matters:** Reassessment routinely surfaces business licenses issued years before the practice location was originally onboarded into IBX. The current "Effective Date cannot be before the selected Practice Location Effective From" hard-stop forces specialists to either edit the license date inaccurately or drop the license altogether — both of which are data-integrity violations. Similarly, some perpetual / non-expiring licenses do not have an expiration date and should be saveable as such.

---

## Current Behavior (observed in QA — screenshot 2026-05-27)

| Field | Current validation | Source |
|-------|-------------------|--------|
| Provider License Effective Date | Browser-level **min = selected Practice Location's Effective From** (renders as "*Value must be `<PL Effective From>` or later.*", e.g. "Value must be 2/1/2015 or later.") | `pRMBusinessLicenseAncNpdb.js` → `modalEffectiveDateMin` getter (lines 209–217) + `min={modalEffectiveDateMin}` on `<lightning-input>` (deployed HTML) |
| Provider License Effective Date | Inline error: **"Provider License Effective Date cannot be before the selected Practice Location Effective From."** | `pRMBusinessLicenseAncNpdb.js` → `modalDateValidationError` / `isEffectiveDateAfterPracticeLocationMin` getter (lines 228–252 — already partially commented in local; still active in QA deployment) |
| Provider License Expiration Date | **Disabled** until Effective Date is filled; if entered, must be **> Effective Date + 1 day** | `pRMBusinessLicenseAncNpdb.js` → `isExpirationDateDisabled` (line 299–303), `modalExpirationDateMin` (line 219–226), `modalDateValidationError` (line 248–258) |
| AC5 doc | "Date validations: Effective ≤ Expiration; Effective ≥ PL effective date" | `requirements/AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` line 128 |

---

## Desired Behavior

### Provider License Effective Date
1. **Remove** the `min = Practice Location Effective From` constraint on the date input.
2. **Remove** the inline error *"Provider License Effective Date cannot be before the selected Practice Location Effective From."*
3. **Remove** the static `2/1/2015 or later` floor (per business decision — any past date is allowed).
4. **Keep** the existing behavior that disables Effective Date until a Practice Location is selected (`isEffectiveDateDisabled` stays as-is — selecting a PL is still required first).
5. **Keep** the existing required indicator (`*`) on the Effective Date label.

### Provider License Expiration Date
1. **Field remains visible** in the New Business License modal (do **not** remove it).
2. **Field is NOT required** — user can save the record without entering an expiration date (current label already has no `*` — confirm).
3. **Remove** the dependent-disabled behavior so the field is independently editable (or, at minimum, allow save when blank).
4. **Keep** the consistency check `Expiration > Effective` **only when the user has entered an expiration date** (i.e., do not enforce when expiration is blank).

### Behavior matrix (target)

| Effective Date entered? | Expiration Date entered? | Save outcome |
|---|---|---|
| Yes (any past date, including before PL Effective From) | No | **Allowed** |
| Yes (any past date) | Yes, and Expiration > Effective | **Allowed** |
| Yes | Yes, and Expiration ≤ Effective | **Blocked** with existing message "Provider License Expiration Date must be after Provider License Effective Date." |
| No | Any | **Blocked** (Effective Date remains required) |

---

## Acceptance Criteria

### AC1 — Effective Date can be backdated to before Practice Location Effective From
**Given** the Credentialing Specialist is on the Verify Licensure step of either the Ancillary PSV (Initial) or Ancillary Reassessment PSV form,
**And** they click **Add New** to open the "New Business License" modal,
**And** they select a Practice Location whose Effective From is `2/1/2015`,
**When** they enter Provider License Effective Date = `6/28/2010`,
**Then** **no** *"Value must be 2/1/2015 or later"* browser validation error shall be shown.
**And** **no** *"Provider License Effective Date cannot be before the selected Practice Location Effective From"* inline error shall be shown.
**And** the **Save** button shall remain enabled (assuming other required fields are filled).

### AC2 — Expiration Date is optional
**Given** the specialist is in the "New Business License" modal with required fields populated (License Number, License State, Effective Date, Status, Practice Location, plus Verified On if Status = Verified, License Class as applicable),
**And** Provider License Expiration Date is left blank,
**When** they click **Save**,
**Then** the record shall save successfully.
**And** the saved `PRM_BusinessLicense__c` record shall have `PRM_ProviderLicenseExpirationDate__c = null`.

### AC3 — Expiration > Effective consistency check is preserved when expiration is entered
**Given** the specialist enters Provider License Effective Date = `1/1/2020`,
**When** they enter Provider License Expiration Date = `1/1/2020` (equal) or `12/31/2019` (earlier),
**Then** the inline error *"Provider License Expiration Date must be after Provider License Effective Date."* shall be shown,
**And** the Save button shall be disabled / save shall be blocked until the dates are valid or expiration is cleared.

### AC4 — Effective Date is still required and still gated on Practice Location selection
**Given** the modal is open,
**When** no Practice Location is selected,
**Then** the Provider License Effective Date input remains disabled (existing behavior).

**And When** Practice Location is selected but Effective Date is left blank,
**Then** save shall be blocked with the existing required-field indication.

### AC5 — Initial Ancillary PSV parity
The same relaxed behavior (AC1, AC2, AC3, AC4) shall apply when the modal is opened from `PRM_AncillaryPSVForm_English` Verify Licensure step (Initial Ancillary PSV), since both flows render through the same `pRMBusinessLicenseAncNpdb` LWC.

### AC6 — Existing licenses display unchanged
**Given** the table view of existing Business Licenses on Verify Licensure,
**Then** display logic shall remain unchanged — historical licenses with effective dates before the PL effective from continue to render with their original values; no retroactive validation banner is shown on the table.

### AC7 — Apex / sObject persistence
**Given** AC1 or AC2 has saved a Business License with effective-before-PL or null expiration,
**When** the record is retrieved via `PRM_BusinessLicenseAncNpdbController` or via subsequent OmniScript reads (e.g. `DRExtractAncAssessNpiLocDetails`),
**Then** the persisted dates shall round-trip correctly and no server-side validation rule shall reject them.
*Dev note: confirm no Salesforce Validation Rule on `BusinessLicense` enforces `PRM_ProviderLicenseEffectiveDate__c ≥` PL Effective From or requires `PRM_ProviderLicenseExpirationDate__c`.*

---

## Technical Section (For Developers)

### Files / Elements to change

| File | Change |
|------|--------|
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | (a) Remove or always-return-`""` from `modalEffectiveDateMin` getter (lines 209–217). (b) Delete the already-commented `isEffectiveDateAfterPracticeLocationMin` block (lines 228–237) and the corresponding branch in `modalDateValidationError` (lines 250–252) — they are dead in source but if the QA deployment is on an older revision, re-confirm the deploy. (c) Update `isExpirationDateDisabled` (lines 299–303) to return `this.isModalReadOnly` only (i.e., **do not** disable based on missing Effective Date) — Expiration is independently editable. (d) Keep `isDateOrderValid` and the "Expiration must be after Effective" branch of `modalDateValidationError` unchanged. |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.html` | (a) If the deployed template binds `min={modalEffectiveDateMin}` on the Effective Date `<lightning-input>`, remove that attribute. (b) Confirm the Expiration Date label does **not** carry a required asterisk (current local template lines 195–197 already do not). (c) Confirm the `disabled` attribute on Expiration Date input reflects the relaxed `isExpirationDateDisabled` getter. |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.css` | No change expected (verify no rule highlights expiration as required). |
| `force-app/main/default/classes/PRM_BusinessLicenseAncNpdbController.cls` | Confirm save / upsert path does **not** reject null `PRM_ProviderLicenseExpirationDate__c` and does **not** compare `PRM_ProviderLicenseEffectiveDate__c` to PL Effective From. If a check exists, remove it. |
| `force-app/main/default/objects/BusinessLicense/validationRules/` (and `PRM_BusinessLicense__c` if applicable) | Audit for any sObject-level validation rule enforcing the relaxed constraints. Deactivate / delete as appropriate (separate change-set if found). |
| `requirements/AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` (AC5 row, line ~128) | Amend AC5 to: `"Date validations: when Expiration is provided, Effective ≤ Expiration. Effective Date is NOT bounded by PL Effective From. Expiration Date is optional."` Add cross-reference back to this story. |

### Test updates

| File | Change |
|------|--------|
| `force-app/main/default/classes/PRM_BusinessLicenseAncNpdbControllerTest.cls` | Add positive tests: (i) save with Effective Date before PL Effective From; (ii) save with null Expiration Date. |
| LWC Jest (if present for `pRMBusinessLicenseAncNpdb`) | Add tests for `modalDateValidationError` returning `""` when effective < PL Effective From, and `""` when expiration is blank. |

### Out of scope
- No DataRaptor changes — extraction queries are unaffected.
- No Integration Procedure changes — payload contract is unchanged (same fields, same shape).
- No changes to duplicate-prevention validation defined in `Ancillary_PSV_Business_Licenses_User_Story.md` (License State + Number + Class + Practice Location duplicate check stays).

---

## Open Questions

1. **Audit trail / case notes:** Should saving a license with `Effective Date < PL Effective From` automatically annotate the case (case note or audit entry) so downstream reviewers see why the dates appear inconsistent? *(Default: No — but flagging for business confirmation.)*
2. **Future-dated effective dates:** This story does not change the upper bound. Confirm whether future-dated Effective Date is still acceptable (current local code does not block it).
3. **CAQH / external sourced licenses:** If the license originated from CAQH and arrives without an expiration, does our existing CAQH import path already null-coalesce expiration correctly? *(Likely yes — should be confirmed during dev.)*

---

## Dependencies

- Parent story `Ancillary_PSV_Business_Licenses_User_Story.md` must be deployed (Add New button on both flows must already be functional).
- No new permissions / FLS changes required.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.js` | LWC controller hosting all current validations |
| `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/pRMBusinessLicenseAncNpdb.html` | LWC template — Effective / Expiration date inputs |
| `force-app/main/default/classes/PRM_BusinessLicenseAncNpdbController.cls` | Apex controller for save / load |
| `force-app/main/default/omniScripts/PRM_AncillaryPSVForm_English_*.os-meta.xml` | Initial PSV OmniScript (embeds the LWC) |
| `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml` | Reassessment PSV OmniScript (embeds the LWC) |
| `vlocity_export/OmniScript/PRM_AncillaryReassessmentPSV_English/PRM_AncillaryReassessmentPSV_English_Element_NewBusinessLicenseBlk.json` | Reassessment "New Business License" block reference |

---

*Source: QA org screenshot (2026-05-27) showing both validation errors, LWC source audit of `pRMBusinessLicenseAncNpdb`, parent story `Ancillary_PSV_Business_Licenses_User_Story.md`, validation source `AddAncillaryPLAndBusinessLicense_Address_Upgrade_Plan.md` (AC5).*
