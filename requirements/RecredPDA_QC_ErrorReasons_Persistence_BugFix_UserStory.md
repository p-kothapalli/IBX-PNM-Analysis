# USER STORY 4: ReCred Network Management QC — Error Reasons Must Be Saved When a QC Review Is Completed

**Persona:** Network Management QC Specialist
**Priority:** P2
**OmniScript:** `PRM_ReCredQCUpdate_English` (v3, active) — QC review step
**Integration Procedures:** `PRM_RecredPDAUpdateRecords_Procedure` (v1, active) → DataRaptor `PRMUpdateIDCaseCaseMgr`
**Relevant Requirements:** New finding — `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §3 G4. No existing bug number.

---

## Story

**As a** Network Management QC Specialist,
**I want** the error reasons I select to be saved on the Case Manager even when I complete the QC review,
**So that** QC quality trends can be reported on and repeat data-entry problems by the PDA team can be identified and coached.

**Why it matters:** Error reasons are captured and saved correctly when a case is **returned** with errors, but they are **silently discarded** when the reviewer selects "QC Completed" — for example, when minor issues were noted but the case was still passed. There is no error message and the screen behaves normally, so no one knows the data is being lost. Any QC trend reporting built on this field is therefore incomplete and understates the true error rate.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Re-credentialing Network Management QC (`Network Management QC` stage) | `PRM_ReCredQCUpdate_English` | QC review step — error-reason selection | Case Manager update on submit |

**Out of scope:** the set of available error reasons; the "Errors Found" path, which already saves correctly; the display-guard defect (US-3).

---

## Current State (from codebase)

### The two QC outcomes write the error reasons under different names

| Persist element (active v3) | Key written on the Case Manager | Persists? |
|---|---|---|
| `SetRecordsErrorsFound` (Errors Found) | `ErrorReasons` — **plural** | **Yes** |
| `SetRecordQCCompleted` (QC Completed) | `ErrorReason` — **singular** | **No** |

- **Location:** `force-app/main/default/omniScripts/PRM_ReCredQCUpdate_English_3.os-meta.xml`

### The persistence layer only maps the plural name

The DataRaptor that writes the Case Manager maps exactly one error-reason path:

```
inputFieldName  : IndividualApplication:ErrorReasons
outputFieldName : PRM_ErrorReasons__c
```

- **Location:** `force-app/main/default/omniDataTransforms/PRMUpdateIDCaseCaseMgr_1.rpt-meta.xml`

### No singular field exists to receive the value

`IndividualApplication` has `PRM_ErrorReasons__c` (a multi-select picklist). There is **no** `PRM_ErrorReason__c`. The singular key therefore matches nothing, is silently ignored, and the selection is dropped without an error.

- **Location:** `force-app/main/default/objects/IndividualApplication/fields/PRM_ErrorReasons__c.field-meta.xml`

---

## Acceptance Criteria

**AC-1 — Error reasons are saved when QC is completed**

**Given** a Network Management QC Specialist has selected one or more error reasons on a re-credentialing QC review,
**When** they select the outcome "QC Completed" and submit,
**Then** the selected error reasons are saved on the Case Manager,
**And** they are visible on the Case Manager record afterwards,
**And** the case still completes and closes exactly as it does today.

**AC-2 — Records updated when QC is completed**

**Given** a Network Management QC Specialist completes a re-credentialing QC review with error reasons selected,
**When** they submit,
**Then** the following records are updated exactly as specified:

**Case Manager — Update**

| Field | Value | Notes |
|---|---|---|
| Stage | Complete | unchanged behaviour |
| Status | Approved | unchanged behaviour |
| Error Reasons | {error reasons selected by the QC Specialist} | **the fix** — currently dropped |
| Latest Case | {cleared} | unchanged behaviour |

**Case — Update**

| Field | Value | Notes |
|---|---|---|
| Status | Closed | unchanged behaviour |

**Note — Create**

| Field | Value | Notes |
|---|---|---|
| Title | Network Management QC Completed | unchanged behaviour |
| Body | {QC notes entered by the specialist} | unchanged behaviour |
| Related to | {the Case Manager} | unchanged behaviour |

**AC-3 — Completing with no error reasons selected leaves the field empty**

**Given** a Network Management QC Specialist completes a QC review **without** selecting any error reasons,
**When** they submit,
**Then** the Error Reasons field on the Case Manager is left empty,
**And** no previously saved error reasons are overwritten with a blank value if the case was returned earlier in its life,
**And** the case completes and closes normally.

**AC-4 — Returning the case with errors continues to work unchanged**

**Given** a Network Management QC Specialist selects error reasons and the outcome "Errors Found",
**When** they submit,
**Then** the error reasons are saved on the Case Manager exactly as they are today,
**And** the case is returned to the PDA team as it is today.

**AC-5 — Error reasons are reportable across both outcomes**

**Given** several re-credentialing cases have been through QC — some completed with error reasons noted, some returned with errors,
**When** a Network Management QC Specialist runs a QC error-reason report,
**Then** cases from **both** outcomes appear with their error reasons,
**And** the completed-with-errors cases are no longer missing from the results.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_ReCredQCUpdate_English` element `SetRecordQCCompleted` | Modified OmniScript element (new version) | Rename the Case Manager key from `ErrorReason` to `ErrorReasons` so it matches the DataRaptor's mapped input path | Drives AC-1, AC-2 |
| `PRMUpdateIDCaseCaseMgr` | No change | Already maps `IndividualApplication:ErrorReasons → PRM_ErrorReasons__c`; no new mapping needed once the key is corrected | Supports AC-1 |
| `PRMUpdateIDCaseMgrPNC` | Verify | The PNC-variant Case Manager DataRaptor also maps `PRM_ErrorReasons__c`; confirm the same key name is used if this flow can route through it | Supports AC-1 |
| Blank-overwrite behaviour | Review | Confirm submitting with no selection does not clear a previously populated multi-select value (see AC-3 and Clarification 2) | Drives AC-3 |

Single-element fix. No new fields, objects, Apex, or permission changes.

---

## Definition of done

- [ ] AC-1 verified in QA: error reasons selected on a completed QC review are visible on the Case Manager afterwards
- [ ] AC-2 verified by field inspection on the Case Manager, Case, and the created Note
- [ ] AC-3 verified: completing with no selection leaves the field empty and does not wipe an earlier value
- [ ] AC-4 verified: the "Errors Found" path still saves error reasons and returns the case
- [ ] AC-5 verified: a QC error-reason report returns cases from both outcomes
- [ ] New OmniScript version **activated** and verified by a Network Management QC Specialist in QA
- [ ] No regression to the rebuttal path on the same step

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Should error reasons be **required** when completing a QC review, or remain optional? | Changes AC-3 from "leave empty" to a blocking validation | BA / Product |
| 2 | If a case was returned with errors and later completed with none selected, should the earlier error reasons be preserved or cleared? | Determines whether the write must be conditional; affects trend reporting accuracy | BA |
| 3 | Has any existing QC reporting been built on this field, and does it need a note that historical completed-review data is missing? | Historical data cannot be recovered — reports may need a caveat or a start date | BA / Reporting |
| 4 | Can this flow route through the PNC-variant Case Manager update, and does it use the same key name? | May require the same rename in a second place | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_ReCredQCUpdate_English` | OmniScript | MEDIUM | One key renamed; new activated version |
| `IndividualApplication.PRM_ErrorReasons__c` | Field (data) | MEDIUM | Starts receiving values it never received before |
| QC trend reporting | Reporting | MEDIUM | Results change once data starts landing; historical gap remains |
| `PRMUpdateIDCaseCaseMgr` | DataRaptor | LOW | No change; already mapped correctly |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `SetRecordQCCompleted` key rename | OmniScript element | **S** | One-word change |
| Blank-overwrite verification | OmniScript / DataRaptor review | **S** | Confirm conditional-write behaviour |
| PNC-variant check | DataRaptor review | **S** | Confirm second path if applicable |
| Regression across both outcomes | QA | **M** | Includes a reporting check |

**Total Estimated Effort:** **S** (a couple of hours including regression) — AI-estimated, validate with team.
