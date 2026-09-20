# PAR Form — PNC Path User Stories

**Document Version:** 1.0  
**Created Date:** April 16, 2026  
**Vertical:** Provider Network Management (PNM)  
**OmniScript:** `PRM_PractitionerParticipationForm_English`  
**Related Documents:**
- `Concierge_Medicine_PAR_Form_Changes_User_Stories.md`
- `PNM_PNC_Backfill_User_Story.md`

---

## Executive Summary

Two user stories address gaps in the Practitioner Participation Form (PAR) related to the **PNC (Physician Network Contracted) path**. The first story validates and documents the correct behavior when a Sr. Data Reporting Analyst enters an NPI for an existing credentialed non-PNC practitioner who is joining a PNC group — the credentialed-practitioner warning must be suppressed and the practitioner's data must prefill in read-only mode. The second story — and the team's primary concern — addresses the absence of a reliable hard block when a user answers **"Yes"** to the PNC Group question on the Practitioner step and then selects a **non-PNC group** on the Group step. Two specific element-level gaps are identified in the codebase and must be remediated.

---

## Use Case Analysis — All PNC Scenarios

The table below maps every combination of practitioner status and Q5 answer to the expected UI behavior, derived from a full read of the `PRM_PractitionerParticipationForm_English` OmniScript elements.

| # | NPI Status | IsCredentialedPNCDelegated | Q5 (PNC Group?) | Expected Behavior |
|---|-----------|---------------------------|----------------|-------------------|
| UC-1 | New practitioner (no NPI record) | N/A | N/A | Full data entry, all fields editable; Q5 not shown (CredentialingStatus not = "Credentialed") |
| UC-2 | Credentialed, non-PNC | false | Yes | Data prefills read-only; warning suppressed; Next enabled → Group step (PNC group type-ahead) |
| UC-3 | Credentialed, non-PNC | false | No | Warning shown ("submit PCR or Off-Cycle Request"); `SetErrorsCredentialingStatus` does NOT fire (IsCredentialedPNCDelegated=false); user can attempt to proceed |
| UC-4 | Credentialed, PNC-Delegated | true | No | Warning shown AND `SetErrorsCredentialingStatus` fires → hard block on Next |
| UC-5 | Credentialed, PNC-Delegated | true | Yes | Warning still shown (IsCredentialedPNCDelegated=true overrides Q5) → ambiguous state; business rule needed |
| UC-6 | Credentialing In Progress (PSV/QC/Committee) | N/A | N/A | `NavigateToOffCycle` TextBlock shown; `ExistingNPICredentialed` validation blocks Next |
| UC-7 | Any status, Q5=Yes | — | Group step: PNC group selected | Validation passes; flow continues |
| **UC-8** | **Any status, Q5=Yes** | **—** | **Group step: Non-PNC group selected** | **Must block — GAP EXISTS (see Story 2)** |

---

# USER STORY 1: PAR Form — Suppress Credentialed Warning and Enable PNC Path for Credentialed Non-PNC Practitioner

**Persona:** Sr. Data Reporting Analyst, Developer  
**Priority:** P0  
**OmniScript:** `PRM_PractitionerParticipationForm_English`  
**Integration Procedures:** `PRM_FetchExistingNPIInfo`  
**Relevant Requirements:** Requirement image — Apr 16, 2026; Use Case UC-2 above

---

## Story

**As a** Sr. Data Reporting Analyst completing the Practitioner Participation Form,  
**I want** the form to suppress the "Credentialed Practitioner" warning and allow me to proceed when I select "Yes" to the PNC Group question for an existing credentialed non-PNC practitioner,  
**So that** I can successfully submit a PNC participation request for a practitioner who is already credentialed but not yet in a PNC group.

**Why it matters:** Without this behavior, the form may misdirect analysts toward the Provider Change Request or Off-Cycle flow, creating unnecessary administrative overhead and preventing valid PNC enrollment from being captured correctly.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationForm_English` | `PractitionerForm` (Step 1) | `FetchExistingNPIInfo` LWC → IP `PRM_FetchExistingNPIInfo` |

---

## Current State (from codebase)

### `CredentialingStatus` (TextBlock — Warning Message)

- **Element Name:** `CredentialingStatus`
- **Type:** Text Block
- **Location:** `vlocity_export/OmniScript/PRM_PractitionerParticipationForm_English/PRM_PractitionerParticipationForm_English_Element_CredentialingStatus.json`
- **Text content:** *"The NPI is associated with a Credentialed Practitioner, please submit a Provider Change Request or Off-Cycle Request."*
- **Show condition (AND):**
  - `PractitionerForm:CredentialingStatus == "Credentialed"` **AND**
  - (`PractitionerForm:IsCredentialedPNCDelegated == true` **OR** `PractitionerParticipationQuestion5 == "No"`)
- **Analysis:** When `Q5 == "Yes"` and `IsCredentialedPNCDelegated == false`, the compound show condition evaluates to `false` → warning is **correctly hidden**. ✓
- **Gap:** When `IsCredentialedPNCDelegated == true` AND `Q5 == "Yes"`, the warning still shows (UC-5 above). Business rule for this combination needs clarification.

### `SetErrorsCredentialingStatus` (Set Errors — Hard Block)

- **Element Name:** `SetErrorsCredentialingStatus`
- **Type:** Set Errors, `validationRequired: "Step"`
- **Location:** `vlocity_export/OmniScript/PRM_PractitionerParticipationForm_English/PRM_PractitionerParticipationForm_English_Element_SetErrorsCredentialingStatus.json`
- **Fires when:** CredentialingStatus="Credentialed" AND IsCredentialedPNCDelegated=true AND Q5="No"
- **Effect:** Sets blocking error on `CredentialingStatus` element; prevents Next.
- **Analysis:** Does NOT fire when Q5="Yes" → Next is not blocked for the PNC path. ✓

### `PractitionerParticipationQuestion5` (Radio Button — Q5)

- **Element Name:** `PractitionerParticipationQuestion5`
- **Type:** Radio Button, `required: true`
- **Label:** *"Is the Practitioner joining a PNC Group?"*
- **Show condition:** `PractitionerForm:CredentialingStatus == "Credentialed"`
- **Options:** Yes / No
- **Location:** `vlocity_export/OmniScript/PRM_PractitionerParticipationForm_English/PRM_PractitionerParticipationForm_English_Element_PractitionerParticipationQuestion5.json`

### `FetchExistingNPIInfo` (Custom LWC)

- **Element Name:** `FetchExistingNPIInfo`
- **Type:** Custom Lightning Web Component (`prmGetInfoBasedOnNPI`)
- **Integration Procedure:** `PRM_FetchExistingNPIInfo`
- **Populates:** `PractitionerForm:CredentialingStatus`, `PractitionerForm:IsCredentialedPNCDelegated`, all prefill fields
- **Location:** `vlocity_export/OmniScript/PRM_PractitionerParticipationForm_English/PRM_PractitionerParticipationForm_English_Element_FetchExistingNPIInfo.json`

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`CredentialingStatus`** | OmniScript Text Block | No change needed for UC-2 — current show condition correctly suppresses warning when Q5=Yes AND IsCredentialedPNCDelegated=false. Regression test required. |
| **`CredentialingStatus`** (UC-5 gap) | OmniScript Text Block | Confirm business rule: should a PNC-delegated credentialed practitioner with Q5=Yes be allowed to proceed? If yes, update show condition to add `IsCredentialedPNCDelegated=false` as an AND rule alongside Q5="No". |
| **`SetErrorsCredentialingStatus`** | OmniScript Set Errors | No change needed for UC-2 — does not fire when Q5=Yes. Regression test required. |
| **`PractitionerParticipationQuestion5`** | OmniScript Radio | No change required. Confirm `readOnly: false` remains correct (user must actively select Yes). |
| **`PRM_FetchExistingNPIInfo`** | Integration Procedure | Confirm IP returns `IsCredentialedPNCDelegated` field for credentialed non-PNC practitioners (must return `false`). |
| **Prefill fields (name, DOB, gender, specialty, etc.)** | OmniScript Elements | Confirm `readOnly: true` is set on all prefilled fields when an existing NPI is recognized. Verify via LWC callback or SetValues after IP response. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRM_FetchExistingNPIInfo` | IP | `npi` (practitioner NPI) | `CredentialingStatus`, `IsCredentialedPNCDelegated`, practitioner demographic fields | Verify `IsCredentialedPNCDelegated` is correctly set to `false` for credentialed non-PNC practitioners |

---

## Acceptance Criteria

**Scenario 1 — Happy Path: Credentialed non-PNC practitioner, Q5=Yes**

**Given** I am a Sr. Data Reporting Analyst on the Home screen,  
**When** I click the Practitioner Participation Form button, navigate to the Practitioner step, select *"Is the Practitioner joining a PNC Group?" = Yes*, and enter the NPI of an existing **credentialed non-PNC practitioner**,  
**Then** I see the practitioner's data pre-filled on the screen (name, DOB, gender, specialty, degree) and all pre-filled data fields are read-only,  
**AND** I do **not** see the warning message: *"The NPI is associated with a Credentialed Practitioner, please submit a Provider Change Request or Off-Cycle Request."*,  
**AND** the Next button is enabled,  
**AND** clicking Next takes me to the PNC Group selection step.

---

**Scenario 2 — Q5=No: Warning must appear**

**Given** I am on the Practitioner step and I enter the NPI of an existing **credentialed non-PNC practitioner** (IsCredentialedPNCDelegated=false),  
**When** I select *"Is the Practitioner joining a PNC Group?" = No*,  
**Then** I see the warning message: *"The NPI is associated with a Credentialed Practitioner, please submit a Provider Change Request or Off-Cycle Request."*  
**AND** the message contains clickable links to Provider Change Request and Off-Cycle Request forms.

---

**Scenario 3 — PNC-Delegated practitioner, Q5=No: Hard block**

**Given** I enter the NPI of an existing **credentialed PNC-delegated practitioner** (IsCredentialedPNCDelegated=true),  
**When** I select *"Is the Practitioner joining a PNC Group?" = No*,  
**Then** the warning message is visible  
**AND** `SetErrorsCredentialingStatus` fires, setting a blocking error on the form  
**AND** I cannot click Next — the form is blocked.

---

**Scenario 4 — Q5 unanswered: Next must be blocked**

**Given** I enter the NPI of an existing credentialed practitioner and the Q5 radio button appears,  
**When** I attempt to click Next without answering Q5,  
**Then** OmniScript required-field validation fires and I cannot proceed until Q5 is answered.

---

**Scenario 5 — PNC-Delegated practitioner, Q5=Yes (clarification needed)**

**Given** I enter the NPI of a **credentialed PNC-delegated practitioner** (IsCredentialedPNCDelegated=true),  
**When** I select *"Is the Practitioner joining a PNC Group?" = Yes*,  
**Then** [BUSINESS RULE NEEDED — see Clarification Questions] the form should either (a) allow proceeding or (b) still block, depending on whether a PNC-delegated practitioner is allowed to enroll in an additional PNC group via PAR.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | When `IsCredentialedPNCDelegated=true` and Q5=Yes, should the user be allowed to proceed to the Group step, or should the form still block? The current `CredentialingStatus` show condition renders the warning for this combination, which is contradictory to the user selecting "Yes." | Determines whether `CredentialingStatus` show condition needs a third AND clause (`IsCredentialedPNCDelegated=false`) | BA / Product |
| 2 | Are all practitioner demographic fields (name, DOB, gender, specialty, degree) set to `readOnly=true` when an existing NPI is found by `FetchExistingNPIInfo`? If this is handled by the LWC callback, confirm the mechanism and test coverage. | Read-only enforcement for prefill fields | Technical |
| 3 | Does `PRM_FetchExistingNPIInfo` IP explicitly return an `IsCredentialedPNCDelegated` boolean for all credentialed non-PNC practitioners? Is this derived from `Account.PRM_PNC__c = false` at the time of query? | Core data correctness for warning suppression logic | Technical |
| 4 | Should the Q5 label say "Is the Practitioner joining a PNC **Group**?" or "Is the Practitioner joining a PNC **practice location**?" — the requirement document uses "practice location" but the codebase uses "Group." | Label accuracy and user clarity | BA / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `CredentialingStatus` TextBlock | OmniScript Element | MEDIUM | Show condition must be regression-tested; UC-5 gap (PNC-delegated + Q5=Yes) needs business decision |
| `SetErrorsCredentialingStatus` | OmniScript Set Errors | LOW | No change needed for UC-2; regression test required |
| `PRM_FetchExistingNPIInfo` | Integration Procedure | HIGH | Must confirm `IsCredentialedPNCDelegated` is correctly returned for all credentialed non-PNC NPI lookups |
| Prefill field `readOnly` states | OmniScript Elements | MEDIUM | Each prefill field must be confirmed read-only when LWC populates it from NPI lookup |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `CredentialingStatus` TextBlock — UC-5 fix (if needed) | OmniScript config | S | One additional AND rule in show condition |
| `PRM_FetchExistingNPIInfo` IP — verification | IP review | S | Read IP logic; confirm `IsCredentialedPNCDelegated` output |
| Prefill `readOnly` verification | OmniScript element audit | M | Review all LWC-populated fields in PractitionerForm step |
| Regression testing (UC-2 through UC-6) | QA | M | Full matrix of NPI status × Q5 combinations |

**Total Estimated Effort:** AI-estimated — validate with team — **M**

---
---

# USER STORY 2: PAR Form — Block Navigation When Non-PNC Group Selected After Q5=Yes

**Persona:** Sr. Data Reporting Analyst, Developer  
**Priority:** P0  
**OmniScript:** `PRM_PractitionerParticipationForm_English`  
**Integration Procedures:** `PRM_IPExtractGroupNameBasedOnTINNPI`  
**Relevant Requirements:** Primary team concern — Apr 16, 2026; Use Case UC-8 above

---

## Story

**As a** Sr. Data Reporting Analyst completing the Practitioner Participation Form,  
**I want** the form to prevent me from advancing past the Group selection step when I have declared the practitioner is joining a PNC group but then select a non-PNC group,  
**So that** a PAR case is never submitted with a conflicting PNC intent and a non-PNC group affiliation, which would create data integrity issues in the credentialing workflow.

**Why it matters:** If a user declares PNC intent on the Practitioner step (Q5=Yes) but selects a non-PNC group on the Group step, the submitted case will carry a PNC flag that does not match the group affiliation. This corrupts downstream credentialing, network enrollment, and PNC reporting logic.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR | `PRM_PractitionerParticipationForm_English` | `PractionerGroup` (Step 2 — "Group") | `PRM_IPExtractGroupNameBasedOnTINNPI` IP; `pnc` Formula element; `IsPNCGroup` Formula; `MSG_PNCGroup` Validation |

---

## Current State (from codebase)

### `IsPNCGroup` (Formula — in `PractionerGroup` step)

- **Expression:** `IF(%PractitionerParticipationQuestion5% != null && %PractitionerParticipationQuestion5% == "Yes", true, false)`
- **Location:** `PRM_PractitionerParticipationForm_English_Element_IsPNCGroup.json`
- **Analysis:** Correctly evaluates to `true` when Q5=Yes. ✓ Used as `IsPNC` parameter in the IP call.

### `GroupTypeAhead` + `IPExtractGroupName` (Type Ahead Block + IP Action)

- **IP called:** `PRM_IPExtractGroupNameBasedOnTINNPI`
- **Extra payload:** `{ "IsPNC": "%IsPNCGroup%", "NPI": "%GroupNPI%", "TaxId": "%GroupTaxId%" }`
- **Location:** `PRM_PractitionerParticipationForm_English_Element_IPExtractGroupName.json`
- **Analysis:** The IP receives the `IsPNC=true` flag when Q5=Yes. **Whether the IP actually filters its results to PNC-only groups when `IsPNC=true` must be confirmed.** If filtering is absent or incomplete at the IP level, non-PNC groups can appear and be selected in the type-ahead.

### `pnc` (Formula — in `GroupInformation` block)

- **Expression:** `IF(%GroupInformation|n:ExistingGroupSelected% == false, false, %GroupInformation|n:pnc%)`
- **Location:** `PRM_PractitionerParticipationForm_English_Element_pnc.json`
- **Analysis:** Resolves to the `pnc` attribute of the selected group from the IP response, or `false` if no group is selected. This value correctly captures whether the selected group is PNC. ✓ **However, this formula is NOT referenced in `MSG_PNCGroup`'s `validateExpression`** — which is the critical gap.

### `MSG_PNCGroup` (Validation — in `GroupInformation` block)

- **Location:** `PRM_PractitionerParticipationForm_English_Element_MSG_PNCGroup.json`
- **Show condition:** Q5=Yes AND `GroupTypeAhead` field is not null
- **Failure message:** *"Please select an existing PNC group."* (type: "Requirement" — blocking)
- **Current `validateExpression` (success condition):**
  ```
  Q5 = "Yes"
  AND GroupInformation|n:GroupTypeAhead-Block:ExistingGroupId != null
  AND GroupInformation|n:GroupTypeAhead-Block:GroupTypeAhead != null
  ```
- **❌ CRITICAL GAP:** The validateExpression confirms that **a group was selected** (ExistingGroupId != null) but does **not** check whether that group is PNC (`pnc == true`). A non-PNC group with a valid ExistingGroupId will pass this validation.
- **Required fix:** Add `GroupInformation|n:pnc == true` as an AND condition in the validateExpression, so validation only passes when the selected group is actually PNC.

### `SetErrorNonPNCGroup` (Set Errors — root level)

- **Location:** `PRM_PractitionerParticipationForm_English_Element_SetErrorNonPNCGroup.json`
- **Current show condition:** `PractitionerParticipationQuestion5 == "No"`
- **Current elementErrorMap:** `{"PractitionerParticipationQuestion5": "=NULL"}`
- **validationRequired:** `"Step"`
- **❌ BUG:** The name "SetErrorNonPNCGroup" strongly implies this element should fire when a **non-PNC group is selected while Q5=Yes**, but its current show condition fires when **Q5="No"** — the opposite scenario. Additionally, its error map targets `PractitionerParticipationQuestion5` (a field on the Practitioner step, not the Group step) with the value `"=NULL"`, which appears to clear the error rather than set a meaningful blocking error. This element is not performing its intended function.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`MSG_PNCGroup`** | OmniScript Validation Element | **Add** `GroupInformation|n:pnc == true` as an additional AND condition in `validateExpression`. This makes the Requirement message block navigation when a non-PNC group is selected with Q5=Yes. |
| **`SetErrorNonPNCGroup`** | OmniScript Set Errors | **Fix show condition** from `Q5 == "No"` to `Q5 == "Yes" AND GroupInformation|n:pnc == false AND GroupInformation|n:ExistingGroupSelected == true`. Update `elementErrorMap` to target a field visible on the Group step (e.g., `GroupInformation|n:GroupTypeAhead-Block:GroupTypeAhead`) with a clear error message: `"The selected group is not a PNC group. Please select a PNC group to continue."` |
| **`PRM_IPExtractGroupNameBasedOnTINNPI`** | Integration Procedure | **Verify and enforce** that when `IsPNC=true` is passed in the payload, the IP filters the Account query/results to only return groups where `Account.PRM_PNC__c = true`. If this filter is missing, add a conditional SOQL filter or Decision node in the IP. |

### Updated `MSG_PNCGroup` validateExpression (target state)

```json
{
  "group": {
    "operator": "AND",
    "rules": [
      { "condition": "=", "data": "Yes", "field": "PractitionerParticipationQuestion5" },
      { "condition": "<>", "data": null, "field": "GroupInformation|n:GroupTypeAhead-Block:ExistingGroupId" },
      { "condition": "<>", "data": null, "field": "GroupInformation|n:GroupTypeAhead-Block:GroupTypeAhead" },
      { "condition": "=", "data": "true", "field": "GroupInformation|n:pnc" }
    ]
  }
}
```

### Updated `SetErrorNonPNCGroup` show condition (target state)

```json
{
  "group": {
    "operator": "AND",
    "rules": [
      { "condition": "=", "data": "Yes", "field": "PractitionerParticipationQuestion5" },
      { "condition": "=", "data": "true", "field": "GroupInformation|n:ExistingGroupSelected" },
      { "condition": "<>", "data": "true", "field": "GroupInformation|n:pnc" }
    ]
  }
}
```

### Updated `SetErrorNonPNCGroup` elementErrorMap (target state)

```json
{
  "GroupInformation|n:GroupTypeAhead-Block:GroupTypeAhead": "The selected group is not a PNC group. Please select a PNC group to continue."
}
```

---

## Acceptance Criteria

**Scenario 1 — Happy Path: Q5=Yes, PNC group selected → must proceed**

**Given** I am on the Group step of the PAR form and Q5 = "Yes" (joining a PNC group),  
**When** I type a group name in the type-ahead field and select a group whose `PRM_PNC__c = true`,  
**Then** no PNC validation error is shown,  
**AND** the `pnc` formula evaluates to `true`,  
**AND** the Next button is enabled and I can proceed to the next step.

---

**Scenario 2 — Block: Q5=Yes, non-PNC group selected → must not proceed**

**Given** I am on the Group step and Q5 = "Yes" (joining a PNC group),  
**When** I type a group name and select a group whose `PRM_PNC__c = false` (non-PNC),  
**Then** the `MSG_PNCGroup` validation fires with failure message: *"Please select an existing PNC group."*  
**AND** the `pnc` formula evaluates to `false`,  
**AND** `SetErrorNonPNCGroup` sets a visible, blocking error on the group name field,  
**AND** I cannot click Next — I am prevented from advancing.

---

**Scenario 3 — Block: Q5=Yes, group typed but not selected (ExistingGroupId=null) → must not proceed**

**Given** I am on the Group step and Q5 = "Yes",  
**When** I type partial text in the group name field but do NOT select a result from the type-ahead,  
**Then** `MSG_PNCGroup` shows failure state (ExistingGroupId is null),  
**AND** I cannot proceed until a valid existing PNC group is selected.

---

**Scenario 4 — Type-ahead filter: Q5=Yes → type-ahead shows PNC groups only**

**Given** I am on the Group step and Q5 = "Yes" (IsPNCGroup formula = true),  
**When** I type in the Group Name type-ahead,  
**Then** `IPExtractGroupName` is called with `IsPNC = true`,  
**AND** the type-ahead results list contains **only groups where `Account.PRM_PNC__c = true`**,  
**AND** non-PNC groups do NOT appear in the suggestion list.

---

**Scenario 5 — Q5=No → type-ahead shows all groups, no PNC restriction**

**Given** I am on the Group step and Q5 = "No" (IsPNCGroup formula = false),  
**When** I type in the Group Name type-ahead,  
**Then** `IPExtractGroupName` is called with `IsPNC = false`,  
**AND** the type-ahead returns groups regardless of PNC status,  
**AND** no PNC validation message appears.

---

**Scenario 6 — Repeat group block (multiple groups): Q5=Yes, second group is non-PNC**

**Given** the `GroupInformation` block is repeatable (up to 4 instances),  
**When** the first group is a valid PNC group and the second group selected is non-PNC (pnc=false),  
**Then** `MSG_PNCGroup` validation fires for the second group instance,  
**AND** the user cannot advance until the second group is replaced with a PNC group.

---

**Scenario 7 — Clearing group selection resets pnc flag**

**Given** I have selected a non-PNC group (pnc=false) and see the PNC error,  
**When** I clear the group name field and select a valid PNC group (pnc=true),  
**Then** the PNC error clears,  
**AND** the `pnc` formula re-evaluates to `true`,  
**AND** the Next button becomes enabled.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Does `PRM_IPExtractGroupNameBasedOnTINNPI` currently filter Account results by `PRM_PNC__c = true` when `IsPNC = true`? If not, is the intent to add this filter now, or rely solely on the OS-level `MSG_PNCGroup` validation as a safety net? | Determines whether IP change is in scope alongside OS changes | Technical |
| 2 | What is the `pnc` attribute path in the Type Ahead Block response JSON? Confirm the exact path the `pnc` formula reads from: `GroupInformation|n:pnc` — is this `Account.PRM_PNC__c` returned by the IP and mapped to the `pnc` field in the type-ahead response? | Required to confirm `pnc` formula is resolving against the correct data path | Technical |
| 3 | The `GroupInformation` block is repeatable (up to 4). Does `MSG_PNCGroup` validation fire independently per block instance, or once at the step level? If per-instance, confirm the formula path references for all instances. | Affects Scenario 6 and multi-group PNC enforcement | Technical |
| 4 | What should happen when the user selects a non-PNC group and then goes back to the Practitioner step and changes Q5 from "Yes" to "No"? Should the previously selected non-PNC group be cleared, or retained? | Determines whether a SetValues/clear logic is needed when Q5 changes | BA / Technical |
| 5 | Is the `SetErrorNonPNCGroup` element currently deployed and active? Its current show condition (Q5="No") appears to be a bug — confirm whether this element was ever functioning correctly or was introduced with incorrect logic. | Determines whether this is a regression or a new defect | Technical |
| 6 | The `pnc` formula in `GroupInformation` evaluates `IF(ExistingGroupSelected == false, false, GroupInformation|n:pnc)`. If the IP does not return a `pnc` attribute in its response, the formula resolves to `false` even for PNC groups — which would incorrectly block PNC group selection. Confirm the IP response payload includes a `pnc` attribute. | Core correctness of the entire validation chain | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `MSG_PNCGroup` Validation | OmniScript Element | HIGH | validateExpression must be updated to include `pnc == true` check; without this, non-PNC groups pass validation |
| `SetErrorNonPNCGroup` Set Errors | OmniScript Element | HIGH | Show condition is incorrect (fires on Q5=No instead of non-PNC group selection); must be fixed |
| `pnc` Formula | OmniScript Formula | MEDIUM | No change needed; verify IP returns `pnc` attribute; verify formula resolves correctly |
| `PRM_IPExtractGroupNameBasedOnTINNPI` | Integration Procedure | HIGH | Must add/confirm PNC filter when `IsPNC=true`; this is the first defense layer |
| `IsPNCGroup` Formula | OmniScript Formula | LOW | No change needed; correctly derives from Q5 |
| `GroupInformation` Block (repeat) | OmniScript Block | MEDIUM | Confirm validation behavior across all repeat instances |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `MSG_PNCGroup` — add `pnc` check to validateExpression | OmniScript config | S | One additional AND rule in validateExpression JSON |
| `SetErrorNonPNCGroup` — fix show condition + error map | OmniScript config | S | Update show condition + elementErrorMap values |
| `PRM_IPExtractGroupNameBasedOnTINNPI` — add PNC filter | IP logic change | M | Add conditional SOQL filter or Decision node based on IsPNC flag |
| `pnc` formula + IP response verification | IP/OS investigation | M | Confirm IP returns pnc attribute; trace data path through type-ahead response |
| Regression testing (all 7 AC scenarios + existing group flows) | QA | L | Full matrix: Q5=Yes/No × group PNC=true/false × repeat groups |

**Total Estimated Effort:** AI-estimated — validate with team — **L** (primarily testing and IP verification; OS config changes are small)

---

## Dependencies

- Story 1 (UC-2 happy path) must be regression-tested first to confirm baseline NPI lookup + Q5=Yes behavior is working.
- Confirmation from Technical that `PRM_IPExtractGroupNameBasedOnTINNPI` response payload includes a `pnc` attribute (prerequisite for MSG_PNCGroup fix to function correctly).
- Business decision on Clarification Question 1 (IP filter vs. OS-only validation) before IP change scope is finalized.

---

*End of Document*
