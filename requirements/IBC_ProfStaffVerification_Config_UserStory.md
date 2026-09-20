# USER STORY 1: IBC Professional Staff Verification — Configuration Foundation (Record Type, Field, Picklists, Layout, Path, Group/Queue, List View)

**Persona:** Credentialing Specialist
**Priority:** P1 (AI-estimated — validate with team)
**OmniScript:** N/A (declarative configuration only)
**Integration Procedures:** N/A
**Relevant Requirements:** `requirements/IBC_ProfStaffVerification_Batch_UserStory.md` (Story 2), `requirements/IBC_ProfStaffVerification_Flow_UserStory.md` (Story 3a), `requirements/IBC_ProfStaffVerification_Termination_UserStory.md` (Story 3b)

> **Story set:** This is the **config foundation** story for IBC Professional Staff Verification (PSV). Stories 2 (daily batch), 3a (verification flow), and 3b (termination flow) depend on the metadata created here.

---

## Story

**As a** Credentialing Specialist,
**I want** the Case Manager and Case objects configured with a Professional Staff Verification record type, outcome field, stage/status/type values, page layout, path, list view, and a dedicated public group and queue,
**So that** yearly professional-staff verification cases can be routed to my team, worked through a consistent screen, and tracked to completion without manual setup.

**Why it matters:** Professional staff are re-verified yearly rather than fully re-credentialed. Without a dedicated record type, outcome field, and routing queue, these verification cases cannot be created by the daily batch (Story 2) or worked through the verification flow (Stories 3a/3b). This story establishes the declarative scaffolding the rest of the feature builds on.

---

## Scope

| Area | Object | Change |
|------|--------|--------|
| Record Type | Case Manager (`IndividualApplication`) | New: Professional Staff Verification |
| Field | Case Manager (`IndividualApplication`) | New picklist: Professional Staff Verification Outcome |
| Picklist values | Case Manager Stage & Status | New values for the PSV record type |
| Case Type | Case | New value: Prof Staff Verification |
| Page Layout | Case Manager | New PSV layout |
| Path | Case Manager | New PSV path on Stage |
| Routing | Public Group + Queue | New PSV group and queue |
| List View | Case Manager | New PSV list view |

**Out of scope:** batch creation of the records (Story 2), the verification guided flow (Stories 3a/3b), and any Apex.

---

## Acceptance Criteria

**AC-1 — New Case Manager Record Type: Professional Staff Verification** *(Pattern B)*

- **Object:** Case Manager (`IndividualApplication`)
- **Record Type Label:** Professional Staff Verification
- **Record Type Name (API):** `PRM_ProfessionalStaffVerification`
- **Description:** Used for yearly professional staff verification for professional staff.
- **Active:** TRUE
- **Available on profiles:** all IBX profiles
- **Permission-set access (record type assignment):** `PRM_CredentialingUser`, `PRM_CredentialingCompliance`, `PRM_SeniorDataReportingSpecialist`, `PRM_ProviderDataAdmin`

**AC-2 — New field: Professional Staff Verification Outcome** *(Pattern B)*

- **API Name:** `PRM_ProfessionalStaffVerificationOutcome__c`
- **Object:** Case Manager (`IndividualApplication`)
- **Label:** Professional Staff Verification Outcome
- **Type:** Picklist
- **Description:** Used to store the Professional Staff Verification Outcome for Professional Staff.
- **Picklist Values:** `Verification Complete`, `Manager Review`, `Term Professional Staff`
- **Track History:** true (recommended — confirm; see Clarification #3)
- **Metadata sync:** added from Salesforce to DART Metadata & Data Dictionary

**AC-3 — Field access & permission sets for Professional Staff Verification Outcome** *(Pattern C)*

- **`PRM_CredentialingUser`, `PRM_CredentialingCompliance`:**
  - Field level: Read and Edit
- **`PRM_ProviderDataAdmin`, `PRM_NetworkManagementQC`:**
  - Field level: Read
- **`PRM_DataViewAll`:**
  - Object level: View All Records
  - Field level: Read
- **`PRM_DataModifyAll`:**
  - Object level: Read, Create, Edit, View All Records
  - Field level: Read and Edit

**AC-4 — Stage picklist values available for the PSV record type** *(Pattern B)*

- **Field:** Stage (Case Manager `IndividualApplication`)
- **Record Type:** Professional Staff Verification (`PRM_ProfessionalStaffVerification`)
- **Values available on this record type:**
  - `Professional Staff Verification` — **new value**
  - `Complete` — existing value, made available on this record type

**AC-5 — Status picklist values available for the PSV record type** *(Pattern B)*

- **Field:** Status (Case Manager `IndividualApplication`)
- **Record Type:** Professional Staff Verification (`PRM_ProfessionalStaffVerification`)
- **Values available on this record type:**
  - `New` — existing
  - `Manager Review` — **new value**
  - `Approved` — existing
  - `Denied` — existing

**AC-6 — New Case Type value** *(Pattern B)*

- **Field:** Type (Case)
- **New value:** `Prof Staff Verification`

**AC-7 — Professional Staff Verification page layout** *(Pattern B — layout spec)*

- **Object:** Case Manager (`IndividualApplication`)
- **Layout Label:** Professional Staff Verification
- **Assigned to record type:** Professional Staff Verification
- **Sections & fields:**

| Section | Left column | Right column |
|---------|-------------|--------------|
| **Case Manager Information** | Application ID | Application Type |
| | Stage | Applied Date |
| | Latest Case | Decision Date |
| | Case Manager Age | |
| **Professional Staff Verification** | License Verification | SAM Review |
| | OIG Review Outcome | Professional Staff Verification Outcome |
| **System Information** | Created By | Last Modified By |

**AC-8 — New Path for Case Manager (PSV)** *(Pattern B)*

- **Object:** Case Manager (`IndividualApplication`)
- **Record Type:** Professional Staff Verification
- **Path picklist:** Stage
- **Added to:** the Professional Staff Verification record page (Lightning record page for the PSV record type)

**AC-9 — New Public Group & Queue** *(Pattern B)*

- **Public Group:**
  - Label: Professional Staff Verification
  - Group Name (API): `PRM_ProfessionalStaffVerificationPG`
- **Queue:**
  - Label: Professional Staff Verification Queue
  - Queue Name (API): `PRM_ProfessionalStaffVerificationQueue`
  - Supported object: Case Manager (`IndividualApplication`)
  - Members: the Professional Staff Verification Public Group is assigned to the Professional Staff Verification Queue

**AC-10 — Professional Staff Verification list view** *(Pattern B — list view spec)*

- **Object:** Case Manager (`IndividualApplication`)
- **List View Label:** Professional Staff Verification
- **Filters:**
  - Owner = Professional Staff Verification Queue
  - Stage ≠ Complete
- **Columns:** Application ID, Account, Stage, Status, Created Date, Last Modified Date

**AC-11 — Verification behaviour (happy path, business language)** *(Pattern A)*

**Given** a Case Manager record with record type Professional Staff Verification is assigned to the Professional Staff Verification Queue,
**When** a Credentialing Specialist opens the Professional Staff Verification list view,
**Then** the case appears in the list with its Application ID, Account, Stage, Status, Created Date, and Last Modified Date,
**And** the case is visible only while its Stage is not Complete,
**And** the Case Manager record opens on the Professional Staff Verification layout with the Stage path displayed.

**AC-12 — Access edge case (negative)** *(Pattern A)*

**Given** a user whose profile has no PSV-related permission set assigned,
**When** they open a Professional Staff Verification Case Manager record,
**Then** they cannot edit the Professional Staff Verification Outcome field,
**And** users with only view-all access (`PRM_DataViewAll`, `PRM_NetworkManagementQC`, `PRM_ProviderDataAdmin`) can read but not edit it.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `IndividualApplication` → `PRM_ProfessionalStaffVerification` | New Record Type | Case Manager record type; active; assigned to the 4 permission sets; available all IBX profiles | Drives AC-1 |
| `IndividualApplication.PRM_ProfessionalStaffVerificationOutcome__c` | New custom picklist field | 3 values (Verification Complete / Manager Review / Term Professional Staff) | Drives AC-2; sync to DART Data Dictionary |
| Permission sets (`PRM_CredentialingUser`, `PRM_CredentialingCompliance`, `PRM_ProviderDataAdmin`, `PRM_NetworkManagementQC`, `PRM_DataViewAll`, `PRM_DataModifyAll`) | Modified FLS / RT assignment | Field + record-type access per AC-3 | Drives AC-3 |
| `IndividualApplication` Stage picklist | New value + RT value set | Add `Professional Staff Verification`; expose `Complete` for the RT | Drives AC-4 |
| `IndividualApplication` Status picklist | New value + RT value set | Add `Manager Review`; expose New/Approved/Denied for the RT | Drives AC-5 |
| `Case.Type` picklist | New value | Add `Prof Staff Verification` | Drives AC-6 |
| Case Manager page layout "Professional Staff Verification" | New layout | Sections per AC-7; assign to the PSV RT | Drives AC-7 |
| Case Manager Lightning record page + Path | New Path (Stage) | Add Path component to the PSV record page | Drives AC-8 |
| `PRM_ProfessionalStaffVerificationPG` (Public Group) + `PRM_ProfessionalStaffVerificationQueue` (Queue) | New Group + Queue | Group assigned to Queue; Queue supports `IndividualApplication` | Drives AC-9; consumed by Story 2 round-robin |
| Case Manager list view "Professional Staff Verification" | New list view | Filters + columns per AC-10 | Drives AC-10 |

---

## Definition of done

- [ ] `PRM_ProfessionalStaffVerification` record type deployed, active, assigned to the 4 permission sets, and available on all IBX profiles.
- [ ] `PRM_ProfessionalStaffVerificationOutcome__c` deployed with the 3 picklist values and FLS applied per AC-3; entry added to DART Metadata & Data Dictionary.
- [ ] Stage exposes `Professional Staff Verification` + `Complete`, and Status exposes `New / Manager Review / Approved / Denied`, for the PSV record type.
- [ ] `Prof Staff Verification` Case Type value deployed.
- [ ] PSV page layout deployed and assigned to the PSV record type; all listed fields present in the correct sections.
- [ ] Stage Path deployed and shown on the PSV record page.
- [ ] `PRM_ProfessionalStaffVerificationPG` and `PRM_ProfessionalStaffVerificationQueue` deployed; group assigned to the queue.
- [ ] PSV list view deployed with the specified filters and columns; verified by a Credentialing Specialist.
- [ ] Access edge case verified: view-only perm sets cannot edit the outcome field.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | The requirement lists `PRM_NetworkManagementQC` for **field Read** access on the outcome field but not for record-type assignment. Confirm QC should have field-read only (no RT assignment). | FLS vs. RT assignment scope | BA / Admin |
| 2 | Should the queue's round-robin assignment be configured here (config), or is the round-robin logic entirely owned by the Story 2 batch? | Prevents duplicate ownership logic | Technical |
| 3 | Should `PRM_ProfessionalStaffVerificationOutcome__c` have field-history tracking enabled (for audit/reporting)? | Reporting / audit | BA |
| 4 | Confirm `Case Manager Age`, `License Verification`, `SAM Review`, and `OIG Review Outcome` already exist as fields on `IndividualApplication` (layout AC-7 assumes they do). | Layout deployability | Technical |
| 5 | Confirm the queue supports `IndividualApplication` (Case Manager) rather than the standard `Case` object, since PSV cases are tracked on the Case Manager. | Routing correctness | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `IndividualApplication` (Case Manager) | Object metadata | MEDIUM | New RT, field, picklist values, layout, path, list view |
| Case | Object metadata | LOW | New Type picklist value |
| Permission sets (6) | Access | MEDIUM | FLS + RT assignment changes |
| Public Group / Queue | Routing | LOW | New group + queue |
| Existing Case Manager record types / layouts | Config | LOW | Must remain unaffected (regression) |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Record type + RT assignment | Config | S | New RT, 4 perm-set assignments |
| Outcome picklist field + FLS | Config | S | 3 values, 6 perm sets |
| Stage / Status / Case Type values | Config | S | Picklist value adds + RT value sets |
| Page layout | Config | M | New layout, field placement |
| Path + record page | Config | S | Stage path |
| Public Group + Queue | Config | S | Group → Queue assignment |
| List view | Config | S | Filters + columns |
| DART Data Dictionary sync | Config/process | S | Metadata registration |

**Total Estimated Effort:** ~M (≈0.5–1 day of declarative config) — AI-estimated, validate with team.
