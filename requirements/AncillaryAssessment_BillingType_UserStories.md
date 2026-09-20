# Ancillary Assessment Guided Flow — Billing Type Enhancement User Stories

> **Source:** Screenshot feedback captured 2026-05-01  
> **Scope:** `PRM_DelegatedPractitionerAddressForm_English` OmniScript (embedded in Ancillary Assessment guided flow)  
> **Related artifact:** `BugFix_AncillaryAssessment_PracticeClassification_Override.md`

---

## Background / Context

The **Billing Type** field (`PRM_BillingType__c`) on the `HealthcareFacility` object captures the claim form type a provider uses when submitting bills — either **UB** (UB-04, institutional/facility claims) or **1500** (CMS-1500, professional/physician claims).

This field is rendered in the Ancillary Assessment guided flow via the embedded `PRM_DelegatedPractitionerAddressForm_English` OmniScript. It appears **twice** — once for the primary office address block (`BillingType` element, parent: `PrimaryOfficeAddressBlock`) and once for each additional/satellite address (`BillingTypeAdditional` element, parent: `AdditionalAddress`).

**Current state of both elements:**

```json
"Type": "Multi-select",
"defaultValue": "1500",
"optionSource": {
    "source": "HealthcareFacility.PRM_BillingType__c",
    "type": "SObject"
},
"required": false
```

The underlying Salesforce field (`PRM_BillingType__c` on `HealthcareFacility`) is already defined as a **Picklist** with exactly two values: `UB` and `1500`. The OmniScript element type (Multi-select) is therefore misaligned with the field definition.

The three asks from the screenshot are:

1. **Change Billing Type from Multi-Select → Picklist** in the Ancillary guided flow
2. **Confirm if Billing Type should be required or optional**
3. **Confirm the tooltip message** — specifically the behavior when the field is left unselected:
   - *"If unselected, Facility/Ancillary defaults to UB & Professional defaults to 1500 downstream"*

---

## Story 1 — Change Billing Type Element from Multi-Select to Picklist

### Story ID
`ENH-PRM-ANCILLARY-002`

### Story Title
Change Billing Type Input from Multi-Select to Picklist in Ancillary Assessment Guided Flow

### User Story

As a **Provider Network Management credentialing coordinator**,  
I want the Billing Type field in the Ancillary Assessment guided flow to be a single-selection Picklist (not a Multi-Select checkbox group),  
So that a coordinator can choose exactly one billing form type — UB or 1500 — per practice location, matching the business rule that a location submits on one form type.

---

### Problem Statement

Both `BillingType` and `BillingTypeAdditional` OmniScript elements in `PRM_DelegatedPractitionerAddressForm_English` are configured as `"Type": "Multi-select"`. This allows coordinators to select both `UB` and `1500` simultaneously, which is not a valid business state. The underlying Salesforce field (`PRM_BillingType__c`) is a single-value Picklist. A Multi-select element that saves to a picklist field will either throw a save error, silently concatenate values in an unsupported format, or save only the last selected value — all of which are defects.

---

### Acceptance Criteria

#### AC-1: Primary Address — Billing Type Renders as Picklist
**Given** a coordinator is on the practice location address step of the Ancillary Assessment guided flow  
**When** the `BillingType` element renders in the `PrimaryOfficeAddressBlock`  
**Then** the element renders as a single-selection Picklist (dropdown), not a multi-checkbox group  
**And** the available options are `UB` and `1500` (sourced from `HealthcareFacility.PRM_BillingType__c`)

#### AC-2: Additional Address — Billing Type Renders as Picklist
**Given** a coordinator has added one or more additional/satellite locations  
**When** the `BillingTypeAdditional` element renders in the `AdditionalAddress` block  
**Then** the element renders as a single-selection Picklist, not a multi-checkbox group  
**And** the available options are `UB` and `1500`

#### AC-3: Only One Value Can Be Selected
**Given** the Billing Type element is a Picklist  
**When** a coordinator selects `UB`  
**Then** `1500` is automatically deselected (and vice versa)  
**And** it is not possible to save both values simultaneously on a single location

#### AC-4: Saved Value Matches Selected Picklist Option
**Given** a coordinator selects `UB` for a primary location Billing Type  
**When** the form is submitted  
**Then** the `HealthcareFacility` record is saved with `PRM_BillingType__c = "UB"`

#### AC-5: No Regression in Data Save
**Given** the element type is changed from Multi-select to Picklist  
**When** existing flows that read `BillingType` from the OmniScript context (e.g., `PRM_AncillaryProviderUtilsPDAService.cls` line 227, `processPracticeLocations()` line 658) execute  
**Then** the value is passed and saved correctly as a single string (not a comma-separated array or multi-value string)

---

### Technical Tasks

| # | Task | Component | Detail |
|---|---|---|---|
| 1 | Change `BillingType` element type | OmniScript `PRM_DelegatedPractitionerAddressForm_English` | In `PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json`, change `"Type": "Multi-select"` → `"Type": "Select"` |
| 2 | Change `BillingTypeAdditional` element type | OmniScript `PRM_DelegatedPractitionerAddressForm_English` | In `PRM_DelegatedPractitionerAddressForm_English_Element_BillingTypeAdditional.json`, change `"Type": "Multi-select"` → `"Type": "Select"` |
| 3 | Activate updated OmniScript | OmniStudio | Activate a new version of `PRM_DelegatedPractitionerAddressForm_English` after both element changes are applied |
| 4 | Verify downstream value format | Apex / DataRaptor | Confirm `PRM_AncillaryProviderUtilsPDAService` and any DataRaptor that maps `BillingType` receives a plain string (`"UB"` or `"1500"`), not an array or multi-value encoding |

### Files to Change

| File | Change |
|---|---|
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json` | `"Type": "Multi-select"` → `"Type": "Select"` |
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingTypeAdditional.json` | `"Type": "Multi-select"` → `"Type": "Select"` |

### Effort Estimate
**2 story points** (configuration change + activation + regression test)

---

---

## Story 2 — Confirm and Configure Billing Type Required/Optional Status

### Story ID
`ENH-PRM-ANCILLARY-003`

### Story Title
Define and Configure Whether Billing Type Is Required or Optional in the Ancillary Assessment Guided Flow

### User Story

As a **Provider Network Management credentialing coordinator**,  
I want it to be clearly defined whether Billing Type is a required field or optional in the Ancillary Assessment guided flow,  
So that coordinators cannot inadvertently submit incomplete records and downstream default logic (UB for Facility, 1500 for Professional) is applied correctly when left unselected.

---

### Problem Statement

Both `BillingType` and `BillingTypeAdditional` elements currently have `"required": false`. There is **no business rule enforcement** at the OmniScript level to mandate a selection. 

However, downstream processing logic in `PRM_AncillaryProviderUtilsPDAService.cls` and related DataRaptors rely on `PRM_BillingType__c` being populated. A blank value may result in null references, incorrect billing claim routing, or silent failures in HACAC decision workflows.

The business has requested a decision be made: **required or optional with smart defaults**.

---

### Business Rule (from Screenshot)

> *"If unselected, Facility/Ancillary defaults to UB & Professional defaults to 1500 downstream"*

This indicates the **preferred behavior is optional with conditional defaults**:
- If the coordinator leaves Billing Type blank:
  - Locations classified as **Facility/Ancillary** → default to **`UB`**
  - Locations classified as **Professional Practice** → default to **`1500`**

---

### Acceptance Criteria

#### AC-1: Field is Optional — Default Applies When Blank (Recommended Path)
**Given** the business decision is to make Billing Type **optional**  
**And** a coordinator leaves Billing Type unselected for a practice location  
**When** the form is submitted  
**Then** the system applies the classification-based default:
- If `PRM_PracticeClassification__c = "Facility"` → `PRM_BillingType__c = "UB"`
- If `PRM_PracticeClassification__c = "Professional Practice"` → `PRM_BillingType__c = "1500"`

#### AC-2: Explicit Selection Always Overrides Default
**Given** a coordinator explicitly selects `UB` or `1500` for any practice location  
**When** the form is submitted  
**Then** the coordinator's explicit selection is saved, regardless of the location's practice classification

#### AC-3: Required Path — Validation Fires Before Submit (If Required Is Chosen)
**Given** the business decision is to make Billing Type **required**  
**And** a coordinator attempts to advance past the address step without selecting a Billing Type  
**When** the coordinator clicks Next or Submit  
**Then** an inline validation error is shown on the Billing Type field  
**And** the coordinator cannot proceed until a selection is made  
**And** this applies to both the primary address block and each additional address block

#### AC-4: OmniScript `required` Property Matches Business Decision
**Given** the business has confirmed the required/optional status  
**When** the OmniScript element configuration is reviewed  
**Then** `"required": true` or `"required": false` is set accordingly in both `BillingType` and `BillingTypeAdditional` elements

#### AC-5: Default Value Configuration
**Given** the field is optional with conditional defaults  
**When** the address step renders  
**Then** the `defaultValue` in both elements is blank (no pre-selection)  
**And** the conditional default logic (`UB` for Facility, `1500` for Professional) is applied server-side at record creation, not as a pre-filled OmniScript value  

> **Note:** The current `"defaultValue": "1500"` in both elements should be evaluated — it pre-selects `1500` for all location types, which is incorrect for Facility locations. It should either be removed (leaving blank) with the classification-based default applied at save time, or made dynamic based on `PracticeLocationType`.

---

### Technical Tasks

| # | Task | Component | Detail |
|---|---|---|---|
| 1 | Business decision gate | Product / BA | Confirm with stakeholders: required or optional? This story cannot be fully implemented until this decision is made. |
| 2 | Update `required` flag | OmniScript | Set `"required": true` or `"required": false` in both `BillingType` and `BillingTypeAdditional` elements per the decision |
| 3 | Remove/fix hardcoded `defaultValue` | OmniScript | Remove `"defaultValue": "1500"` from both elements (it incorrectly pre-selects `1500` for Facility locations). Replace with blank or a conditional formula |
| 4 | Implement classification-based default at save | Integration Procedure / DataRaptor | In `PRM_AncillaryFormRecordsCreation` IP, add a conditional Set Values step: if `BillingType` is blank AND `practiceClassification = "Facility"` → set `BillingType = "UB"`; if blank AND `practiceClassification = "Professional Practice"` → set `BillingType = "1500"` |
| 5 | Update `PRMDRCreateAncillaryHCFacilityLocationAddress` | DataRaptor | Confirm `BillingType` `InputFieldName` correctly reads the resolved (defaulted) value, not the raw blank input |
| 6 | Update `PRMDRCreateAncillaryAdditionalAddressRecords` | DataRaptor | Same as Task 5 for additional addresses |

### Files to Change

| File | Change |
|---|---|
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json` | Update `"required"` flag; clear `"defaultValue"` |
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingTypeAdditional.json` | Update `"required"` flag; clear `"defaultValue"` |
| `PRM_AncillaryFormRecordsCreation` (Integration Procedure) | Add conditional default logic for blank BillingType based on practice classification |
| `PRMDRCreateAncillaryHCFacilityLocationAddress_Items.json` | Verify `InputFieldName` for BillingType mapping |
| `PRMDRCreateAncillaryAdditionalAddressRecords_Items.json` | Verify `InputFieldName` for BillingType mapping |

### Effort Estimate
**5 story points** (pending business decision + OmniScript update + IP conditional logic + DataRaptor verification + E2E testing)

### Dependency
- Blocked by business stakeholder confirmation: **Required vs. Optional**
- Closely related to **Story BUG-PRM-ANCILLARY-001** (practice classification fix) — the classification-based default logic in Task 4 above depends on the correct classification value being available in the IP context, which is the fix from that story.

---

---

## Story 3 — Add Tooltip to Billing Type Field Explaining Default Behavior

### Story ID
`ENH-PRM-ANCILLARY-004`

### Story Title
Add Billing Type Tooltip in Ancillary Assessment Guided Flow to Communicate Classification-Based Default Behavior

### User Story

As a **Provider Network Management credentialing coordinator**,  
I want a tooltip on the Billing Type field in the Ancillary Assessment guided flow that explains what happens when the field is left blank,  
So that I understand the downstream defaulting rules (UB for Facility/Ancillary, 1500 for Professional) without needing to reference separate documentation.

---

### Problem Statement

Both `BillingType` and `BillingTypeAdditional` OmniScript elements currently have:

```json
"help": false,
"helpText": ""
```

There is no tooltip or help text on either element. When a coordinator leaves Billing Type blank, the downstream default behavior (classification-based defaulting) is invisible to the user, creating uncertainty and potential data quality issues when coordinators do not know the business rule.

---

### Proposed Tooltip Text

> **"Billing Type"**  
> *Select the claim form type used by this practice location. If left blank, the system will apply a default based on the location classification:*
> - *Facility / Ancillary providers → UB (UB-04)*
> - *Professional Practice providers → 1500 (CMS-1500)*

*(Final wording subject to business/UX review — confirm with stakeholders before implementation.)*

---

### Acceptance Criteria

#### AC-1: Tooltip Present on Primary Address Billing Type
**Given** a coordinator is on the practice location address step  
**When** the coordinator hovers over or clicks the help icon next to the `BillingType` field in the `PrimaryOfficeAddressBlock`  
**Then** a tooltip/help text appears explaining the field purpose and the UB/1500 classification-based default rule

#### AC-2: Tooltip Present on Additional Address Billing Type
**Given** a coordinator has added one or more additional locations  
**When** the coordinator hovers over or clicks the help icon next to the `BillingTypeAdditional` field  
**Then** the same tooltip/help text appears

#### AC-3: Tooltip Text Is Accurate
**Given** the tooltip is displayed  
**When** a coordinator reads it  
**Then** it correctly states:
- "Facility / Ancillary providers default to UB if unselected"
- "Professional Practice providers default to 1500 if unselected"

#### AC-4: Tooltip Only Shows When Help Is Enabled
**Given** the OmniScript element has `"help": true`  
**When** the element renders  
**Then** the help icon (ⓘ) is visible next to the Billing Type label  
**And** clicking or hovering the icon displays the `helpText` content

#### AC-5: Tooltip Text Confirmed by Business
**Given** the proposed tooltip text  
**When** reviewed by the product owner / business analyst  
**Then** the exact wording is signed off before the OmniScript is activated in production

---

### Technical Tasks

| # | Task | Component | Detail |
|---|---|---|---|
| 1 | Confirm tooltip wording | Product / BA | Get sign-off on the exact helpText string from the business before implementation |
| 2 | Enable help on `BillingType` | OmniScript | In `BillingType` element: set `"help": true` and populate `"helpText"` with the confirmed wording |
| 3 | Enable help on `BillingTypeAdditional` | OmniScript | Same change for the additional address variant |
| 4 | Activate updated OmniScript | OmniStudio | Activate a new version after both elements are updated |
| 5 | Visual QA | QA / UX | Verify help icon renders correctly in both primary and additional address blocks in sandbox; validate tooltip content matches sign-off wording |

### Files to Change

| File | Change |
|---|---|
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json` | Set `"help": true`, populate `"helpText"` with confirmed tooltip text |
| `PRM_DelegatedPractitionerAddressForm_English_Element_BillingTypeAdditional.json` | Same change |

### Effort Estimate
**2 story points** (text confirmation + two-element configuration update + visual QA)

### Dependency
- Blocked by business stakeholder sign-off on tooltip wording
- Can be developed in parallel with Stories 002 and 003, but should be activated in the **same OmniScript version** to minimize deployments

---

---

## Combined Story Summary

| Story ID | Title | Effort | Blocked By |
|---|---|---|---|
| `BUG-PRM-ANCILLARY-001` | Practice Location Classification Overridden to "Facility" | 8 pts | None — ready to implement |
| `ENH-PRM-ANCILLARY-002` | Change Billing Type from Multi-Select to Picklist | 2 pts | None — ready to implement |
| `ENH-PRM-ANCILLARY-003` | Define Required/Optional + Classification-Based Default Logic | 5 pts | Business decision: required vs. optional |
| `ENH-PRM-ANCILLARY-004` | Add Billing Type Tooltip with Default Behavior Explanation | 2 pts | Business sign-off on tooltip wording |

**Total estimate:** 17 story points across 4 stories

---

## Recommended Deployment Grouping

Since all three enhancement stories (002, 003, 004) touch the same OmniScript (`PRM_DelegatedPractitionerAddressForm_English`) and should be activated as a single version to avoid multiple deployments, the recommended approach is:

1. **Sprint 1 (unblocked):** Implement `BUG-PRM-ANCILLARY-001` (classification override fix) and `ENH-PRM-ANCILLARY-002` (Multi-select → Picklist).
2. **Sprint 2 (after business decisions):** Implement `ENH-PRM-ANCILLARY-003` (required/optional + default logic) and `ENH-PRM-ANCILLARY-004` (tooltip) together in one OmniScript activation.

---

## Open Questions for Business

| # | Question | Owner | Needed For |
|---|---|---|---|
| Q1 | Is Billing Type **required** (coordinator must select) or **optional** (system defaults apply if blank)? | Product Owner | Story 003 |
| Q2 | Should the `defaultValue: "1500"` currently pre-filling the field be removed (blank initial state) or changed to a dynamic formula based on practice classification? | Product Owner / BA | Story 003 |
| Q3 | What is the exact approved wording for the tooltip — is *"Facility/Ancillary defaults to UB & Professional defaults to 1500 downstream"* the final text, or should it be expanded? | UX / Business | Story 004 |
| Q4 | Does this change apply only to the Ancillary Assessment guided flow, or also to the standard Practitioner Account Creation flow and PDM Manual Update flow, which also embed the Delegated Practitioner Address Form? | BA | Scope all stories |
