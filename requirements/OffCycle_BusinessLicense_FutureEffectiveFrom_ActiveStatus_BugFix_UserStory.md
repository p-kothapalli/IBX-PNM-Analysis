# USER STORY: Off Cycle Credentialing — A Business License With a Future Effective From Date Must Not Be Marked Active

**Persona:** Credentialing Specialist
**Priority:** P1
**OmniScript:** `PRM_OffCycleCredentialing_English` (v63 — active), `PRM_OffCycleVerification_English` (v38 — active)
**Integration Procedures:** `PRM_validateBusinessLicences`, `PRM_OffCycleRecordsUpdateParent` → `PRM_OffCycleRecordsUpdate_Procedure`, `PRM_OffCycleRecordCreationParent` → `PRM_OffCycleRecordCreation_Procedure`
**Relevant Requirements:**
- ADO Requirement **1484314** — *Off Cycle Credentialing - Future Date - Active Status Update for Business License Effective Date update* (Sprint 65, IHG\BTS EIM\Provider Network Management)
- `requirements/AncillaryPSV_BusinessLicense_DateValidation_Relax_UserStory.md` — sibling license-date story (Ancillary PSV). **Open Question 2 in that story asks exactly this question for the Ancillary flow; this story answers it for Off Cycle.**
- `requirements/OffCycle_NewRegionState_EffectiveDate_UserStory.md` — sibling Off Cycle effective-date story (Level 4 records)
- `requirements/FutureDated_Termination_PushOut_UnitTest_Scenarios.md` — existing Future Dated Processing behaviour

---

## Story

**As a** Credentialing Specialist processing an off-cycle change for a practitioner,
**I want** a business license whose Effective From date is in the future to be saved as **not active** until that date arrives, and then to become active on its own,
**So that** the provider directory, network loads and downstream reporting never show a license as live before the date IBX agreed it takes effect.

**Why it matters:** Active licenses flow straight into provider data that IBX publishes and loads to networks. A license that is flagged Active weeks before its effective date tells every downstream consumer the practitioner is credentialed in that state today — which is a compliance and data-integrity exposure, and the kind of defect that gets found in an audit rather than in QA. The form already tells the specialist that "Active is automatically calculated upon submission", so today's behaviour also contradicts the product's own promise.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Off Cycle Credentialing | `PRM_OffCycleCredentialing_English` (v63) | `CollectAndVerifyNewInformation` → `BusinessLicenseEditBlock` | `PRM_OffCycleWrapper` (load) / `PRM_OmniUtils.updateBusinessLicense` (save) |
| Off Cycle Verification | `PRM_OffCycleVerification_English` (v38) | `CollectAndVerifyNewInformation` payload forwarded to the record-save IPs | Same save path — `PRM_OmniUtils.updateBusinessLicense` |
| Future-dated activation | N/A | Nightly activation run | `PRM_FutureDatedProcessing__c` + `PRM_FutureDatedProcessingBatch` |

**In scope:** the Active flag calculation on business license **save**, the in-form guard that stops a specialist marking a future-dated license Active, and enrolling Business License into the existing future-dated activation framework so the license activates on its date.

**Out of scope:** the Credentials action panel on the Case Manager (a separate save path that does not write Active or Effective From today), the Ancillary PSV license modal, and any change to Effective **To** / termination behaviour.

---

## Current State (from codebase)

### The defect — the update path trusts the form, the create path does not

| Path | Behaviour today | Location |
|---|---|---|
| **New license row** (no Id) | **Correct.** Active is calculated: it is true only when Effective From is empty or on/before today. | `PRM_OmniUtils.buildBusinessLicenseForCreate` (line 784) |
| **Existing license row** (has Id) | **Defect.** Active is copied straight from the form's checkbox with no date check, so a future Effective From saves as Active. | `PRM_OmniUtils.buildBusinessLicenseForUpdate` (lines 818–820) |

### Supporting findings

- The **Active checkbox is editable** in the Off Cycle Credentialing license block, and its own help text reads *"Active is automatically calculated upon submission."* — the field is presented as system-calculated but behaves as user-controlled. Effective From and Effective To in the same block are already read-only.
- The in-form license validation (`PRM_ValidateBusinessLicenseRA.validateLicenses`) checks only two things: Active **and** Pending both ticked, and duplicate State + Number + Class. **There is no effective-date rule.** An effective-date block exists but is commented out (lines 59–67).
- **Off Cycle Verification does not render the license block** — it forwards the payload captured earlier into the same two record-save Integration Procedures. A guard placed in Apex therefore covers both forms; an in-form guard only covers Off Cycle Credentialing.
- **Business License has no trigger and is not enrolled in Future Dated Processing.** There is no `BusinessLicense` trigger in `force-app/main/default/triggers/`, and no Business License handling in `PRM_FutureDatedProcessingUtil`. So today, even if the license were saved inactive, **nothing would ever activate it.** Every comparable credential object (Board Certification, Identifier, Address, Healthcare Provider Npi, …) is enrolled via a trigger handler that calls `PRM_FutureDatedProcessingUtil.createRecords`.
- Two reuse blockers were found in the existing framework and are specced in Technical Implementation below: the util reads `PRM_IsErrorRecord__c` (Business License has `PRM_IsError__c` instead), and the activation batch writes the literal `'Active'` into any `Status` field it finds — Business License uses `Status` for **verification** status (Verified / On Hold), so it would be clobbered.

---

## Acceptance Criteria

### AC-1 — A license dated to start in the future is saved as not active *(happy path)*

**Given** a Credentialing Specialist is working an off-cycle change for a practitioner who has a business license whose Effective From date is later than today,
**When** they submit the off-cycle form,
**Then** the license is saved as **not active**,
**And** the license remains visible to the specialist with its future Effective From date unchanged,
**And** no error is shown — the submission completes normally.

### AC-2 — The specialist is stopped from marking a future-dated license as Active *(negative path)*

**Given** a Credentialing Specialist is on the step that lists the practitioner's business licenses in the Off Cycle Credentialing form,
**And** one license has an Effective From date later than today,
**When** they tick **Active** on that license and try to move to the next step,
**Then** the form blocks them with the message *"A license with a future Effective From date cannot be marked Active. It will activate automatically on its Effective From date."*,
**And** the specialist cannot proceed until they clear the Active tick.

### AC-3 — A license already in effect stays active *(regression)*

**Given** a Credentialing Specialist is working an off-cycle change for a practitioner whose business license has an Effective From date of today or earlier,
**When** they submit the off-cycle form,
**Then** the license is saved as **active**, exactly as it is today,
**And** none of the license's other captured details are altered by this change.

### AC-4 — A license with no Effective From date stays active *(edge case)*

**Given** a Credentialing Specialist is working an off-cycle change for a practitioner whose business license has no Effective From date recorded,
**When** they submit the off-cycle form,
**Then** the license is saved as **active**,
**And** no future-dated activation is scheduled for it.

### AC-5 — How the Active flag is decided *(Pattern D — Active calculation rules)*

**Given** a business license is being saved from either off-cycle form,
**When** the submission is processed,
**Then** the Active flag is calculated by the system — never taken from the specialist's tick — using these rules:

- **Active =**
  - When Effective From is empty → **Active**
  - When Effective From is today or earlier → **Active**
  - When Effective From is later than today → **Not Active**
- **Pending =** unchanged by this story — a future-dated license is simply not yet active, it is not put into a pending state
- **Effective From =** as captured on the form; this story never changes the date itself
- **Effective To =** unchanged by this story

### AC-6 — Records written on submit *(Pattern E — record & field specification)*

**Given** a Credentialing Specialist submits an off-cycle form containing business license rows,
**When** the submission is processed,
**Then** the following records are created/updated exactly as specified:

**Business License — Update** *(existing license rows — rows carrying a record Id)*

| Field | Value | Notes |
|---|---|---|
| Name | {License Number} | only when License Number is provided |
| License Number | {License Number} | as captured |
| License Class | {License Class} | as captured |
| License State | {License State} | as captured |
| Effective From | {Effective From} | as captured; read-only in the form |
| Effective To | {Effective To} | as captured; read-only in the form |
| License Effective Date | {License Effective Date} | as captured |
| License Expiration Date | {License Expiration Date} | as captured |
| Verified Date | {Verified Date} | as captured |
| **Active** | **Calculated per AC-5** | **CHANGED BY THIS STORY** — no longer copied from the form's tick |
| Pending | {Pending} | as captured; unchanged by this story |

**Business License — Create** *(newly added license rows — no record Id)*

| Field | Value | Notes |
|---|---|---|
| — | — | **No change.** The create path already calculates Active per AC-5 and is correct today. Listed so QA confirms create and update now behave identically. |

**Future Dated Processing — Create** *(only when Effective From is later than today)*

| Field | Value | Notes |
|---|---|---|
| Effective Date | {Effective From} | the date the license should switch on |
| Object API Name | Business License | identifies what to activate |
| Record To Process | {the Business License record} | the license being scheduled |
| Status | Activate | distinguishes activation from termination |
| External Id | {Business License record}_Activate | prevents duplicate scheduling if the form is resubmitted |
| Record Type | *(blank)* | Business License has no record types |

### AC-7 — The license switches itself on when its date arrives

**Given** a business license was saved as not active because its Effective From date was in the future,
**When** that Effective From date arrives,
**Then** the license becomes **active** without anyone reopening the case,
**And** it appears as active to the Credentialing Specialist and to downstream provider data on that date and not before.

### AC-8 — Activation must not disturb the license's verification status *(negative path / regression)*

**Given** a business license is scheduled to activate on a future date and its verification status is recorded as Verified or On Hold,
**When** the license activates on its Effective From date,
**Then** its verification status is **unchanged**,
**And** the only thing that changes is that the license becomes active.

### AC-9 — Off Cycle Verification is protected by the same rule *(regression)*

**Given** a Credentialing Specialist submits the Off Cycle Verification form for a practitioner whose business license carries a future Effective From date,
**When** the submission is processed,
**Then** the license is saved as not active and scheduled to activate on its date, exactly as in AC-1 and AC-6,
**And** the rest of the Off Cycle Verification submission completes unchanged.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_OmniUtils.buildBusinessLicenseForUpdate` | Apex — bug fix | Replace the `ebIsactive` passthrough (lines 818–820) with the same calculation the create path already uses: `IsActive = PRM_EffectiveFrom__c == null \|\| PRM_EffectiveFrom__c <= Date.today()`. Extract it into one shared private helper so create and update can never drift again. | **Root-cause fix.** Drives AC-1, AC-3, AC-4, AC-5, AC-6, AC-9 |
| `PRM_ValidateBusinessLicenseRA.validateLicenses` | Apex — enhancement | Add a third rule beside the existing Active+Pending and duplicate checks: reject a row where `ebIsactive` is true and `ebEffectiveFrom > TODAY`, with the AC-2 message. Reuse the existing `Row N: …` error format so it renders in the current warning banner. | Drives AC-2 |
| `PRM_OffCycleCredentialing_English` v64 — `BusinessLicenseEditBlock:ebIsactive` | OmniScript | Set `readOnly: true` on the Active checkbox so it displays the calculated value rather than inviting edits — consistent with `ebEffectiveFrom` / `ebEffectiveTo`, which are already read-only, and with the field's own help text. Keep the AC-2 validation as the safety net for cached sessions. | Drives AC-2. Confirm with the BA — see CQ2 |
| `PRM_BusinessLicenseTrigger` + `PRM_BusinessLicenseTriggerHandler` | New Apex trigger + handler | Mirror `PRM_BoardCertificationTrigger` exactly: after insert/update, guarded by `FeatureManagement.checkPermission('PRM_TriggerBypassPermission')`, calling `PRM_FutureDatedProcessingUtil.createRecords(scope, 'BusinessLicense')`; on update, only for rows where Effective From, Effective To or Pending changed. | Drives AC-6 (Future Dated Processing rows) and AC-7. See CQ1 for the trigger-vs-inline alternative |
| `PRM_FutureDatedProcessingUtil.createRecords` | Apex — defect guard | The method reads `PRM_IsErrorRecord__c` unconditionally; **Business License does not have that field** (it has `PRM_IsError__c`), so the call throws `System.SObjectException: Invalid field` as written. Resolve the error-flag API name per object via describe — same technique already used for the effective-from / active fields — or add a Business License case alongside the existing `BoardCertification` special-casing in `getFieldApiName`. | **Blocker for reuse.** Drives AC-6, AC-7 |
| `PRM_FutureDatedProcessingBatchHandler.processRecords` | Apex — defect guard | On activation the batch writes the literal `'Active'` into any `Status` field the object has (lines 123–137). Business License uses `Status` for **verification** status (Verified / On Hold), so activation would clobber it — and `'Active'` is likely not even a valid picklist value, which would fail the DML. Skip the `Status` write for Business License. | **Blocker for reuse.** Drives AC-8 |
| `PRM_FutureDatedProcBatchSchActivation` / `PRM_FutureDatedProcessingBatch` | Verification only — no change expected | Confirm the activation scheduler (`PRM_FutureDatedProcBatchSchActivation` → `PRM_FutureDatedProcessingBatch`) needs no change — it selects on `PRM_FutureDatedProcessing__c` and resolves the object generically, so adding a new object API name requires no batch edit. | Drives AC-7 |
| `PRM_OmniUtilsTest`, `PRM_ValidateBusinessLicenseRATest`, `PRM_FutureDatedProcessingUtilTest`, `PRM_FutureDatedProcBatchHandlerTest`, new `PRM_BusinessLicenseTriggerHandlerTest` | Apex tests | Cover future / today / past / null Effective From on both create and update; the AC-2 rejection; Future Dated Processing row creation and its external-Id de-duplication; activation leaving verification status untouched; bulk (200 license rows). | ≥ 85% coverage gate |

**Field reference for the AC-6 tables**

| Business label used in the ACs | API name |
|---|---|
| Active | `BusinessLicense.IsActive` |
| Effective From / Effective To | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` |
| License Effective Date / License Expiration Date | `PRM_ProviderLicenseEffectiveDate__c` / `PRM_ProviderLicenseExpirationDate__c` |
| License State / License Number / License Class | `PRM_LicenseState__c` / `LicenseNumber` / `LicenseClass` |
| Verified Date / Pending | `VerifiedDate` / `PRM_Pending__c` |
| Effective Date / Object API Name / Record To Process / Status / External Id / Record Type *(Future Dated Processing)* | `PRM_EffectiveDate__c` / `PRM_ObjectApiName__c` / `PRM_SObjectRecordId__c` / `PRM_Status__c` / `PRM_ExternalId__c` / `PRM_RecordType__c` |

---

## Definition of done

- [ ] A license with a future Effective From date submits from Off Cycle Credentialing and persists as not active (AC-1).
- [ ] Ticking Active on a future-dated license blocks progression with the AC-2 message; clearing the tick unblocks it (AC-2).
- [ ] Licenses dated today, dated in the past, and with no Effective From date all still persist as active (AC-3, AC-4).
- [ ] Create and update paths produce an identical Active value for the same input — verified by a test that runs both (AC-5).
- [ ] A Future Dated Processing row is created for the future-dated license with Status `Activate`, and resubmitting the form does not create a second one (AC-6).
- [ ] On the license's Effective From date the activation run flips it to active, and its verification status is unchanged (AC-7, AC-8).
- [ ] Off Cycle Verification submits with the same result (AC-9).
- [ ] Board Certification, Identifier, Address and the other objects already enrolled in Future Dated Processing regress cleanly — no change to their activation or termination behaviour.
- [ ] ≥ 85 % Apex coverage across the changed classes, including bulk (200 license rows) and the negative paths.
- [ ] No hardcoded Ids; license writes stay bulk-safe at one DML per object type.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | **Trigger or inline?** A `BusinessLicense` trigger is the org's paved path (it mirrors Board Certification and also covers data loads and any future save path), but it is a new trigger on a shared object. The alternative is calling `PRM_FutureDatedProcessingUtil.createRecords` inline at the end of `updateBusinessLicense`, which is smaller but only covers the off-cycle forms. Recommendation: trigger. | Blast radius vs. coverage | Technical |
| 2 | **Should the Active checkbox become read-only,** or stay editable with only the AC-2 validation stopping the invalid combination? Read-only matches the field's own help text but removes the specialist's ability to deactivate a license from this form. | UI behaviour, AC-2 | Product / BA |
| 3 | **Existing bad data:** how many licenses are already Active with a future Effective From date in QA and Production, and do they need a one-off correction script? This story fixes forward only. | Data remediation scope | BA / Ops |
| 4 | **Separate finding — Status is captured but never saved.** The license block collects a Status value (On Hold / Verified) but neither the create nor the update path writes `BusinessLicense.Status`. Should this be raised as its own defect? | Out of scope here; likely a real second bug | BA / Technical |
| 5 | **Ancillary parity:** the Ancillary PSV license story explicitly left "is a future-dated effective date acceptable?" open. Should the Ancillary modal adopt the same rule now, or stay as-is until asked? | Cross-flow consistency | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_OmniUtils` | Apex | **HIGH** | Shared utility fronting many off-cycle remote actions; the license save path is the only method changed, but the class is widely used — regress the other off-cycle remote actions |
| `PRM_FutureDatedProcessingUtil` | Apex | **HIGH** | Shared by every object enrolled in future-dated processing; the error-field fix touches a code path all of them run |
| `PRM_FutureDatedProcessingBatchHandler` | Apex | **HIGH** | Nightly activation and termination for all enrolled objects; the `Status` guard must not alter behaviour for objects that legitimately expect `Status = 'Active'` |
| `PRM_BusinessLicenseTrigger` (new) | Apex trigger | **MEDIUM** | First trigger on `BusinessLicense`; every license insert/update in the org now runs it, including the Ancillary and Credentials-action paths |
| `PRM_OffCycleCredentialing_English` | OmniScript | **MEDIUM** | New version required; license block validation and Active checkbox |
| `PRM_ValidateBusinessLicenseRA` | Apex | **LOW** | Single-purpose validation class used only by the license block |
| `PRM_OffCycleVerification_English` | OmniScript | **LOW** | No metadata change — inherits the Apex-side guard |

---

## Estimated Effort *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Story Points | Notes |
|---|---|---|---|---|
| `PRM_OmniUtils.buildBusinessLicenseForUpdate` | Apex bug fix | **M** | 2 | The root-cause fix is a few lines; extracting the shared helper is the rest |
| `PRM_ValidateBusinessLicenseRA` | Apex enhancement | **M** | 2 | Third rule in an existing loop, reusing the error format |
| `PRM_OffCycleCredentialing_English` v64 | OmniScript | **M** | 2 | Checkbox property + new version + activation |
| `PRM_BusinessLicenseTrigger` + handler | New Apex trigger + handler | **L** | 3 | Direct mirror of the Board Certification pattern |
| `PRM_FutureDatedProcessingUtil` error-field fix | Apex defect guard | **L** | 3 | Shared class — the regression surface is the cost, not the code |
| `PRM_FutureDatedProcessingBatchHandler` Status guard | Apex defect guard | **M** | 2 | One conditional, but must be proven safe for all enrolled objects |
| Apex tests (5 classes) | Apex tests | **L** | 3 | Future / today / past / null, bulk 200, activation-day assertions |
| Regression QA — other future-dated objects | QA | **M** | 2 | Board Certification, Identifier, Address, Account activation + termination |

**Total Estimated Effort:** ~19 story points — **XL** (roughly 2–3 engineer-days of build plus a regression pass).

> The headline defect is a two-line fix. The effort sits almost entirely in AC-7: Business License has never been enrolled in future-dated processing, and enrolling it surfaces two latent defects in the shared framework (the error-field name and the `Status` overwrite). If AC-7 is deferred to a follow-up story, this drops to roughly **M/L — 6 points**, but licenses would then stay inactive until someone activates them by hand.
