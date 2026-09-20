# USER STORY: PDM — Website / Email Updates Must Not Trigger the "Overlapping Active Address" Error

**Persona:** PDM Specialist
**Priority:** P1
**Type:** Bug Fix / Enhancement
**OmniScript:** `PRM_PDMManualUpdatePracticeLocation_English` (v9)
**Integration Procedures:** `PRM_PDMRecordsCreationPracLocation` (v3) → `PRM_PDMCOIHelper` (v11); `PRM_PDMPLRecordsCreationHelper` (v4)
**DataRaptors:** `PRMLoadFacLocAddPCFUpdateCOI`
**Apex (validation source):** `PRM_AddressTriggerHandler.checkForOverlappingDatesOfAddresses()`
**Relevant Requirements:** Root-cause analysis → [`PDM_Address_Error_Analysis.md`](./PDM_Address_Error_Analysis.md)

---

## Story

**As a** PDM Specialist,
**I want** to update a practice location's **website address** or **office email** without changing the physical address,
**So that** my submission saves successfully instead of being blocked by an "Address is already Active for this Location" error for a change I never made to the address.

**Why it matters:** Today a PDM Specialist cannot update website/email in isolation. The guided flow bundles these two fields with the physical-address block under "Add/Update/Terminate Current Office Information," so the system always re-writes the Address record and the overlapping-date validation rejects the save. This forces manual workarounds, blocks routine provider data maintenance, and produces a confusing error message that has nothing to do with the change the specialist intended.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| PDM Manual Updates – Practice Location | `PRM_PDMManualUpdatePracticeLocation_English` | "Add/Update/Terminate Current Office Information" (COI step) | `PRM_PDMCOIHelper` → `PRMLoadFacLocAddPCFUpdateCOI` |
| PDM Manual Updates – Practice Location | `PRM_PDMManualUpdatePracticeLocation_English` | "Update Office Hours" step | `PRM_PDMPLRecordsCreationHelper` |

**In scope:** Website Address and Office Email behavior in the PDM Manual Update Practice Location flow.
**Out of scope:** Physical-address overlap validation logic itself (the trigger rule is correct and stays as-is for true address changes); the trigger is not being weakened.

---

## Current State (from codebase)

### OmniScript — `PRM_PDMManualUpdatePracticeLocation_English_9.os-meta.xml`
- Website Address and Office Email are presented on the **same step** as the physical practice-address fields (Address Line 1/2, City, State, Zip, Phone, Fax) under "Add/Update/Terminate Current Office Information."
- The `ErrorForCOIUpdate` change-detection formula treats `%OfficeAddress:WebsiteAddress%` and `%OfficeAddress:OfficeEmail%` as part of the same "COI changed" decision as the physical-address fields — there is no separation between an address change and a website/email change.

### Integration Procedure — `PRM_PDMCOIHelper_Procedure_11.oip-meta.xml`
- Line **362** the `DRLoadAddressWithId` step explicitly sets `"Address:Pending" : false`.
- Because `PRM_Pending__c = false`, the trigger's bypass condition is **not** met, so the overlapping-address validation always runs on the COI save path — even when only website/email changed.

### DataRaptor — `PRMLoadFacLocAddPCFUpdateCOI_1.rpt-meta.xml`
- Writes to **`HealthcareFacility`** (for `PRM_WebsiteAddress__c` and `PRM_OfficeEmail__c`) **and** to **`Address`** (physical fields plus `PRM_AddressType__c` and `PRM_Active__c`) in the same transform.
- The Address upsert fires **unconditionally** as part of the COI update, so an active address of the same type is re-inserted/updated on the same Location even when no physical-address field changed.

### Apex validation — `PRM_AddressTriggerHandler.checkForOverlappingDatesOfAddresses()` (line ~164–185)
- On `beforeInsert`/`beforeUpdate`, for each incoming active address it looks up existing active addresses on the same `ParentId` (Location) with the same address type and overlapping effective dates, and calls `addError(...)` with: *"An Address is already Active for this Location with the same Type. Please verify there are no overlapping dates and deactivate before proceeding."*
- The rule itself is correct for genuine address changes; the defect is that website/email-only updates reach this code path at all.

### Data-model mismatch
| Field | Where it actually lives |
|-------|--------------------------|
| Website Address | `HealthcareFacility.PRM_WebsiteAddress__c` |
| Office Email | `HealthcareFacility.PRM_OfficeEmail__c` |
| Physical Address | `Address` object |

`PRM_PDMPLRecordsCreationHelper` (v4) already contains an **"Update Office Hours"** manual-update type (`CM:ManualUpdateType = "Update Office Hours"`) with an `OfficeHoursStep` that writes only to `HealthcareFacility` — i.e., a clean, Address-free save path already exists.

---

## Technical Section (For Developers)

> **Selected approach: relocate Website Address and Office Email to the "Update Office Hours" step.** These two fields move off the "Add/Update/Terminate Current Office Information" (COI) step entirely and are captured on the "Update Office Hours" step, which already saves only to `HealthcareFacility` and never touches the `Address` object. This is the business-requested target state and the basis for the ACs above. (A tactical alternative — conditionally suppressing the Address DML on the COI path — is recorded in the analysis doc but is not the chosen approach.)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_PDMManualUpdatePracticeLocation_English` (→ v10) | OmniScript | **Remove** Website Address and Office Email from the "Add/Update/Terminate Current Office Information" step. **Add** them to the "Update Office Hours" step as **optional** (not required) fields, pre-populated with current values. Remove `%OfficeAddress:WebsiteAddress%` and `%OfficeAddress:OfficeEmail%` from the `ErrorForCOIUpdate` formula so website/email no longer trigger the COI/Address save path. |
| Office Hours step "dirty check" | OmniScript formula + Validation/disabled-Next | Capture the originally loaded Office Hours, Website Address, and Office Email values; add a formula that is true only when at least one differs from its original; drive a Validation element / disabled Next button off it with the message *"Please update at least one field (Office Hours, Website Address, or Office Email) before proceeding."* |
| `PRM_PDMPLRecordsCreationHelper` (→ v5) | Integration Procedure | In the "Update Office Hours" branch (`CM:ManualUpdateType = "Update Office Hours"` / `OfficeHoursStep`), also write `HealthcareFacility.PRM_WebsiteAddress__c` and `HealthcareFacility.PRM_OfficeEmail__c`. **No Address DML** in this branch. |
| Office Hours DataRaptor (new/modified Load DR) | DataRaptor | Add `PRM_WebsiteAddress__c` and `PRM_OfficeEmail__c` to the `HealthcareFacility` output. No `Address` object mapping. |
| `PRMLoadFacLocAddPCFUpdateCOI` / `PRM_PDMCOIHelper` | DataRaptor / IP | Remove the now-orphaned website/email mappings from the COI path so the COI step writes only physical-address fields. |

### Notes
- The physical-address overlapping-date validation in `PRM_AddressTriggerHandler` must remain **unchanged** and continue to fire for genuine address changes (guards AC-7).
- Website/email continue to be stored on `HealthcareFacility` (`PRM_WebsiteAddress__c`, `PRM_OfficeEmail__c`) — no schema change; only the capture point and save path move.

---

## Acceptance Criteria

**AC-1 — Website Address and Office Email are removed from the COI step**

**Given** a PDM Specialist opens the "Add/Update/Terminate Current Office Information" step in the PDM Manual Update – Practice Location flow,
**When** the step renders,
**Then** the Website Address field is no longer present on this step,
**And** the Office Email field is no longer present on this step,
**And** only physical-office fields (Address Line 1/2, City, State, Zip, Phone, Fax) remain.

**AC-2 — Website Address and Office Email appear on the "Update Office Hours" step**

**Given** a PDM Specialist opens the "Update Office Hours" step in the PDM Manual Update – Practice Location flow,
**When** the step renders,
**Then** a Website Address field is available for entry/edit,
**And** an Office Email field is available for entry/edit,
**And** both fields are pre-populated with the location's current values.

**AC-3 — Updating website/email from the Office Hours step saves without an address error**

**Given** a PDM Specialist is on the "Update Office Hours" step for a location that has an existing active practice address,
**When** they change the website address and/or office email and submit,
**Then** the new website address and/or office email are saved on the practice location,
**And** the existing physical address is left unchanged,
**And** no "Address is already Active for this Location" error is shown.

**AC-4 — Website and Office Email are individually optional on the Office Hours step**

**Given** a PDM Specialist is on the "Update Office Hours" step and has changed the office hours,
**When** they leave website and/or office email blank and submit,
**Then** the flow does not require website or office email to be filled in,
**And** the submission completes successfully.

**AC-5 — Office hours can be updated together with website/email in one submission**

**Given** a PDM Specialist is on the "Update Office Hours" step and changes the office hours along with the website address and office email,
**When** they submit,
**Then** the updated office hours, website address, and office email are all saved on the practice location,
**And** no address record is created or modified,
**And** no overlapping-address error is shown.

**AC-6 — At least one change is required before the Office Hours step can proceed**

**Given** a PDM Specialist is on the "Update Office Hours" step and has not changed the office hours, the website address, or the office email from their current values,
**When** they try to proceed / submit,
**Then** the system blocks them with a validation message such as *"Please update at least one field (Office Hours, Website Address, or Office Email) before proceeding."*,
**And** the flow does not advance,
**And** no record is created or updated.

**AC-7 — Proceeding is allowed as soon as any one field changes**

**Given** a PDM Specialist is on the "Update Office Hours" step,
**When** they change any single field — the office hours, the website address, or the office email,
**Then** the validation message clears,
**And** they are allowed to proceed / submit.

**AC-8 — The COI step no longer re-writes the address for website/email changes**

**Given** a PDM Specialist completes the "Add/Update/Terminate Current Office Information" step without changing any physical-address field,
**When** they submit,
**Then** no new or duplicate address record is created for the location,
**And** no overlapping-address error is shown.

**AC-9 — Genuine physical-address change still validates overlaps (no regression)**

**Given** a PDM Specialist edits a physical-address field on the COI step (e.g., Address Line 1, City, State, or Zip) in a way that would create a second active address of the same type with overlapping effective dates on the same location,
**When** they submit the flow,
**Then** the system still blocks the save with the "Address is already Active for this Location with the same Type…" message,
**And** the existing overlap protection behaves exactly as it does today.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PDMManualUpdatePracticeLocation_English` | New OmniScript version (→ v10) | Remove Website Address + Office Email from COI step; add them (optional) to the "Update Office Hours" step | Drives AC-1, AC-2, AC-4 |
| `ErrorForCOIUpdate` formula | OmniScript formula | Remove `WebsiteAddress`/`OfficeEmail` from the COI change comparison | Drives AC-1, AC-8 |
| Office Hours "dirty check" (OmniScript validation / disabled-Next condition) | OmniScript formula + Validation element | Compare current Office Hours / Website / Email against their originally loaded values; block Next/Submit with a message until at least one differs | Drives AC-6, AC-7 |
| `PRM_PDMPLRecordsCreationHelper` | New IP version (→ v5) | Office Hours branch writes website/email to `HealthcareFacility`; no Address DML | Drives AC-3, AC-5 |
| Office Hours Load DataRaptor | New/modified DataRaptor | Add website/email to `HealthcareFacility` output (also captures the original values for the dirty check) | Drives AC-3, AC-5 |
| `PRMLoadFacLocAddPCFUpdateCOI` / `PRM_PDMCOIHelper` | DataRaptor / IP | Drop orphaned website/email mappings from the COI path | Drives AC-8 |
| `PRM_AddressTriggerHandler` | Apex (unchanged) | No change — overlap validation must still fire for true address edits | Guards AC-9 |

Deeper design notes (IP step expressions, DataRaptor output config, field placement on the Office Hours step) to be captured in a companion `requirements/Enhancements/` doc.

---

## Definition of Done

- [ ] Website Address and Office Email are removed from the "Add/Update/Terminate Current Office Information" (COI) step (AC-1).
- [ ] Website Address and Office Email appear (optional, pre-populated) on the "Update Office Hours" step (AC-2, AC-4).
- [ ] Website/email updates submitted from the Office Hours step save without the overlapping-address error and without touching the Address record (AC-3, AC-5).
- [ ] The Office Hours step blocks Next/Submit with a clear message when nothing (office hours, website, or email) has changed, and clears once any one field changes (AC-6, AC-7).
- [ ] The COI step no longer creates/modifies an Address record when no physical-address field changed (AC-8).
- [ ] Genuine overlapping physical-address changes are still blocked by the trigger (AC-9 — regression check).
- [ ] `PRM_AddressTriggerHandler` and its tests remain green; new Office Hours save path covered by unit/integration tests.
- [ ] Deployed and validated in QA sandbox per project deployment workflow.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirmed: website/email move to the "Update Office Hours" step and are fully removed from the COI step (not left read-only). Any objection? | OmniScript layout and user retraining | BA / Product |
| 2 | Should website/email updates be auditable/case-logged the same way address changes are today? | Audit/compliance and downstream notifications | Ops / Compliance |
| 3 | Should the "Update Office Hours" step be renamed (e.g., "Update Office Hours, Website & Email") to reflect the added fields? | UX clarity / user training | BA / Product |
| 4 | Are there other PDM flows (e.g., Account-level updates) that bundle website/email with address and have the same defect? | Scope creep / additional stories | Technical |
| 5 | Confirm the canonical persona label — is "PDM Specialist" correct for this flow? | Story header accuracy | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_PDMManualUpdatePracticeLocation_English` | OmniScript | HIGH | Remove website/email from COI step, add to Office Hours step; `ErrorForCOIUpdate` formula change; new version required |
| `PRM_PDMPLRecordsCreationHelper` | Integration Procedure | HIGH | Office Hours branch enhanced to write HCF website/email; new version |
| Office Hours Load DataRaptor | DataRaptor | MEDIUM | Add `PRM_WebsiteAddress__c` / `PRM_OfficeEmail__c` to HCF output |
| `PRM_PDMCOIHelper` / `PRMLoadFacLocAddPCFUpdateCOI` | IP / DataRaptor | MEDIUM | Remove orphaned website/email mappings from the COI path |
| `PRM_AddressTriggerHandler` | Apex | LOW | No code change; must be regression-verified |
| `HealthcareFacility` (`PRM_WebsiteAddress__c`, `PRM_OfficeEmail__c`) | Object/Fields | LOW | Existing fields; no schema change |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_PDMManualUpdatePracticeLocation_English` | OmniScript step move + formula change | L | Remove 2 fields from COI step, add to Office Hours step, edit `ErrorForCOIUpdate`; new version + retest |
| Office Hours "dirty check" validation | OmniScript formula + Validation element | M | Compare loaded vs. current values; block Next/Submit with message until one changes |
| `PRM_PDMPLRecordsCreationHelper` | IP branch enhancement | L | Write website/email to HCF in the Office Hours branch; new version |
| Office Hours Load DataRaptor | DataRaptor field add | M | Add website/email to HCF output |
| `PRM_PDMCOIHelper` / `PRMLoadFacLocAddPCFUpdateCOI` | IP / DataRaptor cleanup | M | Remove orphaned website/email mappings from COI path |
| Regression coverage | Apex test verification | M | Confirm overlap validation still fires for real address edits |

**Total Estimated Effort:** ~XL (1–2 days).
