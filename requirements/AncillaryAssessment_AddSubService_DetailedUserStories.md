# Ancillary Assessment — Add Provider Type / Sub-Service — Detailed User Stories

**Status:** Draft for business sign-off
**Created:** 2026-06-02
**Updated:**
- *2026-06-02 (v3)* — routing rule corrected: reuse the in-flight Case Manager ONLY when its Provider Type matches the submission's Provider Type.
- *2026-06-03 (v4)* — **stories consolidated**. The old US-001 (resolver), US-002 (Scenario 1 reuse), US-003 (Scenario 2A past-PSV), and US-004 (Scenario 2B approved-only) have been merged into a single, expanded **US-001 — Form-submission routing & record-creation contract** that owns every record outcome of an Ancillary form submission. Old US-005 → US-009 have been renumbered down to US-002 → US-006 accordingly. All cross-references in the doc reflect the new numbering.
**Author:** AI agent (with QA-sandbox evidence)
**Background / architectural investigation:** `requirements/AncillaryAssessment_AddSubService_TwoScenarios_UserStory.md`
**Evidence account:** `001UW00000ejn1SYAQ` (Complete Care At Lakeview Llc)
**Primary persona (all stories below):** **Ancillary Cred Specialist** — the credentialing operations role who runs the Ancillary Assessment OmniScript flow in PIE. Story-specific qualifiers (e.g., "Ancillary Cred Specialist serving on the HACAC committee") appear in story headers.

> **How to read this doc.**
>
> - **Business sign-off audience** — read the Story, Why it matters, Preconditions, and Acceptance Criteria. Stop at the Technical Implementation header.
> - **Developer audience** — same sections + the Technical Implementation block of each story + the consolidated Appendix at the bottom.
> - **QA audience** — the Acceptance Criteria are the test scripts. Each Pattern-A AC has a Given/When/Then you can execute step-by-step; each Pattern-B/C AC is a schema or permission spec you can validate via Setup.

### Story map at a glance

| Story | What it owns |
|---|---|
| **US-001** | Form-submission routing + record-creation contract end-to-end. The single source of truth for what records get created, reused, merged, or preserved across all five routing outcomes (NEW, REUSE same-PT PSV, NEW alongside same-PT past-PSV, NEW against same-PT approved AA, multi-PT reject). Owns the new *Preserve Re-Assessment Due Date* field + FLS, child-record dedupe, and Chatter templates per outcome. |
| **US-002** | The two submission rejections (data-refresh-only and multi-Provider-Type). |
| **US-003** | HACAC committee approval honours the *Preserve Re-Assessment Due Date* flag. |
| **US-004** | Field-level merge rule for sub-service updates on a same-Provider-Type Ancillary Assessment. |
| **US-005** | Data clean-up: dedupe existing duplicate same-Provider-Type AAs and backfill the preserve flag. |
| **US-006** | Field-level audit trail (native History + Change Log object) for every AA merge / HACAC / dedupe write. |

---

## 0. Glossary, schema confirmation & decision matrix

### Glossary

| Term | Meaning |
|---|---|
| **Provider Type** | The Provider-Type category a credentialing event belongs to. Examples: *Skilled Nursing*, *Home Health Agency-Adult/Pediatric*, *Hospice*, *Durable Medical Equipment*, *Hospital*. Stored on the Ancillary Assessment as the **RecordType** (e.g., `PRM_SkilledNursing`, `PRM_Hospice`), and equivalently as the value of the **Provider Type & Service** multi-select picklist (`PRM_ProviderTypeService__c`). Each picklist value maps 1:1 to a RecordType. |
| **Sub-service** | Additional details captured *within* a Provider Type (e.g., adding *Ventilator chronic care* details to an existing Skilled Nursing assessment). Sub-services are captured via the per-Provider-Type fields on the existing Ancillary Assessment, not by creating a second Ancillary Assessment for the same Provider Type. |
| **Submission's Provider Type** | The Provider Type implied by the picklist value(s) the Ancillary Cred Specialist selected on the Provider Form. If the picklist values span more than one Provider Type, this is a **multi-PT submission** (US-002 rejects). |
| **CM** | Case Manager — the in-flight credentialing application (`IndividualApplication`). Each Case Manager belongs to exactly one Provider Type, derived from the RecordType of its child Ancillary Assessment(s). |
| **AA** | Ancillary Assessment — one record per *Provider Type* per Account. Sub-services within a Provider Type live as field values on that single AA. |
| **In-flight CM** | A Case Manager currently being worked (status In Progress, any stage). |
| **PSV in-flight CM** | A Case Manager currently in the Primary Source Verification stage. |
| **Past-PSV in-flight CM** | A Case Manager past PSV but not yet closed (Committee Review, PDA Review/Update, or Network Mgmt QC). |
| **Approved CM** | A Case Manager whose HACAC decision was *Approve*. |
| **Form-submission date** | TODAY at the moment the Ancillary form is submitted. |
| **Same-PT match** | The Account has an in-flight Case Manager whose Provider Type equals the submission's Provider Type. |
| **Different-PT** | No in-flight Case Manager on the Account has a Provider Type matching the submission's. |

### Schema confirmation (verified 2026-06-02 against `force-app/main/default/objects/PRM_AncillaryAssessment__c/`)

- **`PRM_ProviderTypeService__c`** — restricted multi-select picklist with ~50 Provider-Type values. *No sub-service values exist in the picklist; each value is itself a distinct Provider Type.*
- **Ancillary Assessment RecordTypes** — 1:1 with the picklist values: `PRM_SkilledNursing`, `PRM_HomeHealthAgencyAdultPediatric`, `PRM_Hospice`, `PRM_DurableMedicalEquipment`, `PRM_Hospital`, `PRM_AmbulatorySurgeryCenter`, `PRM_CardiacMonitoring`, `PRM_ClinicalLaboratory`, `PRM_IDTF`, `PRM_LithotripsyCenter`, `PRM_OutpatientDiabeticEducation`, `PRM_OrthoticsProsthetics`, `PRM_MothersOption`, `PRM_HomePerinatal`, `PRM_PrivateDutyNursing`, `PRM_RenalDialysisCenter`, `PRM_SleepStudy`, `PRM_Ambulance`, `PRM_BirthCenter`, `PRM_General`.
- **Service → Provider Type mapping** is already encoded in `PRM_AncillaryProviderFormDataUpdates.getRecordIds()` (used today to set the AA's RecordType from the picklist value). The resolver reuses this mapping; no new metadata is required.

### Decision matrix (the canonical routing rules in business terms)

The routing decision is made **per submission's Provider Type**. A submission that selects services from more than one Provider Type is rejected before routing (US-002).

| State of the Account, evaluated for the submission's Provider Type | CM behaviour | AA behaviour | Reassessment-date behaviour |
|---|---|---|---|
| **No same-PT CM, no same-PT AA.** *(brand-new for this Provider Type — Account may still have unrelated in-flight CMs / approved AAs for other Provider Types; they are not touched.)* | Create a new Case Manager + Case (today's behaviour). | Insert one new Ancillary Assessment for this Provider Type. | n/a — date set at HACAC = decision date + 3 years. |
| **Same-PT PSV in-flight CM exists.** *(Scenario 1 — sub-service add to a fresh credentialing cycle)* | **Reuse the same Case Manager + Case.** | Reuse the existing same-PT Ancillary Assessment and apply the field-level merge rule (US-004) to capture the new sub-service details. No new AA is created (one AA per Provider Type rule). | No change to the existing date. HACAC handles per US-003. |
| **Same-PT past-PSV in-flight CM exists.** *(Scenario 2A — same PT, can't reuse because the prior CM is past PSV)* | **Create a new Case Manager + Case.** Do NOT disturb the in-flight Case Manager. | Reuse the existing same-PT Ancillary Assessment (link unchanged — stays with the prior CM); apply merge rule for the new sub-service details. | Mark the existing AA's *Preserve Re-Assessment Due Date* flag (per US-001 AC-1.8); HACAC enforces per US-003. |
| **No same-PT in-flight CM, but ≥1 same-PT approved AA.** *(Scenario 2B — re-credentialing cycle for an already-approved Provider Type)* | **Create a new Case Manager + Case.** | Reuse the existing same-PT approved Ancillary Assessment; apply merge rule for new sub-service details. *(If the form selects no sub-service changes, US-002 rejects.)* | Per AA, if its existing reassessment due date is more than 1 year out → mark *Preserve* flag = TRUE (HACAC will keep the existing date). Otherwise → *Preserve* flag = FALSE (HACAC overrides to decision date + 3 years). |
| **Multi-PT submission.** *(The form selects services from more than one Provider Type.)* | **Reject** before any record is touched. | n/a | n/a |

**Important corollary.** *Different Provider Type, in-flight or otherwise, never triggers reuse.* For example: if the Account has an in-flight PSV Case Manager for *Skilled Nursing* and the Ancillary Cred Specialist submits the form for *Home Health Agency*, the system creates a brand-new Home Health Case Manager *alongside* the in-flight Skilled Nursing one. The Skilled Nursing Case Manager is not touched and the Home Health submission is treated as a brand-new credentialing event for Home Health (first row of the matrix). The Account's *Credentialing In Progress* status is already set because of the Skilled Nursing CM and stays unchanged.

---

## US-001 — Form-submission routing & record-creation contract

**Persona:** Ancillary Cred Specialist
**Priority:** P0
**OmniScript:** PRM_AncillaryWelcomeScreen_English, PRM_AncillaryProviderForm_English
**Integration Procedures:** PRM_AncillaryFormRecordsCreationParent, PRM_AncillaryFormRecordsCreation
**Relevant Requirements:** TwoScenarios_UserStory §1 (Scenarios 1, 2A, 2B), §5.1, §5.3; *Provider-Type-matching clarification 2026-06-02*; *Story consolidation 2026-06-03*

### Story

**As an** Ancillary Cred Specialist submitting the Ancillary form for a vendor,
**I want** the system to silently route the submission and create or update the right records for the submission's Provider Type — whether that's a brand-new credentialing event, a sub-service add to a fresh in-flight PSV review, a parallel new Case Manager alongside a same-PT past-PSV review, or a fresh Case Manager against a previously-approved Ancillary Assessment,
**So that** I never have to think about routing, never end up with duplicate Ancillary Assessments for the same Provider Type, never disturb credentialing for other Provider Types on the same vendor, and never extend a provider's reassessment-due-date schedule when an add-sub-service submission shouldn't have.

**Why it matters:** Four problems coexist today and the records-creation Integration Procedure handles none of them.

- **Duplicate Ancillary Assessments for the same Provider Type.** Every submission unconditionally creates a new Case Manager + Case + Ancillary Assessment. The evidence account `001UW00000ejn1SYAQ` already has two Skilled Nursing Ancillary Assessments (`a1VVB000009BuwB2AS` and `a1VUW00000HHxMs2AL`) — one of them with a reassessment due date of 2027-07-08 — from two separate submissions.
- **Cross-Provider-Type contamination.** Reusing any in-flight CM on the Account regardless of Provider Type contaminates Committee Review and confuses notifications. The corrected rule (verified with the business 2026-06-02) is to match by Provider Type.
- **PSV review disruption when adding a sub-service after Committee Review opens.** Once a Case Manager moves past PSV, the credentialing committee timeline cannot be interrupted by writes from a new submission.
- **Silent reassessment-due-date extension at HACAC.** Today, every Approve unconditionally overwrites the reassessment due date with HACAC-decision-date + 3 years. For providers whose existing date is already more than a year out, this silently extends their credentialing window and disrupts notifications.

### Preconditions

- The Account has been resolved by the form's type-ahead Account lookup (existing vendor or brand-new vendor).
- The submission selects exactly one Provider Type (multi-PT submissions are blocked by US-002 before this story runs).
- The submission carries at least one new or changed sub-service detail when the Provider Type is already credentialed (otherwise US-002 rejects).

### Acceptance criteria

#### Routing decision

**AC-1.1 — Routing happens silently at submit time**

**Given** an Ancillary Cred Specialist submits the Ancillary form for a vendor,
**When** they click Submit on the Provider Form,
**Then** the system silently determines, based on the submission's Provider Type, exactly one routing outcome,
**And** no record is created or modified until that routing decision is made,
**And** the Ancillary Cred Specialist is never asked a routing question on screen.

---

**AC-1.2 — Routing decision is per-Provider-Type and produces exactly one of five outcomes**

**Given** the system is evaluating a single-Provider-Type submission for the Account,
**When** it inspects the Account's Case Managers and Ancillary Assessments **for the submission's Provider Type**,
**Then** the routing decision is exactly one of the following, and the system performs the listed record actions atomically inside the submit transaction:

| Outcome (`contextType`) | Trigger | What gets created / updated / preserved |
|---|---|---|
| **`NEW`** — brand-new for this Provider Type | No same-PT CM and no same-PT AA exists on the Account *(unrelated different-PT CMs/AAs may exist; they are not touched)* | Create a new Case Manager. Create a new PSV Case linked to it. Insert one new Ancillary Assessment with the form's Provider Type and sub-service field values. |
| **`REUSE_IN_FLIGHT_PSV_SAME_PT`** — Scenario 1 reuse | A same-PT in-flight CM exists and is still in PSV | **No** new Case Manager. **No** new Case. **No** new Ancillary Assessment. The existing same-PT AA is updated in place via the merge rule (US-004). Child records (Addresses, Identifiers, Business Licenses) are reused or appended per AC-1.4. |
| **`NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV`** — Scenario 2A | A same-PT in-flight CM exists but is past PSV (Committee Review / PDA / Network Mgmt QC) | Create a new Case Manager and new PSV Case alongside the prior CM. The existing same-PT AA is updated in place via the merge rule (US-004), and its Case Manager link **stays with the prior past-PSV CM** (it is NOT re-pointed to the new CM). The prior CM is left completely untouched. |
| **`NEW_CM_AGAINST_APPROVED_AAS_SAME_PT`** — Scenario 2B | No same-PT in-flight CM exists, but ≥1 same-PT approved (or HC3-migrated) AA exists | Create a new Case Manager and new PSV Case. The existing same-PT approved AA is updated in place via the merge rule (US-004), and its Case Manager link is unchanged (stays with the prior approved CM, or stays null for HC3-migrated AAs). The *Preserve Re-Assessment Due Date* flag on the existing AA is evaluated per AC-1.8. |
| **`REJECT_MULTI_PT`** — multi-PT submission | The form's picklist values span more than one Provider Type | Reject the submission; no record is created or modified. Implemented by US-002. |

**And** in every outcome above, no other-Provider-Type Ancillary Assessment on the Account is touched — no field changed, no merge applied, no preserve flag set, no reassessment due date moved.
**And** *different Provider Types never trigger reuse*: if the only in-flight CM on the Account is for a different Provider Type, the submission falls into the **`NEW`** outcome above.

---

**AC-1.3 — Safety net when the Account already has duplicate same-PT in-flight Case Managers**

**Given** an Account currently has more than one in-flight Case Manager *for the submission's Provider Type* still in PSV (a data-quality artefact from the existing bug; e.g., the live evidence on `001UW00000ejn1SYAQ` has two Skilled Nursing AAs and one in-flight Skilled Nursing CM plus one orphan Skilled Nursing AA),
**When** the Ancillary Cred Specialist submits another same-PT Ancillary form,
**Then** the system reuses the **earliest-created** in-flight PSV Case Manager for that Provider Type,
**And** an internal warning is logged for Ops to investigate the duplicate Case Managers,
**And** the Ancillary Cred Specialist's submission still completes successfully.

---

#### Record handling details

**AC-1.4 — Reuse outcome: child records are added only for the delta, not duplicated**

**Given** the routing outcome is `REUSE_IN_FLIGHT_PSV_SAME_PT` and the in-flight Case Manager already has Addresses, Identifiers, Business Licenses, Adverse Action Log entries, and a Provider Form PDF on its Case from the original submission,
**When** the additional form is submitted with overlapping data,
**Then** the system behaves as follows for each child record type:

- **Addresses** — Reuse any existing address that matches on Address Line 1, City, State, and ZIP; do not insert a duplicate row.
- **Identifiers (NPI, Tax ID)** — Reuse any existing identifier on this Account that matches on identifier value; do not insert a duplicate row.
- **Business Licenses** — Reuse any existing business license on this Account that matches on License Number and State; do not insert a duplicate row.
- **Adverse Action Log** — Always append a new log entry (this is an event log; chronology must be preserved).
- **Provider Form PDF** — Always create a new PDF and attach it to the existing Case (every submission produces an audit-ready PDF).

---

**AC-1.5 — Existing reassessment due date is never modified at submit time**

**Given** an existing same-PT Ancillary Assessment has a reassessment due date set,
**When** any add-sub-service submission completes (any of the four non-reject outcomes in AC-1.2),
**Then** the AA's reassessment due date is unchanged after the submission,
**And** the only way the reassessment due date can change is via the committee decision flow (US-003).

---

**AC-1.6 — Account's *Credentialing In Progress* status invariants**

**Given** the routing outcome is `REUSE_IN_FLIGHT_PSV_SAME_PT`, `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV`, or `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT`,
**When** the submission completes,
**Then** the Account's credentialing status remains *Credentialing In Progress*.

**Given** the routing outcome is `NEW` and the Account is currently not in *Credentialing In Progress*,
**When** the submission completes,
**Then** the Account transitions to *Credentialing In Progress* exactly as today's brand-new-vendor flow does.

---

#### Preserve Re-Assessment Due Date — rule, field, FLS

**AC-1.7 — Preserve Re-Assessment Due Date — rule (per AA, per outcome)**

**Given** the system has determined a routing outcome,
**When** the submit transaction runs,
**Then** the *Preserve Re-Assessment Due Date* flag on the existing same-PT AA is set as follows:

| Outcome | Existing same-PT AA's reassessment due date | Preserve flag |
|---|---|---|
| `REUSE_IN_FLIGHT_PSV_SAME_PT` | any | unchanged (no need to preserve; HACAC will set the date when this CM eventually approves) |
| `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` | > TODAY() + 365 days | **TRUE** |
| `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` | ≤ TODAY() + 365 days, or null | **FALSE** |
| `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` | > TODAY() + 365 days | **TRUE** |
| `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` | ≤ TODAY() + 365 days, or null | **FALSE** (HACAC will set the date for the first time via +3 yrs at approval) |
| `NEW` | n/a (no existing same-PT AA) | n/a |

**And** the flag is consumed at HACAC approval per US-003.

---

**AC-1.8 — Create the Preserve Re-Assessment Due Date field on Ancillary Assessment**

- **API Name:** `PRM_PreserveReassessmentDueDate__c`
- **Object:** `PRM_AncillaryAssessment__c` (Ancillary Assessment)
- **Type:** Checkbox (Boolean)
- **Label:** Preserve Re-Assessment Due Date
- **Default:** False
- **Help text:** "When checked, HACAC will keep the current Re-Assessment Due Date instead of updating it to HACAC decision date + 3 years."
- **Description:** "Set automatically at form submission when an existing Re-Assessment Due Date is more than 365 days in the future. HACAC reads this flag at approval to decide whether to preserve the existing date or override to HACAC decision date + 3 years."
- **Track History:** True
- **Required:** False

---

**AC-1.9 — Field Access & Permission Sets for Preserve Re-Assessment Due Date**

- **System Administrator:**
  - Object level: Read, Create, Edit, Delete, View All Records, Modify All Records
  - Field level: Read, Edit
- **PRM_DataModifyAll:**
  - Object level: Read, Create, Edit, View All Records
  - Field level: Read, Edit
- **PRM_AncillaryCredSpecialist, PRM_Credentialing, PRM_BusinessAdmin:**
  - Object level: Read
  - Field level: Read (no Edit) — Ancillary Cred Specialists do not need to manually toggle the flag; the system manages it.
- All other permission sets / profiles: No access to the new field.

---

#### Chatter audit per outcome

**AC-1.10 — Chatter audit on the active Case Manager per outcome**

**Given** the submit transaction completes successfully,
**When** the system writes its audit Chatter,
**Then** exactly one Chatter post is added per submission, on the active Case Manager for the submitted Provider Type, using the template that matches the routing outcome:

| Outcome | Chatter post lands on | Template |
|---|---|---|
| `NEW` | The newly-created Case Manager | *"Created via Ancillary Provider Form on {{TODAY}} for {{Provider Type}} by {{User Name}}."* If the Account has any unrelated different-PT in-flight CMs, append: *" Note: Other in-flight Case Managers on this Account for unrelated Provider Types: {{otherCmList}}."* |
| `REUSE_IN_FLIGHT_PSV_SAME_PT` | The reused (existing) same-PT in-flight PSV CM | *"Additional Ancillary form submitted on {{TODAY}} by {{User Name}} for {{Provider Type}}. Sub-service fields updated: {{ChangedFieldLabels}}."* |
| `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` | The newly-created same-PT CM | *"Created via add-sub-service workflow on {{TODAY}} for {{Provider Type}}. Prior {{Provider Type}} Case Manager still active: {{priorCM.Name}} at stage {{priorCM.Stage}}. Sub-service fields updated on existing Ancillary Assessment: {{ChangedFieldLabels}}."* |
| `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` | The newly-created same-PT CM | *"Created via add-sub-service workflow on {{TODAY}} for {{Provider Type}}. Linked to previously-approved Ancillary Assessment: {{existingAA.Name}} (Reassessment due date preserved: {{preserveFlag}} → {{existingDate}}). Sub-service fields updated: {{ChangedFieldLabels}}."* |

**And** the post is not written if any step of the submission failed.
**And** in the `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` and `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` outcomes, no Chatter post is added to the prior / existing Case Manager's feed (the new CM's feed is the only audit surface for this submission).

---

#### Non-functional

**AC-1.11 — Routing has no measurable performance impact**

**Given** an Ancillary Cred Specialist submits the form,
**When** the routing logic runs,
**Then** the system reads the Account's Case Manager and Ancillary Assessment landscape in at most two SOQL queries (no fan-out per Provider Type),
**And** the overall submit-to-confirmation time is no slower than today's brand-new submission.

---

**AC-1.12 — Submission UX is unchanged for the Ancillary Cred Specialist**

**Given** any non-reject routing decision has been made,
**When** the Ancillary Cred Specialist completes the Submit step,
**Then** no additional screen, banner, modal, or "Are you sure?" pop-up appears,
**And** the form transitions to the next step exactly as it does today,
**And** the only visible difference (when reuse happens) is the Chatter post that lands per AC-1.10.

### Live-data regression suite (on `001UW00000ejn1SYAQ`)

| Test | Scenario | Today's state on the Account | Submission | Expected outcome |
|---|---|---|---|---|
| **L1 — Reuse same-PT PSV CM** | `REUSE_IN_FLIGHT_PSV_SAME_PT` | Skilled Nursing AA `a1VVB000009BuwB2AS` linked to in-flight PSV CM `IA-0000152008`; orphan Skilled Nursing AA `a1VUW00000HHxMs2AL` with reassessment date 2027-07-08 | Submit form for *Skilled Nursing* with at least one new sub-service field value (e.g., toggle *Ventilator Chronic Care* TRUE) | No new CM, no new Case, no new AA. Existing AA `a1VVB000009BuwB2AS` shows merged sub-service value(s). Chatter post on `IA-0000152008` per AC-1.10 template 2. Orphan AA `a1VUW00000HHxMs2AL` untouched (date still 2027-07-08). |
| **L2 — Different-PT brand new** | `NEW` | Same as L1 | Submit form for *Hospice* (a Provider Type not currently on the Account) | New Hospice CM + Case + AA created. Skilled Nursing AAs and CM untouched. Chatter post on the new Hospice CM per AC-1.10 template 1, mentioning the unrelated in-flight Skilled Nursing CM. |
| **L3 — Multi-PT reject** | `REJECT_MULTI_PT` | Same as L1 | Submit form selecting both *Skilled Nursing* and *Home Health Agency-Adult/Pediatric* on the same submission | Submission blocked. No records touched. US-002's multi-PT validation message rendered on the form. |
| **L4 — Same-PT past-PSV new (hypothetical)** | `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` | *Hypothetically* CM `IA-0000152008` has advanced to Committee Review | Submit form for *Skilled Nursing* with new sub-service field value | A new Skilled Nursing CM + Case created alongside `IA-0000152008`. AA `a1VVB000009BuwB2AS` updated in place; its CM link stays with `IA-0000152008` (not re-pointed). Preserve flag set per AC-1.7 (TRUE if existing reassessment date > TODAY()+365). |
| **L5 — Same-PT approved-only new (hypothetical)** | `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` | *Hypothetically* CM `IA-0000152008` has been moved out of in-flight status; orphan AA `a1VUW00000HHxMs2AL` (date 2027-07-08) is the only Skilled Nursing AA on the Account | Submit form for *Skilled Nursing* with new sub-service field value | A new Skilled Nursing CM + Case created. AA `a1VUW00000HHxMs2AL` updated in place with the new sub-service value and Preserve flag = TRUE (date > TODAY()+365). After HACAC approval per US-003, the AA's reassessment date is still 2027-07-08. |
| **L5b — Live-data counter-example** | Same outcome as L5 | Hypothetical existing reassessment date of 2027-05-01 instead (within TODAY()+365) | Same submission as L5 | Same record creation, but Preserve flag = FALSE. HACAC will later override the date to decision date + 3 years per US-003. |

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AncillaryFormContextResolver.cls` | New Apex Callable | Returns the routing decision (`contextType` ∈ `NEW` / `REUSE_IN_FLIGHT_PSV_SAME_PT` / `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` / `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` / `REJECT_MULTI_PT`) + the resolved `submissionProviderType` + existing same-PT CM/Case Ids + same-PT AA references + preserve-flag candidate + a `List<FieldChange>` reflecting what the merge would write | AC-1.1, 1.2, 1.3, 1.7, 1.10, 1.11 |
| Service → Provider Type mapping | Existing helper, reused | `PRM_AncillaryProviderFormDataUpdates.getRecordIds()` already maps each picklist value to its AA RecordType DeveloperName; the resolver consumes this mapping to derive `submissionProviderType` and to filter the in-flight CM / AA lookups | AC-1.2; no new metadata required |
| Resolver SOQL | Two queries total | One on `IndividualApplication` with `PRM_AncillaryAssessments__r` subquery filtered by `AccountId`; one orphan query on `PRM_AncillaryAssessment__c` for HC3-migrated rows. Provider-Type filtering happens in Apex on the returned rows so we can still detect duplicate-PT bugs. | AC-1.11 |
| `PRM_AncillaryFormRecordsCreation_Procedure_19` | New active IP version | Step 1 invokes the resolver. The CM/Case/AA creation steps (today's IP_18 steps 2, 11, 13, 17, 26, 28, 29, 35) become conditional on `contextType`. The same-PT AA update step routes through `mergeAaFields` (US-004) for all three reuse-of-AA outcomes. The `REJECT_MULTI_PT` and `REJECT_NO_CHANGE` outcomes short-circuit before any DML. The existing same-PT AA's `PRM_CaseManager__c` field is excluded from the merge in Scenarios 2A/2B so the link is unchanged. | AC-1.2, 1.4, 1.12 |
| `PRM_AncillaryFormRecordsCreationParent_Procedure_3` | New active IP version | Wires to the new child IP_19 | AC-1.1 |
| Child-record dedupe helpers (Address, Identifier, BusinessLicense) | New Apex helpers in `PRM_AncillaryProviderFormDataUpdates` | Match on natural keys and reuse existing rows; AdverseActionLog and Provider-Form-PDF helpers remain append-only | AC-1.4 |
| Preserve-flag writer | New Apex helper inside `PRM_AncillaryFormContextResolver` | Evaluates `preserve = (existingDate > TODAY() + 365)` on the existing same-PT AA for Scenarios 2A and 2B; writes the boolean at submit time | AC-1.7 |
| `PRM_AncillaryAssessment__c.PRM_PreserveReassessmentDueDate__c` | New custom field | Checkbox, default false, tracked history, help/description per AC-1.8 | AC-1.8 |
| Permission set updates | Modified `PRM_AncillaryCredSpecialist`, `PRM_Credentialing`, `PRM_BusinessAdmin`, `PRM_DataModifyAll` | Read access on the new field (Edit only for DataModifyAll + SysAdmin) per AC-1.9 | AC-1.9 |
| Chatter post writer | New Apex helper | Renders the right template per `contextType` and posts it on the right Case Manager per AC-1.10 | AC-1.10 |
| FOR UPDATE lock on the same-PT in-flight CM query inside the resolver | Concurrency guard | Serialises simultaneous submissions on the same (Account, Provider Type) so two clicks within seconds cannot both create a CM | AC-1.3 + Cross-cutting NFRs |
| `PRM_ExceptionLogger.logException('PRM_AncillaryFormContextResolver','MULTIPLE_INFLIGHT_SAME_PT_CMS',…)` | Log emitter | Info-severity log row for the duplicate-same-PT-CM warning | AC-1.3 |
| `PRM_AncillaryFormContextResolverTest.cls` | New Apex test | ≥ 90 % coverage; at least one method per `contextType` value + multi-in-flight warning path + multi-PT rejection path + different-PT-in-flight isolation path + preserve-flag rule paths (TRUE / FALSE / null) | Quality gate |
| `PRM_AncillaryProviderFormDataUpdatesTest.cls` | New methods | One method per `contextType` non-reject outcome covering record creation, child-record dedupe, Chatter post, and other-PT isolation against `001UW00000ejn1SYAQ` | Quality gate; covers all 5 live-data regression tests |

### Definition of done

- [ ] New field `PRM_PreserveReassessmentDueDate__c` + history-tracking + perm-set FLS deployed.
- [ ] New Apex resolver + Chatter post writer + preserve-flag writer + child-record dedupe helpers deployed.
- [ ] IP_19 created and active; IP_18 retired; parent IP_3 wired to IP_19.
- [ ] `insertAARecords` refactored so it always merges into the existing same-PT AA for the three reuse-of-AA outcomes; never inserts a duplicate same-PT AA.
- [ ] Test classes ≥ 90 % coverage with all 5 live-data regression tests (L1–L5 + L5b) passing on `001UW00000ejn1SYAQ`.

---

## US-002 — Reject submissions that add nothing new or that span multiple Provider Types

**Persona:** Ancillary Cred Specialist
**Priority:** P1
**OmniScript:** PRM_AncillaryProviderForm_English
**Integration Procedures:** PRM_AncillaryFormRecordsCreation
**Relevant Requirements:** TwoScenarios_UserStory §7 Q1; *Multi-PT clarification 2026-06-02*; US-001 AC-1.2 (`REJECT_MULTI_PT`)

### Story

**As an** Ancillary Cred Specialist,
**I want** the system to block my submission when I have selected only already-credentialed Provider Types with no new sub-service detail, or when I have accidentally selected services from more than one Provider Type in one submission,
**So that** I don't create duplicate Ancillary Assessments by re-submitting unchanged data, and so that one submission never tries to credential two Provider Types at once (which would route to two different Case Managers and confuse downstream workflows).

**Why it matters:** Re-submitting an already-credentialed Provider Type with no new sub-service detail creates a duplicate Ancillary Assessment and a duplicate Case Manager today. A multi-Provider-Type submission today is silently treated as one credentialing event but in reality needs to fork into two Case Managers (one per Provider Type), which the current orchestration cannot do safely. Both situations need to be rejected with a clear message until the form UI enforces the constraint up front.

### Current state (verified 2026-06-03)

This rejection logic is **not** implemented today. Layer-by-layer trace:

| Layer | What it does today | Blocks per US-002? |
|---|---|---|
| Welcome screen `PRM_AncillaryWelcomeScreen_English_3` | Static regulatory text + Agree → navigate to provider form. No data load, no IP call. | No |
| Provider form `PRM_AncillaryProviderForm_English_38` | Type-ahead Account lookup + minimal pre-population via `isExistingAccount`. The only duplicate guards are `PrimaryFacilityDuplicateLicense` / `AdditionalFacilityDuplicateLicense` for business-license rows. | No |
| Embedded picker `PRM_AncillaryTypesAndServices_English_23` | Multi-select sourced directly from `PRM_AncillaryAssessment__c.PRM_ServicesType__c` picklist metadata. Every value is always selectable; no Account-scoped filtering. | No |
| Parent IP `PRM_AncillaryFormRecordsCreationParent_Procedure_2` | 3 steps: SetValues → TryCatch (calls IP_18) → ResponseAction. No validation step, no `executionConditionalFormula` short-circuit. | No |
| Records-creation IP `PRM_AncillaryFormRecordsCreation_Procedure_18` | ~32 pure record-creation steps. No precondition check, no rejection branch. | No |
| Dispatcher `PRM_AncillaryProviderFormUtils.cls` | 11 callable methods. Only duplicate-check is `checkDuplicateLicense` for business licenses on a single AA — not for Provider Type & Service across the Account. | No (license dedupe only) |
| `PRM_AncillaryProviderFormDataUpdates.insertAARecords` | Inserts new AAs straight from form context using `getRecordIds()` Service→RecordType mapping. No pre-insert "does this PT&S already exist for this Account?" SOQL. | No |

**Live-data proof.** Account `001UW00000ejn1SYAQ` has two Skilled Nursing Ancillary Assessments (`a1VVB000009BuwB2AS` and `a1VUW00000HHxMs2AL`) created via separate form submissions. If today's flow blocked re-submission of an already-credentialed Provider Type, those duplicates could not exist.

**No reusable pattern elsewhere.** Searches for `alreadyCredentialed | preventSubmission | blockSubmission | cannotSubmit | duplicateAncillary | duplicateAssessment | existingProviderType | alreadyHasProviderType | RestrictedSubmission` across the entire `force-app/main/default/` tree return zero matches in the Ancillary domain. The Practitioner form's `IsCredentialedPNCDelegated` flag *modifies* pre-population behaviour but does not *block* submission — so it is not directly reusable. US-002 needs to be built from scratch.

### Acceptance criteria

**AC-2.1 — Submission is blocked when no Provider Type is new AND no sub-service detail is new**

**Given** every Provider Type the Ancillary Cred Specialist selected on the form already has an Ancillary Assessment on this Account,
**And** the merge of the submission's fields against the existing Ancillary Assessment(s) would result in zero field changes,
**When** they click Submit on the Provider Form,
**Then** the submission is blocked and no records are created or modified.

---

**AC-2.2 — Submission is blocked when the form selects services from more than one Provider Type**

**Given** the Ancillary Cred Specialist has selected services from more than one Provider Type on the form (for example, *Skilled Nursing* and *Home Health Agency-Adult/Pediatric* both ticked),
**When** they click Submit on the Provider Form,
**Then** the submission is blocked and no records are created or modified,
**And** the routing logic does not attempt to split the submission into multiple Case Managers (out of scope for this story — see Open Clarification Questions Q-R2).

---

**AC-2.3 — A clear validation message is shown for each rejection reason**

**Given** the submission has been blocked per AC-2.1 (data-refresh-only),
**When** the OmniScript receives the rejection,
**Then** the screen shows the message exactly: *"This account is already credentialed for the Provider Type(s) you selected and your form does not include any new sub-service details. Please either update at least one sub-service detail, add a different Provider Type, or contact the credentialing team."*

**Given** the submission has been blocked per AC-2.2 (multi-PT),
**When** the OmniScript receives the rejection,
**Then** the screen shows the message exactly: *"You have selected services from more than one Provider Type ({{ProviderTypeListed}}). Please submit one Provider Type at a time. Each Provider Type needs its own credentialing review."*

**And** the Ancillary Cred Specialist is held on the same form step in both cases.

---

**AC-2.4 — Zero side-effects on rejection**

**Given** the submission has been rejected for either reason,
**When** the rejection message is rendered,
**Then** no Case Manager, Case, Ancillary Assessment, Address, Identifier, Business License, Adverse Action Log, or PDF has been created,
**And** no Chatter post has been written,
**And** no existing record has been updated.

---

**AC-2.5 — Rejection is logged as an Info event, not an Error**

**Given** the rejection has fired,
**When** the system logs the event,
**Then** the log row is recorded at *Info* severity (not Error or Warning),
**And** the log row identifies the Account, the selected Provider Type(s), the rejection reason (data-refresh-only vs multi-PT), and the merge-diff size (zero) for AC-2.1.

---

**AC-2.6 — User input is preserved after rejection**

**Given** the Ancillary Cred Specialist had selected one or more Provider Type checkboxes,
**When** the rejection message is shown,
**Then** every checkbox retains the checked/unchecked state they submitted with,
**And** they can press Back, amend the selection, and re-submit without losing context.

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AncillaryFormContextResolver.cls` (US-001) | Modified resolver | Detects multi-PT submissions before any routing logic; detects zero-diff submissions after running `mergeAaFields` (US-004) in dry-run mode; sets `contextType` to `REJECT_MULTI_PT` or `REJECT_NO_CHANGE` accordingly | AC-2.1, 2.2 |
| `PRM_AncillaryFormRecordsCreation_Procedure_19` (US-001) | Modified IP version | Short-circuits after the resolver when `contextType` ∈ { `REJECT_MULTI_PT`, `REJECT_NO_CHANGE` }; returns an error response with the matching `errorCode` | AC-2.1, 2.2, 2.4 |
| OmniScript response template | Modified `PRM_AncillaryProviderForm_English_39` | Renders the two validation messages from AC-2.3 keyed on `errorCode`; preserves checkbox state for AC-2.6 | AC-2.3, 2.6 |
| `PRM_ExceptionLogger.logException('PRM_AncillaryFormContextResolver','REJECT_NO_CHANGE' / 'REJECT_MULTI_PT', …)` | Log emitter | Info-level log with Account Id, selected Provider Types, and rejection reason | AC-2.5 |
| `PRM_AncillaryProviderFormDataUpdatesTest` additions | Apex test | One test per rejection reason; asserts zero DML on rejection | Quality gate |

### Definition of done

- [ ] Both rejection paths wired in the resolver + IP.
- [ ] Both validation messages wired in the OmniScript response template.
- [ ] Info-level log rows written on each rejection.
- [ ] Apex tests assert no DML on rejection for both reasons.

---

## US-003 — HACAC committee approval enforces the preserve flag

**Persona:** Ancillary Cred Specialist (serving on the HACAC committee)
**Priority:** P0
**OmniScript:** PRM_ReviewHACAC_English
**Integration Procedures:** PRM_DataUpdationforHAPACCommitteeReviewParent, PRM_DataUpdationforHAPACCommitteeReview
**Relevant Requirements:** TwoScenarios_UserStory §3.3 / §5.3; US-001 AC-1.7 (preserve flag write at submit) and AC-1.8 (field definition)

### Story

**As an** Ancillary Cred Specialist serving on the HACAC committee and reviewing a Case Manager,
**I want** the Re-Assessment Due Date to be set, refreshed, or preserved per the new conditional rule,
**So that** providers with a future reassessment date already in flight are not unnecessarily extended to +3 years from today's HACAC decision.

**Why it matters:** Today, every Approve decision unconditionally overwrites the reassessment due date with decision-date + 3 years. For providers whose existing date is already more than 1 year out, this silently extends their credentialing window and disrupts the reassessment notification schedule.

### Acceptance criteria

**AC-3.1 — Approve + preserve = TRUE keeps the existing date**

**Given** an Ancillary Assessment has the *Preserve Re-Assessment Due Date* flag set to TRUE and a non-null existing reassessment due date,
**When** the HACAC committee submits an *Approve* decision against the Case Manager that owns this Ancillary Assessment,
**Then** the Ancillary Assessment's reassessment due date is unchanged after the approval transaction completes,
**And** the date the Ancillary Cred Specialist sees on the AA equals the original existing date.

---

**AC-3.2 — Preserve flag clears itself after one use**

**Given** the calculator has just applied the preserve-or-override decision for an Ancillary Assessment,
**When** the approval transaction completes,
**Then** the *Preserve Re-Assessment Due Date* flag on that AA is reset to FALSE,
**And** any subsequent committee decision on the same AA starts from the default *not-preserved* state.

---

**AC-3.3 — Non-Approve decisions are unchanged**

**Given** the HACAC committee submits a *Pend*, *Terminate*, or *Deny* decision,
**When** the decision is recorded,
**Then** the Ancillary Assessment's reassessment due date is set per today's existing terminate/pend logic (no change in behaviour from before this story),
**And** the preserve flag plays no part in the calculation.

---

**AC-3.4 — Approve + preserve = FALSE refreshes to decision date + 3 years**

**Given** an Ancillary Assessment has the *Preserve Re-Assessment Due Date* flag set to FALSE (or null, for legacy AAs untouched by the new resolver) and the committee approves the Case Manager,
**When** the Approve decision is recorded,
**Then** the Ancillary Assessment's reassessment due date equals the HACAC decision date + 3 years.

---

**AC-3.5 — Backward compatibility for legacy AAs**

**Given** a legacy Ancillary Assessment whose preserve flag has never been set (null) — for example HC3-migrated rows that never went through the new resolver,
**When** the HACAC committee approves the Case Manager,
**Then** the legacy AA is treated as preserve = FALSE,
**And** the date is set to decision date + 3 years (today's behaviour),
**And** approximately 99 % of cases that never go through the new resolver continue to behave exactly as they do today.

---

**AC-3.6 — Reassessment OmniScript flow is unchanged**

**Given** an Ancillary Cred Specialist is running the Re-Assessment OmniScript flow (not the add-sub-service flow),
**When** the HACAC committee approves the Re-Assessment Case Manager,
**Then** the Ancillary Assessment's reassessment due date is set to decision date + 3 years exactly as today,
**And** the preserve-flag logic is not applied (out of scope for this story).

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AncillaryHACACReassessmentDateCalculator.cls` | New Apex Callable | Returns the final reassessment date per AA: if `PRM_PreserveReassessmentDueDate__c = TRUE` and existing date is non-null → existing date; else → HACAC decision date + 3 years. After computing, clears the flag back to FALSE. | AC-3.1, 3.2, 3.4, 3.5 |
| `PRMDRHACACUpdateAncillaryAssessmentRecords_2` | New active DataRaptor version | Removes today's hard-coded `IF(SelectedDecision=="Approve", ADDYEAR(HACACDecisionDate, 3), NULL)` formula on `PRM_ReAssessmentDueDate__c`; reads the date from the IP context (populated by the new calculator step) instead | AC-3.1, 3.4 |
| `PRM_DataUpdationforHAPACCommitteeReview_Procedure_9` | New active IP version | Inserts the calculator step *before* the load DR v2; everything else carries forward from today's IP_8 | AC-3.1, 3.2 |
| Reassessment OmniScript flow (`PRM_AncillaryReassessmentPSVFormCreationParent_Procedure_1`) | No change | Continues to use the +3yrs behaviour | AC-3.6 (regression guard) |
| `PRM_AncillaryHACACReassessmentDateCalculatorTest.cls` | New Apex test | Cover preserve = TRUE / FALSE / null × decision = Approve / Pend / Terminate / Deny | Quality gate |

### Definition of done

- [ ] New calculator Apex class + test deployed.
- [ ] DR v2 deployed and active; v1 retired.
- [ ] IP v9 active; v8 retired.
- [ ] End-to-end test on `001UW00000ejn1SYAQ`: submit a same-PT add-sub-service per US-001 live test L4 or L5, approve via HACAC, assert preserve behaviour matches AC-3.1.

---

## US-004 — Merge rule for sub-service updates on an existing same-Provider-Type Ancillary Assessment (field-level overwrite contract)

**Persona:** Ancillary Cred Specialist
**Priority:** P0
**OmniScript:** PRM_AncillaryProviderForm_English
**Integration Procedures:** PRM_AncillaryFormRecordsCreation
**Relevant Requirements:** US-001 AC-1.2 (all three reuse-of-AA outcomes), US-001 AC-1.4 (child-record dedupe); US-006

> **Routing-rule impact assessment (2026-06-02):** US-004 operates **per Ancillary Assessment** for the submitted Provider Type. It is invoked only after the resolver has determined that the submission belongs to the same Provider Type as an existing Ancillary Assessment (the only path that needs merging). Other-Provider-Type AAs are never seen by `mergeAaFields`.

### Story

**As an** Ancillary Cred Specialist,
**I want** a precise, field-level rule that decides which Ancillary Assessment fields are overwritten and which are preserved when I update the sub-service details on an existing Ancillary Assessment for the same Provider Type,
**So that** my second submission cannot silently destroy data captured in the first submission — and so that the audit trail proves exactly what changed and why.

**Why it matters:** The Ancillary Assessment object has ~216 fields. The behaviour we want differs by field type (attestation/warranty fields always overwrite; per-type credentialing fields always overwrite; cross-type common fields behave differently inside a fresh PSV than long after committee approval; addresses preserve to avoid silent inconsistency with the canonical Address object). Without an explicit, business-confirmed merge rule, every developer guess introduces a data-quality bug.

### Field groupings (business-confirmed)

| Group | What it covers (in business terms) | Field count | Rule |
|---|---|---|---|
| **A — System-managed** | Name, RecordType, Account link, Provider Type & Service (the merge key), Case Manager link, Reassessment Due Date, Preserve flag, Auto-name, Operating Hours | 9 | **NEVER OVERWRITE** from form. |
| **B — Attestation / Warranty** | Authorized Signature, Print Name, Title, Signature Date | 4 | **ALWAYS OVERWRITE** on every submission + Chatter audit. |
| **C — Cross-type common** | Medicare participation block, Ownership block, Licensure block, Insurance block, Quality / Subcontractor block | ~20 | **Hybrid:** OVERWRITE if non-blank in Scenario 1 (fresh PSV reuse); BLANK-FILL ONLY in Scenarios 2A/2B (post-HACAC). |
| **D — Per-Provider-Type specific** | The body of the form for each Provider Type (e.g., Licensed Beds, Operating Rooms, Lab Director Name, Ventilator Chronic Care toggle on Skilled Nursing) | ~185 | **ALWAYS OVERWRITE** on every submission + audit (top-20 native History + change log object per US-006). |
| **E — Denormalised address/contact** | The address fields stored on the AA itself (the canonical source is the Address + HealthcareFacility records) | ~30 | **PRESERVE** existing AA address fields. New addresses route through the existing additional-address pipeline. |

### Acceptance criteria

**AC-4.1 — Group A fields are never overwritten by form merge**

**Given** an existing Ancillary Assessment whose Group-A fields (Name, RecordType, Account link, Provider Type & Service, Case Manager link, Reassessment Due Date, Preserve flag, Auto-name, Operating Hours) currently have values,
**When** the Ancillary Cred Specialist re-submits the form for the same Provider Type,
**Then** none of the Group-A fields are changed by the merge,
**And** any change to those fields can only happen via the resolver (Case Manager link, Preserve flag) or via HACAC (Reassessment Due Date).

---

**AC-4.2 — Group B fields are always overwritten with a Chatter audit**

**Given** an existing Ancillary Assessment has values in the Attestation/Warranty block (Authorized Signature, Print Name, Title, Signature Date),
**When** the Ancillary Cred Specialist re-submits the form for the same Provider Type with new values in any of those fields,
**Then** each Group-B field is overwritten with the new value,
**And** a Chatter post is added to the Ancillary Assessment's feed listing the field name, the old value, the new value, the user, and the submission timestamp.

---

**AC-4.3 — Group C fields behave differently inside PSV vs after HACAC**

**Given** a re-submission for the same Provider Type touches Group-C fields (Medicare, Ownership, Licensure, Insurance, Quality/Subcontractor),
**When** the system applies the merge,
**Then** in **Scenario 1 (`REUSE_IN_FLIGHT_PSV_SAME_PT`)**, every Group-C field with a non-blank new value overwrites the existing value (latest answer wins, because the original answers were just typed),
**And** in **Scenarios 2A or 2B (post-PSV or post-HACAC)**, only Group-C fields that are currently blank get filled in (never silently overwrite values vetted by HACAC),
**And** every Group-C write triggers a Chatter post on the Ancillary Assessment listing field name, old value, new value, scenario, user, and timestamp.

---

**AC-4.4 — Group D fields are always overwritten with a full audit trail**

**Given** an existing Ancillary Assessment has values in the per-Provider-Type body (~185 fields),
**When** the Ancillary Cred Specialist re-submits the form for that Provider Type,
**Then** every Group-D field is overwritten with the form's value (latest submission is source of truth),
**And** the change is captured in the audit trail per US-006 (top-20 native History + change log row for every changed field).

---

**AC-4.5 — Group E address fields are preserved; new addresses route through the existing pipeline**

**Given** the Ancillary Cred Specialist enters a different address on a re-submission for the same Provider Type,
**When** the system applies the merge,
**Then** the AA's denormalised address fields (Address Line 1/2, City, State, ZIP, ZIP4, Telephone, Email, and the various Provider/Anesthesia/Hospital/Lab/Rad address blocks) are unchanged,
**And** the new address is created as a separate Address record on the Healthcare Facility via the existing additional-address pipeline,
**And** the existing Ancillary Assessment stays linked to whatever Address it was linked to before.

---

**AC-4.6 — Group C "blank-fill in Scenarios 2A/2B" is logged for ops visibility**

**Given** the resolver determined Scenario 2A or 2B and a Group-C field on the existing AA is blank,
**When** the form provides a non-blank value for that field and the merge applies the BLANK-FILL rule,
**Then** the field is filled,
**And** an Info-level log row is recorded noting the field name, the value applied, the Account, and the Provider Type — so ops can spot unusual patterns of post-HACAC blank-fills.

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AncillaryAssessmentMergeRule__mdt` | New Custom Metadata Type | Per-field rule table (FieldApiName, Group A-E, RuleScenario1, RuleScenario2A, RuleScenario2B, TrackInNativeHistory, Notes); 216 seed rows — one per queryable custom field on the Ancillary Assessment | AC-4.1 through 4.5 |
| `PRM_AncillaryProviderFormDataUpdates.mergeAaFields(existing, incoming, contextType) → MergeResult` | New Apex helper | Reads the metadata-driven rules and applies per-field merge; returns the merged AA + a `List<FieldChange>` describing every change for the audit log. Only invoked against the *same-Provider-Type* AA returned by the resolver. | AC-4.1 through 4.5 |
| Chatter post writer (Group B/C only) | New Apex helper | Builds a single FeedItem on the AA listing every changed Group-B/C field with field name, old → new, scenario, user, timestamp | AC-4.2, 4.3 |
| Change-log writer (all groups) | New Apex helper (per US-006) | Inserts one `PRM_AncillaryAssessmentChangeLog__c` row per changed field | AC-4.4 + US-006 |
| `PRM_ExceptionLogger.logException(..., 'GROUP_C_BLANK_FILL', ...)` | Log emitter | Info-level log entry for Scenario 2A/2B Group-C blank-fills | AC-4.6 |
| Deploy-time field-count assertion in `PRM_AncillaryProviderFormDataUpdatesTest` | Apex test | Fails CI if any new field is added to the AA object without a corresponding metadata rule row | Quality gate |
| Test matrix | Apex test | One method per (Group ∈ {A,B,C,D,E}) × (Scenario ∈ {1, 2A, 2B}) = 15 baseline cases + the AC-4.6 blank-fill log assertion | Quality gate |

### Definition of done

- [ ] CMDT deployed with 216 seed rows.
- [ ] Merge helper + Chatter post writer + change-log writer deployed.
- [ ] Test class at ≥ 95 % coverage with the 15-case matrix + blank-fill log assertion.

---

## US-005 — Data clean-up: dedupe existing duplicate same-Provider-Type AAs and stamp preserve flags retroactively

**Persona:** Ancillary Cred Specialist (acting as data steward for the dedupe run)
**Priority:** P1
**OmniScript:** N/A (batch only)
**Integration Procedures:** N/A
**Relevant Requirements:** TwoScenarios_UserStory §6 row 11; US-001 through US-004

> **Routing-rule impact assessment (2026-06-02):** US-005's dedupe key is **(Account, Provider Type)** — which is consistent with the "one AA per Provider Type per Account" invariant the new routing rule enforces going forward. The dedupe SOQL already groups by `(PRM_Account__c, PRM_ProviderTypeService__c)`, which is the Provider Type.

### Story

**As an** Ancillary Cred Specialist acting as data steward,
**I want** the org's existing duplicate same-Provider-Type Ancillary Assessments and inconsistent reassessment dates cleaned up before the new logic goes live,
**So that** the new resolver and HACAC rules don't run against polluted data and produce unpredictable results on accounts I am responsible for.

**Why it matters:** The live evidence on `001UW00000ejn1SYAQ` proves duplicates are already in production for Skilled Nursing. Going live with the new logic on top of duplicates would cause Committee Review to attach to the wrong Ancillary Assessment and produce visible regressions.

### Preconditions

- US-001 through US-004 deployed (so the new merge logic and the *Preserve* field exist and are referenced by the cleanup batch).

### Acceptance criteria

**AC-5.1 — Dedupe batch survives the earliest, merges the rest, deletes duplicates last (key: Account + Provider Type)**

**Given** an Account has more than one Ancillary Assessment for the same Provider Type,
**When** the dedupe batch processes that Account's group,
**Then** the earliest-created Ancillary Assessment in the group is chosen as the **survivor**,
**And** the field-level merge rule (US-004) is applied to copy values from each duplicate onto the survivor,
**And** if a duplicate has a Case Manager link and the survivor does not, the survivor inherits the duplicate's Case Manager link,
**And** the survivor's reassessment due date is set to the latest non-null value from the group (preserving the most-recent committee decision),
**And** every related Ancillary Staff record is re-pointed from the duplicate to the survivor,
**And** the duplicate Ancillary Assessments are deleted only after the survivor update and child re-parenting have committed successfully.

---

**AC-5.2 — Dry-run mode writes a full audit without changing data**

**Given** an Ancillary Cred Specialist launches the batch in dry-run mode,
**When** the batch executes,
**Then** no Ancillary Assessment, Ancillary Staff, or related record is updated or deleted,
**And** every action the batch would have taken is written to the audit log at Info severity (listing survivor, duplicates, Provider Type, and the planned field merges),
**And** the data-steward team can review the audit before re-running in live mode.

---

**AC-5.3 — After a live run, no Account has duplicate Ancillary Assessments for the same Provider Type**

**Given** the batch has been re-run with dry-run disabled,
**When** the data-steward team runs the post-batch audit query (saved in `requirements/SOQL/2026-06-02_AncillaryAssessment_AddSubService_Investigation.md` Query 5),
**Then** the query returns zero rows — no Account has more than one Ancillary Assessment for the same Provider Type anymore.

---

**AC-5.4 — Backfill the Preserve flag for AAs already in flight at deploy time**

**Given** the backfill batch is run after the dedupe batch,
**When** the backfill batch evaluates Ancillary Assessments whose reassessment due date is more than 1 year out AND whose Case Manager is currently in flight,
**Then** every such Ancillary Assessment has its *Preserve Re-Assessment Due Date* flag set to TRUE,
**And** no other Ancillary Assessment is touched.

---

**AC-5.5 — Both batches are idempotent**

**Given** either batch has just finished a successful run,
**When** the same batch is re-run immediately afterwards against the same data,
**Then** the second run produces zero record changes,
**And** no Info or Error log rows are added for the second run.

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_AncillaryAssessmentDedupeBatch.cls` | New `Database.Batchable<sObject>` | Groups AAs by `(PRM_Account__c, PRM_ProviderTypeService__c)`; applies survivor rule + US-004 merge; re-parents `PRM_AncillaryStaff__c`; deletes duplicates last | AC-5.1, 5.5 |
| Dry-run flag on the batch | Batch parameter | When TRUE, no DML; writes the merge plan to `PRM_ExceptionLog__c` at Info severity | AC-5.2 |
| Post-batch audit SOQL (Query 5) | SOQL query | `GROUP BY (Account, ProviderTypeService) HAVING COUNT(Id) > 1`; archived in the project SOQL folder | AC-5.3 |
| `PRM_AncillaryAssessmentBackfillPreserveFlagBatch.cls` | New batch | Sets preserve flag = TRUE on AAs where existing reassessment date > TODAY()+365 AND parent CM is in flight | AC-5.4 |
| Idempotency guards | Inside both batches | After-state SOQL inside the batch finish() method asserts zero further changes on a re-run | AC-5.5 |
| Test classes | New `PRM_AncillaryAssessmentDedupeBatchTest`, `PRM_AncillaryAssessmentBackfillPreserveFlagBatchTest` | Cover dry-run, live-run, idempotency, and the live-evidence Skilled Nursing duplicates on `001UW00000ejn1SYAQ` | Quality gate |

### Definition of done

- [ ] Both batches deployed.
- [ ] Dry-run executed in QA, audit reviewed by business sign-off.
- [ ] Live run scheduled with rollback plan documented.
- [ ] Post-run audit query returns zero duplicate (Account, Provider Type) rows.

---

## US-006 — Field-level audit trail for AA merges (native History + change-log object)

**Persona:** Ancillary Cred Specialist (acting as credentialing analyst auditing AA changes)
**Priority:** P0 (delivered alongside US-004 because the merge logic depends on it for compliance)
**OmniScript:** N/A
**Integration Procedures:** PRM_DataUpdationforHAPACCommitteeReview (consumes the audit), PRM_AncillaryFormRecordsCreation (writes audit)
**Relevant Requirements:** US-003, US-004, US-005

### Story

**As an** Ancillary Cred Specialist acting as credentialing analyst,
**I want** a complete audit trail of every field-level change the add-sub-service merge logic makes to an Ancillary Assessment,
**So that** I can reconstruct what changed on any Ancillary Assessment, when, by whom, and in which submission context — for HACAC review, regulatory audit, and dispute resolution.

**Why it matters:** Salesforce native History Tracking is limited to 20 fields per custom object. The Ancillary Assessment has 216 fields and Group D alone has ~185. Native History cannot cover the "overwrite per-type fields + enable history tracking" requirement on its own. This story delivers a two-layer audit: native History for the 20 highest-value fields plus a custom change-log object for everything else.

### Acceptance criteria

**AC-6.1 — Enable Native History Tracking on the 20 priority fields on Ancillary Assessment**

- **Object:** `PRM_AncillaryAssessment__c` (Ancillary Assessment)
- **Action:** Set Track Field History = TRUE on each of the following 20 fields and add the standard History related list to every Ancillary Assessment page layout.
- **Field list (top 20 priority — business confirmed):**
  1. `PRM_AuthorizedSignatureForProvider__c` — Authorized Signature
  2. `PRM_PrintName__c` — Print Name
  3. `PRM_Title__c` — Title
  4. `PRM_Date__c` — Signature Date
  5. `PRM_ReAssessmentDueDate__c` — Re-Assessment Due Date *(already tracked today)*
  6. `PRM_PreserveReassessmentDueDate__c` — Preserve Re-Assessment Due Date *(new field per US-001 AC-1.8)*
  7. `PRM_ProviderTypeService__c` — Provider Type & Service
  8. `PRM_CaseManager__c` — Case Manager
  9. `PRM_Accredited__c` — Accredited
  10. `PRM_AccreditationEffectiveDate__c` — Accreditation Effective Date
  11. `PRM_AccreditationExpirationDate__c` — Accreditation Expiration Date
  12. `PRM_SanctionsRestrictionsWithin5Years__c` — Sanctions / Restrictions within 5 yrs
  13. `PRM_SanctionedAccreditationwithin5Years__c` — Sanctioned Accreditation within 5 yrs
  14. `PRM_InsuranceInvoluntarilyRevokedTerm__c` — Insurance Involuntarily Revoked / Terminated
  15. `PRM_ParticipatinginMedicareProgram__c` — Participating in Medicare
  16. `PRM_ConvictedofMedicareFraud__c` — Convicted of Medicare Fraud
  17. `PRM_LicensedBeds__c` — Licensed Beds
  18. `PRM_NumberofOperatingRooms__c` — Number of Operating Rooms
  19. `PRM_MedicalDirectorName__c` — Medical Director Name
  20. `PRM_NameoftheAccreditingOrganization__c` — Name of the Accrediting Organization
- **Driver of selection:** The `PRM_TrackInNativeHistory__c` checkbox on `PRM_AncillaryAssessmentMergeRule__mdt` (US-004); business can swap fields in/out via metadata without code.

---

**AC-6.2 — Create the Ancillary Assessment Change Log object**

- **API Name:** `PRM_AncillaryAssessmentChangeLog__c`
- **Label / Plural:** Ancillary Assessment Change Log / Ancillary Assessment Change Logs
- **Sharing:** Controlled by Parent (parent = `PRM_AncillaryAssessment__c`)
- **Record Name format:** Auto Number — `AACL-{0000000000}`
- **Fields:**
  - `PRM_AncillaryAssessment__c` — Master-Detail(`PRM_AncillaryAssessment__c`); Required
  - `PRM_CaseManager__c` — Lookup(`IndividualApplication`)
  - `PRM_FieldApiName__c` — Text(80)
  - `PRM_FieldLabel__c` — Text(255)
  - `PRM_OldValue__c` — Long Text Area(32768)
  - `PRM_NewValue__c` — Long Text Area(32768)
  - `PRM_ChangedAt__c` — DateTime (default NOW())
  - `PRM_ChangedByUserId__c` — Lookup(`User`)
  - `PRM_ContextType__c` — Picklist {NEW, REUSE_IN_FLIGHT_PSV_SAME_PT, NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV, NEW_CM_AGAINST_APPROVED_AAS_SAME_PT, HACAC_DECISION, DATA_CLEANUP_BATCH, MANUAL}
  - `PRM_ChangeSource__c` — Text(255) (e.g., the class+method that wrote the row, for forensic traceability)
  - `PRM_Notes__c` — Long Text Area

---

**AC-6.3 — Field Access & Permission Sets for Ancillary Assessment Change Log**

- **System Administrator:**
  - Object level: Read, Create, Edit, Delete, View All Records, Modify All Records
  - Field level: Read, Edit
- **PRM_DataModifyAll:**
  - Object level: Read, View All Records
  - Field level: Read
- **PRM_AncillaryCredSpecialist, PRM_Credentialing, PRM_PDM:**
  - Object level: Read
  - Field level: Read
- **All other permission sets / profiles:** No access.
- **Direct write access:** No persona (including SysAdmin) is expected to insert/edit/delete change log rows from the UI; all writes happen via Apex helpers with `with sharing`.

---

**AC-6.4 — Every merge writer produces one change log row per changed field**

**Given** any of the three writers — the form submit merge (US-004), the HACAC reassessment-date calculator (US-003), or the dedupe batch (US-005) — modifies N fields on an Ancillary Assessment,
**When** the transaction completes,
**Then** exactly N Ancillary Assessment Change Log rows are inserted, one per changed field,
**And** each row points to the touched Ancillary Assessment via its master-detail,
**And** each row's *Context Type* reflects the writer (form merge → one of `REUSE_IN_FLIGHT_PSV_SAME_PT` / `NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` / `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT`; HACAC → `HACAC_DECISION`; dedupe batch → `DATA_CLEANUP_BATCH`).

---

**AC-6.5 — Change Log related list visible on the AA page layout**

**Given** an Ancillary Cred Specialist opens any Ancillary Assessment record page,
**When** the page renders,
**Then** the *Ancillary Assessment Change Logs* related list appears immediately below the standard Field History related list,
**And** the related list columns are: Field Label, Old Value, New Value, Changed At, Changed By, Context Type,
**And** the default sort is *Changed At* descending with a page size of 25.

---

**AC-6.6 — 7-year retention via monthly purge**

**Given** the monthly purge batch is scheduled,
**When** it runs on the 1st of the month,
**Then** every Ancillary Assessment Change Log row older than 7 years (Changed At < TODAY().addYears(-7)) is deleted,
**And** no row newer than that is touched.

---

**AC-6.7 — Audit-write coverage in unit tests**

**Given** the unit tests for US-003, US-004, and US-005 are run,
**When** the test suite executes,
**Then** every US-004 merge test asserts that one Change Log row exists per changed field with the right *Context Type*,
**And** the US-003 HACAC date-change test asserts that one Change Log row exists with Context Type = `HACAC_DECISION`,
**And** the US-005 dedupe batch test asserts that one Change Log row exists per field copied onto the survivor with Context Type = `DATA_CLEANUP_BATCH`.

---

**AC-6.8 — *(Stretch)* Unified audit timeline LWC on the Ancillary Assessment record page**

**Given** the audit-timeline Lightning Web Component is deployed and placed on the AA record page,
**When** an Ancillary Cred Specialist opens an Ancillary Assessment,
**Then** the LWC renders native History entries and Change Log rows in a single chronological timeline,
**And** the timeline offers filters by field, context type, user, and date range.

### Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| 20 Ancillary Assessment field metadata files | Modified | Add `<trackHistory>true</trackHistory>` per AC-6.1 | AC-6.1 |
| Ancillary Assessment page layouts | Modified | Add Field History related list | AC-6.1 |
| `PRM_AncillaryAssessmentChangeLog__c` | New custom object | Schema per AC-6.2 (picklist includes the new routing values) | AC-6.2 |
| Permission set updates | Modified per AC-6.3 | Read access on the new object/fields for the four named perm sets | AC-6.3 |
| `PRM_AncillaryAssessmentChangeLogWriter.cls` | New Apex helper | Inserts one change-log row per `FieldChange` returned by `PRM_AncillaryProviderFormDataUpdates.mergeAaFields` (US-004) / `PRM_AncillaryHACACReassessmentDateCalculator` (US-003) / `PRM_AncillaryAssessmentDedupeBatch` (US-005) | AC-6.4 |
| AA page layout — related list config | Modified | Adds the Change Log related list with the column set and sort per AC-6.5 | AC-6.5 |
| `PRM_AncillaryAssessmentChangeLogPurgeBatch.cls` + scheduled job | New Apex batch | Monthly purge of rows older than 7 years | AC-6.6 |
| Test class assertions | Additions to US-003/US-004/US-005 test classes | Assert change-log row counts and Context Type values | Quality gate |
| *(Stretch)* `prmAncillaryAssessmentAuditTimeline` | New LWC | Unified native-History + Change-Log timeline with filters | AC-6.8 (may move to a follow-up story) |

### Definition of done

- [ ] Change Log object + field history metadata + permission sets deployed.
- [ ] Writer helper deployed and called from all three writers (US-003, US-004, US-005).
- [ ] Purge batch deployed and scheduled.
- [ ] Stretch LWC tracked as a follow-up if not included in this sprint.

---

## Cross-cutting non-functional requirements

| Topic | Requirement |
|---|---|
| **Idempotency** | Submitting the same form twice within the same second must not create duplicate records. The resolver acquires a FOR UPDATE lock on the same-PT in-flight Case Manager query so simultaneous submissions for the same `(Account, Provider Type)` serialise. |
| **Concurrency** | Two simultaneous form submissions on the same Account but for *different* Provider Types proceed in parallel (they touch disjoint CM/AA sets). Two simultaneous submissions on the same `(Account, Provider Type)` serialise via the FOR UPDATE lock — the second either sees the first's Case Manager and reuses it (Scenario 1) or sees a Scenario 2A / 2B / brand-new state and routes accordingly. |
| **Auditability** | History tracking on the *Preserve Re-Assessment Due Date* field per US-001 AC-1.8. Chatter posts on the AA and CM per US-001 AC-1.10 and US-004 AC-4.2 / 4.3. Change Log rows on the AA per US-006. |
| **Performance** | The resolver issues at most 2 SOQL queries per submission, returns at most ~10 records, and adds no measurable latency to the form submit. |
| **Logging** | Every routing decision logs to `PRM_ExceptionLog__c` at Info severity with Account Id, submission's Provider Type, contextType, existing same-PT AA Id, preserve-flag candidate. |
| **Backwards compatibility** | The Reassessment OmniScript flow is unchanged (US-003 AC-3.6). PNC, PAR, OffCycle, and Delegated flows are out of scope. Different-Provider-Type Ancillary Assessments on the same Account are never touched by any add-sub-service submission. |
| **Test data** | Use `001UW00000ejn1SYAQ` (Skilled Nursing in-flight PSV CM + duplicate Skilled Nursing AA) for end-to-end regression. The US-001 live-data regression suite (L1–L5b) is the canonical test set; the US-005 dedupe batch's dry-run output must include this Account. |

---

## Open Clarification Questions (introduced 2026-06-02 with the Provider-Type-matching rule)

| # | Question | Impact | Owner |
|---|---|---|---|
| Q-R1 | When the Ancillary Cred Specialist "adds Skilled Vent service" to an in-flight Skilled Nursing review, is the change captured as (a) a Boolean / picklist field on the existing Skilled Nursing AA (e.g., `PRM_VentilatorChronicCareandorWeaning__c`), (b) a new value added to the multi-select picklist `PRM_ProviderTypeService__c` on the existing AA (would require new picklist values), or (c) something else captured on a child record? This document assumes (a) — the merge rule updates per-type fields on the existing AA. Confirm before US-001 implementation. | Determines whether US-002's "no new sub-service" rejection needs to inspect per-type fields only, or also the multi-select picklist. | Business (Ancillary Cred) + Tech |
| Q-R2 | If the Ancillary Cred Specialist accidentally selects services from more than one Provider Type on a single submission (multi-PT), should the system (a) reject outright with the message in US-002 AC-2.3 — *current proposal*, (b) split routing into one Case Manager per Provider Type, (c) prevent the situation at the form by limiting the multi-select picklist to one Provider Type at a time? | Determines US-002 AC-2.2 vs a larger refactor of the resolver and IP to fork submissions, or a UI-only change. | Business (Ancillary Cred) + Product |
| Q-R3 | The Service → Provider Type (= RecordType DeveloperName) mapping is assumed to already exist in `PRM_AncillaryProviderFormDataUpdates.getRecordIds()`. Confirm and link to the canonical implementation; if it lives elsewhere, the resolver needs the right reference. | Implementation pointer for US-001. | Tech |
| Q-R4 | When an Account has both an approved same-PT AA *and* an in-flight different-PT CM, the new submission for the same PT routes to `NEW_CM_AGAINST_APPROVED_AAS_SAME_PT` and a brand-new same-PT CM is created. Is there any business workflow that wants the new same-PT CM's Chatter post to mention the unrelated different-PT in-flight CM for visibility? Current proposal: no — keep the Chatter post focused on the same-PT context (US-001 AC-1.10 template 4 does not mention different-PT CMs). | Determines wording of US-001 AC-1.10 templates. | Business (Ancillary Cred) |

---

## Implementation order (suggested sprints)

| Sprint | Stories | Risk |
|---|---|---|
| 1 | US-001 schema half (Preserve field + FLS + Change-Log object from US-006 + native History on top-20) + US-004 CMDT schema | Low — additive, no behaviour change yet |
| 2 | US-001 behaviour half (resolver + IP_19 + Chatter writer + preserve-flag writer + child-record dedupe + all 5 live regression tests) + US-002 (rejection paths) + US-004 (merge helper + audit writes) | Medium — touches the records-creation IP end-to-end |
| 3 | US-003 (HACAC calculator + DR v2 + IP v9) | Medium — touches Committee Review flow |
| 4 | US-005 (data cleanup batch — dry-run, then live) + US-006 stretch LWC | High — touches live data; phased rollout per account batch |

---

## Resolved decisions log (business-confirmed)

| Decision | Resolution | Captured in |
|---|---|---|
| **Routing rule (updated 2026-06-02)** | **Reuse the in-flight Case Manager only when its Provider Type matches the submission's Provider Type.** Different Provider Type always creates a new Case Manager (even if another PT is in flight). One Ancillary Assessment per Provider Type per Account (sub-services are captured as fields on that one AA). | Decision matrix §0 + US-001 AC-1.2 |
| **Story consolidation (2026-06-03)** | The previously-separate scenario stories (old US-001, US-002, US-003, US-004) collapsed into a single US-001 owning the end-to-end form-submission contract. Old US-005…US-009 renumbered to US-002…US-006. | Story map §0 + each story header |
| Routing UX | **Auto-detect silently**, no extra screen | US-001 AC-1.1, 1.12 |
| Form pre-population on reuse | **Minimal** — pre-populate only Account / Identifiers / Contact-Person; Ancillary Cred Specialist re-fills sub-service detail fields | US-001 (drives OmniScript change in Sprint 2) |
| Multi-Provider-Type submissions | **Reject with a clear message** in v1; revisit split-routing per Q-R2 | US-002 AC-2.2, AC-2.3 |
| Data-refresh-only submissions | **Reject with a clear message** — at least one new sub-service detail must change | US-002 AC-2.1, AC-2.3 |
| Group B (Warranty / Signature) merge rule | **ALWAYS OVERWRITE + Chatter audit** | US-004 AC-4.2 + US-006 |
| Group C (Cross-type common) merge rule | **Hybrid** — OVERWRITE non-blank in Scenario 1; BLANK-FILL ONLY in Scenarios 2A/2B | US-004 AC-4.3 + CMDT split per scenario |
| Group D (Per-type specific) merge rule | **ALWAYS OVERWRITE + field history tracking** (top-20 native History + change-log object for remaining ~165) | US-004 AC-4.4 + US-006 |
| Group E (Address) | **PRESERVE** AA fields; new addresses via existing pipeline | US-004 AC-4.5 |
| Past-PSV same-PT in-flight CM behaviour | Same-PT CM not in PSV → create new CM, update existing same-PT AA (link unchanged) | US-001 AC-1.2 (`NEW_CM_ALONGSIDE_SAME_PT_PAST_PSV` row) |
| Different-PT in-flight CM behaviour | Different PT → create new CM as "brand-new for this Provider Type"; in-flight different-PT CM is untouched | US-001 AC-1.2 (`NEW` row) + AC-1.10 template 1 |
| Preserve-reassessment-date storage | **Per-AA field** *Preserve Re-Assessment Due Date* (Boolean) | US-001 AC-1.8 + US-003 |
| Threshold for preserve | At form-submission TODAY(): existing reassessment date > TODAY()+365 ⇒ preserve | US-001 AC-1.7 + US-003 |
| Per-AA vs consolidated reassessment dates | **Per-AA** (current behaviour preserved) | Decision matrix + US-001 AC-1.5 |
| Explicit Reassessment OmniScript flow | **Unchanged** — keeps current +3yrs behaviour | US-003 AC-3.6 |
| Dedupe survivor rule | **Earliest-created** survives; **latest non-null** reassessment date wins; child Ancillary Staff repointed; dedupe key = (Account, Provider Type) | US-005 AC-5.1 |

---

## Appendix — files / components inventory (active versions only)

| Layer | Component | Action |
|---|---|---|
| OmniScript | `PRM_AncillaryWelcomeScreen_English_3` | No change (routing is silent) |
| OmniScript | `PRM_AncillaryProviderForm_English_38` → `_English_39` | New version: pre-populate minimal block, validation hooks for both US-002 rejection messages |
| IP | `PRM_AncillaryFormRecordsCreationParent_Procedure_2` → `_Procedure_3` | New version: wire to IP_19 |
| IP | `PRM_AncillaryFormRecordsCreation_Procedure_18` → `_Procedure_19` | New version: step 1 calls resolver; record-creation steps made conditional on `contextType`; short-circuits for both reject contextTypes; merge step routes to US-004 |
| Apex | `PRM_AncillaryProviderFormDataUpdates.cls` | Refactor `insertAARecords` to merge-only against same-PT AA per US-001 AC-1.2 (three reuse-of-AA outcomes); `getRecordIds()` (Service → RecordType mapping) reused as the canonical Service → Provider Type mapping for the resolver |
| Apex (new) | `PRM_AncillaryFormContextResolver.cls` | New, US-001 — Provider-Type-aware routing + preserve-flag writer + child-record dedupe orchestration |
| Apex (new) | `PRM_AncillaryHACACReassessmentDateCalculator.cls` | New, US-003 |
| Apex (new) | `PRM_AncillaryAssessmentChangeLogWriter.cls` | New, US-006 |
| Apex (new) | `PRM_AncillaryAssessmentDedupeBatch.cls` | New, US-005 |
| Apex (new) | `PRM_AncillaryAssessmentBackfillPreserveFlagBatch.cls` | New, US-005 |
| Apex (new) | `PRM_AncillaryAssessmentChangeLogPurgeBatch.cls` | New, US-006 |
| IP | `PRM_DataUpdationforHAPACCommitteeReviewParent_Procedure_1` | No change (still calls child) |
| IP | `PRM_DataUpdationforHAPACCommitteeReview_Procedure_8` → `_Procedure_9` | New version: insert HACAC calculator step before load DR |
| DR | `PRMDRHACACUpdateAncillaryAssessmentRecords_1` → `_2` | New version: remove ADDYEAR formula, read date from IP context |
| CMDT (new) | `PRM_AncillaryAssessmentMergeRule__mdt` | New, US-004; seed 216 rows |
| SObject (new) | `PRM_AncillaryAssessmentChangeLog__c` | New, US-006; `PRM_ContextType__c` picklist includes the Provider-Type-aware values from AC-6.2 |
| Field (new) | `PRM_AncillaryAssessment__c.PRM_PreserveReassessmentDueDate__c` | New Boolean, US-001 AC-1.8 |
| Field (modified) | 20 fields on Ancillary Assessment → `<trackHistory>true</trackHistory>` per US-006 AC-6.1 | Add native history tracking |
| LWC (new, stretch) | `prmAncillaryAssessmentAuditTimeline` | New, US-006 AC-6.8 |
| OmniScript | `PRM_ReviewHACAC_English_6` | No change (still wired to the parent IP) |
| All other Ancillary flows (Reassessment, PSV form retrieval, PDA, QC) | No change |
